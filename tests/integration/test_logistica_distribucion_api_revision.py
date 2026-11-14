"""Recuperación y verificación del paso 3 frente a registros incompatibles."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from apps.laboratorios.operacion.presentation import logistica_cerveza_servidor as cerveza
from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.formacion.presentation.logistica_partidas import ErrorPartida, _base_contexto, _serializar, _verificar
from apps.formacion.models.partidas_simulador import EventoPartida, PartidaSimulador, ParticipantePartida
from tests.integration.test_logistica_partidas import DatosPartidas


class EventosAislados:
    """Replica la proyección acotada del queryset sin acceso a una base."""

    def __init__(self, eventos):
        self.eventos = deepcopy(eventos)
        self.columnas = None
        self.limite = None

    def order_by(self, campo):
        assert campo == "revision"
        return self

    def values(self, *columnas):
        self.columnas = columnas
        return self

    def __getitem__(self, tramo):
        self.limite = tramo.stop
        return self.eventos[tramo]


def final_aislado():
    estado = motor.crear_estado("cd-normal", 42)
    eventos = [
        {
            "revision": 1,
            "tipo": "crear",
            "datos": {
                "caso": "cd-normal",
                "semilla": 42,
                "version_motor": motor.VERSION,
            },
        }
    ]
    for revision, decision in enumerate(
        motor.referencia("cd-normal", 42)["decisiones"], 2
    ):
        estado = motor.actuar(estado, decision)
        eventos.append(
            {"revision": revision, "tipo": "decision", "datos": {"decision": decision}}
        )
    return SimpleNamespace(
        simulador="operaciones",
        caso="cd-normal",
        semilla=42,
        version_motor=motor.VERSION,
        version_caso=motor.VERSION_CASO,
        estado=estado,
        observaciones={"operador": motor.observacion(estado)},
        resultado=motor.resultado(estado),
        revision=len(eventos),
        fase="terminada",
        eventos=EventosAislados(eventos),
        pk="qa-sin-bd",
        nombre="QA",
        propietario_id=7,
        actualizada_en=datetime.now(timezone.utc),
        get_deferred_fields=lambda: set(),
    )


class DistribucionRegistroTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original = final_aislado()

    def setUp(self):
        self.partida = deepcopy(self.original)

    def test_replay_valido_proyecta_registro_acotado_y_reconstruye_resultado(self):
        self.assertTrue(_verificar(self.partida))
        self.assertEqual(self.partida.eventos.columnas, ("revision", "tipo", "datos"))
        self.assertEqual(self.partida.eventos.limite, self.partida.revision + 1)

    def test_registro_incompleto_o_extra_se_rechaza_antes_de_recrear_motor(self):
        original = self.partida.eventos.eventos
        variantes = [
            original[1:],
            original[:-1],
            original
            + [{"revision": len(original) + 1, "tipo": "desconocido", "datos": {}}],
        ]
        for eventos in variantes:
            with self.subTest(eventos=len(eventos)):
                self.partida.eventos = EventosAislados(eventos)
                with patch(
                    "apps.formacion.presentation.logistica_partidas.operaciones.crear_estado",
                    side_effect=AssertionError("No interpretar registro incompleto"),
                ):
                    self.assertFalse(_verificar(self.partida))

    def test_revisiones_metadata_tipos_o_datos_alterados_invalidan_registro(self):
        cambios = [
            (0, "revision", 0),
            (0, "tipo", "decision"),
            (
                0,
                "datos",
                {"caso": "cd-pico", "semilla": 42, "version_motor": motor.VERSION},
            ),
            (1, "revision", 3),
            (1, "tipo", "crear"),
            (1, "tipo", "desconocido"),
            (1, "datos", []),
            (1, "datos", {}),
            (1, "datos", {"decision": []}),
            (1, "datos", {"decision": {}, "sobrante": True}),
        ]
        for indice, campo, valor in cambios:
            with self.subTest(indice=indice, campo=campo, valor=valor):
                self.partida = deepcopy(self.original)
                self.partida.eventos.eventos[indice][campo] = valor
                with patch(
                    "apps.formacion.presentation.logistica_partidas.operaciones.crear_estado",
                    side_effect=AssertionError("No interpretar registro alterado"),
                ):
                    self.assertFalse(_verificar(self.partida))

    def test_verificacion_compartida_conserva_cerveza_con_uno_y_cuatro_roles(self):
        for roles in (cerveza.ROLES[:1], cerveza.ROLES):
            with self.subTest(humanos=len(roles)):
                estado = cerveza.crear_estado("base", 13)
                eventos = [
                    {
                        "revision": 1,
                        "tipo": "crear",
                        "datos": {
                            "caso": "cerveza-base",
                            "semilla": 13,
                            "version_motor": cerveza.VERSION,
                        },
                    }
                ]
                for rol in roles:
                    eventos.append(
                        {
                            "revision": len(eventos) + 1,
                            "tipo": "unirse",
                            "datos": {"rol": rol},
                        }
                    )
                eventos.append(
                    {
                        "revision": len(eventos) + 1,
                        "tipo": "iniciar",
                        "datos": {"humanos": list(roles)},
                    }
                )
                for semana in range(1, estado["parametros"]["semanas"] + 1):
                    decisiones = {rol: 4 for rol in roles}
                    for rol in roles:
                        datos = {"rol": rol, "pedido": 4, "semana": semana}
                        if rol == roles[-1]:
                            datos.update(turno_resuelto=True, decisiones=decisiones)
                            estado = cerveza.avanzar(estado, decisiones)
                        eventos.append(
                            {
                                "revision": len(eventos) + 1,
                                "tipo": "pedido",
                                "datos": datos,
                            }
                        )
                partida = deepcopy(self.original)
                partida.simulador = "cerveza"
                partida.caso = "cerveza-base"
                partida.semilla = 13
                partida.version_motor = cerveza.VERSION
                partida.version_caso = "1.0.0"
                partida.estado = estado
                partida.observaciones = {
                    rol: cerveza.observacion(estado, rol) for rol in cerveza.ROLES
                }
                partida.resultado = cerveza.resultado(estado)
                partida.revision = len(eventos)
                partida.eventos = EventosAislados(eventos)
                self.assertTrue(_verificar(partida))

    def test_revision_fuera_de_cota_no_consulta_eventos(self):
        for revision in (0, True, 10001, motor.MAX_DECISIONES + 2):
            with self.subTest(revision=revision):
                self.partida.revision = revision
                self.partida.eventos = None
                self.assertFalse(_verificar(self.partida))

    def test_decision_ilegible_no_produce_excepcion_y_conserva_evidencia(self):
        eventos_antes = deepcopy(self.partida.eventos.eventos)
        self.partida.eventos.eventos[1]["datos"] = {
            "decision": {"accion": "no-existe", "objeto": "lote-a-1"}
        }
        self.assertFalse(_verificar(self.partida))
        self.assertEqual(self.partida.estado, self.original.estado)
        self.assertEqual(eventos_antes[0], self.partida.eventos.eventos[0])

    def test_observaciones_o_resultado_incompatible_tienen_conflicto_controlado(self):
        cambios = [
            ("observaciones", []),
            ("observaciones", "histórico"),
            ("observaciones", {"operador": []}),
            ("observaciones", {}),
            ("resultado", []),
        ]
        for campo, valor in cambios:
            with self.subTest(campo=campo, valor=valor):
                self.partida = deepcopy(self.original)
                setattr(self.partida, campo, valor)
                with self.assertRaises(ErrorPartida) as error:
                    _serializar(self.partida, [], None, SimpleNamespace(pk=7))
                self.assertEqual(error.exception.codigo, 409)

    def test_historia_estructurada_sigue_visible_sin_invocar_motor_actual(self):
        self.partida.version_motor = "0.9.0"
        self.partida.estado = {"esquema_anterior": True}
        with patch.object(
            motor, "observacion", side_effect=AssertionError("No reinterpretar")
        ):
            datos = _serializar(self.partida, [], None, SimpleNamespace(pk=7))
        self.assertTrue(datos["solo_lectura"])
        self.assertEqual(datos["estado"], self.original.observaciones["operador"])

    def test_login_preserva_ruta_caso_semilla_y_sesion_en_next(self):
        ruta = "/laboratorio/logistica/logistica/operaciones/?caso=cd-falla&semilla=0&sesion=12345678-1234-1234-1234-123456789abc"
        peticion = RequestFactory().get(ruta)
        unidad = SimpleNamespace(get_absolute_url=lambda: "/laboratorio/logistica/")
        contexto = _base_contexto(unidad, peticion)
        self.assertEqual(
            parse_qs(urlsplit(contexto["login_url"]).query)["next"], [ruta]
        )
        self.assertFalse(urlsplit(contexto["login_url"]).netloc)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DistribucionRecuperacionApiTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        limites = patch("apps.formacion.presentation.logistica_partidas._limitar")
        limites.start()
        self.addCleanup(limites.stop)
        original = final_aislado()
        self.partida = PartidaSimulador.objects.create(
            unidad=self.unidad,
            propietario=self.usuarios[0],
            simulador="operaciones",
            caso=original.caso,
            nombre="Registro QA privado",
            semilla=original.semilla,
            version_motor=original.version_motor,
            version_caso=original.version_caso,
            estado=original.estado,
            observaciones=original.observaciones,
            resultado=original.resultado,
            fase="terminada",
            revision=original.revision,
        )
        ParticipantePartida.objects.create(
            partida=self.partida, usuario=self.usuarios[0], rol="operador"
        )
        EventoPartida.objects.bulk_create(
            [
                EventoPartida(partida=self.partida, **evento)
                for evento in original.eventos.eventos
            ]
        )

    def test_vista_incompatible_da_409_y_exportacion_conserva_json_original(self):
        for observaciones in ([], "histórico", {"operador": []}):
            with self.subTest(observaciones=observaciones):
                PartidaSimulador.objects.filter(pk=self.partida.pk).update(
                    observaciones=observaciones
                )
                respuesta = self.clientes[0].get(
                    self.ops, {"sesion": str(self.partida.pk)}
                )
                self.assertEqual(respuesta.status_code, 409)
                self.assertEqual(set(respuesta.json()), {"error"})
                self.assertEqual(respuesta["Cache-Control"], "private, no-store")
                exportacion = self.clientes[0].get(
                    self.ops, {"sesion": str(self.partida.pk), "exportar": 1}
                )
                self.assertEqual(exportacion.status_code, 200)
                self.assertEqual(
                    exportacion.json()["estado_final"], self.partida.estado
                )

    def test_verificar_carga_eventos_una_vez_y_no_construye_exportacion(self):
        with patch(
            "apps.formacion.presentation.logistica_partidas._evidencia",
            side_effect=AssertionError("No duplicar exportación"),
        ):
            respuesta = self.clientes[0].get(
                self.ops, {"sesion": str(self.partida.pk), "verificar": 1}
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["verificada"])

    def test_registro_json_malformado_es_falso_y_no_500(self):
        EventoPartida.objects.filter(partida=self.partida, revision=2).update(datos=[])
        respuesta = self.clientes[0].get(
            self.ops, {"sesion": str(self.partida.pk), "verificar": 1}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()["verificada"])
        self.assertEqual(self.partida.eventos.count(), self.partida.revision)

    def test_partida_activa_no_exporta_ni_verifica_turnos_privados(self):
        PartidaSimulador.objects.filter(pk=self.partida.pk).update(fase="activa")
        for parametro in ("verificar", "exportar"):
            respuesta = self.clientes[0].get(
                self.ops, {"sesion": str(self.partida.pk), parametro: 1}
            )
            self.assertEqual(respuesta.status_code, 409)
