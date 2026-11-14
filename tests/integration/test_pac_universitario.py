"""Identidad de necesidades y transferencia segura al formato universitario."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.pac_universitario import (
    ENCABEZADOS_CLASIFICADOS, ENCABEZADOS_CONSOLIDADO, bloques_pac,
    datos_editor_pac, identidades_formulario_pac, leer_pac, observaciones_pac, preparar_pac, render_pac_xlsx, validar_pac,
)


def necesidad(**cambios):
    fila = dict(id_necesidad=str(uuid4()), item='Equipo de prueba', cantidad='2', costo_unitario='12.50',
        justificacion='Necesidad documentada para actividades de la unidad.',
        cpc='', partida='', clasificacion_pac='por_definir', fuente_pac='', observaciones='')
    return dict(fila, **cambios)


class PreparacionPacTests(SimpleTestCase):
    def test_proyeccion_legacy_conserva_datos_y_no_modifica_la_redaccion(self):
        contenido = dict(compras=[dict(item='Material disponible', cantidad='4', costo_unitario='3',
            categoria='insumos', prioridad='alta', fuente='proyecto', trimestre='2')])
        original = deepcopy(contenido)
        nuevo = preparar_pac(contenido)
        self.assertEqual(contenido, original)
        self.assertEqual(nuevo['pac_version'], 2)
        fila = nuevo['compras'][0]
        self.assertEqual(fila['clasificacion_pac'], 'por_definir')
        self.assertEqual(fila['fuente'], 'proyecto')
        self.assertEqual(fila['mes_compra'], '')
        self.assertIsNone(fila['semestre'])
        self.assertNotIn('fuente_pac', fila)
        self.assertEqual(str(UUID(fila['id_necesidad'])), fila['id_necesidad'])
        self.assertEqual(preparar_pac(nuevo), nuevo)

    def test_no_asigna_identidad_a_la_fila_inicial_vacia(self):
        nuevo = preparar_pac(dict(compras=[{}, dict(categoria='equipos'), dict(clasificacion_pac='por_definir')]))
        self.assertEqual(nuevo['compras'], [])

    def test_primer_guardado_legacy_admite_ids_del_get_y_luego_se_reordenan(self):
        legado = dict(compras=[dict(item='Primera necesidad', cantidad='1', costo_unitario='2'),
                              dict(item='Segunda necesidad', cantidad='3', costo_unitario='4')])
        visto = preparar_pac(legado)
        self.assertEqual(visto, preparar_pac(legado))
        ids = [f['id_necesidad'] for f in visto['compras']]
        post = QueryDict(mutable=True)
        post.setlist('compras__id_necesidad', ids)
        post.setlist('compras__item', ['Nombre corregido', 'Segunda necesidad'])
        guardado = leer_pac(post, legado)
        self.assertEqual([f['id_necesidad'] for f in guardado['compras']], ids)
        post.setlist('compras__id_necesidad', ids[::-1])
        post.setlist('compras__item', ['Segunda necesidad', 'Nombre corregido'])
        reordenado = leer_pac(post, guardado)
        self.assertEqual([f['id_necesidad'] for f in reordenado['compras']], ids[::-1])

    def test_ids_de_autoguardado_se_alinean_con_las_filas_vacias_del_dom(self):
        post = QueryDict(mutable=True)
        post.setlist('compras__item', ['Nueva necesidad', '', 'Otra necesidad', ''])
        post.setlist('compras__clasificacion_pac', ['', 'por_definir', 'no_pac', ''])
        guardado = leer_pac(post, {})
        respuesta = identidades_formulario_pac(post, guardado)
        self.assertEqual(len(respuesta), 4)
        self.assertEqual(respuesta[1], '')
        self.assertEqual(respuesta[3], '')
        self.assertEqual([respuesta[0], respuesta[2]], [f['id_necesidad'] for f in guardado['compras']])
        post.setlist('compras__id_necesidad', respuesta)
        self.assertEqual(leer_pac(post, guardado)['compras'], guardado['compras'])

    def test_conserva_identificador_al_guardar_y_legacy_no_visible(self):
        fila = necesidad()
        fila.update(categoria='equipos', prioridad='alta', fuente='institucional', trimestre='3')
        anterior = dict(pac_version=1, centro_costo='Agrupador confirmado', compras=[fila])
        post = QueryDict(mutable=True)
        post.setlist('compras__id_necesidad', [fila['id_necesidad'], ''])
        post.setlist('compras__item', ['Nombre corregido', ''])
        post.setlist('compras__cantidad', ['3', ''])
        post.setlist('compras__costo_unitario', ['10', ''])
        post.setlist('compras__justificacion', ['Sustento revisado', ''])
        guardado = leer_pac(post, anterior)
        self.assertEqual(len(guardado['compras']), 1)
        nueva = guardado['compras'][0]
        self.assertEqual(nueva['id_necesidad'], fila['id_necesidad'])
        self.assertEqual(nueva['item'], 'Nombre corregido')
        self.assertEqual((nueva['categoria'], nueva['prioridad'], nueva['fuente'], nueva['trimestre']),
                         ('equipos', 'alta', 'institucional', '3'))
        self.assertEqual(guardado['centro_costo'], anterior['centro_costo'])

    def test_identificador_ajeno_o_repetido_no_se_acepta(self):
        fila = necesidad()
        anterior = dict(compras=[fila])
        post = QueryDict(mutable=True)
        post.setlist('compras__item', ['Otra necesidad'])
        post.setlist('compras__id_necesidad', [str(uuid4())])
        with self.assertRaisesMessage(ValidationError, 'otro documento'):
            leer_pac(post, anterior)
        post.setlist('compras__item', ['Una necesidad', 'Su duplicado'])
        post.setlist('compras__id_necesidad', [fila['id_necesidad'], fila['id_necesidad']])
        with self.assertRaisesMessage(ValidationError, 'otro documento'):
            leer_pac(post, anterior)

    def test_nueva_fila_recibe_uuid_del_servidor_y_codigos_textuales(self):
        post = QueryDict(mutable=True)
        for clave, valor in dict(item='Insumo de prueba', cantidad='2', costo_unitario='3.50',
            justificacion='Sustento', cpc='000123.5', partida='00530404', fuente_pac='001').items():
            post.setlist('compras__' + clave, [valor])
        nuevo = leer_pac(post, {})
        fila = nuevo['compras'][0]
        self.assertTrue(UUID(fila['id_necesidad']))
        self.assertEqual((fila['cpc'], fila['partida'], fila['fuente_pac']), ('000123.5', '00530404', '001'))
        self.assertEqual(fila['clasificacion_pac'], 'por_definir')

    def test_clasificacion_pendiente_no_bloquea_presentar_requerimientos(self):
        contenido = dict(pac_version=1, centro_costo='', compras=[necesidad()])
        hallazgos = validar_pac(contenido)
        self.assertTrue(hallazgos)
        self.assertTrue(all(h['severidad'] == 'revision' for h in hallazgos))
        self.assertTrue(any('CPC' in h['mensaje'] and 'partida' in h['mensaje'] for h in hallazgos))
        self.assertEqual(validar_pac(dict(compras=[dict(item='Legado')])), [])

    def test_estructura_enum_e_identidades_invalidas_si_bloquean(self):
        for contenido in (dict(pac_version=1, compras={}),
            dict(pac_version=1, compras=['texto']),
            dict(pac_version=1, compras=[dict(necesidad(), clasificacion_pac='inventado')]),
            dict(pac_version=1, compras=[dict(necesidad(), cpc={'codigo': '012'})]),
            dict(pac_version=1, compras=[dict(necesidad(), id_necesidad='no-es-uuid')])):
            with self.subTest(contenido=contenido):
                self.assertTrue(any(h['severidad'] == 'bloqueo' for h in validar_pac(contenido)))

    def test_editor_y_pdf_calculan_mismos_importes_sin_columnas_ilegibles(self):
        contenido = dict(pac_version=1, compras=[necesidad(), dict(necesidad(), cantidad='3', costo_unitario='0.10')])
        datos = datos_editor_pac(contenido)
        self.assertEqual(datos['pac_total'], Decimal('25.30'))
        self.assertEqual(datos['filas_pac'][0]['total'], Decimal('25.00'))
        self.assertEqual({g['clave'] for g in datos['grupos_pac']}, {'necesidad', 'transferencia'})
        bloques = bloques_pac(contenido)
        self.assertEqual(bloques[0]['cabecera'], ['Bien o servicio', 'Cantidad', 'Valor unitario (USD)', 'Total (USD)'])
        self.assertEqual(bloques[0]['filas'][-1][-1], '25.30')
        self.assertTrue(all(len(b.get('cabecera', [])) <= 6 for b in bloques))

    def test_importe_pendiente_no_se_presenta_como_un_total_parcial(self):
        contenido = dict(pac_version=1, compras=[necesidad(costo_unitario='0'),
            necesidad(item='Pendiente de cotización', costo_unitario='')])
        original = deepcopy(contenido)
        datos = datos_editor_pac(contenido)
        self.assertEqual(datos['filas_pac'][0]['total'], Decimal(0))
        self.assertIsNone(datos['filas_pac'][1]['total'])
        self.assertIsNone(datos['pac_total'])
        self.assertEqual(bloques_pac(contenido)[0]['filas'][-1][-1], 'Por completar')
        self.assertEqual(contenido, original)
        for cantidad in ('', '0', '-1', 'NaN'):
            with self.subTest(cantidad=cantidad):
                self.assertIsNone(datos_editor_pac(dict(compras=[necesidad(cantidad=cantidad)]))['pac_total'])
        self.assertEqual(datos_editor_pac(dict(compras=[necesidad(costo_unitario='0')]))['pac_total'], Decimal(0))
        self.assertEqual(datos_editor_pac(dict(compras=[]))['pac_total'], Decimal(0))


class ExportacionPacTests(SimpleTestCase):
    @staticmethod
    def libro(contenido):
        return load_workbook(BytesIO(render_pac_xlsx(contenido, 'Unidad solicitante de prueba', 2027)), data_only=False)

    def test_columnas_hojas_clasificacion_explicita_y_formulas(self):
        filas = [dict(necesidad(), clasificacion_pac='pac', cpc='000001234', partida='00530404', fuente_pac='001'),
                 dict(necesidad(), clasificacion_pac='no_pac', item='Servicio NO PAC'), necesidad()]
        libro = self.libro(dict(pac_version=1, centro_costo='Centro agrupador', compras=filas))
        self.addCleanup(libro.close)
        self.assertEqual(libro.sheetnames, ['CONSOLIDADO', 'PAC', 'NO PAC'])
        cons = libro['CONSOLIDADO']
        self.assertEqual(tuple(c.value for c in cons[4]), ENCABEZADOS_CONSOLIDADO)
        self.assertEqual(tuple(c.value for c in libro['PAC'][4]), ENCABEZADOS_CLASIFICADOS)
        self.assertEqual(tuple(c.value for c in libro['NO PAC'][4]), ENCABEZADOS_CLASIFICADOS)
        self.assertEqual([cons[f'K{n}'].value for n in (5, 6, 7)], ['PAC', 'NOPAC', None])
        self.assertEqual((cons['B5'].value, cons['C5'].value), ('Unidad solicitante de prueba', 'Centro agrupador'))
        self.assertEqual((cons['E5'].value, cons['F5'].value), (2, 12.5))
        self.assertEqual(cons['G5'].value, '=E5*F5')
        self.assertEqual(cons['I5'].value, '=IF(J5="","",LEFT(J5,2))')
        self.assertEqual(cons['G8'].value, '=SUM(G5:G7)')
        self.assertEqual(libro['PAC']['G6'].value, '=SUM(G5:G5)')
        self.assertEqual(libro['NO PAC']['A5'].value, 2)
        self.assertEqual(cons.freeze_panes, 'D5')

    def test_codigos_preservan_ceros_y_usuario_no_inyecta_formulas(self):
        fila = dict(necesidad(), cpc='0000123', partida='00530404', fuente_pac='001',
                    item='=HYPERLINK("https://example.org","Texto")', observaciones='+SUM(1,2)')
        libro = self.libro(dict(pac_version=1, centro_costo='@otra-celda', compras=[fila]))
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertEqual((hoja['H5'].value, hoja['J5'].value, hoja['L5'].value), ('0000123', '00530404', '001'))
        for referencia in ('C5', 'D5', 'H5', 'J5', 'L5', 'M5'):
            self.assertEqual(hoja[referencia].data_type, 's')
        self.assertEqual(hoja['D5'].value, fila['item'])
        self.assertEqual(hoja['M5'].value, observaciones_pac(fila))

    def test_sustento_se_conserva_en_observaciones_sin_duplicarse_y_alto_se_adapta(self):
        sustento = 'Se requiere material para las actividades de la unidad. ' * 30
        fila = necesidad(justificacion='<p>' + sustento + '</p>', observaciones=sustento.strip())
        libro = self.libro(dict(pac_version=1, compras=[fila]))
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertEqual(hoja['M5'].value, 'Justificación: ' + sustento.strip())
        self.assertNotIn('Observaciones:', hoja['M5'].value)
        self.assertGreater(hoja.row_dimensions[5].height, 42)
        self.assertTrue(hoja['M5'].alignment.wrap_text)

    def test_legacy_exporta_borrador_sin_inventar_cpc_partida_o_fuente(self):
        libro = self.libro(dict(compras=[dict(item='Material anterior', cantidad='4', costo_unitario='3',
            categoria='insumos', prioridad='alta', fuente='proyecto', trimestre='2')]))
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertIn('2027', hoja['A2'].value)
        self.assertIn('BORRADOR', hoja['A3'].value)
        self.assertIn('No constituye PAC aprobado', hoja['A3'].comment.text)
        self.assertEqual([hoja[ref].value for ref in ('C5', 'H5', 'J5', 'K5', 'L5')], [None] * 5)
        self.assertEqual(libro['PAC']['G5'].value, '=0')
        self.assertEqual(libro['NO PAC']['G5'].value, '=0')

    def test_importes_invalidos_no_generan_infinito_ni_formula_inyectada(self):
        libro = self.libro(dict(pac_version=1, compras=[dict(necesidad(), cantidad='NaN', costo_unitario='=1+2')]))
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertIsNone(hoja['E5'].value)
        self.assertIsNone(hoja['F5'].value)
        self.assertIsNone(hoja['G5'].value)

    def test_total_incompleto_queda_vacio_y_costo_cero_sigue_siendo_calculable(self):
        contenido = dict(pac_version=1, compras=[necesidad(costo_unitario='0', clasificacion_pac='pac'),
            necesidad(item='Falta cotización', costo_unitario='', clasificacion_pac='no_pac')])
        original = deepcopy(contenido)
        libro = self.libro(contenido)
        self.addCleanup(libro.close)
        hoja = libro['CONSOLIDADO']
        self.assertEqual(hoja['G5'].value, '=E5*F5')
        self.assertIsNone(hoja['G6'].value)
        self.assertIn('Completa', hoja['F6'].comment.text)
        self.assertEqual(hoja['A7'].value, 'TOTAL POR COMPLETAR (USD)')
        self.assertIsNone(hoja['G7'].value)
        self.assertIn('suma parcial', hoja['G7'].comment.text)
        self.assertEqual(libro['PAC']['G6'].value, '=SUM(G5:G5)')
        self.assertIsNone(libro['NO PAC']['G6'].value)
        self.assertEqual(contenido, original)
