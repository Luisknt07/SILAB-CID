"""Mantenimiento atribuible en las cuatro bases, sin completar banderas heredadas."""
import io
from datetime import date, datetime
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.funcionalidad_laboratorios import funcionalidad_documentada
from apps.documentos.presentation.medicion_metas import (
    medir_mantenimiento_integral, registrar_evidencia, registros_de_gestion,
)
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.presentation.reportes_condiciones import (
    acciones_condiciones, documentos_condiciones, reporte_equipamiento, tablas_condiciones,
)
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import MantenimientoEquipo, PlanMantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class MantenimientoPerfilesAuditablesTests(TestCase):
    bases = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')

    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('responsable-mantenimiento-cuatro-qa')
        ficha = EquiposServicios.objects.create(codigo='MANT-CUATRO-QA', nombre='Estación de trabajo QA',
            caracteristicas_publicas='Computador de análisis y adquisición de datos para pruebas QA.')
        cls.unidades, cls.equipos = {}, {}
        for indice, base in enumerate(cls.bases):
            unidad = Unidad.objects.create(nombre='Unidad QA ' + base, slug='mant-cuatro-' + base.replace('_', '-'),
                dependencia=base, administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
            cls.unidades[base] = unidad
            cls.equipos[base] = UnidadEquipo.objects.create(equipo=ficha, laboratorio=unidad,
                codigo_unidad=f'MANT-CUATRO-{indice}', criticidad='critico')

    def setUp(self):
        self.inicio, self.fin, self.hoy = date(2026, 8, 17), date(2026, 12, 8), date(2026, 10, 17)
        temporal = TemporaryDirectory(prefix='citt-qa-mantenimiento-perfiles-')
        self.addCleanup(temporal.cleanup)
        medios = override_settings(MEDIA_ROOT=temporal.name)
        medios.enable()
        self.addCleanup(medios.disable)
        reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        reloj.start()
        self.addCleanup(reloj.stop)

    def archivo(self, codigo):
        salida = io.BytesIO()
        pdf = Canvas(salida)
        pdf.drawString(36, 780, codigo + ': informe QA con alcance revisado, responsable y resultado comprobados.')
        pdf.save()
        return SimpleUploadedFile(codigo + '.pdf', salida.getvalue(), 'application/pdf')

    def acta(self, base, codigo=None, *, verificar=True, archivo=True):
        codigo = codigo or 'ACTA-' + base
        alcance = ['equipos', 'software', 'espacios']
        if base != 'observatorios':
            alcance.append('insumos')
        datos = dict(tipo='INVENTARIO', codigo=codigo, fecha=self.hoy,
            titulo='Revisión de inventario y criticidad ' + base,
            descripcion='Inventario contrastado con los recursos, ubicaciones y responsables de la unidad QA.',
            responsable=self.actor, alcance=alcance, detalle={'revision_criticidad': True})
        if not archivo:
            datos['enlace'] = 'https://example.org/acta/' + codigo
        return registrar_evidencia(self.unidades[base], self.actor, datos, verificar=verificar,
            archivo=self.archivo(codigo) if archivo else None)

    def alcance_infra(self, base, codigo=None, *, verificar=True):
        codigo = codigo or 'ALCANCE-' + base
        return registrar_evidencia(self.unidades[base], self.actor, dict(tipo='PLAN-INFRA', codigo=codigo,
            fecha=self.hoy, titulo='Alcance documentado de infraestructura ' + base,
            descripcion='Revisión del ámbito propio de esta unidad y responsabilidad de mantenimiento.',
            responsable=self.actor, detalle=dict(alcance_infraestructura='no_aplica',
                justificacion_alcance='Sin intervenciones críticas bajo responsabilidad de la unidad en el año; '
                    'la instalación se mantiene por el servicio central según el acta adjunta.')),
            verificar=verificar, archivo=self.archivo(codigo))

    def orden(self, base, codigo, *, informe=True, actor=None, estado='completado'):
        codigo = codigo.replace(base, {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
            'centro_experimental': 'CE', 'observatorios': 'OBS'}[base])
        equipo, unidad = self.equipos[base], self.unidades[base]
        plan = PlanMantenimientoEquipo.objects.filter(equipo=equipo).first()
        if not plan:
            plan = PlanMantenimientoEquipo.objects.create(equipo=equipo, nombre='Plan anual informático QA',
                fecha_inicio=date(2026, 1, 1), proxima_ejecucion=date(2026, 12, 1), responsable=self.actor)
        instante = timezone.make_aware(datetime(2026, 9, 10, 10))
        orden = MantenimientoEquipo(unidad=unidad, equipo=equipo, plan=plan, codigo=codigo,
            titulo='Intervención documentada QA', estado=estado, responsable=actor or self.actor,
            fecha_programada=instante, fecha_inicio=instante, fecha_fin=instante,
            resultado='Limpieza, actualización y prueba de arranque correctas.')
        if informe:
            orden.informe.save(codigo + '.pdf', self.archivo(codigo), save=False)
        # Una importación histórica puede traer la bandera de completado. La
        # lectura debe exigir sus fuentes igualmente, sin fabricar aprobaciones.
        MantenimientoEquipo.objects.bulk_create([orden])
        return orden

    def lectura(self, base):
        return medir_mantenimiento_integral(self.unidades[base], self.inicio, self.fin)

    def test_cuatro_bases_sin_fuentes_quedan_pendientes_y_no_exentas(self):
        for base in self.bases:
            with self.subTest(base=base):
                medida = self.lectura(base)
                self.assertTrue(medida['pendiente'])
                self.assertFalse(medida['no_aplica_verificado'])
                self.assertEqual((medida['numerador'], medida['denominador']), (0, 0))
                self.assertIn('MANTENIMIENTO', registros_de_gestion(
                    self.unidades[base], self.inicio, self.fin)['mediciones_porcentuales'])

    def test_perfil_no_auditable_conserva_su_alcance(self):
        self.assertIsNone(medir_mantenimiento_integral(
            SimpleNamespace(dependencia='sin_perfil_auditable'), self.inicio, self.fin))

    def test_todas_miden_parcial_sin_acreditar_bandera_completada_sin_informe(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.acta(base)
                self.alcance_infra(base)
                self.orden(base, 'RESPALDADA-' + base)
                legada = self.orden(base, 'LEGADA-' + base, informe=False)
                medida = self.lectura(base)
                self.assertFalse(medida['pendiente'])
                self.assertEqual((medida['numerador'], medida['denominador']), (1, 2))
                self.assertEqual(medida['equipos']['completadas_sin_respaldo'], [legada.codigo])

    def test_cero_criticos_solo_exento_con_acta_y_alcance_verificados_en_todas(self):
        for base in self.bases:
            with self.subTest(base=base):
                UnidadEquipo.objects.filter(pk=self.equipos[base].pk).update(criticidad='normal')
                self.acta(base)
                self.assertFalse(self.lectura(base)['no_aplica_verificado'])
                self.alcance_infra(base)
                medida = self.lectura(base)
                self.assertTrue(medida['no_aplica_verificado'])
                self.assertFalse(medida['pendiente'])
                self.assertEqual((medida['numerador'], medida['denominador']), (0, 0))

    def test_inventario_sin_archivo_no_declara_conocido_el_universo_critico(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.acta(base, archivo=False)
                self.alcance_infra(base)
                self.orden(base, 'SIN-ACTA-FISICA-' + base)
                self.assertTrue(self.lectura(base)['pendiente'])
                self.assertFalse(self.lectura(base)['equipos']['universo_conocido'])

    def test_promover_acta_por_sql_no_sustituye_verificacion_atribuida(self):
        for base in self.bases:
            with self.subTest(base=base):
                acta = self.acta(base, verificar=False)
                EvidenciaGestionUnidad.objects.filter(pk=acta.pk).update(estado='validado',
                    validado_por=self.actor, validado_en=timezone.now())
                self.assertFalse(self.lectura(base)['equipos']['universo_conocido'])

    def test_alterar_inventario_invalida_revision_previa_en_todas_las_bases(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.acta(base)
                self.assertTrue(self.lectura(base)['equipos']['universo_conocido'])
                UnidadEquipo.objects.filter(pk=self.equipos[base].pk).update(ubicacion_especifica='Otra sala QA')
                self.assertFalse(self.lectura(base)['equipos']['universo_conocido'])

    def test_responsable_ajeno_o_inactivo_no_acredita_orden(self):
        ajeno = get_user_model().objects.create_user('tecnico-ajeno-mantenimiento-qa')
        for base in self.bases:
            with self.subTest(base=base):
                self.acta(base)
                self.alcance_infra(base)
                self.orden(base, 'AJENA-' + base, actor=ajeno)
                self.assertEqual(self.lectura(base)['numerador'], 0)
        self.actor.is_active = False
        self.actor.save(update_fields=['is_active'])
        for base in self.bases:
            self.orden(base, 'INACTIVA-' + base)
            self.assertEqual(self.lectura(base)['numerador'], 0)

    def test_observatorio_verifica_equipo_informatico_sin_quimica(self):
        base = 'observatorios'
        self.acta(base)
        self.alcance_infra(base)
        self.orden(base, 'INFORMATICA-OBS')
        self.assertEqual((self.lectura(base)['numerador'], self.lectura(base)['denominador']), (1, 1))
        registrar_evidencia(self.unidades[base], self.actor, dict(tipo='FUNCIONALIDAD', codigo='FUNC-OBS-QA',
            fecha=self.hoy, titulo='Prueba funcional de estación de trabajo',
            descripcion='Arranque, acceso y análisis de una muestra documentada.', responsable=self.actor,
            detalle=dict(equipo_id=self.equipos[base].pk, procedimiento='Arranque y ejecución del análisis QA.',
                criterio='Sin errores y resultado de muestra reproducible.', resultado_funcional='operativo',
                hallazgos_funcionales='')), verificar=True, archivo=self.archivo('FUNC-OBS-QA'))
        funcionalidad = funcionalidad_documentada(self.unidades[base], self.inicio, self.fin)
        self.assertEqual(funcionalidad['reales'], 1)
        unidad = self.unidades[base]
        self.assertEqual(len(documentos_condiciones('equipamiento', unidad, self.inicio, self.fin)), 1)
        self.assertIn('tipo=FUNCIONALIDAD', acciones_condiciones('equipamiento', unidad, self.inicio, self.fin)[0]['url'])
        self.assertIn('Arranque y ejecución del análisis QA.', str(tablas_condiciones(
            'equipamiento', unidad, self.inicio, self.fin)))
        self.assertIn('Equipos con prueba funcional del período', str(reporte_equipamiento(
            unidad, self.inicio, self.fin)[2]))
        self.assertNotIn('químic', str(self.lectura(base)))

    def test_infraestructura_atribuida_mide_intervenciones_y_no_solo_plan_en_todas(self):
        for base in self.bases:
            with self.subTest(base=base):
                unidad = self.unidades[base]
                UnidadEquipo.objects.filter(pk=self.equipos[base].pk).update(criticidad='normal')
                self.acta(base)
                espacio = EspacioReservable.objects.create(unidad=unidad, codigo='SALA-ANALISIS-QA',
                    nombre='Sala de análisis ' + base)
                plan = registrar_evidencia(unidad, self.actor, dict(tipo='PLAN-INFRA', codigo='ANUAL-' + base,
                    fecha=date(2026, 8, 17), titulo='Programa de instalaciones de la unidad QA',
                    descripcion='Revisión de alimentación eléctrica y protección de la sala.', responsable=self.actor,
                    detalle=dict(alcance_infraestructura='aplica', alcance_todo_laboratorio=True,
                        justificacion_alcance='El archivo cubre los espacios registrados de la unidad QA.',
                        espacio_id=espacio.pk, ubicacion=espacio.nombre, intervencion='Mantenimiento eléctrico',
                        criticidad='critica', fecha_programada='2026-09-01', frecuencia_dias=30,
                        fecha_fin_programacion='2026-10-01')), verificar=True, archivo=self.archivo('ANUAL-' + base))
                registrar_evidencia(unidad, self.actor, dict(tipo='EJECUCION-INFRA', codigo='REALIZADA-' + base,
                    fecha=date(2026, 9, 2), titulo='Informe de intervención de instalaciones QA',
                    descripcion='Trabajo realizado y comprobación de protección y alimentación.', responsable=self.actor,
                    detalle=dict(plan_id=plan.pk, fecha_programada='2026-09-01', fecha_inicio='2026-09-01',
                        fecha_fin='2026-09-02', resultado='Alimentación y protecciones comprobadas sin hallazgos.')),
                    verificar=True, archivo=self.archivo('REALIZADA-' + base))
                medida = self.lectura(base)
                self.assertFalse(medida['pendiente'])
                self.assertFalse(medida['no_aplica_verificado'])
                self.assertEqual((medida['numerador'], medida['denominador']), (1, 2))
                self.assertTrue(any(f.get('tipo') == 'EJECUCION-INFRA' for f in medida['fuentes']))
                self.assertIn('Medición del programa anual crítico al corte efectivo', str(
                    tablas_condiciones('mantenimiento', unidad, self.inicio, self.fin)))
                self.assertEqual(len(documentos_condiciones('mantenimiento', unidad, self.inicio, self.fin)), 2)
                self.assertEqual(len(acciones_condiciones('mantenimiento', unidad, self.inicio, self.fin)), 2)

    def test_infraestructura_exige_cubrir_cada_espacio_y_rechaza_unidad_ajena(self):
        for base in self.bases:
            with self.subTest(base=base):
                unidad = self.unidades[base]
                espacio = EspacioReservable.objects.create(unidad=unidad, codigo='SALA-CUBIERTA-QA',
                    nombre='Sala cubierta ' + base)
                EspacioReservable.objects.create(unidad=unidad, codigo='SALA-SIN-PLAN-QA', nombre='Sala sin plan ' + base)
                plan = dict(tipo='PLAN-INFRA', codigo='PARCIAL-' + base, fecha=date(2026, 9, 1),
                    titulo='Plan de la instalación de sala QA', descripcion='Intervención de una sala específica.',
                    responsable=self.actor, detalle=dict(alcance_infraestructura='aplica', espacio_id=espacio.pk,
                        ubicacion=espacio.nombre, intervencion='Revisión eléctrica', criticidad='critica',
                        fecha_programada='2026-09-10', frecuencia_dias=0))
                registrar_evidencia(unidad, self.actor, plan, verificar=True, archivo=self.archivo('PARCIAL-' + base))
                medida = self.lectura(base)
                self.assertTrue(medida['pendiente'])
                self.assertEqual(len(medida['infraestructura']['espacios_sin_cobertura']), 1)
                ajena = self.unidades['laboratorios' if base != 'laboratorios' else 'observatorios']
                with self.assertRaises(ValidationError):
                    registrar_evidencia(ajena, self.actor, dict(plan, codigo='AJENO-' + base),
                        verificar=True, archivo=self.archivo('AJENO-' + base))
