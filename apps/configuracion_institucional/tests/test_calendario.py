"""Politica administrable: cuatro instalaciones, historial y fallos seguros."""

from copy import deepcopy
from datetime import date, timedelta
from io import StringIO
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.checks import run_checks
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse

from apps.core.calendario import datos_calendario, politica_calendario
from apps.core.presentation.calendario import calendario_actual, ciclos
from apps.core.presentation.calendario_institucional import con_calendario_institucional
from apps.configuracion_institucional.calendario.forms import CalendarioRevisionForm
from apps.configuracion_institucional.calendario.models import (
    RevisionPoliticaCalendario,
    PublicacionPoliticaCalendario,
)
from apps.configuracion_institucional.calendario.services import (
    guardar_borrador_calendario,
    publicar_calendario,
)
from config.calendario import CALENDARIO_NEUTRO
from config.perfiles.upec import CALENDARIO_ACADEMICO
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico, SemanaAcademica
from apps.core.admin.periodos import VersionCalendarioAcademicoAdmin
from apps.core.usuarios.vigencia import periodo_vigente
from apps.reservas.presentation.periodos import resolver_periodo_reserva


class CalendarioAdministrableTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser("calendario.publicador")
        self.editor = get_user_model().objects.create_user(
            "calendario.editor", is_staff=True
        )
        self.editor.user_permissions.add(
            Permission.objects.get(codename="add_revisionpoliticacalendario")
        )
        self.datos = datos_calendario(politica_calendario(CALENDARIO_ACADEMICO))
        self.client.force_login(self.autor)

    def borrador(self, datos=None):
        return guardar_borrador_calendario(
            datos or self.datos, self.editor, titulo="Calendario QA"
        )

    def publicar(self, revision, base=None):
        return publicar_calendario(revision.pk, self.autor, base_esperada=base)

    def ampliar(self):
        datos = deepcopy(self.datos)
        datos["ciclos"].append(["C", "Tercer trimestre", "ordinario"])
        datos["ambitos"].append(["formacion", "Formación técnica"])
        datos["ambitos_operacion"] = ["formacion"]
        datos["ambito_predeterminado"] = "formacion"
        datos["semanas_predeterminadas"] = 12
        return datos

    def periodo(self, ciclo="A", **cambios):
        with con_calendario_institucional():
            datos = {"codigo": f"2026-{ciclo}", "anio_referencia": 2026, "ciclo": ciclo}
            datos.update(cambios)
            periodo = PeriodoAcademico(**datos)
            periodo.full_clean()
            periodo.save()
            version = VersionCalendarioAcademico.objects.create(
                periodo=periodo,
                fecha_inicio_clases=date(2026, 9, 1),
                fecha_fin_clases=date(2026, 12, 31),
                fecha_fin_periodo=date(2026, 12, 31),
            )
            periodo.estado = "publicado"
            periodo.full_clean()
            periodo.save()
            return periodo, version

    def test_upec_borrador_no_activa_y_publicacion_conserva_periodos(self):
        periodo, version = self.periodo()
        original = PeriodoAcademico.objects.values().get(pk=periodo.pk)
        borrador = self.borrador(self.ampliar())
        with con_calendario_institucional():
            self.assertNotIn("C", dict(ciclos()))
        publicada = self.publicar(borrador)
        with con_calendario_institucional():
            self.assertIn("C", dict(ciclos()))
            nuevo = PeriodoAcademico()
            self.assertEqual(
                (nuevo.ambito, nuevo.semanas_planificadas), ("formacion", 12)
            )
        self.assertEqual(PeriodoAcademico.objects.values().get(pk=periodo.pk), original)
        self.assertEqual(periodo.version_vigente, version)
        self.assertEqual(publicada.basada_en_id, None)
        self.assertFalse(self.editor.is_superuser)

    def test_trimestres_admin_perfil_reserva_misma_politica(self):
        self.publicar(self.borrador(self.ampliar()))
        periodo, _ = self.periodo("C")
        self.assertEqual(periodo_vigente(date(2026, 9, 15)), periodo)
        with con_calendario_institucional():
            self.assertEqual(
                resolver_periodo_reserva(date(2026, 9, 15), {}, "docencia_practica")[
                    "periodo"
                ],
                periodo,
            )
        response = self.client.get(reverse("admin:core_periodoacademico_add"))
        self.assertContains(response, "formacion")
        self.assertContains(response, "Tercer trimestre")
        self.assertContains(response, 'value="12"')

    def test_instituto_un_ciclo_default_ocho_semanas(self):
        base = {**CALENDARIO_NEUTRO, "ciclos": [["A", "Ciclo único", "ordinario"]]}
        with override_settings(ACADEMIC_CALENDAR=base):
            datos = datos_calendario(politica_calendario(base))
            datos["semanas_predeterminadas"] = 8
            self.publicar(self.borrador(datos))
            periodo, _ = self.periodo()
            self.assertEqual(
                (periodo.ambito, periodo.semanas_planificadas), ("institucional", 8)
            )

    def test_centro_investigacion_sin_asociacion_automatica(self):
        with override_settings(ACADEMIC_CALENDAR=CALENDARIO_NEUTRO):
            datos = datos_calendario(politica_calendario(CALENDARIO_NEUTRO))
            datos["ambitos_operacion"] = []
            self.publicar(self.borrador(datos))
            periodo, _ = self.periodo()
            self.assertIsNone(periodo_vigente(date(2026, 9, 15)))
            with con_calendario_institucional():
                result = resolver_periodo_reserva(
                    date(2026, 9, 15),
                    {"periodo_academico": periodo.codigo},
                    "docencia_practica",
                )
                self.assertEqual(result["periodo"], periodo)
            periodo.refresh_from_db()
            self.assertEqual(periodo.estado, "publicado")

    def test_retiro_y_reactivacion_conservan_historia_y_tipo(self):
        periodo, _ = self.periodo()
        original = PeriodoAcademico.objects.values().get(pk=periodo.pk)
        datos = deepcopy(self.datos)
        ciclo = datos["ciclos"].pop(0)
        datos["ciclos_historicos"].append(ciclo)
        primera = self.publicar(self.borrador(datos))
        with con_calendario_institucional():
            periodo.full_clean()
            with self.assertRaises(ValidationError):
                PeriodoAcademico(
                    codigo="2027-A", anio_referencia=2027, ciclo="A"
                ).full_clean()
        self.publicar(self.borrador(self.datos), primera.pk)
        self.assertEqual(PeriodoAcademico.objects.values().get(pk=periodo.pk), original)

    def test_codigos_y_semantica_no_se_eliminan_ni_siquiera_sin_uso(self):
        for key in ["ciclos", "ambitos"]:
            datos = deepcopy(self.datos)
            datos[key].pop()
            revision = self.borrador(datos)
            with self.assertRaises(ValidationError):
                self.publicar(revision)
        datos = deepcopy(self.datos)
        datos["ciclos"][0][2] = "interperiodo"
        with self.assertRaises(ValidationError):
            self.publicar(self.borrador(datos))
        self.assertEqual(
            RevisionPoliticaCalendario.objects.filter(estado="publicada").count(), 0
        )

    def test_limites_menores_bloquean_historia_y_generacion_idempotente(self):
        self.publicar(self.borrador(self.ampliar()))
        periodo, version = self.periodo("C")
        primera = SemanaAcademica.objects.create(
            version_calendario=version,
            numero=1,
            fecha_inicio=version.fecha_inicio_clases,
            fecha_fin=version.fecha_inicio_clases + timedelta(days=6),
            tipo="suspension",
            permite_reservas=False,
        )
        gestion = VersionCalendarioAcademicoAdmin(
            VersionCalendarioAcademico, admin.site
        )
        with patch.object(gestion, "message_user"):
            for _ in range(2):
                gestion.generar_semanas_faltantes(
                    RequestFactory().post("/admin/"),
                    VersionCalendarioAcademico.objects.filter(pk=version.pk),
                )
        self.assertEqual(version.semanas.count(), 12)
        primera.refresh_from_db()
        self.assertFalse(primera.permite_reservas)
        datos = self.ampliar()
        datos.update(semanas_maximas=8, semanas_predeterminadas=8)
        with self.assertRaises(ValidationError):
            self.publicar(
                self.borrador(datos),
                PublicacionPoliticaCalendario.objects.get().revision_id,
            )
        self.assertEqual(periodo.semanas_planificadas, 12)

    def test_base_obsoleta_restaura_como_revision_nueva_e_historial_inmutable(self):
        uno, dos = self.borrador(), self.borrador()
        primera = self.publicar(uno)
        with self.assertRaises(ValidationError):
            self.publicar(dos, primera.pk)
        segunda = self.publicar(primera, primera.pk)
        self.assertNotEqual(primera.pk, segunda.pk)
        self.assertEqual(segunda.fuente, primera)
        for action in [
            lambda: primera.save(),
            lambda: primera.delete(),
            lambda: RevisionPoliticaCalendario.objects.filter(pk=primera.pk).update(
                titulo="Cambio"
            ),
            lambda: PublicacionPoliticaCalendario.objects.all().update(revision=None),
        ]:
            with self.assertRaises(ValidationError):
                action()

    def test_autoridad_fresca_revocada_no_publica(self):
        self.editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["publicar_calendario", "view_revisionpoliticacalendario"]
            )
        )
        self.assertTrue(
            self.editor.has_perm("configuracion_institucional.publicar_calendario")
        )
        revision = self.borrador()
        self.editor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            publicar_calendario(revision.pk, self.editor, base_esperada=None)
        with self.assertRaises(PermissionDenied):
            self.borrador()
        self.assertEqual(
            RevisionPoliticaCalendario.objects.filter(estado="publicada").count(), 0
        )

    def test_json_invalidos_limites_html_booleanos_y_metadatos(self):
        for value in [
            '{"ciclos":[],"ciclos":[]}',
            "{}" + " " * 100000,
            json.dumps({**self.datos, "secreto": "no"}),
            json.dumps({**self.datos, "semanas_maximas": 52}),
            json.dumps({**self.datos, "semanas_minimas": True}),
            json.dumps(
                {**self.datos, "ambitos": [[f"a_{i}", str(i)] for i in range(201)]}
            ),
            json.dumps({**self.datos, "ciclos": [["AA", "<b>No</b>", "ordinario"]]}),
            json.dumps({**self.datos, "ambitos_operacion": ["inexistente"]}),
        ]:
            form = CalendarioRevisionForm({"titulo": "QA", "contenido": value})
            self.assertFalse(form.is_valid())
            self.assertIn(
                "data-payload-rechazado", form.fields["contenido"].widget.attrs
            )
        form = CalendarioRevisionForm(
            {"titulo": "QA", "contenido": json.dumps(self.datos), "estado": "publicada"}
        )
        self.assertTrue(form.is_valid())
        revision = self.borrador(form.cleaned_data["contenido"])
        self.assertEqual(revision.estado, "borrador")

    def test_admin_historia_preview_csrf_idiomas_y_metodos(self):
        add = reverse(
            "admin:configuracion_institucional_revisionpoliticacalendario_add"
        )
        self.assertEqual(
            self.client.post(
                add, {"titulo": "QA", "contenido": json.dumps(self.datos)}
            ).status_code,
            302,
        )
        revision = RevisionPoliticaCalendario.objects.latest("pk")
        review = reverse(
            "admin:configuracion_institucional_revisionpoliticacalendario_publicar",
            args=[revision.pk],
        )
        change = reverse(
            "admin:configuracion_institucional_revisionpoliticacalendario_change",
            args=[revision.pk],
        )
        self.assertContains(self.client.get(change), review)
        for lang, title in [
            ("es", "Crear revisión de calendario"),
            ("en", "Create calendar revision"),
        ]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = lang
            self.assertContains(self.client.get(add), title)
            if lang == 'en':
                self.assertContains(self.client.get(add), 'Ordinary academic period')
                self.assertContains(self.client.get(review), 'Ordinary academic period')
        self.assertEqual(self.client.put(add).status_code, 405)
        self.assertEqual(self.client.put(review).status_code, 405)
        self.assertEqual(self.client.post(review, {}).status_code, 200)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.autor)
        self.assertEqual(csrf.post(review, {"confirmar": "on"}).status_code, 403)
        self.assertEqual(self.client.post(review, {"confirmar": "on"}).status_code, 302)
        self.assertEqual(self.client.post(review, {"confirmar": "on"}).status_code, 200)

    def test_contextos_reset_checks_sin_sql_proveedor_y_namespace(self):
        self.publicar(self.borrador(self.ampliar()))
        with con_calendario_institucional():
            with self.assertNumQueries(0):
                with con_calendario_institucional():
                    self.assertIn("C", dict(ciclos()))
                self.assertFalse(run_checks())
        self.assertNotIn("C", dict(ciclos()))
        with self.assertRaises(RuntimeError):
            with con_calendario_institucional():
                raise RuntimeError
        self.assertNotIn("C", dict(ciclos()))
        with override_settings(ACADEMIC_CALENDAR_PROVIDER=""):
            with self.assertNumQueries(0):
                with con_calendario_institucional():
                    self.assertNotIn("C", dict(ciclos()))
        with override_settings(ACADEMIC_CALENDAR_PROVIDER="unregistered.provider"):
            self.assertIn("slcid.E010", [e.id for e in run_checks()])
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE configuracion_institucional_revisionpoliticacalendario SET institucion_codigo=%s WHERE estado=%s",
                ["OTRA", "publicada"],
            )
        with con_calendario_institucional():
            self.assertNotIn("C", dict(ciclos()))
        with self.assertRaises(CommandError):
            call_command("auditar_calendario_institucional", stdout=StringIO())

    def test_tabla_ausente_fallback_seguro_y_auditor_estricto(self):
        table = "configuracion_institucional_publicacionpoliticacalendario"
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table} RENAME TO calendario148_inaccesible")
        try:
            with con_calendario_institucional():
                self.assertEqual(calendario_actual().semanas_predeterminadas, 16)
            self.assertTrue(get_user_model().objects.filter(pk=self.autor.pk).exists())
            with self.assertRaises(CommandError):
                call_command("auditar_calendario_institucional", stdout=StringIO())
        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"ALTER TABLE calendario148_inaccesible RENAME TO {table}"
                )

    def test_referencias_desconocidas_e_integridad_base_bloquean(self):
        PeriodoAcademico.objects.create(
            codigo="2026-X", anio_referencia=2026, ciclo="X"
        )
        revision = self.borrador()
        with self.assertRaises(ValidationError):
            self.publicar(revision)
        PeriodoAcademico.objects.all().delete()
        primera = self.publicar(revision)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE configuracion_institucional_publicacionpoliticacalendario SET revision_id=%s",
                [revision.pk],
            )
        with self.assertRaises(ValidationError):
            self.publicar(primera, revision.pk)
        review = reverse(
            "admin:configuracion_institucional_revisionpoliticacalendario_publicar",
            args=[primera.pk],
        )
        response = self.client.get(review)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="confirmar"')
