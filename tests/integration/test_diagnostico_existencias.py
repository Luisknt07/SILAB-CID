"""El diagnóstico diferencia activos, licencias, existencias y piezas de referencia."""
from collections import defaultdict
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.diagnostico_compras import _propuestas_equipo
from apps.documentos.presentation.diagnostico_existencias import inventario_por_clase
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios, PiezaEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


class NombrePropuestaTests(SimpleTestCase):
    def test_reposicion_identifica_bien_sin_prefijo_motivo_o_codigo(self):
        equipo = SimpleNamespace(pk=1, codigo_unidad='LAB-IMP-001', equipo=SimpleNamespace(nombre='Impresora 3D'),
            fecha_baja=None, activa=True, estado_unidad='obsoleto', criticidad='normal', valor_referencial=None)
        propuesta = _propuestas_equipo(equipo,
            dict(areas_ids=[], desgaste=dict(limite_horas=None, horas_documentadas=0)), {}, date(2026, 10, 20))[0]
        self.assertEqual(propuesta['item'], 'Impresora 3D')
        self.assertEqual(propuesta['codigo_equipo'], 'LAB-IMP-001')
        self.assertEqual(propuesta['clase_bien'], 'equipos')
        self.assertTrue(propuesta['motivo'])


class ExistenciasDiagnosticoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        actor = get_user_model().objects.create_user('existencias-pac-autor')
        cls.unidad = Unidad.objects.create(nombre='Unidad existencias', slug='unidad-existencias-pac',
            dependencia='laboratorios', administrador=actor, fecha_inicio=date(2024, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad existencias', slug='otra-existencias-pac',
            dependencia='laboratorios', administrador=actor, fecha_inicio=date(2024, 1, 1))
        cls.modelo = EquiposServicios.objects.create(codigo='MOD-PAC-EX', nombre='Equipo de prueba')
        cls.equipo1 = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='PAC-EX-01')
        cls.equipo2 = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='PAC-EX-02')

    def lectura(self):
        return {grupo['clave']: grupo for grupo in inventario_por_clase(self.unidad,
            [self.equipo1, self.equipo2], defaultdict(set, {self.equipo1.pk: {1}, self.equipo2.pk: {2}}),
            {}, {}, {1: 'Área uno', 2: 'Área dos'})}

    def test_existencias_conservan_clase_nombre_cantidad_y_medida_sin_sumarlas(self):
        for sufijo, clase, nombre, cantidad, medida in (
                ('R', 'reactivo', 'Etanol', '2.500', 'litro'),
                ('M', 'material', 'Puntas de pipeta', '3', 'caja de 100'),
                ('I', 'insumo', 'Filamento PLA', '7', 'kilogramo')):
            Consumible.objects.create(unidad=self.unidad, codigo='EX-PAC-' + sufijo, nombre=nombre,
                clasificacion=clase, stock_total=cantidad, unidad_medida=medida)
        Consumible.objects.create(unidad=self.otra, codigo='EX-PAC-AJENO', nombre='Recurso ajeno', stock_total='20')
        lectura = self.lectura()
        self.assertEqual([(lectura[c]['filas'][0]['nombre'], lectura[c]['filas'][0]['unidad_medida'])
            for c in ('reactivos', 'materiales', 'insumos')],
            [('Etanol', 'litro'), ('Puntas de pipeta', 'caja de 100'), ('Filamento PLA', 'kilogramo')])
        self.assertEqual(lectura['reactivos']['filas'][0]['cantidad'], '2.500')
        self.assertNotIn('Recurso ajeno', str(lectura))
        self.assertNotIn('cantidad_total', lectura['insumos'])

    def test_licencias_no_multiplican_sus_totales_por_equipos_o_areas(self):
        licencia = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Licencia CAD', tipo_recurso='licencia',
            tipo_acceso='red', licencias_totales=12, licencias_disponibles=8)
        programa = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Programa libre', tipo_recurso='software',
            licencias_totales=99, licencias_disponibles=99)
        licencia.equipos_instalados.add(self.equipo1, self.equipo2)
        programa.equipos_instalados.add(self.equipo1, self.equipo2)
        filas = {f['nombre']: f for f in self.lectura()['software']['filas']}
        self.assertEqual((filas['Licencia CAD']['cantidad'], filas['Licencia CAD']['licencias_disponibles']), ('12', 8))
        self.assertEqual(filas['Licencia CAD']['areas_ids'], [1, 2])
        self.assertEqual(filas['Programa libre']['cantidad'], '2')
        self.assertIsNone(filas['Programa libre']['licencias_totales'])
        self.assertIn('instalación', filas['Programa libre']['unidad_medida'])

    def test_piezas_son_cantidades_por_modelo_sin_inventar_stock_o_compras(self):
        PiezaEquipo.objects.create(equipo=self.modelo, nombre='Boquilla de impresión', cantidad=2, repuesto_disponible=True)
        grupo = self.lectura()['repuestos']
        self.assertEqual(grupo['registros'], 1)
        pieza = grupo['filas'][0]
        self.assertTrue(pieza['es_referencia'])
        self.assertEqual(pieza['cantidad'], '2')
        self.assertEqual(pieza['unidad_medida'], 'por equipo del modelo')
        self.assertIn('confirmar existencias', pieza['detalle'])
        self.assertEqual(self.lectura()['equipos']['registros'], 2)
