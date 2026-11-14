"""Cobertura y respaldo de laboratorios, sin proyectar hechos ni reinterpretar cierres."""

import io
import tempfile
from datetime import date, datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.evaluacion_cierre import medir_meta
from apps.documentos.presentation.medicion_metas import (
    cobertura_mensual_inspecciones, medir_mantenimiento_critico, medir_mantenimiento_integral,
    registrar_evidencia, registros_de_gestion,
)
from apps.gestion_unidades.presentation.reportes_condiciones import reporte_equipamiento, tablas_condiciones
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class CondicionesLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='condiciones-lab-responsable')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio QA condiciones', slug='qa-condiciones-lab',
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Observatorio QA condiciones', slug='qa-condiciones-observatorio',
            dependencia='observatorios', fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        ficha = EquiposServicios.objects.create(codigo='EQ-CONDICIONES-LAB', nombre='Equipo de prueba',
            caracteristicas_publicas='Voltaje 220 V; capacidad 15 litros; equipo de uso experimental.')
        cls.equipo = UnidadEquipo.objects.create(equipo=ficha, laboratorio=cls.unidad,
            codigo_unidad='UE-CONDICIONES-LAB', criticidad='critico')

    def setUp(self):
        self.inicio, self.fin, self.hoy = date(2026, 8, 17), date(2026, 12, 8), date(2026, 10, 17)
        self.reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)
        self.temporal = tempfile.TemporaryDirectory(prefix='citt-qa-condiciones-')
        self.addCleanup(self.temporal.cleanup)
        self.medios = override_settings(MEDIA_ROOT=self.temporal.name)
        self.medios.enable()
        self.addCleanup(self.medios.disable)

    def pdf(self, codigo):
        salida = io.BytesIO()
        canvas = Canvas(salida)
        canvas.drawString(36, 780, codigo + ' Informe de la actividad realizada con resultado y responsable verificados.')
        canvas.save()
        return SimpleUploadedFile(codigo + '.pdf', salida.getvalue(), 'application/pdf')

    def inspeccion(self, codigo, fecha, demo=False):
        with override_settings(MEDICION_SOLO_DEMO=demo):
            return registrar_evidencia(self.unidad, self.actor, dict(tipo='INSPECCION', codigo=codigo,
                fecha=fecha, titulo='Inspección QA', descripcion='Revisión realizada de condiciones del área.',
                responsable=self.actor, enlace='https://example.org/condiciones/' + codigo,
                detalle=dict(area='Área experimental', condiciones_revisadas=['equipos'], sin_hallazgos=True,
                    hallazgos='', accion_correctiva='', estado_condiciones='seguro',
                    estado_accion='no_requiere', plazo_accion='')), verificar=True)

    def instante(self, mes, dia):
        return timezone.make_aware(datetime(2026, mes, dia, 10))

    def orden(self, codigo='ORD-QA-COND', con_informe=False):
        orden = MantenimientoEquipo(codigo=codigo, unidad=self.unidad, equipo=self.equipo,
            plan=PlanMantenimientoEquipo.objects.filter(equipo=self.equipo, activo=True).first(),
            titulo='Intervención QA', estado='completado', responsable=self.actor,
            fecha_programada=self.instante(9, 1), fecha_inicio=self.instante(9, 1),
            fecha_fin=self.instante(9, 2), resultado='Equipo intervenido y comprobado.')
        if con_informe:
            orden.informe.save(codigo + '.pdf', self.pdf(codigo), save=False)
        MantenimientoEquipo.objects.bulk_create([orden])
        return orden

    def plan(self, revisar=True):
        if revisar:
            self.acta_criticidad()
        return PlanMantenimientoEquipo.objects.create(equipo=self.equipo, nombre='Plan preventivo QA',
            responsable=self.actor, fecha_inicio=date(2026, 1, 1), proxima_ejecucion=date(2026, 11, 1))

    def test_una_inspeccion_no_cubre_otro_mes_ni_demo_reemplaza_respaldo_real(self):
        self.inspeccion('INS-AGO', date(2026, 8, 20))
        self.inspeccion('INS-SEP-DEMO', date(2026, 9, 5), demo=True)
        self.inspeccion('INS-OCT', date(2026, 10, 5))
        datos = cobertura_mensual_inspecciones(self.unidad, self.inicio, self.fin)
        self.assertEqual([m['mes'] for m in datos['meses']], ['2026-08', '2026-09', '2026-10'])
        self.assertEqual((datos['exigibles'], datos['cubiertos_exigibles']), (2, 1))
        self.assertEqual(datos['meses'][1]['demostracion'], 1)
        self.assertFalse(datos['meses'][1]['cumple'])
        medida = registros_de_gestion(self.unidad, self.inicio, self.fin)['mediciones_porcentuales']['INSPECCIONES']
        self.assertEqual((medida['numerador'], medida['denominador']), (1, 2))
        self.assertIn('2026-09', medida['motivo'])

    def test_mes_actual_provisional_no_se_presenta_como_mes_vencido(self):
        datos = cobertura_mensual_inspecciones(self.unidad, self.inicio, self.fin)
        self.assertEqual(datos['vencidos_sin_revision'], 2)
        self.assertTrue(datos['meses'][-1]['dentro_plazo'])
        self.assertFalse(datos['meses'][-1]['exigible'])
        medida = registros_de_gestion(self.unidad, date(2026, 10, 1), self.fin)['mediciones_porcentuales']['INSPECCIONES']
        self.assertEqual(medida['denominador'], 0)
        self.assertTrue(medida['pendiente'])
        self.assertEqual(medir_meta(dict(codigo='INSPECCIONES', nombre='Inspecciones', meta='100 %'),
            {'mediciones_porcentuales': {'INSPECCIONES': medida}})['porcentaje'], 0)

    def test_al_cerrar_periodo_el_ultimo_mes_se_vuelve_exigible(self):
        with patch('django.utils.timezone.localdate', return_value=self.fin):
            datos = cobertura_mensual_inspecciones(self.unidad, self.inicio, self.fin)
        self.assertEqual(datos['exigibles'], 5)
        self.assertTrue(datos['meses'][-1]['exigible'])

    def test_no_exige_inspecciones_antes_del_inicio_de_actividad_del_laboratorio(self):
        self.unidad.fecha_inicio = date(2026, 9, 15)
        datos = cobertura_mensual_inspecciones(self.unidad, self.inicio, self.fin)
        self.assertEqual([m['mes'] for m in datos['meses']], ['2026-09', '2026-10'])

    def test_disponibilidad_usa_solo_dias_hasta_el_corte_efectivo(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(estado_unidad='dañado')
        EventoCicloVidaEquipo.objects.create(equipo=self.equipo, unidad=self.unidad, tipo='cambio_estado',
            fecha=self.instante(10, 16), estado_anterior='disponible', estado_nuevo='dañado', descripcion='Falla QA')
        _, futuras, tarjetas, _ = reporte_equipamiento(self.unidad, self.inicio, self.fin)
        _, actuales, _, _ = reporte_equipamiento(self.unidad, self.inicio, self.hoy)
        self.assertEqual(futuras, actuales)
        self.assertIn('17/10/2026', str(tarjetas))

    def test_inventario_distingue_texto_tecnico_de_una_ficha_formal_adjunta(self):
        tablas = tablas_condiciones('recursos', self.unidad, self.inicio, self.fin)
        self.assertIn('Características técnicas en texto; sin ficha formal adjunta', str(tablas))
        self.assertNotIn('Sin ficha ni especificaciones', str(tablas))

    def test_alterar_acta_integral_verificada_invalida_la_lectura_actual(self):
        e = registrar_evidencia(self.unidad, self.actor, dict(tipo='INVENTARIO', codigo='ACTA-COND',
            fecha=self.hoy, titulo='Acta de revisión integral', descripcion='Comprobación de los cuatro componentes.',
            responsable=self.actor, alcance=['equipos', 'software', 'espacios', 'insumos'],
            enlace='https://example.org/condiciones/acta'), verificar=True)
        self.assertEqual(registros_de_gestion(self.unidad, self.inicio, self.fin)['inventarios_verificados'], 1)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(titulo='Alcance cambiado después de verificar')
        self.assertEqual(registros_de_gestion(self.unidad, self.inicio, self.fin)['inventarios_verificados'], 0)

    def test_desecho_heredado_sin_licencia_o_archivo_no_acredita(self):
        d = RegistroDesecho.objects.create(unidad=self.unidad, nombre='Solvente QA', clase='peligroso',
            fecha_generacion=self.inicio, etapa='entregado', fecha_entrega=date(2026, 9, 1),
            cantidad=1, clave_listado='QA-01', origen='Proceso QA', envase='Bidón', etiquetado=True,
            gestor_autorizado='Gestor declarado QA', manifiesto='MAN-QA', responsable=self.actor)
        registrar_evidencia(self.unidad, self.actor, dict(tipo='DESECHOS', codigo='ACTA-DES-COND',
            fecha=self.hoy, titulo='Conciliación de desechos', descripcion='Partidas cotejadas contra acta independiente.',
            responsable=self.actor, desde=self.inicio, hasta=self.hoy, total_observado=1,
            enlace='https://example.org/condiciones/desechos'), verificar=True)
        def lectura():
            return registros_de_gestion(self.unidad, self.inicio, self.fin)['mediciones_porcentuales']['DESECHOS']
        self.assertEqual(lectura()['numerador'], 0)
        d.licencia_gestor = 'LIC-QA'
        d.documento.save('manifiesto.pdf', self.pdf('MANIFIESTO-QA'), save=False)
        d.save()
        self.assertEqual(lectura()['numerador'], 1)

    def test_plan_critico_sin_universo_o_sin_programacion_no_acredita_porcentaje(self):
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertTrue(medida['pendiente'])
        self.assertEqual(medida['equipos_sin_plan'], 1)
        self.plan()
        self.assertTrue(medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)['pendiente'])

    def test_ejecucion_operativa_no_acredita_plan_critico_sin_informe_real(self):
        self.plan()
        self.orden()
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertFalse(medida['pendiente'])
        self.assertEqual((medida['numerador'], medida['denominador']), (0, 1))
        self.assertEqual(medida['completadas_sin_respaldo'], ['ORD-QA-COND'])

    def test_orden_anual_con_informe_real_acredita_sin_contar_ejecuciones_futuras(self):
        self.plan()
        orden = self.orden(con_informe=True)
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertEqual((medida['numerador'], medida['denominador']), (1, 1))
        MantenimientoEquipo.objects.filter(pk=orden.pk).update(fecha_fin=self.instante(11, 1))
        self.assertEqual(medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)['numerador'], 0)

    def test_observatorio_revisa_mantenimiento_sin_exigir_inspecciones_mensuales_de_laboratorio(self):
        datos = registros_de_gestion(self.otra, self.inicio, self.fin)
        self.assertNotIn('cobertura_inspecciones', datos)
        self.assertNotIn('INSPECCIONES', datos['mediciones_porcentuales'])
        self.assertIn('MANTENIMIENTO', datos['mediciones_porcentuales'])
        medida = medir_mantenimiento_integral(self.otra, self.inicio, self.fin)
        self.assertTrue(medida['pendiente'])
        self.assertFalse(medida['no_aplica_verificado'])

    def acta_criticidad(self, codigo='ACTA-CRITICIDAD-COND', con_archivo=True):
        datos = dict(tipo='INVENTARIO', codigo=codigo, fecha=self.hoy,
            titulo='Acta integral con revisión de criticidad', descripcion='Inventario y criticidad contrastados con acta.',
            responsable=self.actor, alcance=['equipos', 'software', 'espacios', 'insumos'],
            detalle={'revision_criticidad': True})
        if not con_archivo:
            datos['enlace'] = 'https://example.org/condiciones/' + codigo
        return registrar_evidencia(self.unidad, self.actor, datos, verificar=True,
            archivo=self.pdf(codigo) if con_archivo else None)

    def test_cero_criticos_exige_revision_real_con_archivo_y_universo_vigente(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(criticidad='normal')
        self.acta_criticidad(con_archivo=False)
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertFalse(medida['no_aplica_verificado'])
        acta = self.acta_criticidad('ACTA-CRITICIDAD-ARCHIVO')
        self.assertEqual(acta.detalle['equipos_criticidad'][0]['equipo'], self.equipo.pk)
        self.assertEqual(acta.detalle['revision_criticidad_en'], self.hoy.isoformat())
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertTrue(medida['no_aplica_verificado'])
        self.assertFalse(medida['pendiente'])
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(ubicacion_especifica='Nueva instalación')
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertFalse(medida['no_aplica_verificado'])
        self.assertTrue(medida['pendiente'])

    def test_revision_criticidad_de_demostracion_no_define_universo_real(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(criticidad='normal')
        with override_settings(MEDICION_SOLO_DEMO=True):
            self.acta_criticidad()
        self.assertFalse(medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)['no_aplica_verificado'])

    def test_programacion_critica_futura_esta_en_plazo_y_no_es_una_exencion(self):
        self.plan()
        orden = self.orden()
        MantenimientoEquipo.objects.filter(pk=orden.pk).update(estado='programado', fecha_inicio=None, fecha_fin=None,
            fecha_programada=self.instante(11, 1))
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertEqual((medida['numerador'], medida['denominador']), (0, 0))
        self.assertEqual(medida['programadas_futuras'], 1)
        self.assertTrue(medida['pendiente'])
        self.assertFalse(medida['no_aplica_verificado'])
        self.assertIn('dentro de plazo', medida['motivo'])

    def test_inventario_integral_muestra_existencias_de_reactivos_e_insumos(self):
        Consumible.objects.create(unidad=self.unidad, codigo='MAT-COND-INTEGRAL', nombre='Resina QA integral',
            clasificacion='insumo', unidad_medida='l', stock_total=2)
        tablas = tablas_condiciones('recursos', self.unidad, self.inicio, self.fin)
        self.assertIn('Resina QA integral', str(tablas))
        self.assertIn('Existencias actuales de reactivos e insumos', str(tablas))

    def test_programa_critico_de_equipos_no_oculta_alcance_de_infraestructura_desconocido(self):
        self.plan()
        self.orden(con_informe=True)
        medida = medir_mantenimiento_integral(self.unidad, self.inicio, self.fin)
        self.assertEqual((medida['numerador'], medida['denominador']), (1, 1))
        self.assertTrue(medida['pendiente'])
        self.assertFalse(medida['infraestructura']['universo_conocido'])
        self.assertTrue(any(f.get('tipo') == 'MANTENIMIENTO-EQUIPO' and f.get('sha256') for f in medida['fuentes']))

    def test_un_equipo_critico_identificado_no_acredita_revision_del_universo_completo(self):
        self.plan(revisar=False)
        self.orden(con_informe=True)
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertEqual(medida['numerador'], 1)
        self.assertFalse(medida['universo_conocido'])
        self.assertTrue(medida['pendiente'])
        self.assertIn('todos los equipos', medida['motivo'])

    def test_orden_sin_plan_o_con_plan_ajeno_no_acredita_el_programa_critico(self):
        self.plan()
        orden = self.orden(con_informe=True)
        MantenimientoEquipo.objects.filter(pk=orden.pk).update(plan=None)
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertEqual(medida['numerador'], 0)
        self.assertIn('plan activo', str(medida['ordenes_no_acreditables']))
        equipo = UnidadEquipo.objects.create(equipo=self.equipo.equipo, laboratorio=self.otra,
            codigo_unidad='UE-CONDICIONES-OTRA')
        ajeno = PlanMantenimientoEquipo.objects.create(equipo=equipo, nombre='Plan de otro equipo',
            responsable=self.actor, proxima_ejecucion=self.hoy)
        MantenimientoEquipo.objects.filter(pk=orden.pk).update(plan=ajeno)
        self.assertEqual(medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)['numerador'], 0)

    def test_orden_con_responsable_no_vinculado_no_acredita_a_esta_unidad(self):
        self.plan()
        orden = self.orden(con_informe=True)
        ajeno = get_user_model().objects.create_user(username='tecnico-no-vinculado-condiciones')
        MantenimientoEquipo.objects.filter(pk=orden.pk).update(responsable=ajeno)
        medida = medir_mantenimiento_critico(self.unidad, self.inicio, self.fin)
        self.assertEqual(medida['numerador'], 0)
        self.assertIn('responsable vinculado', str(medida['ordenes_no_acreditables']))

    def test_promover_borrador_por_sql_no_crea_verificacion_de_inventario(self):
        evidencia = registrar_evidencia(self.unidad, self.actor, dict(tipo='INVENTARIO', codigo='BORRADOR-SQL-COND',
            fecha=self.hoy, titulo='Inventario todavía sin verificar', descripcion='Acta cargada como borrador.',
            responsable=self.actor, alcance=['equipos', 'software', 'espacios', 'insumos'],
            enlace='https://example.org/condiciones/borrador-sql'))
        EvidenciaGestionUnidad.objects.filter(pk=evidencia.pk).update(estado='validado',
            validado_por=self.actor, validado_en=timezone.now())
        self.assertEqual(registros_de_gestion(self.unidad, self.inicio, self.fin)['inventarios_verificados'], 0)

    def test_quitar_marca_demo_por_sql_no_convierte_inspeccion_en_cobertura_real(self):
        evidencia = self.inspeccion('DEMO-SQL-COND', date(2026, 9, 1), demo=True)
        EvidenciaGestionUnidad.objects.filter(pk=evidencia.pk).update(demostracion=False)
        cobertura = cobertura_mensual_inspecciones(self.unidad, self.inicio, self.fin)
        self.assertEqual(cobertura['cubiertos_exigibles'], 0)
        self.assertFalse(cobertura['meses'][1]['cumple'])

    def test_disponible_sin_prueba_no_equivale_a_funcionalidad_comprobada(self):
        _, _, tarjetas, _ = reporte_equipamiento(self.unidad, self.inicio, self.fin)
        valores = {t[0]: t[1] for t in tarjetas}
        self.assertEqual(valores['Equipos con prueba funcional del período'], '0/1')
        tablas = tablas_condiciones('equipamiento', self.unidad, self.inicio, self.fin)
        self.assertIn('Sin comprobación funcional documentada', str(tablas))

    def test_informe_equipamiento_muestra_prueba_y_hallazgos_sin_cambiar_estado(self):
        registrar_evidencia(self.unidad, self.actor, dict(tipo='FUNCIONALIDAD', codigo='FUNC-COND-QA',
            fecha=self.hoy, titulo='Comprobación de arranque QA', descripcion='Se comprobó una falla de arranque.',
            responsable=self.actor, detalle=dict(equipo_id=self.equipo.pk,
                procedimiento='Secuencia de arranque y parada de emergencia.', criterio='Arranca sin alarma.',
                resultado_funcional='no_operativo', hallazgos_funcionales='Alarma persistente durante arranque.')),
            verificar=True, archivo=self.pdf('FUNC-COND-QA'))
        _, _, tarjetas, _ = reporte_equipamiento(self.unidad, self.inicio, self.fin)
        valores = {t[0]: t[1] for t in tarjetas}
        self.assertEqual(valores['Equipos con prueba funcional del período'], '1/1')
        self.assertIn('1 no operativos', valores['Resultado de las pruebas funcionales'])
        tablas = tablas_condiciones('equipamiento', self.unidad, self.inicio, self.fin)
        self.assertIn('Alarma persistente', str(tablas))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'disponible')
