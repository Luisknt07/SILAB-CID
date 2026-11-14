"""La exportación de Dirección conserva la bandeja y los denominadores globales."""
from contextlib import ExitStack
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from pypdf import PdfReader

from apps.documentos.presentation.cumplimiento import pdf_de_cumplimiento
from apps.gestion_unidades.admin.reportes import ReporteOperativoUnidadAdmin


class CumplimientoPdfBandejaTests(SimpleTestCase):
    def totales(self):
        return dict(unidades=9, cumplen_minimo=2, evaluadas=3, minimo=70,
            completo=40, tardias=1, incumplen=4)

    def test_endpoint_filtra_antes_de_exportar_sin_recalcular_totales(self):
        request = RequestFactory().get('/admin/cumplimiento/', dict(anio=2026, corte='B',
            automatizacion='unidad', formato='pdf', pagina=2))
        request.user = SimpleNamespace(has_perm=lambda permiso: True)
        todas, seleccionadas, totales = [dict(id=1), dict(id=2)], [dict(id=1)], self.totales()
        with ExitStack() as pila:
            prefijo = 'apps.documentos.presentation.cumplimiento.'
            pila.enter_context(patch(prefijo + 'tipos_auditados', return_value=[]))
            pila.enter_context(patch(prefijo + 'unidades_auditadas', return_value=[]))
            pila.enter_context(patch(prefijo + 'cumplimiento_por_periodo', return_value=(todas, totales)))
            filtrar = pila.enter_context(patch(prefijo + 'filtrar_bandeja_automatizacion', return_value=seleccionadas))
            render = pila.enter_context(patch(prefijo + 'pdf_de_cumplimiento', return_value=b'%PDF-bandeja'))
            respuesta = ReporteOperativoUnidadAdmin.cumplimiento_del_expediente(None, request)
        filtrar.assert_called_once_with(todas, 'unidad')
        self.assertIs(render.call_args.args[0], seleccionadas)
        self.assertIs(render.call_args.args[1], totales)
        self.assertEqual(render.call_args.kwargs['bandeja'], 'unidad')
        self.assertEqual(respuesta.content, b'%PDF-bandeja')

    def documento(self, pk, nombre):
        return SimpleNamespace(pk=pk, nombre_documental=nombre, etiqueta_corte='2026-B',
            exigido=SimpleNamespace(es_anexo=False),
            nombre_semaforo='Pendiente', plazo_entrega=None, vence_el=None)

    def renderizar(self, filas):
        totales = self.totales()
        grupos = [dict(nombre='Laboratorios', totales=totales, filas=filas)] if filas else []
        identidad = (SimpleNamespace(codigo='QA'), SimpleNamespace(nombre='Universidad QA', siglas='UQA', paleta={}))
        with ExitStack() as pila:
            prefijo = 'apps.documentos.presentation.cumplimiento.'
            pila.enter_context(patch(prefijo + 'ventana_del_periodo', return_value=(date(2026, 8, 17), date(2026, 12, 8))))
            pila.enter_context(patch(prefijo + 'grupos_por_tipo', return_value=grupos))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.identidad_actual', return_value=identidad))
            pila.enter_context(patch('apps.core.presentation.identidad.identidad_actual', return_value=identidad))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None))
            contenido = pdf_de_cumplimiento(filas, totales, 2026, 'B', bandeja='unidad')
        return '\n'.join(p.extract_text() for p in PdfReader(BytesIO(contenido)).pages)

    def test_pdf_solo_detalla_documentos_de_bandeja_y_explicita_porcentajes_generales(self):
        seleccionado, excluido = self.documento(1, 'DOCUMENTO-SELECCIONADO'), self.documento(2, 'DOCUMENTO-EXCLUIDO')
        fila = dict(unidad=SimpleNamespace(nombre='Unidad QA', adscrita_a=None), etiqueta='Incumple',
            entregas=dict(planificacion=[], informe=[]), validados=0, total=5, completo=0,
            nivel=dict(total=None), matriz=[dict(documento=seleccionado)], incumplimientos=[
                dict(documento=d, etiqueta='Vencido', dias=2, motivo='Sin entregar') for d in (seleccionado, excluido)])
        texto = self.renderizar([fila])
        self.assertIn('DOCUMENTO-SELECCIONADO', texto)
        self.assertNotIn('DOCUMENTO-EXCLUIDO', texto)
        self.assertIn('Bandeja: Pendientes de la unidad', texto)
        self.assertIn('totales generales anteriores corresponden a todo', texto)
        self.assertIn('0/5', texto)

    def test_pdf_bandeja_vacia_no_afirma_que_no_existen_unidades(self):
        texto = self.renderizar([])
        self.assertIn('No hay documentos con ese control dentro del alcance seleccionado.', texto)
        self.assertNotIn('No hay unidades que auditar', texto)
