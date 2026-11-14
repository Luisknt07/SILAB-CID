"""Cierre autonomo: autoridad fresca, persistencia, rollback y repeticion."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.reservas.presentation.ejecucion import registrar_cierre_operativo
from apps.reservas.presentation.finalizacion import completar_reserva
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import NotificacionReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_autoridad_escritores_reserva import crear_unidad


def consumo_de_cinco_dolares(reserva):
    """Un ingreso probado corresponde a material trazable, nunca a personal o patrimonio."""
    prefijo = f'BASE-CIERRE-{reserva.pk}'
    catalogo = EquiposServicios.objects.create(codigo=prefijo, nombre='Equipo del cierre')
    equipo = UnidadEquipo.objects.create(codigo_unidad=prefijo, equipo=catalogo, laboratorio=reserva.laboratorio)
    insumo = Consumible.objects.create(unidad=reserva.laboratorio, codigo=prefijo, nombre='Material del cierre',
        stock_total=Decimal('20'), precio_unitario=Decimal('1'), unidad_medida='g')
    lote = LoteConsumible.objects.create(consumible=insumo, codigo=prefijo, cantidad_inicial=20,
        cantidad_actual=20, estado='en_uso', equipo_en_uso=equipo)
    registro = ReservaConsumible.objects.create(reserva=reserva, consumible=insumo,
        cantidad_solicitada=5, cantidad_aprobada=5)
    reserva.unidades_seleccionadas = json.dumps([{'id': equipo.pk}])
    reserva.save(update_fields=['unidades_seleccionadas'])
    return json.dumps([{'reserva_consumible_id': registro.pk, 'consumida': '5',
                        'lote_id': lote.pk, 'equipo_id': equipo.pk}])


class ContratoCierreOperativoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('cierre-admin')
        cls.titular = User.objects.create_user('cierre-titular')
        cls.ajeno = User.objects.create_user('cierre-ajeno', is_staff=True)
        cls.unidad = crear_unidad('cierre', cls.admin)
        cls.otra = crear_unidad('cierre-otra', cls.ajeno)

    def setUp(self):
        self.reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.titular,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(9), hora_fin=time(10), estado='confirmada', tipo_solicitud='servicio')
        self.datos = {'ejecucion_monto_cobrado': '5',
                      'ejecucion_justificacion_ajuste': 'Ajuste autorizado de prueba',
                      'ejecucion_consumibles_json': consumo_de_cinco_dolares(self.reserva)}
        self.datos['ejecucion_equipos_ids'] = [json.loads(self.datos['ejecucion_consumibles_json'])[0]['equipo_id']]

    def intacta(self):
        self.reserva.refresh_from_db(using='default')
        self.assertFalse(self.reserva.detalle_ejecucion)
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=self.reserva).exists())
        self.assertFalse(IncidenciaEquipo.objects.filter(reserva=self.reserva).exists())

    def test_cierre_directo_persiste_estado_y_liquidacion_sin_save_del_caller(self):
        detalle = registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'completada')
        self.assertEqual(self.reserva.resultado_cierre, 'atendida')
        self.assertIsNotNone(self.reserva.fecha_cierre)
        self.assertEqual(self.reserva.detalle_ejecucion, detalle)
        self.assertEqual(self.reserva.desglose_liquidacion, detalle['liquidacion'])
        self.assertEqual(MovimientoFinancieroUnidad.objects.get(reserva=self.reserva).monto, Decimal('5'))

    def test_no_cobra_sin_material_util_consumido(self):
        self.datos['ejecucion_consumibles_json'] = '[]'
        with self.assertRaisesMessage(ValueError, 'no puede superar los materiales'):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_titular_no_cierra_su_propia_reserva(self):
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.titular, self.datos)
        self.intacta()

    def test_staff_de_otra_unidad_no_cierra(self):
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.ajeno, self.datos)
        self.intacta()

    def test_anonimo_no_cierra(self):
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, AnonymousUser(), self.datos)
        self.intacta()

    def test_cuenta_desactivada_no_usa_objeto_activo_obsoleto(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_administrador_retirado_no_usa_relacion_cacheada(self):
        self.reserva.laboratorio = self.unidad
        type(self.unidad).objects.filter(pk=self.unidad.pk).update(administrador=None)
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_superusuario_revocado_no_usa_privilegio_cacheado(self):
        self.ajeno.is_superuser = True
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.ajeno, self.datos)
        self.intacta()

    def test_delegacion_reservas_cierra(self):
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Delegacion', rol='otro', permisos_operativos={'reservas': True, 'practicas': False})
        registrar_cierre_operativo(self.reserva, self.ajeno, self.datos)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'completada')

    def test_solo_practicas_no_cierra(self):
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Delegacion', rol='otro', permisos_operativos={'reservas': False, 'practicas': True})
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.ajeno, self.datos)
        self.intacta()

    def test_scope_explicito_distinto_rechaza_incluso_superusuario(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_superuser=True)
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos, unidad_esperada=self.otra.pk)
        self.intacta()

    def test_unidad_persistida_distinta_rechaza_objeto_obsoleto(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra)
        with self.assertRaises(PermissionDenied):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_estado_cancelado_persistido_no_usa_estado_confirmado(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado='cancelada')
        with self.assertRaises(ValueError):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()
        self.assertEqual(self.reserva.estado, 'cancelada')

    def test_horario_futuro_persistido_impide_cierre_confirmado(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(fecha=timezone.localdate() + timedelta(days=1))
        with self.assertRaises(ValueError):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_reserva_eliminada_da_error_de_negocio(self):
        Reserva.objects.filter(pk=self.reserva.pk).delete()
        with self.assertRaisesMessage(ValueError, 'ya no'):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)

    def test_alias_distinto_no_escribe_en_default(self):
        self.reserva._state.db = 'otra_base'
        with self.assertRaisesMessage(ValueError, 'base de datos principal'):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()

    def test_detalle_existente_impide_reescritura_aun_con_estado_confirmado(self):
        previo = {'registrada_en': 'historial previo'}
        Reserva.objects.filter(pk=self.reserva.pk).update(detalle_ejecucion=previo)
        for idioma, mensaje in (('es', 'ya tiene un cierre'), ('en', 'already has an operational closure')):
            with self.subTest(idioma=idioma), override(idioma), self.assertRaisesMessage(ValueError, mensaje):
                registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.detalle_ejecucion, previo)
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=self.reserva).exists())

    def test_cierre_heredado_sin_detalle_requiere_permiso_excepcional(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado='completada')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.ajeno,
            nombre='Delegacion', rol='otro', permisos_operativos={'reservas': True, 'corregir_cerradas': False})
        with self.assertRaises(ValueError):
            registrar_cierre_operativo(self.reserva, self.ajeno, self.datos)
        self.intacta()
        registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.reserva.refresh_from_db()
        self.assertTrue(self.reserva.es_efectiva)

    def test_rollback_tardio_revierte_asistencia_ingreso_y_cierre(self):
        persona = RegistroParticipanteReserva.objects.create(
            reserva=self.reserva, usuario=self.titular, nombre='Titular de prueba', rol='solicitante')
        with patch('apps.reservas.presentation.ejecucion._sincronizar_ejecucion_practica',
                   side_effect=ValueError('Fallo tardio de prueba')):
            with self.assertRaisesMessage(ValueError, 'Fallo tardio'):
                registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()
        persona.refresh_from_db()
        self.assertEqual(persona.asistencia, 'prevista')

    def test_repeticion_no_duplica_consumo_incidencia_o_ingreso(self):
        catalogo = EquiposServicios.objects.create(codigo='CIERRE-CAT', nombre='Equipo cierre')
        equipo = UnidadEquipo.objects.create(codigo_unidad='CIERRE-EQ', equipo=catalogo, laboratorio=self.unidad)
        consumible = Consumible.objects.create(unidad=self.unidad, codigo='CIERRE-MAT', nombre='Insumo cierre',
            stock_total=Decimal('100'), precio_unitario=Decimal('1'), unidad_medida='g')
        lote = LoteConsumible.objects.create(consumible=consumible, codigo='CIERRE-LOTE',
            cantidad_inicial=Decimal('100'), cantidad_actual=Decimal('100'), estado='en_uso', equipo_en_uso=equipo)
        registro = ReservaConsumible.objects.create(reserva=self.reserva, consumible=consumible,
            cantidad_solicitada=Decimal('10'), cantidad_aprobada=Decimal('10'))
        Reserva.objects.filter(pk=self.reserva.pk).update(unidades_seleccionadas=json.dumps([{'id': equipo.pk}]))
        self.datos.update(ejecucion_tuvo_incidencia='1', ejecucion_incidencia_equipo_id=str(equipo.pk),
            ejecucion_incidencia_titulo='Incidencia de prueba', ejecucion_incidencia_descripcion='Descripcion de prueba',
            ejecucion_consumibles_json=json.dumps([{'reserva_consumible_id': registro.pk, 'consumida': '10',
                                                  'lote_id': lote.pk, 'equipo_id': equipo.pk}]))
        with patch('apps.reservas.presentation.ejecucion._sincronizar_ejecucion_practica',
                   side_effect=ValueError('Fallo posterior al consumo')):
            with self.assertRaisesMessage(ValueError, 'Fallo posterior'):
                registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.intacta()
        lote.refresh_from_db()
        consumible.refresh_from_db()
        registro.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal('100'))
        self.assertEqual(consumible.stock_total, Decimal('100'))
        self.assertFalse(registro.cantidad_consumida)
        self.assertFalse(EntradaInventario.objects.filter(reserva=self.reserva).exists())
        detalle = registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.datos['ejecucion_monto_cobrado'] = '20'
        with self.assertRaisesMessage(ValueError, 'ya tiene un cierre'):
            registrar_cierre_operativo(self.reserva, self.admin, self.datos)
        self.reserva.refresh_from_db()
        lote.refresh_from_db()
        consumible.refresh_from_db()
        self.assertEqual(self.reserva.detalle_ejecucion, detalle)
        self.assertEqual(lote.cantidad_actual, Decimal('90'))
        self.assertEqual(consumible.stock_total, Decimal('90'))
        self.assertEqual(EntradaInventario.objects.filter(reserva=self.reserva).count(), 1)
        self.assertEqual(IncidenciaEquipo.objects.filter(reserva=self.reserva).count(), 1)
        self.assertEqual(MovimientoFinancieroUnidad.objects.get(reserva=self.reserva).monto, Decimal('5'))

    def test_finalizacion_integral_persiste_relaciones_y_trazabilidad(self):
        responsable = ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=self.admin,
            nombre='Responsable de cierre',
            rol='otro',
            recibe_reservas=True,
        )
        solicitud = SolicitudCambioReserva.objects.create(
            reserva=self.reserva,
            solicitada_por=self.titular,
            motivo_solicitud='Cambio pendiente al cerrar',
        )
        avisos = [
            NotificacionReserva.objects.create(
                reserva=self.reserva,
                usuario=self.titular,
                tipo=tipo,
                titulo='Aviso operativo',
                mensaje='Pendiente antes del cierre',
                clave=clave,
            )
            for tipo, clave in (
                ('cierre_pendiente', f'reserva:{self.reserva.pk}:cierre'),
                ('informacion', f'reserva:{self.reserva.pk}:sin_responsable'),
                ('informacion', f'reserva:{self.reserva.pk}:riesgo_operativo:1'),
            )
        ]
        datos = {
            **self.datos,
            'ejecucion_registrada': '1',
            'participantes_seleccionados': '[]',
            'asistencia_solicitante': 'asistio',
            'ejecucion_asistentes_total': '1',
        }

        resultado = completar_reserva(
            self.reserva,
            actor=self.admin,
            datos=datos,
            observacion='Atencion comprobada.',
            responsable_id=responsable.pk,
            unidad_esperada=self.unidad.pk,
        )

        self.reserva.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertEqual(resultado.pk, self.reserva.pk)
        self.assertEqual(self.reserva.estado, 'completada')
        self.assertEqual(self.reserva.resultado_cierre, 'atendida')
        self.assertEqual(self.reserva.responsable_asignado, responsable)
        self.assertEqual(self.reserva.numero_participantes, 1)
        self.assertEqual(
            self.reserva.registros_participantes.get(usuario=self.titular).asistencia,
            'asistio',
        )
        self.assertEqual(solicitud.estado, 'cancelada')
        self.assertFalse(
            NotificacionReserva.objects.filter(pk__in=[item.pk for item in avisos], leida=False).exists()
        )
        self.assertTrue(
            NotificacionReserva.objects.filter(
                reserva=self.reserva,
                clave__contains=':accion:completar:',
            ).exists()
        )
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.reserva.pk)).exists())
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                usuario=self.admin,
                objeto_id=str(self.reserva.pk),
                descripcion__contains='completada',
            ).exists()
        )

    def test_fallo_tardio_revierte_toda_la_finalizacion_integral(self):
        responsable = ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=self.admin,
            nombre='Responsable para rollback',
            rol='otro',
            recibe_reservas=True,
        )
        solicitud = SolicitudCambioReserva.objects.create(
            reserva=self.reserva,
            solicitada_por=self.titular,
            motivo_solicitud='Debe seguir activa',
        )
        aviso = NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo='cierre_pendiente',
            titulo='Cierre pendiente',
            mensaje='Debe seguir sin leer',
            clave=f'reserva:{self.reserva.pk}:cierre:rollback',
        )
        datos = {
            **self.datos,
            'ejecucion_registrada': '1',
            'participantes_seleccionados': '[]',
            'asistencia_solicitante': 'asistio',
            'ejecucion_asistentes_total': '1',
        }

        with patch(
            'apps.reservas.presentation.finalizacion.otorgar_habilitaciones_por_sesion',
            side_effect=ValueError('Fallo posterior al cierre operativo'),
        ):
            with self.assertRaisesMessage(ValueError, 'Fallo posterior'):
                completar_reserva(
                    self.reserva,
                    actor=self.admin,
                    datos=datos,
                    responsable_id=responsable.pk,
                )

        self.reserva.refresh_from_db()
        solicitud.refresh_from_db()
        aviso.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'confirmada')
        self.assertIsNone(self.reserva.responsable_asignado)
        self.assertFalse(self.reserva.detalle_ejecucion)
        self.assertFalse(self.reserva.registros_participantes.exists())
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(reserva=self.reserva).exists())
        self.assertEqual(solicitud.estado, 'solicitada')
        self.assertFalse(aviso.leida)
        self.assertFalse(LogEntry.objects.filter(object_id=str(self.reserva.pk)).exists())
        self.assertFalse(
            RegistroAuditoriaUnidad.objects.filter(objeto_id=str(self.reserva.pk)).exists()
        )

    def test_revocacion_durante_post_rechaza_en_servicio_y_revierte_participantes(self):
        self.client.force_login(self.admin)

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return completar_reserva(*args, **kwargs)

        with patch('apps.gestion_unidades.presentation.gestion.completar_reserva', side_effect=revocar) as servicio:
            respuesta = self.client.post(reverse('gestion_reserva_accion',
                args=[self.unidad.slug, self.reserva.pk]), {'accion': 'completar', **self.datos})
        servicio.assert_called_once()
        self.assertEqual(respuesta.status_code, 403)
        self.intacta()
        self.assertFalse(self.reserva.registros_participantes.exists())


class BloqueoCierreOperativoTests(TransactionTestCase):
    @skipUnless(connection.vendor == 'postgresql', 'Bloqueo comprobado con PostgreSQL.')
    def test_dos_cierres_concurrentes_generan_un_solo_ingreso(self):
        titular = get_user_model().objects.create_user('escritor-carrera')
        unidad = crear_unidad('carrera-cierre', titular)
        sesion = Reserva.objects.create(laboratorio=unidad, usuario=titular,
            fecha=timezone.localdate() - timedelta(days=1), hora_inicio=time(9), hora_fin=time(10),
            estado='confirmada', tipo_solicitud='servicio')
        datos = {'ejecucion_monto_cobrado': '5', 'ejecucion_justificacion_ajuste': 'Ajuste de prueba',
                 'ejecucion_consumibles_json': consumo_de_cinco_dolares(sesion)}
        retenida, liberar, pid_listo, seleccion_bloqueante = Event(), Event(), Event(), Event()
        pid = []

        def aprobar():
            close_old_connections()
            try:
                with transaction.atomic():
                    fresca = Reserva.objects.select_for_update().get(pk=sesion.pk)
                    registrar_cierre_operativo(fresca, titular, datos)
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError('La prueba no libero el bloqueo.')
            finally:
                connections.close_all()

        def completar():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if sql.lstrip().startswith('SELECT') and 'FROM "webcitt_reserva"' in sql and 'FOR UPDATE' in sql:
                        seleccion_bloqueante.set()
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    return registrar_cierre_operativo(sesion, titular, datos)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            aprobacion = ejecutor.submit(aprobar)
            try:
                self.assertTrue(retenida.wait(timeout=10))
                edicion = ejecutor.submit(completar)
                self.assertTrue(pid_listo.wait(timeout=10))
                self.assertTrue(seleccion_bloqueante.wait(timeout=10))
                esperando = False
                limite = monotonic() + 5
                while monotonic() < limite:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type = 'Lock' "
                                       'FROM pg_stat_activity WHERE pid = %s', [pid[0]])
                        estado = cursor.fetchone()
                    if estado and all(estado):
                        esperando = True
                        break
                    sleep(0.02)
                self.assertTrue(esperando, 'La escritura debe esperar en SELECT FOR UPDATE.')
            finally:
                liberar.set()
            aprobacion.result(timeout=10)
            with self.assertRaisesMessage(ValueError, 'ya tiene un cierre'):
                edicion.result(timeout=10)
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, 'completada')
        self.assertEqual(MovimientoFinancieroUnidad.objects.filter(reserva=sesion).count(), 1)
        self.assertEqual(MovimientoFinancieroUnidad.objects.get(reserva=sesion).monto, Decimal('5'))
