"""Los simuladores dejan mover cada dato, y lo simulado se puede guardar.

Un simulador que solo cambia la escala no enseña nada: el estudiante necesita
bajar el rendimiento de una etapa y ver crecer la merma, o subir un insumo y ver
crecer el producto. Eso es el escenario, y corre por el mismo motor que la
planta usa para producir.

Guardar una simulación guarda las variables con que se corrió, no los
resultados: al abrirla se vuelve a calcular, así que si la receta cambió, se
nota. Y el documento se ve antes de descargarse.
"""

import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.escenarios import aplicar_escenario, cambios_del_escenario, leer_escenario, valores_del_formulario, variables_del_escenario
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, datos_de_receta
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.formacion.models.aula import SimulacionGuardada
from tests.integration.test_produccion_planta import BasePlantaProduce


class ElEscenarioDelAulaTests(BasePlantaProduce):
    def datos(self):
        return datos_de_receta(self.receta_queso, Decimal('1'))

    def test_ofrece_como_variable_cada_dato_que_el_balance_usa(self):
        grupos = variables_del_escenario(self.datos())
        campos = [campo['campo'] for grupo in grupos for campo in grupo['campos']]
        self.assertIn('rendimiento_esperado', campos)
        # Por etapa: su rendimiento, su trabajo, su espera y la opción de quitarla.
        for etapa in self.datos()['etapas']:
            for prefijo in ('rendimiento', 'duracion', 'espera', 'omitir'):
                self.assertIn(f"{prefijo}_{etapa['orden']}", campos)
        # Y una por cada insumo declarado en una etapa.
        primera_con_insumos = next(
            etapa for etapa in self.datos()['etapas'] if etapa['insumos']
        )
        self.assertIn(f"insumo_{primera_con_insumos['orden']}_0", campos)
        for grupo in grupos:
            for campo in grupo['campos']:
                with self.subTest(campo=campo['campo']):
                    self.assertTrue(campo['etiqueta'])
                    self.assertTrue(campo['ayuda'], 'un campo sin explicación es un número a ciegas')
                    # Un número parte del dato de la receta (una espera de 0 min también lo es);
                    # quitar la etapa es una casilla que nace sin marcar.
                    if campo.get('tipo') != 'casilla':
                        self.assertNotIn(campo['valor'], (None, ''))

    def test_solo_guarda_lo_que_de_verdad_se_movio(self):
        datos = self.datos()
        etapa = datos['etapas'][1]
        formulario = {
            f"rendimiento_{etapa['orden']}": etapa['rendimiento_pct'],
            'rendimiento_esperado': datos['rendimiento_esperado'],
        }
        self.assertEqual(leer_escenario(formulario, datos), {})
        formulario[f"rendimiento_{etapa['orden']}"] = '50'
        self.assertEqual(
            leer_escenario(formulario, datos), {f"rendimiento_{etapa['orden']}": '50'}
        )

    def test_descarta_lo_que_no_es_un_dato_del_proceso(self):
        datos = self.datos()
        fuera = {
            'rendimiento_999': '50',       # etapa que no existe
            'rendimiento_1': 'muchísimo',   # no es un número
            'rendimiento_2': '140',         # una etapa no rinde más de lo que entra
            'insumo_1_99': '3',             # insumo que no existe
            'formato': 'pdf',               # ni siquiera es del proceso
        }
        self.assertEqual(leer_escenario(fuera, datos), {})

    def test_bajar_el_rendimiento_de_una_etapa_sube_la_merma(self):
        datos = self.datos()
        etapa = next(
            item for item in datos['etapas']
            if Decimal(item['rendimiento_pct']) == 100 and item['tipo'] == 'operacion'
        )
        antes = balance_de_masa(datos)
        escenario = aplicar_escenario(datos, {f"rendimiento_{etapa['orden']}": '80'})
        despues = balance_de_masa(escenario)

        self.assertLess(
            Decimal(despues['producto_por_balance']), Decimal(antes['producto_por_balance'])
        )
        perdida_antes = sum(Decimal(fila['perdida']) for fila in antes['filas'])
        perdida_despues = sum(Decimal(fila['perdida']) for fila in despues['filas'])
        self.assertGreater(perdida_despues, perdida_antes)
        # La receta de la planta no se tocó.
        self.assertEqual(datos['etapas'][etapa['orden'] - 1]['rendimiento_pct'], etapa['rendimiento_pct'])

    def test_subir_un_insumo_que_se_incorpora_sube_el_producto(self):
        datos = self.datos()
        etapa, indice, insumo = next(
            (etapa, indice, insumo)
            for etapa in datos['etapas']
            for indice, insumo in enumerate(etapa['insumos'])
            if insumo.get('forma_parte') == 'si' and insumo['unidad'].lower().startswith(('kg', 'litro'))
        )
        antes = balance_de_masa(datos)
        doble = str(Decimal(insumo['cantidad']) + Decimal('5'))
        escenario = aplicar_escenario(datos, {f"insumo_{etapa['orden']}_{indice}": doble})
        despues = balance_de_masa(escenario)

        self.assertGreater(
            Decimal(despues['producto_por_balance']), Decimal(antes['producto_por_balance'])
        )

    def test_cuenta_lo_que_se_movio_con_el_valor_de_la_receta(self):
        datos = self.datos()
        cambios = cambios_del_escenario(datos, {'rendimiento_2': '80'})
        self.assertEqual(len(cambios), 1)
        self.assertIn('80', cambios[0]['a'])
        self.assertIn(datos['etapas'][1]['rendimiento_pct'], cambios[0]['de'])

    def test_el_formulario_marca_los_campos_movidos(self):
        grupos = valores_del_formulario(self.datos(), {'rendimiento_2': '80'})
        movidos = [
            campo for grupo in grupos for campo in grupo['campos'] if campo['movido']
        ]
        self.assertEqual([campo['campo'] for campo in movidos], ['rendimiento_2'])
        self.assertEqual(movidos[0]['valor'], '80')
        abiertos = [grupo['titulo'] for grupo in grupos if grupo['movido']]
        self.assertEqual(len(abiertos), 1)


class ElSimuladorConEscenarioTests(BasePlantaProduce):
    def url(self, **parametros):
        base = reverse('simulador_balance', args=[self.unidad.slug])
        consulta = '&'.join(f'{clave}={valor}' for clave, valor in parametros.items())
        return f'{base}?{consulta}' if consulta else base

    def test_muestra_las_variables_el_diagrama_y_lo_que_entra_y_sale(self):
        pagina = self.client.get(self.url(receta=self.receta_queso.pk))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'ENTRADAS Y SALIDAS, ETAPA POR ETAPA')
        self.assertContains(pagina, 'TODO LO QUE ENTRA')
        self.assertContains(pagina, 'TODO LO QUE SALE')
        self.assertContains(pagina, 'Merma total')
        self.assertContains(pagina, 'name="rendimiento_1"')

    def test_mover_un_dato_cambia_el_resultado_y_lo_deja_dicho(self):
        pagina = self.client.get(self.url(receta=self.receta_queso.pk, rendimiento_2='50'))

        self.assertContains(pagina, 'LO QUE MOVISTE EN ESTE ESCENARIO')
        self.assertContains(pagina, 'Volver a los datos de la receta')

    def test_quien_no_entro_simula_igual_pero_no_puede_guardar(self):
        pagina = self.client.get(self.url(receta=self.receta_queso.pk))

        self.assertContains(pagina, 'BALANCE DE MATERIA POR ETAPA')
        self.assertNotContains(pagina, 'GUARDA ESTA SIMULACIÓN')

    def test_la_ficha_del_proceso_no_ofrece_guardar_una_simulacion(self):
        ficha = self.client.get(
            reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk])
        )

        self.assertEqual(ficha.status_code, 200)
        self.assertNotContains(ficha, 'GUARDA ESTA SIMULACIÓN')


class GuardarYRetomarUnaSimulacionTests(BasePlantaProduce):
    def setUp(self):
        super().setUp()
        self.estudiante = get_user_model().objects.create_user(
            username='estudiante.simula',
            email='estudiante.simula@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.estudiante)

    def guardar(self, **extra):
        datos = {
            'simulador': 'balance',
            'receta': str(self.receta_queso.pk),
            'cantidad': '100',
            'rendimiento_2': '80',
            'nombre': 'Corrida con más merma',
            'notas': 'Para ver cuánto suero se pierde.',
        }
        datos.update(extra)
        return self.client.post(
            reverse('guardar_simulacion', args=[self.unidad.slug]), datos
        )

    def test_guarda_las_variables_y_devuelve_al_simulador_con_ellas(self):
        respuesta = self.guardar()

        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(f'simulacion={simulacion.pk}', respuesta.url)
        self.assertIn('guardada=1', respuesta.url)
        self.assertEqual(simulacion.nombre, 'Corrida con más merma')
        self.assertEqual(simulacion.receta, self.receta_queso)
        self.assertEqual(simulacion.familia, self.receta_queso.familia)
        # Guarda las variables, no los resultados.
        self.assertEqual(
            simulacion.parametros,
            {'receta': str(self.receta_queso.pk), 'cantidad': '100', 'rendimiento_2': '80'},
        )
        # Y un resumen para reconocerla en la lista sin recalcularla.
        etiquetas = [etiqueta for etiqueta, _valor in simulacion.resumen]
        self.assertEqual(etiquetas, ['Entra', 'Producto', 'Merma', 'Datos movidos'])

    def test_el_formulario_no_guarda_lo_que_no_es_del_proceso(self):
        self.guardar(formato='pdf', next='/admin/')

        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)
        self.assertNotIn('formato', simulacion.parametros)
        self.assertNotIn('next', simulacion.parametros)

    def test_al_abrirla_el_simulador_llega_con_los_datos_puestos(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)

        pagina = self.client.get(
            reverse('simulador_balance', args=[self.unidad.slug]),
            {'receta': self.receta_queso.pk, 'cantidad': '100', 'rendimiento_2': '80',
             'simulacion': simulacion.pk},
        )

        self.assertContains(pagina, 'ESTÁS EDITANDO UNA SIMULACIÓN GUARDADA')
        self.assertContains(pagina, 'Corrida con más merma')
        self.assertContains(pagina, 'LO QUE MOVISTE EN ESTE ESCENARIO')

    def test_volver_a_guardarla_la_cambia_en_vez_de_duplicarla(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)

        self.guardar(simulacion=str(simulacion.pk), nombre='Corregida', rendimiento_2='70')

        self.assertEqual(SimulacionGuardada.objects.filter(autor=self.estudiante).count(), 1)
        simulacion.refresh_from_db()
        self.assertEqual(simulacion.nombre, 'Corregida')
        self.assertEqual(simulacion.parametros['rendimiento_2'], '70')

    def test_guardarla_aparte_deja_las_dos(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)

        self.guardar(simulacion=str(simulacion.pk), nombre='Una variante', accion='copia')

        nombres = set(
            SimulacionGuardada.objects.filter(autor=self.estudiante).values_list('nombre', flat=True)
        )
        self.assertEqual(nombres, {'Corrida con más merma', 'Una variante'})

    def test_sin_nombre_la_simulacion_igual_queda_reconocible(self):
        self.guardar(nombre='   ')

        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)
        self.assertTrue(simulacion.nombre.startswith('Simulación del '))

    def test_la_lista_ofrece_abrirla_verla_y_borrarla(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)

        pagina = self.client.get(reverse('mis_simulaciones', args=[self.unidad.slug]))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Corrida con más merma')
        self.assertContains(pagina, reverse('reporte_simulacion', args=[self.unidad.slug, simulacion.pk]))
        self.assertContains(pagina, reverse('eliminar_simulacion', args=[self.unidad.slug, simulacion.pk]))
        self.assertContains(pagina, f'simulacion={simulacion.pk}')

    def test_se_elimina_y_desaparece_de_la_lista(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)

        respuesta = self.client.post(
            reverse('eliminar_simulacion', args=[self.unidad.slug, simulacion.pk])
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(SimulacionGuardada.objects.filter(pk=simulacion.pk).exists())
        lista = self.client.get(respuesta.url)
        self.assertContains(lista, 'La simulación se eliminó.')

    def test_la_simulacion_de_otro_no_se_abre_ni_se_borra(self):
        self.guardar()
        simulacion = SimulacionGuardada.objects.get(autor=self.estudiante)
        ajeno = get_user_model().objects.create_user(
            username='otro.estudiante', email='otro@upec.edu.ec', password='clave-segura-pruebas',
        )
        self.client.force_login(ajeno)

        self.assertEqual(
            self.client.get(reverse('reporte_simulacion', args=[self.unidad.slug, simulacion.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse('eliminar_simulacion', args=[self.unidad.slug, simulacion.pk])).status_code,
            404,
        )
        self.assertTrue(SimulacionGuardada.objects.filter(pk=simulacion.pk).exists())
        self.assertNotContains(
            self.client.get(reverse('mis_simulaciones', args=[self.unidad.slug])),
            'Corrida con más merma',
        )

    def test_guardar_y_listar_exigen_haber_entrado(self):
        self.client.logout()

        for respuesta in (
            self.client.get(reverse('mis_simulaciones', args=[self.unidad.slug])),
            self.client.post(reverse('guardar_simulacion', args=[self.unidad.slug]), {}),
        ):
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn('login', respuesta.url)


class ElDocumentoDeUnaSimulacionTests(BasePlantaProduce):
    def setUp(self):
        super().setUp()
        self.estudiante = get_user_model().objects.create_user(
            username='estudiante.reporte',
            email='estudiante.reporte@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.estudiante)
        self.simulacion = SimulacionGuardada.objects.create(
            unidad=self.unidad,
            autor=self.estudiante,
            simulador='balance',
            receta=self.receta_queso,
            nombre='Escenario de prueba',
            notas='Para el informe de la práctica.',
            parametros={'receta': str(self.receta_queso.pk), 'cantidad': '100', 'rendimiento_2': '80'},
        )

    @property
    def url(self):
        return reverse('reporte_simulacion', args=[self.unidad.slug, self.simulacion.pk])

    def test_primero_se_ve_como_queda_con_todas_sus_tablas(self):
        pagina = self.client.get(self.url)

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'ASÍ SE VA A DESCARGAR')
        self.assertContains(pagina, 'logo_upec.png')
        self.assertContains(pagina, 'Escenario de prueba')
        self.assertContains(pagina, 'Para el informe de la práctica.')
        self.assertContains(pagina, 'LO QUE SE MOVIÓ RESPECTO DE LA RECETA')
        self.assertContains(pagina, 'TODO LO QUE ENTRA')
        self.assertContains(pagina, 'TODO LO QUE SALE')
        self.assertContains(pagina, 'formato=pdf')

    def test_y_despues_se_descarga_como_documento(self):
        respuesta = self.client.get(self.url, {'formato': 'pdf'})

        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn(f'simulacion-{self.unidad.slug}-{self.simulacion.pk}.pdf', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertIn(b'/Font', respuesta.content)

    def test_el_documento_se_recalcula_con_el_proceso_de_hoy(self):
        etapa = self.receta_queso.etapas.order_by('orden').first()
        etapa.nombre = 'Recepción renombrada en la planta'
        etapa.save(update_fields=['nombre'])

        pagina = self.client.get(self.url)

        self.assertContains(pagina, 'Recepción renombrada en la planta')


class ElDocumentoDeLosOtrosSimuladoresTests(BasePlantaProduce):
    """Los tres simuladores se guardan, y cada uno tiene su propio documento.

    Un balance de línea guardado no puede descargarse como si fuera un balance
    de materia: lo que el estudiante simuló fueron estaciones y tiempos.
    """

    def setUp(self):
        super().setUp()
        self.estudiante = get_user_model().objects.create_user(
            username='estudiante.otros',
            email='estudiante.otros@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.estudiante)

    def guardada(self, simulador, parametros):
        return SimulacionGuardada.objects.create(
            unidad=self.unidad,
            autor=self.estudiante,
            simulador=simulador,
            receta=self.receta_queso,
            nombre=f'Ensayo de {simulador}',
            parametros={'receta': str(self.receta_queso.pk), **parametros},
        )

    def test_el_balance_de_linea_se_descarga_con_sus_estaciones(self):
        simulacion = self.guardada('linea', {'corridas': '3', 'jornada': '8'})

        pagina = self.client.get(reverse('reporte_simulacion', args=[self.unidad.slug, simulacion.pk]))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Simulación: Balance de línea')
        self.assertContains(pagina, 'CÓMO QUEDAN LAS ESTACIONES')
        self.assertContains(pagina, 'Ritmo que pide la jornada')
        self.assertNotContains(pagina, 'TODO LO QUE SALE')
        pdf = self.client.get(
            reverse('reporte_simulacion', args=[self.unidad.slug, simulacion.pk]), {'formato': 'pdf'}
        )
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_el_requerimiento_se_descarga_contra_las_existencias(self):
        simulacion = self.guardada('materiales', {'cantidad': '200'})

        pagina = self.client.get(reverse('reporte_simulacion', args=[self.unidad.slug, simulacion.pk]))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Simulación: Requerimiento de materiales')
        self.assertContains(pagina, 'LO QUE EL PLAN DEBERÍA ENTREGAR')
        self.assertContains(pagina, 'Falta comprar')

    def test_la_lista_reconoce_cada_simulacion_por_sus_propias_cifras(self):
        from apps.formacion.presentation.simulaciones import resumen_de

        linea = resumen_de(self.guardada('linea', {'corridas': '3', 'jornada': '8'}))
        materiales = resumen_de(self.guardada('materiales', {'cantidad': '200'}))

        self.assertEqual(
            [etiqueta for etiqueta, _valor in linea],
            ['Ritmo que pide', 'Ciclo real', 'Estaciones', 'Alcanza la jornada'],
        )
        self.assertEqual(
            [etiqueta for etiqueta, _valor in materiales],
            ['Insumos', 'Cubiertos', 'Faltantes', 'Corridas'],
        )

    def test_los_tres_simuladores_ofrecen_guardar(self):
        for nombre in ('simulador_balance', 'simulador_linea', 'simulador_materiales'):
            with self.subTest(simulador=nombre):
                pagina = self.client.get(
                    reverse(nombre, args=[self.unidad.slug]), {'receta': self.receta_queso.pk}
                )
                self.assertContains(pagina, 'GUARDA ESTA SIMULACIÓN')
                self.assertContains(pagina, 'Mis simulaciones')


class ElEscenarioNoSeArrastraTests(BasePlantaProduce):
    """Cambiar la escala o el proceso no deja pegados los números del anterior.

    El formulario reenvía todos sus campos. Los insumos se escriben en cantidad,
    y una cantidad depende del tamaño de la corrida: los kilos de sal de una
    corrida de 100 litros no son los de una de 200. Estas pruebas reenvían el
    formulario con el «origen» que la página misma escribió, que es lo que haría
    el navegador.
    """

    def origen_de(self, **parametros):
        """Abre el simulador y devuelve el origen que la página declara."""
        pagina = self.client.get(
            reverse('simulador_balance', args=[self.unidad.slug]), parametros
        )
        encontrado = re.search(r'name="origen" value="([^"]*)"', pagina.content.decode())
        self.assertIsNotNone(encontrado, 'la página no declara su origen')
        return encontrado.group(1)

    def simular(self, **parametros):
        return self.client.get(
            reverse('simulador_balance', args=[self.unidad.slug]), parametros
        )

    def test_al_cambiar_la_escala_solo_sobreviven_los_rendimientos(self):
        datos = datos_de_receta(self.receta_queso, Decimal('1'))
        etapa, indice, insumo = next(
            (etapa, indice, insumo)
            for etapa in datos['etapas']
            for indice, insumo in enumerate(etapa['insumos'])
        )
        origen = self.origen_de(receta=self.receta_queso.pk)

        pagina = self.simular(
            receta=self.receta_queso.pk,
            cantidad=str(self.receta_queso.cantidad_base * 2),
            origen=origen,
            rendimiento_2='80',
            **{f"insumo_{etapa['orden']}_{indice}": str(Decimal(insumo['cantidad']) + 1)},
        )

        cambios = pagina.context['cambios']
        movidas = [cambio['variable'] for cambio in cambios]
        # El rendimiento es un porcentaje y no depende de la escala: viaja.
        self.assertTrue(any('rendimiento' in variable for variable in movidas), movidas)
        # El insumo se escribió para la corrida anterior: se queda.
        self.assertFalse(any(insumo['nombre'] in variable for variable in movidas), movidas)

    def test_al_cambiar_de_proceso_no_viaja_nada(self):
        otra = (
            Receta.objects.filter(unidad=self.unidad, activa=True)
            .exclude(pk=self.receta_queso.pk)
            .first()
        )
        self.assertIsNotNone(otra)
        origen = self.origen_de(receta=self.receta_queso.pk)

        pagina = self.simular(receta=otra.pk, origen=origen, rendimiento_2='80')

        self.assertEqual(pagina.context['cambios'], [])
        self.assertNotContains(pagina, 'LO QUE MOVISTE EN ESTE ESCENARIO')

    def test_sin_cambiar_de_origen_el_escenario_se_conserva(self):
        datos = datos_de_receta(self.receta_queso, Decimal('1'))
        etapa, indice, insumo = next(
            (etapa, indice, insumo)
            for etapa in datos['etapas']
            for indice, insumo in enumerate(etapa['insumos'])
        )
        origen = self.origen_de(receta=self.receta_queso.pk)

        pagina = self.simular(
            receta=self.receta_queso.pk,
            origen=origen,
            rendimiento_2='80',
            **{f"insumo_{etapa['orden']}_{indice}": str(Decimal(insumo['cantidad']) + 1)},
        )

        movidas = [cambio['variable'] for cambio in pagina.context['cambios']]
        self.assertEqual(len(movidas), 2, movidas)
        self.assertTrue(any(insumo['nombre'] in variable for variable in movidas), movidas)
