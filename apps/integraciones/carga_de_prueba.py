"""Carga, por las pantallas de la plataforma, un registro de prueba en cada documento del Centro de reportes.

La usa el comando ``cargar_registros_de_prueba``. Cada paso recorre la misma pantalla que usa una persona, con
``django.test.Client`` y la sesión de la cuenta que corresponde, enviando los mismos campos que el formulario
(las rutas están descritas en ``docs/rutas-de-captura-de-documentos.md``). Lo que la Dirección decide en
Administración se hace con la función de dominio que llama esa pantalla, porque Administración exige segundo
factor y red autorizada, que una sesión de consola no puede presentar.

Todo texto libre empieza con «[PRUEBA] », todo código elegible con «PRUEBA-», y cada archivo de respaldo es un PDF
o una imagen generados en el momento que dicen en grande «DOCUMENTO DE PRUEBA · SILAB-CID».
"""
import json
import traceback
from dataclasses import dataclass, field
from datetime import timedelta
from html.parser import HTMLParser
from io import BytesIO

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import QueryDict
from django.test import Client
from django.urls import reverse
from django.utils import timezone

PREFIJO = '[PRUEBA] '
LEYENDA = 'DOCUMENTO DE PRUEBA · SILAB-CID'
CONDICIONES = ('infraestructura', 'equipos', 'emergencias', 'proteccion', 'almacenamiento', 'limpieza', 'desechos')
INTENCION = ' '.join([f'{PREFIJO}Sesión ficticia de la carga de prueba para comprobar el registro y su cierre.'] * 5)

ANEXOS = (
    ('REGISTRO-USO', 'Anexo 1 · Registros de uso'),
    ('EQUIPAMIENTO', 'Anexo 2 · Mantenimiento y equipamiento'),
    ('INVENTARIO-CORTE', 'Anexo 3 · Inventario'),
    ('FICHAS-TECNICAS', 'Anexo 4 · Fichas técnicas'),
    ('PRACTICAS-FT02', 'Anexo 5 · Planificación de prácticas'),
    ('GUIAS', 'Anexo 6 · Guías de prácticas'),
    ('PRACTICAS-FT03', 'Anexo 7 · Asistencia y evidencias'),
    ('INDUCCION-SEGURIDAD', 'Anexo 8 · Seguridad y condiciones'),
    ('DESECHOS', 'Anexo 9 · Desechos'),
    ('INVESTIGACION', 'Anexo 10 · Investigación'),
    ('TRANSFERENCIA', 'Anexo 11 · Transferencia y servicios'),
)
RESPALDO = (
    ('capacitacion', 'Respaldo · Capacitación y difusión'),
    ('simulacros', 'Respaldo · Simulacros'),
    ('calibracion', 'Respaldo · Calibración de equipos'),
    ('sustancias', 'Respaldo · Sustancias sujetas a control'),
    ('personal', 'Respaldo · Personal de la unidad'),
    ('satisfaccion', 'Respaldo · Satisfacción de los usuarios'),
)
PRINCIPALES = (
    ('RESOLUCION-CREACION', 'Resolución de creación'),
    ('PROTOCOLO-BIOSEGURIDAD', 'Protocolo de seguridad'),
    ('REGLAMENTO-USO', 'Reglamento de uso'),
    ('PLAN-COMPRAS-ANUAL', 'Plan anual de compras'),
    ('PLANIFICACION', 'Planificación semestral'),
    ('INFORME-SEMESTRAL', 'Informe semestral'),
)
NOMBRES = dict(ANEXOS + RESPALDO + PRINCIPALES)


class FalloDePaso(Exception):
    """Una pantalla no aceptó lo enviado: el mensaje dice cuál y qué respondió."""


# ---- archivos de respaldo -------------------------------------------------------------------------------

def pdf_de_prueba(titulo):
    """Un PDF de una página que dice en grande que es un documento de prueba."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    lienzo = Canvas(salida, pagesize=A4, invariant=1)
    ancho, alto = A4
    lienzo.setFont('Helvetica-Bold', 26)
    lienzo.drawCentredString(ancho / 2, alto - 220, LEYENDA)
    lienzo.setFont('Helvetica', 12)
    lienzo.drawCentredString(ancho / 2, alto - 260, titulo[:90])
    lienzo.drawCentredString(ancho / 2, alto - 280, 'Sin validez institucional. Se retira con la carga de prueba.')
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def imagen_de_prueba():
    """Una imagen PNG con la leyenda de prueba en grande."""
    from PIL import Image, ImageDraw, ImageFont

    lienzo = Image.new('RGB', (1200, 500), '#ffffff')
    dibujo = ImageDraw.Draw(lienzo)
    try:
        letra = ImageFont.load_default(size=56)
    except TypeError:
        letra = ImageFont.load_default()
    dibujo.rectangle((10, 10, 1189, 489), outline='#b00020', width=8)
    dibujo.text((600, 250), LEYENDA, fill='#b00020', font=letra, anchor='mm')
    salida = BytesIO()
    lienzo.save(salida, 'PNG')
    return salida.getvalue()


def archivo_pdf(nombre, titulo):
    return SimpleUploadedFile(f'{nombre.lower()}.pdf', pdf_de_prueba(titulo), content_type='application/pdf')


# ---- formularios, como los envía el navegador -----------------------------------------------------------

class FormularioDelPanel(HTMLParser):
    """Un formulario del panel de la unidad con sus valores por omisión (`data-agenda-operation-form`)."""

    def __init__(self, nombre):
        super().__init__()
        self.nombre, self.dentro, self.encontrado = nombre, False, False
        self.datos, self.clases = {}, {}
        self._lista = self._area = None

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == 'form':
            self.dentro = atributos.get('data-agenda-operation-form') == self.nombre
            self.encontrado = self.encontrado or self.dentro
            return
        if not self.dentro:
            return
        nombre = atributos.get('name')
        if etiqueta == 'input' and nombre:
            tipo = atributos.get('type', 'text')
            if tipo == 'checkbox':
                self.clases[nombre] = 'casilla'
                if 'checked' in atributos:
                    self.datos[nombre] = atributos.get('value') or 'on'
            elif tipo not in ('file', 'submit', 'button'):
                self.datos[nombre] = atributos.get('value') or ''
        elif etiqueta == 'select' and nombre:
            self._lista = [nombre, 'multiple' in atributos, False]
            if self._lista[1]:
                self.clases[nombre] = 'multiple'
        elif etiqueta == 'option' and self._lista:
            nombre, multiple, elegido = self._lista
            if not multiple and (not elegido or 'selected' in atributos):
                self.datos[nombre] = atributos.get('value') or ''
                self._lista[2] = True
        elif etiqueta == 'textarea' and nombre:
            self._area = nombre
            self.datos[nombre] = ''

    def handle_data(self, texto):
        if self.dentro and self._area:
            self.datos[self._area] += texto

    def handle_endtag(self, etiqueta):
        if etiqueta == 'form':
            self.dentro = False
        elif etiqueta == 'select':
            self._lista = None
        elif etiqueta == 'textarea':
            self._area = None


class BotonesDelPanel(HTMLParser):
    """Los botones que abren un formulario del panel, con sus atributos `data-field-*`."""

    def __init__(self, formulario):
        super().__init__()
        self.formulario, self.hallados = formulario, []

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == 'button' and atributos.get('data-agenda-operation-open') == self.formulario:
            self.hallados.append(atributos)


class FormulariosDePagina(HTMLParser):
    """Los formularios de una página con los campos que enviaría el navegador (sin `<template>` ni deshabilitados)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.formularios, self.actual, self.textarea, self.select, self.plantillas = [], None, None, None, 0

    def handle_starttag(self, etiqueta, atributos):
        a = dict(atributos)
        if etiqueta == 'template':
            self.plantillas += 1
            return
        if self.plantillas:
            return
        if etiqueta == 'form':
            self.actual = dict(campos=[], opciones={})
            self.formularios.append(self.actual)
            return
        if etiqueta == 'option' and self.select is not None:
            self.select['opciones'].append((a.get('value', ''), 'selected' in a))
            return
        if self.actual is None or not a.get('name'):
            return
        if etiqueta == 'input':
            tipo = a.get('type', 'text').lower()
            if tipo in ('submit', 'button', 'image', 'file', 'reset'):
                return
            if tipo in ('checkbox', 'radio'):
                self.actual['opciones'].setdefault(a['name'], []).append(a.get('value', 'on'))
                if 'checked' not in a:
                    return
            if 'disabled' not in a:
                self.actual['campos'].append((a['name'], a.get('value', 'on' if tipo in ('checkbox', 'radio') else '')))
        elif etiqueta == 'textarea':
            self.textarea = dict(destino=self.actual, nombre=a['name'], texto=[], inactivo='disabled' in a)
        elif etiqueta == 'select':
            self.select = dict(destino=self.actual, nombre=a['name'], multiple='multiple' in a, opciones=[],
                               inactivo='disabled' in a)

    def handle_data(self, datos):
        if self.textarea is not None:
            self.textarea['texto'].append(datos)

    def handle_endtag(self, etiqueta):
        if etiqueta == 'template':
            self.plantillas = max(0, self.plantillas - 1)
        elif self.plantillas:
            return
        elif etiqueta == 'form':
            self.actual = None
        elif etiqueta == 'textarea' and self.textarea is not None:
            if not self.textarea['inactivo']:
                self.textarea['destino']['campos'].append(
                    (self.textarea['nombre'], ''.join(self.textarea['texto']).lstrip('\n')))
            self.textarea = None
        elif etiqueta == 'select' and self.select is not None:
            destino = self.select['destino']
            destino['opciones'].setdefault(self.select['nombre'], []).extend(v for v, _m in self.select['opciones'])
            elegidas = [valor for valor, marcada in self.select['opciones'] if marcada]
            if not elegidas and not self.select['multiple'] and self.select['opciones']:
                elegidas = [self.select['opciones'][0][0]]
            if not self.select['inactivo']:
                destino['campos'].extend((self.select['nombre'], valor) for valor in elegidas)
            self.select = None


def datos_de_formulario(formulario, **cambios):
    """Lo que enviaría el navegador al guardar un formulario de Django sin tocarlo, más los cambios."""
    datos = {}
    for campo in formulario:
        valor = campo.value()
        if valor in (None, '', False) or hasattr(valor, 'read') or hasattr(valor, 'url'):
            continue
        if isinstance(valor, (list, tuple)):
            datos[campo.html_name] = [str(getattr(v, 'pk', v)) for v in valor]
        elif valor is True:
            datos[campo.html_name] = 'on'
        else:
            datos[campo.html_name] = valor.isoformat() if hasattr(valor, 'isoformat') else str(valor)
    for nombre, valor in cambios.items():
        datos[formulario.add_prefix(nombre)] = valor
    return datos


def texto_plano(texto):
    """El texto sin espacios: una celda de tabla puede partir un código en dos renglones."""
    return ''.join(str(texto).split())


def texto_del_pdf(contenido):
    from pypdf import PdfReader

    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


# ---- sesiones -----------------------------------------------------------------------------------------

class Navegador:
    """La sesión de una cuenta real recorriendo las pantallas, como lo haría su navegador."""

    def __init__(self, usuario, host):
        self.usuario = usuario
        self.cliente = Client(HTTP_HOST=host)
        self.cliente.force_login(usuario)

    def get(self, ruta, datos=None, **extra):
        return self.cliente.get(ruta, datos or {}, secure=True, **extra)

    def post(self, ruta, datos=None, **extra):
        return self.cliente.post(ruta, datos if datos is not None else {}, secure=True, **extra)

    def salir(self):
        self.cliente.logout()


def _detalle(respuesta):
    """Lo que respondió la pantalla, para decir por qué no se aceptó."""
    try:
        cuerpo = respuesta.json()
        return str(cuerpo.get('error') or cuerpo.get('errors') or cuerpo)[:500]
    except (ValueError, AttributeError):
        pass
    contexto = getattr(respuesta, 'context', None)
    if contexto is not None:
        for clave in ('form', 'formulario', 'form_generacion'):
            try:
                formulario = contexto[clave]
            except (KeyError, TypeError):
                continue
            if getattr(formulario, 'errors', None):
                return formulario.errors.as_text()[:500]
    try:
        mensajes = ' '.join(str(m) for m in get_messages(respuesta.wsgi_request))
    except Exception:  # noqa: BLE001 - solo es para describir el rechazo
        mensajes = ''
    return mensajes or getattr(respuesta, 'content', b'')[:300].decode('utf-8', 'replace')


def exigir(respuesta, *codigos, que=''):
    if respuesta.status_code not in codigos:
        raise FalloDePaso(f'{que}: respuesta {respuesta.status_code}. {_detalle(respuesta)}')
    return respuesta


# ---- el informe por documento ---------------------------------------------------------------------------

@dataclass
class Registro:
    documento: str
    tabla: str
    codigo: str
    estado: str
    donde: str
    buscar: list = field(default_factory=list)
    aparece: str = ''


@dataclass
class Paso:
    nombre: str
    resultado: str
    detalle: str = ''


# ---- la carga -------------------------------------------------------------------------------------------

class CargaDePrueba:
    """Recorre las pantallas de una unidad y deja un registro válido en cada documento."""

    def __init__(self, unidad, *, admin, usuario, direccion, validador, host, abrir_con_ultimatum=False,
                 rastreo=None):
        from apps.documentos.presentation.expediente import cortes_del_anio, periodo_vigente

        self.unidad, self.slug = unidad, unidad.slug
        self.admin, self.usuario, self.direccion, self.validador = admin, usuario, direccion, validador
        self.host, self.abrir_con_ultimatum = host, abrir_con_ultimatum
        self.rastreo = rastreo
        self.hoy = timezone.localdate()
        self.anio = self.hoy.year
        self.corte = periodo_vigente(cortes_del_anio(self.anio), self.hoy)
        self.inicio, self.fin = cortes_del_anio(self.anio)[self.corte]
        self.registros, self.pasos = [], []
        self.equipo = self.espacio = self.reserva = self.servicio_reserva = None
        self.dias = self._dias_de_atencion()

    # -- ayudas ---------------------------------------------------------------------------------------

    def _dias_de_atencion(self):
        """Días hábiles desde hoy más tres: las reservas se piden con anticipación y dentro del período."""
        dias, fecha = [], self.hoy + timedelta(days=3)
        while len(dias) < 3:
            if fecha.weekday() < 5:
                dias.append(fecha)
            fecha += timedelta(days=1)
        return dias

    def navegador(self, usuario):
        if not hasattr(self, '_navegadores'):
            self._navegadores = {}
        if usuario.pk not in self._navegadores:
            self._navegadores[usuario.pk] = Navegador(usuario, self.host)
        return self._navegadores[usuario.pk]

    def cerrar_sesiones(self):
        for navegador in getattr(self, '_navegadores', {}).values():
            navegador.salir()

    @property
    def web(self):
        return self.navegador(self.admin)

    def operar(self, navegador=None, **datos):
        respuesta = (navegador or self.web).post(reverse('gestion_operacion_accion', args=[self.slug]), datos)
        exigir(respuesta, 200, que=f'Panel de la unidad, formulario «{datos.get("modulo")}»')
        return respuesta.json().get('registro', {}).get('id')

    def decidir(self, reserva, accion, navegador=None, **datos):
        respuesta = (navegador or self.web).post(reverse('gestion_reserva_accion', args=[self.slug, reserva.pk]),
                                                 {'accion': accion, **datos})
        exigir(respuesta, 200, que=f'Reservas y agenda, «{accion}» de {reserva.codigo_reserva}')
        reserva.refresh_from_db()
        return reserva

    def panel(self, vista, **parametros):
        respuesta = self.web.get(reverse('gestion_unidad', args=[self.slug]), dict(view=vista, **parametros))
        exigir(respuesta, 200, que=f'Panel «{vista}»')
        return respuesta.content.decode('utf-8')

    def botones(self, html, formulario, **con):
        lector = BotonesDelPanel(formulario)
        lector.feed(html)
        return [b for b in lector.hallados
                if all(b.get('data-field-' + campo) == str(valor) for campo, valor in con.items())]

    def abrir(self, html, formulario, boton=None, /, **escrito):
        """El formulario del panel con sus valores por omisión, lo que le pasa el botón y lo que se escribe."""
        lector = FormularioDelPanel(formulario)
        lector.feed(html)
        if not lector.encontrado:
            raise FalloDePaso(f'El panel no dibuja el formulario «{formulario}».')
        datos = dict(lector.datos)
        for atributo, valor in (boton or {}).items():
            campo = atributo[len('data-field-'):]
            if not atributo.startswith('data-field-') or (campo not in lector.datos and campo not in lector.clases):
                continue
            if lector.clases.get(campo) == 'casilla':
                datos.pop(campo, None)
                if valor in ('true', '1'):
                    datos[campo] = 'on'
            elif lector.clases.get(campo) == 'multiple':
                datos[campo] = [parte for parte in valor.split(',') if parte]
            else:
                datos[campo] = valor
        datos.update(escrito)
        if 'catalogos_remotos' in datos:
            datos['catalogos_seleccion_cargada'] = '1'
        datos['accion'] = 'guardar'
        return datos

    def guardar_en_panel(self, datos, que):
        respuesta = self.web.post(reverse('gestion_operacion_accion', args=[self.slug]), datos)
        exigir(respuesta, 200, que=que)
        return respuesta.json()

    def evidencia(self, tipo, codigo, titulo, descripcion, **campos):
        """«Registrar evidencia» del Centro de reportes, comprobada y con su respaldo."""
        from apps.documentos.models.medicion import EvidenciaGestionUnidad

        datos = dict(anio=self.anio, corte=self.corte, tipo=tipo, codigo=codigo, fecha=self.hoy.isoformat(),
                     titulo=PREFIJO + titulo, descripcion=PREFIJO + descripcion, responsable=self.admin.pk,
                     verificar='on', archivo=archivo_pdf(codigo, PREFIJO + titulo))
        datos.update(campos)
        respuesta = self.web.post(reverse('fuentes_metas_unidad', args=[self.slug]), datos)
        exigir(respuesta, 302, que=f'Registrar evidencia {tipo}')
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo=codigo)
        if evidencia.estado != 'validado':
            raise FalloDePaso(f'La evidencia {codigo} quedó en «{evidencia.estado}», no verificada.')
        return evidencia

    def donde_anexo(self, codigo):
        return (reverse('gestion_expediente_unidad', args=[self.slug])
                + f'?anio={self.anio}&corte={self.corte}&gestionar=INFORME-SEMESTRAL&anexo={codigo}&borrador=1')

    def donde_respaldo(self, categoria):
        return (reverse('gestion_reporte_unidad', args=[self.slug])
                + f'?categoria_reporte={categoria}&desde={self.inicio.isoformat()}&hasta={self.fin.isoformat()}')

    def donde_principal(self, codigo, anio=None, corte=None):
        corte = self.corte if corte is None else corte
        return (reverse('gestion_expediente_unidad', args=[self.slug])
                + f'?anio={anio or self.anio}&corte={corte}&gestionar={codigo}')

    def anotar(self, documento, tabla, codigo, estado, *buscar):
        if documento in dict(ANEXOS):
            donde = self.donde_anexo(documento)
        elif documento in dict(RESPALDO):
            donde = self.donde_respaldo(documento)
        else:
            donde = self.donde_principal(documento)
        self.registros.append(Registro(documento, tabla, codigo, estado, donde, [b for b in buscar if b]))

    # -- el recorrido ---------------------------------------------------------------------------------

    def paso(self, nombre, funcion, *documentos):
        """Un paso dentro de su propio punto de guardado: si una pantalla lo rechaza, se deshace solo ese paso."""
        marca = len(self.registros)
        marca_rastreo = self.rastreo.marca() if self.rastreo else None
        try:
            with transaction.atomic():
                funcion()
        except (FalloDePaso, ValidationError) as error:
            detalle = ' '.join(getattr(error, 'messages', None) or [str(error)])
            self._fallo(nombre, detalle, marca, documentos, marca_rastreo)
        except Exception as error:  # noqa: BLE001 - un fallo imprevisto se informa y la carga sigue
            ultima = traceback.extract_tb(error.__traceback__)[-1]
            self._fallo(nombre, f'{type(error).__name__}: {error} ({ultima.filename.rsplit("apps", 1)[-1]}:'
                                f'{ultima.lineno})', marca, documentos, marca_rastreo)
        else:
            self.pasos.append(Paso(nombre, 'ok'))

    def _fallo(self, nombre, detalle, marca, documentos, marca_rastreo):
        del self.registros[marca:]
        if self.rastreo:
            self.rastreo.volver(marca_rastreo)
        self.pasos.append(Paso(nombre, 'NO CARGADO', detalle[:600]))
        for documento in documentos:
            self.anotar(documento, nombre, '—', f'NO CARGADO: {detalle[:300]}')

    def ejecutar(self):
        # Las sesiones se abren antes de los pasos: un paso que se deshace no debe llevarse la sesión.
        for usuario in (self.admin, self.usuario, self.validador):
            self.navegador(usuario)
        self.paso('Equipo de prueba, verificación y calibración', self.equipo_de_prueba,
                  'INVENTARIO-CORTE', 'calibracion')
        self.paso('Plan y órdenes de mantenimiento', self.mantenimiento, 'EQUIPAMIENTO', 'calibracion')
        self.paso('Falla resuelta y prueba funcional', self.falla_y_prueba_funcional, 'EQUIPAMIENTO')
        self.paso('Mantenimiento de infraestructura', self.infraestructura, 'EQUIPAMIENTO')
        self.paso('Acta de inventario', self.acta_de_inventario, 'INVENTARIO-CORTE')
        self.paso('Insumo con existencias y consumo', self.insumo, 'INVENTARIO-CORTE')
        self.paso('Reactivo sujeto a control', self.reactivo, 'INVENTARIO-CORTE', 'sustancias')
        self.paso('Espacios y software', self.espacios_y_software, 'FICHAS-TECNICAS')
        self.paso('Formación y designación del personal', self.personal, 'personal')
        self.paso('Práctica: syllabus, guía, planificación y ejecución', self.practica,
                  'PRACTICAS-FT02', 'GUIAS', 'PRACTICAS-FT03')
        self.paso('Reserva de la persona usuaria', self.reserva_del_usuario, 'REGISTRO-USO')
        self.paso('Visita', self.visita, 'REGISTRO-USO')
        self.paso('Servicio especializado', self.servicio, 'TRANSFERENCIA')
        self.paso('Seguridad: requisito, habilitación, ingreso y atención', self.seguridad_y_atencion,
                  'INDUCCION-SEGURIDAD', 'REGISTRO-USO')
        self.paso('Valoración de la atención', self.valoracion, 'satisfaccion')
        self.paso('Inspección e incidente de seguridad', self.inspeccion_e_incidente, 'INDUCCION-SEGURIDAD')
        self.paso('Desecho y entrega al gestor', self.desechos, 'DESECHOS')
        self.paso('Resultado de investigación y transferencia', self.resultados, 'INVESTIGACION', 'TRANSFERENCIA')
        self.paso('Capacitación, difusión y simulacro', self.respaldo_de_gestion, 'capacitacion', 'simulacros')
        self.paso('Preparar el expediente', self.preparar_expediente, *[c for c, _n in PRINCIPALES])
        self.paso('Resolución de creación', self.resolucion, 'RESOLUCION-CREACION')
        self.paso('Protocolo de seguridad', lambda: self.redactado('PROTOCOLO-BIOSEGURIDAD', dict(
            revision_propuestas='revisado', evacuacion_protocolo=(
                f'<p>{PREFIJO}Alarma de viva voz; salida por la puerta principal; encuentro en el patio.</p>'))),
            'PROTOCOLO-BIOSEGURIDAD')
        self.paso('Reglamento de uso', lambda: self.redactado('REGLAMENTO-USO', dict(
            revision_propuestas='revisado')), 'REGLAMENTO-USO')
        self.paso('Plan anual de compras', lambda: self.redactado('PLAN-COMPRAS-ANUAL', dict(
            sin_compras_justificacion=f'<p>{PREFIJO}La dotación actual cubre las actividades previstas; '
                                      'no se solicitan compras.</p>')), 'PLAN-COMPRAS-ANUAL')
        self.paso('Planificación semestral', self.planificacion, 'PLANIFICACION')
        self.paso('Informe semestral (solo se prepara)', self.informe, 'INFORME-SEMESTRAL')

    # -- anexo 2 y 3: equipo, mantenimiento e inventario ---------------------------------------------

    def equipo_de_prueba(self):
        from apps.recursos.models.unidades import UnidadEquipo

        codigo = 'PRUEBA-EQ-01'
        self.equipo = UnidadEquipo.objects.get(pk=self.operar(
            modulo='recursos', entidad='equipo', nombre_catalogo=PREFIJO + 'Equipo de la carga de prueba',
            marca=PREFIJO + 'Marca ficticia', modelo='PRUEBA-MOD-01', codigo_unidad=codigo,
            numero_serie='PRUEBA-SERIE-01', codigo_bien='PRUEBA-BIEN-01', tipo_bien='BLD',
            clase_bien=PREFIJO + 'Equipo ficticio', custodio=PREFIJO + 'Custodia ficticia',
            ubicacion_bodega=PREFIJO + 'Bodega ficticia', valor_contable='1.00', estado_unidad='disponible',
            criticidad='critico', ubicacion_especifica=PREFIJO + 'Mesón ficticio', origen_adquisicion='compra_publica',
            fecha_adquisicion=self.hoy.isoformat(), documento_adquisicion=PREFIJO + 'Acta de ingreso ficticia',
            activa='on', ficha_tecnica=archivo_pdf('PRUEBA-FICHA-TECNICA', PREFIJO + 'Ficha técnica ficticia')))
        # Verificación física: «Confirmar que existe».
        respuesta = self.web.post(reverse('verificar_equipo', args=[self.slug, codigo]),
                                  dict(resultado='existe', nota=PREFIJO + 'Etiqueta ficticia legible.'))
        exigir(respuesta, 302, que='Verificación física del equipo')
        # Calibración: «Editar la ficha» del equipo, sección «Modelo».
        editor = reverse('editar_equipo_ficha', args=[self.slug, codigo])
        formulario = exigir(self.web.get(editor, dict(seccion='modelo')), 200, que='Ficha del equipo').context['form_modelo']
        proxima = self.hoy.replace(year=self.hoy.year + 1, day=1)
        respuesta = self.web.post(editor, dict(datos_de_formulario(
            formulario, fecha_ultima_calibracion=self.hoy.isoformat(), proxima_calibracion=proxima.isoformat()),
            seccion='modelo'), HTTP_X_REQUESTED_WITH='fetch')
        exigir(respuesta, 200, que='Fechas de calibración')
        self.anotar('INVENTARIO-CORTE', '3.2 Equipos', codigo, 'Activo y verificado', 'PRUEBA-SERIE-01')
        self.anotar('calibracion', 'Calibración del equipo', codigo, 'Vigente', codigo)

    def _completar_orden(self, orden, nombre_informe):
        hoy = self.hoy.isoformat()
        self.operar(modulo='mantenimiento', registro_id=orden.pk, equipo_id=orden.equipo_id,
                    responsable=self.admin.pk, tipo=orden.tipo, titulo=orden.titulo, estado='completado',
                    ejecutor='interno', fecha_programada=f'{hoy}T08:00', fecha_inicio=f'{hoy}T08:00',
                    fecha_fin=f'{hoy}T09:30', duracion_horas='2', costo='1.00', plan_id=orden.plan_id or '',
                    incidencia_id=orden.incidencia_id or '', resultado=PREFIJO + 'Trabajo ficticio realizado.',
                    prueba_funcionamiento=PREFIJO + 'Prueba ficticia dentro de tolerancia.',
                    resultado_operativo='apto', informe=archivo_pdf(nombre_informe, PREFIJO + 'Informe ficticio'))
        orden.refresh_from_db()
        if orden.estado != 'completado':
            raise FalloDePaso(f'La orden {orden.codigo} quedó en «{orden.estado}».')
        return orden

    def _orden(self, **datos):
        from apps.recursos.models.mantenimiento import MantenimientoEquipo

        base = dict(modulo='mantenimiento', equipo_id=self.equipo.pk, responsable=self.admin.pk, tipo='preventivo',
                    estado='programado', ejecutor='interno', fecha_programada=f'{self.hoy.isoformat()}T08:00',
                    duracion_horas='2', plan_id='', incidencia_id='')
        return MantenimientoEquipo.objects.get(pk=self.operar(**(base | datos)))

    def mantenimiento(self):
        from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo

        self._exige_equipo()
        plan = PlanMantenimientoEquipo.objects.get(pk=self.operar(
            modulo='plan_mantenimiento', equipo_id=self.equipo.pk, tipo='preventivo', frecuencia_dias='90',
            responsable=self.admin.pk, nombre=PREFIJO + 'Plan preventivo ficticio',
            proveedor=PREFIJO + 'Servicio técnico ficticio'))
        orden = self._completar_orden(self._orden(titulo=PREFIJO + 'Mantenimiento preventivo ficticio'),
                                      'PRUEBA-INFORME-PREVENTIVO')
        self.anotar('EQUIPAMIENTO', '2.1 Plan de mantenimiento', 'PRUEBA-EQ-01', 'Plan activo', plan.nombre[:24])
        self.anotar('EQUIPAMIENTO', '2.2 Mantenimientos del período', orden.codigo, 'Completado con informe', orden.codigo)
        calibracion = self._completar_orden(self._orden(tipo='calibracion', titulo=PREFIJO + 'Calibración ficticia'),
                                            'PRUEBA-CERTIFICADO-CALIBRACION')
        self.anotar('calibracion', 'Orden de calibración', calibracion.codigo, 'Completada con certificado',
                    calibracion.codigo)

    def _exige_equipo(self):
        if self.equipo is None:
            raise FalloDePaso('Falta el equipo de prueba (paso anterior).')

    def _incidencia(self, tipo, titulo, descripcion, solucion, **extra):
        from apps.recursos.models.mantenimiento import IncidenciaEquipo

        datos = dict(modulo='incidencia', equipo_id=self.equipo.pk, titulo=titulo, tipo=tipo, prioridad='media',
                     estado='abierta', descripcion=descripcion, asignada_a=self.admin.pk, solucion='', **extra)
        incidencia = IncidenciaEquipo.objects.get(pk=self.operar(**datos))
        self.operar(**(datos | dict(registro_id=incidencia.pk, estado='resuelta', solucion=solucion)))
        incidencia.refresh_from_db()
        if incidencia.estado != 'resuelta':
            raise FalloDePaso(f'La incidencia quedó en «{incidencia.estado}».')
        return incidencia

    def falla_y_prueba_funcional(self):
        self._exige_equipo()
        titulo = PREFIJO + 'Falla ficticia del equipo de prueba'
        self._incidencia('falla', titulo, PREFIJO + 'Descripción ficticia de la falla.',
                         PREFIJO + 'Solución ficticia aplicada y probada.')
        self.anotar('EQUIPAMIENTO', '2.4 Fallas e incidencias', 'PRUEBA-EQ-01', 'Resuelta', titulo)
        procedimiento = PREFIJO + 'Procedimiento ficticio de prueba funcional.'
        self.evidencia('FUNCIONALIDAD', 'PRUEBA-FUNC-01', 'Prueba funcional ficticia', 'Prueba funcional ficticia.',
                       equipo_id=self.equipo.pk, procedimiento=procedimiento,
                       criterio=PREFIJO + 'Criterio ficticio de aceptación.', resultado_funcional='operativo',
                       hallazgos_funcionales='')
        self.anotar('EQUIPAMIENTO', '2.5 Pruebas funcionales', 'PRUEBA-FUNC-01', 'Evidencia verificada', procedimiento)

    def _espacio(self):
        from apps.gestion_unidades.models.espacios import EspacioReservable

        if self.espacio is None:
            # Un área técnica pide reservar también uno de sus equipos: se elige uno disponible.
            self.equipo_del_espacio = None
            for espacio in (EspacioReservable.objects.filter(unidad=self.unidad, activo=True, reservable=True)
                            .prefetch_related('equipos_asociados').order_by('orden', 'pk')):
                if not espacio.requiere_recurso_tecnico:
                    self.espacio = espacio
                    break
                equipo = next((e for e in espacio.equipos_existentes if e.estado_unidad == 'disponible'), None)
                if equipo and self.espacio is None:
                    self.espacio, self.equipo_del_espacio = espacio, equipo
        if self.espacio is None:
            raise FalloDePaso('La unidad no tiene un espacio activo y reservable (paso «Espacios y software»).')
        return self.espacio

    def infraestructura(self):
        espacio = self._espacio()
        hoy = self.hoy.isoformat()
        intervencion = PREFIJO + 'Revisión ficticia de tomas eléctricas'
        plan = self.evidencia(
            'PLAN-INFRA', 'PRUEBA-PINF-01', 'Plan ficticio de infraestructura', 'Plan ficticio.',
            alcance_infraestructura='aplica', justificacion_alcance=PREFIJO + 'Alcance ficticio del plan de prueba.',
            espacio_id=espacio.pk, ubicacion=PREFIJO + espacio.nombre, intervencion=intervencion,
            criticidad='critica', fecha_programada=hoy, frecuencia_dias='0', fecha_fin_programacion=hoy)
        self.evidencia('EJECUCION-INFRA', 'PRUEBA-EINF-01', 'Ejecución ficticia de infraestructura',
                       'Ejecución ficticia.', plan_id=plan.pk, fecha_programada=hoy, fecha_inicio=hoy, fecha_fin=hoy,
                       resultado=PREFIJO + 'Tomas ficticias revisadas.')
        self.anotar('EQUIPAMIENTO', '2.7 Infraestructura', 'PRUEBA-PINF-01', 'Ejecutada', intervencion)

    def acta_de_inventario(self):
        self.evidencia('INVENTARIO', 'PRUEBA-ACTA-01', 'Acta ficticia de revisión física',
                       'Sin diferencias en la revisión ficticia.', alcance=['equipos', 'software', 'espacios', 'insumos'],
                       revision_criticidad='on')
        self.anotar('INVENTARIO-CORTE', '3.1 Acta de revisión física', 'PRUEBA-ACTA-01', 'Evidencia verificada',
                    'PRUEBA-ACTA-01')

    def _crear_insumo(self, codigo, nombre, **escrito):
        from apps.recursos.models.consumibles import Consumible

        html = self.panel('recursos', modo_recursos='insumos')
        nuevo = [b for b in self.botones(html, 'consumible') if 'data-field-registro_id' not in b]
        if not nuevo:
            raise FalloDePaso('El panel no ofrece «Nuevo insumo».')
        self.guardar_en_panel(self.abrir(html, 'consumible', nuevo[0], codigo=codigo, nombre=nombre, **escrito),
                              'Nuevo insumo')
        return Consumible.objects.get(unidad=self.unidad, codigo=codigo)

    def _recibir(self, insumo, **escrito):
        from apps.recursos.models.consumibles import LoteConsumible

        # El catálogo se pagina: la persona busca el insumo por su código.
        html = self.panel('recursos', modo_recursos='insumos', busqueda_recursos=insumo.codigo)
        boton = [b for b in self.botones(html, 'lote_consumible', consumible_id=insumo.pk)
                 if 'data-field-registro_id' not in b]
        if not boton:
            raise FalloDePaso(f'El panel no ofrece «Recibir existencias» para {insumo.codigo}.')
        self.guardar_en_panel(self.abrir(html, 'lote_consumible', boton[0], **escrito), 'Recibir existencias')
        return LoteConsumible.objects.filter(consumible=insumo).order_by('-pk').first()

    def insumo(self):
        self._exige_equipo()
        insumo = self._crear_insumo('PRUEBA-INS-01', PREFIJO + 'Insumo ficticio de la carga', clasificacion='material',
                                    unidad_medida='unidad', cantidad_por_presentacion='10')
        lote = self._recibir(insumo, documento_recepcion='PRUEBA-REC-01')
        html = self.panel('recursos', modo_recursos='inventario', busqueda_recursos=insumo.codigo)
        consumo = [b for b in self.botones(html, 'inventario', consumible_id=insumo.pk)
                   if b.get('data-field-tipo') == 'salida']
        if not consumo:
            raise FalloDePaso('El panel no ofrece «Consumo o salida» para el insumo de prueba.')
        self.guardar_en_panel(self.abrir(html, 'inventario', consumo[0], motivo='consumo_practica', cantidad='1',
                                         lote_inventario_id=str(lote.pk), abrir_presentacion='1',
                                         equipo_id=str(self.equipo.pk), referencia='PRUEBA-CONSUMO-01'),
                              'Consumo o salida')
        self.anotar('INVENTARIO-CORTE', '3.5 y 3.6 Insumo, ingreso y consumo', 'PRUEBA-INS-01',
                    'Recibido y consumido', 'PRUEBA-INS-01', 'PRUEBA-CONSUMO-01')

    def reactivo(self):
        reactivo = self._crear_insumo('PRUEBA-REA-01', PREFIJO + 'Reactivo ficticio sujeto a control',
                                      clasificacion='reactivo', unidad_medida='ml', cantidad_por_presentacion='100',
                                      sustancia_controlada='true',
                                      autorizacion_control=PREFIJO + 'Autorización ficticia sin validez')
        if not reactivo.sustancia_controlada:
            raise FalloDePaso('El reactivo no quedó marcado como sustancia controlada.')
        self._recibir(reactivo)
        self.anotar('INVENTARIO-CORTE', '3.4 Reactivos', 'PRUEBA-REA-01', 'Con existencias', 'PRUEBA-REA-01')
        self.anotar('sustancias', 'Sustancias sujetas a control', 'PRUEBA-REA-01', 'Con autorización y lote',
                    'PRUEBA-REA-01')

    def espacios_y_software(self):
        """Si la unidad ya tiene espacios y software, se usan; si no, se registra uno de prueba."""
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.software import SoftwareDisponible

        try:
            espacio, estado = self._espacio(), 'Ya existía: se usa'
        except FalloDePaso:
            espacio = EspacioReservable.objects.get(pk=self.operar(
                modulo='recursos', entidad='espacio', codigo='PRUEBA-ESP-01', nombre=PREFIJO + 'Sala ficticia',
                tipo='sala', politica_reserva='mixto', capacidad='10', reservable='on', activo='on'))
            estado = 'Registrado (prueba)'
            self.espacio, self.equipo_del_espacio = espacio, None
        self.anotar('FICHAS-TECNICAS', '4.2 Espacios y talleres', espacio.codigo or espacio.nombre, estado,
                    espacio.codigo or espacio.nombre)
        programa = SoftwareDisponible.objects.filter(unidad=self.unidad, activo=True).order_by('nombre').first()
        if programa is None:
            programa = SoftwareDisponible.objects.get(pk=self.operar(
                modulo='recursos', entidad='software', nombre=PREFIJO + 'Programa ficticio', codigo='PRUEBA-SW-01',
                version='1.0', tipo_recurso='software', tipo_acceso='instalacion', licencias_totales='1',
                licencias_disponibles='1', activo='on'))
            estado = 'Registrado (prueba)'
        else:
            estado = 'Ya existía: se usa'
        self.anotar('FICHAS-TECNICAS', '4.3 Software y simuladores', programa.codigo or programa.nombre, estado,
                    programa.nombre[:30])

    def personal(self):
        """La formación y la designación de una persona que ya está en el equipo humano de la unidad."""
        from apps.gestion_unidades.models.espacios import ResponsableUnidad

        personas = ResponsableUnidad.objects.filter(unidad=self.unidad, activo=True)
        persona = personas.filter(usuario=None).order_by('pk').first() or personas.order_by('pk').first()
        if persona is None:
            raise FalloDePaso('La unidad no tiene personas activas en su equipo humano.')
        html = self.panel('configuracion')
        boton = self.botones(html, 'responsable', registro_id=persona.pk)
        if not boton:
            raise FalloDePaso(f'El panel no ofrece editar a {persona.nombre}.')
        formacion = PREFIJO + 'Formación ficticia de la carga de prueba'
        self.guardar_en_panel(self.abrir(html, 'responsable', boton[0], formacion=formacion,
                                         acto_designacion=PREFIJO + 'Designación ficticia PRUEBA-DES-01',
                                         fecha_designacion=self.hoy.isoformat()), 'Equipo humano')
        persona.refresh_from_db()
        if persona.formacion != formacion:
            raise FalloDePaso('La formación no se guardó.')
        self.anotar('personal', 'Personal de la unidad', persona.nombre, 'Formación y designación registradas',
                    'PRUEBA-DES-01')

    # -- anexos 1, 5, 6 y 7: reservas, visitas y prácticas -------------------------------------------

    def solicitud(self, dia, desde, hasta, **cambios):
        """Lo que envía el asistente de reserva al pedir el espacio, sin insumos."""
        espacio = self._espacio()
        datos = {
            'unidad_id': self.unidad.pk, 'tipo_solicitud': 'recursos', 'proposito_codigo': 'investigacion_innovacion',
            'vinculacion_actividad': 'independiente', 'intencion_solicitud': INTENCION,
            'fecha_inicio': f'{dia}T{desde:02d}:00', 'fecha_fin': f'{dia}T{hasta:02d}:00',
            'horas_seleccionadas': json.dumps(list(range(desde, hasta))), 'participantes_seleccionados': '[]',
            'consumibles_seleccionados': '[]', 'aceptar_terminos': 'on', 'incluye_espacio': 'true',
            'solicito_espacio': 'true', 'alcance_espacio': 'areas', 'espacios_solicitados': [str(espacio.pk)],
            'unidades_seleccionadas': '[]', 'equipo_codigo': 'RECURSOS', 'equipo_nombre': 'Espacio solicitado',
            'provision_consumibles': 'ninguno', 'frecuencia_reserva': 'unica',
        }
        if getattr(self, 'equipo_del_espacio', None):
            datos['unidades_seleccionadas'] = json.dumps([{'id': self.equipo_del_espacio.pk}])
        datos.update(cambios)
        return datos

    def reservar(self, usuario, datos, que):
        from apps.reservas.models.reservas import Reserva

        respuesta = self.navegador(usuario).post(reverse('crear_reserva'), datos)
        exigir(respuesta, 200, que=que)
        return Reserva.objects.get(pk=respuesta.json()['reserva_id'])

    def cerrar_atencion(self, reserva, desde, hasta, asistentes=1, **cambios):
        """«Iniciar atención» y «Completar» en Reservas y agenda, con el horario real y la asistencia."""
        self.decidir(reserva, 'iniciar')
        datos = {
            'ejecucion_registrada': '1', 'asistencia_solicitante': 'asistio',
            'participantes_seleccionados': json.dumps([{'id': u.pk, 'asistencia': 'asistio'}
                                                       for u in reserva.participantes.all()]),
            'ejecucion_hora_inicio': f'{desde:02d}:00', 'ejecucion_hora_fin': f'{hasta:02d}:00',
            'ejecucion_asistentes_total': str(asistentes), 'ejecucion_cumplimiento': 'si',
            'ejecucion_consumibles_json': '[]', 'ejecucion_espacios_ids': [str(self._espacio().pk)],
            'ejecucion_observaciones': PREFIJO + 'Atención ficticia sin novedades.',
        }
        datos.update(cambios)
        reserva = self.decidir(reserva, 'completar', **datos)
        if (reserva.estado, reserva.resultado_cierre) != ('completada', 'atendida'):
            raise FalloDePaso(f'La reserva {reserva.codigo_reserva} quedó en «{reserva.estado}».')
        return reserva

    def _responsable_admin(self):
        from apps.gestion_unidades.models.espacios import ResponsableUnidad

        return (ResponsableUnidad.objects.filter(unidad=self.unidad, usuario=self.admin, activo=True)
                .order_by('pk').first())

    def practica(self):
        from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
        from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
        from apps.reservas.models.reservas import GuiaActividadReserva

        # 1. Asignatura (la que ya tiene la unidad) y un tema de prueba del syllabus.
        asignatura = Asignatura.objects.filter(unidad=self.unidad).order_by('codigo').first()
        if asignatura is None:
            self.operar(modulo='asignatura', codigo='PRUEBA-ASIG-01', nombre=PREFIJO + 'Asignatura ficticia',
                        carrera=PREFIJO + 'Carrera ficticia', semestre='Primero', docente=self.admin.username,
                        estudiantes='10', periodo_id='', descripcion='')
            asignatura = Asignatura.objects.get(unidad=self.unidad, codigo='PRUEBA-ASIG-01')
        tema_nombre = PREFIJO + 'Tema ficticio de la práctica de prueba'
        self.operar(modulo='tema_asignatura', asignatura_id=str(asignatura.pk), orden='99',
                    unidad_tematica=PREFIJO + 'Unidad ficticia', nombre=tema_nombre, receta_id='', ejercicios='',
                    resultado_aprendizaje=PREFIJO + 'Resultado de aprendizaje ficticio.')
        tema = TemaAsignatura.objects.get(asignatura=asignatura, nombre=tema_nombre)
        # 2. Guía: la vigente de la unidad; si no tiene, la redacta la unidad y la aprueba otra persona.
        guia = (GuiaActividadReserva.objects.filter(actividad__unidad=self.unidad, estado_publicacion='publicada',
                                                    es_vigente=True).order_by('pk').first())
        guia_estado = 'Ya existía, aprobada y vigente: se usa'
        if guia is None:
            guia = self._guia_de_prueba()
            guia_estado = f'Aprobada y publicada por {self.validador.get_full_name() or self.validador.username}'
        # 3. La sesión de la práctica, reservada con la guía.
        dia = self.dias[1]
        datos = self.solicitud(dia, 9, 11, proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
                               vinculacion_actividad='catalogo', actividad_catalogo=str(guia.actividad_id),
                               origen_programacion='programada')
        try:
            reserva = self.reservar(self.usuario, datos, 'Reserva de la sesión de práctica')
        except FalloDePaso as rechazo:
            # Una cuenta de estudiante puede no pedir prácticas curriculares: la pide la cuenta de la unidad.
            self.pasos.append(Paso('Sesión de práctica pedida por la cuenta de la unidad', 'aviso', str(rechazo)[:300]))
            reserva = self.reservar(self.admin, datos, 'Reserva de la sesión de práctica')
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        # 4. La unidad completa la planificación con el tema del syllabus y la aprueba.
        ruta = reverse('editar_planificacion_practica', args=[self.slug, plan.pk])
        formulario = exigir(self.web.get(ruta), 200, que='Completar la planificación').context['form']
        datos = {nombre: ('' if formulario[nombre].value() is None else formulario[nombre].value())
                 for nombre in formulario.fields}
        responsable = self._responsable_admin()
        datos.update(tema_asignatura=str(tema.pk), tema='', resultado_aprendizaje='', estudiantes_planificados='1',
                     responsable_tecnico=str(responsable.pk) if responsable else '', accion='enviar')
        exigir(self.web.post(ruta, datos), 302, que='Enviar la planificación a revisión')
        exigir(self.web.post(reverse('accion_planificacion_practica', args=[self.slug, plan.pk]),
                             {'accion': 'aprobar', 'observaciones': PREFIJO + 'Planificación revisada.'}),
               302, que='Aprobar la planificación')
        self.decidir(reserva, 'aprobar')
        plan.refresh_from_db()
        if plan.estado != 'aprobada':
            raise FalloDePaso(f'La planificación quedó en «{plan.estado}».')
        self.anotar('PRACTICAS-FT02', '5.1 Prácticas planificadas', plan.codigo, 'Aprobada', plan.codigo)
        self.anotar('GUIAS', '6.1 Guías', guia.codigo_guia or guia.titulo[:30], guia_estado,
                    guia.codigo_guia or guia.titulo[:30])
        # 5. Ejecución con asistencia y evidencias; la unidad cierra la sesión y otra persona valida.
        ruta = reverse('editar_ejecucion_practica', args=[self.slug, plan.pk])
        formulario = exigir(self.web.get(ruta), 200, que='Registrar ejecución').context['form']
        participantes = [clave for clave, _r in formulario.fields['participantes_asistentes'].choices]
        espacios = [clave for clave, _r in formulario.fields['espacios_utilizados'].choices]
        for accion, tipo, archivo, descripcion in (
                ('guardar', 'asistencia', archivo_pdf('PRUEBA-ASISTENCIA', PREFIJO + 'Lista de asistencia ficticia'),
                 PREFIJO + 'Lista de asistencia ficticia firmada.'),
                ('enviar', 'fotografia', SimpleUploadedFile('prueba-fotografia.png', imagen_de_prueba(), 'image/png'),
                 PREFIJO + 'Fotografía ficticia de la práctica.')):
            respuesta = self.web.post(ruta, {
                'fecha_ejecucion': plan.fecha.isoformat(), 'hora_inicio_real': '09:00', 'hora_fin_real': '11:00',
                'resultado': 'ejecutada', 'motivo': '', 'estudiantes_asistentes': str(max(len(participantes), 1)),
                'observaciones_docente': PREFIJO + 'Objetivo alcanzado.', 'cumplimiento_resultado': 'si',
                'responsable_tecnico': str(responsable.pk) if responsable else '', 'detalle_operativo_registrado': '1',
                'espacios_utilizados': espacios, 'participantes_asistentes': participantes, 'accion': accion,
                'evidencia_tipo': tipo, 'evidencia_descripcion': descripcion, 'evidencias': archivo})
            exigir(respuesta, 302, que=f'Ejecución de la práctica ({accion})')
        reserva.refresh_from_db()
        self.cerrar_atencion(reserva, 9, 11, asistentes=max(len(participantes), 1))
        exigir(self.navegador(self.validador).post(reverse('accion_ejecucion_practica', args=[self.slug, plan.pk]),
                                                   {'accion': 'validar'}), 302, que='Validar la ejecución')
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        if ejecucion.estado != 'validada':
            raise FalloDePaso(f'La ejecución quedó en «{ejecucion.estado}».')
        quien = self.validador.get_full_name() or self.validador.username
        self.anotar('PRACTICAS-FT03', '7.1 a 7.4 Ejecución, asistencia y evidencias', plan.codigo,
                    f'Validada y cerrada por {quien}', plan.codigo, 'Fotografía ficticia de la práctica')
        self.anotar('REGISTRO-USO', '1.1 Sesión de la práctica', reserva.codigo_reserva, 'Atendida y completada',
                    reserva.codigo_reserva)

    def _guia_de_prueba(self):
        from apps.reservas.models.reservas import GuiaActividadReserva

        guia = {
            'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'practica_curricular',
            'nombre_actividad': PREFIJO + 'Práctica ficticia', 'codigo_actividad': 'PRUEBA-ACT-01',
            'descripcion_actividad': PREFIJO + 'Aplicación práctica ficticia.',
            'titulo': PREFIJO + 'Guía ficticia de la carga', 'codigo_guia': 'PRUEBA-GUIA-01',
            'asignatura': PREFIJO + 'Asignatura ficticia', 'carrera_semestre': PREFIJO + 'Carrera ficticia',
            'docente_responsable': self.admin.get_full_name() or self.admin.username,
            'categoria_uso': 'Docencia y práctica curricular', 'duracion': '2 horas', 'maximo_estudiantes': '10',
            'resultado_aprendizaje': PREFIJO + 'Resultado ficticio.', 'objetivos': PREFIJO + 'Objetivo ficticio.',
            'fundamento_teorico': PREFIJO + 'Fundamento ficticio.', 'equipos': PREFIJO + 'Equipo ficticio',
            'materiales': PREFIJO + 'Material ficticio', 'reactivos': '',
            'medidas_seguridad': PREFIJO + 'Medidas ficticias.', 'formato_procedimiento': 'numerado',
            'procedimiento': f'{PREFIJO}Paso uno\n{PREFIJO}Paso dos', 'resultados_esperados': PREFIJO + 'Resultado.',
            'criterios_evaluacion': PREFIJO + 'Criterio.', 'manejo_residuos': PREFIJO + 'No aplica.',
            'bibliografia': PREFIJO + 'Manual ficticio.', 'permite_descarga': 'on', 'solicita_publicacion': 'on',
            'accion': 'enviar_revision',
        }
        exigir(self.web.post(reverse('nueva_guia_practica', args=[self.slug]), guia), 302, que='Nueva guía')
        nueva = GuiaActividadReserva.objects.filter(codigo_guia='PRUEBA-GUIA-01').order_by('-pk').first()
        respuesta = self.navegador(self.validador).post(reverse('cambiar_estado_guia_practica', args=[nueva.pk]),
                                                        {'accion': 'aprobar', 'observacion': PREFIJO + 'Revisada.'})
        exigir(respuesta, 302, 200, que='Aprobar y publicar la guía')
        nueva.refresh_from_db()
        if nueva.estado_publicacion != 'publicada':
            raise FalloDePaso(f'La guía quedó en «{nueva.estado_publicacion}».')
        return nueva

    def reserva_del_usuario(self):
        """Una reserva sin insumos que la unidad aprueba; se atiende después de registrar su ingreso."""
        self.reserva = self.reservar(self.usuario, self.solicitud(self.dias[0], 9, 11), 'Reserva sin insumos')
        self.decidir(self.reserva, 'aprobar')
        if self.reserva.estado != 'confirmada':
            raise FalloDePaso(f'La reserva quedó en «{self.reserva.estado}».')

    def visita(self):
        from apps.reservas.models.visitas import SolicitudVisita
        from apps.reservas.presentation.visitas import oferta_de_visitas

        espacio = self._espacio()
        oferta = oferta_de_visitas(self.unidad)
        if not oferta['acepta'] or espacio not in oferta['areas']:
            areas = [str(a.pk) for a in oferta['areas']] + [str(espacio.pk)]
            self.operar(modulo='oferta_visitas', acepta_visitas='1',
                        personas_por_guia=str(oferta.get('personas_por_guia') or 10),
                        visitas_texto=oferta.get('texto') or '', areas_visitables=sorted(set(areas)))
        dia = self.dias[0]
        respuesta = self.navegador(self.usuario).post(reverse('crear_reserva'), {
            'tipo_solicitud': 'visita', 'unidad_id': self.unidad.pk, 'aceptar_terminos': 'on',
            'fecha_inicio': f'{dia}T14:00', 'fecha_fin': f'{dia}T16:00', 'horas_seleccionadas': '[14, 15]',
            'visita_categoria': 'externa', 'visita_institucion': PREFIJO + 'Colegio ficticio',
            'visita_proposito': 'academica', 'visita_conteo': 'lista', 'visita_personas': '2',
            'visita_descripcion': PREFIJO + 'Conocer la unidad en la visita ficticia.',
            'visita_asistentes_json': json.dumps([
                {'documento': '', 'nombre': nombre, 'rol': 'estudiante', 'telefono': '', 'correo': ''}
                for nombre in (PREFIJO + 'Visitante ficticio uno', PREFIJO + 'Visitante ficticio dos')]),
            'visita_usuarios_json': '[]', 'visita_recorrido': [str(espacio.pk)], 'visita_requisitos_aceptados': 'on'})
        exigir(respuesta, 200, que='Solicitud de visita')
        visita = SolicitudVisita.objects.get(pk=respuesta.json()['visita_id'])
        self.decidir(visita.reserva, 'aprobar')
        self.operar(modulo='visita', registro_id=str(visita.pk), guia=self.admin.username,
                    rango_edades=PREFIJO + '15 a 17 años', observaciones=PREFIJO + 'Grupo puntual.')
        lista = reverse('asistencia_visita', args=[self.slug, visita.pk])
        exigir(self.web.post(lista, {'presentes': [str(a.pk) for a in visita.asistentes.all()], 'nuevos': '',
                                     'observaciones': PREFIJO + 'Llegaron a tiempo.'}), 302, que='Asistencia de la visita')
        reserva = visita.reserva
        reserva.refresh_from_db()
        self.cerrar_atencion(reserva, 14, 16, asistentes=2)
        self.anotar('REGISTRO-USO', '1.4 Visitas', reserva.codigo_reserva, 'Atendida y completada',
                    reserva.codigo_reserva, 'Colegio ficticio')

    def servicio(self):
        from apps.laboratorios.operacion.models.fablab import FablabService

        servicio = (FablabService.objects.filter(unidad=self.unidad, activo=True, publico=True)
                    .exclude(tipo_servicio='visita').order_by('pk').first())
        if servicio is None:
            raise FalloDePaso('La unidad no tiene servicios publicados en su catálogo: no hay qué solicitar.')
        dia = self.dias[2]
        datos = self.solicitud(dia, 9, 11, tipo_solicitud='servicio', servicios_solicitados=[str(servicio.pk)],
                               proposito_codigo='servicio_cientifico_tecnologico', vinculacion_actividad='no_aplica',
                               modalidad_servicio='modelo_listo', alcance_beneficiario='externo',
                               entidad_beneficiaria=PREFIJO + 'Empresa ficticia', cotizacion_aceptada='on',
                               metodo_pago='por_definir', incluye_espacio='false', solicito_espacio='false',
                               espacios_solicitados=[], unidades_seleccionadas='[]', equipo_codigo='',
                               equipo_nombre='', archivos_tecnicos=archivo_pdf(
                                   'PRUEBA-ARCHIVO-TECNICO', PREFIJO + 'Archivo técnico ficticio del servicio'))
        reserva = self.reservar(self.usuario, datos, f'Solicitud del servicio «{servicio.nombre}»')
        self.decidir(reserva, 'aprobar')
        reserva = self.cerrar_atencion(reserva, 9, 11, ejecucion_espacios_ids=[])
        self.servicio_reserva = reserva
        self.anotar('TRANSFERENCIA', '11.2 Servicios especializados', reserva.codigo_reserva, 'Completada y atendida',
                    reserva.codigo_reserva)

    def seguridad_y_atencion(self):
        """Requisito de acceso, habilitación, control de ingreso y, con el ingreso, la atención de la reserva."""
        from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso

        if self.reserva is None:
            raise FalloDePaso('Falta la reserva de la persona usuaria (paso anterior).')
        self.operar(modulo='requisito_acceso', codigo='PRUEBA-REQ-01', nombre=PREFIJO + 'Inducción de seguridad ficticia',
                    tipo='induccion', momento='reservar', vigencia_dias='180', orden='99', consumible_id='',
                    cantidad_por_persona='1', descripcion=PREFIJO + 'Riesgos del área y salidas de emergencia.',
                    aplica_a=['estudiante'], obligatorio='1')
        requisito = RequisitoAcceso.objects.get(unidad=self.unidad, codigo='PRUEBA-REQ-01')
        self.operar(modulo='habilitacion_acceso', persona=self.usuario.username, requisito_id=requisito.pk,
                    fecha=self.hoy.isoformat(), vence='', origen='documento', documento='PRUEBA-HAB-01',
                    observaciones=PREFIJO + 'Certificado ficticio presentado.')
        HabilitacionAcceso.objects.get(requisito=requisito, usuario=self.usuario)
        self.anotar('INDUCCION-SEGURIDAD', '8.1 Requisitos de acceso', 'PRUEBA-REQ-01', 'Activo', 'PRUEBA-REQ-01')
        self.anotar('INDUCCION-SEGURIDAD', '8.2 Habilitaciones', 'PRUEBA-HAB-01', 'Vigente', 'PRUEBA-HAB-01')
        reserva = self.reserva
        personas = list(reserva.registros_participantes.all())
        if not personas:
            raise FalloDePaso(f'La reserva {reserva.codigo_reserva} no tiene participantes para registrar su ingreso.')
        datos = dict(modulo='ingreso', reserva_id=reserva.pk, personas_ids=','.join(str(p.pk) for p in personas))
        for persona in personas:
            datos.update({f'persona_{persona.pk}_ingresa': '1', f'persona_{persona.pk}_proteccion': '1',
                          f'persona_{persona.pk}_restricciones': '1', f'persona_{persona.pk}_hora': '09:05',
                          f'persona_{persona.pk}_salida': '10:55', f'persona_{persona.pk}_motivo': ''})
        self.operar(**datos)
        if not RegistroIngreso.objects.filter(reserva=reserva).exists():
            raise FalloDePaso('El control de ingreso no se registró.')
        self.anotar('INDUCCION-SEGURIDAD', '8.5 Control de ingresos', reserva.codigo_reserva, 'Ingreso registrado',
                    reserva.codigo_reserva)
        self.reserva = self.cerrar_atencion(reserva, 9, 11)
        self.anotar('REGISTRO-USO', '1.1 Sesiones del período', reserva.codigo_reserva, 'Atendida y completada',
                    reserva.codigo_reserva)

    def valoracion(self):
        from apps.reservas.models.valoraciones import ValoracionReserva

        if self.reserva is None or self.reserva.estado != 'completada':
            raise FalloDePaso('Falta la reserva atendida (paso anterior).')
        navegador = self.navegador(self.usuario)
        filas = exigir(navegador.get(reverse('obtener_reservas_usuario')), 200, que='Mis reservas').json()['reservas']
        propia = next((f for f in filas if f['id'] == self.reserva.pk), None)
        if not propia or not propia.get('puede_valorar'):
            raise FalloDePaso('«Mis reservas» no ofrece valorar la reserva atendida.')
        comentario = PREFIJO + 'Comentario ficticio de la carga de prueba.'
        exigir(navegador.post(propia['valorar_url'], {'general': '5', 'atencion_personal': '5', 'estado_equipos': '',
                                                      'instalaciones': '', 'comentario': comentario}),
               201, que='Valorar atención')
        ValoracionReserva.objects.get(reserva=self.reserva)
        self.anotar('satisfaccion', 'Valoraciones', self.reserva.codigo_reserva, 'Valorada (5 de 5)',
                    'Comentario ficticio de la carga')

    # -- anexos 8 a 11 y respaldo de gestión ----------------------------------------------------------

    def inspeccion_e_incidente(self):
        espacio = self._espacio()
        area = PREFIJO + espacio.nombre
        self.evidencia('INSPECCION', 'PRUEBA-INSP-01', 'Inspección ficticia de condiciones',
                       'Chequeo ficticio sin novedades.', area=area, condiciones_revisadas=list(CONDICIONES),
                       estado_condiciones='seguro', sin_hallazgos='on', estado_accion='no_requiere')
        self.anotar('INDUCCION-SEGURIDAD', '8.3 Inspecciones', 'PRUEBA-INSP-01', 'Evidencia verificada', area[:30])
        self._exige_equipo()
        titulo = PREFIJO + 'Incidente de seguridad ficticio'
        self._incidencia('seguridad', titulo, PREFIJO + 'Salpicadura ficticia sin lesiones.',
                         PREFIJO + 'Se limpió el área ficticia.')
        self.anotar('INDUCCION-SEGURIDAD', '8.6 Incidentes de seguridad', 'PRUEBA-EQ-01', 'Resuelto', titulo)

    def desechos(self):
        from apps.recursos.models.desechos import RegistroDesecho

        ruta = reverse('entregas_desechos_unidad', args=[self.slug])
        exigir(self.web.post(ruta, {
            'accion': 'generar', 'desecho-fecha_generacion': self.hoy.isoformat(),
            'desecho-nombre': PREFIJO + 'Solventes usados ficticios', 'desecho-clase': 'peligroso',
            'desecho-clave_listado': 'PRUEBA-Q-01', 'desecho-estado_fisico': 'liquido',
            'desecho-origen': PREFIJO + 'Limpieza ficticia', 'desecho-cantidad': '1.5', 'desecho-unidad_medida': 'l',
            'desecho-envase': PREFIJO + 'Bidón ficticio', 'desecho-etiquetado': 'on',
            'desecho-almacenamiento': PREFIJO + 'Bodega ficticia', 'desecho-etapa': 'almacenado',
            'desecho-responsable': self.admin.pk, 'desecho-observaciones': ''}), 302, que='Registrar desecho generado')
        desecho = RegistroDesecho.objects.get(unidad=self.unidad, clave_listado='PRUEBA-Q-01')
        exigir(self.web.post(ruta, {
            'desechos': [desecho.pk], 'fecha_entrega': self.hoy.isoformat(),
            'gestor_autorizado': PREFIJO + 'Gestor ficticio', 'licencia_gestor': 'PRUEBA-LIC-01',
            'manifiesto': 'PRUEBA-MAN-01', 'responsable': self.admin.pk,
            'documento': archivo_pdf('PRUEBA-MAN-01', PREFIJO + 'Manifiesto ficticio')}), 302, que='Entrega al gestor')
        desecho.refresh_from_db()
        if desecho.etapa != 'entregado':
            raise FalloDePaso(f'El desecho quedó en «{desecho.etapa}».')
        self.anotar('DESECHOS', '9.1 y 9.2 Generación y entrega', 'PRUEBA-MAN-01', 'Entregado con manifiesto',
                    'PRUEBA-Q-01', 'PRUEBA-MAN-01')

    def resultados(self):
        proyecto = PREFIJO + 'Proyecto ficticio de la carga'
        self.evidencia('INVESTIGACION', 'PRUEBA-INV-01', 'Prototipo ficticio', 'Prototipo ficticio con su informe.',
                       proyecto=proyecto, tipo_producto='prototipo', producto=PREFIJO + 'Prototipo ficticio',
                       beneficiario=PREFIJO + 'Grupo ficticio')
        self.anotar('INVESTIGACION', '10.1 Resultados', 'PRUEBA-INV-01', 'Evidencia verificada', 'PRUEBA-INV-01')
        self.evidencia('TRANSFERENCIA', 'PRUEBA-TRF-01', 'Capacitación técnica ficticia', 'Entrega ficticia aceptada.',
                       proyecto=proyecto, tipo_producto='asistencia', producto=PREFIJO + 'Manual ficticio',
                       beneficiario=PREFIJO + 'Asociación ficticia', aceptacion='aceptado',
                       fecha_aceptacion=self.hoy.isoformat(), referencia_aceptacion='PRUEBA-ACEPTACION-01')
        self.anotar('TRANSFERENCIA', '11.1 Transferencias', 'PRUEBA-TRF-01', 'Evidencia verificada',
                    'PRUEBA-ACEPTACION-01')

    def respaldo_de_gestion(self):
        self.evidencia('CAPACITACION', 'PRUEBA-CAP-01', 'Curso ficticio de bioseguridad', 'Certificado ficticio.')
        self.evidencia('DIFUSION', 'PRUEBA-DIF-01', 'Nota ficticia de difusión', 'Publicación ficticia.')
        self.anotar('capacitacion', 'Capacitación y difusión', 'PRUEBA-CAP-01 · PRUEBA-DIF-01', 'Evidencia verificada',
                    'PRUEBA-CAP-01', 'PRUEBA-DIF-01')
        self.evidencia('SIMULACRO', 'PRUEBA-SIM-01', 'Simulacro ficticio de evacuación', 'Evacuación ficticia.',
                       emergencia='sismo', participantes='5', accion_mejora=PREFIJO + 'Acción de mejora ficticia.')
        self.anotar('simulacros', 'Simulacros', 'PRUEBA-SIM-01', 'Evidencia verificada', 'Simulacro ficticio')

    # -- documentos principales ------------------------------------------------------------------------

    @property
    def expediente(self):
        return reverse('gestion_expediente_unidad', args=[self.slug])

    def documento(self, codigo):
        from apps.documentos.models.expediente import DocumentoExpediente

        corte = '' if codigo in ('RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'REGLAMENTO-USO',
                                 'PLAN-COMPRAS-ANUAL') else self.corte
        documento = (DocumentoExpediente.objects.select_related('exigido', 'recurso')
                     .filter(unidad=self.unidad, exigido__codigo=codigo, anio=self.anio, corte=corte).first())
        if documento is None:
            raise FalloDePaso(f'El expediente {self.anio} no tiene el documento {codigo}.')
        return documento

    def preparar_expediente(self):
        from apps.documentos.models.expediente import DocumentoExpediente

        if DocumentoExpediente.objects.filter(unidad=self.unidad, anio=self.anio).exists():
            self.pasos.append(Paso('El expediente ya estaba preparado', 'aviso'))
            return
        respuesta = self.web.post(self.expediente, dict(anio=self.anio, corte=self.corte, accion='preparar'),
                                  follow=True)
        if not DocumentoExpediente.objects.filter(unidad=self.unidad, anio=self.anio).exists():
            raise FalloDePaso(f'«Preparar expediente para trabajar» no creó las filas: {_detalle(respuesta)}')

    def _ya_enviado(self, documento, codigo):
        if documento.estado == 'validado':
            self.anotar(codigo, 'Documento', documento.exigido.codigo, 'Ya estaba enviado: no se toca')
            return True
        return False

    def resolucion(self):
        from apps.documentos.presentation.expediente_archivos import identidad_documental

        documento = self.documento('RESOLUCION-CREACION')
        if self._ya_enviado(documento, 'RESOLUCION-CREACION'):
            return
        confirmacion = {f'correspondencia_{k}': '' if v is None else str(v)
                        for k, v in dict(identidad_documental(documento), version=documento.version).items()}
        confirmacion['correspondencia_confirmada'] = '1'
        respuesta = self.web.post(self.expediente, dict(
            anio=self.anio, corte=self.corte, documento=documento.pk, accion='cargar', enviar='1',
            archivo=archivo_pdf('PRUEBA-RESOLUCION', PREFIJO + 'Resolución de creación ficticia'), **confirmacion),
            follow=True)
        documento.refresh_from_db()
        if documento.estado != 'validado':
            raise FalloDePaso(f'La resolución quedó en «{documento.estado}»: {_detalle(respuesta)}')
        self.decidir_direccion(documento)

    def _editor(self, documento):
        ruta = reverse('redactar_documento_expediente', args=[self.slug, documento.pk])
        return ruta, exigir(self.web.get(ruta), 200, que=f'Editor de {documento.exigido.codigo}').content.decode()

    def guardar_editor(self, documento, cambios):
        """Lo que envía el editor al guardar: todos sus campos, con lo que cambió la persona."""
        ruta, html = self._editor(documento)
        lector = FormulariosDePagina()
        lector.feed(html)
        formulario = next((f for f in lector.formularios if any(n == 'version_base' for n, _v in f['campos'])), None)
        if formulario is None:
            raise FalloDePaso(f'El editor de {documento.exigido.codigo} no dibuja su formulario.')
        if callable(cambios):
            cambios = cambios(formulario)
        datos = QueryDict(mutable=True)
        for nombre, valor in formulario['campos']:
            if nombre not in cambios:
                datos.appendlist(nombre, valor)
        for nombre, valor in cambios.items():
            datos.setlist(nombre, valor if isinstance(valor, list) else [valor])
        respuesta = self.web.post(ruta, datos.urlencode(), content_type='application/x-www-form-urlencoded',
                                  HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        exigir(respuesta, 200, que=f'Guardar {documento.exigido.codigo}')
        return ruta, respuesta.json()

    def generar_y_enviar(self, documento, ruta, version):
        respuesta = self.web.post(ruta, dict(version_base=version, accion='generar_enviar_guardado'),
                                  HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        exigir(respuesta, 200, que=f'Generar y enviar {documento.exigido.codigo}')
        documento.refresh_from_db()
        if documento.estado != 'validado':
            raise FalloDePaso(f'{documento.exigido.codigo} quedó en «{documento.estado}».')

    def abrir_entrega(self, documento):
        """Con el plazo vencido, la entrega la abre el ultimátum colectivo de la Dirección."""
        from apps.documentos.presentation.incumplimiento_documental import establecer_ultimatum

        documento.refresh_from_db()
        if documento.entrega_abierta:
            return
        if not (documento.vencido and not documento.prorroga_activa):
            raise FalloDePaso(f'La entrega de {documento.exigido.codigo} no está abierta todavía.')
        if not self.abrir_con_ultimatum:
            raise FalloDePaso(f'Plazo vencido de {documento.exigido.codigo} y sin ultimátum vigente para la unidad: '
                              'corresponde a la Dirección fijarlo (o --abrir-con-ultimatum en una copia).')
        hasta = max(timezone.localtime().replace(year=2026, month=12, day=15, hour=23, minute=59, second=0,
                                                  microsecond=0), timezone.localtime() + timedelta(days=5))
        establecer_ultimatum(documento, self.direccion, hasta.strftime('%Y-%m-%dT%H:%M'),
                             PREFIJO + 'Ultimátum de ensayo para la carga de prueba.')
        documento.refresh_from_db()
        if not documento.entrega_abierta:
            raise FalloDePaso(f'El ultimátum no abrió la entrega de {documento.exigido.codigo}.')
        self.pasos.append(Paso(f'Ultimátum colectivo de {documento.exigido.codigo}', 'aviso',
                               f'hasta {hasta:%d/%m/%Y %H:%M}'))

    def redactado(self, codigo, cambios, *, antes=None):
        documento = self.documento(codigo)
        if self._ya_enviado(documento, codigo):
            return
        self.abrir_entrega(documento)
        if antes:
            antes()
        ruta, guardado = self.guardar_editor(documento, cambios)
        if guardado.get('faltantes'):
            raise FalloDePaso(f'Faltan apartados: {"; ".join(guardado["faltantes"])[:400]}')
        self.generar_y_enviar(documento, ruta, guardado['version'])
        self.decidir_direccion(documento)

    def decidir_direccion(self, documento):
        """«Aprobar» en Cumplimiento del expediente: la misma función que llama esa pantalla."""
        from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
        from apps.documentos.presentation.revision_documental import decidir_desde_listado

        documento.refresh_from_db()
        decidir_desde_listado(documento, self.direccion, version=documento.version,
                              huella=documento.recurso.hash_sha256, decision='aprobar')
        documento.refresh_from_db()
        estado = 'Enviado y aprobado por la Dirección' if (documento.cumple or aprobacion_vigente(documento)) else (
            f'Enviado; Dirección: {documento.get_estado_display()}')
        self.anotar(documento.exigido.codigo, 'Documento', documento.exigido.codigo, estado)

    def planificacion(self):
        documento = self.documento('PLANIFICACION')

        def cambios(formulario):
            datos = dict(sectores=['docencia'], estado_operativo='B', revision_recursos='revisado',
                         uso_justificacion=PREFIJO + 'Prácticas y sesiones previstas dentro de la jornada.')
            for nombre, _valor in formulario['campos']:
                if nombre.startswith('uso_horas__'):
                    datos[nombre] = '4'
                elif nombre.startswith('act__') and nombre.endswith('__responsable'):
                    datos[nombre] = PREFIJO + (self.admin.get_full_name() or self.admin.username)
            return datos

        if self._ya_enviado(documento, 'PLANIFICACION'):
            return
        self.redactado('PLANIFICACION', cambios)

    def informe(self):
        documento = self.documento('INFORME-SEMESTRAL')
        if self._ya_enviado(documento, 'INFORME-SEMESTRAL'):
            return
        _ruta, guardado = self.guardar_editor(documento, dict(
            logros=f'<ul><li>{PREFIJO}Logro ficticio de la carga de prueba.</li></ul>'))
        documento.refresh_from_db()
        abre = getattr(documento, 'abre_el', None)
        faltan = guardado.get('faltantes') or []
        estado = 'Borrador guardado' + (f'; la entrega se abre el {abre:%d/%m/%Y}' if abre else '')
        if faltan:
            estado += f'; faltan: {"; ".join(faltan)[:200]}'
        self.anotar('INFORME-SEMESTRAL', 'Documento', 'INFORME-SEMESTRAL', estado)

    # -- comprobación en los documentos generados ----------------------------------------------------

    def verificar(self):
        """Genera cada anexo y cada documento de respaldo y busca en su texto el registro cargado."""
        textos, self.no_generados = {}, {}
        for registro in self.registros:
            if registro.estado.startswith('NO CARGADO'):
                registro.aparece = '—'
                continue
            if not registro.buscar:
                registro.aparece = 'n/a'
                continue
            if registro.documento not in textos:
                textos[registro.documento] = self._texto_del_documento(registro.documento)
            texto = textos[registro.documento]
            if texto is None:
                registro.aparece = f'NO SE GENERÓ ({self.no_generados.get(registro.documento, "")})'
                continue
            faltan = [b for b in registro.buscar if texto_plano(b) not in texto]
            registro.aparece = 'sí' if not faltan else 'NO APARECE: ' + ', '.join(faltan)

    def ruta_del_anexo(self, codigo):
        """«Borrador al día» del anexo en el informe semestral del período, como lo abre el Centro de reportes."""
        from apps.documentos.presentation.documentos_entrega import ruta_borrador
        from apps.documentos.presentation.expediente import anexos_del, construir_expediente

        informe = next(d for d in construir_expediente(self.unidad, self.anio, hoy=self.hoy)
                       if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == self.corte)
        return ruta_borrador(next(a for a in anexos_del(informe, incluir_no_aplica=True)
                                  if a.exigido.codigo == codigo))

    def _texto_del_documento(self, documento):
        try:
            if documento in dict(ANEXOS):
                ruta = self.ruta_del_anexo(documento)
                for registro in self.registros:
                    if registro.documento == documento:
                        registro.donde = ruta
                respuesta = self.web.get(ruta)
            else:
                respuesta = self.web.get(reverse('gestion_reporte_unidad', args=[self.slug]), dict(
                    categoria_reporte=documento, desde=self.inicio.isoformat(), hasta=self.fin.isoformat(),
                    formato='pdf'))
                if respuesta.get('Content-Type') != 'application/pdf':
                    respuesta = self.web.get(reverse('gestion_reporte_unidad_pdf', args=[self.slug]), dict(
                        categoria_reporte=documento, desde=self.inicio.isoformat(), hasta=self.fin.isoformat()))
        except Exception as error:  # noqa: BLE001 - un documento que no se genera se informa, no detiene la tabla
            self.no_generados[documento] = f'{type(error).__name__}: {str(error)[:200]}'
            return None
        if respuesta.status_code != 200 or respuesta.get('Content-Type') != 'application/pdf':
            self.no_generados[documento] = f'respuesta {respuesta.status_code} {respuesta.get("Content-Type")}'
            return None
        contenido = respuesta.getvalue() if getattr(respuesta, 'streaming', False) else respuesta.content
        return texto_plano(texto_del_pdf(contenido))

    def tabla(self):
        """Documento · registro cargado · estado alcanzado · aparece · dónde verlo, en el orden del Centro de reportes."""
        orden = [c for c, _n in ANEXOS + RESPALDO + PRINCIPALES]
        filas = sorted(self.registros, key=lambda r: orden.index(r.documento) if r.documento in orden else 99)
        cubiertos = {r.documento for r in filas}
        for codigo in orden:
            if codigo not in cubiertos:
                filas.append(Registro(codigo, '—', '—', 'NO CARGADO', ''))
        filas.sort(key=lambda r: orden.index(r.documento))
        return filas
