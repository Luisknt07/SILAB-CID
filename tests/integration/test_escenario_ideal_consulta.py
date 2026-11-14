"""El ensayo sintético es local, de lectura y accesible sólo a la unidad y sus receptores."""
import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.escenario_ideal_consulta import escenario_disponible
from apps.documentos.presentation.escenario_ideal_exportacion import directorio_escenario
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.utiles import identificar, pdf_legible_prueba


@override_settings(DEBUG=True)
class EscenarioIdealConsultaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinador = usuarios.create_user('ensayo-coordinacion')
        cls.receptor = usuarios.create_user('ensayo-receptor')
        cls.ajeno = usuarios.create_user('ensayo-ajeno')
        cls.direccion = usuarios.create_superuser('ensayo-direccion', 'ensayo@example.test', 'clave-qa')
        for usuario in (cls.coordinador, cls.receptor, cls.ajeno, cls.direccion):
            identificar(usuario, tipo_usuario='administrativo', carrera='')
        cls.dependencia = DependenciaAcademica.objects.create(nombre='Dependencia de ensayo', tipo='decanato')
        cls.dependencia.receptores.add(cls.receptor)
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de ensayo aislado', slug='ensayo-local-qa',
            dependencia='laboratorios', administrador=cls.coordinador, fecha_inicio=date(2026, 1, 1),
            adscrita_a=cls.dependencia)

    def setUp(self):
        temporal = TemporaryDirectory(prefix='citt-qa-consulta-ideal-')
        self.addCleanup(temporal.cleanup)
        configuracion = override_settings(BASE_DIR=Path(temporal.name))
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.directorio = directorio_escenario(self.unidad.slug, 2026, 'B')
        self.directorio.mkdir(parents=True)
        self.pdf = pdf_legible_prueba('PRUEBA AISLADA. DATOS SINTETICOS. SIN VALIDEZ INSTITUCIONAL.')
        self.archivo = self.directorio / 'copia-qa/INFORME-SEMESTRAL.pdf'
        self.archivo.parent.mkdir()
        self.archivo.write_bytes(self.pdf)
        self.manifiesto = dict(version=1, es_prueba=True,
            unidad=dict(slug=self.unidad.slug, nombre=self.unidad.nombre), anio=2026, corte='B',
            inicio='2026-08-17', fin='2026-12-08', corte_simulado='2026-12-09',
            general='100.00', nota_cierre='100.00',
            resumen=dict(practicas_planificadas=6, practicas_ejecutadas=6, guias=1,
                         sesiones=6, estudiantes=12, horas=12, equipos=3),
            indicadores=[dict(codigo='practicas', nombre='Prácticas ejecutadas', indicador='Prácticas',
                meta=6, registrado=6, porcentaje=100, exigible=True, estado='Cumple', motivo='')],
            documentos=[dict(numero=1, codigo='INFORME-SEMESTRAL', nombre='Informe semestral de ensayo',
                anexo=False, estado='validado', resultado='100.00', fuente='Sistema',
                control='Validado automáticamente', hallazgos=[],
                archivo='copia-qa/INFORME-SEMESTRAL.pdf', sha256=hashlib.sha256(self.pdf).hexdigest(),
                original_sha256=hashlib.sha256(self.pdf).hexdigest())])
        self.guardar()
        self.url = reverse('escenario_ideal_laboratorio', args=[self.unidad.slug])
        self.url_pdf = reverse('escenario_ideal_laboratorio_pdf', args=[self.unidad.slug, 'INFORME-SEMESTRAL'])
        self.parametros = dict(anio=2026, corte='B')
        self.client.force_login(self.coordinador)

    def guardar(self, datos=None):
        (self.directorio / 'manifiesto.json').write_text(
            json.dumps(self.manifiesto if datos is None else datos, ensure_ascii=False), encoding='utf8')

    def assert_no_disponible(self):
        self.assertFalse(escenario_disponible(self.unidad, 2026, 'B'))
        for url in (self.url, self.url_pdf):
            self.assertEqual(self.client.get(url, self.parametros).status_code, 404)

    @staticmethod
    def cerrar_pdf(respuesta):
        # El iterador del Client cierra el FileResponse desconectando de forma
        # temporal close_old_connections. Un segundo response.close() manual
        # enviaría request_finished dentro de la transacción del TestCase.
        if getattr(respuesta, 'streaming', False) and not respuesta.closed:
            b''.join(respuesta.streaming_content)

    def test_coordinacion_direccion_y_receptor_pueden_consultar_la_prueba_identificada(self):
        for usuario in (self.coordinador, self.direccion, self.receptor):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = self.client.get(self.url, self.parametros)
                self.assertContains(respuesta, 'PRUEBA')
                self.assertContains(respuesta, 'INFORME-SEMESTRAL')
                self.assertContains(respuesta, self.unidad.nombre)
        self.assertTrue(escenario_disponible(self.unidad, 2026, 'B'))

    def test_pdf_autorizado_conserva_bytes_y_se_entrega_sin_cache_publica(self):
        for usuario in (self.coordinador, self.direccion, self.receptor):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = self.client.get(self.url_pdf, self.parametros)
                try:
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(respuesta['Content-Type'], 'application/pdf')
                    self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
                    self.assertIn('PRUEBA-INFORME-SEMESTRAL.pdf', respuesta['Content-Disposition'])
                    self.assertEqual(b''.join(respuesta.streaming_content), self.pdf)
                finally:
                    self.cerrar_pdf(respuesta)
        descarga = self.client.get(self.url_pdf, dict(self.parametros, descargar='1'))
        try:
            self.assertIn('attachment;', descarga['Content-Disposition'])
        finally:
            self.cerrar_pdf(descarga)

    def test_usuario_ajeno_no_puede_leer_html_ni_pdf(self):
        self.client.force_login(self.ajeno)
        for url in (self.url, self.url_pdf):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, self.parametros).status_code, 403)

    def test_sesion_obligatoria_en_ambas_consultas(self):
        self.client.logout()
        for url in (self.url, self.url_pdf):
            respuesta = self.client.get(url, self.parametros)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn('next=', respuesta['Location'])

    def test_debug_desactivado_oculta_ensayos_incluso_a_direccion(self):
        self.client.force_login(self.direccion)
        with override_settings(DEBUG=False):
            self.assert_no_disponible()

    def test_sin_manifiesto_no_se_muestra_un_ensayo_parcial(self):
        (self.directorio / 'manifiesto.json').unlink()
        self.assert_no_disponible()

    def test_json_invalido_y_raices_de_tipo_incorrecto_responden_404(self):
        ruta = self.directorio / 'manifiesto.json'
        for contenido in ('{incompleto', '[]', 'null', '1', '"texto"'):
            with self.subTest(contenido=contenido):
                ruta.write_text(contenido, encoding='utf8')
                self.assert_no_disponible()

    def test_manifiesto_no_puede_cambiar_unidad_periodo_ni_caracter_de_prueba(self):
        casos = [dict(version=2), dict(es_prueba=False), dict(anio=2025), dict(corte='A'),
                 dict(unidad=dict(slug='otra-unidad')), dict(unidad=None), dict(unidad=[])]
        for cambios in casos:
            with self.subTest(cambios=cambios):
                self.guardar(dict(self.manifiesto, **cambios))
                self.assert_no_disponible()

    def test_parametros_fuera_de_rango_o_no_numericos_no_muestran_el_ensayo(self):
        for parametros in (dict(anio='incorrecto', corte='B'), dict(anio=1900, corte='B'),
                           dict(anio=2300, corte='B'), dict(anio=2026, corte='C'),
                           dict(anio=2025, corte='B'), dict(anio=2026, corte='A')):
            with self.subTest(parametros=parametros):
                for url in (self.url, self.url_pdf):
                    self.assertEqual(self.client.get(url, parametros).status_code, 404)

    def test_listado_de_documentos_invalido_no_dispara_error_500(self):
        casos = [None, {}, 'archivo', [None], ['archivo'],
                 [dict(codigo='INFORME-SEMESTRAL')],
                 [dict(self.manifiesto['documentos'][0], archivo=None)],
                 [dict(self.manifiesto['documentos'][0], sha256=None)],
                 [dict(self.manifiesto['documentos'][0], sha256='huella-invalida')],
                 [dict(self.manifiesto['documentos'][0], codigo='../INFORME')],
                 [dict(self.manifiesto['documentos'][0]), dict(self.manifiesto['documentos'][0])]]
        for documentos in casos:
            with self.subTest(documentos=documentos):
                self.guardar(dict(self.manifiesto, documentos=documentos))
                self.assert_no_disponible()

    def test_documento_desconocido_no_se_busca_por_nombre_en_el_disco(self):
        desconocido = reverse('escenario_ideal_laboratorio_pdf', args=[self.unidad.slug, 'AJENO'])
        self.assertEqual(self.client.get(desconocido, self.parametros).status_code, 404)

    def test_no_se_pueden_servir_rutas_relativas_ni_absolutas_fuera_del_ensayo(self):
        ajeno = self.directorio.parent / 'otro.pdf'
        ajeno.write_bytes(self.pdf)
        for ruta in ('../otro.pdf', str(ajeno.resolve())):
            with self.subTest(ruta=ruta):
                datos = deepcopy(self.manifiesto)
                datos['documentos'][0]['archivo'] = ruta
                self.guardar(datos)
                self.assertEqual(self.client.get(self.url_pdf, self.parametros).status_code, 404)

    def test_archivo_alterado_o_retirado_no_pasa_la_verificacion_de_huella(self):
        self.archivo.write_bytes(self.pdf + b'cambio posterior')
        self.assertEqual(self.client.get(self.url_pdf, self.parametros).status_code, 404)
        self.archivo.unlink()
        self.assertEqual(self.client.get(self.url_pdf, self.parametros).status_code, 404)

    def test_otros_tipos_de_unidad_no_reciben_la_consulta_ideal_de_laboratorio(self):
        self.unidad.dependencia = 'observatorios'
        self.unidad.save(update_fields=['dependencia'])
        self.assert_no_disponible()

    def test_consultas_y_descargas_no_modifican_documentos_notas_ni_auditorias(self):
        modelos = (Unidad, DocumentoExpediente, ControlAutomaticoDocumento, RegistroAuditoriaUnidad)
        antes = {modelo._meta.label: modelo.objects.count() for modelo in modelos}
        self.assertEqual(self.client.get(self.url, self.parametros).status_code, 200)
        respuesta = self.client.get(self.url_pdf, self.parametros)
        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(b''.join(respuesta.streaming_content), self.pdf)
        finally:
            self.cerrar_pdf(respuesta)
        self.assertEqual(antes, {modelo._meta.label: modelo.objects.count() for modelo in modelos})
        self.assertEqual(self.archivo.read_bytes(), self.pdf)

    def test_consulta_no_acepta_post_ni_dispara_operaciones(self):
        for url in (self.url, self.url_pdf):
            self.assertEqual(self.client.post(url, self.parametros).status_code, 405)


class EscenarioIdealPresentacionTests(SimpleTestCase):
    @staticmethod
    def control(**cambios):
        documento = dict(resultado='100.00', fuente='Dirección de prueba', control='Por revisar',
            hallazgos=[dict(mensaje='Se requiere criterio humano para aprobar este documento.')])
        documento.update(cambios)
        return render_to_string('portal/pages/unidades/gestion/includes/escenario_ideal_control.html',
                                dict(documento=documento))

    def test_decision_humana_se_muestra_concluida_y_conserva_diagnostico_previo_desplegable(self):
        for fuente in ('Dirección', 'Dirección de prueba'):
            with self.subTest(fuente=fuente):
                html = self.control(fuente=fuente)
                cerrado, desplegable = html.split('<details>', 1)
                self.assertIn('Revisión humana registrada en el ensayo', cerrado)
                self.assertNotIn('Por revisar', cerrado)
                self.assertIn('Diagnóstico automático anterior a la revisión humana: Por revisar', desplegable)
                self.assertIn('Se requiere criterio humano', desplegable)

    def test_nota_humana_cero_tambien_es_una_revision_realizada_en_el_ensayo(self):
        self.assertIn('Revisión humana registrada en el ensayo', self.control(resultado=0))

    def test_sin_resultado_no_se_inventa_una_revision_humana(self):
        html = self.control(resultado=None)
        self.assertNotIn('Revisión humana registrada', html)
        self.assertIn('Por revisar', html.split('<details>', 1)[0])

    def test_control_del_sistema_no_se_atribuye_a_direccion(self):
        html = self.control(fuente='Sistema', control='Validado automáticamente')
        self.assertIn('Validado automáticamente', html.split('<details>', 1)[0])
        self.assertNotIn('Revisión humana registrada', html)

    def test_nombre_de_indicador_admite_ambos_esquemas_del_exportador(self):
        escenario = dict(anio=2026, corte='B', general='100.00', nota_cierre='100.00',
                         documentos=[], resumen={}, indicadores=[])
        for campos, esperado in ((dict(nombre='Nombre documental'), 'Nombre documental'),
                                 (dict(actividad='Actividad documental'), 'Actividad documental'),
                                 ({}, 'CODIGO-QA')):
            with self.subTest(campos=campos):
                escenario['indicadores'] = [dict(codigo='CODIGO-QA', indicador='Medición QA', **campos)]
                html = render_to_string('portal/pages/unidades/gestion/escenario_ideal.html',
                    dict(unidad=dict(slug='fablab', nombre='FabLab QA'), escenario=escenario))
                self.assertIn('<strong>' + esperado + '</strong>', html)
