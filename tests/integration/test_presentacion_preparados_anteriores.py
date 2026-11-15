"""Los PDF preparados antes del QR comparten el diseño sin cambiar su entrega."""
from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, ArrayObject, TextStringObject, NumberObject
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from apps.documentos.presentation.expediente import _archivar
from apps.documentos.presentation.validacion_pdf import copia_para_recurso
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from tests.integration.test_expediente_redaccion import BaseDeRedaccion


class PresentacionPreparadosAnterioresTests(BaseDeRedaccion):
    def preparar_anterior(self, *, auditar=True, firmado=False):
        d = self.documento('INFORME-SEMESTRAL')
        buffer = BytesIO()
        estilos = getSampleStyleSheet()
        pdf = SimpleDocTemplate(buffer, title='Informe semestral de actividades - Unidad archivada',
            topMargin=100, bottomMargin=70)
        elementos = [Paragraph('1. INFORMACIÓN GENERAL', estilos['Heading2'])]
        tabla = Table([['Tipo de unidad', 'Laboratorio'], ['Nombre', 'Unidad archivada'],
            ['Equipo de la unidad', 'Ana Archivada (Coordinación); Luis Técnico (Responsable técnico)']])
        tabla.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .3, 'black'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold')]))
        elementos.extend([tabla, Paragraph('2. RESULTADOS DEL PERÍODO', estilos['Heading2'])])
        tabla = Table([['Actividad', 'Cantidad'], ['Sesiones', '17'], ['Prácticas ejecutadas', '0']])
        tabla.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .3, 'black'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
        elementos.extend([tabla, Paragraph('3. FIRMAS DE RESPONSABILIDAD', estilos['Heading2'])])
        tabla = Table([['Elaborado por', 'Ana Archivada · Responsable de la unidad']])
        tabla.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .3, 'black'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold')]))
        elementos.append(tabla)

        def encabezado(canvas, _):
            canvas.setFont('Helvetica', 8)
            for y, texto in [(820, 'Código: AP-P-LAP-GO · Informe'), (809, 'Cobertura: Período 2026-A'),
                    (798, 'Versión del documento: 1'), (787, '09/03/2026 - 10/07/2026')]:
                canvas.drawString(45, y, texto)
            canvas.drawString(45, 775, 'Informe semestral de actividades')
        pdf.build(elementos, onFirstPage=encabezado)
        contenido = buffer.getvalue()
        if firmado:
            writer = PdfWriter()
            writer.clone_document_from_reader(PdfReader(BytesIO(contenido)))
            campo = DictionaryObject({NameObject('/FT'): NameObject('/Sig'),
                NameObject('/T'): TextStringObject('FirmaExistente')})
            referencia = writer._add_object(campo)
            if firmado == 'widget':
                widget = DictionaryObject({NameObject('/Subtype'): NameObject('/Widget'),
                    NameObject('/Parent'): referencia,
                    NameObject('/Rect'): ArrayObject([NumberObject(v) for v in (10, 10, 150, 50)])})
                writer.pages[0][NameObject('/Annots')] = ArrayObject([writer._add_object(widget)])
            else:
                writer._root_object[NameObject('/AcroForm')] = DictionaryObject({
                    NameObject('/Fields'): ArrayObject([referencia])})
            salida = BytesIO()
            writer.write(salida)
            contenido = salida.getvalue()
        _archivar(d, contenido, 'informe-anterior.pdf', autor='Ana Archivada', descripcion='Informe preparado', tipo_adjunto='informe')
        d.estado = 'generado'
        d.generado_en = timezone.now()
        d.save()
        if auditar:
            registrar_auditoria(unidad=d.unidad, usuario=self.coordinador, accion='actualizar', objeto=d,
                descripcion='_generar: INFORME-SEMESTRAL', nuevos=dict(recurso_id=d.recurso_id,
                    version=d.version, unidad_id=d.unidad_id, exigido_id=d.exigido_id, estado='generado'))
        return d, contenido

    def test_ver_y_descargar_renuevan_el_mismo_contenido_sin_modificar_la_entrega(self):
        d, original = self.preparar_anterior()
        antes = (d.version, d.estado, d.recurso_id, d.verificacion_qr, d.generado_en)
        self.unidad.nombre = 'Nombre actual que no debe reemplazar el archivo'
        self.unidad.save(update_fields=['nombre'])
        with patch('apps.documentos.presentation.expediente_redaccion.componer', side_effect=AssertionError):
            copia = copia_para_recurso(d.recurso)
            self.assertEqual(copia, copia_para_recurso(d.recurso))
        pdf = PdfReader(BytesIO(copia))
        texto = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        self.assertTrue(pdf.outline)
        self.assertIn('FORMATO INFORME SEMESTRAL', texto)
        self.assertIn('Unidad archivada', texto)
        self.assertIn('Ana Archivada', texto)
        self.assertIn('17', texto)
        self.assertIn('0', texto)
        self.assertNotIn(self.unidad.nombre, texto)
        self.assertNotIn('DOCUMENTO APROBADO', texto)
        self.assertNotIn('SLCID-DOC-1:', str(pdf.metadata))
        self.client.force_login(self.coordinador)
        for sufijo in ('', '?download=1'):
            respuesta = self.client.get(reverse('recurso_unidad', args=[d.recurso_id]) + sufijo)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(b''.join(respuesta.streaming_content), copia)
        d.refresh_from_db()
        self.assertEqual(antes, (d.version, d.estado, d.recurso_id, d.verificacion_qr, d.generado_en))
        with d.recurso.archivo.open('rb') as f:
            self.assertEqual(f.read(), original)

    def test_una_carga_sin_generacion_auditada_no_se_reformatea(self):
        d, _ = self.preparar_anterior(auditar=False)
        self.assertIsNone(copia_para_recurso(d.recurso))

    def test_un_pdf_firmado_no_se_reformatea(self):
        d, _ = self.preparar_anterior(firmado=True)
        self.assertIsNone(copia_para_recurso(d.recurso))

    def test_una_firma_de_pagina_sin_arbol_de_campos_se_conserva(self):
        d, _ = self.preparar_anterior(firmado='widget')
        self.assertIsNone(copia_para_recurso(d.recurso))

    def test_un_archivo_alterado_no_se_presenta_como_preparado(self):
        d, _ = self.preparar_anterior()
        with d.recurso.archivo.open('ab') as f:
            f.write(b'\n% alterado')
        with self.assertRaisesMessage(ValidationError, 'fue modificado'):
            copia_para_recurso(d.recurso)

    def test_una_entrega_validada_no_se_reformatea_sin_constancia(self):
        d, _ = self.preparar_anterior()
        d.estado = 'validado'
        d.save(update_fields=['estado'])
        self.assertIsNone(copia_para_recurso(d.recurso))
