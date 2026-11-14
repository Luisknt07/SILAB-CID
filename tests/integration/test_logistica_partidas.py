"""Identidad, concurrencia, privacidad, persistencia y evidencia de simuladores."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.laboratorios.operacion.presentation import logistica_cerveza_servidor as cerveza
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.partidas_simulador import PartidaSimulador, ParticipantePartida
from apps.directorio_unidades.models.core import Unidad


class DatosPartidas:
    def preparar(self):
        cache.clear()
        self.unidad = Unidad.objects.create(
            nombre="Laboratorio de Logística",
            slug=SLUG_LOGISTICA,
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            activo=True,
        )
        self.usuarios = [
            get_user_model().objects.create_user(
                username=f"jugador{i}", password="test-solo-local"
            )
            for i in range(6)
        ]
        self.clientes = []
        for usuario in self.usuarios:
            cliente = Client()
            cliente.force_login(usuario)
            self.clientes.append(cliente)
        self.api = reverse("logistica_api_cerveza", args=[SLUG_LOGISTICA])
        self.ops = reverse("logistica_api_operaciones", args=[SLUG_LOGISTICA])

    def post(self, cliente, datos, url=None, esperado=200):
        response = cliente.post(url or self.api, datos, content_type="application/json")
        self.assertEqual(response.status_code, esperado, response.content[:1000])
        return response.json().get("sesion", response.json())

    def sala(self, numero=4):
        sesion = self.post(
            self.clientes[0],
            {"accion": "crear", "caso": "cerveza-base", "semilla": 13},
            esperado=201,
        )
        for i, rol in enumerate(cerveza.ROLES[:numero]):
            sesion = self.post(
                self.clientes[i + 1],
                {"accion": "unirse", "codigo": sesion["codigo"], "rol": rol},
            )
        sesion = self.post(
            self.clientes[0],
            {
                "accion": "iniciar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
        )
        return sesion

    def get(self, cliente, sesion, url=None, **params):
        response = cliente.get(url or self.api, {"sesion": sesion["id"], **params})
        self.assertEqual(response.status_code, 200, response.content[:1000])
        return response.json()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PartidasTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        self.limites = patch("apps.formacion.presentation.logistica_partidas._limitar")
        self.mock_limites = self.limites.start()
        self.addCleanup(self.limites.stop)

    def test_lectura_y_escritura_api_requieren_identidad(self):
        for url in (self.api, self.ops):
            self.assertEqual(Client().get(url).status_code, 401)
            self.assertEqual(
                Client()
                .post(url, {"accion": "crear"}, content_type="application/json")
                .status_code,
                401,
            )
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_csrf_no_se_desactiva_para_api(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuarios[0])
        self.assertEqual(
            cliente.post(
                self.api, {"accion": "crear"}, content_type="application/json"
            ).status_code,
            403,
        )

    def test_sala_cuatro_roles_y_estado_privado(self):
        sesion = self.sala()
        self.assertEqual(sesion["fase"], "activa")
        self.assertIsNone(sesion["observacion"])  # Facilitador no ve saldos privados.
        self.assertEqual(sesion["codigo"], "")
        for i, rol in enumerate(cerveza.ROLES):
            vista = self.get(self.clientes[i + 1], sesion)["sesion"]
            self.assertEqual(vista["rol"], rol)
            self.assertEqual(vista["observacion"]["rol"], rol)
            self.assertNotIn("etapas", vista["observacion"])
            self.assertNotIn("decisiones", vista["observacion"])
            self.assertIsNone(vista["resultado"])
            self.assertEqual(
                self.clientes[i + 1]
                .get(self.api, {"sesion": sesion["id"], "exportar": 1})
                .status_code,
                409,
            )

    def test_misma_semana_admite_revision_compartida_y_resuelve_una_vez(self):
        sesion = self.sala()
        revision = sesion["revision"]
        for i in range(4):
            vista = self.post(
                self.clientes[i + 1],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": revision,
                    "decision": {"pedido": 4, "semana": 1},
                },
            )
            self.assertEqual(
                vista["observacion"]["semanas_resueltas"], 1 if i == 3 else 0
            )
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        self.assertEqual(partida.estado["semana"], 1)
        self.assertEqual(
            partida.eventos.filter(tipo="pedido", datos__turno_resuelto=True).count(), 1
        )
        self.assertFalse(partida.participantes.exclude(pedido=None).exists())
        self.post(
            self.clientes[1],
            {
                "accion": "actuar",
                "sesion": sesion["id"],
                "revision": revision,
                "decision": {"pedido": 4, "semana": 1},
            },
            esperado=409,
        )
        self.assertEqual(
            PartidaSimulador.objects.get(pk=sesion["id"]).estado["semana"], 1
        )

    def test_duplicado_de_rol_no_sobrescribe_pedido(self):
        sesion = self.sala()
        datos = {
            "accion": "actuar",
            "sesion": sesion["id"],
            "revision": sesion["revision"],
            "decision": {"pedido": 0, "semana": 1},
        }
        vista = self.post(self.clientes[1], datos)
        self.assertTrue(vista["decision_enviada"])
        self.post(self.clientes[1], datos, esperado=409)
        self.assertEqual(
            ParticipantePartida.objects.get(
                partida_id=sesion["id"], rol="minorista"
            ).pedido,
            0,
        )

    def test_roles_y_usuarios_no_se_pueden_duplicar(self):
        sesion = self.post(self.clientes[0], {"accion": "crear"}, esperado=201)
        self.post(
            self.clientes[1],
            {"accion": "unirse", "codigo": sesion["codigo"], "rol": "minorista"},
        )
        self.post(
            self.clientes[1],
            {"accion": "unirse", "codigo": sesion["codigo"], "rol": "mayorista"},
            esperado=409,
        )
        self.post(
            self.clientes[2],
            {"accion": "unirse", "codigo": sesion["codigo"], "rol": "minorista"},
            esperado=409,
        )
        self.assertEqual(ParticipantePartida.objects.count(), 1)

    def test_otro_usuario_no_observa_modifica_ni_exporta_partida(self):
        sesion = self.sala(numero=1)
        for params in ({}, {"exportar": 1}, {"verificar": 1}):
            self.assertEqual(
                self.clientes[5]
                .get(self.api, {"sesion": sesion["id"], **params})
                .status_code,
                404,
            )
        self.post(
            self.clientes[5],
            {
                "accion": "cerrar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
            esperado=404,
        )
        self.assertEqual(self.clientes[5].get(self.api).json()["sesiones"], [])

    def test_facilitador_es_unico_que_inicia_y_archiva(self):
        sesion = self.post(self.clientes[0], {"accion": "crear"}, esperado=201)
        sesion = self.post(
            self.clientes[1],
            {"accion": "unirse", "codigo": sesion["codigo"], "rol": "minorista"},
        )
        self.post(
            self.clientes[1],
            {
                "accion": "iniciar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
            esperado=403,
        )
        self.post(
            self.clientes[1],
            {
                "accion": "cerrar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
            esperado=403,
        )
        archivada = self.post(
            self.clientes[0],
            {
                "accion": "cerrar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
        )
        self.assertEqual(archivada["fase"], "cerrada")
        self.assertIsNone(archivada["resultado"])
        self.assertEqual(PartidaSimulador.objects.count(), 1)

    def test_solo_un_humano_y_bots_vacantes_finalizan_replay(self):
        sesion = self.sala(numero=1)
        self.assertEqual(sum(p["automatico"] for p in sesion["participantes"]), 3)
        for semana in range(1, 25):
            sesion = self.post(
                self.clientes[1],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"pedido": 4, "semana": semana},
                },
            )
        self.assertEqual(sesion["fase"], "terminada")
        self.assertGreaterEqual(sesion["resultado"]["puntaje"], 0)
        self.assertLessEqual(sesion["resultado"]["puntaje"], 100)
        self.assertTrue(self.get(self.clientes[0], sesion, verificar=1)["verificada"])
        evidencia = self.get(self.clientes[1], sesion, exportar=1)
        self.assertEqual(evidencia["version_motor"], cerveza.VERSION)
        self.assertEqual(evidencia["estado_final"]["semana"], 24)
        self.assertNotIn("jugador0", str(evidencia))
        self.post(
            self.clientes[1],
            {
                "accion": "actuar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
                "decision": {"pedido": 4},
            },
            esperado=409,
        )

    def test_pedido_booleano_negativo_o_excesivo_no_muta(self):
        sesion = self.sala(numero=1)
        revision = sesion["revision"]
        for pedido in (True, -1, 201, "4", None, 1.5):
            self.post(
                self.clientes[1],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": revision,
                    "decision": {"pedido": pedido},
                },
                esperado=400,
            )
        self.assertEqual(
            PartidaSimulador.objects.get(pk=sesion["id"]).revision, revision
        )

    def test_etag_no_transfiere_estado_no_cambia_revision_ni_escribe(self):
        sesion = self.sala(numero=1)
        response = self.clientes[1].get(self.api, {"sesion": sesion["id"]})
        with CaptureQueriesContext(connection) as consultas:
            igual = self.clientes[1].get(
                self.api, {"sesion": sesion["id"]}, HTTP_IF_NONE_MATCH=response["ETag"]
            )
        self.assertEqual(igual.status_code, 304)
        self.assertEqual(igual.content, b"")
        self.assertFalse(
            any(
                q["sql"].lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
                for q in consultas
            )
        )
        self.assertLessEqual(len(consultas), 9)
        self.assertEqual(igual["Cache-Control"], "private, no-store")

    def test_partida_operaciones_persistente_y_prueba_ia_reservada(self):
        sesion = self.post(
            self.clientes[0],
            {"accion": "crear", "caso": "ia-pronostico"},
            self.ops,
            201,
        )
        self.assertEqual(len(sesion["estado"]["datos"]["serie"]), 48)
        for accion in ("entrenar", "seleccionar", "evaluar"):
            sesion = self.post(
                self.clientes[0],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"accion": accion, "objeto": "pronostico"},
                },
                self.ops,
            )
        self.assertEqual(sesion["fase"], "terminada")
        self.assertEqual(len(sesion["estado"]["datos"]["serie"]), 60)
        self.assertTrue(
            self.get(self.clientes[0], sesion, self.ops, verificar=1)["verificada"]
        )
        nuevo_cliente = Client()
        nuevo_cliente.force_login(self.usuarios[0])
        self.assertEqual(
            self.get(nuevo_cliente, sesion, self.ops)["sesion"]["estado"],
            sesion["estado"],
        )
        self.assertEqual(
            self.clientes[0].get(self.api, {"sesion": sesion["id"]}).status_code, 404
        )

    def test_historial_alterado_es_detectado_al_reproducir(self):
        sesion = self.post(
            self.clientes[0],
            {"accion": "crear", "caso": "ia-pronostico"},
            self.ops,
            201,
        )
        for accion in ("entrenar", "seleccionar", "evaluar"):
            sesion = self.post(
                self.clientes[0],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"accion": accion, "objeto": "pronostico"},
                },
                self.ops,
            )
        PartidaSimulador.objects.filter(pk=sesion["id"]).update(
            estado={"alterado": True}
        )
        self.assertFalse(
            self.get(self.clientes[0], sesion, self.ops, verificar=1)["verificada"]
        )

    def test_casos_semillas_y_carga_json_se_validan(self):
        for datos in (
            {"accion": "crear", "caso": "no-existe"},
            {"accion": "crear", "semilla": True},
            {"accion": "crear", "semilla": -1},
            {"accion": "crear", "nombre": "x" * 121},
            [],
        ):
            self.post(self.clientes[0], datos, esperado=400)
        self.assertEqual(
            self.clientes[0]
            .post(self.api, "{}", content_type="text/plain")
            .status_code,
            400,
        )
        self.assertEqual(
            self.clientes[0]
            .post(self.api, "{", content_type="application/json")
            .status_code,
            400,
        )
        self.assertEqual(
            self.clientes[0]
            .post(
                self.api,
                '{"accion":"crear","nombre":"' + "x" * 5000 + '"}',
                content_type="application/json",
            )
            .status_code,
            400,
        )
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_visibilidad_tipologia_unidad_y_seccion_tambien_rigen_api(self):
        AjusteSeccionPlanta.objects.create(
            unidad=self.unidad, numero="4.4", oculta=True
        )
        self.assertEqual(self.clientes[0].get(self.api).status_code, 404)
        self.assertEqual(self.clientes[0].get(self.ops).status_code, 404)
        self.assertEqual(
            self.clientes[0]
            .post(self.api, {"accion": "crear"}, content_type="application/json")
            .status_code,
            404,
        )
        AjusteSeccionPlanta.objects.all().delete()
        self.unidad.activo = False
        self.unidad.save(update_fields=["activo"])
        self.assertEqual(self.clientes[0].get(self.api).status_code, 404)

    def test_limite_de_partidas_activas_y_paginacion_no_carga_estados(self):
        for i in range(20):
            self.post(
                self.clientes[0], {"accion": "crear", "nombre": str(i)}, esperado=201
            )
        self.post(self.clientes[0], {"accion": "crear"}, esperado=409)
        with CaptureQueriesContext(connection) as consultas:
            lista = self.clientes[0].get(self.api).json()
        self.assertEqual(len(lista["sesiones"]), 20)
        self.assertFalse(lista["siguiente"])
        select = next(q["sql"] for q in consultas if "SELECT DISTINCT" in q["sql"])
        self.assertNotIn('"estado"', select)
        self.assertLessEqual(len(consultas), 9)

    def test_rate_limit_regresa_429_sin_mutacion(self):
        from apps.formacion.presentation.logistica_partidas import ErrorPartida

        self.mock_limites.side_effect = ErrorPartida("Espera.", 429)
        self.post(self.clientes[0], {"accion": "crear"}, esperado=429)
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_version_historica_no_se_reinterpreta_con_motor_nuevo(self):
        sesion = self.sala(numero=1)
        PartidaSimulador.objects.filter(pk=sesion["id"]).update(
            version_motor="historico"
        )
        self.post(
            self.clientes[1],
            {
                "accion": "actuar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
                "decision": {"pedido": 4},
            },
            esperado=409,
        )

    def test_lectura_historica_usa_vista_persistida_sin_recalcular_motor(self):
        sesion = self.sala(numero=1)
        PartidaSimulador.objects.filter(pk=sesion["id"]).update(
            version_motor="historico"
        )
        with patch(
            "apps.formacion.presentation.logistica_partidas.cerveza.observacion",
            side_effect=AssertionError("No recalcular lectura"),
        ):
            with CaptureQueriesContext(connection) as consultas:
                vista = self.get(self.clientes[1], sesion)["sesion"]
        self.assertEqual(vista["observacion"]["semana"], 1)
        self.assertEqual(vista["version_motor"], "historico")
        select = next(
            q["sql"] for q in consultas if 'FROM "webcitt_partidasimulador"' in q["sql"]
        )
        self.assertNotIn('"estado"', select)

    def test_no_existe_api_en_otras_unidades_ni_en_centros(self):
        otra = Unidad.objects.create(
            nombre="Centro",
            slug="centro-otra",
            dependencia="centros",
            fecha_inicio=date(2026, 1, 1),
        )
        self.assertEqual(
            self.clientes[0]
            .get(reverse("logistica_api_cerveza", args=[otra.slug]))
            .status_code,
            404,
        )
        self.assertEqual(
            self.clientes[0]
            .get(reverse("logistica_api_operaciones", args=[otra.slug]))
            .status_code,
            404,
        )


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConcurrenciaPartidasTests(DatosPartidas, TransactionTestCase):
    def setUp(self):
        self.preparar()

    @patch("apps.formacion.presentation.logistica_partidas._limitar")
    def test_cuatro_conexiones_deciden_simultaneamente_y_solo_resuelven_un_turno(
        self, limite
    ):
        if connection.vendor != "postgresql":
            self.skipTest(
                "La concurrencia contractual requiere bloqueos de fila de PostgreSQL."
            )
        sesion = self.sala()
        barrera = Barrier(4)

        def enviar(i):
            close_old_connections()
            cliente = Client()
            cliente.force_login(self.usuarios[i + 1])
            barrera.wait(timeout=10)
            response = cliente.post(
                self.api,
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"pedido": i + 4, "semana": 1},
                },
                content_type="application/json",
            )
            valor = (response.status_code, response.json())
            close_old_connections()
            return valor

        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            respuestas = list(ejecutor.map(enviar, range(4)))
        self.assertEqual([r[0] for r in respuestas], [200] * 4, respuestas)
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        self.assertEqual(partida.estado["semana"], 1)
        self.assertEqual(
            partida.eventos.filter(tipo="pedido", datos__turno_resuelto=True).count(), 1
        )
        self.assertEqual(
            partida.estado["decisiones"][0], dict(zip(cerveza.ROLES, range(4, 8)))
        )
