
from tests.integration.utiles import verificar_pertenencia
import json
import re
import tempfile
from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, NotificacionReserva, ProgramacionReserva, Reserva, ReservaAdjunto
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService, FablabServiceConsumible, SolicitudConsumible, SolicitudFabricacion
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.formacion.models.practicas import PlanificacionPractica, RegistroAuditoriaUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


INTENCION_DOCENCIA = (
    "Con el grupo de tercer semestre realizaremos la práctica de prototipado rápido de un "
    "soporte mecánico sencillo. Cada estudiante diseñará la pieza en el software CAD de la "
    "estación de trabajo, la preparará en el laminador y la imprimirá en la impresora 3D con "
    "filamento PLA del laboratorio. Buscamos que apliquen tolerancias de ensamble, calculen "
    "tiempos de impresión y registren el consumo de material en una tabla de evidencias; "
    "usaremos dos horas por sesión durante cuatro semanas del período académico vigente."
)


class ReservasDomainTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpClass(cls):
        cls._media_temporal = tempfile.TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_temporal.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._media_override.disable()
            cls._media_temporal.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="solicitante",
            email="solicitante@upec.edu.ec",
            password="prueba-segura",
            first_name="Ana",
            last_name="Pérez",
        )
        cls.usuario.profile.carrera = "computacion"
        cls.usuario.profile.tipo_usuario = "estudiante"
        cls.usuario.profile.facultad = "agropecuarias_ambientales"
        cls.usuario.profile.nivel_academico = "quinto_semestre"
        cls.usuario.profile.cedula = "2026-0001"
        cls.usuario.profile.institucion = "UPEC"
        cls.usuario.profile.save()
        verificar_pertenencia(cls.usuario)
        cls.docente = get_user_model().objects.create_user(
            username="docente.solicitante",
            email="docente.solicitante@upec.edu.ec",
            password="prueba-segura",
            first_name="María",
            last_name="Docente",
        )
        cls.docente.profile.carrera = "computacion"
        cls.docente.profile.tipo_usuario = "docente"
        cls.docente.profile.facultad = "agropecuarias_ambientales"
        cls.docente.profile.institucion = "UPEC"
        cls.docente.profile.save()
        verificar_pertenencia(cls.docente)
        cls.participante = get_user_model().objects.create_user(
            username="participante.registrado",
            email="participante@upec.edu.ec",
            password="prueba-segura",
            first_name="Luis",
            last_name="Mora",
        )
        cls.participante.profile.carrera = "computacion"
        cls.participante.profile.tipo_usuario = "estudiante"
        cls.participante.profile.facultad = "agropecuarias_ambientales"
        cls.participante.profile.nivel_academico = "tercer_semestre"
        cls.participante.profile.cedula = "2026-0002"
        cls.participante.profile.institucion = "UPEC"
        cls.participante.profile.save()
        cls.laboratorio = Unidad.objects.create(
            nombre="Laboratorio de prueba",
            descripcion="Unidad destinada a verificar el flujo de reservas.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-prueba-reservas",
        )
        cls.otro_laboratorio = Unidad.objects.create(
            nombre="Laboratorio externo",
            descripcion="Unidad usada para comprobar el aislamiento de recursos.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-externo-reservas",
        )
        cls.equipo = EquiposServicios.objects.create(
            codigo="EQ-RES-001",
            nombre="Equipo reservable",
        )
        cls.unidad_equipo = UnidadEquipo.objects.create(
            codigo_unidad="UE-RES-001",
            equipo=cls.equipo,
            laboratorio=cls.laboratorio,
            estado_unidad="disponible",
            activa=True,
        )
        cls.unidad_ajena = UnidadEquipo.objects.create(
            codigo_unidad="UE-RES-002",
            equipo=cls.equipo,
            laboratorio=cls.otro_laboratorio,
            estado_unidad="disponible",
            activa=True,
        )

        cls.material = Consumible.objects.create(
            unidad=cls.laboratorio,
            codigo="MAT-RES-001",
            nombre="Resina para prototipado",
            clasificacion="insumo",
            familia="Resinas para impresión 3D",
            variante="Estándar",
            color="Gris",
            presentacion="Botella de 1 L",
            unidad_medida="kg",
            descripcion="Material disponible para actividades autorizadas.",
            instrucciones_solicitud="Use el valor calculado por el laminador.",
            imagen_catalogo="img/catalogo/fablab/resina-fotopolimerica.png",
            stock_total=Decimal("8.500"),
            minimo=Decimal("1.000"),
            lote="L-2026-08",
        )
        cls.material_apoyo = Consumible.objects.create(
            unidad=cls.laboratorio,
            codigo="MAT-RES-APOYO-001",
            nombre="Probeta graduada de prueba",
            clasificacion="material",
            familia="Vidriería",
            variante="100 mL",
            unidad_medida="unidad",
            descripcion="Material reutilizable de apoyo para la actividad.",
            stock_total=Decimal("6"),
        )
        cls.material_ajeno = Consumible.objects.create(
            unidad=cls.otro_laboratorio,
            codigo="MAT-RES-002",
            nombre="Material ajeno",
            unidad_medida="kg",
            stock_total=Decimal("10"),
        )
        cls.software = SoftwareDisponible.objects.create(
            unidad=cls.laboratorio,
            codigo="SW-RES-001",
            nombre="Software CAD de prueba",
            version="2026",
            tipo_acceso="licencia",
            licencias_totales=5,
            licencias_disponibles=3,
            requiere_reserva=True,
            activo=True,
        )
        cls.software.equipos_instalados.add(cls.unidad_equipo)

    def _payload_reserva(self, unidad_equipo=None, **overrides):
        unidad_equipo = unidad_equipo or self.unidad_equipo
        payload = {
            "unidad_id": self.laboratorio.pk,
            "fecha_inicio": "2026-08-20T09:00",
            "fecha_fin": "2026-08-20T11:00",
            "horas_seleccionadas": json.dumps([9, 10]),
            "proposito": "Docencia",
            "descripcion_proyecto": "Validación funcional del sistema de reservas.",
            "participantes_seleccionados": "[]",
            "aceptar_terminos": "on",
            "modalidad_servicio": "modelo_listo",
            "solicitante_nombre": "Nombre alterado",
            "solicitante_email": "correo-alterado@example.com",
            "unidades_seleccionadas": json.dumps(
                [
                    {
                        "id": unidad_equipo.pk,
                        "codigo": "CODIGO-MANIPULADO",
                        "ubicacion": "Ubicación manipulada",
                        "equipo_nombre": "Equipo manipulado",
                    }
                ]
            ),
        }
        payload.update(overrides)
        return payload

    def _payload_guia_integrada(self):
        return {
            "guia_asignatura": "Diseño y fabricación digital",
            "guia_resultado_aprendizaje": (
                "Configura y ejecuta un proceso de fabricación digital con trazabilidad."
            ),
            "guia_objetivos": (
                "Preparar el modelo, operar el equipo de forma segura y documentar el resultado."
            ),
            "guia_fundamento_teorico": (
                "La fabricación digital transforma modelos virtuales en piezas físicas "
                "mediante parámetros controlados de proceso."
            ),
            "guia_medidas_seguridad": (
                "Usar los elementos de protección definidos y verificar el equipo antes de iniciar."
            ),
            "guia_procedimiento": (
                "Verificar el área y el equipo\nPreparar el archivo\nEjecutar la fabricación\nRegistrar resultados"
            ),
            "guia_resultados_esperados": (
                "Pieza fabricada y registro verificable de parámetros, tiempo y consumo."
            ),
            "guia_criterios_evaluacion": (
                "Seguridad, configuración correcta, calidad del resultado y trazabilidad."
            ),
            "guia_manejo_residuos": (
                "Separar residuos aprovechables y disponer desperdicios según el protocolo."
            ),
            "guia_bibliografia": (
                "Manual de operación del equipo\nProtocolo de seguridad del laboratorio"
            ),
            "guia_permite_descarga": "1",
            "guia_confirmada_solicitante": "1",
        }

    def test_rutas_publicas_pertenecen_al_dominio_reservas(self):
        for route_name in ("crear_reserva", "obtener_reservas_usuario", "cancelar_reserva_usuario"):
            with self.subTest(route_name=route_name):
                kwargs = {"reserva_id": 1} if route_name == "cancelar_reserva_usuario" else {}
                self.assertEqual(
                    resolve(reverse(route_name, kwargs=kwargs)).func.__module__,
                    "apps.reservas.presentation.views",
                )

    def test_creacion_incompleta_conserva_contrato_json(self):
        response = self.client.post(reverse("crear_reserva"), {})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Debe iniciar sesión para enviar una solicitud de reserva.",
            },
        )

    def test_revocacion_entre_cotizar_y_guardar_no_emite_reserva_con_tarifa_anterior(self):
        from unittest.mock import patch
        from apps.reservas.presentation.cotizaciones import calcular_costo_referencial_recursos
        from apps.core.usuarios.verificacion import estado_verificacion, registrar_revision

        self.client.force_login(self.usuario)
        cantidad = Reserva.objects.count()

        def cotizar_y_revocar(*args, **kwargs):
            cotizacion = calcular_costo_referencial_recursos(*args, **kwargs)
            perfil = self.usuario.profile
            registrar_revision(
                perfil_id=perfil.pk,
                revisor=get_user_model().objects.get(username='verificador.pruebas'),
                decision='revocada', fundamento='Revocación sintética durante el envío.',
                referencia='QA-ENVIO', huella=estado_verificacion(perfil)['huella'],
            )
            return cotizacion

        with patch('apps.reservas.presentation.creacion_servicio.calcular_costo_referencial_recursos',
                   side_effect=cotizar_y_revocar):
            respuesta = self.client.post(reverse('crear_reserva'), self._payload_reserva())
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('Tu verificación cambió', respuesta.json()['error'])
        self.assertEqual(Reserva.objects.count(), cantidad)

    @override_settings(TIME_ZONE="Europe/Madrid", LANGUAGE_CODE="es")
    def test_api_rechaza_horas_ambiguas_y_offsets_sin_crear_reservas(self):
        self.client.force_login(self.usuario)
        cantidad = Reserva.objects.count()
        for fecha, mensaje in (("2027-03-28", "no existe"), ("2027-10-31", "se repite")):
            respuesta = self.client.post(reverse("crear_reserva"), self._payload_reserva(
                fecha_inicio=f"{fecha}T02:00", fecha_fin=f"{fecha}T03:00",
                horas_seleccionadas=json.dumps([2]), proposito="Investigación",
            ))
            self.assertEqual(respuesta.status_code, 400, respuesta.content)
            self.assertIn(mensaje, respuesta.json()["error"])
        respuesta = self.client.post(reverse("crear_reserva"), self._payload_reserva(
            fecha_inicio="2027-09-16T09:00+02:00", fecha_fin="2027-09-16T11:00+02:00",
        ))
        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        self.assertIn("sin desplazamiento UTC", respuesta.json()["error"])
        self.assertEqual(Reserva.objects.count(), cantidad)

    def test_consulta_anonima_conserva_contrato_json(self):
        response = self.client.get(reverse("obtener_reservas_usuario"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"success": False, "error": "Usuario no autenticado"},
        )

    def test_usuario_puede_cancelar_solo_una_reserva_propia_pendiente(self):
        self.client.force_login(self.usuario)
        creada = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva = Reserva.objects.get(pk=creada.json()["reserva_id"])

        response = self.client.post(
            reverse("cancelar_reserva_usuario", kwargs={"reserva_id": reserva.pk})
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "cancelada")
        self.assertEqual(response.json()["estado_display"], "Cancelada")
        auditoria = RegistroAuditoriaUnidad.objects.get(
            unidad=self.laboratorio,
            objeto_id=str(reserva.pk),
            descripcion="Cancelación solicitada por el titular de la reserva.",
        )
        self.assertEqual(auditoria.usuario_id, self.usuario.pk)
        self.assertEqual(auditoria.datos_anteriores, {"estado": "pendiente"})
        self.assertEqual(auditoria.datos_nuevos, {"estado": "cancelada"})

        segundo_intento = self.client.post(
            reverse("cancelar_reserva_usuario", kwargs={"reserva_id": reserva.pk})
        )
        self.assertEqual(segundo_intento.status_code, 409)

    def test_reportes_de_reservas_permanecen_protegidos_en_admin(self):
        for route_name in (
            "admin:reservas-estadisticas",
            "admin:reservas-descargar-pdf",
            "admin:reservas-reporte-uso",
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login/", response.url)

    def test_reporte_institucional_muestra_solicitudes_y_participaciones(self):
        administrador = get_user_model().objects.create_superuser(
            username="admin.reporte",
            email="admin.reporte@upec.edu.ec",
            password="prueba-segura",
        )
        self.client.force_login(self.usuario)
        creada = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        self.assertEqual(creada.status_code, 200, creada.content)
        self.client.force_login(administrador)

        response = self.client.get(reverse("admin:reservas-reporte-uso"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reporte de uso por carreras y usuarios")
        self.assertContains(response, "1 solicitudes y 1 participaciones")
        self.assertContains(response, "Uso por propósito institucional")
        self.assertContains(response, "Participaciones por carrera de origen")

    def test_usuario_autenticado_crea_reserva_con_identidad_verificada(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.usuario, self.usuario)
        self.assertEqual(reserva.laboratorio, self.laboratorio)
        self.assertEqual(reserva.nombre_solicitante, "Ana Pérez")
        self.assertEqual(reserva.correo_solicitante, "solicitante@upec.edu.ec")
        self.assertEqual(reserva.numero_participantes, 1)
        self.assertEqual(reserva.tipo_usuario_solicitante, "estudiante")
        self.assertEqual(reserva.facultad_solicitante, "agropecuarias_ambientales")
        self.assertEqual(reserva.carrera_solicitante, "computacion")
        self.assertEqual(reserva.duracion, 2)
        self.assertEqual(reserva.equipo_codigo, self.equipo.codigo)
        self.assertEqual(reserva.equipo_nombre, self.equipo.nombre)
        self.assertTrue(reserva.incluye_espacio)
        self.assertEqual(reserva.alcance_espacio, "espacio_unico")
        unidades_guardadas = json.loads(reserva.unidades_seleccionadas)
        self.assertEqual(
            unidades_guardadas,
            [
                {
                    "id": self.unidad_equipo.pk,
                    "codigo": self.unidad_equipo.codigo_unidad,
                    "ubicacion": "No especificada",
                    "equipo_id": self.equipo.pk,
                    "equipo_codigo": self.equipo.codigo,
                    "equipo_nombre": self.equipo.nombre,
                }
            ],
        )
        comprobante_url = reverse(
            "comprobante_reserva",
            args=[reserva.pk],
        )
        self.assertEqual(response.json()["comprobante_url"], comprobante_url)
        notificacion = NotificacionReserva.objects.get(
            reserva=reserva,
            tipo="confirmacion",
        )
        self.assertEqual(notificacion.usuario, self.usuario)
        self.assertEqual(notificacion.url, comprobante_url)

        comprobante = self.client.get(comprobante_url)
        self.assertEqual(comprobante.status_code, 200)
        self.assertContains(comprobante, "Solicitud recibida correctamente")
        self.assertContains(comprobante, reserva.codigo_reserva)
        self.assertContains(comprobante, self.equipo.nombre)
        self.assertContains(comprobante, "¿Qué sucede ahora?")
        comprobante_pdf = self.client.get(
            reverse("comprobante_reserva_pdf", args=[reserva.pk])
        )
        self.assertEqual(comprobante_pdf.status_code, 200)
        self.assertEqual(comprobante_pdf["Content-Type"], "application/pdf")
        self.assertTrue(comprobante_pdf.content.startswith(b"%PDF"))

        historial = self.client.get(reverse("obtener_reservas_usuario"))
        self.assertEqual(historial.status_code, 200)
        self.assertEqual(
            historial.json()["reservas"][0]["comprobante_url"],
            comprobante_url,
        )

    def test_comprobante_no_expone_reserva_a_otro_usuario(self):
        self.client.force_login(self.usuario)
        response = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        self.assertEqual(response.status_code, 200, response.content)
        otra_persona = get_user_model().objects.create_user(
            username="otro.solicitante",
            email="otro@upec.edu.ec",
            password="prueba-segura",
        )
        identificar(otra_persona)
        self.client.force_login(otra_persona)

        comprobante = self.client.get(response.json()["comprobante_url"])
        comprobante_pdf = self.client.get(
            reverse("comprobante_reserva_pdf", args=[response.json()["reserva_id"]])
        )

        self.assertEqual(comprobante.status_code, 403)
        self.assertEqual(comprobante_pdf.status_code, 403)

    def test_servidor_rechaza_fin_de_semana_no_habilitado(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                fecha_inicio="2026-08-22T09:00",
                fecha_fin="2026-08-22T11:00",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn(
            "solo pueden ser registradas por la administración",
            response.json()["error"],
        )

    def test_reserva_guarda_contexto_institucional_y_fotografia_de_participantes(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica curricular de fabricación digital",
            codigo="FAB-DOC-001",
            unidad=self.laboratorio,
            facultad="agropecuarias_ambientales",
            carrera="computacion",
            periodo_academico="2026-B",
            responsable="Docente responsable de la asignatura",
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía curricular de fabricación digital",
            archivo=SimpleUploadedFile(
                "guia-fabricacion-digital.pdf",
                b"%PDF-1.4\n% guia curricular\n",
                content_type="application/pdf",
            ),
            estado_publicacion="publicada",
            visibilidad="unidad",
            subido_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
                participantes_seleccionados=json.dumps([self.participante.pk]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.proposito_codigo, "docencia_practica")
        self.assertEqual(reserva.subtipo_actividad, "practica_curricular")
        self.assertEqual(reserva.vinculacion_actividad, "catalogo")
        self.assertEqual(reserva.actividad_catalogo, actividad)
        self.assertEqual(reserva.referencia_actividad, actividad.nombre)
        self.assertEqual(reserva.codigo_referencia_actividad, "FAB-DOC-001")
        self.assertEqual(reserva.periodo_academico, "2026-B")
        self.assertEqual(reserva.origen_programacion, "programada")
        self.assertEqual(reserva.facultad_beneficiaria, self.usuario.profile.facultad)
        self.assertEqual(reserva.carrera_beneficiaria, self.usuario.profile.carrera)
        registros = reserva.registros_participantes.order_by("rol")
        self.assertEqual(registros.count(), 2)
        solicitante = registros.get(rol="solicitante")
        secundario = registros.get(rol="participante")
        self.assertEqual(solicitante.usuario, self.usuario)
        self.assertEqual(solicitante.tipo_usuario, "estudiante")
        self.assertEqual(secundario.usuario, self.participante)
        self.assertEqual(secundario.carrera, "computacion")

    def test_reserva_distingue_la_carrera_beneficiaria_de_la_del_solicitante(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="investigacion_innovacion",
                subtipo_actividad="proyecto_investigacion",
                alcance_beneficiario="otra_carrera",
                carrera_beneficiaria="enfermeria",
                vinculacion_actividad="manual",
                referencia_actividad="Proyecto de investigación interdisciplinario",
                codigo_referencia_actividad="PI-2026-015",
                responsable_actividad="Dirección del proyecto",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.carrera_solicitante, "computacion")
        self.assertEqual(reserva.carrera_beneficiaria, "enfermeria")
        self.assertEqual(reserva.facultad_beneficiaria, "salud_educacion")
        self.assertEqual(reserva.vinculacion_actividad, "manual")

    def test_el_expediente_se_publica_como_ventana_sobre_la_agenda(self):
        self.client.force_login(self.usuario)
        pagina = self.client.get(self.laboratorio.get_absolute_url())

        self.assertContains(pagina, 'id="misReservasExpediente"')
        self.assertContains(pagina, 'my-reservations-record__dialog')
        self.assertContains(pagina, 'my-reservations-record__scrim')
        self.assertContains(pagina, 'aria-modal="true"')
        # La guía tiene su propia pestaña, separada del comprobante.
        self.assertContains(pagina, 'data-record-tab="guia"')
        self.assertContains(pagina, 'data-record-panel="guia"')

    def test_el_expediente_del_solicitante_trae_recorrido_y_documentos(self):
        self.client.force_login(self.usuario)
        creada = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva_id = creada.json()["reserva_id"]

        listado = self.client.get(reverse("obtener_reservas_usuario")).json()
        fila = next(item for item in listado["reservas"] if item["id"] == reserva_id)

        # Recorrido: la solicitud ya se envió y la revisión está en curso.
        linea = fila["linea_tiempo"]
        self.assertEqual(linea["situacion"], "en_curso")
        self.assertEqual(linea["etapa_actual"], "revision")
        self.assertEqual(
            [paso["codigo"] for paso in linea["pasos"]],
            ["solicitud", "revision", "confirmada", "ejecucion", "cierre"],
        )
        self.assertEqual(linea["pasos"][0]["situacion"], "hecho")
        self.assertEqual(linea["pasos"][1]["situacion"], "actual")
        self.assertEqual(linea["pasos"][4]["situacion"], "pendiente")
        self.assertTrue(linea["pasos"][0]["fecha"])
        # Documentos que se abren dentro del panel, sin salir a otra pantalla.
        self.assertIn("fragmento=1", fila["comprobante_fragmento_url"])
        self.assertIn("inline=1", fila["comprobante_pdf_url"])
        self.assertIn("requiere_guia", fila["documentacion"])

        fragmento = self.client.get(fila["comprobante_fragmento_url"])
        self.assertEqual(fragmento.status_code, 200)
        self.assertContains(fragmento, "reservation-receipt-embed")
        self.assertNotContains(fragmento, "<html")

        pdf = self.client.get(fila["comprobante_pdf_url"])
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf["Content-Disposition"].startswith("inline"))
        descarga = self.client.get(reverse("comprobante_reserva_pdf", args=[reserva_id]))
        self.assertTrue(descarga["Content-Disposition"].startswith("attachment"))

    def test_el_recorrido_marca_la_etapa_donde_se_detuvo_una_cancelacion(self):
        self.client.force_login(self.usuario)
        creada = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        reserva_id = creada.json()["reserva_id"]
        self.client.post(
            reverse("cancelar_reserva_usuario", args=[reserva_id]),
            {"motivo": "El grupo cambió de horario."},
        )

        listado = self.client.get(reverse("obtener_reservas_usuario")).json()
        fila = next(item for item in listado["reservas"] if item["id"] == reserva_id)
        linea = fila["linea_tiempo"]

        # Se canceló sin aprobación: la línea se corta en la revisión.
        self.assertEqual(linea["situacion"], "interrumpida")
        self.assertEqual(linea["etapa_actual"], "revision")
        situaciones = [paso["situacion"] for paso in linea["pasos"]]
        self.assertEqual(situaciones[0], "hecho")
        self.assertEqual(situaciones[1], "detenido")
        self.assertEqual(situaciones[2:], ["descartado", "descartado", "descartado"])
        self.assertEqual(linea["pasos"][1]["titulo"], "Reserva cancelada")
        self.assertIn("por el solicitante", linea["pasos"][1]["detalle"])

    def test_cancelar_conserva_la_reserva_con_quien_cuando_y_por_que(self):
        self.client.force_login(self.usuario)
        creada = self.client.post(reverse("crear_reserva"), self._payload_reserva())
        self.assertEqual(creada.status_code, 200, creada.content)
        reserva_id = creada.json()["reserva_id"]

        response = self.client.post(
            reverse("cancelar_reserva_usuario", args=[reserva_id]),
            {"motivo": "El grupo cambió de horario de clase."},
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=reserva_id)
        self.assertEqual(reserva.estado, "cancelada")
        self.assertEqual(reserva.origen_cancelacion, "solicitante")
        self.assertEqual(reserva.cancelada_por, self.usuario)
        self.assertIsNotNone(reserva.cancelada_en)
        self.assertEqual(reserva.motivo_cancelacion, "El grupo cambió de horario de clase.")
        self.assertIn("Reserva cancelada por el solicitante: El grupo", reserva.observaciones_validacion)
        self.assertIn("por el solicitante", response.json()["cancelacion"])
        # Sigue en el historial (fuera de la agenda) y en el comprobante.
        listado = self.client.get(reverse("obtener_reservas_usuario")).json()
        fila = next(item for item in listado["reservas"] if item["id"] == reserva_id)
        self.assertFalse(fila["ocupa_agenda"])
        self.assertIn("Motivo: El grupo cambió", fila["cancelacion"])
        comprobante = self.client.get(creada.json()["comprobante_url"])
        self.assertContains(comprobante, "Cancelación")
        self.assertContains(comprobante, "se conserva como registro y evidencia")
        pdf = self.client.get(reverse("comprobante_reserva_pdf", args=[reserva_id]))
        self.assertEqual(pdf.status_code, 200)

    def test_fuera_de_docencia_la_descripcion_es_breve_y_va_al_comprobante(self):
        self.client.force_login(self.usuario)
        breve = (
            "Para el proyecto de riego inteligente imprimiremos en la impresora 3D FDM las "
            "carcasas de tres sensores de humedad y probaremos su ensamble con la placa "
            "electrónica. Traeremos los modelos STL y usaremos filamento del laboratorio "
            "en dos sesiones de tres horas."
        )
        self.assertGreaterEqual(len(breve.split()), 30)
        self.assertLess(len(breve.split()), 50)
        investigacion = dict(
            proposito_codigo="investigacion_innovacion",
            subtipo_actividad="proyecto_investigacion",
            alcance_beneficiario="otra_carrera",
            carrera_beneficiaria="enfermeria",
            vinculacion_actividad="manual",
            referencia_actividad="Proyecto de riego inteligente",
            codigo_referencia_actividad="PI-2026-020",
            responsable_actividad="Dirección del proyecto",
        )

        corta = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(**investigacion, intencion_solicitud="Imprimir tres carcasas."),
        )
        self.assertEqual(corta.status_code, 400)
        self.assertIn("al menos 30 palabras", corta.json()["error"])

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(**investigacion, intencion_solicitud=breve),
        )
        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.intencion_solicitud, breve)
        comprobante = self.client.get(response.json()["comprobante_url"])
        self.assertContains(comprobante, "Lo que se solicita realizar")
        self.assertContains(comprobante, "riego inteligente")
        # La descripcion trazable conserva la intencion, pero el comprobante no la repite.
        self.assertIn("Intención: Para el proyecto", reserva.descripcion_proyecto)
        self.assertEqual(comprobante.content.decode().count("carcasas de tres sensores"), 1)

    def test_practica_curricular_rechaza_una_guia_sin_aprobar(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica con guía pendiente de revisión pública",
            unidad=self.laboratorio,
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía visible para la actividad",
            archivo=SimpleUploadedFile(
                "guia-pendiente.pdf",
                b"%PDF-1.4\n% guia pendiente\n",
                content_type="application/pdf",
            ),
            estado_publicacion="revision",
            visibilidad="participantes",
            subido_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
            ),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("aprobada y vigente", response.json()["error"])
        self.assertFalse(Reserva.objects.exists())

    def test_actividad_nueva_guarda_guias_y_limita_su_acceso_a_participantes(self):
        self.client.force_login(self.docente)
        payload = self._payload_reserva(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            alcance_beneficiario="perfil_solicitante",
            vinculacion_actividad="manual",
            referencia_actividad="Práctica de prototipado",
            origen_programacion="adicional",
            participantes_seleccionados=json.dumps([self.participante.pk]),
            intencion_solicitud=INTENCION_DOCENCIA,
        )
        payload.update(self._payload_guia_integrada())
        payload["guias_actividad"] = [
            SimpleUploadedFile(
                "guia-practica-01.pdf",
                b"%PDF-1.4\n% guia de prueba",
                content_type="application/pdf",
            ),
            SimpleUploadedFile(
                "guia-practica-02.pdf",
                b"%PDF-1.4\n% segunda guia",
                content_type="application/pdf",
            ),
        ]
        payload["permisos_descarga_guias"] = json.dumps([False, True])

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["guias_actividad"], 2)
        actividad = CatalogoActividadReserva.objects.get(
            nombre="Práctica de prototipado"
        )
        self.assertEqual(actividad.estado_publicacion, "revision")
        self.assertEqual(actividad.visibilidad, "participantes")
        self.assertEqual(actividad.codigo, "")
        self.assertEqual(
            actividad.responsable,
            self.docente.get_full_name() or self.docente.username,
        )
        # La descripcion obligatoria de la solicitud describe la actividad.
        self.assertEqual(actividad.descripcion, INTENCION_DOCENCIA)
        self.assertTrue(actividad.participantes_autorizados.filter(pk=self.docente.pk).exists())
        self.assertTrue(
            actividad.participantes_autorizados.filter(pk=self.participante.pk).exists()
        )
        guias = list(actividad.guias.filter(es_estructurada=False).order_by("orden"))
        guia = guias[0]
        self.assertEqual(len(guias), 2)
        self.assertTrue(
            actividad.guias.filter(es_estructurada=True, estado_publicacion="revision").exists()
        )
        plan = PlanificacionPractica.objects.get(
            reserva_id=response.json()["reserva_id"],
        )
        self.assertTrue(plan.requiere_guia)
        self.assertIsNone(plan.guia)
        self.assertEqual(plan.estado, "borrador")
        self.assertEqual(guia.visibilidad, "participantes")
        self.assertEqual(guia.estado_publicacion, "publicada")
        self.assertFalse(guia.permite_descarga)
        self.assertTrue(guias[1].permite_descarga)
        self.assertEqual(guia.titulo, actividad.nombre)
        self.assertEqual(guias[1].titulo, actividad.nombre)
        self.assertTrue(all(len(item.titulo) <= 30 for item in guias))
        self.assertEqual(guia.descripcion, actividad.descripcion)

        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        pagina_pendiente = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(
            pagina_pendiente,
            reverse("ver_guia_actividad", args=[guia.pk]),
        )
        # La guía estructurada está completa y enviada: permite aprobar la
        # reserva, aunque todavía debe publicarse antes de iniciar la ejecución.
        reserva.confirmar(self.usuario)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")

        self.client.force_login(self.participante)
        permitida = self.client.get(reverse("ver_guia_actividad", args=[guia.pk]))
        self.assertEqual(permitida.status_code, 200)
        for closer in permitida._resource_closers:
            closer()
        descarga_bloqueada = self.client.get(
            reverse("ver_guia_actividad", args=[guia.pk]),
            {"download": "1"},
        )
        self.assertEqual(descarga_bloqueada.status_code, 403)
        descarga_permitida = self.client.get(
            reverse("ver_guia_actividad", args=[guias[1].pk]),
            {"download": "1"},
        )
        self.assertEqual(descarga_permitida.status_code, 200)
        self.assertTrue(descarga_permitida["Content-Disposition"].startswith("attachment;"))
        for closer in descarga_permitida._resource_closers:
            closer()

        usuario_ajeno = get_user_model().objects.create_user(
            username="usuario.sin.actividad",
            password="prueba-segura",
        )
        self.client.force_login(usuario_ajeno)
        denegada = self.client.get(reverse("ver_guia_actividad", args=[guia.pk]))
        self.assertEqual(denegada.status_code, 404)

    def test_actividad_docente_nueva_exige_confirmar_la_guia_integrada(self):
        self.client.force_login(self.docente)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="manual",
                referencia_actividad="Práctica docente sin guía",
                origen_programacion="adicional",
            ),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("confirma su contenido", response.json()["error"])
        self.assertFalse(
            CatalogoActividadReserva.objects.filter(
                nombre="Práctica docente sin guía"
            ).exists()
        )

    def test_estudiante_no_puede_forzar_la_creacion_de_una_guia(self):
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            alcance_beneficiario="perfil_solicitante",
            vinculacion_actividad="manual",
            referencia_actividad="Guía creada por estudiante",
            origen_programacion="adicional",
        )
        payload.update(self._payload_guia_integrada())

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("perfil no puede crear guías", response.json()["error"])
        self.assertFalse(
            CatalogoActividadReserva.objects.filter(
                nombre="Guía creada por estudiante"
            ).exists()
        )

    def test_actividad_docente_nueva_guarda_guia_completa_y_la_envia_a_revision(self):
        self.client.force_login(self.docente)
        payload = self._payload_reserva(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            alcance_beneficiario="perfil_solicitante",
            vinculacion_actividad="manual",
            referencia_actividad="Práctica docente integrada",
            origen_programacion="adicional",
            tipo_solicitud="recursos",
            solicito_equipo="true",
            solicito_software="true",
            software_solicitado=[str(self.software.pk)],
            provision_consumibles="unidad",
            consumibles_seleccionados=json.dumps([
                {
                    "id": self.material.pk,
                    "cantidad": "1.250",
                    "metodo_estimacion": "estimacion",
                }
            ]),
        )
        payload.update(self._payload_guia_integrada())

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        actividad = CatalogoActividadReserva.objects.get(
            nombre="Práctica docente integrada"
        )
        guia = GuiaActividadReserva.objects.get(
            actividad=actividad,
            es_estructurada=True,
        )
        self.assertEqual(guia.estado_publicacion, "revision")
        self.assertEqual(actividad.estado_publicacion, "revision")
        self.assertEqual(guia.secciones_faltantes(), [])
        self.assertTrue(guia.permite_descarga)
        self.assertEqual(
            guia.contenido["procedimiento"],
            [
                "Verificar el área y el equipo",
                "Preparar el archivo",
                "Ejecutar la fabricación",
                "Registrar resultados",
            ],
        )
        self.assertEqual(
            guia.contenido["reserva_fuente_id"], response.json()["reserva_id"]
        )
        self.assertEqual(
            guia.contenido["reserva_fuente_codigo"],
            response.json()["numero_referencia"],
        )
        self.assertTrue(
            any(self.unidad_equipo.codigo_unidad in item for item in guia.contenido["equipos"])
        )
        self.assertEqual(guia.contenido["software"], [self.software.nombre])
        self.assertTrue(
            any(self.material.nombre in item and "1.250 kg" in item for item in guia.contenido["materiales"])
        )
        self.assertEqual(guia.contenido["reactivos"], "")
        self.assertIn("El laboratorio clasificará", guia.contenido["manejo_residuos"])
        self.assertNotIn("Separar residuos aprovechables", guia.contenido["manejo_residuos"])
        self.assertIn(
            "Usar los elementos de protección definidos",
            guia.contenido["medidas_seguridad"],
        )
        self.assertEqual(
            guia.contenido["firma_elaborador"]["usuario_id"],
            self.docente.pk,
        )
        self.assertEqual(
            len(guia.contenido["firma_elaborador"]["huella_sha256"]),
            64,
        )
        self.assertTrue(response.json()["guia_estructurada"]["creada"])
        self.assertFalse(response.json()["requiere_accion_documental"])
        self.assertEqual(response.json()["siguiente_paso"], "comprobante")
        self.assertEqual(
            response.json()["siguiente_url"], response.json()["comprobante_url"]
        )
        comprobante = self.client.get(response.json()["comprobante_url"])
        self.assertEqual(comprobante.status_code, 200)
        self.assertContains(comprobante, "Guía en revisión")
        self.assertContains(comprobante, "Ver guía enviada")
        self.assertContains(comprobante, response.json()["numero_referencia"])
        self.assertContains(
            comprobante,
            reverse("ver_guia_actividad", args=[guia.pk]),
        )

    def test_nombre_corto_de_actividad_docente_admite_hasta_30_caracteres(self):
        self.client.force_login(self.docente)
        payload = self._payload_reserva(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            alcance_beneficiario="perfil_solicitante",
            vinculacion_actividad="manual",
            referencia_actividad="A" * 121,
            origen_programacion="adicional",
        )
        payload["guias_actividad"] = SimpleUploadedFile(
            "guia-practica.pdf",
            b"%PDF-1.4\n% guia de prueba",
            content_type="application/pdf",
        )

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("hasta 120 caracteres", response.json()["error"])

    def test_guia_publicada_aparece_en_recursos_y_practicas_y_se_puede_abrir(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica de corte láser",
            codigo="FAB-GUIA-001",
            unidad=self.laboratorio,
            creado_por=self.usuario,
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía de corte y grabado láser",
            archivo=SimpleUploadedFile(
                "guia-corte-laser.pdf",
                b"%PDF-1.4\n% guia publica de prueba\n",
                content_type="application/pdf",
            ),
            visibilidad="publica",
            estado_publicacion="publicada",
            permite_descarga=True,
            subido_por=self.usuario,
        )

        pagina = self.client.get(self.laboratorio.get_absolute_url())

        self.assertEqual(pagina.status_code, 200)
        # La sección 3.1 «Guías de práctica» del laboratorio solo lista aprobadas.
        self.assertContains(pagina, 'data-seccion="4.1"')
        self.assertContains(pagina, f"<strong>{guia.titulo}</strong>")
        self.assertContains(pagina, actividad.nombre)
        self.assertContains(pagina, reverse("ver_guia_actividad", args=[guia.pk]))

        visor = self.client.get(reverse("ver_guia_actividad", args=[guia.pk]))
        self.assertEqual(visor.status_code, 200)
        self.assertEqual(visor["Content-Disposition"], 'inline; filename="guia-corte-laser.pdf"')
        for closer in visor._resource_closers:
            closer()
        descarga = self.client.get(
            reverse("ver_guia_actividad", args=[guia.pk]),
            {"download": "1"},
        )
        self.assertEqual(descarga.status_code, 200)
        self.assertTrue(descarga["Content-Disposition"].startswith("attachment;"))
        for closer in descarga._resource_closers:
            closer()

    def test_el_borrador_ajeno_no_desvia_la_reserva_a_un_editor_prohibido(self):
        """La reserva se apoya en la guía publicada, no en el borrador del autor.

        Una actividad del catálogo puede tener una versión publicada y, encima,
        una revisión que su docente todavía escribe. A quien reserva le
        corresponde la publicada: mandarlo a terminar el borrador ajeno lo
        dejaba en un 404 después de enviar la solicitud.
        """
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica evaluativa con versión en curso",
            codigo="FAB-GUIA-VERSIONES",
            unidad=self.laboratorio,
            creado_por=self.docente,
            estado_publicacion="publicado",
            visibilidad="unidad",
            periodo_academico="2026-B",
        )
        publicada = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía publicada de la práctica",
            codigo_guia="GUIA-VER-01",
            numero_version=1,
            es_estructurada=True,
            es_vigente=True,
            contenido={"laboratorio": self.laboratorio.nombre},
            visibilidad="unidad",
            estado_publicacion="publicada",
            subido_por=self.docente,
        )
        borrador = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía publicada de la práctica",
            codigo_guia="GUIA-VER-01",
            numero_version=2,
            es_estructurada=True,
            contenido={"laboratorio": self.laboratorio.nombre},
            visibilidad="unidad",
            estado_publicacion="borrador",
            subido_por=self.docente,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        datos = response.json()
        self.assertEqual(datos["guia_estructurada"]["id"], publicada.pk)
        self.assertEqual(datos["guia_estructurada"]["url_edicion"], "")
        self.assertFalse(datos["requiere_accion_documental"])
        self.assertEqual(datos["siguiente_paso"], "comprobante")
        self.assertEqual(datos["siguiente_url"], datos["comprobante_url"])
        # El editor sigue cerrado para quien no escribió el borrador.
        editor = self.client.get(
            reverse("editar_guia_practica", args=[self.laboratorio.slug, borrador.pk])
        )
        self.assertEqual(editor.status_code, 404)
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado_publicacion, "borrador")

    def test_guia_estructurada_usa_la_vista_pdf_en_el_visualizador(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica estructurada de impresión FDM",
            codigo="FAB-GUIA-FDM",
            unidad=self.laboratorio,
            creado_por=self.usuario,
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía estructurada FDM",
            codigo_guia="GUIA-FDM-01",
            numero_version=2,
            es_estructurada=True,
            es_vigente=True,
            contenido={"laboratorio": self.laboratorio.nombre},
            visibilidad="publica",
            estado_publicacion="publicada",
            permite_descarga=True,
            subido_por=self.usuario,
        )

        pagina = self.client.get(self.laboratorio.get_absolute_url())

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(
            pagina,
            f"{reverse('ver_guia_actividad', args=[guia.pk])}?preview=pdf",
        )
        self.assertContains(pagina, f"guia-practica-{guia.pk}-v2.pdf")

        # La consola abre el modal compartido, que monta el mismo visor de la
        # vista previa de documentos; ambos componentes se cargan en la página.
        self.assertContains(pagina, 'data-aula-pdf-modal')
        self.assertContains(pagina, 'portal/js/components/visor_pdf_modal.js')
        self.assertContains(pagina, 'portal/js/components/visor_pdf.js')
        consola = finders.find("portal/js/pages/unidades/detalle/gestor_contenido.js")
        with open(consola, encoding="utf-8") as script:
            contenido_consola = script.read()
        self.assertIn("window.visorPdfModal.abrir(enlace,", contenido_consola)
        self.assertIn("enlace.href = url;", contenido_consola)
        self.assertIn("enlace.dataset.pdfDescarga = url;", contenido_consola)
        modal_path = finders.find("portal/js/components/visor_pdf_modal.js")
        with open(modal_path, encoding="utf-8") as script:
            contenido_modal = script.read()
        self.assertIn("window.VisorPdf.montar(marco, direccion, opcionesVisor)", contenido_modal)
        self.assertIn("abrir:mostrarEnContexto", contenido_modal)

        script_path = finders.find("portal/js/components/visor_pdf.js")
        with open(script_path, encoding="utf-8") as script:
            contenido_visor = script.read()
        self.assertIn("window.devicePixelRatio", contenido_visor)
        self.assertIn("const dibujarTodo", contenido_visor)
        self.assertIn("new ResizeObserver", contenido_visor)
        # En el telefono se amplia con dos dedos y en el escritorio con la barra.
        self.assertIn("touchmove", contenido_visor)
        self.assertIn("pdf-viewer-zoom", contenido_visor)

        vista_pdf = self.client.get(
            reverse("ver_guia_actividad", args=[guia.pk]),
            {"preview": "pdf"},
        )
        self.assertEqual(vista_pdf.status_code, 200)
        self.assertEqual(vista_pdf["Content-Type"], "application/pdf")
        self.assertTrue(vista_pdf["Content-Disposition"].startswith("inline;"))
        self.assertTrue(vista_pdf.content.startswith(b"%PDF"))

    def test_reserva_semanal_crea_serie_y_sesiones_concretas_del_periodo(self):
        periodo = PeriodoAcademico.objects.create(
            codigo="2026-B",
            nombre="Periodo académico 2026-B",
            anio_referencia=2026,
            ciclo="B",
            tipo="ordinario",
            ambito="carreras_centros",
            semanas_planificadas=16,
            estado="publicado",
        )
        version = VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            nombre="Calendario de pruebas",
            fecha_inicio_clases=date(2026, 8, 31),
            fecha_fin_clases=date(2026, 9, 20),
            fecha_fin_periodo=date(2026, 9, 30),
            vigente=True,
        )
        for numero, inicio in enumerate(
            (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14)),
            start=1,
        ):
            SemanaAcademica.objects.create(
                version_calendario=version,
                numero=numero,
                fecha_inicio=inicio,
                fecha_fin=date.fromordinal(inicio.toordinal() + 6),
                permite_reservas=True,
            )
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica semanal de manufactura",
            codigo="FAB-DOC-SEM-001",
            unidad=self.laboratorio,
            periodo=periodo,
            responsable="Docente responsable",
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía semanal de manufactura",
            archivo=SimpleUploadedFile(
                "guia-semanal-manufactura.pdf",
                b"%PDF-1.4\n% guia semanal\n",
                content_type="application/pdf",
            ),
            estado_publicacion="publicada",
            visibilidad="unidad",
            subido_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                fecha_inicio="2026-09-01T09:00",
                fecha_fin="2026-09-01T11:00",
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
                frecuencia_reserva="semanal_periodo",
                participantes_seleccionados=json.dumps([self.participante.pk]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["sesiones_creadas"], 3)
        programacion = ProgramacionReserva.objects.get(pk=response.json()["programacion_id"])
        self.assertEqual(programacion.total_sesiones, 3)
        self.assertEqual(programacion.sesiones.count(), 3)
        self.assertEqual(
            list(programacion.sesiones.order_by("fecha").values_list("fecha", flat=True)),
            [date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15)],
        )
        self.assertEqual(
            programacion.sesiones.exclude(semana_academica_numero__isnull=True).count(),
            3,
        )

        # La cantidad indicada es la de una sesion: cada sesion registra esa
        # cantidad y el programa completo se valora por las tres.
        self.material.precio_unitario = Decimal("2.0000")
        self.material.save(update_fields=["precio_unitario"])
        respuesta = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                # Bloque que no toca la hora de almuerzo (13:00-14:00).
                fecha_inicio="2026-09-01T14:00",
                fecha_fin="2026-09-01T16:00",
                horas_seleccionadas=json.dumps([14, 15]),
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
                frecuencia_reserva="semanal_periodo",
                participantes_seleccionados=json.dumps([self.participante.pk]),
                provision_consumibles="unidad",
                consumibles_seleccionados=json.dumps([{
                    "id": self.material.pk,
                    "cantidad": "3",
                    "metodo_estimacion": "estimacion",
                }]),
            ),
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        principal = Reserva.objects.get(pk=respuesta.json()["reserva_id"])
        programa = principal.desglose_cotizacion["programa"]
        self.assertEqual(programa["sesiones"], 3)
        # 3 unidades por sesion × 3 sesiones × $2.00.
        self.assertEqual(principal.desglose_cotizacion["total_insumos"], "18.00")
        self.assertEqual(
            principal.consumibles_solicitados.get().cantidad_solicitada,
            Decimal("3.000"),
        )
        ultima = principal.programacion.sesiones.order_by("fecha").last()
        self.assertEqual(ultima.consumibles_solicitados.get().cantidad_solicitada, Decimal("3.000"))
        comprobante = self.client.get(reverse("comprobante_reserva", args=[principal.pk]))
        self.assertContains(comprobante, "Programa de 3 sesiones de 2 h")
        self.assertContains(comprobante, "las cantidades de insumos son por sesión")
        self.assertContains(comprobante, "Sin cambios posteriores a la solicitud original")

        # Un cambio aprobado recalcula la estimacion de esa sesion y deja rastro.
        from apps.reservas.presentation.cotizaciones import recalcular_estimacion_reserva
        sesion = ultima
        registro = sesion.consumibles_solicitados.get()
        registro.cantidad_solicitada = Decimal("5")
        registro.save(update_fields=["cantidad_solicitada"])
        recalcular_estimacion_reserva(sesion)
        sesion.refresh_from_db()
        self.assertEqual(sesion.costo_estimado, Decimal("10.00"))
        self.assertTrue(sesion.desglose_cotizacion["programa"]["sesion_modificada"])
        self.assertEqual(sesion.desglose_cotizacion["programa"]["sesiones"], 3)

    def test_reserva_semanal_sin_guia_crea_sesiones_independientes(self):
        periodo = PeriodoAcademico.objects.create(
            codigo="2026-B-SIN-GUIA",
            nombre="Período para reservas sin guía",
            anio_referencia=2026,
            ciclo="B",
            tipo="ordinario",
            ambito="carreras_centros",
            semanas_planificadas=16,
            estado="publicado",
        )
        version = VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            nombre="Calendario sin guía",
            fecha_inicio_clases=date(2026, 8, 31),
            fecha_fin_clases=date(2026, 9, 20),
            fecha_fin_periodo=date(2026, 9, 30),
            vigente=True,
        )
        for numero, inicio in enumerate(
            (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14)),
            start=1,
        ):
            SemanaAcademica.objects.create(
                version_calendario=version,
                numero=numero,
                fecha_inicio=inicio,
                fecha_fin=date.fromordinal(inicio.toordinal() + 6),
                permite_reservas=True,
            )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                fecha_inicio="2026-09-01T09:00",
                fecha_fin="2026-09-01T11:00",
                # Toda docencia exige guia; la serie sin guia es de capacitacion.
                proposito_codigo="capacitacion",
                subtipo_actividad="taller",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="independiente",
                frecuencia_reserva="semanal_periodo",
                participantes_seleccionados=json.dumps([self.participante.pk]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["sesiones_creadas"], 3)
        programacion = ProgramacionReserva.objects.get(pk=response.json()["programacion_id"])
        self.assertIsNone(programacion.actividad)
        self.assertEqual(programacion.sesiones.count(), 3)
        self.assertFalse(GuiaActividadReserva.objects.exists())
        self.assertEqual(response.json()["planificaciones_creadas"], 3)
        self.assertEqual(
            PlanificacionPractica.objects.filter(
                reserva__programacion=programacion,
            ).count(),
            3,
        )
        self.assertFalse(
            PlanificacionPractica.objects.filter(
                reserva__programacion=programacion,
                requiere_guia=True,
            ).exists()
        )
        self.assertTrue(
            all(
                reserva.vinculacion_actividad == "independiente"
                for reserva in programacion.sesiones.all()
            )
        )

    def test_reserva_semanal_hasta_fecha_crea_solo_el_rango_solicitado(self):
        periodo = PeriodoAcademico.objects.create(
            codigo="2026-B-RANGO",
            nombre="Período académico para rango semanal",
            anio_referencia=2026,
            ciclo="B",
            tipo="ordinario",
            ambito="carreras_centros",
            semanas_planificadas=16,
            estado="publicado",
        )
        version = VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            nombre="Calendario para rango semanal",
            fecha_inicio_clases=date(2026, 8, 31),
            fecha_fin_clases=date(2026, 9, 20),
            fecha_fin_periodo=date(2026, 9, 30),
            vigente=True,
        )
        for numero, inicio in enumerate(
            (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14)),
            start=1,
        ):
            SemanaAcademica.objects.create(
                version_calendario=version,
                numero=numero,
                fecha_inicio=inicio,
                fecha_fin=date.fromordinal(inicio.toordinal() + 6),
                permite_reservas=True,
            )
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica con rango semanal",
            codigo="FAB-DOC-RANGO-001",
            unidad=self.laboratorio,
            periodo=periodo,
            responsable="Docente responsable",
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía para rango semanal",
            archivo=SimpleUploadedFile(
                "guia-rango-semanal.pdf",
                b"%PDF-1.4\n% guia rango semanal\n",
                content_type="application/pdf",
            ),
            estado_publicacion="publicada",
            visibilidad="unidad",
            subido_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                fecha_inicio="2026-09-01T09:00",
                fecha_fin="2026-09-01T11:00",
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
                frecuencia_reserva="semanal_rango",
                fecha_fin_recurrencia="2026-09-08",
                participantes_seleccionados=json.dumps([self.participante.pk]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["sesiones_creadas"], 2)
        programacion = ProgramacionReserva.objects.get(
            pk=response.json()["programacion_id"]
        )
        self.assertEqual(programacion.frecuencia, "semanal_rango")
        self.assertEqual(programacion.fecha_fin, date(2026, 9, 8))
        self.assertEqual(
            list(
                programacion.sesiones.order_by("fecha").values_list(
                    "fecha", flat=True
                )
            ),
            [date(2026, 9, 1), date(2026, 9, 8)],
        )

    def test_reserva_docente_semanal_exige_participantes_registrados(self):
        periodo = PeriodoAcademico.objects.create(
            codigo="2026-B-SIN-PART",
            nombre="Período semanal sin participantes",
            anio_referencia=2026,
            ciclo="B",
            tipo="ordinario",
            ambito="carreras_centros",
            semanas_planificadas=16,
            estado="publicado",
        )
        version = VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            nombre="Calendario sin participantes",
            fecha_inicio_clases=date(2026, 8, 31),
            fecha_fin_clases=date(2026, 9, 13),
            fecha_fin_periodo=date(2026, 9, 20),
            vigente=True,
        )
        for numero, inicio in enumerate(
            (date(2026, 8, 31), date(2026, 9, 7)),
            start=1,
        ):
            SemanaAcademica.objects.create(
                version_calendario=version,
                numero=numero,
                fecha_inicio=inicio,
                fecha_fin=date.fromordinal(inicio.toordinal() + 6),
                permite_reservas=True,
            )
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica semanal sin participantes",
            codigo="FAB-DOC-SEM-002",
            unidad=self.laboratorio,
            periodo=periodo,
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo="Guía de la programación docente",
            archivo=SimpleUploadedFile(
                "guia-programacion-docente.pdf",
                b"%PDF-1.4\n% guia docente\n",
                content_type="application/pdf",
            ),
            estado_publicacion="publicada",
            visibilidad="unidad",
            subido_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                fecha_inicio="2026-09-01T09:00",
                fecha_fin="2026-09-01T11:00",
                proposito_codigo="docencia_practica",
                subtipo_actividad="practica_curricular",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="catalogo",
                actividad_catalogo=str(actividad.pk),
                origen_programacion="programada",
                frecuencia_reserva="semanal_periodo",
                participantes_seleccionados="[]",
            ),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("participante registrado", response.json()["error"])
        self.assertFalse(ProgramacionReserva.objects.exists())

    def test_toda_actividad_docente_exige_guia(self):
        self.client.force_login(self.usuario)

        for subtipo in ("simulacion_demostracion", "practica_evaluativa", "taller_docente"):
            with self.subTest(subtipo=subtipo):
                response = self.client.post(
                    reverse("crear_reserva"),
                    self._payload_reserva(
                        proposito_codigo="docencia_practica",
                        subtipo_actividad=subtipo,
                        alcance_beneficiario="perfil_solicitante",
                        vinculacion_actividad="independiente",
                        origen_programacion="adicional",
                    ),
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("actividad docente", response.json()["error"])
        self.assertFalse(Reserva.objects.exists())

    def test_propositos_no_docentes_permiten_reserva_puntual_sin_actividad_ni_guia(self):
        self.client.force_login(self.usuario)

        casos = (
            ("investigacion_innovacion", "proyecto_investigacion", {}),
            ("vinculacion", "proyecto_vinculacion", {}),
            ("capacitacion", "curso", {}),
            ("servicio_cientifico_tecnologico", "servicio_autorizado", {}),
            ("titulacion", "trabajo_titulacion", {}),
            ("otro", "otro", {"detalle_otro_proposito": "Uso puntual autorizado"}),
        )
        for proposito, subtipo, extras in casos:
            with self.subTest(proposito=proposito):
                response = self.client.post(
                    reverse("crear_reserva"),
                    self._payload_reserva(
                        proposito_codigo=proposito,
                        subtipo_actividad=subtipo,
                        alcance_beneficiario="perfil_solicitante",
                        vinculacion_actividad="independiente",
                        **extras,
                    ),
                )

                self.assertEqual(response.status_code, 200, response.content)
                reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
                self.assertEqual(reserva.vinculacion_actividad, "independiente")
                self.assertEqual(reserva.referencia_actividad, "")
                self.assertIsNone(reserva.actividad_catalogo)
                plan = PlanificacionPractica.objects.get(reserva=reserva)
                self.assertFalse(plan.requiere_guia)
                self.assertEqual(plan.estado, "revision")
                reserva.delete()
                plan.delete()
        self.assertFalse(GuiaActividadReserva.objects.exists())

    def test_no_permite_reservar_recursos_de_otra_unidad(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(self.unidad_ajena),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("ya no están disponibles", response.json()["error"])
        self.assertFalse(Reserva.objects.exists())

    def test_detalle_muestra_catalogo_explicito_de_materiales(self):
        response = self.client.get(self.laboratorio.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insumos y materiales del laboratorio")
        self.assertContains(response, "Insumos")
        self.assertContains(response, "Materiales")
        self.assertContains(response, "Resinas para impresión 3D")
        self.assertContains(response, "Vidriería")
        self.assertContains(response, self.material_apoyo.nombre)
        self.assertContains(response, self.material.nombre)
        self.assertContains(response, self.material.codigo)
        self.assertContains(response, self.material.lote)
        self.assertContains(response, self.material.familia)
        self.assertContains(response, self.material.color)
        # La cantidad se pide siempre: ya no hay manera de dejarla en blanco.
        self.assertContains(response, "Obligatoria: escribe la cantidad que consume una pieza")
        self.assertContains(response, "data-quantity-total")
        self.assertNotContains(response, "No conozco la cantidad")
        self.assertNotContains(response, "estimación previa")
        # Reservar solo el espacio se declara y se confirma antes de continuar.
        self.assertContains(response, 'id="avisoAlcanceRecursos"')
        self.assertContains(response, "Esto es lo que vas a solicitar")
        self.assertContains(response, "data-scope-confirm")
        # Las piezas y el detalle del trabajo se declaran en cada equipo.
        self.assertContains(response, 'id="plantillaTrabajoEquipo"')
        self.assertContains(response, "data-equipment-pieces")
        self.assertContains(response, "data-equipment-detail")
        self.assertContains(response, 'data-detalle="')
        self.assertNotContains(response, "reservation-consumable__method")
        # Insumos como tarjetas con detalles desplegables (sin tabla).
        self.assertContains(response, "reservation-consumable-list")
        self.assertContains(response, 'data-item-toggle')
        self.assertContains(response, 'data-stock-note')
        self.assertNotContains(response, "reservation-materials-table")
        self.assertContains(response, "data-material-image")
        self.assertContains(response, self.material.imagen_catalogo)
        self.assertNotContains(response, self.material_ajeno.nombre)
        self.assertContains(response, "Software y licencias")
        self.assertContains(response, self.software.nombre)
        self.assertContains(response, "Estudiantes o participantes que asistirán")
        self.assertContains(response, "Propósito institucional de la solicitud")
        self.assertContains(response, "Nombre inteligente de tu solicitud")
        self.assertNotContains(response, "Cantidad de participantes")
        self.assertContains(response, "Cuánto costará este trabajo")
        self.assertContains(response, "Confirma el valor estimado y cómo pagarás")

    def test_asistente_publica_un_solo_contrato_versionado_y_sin_cache(self):
        response = self.client.get(self.laboratorio.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Cache-Control"],
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertEqual(response.headers["Expires"], "0")

        html = response.content.decode()
        self.assertEqual(html.count('<form id="reservaForm"'), 1)
        # El selector de idioma y el rango de páginas del visor de PDF son formularios independientes de la reserva.
        self.assertEqual(html.count('data-language-switch'), 1)
        self.assertEqual(html.count('<form class="aula-pdf-modal__rango"'), 1)
        self.assertEqual(html.count("<form"), 3)
        for element_id in (
            "equiposReservaModal",
            "reservaForm",
            "solicitantePrincipal",
            "participantesReserva",
            "propositoReserva",
            "vinculacionActividadCampo",
            "tituloAutomaticoReserva",
            "descripcionProyecto",
            "softwareReservaCatalogo",
        ):
            with self.subTest(element_id=element_id):
                self.assertEqual(html.count(f'id="{element_id}"'), 1)

        # La version del contrato se lee del HTML; la prueba exige que el JS la
        # comparta, sin fijar un literal que obligue a editarla en cada cambio.
        construccion = re.search(r'data-reservation-build="([^"]+)"', html)
        self.assertIsNotNone(construccion)
        self.assertRegex(construccion.group(1), r"^\d{8}-[a-z0-9-]+-v\d+$")
        self.assertIn('data-reservas-software="true"', html)
        self.assertIn('data-resource-illustration-url="/static/portal/img/reservas/reservar-recursos-v1.webp"', html)
        self.assertIn('data-service-illustration-url="/static/portal/img/reservas/encargar-servicio-v1.webp"', html)
        self.assertIn('data-space-resource-image-url="/static/img/generated/home-hero/hero-fabricacion-avanzada.png"', html)
        self.assertIn('data-equipment-resource-image-url="/static/img/catalogo/fablab/equipos/impresora-3d-fdm.png"', html)
        self.assertIn('data-software-resource-image-url="/static/img/generated/platforms/software-analytics.png"', html)
        self.assertIn('data-resource-tutorial-url="https://www.youtube.com/watch?v=Vcxz9ss2MAs"', html)
        self.assertIn('data-service-tutorial-url="https://www.youtube.com/watch?v=wWa1sYdW1BU"', html)
        self.assertIsNotNone(finders.find("portal/img/reservas/reservar-recursos-v1.webp"))
        self.assertIsNotNone(finders.find("portal/img/reservas/encargar-servicio-v1.webp"))

        script_path = finders.find(
            "portal/js/pages/unidades/reservas/reservation_wizard.js"
        )
        with open(script_path, encoding="utf-8") as script:
            contenido = script.read()
        # Se conserva el contrato de valores; gettext solo envuelve las etiquetas.
        contenido = re.sub(r'''gettext\((('(?:[^'\\]|\\.)*')|("(?:[^"\\]|\\.)*"))\)''', r'\1', contenido)

        self.assertIn(f"const EXPECTED_BUILD = '{construccion.group(1)}'", contenido)
        self.assertIn("safelyMove(integratedCalendar, 'frecuenciaReservaCampo')", contenido)
        self.assertIn("element('monthGrid')?.closest('.cal-box')", contenido)
        self.assertIn('id="contextoActividadReserva"', html)
        self.assertIn('name="proposito_codigo"', html)
        self.assertIn('name="vinculacion_actividad"', html)
        self.assertIn('value="independiente"', html)
        self.assertIn('id="actividadCatalogoDetalle"', html)
        self.assertIn("function updatePurposeContext", contenido)
        self.assertIn("function updateActivityLinkContext", contenido)
        self.assertIn("function suggestedActivityName()", contenido)
        self.assertIn("function refreshFinalActivityIdentity", contenido)
        self.assertIn("id = 'identificacionFinalActividad'", contenido)
        self.assertIn("data-use-activity-suggestion", contenido)
        self.assertIn("Completar campos sugeridos", contenido)
        self.assertIn("function applyGuideSuggestions()", contenido)
        self.assertIn("canAuthorGuides ? manualInput", contenido)
        self.assertNotIn('id="actividadDocenteDirecta"', html)
        self.assertIn('Nombre corto de la actividad o guía', html)
        self.assertIn('maxlength="120"', html)
        self.assertIn('id="referenciaActividadAyuda"', html)
        self.assertIn("activityReferenceInput.maxLength", contenido)
        self.assertIn("Hasta 120 caracteres", contenido)
        self.assertNotIn('id="codigoReferenciaCampo"', html)
        self.assertNotIn('id="responsableActividadCampo"', html)
        self.assertIn('id="guiasActividadInput"', html)
        self.assertIn('id="permisosDescargaGuias"', html)
        self.assertIn('id="guiasActividadAccion"', html)
        self.assertNotIn('id="guiaActividadPreviewFrame"', html)
        self.assertIn('data-aula-pdf-modal', html)
        self.assertIn("function previewActivityGuide(file)", contenido)
        self.assertIn("URL.createObjectURL(file)", contenido)
        self.assertIn("activityGuideFiles = [...activityGuideFiles, ...added]", contenido)
        self.assertIn("function syncActivityGuidePermissions()", contenido)
        self.assertIn("Solo visualización", contenido)
        self.assertIn("previewActivityGuide(added[0])", contenido)
        self.assertNotIn("directTeachingFlow && !selectedActivityLink()", contenido)
        self.assertIn("No utilizaré guía", html)
        # La pregunta sobre la guia solo aparece en practica curricular; el resto
        # de docencia decide al final con el interruptor "Generar guia".
        self.assertIn(
            "activityLinkField.hidden = !(directTeachingFlow && curricularPractice)", contenido
        )
        self.assertNotIn("guideIsOptionalHere", contenido)
        self.assertIn("['taller_docente', 'Taller práctico de asignatura']", contenido)
        self.assertNotIn("Reserva puntual sin documentos", contenido)
        self.assertIn("const independentAllowed = Boolean(purpose) && !curricularPractice", contenido)
        self.assertIn("independentAllowed && !directTeachingFlow", contenido)
        self.assertIn("input.checked = input === independentInput", contenido)
        self.assertIn("updatePurposeContext({ reset: true })", contenido)
        self.assertIn("Este propósito no requiere guías", contenido)
        self.assertIn("const usesTeachingGuides = false", contenido)
        self.assertIn("if (activityGuidesField) activityGuidesField.hidden = true", contenido)
        self.assertIn("El sistema creará una guía estructurada editable", contenido)
        self.assertIn("id = 'guiaPracticaIntegrada'", contenido)
        self.assertNotIn("purposeContextGrid.insertBefore(\n        guideBuilder", contenido)
        self.assertIn("requirementsCard.appendChild(guideBuilder)", contenido)
        self.assertIn("id = 'revisionFinalGuiaIntegrada'", contenido)
        # La guia se redacta sobre su propio formato en el dialogo "Revisar y completar guia".
        self.assertNotIn("Visualizar guía completa en HTML", contenido)
        self.assertIn("Revisar y completar guía", contenido)
        self.assertIn("function ensureGuideEditor()", contenido)
        self.assertIn('name="guia_formato_contenido" value="html"', contenido)
        self.assertIn('name="guia_resultado_aprendizaje"', contenido)
        self.assertIn('name="guia_asignatura"', contenido)
        self.assertIn('name="guia_formato_procedimiento"', contenido)
        self.assertIn('name="guia_procedimiento"', contenido)
        self.assertIn('name="guia_confirmada_solicitante"', contenido)
        self.assertNotIn('name="guia_reactivos"', contenido)
        self.assertNotIn('name="guia_manejo_residuos"', contenido)
        # Las politicas automaticas se leen en el documento FT04 (apartados 06 y 09),
        # no en un bloque aparte del paso 4.
        self.assertNotIn('reservation-guide-builder__institutional-policy', contenido)
        self.assertIn('data-guide-auto="waste"', html)
        self.assertIn("is-equipment-incompatible", contenido)
        self.assertIn('id="provisionConsumibles"', html)
        self.assertIn("function renderGuidePreview()", contenido)
        self.assertIn("function validateEmbeddedGuide", contenido)
        self.assertNotIn("if (!validateEmbeddedGuide({ requireAcceptance: false })) return", contenido)
        self.assertIn("Apartados obligatorios por completar", contenido)
        self.assertIn("guidePreviewAccept.disabled = Boolean(missing.length) || pending > 0", contenido)
        self.assertIn("resources.appendChild(primaryResourceChoices)", contenido)
        self.assertIn("resources.appendChild(serviceCatalog)", contenido)
        self.assertNotIn("typeCard.appendChild(primaryResourceChoices)", contenido)
        self.assertIn("Software y licencias", contenido)
        self.assertIn("Equipos, software e insumos no se vuelven a escribir", contenido)
        # Resultado de aprendizaje, objetivos y procedimiento; la asignatura se
        # pide en la identificacion de la actividad, fuera del constructor.
        self.assertEqual(contenido.count("data-guide-required data-guide-label="), 3)
        self.assertIn('data-final-subject-field><span>Asignatura o módulo formativo *</span>', contenido)
        self.assertIn("Reservas y servicios", html)
        self.assertIn("Completa, revisa y confirma", contenido)
        self.assertIn(
            "purposeContextGrid && !element('vinculacionActividadCampo')",
            contenido,
        )
        self.assertIn("const resourceChoiceImages = {", contenido)
        self.assertIn("rw-resource-choice__visual", contenido)
        self.assertIn(
            "if (!force && target > state.step && !validateStep(state.step)) return;",
            contenido,
        )
        self.assertIn("button.disabled = isFutureStep", contenido)
        self.assertNotIn("window.location.replace", contenido)
        self.assertIn("modal.dataset.reservationBuild = EXPECTED_BUILD", contenido)
        self.assertIn("currentUrl.searchParams.delete('_reservation_build')", contenido)
        self.assertIn("0 participantes secundarios", html)
        self.assertIn("actividad docente semanal o de todo el período", html)
        self.assertIn("function showParticipantRequirement()", contenido)
        self.assertIn("showStep(2, true)", contenido)
        self.assertIn("Agrega al menos un estudiante o participante", contenido)
        self.assertIn("function selectedResourceCounts()", contenido)
        self.assertIn("function formatSchedule(dateValue, hoursValue)", contenido)
        self.assertIn("weekday: 'long'", contenido)
        self.assertIn("const schedule = formatSchedule(date, hours)", contenido)
        self.assertIn("frequency === 'semanal_periodo'", contenido)
        self.assertIn('value="semanal_rango"', html)
        self.assertIn('id="fechaFinRecurrencia"', html)
        self.assertIn(
            "Reserva de equipo${counts.equipment === 1 ? '' : 's'}",
            contenido,
        )

    def test_guia_integrada_acepta_apartados_complementarios_vacios(self):
        self.client.force_login(self.docente)
        payload = self._payload_reserva(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            alcance_beneficiario="perfil_solicitante",
            vinculacion_actividad="manual",
            referencia_actividad="Práctica con mínimo FT04",
            origen_programacion="adicional",
        )
        payload.update({
            "guia_asignatura": "Diseño y fabricación digital",
            "guia_resultado_aprendizaje": "Aplica el procedimiento de forma verificable.",
            "guia_objetivos": "Ejecutar correctamente la actividad propuesta.",
            "guia_formato_procedimiento": "vinetas",
            "guia_procedimiento": "Preparar recursos\nEjecutar actividad\nRegistrar resultado",
            "guia_confirmada_solicitante": "1",
        })

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        guia = GuiaActividadReserva.objects.get(
            actividad__nombre="Práctica con mínimo FT04",
            es_estructurada=True,
        )
        self.assertEqual(guia.estado_publicacion, "revision")
        self.assertEqual(guia.secciones_faltantes(), [])
        self.assertEqual(guia.contenido["asignatura"], "Diseño y fabricación digital")
        self.assertEqual(guia.contenido["formato_procedimiento"], "vinetas")
        self.assertEqual(guia.contenido["fundamento_teorico"], "")

    def test_asistente_retira_la_clase_que_ocultaba_el_catalogo_movido(self):
        script_path = finders.find(
            "portal/js/pages/unidades/reservas/reservation_wizard.js"
        )

        with open(script_path, encoding="utf-8") as script:
            contenido = script.read()

        self.assertIn(
            "node.classList.remove('reservation-legacy-region')",
            contenido,
        )

    def test_asistente_publica_servicios_guiados_y_sin_panel_lateral(self):
        servicio = FablabService.objects.create(
            code="FAB-GUIA",
            nombre="Fabricación guiada",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            resultado_entregado="Pieza terminada y revisada.",
            cuando_elegirlo="Necesitas fabricar un prototipo funcional.",
            tiempo_estimado_texto="Dos días laborables.",
            tutorial_titulo="Preparar el archivo técnico",
            tutorial_youtube_url="https://www.youtube.com/watch?v=xYzAbCdEf12",
        )

        response = self.client.get(self.laboratorio.get_absolute_url())

        self.assertContains(response, servicio.resultado_entregado)
        self.assertContains(response, servicio.cuando_elegirlo)
        self.assertContains(response, servicio.tiempo_estimado_texto)
        self.assertNotContains(response, servicio.tutorial_youtube_url)
        self.assertContains(response, 'name="incluye_espacio"')
        self.assertNotContains(response, "¿Cómo funciona?")
        self.assertNotContains(
            response,
            '<textarea class="form-control" id="descripcionProyecto"',
        )

        script_path = finders.find(
            "portal/js/pages/unidades/reservas/reservation_wizard.js"
        )
        with open(script_path, encoding="utf-8") as script:
            contenido = script.read()
        self.assertNotIn("rw-help", contenido)
        self.assertIn("Cómo reservar recursos", contenido)
        self.assertIn("Cómo encargar un servicio", contenido)
        # La ayuda vive dentro de cada tarjeta de ruta (preparacion y videotutorial),
        # sin bloque de orientacion aparte ni franja de pasos desplazable.
        self.assertNotIn("rw-onboarding", contenido)
        self.assertNotIn("rw-route", contenido)
        self.assertIn("Prepárate con:", contenido)
        self.assertIn("rw-type__tutorial", contenido)
        self.assertIn("const tutorialDescription = element('visorTutorialDescripcion')", contenido)
        self.assertIn("rw-type__visual", contenido)
        self.assertIn("types.querySelectorAll('[data-generic-tutorial]')", contenido)
        self.assertIn("Video demostrativo temporal", contenido)
        self.assertIn("Selecciona una fecha y al menos un bloque horario", contenido)
        self.assertIn("youtube-nocookie.com/embed/", contenido)
        self.assertIn("selectedMode.value === 'modelo_listo'", contenido)
        self.assertIn("renderTechnicalFiles", contenido)
        self.assertIn("applyServiceModeSelection(input, true)", contenido)
        self.assertIn("technicalFiles.hidden = false", contenido)
        self.assertIn("Carga preparada y conservada", contenido)
        self.assertContains(response, 'name="indicaciones_archivos"')
        self.assertContains(response, "Arrastra tus archivos aquí")
        self.assertContains(response, 'id="archivosTecnicosReserva" aria-live="polite"')

        calendar_script_path = finders.find(
            "portal/js/pages/unidades/reservas/modal_reserva_equipos.js"
        )
        with open(calendar_script_path, encoding="utf-8") as calendar_script:
            calendar_content = calendar_script.read()
        self.assertIn("view: 'week'", calendar_content)
        self.assertIn("rw-week-schedule", calendar_content)
        self.assertIn("data-calendar-slot", calendar_content)
        self.assertIn("selectCalendarSlot", calendar_content)
        self.assertIn("Las tarjetas muestran qué está reservado", calendar_content)
        self.assertIn("Agenda del día", calendar_content)
        self.assertIn("event.reservado_por", calendar_content)
        self.assertIn("debeMostrarDiaEnAgendaSemanal", calendar_content)
        self.assertIn("Jornada especial gestionada por la administración", calendar_content)
        self.assertIn("--rw-calendar-day-count", calendar_content)
        self.assertContains(response, 'data-reservation-admin="false"')

    def test_visor_de_materiales_supera_el_modal_y_limita_su_tamano(self):
        style_path = finders.find(
            "portal/css/pages/unidades/reservation_wizard.css"
        )

        with open(style_path, encoding="utf-8") as stylesheet:
            contenido = stylesheet.read()

        self.assertIn("z-index: 100100 !important", contenido)
        self.assertIn("width: min(460px, calc(100vw - 40px))", contenido)

    def test_servicio_no_permite_solicitar_inventario_como_reserva(self):
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            tipo_solicitud="servicio",
            provision_consumibles="unidad",
            unidades_seleccionadas="[]",
            consumibles_seleccionados=json.dumps([
                {"id": self.material.pk, "cantidad": "1.250"},
            ]),
        )

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("automáticamente", response.json()["error"])

    def test_cantidad_de_material_puede_quedar_para_revision_tecnica(self):
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            provision_consumibles="unidad",
            consumibles_seleccionados=json.dumps([
                {
                    "id": self.material.pk,
                    "cantidad": None,
                    "metodo_estimacion": "revision",
                },
            ]),
        )

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200)
        solicitado = Reserva.objects.get(
            pk=response.json()["reserva_id"]
        ).consumibles_solicitados.get()
        self.assertIsNone(solicitado.cantidad_solicitada)
        self.assertEqual(solicitado.metodo_estimacion, "revision")

    def test_las_piezas_de_la_practica_explican_la_cantidad_de_insumos(self):
        """La reserva pregunta las piezas igual que el servicio.

        Sin ese número, «2 kg» no dice si son dos piezas de un kilo o veinte de
        cien gramos, y quien revisa no puede juzgar la cantidad.
        """
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            provision_consumibles="unidad",
            piezas_por_sesion="5",
            # 0,4 kg por pieza × 5 piezas: el asistente envía el consumo de la sesión.
            consumibles_seleccionados=json.dumps([
                {
                    "id": self.material.pk,
                    "cantidad": "2.000",
                    "metodo_estimacion": "estimacion",
                },
            ]),
        )

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.cantidad_piezas, 5)
        self.assertEqual(
            reserva.consumibles_solicitados.get().cantidad_solicitada,
            Decimal("2.000"),
        )
        comprobante = self.client.get(reverse("comprobante_reserva", args=[reserva.pk]))
        self.assertContains(comprobante, "2 kg solicitados · 5 piezas")

    def test_la_reserva_de_recursos_guarda_el_trabajo_declarado_por_equipo(self):
        """Cada equipo dice cuántas piezas hará y cómo las necesita.

        Una impresora de resina y una FDM del mismo trabajo no producen lo
        mismo, así que el asistente suma las piezas y envía una línea por
        equipo; el laboratorio lee ese detalle antes de aprobar.
        """
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            provision_consumibles="unidad",
            piezas_por_sesion="5",
            detalle_trabajo_recursos=(
                "Impresora 3D de resina · 2 piezas: figuras de 30 mm, acabado liso\n"
                "Impresora 3D FDM · 3 piezas: soportes en PLA azul"
            ),
            consumibles_seleccionados=json.dumps([
                {
                    "id": self.material.pk,
                    "cantidad": "2.000",
                    "metodo_estimacion": "estimacion",
                },
            ]),
        )

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.cantidad_piezas, 5)
        self.assertIn("Impresora 3D de resina · 2 piezas", reserva.detalle_trabajo)
        self.assertIn("soportes en PLA azul", reserva.detalle_trabajo)
        comprobante = self.client.get(reverse("comprobante_reserva", args=[reserva.pk]))
        self.assertContains(comprobante, "5 piezas en total")
        self.assertContains(comprobante, "figuras de 30 mm")

    def test_servicio_fablab_exige_archivo_y_guarda_trazabilidad(self):
        self.client.force_login(self.usuario)
        servicio = FablabService.objects.create(
            code="FAB-TEST",
            nombre="Impresión 3D de prueba",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_reserva=True,
            requiere_revision_tecnica=True,
            requiere_archivos=True,
            requiere_cotizacion=True,
            tarifa_base=Decimal("10.00"),
            horas_equipo_estimadas=Decimal("2.00"),
            costo_hora_equipo=Decimal("3.00"),
            horas_mano_obra_estimadas=Decimal("1.00"),
            costo_hora_mano_obra=Decimal("4.00"),
            costo_diseno_completo=Decimal("20.00"),
        )
        payload = self._payload_reserva(
            tipo_solicitud="servicio",
            provision_consumibles="ninguno",
            unidades_seleccionadas="[]",
            servicios_solicitados=[str(servicio.pk)],
            cotizacion_aceptada="true",
            metodo_pago="ventanilla",
        )

        sin_archivo = self.client.post(reverse("crear_reserva"), payload)
        self.assertEqual(sin_archivo.status_code, 400)
        self.assertIn("Adjunta al menos", sin_archivo.json()["error"])

        payload["archivos_tecnicos"] = SimpleUploadedFile(
            "modelo_prueba.stl",
            b"solid prueba\nendsolid prueba",
            content_type="model/stl",
        )
        payload["indicaciones_archivos"] = json.dumps([{
            "nombre": "modelo_prueba.stl",
            "indicaciones": "Abrir con Blender 4.2; unidades en milímetros.",
        }])
        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(list(reserva.servicios_solicitados.all()), [servicio])
        self.assertEqual(reserva.modalidad_servicio, "modelo_listo")
        # La UPEC asume base, equipo y personal; sin materiales no hay cobro.
        self.assertEqual(reserva.costo_estimado, Decimal("0.00"))
        self.assertEqual(reserva.desglose_cotizacion["valor_referencial"], "20.00")
        self.assertEqual(reserva.desglose_cotizacion["no_cobrado"], "20.00")
        self.assertEqual(reserva.desglose_cotizacion["aporte_institucional"], "20.00")
        self.assertEqual(reserva.cantidad_piezas, 1)
        self.assertEqual(reserva.urgencia_servicio, "normal")
        self.assertTrue(reserva.cotizacion_aceptada)
        self.assertIn("Impresión 3D de prueba", reserva.titulo_solicitud)
        adjunto = reserva.archivos_tecnicos.get()
        self.assertEqual(adjunto.nombre_original, "modelo_prueba.stl")
        self.assertEqual(adjunto.extension, ".stl")
        self.assertEqual(
            adjunto.indicaciones_visualizacion,
            "Abrir con Blender 4.2; unidades en milímetros.",
        )
        orden = SolicitudFabricacion.objects.get(reserva=reserva)
        self.assertEqual(list(orden.servicios.all()), [servicio])
        self.assertEqual(orden.costo_materiales_estimado, Decimal("0.00"))
        self.assertEqual(orden.tiempo_estimado_horas, Decimal("3.00"))
        self.assertEqual(orden.prioridad, "normal")
        self.assertEqual(orden.fecha_programada_inicio.date(), reserva.fecha)

    def test_busqueda_y_registro_de_participantes_reemplazan_cantidad_manual(self):
        self.client.force_login(self.usuario)

        search = self.client.get(
            reverse("buscar_usuarios_reserva"),
            {"q": "Luis Mora"},
        )

        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json()["usuarios"][0]["id"], self.participante.pk)
        self.assertEqual(search.json()["usuarios"][0]["tipo"], "Estudiante UPEC")
        self.assertEqual(
            search.json()["usuarios"][0]["facultad"],
            "Facultad de Industrias Agropecuarias y Ciencias Ambientales",
        )
        self.assertTrue(search.json()["usuarios"][0]["habilitado"])

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                participantes_seleccionados=json.dumps([self.participante.pk]),
            ),
        )
        self.assertEqual(response.status_code, 200)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.numero_participantes, 2)
        self.assertEqual(list(reserva.participantes.all()), [self.participante])

    def test_software_se_reserva_con_equipo_y_espacio_sin_inventario(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="software",
                software_solicitado=[str(self.software.pk)],
                solicito_espacio="false",
                solicito_equipo="false",
                solicito_software="true",
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.tipo_solicitud, "software")
        self.assertEqual(list(reserva.software_solicitado.all()), [self.software])
        self.assertFalse(reserva.consumibles_solicitados.exists())
        self.assertEqual(
            [item["id"] for item in reserva.get_unidades_seleccionadas_list()],
            [self.unidad_equipo.pk],
        )
        self.assertTrue(reserva.incluye_espacio)
        self.assertFalse(reserva.solicito_espacio)
        self.assertFalse(reserva.solicito_equipo)
        self.assertTrue(reserva.solicito_software)
        self.assertEqual(reserva.alcance_espacio, "espacio_unico")
        self.assertIn(self.software.nombre, reserva.titulo_solicitud)

    def test_software_instalado_asigna_automaticamente_el_espacio_fisico(self):
        instalado = SoftwareDisponible.objects.create(
            unidad=self.laboratorio,
            codigo="SW-INSTALADO-001",
            nombre="Software instalado en estación",
            tipo_acceso="instalacion",
            licencias_totales=2,
            licencias_disponibles=2,
            requiere_reserva=True,
            activo=True,
        )
        instalado.equipos_instalados.add(self.unidad_equipo)
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="software",
                software_solicitado=[str(instalado.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertTrue(reserva.incluye_espacio)
        self.assertEqual(reserva.alcance_espacio, "espacio_unico")

    def test_software_rechaza_un_equipo_donde_no_esta_disponible(self):
        otro_equipo = EquiposServicios.objects.create(
            codigo="EQ-RES-OTRO",
            nombre="Equipo sin el software solicitado",
        )
        otra_unidad = UnidadEquipo.objects.create(
            codigo_unidad="UE-RES-OTRA",
            equipo=otro_equipo,
            laboratorio=self.laboratorio,
            estado_unidad="disponible",
            activa=True,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                unidad_equipo=otra_unidad,
                tipo_solicitud="software",
                software_solicitado=[str(self.software.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("donde esté disponible", response.json()["error"])

    def test_recursos_combina_espacio_equipo_y_software_con_tema_automatico(self):
        self.client.force_login(self.usuario)
        payload = self._payload_reserva(
            tipo_solicitud="recursos",
            incluye_espacio="true",
            software_solicitado=[str(self.software.pk)],
            solicito_espacio="true",
            solicito_equipo="true",
            solicito_software="true",
            provision_consumibles="ninguno",
        )
        payload.pop("descripcion_proyecto")

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.tipo_solicitud, "recursos")
        self.assertTrue(reserva.incluye_espacio)
        self.assertTrue(reserva.solicito_espacio)
        self.assertTrue(reserva.solicito_equipo)
        self.assertTrue(reserva.solicito_software)
        self.assertEqual(list(reserva.software_solicitado.all()), [self.software])
        self.assertIn(self.equipo.nombre, reserva.titulo_solicitud)
        self.assertIn(self.software.nombre, reserva.titulo_solicitud)
        self.assertIn("Uso de recursos solicitado", reserva.descripcion_proyecto)

    def test_recursos_requiere_al_menos_una_categoria_o_recurso(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Selecciona al menos", response.json()["error"])

    def test_servicio_asistido_admite_recursos_complementarios(self):
        servicio = FablabService.objects.create(
            code="FAB-ASISTIDO",
            nombre="Diseño asistido de prueba",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_archivos=True,
            requiere_cotizacion=False,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="servicio",
                modalidad_servicio="diseno_asistido",
                servicios_solicitados=[str(servicio.pk)],
                software_solicitado=[str(self.software.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertTrue(reserva.incluye_espacio)
        self.assertEqual(list(reserva.software_solicitado.all()), [self.software])
        self.assertIn("Diseñaré en el laboratorio", reserva.titulo_solicitud)
        self.assertIn("Recursos complementarios", reserva.descripcion_proyecto)

    def test_diseno_completo_no_exige_archivo_aunque_el_servicio_lo_admita(self):
        servicio = FablabService.objects.create(
            code="FAB-COMP-SIN-ARCH",
            nombre="Diseño completo sin archivo inicial",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_archivos=True,
            requiere_cotizacion=False,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="servicio",
                modalidad_servicio="diseno_completo",
                servicios_solicitados=[str(servicio.pk)],
                unidades_seleccionadas="[]",
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.modalidad_servicio, "diseno_completo")
        self.assertFalse(reserva.archivos_tecnicos.exists())

    def test_administrador_visualiza_descarga_e_indicaciones_del_adjunto(self):
        reserva = Reserva.objects.create(
            laboratorio=self.laboratorio,
            usuario=self.usuario,
            fecha=date(2026, 8, 22),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            nombre_solicitante="Ana Pérez",
            correo_solicitante=self.usuario.email,
            titulo_solicitud="Servicio con archivo técnico",
        )
        adjunto = ReservaAdjunto.objects.create(
            reserva=reserva,
            archivo=SimpleUploadedFile("pieza.3mf", b"modelo", content_type="model/3mf"),
            nombre_original="pieza.3mf",
            extension=".3mf",
            tipo_contenido="model/3mf",
            tamano=6,
            indicaciones_visualizacion="Abrir con PrusaSlicer 2.8; perfil 0.20 mm.",
        )
        administrador = get_user_model().objects.create_superuser(
            username="admin-adjuntos",
            email="admin-adjuntos@upec.edu.ec",
            password="prueba-segura",
        )
        self.client.force_login(administrador)

        detalle_adjunto = self.client.get(
            reverse("admin:reservas_reservaadjunto_change", args=[adjunto.pk])
        )
        detalle_reserva = self.client.get(
            reverse("admin:reservas_reserva_change", args=[reserva.pk])
        )

        for respuesta in (detalle_adjunto, detalle_reserva):
            self.assertEqual(respuesta.status_code, 200)
            self.assertContains(respuesta, "Descargar pieza.3mf")
            self.assertContains(respuesta, "Abrir con PrusaSlicer 2.8")

    def test_servicio_no_asistido_rechaza_recursos_del_usuario(self):
        servicio = FablabService.objects.create(
            code="FAB-COMPLETO",
            nombre="Diseño completo de prueba",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_archivos=False,
            requiere_cotizacion=False,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="servicio",
                modalidad_servicio="diseno_completo",
                servicios_solicitados=[str(servicio.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("equipos", response.json()["error"])

    def test_perfil_incompleto_no_puede_crear_una_reserva(self):
        usuario = get_user_model().objects.create_user(
            username="perfil-incompleto",
            email="incompleto@upec.edu.ec",
            password="prueba-segura",
            first_name="Perfil",
            last_name="Incompleto",
        )
        self.client.force_login(usuario)

        response = self.client.post(reverse("crear_reserva"), self._payload_reserva())

        # La compuerta del perfil detiene la solicitud antes de la vista.
        self.assertEqual(response.status_code, 403)
        self.assertIn("Completa y confirma tus datos", response.json()["error"])
        self.assertEqual(response.json()["perfil_url"], reverse("profile"))
        self.assertFalse(Reserva.objects.filter(usuario=usuario).exists())

        # Con los datos institucionales al día, la misma solicitud llega a la
        # validación de la reserva.
        identificar(usuario, tipo_usuario="estudiante")

        completa = self.client.post(reverse("crear_reserva"), self._payload_reserva())

        self.assertEqual(completa.status_code, 200, completa.content)

    def test_cotizacion_diferencia_modalidad_y_usuario_estudiante(self):
        verificar_pertenencia(self.participante)
        servicio = FablabService.objects.create(
            code="FAB-COTIZA",
            nombre="Servicio cotizable",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_cotizacion=True,
            tarifa_base=Decimal("10"),
            costo_diseno_completo=Decimal("20"),
            descuento_estudiante=Decimal("40"),
        )
        self.client.force_login(self.participante)

        response = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [servicio.pk],
                "modalidad": "diseno_completo",
            },
        )

        self.assertEqual(response.status_code, 200)
        cotizacion = response.json()["cotizacion"]
        self.assertEqual(cotizacion["segmento"], "estudiante")
        # La UPEC asume base y diseño: sin materiales, el usuario paga cero.
        self.assertEqual(cotizacion["subtotal"], "30.00")
        self.assertEqual(cotizacion["valor_referencial"], "30.00")
        self.assertEqual(cotizacion["no_cobrado"], "30.00")
        self.assertEqual(cotizacion["descuentos_segmento"], "0.00")
        self.assertEqual(cotizacion["aporte_institucional"], "30.00")
        self.assertEqual(cotizacion["valor_estimado_usuario"], "0.00")
        self.assertEqual(cotizacion["total"], "0.00")
        componentes = {item["clave"]: item for item in cotizacion["conceptos"][0]["componentes"]}
        self.assertFalse(componentes["tarifa_base"]["cobrado"])
        self.assertFalse(componentes["diseno"]["cobrado"])
        self.assertEqual(cotizacion["politica_cobro"]["materiales"], True)

    def test_reserva_recursos_separa_valor_referencial_aporte_e_insumos(self):
        configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(
            unidad=self.laboratorio
        )
        configuracion.tarifa_referencial_hora_espacio = Decimal("5.00")
        configuracion.tarifa_referencial_hora_equipo = Decimal("10.00")
        configuracion.tarifa_referencial_hora_software = Decimal("3.00")
        configuracion.tarifa_referencial_hora_acompanamiento = Decimal("4.00")
        configuracion.aporte_institucional_recursos_pct = Decimal("50.00")
        configuracion.save()
        self.material.precio_unitario = Decimal("3.0000")
        self.material.save(update_fields=["precio_unitario"])
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                solicito_equipo="true",
                solicito_espacio="false",
                alcance_espacio="espacio_unico",
                provision_consumibles="unidad",
                consumibles_seleccionados=json.dumps([
                    {
                        "id": self.material.pk,
                        "cantidad": "2",
                        "metodo_estimacion": "estimacion",
                    }
                ]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        desglose = reserva.desglose_cotizacion
        self.assertEqual(desglose["total_insumos"], "6.00")
        self.assertEqual(desglose["costo_apoyo_institucional"], "38.00")
        self.assertEqual(desglose["valor_referencial"], "44.00")
        self.assertEqual(desglose["aporte_institucional"], "38.00")
        self.assertEqual(desglose["valor_estimado_usuario"], "6.00")
        self.assertEqual(reserva.costo_estimado, Decimal("6.00"))
        self.assertEqual(len(desglose["componentes_apoyo"]), 3)

    def test_servicio_muestra_y_registra_insumos_tecnicos_automaticos(self):
        self.material.precio_unitario = Decimal("2.0000")
        self.material.save(update_fields=["precio_unitario"])
        servicio = FablabService.objects.create(
            code="FAB-INSUMOS-AUTO",
            nombre="Servicio con insumos planificados",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            requiere_cotizacion=True,
            tarifa_base=Decimal("10.00"),
            descuento_estudiante=Decimal("40.00"),
        )
        FablabServiceConsumible.objects.create(
            service=servicio,
            consumible=self.material,
            cantidad_sugerida=Decimal("1.250"),
            obligatorio=True,
        )
        self.client.force_login(self.usuario)

        quote_response = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [servicio.pk],
                "modalidad": "modelo_listo",
            },
        )
        self.assertEqual(quote_response.status_code, 200, quote_response.content)
        quote = quote_response.json()["cotizacion"]
        self.assertEqual(quote["total_insumos"], "2.50")
        # La tarifa base ($10) queda como referencia asumida por la UPEC; el
        # material se cobra siempre.
        self.assertEqual(quote["aporte_institucional"], "10.00")
        self.assertEqual(quote["valor_estimado_usuario"], "2.50")
        self.assertEqual(quote["materiales_planificados"][0]["cantidad"], "1.25")
        self.assertEqual(quote["materiales_planificados"][0]["unidad"], "kg")
        self.assertIn("stock", quote["materiales_planificados"][0])

        # La persona indica su consumo: se recalcula con esa cantidad.
        consumible_id = quote["materiales_planificados"][0]["id"]
        ajustada = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [servicio.pk],
                "modalidad": "modelo_listo",
                "cantidades": json.dumps({str(consumible_id): "2"}),
            },
        )
        self.assertEqual(ajustada.status_code, 200, ajustada.content)
        self.assertEqual(ajustada.json()["cotizacion"]["materiales_planificados"][0]["cantidad"], "2")
        self.assertEqual(ajustada.json()["cotizacion"]["total_insumos"], "4.00")
        # Por encima de la existencia no se cotiza ni se reserva.
        excedida = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [servicio.pk],
                "modalidad": "modelo_listo",
                "cantidades": json.dumps({str(consumible_id): "999999"}),
            },
        )
        self.assertEqual(excedida.status_code, 400, excedida.content)
        self.assertIn("supera la existencia", excedida.json()["error"])

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="servicio",
                provision_consumibles="ninguno",
                unidades_seleccionadas="[]",
                servicios_solicitados=[str(servicio.pk)],
                cotizacion_aceptada="true",
                metodo_pago="por_definir",
            ),
        )
        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        solicitado = reserva.consumibles_solicitados.get(consumible=self.material)
        self.assertEqual(reserva.provision_consumibles, "unidad")
        self.assertEqual(solicitado.cantidad_solicitada, Decimal("1.250"))
        self.assertEqual(response.json()["consumibles_solicitados"], 1)
        orden = SolicitudFabricacion.objects.get(reserva=reserva)
        self.assertEqual(orden.costo_materiales_estimado, Decimal("2.50"))
        self.assertEqual(
            SolicitudConsumible.objects.get(solicitud=orden).cantidad,
            Decimal("1.250"),
        )

    def test_reserva_valora_insumos_sin_convertirlos_en_cobro(self):
        self.material.precio_unitario = Decimal("2.5000")
        self.material.save(update_fields=["precio_unitario"])
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                provision_consumibles="unidad",
                consumibles_seleccionados=json.dumps([{
                    "id": self.material.pk,
                    "cantidad": "1.200",
                    "metodo_estimacion": "simulacion",
                }]),
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.costo_estimado, Decimal("3.00"))
        self.assertFalse(reserva.cotizacion_aceptada)
        self.assertEqual(reserva.desglose_cotizacion["tipo"], "recursos")
        self.assertIn("no constituye un cobro", reserva.desglose_cotizacion["advertencia"])

        comprobante = self.client.get(
            reverse("comprobante_reserva", args=[reserva.pk]),
        )
        self.assertEqual(comprobante.status_code, 200)
        self.assertContains(comprobante, "Estimación económica de la reserva")
        self.assertContains(comprobante, "aporte UPEC")

    def test_servicio_docente_no_crea_actividad_ni_guia_de_practica(self):
        servicio = FablabService.objects.create(
            code="FAB-DOC-SIN-GUIA",
            nombre="Fabricación encargada para docencia",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="servicio",
                provision_consumibles="ninguno",
                unidades_seleccionadas="[]",
                servicios_solicitados=[str(servicio.pk)],
                vinculacion_actividad="manual",
                referencia_actividad="Guía que no corresponde",
                origen_programacion="programada",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(reserva.vinculacion_actividad, "no_aplica")
        self.assertIsNone(reserva.actividad_catalogo)
        self.assertIsNone(response.json()["guia_estructurada"])
        self.assertIsNone(response.json()["planificacion_id"])
        self.assertEqual(response.json()["planificaciones_creadas"], 0)
        self.assertFalse(PlanificacionPractica.objects.filter(reserva=reserva).exists())

    def test_cotizacion_rechaza_modalidad_no_publicada_por_el_servicio(self):
        servicio = FablabService.objects.create(
            code="FAB-MODO",
            nombre="Servicio sin modelo listo",
            unidad=self.laboratorio,
            activo=True,
            publico=True,
            permite_modelo_listo=False,
        )
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [servicio.pk],
                "modalidad": "modelo_listo",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(servicio.nombre, response.json()["error"])

    def test_laboratorio_sin_catalogo_guia_al_usuario_sin_ocultar_la_seccion(self):
        self.material_ajeno.visible_en_reservas = False
        self.material_ajeno.save(update_fields=["visible_en_reservas"])
        response = self.client.get(self.otro_laboratorio.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insumos y materiales del laboratorio")
        # Sin opciones de provision: no marcar insumos es no necesitarlos y
        # marcarlos es solicitarlos; el valor viaja en un campo oculto.
        self.assertContains(response, 'id="provisionConsumibles"')
        self.assertNotContains(response, "No necesito insumos ni materiales")
        self.assertNotContains(response, "Llevaré materiales propios")
        self.assertNotContains(response, "No estoy seguro; necesito orientación")
        self.assertContains(response, "No hay insumos ni materiales publicados")

    def test_solicitar_inventario_exige_seleccionar_un_articulo(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                provision_consumibles="unidad",
                consumibles_seleccionados="[]",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Selecciona al menos", response.json()["error"])

    def test_material_propio_ya_no_se_declara_desde_el_formulario(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(provision_consumibles="propios"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("materiales de la actividad", response.json()["error"])

    def test_rechaza_material_ajeno_o_cantidad_superior_al_stock(self):
        self.client.force_login(self.usuario)
        casos = (
            ({"id": self.material_ajeno.pk, "cantidad": "1"}, "no pertenece"),
            ({"id": self.material.pk, "cantidad": "99"}, "supera la existencia"),
        )
        for seleccion, mensaje in casos:
            with self.subTest(seleccion=seleccion):
                response = self.client.post(
                    reverse("crear_reserva"),
                    self._payload_reserva(
                        consumibles_seleccionados=json.dumps([seleccion]),
                    ),
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(mensaje, response.json()["error"])

    def test_reserva_rechaza_insumo_incompatible_con_el_equipo(self):
        otro_modelo = EquiposServicios.objects.create(
            codigo="EQ-RES-INCOMPATIBLE",
            nombre="Equipo con otro estándar",
        )
        UnidadEquipo.objects.create(
            codigo_unidad="UE-RES-INCOMPATIBLE",
            equipo=otro_modelo,
            laboratorio=self.laboratorio,
        )
        ConsumiblePorEquipo.objects.create(
            consumible=self.material,
            equipo=otro_modelo,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                provision_consumibles="unidad",
                consumibles_seleccionados=json.dumps([
                    {"id": self.material.pk, "cantidad": "1.000"},
                ]),
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("no son compatibles", response.json()["error"])
        self.assertIn(self.material.nombre, response.json()["error"])

    def test_terminos_se_aceptan_en_la_confirmacion_final(self):
        self.client.force_login(self.usuario)
        payload = self._payload_reserva()
        payload.pop("aceptar_terminos")

        response = self.client.post(reverse("crear_reserva"), payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Acepta las condiciones", response.json()["error"])
        self.assertFalse(Reserva.objects.exists())

    def test_formulario_publico_no_permite_elegir_al_personal(self):
        self.client.force_login(self.usuario)

        response = self.client.get(self.laboratorio.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acompañamiento técnico.")
        self.assertNotContains(response, "reservation-responsible-item")
        self.assertNotContains(response, 'name="responsable_asignado"')

    def test_guarda_area_y_deja_responsable_para_asignacion_interna(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="FAB-AREA-IMP3D",
            nombre="Área de impresión 3D",
            descripcion_publica="Zona para fabricación aditiva.",
            ubicacion="Zona norte",
            capacidad=6,
        )
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                espacios_solicitados=[str(area.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(list(reserva.espacios_solicitados.all()), [area])
        self.assertIsNone(reserva.responsable_asignado)
        self.assertIn(area.nombre, reserva.titulo_solicitud)
        self.assertEqual(response.json()["espacios_solicitados"], 1)
        self.assertIsNone(response.json()["responsable_asignado"])

    def test_area_tecnica_exige_equipo_asociado_y_el_mobiliario_se_incluye(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-TECNICA",
            nombre="Área técnica de prototipado",
            mobiliario_incluido="Mesa, sillas y tomas eléctricas.",
            politica_reserva="tecnico",
        )
        area.equipos_asociados.add(self.unidad_equipo)
        self.client.force_login(self.usuario)

        sin_equipo = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                espacios_solicitados=[str(area.pk)],
                provision_consumibles="ninguno",
            ),
        )
        con_equipo = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                incluye_espacio="true",
                espacios_solicitados=[str(area.pk)],
                provision_consumibles="ninguno",
                fecha_inicio="2026-08-21T09:00",
                fecha_fin="2026-08-21T11:00",
            ),
        )

        self.assertEqual(sin_equipo.status_code, 400)
        self.assertIn("equipo o software asociado", sin_equipo.json()["error"])
        self.assertEqual(con_equipo.status_code, 200, con_equipo.content)

    def test_area_mixta_con_equipo_asociado_admite_solo_mobiliario(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="SALA-MIXTA",
            nombre="Sala de capacitación mixta",
            mobiliario_incluido="Mesas, sillas, pizarra y red institucional.",
            politica_reserva="mixto",
        )
        area.equipos_asociados.add(self.unidad_equipo)
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                espacios_solicitados=[str(area.pk)],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reserva = Reserva.objects.get(pk=response.json()["reserva_id"])
        self.assertEqual(list(reserva.espacios_solicitados.all()), [area])
        self.assertEqual(json.loads(reserva.unidades_seleccionadas), [])

    def test_rechaza_area_o_responsable_de_otra_unidad(self):
        area_ajena = EspacioReservable.objects.create(
            unidad=self.otro_laboratorio,
            codigo="AREA-AJENA",
            nombre="Área ajena",
        )
        responsable_ajeno = ResponsableUnidad.objects.create(
            unidad=self.otro_laboratorio,
            nombre="Responsable ajeno",
            email="ajeno@example.com",
        )
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-PROPIA",
            nombre="Área propia",
        )
        self.client.force_login(self.usuario)

        casos = (
            (
                {
                    "espacios_solicitados": [str(area_ajena.pk)],
                    "responsable_asignado": "",
                },
                "ya no está disponible",
            ),
            (
                {
                    "espacios_solicitados": [str(area.pk)],
                    "responsable_asignado": str(responsable_ajeno.pk),
                },
                "corresponde a la administración",
            ),
        )
        for extras, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                response = self.client.post(
                    reverse("crear_reserva"),
                    self._payload_reserva(
                        tipo_solicitud="recursos",
                        unidades_seleccionadas="[]",
                        incluye_espacio="true",
                        provision_consumibles="ninguno",
                        **extras,
                    ),
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(mensaje, response.json()["error"])

    def test_disponibilidad_bloquea_la_misma_area_pero_no_otra(self):
        area_impresion = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-IMPRESION",
            nombre="Área de impresión 3D",
        )
        area_laser = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-LASER",
            nombre="Área de corte láser",
        )
        self.client.force_login(self.usuario)

        def solicitar(area):
            return self.client.post(
                reverse("crear_reserva"),
                self._payload_reserva(
                    tipo_solicitud="recursos",
                    unidades_seleccionadas="[]",
                    incluye_espacio="true",
                    espacios_solicitados=[str(area.pk)],
                    provision_consumibles="ninguno",
                ),
            )

        primera = solicitar(area_impresion)
        repetida = solicitar(area_impresion)
        otra_area = solicitar(area_laser)

        self.assertEqual(primera.status_code, 200, primera.content)
        self.assertEqual(repetida.status_code, 400)
        self.assertIn("ya está ocupada", repetida.json()["error"])
        self.assertEqual(otra_area.status_code, 200, otra_area.content)

    def test_investigacion_comparte_area_hasta_completar_capacidad(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-COMPARTIDA",
            nombre="Area compartida de investigacion",
            capacidad=2,
        )
        self.client.force_login(self.usuario)
        common = {
            "tipo_solicitud": "recursos",
            "unidades_seleccionadas": "[]",
            "incluye_espacio": "true",
            "alcance_espacio": "areas",
            "espacios_solicitados": [str(area.pk)],
            "provision_consumibles": "ninguno",
            "proposito_codigo": "investigacion_innovacion",
            "subtipo_actividad": "proyecto_investigacion",
            "alcance_beneficiario": "perfil_solicitante",
            "vinculacion_actividad": "independiente",
        }

        first = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(**common),
        )
        second = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(**common),
        )
        third = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(**common),
        )

        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(third.status_code, 400)
        self.assertIn("capacidad", third.json()["error"].lower())

    def test_unidad_completa_no_puede_cruzarse_con_un_equipo_reservado(self):
        EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-REFERENCIA",
            nombre="Area de referencia",
            capacidad=8,
        )
        self.client.force_login(self.usuario)
        equipment_booking = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(),
        )
        full_unit_booking = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                alcance_espacio="unidad_completa",
                espacios_solicitados=[],
                provision_consumibles="ninguno",
            ),
        )

        self.assertEqual(equipment_booking.status_code, 200, equipment_booking.content)
        self.assertEqual(full_unit_booking.status_code, 400)
        self.assertIn("unidad completa", full_unit_booking.json()["error"].lower())

    def test_docencia_en_unidad_completa_bloquea_una_reserva_parcial_posterior(self):
        self.client.force_login(self.usuario)
        full_unit_booking = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                alcance_espacio="unidad_completa",
                provision_consumibles="ninguno",
            ),
        )
        partial_booking = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                proposito_codigo="investigacion_innovacion",
                subtipo_actividad="proyecto_investigacion",
                alcance_beneficiario="perfil_solicitante",
                vinculacion_actividad="independiente",
            ),
        )

        self.assertEqual(full_unit_booking.status_code, 200, full_unit_booking.content)
        self.assertEqual(partial_booking.status_code, 400)
        self.assertIn("unidad completa", partial_booking.json()["error"].lower())

    def test_consulta_de_usuario_incluye_area_y_contacto_responsable(self):
        area = EspacioReservable.objects.create(
            unidad=self.laboratorio,
            codigo="AREA-DISENO",
            nombre="Estación de diseño",
            tipo="estacion",
            ubicacion="Zona digital",
        )
        responsable = ResponsableUnidad.objects.create(
            unidad=self.laboratorio,
            usuario=get_user_model().objects.create_user(
                username="laboratorista-turno-reserva",
                email="turno@upec.edu.ec",
            ),
            nombre="Laboratorista de turno",
            rol="laboratorista",
            email="turno@upec.edu.ec",
            telefono="Ext. 123",
            recibe_reservas=True,
        )
        self.client.force_login(self.usuario)
        creada = self.client.post(
            reverse("crear_reserva"),
            self._payload_reserva(
                tipo_solicitud="recursos",
                unidades_seleccionadas="[]",
                incluye_espacio="true",
                espacios_solicitados=[str(area.pk)],
                provision_consumibles="ninguno",
            ),
        )
        self.assertEqual(creada.status_code, 200, creada.content)
        Reserva.objects.filter(pk=creada.json()["reserva_id"]).update(
            responsable_asignado=responsable,
        )

        response = self.client.get(reverse("obtener_reservas_usuario"))

        self.assertEqual(response.status_code, 200)
        reserva = response.json()["reservas"][0]
        self.assertEqual(reserva["espacios"][0]["nombre"], area.nombre)
        self.assertEqual(reserva["responsable"]["nombre"], responsable.nombre)
        self.assertEqual(reserva["responsable"]["correo"], responsable.email)
        # Banderas derivadas de la maquina de estados, para que Mis reservas
        # no repita listas de estados a mano.
        self.assertFalse(reserva["es_cerrada"])
        self.assertTrue(reserva["ocupa_agenda"])
        self.assertTrue(reserva["puede_cancelar"])
        self.assertTrue(reserva["puede_solicitar_cambio"])
        Reserva.objects.filter(pk=reserva["id"]).update(estado="completada")
        cerrada = self.client.get(reverse("obtener_reservas_usuario")).json()["reservas"][0]
        self.assertTrue(cerrada["es_cerrada"])
        self.assertFalse(cerrada["ocupa_agenda"])
        self.assertFalse(cerrada["puede_cancelar"])
        self.assertFalse(cerrada["puede_solicitar_cambio"])
