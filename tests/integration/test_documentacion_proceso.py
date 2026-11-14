"""La documentación de un proceso: la teoría detrás de cada etapa.

La ficha dice qué hace la planta paso a paso; la documentación dice por qué:
qué operación unitaria es cada etapa, qué fenómeno ocurre, qué variable la
gobierna y qué pasa fuera de rango. Nada se escribe a mano por proceso: cada
etapa se clasifica por su nombre y el resto sale de la receta cargada, así que
tiene que valer igual para las quince recetas de las cinco plantas.
"""

from decimal import Decimal

from django.urls import reverse

from apps.documentos.presentation.documentacion import OPERACIONES, balance_general, clasificar_etapa, documentacion_de_proceso, entradas_y_salidas
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class ElGlosarioDeOperacionesTests(BasePlantaProduce):
    def test_cada_operacion_explica_que_pasa_y_como_se_mide(self):
        for operacion in OPERACIONES:
            with self.subTest(operacion=operacion['clave']):
                for clave in ('nombre', 'familia', 'fenomeno', 'variable', 'fuera_de_rango', 'se_mide', 'icono'):
                    self.assertTrue(operacion.get(clave), f'{operacion["clave"]} sin «{clave}»')
                self.assertTrue(operacion['icono'].startswith('fas fa-'))

    def test_clasifica_las_etapas_de_todas_las_recetas_de_la_planta(self):
        sin_clasificar = []
        for receta in Receta.objects.filter(unidad=self.unidad, activa=True):
            for etapa in datos_de_receta(receta, Decimal('1'))['etapas']:
                if clasificar_etapa(etapa)['clave'] == 'operacion':
                    sin_clasificar.append(f'{receta.codigo}: {etapa["nombre"]}')
        self.assertEqual(sin_clasificar, [], f'etapas sin operación unitaria: {sin_clasificar}')

    def test_reconoce_la_operacion_por_el_nombre_de_la_etapa(self):
        casos = {
            'Pasteurización': 'termico_alto',
            'Incubación': 'fermentacion',
            'Corte y desuerado': 'separacion',
            'Molienda por disco de 8 mm': 'reduccion',
            'Concentración con agitación': 'concentracion',
            'Envasado y etiquetado': 'envasado',
            'Limpieza de la línea': 'limpieza',
        }
        for nombre, esperado in casos.items():
            with self.subTest(etapa=nombre):
                self.assertEqual(clasificar_etapa({'nombre': nombre, 'tipo': 'operacion'})['clave'], esperado)
        # Mover no transforma: el tipo manda sobre la palabra «cámara» del nombre.
        self.assertEqual(
            clasificar_etapa({'nombre': 'Traslado a la cámara', 'tipo': 'transporte'})['clave'],
            'transporte',
        )

    def test_una_etapa_sin_nombre_reconocible_cae_en_su_tipo(self):
        self.assertEqual(clasificar_etapa({'nombre': 'Paso propio', 'tipo': 'espera'})['clave'], 'espera')
        self.assertEqual(clasificar_etapa({'nombre': 'Paso propio', 'tipo': 'transporte'})['clave'], 'transporte')
        self.assertEqual(clasificar_etapa({'nombre': 'Paso propio', 'tipo': 'operacion'})['clave'], 'operacion')


class LaDocumentacionDelProcesoTests(BasePlantaProduce):
    def documentacion(self, codigo='LAC-REC-QUESO-100'):
        receta = Receta.objects.get(codigo=codigo)
        return documentacion_de_proceso(receta, self.unidad, Decimal('1'))

    def test_arma_el_flujo_con_lo_que_entra_y_lo_que_sale_de_cada_etapa(self):
        documentacion = self.documentacion()
        flujo = documentacion['flujo']
        self.assertEqual(len(flujo), self.receta_queso.etapas.count())
        primera = flujo[0]
        self.assertEqual(primera['orden'], 1)
        self.assertEqual(primera['operacion']['clave'], 'recepcion')
        # La leche entra en la primera etapa y la masa continúa hacia la segunda.
        self.assertIn('Leche cruda', [insumo['nombre'] for insumo in primera['insumos']])
        self.assertTrue(primera['entra'])
        # El suero sale en la etapa de desuerado, declarado por la receta.
        salidas = [salida['nombre'] for fila in flujo for salida in fila['salidas']]
        self.assertTrue(any('Suero' in salida for salida in salidas), salidas)
        # Las mermas del balance aparecen marcadas como tales.
        clases = {salida['clase'] for fila in flujo for salida in fila['salidas']}
        self.assertIn('merma', clases)

    def test_agrupa_las_etapas_por_operacion_unitaria_en_el_orden_en_que_ocurren(self):
        operaciones = self.documentacion()['operaciones']
        self.assertGreaterEqual(len(operaciones), 5)
        claves = [operacion['clave'] for operacion in operaciones]
        # La recepción abre el proceso.
        self.assertEqual(claves[0], 'recepcion')
        # Cada operación dice qué etapas de este proceso la usan.
        for operacion in operaciones:
            with self.subTest(operacion=operacion['clave']):
                self.assertTrue(operacion['etapas'])
                self.assertTrue(all(etapa['nombre'] for etapa in operacion['etapas']))
        # El orden es el de la corrida, no el del glosario.
        primeros = [operacion['etapas'][0]['orden'] for operacion in operaciones]
        self.assertEqual(primeros, sorted(primeros))

    def test_lista_las_variables_que_los_simuladores_dejan_mover(self):
        variables = self.documentacion()['variables']
        nombres = [variable['nombre'] for variable in variables]
        self.assertIn('Escala de la corrida', nombres)
        self.assertIn('Rendimiento esperado', nombres)
        self.assertIn('Existencias en bodega', nombres)
        for variable in variables:
            with self.subTest(variable=variable['nombre']):
                self.assertTrue(variable['valor'])
                self.assertTrue(variable['de_donde'])
                self.assertTrue(variable['efecto'])
                self.assertTrue(variable['simulador'])

    def test_dice_de_donde_sale_cada_dato(self):
        datos = self.documentacion()['datos_que_usa']
        self.assertGreaterEqual(len(datos), 4)
        fuentes = ' '.join(fila['fuente'] for fila in datos)
        self.assertIn('LAC-REC-QUESO-100', fuentes)
        self.assertIn('inventario', fuentes.lower())

    def test_la_pagina_se_publica_y_se_puede_incrustar(self):
        pagina = self.client.get(
            reverse('documentacion_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        )
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertContains(pagina, 'Documentación del proceso')
        self.assertContains(pagina, 'ENTRADAS Y SALIDAS, ETAPA POR ETAPA')
        self.assertContains(pagina, 'LAS OPERACIONES UNITARIAS DE ESTE PROCESO')
        self.assertContains(pagina, 'VARIABLES QUE SE PUEDEN MOVER')
        self.assertContains(pagina, 'Tratamiento térmico')
        self.assertContains(pagina, 'esta-incrustado')

    def test_un_proceso_de_otra_unidad_no_se_abre_desde_aqui(self):
        otra = Unidad.objects.create(
            nombre='Otra planta', slug='otra-planta-documentacion',
            descripcion='Unidad ajena de prueba.',
            fecha_inicio=self.unidad.fecha_inicio, dependencia='plantas_piloto',
        )
        producto = Producto.objects.create(
            unidad=otra, codigo='DOC-PROD-AJENO', nombre='Producto ajeno',
            unidad_medida='kg',
        )
        ajena = Receta.objects.create(
            unidad=otra, producto=producto, codigo='DOC-REC-AJENA',
            nombre='Proceso ajeno', cantidad_base=1, unidad_base='kg',
            rendimiento_esperado=1,
        )
        respuesta = self.client.get(
            reverse('documentacion_proceso', args=[self.unidad.slug, ajena.pk])
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_la_ficha_y_el_aula_llevan_a_la_documentacion(self):
        ficha = self.client.get(
            reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk])
        )
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(
            ficha, reverse('documentacion_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        )
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, 'Documentación de los procesos')
        self.assertContains(pagina, 'Ruta del saber y documentación técnica')
        self.assertNotContains(pagina, f'documentacion-proceso-{self.receta_queso.pk}')
        self.assertContains(ficha, 'Documentación técnica')
        self.assertContains(ficha, 'Capacidad y equilibrado')


class ElBalanceGeneralDeLaCorridaTests(BasePlantaProduce):
    """La corrida entera en un bloque: lo que entra, lo que sale y lo que se pierde.

    Los totales no se suman aparte: salen del balance por etapa, que ya resolvió
    las conversiones. Si una etapa declara más salida de la que pierde, el
    diagrama lo dice y nombra la etapa, porque eso es un error de la receta que
    la planta tiene que corregir.
    """

    def general(self, codigo='LAC-REC-QUESO-100'):
        receta = Receta.objects.get(codigo=codigo)
        datos = datos_de_receta(receta, Decimal('1'))
        return balance_general(datos, entradas_y_salidas(datos)), datos

    def test_la_materia_prima_encabeza_las_entradas_con_su_nombre(self):
        general, datos = self.general()
        primera = general['entradas'][0]
        self.assertEqual(primera['clase'], 'base')
        self.assertEqual(primera['nombre'], 'Leche cruda')
        self.assertEqual(primera['cantidad'], datos['cantidad_base'])
        self.assertEqual(primera['unidad'], datos['unidad_base'])
        # La materia prima no se cuenta dos veces: no reaparece como auxiliar.
        self.assertNotIn('Leche cruda', [fila['nombre'] for fila in general['auxiliares']])

    def test_separa_lo_que_se_incorpora_de_lo_que_solo_se_consume(self):
        general, _datos = self.general()
        incorporados = [fila['nombre'] for fila in general['entradas'] if fila['clase'] == 'insumo']
        auxiliares = [fila['nombre'] for fila in general['auxiliares']]
        self.assertTrue(incorporados, 'la receta del queso incorpora sal y cuajo')
        self.assertTrue(auxiliares, 'y usa paños y empaques que no quedan en el producto')
        self.assertEqual(set(incorporados) & set(auxiliares), set())

    def test_el_producto_las_salidas_declaradas_y_la_merma_salen_por_la_derecha(self):
        general, datos = self.general()
        clases = [fila['clase'] for fila in general['salidas']]
        self.assertEqual(clases[0], 'producto')
        self.assertEqual(general['salidas'][0]['nombre'], datos['producto'])
        self.assertIn('subproducto', clases)
        self.assertIn('merma', clases)

    def test_el_agua_de_lavado_sale_pero_nunca_fue_parte_del_producto(self):
        general, _datos = self.general()
        externas = [fila['nombre'] for fila in general['externas']]
        self.assertTrue(any('Agua' in nombre for nombre in externas), externas)
        # Y por eso no entra al total de lo que sale.
        self.assertNotIn('Agua', ' '.join(fila['nombre'] for fila in general['salidas']))

    def test_lo_que_entra_es_lo_que_sale_cuando_la_receta_es_consistente(self):
        general, _datos = self.general()
        self.assertTrue(general['cuadra'], f"{general['entra_total']} != {general['sale_total']}")
        self.assertEqual(general['entra_total'], general['sale_total'])
        self.assertEqual(general['descuadres'], [])

    def test_cuando_una_etapa_declara_de_mas_el_diagrama_nombra_la_etapa(self):
        salida = (
            self.receta_queso.salidas.filter(etapa__isnull=False, etapa__rendimiento_pct__lt=100)
            .order_by('etapa__orden')
            .first()
        )
        self.assertIsNotNone(salida, 'la receta del queso declara suero en el desuerado')
        etapa = salida.etapa
        salida.cantidad = salida.cantidad * 10
        salida.save(update_fields=['cantidad'])

        general, _datos = self.general()

        self.assertFalse(general['cuadra'])
        self.assertTrue(general['sobra_declarado'])
        self.assertEqual([fila['orden'] for fila in general['descuadres']], [etapa.orden])

    def test_la_pagina_dibuja_el_bloque_con_su_comprobacion(self):
        pagina = self.client.get(
            reverse('documentacion_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        )

        self.assertContains(pagina, 'BALANCE DE MATERIA DE TODA LA CORRIDA')
        self.assertContains(pagina, 'Se consumen sin quedar en el producto')
        self.assertContains(pagina, 'doc-general__caja')

    def test_el_simulador_dibuja_el_mismo_bloque(self):
        pagina = self.client.get(
            reverse('simulador_balance', args=[self.unidad.slug]),
            {'receta': self.receta_queso.pk},
        )

        self.assertContains(pagina, 'BALANCE DE MATERIA DE TODA LA CORRIDA')
