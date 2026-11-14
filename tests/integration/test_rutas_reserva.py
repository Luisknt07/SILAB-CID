"""La entrada de cada unidad describe su oferta, sin mezclar visitas con servicios."""

from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings
from django.utils.translation import override

from apps.reservas.presentation.rutas import textos_rutas_reserva


@override_settings(LANGUAGE_CODE='es')
class TextosRutasReservaTests(SimpleTestCase):
    def textos(self, *, espacios=False, equipos=False, software=False, servicios=()):
        configuracion = SimpleNamespace(reservas_espacios=espacios, reservas_equipos=equipos)
        with override('es'):
            return textos_rutas_reserva(configuracion, servicios, software)

    def test_unidad_solo_con_software_no_ofrece_espacios_o_maquinas(self):
        textos = self.textos(software=True)
        self.assertIn('utilizan software', textos['recursos'])
        self.assertNotIn('espacios', textos['recursos'])
        self.assertNotIn('equipos', textos['recursos'])

    def test_unidad_con_laboratorio_fisico_y_software_enumera_sus_capacidades(self):
        textos = self.textos(espacios=True, equipos=True, software=True)
        self.assertIn('espacios, equipos e instrumentos y software', textos['recursos'])

    def test_servicios_de_analisis_no_heredan_fabricacion_ni_visitas(self):
        servicios = [
            SimpleNamespace(nombre='Recorrido escolar', tipo_servicio='visita'),
            SimpleNamespace(nombre='Análisis microbiológico', tipo_servicio='analisis'),
            SimpleNamespace(nombre='Análisis microbiológico', tipo_servicio='analisis'),
        ]
        textos = self.textos(equipos=True, servicios=servicios)
        self.assertIn('Análisis microbiológico', textos['servicios'])
        self.assertEqual(textos['servicios'].count('Análisis microbiológico'), 1)
        self.assertNotIn('Recorrido escolar', textos['servicios'])
        self.assertNotIn('fabricación', textos['servicios'])

    def test_sin_catalogo_no_inventa_servicios_ni_recursos(self):
        textos = self.textos()
        self.assertIn('no tiene reservas de recursos habilitadas', textos['recursos'])
        self.assertNotIn('Servicios publicados', textos['servicios'])
        self.assertIn('revisión técnica', textos['servicios'])

    def test_resumen_de_catalogo_largo_se_limita_a_tres_servicios(self):
        servicios = [SimpleNamespace(nombre=f'Ensayo {i}', tipo_servicio='analisis') for i in range(5)]
        textos = self.textos(servicios=servicios)
        self.assertIn('Ensayo 2', textos['servicios'])
        self.assertNotIn('Ensayo 3', textos['servicios'])
