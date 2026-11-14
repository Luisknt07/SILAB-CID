"""Notas parciales, documentos incorrectos y correcciones mediante las API de las cuatro unidades."""
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings

from apps.documentos.management.commands.auditar_escenarios_unidades import (
    AuditoriaHipotesis, TIPOS, declaracion, exigir_qa_local,
)
from apps.documentos.presentation.expediente import cargar_documento
from apps.documentos.presentation.expediente_archivos import codificar_metadatos, identidad_documental


class GuardasHipotesisTests(SimpleTestCase):
    @override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
    def test_comando_rechaza_la_base_operativa_sin_consultarla(self):
        with patch.dict(connection.settings_dict, NAME='citt_db', HOST='127.0.0.1'):
            with self.assertRaises(CommandError):
                exigir_qa_local()


@override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend',
    MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class HipotesisCumplimientoTipologiasTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory(prefix='citt-hipotesis-cuatro-tipos-')
        self.addCleanup(self.media.cleanup)
        self.opciones = override_settings(MEDIA_ROOT=self.media.name)
        self.opciones.enable()
        self.addCleanup(self.opciones.disable)

    def test_cuatro_unidades_aprueban_documentos_sin_puntos_recurrentes(self):
        resultado = AuditoriaHipotesis('testsvarios').ejecutar()
        self.assertEqual({u['tipo'] for u in resultado['unidades']}, set(TIPOS))
        self.assertEqual(resultado['total'], 56)
        self.assertEqual(resultado['brechas'], [])
        self.assertTrue(all(u['resultado_operativo'] is None for u in resultado['unidades']))
        for tipo in TIPOS:
            casos = {c['hipotesis']: c for c in resultado['casos'] if c['tipo'] == tipo}
            with self.subTest(tipo=tipo):
                self.assertEqual(casos['sin_datos_no_inventa_cumplimiento']['observado'], '0.00')
                self.assertEqual(casos['resolucion_vigente_sin_puntos']['observado'], '0.00')
                self.assertTrue(casos['permanente_no_admite_nota']['observado'])
                self.assertTrue(casos['archivo_alterado_detiene_evaluacion']['observado'])
                self.assertTrue(casos['aforo_insuficiente']['observado'])
        self.assertTrue(any(Path(self.media.name).rglob('*.pdf')))

    def test_archivo_de_otra_unidad_se_rechaza_en_cada_tipologia(self):
        from django.contrib.auth import get_user_model
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.presentation.expediente import construir_expediente
        from reportlab.pdfgen.canvas import Canvas
        actor = get_user_model().objects.create_user(username='qa-correspondencia-cuatro')
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                unidad = Unidad.objects.create(nombre='QA identidad ' + tipo, slug='qa-identidad-' + tipo,
                    dependencia=tipo, administrador=actor, fecha_inicio=date(2026, 1, 1))
                documento = next(d for d in construir_expediente(unidad, 2026)
                    if d.exigido.codigo == 'RESOLUCION-CREACION')
                salida = BytesIO()
                lienzo = Canvas(salida)
                lienzo.setSubject(codificar_metadatos(dict(identidad_documental(documento),
                    unidad_id=documento.unidad_id + 1000, esquema=1, borrador=False)))
                lienzo.drawString(40, 780, 'PRUEBA QA: archivo ajeno a la unidad indicada.')
                lienzo.save()
                archivo = SimpleUploadedFile('unidad-equivocada.pdf', salida.getvalue())
                with self.assertRaisesMessage(ValidationError, 'otro documento, unidad o período'):
                    cargar_documento(documento, archivo, actor,
                        declaracion_correspondencia=declaracion(documento))
                documento.refresh_from_db()
                self.assertIsNone(documento.recurso_id)
