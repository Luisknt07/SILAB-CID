"""Correcciones de la auditoría de los cursos: fechas de las ediciones, reinscripción, pagos y matrícula, certificados
reemitibles y sin cédula en lo público, evaluaciones que no se aprueban probando, comentarios y entradas inválidas."""
import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.certificados_cursos import firmante_de
from apps.formacion.models.cursos import CertificadoCurso, ComentarioLeccion, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.formacion.models.cursos_inscripcion import CodigoDescuento, PagoInscripcion
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-auditoria-')
HOY = date(2026, 10, 4)


@override_settings(MEDIA_ROOT=MEDIOS)
class AuditoriaDeCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-aud2', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-aud2', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.lab = Unidad.objects.create(nombre='Laboratorio auditado', slug='lab-aud2', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='AU-CUR-001', nombre='Curso auditado', publicado=True,
                                         inscripcion='abierta')
        hoy = timezone.localdate()
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Vigente', anio=hoy.year,
                                                  inicio=hoy + timedelta(days=10))
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Único')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Lectura', tipo='texto')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def url(self, nombre, *extra, curso=None):
        return reverse(nombre, args=[self.lab.slug, (curso or self.curso).codigo, *extra])

    # ------------------------------------------------------------------------------------- ediciones
    def test_una_edicion_vieja_sin_fechas_no_tapa_a_la_nueva(self):
        curso = Curso.objects.create(unidad=self.lab, codigo='AU-CUR-002', nombre='Con dos ediciones', publicado=True)
        vieja = EdicionCurso.objects.create(curso=curso, nombre='2025', anio=2025)
        nueva = EdicionCurso.objects.create(curso=curso, nombre='2026-II', anio=2026, inicio=date(2026, 11, 1))
        self.assertEqual(vieja.estado(HOY)[0], 'finalizada')
        self.assertEqual(curso.edicion_vigente(HOY), nueva)
        empezada = EdicionCurso(curso=curso, nombre='x', anio=2026, inicio=date(2026, 10, 1), fin=date(2026, 11, 30))
        self.assertEqual(empezada.estado(date(2026, 10, 1))[0], 'inscripciones')  # el día del inicio aún se inscribe
        self.assertEqual(empezada.estado(HOY)[0], 'en_curso')
        empezada.inscripciones_hasta = date(2026, 10, 15)
        self.assertEqual(empezada.estado(HOY)[0], 'inscripciones')  # inscripción tardía

    def test_cupo_cero_cierra_la_edicion_y_el_nombre_no_se_repite(self):
        EdicionCurso.objects.filter(pk=self.edicion.pk).update(cupo=0)
        self.client.force_login(self.ana)
        self.client.post(self.url('inscribirse_curso'), {'edicion': self.edicion.pk,
                                                           'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA'})
        self.assertFalse(InscripcionCurso.objects.exists())
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('editar_registro', args=[self.lab.slug, 'edicion_curso', 'nuevo']),
                                     {'padre': self.curso.pk, 'registro-nombre': 'vigente', 'registro-tipo_grupo': 'periodica', 'registro-anio': '2026',
                                      'registro-activa': 'on'})
        self.assertContains(respuesta, 'El curso ya tiene una edición')

    # ------------------------------------------------------------------------------------- inscripción
    def test_quien_fue_retirado_vuelve_y_un_rechazo_viejo_no_bloquea_la_nueva_edicion(self):
        InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='retirada')
        self.client.force_login(self.ana)
        self.client.post(self.url('inscribirse_curso'), {'edicion': self.edicion.pk,
                                                           'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA'})
        self.assertEqual(InscripcionCurso.objects.get(usuario=self.ana).estado, 'aceptada')
        curso = Curso.objects.create(unidad=self.lab, codigo='AU-CUR-003', nombre='Repetido', publicado=True)
        anterior = EdicionCurso.objects.create(curso=curso, nombre='2025', anio=2025, inicio=date(2025, 3, 1), fin=date(2025, 4, 1))
        InscripcionCurso.objects.create(edicion=anterior, usuario=self.ana, estado='rechazada')
        hoy = timezone.localdate()
        EdicionCurso.objects.create(curso=curso, nombre='Nueva', anio=hoy.year, inicio=hoy + timedelta(days=5))
        self.assertContains(self.client.get(self.url('curso_unidad', curso=curso)), 'Elegir grupo e inscribirme')

    def test_matricula_y_rechazo_no_pisan_lo_que_la_persona_pago(self):
        curso = Curso.objects.create(unidad=self.lab, codigo='AU-CUR-004', nombre='Pagado', publicado=True,
                                     costo=Decimal('20'), pago_transferencia=True)
        edicion = EdicionCurso.objects.create(curso=curso, nombre='Única', anio=timezone.localdate().year)
        inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=self.ana, estado='pendiente')
        pago = PagoInscripcion.objects.create(inscripcion=inscripcion, monto_original=20, monto=20, medio='transferencia',
                                              referencia='TX-1')
        self.client.force_login(self.admin)
        self.client.post(self.url('inscritos_curso', curso=curso), {'accion': 'matricular', 'edicion': edicion.pk,
                                                                     'personas': 'ana-aud2'})
        pago.refresh_from_db()
        inscripcion.refresh_from_db()
        self.assertEqual((pago.estado, pago.referencia, inscripcion.estado), ('pendiente', 'TX-1', 'aceptada'))
        self.client.post(self.url('inscritos_curso', curso=curso), {'accion': 'rechazar_pago', 'pago': pago.pk})
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.estado, 'aceptada')
        # Un pago rechazado de alguien ya aceptado no se reenvía (ni lo saca del aula).
        self.client.force_login(self.ana)
        self.client.post(self.url('pagar_curso', curso=curso), {'medio': 'transferencia', 'referencia': 'TX-2'})
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.estado, 'aceptada')

    def test_los_usos_de_un_codigo_no_cuentan_inscripciones_rechazadas(self):
        curso = Curso.objects.create(unidad=self.lab, codigo='AU-CUR-005', nombre='Con código', publicado=True, costo=Decimal('10'))
        edicion = EdicionCurso.objects.create(curso=curso, nombre='Única', anio=timezone.localdate().year)
        codigo = CodigoDescuento.objects.create(curso=curso, codigo='UNO', porcentaje=100, usos_maximos=1)
        inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=self.ana, estado='rechazada')
        PagoInscripcion.objects.create(inscripcion=inscripcion, monto_original=10, monto=0, codigo=codigo, estado='exonerado')
        self.assertEqual(codigo.usos, 0)
        self.assertEqual(codigo.motivo_invalido(), '')

    # ------------------------------------------------------------------------------------- certificados
    def test_un_certificado_anulado_se_vuelve_a_emitir_y_el_publico_no_ve_la_cedula(self):
        # Una actividad certificable registra fechas y horas reales antes de emitir.
        EdicionCurso.objects.filter(pk=self.edicion.pk).update(
            fin=self.edicion.inicio + timedelta(days=1), horas_certificadas=2)
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        primero = CertificadoCurso.objects.get()
        CertificadoCurso.objects.filter(pk=primero.pk).update(anulado=True, motivo_anulacion='Nombre equivocado')
        self.assertEqual(self.client.get(self.url('mi_certificado')).status_code, 404)
        self.client.force_login(self.admin)
        self.client.post(self.url('reemitir_certificado', primero.pk))
        nuevo = CertificadoCurso.objects.get(anulado=False)
        self.assertNotEqual(nuevo.codigo, primero.codigo)
        self.assertEqual(nuevo.inscripcion, inscripcion)
        with mock.patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF') as pdf:
            self.client.logout()
            self.client.get(reverse('verificar_certificado', args=[nuevo.codigo]), {'formato': 'pdf'})
            self.assertEqual(pdf.call_args.args[1], False)
        Curso.objects.filter(pk=self.curso.pk).update(firma_nombre='Ing. Pérez', firma_cargo='')
        self.assertEqual(firmante_de(Curso.objects.get(pk=self.curso.pk)), ('Ing. Pérez', 'Coordinación de Laboratorio auditado'))

    # ------------------------------------------------------------------------------------- evaluaciones y deberes
    def test_la_evaluacion_no_se_aprueba_probando_y_no_se_rinde_sin_preguntas(self):
        InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        evaluacion = LeccionCurso.objects.create(modulo=self.lectura.modulo, orden=2, titulo='Prueba', tipo='evaluacion', intentos=2)
        self.client.force_login(self.ana)
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        self.client.post(self.url('rendir_evaluacion', evaluacion.pk))
        self.assertFalse(IntentoEvaluacion.objects.exists())  # sin preguntas no gasta intentos
        PreguntaEvaluacion.objects.create(leccion=evaluacion, enunciado='2 + 2', opciones='*4\n5', explicacion='Suma directa.')
        pregunta = evaluacion.preguntas.get()
        self.client.post(self.url('rendir_evaluacion', evaluacion.pk), {f'p{pregunta.pk}': '1'})
        aula = self.client.get(self.url('aula_curso_leccion', evaluacion.pk))
        self.assertContains(aula, '0 de 1 correctas')
        self.assertNotContains(aula, 'Suma directa.')
        self.assertNotContains(aula, 'is-error')

    def test_nota_invalida_entrega_pesada_y_volver_externo(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        deber = LeccionCurso.objects.create(modulo=self.lectura.modulo, orden=2, titulo='Deber', tipo='deber')
        entrega = EntregaDeber.objects.create(inscripcion=inscripcion, leccion=deber, enlace='https://example.org/x')
        self.client.force_login(self.admin)
        respuesta = self.client.post(self.url('calificaciones_curso'), {'entrega': entrega.pk, 'accion': 'calificar', 'nota': 'nan'})
        self.assertContains(respuesta, 'Escriba una nota entre 0 y 10')
        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, 'entregada')
        self.assertIsNone(entrega.nota)
        self.assertIsNone(entrega.calificada_por)
        destino = self.client.post(reverse('editar_registro', args=[self.lab.slug, 'modulo_curso', self.lectura.modulo.pk]),
                                   {'registro-orden': '1', 'registro-titulo': 'Único', 'volver': '//evil.example.com/'})
        self.assertEqual(destino['Location'], self.lab.get_absolute_url())
        self.client.force_login(self.ana)
        with mock.patch('apps.formacion.presentation.calificaciones_cursos.TAMANO_MAXIMO_ENTREGA', 10):
            respuesta = self.client.post(self.url('entregar_deber', deber.pk),
                                         {'archivo': SimpleUploadedFile('grande.pdf', b'%PDF-1.4 ' + b'x' * 50)})
        self.assertContains(respuesta, 'El archivo pesa más de')

    # ------------------------------------------------------------------------------------- comentarios
    def test_comentarios_en_lecciones_publicadas_y_las_respuestas_se_conservan(self):
        InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        oculta = LeccionCurso.objects.create(modulo=self.lectura.modulo, orden=3, titulo='Borrador', tipo='texto', publicada=False)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.post(self.url('comentar_leccion', oculta.pk), {'texto': 'hola'}).status_code, 404)
        self.client.post(self.url('comentar_leccion', self.lectura.pk), {'texto': '¿Pregunta?'})
        pregunta = ComentarioLeccion.objects.get()
        ComentarioLeccion.objects.create(leccion=self.lectura, usuario=self.admin, texto='Respuesta', respuesta_a=pregunta)
        self.client.post(self.url('moderar_comentario', pregunta.pk))
        pregunta.refresh_from_db()
        self.assertEqual(pregunta.texto, 'Pregunta retirada por su autor.')
        self.assertTrue(ComentarioLeccion.objects.filter(texto='Respuesta').exists())
