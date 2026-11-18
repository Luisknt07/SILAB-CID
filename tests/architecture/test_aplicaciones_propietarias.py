"""La separación es verificable en el registro y en el código que se ejecuta."""
import ast
from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.test import SimpleTestCase

from apps.integraciones.propiedad_modelos import PAQUETES_PROPIETARIOS, PROPIETARIOS_MODELOS
from config.rutas_operativas import PROVEEDORES
from config.modulos import registro_de_despliegue


class AplicacionesPropietariasTests(SimpleTestCase):
    def test_codigo_no_importa_el_paquete_retirado(self):
        raiz = Path(settings.BASE_DIR)
        infracciones = []
        for carpeta in ('apps', 'config', 'scripts'):
            for path in (raiz / carpeta).rglob('*.py'):
                tree = ast.parse(path.read_text(encoding='utf-8-sig'))
                for node in ast.walk(tree):
                    referencias = []
                    if isinstance(node, ast.ImportFrom) and not node.level:
                        referencias.append(node.module or '')
                    elif isinstance(node, ast.Import):
                        referencias.extend(alias.name for alias in node.names)
                    if any(name == 'webcitt' or name.startswith('webcitt.') for name in referencias):
                        infracciones.append((path.relative_to(raiz).as_posix(), node.lineno))
        self.assertEqual(infracciones, [])

    def test_historial_no_es_contenedor_de_negocio(self):
        self.assertFalse((Path(settings.BASE_DIR) / 'webcitt').exists())
        historial = apps.get_app_config('webcitt')
        self.assertEqual(historial.name, 'apps.historial_modelos')
        self.assertEqual(list(historial.get_models()), [])
        self.assertEqual(len(PROPIETARIOS_MODELOS), 182)

    def test_modelos_y_administradores_residen_en_sus_propietarios(self):
        registro = registro_de_despliegue()
        for nombre, label in PROPIETARIOS_MODELOS.items():
            modelo = apps.get_model(label, nombre)
            paquete = PAQUETES_PROPIETARIOS[label]
            with self.subTest(modelo=modelo._meta.label):
                self.assertEqual(apps.get_app_config(label).name, paquete)
                manifiesto = registro.manifiestos[label]
                self.assertEqual(manifiesto.app_django, paquete)
                self.assertIn(paquete + '.admin', manifiesto.administracion)
                self.assertIn(paquete + '.presentation.operativas_urls', manifiesto.rutas)
                self.assertTrue(modelo.__module__.startswith(paquete + '.models.'))
                self.assertEqual(modelo._meta.proxy, nombre in {'ReporteOperativoUnidad', 'Adjunto'})
                if modelo in admin.site._registry:
                    panel = admin.site._registry[modelo]
                    self.assertTrue(type(panel).__module__.startswith(paquete + '.admin.'))

    def test_rutas_diferidas_son_del_proveedor_y_no_importan_controladores(self):
        prioridades = []
        for proveedor in PROVEEDORES:
            paquete = proveedor.rsplit('.presentation.', 1)[0]
            for ruta in import_module(proveedor).urlpatterns:
                with self.subTest(proveedor=proveedor, nombre=ruta.name):
                    self.assertTrue(ruta.callback.ruta_diferida.startswith(paquete + '.'))
                    prioridades.append(ruta.prioridad_proyecto)
        self.assertEqual(len(prioridades), 277)
        self.assertEqual(len(prioridades), len(set(prioridades)))
