"""Calidad e inocuidad: qué se mide, con qué límite y qué pasa cuando se sale de él.

Sobre la Planta Piloto de Lácteos cargada: el plan declara los parámetros y
sus límites en la recepción, durante el proceso y al liberar; el control los
mide sobre un lote y decide; lo conforme libera el lote, lo que sale del
límite abre la no conformidad y el lote espera su disposición. El plan HACCP
cruza los puntos críticos de cada proceso con los parámetros que los vigilan.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.calidad import plan_haccp
from apps.plantas_piloto.operacion.models.calidad import AccionCorrectiva, ControlCalidad, NoConformidad, ParametroCalidad, PlanCalidad
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, Receta
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class BaseCalidad(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plan_recepcion = PlanCalidad.objects.get(codigo='LAC-CAL-RECEPCION-LECHE')
        cls.plan_queso = PlanCalidad.objects.get(codigo='LAC-CAL-LIBERACION-QUESO')
        cls.control_url = reverse('control_calidad', args=[cls.unidad.slug])

    def valores(self, plan, **cambios):
        """Un juego de valores dentro del límite, con los que la prueba quiera mover."""
        dentro = {
            'Temperatura de llegada': '4',
            'Acidez titulable': '16',
            'Densidad a 15 °C': '1.030',
            'Prueba de alcohol': 'negativa',
            'Inhibidores y antibióticos': 'negativa',
            'Grasa': '3.6',
            'pH del queso': '6.4',
            'Humedad': '55',
            'Temperatura del lote en cámara': '4',
            'Coliformes totales': '10',
            'Aspecto, olor y sabor': 'conforme',
        }
        dentro.update(cambios)
        datos = {}
        for parametro in plan.parametros_ordenados():
            datos[f'parametro_{parametro.pk}'] = dentro[parametro.nombre]
        return datos

    def controlar(self, plan, consulta, usuario=None, **cambios):
        self.client.force_login(usuario or self.coordinacion)
        datos = self.valores(plan, **cambios)
        datos['observaciones'] = 'Control de la prueba.'
        return self.client.post(f'{self.control_url}?{consulta}', datos)

    def lote_de_queso_en_cuarentena(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=2)).isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        return LoteProducto.objects.get(orden=orden, producto__codigo='LAC-PRD-QUESO-FRESCO')

    def leche_del_cliente(self):
        """Un lote de leche recibido de un cliente, todavía sin su control de recepción."""
        return LoteConsumible.objects.create(
            consumible=Consumible.objects.get(codigo='LAC-INS-LECHE'),
            codigo='LAC-LECHE-CLIENTE-1',
            cantidad_inicial=Decimal('200.000'),
            cantidad_actual=Decimal('200.000'),
            estado='bodega',
            bodega='Plataforma de recepción',
            material_cliente=True,
            fecha_vencimiento=self.hoy + timedelta(days=3),
        )


class LaPlantaDeclaraQueMideTests(BaseCalidad):
    def test_la_carga_trae_los_planes_con_sus_parametros_y_limites(self):
        planes = dict(
            PlanCalidad.objects.filter(unidad=self.unidad).values_list('codigo', 'momento')
        )
        self.assertEqual(planes['LAC-CAL-RECEPCION-LECHE'], 'recepcion')
        self.assertEqual(planes['LAC-CAL-PROCESO-QUESO'], 'proceso')
        self.assertEqual(planes['LAC-CAL-LIBERACION-YOGUR'], 'liberacion')
        self.assertEqual(len(planes), 15)
        self.assertEqual(
            ParametroCalidad.objects.filter(plan__unidad=self.unidad).count(), 76
        )
        # El plan de recepción mira la materia prima; el de liberación, el producto.
        self.assertEqual(self.plan_recepcion.consumible.codigo, 'LAC-INS-LECHE')
        self.assertIsNone(self.plan_recepcion.producto)
        self.assertEqual(self.plan_queso.producto.codigo, 'LAC-PRD-QUESO-FRESCO')
        limites = {
            parametro.nombre: parametro.limite_texto
            for parametro in self.plan_recepcion.parametros_ordenados()
        }
        self.assertEqual(limites['Acidez titulable'], '14–18 °D')
        self.assertEqual(limites['Grasa'], '≥ 3 %')
        self.assertEqual(limites['Prueba de alcohol'], 'negativa')
        self.assertEqual(
            {parametro.nombre: parametro.limite_texto for parametro in self.plan_queso.parametros_ordenados()}['Humedad'],
            '≤ 60 %',
        )
        # La carga se repite sin duplicar planes ni parámetros.
        from django.core.management import call_command
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        self.assertEqual(PlanCalidad.objects.filter(unidad=self.unidad).count(), 15)
        self.assertEqual(ParametroCalidad.objects.filter(plan__unidad=self.unidad).count(), 76)

    def test_el_plan_haccp_cruza_los_puntos_criticos_con_sus_parametros(self):
        queso = Receta.objects.get(codigo='LAC-REC-QUESO-100')
        filas = {
            fila['etapa'].nombre: fila
            for item in plan_haccp(self.unidad, [queso]) for fila in item['filas']
        }
        # El plan HACCP lleva solo los PCC (inocuidad); la recepción es un control de calidad.
        self.assertEqual(set(filas), {'Pasteurización'})
        vigilan = [parametro.nombre for parametro in filas['Pasteurización']['parametros']]
        self.assertEqual(vigilan, ['Temperatura de pasteurización', 'Tiempo de sostenimiento'])
        self.assertEqual(filas['Pasteurización']['limite'], '65 °C durante 30 minutos')
        self.assertEqual(filas['Pasteurización']['codigo'], 'PCC-1')

    def test_la_pagina_del_plan_haccp_se_publica_y_se_puede_incrustar(self):
        respuesta = self.client.get(reverse('plan_haccp', args=[self.unidad.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertContains(respuesta, 'Plan HACCP')
        self.assertContains(respuesta, 'Temperatura de pasteurización')
        self.assertContains(respuesta, '63–68 °C')
        self.assertContains(respuesta, 'Recepción de leche cruda')

    def test_la_ficha_publica_dice_que_mide_cada_plan(self):
        respuesta = self.client.get(reverse('calidad_publica', args=[self.unidad.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'QUÉ MIDE CADA PLAN Y CON QUÉ LÍMITE')
        self.assertContains(respuesta, 'Recepción de leche cruda')
        self.assertContains(respuesta, '14–18 °D')
        self.assertContains(respuesta, 'Plan HACCP')
        publicada = respuesta.context['calidad']['publicada']
        self.assertEqual(len(publicada['planes']), 15)
        self.assertEqual(publicada['parametros_totales'], 76)


class ElPanelDeCalidadTests(BaseCalidad):
    def test_la_pestana_es_de_la_planta_y_lista_lo_que_espera_control(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.leche_del_cliente()
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertEqual(panel.status_code, 200)
        secciones = {item['clave']: item['habilitada'] for item in panel.context['secciones_gestion']}
        self.assertTrue(secciones['calidad'])
        self.assertContains(panel, 'data-management-view="calidad"')
        self.assertContains(panel, 'data-agenda-operation-form="plan_calidad"')
        self.assertContains(panel, 'data-agenda-operation-form="parametro_calidad"')
        self.assertContains(panel, 'data-agenda-operation-form="no_conformidad"')
        self.assertContains(panel, 'data-agenda-operation-form="accion_correctiva"')
        self.assertContains(panel, f'{self.control_url}?lote_producto={lote.pk}')
        self.assertContains(panel, 'LAC-LECHE-CLIENTE-1')
        self.assertContains(panel, 'Liberación de queso fresco')

    def test_un_laboratorio_no_tiene_la_pestana_de_calidad(self):
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin producción', descripcion='Solo reserva.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            slug='laboratorio-sin-calidad', administrador=self.coordinacion,
        )
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[laboratorio.slug]))
        self.assertEqual(panel.status_code, 200)
        claves = {item['clave'] for item in panel.context['secciones_gestion']}
        self.assertNotIn('calidad', claves)
        self.assertNotContains(panel, 'data-management-view="calidad"')
        self.assertNotContains(panel, 'data-agenda-operation-form="plan_calidad"')

    def test_la_hoja_de_control_solo_la_abre_quien_opera_la_produccion(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.client.force_login(self.estudiante)
        respuesta = self.client.get(f'{self.control_url}?lote_producto={lote.pk}')
        self.assertEqual(respuesta.status_code, 403)


class ElControlDecideElLoteTests(BaseCalidad):
    def test_un_control_conforme_libera_el_lote(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.assertEqual(lote.control_calidad, 'pendiente')
        respuesta = self.controlar(self.plan_queso, f'lote_producto={lote.pk}')
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b''))
        control = ControlCalidad.objects.get(lote_producto=lote)
        self.assertEqual(control.resultado, 'conforme')
        self.assertEqual(control.plan, self.plan_queso)
        self.assertEqual(control.mediciones.count(), 5)
        self.assertTrue(all(medicion.conforme for medicion in control.mediciones.all()))
        lote.refresh_from_db()
        self.assertEqual(lote.control_calidad, 'aprobado')
        self.assertEqual(lote.estado, 'disponible')
        self.assertFalse(NoConformidad.objects.filter(unidad=self.unidad).exists())
        # La página vuelve al mismo lote con el control recién hecho.
        seguimiento = self.client.get(respuesta['Location'])
        self.assertEqual(seguimiento.status_code, 200)
        self.assertContains(seguimiento, 'el lote queda liberado')

    def test_un_valor_fuera_de_limite_abre_la_no_conformidad_y_deja_el_lote_en_cuarentena(self):
        lote = self.lote_de_queso_en_cuarentena()
        respuesta = self.controlar(
            self.plan_queso, f'lote_producto={lote.pk}', **{'pH del queso': '5.2', 'Humedad': '64'}
        )
        self.assertEqual(respuesta.status_code, 302)
        control = ControlCalidad.objects.get(lote_producto=lote)
        self.assertEqual(control.resultado, 'no_conforme')
        fuera = {medicion.parametro.nombre for medicion in control.mediciones.filter(conforme=False)}
        self.assertEqual(fuera, {'pH del queso', 'Humedad'})
        no_conformidad = NoConformidad.objects.get(control=control)
        self.assertEqual(no_conformidad.gravedad, 'critica')
        self.assertEqual(no_conformidad.estado, 'abierta')
        self.assertEqual(no_conformidad.disposicion, 'pendiente')
        self.assertEqual(no_conformidad.lote_producto, lote)
        self.assertTrue(no_conformidad.codigo.startswith('NC-'))
        self.assertIn('pH del queso = 5.2', no_conformidad.descripcion)
        self.assertIn('6.1–6.8', no_conformidad.descripcion)
        lote.refresh_from_db()
        self.assertEqual(lote.control_calidad, 'pendiente')
        self.assertEqual(lote.estado, 'cuarentena')

    def test_un_parametro_sin_valor_no_registra_el_control(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.client.force_login(self.coordinacion)
        datos = self.valores(self.plan_queso)
        parametro = self.plan_queso.parametros_ordenados()[0]
        datos[f'parametro_{parametro.pk}'] = ''
        respuesta = self.client.post(f'{self.control_url}?lote_producto={lote.pk}', datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'Registra el valor de {parametro.nombre}')
        self.assertFalse(ControlCalidad.objects.filter(lote_producto=lote).exists())
        lote.refresh_from_db()
        self.assertEqual(lote.control_calidad, 'pendiente')

    def test_la_recepcion_de_la_materia_prima_del_cliente_usa_su_propio_plan(self):
        lote = self.leche_del_cliente()
        respuesta = self.controlar(self.plan_recepcion, f'lote_consumible={lote.pk}')
        self.assertEqual(respuesta.status_code, 302)
        control = ControlCalidad.objects.get(lote_consumible=lote)
        self.assertEqual(control.plan, self.plan_recepcion)
        self.assertEqual(control.resultado, 'conforme')
        self.assertEqual(control.mediciones.count(), 6)
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'bodega')


class LaNoConformidadSeTrataTests(BaseCalidad):
    def no_conformidad_del_queso(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.assertEqual(
            self.controlar(self.plan_queso, f'lote_producto={lote.pk}', **{'pH del queso': '5.2'}).status_code,
            302,
        )
        return lote, NoConformidad.objects.get(lote_producto=lote)

    def test_el_rechazo_da_de_baja_el_lote_y_cierra_la_no_conformidad(self):
        lote, no_conformidad = self.no_conformidad_del_queso()
        respuesta = self.operar(
            modulo='no_conformidad',
            registro_id=no_conformidad.pk,
            disposicion='rechazo',
            estado='cerrada',
            causa='Cuajada ácida por leche de la tarde retenida sin frío.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        no_conformidad.refresh_from_db()
        self.assertEqual(no_conformidad.disposicion, 'rechazo')
        self.assertEqual(no_conformidad.estado, 'cerrada')
        self.assertIsNotNone(no_conformidad.cerrada_en)
        lote.refresh_from_db()
        self.assertEqual(lote.control_calidad, 'rechazado')
        self.assertEqual(lote.estado, 'retirado')
        baja = MovimientoProducto.objects.get(lote=lote, tipo='baja')
        self.assertIn(no_conformidad.codigo, baja.motivo)

    def test_la_liberacion_condicionada_deja_salir_el_lote(self):
        lote, no_conformidad = self.no_conformidad_del_queso()
        respuesta = self.operar(
            modulo='no_conformidad',
            registro_id=no_conformidad.pk,
            disposicion='liberacion_condicionada',
            estado='en_tratamiento',
            causa='Desviación de pH sin riesgo microbiológico; se destina a consumo interno.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        lote.refresh_from_db()
        self.assertEqual(lote.control_calidad, 'aprobado')
        self.assertEqual(lote.estado, 'disponible')
        no_conformidad.refresh_from_db()
        self.assertEqual(no_conformidad.estado, 'en_tratamiento')
        self.assertIsNone(no_conformidad.cerrada_en)

    def test_no_se_cierra_una_no_conformidad_sin_decidir_la_disposicion(self):
        _, no_conformidad = self.no_conformidad_del_queso()
        respuesta = self.operar(
            modulo='no_conformidad', registro_id=no_conformidad.pk,
            disposicion='pendiente', estado='cerrada', causa='',
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('disposición decidida', respuesta.json()['error'])
        no_conformidad.refresh_from_db()
        self.assertEqual(no_conformidad.estado, 'abierta')

    def test_la_accion_correctiva_pone_la_no_conformidad_en_tratamiento(self):
        _, no_conformidad = self.no_conformidad_del_queso()
        respuesta = self.operar(
            modulo='accion_correctiva',
            no_conformidad_id=no_conformidad.pk,
            descripcion='Enfriar la leche de la tarde a 4 °C antes de guardarla y revisar el tanque.',
            responsable=self.laboratorista.username,
            fecha_compromiso=(self.hoy + timedelta(days=7)).isoformat(),
            estado='pendiente',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        accion = AccionCorrectiva.objects.get(no_conformidad=no_conformidad)
        self.assertEqual(accion.responsable, self.laboratorista)
        self.assertEqual(accion.estado, 'pendiente')
        self.assertIsNone(accion.fecha_cierre)
        self.assertFalse(accion.vencida)
        no_conformidad.refresh_from_db()
        self.assertEqual(no_conformidad.estado, 'en_tratamiento')
        # Verificada, la acción queda cerrada con su fecha.
        respuesta = self.operar(
            modulo='accion_correctiva',
            registro_id=accion.pk,
            descripcion=accion.descripcion,
            responsable=self.laboratorista.username,
            fecha_compromiso=(self.hoy + timedelta(days=7)).isoformat(),
            estado='verificada',
            verificacion='Dos semanas de recepciones con acidez dentro del rango.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        accion.refresh_from_db()
        self.assertEqual(accion.estado, 'verificada')
        self.assertEqual(accion.fecha_cierre, self.hoy)


class LosPlanesSeEditanDesdeElPanelTests(BaseCalidad):
    def test_la_planta_crea_un_plan_y_su_parametro(self):
        respuesta = self.operar(
            modulo='plan_calidad',
            codigo='lac-cal-mozzarella',
            nombre='Liberación de mozzarella',
            momento='liberacion',
            producto_id=self.unidad.productos.get(codigo='LAC-PRD-MOZZARELLA').pk,
            descripcion='El hilado y la humedad deciden la horma.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        plan = PlanCalidad.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertEqual(plan.codigo, 'LAC-CAL-MOZZARELLA')
        self.assertEqual(plan.unidad, self.unidad)
        respuesta = self.operar(
            modulo='parametro_calidad',
            plan_id=plan.pk,
            orden='1',
            nombre='Humedad de la horma',
            tipo='numerico',
            unidad_medida='%',
            minimo='48',
            maximo='56',
            metodo='Secado en estufa a 102 °C',
            critico='on',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        parametro = ParametroCalidad.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertEqual(parametro.limite_texto, '48–56 %')
        self.assertTrue(parametro.critico)
        # Desactivado, sale del plan sin borrar lo ya medido.
        respuesta = self.operar(
            modulo='parametro_calidad', registro_id=parametro.pk, accion='desactivar',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        parametro.refresh_from_db()
        self.assertFalse(parametro.activo)
        self.assertEqual(plan.parametros_ordenados(), [])

    def test_un_plan_de_recepcion_necesita_su_materia_prima(self):
        respuesta = self.operar(
            modulo='plan_calidad',
            codigo='LAC-CAL-SIN-INSUMO',
            nombre='Recepción sin materia prima',
            momento='recepcion',
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('qué materia prima recibe', respuesta.json()['error'])

    def test_un_parametro_numerico_necesita_al_menos_un_limite(self):
        respuesta = self.operar(
            modulo='parametro_calidad',
            plan_id=self.plan_queso.pk,
            nombre='Color sin límite',
            tipo='numerico',
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('mínimo, un máximo o ambos', respuesta.json()['error'])
