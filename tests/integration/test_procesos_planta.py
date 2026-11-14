"""La receta con etapas: el proceso del que sale todo lo demás.

Sobre la Planta Piloto de Lácteos cargada: cada receta declara sus etapas
con el tipo del cursograma, dónde ocurren, cuánto duran, cuánta masa
continúa y sus puntos críticos. De ahí salen el balance de masa, el
cronograma, los diagramas de flujo y sinóptico, el cursograma analítico, la
ficha de proceso, el reporte y lo que la guía de práctica toma prellenado.
"""

from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_flujo
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, cronograma, cursograma_analitico, datos_de_receta, diagrama_flujo_svg, diagrama_sinoptico_svg, guia_desde_proceso, resumen_proceso
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, Producto, Receta
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class LaRecetaTieneEtapasTests(BasePlantaProduce):
    def test_la_carga_trae_las_etapas_con_sus_insumos_y_salidas(self):
        etapas = list(self.receta_queso.etapas.order_by('orden'))
        self.assertEqual(len(etapas), 11)
        tipos = [etapa.tipo for etapa in etapas]
        self.assertEqual(tipos.count('operacion'), 6)
        self.assertEqual(tipos.count('inspeccion'), 1)
        self.assertEqual(tipos.count('espera'), 2)
        self.assertEqual(tipos.count('transporte'), 1)
        self.assertEqual(tipos.count('almacenamiento'), 1)
        recepcion, pasteurizacion = etapas[0], etapas[1]
        # Acidez y densidad son calidad (PC); la pasteurización es el PCC de inocuidad.
        self.assertTrue(recepcion.punto_control)
        self.assertFalse(recepcion.punto_critico)
        self.assertTrue(pasteurizacion.punto_critico)
        self.assertEqual(recepcion.equipo.codigo, 'LAC-EQ-TANQUE')
        self.assertEqual(recepcion.espacio.codigo, 'LAC-AREA-RECEPCION')
        self.assertIn('65 °C', pasteurizacion.limite)
        # Cada insumo y cada salida saben en qué etapa entran o salen.
        leche = self.receta_queso.insumos.get(consumible__codigo='LAC-INS-LECHE')
        self.assertEqual(leche.etapa.orden, 1)
        cuajo = self.receta_queso.insumos.get(consumible__codigo='LAC-INS-CUAJO')
        self.assertEqual(cuajo.etapa.nombre, 'Enfriamiento y adición de cloruro y cuajo')
        suero = self.receta_queso.salidas.get(producto__codigo='LAC-PRD-SUERO')
        self.assertEqual(suero.etapa.nombre, 'Corte y desuerado')
        # Quince minutos de trabajo más la prensa, la coagulación y la cámara: 1830 minutos.
        self.assertEqual(self.receta_queso.duracion_estandar_min, 1830)
        # La carga se repite sin duplicar etapas.
        from django.core.management import call_command
        antes = EtapaReceta.objects.filter(receta__unidad=self.unidad).count()
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        self.assertEqual(self.receta_queso.etapas.count(), 11)
        self.assertEqual(EtapaReceta.objects.filter(receta__unidad=self.unidad).count(), antes)

    def test_el_motor_deriva_resumen_balance_y_cronograma(self):
        datos = datos_de_receta(self.receta_queso)
        resumen = resumen_proceso(datos)
        self.assertEqual(resumen['etapas'], 11)
        self.assertEqual(resumen['puntos_criticos'], 1)
        self.assertEqual(resumen['puntos_control'], 1)
        self.assertEqual(resumen['personas_max'], 3)
        self.assertEqual(resumen['duracion_min'], 1830)
        self.assertEqual(resumen['trabajo_min'], 230)
        self.assertEqual(resumen['conteo']['operacion'], 6)

        balance = balance_de_masa(datos)
        corte = balance['filas'][4]
        self.assertEqual(corte['nombre'], 'Corte y desuerado')
        # El cloruro y el cuajo se incorporan en la tina: 99,03 litros llegan al corte.
        self.assertEqual(corte['entra'], '99.03')
        self.assertEqual(corte['continua'], '13.864')
        self.assertEqual(corte['declarado'], '85')
        self.assertEqual(corte['perdida'], '0.166')
        salado = balance['filas'][5]
        self.assertEqual(salado['agregado'], '0.4')
        limpieza = balance['filas'][10]
        self.assertEqual(limpieza['externo'], '60')
        self.assertEqual(limpieza['exceso'], '')
        self.assertEqual(balance['producto_por_balance'], '12.022')
        self.assertEqual(balance['producto_esperado'], '12')
        # Dos corridas base: la leche entra doble y el suero sale doble.
        doble = balance_de_masa(datos_de_receta(self.receta_queso, factor=2))
        self.assertEqual(doble['entrada'], '200')
        self.assertEqual(doble['filas'][4]['declarado'], '170')

        crono = cronograma(datos)
        self.assertEqual(crono['total_min'], 1830)
        self.assertEqual(crono['filas'][1]['inicio_min'], 15)
        self.assertEqual(crono['filas'][1]['fin_min'], 60)
        self.assertEqual(crono['filas'][6]['duracion_min'], 130)

    def test_los_diagramas_y_el_cursograma_salen_de_las_etapas(self):
        datos = datos_de_receta(self.receta_queso)
        flujo = diagrama_flujo_svg(datos)
        self.assertIn('<svg', flujo)
        self.assertIn('Pasteurización', flujo)
        # Codex CXC 1-1969: los PCC numerados en el orden del proceso, entre inicio y fin (ISO 5807).
        self.assertIn('PCC-1', flujo)  # Pasteurización (inocuidad).
        self.assertIn('PC-1', flujo)   # Recepción: acidez y densidad (calidad).
        self.assertNotIn('PCC-2', flujo)
        self.assertIn('>Inicio<', flujo)
        self.assertIn('Fin: producto terminado', flujo)
        self.assertIn('Suero de quesería 85 litros', flujo)
        # ASME Y15.3 como formas: cada tipo con la suya (6 operaciones, 1 inspección, 1 transporte,
        # 2 demoras y 1 almacenamiento), además de la leyenda.
        figuras = diagrama_flujo(datos).figuras
        self.assertEqual(sum(1 for f in figuras if f[0] == 'circulo' and f[3] == 10), 6)
        self.assertEqual(sum(1 for f in figuras if f[0] == 'rect' and f[3] == f[4] == 20), 1)
        self.assertEqual(sum(1 for f in figuras if f[0] == 'poligono' and len(f[1]) == 7), 2)  # transporte
        sinoptico = diagrama_sinoptico_svg(datos)
        # DOP: seis operaciones (O-1…O-6) y una inspección (I-1); lo demás va en el cursograma.
        for clave in ('O-1', 'O-6', 'I-1'):
            self.assertIn(f'>{clave}<', sinoptico)
        self.assertNotIn('O-7', sinoptico)
        self.assertNotIn('Coagulación', sinoptico)
        # La materia prima encabeza la línea y no entra otra vez por un costado.
        self.assertIn('Leche cruda 100 litros · materia prima', sinoptico)
        self.assertEqual(sinoptico.count('Leche cruda'), 1)
        cursograma = cursograma_analitico(datos)
        self.assertEqual(len(cursograma['filas']), 11)
        self.assertEqual(cursograma['resumen']['operacion']['cantidad'], 6)
        self.assertEqual(cursograma['resumen']['transporte']['distancia_m'], '25')
        self.assertEqual(cursograma['total_min'], 1830)
        # ASME: la espera declarada dentro de cualquier etapa se suma a las demoras.
        demoras = sum(e['duracion_min'] for e in datos['etapas'] if e['tipo'] == 'espera') + sum(
            e['espera_min'] for e in datos['etapas'])
        self.assertEqual(cursograma['resumen']['espera']['tiempo_min'], demoras)
        self.assertEqual(cursograma['total_distancia_m'], '25')
        self.assertEqual([item['simbolo'] for item in cursograma['resumen_por_tipo']], ['○', '□', '⇨', 'D', '▽'])
        self.assertIn('PCC: Temperatura y tiempo de pasteurización', cursograma['filas'][1]['observacion'])


class ElCatalogoCompletoDeLacteosTests(BasePlantaProduce):
    """Todo lo que una planta de lácteos hace, con su proceso completo."""

    def test_las_ocho_recetas_tienen_proceso_completo_y_software(self):
        recetas = {receta.codigo: receta for receta in Receta.objects.filter(unidad=self.unidad, origen='referencia').prefetch_related('etapas', 'software')}
        self.assertEqual(set(recetas), {
            'LAC-REC-LECHE-100', 'LAC-REC-YOGUR-100', 'LAC-REC-QUESO-100', 'LAC-REC-MOZZARELLA-100',
            'LAC-REC-SEMIMADURO-100', 'LAC-REC-MANTEQUILLA-20', 'LAC-REC-MANJAR-50', 'LAC-REC-CREMA-100',
            'LAC-REC-HELADO-30', 'LAC-REC-RICOTTA-100', 'LAC-REC-BEBIDA-SUERO-100',
        })
        for codigo, receta in recetas.items():
            with self.subTest(receta=codigo):
                etapas = list(receta.etapas.order_by('orden'))
                self.assertGreaterEqual(len(etapas), 8)
                # Todo proceso empieza controlando lo que entra y termina limpiando la línea.
                self.assertEqual(etapas[0].tipo, 'inspeccion')
                self.assertTrue(etapas[0].punto_critico or etapas[0].punto_control)
                # Codex: todo proceso identifica al menos un PCC de inocuidad.
                self.assertTrue(any(etapa.punto_critico for etapa in etapas))
                self.assertFalse(any(etapa.punto_critico and etapa.punto_control for etapa in etapas))
                self.assertTrue(etapas[-1].nombre.startswith('Limpieza'))
                self.assertTrue(etapas[-1].salidas.filter(producto__codigo='LAC-PRD-AGUA-LAVADO').exists())
                self.assertIn('LAC-SW-TRAZA', [programa.codigo for programa in receta.software.all()])
                # El balance de masa por etapas cierra cerca del rendimiento declarado.
                balance = balance_de_masa(datos_de_receta(receta))
                self.assertLess(abs(Decimal(balance['diferencia'])), Decimal('0.5'), balance)
                self.assertFalse(any(fila['exceso'] for fila in balance['filas']), balance['filas'])
        # Los equipos nuevos de la planta existen y la caldera también apoya a la marmita.
        for codigo in ('LAC-EQ-MARMITA', 'LAC-EQ-HILADORA', 'LAC-EQ-MANTEQUILLERA', 'LAC-EQ-MADURACION'):
            with self.subTest(equipo=codigo):
                self.assertEqual(EquiposServicios.objects.get(codigo=codigo).rol, 'principal')
        caldera = EquiposServicios.objects.get(codigo='LAC-EQ-CALDERA')
        self.assertIn('LAC-EQ-MARMITA', caldera.apoya_a.values_list('codigo', flat=True))
        # Los productos de los cuatro tipos y el intermedio que vuelve a entrar.
        tipos = dict(Producto.objects.filter(unidad=self.unidad).values_list('codigo', 'tipo'))
        self.assertEqual(tipos['LAC-PRD-MOZZARELLA'], 'terminado')
        self.assertEqual(tipos['LAC-PRD-MAZADA'], 'subproducto')
        self.assertEqual(tipos['LAC-PRD-LECHE-DESCREMADA'], 'intermedio')
        self.assertEqual(tipos['LAC-PRD-AGUA-EVAPORADA'], 'residuo')
        self.assertEqual(Consumible.objects.get(codigo='LAC-INS-CREMA').stock_total, Decimal('0.000'))
        # La guía toma el software del proceso.
        guia = guia_desde_proceso(datos_de_receta(recetas['LAC-REC-YOGUR-100']))
        self.assertEqual(guia['software'], ['Registro de trazabilidad de lotes', 'Simulador de balance de materia y energía'])
        self.assertTrue(any('Pulpa de mora' in item for item in guia['materiales']))

    def test_un_intermedio_vuelve_a_entrar_como_insumo_de_la_misma_planta(self):
        from datetime import timedelta

        from apps.recursos.models.consumibles import LoteConsumible
        from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto

        crema = Producto.objects.get(codigo='LAC-PRD-CREMA')
        lote = LoteProducto.objects.create(
            unidad=self.unidad, producto=crema, codigo=f'LAC-PRD-CREMA-{self.hoy:%y%m%d}-01',
            cantidad_inicial=Decimal('16'), cantidad_disponible=Decimal('16'),
            fecha_produccion=self.hoy, fecha_vencimiento=self.hoy + timedelta(days=10),
            estado='disponible', control_calidad='no_aplica',
        )
        insumo = Consumible.objects.get(codigo='LAC-INS-CREMA')
        respuesta = self.operar(
            modulo='movimiento_producto', lote_id=lote.pk, tipo='consumo_interno', cantidad='15',
            consumible_destino_id=insumo.pk, referencia='Corrida de mantequilla',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        movimiento = MovimientoProducto.objects.get(lote=lote, tipo='consumo_interno')
        self.assertIn('Inventario de la planta', movimiento.destino)
        self.assertIsNone(movimiento.unidad_destino)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_disponible, Decimal('1.000'))
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_total, Decimal('15.000'))
        recibido = LoteConsumible.objects.get(codigo=f'{lote.codigo}-INT')
        self.assertEqual(recibido.consumible, insumo)
        self.assertEqual(recibido.estado, 'bodega')
        self.assertEqual(recibido.fecha_vencimiento, self.hoy + timedelta(days=10))
        self.assertEqual(movimiento.entrada_destino.unidad, self.unidad)
        # Un insumo de otra unidad no recibe un consumo interno.
        otra = Unidad.objects.create(
            nombre='Otra planta', descripcion='.', fecha_inicio='2026-01-01',
            dependencia='plantas_piloto', slug='otra-planta-prueba-interno',
        )
        ajeno = Consumible.objects.create(
            unidad=otra, codigo='OTRA-INS', nombre='Insumo ajeno', clasificacion='insumo',
            unidad_medida='litro', cantidad_por_presentacion=Decimal('1'),
        )
        rechazo = self.operar(
            modulo='movimiento_producto', lote_id=lote.pk, tipo='consumo_interno', cantidad='1',
            consumible_destino_id=ajeno.pk,
        )
        self.assertEqual(rechazo.status_code, 404)


class ElPanelGuardaEtapasTests(BasePlantaProduce):
    def test_la_marca_externa_se_guarda_se_reabre_y_se_puede_retirar(self):
        import json
        from apps.plantas_piloto.operacion.presentation.gestion_produccion import _lineas_json

        respuesta = self._receta_nueva(salida_externa_al_flujo=['si'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        receta = Receta.objects.get(codigo='LAC-REC-PRUEBA')
        self.assertTrue(receta.salidas.get().externa_al_flujo)
        self.assertEqual(json.loads(_lineas_json(receta))['salidas'][0]['externa_al_flujo'], 'si')
        self.assertTrue(datos_de_receta(receta)['etapas'][1]['salidas'][0]['externa_al_flujo'])
        respuesta = self._receta_nueva(registro_id=receta.pk, salida_externa_al_flujo=['no'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertFalse(receta.salidas.get().externa_al_flujo)

    def _receta_nueva(self, **extra):
        tanque = EquiposServicios.objects.get(codigo='LAC-EQ-TANQUE')
        pasteur = EquiposServicios.objects.get(codigo='LAC-EQ-PASTEUR')
        recepcion = EspacioReservable.objects.get(codigo='LAC-AREA-RECEPCION')
        linea = EspacioReservable.objects.get(codigo='LAC-LINEA-PROCESO')
        crema = Producto.objects.get(codigo='LAC-PRD-CREMA')
        datos = {
            'modulo': 'receta',
            'producto_id': Producto.objects.get(codigo='LAC-PRD-LECHE-PAST').pk,
            'codigo': 'LAC-REC-PRUEBA',
            'nombre': 'Leche pasteurizada de prueba por 50 litros',
            'cantidad_base': '50',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '47',
            'duracion_horas': '1.5',
            'activa': 'on',
            'etapa_nombre': ['Recepción', 'Pasteurización', ''],
            'etapa_tipo': ['inspeccion', 'operacion', 'operacion'],
            'etapa_equipo': [str(tanque.pk), str(pasteur.pk), ''],
            'etapa_espacio': [str(recepcion.pk), str(linea.pk), ''],
            'etapa_duracion': ['10', '30', '0'],
            'etapa_espera': ['0', '0', '0'],
            'etapa_personas': ['2', '1', '1'],
            'etapa_rendimiento': ['100', '97', '100'],
            'etapa_distancia': ['0', '0', '0'],
            'etapa_punto_critico': ['si', 'si', 'no'],
            'etapa_parametro': ['Acidez', 'Temperatura', ''],
            'etapa_limite': ['14 a 18 °D', '72 °C por 15 s', ''],
            'etapa_instrucciones': ['Filtrar y muestrear.', '', ''],
            'insumo_consumible': [str(Consumible.objects.get(codigo='LAC-INS-LECHE').pk)],
            'insumo_cantidad': ['50'],
            'insumo_obligatorio': ['si'],
            'insumo_etapa': ['1'],
            'salida_producto': [str(crema.pk)],
            'salida_cantidad': ['1.5'],
            'salida_etapa': ['2'],
            'software': [str(SoftwareDisponible.objects.get(codigo='LAC-SW-TRAZA', unidad=self.unidad).pk)],
        }
        datos.update(extra)
        return self.operar(**datos)

    def test_las_filas_de_etapas_se_guardan_en_orden_y_asignan_insumos_y_salidas(self):
        respuesta = self._receta_nueva()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        receta = Receta.objects.get(codigo='LAC-REC-PRUEBA')
        etapas = list(receta.etapas.order_by('orden'))
        # La tercera fila iba vacía: no es una etapa.
        self.assertEqual([etapa.nombre for etapa in etapas], ['Recepción', 'Pasteurización'])
        self.assertEqual(etapas[0].tipo, 'inspeccion')
        self.assertEqual(etapas[1].equipo.codigo, 'LAC-EQ-PASTEUR')
        self.assertEqual(etapas[1].rendimiento_pct, Decimal('97.00'))
        self.assertTrue(etapas[1].punto_critico)
        self.assertEqual(receta.insumos.get().etapa, etapas[0])
        self.assertEqual(receta.salidas.get().etapa, etapas[1])
        self.assertEqual(receta.software.get().codigo, 'LAC-SW-TRAZA')
        # Al editar con una sola etapa, la segunda desaparece y la salida queda sin etapa.
        edicion = self._receta_nueva(
            registro_id=receta.pk,
            etapa_nombre=['Recepción'], etapa_tipo=['inspeccion'],
            etapa_equipo=[str(etapas[0].equipo_id)], etapa_espacio=[str(etapas[0].espacio_id)],
            etapa_duracion=['10'], etapa_espera=['0'], etapa_personas=['2'], etapa_rendimiento=['100'],
            etapa_distancia=['0'], etapa_punto_critico=['si'], etapa_parametro=['Acidez'],
            etapa_limite=['14 a 18 °D'], etapa_instrucciones=[''], salida_etapa=[''],
        )
        self.assertEqual(edicion.status_code, 200, edicion.content)
        self.assertEqual(receta.etapas.count(), 1)
        self.assertIsNone(receta.salidas.get().etapa)

    def test_las_etapas_se_validan(self):
        sin_parametro = self._receta_nueva(etapa_parametro=['', 'Temperatura', ''])
        self.assertEqual(sin_parametro.status_code, 400)
        self.assertIn('punto crítico', sin_parametro.json()['error'].lower())
        self.assertFalse(Receta.objects.filter(codigo='LAC-REC-PRUEBA').exists())
        etapa_inexistente = self._receta_nueva(insumo_etapa=['7'])
        self.assertEqual(etapa_inexistente.status_code, 400)
        self.assertIn('etapa 7', etapa_inexistente.json()['error'])
        otra_unidad = Unidad.objects.create(
            nombre='Otra planta', descripcion='.', fecha_inicio='2026-01-01',
            dependencia='plantas_piloto', slug='otra-planta-prueba',
        )
        ajeno = EspacioReservable.objects.create(unidad=otra_unidad, codigo='OTRA-AREA', nombre='Área ajena', tipo='area', capacidad=5)
        espacio_ajeno = self._receta_nueva(etapa_espacio=[str(ajeno.pk), '', ''])
        self.assertEqual(espacio_ajeno.status_code, 400)
        self.assertIn('no pertenece', espacio_ajeno.json()['error'])
        excesivo = self._receta_nueva(etapa_rendimiento=['100', '120', '100'])
        self.assertEqual(excesivo.status_code, 400)
        self.assertIn('100', excesivo.json()['error'])

    def test_la_pestana_muestra_el_proceso_de_cada_receta(self):
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]) + '?view=produccion')
        self.assertEqual(panel.status_code, 200)
        self.assertContains(panel, 'Etapas, tiempos y diagrama de cada receta')
        self.assertContains(panel, 'aria-label="Diagrama de flujo del proceso: Queso fresco"')
        self.assertContains(panel, reverse('ficha_proceso', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertContains(panel, 'data-recipe-template="etapas"')
        self.assertContains(panel, 'name="insumo_etapa"')
        # Las filas de edición llevan las etapas para que el cajón las rearme.
        self.assertContains(panel, '&quot;etapas&quot;: [{&quot;nombre&quot;: &quot;Recepci')

    # La planta parte de un proceso predefinido, lo ajusta y lo guarda como su versión.
    def test_guardar_como_version_no_toca_el_original(self):
        self.assertEqual(self._receta_nueva().status_code, 200)
        original = Receta.objects.get(codigo='LAC-REC-PRUEBA')
        respuesta = self._receta_nueva(
            registro_id=original.pk, guardar_como='version', etapa_duracion=['10', '45', '0'],
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        version = Receta.objects.get(codigo='LAC-REC-PRUEBA-V1')
        self.assertEqual(version.origen, 'derivado')
        self.assertEqual(version.derivado_de, original)
        self.assertIn('versión de la planta', version.nombre)
        self.assertEqual(version.etapas.get(orden=2).duracion_min, 45)
        self.assertEqual(original.etapas.get(orden=2).duracion_min, 30)
        # La planta revisa su versión y la marca validada.
        self._receta_nueva(
            registro_id=version.pk, codigo=version.codigo, nombre=version.nombre, origen='validado',
        )
        version.refresh_from_db()
        self.assertEqual(version.origen, 'validado')


class LaFichaElReporteYLaGuiaTests(BasePlantaProduce):
    def test_la_ficha_de_proceso_se_consulta_desde_el_panel_y_no_desde_fuera(self):
        url = reverse('ficha_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        self.client.force_login(self.coordinacion)
        ficha = self.client.get(url)
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, 'Ficha de proceso')
        self.assertContains(ficha, 'CURSOGRAMA ANALÍTICO')
        self.assertContains(ficha, 'BALANCE DE MASA')
        self.assertContains(ficha, 'Diagrama sinóptico')
        self.assertContains(ficha, '13.86')
        self.assertContains(ficha, '1830 min')
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_el_reporte_de_procesos_sale_en_html_y_hoja_de_calculo(self):
        self.client.force_login(self.coordinacion)
        consulta = '?categoria_reporte=procesos'
        html = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]) + consulta)
        self.assertEqual(html.status_code, 200)
        self.assertContains(html, 'Pasteurización')
        self.assertContains(html, 'Temperatura y tiempo de pasteurización (65 °C durante 30 minutos)')
        self.assertContains(html, 'Leche cruda 100 litro')
        xlsx = self.client.get(reverse('gestion_reporte_unidad_xlsx', args=[self.unidad.slug]) + consulta + '&estado=inspeccion')
        self.assertEqual(xlsx.status_code, 200)
        with ZipFile(BytesIO(xlsx.content)) as libro:
            contenido = b''.join(libro.read(nombre) for nombre in libro.namelist() if nombre.endswith('.xml'))
        self.assertIn('Recepción y control de la leche'.encode(), contenido)
        self.assertNotIn('Prensado'.encode(), contenido)

    def test_la_guia_toma_equipos_materiales_y_procedimiento_del_proceso(self):
        datos = guia_desde_proceso(datos_de_receta(self.receta_queso))
        self.assertIn('Pasteurizador por lotes', datos['equipos'])
        self.assertTrue(any('(auxiliar)' in equipo for equipo in datos['equipos']))
        self.assertIn('Leche cruda: 100 litro (etapa 1)', datos['materiales'])
        self.assertIn('<ol class="guide-steps">', datos['procedimiento_html'])
        self.assertIn('Pasteurización', datos['procedimiento_html'])
        self.assertIn('65 °C durante 30 minutos', datos['seguridad_html'])
        self.assertIn('12 kg', datos['resultados_html'])
        self.assertIn('h', datos['duracion'])

        self.client.force_login(self.docente)
        json_url = reverse('guia_desde_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        respuesta = self.client.get(json_url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['proceso'], 'Queso fresco')
        editor = self.client.get(reverse('nueva_guia_practica', args=[self.unidad.slug]))
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, 'Tomar del proceso')
        self.assertContains(editor, json_url)
        self.assertContains(editor, 'Queso fresco → Queso fresco · 11 etapas')
        # Un laboratorio sin producción no ofrece procesos en su editor.
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin producción', descripcion='.', fecha_inicio='2026-01-01',
            dependencia='laboratorios', slug='laboratorio-sin-produccion', administrador=self.coordinacion,
        )
        editor_lab = self.client.get(reverse('nueva_guia_practica', args=[laboratorio.slug]))
        self.assertEqual(editor_lab.status_code, 200)
        self.assertNotContains(editor_lab, 'Tomar del proceso')
