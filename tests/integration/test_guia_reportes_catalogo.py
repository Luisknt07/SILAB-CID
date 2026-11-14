"""La orientación refleja el catálogo, la unidad y sus circuitos reales."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.expediente import contexto_del_expediente, cortes_del_anio
from apps.documentos.presentation.guia_reportes import REPORTES
from apps.gestion_unidades.presentation.gestion_reportes import categorias_para
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes


class GuiaReportesCatalogoTests(BaseAlcanceReportes):
    def contexto(self, tipo='laboratorios', usuario=None, corte='B'):
        return contexto_del_expediente(self.unidades[tipo], 2026, corte, cortes_del_anio(2026),
            date(2026, 10, 17), usuario=usuario or self.usuarios[tipo])

    @staticmethod
    def items(contexto):
        return [item for grupo in contexto['guia_reportes']['grupos'] for item in grupo['items']]

    def test_todos_los_reportes_ofrecidos_tienen_proposito_y_acceso_para_los_cuatro_tipos(self):
        propias = {'laboratorios': 'planificaciones', 'plantas_piloto': 'control-calidad',
                   'centro_experimental': 'ensayos', 'observatorios': 'datos-observatorio'}
        for tipo, unidad in self.unidades.items():
            with self.subTest(tipo=tipo):
                contexto = self.contexto(tipo)
                grupos = contexto['guia_reportes']['grupos']
                self.assertEqual([g['clave'] for g in grupos], ['base', 'apertura', 'registros', 'cierre'])
                categorias = dict(categorias_para(unidad))
                self.assertTrue(set(categorias) <= set(REPORTES))
                consultables = {}
                for item in self.items(contexto):
                    self.assertTrue(item['proposito'])
                    self.assertTrue(item['frecuencia'])
                    self.assertTrue(item['seguimiento'])
                    for accion in item['acciones']:
                        if accion['url'].startswith('#'):
                            continue
                        ruta = urlsplit(accion['url'])
                        resolve(ruta.path)
                        categoria = parse_qs(ruta.query).get('categoria_reporte', [''])[0]
                        if categoria:
                            consultables[categoria] = item
                            self.assertEqual(parse_qs(ruta.query)['desde'], [contexto['rango_periodo'][0].isoformat()])
                self.assertEqual(set(consultables), set(categorias))
                self.assertIn(propias[tipo], consultables)
                self.assertIn('retiros', consultables)
                self.assertIn('mejora', consultables)
                if tipo == 'observatorios':
                    self.assertTrue({'planificaciones', 'ejecuciones', 'seguridad', 'desechos'}.isdisjoint(consultables))

    def test_abrir_la_guia_no_crea_registros_aprobaciones_ni_archivos(self):
        cantidad = DocumentoExpediente.objects.count()
        with CaptureQueriesContext(connection) as consultas:
            contexto = self.contexto()
        escrituras = [q['sql'] for q in consultas if q['sql'].lstrip().split(' ', 1)[0].upper() in
                      ('INSERT', 'UPDATE', 'DELETE')]
        self.assertEqual(escrituras, [])
        self.assertEqual(DocumentoExpediente.objects.count(), cantidad)
        self.assertEqual(contexto['progreso_general']['porcentaje'], 0)

    def test_documentos_unicos_anuales_y_semestrales_explican_su_funcion_sin_otra_obligacion(self):
        items = {item['codigo']: item for item in self.items(self.contexto())}
        resolucion = items['RESOLUCION-CREACION']
        self.assertIn('Una vez', resolucion['frecuencia'])
        self.assertIn('no se califica', resolucion['validacion'])
        self.assertEqual(resolucion['prioridad'], 'Documento principal')
        self.assertIn('próximo año', items['PLAN-COMPRAS-ANUAL']['proposito'])
        self.assertIn('no autoriza gasto', items['PLAN-COMPRAS-ANUAL']['validacion'])
        self.assertIn('no acredita actividades ejecutadas', items['PLANIFICACION']['validacion'])
        self.assertIn('resultados parciales', items['INFORME-SEMESTRAL']['validacion'])
        self.assertEqual(items['retiros']['prioridad'], 'Consulta de seguimiento')
        self.assertIn('no crea una entrega', items['retiros']['frecuencia'])
        self.assertEqual(items['retiros']['estado'], '')

    def test_nombres_personalizados_y_evidencias_propias_se_conservan(self):
        exigido = DocumentoExigido.objects.get(codigo='PRACTICAS-FT02')
        exigido.nombre = 'Programación institucional de fabricación digital'
        exigido.save(update_fields=['nombre'])
        propia = DocumentoExigido.objects.create(codigo='RESPALDO-PROPIO', nombre='Registro específico de equipos',
            periodicidad='semestral', origen='unidad', anexo_de=DocumentoExigido.objects.get(codigo='INFORME-SEMESTRAL'))
        DocumentoExpediente.objects.create(unidad=self.unidades['laboratorios'], exigido=propia, anio=2026, corte='B')
        items = self.items(self.contexto())
        self.assertEqual(next(i for i in items if i['codigo'] == exigido.codigo)['nombre'], exigido.nombre)
        self.assertEqual(next(i for i in items if i['codigo'] == propia.codigo)['nombre'], propia.nombre)

    def test_sin_permiso_operativo_no_se_ofrecen_editores_ni_registros(self):
        contexto = self.contexto(usuario=self.usuarios['observatorios'])
        acciones = [a for i in self.items(contexto) for a in i['acciones']]
        self.assertFalse(any(a['tipo'] in ('editor', 'registro') for a in acciones))
        self.assertTrue(any(a['tipo'] == 'entrega' for a in acciones))

    def test_origenes_respetan_las_vistas_y_los_documentos_enviados_no_ofrecen_edicion(self):
        documento = self.documentos['laboratorios']
        DocumentoExpediente.objects.filter(pk=documento.pk).update(estado='validado')
        items = self.items(self.contexto())
        plan = next(i for i in items if i['codigo'] == 'PLANIFICACION')
        self.assertFalse(any(a['tipo'] == 'editor' for a in plan['acciones']))
        cursos = next(i for i in items if i['codigo'] == 'cursos')
        origen = next(a for a in cursos['acciones'] if a['tipo'] == 'registro')
        self.assertEqual(parse_qs(urlsplit(origen['url']).query), {'view': ['cursos']})
        observatorio = self.items(self.contexto('observatorios'))
        for codigo, vista in (('OBS-DATOS', 'obs_indicadores'), ('OBS-BOLETINES', 'obs_publicaciones')):
            item = next(i for i in observatorio if i['codigo'] == codigo)
            origen = next(a for a in item['acciones'] if a['tipo'] == 'registro')
            self.assertEqual(parse_qs(urlsplit(origen['url']).query)['view'], [vista])

    def test_categorias_y_consultas_no_ofrecen_produccion_inhabilitada(self):
        for tipo in ('laboratorios', 'observatorios', 'centro_experimental'):
            with self.subTest(tipo=tipo):
                contexto = self.contexto(tipo)
                self.assertTrue({'produccion', 'procesos', 'calidad'}.isdisjoint(dict(categorias_para(self.unidades[tipo]))))
                self.assertTrue({'produccion', 'procesos', 'calidad'}.isdisjoint(c['codigo'] for c in contexto['consultas']))

    def test_consulta_anual_conserva_ambos_anexos_sin_apropiarse_del_estado_de_un_semestre(self):
        contexto = self.contexto(corte='')
        item = next(i for i in self.items(contexto) if i['codigo'] == 'PRACTICAS-FT02')
        entregas = [a for a in item['acciones'] if a['tipo'] == 'entrega']
        self.assertEqual({parse_qs(urlsplit(a['url']).query)['corte'][0] for a in entregas}, {'A', 'B'})
        self.assertEqual(item['estado'], '')

    def test_la_pantalla_publica_los_cuatro_bloques_y_conserva_la_entrega(self):
        self.client.force_login(self.usuarios['laboratorios'])
        for nombre in ('gestion_expediente_unidad', 'gestion_unidad'):
            with self.subTest(vista=nombre):
                pagina = self.client.get(reverse(nombre, args=[self.unidades['laboratorios'].slug]),
                                         {'anio': 2026, 'corte': 'B', 'view': 'reportes'})
                self.assertEqual(pagina.status_code, 200)
                for titulo in ('Qué reportar y dónde hacerlo', 'Vigencia y plan anual', 'Evidencias del período',
                               'Cierre y seguimiento', 'data-reporte-informacion-contenido', 'entregas-documentos'):
                    self.assertContains(pagina, titulo)
