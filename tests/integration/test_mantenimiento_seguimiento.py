"""Seguimiento riguroso del mantenimiento: semáforo, plan, vida útil y baja.

El panel responde lo que pregunta la auditoría: qué equipo está al día y cuál
no, cada cuánto le toca, qué se hizo y qué falta, cuánto costó con repuestos,
cuánta vida útil le queda y qué pasó con los que se dieron de baja.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.recursos.presentation.mantenimiento_panel import agenda_de_mantenimiento, filas_de_equipos, historial_equipo, panel_mantenimiento, series_por_mes
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class BaseDeMantenimiento(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.hoy = date(2026, 9, 22)
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-mantenimiento', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de mantenimiento', slug='laboratorio-mantenimiento', dependencia='laboratorios',
            descripcion='Laboratorio de prueba.', fecha_inicio=date(2024, 1, 1), administrador=cls.coordinador)
        cls.equipos = {}
        for codigo, nombre, criticidad, vida, adquirido in (
            ('LAB-IMP-01', 'Impresora 3D', 'critico', 8, date(2019, 3, 1)),
            ('LAB-CNC-01', 'Fresadora CNC', 'critico', 12, date(2024, 2, 1)),
            ('LAB-SCAN-01', 'Escáner 3D', 'normal', 6, date(2021, 8, 15)),
            ('LAB-RES-01', 'Impresora de resina', 'normal', 6, date(2017, 6, 1)),
        ):
            servicio = EquiposServicios.objects.create(codigo=codigo, nombre=nombre)
            cls.equipos[codigo] = UnidadEquipo.objects.create(
                codigo_unidad=codigo, equipo=servicio, laboratorio=cls.unidad, estado_unidad='disponible',
                criticidad=criticidad, vida_util_anios=vida, fecha_adquisicion=adquirido, valor_referencial=1000)

    def fila(self, filas, codigo):
        return next(f for f in filas if f['equipo'].codigo_unidad == codigo)


class SemaforoDeEquiposTests(BaseDeMantenimiento):
    def test_el_plan_vencido_y_el_critico_sin_plan_piden_intervencion(self):
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipos['LAB-IMP-01'], nombre='Calibración', tipo='preventivo', frecuencia_dias=90,
            fecha_inicio=self.hoy - timedelta(days=200), proxima_ejecucion=self.hoy - timedelta(days=10))

        filas = filas_de_equipos(self.unidad, self.hoy)

        vencido = self.fila(filas, 'LAB-IMP-01')
        self.assertEqual(vencido['semaforo'], 'critico')
        self.assertIn('vencido', ' '.join(vencido['motivos']))
        # La fresadora es crítica y no tiene plan: la institución exige uno.
        sin_plan = self.fila(filas, 'LAB-CNC-01')
        self.assertEqual(sin_plan['semaforo'], 'critico')
        self.assertIn('sin plan de mantenimiento', ' '.join(sin_plan['motivos']))
        # Un equipo normal sin plan no es una falta.
        self.assertEqual(self.fila(filas, 'LAB-SCAN-01')['semaforo'], 'atencion')
        self.assertEqual(filas[0]['semaforo'], 'critico')

    def test_la_vida_util_cumplida_y_las_incidencias_piden_atencion(self):
        IncidenciaEquipo.objects.create(
            equipo=self.equipos['LAB-CNC-01'], unidad=self.unidad, titulo='Ruido en husillo', tipo='falla',
            prioridad='media', estado='abierta', descripcion='Ruido anormal.', reportada_por=self.coordinador)
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipos['LAB-CNC-01'], nombre='Inspección', tipo='inspeccion', frecuencia_dias=180,
            fecha_inicio=self.hoy, proxima_ejecucion=self.hoy + timedelta(days=120))

        filas = filas_de_equipos(self.unidad, self.hoy)

        con_incidencia = self.fila(filas, 'LAB-CNC-01')
        self.assertEqual(con_incidencia['semaforo'], 'atencion')
        self.assertEqual(con_incidencia['incidencias_abiertas'], 1)
        # La resina se adquirió en 2017 con seis años de vida útil: ya se cumplió.
        resina = self.fila(filas, 'LAB-RES-01')
        self.assertGreaterEqual(resina['vida_util'], 100)
        self.assertIn('Vida útil cumplida', ' '.join(resina['motivos']))

    def test_el_equipo_de_baja_sale_del_semaforo_operativo_y_deja_su_motivo(self):
        equipo = self.equipos['LAB-RES-01']
        equipo.fecha_baja = self.hoy - timedelta(days=30)
        equipo.motivo_baja = 'obsolescencia'
        equipo.observacion_baja = 'Acta 2026-014.'
        equipo.reemplazado_por = self.equipos['LAB-IMP-01']
        equipo.save()

        panel = panel_mantenimiento(self.unidad, self.hoy)

        self.assertEqual([f['equipo'].codigo_unidad for f in panel['bajas']], ['LAB-RES-01'])
        self.assertEqual(panel['cifras']['equipos'], 3)
        self.assertEqual(panel['cifras']['bajas'], 1)
        baja = self.fila(panel['filas'], 'LAB-RES-01')
        self.assertEqual(baja['semaforo'], 'baja')
        self.assertIn('Obsolescencia técnica', baja['motivos'][0])
        # La baja queda en el ciclo de vida del activo, con su reemplazo.
        evento = EventoCicloVidaEquipo.objects.filter(equipo=equipo, tipo='baja').first()
        self.assertIsNotNone(evento)
        self.assertIn('LAB-IMP-01', evento.descripcion)
        self.assertIn(evento, historial_equipo(equipo))


class CumplimientoYCostoTests(BaseDeMantenimiento):
    def orden(self, codigo, dias, estado='completado', costo=None):
        # La fecha de corte del informe y sus órdenes pertenecen al mismo
        # escenario. Usar el reloj real aquí hacía cambiar el resultado cada mes.
        corte = timezone.make_aware(datetime.combine(self.hoy, time(12)))
        return MantenimientoEquipo.objects.create(
            equipo=self.equipos[codigo], unidad=self.unidad, tipo='preventivo', estado=estado,
            titulo=f'Mantenimiento {codigo}',
            fecha_programada=corte - timedelta(days=dias),
            fecha_inicio=corte - timedelta(days=dias) if estado != 'programado' else None,
            fecha_fin=corte - timedelta(days=dias - 2) if estado == 'completado' else None,
            responsable=self.coordinador, costo=costo,
            resultado='Ejecutado sin novedades.' if estado == 'completado' else '')

    def test_el_costo_suma_la_orden_y_sus_repuestos(self):
        orden = self.orden('LAB-IMP-01', 40, costo=Decimal('120.00'))
        RepuestoMantenimiento.objects.create(
            mantenimiento=orden, descripcion='Boquilla 0.4 mm', cantidad=2, costo_unitario=Decimal('15.00'),
            procedencia='compra')

        fila = self.fila(filas_de_equipos(self.unidad, self.hoy), 'LAB-IMP-01')

        # Dos boquillas a 15: el repuesto cuenta por cantidad, no por unidad.
        self.assertEqual(fila['costo'], Decimal('150.00'))
        self.assertEqual(fila['completados'], 1)
        # La orden duró dos días: el equipo estuvo detenido ese tiempo.
        self.assertEqual(fila['dias_detenido'], 2)

    def test_el_cumplimiento_compara_lo_programado_con_lo_ejecutado(self):
        self.orden('LAB-IMP-01', 40, costo=Decimal('50.00'))
        self.orden('LAB-CNC-01', 20, estado='programado')
        self.orden('LAB-SCAN-01', 10, estado='en_proceso')

        panel = panel_mantenimiento(self.unidad, self.hoy)

        self.assertEqual(panel['cifras']['programados'], 3)
        self.assertEqual(panel['cifras']['completados'], 1)
        self.assertEqual(panel['cifras']['cumplimiento'], 33)
        self.assertEqual(panel['cifras']['costo'], Decimal('50.00'))

    def test_la_serie_por_mes_cubre_doce_meses_y_ubica_cada_orden_en_el_suyo(self):
        self.orden('LAB-IMP-01', 40, costo=Decimal('80.00'))

        serie = series_por_mes(self.unidad, self.hoy)

        self.assertEqual(len(serie), 12)
        self.assertEqual(serie[-1]['etiqueta'], 'Sep 26')
        con_orden = [mes for mes in serie if mes['programados']]
        self.assertEqual(len(con_orden), 1)
        self.assertEqual(sum(mes['completados'] for mes in serie), 1)
        self.assertEqual(sum(mes['costo'] for mes in serie), 80.0)

    def test_el_cumplimiento_no_incluye_ordenes_fuera_de_los_doce_meses(self):
        self.orden('LAB-IMP-01', 10, costo=Decimal('50.00'))
        self.orden('LAB-CNC-01', -40, costo=Decimal('70.00'))  # Mes posterior al corte.
        self.orden('LAB-SCAN-01', 400, costo=Decimal('90.00'))  # Antes del período.

        cifras = panel_mantenimiento(self.unidad, self.hoy)['cifras']

        self.assertEqual(cifras['programados'], 1)
        self.assertEqual(cifras['completados'], 1)
        # El costo de la serie tiene el mismo período; el de los equipos es histórico.
        self.assertEqual(sum(mes['costo'] for mes in series_por_mes(self.unidad, self.hoy)), 50.0)

    def test_la_cobertura_cuenta_solo_los_equipos_en_operacion(self):
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipos['LAB-IMP-01'], nombre='Calibración', tipo='preventivo', frecuencia_dias=90,
            fecha_inicio=self.hoy, proxima_ejecucion=self.hoy + timedelta(days=90))
        equipo = self.equipos['LAB-RES-01']
        equipo.fecha_baja = self.hoy
        equipo.motivo_baja = 'vida_util'
        equipo.observacion_baja = 'Diagnóstico técnico: vida útil agotada. Conservado para trámite patrimonial.'
        equipo.save()

        cifras = panel_mantenimiento(self.unidad, self.hoy)['cifras']

        self.assertEqual((cifras['equipos'], cifras['con_plan'], cifras['cobertura']), (3, 1, 33))
        self.assertEqual(cifras['criticos_sin_plan'], 1)


class PanelYReporteTests(BaseDeMantenimiento):
    def test_la_consola_muestra_el_semaforo_los_graficos_y_el_ciclo_de_vida(self):
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipos['LAB-IMP-01'], nombre='Calibración del extrusor', tipo='preventivo',
            frecuencia_dias=90, fecha_inicio=date(2026, 1, 1), proxima_ejecucion=date(2026, 3, 1))
        equipo = self.equipos['LAB-RES-01']
        equipo.fecha_baja = date(2026, 8, 1)
        equipo.motivo_baja = 'obsolescencia'
        equipo.observacion_baja = 'Acta 2026-014.'
        equipo.save()
        self.client.force_login(self.coordinador)

        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        self.assertContains(panel, 'Cobertura de planes')
        self.assertContains(panel, 'Cumplimiento del plan')
        self.assertContains(panel, 'Programado frente a ejecutado')
        self.assertContains(panel, 'Estado de los equipos')
        self.assertContains(panel, 'Qué le toca a cada equipo')
        self.assertContains(panel, 'Calibración del extrusor')
        self.assertContains(panel, 'cada 90 días')
        self.assertContains(panel, 'Equipos dados de baja')
        self.assertContains(panel, 'Acta 2026-014.')
        self.assertContains(panel, 'mant-semaforo is-critico')

    def test_el_reporte_de_mantenimiento_sustenta_equipo_por_equipo(self):
        orden = MantenimientoEquipo.objects.create(
            equipo=self.equipos['LAB-IMP-01'], unidad=self.unidad, tipo='preventivo', estado='completado',
            titulo='Calibración', fecha_programada=timezone.now() - timedelta(days=15),
            fecha_inicio=timezone.now() - timedelta(days=15), fecha_fin=timezone.now() - timedelta(days=14),
            responsable=self.coordinador, costo=Decimal('90.00'), resultado='Sin novedades.')
        RepuestoMantenimiento.objects.create(
            mantenimiento=orden, descripcion='Boquilla', cantidad=1, costo_unitario=Decimal('10.00'))
        peticion = RequestFactory().get('/', {'categoria_reporte': 'mantenimiento'})
        peticion.user = self.coordinador

        reporte = build_unit_report(peticion, self.unidad)

        datos = reporte['dataset']
        self.assertEqual(datos['headers'][:3], ['Equipo', 'Criticidad', 'Estado'])
        fila = next(f for f in datos['rows'] if f[0].startswith('LAB-IMP-01'))
        self.assertEqual(fila[1], 'Crítico')  # una palabra: la tabla tiene dieciséis columnas
        columna = {nombre: indice for indice, nombre in enumerate(datos['headers'])}
        self.assertEqual(fila[columna['Hechos']], '1/1')
        self.assertEqual(fila[columna['Costo USD']], '100.00')
        # Sin plan no se inventa un ejecutor ni un cronograma; la garantía se declara.
        self.assertEqual(fila[columna['Plan y frecuencia']], 'Sin plan registrado')
        self.assertEqual(fila[columna['Ejecuta']], '—')
        self.assertEqual(fila[columna['Cronograma']], '—')
        self.assertEqual(fila[columna['Garantía']], 'No registrada')
        tarjetas = {c[0]: c[1] for c in datos['cards']}
        self.assertEqual(tarjetas['Repuestos utilizados'], 1)
        self.assertEqual(tarjetas['Costo del período (USD)'], '100.00')
        self.assertEqual(tarjetas['Cobertura del plan'], '0 %')  # ningún equipo tiene plan en este caso
        # El reporte es el documento del expediente: el centro lo dice y enlaza allí.
        self.assertEqual(reporte['expediente']['nombre'],
                         'Plan anual de mantenimiento preventivo y correctivo')

    def test_el_reporte_se_filtra_por_estado_del_semaforo(self):
        peticion = RequestFactory().get('/', {'categoria_reporte': 'mantenimiento', 'estado': 'critico'})
        peticion.user = self.coordinador

        reporte = build_unit_report(peticion, self.unidad)

        estados = {fila[2] for fila in reporte['dataset']['rows']}
        self.assertEqual(estados, {'Intervención'})  # la columna se llama «Estado»
        self.assertIn(('critico', 'Requiere intervención'), reporte['choices']['states'])


class AgendaDelSeguimientoTests(BaseDeMantenimiento):
    """Lo que viene se ordena por urgencia en vez de repetir la lista de planes."""

    def plan(self, codigo, nombre, dias, **extra):
        return PlanMantenimientoEquipo.objects.create(
            equipo=self.equipos[codigo], nombre=nombre, tipo='preventivo', frecuencia_dias=30,
            fecha_inicio=self.hoy - timedelta(days=30),
            proxima_ejecucion=self.hoy + timedelta(days=dias), **extra)

    def test_la_agenda_agrupa_por_urgencia_y_respeta_el_orden(self):
        self.plan('LAB-IMP-01', 'Calibración atrasada', -5)
        self.plan('LAB-CNC-01', 'Limpieza de esta semana', 3)
        self.plan('LAB-SCAN-01', 'Revisión del mes', 20)
        self.plan('LAB-RES-01', 'Cambio de película', 90, ejecutor='externo')

        agenda = agenda_de_mantenimiento(self.unidad, self.hoy)

        self.assertEqual([grupo['clave'] for grupo in agenda],
                         ['vencido', 'semana', 'mes', 'despues'])
        self.assertEqual([grupo['tono'] for grupo in agenda],
                         ['critico', 'atencion', 'atencion', 'al_dia'])
        vencido = agenda[0]['items'][0]
        self.assertEqual(vencido['plan'].nombre, 'Calibración atrasada')
        self.assertEqual(vencido['dias'], -5)
        self.assertEqual(agenda[3]['items'][0]['plan'].get_ejecutor_display(),
                         'Técnico especializado externo o proveedor')

    def test_un_grupo_sin_planes_no_aparece(self):
        self.plan('LAB-IMP-01', 'Solo esta semana', 2)

        agenda = agenda_de_mantenimiento(self.unidad, self.hoy)

        self.assertEqual([grupo['clave'] for grupo in agenda], ['semana'])

    def test_el_plan_de_un_equipo_dado_de_baja_no_se_agenda(self):
        self.plan('LAB-IMP-01', 'Plan del retirado', 4)
        equipo = self.equipos['LAB-IMP-01']
        equipo.fecha_baja = self.hoy - timedelta(days=1)
        equipo.motivo_baja = 'obsolescencia'
        equipo.observacion_baja = 'Retiro técnico documentado: ya no presta el servicio previsto.'
        equipo.save()

        self.assertEqual(agenda_de_mantenimiento(self.unidad, self.hoy), [])

    def test_la_fila_trae_la_criticidad_en_una_palabra(self):
        filas = filas_de_equipos(self.unidad, self.hoy)

        fila = self.fila(filas, 'LAB-IMP-01')
        self.assertEqual(fila['criticidad_corta'], 'Crítico')
        # La definición completa sigue disponible para el título del chip.
        self.assertTrue(fila['criticidad'].startswith('Crítico:'))

    def test_desde_lo_que_viene_se_salta_a_esa_semana_de_la_agenda(self):
        """No hace falta otro calendario: el que ya existe muestra estos cierres."""
        self.plan('LAB-CNC-01', 'Limpieza de esta semana', 3)
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        contenido = pagina.content.decode()
        semana = (self.hoy + timedelta(days=3)).isoformat()
        self.assertIn(f'modo_reservas=agenda&amp;semana={semana}', contenido)
        self.assertIn('Ver en la agenda', contenido)

    def test_la_consola_muestra_la_agenda_y_no_repite_el_motivo_en_la_tabla(self):
        self.plan('LAB-CNC-01', 'Limpieza de esta semana', 3)
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        contenido = pagina.content.decode()
        self.assertIn('Lo que viene', contenido)
        self.assertIn('mant-agenda__lista', contenido)
        self.assertIn('mant-criticidad', contenido)
        # El motivo queda en el título del semáforo, no repetido bajo cada fila.
        self.assertIn('class="mant-semaforo is-critico" title=', contenido)


class ReporteDeIncidenciaTests(BaseDeMantenimiento):
    """Reportar una novedad se hace con opciones que se reconocen de un vistazo."""

    def abrir(self):
        self.client.force_login(self.coordinador)
        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})
        return pagina.content.decode()

    def test_el_formulario_ofrece_tipo_prioridad_y_estado_como_opciones(self):
        contenido = self.abrir()

        for campo in ('tipo', 'prioridad', 'estado'):
            self.assertIn(f'type="radio" name="{campo}"', contenido)
        self.assertIn('unit-console-operation__tarjetas', contenido)
        self.assertIn('unit-console-operation__escala', contenido)
        self.assertIn('unit-console-operation__ruta', contenido)
        # Sigue pudiendo asignarse a alguien y declarar que detiene la operación.
        self.assertIn('name="asignada_a"', contenido)
        self.assertIn('name="detiene_operacion"', contenido)

    def test_el_equipo_elegido_se_reconoce_por_su_foto_y_su_estado(self):
        contenido = self.abrir()

        self.assertIn('data-incidencia-equipo', contenido)
        self.assertIn('data-incidencia-ficha', contenido)
        equipo = self.equipos['LAB-IMP-01']
        self.assertIn(f'data-codigo="{equipo.codigo_unidad}"', contenido)
        self.assertIn(f'data-foto="{equipo.equipo.imagen_publica_url}"', contenido)

    def test_la_orden_registra_quien_la_ejecuta_y_cuanto_costo_el_servicio(self):
        self.client.force_login(self.coordinador)
        equipo = self.equipos['LAB-CNC-01']

        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'mantenimiento',
                'equipo_id': equipo.pk,
                'titulo': 'Calibración anual del husillo',
                'tipo': 'calibracion',
                'estado': 'completado',
                'ejecutor': 'externo',
                'proveedor': 'Metalmecánica de precisión',
                'costo': '250.00',
                'fecha_programada': '2026-09-02T09:00',
                'resultado': 'Certificado de calibración entregado.',
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        orden = MantenimientoEquipo.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertEqual(orden.ejecutor, 'externo')
        self.assertEqual(orden.costo, Decimal('250.00'))

    def test_una_orden_sin_costo_no_inventa_un_cero(self):
        self.client.force_login(self.coordinador)

        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'mantenimiento',
                'equipo_id': self.equipos['LAB-SCAN-01'].pk,
                'titulo': 'Limpieza del cabezal',
                'tipo': 'preventivo',
                'estado': 'programado',
                'ejecutor': 'interno',
                'fecha_programada': '2026-10-02T09:00',
            },
        )

        orden = MantenimientoEquipo.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertIsNone(orden.costo)
        self.assertEqual(orden.ejecutor, 'interno')


class MantenimientoEnElCalendarioTests(BaseDeMantenimiento):
    """Una intervención cierra las horas del equipo en la agenda de reservas."""

    def validar(self, fecha, desde, hasta, equipo):
        """La misma comprobación que hace la reserva antes de aceptar."""
        from apps.reservas.presentation.conflictos import validar_conflictos_recursos

        validar_conflictos_recursos(
            self.unidad, fecha, desde, hasta,
            [{'id': equipo.pk, 'nombre': equipo.equipo.nombre}], [], [],
            incluye_espacio=False, alcance_espacio='', tipo_solicitud='equipos',
            modalidad_servicio='', proposito_codigo='docencia_practica', numero_participantes=1)

    def orden(self, codigo='LAB-IMP-01', **extra):
        datos = dict(
            equipo=self.equipos[codigo], unidad=self.unidad, tipo='preventivo', estado='programado',
            titulo='Calibración trimestral', descripcion='Ajuste de ejes.',
            fecha_programada=timezone.make_aware(datetime(2026, 10, 6, 9, 0)), duracion_horas=3)
        datos.update(extra)
        return MantenimientoEquipo.objects.create(**datos)

    def test_la_orden_programada_reserva_el_equipo_en_el_calendario(self):
        orden = self.orden()

        bloqueo = BloqueoAgendaUnidad.objects.get(mantenimiento=orden)
        self.assertEqual(bloqueo.tipo, 'mantenimiento')
        self.assertEqual(bloqueo.alcance, 'equipos')
        self.assertEqual(list(bloqueo.equipos.all()), [self.equipos['LAB-IMP-01']])
        self.assertEqual(bloqueo.fecha_inicio, date(2026, 10, 6))
        self.assertEqual((bloqueo.hora_inicio.hour, bloqueo.hora_fin.hour), (9, 12))
        self.assertTrue(bloqueo.activo)
        self.assertIn(orden.titulo, bloqueo.titulo)

    def test_al_cambiar_la_fecha_o_la_duracion_el_cierre_la_sigue(self):
        orden = self.orden()

        orden.fecha_programada = timezone.make_aware(datetime(2026, 10, 20, 14, 0))
        orden.duracion_horas = 2
        orden.save()

        bloqueo = BloqueoAgendaUnidad.objects.get(mantenimiento=orden)
        self.assertEqual(bloqueo.fecha_inicio, date(2026, 10, 20))
        self.assertEqual((bloqueo.hora_inicio.hour, bloqueo.hora_fin.hour), (14, 16))

    def test_una_orden_cancelada_libera_la_agenda(self):
        orden = self.orden()

        orden.estado = 'cancelado'
        orden.save()

        self.assertFalse(BloqueoAgendaUnidad.objects.filter(mantenimiento=orden).exists())

    def test_quien_no_quiere_cerrar_la_agenda_puede_decirlo(self):
        orden = self.orden(bloquea_agenda=False)

        self.assertFalse(BloqueoAgendaUnidad.objects.filter(mantenimiento=orden).exists())

        orden.bloquea_agenda = True
        orden.save()

        self.assertTrue(BloqueoAgendaUnidad.objects.filter(mantenimiento=orden).exists())

    def test_el_cierre_impide_reservar_ese_equipo_a_esa_hora(self):
        orden = self.orden()
        equipo = self.equipos['LAB-IMP-01']

        with self.assertRaises(ValueError) as fallo:
            self.validar(date(2026, 10, 6), time(10, 0), time(11, 0), equipo)

        self.assertIn(orden.titulo, str(fallo.exception))

    def test_fuera_de_esa_ventana_el_equipo_sigue_disponible(self):
        self.orden()
        equipo = self.equipos['LAB-IMP-01']

        self.validar(date(2026, 10, 6), time(15, 0), time(16, 0), equipo)

    def test_el_cierre_no_alcanza_a_los_demas_equipos_de_la_unidad(self):
        self.orden()
        otro = self.equipos['LAB-CNC-01']

        self.validar(date(2026, 10, 6), time(10, 0), time(11, 0), otro)

    def test_la_consola_pide_la_duracion_y_si_toma_el_calendario(self):
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        contenido = pagina.content.decode()
        self.assertIn('name="duracion_horas"', contenido)
        self.assertIn('name="bloquea_agenda"', contenido)

    def test_la_orden_guardada_desde_la_consola_cierra_la_agenda(self):
        self.client.force_login(self.coordinador)

        respuesta = self.client.post(
            reverse('gestion_operacion_accion', args=[self.unidad.slug]),
            {
                'modulo': 'mantenimiento',
                'equipo_id': self.equipos['LAB-SCAN-01'].pk,
                'titulo': 'Verificación de precisión',
                'tipo': 'calibracion',
                'estado': 'programado',
                'ejecutor': 'externo',
                'fecha_programada': '2026-11-10T08:00',
                'duracion_horas': '4',
                'bloquea_agenda': 'true',
            },
        )

        orden = MantenimientoEquipo.objects.get(pk=respuesta.json()['registro']['id'])
        bloqueo = BloqueoAgendaUnidad.objects.get(mantenimiento=orden)
        self.assertEqual(orden.duracion_horas, 4)
        self.assertEqual((bloqueo.hora_inicio.hour, bloqueo.hora_fin.hour), (8, 12))


class SinEquiposNoAplicaTests(TestCase):
    """Una unidad sin equipos no incumple el plan: no le aplica."""

    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-sin-equipos', password='clave-segura')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio sin equipos', slug='laboratorio-sin-equipos',
            dependencia='laboratorios', descripcion='Sin inventario todavía.',
            fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)

    def test_el_panel_lo_dice_en_vez_de_dibujar_ceros(self):
        self.assertTrue(panel_mantenimiento(self.unidad)['sin_equipos'])

        self.client.force_login(self.coordinador)
        pagina = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        contenido = pagina.content.decode()
        self.assertIn('todavía no tiene equipos registrados', contenido)
        self.assertIn('no aplica', contenido)
        # Sin equipos no se dibuja el semáforo ni la tabla del parque.
        self.assertNotIn('mant-cifras', contenido)

    def test_observatorio_no_abre_mantenimiento_fuera_de_su_navegacion(self):
        observatorio = Unidad.objects.create(
            nombre='Observatorio propio', slug='observatorio-mantenimiento-no-aplica',
            dependencia='observatorios', descripcion='Indicadores sin parque de equipos.',
            fecha_inicio=date(2025, 1, 1), administrador=self.coordinador,
        )
        self.client.force_login(self.coordinador)
        with patch('apps.gestion_unidades.presentation.gestion.panel_mantenimiento',
                   side_effect=AssertionError('No cargar un módulo fuera de la navegación autorizada')):
            pagina = self.client.get(reverse('gestion_unidad', args=[observatorio.slug]),
                                     {'view': 'mantenimiento'})
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context['vista_gestion'], 'obs_indicadores')
        self.assertContains(pagina, 'data-management-view="obs_indicadores"')
        self.assertNotContains(pagina, 'data-management-view="mantenimiento"')
        self.assertNotIn('panel_mantenimiento', pagina.context)
