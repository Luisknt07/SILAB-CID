"""Las entregas, sus indicadores y la mejora mantienen papeles distintos."""
from datetime import date
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')
RAIZ = 'portal/pages/unidades/gestion/includes/'


class LecturaTabla(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entregas = 0
        self.exigencias = []

    def handle_starttag(self, tag, attrs):
        valores = dict(attrs)
        if tag == 'tr' and 'data-entrega' in valores:
            self.entregas += 1
        if tag == 'span' and 'reporte-exigencia' in valores.get('class', '').split():
            self.exigencias.append(valores)


class RevisionInterfazDocumentalTests(SimpleTestCase):
    def contexto(self, tipo='laboratorios', **extra):
        unidad = SimpleNamespace(pk=11, slug='revision-' + tipo, nombre='Unidad QA',
            dependencia=tipo, codigo_base=tipo, administrador=None, adscrita_a=None)

        def documento(numero, codigo, permanente=False):
            return SimpleNamespace(pk=numero, unidad=unidad, unidad_id=11,
                exigido=SimpleNamespace(codigo=codigo, redactable=False),
                nombre_documental=codigo, anio=2026, corte='' if permanente else 'B',
                etiqueta_corte='Documento permanente' if permanente else '2026-B',
                estado='pendiente', recurso_id=None, aprobacion_en_linea_disponible=True,
                resumen_interfaz=dict(permanente=permanente, grupo='pendientes'))

        plan, informe = documento(4, 'PLANIFICACION'), documento(5, 'INFORME-SEMESTRAL')
        contexto = dict(unidad=unidad, anio=2026, anios=[2026], corte='B',
            rango_periodo=(date(2026, 7, 1), date(2026, 12, 31)),
            etiqueta_periodo='Período 2026-B', total_entregas=5,
            de_la_unidad=[documento(1, 'RESOLUCION-CREACION', True),
                          documento(2, 'PROTOCOLO-BIOSEGURIDAD', True)],
            del_anio=[documento(3, 'PLAN-COMPRAS-ANUAL')],
            periodos=[dict(corte='B', etiqueta='2026-B', entregas=[
                dict(documento=plan, nombre=plan.nombre_documental, anexos=[]),
                dict(documento=informe, nombre=informe.nombre_documental, anexos=[])])],
            cumplimiento=dict(filas=[1], requiere_mejora=False, informe=None,
                periodo_iniciado=True, minimo=70, actividad_metricas=[('Atenciones', 2)]),
            progreso_general=dict(resultado_porcentaje=None))
        contexto.update(extra)
        return contexto

    def test_las_filas_principales_concuerdan_con_el_conteo_sin_sumar_mejora(self):
        recurso = SimpleNamespace(pk=417, nombre='Antecedente de mejora', version=1)
        for tipo in TIPOS:
            contexto = self.contexto(tipo)
            contexto['cumplimiento'].update(informe=recurso)
            html = render_to_string(RAIZ + 'expediente_cuerpo.html', contexto)
            tabla = html.split('<table class="entregas__tabla entregas__tabla--simple">', 1)[1].split('</table>', 1)[0]
            lectura = LecturaTabla()
            lectura.feed(tabla)
            with self.subTest(tipo=tipo):
                self.assertEqual(lectura.entregas, 5)
                self.assertIn('5 documentos obligatorios', tabla)
                self.assertNotIn('data-documento-mejora', tabla)
                self.assertIn('Planificación y respaldo de actividades', tabla)
                self.assertNotIn('respaldo de prácticas', tabla)
                self.assertIn('data-documento-mejora', html.split('</table>', 1)[1])

    def test_sin_causa_no_se_presenta_un_informe_adicional(self):
        html = render_to_string(RAIZ + 'mejora_seguimiento.html', self.contexto())
        self.assertIn('Resultado y mejora continua', html)
        self.assertNotIn('data-documento-mejora', html)
        self.assertNotIn('value="mejora"', html)
        self.assertNotIn('value="remitir_mejora"', html)

    def test_el_antecedente_sigue_visible_sin_filas_actuales_ni_nueva_exigencia(self):
        contexto = self.contexto(cumplimiento=dict(filas=[], requiere_mejora=False), mejora_antecedente=True)
        recurso = SimpleNamespace(pk=417, nombre='Antecedente de mejora', version=1)
        contexto['tramite_mejora'] = SimpleNamespace(recurso=recurso, recurso_id=417,
            estado='Archivado, pendiente de remisión', remitido_en=None, recibido_en=None, decidido_en=None)
        html = render_to_string(RAIZ + 'mejora_seguimiento.html', contexto)
        self.assertIn('data-documento-mejora', html)
        self.assertIn('data-pdf-titulo="Antecedente de mejora"', html)
        self.assertIn('Antecedente conservado', html)
        self.assertNotIn('value="mejora"', html)
        self.assertNotIn('value="remitir_mejora"', html)

    def test_mejora_requerida_conserva_resultado_cero_y_su_accion(self):
        contexto = self.contexto(progreso_general=dict(resultado_porcentaje=0))
        contexto['cumplimiento'].update(requiere_mejora=True, bajo_minimo=True, sin_uso_al_cierre=True)
        html = render_to_string(RAIZ + 'mejora_seguimiento.html', contexto)
        self.assertIn('0,00 %', html)
        self.assertIn('value="mejora"', html)
        self.assertIn('no es una entrega periódica adicional', html)

    def test_actividad_y_falta_de_medicion_se_presentan_sin_presumir_inactividad(self):
        contexto = self.contexto('observatorios')
        contexto['cumplimiento'].update(sin_uso=True, actividad_perfil_pendiente=True,
            actividad_metricas=[('Indicadores actualizados', 3), ('Publicaciones', 2)])
        html = render_to_string(RAIZ + 'mejora_seguimiento.html', contexto)
        self.assertIn('Indicadores actualizados', html)
        self.assertIn('Publicaciones', html)
        self.assertNotIn('<dt>Prácticas</dt>', html)
        self.assertIn('no se presume inactividad', html)
        self.assertNotIn('Sin actividad acreditada al cierre.', html)

    def test_el_listado_de_direccion_identifica_seguimiento_por_unidad(self):
        contexto = self.contexto(seguimiento_en_admin=True)
        html = render_to_string(RAIZ + 'mejora_seguimiento.html', contexto)
        self.assertIn('id="resultado-seguimiento-11"', html)
        self.assertNotIn('id="resultado-seguimiento"', html)

    def test_exigencia_compartida_se_muestra_una_vez_y_ambas_metas_permanecen(self):
        indicadores = [dict(codigo=codigo, indicador=nombre, exigencia='Sin definir',
            estado='Sin definir en planificación', porcentaje=None, registrado=None)
            for codigo, nombre in (('TRANSFERENCIA', 'Transferencias documentadas'),
                                   ('SERVICIOS', 'Servicios entregados'))]
        contexto = self.contexto()
        contexto.update(indicadores=indicadores, modo_admin=True, recurso=None,
            nombre='Informe de transferencia', numero_item=1,
            anexo=SimpleNamespace(pk=7))
        html = render_to_string(RAIZ + 'anexo_cierre_fila.html', contexto)
        lectura = LecturaTabla()
        lectura.feed(html)
        self.assertEqual(len(lectura.exigencias), 1)
        self.assertIn('<td rowspan="2"><span class="reporte-exigencia', html)
        self.assertIn('data-meta-codigo="TRANSFERENCIA"', html)
        self.assertIn('data-meta-codigo="SERVICIOS"', html)
        self.assertIn('Transferencias documentadas', html)
        self.assertIn('Servicios entregados', html)
        indicadores[1]['exigencia'] = 'Obligatorio del período'
        distinto = LecturaTabla()
        distinto.feed(render_to_string(RAIZ + 'anexo_cierre_fila.html', contexto))
        self.assertEqual(len(distinto.exigencias), 2)
