"""La tabla distingue edición, borrador y entrega sin un selector intermedio de archivos."""
import re
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.documentos.presentation.evaluacion_cierre import cierre_archivado
from apps.recursos.models.recursos import Recurso
from tests.integration.test_cumplimiento_expediente import PDF_FIRMADO
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente, ANIO
from tests.integration.utiles import (
    datos_correspondencia_revisada, evaluar_documento_revisado, recibir_documento_revisado,
)


class AccesosReportesTests(BaseDelExpediente):
    def test_tabla_ofrece_pdf_directo_y_edicion_en_otra_columna(self):
        d, _ = self.archivado(self.laboratorio)
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.laboratorio.slug]),
                                   dict(anio=ANIO, corte=d.corte))
        self.assertContains(respuesta, 'data-entrega-editor')
        self.assertContains(respuesta, 'data-editor-dialogo')
        self.assertContains(respuesta, 'data-columna="Acciones"')
        self.assertNotContains(respuesta, '<th scope="col">Borrador</th>')
        self.assertContains(respuesta, 'data-ver-pdf')
        self.assertNotContains(respuesta, 'aria-label="Ver documentos de')

    def fila(self, respuesta, documento):
        return re.search(r'<tr[^>]+id="entrega-' + str(documento.pk) + r'".*?</tr>',
                         respuesta.content.decode(), re.S)[0]

    def test_orden_sigue_el_flujo_y_el_preparado_no_se_confunde_con_enviado(self):
        d, url = self.archivado(self.laboratorio)
        fila = self.fila(self.client.get(url, dict(anio=ANIO, corte=d.corte)), d)
        self.assertEqual(re.findall(r'data-columna="([^"]+)"', fila), [
            'Estado', 'Avance', 'Fechas', 'Observaciones', 'Acciones'])
        self.assertIn('Sin envío', fila)
        self.assertIn(reverse('recurso_unidad', args=[d.recurso_id]), fila)
        self.assertIn('>Ver</a>', fila)

    def test_modal_de_carga_no_repite_edicion_pdf_ni_historial(self):
        d, url = self.archivado(self.laboratorio)
        respuesta = self.client.get(url, dict(anio=ANIO, corte=d.corte, gestionar=d.pk, fragment='1'))
        self.assertContains(respuesta, 'Cargar y enviar a Dirección')
        self.assertContains(respuesta, 'name="enviar" value="1"')
        self.assertNotContains(respuesta, 'data-entrega-editor')
        self.assertNotContains(respuesta, 'data-ver-pdf')
        self.assertNotContains(respuesta, 'vista=versiones')

    def test_enviado_se_ve_directo_y_calificacion_incluye_cero_y_fecha(self):
        d, url = self.enviado(self.laboratorio)
        recibir_documento_revisado(d, self.direccion)
        evaluar_documento_revisado(d, self.direccion, 0, 'No cumple.', recomendaciones='Completar la evidencia.')
        fila = self.fila(self.client.get(url, dict(anio=ANIO, corte=d.corte)), d)
        self.assertIn(reverse('recurso_unidad', args=[d.recurso_id]), fila)
        self.assertIn('>Ver</a>', fila)
        self.assertNotIn('>Cargar</a>', fila)
        self.assertIn('Resultado: 0 %', fila)
        self.assertIn('data-estado-aprobacion="aprobado"', fila)
        self.assertIn('Enviado:', fila)


class CargarYEnviarTests(BaseDelExpediente):
    def cargar_y_enviar(self, documento, contenido=PDF_FIRMADO):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        return self.client.post(url, dict(anio=ANIO, corte=self.corte, documento=documento.pk,
                                         accion='cargar', enviar='1',
                                         **datos_correspondencia_revisada(documento),
                                         archivo=SimpleUploadedFile('documento.pdf', contenido)), follow=True)

    def test_carga_y_envio_confirman_archivo_estado_y_fecha_juntos(self):
        d = self.documento(self.laboratorio, 'RESOLUCION-CREACION', corte='')
        self.abrir_plazo(d)
        respuesta = self.cargar_y_enviar(d)
        self.assertContains(respuesta, 'cargado y enviado a la Dirección.')
        d.refresh_from_db()
        self.assertEqual(d.estado, 'validado')
        self.assertIsNotNone(d.recurso_id)
        self.assertIsNotNone(d.validado_en)
        self.assertEqual(d.validado_por, self.coordinador)
        self.assertIsNone(d.recibido_en)
        self.assertIsNone(d.evaluacion)

    def test_falta_de_anexos_revierte_la_carga_y_los_archivos_nuevos(self):
        d = self.documento(self.laboratorio, 'PLANIFICACION')
        self.abrir_plazo(d)
        recursos = Recurso.objects.count()
        archivos = {p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
        respuesta = self.cargar_y_enviar(d)
        self.assertContains(respuesta, 'Faltan por revisar y validar')
        d.refresh_from_db()
        self.assertIsNone(d.recurso_id)
        self.assertIsNone(d.validado_en)
        self.assertEqual(d.version, 0)
        self.assertEqual(Recurso.objects.count(), recursos)
        self.assertEqual({p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}, archivos)

    def test_rechaza_sin_firma_y_no_reemplaza_un_enviado(self):
        d = self.documento(self.laboratorio, 'PROTOCOLO-BIOSEGURIDAD', corte='')
        self.abrir_plazo(d)
        self.cargar_y_enviar(d, b'%PDF-1.4 sin firma')
        d.refresh_from_db()
        self.assertIsNone(d.recurso_id)
        self.assertIsNone(d.validado_en)
        enviado, _ = self.enviado(self.laboratorio)
        anterior = (enviado.recurso_id, enviado.version, enviado.validado_en)
        respuesta = self.cargar_y_enviar(enviado)
        self.assertContains(respuesta, 'La entrega ya fue enviada')
        enviado.refresh_from_db()
        self.assertEqual((enviado.recurso_id, enviado.version, enviado.validado_en), anterior)


class MetasYDocumentosUnificadosTests(BaseDelExpediente):
    def test_unidad_ve_una_tabla_con_todas_las_metas_y_anexos(self):
        d, url = self.archivado(self.laboratorio)
        from apps.documentos.presentation.expediente_redaccion import obtener_redaccion
        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        plan.marco_periodo, plan.tramo_inicio, plan.tramo_fin = d.marco_periodo, d.tramo_inicio, d.tramo_fin
        plan.save(update_fields=['marco_periodo', 'tramo_inicio', 'tramo_fin'])
        obtener_redaccion(plan).save()
        r = self.client.get(url, dict(anio=ANIO, corte=d.corte))
        html = r.content.decode()
        self.assertEqual(html.count('data-cierre-evidencias'), 1)
        self.assertNotContains(r, 'cierre-indicadores__metas')
        self.assertContains(r, 'Sin anexo específico')
        entrega = next(e for p in r.context['periodos'] for e in p['entregas'] if e['documento'].pk == d.pk)
        esperados = {f['codigo'] for f in entrega['cierre']['filas']}
        esperados.update(f['codigo'] for a in entrega['anexos'] for f in a.indicadores_cierre)
        codigos = re.findall(r'data-indicador-anexo="([^"]+)"', html)
        self.assertCountEqual(codigos, esperados)
        self.assertIn('MANTENIMIENTO', codigos)
        for anexo in entrega['anexos']:
            self.assertIn(f'&amp;anexo={anexo.pk}&amp;borrador=1', html)

    def test_director_ve_una_tabla_con_evidencia_congelada_y_sin_cambiarla(self):
        d, _ = self.enviado(self.laboratorio)
        anterior = cierre_archivado(d)
        self.client.force_login(self.direccion)
        r = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                            dict(anio=ANIO, corte=d.corte, revisar=d.pk))
        self.assertContains(r, 'data-cierre-evidencias', count=1)
        self.assertNotContains(r, 'cierre-indicadores__metas')
        for anexo in anterior['anexos']:
            if anexo['recurso']:
                self.assertContains(r, reverse('recurso_unidad', args=[anexo['recurso']]))
        self.assertEqual(cierre_archivado(d), anterior)
