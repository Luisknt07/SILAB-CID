"""Casos adversariales del API: privacidad, atomicidad e integridad de evidencia.

No ejecuta comandos ni necesita datos institucionales reales. Cada prueba usa
la base aislada del runner autorizado. Las pruebas de concurrencia exigen SQL
con bloqueos de fila reales de PostgreSQL.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import re
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.db import close_old_connections, connection
from django.test import (
    Client,
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.test.utils import CaptureQueriesContext

from apps.laboratorios.operacion.presentation import logistica_cerveza_servidor as cerveza
from apps.formacion.presentation.logistica_partidas import ErrorPartida, _limitar
from apps.formacion.models.partidas_simulador import EventoPartida, PartidaSimulador, ParticipantePartida
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_logistica_partidas import DatosPartidas


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PartidasAdversarialTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        limites = patch("apps.formacion.presentation.logistica_partidas._limitar")
        limites.start()
        self.addCleanup(limites.stop)

    def test_json_profundo_menor_a_4kb_es_rechazado_sin_escribir(self):
        cuerpo = '{"accion":"crear","x":' + "[" * 1200 + "0" + "]" * 1200 + "}"
        self.assertLess(len(cuerpo.encode()), 4096)
        for url in (self.api, self.ops):
            respuesta = self.clientes[0].post(
                url, cuerpo, content_type="application/json"
            )
            self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(PartidaSimulador.objects.count(), 0)
        self.assertEqual(EventoPartida.objects.count(), 0)

    def test_metodos_no_admitidos_y_get_accion_no_mutan(self):
        for metodo in ("put", "patch", "delete", "options"):
            for url in (self.api, self.ops):
                respuesta = getattr(self.clientes[0], metodo)(
                    url, '{"accion":"crear"}', content_type="application/json"
                )
                self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(
            self.clientes[0].get(self.api, {"accion": "crear"}).status_code, 200
        )
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_partida_de_otra_unidad_no_se_abre_aunque_sea_del_mismo_propietario(self):
        otra = Unidad.objects.create(
            nombre="Unidad QA separada",
            slug="unidad-qa-separada",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
        )
        partida = PartidaSimulador.objects.create(
            unidad=otra,
            propietario=self.usuarios[0],
            simulador="cerveza",
            caso="cerveza-base",
            nombre="Otra unidad",
            version_motor=cerveza.VERSION,
            estado=cerveza.crear_estado(),
        )
        for params in ({}, {"exportar": 1}, {"verificar": 1}):
            self.assertEqual(
                self.clientes[0]
                .get(self.api, {"sesion": str(partida.pk), **params})
                .status_code,
                404,
            )
        self.post(
            self.clientes[0],
            {
                "accion": "cerrar",
                "sesion": str(partida.pk),
                "revision": 0,
            },
            esperado=404,
        )
        partida.refresh_from_db()
        self.assertEqual(partida.fase, "sala")
        self.assertEqual(partida.revision, 0)

    def test_parametros_raw_estado_y_rol_no_exponen_saldos_ajenos(self):
        sesion = self.sala()
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        partida.estado["canario_privado"] = "NO_PUBLICAR_ESTADO_CRUDO"
        partida.observaciones["fabrica"]["canario_privado"] = "NO_PUBLICAR_OTRO_ROL"
        partida.save(update_fields=["estado", "observaciones"])
        respuesta = self.clientes[1].get(
            self.api,
            {
                "sesion": sesion["id"],
                "raw": 1,
                "estado": 1,
                "rol": "fabrica",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["sesion"]["rol"], "minorista")
        self.assertNotIn("NO_PUBLICAR", respuesta.content.decode())
        self.assertNotIn("estado", respuesta.json()["sesion"])

    def test_etag_de_otro_rol_no_devuelve_304_ni_permite_acceso_ajeno(self):
        sesion = self.sala()
        etag = self.clientes[1].get(self.api, {"sesion": sesion["id"]})["ETag"]
        mayorista = self.clientes[2].get(
            self.api, {"sesion": sesion["id"]}, HTTP_IF_NONE_MATCH=etag
        )
        self.assertEqual(mayorista.status_code, 200)
        self.assertNotEqual(mayorista["ETag"], etag)
        self.assertEqual(mayorista.json()["sesion"]["observacion"]["rol"], "mayorista")
        self.assertEqual(
            self.clientes[5]
            .get(self.api, {"sesion": sesion["id"]}, HTTP_IF_NONE_MATCH=etag)
            .status_code,
            404,
        )

    def test_inyeccion_de_rol_estado_o_futuro_en_decision_no_muta(self):
        sesion = self.sala(numero=1)
        revision = sesion["revision"]
        for campo, valor in (
            ("rol", "fabrica"),
            ("estado", {"semana": 24}),
            ("demanda_futura", [999]),
        ):
            self.post(
                self.clientes[1],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": revision,
                    "decision": {"pedido": 4, "semana": 1, campo: valor},
                },
                esperado=400,
            )
        self.assertEqual(
            PartidaSimulador.objects.get(pk=sesion["id"]).revision, revision
        )
        self.assertFalse(ParticipantePartida.objects.exclude(pedido=None).exists())
        self.assertFalse(EventoPartida.objects.filter(tipo="pedido").exists())

    def test_error_del_motor_revierte_pedido_estado_revision_y_eventos(self):
        sesion = self.sala(numero=1)
        antes = PartidaSimulador.objects.get(pk=sesion["id"])
        eventos = antes.eventos.count()
        with patch(
            "apps.formacion.presentation.logistica_partidas.cerveza.avanzar",
            side_effect=ValueError("Error controlado QA"),
        ):
            self.post(
                self.clientes[1],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"pedido": 7, "semana": 1},
                },
                esperado=400,
            )
        despues = PartidaSimulador.objects.get(pk=sesion["id"])
        self.assertEqual(despues.estado, antes.estado)
        self.assertEqual(despues.observaciones, antes.observaciones)
        self.assertEqual(despues.revision, antes.revision)
        self.assertEqual(despues.eventos.count(), eventos)
        self.assertIsNone(despues.participantes.get(rol="minorista").pedido)

    def test_sala_sin_humanos_no_se_activa_y_no_se_pierde(self):
        sesion = self.post(self.clientes[0], {"accion": "crear"}, esperado=201)
        self.post(
            self.clientes[0],
            {
                "accion": "iniciar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
            },
            esperado=409,
        )
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        self.assertEqual(partida.fase, "sala")
        self.assertEqual(partida.revision, sesion["revision"])
        self.assertEqual(partida.eventos.count(), 1)

    def test_prueba_ia_no_sale_por_exportacion_verificacion_ni_parametros_raw(self):
        sesion = self.post(
            self.clientes[0],
            {
                "accion": "crear",
                "caso": "ia-pronostico",
            },
            self.ops,
            201,
        )
        for parametro in ("exportar", "verificar"):
            self.assertEqual(
                self.clientes[0]
                .get(
                    self.ops,
                    {
                        "sesion": sesion["id"],
                        parametro: 1,
                    },
                )
                .status_code,
                409,
            )
        for parametros in ({}, {"raw": 1, "estado": 1}):
            vista = self.get(self.clientes[0], sesion, self.ops, **parametros)["sesion"]
            self.assertEqual(len(vista["estado"]["datos"]["serie"]), 48)
            self.assertIsNone(vista["resultado"])
        self.assertEqual(
            len(PartidaSimulador.objects.get(pk=sesion["id"]).estado["datos"]["serie"]),
            60,
        )

    def test_lectura_historica_no_invoca_motor_actual_ni_consulta_estado_crudo(self):
        sesion = self.sala(numero=1)
        esperado = self.get(self.clientes[1], sesion)["sesion"]["observacion"]
        PartidaSimulador.objects.filter(pk=sesion["id"]).update(
            version_motor="version-anterior",
            estado={"estructura_antigua": "conservada"},
        )
        with patch(
            "apps.formacion.presentation.logistica_partidas.cerveza.observacion",
            side_effect=AssertionError("No reinterpretar historia"),
        ):
            with CaptureQueriesContext(connection) as consultas:
                vista = self.get(self.clientes[1], sesion)["sesion"]
        self.assertEqual(vista["observacion"], esperado)
        self.assertEqual(vista["version_motor"], "version-anterior")
        tabla = re.escape(PartidaSimulador._meta.db_table)
        selects = [
            q["sql"].split(" FROM ", 1)[0]
            for q in consultas
            if q["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertFalse(
            any(re.search(r'"' + tabla + r'"\."estado"', sql) for sql in selects)
        )
        # La interfaz envía semana: el rechazo de versión debe preceder a la
        # interpretación de un esquema histórico que ya no conoce el motor.
        self.post(
            self.clientes[1],
            {
                "accion": "actuar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
                "decision": {"pedido": 4, "semana": 1},
            },
            esperado=409,
        )

    def test_sondeo_304_no_carga_json_de_estado_observaciones_ni_resultado(self):
        sesion = self.sala(numero=1)
        etag = self.clientes[1].get(self.api, {"sesion": sesion["id"]})["ETag"]
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.clientes[1].get(
                self.api, {"sesion": sesion["id"]}, HTTP_IF_NONE_MATCH=etag
            )
        self.assertEqual(respuesta.status_code, 304)
        tabla = re.escape(PartidaSimulador._meta.db_table)
        selects = [
            q["sql"].split(" FROM ", 1)[0]
            for q in consultas
            if q["sql"].lstrip().upper().startswith("SELECT")
        ]
        for campo in ("estado", "observaciones", "resultado"):
            self.assertFalse(
                any(
                    re.search(r'"' + tabla + r'"\."' + campo + '"', sql)
                    for sql in selects
                ),
                campo,
            )

    def test_listado_extrae_puntaje_sin_cargar_json_completo(self):
        self.post(self.clientes[0], {"accion": "crear"}, esperado=201)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.clientes[0].get(self.api)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["sesiones"]), 1)
        self.assertIn("puntaje", respuesta.json()["sesiones"][0])
        tabla = re.escape(PartidaSimulador._meta.db_table)
        selects = [
            q["sql"].split(" FROM ", 1)[0]
            for q in consultas
            if q["sql"].lstrip().upper().startswith("SELECT")
        ]
        for campo in ("estado", "observaciones", "resultado"):
            # La extracción SQL resultado->'puntaje' es intencional; no admite
            # seleccionar el documento completo como columna de cada tarjeta.
            campo_completo = r'"' + tabla + r'"\."' + campo + r'"(?!\s*(?:->|#>))'
            self.assertFalse(
                any(re.search(campo_completo, sql) for sql in selects), campo
            )

    def test_verificacion_detecta_resultado_alterado_aunque_el_estado_sea_reproducible(
        self,
    ):
        sesion = self.post(
            self.clientes[0],
            {
                "accion": "crear",
                "caso": "ia-pronostico",
            },
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
        self.assertTrue(
            self.get(self.clientes[0], sesion, self.ops, verificar=1)["verificada"]
        )
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        resultado = dict(partida.resultado)
        resultado["puntaje"] = resultado["puntaje"] + 0.01
        PartidaSimulador.objects.filter(pk=partida.pk).update(resultado=resultado)
        self.assertFalse(
            self.get(self.clientes[0], sesion, self.ops, verificar=1)["verificada"]
        )


class RatePartidasAdversarialTests(SimpleTestCase):
    def test_limite_real_de_cache_acepta_hasta_cupo_y_rechaza_la_siguiente(self):
        cache.clear()
        self.addCleanup(cache.clear)
        usuario, unidad = SimpleNamespace(pk=77), SimpleNamespace(pk=88)
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 10, 11, 12, tzinfo=timezone.utc),
        ):
            for _ in range(3):
                _limitar(usuario, unidad, "qa", 3)
            with self.assertRaises(ErrorPartida) as error:
                _limitar(usuario, unidad, "qa", 3)
        self.assertEqual(error.exception.codigo, 429)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CupoConcurrentePartidasTests(DatosPartidas, TransactionTestCase):
    def setUp(self):
        self.preparar()

    @patch("apps.formacion.presentation.logistica_partidas._limitar")
    def test_dos_creaciones_concurrentes_no_superan_20_partidas_del_propietario(
        self, limite
    ):
        if connection.vendor != "postgresql":
            self.skipTest(
                "La concurrencia del cupo exige bloqueos reales de PostgreSQL."
            )
        PartidaSimulador.objects.bulk_create(
            [
                PartidaSimulador(
                    unidad=self.unidad,
                    propietario=self.usuarios[0],
                    simulador="cerveza",
                    caso="cerveza-base",
                    nombre=f"Sala QA {i}",
                    version_motor=cerveza.VERSION,
                    estado=cerveza.crear_estado(),
                )
                for i in range(19)
            ]
        )
        barrera = Barrier(2)

        def crear(_):
            close_old_connections()
            try:
                cliente = Client()
                cliente.force_login(self.usuarios[0])
                barrera.wait(timeout=10)
                respuesta = cliente.post(
                    self.api, {"accion": "crear"}, content_type="application/json"
                )
                return respuesta.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            resultados = list(ejecutor.map(crear, range(2)))
        self.assertEqual(sorted(resultados), [201, 409])
        self.assertEqual(
            PartidaSimulador.objects.filter(
                propietario=self.usuarios[0], fase__in=["sala", "activa"]
            ).count(),
            20,
        )
