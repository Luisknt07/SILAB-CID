"""El semestre revisa recursos y ejecución; las necesidades se capturan una vez al año."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.documentos.presentation.recursos_periodo import (
    _bloques_anual, _bloques_antecedente, _bloques_egresos, _detalle_anual,
    _estado_anual, _plan_anual, _tabla_referencia, bloques_recursos, es_esquema_recursos,
    fijar_recursos, preparar_recursos,
)


class RecursosPeriodoTests(SimpleTestCase):
    def setUp(self):
        self.documento = SimpleNamespace(pk=20, unidad_id=7, anio=2027,
            unidad=SimpleNamespace(pk=7, codigo_base='laboratorios'))
        self.inicio, self.fin = date(2027, 1, 1), date(2027, 6, 30)

    def anual(self, **cambios):
        datos = dict(pk=5, unidad_id=7, anio=2026, estado='pendiente', recurso_id=None,
                     nombre_documental='Plan anual de compras y presupuesto para el año siguiente', version=1)
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_preparar_propone_revision_y_conserva_la_captura_legacy_sin_mutarla(self):
        contenido = dict(inversion=[dict(item='Equipo anterior', cantidad='1')],
                         sin_inversion_justificacion='Justificación anterior')
        original = deepcopy(contenido)
        resultado = preparar_recursos(contenido)
        self.assertEqual(contenido, original)
        self.assertTrue(es_esquema_recursos(resultado))
        self.assertEqual(resultado['inversion'], original['inversion'])
        self.assertEqual(resultado['sin_inversion_justificacion'], original['sin_inversion_justificacion'])
        self.assertIn('Propuesta para revisión', resultado['cobertura_recursos'])
        self.assertEqual(resultado['revision_recursos'], '')

    def test_la_marca_no_acepta_booleanos_ni_versiones_ajenas(self):
        for valor in (True, '1', 2, None):
            with self.subTest(valor=valor):
                self.assertFalse(es_esquema_recursos(dict(recursos_periodo_version=valor)))
        self.assertFalse(es_esquema_recursos([]))

    def test_una_edicion_revisada_no_se_sustituye_por_la_propuesta_inicial(self):
        contenido = dict(recursos_periodo_version=1, cobertura_recursos='<p>Cobertura revisada.</p>',
                         revision_recursos='revisado')
        self.assertEqual(preparar_recursos(contenido), contenido)
        contenido['cobertura_recursos'] = ''
        self.assertEqual(preparar_recursos(contenido)['cobertura_recursos'], '')

    def test_la_referencia_anual_es_la_elaborada_el_ano_anterior_de_la_misma_unidad(self):
        with patch('apps.documentos.models.expediente.DocumentoExpediente.objects.filter') as consulta:
            consulta.return_value.select_related.return_value.order_by.return_value.first.return_value = None
            self.assertIsNone(_plan_anual(self.documento))
        consulta.assert_called_once_with(unidad_id=7, anio=2026,
            exigido__codigo='PLAN-COMPRAS-ANUAL', corte='', mes__isnull=True)

    def test_una_propuesta_aprobada_documentalmente_no_se_etiqueta_como_pac_autorizado(self):
        anual = self.anual(estado='validado', recurso_id=4,
                          recurso=SimpleNamespace(activo=True, estado='vigente'))
        constancia = SimpleNamespace(observado_en=None, enviado_en=self.inicio, aprobado_en=self.inicio)
        self.assertEqual(_estado_anual(anual, constancia), 'Propuesta con conformidad documental de Dirección')
        constancia.observado_en = self.fin
        self.assertEqual(_estado_anual(anual, constancia), 'Propuesta devuelta para corrección')

    def test_sin_referencia_no_se_inventa_aprobacion_ni_cobertura(self):
        with patch('apps.documentos.presentation.recursos_periodo._plan_anual', return_value=None):
            bloques = _bloques_anual(self.documento)
        self.assertIn(('Año de ejecución de referencia', '2027'), bloques[0]['pares'])
        self.assertIn(('Año de elaboración de las necesidades', '2026'), bloques[0]['pares'])
        self.assertIn('No registrada', bloques[0]['pares'][-1][1])
        self.assertIn('no autoriza compras', bloques[-1]['texto'])

    def test_referencia_emitida_usa_el_contenido_conservado_y_no_el_borrador_actual(self):
        cabecera = ['Categoría', 'Ítem', 'Cantidad', 'Justificación', 'Prioridad',
                    'Costo unitario (USD)', 'Fuente', 'Trimestre', 'Total (USD)']
        constancia = SimpleNamespace(contenido_emitido=dict(secciones=[dict(codigo='compras', bloques=[
            dict(tipo='tabla', cabecera=cabecera, filas=[
                ['Equipos', 'Necesidad emitida', '2', 'Fundamento', 'Alta', '10', 'Institucional', '1', '20.00'],
                ['Total proyectado', '', '', '', '', '', '', '', '20.00']]),
            dict(tipo='rico', html='<p>Fundamento conservado.</p>')])]))
        with patch('apps.documentos.models.expediente.DocumentoElaborado.objects.filter',
                   side_effect=AssertionError('No se debe reconstruir el archivo emitido desde el borrador.')):
            bloques = _detalle_anual(self.anual(recurso_id=4), constancia)
        self.assertEqual(bloques[0]['cabecera'], ['Ítem', 'Cantidad', 'Total (USD)', 'Trimestre'])
        self.assertEqual(bloques[0]['filas'][0], ['Necesidad emitida', '2', '20.00', '1'])
        self.assertEqual(bloques[0]['filas'][-1], ['Total propuesto', '', '20.00', ''])
        self.assertEqual(bloques[1]['texto'], 'Fundamento conservado.')

    def test_una_entrega_externa_no_se_reconstruye_desde_la_redaccion(self):
        with patch('apps.documentos.models.expediente.DocumentoElaborado.objects.filter',
                   side_effect=AssertionError('La referencia externa se consulta en su archivo.')):
            bloques = _detalle_anual(self.anual(recurso_id=4), None)
        self.assertIn('Consulte el archivo anual', bloques[0]['texto'])

    def test_admite_el_encabezado_del_pac_y_el_encabezado_anterior(self):
        for nombre in ('Ítem', 'Bien o servicio'):
            with self.subTest(nombre=nombre):
                tabla = _tabla_referencia(dict(cabecera=[nombre, 'Cantidad', 'Total (USD)', 'Trimestre'],
                    filas=[['Instrumento', '2', '100.00', '1']]))
                self.assertEqual(tabla['cabecera'][0], nombre)
                self.assertEqual(tabla['filas'], [['Instrumento', '2', '100.00', '1']])

    def test_referencia_pac_programado_conserva_area_mes_y_semestre_del_snapshot(self):
        constancia = SimpleNamespace(contenido_emitido=dict(secciones=[dict(codigo='compras', bloques=[
            dict(tipo='tabla', cabecera=['Área', 'Bien o servicio', 'Cantidad', 'Valor unitario (USD)', 'Total (USD)', 'Mes', 'Semestre'],
                filas=[['Área emitida', 'Equipo emitido', '2', '10', '20.00', 'Julio', '2'],
                       ['Total previsto', '', '', '', '20.00', '', '']])])]))
        with patch('apps.documentos.models.expediente.DocumentoElaborado.objects.filter',
                   side_effect=AssertionError('La programación emitida se conserva en el snapshot.')):
            bloques = _detalle_anual(self.anual(recurso_id=4), constancia)
        self.assertEqual(bloques[0]['cabecera'], ['Bien o servicio', 'Área', 'Cantidad', 'Total (USD)', 'Mes', 'Semestre'])
        self.assertEqual(bloques[0]['filas'][0], ['Equipo emitido', 'Área emitida', '2', '20.00', 'Julio', '2'])
        self.assertEqual(bloques[0]['filas'][-1], ['Total propuesto', '', '', '20.00', '', ''])

    def test_referencia_borrador_nuevo_muestra_mes_sin_reconstruirlo_desde_trimestre(self):
        contenido = dict(pac_version=2, compras=[dict(item='Equipo en borrador', cantidad='2', costo_unitario='10',
            justificacion='Sustento', area_id='unidad', area_nombre='Unidad completa', tipo_necesidad='dotacion',
            mes_compra='7', trimestre='1')])
        with patch('apps.documentos.models.expediente.DocumentoElaborado.objects.filter') as consulta:
            consulta.return_value.first.return_value = SimpleNamespace(contenido=contenido)
            bloques = _detalle_anual(self.anual(), None)
        self.assertEqual(bloques[0]['cabecera'], ['Bien o servicio', 'Área', 'Cantidad propuesta', 'Mes previsto', 'Semestre'])
        self.assertEqual(bloques[0]['filas'], [['Equipo en borrador', 'Unidad completa', '2', 'Julio', '2']])

    def test_egresos_solo_usa_movimientos_confirmados_del_semestre_y_de_la_unidad(self):
        with patch('apps.finanzas.models.finanzas.MovimientoFinancieroUnidad.objects.filter') as consulta:
            consulta.return_value.values.return_value.annotate.return_value.order_by.return_value = [
                dict(fuente_fondos='presupuesto_institucional', total=Decimal('125.50'), registros=2),
                dict(fuente_fondos='proyecto', total=Decimal('24.50'), registros=1)]
            bloques = _bloques_egresos(self.documento, self.inicio, self.fin)
        consulta.assert_called_once_with(unidad_id=7, tipo='egreso', estado='confirmado',
                                        fecha_movimiento__range=(self.inicio, self.fin))
        self.assertIn(('Total registrado (USD)', '150.00'), bloques[0]['pares'])
        self.assertIn(('Movimientos confirmados', '3'), bloques[0]['pares'])
        self.assertIn('No se asignan a partidas', bloques[-1]['texto'])
        self.assertNotIn('ítem', str(consulta.call_args).casefold())

    def test_sin_egresos_no_se_declara_una_ejecucion_presupuestaria_total(self):
        with patch('apps.finanzas.models.finanzas.MovimientoFinancieroUnidad.objects.filter') as consulta:
            consulta.return_value.values.return_value.annotate.return_value.order_by.return_value = []
            bloques = _bloques_egresos(self.documento, self.inicio, self.fin)
        self.assertIn(('Total registrado (USD)', '0.00'), bloques[0]['pares'])
        self.assertIn('No hay egresos confirmados', bloques[1]['texto'])

    def test_los_datos_legacy_son_antecedentes_de_solo_lectura(self):
        contenido = dict(inversion=[dict(categoria='equipos'), dict(item='Equipo anterior',
            cantidad='2', costo_unitario='15')], sin_inversion_justificacion='<p>Nota previa.</p>')
        original = deepcopy(contenido)
        bloques = _bloques_antecedente(contenido)
        self.assertEqual(contenido, original)
        self.assertIn('No constituye una nueva solicitud', bloques[0]['texto'])
        self.assertEqual(bloques[1]['filas'], [['Equipo anterior', '2', '30.00']])
        self.assertEqual(bloques[-1]['texto'], 'Nota previa.')

    def test_la_captura_fijada_no_cambia_al_actualizar_las_fuentes(self):
        fuente = [dict(tipo='pares', titulo='Datos al emitir', pares=[('Total', '150.00')])]
        with patch('apps.documentos.presentation.recursos_periodo._bloques_actuales', return_value=fuente) as consulta:
            contenido = fijar_recursos(self.documento, self.inicio, self.fin, {})
        consulta.assert_called_once()
        with patch('apps.documentos.presentation.recursos_periodo._bloques_actuales',
                   side_effect=AssertionError('Una emisión reutiliza sus fuentes conservadas.')):
            bloques = bloques_recursos(self.documento, self.inicio, self.fin, contenido)
        bloques[0]['pares'][0] = ('Total', '999.00')
        self.assertEqual(contenido['recursos_periodo_fuentes']['bloques'][0]['pares'][0], ('Total', '150.00'))

    def test_otra_unidad_o_tramo_no_reutiliza_una_captura_ajena(self):
        with patch('apps.documentos.presentation.recursos_periodo._bloques_actuales', return_value=[]):
            contenido = fijar_recursos(self.documento, self.inicio, self.fin, {})
        for campo, valor in (('unidad', 8), ('anio', 2028), ('inicio', '2027-07-01')):
            with self.subTest(campo=campo):
                propuesta = deepcopy(contenido)
                propuesta['recursos_periodo_fuentes'][campo] = valor
                with patch('apps.documentos.presentation.recursos_periodo._bloques_actuales', return_value=[]) as consulta:
                    bloques_recursos(self.documento, self.inicio, self.fin, propuesta)
                consulta.assert_called_once()

    def test_las_cuatro_tipologias_consultan_las_mismas_fuentes_por_unidad(self):
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(tipo=tipo):
                self.documento.unidad.codigo_base = tipo
                with patch('apps.documentos.presentation.recursos_periodo._bloques_actuales', return_value=[]) as consulta:
                    resultado = fijar_recursos(self.documento, self.inicio, self.fin, {})
                consulta.assert_called_once()
                self.assertEqual(consulta.call_args.args[:3], (self.documento, self.inicio, self.fin))
                self.assertEqual(consulta.call_args.args[3]['recursos_periodo_version'], 1)
                self.assertEqual(resultado['recursos_periodo_fuentes']['unidad'], 7)


class RecursosPeriodoBDTests(TestCase):
    def setUp(self):
        from apps.directorio_unidades.models.core import Unidad

        self.actor = get_user_model().objects.create_user(username='recursos-periodo-autor')
        self.unidad = Unidad.objects.create(nombre='Unidad de recursos del semestre', slug='recursos-periodo-bd',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2025, 1, 1))
        self.otra_unidad = Unidad.objects.create(nombre='Otra unidad de recursos', slug='recursos-periodo-otra',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2025, 1, 1))
        self.documento = SimpleNamespace(pk=20, unidad_id=self.unidad.pk, unidad=self.unidad, anio=2027)
        self.inicio, self.fin = date(2027, 1, 1), date(2027, 6, 30)

    def movimiento(self, **cambios):
        from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad

        datos = dict(unidad=self.unidad, tipo='egreso', categoria='operacion', fuente_fondos='presupuesto_institucional',
            estado='confirmado', fecha_movimiento=self.inicio, monto=Decimal('10.00'),
            descripcion='Egreso registrado con respaldo', creado_por=self.actor, actualizado_por=self.actor,
            referencia='Factura de prueba', comprobante='finanzas/comprobantes/prueba-recursos.pdf',
            procedimiento_solicitado='publico', procedimiento_verificado=True,
            referencia_autorizacion='Acto de prueba autorizado por delegado', certificacion_presupuestaria='CP-prueba')
        datos.update(cambios)
        return MovimientoFinancieroUnidad.objects.create(**datos)

    def test_selecciona_la_propuesta_para_ejecucion_actual_sin_confundir_ano_ni_unidad(self):
        from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente

        exigido, _ = DocumentoExigido.objects.get_or_create(codigo='PLAN-COMPRAS-ANUAL',
            defaults=dict(nombre='Plan anual de necesidades', carpeta='planeacion', fuente_reporte='compras'))
        actual = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido, anio=2026)
        DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido, anio=2027)
        DocumentoExpediente.objects.create(unidad=self.otra_unidad, exigido=exigido, anio=2026)
        self.assertEqual(_plan_anual(self.documento).pk, actual.pk)

    def test_agrega_solo_egresos_confirmados_de_la_unidad_y_del_semestre(self):
        self.movimiento(monto=Decimal('125.50'))
        self.movimiento(monto=Decimal('24.50'), fuente_fondos='proyecto', fecha_movimiento=self.fin)
        self.movimiento(estado='pendiente', monto=Decimal('300'))
        self.movimiento(estado='anulado', monto=Decimal('400'), motivo_anulacion='Registro duplicado')
        self.movimiento(tipo='ingreso', categoria='otro_ingreso', monto=Decimal('500'))
        self.movimiento(unidad=self.otra_unidad, monto=Decimal('600'))
        self.movimiento(fecha_movimiento=date(2027, 7, 1), monto=Decimal('700'))
        self.movimiento(fecha_movimiento=date(2026, 12, 31), monto=Decimal('800'))
        bloques = _bloques_egresos(self.documento, self.inicio, self.fin)
        self.assertIn(('Total registrado (USD)', '150.00'), bloques[0]['pares'])
        self.assertIn(('Movimientos confirmados', '2'), bloques[0]['pares'])
        self.assertEqual(len(bloques[1]['filas']), 2)

    def test_fuentes_fijadas_no_cambian_por_nuevos_movimientos(self):
        self.movimiento(monto=Decimal('10'))
        fijado = fijar_recursos(self.documento, self.inicio, self.fin, {})
        self.movimiento(monto=Decimal('20'))
        with self.assertNumQueries(0):
            conservados = bloques_recursos(self.documento, self.inicio, self.fin, fijado)
        renovado = fijar_recursos(self.documento, self.inicio, self.fin, fijado, actualizar=True)
        def resumen(bloques):
            return next(b for b in bloques if b.get('titulo') ==
                'Egresos confirmados registrados en el semestre')['pares']
        self.assertIn(('Total registrado (USD)', '10.00'), resumen(conservados))
        self.assertIn(('Total registrado (USD)', '30.00'), resumen(renovado['recursos_periodo_fuentes']['bloques']))

    def test_inventario_real_por_cada_tipologia_sin_duplicar_equipo_compartido(self):
        from apps.directorio_unidades.models.core import Unidad
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.consumibles import Consumible
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.software import SoftwareDisponible
        from apps.recursos.models.unidades import UnidadEquipo
        from apps.documentos.presentation.recursos_periodo import _bloques_inventario

        for indice, tipo in enumerate(('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')):
            with self.subTest(tipo=tipo):
                unidad = Unidad.objects.create(nombre=f'Inventario {tipo}', slug=f'recursos-inventario-{indice}',
                    dependencia=tipo, administrador=self.actor, fecha_inicio=date(2025, 1, 1))
                equipo = EquiposServicios.objects.create(codigo=f'REC-TIPO-{indice}', nombre=f'Equipo {tipo}')
                activo = UnidadEquipo.objects.create(equipo=equipo, laboratorio=unidad,
                    codigo_unidad=f'REC-ACTIVO-{indice}', estado_unidad='disponible')
                activo.laboratorios.add(unidad)
                UnidadEquipo.objects.create(equipo=equipo, laboratorio=unidad,
                    codigo_unidad=f'REC-INACTIVO-{indice}', activa=False)
                SoftwareDisponible.objects.create(unidad=unidad, nombre='Software disponible')
                SoftwareDisponible.objects.create(unidad=unidad, nombre='Software retirado', activo=False)
                Consumible.objects.create(unidad=unidad, codigo=f'REC-IN-{indice}', nombre='Insumo registrado')
                Consumible.objects.create(unidad=unidad, codigo=f'REC-IN-OFF-{indice}', nombre='Insumo inactivo', activo=False)
                EspacioReservable.objects.create(unidad=unidad, codigo='ESP-A', nombre='Espacio registrado')
                EspacioReservable.objects.create(unidad=unidad, codigo='ESP-B', nombre='Espacio inactivo', activo=False)
                pares = dict(_bloques_inventario(SimpleNamespace(unidad_id=unidad.pk))[0]['pares'])
                self.assertEqual(pares['Equipos activos registrados'], '1')
                self.assertEqual(pares['Equipos con estado disponible o en uso'], '1')
                self.assertEqual(pares['Software activo registrado'], '1')
                self.assertEqual(pares['Insumos activos registrados'], '1')
                self.assertEqual(pares['Espacios activos registrados'], '1')
