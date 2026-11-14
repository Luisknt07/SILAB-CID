"""La dependencia consulta la copia remitida, sin acceso a lecturas de trabajo."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.documentos.models.necesidades import RemisionNecesidades
from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.expediente import DocumentoExigido
from apps.documentos.presentation.necesidades_decanato_vistas import _acceso
from apps.documentos.presentation.necesidades_remision import remitir_necesidades
from tests.integration import test_necesidades_decanato as escenarios


class NecesidadesDecanatoVistasTests(TestCase):
    unidad = escenarios.NecesidadesDecanatoTests.unidad
    captura = escenarios.NecesidadesDecanatoTests.captura
    emitido = escenarios.NecesidadesDecanatoTests.emitido

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.director = usuarios.objects.create_superuser('director-vistas-necesidades', password=None)
        cls.receptor = usuarios.objects.create_user('receptor-vistas-necesidades', is_staff=True)
        cls.operador = usuarios.objects.create_user('operador-vistas-necesidades', is_staff=True)
        cls.dep = DependenciaAcademica.objects.create(nombre='Decanato de prueba', centro_costo='Agrupador confirmado')
        cls.dep.receptores.add(cls.receptor)
        cls.dep_ajena = DependenciaAcademica.objects.create(nombre='Otro centro de costo')
        cls.exigido, _ = DocumentoExigido.objects.get_or_create(codigo='PLAN-COMPRAS-ANUAL', defaults=dict(
            nombre='Necesidades anuales', carpeta='planeacion', periodicidad='anual',
            origen='ambos', fuente_reporte='compras', requiere_firma=True))

    def setUp(self):
        self.url = reverse('admin:reportes-necesidades-decanato')
        # La navegación global consulta el subsistema científico en otra BD.
        # Esta suite integra el expediente y su UI, sin abrir esa base ajena.
        menu_centros = patch('apps.centros_id.informes.puede_reportar_centros', return_value=False)
        menu_centros.start()
        self.addCleanup(menu_centros.stop)

    def remision(self, sufijo='vista', dependencia=None):
        if dependencia is not None:
            dependencia.receptores.add(self.operador)
        unidad = self.unidad(sufijo, dependencia)
        datos = self.captura(unidad, item='Necesidad archivada ' + sufijo, mes='9')
        datos['compras'][0]['clase_bien'] = 'software'
        self.emitido(unidad, datos)
        return remitir_necesidades(2026, dependencia or self.dep, self.director)

    def test_direccion_ve_lectura_actual_y_selecciona_dependencia_para_remitir(self):
        self.unidad('pendiente-vista')
        self.client.force_login(self.director)
        respuesta = self.client.get(self.url, {'ejercicio': 2027})
        self.assertContains(respuesta, 'Lectura actual de Dirección')
        self.assertContains(respuesta, 'Unidad pendiente-vista')
        self.assertContains(respuesta, 'Selecciona una dependencia para remitirle su informe.')
        self.assertContains(respuesta, 'Año de compras')
        self.assertContains(respuesta, 'Descargar Excel')
        self.assertIsNone(respuesta.context['remision'])

    def test_receptor_sin_remision_no_recibe_lectura_ni_exportacion_actual(self):
        self.remision('otra', self.dep_ajena)
        self.client.force_login(self.receptor)
        with patch('apps.documentos.presentation.necesidades_decanato_vistas.lectura_necesidades') as lectura:
            respuesta = self.client.get(self.url, {'ejercicio': 2027})
        lectura.assert_not_called()
        self.assertContains(respuesta, 'Sin informe remitido')
        self.assertNotContains(respuesta, 'Descargar Excel')
        self.assertNotContains(respuesta, self.dep_ajena.nombre)
        self.assertNotContains(respuesta, 'Necesidad archivada otra')
        self.assertIsNone(respuesta.context['lectura'])
        self.assertEqual(self.client.get(self.url, {'ejercicio': 2027, 'formato': 'pdf'}).status_code, 404)
        self.assertEqual(self.client.get(self.url, {'ejercicio': 2027, 'formato': 'xlsx'}).status_code, 404)

    def test_administrar_unidad_no_concede_acceso_y_cuenta_debe_seguir_activa(self):
        self.unidad('operador')
        self.client.force_login(self.operador)
        self.assertEqual(self.client.get(self.url, {'ejercicio': 2027}).status_code, 403)
        type(self.receptor).objects.filter(pk=self.receptor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            _acceso(self.receptor)

    def test_receptor_no_puede_remitir_ni_elegir_dependencia_ajena(self):
        self.client.force_login(self.receptor)
        respuesta = self.client.post(self.url, {'accion': 'remitir', 'ejercicio': 2027, 'dependencia': self.dep.pk})
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(RemisionNecesidades.objects.exists())
        self.assertEqual(self.client.get(self.url, {'ejercicio': 2027, 'dependencia': self.dep_ajena.pk}).status_code, 403)

    def test_direccion_remite_y_redirige_a_la_misma_copia_que_vera_decanato(self):
        unidad = self.unidad('remitir')
        self.emitido(unidad, self.captura(unidad))
        self.client.force_login(self.director)
        respuesta = self.client.post(self.url, {'accion': 'remitir', 'ejercicio': 2027, 'dependencia': self.dep.pk})
        remision = RemisionNecesidades.objects.get()
        self.assertRedirects(respuesta, f'{self.url}?ejercicio=2027&dependencia={self.dep.pk}&remision={remision.pk}')
        respuesta = self.client.get(respuesta.url)
        self.assertContains(respuesta, 'Copia remitida a ' + self.dep.nombre)
        self.assertContains(respuesta, 'Volver a la lectura actual')
        self.assertNotContains(respuesta, 'name="accion" value="remitir"')
        self.client.force_login(self.receptor)
        respuesta = self.client.get(self.url, {'ejercicio': 2027})
        self.assertEqual(respuesta.context['remision'].pk, remision.pk)
        self.assertNotContains(respuesta, 'Volver a la lectura actual')
        self.assertNotContains(respuesta, 'name="accion" value="remitir"')

    def test_receptor_ve_ultima_copia_y_puede_consultar_antecedente(self):
        anterior = self.remision('anterior')
        nueva_unidad = self.unidad('posterior')
        self.emitido(nueva_unidad, self.captura(nueva_unidad, sin_compras=True))
        posterior = remitir_necesidades(2026, self.dep, self.director)
        self.client.force_login(self.receptor)
        with patch('apps.documentos.presentation.necesidades_decanato_vistas.lectura_necesidades') as lectura:
            respuesta = self.client.get(self.url, {'ejercicio': 2027})
        lectura.assert_not_called()
        self.assertEqual(respuesta.context['remision'].pk, posterior.pk)
        self.assertContains(respuesta, 'Sin compras justificadas')
        self.assertContains(respuesta, 'Semestre 2')
        self.assertContains(respuesta, 'Septiembre')
        self.assertContains(respuesta, 'Software')
        self.assertContains(respuesta, 'Informes remitidos de 2027 (2)')
        respuesta = self.client.get(self.url, {'remision': anterior.pk})
        self.assertEqual(respuesta.context['remision'].pk, anterior.pk)
        self.assertEqual(respuesta.context['ejercicio'], 2027)
        self.assertNotContains(respuesta, 'Unidad posterior')

    def test_remision_ajena_y_filtros_incompatibles_no_exponen_copia(self):
        propia = self.remision()
        ajena = self.remision('ajena', self.dep_ajena)
        self.client.force_login(self.receptor)
        self.assertEqual(self.client.get(self.url, {'remision': ajena.pk}).status_code, 404)
        self.assertEqual(self.client.get(self.url, {'remision': propia.pk, 'ejercicio': 2028}).status_code, 404)
        self.client.force_login(self.director)
        self.assertEqual(self.client.get(self.url, {'remision': propia.pk, 'dependencia': self.dep_ajena.pk}).status_code, 404)

    def test_descargas_usan_exclusivamente_contenido_de_la_copia_visible(self):
        remision = self.remision()
        self.client.force_login(self.receptor)
        for formato, funcion in (('pdf', 'render_necesidades_pdf'), ('xlsx', 'render_necesidades_xlsx')):
            with (self.subTest(formato=formato),
                    patch('apps.documentos.presentation.necesidades_decanato_vistas.lectura_necesidades') as lectura,
                    patch('apps.documentos.presentation.necesidades_decanato_vistas.' + funcion, return_value=b'archivo probado') as render):
                respuesta = self.client.get(self.url, {'ejercicio': 2027, 'formato': formato})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.content, b'archivo probado')
            self.assertIn(f'necesidades-2027-centros-de-costo.{formato}', respuesta['Content-Disposition'])
            render.assert_called_once_with(remision.contenido)
            lectura.assert_not_called()
            self.assertIn('no-store', respuesta['Cache-Control'])

    def test_copia_con_integridad_invalida_no_se_descarga(self):
        remision = self.remision()
        self.client.force_login(self.receptor)
        with patch('apps.documentos.presentation.necesidades_decanato_vistas.contenido_remision', side_effect=ValidationError('Captura alterada.')):
            respuesta = self.client.get(self.url, {'remision': remision.pk})
            self.assertContains(respuesta, 'Captura alterada.')
            self.assertNotContains(respuesta, 'Descargar Excel')
            self.assertEqual(self.client.get(self.url, {'remision': remision.pk, 'formato': 'pdf'}).status_code, 404)

    def test_filtros_invalidos_y_remision_global_no_mutan_registros(self):
        self.client.force_login(self.director)
        for ejercicio in ('texto', '2020', '2101', '2027.0', '9' * 5000):
            self.assertEqual(self.client.get(self.url, {'ejercicio': ejercicio}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'ejercicio': 2027, 'formato': 'csv'}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {'ejercicio': 2027, 'accion': 'remitir'}).status_code, 400)
        self.assertFalse(RemisionNecesidades.objects.exists())
