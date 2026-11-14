"""Un permiso de modelo no concede el gobierno de los demás centros."""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.centros_id.areas import opciones_areas
from apps.centros_id.identidades import identidad_de
from apps.centros_id.models import (
    Aliado, CentroID, Componente, EquipoCentro, Grupo, Integrante, LineaInvestigacion, PasoProceso,
    ProcesoArea, Proyecto, Resultado,
)


class CentroIDAdminAislamientoTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.gestor = Usuario.objects.create_user('admin.centro.gestor', is_staff=True)
        cls.ajeno = Usuario.objects.create_user('admin.centro.ajeno', is_staff=True)
        cls.superusuario = Usuario.objects.create_superuser('admin.centro.global', 'global@example.test', 'clave')
        permisos = Permission.objects.filter(content_type__app_label='centros_id')
        cls.gestor.user_permissions.set(permisos)
        cls.ajeno.user_permissions.set(permisos)
        datos = {'area': opciones_areas()[0][0], 'proposito': 'Fixture de aislamiento administrativo'}
        cls.propio = CentroID.objects.create(nombre='Centro propio', slug='admin-propio',
                                             responsable=identidad_de(cls.gestor), **datos)
        cls.compartido = CentroID.objects.create(nombre='Centro con gestión asignada', slug='admin-compartido', **datos)
        cls.compartido.gestores.add(cls.gestor)
        cls.otro = CentroID.objects.create(nombre='Centro ajeno restringido', slug='admin-ajeno',
                                           responsable=identidad_de(cls.ajeno), **datos)
        cls.area_propia = Componente.objects.create(centro=cls.propio, codigo='propia', nombre='Área propia')
        cls.area_ajena = Componente.objects.create(centro=cls.otro, codigo='ajena', nombre='Área ajena restringida')

    def peticion(self, usuario):
        peticion = RequestFactory().get('/admin/')
        peticion.user = usuario
        return peticion

    def test_staff_con_permisos_de_modelo_solo_consulta_sus_centros(self):
        panel = admin.site._registry[CentroID]
        peticion = self.peticion(self.gestor)
        self.assertSetEqual(set(panel.get_queryset(peticion).values_list('pk', flat=True)),
                            {self.propio.pk, self.compartido.pk})
        self.assertTrue(panel.has_view_permission(peticion, self.propio))
        self.assertTrue(panel.has_change_permission(peticion, self.compartido))
        self.assertFalse(panel.has_view_permission(peticion, self.otro))
        self.assertFalse(panel.has_change_permission(peticion, self.otro))
        self.assertEqual(list(panel.get_formsets_with_inlines(peticion, self.otro)), [])

    def test_get_y_post_a_ficha_ajena_no_muestran_ni_modifican_datos(self):
        self.client.force_login(self.gestor)
        lista = self.client.get(reverse('admin:centros_id_centroid_changelist'))
        self.assertContains(lista, self.propio.nombre)
        self.assertNotContains(lista, self.otro.nombre)
        direccion = reverse('admin:centros_id_centroid_change', args=[self.otro.pk])
        for metodo, datos in (('get', {}), ('post', {'nombre': 'Intrusión', '_save': 'Guardar'})):
            respuesta = getattr(self.client, metodo)(direccion, datos)
            # Django trata un objeto fuera del queryset como un ID inexistente.
            self.assertRedirects(respuesta, reverse('admin:index'), fetch_redirect_response=False)
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.nombre, 'Centro ajeno restringido')
        with self.assertRaises(PermissionDenied):
            admin.site._registry[CentroID].save_model(self.peticion(self.gestor), self.otro, None, True)

    def test_staff_no_crea_ni_borra_centros_aunque_tenga_permisos_de_modelo(self):
        panel = admin.site._registry[CentroID]
        peticion = self.peticion(self.gestor)
        self.assertFalse(panel.has_add_permission(peticion))
        self.assertFalse(panel.has_delete_permission(peticion, self.propio))
        self.assertNotIn('delete_selected', panel.get_actions(peticion))
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(reverse('admin:centros_id_centroid_add')).status_code, 403)
        direccion = reverse('admin:centros_id_centroid_delete', args=[self.propio.pk])
        self.assertEqual(self.client.get(direccion).status_code, 403)
        self.assertEqual(self.client.post(direccion, {'post': 'yes'}).status_code, 403)
        self.assertTrue(CentroID.objects.filter(pk=self.propio.pk).exists())

    def test_superusuario_canonico_conserva_la_gestion_global(self):
        panel = admin.site._registry[CentroID]
        peticion = self.peticion(self.superusuario)
        self.assertEqual(panel.get_queryset(peticion).count(), 3)
        self.assertTrue(panel.has_add_permission(peticion))
        self.assertTrue(panel.has_delete_permission(peticion, self.otro))
        self.assertTrue(panel.has_change_permission(peticion, self.otro))
        self.client.force_login(self.superusuario)
        self.assertEqual(self.client.get(reverse('admin:centros_id_centroid_change', args=[self.otro.pk])).status_code, 200)

    def test_revocacion_en_auth_y_gestion_no_depende_de_la_proyeccion(self):
        panel = admin.site._registry[CentroID]
        peticion = self.peticion(self.gestor)
        self.compartido.gestores.remove(self.gestor)
        self.propio.responsable = identidad_de(self.ajeno)
        self.propio.save()
        self.assertFalse(panel.get_queryset(peticion).exists())
        self.assertFalse(panel.has_change_permission(peticion, self.propio))
        peticion.user = identidad_de(self.gestor)
        self.assertFalse(panel.get_queryset(peticion).exists())
        self.assertFalse(panel.has_change_permission(peticion, self.propio))
        self.assertFalse(panel.has_add_permission(peticion))
        get_user_model().objects.filter(pk=self.superusuario.pk).update(is_superuser=False)
        peticion.user = self.superusuario  # El objeto de la petición conserva el dato antiguo.
        self.assertFalse(panel.has_add_permission(peticion))
        self.assertFalse(panel.get_queryset(peticion).exists())

    def test_inlines_acotan_fk_al_centro_actual_incluso_para_superusuario(self):
        panel = admin.site._registry[CentroID]
        for usuario in (self.gestor, self.superusuario):
            with self.subTest(usuario=usuario.username):
                formularios = dict((inline.model, formulario) for formulario, inline in
                                   panel.get_formsets_with_inlines(self.peticion(usuario), self.propio))
                linea = formularios[LineaInvestigacion]
                opciones = linea.form.base_fields['componente'].queryset
                self.assertListEqual(list(opciones.values_list('pk', flat=True)), [self.area_propia.pk])
                prefijo = linea.get_default_prefix()
                datos = {f'{prefijo}-TOTAL_FORMS': '1', f'{prefijo}-INITIAL_FORMS': '0',
                         f'{prefijo}-MIN_NUM_FORMS': '0', f'{prefijo}-MAX_NUM_FORMS': '1000',
                         f'{prefijo}-0-nombre': 'Línea manipulada', f'{prefijo}-0-resultados': 'Resultados',
                         f'{prefijo}-0-orden': '0', f'{prefijo}-0-componente': str(self.area_ajena.pk)}
                formulario = linea(datos, instance=self.propio, prefix=prefijo)
                self.assertFalse(formulario.is_valid())
                self.assertEqual(formulario.forms[0].errors.as_data()['componente'][0].code, 'invalid_choice')
                datos[f'{prefijo}-0-componente'] = str(self.area_propia.pk)
                self.assertTrue(linea(datos, instance=self.propio, prefix=prefijo).is_valid())

    def test_selectores_multiples_de_contenido_no_muestran_registros_ajenos(self):
        linea = LineaInvestigacion.objects.create(centro=self.otro, nombre='Línea ajena', resultados='Reservados')
        persona = Integrante.objects.create(centro=self.otro, nombre='Persona ajena', rol='investigador')
        aliado = Aliado.objects.create(centro=self.otro, nombre='Aliado ajeno', tipo='empresa')
        proyecto = Proyecto.objects.create(centro=self.propio, titulo='Proyecto propio', resumen='Resumen')
        casos = ((Proyecto, proyecto, 'componentes', self.area_ajena),
                 (Proyecto, proyecto, 'equipo', persona), (Proyecto, proyecto, 'aliados', aliado),
                 (Grupo, Grupo(centro=self.propio), 'lineas', linea),
                 (Integrante, Integrante(centro=self.propio), 'lineas', linea),
                 (Resultado, Resultado(centro=self.propio), 'autores', persona))
        for usuario in (self.gestor, self.superusuario):
            for modelo, objeto, campo, ajeno in casos:
                with self.subTest(usuario=usuario.username, modelo=modelo.__name__, campo=campo):
                    formulario = admin.site._registry[modelo].get_form(self.peticion(usuario), objeto)
                    self.assertFalse(formulario.base_fields[campo].queryset.filter(pk=ajeno.pk).exists())

    def test_post_manipulado_no_vincula_m2m_ajenas_y_post_valido_si_guarda(self):
        proyecto = Proyecto.objects.create(centro=self.propio, titulo='Proyecto propio', resumen='Resumen')
        self.client.force_login(self.gestor)
        direccion = reverse('admin:centros_id_proyecto_change', args=[proyecto.pk])
        datos = {'centro': self.propio.pk, 'titulo': proyecto.titulo, 'resumen': proyecto.resumen,
                 'categoria': 'investigacion', 'estado': 'formulacion', 'etapa': 'problema', 'publicado': 'on',
                 'componentes': [self.area_ajena.pk], 'hitos_registrados-TOTAL_FORMS': '0',
                 'hitos_registrados-INITIAL_FORMS': '0', 'hitos_registrados-MIN_NUM_FORMS': '0',
                 'hitos_registrados-MAX_NUM_FORMS': '1000', '_save': 'Guardar'}
        respuesta = self.client.post(direccion, datos)
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context['adminform'].form
        self.assertEqual(formulario.errors.as_data()['componentes'][0].code, 'invalid_choice')
        self.assertFalse(proyecto.componentes.exists())
        datos['componentes'] = [self.area_propia.pk]
        respuesta = self.client.post(direccion, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertListEqual(list(proyecto.componentes.values_list('pk', flat=True)), [self.area_propia.pk])

    def test_inline_de_proceso_no_vincula_equipos_de_otro_centro(self):
        proceso = ProcesoArea.objects.create(componente=self.area_propia, nombre='Proceso propio')
        ajeno = EquipoCentro.objects.create(componente=self.area_ajena, nombre='Equipo ajeno')
        propio = EquipoCentro.objects.create(componente=self.area_propia, nombre='Equipo propio')
        panel = admin.site._registry[ProcesoArea]
        formularios = dict((inline.model, formulario) for formulario, inline in
                           panel.get_formsets_with_inlines(self.peticion(self.gestor), proceso))
        paso = formularios[PasoProceso]
        self.assertFalse(paso.form.base_fields['equipos'].queryset.filter(pk=ajeno.pk).exists())
        prefijo = paso.get_default_prefix()
        datos = {f'{prefijo}-TOTAL_FORMS': '1', f'{prefijo}-INITIAL_FORMS': '0',
                 f'{prefijo}-MIN_NUM_FORMS': '0', f'{prefijo}-MAX_NUM_FORMS': '1000',
                 f'{prefijo}-0-numero': '1', f'{prefijo}-0-nombre': 'Paso', f'{prefijo}-0-equipos': [ajeno.pk]}
        formulario = paso(datos, instance=proceso, prefix=prefijo)
        self.assertFalse(formulario.is_valid())
        self.assertEqual(formulario.forms[0].errors.as_data()['equipos'][0].code, 'invalid_choice')
        datos[f'{prefijo}-0-equipos'] = [propio.pk]
        self.assertTrue(paso(datos, instance=proceso, prefix=prefijo).is_valid())
