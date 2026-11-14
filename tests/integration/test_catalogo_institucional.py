import io
import json
import subprocess
import sys
from datetime import date

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.checks import run_checks
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.catalogos import catalogo_academico
from apps.core.checks import catalogo_configurado
from apps.core.presentation.auditoria_catalogos import auditar_catalogo
from apps.core.presentation.catalogos import catalogo_actual, carreras, carreras_academicas, facultades
from config.catalogos import configuracion_catalogo
from config.perfiles.upec import CATALOGO_ACADEMICO
from apps.gestion_unidades.admin.configuracion import HorarioOperacionUnidadForm
from apps.core.admin.usuarios import UserProfileAdmin
from apps.reservas.presentation.views import _validar_contexto_actividad
from apps.core.usuarios.forms import RegistroInstitucionalForm
from apps.reservas.models.reservas import CatalogoActividadReserva, RegistroParticipanteReserva, Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile
from apps.core.models.periodos import VinculacionUsuarioPeriodo


CATALOGO_PROPIO = {
    "facultades": [["ingenieria", "Escuela de Ingeniería"], ["salud", "Escuela de Salud"]],
    "carreras": [["sistemas", "Ingeniería de Sistemas", "ingenieria"], ["medicina", "Medicina", "salud"]],
    "tipos_con_carrera": ["estudiante", "docente"],
}
IDENTIDAD_PROPIA = {"nombre": "Universidad Técnica", "siglas": "UT"}


class CatalogoInstitucionalTests(TestCase):
    def datos(self, **cambios):
        datos = {
            "username": "catalogo.estudiante", "first_name": "Ana", "last_name": "Paz",
            "email": "ana@example.org", "password1": "Catalogo-Prueba-2026!",
            "password2": "Catalogo-Prueba-2026!", "tipo_usuario": "estudiante",
            "facultad": "ingenieria", "carrera": "sistemas", "nivel_academico": "quinto_semestre",
            "cedula": "DOC-2026", "institucion": "Texto enviado por el cliente",
        }
        datos.update(cambios)
        return datos

    def test_upec_conserva_codigos_y_separa_carreras_historicas(self):
        self.assertEqual(len(facultades()), 6)
        self.assertEqual(len(carreras_academicas()), 16)
        self.assertEqual(len(carreras()), 21)
        self.assertEqual(UserProfile.facultad_para_carrera("alimentos"), "agropecuarias_ambientales")
        self.assertIn(("docente", "Personal Docente"), carreras())
        self.assertNotIn("docente", dict(carreras_academicas()))
        self.assertEqual(configuracion_catalogo({}), CATALOGO_ACADEMICO)
        self.assertEqual(configuracion_catalogo({"INSTITUTION_PROFILE": "custom"}), {})
        catalogo = catalogo_actual()
        with self.assertRaises(AttributeError):
            catalogo.facultades = ()

    @override_settings(ACADEMIC_CATALOG=CATALOGO_PROPIO, INSTITUTION_IDENTITY=IDENTIDAD_PROPIA)
    def test_institucion_propia_coincide_en_registro_modelos_admin_y_reservas(self):
        formulario = RegistroInstitucionalForm(self.datos())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        self.assertEqual(usuario.profile.institucion, "UT")
        self.assertTrue(usuario.profile.perfil_reserva_completo)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.groups.exists())
        for modelo, sufijo in (
            (UserProfile, ""), (CatalogoActividadReserva, ""), (RegistroParticipanteReserva, ""),
            (VinculacionUsuarioPeriodo, ""), (Reserva, "_solicitante"), (Reserva, "_beneficiaria"),
        ):
            with self.subTest(modelo=modelo.__name__, sufijo=sufijo):
                modelo._meta.get_field("carrera" + sufijo).clean("sistemas", None)
                modelo._meta.get_field("facultad" + sufijo).clean("ingenieria", None)
                with self.assertRaises(ValidationError):
                    modelo._meta.get_field("carrera" + sufijo).clean("computacion", None)
        peticion = RequestFactory().get("/admin/")
        peticion.user = usuario
        form_admin = UserProfileAdmin(UserProfile, admin.site).get_form(peticion)()
        self.assertIn("sistemas", dict(form_admin.fields["carrera"].choices))
        self.assertNotIn("computacion", dict(form_admin.fields["carrera"].choices))
        self.assertIn(("docente", "Docente UT"), HorarioOperacionUnidadForm().fields["tipos_usuario_habilitados"].choices)
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse("profile"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual({fila["value"] for fila in respuesta.context["carreras_perfil"]}, {"sistemas", "medicina"})
        unidad = Unidad.objects.create(nombre="Laboratorio propio", slug="laboratorio-propio",
                                       dependencia="laboratorios", fecha_inicio=date(2026, 1, 1))
        respuesta = self.client.get(reverse("laboratorio_detalle", args=[unidad.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual({fila["codigo"] for fila in respuesta.context["carreras_reserva"]}, {"sistemas", "medicina"})

    @override_settings(ACADEMIC_CATALOG=CATALOGO_PROPIO, INSTITUTION_IDENTITY=IDENTIDAD_PROPIA)
    def test_rechaza_cruces_de_facultad_y_carreras_ajenas(self):
        for cambios in ({"facultad": "salud"}, {"carrera": "computacion"}, {"facultad": "externo"}):
            with self.subTest(cambios=cambios):
                self.assertFalse(RegistroInstitucionalForm(self.datos(**cambios)).is_valid())
        usuario = get_user_model().objects.create_user(username="modelo.cruzado")
        perfil = usuario.profile
        perfil.facultad, perfil.carrera = "salud", "sistemas"
        with self.assertRaises(ValidationError):
            perfil.full_clean()
        vinculacion = VinculacionUsuarioPeriodo(tipo_usuario="estudiante", facultad="salud", carrera="sistemas")
        with self.assertRaises(ValidationError):
            vinculacion.clean()

    def test_institucion_sin_carreras_no_hereda_catalogo_universitario(self):
        catalogo = {"facultades": [["investigacion", "Dirección de Investigación"]]}
        with override_settings(ACADEMIC_CATALOG=catalogo, INSTITUTION_IDENTITY=IDENTIDAD_PROPIA):
            formulario = RegistroInstitucionalForm(self.datos(
                tipo_usuario="investigador", facultad="investigacion", carrera="", nivel_academico="",
            ))
            self.assertTrue(formulario.is_valid(), formulario.errors)
            usuario = formulario.save()
            self.assertTrue(usuario.profile.perfil_reserva_completo)
            self.assertEqual(carreras(), ())
            self.assertEqual(VinculacionUsuarioPeriodo(tipo_usuario="investigador", facultad="investigacion").clean(), None)
        with override_settings(ACADEMIC_CATALOG={}):
            self.assertFalse(RegistroInstitucionalForm(self.datos()).is_valid())
            self.assertEqual(carreras(), ())

    @override_settings(ACADEMIC_CATALOG=CATALOGO_PROPIO, INSTITUTION_IDENTITY=IDENTIDAD_PROPIA)
    def test_externo_conserva_procedencia_sin_recibir_privilegios(self):
        formulario = RegistroInstitucionalForm(self.datos(
            tipo_usuario="externo", facultad="", carrera="", nivel_academico="", institucion="Empresa independiente",
        ))
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        self.assertEqual(usuario.profile.institucion, "Empresa independiente")
        self.assertEqual(usuario.profile.facultad, "externo")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.groups.exists())

    def test_auditoria_detecta_retiro_y_cruces_sin_modificar_historia(self):
        usuario = get_user_model().objects.create_user(username="historia.privada", email="privado@example.org")
        UserProfile.objects.filter(pk=usuario.profile.pk).update(facultad="agropecuarias_ambientales", carrera="alimentos")
        anterior = UserProfile.objects.values().get(pk=usuario.profile.pk)
        nuevo = dict(CATALOGO_ACADEMICO)
        nuevo["carreras"] = [fila for fila in nuevo["carreras"] if fila[0] != "alimentos"]
        salida = io.StringIO()
        with override_settings(ACADEMIC_CATALOG=nuevo):
            with self.assertRaises(CommandError):
                call_command("auditar_catalogo_institucional", stdout=salida)
            self.assertNotIn(usuario.username, salida.getvalue())
            self.assertNotIn(usuario.email, salida.getvalue())
            nuevo["carreras_historicas"] = [*nuevo["carreras_historicas"], ["alimentos", "Carrera de Alimentos"]]
            self.assertTrue(all(fila["codigos_desconocidos"] == 0 for fila in auditar_catalogo()))
            self.assertNotIn("alimentos", dict(carreras_academicas()))
            self.assertEqual(dict(carreras())["alimentos"], "Carrera de Alimentos")
            perfil_retirado = usuario.profile
            perfil_retirado.tipo_usuario = "docente"
            perfil_retirado.facultad, perfil_retirado.carrera = "agropecuarias_ambientales", "alimentos"
            self.assertIn("carrera", perfil_retirado.campos_faltantes_reserva())
        self.assertEqual(UserProfile.objects.values().get(pk=usuario.profile.pk), anterior)
        UserProfile.objects.filter(pk=usuario.profile.pk).update(facultad="salud_educacion")
        self.assertTrue(any(fila["relaciones_incompatibles"] == 1 for fila in auditar_catalogo()))

    def test_beneficiario_rechaza_categoria_historica_como_carrera(self):
        usuario = get_user_model().objects.create_user(username="beneficiario")
        for codigo, esperado in (("docente", None), ("alimentos", "agropecuarias_ambientales")):
            peticion = RequestFactory().post("/", {"alcance_beneficiario": "otra_carrera", "carrera_beneficiaria": codigo})
            peticion.user = usuario
            if esperado is None:
                with self.assertRaisesRegex(ValueError, "carrera institucional"):
                    _validar_contexto_actividad(peticion, None, usuario.profile, "docencia_practica", validacion_completa=False)
            else:
                resultado = _validar_contexto_actividad(peticion, None, usuario.profile, "docencia_practica", validacion_completa=False)
                self.assertEqual(resultado["facultad_beneficiaria"], esperado)
                self.assertEqual(resultado["entidad_beneficiaria"], "UPEC")

    def test_configuracion_invalida_y_json_no_importan_codigo(self):
        invalidos = (
            {"secret": "no proyectar"}, {"facultades": "texto"},
            {"facultades": [["x", "X"], ["x", "Duplicado"]]},
            {"facultades": [["x", "<script>"]]},
            {"carreras": [["sistemas", "Sistemas", "inexistente"]]},
            {"tipos_con_carrera": ["externo"]}, {"tipos_con_carrera": ["estudiante"]},
            {"facultades": [["../ruta", "Inválido"]]},
            {"carreras_historicas": [["x", "Histórica"], ["x", "Duplicada"]]},
        )
        for datos in invalidos:
            with self.subTest(datos=datos), override_settings(ACADEMIC_CATALOG=datos):
                self.assertEqual([error.id for error in catalogo_configurado(None)], ["slcid.E002"])
                self.assertIn("slcid.E002", [error.id for error in run_checks()])
                with self.assertRaises(ValueError):
                    catalogo_academico(datos)
        for contenido in ('{"facultades":[],"facultades":[]}', 'import os', '', '{'):
            with self.subTest(contenido=contenido), self.assertRaises(ValueError):
                configuracion_catalogo({"ACADEMIC_CATALOG_JSON": contenido})
        datos = configuracion_catalogo({"INSTITUTION_PROFILE": "custom", "ACADEMIC_CATALOG_JSON": json.dumps(CATALOGO_PROPIO)})
        self.assertEqual(catalogo_academico(datos).facultad_para_carrera("sistemas"), "ingenieria")
        resultado = subprocess.run([sys.executable, "-c",
            "import sys; import apps.core.catalogos; assert 'django' not in sys.modules; assert 'webcitt' not in sys.modules"],
            capture_output=True, text=True, check=False)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
