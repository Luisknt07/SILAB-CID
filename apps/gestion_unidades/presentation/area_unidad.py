"""Cada área de la unidad en su propia página, con el diseño de «Ficha de la unidad».

Se abre desde el menú «Contenidos» de la ficha, un botón por área. Reúne dos cosas:

- Lo que el área tiene registrado: cómo se reserva, quién la atiende, sus equipos con su ficha
  técnica, el software que corre en ellos, sus recursos en línea y los procesos que pasan por ella.
- Su ficha explicativa: qué es la tecnología, cómo funciona, qué se puede hacer, el equipamiento
  y el software que necesita, la documentación, las conexiones y la seguridad. El público la ve
  cuando la unidad la publica; antes, solo quien gestiona la unidad, como borrador.
"""
from collections import OrderedDict
from copy import copy

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.edicion_area import puede_editar_area
from apps.formacion.presentation.aula import areas_y_equipos
from apps.gestion_unidades.presentation.fusion_areas import area_vigente
from apps.recursos.presentation.ficha_equipo import ESPACIOS_DE_ADMINISTRACION
from apps.recursos.models.consumibles import ConsumiblePorEquipo
from apps.gestion_unidades.presentation.ficha_unidad import enlace_telefonico, iniciales
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.gestion_unidades.presentation.gobierno_editorial import visibles_para
from apps.gestion_unidades.presentation.plantillas_ficha import pares_de
from apps.laboratorios.operacion.presentation.procesos_laboratorio import resumen_de


def persona_de(responsable):
    """El responsable del área con los mismos datos que muestra «Quién la atiende» en la ficha."""
    if responsable is None:
        return None
    return {
        'nombre': responsable.nombre_publico,
        'rol': responsable.get_rol_display(),
        'descripcion': responsable.descripcion,
        'email': responsable.email_publico,
        'telefono': responsable.telefono_publico,
        'enlace_telefono': enlace_telefonico(responsable.telefono_publico) if responsable.telefono_publico else '',
        'horario': responsable.horario_atencion,
        'foto': responsable.foto_publica_url,
        'iniciales': iniciales(responsable.nombre_publico),
    }


def lineas(texto):
    """Un texto escrito en renglones, como lista; vacío si no hay nada."""
    return [renglon.strip(' -•\t') for renglon in (texto or '').splitlines() if renglon.strip(' -•\t')]


def antetitulo_de(unidad):
    return 'Área del laboratorio' if unidad.dependencia == 'laboratorios' else 'Área de la unidad'


def equipos_de_ficha(elementos, inventario, zonas, unidad_id=None):
    """Un modelo por ficha, sin convertir cantidades propuestas en activos.

    Los puestos que describen el mismo modelo conservan sus identificadores y zonas.
    El inventario recibido ya está limitado al área y a la visibilidad del usuario.
    Ningún vínculo o descripción se modifica en la base de datos.
    """
    por_modelo = {}
    for fisica in inventario:
        por_modelo.setdefault(fisica.equipo_id, OrderedDict())[fisica.pk] = fisica
    grupos = OrderedDict()
    for elemento in elementos:
        if elemento.tipo != 'equipo':
            continue
        adquirido = bool(elemento.registrado_id and not elemento.solo_referencia)
        clave = (elemento.ficha_id, elemento.registrado.equipo_id) if adquirido else ('referencia', elemento.pk)
        if clave not in grupos:
            equipo = copy(elemento)
            equipo.modelo_registrado = adquirido
            equipo.elementos_origen = []
            equipo.zonas = []
            equipo.unidades = list(por_modelo.get(elemento.registrado.equipo_id, {}).values()) if adquirido else []
            equipo.disponibles = sum(fisica.estado_unidad == 'disponible' for fisica in equipo.unidades)
            equipo.especificaciones_mostradas = elemento.lista_especificaciones
            equipo.consumibles_mostrados = elemento.lista_consumibles
            equipo.cuidados_mostrados = elemento.lista_cuidados
            equipo.modelo_mostrado = elemento.ejemplo
            if adquirido:
                tipo = elemento.registrado.equipo
                equipo.nombre = tipo.nombre
                equipo.modelo_mostrado = ' · '.join(valor for valor in (tipo.marca, tipo.modelo) if valor)
                equipo.para_que = tipo.uso_publico or elemento.para_que
                # Las características del modelo real prevalecen sobre ejemplos de otra marca.
                pares, prosa = pares_de(tipo.caracteristicas_publicas)
                especificaciones = OrderedDict(pares)
                especificaciones.update((str(k), str(v)) for k, v in (tipo.especificaciones or {}).items() if v not in ('', None))
                equipo.especificaciones_mostradas = list(especificaciones.items())
                equipo.caracteristicas_mostradas = prosa
                equipo.consumibles_mostrados = list(dict.fromkeys(
                    vinculo.consumible.nombre for vinculo in getattr(tipo, 'consumibles_del_area', ())
                    if vinculo.consumible.unidad_id == unidad_id))
                equipo.cuidados_mostrados = lineas(tipo.instrucciones_publicas)
            grupos[clave] = equipo
        equipo = grupos[clave]
        equipo.elementos_origen.append({'id': elemento.pk, 'nombre': elemento.nombre})
        equipo.zonas = sorted(set(equipo.zonas) | {
            indice for indice, zona in enumerate(zonas) if elemento.nombre in zona['equipos']})
    return sorted(grupos.values(), key=lambda equipo: (equipo.nivel == 'alta', equipo.orden))


def ficha_de(espacio, gestor, inventario=(), usuario=None):
    """La ficha explicativa del área con sus elementos agrupados, o None si no se puede mostrar.

    Cada equipo de la ficha lleva sus unidades del inventario del área (código, estado y ubicación),
    y cada insumo y programa su registro, para que la página diga lo mismo que gestión y reservas.
    """
    try:
        ficha = espacio.ficha
    except ObjectDoesNotExist:
        return None
    if not ficha.publicada and not gestor:
        return None
    originales = list(ficha.elementos.select_related(
        'registrado__equipo', 'insumo_registrado', 'software_registrado',
    ).prefetch_related(Prefetch(
        'registrado__equipo__consumibles',
        queryset=ConsumiblePorEquipo.objects.filter(
            consumible__unidad_id=espacio.unidad_id,
        ).select_related('consumible'),
        to_attr='consumibles_del_area',
    )))
    elementos = visibles_para(originales, espacio.unidad, usuario)
    ids_visibles = {elemento.pk for elemento in elementos}
    ocultos = {elemento.nombre for elemento in originales if elemento.pk not in ids_visibles}
    zonas = ficha.zonas
    for zona in zonas:
        zona['equipos'] = [nombre for nombre in zona['equipos'] if nombre not in ocultos]
    equipos = equipos_de_ficha(elementos, inventario, zonas, espacio.unidad_id)
    return {
        'ficha': ficha,
        'pasos': ficha.pasos,
        'zonas': zonas,
        'equipos': equipos,
        'total_equipos': len(equipos),
        'insumos': [elemento for elemento in elementos if elemento.tipo == 'insumo'],
        'imagenes': [elemento for elemento in elementos if elemento.tipo == 'imagen' and elemento.imagen_url],
        'videos': [elemento for elemento in elementos if elemento.tipo == 'video' and elemento.youtube_id],
        'software': [elemento for elemento in elementos if elemento.tipo == 'software'],
        'documentos': [elemento for elemento in elementos if elemento.tipo == 'documento'],
    }


def medios_de(espacio, contenido):
    """La galería y los videos del área: primero lo que la unidad subió, después lo referencial; los videos
    propios, si los hay, reemplazan a los de referencia.

    Cada imagen dice si es propia o referencial, para rotularla; la portada es la primera.
    """
    medios = list(espacio.medios_interiores.filter(publicado=True).order_by('orden', 'pk'))
    galeria = [{'url': espacio.imagen_propia_url, 'titulo': espacio.nombre, 'descripcion': '', 'referencial': False}
               ] if espacio.imagen else []
    galeria += [{'url': medio.imagen.url, 'titulo': medio.titulo, 'descripcion': medio.descripcion,
                 'referencial': medio.es_referencial}
                for medio in medios if medio.tipo == 'foto' and medio.imagen]
    videos = [{'id': medio.youtube_id, 'titulo': medio.titulo, 'canal': '', 'descripcion': medio.descripcion, 'propio': True}
              for medio in medios if medio.tipo == 'video' and medio.youtube_id]
    if contenido:
        galeria += [{'url': imagen.imagen_url, 'titulo': imagen.nombre, 'descripcion': imagen.para_que,
                     'referencial': imagen.es_referencial, 'credito': imagen.ejemplo, 'fuente': imagen.url} for imagen in contenido['imagenes']]
        # Los videos que la unidad guardó reemplazan a los de referencia.
        videos = videos or [{'id': video.youtube_id, 'titulo': video.nombre, 'canal': video.ejemplo,
                             'descripcion': video.para_que, 'propio': False} for video in contenido['videos']]
    # Una misma imagen de referencia llega por dos caminos (la copia del interior y la ficha) y, tras
    # fusionar áreas, repetida: se muestra una sola vez. Las fotos propias nunca se descartan.
    vistas, sin_repetir = set(), []
    for imagen in galeria:
        clave = (imagen['url'],) if not imagen['referencial'] else ('referencial', imagen['titulo'].strip().casefold())
        if clave in vistas:
            continue
        vistas.add(clave)
        sin_repetir.append(imagen)
    galeria = sin_repetir
    return {'galeria': galeria, 'videos': videos, 'portada': galeria[0] if galeria else None,
            'franja': galeria[1] if len(galeria) > 1 else (galeria[0] if galeria else None)}


def procesos_del_area(unidad, espacio, gestor):
    """Los procesos que tienen alguna etapa en el área; con borradores para quien la gestiona."""
    procesos = Receta.objects.filter(unidad=unidad, etapas__espacio=espacio).distinct().select_related('producto')
    if not gestor:
        procesos = procesos.filter(activa=True)
    # Una planta tiene su propia ficha de proceso, con balances y control; un laboratorio, el paso a paso.
    ruta = 'ficha_proceso_publica' if unidad.dependencia == 'plantas_piloto' else 'proceso_laboratorio'
    return [{'proceso': proceso, 'resumen': resumen_de(proceso), 'url': reverse(ruta, args=[unidad.slug, proceso.pk]),
             'etapas': [etapa for etapa in proceso.etapas.all() if etapa.espacio_id == espacio.pk]}
            for proceso in procesos.prefetch_related('etapas').order_by('nombre')]


def revisar_ficha(unidad, ficha):
    """La ficha en la sección del tipo de la unidad, donde la edita su administrador."""
    espacio = ESPACIOS_DE_ADMINISTRACION.get(unidad.dependencia, 'gestion_unidades')
    return reverse(f'admin:{espacio}_fichaarea_change', args=[ficha.pk])


@xframe_options_sameorigin
def area_unidad_view(request, slug, codigo):
    """La página de un área: qué es, qué se hace, con qué, cómo se reserva y quién la atiende."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    infraestructura = areas_y_equipos(unidad, request.user)
    area = next((area for area in infraestructura['areas'] if area['espacio'].codigo == codigo), None)
    if area is None:
        # Un área que se fusionó lleva a la que la recibió: los enlaces viejos siguen funcionando.
        integrada = EspacioReservable.objects.filter(unidad=unidad, codigo=codigo, integrada_en__isnull=False).first()
        vigente = area_vigente(integrada) if integrada else None
        if vigente is not None and vigente.activo:
            return redirect('area_unidad', slug=unidad.slug, codigo=vigente.codigo)
        raise Http404('El área no existe o no está activa')
    espacio = area['espacio']
    gestor = puede_gestionar_unidad(request.user, unidad)
    contenido = ficha_de(espacio, gestor, area['equipos'], request.user)
    descritos = {elemento.registrado.equipo_id for elemento in contenido['equipos']
                 if elemento.modelo_registrado} if contenido else set()
    return render(request, 'portal/pages/unidades/detalle/area_unidad.html', {
        'unidad': unidad,
        'area': area,
        'contenido': contenido,
        'medios': medios_de(espacio, contenido),
        'cifra_equipos': len(area['equipos']) or (contenido['total_equipos'] if contenido else 0),
        'solo_fichas_equipamiento': not area['equipos'] and bool(contenido),
        'aforo_pendiente': not espacio.reservable and 'Aforo y capacidad técnica pendientes de levantamiento.' in espacio.caracteristicas,
        # Los equipos registrados que la ficha no describe siguen a la vista, aparte.
        'otros_registrados': [equipo for equipo in area['equipos'] if equipo.equipo_id not in descritos],
        'procesos': procesos_del_area(unidad, espacio, gestor),
        'antetitulo': antetitulo_de(unidad),
        'persona': persona_de(area['responsable']),
        'caracteristicas': lineas(espacio.caracteristicas),
        'mobiliario': lineas(espacio.mobiliario_incluido),
        'otras_areas': [otra for otra in infraestructura['areas'] if otra is not area],
        'todas_url': reverse('areas_equipos', args=[unidad.slug]),
        'editar_url': reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]) if gestor else '',
        # Editar el área desde su propia página (dentro del visualizador), por secciones.
        'editar_area_url': reverse('editar_area', args=[unidad.slug, espacio.codigo]) if puede_editar_area(request.user, unidad) else '',
        'revisar_ficha_url': revisar_ficha(unidad, contenido['ficha'])
        if contenido and not contenido['ficha'].publicada else '',
    })
