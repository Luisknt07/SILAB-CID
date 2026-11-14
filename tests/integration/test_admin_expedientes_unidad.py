from django.urls import reverse
from tests.integration.test_acceso_admin_unidades import AccesoAdminUnidadesTests
from apps.formacion.models.asignaturas import Asignatura


class ExpedientesAdminUnidadTests(AccesoAdminUnidadesTests):
    def test_alcance_se_aplica_a_cada_tipo_sin_permisos_globales(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.gestion_unidades.admin.alcance_unidad import AlcanceUnidadAdmin
        from apps.directorio_unidades.models.core import Unidad
        from apps.gestion_unidades.models.espacios import ResponsableUnidad
        self.preparar_coordinacion()
        peticion = RequestFactory().get('/admin/')
        peticion.user = self.personal
        for tipo in ('plantas_piloto', 'centros_experimentales', 'observatorios'):
            panel = next(a for m, a in admin.site._registry.items()
                         if m._meta.app_label == tipo and isinstance(a, AlcanceUnidadAdmin))
            unidad = Unidad.objects.create(nombre=f'Unidad {tipo}', slug=f'unidad-{tipo}', dependencia=panel.codigos()[0],
                                           fecha_inicio=self.laboratorio.fecha_inicio)
            ResponsableUnidad.objects.create(unidad=unidad, usuario=self.personal, nombre='Coordinación', rol='coordinacion', activo=True)
            for modelo, administrador in admin.site._registry.items():
                if modelo._meta.app_label == tipo and isinstance(administrador, AlcanceUnidadAdmin):
                    self.assertTrue(administrador.has_module_permission(peticion), modelo.__name__)
                    self.assertTrue(administrador.has_view_permission(peticion), modelo.__name__)
        self.assertFalse(self.personal.get_all_permissions())

    def test_listas_y_formularios_acotados_con_guardado(self):
        self.preparar_coordinacion()
        self.client.force_login(self.personal)
        propia = Asignatura.objects.create(unidad=self.laboratorio, codigo='A1', nombre='Asignatura propia')
        ajena = Asignatura.objects.create(unidad=self.suelto, codigo='A2', nombre='Asignatura ajena')
        lista = self.client.get(reverse('admin:laboratorios_asignatura_changelist'), {'todas': '1'})
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(list(lista.context['cl'].queryset.values_list('pk', flat=True)), [propia.pk])
        alta = reverse('admin:laboratorios_asignatura_add')
        formulario = self.client.get(alta)
        self.assertEqual(formulario.status_code, 200)
        self.assertEqual(list(formulario.context['adminform'].form.fields['unidad'].queryset.values_list('pk', flat=True)), [self.laboratorio.pk])
        datos = {'unidad': self.suelto.pk, 'codigo': 'NUEVA', 'nombre': 'Nueva', 'estudiantes': 1, 'activa': 'on', '_save': 'Guardar'}
        respuesta = self.client.post(alta, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('unidad', respuesta.context['adminform'].form.errors)
        datos['unidad'] = self.laboratorio.pk
        self.assertEqual(self.client.post(alta, datos).status_code, 302)
        cambio = reverse('admin:laboratorios_asignatura_change', args=[propia.pk])
        datos.update({'unidad': self.suelto.pk, 'codigo': 'A1', 'nombre': 'Editada'})
        self.assertEqual(self.client.post(cambio, datos).status_code, 302)
        propia.refresh_from_db()
        self.assertEqual(propia.nombre, 'Editada')
        self.assertEqual(propia.unidad_id, self.laboratorio.pk)
        self.assertIn(self.client.get(reverse('admin:laboratorios_asignatura_change', args=[ajena.pk])).status_code, (302, 403, 404))

    def test_todas_las_listas_del_tipo_y_selector_no_exponen_otras_unidades(self):
        from django.contrib import admin
        from apps.gestion_unidades.admin.alcance_unidad import AlcanceUnidadAdmin
        self.preparar_coordinacion()
        self.client.force_login(self.personal)
        for modelo, administrador in admin.site._registry.items():
            if modelo._meta.app_label != 'laboratorios' or not isinstance(administrador, AlcanceUnidadAdmin):
                continue
            with self.subTest(modelo=modelo.__name__):
                url = reverse(f'admin:laboratorios_{modelo._meta.model_name}_changelist')
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotContains(respuesta, self.suelto.nombre)
                if administrador.has_add_permission(respuesta.wsgi_request):
                    self.assertEqual(self.client.get(reverse(f'admin:laboratorios_{modelo._meta.model_name}_add')).status_code, 200)
