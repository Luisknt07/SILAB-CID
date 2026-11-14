"""Grupos explícitos, listas atómicas e identidad confirmada para matrículas externas."""
from datetime import date, timedelta
from decimal import Decimal

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso
from apps.formacion.models.cursos_inscripcion import InvitacionCurso, PagoInscripcion
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.presentation.matriculas_cursos import aplicar_invitaciones, cupos_disponibles, matricular_lista
from apps.formacion.presentation.matriculas_datos import leer_lista_matricula, validar_datos_matricula
from apps.formacion.presentation.matriculas_forms import GrupoCursoForm


class DatosMatriculaTests(SimpleTestCase):
    def test_csv_utf8_y_alias_cedula_normalizan_datos(self):
        filas = leer_lista_matricula('\ufeffcorreo;cedula;nombres_completos\n ANA@EXAMPLE.ORG ; doc-123 ; Ana  Ríos\n')
        self.assertEqual(filas, [{'correo': 'ana@example.org', 'documento': 'DOC-123', 'nombres_completos': 'Ana Ríos'}])

    def test_rechaza_listas_con_duplicados_por_correo_o_documento(self):
        for segunda in ('ANA@example.org,DOC-222,Luis Paz', 'luis@example.org,doc-111,Luis Paz'):
            with self.subTest(segunda=segunda), self.assertRaises(ValidationError):
                leer_lista_matricula('correo,documento,nombres_completos\nana@example.org,DOC-111,Ana Ríos\n' + segunda)

    def test_rechaza_fila_invalida_html_formula_y_cedula_incorrecta(self):
        for documento, nombre in (('1234567890', 'Ana Ríos'), ('DOC-123', '<script>Ana</script>'),
                                  ('DOC-123', '=HYPERLINK("datos")'), ('DOC-123', 'Ana\x00 Ríos')):
            with self.subTest(documento=documento, nombre=nombre), self.assertRaises(ValidationError):
                validar_datos_matricula(correo='ana@example.org', documento=documento, nombres_completos=nombre)

    def test_limites_y_formato_se_comprueban_en_backend(self):
        for contenido in (b'\xff', b'x' * 1_048_577, 'correo,nombre\na@example.org,Ana',
                          'correo,documento,nombres_completos\n' + '\n'.join(
                              f'a{i}@example.org,DOC-{i:03},Persona Ejemplo' for i in range(101))):
            with self.subTest(tipo=type(contenido)), self.assertRaises(ValidationError):
                leer_lista_matricula(contenido)


class GruposMatriculaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_user('gestor-grupos', 'gestor@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-grupos', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-grupos', 'luis@example.org', 'clave', first_name='Luis', last_name='Paz')
        cls.ajeno = usuarios.objects.create_user('ajeno-grupos', 'ajeno@example.org', 'clave')
        EmailAddress.objects.create(user=cls.ana, email=cls.ana.email, verified=True, primary=True)
        cls.unidad = Unidad.objects.create(nombre='Unidad de grupos', slug='unidad-grupos', dependencia='laboratorios',
                                          administrador=cls.gestor, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad de grupos', slug='otra-unidad-grupos', dependencia='laboratorios',
                                        administrador=cls.ajeno, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='GRUPOS-001', nombre='Curso compartido', publicado=True,
                                        emite_certificado=False)
        cls.curso_ajeno = Curso.objects.create(unidad=cls.otra, codigo='GRUPOS-002', nombre='Curso ajeno', publicado=True)
        hoy = timezone.localdate()
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Primero', anio=hoy.year,
                                                inicio=hoy + timedelta(days=7), cupo=5)
        cls.segundo = EdicionCurso.objects.create(curso=cls.curso, nombre='A medida', anio=hoy.year,
                                                  tipo_grupo='a_medida', destinatario='Asociación de práctica',
                                                  inicio=hoy + timedelta(days=9), cupo=3)
        cls.grupo_ajeno = EdicionCurso.objects.create(curso=cls.curso_ajeno, nombre='Ajeno', anio=hoy.year)
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Contenido único')
        cls.leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lectura compartida', contenido='Ejemplo')

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.unidad.slug, self.curso.codigo, *extra])

    def fila(self, correo='ana@example.org', documento='DOC-ANA', nombre='Ana Ríos'):
        return {'correo': correo, 'documento': documento, 'nombres_completos': nombre}

    def test_matricula_cuenta_verificada_con_snapshot_sin_cambiar_identidad(self):
        documento_original = self.ana.profile.cedula
        resultado = matricular_lista(self.grupo, [self.fila(nombre='Ana Ríos de la lista')], self.gestor)
        inscripcion = InscripcionCurso.objects.get(usuario=self.ana, edicion=self.grupo)
        self.assertEqual(resultado['matriculadas'], ['ana@example.org'])
        self.assertEqual((inscripcion.nombres_completos, inscripcion.documento), ('Ana Ríos de la lista', 'DOC-ANA'))
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.first_name, self.ana.last_name, self.ana.email), ('Ana', 'Ríos', 'ana@example.org'))
        self.assertEqual(self.ana.profile.cedula, documento_original)

    def test_correo_no_verificado_queda_invitado_y_reserva_cupo(self):
        resultado = matricular_lista(self.grupo, [self.fila('luis@example.org', 'DOC-LUIS', 'Luis Paz')], self.gestor)
        self.assertEqual(resultado['invitadas'], ['luis@example.org'])
        self.assertFalse(InscripcionCurso.objects.filter(usuario=self.luis).exists())
        self.assertEqual(cupos_disponibles(self.grupo), 4)
        aplicar_invitaciones(self.luis)
        self.assertFalse(InscripcionCurso.objects.filter(usuario=self.luis).exists())
        correo = EmailAddress.objects.create(user=self.luis, email=self.luis.email, verified=True, primary=True)
        email_confirmed.send(sender=EmailAddress, request=None, email_address=correo)
        inscripcion = InscripcionCurso.objects.get(usuario=self.luis)
        self.assertEqual((inscripcion.nombres_completos, inscripcion.documento), ('Luis Paz', 'DOC-LUIS'))
        self.assertEqual(cupos_disponibles(self.grupo), 4)
        self.assertEqual(InvitacionCurso.objects.get(correo=self.luis.email).inscripcion, inscripcion)

    def test_correo_secundario_verificado_tambien_vincula(self):
        matricular_lista(self.grupo, [self.fila('alias@example.org', 'DOC-ALIAS', 'Luis Paz')], self.gestor)
        EmailAddress.objects.create(user=self.luis, email='alias@example.org', verified=True, primary=False)
        aplicar_invitaciones(self.luis)
        self.assertTrue(InscripcionCurso.objects.filter(usuario=self.luis, edicion=self.grupo).exists())

    def test_lista_superior_al_cupo_no_guarda_ni_cuentas_ni_invitaciones(self):
        self.grupo.cupo = 1
        self.grupo.save(update_fields=['cupo'])
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [self.fila(), self.fila('nueva@example.org', 'DOC-NUEVA', 'Nueva Persona')], self.gestor)
        self.assertFalse(self.grupo.inscripciones.exists())
        self.assertFalse(self.grupo.invitaciones.exists())

    def test_repetir_lista_es_idempotente_y_no_consume_otro_cupo(self):
        filas = [self.fila(), self.fila('nueva@example.org', 'DOC-NUEVA', 'Nueva Persona')]
        matricular_lista(self.grupo, filas, self.gestor)
        repetida = matricular_lista(self.grupo, filas, self.gestor)
        self.assertEqual(len(repetida['ya_estaban']), 2)
        self.assertEqual(cupos_disponibles(self.grupo), 3)
        self.assertEqual(self.grupo.inscripciones.count(), 1)
        self.assertEqual(self.grupo.invitaciones.count(), 2)

    def test_documento_repetido_entre_cuentas_se_rechaza(self):
        matricular_lista(self.grupo, [self.fila()], self.gestor)
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [self.fila('otra@example.org', 'DOC-ANA', 'Otra Persona')], self.gestor)
        self.assertEqual(self.grupo.invitaciones.count(), 1)

    def test_lista_revierte_tambien_un_error_tardio_de_identidad(self):
        InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.ana, estado='rechazada',
                                        nombres_completos='Identidad anterior', documento='DOC-ANA')
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [self.fila('nueva@example.org', 'DOC-NUEVA', 'Nueva Persona'), self.fila()], self.gestor)
        self.assertFalse(self.grupo.invitaciones.exists())
        self.assertEqual(self.grupo.inscripciones.get().estado, 'rechazada')

    def test_no_se_matricula_en_una_unidad_ajena(self):
        with self.assertRaises(PermissionDenied):
            matricular_lista(self.grupo_ajeno, [self.fila()], self.gestor)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.url('inscritos_curso')).status_code, 403)

    def test_inscripcion_exige_grupo_y_datos_en_backend(self):
        self.client.force_login(self.ana)
        respuesta = self.client.post(self.url('inscribirse_curso'), {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(self.grupo.inscripciones.exists())
        self.assertIn('edicion', respuesta.context['formulario'].errors)
        self.assertIn('documento', respuesta.context['formulario'].errors)

    def test_elegir_segundo_grupo_y_avance_no_se_mezcla_con_primero(self):
        self.client.force_login(self.ana)
        respuesta = self.client.post(self.url('inscribirse_curso'), {
            'edicion': self.segundo.pk, 'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA'})
        self.assertRedirects(respuesta, self.url('curso_unidad') + f'?edicion={self.segundo.pk}#inscripcion')
        self.assertFalse(self.grupo.inscripciones.exists())
        inscripcion = self.segundo.inscripciones.get()
        completar = self.url('completar_leccion', self.leccion.pk)
        self.assertEqual(self.client.post(completar + f'?edicion={self.grupo.pk}').status_code, 403)
        respuesta = self.client.post(completar + f'?edicion={self.segundo.pk}')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(f'edicion={self.segundo.pk}', respuesta.url)
        self.assertEqual(inscripcion.progresos.count(), 1)
        self.assertFalse(self.grupo.inscripciones.exists())

    def test_edicion_ajena_nunca_recurre_a_otra_inscripcion(self):
        InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.ana, estado='aceptada')
        self.client.force_login(self.ana)
        for nombre in ('curso_unidad', 'aula_curso'):
            self.assertEqual(self.client.get(self.url(nombre) + f'?edicion={self.grupo_ajeno.pk}').status_code, 404)
        respuesta = self.client.post(self.url('inscribirse_curso'), {
            'edicion': self.grupo_ajeno.pk, 'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA'})
        self.assertEqual(respuesta.status_code, 404)

    def test_el_pago_pertenece_al_grupo_elegido_y_valida_su_cupo(self):
        self.curso.costo = Decimal('40.00')
        self.curso.save(update_fields=['costo'])
        self.client.force_login(self.ana)
        respuesta = self.client.post(self.url('pagar_curso'), {
            'edicion': self.segundo.pk, 'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA',
            'medio': 'transferencia', 'referencia': 'PRUEBA-1'})
        self.assertEqual(respuesta.status_code, 302)
        pago = PagoInscripcion.objects.get()
        self.assertEqual(pago.inscripcion.edicion, self.segundo)
        self.assertEqual(pago.inscripcion.documento, 'DOC-ANA')
        self.assertFalse(self.grupo.inscripciones.exists())

    def test_cancelar_invitacion_libera_cupo_y_evitar_vinculacion(self):
        matricular_lista(self.grupo, [self.fila('nueva@example.org', 'DOC-NUEVA', 'Nueva Persona')], self.gestor)
        invitacion = self.grupo.invitaciones.get()
        self.client.force_login(self.gestor)
        self.client.post(self.url('inscritos_curso'), {'accion': 'cancelar_invitacion', 'invitacion': invitacion.pk})
        invitacion.refresh_from_db()
        self.assertFalse(invitacion.activa)
        self.assertEqual(cupos_disponibles(self.grupo), 5)

    def test_formulario_grupo_no_reduce_cupo_por_debajo_de_reservas(self):
        matricular_lista(self.grupo, [self.fila('nueva@example.org', 'DOC-NUEVA', 'Nueva Persona')], self.gestor)
        form = GrupoCursoForm({'nombre': self.grupo.nombre, 'tipo_grupo': 'periodica', 'anio': self.grupo.anio,
                               'cupo': 0, 'activa': 'on'}, curso=self.curso, instance=self.grupo)
        self.assertFalse(form.is_valid())
        self.assertIn('cupo', form.errors)

    def test_grupos_comparten_contenido_sin_duplicar_modulos(self):
        self.assertEqual(self.curso.modulos.count(), 1)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(self.url('grupos_curso')), 'Asociación de práctica')
        self.assertEqual(self.curso.modulos.count(), 1)

    def test_invitacion_vinculada_no_se_reasigna_a_otro_dueño_del_correo(self):
        anterior = get_user_model().objects.create_user('dueno-anterior-grupo', 'anterior@example.org', 'clave')
        inscripcion = InscripcionCurso.objects.create(edicion=self.grupo, usuario=anterior, estado='retirada')
        invitacion = InvitacionCurso.objects.create(edicion=self.grupo, correo=self.ana.email, inscripcion=inscripcion)
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [self.fila()], self.gestor)
        invitacion.refresh_from_db()
        self.assertEqual(invitacion.inscripcion, inscripcion)
        self.assertFalse(self.grupo.inscripciones.filter(usuario=self.ana).exists())

    def test_documento_de_matricula_retirada_se_valida_antes_del_constraint(self):
        InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.luis, estado='retirada', documento='DOC-ANA')
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [self.fila()], self.gestor)
        self.assertFalse(self.grupo.invitaciones.exists())
        self.assertFalse(self.grupo.inscripciones.filter(usuario=self.ana).exists())
