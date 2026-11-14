"""Certificados de los cursos: se emiten solos al cumplir todo, guardan lo que certifican, se descargan en PDF con QR
y cualquiera los verifica por su código; la unidad puede anularlos con un motivo."""
import re
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


class CertificadosDeCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-cert', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-cert', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-cert', 'luis@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio certificador', slug='lab-cert', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        ResponsableUnidad.objects.create(unidad=cls.lab, nombre='María Paredes', rol='coordinacion')
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LC-CUR-010', nombre='Impresión 3D', publicado=True,
                                         clasificacion='corto', duracion_horas=20)
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year,
                                                 inicio=timezone.localdate(), fin=timezone.localdate())
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Único')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Lectura', tipo='texto')
        cls.evaluacion = LeccionCurso.objects.create(modulo=modulo, orden=2, titulo='Prueba', tipo='evaluacion', nota_minima=60)
        cls.pregunta = PreguntaEvaluacion.objects.create(leccion=cls.evaluacion, enunciado='2 + 2', opciones='*4\n5')
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.ana, estado='aceptada')

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def aprobar(self):
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        self.assertFalse(CertificadoCurso.objects.exists())
        self.client.post(self.url('rendir_evaluacion', self.evaluacion.pk), {f'p{self.pregunta.pk}': '0'})
        return CertificadoCurso.objects.get()

    def test_se_emite_solo_al_aprobar_y_guarda_lo_que_certifica(self):
        certificado = self.aprobar()
        self.assertRegex(certificado.codigo, r'^CERT-[A-Z2-9]{4}-[A-Z2-9]{4}$')
        self.assertEqual((certificado.tipo, certificado.nombre, certificado.horas, certificado.nota_final,
                          certificado.firma_nombre, certificado.firma_cargo),
                         ('aprobacion', 'Ana Ríos', 20, Decimal('100.00'), 'María Paredes',
                          'Coordinación de Laboratorio certificador'))
        Curso.objects.filter(pk=self.curso.pk).update(nombre='Otro nombre')
        certificado.refresh_from_db()
        self.assertEqual(certificado.curso_nombre, 'Impresión 3D')
        aula = self.client.get(self.url('aula_curso'))
        self.assertContains(aula, self.url('mi_certificado'))
        pdf = self.client.get(self.url('mi_certificado'))
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(self.url('mi_certificado')).status_code, 404)

    def test_sin_evaluaciones_es_de_participacion_y_sin_certificado_no_se_emite(self):
        LeccionCurso.objects.filter(pk=self.evaluacion.pk).update(obligatoria=False)
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        certificado = CertificadoCurso.objects.get()
        self.assertEqual((certificado.tipo, certificado.nota_final), ('participacion', None))
        certificado.delete()
        Curso.objects.filter(pk=self.curso.pk).update(emite_certificado=False)
        self.assertEqual(self.client.get(self.url('mi_certificado')).status_code, 404)
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_el_deber_aprobado_por_el_instructor_emite_el_certificado(self):
        LeccionCurso.objects.filter(pk=self.evaluacion.pk).update(tipo='deber')
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        entrega = EntregaDeber.objects.create(inscripcion=self.inscripcion, leccion=self.evaluacion,
                                              enlace='https://example.org/t')
        self.client.force_login(self.admin)
        self.client.post(self.url('calificaciones_curso'), {'entrega': entrega.pk, 'accion': 'calificar', 'nota': '80'})
        self.assertEqual(CertificadoCurso.objects.get().nota_final, Decimal('80.00'))

    def test_cualquiera_lo_verifica_por_su_codigo_y_la_unidad_lo_anula(self):
        certificado = self.aprobar()
        self.client.logout()
        verificar = reverse('verificar_certificado', args=[certificado.codigo])
        pagina = self.client.get(verificar)
        self.assertContains(pagina, 'Certificado auténtico y vigente')
        self.assertContains(pagina, 'Ana Ríos')
        self.assertTrue(self.client.get(verificar, {'formato': 'pdf'}).content.startswith(b'%PDF'))
        buscar = reverse('verificar_certificado_buscar')
        self.assertContains(self.client.get(buscar, {'codigo': certificado.codigo.lower()}), 'Certificado auténtico')
        self.assertContains(self.client.get(buscar, {'codigo': 'CERT-AAAA-AAAA'}), 'No existe un certificado', status_code=404)
        anular = self.url('anular_certificado', certificado.pk)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.post(anular, {'motivo': 'x'}).status_code, 403)
        self.client.force_login(self.admin)
        inscritos = self.client.get(self.url('inscritos_curso'))
        self.assertContains(inscritos, certificado.codigo)
        self.client.post(anular, {'motivo': 'Se emitió a la persona equivocada.'})
        self.client.logout()
        pagina = self.client.get(verificar)
        self.assertContains(pagina, 'Certificado anulado')
        self.assertContains(pagina, 'Se emitió a la persona equivocada.')
        self.assertNotContains(pagina, 'formato=pdf')
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url('mi_certificado')).status_code, 404)

    def test_la_asistencia_registrada_tambien_completa_el_curso(self):
        LeccionCurso.objects.filter(pk=self.evaluacion.pk).update(tipo='en_vivo')
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        self.client.force_login(self.admin)
        self.client.post(self.url('inscritos_curso'), {'accion': 'asistencia', 'inscripcion': self.inscripcion.pk,
                                                       'leccion': self.evaluacion.pk, 'asistio': '1'})
        self.assertEqual(CertificadoCurso.objects.get().tipo, 'participacion')
        self.assertTrue(re.match(r'^CERT-', CertificadoCurso.objects.get().codigo))
