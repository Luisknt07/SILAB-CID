"""Aula y simuladores: las funciones de la planta en el visor público de su ficha.

La ficha publica los sistemas de producción (línea → proceso) con la ficha de
cada proceso, los simuladores que corren sobre los motores reales (balance
de materia y energía, balance de línea, requerimiento de materiales) y los
protocolos de control. Un simulador toma los datos de una reserva o de una
programación, o corre libre.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.formacion.presentation.aula import carpetas_del_aula, lineas_de_procesos, procesos_publicos
from apps.plantas_piloto.operacion.presentation.motores import balance_de_energia, balance_de_linea, requerimiento_de_materiales
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
from apps.plantas_piloto.operacion.management.plantas.taxonomia import PRODUCTOS_TAXONOMIA
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, Producto, Receta
from apps.reservas.models.reservas import ProgramacionReserva
from apps.recursos.models.software import SoftwareDisponible
from tests.integration.test_programacion_asignatura import BaseProgramacion
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class ElAulaEnLaFichaTests(BasePracticaPorProceso):
    def test_el_arbol_muestra_completo_el_mapa_hasta_produccion(self):
        # El mapa completo, con las secciones pendientes, lo ve quien gestiona la planta.
        self.client.force_login(get_user_model().objects.create_superuser('gestor.mapa', 'g@example.org', 'clave'))
        respuesta = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()

        def modulo(clave):
            desde = html.rindex(f'data-modulo="{clave}"')
            hasta = html.find('class="modulo-carpeta-list', desde)
            return html[desde:hasta if hasta > 0 else None]

        esperadas = {
            'informacion-general': [f'1.{numero}' for numero in range(1, 6)],
            'procesos-protocolos': [f'2.{numero}' for numero in range(1, 7)],
            'equipos-infraestructura': [f'3.{numero}' for numero in range(1, 5)],
            'produccion-lotes': [f'4.{numero}' for numero in range(1, 7)],
        }
        for clave, numeros in esperadas.items():
            contenido = modulo(clave)
            posiciones = [contenido.index(f'data-seccion="{numero}"') for numero in numeros]
            self.assertEqual(posiciones, sorted(posiciones), clave)
        self.assertContains(respuesta, 'La planta por dentro')
        self.assertContains(respuesta, 'Normativa y marco sanitario')
        self.assertContains(respuesta, 'Repositorio y descargas')
        self.assertContains(respuesta, 'Contenido pendiente de publicación por la unidad.')
        self.assertContains(respuesta, 'Matriz de materiales e insumos')
        self.assertContains(respuesta, 'Métodos, tiempos y secuencia')
        self.assertContains(respuesta, 'Ruta del saber y documentación técnica')
        self.assertContains(respuesta, 'Repositorio institucional')
        # 4.2 ya no es un aviso: lleva la ficha técnica de cada producto.
        self.assertContains(respuesta, 'data-id="ficha-producto-')

    def test_el_arbol_abre_una_seccion_y_una_familia_a_la_vez(self):
        modulos = list(self.unidad.modulos_contenido.filter(activo=True).order_by('orden', 'id'))
        carpetas = carpetas_del_aula(self.unidad, modulos, procesos_publicos(self.unidad))
        claves = {carpeta['modulo'] for carpeta in carpetas}
        for clave in claves:
            self.assertEqual(sum(carpeta['abierta'] for carpeta in carpetas if carpeta['modulo'] == clave), 1)
        for carpeta in carpetas:
            self.assertEqual(sum(grupo['abierta'] for grupo in carpeta['grupos']), 1)
        por_id = {carpeta['id']: carpeta for carpeta in carpetas}
        self.assertEqual(por_id['SimuladoresProceso']['total'], 3)
        self.assertNotIn('DocumentacionProcesos', por_id)

    def test_la_ficha_publica_los_sistemas_de_produccion_con_sus_fichas_y_simuladores(self):
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'Sistemas de producción')
        self.assertContains(ficha, 'Quesos')
        self.assertContains(ficha, 'Leches y fermentados')
        self.assertContains(ficha, f'data-id="ficha-proceso-{self.receta_queso.pk}"')
        self.assertContains(ficha, 'data-id="simulador-balance"')
        self.assertNotContains(ficha, f'data-id="simulador-balance-{self.receta_queso.pk}"')
        self.assertNotContains(
            ficha,
            reverse('simulador_balance', args=[self.unidad.slug]) + f'?receta={self.receta_queso.pk}',
        )
        self.assertContains(ficha, 'data-id="simulador-linea"')
        self.assertContains(ficha, 'data-id="simulador-materiales"')
        self.assertContains(ficha, 'data-id="indice-materiales-insumos"')
        self.assertContains(ficha, 'data-id="indice-metodos-tiempos"')
        self.assertContains(ficha, 'data-id="ruta-saber-documentacion"')
        self.assertContains(ficha, 'data-target="#collapseSistemasProduccion"')
        self.assertContains(ficha, 'data-target="#collapseSistemasProduccionGrupo1"')
        self.assertContains(ficha, 'data-id="protocolos-control-LAC-F02"')
        self.assertContains(ficha, 'data-id="produccion-planta"')
        self.assertContains(ficha, 'data-id="calidad-lotes-LAC-F02"')
        self.assertContains(ficha, 'data-id="calidad-transversal"')
        self.assertContains(ficha, 'data-id="area-')
        # Cada pestaña recibe lo suyo: procesos, producción, calidad y equipos.
        html = ficha.content.decode()
        def modulo(clave):
            # La pestaña de navegación lleva el mismo data-modulo; el acordeón es la última aparición.
            desde = html.rindex(f'data-modulo="{clave}"')
            hasta = html.find('class="modulo-carpeta-list', desde)
            return html[desde:hasta if hasta > 0 else None]
        self.assertIn('ficha-proceso-', modulo('procesos-protocolos'))
        self.assertIn('simulador-balance', modulo('procesos-protocolos'))
        self.assertNotIn('simulador-linea', modulo('procesos-protocolos'))
        self.assertNotIn('simulador-materiales', modulo('procesos-protocolos'))
        self.assertIn('simulador-materiales', modulo('produccion-lotes'))
        self.assertIn('produccion-planta', modulo('produccion-lotes'))
        self.assertIn('corridas-lotes', modulo('produccion-lotes'))
        self.assertNotIn('No hay carpetas disponibles', modulo('produccion-lotes'))
        self.assertIn('protocolos-control', modulo('calidad-inocuidad'))
        self.assertIn('calidad-lotes', modulo('calidad-inocuidad'))
        self.assertIn('data-id="area-', modulo('equipos-infraestructura'))
        self.assertIn('simulador-linea', modulo('equipos-infraestructura'))
        self.assertIn('ficha-equipo-', modulo('equipos-infraestructura'))
        self.assertContains(ficha, reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        # 2.1 conserva los procesos validados y completa la taxonomía con las
        # fichas de producto cuyo proceso técnico aún está por configurar.
        self.assertEqual(html.count('data-id="ficha-proceso-'), len(procesos_publicos(self.unidad)))
        arequipe = Producto.objects.get(unidad=self.unidad, nombre='Arequipe')
        self.assertContains(ficha, f'data-id="ficha-producto-{arequipe.pk}"')
        self.assertContains(ficha, reverse(
            'ficha_producto_publica', args=[self.unidad.slug, arequipe.pk],
        ))
        for familia, referencias in PRODUCTOS_TAXONOMIA['LAC'].items():
            self.assertContains(ficha, familia)
            for nombre, _unidad_medida in referencias:
                producto = Producto.objects.get(unidad=self.unidad, nombre=nombre)
                if not Receta.objects.filter(unidad=self.unidad, producto=producto).exists():
                    self.assertContains(ficha, f'data-id="ficha-producto-{producto.pk}"')
        catalogo = self.client.get(reverse('produccion_publica', args=[self.unidad.slug]))
        for referencias in PRODUCTOS_TAXONOMIA['LAC'].values():
            for nombre, _unidad_medida in referencias:
                with self.subTest(producto=nombre):
                    producto = Producto.objects.get(unidad=self.unidad, nombre=nombre)
                    self.assertContains(catalogo, nombre)
                    self.assertContains(
                        catalogo,
                        reverse('ficha_producto_publica', args=[self.unidad.slug, producto.pk]),
                    )
        ficha_arequipe = self.client.get(
            reverse('ficha_producto_publica', args=[self.unidad.slug, arequipe.pk])
        )
        self.assertEqual(ficha_arequipe.status_code, 200)
        self.assertContains(ficha_arequipe, 'Arequipe')
        # El arequipe parte del proceso del manjar: se ofrece como derivado, por validar.
        self.assertContains(ficha_arequipe, 'proceso derivado de manjar de leche, por validar')
        self.assertContains(ficha_arequipe, 'Ver el documento')
        # El suero en polvo necesita un equipo que la planta no tiene: queda sin proceso.
        suero_polvo = Producto.objects.get(unidad=self.unidad, nombre='Suero en polvo')
        ficha_suero = self.client.get(reverse('ficha_producto_publica', args=[self.unidad.slug, suero_polvo.pk]))
        self.assertContains(ficha_suero, 'Su receta, balance, capacidad y documentación técnica')
        producto_queso = self.client.get(
            reverse('ficha_producto_publica', args=[self.unidad.slug, self.receta_queso.producto_id])
        )
        self.assertEqual(producto_queso.status_code, 200)
        self.assertContains(producto_queso, 'Abrir proceso técnico')
        self.assertContains(
            producto_queso,
            reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]),
        )
        lineas = lineas_de_procesos(procesos_publicos(self.unidad))
        self.assertEqual([linea['nombre'] for linea in lineas], [
            'Leches y fermentados', 'Quesos', 'Cremas y mantequilla', 'Dulces de leche', 'Helados',
            'Derivados del suero',
        ])
        # El queso maduro se ofrece como derivado del semimaduro, junto a los tres de referencia.
        self.assertEqual(
            sorted(receta.codigo for receta in next(linea for linea in lineas if linea['nombre'] == 'Quesos')['procesos']),
            ['LAC-REC-DER-CAT-02-04', 'LAC-REC-MOZZARELLA-100', 'LAC-REC-QUESO-100', 'LAC-REC-SEMIMADURO-100'],
        )
        # La ficha del proceso, pública, con sus diagramas y sin la barra del panel.
        pagina = self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Diagrama de flujo')
        self.assertContains(pagina, 'CURSOGRAMA ANALÍTICO')
        self.assertContains(pagina, 'Volver a la unidad')
        self.assertNotContains(pagina, 'Volver a producción')
        self.assertContains(pagina, 'Balance de materia y energía')
        self.assertContains(pagina, 'Documentación técnica')
        self.assertContains(pagina, 'Capacidad y equilibrado')
        self.assertContains(pagina, 'Ficha del producto')
        self.assertContains(pagina, 'class="accion-proceso is-active"')
        self.assertContains(pagina, self.receta_queso.nombre_publico)
        self.assertNotContains(pagina, self.receta_queso.nombre)
        # El visor las carga en un iframe del mismo origen: el servidor debe permitirlo.
        self.assertEqual(pagina['X-Frame-Options'], 'SAMEORIGIN')
        for nombre in ('materiales_insumos', 'metodos_tiempos', 'ruta_saber_documentacion', 'simulador_balance', 'simulador_linea', 'simulador_materiales', 'protocolos_control', 'produccion_publica', 'corridas_lotes_publicos', 'calidad_publica', 'areas_equipos'):
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre, args=[self.unidad.slug]))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, 999999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('simulador_balance', args=['unidad-que-no-existe'])).status_code, 404)
        # Los simuladores son software propio de acceso remoto, ligado a sus procesos.
        self.assertEqual(SoftwareDisponible.objects.get(unidad=self.unidad, codigo='LAC-SW-LINEA').tipo_acceso, 'remoto')
        self.assertIn('LAC-SW-LINEA', [programa.codigo for programa in self.receta_queso.software.all()])
        yogur = Receta.objects.get(codigo='LAC-REC-YOGUR-100')
        self.assertIn('LAC-SW-BALANCE', [programa.codigo for programa in yogur.software.all()])
        familia_quesos = Producto.objects.get(codigo='LAC-PRD-QUESO-FRESCO').familia
        self.assertEqual(familia_quesos.nombre, 'Quesos')
        # El panel registra la línea de producción de un producto.
        respuesta = self.operar(
            modulo='producto', codigo='LAC-PRD-RICOTA', nombre='Ricota', tipo='terminado', unidad_medida='kg',
            presentacion='', precio_venta='0', vida_util_dias='10', familia_id=familia_quesos.pk,
            activo='on', publico='on',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(Producto.objects.get(codigo='LAC-PRD-RICOTA').familia, familia_quesos)

    def test_las_tres_primeras_pestanas_usan_las_secciones_del_nuevo_mapa(self):
        # El mapa completo, con las secciones pendientes, lo ve quien gestiona la planta.
        self.client.force_login(get_user_model().objects.create_superuser('gestor.mapa', 'g@example.org', 'clave'))
        ficha = self.client.get(self.unidad.get_absolute_url())

        for numero, titulo in (
            ('1.1', 'Presentación'),
            ('1.2', 'La unidad'),
            ('2.1', 'Sistemas de producción'),
            ('2.4', 'Simuladores y cálculo del proceso'),
            ('3.1', 'Áreas y equipos'),
            ('3.2', 'Fichas de equipo'),
            ('3.4', 'Capacidad, cuellos de botella y equilibrado'),
        ):
            with self.subTest(seccion=numero):
                self.assertContains(ficha, numero)
                self.assertContains(ficha, titulo)

        self.assertContains(ficha, 'data-seccion="2.2"')
        self.assertContains(ficha, 'data-seccion="2.3"')
        self.assertContains(ficha, 'data-seccion="2.5"')
        self.assertContains(ficha, 'data-seccion="3.3"')
        self.assertNotContains(ficha, 'Todavía sin contenido')
        self.assertNotContains(ficha, 'Navegación del módulo')
        self.assertNotContains(ficha, 'id="modulo-titulo"')

    def test_el_acceso_antiguo_de_simuladores_llega_a_la_seccion_2_4(self):
        respuesta = self.client.get(
            reverse('simuladores_proceso_legacy', args=[self.unidad.slug])
        )

        self.assertEqual(respuesta.status_code, 301)
        self.assertEqual(
            respuesta['Location'],
            f'{self.unidad.get_absolute_url()}?recurso=simulador-balance#procesos-protocolos',
        )

    def test_el_balance_de_materia_y_energia_toma_los_datos_de_la_reserva(self):
        respuesta = self.reservar(self.carga_docencia(self.seleccion('2')))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva_id = respuesta.json()['reserva_id']
        url = reverse('simulador_balance', args=[self.unidad.slug])
        libre = self.client.get(url)
        self.assertContains(libre, 'Balance de materia y energía')
        self.assertContains(libre, 'name="cantidad"')
        self.assertNotContains(libre, 'DATOS DE LA RESERVA')
        # Con la reserva: el queso fresco a 200 litros, que es lo que se pidió.
        con_reserva = self.client.get(f'{url}?reserva={reserva_id}')
        self.assertContains(con_reserva, 'DATOS DE LA RESERVA')
        self.assertContains(con_reserva, 'value="200"')
        self.assertContains(con_reserva, f'<option value="{self.receta_queso.pk}" selected')
        self.assertContains(con_reserva, 'name="reserva" value="' + str(reserva_id) + '"')
        # El comprobante lleva al aula con los datos ya cargados.
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva_id]))
        self.assertContains(comprobante, 'Aula: simula con los datos de esta solicitud')
        self.assertContains(comprobante, f'{url}?reserva={reserva_id}')
        # Quien no participa no ve la reserva: el simulador corre libre.
        self.client.force_login(self.estudiante)
        ajeno = self.client.get(f'{url}?reserva={reserva_id}')
        self.assertEqual(ajeno.status_code, 200)
        self.assertNotContains(ajeno, 'DATOS DE LA RESERVA')
        self.client.logout()
        anonimo = self.client.get(
            f'{url}?reserva={reserva_id}&receta={self.receta_queso.pk}&cantidad=50'
            '&t_inicial=4&t_proceso=65&t_final=4&eficiencia=80&potencia_kw=10'
        )
        self.assertEqual(anonimo.status_code, 200)
        self.assertNotContains(anonimo, 'DATOS DE LA RESERVA')
        self.assertContains(anonimo, '12346 kJ')
        # 50 litros pesan 51.5 kg; calentar 61 K pide 12 346 kJ útiles, 15 433 kJ al 80 %.
        energia = balance_de_energia(
            datos_de_receta(self.receta_queso, Decimal('0.5')),
            t_inicial=Decimal('4'), t_proceso=Decimal('65'), t_final=Decimal('4'),
            eficiencia=Decimal('0.8'), potencia_kw=Decimal('10'),
        )
        self.assertEqual(energia['masa_kg'], '51.5')
        self.assertEqual(energia['calor_util_kj'], '12346')
        self.assertEqual(energia['calor_suministrado_kj'], '15433')
        self.assertEqual(energia['calor_kwh'], '4.29')
        self.assertEqual(energia['vapor_kg'], '6.8')
        self.assertEqual(energia['frio_kwh'], '1.37')
        self.assertEqual(energia['minutos'], '26')

    def test_el_balance_de_linea_y_el_requerimiento_de_materiales(self):
        url = reverse('simulador_linea', args=[self.unidad.slug])
        pagina = self.client.get(f'{url}?receta={self.receta_queso.pk}&corridas=2&jornada=8')
        self.assertContains(pagina, 'Cuello de botella')
        self.assertContains(pagina, '240 min')
        etapas = list(self.receta_queso.etapas.all())
        linea = balance_de_linea(datos_de_receta(self.receta_queso), corridas=Decimal('2'), jornada_min=Decimal('480'))
        self.assertEqual(linea['takt'], '240')
        self.assertEqual(linea['trabajo_total'], sum(etapa.duracion_min for etapa in etapas))
        self.assertEqual(linea['cuello']['trabajo'], max(etapa.duracion_min for etapa in etapas))
        self.assertGreaterEqual(linea['numero_estaciones'], linea['estaciones_minimas'])
        self.assertEqual(sum(len(estacion['etapas']) for estacion in linea['estaciones']), len(etapas))
        self.assertEqual(linea['capacidad'], 480 // max(etapa.duracion_min for etapa in etapas))
        # Materiales: dos procesos contra el inventario de la planta.
        yogur = Receta.objects.get(codigo='LAC-REC-YOGUR-100')
        url = reverse('simulador_materiales', args=[self.unidad.slug])
        pagina = self.client.get(f'{url}?cantidad_{self.receta_queso.pk}=200&cantidad_{yogur.pk}=100')
        self.assertContains(pagina, 'Requerimiento de materiales')
        self.assertContains(pagina, 'Pulpa de mora')
        self.assertContains(pagina, 'PLAN DE CORRIDAS')
        requerimiento = requerimiento_de_materiales([
            {'receta': self.receta_queso, 'factor': Decimal('2'), 'etiqueta': 'queso'},
            {'receta': yogur, 'factor': Decimal('1'), 'etiqueta': 'yogur'},
        ])
        esperado = {}
        for receta, factor in ((self.receta_queso, Decimal('2')), (yogur, Decimal('1'))):
            for item in receta.insumos_para(factor):
                nombre = item['consumible'].nombre
                esperado[nombre] = esperado.get(nombre, Decimal('0')) + item['cantidad']
        self.assertEqual({fila['nombre']: Decimal(fila['bruto']) for fila in requerimiento['filas']}, esperado)
        self.assertEqual(requerimiento['faltantes'], sum(1 for fila in requerimiento['filas'] if not fila['cubre']))
        self.assertEqual(requerimiento['corridas'], '3')
        self.assertTrue(any(salida['principal'] and salida['nombre'] == 'Queso fresco' for salida in requerimiento['salidas']))
        vacio = self.client.get(url)
        self.assertContains(vacio, 'Calcular el requerimiento')
        self.assertNotContains(vacio, 'PLAN DE CORRIDAS')

    def test_los_protocolos_de_control_listan_los_puntos_criticos(self):
        pagina = self.client.get(reverse('protocolos_control', args=[self.unidad.slug]))
        self.assertContains(pagina, 'Protocolos de control')
        self.assertContains(pagina, self.receta_queso.nombre_publico.upper())
        primera = self.receta_queso.etapas.order_by('orden').first()
        # El protocolo abarca los PCC (inocuidad) y los PC (calidad), cada uno identificado.
        self.assertTrue(primera.punto_control)
        self.assertContains(pagina, primera.nombre)
        self.assertContains(pagina, 'PC · calidad')
        self.assertContains(pagina, 'PCC · inocuidad')


class ElAulaDeLaProgramacionTests(BaseProgramacion):
    def test_el_requerimiento_de_materiales_de_toda_la_programacion(self):
        leche = Receta.objects.get(codigo='LAC-REC-LECHE-100')
        yogur = Receta.objects.get(codigo='LAC-REC-YOGUR-100')
        fechas = [(self.martes + timedelta(days=7 * numero)).isoformat() for numero in range(3)]
        cronograma = json.dumps([
            {'fecha': fechas[0], 'tema': 'Recepción', 'tema_id': None, 'receta_id': None, 'cantidad': ''},
            {'fecha': fechas[1], 'tema': 'Leche', 'tema_id': None, 'receta_id': leche.pk, 'cantidad': '200'},
            {'fecha': fechas[2], 'tema': 'Yogur', 'tema_id': None, 'receta_id': yogur.pk, 'cantidad': '100'},
        ])
        respuesta = self.programar(cronograma=cronograma)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        programacion = ProgramacionReserva.objects.get(pk=respuesta.json()['programacion_id'])
        url = reverse('simulador_materiales', args=[self.unidad.slug])
        self.client.force_login(self.docente)
        pagina = self.client.get(f'{url}?programacion={programacion.pk}')
        self.assertContains(pagina, 'programación de 3 sesiones')
        self.assertContains(pagina, leche.nombre)
        self.assertContains(pagina, yogur.nombre)
        self.assertContains(pagina, 'Pulpa de mora')
        # Las sesiones programadas enlazan sus simuladores; la sesión sin proceso, no.
        lista = self.client.get(reverse('mis_sesiones', args=[self.unidad.slug]))
        self.assertContains(lista, 'Materiales del período')
        self.assertContains(lista, f'?programacion={programacion.pk}')
        segunda = self.sesiones_de(programacion)[1]
        sesion = self.client.get(reverse('completar_sesion', args=[segunda.pk]))
        self.assertContains(sesion, 'Simula con estos datos')
        self.assertContains(sesion, f'?reserva={segunda.pk}')
        # El estudiante participante también simula con los datos de su sesión.
        self.client.force_login(self.estudiante)
        del_estudiante = self.client.get(f"{reverse('simulador_balance', args=[self.unidad.slug])}?reserva={segunda.pk}")
        self.assertContains(del_estudiante, 'DATOS DE LA RESERVA')
        self.assertContains(del_estudiante, 'value="200"')


class LasPestanasDeLaPlantaTests(BasePracticaPorProceso):
    def test_produccion_calidad_y_areas_tienen_su_pagina(self):
        lote = LoteProducto.objects.create(
            unidad=self.unidad, producto=self.receta_queso.producto, codigo='LOTE-QF-PRUEBA',
            cantidad_inicial=Decimal('20'), cantidad_disponible=Decimal('12'), estado='disponible',
            control_calidad='aprobado', ubicacion='Cámara 1',
        )
        vencido = LoteProducto.objects.create(
            unidad=self.unidad, producto=self.receta_queso.producto, codigo='LOTE-QF-CUARENTENA',
            cantidad_inicial=Decimal('5'), cantidad_disponible=Decimal('5'), estado='cuarentena',
            control_calidad='pendiente',
        )
        produccion = self.client.get(reverse('produccion_publica', args=[self.unidad.slug]))
        self.assertContains(produccion, 'Lo que produce la planta')
        self.assertContains(produccion, 'QUESOS')
        self.assertContains(produccion, 'Queso fresco')
        self.assertEqual(
            produccion.context['produccion']['resumen']['productos'],
            Producto.objects.filter(
                unidad=self.unidad, activo=True, publico=True, tipo__in=Producto.TIPOS_PUBLICOS,
            ).count(),
        )
        for referencias in PRODUCTOS_TAXONOMIA['LAC'].values():
            for nombre, _unidad_medida in referencias:
                with self.subTest(producto=nombre):
                    producto = Producto.objects.get(unidad=self.unidad, nombre=nombre)
                    self.assertContains(produccion, nombre)
                    self.assertContains(
                        produccion,
                        reverse('ficha_producto_publica', args=[self.unidad.slug, producto.pk]),
                    )
        self.assertNotContains(produccion, lote.codigo)
        self.assertNotContains(produccion, vencido.codigo)
        self.assertNotContains(produccion, 'Cámara 1')
        actividad = self.client.get(reverse('corridas_lotes_publicos', args=[self.unidad.slug]))
        self.assertEqual(actividad.status_code, 200)
        self.assertContains(actividad, '0 corridas cerradas este mes · 1 lote vigente')
        self.assertNotContains(actividad, lote.codigo)
        self.assertNotContains(actividad, 'Cámara 1')
        ficha_publica = FichaContenido.objects.get(codigo='LAC-DOC-CORRIDAS-RESUMEN')
        ficha_interna = FichaContenido.objects.get(codigo='LAC-DOC-CORRIDAS-DETALLE')
        self.assertEqual(ficha_publica.visibilidad, 'publica')
        self.assertEqual(ficha_interna.visibilidad, 'interna')
        detalle_directo = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertEqual(detalle_directo.status_code, 302)
        calidad = self.client.get(reverse('calidad_publica', args=[self.unidad.slug]))
        self.assertContains(calidad, 'Calidad e inocuidad')
        # La 5.4 resume el control por producto; el detalle de cada lote queda en la consola.
        self.assertNotContains(calidad, vencido.codigo)
        fila = next(
            item for item in calidad.context['calidad']['por_producto']
            if item['producto__nombre'] == self.receta_queso.producto.nombre
        )
        self.assertEqual((fila['liberados'], fila['por_liberar']), (1, 1))
        self.assertContains(calidad, 'REQUISITOS PARA INGRESAR A LA UNIDAD')
        self.assertContains(calidad, self.receta_queso.nombre_publico)
        primera = self.receta_queso.etapas.order_by('orden').first()
        self.assertContains(calidad, primera.nombre)
        areas = self.client.get(reverse('areas_equipos', args=[self.unidad.slug]))
        self.assertContains(areas, 'Áreas y equipos de la unidad')
        self.assertContains(areas, 'Área de recepción de leche')
        # Cada tarjeta abre la página de su área, y ahí están sus equipos.
        for area in areas.context['infraestructura']['areas']:
            self.assertContains(areas, area['url'])
        con_equipos = next(area for area in areas.context['infraestructura']['areas'] if area['equipos'])
        self.assertContains(self.client.get(con_equipos['url']), con_equipos['equipos'][0].equipo.nombre)
        # La página del área dice con qué mobiliario cuenta.
        quesera = next(area for area in areas.context['infraestructura']['areas']
                       if 'Tina quesera' in area['espacio'].mobiliario_incluido)
        self.assertContains(self.client.get(quesera['url']), 'Tina quesera')

    def test_produccion_muestra_todo_el_mapa_y_ordena_sus_secciones(self):
        # El mapa completo, con las secciones pendientes, lo ve quien gestiona la planta.
        self.client.force_login(get_user_model().objects.create_superuser('gestor.mapa', 'g@example.org', 'clave'))
        ficha = self.client.get(self.unidad.get_absolute_url()).content.decode()
        secciones = (
            ('4.1', 'Lo que produce la planta'),
            ('4.2', 'Fichas técnicas de producto'),
            ('4.3', 'Empaque y presentación'),
            ('4.4', 'Requerimiento de materiales'),
            ('4.5', 'Corridas y lotes'),
            ('4.6', 'Desarrollo de producto'),
        )
        posiciones = []
        for numero, titulo in secciones:
            self.assertIn(numero, ficha)
            self.assertIn(titulo, ficha)
            posiciones.append(ficha.index(f'data-seccion="{numero}"'))
        self.assertEqual(posiciones, sorted(posiciones))
