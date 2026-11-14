"""Documentos separados de gestión, fechas reales y rectificación trazable de anexos."""

from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ValidationError
from tests.integration.utiles import (cargar_documento_revisado)
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.expediente import (
    anexos_del, leer_expediente, observar_documento, rectificar_anexo, validar_anexo, validar_documento,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from tests.integration.test_cumplimiento_expediente import PDF_FIRMADO
from apps.documentos.presentation.expediente_archivos import versiones_del_documento
from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente, ANIO


class DocumentosYRectificacionTests(BaseDelExpediente):
    def modal(self, d, vista, **datos):
        return self.client.get(
            reverse('gestion_expediente_unidad', args=[d.unidad.slug]),
            dict(anio=ANIO, corte=d.corte, gestionar=d.pk, vista=vista, fragment='1', **datos),
        )

    def test_tabla_compacta_separa_estado_avance_fechas_y_acciones(self):
        d, ruta = self.archivado(self.laboratorio)
        html = self.client.get(ruta, dict(anio=ANIO, corte=d.corte)).content.decode()
        tabla = html.split('<table class="entregas__tabla entregas__tabla--simple">')[1].split('</table>')[0]
        self.assertNotIn('>Borrador</th>', tabla)
        for encabezado in ('Documento', 'Estado', 'Avance', 'Fechas', 'Observaciones', 'Acciones'):
            self.assertIn(f'>{encabezado}</th>', tabla)
        for texto in ('>PDF</th>', '>Versiones</a>', '>Ver borrador</a>', '>Anexos ('):
            self.assertNotIn(texto, tabla)
        self.assertIn('data-entrega-editor', tabla)
        self.assertContains(self.modal(d, 'anexos'), 'data-cierre-indicadores')
        self.assertContains(self.modal(d, 'versiones'), 'data-entrega-versiones')

    def test_fechas_no_confunden_carga_con_envio_ni_recepcion_con_evaluacion(self):
        d, _ = self.archivado(self.laboratorio)
        self.assertIsNotNone(d.entregado_en)  # Marca técnica de la carga, no del envío.
        self.assertIsNone(resumen_de_entrega(d)['fecha_envio'])
        for a in anexos_del(d):
            validar_anexo(a, self.coordinador)
        validar_documento(d, self.coordinador)
        d.refresh_from_db()
        self.assertEqual(resumen_de_entrega(d)['fecha_envio'], d.validado_en)
        d.recibido_en = timezone.now()
        self.assertIsNone(resumen_de_entrega(d)['fecha_revision'])
        d.evaluado_en = timezone.now()
        self.assertEqual(resumen_de_entrega(d)['fecha_revision'], d.evaluado_en)
        self.assertEqual(resumen_de_entrega(d)['tipo_revision'], 'Evaluado')
        d.evaluado_en = None
        d.estado = 'observado'
        self.assertEqual(resumen_de_entrega(d)['fecha_revision'], d.validado_en)
        self.assertEqual(resumen_de_entrega(d)['tipo_revision'], 'Observado')
        d.refresh_from_db()
        envio = d.validado_en
        observar_documento(d, self.direccion, 'Corregir y reenviar', hasta=timezone.now() + timedelta(days=3))
        observado = next(f for f in leer_expediente(d.unidad, ANIO) if f.pk == d.pk)
        self.assertEqual(resumen_de_entrega(observado)['fecha_envio'], envio)

    def test_retirar_revision_actualizar_y_reenviar_conserva_archivo(self):
        d = self.documento(self.laboratorio, codigo='PLANIFICACION')
        self.abrir_plazo(d)
        cargar_documento_revisado(d, SimpleUploadedFile('plan.pdf', PDF_FIRMADO), self.coordinador)
        ruta = reverse('gestion_expediente_unidad', args=[d.unidad.slug])
        self.client.force_login(self.coordinador)
        anexos = anexos_del(d)
        a = anexos[0]
        for otro in anexos:
            validar_anexo(otro, self.coordinador)
        archivo, version = a.recurso_id, a.version
        ruta_anterior = Path(a.recurso.archivo.path)
        contenido = ruta_anterior.read_bytes()
        self.assertContains(self.modal(d, 'anexos'), 'Volver a revisar')
        self.client.post(ruta, dict(documento=a.pk, accion='rectificar_anexo', version=version))
        a.refresh_from_db()
        self.assertEqual((a.estado, a.recurso_id, a.version), ('generado', archivo, version))
        self.assertIsNone(a.validado_en)
        self.assertIsNone(a.validado_por_id)
        with self.assertRaises(ValidationError):
            validar_documento(d, self.coordinador)
        self.client.post(ruta, dict(documento=a.pk, accion='actualizar_anexo', version=version))
        a.refresh_from_db()
        self.assertEqual(a.version, version + 1)
        self.assertEqual(a.recurso.reemplaza_a_id, archivo)
        self.assertEqual(a.estado, 'generado')
        self.assertEqual(ruta_anterior.read_bytes(), contenido)
        self.assertEqual(len(versiones_del_documento(a)), 2)
        validar_anexo(a, self.coordinador)
        validar_documento(d, self.coordinador)
        d.refresh_from_db()
        self.assertEqual(d.estado, 'validado')
        self.assertIsNone(d.recibido_en)

    def test_rectificacion_rechaza_version_antigua_y_documento_principal(self):
        d, _ = self.archivado(self.laboratorio)
        a = anexos_del(d)[0]
        validar_anexo(a, self.coordinador)
        with self.assertRaises(ValidationError):
            rectificar_anexo(a, self.coordinador, a.version + 1, actualizar=True)
        a.refresh_from_db()
        self.assertEqual(a.estado, 'validado')
        with self.assertRaises(ValidationError):
            rectificar_anexo(d, self.coordinador, d.version)

    def test_enviado_protege_anexos_incluso_superadmin_hasta_devolucion(self):
        d, ruta = self.enviado(self.laboratorio)
        a = anexos_del(d)[0]
        original = (a.estado, a.recurso_id, a.version, a.validado_en)
        self.client.force_login(self.direccion)
        self.assertNotContains(self.modal(d, 'anexos'), 'value="rectificar_anexo"')
        for accion in ['rectificar_anexo', 'actualizar_anexo', 'validar_anexo']:
            self.client.post(ruta, dict(documento=a.pk, accion=accion, version=a.version))
            a.refresh_from_db()
            self.assertEqual((a.estado, a.recurso_id, a.version, a.validado_en), original)
        with self.assertRaises(ValidationError):
            rectificar_anexo(a, self.direccion, a.version, actualizar=True)
        observar_documento(d, self.direccion, 'Corregir anexo', hasta=timezone.now() + timedelta(days=3))
        rectificar_anexo(a, self.coordinador, a.version, actualizar=True)
        a.refresh_from_db()
        self.assertEqual(a.version, original[2] + 1)
        self.assertEqual(a.estado, 'generado')

    def test_historial_anexo_solo_dentro_de_su_entrega(self):
        d, _ = self.archivado(self.laboratorio)
        a = anexos_del(d)[0]
        self.assertContains(self.modal(d, 'versiones', anexo=a.pk), a.nombre_documental)
        ajeno, _ = self.archivado(self.suelto)
        self.assertEqual(self.modal(d, 'versiones', anexo=anexos_del(ajeno)[0].pk).status_code, 404)

    def test_admin_tabla_compacta_muestra_documento_y_acciones_del_mismo_registro(self):
        documento, _ = self.archivado(self.laboratorio)
        self.client.force_login(self.direccion)
        html = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                               dict(anio=ANIO, corte=self.corte)).content.decode()
        for encabezado in ('Documento', 'Estado', 'Avance', 'Fechas', 'Observaciones', 'Acciones'):
            self.assertIn(f'<th>{encabezado}</th>', html)
        fila = html.split(f'<tr data-avance-documento="{documento.pk}">')[1].split('</tr>')[0]
        self.assertIn(documento.nombre_documental, fila)
        self.assertIn('class="documento-fechas"', fila)
        acciones = fila.split('<td class="citt-matriz__decision">')[1].split('</td>')[0]
        self.assertIn(reverse('recurso_unidad', args=[documento.recurso_id]), acciones)
        self.assertIn('data-ver-pdf', acciones)
        self.assertIn('data-decision-qr', acciones)
