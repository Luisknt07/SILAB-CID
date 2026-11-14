"""Comparaciones privadas, datos públicos y actualizaciones de reglas de CD.

Pruebas adversariales independientes: sólo usan la base aislada del runner.
Las formas históricas se simulan con JSON válido de esquema anterior; nunca
se modifican partidas institucionales ni se envían órdenes a equipos.
"""

from copy import deepcopy
from datetime import date
import re
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.laboratorios.operacion.presentation.logistica_distribucion import _csv
from apps.formacion.models.partidas_simulador import EventoPartida, PartidaSimulador, ParticipantePartida
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_logistica_partidas import DatosPartidas


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DistribucionAdversarialTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        limites = patch("apps.formacion.presentation.logistica_partidas._limitar")
        limites.start()
        self.addCleanup(limites.stop)
        self.hub = reverse("logistica_distribucion", args=[self.unidad.slug])

    def final(self, propietario=0, caso="cd-normal", semilla=42, unidad=None):
        estado = motor.crear_estado(caso, semilla)
        for decision in motor.referencia(caso, semilla)["decisiones"]:
            estado = motor.actuar(estado, decision)
        partida = PartidaSimulador.objects.create(
            unidad=unidad or self.unidad,
            propietario=self.usuarios[propietario],
            simulador="operaciones",
            caso=caso,
            semilla=semilla,
            version_motor=motor.VERSION,
            version_caso=motor.VERSION_CASO,
            nombre="Práctica privada " + str(propietario),
            estado=estado,
            observaciones={"operador": motor.observacion(estado)},
            resultado=motor.resultado(estado),
            fase="terminada",
            revision=1,
        )
        ParticipantePartida.objects.create(
            partida=partida, usuario=self.usuarios[propietario], rol="operador"
        )
        return partida

    def comparar(self, *partidas, cliente=0, **parametros):
        return self.clientes[cliente].get(
            self.ops,
            {"comparar": ",".join(str(p.pk) for p in partidas), **parametros},
        )

    def test_anonimo_no_consulta_comparaciones_ni_recibe_identidades(self):
        propias = [self.final(), self.final()]
        respuesta = Client().get(
            self.ops, {"comparar": ",".join(str(p.pk) for p in propias)}
        )
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn(str(propias[0].pk), respuesta.content.decode())
        self.assertNotIn("sesiones", respuesta.json())

    def test_otra_persona_no_compara_partida_ajena_incluso_siendo_superusuario(self):
        propia, ajena = self.final(), self.final(propietario=1)
        ajena.nombre = "CANARIO_PRIVADO_NO_PUBLICAR"
        ajena.save(update_fields=["nombre"])
        for superusuario in (False, True):
            with self.subTest(superusuario=superusuario):
                self.usuarios[0].is_superuser = superusuario
                self.usuarios[0].is_staff = superusuario
                self.usuarios[0].save(update_fields=["is_superuser", "is_staff"])
                respuesta = self.comparar(propia, ajena)
                self.assertEqual(respuesta.status_code, 404)
                self.assertNotIn("CANARIO_PRIVADO", respuesta.content.decode())
                self.assertEqual(set(respuesta.json()), {"error"})

    def test_propietario_no_compara_datos_de_otro_dominio_unidad_o_caso(self):
        propia = self.final()
        otra = Unidad.objects.create(
            nombre="Unidad QA independiente",
            slug="otra-unidad-distribucion-qa",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
        )
        ajena_unidad = self.final(unidad=otra)
        self.assertEqual(self.comparar(propia, ajena_unidad).status_code, 404)
        otra_familia = self.final()
        for campo, valor in (
            ("simulador", "cerveza"),
            ("caso", "almacen-trazabilidad"),
        ):
            with self.subTest(campo=campo):
                otra_familia.simulador, otra_familia.caso = "operaciones", "cd-normal"
                setattr(otra_familia, campo, valor)
                otra_familia.save(update_fields=["simulador", "caso"])
                self.assertEqual(self.comparar(propia, otra_familia).status_code, 404)

    def test_comparar_proyecta_solo_resultados_acotados_sin_eventos_ni_estados(self):
        primeras = [self.final(), self.final(caso="cd-falla")]
        for p in primeras:
            p.estado["canario_privado"] = "NO_CARGAR_ESTADO_CRUDO"
            p.observaciones["canario_privado"] = "NO_CARGAR_OBSERVACIONES"
            p.save(update_fields=["estado", "observaciones"])
            EventoPartida.objects.create(
                partida=p, revision=1, tipo="qa", datos={"canario": "NO_CARGAR_EVENTOS"}
            )
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.comparar(*primeras)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["tipo"], "contingencias")
        self.assertNotIn("NO_CARGAR", respuesta.content.decode())
        self.assertEqual(
            [s["id"] for s in respuesta.json()["sesiones"]],
            [str(p.pk) for p in primeras],
        )
        self.assertLessEqual(len(consultas), 10)
        sql_partidas = [
            q["sql"] for q in consultas if PartidaSimulador._meta.db_table in q["sql"]
        ]
        self.assertEqual(len(sql_partidas), 1)
        proyeccion = sql_partidas[0].split(" FROM ", 1)[0]
        for campo in ("estado", "observaciones"):
            self.assertNotRegex(
                proyeccion,
                r'"'
                + re.escape(PartidaSimulador._meta.db_table)
                + r'"\."'
                + campo
                + r'"',
            )
        self.assertFalse(
            any(EventoPartida._meta.db_table in q["sql"] for q in consultas)
        )
        self.assertFalse(any("COUNT(" in q["sql"].upper() for q in consultas))
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertIn("Cookie", {v.strip() for v in respuesta["Vary"].split(",")})

    def test_comparacion_exige_dos_o_tres_uuid_distintos_y_conserva_orden(self):
        propias = [self.final(), self.final(), self.final()]
        valores = [
            "",
            "no-es-uuid",
            str(propias[0].pk),
            ",".join([str(propias[0].pk)] * 2),
            ",".join(str(p.pk) for p in propias + propias[:1]),
        ]
        for valor in valores[1:]:
            with self.subTest(valor=valor):
                respuesta = self.clientes[0].get(self.ops, {"comparar": valor})
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(set(respuesta.json()), {"error"})
        respuesta = self.comparar(*reversed(propias))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [s["id"] for s in respuesta.json()["sesiones"]],
            [str(p.pk) for p in reversed(propias)],
        )
        self.assertTrue(all(m["deltas"][0] == 0 for m in respuesta.json()["metricas"]))

    def test_comparacion_rechaza_fases_semillas_o_versiones_incompatibles(self):
        primera, segunda = self.final(), self.final()
        cambios = [
            {"fase": "activa"},
            {"semilla": 43},
            {"version_motor": "0.9.0"},
            {"version_caso": "0.9.0"},
            {"resultado": {**segunda.resultado, "version_dataset": "0.9.0"}},
        ]
        original = {
            k: deepcopy(getattr(segunda, k)) for cambio in cambios for k in cambio
        }
        for cambio in cambios:
            with self.subTest(cambio=list(cambio)):
                PartidaSimulador.objects.filter(pk=segunda.pk).update(
                    **{**original, **cambio}
                )
                respuesta = self.comparar(primera, segunda)
                self.assertEqual(respuesta.status_code, 409)
                self.assertEqual(set(respuesta.json()), {"error"})
        PartidaSimulador.objects.filter(pk=segunda.pk).update(**original)
        self.assertEqual(
            self.comparar(primera, segunda, formato="xml").status_code, 400
        )

    def test_resultados_historicos_con_formas_distintas_rechazan_409_sin_500(self):
        primera, segunda = self.final(), self.final()
        tipos = [
            [],
            "esquema previo",
            42,
            {"version_dataset": "1.0.0", "kpis": None},
            {"version_dataset": [], "kpis": []},
            {
                "version_dataset": "1.0.0",
                "kpis": [{"id": [], "valor": 1, "unidad": "m"}],
            },
            {
                "version_dataset": "1.0.0",
                "kpis": [{"id": "minutos", "valor": 1, "unidad": []}],
            },
        ]
        cliente = Client(raise_request_exception=False)
        cliente.force_login(self.usuarios[0])
        for resultado in tipos:
            with self.subTest(resultado=resultado):
                PartidaSimulador.objects.filter(pk=segunda.pk).update(
                    resultado=resultado
                )
                respuesta = cliente.get(
                    self.ops, {"comparar": str(primera.pk) + "," + str(segunda.pk)}
                )
                self.assertEqual(respuesta.status_code, 409)
                self.assertEqual(set(respuesta.json()), {"error"})

    def test_comparacion_historica_compatible_no_reinterpreta_motor_actual(self):
        propias = [self.final(), self.final()]
        for partida in propias:
            resultado = deepcopy(partida.resultado)
            resultado.update(
                version_motor="0.9.0", version_caso="0.9.0", version_dataset="0.9.0"
            )
            PartidaSimulador.objects.filter(pk=partida.pk).update(
                version_motor="0.9.0",
                version_caso="0.9.0",
                resultado=resultado,
                estado={"esquema_antiguo": True},
            )
        with (
            patch.object(
                motor, "crear_estado", side_effect=AssertionError("No recrear historia")
            ),
            patch.object(
                motor, "resultado", side_effect=AssertionError("No recalcular historia")
            ),
        ):
            respuesta = self.comparar(*propias)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            {s["version_dataset"] for s in respuesta.json()["sesiones"]}, {"0.9.0"}
        )

    def test_crear_guarda_version_caso_del_motor_y_no_default_historico(self):
        with patch.object(motor, "VERSION_CASO", "2.0.0"):
            sesion = self.post(
                self.clientes[0],
                {"accion": "crear", "caso": "cd-normal"},
                self.ops,
                201,
            )
            self.assertEqual(sesion["version_caso"], "2.0.0")
            self.assertFalse(sesion["solo_lectura"])
            partida = PartidaSimulador.objects.get(pk=sesion["id"])
            self.assertEqual(partida.version_caso, partida.estado["version_caso"])

    def test_dataset_historico_es_solo_lectura_antes_de_interpretar_su_estado(self):
        sesion = self.post(
            self.clientes[0], {"accion": "crear", "caso": "cd-normal"}, self.ops, 201
        )
        partida = PartidaSimulador.objects.get(pk=sesion["id"])
        observaciones = deepcopy(partida.observaciones)
        observaciones["operador"]["version_dataset"] = "0.9.0"
        PartidaSimulador.objects.filter(pk=partida.pk).update(
            estado={"version_dataset": "0.9.0", "esquema_antiguo": True},
            observaciones=observaciones,
        )
        with patch.object(
            motor, "observacion", side_effect=AssertionError("No reinterpretar")
        ):
            respuesta = self.clientes[0].get(self.ops, {"sesion": sesion["id"]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["sesion"]["solo_lectura"])
        self.post(
            self.clientes[0],
            {
                "accion": "actuar",
                "sesion": sesion["id"],
                "revision": sesion["revision"],
                "decision": {"accion": "inspeccionar", "objeto": "lote-a-1"},
            },
            self.ops,
            409,
        )
        partida.refresh_from_db()
        self.assertEqual(partida.revision, sesion["revision"])
        self.assertEqual(
            partida.estado, {"version_dataset": "0.9.0", "esquema_antiguo": True}
        )

    def test_cambio_de_reglas_invalida_etag_aunque_revision_no_cambie(self):
        sesion = self.post(
            self.clientes[0], {"accion": "crear", "caso": "cd-normal"}, self.ops, 201
        )
        primera = self.clientes[0].get(self.ops, {"sesion": sesion["id"]})
        with patch.object(motor, "DATASET_VERSION", "2.0.0"):
            nueva = self.clientes[0].get(
                self.ops, {"sesion": sesion["id"]}, HTTP_IF_NONE_MATCH=primera["ETag"]
            )
        self.assertEqual(nueva.status_code, 200)
        self.assertNotEqual(nueva["ETag"], primera["ETag"])
        self.assertTrue(nueva.json()["sesion"]["solo_lectura"])

    def test_fallo_de_motor_nuevo_revierte_estado_revision_y_eventos(self):
        sesion = self.post(
            self.clientes[0], {"accion": "crear", "caso": "cd-normal"}, self.ops, 201
        )
        antes = PartidaSimulador.objects.get(pk=sesion["id"])
        with patch.object(
            motor, "actuar", side_effect=ValueError("Error QA controlado")
        ):
            self.post(
                self.clientes[0],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": {"accion": "inspeccionar", "objeto": "lote-a-1"},
                },
                self.ops,
                400,
            )
        despues = PartidaSimulador.objects.get(pk=sesion["id"])
        self.assertEqual(despues.estado, antes.estado)
        self.assertEqual(despues.observaciones, antes.observaciones)
        self.assertEqual(despues.revision, antes.revision)
        self.assertEqual(despues.eventos.count(), 1)

    def test_datasets_publicos_no_consultan_partidas_ni_revelan_hallazgos(self):
        for caso in motor.CASOS:
            for tabla in ("productos", "ubicaciones", "pedidos", "recursos"):
                with (
                    self.subTest(caso=caso, tabla=tabla),
                    CaptureQueriesContext(connection) as consultas,
                ):
                    respuesta = Client().get(
                        self.hub, {"caso": caso, "dataset": tabla, "semilla": 42}
                    )
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta["Content-Type"].startswith("text/csv"))
                self.assertNotIn("defectuosas", respuesta.content.decode("utf-8"))
                self.assertFalse(
                    any(
                        PartidaSimulador._meta.db_table in q["sql"]
                        or EventoPartida._meta.db_table in q["sql"]
                        for q in consultas
                    )
                )
                self.assertFalse(
                    any(
                        q["sql"]
                        .lstrip()
                        .upper()
                        .startswith(("UPDATE", "INSERT", "DELETE"))
                        for q in consultas
                    )
                )
        for tabla in ("estado", "eventos", "lotes", "resultados", "../recursos"):
            respuesta = Client().get(self.hub, {"dataset": tabla})
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(set(respuesta.json()), {"error"})
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_familia_filtra_sin_exponer_otras_practicas_y_no_carga_json_pesado(self):
        propia = self.final()
        self.final(propietario=1)
        ajena_familia = self.final()
        PartidaSimulador.objects.filter(pk=ajena_familia.pk).update(
            caso="fabrica-flujo"
        )
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.clientes[0].get(
                self.ops, {"familia": "centro-distribucion"}
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [s["id"] for s in respuesta.json()["sesiones"]], [str(propia.pk)]
        )
        selects = [
            q["sql"].split(" FROM ", 1)[0]
            for q in consultas
            if q["sql"].lstrip().upper().startswith("SELECT")
        ]
        for campo in ("estado", "observaciones", "resultado"):
            patron = (
                r'"'
                + re.escape(PartidaSimulador._meta.db_table)
                + r'"\."'
                + campo
                + r'"(?!\s*(?:->|#>))'
            )
            self.assertFalse(any(re.search(patron, sql) for sql in selects), campo)
        self.assertFalse(any("COUNT(" in q["sql"].upper() for q in consultas))

    def test_csv_neutraliza_formulas_y_preserva_tablas_con_newlines(self):
        valores = ["=1+1", " +1", "\t@SUM(1)", "-1+2", "normal", "línea 1\nlínea 2"]
        respuesta = _csv("qa.csv", ["valor"], [[v] for v in valores])
        import csv
        import io

        filas = list(csv.reader(io.StringIO(respuesta.content.decode("utf-8-sig"))))
        self.assertEqual(filas[0], ["valor"])
        self.assertEqual([f[0] for f in filas[1:5]], ["'" + v for v in valores[:4]])
        self.assertEqual([f[0] for f in filas[5:]], valores[4:])
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
