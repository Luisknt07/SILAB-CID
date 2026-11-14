"""Oferta externa pública y aislamiento respecto del aula y la matrícula local."""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.formacion.presentation.aula_cursos import puede_inscribirse
from apps.formacion.presentation.certificados_cursos import emitir_certificado_evento, emitir_si_corresponde
from apps.formacion.presentation.matriculas_cursos import aplicar_invitaciones, matricular_lista
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.enlaces_formacion import validar_enlace_formacion


class CursosExternosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('externos-gestor', 'externos@example.org', 'clave')
        cls.persona = get_user_model().objects.create_user('externos-persona', password='clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de formación externa', slug='formacion-externa',
            dependencia='laboratorios', descripcion='Laboratorio', fecha_inicio=date(2026, 1, 1), administrador=cls.gestor)
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='EXT-001', nombre='Seminario de colaboración',
            clasificacion='seminario', origen='externo', url_externa='https://formacion.example.org/seminario',
            entidad_organizadora='Universidad colaboradora', participacion_unidad='colaborador', publicado=True)
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Edición informativa', anio=2026)

    def test_destinos_publicos_y_rechazo_de_credenciales_y_red_local(self):
        for url in ('https://formacion.example.org/curso?a=1', 'http://academia.example.org/evento'):
            validar_enlace_formacion(url)
        for url in ('javascript:alert(1)', 'https://persona:secreto@example.org/curso', 'http://localhost/curso',
                    'http://127.0.0.1/curso', 'http://10.1.2.3/curso', 'http://[::1]/curso',
                    'https://intranet.local/curso', 'http://169.254.169.254/latest', 'https://example.org:99999/curso'):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                validar_enlace_formacion(url)

    def test_publicar_externo_requiere_enlace_y_organizador(self):
        for cambios in ({'url_externa': ''}, {'entidad_organizadora': ''}):
            curso = Curso.objects.get(pk=self.curso.pk)
            for campo, valor in cambios.items():
                setattr(curso, campo, valor)
            with self.assertRaises(ValidationError):
                curso.full_clean()

    def test_borrador_externo_puede_completarse_despues(self):
        curso = Curso(unidad=self.unidad, codigo='EXT-BORRADOR', nombre='Encuentro por completar', origen='externo')
        curso.full_clean()

    def test_aula_y_post_de_matricula_externa_no_crean_inscripciones(self):
        self.client.force_login(self.persona)
        argumentos = [self.unidad.slug, self.curso.codigo]
        self.assertEqual(self.client.get(reverse('aula_curso', args=argumentos)).status_code, 404)
        self.assertEqual(self.client.post(reverse('inscribirse_curso', args=argumentos), {'edicion': self.grupo.pk}).status_code, 404)
        self.assertEqual(self.client.get(reverse('pagar_curso', args=argumentos)).status_code, 404)
        self.assertEqual(InscripcionCurso.objects.filter(edicion=self.grupo).count(), 0)
        self.assertFalse(puede_inscribirse(self.curso, self.grupo, self.persona)[0])

    def test_importacion_de_matricula_tambien_rechaza_externo(self):
        with self.assertRaises(ValidationError):
            matricular_lista(self.grupo, [{'correo': 'persona@example.org', 'nombres_completos': 'Persona Ejemplo',
                'documento': 'EXT-1234'}], self.gestor)
        self.assertEqual(InscripcionCurso.objects.filter(edicion=self.grupo).count(), 0)

    def test_origen_no_cambia_si_hay_historial(self):
        nativo = Curso.objects.create(unidad=self.unidad, codigo='NAT-HIST', nombre='Formación nativa')
        grupo = EdicionCurso.objects.create(curso=nativo, nombre='Grupo', anio=2026)
        InscripcionCurso.objects.create(edicion=grupo, usuario=self.persona, estado='retirada')
        nativo.origen = 'externo'
        with self.assertRaises(ValidationError):
            nativo.save()
        nativo.refresh_from_db()
        self.assertFalse(nativo.es_externo)

    def test_cambiar_origen_sin_historial_conserva_los_datos(self):
        self.curso.origen = 'nativo'
        self.curso.save()
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.url_externa, 'https://formacion.example.org/seminario')
        self.assertEqual(self.curso.entidad_organizadora, 'Universidad colaboradora')

    def test_enlace_inseguro_cargado_sin_formulario_no_se_presenta_como_href(self):
        Curso.objects.filter(pk=self.curso.pk).update(url_externa='javascript:alert(1)')
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.url_externa_segura, '')

    def test_gestor_no_abre_grupos_ni_certificados_externos_por_url_directa(self):
        self.client.force_login(self.gestor)
        argumentos = [self.unidad.slug, self.curso.codigo]
        for nombre in ('grupos_curso', 'editar_certificado_curso', 'mi_certificado'):
            with self.subTest(ruta=nombre):
                self.assertEqual(self.client.get(reverse(nombre, args=argumentos)).status_code, 404)

    def test_emision_de_certificados_rechaza_externo_aun_con_matricula_importada(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.persona, estado='aceptada')
        self.assertIsNone(emitir_si_corresponde(inscripcion))
        with self.assertRaises(ValidationError):
            emitir_certificado_evento(inscripcion, self.gestor, 'participacion', 'Participación verificada', confirmacion=True)

    def test_vincular_correo_omite_externos_e_inactivos_y_reactivar_conserva_invitacion(self):
        from allauth.account.models import EmailAddress

        correo = 'invitacion-formacion@example.org'
        EmailAddress.objects.create(user=self.persona, email=correo, verified=True, primary=True)
        nativo = Curso.objects.create(unidad=self.unidad, codigo='NAT-INACTIVO', nombre='Actividad pausada', activo=False)
        grupo = EdicionCurso.objects.create(curso=nativo, nombre='Grupo', anio=2026)
        invitaciones = [InvitacionCurso.objects.create(edicion=edicion, correo=correo, activa=True,
            nombres_completos='Persona Ejemplo', documento='PAS-123456') for edicion in (self.grupo, grupo)]
        self.assertEqual(aplicar_invitaciones(self.persona), [])
        self.assertFalse(InscripcionCurso.objects.filter(usuario=self.persona).exists())
        self.assertTrue(all(InvitacionCurso.objects.filter(pk=i.pk, inscripcion__isnull=True).exists() for i in invitaciones))
        Curso.objects.filter(pk=nativo.pk).update(activo=True)
        vinculadas = aplicar_invitaciones(self.persona)
        self.assertEqual(len(vinculadas), 1)
        self.assertEqual(vinculadas[0].edicion_id, grupo.pk)
        self.assertTrue(InvitacionCurso.objects.filter(pk=invitaciones[0].pk, inscripcion__isnull=True).exists())
