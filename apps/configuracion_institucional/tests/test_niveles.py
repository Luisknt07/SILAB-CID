"""Publicacion de niveles, referencias conservadas y consumidores reales."""

from copy import deepcopy
from io import StringIO
from datetime import timedelta
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.conf import settings
from django.core.checks import run_checks
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command, CommandError
from django.db import connection, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.configuracion_institucional.niveles.forms import NivelesRevisionForm
from apps.configuracion_institucional.niveles.models import (
    RevisionNivelesAcademicos,
    PublicacionNivelesAcademicos,
)
from apps.configuracion_institucional.niveles.services import (
    guardar_borrador_niveles,
    publicar_niveles,
)
from apps.core.niveles import datos_niveles, niveles_academicos
from apps.core.presentation.niveles import niveles, niveles_estudiantiles
from apps.core.presentation.niveles_institucionales import con_niveles_institucionales
from config.perfiles.upec import NIVELES_ACADEMICOS

PROPIOS = {
    "niveles": [
        ["anio_uno", "Primer año"],
        ["anio_dos", "Segundo año"],
        ["trimestre_uno", "Primer trimestre"],
        ["trimestre_dos", "Segundo trimestre"],
        ["tesis", "Tesis"],
    ],
    "estudiantes": ["anio_uno", "anio_dos", "trimestre_uno", "trimestre_dos", "tesis"],
    "secuencias": [["anio_uno", "anio_dos"], ["trimestre_uno", "trimestre_dos"]],
}


class NivelesAdministrablesTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser("niveles.publicador")
        self.editor = get_user_model().objects.create_user(
            "niveles.editor", is_staff=True
        )
        self.editor.user_permissions.add(
            Permission.objects.get(codename="add_revisionnivelesacademicos")
        )
        self.datos = datos_niveles(niveles_academicos(NIVELES_ACADEMICOS))
        self.client.force_login(self.autor)

    def borrador(self, datos=None):
        return guardar_borrador_niveles(
            datos if datos is not None else self.datos,
            self.editor,
            titulo="Propuesta QA",
        )

    def publicar(self, revision, base=None):
        return publicar_niveles(revision.pk, self.autor, base_esperada=base)

    def ampliar(self):
        datos = deepcopy(self.datos)
        datos["niveles"] += [["anio_uno", "Primer año"], ["anio_dos", "Segundo año"]]
        datos["estudiantes"] += ["anio_uno", "anio_dos"]
        datos["secuencias"] += [["anio_uno", "anio_dos"]]
        return datos

    def test_upec_borrador_publicacion_choices_modelos_y_formularios(self):
        from apps.core.models.usuarios_base import UserProfile
        from apps.reservas.models.reservas import Reserva, RegistroParticipanteReserva
        from apps.core.models.periodos import VinculacionUsuarioPeriodo
        from apps.core.usuarios.forms import RegistroInstitucionalForm

        revision = self.borrador(self.ampliar())
        self.assertNotIn("anio_uno", dict(niveles()))

        self.publicar(revision)
        with con_niveles_institucionales():
            for model, field in [
                (UserProfile, "nivel_academico"),
                (Reserva, "nivel_academico_solicitante"),
                (VinculacionUsuarioPeriodo, "nivel_academico"),
                (RegistroParticipanteReserva, "nivel_academico"),
            ]:
                model._meta.get_field(field).clean("anio_uno", None)
            self.assertIn(
                "anio_uno",
                dict(RegistroInstitucionalForm().fields["nivel_academico"].choices),
            )
        self.assertContains(self.client.get("/profile/"), "Primer año")
        self.assertNotIn("anio_uno", dict(niveles()))

    def test_revision_explicita_estudiante_usa_nivel_publicado_fuera_de_http(self):
        from tests.integration.utiles import identificar
        from apps.core.usuarios.verificacion import estado_verificacion, registrar_revision

        self.publicar(self.borrador(self.ampliar()))
        user = get_user_model().objects.create_user("estudiante.nivel.publicado")
        profile = identificar(
            user, tipo_usuario="estudiante", nivel_academico="anio_uno"
        )
        self.assertFalse(estado_verificacion(profile)["verificada"])
        registrar_revision(
            perfil_id=profile.pk,
            revisor=self.autor,
            decision="aprobada",
            fundamento="Identidad sintetica QA.",
            referencia="QA-NIVEL",
            huella=estado_verificacion(profile)["huella"],
        )
        self.assertTrue(estado_verificacion(profile)["verificada"])
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())

    @override_settings(ACADEMIC_LEVELS={})
    def test_anios_trimestres_y_nivel_independiente_fuera_de_http(self):
        from apps.core.usuarios.vigencia import siguiente_nivel

        self.publicar(self.borrador(PROPIOS))
        self.assertEqual(siguiente_nivel("anio_uno"), "anio_dos")
        self.assertEqual(siguiente_nivel("trimestre_uno"), "trimestre_dos")
        self.assertEqual(siguiente_nivel("anio_dos"), "anio_dos")
        self.assertEqual(siguiente_nivel("tesis"), "tesis")

    @override_settings(ACADEMIC_LEVELS={})
    def test_institucion_sin_docencia_no_inventa_niveles_ni_privilegios(self):
        self.publicar(self.borrador({}))
        with con_niveles_institucionales():
            self.assertFalse(niveles_estudiantiles())
        self.assertFalse(self.editor.groups.exists())
        self.assertFalse(
            self.editor.has_perm("configuracion_institucional.publicar_niveles")
        )

    def test_retiro_historico_conserva_perfil_y_bloquea_estudiante_hasta_actualizar(
        self,
    ):
        from apps.core.models.usuarios_base import UserProfile

        user = get_user_model().objects.create_user("nivel.retirado")
        profile = UserProfile.objects.get(user=user)
        profile.tipo_usuario = "estudiante"
        profile.facultad = "agropecuarias_ambientales"
        profile.carrera = "alimentos"
        profile.nivel_academico = "primer_semestre"
        profile.cedula = "DOC-QA"
        profile.save()
        datos = deepcopy(self.datos)
        row = datos["niveles"].pop(0)
        datos["historicos"].append(row)
        datos["estudiantes"].remove(row[0])
        datos["secuencias"][0].remove(row[0])
        published = self.publicar(self.borrador(datos))
        profile.refresh_from_db()
        self.assertEqual(profile.nivel_academico, row[0])
        with con_niveles_institucionales():
            self.assertIn(row[0], dict(niveles()))
            self.assertNotIn(row[0], dict(niveles_estudiantiles()))
            self.assertIn("semestre", profile.campos_faltantes_reserva())
        self.publicar(self.borrador(), published.pk)

    def test_no_elimina_codigos_ni_historicos_aun_sin_uso(self):
        datos = deepcopy(self.datos)
        datos["niveles"].pop()
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador(datos))
        self.assertFalse(
            RevisionNivelesAcademicos.objects.filter(estado="publicada").exists()
        )

    def test_cambio_ruta_propone_confirmacion_sin_reescribir_vinculacion(self):
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico, VinculacionUsuarioPeriodo
        from apps.core.models.usuarios_base import UserProfile
        from apps.core.usuarios.vigencia import estado_perfil

        user = get_user_model().objects.create_user(
            "nivel.avance",
            first_name="Ana",
            last_name="QA",
            email="nivel.avance@example.com",
        )
        profile = UserProfile.objects.get(user=user)
        profile.tipo_usuario = "estudiante"
        profile.facultad = "agropecuarias_ambientales"
        profile.carrera = "alimentos"
        profile.nivel_academico = "primer_semestre"
        profile.cedula = "DOC-QA"
        profile.save()
        today = timezone.localdate()
        periods = []
        for code, start, end in [
            ("2025-A", today - timedelta(days=200), today - timedelta(days=100)),
            ("2026-B", today - timedelta(days=10), today + timedelta(days=60)),
        ]:
            period = PeriodoAcademico.objects.create(
                codigo=code,
                anio_referencia=int(code[:4]),
                ciclo=code[-1],
                tipo="ordinario",
                ambito="carreras_centros",
                estado="publicado",
            )
            VersionCalendarioAcademico.objects.create(
                periodo=period,
                numero=1,
                vigente=True,
                fecha_inicio_clases=start,
                fecha_fin_clases=end,
                fecha_fin_periodo=end,
            )
            periods.append(period)
        old = VinculacionUsuarioPeriodo.objects.create(
            usuario=user,
            periodo=periods[0],
            tipo_usuario="estudiante",
            facultad=profile.facultad,
            carrera=profile.carrera,
            nivel_academico="primer_semestre",
        )
        datos = deepcopy(self.datos)
        datos["secuencias"] = [["primer_semestre", "tercer_semestre"]]
        self.publicar(self.borrador(datos))
        user.refresh_from_db()
        state = estado_perfil(user)
        self.assertEqual(state["propuesta"]["nivel_academico"], "tercer_semestre")
        self.assertTrue(state["requiere_confirmacion"])
        self.assertFalse(
            VinculacionUsuarioPeriodo.objects.filter(
                usuario=user, periodo=periods[1]
            ).exists()
        )
        old.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(old.nivel_academico, "primer_semestre")
        self.assertEqual(profile.nivel_academico, "primer_semestre")

    def test_base_obsoleta_recuperacion_nueva_y_guardas_historia(self):
        first = self.publicar(self.borrador())
        stale = self.borrador()
        second = self.publicar(self.borrador(), first.pk)
        with self.assertRaises(ValidationError):
            self.publicar(stale, second.pk)
        recovered = self.publicar(first, second.pk)
        self.assertEqual(recovered.fuente_id, first.pk)
        self.assertEqual(recovered.basada_en_id, second.pk)
        for operation in [
            lambda: first.save(_desde_editor=True),
            lambda: first.delete(),
            lambda: RevisionNivelesAcademicos.objects.filter(pk=first.pk).update(
                titulo="Otro"
            ),
            lambda: PublicacionNivelesAcademicos.objects.update(revision=first),
        ]:
            with self.assertRaises(ValidationError):
                operation()

    def test_permisos_frescos_revocados_y_cuenta_inactiva(self):
        revision = self.borrador()
        with self.assertRaises(PermissionDenied):
            self.publicar_con_editor(revision)
        perms = Permission.objects.filter(
            codename__in=["publicar_niveles", "view_revisionnivelesacademicos"]
        )
        self.editor.user_permissions.add(*perms)
        self.editor = get_user_model().objects.get(pk=self.editor.pk)
        self.assertTrue(
            self.editor.has_perm("configuracion_institucional.publicar_niveles")
        )
        self.editor.user_permissions.remove(*perms)
        with self.assertRaises(PermissionDenied):
            self.publicar_con_editor(revision)
        self.editor.user_permissions.add(*perms)
        get_user_model().objects.filter(pk=self.editor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.publicar_con_editor(revision)

    def publicar_con_editor(self, revision):
        return publicar_niveles(revision.pk, self.editor, base_esperada=None)

    def test_validacion_json_duplicados_limites_html_rutas_y_metadatos(self):
        for contenido in [
            '{"niveles":[],"niveles":[]}',
            "{}" + " " * 100_000,
            json.dumps({**self.datos, "desconocido": True}),
            json.dumps(
                {**self.datos, "secuencias": [["primer_semestre", "primer_semestre"]]}
            ),
            json.dumps({**self.datos, "etiqueta_faltante": "<script>bad</script>"}),
            json.dumps(
                {**self.datos, "niveles": [[f"n_{i}", str(i)] for i in range(201)]}
            ),
        ]:
            self.assertFalse(
                NivelesRevisionForm({"titulo": "QA", "contenido": contenido}).is_valid()
            )
        self.assertFalse(
            NivelesRevisionForm({"titulo": "<b>QA</b>", "contenido": "{}"}).is_valid()
        )
        self.assertTrue(
            NivelesRevisionForm(
                {
                    "titulo": "QA",
                    "contenido": json.dumps(self.datos),
                    "estado": "publicada",
                }
            ).is_valid()
        )

    def test_admin_real_borrador_publicacion_csrf_metodos_e_idiomas(self):
        add = reverse("admin:configuracion_institucional_revisionnivelesacademicos_add")
        response = self.client.post(
            add,
            {
                "titulo": "QA",
                "contenido": json.dumps(self.datos),
                "estado": "publicada",
            },
        )
        self.assertEqual(response.status_code, 302)
        draft = RevisionNivelesAcademicos.objects.latest("pk")
        self.assertEqual(draft.estado, "borrador")
        change = reverse(
            "admin:configuracion_institucional_revisionnivelesacademicos_change",
            args=[draft.pk],
        )
        publish = reverse(
            "admin:configuracion_institucional_revisionnivelesacademicos_publicar",
            args=[draft.pk],
        )
        self.assertContains(self.client.get(change), publish)
        self.assertContains(self.client.get(publish), reverse('admin:configuracion_institucional_revisionnivelesacademicos_changelist'))
        for lang, editor_title, preview_title in [
            ("es", "Crear revisión de niveles", "Revisar y publicar niveles"),
            ("en", "Create levels revision", "Review and publish levels"),
        ]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = lang
            self.assertContains(self.client.get(add), editor_title)
            self.assertContains(self.client.get(publish), preview_title)
            if lang == 'en':
                self.assertContains(self.client.get(add), 'Academic levels')
                self.assertContains(self.client.get(add), 'Remove from proposal')
        self.assertEqual(self.client.put(add).status_code, 405)
        self.assertEqual(self.client.put(publish).status_code, 405)
        self.assertEqual(self.client.post(publish, {}).status_code, 200)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.autor)
        self.assertEqual(
            csrf_client.post(publish, {"confirmar": "on"}).status_code, 403
        )
        self.assertEqual(
            self.client.post(publish, {"confirmar": "on"}).status_code, 302
        )
        self.assertEqual(
            self.client.post(publish, {"confirmar": "on"}).status_code, 200
        )

    def test_contexto_reset_checks_sin_sql_y_namespace_estricto(self):
        self.publicar(self.borrador(self.ampliar()))
        with con_niveles_institucionales():
            with self.assertNumQueries(0):
                with con_niveles_institucionales():
                    self.assertIn("anio_uno", dict(niveles()))
                self.assertFalse(run_checks())
        self.assertNotIn("anio_uno", dict(niveles()))
        with self.assertRaises(RuntimeError):
            with con_niveles_institucionales():
                raise RuntimeError
        self.assertNotIn("anio_uno", dict(niveles()))
        with override_settings(ACADEMIC_LEVELS_PROVIDER=""):
            with self.assertNumQueries(0):
                with con_niveles_institucionales():
                    self.assertEqual(len(niveles()), 20)
        with override_settings(ACADEMIC_LEVELS_PROVIDER="unregistered.provider"):
            self.assertIn("slcid.E009", [error.id for error in run_checks()])
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE configuracion_institucional_revisionnivelesacademicos SET institucion_codigo=%s WHERE estado=%s",
                ["otra_qa", "publicada"],
            )
        with con_niveles_institucionales():
            self.assertEqual(len(niveles()), 20)
        with self.assertRaises(CommandError):
            call_command("auditar_catalogo_institucional", stdout=StringIO())

    def test_tabla_ausente_savepoint_y_base_corrupta_no_se_certifican(self):
        self.publicar(self.borrador())
        table = "configuracion_institucional_publicacionnivelesacademicos"
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table} RENAME TO niveles_qa_ausente")
        try:
            with transaction.atomic():
                with con_niveles_institucionales():
                    self.assertEqual(len(niveles()), 20)
                self.assertTrue(
                    get_user_model().objects.filter(pk=self.autor.pk).exists()
                )
            with self.assertRaises(CommandError):
                call_command("auditar_catalogo_institucional", stdout=StringIO())
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE niveles_qa_ausente RENAME TO {table}")
        draft = self.borrador()
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET revision_id=%s", [draft.pk])
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador(), draft.pk)
        publish = reverse(
            "admin:configuracion_institucional_revisionnivelesacademicos_publicar",
            args=[draft.pk],
        )
        self.assertEqual(self.client.get(publish).status_code, 200)
        response = self.client.get(publish)
        self.assertTrue(response.context["problemas"])
        self.assertNotContains(response, "Confirmar publicación")

    def test_auditor_propuesta_incompatible_no_publica_ni_modifica_perfil(self):
        from apps.core.models.usuarios_base import UserProfile

        user = get_user_model().objects.create_user("nivel.incompatible")
        UserProfile.objects.filter(user=user).update(nivel_academico="desconocido_qa")
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador())
        self.assertFalse(
            RevisionNivelesAcademicos.objects.filter(estado="publicada").exists()
        )
        self.assertEqual(
            UserProfile.objects.get(user=user).nivel_academico, "desconocido_qa"
        )
        self.assertFalse(PublicacionNivelesAcademicos.objects.get(pk=1).revision_id)
