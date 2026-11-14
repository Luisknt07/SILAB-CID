"""El ensayo local identifica sus copias sin abrir conexiones operativas."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace

from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.core.presentation.ensayo_fablab import contexto_ensayo_fablab
from config.ensayo_fablab import BASES_ENSAYO_FABLAB, bases_de_ensayo_fablab


class EntornoEnsayoFablabTests(SimpleTestCase):
    @override_settings(DEBUG=True, REVISION_TIPOLOGIAS_ACTIVA=True)
    def test_los_casos_parciales_no_ofrecen_el_escenario_perfecto_anterior(self):
        from apps.documentos.presentation.escenario_ideal_consulta import _manifiesto
        self.assertIsNone(_manifiesto('laboratorio-fabricacion-digital-prototipado', 2026, 'B'))

    def test_el_perfil_no_admite_produccion_ni_postgresql_remoto(self):
        bases = {'default': {'NAME': 'citt_db', 'HOST': 'localhost'}}
        with self.assertRaises(ImproperlyConfigured):
            bases_de_ensayo_fablab(bases, False)
        for host in ('', '0.0.0.0', 'postgres.example.invalid', '192.168.1.2'):
            with self.subTest(host=host), self.assertRaises(ImproperlyConfigured):
                bases_de_ensayo_fablab({'default': {'HOST': host}}, True)

    def test_ambos_alias_apuntan_a_copias_sin_modificar_el_perfil_comun(self):
        bases = {'default': {'NAME': 'citt_db', 'HOST': '127.0.0.1', 'USER': 'local',
                            'TEST': {'NAME': 'otra_base'}, 'OPTIONS': {'connect_timeout': 5}},
                 'centros': {'NAME': 'centros_operativo', 'HOST': 'remoto'}}
        original = deepcopy(bases)
        resultado = bases_de_ensayo_fablab(bases, True)
        self.assertEqual(bases, original)
        self.assertEqual({alias: datos['NAME'] for alias, datos in resultado.items()}, BASES_ENSAYO_FABLAB)
        self.assertEqual({datos['HOST'] for datos in resultado.values()}, {'127.0.0.1'})
        self.assertNotIn('TEST', resultado['default'])
        resultado['centros']['OPTIONS']['connect_timeout'] = 8
        self.assertEqual(resultado['default']['OPTIONS']['connect_timeout'], 5)

    def _bases(self):
        return {alias: {'NAME': nombre, 'HOST': 'localhost'} for alias, nombre in BASES_ENSAYO_FABLAB.items()}

    def test_el_fablab_original_no_se_identifica_como_un_caso_de_prueba(self):
        with override_settings(DEBUG=True, ENSAYO_FABLAB_ACTIVO=True, ESCENARIO_IDEAL_AISLADO=True,
                DATABASES=self._bases(), REVISION_TIPOLOGIAS_CASOS=(('fablab-prueba-reportes-2026b', 'FabLab (prueba)'),)):
            original = SimpleNamespace(resolver_match=SimpleNamespace(kwargs={
                'slug': 'laboratorio-fabricacion-digital-prototipado'}), GET={})
            self.assertEqual(contexto_ensayo_fablab(original), {})
            prueba = SimpleNamespace(resolver_match=SimpleNamespace(kwargs={
                'slug': 'fablab-prueba-reportes-2026b'}), GET={})
            self.assertTrue(contexto_ensayo_fablab(prueba)['ensayo_fablab'])

    def test_el_aviso_requiere_las_dos_copias_y_habilitacion_explicita(self):
        correcto = dict(DEBUG=True, ENSAYO_FABLAB_ACTIVO=True, ESCENARIO_IDEAL_AISLADO=True,
                        DATABASES=self._bases())
        for cambio in (dict(DEBUG=False), dict(ENSAYO_FABLAB_ACTIVO=False),
                       dict(ESCENARIO_IDEAL_AISLADO=False),
                       dict(DATABASES={'default': {'NAME': 'citt_db', 'HOST': 'localhost'}})):
            with self.subTest(cambio=cambio), override_settings(**(correcto | cambio)):
                self.assertEqual(contexto_ensayo_fablab(None), {})
        with override_settings(**correcto):
            self.assertEqual(contexto_ensayo_fablab(None)['ensayo_fablab']['fecha_corte'], timezone.localdate())

    def test_admin_reconoce_el_caso_por_id_y_no_etiqueta_el_original(self):
        with override_settings(DEBUG=True, ENSAYO_FABLAB_ACTIVO=True, ESCENARIO_IDEAL_AISLADO=True,
                DATABASES=self._bases(),
                REVISION_TIPOLOGIAS_CASOS=(('fablab-prueba-reportes-2026b', 'FabLab (prueba)'),),
                REVISION_TIPOLOGIAS_IDENTIFICADORES={'49': 'fablab-prueba-reportes-2026b'}):
            for identificador, es_caso in (('49', True), ('11', False), ('9999', False)):
                with self.subTest(identificador=identificador):
                    request = SimpleNamespace(resolver_match=SimpleNamespace(kwargs={}),
                                              GET={'unidad': identificador})
                    self.assertEqual(bool(contexto_ensayo_fablab(request)), es_caso)

    def test_el_aviso_no_identifica_una_copia_remota_como_local(self):
        bases = self._bases()
        bases['centros']['HOST'] = 'postgres.example.invalid'
        with override_settings(DEBUG=True, ENSAYO_FABLAB_ACTIVO=True, ESCENARIO_IDEAL_AISLADO=True,
                               DATABASES=bases):
            self.assertEqual(contexto_ensayo_fablab(None), {})

    def test_aviso_pequeno_compartido_solo_cuando_el_contexto_esta_activo(self):
        plantilla = 'portal/pages/unidades/gestion/includes/aviso_ensayo_fablab.html'
        self.assertNotIn('data-ensayo-fablab', render_to_string(plantilla, {}))
        contenido = render_to_string(plantilla, {'ensayo_fablab': {
            'periodo': '2026-B', 'fecha_corte': date(2026, 12, 9)}})
        self.assertIn('Revisión de casos parciales · 2026-B', contenido)
        self.assertIn('Fecha actual 09/12/2026 · registros identificados de prueba', contenido)
        self.assertNotIn('citt_db', contenido)
