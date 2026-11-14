from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.laboratorios.operacion.admin.fabricacion import SolicitudFabricacionAdminForm
from apps.recursos.models.consumibles import Consumible
from apps.core.models.usuarios import Decanato
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion


class FlujoFabLabIntegradoTests(TestCase):
    def setUp(self):
        self.administrador = get_user_model().objects.create_superuser(
            username='admin-integracion',
            email='admin-integracion@upec.edu.ec',
            password='clave-pruebas',
        )

    def test_aprobacion_tecnica_actualiza_estado_y_fecha(self):
        solicitud = SolicitudFabricacion.objects.create(
            nombre_proyecto='Prototipo de prueba',
            tiempo_estimado_horas=2,
            costo_materiales_estimado=15,
        )

        solicitud.revision_laboratorista = 'aprobada'
        solicitud.save()
        solicitud.refresh_from_db()

        self.assertEqual(solicitud.estado, 'estimada')
        self.assertIsNotNone(solicitud.fecha_revision_laboratorista)

    def test_admin_exige_estimacion_para_aprobar(self):
        formulario = SolicitudFabricacionAdminForm(
            data={
                'fecha_solicitud': '2026-08-12',
                'tipo_trabajo': 'investigacion',
                'revision_laboratorista': 'aprobada',
                'estado': 'pendiente',
            }
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn('costo y el tiempo estimados', formulario.non_field_errors()[0])

    def test_admin_permite_abrir_y_editar_una_solicitud(self):
        solicitud = SolicitudFabricacion.objects.create(
            nombre_proyecto='Solicitud editable',
        )
        self.client.force_login(self.administrador)

        respuesta = self.client.get(
            reverse('admin:laboratorios_operacion_solicitudfabricacion_change', args=[solicitud.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Solicitud editable')


class InventarioMinimoIntegradoTests(TestCase):
    def test_alerta_solo_se_activa_con_umbral_configurado(self):
        consumible = Consumible.objects.create(
            codigo='MIN-001',
            nombre='Filamento',
            stock_total=3,
            minimo=5,
        )
        self.assertTrue(consumible.bajo_minimo)

        consumible.minimo = 0
        self.assertFalse(consumible.bajo_minimo)


class DecanatoIntegradoTests(TestCase):
    def test_perfil_configura_acceso_minimo_a_solicitudes(self):
        usuario = get_user_model().objects.create_user(
            username='decanato-prueba',
            password='clave-pruebas',
        )

        Decanato.objects.create(usuario=usuario)
        usuario.refresh_from_db()

        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.groups.filter(name='Decanato').exists())
        self.assertTrue(
            usuario.has_perm('laboratorios_operacion.view_solicitudfabricacion')
        )
        self.assertTrue(
            usuario.has_perm('laboratorios_operacion.change_solicitudfabricacion')
        )

    def test_decanato_usa_modulo_administrativo_especializado(self):
        registro = admin.site._registry[Decanato]
        self.assertEqual(registro.__class__.__module__, 'apps.core.admin.usuarios')
