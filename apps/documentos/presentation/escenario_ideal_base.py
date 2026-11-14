"""Utilidades del ensayo integral: nunca se ejecutan contra la base operativa."""
from contextlib import contextmanager
from datetime import datetime, time, timezone as timezone_datetime
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone


def exigir_entorno_ideal():
    if not (settings.DEBUG and str(connection.settings_dict['NAME']).startswith('test_citt_ideal_')
            and getattr(settings, 'ESCENARIO_IDEAL_AISLADO', False)):
        raise CommandError('El escenario ideal sólo se permite en su base de ensayo aislada.')


@contextmanager
def reloj_ideal(fecha, hora=9):
    """Simula únicamente el reloj; permisos y validaciones siguen funcionando."""
    exigir_entorno_ideal()
    hora = time(hora) if isinstance(hora, int) else hora
    instante = timezone.make_aware(datetime.combine(fecha, hora)).astimezone(timezone_datetime.utc)
    with patch('django.utils.timezone.now', return_value=instante), patch(
            'django.utils.timezone.localdate', return_value=fecha):
        yield instante


def pdf_prueba(titulo, lineas=()):
    """Respaldo sintético legible, con aviso de prueba en todas sus páginas."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape
    exigir_entorno_ideal()
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle('PruebaTitulo', parent=estilos['Title'], fontSize=15, leading=19,
        textColor=colors.HexColor('#2b633c'), alignment=TA_CENTER))
    if isinstance(lineas, str):
        lineas = lineas.splitlines()
    historia = [Paragraph(escape(str(titulo)), estilos['PruebaTitulo']), Spacer(1, 12)]
    historia.extend(Paragraph(escape(str(linea)), estilos['BodyText']) for linea in lineas)
    historia += [Spacer(1, 18), Paragraph('Escenario sintético para verificar registros, indicadores '
        'y trazabilidad de FabLab. No acredita hechos, firmas ni aprobaciones institucionales reales.', estilos['BodyText'])]
    def marco(canvas, documento):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#9c312b'))
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(A4[0] / 2, A4[1] - 27, 'PRUEBA INTEGRAL · SIN VALIDEZ INSTITUCIONAL')
        canvas.setFont('Helvetica', 8)
        canvas.drawString(40, 25, 'FabLab · datos sintéticos · entorno aislado')
        canvas.drawRightString(A4[0] - 40, 25, str(documento.page))
        canvas.restoreState()
    SimpleDocTemplate(salida, pagesize=A4, leftMargin=40, rightMargin=40,
        topMargin=55, bottomMargin=45, title='PRUEBA · ' + str(titulo)).build(
        historia, onFirstPage=marco, onLaterPages=marco)
    return salida.getvalue()


def firmar_pdf_prueba(datos):
    """Firma estructural ficticia para ejercitar la carga; no es un certificado válido."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, ByteStringObject, DictionaryObject, NameObject, NumberObject
    exigir_entorno_ideal()
    escritor = PdfWriter(clone_from=PdfReader(BytesIO(datos)))
    firma = DictionaryObject({NameObject('/Type'): NameObject('/Sig'),
        NameObject('/ByteRange'): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0), NumberObject(0)]),
        NameObject('/Contents'): ByteStringObject(b'PRUEBA SIN CERTIFICADO NI VALIDEZ')})
    campo = DictionaryObject({NameObject('/FT'): NameObject('/Sig'), NameObject('/V'): escritor._add_object(firma)})
    escritor._root_object[NameObject('/AcroForm')] = DictionaryObject({
        NameObject('/Fields'): ArrayObject([escritor._add_object(campo)])})
    salida = BytesIO()
    escritor.write(salida)
    return salida.getvalue()
