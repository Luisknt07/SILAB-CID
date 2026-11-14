"""Bibliografía y materiales complementarios de la guía FT04.

El docente pega entradas BibTeX (``@article{...}``) o escribe referencias ya
redactadas, una por línea. Aquí se convierten a cadenas legibles en estilo
IEEE, que comparten la vista HTML, el PDF y la vista previa del asistente.
La fuente original se conserva en ``contenido['bibliografia_fuente']`` para
poder seguir editándola.

Los materiales complementarios se escriben como ``Título | https://enlace``
y se guardan como ``{"titulo", "url"}``.
"""

import re
from urllib.parse import urlsplit

MESES = {
    '1': 'ene.', '2': 'feb.', '3': 'mar.', '4': 'abr.', '5': 'may.', '6': 'jun.',
    '7': 'jul.', '8': 'ago.', '9': 'sep.', '10': 'oct.', '11': 'nov.', '12': 'dic.',
    'jan': 'ene.', 'feb': 'feb.', 'mar': 'mar.', 'apr': 'abr.', 'may': 'may.',
    'jun': 'jun.', 'jul': 'jul.', 'aug': 'ago.', 'sep': 'sep.', 'oct': 'oct.',
    'nov': 'nov.', 'dec': 'dic.',
    'ene': 'ene.', 'abr': 'abr.', 'ago': 'ago.', 'dic': 'dic.',
}
ACENTOS = {
    "'": {'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú', 'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú'},
    '"': {'a': 'ä', 'e': 'ë', 'i': 'ï', 'o': 'ö', 'u': 'ü', 'A': 'Ä', 'E': 'Ë', 'I': 'Ï', 'O': 'Ö', 'U': 'Ü'},
    '~': {'n': 'ñ', 'N': 'Ñ', 'a': 'ã', 'o': 'õ'},
    '`': {'a': 'à', 'e': 'è', 'i': 'ì', 'o': 'ò', 'u': 'ù'},
    '^': {'a': 'â', 'e': 'ê', 'i': 'î', 'o': 'ô', 'u': 'û'},
}
PARTICULAS = {'de', 'del', 'la', 'las', 'los', 'da', 'das', 'do', 'dos', 'van', 'von', 'der', 'di', 'le', 'du'}
TIPOS_TESIS = {'phdthesis': 'Tesis doctoral', 'mastersthesis': 'Tesis de maestría'}


def limpiar_latex(valor):
    """Quita llaves, macros de acento y espacios duros de un valor BibTeX."""
    texto = str(valor or '')

    def acento(coincidencia):
        tipo, letra = coincidencia.group(1), coincidencia.group(2)
        return ACENTOS.get(tipo, {}).get(letra, letra)

    texto = re.sub(r"\{?\\(['\"~`^])\{?([A-Za-z])\}?\}?", acento, texto)
    texto = texto.replace('\\&', '&').replace('\\%', '%').replace('\\_', '_')
    texto = re.sub(r'\\[a-zA-Z]+\s*', '', texto)
    texto = texto.replace('~', ' ')
    texto = re.sub(r'[{}]', '', texto)
    texto = texto.replace('---', '—').replace('--', '–')
    return re.sub(r'\s+', ' ', texto).strip()


def _dividir_campos(cuerpo):
    """Separa ``clave = valor`` por comas de nivel cero, respetando llaves y comillas."""
    partes = []
    actual = []
    profundidad = 0
    entre_comillas = False
    for caracter in cuerpo:
        if caracter == '"' and profundidad == 0:
            entre_comillas = not entre_comillas
        elif caracter == '{':
            profundidad += 1
        elif caracter == '}':
            profundidad = max(0, profundidad - 1)
        if caracter == ',' and profundidad == 0 and not entre_comillas:
            partes.append(''.join(actual))
            actual = []
            continue
        actual.append(caracter)
    partes.append(''.join(actual))
    return [parte.strip() for parte in partes if parte.strip()]


def _valor_campo(bruto, *, literal=False):
    valor = bruto.strip()
    if valor.startswith('{') and valor.endswith('}'):
        valor = valor[1:-1]
    elif valor.startswith('"') and valor.endswith('"'):
        valor = valor[1:-1]
    # Autores y editores conservan sus llaves internas: ``{{Institución}}``
    # indica un nombre corporativo que no se abrevia.
    return valor.strip() if literal else limpiar_latex(valor)


def parsear_bibtex(texto):
    """Devuelve las entradas BibTeX halladas en ``texto`` con su posición.

    Cada entrada es ``{"tipo", "clave", "campos", "inicio", "fin"}``; los
    nombres de campo van en minúsculas y los valores ya limpios de LaTeX.
    """
    entradas = []
    texto = str(texto or '')
    for coincidencia in re.finditer(r'@(\w+)\s*\{', texto):
        tipo = coincidencia.group(1).lower()
        if tipo in {'comment', 'preamble', 'string'}:
            continue
        inicio_cuerpo = coincidencia.end()
        profundidad = 1
        posicion = inicio_cuerpo
        while posicion < len(texto) and profundidad:
            if texto[posicion] == '{':
                profundidad += 1
            elif texto[posicion] == '}':
                profundidad -= 1
            posicion += 1
        if profundidad:
            break
        cuerpo = texto[inicio_cuerpo:posicion - 1]
        partes = _dividir_campos(cuerpo)
        clave = ''
        campos = {}
        if partes and '=' not in partes[0]:
            clave = partes.pop(0).strip()
        for parte in partes:
            if '=' not in parte:
                continue
            nombre, bruto = parte.split('=', 1)
            nombre = nombre.strip().lower()
            campos[nombre] = _valor_campo(bruto, literal=nombre in {'author', 'editor'})
        entradas.append({
            'tipo': tipo,
            'clave': clave,
            'campos': campos,
            'inicio': coincidencia.start(),
            'fin': posicion,
        })
    return entradas


def _iniciales(nombres):
    iniciales = []
    for nombre in nombres.replace('.', ' ').split():
        partes = [parte for parte in nombre.split('-') if parte]
        iniciales.append('-'.join(f'{parte[0].upper()}.' for parte in partes))
    return ' '.join(iniciales)


def formatear_autor_ieee(nombre):
    """``Apellido, Nombre`` o ``Nombre Apellido`` → ``N. Apellido``.

    Un nombre entre llaves (``{Organización Mundial de la Salud}``) es
    corporativo y se conserva completo.
    """
    bruto = str(nombre or '').strip()
    if bruto.startswith('{') and bruto.endswith('}'):
        return limpiar_latex(bruto)
    nombre = limpiar_latex(bruto)
    if not nombre:
        return ''
    if ',' in nombre:
        apellido, _, nombres = nombre.partition(',')
        apellido, nombres = apellido.strip(), nombres.strip()
    else:
        palabras = nombre.split()
        if len(palabras) == 1:
            return palabras[0]
        indice = len(palabras) - 1
        while indice > 1 and palabras[indice - 1].lower() in PARTICULAS:
            indice -= 1
        apellido = ' '.join(palabras[indice:])
        nombres = ' '.join(palabras[:indice])
    iniciales = _iniciales(nombres)
    return f'{iniciales} {apellido}'.strip()


def formatear_autores_ieee(valor):
    """Lista de autores IEEE: hasta seis nombres; desde el séptimo, ``et al.``"""
    autores = [
        formatear_autor_ieee(parte)
        for parte in re.split(r'\s+and\s+', str(valor or ''), flags=re.IGNORECASE)
        if parte.strip()
    ]
    autores = [autor for autor in autores if autor]
    if not autores:
        return ''
    if len(autores) > 6:
        return f'{autores[0]} et al.'
    if len(autores) == 1:
        return autores[0]
    return ', '.join(autores[:-1]) + ' y ' + autores[-1]


def _mes(valor):
    clave = str(valor or '').strip().lower()
    if not clave:
        return ''
    clave = clave.rstrip('.')[:3] if not clave.isdigit() else str(int(clave))
    return MESES.get(clave, str(valor).strip())


def _paginas(valor):
    valor = str(valor or '').strip()
    if not valor:
        return ''
    return f'p. {valor}' if re.fullmatch(r'\d+', valor) else f'pp. {valor}'


def _edicion(valor):
    valor = str(valor or '').strip()
    if not valor:
        return ''
    return f'{valor}.ª ed.' if valor.isdigit() else f'{valor} ed.'


def formatear_ieee(entrada):
    """Una entrada de :func:`parsear_bibtex` → referencia IEEE (sin ``[n]``)."""
    tipo = entrada.get('tipo', 'misc')
    campos = entrada.get('campos', {})
    autores = formatear_autores_ieee(campos.get('author') or campos.get('editor'))
    titulo = campos.get('title', '')
    anio = campos.get('year', '')
    fecha = ' '.join(parte for parte in (_mes(campos.get('month')), anio) if parte)
    doi = f"doi: {campos['doi']}" if campos.get('doi') else ''
    lugar_editorial = ': '.join(parte for parte in (campos.get('address'), campos.get('publisher')) if parte)
    partes = []

    if tipo == 'article':
        partes = [
            autores, f'“{titulo},”' if titulo else '', campos.get('journal', ''),
            f"vol. {campos['volume']}" if campos.get('volume') else '',
            f"n.º {campos['number']}" if campos.get('number') else '',
            _paginas(campos.get('pages')), fecha, doi,
        ]
    elif tipo == 'book':
        cabecera = ', '.join(parte for parte in (autores, titulo, _edicion(campos.get('edition'))) if parte)
        cola = ', '.join(parte for parte in (lugar_editorial, anio) if parte)
        if cola:
            cabecera = cabecera if cabecera.endswith('.') else f'{cabecera}.'
            referencia = f'{cabecera} {cola}.'
        else:
            referencia = cabecera if cabecera.endswith('.') else f'{cabecera}.'
        return _con_url(referencia, campos)
    elif tipo in {'inbook', 'incollection'}:
        editor = formatear_autores_ieee(campos.get('editor')) if campos.get('author') and campos.get('editor') else ''
        partes = [
            autores, f'“{titulo},”' if titulo else '',
            f"en {campos['booktitle']}" if campos.get('booktitle') else '',
            f'{editor}, Ed.' if editor else '', lugar_editorial, anio, _paginas(campos.get('pages')),
        ]
    elif tipo in {'inproceedings', 'conference', 'proceedings'}:
        partes = [
            autores, f'“{titulo},”' if titulo else '',
            f"en {campos['booktitle']}" if campos.get('booktitle') else '',
            campos.get('address', ''), fecha, _paginas(campos.get('pages')), doi,
        ]
    elif tipo in TIPOS_TESIS:
        partes = [
            autores, f'“{titulo},”' if titulo else '', TIPOS_TESIS[tipo],
            campos.get('school', ''), campos.get('address', ''), anio,
        ]
    elif tipo == 'techreport':
        partes = [
            autores, f'“{titulo},”' if titulo else '', campos.get('institution', ''),
            campos.get('address', ''),
            f"Inf. téc. {campos['number']}" if campos.get('number') else '', anio,
        ]
    elif tipo == 'manual':
        partes = [autores, titulo, campos.get('organization', ''), campos.get('address', ''), anio]
    else:
        # misc, online, unpublished y cualquier tipo no previsto.
        partes = [
            autores, f'“{titulo},”' if titulo else '',
            campos.get('howpublished') or campos.get('publisher') or campos.get('organization')
            or campos.get('journal') or campos.get('note', ''),
            fecha,
        ]
    return _con_url(_unir(partes), campos)


def _con_url(referencia, campos):
    url = campos.get('url', '')
    if not url or not referencia:
        return referencia
    acceso = f" (accedido: {campos['urldate']})" if campos.get('urldate') else ''
    return f'{referencia} [En línea]. Disponible en: {url}{acceso}'


def _unir(partes, separador=', '):
    limpias = [str(parte).strip() for parte in partes if str(parte or '').strip()]
    if not limpias:
        return ''
    texto = separador.join(limpias)
    texto = re.sub(r',”\s*,', ',”', texto)
    texto = texto.replace(',”.', '.”').replace(', .', '.')
    if texto.endswith(',”'):
        texto = texto[:-2] + '.”'
    elif not texto.endswith('.'):
        texto += '.'
    return texto


def normalizar_bibliografia(texto):
    """Texto mixto (BibTeX y líneas sueltas) → lista de referencias IEEE.

    Las líneas sueltas se conservan tal cual, sin su numeración previa; la
    numeración ``[n]`` la agregan la vista HTML, el PDF y la vista previa.
    """
    texto = str(texto or '')
    referencias = []

    def agregar_lineas(fragmento):
        for linea in fragmento.splitlines():
            limpia = re.sub(r'^\s*(?:\[\d+\]|\d+[.)])\s*', '', linea).strip()
            if limpia:
                referencias.append(limpia)

    cursor = 0
    for entrada in parsear_bibtex(texto):
        agregar_lineas(texto[cursor:entrada['inicio']])
        formateada = formatear_ieee(entrada)
        if formateada:
            referencias.append(formateada)
        cursor = entrada['fin']
    agregar_lineas(texto[cursor:])
    return referencias


def normalizar_materiales_complementarios(texto):
    """``Título | https://enlace`` por línea → ``[{"titulo", "url"}]``."""
    materiales = []
    for linea in str(texto or '').splitlines():
        linea = linea.strip().lstrip('-•* ').strip()
        if not linea:
            continue
        titulo, _, url = linea.partition('|')
        titulo, url = titulo.strip(), url.strip()
        if not url and re.match(r'^https?://', titulo, re.IGNORECASE):
            url, titulo = titulo, ''
        if url and not re.match(r'^https?://', url, re.IGNORECASE):
            titulo, url = f'{titulo} | {url}'.strip(' |'), ''
        if url and not titulo:
            titulo = urlsplit(url).netloc or url
        materiales.append({'titulo': titulo, 'url': url})
    return materiales


def materiales_a_texto(materiales):
    """Inverso de :func:`normalizar_materiales_complementarios` para editar."""
    if isinstance(materiales, str):
        return materiales
    lineas = []
    for item in materiales or []:
        if isinstance(item, dict):
            titulo, url = item.get('titulo', ''), item.get('url', '')
            lineas.append(f'{titulo} | {url}' if url else titulo)
        elif str(item).strip():
            lineas.append(str(item).strip())
    return '\n'.join(lineas)
