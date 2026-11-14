import io
import json
import subprocess
import sys
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings

from apps.core.calendario import politica_calendario
from apps.core.presentation.auditoria_calendario import auditar_calendario
from apps.core.presentation.calendario import ambitos, ambitos_operacion, ciclos
from config.calendario import configuracion_calendario
from config.perfiles.upec import CALENDARIO_ACADEMICO
from apps.core.admin.periodos import PeriodoAcademicoAdmin, VersionCalendarioAcademicoAdmin
from apps.reservas.presentation.periodos import resolver_periodo_reserva
from apps.core.usuarios.vigencia import periodo_vigente
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico


CALENDARIO_PROPIO = {
    "ciclos": [["A", "Primer trimestre", "ordinario"], ["B", "Segundo trimestre", "ordinario"],
               ["C", "Tercer trimestre", "ordinario"], ["I", "Operación entre períodos", "interperiodo"]],
    "ambitos": [["formacion", "Formación técnica"]], "ambitos_operacion": ["formacion"],
    "ambito_predeterminado": "formacion", "semanas_predeterminadas": 12,
}


class CalendarioInstitucionalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(username="admin.calendario", password="Clave-Calendario-2026!")

    def periodo(self, ciclo="C", inicio=date(2026, 9, 1), fin=date(2026, 12, 31), **cambios):
        datos = dict(codigo=f"2026-{ciclo}", anio_referencia=2026, ciclo=ciclo)
        datos.update(cambios)
        periodo = PeriodoAcademico(**datos)
        periodo.full_clean()
        periodo.save()
        version = VersionCalendarioAcademico(periodo=periodo, numero=1,
                                             fecha_inicio_clases=inicio, fecha_fin_clases=fin, fecha_fin_periodo=fin)
        version.full_clean()
        version.save()
        periodo.estado = "publicado"
        periodo.full_clean()
        periodo.save()
        return periodo, version

    def test_upec_preserva_ciclos_ambitos_y_limites(self):
        self.assertEqual(configuracion_calendario({}), CALENDARIO_ACADEMICO)
        self.assertEqual(len(ciclos()), 4)
        self.assertEqual(len(ambitos()), 6)
        self.assertEqual(ambitos_operacion(), ("carreras_centros", "institucional"))
        self.assertEqual(PeriodoAcademico().ambito, "carreras_centros")
        self.assertEqual(PeriodoAcademico().semanas_planificadas, 16)
        for ciclo, tipo in (("C", "ordinario"), ("E", "ordinario"), ("A", "interperiodo")):
            with self.subTest(ciclo=ciclo, tipo=tipo), self.assertRaises(ValidationError):
                PeriodoAcademico(codigo="2026-X", anio_referencia=2026, ciclo=ciclo, tipo=tipo).full_clean()
        self.periodo(ciclo="A")
        self.assertEqual(auditar_calendario()["ciclos_tipos_incompatibles"], 0)

    @override_settings(ACADEMIC_CALENDAR=CALENDARIO_PROPIO)
    def test_tres_trimestres_propios_coinciden_en_admin_perfil_y_reserva(self):
        periodos = []
        for ciclo, inicio, fin in (("A", date(2026, 1, 1), date(2026, 4, 30)),
                                  ("B", date(2026, 5, 1), date(2026, 8, 31)),
                                  ("C", date(2026, 9, 1), date(2026, 12, 31))):
            periodo, _ = self.periodo(ciclo, inicio, fin)
            periodos.append(periodo)
            self.assertEqual(periodo.semanas_planificadas, 12)
            self.assertEqual(periodo.ambito, "formacion")
            self.assertEqual(periodo_vigente(inicio), periodo)
            self.assertEqual(resolver_periodo_reserva(inicio, {}, "docencia_practica")["periodo"], periodo)
        peticion = RequestFactory().get("/admin/")
        peticion.user = self.usuario
        formulario = PeriodoAcademicoAdmin(PeriodoAcademico, admin.site).get_form(peticion)()
        self.assertIn("C", dict(formulario.fields["ciclo"].choices))
        self.assertEqual(formulario["ambito"].value(), "formacion")
        self.assertEqual(formulario["semanas_planificadas"].value(), 12)
        resultado = auditar_calendario()
        self.assertTrue(all(v == 0 for c, v in resultado.items() if c not in {"periodos", "semanas"}))
        self.assertEqual(resultado["periodos"], len(periodos))

    @override_settings(ACADEMIC_CALENDAR=CALENDARIO_PROPIO)
    def test_seleccion_sigue_fechas_y_no_orden_alfabetico_del_ciclo(self):
        self.periodo(ciclo="C", inicio=date(2026, 7, 1))
        posterior, _ = self.periodo(ciclo="A", inicio=date(2026, 9, 1))
        self.assertEqual(periodo_vigente(date(2026, 9, 15)), posterior)
        self.assertEqual(resolver_periodo_reserva(date(2026, 9, 15), {}, "docencia_practica")["periodo"], posterior)
        with self.assertRaisesRegex(ValueError, "fecha seleccionada"):
            resolver_periodo_reserva(date(2026, 1, 1), {"periodo_academico": posterior.codigo}, "docencia_practica")

    @override_settings(ACADEMIC_CALENDAR=CALENDARIO_PROPIO)
    def test_semanas_generadas_son_idempotentes_y_conservan_configuracion(self):
        periodo, version = self.periodo(semanas_planificadas=3)
        primera = SemanaAcademica.objects.create(version_calendario=version, numero=1,
                                                fecha_inicio=version.fecha_inicio_clases,
                                                fecha_fin=version.fecha_inicio_clases + timedelta(days=6),
                                                tipo="suspension", permite_reservas=False)
        gestion = VersionCalendarioAcademicoAdmin(VersionCalendarioAcademico, admin.site)
        with patch.object(gestion, "message_user"):
            for _ in range(2):
                gestion.generar_semanas_faltantes(RequestFactory().post("/admin/"),
                                                 VersionCalendarioAcademico.objects.filter(pk=version.pk))
        self.assertEqual(version.semanas.count(), 3)
        primera.refresh_from_db()
        self.assertFalse(primera.permite_reservas)
        self.assertEqual(primera.tipo, "suspension")
        self.assertEqual(auditar_calendario()["semanas_fuera_de_plan"], 0)
        SemanaAcademica.objects.filter(pk=primera.pk).update(numero=4)
        self.assertEqual(auditar_calendario()["semanas_fuera_de_plan"], 1)
        SemanaAcademica.objects.filter(pk=primera.pk).update(numero=1)
        with override_settings(ACADEMIC_CALENDAR={**CALENDARIO_PROPIO, "semanas_maximas": 2, "semanas_predeterminadas": 2}):
            with patch.object(gestion, "message_user") as aviso:
                gestion.generar_semanas_faltantes(RequestFactory().post("/admin/"),
                                                 VersionCalendarioAcademico.objects.filter(pk=version.pk))
                self.assertTrue(aviso.called)
            with self.assertRaises(CommandError):
                call_command("auditar_calendario_institucional", stdout=io.StringIO())
        self.assertEqual(version.semanas.count(), periodo.semanas_planificadas)

    @override_settings(ACADEMIC_CALENDAR=CALENDARIO_PROPIO)
    def test_historia_se_conserva_y_operacion_puede_excluir_ambitos(self):
        periodo, _ = self.periodo()
        original = PeriodoAcademico.objects.values().get(pk=periodo.pk)
        retirado = {**CALENDARIO_PROPIO, "ciclos": CALENDARIO_PROPIO["ciclos"][:2],
                    "ciclos_historicos": [CALENDARIO_PROPIO["ciclos"][2]], "ambitos_operacion": []}
        with override_settings(ACADEMIC_CALENDAR=retirado):
            periodo.full_clean()
            self.assertIsNone(periodo_vigente(date(2026, 9, 15)))
            nuevo = PeriodoAcademico(codigo="2027-C", anio_referencia=2027, ciclo="C")
            with self.assertRaises(ValidationError):
                nuevo.full_clean()
            nuevo.pk = periodo.pk + 1000
            with self.assertRaises(ValidationError):
                nuevo.full_clean()
            self.assertEqual(auditar_calendario()["ciclos_desconocidos"], 0)
        with override_settings(ACADEMIC_CALENDAR={**retirado, "ciclos_historicos": []}):
            with self.assertRaises(CommandError):
                call_command("auditar_calendario_institucional", stdout=io.StringIO())
        self.assertEqual(PeriodoAcademico.objects.values().get(pk=periodo.pk), original)

    def test_configuracion_invalida_falla_con_diagnostico_y_no_importa_django(self):
        for cambio in ({"secreto": "no proyectar"}, {"semanas_maximas": 52}, {"semanas_minimas": True},
                       {"ciclos": [["AA", "Largo", "ordinario"]]}, {"ambitos_operacion": ["inexistente"]},
                       {"ciclos_historicos": [CALENDARIO_PROPIO["ciclos"][0]]}, {"ambitos": [["x", "<script>"]]}):
            with self.subTest(cambio=cambio), override_settings(ACADEMIC_CALENDAR={**CALENDARIO_PROPIO, **cambio}):
                self.assertIn("slcid.E004", [error.id for error in run_checks()])
                with self.assertRaises(ValueError):
                    politica_calendario({**CALENDARIO_PROPIO, **cambio})
        for texto in ('{"ciclos":[],"ciclos":[]}', '{', 'import os'):
            with self.assertRaises(ValueError):
                configuracion_calendario({"ACADEMIC_CALENDAR_JSON": texto})
        self.assertEqual(configuracion_calendario({"ACADEMIC_CALENDAR_JSON": json.dumps(CALENDARIO_PROPIO)}),
                         CALENDARIO_PROPIO)
        neutro = politica_calendario(configuracion_calendario({"INSTITUTION_PROFILE": "custom"}))
        self.assertEqual(neutro.ambitos_operacion, ("institucional",))
        self.assertNotIn("ciden", dict(neutro.ambitos))
        resultado = subprocess.run([sys.executable, "-c", "from apps.core.calendario import TIPOS_PERIODO; "
                                    "import sys; assert len(TIPOS_PERIODO)==3 and 'django' not in sys.modules"],
                                   capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
