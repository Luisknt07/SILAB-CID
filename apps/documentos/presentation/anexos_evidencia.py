"""Anexos del informe semestral: el formato de registro común y qué módulo arma cada anexo.

Un anexo recoge los datos del período; no es un informe. El análisis (avance, estado de cada
meta y lo que falta para cumplirla) está en el informe semestral. La estructura completa, con
las tablas y columnas de cada anexo por tipo de unidad, está en
``docs/estructura-anexos-por-tipo-de-unidad.md``.

Todos los anexos llevan:

- el encabezado institucional de tres columnas;
- un cuadro de datos generales: unidad, período, informe al que acompaña y número de anexo,
  fecha de los datos, responsable, exigencia que responde, metas que respalda y fuente;
- una tabla por registro, numerada «n.m», con su nombre en la primera fila, sus columnas y
  el total al pie.

No llevan apartados ni párrafos. Cada anexo presenta todos los registros del período, en
cualquier estado; los anulados no se presentan. Cada dato tiene un anexo dueño y los demás
lo citan por su código.

Este módulo es el motor. Los registros de cada anexo los arman los módulos
``anexos_recursos``, ``anexos_practicas``, ``anexos_seguridad``, ``anexos_resultados`` y
``anexos_propios``; cada constructor recibe un :class:`Contexto` y devuelve una lista de
:class:`Registro`.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from importlib import import_module
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

# Anexos comunes, en el orden de la universidad. Código: (nombre por omisión, metas que respalda).
ANEXOS = {
    'REGISTRO-USO': ('Registros de uso de la unidad', ('USO', 'USO-EFECTIVO')),
    'EQUIPAMIENTO': ('Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad',
                     ('MANTENIMIENTO',)),
    'INVENTARIO-CORTE': ('Inventario de equipamiento, reactivos e insumos', ('INVENTARIO',)),
    'FICHAS-TECNICAS': ('Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados', ()),
    'PRACTICAS-FT02': ('Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable', ('PRACTICAS-PLAN',)),
    'GUIAS': ('Guías de prácticas aprobadas y vinculadas con los contenidos del syllabus', ('GUIAS',)),
    'PRACTICAS-FT03': ('Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados', ('PRACTICAS',)),
    'INDUCCION-SEGURIDAD': ('Reportes de seguridad y condiciones de operación', ('SEGURIDAD', 'INSPECCIONES')),
    'DESECHOS': ('Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable', ('DESECHOS',)),
    'INVESTIGACION': ('Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros', ('INVESTIGACION',)),
    'TRANSFERENCIA': ('Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad',
                      ('TRANSFERENCIA', 'SERVICIOS')),
}
# Anexos propios de planta piloto, centro experimental y observatorio.
ANEXOS_PERFIL = {
    'PP-PRODUCCION': ('Producción de la planta piloto: órdenes, lotes y entregas', ('PRODUCCION',)),
    'PP-CALIDAD': ('Control de calidad de la planta piloto: controles y no conformidades', ('CONTROL-CALIDAD',)),
    'CE-ENSAYOS': ('Ensayos y parcelas experimentales', ('ENSAYOS',)),
    'CE-PRODUCCION': ('Producción agropecuaria: ciclos, labores, sanidad y cosechas', ()),
    'OBS-DATOS': ('Datos del observatorio: fuentes, metodología y actualización de indicadores',
                  ('DATOS-ACTUALIZADOS',)),
    'OBS-BOLETINES': ('Publicaciones del observatorio: boletines y calendario', ('BOLETINES',)),
    'OBS-EVENTOS': ('Socialización del observatorio: eventos y participantes', ('EVENTOS',)),
}
# La redacción de la universidad a la que responde cada anexo común.
EXIGENCIAS = {
    'REGISTRO-USO': 'Planificación y registros de uso de laboratorios.',
    'EQUIPAMIENTO': 'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad.',
    'INVENTARIO-CORTE': 'Inventario de equipamiento, reactivos e insumos.',
    'FICHAS-TECNICAS': 'Inventario o ficha técnica de laboratorios, talleres, software, simuladores y espacios '
                       'utilizados.',
    'PRACTICAS-FT02': 'Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y '
                      'responsable.',
    'GUIAS': 'Guías de prácticas de laboratorio, aprobadas y vinculadas con los contenidos del syllabus.',
    'PRACTICAS-FT03': 'Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, '
                      'informes de estudiantes y productos desarrollados.',
    'INDUCCION-SEGURIDAD': 'Protocolos de bioseguridad y reportes de seguridad y condiciones de operación.',
    'DESECHOS': 'Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable.',
    'INVESTIGACION': 'Informes de resultados de investigación aplicada y desarrollo tecnológico generados en '
                     'laboratorios y centros.',
    'TRANSFERENCIA': 'Informes de transferencia de conocimiento, tecnología y prestación de servicios '
                     'especializados a la sociedad.',
}
# Quién arma cada anexo: «módulo:función» dentro de apps.documentos.presentation.
CONSTRUCTORES = {
    'REGISTRO-USO': 'anexos_recursos:uso',
    'EQUIPAMIENTO': 'anexos_recursos:mantenimiento',
    'INVENTARIO-CORTE': 'anexos_recursos:inventario',
    'FICHAS-TECNICAS': 'anexos_recursos:fichas',
    'PRACTICAS-FT02': 'anexos_practicas:planificacion',
    'GUIAS': 'anexos_practicas:guias',
    'PRACTICAS-FT03': 'anexos_practicas:evidencias',
    'INDUCCION-SEGURIDAD': 'anexos_seguridad:seguridad',
    'DESECHOS': 'anexos_seguridad:desechos',
    'INVESTIGACION': 'anexos_resultados:investigacion',
    'TRANSFERENCIA': 'anexos_resultados:transferencia',
    'PP-PRODUCCION': 'anexos_propios:produccion_planta',
    'PP-CALIDAD': 'anexos_propios:calidad_planta',
    'CE-ENSAYOS': 'anexos_propios:ensayos',
    'CE-PRODUCCION': 'anexos_propios:produccion_agropecuaria',
    'OBS-DATOS': 'anexos_propios:datos_observatorio',
    'OBS-BOLETINES': 'anexos_propios:publicaciones_observatorio',
    'OBS-EVENTOS': 'anexos_propios:socializacion_observatorio',
}
# El orden en que se numeran: comunes, propios y, al final, los condicionales.
ORDEN = ('REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS', 'PRACTICAS-FT02', 'GUIAS',
         'PRACTICAS-FT03', 'INDUCCION-SEGURIDAD', 'PP-PRODUCCION', 'PP-CALIDAD', 'CE-ENSAYOS', 'CE-PRODUCCION',
         'OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS', 'DESECHOS', 'INVESTIGACION', 'TRANSFERENCIA')

# Se presentan solo cuando aplican; si no, conservan su número y el informe los lista como «No aplica».
CONDICIONALES = frozenset(('DESECHOS', 'INVESTIGACION', 'TRANSFERENCIA'))
MOTIVOS_NO_APLICA = {
    'DESECHOS': ('La planificación del período no compromete la gestión de desechos, la unidad no registró '
                 'desechos peligrosos ni especiales y su inventario no tiene reactivos, agroquímicos ni '
                 'medicamentos veterinarios; este anexo no se presenta.'),
    'INVESTIGACION': 'La planificación del período no compromete metas de investigación; este anexo no se presenta.',
    'TRANSFERENCIA': ('La planificación del período no compromete metas de transferencia ni de servicios y no hubo '
                      'servicios atendidos; este anexo no se presenta.'),
}
# Se conserva el nombre para quien lo importaba antes de que hubiera un motivo por anexo.
NO_COMPROMETIDO = MOTIVOS_NO_APLICA['INVESTIGACION']
FUENTE = ('Registros de la plataforma al corte. Cada dato se presenta en un solo anexo; los demás lo citan por '
          'su código.')

TIPOS_DE_UNIDAD = {'laboratorios': 'Laboratorio', 'plantas_piloto': 'Planta piloto',
                   'centro_experimental': 'Centro experimental', 'observatorios': 'Observatorio'}
MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre')
LARGO_MAXIMO = 300  # Una celda nunca ocupa más que una página.
COLUMNAS_MAXIMAS = 9  # En la hoja apaisada, con letra de 8,5 pt.
# Una imagen va en miniatura dentro de su celda; el archivo completo se abre con el enlace.
MINIATURA_ANCHO = 45 * 72 / 25.4  # 45 mm, en puntos
MINIATURA_ALTO = 34 * 72 / 25.4  # 34 mm
MINIATURA_LADO = 700  # Píxeles del lado mayor de la copia que se incrusta, para que el PDF no pese.
MINIATURA_CALIDAD = 70
EXTENSIONES_DE_IMAGEN = ('.png', '.jpg', '.jpeg', '.webp')
FORMATOS_DE_IMAGEN = ('PNG', 'JPEG', 'MPO', 'WEBP')
PESO_MAXIMO_DE_IMAGEN = 25 * 1024 * 1024


# -- piezas de una tabla -----------------------------------------------------------------

@dataclass
class Registro:
    """Una tabla del anexo: su nombre va en la primera fila y el total al pie."""
    titulo: str
    cabecera: tuple
    filas: list = field(default_factory=list)  # Listas de celdas; una fila puede ser un Grupo.
    pesos: tuple = ()
    total: str | None = ''  # '' pone el total por omisión; None, ninguno.
    suma: list | None = None  # Fila de totales alineada con las columnas.
    vacio: str = 'Sin registros en el período.'
    ficha: bool = False  # Dos columnas «dato / valor», sin fila de títulos.


@dataclass
class Enlace:
    """Un archivo o una dirección: se muestra el texto, nunca la URL entera."""
    texto: str
    url: str


@dataclass
class Par:
    """Celda de dos líneas: el dato principal y, debajo y más pequeño, el que lo acompaña."""
    principal: object
    secundario: object = ''


@dataclass
class Imagen:
    """Una fotografía o una captura: va en miniatura y, debajo, el enlace para abrirla completa.

    ``archivo`` es un archivo guardado (FileField), una ruta o el contenido en bytes. Si no se
    puede abrir como imagen, la celda queda con el enlace y el pie: nunca detiene el anexo.
    """
    archivo: object
    enlace: object = None
    pie: str = ''
    _copia: object = field(default=None, init=False, repr=False, compare=False)

    def copia(self):
        """La copia reducida que se incrusta: (JPEG, ancho, alto) en píxeles; ``None`` si no se pudo abrir."""
        if self._copia is None:
            self._copia = _copia_reducida(self.archivo) or ()
        return self._copia or None

    def medida(self, ancho=MINIATURA_ANCHO, alto=MINIATURA_ALTO):
        """Ancho y alto con que se dibuja, en puntos: cabe en el recuadro sin deformarse ni ampliarse."""
        if not self.copia():
            return 0, 0
        _contenido, pixeles_ancho, pixeles_alto = self.copia()
        escala = min(ancho / pixeles_ancho, alto / pixeles_alto, 1)
        return pixeles_ancho * escala, pixeles_alto * escala

    def sin_imagen(self):
        """La celda cuando la imagen no se puede mostrar: el enlace y, debajo, el pie."""
        return par(self.enlace or '—', self.pie)


@dataclass
class Grupo:
    """Fila de subtítulo que agrupa las filas siguientes (por ejemplo, una asignatura)."""
    texto: str


@dataclass
class Contexto:
    """Lo que recibe el constructor de un anexo."""
    documento: object
    unidad: object
    base: str  # laboratorios, plantas_piloto, centro_experimental u observatorios
    inicio: object
    fin: object
    corte: object  # El menor entre el fin del período y hoy.
    lectura: dict
    numero: int | None = None
    _reportes: dict = field(default_factory=dict)

    def reporte(self, categoria):
        """El reporte del Centro de reportes de esa categoría para la unidad y el período, una sola vez."""
        if categoria not in self._reportes:
            from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
            self._reportes[categoria] = _generic_report(categoria, self.unidad, self.inicio, self.fin)
        return self._reportes[categoria]

    @property
    def registros(self):
        """Los registros del período tal como los mide el informe (diagnósticos, coberturas, mediciones)."""
        return self.lectura['registros']


def es_anexo_de_evidencia(exigido):
    return exigido.codigo in ANEXOS or exigido.codigo in ANEXOS_PERFIL


def metas_del_anexo(codigo):
    return (ANEXOS.get(codigo) or ANEXOS_PERFIL[codigo])[1]


def orden_del_anexo(codigo):
    return ORDEN.index(codigo) if codigo in ORDEN else len(ORDEN)


# -- escritura de celdas -----------------------------------------------------------------

def cifra(valor, decimales=1):
    """Número con la escritura local: 1.250 y 65,2."""
    if valor is None or valor == '':
        return '—'
    try:
        numero = Decimal(str(valor).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return str(valor)
    if numero == numero.to_integral_value():
        return f'{int(numero):,}'.replace(',', '.')
    return f'{numero:,.{decimales}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def plural(cantidad, singular, plural_):
    return f'{cifra(cantidad)} {singular if cantidad == 1 else plural_}'


def texto(valor, largo=None):
    """Texto de una celda: sin saltos, con «—» si está vacío y recortado si es muy largo."""
    limpio = ' '.join(str(valor if valor not in (None, '') else '—').split())
    largo = min(largo or LARGO_MAXIMO, LARGO_MAXIMO)
    if len(limpio) > largo:
        limpio = limpio[:largo - 1].rstrip() + '…'
    return limpio


def fecha(valor, formato='%d/%m/%Y'):
    """Fecha local «dd/mm/aaaa»; acepta fechas y fechas con hora."""
    if not valor:
        return '—'
    if hasattr(valor, 'hour'):
        from django.utils import timezone
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)
    return valor.strftime(formato)


def hora(valor):
    return fecha(valor, '%H:%M')


def si_no(valor):
    return 'Sí' if valor else 'No'


def nombre_de(usuario):
    if not usuario:
        return '—'
    return (usuario.get_full_name() or usuario.get_username()).strip() or '—'


def par(principal, secundario=''):
    """Celda de dos líneas; si falta la segunda, queda de una."""
    secundario = '' if secundario in (None, '', '—') else secundario
    return Par(principal, secundario) if secundario != '' else principal


def enlace(direccion, rotulo='Abrir'):
    """Enlace a un archivo o dirección; «—» si no hay. Una ruta del sitio se vuelve dirección completa."""
    direccion = str(direccion or '').strip()
    if not direccion:
        return '—'
    if direccion.startswith('/'):
        from django.conf import settings
        direccion = settings.SITE_URL.rstrip('/') + direccion
    return Enlace(rotulo, direccion)


def enlace_archivo(archivo, rotulo='Abrir'):
    """Enlace a un archivo guardado (FileField); «—» si no hay archivo."""
    if not archivo or not getattr(archivo, 'name', ''):
        return '—'
    try:
        return enlace(archivo.url, rotulo)
    except ValueError:
        return '—'


def enlace_recurso(recurso, rotulo='Abrir'):
    """Enlace al recurso del gestor documental de la unidad."""
    if not recurso:
        return '—'
    from django.urls import reverse
    return enlace(reverse('recurso_unidad', args=[recurso.pk]), rotulo)


def imagen(archivo, enlace=None, pie=''):
    """Celda con la miniatura de un archivo guardado; si no es una imagen que se pueda abrir, el enlace y el pie.

    Solo se muestran PNG, JPG y WEBP. Un PDF, un documento, un video o un archivo que falta o
    está dañado quedan como estaban: con su enlace.
    """
    celda_de_imagen = Imagen(archivo, enlace, pie)
    nombre = str(archivo if isinstance(archivo, (str, Path)) else getattr(archivo, 'name', '') or '')
    if nombre.lower().endswith(EXTENSIONES_DE_IMAGEN) and celda_de_imagen.copia():
        return celda_de_imagen
    return celda_de_imagen.sin_imagen()


def _copia_reducida(archivo):
    """La imagen como JPEG pequeño, derecha según su orientación: (contenido, ancho, alto); ``None`` si no se abre."""
    try:
        from PIL import Image, ImageOps

        if isinstance(archivo, (bytes, bytearray)):
            contenido = bytes(archivo)
        elif isinstance(archivo, (str, Path)):
            with open(archivo, 'rb') as abierto:
                contenido = abierto.read(PESO_MAXIMO_DE_IMAGEN + 1)
        else:
            with archivo.open('rb') as abierto:
                contenido = abierto.read(PESO_MAXIMO_DE_IMAGEN + 1)
        if not contenido or len(contenido) > PESO_MAXIMO_DE_IMAGEN:
            return None
        with Image.open(BytesIO(contenido)) as original:
            if original.format not in FORMATOS_DE_IMAGEN:
                return None
            # Una fotografía de varios megapíxeles se decodifica ya reducida.
            original.draft('RGB', (MINIATURA_LADO, MINIATURA_LADO))
            copia = ImageOps.exif_transpose(original)
            copia.thumbnail((MINIATURA_LADO, MINIATURA_LADO))
            if copia.mode in ('RGBA', 'LA', 'PA') or 'transparency' in copia.info:
                # El JPEG no tiene transparencia: la imagen se asienta sobre blanco.
                copia = copia.convert('RGBA')
                fondo = Image.new('RGB', copia.size, 'white')
                fondo.paste(copia, mask=copia.getchannel('A'))
                copia = fondo
            else:
                copia = copia.convert('RGB')
            salida = BytesIO()
            copia.save(salida, 'JPEG', quality=MINIATURA_CALIDAD, optimize=True)
            return salida.getvalue(), copia.width, copia.height
    except Exception:  # Un archivo ausente, dañado o desmesurado deja el enlace; el anexo se genera igual.
        return None


def celda(valor):
    """Texto de la celda; una dirección se vuelve un enlace corto en lugar de la URL entera."""
    limpio = str(valor or '').strip()
    if limpio.startswith(('http://', 'https://')) and ' ' not in limpio:
        return Enlace('Abrir enlace', limpio)
    if limpio.startswith('/') and ' ' not in limpio:
        return enlace(limpio, 'Abrir archivo')
    return texto(valor)


def mes(clave):
    anio, numero = str(clave).split('-')[:2]
    return f'{MESES[int(numero) - 1].capitalize()} {anio}'


def faltan(faltantes, cortos=None):
    """«Completo» o «Falta: …», con cada requisito en una o dos palabras."""
    cortos = cortos or {}
    lista = []
    for requisito in faltantes or ():
        corto = cortos.get(str(requisito).strip(), str(requisito).strip().lower())
        if corto and corto not in lista:
            lista.append(corto)
    return 'Completo' if not lista else 'Falta: ' + ', '.join(lista)


def tabla_del_reporte(reporte, titulo):
    """Las filas (como diccionarios) de la tabla del reporte cuyo título empieza por ``titulo``."""
    for tabla in reporte.get('tablas') or ():
        if str(tabla.get('titulo', '')).startswith(titulo):
            return [dict(zip(tabla.get('headers') or (), fila)) for fila in tabla.get('rows') or ()]
    return []


def filas_del_reporte(reporte):
    return [dict(zip(reporte.get('headers') or (), fila)) for fila in reporte.get('rows') or ()]


def vigentes(filas, columna='Estado documental'):
    """Sin los registros anulados: el Centro de reportes los conserva visibles, el anexo no los presenta."""
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    anulado = dict(EvidenciaGestionUnidad.ESTADOS)['anulado']
    return [fila for fila in filas if str(fila.get(columna, '')).strip() != anulado]


_vigentes = vigentes


def evidencias_de_gestion(unidad, tipo, inicio, fin):
    """Evidencias de gestión del tipo dado en el período, sin las anuladas, por fecha."""
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    return list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=tipo, fecha__range=(inicio, fin))
                .exclude(estado='anulado').select_related('responsable', 'recurso', 'validado_por')
                .order_by('fecha', 'pk'))


def verificacion(evidencia):
    """Estado de una evidencia de gestión en palabras: verificada, borrador o demostración."""
    if evidencia.demostracion:
        return 'Demostración; no acredita'
    return evidencia.get_estado_display()


def total_con_respaldo(filas, sustantivo=('registro', 'registros')):
    datos = [fila for fila in filas if not isinstance(fila, Grupo)]
    completos = sum(_texto_de(fila[-1]) == 'Completo' for fila in datos)
    return f'Total: {plural(len(datos), *sustantivo)} · con respaldo completo: {cifra(completos)}'


# -- anchos de columna -------------------------------------------------------------------

def _texto_de(valor):
    """El texto más largo que ocupa una línea de la celda, para medir su ancho habitual."""
    return max(_lineas_de(valor), key=len)


def _lineas_de(valor):
    """Las líneas de texto de una celda: una, o dos si es un :class:`Par`."""
    if isinstance(valor, Enlace):
        return [valor.texto]
    if isinstance(valor, Par):
        return _lineas_de(valor.principal) + _lineas_de(valor.secundario)
    if isinstance(valor, Imagen):
        # Lo que va escrito debajo de la miniatura; el ancho de esta lo da :func:`_ancho_de_imagen`.
        return _lineas_de(valor.sin_imagen())
    return [str(valor)]


def _ancho_de_imagen(valor):
    """El ancho, en puntos, de la miniatura de la celda; cero si la celda no lleva imagen."""
    return valor.medida()[0] if isinstance(valor, Imagen) else 0


def _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano):
    """Por columna: lo mínimo para no partir palabras y lo que pide su texto habitual, en puntos."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    relleno = 11  # márgenes internos de la celda
    filas = [fila for fila in filas if not isinstance(fila, Grupo)]
    minimos, deseados = [], []
    for i, titulo in enumerate(cabecera):
        textos = [_texto_de(fila[i]) for fila in filas]
        # La palabra más larga de cualquiera de las dos líneas: un código largo no se parte.
        palabra = max((stringWidth(p, regular, tamano) for fila in filas for t in _lineas_de(fila[i])
                       for p in t.split()), default=0)
        # Una miniatura tampoco se recorta: la columna le hace sitio como a una palabra larga.
        figura = max((_ancho_de_imagen(fila[i]) for fila in filas), default=0)
        minimo = max(max(stringWidth(p, negrita, tamano) for p in str(titulo).split() or ['']),
                     min(palabra, ancho * .22), figura) + relleno
        largos = sorted(stringWidth(t, regular, tamano) for t in textos) or [0]
        tipico = largos[int((len(largos) - 1) * .8)]
        minimos.append(minimo)
        deseados.append(max(minimo, min(tipico + relleno, ancho * .4)))
    return minimos, deseados


def _anchos_por_contenido(cabecera, filas, ancho, negrita, regular, tamano):
    """Ancho de cada columna, en puntos, según lo que suele llevar.

    Primero asegura que quepan enteras la palabra más larga del título y la del contenido (esta,
    hasta un tope); lo que sobra va a las columnas que llevan más texto.
    """
    minimos, deseados = _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano)
    if sum(minimos) >= ancho:
        return [ancho * m / sum(minimos) for m in minimos]
    if sum(deseados) <= ancho:
        return [d * ancho / sum(deseados) for d in deseados]
    holguras = [d - m for d, m in zip(deseados, minimos)]
    resto = ancho - sum(minimos)
    return [m + resto * h / sum(holguras) for m, h in zip(minimos, holguras)]


def _anchos_fijos(pesos, cabecera, filas, ancho, negrita, regular, tamano):
    """Los anchos pedidos, ensanchando la columna cuya palabra más larga no cabe.

    Lo que le falta a esa columna sale de las que tienen holgura, como un código largo sin
    espacios en una columna estrecha.
    """
    anchos = [ancho * p / sum(pesos) for p in pesos]
    minimos, _deseados = _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano)
    faltantes = sum(max(0, m - a) for a, m in zip(anchos, minimos))
    if not faltantes:
        return anchos
    holguras = [max(0, a - m) for a, m in zip(anchos, minimos)]
    if sum(holguras) <= faltantes:
        return [ancho * m / sum(minimos) for m in minimos]
    return [m if a < m else a - faltantes * h / sum(holguras) for a, m, h in zip(anchos, minimos, holguras)]


# -- las metas, con las cifras del informe ------------------------------------------------

_lecturas = ContextVar('lecturas_de_metas', default=None)


@contextmanager
def lecturas_compartidas():
    """Mientras dura, la lectura de metas de un mismo período se calcula una sola vez.

    Generar los anexos de un informe los arma uno tras otro con los mismos registros.
    """
    if _lecturas.get() is not None:
        yield
        return
    marca = _lecturas.set({})
    try:
        yield
    finally:
        _lecturas.reset(marca)


def lectura_de_metas(documento, inicio, fin):
    """Las metas del período medidas igual que en el informe: mismas funciones, mismas fuentes."""
    compartidas = _lecturas.get()
    clave = (documento.unidad_id, documento.anio, documento.corte, inicio, fin)
    if compartidas is not None and clave in compartidas:
        return compartidas[clave]
    from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
    from .evaluacion_cierre import evaluar_meta
    from .expediente_redaccion import filas_de_cumplimiento, registros_del_periodo

    registros = registros_del_periodo(documento.unidad, inicio, fin)
    informe = DocumentoExpediente.objects.filter(
        unidad=documento.unidad, anio=documento.anio, corte=documento.corte,
        exigido__codigo='INFORME-SEMESTRAL', mes__isnull=True).first()
    lectura = {'hay_plan': False, 'filas': {}, 'registros': registros, 'informe': informe,
               'unidad': documento.unidad, 'inicio': inicio, 'fin': fin}
    if informe is not None:
        redaccion = DocumentoElaborado.objects.filter(documento_id=informe.pk).first()
        datos = filas_de_cumplimiento(informe, redaccion.contenido if redaccion else {}, inicio, fin, registros)
        lectura['hay_plan'] = datos['hay_plan']
        lectura['filas'] = {f['codigo']: (f, evaluar_meta(f, registros)) for f in datos['todas']}
    if compartidas is not None:
        compartidas[clave] = lectura
    return lectura


def _compromete(codigo, lectura):
    return any(lectura['filas'].get(meta, ({}, None))[0].get('aplica', False) for meta in metas_del_anexo(codigo))


def _genera_desechos(unidad, inicio, fin):
    """La unidad registró desechos en el período o guarda reactivos, agroquímicos o medicamentos veterinarios."""
    from apps.recursos.models.consumibles import Consumible
    from apps.recursos.models.desechos import RegistroDesecho
    if RegistroDesecho.objects.filter(unidad=unidad, fecha_generacion__range=(inicio, fin)).exists():
        return True
    return Consumible.objects.filter(unidad=unidad, activo=True,
                                     clasificacion__in=('reactivo', 'agroquimico', 'veterinario')).exists()


def _hubo_servicios(unidad, inicio, fin):
    """Hubo servicios o solicitudes de información atendidos en el período."""
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS
    if (Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin), tipo_solicitud='servicio')
            .exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS).exists()):
        return True
    from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
    from apps.observatorios.operacion.models.observatorios import SolicitudDatos
    if (SolicitudFabricacion.objects.filter(unidad=unidad, fecha_solicitud__range=(inicio, fin))
            .exclude(estado='rechazada').exists()):
        return True
    return SolicitudDatos.objects.filter(unidad=unidad, estado='atendida',
                                         atendida__date__range=(inicio, fin)).exists()


def aplica_el_anexo(codigo, lectura):
    """Un anexo condicional se presenta solo cuando aplica (docs/estructura-anexos-por-tipo-de-unidad.md).

    - Investigación: si la planificación compromete su meta.
    - Transferencia y servicios: si la planificación los compromete o hubo servicios atendidos.
    - Desechos: si la planificación compromete su gestión, la unidad registró desechos o guarda
      reactivos, agroquímicos o medicamentos veterinarios.
    """
    if codigo not in CONDICIONALES:
        return True
    if _compromete(codigo, lectura):
        return True
    unidad, inicio, fin = lectura.get('unidad'), lectura.get('inicio'), lectura.get('fin')
    if codigo == 'INVESTIGACION' or unidad is None:
        return False
    if codigo == 'DESECHOS':
        return _genera_desechos(unidad, inicio, fin)
    return _hubo_servicios(unidad, inicio, fin)


def motivo_no_aplica(codigo):
    return MOTIVOS_NO_APLICA.get(codigo, 'Este anexo no aplica a la unidad en el período.')


def anexos_numerados(informe):
    """Los anexos del informe en su orden: [(número, documento)].

    Un anexo que no aplica conserva su número: el informe lo lista como «No aplica».
    """
    from .expediente import anexos_del
    if informe is None or not informe.pk or informe.exigido.codigo != 'INFORME-SEMESTRAL':
        return []
    anexos = [a for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.activo]
    return list(enumerate(anexos, 1))


def anexo_de_cada_meta(informe):
    """{código de meta: 'Anexo n'} según los anexos que el informe presenta."""
    from .evaluacion_cierre import ANEXOS_METAS
    resultado = {}
    for numero, anexo in anexos_numerados(informe):
        if anexo.estado == 'no_aplica':
            continue
        for meta in ANEXOS_METAS.get(anexo.exigido.codigo, ()):
            resultado.setdefault(meta, f'Anexo {numero}')
    return resultado


def numero_de_anexo(documento, informe):
    numero = next((n for n, anexo in anexos_numerados(informe) if anexo.pk == documento.pk), None)
    if numero is not None:
        return numero
    # Antes de habilitar el expediente el anexo no tiene fila: lleva el número que tendrá, su
    # posición entre los anexos que el expediente proyecta para ese período.
    from .expediente import leer_expediente
    proyectados = sorted(
        (d for d in leer_expediente(documento.unidad, documento.anio)
         if d.exigido.es_anexo and d.corte == documento.corte and not d.mes
         and d.exigido.anexo_de.codigo == 'INFORME-SEMESTRAL'),
        key=lambda d: (d.exigido.orden, d.exigido.codigo))
    return next((n for n, d in enumerate(proyectados, 1) if d.exigido_id == documento.exigido_id), None)


def con_respaldo(codigo, medido, registros):
    medicion = (registros.get('mediciones_porcentuales') or {}).get(codigo) or {}
    if medicion.get('denominador'):
        unidad = ' meses' if codigo == 'INSPECCIONES' else ''
        return f"{cifra(medicion.get('numerador'))} de {cifra(medicion['denominador'])}{unidad}"
    return cifra(medido.get('registrado'))


def metas_que_respalda(codigo, lectura):
    """Los nombres de las metas del anexo que la planificación compromete, como en el informe."""
    from .expediente_redaccion import ACTIVIDADES_PLAN
    catalogo = {a.codigo: a.nombre for a in ACTIVIDADES_PLAN}
    nombres = []
    for meta in metas_del_anexo(codigo):
        fila = lectura['filas'].get(meta, ({}, None))[0]
        if lectura['hay_plan'] and meta in lectura['filas'] and not fila.get('aplica', True):
            continue
        nombre = fila.get('nombre') or catalogo.get(meta)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
    return nombres


# -- composición -------------------------------------------------------------------------

def constructor_de(codigo):
    """La función que arma los registros del anexo."""
    modulo, funcion = CONSTRUCTORES[codigo].split(':')
    return getattr(import_module(f'apps.documentos.presentation.{modulo}'), funcion)


def contexto_del_anexo(documento, inicio, fin, lectura=None):
    from django.utils import timezone
    from .perfil_unidades import base_de

    lectura = lectura or lectura_de_metas(documento, inicio, fin)
    return Contexto(documento=documento, unidad=documento.unidad, base=base_de(documento.unidad), inicio=inicio,
                    fin=fin, corte=min(fin, timezone.localdate()), lectura=lectura,
                    numero=numero_de_anexo(documento, lectura.get('informe')))


def componer_anexo(documento, inicio, fin, lectura=None):
    """El anexo listo para dibujar: título, datos generales y registros."""
    codigo = documento.exigido.codigo
    contexto = contexto_del_anexo(documento, inicio, fin, lectura)
    por_omision = (ANEXOS.get(codigo) or ANEXOS_PERFIL[codigo])[0]
    # El nombre del catálogo para el tipo de unidad («Registros de uso de la planta piloto»), si lo tiene.
    titulo = documento.exigido.nombre_para(documento.unidad) or por_omision
    metas = metas_que_respalda(codigo, contexto.lectura)
    unidad = documento.unidad
    periodo = (f'{documento.anio}-{documento.corte} · del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}'
               if documento.corte else documento.etiqueta_corte)
    from .expediente import tramo_del_documento
    if (inicio, fin) != tuple(tramo_del_documento(documento)):
        # Consulta en otro rango: se dice, para que no se confunda con el anexo del período.
        periodo = f'Consulta del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y} · período {documento.etiqueta_corte}'
    cortos = [
        ('Unidad', unidad.nombre),
        ('Tipo de unidad', TIPOS_DE_UNIDAD.get(contexto.base, '—')),
        ('Período', periodo),
        ('Datos al', f'{contexto.corte:%d/%m/%Y}'),
        ('Acompaña a', f'Informe semestral {documento.anio}-{documento.corte}'
                       + (f' · Anexo {contexto.numero}' if contexto.numero else '')),
        ('Responsable', nombre_de(getattr(unidad, 'administrador', None))),
    ]
    largos = []
    if codigo in EXIGENCIAS:
        largos.append(('Exigencia que responde', EXIGENCIAS[codigo]))
    largos.append(('Metas que respalda', '; '.join(metas) if metas
                   else 'Registro del período, sin meta propia en la planificación.'))
    largos.append(('Fuente', FUENTE))
    registros = constructor_de(codigo)(contexto)
    for registro in registros:
        if not registro.ficha and len(registro.cabecera) > COLUMNAS_MAXIMAS:
            raise ValueError(f'«{registro.titulo}» tiene {len(registro.cabecera)} columnas; el máximo es '
                             f'{COLUMNAS_MAXIMAS}.')
    return {'titulo': titulo, 'numero': contexto.numero, 'datos': cortos + largos, 'datos_cortos': len(cortos),
            'registros': registros}


# -- PDF ----------------------------------------------------------------------------------

def pdf_del_anexo(documento, inicio, fin, *, codigo_documento, version, lectura=None):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.platypus import Image as Miniatura

    from apps.core.presentation.estilo_reportes import estilos_informe
    from apps.core.presentation.pdf_institucional import marco_institucional, metadatos_documento

    compuesto = componer_anexo(documento, inicio, fin, lectura)
    dibujar, CanvasNumerado, medidas = marco_institucional(
        formato=compuesto['titulo'], apaisado=True, pie='Expediente de calidad',
        # Sin número de versión: es un contador interno de archivos, no una edición del formato.
        metadatos=metadatos_documento(codigo_documento, periodo=documento.etiqueta_corte))
    # Sin marca de borrador: el anexo que se consulta al día es el mismo formato que se archiva.
    tinta = medidas['colores']
    ancho = medidas['ancho_util']
    estilos = estilos_informe(tinta)
    negrita = estilos['celda_b'].fontName
    normal = ParagraphStyle('AnexoCelda', parent=estilos['celda'], textColor=tinta['oscuro'])
    etiqueta = ParagraphStyle('AnexoEtiqueta', parent=normal, fontName=negrita)
    nombre = ParagraphStyle('AnexoRegistro', parent=etiqueta, textColor=tinta['primario'])
    tenue = ParagraphStyle('AnexoVacio', parent=normal, textColor=tinta['tenue'])

    def color(clave):
        return '#' + tinta[clave].hexval()[2:]

    rejilla = [('INNERGRID', (0, 0), (-1, -1), .3, tinta['linea']), ('BOX', (0, 0), (-1, -1), .5, tinta['linea']),
               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
               ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
               ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    fondo_grupo = colors.HexColor('#E9F0EB')

    def marcado(valor):
        """El contenido de una celda en el marcado de ReportLab."""
        if isinstance(valor, Enlace):
            return (f'<a href="{escape(valor.url, {chr(34): "&quot;"})}" color="{color("primario")}">'
                    f'{escape(valor.texto)}</a>')
        if isinstance(valor, Par):
            return (f'{marcado(valor.principal)}<br/><font size="7.5" color="{color("tenue")}">'
                    f'{marcado(valor.secundario)}</font>')
        return escape(str(valor))

    def parrafo(valor, estilo=normal):
        return Paragraph(marcado(valor), estilo)

    def contenido(valor, disponible):
        """Lo que se dibuja en una celda de datos: un párrafo o, si es una imagen, su miniatura y el enlace."""
        if not isinstance(valor, Imagen):
            return parrafo(valor)
        if not valor.copia():
            return parrafo(valor.sin_imagen())
        # La miniatura no se parte entre hojas: la fila entera pasa a la siguiente.
        figura = Miniatura(BytesIO(valor.copia()[0]), *valor.medida(min(MINIATURA_ANCHO, disponible)))
        return [figura, Spacer(1, 2), parrafo(valor.sin_imagen())]

    def datos_generales(pares, cortos):
        # Dos pares por fila; la exigencia, las metas y la fuente ocupan la fila entera.
        filas, estilo = [], list(rejilla)
        for i in range(0, cortos, 2):
            fila = []
            for clave, valor in pares[i:i + 2]:
                fila += [parrafo(clave, etiqueta), parrafo(valor)]
            filas.append(fila)
        for clave, valor in pares[cortos:]:
            filas.append([parrafo(clave, etiqueta), parrafo(valor), '', ''])
            estilo.append(('SPAN', (1, len(filas) - 1), (3, len(filas) - 1)))
        estilo += [('BACKGROUND', (0, 0), (0, -1), tinta['suave']),
                   ('BACKGROUND', (2, 0), (2, cortos // 2 - 1), tinta['suave'])]
        t = Table(filas, colWidths=[ancho * p for p in (.15, .37, .12, .36)], hAlign='LEFT')
        t.setStyle(TableStyle(estilo))
        return t

    def tabla(registro, titulo):
        columnas = len(registro.cabecera)
        vacia = [''] * (columnas - 1)
        if registro.ficha:
            anchos = [ancho * .28, ancho * .72]
        elif registro.pesos:
            anchos = _anchos_fijos(registro.pesos, registro.cabecera, registro.filas, ancho, negrita,
                                   normal.fontName, normal.fontSize)
        else:
            anchos = _anchos_por_contenido(registro.cabecera, registro.filas, ancho, negrita,
                                           normal.fontName, normal.fontSize)
        datos = [[parrafo(titulo.upper(), nombre), *vacia]]
        estilo = list(rejilla) + [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), tinta['suave'])]
        if not registro.ficha:
            datos.append([parrafo(c, etiqueta) for c in registro.cabecera])
            estilo.append(('LINEBELOW', (0, 1), (-1, 1), .8, tinta['primario']))
        primera = len(datos)
        if not registro.filas:
            datos.append([parrafo(registro.vacio, tenue), *vacia])
            estilo.append(('SPAN', (0, primera), (-1, primera)))
        else:
            if registro.ficha:
                estilo.append(('BACKGROUND', (0, primera), (0, -1), tinta['suave']))
            else:
                estilo.append(('ROWBACKGROUNDS', (0, primera), (-1, -1), [colors.white, colors.HexColor('#F8FAF9')]))
            for fila in registro.filas:
                if isinstance(fila, Grupo):
                    posicion = len(datos)
                    datos.append([parrafo(fila.texto, etiqueta), *vacia])
                    estilo += [('SPAN', (0, posicion), (-1, posicion)),
                               ('BACKGROUND', (0, posicion), (-1, posicion), fondo_grupo)]
                elif registro.ficha:
                    datos.append([parrafo(fila[0], etiqueta), contenido(fila[1], anchos[1] - 10)])
                else:
                    # Diez puntos son los márgenes laterales de la celda.
                    datos.append([contenido(v, a - 10) for v, a in zip(fila, anchos)])
            total = registro.total
            if total == '' and not registro.ficha:
                cuenta = sum(not isinstance(fila, Grupo) for fila in registro.filas)
                total = (total_con_respaldo(registro.filas) if registro.cabecera[-1] == 'Respaldo'
                         else f'Total: {plural(cuenta, "registro", "registros")}')
            pie = ([parrafo(v, etiqueta) for v in registro.suma] if registro.suma
                   else [parrafo(total, etiqueta), *vacia] if total else None)
            if pie:
                datos.append(pie)
                estilo += [('BACKGROUND', (0, -1), (-1, -1), tinta['suave']),
                           ('LINEABOVE', (0, -1), (-1, -1), .8, tinta['primario'])]
                if not registro.suma:
                    estilo.append(('SPAN', (0, -1), (-1, -1)))
        t = Table(datos, colWidths=anchos, repeatRows=1 if registro.ficha else 2, hAlign='LEFT')
        t.setStyle(TableStyle(estilo))
        return t

    historia = [datos_generales(compuesto['datos'], compuesto['datos_cortos']), Spacer(1, 5 * mm)]
    for posicion, registro in enumerate(compuesto['registros'], 1):
        # Cada tabla se cita por su número: «Anexo 2, tabla 2.4».
        numero = f"{compuesto['numero']}.{posicion}" if compuesto['numero'] else str(posicion)
        # El nombre y las columnas de un registro no quedan solos al pie de una hoja.
        historia += [CondPageBreak(28 * mm), tabla(registro, f'{numero} {registro.titulo}'), Spacer(1, 5 * mm)]

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f"{compuesto['titulo']} - {documento.unidad.nombre}",
    ).build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return buffer.getvalue()
