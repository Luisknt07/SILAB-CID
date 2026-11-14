"""Lo que el titular puede hacer con su propia solicitud de cambio.

Tres huecos verificados a mano: no podia retirar una propuesta enviada, no veia
que habia propuesto y una cantidad de insumo vacia se aceptaba al enviar y
fallaba al aprobar con el error visible solo para el personal.
"""

from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
from apps.reservas.models.reservas import NotificacionReserva, Reserva, SolicitudCambioReserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class _CambiosTitularBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            'admin-titular', password='clave', email='admin-titular@upec.edu.ec'
        )
        cls.titular = User.objects.create_user(
            'titular-cambios-propios', password='clave', email='titular-propio@upec.edu.ec'
        )
        cls.ajeno = User.objects.create_user('ajeno-titular', password='clave')
        for persona in (cls.admin, cls.titular, cls.ajeno):
            identificar(persona)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de cambios del titular',
            descripcion='Unidad para probar el retiro y la propuesta visible.',
            fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-cambios-titular',
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
            equipo_codigo='EQ-TITULAR',
            equipo_nombre='Equipo original',
            titulo_solicitud='Actividad original',
            motivo='Necesidad original',
            descripcion_proyecto='Descripción original',
            proposito_codigo='docencia_practica',
            estado='confirmada',
        )

    def solicitar(self):
        self.client.force_login(self.titular)
        respuesta = self.client.post(
            reverse('solicitar_cambio_reserva', args=[self.reserva.pk]),
            {'motivo': 'El grupo necesita cambiar la fecha y el horario.'},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        # Tras un retiro puede existir una solicitud cancelada anterior.
        return (
            SolicitudCambioReserva.objects.filter(reserva=self.reserva)
            .order_by('-pk').first()
        )

    def autorizar(self, solicitud, campos):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse(
                'gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, solicitud.pk],
            ),
            {'accion': 'autorizar', 'campos': campos},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        solicitud.refresh_from_db()
        return solicitud

    def retirar(self, solicitud, **extra):
        return self.client.post(
            reverse('retirar_solicitud_cambio_reserva', args=[solicitud.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            **extra,
        )


class RetiroDeSolicitudTests(_CambiosTitularBase):
    def test_el_titular_retira_su_solicitud_y_puede_pedir_otra(self):
        solicitud = self.solicitar()

        respuesta = self.retirar(solicitud)

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        datos = respuesta.json()['solicitud_cambio']
        self.assertEqual(datos['estado'], 'cancelada')
        self.assertFalse(datos['puede_retirar'])
        solicitud.refresh_from_db()
        self.assertIn('Retirada por el titular', solicitud.observacion_revision)
        self.assertTrue(
            NotificacionReserva.objects.filter(
                reserva=self.reserva,
                usuario=self.admin,
                titulo='Solicitud de cambio retirada',
            ).exists()
        )
        # La reserva vuelve a admitir una solicitud nueva.
        self.assertEqual(self.solicitar().estado, 'solicitada')

    def test_solo_el_titular_y_solo_mientras_siga_activa(self):
        solicitud = self.solicitar()

        self.client.force_login(self.ajeno)
        self.assertEqual(self.retirar(solicitud).status_code, 404)

        SolicitudCambioReserva.objects.filter(pk=solicitud.pk).update(estado='aprobada')
        self.client.force_login(self.titular)
        self.assertEqual(self.retirar(solicitud).status_code, 409)

    def test_sin_ajax_vuelve_a_mis_reservas_con_el_aviso_visible(self):
        solicitud = self.solicitar()

        respuesta = self.client.post(
            reverse('retirar_solicitud_cambio_reserva', args=[solicitud.pk]),
            follow=True,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Tu solicitud de cambio fue retirada')


class PropuestaVisibleTests(_CambiosTitularBase):
    def test_el_titular_ve_lo_que_propuso_con_nombres_legibles(self):
        solicitud = self.autorizar(self.solicitar(), ['fecha_horario', 'actividad'])
        self.client.force_login(self.titular)
        envio = self.client.post(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk]),
            {
                'fecha': self.fecha_nueva.isoformat(),
                'hora_inicio': '12:00',
                'hora_fin': '14:00',
                'titulo_solicitud': 'Actividad reprogramada por el titular',
                'motivo': 'Cambio de disponibilidad del grupo.',
                'descripcion_proyecto': 'Mismo alcance en una nueva jornada.',
                'requisitos_especiales': '',
            },
        )
        self.assertEqual(envio.status_code, 302, envio.content)

        datos = self.client.get(reverse('obtener_reservas_usuario')).json()['reservas'][0]
        cambio = datos['solicitud_cambio']
        self.assertEqual(cambio['estado'], 'enviada')
        self.assertTrue(cambio['puede_retirar'])
        por_etiqueta = {item['etiqueta']: item for item in cambio['diferencias']}
        self.assertEqual(
            por_etiqueta['Fecha']['nuevo'], self.fecha_nueva.strftime('%d/%m/%Y')
        )
        self.assertEqual(
            por_etiqueta['Fecha']['anterior'], self.fecha_original.strftime('%d/%m/%Y')
        )
        self.assertEqual(
            por_etiqueta['Título']['nuevo'], 'Actividad reprogramada por el titular'
        )

        pagina = self.client.get(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk])
        )
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Lo que propusiste')
        self.assertContains(pagina, 'Actividad reprogramada por el titular')
        self.assertContains(pagina, 'Retirar solicitud')


class CantidadDeInsumoTests(_CambiosTitularBase):
    def test_una_cantidad_vacia_se_rechaza_al_enviar_y_no_al_aprobar(self):
        insumo = Consumible.objects.create(
            unidad=self.unidad,
            codigo='INS-CANTIDAD',
            nombre='Filamento PLA',
            unidad_medida='g',
            stock_total=Decimal('500'),
            visible_en_reservas=True,
        )
        solicitud = self.autorizar(self.solicitar(), ['insumos'])
        self.client.force_login(self.titular)
        url = reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk])

        sin_cantidad = self.client.post(url, {
            'consumibles_ids': [insumo.pk],
            f'consumible_{insumo.pk}_cantidad': '',
            f'consumible_{insumo.pk}_metodo': 'estimacion',
        })

        self.assertEqual(sin_cantidad.status_code, 200)
        self.assertContains(sin_cantidad, 'Indica la cantidad solicitada')
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'autorizada')

        # Pedir revision tecnica si admite dejar la cantidad abierta.
        con_revision = self.client.post(url, {
            'consumibles_ids': [insumo.pk],
            f'consumible_{insumo.pk}_cantidad': '',
            f'consumible_{insumo.pk}_metodo': 'revision',
        })

        self.assertEqual(con_revision.status_code, 302, con_revision.content)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'enviada')
        fila = solicitud.propuesta['consumibles'][0]
        self.assertIsNone(fila['cantidad_solicitada'])
        self.assertEqual(fila['metodo_estimacion'], 'revision')

    def test_una_cantidad_valida_se_normaliza_y_se_describe(self):
        insumo = Consumible.objects.create(
            unidad=self.unidad,
            codigo='INS-NORMAL',
            nombre='Resina',
            unidad_medida='ml',
            stock_total=Decimal('900'),
            visible_en_reservas=True,
        )
        solicitud = self.autorizar(self.solicitar(), ['insumos'])
        self.client.force_login(self.titular)

        respuesta = self.client.post(
            reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk]),
            {
                'consumibles_ids': [insumo.pk],
                f'consumible_{insumo.pk}_cantidad': '12,5',
                f'consumible_{insumo.pk}_metodo': 'estimacion',
            },
        )

        self.assertEqual(respuesta.status_code, 302, respuesta.content)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.propuesta['consumibles'][0]['cantidad_solicitada'], '12.5')
        cambio = self.client.get(reverse('obtener_reservas_usuario')).json()['reservas'][0]['solicitud_cambio']
        insumos = next(item for item in cambio['diferencias'] if item['etiqueta'] == 'Insumos y cantidades')
        self.assertIn('Resina: 12.5 ml', insumos['nuevo'])
