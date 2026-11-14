from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
from apps.reservas.models.reservas import Reserva, ReservaConsumible, RevisionReserva, SolicitudCambioReserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class CambiosReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            'admin-cambios', password='clave', email='admin@upec.edu.ec'
        )
        cls.titular = User.objects.create_user(
            'titular-cambios', password='clave', email='titular@upec.edu.ec'
        )
        cls.ajeno = User.objects.create_user('ajeno-cambios', password='clave')
        for persona in (cls.admin, cls.titular, cls.ajeno):
            identificar(persona)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de cambios controlados',
            descripcion='Unidad para probar revisiones.',
            fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-cambios-controlados',
            dependencia='laboratorios',
            administrador=cls.admin,
        )
        cls.fecha_original = timezone.localdate() + timedelta(days=4)
        cls.fecha_nueva = cls.fecha_original + timedelta(days=1)
        for fecha in {cls.fecha_original, cls.fecha_nueva}:
            HorarioOperacionUnidad.objects.create(
                unidad=cls.unidad,
                dia_semana=fecha.weekday(),
                hora_inicio=time(7),
                hora_fin=time(18),
            )

    def setUp(self):
        self.reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.titular,
            fecha=self.fecha_original,
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='EQ-CAMBIO',
            equipo_nombre='Equipo original',
            titulo_solicitud='Actividad original',
            motivo='Necesidad original',
            descripcion_proyecto='Descripción original',
            proposito_codigo='docencia_practica',
            estado='confirmada',
        )

    def solicitar(self):
        self.client.force_login(self.titular)
        return self.client.post(
            reverse('solicitar_cambio_reserva', args=[self.reserva.pk]),
            {'motivo': 'El grupo necesita cambiar la fecha y el horario.'},
        )

    def autorizar(self, solicitud):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse(
                'gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, solicitud.pk],
            ),
            {'accion': 'autorizar', 'campos': ['fecha_horario', 'actividad']},
        )

    def enviar_propuesta(self, solicitud):
        self.client.force_login(self.titular)
        return self.client.post(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk]),
            {
                'fecha': self.fecha_nueva.isoformat(),
                'hora_inicio': '12:00',
                'hora_fin': '14:00',
                'titulo_solicitud': 'Actividad reprogramada por el titular',
                'motivo': 'Cambio de disponibilidad del grupo.',
                'descripcion_proyecto': 'Mismo alcance en una nueva jornada.',
                'requisitos_especiales': 'Preparar el equipo antes de las 12:00.',
            },
        )

    def test_circuito_completo_no_sobrescribe_hasta_aprobar(self):
        response = self.solicitar()
        self.assertEqual(response.status_code, 201)
        solicitud = SolicitudCambioReserva.objects.get(reserva=self.reserva)
        self.assertEqual(solicitud.estado, 'solicitada')
        self.assertEqual(self.reserva.revisiones.count(), 1)

        response = self.autorizar(solicitud)
        self.assertEqual(response.status_code, 200)
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.puede_editar)

        response = self.enviar_propuesta(solicitud)
        self.assertEqual(response.status_code, 302)
        solicitud.refresh_from_db()
        self.reserva.refresh_from_db()
        self.assertEqual(solicitud.estado, 'enviada')
        self.assertEqual(self.reserva.fecha, self.fecha_original)
        self.assertEqual(self.reserva.titulo_solicitud, 'Actividad original')

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                'gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, solicitud.pk],
            ),
            {'accion': 'aprobar', 'observacion': 'Disponibilidad verificada.'},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.reserva.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertEqual(self.reserva.fecha, self.fecha_nueva)
        self.assertEqual(self.reserva.hora_inicio, time(12))
        self.assertEqual(
            self.reserva.titulo_solicitud,
            'Actividad reprogramada por el titular',
        )
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertEqual(self.reserva.revisiones.count(), 2)
        self.assertEqual(solicitud.revision_aplicada.numero, 2)

    def test_editor_autorizado_se_visualiza(self):
        self.solicitar()
        solicitud = SolicitudCambioReserva.objects.get(reserva=self.reserva)
        self.autorizar(solicitud)
        self.client.force_login(self.titular)

        response = self.client.get(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preparar propuesta de cambio')

    def test_cambio_de_fecha_no_altera_aprobacion_de_insumos(self):
        insumo = Consumible.objects.create(
            unidad=self.unidad,
            codigo='INS-CAMBIO-FECHA',
            nombre='Filamento reservado',
            unidad_medida='g',
            stock_total=Decimal('1000'),
        )
        detalle = ReservaConsumible.objects.create(
            reserva=self.reserva,
            consumible=insumo,
            cantidad_solicitada=Decimal('150'),
            cantidad_aprobada=Decimal('125'),
        )
        self.solicitar()
        solicitud = SolicitudCambioReserva.objects.get(reserva=self.reserva)
        self.autorizar(solicitud)
        self.enviar_propuesta(solicitud)
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                'gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, solicitud.pk],
            ),
            {'accion': 'aprobar'},
        )

        self.assertEqual(response.status_code, 200, response.content)
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_solicitada, Decimal('150'))
        self.assertEqual(detalle.cantidad_aprobada, Decimal('125'))

    def test_correccion_directa_del_administrador_genera_version(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                'gestion_reserva_accion',
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                'accion': 'actualizar',
                'fecha': self.fecha_nueva.isoformat(),
                'hora_inicio': '10:00',
                'hora_fin': '12:00',
                'titulo_solicitud': 'Corrección administrativa trazable',
                'numero_participantes': '1',
                'descripcion_proyecto': 'Alcance corregido por el laboratorio.',
                'motivo': 'Reprogramación operativa.',
                'justificacion_cambio': 'Disponibilidad real del laboratorio.',
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        revisiones = list(self.reserva.revisiones.order_by('numero'))
        self.assertEqual([item.numero for item in revisiones], [1, 2])
        self.assertEqual(revisiones[1].tipo, 'correccion_admin')
        self.assertEqual(
            revisiones[1].datos['titulo_solicitud'],
            'Corrección administrativa trazable',
        )

    def test_usuario_ajeno_no_puede_editar_la_propuesta(self):
        self.solicitar()
        solicitud = SolicitudCambioReserva.objects.get(reserva=self.reserva)
        self.autorizar(solicitud)
        self.client.force_login(self.ajeno)

        response = self.client.get(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_no_admite_dos_solicitudes_activas(self):
        self.solicitar()
        response = self.solicitar()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            SolicitudCambioReserva.objects.filter(reserva=self.reserva).count(),
            1,
        )

    def test_detecta_cambio_concurrente_antes_de_aplicar(self):
        self.solicitar()
        solicitud = SolicitudCambioReserva.objects.get(reserva=self.reserva)
        self.autorizar(solicitud)
        self.enviar_propuesta(solicitud)
        self.reserva.titulo_solicitud = 'Corrección administrativa concurrente'
        self.reserva.save()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                'gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, solicitud.pk],
            ),
            {'accion': 'aprobar'},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('cambió mientras', response.json()['error'])
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'enviada')

    def test_revision_es_inmutable(self):
        self.solicitar()
        revision = RevisionReserva.objects.get(reserva=self.reserva, numero=1)
        revision.motivo = 'Intento de sobrescritura'

        with self.assertRaises(ValidationError):
            revision.save()
