"""Catálogo de formación: navegación acotada, filtros SQL y separación editorial."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.formacion.presentation.cursos import NuevoCursoForm, crear_curso, grupos_de_cursos
from apps.formacion.models.cursos import Curso, EdicionCurso
from apps.directorio_unidades.models.core import Unidad


class CatalogoFormacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_superuser('catalogo-formacion-admin', 'catalogo@example.org', 'clave')
        cls.visitante = usuarios.objects.create_user('catalogo-formacion-visitante', password='clave')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de formación escalable', slug='catalogo-formacion', dependencia='laboratorios',
            descripcion='Catálogo de prueba.', fecha_inicio=date(2026, 1, 1),
        )
        cls.ajena = Unidad.objects.create(
            nombre='Otra unidad de formación', slug='catalogo-formacion-ajeno', dependencia='laboratorios',
            descripcion='Otra unidad.', fecha_inicio=date(2026, 1, 1),
        )
        cls.curso = Curso.objects.create(
            unidad=cls.unidad, codigo='CAT-BASE', nombre='Inventarios y trazabilidad digital',
            clasificacion='corto', modalidad='autoguiado', publicado=True, activo=True, orden=1,
        )
        cls.externo = Curso.objects.create(
            unidad=cls.unidad, codigo='CAT-WEB', nombre='Webinar sobre logística sostenible',
            clasificacion='webinar', modalidad='en_vivo', publicado=True, activo=True, orden=2,
            origen='externo', url_externa='https://formacion.example.org/webinar',
            entidad_organizadora='Instituto de Transporte Sostenible', participacion_unidad='colaborador',
        )
        cls.borrador = Curso.objects.create(
            unidad=cls.unidad, codigo='CAT-BORRADOR', nombre='Borrador confidencial de automatización',
            clasificacion='seminario', publicado=False, activo=True,
        )
        cls.inactivo = Curso.objects.create(
            unidad=cls.unidad, codigo='CAT-INACTIVO', nombre='Conferencia inactiva de robótica',
            clasificacion='conferencia', publicado=True, activo=False,
        )
        cls.curso_ajeno = Curso.objects.create(
            unidad=cls.ajena, codigo='CAT-AJENO', nombre='Oferta ajena que no pertenece al catálogo',
            publicado=True, activo=True,
        )
        EdicionCurso.objects.create(curso=cls.curso, nombre='2026-I', anio=2026, activa=True)
        EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=2026, activa=True)
        EdicionCurso.objects.create(curso=cls.externo, nombre='2027', anio=2027, activa=True)
        EdicionCurso.objects.create(curso=cls.borrador, nombre='2030', anio=2030, activa=True)
        EdicionCurso.objects.create(curso=cls.inactivo, nombre='2031', anio=2031, activa=True)
        cls.masivos = Curso.objects.bulk_create([
            Curso(unidad=cls.unidad, codigo=f'CAT-MASIVO-{numero:03d}', nombre=f'Capacitación en procesos {numero:03d}',
                  clasificacion='capacitacion', modalidad='mixto', publicado=True, activo=True, orden=100 + numero)
            for numero in range(39)
        ])
        EdicionCurso.objects.bulk_create([
            EdicionCurso(curso=curso, nombre='2026', anio=2026, activa=True) for curso in cls.masivos
        ])

    @property
    def url(self):
        return reverse('cursos_unidad', args=[self.unidad.slug])

    def cursos_de(self, respuesta):
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context['cursos']

    def test_catalogo_categorias_y_fichas_admiten_el_visor_con_deny_global(self):
        with self.settings(X_FRAME_OPTIONS='DENY'):
            for usuario in (None, self.visitante, self.gestor):
                if usuario is None:
                    self.client.logout()
                else:
                    self.client.force_login(usuario)
                for sufijo in ('', '?categoria=corto', '?categoria=webinar', '?pagina=2'):
                    with self.subTest(usuario=usuario, sufijo=sufijo):
                        respuesta = self.client.get(self.url + sufijo)
                        self.assertEqual(respuesta.status_code, 200)
                        self.assertEqual(respuesta.headers['X-Frame-Options'], 'SAMEORIGIN')
                for curso in (self.curso, self.externo):
                    respuesta = self.client.get(reverse('curso_unidad', args=[self.unidad.slug, curso.codigo]))
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(respuesta.headers['X-Frame-Options'], 'SAMEORIGIN')
            self.client.logout()
            respuesta = self.client.get(reverse('curso_unidad', args=[self.unidad.slug, self.borrador.codigo]))
            self.assertEqual(respuesta.status_code, 404)
            self.assertEqual(respuesta.headers['X-Frame-Options'], 'DENY')

    def test_catalogo_publico_pagina_doce_ofertas_sin_fugas_entre_unidades_o_estados(self):
        respuesta = self.client.get(self.url)
        cursos = self.cursos_de(respuesta)
        self.assertEqual(len(cursos), 12)
        self.assertEqual(respuesta.context['total_cursos'], 41)
        self.assertEqual(respuesta.context['total_filtrado'], 41)
        self.assertEqual(respuesta.context['pagina'].paginator.per_page, 12)
        self.assertEqual(respuesta.context['pagina'].paginator.num_pages, 4)
        for prohibido in (self.borrador, self.inactivo, self.curso_ajeno):
            self.assertNotContains(respuesta, prohibido.nombre)
            self.assertNotIn(prohibido.pk, [curso.pk for curso in cursos])
        self.assertNotIn(2030, respuesta.context['anios'])
        self.assertNotIn(2031, respuesta.context['anios'])

    def test_paginacion_estable_no_repite_ni_omite_ofertas(self):
        ids = []
        for numero in range(1, 5):
            cursos = self.cursos_de(self.client.get(self.url, {'pagina': str(numero)}))
            self.assertLessEqual(len(cursos), 12)
            ids.extend(curso.pk for curso in cursos)
        esperados = set(Curso.objects.filter(unidad=self.unidad, publicado=True, activo=True).values_list('pk', flat=True))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), esperados)

    def test_busqueda_encuentra_nombre_codigo_y_entidad_organizadora(self):
        for texto, esperado in (('trazabilidad digital', self.curso), ('CAT-WEB', self.externo),
                                ('Instituto de Transporte Sostenible', self.externo)):
            with self.subTest(busqueda=texto):
                respuesta = self.client.get(self.url, {'q': texto})
                self.assertEqual([curso.pk for curso in self.cursos_de(respuesta)], [esperado.pk])
                self.assertEqual(respuesta.context['total_filtrado'], 1)

    def test_filtros_combinados_categoria_modalidad_origen_y_anio(self):
        filtros = {'categoria': 'webinar', 'modalidad': 'en_vivo', 'origen': 'externo', 'anio': '2027'}
        respuesta = self.client.get(self.url, filtros)
        self.assertEqual([curso.pk for curso in self.cursos_de(respuesta)], [self.externo.pk])
        self.assertEqual(respuesta.context['total_filtrado'], 1)
        for clave, valor in filtros.items():
            self.assertEqual(str(respuesta.context['filtros'][clave]), valor)
        respuesta = self.client.get(self.url, {**filtros, 'anio': '2026'})
        self.assertEqual(self.cursos_de(respuesta), [])
        self.assertEqual(respuesta.context['total_filtrado'], 0)

    def test_filtro_anual_no_duplica_curso_con_dos_ediciones_en_el_mismo_anio(self):
        respuesta = self.client.get(self.url, {'categoria': 'corto', 'anio': '2026'})
        self.assertEqual([curso.pk for curso in self.cursos_de(respuesta)], [self.curso.pk])
        self.assertEqual(respuesta.context['total_filtrado'], 1)

    def test_edicion_inactiva_no_inventa_un_anio_publico(self):
        EdicionCurso.objects.create(curso=self.curso, nombre='Edición archivada', anio=2028, activa=False)
        respuesta = self.client.get(self.url)
        self.assertNotIn(2028, respuesta.context['anios'])

    def test_solo_gestor_consulta_borradores_o_inactivos(self):
        for usuario in (None, self.visitante):
            if usuario is None:
                self.client.logout()
            else:
                self.client.force_login(usuario)
            for estado, prohibido in (('borrador', self.borrador), ('inactivo', self.inactivo)):
                with self.subTest(usuario=usuario, estado=estado):
                    respuesta = self.client.get(self.url, {'estado': estado, 'q': prohibido.nombre})
                    self.assertEqual(self.cursos_de(respuesta), [])
        self.client.force_login(self.gestor)
        for estado, esperado in (('borrador', self.borrador), ('inactivo', self.inactivo)):
            with self.subTest(estado=estado):
                respuesta = self.client.get(self.url, {'estado': estado})
                self.assertEqual([curso.pk for curso in self.cursos_de(respuesta)], [esperado.pk])
                self.assertEqual(respuesta.context['total_filtrado'], 1)

    def test_parametros_invalidos_extremos_no_producen_error_ni_exponen_borradores(self):
        casos = [
            {'anio': '9' * 5000}, {'anio': '１２３４'},
            {'pagina': '9' * 5000}, {'pagina': '-1'}, {'pagina': 'no-es-numero'},
            {'categoria': '../', 'modalidad': 'inexistente', 'origen': '<script>', 'estado': 'inactivo'},
        ]
        for parametros in casos:
            with self.subTest(parametros=str(parametros)[:100]):
                respuesta = self.client.get(self.url, parametros)
                cursos = self.cursos_de(respuesta)
                self.assertLessEqual(len(cursos), 12)
                self.assertNotContains(respuesta, self.borrador.nombre)
                self.assertNotContains(respuesta, self.inactivo.nombre)
                self.assertGreaterEqual(respuesta.context['pagina'].number, 1)
                self.assertLessEqual(respuesta.context['pagina'].number, respuesta.context['pagina'].paginator.num_pages)

    def test_busqueda_se_normaliza_limita_y_escapa_en_html(self):
        texto = '<script>alert(1)</script>'
        respuesta = self.client.get(self.url, {'q': texto})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, texto)
        self.assertContains(respuesta, '&lt;script&gt;alert(1)&lt;/script&gt;')
        respuesta = self.client.get(self.url, {'q': '  trazabilidad\t\n digital  '})
        self.assertEqual(respuesta.context['filtros']['q'], 'trazabilidad digital')
        respuesta = self.client.get(self.url, {'q': 'x' * 5000})
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(respuesta.context['filtros']['q']), 120)

    def test_query_de_tarjetas_aplica_limit_y_precarga_ediciones_solo_de_la_pagina(self):
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url)
            cursos = self.cursos_de(respuesta)
        sql = [consulta['sql'].upper() for consulta in consultas.captured_queries]
        tarjetas = [consulta for consulta in sql if 'FROM "WEBCITT_CURSO"' in consulta
                    and consulta.startswith('SELECT "WEBCITT_CURSO"."ID"')]
        self.assertTrue(tarjetas, 'Debe existir una consulta acotada para las tarjetas visibles.')
        self.assertTrue(any('LIMIT 12' in consulta for consulta in tarjetas))
        self.assertFalse(any('LIMIT' not in consulta for consulta in tarjetas), 'No materializar el catálogo entero.')
        with self.assertNumQueries(0):
            for curso in cursos:
                list(curso.ediciones.all())

    def test_numero_de_consultas_no_crece_con_el_numero_de_cursos(self):
        Curso.objects.filter(pk__in=[curso.pk for curso in self.masivos]).update(activo=False)
        with CaptureQueriesContext(connection) as pocas:
            self.client.get(self.url)
        Curso.objects.filter(pk__in=[curso.pk for curso in self.masivos]).update(activo=True)
        with CaptureQueriesContext(connection) as muchas:
            self.client.get(self.url)
        self.assertLessEqual(len(muchas), len(pocas) + 2)

    def test_menu_usa_catalogo_y_categorias_sin_repetir_tarjetas_individuales(self):
        with CaptureQueriesContext(connection) as consultas:
            grupos = grupos_de_cursos(self.unidad, None)
        botones = [boton for grupo in grupos for boton in grupo['botones']]
        texto = str(botones)
        self.assertIn('Catálogo de cursos y eventos', texto)
        self.assertIn('cursos-por-anio', texto)
        for curso in (self.curso, self.externo, self.borrador, self.inactivo, *self.masivos):
            self.assertNotIn(reverse('curso_unidad', args=[self.unidad.slug, curso.codigo]), texto)
        self.assertLessEqual(len(botones), len(Curso.CLASIFICACIONES) + 3)
        self.assertLessEqual(len(consultas), 10)
        url_catalogo = reverse('cursos_unidad', args=[self.unidad.slug])
        urls_categoria = [boton.get('url', '') for boton in botones
                          if parse_qs(urlsplit(boton.get('url', '')).query).get('categoria')]
        self.assertTrue(urls_categoria)
        self.assertTrue(all(urlsplit(url).path == url_catalogo for url in urls_categoria))

    def test_detalle_inactivo_o_borrador_no_es_publico_y_ajeno_no_se_cruza(self):
        for curso in (self.borrador, self.inactivo, self.curso_ajeno):
            with self.subTest(curso=curso.codigo):
                self.assertEqual(self.client.get(reverse('curso_unidad', args=[self.unidad.slug, curso.codigo])).status_code, 404)
        self.client.force_login(self.gestor)
        for curso in (self.borrador, self.inactivo):
            self.assertEqual(self.client.get(reverse('curso_unidad', args=[self.unidad.slug, curso.codigo])).status_code, 200)
        self.assertEqual(self.client.get(reverse('curso_unidad', args=[self.unidad.slug, self.curso_ajeno.codigo])).status_code, 404)


class CreacionFormacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('creacion-formacion-admin', 'crear@example.org', 'clave')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de creación de formación', slug='crear-formacion', dependencia='laboratorios',
            descripcion='Actividades de prueba.', fecha_inicio=date(2026, 1, 1),
        )

    def test_formulario_externo_borrador_no_exige_url_ni_anio_y_no_crea_aula_o_edicion(self):
        formulario = NuevoCursoForm({
            'nombre': 'Seminario interinstitucional por completar', 'clasificacion': 'seminario',
            'modalidad': 'en_vivo', 'origen': 'externo', 'participacion_unidad': 'colaborador',
        })
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertIsNone(formulario.cleaned_data['anio'])
        self.assertEqual(formulario.cleaned_data['url_externa'], '')
        curso = crear_curso(self.unidad, **formulario.cleaned_data)
        self.assertEqual(curso.origen, 'externo')
        self.assertFalse(curso.publicado)
        self.assertFalse(curso.emite_certificado)
        self.assertFalse(curso.pago_transferencia)
        self.assertEqual(curso.participacion_unidad, 'colaborador')
        self.assertFalse(curso.ediciones.exists())
        self.assertFalse(curso.modulos.exists())
        self.assertEqual(curso.url_externa, '')

    def test_alta_externa_desde_el_formulario_no_crea_convocatoria_local_ni_matriculas(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.post(reverse('nuevo_curso', args=[self.unidad.slug]), {
            'nombre': 'Encuentro externo de innovación', 'clasificacion': 'encuentro', 'modalidad': 'en_vivo',
            'origen': 'externo', 'entidad_organizadora': 'Instituto colaborador',
            'url_externa': 'https://formacion.example.org/encuentro', 'participacion_unidad': 'colaborador',
        }, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        curso = Curso.objects.get(unidad=self.unidad, nombre='Encuentro externo de innovación')
        self.assertEqual(respuesta.json()['abrir'], reverse('curso_unidad', args=[self.unidad.slug, curso.codigo]))
        self.assertEqual(curso.url_externa, 'https://formacion.example.org/encuentro')
        self.assertFalse(curso.publicado)
        self.assertFalse(curso.ediciones.exists())
        self.assertFalse(curso.modulos.exists())

    def test_formulario_nativo_exige_anio_y_conserva_valores_por_defecto_del_post_anterior(self):
        datos = {'nombre': 'Curso nativo', 'clasificacion': 'corto', 'modalidad': 'autoguiado'}
        formulario = NuevoCursoForm(datos)
        self.assertFalse(formulario.is_valid())
        self.assertIn('anio', formulario.errors)
        formulario = NuevoCursoForm({**datos, 'anio': '2027'})
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(formulario.cleaned_data['origen'], 'nativo')
        self.assertEqual(formulario.cleaned_data['participacion_unidad'], 'organizador')

    def test_eventos_nativos_crean_convocatoria_sin_programa_de_aula_automatico(self):
        for clasificacion in ('webinar', 'seminario', 'conferencia', 'congreso', 'jornada', 'encuentro'):
            with self.subTest(clasificacion=clasificacion):
                curso = crear_curso(self.unidad, f'Evento de tipo {clasificacion}', clasificacion,
                                     'en_vivo', 4, anio=2027)
                self.assertEqual(curso.origen, 'nativo')
                self.assertFalse(curso.publicado)
                self.assertTrue(curso.emite_certificado)
                self.assertEqual(list(curso.ediciones.values_list('nombre', 'anio')), [('2027', 2027)])
                self.assertFalse(curso.modulos.exists())
