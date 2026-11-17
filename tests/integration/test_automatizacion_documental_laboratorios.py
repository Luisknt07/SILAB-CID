"""Paso automático real, excepciones, autoría y conservación de resultados."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
from apps.documentos.models.expediente import DocumentoExpediente, PoliticaDeCalidad
from apps.documentos.presentation.automatizacion_documental import (
    completar_controles, procesar_documento, resumen_automatizacion,
)
from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
from apps.documentos.presentation.expediente import _generar, construir_expediente, tramo_del_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_seguimiento_gobernanza import designar


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class AutomatizacionDocumentalLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='auto-laboratorio-responsable')
        cls.otro = get_user_model().objects.create_user(username='auto-sin-permiso')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio automático QA', slug='auto-lab-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2025, 1, 1))
        documentos = construir_expediente(cls.unidad, 2025)
        # Resultados de investigación (documentos.0027), con la plantilla común de los anexos del informe: con un
        # resultado verificado por el responsable queda completo y no necesita al Director.
        cls.anexo_id = next(d.pk for d in documentos if d.exigido.codigo == 'INVESTIGACION' and d.corte == 'B')
        cls.informe_id = next(d.pk for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-qa-automatizacion-')
        self.addCleanup(carpeta.cleanup)
        medio = override_settings(MEDIA_ROOT=carpeta.name)
        medio.enable()
        self.addCleanup(medio.disable)
        self.registrar_resultado()
        self.anexo = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=self.anexo_id)

    def registrar_resultado(self):
        """Un resultado de investigación del período, con su respaldo en PDF y verificado por el responsable."""
        from apps.documentos.presentation.medicion_metas import registrar_evidencia
        salida = BytesIO()
        pagina = Canvas(salida)
        pagina.drawString(35, 780, 'AUTO-RESULTADO-QA: respaldo real de prueba aislada, procedimiento, alcance y '
                                   'resultado verificables.')
        pagina.save()
        return registrar_evidencia(self.unidad, self.actor, dict(
            tipo='INVESTIGACION', codigo='AUTO-RESULTADO-QA', fecha=date(2025, 10, 17),
            titulo='Resultado documentado AUTO-RESULTADO-QA',
            descripcion='Resultado ocurrido, revisado y atribuido al responsable de la unidad QA.',
            responsable=self.actor, detalle=dict(
                proyecto='Proyecto de laboratorio QA', tipo_producto='informe',
                producto='Informe de resultados obtenidos QA', beneficiario='Comunidad universitaria QA')),
            verificar=True, archivo=SimpleUploadedFile('AUTO-RESULTADO-QA.pdf', salida.getvalue(), 'application/pdf'))

    def generar(self):
        _generar(self.anexo, self.actor)
        return self.anexo

    def informe_con_archivo(self):
        self.generar()
        informe = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=self.informe_id)
        # Fixture del orquestador: la comprobación profunda del PDF y del cierre
        # se ejercita en los módulos propios; aquí aislamos la política de notas.
        informe.recurso = self.anexo.recurso
        informe.version = 1
        informe.estado = 'validado'
        informe.save(update_fields=['recurso', 'version', 'estado'])
        return informe

    @staticmethod
    def analisis_conforme(*_):
        confianza = dict(confiable=True, archivo_integro=True, motivos=[])
        return confianza, [], dict(procedencia=confianza, nota_calculada=100,
            correspondencia_automatica=True, recepcion_automatica=False)

    def test_anexo_nativo_informativo_completo_avanza_sin_director(self):
        self.generar()
        control = procesar_documento(self.anexo, usuario=self.actor)
        self.anexo.refresh_from_db()
        self.assertEqual((control.estado, control.aplicado, self.anexo.estado), ('automatico', True, 'validado'))
        self.assertIsNone(self.anexo.validado_por)
        self.assertIsNone(self.anexo.evaluacion)
        self.assertIsNone(control.nota)  # No duplicar obligaciones con una nota por anexo.
        self.assertTrue(control.resumen['correspondencia_automatica'])

    def test_repetir_no_cambia_archivo_ni_duplica_evento_de_control(self):
        self.generar()
        primero = procesar_documento(self.anexo)
        auditorias = RegistroAuditoriaUnidad.objects.count()
        segundo = procesar_documento(self.anexo)
        self.assertGreaterEqual(segundo.comprobado_en, primero.comprobado_en)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)
        self.assertEqual(primero.recurso_id, segundo.recurso_id)

    def test_alterar_bytes_impide_validacion_y_conserva_advertencia(self):
        self.generar()
        procesar_documento(self.anexo)
        ruta = Path(self.anexo.recurso.archivo.path)
        ruta.write_bytes(ruta.read_bytes() + b'alteracion no registrada')
        control = procesar_documento(self.anexo)
        self.assertEqual(control.estado, 'bloqueado')
        self.assertFalse(control.aplicado)
        self.anexo.refresh_from_db()
        self.assertEqual(self.anexo.estado, 'generado')

    def test_demo_no_avanza_aunque_el_pdf_nativo_sea_identico(self):
        self.generar()
        with override_settings(MEDICION_SOLO_DEMO=True):
            control = procesar_documento(self.anexo)
        self.assertEqual(control.estado, 'bloqueado')
        self.assertFalse(control.aplicado)

    def test_catalogo_personalizado_no_hereda_aprobacion_automatica(self):
        self.generar()
        self.anexo.exigido.requiere_firma = True
        self.anexo.exigido.save(update_fields=['requiere_firma'])
        control = procesar_documento(self.anexo)
        self.assertNotEqual(control.estado, 'automatico')
        self.assertFalse(control.aplicado)

    def test_sin_archivo_muestra_que_falta_sin_inventar_avance(self):
        control = procesar_documento(self.anexo)
        self.assertEqual(control.estado, 'sin_archivo')
        self.assertIsNone(control.nota)
        self.assertFalse(control.aplicado)

    def test_actor_ajeno_no_puede_ejecutar_el_control(self):
        with self.assertRaises(PermissionDenied):
            procesar_documento(self.anexo, usuario=self.otro)
        self.assertFalse(ControlAutomaticoDocumento.objects.exists())

    def test_tipologia_fuera_de_las_cuatro_no_recibe_controles(self):
        self.unidad.dependencia = 'centros_id'
        self.unidad.save(update_fields=['dependencia'])
        self.anexo.unidad = self.unidad
        self.assertIsNone(procesar_documento(self.anexo))
        self.assertFalse(ControlAutomaticoDocumento.objects.exists())

    def test_las_cuatro_tipologias_reciben_control_sin_inventar_archivo_ni_nota(self):
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(tipo=tipo):
                self.unidad.dependencia = tipo
                self.unidad.save(update_fields=['dependencia'])
                self.anexo.unidad = self.unidad
                control = procesar_documento(self.anexo)
                self.assertIsNotNone(control)
                self.assertEqual(control.estado, 'sin_archivo')
                self.assertIsNone(control.nota)
                self.assertFalse(control.aplicado)

    def test_contexto_de_otra_unidad_o_periodo_no_se_puede_reutilizar(self):
        inicio, fin = tramo_del_documento(self.anexo)
        contexto = ContextoCalidad(self.unidad, date(2024, 1, 1), fin)
        self.assertNotEqual(contexto.inicio, inicio)
        with self.assertRaisesMessage(ValueError, 'no corresponde'):
            procesar_documento(self.anexo, contexto=contexto)

    def test_lista_batch_no_abre_pdfs_y_repetir_resumen_no_consulta(self):
        self.generar()
        procesar_documento(self.anexo)
        documentos = list(DocumentoExpediente.objects.filter(pk=self.anexo.pk).select_related('unidad', 'exigido', 'recurso'))
        with self.assertNumQueries(1):
            completar_controles(documentos)
        with self.assertNumQueries(0):
            resumen = resumen_automatizacion(documentos)
            self.assertEqual(resumen['automatico'], 1)
            self.assertIsNone(documentos[0].nota)

    def test_version_nueva_retira_el_control_visible_y_el_aporte_anterior(self):
        informe = self.informe_con_archivo()
        with patch('apps.documentos.presentation.automatizacion_documental._analizar', self.analisis_conforme):
            procesar_documento(informe)
        self.assertEqual(informe.nota, 100)
        informe.version += 1
        informe.save(update_fields=['version'])
        completar_controles([informe])
        self.assertFalse(informe.automatizacion['vigente'])
        self.assertIsNone(informe.nota)

    def test_cambio_de_reglas_o_firma_invalida_control_sin_abrir_pdf(self):
        self.generar()
        procesar_documento(self.anexo)
        for campo, valor in (('requiere_firma', True), ('fuente_reporte', 'informe'),
                ('origen', 'unidad'), ('periodicidad', 'anual'), ('activo', False)):
            with self.subTest(campo=campo):
                original = getattr(self.anexo.exigido, campo)
                setattr(self.anexo.exigido, campo, valor)
                completar_controles([self.anexo])
                self.assertFalse(self.anexo.automatizacion['vigente'])
                setattr(self.anexo.exigido, campo, original)
        self.anexo.firma_verificada = not self.anexo.firma_verificada
        completar_controles([self.anexo])
        self.assertFalse(self.anexo.automatizacion['vigente'])

    def test_nota_automatica_no_inventa_evaluador_y_conserva_politica_congelada(self):
        informe = self.informe_con_archivo()
        informe.entregado_tarde = True
        informe.save(update_fields=['entregado_tarde'])
        PoliticaDeCalidad.objects.update_or_create(pk=1, defaults=dict(penalizacion_entrega_tardia=20))
        with patch('apps.documentos.presentation.automatizacion_documental._analizar', self.analisis_conforme):
            control = procesar_documento(informe)
            self.assertEqual(control.nota, Decimal(80))
            informe.refresh_from_db()
            self.assertIsNone(informe.evaluacion)
            self.assertIsNone(informe.evaluado_por)
            self.assertIsNone(informe.recibido_por)
            self.assertIsNotNone(informe.recibido_en)
            PoliticaDeCalidad.objects.update_or_create(pk=1, defaults=dict(penalizacion_entrega_tardia=30))
            segundo = procesar_documento(informe)
        self.assertEqual(segundo.nota, 80)
        self.assertEqual(segundo.fuentes_sha256, control.fuentes_sha256)

    def test_evaluacion_manual_incluso_sin_usuario_no_se_sustituye(self):
        informe = self.informe_con_archivo()
        informe.evaluacion, informe.evaluacion_version = 75, informe.version
        informe.save(update_fields=['evaluacion', 'evaluacion_version'])
        with patch('apps.documentos.presentation.automatizacion_documental._analizar', self.analisis_conforme):
            control = procesar_documento(informe)
        informe.refresh_from_db()
        self.assertTrue(control.resumen['manual_preservada'])
        self.assertFalse(control.aplicado)
        self.assertEqual(informe.nota, 75)

    def test_diagnostico_conforme_conserva_aplicacion_nota_y_politica(self):
        informe = self.informe_con_archivo()
        with patch('apps.documentos.presentation.automatizacion_documental._analizar', self.analisis_conforme):
            anterior = procesar_documento(informe)
            diagnostico = procesar_documento(informe, aplicar=False)
        self.assertTrue(diagnostico.aplicado)
        self.assertEqual(diagnostico.nota, anterior.nota)
        self.assertEqual(diagnostico.politica, anterior.politica)
        self.assertEqual(informe.nota, 100)

    def resolucion_heredada(self):
        from apps.documentos.presentation.conformidad_permanente import aprobar_permanente
        from apps.documentos.presentation.expediente import (
            _heredar, cargar_documento, validar_documento,
        )
        from tests.integration.test_confianza_documental_automatica import pdf_prueba
        from tests.integration.utiles import correspondencia_revisada
        director = get_user_model().objects.create_superuser(username='auto-director-qa', password='qa')
        designar(director)
        documentos = construir_expediente(self.unidad, 2024)
        origen = next(d for d in documentos if d.exigido.codigo == 'RESOLUCION-CREACION')
        cargar_documento(origen, SimpleUploadedFile('resolucion-qa.pdf', pdf_prueba(texto=
            'Resolución QA de creación del Laboratorio automático QA. Autoridad y fecha de pruebas.')),
            self.actor, declaracion_correspondencia=correspondencia_revisada(origen))
        validar_documento(origen, self.actor)
        aprobar_permanente(origen, director, version=origen.version,
            huella=origen.recurso.hash_sha256, confirmado=True,
            declaracion_correspondencia=correspondencia_revisada(origen))
        actual = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(
            unidad=self.unidad, anio=2025, exigido__codigo='RESOLUCION-CREACION')
        _heredar(actual)
        return origen, actual

    def test_aprobacion_permanente_humana_se_reutiliza_solo_para_mismo_archivo(self):
        origen, actual = self.resolucion_heredada()
        control = procesar_documento(actual)
        self.assertTrue(control.aplicado)
        self.assertIsNone(actual.nota)
        self.assertIs(actual.cumple, True)
        self.assertIsNone(actual.evaluacion)
        self.assertIsNone(origen.evaluacion)
        self.assertIsNone(origen.evaluado_por_id)
        self.assertEqual(control.resumen['aprobacion_reutilizada']['documento_id'], origen.pk)
        self.assertEqual(control.resumen['aprobacion_reutilizada']['actor_id'], origen.recibido_por_id)

    def test_cambio_del_archivo_permanente_impide_reutilizar_aprobacion(self):
        origen, actual = self.resolucion_heredada()
        ruta = Path(actual.recurso.archivo.path)
        ruta.write_bytes(ruta.read_bytes() + b'cambio de archivo')
        control = procesar_documento(actual)
        self.assertFalse(control.aplicado)
        self.assertIsNone(actual.nota)
        origen.refresh_from_db()
        self.assertIsNone(origen.evaluacion)
        self.assertIsNone(origen.evaluado_por_id)

    def test_simulacion_del_comando_no_guarda_y_diagnostico_no_valida(self):
        self.generar()
        auditorias = RegistroAuditoriaUnidad.objects.count()
        call_command('automatizar_documentos_laboratorios', unidad=self.unidad.slug, anio=2025, corte='B', verbosity=0)
        self.assertFalse(ControlAutomaticoDocumento.objects.exists())
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), auditorias)
        call_command('automatizar_documentos_laboratorios', unidad=self.unidad.slug, anio=2025,
                     corte='B', solo_diagnostico=True, verbosity=0)
        self.anexo.refresh_from_db()
        self.assertEqual(self.anexo.estado, 'generado')
        self.assertFalse(ControlAutomaticoDocumento.objects.filter(aplicado=True).exists())

    def test_get_no_analiza_y_post_autorizado_muestra_resumen_y_hallazgos(self):
        self.generar()
        self.client.force_login(self.actor)
        ruta = reverse('gestion_expediente_unidad', args=[self.unidad.slug])
        inicial = RegistroAuditoriaUnidad.objects.count()
        respuesta = self.client.get(ruta, dict(anio=2025, corte='B'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), inicial)
        self.assertFalse(ControlAutomaticoDocumento.objects.exists())
        respuesta = self.client.post(ruta, dict(accion='automatizar', anio=2025, corte='B'))
        self.assertEqual(respuesta.status_code, 302)
        respuesta = self.client.get(ruta, dict(anio=2025, corte='B'))
        self.assertContains(respuesta, 'Validado automáticamente')
        self.assertTrue(ControlAutomaticoDocumento.objects.filter(aplicado=True).exists())
