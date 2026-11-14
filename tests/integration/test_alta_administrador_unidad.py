from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad, puede_gestionar_unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


class AltaAdministradorUnidadTests(BaseDelExpediente):
    def setUp(self):
        self.suelto.administrador = None
        self.suelto.save(update_fields=['administrador'])
        self.client.force_login(self.direccion)

    def datos(self, **extra):
        return {'username': 'administrador.nuevo', 'first_name': 'Ana', 'last_name': 'Prueba',
                'email': 'ana.unidad@example.test', 'usable_password': 'true',
                'password1': 'Alta-2026-cuenta-prueba!', 'password2': 'Alta-2026-cuenta-prueba!',
                '_save': 'Guardar', **extra}

    def test_alta_asigna_solo_unidad_y_permisos_por_defecto_con_auditoria(self):
        response = self.client.post(reverse('admin:auth_user_add'), self.datos(unidad_administrada=self.suelto.pk))
        self.assertEqual(response.status_code, 302)
        usuario = get_user_model().objects.get(username='administrador.nuevo')
        self.suelto.refresh_from_db()
        self.assertEqual(self.suelto.administrador_id, usuario.pk)
        self.assertTrue(all(permisos_operativos_unidad(usuario, self.suelto).values()))
        self.assertFalse(puede_gestionar_unidad(usuario, self.laboratorio))
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(unidad=self.suelto,
                        descripcion='Asignación de administrador al crear la cuenta').exists())
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 200)

    def test_alta_sin_unidad_no_otorga_privilegios(self):
        self.assertEqual(self.client.post(reverse('admin:auth_user_add'), self.datos()).status_code, 302)
        usuario = get_user_model().objects.get(username='administrador.nuevo')
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.unidades_administradas.exists())

    def test_no_sustituye_administrador_ni_duplica_correo(self):
        response = self.client.post(reverse('admin:auth_user_add'), self.datos(unidad_administrada=self.laboratorio.pk))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='administrador.nuevo').exists())
        response = self.client.post(reverse('admin:auth_user_add'), self.datos(email=self.direccion.email.upper()))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='administrador.nuevo').exists())

    def test_staff_delegado_no_puede_crear_cuentas(self):
        self.client.force_login(self.decano)
        self.assertEqual(self.client.get(reverse('admin:auth_user_add')).status_code, 403)

    def test_indice_distingue_gestion_de_personas_y_configuracion_tecnica(self):
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Cuentas y administradores de unidad')
        self.assertContains(response, 'Historial de verificaciones')
        self.assertContains(response, 'Configuración técnica de acceso')

    def test_directorio_agrupa_sin_perder_cuentas_y_conserva_tabla(self):
        from apps.gestion_unidades.models.espacios import ResponsableUnidad
        personal = get_user_model().objects.create_user('personal.directorio', email='personal@example.test')
        ResponsableUnidad.objects.create(unidad=self.laboratorio, usuario=personal,
                                         nombre='Personal', rol='laboratorista', activo=True)
        url = reverse('admin:auth_user_changelist')
        respuesta = self.client.get(url)
        self.assertContains(respuesta, 'Usuarios por tipo y unidad')
        filas = [fila for grupo in respuesta.context['grupos'] for fila in grupo['unidades']]
        laboratorio = next(f for f in filas if f['unidad'].pk == self.laboratorio.pk)
        self.assertEqual({f['cuenta'].pk for f in laboratorio['usuarios']}, {self.coordinador.pk, personal.pk})
        self.assertContains(respuesta, 'personal@example.test')
        encontrada = self.client.get(url, {'q': 'personal.directorio'})
        self.assertEqual(encontrada.context['total'], 1)
        self.assertEqual(len(encontrada.context['grupos']), 1)
        self.assertEqual(self.client.get(url, {'vista': 'tabla'}).status_code, 200)
