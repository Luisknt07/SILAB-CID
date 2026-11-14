"""Tipo de adjunto: se deduce del archivo cuando el editor lo deja en «Automático»."""
import zipfile
from pathlib import Path

from apps.recursos.models.recursos import TIPOS_ADJUNTO

MULTIMEDIA = {'.html', '.htm', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.mp4', '.webm', '.mov', '.glb', '.gltf'}
DATOS = {'.xls', '.xlsx', '.ods', '.csv', '.tsv', '.json', '.xml', '.ipynb'}
PLANOS = {'.dwg', '.dxf', '.step', '.stp', '.iges', '.igs', '.obj', '.stl'}
# Archivos que delatan el reproductor de un recorrido 360° exportado.
MARCAS_360 = ('pano2vr_player.js', 'krpano.js', 'tour.xml', 'marzipano.js', 'pannellum.js', 'tdvplayer')

# Grupos del selector: primero lo que se publica en el visor; al final lo que genera el sistema.
GRUPOS = (
    ('Contenido para el visor', ('multimedia', 'recorrido_360', 'publicacion', 'artefacto', 'microproyecto_django')),
    ('Documentos técnicos', ('manual', 'ficha_tecnica', 'plano', 'hoja_seguridad', 'norma', 'plantilla')),
    ('Datos', ('dataset',)),
    ('Registros de calidad', ('informe', 'certificado', 'evidencia')),
)


def opciones_agrupadas():
    etiquetas = dict(TIPOS_ADJUNTO)
    return [('', 'Automático (según el archivo)'),
            *((grupo, [(clave, etiquetas[clave]) for clave in claves]) for grupo, claves in GRUPOS)]


def nombres_del_zip(archivo):
    """Rutas del ZIP, sin consumir el archivo que guardará Django."""
    posicion = archivo.tell()
    try:
        with zipfile.ZipFile(archivo) as paquete:
            return paquete.namelist()
    finally:
        archivo.seek(posicion)


def entrada_360(nombres):
    """El index.html que abre el recorrido: en la raíz o dentro de la única carpeta del ZIP.

    Comprimir la carpeta que exporta el programa deja todo dentro de ella; ese
    ZIP también vale. Sin entrada, devuelve ''.
    """
    utiles = [nombre for nombre in nombres if not nombre.startswith('__MACOSX/')]
    carpetas = {nombre.split('/', 1)[0] for nombre in utiles}
    candidatas = ['index.html'] + ([f'{carpetas.pop()}/index.html'] if len(carpetas) == 1 else [])
    for candidata in candidatas:
        for nombre in utiles:
            if nombre.lower() == candidata.lower():
                return nombre
    return ''


def es_recorrido_360(archivo):
    nombres = nombres_del_zip(archivo)
    return bool(entrada_360(nombres)) and any(marca in nombre.lower() for nombre in nombres for marca in MARCAS_360)


def inferir(archivo, url=''):
    """Microproyecto si el ZIP trae Django, recorrido si trae un reproductor 360°; si no, según la extensión."""
    if not archivo:
        return 'publicacion' if url else 'informe'
    extension = Path(archivo.name).suffix.lower()
    if extension == '.zip':
        from apps.recursos.presentation.microproyectos import contiene_django
        try:
            if contiene_django(archivo):
                return 'microproyecto_django'
            return 'recorrido_360' if es_recorrido_360(archivo) else 'multimedia'
        except Exception:  # noqa: BLE001 - un ZIP ilegible lo rechaza la validación del archivo.
            return 'multimedia'
    if extension in MULTIMEDIA:
        return 'multimedia'
    if extension in DATOS:
        return 'dataset'
    if extension in PLANOS:
        return 'plano'
    return 'informe'
