"""Cursos y capacitaciones (sección 4.3): cada curso tiene su página de presentación y sus ediciones por año; el menú
los agrupa por clasificación y la unidad los crea y edita desde la propia página."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.cursos import crear_curso
from apps.formacion.models.cursos import Curso, EdicionCurso
from apps.directorio_unidades.models.core import Unidad


class CursosDeLaUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-cursos', 'c@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con cursos', slug='lab-cursos', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.hoy = timezone.localdate()
        cls.corto = Curso.objects.create(
            unidad=cls.lab, codigo='LC-CUR-001', nombre='Impresión 3D desde cero', lema='Tu primera pieza en 20 horas',
            clasificacion='corto', modalidad='mixto', duracion_horas=20, publicado=True,
            aprendizajes='Modelar piezas\nPreparar la impresora', instructores='Ana Pérez | Diseño 3D')
        EdicionCurso.objects.create(curso=cls.corto, nombre=f'{cls.hoy.year}-I', anio=cls.hoy.year,
                                    inicio=cls.hoy + timedelta(days=10), fin=cls.hoy + timedelta(days=40), cupo=15)
        EdicionCurso.objects.create(curso=cls.corto, nombre='2024-I', anio=2024, inicio=date(2024, 3, 1),
                                    fin=date(2024, 4, 1))
        cls.borrador = Curso.objects.create(unidad=cls.lab, codigo='LC-CUR-002', nombre='Taller de corte láser',
                                            clasificacion='taller', publicado=False)

    def ficha(self):
        return self.client.get(self.lab.get_absolute_url()).content.decode()

    def test_el_menu_ofrece_catalogo_y_categorias_sin_enumerar_cada_curso(self):
        pagina = self.ficha()
        for marca in ('Cursos cortos (1)', 'Catálogo de cursos y eventos',
                      reverse('cursos_unidad', args=[self.lab.slug]) + '?categoria=corto'):
            self.assertIn(marca, pagina)
        for curso in (self.corto, self.borrador):
            self.assertNotIn(reverse('curso_unidad', args=[self.lab.slug, curso.codigo]), pagina)
        self.assertNotIn('Talleres (1)', pagina)
        self.client.force_login(self.admin)
        pagina = self.ficha()
        self.assertIn('Talleres (1)', pagina)
        self.assertNotIn(reverse('curso_unidad', args=[self.lab.slug, self.borrador.codigo]), pagina)
        self.assertIn(reverse('nuevo_curso', args=[self.lab.slug]), pagina)

    def test_la_pagina_del_curso_presenta_sus_ediciones_e_instructores(self):
        url = reverse('curso_unidad', args=[self.lab.slug, 'LC-CUR-001'])
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Tu primera pieza en 20 horas')
        self.assertContains(pagina, f'<strong>{self.hoy.year}-I</strong><span class="curso__estado">Inscripciones abiertas</span>')
        self.assertContains(pagina, 'Inicia sesión o crea tu cuenta para inscribirte')
        self.assertContains(pagina, 'Ana Pérez')
        self.assertContains(pagina, 'Preparar la impresora')
        self.assertContains(pagina, '15 cupos')
        self.assertNotContains(pagina, 'data-editar-ficha')
        self.assertEqual(self.client.get(reverse('curso_unidad', args=[self.lab.slug, 'LC-CUR-002'])).status_code, 404)
        self.client.force_login(self.admin)
        pagina = self.client.get(url)
        self.assertContains(pagina, reverse('editar_registro', args=[self.lab.slug, 'curso', self.corto.pk]) + '?grupo=presentacion')
        self.assertContains(pagina, reverse('editar_registro', args=[self.lab.slug, 'edicion_curso', 'nuevo']) + f'?padre={self.corto.pk}')
        self.assertContains(self.client.get(reverse('curso_unidad', args=[self.lab.slug, 'LC-CUR-002'])), 'Curso sin publicar')

    def test_catalogo_filtra_por_anio_sin_duplicar_ediciones_del_curso(self):
        url = reverse('cursos_unidad', args=[self.lab.slug])
        pagina = self.client.get(url)
        self.assertEqual(pagina.context['anios'], [self.hoy.year, 2024])
        self.assertEqual(pagina.context['total_cursos'], 1)
        filtrada = self.client.get(url, {'anio': '2024'})
        self.assertEqual(filtrada.context['cursos'], [self.corto])
        self.assertEqual(str(filtrada.context['filtros']['anio']), '2024')
        self.assertEqual(filtrada.context['total_filtrado'], 1)
        invalida = self.client.get(url, {'anio': '1999'})
        self.assertFalse(invalida.context['filtros']['anio'])
        self.assertEqual(invalida.context['cursos'], [self.corto])

    def test_la_unidad_crea_un_curso_con_texto_guia_y_su_primera_edicion(self):
        self.client.force_login(self.admin)
        url = reverse('nuevo_curso', args=[self.lab.slug])
        self.assertContains(self.client.get(url, {'fragmento': '1'}), 'name="clasificacion"')
        respuesta = self.client.post(url, {'nombre': 'Robótica educativa', 'clasificacion': 'largo',
                                           'modalidad': 'en_vivo', 'duracion_horas': '60', 'anio': '2027'},
                                     HTTP_X_REQUESTED_WITH='fetch')
        curso = Curso.objects.get(nombre='Robótica educativa')
        self.assertEqual(respuesta.json(), {'ok': True, 'abrir': reverse('curso_unidad', args=[self.lab.slug, curso.codigo])})
        self.assertFalse(curso.publicado)
        self.assertIn('Una frase que invite a inscribirse', curso.lema)
        self.assertEqual(list(curso.ediciones.values_list('nombre', 'anio')), [('2027', 2027)])
        # Nace con la estructura estándar: bienvenida, un módulo con su evaluación y el cierre con la evaluación final.
        self.assertEqual(list(curso.modulos.values_list('titulo', flat=True)),
                         ['Bienvenida', 'Módulo 1', 'Proyecto final y evaluación final'])
        self.assertEqual(curso.modulos.last().lecciones.last().titulo, 'Evaluación final')
        self.assertNotEqual(curso.codigo, crear_curso(self.lab, 'Otro', 'corto', 'autoguiado', None, 2027).codigo)

    def test_se_edita_la_presentacion_y_se_agrega_una_edicion_desde_la_pagina(self):
        self.client.force_login(self.admin)
        url = reverse('editar_registro', args=[self.lab.slug, 'curso', self.borrador.pk])
        self.client.post(url, {'grupo': 'presentacion', 'registro-nombre': 'Taller de corte láser',
                               'registro-clasificacion': 'taller', 'registro-modalidad': 'en_vivo',
                               'registro-lema': 'Corta y graba tus diseños', 'registro-publicado': 'on'},
                         HTTP_X_REQUESTED_WITH='fetch')
        self.borrador.refresh_from_db()
        self.assertTrue(self.borrador.publicado)
        nueva = reverse('editar_registro', args=[self.lab.slug, 'edicion_curso', 'nuevo'])
        respuesta = self.client.post(nueva, {'padre': self.borrador.pk, 'registro-nombre': '2026-II', 'registro-tipo_grupo': 'periodica', 'registro-anio': '2026',
                                             'registro-inicio': '2026-09-01', 'registro-fin': '2026-08-01',
                                             'registro-activa': 'on'})
        self.assertContains(respuesta, 'Termina antes de empezar.')
        respuesta = self.client.post(nueva, {'padre': self.borrador.pk, 'registro-nombre': '2026-II', 'registro-tipo_grupo': 'periodica', 'registro-anio': '2026',
                                             'registro-inicio': '2026-09-01', 'registro-activa': 'on'},
                                     HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.assertEqual(self.borrador.ediciones.get().nombre, '2026-II')

    def test_el_estado_de_cada_edicion_sigue_sus_fechas(self):
        hoy = date(2026, 5, 10)
        edicion = EdicionCurso(curso=self.corto, nombre='x', anio=2026, inicio=date(2026, 6, 1), fin=date(2026, 7, 1),
                               inscripciones_desde=date(2026, 5, 15))
        self.assertEqual(edicion.estado(hoy)[0], 'proxima')
        self.assertEqual(edicion.estado(date(2026, 5, 20))[0], 'inscripciones')
        self.assertEqual(edicion.estado(date(2026, 6, 10))[0], 'en_curso')
        self.assertEqual(edicion.estado(date(2026, 7, 2))[0], 'finalizada')
        edicion.inicio = date(2025, 6, 1)
        with self.assertRaises(ValidationError):
            edicion.full_clean()
        self.assertEqual(self.corto.edicion_vigente().nombre, f'{self.hoy.year}-I')
