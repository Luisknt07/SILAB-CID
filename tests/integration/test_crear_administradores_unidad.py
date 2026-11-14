"""Cada unidad recibe su cuenta de administración, con alcance solo sobre su unidad.

La cuenta no es staff ni superusuario: administra su unidad porque la unidad la nombra
administradora, y no puede gestionar ninguna otra. Repetir el comando no cambia contraseñas
salvo que se pida; quien administraba antes queda como coordinación.
"""
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad, puede_gestionar_unidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


class CrearAdministradoresUnidadTests(TestCase):
    def setUp(self):
        self.superusuario = get_user_model().objects.create_superuser('super.pruebas', 's@example.org', 'clave')
        self.persona = get_user_model().objects.create_user('persona.anterior', 'p@example.org', 'clave')
        self.fablab = Unidad.objects.create(
            slug='laboratorio-fabricacion-digital-prototipado', nombre='Laboratorio de Fabricación Digital y Prototipado',
            nombre_corto='FabLab UPEC', descripcion='.', fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            administrador=self.superusuario)
        self.planta = Unidad.objects.create(
            slug='planta-piloto-lacteos', nombre='Planta Piloto de Procesamiento de Lácteos', nombre_corto='Lácteos',
            descripcion='.', fecha_inicio=date(2026, 1, 1), dependencia='plantas_piloto', administrador=self.persona)
        self.observatorio = Unidad.objects.create(
            slug='observatorio-osezif', nombre='Observatorio Socioeconómico de la Zona de Integración Fronteriza',
            nombre_corto='OSEZIF', descripcion='.', fecha_inicio=date(2026, 1, 1), dependencia='observatorios')

    def correr(self, **opciones):
        salida = StringIO()
        call_command('crear_administradores_unidad', stdout=salida, **opciones)
        return salida.getvalue()

    def test_crea_una_cuenta_por_unidad_con_alcance_solo_sobre_ella(self):
        salida = self.correr()
        fila = next(linea for linea in salida.splitlines() if '| admin.fablab |' in linea)
        clave = fila.rsplit('|', 1)[1].strip()
        self.assertGreaterEqual(len(clave), 12)
        cuenta = get_user_model().objects.get(username='admin.fablab')
        self.assertTrue(cuenta.check_password(clave))
        self.assertFalse(cuenta.is_staff or cuenta.is_superuser)
        self.assertEqual((cuenta.first_name, cuenta.last_name), ('Administración', 'FabLab UPEC'))
        self.assertEqual(cuenta.profile.tipo_usuario, 'administrativo')
        for unidad in (self.fablab, self.planta, self.observatorio):
            unidad.refresh_from_db()
        self.assertEqual(self.fablab.administrador, cuenta)
        self.assertEqual(self.planta.administrador.username, 'admin.planta-lacteos')
        self.assertEqual(self.observatorio.administrador.username, 'admin.osezif')
        # Todo sobre su unidad, nada sobre las demás.
        self.assertTrue(all(permisos_operativos_unidad(cuenta, self.fablab).values()))
        self.assertTrue(puede_gestionar_unidad(cuenta, self.fablab))
        self.assertFalse(puede_gestionar_unidad(cuenta, self.planta))
        self.assertFalse(any(permisos_operativos_unidad(cuenta, self.planta).values()))
        self.assertTrue(ResponsableUnidad.objects.filter(unidad=self.fablab, usuario=cuenta, rol='coordinacion').exists())
        # Quien administraba antes queda como coordinación; el superusuario no lo necesita.
        self.assertTrue(ResponsableUnidad.objects.filter(unidad=self.planta, usuario=self.persona, rol='coordinacion').exists())
        self.assertFalse(ResponsableUnidad.objects.filter(unidad=self.fablab, usuario=self.superusuario).exists())
        self.assertIn('3 cuentas creadas', salida)

    def test_entra_al_admin_solo_con_su_unidad(self):
        self.correr()
        self.correr(restablecer=True)
        salida = self.correr(restablecer=True)
        clave = next(linea for linea in salida.splitlines() if '| admin.fablab |' in linea).rsplit('|', 1)[1].strip()
        self.assertTrue(self.client.login(username='admin.fablab', password=clave))
        inicio = self.client.get(reverse('admin:index'))
        self.assertEqual(inicio.status_code, 200)
        self.assertContains(inicio, 'FabLab UPEC')
        self.assertNotContains(inicio, 'Planta Piloto de Procesamiento de Lácteos')
        propia = self.client.get(reverse('admin:laboratorios_laboratorio_change', args=[self.fablab.pk]))
        self.assertEqual(propia.status_code, 200)
        ajena = self.client.get(reverse('admin:plantas_piloto_plantapiloto_change', args=[self.planta.pk]))
        self.assertNotEqual(ajena.status_code, 200)
        self.assertNotEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion_unidad', args=[self.fablab.slug])).status_code, 200)
        self.assertNotEqual(self.client.get(reverse('gestion_unidad', args=[self.planta.slug])).status_code, 200)

    def test_repetir_no_cambia_contrasenas_ni_duplica(self):
        self.correr()
        cuenta = get_user_model().objects.get(username='admin.osezif')
        clave_guardada = cuenta.password
        salida = self.correr()
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.password, clave_guardada)
        self.assertIn('0 cuentas creadas, 3 ya existían', salida)
        self.assertIn('| admin.osezif | (sin cambio)', salida)
        self.assertEqual(ResponsableUnidad.objects.filter(unidad=self.observatorio, usuario=cuenta).count(), 1)
        self.correr(restablecer=True)
        cuenta.refresh_from_db()
        self.assertNotEqual(cuenta.password, clave_guardada)
