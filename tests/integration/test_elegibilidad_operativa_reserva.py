"""Las decisiones futuras revalidan recursos sin impedir documentar el pasado."""

import json
from datetime import time, timedelta

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.reservas.presentation.aprobacion import aprobar_reserva
from apps.reservas.presentation.transiciones_operativas import transicionar_reserva_operativa
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import NotificacionReserva, Reserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_aprobacion_reserva import crear_responsable
from tests.integration.test_autoridad_escritores_reserva import crear_unidad


@override_settings(CITT_EXIGIR_EQUIPOS_VERIFICADOS=False)
class ElegibilidadOperativaReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.admin = usuario.objects.create_user("elegibilidad-admin")
        cls.titular = usuario.objects.create_user("elegibilidad-titular")
        cls.tecnico = usuario.objects.create_user("elegibilidad-tecnico")
        cls.unidad = crear_unidad("elegibilidad", cls.admin)
        cls.otra_unidad = crear_unidad("elegibilidad-otra")
        cls.responsable = crear_responsable(
            cls.unidad, cls.tecnico, "Técnico de elegibilidad"
        )
        equipo = EquiposServicios.objects.create(
            codigo="ELEG-01", nombre="Maqueta logística"
        )
        cls.equipo = UnidadEquipo.objects.create(
            equipo=equipo,
            laboratorio=cls.unidad,
            codigo_unidad="ELEG-FIS-01",
            activa=True,
            estado_unidad="disponible",
            existencia_verificada=True,
        )
        cls.espacio = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo="ELEG-AREA-01", nombre="Área de maquetas"
        )
        cls.software = SoftwareDisponible.objects.create(
            unidad=cls.unidad,
            nombre="Simulador local",
            tipo_acceso="licencia",
            licencias_totales=2,
            licencias_disponibles=2,
        )

    def reserva(self, *, estado="pendiente", pasada=False, equipos=True):
        return Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.titular,
            fecha=timezone.localdate() + timedelta(days=-1 if pasada else 1),
            hora_inicio=time(9),
            hora_fin=time(10),
            estado=estado,
            unidades_seleccionadas=json.dumps(
                [{"id": self.equipo.pk, "codigo": self.equipo.codigo_unidad}]
                if equipos
                else []
            ),
        )

    def aprobar(self, reserva):
        return aprobar_reserva(
            reserva,
            actor=self.admin,
            responsable_id=self.responsable.pk,
            unidad_esperada=self.unidad.pk,
        )

    def iniciar(self, reserva):
        return transicionar_reserva_operativa(
            reserva,
            actor=self.admin,
            accion="iniciar",
            responsable_id=self.responsable.pk,
            unidad_esperada=self.unidad.pk,
        )

    def foto(self, reserva):
        return (
            list(Reserva.objects.filter(pk=reserva.pk).values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
        )

    def rechaza_sin_efectos(self, operacion, reserva, mensaje):
        antes = self.foto(reserva)
        with self.assertRaisesMessage(ValueError, mensaje):
            operacion(reserva)
        self.assertEqual(self.foto(reserva), antes)

    def test_aprobacion_rechaza_estados_no_disponibles_del_equipo(self):
        for estado in ("mantenimiento", "dañado", "prestado", "no_disponible"):
            with self.subTest(estado=estado):
                UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
                    estado_unidad=estado
                )
                self.rechaza_sin_efectos(
                    self.aprobar, self.reserva(), "Maqueta logística"
                )

    def test_inicio_relee_mantenimiento_posterior_a_aprobacion(self):
        reserva = self.aprobar(self.reserva())
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            estado_unidad="mantenimiento"
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "mantenimiento")

    def test_inicio_rechaza_equipo_retirado(self):
        reserva = self.reserva(estado="confirmada")
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(activa=False)
        self.rechaza_sin_efectos(self.iniciar, reserva, "retirado del servicio")

    def test_inicio_rechaza_equipo_que_dejo_de_pertenecer_a_unidad(self):
        reserva = self.reserva(estado="confirmada")
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            laboratorio=self.otra_unidad
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "ya no está asociado")

    def test_equipo_compartido_sigue_siendo_elegible(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            laboratorio=self.otra_unidad
        )
        self.equipo.laboratorios.add(self.unidad)
        reserva = self.aprobar(self.reserva())
        self.assertEqual(self.iniciar(reserva).estado, "en_proceso")

    def test_inicio_rechaza_identificador_de_equipo_inexistente(self):
        reserva = self.reserva(estado="confirmada")
        Reserva.objects.filter(pk=reserva.pk).update(
            unidades_seleccionadas=json.dumps([{"id": self.equipo.pk + 999999}])
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "ya no existe")

    @override_settings(CITT_EXIGIR_EQUIPOS_VERIFICADOS=True)
    def test_respeta_la_politica_existente_de_existencia_verificada(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            existencia_verificada=False
        )
        self.rechaza_sin_efectos(
            self.aprobar, self.reserva(), "no tiene existencia verificada"
        )
        self.rechaza_sin_efectos(
            self.iniciar,
            self.reserva(estado="confirmada"),
            "no tiene existencia verificada",
        )

    def test_no_activa_una_politica_nueva_de_verificacion(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            existencia_verificada=False
        )
        self.assertEqual(self.aprobar(self.reserva()).estado, "confirmada")

    def test_inicio_rechaza_espacio_desactivado_o_no_reservable(self):
        reserva = self.reserva(estado="confirmada")
        reserva.espacios_solicitados.add(self.espacio)
        for valores in ({"activo": False}, {"activo": True, "reservable": False}):
            with self.subTest(valores=valores):
                EspacioReservable.objects.filter(pk=self.espacio.pk).update(**valores)
                self.rechaza_sin_efectos(self.iniciar, reserva, "no está habilitado")

    def test_inicio_rechaza_espacio_de_otra_unidad(self):
        reserva = self.reserva(estado="confirmada")
        reserva.espacios_solicitados.add(self.espacio)
        EspacioReservable.objects.filter(pk=self.espacio.pk).update(
            unidad=self.otra_unidad
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "ya no pertenece")

    def test_inicio_rechaza_software_desactivado_o_sin_licencias(self):
        reserva = self.reserva(estado="confirmada")
        reserva.software_solicitado.add(self.software)
        for valores, mensaje in (
            ({"activo": False}, "deshabilitado"),
            ({"activo": True, "licencias_disponibles": 0}, "licencias disponibles"),
        ):
            with self.subTest(valores=valores):
                SoftwareDisponible.objects.filter(pk=self.software.pk).update(**valores)
                self.rechaza_sin_efectos(self.iniciar, reserva, mensaje)

    def test_inicio_rechaza_software_de_otra_unidad(self):
        reserva = self.reserva(estado="confirmada")
        reserva.software_solicitado.add(self.software)
        SoftwareDisponible.objects.filter(pk=self.software.pk).update(
            unidad=self.otra_unidad
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "ya no pertenece")

    def test_software_instalado_no_puede_usar_solo_equipos_fuera_de_servicio(self):
        reserva = self.reserva(estado="confirmada", equipos=False)
        reserva.software_solicitado.add(self.software)
        SoftwareDisponible.objects.filter(pk=self.software.pk).update(
            tipo_acceso="instalacion"
        )
        self.software.equipos_instalados.add(self.equipo)
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            estado_unidad="mantenimiento"
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "equipo instalado disponible")

    def test_inicio_revalida_un_bloqueo_de_agenda_nuevo(self):
        reserva = self.aprobar(self.reserva())
        BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            titulo="Cierre preventivo",
            fecha_inicio=reserva.fecha,
            fecha_fin=reserva.fecha,
            dia_completo=True,
            alcance="unidad_completa",
        )
        self.rechaza_sin_efectos(self.iniciar, reserva, "Cierre preventivo")

    def test_aprobacion_rechaza_el_bloqueo_de_un_equipo_seleccionado(self):
        reserva = self.reserva()
        bloqueo = BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            titulo="Revisión de maqueta",
            fecha_inicio=reserva.fecha,
            fecha_fin=reserva.fecha,
            dia_completo=True,
            alcance="equipos",
        )
        bloqueo.equipos.add(self.equipo)
        self.rechaza_sin_efectos(self.aprobar, reserva, "Revisión de maqueta")

    def test_inicio_revalida_solapamiento_y_excluye_su_propia_reserva(self):
        reserva = self.reserva(estado="confirmada")
        self.reserva(estado="confirmada")
        self.rechaza_sin_efectos(self.iniciar, reserva, "ya está reservado")

    def test_http_devuelve_conflicto_controlado_por_equipo_fuera_de_servicio(self):
        reserva = self.reserva(estado="confirmada")
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            estado_unidad="mantenimiento"
        )
        self.client.force_login(self.admin)
        antes = self.foto(reserva)
        respuesta = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, reserva.pk]),
            {"accion": "iniciar"},
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertFalse(respuesta.json()["success"])
        self.assertIn("mantenimiento", respuesta.json()["error"])
        self.assertEqual(self.foto(reserva), antes)

    def test_cierres_retrospectivos_no_dependen_de_elegibilidad_actual(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(
            activa=False, estado_unidad="mantenimiento"
        )
        for accion in ("no_atendida", "no_presentado"):
            with self.subTest(accion=accion):
                reserva = self.reserva(estado="confirmada", pasada=True)
                resultado = transicionar_reserva_operativa(
                    reserva,
                    actor=self.admin,
                    accion=accion,
                    observacion="Se documenta el resultado de la sesión pasada.",
                    unidad_esperada=self.unidad.pk,
                )
                self.assertEqual(resultado.estado, accion)

    def test_http_selecciones_corruptas_devuelven_409_sin_efectos(self):
        self.client.force_login(self.admin)
        selecciones = [
            "JSON roto",
            "null",
            json.dumps({"id": self.equipo.pk}),
            json.dumps([{}]),
            json.dumps([{"id": {}}]),
            json.dumps([{"id": []}]),
            json.dumps([{"id": True}]),
            json.dumps([{"id": 1.5}]),
            json.dumps([{"id": -1}]),
            json.dumps([{"id": 2**80}]),
        ]
        for accion, estado in (("aprobar", "pendiente"), ("iniciar", "confirmada")):
            for seleccion in selecciones:
                with self.subTest(accion=accion, seleccion=seleccion):
                    reserva = self.reserva(estado=estado)
                    Reserva.objects.filter(pk=reserva.pk).update(
                        unidades_seleccionadas=seleccion
                    )
                    antes = self.foto(reserva)
                    respuesta = self.client.post(
                        reverse(
                            "gestion_reserva_accion",
                            args=[self.unidad.slug, reserva.pk],
                        ),
                        {"accion": accion, "responsable_id": self.responsable.pk},
                    )
                    self.assertEqual(respuesta.status_code, 409)
                    self.assertFalse(respuesta.json()["success"])
                    self.assertIn("selección de equipos", respuesta.json()["error"])
                    self.assertEqual(self.foto(reserva), antes)

    def test_selecciones_validas_heredadas_conservan_compatibilidad(self):
        selecciones = [
            [{"id": self.equipo.pk, "codigo": self.equipo.codigo_unidad}],
            [{"id": str(self.equipo.pk)}],
            [self.equipo.pk],
            [str(self.equipo.pk)],
            [],
        ]
        for indice, seleccion in enumerate(selecciones):
            with self.subTest(seleccion=seleccion):
                reserva = self.reserva()
                Reserva.objects.filter(pk=reserva.pk).update(
                    unidades_seleccionadas=json.dumps(seleccion),
                    hora_inicio=time(8 + indice),
                    hora_fin=time(9 + indice),
                )
                aprobada = self.aprobar(reserva)
                self.assertEqual(self.iniciar(aprobada).estado, "en_proceso")
