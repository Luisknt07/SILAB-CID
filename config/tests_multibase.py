"""Integración PostgreSQL optativa; ejecutar con settings_testing_multibase.

Fuera de la suite histórica de una base: exige dos bases de QA independientes.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections, router, transaction
from django.test import TestCase
from unittest import skipUnless

from apps.centros_id.identidades import identidad_de
from apps.centros_id.models import CentroID, CuentaCentro


# PruebasAisladas envuelve discovery con override_settings(MEDIA_ROOT=...).
# Django UserSettingsHolder.SETTINGS_MODULE es None en ese contexto; validar
# el aislamiento real en lugar de comparar ese metadato del módulo.
MULTIBASE = (
    settings.CENTROS_DB_ENABLED
    and {'default', 'centros'} <= settings.DATABASES.keys()
    and settings.DATABASES['default']['NAME'] != settings.DATABASES['centros']['NAME']
    and all(
        settings.DATABASES[alias]['ENGINE'] == 'django.db.backends.postgresql'
        and str(settings.DATABASES[alias]['NAME']).startswith(('citt_qa_', 'test_citt_qa_'))
        and not settings.DATABASES[alias].get('TEST', {}).get('MIRROR')
        for alias in ('default', 'centros')
    )
)


@skipUnless(MULTIBASE, 'Esta suite exige el perfil multibase aislado.')
class SeparacionFisicaCentrosTests(TestCase):
    databases = {'default', 'centros'} if MULTIBASE else {'default'}

    def tablas(self, alias):
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            return {row[0] for row in cursor.fetchall()}

    def test_esquemas_realmente_separados_sin_auth_permisos_o_sesiones_duplicados(self):
        self.assertNotEqual(connections['default'].settings_dict['NAME'], connections['centros'].settings_dict['NAME'])
        principal, centros = self.tablas('default'), self.tablas('centros')
        self.assertIn(get_user_model()._meta.db_table, principal)
        self.assertIn(CuentaCentro._meta.db_table, centros)
        self.assertIn(CentroID._meta.db_table, centros)
        self.assertFalse(any(tabla.startswith('centros_id_') for tabla in principal))
        self.assertTrue(all(tabla.startswith('centros_id_') or tabla == 'django_migrations' for tabla in centros))
        with connections['centros'].cursor() as cursor:
            cursor.execute("SELECT target.relname FROM pg_constraint fk "
                           "JOIN pg_class target ON target.oid=fk.confrelid WHERE fk.contype='f'")
            self.assertTrue(all(row[0].startswith('centros_id_') for row in cursor.fetchall()))

    def test_crud_proyecta_solo_presentacion_y_autoriza_desde_identidad_central_vigente(self):
        usuario = get_user_model().objects.create_user('qa-centros', password='clave-no-se-copia', first_name='Persona QA')
        cuenta = identidad_de(usuario)
        self.assertEqual(usuario._state.db, 'default')
        self.assertEqual(cuenta._state.db, 'centros')
        self.assertEqual(cuenta.pk, usuario.pk)
        self.assertEqual(cuenta.first_name, usuario.first_name)
        campos = {campo.name for campo in CuentaCentro._meta.fields}
        self.assertTrue({'password', 'is_superuser', 'is_staff', 'groups', 'user_permissions'}.isdisjoint(campos))
        with transaction.atomic(using='centros'):
            centro = CentroID.objects.create(nombre='Centro QA', slug='centro-qa', proposito='Verificación aislada',
                                            area=CentroID._meta.get_field('area').choices[0][0], responsable=usuario)
            centro.gestores.add(usuario)
        centro = CentroID.objects.select_related('responsable').get(pk=centro.pk)
        self.assertEqual(centro._state.db, 'centros')
        self.assertIsInstance(centro.responsable, CuentaCentro)
        self.assertTrue(centro.puede_gestionar(usuario))
        self.assertFalse(router.allow_relation(usuario, centro))
        get_user_model().objects.filter(pk=usuario.pk).update(is_active=False)
        self.assertFalse(centro.puede_gestionar(usuario))

    def test_borrado_central_no_concede_acceso_a_proyeccion_huerfana(self):
        usuario = get_user_model().objects.create_user('qa-centros-eliminado')
        cuenta = identidad_de(usuario)
        identificador = usuario.pk
        usuario.delete()
        self.assertTrue(CuentaCentro.objects.filter(pk=identificador).exists())
        from apps.centros_id.identidades import principal_vigente
        self.assertIsNone(principal_vigente(identificador))
        self.assertIsNone(principal_vigente(cuenta))
