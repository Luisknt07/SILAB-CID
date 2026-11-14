from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, unidades_gestionables
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


class AccesoAdminUnidadesTests(BaseDelExpediente):
    def setUp(self):
        self.personal = get_user_model().objects.create_user('personal-acceso', password='clave-segura')

    def preparar_coordinacion(self):
        self.personal.is_staff = True
        self.personal.save(update_fields=['is_staff'])
        return ResponsableUnidad.objects.create(
            unidad=self.laboratorio, usuario=self.personal, nombre='Coordinación',
            rol='coordinacion', activo=True, permisos_operativos={'recursos': True})

    def test_staff_sin_permisos_globales_entra_al_panel(self):
        self.preparar_coordinacion()
        self.client.force_login(self.personal)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertRedirects(self.client.get(reverse('admin:login')),
                            reverse('admin:index'), fetch_redirect_response=False)
        panel = self.client.get(reverse('gestion_unidad', args=[self.laboratorio.slug]), {'view': 'configuracion'})
        self.assertEqual(panel.status_code, 200)
        self.assertTrue(panel.context['puede_administrar_personal'])
        self.assertTrue(panel.context['puede_operar_configuracion'])
        self.assertContains(panel, reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk]))
        self.assertNotContains(panel, '<option value="coordinacion">')

    def test_coordinacion_asigna_operadores_solo_en_su_unidad(self):
        asignacion = self.preparar_coordinacion()
        self.client.force_login(self.personal)
        destino = reverse('gestion_operacion_accion', args=[self.laboratorio.slug])
        datos = {'modulo': 'responsable', 'nombre': 'Operador', 'usuario_id': self.decano.pk,
                 'rol': 'tecnico', 'activo': 'true', 'permiso_recursos': 'true'}
        for rol in ('laboratorista', 'tecnico', 'responsable_tecnico', 'soporte'):
            datos['rol'] = rol
            respuesta = self.client.post(destino, datos)
            self.assertEqual(respuesta.status_code, 200, respuesta.content)
            datos['registro_id'] = respuesta.json()['registro']['id']
        self.assertEqual(self.client.post(reverse('gestion_operacion_accion', args=[self.suelto.slug]), datos).status_code, 403)
        self.assertEqual(self.client.post(destino, {**datos, 'rol': 'coordinacion'}).status_code, 403)
        self.assertEqual(self.client.post(destino, {**datos, 'permiso_configuracion': 'true'}).status_code, 200)
        self.assertEqual(self.client.post(destino, {**datos, 'usuario_id': self.direccion.pk}).status_code, 403)
        self.assertEqual(self.client.post(destino, {**datos, 'registro_id': asignacion.pk, 'accion': 'desactivar'}).status_code, 403)
        asignacion.refresh_from_db()
        self.assertTrue(asignacion.activo)

    def test_anonimo_usa_el_login_existente(self):
        response = self.client.get(reverse('admin:login'), {'next': reverse('admin:index')})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login') + '?next='))

    def test_personal_de_una_unidad_entra_a_su_panel_sin_elevar_privilegios(self):
        ResponsableUnidad.objects.create(unidad=self.laboratorio, usuario=self.personal,
                                         nombre='Personal de prueba', rol='laboratorista', activo=True,
                                         permisos_operativos={'recursos': True, 'configuracion': False})
        self.client.force_login(self.personal)
        response = self.client.get(reverse('admin:login'))
        self.assertRedirects(response, reverse('gestion_unidad', args=[self.laboratorio.slug]), fetch_redirect_response=False)
        self.personal.refresh_from_db()
        self.assertFalse(self.personal.is_staff)
        self.assertFalse(self.personal.is_superuser)
        self.assertFalse(unidades_gestionables(self.personal).filter(pk=self.suelto.pk).exists())
        self.assertFalse(puede_operar_modulo_unidad(self.personal, self.laboratorio, 'configuracion'))
        response = self.client.get(reverse('gestion_unidad', args=[self.suelto.slug]))
        self.assertIn(response.status_code, (403, 404))

    def test_varias_unidades_vuelven_al_selector_del_perfil(self):
        self.client.force_login(self.coordinador)
        response = self.client.get(reverse('admin:login'))
        self.assertEqual(response.url, reverse('admin:index'))

    def test_admin_contenidos_aisla_unidades_y_no_permite_cambiar_privilegios(self):
        self.preparar_coordinacion()
        self.personal.is_staff = False
        self.personal.save(update_fields=['is_staff'])
        self.client.force_login(self.personal)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        lista = self.client.get(reverse('admin:directorio_unidades_unidad_changelist'))
        self.assertEqual(list(lista.context['cl'].queryset.values_list('pk', flat=True)), [self.laboratorio.pk])
        destino = reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk])
        formulario = self.client.get(destino)
        self.assertEqual(formulario.status_code, 200)
        campos = formulario.context['adminform'].form.fields
        self.assertIn('descripcion', campos)
        self.assertNotIn('administrador', campos)
        self.assertNotIn('nombre', campos)
        nombre_original = self.laboratorio.nombre
        datos = {}
        for nombre, valor in formulario.context['adminform'].form.initial.items():
            from django.forms import FileField
            if nombre in campos and isinstance(campos[nombre], FileField):
                continue
            if nombre not in campos or valor is None:
                continue
            if isinstance(valor, (list, tuple)):
                valor = [getattr(item, 'pk', item) for item in valor]
            datos[nombre] = valor
        for inline in formulario.context['inline_admin_formsets']:
            prefix = inline.formset.prefix
            datos.update({f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                          f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000'})
        datos.update({'nombre': 'Cambio no autorizado', 'descripcion': 'Contenido actualizado',
                      'administrador': self.personal.pk, '_save': 'Guardar'})
        respuesta = self.client.post(destino, datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['adminform'].form.errors)
        self.laboratorio.refresh_from_db()
        self.assertEqual(self.laboratorio.descripcion, 'Contenido actualizado')
        self.assertEqual(self.laboratorio.nombre, nombre_original)
        self.assertEqual(self.laboratorio.administrador_id, self.coordinador.pk)
        otra = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.suelto.pk]))
        self.assertIn(otra.status_code, (302, 403, 404))
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 403)

    def test_autonomia_vigente_por_defecto_y_revocacion(self):
        from apps.core.roles import MODULOS_OPERATIVOS
        from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad
        asignacion = self.preparar_coordinacion()
        asignacion.permisos_operativos = dict.fromkeys(MODULOS_OPERATIVOS, False)
        asignacion.save()
        self.assertTrue(all(permisos_operativos_unidad(self.personal, self.laboratorio).values()))
        self.assertFalse(any(permisos_operativos_unidad(self.personal, self.suelto).values()))
        self.client.force_login(self.personal)
        indice = self.client.get(reverse('admin:index'))
        self.assertContains(indice, reverse('gestion_unidad', args=[self.laboratorio.slug]))
        self.assertContains(indice, 'data-panel-direct')
        self.assertNotContains(indice, reverse('gestion_unidad', args=[self.suelto.slug]))
        areas = indice.context['app_list']
        self.assertEqual(len(areas), 1)
        self.assertTrue(indice.context['solo_gestion_unidades'])
        self.assertNotContains(indice, 'data-admin-target="resumen"')
        self.assertNotContains(indice, 'data-admin-target="laboratorios"')
        self.assertGreater(len(areas[0]['models']), 2)
        self.assertEqual(areas[0]['models'][0]['admin_url'], reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk]))
        self.assertTrue(areas[0]['models'][1]['navegacion_directa'])
        asignacion.activo = False
        asignacion.save()
        self.assertFalse(any(permisos_operativos_unidad(self.personal, self.laboratorio).values()))
        self.assertFalse(self.client.get(reverse('admin:index')).status_code == 200)

    def test_documentos_existentes_sin_relaciones_de_otra_unidad(self):
        from apps.recursos.models.recursos import Recurso
        self.preparar_coordinacion()
        propio = Recurso.objects.create(unidad=self.laboratorio, nombre='Manual local', url='https://example.org/manual')
        ajeno = Recurso.objects.create(unidad=self.suelto, nombre='Manual ajeno', url='https://example.org/otro')
        self.client.force_login(self.personal)
        respuesta = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk]))
        self.assertEqual(respuesta.status_code, 200)
        inline = next(item for item in respuesta.context['inline_admin_formsets'] if item.formset.model is Recurso)
        self.assertEqual(list(inline.formset.queryset), [propio])
        self.assertNotIn(ajeno.pk, inline.formset.forms[0].fields['reemplaza_a'].queryset.values_list('pk', flat=True))
        self.assertEqual(self.client.get(reverse('admin:directorio_unidades_unidad_delete', args=[self.laboratorio.pk])).status_code, 403)

    def test_superusuario_conserva_destino_y_rechaza_redireccion_externa(self):
        self.client.force_login(self.direccion)
        destino = reverse('admin:documentos_documentoexpediente_changelist')
        self.assertRedirects(self.client.get(reverse('admin:login'), {'next': destino}), destino,
                             fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('admin:login'), {'next': 'https://externo.test/'}),
                             reverse('admin:index'), fetch_redirect_response=False)

    def test_usuario_sin_unidad_no_recibe_acceso_ni_otro_login(self):
        self.client.force_login(self.personal)
        self.assertEqual(self.client.get(reverse('admin:login')).status_code, 403)
