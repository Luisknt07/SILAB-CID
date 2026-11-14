import json
from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, CapacidadOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.utilizacion import calculate_unit_utilization


class CalendarioPublicoReservasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = Unidad.objects.create(
            nombre="Laboratorio con agenda",
            descripcion="Unidad para probar la ocupación pública.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-con-agenda",
        )
        cls.equipo = EquiposServicios.objects.create(
            codigo="EQ-CAL-001",
            nombre="Equipo del calendario",
        )
        cls.unidad_a = UnidadEquipo.objects.create(
            codigo_unidad="CAL-A-001",
            equipo=cls.equipo,
            laboratorio=cls.laboratorio,
            estado_unidad="disponible",
            activa=True,
        )
        cls.unidad_b = UnidadEquipo.objects.create(
            codigo_unidad="CAL-B-001",
            equipo=cls.equipo,
            laboratorio=cls.laboratorio,
            estado_unidad="disponible",
            activa=True,
        )
        cls.usuario = get_user_model().objects.create_user(
            username="persona.calendario",
            email="dato-privado@upec.edu.ec",
            password="calendario-seguro",
            first_name="Dato",
            last_name="Privado",
        )
        cls.software = SoftwareDisponible.objects.create(
            unidad=cls.laboratorio,
            nombre="Licencia concurrente de prueba",
            codigo="SW-CAL-001",
            tipo_recurso="licencia",
            tipo_acceso="red",
            licencias_totales=2,
            licencias_disponibles=2,
            requiere_reserva=True,
            activo=True,
        )

    def _reserva(self, unidad, *, estado="confirmada", hora=9, **overrides):
        values = {
            "laboratorio": self.laboratorio,
            "usuario": self.usuario,
            "fecha": date(2026, 9, 8),
            "hora_inicio": time(hora, 0),
            "hora_fin": time(hora + 2, 0),
            "horas_seleccionadas": json.dumps([hora, hora + 1]),
            "equipo_codigo": unidad.equipo.codigo,
            "equipo_nombre": unidad.equipo.nombre,
            "unidades_seleccionadas": json.dumps(
                [{"id": unidad.pk, "codigo": unidad.codigo_unidad}]
            ),
            "nombre_solicitante": "Nombre confidencial",
            "correo_solicitante": "correo-confidencial@example.com",
            "proposito": "Investigación confidencial",
            "descripcion_proyecto": "Descripción que no debe publicarse",
            "titulo_solicitud": "Título privado del proyecto",
            "estado": estado,
        }
        values.update(overrides)
        return Reserva.objects.create(**values)

    def test_calendario_publica_ocupacion_sin_datos_personales(self):
        self._reserva(self.unidad_a)

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {"desde": "2026-09-01", "hasta": "2026-09-30"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertFalse(payload["seleccion_recursos_aplicada"])
        self.assertEqual(payload["dias"]["2026-09-08"]["solicitudes"], 1)
        self.assertEqual(payload["dias"]["2026-09-08"]["horas_ocupadas"], [9, 10])
        self.assertEqual(payload["eventos"][0]["etiqueta"], "Actividad registrada")
        self.assertEqual(payload["eventos"][0]["reservado_por"], "Usuario registrado")
        self.assertIn("Reserva de equipos", payload["eventos"][0]["resumen"])
        self.assertEqual(payload["eventos"][0]["estado_display"], "Confirmada")
        self.assertEqual(payload["eventos"][0]["tipo_solicitud_display"], "Reserva de equipos")
        self.assertEqual(payload["eventos"][0]["participantes"], 1)
        self.assertEqual(payload["eventos"][0]["actividad"], "")
        self.assertTrue(payload["eventos"][0]["evento_id"].startswith("reserva-"))
        serialized = response.content.decode("utf-8")
        for private_value in (
            "Dato Privado",
            "dato-privado@upec.edu.ec",
            "Nombre confidencial",
            "correo-confidencial@example.com",
            "Título privado del proyecto",
            "Descripción que no debe publicarse",
        ):
            self.assertNotIn(private_value, serialized)

    def test_agenda_general_muestra_todo_y_solo_bloquea_conflictos_de_la_seleccion(self):
        self._reserva(self.unidad_a, hora=9)
        self._reserva(self.unidad_b, hora=9)

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {
                "desde": "2026-09-08",
                "hasta": "2026-09-08",
                "unidades": str(self.unidad_a.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["seleccion_recursos_aplicada"])
        self.assertEqual(len(payload["eventos"]), 2)
        evento_conflictivo = next(
            evento for evento in payload["eventos"] if evento["coincide_seleccion"]
        )
        evento_informativo = next(
            evento for evento in payload["eventos"] if not evento["coincide_seleccion"]
        )
        self.assertEqual(evento_conflictivo["horas"], [9, 10])
        self.assertEqual(evento_conflictivo["etiqueta"], "Horario ocupado")
        self.assertTrue(evento_conflictivo["bloquea_seleccion"])
        self.assertEqual(evento_informativo["horas"], [9, 10])
        self.assertEqual(evento_informativo["etiqueta"], "Actividad registrada")
        self.assertFalse(evento_informativo["bloquea_seleccion"])
        self.assertEqual(payload["dias"]["2026-09-08"]["solicitudes"], 2)
        self.assertEqual(
            payload["dias"]["2026-09-08"]["horas_bloqueadas"],
            [9, 10],
        )
        self.assertTrue(payload["dias"]["2026-09-08"]["bloquea_seleccion"])

    def test_usuario_autenticado_ve_quien_reservo_sin_exponer_correo(self):
        self._reserva(self.unidad_a)
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {"desde": "2026-09-08", "hasta": "2026-09-08"},
        )

        self.assertEqual(response.status_code, 200)
        serialized = response.content.decode("utf-8")
        self.assertEqual(response.json()["eventos"][0]["reservado_por"], "Nombre confidencial")
        self.assertNotIn("correo-confidencial@example.com", serialized)

    def test_canceladas_no_ocupan_el_calendario(self):
        self._reserva(self.unidad_a, estado="cancelada")

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {"desde": "2026-09-08", "hasta": "2026-09-08"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["eventos"], [])
        self.assertEqual(response.json()["dias"], {})

    def test_filtro_de_area_distingue_estaciones_del_mismo_laboratorio(self):
        area_a = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-CAL-A",
            nombre="Área de impresión 3D",
        )
        area_b = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-CAL-B",
            nombre="Área de corte",
        )
        reserva_a = self._reserva(
            self.unidad_a,
            hora=8,
            tipo_solicitud="recursos",
            incluye_espacio=True,
        )
        reserva_a.espacios_solicitados.add(area_a)
        reserva_b = self._reserva(
            self.unidad_b,
            hora=15,
            tipo_solicitud="recursos",
            incluye_espacio=True,
        )
        reserva_b.espacios_solicitados.add(area_b)

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {
                "desde": "2026-09-08",
                "hasta": "2026-09-08",
                "espacios": str(area_a.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["eventos"]), 2)
        evento_area = next(
            evento for evento in payload["eventos"] if evento["coincide_seleccion"]
        )
        evento_otro = next(
            evento for evento in payload["eventos"] if not evento["coincide_seleccion"]
        )
        self.assertEqual(evento_area["horas"], [8, 9])
        self.assertTrue(evento_area["bloquea_seleccion"])
        self.assertEqual(evento_otro["horas"], [15, 16])
        self.assertFalse(evento_otro["bloquea_seleccion"])

    def test_unidad_completa_bloquea_cualquier_uso_fisico_y_no_solo_areas(self):
        self._reserva(
            self.unidad_a,
            hora=9,
            tipo_solicitud="recursos",
            unidades_seleccionadas="[]",
            incluye_espacio=True,
            proposito_codigo="docencia_practica",
        )

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {
                "desde": "2026-09-08",
                "hasta": "2026-09-08",
                "unidades": str(self.unidad_b.pk),
                "proposito_codigo": "investigacion_innovacion",
                "participantes": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["dias"]["2026-09-08"]["horas_bloqueadas"], [9, 10])
        self.assertEqual(payload["eventos"][0]["alcance_espacio"], "unidad_completa")
        self.assertIn("unidad completa", " ".join(payload["eventos"][0]["motivos_bloqueo"]).lower())

    def test_nueva_reserva_de_unidad_completa_bloquea_equipos_ya_reservados(self):
        self._reserva(
            self.unidad_a,
            hora=9,
            proposito_codigo="investigacion_innovacion",
        )

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {
                "desde": "2026-09-08",
                "hasta": "2026-09-08",
                "incluye_espacio": "true",
                "proposito_codigo": "docencia_practica",
                "participantes": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["dias"]["2026-09-08"]["horas_bloqueadas"],
            [9, 10],
        )

    def test_area_no_docente_se_comparte_hasta_alcanzar_su_capacidad(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-CAPACIDAD",
            nombre="Area de investigacion compartida",
            capacidad=4,
        )
        existing = self._reserva(
            self.unidad_a,
            hora=11,
            tipo_solicitud="recursos",
            unidades_seleccionadas="[]",
            incluye_espacio=True,
            proposito_codigo="investigacion_innovacion",
            numero_participantes=2,
        )
        existing.espacios_solicitados.add(area)
        url = reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk])
        params = {
            "desde": "2026-09-08",
            "hasta": "2026-09-08",
            "espacios": str(area.pk),
            "proposito_codigo": "investigacion_innovacion",
        }

        available = self.client.get(url, {**params, "participantes": "2"}).json()
        self.assertEqual(available["dias"]["2026-09-08"]["horas_bloqueadas"], [])
        # El calendario muestra cuantos puestos quedan antes de llenarse.
        self.assertEqual(available["capacidad_seleccion"], 4)
        self.assertEqual(available["dias"]["2026-09-08"]["ocupacion"], {"11": 2, "12": 2})

        full = self.client.get(url, {**params, "participantes": "3"}).json()
        self.assertEqual(full["dias"]["2026-09-08"]["horas_bloqueadas"], [11, 12])
        self.assertIn("capacidad", " ".join(full["eventos"][0]["motivos_bloqueo"]).lower())

        # La unidad completa no comparte cupo: bloquea todo el laboratorio.
        full_unit = self.client.get(
            url, {**params, "espacios": "", "alcance_espacio": "unidad_completa"}
        ).json()
        self.assertEqual(full_unit["capacidad_seleccion"], 0)
        self.assertEqual(full_unit["dias"]["2026-09-08"]["ocupacion"], {})

    def test_area_docente_es_exclusiva_aunque_tenga_capacidad_libre(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-DOCENCIA",
            nombre="Area docente",
            capacidad=30,
        )
        existing = self._reserva(
            self.unidad_a,
            hora=13,
            tipo_solicitud="recursos",
            unidades_seleccionadas="[]",
            incluye_espacio=True,
            proposito_codigo="docencia_practica",
            numero_participantes=2,
        )
        existing.espacios_solicitados.add(area)

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {
                "desde": "2026-09-08",
                "hasta": "2026-09-08",
                "espacios": str(area.pk),
                "proposito_codigo": "investigacion_innovacion",
                "participantes": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["dias"]["2026-09-08"]["horas_bloqueadas"], [13, 14])

    def test_api_de_equipos_publica_guia_y_oculta_datos_operativos(self):
        self.equipo.imagen_catalogo = "img/catalogo/equipos/equipo-prueba.png"
        self.equipo.caracteristicas_publicas = "Volumen útil de prueba."
        self.equipo.uso_publico = "Prototipado y validación."
        self.equipo.instrucciones_publicas = "Completa la inducción antes de usarlo."
        self.equipo.marca = "Marca pública"
        self.equipo.modelo = "Modelo público"
        self.equipo.save()
        self.unidad_a.observaciones = "Dato operativo privado"
        self.unidad_a.save(update_fields=["observaciones"])

        response = self.client.get(
            reverse("obtener_unidades_laboratorio", args=[self.laboratorio.pk])
        )

        self.assertEqual(response.status_code, 200)
        equipment = response.json()["unidades"][0]
        self.assertEqual(equipment["uso_publico"], "Prototipado y validación.")
        self.assertEqual(equipment["marca"], "Marca pública")
        self.assertTrue(equipment["imagen_url"].endswith("equipo-prueba.png"))
        self.assertNotIn("observaciones", equipment)
        self.assertNotIn("fecha_ultimo_mantenimiento", equipment)
        self.assertNotIn("Dato operativo privado", response.content.decode("utf-8"))

    def test_software_concurrente_bloquea_solo_cuando_agota_licencias(self):
        first = self._reserva(
            self.unidad_a,
            hora=11,
            tipo_solicitud="software",
            unidades_seleccionadas="[]",
        )
        first.software_solicitado.add(self.software)
        url = reverse(
            "obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]
        )
        params = {
            "desde": "2026-09-08",
            "hasta": "2026-09-08",
            "software": str(self.software.pk),
        }

        with_capacity = self.client.get(url, params).json()
        self.assertEqual(with_capacity["dias"]["2026-09-08"]["horas_bloqueadas"], [])
        self.assertFalse(with_capacity["dias"]["2026-09-08"]["bloquea_seleccion"])

        second = self._reserva(
            self.unidad_b,
            hora=11,
            tipo_solicitud="software",
            unidades_seleccionadas="[]",
        )
        second.software_solicitado.add(self.software)

        without_capacity = self.client.get(url, params).json()
        self.assertEqual(
            without_capacity["dias"]["2026-09-08"]["horas_bloqueadas"],
            [11, 12],
        )
        self.assertTrue(
            without_capacity["dias"]["2026-09-08"]["bloquea_seleccion"]
        )

    def test_cierre_administrativo_aparece_y_bloquea_sin_seleccion_previa(self):
        BloqueoAgendaUnidad.objects.create(
            unidad=self.laboratorio,
            tipo="feriado",
            titulo="SuspensiÃ³n institucional de prueba",
            motivo="Cierre de jornada",
            fecha_inicio=date(2026, 9, 8),
            fecha_fin=date(2026, 9, 8),
            dia_completo=True,
            alcance="unidad_completa",
        )

        response = self.client.get(
            reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]),
            {"desde": "2026-09-08", "hasta": "2026-09-08"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        event = payload["eventos"][0]
        self.assertEqual(event["tipo_evento"], "bloqueo")
        self.assertEqual(event["proposito_codigo"], "bloqueo")
        self.assertTrue(event["bloquea_seleccion"])
        self.assertIn(9, payload["dias"]["2026-09-08"]["horas_bloqueadas"])

    def test_mantenimiento_de_equipo_conserva_disponible_otro_equipo(self):
        block = BloqueoAgendaUnidad.objects.create(
            unidad=self.laboratorio,
            tipo="mantenimiento",
            titulo="Mantenimiento focalizado",
            fecha_inicio=date(2026, 9, 8),
            fecha_fin=date(2026, 9, 8),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            alcance="equipos",
        )
        block.equipos.add(self.unidad_a)
        url = reverse("obtener_ocupacion_laboratorio", args=[self.laboratorio.pk])
        params = {"desde": "2026-09-08", "hasta": "2026-09-08"}

        affected = self.client.get(url, {**params, "unidades": self.unidad_a.pk}).json()
        available = self.client.get(url, {**params, "unidades": self.unidad_b.pk}).json()

        self.assertEqual(affected["dias"]["2026-09-08"]["horas_bloqueadas"], [9, 10])
        self.assertEqual(available["dias"]["2026-09-08"]["horas_bloqueadas"], [])

    def test_indicador_separa_frecuencia_ocupacion_y_utilizacion(self):
        HorarioOperacionUnidad.objects.filter(unidad=self.laboratorio).delete()
        HorarioOperacionUnidad.objects.create(
            unidad=self.laboratorio,
            dia_semana=1,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
        )
        CapacidadOperativaUnidad.objects.create(
            unidad=self.laboratorio,
            vigente_desde=date(2026, 9, 1),
            aforo_seguridad=10,
            puestos_mobiliario=8,
            puestos_equipados=4,
            capacidad_personal=6,
        )
        BloqueoAgendaUnidad.objects.create(
            unidad=self.laboratorio,
            tipo="mantenimiento",
            titulo="Cierre posterior a la jornada medida",
            fecha_inicio=date(2026, 9, 8),
            fecha_fin=date(2026, 9, 8),
            hora_inicio=time(11, 0),
            hora_fin=time(12, 0),
            alcance="unidad_completa",
        )
        self._reserva(
            self.unidad_a,
            hora=9,
            numero_participantes=2,
            estado="completada",
            resultado_cierre="atendida",
            detalle_ejecucion={
                "registrada_en": "2026-09-08T11:05:00-05:00",
                "horario_real": {"inicio": "09:00", "fin": "11:00"},
                "asistentes_total": 2,
            },
        )

        indicator = calculate_unit_utilization(
            self.laboratorio,
            date(2026, 9, 8),
            date(2026, 9, 8),
        )

        self.assertEqual(indicator["capacity"], 4)
        self.assertEqual(indicator["frequency"], 100.0)
        self.assertEqual(indicator["occupancy"], 50.0)
        self.assertEqual(indicator["utilization"], 50.0)
        self.assertEqual(indicator["level"]["code"], "moderate")

    def test_indicador_usa_horario_y_asistencia_reales_del_cierre(self):
        HorarioOperacionUnidad.objects.filter(unidad=self.laboratorio).delete()
        HorarioOperacionUnidad.objects.create(
            unidad=self.laboratorio,
            dia_semana=1,
            hora_inicio=time(9, 0),
            hora_fin=time(13, 0),
        )
        CapacidadOperativaUnidad.objects.create(
            unidad=self.laboratorio,
            vigente_desde=date(2026, 9, 1),
            aforo_seguridad=10,
            puestos_mobiliario=8,
            puestos_equipados=4,
            capacidad_personal=6,
        )
        self._reserva(
            self.unidad_a,
            hora=9,
            numero_participantes=4,
            estado="completada",
            resultado_cierre="atendida",
            detalle_ejecucion={
                "registrada_en": "2026-09-08T10:00:00-05:00",
                "horario_real": {"inicio": "09:00", "fin": "10:00"},
                "asistentes_total": 2,
            },
        )

        indicator = calculate_unit_utilization(
            self.laboratorio,
            date(2026, 9, 8),
            date(2026, 9, 8),
        )

        self.assertEqual(indicator["theoretical_person_hours"], 16)
        self.assertEqual(indicator["actual_person_hours"], 2)
        self.assertEqual(indicator["frequency"], 25.0)
        self.assertEqual(indicator["occupancy"], 50.0)
        self.assertEqual(indicator["utilization"], 12.5)

    def test_rechaza_fechas_invalidas_y_rangos_excesivos(self):
        url = reverse(
            "obtener_ocupacion_laboratorio", args=[self.laboratorio.pk]
        )
        cases = (
            ({"desde": "08-09-2026", "hasta": "2026-09-09"}, "AAAA-MM-DD"),
            ({"desde": "2026-09-10", "hasta": "2026-09-09"}, "anterior"),
            ({"desde": "2026-01-01", "hasta": "2026-12-31"}, "rango máximo"),
        )
        for params, expected_message in cases:
            with self.subTest(params=params):
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_message, response.json()["error"])
