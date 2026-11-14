"""Acciones explícitas de oferta y conservación del historial de la unidad."""
from datetime import date
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, ParticipanteEvento
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.directorio_unidades.models.core import Unidad


class CicloVidaCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('estado-gestor', 'estado@example.org', 'clave')
        cls.persona = get_user_model().objects.create_user('estado-persona', password='clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio estados', slug='laboratorio-estados',
            dependencia='laboratorios', descripcion='Laboratorio', fecha_inicio=date(2026, 1, 1), administrador=cls.gestor)
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='ESTADO-001', nombre='Curso con control de estado', publicado=True)
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo', anio=2026)

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('estado_curso', args=[self.unidad.slug, self.curso.codigo])

    def test_estado_es_post_con_permiso_y_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(self.persona)
        self.assertEqual(self.client.post(self.url, {'accion': 'desactivar'}).status_code, 403)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.gestor)
        self.assertEqual(protegido.post(self.url, {'accion': 'desactivar'}).status_code, 403)

    def test_desactivar_y_reactivar_no_cambia_publicacion_ni_contenido(self):
        for accion, activo in [('desactivar', False), ('activar', True)]:
            self.assertEqual(self.client.post(self.url, {'accion': accion}).status_code, 302)
            self.curso.refresh_from_db()
            self.assertEqual(self.curso.activo, activo)
            self.assertTrue(self.curso.publicado)
            self.assertTrue(self.curso.ediciones.filter(pk=self.grupo.pk).exists())

    def test_eliminar_requiere_confirmacion_y_no_admite_get(self):
        self.assertEqual(self.client.post(self.url, {'accion': 'eliminar'}).status_code, 400)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
        self.assertEqual(self.client.post(self.url, {'accion': 'eliminar', 'confirmar': self.curso.codigo}).status_code, 302)
        self.assertFalse(Curso.objects.filter(pk=self.curso.pk).exists())

    def test_no_elimina_matricula_retirada_participante_o_invitacion_cancelada(self):
        for tipo in ('matricula', 'participante', 'invitacion'):
            with self.subTest(tipo=tipo):
                curso = Curso.objects.create(unidad=self.unidad, codigo=f'ESTADO-{tipo}', nombre=tipo)
                grupo = EdicionCurso.objects.create(curso=curso, nombre='Grupo', anio=2026)
                if tipo == 'matricula':
                    InscripcionCurso.objects.create(edicion=grupo, usuario=self.persona, estado='retirada')
                elif tipo == 'participante':
                    ParticipanteEvento.objects.create(edicion=grupo, documento='PART-001', nombres_completos='Persona Ejemplo')
                else:
                    InvitacionCurso.objects.create(edicion=grupo, correo='invitada@example.org', activa=False)
                with self.assertRaises(ValidationError):
                    curso.delete()
                url = reverse('estado_curso', args=[self.unidad.slug, curso.codigo])
                self.assertEqual(self.client.post(url, {'accion': 'eliminar', 'confirmar': curso.codigo}).status_code, 302)
                self.assertTrue(Curso.objects.filter(pk=curso.pk).exists())

    def test_borrado_masivo_admin_con_historial_es_atomico(self):
        InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.persona, estado='aceptada')
        libre = Curso.objects.create(unidad=self.unidad, codigo='ESTADO-LIBRE', nombre='Sin historial')
        solicitud = RequestFactory().post('/admin/')
        solicitud.user = self.gestor
        panel = admin.site._registry[Curso]
        with self.assertRaises(ValidationError):
            panel.delete_queryset(solicitud, Curso.objects.filter(pk__in=[libre.pk, self.curso.pk]))
        self.assertTrue(Curso.objects.filter(pk=libre.pk).exists())
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())

    def test_aceptado_conserva_aula_inactiva_sin_nuevas_matriculas(self):
        InscripcionCurso.objects.create(edicion=self.grupo, usuario=self.persona, estado='aceptada')
        self.curso.activo = False
        self.curso.save(update_fields=['activo'])
        self.client.force_login(self.persona)
        argumentos = [self.unidad.slug, self.curso.codigo]
        self.assertEqual(self.client.get(reverse('aula_curso', args=argumentos)).status_code, 200)
        self.assertEqual(self.client.get(reverse('pagar_curso', args=argumentos)).status_code, 404)

    def test_edicion_antigua_no_desactiva_por_omitir_campo_nuevo(self):
        url = reverse('editar_registro', args=[self.unidad.slug, 'curso', self.curso.pk])
        respuesta = self.client.post(url, {'grupo': 'presentacion', 'registro-nombre': self.curso.nombre,
            'registro-clasificacion': 'corto', 'registro-modalidad': 'autoguiado', 'registro-publicado': 'on'})
        self.assertEqual(respuesta.status_code, 302)
        self.curso.refresh_from_db()
        self.assertTrue(self.curso.activo)
        respuesta = self.client.post(url, {'grupo': 'presentacion', 'registro-nombre': self.curso.nombre,
            'registro-clasificacion': 'corto', 'registro-modalidad': 'autoguiado', 'registro-publicado': 'on',
            'registro-estado_presente': '1'})
        self.assertEqual(respuesta.status_code, 302)
        self.curso.refresh_from_db()
        self.assertFalse(self.curso.activo)

    def test_admin_de_unidad_no_puede_cambiar_actividad_ajena(self):
        personal = get_user_model().objects.create_user('estado-staff', password='clave', is_staff=True)
        personal.user_permissions.add(*Permission.objects.filter(content_type__app_label='formacion',
            codename__in=['view_curso', 'change_curso', 'delete_curso', 'view_inscripcioncurso']))
        propia = Unidad.objects.create(nombre='Unidad del personal', slug='unidad-estado-personal',
            dependencia='laboratorios', descripcion='Laboratorio', fecha_inicio=date(2026, 1, 1), administrador=personal)
        curso = Curso.objects.create(unidad=propia, codigo='ESTADO-PROPIO', nombre='Actividad de su unidad')
        solicitud = RequestFactory().get('/admin/')
        solicitud.user = personal
        panel = admin.site._registry[Curso]
        self.assertEqual(list(panel.get_queryset(solicitud).values_list('pk', flat=True)), [curso.pk])
        self.assertTrue(panel.has_change_permission(solicitud, curso))
        self.assertFalse(panel.has_change_permission(solicitud, self.curso))
        self.assertFalse(panel.has_delete_permission(solicitud, self.curso))

    def test_matricula_relee_estado_si_cambio_despues_de_abrir_el_curso(self):
        leido = Curso.objects.get(pk=self.curso.pk)
        Curso.objects.filter(pk=self.curso.pk).update(activo=False)
        self.client.force_login(self.persona)
        # Representa una consulta que empezó antes de la desactivación. La
        # decisión de escribir debe usar el estado actual bajo bloqueo.
        with patch('apps.formacion.presentation.aula_cursos._curso', return_value=(self.unidad, leido)):
            respuesta = self.client.post(reverse('inscribirse_curso', args=[self.unidad.slug, leido.codigo]),
                {'edicion': self.grupo.pk, 'nombres_completos': 'Persona Ejemplo', 'documento': 'PAS-123456'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(InscripcionCurso.objects.filter(edicion=self.grupo).exists())

    def test_edicion_no_elimina_invitacion_cancelada_desde_otra_entrada(self):
        invitacion = InvitacionCurso.objects.create(edicion=self.grupo, correo='cancelada@example.org', activa=False)
        with self.assertRaises(ValidationError):
            self.grupo.delete()
        self.assertTrue(InvitacionCurso.objects.filter(pk=invitacion.pk).exists())

    def test_editor_informa_proteccion_sobrevenida_sin_error_500(self):
        url = reverse('editar_registro', args=[self.unidad.slug, 'curso', self.curso.pk])
        with patch.object(Curso, 'delete', side_effect=ValidationError('Se incorporó un participante. Desactiva la actividad.')):
            respuesta = self.client.post(url, {'grupo': 'presentacion', 'registro-nombre': self.curso.nombre,
                'registro-clasificacion': 'corto', 'registro-modalidad': 'autoguiado', 'registro-eliminar': 'on'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Se incorporó un participante', str(respuesta.context['formulario'].errors))
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())

    def test_admin_informa_proteccion_sobrevenida_sin_error_500(self):
        url = reverse('admin:formacion_curso_delete', args=[self.curso.pk])
        with patch.object(Curso, 'delete', side_effect=ValidationError('Se incorporó un participante. Desactiva la actividad.')):
            respuesta = self.client.post(url, {'post': 'yes'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
