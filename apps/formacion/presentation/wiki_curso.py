"""Aula wiki: subconjunto Markdown explícito y seguro, compartido con el PDF.

Sólo se activa si la primera línea es [AULA_WIKI]. No admite HTML, plantillas,
JavaScript, imágenes remotas ni estilos del contenido. No necesita paquetes nuevos.

parsear_wiki devuelve bloques de texto sin HTML (también útiles para el PDF):
* titulo: nivel (2/3), texto e id estable wiki-<slug>-<aparición>.
* parrafo: texto; se conservan los marcadores inline para el consumidor.
* lista: ordenada, inicio e items (lista de textos, sin listas anidadas).
* tabla: cabeceras y filas, normalizadas al mismo número de columnas.
* codigo: lenguaje y texto literal, conservando saltos de línea.
* aviso: clase (tip/note/warning), titulo y texto multilinea.
* imagen: alt y src local validada; separador: sin otros campos.

Sin prefijo, parsear_wiki devuelve []. El consumidor PDF debe convertir los
marcadores inline mediante su propio escape: los campos NO son HTML confiable.
"""

import re
from html import escape
from urllib.parse import unquote, urlsplit

from django.utils.text import slugify

PREFIJO = '[AULA_WIKI]'
IMAGEN_LOCAL = re.compile(r'/static/portal/img/cursos/logistica-ia/[A-Za-z0-9_-]+\.svg\Z')
TITULO = re.compile(r'^(#{2,3})\s+(.+)$')
LISTA = re.compile(r'^(?:(\d{1,6})[.)]|([-*]))\s+(.+)$')
AVISO = re.compile(r'^>\s*\[!(TIP|NOTE|WARNING)\]\s*(.*)$', re.IGNORECASE)
IMAGEN = re.compile(r'^!\[([^\]\n]*)\]\(([^)\s]+)\)$')
INLINE = re.compile(r'`([^`\n]+)`|\*\*([^*\n]+)\*\*|\[([^\]\n]+)\]\(([^)\s]+)\)')
AVISOS = {
    'tip': ('Consejo', 'fas fa-lightbulb'),
    'note': ('Nota', 'fas fa-info-circle'),
    'warning': ('Atención', 'fas fa-exclamation-triangle'),
}


def es_wiki(contenido):
    """Opt-in: prefijo exacto en su primera línea, sin activar otros cursos."""
    lineas = str(contenido or '').splitlines()
    return bool(lineas and lineas[0] == PREFIJO)


def url_segura(valor):
    """Sólo http(s), anclas o rutas internas absolutas, sin controles ni traversal."""
    valor = str(valor or '')
    if not valor or any(ord(c) < 32 or ord(c) == 127 for c in valor):
        return ''
    comprobada = valor
    for _ in range(3):
        decodificada = unquote(comprobada)
        if decodificada == comprobada:
            break
        comprobada = decodificada
    if any(ord(c) < 32 or ord(c) == 127 for c in comprobada) or '\\' in comprobada:
        return ''
    if any(c in comprobada for c in '<>"\''):
        return ''
    if valor.startswith('#'):
        return valor if re.fullmatch(r'#[A-Za-z0-9_-]+', valor) else ''
    try:
        partes = urlsplit(valor)
        if partes.scheme.lower() in {'http', 'https'}:
            if not partes.netloc or partes.username or partes.password:
                return ''
            # Interpretar el puerto detecta una autoridad mal formada.
            partes.port
            return valor
        if partes.scheme or partes.netloc or not valor.startswith('/') or comprobada.startswith('//'):
            return ''
        segmentos = urlsplit(comprobada).path.split('/')
        if any(segmento in {'.', '..'} for segmento in segmentos):
            return ''
        return valor
    except ValueError:
        return ''


def _celdas(linea):
    """Admite barras escapadas; las barras normales separan columnas."""
    linea = linea.strip().strip('|')
    return [celda.strip().replace('\\|', '|') for celda in re.split(r'(?<!\\)\|', linea)]


def _es_tabla(linea):
    return linea.strip().startswith('|') and linea.strip().endswith('|')


def _separador_tabla(linea):
    return _es_tabla(linea) and all(re.fullmatch(r':?-{3,}:?', celda) for celda in _celdas(linea))


def parsear_wiki(contenido):
    """Analiza sólo el subconjunto documentado; no interpreta HTML arbitrario."""
    if not es_wiki(contenido):
        return []
    lineas = str(contenido).splitlines()[1:]
    bloques, apariciones = [], {}
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        if not linea:
            i += 1
            continue
        cerca = re.fullmatch(r'(`{3,}|~{3,})([A-Za-z0-9_-]{0,24})\s*', linea)
        if cerca:
            marca, lenguaje = cerca.groups()
            codigo = []
            i += 1
            while i < len(lineas) and lineas[i].strip() != marca:
                codigo.append(lineas[i])
                i += 1
            bloques.append({'tipo': 'codigo', 'lenguaje': lenguaje, 'texto': '\n'.join(codigo)})
            i += 1
            continue
        aviso = AVISO.match(linea)
        if aviso:
            clase = aviso.group(1).lower()
            texto_aviso = [aviso.group(2)] if aviso.group(2) else []
            i += 1
            while i < len(lineas) and lineas[i].lstrip().startswith('>'):
                texto_aviso.append(re.sub(r'^\s*> ?', '', lineas[i]))
                i += 1
            bloques.append({'tipo': 'aviso', 'clase': clase,
                            'titulo': AVISOS[clase][0], 'texto': '\n'.join(texto_aviso).strip()})
            continue
        titulo = TITULO.match(linea)
        if titulo:
            texto_titulo = titulo.group(2).strip()
            nombre = slugify(texto_titulo)[:70] or 'seccion'
            apariciones[nombre] = apariciones.get(nombre, 0) + 1
            bloques.append({'tipo': 'titulo', 'nivel': len(titulo.group(1)), 'texto': texto_titulo,
                            'id': f'wiki-{nombre}-{apariciones[nombre]}'})
            i += 1
            continue
        imagen = IMAGEN.match(linea)
        if imagen and IMAGEN_LOCAL.fullmatch(imagen.group(2)):
            bloques.append({'tipo': 'imagen', 'alt': imagen.group(1), 'src': imagen.group(2)})
            i += 1
            continue
        if linea in {'---', '***'}:
            bloques.append({'tipo': 'separador'})
            i += 1
            continue
        if _es_tabla(linea) and i + 1 < len(lineas) and _separador_tabla(lineas[i + 1]):
            cabeceras, filas = _celdas(linea), []
            i += 2
            while i < len(lineas) and _es_tabla(lineas[i]):
                filas.append(_celdas(lineas[i]))
                i += 1
            ancho = max([len(cabeceras)] + [len(fila) for fila in filas])
            cabeceras += [f'Columna {n + 1}' for n in range(len(cabeceras), ancho)]
            filas = [fila + [''] * (ancho - len(fila)) for fila in filas]
            bloques.append({'tipo': 'tabla', 'cabeceras': cabeceras, 'filas': filas})
            continue
        item = LISTA.match(linea)
        if item:
            ordenada = item.group(1) is not None
            inicio = int(item.group(1)) if ordenada else 1
            items = []
            while i < len(lineas):
                item = LISTA.match(lineas[i].strip())
                if not item or (item.group(1) is not None) != ordenada:
                    break
                items.append(item.group(3))
                i += 1
            bloques.append({'tipo': 'lista', 'ordenada': ordenada, 'inicio': inicio, 'items': items})
            continue
        parrafo = [linea]
        i += 1
        while i < len(lineas):
            siguiente = lineas[i].strip()
            if (not siguiente or TITULO.match(siguiente) or LISTA.match(siguiente) or AVISO.match(siguiente)
                    or IMAGEN.match(siguiente) or _es_tabla(siguiente)
                    or siguiente.startswith(('```', '~~~')) or siguiente in {'---', '***'}):
                break
            parrafo.append(siguiente)
            i += 1
        bloques.append({'tipo': 'parrafo', 'texto': ' '.join(parrafo)})
    return bloques


def inline_wiki(texto, *, enlaces=True):
    """Genera etiquetas propias y escapa cada fragmento proveniente del contenido."""
    texto = str(texto or '')
    partes, cursor = [], 0
    for token in INLINE.finditer(texto):
        partes.append(escape(texto[cursor:token.start()]))
        codigo, negrita, etiqueta, destino = token.groups()
        if codigo is not None:
            partes.append(f'<code>{escape(codigo)}</code>')
        elif negrita is not None:
            partes.append(f'<strong>{inline_wiki(negrita, enlaces=False)}</strong>')
        else:
            direccion = url_segura(destino) if enlaces else ''
            rotulo = inline_wiki(etiqueta, enlaces=False)
            if direccion:
                atributos = ' target="_blank" rel="noopener noreferrer"' if direccion.lower().startswith(('http://', 'https://')) else ''
                partes.append(f'<a href="{escape(direccion, quote=True)}"{atributos}>{rotulo}</a>')
            else:
                partes.append(rotulo)
        cursor = token.end()
    partes.append(escape(texto[cursor:]))
    return ''.join(partes)


def _html_bloques(bloques):
    partes = []
    numero = 0
    for bloque in bloques:
        tipo = bloque['tipo']
        if tipo == 'titulo':
            nivel = 'h3' if bloque['nivel'] == 2 else 'h4'
            if bloque['nivel'] == 2:
                numero += 1
            insignia = f'<span class="curso-wiki__numero" aria-hidden="true">{numero}</span>' if bloque['nivel'] == 2 else ''
            partes.append(f'<{nivel} class="curso-wiki__titulo" id="{escape(bloque["id"])}" tabindex="-1">'
                          f'{insignia}{inline_wiki(bloque["texto"])}</{nivel}>')
        elif tipo == 'parrafo':
            partes.append(f'<p>{inline_wiki(bloque["texto"])}</p>')
        elif tipo == 'lista':
            tag = 'ol' if bloque['ordenada'] else 'ul'
            inicio = f' start="{bloque["inicio"]}"' if bloque['ordenada'] else ''
            partes.append(f'<{tag}{inicio}>' + ''.join(f'<li>{inline_wiki(item)}</li>' for item in bloque['items']) + f'</{tag}>')
        elif tipo == 'tabla':
            cabecera = ''.join(f'<th scope="col">{inline_wiki(celda)}</th>' for celda in bloque['cabeceras'])
            filas = ''.join('<tr>' + ''.join(f'<td>{inline_wiki(celda)}</td>' for celda in fila) + '</tr>' for fila in bloque['filas'])
            partes.append('<div class="curso-wiki__tabla" role="region" aria-label="Tabla de contenido de la lección" tabindex="0">'
                          f'<table><thead><tr>{cabecera}</tr></thead><tbody>{filas}</tbody></table></div>')
        elif tipo == 'codigo':
            lenguaje = f'<span class="curso-wiki__lenguaje">{escape(bloque["lenguaje"])}</span>' if bloque['lenguaje'] else ''
            partes.append('<div class="curso-wiki__codigo">' + lenguaje + '<pre tabindex="0" aria-label="Ejemplo de código">'
                          f'<code>{escape(bloque["texto"])}</code></pre></div>')
        elif tipo == 'aviso':
            _, icono = AVISOS[bloque['clase']]
            cuerpo = '<br>'.join(inline_wiki(linea) for linea in bloque['texto'].splitlines())
            partes.append(f'<aside class="curso-wiki__aviso curso-wiki__aviso--{bloque["clase"]}" '
                          f'aria-label="{escape(bloque["titulo"])}"><strong class="curso-wiki__aviso-titulo">'
                          f'<i class="{icono}" aria-hidden="true"></i> {escape(bloque["titulo"])}</strong><p>{cuerpo}</p></aside>')
        elif tipo == 'imagen':
            fuente = escape(bloque['src'], quote=True)
            alternativa = escape(bloque['alt'], quote=True)
            partes.append('<figure class="curso-wiki__figura">'
                          f'<a class="curso-wiki__ampliar" href="{fuente}" target="_blank" rel="noopener noreferrer" '
                          f'aria-label="Abrir diagrama: {alternativa}"><img src="{fuente}" alt="{alternativa}" '
                          'loading="lazy" decoding="async"></a>'
                          f'<figcaption><span>{escape(bloque["alt"])}</span> '
                          f'<a href="{fuente}" target="_blank" rel="noopener noreferrer">'
                          '<i class="fas fa-expand" aria-hidden="true"></i> Abrir diagrama'
                          '<span class="curso-wiki__sr"> en otra pestaña</span></a></figcaption></figure>')
        elif tipo == 'separador':
            partes.append('<hr>')
    return ''.join(partes)


def html_wiki(contenido):
    """Renderer opt-in. No marca texto original ni HTML aportado como seguro."""
    if not es_wiki(contenido):
        return escape(str(contenido or ''))
    bloques = parsear_wiki(contenido)
    titulos = [bloque for bloque in bloques if bloque['tipo'] == 'titulo']
    indice = ''
    if titulos:
        items = ''.join(f'<li class="curso-wiki__indice-nivel-{bloque["nivel"]}">'
                        f'<a href="#{escape(bloque["id"])}">{inline_wiki(bloque["texto"], enlaces=False)}</a></li>'
                        for bloque in titulos)
        indice = '<nav class="curso-wiki__indice" aria-label="Índice de esta lección"><details>' \
                 '<summary><i class="fas fa-map-signs" aria-hidden="true"></i> En esta lección</summary>' \
                 f'<ol>{items}</ol></details></nav>'
    return f'<article class="curso-wiki">{indice}{_html_bloques(bloques)}</article>'
