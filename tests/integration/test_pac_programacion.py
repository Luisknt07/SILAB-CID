"""Adquisiciones por área y mes, con referencias propias e históricos intactos."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
import json

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.pac_universitario import (
    ENCABEZADOS_CLASIFICADOS, ENCABEZADOS_CONSOLIDADO, ENCABEZADOS_PROGRAMACION,
    bloques_pac, datos_editor_pac, leer_pac, preparar_pac, render_pac_xlsx,
    semestre_compra, validar_pac,
)
from apps.gestion_unidades.models.espacios import EspacioReservable
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.test_pac_universitario import necesidad


def contenido_v2(**cambios):
    fila = necesidad(area_id='unidad', area_nombre='Unidad completa', tipo_necesidad='dotacion',
        mes_compra='1', equipos_referencia=[], equipo_referencia='')
    fila.update(cambios)
    return dict(pac_version=2, compras=[fila])


class ProgramacionPacPuraTests(SimpleTestCase):
    def test_semestre_depende_del_calendario_y_no_del_periodo_academico(self):
        for mes in range(1, 13):
            self.assertEqual(semestre_compra(str(mes)), 1 if mes <= 6 else 2)
        for mes in ('', '0', '13', '-1', '1.5', True, None):
            self.assertIsNone(semestre_compra(mes))

    def test_validacion_nueva_exige_area_motivo_y_mes_sin_imponer_codigos_oficiales(self):
        contenido = contenido_v2()
        self.assertTrue(all(h['severidad'] == 'revision' for h in validar_pac(contenido)))
        contenido['compras'][0].update(area_id='', tipo_necesidad='', mes_compra='')
        reglas = {h['regla'] for h in validar_pac(contenido) if h['severidad'] == 'bloqueo'}
        self.assertEqual(reglas, {'pac_area_pendiente', 'pac_tipo_pendiente', 'pac_programacion_pendiente'})
        contenido['pac_version'] = 1
        self.assertTrue(all(h['severidad'] == 'revision' for h in validar_pac(contenido)))

    def test_reposicion_identifica_equipo_y_no_acepta_json_ajeno_a_la_estructura(self):
        self.assertIn('pac_reposicion_sin_equipo', {h['regla'] for h in validar_pac(contenido_v2(tipo_necesidad='reposicion'))})
        for equipos in ('[true]', '{}', '["texto"]', [-2]):
            self.assertIn('pac_equipos_invalidos', {h['regla'] for h in validar_pac(contenido_v2(equipos_referencia=equipos))})

    def test_migrar_no_inventa_mes_ni_motivo_y_no_cambia_archivo_anterior(self):
        legado = dict(pac_version=1, compras=[necesidad(trimestre='3')])
        original = deepcopy(legado)
        nuevo = preparar_pac(legado)
        self.assertEqual(nuevo['pac_version'], 2)
        self.assertEqual(nuevo['compras'][0]['mes_compra'], '')
        self.assertEqual(nuevo['compras'][0]['tipo_necesidad'], '')
        self.assertIsNone(nuevo['compras'][0]['semestre'])
        self.assertEqual(legado, original)
        self.assertEqual(nuevo['compras'][0]['id_necesidad'], legado['compras'][0]['id_necesidad'])

    def test_dos_compras_en_meses_distintos_suman_solo_sus_cantidades(self):
        contenido = contenido_v2(cantidad='2', costo_unitario='10', mes_compra='6')
        contenido['compras'].append(dict(necesidad(), area_id='unidad', area_nombre='Unidad completa',
            tipo_necesidad='dotacion', mes_compra='7', cantidad='3', costo_unitario='10'))
        datos = datos_editor_pac(contenido)
        self.assertEqual(datos['pac_total'], Decimal('50'))
        self.assertEqual([f['semestre'] for f in datos['filas_pac']], [1, 2])
        pdf = bloques_pac(contenido)[0]
        self.assertEqual(pdf['cabecera'], ['Área', 'Bien o servicio', 'Cantidad', 'Valor unitario (USD)', 'Total (USD)', 'Mes', 'Semestre'])
        self.assertEqual(pdf['filas'][-1][4], '50.00')
        self.assertEqual(pdf['filas'][0][-2:], ['Junio', '1'])
        self.assertEqual(pdf['filas'][1][-2:], ['Julio', '2'])

    def test_excel_conserva_matriz_y_anade_programacion_sin_perder_sustento(self):
        contenido = contenido_v2(tipo_necesidad='reposicion', equipos_referencia=['3'],
            equipo_referencia='EQ-001 · Equipo actual', area_nombre='Área técnica', mes_compra='7',
            justificacion='<p>El uso registrado exige sustituir el equipo actual.</p>', cpc='000123', partida='0053')
        original = deepcopy(contenido)
        libro = load_workbook(BytesIO(render_pac_xlsx(contenido, 'Unidad solicitante', 2027)))
        self.addCleanup(libro.close)
        self.assertEqual(libro.sheetnames, ['CONSOLIDADO', 'PAC', 'NO PAC', 'PROGRAMACION'])
        self.assertEqual(tuple(c.value for c in libro['CONSOLIDADO'][4]), ENCABEZADOS_CONSOLIDADO)
        self.assertEqual(tuple(c.value for c in libro['PAC'][4]), ENCABEZADOS_CLASIFICADOS)
        hoja = libro['PROGRAMACION']
        self.assertEqual(tuple(c.value for c in hoja[4]), ENCABEZADOS_PROGRAMACION)
        self.assertEqual((hoja['A5'].value, hoja['B5'].value, hoja['C5'].value),
            ('Área técnica', 'Reposición', 'EQ-001 · Equipo actual'))
        self.assertEqual((hoja['H5'].value, hoja['I5'].value), (2, 'Julio'))
        self.assertEqual(hoja['G5'].value, '=E5*F5')
        self.assertEqual(hoja['G6'].value, '=SUM(G5:G5)')
        for texto in ('Área técnica', 'Reposición', 'EQ-001', 'Julio', 'semestre 2', 'uso registrado'):
            self.assertIn(texto, libro['CONSOLIDADO']['M5'].value)
        self.assertEqual(contenido, original)

    def test_excel_programacion_no_presenta_total_parcial_y_trata_textos_como_texto(self):
        contenido = contenido_v2(area_nombre='=1+1', justificacion='@texto', costo_unitario='')
        libro = load_workbook(BytesIO(render_pac_xlsx(contenido, 'Unidad', 2027)))
        self.addCleanup(libro.close)
        hoja = libro['PROGRAMACION']
        self.assertEqual(hoja['A5'].data_type, 's')
        self.assertEqual(hoja['J5'].data_type, 's')
        self.assertIsNone(hoja['G6'].value)
        self.assertIn('suma parcial', hoja['G6'].comment.text)

    def test_editor_expone_campos_nuevos_aun_para_lectura_v1(self):
        contenido = dict(pac_version=1, compras=[necesidad(equipos_referencia=['3', 4])])
        original = deepcopy(contenido)
        datos = datos_editor_pac(contenido)
        self.assertTrue({'area_id', 'tipo_necesidad', 'mes_compra', 'equipos_referencia'} <= datos['campos_pac'].keys())
        self.assertEqual(datos['filas_pac'][0]['equipos_ids'], ['3', '4'])
        self.assertEqual(json.loads(datos['filas_pac'][0]['equipos_json']), ['3', '4'])
        self.assertEqual(contenido, original)


class FuentesDeProgramacionPacTests(BaseDeRedaccion):
    def formulario(self, area='unidad', equipos=None):
        post = QueryDict(mutable=True)
        fila = contenido_v2()['compras'][0]
        fila.update(id_necesidad='', area_id=area, equipos_referencia=json.dumps(equipos or []),
                    area_nombre='Nombre falsificado', equipo_referencia='Código falsificado')
        for clave, valor in fila.items():
            post.setlist('compras__' + clave, [str(valor)])
        return post

    def test_area_y_equipo_salen_de_registros_propios_y_no_del_post(self):
        area = self.unidad.espacios_reservables.get()
        post = self.formulario(str(area.pk), [str(self.unidad_equipo.pk)])
        contenido = leer_pac(post, {}, unidad=self.unidad)
        fila = contenido['compras'][0]
        self.assertEqual(fila['area_nombre'], area.nombre)
        self.assertIn(self.unidad_equipo.codigo_unidad, fila['equipo_referencia'])
        self.assertNotIn('falsificado', fila['equipo_referencia'])
        self.assertEqual(fila['equipos_referencia'], [str(self.unidad_equipo.pk)])

    def test_no_admite_area_de_otra_unidad_ni_equipo_no_registrado(self):
        otra = Unidad.objects.create(nombre='Otra unidad de fuentes PAC', slug='otra-fuentes-pac',
            dependencia='observatorios', fecha_inicio=self.unidad.fecha_inicio)
        area = EspacioReservable.objects.create(unidad=otra, codigo='AJENO', nombre='Área ajena')
        for post in (self.formulario(str(area.pk)), self.formulario(equipos=['999999999'])):
            with self.subTest(post=post), self.assertRaises(ValidationError):
                leer_pac(post, {}, unidad=self.unidad)

    def test_revisa_area_retirada_y_equipo_transferido_despues_del_guardado(self):
        area = self.unidad.espacios_reservables.get()
        contenido = leer_pac(self.formulario(str(area.pk), [str(self.unidad_equipo.pk)]), {}, unidad=self.unidad)
        EspacioReservable.objects.filter(pk=area.pk).update(activo=False)
        self.unidad_equipo.laboratorios.clear()
        self.unidad_equipo.laboratorio = None
        self.unidad_equipo.save(update_fields=['laboratorio'])
        reglas = {h['regla'] for h in validar_pac(contenido, unidad=self.unidad)}
        self.assertIn('pac_area_ajena', reglas)
        self.assertIn('pac_equipo_ajeno', reglas)

    def test_proyeccion_editable_corrige_solo_nombres_generados_comprobados_y_no_archivo(self):
        nombre, codigo = self.unidad_equipo.equipo.nombre, self.unidad_equipo.codigo_unidad
        for generado in (f'{nombre} ({codigo})', f'{nombre} · {codigo}', f'{nombre} ({codigo}) · {codigo}'):
            with self.subTest(generado=generado):
                original = contenido_v2(item=generado, equipos_referencia=[str(self.unidad_equipo.pk)],
                    especificaciones='Características registradas sin cambiar.', equipo_referencia='Referencia original')
                copia = deepcopy(original)
                editable = preparar_pac(original, unidad=self.unidad)
                self.assertEqual(editable['compras'][0]['item'], nombre)
                self.assertEqual(editable['compras'][0]['especificaciones'], original['compras'][0]['especificaciones'])
                self.assertEqual(editable['compras'][0]['id_necesidad'], original['compras'][0]['id_necesidad'])
                self.assertEqual(original, copia)
                libro = load_workbook(BytesIO(render_pac_xlsx(original, self.unidad.nombre, 2027, borrador=False)))
                try:
                    self.assertEqual(libro['CONSOLIDADO']['D5'].value, generado)
                finally:
                    libro.close()

    def test_post_normaliza_sufijo_generado_pero_conserva_nombre_escrito_y_especificaciones(self):
        nombre, codigo = self.unidad_equipo.equipo.nombre, self.unidad_equipo.codigo_unidad
        for item, esperado in ((f'{nombre} ({codigo})', nombre),
                (f'{nombre} · {codigo}', nombre), (f'DIR/{nombre} ({codigo})', f'DIR/{nombre} ({codigo})'),
                (f'{nombre} de alto rendimiento ({codigo})', f'{nombre} de alto rendimiento ({codigo})')):
            with self.subTest(item=item):
                post = self.formulario(equipos=[str(self.unidad_equipo.pk)])
                post.setlist('compras__item', [item])
                post.setlist('compras__especificaciones', ['Configuración requerida.'])
                fila = leer_pac(post, {}, unidad=self.unidad)['compras'][0]
                self.assertEqual(fila['item'], esperado)
                self.assertEqual(fila['especificaciones'], 'Configuración requerida.')
                self.assertEqual(fila['equipos_referencia'], [str(self.unidad_equipo.pk)])

    def test_nombre_con_codigo_sin_activo_propio_seleccionado_no_se_modifica(self):
        nombre, codigo = self.unidad_equipo.equipo.nombre, self.unidad_equipo.codigo_unidad
        for referencias, item in (([], f'{nombre} ({codigo})'),
                (['999999999'], f'{nombre} ({codigo})'),
                ([str(self.unidad_equipo.pk)], f'{nombre} (CODIGO-NO-COMPROBADO)')):
            with self.subTest(referencias=referencias, item=item):
                original = contenido_v2(item=item, equipos_referencia=referencias)
                self.assertEqual(preparar_pac(original, unidad=self.unidad)['compras'][0]['item'], item)
