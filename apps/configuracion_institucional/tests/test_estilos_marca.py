"""Contrato visual seguro, compatible con revisiones anteriores y reversible."""
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.estilos_marca import OPCIONES_ESTILO
from apps.core.paleta import PALETA_SUGERIDA, componentes_paleta, contraste, validar_paleta
from apps.configuracion_institucional.models import RevisionPresentacion
from apps.configuracion_institucional.paleta import PaletaField
from apps.configuracion_institucional.services import guardar_borrador, publicar_revision

ESTILO = {
    'linea_color': '#c06400', 'linea_degradado': 'linear-gradient(90deg, #ffd700, #ffffff)',
    'linea_grosor': 4, 'linea_intensidad': 60, 'linea_ancho': 75,
    'degradado_superficie': 'linear-gradient(110deg, #082b22, #071525)',
    'capa_color': '#ffffff', 'capa_intensidad': 30, 'capa_ancho': 35,
    'fuente_cuerpo': 'verdana', 'fuente_titulos': 'georgia', 'escala_fuente': 115,
    'titulo_color': '#18312a', 'icono_color': '#18312a',
    'degradado_intensidad': 40, 'degradado_ancho': 55,
}


class ContratoEstilosMarcaTests(SimpleTestCase):
    def test_rechaza_css_urls_fuentes_y_numeros_fuera_de_limites(self):
        for cambio in ({'fuente_cuerpo': 'url(https://example.test/font)'}, {'fuente_titulos': '</style>'},
                       {'linea_degradado': 'linear-gradient(90deg, red, url(x))'},
                       {'linea_color': '#123456;display:none'}, {'linea_grosor': True},
                       {'linea_grosor': 0}, {'linea_intensidad': 24}, {'capa_intensidad': 29},
                       {'escala_fuente': 116}, {'degradado_ancho': '80'}, {'degradado_intensidad': -1},
                       {'icono_color': '#ffffff'}, {'titulo_color': '#ffffff'},
                       {'degradado_superficie': 'linear-gradient(90deg, #ffffff, #071525)'}):
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                validar_paleta({**PALETA_SUGERIDA, **cambio})

    def test_linea_clara_decorativa_y_placa_oscura_con_capa_tenue(self):
        salida = dict(validar_paleta({**PALETA_SUGERIDA, **ESTILO}))
        derivados = componentes_paleta(salida)
        self.assertEqual(derivados['linea_opacidad'], .6)
        self.assertEqual(derivados['linea_ancho'], 75)
        self.assertEqual(derivados['capa_opacidad'], .3)
        self.assertEqual(derivados['placa'], PALETA_SUGERIDA['oscuro'])
        self.assertGreaterEqual(contraste('#ffffff', derivados['placa']), 4.5)
        self.assertEqual(derivados['fuente_cuerpo'], 'Verdana, Geneva, sans-serif')
        self.assertIn('Georgia', derivados['fuente_titulos'])
        self.assertIn('#ffffff', salida['linea_degradado'])
        limites = componentes_paleta({**PALETA_SUGERIDA, 'fondo': '#ffffff',
            'titulo_color': '#767676', 'icono_color': '#767676'})
        for superficie in ('primario_suave', 'acento_suave'):
            self.assertGreaterEqual(contraste('#767676', limites[superficie]), 4.5)

    def test_mezcla_y_extension_conservan_contraste_en_cuatro_casos(self):
        for intensidad, ancho in ((0, 20), (30, 45), (70, 75), (100, 100)):
            paleta = {**PALETA_SUGERIDA, 'degradado_primario': 'linear-gradient(135deg, #082b22, #064e3b 50%, #071525)',
                      'degradado_intensidad': intensidad, 'degradado_ancho': ancho}
            derivados = componentes_paleta(paleta)
            for color in re.findall(r'#[a-f0-9]{6}', derivados['imagen_primaria']):
                self.assertGreaterEqual(contraste('#ffffff', color), 4.5)
                self.assertGreaterEqual(contraste(paleta['acento'], color), 4.5)
            self.assertIn(f'{ancho}%', derivados['imagen_primaria'])
        self.assertEqual(componentes_paleta({}), {})

    def test_formulario_conserva_indices_anteriores_y_roundtrip(self):
        campo = PaletaField()
        self.assertEqual(campo.clean([True, *PALETA_SUGERIDA.values()]), PALETA_SUGERIDA)
        paleta = {**PALETA_SUGERIDA, **ESTILO}
        self.assertEqual(campo.clean(campo.widget.decompress(paleta)), dict(validar_paleta(paleta)))
        self.assertEqual(len(campo.widget.widgets), 7 + len(OPCIONES_ESTILO))
        with self.assertRaises(ValidationError):
            campo.clean([True, *PALETA_SUGERIDA.values(), '', '#123456', '', 7])


class PublicacionEstilosMarcaTests(TestCase):
    def test_publicacion_y_reversion_conservan_historial_y_fuentes_de_iconos(self):
        autor = get_user_model().objects.create_superuser('estilos.qa')
        datos = dict(nombre_producto='Sistema QA', nombre_corto_producto='QA', nombre_institucion='QA')
        primera = publicar_revision(guardar_borrador(RevisionPresentacion(**datos, paleta=PALETA_SUGERIDA), autor).pk,
                                    autor, base_esperada=None)
        borrador = guardar_borrador(RevisionPresentacion(**datos, paleta={**PALETA_SUGERIDA, **ESTILO}), autor)
        self.assertNotIn('--institucion-fuente-cuerpo:', self.client.get('/').content.decode())
        vigente = publicar_revision(borrador.pk, autor, base_esperada=primera.pk)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-linea-grosor: 4px;', html)
        self.assertIn('--institucion-capa-opacidad: 0.30;', html)
        self.assertIn('Georgia', html)
        self.assertIn('html { font-size: 115%; }', html)
        self.assertNotIn('i, svg { font-family:', html)
        restaurada = publicar_revision(primera.pk, autor, base_esperada=vigente.pk)
        vigente.refresh_from_db()
        self.assertEqual(vigente.paleta['fuente_cuerpo'], 'verdana')
        self.assertEqual(restaurada.paleta, PALETA_SUGERIDA)

    def test_admin_muestra_controles_y_revision_lee_numeros_sin_estilo_css(self):
        autor = get_user_model().objects.create_superuser('estilos.admin')
        self.client.force_login(autor)
        respuesta = self.client.get(reverse('admin:configuracion_institucional_revisionpresentacion_add'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('data-palette-style="linea_grosor"', respuesta.content.decode())
        revision = guardar_borrador(RevisionPresentacion(nombre_producto='QA', nombre_corto_producto='QA',
            nombre_institucion='QA', paleta={**PALETA_SUGERIDA, **ESTILO}), autor)
        review = self.client.get(reverse('admin:configuracion_institucional_revisionpresentacion_publicar', args=[revision.pk]))
        self.assertEqual(review.status_code, 200)
        self.assertNotIn('background:115', review.content.decode())
        self.assertIn('verdana', review.content.decode())
