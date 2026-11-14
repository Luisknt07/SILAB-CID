"""Privacidad y proyección del seguimiento de un expediente presencial."""

import json
from datetime import time, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, RegistroParticipanteReserva, Reserva
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.formacion.models.partidas_simulador import PartidaSimulador
from apps.reservas.models.seguridad import RegistroIngreso
from tests.integration import test_logistica_operacion as fixtures


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.enlaces.append(dict(attrs))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class OperacionLogisticaSeguimientoTests(TestCase):
    # Comparte los datos sintéticos del panel sin heredar ni repetir sus pruebas.
    setUpTestData = classmethod(fixtures.OperacionLogisticaTests.setUpTestData.__func__)
    setUp = fixtures.OperacionLogisticaTests.setUp
    actividad = fixtures.OperacionLogisticaTests.actividad
    plan = fixtures.OperacionLogisticaTests.plan
    delegar = fixtures.OperacionLogisticaTests.delegar

    def reserva(self, actividad, numero=1, **datos):
        return Reserva.objects.create(
            laboratorio=datos.pop("laboratorio", self.unidad),
            actividad_catalogo=actividad,
            usuario=self.docente,
            fecha=timezone.localdate(),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo="QA-SEGUIMIENTO-" + str(numero),
            equipo_nombre="Maqueta sintética",
            estado=datos.pop("estado", "confirmada"),
            **datos,
        )

    def ejecucion(self, plan, **datos):
        return EjecucionPractica.objects.create(
            planificacion=plan,
            fecha_ejecucion=timezone.localdate(),
            resultado=datos.pop("resultado", "ejecutada"),
            estado=datos.pop("estado", "revision"),
            creado_por=self.docente,
            hora_inicio_real=time(8),
            hora_fin_real=time(10),
            cumplimiento_resultado="si",
            **datos,
        )

    def evidencia(self, ejecucion, numero=1, **datos):
        return EvidenciaPractica.objects.create(
            ejecucion=ejecucion,
            tipo=datos.pop("tipo", "bitacora"),
            archivo="practicas/evidencias/qa/RUTA-PRIVADA-" + str(numero) + ".csv",
            nombre_original="NOMBRE-PRIVADO-" + str(numero) + ".csv",
            extension="csv",
            tipo_contenido="text/csv",
            tamano=100,
            descripcion="DESCRIPCION-PRIVADA-" + str(numero),
            subido_por=self.docente,
            **datos,
        )

    @staticmethod
    def controles(response):
        return {control["id"]: control for control in response.context["controles"]}

    def consultar(self, actividad, plan, **parametros):
        return self.client.get(
            self.url,
            {"actividad": actividad.pk, "plan": plan.pk, **parametros},
        )

    def test_plan_privado_no_se_revela_por_conocer_su_identificador(self):
        actividad = self.actividad()
        privado = self.plan(actividad, 1, creado_por=self.admin)
        PlanificacionPractica.objects.filter(pk=privado.pk).update(
            tema="TEMA-PLAN-PRIVADO"
        )
        self.client.force_login(self.docente)
        response = self.consultar(actividad, privado)
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "TEMA-PLAN-PRIVADO", status_code=404)

    def test_plan_de_otra_unidad_otra_actividad_o_eliminado_devuelve404(self):
        actividad = self.actividad()
        otra_actividad = self.actividad(nombre="Actividad diferente")
        actividad_otra_unidad = self.actividad(unidad=self.otra)
        casos = (
            self.plan(otra_actividad, 1),
            self.plan(actividad_otra_unidad, 2, unidad=self.otra),
            self.plan(actividad, 3, eliminado_en=timezone.now()),
        )
        for plan in casos:
            with self.subTest(plan=plan.pk):
                self.assertEqual(self.consultar(actividad, plan).status_code, 404)

    def test_plan_sin_actividad_y_plan_sin_parametro_actividad_no_se_seleccionan(self):
        actividad = self.actividad()
        sin_actividad = self.plan(None, 1)
        con_actividad = self.plan(actividad, 2)
        self.assertEqual(self.consultar(actividad, sin_actividad).status_code, 404)
        self.assertEqual(
            self.client.get(self.url, {"plan": con_actividad.pk}).status_code, 404
        )
        self.assertEqual(
            self.client.get(self.url, {"plan": sin_actividad.pk}).status_code, 404
        )

    def test_identificador_malformado_o_inexistente_no_se_sustituye_por_otro_plan(self):
        actividad = self.actividad()
        self.plan(actividad, 1)
        for identificador in (
            "-1",
            "１２",
            "1.0",
            "1 OR 1=1",
            "9" * 11,
            "0",
            "9999999999",
            "<script>",
        ):
            with self.subTest(identificador=identificador):
                response = self.client.get(
                    self.url, {"actividad": actividad.pk, "plan": identificador}
                )
                self.assertEqual(response.status_code, 404)

    def test_seleccion_fuera_de_cinco_recientes_se_consulta_directamente(self):
        actividad = self.actividad()
        antiguo = self.plan(actividad, 1)
        PlanificacionPractica.objects.filter(pk=antiguo.pk).update(
            fecha=timezone.localdate() - timedelta(days=20)
        )
        recientes = [self.plan(actividad, numero) for numero in range(2, 8)]
        response = self.consultar(actividad, antiguo, caso="cd-pico", semilla=0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expediente"]["id"], antiguo.pk)
        self.assertEqual(response.context["plan_seleccionado"], antiguo.pk)
        self.assertEqual(len(response.context["planes"]), 5)
        self.assertNotIn(
            antiguo.pk, [plan["id"] for plan in response.context["planes"]]
        )
        self.assertTrue(
            {plan["id"] for plan in response.context["planes"]}.issubset(
                {plan.pk for plan in recientes}
            )
        )
        self.assertContains(response, antiguo.codigo)

    def test_sin_seleccion_otros_expedientes_validados_no_completan_controles(self):
        actividad = self.actividad()
        reserva = self.reserva(
            actividad, estado="completada", resultado_cierre="atendida"
        )
        plan = self.plan(actividad, 1, estado="aprobada", reserva=reserva)
        self.ejecucion(plan, estado="validada")
        response = self.client.get(self.url, {"actividad": actividad.pk})
        self.assertIsNone(response.context["expediente"])
        self.assertIsNone(response.context["plan_seleccionado"])
        controles = self.controles(response)
        self.assertEqual(controles["plan"]["estado"], "pendiente")
        self.assertEqual(controles["ejecucion"]["estado"], "pendiente")
        self.assertEqual(controles["reporte"]["estado"], "pendiente")

    def test_cierre_cancelado_o_reprogramado_es_documental_sin_uso_efectivo(self):
        actividad = self.actividad()
        for numero, resultado in enumerate(("cancelada", "reprogramada"), start=1):
            with self.subTest(resultado=resultado):
                reserva = self.reserva(
                    actividad,
                    numero,
                    estado="cancelada" if resultado == "cancelada" else "confirmada",
                )
                plan = self.plan(actividad, numero, estado="aprobada", reserva=reserva)
                self.ejecucion(
                    plan,
                    estado="validada",
                    resultado=resultado,
                    motivo="Motivo sintético de cierre",
                    estudiantes_asistentes=0,
                )
                response = self.consultar(actividad, plan)
                ejecucion = response.context["expediente"]["ejecucion"]
                self.assertEqual(ejecucion["resultado"], resultado)
                self.assertFalse(ejecucion["efectiva"])
                self.assertEqual(ejecucion["asistentes"], 0)
                controles = self.controles(response)
                self.assertEqual(controles["ejecucion"]["estado"], "verificado")
                self.assertEqual(controles["reporte"]["estado"], "registrado")
                self.assertIn("sin uso efectivo", controles["reporte"]["detalle"])
                self.assertEqual(response.context["expediente"]["ejecucion_url"], "")

    def test_solo_realizada_y_validada_se_muestra_como_efectiva(self):
        actividad = self.actividad()
        reserva = self.reserva(
            actividad, estado="completada", resultado_cierre="atendida"
        )
        plan = self.plan(actividad, 1, estado="aprobada", reserva=reserva)
        ejecucion = self.ejecucion(plan, estado="revision", estudiantes_asistentes=2)
        response = self.consultar(actividad, plan)
        self.assertFalse(response.context["expediente"]["ejecucion"]["efectiva"])
        self.assertEqual(self.controles(response)["reporte"]["estado"], "pendiente")
        ejecucion.estado = "validada"
        ejecucion.save(update_fields=["estado"])
        response = self.consultar(actividad, plan)
        self.assertTrue(response.context["expediente"]["ejecucion"]["efectiva"])
        self.assertEqual(self.controles(response)["reporte"]["estado"], "verificado")
        # Inicio o cierre registrado no se transforma en certificación de seguridad física.
        self.assertEqual(self.controles(response)["seguridad"]["estado"], "registrado")

    def test_evidencia_solo_agrega_conteos_sin_nombres_archivos_ni_json_operativo(self):
        actividad = self.actividad()
        plan = self.plan(
            actividad, 1, estado="aprobada", reserva=self.reserva(actividad)
        )
        ejecucion = self.ejecucion(
            plan, detalle_operativo={"PRIVADO-JSON-OPERATIVO": "No cargar"}
        )
        self.evidencia(ejecucion, 1)
        self.evidencia(ejecucion, 2)
        self.evidencia(ejecucion, 3, tipo="informe")
        with CaptureQueriesContext(connection) as sql:
            response = self.consultar(actividad, plan)
        resumen = response.context["expediente"]
        self.assertEqual(resumen["evidencias_total"], 3)
        self.assertEqual(
            {item["titulo"]: item["total"] for item in resumen["evidencias"]},
            {"Bitácora": 2, "Informe de estudiante": 1},
        )
        serializado = json.dumps(resumen, default=str)
        for privado in (
            "RUTA-PRIVADA",
            "NOMBRE-PRIVADO",
            "DESCRIPCION-PRIVADA",
            "PRIVADO-JSON-OPERATIVO",
        ):
            self.assertNotIn(privado, serializado)
            self.assertNotContains(response, privado)
        consultas = [
            item["sql"]
            for item in sql
            if 'FROM "webcitt_evidenciapractica"' in item["sql"]
        ]
        self.assertEqual(len(consultas), 1)
        self.assertIn("COUNT(", consultas[0].upper())
        for campo in ("archivo", "nombre_original", "descripcion"):
            self.assertNotIn('"' + campo + '"', consultas[0])
        consultas_planes = [
            item["sql"]
            for item in sql
            if 'FROM "webcitt_planificacionpractica"' in item["sql"]
        ]
        self.assertTrue(consultas_planes)
        self.assertTrue(
            all('"detalle_operativo"' not in consulta for consulta in consultas_planes)
        )

    def test_cinco_planes_con_ejecuciones_no_agregan_consultas_por_fila(self):
        actividad = self.actividad()
        seleccionado = self.plan(
            actividad, 1, estado="aprobada", reserva=self.reserva(actividad)
        )
        ejecucion = self.ejecucion(seleccionado)
        self.evidencia(ejecucion)
        self.consultar(actividad, seleccionado)
        with CaptureQueriesContext(connection) as base:
            self.consultar(actividad, seleccionado)
        for numero in range(2, 6):
            plan = self.plan(actividad, numero)
            self.evidencia(self.ejecucion(plan), numero)
        with CaptureQueriesContext(connection) as completo:
            response = self.consultar(actividad, seleccionado)
        self.assertEqual(len(response.context["planes"]), 5)
        self.assertEqual(len(completo), len(base))
        self.assertEqual(response.context["expediente"]["evidencias_total"], 1)
        consultas_plan = [
            item["sql"]
            for item in completo
            if 'FROM "webcitt_planificacionpractica"' in item["sql"]
        ]
        self.assertEqual(len(consultas_plan), 2)
        self.assertTrue(any("LIMIT 5" in consulta for consulta in consultas_plan))
        self.assertTrue(any("LIMIT 1" in consulta for consulta in consultas_plan))
        self.assertEqual(
            sum('FROM "webcitt_evidenciapractica"' in item["sql"] for item in completo),
            1,
        )

    def test_buscar_conserva_seleccion_y_cambiar_actividad_descarta_plan(self):
        actividad = self.actividad(nombre="Distribución")
        otra_actividad = self.actividad(nombre="Transporte")
        plan = self.plan(actividad, 1)
        response = self.consultar(
            actividad, plan, q="Distribución", caso="cd-falla", semilla=0
        )
        self.assertEqual(response.context["expediente"]["id"], plan.pk)
        self.assertContains(response, 'name="plan" value="' + str(plan.pk) + '"')
        response = self.consultar(actividad, plan, caso="cd-falla", semilla=0)
        otra_fila = next(
            item
            for item in response.context["actividades"]
            if item["id"] == otra_actividad.pk
        )
        parametros = parse_qs(urlparse(otra_fila["url"]).query)
        self.assertEqual(parametros["actividad"], [str(otra_actividad.pk)])
        self.assertEqual(parametros["semilla"], ["0"])
        self.assertEqual(parametros["caso"], ["cd-falla"])
        self.assertNotIn("plan", parametros)
        siguiente = self.client.get(otra_fila["url"])
        self.assertEqual(siguiente.status_code, 200)
        self.assertIsNone(siguiente.context["expediente"])

    def test_seleccion_url_tiene_un_fragmento_y_no_abre_portal_en_el_visor(self):
        actividad = self.actividad()
        plan = self.plan(actividad, 1)
        response = self.consultar(actividad, plan)
        enlace = response.context["planes"][0]["seleccion_url"]
        self.assertEqual(urlparse(enlace).fragment, "expediente")
        parser = Enlaces()
        parser.feed(response.content.decode())
        seleccion = next(
            attrs for attrs in parser.enlaces if attrs.get("aria-current") == "true"
        )
        self.assertEqual(urlparse(seleccion["href"]).fragment, "expediente")
        self.assertNotIn("target", seleccion)
        expediente = [
            attrs
            for attrs in parser.enlaces
            if attrs.get("href") == response.context["expediente"]["url"]
        ]
        self.assertTrue(expediente)
        self.assertTrue(all(attrs.get("target") == "_top" for attrs in expediente))

    def test_ejecucion_eliminada_no_se_proyecta_ni_ofrece_editarla(self):
        actividad = self.actividad()
        plan = self.plan(
            actividad, 1, estado="aprobada", reserva=self.reserva(actividad)
        )
        ejecucion = self.ejecucion(plan, eliminado_en=timezone.now())
        self.evidencia(ejecucion)
        response = self.consultar(actividad, plan)
        resumen = response.context["expediente"]
        self.assertIsNone(resumen["ejecucion"])
        self.assertEqual(resumen["ejecucion_url"], "")
        self.assertEqual(resumen["evidencias_total"], 0)
        self.assertEqual(resumen["evidencias"], [])
        self.assertEqual(self.controles(response)["ejecucion"]["estado"], "pendiente")
        self.assertNotContains(response, "Registrar o completar FT03")

    def test_participante_autorizado_consulta_sesion_sin_editar_ejecucion_ajena(self):
        actividad = self.actividad()
        actividad.participantes_autorizados.add(self.participante)
        plan = self.plan(
            actividad, 1, estado="aprobada", reserva=self.reserva(actividad)
        )
        self.client.force_login(self.participante)
        response = self.consultar(actividad, plan)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expediente"]["id"], plan.pk)
        self.assertEqual(response.context["expediente"]["ejecucion_url"], "")
        self.assertEqual(response.context["indicadores"], [])
        self.assertNotContains(response, "Registrar o completar FT03")

    def test_guia_publicada_de_actividad_no_completa_plan_que_no_la_vincula(self):
        actividad = self.actividad()
        publicada = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía publicada",
            es_estructurada=True,
            estado_publicacion="publicada",
            subido_por=self.docente,
        )
        plan = self.plan(actividad, 1, requiere_guia=True)
        response = self.consultar(actividad, plan)
        self.assertEqual(response.context["guia_publicada"]["id"], publicada.pk)
        self.assertIsNone(response.context["expediente"]["guia"])
        self.assertEqual(self.controles(response)["guia"]["estado"], "pendiente")

    def test_leer_seleccion_no_crea_auditoria_ejecucion_reserva_o_uso_fisico(self):
        actividad = self.actividad()
        plan = self.plan(actividad, 1)
        modelos = (
            CatalogoActividadReserva,
            PlanificacionPractica,
            EjecucionPractica,
            EvidenciaPractica,
            Reserva,
            RegistroAuditoriaUnidad,
            RegistroIngreso,
            RegistroParticipanteReserva,
            PartidaSimulador,
        )
        antes = {modelo.__name__: modelo.objects.count() for modelo in modelos}
        with CaptureQueriesContext(connection) as sql:
            response = self.consultar(actividad, plan, caso="cd-normal", semilla=0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {modelo.__name__: modelo.objects.count() for modelo in modelos}, antes
        )
        self.assertFalse(
            any(
                consulta["sql"]
                .lstrip()
                .upper()
                .startswith(("INSERT", "UPDATE", "DELETE"))
                for consulta in sql
            )
        )
        self.assertFalse(
            any(
                "webcitt_partidasimulador" in consulta["sql"]
                or "webcitt_eventopartida" in consulta["sql"]
                for consulta in sql
            )
        )
