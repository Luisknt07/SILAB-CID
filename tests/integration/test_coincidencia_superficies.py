"""Las cuatro superficies de una reserva deben decir lo mismo.

Asistente y comprobante, Mis reservas, Gestionar laboratorio y el
administrador operan sobre el mismo expediente. Estas pruebas fijan que ninguna
se salte las reglas de las otras ni deje informacion contradictoria.
"""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.reservas.presentation.notificaciones import _url_reserva
from apps.reservas.models.reservas import CatalogoActividadReserva, NotificacionReserva, Reserva, SolicitudCambioReserva
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


def _unidad(slug, administrador):
    return Unidad.objects.create(
        nombre=f'Laboratorio {slug}',
        slug=slug,
        dependencia='laboratorios',
        descripcion='Unidad para validar coincidencia entre superficies.',
        fecha_inicio=date(2026, 1, 1),
        administrador=administrador,
    )


def _reserva(unidad, usuario, **extra):
    datos = {
        'laboratorio': unidad,
        'usuario': usuario,
        'fecha': date(2026, 11, 10),
        'hora_inicio': time(9),
        'hora_fin': time(11),
        'equipo_codigo': 'EQ-COIN',
        'equipo_nombre': 'Equipo de coincidencia',
        'estado': 'pendiente',
    }
    datos.update(extra)
    return Reserva.objects.create(**datos)


class MensajesVisiblesTests(TestCase):
    """Los errores tras un POST-redirect se muestran en el portal."""

    def test_el_rechazo_del_comprobante_de_pago_se_ve_en_pantalla(self):
        staff = get_user_model().objects.create_superuser(
            'staff-mensajes', 'mensajes@upec.edu.ec', 'clave-segura'
        )
        unidad = _unidad('laboratorio-mensajes', staff)
        reserva = _reserva(unidad, staff, tipo_solicitud='servicio')
        SolicitudFabricacion.objects.create(
            unidad=unidad, reserva=reserva, solicitante=staff,
            nombre_proyecto='Servicio con pago', estado='en_revision',
        )
        self.client.force_login(staff)

        respuesta = self.client.post(
            reverse('subir_comprobante_pago', args=[reserva.pk]),
            {'comprobante_pago': SimpleUploadedFile(
                'pago.exe', b'binario', content_type='application/octet-stream'
            )},
            follow=True,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'portal-messages__item is-error')
        self.assertContains(respuesta, 'El comprobante debe ser PDF o imagen')


class EnlacesDeSeguimientoTests(TestCase):
    """Los avisos llevan a Mis reservas con la reserva ya seleccionada."""

    def test_los_avisos_y_el_comprobante_identifican_la_reserva(self):
        staff = get_user_model().objects.create_superuser(
            'staff-enlaces', 'enlaces@upec.edu.ec', 'clave-segura'
        )
        unidad = _unidad('laboratorio-enlaces', staff)
        reserva = _reserva(unidad, staff)

        self.assertEqual(
            _url_reserva(reserva),
            f"{reverse('laboratorio_detalle', args=[unidad.slug])}"
            f"?reserva={reserva.pk}#mis-reservas",
        )
        self.client.force_login(staff)
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertEqual(comprobante.status_code, 200)
        self.assertEqual(
            comprobante.context['volver_url'],
            f"{reverse('laboratorio_detalle', args=[unidad.slug])}"
            f"?reserva={reserva.pk}#mis-reservas",
        )


class CierreDesdeEjecucionTests(TestCase):
    """Validar el FT03 cierra la reserva por la misma maquina de estados del panel."""

    def setUp(self):
        User = get_user_model()
        self.operador = User.objects.create_superuser(
            'operador-ft03', 'ft03@upec.edu.ec', 'clave-segura'
        )
        self.unidad = _unidad('laboratorio-ft03', self.operador)
        self.actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Practica FT03',
            unidad=self.unidad,
            creado_por=self.operador,
        )
        self.client.force_login(self.operador)

    def _plan_con_ejecucion(self, reserva):
        plan = PlanificacionPractica.objects.create(
            actividad=self.actividad,
            unidad=self.unidad,
            reserva=reserva,
            fecha=reserva.fecha,
            hora_inicio=reserva.hora_inicio,
            hora_fin=reserva.hora_fin,
            carrera='Computacion',
            semestre='Quinto',
            asignatura='Fabricacion digital',
            docente_tutor='Docente FT03',
            tema='Impresion de una pieza',
            resultado_aprendizaje='Imprime una pieza funcional.',
            estudiantes_planificados=8,
            requiere_guia=False,
            estado='aprobada',
            creado_por=self.operador,
        )
        EjecucionPractica.objects.create(
            planificacion=plan,
            fecha_ejecucion=reserva.fecha,
            hora_inicio_real=time(9, 5),
            hora_fin_real=time(10, 50),
            resultado='ejecutada',
            estudiantes_asistentes=7,
            recursos_utilizados='Impresora FDM',
            observaciones_docente='Se imprimio la pieza sin novedades.',
            cumplimiento_resultado='si',
            estado='registrada',
            creado_por=self.operador,
        )
        return plan

    def test_una_reserva_confirmada_se_completa_con_bitacora_y_aviso(self):
        reserva = _reserva(
            self.unidad, self.operador, estado='confirmada',
            vinculacion_actividad='independiente',
        )
        plan = self._plan_con_ejecucion(reserva)

        respuesta = self.client.post(
            reverse('accion_ejecucion_practica', args=[self.unidad.slug, plan.pk]),
            {'accion': 'validar'},
            follow=True,
        )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'completada', respuesta.content[:1500])
        self.assertEqual(reserva.resultado_cierre, 'atendida')
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                entidad=Reserva._meta.label, objeto_id=str(reserva.pk), accion='completar'
            ).exists()
        )
        self.assertTrue(NotificacionReserva.objects.filter(reserva=reserva).exists())

    def test_una_reserva_pendiente_no_se_cierra_a_la_fuerza(self):
        reserva = _reserva(
            self.unidad, self.operador, estado='pendiente',
            vinculacion_actividad='independiente',
        )
        plan = self._plan_con_ejecucion(reserva)

        respuesta = self.client.post(
            reverse('accion_ejecucion_practica', args=[self.unidad.slug, plan.pk]),
            {'accion': 'validar'},
            follow=True,
        )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pendiente')
        self.assertContains(respuesta, 'no admite esa transición')
        self.assertEqual(
            EjecucionPractica.objects.get(planificacion=plan).estado, 'registrada'
        )


class SolicitudDeCambioCoherenteTests(TestCase):
    """Una reserva que ya no admite cambios no conserva solicitudes activas."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            'admin-cambios', 'cambios@upec.edu.ec', 'clave-segura'
        )
        self.titular = User.objects.create_user('titular-cambios', password='clave-segura')
        identificar(self.titular)
        self.unidad = _unidad('laboratorio-cambios', self.admin)

    def _solicitud(self, reserva):
        self.client.force_login(self.titular)
        respuesta = self.client.post(
            reverse('solicitar_cambio_reserva', args=[reserva.pk]),
            {'motivo': 'Necesito cambiar la fecha.'},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return SolicitudCambioReserva.objects.get(reserva=reserva)

    def test_cancelar_desde_mis_reservas_cierra_la_solicitud_activa(self):
        reserva = _reserva(self.unidad, self.titular, estado='pendiente')
        solicitud = self._solicitud(reserva)
        self.assertIn(solicitud.estado, SolicitudCambioReserva.ESTADOS_ACTIVOS)

        self.client.post(reverse('cancelar_reserva_usuario', args=[reserva.pk]))

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'cancelada')

    def test_cerrar_desde_el_panel_cierra_la_solicitud_activa(self):
        reserva = _reserva(self.unidad, self.titular, estado='confirmada')
        solicitud = self._solicitud(reserva)

        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {'accion': 'cancelar', 'observacion': 'La unidad cierra por mantenimiento.'},
        )

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'cancelada')
        self.assertIn('ya no aplica', solicitud.observacion_revision)


class ContadoresYEstadisticasTests(TestCase):
    """Los conteos del panel y del administrador usan la misma definicion."""

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            'admin-conteos', 'conteos@upec.edu.ec', 'clave-segura'
        )
        self.unidad = _unidad('laboratorio-conteos', self.admin)
        self.client.force_login(self.admin)

    def test_el_panel_cuenta_todas_las_planificaciones_en_revision(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Practica contada',
            unidad=self.unidad,
            creado_por=self.admin,
        )
        for dia in (3, 4):
            PlanificacionPractica.objects.create(
                actividad=actividad, unidad=self.unidad,
                fecha=date(2026, 11, dia), hora_inicio=time(8), hora_fin=time(10),
                carrera='Computacion', semestre='Quinto', asignatura='Asignatura',
                docente_tutor='Docente', tema='Tema',
                resultado_aprendizaje='Resultado', estudiantes_planificados=5,
                estado='revision', creado_por=self.admin,
            )

        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'practicas'})

        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context['planificaciones_revision_total'], 2)

    def test_las_estadisticas_del_admin_cuentan_en_proceso_como_aprobada(self):
        _reserva(self.unidad, self.admin, estado='en_proceso')
        _reserva(self.unidad, self.admin, estado='pendiente', hora_inicio=time(12), hora_fin=time(13))

        respuesta = self.client.get(
            reverse('admin:reservas-estadisticas'), {'por_laboratorio': '1'}
        )

        self.assertEqual(respuesta.status_code, 200)
        fila = next(f for f in respuesta.context['filas'] if f[0].startswith('Laboratorio labora'))
        nombre, aprobadas, no_aprobadas, _porcentaje = fila
        self.assertEqual((aprobadas, no_aprobadas), (1, 1))
