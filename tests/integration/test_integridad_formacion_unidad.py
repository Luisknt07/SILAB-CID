"""La formación deriva su unidad del curso y rechaza relaciones académicas cruzadas."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.test import SimpleTestCase, TestCase

from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.formacion.models.cursos_inscripcion import ClaseGrupoCurso, CodigoDescuento, InvitacionCurso, PagoInscripcion
from apps.formacion.models.cursos import ComentarioLeccion, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad


class RelacionesFormacionSinBaseTests(SimpleTestCase):
    def setUp(self):
        self.persona = get_user_model()(pk=-10, username='identidad-sin-guardar')
        self.unidad = Unidad(pk=-1, nombre='Unidad A')
        self.otra_unidad = Unidad(pk=-2, nombre='Unidad B')
        self.curso = Curso(pk=-11, unidad=self.unidad, codigo='REL-A', nombre='Curso A')
        self.otro_curso = Curso(pk=-12, unidad=self.unidad, codigo='REL-A2', nombre='Otro curso de A')
        self.curso_ajeno = Curso(pk=-13, unidad=self.otra_unidad, codigo='REL-B', nombre='Curso B')
        self.grupo = EdicionCurso(pk=-21, curso=self.curso, nombre='Grupo A', anio=2026)
        self.matricula = InscripcionCurso(pk=-31, edicion=self.grupo, usuario=self.persona)

    def leccion(self, curso, tipo='texto', pk=-41):
        modulo = ModuloCurso(pk=pk - 100, curso=curso, titulo='Módulo')
        return LeccionCurso(pk=pk, modulo=modulo, titulo='Lección', tipo=tipo)

    def validar_actividad(self, modelo, tipo, **extra):
        modelo(inscripcion=self.matricula, leccion=self.leccion(self.curso, tipo), **extra).clean()
        for curso in (self.otro_curso, self.curso_ajeno):
            with self.subTest(curso=curso.codigo), self.assertRaisesMessage(ValidationError, 'curso'):
                modelo(inscripcion=self.matricula, leccion=self.leccion(curso, tipo), **extra).clean()

    def test_progreso_rechaza_leccion_de_otro_curso_aunque_compartan_unidad(self):
        self.validar_actividad(ProgresoLeccion, 'texto')

    def test_intento_rechaza_evaluacion_de_otro_curso(self):
        self.validar_actividad(IntentoEvaluacion, 'evaluacion', nota=Decimal('80'))

    def test_entrega_rechaza_deber_de_otro_curso(self):
        self.validar_actividad(EntregaDeber, 'deber')

    def test_pago_rechaza_codigo_de_otro_curso(self):
        for curso in (self.curso, self.otro_curso, self.curso_ajeno):
            codigo = CodigoDescuento(pk=-51, curso=curso, codigo='BECA', porcentaje=10)
            pago = PagoInscripcion(inscripcion=self.matricula, codigo=codigo,
                monto_original=0, monto=0, estado='exonerado')
            with self.subTest(curso=curso.codigo):
                if curso == self.curso:
                    pago.clean()
                else:
                    with self.assertRaisesMessage(ValidationError, 'curso'):
                        pago.clean()

    def test_invitacion_vinculada_rechaza_matricula_de_otro_grupo(self):
        InvitacionCurso(edicion=self.grupo, inscripcion=self.matricula,
            correo='persona@example.invalid').clean()
        for curso in (self.curso, self.otro_curso, self.curso_ajeno):
            grupo = EdicionCurso(pk=-22, curso=curso, nombre='Otro grupo', anio=2026)
            with self.subTest(curso=curso.codigo), self.assertRaisesMessage(ValidationError, 'grupo'):
                InvitacionCurso(edicion=grupo, inscripcion=self.matricula,
                    correo='persona@example.invalid').clean()

    def test_respuesta_comentario_pertenece_a_su_misma_leccion(self):
        leccion = self.leccion(self.curso)
        original = ComentarioLeccion(pk=-61, leccion=leccion, usuario=self.persona, texto='Pregunta')
        ComentarioLeccion(leccion=leccion, usuario=self.persona, texto='Respuesta', respuesta_a=original).clean()
        for curso in (self.curso, self.otro_curso, self.curso_ajeno):
            with self.subTest(curso=curso.codigo), self.assertRaisesMessage(ValidationError, 'lección'):
                ComentarioLeccion(leccion=self.leccion(curso, pk=-42), usuario=self.persona,
                    texto='Respuesta cruzada', respuesta_a=original).clean()

    def test_clase_por_grupo_ya_exige_mismo_curso(self):
        ClaseGrupoCurso(edicion=self.grupo, leccion=self.leccion(self.curso, 'en_vivo')).clean()
        with self.assertRaisesMessage(ValidationError, 'curso'):
            ClaseGrupoCurso(edicion=self.grupo, leccion=self.leccion(self.curso_ajeno, 'en_vivo')).clean()

    def test_actividad_catalogo_global_o_de_la_unidad_se_admite(self):
        for unidad in (None, self.unidad):
            actividad = CatalogoActividadReserva(pk=-71, unidad=unidad, nombre='Actividad')
            Curso(unidad=self.unidad, actividad_catalogo=actividad).clean()
        actividad = CatalogoActividadReserva(pk=-72, unidad=self.otra_unidad, nombre='Otra actividad')
        with self.assertRaisesMessage(ValidationError, 'unidad'):
            Curso(unidad=self.unidad, actividad_catalogo=actividad).clean()

    def test_las_relaciones_incompletas_de_formulario_no_desreferencian_fk_ausentes(self):
        for modelo in (ProgresoLeccion, IntentoEvaluacion, EntregaDeber, ComentarioLeccion):
            with self.subTest(modelo=modelo.__name__):
                modelo().clean()
        PagoInscripcion(monto=0).clean()
        InvitacionCurso(correo='persona@example.invalid').clean()

    def test_grupos_del_mismo_curso_comparten_lecciones_sin_cruzar_matriculas(self):
        otro_grupo = EdicionCurso(pk=-23, curso=self.curso, nombre='Grupo compartido', anio=2026)
        matricula = InscripcionCurso(pk=-32, edicion=otro_grupo, usuario=self.persona)
        for modelo, tipo in ((ProgresoLeccion, 'texto'), (IntentoEvaluacion, 'evaluacion'), (EntregaDeber, 'deber')):
            with self.subTest(modelo=modelo.__name__):
                modelo(inscripcion=matricula, leccion=self.leccion(self.curso, tipo)).clean()


class IntegridadFormacionPersistidaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.persona = get_user_model().objects.create_user('relacion-formacion', 'persona@example.invalid')
        cls.unidad = Unidad.objects.create(nombre='Unidad origen', slug='unidad-relacion-a',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Unidad ajena', slug='unidad-relacion-b',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='REL-A', nombre='Curso origen', emite_certificado=False)
        cls.curso_ajeno = Curso.objects.create(unidad=cls.otra, codigo='REL-B', nombre='Curso ajeno', emite_certificado=False)
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=2026)
        cls.matricula = InscripcionCurso.objects.create(edicion=cls.grupo, usuario=cls.persona, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso_ajeno, titulo='Módulo ajeno')
        cls.leccion_ajena = LeccionCurso.objects.create(modulo=modulo, titulo='Lección ajena', tipo='texto')

    def test_formulario_modelo_no_acepta_progreso_cruzado_entre_unidades(self):
        formulario_tipo = modelform_factory(ProgresoLeccion, fields=('inscripcion', 'leccion'))
        formulario = formulario_tipo({'inscripcion': self.matricula.pk, 'leccion': self.leccion_ajena.pk})
        self.assertFalse(formulario.is_valid())
        self.assertIn('leccion', formulario.errors)
        self.assertFalse(ProgresoLeccion.objects.exists())
        modulo = ModuloCurso.objects.create(curso=self.curso, titulo='Módulo propio')
        leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lección propia', tipo='texto')
        valido = formulario_tipo({'inscripcion': self.matricula.pk, 'leccion': leccion.pk})
        self.assertTrue(valido.is_valid(), valido.errors)
        self.assertEqual(valido.save().inscripcion, self.matricula)

    def test_servicio_completar_no_guarda_progreso_en_curso_ajeno(self):
        from apps.formacion.presentation.aula_cursos import completar
        with self.assertRaisesMessage(ValidationError, 'curso'):
            completar(self.matricula, self.leccion_ajena)
        self.assertFalse(ProgresoLeccion.objects.exists())
        modulo = ModuloCurso.objects.create(curso=self.curso, titulo='Módulo propio')
        leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lección propia', tipo='texto')
        self.assertIsNone(completar(self.matricula, leccion))
        self.assertEqual(ProgresoLeccion.objects.get().leccion, leccion)
