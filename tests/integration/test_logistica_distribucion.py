"""El centro CD integra datos públicos y evidencia privada sin mutar otra gestión."""

from copy import deepcopy
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.laboratorios.operacion.presentation import logistica_motores as registro
from apps.laboratorios.operacion.presentation.logistica_distribucion import _celda
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.partidas_simulador import PartidaSimulador, ParticipantePartida

from tests.integration.test_logistica_partidas import DatosPartidas


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DistribucionTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        self.limites = patch("apps.formacion.presentation.logistica_partidas._limitar")
        self.limites.start()
        self.addCleanup(self.limites.stop)
        self.hub = reverse("logistica_distribucion", args=[SLUG_LOGISTICA])
        self.escena = reverse("logistica_operaciones", args=[SLUG_LOGISTICA])

    def final(self, caso="cd-normal", semilla=42, usuario=0):
        estado = motor.crear_estado(caso, semilla)
        for decision in motor.referencia(caso, semilla)["decisiones"]:
            estado = motor.actuar(estado, decision)
        partida = PartidaSimulador.objects.create(
            unidad=self.unidad,
            propietario=self.usuarios[usuario],
            simulador="operaciones",
            caso=caso,
            nombre="Entrega <img src=x onerror=alert(1)>",
            semilla=semilla,
            version_motor=motor.VERSION,
            version_caso=motor.VERSION_CASO,
            estado=estado,
            observaciones={"operador": motor.observacion(estado)},
            resultado=motor.resultado(estado),
            fase="terminada",
        )
        ParticipantePartida.objects.create(
            partida=partida, usuario=self.usuarios[usuario], rol="operador"
        )
        return partida

    def comparar(self, *partidas, cliente=None, **params):
        return (cliente or self.clientes[0]).get(
            self.ops, {"comparar": ",".join(str(p.pk) for p in partidas), **params}
        )

    def test_guia_y_tres_previsualizaciones_publicas_coherentes_sin_partidas(self):
        for caso in motor.CASOS:
            for url in (self.hub, self.escena):
                with (
                    self.subTest(caso=caso, url=url),
                    CaptureQueriesContext(connection) as sql,
                ):
                    response = Client().get(url, {"caso": caso, "semilla": 73})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
                self.assertFalse(
                    any("webcitt_partidasimulador" in q["sql"] for q in sql)
                )
                self.assertFalse(
                    any(
                        q["sql"]
                        .lstrip()
                        .upper()
                        .startswith(("INSERT", "UPDATE", "DELETE"))
                        for q in sql
                    )
                )
                if url == self.escena:
                    vista = response.context["datos_iniciales"]["estado"]
                    self.assertEqual((vista["caso"], vista["semilla"]), (caso, 73))
                    self.assertContains(response, 'value="73"')
                    self.assertContains(response, 'semilla=73')
                else:
                    self.assertContains(response, "Bitácora y reconstrucción")
                    self.assertContains(response, "Descriptores de evaluación")
                    self.assertContains(response, "Asignar ubicaciones")
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_entradas_csv_tienen_version_semilla_y_no_hallazgos_ocultos(self):
        for caso in motor.CASOS:
            for tabla in ("productos", "ubicaciones", "pedidos", "recursos"):
                with self.subTest(caso=caso, tabla=tabla):
                    response = Client().get(
                        self.hub, {"caso": caso, "semilla": 11, "dataset": tabla}
                    )
                    self.assertEqual(response.status_code, 200)
                    texto = response.content.decode("utf-8-sig")
                    self.assertTrue(texto.startswith("caso,semilla,version_dataset,"))
                    self.assertIn(caso + ",11,1.0.0,", texto)
                    self.assertNotIn("defectuosas", texto)
                    self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(
            Client().get(self.hub, {"dataset": "../../estado"}).status_code, 400
        )

    def test_semilla_invalida_es_estable_y_no_rompe_guia_o_escena(self):
        for semilla in ("abc", "-1", "2147483648", "", "<script>"):
            for url in (self.hub, self.escena):
                response = self.client.get(
                    url, {"semilla": semilla, "caso": "cd-normal"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context["semilla"]
                    if url == self.hub
                    else response.context["semilla_inicial"],
                    42,
                )

    def test_seccion_oculta_impide_guia_y_csv(self):
        AjusteSeccionPlanta.objects.create(
            unidad=self.unidad, numero="4.4", oculta=True
        )
        for params in ({}, {"dataset": "productos"}):
            self.assertEqual(self.client.get(self.hub, params).status_code, 404)

    def test_registro_no_modifica_seis_motores_anteriores(self):
        from apps.laboratorios.operacion.presentation import logistica_operaciones_motor as anterior

        self.assertEqual(len(registro.catalogo()), 9)
        for caso in anterior.CASOS:
            self.assertEqual(
                registro.crear_estado(caso, 11), anterior.crear_estado(caso, 11)
            )
            self.assertEqual(registro.version(caso), anterior.VERSION)
        self.assertFalse(registro.vigente("no-existe", "1.0.0", "1.0.0"))
        self.assertFalse(registro.vigente("cd-normal", "anterior", "1.0.0"))

    def test_flujo_http_completo_guardado_recuperacion_y_verificacion(self):
        sesion = self.post(
            self.clientes[0],
            {"accion": "crear", "caso": "cd-falla", "semilla": 42},
            url=self.ops,
            esperado=201,
        )
        self.assertFalse(sesion["solo_lectura"])
        for decision in motor.referencia("cd-falla", 42)["decisiones"]:
            sesion = self.post(
                self.clientes[0],
                {
                    "accion": "actuar",
                    "sesion": sesion["id"],
                    "revision": sesion["revision"],
                    "decision": decision,
                },
                url=self.ops,
            )
        self.assertEqual(sesion["fase"], "terminada")
        self.assertEqual(sesion["resultado"]["puntaje"], 100)
        nuevo = Client()
        nuevo.force_login(self.usuarios[0])
        recuperada = self.get(nuevo, sesion, url=self.ops)["sesion"]
        self.assertEqual(recuperada["resultado"], sesion["resultado"])
        self.assertTrue(
            self.get(nuevo, sesion, url=self.ops, verificar=1)["verificada"]
        )
        evidencia = self.get(nuevo, sesion, url=self.ops, exportar=1)
        self.assertEqual(evidencia["estado_final"]["caso"], "cd-falla")
        self.assertTrue(
            all(b["diferencia"] == 0 for b in evidencia["resultado"]["balances"])
        )

    def test_crear_tres_casos_guarda_su_version_y_vista(self):
        for caso in motor.CASOS:
            sesion = self.post(
                self.clientes[0],
                {"accion": "crear", "caso": caso, "semilla": 0},
                url=self.ops,
                esperado=201,
            )
            self.assertEqual(sesion["estado"]["version_dataset"], motor.DATASET_VERSION)
            self.assertEqual(sesion["estado"]["semilla"], 0)
            self.assertEqual(sesion["version_motor"], registro.version(caso))

    def test_comparar_estrategias_consulta_solo_resultados_acotados(self):
        uno, dos = self.final(), self.final()
        with CaptureQueriesContext(connection) as sql:
            response = self.comparar(uno, dos)
        self.assertEqual(response.status_code, 200, response.content[:1000])
        data = response.json()
        self.assertEqual(data["tipo"], "estrategias")
        self.assertEqual(
            [s["id"] for s in data["sesiones"]], [str(uno.pk), str(dos.pk)]
        )
        self.assertTrue(
            all(all(delta == 0 for delta in m["deltas"]) for m in data["metricas"])
        )
        consultas = [q["sql"] for q in sql if "webcitt_partidasimulador" in q["sql"]]
        self.assertEqual(len(consultas), 1)
        self.assertNotIn('"estado"', consultas[0])
        self.assertNotIn('"observaciones"', consultas[0])
        self.assertNotIn("webcitt_eventopartida", " ".join(q["sql"] for q in sql))
        self.assertNotIn("estado_final", data)

    def test_comparar_variantes_separa_condiciones_y_preserva_orden(self):
        uno, dos, tres = self.final(), self.final("cd-pico"), self.final("cd-falla")
        data = self.comparar(tres, uno, dos).json()
        self.assertEqual(data["tipo"], "contingencias")
        self.assertEqual(data["sesiones"][0]["id"], str(tres.pk))
        self.assertTrue(any("no atribuyas" in aviso for aviso in data["advertencias"]))
        minutos = next(m for m in data["metricas"] if m["id"] == "minutos")
        self.assertEqual(minutos["valores"], [132, 118, 139])
        self.assertEqual(minutos["deltas"], [0, -14, 7])

    def test_comparacion_no_admite_datos_de_otro_usuario_ni_anonimos(self):
        uno, otro = self.final(), self.final(usuario=1)
        self.assertEqual(self.comparar(uno, otro).status_code, 404)
        self.assertEqual(self.comparar(uno, otro, cliente=Client()).status_code, 401)

    def test_comparacion_exige_misma_semilla_y_versiones(self):
        uno, dos = self.final(), self.final(semilla=73)
        self.assertEqual(self.comparar(uno, dos).status_code, 409)
        dos.semilla = 42
        dos.version_motor = "0.9"
        dos.save(update_fields=["semilla", "version_motor"])
        self.assertEqual(self.comparar(uno, dos).status_code, 409)
        dos.version_motor = uno.version_motor
        dos.resultado = deepcopy(dos.resultado)
        dos.resultado["version_dataset"] = "0.9"
        dos.save(update_fields=["version_motor", "resultado"])
        self.assertEqual(self.comparar(uno, dos).status_code, 409)

    def test_comparacion_rechaza_duplicados_lote_ilimitado_y_activa(self):
        uno, dos = self.final(), self.final()
        self.assertEqual(self.comparar(uno, uno).status_code, 400)
        self.assertEqual(self.comparar(uno).status_code, 400)
        self.assertEqual(self.comparar(uno, dos, uno, dos).status_code, 400)
        self.assertEqual(
            self.clientes[0].get(self.ops, {"comparar": "no,uuid"}).status_code, 400
        )
        dos.fase = "activa"
        dos.save(update_fields=["fase"])
        self.assertEqual(self.comparar(uno, dos).status_code, 409)

    def test_resultado_historico_compara_sin_reinterpretar_motor(self):
        uno, dos = self.final(), self.final()
        for partida in (uno, dos):
            partida.version_motor = "0.9"
            partida.resultado["version_motor"] = "0.9"
            partida.save(update_fields=["version_motor", "resultado"])
        with (
            patch.object(
                motor,
                "resultado",
                side_effect=AssertionError("No recalcular históricos"),
            ),
            patch.object(motor, "actuar", side_effect=AssertionError("No ejecutar")),
        ):
            response = self.comparar(uno, dos)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sesiones"][0]["version_motor"], "0.9")

    def test_comparacion_csv_y_campos_textuales_no_ejecutan_formulas(self):
        uno, dos = self.final(), self.final("cd-pico")
        response = self.comparar(uno, dos, formato="csv")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.content.decode("utf-8-sig").startswith(
                "tipo_comparacion,practica,caso,semilla,version_motor"
            )
        )
        self.assertEqual(self.comparar(uno, dos, formato="html").status_code, 400)
        for value in ("=1+1", " +SUM(A1)", "@comando", "-formula"):
            self.assertTrue(_celda(value).startswith("'"))
        self.assertEqual(_celda(-14), -14)

    def test_listado_filtra_familia_sin_cargar_estados_y_muestra_semilla(self):
        uno = self.final()
        self.post(
            self.clientes[0],
            {"accion": "crear", "caso": "ia-pronostico"},
            url=self.ops,
            esperado=201,
        )
        response = self.clientes[0].get(self.ops, {"familia": "centro-distribucion"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["id"] for s in response.json()["sesiones"]], [str(uno.pk)])
        self.assertEqual(response.json()["sesiones"][0]["semilla"], 42)
        self.assertEqual(
            self.clientes[0].get(self.ops, {"familia": "otro"}).status_code, 400
        )

    def test_menu_incluye_guia_sin_consultar_partidas(self):
        with CaptureQueriesContext(connection) as sql:
            response = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(response, self.hub)
        self.assertFalse(any("webcitt_partidasimulador" in q["sql"] for q in sql))

    def test_api_no_disponible_entrega_json_con_cabeceras_privadas(self):
        AjusteSeccionPlanta.objects.create(
            unidad=self.unidad, numero="4.4", oculta=True
        )
        for url in (self.api, self.ops):
            response = self.clientes[0].get(url)
            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.json())
            self.assertEqual(response["Cache-Control"], "private, no-store")
        AjusteSeccionPlanta.objects.filter(unidad=self.unidad).delete()
        response = Client().get(self.ops)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_comparacion_no_mezcla_metadata_y_resultado_incoherentes(self):
        uno, dos = self.final(), self.final()
        original = deepcopy(dos.resultado)
        for campo, valor in (
            ("caso", "cd-pico"),
            ("semilla", 73),
            ("familia", "otra"),
            ("puntaje", -1),
        ):
            dos.resultado = {**deepcopy(original), campo: valor}
            dos.save(update_fields=["resultado"])
            self.assertEqual(self.comparar(uno, dos).status_code, 409)
