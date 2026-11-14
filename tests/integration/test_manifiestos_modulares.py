"""Metadatos seguros, limites reales del legado y diagnostico sin consultas."""
from dataclasses import FrozenInstanceError, replace
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.checks import modulos_configurados
from apps.core.modulos import ManifiestoModulo, RegistroModulos
from config.modulos import registro_de_despliegue


ROOT = Path(__file__).resolve().parents[2]


class ManifiestosModularesTests(SimpleTestCase):
    def manifiesto(self, identificador='ejemplo', **campos):
        return ManifiestoModulo(identificador, '1.0.0', f'apps.{identificador}', 'propio', **campos)

    def test_manifiesto_y_catalogo_no_permiten_editar_valores_publicos(self):
        manifiesto = self.manifiesto()
        registro = RegistroModulos((manifiesto,))
        with self.assertRaises(FrozenInstanceError):
            manifiesto.version = '2.0.0'
        with self.assertRaises(TypeError):
            registro.manifiestos['otro'] = manifiesto

    def test_rechaza_formatos_mutables_y_referencias_fuera_del_propietario(self):
        base = self.manifiesto()
        for campos in (
            {'identificador': '../otro'}, {'version': 'latest'}, {'version_esquema': True},
            {'paquete': 'apps/ejemplo'}, {'etapa': 'terminado'},
            {'dependencias': ['core']}, {'dependencias': ('core', 'core')},
            {'dependencias': ('ejemplo',)},
            {'dependencias': ('core',), 'integraciones_opcionales': ('core',)},
            {'app_django': 'apps.otra'}, {'rutas': ('apps.otra.urls',)},
            {'rutas': ('apps.ejemplo.urls;ejecutar',)},
            {'migraciones': ('apps.ejemplo.migrations',)}, {'capacidades': ('url()',)},
        ):
            with self.subTest(campos=campos), self.assertRaises(ValueError):
                replace(base, **campos)

    def test_rechaza_registro_vacio_duplicados_y_paquetes_compartidos(self):
        primero = self.manifiesto()
        for manifiestos in ((), (object(),), (primero, primero),
                            (primero, replace(primero, identificador='otra'))):
            with self.subTest(manifiestos=manifiestos), self.assertRaises(ValueError):
                RegistroModulos(manifiestos)

    def test_rechaza_dependencia_ausente_y_ciclo_obligatorio(self):
        with self.assertRaises(ValueError):
            RegistroModulos((self.manifiesto(dependencias=('ausente',)),))
        with self.assertRaises(ValueError):
            RegistroModulos((self.manifiesto('uno', dependencias=('dos',)),
                             self.manifiesto('dos', dependencias=('uno',))))

    def test_plan_estable_resuelve_dependencias_sin_incluir_opcionales(self):
        modulos = (self.manifiesto('base', integraciones_opcionales=('vertical', 'ausente')),
                   self.manifiesto('vertical', dependencias=('base',)), self.manifiesto('otra'))
        registro = RegistroModulos(modulos)
        self.assertEqual(registro.plan(('vertical', 'vertical')), ('base', 'vertical'))
        self.assertEqual(registro.plan(('base',)), ('base',))
        self.assertEqual(registro.plan(('otra', 'vertical')), registro.plan(('vertical', 'otra')))
        self.assertEqual(registro.plan(('vertical',)), RegistroModulos(reversed(modulos)).plan(('vertical',)))

    def test_no_acepta_selecciones_desconocidas_o_strings_como_lista(self):
        registro = RegistroModulos((self.manifiesto(),))
        for seleccion in ((), [], 'ejemplo', ('no_registrado',), (None,)):
            with self.subTest(seleccion=seleccion), self.assertRaises(ValueError):
                registro.plan(seleccion)

    def test_centros_id_y_portal_no_exigen_verticales_ni_legado_en_el_plan(self):
        registro = registro_de_despliegue()
        self.assertEqual(registro.plan(('centros_id',)), ('core', 'centros_id'))
        self.assertEqual(registro.plan(('portal',)), ('core', 'portal'))
        self.assertEqual(
            registro.manifiestos['centros_id'].app_django,
            'apps.centros_id',
        )
        # Administra su propio registro sin que el plan arrastre el directorio, que es una integración opcional.
        self.assertEqual(registro.manifiestos['centros_id'].administracion, ('apps.centros_id.admin',))

    def test_cuatro_verticales_declaran_legado_sin_exigirse_entre_si(self):
        registro = registro_de_despliegue()
        verticales = {'laboratorios', 'plantas_piloto', 'observatorios', 'centros_experimentales'}
        for identificador in verticales:
            with self.subTest(identificador=identificador):
                plan = registro.plan((identificador,))
                self.assertIn('gestion_unidades', plan)
                self.assertNotIn('legado_webcitt', plan)
                self.assertIn('integraciones', plan)
                self.assertEqual(set(plan) & verticales, {identificador})
                self.assertEqual(
                    registro.manifiestos[identificador].app_django,
                    f'apps.{identificador}',
                )

    def test_puntos_de_entrada_declarados_existen_sin_importarlos(self):
        registro = registro_de_despliegue()
        self.assertEqual(len(registro.manifiestos), 21)
        for manifiesto in registro.manifiestos.values():
            for campo in ('paquete', 'rutas', 'administracion', 'migraciones', 'comandos', 'tareas', 'salud'):
                valores = (manifiesto.paquete,) if campo == 'paquete' else getattr(manifiesto, campo)
                for valor in valores:
                    ruta = ROOT.joinpath(*valor.split('.'))
                    with self.subTest(punto=valor):
                        self.assertTrue(ruta.with_suffix('.py').is_file() or (ruta / '__init__.py').is_file())

    def test_registro_carga_sin_django_setup_orm_o_controladores(self):
        codigo = '''
import importlib.abc
import sys
class Bloqueo(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'django' or '.models' in fullname or '.presentation' in fullname or '.admin' in fullname:
            raise ImportError('Punto de entrada cargado durante registro: ' + fullname)
sys.meta_path.insert(0, Bloqueo())
from config.modulos import registro_de_despliegue
registro = registro_de_despliegue()
assert len(registro.manifiestos) == 21
assert 'gestion_unidades' in registro.plan(('laboratorios',))
assert 'django' not in sys.modules
'''
        resultado = subprocess.run([sys.executable, '-c', codigo], cwd=ROOT,
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_check_verifica_apps_resueltas_y_detecta_app_ausente(self):
        self.assertEqual(modulos_configurados(None), [])
        instaladas = [c for c in apps.get_app_configs() if c.name != 'apps.portal']
        with patch('apps.core.checks.apps.get_app_configs', return_value=instaladas):
            self.assertEqual([e.id for e in modulos_configurados(None)], ['slcid.E011'])

    def test_check_rechaza_registro_invalido_sin_filtrar_detalles(self):
        with patch('config.modulos.registro_de_despliegue', side_effect=ValueError('detalle interno')):
            errores = modulos_configurados(None)
            self.assertEqual([e.id for e in errores], ['slcid.E011'])
            self.assertNotIn('detalle interno', errores[0].msg)

    def test_auditoria_no_consulta_base_ni_expone_configuracion_o_autoriza(self):
        salida = StringIO()
        call_command('auditar_modulos', modulo=['laboratorios'], stdout=salida)
        datos = json.loads(salida.getvalue())
        self.assertEqual(datos['alcance'], 'metadatos_de_despliegue_no_autorizacion')
        self.assertEqual(datos['plan_dependencias'],
                         list(registro_de_despliegue().plan(('laboratorios',))))
        self.assertEqual(datos['modulos'][-1]['identificador'], 'laboratorios')
        for campo in ('habilitado', 'autorizado', 'salud_ok', 'secret_key', 'db_password', 'usuarios'):
            self.assertNotIn(campo, salida.getvalue().lower())
        with self.assertRaises(CommandError):
            call_command('auditar_modulos', modulo=['inexistente'], stdout=StringIO())
