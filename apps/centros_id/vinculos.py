"""Las unidades del directorio con las que se articula un centro, nombradas por su identificador público.

El directorio de unidades es una integración opcional: si la configuración declara su proveedor, cada unidad se
resuelve con su contrato de identidad (nombre, tipo) y se enlaza a su ficha; si no, o si la unidad ya no existe, no
se enlaza. El centro nunca guarda una clave foránea hacia la tabla de unidades ni importa el directorio.
"""
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils.module_loading import import_string

# El único proveedor que el centro acepta para nombrar unidades: el contrato de identidad del directorio.
PROVEEDOR_UNIDADES = 'apps.directorio_unidades.selectors.obtener_identidad_publica'
# Y el único que acepta para dibujar las sedes de la institución (punto, contorno y edificios) en su mapa de ubicación.
PROVEEDOR_SEDES = 'apps.directorio_unidades.presentation.ubicacion.sedes_en_el_mapa'

# La ficha pública de cada tipo del contrato, por el nombre de su ruta.
RUTA_POR_TIPO = {
    'laboratorios': 'laboratorio_detalle',
    'plantas_piloto': 'planta_piloto_detalle',
    'centro_experimental': 'centro_experimental_detalle',
    'observatorios': 'observatorio_detalle',
}
TIPO_LEGIBLE = {'laboratorios': 'Laboratorio', 'plantas_piloto': 'Planta piloto',
                'centro_experimental': 'Centro experimental', 'observatorios': 'Observatorio'}


def proveedor_unidades():
    ruta = getattr(settings, 'CENTROS_ID_UNIT_PROVIDER', '')
    if not ruta:
        return None
    if ruta != PROVEEDOR_UNIDADES:
        raise ValueError('El proveedor de unidades de los Centros I+D no está registrado.')
    return import_string(ruta)


def proveedor_sedes():
    ruta = getattr(settings, 'CENTROS_ID_SEDES_PROVIDER', '')
    if not ruta:
        return None
    if ruta != PROVEEDOR_SEDES:
        raise ValueError('El proveedor de sedes de los Centros I+D no está registrado.')
    return import_string(ruta)


def sedes_en_el_mapa():
    """Las sedes de la institución para el mapa del centro (nombre, localidad, dirección, punto, contorno, edificios y
    cómo llegar); sin proveedor, el mapa muestra solo el centro."""
    obtener_sedes = proveedor_sedes()
    return list(obtener_sedes()) if obtener_sedes else []


def unidad_publica(slug):
    """{'nombre', 'tipo', 'url'} de una unidad activa, o None si no existe o el despliegue no declara el directorio."""
    obtener_identidad = proveedor_unidades()
    if not slug or obtener_identidad is None:
        return None
    identidad = obtener_identidad(slug)
    if identidad is None:
        return None
    tipo = identidad.tipo.value
    try:
        url = reverse(RUTA_POR_TIPO[tipo], kwargs={'slug': identidad.slug})
    except (KeyError, NoReverseMatch):
        url = ''
    return {'nombre': identidad.nombre, 'tipo': TIPO_LEGIBLE.get(tipo, ''), 'url': url, 'slug': identidad.slug}


def unidades_de(slugs):
    """Las unidades resueltas, en el orden pedido; las que no existen se omiten."""
    vistas, resultado = set(), []
    for slug in slugs:
        if slug in vistas:
            continue
        vistas.add(slug)
        unidad = unidad_publica(slug)
        if unidad:
            resultado.append(unidad)
    return resultado


def centros_que_integran(slug):
    """Desde la otra punta: los Centros I+D activos que se articulan con una unidad (para su ficha).

    Lo usa el directorio sin conocer los modelos del centro: recibe nombres, enlaces y para qué.
    """
    from .models import Articulacion, Componente

    if not slug:
        return []
    filas = {}
    for articulacion in Articulacion.objects.filter(unidad_slug=slug, centro__activo=True).select_related('centro'):
        filas.setdefault(articulacion.centro_id, {'centro': articulacion.centro, 'forma': articulacion.forma, 'componentes': []})
    for componente in Componente.objects.filter(centro__activo=True, publicado=True,
                                                unidades_articuladas__icontains=slug).select_related('centro'):
        if slug in componente.lista_unidades:
            fila = filas.setdefault(componente.centro_id, {'centro': componente.centro, 'forma': '', 'componentes': []})
            fila['componentes'].append({'nombre': componente.nombre_corto or componente.nombre,
                                        'url': reverse('componente_centro_id', args=[componente.centro.slug, componente.codigo])})
    return [{'nombre': str(fila['centro']), 'url': reverse('centro_id', args=[fila['centro'].slug]),
             'estado': fila['centro'].get_estado_display(), 'forma': fila['forma'], 'componentes': fila['componentes']}
            for fila in filas.values()]


def oferta_vinculada(slugs):
    """Lee oferta pública con el proveedor del directorio; no crea operaciones heredadas."""
    if proveedor_unidades() is None or not slugs:
        return {'unidades': [], 'cursos': []}
    obtener = import_string('apps.directorio_unidades.selectors.oferta_publica_para_centros')
    return obtener(slugs)
