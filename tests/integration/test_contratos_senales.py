"""Contratos revisados, registros unicos y limites entre unidades."""
from dataclasses import FrozenInstanceError, replace
from datetime import date
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import SimpleTestCase, TestCase

from apps.integraciones.auditoria_senales import (
    auditar_contratos_senales, conexiones_cuentas, conexiones_modelos, huella_revision,
)
from apps.integraciones.contratos_senales import CONTRATOS, registro_contratos
from apps.gestion_unidades.models.repositorio import ArtefactoExterno
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad


class ContratosSenalesTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.datos = auditar_contratos_senales()

    def test_codigo_y_conexiones_tienen_revision_completa(self):
        self.assertEqual(self.datos['hallazgos'], [])
        self.assertEqual(self.datos['resumen']['contratos'], 35)
        self.assertEqual(self.datos['resumen']['decoradores'], 35)
        self.assertEqual(self.datos['resumen']['conexiones_propias'], 35)
        self.assertTrue(all(c['registros_efectivos'] == 1 for c in self.datos['contratos']))

    def test_registro_y_efectos_inmutables(self):
        with self.assertRaises(FrozenInstanceError):
            CONTRATOS[0].fallo = 'ignorar'
        with self.assertRaises(TypeError):
            registro_contratos()[CONTRATOS[0].clave] = CONTRATOS[1]
        for cambios in ({'funcion': None}, {'modulo': '../fuera'}, {'escrituras': []},
                        {'propietario_actual': 'plantas_piloto'}, {'alias': 'arbitrario'},
                        {'sender': '*', 'modelo_sender': '*'}, {'modelo_sender': '*'}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                replace(CONTRATOS[0], **cambios)

    def test_no_acepta_duplicados_o_encadenamientos_ausentes(self):
        for contratos in ((), (CONTRATOS[0], CONTRATOS[0]),
                          (replace(CONTRATOS[0], encadenamientos=('ausente',)),)):
            with self.subTest(contratos=contratos), self.assertRaises(ValueError):
                registro_contratos(contratos)

    def test_importar_contratos_no_importa_django_o_modelos(self):
        codigo = "from apps.integraciones.contratos_senales import registro_contratos; import sys; assert len(registro_contratos()) == 35; assert 'django' not in sys.modules; assert 'apps.integraciones.modelos' not in sys.modules"
        resultado = subprocess.run([sys.executable, '-c', codigo], cwd=Path(__file__).resolve().parents[2],
                                   capture_output=True, text=True, timeout=20)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_ready_repetido_no_duplica_conexiones(self):
        config = apps.get_app_config('core')
        previas = conexiones_modelos() + conexiones_cuentas()
        config.ready()
        config.ready()
        self.assertEqual(conexiones_modelos() + conexiones_cuentas(), previas)

    def test_conexiones_de_cuentas_ausentes_o_duplicadas_generan_hallazgos(self):
        conexiones = conexiones_cuentas()
        self.assertEqual(len(conexiones), 2)
        for alteradas in (conexiones[1:], conexiones + [conexiones[0]]):
            with self.subTest(cantidad=len(alteradas)), patch(
                    'apps.integraciones.auditoria_senales.conexiones_cuentas', return_value=alteradas):
                datos = auditar_contratos_senales()
            self.assertIn('registro_ausente_o_duplicado', [h['tipo'] for h in datos['hallazgos']])

    def test_registro_de_cuentas_es_global_explicito_y_conserva_efectos(self):
        contratos = [c for c in CONTRATOS if c.senal in ('user_logged_in', 'email_confirmed')]
        self.assertEqual(len(contratos), 2)
        for contrato in contratos:
            self.assertEqual((contrato.sender, contrato.modelo_sender), ('*', '*'))
            self.assertEqual(contrato.fallo, 'propaga')
            self.assertIn('PagoInscripcion', contrato.escrituras)
            self.assertIn('correo verificado y univoco', contrato.condicion)
        nombre, sender, callback, asincrona = conexiones_cuentas()[0]
        with patch('apps.integraciones.auditoria_senales.conexiones_cuentas',
                   return_value=[(nombre, id(apps.get_model('auth.User')), callback, asincrona)]):
            datos = auditar_contratos_senales()
        self.assertIn('conexion_sin_contrato', [h['tipo'] for h in datos['hallazgos']])

    def test_receiver_propio_nuevo_sigue_exigiendo_contrato(self):
        from apps.integraciones.superficies import senales
        from django.conf import settings

        observadas = senales(Path(settings.BASE_DIR))
        nueva = {**observadas[0], 'funcion': 'sin_revision'}
        with patch('apps.integraciones.auditoria_senales.senales', return_value=[*observadas, nueva]):
            datos = auditar_contratos_senales()
        self.assertIn({'tipo': 'sin_contrato', 'archivo': nueva['archivo'], 'funcion': 'sin_revision'},
                      datos['hallazgos'])

    def test_conexiones_ausentes_o_duplicadas_generan_hallazgos(self):
        conexiones = conexiones_modelos()
        for alteradas in (conexiones[1:], conexiones + [conexiones[0]]):
            with self.subTest(cantidad=len(alteradas)), patch(
                    'apps.integraciones.auditoria_senales.conexiones_modelos', return_value=alteradas):
                datos = auditar_contratos_senales()
            self.assertIn('registro_ausente_o_duplicado', [h['tipo'] for h in datos['hallazgos']])

    def test_conexion_global_no_se_confunde_con_sender_revisado(self):
        from apps.core.models.usuarios_base import create_user_profile
        conexiones = conexiones_modelos() + [('post_save', id(None), create_user_profile, False)]
        with patch('apps.integraciones.auditoria_senales.conexiones_modelos', return_value=conexiones):
            datos = auditar_contratos_senales()
        self.assertIn('conexion_sin_contrato', [h['tipo'] for h in datos['hallazgos']])

    def test_no_ejecuta_receivers(self):
        from apps.integraciones import senales_unidades as signals
        from apps.formacion.presentation import matriculas_signals

        for funcion in (signals.crear_perfil_especializado_unidad,
                        matriculas_signals.vincular_correo_confirmado, matriculas_signals.vincular_al_ingresar):
            original = funcion.__code__
            try:
                funcion.__code__ = (lambda *a, **k: (_ for _ in ()).throw(AssertionError('Receiver ejecutado'))).__code__
                self.assertEqual(auditar_contratos_senales()['hallazgos'], [])
            finally:
                funcion.__code__ = original

    def test_cambio_de_codigo_exige_revision(self):
        from apps.integraciones.contratos_senales import HUELLAS_REVISION
        huellas = {**HUELLAS_REVISION, 'apps/integraciones/senales_unidades.py': '0' * 64}
        with patch('apps.integraciones.auditoria_senales.HUELLAS_REVISION', huellas):
            datos = auditar_contratos_senales()
        self.assertIn('codigo_pendiente_revision', [h['tipo'] for h in datos['hallazgos']])

    def test_archivo_de_receiver_nuevo_exige_su_propia_huella(self):
        from apps.integraciones.contratos_senales import HUELLAS_REVISION
        nombre = 'apps/core/models/usuarios_base.py'
        huellas = {archivo: sha for archivo, sha in HUELLAS_REVISION.items() if archivo != nombre}
        with patch('apps.integraciones.auditoria_senales.HUELLAS_REVISION', huellas):
            datos = auditar_contratos_senales()
        self.assertIn({'tipo': 'codigo_sin_revision', 'archivo': nombre}, datos['hallazgos'])

    def test_normaliza_finales_de_linea_sin_ocultar_cambios(self):
        self.assertEqual(huella_revision(b'a\r\nb\r\n'), huella_revision(b'a\nb\n'))
        self.assertNotEqual(huella_revision(b'a\nb\n'), huella_revision(b'a\nc\n'))

    def test_limites_y_encadenamiento_no_conceden_autoridad(self):
        contratos = {c.funcion: c for c in CONTRATOS}
        self.assertEqual(contratos['asignar_codigo_reserva'].fallo, 'registra_fallo_no_bloqueante')
        self.assertEqual(contratos['configurar_usuario_decanato'].encadenamientos,
                         ('create_user_profile', 'save_user_profile'))
        from apps.integraciones.propiedad_modelos import PAQUETES_PROPIETARIOS
        for contrato in CONTRATOS:
            paquete = PAQUETES_PROPIETARIOS.get(contrato.propietario_actual, 'apps.integraciones')
            self.assertTrue(contrato.modulo.startswith(paquete + '.'))

    def test_cli_estricto_resumen_y_error_sin_detalles(self):
        salida = StringIO()
        call_command('auditar_contratos_senales', resumen=True, estricto=True, stdout=salida)
        self.assertEqual(json.loads(salida.getvalue())['resumen']['hallazgos'], 0)
        with patch('apps.integraciones.management.commands.auditar_contratos_senales.auditar_contratos_senales',
                   return_value={**self.datos, 'hallazgos': [{'tipo': 'pendiente'}]}):
            with self.assertRaises(CommandError):
                call_command('auditar_contratos_senales', estricto=True, stdout=StringIO())
        with patch('apps.integraciones.management.commands.auditar_contratos_senales.auditar_contratos_senales',
                   side_effect=OSError('dato_privado')):
            with self.assertRaises(CommandError) as error:
                call_command('auditar_contratos_senales', stdout=StringIO())
        self.assertNotIn('dato_privado', str(error.exception))

    def test_codigo_reserva_error_se_registra_sin_bloquear(self):
        from apps.reservas.models.reservas import asignar_codigo_reserva
        instancia = Mock(codigo_reserva=None)
        with patch('apps.reservas.services.codigos_reserva.asegurar_codigo_reserva',
                   side_effect=RuntimeError('dato_privado')), self.assertLogs(
                       'apps.reservas.services.codigos_reserva', level='WARNING') as registro:
            asignar_codigo_reserva(None, instancia, False)
        self.assertIsNone(instancia.codigo_reserva)
        self.assertNotIn('dato_privado', str(registro.output))


class BloqueoSQLContratosTests(TestCase):
    def test_sql_accidental_se_rechaza_y_limpia_contexto(self):
        def consultar():
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')

        previos = list(connection.execute_wrappers)
        with patch('apps.integraciones.auditoria_senales.conexiones_modelos', consultar):
            with self.assertRaisesMessage(ValueError, 'no permite consultas'):
                auditar_contratos_senales()
        self.assertEqual(connection.execute_wrappers, previos)


class VinculosArchivosUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = Unidad.objects.create(nombre='Contrato A', slug='contrato-a',
                                      fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')
        cls.b = Unidad.objects.create(nombre='Contrato B', slug='contrato-b',
                                      fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')
        cls.ra = Recurso.objects.create(nombre='Archivo A', unidad=cls.a)
        cls.rb = Recurso.objects.create(nombre='Archivo B', unidad=cls.b)
        datos = dict(descripcion='Contrato de prueba', tipo='otro', software_requerido='Ninguno',
                     licencia_software='libre', requisitos_tecnicos='Prueba', instrucciones_uso='Prueba',
                     que_representa='Prueba', supuestos_simplificaciones='Prueba', limitaciones_conocidas='Prueba',
                     autor='Prueba', licencia_uso='Prueba')
        cls.aa = ArtefactoExterno.objects.create(codigo='AAA-SIM-UNO', nombre='Artefacto A', unidad=cls.a, **datos)
        cls.ab = ArtefactoExterno.objects.create(codigo='BBB-SIM-UNO', nombre='Artefacto B', unidad=cls.b, **datos)

    def test_directo_rechaza_lote_mixto_sin_vinculos_parciales(self):
        with self.assertRaises(ValidationError), transaction.atomic():
            self.aa.archivos.add(self.ra, self.rb)
        self.assertFalse(self.aa.archivos.exists())

    def test_inverso_rechaza_lote_mixto_sin_vinculos_parciales(self):
        with self.assertRaises(ValidationError), transaction.atomic():
            self.ra.artefactos_externos.add(self.aa, self.ab)
        self.assertFalse(self.ra.artefactos_externos.exists())

    def test_ambos_sentidos_permiten_misma_unidad_y_repeticion(self):
        self.aa.archivos.add(self.ra)
        self.ra.artefactos_externos.add(self.aa)
        self.assertEqual(self.aa.archivos.count(), 1)
        self.rb.artefactos_externos.add(self.ab)
        self.assertEqual(self.ab.archivos.count(), 1)

    def test_inverso_set_rechazado_preserva_relacion_previa(self):
        self.aa.archivos.add(self.ra)
        with self.assertRaises(ValidationError), transaction.atomic():
            self.ra.artefactos_externos.set([self.ab])
        self.assertEqual(list(self.ra.artefactos_externos.all()), [self.aa])

    def test_validacion_usa_alias_de_la_operacion(self):
        from apps.integraciones.senales_unidades import validar_archivos_del_artefacto
        with patch.object(ArtefactoExterno.objects, 'using') as usar:
            usar.return_value.filter.return_value.exclude.return_value.exists.return_value = False
            validar_archivos_del_artefacto(None, self.ra, 'pre_add', {self.aa.pk}, True, using='alias_revision')
        usar.assert_called_once_with('alias_revision')
