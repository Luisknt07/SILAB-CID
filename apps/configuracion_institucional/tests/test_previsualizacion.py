"""El editor conserva archivos e historial y ofrece vista previa sin publicar."""
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ..imagenes import CAMPOS_IMAGENES
from ..models import RevisionPresentacion
from ..services import guardar_borrador, publicar_revision
from .test_imagenes import imagen


class PrevisualizacionLogoTests(TestCase):
    def setUp(self):
        (Path(settings.BASE_DIR) / 'var' / 'tmp').mkdir(parents=True, exist_ok=True)
        directorio = TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'var' / 'tmp')
        self.addCleanup(directorio.cleanup)
        configuracion = override_settings(INSTITUTION_LOGO_ROOT=directorio.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.autor = get_user_model().objects.create_superuser('previsualizacion.qa')
        self.client.force_login(self.autor)
        self.url = reverse('admin:configuracion_institucional_revisionpresentacion_add')
        self.datos = dict(nombre_producto='Sistema QA', nombre_corto_producto='QA',
                          nombre_institucion='Institucion QA', logo='', logo_secundario='')

    def test_editor_vacio_no_guarda_y_carga_recursos_una_vez(self):
        contenido = self.client.get(self.url).content.decode()
        self.assertEqual(contenido.count('data-logo-editor'), 5)
        self.assertEqual(contenido.count('type="file"'), 5)
        self.assertEqual(contenido.count('logos_editor.js?'), 1)
        self.assertEqual(contenido.count('logos_editor.css?'), 1)
        self.assertEqual(RevisionPresentacion.objects.count(), 0)

    def test_imagenes_heredadas_visibles_sin_javascript_y_retiro_conserva_historial(self):
        borrador = guardar_borrador(RevisionPresentacion(**self.datos,
            **{campo: imagen() for campo in CAMPOS_IMAGENES}), self.autor)
        publicada = publicar_revision(borrador.pk, self.autor, base_esperada=None)
        contenido = self.client.get(self.url).content.decode()
        for campo in CAMPOS_IMAGENES:
            fuente = getattr(publicada, campo).url
            self.assertEqual(len(re.findall(
                rf'<img[^>]*src="{re.escape(fuente)}"[^>]*data-logo-image', contenido)), 2)
            self.assertIn(f'data-logo-original="{fuente}"', contenido)
        respuesta = self.client.post(self.url, {**self.datos,
            'fuente_imagenes': publicada.pk, 'logo_claro-clear': 'on'})
        self.assertEqual(respuesta.status_code, 302)
        nueva = RevisionPresentacion.objects.first()
        self.assertFalse(nueva.logo_claro)
        self.assertEqual(nueva.logo_oscuro.name, publicada.logo_oscuro.name)
        publicada.refresh_from_db()
        self.assertTrue(Path(publicada.logo_claro.path).is_file())
