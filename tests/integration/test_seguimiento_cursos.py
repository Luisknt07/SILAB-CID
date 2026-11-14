"""Notas /10 e informes por cohorte: exactitud, historial y permisos privados."""
import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.formacion.presentation.notas_cursos import nota_desde_diez, nota_sobre_diez
from apps.formacion.presentation.seguimiento_cursos import seguimiento_curso_view, seguimiento_de, seguimiento_participante_view
from apps.gestion_unidades.presentation.seguimiento_reportes import celda_csv_segura
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, PreguntaEvaluacion, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad


class EscalaNotasTests(SimpleTestCase):
    def test_conversion_exacta_no_redondea_hasta_la_aprobacion(self):
        for almacenada, publica in (('0.00', '0'), ('69.99', '6.999'), ('70.00', '7'), ('100.00', '10')):
            with self.subTest(nota=almacenada):
                self.assertEqual(nota_sobre_diez(Decimal(almacenada)), Decimal(publica))
                self.assertEqual(nota_desde_diez(publica), Decimal(almacenada))
        self.assertEqual(nota_desde_diez(' 7,25 '), Decimal('72.50'))
        self.assertIsNone(nota_sobre_diez(None))

    def test_entrada_rechaza_valores_no_finitos_fuera_de_rango_y_precision_perdida(self):
        for valor in ('NaN', 'sNaN', 'Infinity', '-Infinity', '-0.001', '10.001', '6.9999', '', 'abc', '1e99999'):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                nota_desde_diez(valor)
        for valor in ('NaN', 'Infinity', '101', '-1', 'abc'):
            self.assertIsNone(nota_sobre_diez(valor))

    def test_csv_neutraliza_formulas_tras_blancos_y_controles(self):
        for valor in ('=1+1', '+SUM(A1)', '-2+3', '@SUM(A1)', '  =1+1', '\t=1+1', '\rnombre', '\nnombre'):
            with self.subTest(valor=valor):
                self.assertTrue(celda_csv_segura(valor).startswith("'"))
        self.assertEqual(celda_csv_segura('Ana Ríos'), 'Ana Ríos')
        self.assertEqual(celda_csv_segura(Decimal('7.25')), '7.25')


class SeguimientoCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-seguimiento', 'admin@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-seguimiento', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-seguimiento', 'luis@example.org', 'clave', first_name='Luis')
        cls.lab = Unidad.objects.create(nombre='Laboratorio de seguimiento', slug='lab-seguimiento',
            dependencia='laboratorios', descripcion='Prueba', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='SEG-CUR-001', nombre='Aplicaciones logísticas',
                                         publicado=True, emite_certificado=False)
        cls.grupo_a = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=2026)
        cls.grupo_b = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo B', anio=2026)
        cls.grupo_c = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo C', anio=2026)
        cls.ana_a = InscripcionCurso.objects.create(edicion=cls.grupo_a, usuario=cls.ana, estado='aceptada')
        cls.ana_b = InscripcionCurso.objects.create(edicion=cls.grupo_b, usuario=cls.ana, estado='aceptada')
        cls.luis_a = InscripcionCurso.objects.create(edicion=cls.grupo_a, usuario=cls.luis, estado='aceptada')
        cls.luis_c = InscripcionCurso.objects.create(edicion=cls.grupo_c, usuario=cls.luis, estado='aceptada')
        cls.modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Inventario')
        cls.lectura = LeccionCurso.objects.create(modulo=cls.modulo, orden=1, titulo='Proceso', tipo='texto')
        cls.examen = LeccionCurso.objects.create(modulo=cls.modulo, orden=2, titulo='Quiz de inventario',
                                                tipo='evaluacion', nota_minima=70, intentos=3)
        cls.pregunta = PreguntaEvaluacion.objects.create(leccion=cls.examen, enunciado='Salida mayor que stock',
                                                        opciones='*Rechazar\nPermitir')
        cls.deber = LeccionCurso.objects.create(modulo=cls.modulo, orden=3, titulo='Aplicación final',
                                               tipo='deber', nota_minima=70)

    def url(self, nombre, *extra, edicion=None):
        destino = reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])
        return destino + f'?edicion={edicion.pk}' if edicion else destino

    def personal(self, usuario=None, **consulta):
        request = RequestFactory().get('/seguimiento/', consulta)
        request.user = usuario or self.ana
        return seguimiento_curso_view(request, self.lab.slug, self.curso.codigo)

    def intento(self, inscripcion, nota, aprobado=False):
        return IntentoEvaluacion.objects.create(inscripcion=inscripcion, leccion=self.examen,
                                                nota=Decimal(nota), aprobado=aprobado)

    def test_los_grupos_no_comparten_avance_notas_ni_oportunidades(self):
        ProgresoLeccion.objects.create(inscripcion=self.ana_a, leccion=self.lectura)
        self.intento(self.ana_a, '69.99')
        self.intento(self.ana_a, '80.00', True)
        ProgresoLeccion.objects.create(inscripcion=self.ana_a, leccion=self.examen)
        primero, segundo = seguimiento_de(self.ana_a), seguimiento_de(self.ana_b)
        self.assertEqual(primero['avance']['completadas'], 2)
        self.assertEqual(segundo['avance']['completadas'], 0)
        self.assertEqual([fila['nota_10'] for fila in primero['calificadas'][0]['intentos']],
                         [Decimal('6.999'), Decimal('8')])
        self.assertEqual(segundo['calificadas'][0]['intentos'], [])
        self.assertEqual(segundo['calificadas'][0]['restantes'], 3)
        pagina = self.personal(edicion=self.grupo_a.pk)
        self.assertContains(pagina, '6,999 / 10')
        self.assertIn('no-store', pagina['Cache-Control'])
        self.assertIn('private', pagina['Cache-Control'])
        self.assertContains(pagina, f'edicion={self.grupo_a.pk}')
        self.assertNotContains(self.personal(edicion=self.grupo_b.pk), '6,999 / 10')

    def test_mantiene_aprobacion_historica_y_clasifica_agotados(self):
        self.intento(self.ana_a, '70.00', True)
        LeccionCurso.objects.filter(pk=self.examen.pk).update(nota_minima=80)
        self.assertTrue(seguimiento_de(self.ana_a)['calificadas'][0]['aprobado'])
        for _ in range(3):
            self.intento(self.luis_a, '0')
        resumen = seguimiento_de(self.luis_a)
        self.assertEqual(resumen['estado'], 'reprobado')
        self.assertEqual(resumen['oportunidades'], 0)
        self.assertEqual(resumen['calificadas'][0]['restantes'], 0)
        EntregaDeber.objects.create(inscripcion=self.ana_b, leccion=self.deber,
            enlace='https://example.org/trabajo', estado='devuelta', nota=Decimal('60.00'))
        resumen = seguimiento_de(self.ana_b)
        self.assertEqual(resumen['estado'], 'pendiente')
        self.assertEqual(resumen['calificadas'][1]['rotulo'], 'Corregir y volver a entregar')

    def test_personal_solo_propias_y_login_sin_conceder_acceso_por_otro_grupo(self):
        with self.assertRaises(Http404):
            self.personal(edicion=self.grupo_c.pk)
        with self.assertRaises(Http404):
            self.personal(edicion='no-es-un-id')
        with self.assertRaises(Http404):
            self.personal(usuario=self.admin, edicion=self.grupo_a.pk)
        request = RequestFactory().get('/seguimiento/')
        request.user = AnonymousUser()
        self.assertEqual(seguimiento_curso_view(request, self.lab.slug, self.curso.codigo).status_code, 302)

    def test_reporte_historico_sigue_disponible_en_retirada_curso_borrador_unidad_inactiva(self):
        self.intento(self.ana_a, '80.00', True)
        InscripcionCurso.objects.filter(pk=self.ana_a.pk).update(estado='retirada')
        Curso.objects.filter(pk=self.curso.pk).update(publicado=False)
        Unidad.objects.filter(pk=self.lab.pk).update(activo=False)
        pagina = self.personal(edicion=self.grupo_a.pk)
        self.assertContains(pagina, 'Retirado')
        self.assertContains(pagina, '8 / 10')
        self.assertNotContains(pagina, 'Volver al aula')
        self.assertContains(pagina, reverse('mi_formacion'))
        self.assertContains(pagina, 'Mi formación')
        pdf = self.personal(edicion=self.grupo_a.pk, formato='pdf')
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertGreater(len(pdf.content), 3000)
        self.assertIn('private', pdf['Cache-Control'])
        self.assertIn('no-store', pdf['Cache-Control'])
        self.assertEqual(pdf['X-Content-Type-Options'], 'nosniff')
        with patch('apps.gestion_unidades.presentation.seguimiento_reportes.pdf_del_seguimiento') as generar:
            with self.assertRaises(Http404):
                self.personal(edicion=self.grupo_c.pk, formato='pdf')
            generar.assert_not_called()

    def test_califica_sobre_diez_sin_cambiar_historico_y_muestra_errores(self):
        entrega = EntregaDeber.objects.create(inscripcion=self.ana_a, leccion=self.deber, enlace='https://example.org/a')
        self.client.force_login(self.admin)
        destino = self.url('calificaciones_curso', edicion=self.grupo_a)
        self.client.post(destino, {'entrega': entrega.pk, 'accion': 'calificar', 'nota_sobre_10': '6,999'})
        entrega.refresh_from_db()
        self.assertEqual((entrega.nota, entrega.estado), (Decimal('69.99'), 'devuelta'))
        self.client.post(destino, {'entrega': entrega.pk, 'accion': 'calificar', 'nota_sobre_10': '7'})
        entrega.refresh_from_db()
        self.assertEqual((entrega.nota, entrega.estado), (Decimal('70.00'), 'aprobada'))
        for invalida in ('NaN', 'Infinity', '10.1', '-1', '6.9999', ''):
            with self.subTest(nota=invalida):
                pagina = self.client.post(destino, {'entrega': entrega.pk, 'accion': 'calificar',
                                                    'nota_sobre_10': invalida, 'nota': '100'})
                self.assertContains(pagina, 'Escriba una nota entre 0 y 10')
                entrega.refresh_from_db()
                self.assertEqual(entrega.nota, Decimal('70.00'))
        self.client.post(destino, {'entrega': entrega.pk, 'accion': 'calificar', 'nota': '85'})
        entrega.refresh_from_db()
        self.assertEqual(entrega.nota, Decimal('85.00'))

    def test_gestor_filtra_estado_e_intentos_y_exporta_solo_grupo_autorizado(self):
        for leccion in (self.lectura, self.examen, self.deber):
            ProgresoLeccion.objects.create(inscripcion=self.ana_a, leccion=leccion)
        self.intento(self.ana_a, '90.00', True)
        for _ in range(3):
            self.intento(self.luis_a, '20.00')
        self.intento(self.ana_b, '60.00')
        self.client.force_login(self.admin)
        destino = self.url('calificaciones_curso', edicion=self.grupo_a)
        pagina = self.client.get(destino, {'estado': 'reprobado', 'intentos': 'agotados', 'edicion': self.grupo_a.pk})
        self.assertEqual([inscrito.pk for inscrito in pagina.context['inscritos']], [self.luis_a.pk])
        self.assertIn('no-store', pagina['Cache-Control'])
        self.assertIn('private', pagina['Cache-Control'])
        self.assertEqual(pagina.context['totales'], {'aprobado': 1, 'reprobado': 1, 'pendiente': 0})
        csv = self.client.get(destino, {'formato': 'csv', 'estado': 'reprobado', 'edicion': self.grupo_a.pk})
        self.assertEqual(csv['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('private', csv['Cache-Control'])
        self.assertIn('no-store', csv['Cache-Control'])
        filas = list(__import__('csv').reader(io.StringIO(csv.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(filas), 5)  # cabecera, tres intentos y el deber pendiente de Luis
        self.assertTrue(all(fila[2] == 'Grupo A' for fila in filas[1:]))
        self.assertTrue(all(fila[3] == 'Luis' for fila in filas[1:]))
        self.assertEqual([fila[12] for fila in filas[1:4]], ['1', '2', '3'])
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(destino, {'formato': 'csv'}).status_code, 403)

    def test_csv_desactiva_formula_en_nombres_y_actividades(self):
        get_user_model().objects.filter(pk=self.ana.pk).update(first_name='=1+1', last_name='')
        InscripcionCurso.objects.filter(pk=self.ana_a.pk).update(nombres_completos='=1+1')
        LeccionCurso.objects.filter(pk=self.examen.pk).update(titulo=' @SUM(A1)')
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.url('calificaciones_curso', edicion=self.grupo_a),
                                   {'formato': 'csv', 'q': '=1+1', 'edicion': self.grupo_a.pk})
        filas = list(csv.reader(io.StringIO(respuesta.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(filas[1][3], "'=1+1")
        self.assertEqual(filas[1][7], "' @SUM(A1)")

    def test_calificar_otro_grupo_y_sin_csrf_no_modifica_la_entrega(self):
        entrega = EntregaDeber.objects.create(inscripcion=self.ana_b, leccion=self.deber, enlace='https://example.org/b')
        self.client.force_login(self.admin)
        respuesta = self.client.post(self.url('calificaciones_curso', edicion=self.grupo_a),
            {'entrega': entrega.pk, 'accion': 'calificar', 'nota_sobre_10': '10'})
        self.assertEqual(respuesta.status_code, 404)
        entrega.refresh_from_db()
        self.assertIsNone(entrega.nota)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.admin)
        self.assertEqual(protegido.post(self.url('calificaciones_curso', edicion=self.grupo_b),
            {'entrega': entrega.pk, 'accion': 'calificar', 'nota_sobre_10': '10'}).status_code, 403)

    def test_cupo_de_intentos_configurable_y_nota_no_acepta_override_frontend(self):
        ProgresoLeccion.objects.create(inscripcion=self.ana_a, leccion=self.lectura)
        self.client.force_login(self.ana)
        destino = self.url('rendir_evaluacion', self.examen.pk, edicion=self.grupo_a)
        for _ in range(4):
            self.client.post(destino, {f'p{self.pregunta.pk}': '1', 'nota': '100', 'aprobado': 'true'})
        self.assertEqual(IntentoEvaluacion.objects.filter(inscripcion=self.ana_a).count(), 3)
        self.assertFalse(IntentoEvaluacion.objects.filter(inscripcion=self.ana_a, aprobado=True).exists())
        self.assertFalse(IntentoEvaluacion.objects.filter(inscripcion=self.ana_b).exists())
        self.assertFalse(ProgresoLeccion.objects.filter(inscripcion=self.ana_a, leccion=self.examen).exists())
        LeccionCurso.objects.filter(pk=self.examen.pk).update(intentos=4)
        self.client.post(destino, {f'p{self.pregunta.pk}': '0'})
        self.assertTrue(IntentoEvaluacion.objects.filter(inscripcion=self.ana_a, aprobado=True).exists())
        self.assertEqual(IntentoEvaluacion.objects.filter(inscripcion=self.ana_a).count(), 4)

    def test_certificado_vigente_bloquea_recalificar_sin_borrar_nota_progreso_ni_certificado(self):
        entrega = EntregaDeber.objects.create(inscripcion=self.ana_a, leccion=self.deber,
            enlace='https://example.org/aprobado', estado='aprobada', nota=Decimal('80.00'),
            retroalimentacion='Trabajo aprobado.')
        progreso = ProgresoLeccion.objects.create(inscripcion=self.ana_a, leccion=self.deber)
        certificado = CertificadoCurso.objects.create(inscripcion=self.ana_a, codigo='CERT-TEST-SEG1',
            nombre='Ana Ríos', curso_nombre=self.curso.nombre, clasificacion='Curso corto',
            edicion=self.grupo_a.nombre, unidad_nombre=self.lab.nombre, nota_final=Decimal('80.00'))
        self.client.force_login(self.admin)
        for accion in ('calificar', 'devolver'):
            with self.subTest(accion=accion):
                pagina = self.client.post(self.url('calificaciones_curso', edicion=self.grupo_a),
                    {'entrega': entrega.pk, 'accion': accion, 'nota_sobre_10': '2',
                     'retroalimentacion': 'No debe guardarse.'})
                self.assertContains(pagina, 'Esta entrega sustenta un certificado vigente')
                entrega.refresh_from_db()
                certificado.refresh_from_db()
                self.assertEqual((entrega.estado, entrega.nota, entrega.retroalimentacion),
                                 ('aprobada', Decimal('80.00'), 'Trabajo aprobado.'))
                self.assertTrue(ProgresoLeccion.objects.filter(pk=progreso.pk).exists())
                self.assertFalse(certificado.anulado)
                self.assertEqual(certificado.nota_final, Decimal('80.00'))

    def test_gestor_consulta_participante_exacto_y_rechaza_otro_curso(self):
        request = RequestFactory().get('/participante/reporte/')
        request.user = self.admin
        respuesta = seguimiento_participante_view(request, self.lab.slug, self.curso.codigo, self.ana_a.pk)
        self.assertContains(respuesta, 'Seguimiento del participante')
        self.assertContains(respuesta, 'Ana Ríos')
        self.assertContains(respuesta, 'Grupo A')
        self.assertNotContains(respuesta, 'Ver grupo')
        otro_curso = Curso.objects.create(unidad=self.lab, codigo='SEG-OTRO', nombre='Otro curso', publicado=True)
        otro_grupo = EdicionCurso.objects.create(curso=otro_curso, nombre='Otro grupo', anio=2026)
        otra_inscripcion = InscripcionCurso.objects.create(edicion=otro_grupo, usuario=self.ana, estado='aceptada')
        with self.assertRaises(Http404):
            seguimiento_participante_view(request, self.lab.slug, self.curso.codigo, otra_inscripcion.pk)
        request.user = self.ana
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            seguimiento_participante_view(request, self.lab.slug, self.curso.codigo, self.ana_a.pk)
