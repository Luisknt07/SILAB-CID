"""La ficha pública de una unidad solo enlaza guías que quien mira puede abrir.

El selector de guías de la reserva listaba toda guía publicada; la vista de la
guía, en cambio, cierra con 404 las de visibilidad «unidad» a quien no ha
iniciado sesión. Un visitante recibía enlaces rotos.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva
from apps.directorio_unidades.models.core import Unidad


class EnlacesAGuiasDesdeLaFichaTests(TestCase):
    def setUp(self):
        self.unidad = Unidad.objects.create(nombre='Laboratorio de prototipado', slug='lab-prototipado',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        actividad = CatalogoActividadReserva.objects.create(
            unidad=self.unidad, nombre='Impresión FDM', activo=True,
            estado_publicacion='publicado', visibilidad='unidad')
        self.interna = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía para la comunidad de la unidad',
            visibilidad='unidad', estado_publicacion='publicada', activo=True)
        self.publica = GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía abierta a todo el público',
            visibilidad='publica', estado_publicacion='publicada', activo=True,
            es_estructurada=True, contenido={'secciones': []})

    def test_el_visitante_solo_ve_enlaces_a_guias_que_puede_abrir(self):
        ficha = self.client.get(self.unidad.get_absolute_url())

        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, reverse('ver_guia_actividad', args=[self.publica.pk]))
        self.assertNotContains(ficha, reverse('ver_guia_actividad', args=[self.interna.pk]))
        # La regla de la vista no cambia: la guía de la unidad sigue cerrada al visitante.
        self.assertEqual(self.client.get(reverse('ver_guia_actividad', args=[self.interna.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('ver_guia_actividad', args=[self.publica.pk])).status_code, 200)
