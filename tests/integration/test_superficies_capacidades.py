"""Inventario sin SQL, sin operaciones y sin atribuciones automaticas de autoridad."""
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import RequestFactory, SimpleTestCase, TestCase

from apps.integraciones.superficies import analizar_python, archivo_local, inventario_superficies, senales
from apps.core.admin.site import _lista_aplicaciones_agrupada


class SuperficiesTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.datos = inventario_superficies()

    def test_inventario_serializable_sin_datos_o_permisos_efectivos(self):
        texto = json.dumps(self.datos)
        self.assertTrue(self.datos['no_consulta_datos'])
        self.assertTrue(self.datos['no_concede_permisos'])
        self.assertEqual(self.datos['alcance'], 'codigo_declarado_no_autorizacion_efectiva')
        self.assertNotIn(str(settings.BASE_DIR), texto)
        self.assertNotIn(settings.SECRET_KEY, texto)
        self.assertEqual(self.datos['resumen']['modulos_seleccionados'], 21)

    def test_seleccion_vertical_no_oculta_operacion_compartida(self):
        datos = inventario_superficies(('observatorios',))
        self.assertEqual(datos['seleccion_modulos'], ['observatorios'])
        self.assertEqual(datos['superficies_compartidas'], self.datos['superficies_compartidas'])
        self.assertEqual(datos['modulos'][0]['operacion_por_tipo'], 'aplicacion_propietaria_y_capacidades_compartidas')

    def test_politica_registrada_no_es_habilitacion_efectiva(self):
        registradas = [(m['identificador'], c['identificador'])
                       for m in self.datos['modulos'] for c in m['capacidades']
                       if c['registrada_en_politica']]
        self.assertEqual(
            registradas,
            [
                ('portal', 'portada_inicio'),
                ('reservas', 'reservas_operativas'),
            ],
        )
        for modulo in self.datos['modulos']:
            self.assertEqual(modulo['asignacion_ruta_a_capacidad'], 'requiere_revision_manual')

    def test_otras_secciones_portal_y_centros_tienen_entradas(self):
        modulos = {m['identificador']: m for m in self.datos['modulos']}
        self.assertEqual(len(modulos['portal']['rutas_propias']), 6)
        self.assertTrue(modulos['centros_id']['rutas_propias'])

    def test_centros_id_es_dueno_de_su_registro_y_no_de_unidades(self):
        """Un Centro I+D no se agenda ni presta equipos: tabla y permisos propios.

        La vertical dejo de ser solo una portada cuando recibio su registro;
        lo que no puede es apropiarse de la unidad heredada.
        """
        modulos = {m['identificador']: m for m in self.datos['modulos']}
        modelos = {m['modelo']: m for m in modulos['centros_id']['modelos']}
        self.assertTrue({'centros_id.CentroID', 'centros_id.Componente', 'centros_id.Servicio',
                         'centros_id.SolicitudCentro'} <= set(modelos))
        for modelo in modelos.values():
            self.assertEqual(modelo['propietario_actual'], 'apps.centros_id')
            self.assertNotIn('webcitt_unidad', modelo['tabla'])
        propio = modelos['centros_id.CentroID']
        self.assertEqual(propio['propietario_actual'], 'apps.centros_id')
        self.assertTrue(propio['admin_registrado'])
        self.assertEqual(sorted(propio['permisos_declarados']), [
            'centros_id.add_centroid', 'centros_id.change_centroid',
            'centros_id.delete_centroid', 'centros_id.view_centroid'])
        self.assertNotIn('webcitt_unidad', propio['tabla'])

    def test_senales_incluye_modelos_y_no_solo_signals(self):
        senales = self.datos['superficies_compartidas']['senales']
        archivos = {s['archivo'] for s in senales}
        self.assertTrue({'apps/integraciones/senales_unidades.py', 'apps/directorio_unidades/models/core.py',
                         'apps/reservas/models/reservas.py', 'apps/recursos/models/recursos.py',
                         'apps/core/models/usuarios.py'} <= archivos)
        self.assertEqual(len(senales), len({(s['archivo'], s['linea'], str(s['senal'])) for s in senales}))
        self.assertTrue(all(len(s['sha256']) == 64 for s in senales))

    def test_senales_poda_entornos_antes_de_leer_y_conserva_codigo_propio(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            codigo = '@receiver(post_save, sender=Unidad)\ndef recibir(sender, **kwargs): pass\n'
            propia = raiz / 'apps/ejemplo/senales.py'
            propia.parent.mkdir(parents=True)
            propia.write_text(codigo, encoding='utf-8')
            for carpeta in ('.qa/venv/Lib/site-packages', '.venv', 'venv', 'site-packages'):
                externa = raiz / 'apps/ejemplo/management/kit' / carpeta / 'tercero.py'
                externa.parent.mkdir(parents=True, exist_ok=True)
                externa.write_text('sintaxis invalida: [', encoding='utf-8')
            with patch('apps.integraciones.superficies.analizar_python', wraps=analizar_python) as analizar:
                encontradas = senales(raiz)
            self.assertEqual(analizar.call_count, 1)
            self.assertEqual([s['archivo'] for s in encontradas], ['apps/ejemplo/senales.py'])
            propia.write_text(codigo + '# Cambio que requiere revision\n', encoding='utf-8')
            self.assertNotEqual(encontradas[0]['sha256'], senales(raiz)[0]['sha256'])

    def test_tareas_operativas_se_conservan_como_compartidas(self):
        compartidas = self.datos['superficies_compartidas']
        comandos = {c['nombre'] for c in compartidas['comandos']}
        self.assertIn('procesar_recordatorios_reservas', comandos)
        self.assertIn('sincronizar_planificaciones_reservas', comandos)
        scheduler = next(s for s in compartidas['scripts'] if s['archivo'] == 'scripts/docker_scheduler.sh')
        self.assertIn('procesar_recordatorios_reservas', scheduler['referencias_comandos'])
        self.assertTrue(scheduler['autoridad_requiere_revision'])

    def test_acciones_callable_no_se_ejecutan_y_se_serializan(self):
        llamadas = []

        def accion(modeladmin, request, queryset):
            llamadas.append(True)

        administrador = next(a for m, a in admin.site._registry.items() if m._meta.app_label == 'reservas')
        with patch.object(administrador, 'actions', [accion]):
            datos = inventario_superficies()
        acciones = [a for m in datos['superficies_compartidas']['administracion']
                    for a in (m['acciones_declaradas'] or []) if isinstance(a, dict)]
        self.assertIn('accion', [a['nombre'] for a in acciones])
        self.assertFalse(llamadas)
        json.dumps(datos)

    def test_acciones_globales_no_desaparecen_con_actions_vacio(self):
        self.assertIn('delete_selected', [a['nombre'] for a in
                      self.datos['superficies_compartidas']['acciones_globales_admin']])

    def test_cli_resumen_y_seleccion(self):
        salida = StringIO()
        call_command('auditar_superficies_capacidades', modulo=['observatorios'], resumen=True, stdout=salida)
        datos = json.loads(salida.getvalue())
        self.assertNotIn('superficies_compartidas', datos)
        self.assertEqual(datos['seleccion_modulos'], ['observatorios'])
        self.assertEqual(datos['resumen']['rutas_heredadas'], self.datos['resumen']['rutas_heredadas'])

    def test_cli_rechaza_seleccion_invalida_sin_filtrar_detalle(self):
        for seleccion in ([], ['no_registrado']):
            with self.subTest(seleccion=seleccion), self.assertRaises(CommandError) as error:
                call_command('auditar_superficies_capacidades', modulo=seleccion, stdout=StringIO())
            self.assertNotIn('no_registrado', str(error.exception))

    def test_no_acepta_fuentes_fuera_del_proyecto(self):
        raiz = Path(settings.BASE_DIR)
        self.assertIsNone(archivo_local(raiz.parent / 'ajeno.py', raiz))
        self.assertEqual(archivo_local(raiz / 'apps/core/manifiesto.py', raiz), 'apps/core/manifiesto.py')

    def test_controles_y_auditoria_en_configuracion_institucional(self):
        # El agrupador no altera permisos: recibe exclusivamente modelos ya visibles.
        class Sitio:
            def _citt_original_get_app_list(self, request, app_label):
                return [{'app_label': 'configuracion_institucional', 'models': [
                    {'object_name': nombre, 'name': nombre} for nombre in ('EstadoCapacidad', 'CambioCapacidad')]}]

        peticion = RequestFactory().get('/admin/')
        peticion.user = SimpleNamespace(is_active=True, is_staff=True,
                                       is_superuser=True, has_perm=lambda *permiso: True)
        grupos = _lista_aplicaciones_agrupada(Sitio(), peticion)
        # Los dos modelos quedan en «Institución» y en ningún otro grupo (el de reportes es propio del superusuario).
        con_modelos = {g['slug']: [m['object_name'] for m in g['models']] for g in grupos
                       if any(m.get('object_name') in ('EstadoCapacidad', 'CambioCapacidad') for m in g['models'])}
        self.assertEqual(con_modelos, {'institucion': ['EstadoCapacidad', 'CambioCapacidad']})


class BloqueoSQLInventarioTests(TestCase):
    def test_sql_accidental_se_deniega_y_wrapper_se_retira(self):
        def consulta(seleccion):
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')

        previos = list(connection.execute_wrappers)
        with patch('apps.integraciones.superficies._inventario_superficies', consulta):
            with self.assertRaisesMessage(ValueError, 'no permite consultas'):
                inventario_superficies()
        self.assertEqual(connection.execute_wrappers, previos)
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            self.assertEqual(cursor.fetchone(), (1,))

    def test_wrapper_se_retira_al_terminar_correctamente(self):
        previos = list(connection.execute_wrappers)
        inventario_superficies(('centros_id',))
        self.assertEqual(connection.execute_wrappers, previos)
