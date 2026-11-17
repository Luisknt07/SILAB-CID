"""La función institucional se registra con su acto, sin duplicarse, y se puede revocar."""
from datetime import date, timedelta
from io import StringIO

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.core.gobernanza import es_revisor_institucional, tiene_funcion
from apps.core.models.gobernanza import AsignacionGobernanza
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad

ACTO = ('--acto', 'Encargo de prueba de la función de seguimiento', '--dedicacion', 'Cobertura de prueba')


class DesignarFuncionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.tecnico = usuarios.create_superuser('designa-tecnico', password=None)
        cls.direccion = usuarios.create_user('designa-direccion', password=None)

    def comando(self, *opciones):
        salida = StringIO()
        call_command('designar_funcion', *opciones, stdout=salida)
        return salida.getvalue()

    def designar(self, *opciones):
        return self.comando('--usuario', 'designa-direccion', '--rol', 'seguimiento', *ACTO, *opciones)

    def test_sin_aplicar_solo_ensaya(self):
        salida = self.designar()
        self.assertIn('ENSAYO', salida)
        self.assertIn('designa-direccion', salida)
        self.assertFalse(AsignacionGobernanza.objects.exists())
        self.assertFalse(LogEntry.objects.exists())

    def test_aplicar_deja_la_funcion_vigente_con_su_acto_y_quien_la_registro(self):
        self.assertFalse(es_revisor_institucional(self.direccion))
        self.designar('--aplicar')
        designacion = AsignacionGobernanza.objects.get()
        self.assertEqual((designacion.usuario, designacion.registrado_por, designacion.desde, designacion.hasta),
                         (self.direccion, self.tecnico, timezone.localdate(), None))
        self.assertEqual(designacion.acto, ACTO[1])
        self.assertTrue(es_revisor_institucional(self.direccion))
        # Queda en el historial de administración, como si se hubiera registrado en pantalla.
        self.assertEqual(LogEntry.objects.get().user, self.tecnico)

    def test_repetir_no_duplica_la_designacion_vigente(self):
        self.designar('--aplicar')
        self.assertIn('No se duplica', self.designar('--aplicar'))
        self.assertEqual(AsignacionGobernanza.objects.count(), 1)

    def test_avisa_las_unidades_que_la_cuenta_no_podra_revisar(self):
        Unidad.objects.create(nombre='Laboratorio que administra', slug='designa-administra',
                              dependencia='laboratorios', administrador=self.direccion, fecha_inicio=date(2025, 1, 1))
        coordinada = Unidad.objects.create(nombre='Laboratorio que coordina', slug='designa-coordina',
                                           dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        ResponsableUnidad.objects.create(unidad=coordinada, usuario=self.direccion, nombre='Coordinación de prueba',
                                         rol='coordinacion', activo=True)
        ajena = Unidad.objects.create(nombre='Laboratorio ajeno', slug='designa-ajeno',
                                      dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        salida = self.designar('--aplicar')
        self.assertIn('Laboratorio que administra', salida)
        self.assertIn('Laboratorio que coordina', salida)
        self.assertNotIn(ajena.nombre, salida)

    def test_revocar_quita_la_funcion_y_conserva_el_registro(self):
        self.designar('--aplicar')
        self.comando('--usuario', 'designa-direccion', '--rol', 'seguimiento', '--revocar')
        self.assertTrue(es_revisor_institucional(self.direccion))  # el ensayo no revoca
        salida = self.comando('--usuario', 'designa-direccion', '--rol', 'seguimiento', '--revocar', '--aplicar')
        self.assertIn('Revocada', salida)
        self.assertFalse(es_revisor_institucional(self.direccion))
        self.assertFalse(AsignacionGobernanza.objects.get().activa)
        self.assertEqual(LogEntry.objects.count(), 2)
        # Después de revocada se puede volver a designar.
        self.designar('--aplicar')
        self.assertTrue(es_revisor_institucional(self.direccion))

    def test_exige_acto_dedicacion_y_el_ambito_que_corresponde_a_la_funcion(self):
        with self.assertRaises(CommandError):
            self.comando('--usuario', 'designa-direccion', '--rol', 'seguimiento', '--aplicar')
        with self.assertRaises(CommandError):  # la dependencia requiere su ID
            self.comando('--usuario', 'designa-direccion', '--rol', 'adscripcion', *ACTO, '--aplicar')
        with self.assertRaises(CommandError):  # el seguimiento es institucional, sin ámbito
            self.designar('--referencia', '7', '--aplicar')
        self.assertFalse(AsignacionGobernanza.objects.exists())
        self.comando('--usuario', 'designa-direccion', '--rol', 'adscripcion', '--referencia', '7', *ACTO, '--aplicar')
        self.assertTrue(tiene_funcion(self.direccion, 'adscripcion', 7))

    def test_rechaza_cuentas_inexistentes_inactivas_y_registros_sin_superusuario(self):
        with self.assertRaises(CommandError):
            self.comando('--usuario', 'no-existe', '--rol', 'seguimiento', *ACTO, '--aplicar')
        get_user_model().objects.create_user('designa-inactiva', password=None, is_active=False)
        with self.assertRaises(CommandError):
            self.comando('--usuario', 'designa-inactiva', '--rol', 'seguimiento', *ACTO, '--aplicar')
        with self.assertRaises(CommandError):
            self.designar('--registra', 'designa-direccion', '--aplicar')
        get_user_model().objects.create_superuser('designa-otro-tecnico', password=None)
        with self.assertRaises(CommandError):  # con dos superusuarios hay que decir quién registra
            self.designar('--aplicar')
        self.designar('--registra', 'designa-otro-tecnico', '--aplicar')
        self.assertEqual(AsignacionGobernanza.objects.get().registrado_por.username, 'designa-otro-tecnico')

    def test_la_vigencia_futura_o_vencida_no_concede_la_funcion_y_listar_lo_dice(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertIn('empieza a regir', self.designar('--desde', manana, '--aplicar'))
        self.assertFalse(es_revisor_institucional(self.direccion))
        self.assertIn('sin efecto', self.comando('--listar'))
        with self.assertRaises(CommandError):
            self.designar('--desde', '17/11/2026', '--aplicar')
