"""Publicaciones academicas, contratos operativos y fallos sin alterar historia."""
from copy import deepcopy
from io import StringIO
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.checks import run_checks
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import CommandError, call_command
from django.db import connection, transaction, IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.catalogos import catalogo_academico, datos_catalogo
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional
from apps.core.presentation.catalogos import catalogo_actual, catalogo_de_despliegue, carreras, carreras_academicas
from apps.configuracion_institucional.catalogos.forms import CatalogoRevisionForm
from apps.configuracion_institucional.catalogos.models import PublicacionCatalogoAcademico, RevisionCatalogoAcademico
from apps.configuracion_institucional.catalogos.services import guardar_borrador_catalogo, publicar_catalogo
from config.perfiles.upec import CATALOGO_ACADEMICO


class CatalogosAdministrablesTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('catalogo.admin')
        self.editor = get_user_model().objects.create_user('catalogo.editor', is_staff=True)
        self.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label='configuracion_institucional', codename='add_revisioncatalogoacademico'))
        self.datos = deepcopy(CATALOGO_ACADEMICO)
        self.client.force_login(self.autor)

    def borrador(self, datos=None, titulo='Propuesta académica'):
        return guardar_borrador_catalogo(datos if datos is not None else self.datos, self.editor, titulo=titulo)

    def publicar(self, borrador, base=None):
        return publicar_catalogo(borrador.pk, self.autor, base_esperada=base)

    def ampliar(self):
        datos = deepcopy(self.datos)
        datos['facultades'] = [*datos['facultades'], ['ingenieria_qa', 'Escuela QA']]
        datos['carreras'] = [*datos['carreras'], ['sistemas_qa', 'Sistemas QA', 'ingenieria_qa']]
        return datos

    def test_upec_borrador_no_cambia_y_publicacion_integra_registro_modelos_admin_y_reserva(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.core.admin.usuarios import UserProfileAdmin
        from apps.core.usuarios.forms import RegistroInstitucionalForm
        from apps.core.models.usuarios_base import UserProfile
        from apps.reservas.models.reservas import Reserva
        from apps.core.models.periodos import VinculacionUsuarioPeriodo

        revision = self.borrador(self.ampliar())
        self.assertNotIn('sistemas_qa', dict(carreras()))
        self.publicar(revision)
        with con_catalogo_institucional():
            self.assertIn('sistemas_qa', dict(carreras_academicas()))
            for modelo, sufijo in [(UserProfile, ''), (Reserva, '_solicitante'), (VinculacionUsuarioPeriodo, '')]:
                modelo._meta.get_field('carrera' + sufijo).clean('sistemas_qa', None)
            self.assertIn('sistemas_qa', dict(RegistroInstitucionalForm().fields['carrera'].choices))
            peticion = RequestFactory().get('/admin/')
            peticion.user = self.autor
            self.assertIn('sistemas_qa', dict(UserProfileAdmin(UserProfile, admin.site).get_form(peticion)().fields['carrera'].choices))
        respuesta = self.client.get('/profile/')
        self.assertContains(respuesta, 'Sistemas QA')
        self.assertNotIn('sistemas_qa', dict(carreras()))

    def test_retirar_carrera_conserva_datos_etiqueta_historica_y_permite_reactivacion_original(self):
        from apps.core.models.usuarios_base import UserProfile

        persona = get_user_model().objects.create_user('historia.catalogo', email='privado@example.test')
        UserProfile.objects.filter(user=persona).update(tipo_usuario='docente', facultad='agropecuarias_ambientales', carrera='alimentos')
        antes = UserProfile.objects.values().get(user=persona)
        datos = deepcopy(self.datos)
        datos['carreras'] = [fila for fila in datos['carreras'] if fila[0] != 'alimentos']
        datos['carreras_historicas'] = [*datos['carreras_historicas'], ['alimentos', 'Carrera de Alimentos']]
        retirada = self.publicar(self.borrador(datos))
        with con_catalogo_institucional():
            self.assertIn('alimentos', dict(carreras()))
            self.assertNotIn('alimentos', dict(carreras_academicas()))
            self.assertIn('carrera', UserProfile.objects.get(user=persona).campos_faltantes_reserva())
        self.assertEqual(antes, UserProfile.objects.values().get(user=persona))
        reactivada = self.publicar(self.borrador(), retirada.pk)
        self.assertEqual(reactivada.relaciones_reservadas['alimentos'], 'agropecuarias_ambientales')

    @override_settings(ACADEMIC_CATALOG={'facultades': [['investigacion', 'Investigación']], 'carreras': [],
                                        'carreras_historicas': [], 'tipos_con_carrera': []},
                       INSTITUTION_IDENTITY={'nombre': 'Instituto QA', 'siglas': 'IQA'})
    def test_institucion_solo_investigacion_sin_carreras_ni_privilegios_implicitos(self):
        publicado = self.publicar(self.borrador(settings.ACADEMIC_CATALOG))
        self.assertEqual(publicado.institucion_codigo, 'IQA')
        with con_catalogo_institucional():
            self.assertEqual(carreras_academicas(), ())
            self.assertEqual(catalogo_actual().tipos_con_carrera, ())
        self.assertFalse(self.editor.groups.exists())
        self.assertFalse(self.editor.has_perm('configuracion_institucional.publicar_catalogo'))

    def test_no_retira_codigos_anteriores_aunque_sin_uso_ni_reasigna_relaciones(self):
        invalidos = []
        eliminado = deepcopy(self.datos)
        eliminado['carreras'] = [fila for fila in eliminado['carreras'] if fila[0] != 'alimentos']
        invalidos.append(eliminado)
        reasignado = deepcopy(self.datos)
        reasignado['carreras'] = [[c, e, 'salud_educacion' if c == 'alimentos' else f] for c, e, f in reasignado['carreras']]
        invalidos.append(reasignado)
        for datos in invalidos:
            with self.subTest(datos=datos['carreras'][-1]):
                with self.assertRaises(ValidationError):
                    self.publicar(self.borrador(datos))
                self.assertIsNone(PublicacionCatalogoAcademico.objects.get(pk=1).revision_id)
        self.assertEqual(RevisionCatalogoAcademico.objects.filter(estado='publicada').count(), 0)

    def test_reactivacion_reasignada_y_reuso_clasificacion_historica_se_denegan(self):
        datos = deepcopy(self.datos)
        datos['carreras'] = [fila for fila in datos['carreras'] if fila[0] != 'alimentos']
        datos['carreras_historicas'] = [*datos['carreras_historicas'], ['alimentos', 'Alimentos']]
        publicada = self.publicar(self.borrador(datos))
        reasignada = deepcopy(self.datos)
        reasignada['carreras'] = [[c, e, 'salud_educacion' if c == 'alimentos' else f] for c, e, f in reasignada['carreras']]
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador(reasignada), publicada.pk)
        reuso = deepcopy(datos)
        reuso['carreras_historicas'] = [fila for fila in reuso['carreras_historicas'] if fila[0] != 'docente']
        reuso['carreras'] = [*reuso['carreras'], ['docente', 'Nueva carrera', 'salud_educacion']]
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador(reuso), publicada.pk)

    def test_base_obsoleta_restore_inmutable_y_restore_que_perderia_codigos_bloqueado(self):
        primero = self.publicar(self.borrador())
        viejo = self.borrador()
        cambios = deepcopy(self.datos)
        cambios['facultades'] = [[c, 'Etiqueta actualizada' if c == 'salud_educacion' else e] for c, e in cambios['facultades']]
        segundo = self.publicar(self.borrador(cambios), primero.pk)
        with self.assertRaises(ValidationError):
            self.publicar(viejo, primero.pk)
        with self.assertRaises(ValidationError):
            self.publicar(viejo, segundo.pk)
        restaurada = self.publicar(primero, segundo.pk)
        self.assertEqual(restaurada.fuente_id, primero.pk)
        self.assertEqual(restaurada.basada_en_id, segundo.pk)
        ampliada = self.publicar(self.borrador(self.ampliar()), restaurada.pk)
        with self.assertRaises(ValidationError):
            self.publicar(primero, ampliada.pk)

    def test_autoridad_fresca_staff_no_publica_permiso_revocado_ni_cuenta_inactiva(self):
        borrador = self.borrador()
        with self.assertRaises(PermissionDenied):
            publicar_catalogo(borrador.pk, self.editor, base_esperada=None)
        publicador = get_user_model().objects.create_user('publicador.catalogo', is_staff=True)
        permisos = Permission.objects.filter(content_type__app_label='configuracion_institucional',
                                             codename__in=['view_revisioncatalogoacademico', 'publicar_catalogo'])
        publicador.user_permissions.add(*permisos)
        self.assertTrue(publicador.has_perm('configuracion_institucional.publicar_catalogo'))
        publicador.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            publicar_catalogo(borrador.pk, publicador, base_esperada=None)
        get_user_model().objects.filter(pk=self.editor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.borrador()

    def test_historia_y_puntero_no_se_modifican_por_rutas_orm(self):
        revision = self.publicar(self.borrador())
        for accion in [lambda: revision.save(_desde_editor=True), lambda: revision.delete(),
                       lambda: RevisionCatalogoAcademico.objects.all().update(titulo='Otro'),
                       lambda: RevisionCatalogoAcademico.objects.all().delete(),
                       lambda: RevisionCatalogoAcademico.objects.bulk_create([]),
                       lambda: PublicacionCatalogoAcademico.objects.all().update(revision_id=None),
                       lambda: PublicacionCatalogoAcademico.objects.get(pk=1).delete()]:
            with self.assertRaises(ValidationError):
                accion()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PublicacionCatalogoAcademico(pk=2).save(_desde_editor=True)

    def test_admin_real_borrador_errores_csrf_confirmacion_y_metadata_ignorada(self):
        crear = reverse('admin:configuracion_institucional_revisioncatalogoacademico_add')
        respuesta = self.client.get(crear)
        self.assertContains(respuesta, 'catalogo-editor')
        self.assertContains(respuesta, 'configuracion_institucional/catalogos.js')
        for idioma, texto in [('en', 'Save Draft'), ('es', 'Guardar borrador')]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            self.assertContains(self.client.get(crear), texto)
        for contenido in ['{"facultades":[],"facultades":[]}', '{', '{"secret":"no"}',
                          json.dumps({'facultades': [['x', '<script>']]})]:
            respuesta = self.client.post(crear, {'titulo': 'Propuesta', 'contenido': contenido})
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.context['form'].errors)
        respuesta = self.client.post(crear, {'titulo': 'Propuesta', 'contenido': json.dumps(self.ampliar()),
                                             'estado':'publicada', 'institucion_codigo':'AJENA', 'relaciones_reservadas':'{}'})
        self.assertEqual(respuesta.status_code, 302)
        borrador = RevisionCatalogoAcademico.objects.latest('pk')
        self.assertEqual(borrador.estado, 'borrador')
        self.assertEqual(borrador.institucion_codigo, 'UPEC')
        publicar = reverse('admin:configuracion_institucional_revisioncatalogoacademico_publicar', args=[borrador.pk])
        for idioma, texto in [('en', 'Review and publish catalog'), ('es', 'Revisar y publicar catálogo')]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            self.assertContains(self.client.get(publicar), texto)
        self.assertEqual(self.client.put(publicar).status_code, 405)
        seguro = Client(enforce_csrf_checks=True)
        seguro.force_login(self.autor)
        self.assertEqual(seguro.post(publicar, {'confirmar':'on'}).status_code, 403)
        self.assertEqual(self.client.post(publicar, {}).status_code, 200)
        self.assertIsNone(PublicacionCatalogoAcademico.objects.get(pk=1).revision_id)
        self.assertEqual(self.client.post(publicar, {'confirmar':'on'}).status_code, 302)
        self.assertEqual(self.client.post(publicar, {'confirmar':'on'}).status_code, 200)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(publicar).status_code, 403)

    def test_contexto_persistente_por_solicitud_anidado_reset_y_checks_sin_consultas(self):
        primero = self.publicar(self.borrador())
        with con_catalogo_institucional():
            original = catalogo_actual()
            siguiente = self.publicar(self.borrador(self.ampliar()), primero.pk)
            with self.assertNumQueries(0), con_catalogo_institucional():
                self.assertIs(catalogo_actual(), original)
        with con_catalogo_institucional():
            self.assertIn('sistemas_qa', dict(carreras_academicas()))
        self.assertEqual(catalogo_actual(), catalogo_de_despliegue())
        with self.assertRaises(RuntimeError), con_catalogo_institucional():
            raise RuntimeError
        self.assertEqual(catalogo_actual(), catalogo_de_despliegue())
        with self.assertNumQueries(0):
            self.assertFalse(run_checks())
        self.assertEqual(PublicacionCatalogoAcademico.objects.get(pk=1).revision_id, siguiente.pk)

    def test_proveedor_opcional_y_otra_institucion_no_hereda_publicacion(self):
        self.publicar(self.borrador(self.ampliar()))
        with override_settings(ACADEMIC_CATALOG_PROVIDER=''), self.assertNumQueries(0), con_catalogo_institucional():
            self.assertNotIn('sistemas_qa', dict(carreras_academicas()))
        with override_settings(INSTITUTION_IDENTITY={'nombre':'Otra institución', 'siglas':'OTRA'}):
            with self.assertLogs('apps.configuracion_institucional.catalogos.selectors', 'WARNING'), con_catalogo_institucional():
                self.assertEqual(catalogo_actual(), catalogo_de_despliegue())
            with self.assertRaises(ValueError), con_catalogo_institucional(estricto=True):
                pass

    def test_tabla_ausente_no_rompe_transaccion_y_auditor_explicito_falla(self):
        temporal = connection.ops.quote_name('qa_catalogo_temporal')
        tabla = connection.ops.quote_name(PublicacionCatalogoAcademico._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f'ALTER TABLE {tabla} RENAME TO {temporal}')
        try:
            with self.assertLogs('apps.configuracion_institucional.catalogos.selectors', 'WARNING'), con_catalogo_institucional():
                self.assertEqual(catalogo_actual(), catalogo_de_despliegue())
            self.assertTrue(get_user_model().objects.filter(pk=self.autor.pk).exists())
            with self.assertRaises(CommandError):
                call_command('auditar_catalogo_institucional', stdout=StringIO())
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f'ALTER TABLE {temporal} RENAME TO {tabla}')

    def test_auditor_publicacion_real_y_invalida_sin_pii_ni_certificacion_falsa(self):
        borrador = self.borrador(self.ampliar())
        self.publicar(borrador)
        salida = StringIO()
        call_command('auditar_catalogo_institucional', stdout=salida)
        self.assertIn('Catalogo compatible', salida.getvalue())
        self.assertNotIn(self.autor.username, salida.getvalue())
        with connection.cursor() as cursor:
            cursor.execute('UPDATE configuracion_institucional_publicacioncatalogoacademico SET revision_id=%s WHERE id=1', [borrador.pk])
        with self.assertRaises(CommandError):
            call_command('auditar_catalogo_institucional', stdout=StringIO())

    def test_auditoria_conteos_incompatibles_impide_alta_parcial(self):
        borrador = self.borrador()
        with patch('apps.configuracion_institucional.catalogos.services.auditar_catalogo', return_value=[
                {'codigos_desconocidos':1, 'relaciones_incompatibles':0}]):
            with self.assertRaises(ValidationError):
                self.publicar(borrador)
        self.assertEqual(RevisionCatalogoAcademico.objects.filter(estado='publicada').count(), 0)
        self.assertIsNone(PublicacionCatalogoAcademico.objects.get(pk=1).revision_id)

    def test_referencia_invalida_real_impide_publicacion_y_no_modifica_perfil(self):
        from apps.core.models.usuarios_base import UserProfile

        UserProfile.objects.filter(user=self.editor).update(carrera='no_referencia')
        antes = UserProfile.objects.values().get(user=self.editor)
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador())
        self.assertEqual(antes, UserProfile.objects.values().get(user=self.editor))
        self.assertEqual(RevisionCatalogoAcademico.objects.filter(estado='publicada').count(), 0)

    def test_editor_normaliza_payload_validado_y_limites_sin_importar_codigo(self):
        datos = {'facultades': [[f'd{i}', f'Dependencia {i}'] for i in range(200)], 'carreras': [], 'tipos_con_carrera': []}
        normalizado = datos_catalogo(catalogo_academico(datos))
        self.assertEqual(len(normalizado['facultades']), 201)
        self.assertEqual(catalogo_academico(normalizado), catalogo_academico(datos))
        form = CatalogoRevisionForm({'titulo':'Propuesta', 'contenido':json.dumps(normalizado)})
        self.assertTrue(form.is_valid(), form.errors)
        for datos in [{'secret':'x'}, {'facultades':[['../x','X']]}, {'tipos_con_carrera':['externo']},
                      {'facultades':[['x','X']], 'carreras':[['s','Carrera','ajena']]}]:
            with self.assertRaises(ValidationError):
                self.borrador(datos)
        self.assertEqual(RevisionCatalogoAcademico.objects.count(), 0)

    def test_dos_mil_carreras_usando_payload_unico_y_limite_real_de_entrada(self):
        datos = {'facultades': [['qa', 'Escuela QA']],
                 'carreras': [[f'programa_{i}', f'Programa {i}', 'qa'] for i in range(2000)],
                 'carreras_historicas': [], 'tipos_con_carrera': ['estudiante']}
        form = CatalogoRevisionForm({'titulo':'Catálogo amplio', 'contenido':json.dumps(datos)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data['contenido']['carreras']), 2000)
        datos['carreras'].append(['demasiadas', 'Fuera del límite', 'qa'])
        self.assertFalse(CatalogoRevisionForm({'titulo':'Inválido', 'contenido':json.dumps(datos)}).is_valid())
        self.assertFalse(CatalogoRevisionForm({'titulo':'Inválido', 'contenido':' ' * 1_000_001}).is_valid())

    def test_verificacion_fuera_de_http_consulta_catalogo_publicado_sin_autoaprobar(self):
        from tests.integration.utiles import identificar
        from apps.core.usuarios.verificacion import estado_verificacion, registrar_revision

        self.publicar(self.borrador(self.ampliar()))
        persona = get_user_model().objects.create_user('docente.nueva.carrera')
        perfil = identificar(persona, carrera='sistemas_qa', facultad='ingenieria_qa')
        estado = estado_verificacion(perfil)
        self.assertFalse(estado['verificada'])
        registrar_revision(perfil_id=perfil.pk, revisor=self.autor, decision='aprobada',
                           fundamento='Identidad sintética acreditada.', referencia='QA-18', huella=estado['huella'])
        self.assertTrue(estado_verificacion(perfil)['verificada'])
        self.assertFalse(persona.groups.exists())

    def test_base_invalida_no_se_sobrescribe_y_admin_muestra_bloqueo(self):
        falso = self.borrador()
        with connection.cursor() as cursor:
            cursor.execute('UPDATE configuracion_institucional_publicacioncatalogoacademico SET revision_id=%s WHERE id=1', [falso.pk])
        propuesta = self.borrador()
        with self.assertRaises(ValidationError):
            self.publicar(propuesta, falso.pk)
        ruta = reverse('admin:configuracion_institucional_revisioncatalogoacademico_publicar', args=[propuesta.pk])
        # La pantalla valida la base explícitamente; no necesita resolver el
        # proveedor global que ya es diferido para evitar consultas innecesarias.
        with patch('apps.core.presentation.catalogo_institucional.import_string') as cargar_proveedor:
            respuesta = self.client.get(ruta)
        cargar_proveedor.assert_not_called()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['problemas'])
        self.assertEqual(PublicacionCatalogoAcademico.objects.get(pk=1).revision_id, falso.pk)
        self.assertEqual(RevisionCatalogoAcademico.objects.filter(estado='publicada').count(), 0)
