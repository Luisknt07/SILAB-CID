"""«¿Qué pasa si?»: el escenario mueve tiempos y quita etapas, y todo se recalcula sin tocar la receta.

El estudiante parte del proceso de la planta y prueba variantes: una etapa más
larga, una espera más corta, una etapa que se quita. El balance, el cronograma y
el diagrama de flujo se recalculan con el proceso que resulta, se comparan con la
receta y la simulación se guarda con esos cambios.
"""
from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.escenarios import aplicar_escenario, cambios_del_escenario, escenario_del_formulario, leer_escenario
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta, resumen_proceso
from apps.formacion.presentation.simulaciones import parametros_guardables
from tests.integration.test_produccion_planta import BasePlantaProduce


class QuePasaSiTests(BasePlantaProduce):
    def test_quitar_una_etapa_y_mover_sus_tiempos_recalcula_el_proceso(self):
        datos = datos_de_receta(self.receta_queso, Decimal('1'))
        antes = resumen_proceso(datos)
        segunda = datos['etapas'][1]
        tercera = datos['etapas'][2]
        ajustes = leer_escenario({
            f"omitir_{segunda['orden']}": '1',
            f"duracion_{tercera['orden']}": str(tercera['duracion_min'] + 30),
            f"espera_{tercera['orden']}": str(tercera['espera_min']),
        }, datos)
        # La espera que no cambió no se guarda.
        self.assertEqual(set(ajustes), {f"omitir_{segunda['orden']}", f"duracion_{tercera['orden']}"})
        escenario = aplicar_escenario(datos, ajustes)
        self.assertEqual(len(escenario['etapas']), len(datos['etapas']) - 1)
        self.assertNotIn(segunda['orden'], [etapa['orden'] for etapa in escenario['etapas']])
        despues = resumen_proceso(escenario)
        self.assertNotEqual(despues['duracion_min'], antes['duracion_min'])
        # La receta sigue intacta.
        self.assertEqual(len(datos_de_receta(self.receta_queso, Decimal('1'))['etapas']), len(datos['etapas']))
        cambios = {cambio['variable']: cambio['a'] for cambio in cambios_del_escenario(datos, ajustes)}
        self.assertEqual(cambios[f"{segunda['orden']}. {segunda['nombre']}"], 'quitada')
        self.assertEqual(cambios[f"{tercera['orden']}. {tercera['nombre']} · trabajo"], f"{tercera['duracion_min'] + 30} min")

    def test_los_tiempos_y_las_etapas_quitadas_sobreviven_a_un_cambio_de_escala(self):
        datos = datos_de_receta(self.receta_queso, Decimal('1'))
        fuente = {'origen': f'{self.receta_queso.pk}:100', 'omitir_2': '1', 'duracion_3': '99', 'insumo_1_0': '5'}
        ajustes = escenario_del_formulario(fuente, datos, f'{self.receta_queso.pk}:200')
        self.assertEqual(set(ajustes), {'omitir_2', 'duracion_3'})

    def test_la_simulacion_compara_con_la_receta_y_se_guarda_con_los_cambios(self):
        url = reverse('simulador_balance', args=[self.unidad.slug])
        consulta = f'?receta={self.receta_queso.pk}&cantidad=100&omitir_2=1&duracion_3=90'
        pagina = self.client.get(url + consulta)
        self.assertContains(pagina, 'TU ESCENARIO FRENTE A LA RECETA')
        self.assertContains(pagina, 'quitada')
        self.assertContains(pagina, 'name="omitir_2" value="1" checked')
        self.assertContains(pagina, 'Diagrama de flujo del proceso')
        documento = self.client.get(url + consulta + '&formato=pdf')
        self.assertEqual(documento['Content-Type'], 'application/pdf')
        guardables = parametros_guardables({'receta': '1', 'omitir_2': '1', 'duracion_3': '90', 'espera_4': '10'})
        self.assertEqual(set(guardables), {'receta', 'omitir_2', 'duracion_3', 'espera_4'})
