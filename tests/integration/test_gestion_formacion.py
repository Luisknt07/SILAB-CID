"""Integración de perfil, cohortes y edición de notas desde el portal."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.edicion_registro import REGISTRO, formulario_de


class GestionFormacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_user('gestion-formacion', 'gestion@example.org', 'clave')
        cls.persona = usuarios.objects.create_user('persona-formacion', 'persona@example.org', 'clave')
        cls.otra = usuarios.objects.create_user('otra-formacion', 'otra@example.org', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Unidad formación', slug='unidad-formacion',
            dependencia='laboratorios', administrador=cls.gestor, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='FORM-001', nombre='Curso con grupos',
            publicado=True, emite_certificado=False)
        cls.primero = EdicionCurso.objects.create(curso=cls.curso, nombre='Convocatoria uno', anio=2026)
        cls.segundo = EdicionCurso.objects.create(curso=cls.curso, nombre='Convocatoria dos', anio=2026)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.primero, usuario=cls.persona,
            estado='aceptada', nombres_completos='Persona de primera convocatoria', documento='DOC-111')
        cls.historica = InscripcionCurso.objects.create(edicion=cls.segundo, usuario=cls.persona,
            estado='retirada', nombres_completos='Persona de segunda convocatoria', documento='DOC-111')
        InscripcionCurso.objects.create(edicion=cls.primero, usuario=cls.otra,
            estado='aceptada', nombres_completos='No mostrar datos ajenos', documento='DOC-222')
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Primera unidad')
        cls.leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lectura', contenido='Práctica')

    def test_perfil_muestra_cada_matricula_propia_y_no_las_ajenas(self):
        self.client.force_login(self.persona)
        respuesta = self.client.get(reverse('mi_formacion'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual({fila['inscripcion'].pk for fila in respuesta.context['filas']},
            {self.inscripcion.pk, self.historica.pk})
        self.assertNotContains(respuesta, 'No mostrar datos ajenos')
        self.assertIn('no-store', respuesta['Cache-Control'])
        for fila in respuesta.context['filas']:
            self.assertIn('edicion=' + str(fila['inscripcion'].edicion_id), fila['reporte_url'])
        historica = next(fila for fila in respuesta.context['filas'] if fila['inscripcion'].pk == self.historica.pk)
        self.assertEqual(historica['aula_url'], '')

    def test_perfil_requiere_login(self):
        self.assertEqual(self.client.get(reverse('mi_formacion')).status_code, 302)

    def test_historial_permanece_con_curso_y_unidad_inactivos(self):
        Curso.objects.filter(pk=self.curso.pk).update(publicado=False)
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.client.force_login(self.persona)
        url = reverse('seguimiento_curso', args=[self.unidad.slug, self.curso.codigo])
        respuesta = self.client.get(url, {'edicion': self.segundo.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['seguimiento']['inscripcion'].pk, self.historica.pk)
        self.assertFalse(respuesta.context['seguimiento']['acceso_aula'])
        self.assertEqual(respuesta.context['curso_url'], reverse('mi_formacion'))

    def test_panel_gestor_renderiza_enlaces_al_reporte_exacto(self):
        self.client.force_login(self.gestor)
        url = reverse('inscritos_curso', args=[self.unidad.slug, self.curso.codigo])
        respuesta = self.client.get(url, {'edicion': self.primero.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse('seguimiento_participante_curso',
            args=[self.unidad.slug, self.curso.codigo, self.inscripcion.pk]))
        self.assertContains(respuesta, 'Persona de primera convocatoria')
        self.assertNotContains(respuesta, 'Persona de segunda convocatoria')

    def test_enlaces_del_aula_conservan_convocatoria(self):
        self.client.force_login(self.persona)
        url = reverse('aula_curso_leccion', args=[self.unidad.slug, self.curso.codigo, self.leccion.pk])
        respuesta = self.client.get(url, {'edicion': self.primero.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse('completar_leccion',
            args=[self.unidad.slug, self.curso.codigo, self.leccion.pk]) + '?edicion=' + str(self.primero.pk))
        self.assertContains(respuesta, reverse('comentar_leccion',
            args=[self.unidad.slug, self.curso.codigo, self.leccion.pk]) + '?edicion=' + str(self.primero.pk))

    def test_editor_nota_convierte_sobre_diez_sin_cambiar_escala_historica(self):
        edicion = REGISTRO['leccion_curso']
        leccion = LeccionCurso(modulo=self.leccion.modulo, titulo='Examen', tipo='evaluacion', nota_minima=70)
        formulario = formulario_de(edicion, self.unidad, ('nota_minima',),
            datos={'registro-nota_minima': '7.5'}, instancia=leccion)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(formulario.cleaned_data['nota_minima'], 75)
        self.assertEqual(formulario.initial['nota_minima'], Decimal('7'))
        fuera = formulario_de(edicion, self.unidad, ('nota_minima',),
            datos={'registro-nota_minima': '11'}, instancia=leccion)
        self.assertFalse(fuera.is_valid())

    def test_emision_relee_estado_de_matricula_antes_de_certificar(self):
        from apps.formacion.presentation.certificados_cursos import emitir_si_corresponde
        Curso.objects.filter(pk=self.curso.pk).update(emite_certificado=True)
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.leccion)
        InscripcionCurso.objects.filter(pk=self.inscripcion.pk).update(estado='retirada')
        self.assertEqual(self.inscripcion.estado, 'aceptada')
        self.assertIsNone(emitir_si_corresponde(self.inscripcion))
        self.assertFalse(CertificadoCurso.objects.filter(inscripcion=self.inscripcion).exists())
