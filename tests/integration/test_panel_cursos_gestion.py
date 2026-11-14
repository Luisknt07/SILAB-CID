"""La consola de cursos comparte alcance, filtros y cifras con sus reportes privados."""
import csv
import io
from datetime import date
from html.parser import HTMLParser
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.messages import SUCCESS, get_messages
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class _PanelCursosHTML(HTMLParser):
    """Aísla la sección real: el panel incluye también selectores de personal."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.nivel = 0
        self.paneles = 0
        self.fragmentos = []

    def handle_starttag(self, tag, attrs):
        if self.nivel:
            self.fragmentos.append(self.get_starttag_text())
            if tag == 'section':
                self.nivel += 1
        elif tag == 'section' and 'data-cursos-panel' in dict(attrs):
            self.nivel = 1
            self.paneles += 1
            self.fragmentos.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.nivel:
            self.fragmentos.append(f'</{tag}>')
            if tag == 'section':
                self.nivel -= 1

    def handle_startendtag(self, tag, attrs):
        if self.nivel:
            self.fragmentos.append(self.get_starttag_text())

    def handle_data(self, data):
        if self.nivel:
            self.fragmentos.append(data)

    def handle_entityref(self, name):
        if self.nivel:
            self.fragmentos.append(f'&{name};')

    def handle_charref(self, name):
        if self.nivel:
            self.fragmentos.append(f'&#{name};')


class PanelCursosGestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_user('gestor-panel-cursos', password='clave')
        cls.sin_cursos = usuarios.objects.create_user('tecnico-panel-cursos', password='clave')
        cls.ajeno = usuarios.objects.create_user('ajeno-panel-cursos', password='clave')
        for persona in (cls.gestor, cls.sin_cursos):
            identificar(persona, tipo_usuario='administrativo', carrera='')
        identificar(cls.ajeno, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de formación operativa', slug='lab-panel-cursos',
            descripcion='Prueba de formación', fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios', administrador=cls.gestor,
        )
        cls.otra_unidad = Unidad.objects.create(
            nombre='Unidad confidencial ajena', slug='lab-ajeno-panel-cursos',
            descripcion='Otra unidad', fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
        )
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.sin_cursos, rol='responsable_tecnico',
            activo=True, permisos_operativos={'practicas': False},
        )
        cls.curso = Curso.objects.create(
            unidad=cls.unidad, codigo='PANEL-CUR-001', nombre='Aplicaciones logísticas',
            publicado=True, duracion_horas=40,
        )
        cls.borrador = Curso.objects.create(
            unidad=cls.unidad, codigo='PANEL-CUR-BOR', nombre='Curso reservado en preparación',
            publicado=False,
        )
        cls.otro_curso = Curso.objects.create(
            unidad=cls.otra_unidad, codigo='PANEL-CUR-AJENO', nombre='Curso confidencial ajeno',
            publicado=True,
        )
        cls.grupo_a = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=2026)
        cls.grupo_b = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo B', anio=2026)
        cls.grupo_borrador = EdicionCurso.objects.create(curso=cls.borrador, nombre='Grupo borrador', anio=2026)
        cls.grupo_ajeno = EdicionCurso.objects.create(curso=cls.otro_curso, nombre='Grupo ajeno', anio=2026)
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Operaciones')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, titulo='Proceso', tipo='texto', orden=1)
        cls.examen = LeccionCurso.objects.create(
            modulo=modulo, titulo='Evaluación', tipo='evaluacion', orden=2, nota_minima=70, intentos=3,
        )
        cls.deber = LeccionCurso.objects.create(modulo=modulo, titulo='Aplicación final', tipo='deber', orden=3)
        cls.deber_borrador = LeccionCurso.objects.create(
            modulo=modulo, titulo='Trabajo no publicado', tipo='deber', publicada=False, orden=4,
        )
        modulo_ajeno = ModuloCurso.objects.create(curso=cls.otro_curso, titulo='Módulo ajeno')
        cls.lecciones_ajenas = [LeccionCurso.objects.create(
            modulo=modulo_ajeno, titulo=f'Lección ajena {numero}', tipo='texto', orden=numero,
        ) for numero in range(1, 4)]

        cls.aprobado = cls.matricular('aprobado', 'Ana Aprobada', 'aceptada')
        cls.certificado = cls.matricular('certificado', 'Beatriz Certificada', 'aceptada')
        cls.en_curso = cls.matricular('en-curso', 'Carlos En Curso', 'aceptada', cls.grupo_b)
        cls.reprobado = cls.matricular('reprobado', 'Diego Reprobado', 'aceptada')
        cls.pendiente = cls.matricular('pendiente', 'Elena Pendiente', 'pendiente')
        cls.retirado = cls.matricular('retirado', 'Felipe Retirado', 'retirada')
        cls.rechazado = cls.matricular('rechazado', 'Gabriela Rechazada', 'rechazada')
        cls.inscripcion_ajena = cls.matricular(
            'confidencial', 'Persona Confidencial Ajena', 'aceptada', cls.grupo_ajeno,
        )
        for inscrito in (cls.aprobado, cls.certificado, cls.pendiente, cls.retirado, cls.rechazado):
            for leccion in (cls.lectura, cls.examen, cls.deber):
                ProgresoLeccion.objects.create(inscripcion=inscrito, leccion=leccion)
        for inscrito in (cls.aprobado, cls.certificado):
            IntentoEvaluacion.objects.create(inscripcion=inscrito, leccion=cls.examen, nota=Decimal('80.00'), aprobado=True)
            EntregaDeber.objects.create(inscripcion=inscrito, leccion=cls.deber, estado='aprobada', nota=Decimal('90.00'))
        for inscrito in (cls.en_curso, cls.reprobado):
            ProgresoLeccion.objects.create(inscripcion=inscrito, leccion=cls.lectura)
        # Ni un progreso ajeno ni trabajos ocultos o de matrículas pendientes
        # pueden inflar las cifras académicas que requiere atender la unidad.
        for leccion in cls.lecciones_ajenas:
            ProgresoLeccion.objects.create(inscripcion=cls.en_curso, leccion=leccion)
        EntregaDeber.objects.create(inscripcion=cls.en_curso, leccion=cls.deber, estado='entregada')
        EntregaDeber.objects.create(inscripcion=cls.aprobado, leccion=cls.deber_borrador, estado='entregada')
        EntregaDeber.objects.create(inscripcion=cls.pendiente, leccion=cls.deber, estado='entregada')
        for _ in range(3):
            IntentoEvaluacion.objects.create(inscripcion=cls.reprobado, leccion=cls.examen, nota=Decimal('50.00'))
        cls.certificado_vigente = CertificadoCurso.objects.create(
            inscripcion=cls.certificado, codigo='CERT-PANEL-VIGENTE', nombre='Beatriz Certificada',
            curso_nombre=cls.curso.nombre, clasificacion='Curso corto', horas=40,
            edicion=cls.grupo_a.nombre, unidad_nombre=cls.unidad.nombre, nota_final=Decimal('85.00'),
        )
        CertificadoCurso.objects.create(
            inscripcion=cls.retirado, codigo='CERT-PANEL-ANULADO', nombre='Felipe Retirado',
            curso_nombre=cls.curso.nombre, clasificacion='Curso corto', horas=40,
            edicion=cls.grupo_a.nombre, unidad_nombre=cls.unidad.nombre, anulado=True,
        )
        cls.url = reverse('gestion_unidad', args=[cls.unidad.slug])
        cls.csv_url = reverse('gestion_cursos_csv', args=[cls.unidad.slug])
        cls.pdf_url = reverse('gestion_cursos_pdf', args=[cls.unidad.slug])

    @classmethod
    def matricular(cls, clave, nombre, estado='aceptada', grupo=None):
        persona = get_user_model().objects.create_user(
            f'panel-cursos-{clave}', email=f'{clave}@example.org', first_name=nombre,
        )
        return InscripcionCurso.objects.create(
            edicion=grupo or cls.grupo_a, usuario=persona, estado=estado,
            nombres_completos=nombre, documento=f'DOC-{clave}',
        )

    def panel(self, **filtros):
        self.client.force_login(self.gestor)
        return self.client.get(self.url, {'view': 'cursos', **filtros})

    def filas(self, response):
        return response.context['cursos_gestion']['participantes']

    def ids(self, response):
        return {fila['inscripcion'].pk for fila in self.filas(response)}

    def html_cursos(self, response, esperado=1):
        parser = _PanelCursosHTML()
        parser.feed(response.content.decode())
        self.assertEqual(parser.paneles, esperado)
        self.assertEqual(parser.nivel, 0)
        return ''.join(parser.fragmentos)

    def test_panel_y_reportes_requieren_login_y_vinculo_a_la_unidad(self):
        for url in (self.url, self.csv_url, self.pdf_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {'view': 'cursos'}).status_code, 302)
        self.client.force_login(self.ajeno)
        for url in (self.url, self.csv_url, self.pdf_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {'view': 'cursos'}).status_code, 403)

    def test_personal_sin_practicas_no_recibe_datos_ocultos_en_el_dom(self):
        self.client.force_login(self.sin_cursos)
        pagina = self.client.get(self.url)
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, 'data-management-target="cursos"')
        self.assertNotContains(pagina, 'data-management-view="cursos"')
        cursos_html = self.html_cursos(pagina, esperado=0)
        self.assertNotIn(self.borrador.nombre, cursos_html)
        self.assertNotIn(self.aprobado.documento, cursos_html)
        self.assertNotIn(self.aprobado.nombres_completos, cursos_html)
        self.assertFalse(pagina.context.get('cursos_gestion'))
        for url in (self.url, self.csv_url, self.pdf_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {'view': 'cursos'}).status_code, 403)

    def test_gestor_ve_borradores_y_acciones_del_curso_sin_mezclar_unidades(self):
        pagina = self.panel()
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'data-management-target="cursos"')
        self.assertContains(pagina, 'data-management-view="cursos"')
        self.assertEqual(pagina.context['vista_gestion'], 'cursos')
        cursos_html = self.html_cursos(pagina)
        self.assertIn(self.borrador.nombre, cursos_html)
        self.assertNotIn(self.otro_curso.nombre, cursos_html)
        self.assertNotIn(self.inscripcion_ajena.nombres_completos, cursos_html)
        self.assertNotIn(self.inscripcion_ajena.documento, cursos_html)
        self.assertNotIn(self.inscripcion_ajena.pk, self.ids(pagina))
        self.assertNotIn(self.otro_curso.pk, {item['curso'].pk
            for item in pagina.context['cursos_gestion']['cursos']})
        self.assertIn(reverse('editar_certificado_curso', args=[self.unidad.slug, self.curso.codigo]), cursos_html)
        self.assertIn('private', pagina['Cache-Control'])
        self.assertIn('no-store', pagina['Cache-Control'])

    def test_indicadores_excluyen_matriculas_inactivas_progresos_ajenos_y_anulados_sin_emitir(self):
        certificados = CertificadoCurso.objects.count()
        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde') as emitir:
            pagina = self.panel()
        emitir.assert_not_called()
        self.assertEqual(CertificadoCurso.objects.count(), certificados)
        resumen = pagina.context['cursos_gestion']['resumen']
        esperados = {
            'cursos': 2, 'publicados': 1, 'borradores': 1, 'grupos': 3,
            'inscripciones': 7, 'aceptadas': 4, 'pendientes': 1,
            'por_calificar': 1, 'aprobados': 2, 'reprobados': 1, 'certificados': 1,
        }
        for clave, total in esperados.items():
            with self.subTest(indicador=clave):
                self.assertEqual(resumen[clave], total)

    def test_filtros_academicos_no_equiparan_avance_historico_a_matricula_aceptada(self):
        for estado, esperados in (
            ('aprobado', {self.aprobado.pk, self.certificado.pk}),
            ('por_calificar', {self.en_curso.pk}),
            ('reprobado', {self.reprobado.pk}),
            ('certificado', {self.certificado.pk}),
            ('pendiente', {self.pendiente.pk}),
            ('retirada', {self.retirado.pk}),
        ):
            with self.subTest(estado=estado):
                pagina = self.panel(estado_cursos=estado)
                self.assertEqual(pagina.status_code, 200)
                self.assertEqual(self.ids(pagina), esperados)
                self.assertEqual(pagina.context['cursos_gestion']['resumen']['inscripciones'], len(esperados))

    def test_curso_grupo_y_busqueda_conservan_cohorte_y_alcance(self):
        pagina = self.panel(curso_cursos=self.curso.pk, grupo_cursos=self.grupo_b.pk)
        self.assertEqual(self.ids(pagina), {self.en_curso.pk})
        self.assertEqual(pagina.context['cursos_gestion']['modo'], 'participantes')
        catalogo = self.panel(curso_cursos=self.curso.pk, grupo_cursos=self.grupo_b.pk, modo_cursos='cursos')
        self.assertEqual(catalogo.context['cursos_gestion']['modo'], 'cursos')
        self.assertEqual(self.ids(catalogo), {self.en_curso.pk})
        for consulta in (self.en_curso.nombres_completos, self.en_curso.documento, self.en_curso.usuario.email):
            with self.subTest(q=consulta):
                pagina = self.panel(q_cursos=consulta)
                self.assertEqual(self.ids(pagina), {self.en_curso.pk})
        for fila in self.filas(pagina):
            self.assertEqual(fila['grupo'].pk, self.grupo_b.pk)
            self.assertEqual(fila['reporte_url'], reverse('seguimiento_participante_curso',
                args=[self.unidad.slug, self.curso.codigo, self.en_curso.pk]))
            self.assertEqual(fila['reporte_pdf_url'], fila['reporte_url'] + '?formato=pdf')

    def test_parametros_invalidos_y_referencias_ajenas_no_abren_otro_curso(self):
        consultas = (
            {'curso_cursos': 'no-es-id'}, {'grupo_cursos': '-1'},
            {'curso_cursos': self.otro_curso.pk}, {'grupo_cursos': self.grupo_ajeno.pk},
            {'curso_cursos': self.curso.pk, 'grupo_cursos': self.grupo_borrador.pk},
            {'estado_cursos': 'estado-inventado'},
        )
        self.client.force_login(self.gestor)
        for consulta in consultas:
            for url in (self.url, self.csv_url, self.pdf_url):
                with self.subTest(url=url, consulta=consulta):
                    self.assertEqual(self.client.get(url, {'view': 'cursos', **consulta}).status_code, 404)

    def test_paginacion_no_pierde_participantes_y_normaliza_numero_de_pagina(self):
        for numero in range(25):
            self.matricular(f'pagina-{numero:02d}', f'Participante página {numero:02d}')
        primera = self.panel()
        segunda = self.panel(pagina_cursos=2)
        self.assertEqual(primera.context['cursos_gestion']['pagina'].paginator.count, 32)
        self.assertEqual(len(self.filas(primera)), 25)
        self.assertEqual(len(self.filas(segunda)), 7)
        self.assertFalse(self.ids(primera) & self.ids(segunda))
        self.assertEqual(len(self.ids(primera) | self.ids(segunda)), 32)
        self.assertEqual(self.panel(pagina_cursos='abc').context['cursos_gestion']['pagina'].number, 1)
        for numero in (-1, 999):
            with self.subTest(pagina=numero):
                self.assertEqual(self.panel(pagina_cursos=numero).context['cursos_gestion']['pagina'].number, 2)

    def test_csv_compartido_respeta_filtros_y_neutraliza_formulas_en_identidad(self):
        InscripcionCurso.objects.filter(pk=self.aprobado.pk).update(nombres_completos='=SUM(A1:A2)')
        consulta = {
            'curso_cursos': self.curso.pk, 'grupo_cursos': self.grupo_a.pk,
            'estado_cursos': 'aprobado', 'q_cursos': '=SUM(A1:A2)',
        }
        pagina = self.panel(**consulta)
        self.assertEqual(self.ids(pagina), {self.aprobado.pk})
        csv_respuesta = self.client.get(self.csv_url, consulta)
        self.assertEqual(csv_respuesta.status_code, 200)
        self.assertEqual(csv_respuesta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('private', csv_respuesta['Cache-Control'])
        self.assertIn('no-store', csv_respuesta['Cache-Control'])
        self.assertEqual(csv_respuesta['X-Content-Type-Options'], 'nosniff')
        filas = list(csv.reader(io.StringIO(csv_respuesta.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(filas), 2)
        self.assertIn("'=SUM(A1:A2)", filas[1])
        self.assertIn(self.grupo_a.nombre, filas[1])
        self.assertNotIn(self.inscripcion_ajena.documento, csv_respuesta.content.decode('utf-8-sig'))

    def test_exportaciones_incluyen_todo_el_filtro_aunque_la_vista_este_paginada(self):
        for numero in range(25):
            self.matricular(f'csv-{numero:02d}', f'Participante CSV {numero:02d}')
        self.client.force_login(self.gestor)
        respuesta = self.client.get(self.csv_url, {'pagina_cursos': 2})
        filas = list(csv.reader(io.StringIO(respuesta.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(filas), 33)
        self.assertEqual(len({tuple(fila) for fila in filas[1:]}), 32)

    def test_pdf_es_privado_y_solo_consulta_sin_emitir_certificados(self):
        self.client.force_login(self.gestor)
        antes = CertificadoCurso.objects.count()
        from apps.formacion.presentation import gestion_cursos
        generar = gestion_cursos.pdf_control_cursos
        capturadas = []

        def capturar(unidad, resumen, filas, filtros):
            filas = list(filas)
            capturadas.extend(filas)
            self.assertEqual(unidad.pk, self.unidad.pk)
            self.assertEqual(resumen['inscripciones'], 1)
            return generar(unidad, resumen, filas, filtros)

        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde') as emitir, \
                patch.object(gestion_cursos, 'pdf_control_cursos', side_effect=capturar):
            respuesta = self.client.get(self.pdf_url, {
                'curso_cursos': self.curso.pk, 'grupo_cursos': self.grupo_b.pk,
            })
        emitir.assert_not_called()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(CertificadoCurso.objects.count(), antes)
        self.assertEqual({fila['inscripcion'].pk for fila in capturadas}, {self.en_curso.pk})


    def test_grupo_guardado_confirma_exito_solo_despues_de_persistir(self):
        self.client.force_login(self.gestor)
        url = reverse('grupos_curso', args=[self.unidad.slug, self.curso.codigo])
        respuesta = self.client.post(url, {
            'nombre': 'Nuevo grupo autorizado', 'tipo_grupo': 'periodica',
            'anio': 2026, 'cupo': 20, 'activa': 'on',
        }, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(EdicionCurso.objects.filter(
            curso=self.curso, nombre='Nuevo grupo autorizado', cupo=20, activa=True,
        ).count(), 1)
        self.assertTrue(any(mensaje.level == SUCCESS for mensaje in get_messages(respuesta.wsgi_request)))
        self.assertContains(respuesta, 'portal-messages__item is-success')

    def test_aceptar_inscripcion_sin_cupo_no_confirma_guardado_ni_cambia_estado(self):
        grupo = EdicionCurso.objects.create(curso=self.curso, nombre='Grupo con cupo agotado', anio=2026, cupo=1)
        self.matricular('plaza-ocupada', 'Persona con plaza', 'aceptada', grupo)
        pendiente = self.matricular('plaza-pendiente', 'Persona pendiente de plaza', 'pendiente', grupo)
        self.client.force_login(self.gestor)
        url = reverse('inscritos_curso', args=[self.unidad.slug, self.curso.codigo]) + f'?edicion={grupo.pk}'
        respuesta = self.client.post(url, {
            'accion': 'aceptar', 'edicion': grupo.pk, 'inscripcion': pendiente.pk,
        }, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, 'pendiente')
        self.assertIsNone(pendiente.fecha_respuesta)
        self.assertEqual(grupo.inscripciones.filter(estado='aceptada').count(), 1)
        self.assertTrue(respuesta.context['mensaje'])
        self.assertFalse(any(mensaje.level == SUCCESS for mensaje in get_messages(respuesta.wsgi_request)))

    def test_matricula_individual_invalida_no_produce_senal_de_exito_ni_invita(self):
        self.client.force_login(self.gestor)
        inscripciones = InscripcionCurso.objects.count()
        invitaciones = InvitacionCurso.objects.count()
        url = reverse('inscritos_curso', args=[self.unidad.slug, self.curso.codigo]) + f'?edicion={self.grupo_b.pk}'
        with patch('apps.formacion.presentation.matriculas_cursos.matricular_lista') as matricular:
            respuesta = self.client.post(url, {
                'accion': 'matricular_individual', 'edicion': self.grupo_b.pk,
                'correo': 'correo sin formato', 'nombres_completos': 'Persona con datos inválidos',
                'documento': 'DOC-MATRICULA-ERROR',
            }, follow=True)
        matricular.assert_not_called()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(InscripcionCurso.objects.count(), inscripciones)
        self.assertEqual(InvitacionCurso.objects.count(), invitaciones)
        self.assertTrue(respuesta.context['mensaje'])
        self.assertFalse(any(mensaje.level == SUCCESS for mensaje in get_messages(respuesta.wsgi_request)))

    def ampliar_oferta(self, cantidad=39):
        cursos = Curso.objects.bulk_create([
            Curso(unidad=self.unidad, codigo=f'PANEL-OFERTA-{numero:03d}',
                  nombre=f'Actividad de formación {numero:03d}', publicado=True, orden=numero + 1)
            for numero in range(cantidad)
        ])
        EdicionCurso.objects.bulk_create([
            EdicionCurso(curso=curso, nombre='Convocatoria 2026', anio=2026) for curso in cursos
        ])
        return cursos

    def test_oferta_admin_pagina_doce_tarjetas_en_sql_y_conserva_indicadores_globales(self):
        self.ampliar_oferta()
        self.client.force_login(self.gestor)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.url, {'view': 'cursos', 'modo_cursos': 'cursos'})
        self.assertEqual(respuesta.status_code, 200)
        contexto = respuesta.context['cursos_gestion']
        self.assertEqual(len(contexto['cursos']), 12)
        self.assertEqual(contexto['pagina_oferta'].paginator.count, 41)
        self.assertEqual(contexto['pagina_oferta'].paginator.per_page, 12)
        self.assertEqual(contexto['resumen']['cursos'], 41)
        self.assertEqual(contexto['resumen']['grupos'], 42)
        tabla = Curso._meta.db_table.upper()
        tabla_unidad = Unidad._meta.db_table.upper()
        sql_tarjetas = [consulta['sql'].upper() for consulta in consultas.captured_queries
                       if consulta['sql'].upper().startswith(f'SELECT "{tabla}"."ID"')
                       and f'JOIN "{tabla_unidad}"' in consulta['sql'].upper()]
        self.assertTrue(sql_tarjetas)
        self.assertTrue(all('LIMIT 12' in sql for sql in sql_tarjetas))
        self.assertContains(respuesta, 'Buscar en catálogo')
        self.assertEqual(contexto['catalogo_url'], reverse('cursos_unidad', args=[self.unidad.slug]))
        self.assertIn('data-panel-direct', self.html_cursos(respuesta))
        curso_base = next(item for item in contexto['cursos'] if item['curso'].pk == self.curso.pk)
        self.assertEqual(curso_base['inscripciones'], 7)
        self.assertEqual(curso_base['grupos'], 2)

    def test_paginacion_de_oferta_es_estable_e_independiente_de_veinticinco_participantes(self):
        self.ampliar_oferta()
        for numero in range(25):
            self.matricular(f'oferta-pagina-{numero:02d}', f'Participante de oferta {numero:02d}')
        primera = self.panel(modo_cursos='cursos')
        segunda = self.panel(modo_cursos='cursos', pagina_oferta_cursos=2, pagina_cursos=2)
        contexto_primera = primera.context['cursos_gestion']
        contexto_segunda = segunda.context['cursos_gestion']
        self.assertEqual(contexto_primera['pagina_oferta'].number, 1)
        self.assertEqual(contexto_segunda['pagina_oferta'].number, 2)
        self.assertEqual(len(contexto_primera['cursos']), 12)
        self.assertEqual(len(contexto_segunda['cursos']), 12)
        self.assertEqual(len(contexto_primera['participantes']), 25)
        self.assertEqual(len(contexto_segunda['participantes']), 7)
        self.assertFalse({item['curso'].pk for item in contexto_primera['cursos']}
                         & {item['curso'].pk for item in contexto_segunda['cursos']})
        self.assertFalse(self.ids(primera) & self.ids(segunda))
        ids_oferta = []
        for numero in range(1, 5):
            pagina = self.panel(modo_cursos='cursos', pagina_oferta_cursos=numero)
            ids_oferta.extend(item['curso'].pk for item in pagina.context['cursos_gestion']['cursos'])
        self.assertEqual(len(ids_oferta), len(set(ids_oferta)))
        self.assertEqual(set(ids_oferta), set(Curso.objects.filter(unidad=self.unidad).values_list('pk', flat=True)))
        filtrada = self.panel(modo_cursos='cursos', pagina_oferta_cursos=2, pagina_cursos=2,
                             estado_cursos='aceptada', q_cursos='panel-cursos')
        contexto = filtrada.context['cursos_gestion']
        self.assertEqual(contexto['pagina_oferta'].number, 2)
        self.assertEqual(contexto['pagina'].number, 2)
        siguiente = parse_qs(urlsplit(contexto['siguiente_oferta_url']).query)
        self.assertEqual(siguiente['view'], ['cursos'])
        self.assertEqual(siguiente['modo_cursos'], ['cursos'])
        self.assertEqual(siguiente['pagina_oferta_cursos'], ['3'])
        self.assertEqual(siguiente['pagina_cursos'], ['2'])
        self.assertEqual(siguiente['estado_cursos'], ['aceptada'])
        self.assertEqual(siguiente['q_cursos'], ['panel-cursos'])
        for enlace in contexto['paginacion']:
            parametros = parse_qs(urlsplit(enlace['url']).query)
            self.assertEqual(parametros['pagina_oferta_cursos'], ['2'])
            self.assertEqual(parametros['modo_cursos'], ['participantes'])

    def test_pagina_de_oferta_invalida_o_extrema_no_rompe_el_panel(self):
        self.ampliar_oferta(13)
        for valor in ('9' * 5000, '-1', 'abc', '１２', ''):
            with self.subTest(valor=valor[:30]):
                respuesta = self.panel(modo_cursos='cursos', pagina_oferta_cursos=valor)
                self.assertEqual(respuesta.status_code, 200)
                contexto = respuesta.context['cursos_gestion']
                self.assertEqual(contexto['pagina_oferta'].number, 1)
                self.assertEqual(len(contexto['cursos']), 12)
                self.assertEqual(contexto['pagina'].number, 1)
        ultima = self.panel(modo_cursos='cursos', pagina_oferta_cursos='999999')
        self.assertEqual(ultima.context['cursos_gestion']['pagina_oferta'].number, 2)
        self.assertEqual(len(ultima.context['cursos_gestion']['cursos']), 3)
