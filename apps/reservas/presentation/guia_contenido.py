"""Contenido enriquecido de la guía FT04: subtítulos, listas, tablas e imágenes.

Mini-lenguaje en texto plano que comparten el asistente (vista previa), la
vista HTML y el PDF:

- ``## Subtítulo``
- ``- viñeta`` / ``1. numerado``
- tabla: líneas que empiezan con ``|``; la primera fila es la cabecera y una
  fila ``|---|---|`` se ignora
- imagen: ``![Figura 1: título](figura:1)`` para una figura cargada en la
  guía, o ``![título](https://...)`` para una imagen externa

En el procedimiento, las tablas e imágenes escritas debajo de un paso quedan
adjuntas a ese paso. Las figuras se guardan en ``ImagenGuiaActividad`` y se
citan por su posición (``figura:N``), de modo que el texto no depende de
rutas de archivo.
"""

import re
from html import escape
from pathlib import Path

from django.db import transaction
from PIL import Image as ImagenPil, UnidentifiedImageError

from apps.reservas.models.reservas import ImagenGuiaActividad

PATRON_IMAGEN = re.compile(r'^!\[(?P<texto>[^\]]*)\]\((?P<fuente>[^)\s]+)\)$')
PATRON_SUBTITULO = re.compile(r'^#{2,3}\s+(.+)$')
PATRON_NUMERADO = re.compile(r'^\d+[.)]\s+(.+)$')
PATRON_VINETA = re.compile(r'^[-*•]\s+(.+)$')
PATRON_PREFIJO_PASO = re.compile(r'^\s*(?:\d+[.)]|[-*•])\s*')
EXTENSIONES_IMAGEN = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
TAMANO_MAXIMO_IMAGEN = 5 * 1024 * 1024
MAXIMO_IMAGENES = 12


def _lineas(valor):
    if isinstance(valor, (list, tuple)):
        return [str(item) for item in valor]
    return str(valor or '').splitlines()


def es_linea_tabla(linea):
    return linea.strip().startswith('|')


def es_separador_tabla(linea):
    texto = linea.strip()
    return bool(re.fullmatch(r'[|\s:\-]+', texto)) and '-' in texto


def celdas_tabla(linea):
    texto = linea.strip()
    if texto.startswith('|'):
        texto = texto[1:]
    if texto.endswith('|'):
        texto = texto[:-1]
    return [celda.strip() for celda in texto.split('|')]


def imagen_de(linea):
    coincidencia = PATRON_IMAGEN.match(linea.strip())
    if not coincidencia:
        return None
    return {
        'tipo': 'imagen',
        'texto': coincidencia.group('texto').strip(),
        'fuente': coincidencia.group('fuente').strip(),
    }


def es_linea_adjunta(linea):
    return es_linea_tabla(linea) or imagen_de(linea) is not None


def bloques_enriquecidos(valor):
    """Texto → bloques ``parrafo``, ``subtitulo``, ``lista``, ``tabla`` e ``imagen``."""
    bloques = []
    parrafo = []
    lista = None
    tabla = None

    def cerrar_parrafo():
        if parrafo:
            bloques.append({'tipo': 'parrafo', 'texto': ' '.join(parrafo)})
            parrafo.clear()

    def cerrar_lista():
        nonlocal lista
        if lista:
            bloques.append(lista)
            lista = None

    def cerrar_tabla():
        nonlocal tabla
        if tabla:
            if tabla['filas']:
                bloques.append(tabla)
            tabla = None

    for bruta in _lineas(valor):
        linea = bruta.strip()
        if not linea:
            cerrar_parrafo()
            cerrar_lista()
            cerrar_tabla()
            continue
        if es_linea_tabla(linea):
            cerrar_parrafo()
            cerrar_lista()
            if es_separador_tabla(linea):
                continue
            if tabla is None:
                tabla = {'tipo': 'tabla', 'filas': []}
            tabla['filas'].append(celdas_tabla(linea))
            continue
        cerrar_tabla()
        imagen = imagen_de(linea)
        if imagen:
            cerrar_parrafo()
            cerrar_lista()
            bloques.append(imagen)
            continue
        subtitulo = PATRON_SUBTITULO.match(linea)
        if subtitulo:
            cerrar_parrafo()
            cerrar_lista()
            bloques.append({'tipo': 'subtitulo', 'texto': subtitulo.group(1).strip()})
            continue
        numerado = PATRON_NUMERADO.match(linea)
        vineta = PATRON_VINETA.match(linea)
        if numerado or vineta:
            cerrar_parrafo()
            ordenada = bool(numerado)
            if lista is None or lista['ordenada'] != ordenada:
                cerrar_lista()
                lista = {'tipo': 'lista', 'ordenada': ordenada, 'items': []}
            lista['items'].append((numerado or vineta).group(1).strip())
            continue
        cerrar_lista()
        parrafo.append(linea)
    cerrar_parrafo()
    cerrar_lista()
    cerrar_tabla()
    return bloques


def parrafos_procedimiento(texto):
    """Párrafos separados por línea vacía; tablas e imágenes quedan como ítems propios."""
    items = []
    for bloque in re.split(r'\n\s*\n', str(texto or '')):
        parrafo = []
        for linea in bloque.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            if es_linea_adjunta(linea):
                if parrafo:
                    items.append(' '.join(parrafo))
                    parrafo = []
                items.append(linea)
            else:
                parrafo.append(linea)
        if parrafo:
            items.append(' '.join(parrafo))
    return items


def texto_procedimiento_parrafos(items):
    """Inverso de :func:`parrafos_procedimiento` para editar (filas de tabla juntas)."""
    partes = []
    anterior = None
    for item in items or []:
        item = str(item)
        if anterior is not None:
            juntas = es_linea_adjunta(item) and es_linea_adjunta(anterior)
            partes.append('\n' if juntas else '\n\n')
        partes.append(item)
        anterior = item
    return ''.join(partes)


def pasos_procedimiento(items, formato='numerado'):
    """Procedimiento como pasos con sus adjuntos (tablas o figuras debajo del paso).

    Con formato ``parrafos`` devuelve directamente los bloques enriquecidos.
    """
    lineas = [linea.strip() for linea in _lineas(items) if linea.strip()]
    if formato == 'parrafos':
        return bloques_enriquecidos(texto_procedimiento_parrafos(lineas))
    pasos = []
    for linea in lineas:
        if es_linea_adjunta(linea):
            if not pasos:
                pasos.append({'tipo': 'paso', 'texto': '', 'lineas': []})
            pasos[-1]['lineas'].append(linea)
            continue
        pasos.append({
            'tipo': 'paso',
            'texto': PATRON_PREFIJO_PASO.sub('', linea).strip(),
            'lineas': [],
        })
    for paso in pasos:
        paso['adjuntos'] = bloques_enriquecidos('\n'.join(paso.pop('lineas')))
    return pasos


def tiene_adjuntos(bloques):
    for bloque in bloques or []:
        if bloque.get('tipo') in {'tabla', 'imagen'}:
            return True
        if bloque.get('tipo') == 'paso' and bloque.get('adjuntos'):
            return True
    return False


def resolver_figura(fuente, figuras):
    """``figura:N`` → figura cargada N; ``https://…`` → imagen externa."""
    fuente = str(fuente or '').strip()
    numero = re.fullmatch(r'figura:(\d+)', fuente.lower())
    if numero:
        posicion = int(numero.group(1))
        for figura in figuras or []:
            if int(figura.get('n') or 0) == posicion:
                return figura
        return None
    if re.match(r'^https?://', fuente, re.IGNORECASE):
        return {'n': None, 'titulo': '', 'url': fuente, 'ruta': None}
    return None


def html_tabla(filas):
    if not filas:
        return ''
    ancho = max(len(fila) for fila in filas)

    def fila_html(celdas, etiqueta):
        celdas = list(celdas) + [''] * (ancho - len(celdas))
        return '<tr>' + ''.join(f'<{etiqueta}>{escape(celda)}</{etiqueta}>' for celda in celdas) + '</tr>'

    cuerpo = ''.join(fila_html(fila, 'td') for fila in filas[1:])
    return (
        '<div class="guide-table-wrap"><table class="guide-table">'
        f'<thead>{fila_html(filas[0], "th")}</thead>'
        + (f'<tbody>{cuerpo}</tbody>' if cuerpo else '')
        + '</table></div>'
    )


def html_imagen(bloque, figuras):
    figura = resolver_figura(bloque['fuente'], figuras)
    texto = bloque.get('texto') or (figura or {}).get('titulo') or ''
    if not figura or not figura.get('url'):
        return (
            '<p class="guide-figure guide-figure--missing">'
            f'[{escape(texto or bloque["fuente"])}: imagen no disponible]</p>'
        )
    pie = f'<figcaption>{escape(texto)}</figcaption>' if texto else ''
    return (
        '<figure class="guide-figure">'
        f'<img src="{escape(figura["url"])}" alt="{escape(texto)}">{pie}</figure>'
    )


def html_bloques(bloques, figuras=None):
    partes = []
    for bloque in bloques or []:
        tipo = bloque.get('tipo')
        if tipo == 'parrafo':
            partes.append(f'<p>{escape(bloque["texto"])}</p>')
        elif tipo == 'subtitulo':
            partes.append(f'<h4>{escape(bloque["texto"])}</h4>')
        elif tipo == 'lista':
            etiqueta = 'ol' if bloque['ordenada'] else 'ul'
            items = ''.join(f'<li>{escape(item)}</li>' for item in bloque['items'])
            partes.append(f'<{etiqueta}>{items}</{etiqueta}>')
        elif tipo == 'tabla':
            partes.append(html_tabla(bloque['filas']))
        elif tipo == 'imagen':
            partes.append(html_imagen(bloque, figuras))
    return ''.join(partes)


def html_procedimiento(items, formato='numerado', figuras=None):
    pasos = pasos_procedimiento(items, formato)
    if formato == 'parrafos':
        html = html_bloques(pasos, figuras)
        return f'<div class="guide-procedure-paragraphs">{html or "<p>No registrado</p>"}</div>'
    if not pasos:
        return '<p>No registrado</p>'
    etiqueta = 'ul' if formato == 'vinetas' else 'ol'
    prefijo = ''
    if not pasos[0]['texto']:
        prefijo = html_bloques(pasos[0]['adjuntos'], figuras)
    elementos = ''.join(
        f'<li>{escape(paso["texto"])}{html_bloques(paso["adjuntos"], figuras)}</li>'
        for paso in pasos
        if paso['texto']
    )
    if not elementos:
        return prefijo or '<p>No registrado</p>'
    return f'{prefijo}<{etiqueta}>{elementos}</{etiqueta}>'


def figuras_de_guia(guia):
    """Figuras de la guía en orden: ``{"n", "titulo", "url", "ruta", "pk"}``."""
    figuras = []
    if guia is None or guia.pk is None:
        return figuras
    for posicion, imagen in enumerate(guia.imagenes.all(), 1):
        try:
            url = imagen.imagen.url
            ruta = imagen.imagen.path
        except (ValueError, NotImplementedError):
            url, ruta = '', None
        figuras.append({
            'n': posicion,
            'titulo': imagen.titulo,
            'url': url,
            'ruta': ruta,
            'pk': imagen.pk,
        })
    return figuras


def validar_imagenes_guia(archivos, *, existentes=0):
    """Extensión, tipo, tamaño, cantidad y contenido real de imagen."""
    archivos = list(archivos or [])
    if existentes + len(archivos) > MAXIMO_IMAGENES:
        raise ValueError(f'La guía admite hasta {MAXIMO_IMAGENES} imágenes')
    for archivo in archivos:
        if Path(archivo.name).suffix.lower() not in EXTENSIONES_IMAGEN:
            raise ValueError(f'La imagen {archivo.name} debe ser JPG, PNG, GIF o WebP')
        if archivo.size > TAMANO_MAXIMO_IMAGEN:
            raise ValueError(f'La imagen {archivo.name} supera los 5 MB permitidos')
        try:
            with ImagenPil.open(archivo) as imagen:
                imagen.verify()
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise ValueError(f'El archivo {archivo.name} no es una imagen válida') from error
        finally:
            archivo.seek(0)
    return archivos


def figuras_borrador(token, usuario):
    """Figuras cargadas desde el editor antes de existir la guía, de esta persona."""
    token = str(token or '').strip()[:40]
    if not token or usuario is None or not getattr(usuario, 'pk', None):
        return ImagenGuiaActividad.objects.none()
    return ImagenGuiaActividad.objects.filter(
        guia__isnull=True, borrador_token=token, subido_por=usuario,
    ).order_by('pk')


def figuras_permitidas(guia=None, token='', usuario=None):
    """Identificadores que un apartado puede citar: los de la guía y los del borrador propio."""
    ids = set()
    if guia is not None and guia.pk:
        ids.update(guia.imagenes.values_list('pk', flat=True))
    ids.update(figuras_borrador(token, usuario).values_list('pk', flat=True))
    return ids


def guardar_figura(archivo, titulo='', *, usuario, guia=None, token=''):
    """Una figura cargada desde el editor visual (con guía o en borrador)."""
    existentes = guia.imagenes.count() if guia is not None and guia.pk else figuras_borrador(token, usuario).count()
    validar_imagenes_guia([archivo], existentes=existentes)
    return ImagenGuiaActividad.objects.create(
        guia=guia if guia is not None and guia.pk else None,
        borrador_token='' if guia is not None and guia.pk else str(token or '').strip()[:40],
        subido_por=usuario,
        imagen=archivo,
        titulo=str(titulo or '').strip()[:200],
        orden=existentes + 1,
        tamano=archivo.size,
    )


def adjuntar_figuras_borrador(guia, token, usuario):
    """Asocia a la guía recién guardada las figuras cargadas en borrador."""
    adjuntadas = []
    orden = guia.imagenes.count()
    for imagen in figuras_borrador(token, usuario):
        orden += 1
        imagen.guia = guia
        imagen.orden = orden
        imagen.borrador_token = ''
        imagen.save(update_fields=['guia', 'orden', 'borrador_token'])
        adjuntadas.append(imagen)
    return adjuntadas


@transaction.atomic
def guardar_imagenes_guia(guia, archivos, titulos=(), *, eliminar=()):
    """Elimina las figuras marcadas, agrega las nuevas y renumera ``orden``."""
    ids = {int(valor) for valor in eliminar or () if str(valor).isdigit()}
    retiradas = guia.imagenes.filter(pk__in=ids)
    archivos = validar_imagenes_guia(archivos, existentes=guia.imagenes.count() - retiradas.count())
    for imagen in retiradas:
        nombre, almacen = imagen.imagen.name, imagen.imagen.storage
        imagen.delete()
        if nombre:
            transaction.on_commit(lambda ruta=nombre, storage=almacen: storage.delete(ruta), robust=True)
    titulos = [str(titulo).strip() for titulo in (titulos or [])]
    orden = guia.imagenes.count()
    for posicion, archivo in enumerate(archivos):
        orden += 1
        ImagenGuiaActividad.objects.create(
            guia=guia,
            imagen=archivo,
            titulo=(titulos[posicion] if posicion < len(titulos) else '')[:200],
            orden=orden,
            tamano=archivo.size,
        )
    for posicion, imagen in enumerate(guia.imagenes.order_by('orden', 'pk'), 1):
        if imagen.orden != posicion:
            ImagenGuiaActividad.objects.filter(pk=imagen.pk).update(orden=posicion)
    return list(guia.imagenes.all())
