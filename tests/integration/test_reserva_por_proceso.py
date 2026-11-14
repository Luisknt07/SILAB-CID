"""La práctica por proceso: la planta marca lo que el proceso exige.

El docente elige el proceso y la escala; el sistema deriva áreas, equipos
con auxiliares, software, insumos escalados y la duración de la sesión. La
solicitud entra por el motor de reservas, que exige lo obligatorio del
proceso; al aprobarse nace la orden de la práctica con la línea bloqueada,
y al cerrar no se descuenta dos veces lo que la reserva ya descontó.
"""

import json
from datetime import time, timedelta
from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.gestion_produccion import _plan_json, orden_de_practica
from apps.reservas.presentation.proceso import seleccion_por_proceso
from apps.plantas_piloto.operacion.management.plantas.taxonomia import PRODUCTOS_TAXONOMIA
from apps.recursos.models.consumibles import EntradaInventario, LoteConsumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Producto
from apps.formacion.models.practicas import PlanificacionPractica
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_laboratorios_institucionales import _dia_habil
from tests.integration.test_produccion_planta import BasePlantaProduce


class BasePracticaPorProceso(BasePlantaProduce):
    def seleccion(self, factor='2', hora=None):
        return seleccion_por_proceso(self.receta_queso, Decimal(factor), hora_inicio=hora)

    def aprobar_guia(self, reserva):
        """La guía integrada nace en revisión; la planta la aprueba antes que la reserva."""
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        guia = (
            GuiaActividadReserva.objects.filter(actividad=plan.actividad, activo=True)
            .order_by('-numero_version', '-pk')
            .first()
        )
        self.client.force_login(self.coordinacion)
        respuesta = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[guia.pk]),
            {'accion': 'aprobar', 'observacion': 'Guía verificada.'},
        )
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b'')[:300])

    def aprobar(self, reserva):
        self.client.force_login(self.coordinacion)
        return self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {'accion': 'aprobar', 'observacion': 'Práctica aprobada.'},
        )

    def carga_docencia(self, seleccion, **extra):
        """Lo que la página envía al motor de reservas para una práctica docente."""
        fecha = self.inicio.isoformat()
        sesion = seleccion['sesion']
        datos = {
            'unidad_id': self.unidad.pk,
            'tipo_solicitud': 'recursos',
            'receta_id': self.receta_queso.pk,
            'factor_proceso': seleccion['factor'],
            'fecha_inicio': f"{fecha}T{sesion['hora_inicio']}",
            'fecha_fin': f"{fecha}T{sesion['hora_fin']}",
            'horas_seleccionadas': json.dumps(sesion['horas']),
            'incluye_espacio': '1',
            'solicito_espacio': 'true',
            'solicito_equipo': 'true',
            'solicito_software': 'true',
            'alcance_espacio': 'areas',
            'espacios_solicitados': [str(e['id']) for e in seleccion['espacios']],
            'unidades_seleccionadas': json.dumps([
                {'id': e['id'], 'codigo': e['codigo'], 'equipo_codigo': e['equipo_codigo'], 'equipo_nombre': e['equipo_nombre']}
                for e in seleccion['equipos']
            ]),
            'software_solicitado': [str(s['id']) for s in seleccion['software']],
            'consumibles_seleccionados': json.dumps([
                {'id': i['id'], 'cantidad': i['cantidad'], 'metodo_estimacion': 'simulacion'} for i in seleccion['insumos']
            ]),
            'provision_consumibles': 'unidad',
            'piezas_por_sesion': str(seleccion['piezas']),
            'detalle_trabajo_recursos': 'Práctica de queso fresco a dos corridas base.',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Elaboración de queso fresco: control de puntos críticos',
            'origen_programacion': 'programada',
            'descripcion_proyecto': 'Los estudiantes conducen el proceso completo y registran los puntos críticos.',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'guia_confirmada_solicitante': '1',
            'guia_formato_contenido': 'html',
            'guia_formato_procedimiento': 'numerado',
            'guia_asignatura': 'Tecnología de Lácteos: Quesos',
            'guia_resultado_aprendizaje': '<p>Conduce el proceso de queso fresco de principio a fin.</p>',
            'guia_objetivos': '<ul><li>Elaborar queso fresco a escala de dos corridas.</li></ul>',
            'guia_procedimiento': '<ol class="guide-steps"><li><p>Recepción y control de la leche.</p></li><li><p>Pasteurización a 65 °C.</p></li></ol>',
        }
        datos.update(extra)
        return datos

    def reservar(self, datos, usuario=None):
        self.client.force_login(usuario or self.docente)
        return self.client.post(reverse('crear_reserva'), datos)


class LaSeleccionDelProcesoTests(BasePracticaPorProceso):
    databases = {'default', 'centros'}

    def test_el_proceso_deriva_areas_equipos_software_insumos_y_sesion(self):
        seleccion = self.seleccion('2')
        self.assertEqual(seleccion['escala'], '200 litros de leche')
        self.assertEqual(seleccion['producto_esperado'], '24 kg')
        self.assertEqual(
            [e['nombre'] for e in seleccion['espacios']],
            [
                'Área de recepción de leche', 'Línea de proceso térmico', 'Sala de quesería',
                'Sala de fermentación y envasado', 'Cámara de frío',
            ],
        )
        codigos = {e['equipo_codigo'] for e in seleccion['equipos']}
        self.assertEqual(codigos, {
            'LAC-EQ-TANQUE', 'LAC-EQ-PASTEUR', 'LAC-EQ-TINA', 'LAC-EQ-PRENSA', 'LAC-EQ-ENVASADORA', 'LAC-EQ-CAMARA',
        })
        pasteur = next(e for e in seleccion['equipos'] if e['equipo_codigo'] == 'LAC-EQ-PASTEUR')
        self.assertEqual(pasteur['codigo'], 'LAC-EQP-PAST-01')
        self.assertIn('Caldera de vapor', pasteur['auxiliares'])
        self.assertEqual(pasteur['etapas'], [2, 11])
        self.assertTrue(all(e['obligatorio'] for e in seleccion['equipos']))
        self.assertEqual(
            sorted(s['nombre'] for s in seleccion['software']),
            ['Registro de trazabilidad de lotes', 'Simulador de balance de línea'],
        )
        insumos = {i['nombre']: i for i in seleccion['insumos']}
        self.assertEqual(insumos['Leche cruda']['cantidad'], '200')
        self.assertEqual(insumos['Sal refinada']['cantidad'], '0.8')
        self.assertFalse(insumos['Paño de quesería']['obligatorio'])
        self.assertEqual(len(seleccion['ruta']), 11)
        self.assertEqual(seleccion['ruta'][0]['nombre'], 'Recepción y control de la leche')
        self.assertEqual(seleccion['ruta'][0]['espacio'], 'Área de recepción de leche')
        self.assertEqual(seleccion['ruta'][1]['equipo'], 'Pasteurizador por lotes')
        self.assertTrue(any(etapa['punto_critico'] for etapa in seleccion['ruta']))
        self.assertEqual(seleccion['faltantes'], [])
        self.assertEqual(seleccion['piezas'], 2)
        # Seis horas y media de línea desde las 07:00; la refrigeración de un día sigue después.
        sesion = seleccion['sesion']
        self.assertEqual(sesion['hora_inicio'], '07:00')
        self.assertEqual(sesion['horas'], [7, 8, 9, 10, 11, 12, 13])
        self.assertEqual(sesion['minutos_sesion'], 390)
        self.assertEqual(sesion['dias_extra'], 1)
        self.assertTrue(sesion['cabe_en_jornada'])
        self.assertTrue(sesion['cruza_almuerzo'])
        # Empezando a las 13:00 el proceso no cabe en la jornada.
        tarde = self.seleccion('2', hora=time(13, 0))
        self.assertFalse(tarde['sesion']['cabe_en_jornada'])
        self.assertEqual(tarde['sesion']['horas'], [13, 14, 15, 16])
        # Si la planta reubica la envasadora, la selección sigue a la máquina.
        envasadora = UnidadEquipo.objects.get(codigo_unidad='LAC-EQP-ENV-01')
        EspacioReservable.objects.get(codigo='LAC-AREA-FERMENTACION').equipos_asociados.remove(envasadora)
        EspacioReservable.objects.get(codigo='LAC-SALA-CAPACITACION').equipos_asociados.add(envasadora)
        reubicada = self.seleccion('2')
        self.assertIn('Sala de capacitación y degustación', [e['nombre'] for e in reubicada['espacios']])

    def test_la_seleccion_y_el_asistente_se_ofrecen_a_quien_inicia_sesion(self):
        url = reverse('seleccion_por_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        anonimo = self.client.get(url)
        self.assertEqual(anonimo.status_code, 302)
        self.client.force_login(self.docente)
        respuesta = self.client.get(url + '?factor=1.5&hora=08:00')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['success'])
        self.assertEqual(datos['escala'], '150 litros de leche')
        self.assertEqual(datos['sesion']['hora_inicio'], '08:00')
        self.assertEqual(self.client.get(url + '?factor=0').status_code, 400)
        # Con «guia» viajan los apartados FT04 que el proceso sabe llenar.
        con_guia = self.client.get(url + '?factor=2&guia=1').json()
        self.assertIn('Pasteuriza', con_guia['guia']['guia_procedimiento'])
        self.assertIn('<ul>', con_guia['guia']['guia_objetivos'])
        # El asistente de la unidad pregunta el proceso en la misma ruta de siempre; un
        # laboratorio sin procesos no pregunta nada.
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'id="procesoReserva"')
        self.assertContains(ficha, '¿Qué producto y proceso vas a realizar?')
        self.assertContains(ficha, 'Queso fresco · proceso técnico de 11 etapas')
        self.assertContains(ficha, 'data-base="100"')
        for familia, referencias in PRODUCTOS_TAXONOMIA['LAC'].items():
            self.assertContains(ficha, f'<optgroup label="{familia}">')
            for nombre, _unidad_medida in referencias:
                self.assertContains(ficha, f'data-producto="{nombre}"')
        self.assertContains(ficha, 'Helado de crema · proceso técnico de 11 etapas')
        self.assertContains(ficha, 'Arequipe · derivado, por validar · proceso técnico de')
        self.assertContains(ficha, 'Suero en polvo · proceso por configurar')
        self.assertContains(ficha, 'Ricotta · proceso técnico de 11 etapas')
        self.assertContains(ficha, 'data-selection-url-template="/laboratorio/planta-piloto-lacteos/procesos/0/seleccion.json"')
        self.assertContains(ficha, 'name="factor_proceso"')
        script = (
            'apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js'
        )
        with open(script, encoding='utf-8') as archivo:
            codigo_asistente = archivo.read()
        self.assertIn('dataGrid.insertBefore(processField, purposeSection)', codigo_asistente)
        self.assertIn('rw-process-route__track', codigo_asistente)
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin procesos', descripcion='.', fecha_inicio='2026-01-01',
            dependencia='laboratorios', slug='laboratorio-sin-procesos',
        )
        ficha_lab = self.client.get(laboratorio.get_absolute_url())
        self.assertNotContains(ficha_lab, 'id="procesoReserva"')


class LaReservaPorProcesoTests(BasePracticaPorProceso):
    def test_la_solicitud_guarda_el_proceso_y_exige_lo_obligatorio(self):
        seleccion = self.seleccion('2')
        respuesta = self.reservar(self.carga_docencia(seleccion))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.receta, self.receta_queso)
        self.assertEqual(reserva.producto_solicitado, self.receta_queso.producto)
        self.assertEqual(reserva.factor_proceso, Decimal('2.000'))
        self.assertEqual(reserva.tipo_solicitud, 'recursos')
        self.assertEqual(reserva.cantidad_piezas, 2)
        self.assertEqual(reserva.espacios_solicitados.count(), 5)
        self.assertEqual(len(reserva.get_unidades_seleccionadas_list()), 6)
        # Los siete insumos del proceso más la protección por persona que la planta entrega.
        self.assertEqual(reserva.consumibles_solicitados.count(), 9)
        cofias = reserva.consumibles_solicitados.get(consumible__codigo='LAC-PRO-COFIA')
        self.assertEqual(cofias.cantidad_solicitada, Decimal('3.000'))
        leche = reserva.consumibles_solicitados.get(consumible__codigo='LAC-INS-LECHE')
        self.assertEqual(leche.cantidad_solicitada, Decimal('200.000'))
        self.assertEqual(reserva.hora_inicio.hour, 7)
        self.assertEqual(reserva.hora_fin.hour, 14)
        # Sin la prensa, el motor devuelve qué falta y no crea nada.
        sin_prensa = [e for e in seleccion['equipos'] if e['equipo_codigo'] != 'LAC-EQ-PRENSA']
        otro_dia = _dia_habil(self.inicio + timedelta(days=1)).isoformat()
        rechazo = self.reservar(self.carga_docencia(
            seleccion,
            unidades_seleccionadas=json.dumps([
                {'id': e['id'], 'codigo': e['codigo'], 'equipo_codigo': e['equipo_codigo'], 'equipo_nombre': e['equipo_nombre']}
                for e in sin_prensa
            ]),
            fecha_inicio=f"{otro_dia}T07:00",
            fecha_fin=f"{otro_dia}T14:00",
        ))
        self.assertEqual(rechazo.status_code, 400)
        self.assertIn('Prensa neumática de quesos', rechazo.json()['error'])
        self.assertEqual(Reserva.objects.filter(receta=self.receta_queso).count(), 1)
        # Un proceso de otra unidad o una escala inválida tampoco pasan.
        ajena = self.reservar(self.carga_docencia(seleccion, receta_id='999999'))
        self.assertEqual(ajena.status_code, 400)
        self.assertIn('no está disponible', ajena.json()['error'])

    def test_un_producto_sin_receta_se_reserva_con_recursos_manual_y_trazabilidad(self):
        seleccion = self.seleccion('1')
        arequipe = Producto.objects.get(unidad=self.unidad, nombre='Arequipe')
        respuesta = self.reservar(self.carga_docencia(
            seleccion,
            receta_id='',
            factor_proceso='',
            producto_id=str(arequipe.pk),
            fecha_fin=f'{self.inicio.isoformat()}T12:00',
            horas_seleccionadas=json.dumps([7, 8, 9, 10, 11]),
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertIsNone(reserva.receta)
        self.assertIsNone(reserva.factor_proceso)
        self.assertEqual(reserva.producto_solicitado, arequipe)
        self.assertIn('Producto: Arequipe', reserva.titulo_solicitud)
        self.assertEqual(reserva.espacios_solicitados.count(), len(seleccion['espacios']))

        detalle = self.client.get(reverse('obtener_reservas_usuario')).json()
        serializada = next(item for item in detalle['reservas'] if item['id'] == reserva.pk)
        self.assertEqual(serializada['producto_solicitado'], 'Arequipe')

    def test_al_aprobar_nace_la_orden_y_al_cerrar_no_se_descuenta_dos_veces(self):
        seleccion = self.seleccion('2')
        respuesta = self.reservar(self.carga_docencia(seleccion))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        # Una guía completa en revisión permite aprobar la reserva y crear la orden.
        # La publicación sigue siendo necesaria antes de iniciar la ejecución.
        aprobacion = self.aprobar(reserva)
        self.assertEqual(aprobacion.status_code, 200, aprobacion.content)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        self.assertEqual(orden.origen, 'practica')
        self.assertEqual(orden.factor, Decimal('2.000'))
        self.assertEqual(orden.cantidad_planificada, Decimal('24.000'))
        self.assertEqual(orden.fecha_inicio, self.inicio)
        self.assertEqual(orden.fecha_fin, self.inicio + timedelta(days=1))
        self.assertEqual(orden.linea.codigo, 'LAC-LINEA-PROCESO')
        self.assertEqual(orden.equipos.count(), 6)
        self.assertEqual(orden.bloqueo.tipo, 'produccion')
        self.assertEqual(orden.bloqueo.fecha_fin, self.inicio + timedelta(days=1))
        # Volver a aprobar no duplica la orden.
        self.assertEqual(orden_de_practica(reserva, self.coordinacion), orden)
        self.assertEqual(OrdenProduccion.objects.filter(reserva=reserva).count(), 1)

        # La sesión ya pasó: al cerrar la atención la leche sale del lote del tanque
        # y la orden ya no la descuenta.
        Reserva.objects.filter(pk=reserva.pk).update(fecha=_dia_habil(self.hoy - timedelta(days=4)))
        pedidos = {p.consumible.codigo: p for p in reserva.consumibles_solicitados.all()}
        lote_leche = LoteConsumible.objects.get(codigo='LAC-LECHE-L1')
        tanque = UnidadEquipo.objects.get(codigo_unidad='LAC-EQP-TANQ-01')
        # La reserva puede aprobarse con la guía en revisión; su ejecución
        # requiere que el laboratorio haya aprobado y publicado la guía.
        from apps.reservas.models.reservas import GuiaActividadReserva
        GuiaActividadReserva.objects.filter(actividad=reserva.actividad_catalogo).update(
            estado_publicacion='publicada', es_vigente=True,
        )
        cierre = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {
                'accion': 'completar', 'observacion': 'Práctica realizada.',
                'ejecucion_registrada': '1', 'participantes_seleccionados': '[]',
                'asistencia_solicitante': 'asistio', 'ejecucion_hora_inicio': '07:00',
                'ejecucion_hora_fin': '13:30', 'ejecucion_asistentes_total': '16',
                'ejecucion_piezas': '2', 'ejecucion_cumplimiento': 'si',
                'ejecucion_equipos_ids': [str(tanque.pk)],
                'ejecucion_consumibles_json': json.dumps([{
                    'reserva_consumible_id': pedidos['LAC-INS-LECHE'].pk,
                    'consumida': '198', 'desperdiciada': '2', 'lote_id': lote_leche.pk, 'equipo_id': tanque.pk,
                    'motivo_desperdicio': 'desperdicio_calidad', 'piezas': 2, 'modo_cantidad': 'distintas', 'detalle_piezas': ['99', '99'],
                }]),
                'ejecucion_observaciones': 'Dos lotes de queso fresco.',
            },
        )
        self.assertEqual(cierre.status_code, 200, cierre.content)
        lote_leche.refresh_from_db()
        self.assertEqual(lote_leche.cantidad_actual, Decimal('0.000'))
        self.assertTrue(EntradaInventario.objects.filter(reserva=reserva, consumible__codigo='LAC-INS-LECHE').exists())
        plan = json.loads(_plan_json(orden))
        leche_plan = next(i for i in plan['insumos'] if i['nombre'] == 'Leche cruda')
        self.assertTrue(leche_plan['descontado_en_reserva'])
        self.assertEqual(leche_plan['cantidad'], '0')
        cuajo_plan = next(i for i in plan['insumos'] if i['nombre'] == 'Cuajo líquido')
        self.assertFalse(cuajo_plan['descontado_en_reserva'])
        self.assertEqual(cuajo_plan['cantidad'], '20.000')

    def test_una_reserva_cancelada_libera_la_linea_de_la_practica(self):
        seleccion = self.seleccion('1')
        respuesta = self.reservar(self.carga_docencia(seleccion))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.aprobar_guia(reserva)
        self.assertEqual(self.aprobar(reserva).status_code, 200)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        self.assertTrue(orden.bloqueo.activo)
        rechazo = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {'accion': 'cancelar', 'observacion': 'La docente no podrá asistir.'},
        )
        self.assertEqual(rechazo.status_code, 200, rechazo.content)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'cancelada')
        orden.bloqueo.refresh_from_db()
        self.assertFalse(orden.bloqueo.activo)

    def test_un_investigador_reserva_por_proceso_sin_guia_integrada(self):
        seleccion = self.seleccion('0.5')
        datos = self.carga_docencia(
            seleccion,
            proposito_codigo='investigacion_innovacion',
            subtipo_actividad='desarrollo_experimental',
            referencia_actividad='Ensayo de rendimiento del queso con leche descremada',
        )
        for clave in list(datos):
            if clave.startswith('guia_') or clave == 'origen_programacion':
                datos.pop(clave)
        respuesta = self.reservar(datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.factor_proceso, Decimal('0.500'))
        self.assertEqual(reserva.cantidad_piezas, 1)
        self.assertEqual(self.aprobar(reserva).status_code, 200)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        self.assertEqual(orden.origen, 'investigacion')
        self.assertEqual(orden.cantidad_planificada, Decimal('6.000'))
