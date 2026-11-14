"""Bloque de responsables y copia aprobada del PDF, sin cambiar el original emitido."""
import hashlib
from io import BytesIO
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepInFrame, Paragraph

NOMBRE_FORMULARIO = 'SLCIDValidacion'
FORMATO = 5
ALTO = 46 * mm


def _fecha(valor):
    if not valor:
        return ''
    local = timezone.localtime(valor)
    meses = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
             'septiembre', 'octubre', 'noviembre', 'diciembre')
    return f'{local.day:02d} de {meses[local.month - 1]} de {local.year} {local:%H:%M}'


def dibujar_bloque(canvas, ancho, datos, alto=ALTO):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import createBarcodeDrawing
    from apps.core.reportes import _fuentes_pdf
    regular, negrita = _fuentes_pdf()
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#6b7a73'))
    canvas.setLineWidth(.6)
    canvas.setDash(2, 2)
    canvas.line(0, alto, ancho, alto)
    canvas.line(0, 0, ancho, 0)
    canvas.setDash()
    estilo = ParagraphStyle('validacion', fontName=regular, fontSize=9, leading=12,
        textColor=colors.HexColor('#24392d'))
    if datos.get('url'):
        qr = createBarcodeDrawing('QR', value=datos['url'], width=32*mm, height=32*mm)
        renderPDF.draw(qr, canvas, 0, (alto - 32*mm) / 2)
    espacio_qr = 37 * mm if datos.get('url') else 0
    columna = (ancho - espacio_qr) / 2
    titulo = 'DOCUMENTO APROBADO POR DIRECCIÓN' if datos.get('aprobado_en') else 'DOCUMENTO EMITIDO PARA REVISIÓN'
    canvas.setFont(negrita, 10)
    canvas.setFillColor(colors.HexColor('#29653f'))
    canvas.drawString(espacio_qr, alto - 6*mm, titulo)
    for i, (rol, nombre, cedula, fecha) in enumerate((
        ('ELABORADO POR', datos.get('emisor', ''), datos.get('emisor_cedula'), datos.get('emitido_en')),
        ('APROBADO POR', datos.get('aprobador') or 'Pendiente de aprobación', datos.get('aprobador_cedula'), datos.get('aprobado_en')),
    )):
        x = espacio_qr + i * columna
        texto = f'<font size="8.5" color="#29653f"><b>{rol}</b></font><br/>'
        texto += f'<b>{escape(nombre.upper())}</b><br/>'
        texto += f'<font color="#60736a">Cédula:</font> <b>{escape(cedula or "No registrada")}</b><br/>'
        if fecha:
            texto += '<font color="#60736a">Fecha y hora:</font><br/><b>' + _fecha(fecha) + '</b>'
        p = Paragraph(texto, estilo)
        contenido = KeepInFrame(columna - 4*mm, alto - 20*mm, [p], mode='shrink', hAlign='LEFT')
        _, alto_texto = contenido.wrapOn(canvas, columna - 4*mm, alto - 20*mm)
        contenido.drawOn(canvas, x, alto - 11*mm - alto_texto)
    leyenda = 'Verifique la autenticidad del documento mediante el código QR.' if datos.get('url') else ''
    canvas.setFont(regular, 6.8)
    canvas.setFillColor(colors.HexColor('#586b5e'))
    canvas.drawString(espacio_qr, 3*mm, leyenda)
    canvas.restoreState()


class BloqueValidacion(Flowable):
    def __init__(self, datos, alto=ALTO):
        super().__init__()
        self.datos, self.height = datos, alto

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return self.width, self.height

    def draw(self):
        self.canv.beginForm(NOMBRE_FORMULARIO, 0, 0, self.width, self.height)
        dibujar_bloque(self.canv, self.width, self.datos, self.height)
        self.canv.endForm()
        self.canv.doForm(NOMBRE_FORMULARIO)
        if self.datos.get('url'):
            self.canv.linkURL(self.datos['url'], (0, 0, self.width, self.height), relative=1, thickness=0)


def datos_de_emision(documento):
    from .aprobacion_en_linea import url_verificacion, cedula_del_usuario
    token = getattr(documento, '_token_emision', None)
    actor = getattr(documento, '_emisor_emision', None)
    if not token or actor is None:
        return None
    return dict(url=url_verificacion(token), emisor=actor.get_full_name() or actor.get_username(),
        emisor_cedula=cedula_del_usuario(actor), emitido_en=timezone.now(), version=documento.version + 1)


def _formulario(pagina):
    objetos = pagina.get('/Resources', {}).get('/XObject', {})
    return next(((clave, valor) for clave, valor in objetos.items()
        if NOMBRE_FORMULARIO in str(clave)), None)


def _representar_aprobada(contenido, constancia):
    """Representación determinista: mismo QR, cuerpo emitido y responsables registrados."""
    from pypdf import PdfReader, PdfWriter
    if hashlib.sha256(contenido).hexdigest() != constancia.sha256:
        raise ValidationError('El archivo emitido fue modificado.')
    from .contenido_emitido import recuperar_del_pdf, restaurar_compuesto
    from .expediente_pdf import render_documento_pdf
    datos_archivados = constancia.contenido_emitido or recuperar_del_pdf(contenido, constancia)
    salida = render_documento_pdf(restaurar_compuesto(datos_archivados, constancia))
    lector_nuevo = PdfReader(BytesIO(salida))
    escritor_nuevo = PdfWriter()
    escritor_nuevo.clone_document_from_reader(lector_nuevo)
    escritor_nuevo.add_metadata({'/SLCIDFormatoValidacion': str(FORMATO)})
    final_nuevo = BytesIO()
    escritor_nuevo.write(final_nuevo)
    return final_nuevo.getvalue()


def copia_aprobada(contenido, constancia):
    """Conserva la copia aprobada y sus presentaciones sin sustituir descargas anteriores."""
    from django.core.files.base import ContentFile
    from django.db import transaction
    from apps.documentos.models.constancias import ConstanciaDocumento
    from .expediente_operaciones import recordar_archivo
    if hashlib.sha256(contenido).hexdigest() != constancia.sha256:
        raise ValidationError('El archivo emitido fue modificado.')
    if not constancia.aprobado_en:
        return contenido
    creado = None
    try:
        with transaction.atomic():
            actual = ConstanciaDocumento.objects.select_for_update().get(pk=constancia.pk)
            if actual.sha256 != constancia.sha256:
                raise ValidationError('La identidad de la versión no corresponde al archivo emitido.')
            if not actual.aprobado_en:
                return contenido
            if actual.archivo_aprobado:
                try:
                    with actual.archivo_aprobado.open('rb') as archivo:
                        copia = archivo.read()
                except OSError as error:
                    raise ValidationError('La copia aprobada no está disponible.') from error
                if hashlib.sha256(copia).hexdigest() != actual.sha256_aprobado:
                    raise ValidationError('La copia aprobada fue modificada.')
                from pypdf import PdfReader
                if str((PdfReader(BytesIO(copia)).metadata or {}).get('/SLCIDFormatoValidacion', '')) != str(FORMATO):
                    from apps.documentos.models.constancias import PresentacionDocumento
                    presentacion = actual.presentaciones.filter(formato=FORMATO,aprobada=True).first()
                    if presentacion:
                        with presentacion.archivo.open('rb') as archivo:
                            copia = archivo.read()
                        if hashlib.sha256(copia).hexdigest() != presentacion.sha256:
                            raise ValidationError('La copia de presentación fue modificada.')
                    else:
                        copia = _representar_aprobada(contenido, actual)
                        presentacion = PresentacionDocumento(constancia=actual, formato=FORMATO,
                            sha256=hashlib.sha256(copia).hexdigest())
                        presentacion.archivo.save(f'{actual.token}-formato-{FORMATO}.pdf', ContentFile(copia), save=False)
                        creado = (presentacion.archivo.storage, presentacion.archivo.name)
                        recordar_archivo(presentacion.archivo)
                        presentacion.save()
            else:
                copia = _representar_aprobada(contenido, actual)
                actual.archivo_aprobado.save(f'{actual.token}.pdf', ContentFile(copia), save=False)
                creado = (actual.archivo_aprobado.storage, actual.archivo_aprobado.name)
                recordar_archivo(actual.archivo_aprobado)
                actual.sha256_aprobado = hashlib.sha256(copia).hexdigest()
                actual.save(update_fields=['archivo_aprobado', 'sha256_aprobado'])
            constancia.archivo_aprobado = actual.archivo_aprobado
            constancia.sha256_aprobado = actual.sha256_aprobado
            return copia
    except Exception:
        if creado:
            creado[0].delete(creado[1])
        raise


def copia_para_recurso(recurso):
    from apps.documentos.models.constancias import ConstanciaDocumento
    c = ConstanciaDocumento.objects.filter(recurso_id=recurso.pk,
        observado_en__isnull=True, documento__estado__in=('generado','validado'),
        documento__verificacion_qr__isnull=False).select_related('documento').first()
    if not c:
        from apps.documentos.models.expediente import DocumentoExpediente
        from .contenido_emitido import recuperar_preparado_anterior
        from .expediente_pdf import render_documento_pdf
        documento = DocumentoExpediente.objects.filter(recurso=recurso, estado='generado',
            verificacion_qr__isnull=True, exigido__fuente_reporte__in=('planificacion', 'informe', 'compras', 'mejora')
        ).select_related('recurso', 'exigido').first()
        if not documento:
            return None
        with recurso.archivo.open('rb') as archivo:
            compuesto = recuperar_preparado_anterior(archivo.read(), documento)
        return render_documento_pdf(compuesto) if compuesto else None
    if (c.documento.verificacion_qr != c.token or c.documento.recurso_id != recurso.pk
            or c.documento.version != c.version or recurso.estado != 'vigente'):
        return None
    with recurso.archivo.open('rb') as archivo:
        return copia_aprobada(archivo.read(), c) if c.aprobado_en else copia_preparada(archivo.read(),c)


def copia_preparada(contenido, constancia):
    """La vista de una emisión pendiente usa el mismo contenido y conserva cada descarga."""
    from django.core.files.base import ContentFile
    from django.db import transaction
    from apps.documentos.models.constancias import ConstanciaDocumento, PresentacionDocumento
    from .expediente_operaciones import recordar_archivo
    if hashlib.sha256(contenido).hexdigest()!=constancia.sha256:
        raise ValidationError('El archivo emitido fue modificado.')
    creado=None
    try:
        with transaction.atomic():
            actual=ConstanciaDocumento.objects.select_for_update().get(pk=constancia.pk)
            if actual.aprobado_en:
                return copia_aprobada(contenido,actual)
            presentacion=actual.presentaciones.filter(formato=FORMATO,aprobada=False).first()
            if presentacion:
                with presentacion.archivo.open('rb') as archivo:
                    copia=archivo.read()
                if hashlib.sha256(copia).hexdigest()!=presentacion.sha256:
                    raise ValidationError('La copia de presentación fue modificada.')
            else:
                copia=_representar_aprobada(contenido,actual)
                presentacion=PresentacionDocumento(constancia=actual,formato=FORMATO,aprobada=False,
                    sha256=hashlib.sha256(copia).hexdigest())
                presentacion.archivo.save(f'{actual.token}-formato-{FORMATO}-emitido.pdf',ContentFile(copia),save=False)
                creado=(presentacion.archivo.storage,presentacion.archivo.name)
                recordar_archivo(presentacion.archivo)
                presentacion.save()
            return copia
    except Exception:
        if creado:
            creado[0].delete(creado[1])
        raise
