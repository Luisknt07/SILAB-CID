"""Transferencia real PostgreSQL entre dos bases, sin mirrors ni datos reales."""
from contextlib import contextmanager
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.centros_id.management.commands.copiar_centros_id import (
    FUNCION_SELLO, TRIGGER_SELLO, estructura, resumen, sellar_origen, tablas_centros,
)
from apps.centros_id.models import CentroID, Componente, CuentaCentro, GestorCentro


@skipUnless(getattr(settings, 'CENTROS_DB_ENABLED', False) and 'centros' in settings.DATABASES,
            'Ejecutar con config.settings_testing_multibase para verificar dos bases reales.')
class TransferenciaCentrosTests(TransactionTestCase):
    databases = {'default', 'centros'} if 'centros' in settings.DATABASES else {'default'}

    def setUp(self):
        super().setUp()
        self.origen = connections['default']
        if self.origen.vendor != 'postgresql':
            self.skipTest('Requiere PostgreSQL.')
        # El router mantiene estas tablas fuera de default. El test representa
        # una instalación anterior al corte dentro de su base efímera.
        existentes = set(self.origen.introspection.table_names())
        self.tablas_creadas = set(tablas_centros()) - existentes
        with self.origen.schema_editor() as editor:
            for modelo in apps.get_app_config('centros_id').get_models():
                if modelo._meta.db_table in self.tablas_creadas:
                    editor.create_model(modelo)
        self.cuenta = CuentaCentro.objects.using('default').create(id=12001, username='copia.identidad',
            first_name='Identidad QA', email='identidad@example.test')
        self.centro = CentroID.objects.using('default').create(nombre='Centro QA de origen', slug='qa-copia', sigla='QA',
            responsable_id=self.cuenta.pk)
        self.gestor = GestorCentro.objects.using('default').create(id=9001, centro_id=self.centro.pk, cuenta_id=self.cuenta.pk)
        self.area = Componente.objects.using('default').create(centro_id=self.centro.pk, codigo='qa', nombre='Área QA')

    def tearDown(self):
        # Solo tablas creadas por esta prueba en una BD efímera. Nunca se
        # ejecuta este código contra la base operativa.
        with self.origen.cursor() as cursor:
            for tabla in sorted(self.tablas_creadas):
                cursor.execute(f'DROP TABLE IF EXISTS {self.origen.ops.quote_name(tabla)} CASCADE')
            cursor.execute(f'DROP FUNCTION IF EXISTS {self.origen.ops.quote_name(FUNCION_SELLO)}()')
        super().tearDown()

    def copiar(self, **opciones):
        salida = StringIO()
        call_command('copiar_centros_id', origen='default', destino='centros', stdout=salida, **opciones)
        return salida.getvalue()

    def test_copia_conserva_ids_relaciones_origen_y_secuencias(self):
        texto = self.copiar(copiar=True)
        self.assertIn('Copia confirmada', texto)
        self.assertEqual(CentroID.objects.using('centros').get().pk, self.centro.pk)
        area = Componente.objects.using('centros').select_related('centro').get()
        self.assertEqual(area.pk, self.area.pk)
        self.assertEqual(area.centro.slug, self.centro.slug)
        self.assertEqual(area.centro.responsable.get_full_name(), 'Identidad QA')
        self.assertEqual(list(area.centro.gestores.values_list('pk', flat=True)), [self.cuenta.pk])
        self.assertEqual(GestorCentro.objects.using('centros').get().pk, self.gestor.pk)
        self.assertTrue(CentroID.objects.using('default').filter(pk=self.centro.pk).exists())
        self.assertIn('Comparación correcta', self.copiar())
        siguiente = CentroID.objects.using('centros').create(nombre='Nuevo centro', slug='nuevo-qa', sigla='NQA')
        self.assertGreater(siguiente.pk, self.centro.pk)

    def test_no_sobrescribe_un_destino_con_datos(self):
        existente = CentroID.objects.using('centros').create(nombre='Existente', slug='existente-qa', sigla='EQA')
        with self.assertRaisesMessage(CommandError, 'contiene registros'):
            self.copiar(copiar=True)
        self.assertEqual(CentroID.objects.using('centros').get().pk, existente.pk)
        self.assertEqual(CentroID.objects.using('default').count(), 1)

    def test_detecta_diferencias_sin_mutar_ninguna_base(self):
        self.copiar(copiar=True)
        CentroID.objects.using('centros').filter(pk=self.centro.pk).update(nombre='Cambio QA')
        with self.assertRaisesMessage(CommandError, 'difiere'):
            self.copiar()
        self.assertEqual(CentroID.objects.using('default').get().nombre, 'Centro QA de origen')
        self.assertEqual(CentroID.objects.using('centros').get().nombre, 'Cambio QA')

    def test_rechaza_copiar_sobre_el_mismo_alias(self):
        with self.assertRaisesMessage(CommandError, 'diferentes'):
            call_command('copiar_centros_id', origen='default', destino='default', copiar=True)

    def test_incluye_escritura_confirmada_antes_del_bloqueo(self):
        # El ejecutor lee metadatos antes de LOCK TABLE. Un snapshot repetible
        # fijado en ese momento copiaría la versión anterior de esta fila.
        escrito = False

        def ejecutar(conexion):
            nonlocal escrito
            ejecutor = MigrationExecutor(conexion)
            if conexion is self.origen and not escrito:
                escritor = conexion.copy(alias='escritor_centros_qa')
                try:
                    with escritor.cursor() as cursor:
                        cursor.execute('UPDATE centros_id_centroid SET nombre=%s WHERE id=%s',
                                       ['Confirmado antes del bloqueo', self.centro.pk])
                    escrito = True
                finally:
                    escritor.close()
            return ejecutor

        with patch('apps.centros_id.management.commands.copiar_centros_id.MigrationExecutor', side_effect=ejecutar):
            self.copiar(copiar=True)
        self.assertTrue(escrito)
        self.assertEqual(CentroID.objects.using('centros').get().nombre, 'Confirmado antes del bloqueo')
        self.assertEqual(CentroID.objects.using('default').get().nombre, 'Confirmado antes del bloqueo')

    def test_fallo_de_digest_revierte_toda_la_copia(self):
        def discordante(conexion, tabla, columnas, primaria):
            resultado = resumen(conexion, tabla, columnas, primaria)
            if conexion.alias == 'centros' and tabla == CentroID._meta.db_table:
                resultado['filas'] += 1
            return resultado

        with patch('apps.centros_id.management.commands.copiar_centros_id.resumen', side_effect=discordante):
            with self.assertRaisesMessage(CommandError, 'difiere'):
                self.copiar(copiar=True)
        self.assertFalse(CentroID.objects.using('centros').exists())
        self.assertFalse(CuentaCentro.objects.using('centros').exists())
        self.assertFalse(GestorCentro.objects.using('centros').exists())
        self.assertTrue(CentroID.objects.using('default').filter(pk=self.centro.pk).exists())

    def test_restricciones_equivalentes_no_dependen_del_nombre(self):
        destino = connections['centros']
        tabla = Componente._meta.db_table
        with destino.cursor() as cursor:
            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f' ORDER BY conname LIMIT 1",
                [tabla],
            )
            nombre = cursor.fetchone()[0]
            nuevo = 'qa_fk_nombre_diferente'
            cursor.execute(f'ALTER TABLE {destino.ops.quote_name(tabla)} RENAME CONSTRAINT '
                           f'{destino.ops.quote_name(nombre)} TO {destino.ops.quote_name(nuevo)}')
        try:
            self.assertEqual(estructura(self.origen, [tabla]), estructura(destino, [tabla]))
            self.assertIn('Copia confirmada', self.copiar(copiar=True))
        finally:
            with destino.cursor() as cursor:
                cursor.execute(f'ALTER TABLE {destino.ops.quote_name(tabla)} RENAME CONSTRAINT '
                               f'{destino.ops.quote_name(nuevo)} TO {destino.ops.quote_name(nombre)}')

    def test_fk_eliminada_impide_copia_aunque_columnas_coincidan(self):
        destino = connections['centros']
        tabla = Componente._meta.db_table
        with destino.cursor() as cursor:
            cursor.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid=%s::regclass AND contype='f' ORDER BY conname LIMIT 1", [tabla],
            )
            nombre, definicion = cursor.fetchone()
            cursor.execute(f'ALTER TABLE {destino.ops.quote_name(tabla)} DROP CONSTRAINT {destino.ops.quote_name(nombre)}')
        try:
            with self.assertRaisesMessage(CommandError, 'esquemas'):
                self.copiar(copiar=True)
            self.assertFalse(CentroID.objects.using('centros').exists())
            self.assertTrue(CentroID.objects.using('default').filter(pk=self.centro.pk).exists())
        finally:
            with destino.cursor() as cursor:
                cursor.execute(f'ALTER TABLE {destino.ops.quote_name(tabla)} '
                               f'ADD CONSTRAINT {destino.ops.quote_name(nombre)} {definicion}')

    def test_sello_exige_copia_verificada(self):
        with self.assertRaisesMessage(CommandError, '--sellar-origen requiere --copiar'):
            self.copiar(sellar_origen=True)
        self.assertTrue(CentroID.objects.using('default').exists())
        self.assertFalse(CentroID.objects.using('centros').exists())

    def test_sello_conserva_lecturas_y_bloquea_cualquier_escritura_legacy(self):
        texto = self.copiar(copiar=True, sellar_origen=True)
        self.assertIn('Origen sellado', texto)
        self.assertIn('Comparación correcta', self.copiar())
        self.assertEqual(CentroID.objects.using('default').get().pk, self.centro.pk)
        with self.origen.cursor() as cursor:
            cursor.execute("SELECT count(*), bool_and(tgenabled='A') FROM pg_trigger "
                           "WHERE tgname=%s AND NOT tgisinternal", [TRIGGER_SELLO])
            cantidad, siempre = cursor.fetchone()
        self.assertEqual(cantidad, len(tablas_centros()))
        self.assertTrue(siempre)
        tabla = self.origen.ops.quote_name(CentroID._meta.db_table)
        # Un trigger por sentencia también impide cambios que afectarían cero
        # filas: no depende del estado o de datos concretos del origen.
        sentencias = [
            f'INSERT INTO {tabla} (nombre) SELECT nombre FROM {tabla} WHERE FALSE',
            f'UPDATE {tabla} SET nombre=nombre WHERE FALSE',
            f'DELETE FROM {tabla} WHERE FALSE',
            f'TRUNCATE {tabla} CASCADE',
        ]
        for sql in sentencias:
            with self.subTest(sentencia=sql.split()[0]):
                with self.assertRaisesMessage(DatabaseError, 'base independiente'):
                    with self.origen.cursor() as cursor:
                        cursor.execute(sql)
        CentroID.objects.using('centros').filter(pk=self.centro.pk).update(nombre='Alta en base independiente')
        self.assertEqual(CentroID.objects.using('centros').get().nombre, 'Alta en base independiente')
        self.assertEqual(CentroID.objects.using('default').get().nombre, 'Centro QA de origen')

    def test_fallo_del_sello_revierte_copia_y_ddl_de_origen(self):
        def sellar_y_fallar(conexion, tablas):
            sellar_origen(conexion, tablas)
            raise RuntimeError('Fallo simulado de QA')

        with patch('apps.centros_id.management.commands.copiar_centros_id.sellar_origen', side_effect=sellar_y_fallar):
            with self.assertRaisesMessage(CommandError, 'se revirtió (RuntimeError)'):
                self.copiar(copiar=True, sellar_origen=True)
        self.assertFalse(CentroID.objects.using('centros').exists())
        with self.origen.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM pg_trigger WHERE tgname=%s', [TRIGGER_SELLO])
            self.assertEqual(cursor.fetchone()[0], 0)
        self.assertEqual(CentroID.objects.using('default').filter(pk=self.centro.pk).update(nombre='Origen editable'), 1)

    def test_error_posterior_al_commit_destino_no_promete_rollback(self):
        atomic_original = transaction.atomic

        @contextmanager
        def atomic_con_fallo(*args, **kwargs):
            with atomic_original(*args, **kwargs):
                yield
            if kwargs.get('using') == 'default':
                raise DatabaseError('Fallo simulado de cierre del origen')

        with patch('apps.centros_id.management.commands.copiar_centros_id.transaction.atomic', side_effect=atomic_con_fallo):
            with self.assertRaisesMessage(CommandError, 'El destino ya confirmó la copia'):
                self.copiar(copiar=True)
        self.assertEqual(CentroID.objects.using('centros').get().pk, self.centro.pk)
        self.assertIn('Comparación correcta', self.copiar())

    def test_error_durante_commit_destino_informa_resultado_incierto(self):
        atomic_original = transaction.atomic

        @contextmanager
        def atomic_con_fallo(*args, **kwargs):
            with atomic_original(*args, **kwargs):
                yield
            if kwargs.get('using') == 'centros':
                raise DatabaseError('Pérdida simulada de respuesta del commit')

        with patch('apps.centros_id.management.commands.copiar_centros_id.transaction.atomic', side_effect=atomic_con_fallo):
            with self.assertRaisesMessage(CommandError, 'No se pudo verificar la confirmación del destino'):
                self.copiar(copiar=True)
        self.assertEqual(CentroID.objects.using('centros').get().pk, self.centro.pk)
        self.assertIn('Comparación correcta', self.copiar())
