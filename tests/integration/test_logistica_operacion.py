"""Aislamiento, permisos y consultas del bloque presencial logístico."""

from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.roles import MODULOS_OPERATIVOS
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, RegistroParticipanteReserva, Reserva
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.formacion.models.partidas_simulador import PartidaSimulador
from apps.reservas.models.seguridad import RegistroIngreso, RequisitoAcceso
from apps.gestion_unidades.models.espacios import ResponsableUnidad, EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import verificar_pertenencia


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class OperacionLogisticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("cd-admin", password="solo-prueba")
        cls.docente = User.objects.create_user("cd-docente", password="solo-prueba")
        cls.participante = User.objects.create_user(
            "cd-participante", password="solo-prueba"
        )
        cls.ajeno = User.objects.create_user("cd-ajeno", password="solo-prueba")
        cls.delegado = User.objects.create_user("cd-delegado", password="solo-prueba")
        cls.admin_otra = User.objects.create_user(
            "cd-admin-otra", password="solo-prueba"
        )
        cls.docente.profile.tipo_usuario = "docente"
        cls.docente.profile.institucion = "UPEC"
        cls.docente.profile.facultad = "agropecuarias_ambientales"
        cls.docente.profile.carrera = "computacion"
        cls.docente.profile.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio logístico de prueba",
            slug=SLUG_LOGISTICA,
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            activo=True,
            administrador=cls.admin,
            capacidad_personas=None,
        )
        cls.otra = Unidad.objects.create(
            nombre="Otra unidad privada",
            slug="otro-laboratorio-cd",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            activo=True,
            administrador=cls.admin_otra,
        )
        cls.equipo = EquiposServicios.objects.create(
            codigo="EQ-QA-CD", nombre="Maqueta de prueba"
        )
        cls.url = reverse("logistica_operacion", args=[SLUG_LOGISTICA])

    def setUp(self):
        self.client.force_login(self.admin)

    def actividad(self, *, unidad=None, autor=None, **datos):
        return CatalogoActividadReserva.objects.create(
            unidad=unidad or self.unidad,
            creado_por=autor or self.docente,
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre=datos.pop("nombre", "Práctica de distribución"),
            **datos,
        )

    def delegar(self, *modulos):
        permisos = dict.fromkeys(MODULOS_OPERATIVOS, False)
        permisos.update({modulo: True for modulo in modulos})
        ResponsableUnidad.objects.update_or_create(
            unidad=self.unidad,
            usuario=self.delegado,
            defaults={
                "nombre": "Delegación sintética",
                "rol": "otro",
                "activo": True,
                "permisos_operativos": permisos,
                "recibe_reservas": False,
            },
        )
        self.client.force_login(self.delegado)

    def recurso(self, codigo, *, unidad=None, **datos):
        return UnidadEquipo.objects.create(
            laboratorio=unidad or self.unidad,
            equipo=self.equipo,
            codigo_unidad=codigo,
            estado_unidad=datos.pop("estado_unidad", "disponible"),
            activa=datos.pop("activa", True),
            **datos,
        )

    def plan(self, actividad, numero, **datos):
        return PlanificacionPractica.objects.create(
            unidad=datos.pop("unidad", self.unidad),
            actividad=actividad,
            codigo="PL-QA-CD-" + str(numero),
            fecha=timezone.localdate(),
            hora_inicio=time(8),
            hora_fin=time(10),
            tema="Práctica " + str(numero),
            asignatura="Logística de almacenamiento",
            docente_tutor="Docente sintético",
            resultado_aprendizaje="Concilia los SKU.",
            creado_por=datos.pop("creado_por", self.docente),
            **datos,
        )

    @staticmethod
    def indicadores(response):
        return {fila["titulo"]: fila for fila in response.context["indicadores"]}

    def test_anonimo_redirige_a_identidad_y_ajeno_no_consulta_datos(self):
        response = Client().get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response["Location"])
        self.client.force_login(self.ajeno)
        with CaptureQueriesContext(connection) as sql:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(any("webcitt_unidadequipo" in q["sql"] for q in sql))
        self.assertFalse(any("webcitt_guiaactividadreserva" in q["sql"] for q in sql))

    def test_cuenta_inactiva_no_accede_aunque_request_contenga_identidad(self):
        from apps.laboratorios.operacion.presentation.logistica_operacion import operacion_view

        self.admin.is_active = False
        request = RequestFactory().get(self.url)
        request.user = self.admin
        with self.assertRaises(PermissionDenied):
            operacion_view(request, SLUG_LOGISTICA)

    def test_administrador_de_otra_unidad_no_hereda_acceso(self):
        self.client.force_login(self.admin_otra)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.get(
                reverse("logistica_operacion", args=[self.otra.slug])
            ).status_code,
            404,
        )

    def test_unidad_inactiva_modulo_oculto_y_seccion_oculta_devuelven404(self):
        self.unidad.activo = False
        self.unidad.save(update_fields=["activo"])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.unidad.activo = True
        self.unidad.save(update_fields=["activo"])
        self.unidad.modulos_contenido.filter(clave="docencia-capacitacion").update(
            activo=False
        )
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.unidad.modulos_contenido.filter(clave="docencia-capacitacion").update(
            activo=True
        )
        AjusteSeccionPlanta.objects.create(
            unidad=self.unidad, numero="4.4", oculta=True
        )
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_post_no_crea_actividades_o_reservas_y_get_es_privado(self):
        response = self.client.post(self.url, {"accion": "crear", "actividad": "nueva"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(CatalogoActividadReserva.objects.count(), 0)
        self.assertEqual(Reserva.objects.count(), 0)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("Cookie", response.get("Vary", ""))

    def test_docente_verificado_adapta_sin_ver_inventario_operativo_ajeno(self):
        self.recurso("QA-PRIVADO", existencia_verificada=True)
        privada = self.actividad(nombre="Actividad de otra persona", autor=self.admin)
        self.client.force_login(self.docente)
        with CaptureQueriesContext(connection) as sql:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["adaptar_url"])
        self.assertEqual(response.context["indicadores"], [])
        self.assertEqual(response.context["actividades"], [])
        self.assertNotContains(response, privada.nombre)
        self.assertFalse(any("webcitt_unidadequipo" in q["sql"] for q in sql))
        self.assertEqual(
            self.client.get(self.url, {"actividad": privada.pk}).status_code, 404
        )

    def test_delegacion_recursos_ve_solo_inventario_y_no_seguridad_capacidad_o_guias(
        self,
    ):
        self.delegar("recursos")
        self.recurso("QA-UNO", existencia_verificada=True)
        privada = self.actividad(nombre="Actividad privada")
        response = self.client.get(self.url)
        indicadores = self.indicadores(response)
        self.assertEqual(
            set(indicadores),
            {
                "Equipos catalogados",
                "Existencia verificada",
                "Verificados y disponibles",
                "Espacios reservables activos",
            },
        )
        self.assertEqual(indicadores["Verificados y disponibles"]["valor"], 1)
        self.assertFalse(response.context["adaptar_url"])
        self.assertEqual({e["id"] for e in response.context["enlaces"]}, {"recursos"})
        self.assertEqual(
            self.client.get(self.url, {"actividad": privada.pk}).status_code, 404
        )

    def test_delegacion_inventario_no_obtiene_estadisticas_de_recursos_por_nombre(self):
        self.delegar("inventario")
        self.recurso("QA-OCULTO", existencia_verificada=True)
        with CaptureQueriesContext(connection) as sql:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["indicadores"], [])
        self.assertEqual(response.context["enlaces"], [])
        self.assertFalse(any("webcitt_unidadequipo" in q["sql"] for q in sql))

    def test_delegacion_seguridad_no_ve_inventario_y_ausencia_no_es_aprobacion(self):
        self.delegar("seguridad")
        response = self.client.get(self.url)
        indicadores = self.indicadores(response)
        self.assertEqual(
            set(indicadores), {"Requisitos obligatorios", "Requisitos de inducción"}
        )
        self.assertEqual(indicadores["Requisitos obligatorios"]["valor"], 0)
        self.assertEqual(indicadores["Requisitos obligatorios"]["estado"], "pendiente")
        self.assertIn("no equivale", indicadores["Requisitos obligatorios"]["detalle"])
        RequisitoAcceso.objects.create(
            unidad=self.unidad,
            codigo="QA-IND",
            nombre="Inducción",
            tipo="induccion",
            obligatorio=True,
            activo=True,
        )
        RequisitoAcceso.objects.create(
            unidad=self.otra,
            codigo="QA-IND-OTRA",
            nombre="Inducción otra",
            tipo="induccion",
            obligatorio=True,
            activo=True,
        )
        RequisitoAcceso.objects.create(
            unidad=self.unidad,
            codigo="QA-IND-OFF",
            nombre="Inactiva",
            tipo="induccion",
            obligatorio=True,
            activo=False,
        )
        valores = self.indicadores(self.client.get(self.url))
        self.assertEqual(valores["Requisitos de inducción"]["valor"], 1)

    def test_disponible_sin_verificacion_no_es_existencia_ni_recurso_operativo(self):
        self.recurso("QA-NOVERIFICADO")
        self.recurso("QA-VERIFICADO", existencia_verificada=True)
        self.recurso(
            "QA-MANT", existencia_verificada=True, estado_unidad="mantenimiento"
        )
        self.recurso("QA-INACTIVO", existencia_verificada=True, activa=False)
        self.recurso("QA-OTRA", unidad=self.otra, existencia_verificada=True)
        with override_settings(CITT_EXIGIR_EQUIPOS_VERIFICADOS=False):
            valores = self.indicadores(self.client.get(self.url))
        self.assertEqual(valores["Equipos catalogados"]["valor"], 4)
        self.assertEqual(valores["Existencia verificada"]["valor"], 2)
        self.assertEqual(valores["Verificados y disponibles"]["valor"], 1)

    def test_aforo_null_no_se_infiere_sumando_areas_y_cero_se_conserva(self):
        for i in range(2):
            EspacioReservable.objects.create(
                unidad=self.unidad,
                codigo="QA-AREA-" + str(i),
                nombre="Área",
                capacidad=50,
                activo=True,
                reservable=True,
            )
        EspacioReservable.objects.create(
            unidad=self.otra, codigo="QA-OTRA", nombre="Área otra", capacidad=99
        )
        valores = self.indicadores(self.client.get(self.url))
        self.assertEqual(valores["Aforo general registrado"]["valor"], "Sin registrar")
        self.assertEqual(valores["Espacios reservables activos"]["valor"], 2)
        self.unidad.capacidad_personas = 0
        self.unidad.save(update_fields=["capacidad_personas"])
        self.assertEqual(
            self.indicadores(self.client.get(self.url))["Aforo general registrado"][
                "valor"
            ],
            0,
        )

    def test_capacidad_solo_activa_vigente_y_con_respaldo_no_futura_o_vencida(self):
        hoy = timezone.localdate()
        for unidad, desde, hasta, activo in (
            (self.unidad, hoy - timedelta(days=20), hoy - timedelta(days=1), True),
            (self.unidad, hoy + timedelta(days=1), None, True),
            (self.unidad, hoy - timedelta(days=1), None, False),
            (self.otra, hoy, None, True),
        ):
            CapacidadOperativaUnidad.objects.create(
                unidad=unidad,
                vigente_desde=desde,
                vigente_hasta=hasta,
                activo=activo,
                aforo_seguridad=99,
                puestos_mobiliario=99,
                puestos_equipados=99,
                capacidad_personal=99,
                fuente="Inspección sintética",
            )
        self.assertEqual(
            self.indicadores(self.client.get(self.url))["Capacidad operativa vigente"][
                "valor"
            ],
            "Sin registrar",
        )
        actual = CapacidadOperativaUnidad.objects.create(
            unidad=self.unidad,
            vigente_desde=hoy,
            vigente_hasta=hoy,
            activo=True,
            aforo_seguridad=20,
            puestos_mobiliario=16,
            puestos_equipados=12,
            capacidad_personal=8,
            fuente="Inspección sintética",
        )
        indicador = self.indicadores(self.client.get(self.url))[
            "Capacidad operativa vigente"
        ]
        self.assertEqual((indicador["valor"], indicador["estado"]), (8, "registrado"))
        actual.fuente = "   "
        actual.save(update_fields=["fuente"])
        self.assertEqual(
            self.indicadores(self.client.get(self.url))["Capacidad operativa vigente"][
                "estado"
            ],
            "pendiente",
        )

    def test_paginacion12_busqueda_acotada_y_actividad_inactiva_excluida(self):
        for i in range(25):
            self.actividad(
                nombre="Actividad " + str(i).zfill(2), codigo="ACT-" + str(i)
            )
        self.actividad(nombre="Inactiva privada", activo=False)
        primera = self.client.get(self.url)
        segunda = self.client.get(self.url, {"page": 2})
        ultima = self.client.get(self.url, {"page": 999})
        self.assertEqual(
            [len(r.context["actividades"]) for r in (primera, segunda, ultima)],
            [12, 12, 1],
        )
        self.assertEqual(primera.context["pagina"].paginator.count, 25)
        self.assertFalse(
            {a["id"] for a in primera.context["actividades"]}
            & {a["id"] for a in segunda.context["actividades"]}
        )
        self.assertEqual(
            len(
                self.client.get(self.url, {"q": "Actividad 24"}).context["actividades"]
            ),
            1,
        )
        self.assertEqual(
            len(self.client.get(self.url, {"q": "a" * 300}).context["q"]), 100
        )
        self.assertEqual(
            self.client.get(self.url, {"page": "no-numero"}).context["pagina"].number, 1
        )

    def test_guias_max3_planes_max5_y_consulta_sin_json_contenido(self):
        actividad = self.actividad()
        for i in range(1, 7):
            GuiaActividadReserva.objects.create(
                actividad=actividad,
                titulo="Guía " + str(i),
                numero_version=i,
                es_estructurada=True,
                contenido={"privado": "CONTENIDO-JSON-NO-CARGAR"},
                subido_por=self.docente,
            )
            self.plan(actividad, i)
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía inactiva",
            numero_version=90,
            es_estructurada=True,
            activo=False,
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía importada",
            numero_version=91,
            es_estructurada=False,
        )
        self.plan(actividad, 90, eliminado_en=timezone.now())
        with CaptureQueriesContext(connection) as sql:
            response = self.client.get(self.url, {"actividad": actividad.pk})
        self.assertEqual(len(response.context["guias"]), 3)
        self.assertEqual([g["version"] for g in response.context["guias"]], [6, 5, 4])
        self.assertEqual(len(response.context["planes"]), 5)
        self.assertNotContains(response, "CONTENIDO-JSON-NO-CARGAR")
        consulta = [
            q["sql"]
            for q in sql
            if 'FROM "webcitt_guiaactividadreserva"' in q["sql"]
            and '"titulo"' in q["sql"]
        ]
        self.assertEqual(len(consulta), 2)
        self.assertTrue(all('"contenido"' not in query for query in consulta))
        self.assertEqual(
            sorted(query.rsplit("LIMIT ", 1)[-1] for query in consulta), ["1", "3"]
        )
        consulta_planes = [
            q["sql"] for q in sql if 'FROM "webcitt_planificacionpractica"' in q["sql"]
        ]
        self.assertEqual(len(consulta_planes), 1)
        self.assertIn("LIMIT 5", consulta_planes[0])

    def test_participante_ve_solo_actividad_asignada_y_no_edita_ejecucion_de_otro(self):
        actividad = self.actividad(nombre="Actividad compartida")
        actividad.participantes_autorizados.add(self.participante)
        self.actividad(nombre="Actividad privada ajena")
        documento = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía privada compartida",
            numero_version=1,
            es_estructurada=True,
            visibilidad="participantes",
            subido_por=self.docente,
        )
        plan = self.plan(actividad, 1, estado="aprobada")
        self.client.force_login(self.participante)
        response = self.client.get(self.url, {"actividad": actividad.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [a["id"] for a in response.context["actividades"]], [actividad.pk]
        )
        self.assertEqual([g["id"] for g in response.context["guias"]], [documento.pk])
        self.assertEqual([p["id"] for p in response.context["planes"]], [plan.pk])
        self.assertEqual(response.context["planes"][0]["ejecucion_url"], "")
        self.assertFalse(response.context["adaptar_url"])
        self.assertEqual(response.context["indicadores"], [])
        self.assertNotContains(response, "Actividad privada ajena")
        self.assertEqual(
            self.client.get(
                reverse("ver_guia_actividad", args=[documento.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "detalle_planificacion_practica", args=[SLUG_LOGISTICA, plan.pk]
                )
            ).status_code,
            200,
        )

    def test_docente_autor_ve_solo_sus_actividades_y_no_versiones_de_otra_unidad(self):
        propia = self.actividad(nombre="Propia")
        otra = self.actividad(unidad=self.otra, nombre="Contenido de otra unidad")
        self.actividad(nombre="De otro autor", autor=self.admin)
        self.client.force_login(self.docente)
        response = self.client.get(self.url, {"actividad": propia.pk})
        self.assertEqual(
            [a["id"] for a in response.context["actividades"]], [propia.pk]
        )
        self.assertEqual(
            self.client.get(self.url, {"actividad": otra.pk}).status_code, 404
        )
        self.assertNotContains(response, otra.nombre)

    def test_actividad_manipulada_o_inactiva_no_se_sustituye_silenciosamente(self):
        privada = self.actividad(autor=self.admin)
        inactiva = self.actividad(activo=False)
        self.client.force_login(self.docente)
        for seleccion in (
            str(privada.pk),
            str(inactiva.pk),
            "9999999999",
            "1 OR 1=1",
            "-1",
            "１２",
            "1.0",
            "9" * 11,
            "<script>",
        ):
            with self.subTest(seleccion=seleccion):
                self.assertEqual(
                    self.client.get(self.url, {"actividad": seleccion}).status_code, 404
                )

    def test_semilla0_y_caso_se_conservan_en_navegacion_y_precarga(self):
        actividad = self.actividad()
        response = self.client.get(
            self.url, {"caso": "cd-falla", "semilla": 0, "actividad": actividad.pk}
        )
        self.assertEqual(
            (response.context["caso"], response.context["semilla"]), ("cd-falla", 0)
        )
        for clave in ("volver_url", "simulador_url", "adaptar_url"):
            self.assertIn("semilla=0", response.context[clave])
            self.assertIn("caso=cd-falla", response.context[clave])
        self.assertIn("plantilla=logistica-cd", response.context["adaptar_url"])
        for fila in response.context["actividades"]:
            self.assertIn("semilla=0", fila["url"])
        for parametros in (
            {"caso": "inventado"},
            {"semilla": "-1"},
            {"semilla": "2147483648"},
        ):
            r = self.client.get(self.url, parametros)
            self.assertEqual(
                (r.context["caso"], r.context["semilla"]), ("cd-normal", 42)
            )

    def test_lecturas_no_crean_expedientes_asistencia_consumos_o_partidas(self):
        actividad = self.actividad()
        tablas = (
            CatalogoActividadReserva,
            GuiaActividadReserva,
            PlanificacionPractica,
            EjecucionPractica,
            EvidenciaPractica,
            Reserva,
            RegistroAuditoriaUnidad,
            RegistroIngreso,
            RegistroParticipanteReserva,
            PartidaSimulador,
        )
        antes = {m.__name__: m.objects.count() for m in tablas}
        with CaptureQueriesContext(connection) as sql:
            for parametros in (
                {},
                {"actividad": actividad.pk},
                {"semilla": 0},
                {"q": "ausente", "page": 2},
            ):
                self.assertEqual(self.client.get(self.url, parametros).status_code, 200)
        self.assertEqual({m.__name__: m.objects.count() for m in tablas}, antes)
        for q in sql:
            self.assertFalse(
                q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")),
                q["sql"],
            )
            self.assertNotIn("webcitt_partidasimulador", q["sql"])
            self.assertNotIn("webcitt_eventopartida", q["sql"])
        self.assertTrue(
            all(
                c["estado"] == "pendiente"
                for c in self.client.get(self.url).context["controles"]
            )
        )

    def test_inventario_creciente_no_agrega_consultas_ni_materializa_filas(self):
        self.recurso("QA-BASE", existencia_verificada=True)
        self.client.get(self.url)  # Calentar exclusivamente cachés de presentación.
        with CaptureQueriesContext(connection) as base:
            self.assertEqual(self.client.get(self.url).status_code, 200)
        UnidadEquipo.objects.bulk_create(
            [
                UnidadEquipo(
                    laboratorio=self.unidad,
                    equipo=self.equipo,
                    codigo_unidad="QA-MASA-" + str(i),
                    activa=True,
                    estado_unidad="disponible",
                    existencia_verificada=False,
                )
                for i in range(250)
            ]
        )
        with CaptureQueriesContext(connection) as grande:
            response = self.client.get(self.url)
        consultas = [q["sql"] for q in grande if "webcitt_unidadequipo" in q["sql"]]
        self.assertEqual(len(consultas), 1)
        self.assertIn("COUNT(", consultas[0].upper())
        self.assertNotIn('"numero_serie"', consultas[0])
        self.assertLessEqual(len(grande), len(base) + 1)
        self.assertEqual(
            self.indicadores(response)["Equipos catalogados"]["valor"], 251
        )
        self.assertEqual(
            self.indicadores(response)["Verificados y disponibles"]["valor"], 1
        )

    def test_planes_aprobados_sin_ejecucion_no_significan_cierre_efectivo(self):
        actividad = self.actividad()
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=actividad,
            usuario=self.docente,
            fecha=timezone.localdate(),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo="QA-RESERVA",
            equipo_nombre="Maqueta sintética",
            estado="confirmada",
        )
        plan = self.plan(actividad, 1, estado="aprobada", reserva=reserva)
        response = self.client.get(
            self.url, {"actividad": actividad.pk, "plan": plan.pk}
        )
        controles = {c["id"]: c for c in response.context["controles"]}
        self.assertEqual(controles["plan"]["estado"], "registrado")
        self.assertEqual(controles["ejecucion"]["estado"], "pendiente")
        self.assertEqual(controles["reporte"]["estado"], "pendiente")
        self.assertTrue(response.context["planes"][0]["ejecucion_url"])
        EjecucionPractica.objects.create(
            planificacion=plan,
            fecha_ejecucion=timezone.localdate(),
            resultado="ejecutada",
            estado="revision",
            creado_por=self.docente,
            hora_inicio_real=time(8),
            hora_fin_real=time(10),
            cumplimiento_resultado="si",
        )
        response = self.client.get(
            self.url, {"actividad": actividad.pk, "plan": plan.pk}
        )
        self.assertEqual(response.context["planes"][0]["ejecucion_url"], "")
        self.assertIn(
            "Sólo las ejecuciones validadas",
            next(c for c in response.context["controles"] if c["id"] == "reporte")[
                "detalle"
            ],
        )

    def test_presentacion_escapa_busqueda_y_nombre_actividad(self):
        self.actividad(nombre='<script>alert("privado")</script>')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'<script>alert("privado")</script>', response.content)
        self.assertIn(b"&lt;script&gt;", response.content)
        response = self.client.get(self.url, {"q": "<img src=x onerror=alert(1)>"})
        self.assertNotIn(b"<img src=x onerror=alert(1)>", response.content)

    def test_equipos_principales_y_asociados_m2m_se_cuentan_una_sola_vez(self):
        principal = self.recurso("QA-PRINCIPAL", existencia_verificada=True)
        principal.laboratorios.add(self.unidad, self.otra)
        compartido = self.recurso(
            "QA-COMPARTIDO", unidad=self.otra, existencia_verificada=True
        )
        compartido.laboratorios.add(self.unidad)
        no_verificado = self.recurso("QA-COMPARTIDO-NO-VERIFICADO", unidad=self.otra)
        no_verificado.laboratorios.add(self.unidad)
        self.recurso("QA-AJENO", unidad=self.otra, existencia_verificada=True)
        valores = self.indicadores(self.client.get(self.url))
        self.assertEqual(valores["Equipos catalogados"]["valor"], 3)
        self.assertEqual(valores["Existencia verificada"]["valor"], 2)
        self.assertEqual(valores["Verificados y disponibles"]["valor"], 2)

    def test_guia_publicada_anterior_no_se_oculta_por_tres_borradores_recientes(self):
        actividad = self.actividad()
        publicada = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Versión publicada anterior",
            numero_version=1,
            es_estructurada=True,
            estado_publicacion="publicada",
            activo=True,
            subido_por=self.docente,
        )
        for version in (2, 3, 4):
            GuiaActividadReserva.objects.create(
                actividad=actividad,
                titulo="Borrador " + str(version),
                numero_version=version,
                es_estructurada=True,
                estado_publicacion="borrador",
                activo=True,
                subido_por=self.docente,
            )
        response = self.client.get(self.url, {"actividad": actividad.pk})
        self.assertEqual([g["version"] for g in response.context["guias"]], [4, 3, 2])
        control = next(x for x in response.context["controles"] if x["id"] == "guia")
        self.assertEqual(control["estado"], "registrado")
        publicada.activo = False
        publicada.save(update_fields=["activo"])
        response = self.client.get(self.url, {"actividad": actividad.pk})
        self.assertEqual(
            next(x for x in response.context["controles"] if x["id"] == "guia")[
                "estado"
            ],
            "pendiente",
        )

    def test_plan_aprobado_sin_reserva_no_ofrece_registrar_ejecucion(self):
        actividad = self.actividad()
        plan = self.plan(actividad, 101, estado="aprobada")
        response = self.client.get(self.url, {"actividad": actividad.pk})
        fila = next(p for p in response.context["planes"] if p["id"] == plan.pk)
        self.assertEqual(fila["ejecucion_url"], "")
        self.assertTrue(fila["url"])
        self.assertIsNone(plan.reserva_id)
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(EjecucionPractica.objects.count(), 0)

    def test_delegado_solo_agenda_recibe_enlace_agenda_sin_decidir_reservas(self):
        self.delegar("agenda")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["permisos"]["agenda"])
        self.assertFalse(response.context["permisos"]["reservas"])
        self.assertEqual(response.context["indicadores"], [])
        self.assertEqual({e["id"] for e in response.context["enlaces"]}, {"agenda"})
        self.assertIn("modo_reservas=agenda", response.context["enlaces"][0]["url"])
        self.assertFalse(response.context["adaptar_url"])
