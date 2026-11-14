"""La identidad local conserva referencias sin duplicar autenticación o privilegios."""
from datetime import timedelta

from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.centros_id.areas import opciones_areas
from apps.centros_id.formularios import CentroIDForm
from apps.centros_id.identidades import identidad_de, principal_vigente
from apps.centros_id.models import (
    CentroID, Componente, CuentaCentro, EquipoCentro, GestorCentro, HabilitacionEquipo,
    RegistroSolicitud, SolicitudCentro,
)


class IdentidadesCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.gestor = Usuario.objects.create_user('identidad.gestor', first_name='Ana', last_name='Pérez',
                                                 email='ana@example.test', is_staff=True)
        cls.solicitante = Usuario.objects.create_user('identidad.solicitante')
        cls.ajeno = Usuario.objects.create_user('identidad.ajeno')
        cls.centro = CentroID.objects.create(nombre='Centro de pruebas', slug='identidad-centro',
            area=opciones_areas()[0][0], proposito='Validación', responsable=identidad_de(cls.gestor))

    def test_proyeccion_preserva_id_sin_credenciales_ni_privilegios(self):
        cuenta = identidad_de(self.gestor)
        self.assertEqual(cuenta.pk, self.gestor.pk)
        self.assertEqual(cuenta.get_full_name(), 'Ana Pérez')
        self.assertEqual(cuenta.email, 'ana@example.test')
        campos = {f.name for f in CuentaCentro._meta.fields}
        self.assertEqual(campos, {'id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'actualizada_en'})
        self.assertFalse(hasattr(cuenta, 'is_superuser'))
        self.assertFalse(hasattr(cuenta, 'check_password'))
        self.assertFalse(CuentaCentro.objects.filter(pk=self.ajeno.pk).exists())

    def test_proyeccion_actualiza_presentacion_solo_desde_autoridad(self):
        get_user_model().objects.filter(pk=self.gestor.pk).update(first_name='Nombre actualizado', is_active=False)
        cuenta = identidad_de(self.gestor)
        self.assertEqual(cuenta.first_name, 'Nombre actualizado')
        self.assertFalse(cuenta.is_active)
        self.assertIsNone(principal_vigente(self.gestor))

    def test_no_acepta_identidad_sin_guardar_ni_fabricada(self):
        with self.assertRaises(ValidationError):
            identidad_de(get_user_model()(username='sin.guardar'))
        with self.assertRaises(ValidationError):
            identidad_de(CuentaCentro(id=self.gestor.pk, username='falsa'))
        self.assertIsNone(principal_vigente(CuentaCentro.objects.get(pk=self.gestor.pk)))
        self.assertIsNone(principal_vigente(True))

    def test_permiso_ignora_privilegios_fabricados_y_proyeccion_local(self):
        falso = get_user_model()(pk=self.ajeno.pk, username='falso', is_superuser=True)
        falso._state.adding = False
        self.assertFalse(self.centro.puede_gestionar(falso))
        self.assertFalse(self.centro.puede_gestionar(identidad_de(self.gestor)))
        self.assertFalse(self.centro.puede_gestionar(self.gestor.pk))
        self.assertTrue(self.centro.puede_gestionar(self.gestor))
        self.assertFalse(self.centro.puede_gestionar(self.ajeno))

    def test_cuenta_desactivada_en_auth_no_gestiona_con_proyeccion_antigua(self):
        self.assertTrue(CuentaCentro.objects.get(pk=self.gestor.pk).is_active)
        get_user_model().objects.filter(pk=self.gestor.pk).update(is_active=False)
        self.assertFalse(self.centro.puede_gestionar(self.gestor))

    def test_todas_las_relaciones_del_dominio_son_locales(self):
        referencias = []
        for modelo in apps.get_app_config('centros_id').get_models(include_auto_created=True):
            for campo in modelo._meta.get_fields():
                if campo.is_relation and not campo.auto_created:
                    self.assertNotEqual(campo.related_model, get_user_model(), (modelo.__name__, campo.name))
                    if campo.related_model is CuentaCentro and not campo.many_to_many:
                        referencias.append((modelo.__name__, campo.name))
        self.assertEqual(len(referencias), 20)  # 19 FK y la tabla puente.
        self.assertEqual(GestorCentro._meta.db_table, 'centros_id_centroid_gestores')
        self.assertEqual(GestorCentro._meta.get_field('cuenta').column, 'user_id')
        self.assertEqual(GestorCentro._meta.get_field('centro').column, 'centroid_id')

    def test_escritura_antigua_convierte_objeto_antes_de_asignar_la_fk(self):
        self.centro.responsable = self.ajeno
        self.assertIsInstance(self.centro.responsable, CuentaCentro)
        self.centro.save()
        self.assertTrue(CentroID.objects.filter(responsable=self.ajeno).exists())
        self.assertTrue(CentroID.objects.filter(Q(responsable=self.ajeno)).exists())
        self.assertTrue(CentroID.objects.filter(responsable__in=[self.ajeno]).exists())
        with self.assertRaises(ValueError):
            CentroID.objects.filter(responsable__in=get_user_model().objects.all()).exists()

    def test_gestores_acepta_compatibilidad_sin_relacionar_modelos_auth(self):
        self.centro.gestores.add(self.ajeno)
        self.assertTrue(self.centro.puede_gestionar(self.ajeno))
        self.assertIsInstance(self.centro.gestores.get(pk=self.ajeno.pk), CuentaCentro)
        self.centro.gestores.set([self.solicitante])
        self.assertEqual(list(self.centro.gestores.values_list('pk', flat=True)), [self.solicitante.pk])
        self.centro.gestores.remove(self.solicitante)
        self.assertFalse(self.centro.gestores.exists())

    def test_formulario_selecciona_auth_activo_y_proyecta_solo_elegido(self):
        campo = CentroID._meta.get_field('responsable').formfield()
        self.assertIs(campo.queryset.model, get_user_model())
        cuenta = campo.clean(str(self.ajeno.pk))
        self.assertIsInstance(cuenta, CuentaCentro)
        self.assertEqual(cuenta.pk, self.ajeno.pk)
        self.assertFalse(CuentaCentro.objects.filter(pk=self.solicitante.pk).exists())
        get_user_model().objects.filter(pk=self.solicitante.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            campo.clean(str(self.solicitante.pk))

    def test_formulario_multiple_conserva_ids_y_guarda_puente_local(self):
        Clase = forms.modelform_factory(CentroID, form=CentroIDForm,
            fields=('nombre', 'slug', 'area', 'proposito', 'responsable'))
        form = Clase(data={'nombre': self.centro.nombre, 'slug': self.centro.slug, 'area': self.centro.area,
            'proposito': self.centro.proposito, 'responsable': self.gestor.pk,
            'cuentas_gestoras': [self.ajeno.pk]}, instance=self.centro)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(list(self.centro.gestores.values_list('pk', flat=True)), [self.ajeno.pk])
        self.assertFalse(CuentaCentro.objects.filter(pk=self.solicitante.pk).exists())

    def test_campo_inmovil_conserva_referencia_ante_baja_auth(self):
        cuenta = identidad_de(self.ajeno)
        identificador = self.ajeno.pk
        self.ajeno.delete()
        campo = HabilitacionEquipo._meta.get_field('usuario').formfield()
        campo.disabled = True
        self.assertEqual(campo.clean(identificador).pk, cuenta.pk)

    def test_baja_auth_conserva_solicitud_historial_y_nombre_local(self):
        solicitud = SolicitudCentro.objects.create(centro=self.centro, usuario=identidad_de(self.solicitante),
            titulo='Validación', problema='Necesidad', resultado_esperado='Informe')
        registro = RegistroSolicitud.objects.create(solicitud=solicitud, autor=identidad_de(self.solicitante),
            estado_nuevo='recibida', detalle='Información conservada')
        identificador = self.solicitante.pk
        self.solicitante.delete()
        solicitud.refresh_from_db()
        registro.refresh_from_db()
        self.assertEqual(solicitud.usuario_id, identificador)
        self.assertEqual(registro.autor_id, identificador)
        self.assertEqual(registro.autor.username, 'identidad.solicitante')
        with self.assertRaises(ProtectedError):
            CuentaCentro.objects.get(pk=identificador).delete()

    def test_verificador_se_autoriza_en_auth_y_no_con_snapshot_de_privilegios(self):
        area = Componente.objects.create(centro=self.centro, codigo='validacion', nombre='Validación',
            tipo='laboratorio', resumen='Pruebas', descripcion='Pruebas técnicas')
        equipo = EquipoCentro.objects.create(componente=area, categoria='Pruebas', nombre='Equipo')
        habilitacion = HabilitacionEquipo(equipo=equipo, usuario=identidad_de(self.solicitante),
            verificador=identidad_de(self.gestor), desde=timezone.localdate(),
            hasta=timezone.localdate()+timedelta(days=30), evidencia='Acta de evaluación')
        habilitacion.full_clean()
        get_user_model().objects.filter(pk=self.gestor.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            habilitacion.full_clean()
