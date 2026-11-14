"""La vigencia es una decisión sin puntuación de desempeño semestral."""
from contextlib import ExitStack
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from pypdf import PdfReader

from apps.documentos.presentation.mejora_continua import pdf_de_mejora_continua
from apps.gestion_unidades.presentation.reportes_condiciones import _tablas_seguridad


class ExportacionesVigenciaPermanenteTests(SimpleTestCase):
    def documento(self, codigo='RESOLUCION-CREACION'):
        return SimpleNamespace(
            exigido=SimpleNamespace(codigo=codigo, periodicidad='unica', es_anexo=False,
                                   nombre='Documento permanente QA'),
            nombre_documental='DOCUMENTO-PERMANENTE-QA', etiqueta_corte='Año 2026',
            estado='validado', nota=100, evaluacion=90,
            aprobacion_permanente={'vigente': True, 'comentario': 'Autoridad y alcance comprobados.'},
            observacion='', evaluacion_observacion='Calificación histórica 90 %',
            evaluacion_debilidades='', evaluacion_recomendaciones='', version=1,
            recurso=SimpleNamespace(unidad_id=1, archivo='protocolo.pdf'),
            firma_verificada=True, validado_por=None, cargado_por=None,
            get_estado_display=lambda: 'Validado y enviado',
        )

    def test_pdf_de_mejora_muestra_vigencia_sin_publicar_el_credito_como_nota(self):
        documento = self.documento()
        fila = dict(documento=documento, nota=100, estado='Validado y enviado')
        cumplimiento = dict(
            unidad=SimpleNamespace(nombre='Laboratorio QA', dependencia='laboratorios', adscrita_a=None),
            anio=2026, corte='B', inicio=date(2026, 8, 17), fin=date(2026, 12, 8),
            filas=[fila], total=None, minimo=70, etiqueta='Sin cierre operativo evaluado',
            evaluados=0, sin_puntuar=0, incumplidos=[], sin_uso=True,
            uso=dict(sesiones=0, atendidas=0, horas=0, usuarios=0, practicas=0, servicios=0),
        )
        identidad = (SimpleNamespace(codigo='QA'),
                     SimpleNamespace(nombre='Universidad QA', siglas='UQA', paleta={}))
        with ExitStack() as pila:
            for modulo in ('apps.documentos.presentation.expediente_pdf',
                           'apps.core.presentation.pdf_institucional'):
                pila.enter_context(patch(modulo + '.identidad_actual', return_value=identidad))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional',
                                     return_value=None))
            contenido = pdf_de_mejora_continua(cumplimiento)
        texto = ' '.join(' '.join(p.extract_text() for p in PdfReader(BytesIO(contenido)).pages).split())

        self.assertIn('Vigente', texto)
        self.assertIn('aprobación única', texto)
        self.assertIn('Resultado / vigencia', texto)
        self.assertNotIn('Nota registrada', texto)
        self.assertNotIn('90 %', texto)
        # La aprobación permanente no inventa un resultado del cierre.
        self.assertNotIn('100 %', texto)
        self.assertEqual((documento.nota, documento.evaluacion, fila['nota']), (100, 90, 100))

    def test_dataset_compartido_de_seguridad_distingue_aprobacion_y_archivo(self):
        documento = self.documento('PROTOCOLO-BIOSEGURIDAD')
        unidad = SimpleNamespace(pk=1)
        consulta_vacia = MagicMock()
        for metodo in ('order_by', 'select_related', 'distinct'):
            getattr(consulta_vacia, metodo).return_value = consulta_vacia
        consulta_vacia.__getitem__.return_value = []
        prefijo = 'apps.gestion_unidades.presentation.reportes_condiciones.'
        with ExitStack() as pila:
            pila.enter_context(patch(prefijo + '_documentos_seguridad', return_value=(documento, [])))
            pila.enter_context(patch(prefijo + '_documento_respaldado', return_value=True))
            pila.enter_context(patch(prefijo + '_respaldo', return_value='protocolo.pdf'))
            pila.enter_context(patch(prefijo + '_inspecciones', return_value=[]))
            pila.enter_context(patch(prefijo + 'es_laboratorio', return_value=False))
            for modelo in ('RequisitoAcceso', 'HabilitacionAcceso', 'IncidenciaEquipo'):
                pila.enter_context(patch(prefijo + modelo + '.objects.filter', return_value=consulta_vacia))
            for aprobacion, esperado in (
                ({'vigente': True}, 'Vigente'),
                ({'vigente': False}, 'Pendiente de aprobación'),
                ({'revocada': True}, 'Observado'),
            ):
                with self.subTest(estado=esperado):
                    documento.aprobacion_permanente = aprobacion
                    tablas = _tablas_seguridad(unidad, date(2026, 3, 1), date(2026, 3, 10))
                    fila = tablas[0]['rows'][0]
                    self.assertEqual(fila[2], esperado)
                    self.assertIn('Aprobación técnica única.', fila[-1])
                    self.assertNotIn('100 %', str(fila))
                    self.assertEqual(documento.nota, 100)
