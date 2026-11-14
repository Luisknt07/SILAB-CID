"""Paso 6: ficha técnica, red de contenidos, exportación y tablero interno."""

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.gestion_unidades.presentation.completitud import tablero_unidad
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_produccion_planta import BasePlantaProduce


class PasoSeisTests(BasePlantaProduce):
    def setUp(self):
        super().setUp()
        # Una planta sin levantamiento: la ficha de cada equipo nace sin datos técnicos.
        EquiposServicios.objects.filter(unidades__laboratorio=self.unidad).update(
            origen_datos_tecnicos='', modo_operacion='', capacidad_nominal=None, unidad_capacidad='',
            capacidad_util_min=None, capacidad_util_max=None, tiempo_setup=None, tiempo_limpieza=None,
            coordenada_x=None, coordenada_y=None, mtbf=None, mttr=None,
        )

    def test_la_ficha_de_equipo_acepta_el_levantamiento_y_sube_su_completitud(self):
        unidad_equipo = UnidadEquipo.objects.filter(laboratorio=self.unidad).select_related('equipo').first()
        equipo = unidad_equipo.equipo
        antes = unidad_equipo.completitud_ficha
        equipo.modo_operacion = 'lote'
        equipo.capacidad_nominal = '100'
        equipo.unidad_capacidad = 'L/lote'
        equipo.capacidad_util_min = '40'
        equipo.capacidad_util_max = '80'
        equipo.tiempo_setup = '15'
        equipo.tiempo_limpieza = '30'
        equipo.coordenada_x = '4.2'
        equipo.coordenada_y = '7.8'
        equipo.save()
        self.assertGreater(unidad_equipo.completitud_ficha, antes)
        self.assertNotIn('capacidad_util_max', [item['campo'] for item in equipo.campos_criticos_vacios])
        self.assertNotIn('coordenada_x', [item['campo'] for item in equipo.campos_criticos_vacios])

    def test_producto_y_proceso_conservan_la_misma_ruta_contextual(self):
        urls = (
            reverse('ficha_producto_publica', args=[self.unidad.slug, self.receta_queso.producto_id]),
            reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]),
        )
        for url in urls:
            pagina = self.client.get(url)
            self.assertEqual(pagina.status_code, 200)
            self.assertContains(pagina, 'Ficha del producto')
            self.assertContains(pagina, 'Ficha del proceso')
            self.assertContains(pagina, 'Simular · Balance de materia y energía')
            self.assertContains(pagina, 'Documentación técnica · Saber y hacer')
            self.assertContains(pagina, 'Datos (CSV)')
            self.assertContains(pagina, 'Citar')

    def test_la_documentacion_explica_la_ruta_y_las_formulas(self):
        pagina = self.client.get(reverse(
            'documentacion_proceso', args=[self.unidad.slug, self.receta_queso.pk],
        ))
        self.assertContains(pagina, 'RUTA DEL SABER Y DEL HACER')
        self.assertContains(pagina, 'Comprender')
        self.assertContains(pagina, 'Calcular')
        self.assertContains(pagina, 'Acumulación = Entrada − Salida + Generación − Consumo')
        self.assertContains(pagina, 'Q = m · cₚ · ΔT')
        self.assertContains(pagina, 'Relacionado con')

    def test_exporta_los_datos_que_generan_la_ficha(self):
        respuesta = self.client.get(reverse(
            'datos_proceso_csv', args=[self.unidad.slug, self.receta_queso.pk],
        ))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'text/csv; charset=utf-8')
        texto = respuesta.content.decode('utf-8-sig')
        self.assertIn('Código;Proceso;Orden;Etapa', texto)
        self.assertIn(self.receta_queso.codigo, texto)
        self.assertIn('Recepción', texto)

    def test_documentacion_y_equipo_conservan_su_pdf_institucional(self):
        documentacion = self.client.get(
            reverse('documentacion_proceso', args=[self.unidad.slug, self.receta_queso.pk]),
            {'formato': 'pdf'},
        )
        self.assertEqual(documentacion.status_code, 200)
        self.assertEqual(documentacion['Content-Type'], 'application/pdf')

        unidad_equipo = UnidadEquipo.objects.filter(laboratorio=self.unidad).first()
        equipo = self.client.get(
            reverse('ficha_equipo_publica', args=[self.unidad.slug, unidad_equipo.codigo_unidad]),
            {'formato': 'pdf'},
        )
        self.assertEqual(equipo.status_code, 200)
        self.assertEqual(equipo['Content-Type'], 'application/pdf')

    def test_el_tablero_calcula_seccion_pestana_planta_y_plataforma_solo_para_gestion(self):
        ficha = FichaContenido.objects.get(codigo='LAC-DOC-CORRIDAS-RESUMEN')
        ficha.estado_validacion = 'validada'
        ficha.validado_por = self.coordinacion
        ficha.save(update_fields=['estado_validacion', 'validado_por'])
        tablero = tablero_unidad(self.unidad)
        self.assertEqual(len(tablero['pestanas']), 6)
        self.assertEqual(sum(len(item['secciones']) for item in tablero['pestanas']), 34)
        self.assertGreater(tablero['esperado'], 0)
        self.assertGreaterEqual(tablero['porcentaje'], 0)
        self.assertTrue(tablero['bloqueos'])
        self.assertEqual(len(tablero['familias']), self.unidad.familias_producto.filter(activa=True).count())
        self.assertTrue(
            {fila['estado'] for pestana in tablero['pestanas'] for fila in pestana['secciones']}
            <= {'aprobado', 'parcial', 'pendiente', 'bloqueado'}
        )
        self.assertTrue(
            {item['estado'] for item in tablero['fichas']}
            <= {'aprobado', 'parcial', 'pendiente', 'bloqueado'}
        )

        url = reverse('completitud_plantas', args=[self.unidad.slug])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.coordinacion)
        pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Avance por pestaña y sección')
        self.assertContains(pagina, 'Avance por familia')
        self.assertContains(pagina, 'Validación institucional')
        self.assertContains(pagina, 'Campos críticos vacíos')
        self.assertContains(pagina, 'Plataforma en tu alcance')

        ajeno = get_user_model().objects.create_user('ajeno.paso6', password='clave')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 403)
