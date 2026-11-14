"""Capacidad efectiva y universos vacíos respaldados, sin regalar cumplimiento."""
from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.evaluacion_cierre import evaluar_meta
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN
from apps.documentos.presentation.medicion_metas import registrar_evidencia, registros_de_gestion
from apps.documentos.presentation.politica_metas_unidades import (
    actividades_proporcionales, capacidad_de, ficha_indicador,
)
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.seguridad import RegistroIngreso


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class MetasCapacidadYCerosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='metas-capacidad-cero-qa')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio capacidad QA', slug='metas-capacidad-cero',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2020, 1, 1))
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='AREA-METAS',
            nombre='Área QA de trabajo', politica_reserva='general')
        cls.ficha = EquiposServicios.objects.create(codigo='FICHA-METAS', nombre='Equipo QA')

    def setUp(self):
        self.inicio, self.fin, self.hoy = date(2026, 8, 17), date(2026, 12, 8), date(2026, 10, 17)
        reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        reloj.start()
        self.addCleanup(reloj.stop)

    def acta(self, tipo, *, total=0, desde=None, hasta=None, codigo=None, verificar=True, demo=False):
        with override_settings(MEDICION_SOLO_DEMO=demo):
            return registrar_evidencia(self.unidad, self.actor,
                dict(tipo=tipo, codigo=codigo or 'ACTA-' + tipo, titulo='Conciliación QA',
                    descripcion='Tramo contrastado con la fuente independiente y responsable identificado.',
                    fecha=self.hoy, responsable=self.actor, desde=desde or self.inicio,
                    hasta=hasta or self.hoy, total_observado=total,
                    enlace='https://example.org/metas/' + (codigo or tipo)), verificar=verificar)

    def registros(self):
        return registros_de_gestion(self.unidad, self.inicio, self.fin)

    def fila(self, codigo, registros):
        return evaluar_meta(dict(codigo=codigo, nombre=codigo, indicador=codigo, meta='100 %',
            aplica=True, obligatoria=True, institucional=True), registros)

    def reserva(self, fecha=None, *, total=None):
        detalle = {'registrada_en': '2026-10-17T09:00:00-05:00'}
        if total is not None:
            detalle['asistentes_total'] = total
        return Reserva.objects.create(laboratorio=self.unidad, usuario=self.actor, fecha=fecha or self.hoy,
            hora_inicio=time(9), hora_fin=time(10), equipo_codigo='QA', equipo_nombre='Equipo QA',
            estado='completada', resultado_cierre='atendida', detalle_ejecucion=detalle)

    def test_bienes_danados_obsoletos_y_retirados_no_elevan_capacidad_utilizable(self):
        for estado in ('disponible', 'dañado', 'obsoleto', 'no_localizado', 'no_disponible', 'mantenimiento'):
            UnidadEquipo.objects.create(equipo=self.ficha, laboratorio=self.unidad,
                codigo_unidad='CAP-' + estado, estado_unidad=estado)
        baja = UnidadEquipo.objects.create(equipo=self.ficha, laboratorio=self.unidad, codigo_unidad='CAP-BAJA')
        UnidadEquipo.objects.filter(pk=baja.pk).update(fecha_baja=date(2026, 1, 1), activa=False)
        lectura = capacidad_de(self.unidad, self.inicio, self.fin)
        self.assertEqual((lectura['equipos_registrados'], lectura['equipos_utilizables']), (7, 1))
        self.assertEqual(lectura['equipos_no_utilizables'], 5)
        self.assertEqual(lectura['nivel'], 'limitada')
        self.assertEqual(lectura['practicas_recomendadas'], 4)

    def test_software_remoto_y_personal_permiten_capacidad_sin_comprar_equipos(self):
        for numero in range(3):
            SoftwareDisponible.objects.create(unidad=self.unidad, nombre=f'Programa QA {numero}',
                tipo_acceso='remoto', licencias_disponibles=1)
        otro = get_user_model().objects.create_user(username='metas-segundo-responsable')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=otro, activo=True)
        lectura = capacidad_de(self.unidad, self.inicio, self.fin)
        self.assertEqual(lectura['software_utilizable'], 3)
        self.assertEqual(lectura['nivel'], 'consolidada')
        self.assertEqual(lectura['practicas_recomendadas'], 6)
        self.assertFalse(lectura['requiere_revision'])

    def test_software_instalado_sin_equipo_utilizable_no_infla_la_capacidad(self):
        equipo = UnidadEquipo.objects.create(equipo=self.ficha, laboratorio=self.unidad,
            codigo_unidad='CAP-SOFT-DANO', estado_unidad='dañado')
        programa = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Instalación QA')
        programa.equipos_instalados.add(equipo)
        lectura = capacidad_de(self.unidad, self.inicio, self.fin)
        self.assertEqual((lectura['software'], lectura['software_utilizable']), (1, 0))
        self.assertEqual(lectura['practicas_minimas'], 2)

    def test_apertura_tardia_propone_una_actividad_y_exige_revision_sin_borrar_funcion(self):
        self.unidad.fecha_inicio = date(2026, 11, 1)
        lectura = capacidad_de(self.unidad, self.inicio, self.fin)
        self.assertEqual(lectura['dias_efectivos'], 38)
        self.assertEqual((lectura['practicas_minimas'], lectura['practicas_recomendadas']), (1, 1))
        self.assertTrue(lectura['requiere_revision'])
        actividades = {a.codigo: a for a in actividades_proporcionales(
            ACTIVIDADES_PLAN, 'laboratorios', capacidad=lectura)}
        self.assertEqual(actividades['PRACTICAS'].minimo, '≥ 1 por período')
        self.assertFalse(actividades['PRACTICAS'].segun_programacion)

    def test_apertura_fuera_de_periodo_no_se_convierte_en_exencion(self):
        self.unidad.fecha_inicio = date(2027, 1, 1)
        lectura = capacidad_de(self.unidad, self.inicio, self.fin)
        self.assertEqual(lectura['dias_efectivos'], 0)
        self.assertEqual(lectura['practicas_minimas'], 0)
        self.assertTrue(lectura['requiere_revision'])
        actividades = {a.codigo: a for a in actividades_proporcionales(
            ACTIVIDADES_PLAN, 'laboratorios', capacidad=lectura)}
        self.assertEqual(actividades['PRACTICAS'].minimo, '≥ 2 por período')

    def test_ficha_explica_origen_formula_y_semestre_sin_inventar_cuota_universitaria(self):
        actividad = next(a for a in ACTIVIDADES_PLAN if a.codigo == 'DESECHOS')
        ficha = ficha_indicador(actividad)
        self.assertIn('no es una cuota universitaria', ficha['fuente'])
        self.assertIn('Partidas', ficha['formula'])
        self.assertIn('enero–junio o julio–diciembre', ficha['duracion'])
        self.assertIn('la docencia sigue su calendario académico', ficha['duracion'])
        self.assertIn('cero generación', ficha['evidencia'])
        self.assertEqual(ficha['titulo'], actividad.indicador)
        self.assertIn(('Cálculo', ficha['formula']), ficha['pares'])

    def test_cero_desechos_conciliado_se_excluye_sin_cien_ficticio_y_uso_sigue_cero(self):
        self.acta('DESECHOS')
        self.acta('USO')
        registros = self.registros()
        residuo = self.fila('DESECHOS', registros)
        self.assertEqual(residuo['estado'], 'No aplica')
        self.assertIsNone(residuo['porcentaje'])
        self.assertFalse(residuo['exigible'])
        uso = self.fila('USO', registros)
        self.assertEqual(uso['porcentaje'], 0)
        self.assertTrue(uso['exigible'])

    def test_sin_acta_completa_o_con_demo_cero_no_demuestra_no_aplicacion(self):
        self.assertFalse(self.fila('DESECHOS', self.registros()).get('no_aplica_verificado', False))
        self.acta('DESECHOS', desde=self.hoy, codigo='TRAMO-INCOMPLETO')
        self.assertFalse(self.fila('DESECHOS', self.registros()).get('no_aplica_verificado', False))
        self.acta('USO', codigo='USO-DEMO', demo=True)
        self.assertFalse(self.fila('SEGURIDAD', self.registros()).get('no_aplica_verificado', False))

    def test_partida_nativa_incompleta_impide_declarar_cero_generacion(self):
        self.acta('DESECHOS')
        RegistroDesecho.objects.create(unidad=self.unidad, nombre='Partida incompleta QA',
            clase='peligroso', fecha_generacion=self.hoy, cantidad=1, responsable=self.actor)
        self.assertFalse(self.fila('DESECHOS', self.registros()).get('no_aplica_verificado', False))

    def test_ausencia_nuevos_necesita_conciliacion_y_no_se_infiere_de_tabla_vacia(self):
        self.assertTrue(self.fila('SEGURIDAD', self.registros())['exigible'])
        self.acta('USO')
        seguridad = self.fila('SEGURIDAD', self.registros())
        self.assertEqual(seguridad['estado'], 'No aplica')
        self.assertIsNone(seguridad['porcentaje'])

    def test_usuarios_antiguos_con_asistencia_completa_no_cuentan_como_nuevos(self):
        anterior = self.reserva(date(2026, 8, 1), total=1)
        RegistroIngreso.objects.create(reserva=anterior, usuario=self.actor, nombre='Usuario anterior QA')
        actual = self.reserva(total=1)
        RegistroIngreso.objects.create(reserva=actual, usuario=self.actor, nombre='Usuario anterior QA')
        self.acta('USO', total=1)
        seguridad = self.fila('SEGURIDAD', self.registros())
        self.assertEqual(seguridad['estado'], 'No aplica')
        actual.detalle_ejecucion.pop('asistentes_total')
        actual.save(update_fields=['detalle_ejecucion'])
        self.assertTrue(self.fila('SEGURIDAD', self.registros())['exigible'])

    def test_ingreso_desconocido_no_se_excluye_aunque_el_acta_declare_cero(self):
        reserva = self.reserva(total=1)
        RegistroIngreso.objects.create(reserva=reserva, nombre='Identidad pendiente QA')
        self.acta('USO', total=1)
        seguridad = self.fila('SEGURIDAD', self.registros())
        self.assertTrue(seguridad['exigible'])
        self.assertEqual(seguridad['porcentaje'], 0)

    def test_unidad_nueva_concilia_solo_desde_su_apertura_real(self):
        self.unidad.fecha_inicio = date(2026, 10, 1)
        self.unidad.save(update_fields=['fecha_inicio'])
        self.acta('DESECHOS', desde=date(2026, 10, 1))
        self.acta('USO', desde=date(2026, 10, 1))
        registros = self.registros()
        for codigo in ('DESECHOS', 'SEGURIDAD'):
            self.assertFalse(self.fila(codigo, registros)['exigible'])
        self.assertEqual(registros['mediciones_porcentuales']['USO']['desde'], '2026-10-01')
