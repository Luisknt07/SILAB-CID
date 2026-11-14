import io
import json
import subprocess
import sys
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.niveles import niveles_academicos
from apps.core.presentation.auditoria_catalogos import auditar_catalogo
from apps.core.presentation.niveles import niveles, niveles_estudiantiles
from config.niveles import configuracion_niveles
from config.perfiles.upec import NIVELES_ACADEMICOS
from apps.core.admin.usuarios import UserProfileAdmin
from apps.core.usuarios.forms import RegistroInstitucionalForm
from apps.core.usuarios.vigencia import estado_perfil, propuesta_para, siguiente_nivel
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico, VinculacionUsuarioPeriodo
from apps.reservas.models.reservas import RegistroParticipanteReserva, Reserva
from apps.core.models.usuarios_base import UserProfile


NIVELES_PROPIOS = {
    "niveles": [["anio_uno", "Primer año"], ["anio_dos", "Segundo año"],
                ["trimestre_uno", "Primer trimestre"], ["trimestre_dos", "Segundo trimestre"],
                ["tesis", "Tesis"]],
    "estudiantes": ["anio_uno", "anio_dos", "trimestre_uno", "trimestre_dos", "tesis"],
    "secuencias": [["anio_uno", "anio_dos"], ["trimestre_uno", "trimestre_dos"]],
    "historicos": [["nivel_retirado", "Nivel anterior"]],
}


class NivelesInstitucionalesTests(TestCase):
    def datos(self, **cambios):
        datos = dict(username="nivel.prueba", first_name="Ana", last_name="Prueba",
                     email="nivel@example.com", password1="Clave-Academica-2026!",
                     password2="Clave-Academica-2026!", tipo_usuario="estudiante",
                     facultad="agropecuarias_ambientales", carrera="computacion",
                     nivel_academico="anio_uno", cedula="DOC-NIVEL", institucion="")
        datos.update(cambios)
        return datos

    def periodo(self, codigo, anio, inicio, fin, **cambios):
        datos = dict(codigo=codigo, anio_referencia=anio, ciclo="A", tipo="ordinario",
                     ambito="carreras_centros", estado="publicado")
        datos.update(cambios)
        periodo = PeriodoAcademico.objects.create(**datos)
        VersionCalendarioAcademico.objects.create(periodo=periodo, numero=1, vigente=True,
                                                 fecha_inicio_clases=inicio, fecha_fin_clases=fin,
                                                 fecha_fin_periodo=fin)
        return periodo

    def test_upec_conserva_los_20_codigos_y_el_avance_de_10_semestres(self):
        self.assertEqual(len(niveles()), 20)
        self.assertEqual(len(niveles_estudiantiles()), 10)
        self.assertEqual(siguiente_nivel("quinto_semestre"), "sexto_semestre")
        self.assertEqual(siguiente_nivel("decimo_semestre"), "decimo_semestre")
        self.assertEqual(siguiente_nivel("tesis"), "tesis")
        self.assertEqual(configuracion_niveles({}), NIVELES_ACADEMICOS)
        self.assertEqual(configuracion_niveles({"INSTITUTION_PROFILE": "custom"}), {})
        formulario = RegistroInstitucionalForm(self.datos(nivel_academico="quinto_semestre"))
        self.assertTrue(formulario.is_valid(), formulario.errors)
        with self.assertRaises(AttributeError):
            niveles_academicos(NIVELES_ACADEMICOS).secuencias = ()
        usuario = formulario.save()
        usuario.profile.nivel_academico = "inventado_semestre"
        self.assertIn("semestre", usuario.profile.campos_faltantes_reserva())

    @override_settings(ACADEMIC_LEVELS=NIVELES_PROPIOS)
    def test_anios_y_trimestres_coinciden_en_formulario_admin_reserva_y_perfil(self):
        formulario = RegistroInstitucionalForm(self.datos())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        self.assertTrue(usuario.profile.perfil_reserva_completo)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.groups.exists())
        for modelo, nombre in ((UserProfile, "nivel_academico"), (Reserva, "nivel_academico_solicitante"),
                               (RegistroParticipanteReserva, "nivel_academico"),
                               (VinculacionUsuarioPeriodo, "nivel_academico")):
            with self.subTest(modelo=modelo.__name__):
                modelo._meta.get_field(nombre).clean("trimestre_uno", None)
                with self.assertRaises(ValidationError):
                    modelo._meta.get_field(nombre).clean("quinto_semestre", None)
        peticion = RequestFactory().get("/admin/")
        peticion.user = usuario
        formulario_admin = UserProfileAdmin(UserProfile, admin.site).get_form(peticion)()
        self.assertIn("anio_uno", dict(formulario_admin.fields["nivel_academico"].choices))
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse("profile"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'value="anio_uno" selected')
        self.assertNotContains(respuesta, "Seleccionar semestre")
        self.assertEqual(siguiente_nivel("trimestre_uno"), "trimestre_dos")
        self.assertEqual(siguiente_nivel("anio_dos"), "anio_dos")
        self.assertEqual(siguiente_nivel("tesis"), "tesis")

    @override_settings(ACADEMIC_LEVELS=NIVELES_PROPIOS)
    def test_propuesta_espera_confirmacion_y_no_reescribe_el_periodo_anterior(self):
        formulario = RegistroInstitucionalForm(self.datos())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        hoy = timezone.localdate()
        anterior = self.periodo("ANTERIOR", 2025, hoy - timedelta(days=200), hoy - timedelta(days=100))
        actual = self.periodo("ACTUAL", 2026, hoy - timedelta(days=10), hoy + timedelta(days=60))
        historia = VinculacionUsuarioPeriodo.objects.create(
            usuario=usuario, periodo=anterior, tipo_usuario="estudiante",
            facultad=usuario.profile.facultad, carrera=usuario.profile.carrera, nivel_academico="anio_uno")
        estado = estado_perfil(usuario)
        self.assertEqual(estado["propuesta"]["nivel_academico"], "anio_dos")
        self.assertTrue(estado["requiere_confirmacion"])
        self.assertFalse(VinculacionUsuarioPeriodo.objects.filter(usuario=usuario, periodo=actual).exists())
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse("profile_edit"), self.datos(nivel_academico="anio_uno"))
        self.assertRedirects(respuesta, reverse("profile"))
        self.assertTrue(estado_perfil(usuario)["vigente"])
        historia.refresh_from_db()
        self.assertEqual(historia.nivel_academico, "anio_uno")
        self.assertEqual(VinculacionUsuarioPeriodo.objects.get(usuario=usuario, periodo=actual).nivel_academico,
                         "anio_uno")

    @override_settings(ACADEMIC_LEVELS=NIVELES_PROPIOS)
    def test_calendario_ignora_vinculaciones_futuras_inactivas_y_de_otro_programa(self):
        formulario = RegistroInstitucionalForm(self.datos())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        actual = self.periodo("ACTUAL", 2026, date(2026, 9, 1), date(2026, 12, 31))
        anterior = self.periodo("ANTERIOR", 2025, date(2025, 1, 1), date(2025, 12, 31))
        futuro = self.periodo("FUTURO", 2027, date(2027, 1, 1), date(2027, 12, 31))
        datos = dict(usuario=usuario, tipo_usuario="estudiante", facultad=usuario.profile.facultad,
                     carrera=usuario.profile.carrera, nivel_academico="trimestre_uno")
        VinculacionUsuarioPeriodo.objects.create(periodo=futuro, **datos)
        historia = VinculacionUsuarioPeriodo.objects.create(periodo=anterior, estado="inactiva", **datos)
        self.assertFalse(propuesta_para(usuario, usuario.profile, actual)["avanzado"])
        historia.estado = "activa"
        historia.carrera = "alimentos"
        historia.save()
        self.assertFalse(propuesta_para(usuario, usuario.profile, actual)["avanzado"])
        historia.carrera = usuario.profile.carrera
        historia.save()
        self.assertEqual(propuesta_para(usuario, usuario.profile, actual)["nivel_academico"], "trimestre_dos")
        anterior.estado = "borrador"
        anterior.save()
        self.assertFalse(propuesta_para(usuario, usuario.profile, actual)["avanzado"])

    @override_settings(ACADEMIC_LEVELS={})
    def test_institucion_sin_docencia_no_hereda_niveles_ni_habilita_estudiantes(self):
        self.assertEqual(niveles(), ())
        formulario = RegistroInstitucionalForm(self.datos(tipo_usuario="administrativo", carrera="",
                                                         facultad="administracion_central", nivel_academico=""))
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertTrue(formulario.save().profile.perfil_reserva_completo)
        formulario = RegistroInstitucionalForm(self.datos(nivel_academico=""))
        self.assertFalse(formulario.is_valid())
        self.assertIn("nivel_academico", formulario.errors)

    @override_settings(ACADEMIC_LEVELS=NIVELES_PROPIOS)
    def test_niveles_retirados_se_auditan_sin_perder_historia(self):
        usuario = get_user_model().objects.create_user(username="historia.niveles")
        UserProfile.objects.filter(pk=usuario.profile.pk).update(nivel_academico="nivel_retirado")
        original = UserProfile.objects.values().get(pk=usuario.profile.pk)
        self.assertTrue(all(fila["codigos_desconocidos"] == 0 for fila in auditar_catalogo()))
        self.assertIn("nivel_retirado", dict(niveles()))
        self.assertNotIn("nivel_retirado", dict(niveles_estudiantiles()))
        self.assertFalse(RegistroInstitucionalForm(self.datos(nivel_academico="nivel_retirado")).is_valid())
        with override_settings(ACADEMIC_LEVELS={**NIVELES_PROPIOS, "historicos": []}):
            with self.assertRaises(CommandError):
                call_command("auditar_catalogo_institucional", stdout=io.StringIO())
        self.assertEqual(UserProfile.objects.values().get(pk=usuario.profile.pk), original)

    def test_configuracion_rechaza_ciclos_rutas_ambiguas_codigos_largos_y_json_duplicado(self):
        invalidos = ({"secreto": "no proyectar"}, {"niveles": [["x" * 31, "Largo"]]},
                     {**NIVELES_PROPIOS, "secuencias": [["anio_uno", "anio_uno"]]},
                     {**NIVELES_PROPIOS, "secuencias": [["anio_uno", "anio_dos"], ["anio_dos", "tesis"]]},
                     {**NIVELES_PROPIOS, "estudiantes": ["nivel_retirado"]},
                     {**NIVELES_PROPIOS, "secuencias": [["anio_uno", "inexistente"]]},
                     {"etiqueta_faltante": "<script>"}, {"niveles": [["x", "X"], ["x", "Duplicado"]]})
        for datos in invalidos:
            with self.subTest(datos=datos), override_settings(ACADEMIC_LEVELS=datos):
                self.assertIn("slcid.E003", [error.id for error in run_checks()])
                with self.assertRaises(ValueError):
                    niveles_academicos(datos)
        for contenido in ('{"niveles":[],"niveles":[]}', 'import os', '{', ''):
            with self.subTest(contenido=contenido), self.assertRaises(ValueError):
                configuracion_niveles({"ACADEMIC_LEVELS_JSON": contenido})
        self.assertEqual(configuracion_niveles({"ACADEMIC_LEVELS_JSON": json.dumps(NIVELES_PROPIOS)}),
                         NIVELES_PROPIOS)
        resultado = subprocess.run([sys.executable, "-c", "from apps.core.niveles import niveles_academicos; "
                                    "assert niveles_academicos({}).siguiente('x') == 'x'; "
                                    "import sys; assert 'django' not in sys.modules"], capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
