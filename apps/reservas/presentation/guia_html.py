"""Contenido enriquecido de la guía FT04 en HTML acotado (``formato_contenido = "html"``).

El editor visual escribe directamente sobre la plantilla institucional; cada
apartado autorizado llega como un fragmento HTML que aquí se **sanea por lista
blanca** con el analizador de la biblioteca estándar (nunca con expresiones
regulares): se reconstruye un árbol solo con las etiquetas, atributos y
estructuras permitidas y se descarta todo lo demás (estilos, clases ajenas,
scripts, imágenes externas...).

Del mismo árbol salen las tres salidas, así la numeración de figuras y tablas
coincide en el editor, la vista HTML y el PDF:

- :func:`sanear` → HTML normalizado que se guarda en ``contenido``;
- :class:`DocumentoHtml` → HTML de presentación (con las imágenes resueltas
  desde ``ImagenGuiaActividad`` y los pies «Figura N.» / «Tabla N.») y bloques
  para el generador PDF;
- :func:`html_desde_legado` → convierte el mini-lenguaje anterior (``##``,
  ``|`` y ``![t](figura:N)``) al abrir una guía antigua en el editor.

Las figuras se referencian por el identificador estable de la imagen
(``data-figura``), no por su número visible ni por su ruta.
"""

from html import escape
from html.parser import HTMLParser
import re
from xml.sax.saxutils import escape as escape_xml

FORMATO_HTML = 'html'

# Orden de aparicion en el documento: define la numeracion de figuras y tablas.
CAMPOS_RICOS = (
    'resultado_aprendizaje',
    'objetivos',
    'fundamento_teorico',
    'medidas_seguridad',
    'procedimiento',
    'resultados_esperados',
    'criterios_evaluacion',
)

# Que admite cada apartado. "texto": parrafos, listas y enfasis; "tablas": ademas
# subtitulos y tablas; "rico": ademas figuras; "pasos": procedimiento por pasos,
# cada paso admite parrafos, listas, tablas y figuras.
POLITICAS = {
    'texto': {'titulos': False, 'tablas': False, 'figuras': False},
    'tablas': {'titulos': True, 'tablas': True, 'figuras': False},
    'rico': {'titulos': True, 'tablas': True, 'figuras': True},
    'pasos': {'titulos': False, 'tablas': True, 'figuras': True},
}
POLITICA_POR_CAMPO = {
    'resultado_aprendizaje': 'texto',
    'objetivos': 'texto',
    'fundamento_teorico': 'rico',
    'medidas_seguridad': 'texto',
    'procedimiento': 'pasos',
    'resultados_esperados': 'tablas',
    'criterios_evaluacion': 'tablas',
}
TAMANOS_FIGURA = ('pequena', 'mediana', 'ancha')
ETIQUETAS_VACIAS = {'br', 'img', 'hr', 'col', 'input', 'meta', 'link', 'wbr', 'source', 'area', 'base'}
# Se descartan con todo su contenido.
DESCARTAR = {
    'script', 'style', 'head', 'meta', 'link', 'title', 'iframe', 'object', 'embed',
    'svg', 'math', 'template', 'noscript', 'video', 'audio', 'canvas', 'form',
    'input', 'button', 'select', 'textarea', 'option', 'xml',
}
MAPA_ETIQUETAS = {
    'b': 'strong', 'i': 'em', 'h1': 'h4', 'h2': 'h4', 'h3': 'h4', 'h6': 'h5',
}
INLINE = {'strong', 'em', 'a', 'br'}
PATRON_URL = re.compile(r'^(https?://|mailto:)', re.IGNORECASE)
PATRON_ESPACIOS = re.compile(r'[ \t\r\n\f\v ]+')
LIMITE_HTML = 400_000


class Nodo:
    __slots__ = ('etiqueta', 'atributos', 'hijos', 'texto')

    def __init__(self, etiqueta, atributos=None, texto=None):
        self.etiqueta = etiqueta
        self.atributos = dict(atributos or {})
        self.hijos = []
        self.texto = texto

    @property
    def es_texto(self):
        return self.etiqueta == '#texto'

    def texto_plano(self):
        if self.es_texto:
            return self.texto or ''
        if self.etiqueta == 'br':
            return '\n'
        return ''.join(hijo.texto_plano() for hijo in self.hijos)


class _Analizador(HTMLParser):
    """Construye el árbol sin interpretar nada: entidades resueltas, texto literal."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo('#raiz')
        self.pila = [self.raiz]

    def handle_starttag(self, tag, attrs):
        if len(self.pila) >= 64:
            from django.core.exceptions import ValidationError
            raise ValidationError('El contenido HTML tiene demasiados niveles anidados.')
        nodo = Nodo(tag.lower(), {clave.lower(): (valor or '') for clave, valor in attrs})
        self.pila[-1].hijos.append(nodo)
        if nodo.etiqueta not in ETIQUETAS_VACIAS:
            self.pila.append(nodo)

    def handle_startendtag(self, tag, attrs):
        self.pila[-1].hijos.append(
            Nodo(tag.lower(), {clave.lower(): (valor or '') for clave, valor in attrs})
        )

    def handle_endtag(self, tag):
        tag = tag.lower()
        for posicion in range(len(self.pila) - 1, 0, -1):
            if self.pila[posicion].etiqueta == tag:
                del self.pila[posicion:]
                return

    def handle_data(self, data):
        if data:
            self.pila[-1].hijos.append(Nodo('#texto', texto=data))


def analizar(html):
    analizador = _Analizador()
    value = str(html or '')
    if len(value) > LIMITE_HTML:
        from django.core.exceptions import ValidationError
        raise ValidationError('El contenido HTML supera el tamaño permitido.')
    analizador.feed(value)
    analizador.close()
    return analizador.raiz


def texto_plano(html):
    """Texto sin etiquetas, para saber si un apartado está vacío."""
    return PATRON_ESPACIOS.sub(' ', analizar(html).texto_plano()).strip()


def esta_vacio(html):
    return not texto_plano(html)


# --------------------------------------------------------------------- saneado


class Saneador:
    """Reconstruye el fragmento con la política del apartado.

    ``figuras_permitidas``: identificadores de imagen que pueden citarse; si se
    indica, cualquier otra figura se elimina (evita referenciar imágenes ajenas).
    """

    def __init__(self, politica='rico', figuras_permitidas=None):
        self.politica = POLITICAS.get(politica, POLITICAS['rico'])
        self.es_pasos = politica == 'pasos'
        self.figuras_permitidas = (
            {str(valor) for valor in figuras_permitidas} if figuras_permitidas is not None else None
        )
        self.avisos = []

    # -- utilidades de texto -------------------------------------------------
    @staticmethod
    def _texto(nodo, preservar=False):
        texto = nodo.texto or ''
        return texto if preservar else PATRON_ESPACIOS.sub(' ', texto)

    def _inline(self, nodos, permitir_br=True):
        """Devuelve solo contenido en línea (texto, strong, em, a, br)."""
        resultado = []
        for nodo in nodos:
            if nodo.es_texto:
                texto = self._texto(nodo)
                if texto:
                    resultado.append(Nodo('#texto', texto=texto))
                continue
            etiqueta = MAPA_ETIQUETAS.get(nodo.etiqueta, nodo.etiqueta)
            if etiqueta in DESCARTAR:
                continue
            if etiqueta == 'br':
                if permitir_br:
                    resultado.append(Nodo('br'))
                continue
            if etiqueta in {'strong', 'em'}:
                hijos = self._inline(nodo.hijos, permitir_br)
                if hijos:
                    nuevo = Nodo(etiqueta)
                    nuevo.hijos = hijos
                    resultado.append(nuevo)
                continue
            if etiqueta == 'a':
                href = (nodo.atributos.get('href') or '').strip()
                hijos = self._inline(nodo.hijos, permitir_br)
                if PATRON_URL.match(href) and hijos:
                    nuevo = Nodo('a', {'href': href, 'target': '_blank', 'rel': 'noopener'})
                    nuevo.hijos = hijos
                    resultado.append(nuevo)
                else:
                    resultado.extend(hijos)
                continue
            if etiqueta == 'img':
                self._imagen_no_recuperable(nodo)
                continue
            # Cualquier otra etiqueta (span, font, u, div dentro de un parrafo...)
            # se desenvuelve: se conserva el texto, no el formato ajeno.
            resultado.extend(self._inline(nodo.hijos, permitir_br))
        return self._recortar(resultado)

    @staticmethod
    def _recortar(nodos):
        """Quita espacios y saltos sobrantes al inicio y al final de una línea."""
        while nodos and nodos[0].es_texto and not nodos[0].texto.strip():
            nodos.pop(0)
        while nodos and (
            (nodos[-1].es_texto and not nodos[-1].texto.strip()) or nodos[-1].etiqueta == 'br'
        ):
            nodos.pop()
        if nodos and nodos[0].es_texto:
            nodos[0].texto = nodos[0].texto.lstrip()
        if nodos and nodos[-1].es_texto:
            nodos[-1].texto = nodos[-1].texto.rstrip()
        return nodos

    def _imagen_no_recuperable(self, nodo):
        if nodo.atributos.get('data-figura') and self._figura_desde(nodo) is not None:
            return
        self.avisos.append('imagen_no_recuperable')

    # -- bloques -------------------------------------------------------------
    def _figura_desde(self, nodo):
        identificador = str(nodo.atributos.get('data-figura') or '').strip()
        if not identificador.isdigit():
            return None
        if self.figuras_permitidas is not None and identificador not in self.figuras_permitidas:
            return None
        tamano = nodo.atributos.get('data-tamano') or 'mediana'
        if tamano not in TAMANOS_FIGURA:
            tamano = 'mediana'
        return Nodo('figure', {
            'class': 'guide-figure',
            'data-figura': identificador,
            'data-titulo': (nodo.atributos.get('data-titulo') or '').strip()[:200],
            'data-fuente': (nodo.atributos.get('data-fuente') or '').strip()[:200],
            'data-tamano': tamano,
        })

    def _tabla_desde(self, tabla, titulo=''):
        filas = []
        cabecera = False
        for seccion in tabla.hijos:
            grupo = [seccion] if seccion.etiqueta == 'tr' else (
                seccion.hijos if seccion.etiqueta in {'thead', 'tbody', 'tfoot'} else []
            )
            for fila in grupo:
                if fila.etiqueta != 'tr':
                    continue
                celdas = []
                for celda in fila.hijos:
                    if celda.etiqueta not in {'td', 'th'}:
                        continue
                    if celda.etiqueta == 'th' and not filas and not celdas:
                        cabecera = True
                    nueva = Nodo('td')
                    nueva.hijos = self._inline(self._aplanar_celda(celda.hijos))
                    celdas.append(nueva)
                if celdas:
                    filas.append(celdas)
        if not filas:
            return None
        ancho = max(len(fila) for fila in filas)
        for fila in filas:
            fila.extend(Nodo('td') for _ in range(ancho - len(fila)))
        if str(tabla.atributos.get('data-cabecera', '')).strip() in {'1', 'true'}:
            cabecera = True
        bloque = Nodo('figure', {
            'class': 'guide-table',
            'data-titulo': titulo[:200],
            'data-cabecera': '1' if cabecera else '0',
        })
        contenedor = Nodo('table')
        for fila in filas:
            tr = Nodo('tr')
            tr.hijos = fila
            contenedor.hijos.append(tr)
        bloque.hijos.append(contenedor)
        return bloque

    def _aplanar_celda(self, hijos):
        """Un párrafo por línea dentro de la celda: Word manda <p> en cada celda."""
        resultado = []
        for hijo in hijos:
            if not hijo.es_texto and hijo.etiqueta in {'p', 'div'}:
                if resultado:
                    resultado.append(Nodo('br'))
                resultado.extend(self._aplanar_celda(hijo.hijos))
            else:
                resultado.append(hijo)
        return resultado

    def _bloques(self, nodos, *, en_paso=False):
        """Convierte hijos arbitrarios en una secuencia de bloques permitidos."""
        resultado = []
        pendiente = []  # contenido en linea que aun no tiene parrafo

        def cerrar_pendiente():
            hijos = self._inline(pendiente)
            pendiente.clear()
            if hijos:
                parrafo = Nodo('p')
                parrafo.hijos = hijos
                resultado.append(parrafo)

        for nodo in nodos:
            if nodo.es_texto:
                pendiente.append(nodo)
                continue
            etiqueta = MAPA_ETIQUETAS.get(nodo.etiqueta, nodo.etiqueta)
            if etiqueta in DESCARTAR:
                continue
            if etiqueta in INLINE or etiqueta in {'span', 'font', 'u', 's', 'sub', 'sup', 'code', 'small', 'mark', 'label'}:
                pendiente.append(nodo)
                continue
            if etiqueta == 'img':
                figura = self._figura_desde(nodo)
                cerrar_pendiente()
                if figura is not None and self.politica['figuras']:
                    resultado.append(figura)
                else:
                    self._imagen_no_recuperable(nodo)
                continue
            if etiqueta == 'figure':
                cerrar_pendiente()
                clases = (nodo.atributos.get('class') or '').split()
                # En el editor la tabla va dentro de un contenedor desplazable.
                tabla = _buscar(nodo, 'table')
                if 'guide-table' in clases or tabla is not None:
                    if self.politica['tablas']:
                        if tabla is not None and nodo.atributos.get('data-cabecera') in {'1', 'true'}:
                            tabla.atributos['data-cabecera'] = '1'
                        bloque = self._tabla_desde(tabla, nodo.atributos.get('data-titulo') or '') if tabla else None
                        if bloque is not None:
                            resultado.append(bloque)
                    continue
                figura = self._figura_desde(nodo)
                if figura is not None and self.politica['figuras']:
                    resultado.append(figura)
                elif nodo.atributos.get('data-figura'):
                    self.avisos.append('figura_no_autorizada')
                else:
                    # Un <figure> ajeno (Word, otra web): se conserva su texto.
                    resultado.extend(self._bloques(
                        [hijo for hijo in nodo.hijos if hijo.etiqueta != 'img'], en_paso=en_paso,
                    ))
                continue
            if etiqueta == 'table':
                cerrar_pendiente()
                if self.politica['tablas']:
                    bloque = self._tabla_desde(nodo)
                    if bloque is not None:
                        resultado.append(bloque)
                else:
                    for seccion in nodo.hijos:
                        resultado.extend(self._bloques(seccion.hijos, en_paso=en_paso))
                continue
            if etiqueta in {'h4', 'h5'}:
                cerrar_pendiente()
                hijos = self._inline(nodo.hijos, permitir_br=False)
                if hijos:
                    nuevo = Nodo(etiqueta if self.politica['titulos'] else 'p')
                    nuevo.hijos = hijos
                    resultado.append(nuevo)
                continue
            if etiqueta in {'ul', 'ol'}:
                cerrar_pendiente()
                lista = self._lista(nodo, etiqueta)
                if lista is not None:
                    resultado.append(lista)
                continue
            if etiqueta == 'li':
                # Un <li> suelto (sin lista): se trata como parrafo.
                cerrar_pendiente()
                resultado.extend(self._bloques(nodo.hijos, en_paso=en_paso))
                continue
            if etiqueta in {'p', 'div', 'section', 'article', 'blockquote', 'pre', 'header', 'footer', 'main', 'aside', 'nav', 'center', 'dl', 'dt', 'dd', 'address', 'tbody', 'thead', 'tr', 'td', 'th', 'hr'}:
                cerrar_pendiente()
                if etiqueta == 'hr':
                    continue
                hijos = nodo.hijos
                if etiqueta == 'p' and all(
                    hijo.es_texto or MAPA_ETIQUETAS.get(hijo.etiqueta, hijo.etiqueta) in INLINE
                    or hijo.etiqueta in {'span', 'font', 'u', 's', 'sub', 'sup', 'code', 'small', 'mark'}
                    for hijo in hijos
                ):
                    contenido = self._inline(hijos)
                    if contenido:
                        parrafo = Nodo('p')
                        parrafo.hijos = contenido
                        resultado.append(parrafo)
                    continue
                resultado.extend(self._bloques(hijos, en_paso=en_paso))
                continue
            # Etiqueta desconocida: se desenvuelve.
            resultado.extend(self._bloques(nodo.hijos, en_paso=en_paso))
        cerrar_pendiente()
        return resultado

    def _lista(self, nodo, etiqueta):
        lista = Nodo(etiqueta)
        sueltos = []
        for hijo in nodo.hijos:
            if hijo.es_texto or hijo.etiqueta != 'li':
                sueltos.append(hijo)
                continue
            if sueltos:
                self._agregar_item(lista, sueltos)
                sueltos = []
            self._agregar_item(lista, hijo.hijos)
        if sueltos:
            self._agregar_item(lista, sueltos)
        return lista if lista.hijos else None

    def _agregar_item(self, lista, hijos):
        item = Nodo('li')
        pendiente = []
        for hijo in hijos:
            if not hijo.es_texto and hijo.etiqueta in {'ul', 'ol'}:
                item.hijos.extend(self._inline(pendiente))
                pendiente = []
                sublista = self._lista(hijo, hijo.etiqueta)
                if sublista is not None:
                    item.hijos.append(sublista)
            elif not hijo.es_texto and hijo.etiqueta in {'p', 'div'}:
                # Varios parrafos en un item de lista: se separan con salto de linea.
                if pendiente and self._inline(pendiente):
                    pendiente.append(Nodo('br'))
                pendiente.extend(hijo.hijos)
            else:
                pendiente.append(hijo)
        item.hijos.extend(self._inline(pendiente))
        item.hijos = self._recortar(item.hijos)
        if item.hijos:
            lista.hijos.append(item)

    def _pasos(self, nodos):
        """Procedimiento: cada paso es un <li> con sus propios bloques."""
        pasos = Nodo('ol', {'class': 'guide-steps'})
        for nodo in nodos:
            if nodo.es_texto:
                if nodo.texto.strip():
                    self._agregar_paso(pasos, [nodo])
                continue
            if nodo.etiqueta in {'ol', 'ul'}:
                for hijo in nodo.hijos:
                    if hijo.etiqueta == 'li':
                        self._agregar_paso(pasos, hijo.hijos)
                    elif not hijo.es_texto or hijo.texto.strip():
                        self._agregar_paso(pasos, [hijo])
                continue
            self._agregar_paso(pasos, [nodo])
        return pasos

    def _agregar_paso(self, pasos, hijos):
        bloques = self._bloques(hijos, en_paso=True)
        if not bloques:
            return
        paso = Nodo('li')
        paso.hijos = bloques
        pasos.hijos.append(paso)

    def sanear(self, html):
        raiz = analizar(html)
        if self.es_pasos:
            pasos = self._pasos(raiz.hijos)
            return serializar([pasos]) if pasos.hijos else ''
        return serializar(self._bloques(raiz.hijos))


def _buscar(nodo, etiqueta):
    """Primer descendiente con la etiqueta indicada."""
    for hijo in nodo.hijos:
        if hijo.es_texto:
            continue
        if hijo.etiqueta == etiqueta:
            return hijo
        encontrado = _buscar(hijo, etiqueta)
        if encontrado is not None:
            return encontrado
    return None


def serializar(nodos):
    """Árbol → HTML normalizado (texto y atributos escapados)."""
    partes = []
    for nodo in nodos:
        if nodo.es_texto:
            partes.append(escape(nodo.texto or '', quote=False))
            continue
        atributos = ''.join(
            f' {clave}="{escape(str(valor), quote=True)}"'
            for clave, valor in nodo.atributos.items()
            if valor or clave.startswith('data-')
        )
        if nodo.etiqueta in ETIQUETAS_VACIAS:
            partes.append(f'<{nodo.etiqueta}{atributos}>')
            continue
        partes.append(f'<{nodo.etiqueta}{atributos}>{serializar(nodo.hijos)}</{nodo.etiqueta}>')
    return ''.join(partes)


def sanear(html, politica='rico', figuras_permitidas=None):
    """HTML del editor → HTML acotado listo para guardar. Devuelve ``(html, avisos)``."""
    saneador = Saneador(politica, figuras_permitidas)
    return saneador.sanear(html), saneador.avisos


def sanear_campo(clave, html, figuras_permitidas=None):
    return sanear(html, POLITICA_POR_CAMPO.get(clave, 'rico'), figuras_permitidas)[0]


# ----------------------------------------------------------------- documento


def _markup_pdf(nodos):
    """Contenido en línea → marcado que entiende ``reportlab.platypus.Paragraph``."""
    partes = []
    for nodo in nodos:
        if nodo.es_texto:
            partes.append(escape_xml(nodo.texto or ''))
        elif nodo.etiqueta == 'br':
            partes.append('<br/>')
        elif nodo.etiqueta == 'strong':
            partes.append(f'<b>{_markup_pdf(nodo.hijos)}</b>')
        elif nodo.etiqueta == 'em':
            partes.append(f'<i>{_markup_pdf(nodo.hijos)}</i>')
        elif nodo.etiqueta == 'a':
            href = escape_xml(nodo.atributos.get('href', ''), {'"': '&quot;'})
            partes.append(f'<a href="{href}" color="#1a5b3f"><u>{_markup_pdf(nodo.hijos)}</u></a>')
        else:
            partes.append(_markup_pdf(nodo.hijos))
    return ''.join(partes)


def _pie(prefijo, numero, titulo, fuente=''):
    texto = f'{prefijo} {numero}.'
    if titulo:
        texto += f' {titulo}'
    if fuente:
        texto += f' Fuente: {fuente}'
    return texto


class DocumentoHtml:
    """Todos los apartados enriquecidos de una guía, numerados en orden de aparición.

    ``figuras`` es la lista de :func:`guia_contenido.figuras_de_guia`
    (``{"pk", "url", "ruta", "titulo"}``).
    """

    def __init__(self, contenido, figuras=None, *, formato_procedimiento='numerado'):
        self.contenido = contenido or {}
        self.figuras = {str(figura.get('pk')): figura for figura in (figuras or [])}
        self.formato_procedimiento = formato_procedimiento
        self.arboles = {}
        self.numeros_figura = {}
        self.numeros_tabla = {}
        contador = {'figura': 0, 'tabla': 0}
        for clave in CAMPOS_RICOS:
            valor = self.contenido.get(clave)
            if not isinstance(valor, str):
                valor = ''
            # También protege registros antiguos o importados fuera del editor.
            valor = sanear(valor, POLITICA_POR_CAMPO.get(clave, 'rico'))[0]
            arbol = analizar(valor).hijos
            self.arboles[clave] = arbol
            self._numerar(arbol, contador)

    def _numerar(self, nodos, contador):
        for nodo in nodos:
            if nodo.es_texto:
                continue
            if nodo.etiqueta == 'figure':
                clases = (nodo.atributos.get('class') or '').split()
                if 'guide-table' in clases:
                    contador['tabla'] += 1
                    self.numeros_tabla[id(nodo)] = contador['tabla']
                elif nodo.atributos.get('data-figura'):
                    contador['figura'] += 1
                    self.numeros_figura[id(nodo)] = contador['figura']
            self._numerar(nodo.hijos, contador)

    # -- HTML de presentacion ------------------------------------------------
    def html(self, clave, *, edicion=False):
        """HTML listo para la vista o para las zonas del editor (imágenes resueltas)."""
        arbol = self.arboles.get(clave, [])
        if clave == 'procedimiento' and not edicion and self.formato_procedimiento == 'vinetas':
            return self._render(arbol, lista_pasos='ul')
        return self._render(arbol)

    def _render(self, nodos, lista_pasos='ol'):
        partes = []
        for nodo in nodos:
            if nodo.es_texto:
                partes.append(escape(nodo.texto or '', quote=False))
                continue
            etiqueta = nodo.etiqueta
            if etiqueta == 'figure':
                partes.append(self._render_figure(nodo))
                continue
            if etiqueta == 'ol' and 'guide-steps' in (nodo.atributos.get('class') or '').split():
                etiqueta = lista_pasos
                partes.append(f'<{etiqueta} class="guide-steps">{self._render(nodo.hijos)}</{etiqueta}>')
                continue
            if etiqueta in ETIQUETAS_VACIAS:
                partes.append(f'<{etiqueta}>')
                continue
            atributos = ''.join(
                f' {clave}="{escape(str(valor), quote=True)}"'
                for clave, valor in nodo.atributos.items()
                if valor
            )
            partes.append(f'<{etiqueta}{atributos}>{self._render(nodo.hijos)}</{etiqueta}>')
        return ''.join(partes)

    def _render_figure(self, nodo):
        clases = (nodo.atributos.get('class') or '').split()
        titulo = nodo.atributos.get('data-titulo') or ''
        if 'guide-table' in clases:
            numero = self.numeros_tabla.get(id(nodo), 0)
            tabla = next((hijo for hijo in nodo.hijos if hijo.etiqueta == 'table'), None)
            filas = [fila for fila in (tabla.hijos if tabla else []) if fila.etiqueta == 'tr']
            cabecera = nodo.atributos.get('data-cabecera') == '1'
            html_filas = []
            for posicion, fila in enumerate(filas):
                etiqueta = 'th' if cabecera and posicion == 0 else 'td'
                celdas = ''.join(
                    f'<{etiqueta}>{self._render(celda.hijos)}</{etiqueta}>' for celda in fila.hijos
                )
                html_filas.append(f'<tr>{celdas}</tr>')
            cuerpo = ''.join(html_filas[1:]) if cabecera else ''.join(html_filas)
            cabeza = f'<thead>{html_filas[0]}</thead>' if cabecera and html_filas else ''
            return (
                f'<figure class="guide-table" data-titulo="{escape(titulo, quote=True)}" '
                f'data-cabecera="{"1" if cabecera else "0"}">'
                f'<figcaption>{escape(_pie("Tabla", numero, titulo))}</figcaption>'
                f'<div class="guide-table-wrap"><table class="guide-table__grid">'
                f'{cabeza}<tbody>{cuerpo}</tbody></table></div></figure>'
            )
        identificador = nodo.atributos.get('data-figura') or ''
        figura = self.figuras.get(identificador)
        numero = self.numeros_figura.get(id(nodo), 0)
        fuente = nodo.atributos.get('data-fuente') or ''
        tamano = nodo.atributos.get('data-tamano') or 'mediana'
        pie = escape(_pie('Figura', numero, titulo, fuente))
        if not figura or not figura.get('url'):
            return f'<p class="guide-figure guide-figure--missing">[{pie}: imagen no disponible]</p>'
        return (
            f'<figure class="guide-figure is-{tamano}" data-figura="{escape(identificador, quote=True)}" '
            f'data-titulo="{escape(titulo, quote=True)}" data-fuente="{escape(fuente, quote=True)}" '
            f'data-tamano="{tamano}">'
            f'<img src="{escape(figura["url"], quote=True)}" alt="{escape(titulo or f"Figura {numero}", quote=True)}">'
            f'<figcaption>{pie}</figcaption></figure>'
        )

    # -- bloques para el PDF -------------------------------------------------
    def bloques(self, clave):
        return self._bloques(self.arboles.get(clave, []))

    def _bloques(self, nodos):
        bloques = []
        for nodo in nodos:
            if nodo.es_texto:
                if nodo.texto.strip():
                    bloques.append({'tipo': 'parrafo', 'html': escape_xml(nodo.texto.strip())})
                continue
            etiqueta = nodo.etiqueta
            if etiqueta == 'p':
                bloques.append({'tipo': 'parrafo', 'html': _markup_pdf(nodo.hijos)})
            elif etiqueta == 'h4':
                bloques.append({'tipo': 'subtitulo', 'html': _markup_pdf(nodo.hijos)})
            elif etiqueta == 'h5':
                bloques.append({'tipo': 'subapartado', 'html': _markup_pdf(nodo.hijos)})
            elif etiqueta in {'ul', 'ol'}:
                if 'guide-steps' in (nodo.atributos.get('class') or '').split():
                    for paso in nodo.hijos:
                        if paso.etiqueta == 'li':
                            bloques.append({'tipo': 'paso', 'bloques': self._bloques(paso.hijos)})
                    continue
                bloques.append({'tipo': 'lista', 'ordenada': etiqueta == 'ol', 'items': self._items(nodo)})
            elif etiqueta == 'figure':
                bloques.append(self._bloque_figure(nodo))
            else:
                bloques.extend(self._bloques(nodo.hijos))
        return bloques

    def _items(self, lista):
        items = []
        for item in lista.hijos:
            if item.etiqueta != 'li':
                continue
            sublistas = [hijo for hijo in item.hijos if hijo.etiqueta in {'ul', 'ol'}]
            propios = [hijo for hijo in item.hijos if hijo.etiqueta not in {'ul', 'ol'}]
            items.append({
                'html': _markup_pdf(propios),
                'sub': [
                    {'ordenada': sub.etiqueta == 'ol', 'items': self._items(sub)} for sub in sublistas
                ],
            })
        return items

    def _bloque_figure(self, nodo):
        clases = (nodo.atributos.get('class') or '').split()
        titulo = nodo.atributos.get('data-titulo') or ''
        if 'guide-table' in clases:
            tabla = next((hijo for hijo in nodo.hijos if hijo.etiqueta == 'table'), None)
            filas = [
                [_markup_pdf(celda.hijos) for celda in fila.hijos]
                for fila in (tabla.hijos if tabla else []) if fila.etiqueta == 'tr'
            ]
            return {
                'tipo': 'tabla',
                'filas': filas,
                'cabecera': nodo.atributos.get('data-cabecera') == '1',
                'titulo': _pie('Tabla', self.numeros_tabla.get(id(nodo), 0), titulo),
            }
        figura = self.figuras.get(nodo.atributos.get('data-figura') or '') or {}
        return {
            'tipo': 'imagen',
            'ruta': figura.get('ruta'),
            'url': figura.get('url', ''),
            'tamano': nodo.atributos.get('data-tamano') or 'mediana',
            'titulo': _pie(
                'Figura', self.numeros_figura.get(id(nodo), 0), titulo,
                nodo.atributos.get('data-fuente') or '',
            ),
        }

    def tiene_adjuntos(self, clave):
        return any(
            bloque['tipo'] in {'tabla', 'imagen'}
            or (bloque['tipo'] == 'paso' and any(sub['tipo'] in {'tabla', 'imagen'} for sub in bloque['bloques']))
            for bloque in self.bloques(clave)
        )

    def vacio(self, clave):
        return not texto_plano(self.contenido.get(clave) or '')


def bloques_de_html(html):
    """Bloques para el PDF de un fragmento HTML acotado suelto (sin numeración global).

    Lo usan documentos distintos de la guía (planificación e informe del
    expediente) que reutilizan el mismo editor y el mismo saneado.
    """
    documento = DocumentoHtml({})
    arbol = analizar(sanear(html or '', 'rico')[0]).hijos
    documento._numerar(arbol, {'figura': 0, 'tabla': 0})
    return documento._bloques(arbol)


# ----------------------------------------------------- formato anterior → HTML


def _p(texto):
    return f'<p>{escape(texto, quote=False)}</p>'


def _html_bloques_legado(bloques, figuras):
    """Bloques de ``guia_contenido.bloques_enriquecidos`` → HTML acotado."""
    partes = []
    for bloque in bloques:
        tipo = bloque.get('tipo')
        if tipo == 'parrafo':
            partes.append(_p(bloque['texto']))
        elif tipo == 'subtitulo':
            partes.append(f'<h4>{escape(bloque["texto"], quote=False)}</h4>')
        elif tipo == 'lista':
            etiqueta = 'ol' if bloque['ordenada'] else 'ul'
            items = ''.join(f'<li>{escape(item, quote=False)}</li>' for item in bloque['items'])
            partes.append(f'<{etiqueta}>{items}</{etiqueta}>')
        elif tipo == 'tabla':
            filas = bloque['filas']
            ancho = max(len(fila) for fila in filas)
            html_filas = ''.join(
                '<tr>' + ''.join(
                    f'<td>{escape(celda, quote=False)}</td>'
                    for celda in list(fila) + [''] * (ancho - len(fila))
                ) + '</tr>'
                for fila in filas
            )
            partes.append(
                f'<figure class="guide-table" data-titulo="" data-cabecera="1"><table>{html_filas}</table></figure>'
            )
        elif tipo == 'imagen':
            fuente = str(bloque.get('fuente') or '')
            numero = re.fullmatch(r'figura:(\d+)', fuente.lower())
            figura = None
            if numero:
                posicion = int(numero.group(1))
                figura = next((item for item in figuras or [] if int(item.get('n') or 0) == posicion), None)
            titulo = re.sub(r'^Figura\s+\d+\s*:\s*', '', bloque.get('texto') or '', flags=re.IGNORECASE).strip()
            if figura and figura.get('pk'):
                partes.append(
                    f'<figure class="guide-figure" data-figura="{figura["pk"]}" '
                    f'data-titulo="{escape(titulo or figura.get("titulo") or "", quote=True)}" '
                    'data-fuente="" data-tamano="mediana"></figure>'
                )
            elif re.match(r'^https?://', fuente, re.IGNORECASE):
                # Las imagenes externas no se descargan: queda el enlace.
                partes.append(
                    f'<p><a href="{escape(fuente, quote=True)}" target="_blank" rel="noopener">'
                    f'{escape(titulo or "Imagen externa", quote=False)}</a></p>'
                )
            elif titulo:
                partes.append(_p(f'[{titulo}: imagen no disponible]'))
    return ''.join(partes)


def html_desde_legado(contenido, figuras=None):
    """Guía en formato de texto → apartados en HTML acotado, sin tocar el original.

    Devuelve ``{clave: html}`` para ``CAMPOS_RICOS``. Las figuras se resuelven
    por su posición (``figura:N`` → imagen N) al identificador estable.
    """
    from apps.reservas.presentation.guia_contenido import bloques_enriquecidos, pasos_procedimiento

    contenido = contenido or {}
    resultado = {}
    for clave in CAMPOS_RICOS:
        if clave == 'procedimiento':
            continue
        valor = contenido.get(clave)
        if isinstance(valor, (list, tuple)):
            valor = '\n'.join(str(item) for item in valor)
        valor = str(valor or '')
        if POLITICA_POR_CAMPO.get(clave) == 'texto' and not re.search(r'^\s*(?:#{2,3}\s|\||!\[)', valor, re.MULTILINE):
            # Apartados de lineas: cada linea es un elemento de lista si son varias.
            lineas = [re.sub(r'^\s*(?:\d+[.)]|[-*•])\s*', '', linea).strip() for linea in valor.splitlines()]
            lineas = [linea for linea in lineas if linea]
            if len(lineas) > 1:
                resultado[clave] = '<ul>' + ''.join(f'<li>{escape(linea, quote=False)}</li>' for linea in lineas) + '</ul>'
            else:
                resultado[clave] = _p(lineas[0]) if lineas else ''
            continue
        resultado[clave] = _html_bloques_legado(bloques_enriquecidos(valor), figuras)
    formato = contenido.get('formato_procedimiento') or 'numerado'
    pasos = pasos_procedimiento(contenido.get('procedimiento') or [], formato)
    if formato == 'parrafos':
        resultado['procedimiento'] = _html_bloques_legado(pasos, figuras)
    else:
        items = []
        for paso in pasos:
            cuerpo = (_p(paso['texto']) if paso.get('texto') else '') + _html_bloques_legado(paso.get('adjuntos') or [], figuras)
            if cuerpo:
                items.append(f'<li>{cuerpo}</li>')
        resultado['procedimiento'] = f'<ol class="guide-steps">{"".join(items)}</ol>' if items else ''
    return resultado


def texto_a_html(texto, politica='rico'):
    """Texto plano (sugerencias, mini-lenguaje) → HTML acotado del apartado."""
    from apps.reservas.presentation.guia_contenido import bloques_enriquecidos

    texto = str(texto or '')
    if politica == 'texto':
        lineas = [re.sub(r'^\s*(?:\d+[.)]|[-*•])\s*', '', linea).strip() for linea in texto.splitlines()]
        lineas = [linea for linea in lineas if linea]
        if len(lineas) > 1:
            return '<ul>' + ''.join(f'<li>{escape(linea, quote=False)}</li>' for linea in lineas) + '</ul>'
        return _p(lineas[0]) if lineas else ''
    if politica == 'pasos':
        pasos = [re.sub(r'^\s*(?:\d+[.)]|[-*•])\s*', '', linea).strip() for linea in texto.splitlines()]
        pasos = [paso for paso in pasos if paso]
        return '<ol class="guide-steps">' + ''.join(f'<li>{_p(paso)}</li>' for paso in pasos) + '</ol>' if pasos else ''
    return _html_bloques_legado(bloques_enriquecidos(texto), [])
