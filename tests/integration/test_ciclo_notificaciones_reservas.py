from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command, CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.reservas.presentation import notificaciones as notificaciones_reservas
from apps.reservas.presentation.notificaciones import crear_notificacion, procesar_recordatorios_reservas, reenviar_notificaciones_pendientes
from apps.reservas.presentation.ciclo import analizar_riesgos_operativos_reservas
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import NotificacionReserva, Reserva, ReservaConsumible
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CicloNotificacionesReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('admin-ciclo', email='admin@upec.edu.ec', password='clave')
        cls.solicitante = User.objects.create_user('usuario-ciclo', email='usuario@upec.edu.ec', password='clave')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ciclo de reservas',
            descripcion='Pruebas de cierre y notificaciones.',
            fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-ciclo-reservas',
            dependencia='laboratorios',
            administrador=cls.admin,
        )
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.admin,
            rol='responsable_tecnico',
            activo=True,
            recibe_reservas=True,
        )

    def reserva(
        self,
        *,
        estado,
        fecha=None,
        hora_inicio=time(8),
        hora_fin=time(9),
        asignada=True,
    ):
        return Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.solicitante,
            responsable_asignado=self.responsable if asignada else None,
            fecha=fecha or timezone.localdate(),
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            equipo_codigo='EQ-CICLO',
            equipo_nombre='Equipo de ciclo',
            titulo_solicitud='Reserva para validar ciclo',
            proposito_codigo='docencia_practica',
            estado=estado,
        )

    def otra_unidad(self):
        return Unidad.objects.create(
            nombre='Laboratorio fuera del alcance',
            descripcion='Unidad independiente para probar el proceso periodico.',
            fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-fuera-alcance',
            dependencia='laboratorios',
            administrador=self.admin,
        )

    def test_proceso_automatico_vence_pendientes_y_avisa_cierres_una_sola_vez(self):
        pendiente = self.reserva(estado='pendiente', fecha=timezone.localdate() - timedelta(days=1))
        confirmada = self.reserva(estado='confirmada', fecha=timezone.localdate() - timedelta(days=1))

        primero = procesar_recordatorios_reservas(enviar_email=False)
        segundo = procesar_recordatorios_reservas(enviar_email=False)

        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, 'vencida')
        self.assertEqual(pendiente.resultado_cierre, 'vencida')
        self.assertEqual(primero['vencidas'], 1)
        self.assertEqual(segundo['vencidas'], 0)
        self.assertEqual(
            NotificacionReserva.objects.filter(reserva=confirmada, tipo='cierre_pendiente').count(),
            1,
        )
        auditoria = RegistroAuditoriaUnidad.objects.get(
            objeto_id=str(pendiente.pk),
            descripcion='Vencimiento automático de solicitud sin aprobación.',
        )
        self.assertIsNone(auditoria.usuario)
        self.assertEqual(auditoria.datos_anteriores['estado'], 'pendiente')
        self.assertEqual(auditoria.datos_nuevos['estado'], 'vencida')

    def test_no_cierra_automaticamente_confirmadas_o_en_proceso(self):
        fecha_base = date(2026, 9, 3)
        zona = timezone.get_current_timezone()
        ahora = timezone.make_aware(datetime.combine(fecha_base, time(10)), zona)
        confirmada = self.reserva(
            estado='confirmada',
            fecha=fecha_base,
            hora_inicio=time(8),
            hora_fin=time(9),
        )
        en_proceso = self.reserva(
            estado='en_proceso',
            fecha=fecha_base,
            hora_inicio=time(8),
            hora_fin=time(9),
        )

        resultado = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)

        confirmada.refresh_from_db()
        en_proceso.refresh_from_db()
        self.assertEqual(confirmada.estado, 'confirmada')
        self.assertEqual(en_proceso.estado, 'en_proceso')
        self.assertEqual(resultado['cierres_pendientes'], 2)

    def test_vence_una_pendiente_del_mismo_dia_al_terminar_la_hora(self):
        fecha_base = date(2026, 9, 3)
        zona = timezone.get_current_timezone()
        ahora = timezone.make_aware(datetime.combine(fecha_base, time(10)), zona)
        pendiente = self.reserva(
            estado='pendiente',
            fecha=fecha_base,
            hora_inicio=time(8),
            hora_fin=time(9),
        )

        procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)

        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, 'vencida')
        self.assertEqual(pendiente.resultado_cierre, 'vencida')

    def test_proceso_acotado_no_lee_ni_escribe_reservas_de_otra_unidad(self):
        propia = self.reserva(
            estado='pendiente',
            fecha=timezone.localdate() - timedelta(days=1),
        )
        ajena = Reserva.objects.create(
            laboratorio=self.otra_unidad(),
            usuario=self.solicitante,
            fecha=timezone.localdate() - timedelta(days=1),
            hora_inicio=time(8),
            hora_fin=time(9),
            equipo_codigo='EQ-AJENO',
            equipo_nombre='Equipo ajeno',
            titulo_solicitud='Reserva ajena al proceso',
            proposito_codigo='docencia_practica',
            estado='pendiente',
        )

        ahora = timezone.now()
        with patch(
            'apps.formacion.presentation.asignaturas.avisar_guias_de_sesion',
            return_value=0,
        ) as avisar_guias:
            resultado = procesar_recordatorios_reservas(
                ahora=ahora,
                enviar_email=False,
                unidad=self.unidad,
            )

        propia.refresh_from_db()
        ajena.refresh_from_db()
        self.assertEqual(resultado['vencidas'], 1)
        self.assertEqual(propia.estado, 'vencida')
        self.assertEqual(ajena.estado, 'pendiente')
        self.assertFalse(NotificacionReserva.objects.filter(reserva=ajena).exists())
        avisar_guias.assert_called_once_with(
            ahora,
            enviar_email=False,
            unidad=self.unidad,
        )

    def test_aviso_de_asignacion_es_idempotente_y_abre_la_solicitud(self):
        fecha_base = date(2026, 9, 3)
        zona = timezone.get_current_timezone()
        ahora = timezone.make_aware(datetime.combine(fecha_base, time(7)), zona)
        reserva = self.reserva(
            estado='pendiente',
            fecha=fecha_base + timedelta(days=1),
            asignada=False,
        )

        primero = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)
        segundo = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)

        notification = NotificacionReserva.objects.get(
            clave=f'reserva:{reserva.pk}:sin_responsable'
        )
        self.assertEqual(primero['sin_responsable'], 1)
        self.assertEqual(segundo['sin_responsable'], 0)
        self.assertEqual(notification.usuario, self.admin)
        self.assertIn('filtro_reservas=sin_asignar', notification.url)
        self.assertIn(f'reserva={reserva.pk}', notification.url)

    def test_detecta_y_notifica_riesgos_de_recursos_y_stock_sin_duplicar(self):
        fecha_base = date(2026, 9, 3)
        zona = timezone.get_current_timezone()
        ahora = timezone.make_aware(datetime.combine(fecha_base, time(7)), zona)
        catalog = EquiposServicios.objects.create(
            codigo='EQ-RIESGO',
            nombre='Impresora con falla',
        )
        equipment = UnidadEquipo.objects.create(
            codigo_unidad='UE-RIESGO-001',
            equipo=catalog,
            laboratorio=self.unidad,
            estado_unidad='dañado',
            activa=True,
        )
        space = EspacioReservable.objects.create(
            unidad=self.unidad,
            codigo='AREA-RIESGO',
            nombre='Área temporalmente cerrada',
            reservable=False,
        )
        software = SoftwareDisponible.objects.create(
            unidad=self.unidad,
            codigo='SW-RIESGO',
            nombre='CAD sin licencias',
            tipo_acceso='licencia',
            licencias_totales=1,
            licencias_disponibles=0,
        )
        consumable = Consumible.objects.create(
            unidad=self.unidad,
            codigo='MAT-RIESGO',
            nombre='Filamento crítico',
            unidad_medida='g',
            stock_total=Decimal('50'),
            stock_seguridad=Decimal('20'),
            minimo=Decimal('20'),
        )
        reservation = self.reserva(
            estado='confirmada',
            fecha=fecha_base + timedelta(days=1),
        )
        reservation.unidades_seleccionadas = json.dumps([{'id': equipment.pk}])
        reservation.incluye_espacio = True
        reservation.solicito_espacio = True
        reservation.alcance_espacio = 'areas'
        reservation.provision_consumibles = 'unidad'
        reservation.save()
        reservation.espacios_solicitados.add(space)
        reservation.software_solicitado.add(software)
        ReservaConsumible.objects.create(
            reserva=reservation,
            consumible=consumable,
            cantidad_solicitada=Decimal('40'),
        )
        block = BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            tipo='mantenimiento',
            titulo='Cierre preventivo del área',
            fecha_inicio=reservation.fecha,
            fecha_fin=reservation.fecha,
            dia_completo=True,
            alcance='areas',
        )
        block.espacios.add(space)

        analysis = analizar_riesgos_operativos_reservas(
            unidad=self.unidad,
            ahora=ahora,
        )
        codes = {
            risk['codigo']
            for item in analysis
            if item['reserva'].pk == reservation.pk
            for risk in item['riesgos']
        }
        first = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)
        second = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)

        self.assertTrue(
            {
                'equipo_no_disponible',
                'espacio_no_disponible',
                'software_sin_licencias',
                'bloqueo_agenda',
                'stock_proyectado_insuficiente',
            }.issubset(codes)
        )
        self.assertEqual(first['riesgos_operativos'], 1)
        self.assertEqual(second['riesgos_operativos'], 0)
        notification = NotificacionReserva.objects.get(
            reserva=reservation,
            clave__contains=':riesgo_operativo:',
        )
        self.assertIn('filtro_reservas=riesgo', notification.url)
        self.assertIn(f'reserva={reservation.pk}', notification.url)

    def test_laboratorista_cierra_como_no_atendida_con_motivo(self):
        reserva = self.reserva(estado='confirmada', fecha=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {'accion': 'no_atendida', 'observacion': 'Equipo fuera de servicio; se contactó al usuario.'},
        )

        self.assertEqual(response.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'no_atendida')
        self.assertEqual(reserva.resultado_cierre, 'no_atendida')
        self.assertIsNotNone(reserva.fecha_cierre)
        self.assertTrue(NotificacionReserva.objects.filter(reserva=reserva, usuario=self.solicitante).exists())

    def test_reporte_separa_solicitudes_de_atenciones_efectivas(self):
        completada = self.reserva(estado='completada')
        completada.resultado_cierre = 'atendida'
        completada.numero_participantes = 4
        completada.detalle_ejecucion = {
            'registrada_en': timezone.now().isoformat(),
            'asistentes_total': 4,
        }
        completada.save()
        self.reserva(estado='confirmada', hora_inicio=time(10), hora_fin=time(12))
        request = RequestFactory().get('/', {
            'desde': timezone.localdate().isoformat(),
            'hasta': timezone.localdate().isoformat(),
        })

        reporte = build_unit_report(request, self.unidad)

        self.assertEqual(reporte['metrics']['total'], 2)
        self.assertEqual(reporte['metrics']['confirmed'], 1)
        self.assertEqual(reporte['metrics']['hours'], 1.0)
        self.assertEqual(reporte['metrics']['participants'], 4)

    def test_recordatorios_24h_y_2h_son_idempotentes(self):
        fecha_base = timezone.localdate()
        zona = timezone.get_current_timezone()
        ahora = timezone.make_aware(datetime.combine(fecha_base, time(8)), zona)
        reserva_24h = self.reserva(
            estado='confirmada',
            fecha=fecha_base + timedelta(days=1),
            hora_inicio=time(8),
            hora_fin=time(9),
        )
        reserva_2h = self.reserva(
            estado='confirmada',
            fecha=fecha_base,
            hora_inicio=time(9),
            hora_fin=time(10),
        )

        primero = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)
        segundo = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)

        self.assertEqual(primero['recordatorios_24h'], 1)
        self.assertEqual(primero['recordatorios_2h'], 1)
        self.assertEqual(segundo['recordatorios_24h'], 0)
        self.assertEqual(segundo['recordatorios_2h'], 0)
        self.assertEqual(
            NotificacionReserva.objects.filter(reserva=reserva_24h, tipo='recordatorio_24h').count(),
            1,
        )
        self.assertEqual(
            NotificacionReserva.objects.filter(reserva=reserva_2h, tipo='recordatorio_2h').count(),
            1,
        )

    def test_correo_usa_plantilla_html_y_registra_entrega(self):
        reserva = self.reserva(estado='confirmada')
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            notificacion, creada = crear_notificacion(
                reserva=reserva,
                usuario=self.solicitante,
                tipo='estado',
                titulo='Reserva confirmada',
                mensaje='La reserva está lista para ser atendida.',
                clave=f'prueba-correo:{reserva.pk}',
            )

        notificacion.refresh_from_db()
        reserva.refresh_from_db()
        self.assertTrue(creada)
        self.assertTrue(notificacion.enviada_email)
        self.assertEqual(notificacion.intentos_email, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('GESTIÓN Y RESERVA', mail.outbox[0].alternatives[0][0])
        self.assertIn(reserva.codigo_reserva, mail.outbox[0].alternatives[0][0])
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')

    def test_backend_local_deja_correo_pendiente_y_lo_envia_al_configurar(self):
        reserva = self.reserva(estado='pendiente')

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            with self.captureOnCommitCallbacks(execute=True):
                notificacion, _ = crear_notificacion(
                    reserva=reserva,
                    usuario=self.solicitante,
                    tipo='confirmacion',
                    titulo='Solicitud recibida',
                    mensaje='La copia queda guardada en el sistema.',
                    clave=f'prueba-correo-pendiente:{reserva.pk}',
                )

        notificacion.refresh_from_db()
        self.assertFalse(notificacion.enviada_email)
        self.assertEqual(notificacion.intentos_email, 0)
        self.assertIn('pendiente', notificacion.error_email.lower())

        resultado = reenviar_notificaciones_pendientes()

        notificacion.refresh_from_db()
        self.assertEqual(resultado['correos_reintentados'], 1)
        self.assertTrue(notificacion.enviada_email)

    def test_reintentos_de_correo_respetan_el_alcance_de_unidad(self):
        propia = self.reserva(estado='pendiente')
        ajena = Reserva.objects.create(
            laboratorio=self.otra_unidad(),
            usuario=self.solicitante,
            fecha=timezone.localdate(),
            hora_inicio=time(10),
            hora_fin=time(11),
            equipo_codigo='EQ-CORREO-AJENO',
            equipo_nombre='Equipo de otra unidad',
            titulo_solicitud='Correo fuera del alcance',
            proposito_codigo='docencia_practica',
            estado='pendiente',
        )
        notificacion_propia, _ = crear_notificacion(
            reserva=propia,
            usuario=self.solicitante,
            tipo='estado',
            titulo='Aviso propio',
            mensaje='Aviso de la unidad procesada.',
            clave=f'correo-propio:{propia.pk}',
            enviar_email=False,
        )
        notificacion_ajena, _ = crear_notificacion(
            reserva=ajena,
            usuario=self.solicitante,
            tipo='estado',
            titulo='Aviso ajeno',
            mensaje='Aviso de otra unidad.',
            clave=f'correo-ajeno:{ajena.pk}',
            enviar_email=False,
        )
        NotificacionReserva.objects.filter(
            pk__in=(notificacion_propia.pk, notificacion_ajena.pk)
        ).update(error_email='Envío pendiente: configuración institucional.')
        mail.outbox.clear()

        resultado = reenviar_notificaciones_pendientes(unidad=self.unidad)

        notificacion_propia.refresh_from_db()
        notificacion_ajena.refresh_from_db()
        self.assertEqual(resultado, {'correos_reintentados': 1, 'correos_fallidos': 0})
        self.assertTrue(notificacion_propia.enviada_email)
        self.assertFalse(notificacion_ajena.enviada_email)
        self.assertEqual(notificacion_ajena.intentos_email, 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_reclamo_de_intento_impide_dos_entregas_del_mismo_aviso(self):
        reserva = self.reserva(estado='confirmada')
        notificacion, _ = crear_notificacion(
            reserva=reserva,
            usuario=self.solicitante,
            tipo='estado',
            titulo='Aviso reclamado',
            mensaje='Solo un ejecutor debe reclamarlo.',
            clave=f'correo-reclamado:{reserva.pk}',
            enviar_email=False,
        )
        ahora = timezone.now()

        primero = notificaciones_reservas._reclamar_intento_email(
            notificacion.pk,
            ahora=ahora,
        )
        segundo = notificaciones_reservas._reclamar_intento_email(
            notificacion.pk,
            ahora=ahora,
        )

        notificacion.refresh_from_db()
        self.assertIsNotNone(primero)
        self.assertIsNone(segundo)
        self.assertEqual(notificacion.intentos_email, 1)
        self.assertEqual(notificacion.ultimo_intento_email, ahora)

    @override_settings(RESERVATION_EMAIL_RETRY_MINUTES=15)
    def test_correo_fallido_se_reintenta_sin_duplicar_notificacion(self):
        reserva = self.reserva(estado='confirmada')
        with patch(
            'apps.reservas.presentation.notificaciones.EmailMultiAlternatives.send',
            side_effect=RuntimeError('SMTP no disponible'),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                notificacion, _ = crear_notificacion(
                    reserva=reserva,
                    usuario=self.solicitante,
                    tipo='estado',
                    titulo='Cambio operativo',
                    mensaje='Se actualizó la reserva.',
                    clave=f'prueba-reintento:{reserva.pk}',
                )

        notificacion.refresh_from_db()
        self.assertFalse(notificacion.enviada_email)
        self.assertEqual(notificacion.intentos_email, 1)
        self.assertIn('SMTP no disponible', notificacion.error_email)
        notificacion.ultimo_intento_email = timezone.now() - timedelta(minutes=16)
        notificacion.save(update_fields=['ultimo_intento_email'])

        with patch(
            'apps.reservas.presentation.notificaciones.EmailMultiAlternatives.send',
            return_value=1,
        ):
            resultado = reenviar_notificaciones_pendientes()

        notificacion.refresh_from_db()
        self.assertEqual(resultado['correos_reintentados'], 1)
        self.assertEqual(resultado['correos_fallidos'], 0)
        self.assertTrue(notificacion.enviada_email)
        self.assertEqual(notificacion.intentos_email, 2)
        self.assertEqual(
            NotificacionReserva.objects.filter(clave=f'prueba-reintento:{reserva.pk}').count(),
            1,
        )

    def test_comando_diagnostica_correo_sin_enviar(self):
        salida = StringIO()
        call_command('verificar_correo_reservas', stdout=salida)
        texto = salida.getvalue()
        self.assertIn('Backend:', texto)
        self.assertIn('Configuración inspeccionada sin enviar correo.', texto)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_comando_no_confunde_salida_de_consola_con_entrega_real(self):
        with self.assertRaisesMessage(
            CommandError,
            'el backend de consola no entrega correos reales',
        ):
            call_command(
                'verificar_correo_reservas',
                enviar=True,
                destinatario='luis.alpala@upec.edu.ec',
            )

    def test_comando_simula_recordatorios_sin_guardar_cambios(self):
        pendiente = self.reserva(
            estado='pendiente',
            fecha=timezone.localdate() - timedelta(days=1),
        )
        salida = StringIO()

        call_command('procesar_recordatorios_reservas', simular=True, stdout=salida)

        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, 'pendiente')
        self.assertIn('SIMULACIÓN (sin cambios)', salida.getvalue())

    def test_comando_limita_por_slug_y_rechaza_unidad_inexistente(self):
        salida = StringIO()
        with patch(
            'apps.reservas.management.commands.procesar_recordatorios_reservas.'
            'procesar_recordatorios_reservas',
            return_value={'vencidas': 0},
        ) as procesar:
            call_command(
                'procesar_recordatorios_reservas',
                unidad=self.unidad.slug,
                sin_correo=True,
                stdout=salida,
            )
        procesar.assert_called_once_with(enviar_email=False, unidad=self.unidad)
        with self.assertRaisesMessage(CommandError, 'No existe una unidad'):
            call_command(
                'procesar_recordatorios_reservas',
                unidad='unidad-inexistente',
                stdout=StringIO(),
            )
