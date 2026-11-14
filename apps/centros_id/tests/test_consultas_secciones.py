"""Presupuestos de consultas para impedir que una sección cargue el centro entero."""
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import connections, router
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import CentroID, Servicio
from apps.centros_id.presentation.secciones import seccion_view
from apps.centros_id.presentation.views import CentrosIDView, _cifras_de_pestana


class ConsultasSeccionesTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Centro de consultas', slug='centro-consultas',
                                            proposito='Investigación aplicada', area='digitales')
        Servicio.objects.create(centro=cls.centro, nombre='Ensayo técnico', activo=True)

    def test_crear_contenidos_y_consultar_seccion_estatica_no_usa_sql(self):
        with self.assertNumQueries(0, using=router.db_for_read(CentroID)):
            c = Contenidos(self.centro, AnonymousUser())
            self.assertTrue(c.tiene('presentacion'))
            self.assertTrue(c.tiene('documentos'))
            self.assertFalse(c.tiene('clave-desconocida'))
            self.assertFalse(c.tiene('visitas'))

    def test_portafolio_consulta_servicios_una_vez_y_no_carga_otros_dominios(self):
        c = Contenidos(self.centro, AnonymousUser())
        with self.assertNumQueries(1, using=router.db_for_read(CentroID)):
            self.assertTrue(c.tiene('portafolio'))
            self.assertEqual([s.nombre for s in c.servicios], ['Ensayo técnico'])
        with self.assertNumQueries(0, using=router.db_for_read(CentroID)):
            self.assertTrue(c.tiene('portafolio'))
            self.assertEqual(len(c.servicios), 1)
        self.assertNotIn('proyectos', c.__dict__)
        self.assertNotIn('resultados', c.__dict__)
        self.assertNotIn('areas', c.__dict__)

    def test_cifras_de_una_pestana_no_materializan_otras(self):
        c = Contenidos(self.centro, AnonymousUser())
        _cifras_de_pestana(c, 'servicios')
        for nombre in ('proyectos', 'resultados', 'integrantes', 'zonas', 'areas', 'documentos'):
            with self.subTest(nombre=nombre):
                self.assertNotIn(nombre, c.__dict__)

    def test_carpetas_de_equipo_no_cargan_produccion_ni_equipamiento(self):
        c = Contenidos(self.centro, AnonymousUser())
        self.assertEqual(set(c.carpetas(solo_pestana='equipo')), {'equipo'})
        for nombre in ('proyectos', 'resultados', 'areas', 'zonas', 'documentos', 'servicios'):
            with self.subTest(nombre=nombre):
                self.assertNotIn(nombre, c.__dict__)

    def test_identidad_no_consulta_proyectos_resultados_ni_oferta_de_unidades(self):
        request = RequestFactory().get('/centros/centro-consultas/identidad/')
        request.user = AnonymousUser()
        with patch('apps.centros_id.presentation.secciones.render', side_effect=lambda _r, _t, c: c):
            with CaptureQueriesContext(connections[router.db_for_read(CentroID)]) as capturadas:
                contexto = seccion_view(request, self.centro.slug, 'identidad')
        self.assertEqual(contexto['centro'].pk, self.centro.pk)
        sql = ' '.join(q['sql'].lower() for q in capturadas)
        for tabla in ('centros_id_proyecto', 'centros_id_resultado', 'centros_id_equipocentro',
                      'webcitt_curso', 'webcitt_inscripcioncurso'):
            with self.subTest(tabla=tabla):
                self.assertNotIn(tabla, sql)
        self.assertLessEqual(len(capturadas), 8)

    def test_portada_de_varios_centros_usa_siete_consultas_sin_equipos_ni_proyectos(self):
        for numero in range(5):
            CentroID.objects.create(nombre=f'Centro {numero}', slug=f'centro-{numero}', proposito='Investigación')
        with CaptureQueriesContext(connections[router.db_for_read(CentroID)]) as capturadas:
            contexto = CentrosIDView().get_context_data()
        self.assertEqual(len(contexto['centros']), 6)
        self.assertEqual(len(capturadas), 7)
        sql = ' '.join(q['sql'].lower() for q in capturadas)
        for tabla in ('centros_id_proyecto', 'centros_id_resultado', 'centros_id_equipocentro'):
            self.assertNotIn(tabla, sql)

    def test_foto_del_catalogo_reutiliza_imagenes_precargadas(self):
        from apps.centros_id.presentation.views import _portada_de
        centro = CentroID.objects.prefetch_related('imagenes').get(pk=self.centro.pk)
        with self.assertNumQueries(0, using=router.db_for_read(CentroID)):
            self.assertEqual(_portada_de(centro), '')
