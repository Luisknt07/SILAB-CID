"""Los cursos precargados (Bambu Lab, Fusion, Odoo) se cargan completos con la estructura estándar, no se duplican al repetir
la orden, sus preguntas son válidas y se recorren enteros hasta el certificado."""
import shutil
import tempfile
from datetime import date
from importlib import import_module
from io import StringIO
from zipfile import is_zipfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.formacion.management.commands.cargar_curso_precargado import CURSOS
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, PreguntaEvaluacion
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-precargados-')


@override_settings(MEDIA_ROOT=MEDIOS)
class CursosPrecargadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lab = Unidad.objects.create(nombre='Laboratorio de Fabricación Digital', slug='lab-precargados',
                                        dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.ana = get_user_model().objects.create_user('ana-pre', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.admin = get_user_model().objects.create_superuser('admin-pre', 'a@example.org', 'clave')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def cargar(self, nombre, *extra):
        salida = StringIO()
        call_command('cargar_curso_precargado', nombre, '--unidad', self.lab.slug, *extra, stdout=salida)
        return salida.getvalue()

    def test_cada_curso_se_carga_completo_con_la_estructura_estandar(self):
        for nombre, (modulo, _unidad) in CURSOS.items():
            with self.subTest(curso=nombre):
                datos = import_module(f'apps.formacion.management.cursos_precargados.{modulo}')
                self.assertIn('Simulación', self.cargar(nombre, '--simular'))
                self.assertFalse(Curso.objects.filter(nombre=datos.CURSO['nombre']).exists())
                self.cargar(nombre)
                curso = Curso.objects.get(nombre=datos.CURSO['nombre'])
                lecciones = LeccionCurso.objects.filter(modulo__curso=curso)
                esperadas = sum(len(lista) for _titulo, _descripcion, lista in datos.MODULOS)
                self.assertEqual((curso.modulos.count(), lecciones.count()), (len(datos.MODULOS), esperadas))
                self.assertFalse(curso.publicado)
                self.assertTrue(all(leccion.video_id or leccion.archivo for leccion in lecciones.filter(tipo='video')))
                # Estándar: cada módulo cierra con una actividad calificada y el último con la evaluación final.
                for _titulo, _descripcion, lista in datos.MODULOS[1:]:
                    self.assertTrue(any(tipo in ('evaluacion', 'deber', 'en_vivo') for tipo, _t, _d in lista))
                self.assertEqual(datos.MODULOS[-1][2][-1][0], 'evaluacion')
                for pregunta in PreguntaEvaluacion.objects.filter(leccion__modulo__curso=curso):
                    pregunta.full_clean()
                for guia in lecciones.filter(tipo='material').exclude(archivo=''):
                    if guia.archivo.name.endswith('.zip'):
                        self.assertTrue(is_zipfile(guia.archivo))
                    else:
                        self.assertEqual(guia.archivo.read(4), b'%PDF')
                self.assertIn('nada nuevo', self.cargar(nombre))
                sobrante = LeccionCurso.objects.create(modulo=curso.modulos.first(), orden=99, titulo='Retirar', tipo='texto')
                self.assertIn('lecciones retiradas', self.cargar(nombre))
                self.assertFalse(LeccionCurso.objects.filter(pk=sobrante.pk).exists())

    def test_cada_curso_se_recorre_entero_hasta_el_certificado(self):
        for nombre, (modulo, _unidad) in CURSOS.items():
            with self.subTest(curso=nombre):
                datos = import_module(f'apps.formacion.management.cursos_precargados.{modulo}')
                self.cargar(nombre)
                curso = Curso.objects.get(nombre=datos.CURSO['nombre'])
                # La certificación se habilita explícitamente sólo en esta convocatoria sintética.
                Curso.objects.filter(pk=curso.pk).update(publicado=True, emite_certificado=True)
                edicion = EdicionCurso.objects.get(curso=curso)
                # La carga editorial no inventa fechas: el gestor configura una
                # convocatoria sintética antes de acreditar el curso en esta prueba.
                edicion.inicio = edicion.inicio or date(2026, 10, 1)
                edicion.fin = edicion.fin or date(2026, 10, 31)
                edicion.horas_certificadas = curso.duracion_horas
                edicion.save(update_fields=['inicio', 'fin', 'horas_certificadas'])
                inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=self.ana, estado='aceptada')
                self.recorrer(curso, inscripcion)
                certificado = CertificadoCurso.objects.get(inscripcion=inscripcion)
                self.assertEqual((certificado.tipo, certificado.horas), ('aprobacion', datos.CURSO['duracion_horas']))

    def recorrer(self, curso, inscripcion):
        base = [self.lab.slug, curso.codigo]
        for leccion in LeccionCurso.objects.filter(modulo__curso=curso, obligatoria=True).order_by('modulo__orden', 'orden'):
            if leccion.tipo in ('texto', 'video', 'material'):
                self.client.force_login(self.ana)
                self.client.post(reverse('completar_leccion', args=[*base, leccion.pk]))
            elif leccion.tipo == 'evaluacion':
                self.client.force_login(self.ana)
                respuestas = {}
                for pregunta in leccion.preguntas.all():
                    respuestas[f'p{pregunta.pk}'] = (pregunta.respuestas_aceptadas.splitlines()[0] if pregunta.tipo == 'corta'
                                                     else [str(i) for i, (_t, correcta) in enumerate(pregunta.lista_opciones) if correcta])
                self.client.post(reverse('rendir_evaluacion', args=[*base, leccion.pk]), respuestas)
                self.assertTrue(leccion.intentos_rendidos.filter(aprobado=True).exists(), leccion.titulo)
            elif leccion.tipo == 'deber':
                self.client.force_login(self.ana)
                self.client.post(reverse('entregar_deber', args=[*base, leccion.pk]), {'enlace': 'https://example.org/t'})
                self.client.force_login(self.admin)
                self.client.post(reverse('calificaciones_curso', args=base),
                                 {'entrega': leccion.entregas.get().pk, 'accion': 'calificar', 'nota': '95'})
            else:
                self.client.force_login(self.admin)
                self.client.post(reverse('inscritos_curso', args=base), {'accion': 'asistencia', 'inscripcion': inscripcion.pk,
                                                                         'leccion': leccion.pk, 'asistio': '1'})
