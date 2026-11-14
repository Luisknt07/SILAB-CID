from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico, VinculacionUsuarioPeriodo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad


class PeriodosAcademicosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin.periodos",
            email="admin.periodos@upec.edu.ec",
            password="periodo-seguro",
        )
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio para períodos",
            descripcion="Unidad de validación temporal.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-periodos",
        )
        cls.periodo = PeriodoAcademico.objects.create(
            codigo="2026-B",
            nombre="Período académico 2026-B",
            anio_referencia=2026,
            ciclo="B",
            tipo="ordinario",
            ambito="carreras_centros",
            semanas_planificadas=16,
            estado="borrador",
        )
        cls.version = VersionCalendarioAcademico.objects.create(
            periodo=cls.periodo,
            numero=1,
            nombre="Calendario aprobado",
            fecha_inicio_clases=date(2026, 8, 31),
            fecha_fin_clases=date(2026, 12, 18),
            fecha_fin_periodo=date(2026, 12, 31),
            vigente=True,
        )
        cls.semana = SemanaAcademica.objects.create(
            version_calendario=cls.version,
            numero=1,
            fecha_inicio=date(2026, 8, 31),
            fecha_fin=date(2026, 9, 6),
        )
        cls.periodo.estado = "publicado"
        cls.periodo.full_clean()
        cls.periodo.save(update_fields=["estado", "actualizado_en"])

    def _crear_reserva(self, **overrides):
        values = {
            "laboratorio": self.unidad,
            "usuario": self.usuario,
            "fecha": date(2026, 9, 2),
            "hora_inicio": time(9, 0),
            "hora_fin": time(11, 0),
            "equipo_codigo": "PER-EQ-001",
            "equipo_nombre": "Equipo temporal",
            "proposito": "Docencia",
            "proposito_codigo": "docencia_practica",
            "periodo": self.periodo,
            "estado": "confirmada",
            "duracion": 2,
        }
        values.update(overrides)
        return Reserva.objects.create(**values)

    def test_reserva_conserva_periodo_version_y_semana_vigentes(self):
        reserva = self._crear_reserva()

        self.assertEqual(reserva.periodo_academico, "2026-B")
        self.assertEqual(reserva.version_calendario, self.version)
        self.assertEqual(reserva.semana_academica, self.semana)
        self.assertEqual(reserva.semana_academica_numero, 1)

    def test_periodo_se_resuelve_por_fecha_y_ambito(self):
        encontrado = PeriodoAcademico.objects.para_fecha(
            date(2026, 9, 2),
            ambito="carreras_centros",
        ).get()

        self.assertEqual(encontrado, self.periodo)
        self.assertEqual(encontrado.semana_para_fecha(date(2026, 9, 2)), self.semana)

    def test_vinculacion_preserva_la_clasificacion_del_usuario_por_periodo(self):
        vinculacion = VinculacionUsuarioPeriodo.objects.create(
            usuario=self.usuario,
            periodo=self.periodo,
            tipo_usuario="estudiante",
            facultad="comercio_administracion",
            carrera="logistica_transporte",
            nivel_academico="quinto_semestre",
            paralelo="A",
            institucion="UPEC",
            fuente="sistema_academico",
            validada=True,
        )

        vinculacion.full_clean()
        self.assertEqual(vinculacion.periodo.codigo, "2026-B")
        self.assertTrue(vinculacion.validada)

    def test_reporte_filtra_periodo_y_agrupa_semana_academica(self):
        self._crear_reserva()
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse("admin:reservas-reporte-uso"),
            {
                "periodo": self.periodo.pk,
                "semana": 1,
                "agrupacion": "semana_academica",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-B")
        self.assertContains(response, "Semana 1")
        self.assertEqual(response.context["total_solicitudes"], 1)

    def test_reporte_distingue_dias_laborables_y_fin_de_semana(self):
        self._crear_reserva()
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse("admin:reservas-reporte-uso"),
            {"agrupacion": "tipo_jornada"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uso por tipo de jornada")
        self.assertContains(response, "Día laborable")
