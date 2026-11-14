from django.core.exceptions import ValidationError

from apps.plantas_piloto.operacion.presentation.calidad import plan_haccp
from apps.plantas_piloto.operacion.presentation.diagramas import controles, diagrama_flujo
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, Receta
from tests.integration.test_produccion_planta import BasePlantaProduce


class PuntosDeControlTests(BasePlantaProduce):
    """Codex CXC 1-1969: PCC para inocuidad; lo que controla calidad o proceso es un PC."""

    def test_una_etapa_es_pcc_o_pc_no_ambas(self):
        etapa = self.receta_queso.etapas.order_by('orden').first()
        etapa.punto_critico = etapa.punto_control = True
        with self.assertRaises(ValidationError) as error:
            etapa.full_clean()
        self.assertIn('punto_control', error.exception.message_dict)

    def test_la_siembra_ya_trae_la_clasificacion_revisada(self):
        recepcion, pasteurizacion = self.receta_queso.etapas.order_by('orden')[:2]
        self.assertTrue(recepcion.punto_control)
        self.assertTrue(pasteurizacion.punto_critico)
        mantequilla = Receta.objects.get(codigo='LAC-REC-MANTEQUILLA-20').etapas.get(orden=1)
        self.assertTrue(mantequilla.punto_critico)
        self.assertIn('Fosfatasa', mantequilla.parametro)
        # Todos los procesos de la planta conservan al menos un PCC.
        for receta in Receta.objects.filter(unidad=self.unidad):
            self.assertTrue(receta.etapas.filter(punto_critico=True).exists(), receta.codigo)

    def test_los_diagramas_numeran_aparte_pcc_y_pc(self):
        datos = datos_de_receta(self.receta_queso)
        marcas = controles(datos['etapas'])
        self.assertEqual(marcas[1][0], 'PC-1')
        self.assertEqual(marcas[2][0], 'PCC-1')
        self.assertNotEqual(marcas[1][1], marcas[2][1])
        svg = diagrama_flujo(datos).svg()
        self.assertIn('punto crítico (inocuidad)', svg)
        self.assertIn('punto de control (calidad)', svg)

    def test_el_plan_haccp_no_incluye_los_pc(self):
        filas = [fila['etapa'] for item in plan_haccp(self.unidad, [self.receta_queso]) for fila in item['filas']]
        self.assertTrue(filas)
        self.assertTrue(all(etapa.punto_critico and not etapa.punto_control for etapa in filas))
        self.assertFalse(EtapaReceta.objects.filter(pk__in=[e.pk for e in filas], punto_control=True).exists())
