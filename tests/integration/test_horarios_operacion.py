from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.reservas.presentation.horarios import validar_horario_operativo as _validar_horario_operativo
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.directorio_unidades.models.core import Unidad


class HorariosOperacionUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio con atención flexible",
            descripcion="Unidad para validar jornadas ordinarias e intersemestrales.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-horarios-flexibles",
        )
        cls.interperiodo = PeriodoAcademico.objects.create(
            codigo="2026-I1",
            nombre="Interperíodo agosto 2026",
            anio_referencia=2026,
            ciclo="I",
            tipo="interperiodo",
            ambito="institucional",
            semanas_planificadas=2,
            estado="borrador",
        )
        cls.version = VersionCalendarioAcademico.objects.create(
            periodo=cls.interperiodo,
            numero=1,
            fecha_inicio_clases=date(2026, 8, 24),
            fecha_fin_clases=date(2026, 8, 30),
            fecha_fin_periodo=date(2026, 9, 6),
            vigente=True,
        )
        cls.semana = SemanaAcademica.objects.create(
            version_calendario=cls.version,
            numero=1,
            fecha_inicio=date(2026, 8, 24),
            fecha_fin=date(2026, 8, 30),
            tipo="operacion_interperiodo",
        )
        cls.interperiodo.estado = "publicado"
        cls.interperiodo.save(update_fields=["estado", "actualizado_en"])
        cls.horario_sabado = HorarioOperacionUnidad.objects.create(
            unidad=cls.unidad,
            periodo=cls.interperiodo,
            nombre="Servicios intersemestrales de investigación",
            dia_semana=5,
            hora_inicio=time(8, 0),
            hora_fin=time(13, 0),
            permite_recursos=False,
            permite_servicios=True,
            tipos_usuario_habilitados=["docente", "investigador"],
            propositos_habilitados=["investigacion_innovacion"],
        )
        cls.horario_jueves = HorarioOperacionUnidad.objects.create(
            unidad=cls.unidad,
            periodo=cls.interperiodo,
            nombre="Servicios intersemestrales de investigación",
            dia_semana=3,
            hora_inicio=time(8, 0),
            hora_fin=time(13, 0),
            permite_recursos=False,
            permite_servicios=True,
            tipos_usuario_habilitados=["docente", "investigador"],
            propositos_habilitados=["investigacion_innovacion"],
        )

    def validar(self, **overrides):
        values = {
            "unidad": self.unidad,
            "periodo": self.interperiodo,
            "semana": self.semana,
            "fecha": date(2026, 8, 29),
            "hora_inicio": time(9, 0),
            "hora_fin": time(11, 0),
            "tipo_solicitud": "servicio",
            "modalidad_servicio": "diseno_completo",
            "tipo_usuario": "investigador",
            "proposito_codigo": "investigacion_innovacion",
        }
        values.update(overrides)
        return _validar_horario_operativo(**values)

    def test_unidad_nueva_recibe_horario_general_de_lunes_a_viernes(self):
        generales = self.unidad.horarios_operacion.filter(periodo__isnull=True)

        self.assertEqual(generales.count(), 5)
        self.assertEqual(set(generales.values_list("dia_semana", flat=True)), set(range(5)))

    def test_fin_de_semana_solo_puede_registrarlo_la_administracion(self):
        with self.assertRaisesMessage(
            ValueError,
            "solo pueden ser registradas por la administración",
        ):
            self.validar()

        self.assertIsNone(self.validar(es_administrador=True))

    def test_cada_unidad_decide_su_horario_y_arranca_de_ocho_a_seis(self):
        """La jornada operativa puede ser más amplia; lo que se ofrece, no.

        La unidad abre su jornada de 07:00 a 20:00 y su configuración empieza
        ofreciendo de 08:00 a 18:00. Fuera de esa franja solo registra la
        administración, dentro de la jornada. Cuando el laboratorio declara
        otro horario, sus usuarios reservan esas horas.
        """
        base = {
            "periodo": None,
            "semana": None,
            "fecha": date(2026, 9, 7),
            "tipo_solicitud": "equipo",
            "modalidad_servicio": "",
        }

        self.assertIsNone(
            self.validar(**base, hora_inicio=time(8, 0), hora_fin=time(10, 0))
        )
        self.assertIsNone(
            self.validar(**base, hora_inicio=time(16, 0), hora_fin=time(18, 0))
        )

        with self.assertRaisesMessage(ValueError, "empieza a las 08:00"):
            self.validar(**base, hora_inicio=time(7, 0), hora_fin=time(9, 0))

        with self.assertRaisesMessage(ValueError, "termina a las 18:00"):
            self.validar(**base, hora_inicio=time(18, 0), hora_fin=time(20, 0))

        # La administración sí registra la extensión, y ni ella pasa de 20:00.
        self.assertIsNone(
            self.validar(
                **base,
                hora_inicio=time(18, 0),
                hora_fin=time(20, 0),
                es_administrador=True,
            )
        )
        with self.assertRaisesMessage(ValueError, "fuera de la jornada habilitada"):
            self.validar(
                **base,
                hora_inicio=time(19, 0),
                hora_fin=time(21, 0),
                es_administrador=True,
            )

        # El laboratorio que atiende de 07:00 a 20:00 lo declara y sus usuarios
        # reservan esas horas sin pedir nada a nadie.
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        configuracion.hora_apertura_atencion = time(7, 0)
        configuracion.hora_cierre_atencion = time(20, 0)
        configuracion.full_clean()
        configuracion.save()
        self.unidad.refresh_from_db()

        self.assertIsNone(
            self.validar(**base, hora_inicio=time(7, 0), hora_fin=time(9, 0))
        )
        self.assertIsNone(
            self.validar(**base, hora_inicio=time(18, 0), hora_fin=time(20, 0))
        )

    def test_el_horario_de_atencion_se_declara_en_horas_completas_y_coherentes(self):
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        configuracion.hora_apertura_atencion = time(8, 30)
        with self.assertRaisesMessage(ValidationError, "horas completas"):
            configuracion.full_clean()

        configuracion.hora_apertura_atencion = time(18, 0)
        configuracion.hora_cierre_atencion = time(8, 0)
        with self.assertRaisesMessage(ValidationError, "después de la hora en que empieza"):
            configuracion.full_clean()

    def test_la_hora_de_almuerzo_no_se_reserva_salvo_panel_de_gestion_o_servicio(self):
        # Lunes con el horario general: el bloque 13:00-14:00 queda fuera,
        # tambien para una cuenta administradora; solo el panel de gestion
        # (permitir_almuerzo) lo registra.
        base = {
            "periodo": None,
            "semana": None,
            "fecha": date(2026, 9, 7),
            "hora_inicio": time(12, 0),
            "hora_fin": time(14, 0),
            "tipo_solicitud": "equipo",
            "modalidad_servicio": "",
        }
        with self.assertRaisesMessage(ValueError, "hora de almuerzo"):
            self.validar(**base)

        with self.assertRaisesMessage(ValueError, "hora de almuerzo"):
            self.validar(**base, es_administrador=True)

        self.assertIsNone(self.validar(**base, permitir_almuerzo=True))
        self.assertIsNone(self.validar(**{**base, "tipo_solicitud": "servicio", "modalidad_servicio": "modelo_listo"}))
        self.assertIsNone(self.validar(**{**base, "hora_inicio": time(14, 0), "hora_fin": time(16, 0)}))

    def test_interperiodo_restringe_perfil_y_modalidad_no_habilitados(self):
        with self.assertRaisesMessage(ValueError, "para tu perfil y propósito"):
            self.validar(fecha=date(2026, 8, 27), tipo_usuario="estudiante")

        with self.assertRaisesMessage(ValueError, "para tu perfil y propósito"):
            self.validar(fecha=date(2026, 8, 27), tipo_solicitud="equipo")

    def test_horario_especifico_reemplaza_al_general_durante_interperiodo(self):
        with self.assertRaisesMessage(ValueError, "no tiene servicios habilitadas"):
            self.validar(fecha=date(2026, 8, 28))

    def test_semana_cerrada_bloquea_la_reserva_aunque_exista_horario(self):
        self.semana.permite_reservas = False
        self.semana.save(update_fields=["permite_reservas"])

        with self.assertRaisesMessage(ValueError, "no permite reservas"):
            self.validar()
