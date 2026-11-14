"""Delegaciones seguras, revocacion y aislamiento entre unidades."""

from datetime import date
from pathlib import Path
import subprocess
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.translation import override

from apps.core.checks import roles_configurados
from apps.core.roles import (
    politica_predeterminada, politica_roles,
    permisos_recomendados, resolver_delegacion, validar_delegacion,
)
from config.roles import configuracion_roles
from apps.gestion_unidades.presentation.permisos import permisos_operativos_responsable, permisos_operativos_unidad, puede_administrar_personal_unidad, puede_gestionar_unidad, unidades_gestionables
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class PoliticaRolesTests(SimpleTestCase):
    def setUp(self):
        self.politica = politica_roles(politica_predeterminada())

    def test_predeterminados_conservan_delegaciones_y_no_dan_configuracion(self):
        for rol in self.politica:
            permisos = permisos_recomendados(rol, True, self.politica)
            self.assertFalse(permisos['configuracion'])
            self.assertFalse(permisos['corregir_cerradas'])
        self.assertTrue(permisos_recomendados('coordinacion', False, self.politica)['reservas'])
        self.assertFalse(permisos_recomendados('laboratorista', False, self.politica)['reservas'])
        self.assertTrue(permisos_recomendados('laboratorista', True, self.politica)['reservas'])
        self.assertFalse(any(permisos_recomendados('otro', True, self.politica).values()))

    def test_booleano_falso_prevalece_sobre_recomendacion(self):
        permisos = resolver_delegacion('coordinacion', True, {'reservas': False}, self.politica)
        self.assertFalse(permisos['reservas'])
        self.assertTrue(permisos['agenda'])

    def test_datos_malformados_no_conceden_ni_recomendaciones(self):
        for dato in [None, [], False, 'false', {'reservas': 'false'}, {'reservas': 1},
                     {'reservas': 0}, {'reservas': None}, {'superadmin': True}]:
            with self.subTest(dato=dato):
                with self.assertRaises(ValueError):
                    validar_delegacion(dato)
                self.assertFalse(any(resolver_delegacion('coordinacion', True, dato, self.politica).values()))

    def test_rol_desconocido_no_concede_delegaciones_explicitas(self):
        self.assertFalse(any(resolver_delegacion('superadmin', True, {'reservas': True}, self.politica).values()))

    def test_configuracion_invalida_diagnosticada_al_arrancar(self):
        for politica in [None, [], {'superadmin': []}, {'tecnico': ['todo']},
                         {'tecnico': 'recursos'}, {'tecnico': [True]},
                         {'tecnico': ['recursos', 'recursos']}]:
            with self.subTest(politica=politica), override_settings(OPERATIONAL_ROLES=politica):
                self.assertEqual(roles_configurados(None)[0].id, 'slcid.E006')

    def test_json_no_ejecuta_codigo_y_rechaza_duplicados(self):
        for contenido in ['__import__("os")', '{"tecnico":[],"tecnico":["finanzas"]}', 'x'*100_001]:
            with self.subTest(contenido=contenido[:50]), self.assertRaises(ValueError):
                configuracion_roles({'OPERATIONAL_ROLES_JSON': contenido})
        self.assertEqual(configuracion_roles({'DB_PASSWORD': 'secreto'}), politica_predeterminada())

    def test_configuracion_inmutable_y_aislada_entre_instalaciones(self):
        entrada = {'tecnico': ['inventario']}
        politica = politica_roles(entrada)
        entrada['tecnico'].append('finanzas')
        self.assertEqual(politica['tecnico'], ('inventario',))
        with self.assertRaises(TypeError):
            politica['tecnico'] = ()
        self.assertNotIn('finanzas', politica_roles({'tecnico': ['recursos']})['tecnico'])

    def test_nucleo_se_importa_sin_django_o_unidades(self):
        codigo = (
            'import sys; import apps.core.roles; '
            'assert not any(m == "django" or m.startswith("webcitt") for m in sys.modules)'
        )
        resultado = subprocess.run([sys.executable, '-c', codigo],
                                  cwd=Path(__file__).resolve().parents[2], capture_output=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


class DelegacionesUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.principal = Usuario.objects.create_user('principal.roles')
        cls.tecnico = Usuario.objects.create_user('tecnico.roles')
        cls.declarado = Usuario.objects.create_user('usuario.declarado')
        cls.superusuario = Usuario.objects.create_superuser('super.roles', password=None)
        for usuario in [cls.principal, cls.tecnico, cls.declarado]:
            identificar(usuario, tipo_usuario='administrativo')
        cls.unidad = Unidad.objects.create(nombre='Unidad A', descripcion='QA',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios', administrador=cls.principal,
            slug='unidad-a-roles')
        cls.otra = Unidad.objects.create(nombre='Unidad B', descripcion='QA',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios', slug='unidad-b-roles')
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.tecnico,
            rol='tecnico', permisos_operativos={'inventario': True, 'finanzas': False})

    def test_nombre_institucion_y_tipo_declarado_no_delegan(self):
        perfil = self.declarado.profile
        for tipo in ['estudiante', 'docente', 'investigador', 'administrativo']:
            with self.subTest(tipo=tipo):
                perfil.tipo_usuario = tipo
                perfil.institucion = 'UPEC - administrador global'
                perfil.save()
                self.assertFalse(puede_gestionar_unidad(self.declarado, self.unidad))
                self.assertFalse(any(permisos_operativos_unidad(self.declarado, self.unidad).values()))

    def test_delegacion_no_se_extiende_a_otra_unidad(self):
        self.assertTrue(permisos_operativos_unidad(self.tecnico, self.unidad)['inventario'])
        self.assertFalse(any(permisos_operativos_unidad(self.tecnico, self.otra).values()))
        self.assertEqual(list(unidades_gestionables(self.tecnico)), [self.unidad])

    def test_cuenta_inactiva_denegada_incluso_principal_y_superusuario(self):
        for usuario in [self.tecnico, self.principal, self.superusuario]:
            with self.subTest(usuario=usuario.username):
                usuario.is_active = False
                usuario.save(update_fields=['is_active'])
                self.assertFalse(unidades_gestionables(usuario).exists())
                self.assertFalse(puede_gestionar_unidad(usuario, self.unidad))
                self.assertFalse(puede_administrar_personal_unidad(usuario, self.unidad))
                self.assertFalse(any(permisos_operativos_unidad(usuario, self.unidad).values()))

    def test_desactivar_y_reactivar_preserva_matriz_sin_autorizar_desactivado(self):
        self.responsable.activo = False
        self.responsable.save(update_fields=['activo'])
        self.assertFalse(puede_gestionar_unidad(self.tecnico, self.unidad))
        self.assertFalse(any(permisos_operativos_unidad(self.tecnico, self.unidad).values()))
        self.assertTrue(permisos_operativos_responsable(self.responsable)['inventario'])
        self.responsable.activo = True
        self.responsable.save(update_fields=['activo'])
        self.assertTrue(permisos_operativos_unidad(self.tecnico, self.unidad)['inventario'])

    def test_full_clean_rechaza_json_invalido_con_error_de_campo(self):
        for matriz in [['inventario'], {'inventario': 'false'}, {'inventario': 1}, {'inexistente': True}]:
            with self.subTest(matriz=matriz):
                self.responsable.permisos_operativos = matriz
                with self.assertRaises(ValidationError) as error:
                    self.responsable.full_clean()
                self.assertIn('permisos_operativos', error.exception.message_dict)

    def test_datos_guardados_sin_validar_denegados_en_endpoint_real(self):
        self.responsable.permisos_operativos = {'inventario': 'false', 'recursos': True}
        self.responsable.save(update_fields=['permisos_operativos'])
        self.assertFalse(any(permisos_operativos_unidad(self.tecnico, self.unidad).values()))
        self.client.force_login(self.tecnico)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]),
                                    {'modulo': 'inventario', 'accion': 'guardar'})
        self.assertEqual(respuesta.status_code, 403)

    def test_politica_por_instalacion_cambia_recomendaciones_sin_borrar_delegacion(self):
        with override_settings(OPERATIONAL_ROLES={'tecnico': ['finanzas']}):
            permisos = permisos_operativos_unidad(self.tecnico, self.unidad)
            self.assertTrue(permisos['inventario'])
            self.assertFalse(permisos['finanzas'])
            self.assertFalse(permisos['recursos'])
        self.assertTrue(permisos_operativos_unidad(self.tecnico, self.unidad)['recursos'])

    def test_cuatro_tipos_de_unidad_comparten_contrato_sin_compartir_delegaciones(self):
        for dependencia in ['laboratorios', 'plantas_piloto', 'observatorios', 'centro_experimental']:
            with self.subTest(dependencia=dependencia):
                unidad = Unidad.objects.create(nombre='Unidad '+dependencia, descripcion='QA',
                    fecha_inicio=date(2026, 1, 1), dependencia=dependencia)
                responsable = ResponsableUnidad.objects.create(unidad=unidad, usuario=self.declarado,
                    rol='otro', permisos_operativos={'reportes': True})
                self.assertTrue(permisos_operativos_unidad(self.declarado, unidad)['reportes'])
                self.assertFalse(any(permisos_operativos_unidad(self.declarado, self.unidad).values()))
                responsable.activo = False
                responsable.save(update_fields=['activo'])
                self.assertFalse(any(permisos_operativos_unidad(self.declarado, unidad).values()))

    def test_superusuario_y_principal_activos_conservan_accesos(self):
        self.assertTrue(all(permisos_operativos_unidad(self.principal, self.unidad).values()))
        self.assertTrue(all(permisos_operativos_unidad(self.superusuario, self.otra).values()))
        self.assertFalse(any(permisos_operativos_unidad(AnonymousUser(), self.unidad).values()))

    def test_cuenta_sin_guardar_no_coincide_con_administrador_vacio(self):
        usuario = get_user_model()(username='sin-guardar', is_active=True)
        self.assertIsNone(usuario.pk)
        self.assertFalse(any(permisos_operativos_unidad(usuario, self.otra).values()))
        self.assertFalse(puede_administrar_personal_unidad(usuario, self.otra))
        self.assertFalse(unidades_gestionables(usuario).exists())

    def test_error_de_matriz_se_traduce_en_ingles(self):
        self.responsable.permisos_operativos = {'reservas': 'false'}
        with override('en'), self.assertRaises(ValidationError) as error:
            self.responsable.full_clean()
        self.assertIn('Each permission', error.exception.message_dict['permisos_operativos'][0])
