"""Prueba SQL real con rol sin BYPASSRLS; las consultas ORM no añaden filtros de propietario."""
import uuid
from contextlib import contextmanager
from datetime import date
from unittest import SkipTest

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from apps.integraciones import modelos as models


class RlsPersonalTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != 'postgresql':
            raise SkipTest('RLS requiere PostgreSQL real.')
        cls.role = 'slcid_test_' + uuid.uuid4().hex[:12]
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname=current_user')
            if not cursor.fetchone()[0]:
                raise SkipTest('El rol de prueba requiere CREATEROLE para comprobar un usuario restringido.')
            cursor.execute(f'CREATE ROLE {cls.role} NOLOGIN NOSUPERUSER NOBYPASSRLS')
            cursor.execute(f'GRANT USAGE ON SCHEMA public TO {cls.role}')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {cls.role}')
            cursor.execute(f'GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {cls.role}')
            if settings.CENTROS_DB_ENABLED:
                # El esquema legado puede conservarse tras el corte. La cuenta
                # QA debe tener los mismos límites que una cuenta web real.
                cursor.execute("SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                               "WHERE n.nspname='public' AND left(c.relname,11)='centros_id_' "
                               "AND c.relkind IN ('r','p','v','m','f','S')")
                for tabla, tipo in cursor.fetchall():
                    objeto = 'SEQUENCE' if tipo == 'S' else 'TABLE'
                    cursor.execute(f'REVOKE ALL ON {objeto} public.{connection.ops.quote_name(tabla)} FROM {cls.role}')

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP OWNED BY {cls.role}')
                cursor.execute(f'DROP ROLE {cls.role}')
        finally:
            super().tearDownClass()

    def setUp(self):
        self.owner = get_user_model().objects.create_user('propietario')
        self.other = get_user_model().objects.create_user('otro')
        self.unit = models.Unidad.objects.create(nombre='Unidad RLS', slug='unidad-rls', dependencia='laboratorios', fecha_inicio=date.today())
        course = models.Curso.objects.create(unidad=self.unit, codigo='RLS-CUR', nombre='Curso RLS')
        edition = models.EdicionCurso.objects.create(curso=course, nombre='RLS', anio=2026, inicio=date.today(), fin=date.today())
        module = models.ModuloCurso.objects.create(curso=course, titulo='Módulo')
        lesson = models.LeccionCurso.objects.create(modulo=module, titulo='Lección')
        product = models.Producto.objects.create(unidad=self.unit, nombre='Producto RLS')
        recipe = models.Receta.objects.create(unidad=self.unit, producto=product, nombre='Receta RLS', cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        self.teacher = get_user_model().objects.create_user('docente-rls')
        exercise = models.EjercicioAula.objects.create(unidad=self.unit, receta=recipe, nombre='Ejercicio RLS',
                                                      consigna='Prueba', creado_por=self.teacher)
        self.tables = [models.IntentoEjercicio, models.SimulacionGuardada, models.ProgresoLeccion, models.IntentoEvaluacion, models.EntregaDeber, models.PagoInscripcion]
        for user in (self.owner, self.other):
            models.IntentoEjercicio.objects.create(ejercicio=exercise, estudiante=user)
            models.SimulacionGuardada.objects.create(unidad=self.unit, autor=user, simulador='balance', nombre='Privada')
            inscription = models.InscripcionCurso.objects.create(edicion=edition, usuario=user)
            models.ProgresoLeccion.objects.create(inscripcion=inscription, leccion=lesson)
            models.IntentoEvaluacion.objects.create(inscripcion=inscription, leccion=lesson, nota=0)
            models.EntregaDeber.objects.create(inscripcion=inscription, leccion=lesson)
            models.PagoInscripcion.objects.create(inscripcion=inscription, monto_original=0, monto=0)

    @contextmanager
    def identity(self, user_id=0, units='', superuser='off'):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'SET LOCAL ROLE {self.role}')
                cursor.execute("SELECT set_config('slcid.user_id', %s, true), set_config('slcid.units', %s, true), set_config('slcid.superuser', %s, true)", [str(user_id), units, superuser])
            yield

    def test_sin_identidad_no_se_lee_ninguna_fila_personal(self):
        with self.identity():
            for model in self.tables:
                self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_consulta_sin_filtro_solo_devuelve_filas_propias(self):
        with self.identity(self.owner.pk):
            for model in self.tables:
                self.assertEqual(model.objects.count(), 1, model.__name__)
            self.assertEqual(models.SimulacionGuardada.objects.exclude(autor_id=self.owner.pk).count(), 0)

    def test_no_se_puede_cambiar_el_propietario_por_sql_ni_insertar_para_otro(self):
        with self.identity(self.owner.pk):
            with self.assertRaises(DatabaseError), transaction.atomic():
                models.SimulacionGuardada.objects.update(autor_id=self.other.pk)
            with self.assertRaises(DatabaseError), transaction.atomic():
                models.SimulacionGuardada.objects.create(unidad=self.unit, autor=self.other, nombre='Ajena', simulador='balance')

    def test_personal_de_otra_unidad_no_recibe_acceso_y_el_gestor_autorizado_si(self):
        with self.identity(0, units=str(self.unit.pk + 100)):
            self.assertEqual(models.EntregaDeber.objects.count(), 0)
        with self.identity(0, units=str(self.unit.pk)):
            self.assertEqual(models.EntregaDeber.objects.count(), 2)
            # La simulación privada no se hace pública para personal operativo.
            self.assertEqual(models.SimulacionGuardada.objects.count(), 0)

    def test_docente_solo_lee_los_intentos_de_sus_ejercicios(self):
        with self.identity(self.teacher.pk):
            self.assertEqual(models.IntentoEjercicio.objects.count(), 2)
            self.assertEqual(models.EntregaDeber.objects.count(), 0)

    def test_contexto_no_se_filtra_a_la_siguiente_transaccion(self):
        with self.identity(self.owner.pk):
            self.assertEqual(models.SimulacionGuardada.objects.count(), 1)
        with self.identity(self.other.pk):
            self.assertEqual(models.SimulacionGuardada.objects.get().autor_id, self.other.pk)
        with self.identity(0, superuser='on'):
            self.assertEqual(models.SimulacionGuardada.objects.count(), 2)
        with self.identity():
            self.assertEqual(models.SimulacionGuardada.objects.count(), 0)

    def test_verificacion_rechaza_superusuario_y_acepta_rol_web_restringido(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from io import StringIO
        with self.assertRaises(CommandError):
            call_command('verificar_seguridad_bd', stdout=StringIO())
        with self.identity():
            call_command('verificar_seguridad_bd', stdout=StringIO())

    def test_las_seis_tablas_tienen_rls_forzado(self):
        from apps.core.management.commands.verificar_seguridad_bd import TABLES
        with connection.cursor() as cursor:
            cursor.execute('SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname=ANY(%s)', [list(TABLES)])
            rows = cursor.fetchall()
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(enabled and forced for _, enabled, forced in rows))
