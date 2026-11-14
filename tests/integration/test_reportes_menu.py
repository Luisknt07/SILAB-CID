"""El menú ordena herramientas autorizadas sin ampliar su alcance ni repetirlas."""
from collections import Counter
from copy import deepcopy
from html.parser import HTMLParser

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse


class LecturaBloquesReportes(HTMLParser):
    """Atribuye los accesos a su contenedor real, también con marcado anidado."""
    VACIOS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__()
        self.pila = []
        self.paneles = []
        self.enlaces_fuera = []
        self.tabs = []
        self.navegaciones = []
        self.leyendas_fuera = []
        self.columnas = []
        self.elementos = []

    def handle_starttag(self, tag, attrs):
        datos = dict(attrs)
        elemento = {'tag': tag, 'attrs': datos, 'contenido': [],
                    'padre': self.pila[-1][3] if self.pila else None}
        self.elementos.append(elemento)
        if elemento['padre'] is not None:
            elemento['padre']['contenido'].append(elemento)
        panel = self.pila[-1][1] if self.pila else None
        dentro_columnas = self.pila[-1][2] if self.pila else False
        if 'data-reportes-columnas' in datos:
            dentro_columnas = True
            self.columnas.append(datos)
        if 'data-reportes-seccion' in datos:
            panel = {'attrs': datos, 'enlaces': [], 'categorias': [], 'leyendas': [],
                     'dentro_columnas': dentro_columnas}
            self.paneles.append(panel)
        if tag == 'a':
            (panel['enlaces'] if panel is not None else self.enlaces_fuera).append(datos)
        if 'data-reportes-categoria' in datos and panel is not None:
            panel['categorias'].append(datos['data-reportes-categoria'])
        if 'citt-reportes__leyenda' in datos.get('class', '').split():
            (panel['leyendas'] if panel is not None else self.leyendas_fuera).append(datos)
        if 'data-reportes-tabs' in datos:
            self.navegaciones.append(datos)
        if 'data-reportes-tab' in datos:
            self.tabs.append(datos)
        if tag not in self.VACIOS:
            self.pila.append((tag, panel, dentro_columnas, elemento))

    def handle_data(self, data):
        if self.pila:
            self.pila[-1][3]['contenido'].append(data)

    @classmethod
    def texto(cls, elemento):
        return ''.join(parte if isinstance(parte, str) else cls.texto(parte)
                       for parte in elemento['contenido'])

    @staticmethod
    def dentro(elemento, contenedor):
        padre = elemento['padre']
        while padre is not None:
            if padre is contenedor:
                return True
            padre = padre['padre']
        return False

    def handle_endtag(self, tag):
        for indice in range(len(self.pila) - 1, -1, -1):
            if self.pila[indice][0] == tag:
                del self.pila[indice:]
                break


class OrganizacionReportesTests(SimpleTestCase):
    def tarjetas(self, *, respaldo=False):
        """Las mismas entradas del sitio, después de su filtro de permisos."""
        from apps.core.admin.site import _DESPUES_DE_LOS_TIPOS

        reportes = next(c for c in _DESPUES_DE_LOS_TIPOS if c['slug'] == 'reportes')
        tarjetas = [
            dict(name='Alertas de uso de equipos', object_name='AlertaUsoEquipo',
                 admin_url=reverse('admin:recursos_alertausoequipo_changelist'),
                 descripcion='Alertas ya registradas.', perms={'view': True}, add_url=None),
            dict(name='Traspasos de equipos', object_name='TraspasoEquipo',
                 admin_url=reverse('admin:recursos_traspasoequipo_changelist'),
                 descripcion='Movimientos entre unidades.', perms={'view': True}, add_url=None),
        ]
        for enlace in reportes['enlaces']:
            if enlace.get('solo_sin_expediente') and not respaldo:
                continue
            if respaldo and enlace['ruta'] == 'admin:reportes-cumplimiento-expediente':
                continue
            tarjetas.append(dict(name=enlace['nombre'], object_name=enlace['ruta'].split(':')[-1],
                admin_url=reverse(enlace['ruta']), descripcion=enlace['descripcion'],
                perms={'view': True}, add_url=None))
        return tarjetas

    def organizar(self, tarjetas):
        from apps.core.admin.reportes_menu import organizar_reportes
        return organizar_reportes(tarjetas)

    def tarjetas_organizadas(self, menu):
        tarjetas = []
        for seccion in menu['secciones']:
            if seccion['principal']:
                tarjetas.append(seccion['principal'])
            tarjetas.extend(tarjeta for categoria in seccion['categorias']
                            for subcategoria in categoria['subcategorias']
                            for tarjeta in subcategoria['models'])
        return tarjetas

    def seccion(self, menu, codigo='unidades'):
        return next(seccion for seccion in menu['secciones'] if seccion['codigo'] == codigo)

    def test_cumplimiento_es_principal_sin_modificar_la_entrada(self):
        tarjetas = self.tarjetas()
        originales = deepcopy(tarjetas)
        menu = self.organizar(tarjetas)
        principal = self.seccion(menu)['principal']

        self.assertEqual(tarjetas, originales)
        self.assertEqual(principal['object_name'], 'reportes-cumplimiento-expediente')
        self.assertEqual(principal['name'], 'Cumplimiento del expediente por unidad')
        self.assertEqual(principal['admin_url'], reverse('admin:reportes-cumplimiento-expediente'))

    def test_cada_herramienta_autorizada_aparece_una_sola_vez(self):
        tarjetas = self.tarjetas()
        self.assertEqual(len(tarjetas), 15)
        ordenadas = self.tarjetas_organizadas(self.organizar(tarjetas))

        self.assertEqual(Counter(t['object_name'] for t in ordenadas),
                         Counter(t['object_name'] for t in tarjetas))
        self.assertEqual(len({t['admin_url'] for t in ordenadas}), len(tarjetas))
        self.assertEqual({t['object_name']: t['admin_url'] for t in ordenadas},
                         {t['object_name']: t['admin_url'] for t in tarjetas})

    def test_categorias_reunen_entregas_compras_uso_actividad_y_apoyo(self):
        menu = self.organizar(self.tarjetas())
        self.assertEqual([s['codigo'] for s in menu['secciones']], ['unidades', 'centros_id'])
        categorias = self.seccion(menu)['categorias']
        self.assertEqual([c['codigo'] for c in categorias],
                         ['evaluacion', 'compras_equipos', 'actividad', 'apoyo'])
        por_categoria = {c['codigo']: {t['object_name'] for sub in c['subcategorias']
                                     for t in sub['models']} for c in categorias}
        self.assertEqual(por_categoria, {
            'evaluacion': {'reportes-expediente-por-tipo', 'documentos_informemejora_changelist'},
            'compras_equipos': {'reportes-necesidades-decanato', 'equipamiento_institucional',
                               'recursos_unidadequipo_transparencia', 'AlertaUsoEquipo', 'TraspasoEquipo'},
            'actividad': {'reportes-institucional', 'gestion_unidades_reporteoperativounidad_changelist',
                          'reservas-estadisticas', 'reservas-reporte-uso',
                          'reservas-reporte-listado'},
            'apoyo': {'lector_equipos'},
        })
        for categoria in categorias:
            self.assertTrue(categoria['subcategorias'])
            self.assertTrue(categoria['nombre'])
            for subcategoria in categoria['subcategorias']:
                self.assertTrue(subcategoria['models'])
                self.assertTrue(subcategoria['nombre'])

    def test_filtrado_previo_no_inventa_principal_ni_herramientas_ajenas(self):
        autorizadas = [t for t in self.tarjetas() if t['object_name'].startswith('reservas-')]
        menu = self.organizar(autorizadas)

        self.assertEqual([s['codigo'] for s in menu['secciones']], ['unidades'])
        unidades = self.seccion(menu)
        self.assertIsNone(unidades['principal'])
        self.assertEqual([c['codigo'] for c in unidades['categorias']], ['actividad'])
        self.assertEqual(len(unidades['categorias'][0]['subcategorias']), 1)
        self.assertEqual({t['object_name'] for t in self.tarjetas_organizadas(menu)},
                         {t['object_name'] for t in autorizadas})

    def test_centros_tienen_su_principal_fuera_de_las_herramientas_de_unidades(self):
        tarjetas = self.tarjetas()
        originales = deepcopy(tarjetas)
        menu = self.organizar(tarjetas)
        centros = self.seccion(menu, 'centros_id')

        self.assertEqual(centros['nombre'], 'Centros de Investigación y Desarrollo')
        self.assertEqual(centros['principal']['object_name'], 'reportes_centros_id')
        self.assertEqual(centros['principal']['admin_url'], reverse('reportes_centros_id'))
        self.assertEqual(centros['principal']['tipo_menu']['codigo'], 'sistema')
        self.assertEqual(centros['categorias'], [])
        self.assertEqual(tarjetas, originales)
        accesos_unidades = self.tarjetas_organizadas({'secciones': [self.seccion(menu)]})
        self.assertNotIn('reportes_centros_id', [t['object_name'] for t in accesos_unidades])

    def test_acceso_solo_a_centros_no_inventa_seccion_de_unidades(self):
        autorizadas = [t for t in self.tarjetas() if t['object_name'] == 'reportes_centros_id']
        menu = self.organizar(autorizadas)

        self.assertEqual([s['codigo'] for s in menu['secciones']], ['centros_id'])
        self.assertEqual(self.seccion(menu, 'centros_id')['principal']['admin_url'], reverse('reportes_centros_id'))
        self.assertEqual(self.seccion(menu, 'centros_id')['categorias'], [])
        self.assertEqual({tipo['codigo'] for tipo in self.seccion(menu, 'centros_id')['tipos']}, {'sistema'})
        html = self.renderizar(autorizadas)
        enlaces, categorias = self.enlaces_y_categorias(html)
        self.assertEqual([e['href'] for e in enlaces], [reverse('reportes_centros_id')])
        self.assertEqual(categorias, [])
        self.assertNotIn('data-reportes-ambito="unidades"', html)
        self.assertNotIn('data-reportes-seccion="unidades"', html)
        self.assertNotIn('Evaluar unidades', html)

    def test_respaldo_sin_cumplimiento_conserva_destino_y_nombre_original(self):
        tarjetas = self.tarjetas(respaldo=True)
        originales = deepcopy(tarjetas)
        menu = self.organizar(tarjetas)
        principal = self.seccion(menu)['principal']

        self.assertEqual(tarjetas, originales)
        self.assertEqual(principal['object_name'], 'reportes-evidencias-por-tipo')
        self.assertEqual(principal['name'], 'Expedientes de las unidades')
        self.assertEqual(principal['admin_url'], reverse('admin:reportes-evidencias-por-tipo'))
        self.assertEqual(Counter(t['object_name'] for t in self.tarjetas_organizadas(menu)),
                         Counter(t['object_name'] for t in tarjetas))

    def test_herramienta_nueva_no_desaparece_por_falta_de_clasificacion(self):
        nueva = dict(name='Consulta futura', object_name='consulta_futura',
                     admin_url='/admin/consulta-futura/', descripcion='Otra consulta autorizada.',
                     perms={'view': True}, add_url=None)
        menu = self.organizar([nueva])

        self.assertEqual([s['codigo'] for s in menu['secciones']], ['otras'])
        self.assertIsNone(self.seccion(menu, 'otras')['principal'])
        self.assertEqual([c['codigo'] for c in self.seccion(menu, 'otras')['categorias']], ['otras'])
        self.assertEqual(self.tarjetas_organizadas(menu), [nueva])
        html = self.renderizar([nueva])
        self.assertIn('Tipo por definir', html)
        self.assertIn('data-reporte-tipo="sin_clasificar"', html)
        self.assertIn('href="/admin/consulta-futura/"', html)

    def test_sin_herramientas_no_hay_encabezados_vacios(self):
        menu = self.organizar([])
        self.assertEqual(menu['secciones'], [])

    def test_tipos_distinguen_documentos_consultas_gestion_y_evaluacion(self):
        tarjetas = self.tarjetas()
        originales = deepcopy(tarjetas)
        menu = self.organizar(tarjetas)
        por_clave = {t['object_name']: t for t in self.tarjetas_organizadas(menu)}
        principal = self.seccion(menu)['principal']

        self.assertEqual(tarjetas, originales)
        self.assertEqual(principal['tipo_menu']['codigo'], 'evaluacion')
        self.assertEqual(principal['tipo_menu']['nombre'], 'Panel de evaluación')
        documentos = {'reportes-necesidades-decanato', 'documentos_informemejora_changelist'}
        gestion = {'AlertaUsoEquipo', 'TraspasoEquipo', 'lector_equipos'}
        for clave, tarjeta in por_clave.items():
            with self.subTest(herramienta=clave):
                tipo = tarjeta['tipo_menu']
                esperado = ('evaluacion' if clave == 'reportes-cumplimiento-expediente' else
                            'documentos' if clave in documentos else
                            'gestion' if clave in gestion else 'sistema')
                self.assertEqual(tipo['codigo'], esperado)
                self.assertTrue(tipo['nombre'])
                self.assertTrue(tipo['descripcion'])
        # El resumen compara datos; no constituye otra entrega documental.
        self.assertEqual(por_clave['reportes-expediente-por-tipo']['tipo_menu']['codigo'], 'sistema')

    def test_leyenda_refleja_solo_los_tipos_autorizados_y_respaldo_documental(self):
        tarjetas = self.tarjetas()
        casos = [
            (tarjetas, {'unidades': {'documentos', 'sistema', 'gestion'}, 'centros_id': {'sistema'}}),
            ([t for t in tarjetas if t['object_name'].startswith('reservas-')], {'unidades': {'sistema'}}),
            ([t for t in tarjetas if t['object_name'] == 'reportes-cumplimiento-expediente'], {'unidades': set()}),
            ([], {}),
        ]
        for autorizadas, tipos_esperados in casos:
            with self.subTest(tarjetas=[t['object_name'] for t in autorizadas]):
                menu = self.organizar(autorizadas)
                self.assertEqual({s['codigo']: {t['codigo'] for t in s['tipos']}
                                  for s in menu['secciones']}, tipos_esperados)
                for seccion in menu['secciones']:
                    self.assertEqual(len(seccion['tipos']), len(tipos_esperados[seccion['codigo']]))
        respaldo = self.organizar(self.tarjetas(respaldo=True))
        self.assertEqual(self.seccion(respaldo)['principal']['tipo_menu']['codigo'], 'documentos')

    def test_marcado_identifica_cada_tipo_y_mantiene_los_destinos(self):
        class TarjetasMarcadas(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tipos = []

            def handle_starttag(self, tag, attrs):
                datos = dict(attrs)
                if tag == 'article' or 'data-reporte-principal' in datos:
                    self.tipos.append(datos.get('data-reporte-tipo'))

        for respaldo in (False, True):
            with self.subTest(respaldo=respaldo):
                tarjetas = self.tarjetas(respaldo=respaldo)
                menu = self.organizar(tarjetas)
                html = self.renderizar(tarjetas)
                lectura = TarjetasMarcadas()
                lectura.feed(html)
                self.assertEqual(Counter(lectura.tipos), Counter(
                    t['tipo_menu']['codigo'] for t in self.tarjetas_organizadas(menu)))
                for tarjeta in self.tarjetas_organizadas(menu):
                    self.assertIn(tarjeta['tipo_menu']['nombre'], html)
                enlaces, _ = self.enlaces_y_categorias(html)
                self.assertEqual(Counter(e['href'] for e in enlaces),
                                 Counter(t['admin_url'] for t in tarjetas))

    def renderizar(self, tarjetas):
        return render_to_string('admin/includes/reportes_menu.html', {
            'app': {'slug': 'reportes'},
            'menu_reportes': self.organizar(tarjetas),
        })

    def enlaces_y_categorias(self, html):
        class Navegacion(HTMLParser):
            def __init__(self):
                super().__init__()
                self.enlaces = []
                self.categorias = []

            def handle_starttag(self, tag, attrs):
                datos = dict(attrs)
                if tag == 'a':
                    self.enlaces.append(datos)
                if 'data-reportes-categoria' in datos:
                    self.categorias.append(datos['data-reportes-categoria'])

        lectura = Navegacion()
        lectura.feed(html)
        return lectura.enlaces, lectura.categorias

    def test_marcado_destaca_cumplimiento_y_no_repite_ningun_destino(self):
        tarjetas = self.tarjetas()
        html = self.renderizar(tarjetas)
        enlaces, categorias = self.enlaces_y_categorias(html)
        principales = [e for e in enlaces if 'data-reporte-principal' in e]

        self.assertEqual(len(principales), 2)
        self.assertEqual(enlaces[0], principales[0])
        self.assertEqual(principales[0]['href'], reverse('admin:reportes-cumplimiento-expediente'))
        self.assertEqual(principales[1]['href'], reverse('reportes_centros_id'))
        self.assertIn('Cumplimiento del expediente por unidad', html)
        self.assertIn('Evaluar unidades', html)
        self.assertIn('Consultar reportes', html)
        self.assertEqual(Counter(e['href'] for e in enlaces),
                         Counter(t['admin_url'] for t in tarjetas))
        self.assertEqual(categorias, ['evaluacion', 'compras_equipos', 'actividad', 'apoyo'])

    def test_marcado_limitado_a_reservas_respeta_las_tarjetas_recibidas(self):
        autorizadas = [t for t in self.tarjetas() if t['object_name'].startswith('reservas-')]
        html = self.renderizar(autorizadas)
        enlaces, categorias = self.enlaces_y_categorias(html)

        self.assertEqual(categorias, ['actividad'])
        self.assertFalse(any('data-reporte-principal' in e for e in enlaces))
        self.assertNotIn('Evaluar unidades', html)
        self.assertNotIn('data-reportes-ambito="centros_id"', html)
        self.assertNotIn('data-reportes-seccion="centros_id"', html)
        self.assertEqual(Counter(e['href'] for e in enlaces),
                         Counter(t['admin_url'] for t in autorizadas))

    def test_cada_bloque_contiene_su_principal_y_todas_sus_herramientas(self):
        tarjetas = self.tarjetas()
        menu = self.organizar(tarjetas)
        lectura = LecturaBloquesReportes()
        lectura.feed(self.renderizar(tarjetas))
        self.assertEqual([p['attrs']['data-reportes-seccion'] for p in lectura.paneles],
                         ['unidades', 'centros_id'])
        self.assertEqual(lectura.enlaces_fuera, [])
        self.assertEqual(lectura.leyendas_fuera, [])
        for panel in lectura.paneles:
            codigo = panel['attrs']['data-reportes-seccion']
            seccion = self.seccion(menu, codigo)
            with self.subTest(ambito=codigo):
                self.assertEqual(panel['attrs']['data-reportes-ambito'], codigo)
                self.assertEqual(panel['attrs']['id'], 'reportes-panel-' + codigo)
                # Las dos categorías se muestran completas desde el HTML.
                self.assertNotIn('hidden', panel['attrs'])
                self.assertEqual(panel['enlaces'][0]['href'], seccion['principal']['admin_url'])
                self.assertEqual([e['href'] for e in panel['enlaces'] if 'data-reporte-principal' in e],
                                 [seccion['principal']['admin_url']])
                esperadas = self.tarjetas_organizadas({'secciones': [seccion]})
                self.assertEqual(Counter(e['href'] for e in panel['enlaces']),
                                 Counter(t['admin_url'] for t in esperadas))
                self.assertEqual(panel['categorias'], [c['codigo'] for c in seccion['categorias']])
                self.assertEqual(len(panel['leyendas']), 1 if seccion['tipos'] else 0)

    def test_columnas_muestran_ambos_bloques_sin_tabs_ni_script_de_seleccion(self):
        html = self.renderizar(self.tarjetas())
        lectura = LecturaBloquesReportes()
        lectura.feed(html)
        self.assertEqual(len(lectura.columnas), 1)
        self.assertEqual(lectura.navegaciones, [])
        self.assertEqual(lectura.tabs, [])
        self.assertNotIn('reportes_menu.js', html)
        self.assertEqual([p['attrs']['data-reportes-seccion'] for p in lectura.paneles],
                         ['unidades', 'centros_id'])
        self.assertEqual(len({p['attrs']['id'] for p in lectura.paneles}), 2)
        for panel in lectura.paneles:
            self.assertTrue(panel['dentro_columnas'])
            self.assertNotIn('hidden', panel['attrs'])

    def test_una_sola_categoria_autorizada_muestra_su_bloque_completo(self):
        for prefijo in ('reservas-', 'reportes_centros_id'):
            with self.subTest(acceso=prefijo):
                autorizadas = [t for t in self.tarjetas() if t['object_name'].startswith(prefijo)]
                lectura = LecturaBloquesReportes()
                lectura.feed(self.renderizar(autorizadas))
                self.assertEqual(lectura.navegaciones, [])
                self.assertEqual(lectura.tabs, [])
                self.assertEqual(len(lectura.columnas), 1)
                self.assertEqual(len(lectura.paneles), 1)
                self.assertTrue(lectura.paneles[0]['dentro_columnas'])
                self.assertNotIn('hidden', lectura.paneles[0]['attrs'])
                self.assertEqual(lectura.enlaces_fuera, [])

    def test_categorias_y_ayuda_tienen_summary_nativo_y_apertura_inicial_clara(self):
        lectura = LecturaBloquesReportes()
        lectura.feed(self.renderizar(self.tarjetas()))
        categorias = [e for e in lectura.elementos if 'data-reportes-categoria' in e['attrs']]
        self.assertEqual(len(categorias), 4)
        for categoria in categorias:
            codigo = categoria['attrs']['data-reportes-categoria']
            with self.subTest(categoria=codigo):
                self.assertEqual(categoria['tag'], 'details')
                self.assertEqual('open' in categoria['attrs'], codigo == 'evaluacion')
                hijos = [e for e in categoria['contenido'] if isinstance(e, dict)]
                self.assertEqual(hijos[0]['tag'], 'summary')
                self.assertEqual(len([h for h in hijos if h['tag'] == 'summary']), 1)
                resumen = hijos[0]
                titulo = next(e for e in lectura.elementos if e['tag'] == 'h3'
                              and lectura.dentro(e, resumen))
                self.assertEqual(titulo['attrs']['id'], 'reportes-' + codigo)
                self.assertTrue(lectura.texto(titulo).strip())
                cantidad = [e for e in lectura.elementos
                            if 'citt-reportes__cantidad' in e['attrs'].get('class', '').split()
                            and lectura.dentro(e, resumen)]
                self.assertEqual(len(cantidad), 1)
                filas = [e for e in lectura.elementos if e['tag'] == 'article'
                         and lectura.dentro(e, categoria)]
                self.assertRegex(lectura.texto(cantidad[0]).strip(), rf'^{len(filas)}\b')
        ayudas = [e for e in lectura.elementos
                  if 'citt-reportes__leyenda' in e['attrs'].get('class', '').split()]
        self.assertEqual(len(ayudas), 2)
        for ayuda in ayudas:
            self.assertEqual(ayuda['tag'], 'aside')
            detalles = [e for e in lectura.elementos if e['tag'] == 'details' and lectura.dentro(e, ayuda)]
            self.assertEqual(len(detalles), 1)
            self.assertNotIn('open', detalles[0]['attrs'])
            resumen = next(e for e in lectura.elementos
                           if e['tag'] == 'summary' and e['padre'] is detalles[0])
            self.assertIn('Cómo se identifican los accesos', lectura.texto(resumen))

    def test_cada_fila_conserva_su_propio_titulo_enlace_y_badge(self):
        tarjetas = self.tarjetas()
        menu = self.organizar(tarjetas)
        principales = {s['principal']['object_name'] for s in menu['secciones'] if s['principal']}
        esperadas = {t['admin_url']: t for t in self.tarjetas_organizadas(menu)
                     if t['object_name'] not in principales}
        lectura = LecturaBloquesReportes()
        lectura.feed(self.renderizar(tarjetas))
        filas = [e for e in lectura.elementos if e['tag'] == 'article' and 'data-reporte-tipo' in e['attrs']]
        self.assertEqual(len(filas), len(esperadas))
        for fila in filas:
            enlaces = [e for e in lectura.elementos if e['tag'] == 'a' and lectura.dentro(e, fila)]
            self.assertEqual(len(enlaces), 1)
            tarjeta = esperadas[enlaces[0]['attrs']['href']]
            with self.subTest(fila=tarjeta['object_name']):
                self.assertEqual(lectura.texto(enlaces[0]).strip(), tarjeta['name'])
                self.assertEqual(fila['attrs']['data-reporte-tipo'], tarjeta['tipo_menu']['codigo'])
                badges = [e for e in lectura.elementos
                          if 'citt-reportes__tipo' in e['attrs'].get('class', '').split()
                          and lectura.dentro(e, fila)]
                self.assertEqual(len(badges), 1)
                self.assertEqual(lectura.texto(badges[0]).strip(), tarjeta['tipo_menu']['nombre'])
                self.assertNotIn('hidden', badges[0]['attrs'])

    def test_marcado_de_respaldo_abre_expedientes_sin_ofrecer_evaluacion(self):
        html = self.renderizar(self.tarjetas(respaldo=True))
        enlaces, _ = self.enlaces_y_categorias(html)
        principal = next(e for e in enlaces if 'data-reporte-principal' in e)

        self.assertEqual(principal['href'], reverse('admin:reportes-evidencias-por-tipo'))
        self.assertIn('Expedientes de las unidades', html)
        self.assertIn('Abrir expedientes', html)
        self.assertNotIn('Evaluar unidades', html)
