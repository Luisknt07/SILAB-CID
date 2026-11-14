"""Consulta de cohortes sin emisiones laterales ni lecturas por participante."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.db import connection

from apps.formacion.presentation.aula_cursos import avance, inscritos_view, lecciones_de
from apps.formacion.presentation.certificados_diseno import dibujar_certificado
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad


class ConsultaInscritosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-consulta-inscritos', 'admin@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-consulta-inscritos', 'ana@example.org', 'clave',
                                              first_name='Ana', last_name='Ríos')
        cls.ajeno = usuarios.objects.create_user('staff-ajeno-inscritos', 'ajeno@example.org', 'clave', is_staff=True)
        cls.unidad = Unidad.objects.create(nombre='Unidad consulta de inscritos', slug='consulta-inscritos',
            dependencia='laboratorios', descripcion='Prueba', fecha_inicio=timezone.localdate())
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='CONSULTA-001', nombre='Curso de consulta',
            publicado=True, emite_certificado=True, duracion_horas=20)
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Cohorte actual',
            anio=timezone.localdate().year, inicio=timezone.localdate(), fin=timezone.localdate())
        cls.otro_grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Cohorte histórica',
            anio=timezone.localdate().year, inicio=timezone.localdate(), fin=timezone.localdate())
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.grupo, usuario=cls.ana, estado='aceptada')
        cls.historica = InscripcionCurso.objects.create(edicion=cls.otro_grupo, usuario=cls.ana, estado='aceptada')
        cls.modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Contenido')
        cls.lectura = LeccionCurso.objects.create(modulo=cls.modulo, titulo='Lectura', tipo='texto', orden=1)
        cls.evaluacion = LeccionCurso.objects.create(modulo=cls.modulo, titulo='Evaluación', tipo='evaluacion',
            orden=2, intentos=3, nota_minima=70)

    def url(self, **consulta):
        destino = reverse('inscritos_curso', args=[self.unidad.slug, self.curso.codigo])
        from urllib.parse import urlencode
        return destino + '?' + urlencode({'edicion': self.grupo.pk, **consulta})

    def aprobar(self, inscripcion=None):
        inscripcion = inscripcion or self.inscripcion
        for leccion in (self.lectura, self.evaluacion):
            ProgresoLeccion.objects.create(inscripcion=inscripcion, leccion=leccion)
        IntentoEvaluacion.objects.create(inscripcion=inscripcion, leccion=self.evaluacion,
                                        nota=Decimal('80.00'), aprobado=True)

    def consulta(self, **parametros):
        request = RequestFactory().get(self.url(**parametros))
        request.user = self.admin
        request.session = {}
        sentencias = []

        def registrar(ejecutar, sql, params, many, contexto):
            sentencias.append((sql, params))
            self.assertNotIn(sql.lstrip().split()[0].upper(), {'INSERT', 'UPDATE', 'DELETE', 'MERGE'})
            return ejecutar(sql, params, many, contexto)

        with connection.execute_wrapper(registrar), patch(
                'apps.formacion.presentation.aula_cursos.render', wraps=render) as mostrar:
            respuesta = inscritos_view(request, self.unidad.slug, self.curso.codigo)
        return respuesta, mostrar.call_args.args[2], sentencias

    def test_get_completo_es_solo_consulta_y_ofrece_emision_explicita(self):
        self.aprobar()
        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde', return_value=None) as emitir:
            respuesta, contexto, _ = self.consulta(accion='emitir_certificado_academico')
        emitir.assert_not_called()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(contexto['resumen_grupo'],
                         {'matriculados': 1, 'aprobados': 1, 'certificados': 0, 'por_revisar': 0})
        self.assertEqual(contexto['inscritos'][0].seguimiento['certificado_estado'], 'listo')
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertContains(respuesta, 'name="accion" value="emitir_certificado_academico"')
        self.assertContains(respuesta, 'Emitir certificado académico')
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertIn('private', respuesta['Cache-Control'])

    def test_consultas_no_crecen_al_pasar_de_uno_a_cincuenta_y_un_inscritos(self):
        _, primero, sql_inicial = self.consulta()
        usuarios = get_user_model().objects.bulk_create([
            get_user_model()(username=f'persona-cohorte-{i}', first_name=f'Persona {i}', email=f'p{i}@example.org')
            for i in range(50)
        ])
        InscripcionCurso.objects.bulk_create([
            InscripcionCurso(edicion=self.grupo, usuario=usuario, estado='aceptada') for usuario in usuarios
        ])
        respuesta, segundo, sql_final = self.consulta()
        self.assertEqual(len(primero['inscritos']), 1)
        self.assertEqual(len(segundo['inscritos']), 51)
        self.assertContains(respuesta, 'Persona 49')
        self.assertLessEqual(len(sql_final), len(sql_inicial) + 1)
        # Se mide SQL real durante la vista y el render, no solamente los objetos del contexto.
        self.assertGreater(len(sql_inicial), 5)

    def test_avance_utiliza_el_prefetch_y_conserva_lecciones_completadas(self):
        self.aprobar()
        inscripcion = InscripcionCurso.objects.prefetch_related('progresos').get(pk=self.inscripcion.pk)
        modulos = lecciones_de(self.curso)
        with self.assertNumQueries(0):
            progreso = avance(self.curso, inscripcion, modulos)
        self.assertEqual(progreso['hechas'], {self.lectura.pk, self.evaluacion.pk})
        self.assertEqual((progreso['completadas'], progreso['total'], progreso['porcentaje']), (2, 2, 100))
        with self.assertNumQueries(1):
            sin_precarga = avance(self.curso, self.inscripcion, modulos)
        self.assertEqual(sin_precarga, progreso)

    def test_filtros_y_totales_del_grupo_conservan_semantica_historica(self):
        self.aprobar()
        fallido = InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.ajeno, estado='aceptada')
        for _ in range(3):
            IntentoEvaluacion.objects.create(inscripcion=fallido, leccion=self.evaluacion,
                                            nota=Decimal('20'), aprobado=False)
        # La cohorte ajena no afecta los totales de la seleccionada.
        self.aprobar(self.historica)
        _, contexto, _ = self.consulta(estado='reprobado')
        self.assertEqual([propio.pk for propio in contexto['inscritos']], [fallido.pk])
        self.assertEqual(contexto['resumen_grupo']['matriculados'], 2)
        self.assertEqual(contexto['resumen_grupo']['aprobados'], 1)
        _, contexto, _ = self.consulta(certificado='listo', q='Ana Ríos')
        self.assertEqual([propio.pk for propio in contexto['inscritos']], [self.inscripcion.pk])
        self.assertEqual(contexto['resumen_grupo']['matriculados'], 2)
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_certificado_vigente_tiene_prioridad_sobre_anulado_y_no_se_reemite(self):
        self.aprobar()
        vigente = CertificadoCurso.objects.create(inscripcion=self.inscripcion, codigo='CERT-CONS-VIGE',
            nombre='Ana', curso_nombre=self.curso.nombre, unidad_nombre=self.unidad.nombre)
        CertificadoCurso.objects.create(inscripcion=self.inscripcion, codigo='CERT-CONS-ANUL', nombre='Ana',
            curso_nombre=self.curso.nombre, unidad_nombre=self.unidad.nombre, anulado=True,
            emitido_en=timezone.now() + timedelta(days=1))
        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde') as emitir:
            respuesta, contexto, _ = self.consulta(certificado='emitido')
        emitir.assert_not_called()
        self.assertEqual(contexto['inscritos'][0].certificado_emitido.pk, vigente.pk)
        self.assertContains(respuesta, vigente.codigo)
        self.assertNotContains(respuesta, 'name="accion" value="emitir_certificado_academico"')
        self.assertEqual(contexto['resumen_grupo']['certificados'], 1)

    def test_post_academico_es_idempotente_y_conserva_filtros_y_grupo(self):
        self.aprobar()
        self.client.force_login(self.admin)
        destino = self.url(estado='aprobado', certificado='listo', q='Ana')
        with patch('apps.formacion.presentation.certificados_diseno.dibujar_certificado',
                   wraps=dibujar_certificado) as dibujar:
            for _ in range(2):
                respuesta = self.client.post(destino, {'accion': 'emitir_certificado_academico',
                    'inscripcion': self.inscripcion.pk, 'edicion': self.grupo.pk,
                    'nota': '100', 'tipo': 'organizador'})
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn('estado=aprobado', respuesta.url)
                self.assertIn('certificado=listo', respuesta.url)
                self.assertIn(f'edicion={self.grupo.pk}', respuesta.url)
            self.assertEqual(dibujar.call_count, 1)
        certificado = CertificadoCurso.objects.get(inscripcion=self.inscripcion)
        self.assertEqual(certificado.tipo, 'aprobacion')
        self.assertEqual(certificado.nota_final, Decimal('80.00'))
        self.assertFalse(certificado.emision_manual)

    def test_post_sin_requisitos_no_emite_y_anulado_exige_reemision_especifica(self):
        self.client.force_login(self.admin)
        with patch('apps.formacion.presentation.certificados_diseno.dibujar_certificado') as dibujar:
            self.assertEqual(self.client.post(self.url(), {'accion': 'emitir_certificado_academico',
                'inscripcion': self.inscripcion.pk, 'edicion': self.grupo.pk}).status_code, 302)
            self.assertFalse(CertificadoCurso.objects.exists())
            self.aprobar()
            CertificadoCurso.objects.create(inscripcion=self.inscripcion, codigo='CERT-SOLO-ANUL',
                nombre='Ana', curso_nombre=self.curso.nombre, unidad_nombre=self.unidad.nombre, anulado=True)
            self.client.post(self.url(), {'accion': 'emitir_certificado_academico',
                'inscripcion': self.inscripcion.pk, 'edicion': self.grupo.pk})
        dibujar.assert_not_called()
        self.assertEqual(CertificadoCurso.objects.count(), 1)
        self.assertFalse(CertificadoCurso.objects.filter(anulado=False).exists())

    def test_post_rechaza_otro_grupo_otro_curso_y_unidad_ajena(self):
        otro_curso = Curso.objects.create(unidad=self.unidad, codigo='CONSULTA-OTRO', nombre='Otro curso')
        otro_grupo = EdicionCurso.objects.create(curso=otro_curso, nombre='Otro', anio=2026)
        otra = InscripcionCurso.objects.create(edicion=otro_grupo, usuario=self.ana, estado='aceptada')
        self.client.force_login(self.admin)
        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde') as emitir:
            for objetivo in (self.historica, otra):
                with self.subTest(inscripcion=objetivo.pk):
                    respuesta = self.client.post(self.url(), {'accion': 'emitir_certificado_academico',
                        'inscripcion': objetivo.pk, 'edicion': self.grupo.pk})
                    self.assertEqual(respuesta.status_code, 404)
            self.client.force_login(self.ajeno)
            self.assertEqual(self.client.get(self.url()).status_code, 403)
            self.assertEqual(self.client.post(self.url(), {'accion': 'emitir_certificado_academico',
                'inscripcion': self.inscripcion.pk, 'edicion': self.grupo.pk}).status_code, 403)
        emitir.assert_not_called()
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_post_exige_csrf(self):
        self.aprobar()
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        with patch('apps.formacion.presentation.certificados_cursos.emitir_si_corresponde') as emitir:
            respuesta = cliente.post(self.url(), {'accion': 'emitir_certificado_academico',
                'inscripcion': self.inscripcion.pk, 'edicion': self.grupo.pk})
        self.assertEqual(respuesta.status_code, 403)
        emitir.assert_not_called()

    def test_historial_propio_precarga_actividades_solo_de_la_edicion_elegida(self):
        self.aprobar(self.historica)
        self.client.force_login(self.ana)
        sql = []

        def registrar(ejecutar, consulta, params, many, contexto):
            if any(tabla in consulta for tabla in ('webcitt_progresoleccion', 'webcitt_intentoevaluacion',
                                                   'webcitt_entregadeber', 'webcitt_certificadocurso')):
                sql.append((consulta, params))
            return ejecutar(consulta, params, many, contexto)

        destino = reverse('seguimiento_curso', args=[self.unidad.slug, self.curso.codigo])
        with connection.execute_wrapper(registrar):
            respuesta = self.client.get(destino, {'edicion': self.grupo.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.otro_grupo.nombre)
        self.assertEqual(respuesta.context['seguimiento']['avance']['completadas'], 0)
        self.assertEqual(len(sql), 4)
        for consulta, parametros in sql:
            self.assertEqual(tuple(parametros), (self.inscripcion.pk,), consulta)
