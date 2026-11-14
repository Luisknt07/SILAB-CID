"""El lector de equipos: se apunta la cámara a la etiqueta y aparece todo lo del equipo.

Lee el código de barras de bodega, el QR del sistema o un código escrito a mano. Si el equipo ya está
registrado muestra su situación completa (estado, unidad y área, mantenimientos, incidencias, vida
útil, uso, recorrido entre unidades e historia) y lo ubica entre los suyos: los hermanos (el mismo
modelo en la unidad), el mismo modelo en otras unidades y su familia de producto. Si el código es
nuevo, lo primero es qué equipo es: llega del reporte de bodega guardado o se escribe, y con ese nombre
se muestra solo lo relacionado (los equipos de la unidad sin código, los modelos que ya existen y las
áreas donde suele estar). Quien gestiona los recursos asigna el código a un equipo sin código (lo habitual
al etiquetar lo que la unidad ya usaba) o abre el alta completa en la gestión, con todo eso ya puesto.
El custodio y el valor solo los ve quien gestiona la unidad del equipo.
"""
import json
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.gestion_unidades.management.fichas_area.familias_equipo import familia_de
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.recursos.presentation.catalogo_inventario import nucleo, palabras, se_excluyen, semejanza
from apps.recursos.presentation.codigos_equipo import PREFIJO_INSTITUCIONAL, buscar_equipo, codigo_leido, etiqueta_de, ve_datos_patrimoniales
from apps.recursos.presentation.equipo_publico import imagen_de
from apps.recursos.presentation.ficha_equipo import ficha_equipo, linea_de_trazabilidad
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.recursos.presentation.reportes_bodega import bien_de_bodega, fecha_de, serie_de, valor_de

# Desde qué parecido un modelo o un equipo cuenta como relacionado con el nombre leído.
PARECIDO_MINIMO = 0.3

# Lo que cuenta un cambio de custodio nombra a funcionarios: solo lo lee quien gestiona la unidad.
HITOS_PATRIMONIALES = {'cambio_custodio'}


def puede_usar_lector(usuario):
    """El lector es para el personal: staff o quien opera los recursos o el mantenimiento de alguna unidad."""
    if usuario.is_staff or usuario.is_superuser:
        return True
    return any(puede_operar_modulo_unidad(usuario, unidad, modulo)
               for unidad in Unidad.objects.filter(activo=True) for modulo in ('recursos', 'mantenimiento'))


def _unidades_que_registra(usuario):
    return [unidad for unidad in Unidad.objects.filter(activo=True).order_by('nombre')
            if puede_operar_modulo_unidad(usuario, unidad, 'recursos')]


def gestion_de_activos(unidad, **parametros):
    """La gestión de recursos de la unidad (activos y espacios), con lo que el lector le pide abrir."""
    consulta = {'view': 'recursos', 'modo_recursos': 'activos', **parametros}
    return f"{reverse('gestion_unidad', args=[unidad.slug])}?{urlencode(consulta)}"


def datos_de_bodega(usuario, codigo):
    """Lo que el reporte de bodega guardado dice de un código nuevo: con eso el registro arranca lleno.

    El custodio, la ubicación, la fecha de ingreso y el valor solo van a quien gestiona la unidad del bien.
    """
    bien = bien_de_bodega(codigo)
    if not bien:
        return None
    unidad = Unidad.objects.filter(slug=bien['unidad'], activo=True).first()
    area = EspacioReservable.objects.filter(unidad=unidad, codigo=bien['area'], activo=True).first() if unidad else None
    datos = {
        'nombre': bien.get('nombre') or bien['descripcion'].strip().capitalize(),
        'descripcion': bien['descripcion'],
        'marca': bien.get('marca', '').title(),
        'modelo': bien.get('modelo', ''),
        'color': bien.get('color', ''),
        'material': bien.get('material', ''),
        'dimensiones': bien.get('dimensiones', ''),
        'serie': serie_de(bien),
        'tipo_bien': bien.get('tipo_bien', '').upper() if bien.get('tipo_bien', '').upper() in dict(UnidadEquipo.TIPOS_BIEN) else '',
        'unidad': unidad.slug if unidad else '',
        'unidad_nombre': unidad.nombre if unidad else '',
        'area': area.pk if area else None,
        'area_nombre': area.nombre if area else '',
    }
    if unidad is not None and puede_operar_modulo_unidad(usuario, unidad, 'recursos'):
        fecha, valor = fecha_de(bien.get('fecha_ingreso', '')), valor_de(bien.get('valor_contable', ''))
        datos.update({
            'custodio': bien.get('custodio', ''),
            'ubicacion_bodega': bien.get('ubicacion_bodega', ''),
            'fecha_ingreso_bodega': fecha.isoformat() if fecha else '',
            'valor_contable': f'{valor:.2f}' if valor is not None else '',
        })
    return datos


def sugerencias(unidad, nombre, marca='', modelo='', codigo=''):
    """Solo lo relacionado con el equipo leído, para no recorrer todo el inventario.

    Con el nombre (y la marca o el modelo, si se conocen) se calcula el parecido con cada modelo del
    catálogo que tiene equipos activos: las tecnologías que se excluyen (resina y filamento, fibra y CO2…)
    no se mezclan, y los modelos de la misma familia de producto suben. De ahí salen los equipos de la
    unidad que aún no tienen código, los modelos ya existentes (con dónde están) y las áreas donde la
    unidad tiene equipos parecidos.
    """
    buscadas, extra = palabras(nombre), palabras(f'{marca} {modelo}')
    tipos = list(EquiposServicios.objects.filter(unidades__activa=True, unidades__laboratorio__activo=True)
                 .distinct().select_related('familia'))
    puntajes, compartidas, cercanos, excluidos = {}, {}, set(), set()
    principal = nucleo(nombre)
    for tipo in tipos if buscadas else []:
        nombre_tipo = palabras(tipo.nombre)
        if se_excluyen(buscadas, nombre_tipo):
            excluidos.add(tipo.pk)
            continue
        # El parecido de los nombres y cuánto de lo buscado está en el modelo: «visor» abarca todos los
        # visores, pero «impresora 3D de resina» ya no trae las impresoras de etiquetas.
        parecido = semejanza(buscadas, nombre_tipo, extra, palabras(f'{tipo.marca or ""} {tipo.modelo or ""}'))
        puntaje = (parecido + len(buscadas & nombre_tipo) / len(buscadas)) / 2
        if puntaje:
            puntajes[tipo.pk], compartidas[tipo.pk] = puntaje, len(buscadas & nombre_tipo)
        # Cuenta como el mismo equipo si nombra la misma cosa (impresora, láser, visor…) o casi todo coincide:
        # una palabra suelta en común («fibra») no vuelve parientes a un láser y a un micrófono.
        if nucleo(tipo.nombre) == principal or parecido >= 0.5:
            cercanos.add(tipo.pk)
    # La familia: la del nombre conocido o, si no, la del modelo más parecido con al menos dos palabras en común.
    familia = FamiliaEquipo.objects.filter(nombre=familia_de(nombre)).first() if buscadas else None
    if familia is None and puntajes:
        mejor = max(puntajes, key=lambda pk: (compartidas[pk], puntajes[pk]))
        candidato = next(tipo for tipo in tipos if tipo.pk == mejor)
        if compartidas[mejor] >= 2 and puntajes[mejor] >= 0.34 and candidato.familia_id:
            familia = candidato.familia
    if familia is not None:
        for tipo in tipos:
            if tipo.familia_id == familia.pk and tipo.pk not in excluidos:
                puntajes[tipo.pk] = puntajes.get(tipo.pk, 0) + 0.4
                cercanos.add(tipo.pk)
    relacionados = {pk: puntaje for pk, puntaje in puntajes.items() if puntaje >= PARECIDO_MINIMO and pk in cercanos}

    de_la_unidad = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True).distinct()
    sin_codigo = sorted(
        de_la_unidad.filter(codigo_bien__isnull=True, equipo_id__in=relacionados)
        .select_related('equipo').prefetch_related('espacios_asociados'),
        key=lambda equipo: (-relacionados[equipo.equipo_id], equipo.codigo_unidad))[:12]
    presencia = {}
    for fila in (UnidadEquipo.objects.filter(activa=True, laboratorio__activo=True, equipo_id__in=relacionados)
                 .values('equipo_id', 'laboratorio_id', 'laboratorio__nombre').annotate(total=Count('pk'))
                 .order_by('-total')):
        presencia.setdefault(fila['equipo_id'], []).append(
            {'unidad': fila['laboratorio__nombre'], 'total': fila['total'], 'esta': fila['laboratorio_id'] == unidad.pk})
    en_la_unidad = set(de_la_unidad.filter(equipo_id__in=relacionados).values_list('equipo_id', flat=True))
    modelos = sorted((tipo for tipo in tipos if tipo.pk in relacionados),
                     key=lambda tipo: (-(relacionados[tipo.pk] + (0.2 if tipo.pk in en_la_unidad else 0)), tipo.nombre))[:8]
    por_area = {}
    for espacio_id in (EspacioReservable.equipos_asociados.through.objects
                       .filter(espacioreservable__unidad=unidad, unidadequipo__equipo_id__in=relacionados)
                       .values_list('espacioreservable_id', flat=True)):
        por_area[espacio_id] = por_area.get(espacio_id, 0) + 1
    areas = sorted(EspacioReservable.objects.filter(unidad=unidad, activo=True),
                   key=lambda area: (-por_area.get(area.pk, 0), area.orden, area.nombre))
    return {
        'familia': {'id': familia.pk, 'nombre': familia.nombre} if familia else None,
        'equipos': [{'id': equipo.pk, 'codigo': equipo.codigo_unidad, 'nombre': equipo.equipo.nombre,
                     'area': ', '.join(espacio.nombre for espacio in equipo.espacios_asociados.all())}
                    for equipo in sin_codigo],
        'modelos': [{'id': tipo.pk, 'codigo': tipo.codigo, 'nombre': tipo.nombre,
                     'marca_modelo': ' '.join(filter(None, (tipo.marca, tipo.modelo))),
                     'familia': tipo.familia.nombre if tipo.familia_id else '', 'imagen': imagen_de(tipo)[0],
                     'icono': tipo.icono or 'fas fa-cogs', 'en_la_unidad': tipo.pk in en_la_unidad,
                     'presencia': presencia.get(tipo.pk, [])} for tipo in modelos],
        'areas': [{'id': area.pk, 'nombre': area.nombre, 'sugerida': bool(por_area.get(area.pk))} for area in areas],
    }


def _fecha(valor):
    """Una fecha o un momento (en hora local) como día/mes/año."""
    if not valor:
        return ''
    if getattr(valor, 'tzinfo', None) is not None:
        valor = timezone.localtime(valor)
    return valor.strftime('%d/%m/%Y')


def _resumen(equipo):
    """Un equipo emparentado, en una línea: para ubicarlo y abrirlo en el lector."""
    return {
        'codigo': equipo.codigo_unidad,
        'codigo_bien': equipo.codigo_bien or '',
        'nombre': equipo.equipo.nombre,
        'unidad': equipo.laboratorio.nombre if equipo.laboratorio_id else '',
        'area': ', '.join(espacio.nombre for espacio in equipo.espacios_asociados.all()) or equipo.ubicacion_especifica or '',
        'estado': equipo.get_estado_unidad_display(),
        'disponible': equipo.estado_unidad == 'disponible',
    }


def parentela(usuario, equipo):
    """Los equipos emparentados, para saber cuántos hay y dónde están.

    Hermanos: el mismo modelo en la misma unidad. Mismo modelo: en otras unidades. Familia: equipos
    equivalentes de otros modelos (la familia de producto), con el total por unidad. Solo lo activo.
    """
    tipo = equipo.equipo
    activos = (UnidadEquipo.objects.filter(activa=True, fecha_baja__isnull=True, laboratorio__activo=True)
               .select_related('equipo', 'laboratorio').prefetch_related('espacios_asociados'))
    otros = activos.exclude(pk=equipo.pk)
    datos = {
        'hermanos': [_resumen(item) for item in
                     otros.filter(equipo=tipo, laboratorio_id=equipo.laboratorio_id).order_by('codigo_unidad')[:40]],
        'mismo_modelo': [_resumen(item) for item in
                         otros.filter(equipo=tipo).exclude(laboratorio_id=equipo.laboratorio_id)
                         .order_by('laboratorio__nombre', 'codigo_unidad')[:40]],
        'familia': None,
    }
    if tipo.familia_id:
        de_la_familia = activos.filter(equipo__familia_id=tipo.familia_id)
        por_unidad = (de_la_familia.values('laboratorio_id', 'laboratorio__nombre')
                      .annotate(total=Count('pk'), disponibles=Count('pk', filter=Q(estado_unidad='disponible')))
                      .order_by('-total', 'laboratorio__nombre'))
        parientes = sorted(de_la_familia.exclude(equipo=tipo)[:80],
                           key=lambda item: (item.laboratorio_id != equipo.laboratorio_id, item.laboratorio.nombre,
                                             item.equipo.nombre, item.codigo_unidad))
        datos['familia'] = {
            'nombre': tipo.familia.nombre,
            'total': sum(fila['total'] for fila in por_unidad),
            'unidades': [{'unidad': fila['laboratorio__nombre'], 'total': fila['total'], 'disponibles': fila['disponibles'],
                          'esta': fila['laboratorio_id'] == equipo.laboratorio_id} for fila in por_unidad],
            'parientes': [_resumen(item) for item in parientes],
            'url': (reverse('familia_equipo_institucional', args=[tipo.familia.slug])
                    if usuario.has_perm('recursos.view_unidadequipo') else ''),
        }
    return datos


def recorrido_de(equipo):
    """Por qué unidades ha pasado el equipo: la del registro y cada transferencia, en orden."""
    paradas = []
    for evento in (EventoCicloVidaEquipo.objects.filter(equipo=equipo, tipo__in=('registro', 'transferencia'))
                   .select_related('unidad').order_by('fecha')):
        nombre = evento.unidad.nombre if evento.unidad_id else 'Sin unidad'
        if not paradas or paradas[-1]['unidad'] != nombre:
            paradas.append({'unidad': nombre, 'desde': _fecha(evento.fecha),
                            'como': 'Registro' if evento.tipo == 'registro' else 'Transferencia'})
    return paradas


def datos_del_equipo(request, equipo):
    """La tarjeta del lector: identificación, situación, origen, mantenimiento, parentela e historia."""
    unidad = equipo.laboratorio
    gestor = ve_datos_patrimoniales(request.user, equipo)
    opera_recursos = bool(unidad) and puede_operar_modulo_unidad(request.user, unidad, 'recursos')
    ficha = ficha_equipo(equipo)
    tipo = equipo.equipo
    vida = ficha['vida']
    contenido = ficha['contenido']
    prestamo = (PrestamoEquipo.objects.filter(equipo=equipo, estado__in=PrestamoEquipo.ESTADOS_FUERA)
                .order_by('-fecha_salida').first())
    return {
        'encontrado': True,
        'codigo_sistema': equipo.codigo_unidad,
        'codigo_bien': equipo.codigo_bien or '',
        'etiqueta': etiqueta_de(equipo),
        'tipo_bien': equipo.get_tipo_bien_display() if equipo.tipo_bien else '',
        'clase_bien': equipo.clase_bien,
        'codigos_anteriores': list(equipo.codigos_anteriores.values_list('codigo', flat=True)),
        'nombre': tipo.nombre,
        'modelo_codigo': tipo.codigo,
        # «Otros equipos» es lo que se deduce cuando nada clasifica al equipo: no lo describe.
        'categoria': '' if contenido['categoria'] == 'Otros equipos' else contenido['categoria'],
        'familia_nombre': tipo.familia.nombre if tipo.familia_id else '',
        'marca_modelo': ' '.join(filter(None, (tipo.marca, tipo.modelo))),
        'serie': equipo.numero_serie or '',
        'imagen': imagen_de(tipo)[0],
        'icono': tipo.icono or 'fas fa-cogs',
        'unidad': unidad.nombre if unidad else '',
        'areas': [espacio.nombre for espacio in contenido['espacios']],
        'ubicacion': equipo.ubicacion_especifica or '',
        'estado': equipo.get_estado_unidad_display(),
        'activa': equipo.activa,
        'criticidad': equipo.get_criticidad_display() if equipo.criticidad else '',
        'semaforo': ficha['semaforo'],
        'semaforo_texto': ficha['etiqueta'],
        'motivos': ficha['motivos'],
        'origen': {
            'adquisicion': equipo.get_origen_adquisicion_display() if equipo.origen_adquisicion else '',
            'fecha_adquisicion': _fecha(equipo.fecha_adquisicion),
            'fecha_ingreso_bodega': _fecha(equipo.fecha_ingreso_bodega),
            'documento': equipo.documento_adquisicion if gestor else '',
        },
        'recorrido': recorrido_de(equipo),
        'garantia': _fecha(ficha['garantia']['fin']) if ficha['garantia']['vigente'] else '',
        'ultimo_mantenimiento': _fecha(equipo.fecha_ultimo_mantenimiento),
        'proximo_mantenimiento': _fecha(ficha['proximo']),
        'mantenimientos': [{'fecha': _fecha(item['orden'].fecha_fin or item['orden'].fecha_programada),
                            'titulo': f"{item['orden'].get_tipo_display()}: {item['orden'].titulo}",
                            'estado': item['orden'].get_estado_display()} for item in ficha['fichas'][:6]],
        'incidencias_abiertas': ficha['incidencias_abiertas'],
        'incidencias': [{'fecha': _fecha(incidencia.fecha_reporte), 'titulo': incidencia.titulo,
                         'estado': incidencia.get_estado_display()}
                        for incidencia in ficha['incidencias'] if incidencia.estado not in incidencia.ESTADOS_CERRADOS],
        'prestamo': {'devuelve': _fecha(prestamo.fecha_retorno_previsto), 'vencido': prestamo.vencido,
                     'tipo': prestamo.get_tipo_display()} if prestamo else None,
        'horas_de_uso': float(ficha['uso']['horas_acumuladas'] or 0),
        'sesiones': ficha['uso']['sesiones'],
        'vida_consumida': vida['consumida'],
        'requiere_cambio': bool(vida['cumplida']),
        'vida_alerta': bool(vida['alerta']),
        'vida_texto': vida['motivo_texto'],
        'software': [programa.nombre for programa in contenido['software']],
        'insumos': [insumo.nombre for insumo in contenido['insumos']],
        'custodio': equipo.custodio if gestor else '',
        'ubicacion_bodega': equipo.ubicacion_bodega if gestor else '',
        'valor_contable': f'{equipo.valor_contable:.2f}' if gestor and equipo.valor_contable else '',
        'historia': [{'fecha': _fecha(hito['fecha']), 'titulo': hito['titulo'], 'detalle': hito['detalle']}
                     for hito in linea_de_trazabilidad(equipo, limite=40)
                     if gestor or hito.get('tipo') not in HITOS_PATRIMONIALES],
        'parentela': parentela(request.user, equipo),
        'ficha_url': reverse('ficha_equipo_publica', args=[unidad.slug, equipo.codigo_unidad]) if unidad else '',
        'ficha_interna_url': reverse('ficha_equipo_unidad', args=[unidad.slug, equipo.pk]) if gestor else '',
        'etiqueta_url': f"{reverse('etiquetas_equipos', args=[unidad.slug])}?equipo={equipo.pk}" if gestor else '',
        'editar_url': gestion_de_activos(unidad, editar_equipo=equipo.pk) if opera_recursos else '',
    }


@login_required
def lector_equipos_view(request):
    if not puede_usar_lector(request.user):
        raise PermissionDenied('El lector de equipos es para el personal de las unidades.')
    unidades = _unidades_que_registra(request.user)
    # Abierto desde la gestión de una unidad: esa queda elegida y la cabecera lleva de vuelta a ella.
    actual = next((unidad for unidad in unidades if unidad.slug == request.GET.get('unidad')), None)
    return render(request, 'portal/pages/unidades/lector/lector.html', {
        'page_key': 'lector-equipos',
        'page_title': 'Lector de equipos',
        'unidad_actual': actual,
        'volver_url': gestion_de_activos(actual) if actual else '',
        'puede_ver_tablero': request.user.has_perm('recursos.view_unidadequipo'),
        'unidades': [{'slug': unidad.slug, 'nombre': unidad.nombre, 'gestion': gestion_de_activos(unidad)}
                     for unidad in unidades],
        'tipos_bien': UnidadEquipo.TIPOS_BIEN,
        'prefijo': PREFIJO_INSTITUCIONAL,
        'zxing': static('js/vendor/zxing-library-0.21.3.min.js'),
    })


@login_required
@require_GET
def buscar_equipo_api(request):
    """?codigo=<lectura> → el equipo; si es nuevo, lo que bodega dice de él y el código del sistema sugerido."""
    if not puede_usar_lector(request.user):
        return JsonResponse({'error': 'El lector de equipos es para el personal de las unidades.'}, status=403)
    from apps.gestion_unidades.presentation.gobierno_editorial import objeto_visible_para

    codigo = codigo_leido(request.GET.get('codigo', ''))
    equipo = buscar_equipo(codigo)
    # Lo retirado o no publicado solo lo ve quien gestiona la unidad del equipo.
    if equipo is not None and not ve_datos_patrimoniales(request.user, equipo) and (
            not equipo.activa or not equipo.laboratorio_id
            or not objeto_visible_para(equipo, equipo.laboratorio, request.user)):
        equipo = None
    if equipo is None:
        # Solo un código de bodega (numérico) se registra; el del sistema se asigna con el estándar al guardar.
        valido = codigo.isdigit()
        return JsonResponse({'encontrado': False, 'codigo': codigo, 'valido': valido,
                             'bodega': datos_de_bodega(request.user, codigo) if valido else None})
    return JsonResponse(datos_del_equipo(request, equipo))


@login_required
@require_GET
def sugerencias_api(request):
    """?unidad=<slug>&nombre=<qué equipo es>[&marca=&modelo=&codigo=] → solo lo relacionado con ese equipo."""
    unidad = Unidad.objects.filter(slug=request.GET.get('unidad', ''), activo=True).first()
    if unidad is None or not puede_operar_modulo_unidad(request.user, unidad, 'recursos'):
        return JsonResponse({'error': 'No gestionas los recursos de esa unidad.'}, status=403)
    texto = {clave: (request.GET.get(clave) or '').strip()[:120] for clave in ('nombre', 'marca', 'modelo', 'codigo')}
    return JsonResponse(sugerencias(unidad, texto['nombre'], texto['marca'], texto['modelo'],
                                    texto['codigo'] if texto['codigo'].isdigit() else ''))


@login_required
@require_POST
def registrar_equipo_api(request):
    """Asigna el código leído a un equipo de la unidad que aún no lo tenía.

    Un equipo nuevo no se registra aquí: el lector abre el alta completa de la gestión de la unidad.
    """
    try:
        datos = json.loads(request.body or '{}')
    except ValueError:
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)
    if not isinstance(datos, dict):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    def texto(clave, largo):
        return str(datos.get(clave) or '').strip()[:largo]

    codigo = codigo_leido(texto('codigo', 60))
    if not codigo:
        return JsonResponse({'error': 'Falta el código leído.'}, status=400)
    if len(codigo) > UnidadEquipo._meta.get_field('codigo_bien').max_length:
        return JsonResponse({'error': 'El código leído es demasiado largo para un código de bien.'}, status=400)
    if buscar_equipo(codigo) is not None:
        return JsonResponse({'error': 'Ese código ya pertenece a un equipo registrado.'}, status=409)
    if not codigo.isdigit():
        return JsonResponse({'error': f'La etiqueta no tiene el formato de bodega ({PREFIJO_INSTITUCIONAL}-número del bien).'},
                            status=400)
    if not texto('equipo_id', 12).isdigit():
        return JsonResponse({'error': 'Elige el equipo al que pertenece la etiqueta.'}, status=400)
    try:
        with transaction.atomic():
            equipo = UnidadEquipo.objects.select_related('laboratorio').filter(
                pk=int(texto('equipo_id', 12)), codigo_bien__isnull=True, laboratorio__isnull=False).first()
            if equipo is None or not puede_operar_modulo_unidad(request.user, equipo.laboratorio, 'recursos'):
                return JsonResponse({'error': 'No puedes asignar códigos a ese equipo.'}, status=403)
            equipo.codigo_bien = codigo
            if texto('serie', 100) and not equipo.numero_serie:
                equipo.numero_serie = texto('serie', 100)
            for campo, largo in (('clase_bien', 160), ('custodio', 160)):
                if texto(campo, largo):
                    setattr(equipo, campo, texto(campo, largo))
            if texto('tipo_bien', 3) in dict(UnidadEquipo.TIPOS_BIEN):
                equipo.tipo_bien = texto('tipo_bien', 3)
            equipo.save()
    except IntegrityError:
        return JsonResponse({'error': 'Ese código ya está en uso.'}, status=409)
    except ValidationError as error:
        return JsonResponse({'error': '; '.join(error.messages)}, status=400)
    return JsonResponse(datos_del_equipo(request, equipo))
