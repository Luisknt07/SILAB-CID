from datetime import timedelta, time
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone

from apps.documentos.models.avisos_documentales import AvisoDocumental
from apps.documentos.presentation.avisos_documentales import preparar_avisos, enviar_pendientes
from apps.documentos.presentation.expediente import habilitar_entrega_tardia, solicitar_entrega_tardia
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


class PlazosDocumentalesTests(BaseDelExpediente):
    def test_asignacion_inicial_comun_y_proteccion_de_plazo_existente(self):
        from apps.documentos.presentation.plazos_documentales import asignar_plazo_inicial
        documento = self.documento(self.laboratorio, 'PLANIFICACION')
        otro = self.documento(self.suelto, 'PLANIFICACION')
        documento.exigido.plazo_regla = 'ninguno'
        documento.exigido.fecha_limite = None
        documento.exigido.save()
        for doc in (documento, otro):
            doc.vence_el = None
            doc.save()
        cierre = timezone.now().replace(month=12, day=31, hour=20)
        with self.assertRaises(ValidationError):
            asignar_plazo_inicial(documento, self.coordinador, cierre.isoformat())
        with self.assertRaises(ValidationError):
            asignar_plazo_inicial(documento, self.direccion, 'incorrecta')
        asignar_plazo_inicial(documento, self.direccion, cierre.isoformat())
        otro.refresh_from_db()
        self.assertEqual(otro.vence_el, timezone.localtime(cierre).date())
        with self.assertRaises(ValidationError):
            asignar_plazo_inicial(documento, self.direccion, cierre.isoformat())

    def test_reapertura_caduca_y_exige_nueva_solicitud(self):
        documento = self.documento(self.laboratorio, 'PLANIFICACION')
        documento.ultimatum_hasta = timezone.now() - timedelta(hours=1)
        documento.vence_el = timezone.localdate() - timedelta(days=1)
        documento.save()
        solicitar_entrega_tardia(documento, self.coordinador, 'Faltó la firma.')
        with self.assertRaises(ValidationError):
            habilitar_entrega_tardia(documento, self.direccion)
        cierre = timezone.now() + timedelta(hours=2)
        habilitar_entrega_tardia(documento, self.direccion, cierre)
        self.assertTrue(documento.prorroga_activa)
        self.assertTrue(documento.vencido)
        with patch('apps.documentos.models.expediente.timezone.now', return_value=cierre + timedelta(seconds=1)):
            self.assertFalse(documento.entrega_abierta)
            with self.assertRaises(ValidationError):
                habilitar_entrega_tardia(documento, self.direccion, cierre + timedelta(days=1))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DOCUMENT_SMS_BACKEND='')
    def test_avisos_separados_por_plazo_y_umbral_sin_duplicar_correo(self):
        documento = self.documento(self.laboratorio, 'PLANIFICACION')
        ahora = timezone.now()
        documento.vence_el = timezone.localdate(ahora + timedelta(days=7))
        documento.exigido.hora_limite = time(12, 0)
        documento.exigido.save()
        documento.save()
        inicio = documento.plazo_original - timedelta(days=7)
        preparar_avisos(inicio)
        preparar_avisos(inicio)
        avisos = AvisoDocumental.objects.filter(documento=documento)
        self.assertEqual(avisos.count(), 1)
        aviso = avisos.get()
        self.assertEqual(aviso.horas, 168)
        with patch('apps.documentos.presentation.avisos_documentales.send_mail', return_value=1) as correo:
            enviar_pendientes(inicio)
            enviar_pendientes(inicio + timedelta(minutes=20))
            self.assertEqual(correo.call_count, 1)
        aviso.refresh_from_db()
        self.assertTrue(aviso.email_enviado)
        self.assertFalse(aviso.sms_enviado)
        self.assertTrue(aviso.error_sms)
        preparar_avisos(documento.plazo_original - timedelta(hours=24))
        self.assertEqual(avisos.count(), 2)
