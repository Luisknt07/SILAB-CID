"""Retirar una unidad queda claro: se desactiva siempre; se elimina solo si no tiene historial.

Desactivada, sale del catálogo y de su ficha pública, y todo lo suyo se conserva;
quien la gestiona la sigue viendo. El editor, el tablero y la tarjeta del área
dicen su estado y llevan a «Estado de la unidad».
"""
from datetime import date

from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.baja import historial_de
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad


class EstadoDeLaUnidadTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('estado.admin', 'e@example.org', 'clave')
        self.client.force_login(self.admin)
        self.unidad = Unidad.objects.create(nombre='Laboratorio de estado', slug='lab-estado',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.url = reverse('admin:laboratorios_laboratorio_estado', args=[self.unidad.pk])

    def test_el_editor_el_tablero_y_el_area_dicen_su_estado_y_llevan_a_cambiarlo(self):
        for pagina in (reverse('admin:laboratorios_laboratorio_change', args=[self.unidad.pk]),
                       reverse('admin:laboratorios_laboratorio_tablero', args=[self.unidad.pk])):
            respuesta = self.client.get(pagina)
            self.assertContains(respuesta, 'Activa: se ve en el portal.')
            self.assertContains(respuesta, self.url)
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        area = self.client.get(reverse('admin:index')).content.decode()
        self.assertIn('citt-admin-unidad is-desactivada', area)

    def test_desactivar_la_retira_del_portal_y_conserva_todo(self):
        ficha = self.unidad.get_absolute_url()
        self.assertEqual(self.client.get(ficha).status_code, 200)
        self.client.post(self.url, {'accion': 'desactivar'})
        self.unidad.refresh_from_db()
        self.assertFalse(self.unidad.activo)
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.unidad.pk), change_message__contains='desactivada').exists())
        # Quien la gestiona la sigue viendo; el público, no.
        self.assertEqual(self.client.get(ficha).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(ficha).status_code, 404)
        self.assertNotContains(self.client.get(reverse('laboratorios_unidades')), 'Laboratorio de estado')
        self.client.force_login(self.admin)
        self.client.post(self.url, {'accion': 'reactivar'})
        self.unidad.refresh_from_db()
        self.assertTrue(self.unidad.activo)

    def test_sin_historial_se_elimina_y_con_historial_no(self):
        self.assertEqual(historial_de(self.unidad), [])
        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'No tiene historial')
        Recurso.objects.create(unidad=self.unidad, nombre='Guía', url='https://example.org/guia')
        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'No se puede eliminar')
        self.assertIn('recursos', [nombre.lower() for nombre, _total in pagina.context['historial']])
        respuesta = self.client.post(self.url, {'accion': 'eliminar'}, follow=True)
        self.assertContains(respuesta, 'Tiene historial: no se puede eliminar.')
        self.assertTrue(Unidad.objects.filter(pk=self.unidad.pk).exists())
        Recurso.objects.filter(unidad=self.unidad).delete()
        respuesta = self.client.post(self.url, {'accion': 'eliminar'})
        self.assertRedirects(respuesta, reverse('admin:index') + '#laboratorios', fetch_redirect_response=False)
        self.assertFalse(Unidad.objects.filter(pk=self.unidad.pk).exists())
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.unidad.pk), action_flag=DELETION).exists())

    def test_fuera_de_su_alcance_no_existe(self):
        personal = get_user_model().objects.create_user('personal.estado', password='clave', is_staff=True)
        self.client.force_login(personal)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'accion': 'desactivar'}).status_code, 404)
        self.unidad.refresh_from_db()
        self.assertTrue(self.unidad.activo)


class AreasSinRepetirTests(TestCase):
    def test_los_tipos_de_unidad_y_la_lista_de_cada_tipo_aparecen_una_sola_vez(self):
        self.client.force_login(get_user_model().objects.create_superuser('areas.admin', 'a@example.org', 'clave'))
        area = self.client.get(reverse('admin:index')).content.decode()
        tipologias = reverse('admin:configuracion_institucional_tipologiaunidad_changelist')
        self.assertEqual(area.count(f'href="{tipologias}"'), 1)
        self.assertNotIn('Común a todas las unidades', area)
        laboratorios = reverse('admin:laboratorios_laboratorio_changelist')
        self.assertEqual(area.count(f'href="{laboratorios}"'), 1)
        self.assertIn(reverse('admin:laboratorios_laboratorio_add'), area)
        # Un registro heredado sin uso no ocupa lugar en el inicio; los catálogos dicen qué son.
        self.assertNotIn(reverse('admin:recursos_archivorecurso_changelist'), area)
        self.assertIn('Las sedes y campus, con su contorno y edificios en el mapa de ubicación.', area)
