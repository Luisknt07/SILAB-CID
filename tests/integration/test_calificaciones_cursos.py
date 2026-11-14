"""Evaluaciones y deberes de los cursos: preguntas que se califican solas con nota mínima e intentos, entregas que
califica el instructor, y solo lo aprobado cuenta como lección completada."""
import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, PreguntaEvaluacion, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-calificaciones-')


@override_settings(MEDIA_ROOT=MEDIOS)
class CalificacionesDeCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-notas', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-notas', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-notas', 'luis@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con notas', slug='lab-notas', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LN-CUR-001', nombre='Electrónica', publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        cls.otra = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.luis, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Fundamentos')
        cls.evaluacion = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Prueba de Ohm', tipo='evaluacion',
                                                     nota_minima=70, intentos=2)
        cls.unica = PreguntaEvaluacion.objects.create(leccion=cls.evaluacion, orden=1, enunciado='2 + 2', opciones='*4\n5',
                                                      explicacion='Suma directa.')
        cls.multiple = PreguntaEvaluacion.objects.create(leccion=cls.evaluacion, orden=2, enunciado='Son conductores',
                                                         tipo='multiple', opciones='*Cobre\n*Aluminio\nVidrio')
        cls.corta = PreguntaEvaluacion.objects.create(leccion=cls.evaluacion, orden=3, enunciado='¿Qué ley es V = IR?',
                                                      tipo='corta', respuestas_aceptadas='Ley de Ohm\nOhm')
        cls.deber = LeccionCurso.objects.create(modulo=modulo, orden=2, titulo='Circuito en protoboard', tipo='deber',
                                                nota_minima=70)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def test_rollback_al_reemplazar_entrega_conserva_archivo_anterior(self):
        entrega = EntregaDeber.objects.create(
            leccion=self.deber, inscripcion=self.inscripcion,
            archivo=SimpleUploadedFile('deber.pdf', b'%PDF-1.4 entrega anterior', content_type='application/pdf'))
        anterior, almacen = entrega.archivo.name, entrega.archivo.storage
        self.client.force_login(self.ana)
        with self.assertRaisesMessage(RuntimeError, 'Rollback de la operación exterior'):
            with transaction.atomic():
                respuesta = self.client.post(self.url('entregar_deber', self.deber.pk), {
                    'archivo': SimpleUploadedFile('deber.pdf', b'%PDF-1.4 reemplazo', content_type='application/pdf')})
                self.assertEqual(respuesta.status_code, 302)
                entrega.refresh_from_db()
                self.assertNotEqual(entrega.archivo.name, anterior)
                raise RuntimeError('Rollback de la operación exterior')
        entrega.refresh_from_db()
        self.assertEqual(entrega.archivo.name, anterior)
        self.assertTrue(almacen.exists(anterior))
        with almacen.open(anterior, 'rb') as original:
            self.assertEqual(original.read(), b'%PDF-1.4 entrega anterior')

    def test_reemplazo_borra_archivo_anterior_solo_despues_del_commit(self):
        entrega = EntregaDeber.objects.create(
            leccion=self.deber, inscripcion=self.inscripcion,
            archivo=SimpleUploadedFile('deber.pdf', b'%PDF-1.4 entrega anterior', content_type='application/pdf'))
        anterior, almacen = entrega.archivo.name, entrega.archivo.storage
        self.client.force_login(self.ana)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            respuesta = self.client.post(self.url('entregar_deber', self.deber.pk), {
                'archivo': SimpleUploadedFile('deber.pdf', b'%PDF-1.4 reemplazo', content_type='application/pdf')})
            self.assertEqual(respuesta.status_code, 302)
            entrega.refresh_from_db()
            self.assertNotEqual(entrega.archivo.name, anterior)
            self.assertTrue(almacen.exists(anterior))
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(almacen.exists(anterior))
        with entrega.archivo.open('rb') as actual:
            self.assertEqual(actual.read(), b'%PDF-1.4 reemplazo')

    def rendir(self, respuestas):
        return self.client.post(self.url('rendir_evaluacion', self.evaluacion.pk), respuestas)

    def test_la_evaluacion_se_califica_sola_con_nota_minima_e_intentos(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk)), 'Enviar mis respuestas')
        self.rendir({f'p{self.unica.pk}': '0', f'p{self.multiple.pk}': ['0'], f'p{self.corta.pk}': 'Kirchhoff'})
        primero = IntentoEvaluacion.objects.get()
        self.assertEqual((primero.nota, primero.aprobado), (Decimal('33.33'), False))
        aula = self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk))
        self.assertEqual(aula.context['evaluacion']['restantes'], 1)
        self.assertFalse(aula.context['evaluacion']['revelar'])
        self.assertContains(aula, 'Enviar otro intento')
        self.rendir({f'p{self.unica.pk}': '0', f'p{self.multiple.pk}': ['0', '1'], f'p{self.corta.pk}': '  LEY DE ÓHM '})
        self.rendir({f'p{self.unica.pk}': '1'})
        self.assertEqual(list(IntentoEvaluacion.objects.values_list('nota', 'aprobado')),
                         [(Decimal('100.00'), True), (Decimal('33.33'), False)])
        self.assertTrue(ProgresoLeccion.objects.filter(inscripcion=self.inscripcion, leccion=self.evaluacion).exists())
        aula = self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk))
        self.assertTrue(aula.context['evaluacion']['revelar'])
        self.assertContains(aula, 'Suma directa.')
        self.client.post(self.url('completar_leccion', self.deber.pk))
        self.assertFalse(ProgresoLeccion.objects.filter(leccion=self.deber).exists())

    def test_la_evaluacion_vencida_no_se_rinde_y_las_preguntas_se_validan(self):
        LeccionCurso.objects.filter(pk=self.evaluacion.pk).update(fecha_limite=timezone.now() - timedelta(hours=1))
        self.client.force_login(self.ana)
        self.rendir({f'p{self.unica.pk}': '0'})
        self.assertFalse(IntentoEvaluacion.objects.exists())
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk)), 'El plazo de esta evaluación terminó.')
        self.client.force_login(self.admin)
        nueva = reverse('editar_registro', args=[self.lab.slug, 'pregunta_curso', 'nuevo'])
        for opciones, error in (('*a\n*b', 'marque solo una opción'), ('a\nb', 'Marque con * al inicio'), ('*a', 'al menos dos opciones')):
            with self.subTest(opciones=opciones):
                respuesta = self.client.post(nueva, {'padre': self.evaluacion.pk, 'registro-orden': '4', 'registro-tipo': 'unica',
                                                     'registro-enunciado': 'Otra', 'registro-opciones': opciones,
                                                     'registro-puntos': '1'})
                self.assertContains(respuesta, error)
        aula = self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk))
        self.assertContains(aula, 'Nueva pregunta')
        self.assertContains(aula, 'calificada__opcion is-correcta')

    def test_el_deber_lo_califica_el_instructor_y_puede_devolverlo(self):
        self.client.force_login(self.ana)
        entregar = self.url('entregar_deber', self.deber.pk)
        self.assertContains(self.client.post(entregar, {'comentario': 'Sin archivo'}),
                            'Suba el archivo del trabajo o escriba el enlace donde está.')
        self.client.post(entregar, {'archivo': SimpleUploadedFile('circuito.pdf', b'%PDF-1.4 c', content_type='application/pdf'),
                                    'comentario': 'Primera versión'})
        entrega = EntregaDeber.objects.get()
        self.assertEqual(entrega.estado, 'entregada')
        self.client.force_login(self.admin)
        calificaciones = self.url('calificaciones_curso')
        self.assertEqual(list(self.client.get(calificaciones).context['por_revisar']), [entrega])
        self.client.post(calificaciones, {'entrega': entrega.pk, 'accion': 'calificar', 'nota': '60',
                                          'retroalimentacion': 'Falta la resistencia de carga.'})
        entrega.refresh_from_db()
        self.assertEqual((entrega.estado, entrega.nota), ('devuelta', Decimal('60.00')))
        self.assertFalse(ProgresoLeccion.objects.filter(leccion=self.deber).exists())
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.deber.pk)), 'Falta la resistencia de carga.')
        self.client.post(entregar, {'enlace': 'https://example.org/circuito'})
        entrega.refresh_from_db()
        self.assertEqual((entrega.estado, entrega.nota, bool(entrega.archivo)), ('entregada', None, True))
        self.client.force_login(self.admin)
        self.client.post(calificaciones, {'entrega': entrega.pk, 'accion': 'calificar', 'nota': '90'})
        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, 'aprobada')
        self.assertEqual(ProgresoLeccion.objects.get(leccion=self.deber).registrada_por, self.admin)
        libro = self.client.get(calificaciones).context['inscritos']
        notas = {inscrito.usuario.username: inscrito.notas for inscrito in libro}
        self.assertEqual(notas['ana-notas'][1]['nota'], Decimal('90.00'))
        self.client.force_login(self.ana)
        self.client.post(entregar, {'enlace': 'https://example.org/otro'})
        entrega.refresh_from_db()
        self.assertEqual(entrega.enlace, 'https://example.org/circuito')

    def test_la_entrega_solo_la_ven_quien_la_hizo_y_quien_califica(self):
        entrega = EntregaDeber.objects.create(inscripcion=self.inscripcion, leccion=self.deber,
                                              archivo=SimpleUploadedFile('t.pdf', b'%PDF-1.4 t', content_type='application/pdf'))
        url = self.url('archivo_entrega', entrega.pk)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get('/media/' + entrega.archivo.name).status_code, 404)
        for persona in (self.ana, self.admin):
            self.client.force_login(persona)
            self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(self.url('calificaciones_curso')).status_code, 403)
