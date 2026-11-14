"""Contrato de acceso del recurso nativo: aislamiento, visibilidad y cero escrituras."""
from datetime import date
from unittest.mock import patch

from django.db import connection
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import path

from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA, juego_cerveza_logistica_view
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.directorio_unidades.models.core import Unidad

urlpatterns = [
    path('laboratorio/<slug:slug>/logistica/juego-cerveza/', juego_cerveza_logistica_view),
    path('laboratorio/<slug:slug>/', lambda request, slug: HttpResponse('Ficha'), name='laboratorio_detalle'),
]


@override_settings(ROOT_URLCONF=__name__)
class JuegoCervezaLogisticaViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Logística, Transporte y Cadena de Suministro',
            slug=SLUG_LOGISTICA, dependencia='laboratorios', descripcion='Laboratorio docente',
            fecha_inicio=date(2026, 1, 1), activo=True,
        )

    def url(self, slug=SLUG_LOGISTICA):
        return f'/laboratorio/{slug}/logistica/juego-cerveza/'

    def test_recurso_publico_sin_datos_personales_ni_servicios_remotos(self):
        response = self.client.get(self.url())
        self.assertContains(response, 'Una decisión local.')
        self.assertContains(response, 'logistica_cerveza_motor.js')
        self.assertContains(response, 'Datos sintéticos')
        self.assertContains(response, 'Reproducir JSON')
        self.assertContains(response, 'systemdynamics.org')
        self.assertNotContains(response, 'cdnjs.cloudflare')
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_no_hay_mutaciones_ni_consultas_de_equipos_reservas_cursos_o_usuarios(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        for query in queries:
            sql = query['sql'].upper()
            self.assertFalse(any(operation in sql for operation in ('INSERT INTO', 'UPDATE ', 'DELETE FROM')))
            self.assertFalse(any(table in sql for table in ('WEBCITT_RESERVA', 'WEBCITT_CURSO', 'AUTH_USER', 'WEBCITT_EQUIPO')))
        self.assertLessEqual(len(queries), 7)

    def test_no_se_abre_en_otra_unidad_aunque_tenga_nombre_parecido(self):
        Unidad.objects.create(nombre='Otro laboratorio de logística', slug='otra-logistica',
                              dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.assertEqual(self.client.get(self.url('otra-logistica')).status_code, 404)

    def test_unidad_inactiva_no_expone_el_recurso(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_una_dependencia_incorrecta_no_expone_el_recurso(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(dependencia='observatorios')
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_respeta_pestana_desactivada(self):
        self.unidad.modulos_contenido.filter(clave='docencia-capacitacion').update(activo=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_respeta_seccion_aprendizaje_oculta(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='4.4', oculta=True)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    @patch('apps.laboratorios.operacion.presentation.logistica_juego.tipologia_activa', return_value=False)
    def test_tipologia_desactivada_no_expone_el_recurso(self, tipologia):
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        tipologia.assert_called_once_with('laboratorios')

    def test_solo_permite_lectura(self):
        self.assertEqual(self.client.post(self.url(), {'order': 7}).status_code, 405)
        self.assertEqual(self.client.put(self.url(), '{}', content_type='application/json').status_code, 405)
