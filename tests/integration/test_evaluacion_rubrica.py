"""Rúbrica calculada en servidor, sin validar borradores ni perder la trazabilidad."""
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from tests.integration.utiles import (pdf_legible_prueba, cargar_documento_revisado, recibir_documento_revisado)
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.templatetags.static import static

from apps.formacion.presentation.evaluacion_rubrica import evaluar_con_rubrica, revisar_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.documentos.models.expediente import DocumentoExigido
from tests.integration.test_direccion_recibe_y_califica import ANIO, BaseDelExpediente


class RubricaTests(BaseDelExpediente):
    codigo_rubrica = 'EVIDENCIA-EVALUACION-ESPECIAL'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Los documentos personalizados conservan la rúbrica genérica. Los
        # permanentes y los planes tienen su propia aprobación o conformidad.
        DocumentoExigido.objects.create(
            codigo=cls.codigo_rubrica,
            nombre='Evidencia especial sujeta a evaluación documental',
            carpeta='evaluacion',
            periodicidad='semestral',
            origen='unidad',
            requiere_firma=True,
        )

    def documento_rubrica(self, unidad=None):
        return self.documento(unidad or self.laboratorio, self.codigo_rubrica)

    def test_el_reporte_inicia_en_el_periodo_del_calendario_y_respeta_filtros(self):
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        cortes = {'A': (date(ANIO, 2, 1), date(ANIO, 8, 15)),
                  'B': (date(ANIO, 8, 16), date(ANIO, 12, 20))}
        with patch('apps.gestion_unidades.admin.reportes.timezone.localdate', return_value=date(ANIO, 7, 20)), \
             patch('apps.documentos.presentation.expediente.cortes_del_anio', return_value=cortes):
            pagina = self.client.get(url)
            self.assertEqual(pagina.context['corte'], 'A')
            self.assertEqual(pagina.context['anio'], ANIO)
            anual = self.client.get(url, {'anio': ANIO, 'corte': ''})
            self.assertEqual(anual.context['corte'], '')
            elegido = self.client.get(url, {'anio': ANIO, 'corte': 'B'})
            self.assertEqual(elegido.context['corte'], 'B')

    def test_incumplimiento_sin_entrega_se_califica_sin_simular_recepcion(self):
        documento = self.documento_rubrica()
        estado = documento.estado
        valores = {f'criterio_{i}': '0' for i in range(4)}
        evaluar_con_rubrica(documento, self.direccion, valores, documento.version, '', True,
                           comentario='No se ha entregado la evidencia.')
        documento.refresh_from_db()
        self.assertEqual(documento.nota, 0)
        self.assertFalse(documento.cumple)
        self.assertEqual(documento.estado, estado)
        self.assertFalse(documento.firma_verificada)
        self.assertIsNone(documento.recurso_id)
        self.assertTrue(documento.evaluacion_recomendaciones)
        self.client.force_login(self.direccion)
        pagina = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                               {'anio': ANIO, 'revisar': documento.pk})
        self.assertContains(pagina, 'data-revision-titulo="Revisar documento"', count=1)
        self.assertContains(pagina, 'data-evaluar-documento')
        self.assertNotContains(pagina, 'id="formEvaluacion"')
        with self.assertRaises(ValidationError):
            evaluar_con_rubrica(documento, self.direccion,
                               {f'criterio_{i}': '75' for i in range(4)}, documento.version, '', True)

    def test_minimo_alto_no_recomienda_mantener_un_resultado_insuficiente(self):
        from apps.documentos.models.expediente import PoliticaDeCalidad
        from apps.documentos.models.expediente import olvidar_politica

        documento = self.entrega()
        politica = PoliticaDeCalidad.objects.first() or PoliticaDeCalidad()
        politica.minimo_cumplimiento = 80
        politica.save()
        olvidar_politica()
        self.addCleanup(olvidar_politica)
        self.evaluar(documento, nivel=75)
        self.assertIn('80 %', documento.evaluacion_recomendaciones)
        self.assertNotIn('Mantener los resultados', documento.evaluacion_recomendaciones)
        self.assertTrue(documento.evaluacion_debilidades)

    def entrega(self):
        documento = self.documento_rubrica()
        self.abrir_plazo(documento)
        cargar_documento_revisado(documento, SimpleUploadedFile('evidencia.pdf', pdf_legible_prueba('Evidencia de prueba para la rúbrica.', firmado=True)), self.coordinador)
        recibir_documento_revisado(documento, self.direccion)
        return documento

    def evaluar(self, documento, nivel=50, **extra):
        argumentos = dict(valores={f'criterio_{i}': str(nivel) for i in range(4)},
            version=documento.version, huella=documento.recurso.hash_sha256, confirmado=True)
        argumentos.update(extra)
        evaluar_con_rubrica(documento, self.direccion, **argumentos)

    def test_calcula_nota_y_observaciones_y_conserva_los_criterios(self):
        documento = self.entrega()
        self.evaluar(documento)
        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 50)
        self.assertTrue(documento.evaluacion_debilidades)
        self.assertTrue(documento.evaluacion_recomendaciones)
        registro = RegistroAuditoriaUnidad.objects.filter(datos_nuevos__rubrica__isnull=False).get()
        self.assertEqual(registro.datos_nuevos['nota_bruta'], 50)
        self.assertEqual(len(registro.datos_nuevos['criterios']), 4)
        self.assertEqual(registro.datos_nuevos['sha256'], documento.recurso.hash_sha256)

    def test_rechaza_version_obsoleta_y_niveles_inventados(self):
        documento = self.entrega()
        for extra in ({'version': 999}, {'huella': 'otra'}, {'confirmado': False},
                      {'valores': {'criterio_0': '1000'}}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                self.evaluar(documento, **extra)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

    def test_no_califica_un_borrador_como_si_estuviera_firmado(self):
        documento = self.documento_rubrica()
        with self.assertRaises(ValidationError):
            evaluar_con_rubrica(documento, self.direccion, {}, documento.version, '', True)

    def test_redondeo_y_reconocimiento_son_explicitos(self):
        documento = self.entrega()
        self.evaluar(documento, valores={'criterio_0': '50', 'criterio_1': '50', 'criterio_2': '75', 'criterio_3': '75'})
        self.assertEqual(documento.evaluacion, 63)
        self.evaluar(documento, nivel=100)
        self.assertIn('Gestión destacada', documento.evaluacion_observacion)

    def test_revision_y_acordeones_se_renderizan_sin_guardar_evaluacion(self):
        documento = self.entrega()
        self.client.force_login(self.direccion)
        pagina = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
            {'anio': ANIO, 'revisar': documento.pk})
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'class="citt-unidad"')
        self.assertContains(pagina, 'data-revision-titulo="Revisar documento"')
        self.assertContains(pagina, static('admin/js/evaluacion_unidades.js'))
        ruta_script = finders.find('admin/js/evaluacion_unidades.js')
        self.assertIsNotNone(ruta_script)
        script = Path(ruta_script).read_text(encoding='utf-8')
        self.assertIn('document.body.appendChild(modal)', script)
        self.assertIn('[data-evaluar-documento]', script)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

    def test_la_resolucion_muestra_vigencia_sin_ofrecer_cuatro_criterios(self):
        documento = self.documento(self.laboratorio, 'RESOLUCION-CREACION', '')
        self.assertEqual(revisar_documento(documento)['modalidad'], 'permanente')
        self.client.force_login(self.direccion)
        auditorias = RegistroAuditoriaUnidad.objects.count()

        pagina = self.client.get(
            reverse('admin:reportes-cumplimiento-expediente'),
            {'anio': ANIO, 'revisar': documento.pk},
        )

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Documento permanente')
        self.assertContains(pagina, 'No recibe calificación numérica.')
        self.assertNotContains(pagina, 'id="formEvaluacion"')
        self.assertNotContains(pagina, 'data-rubrica')
        self.assertNotContains(pagina, 'Guardar evaluación y observaciones')
        for indice in range(4):
            self.assertNotContains(pagina, f'name="criterio_{indice}"')
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)
        self.assertIsNone(documento.recibido_en)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)

    def test_la_revision_no_ofrece_guardar_sin_recibir(self):
        documento = self.entrega()
        documento.estado = 'cargado'
        self.assertFalse(revisar_documento(documento)['evaluable'])
        self.assertTrue(revisar_documento(documento)['recibible'])

    def test_el_post_del_admin_calcula_y_conserva_la_ruta(self):
        documento = self.entrega()
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        respuesta = self.client.post(url, {
            'accion': 'evaluar_rubrica', 'documento': documento.pk,
            'version': documento.version, 'huella': documento.recurso.hash_sha256,
            'confirmado': '1', 'query': f'anio={ANIO}&revisar={documento.pk}#evaluacion',
            **{f'criterio_{i}': '75' for i in range(4)},
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(f'revisar={documento.pk}', respuesta.url)
        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 75)

    def test_el_decanato_no_guarda_rubrica_ni_ve_documentos_ajenos(self):
        documento = self.entrega()
        self.client.force_login(self.decano)
        url = reverse('admin:reportes-cumplimiento-expediente')
        respuesta = self.client.post(url, {'accion': 'evaluar_rubrica', 'documento': documento.pk})
        self.assertEqual(respuesta.status_code, 403)
        ajeno = self.documento_rubrica(self.suelto)
        self.assertEqual(self.client.get(url, {'anio': ANIO, 'revisar': ajeno.pk}).status_code, 400)
