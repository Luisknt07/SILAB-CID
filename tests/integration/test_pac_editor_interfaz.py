"""Las tarjetas PAC mantienen el contrato de guardado y clonado del editor."""
from decimal import Decimal
from html.parser import HTMLParser
import json
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.presentation.pac_universitario import datos_editor_pac, preparar_pac


class FilasPAC(HTMLParser):
    def __init__(self):
        super().__init__()
        self.filas = []
        self.actual = None
        self.en_cuerpo = False
        self.tablas = []
        self.pestanas = []
        self.paneles = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'button' and attrs.get('role') == 'tab':
            self.pestanas.append(attrs)
        if attrs.get('role') == 'tabpanel':
            self.paneles.append(attrs)
        if tag == 'table':
            self.tablas.append('pac-editor__tabla' in attrs.get('class', '').split())
        elif tag == 'tbody':
            self.en_cuerpo = bool(self.tablas and self.tablas[-1])
        elif tag == 'tr' and self.en_cuerpo:
            self.actual = dict(plantilla='data-fila-plantilla' in attrs, celdas=0, controles=[], secciones=[])
            self.filas.append(self.actual)
        elif tag == 'section' and self.actual is not None:
            self.actual['secciones'].append(attrs)
        elif tag == 'td' and self.actual is not None:
            self.actual['celdas'] += 1
        elif tag in ('input', 'select', 'textarea') and self.actual is not None and 'name' in attrs:
            self.actual['controles'].append(attrs)

    def handle_endtag(self, tag):
        if tag == 'tr':
            self.actual = None
        elif tag == 'tbody':
            self.en_cuerpo = False
        elif tag == 'table':
            self.tablas.pop()


class PacEditorInterfazTests(SimpleTestCase):
    def contexto(self):
        grupos = [dict(etiqueta='Bien o servicio', campos=[
            dict(clave='area_id', etiqueta='Área', tipo='opcion', opciones=(('unidad', 'Toda la unidad'), ('2', 'Área de fabricación'))),
            dict(clave='tipo_necesidad', etiqueta='Motivo', tipo='opcion', opciones=(('reposicion', 'Reposición'), ('dotacion', 'Dotación'))),
            dict(clave='item', etiqueta='Nombre del bien o servicio', tipo='texto'),
            dict(clave='cantidad', etiqueta='Cantidad', tipo='numero'),
            dict(clave='costo_unitario', etiqueta='Valor unitario (USD)', tipo='numero'),
            dict(clave='mes_compra', etiqueta='Mes de compra', tipo='opcion', opciones=tuple((str(n), str(n)) for n in range(1, 13))),
            dict(clave='justificacion', etiqueta='Justificación de la necesidad', tipo='multilinea'),
        ]), dict(etiqueta='Clasificación', campos=[
            dict(clave='cpc', etiqueta='CPC', tipo='texto'),
            dict(clave='partida', etiqueta='Partida', tipo='texto'),
            dict(clave='grupo', etiqueta='Grupo', tipo='texto'),
            dict(clave='clasificacion_pac', etiqueta='Clasificación', tipo='opcion',
                 opciones=(('PAC', 'PAC'), ('NOPAC', 'No PAC'))),
            dict(clave='fuente_pac', etiqueta='Fuente', tipo='texto',
                 ayuda='Código o denominación confirmado por el área administrativa; no equivale a la fuente interna.'),
            dict(clave='observaciones', etiqueta='Observaciones', tipo='multilinea'),
        ])]
        filas = [dict(valor=dict(id_necesidad='identificador-original', area_id='2', tipo_necesidad='reposicion', mes_compra='9',
            item='Pieza <especial>', cantidad='2', justificacion='Reponer el equipo que presenta una falla documentada.',
            costo_unitario='0', cpc='001234567', partida='530814', grupo='53', clasificacion_pac='',
            fuente_pac='', observaciones='Verificar cotización.'), total=Decimal(0), semestre=2,
            equipos_ids=['eq-1'], equipos_json='["eq-1"]')]
        return dict(dato=dict(version_pac=2, centro_costo='Dirección académica', grupos_pac=grupos, campos_pac={c['clave']: c for g in grupos for c in g['campos']},
            opciones_equipos=(('eq-1', 'EQ-01 · Equipo de fabricación'), ('eq-2', 'EQ-02 · Equipo de medición')),
            filas_pac=filas, pac_total=Decimal(0), fuentes_pac=(
            ('001', 'Recursos fiscales'), ('002', 'Recursos fiscales generados por instituciones'),
            ('003', 'Recursos provenientes de preasignaciones'))),
                    campo=SimpleNamespace(ayuda=''), documento=SimpleNamespace(estado='generado'))

    def render(self, contexto):
        html = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', contexto)
        parser = FilasPAC()
        parser.feed(html)
        return html, parser.filas

    def test_cada_necesidad_y_la_plantilla_guardan_las_mismas_columnas_sin_tabla_ancha(self):
        html, filas = self.render(self.contexto())
        self.assertEqual(len(filas), 2)
        self.assertEqual([f['celdas'] for f in filas], [1, 1])
        self.assertFalse(filas[0]['plantilla'])
        self.assertTrue(filas[1]['plantilla'])
        nombres = [c['name'] for c in filas[0]['controles']]
        self.assertEqual(nombres, [c['name'] for c in filas[1]['controles']])
        self.assertEqual(len(nombres), len(set(nombres)))
        self.assertNotIn('compras__grupo', nombres)
        self.assertIn('data-tabla="compras"', html)
        self.assertEqual(html.count('data-quitar-fila'), 2)

    def test_id_y_codigo_se_conservan_como_texto_sin_poblar_la_plantilla(self):
        html, filas = self.render(self.contexto())
        controles = {c['name']: c for c in filas[0]['controles']}
        plantilla = {c['name']: c for c in filas[1]['controles']}
        self.assertEqual(controles['compras__id_necesidad']['value'], 'identificador-original')
        self.assertEqual(controles['compras__cpc']['value'], '001234567')
        self.assertEqual(controles['compras__cpc']['type'], 'text')
        self.assertEqual(plantilla['compras__id_necesidad']['value'], '')
        self.assertEqual(plantilla['compras__item']['value'], '')
        self.assertIn('Pieza &lt;especial&gt;', html)

    def test_no_asigna_una_fuente_ni_clasificacion_a_una_necesidad_pendiente(self):
        html, filas = self.render(self.contexto())
        self.assertIn('Clasificación por definir', html)
        self.assertIn('value="001"', html)
        self.assertNotIn('value="001" selected', html)
        self.assertNotIn('value="PAC" selected', html)
        self.assertNotIn('value="NOPAC" selected', html)
        self.assertIn('data-pac-total', html)
        self.assertEqual(html.count('id="pac-fuentes-referencia"'), 1)
        fuente = next(c for c in filas[0]['controles'] if c['name'] == 'compras__fuente_pac')
        self.assertEqual(fuente['type'], 'text')
        self.assertEqual(fuente['list'], 'pac-fuentes-referencia')
        self.assertEqual(fuente['value'], '')
        self.assertEqual(fuente['placeholder'], 'Código o denominación confirmado')
        self.assertIn('los datos desconocidos pueden quedar pendientes', html)

    def test_sin_filas_conserva_una_plantilla_vacia_y_la_orientacion_para_empezar(self):
        contexto = self.contexto()
        contexto['dato']['filas_pac'] = []
        html, filas = self.render(contexto)
        self.assertEqual(len(filas), 1)
        self.assertTrue(filas[0]['plantilla'])
        self.assertIn('data-pac-vacio>', html)
        self.assertIn('Añadir necesidad', html)

    def test_el_estado_por_definir_no_crea_opciones_duplicadas_al_clonar(self):
        contexto = self.contexto()
        contexto['dato']['grupos_pac'][1]['campos'][3]['opciones'] = (
            ('por_definir', 'Por definir'), ('pac', 'PAC'), ('no_pac', 'NO PAC'))
        contexto['dato']['filas_pac'][0]['valor']['clasificacion_pac'] = 'por_definir'
        html, _filas = self.render(contexto)
        self.assertNotIn('value="por_definir"', html)
        self.assertIn('value="" selected>Clasificación por definir', html)

    def test_datos_y_sustento_estan_visibles_en_apartados_sin_desplegables(self):
        html, filas = self.render(self.contexto())
        for titulo in ('Área', 'Motivo', 'Nombre del bien o servicio', 'Cantidad', 'Valor unitario (USD)',
                       'Total (USD)', 'Mes de compra', 'Semestre'):
            self.assertIn(f'<span>{titulo}</span>', html)
        self.assertIn('pac-editor__desplazamiento', html)
        self.assertIn('CPC y datos administrativos', html)
        self.assertNotIn('<details', html)
        for fila in filas:
            self.assertEqual([s['aria-label'] for s in fila['secciones']], [
                'Bien solicitado y programación', 'Contraste con lo existente',
                'Especificaciones y sustento', 'CPC y datos administrativos'])
            self.assertTrue(all('hidden' not in s for s in fila['secciones']))
        controles = {c['name']: c for c in filas[0]['controles']}
        self.assertIn('compras__mes_compra', controles)
        self.assertNotIn('compras__semestre', controles)
        self.assertEqual(controles['compras__equipos_referencia']['type'], 'hidden')
        self.assertEqual(json.loads(controles['compras__equipos_referencia']['value']), ['eq-1'])
        self.assertIn('value="eq-1" selected', html)

    def test_pestanas_conservan_una_sola_fila_por_compra_y_todos_sus_campos(self):
        contexto = self.contexto()
        contenido = preparar_pac(dict(compras=[dict(item='Licencia CAD', clase_bien='software',
            area_id='unidad', tipo_necesidad='ampliacion', cantidad='2', costo_unitario='20',
            mes_compra='7', justificacion='Contrastar licencias existentes y demanda.', equipos_referencia=[])]))
        contexto['dato'] = datos_editor_pac(contenido)
        html, filas = self.render(contexto)
        parser = FilasPAC()
        parser.feed(html)
        self.assertEqual(len(filas), 2)  # Una compra y una plantilla; el resumen no es otra captura.
        self.assertEqual({p['data-pac-tab-clase'] for p in parser.pestanas},
                         {'', 'equipos', 'software', 'materiales', 'insumos', 'servicios', 'por_clasificar'})
        self.assertEqual(len({p['id'] for p in parser.pestanas}), len(parser.pestanas))
        self.assertEqual(len(parser.paneles), 1)
        panel = parser.paneles[0]
        self.assertTrue(all(p['type'] == 'button' and p['aria-controls'] == panel['id']
                            for p in parser.pestanas))
        self.assertEqual(sum(p['aria-selected'] == 'true' for p in parser.pestanas), 1)
        self.assertEqual(next(p['id'] for p in parser.pestanas if p['aria-selected'] == 'true'),
                         panel['aria-labelledby'])
        self.assertNotIn('<details', html)
        for fila in filas:
            nombres = [c['name'] for c in fila['controles']]
            self.assertEqual(len(nombres), len(set(nombres)))
            self.assertTrue(all('disabled' not in c for c in fila['controles']))
            self.assertTrue({'compras__clase_bien', 'compras__especificaciones', 'compras__unidad_medida',
                'compras__justificacion', 'compras__cpc', 'compras__partida', 'compras__fuente_pac',
                'compras__grupo_fases', 'compras__resultado_fase'} <= set(nombres))
            self.assertEqual(len(fila['secciones']), 5)
            self.assertTrue(all('hidden' not in s for s in fila['secciones']))
        self.assertEqual([c['name'] for c in filas[0]['controles']],
                         [c['name'] for c in filas[1]['controles']])

    def test_un_enviado_anterior_muestra_solo_sus_datos_conservados_sin_campos_nuevos(self):
        contexto = self.contexto()
        contexto['dato']['version_pac'] = 1
        contexto['documento'].estado = 'validado'
        fila = contexto['dato']['filas_pac'][0]['valor']
        for clave in ('area_id', 'tipo_necesidad', 'mes_compra', 'equipos_referencia'):
            fila.pop(clave, None)
        fila.update(prioridad='alta', fuente='institucional', trimestre='2')
        html, filas = self.render(contexto)
        self.assertIn('data-pac-legado', html)
        self.assertNotIn('data-pac-editor', html)
        self.assertEqual(len(filas), 1)
        self.assertFalse(filas[0]['plantilla'])
        self.assertEqual([(c['name'], c.get('type'), c.get('value')) for c in filas[0]['controles']],
                         [('compras__id_necesidad', 'hidden', 'identificador-original')])
        self.assertNotIn('Mes de compra', html)
        self.assertNotIn('data-pac-semestre', html)
        self.assertNotIn('Por completar', html)
        self.assertIn('Pieza &lt;especial&gt;', html)
        self.assertIn('Reponer el equipo que presenta una falla documentada.', html)
        self.assertIn('001234567', html)
        self.assertIn('Fuente interna registrada', html)
        self.assertIn('Trimestre previsto', html)

    def test_el_centro_de_costo_se_captura_una_sola_vez_fuera_de_las_necesidades(self):
        html, filas = self.render(self.contexto())
        self.assertEqual(html.count('name="centro_costo"'), 1)
        self.assertIn('value="Dirección académica"', html)
        self.assertTrue(all(not any(c['name'] == 'centro_costo' for c in f['controles']) for f in filas))
