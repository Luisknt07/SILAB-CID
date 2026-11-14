"""Reporte con storage remoto y métricas agregadas, sin expedientes personales."""
from io import BytesIO
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import connections, router
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from PIL import Image as Imagen

from apps.centros_id.models import CentroID, Componente, Riesgo, Servicio, SolicitudCentro
from apps.centros_id.reportes import reporte_del_centro


class StorageSinPath(Storage):
    def __init__(self):
        imagen = BytesIO()
        Imagen.new('RGB', (32, 16), '#006633').save(imagen, format='PNG')
        self.contenido = imagen.getvalue()
        self.aperturas = 0

    def _open(self, name, mode='rb'):
        self.aperturas += 1
        return ContentFile(self.contenido, name=name)

    def path(self, name):
        raise AssertionError('Un storage remoto no tiene path local')


class ReportesEficientesTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Reporte público', slug='reporte-eficiente', proposito='Investigar')
        for numero in range(8):
            area = Componente.objects.create(centro=cls.centro, codigo=f'area-{numero}', nombre=f'Área {numero}')
            Servicio.objects.create(centro=cls.centro, componente=area, nombre=f'Servicio {numero}', activo=True)
        Riesgo.objects.create(centro=cls.centro, categoria='Operativo', riesgo='Riesgo', efecto='Demora', mitigacion='Control')
        usuario = get_user_model().objects.create_user('PERSONA_SECRETA')
        SolicitudCentro.objects.create(centro=cls.centro, usuario=usuario, titulo='DETALLE_PRIVADO',
            problema='NECESIDAD_PRIVADA', resultado_esperado='ENTREGABLE_PRIVADO')

    def test_reporte_abre_storage_y_solo_consulta_agregados_de_expedientes(self):
        storage = StorageSinPath()
        self.centro.imagen = 'centros_id/portadas/remota.png'
        self.centro.imagen.storage = storage
        identidad = (None, SimpleNamespace(nombre='Universidad de prueba', paleta={}))
        with patch('apps.centros_id.reportes.identidad_actual', return_value=identidad), \
                patch('apps.centros_id.reportes.logo_institucional', return_value=None):
            with CaptureQueriesContext(connections[router.db_for_read(CentroID)]) as consultas:
                respuesta = reporte_del_centro(self.centro)
        self.assertEqual(storage.aperturas, 1)
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        # PyMuPDF es una herramienta opcional de QA, no una dependencia del
        # servicio. Cuando está disponible también comprobar el PDF compuesto.
        if find_spec('fitz'):
            import fitz
            with fitz.open(stream=respuesta.content, filetype='pdf') as lector:
                self.assertTrue(any(pagina.get_images() for pagina in lector))
                texto = '\n'.join(p.get_text() for p in lector)
            self.assertIn('Solicitudes recibidas', texto)
            self.assertIn('Recibida', texto)
            for secreto in ('PERSONA_SECRETA', 'DETALLE_PRIVADO', 'NECESIDAD_PRIVADA', 'ENTREGABLE_PRIVADO'):
                self.assertNotIn(secreto, texto)
        sql = [q['sql'].lower() for q in consultas]
        expedientes = [q for q in sql if 'from "centros_id_solicitudcentro"' in q]
        self.assertEqual(len(expedientes), 1)
        self.assertIn('count(', expedientes[0])
        self.assertNotIn('"problema"', expedientes[0])
        self.assertNotIn('"usuario_id"', expedientes[0])
        # Ocho áreas no provocan ocho consultas de servicios.
        consultas_servicios = [q for q in sql if 'from "centros_id_servicio"' in q]
        self.assertEqual(len(consultas_servicios), 1)
