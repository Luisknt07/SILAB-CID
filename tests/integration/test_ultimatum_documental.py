from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.avisos_documentales import AvisoDocumental, UltimatumDocumental
from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.avisos_documentales import enviar_pendientes
from apps.documentos.presentation.expediente import solicitar_entrega_tardia, habilitar_entrega_tardia
from apps.documentos.presentation.incumplimiento_documental import establecer_ultimatum, evaluar_vencimientos
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


class UltimatumDocumentalTests(BaseDelExpediente):
    def vencido(self):
        doc = self.documento(self.laboratorio, 'PLANIFICACION')
        doc.exigido.fecha_limite = timezone.localdate() - timedelta(days=2)
        doc.exigido.save()
        doc.vence_el = doc.exigido.fecha_limite
        doc.save()
        return doc

    def test_admin_permite_aplicar_desde_la_fila_sin_solicitud(self):
        doc = self.vencido()
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        respuesta = self.client.post(url, {'accion': 'ultimatum', 'documento': doc.pk,
                                          'hasta': (timezone.now() + timedelta(days=3)).isoformat(),
                                          'motivo': 'Completar la documentación',
                                          'query': f'anio={doc.anio}&corte={doc.corte}'})
        self.assertEqual(respuesta.status_code, 302)
        doc.refresh_from_db()
        self.assertIsNotNone(doc.ultimatum_hasta)
        respuesta = self.client.get(url, dict(anio=doc.anio, corte=doc.corte, plazos=doc.pk))
        self.assertContains(respuesta, 'Ultimátum de Dirección')

    def test_colectivo_materializa_unidades_y_no_puede_repetirse(self):
        doc = self.vencido()
        cierre = timezone.now() + timedelta(days=3)
        with self.assertRaises(ValidationError):
            establecer_ultimatum(doc, self.coordinador, cierre.isoformat(), 'Última entrega')
        cantidad = establecer_ultimatum(doc, self.direccion, cierre.isoformat(), 'Completar documentos pendientes')
        self.assertGreaterEqual(cantidad, 2)
        otro = DocumentoExpediente.objects.get(unidad=self.suelto, exigido=doc.exigido, anio=doc.anio, corte=doc.corte)
        self.assertEqual(otro.ultimatum_hasta, cierre)
        self.assertTrue(otro.entrega_abierta)
        self.assertTrue(otro.vencido)
        self.assertEqual(UltimatumDocumental.objects.count(), 1)
        self.assertTrue(AvisoDocumental.objects.filter(documento=otro, tipo='ultimatum').exists())
        with self.assertRaises(ValidationError):
            establecer_ultimatum(doc, self.direccion, (cierre + timedelta(days=1)).isoformat(), 'Otra oportunidad')

    def test_solicitud_solo_despues_del_ultimatum(self):
        doc = self.vencido()
        with self.assertRaises(ValidationError):
            solicitar_entrega_tardia(doc, self.coordinador, 'Faltó la firma')
        cierre = timezone.now() + timedelta(days=2)
        establecer_ultimatum(doc, self.direccion, cierre.isoformat(), 'Última entrega')
        doc.refresh_from_db()
        with self.assertRaises(ValidationError):
            solicitar_entrega_tardia(doc, self.coordinador, 'Faltó la firma')
        with patch('django.utils.timezone.now', return_value=cierre + timedelta(seconds=1)):
            solicitar_entrega_tardia(doc, self.coordinador, 'Faltó la firma')
            habilitar_entrega_tardia(doc, self.direccion, cierre + timedelta(days=2))
            self.assertTrue(doc.entrega_abierta)

    def test_no_modifica_entregados_ni_sin_plazo_y_evaluacion_idempotente(self):
        doc = self.vencido()
        enviado = self.documento(self.suelto, 'PLANIFICACION')
        enviado.estado = 'validado'
        enviado.save()
        evaluar_vencimientos()
        doc.refresh_from_db()
        # La planificación es de cumplimiento obligatorio: la no entrega es incumplimiento, sin porcentaje.
        self.assertIsNone(doc.nota)
        self.assertIs(doc.cumple, False)
        self.assertIsNone(doc.evaluado_por)
        self.assertIn('Incumplimiento por no entrega', doc.evaluacion_observacion)
        self.assertIn('completar', doc.evaluacion_recomendaciones)
        aviso = AvisoDocumental.objects.get(documento=doc, tipo='evaluacion')
        self.assertIn('mejora continua', aviso.mensaje)
        evaluar_vencimientos()
        self.assertEqual(AvisoDocumental.objects.filter(documento=doc, tipo='evaluacion').count(), 1)
        enviado.refresh_from_db()
        self.assertIsNone(enviado.evaluacion)

    def test_ultimatum_difiere_evaluacion_hasta_su_vencimiento(self):
        doc = self.vencido()
        cierre = timezone.now() + timedelta(days=2)
        establecer_ultimatum(doc, self.direccion, cierre.isoformat(), 'Última entrega')
        evaluar_vencimientos()
        doc.refresh_from_db()
        self.assertIsNone(doc.evaluacion)
        evaluar_vencimientos(cierre + timedelta(seconds=1))
        doc.refresh_from_db()
        self.assertIs(doc.cumple, False)
        self.assertIn('ultimátum', doc.evaluacion_observacion)

    def test_respeta_evaluacion_manual(self):
        doc = self.vencido()
        doc.evaluacion = 0
        doc.evaluacion_version = doc.version
        doc.evaluado_por = self.direccion
        doc.evaluacion_observacion = 'Decisión manual'
        doc.save()
        evaluar_vencimientos()
        doc.refresh_from_db()
        self.assertEqual(doc.evaluacion_observacion, 'Decisión manual')
        self.assertFalse(AvisoDocumental.objects.filter(documento=doc, tipo='evaluacion').exists())

    def test_no_califica_sin_fecha_ni_antes_del_cierre(self):
        doc = self.vencido()
        doc.vence_el = None
        doc.save()
        evaluar_vencimientos()
        doc.refresh_from_db()
        self.assertIsNone(doc.evaluacion)
        doc.vence_el = timezone.localdate() + timedelta(days=3)
        doc.save()
        evaluar_vencimientos(doc.plazo_original)
        doc.refresh_from_db()
        self.assertIsNone(doc.evaluacion)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DOCUMENT_SMS_BACKEND='')
    def test_aviso_de_evaluacion_se_envia_aunque_el_plazo_ya_vencio(self):
        doc = self.vencido()
        self.coordinador.email = 'responsable@example.test'
        self.coordinador.save()
        evaluar_vencimientos()
        with patch('apps.documentos.presentation.avisos_documentales.send_mail', return_value=1) as correo:
            enviar_pendientes()
            llamadas = correo.call_count
            self.assertGreater(llamadas, 0)
            enviar_pendientes(timezone.now() + timedelta(minutes=20))
            self.assertEqual(correo.call_count, llamadas)
        aviso = AvisoDocumental.objects.get(documento=doc, tipo='evaluacion')
        self.assertTrue(aviso.email_enviado)
        self.assertFalse(aviso.sms_enviado)
