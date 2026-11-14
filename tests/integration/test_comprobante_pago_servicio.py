"""Comprobante de pago de la orden de servicio, dentro del comprobante unificado.

Esta capacidad vivia en el formulario publico ``/fabricacion/``, que permitia
crear solicitudes sin reserva, sin agenda, sin cotizacion y sin compuerta
documental. Al retirar esa entrada paralela, la subida del respaldo se conservo
aqui, ligada a la orden de servicio que ya genera el asistente unificado.
"""

import tempfile
from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.reservas.models.reservas import Reserva
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


def _pdf(nombre='pago.pdf'):
    return SimpleUploadedFile(nombre, b'%PDF-1.4 comprobante', content_type='application/pdf')


class ComprobantePagoServicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.titular = User.objects.create_user('titular-pago', password='clave-segura')
        cls.ajeno = User.objects.create_user('ajeno-pago', password='clave-segura')
        for persona in (cls.titular, cls.ajeno):
            identificar(persona)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de servicios',
            slug='laboratorio-servicios-pago',
            dependencia='laboratorios',
            descripcion='Unidad para validar el respaldo de pago.',
            fecha_inicio=date(2026, 1, 1),
        )
        cls.reserva = Reserva.objects.create(
            laboratorio=cls.unidad,
            usuario=cls.titular,
            fecha=date(2026, 10, 5),
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='SERVICIO',
            equipo_nombre='Servicio tecnico',
            tipo_solicitud='servicio',
            metodo_pago='transferencia',
        )
        cls.orden = SolicitudFabricacion.objects.create(
            unidad=cls.unidad,
            reserva=cls.reserva,
            solicitante=cls.titular,
            nombre_proyecto='Servicio con pago',
            estado='en_revision',
        )

    def _url(self):
        return reverse('subir_comprobante_pago', args=[self.reserva.pk])

    def test_el_titular_adjunta_su_respaldo_de_pago(self):
        self.client.force_login(self.titular)

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            respuesta = self.client.post(self._url(), {'comprobante_pago': _pdf()})
            self.orden.refresh_from_db()
            nombre = self.orden.comprobante_pago.name

        self.assertRedirects(
            respuesta, reverse('comprobante_reserva', args=[self.reserva.pk])
        )
        self.assertTrue(nombre.endswith('pago.pdf'))

    def test_otro_usuario_no_puede_adjuntar_sobre_una_reserva_ajena(self):
        self.client.force_login(self.ajeno)

        respuesta = self.client.post(self._url(), {'comprobante_pago': _pdf()})

        self.assertEqual(respuesta.status_code, 403)
        self.orden.refresh_from_db()
        self.assertFalse(self.orden.comprobante_pago)

    def test_rechaza_un_formato_no_permitido(self):
        self.client.force_login(self.titular)

        respuesta = self.client.post(
            self._url(),
            {'comprobante_pago': SimpleUploadedFile(
                'pago.exe', b'binario', content_type='application/octet-stream'
            )},
        )

        self.assertRedirects(
            respuesta, reverse('comprobante_reserva', args=[self.reserva.pk])
        )
        self.orden.refresh_from_db()
        self.assertFalse(self.orden.comprobante_pago)

    def test_el_comprobante_ofrece_la_subida_solo_al_titular(self):
        self.client.force_login(self.titular)
        propio = self.client.get(reverse('comprobante_reserva', args=[self.reserva.pk]))
        self.assertContains(propio, 'Comprobante de pago pendiente')

        self.client.force_login(self.ajeno)
        ajeno = self.client.get(reverse('comprobante_reserva', args=[self.reserva.pk]))
        self.assertEqual(ajeno.status_code, 403)
