"""Selección académica de certificados con el catálogo compartido y guardado real."""
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.presentation.catalogos import catalogo_actual
from apps.core.presentation.identidad import identidad_actual
from apps.formacion.models.cursos import CertificadoCurso, Curso
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.cursos_certificacion import IMAGENES_CERTIFICADO


class SelectorAcademicoCertificadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalogo = catalogo_actual()
        cls.carrera = cls.catalogo.carreras[0]
        cls.otra_carrera = next(fila for fila in cls.catalogo.carreras if fila[2] != cls.carrera[2])
        cls.gestor = get_user_model().objects.create_superuser(
            'gestor-selector-certificado', 'selector-certificado@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio del selector', slug='lab-selector-certificado', dependencia='laboratorios',
            descripcion='.', fecha_inicio=date(2026, 1, 1),
            facultad=cls.carrera[2], carreras=cls.carrera[0])
        cls.curso = Curso.objects.create(
            unidad=cls.unidad, codigo='SEL-CERT-001', nombre='Diseño y tecnología', duracion_horas=20,
            firma_nombre='Responsable académico', firma_cargo='Coordinación del laboratorio')

    def setUp(self):
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.client.force_login(self.gestor)

    def url(self, nombre):
        return reverse(nombre, args=[self.unidad.slug, self.curso.codigo])

    def datos_editor(self):
        respuesta = self.client.get(self.url('editar_certificado_curso'))
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context['formulario']
        datos = {}
        for nombre in formulario.fields:
            if nombre in IMAGENES_CERTIFICADO or nombre.startswith('quitar_'):
                continue
            valor = formulario[nombre].value()
            if valor is not None and valor is not False:
                datos[nombre] = valor
        return respuesta, datos

    def guardar_previa(self, datos):
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200, previa.content[:1000])
        self.assertEqual(previa['Content-Type'], 'application/pdf')
        self.assertTrue(previa.content.startswith(b'%PDF-'))
        datos = dict(datos, vista_previa_token=previa['X-Certificado-Vista-Previa'])
        guardado = self.client.post(self.url('editar_certificado_curso'), datos)
        self.assertEqual(guardado.status_code, 302, guardado.content[:1000])
        return ConfiguracionCertificadoCurso.objects.get(curso=self.curso)

    def test_get_reutiliza_catalogo_y_resuelve_adscripcion_sin_guardar(self):
        respuesta, datos = self.datos_editor()
        formulario = respuesta.context['formulario']
        self.assertContains(respuesta, 'name="facultad_catalogo"')
        self.assertContains(respuesta, 'name="carrera_catalogo"')
        self.assertEqual(formulario['facultad_catalogo'].value(), self.carrera[2])
        self.assertEqual(formulario['carrera_catalogo'].value(), self.carrera[0])
        self.assertEqual(formulario['facultad_nombre'].value(), dict(self.catalogo.facultades)[self.carrera[2]])
        self.assertEqual(formulario['carrera_nombre'].value(), self.carrera[1])
        paleta = dict(identidad_actual()[1].paleta)
        for campo, clave in (('color_primario', 'primario'), ('color_acento', 'acento')):
            self.assertEqual(formulario.fields[campo].widget.attrs['placeholder'], paleta.get(clave, {'primario': '#006633', 'acento': '#ffce00'}[clave]))
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertIn('facultad_catalogo', datos)

    def test_seleccion_preview_y_guardado_conservan_nombres_y_colores(self):
        _, datos = self.datos_editor()
        datos.update(facultad_catalogo=self.otra_carrera[2], carrera_catalogo=self.otra_carrera[0],
                     mostrar_facultad='on', mostrar_carrera='on', color_primario='#126045', color_acento='#D8BA42',
                     fecha_inicio='2026-10-01', fecha_fin='2026-10-10')
        configuracion = self.guardar_previa(datos)
        self.assertEqual(configuracion.facultad_nombre, dict(self.catalogo.facultades)[self.otra_carrera[2]])
        self.assertEqual(configuracion.carrera_nombre, self.otra_carrera[1])
        self.assertTrue(configuracion.mostrar_facultad)
        self.assertTrue(configuracion.mostrar_carrera)
        self.assertEqual(configuracion.color_primario, '#126045')
        self.assertEqual(configuracion.color_acento, '#D8BA42')
        formulario = self.client.get(self.url('editar_certificado_curso')).context['formulario']
        self.assertEqual(formulario['facultad_catalogo'].value(), self.otra_carrera[2])
        self.assertEqual(formulario['carrera_catalogo'].value(), self.otra_carrera[0])
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_carrera_de_otra_facultad_no_puede_previsualizarse_ni_guardarse(self):
        _, datos = self.datos_editor()
        datos.update(facultad_catalogo=self.carrera[2], carrera_catalogo=self.otra_carrera[0],
                     mostrar_facultad='on', mostrar_carrera='on')
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado') as generar:
            previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
            self.assertEqual(previa.status_code, 400)
            self.assertIn('carrera_catalogo', previa.json()['errores'])
            guardado = self.client.post(self.url('editar_certificado_curso'), datos,
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(guardado.status_code, 400)
            self.assertIn('carrera_catalogo', guardado.json()['errores'])
            generar.assert_not_called()
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_adscripciones_personalizadas_heredadas_sobreviven_guardado(self):
        configuracion = ConfiguracionCertificadoCurso.objects.create(
            curso=self.curso, mostrar_facultad=True, facultad_nombre='Facultad autorizada histórica',
            mostrar_carrera=True, carrera_nombre='Programa académico histórico',
            color_primario='#126045', color_acento='#D8BA42')
        _, datos = self.datos_editor()
        resultado = self.guardar_previa(datos)
        self.assertEqual(resultado.pk, configuracion.pk)
        self.assertEqual(resultado.facultad_nombre, configuracion.facultad_nombre)
        self.assertEqual(resultado.carrera_nombre, configuracion.carrera_nombre)
        self.assertEqual(resultado.color_primario, configuracion.color_primario)
        self.assertEqual(resultado.color_acento, configuracion.color_acento)
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_personalizacion_visual_se_previsualiza_guarda_y_recupera(self):
        _, datos = self.datos_editor()
        datos.update(color_texto='#263D33', color_titulos='#71391D', tipografia='nunito',
                     mostrar_pie_tecnologico='on', estilo_pie_tecnologico='fabricacion', modo_fondo='claro')
        configuracion = self.guardar_previa(datos)
        for nombre in ('color_texto', 'color_titulos', 'tipografia', 'estilo_pie_tecnologico'):
            self.assertEqual(getattr(configuracion, nombre), datos[nombre])
        self.assertTrue(configuracion.mostrar_pie_tecnologico)
        respuesta, nuevos = self.datos_editor()
        self.assertContains(respuesta, 'name="tipografia"')
        self.assertContains(respuesta, 'data-color-picker="color_texto"')
        nuevos['diseno'] = 'circuitos'
        nuevos.pop('mostrar_pie_tecnologico', None)
        resultado = self.guardar_previa(nuevos)
        self.assertFalse(resultado.mostrar_pie_tecnologico)
        self.assertEqual(resultado.color_titulos, '#71391D')
        self.assertEqual(resultado.tipografia, 'nunito')
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_cambiar_color_de_texto_invalida_token_previo(self):
        _, datos = self.datos_editor()
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        datos.update(vista_previa_token=previa['X-Certificado-Vista-Previa'], color_texto='#321234')
        respuesta = self.client.post(self.url('editar_certificado_curso'), datos,
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
