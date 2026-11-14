"""Suspensión integral y recuperable de la operación de reservas."""

from datetime import time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.configuracion_institucional.capacidades.services import cambiar_habilitacion
from config.capacidades import controles_de_despliegue
from apps.reservas.presentation.capacidad import CAPACIDAD_RESERVAS, MODULO_RESERVAS, CapacidadReservasSuspendida, operacion_reservas
from apps.reservas.presentation.creacion_transaccion import crear_expediente_reserva
from apps.reservas.presentation.notificaciones import procesar_recordatorios_reservas
from apps.reservas.presentation.solicitudes_propias import cancelar_reserva_propia
from apps.reservas.presentation import visitas
from apps.reservas.presentation import administracion, aprobacion, cambios, correccion, cronograma, decisiones_cambio, decisiones_reserva, ejecucion, finalizacion, mantenimiento, solicitudes_propias, transiciones_operativas
from apps.reservas.manifiesto import MANIFIESTO
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class CapacidadReservasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.gestor = usuarios.create_superuser('capacidad-reservas-gestor')
        cls.titular = usuarios.create_user(
            'capacidad-reservas-titular',
            email='capacidad.reservas@upec.edu.ec',
            password='clave-segura',
        )
        identificar(cls.titular)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio capacidad reservas',
            slug='laboratorio-capacidad-reservas',
            fecha_inicio=timezone.localdate(),
            dependencia='laboratorios',
        )

    def crear_reserva(self, *, fecha=None):
        return Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.titular,
            fecha=fecha or timezone.localdate() + timedelta(days=1),
            hora_inicio=time(8),
            hora_fin=time(9),
            estado='pendiente',
            tipo_solicitud='recursos',
            titulo_solicitud='Reserva bajo control institucional',
        )

    def cambiar(self, habilitada, version):
        return cambiar_habilitacion(
            MODULO_RESERVAS,
            CAPACIDAD_RESERVAS,
            habilitada,
            self.gestor,
            version_esperada=version,
            motivo='Control operativo de reservas en prueba',
        )

    def test_manifiesto_y_politica_declaran_la_misma_capacidad(self):
        self.assertIn(CAPACIDAD_RESERVAS, MANIFIESTO.capacidades)
        controles = controles_de_despliegue({})
        self.assertIn(f'{MODULO_RESERVAS}.{CAPACIDAD_RESERVAS}', controles)

    def test_suspension_impide_crear_y_cancelar_sin_tocar_el_expediente(self):
        reserva = self.crear_reserva()
        self.cambiar(False, 0)

        with self.assertRaises(CapacidadReservasSuspendida):
            crear_expediente_reserva(None, completar_guia=None, auditar=None)
        with self.assertRaises(CapacidadReservasSuspendida):
            cancelar_reserva_propia(
                reserva,
                actor=self.titular,
                unidad_esperada=self.unidad.pk,
            )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pendiente')
        self.assertEqual(Reserva.objects.count(), 1)

    def test_todos_los_casos_de_uso_escritores_entran_por_la_misma_compuerta(self):
        escritores = (
            administracion.gestionar_reserva_administrativa,
            aprobacion.aprobar_reserva,
            cambios.enviar_propuesta_cambio,
            cambios.aplicar_solicitud_cambio,
            correccion.corregir_reserva,
            cronograma.completar_sesion,
            decisiones_cambio.autorizar_solicitud_cambio,
            decisiones_cambio.rechazar_solicitud_cambio,
            decisiones_cambio.retirar_solicitud_cambio,
            decisiones_reserva.decidir_reserva,
            ejecucion.registrar_cierre_operativo,
            finalizacion.completar_reserva,
            mantenimiento.inicializar_revisiones_unidad,
            mantenimiento.sincronizar_planificaciones_unidad,
            solicitudes_propias.crear_solicitud_cambio,
            solicitudes_propias.cancelar_reserva_propia,
            transiciones_operativas.transicionar_reserva_operativa,
            visitas.crear_visita,
            visitas.registrar_asistencia,
        )
        self.cambiar(False, 0)

        for escritor in escritores:
            with self.subTest(escritor=escritor.__name__), self.assertRaises(
                CapacidadReservasSuspendida
            ):
                escritor()

    def test_compuerta_no_disfraza_una_denegacion_del_caso_de_uso(self):
        @operacion_reservas
        def operacion_denegada():
            raise PermissionDenied('Permiso propio del caso de uso')

        with self.assertRaisesMessage(PermissionDenied, 'Permiso propio del caso de uso'):
            operacion_denegada()

    def test_suspension_se_presenta_en_el_idioma_activo(self):
        reserva = self.crear_reserva()
        self.cambiar(False, 0)

        with override('en'), self.assertRaisesMessage(
            CapacidadReservasSuspendida,
            'Reservation operations have been temporarily suspended',
        ):
            cancelar_reserva_propia(
                reserva,
                actor=self.titular,
                unidad_esperada=self.unidad.pk,
            )

    def test_comando_de_mantenimiento_respeta_la_suspension(self):
        self.crear_reserva()
        self.cambiar(False, 0)

        with self.assertRaisesMessage(CommandError, 'suspendida temporalmente'):
            call_command(
                'inicializar_revisiones_reservas',
                unidad=self.unidad.slug,
                stdout=StringIO(),
            )

    def test_tarea_suspendida_no_pierde_trabajo_y_reanuda_al_habilitar(self):
        reserva = self.crear_reserva(fecha=timezone.localdate() - timedelta(days=1))
        self.cambiar(False, 0)

        resultado_suspendido = procesar_recordatorios_reservas(enviar_email=False)
        reserva.refresh_from_db()
        self.assertEqual(resultado_suspendido['vencidas'], 0)
        self.assertEqual(reserva.estado, 'pendiente')

        self.cambiar(True, 1)
        resultado_reanudado = procesar_recordatorios_reservas(enviar_email=False)
        reserva.refresh_from_db()
        self.assertEqual(resultado_reanudado['vencidas'], 1)
        self.assertEqual(reserva.estado, 'vencida')

    def test_diagnostico_y_pdf_siguen_disponibles_pero_reparacion_se_bloquea(self):
        reserva = self.crear_reserva()
        Reserva.objects.filter(pk=reserva.pk).update(codigo_reserva=None)
        self.cambiar(False, 0)

        salida = StringIO()
        call_command('recuperar_codigos_reservas', stdout=salida)
        self.assertIn('"modo": "auditoria"', salida.getvalue())
        with self.assertRaisesMessage(CommandError, 'suspendida temporalmente'):
            call_command(
                'recuperar_codigos_reservas',
                aplicar=True,
                unidad=self.unidad.pk,
                stdout=StringIO(),
            )

        self.client.force_login(self.titular)
        respuesta = self.client.get(
            reverse('comprobante_reserva_pdf', args=[reserva.pk]),
            {'inline': '1'},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
