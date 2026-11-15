"""La ficha pública de un equipo: todo lo que la unidad sabe de él, leído del mismo registro que usan
reservas, gestión y reportes.

Un equipo es un tipo (su ficha técnica) con una o varias unidades físicas, cada una con su código,
estado, ubicación y área. La ficha muestra el tipo completo y todas sus unidades; los insumos y el
software salen del inventario y del catálogo de programas, no de un texto aparte.
"""
from django.db.models import Q
from django.templatetags.static import static
from django.urls import reverse

from apps.recursos.models.redistribucion import AlertaUsoEquipo, EquipoEnTraspaso, TraspasoEquipo
from apps.recursos.models.consumibles import ConsumiblePorEquipo
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.componentes_equipo import componentes_con_inventario
from apps.gestion_unidades.presentation.plantillas_ficha import ficha_estandar
from apps.recursos.presentation.uso_equipos import situaciones


def renglones(texto):
    return [renglon.strip(' -•\t') for renglon in (texto or '').splitlines() if renglon.strip(' -•\t')]


def pares(texto):
    """Las características escritas «Clave: valor», una por renglón, como pares."""
    return [tuple(parte.strip() for parte in (renglon.split(':', 1) + [''])[:2]) for renglon in renglones(texto)]


def imagen_de(tipo):
    """La foto propia del equipo o su foto de catálogo; vacío si no tiene (se ilustra con su ícono)."""
    if tipo.imagen:
        try:
            return tipo.imagen.url, False
        except ValueError:
            pass
    if tipo.imagen_catalogo:
        return static(tipo.imagen_catalogo), True
    return '', False


def documentos_de(tipo):
    archivos = (('Ficha técnica del fabricante', 'fas fa-file-pdf', tipo.ficha_tecnica),
                ('Manual de operación', 'fas fa-book', tipo.manual_operacion),
                ('Video de montaje y cuidados', 'fas fa-video', tipo.video_montaje_cuidados),
                ('Instalación de controladores', 'fas fa-plug', tipo.explicacion_drivers))
    documentos = [{'nombre': nombre, 'icono': icono, 'url': archivo.url} for nombre, icono, archivo in archivos if archivo]
    vistos = {documento['url'] for documento in documentos}
    for documento in tipo.medios_publicos.get('documentos', []):
        if documento['url'] not in vistos:
            documentos.append({'nombre': documento['titulo'], 'icono': 'fas fa-external-link-alt', 'url': documento['url']})
            vistos.add(documento['url'])
    return documentos


LEMA_MAXIMO = 180


def por_unidad(equipos, situacion_de):
    """Los equipos agrupados por unidad: cuántos, cuántos disponibles y, si se midió, horas y ociosos."""
    grupos = {}
    for equipo in equipos:
        grupo = grupos.setdefault(equipo.laboratorio_id, {
            'unidad': equipo.laboratorio, 'total': 0, 'disponibles': 0, 'horas': 0.0, 'ociosos': 0, 'modelos': [],
            'url': reverse('ficha_equipo_publica', args=[equipo.laboratorio.slug, equipo.codigo_unidad])})
        grupo['total'] += 1
        grupo['disponibles'] += equipo.estado_unidad == 'disponible'
        if equipo.equipo.nombre not in grupo['modelos']:
            grupo['modelos'].append(equipo.equipo.nombre)
        situacion = situacion_de.get(equipo.pk)
        if situacion:
            grupo['horas'] += situacion['horas']
            grupo['ociosos'] += situacion['alerta']
    for grupo in grupos.values():
        grupo['horas_por_equipo'] = round(grupo['horas'] / grupo['total'], 1)
    return sorted(grupos.values(), key=lambda grupo: (-grupo['total'], grupo['unidad'].nombre))
NIVELES_DE_EQUIPAMIENTO = {'basico': 'Equipamiento básico', 'alta': 'Equipamiento de alta capacidad'}


def detalle_de_equipo(unidad, unidad_equipo, gestor=False):
    from apps.formacion.presentation.aula import ICONOS_DE_ESPACIO

    tipo = unidad_equipo.equipo
    # Quien gestiona ve todas las unidades físicas; el público, solo las que están en servicio.
    base = UnidadEquipo.objects.all() if gestor else UnidadEquipo.objects.publicos()
    unidades = list(
        base.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), equipo=tipo, activa=True)
        .prefetch_related('espacios_asociados').distinct().order_by('codigo_unidad')
    )
    if unidad_equipo not in unidades:
        unidades.insert(0, unidad_equipo)
    espacios = {}
    for fisica in unidades:
        fisica.areas = list(fisica.espacios_asociados.all())
        for espacio in fisica.areas:
            espacios[espacio.pk] = espacio
    # Lo que aporta la ficha del área (nivel, ícono, insumos que nombra) solo si está publicada o lo ve su gestor.
    elementos = ElementoFichaArea.objects.filter(registrado__equipo=tipo, ficha__espacio__unidad=unidad)
    if not gestor:
        elementos = elementos.filter(ficha__publicada=True)
    elemento = elementos.select_related('ficha__espacio').first()
    insumos = list(ConsumiblePorEquipo.objects.filter(equipo=tipo, consumible__unidad=unidad, consumible__activo=True)
                   .select_related('consumible').order_by('consumible__nombre'))
    software = list(SoftwareDisponible.objects.filter(unidad=unidad, activo=True, equipos_instalados__equipo=tipo)
                    .distinct().order_by('nombre'))
    imagen, referencial = imagen_de(tipo)
    # Lo que trabaja junto a él en sus áreas, para seguir recorriendo.
    vecinos = {}
    for vecino in (base.filter(espacios_asociados__in=espacios, activa=True).exclude(equipo=tipo)
                   .select_related('equipo').order_by('equipo__nombre', 'codigo_unidad')):
        vecinos.setdefault(vecino.equipo_id, vecino)
    areas = [{'espacio': espacio, 'url': reverse('area_unidad', args=[unidad.slug, espacio.codigo]),
              'icono': ICONOS_DE_ESPACIO.get(espacio.tipo, 'fas fa-vector-square')} for espacio in espacios.values()]
    for fisica in unidades:
        # Las áreas de cada unidad física, para la identificación que cambia de unidad sin recargar.
        propias = {espacio.pk for espacio in fisica.areas}
        fisica.areas_detalle = [area for area in areas if area['espacio'].pk in propias]
        # El lugar dentro del área, sin repetir su nombre («Impresión 3D · Granja de impresión» → «Granja de impresión»).
        lugar = (fisica.ubicacion_especifica or '').strip()
        for espacio in fisica.areas:
            if lugar.lower().startswith(espacio.nombre.lower()):
                lugar = lugar[len(espacio.nombre):].lstrip(' ·-—,:')
        fisica.lugar = lugar
    # Dónde más está este modelo y sus equivalentes (la misma familia de producto): para reservar allá y, en
    # gestión, para ver si conviene redistribuir antes de comprar.
    ajenos = (base.filter(activa=True, laboratorio__activo=True).exclude(laboratorio=unidad)
              .exclude(laboratorio__isnull=True).select_related('laboratorio', 'equipo'))
    mismo_modelo = list(ajenos.filter(equipo=tipo).order_by('laboratorio__nombre', 'codigo_unidad'))
    equivalentes = (list(ajenos.filter(equipo__familia_id=tipo.familia_id).exclude(equipo=tipo)
                         .order_by('laboratorio__nombre', 'equipo__nombre', 'codigo_unidad')) if tipo.familia_id else [])
    situacion_de = situaciones(unidades + mismo_modelo + equivalentes) if gestor else {}
    alertas, traspasos = {}, {}
    if gestor:
        from apps.recursos.presentation.lector_equipos import recorrido_de

        alertas = {alerta.equipo_id: alerta for alerta in
                   AlertaUsoEquipo.objects.filter(equipo__in=unidades, estado__in=AlertaUsoEquipo.VIGENTES)}
        traspasos = {item.equipo_id: item.traspaso for item in
                     EquipoEnTraspaso.objects.filter(equipo__in=unidades, traspaso__estado__in=TraspasoEquipo.EN_CURSO)
                     .select_related('traspaso__unidad_destino')}
    for fisica in unidades:
        fisica.situacion = situacion_de.get(fisica.pk)
        # Quien gestiona: la alerta de uso, el traspaso en curso y por qué unidades ha pasado.
        fisica.alerta_uso = alertas.get(fisica.pk)
        fisica.traspaso_en_curso = traspasos.get(fisica.pk)
        fisica.recorrido = recorrido_de(fisica) if gestor else []
    estandar = ficha_estandar(tipo, gestor=gestor)
    insumos_de_ficha = elemento.lista_consumibles if elemento and not insumos else []
    # Componentes con foto (las del modelo, tipo accesorio) o ícono, y los consumibles del inventario con los repuestos.
    estandar['componentes'] = componentes_con_inventario(
        estandar['componentes'], insumos, insumos_de_ficha,
        [foto for foto in estandar['fotos'] if foto['tipo'] in ('Accesorio', 'Detalle')])
    descripcion, uso = (tipo.descripcion or '').strip(), (tipo.uso_publico or '').strip()
    comercial = ' '.join(filter(None, (tipo.marca, tipo.modelo))).strip()
    referencia = next((item['valor'] for item in estandar['especificaciones'] if item['clave'].lower() == 'modelo de referencia'), '')
    propuesta = tipo.medios_publicos.get('identidad_propuesta', {})
    if propuesta:
        referencia = ' '.join(filter(None, (propuesta.get('marca'), propuesta.get('modelo'))))
    comercial_completo = bool(tipo.marca and tipo.modelo)
    return {
        'tipo': tipo,
        'estandar': estandar,
        # Lo que distingue al modelo a primera vista: «HP Z8 Fury G5» o, mientras la unidad no confirme marca y
        # modelo, el modelo de referencia de su ficha («Meta Quest 3S o Quest 3»).
        'nombre_comercial': comercial if comercial_completo or not referencia else referencia,
        'nombre_comercial_referencial': not comercial_completo and bool(referencia),
        # Una frase corta va de lema en la portada y no se repite en «Descripción»; lo que repite la descripción
        # tampoco vuelve como «Para qué se usa».
        'lema': descripcion if len(descripcion) <= LEMA_MAXIMO else '',
        'uso_propio': '' if uso == descripcion else uso,
        'posicion': next((indice for indice, fisica in enumerate(unidades, start=1) if fisica.pk == unidad_equipo.pk), 1),
        'unidades': unidades,
        'otras_unidades': por_unidad(mismo_modelo, situacion_de),
        'equivalentes': por_unidad(equivalentes, situacion_de),
        'aqui': {'horas': round(sum(s['horas'] for s in (f.situacion for f in unidades) if s), 1),
                 'ociosos': sum(1 for f in unidades if f.situacion and f.situacion['alerta'])} if gestor else None,
        'disponibles': sum(1 for fisica in unidades if fisica.activa and fisica.estado_unidad == 'disponible'),
        'en_inventario': sum(1 for fisica in unidades if fisica.activa and not fisica.fecha_baja),
        'areas': areas,
        'caracteristicas': pares(tipo.caracteristicas_publicas),
        'cuidados': renglones(tipo.instrucciones_publicas),
        'insumos': insumos,
        # Sin insumos atados en el inventario, los que nombra la ficha del área.
        'insumos_de_ficha': insumos_de_ficha,
        'software': software,
        # El texto libre del tipo, cuando no hay programas instalados («No requiere…» no es un programa).
        'software_de_ficha': [] if software or (tipo.software or '').strip().lower().startswith('no ')
        else [nombre.strip() for nombre in (tipo.software or '').split(',') if nombre.strip()],
        'auxiliares': list(tipo.auxiliares.filter(unidades__laboratorio=unidad, unidades__activa=True).distinct()),
        'icono': tipo.icono or (elemento.icono if elemento else '') or 'fas fa-cogs',
        'nivel': NIVELES_DE_EQUIPAMIENTO.get(elemento.nivel, elemento.get_nivel_display()) if elemento and elemento.nivel else '',
        'imagen': imagen,
        'imagen_referencial': referencial,
        'documentos': documentos_de(tipo),
        'vecinos': [{'equipo': vecino, 'imagen': imagen_de(vecino.equipo)[0],
                     'url': reverse('ficha_equipo_publica', args=[unidad.slug, vecino.codigo_unidad])}
                    for vecino in list(vecinos.values())[:8]],
    }
