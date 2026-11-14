"""Decisiones autonomas: autoridad vigente, rollback de avisos y bloqueo real."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.reservas.presentation.decisiones_cambio import autorizar_solicitud_cambio, rechazar_solicitud_cambio, retirar_solicitud_cambio
from apps.reservas.presentation.notificaciones import crear_notificacion
from apps.reservas.models.reservas import NotificacionReserva, Reserva, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from tests.integration.test_envio_propuestas_reserva import crear_propuesta
from tests.integration.utiles import identificar


SERVICIOS = {'autorizar': autorizar_solicitud_cambio, 'rechazar': rechazar_solicitud_cambio,
             'retirar': retirar_solicitud_cambio}


class DecisionesCambioReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('decision-admin')
        cls.titular = User.objects.create_user('decision-titular')
        cls.ajeno = User.objects.create_user('decision-ajeno', is_staff=True)
        for persona in [cls.admin, cls.titular, cls.ajeno]:
            identificar(persona)
        cls.unidad = crear_unidad('decision', cls.admin)
        cls.otra = crear_unidad('decision-otra', cls.ajeno)

    def setUp(self):
        self.reserva, self.solicitud = crear_propuesta(self.unidad, self.titular)
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado='solicitada')
        # Mantener la reserva leida originalmente para probar alcance obsoleto.
        self.solicitud.estado = 'solicitada'

    def decidir(self, accion, **extra):
        datos = {'actor': self.titular if accion == 'retirar' else self.admin}
        if accion == 'autorizar':
            datos['campos'] = ['actividad', 'actividad', 'insumos']
        elif accion == 'rechazar':
            datos['observacion'] = 'Motivo suficiente para rechazar'
        datos.update(extra)
        return SERVICIOS[accion](self.solicitud, **datos)

    def foto(self):
        return (Reserva.objects.filter(pk=self.reserva.pk).values().get(),
                SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).values().get(),
                RegistroAuditoriaUnidad.objects.count(), NotificacionReserva.objects.count())

    def sin_efectos(self, accion, excepcion=PermissionDenied, **extra):
        antes = self.foto()
        with self.assertRaises(excepcion):
            self.decidir(accion, **extra)
        self.assertEqual(self.foto(), antes)

    def test_autorizar_directamente_persiste_ventana_autor_auditoria_y_aviso(self):
        antes = Reserva.objects.filter(pk=self.reserva.pk).values().get()
        resultado = self.decidir('autorizar')
        self.assertEqual(resultado.estado, 'autorizada')
        self.assertEqual(resultado.campos_autorizados, ['actividad', 'insumos'])
        self.assertEqual(resultado.autorizada_por_id, self.admin.pk)
        self.assertEqual(resultado.autorizacion_vence_en - resultado.autorizada_en, timedelta(hours=48))
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().usuario_id, self.admin.pk)
        self.assertEqual(NotificacionReserva.objects.get().usuario_id, self.titular.pk)
        self.assertEqual(Reserva.objects.filter(pk=self.reserva.pk).values().get(), antes)
        self.assertFalse(self.reserva.revisiones.exists())

    def test_rechazar_conserva_propuesta_ventana_y_reserva_y_atribuye_decision(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(
            estado='enviada', propuesta={'titulo_solicitud': 'Propuesta pendiente'})
        antes = self.foto()
        resultado = self.decidir('rechazar')
        self.assertEqual(resultado.estado, 'rechazada')
        self.assertEqual(resultado.revisada_por_id, self.admin.pk)
        self.assertEqual(resultado.propuesta, antes[1]['propuesta'])
        self.assertEqual(resultado.autorizacion_vence_en, antes[1]['autorizacion_vence_en'])
        self.assertEqual(self.foto()[0], antes[0])
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().usuario_id, self.admin.pk)
        self.assertEqual(NotificacionReserva.objects.get().usuario_id, self.titular.pk)

    def test_retirar_atribuye_titular_y_avisa_personal_sin_cambiar_reserva(self):
        antes = self.foto()
        resultado = self.decidir('retirar')
        self.assertEqual(resultado.estado, 'cancelada')
        self.assertEqual(resultado.revisada_por_id, self.titular.pk)
        self.assertEqual(self.foto()[0], antes[0])
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().usuario_id, self.titular.pk)
        self.assertEqual(NotificacionReserva.objects.get().usuario_id, self.admin.pk)

    def test_cuenta_desactivada_persistida_rechaza_los_tres_actores_cacheados(self):
        get_user_model().objects.filter(pk__in=[self.admin.pk, self.titular.pk]).update(is_active=False)
        for accion in SERVICIOS:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_anonimo_staff_titular_o_administrador_de_otra_unidad_no_decide(self):
        for accion in SERVICIOS:
            actores = [AnonymousUser(), self.ajeno] + ([] if accion == 'retirar' else [self.titular])
            for actor in actores:
                with self.subTest(accion=accion, actor=actor):
                    self.sin_efectos(accion, actor=actor)

    def test_superusuario_revocado_no_usa_privilegio_cacheado(self):
        self.ajeno.is_superuser = True
        for accion in ['autorizar', 'rechazar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, actor=self.ajeno)

    def test_superusuario_no_reemplaza_titular_en_retirada(self):
        get_user_model().objects.filter(pk=self.ajeno.pk).update(is_superuser=True)
        self.sin_efectos('retirar', actor=self.ajeno)

    def test_administrador_reasignado_no_usa_unidad_cacheada(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(administrador=self.ajeno)
        for accion in ['autorizar', 'rechazar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_delegacion_revocada_no_autoriza_o_rechaza(self):
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Delegacion revocada', rol='otro', activo=False, permisos_operativos={'reservas': True})
        for accion in ['autorizar', 'rechazar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, actor=self.ajeno)

    def test_practicas_no_concede_decisiones_de_reservas(self):
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Practicas', rol='otro', permisos_operativos={'practicas': True, 'reservas': False})
        for accion in ['autorizar', 'rechazar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, actor=self.ajeno)

    def test_delegacion_vigente_de_reservas_permite_decision_directa(self):
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Reservas', rol='otro', permisos_operativos={'reservas': True})
        self.assertEqual(self.decidir('autorizar', actor=self.ajeno).autorizada_por_id, self.ajeno.pk)
        self.assertEqual(self.decidir('rechazar', actor=self.ajeno).revisada_por_id, self.ajeno.pk)

    def test_alcance_explicito_equivocado_impide_los_tres_servicios(self):
        for accion in SERVICIOS:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, unidad_esperada=self.otra.pk)

    def test_unidad_reasignada_no_decide_desde_instancia_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra)
        for accion in SERVICIOS:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_titular_o_solicitante_reasignado_impide_retirada(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(usuario=self.ajeno)
        self.sin_efectos('retirar')
        Reserva.objects.filter(pk=self.reserva.pk).update(usuario=self.titular)
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(solicitada_por=self.ajeno)
        self.sin_efectos('retirar')

    def test_autorizar_no_abre_ventana_para_antiguo_titular(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(usuario=self.ajeno)
        self.sin_efectos('autorizar', ValidationError)

    def test_alias_distinto_rechaza_las_tres_decisiones(self):
        self.solicitud._state.db = 'otra'
        for accion in SERVICIOS:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, ValidationError)

    def test_solicitud_desaparecida_da_error_de_dominio(self):
        pk = self.solicitud.pk
        SolicitudCambioReserva.objects.filter(pk=pk).delete()
        for accion in SERVICIOS:
            with self.subTest(accion=accion), self.assertRaises(ValidationError):
                self.decidir(accion)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())

    def test_decision_cerrada_persistida_no_se_sobrescribe(self):
        for estado in ['aprobada', 'rechazada', 'cancelada', 'vencida']:
            SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado=estado)
            for accion in SERVICIOS:
                with self.subTest(estado=estado, accion=accion):
                    self.sin_efectos(accion, ValidationError)

    def test_autorizacion_repetida_no_extiende_plazo_o_duplica_aviso(self):
        self.decidir('autorizar')
        self.sin_efectos('autorizar', ValidationError)

    def test_rechazo_o_retirada_repetida_preserva_primera_decision(self):
        self.decidir('rechazar')
        self.sin_efectos('rechazar', ValidationError, observacion='Otro motivo posterior')
        self.sin_efectos('retirar', ValidationError)

    def test_autorizar_rechaza_reserva_iniciada_o_cerrada(self):
        for estado in ['en_proceso', 'completada', 'cancelada', 'rechazada', 'vencida']:
            Reserva.objects.filter(pk=self.reserva.pk).update(estado=estado)
            with self.subTest(estado=estado):
                self.sin_efectos('autorizar', ValidationError)

    def test_limpieza_rechazo_y_retirada_permitida_con_reserva_cerrada_y_ventana_vencida(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado='cancelada')
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado='autorizada',
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.decidir('rechazar').estado, 'rechazada')
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado='autorizada')
        self.assertEqual(self.decidir('retirar').estado, 'cancelada')

    def test_campos_explicitos_invalidos_no_habilitan_todos_los_grupos(self):
        for campos in [[], ['inventado'], ['actividad', 'inventado'], [{}], 'actividad', {'actividad': True}]:
            with self.subTest(campos=campos):
                self.sin_efectos('autorizar', ValidationError, campos=campos)
        self.assertEqual(self.decidir('autorizar', campos=None).campos_autorizados,
                         [campo for campo, _ in SolicitudCambioReserva.CAMPOS_CHOICES])

    def test_motivo_rechazo_obligatorio_y_normalizado(self):
        for motivo in ['', '    ', 'abc', None, []]:
            with self.subTest(motivo=motivo):
                self.sin_efectos('rechazar', ValidationError, observacion=motivo)
        self.assertEqual(self.decidir('rechazar', observacion='   Motivo aceptable   ').observacion_revision, 'Motivo aceptable')

    def test_fallo_tardio_de_aviso_revierte_solicitud_auditoria_y_aviso_real(self):
        def fallar(**kwargs):
            crear_notificacion(**kwargs)
            raise RuntimeError('Fallo despues del aviso real')
        for accion in SERVICIOS:
            antes = self.foto()
            with self.subTest(accion=accion), self.captureOnCommitCallbacks() as callbacks:
                with patch('apps.reservas.presentation.decisiones_cambio.crear_notificacion', side_effect=fallar):
                    with self.assertRaises(RuntimeError):
                        self.decidir(accion)
                self.assertEqual(self.foto(), antes)
            self.assertEqual(callbacks, [])

    def test_error_de_conflicto_y_aviso_en_ingles(self):
        with override('en'):
            self.decidir('autorizar')
            self.assertEqual(NotificacionReserva.objects.get().titulo, 'Reservation editing enabled')
            with self.assertRaisesMessage(ValidationError, 'The request has already been handled.'):
                self.decidir('autorizar')

    def test_http_revocacion_entre_entrada_y_servicio_da_403_sin_efectos(self):
        for accion in SERVICIOS:
            actor = self.titular if accion == 'retirar' else self.admin
            get_user_model().objects.filter(pk=actor.pk).update(is_active=True)
            self.client.force_login(actor)
            antes = self.foto()

            def revocar(*args, **kwargs):
                get_user_model().objects.filter(pk=actor.pk).update(is_active=False)
                return SERVICIOS[accion](*args, **kwargs)

            with self.subTest(accion=accion), patch(
                f'apps.reservas.presentation.cambios_views.{SERVICIOS[accion].__name__}', side_effect=revocar
            ) as servicio:
                url = reverse('retirar_solicitud_cambio_reserva', args=[self.solicitud.pk]) if accion == 'retirar' else reverse(
                    'gestion_solicitud_cambio_reserva_accion', args=[self.unidad.slug, self.solicitud.pk])
                respuesta = self.client.post(url, {'accion': accion, 'campos': ['actividad'], 'observacion': 'Motivo valido'},
                                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                servicio.assert_called_once()
                self.assertEqual(respuesta.status_code, 403)
                self.assertEqual(self.foto(), antes)

    def test_http_campos_json_invalidos_da_400_y_no_amplia_permiso(self):
        self.client.force_login(self.admin)
        url = reverse('gestion_solicitud_cambio_reserva_accion', args=[self.unidad.slug, self.solicitud.pk])
        for valor in ['[{}]', '[', '[]', '["inventado"]', 'inventado', '[' * 1100 + ']' * 1100]:
            antes = self.foto()
            with self.subTest(valor=valor):
                respuesta = self.client.post(url, {'accion': 'autorizar', 'campos': valor})
                self.assertEqual(respuesta.status_code, 400, respuesta.content)
                self.assertEqual(self.foto(), antes)
        respuesta = self.client.post(url, {'accion': 'autorizar', 'campos': '["actividad"]'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()['solicitud_cambio']['campos_autorizados'], ['actividad'])


class CarrerasDecisionesCambioTests(TransactionTestCase):
    def carrera(self, modo):
        User = get_user_model()
        admin, titular, ajeno = [User.objects.create_user('decision-carrera-' + s) for s in ['admin', 'titular', 'ajeno']]
        unidad = crear_unidad('decision-carrera', admin)
        reserva, solicitud = crear_propuesta(unidad, titular)
        SolicitudCambioReserva.objects.filter(pk=solicitud.pk).update(estado='solicitada')
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid, orden = [], []

        def primero():
            close_old_connections()
            try:
                with transaction.atomic():
                    Reserva.objects.select_for_update().get(pk=reserva.pk)
                    if modo == 'doble_autorizacion':
                        autorizar_solicitud_cambio(solicitud, actor=admin, campos=['actividad'])
                    elif modo == 'rechazo_retirada':
                        rechazar_solicitud_cambio(solicitud, actor=admin, observacion='Primera decision de rechazo')
                    else:
                        Unidad.objects.filter(pk=unidad.pk).update(administrador=ajeno)
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError('La prueba no libero el bloqueo.')
            finally:
                connections.close_all()

        def segundo():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if sql.lstrip().startswith('SELECT') and 'FOR UPDATE' in sql:
                        if 'FROM "webcitt_reserva"' in sql:
                            orden.append('reserva')
                            seleccion.set()
                        elif 'FROM "webcitt_solicitudcambioreserva"' in sql:
                            orden.append('solicitud')
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    if modo == 'rechazo_retirada':
                        return retirar_solicitud_cambio(solicitud, actor=titular)
                    return autorizar_solicitud_cambio(solicitud, actor=admin, campos=['insumos'])
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            inicial = ejecutor.submit(primero)
            try:
                self.assertTrue(retenida.wait(timeout=10))
                posterior = ejecutor.submit(segundo)
                self.assertTrue(pid_listo.wait(timeout=10))
                self.assertTrue(seleccion.wait(timeout=10))
                espera = False
                limite = monotonic() + 5
                while monotonic() < limite:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = %s", [pid[0]])
                        fila = cursor.fetchone()
                    if fila and fila[0]:
                        espera = True
                        break
                    sleep(0.02)
                self.assertTrue(espera, 'La segunda decision debe esperar la reserva.')
            finally:
                liberar.set()
            inicial.result(timeout=10)
            with self.assertRaises(PermissionDenied if modo == 'revocacion_unidad' else ValidationError):
                posterior.result(timeout=10)
        self.assertEqual(orden[:2], ['reserva', 'solicitud'])
        solicitud.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(reserva.titulo_solicitud, 'Actividad original')
        if modo == 'revocacion_unidad':
            self.assertEqual(solicitud.estado, 'solicitada')
            self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
            self.assertFalse(NotificacionReserva.objects.exists())
        else:
            self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
            self.assertEqual(NotificacionReserva.objects.count(), 1)
            if modo == 'doble_autorizacion':
                self.assertEqual(solicitud.estado, 'autorizada')
                self.assertEqual(solicitud.campos_autorizados, ['actividad'])
            else:
                self.assertEqual(solicitud.estado, 'rechazada')
                self.assertEqual(solicitud.revisada_por_id, admin.pk)

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_dos_autorizaciones_concurrentes_no_extienden_o_amplian_primera_ventana(self):
        self.carrera('doble_autorizacion')

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_rechazo_concurrente_no_se_reinterpreta_como_retirada(self):
        self.carrera('rechazo_retirada')

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_revocacion_de_administrador_durante_espera_no_usa_join_obsoleto(self):
        self.carrera('revocacion_unidad')
