"""Formación y designación del personal de la unidad: dónde se escriben y quién puede escribirlas.

Los tres campos (`formacion`, `acto_designacion`, `fecha_designacion`) alimentan la tabla «Personal de la
unidad» del anexo de fichas técnicas (docs/estructura-anexos-por-tipo-de-unidad.md, sección 4.4). Se editan en
el formulario del personal del panel de gestión, con los permisos que ya tenía, y en el admin de Django.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad


class FormacionYDesignacionDelPersonalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.administradora = usuarios.create_user('administradora-designacion', first_name='Alba',
                                                  last_name='Administradora')
        cls.coordinador = usuarios.create_user('coordinador-designacion', first_name='Ciro', last_name='Coordinador')
        cls.tecnico = usuarios.create_user('tecnico-designacion', first_name='Teo', last_name='Técnico')
        cls.ajeno = usuarios.create_user('ajeno-designacion')
        cls.superusuario = usuarios.create_superuser('superusuario-designacion', password='clave-de-prueba')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de designaciones', slug='laboratorio-designaciones',
                                           dependencia='laboratorios', fecha_inicio=date(2025, 1, 1),
                                           administrador=cls.administradora)
        cls.coordinacion = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.coordinador,
                                                            rol='coordinacion')
        # El técnico opera la configuración de la unidad, pero no administra a su personal.
        cls.asignacion = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico, rol='tecnico', horario_atencion='Mañanas',
            permisos_operativos={'configuracion': True})
        cls.destino = reverse('gestion_operacion_accion', args=[cls.unidad.slug])

    def datos(self, **cambios):
        return {'modulo': 'responsable', 'registro_id': self.asignacion.pk, 'usuario_id': self.tecnico.pk,
                'nombre': 'Teo Técnico', 'rol': 'tecnico', 'horario_atencion': 'Mañanas', 'activo': 'on',
                'permiso_configuracion': 'on', 'formacion': 'Tecnólogo de prueba en electrónica',
                'acto_designacion': 'Memorando de prueba 015', 'fecha_designacion': '2026-03-02'} | cambios

    def designacion(self):
        self.asignacion.refresh_from_db()
        return self.asignacion.formacion, self.asignacion.acto_designacion, self.asignacion.fecha_designacion

    def test_la_administracion_y_la_coordinacion_guardan_los_tres_campos(self):
        self.client.force_login(self.administradora)
        respuesta = self.client.post(self.destino, self.datos())
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self.designacion(),
                         ('Tecnólogo de prueba en electrónica', 'Memorando de prueba 015', date(2026, 3, 2)))
        # El cambio deja rastro, con el valor anterior y el nuevo.
        rastro = RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).latest('pk')
        self.assertEqual(rastro.usuario, self.administradora)
        self.assertEqual(rastro.datos_anteriores['acto_designacion'], '')
        self.assertEqual(rastro.datos_nuevos['acto_designacion'], 'Memorando de prueba 015')
        self.assertEqual(rastro.datos_nuevos['fecha_designacion'], '2026-03-02')
        # La coordinación administra al personal operativo de su unidad: también los corrige.
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(self.destino, self.datos(acto_designacion='Memorando de prueba 016',
                                                              fecha_designacion=''))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self.designacion(), ('Tecnólogo de prueba en electrónica', 'Memorando de prueba 016', None))

    def test_un_responsable_nuevo_nace_con_su_formacion_y_su_designacion(self):
        self.client.force_login(self.administradora)
        respuesta = self.client.post(self.destino, {
            'modulo': 'responsable', 'nombre': 'Contacto Ficticio', 'email': 'contacto@example.org', 'rol': 'soporte',
            'activo': 'on', 'formacion': 'Bachiller técnico de prueba', 'acto_designacion': 'Acta de prueba 3',
            'fecha_designacion': '2026-08-10'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        nuevo = ResponsableUnidad.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertEqual((nuevo.formacion, nuevo.acto_designacion, nuevo.fecha_designacion),
                         ('Bachiller técnico de prueba', 'Acta de prueba 3', date(2026, 8, 10)))

    def test_una_fecha_mal_escrita_se_rechaza_y_no_cambia_nada(self):
        self.client.force_login(self.administradora)
        respuesta = self.client.post(self.destino, self.datos(fecha_designacion='2 de marzo'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('La fecha de designación', respuesta.json()['error'])
        self.assertEqual(self.designacion(), ('', '', None))

    def test_un_formulario_que_no_trae_los_campos_no_los_borra(self):
        ResponsableUnidad.objects.filter(pk=self.asignacion.pk).update(
            formacion='Tecnólogo de prueba en electrónica', acto_designacion='Memorando de prueba 015',
            fecha_designacion=date(2026, 3, 2))
        self.client.force_login(self.administradora)
        datos = self.datos(horario_atencion='Tardes')
        for campo in ('formacion', 'acto_designacion', 'fecha_designacion'):
            del datos[campo]
        respuesta = self.client.post(self.destino, datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self.designacion(),
                         ('Tecnólogo de prueba en electrónica', 'Memorando de prueba 015', date(2026, 3, 2)))
        self.assertEqual(self.asignacion.horario_atencion, 'Tardes')

    def test_quien_no_puede_editar_personal_no_escribe_la_designacion(self):
        # Ni el técnico de la unidad sobre su propia ficha, ni una cuenta ajena, ni quien no ha entrado.
        for actor in (self.tecnico, self.ajeno):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                self.assertEqual(self.client.post(self.destino, self.datos()).status_code, 403)
                self.assertEqual(self.designacion(), ('', '', None))
        self.client.logout()
        self.assertEqual(self.client.post(self.destino, self.datos()).status_code, 302)
        self.assertEqual(self.designacion(), ('', '', None))
        # La coordinación no modifica la asignación de otra coordinación (aquí, la suya propia).
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(self.destino, self.datos(
            registro_id=self.coordinacion.pk, usuario_id=self.coordinador.pk, nombre='Ciro Coordinador',
            rol='coordinacion'))
        self.assertEqual(respuesta.status_code, 403)
        self.coordinacion.refresh_from_db()
        self.assertEqual(self.coordinacion.acto_designacion, '')

    def test_el_panel_ofrece_los_campos_y_los_precarga_solo_a_quien_edita_personal(self):
        ResponsableUnidad.objects.filter(pk=self.asignacion.pk).update(
            formacion='Tecnólogo de prueba en electrónica', acto_designacion='Memorando de prueba 015',
            fecha_designacion=date(2026, 3, 2))
        panel = reverse('gestion_unidad', args=[self.unidad.slug])
        self.client.force_login(self.administradora)
        respuesta = self.client.get(panel, {'view': 'configuracion'})
        self.assertEqual(respuesta.status_code, 200)
        for campo in ('<input name="formacion" maxlength="200">', '<input name="acto_designacion" maxlength="200"',
                      '<input type="date" name="fecha_designacion">',
                      'data-field-formacion="Tecnólogo de prueba en electrónica"',
                      'data-field-acto_designacion="Memorando de prueba 015"',
                      'data-field-fecha_designacion="2026-03-02"'):
            self.assertContains(respuesta, campo)
        # El técnico entra a la configuración, pero no recibe el botón que precarga los datos del personal.
        self.client.force_login(self.tecnico)
        respuesta = self.client.get(panel, {'view': 'configuracion'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context['puede_administrar_personal'])
        self.assertNotContains(respuesta, 'data-field-acto_designacion')

    def test_el_admin_de_django_edita_los_tres_campos(self):
        self.client.force_login(self.superusuario)
        ficha = self.client.get(reverse('admin:gestion_unidades_responsableunidad_change', args=[self.asignacion.pk]))
        self.assertEqual(ficha.status_code, 200)
        for campo in ('formacion', 'acto_designacion', 'fecha_designacion'):
            self.assertContains(ficha, f'name="{campo}"')
        # También en la tabla de responsables del editor de la unidad.
        from apps.gestion_unidades.admin.configuracion import ResponsableUnidadAdmin, ResponsableUnidadInline
        for clase in (ResponsableUnidadAdmin, ResponsableUnidadInline):
            self.assertLessEqual({'formacion', 'acto_designacion', 'fecha_designacion'}, set(clase.fields))
