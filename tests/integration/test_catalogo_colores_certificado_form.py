"""Catálogo académico y colores del certificado sin consultas ni persistencia."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.catalogos import catalogo_academico
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm


class CatalogoColoresCertificadoFormTests(SimpleTestCase):
    def setUp(self):
        self.catalogo = catalogo_academico({
            'facultades': [('fac_a', 'Facultad A'), ('fac_b', 'Facultad B')],
            'carreras': [('car_a', 'Carrera A', 'fac_a'), ('car_b', 'Carrera B', 'fac_b')],
        })
        self.catalogo_mock = patch('apps.formacion.presentation.certificados_forms.catalogo_actual', return_value=self.catalogo)
        self.catalogo_mock.start()
        self.addCleanup(self.catalogo_mock.stop)

    def datos(self, **cambios):
        formulario = ConfiguracionCertificadoForm()
        datos = {}
        for nombre, campo in formulario.fields.items():
            valor = formulario[nombre].value()
            if getattr(campo.widget, 'input_type', '') == 'file':
                continue
            if valor is True:
                datos[nombre] = 'on'
            elif valor not in (None, False):
                datos[nombre] = str(valor)
        datos.update(cambios)
        return datos

    def test_catalogo_contextual_e_iniciales_canonicos(self):
        formulario = ConfiguracionCertificadoForm(initial={'facultad_nombre': 'fac_a', 'carrera_nombre': 'Carrera A'})
        self.assertEqual(formulario['facultad_catalogo'].value(), 'fac_a')
        self.assertEqual(formulario['carrera_catalogo'].value(), 'car_a')
        self.assertNotIn('externo', dict(formulario.fields['facultad_catalogo'].choices))
        self.assertEqual(formulario.catalogo_editor['carreras'][0]['facultad'], 'fac_a')
        nuevo = catalogo_academico({'facultades': [('nueva', 'Dependencia vigente')]})
        with patch('apps.formacion.presentation.certificados_forms.catalogo_actual', return_value=nuevo):
            actualizado = ConfiguracionCertificadoForm()
        self.assertIn('nueva', dict(actualizado.fields['facultad_catalogo'].choices))
        self.assertNotIn('fac_a', dict(actualizado.fields['facultad_catalogo'].choices))

    def test_seleccion_resuelve_etiquetas_y_no_confia_en_texto_enviado(self):
        formulario = ConfiguracionCertificadoForm(self.datos(
            facultad_catalogo='fac_b', carrera_catalogo='car_b',
            facultad_nombre='Nombre alterado', carrera_nombre='Nombre alterado',
            mostrar_facultad='on', mostrar_carrera='on'))
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(formulario.instance.facultad_nombre, 'Facultad B')
        self.assertEqual(formulario.instance.carrera_nombre, 'Carrera B')

    def test_rechaza_relacion_cruzada_y_codigo_inventado(self):
        for facultad, carrera, campo in [('fac_a', 'car_b', 'carrera_catalogo'), ('fac_a', 'inventada', 'carrera_catalogo')]:
            with self.subTest(carrera=carrera):
                formulario = ConfiguracionCertificadoForm(self.datos(
                    facultad_catalogo=facultad, carrera_catalogo=carrera, mostrar_carrera='on'))
                self.assertFalse(formulario.is_valid())
                self.assertIn(campo, formulario.errors)

    def test_nombres_legados_siguen_editables_y_conservados(self):
        inicial = {'facultad_nombre': 'Dependencia histórica', 'carrera_nombre': 'Programa histórico'}
        formulario = ConfiguracionCertificadoForm(initial=inicial)
        self.assertEqual(formulario['facultad_catalogo'].value(), '__personalizado__')
        self.assertEqual(formulario['carrera_catalogo'].value(), '__personalizado__')
        editado = ConfiguracionCertificadoForm(self.datos(
            facultad_catalogo='__personalizado__', carrera_catalogo='__personalizado__',
            **inicial, mostrar_facultad='on', mostrar_carrera='on'))
        self.assertTrue(editado.is_valid(), editado.errors)
        self.assertEqual(editado.instance.carrera_nombre, inicial['carrera_nombre'])

    def test_carrera_legada_sin_facultad_no_inventa_adscripcion(self):
        formulario = ConfiguracionCertificadoForm(self.datos(
            facultad_catalogo='', carrera_catalogo='__personalizado__',
            facultad_nombre='', carrera_nombre='Programa histórico independiente', mostrar_carrera='on'))
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(formulario.instance.facultad_nombre, '')

    def test_paleta_contextual_no_sobrescribe_personalizados(self):
        identidad = (None, SimpleNamespace(paleta=(('primario', '#123456'), ('acento', '#abcdef'))))
        with patch('apps.formacion.presentation.certificados_forms.identidad_actual', return_value=identidad):
            formulario = ConfiguracionCertificadoForm(initial={'color_primario': '#163D5C', 'color_acento': '#38B9CF', 'diseno': 'ia_particulas'})
            self.assertEqual(formulario.paleta_predeterminada['primario'], '#123456')
            self.assertEqual(formulario.fields['color_acento'].widget.attrs['placeholder'], '#abcdef')
            self.assertEqual(formulario.paletas_editor[0]['acento'], '#abcdef')
            self.assertEqual(formulario['color_primario'].value(), '#163D5C')
            self.assertEqual(formulario['color_acento'].value(), '#38B9CF')
