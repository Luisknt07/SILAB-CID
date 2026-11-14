"""Ensayo HTTP del expediente presencial, con datos y archivos aislados de QA.

Las reservas son solicitudes sintéticas del fixture. Su aprobación, inicio,
registro FT03, revisión y consulta se realizan por los endpoints institucionales.
No se sustituye la verificación de una maqueta ni una aceptación presencial real.
"""

from datetime import date, time
from io import BytesIO
import json
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.laboratorios.operacion.presentation.logistica_operacion_contenido import inicial_guia
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.reservas.models.reservas import GuiaActividadReserva, NotificacionReserva, RegistroParticipanteReserva, Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from apps.formacion.models.partidas_simulador import PartidaSimulador
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import verificar_pertenencia


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CITT_EXIGIR_EQUIPOS_VERIFICADOS=True,
)
class EnsayoPresencialLogisticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_user("qa-ensayo-admin")
        cls.docente = usuarios.objects.create_user(
            "qa-ensayo-docente", first_name="Docente", last_name="QA"
        )
        cls.participante = usuarios.objects.create_user("qa-ensayo-participante")
        cls.admin_otra = usuarios.objects.create_user("qa-ensayo-admin-otra")
        cls.ajeno = usuarios.objects.create_user("qa-ensayo-ajeno")
        cls.docente.profile.tipo_usuario = "docente"
        cls.docente.profile.institucion = "UPEC"
        cls.docente.profile.facultad = "agropecuarias_ambientales"
        cls.docente.profile.carrera = "computacion"
        cls.docente.profile.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio logístico del ensayo sintético",
            slug=SLUG_LOGISTICA,
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.admin,
            activo=True,
        )
        cls.otra = Unidad.objects.create(
            nombre="Otra unidad del ensayo sintético",
            slug="qa-ensayo-otra-unidad",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.admin_otra,
            activo=True,
        )
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.admin,
            nombre="Responsable técnico QA",
            rol="responsable_tecnico",
            activo=True,
            recibe_reservas=True,
        )
        ficha = EquiposServicios.objects.create(
            codigo="QA-ENSAYO-MAQUETA", nombre="Maqueta didáctica sintética"
        )
        cls.equipo = UnidadEquipo.objects.create(
            laboratorio=cls.unidad,
            equipo=ficha,
            codigo_unidad="QA-ENSAYO-CD-01",
            estado_unidad="disponible",
            activa=True,
            existencia_verificada=True,
        )

    def setUp(self):
        carpeta = TemporaryDirectory(prefix="citt-ensayo-presencial-")
        self.addCleanup(carpeta.cleanup)
        configuracion = override_settings(MEDIA_ROOT=carpeta.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.fecha = timezone.localdate()
        self.client.force_login(self.docente)

    def url(self, nombre, objeto=None, *, unidad=None):
        args = [(unidad or self.unidad).slug]
        if objeto is not None:
            args.append(objeto.pk)
        return reverse(nombre, args=args)

    def preparar_solicitud(self, *, publicar=True):
        url = (
            self.url("nueva_guia_practica")
            + "?plantilla=logistica-cd&caso=cd-normal&semilla=42"
        )
        self.client.force_login(self.docente)
        respuesta = self.client.post(
            url,
            {
                **inicial_guia("cd-normal", 42),
                "docente_responsable": "Docente QA",
                "categoria_uso": "Docencia y práctica curricular",
                "carrera_semestre": "Logística y Transporte · cuarto semestre",
                "duracion": "120 minutos",
                "maximo_estudiantes": "4",
                "equipos": "Maqueta didáctica sintética verificada en este fixture",
                "materiales": "Cajas didácticas y hoja de conciliación",
                "manejo_residuos": "Recuperar y ordenar las cajas reutilizables.",
                "accion": "enviar_revision",
            },
        )
        self.assertEqual(respuesta.status_code, 302, respuesta.content[:400])
        guia = GuiaActividadReserva.objects.get()
        self.assertEqual(guia.estado_publicacion, "revision")
        if publicar:
            self.client.force_login(self.admin)
            respuesta = self.client.post(
                reverse("cambiar_estado_guia_practica", args=[guia.pk]),
                {"accion": "aprobar", "observacion": "Protocolo sintético revisado."},
            )
            self.assertEqual(respuesta.status_code, 302)
            guia.refresh_from_db()
            self.assertEqual(
                guia.estado_publicacion, "publicada", guia.observaciones_revision
            )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            usuario=self.docente,
            actividad_catalogo=guia.actividad,
            fecha=self.fecha,
            hora_inicio=time(8),
            hora_fin=time(10),
            numero_participantes=4,
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            vinculacion_actividad="catalogo",
            titulo_solicitud="Ensayo sintético del centro de distribución",
            referencia_actividad="Logística de almacenamiento e inventario",
            responsable_actividad="Docente QA",
            equipo_codigo=self.equipo.codigo_unidad,
            equipo_nombre=self.equipo.equipo.nombre,
            unidades_seleccionadas=json.dumps(
                [
                    {
                        "id": self.equipo.pk,
                        "codigo": self.equipo.codigo_unidad,
                        "nombre": self.equipo.equipo.nombre,
                    }
                ]
            ),
            estado="pendiente",
        )
        return guia, reserva

    def aprobar(self, reserva):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            self.url("gestion_reserva_accion", reserva),
            {"accion": "aprobar", "responsable_id": self.responsable.pk},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.json()["success"])
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        return PlanificacionPractica.objects.get(reserva=reserva)

    def iniciar(self, reserva):
        self.client.force_login(self.admin)
        return self.client.post(
            self.url("gestion_reserva_accion", reserva), {"accion": "iniciar"}
        )

    def datos_ft03(self, plan, *, archivo=None):
        self.client.force_login(self.docente)
        respuesta = self.client.get(self.url("editar_ejecucion_practica", plan))
        self.assertEqual(respuesta.status_code, 200)
        participante = plan.reserva.registros_participantes.get(usuario=self.docente)
        datos = {
            "fecha_ejecucion": self.fecha.isoformat(),
            "hora_inicio_real": "08:05",
            "hora_fin_real": "09:55",
            "resultado": "ejecutada",
            "estudiantes_asistentes": "4",
            "cumplimiento_resultado": "si",
            "responsable_tecnico": self.responsable.pk,
            "observaciones_docente": "Se conciliaron los registros sintéticos y se ordenó el puesto.",
            "detalle_operativo_registrado": "1",
            "equipos_utilizados": [str(self.equipo.pk)],
            "participantes_asistentes": [str(participante.pk)],
            "accion": "enviar",
        }
        if archivo is not None:
            datos.update(
                evidencias=archivo,
                evidencia_tipo="informe",
                evidencia_descripcion="Conciliación sintética del ensayo QA; sin personas ni datos reales.",
            )
        return datos

    def enviar_ft03(self, plan):
        respuesta = self.client.post(
            self.url("editar_ejecucion_practica", plan),
            self.datos_ft03(
                plan,
                archivo=SimpleUploadedFile(
                    "conciliacion-qa.csv", b"sku,diferencia\nSKU-A,0\n", "text/csv"
                ),
            ),
        )
        self.assertEqual(respuesta.status_code, 302, respuesta.content[:400])
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual(ejecucion.estado, "revision")
        return ejecucion

    def validar(self, plan):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
        )
        self.assertEqual(respuesta.status_code, 302)
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual(ejecucion.estado, "validada")
        return ejecucion

    def efectos(self):
        return {
            "planes": PlanificacionPractica.objects.count(),
            "ejecuciones": EjecucionPractica.objects.count(),
            "evidencias": EvidenciaPractica.objects.count(),
            "auditoria": RegistroAuditoriaUnidad.objects.count(),
            "avisos": NotificacionReserva.objects.count(),
        }

    def test_circuito_completo_conserva_guia_recursos_asistencia_y_reporte(self):
        guia, reserva = self.preparar_solicitud()
        procedencia = guia.contenido["procedencia_simulacion"]
        self.assertEqual(procedencia["caso"], "cd-normal")
        self.assertFalse(procedencia["autoriza_presencial"])
        plan = self.aprobar(reserva)
        self.assertEqual(
            (plan.guia_id, plan.actividad_id, plan.estado),
            (guia.pk, guia.actividad_id, "aprobada"),
        )
        self.assertEqual(plan.estudiantes_planificados, 4)
        self.assertEqual(self.iniciar(reserva).status_code, 200)
        ejecucion = self.enviar_ft03(plan)
        evidencia = ejecucion.evidencias.get()
        ejecucion = self.validar(plan)
        reserva.refresh_from_db()
        self.assertEqual(
            (reserva.estado, reserva.resultado_cierre), ("completada", "atendida")
        )
        self.assertTrue(ejecucion.es_efectiva)
        self.assertEqual(
            ejecucion.detalle_operativo["equipos"][0]["codigo"],
            self.equipo.codigo_unidad,
        )
        self.assertEqual(
            reserva.registros_participantes.get(usuario=self.docente).asistencia,
            "asistio",
        )
        respuesta = self.client.get(
            self.url("gestion_reporte_unidad"),
            {
                "categoria_reporte": "ejecuciones",
                "desde": self.fecha.isoformat(),
                "hasta": self.fecha.isoformat(),
            },
        )
        self.assertContains(respuesta, "FT03")
        self.assertContains(respuesta, ejecucion.observaciones_docente)
        self.assertContains(respuesta, "Informe de estudiante")
        self.assertEqual(ejecucion.evidencias.get().pk, evidencia.pk)
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_guia_completa_en_revision_reserva_turno_sin_autorizar_inicio(self):
        guia, reserva = self.preparar_solicitud(publicar=False)
        plan = self.aprobar(reserva)
        guia.refresh_from_db()
        self.assertEqual(
            (reserva.estado, guia.estado_publicacion, plan.estado),
            ("confirmada", "revision", "borrador"),
        )
        antes = self.efectos()
        respuesta = self.iniciar(reserva)
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["code"], "documentacion_pendiente")
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertIsNone(reserva.fecha_inicio_atencion)
        self.assertEqual(self.efectos(), antes)
        from apps.formacion.presentation.practicas_integracion import DocumentacionReservaPendiente, validar_compuerta_documental

        for accion in ("iniciar", "completar"):
            with (
                self.subTest(accion=accion),
                self.assertRaises(DocumentacionReservaPendiente),
            ):
                validar_compuerta_documental(reserva, accion)
        self.assertEqual(self.efectos(), antes)

    def test_inicio_revalida_la_guia_retirada_despues_de_aprobar(self):
        guia, reserva = self.preparar_solicitud()
        self.aprobar(reserva)
        guia.activo = False
        guia.save(update_fields=["activo"])
        antes = self.efectos()
        respuesta = self.iniciar(reserva)
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["code"], "documentacion_pendiente")
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertEqual(self.efectos(), antes)

    def test_bloqueo_posterior_a_aprobacion_impide_inicio_sin_efectos(self):
        _, reserva = self.preparar_solicitud()
        self.aprobar(reserva)
        bloqueo = BloqueoAgendaUnidad.objects.create(
            unidad=self.unidad,
            tipo="mantenimiento",
            titulo="Inspección sobrevenida QA",
            motivo="Recurso temporalmente aislado",
            fecha_inicio=self.fecha,
            fecha_fin=self.fecha,
            hora_inicio=time(8),
            hora_fin=time(10),
            alcance="equipos",
        )
        bloqueo.equipos.add(self.equipo)
        antes = self.efectos()
        respuesta = self.iniciar(reserva)
        self.assertEqual(respuesta.status_code, 409)
        self.assertFalse(respuesta.json()["success"])
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertIsNone(reserva.fecha_inicio_atencion)
        self.assertEqual(self.efectos(), antes)

    def test_equipo_en_mantenimiento_despues_de_aprobar_no_inicia(self):
        _, reserva = self.preparar_solicitud()
        self.aprobar(reserva)
        self.equipo.estado_unidad = "mantenimiento"
        self.equipo.save(update_fields=["estado_unidad"])
        antes = self.efectos()
        respuesta = self.iniciar(reserva)
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("mantenimiento", respuesta.json()["error"].lower())
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "confirmada")
        self.assertEqual(self.efectos(), antes)

    def test_recurso_restaurado_permite_iniciar_una_sola_vez(self):
        _, reserva = self.preparar_solicitud()
        self.aprobar(reserva)
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(activa=False)
        self.assertEqual(self.iniciar(reserva).status_code, 409)
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(activa=True)
        self.assertEqual(self.iniciar(reserva).status_code, 200)
        reserva.refresh_from_db()
        inicio = reserva.fecha_inicio_atencion
        antes = self.efectos()
        self.assertEqual(self.iniciar(reserva).status_code, 409)
        reserva.refresh_from_db()
        self.assertEqual(
            (reserva.estado, reserva.fecha_inicio_atencion), ("en_proceso", inicio)
        )
        self.assertEqual(self.efectos(), antes)

    def test_autor_no_hereda_aprobacion_reserva_plan_o_validacion(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        self.enviar_ft03(plan)
        antes = self.efectos()
        self.client.force_login(self.docente)
        for nombre, objeto, accion in (
            ("gestion_reserva_accion", reserva, "aprobar"),
            ("accion_planificacion_practica", plan, "aprobar"),
            ("accion_ejecucion_practica", plan, "validar"),
        ):
            with self.subTest(accion=nombre):
                self.assertEqual(
                    self.client.post(
                        self.url(nombre, objeto), {"accion": accion}
                    ).status_code,
                    403,
                )
        self.assertEqual(self.efectos(), antes)
        self.assertEqual(
            EjecucionPractica.objects.get(planificacion=plan).estado, "revision"
        )

    def test_participante_consulta_evidencia_sin_editar_o_validar(self):
        guia, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        ejecucion = self.enviar_ft03(plan)
        evidencia = ejecucion.evidencias.get()
        guia.actividad.participantes_autorizados.add(self.participante)
        self.client.force_login(self.participante)
        antes = self.efectos()
        self.assertEqual(
            self.client.get(
                self.url("detalle_planificacion_practica", plan)
            ).status_code,
            200,
        )
        respuesta = self.client.get(self.url("evidencia_practica", evidencia))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            b"".join(respuesta.streaming_content), b"sku,diferencia\nSKU-A,0\n"
        )
        self.assertEqual(
            self.client.post(
                self.url("editar_ejecucion_practica", plan), {"accion": "guardar"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
            ).status_code,
            403,
        )
        self.assertEqual(self.efectos(), antes)

    def test_admin_otra_unidad_no_accede_a_expediente_evidencia_o_reportes(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        ejecucion = self.enviar_ft03(plan)
        evidencia = ejecucion.evidencias.get()
        self.client.force_login(self.admin_otra)
        antes = self.efectos()
        self.assertEqual(
            self.client.get(
                self.url("detalle_planificacion_practica", plan)
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(self.url("evidencia_practica", evidencia)).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                self.url("evidencia_practica", evidencia, unidad=self.otra)
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(self.url("gestion_reporte_unidad")).status_code, 403
        )
        self.assertEqual(self.efectos(), antes)
        reporte = self.client.get(
            self.url("gestion_reporte_unidad", unidad=self.otra),
            {"categoria_reporte": "ejecuciones"},
        )
        self.assertEqual(reporte.status_code, 200)
        self.assertNotContains(reporte, ejecucion.observaciones_docente)
        self.assertEqual(self.efectos(), {**antes, "auditoria": antes["auditoria"] + 1})
        lectura = RegistroAuditoriaUnidad.objects.latest("pk")
        self.assertEqual(
            (lectura.unidad_id, lectura.usuario_id, lectura.accion),
            (self.otra.pk, self.admin_otra.pk, "consultar"),
        )

    def test_adjunto_no_admitido_revierte_ft03_asistencia_y_auditoria(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        datos = self.datos_ft03(
            plan,
            archivo=SimpleUploadedFile(
                "no-admitido.exe", b"qa", "application/octet-stream"
            ),
        )
        participantes = list(RegistroParticipanteReserva.objects.values())
        antes = self.efectos()
        respuesta = self.client.post(self.url("editar_ejecucion_practica", plan), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertContains(respuesta, "formato admitido")
        self.assertEqual(self.efectos(), antes)
        self.assertEqual(
            list(RegistroParticipanteReserva.objects.values()), participantes
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "en_proceso")

    def test_reenvio_y_validacion_repetida_no_duplican_evidencias_o_cierre(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        ejecucion = self.enviar_ft03(plan)
        antes = self.efectos()
        self.assertEqual(
            self.client.post(
                self.url("editar_ejecucion_practica", plan), {"accion": "enviar"}
            ).status_code,
            403,
        )
        self.assertEqual(self.efectos(), antes)
        self.validar(plan)
        cierre = Reserva.objects.get(pk=reserva.pk).fecha_cierre
        antes = self.efectos()
        respuesta = self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.efectos(), antes)
        self.assertEqual(Reserva.objects.get(pk=reserva.pk).fecha_cierre, cierre)
        self.assertEqual(ejecucion.evidencias.count(), 1)

    def test_reportes_html_y_excel_conservan_el_mismo_expediente(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        ejecucion = self.enviar_ft03(plan)
        self.validar(plan)
        antes = self.efectos()
        for categoria, contenido in (
            ("planificaciones", plan.tema),
            ("ejecuciones", ejecucion.observaciones_docente),
        ):
            parametros = {
                "categoria_reporte": categoria,
                "desde": self.fecha.isoformat(),
                "hasta": self.fecha.isoformat(),
            }
            html = self.client.get(self.url("gestion_reporte_unidad"), parametros)
            self.assertContains(html, contenido)
            excel = self.client.get(self.url("gestion_reporte_unidad_xlsx"), parametros)
            self.assertEqual(excel.status_code, 200)
            with ZipFile(BytesIO(excel.content)) as paquete:
                tablas = "\n".join(
                    paquete.read(nombre).decode("utf-8")
                    for nombre in paquete.namelist()
                    if nombre.startswith("xl/worksheets/sheet")
                )
            self.assertIn(contenido, tablas)
            self.assertIn(self.unidad.nombre, tablas)
        self.assertEqual(self.efectos(), {**antes, "auditoria": antes["auditoria"] + 4})
        self.assertEqual(
            (PlanificacionPractica.objects.count(), EjecucionPractica.objects.count()),
            (1, 1),
        )

    def test_csrf_no_permite_aprobar_iniciar_o_validar_desde_otra_pagina(self):
        _, reserva = self.preparar_solicitud()
        plan = self.aprobar(reserva)
        self.iniciar(reserva)
        self.enviar_ft03(plan)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        antes = self.efectos()
        for nombre, objeto, accion in (
            ("gestion_reserva_accion", reserva, "aprobar"),
            ("gestion_reserva_accion", reserva, "iniciar"),
            ("accion_ejecucion_practica", plan, "validar"),
        ):
            with self.subTest(vista=nombre):
                self.assertEqual(
                    cliente.post(
                        self.url(nombre, objeto), {"accion": accion}
                    ).status_code,
                    403,
                )
        self.assertEqual(self.efectos(), antes)

    def test_induccion_y_registro_de_ingreso_se_exigen_antes_de_iniciar(self):
        from apps.formacion.presentation.practicas_integracion import asegurar_participantes_reserva

        _, reserva = self.preparar_solicitud()
        self.aprobar(reserva)
        requisito = RequisitoAcceso.objects.create(
            unidad=self.unidad,
            codigo="QA-ENSAYO-IND",
            nombre="Inducción sintética QA",
            tipo="induccion",
            aplica_a=["docente"],
            obligatorio=True,
            momento="ingresar",
            activo=True,
        )
        asegurar_participantes_reserva(reserva)
        participante = reserva.registros_participantes.get(usuario=self.docente)
        self.assertEqual(self.iniciar(reserva).status_code, 409)
        self.assertEqual(RegistroIngreso.objects.count(), 0)
        HabilitacionAcceso.objects.create(
            usuario=self.docente,
            requisito=requisito,
            fecha=self.fecha,
            origen="manual",
            otorgada_por=self.admin,
        )
        respuesta = self.client.post(
            self.url("gestion_operacion_accion"),
            {
                "modulo": "ingreso",
                "reserva_id": reserva.pk,
                "personas_ids": str(participante.pk),
                f"persona_{participante.pk}_ingresa": "1",
                f"persona_{participante.pk}_hora": "08:00",
                "accion": "guardar",
            },
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.json()["success"])
        self.assertTrue(RegistroIngreso.objects.get().ingresa)
        self.assertEqual(self.iniciar(reserva).status_code, 200)
