"""Contrato de aislamiento de Centros I+D frente a las unidades heredadas."""
import ast
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase


class LimitesDominioCentrosTests(SimpleTestCase):
    def test_relaciones_operativas_permanecen_dentro_del_dominio(self):
        usuario = get_user_model()
        for modelo in apps.get_app_config('centros_id').get_models():
            for campo in (*modelo._meta.fields, *modelo._meta.many_to_many):
                relacionado = campo.related_model if campo.is_relation else None
                if relacionado is None or relacionado is usuario:
                    continue
                with self.subTest(modelo=modelo.__name__, campo=campo.name):
                    self.assertEqual(relacionado._meta.app_label, 'centros_id',
                                     'Integre otros dominios mediante contratos, sin compartir su operación.')

    def test_codigo_operativo_no_importa_modelos_ni_funciones_de_unidades(self):
        carpeta = Path(apps.get_app_config('centros_id').path)
        ajenos = ('webcitt', 'apps.laboratorios', 'apps.plantas_piloto',
                  'apps.centros_experimentales', 'apps.observatorios')
        for archivo in carpeta.rglob('*.py'):
            relativo = archivo.relative_to(carpeta)
            if relativo.parts[0] in ('migrations', 'tests'):
                continue
            tree = ast.parse(archivo.read_text(encoding='utf-8-sig'))
            for nodo in ast.walk(tree):
                nombres = ([alias.name for alias in nodo.names] if isinstance(nodo, ast.Import)
                           else [nodo.module or ''] if isinstance(nodo, ast.ImportFrom) and not nodo.level
                           else [])
                for nombre in nombres:
                    with self.subTest(archivo=str(relativo), linea=nodo.lineno):
                        self.assertFalse(any(nombre == prefijo or nombre.startswith(prefijo + '.')
                                             for prefijo in ajenos))
