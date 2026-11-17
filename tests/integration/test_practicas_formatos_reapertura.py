"""Formatos imprimibles de la práctica y reapertura de una ejecución validada.

La lista de asistencia y la bitácora se imprimen antes de la sesión, se firman a mano
y vuelven escaneadas como evidencias. Una ejecución ya validada se reabre con motivo
para corregirla, mientras el informe semestral de su período no se haya enviado.

Reutiliza los datos y ayudantes del expediente de prácticas, sin heredar sus pruebas.
"""

import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from pypdf import PdfReader

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.formacion.models.practicas import EjecucionPractica, RegistroAuditoriaUnidad
from apps.formacion.presentation.practicas_formatos import FILAS_ADICIONALES, filas_asistencia
from apps.reservas.models.reservas import RegistroParticipanteReserva, Reserva
from tests.integration import test_practicas_integridad_expediente as expediente

MOTIVO = "Falta adjuntar la lista de asistencia firmada."


class BaseExpedientePractica(TestCase):
    @classmethod
    def setUpTestData(cls):
        expediente.IntegridadExpedientePracticasTests.setUpTestData.__func__(cls)

    plan = expediente.IntegridadExpedientePracticasTests.plan
    ejecucion = expediente.IntegridadExpedientePracticasTests.ejecucion
    datos_ejecucion = expediente.IntegridadExpedientePracticasTests.datos_ejecucion
    url = expediente.IntegridadExpedientePracticasTests.url


class FormatosImprimiblesTests(BaseExpedientePractica):
    FORMATOS = (
        ("lista_asistencia_practica_pdf", "SLCID-PRACTICAS-ASISTENCIA", "LISTA DE ASISTENCIA DE LA PRÁCTICA",
         "Registro de asistencia firmado"),
        ("bitacora_practica_pdf", "SLCID-PRACTICAS-BITACORA", "BITÁCORA DE LA PRÁCTICA", "«Bitácora»"),
    )

    def participantes(self):
        for nombre in ("Estudiante Ficticia Uno", "Estudiante Ficticio Dos"):
            RegistroParticipanteReserva.objects.create(reserva=self.reserva, nombre=nombre, rol="participante")

    def texto(self, respuesta):
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
        paginas = PdfReader(BytesIO(respuesta.content)).pages
        return " ".join("\n".join(pagina.extract_text() or "" for pagina in paginas).split()), len(paginas)

    def test_los_formatos_salen_con_su_codigo_los_datos_de_la_practica_y_sin_version_ni_borrador(self):
        plan = self.plan()
        self.participantes()
        self.client.force_login(self.autor)
        for nombre, codigo, titulo, tipo_evidencia in self.FORMATOS:
            with self.subTest(formato=nombre):
                respuesta = self.client.get(self.url(nombre, plan))
                texto, _ = self.texto(respuesta)
                for esperado in (codigo, titulo, plan.codigo, plan.tema, self.unidad.nombre, plan.asignatura,
                                 plan.docente_tutor, "10/10/2026", "08:00–10:00", "Responsable técnico",
                                 "Registrar ejecución", tipo_evidencia):
                    self.assertIn(esperado, texto)
                self.assertNotIn("Versión", texto)
                self.assertNotIn("BORRADOR", texto.upper())
                if os.environ.get("CITT_PDF_QA_DIR"):
                    salida = Path(os.environ["CITT_PDF_QA_DIR"])
                    salida.mkdir(parents=True, exist_ok=True)
                    (salida / f"{nombre}.pdf").write_bytes(respuesta.content)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(accion="descargar").count(), 2)

    def test_la_lista_imprime_a_los_participantes_registrados_y_la_bitacora_sus_apartados(self):
        plan = self.plan()
        self.participantes()
        self.client.force_login(self.operador)
        lista, _ = self.texto(self.client.get(self.url("lista_asistencia_practica_pdf", plan)))
        for esperado in ("Estudiante Ficticia Uno", "Estudiante Ficticio Dos", "Nombres y apellidos",
                         "Cédula o código", "Carrera / nivel", "Firma"):
            self.assertIn(esperado, lista)
        bitacora, paginas = self.texto(self.client.get(self.url("bitacora_practica_pdf", plan)))
        for esperado in ("Actividades realizadas", "Equipos, materiales y software utilizados",
                         "Resultados u observaciones", "Incidentes o novedades", "Docente"):
            self.assertIn(esperado, bitacora)
        # La bitácora no lleva lista nominal: la firman el docente y el responsable técnico.
        self.assertNotIn("Estudiante Ficticia Uno", bitacora)
        self.assertEqual(paginas, 1)

    def test_la_lista_completa_filas_en_blanco_hasta_los_estudiantes_previstos_y_algunas_mas(self):
        plan = self.plan(estudiantes_planificados=4)
        self.participantes()
        filas = filas_asistencia(plan)
        self.assertEqual([nombre for nombre, _ in filas[:2]], ["Estudiante Ficticia Uno", "Estudiante Ficticio Dos"])
        self.assertEqual(len(filas), 4 + FILAS_ADICIONALES)
        self.assertEqual(set(filas[2:]), {("", "")})
        # Con más registrados que previstos nadie se queda sin fila.
        for numero in range(3, 8):
            RegistroParticipanteReserva.objects.create(
                reserva=self.reserva, nombre=f"Estudiante Ficticio {numero}", rol="participante")
        self.assertEqual(len(filas_asistencia(plan)), 7 + FILAS_ADICIONALES)

    def test_una_lista_larga_ocupa_varias_paginas_y_repite_su_encabezado(self):
        plan = self.plan(estudiantes_planificados=60)
        self.client.force_login(self.autor)
        texto, paginas = self.texto(self.client.get(self.url("lista_asistencia_practica_pdf", plan)))
        self.assertGreater(paginas, 1)
        self.assertEqual(texto.count("Nombres y apellidos"), paginas)
        self.assertEqual(texto.count("SLCID-PRACTICAS-ASISTENCIA"), paginas)

    def test_los_formatos_se_descargan_en_cualquier_estado_incluso_sin_reserva(self):
        self.client.force_login(self.autor)
        for estado in ("borrador", "revision", "observada", "aprobada"):
            plan = self.plan(reserva=False, estado=estado)
            for nombre, codigo, _, _ in self.FORMATOS:
                with self.subTest(estado=estado, formato=nombre):
                    texto, _ = self.texto(self.client.get(self.url(nombre, plan)))
                    self.assertIn(codigo, texto)

    def test_quien_no_puede_ver_la_practica_no_descarga_sus_formatos(self):
        plan = self.plan()
        for nombre, _, _, _ in self.FORMATOS:
            with self.subTest(formato=nombre):
                self.assertEqual(self.client.get(self.url(nombre, plan)).status_code, 302)
                self.client.force_login(self.ajeno)
                self.assertEqual(self.client.get(self.url(nombre, plan)).status_code, 403)
                self.client.logout()
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_la_ficha_y_el_formulario_de_ejecucion_enlazan_los_dos_formatos(self):
        plan = self.plan()
        self.client.force_login(self.autor)
        for vista in ("detalle_planificacion_practica", "editar_ejecucion_practica"):
            with self.subTest(vista=vista):
                respuesta = self.client.get(self.url(vista, plan))
                for nombre, _, _, _ in self.FORMATOS:
                    self.assertContains(respuesta, self.url(nombre, plan))


class ReaperturaDeEjecucionValidadaTests(BaseExpedientePractica):
    def setUp(self):
        carpeta = TemporaryDirectory(prefix="citt-reapertura-")
        self.addCleanup(carpeta.cleanup)
        configuracion = override_settings(MEDIA_ROOT=carpeta.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)

    def validada(self, **extra):
        plan = self.plan()
        return plan, self.ejecucion(plan, estado="validada", validado_por=self.operador, **extra)

    def reabrir(self, plan, usuario=None, **datos):
        self.client.force_login(usuario or self.operador)
        return self.client.post(self.url("accion_ejecucion_practica", plan), {"accion": "reabrir", **datos})

    def mensajes(self, respuesta):
        return " ".join(str(mensaje) for mensaje in get_messages(respuesta.wsgi_request))

    def informe_semestral(self, corte, estado="validado"):
        return DocumentoExpediente.objects.create(
            unidad=self.unidad, exigido=DocumentoExigido.objects.get(codigo="INFORME-SEMESTRAL"),
            anio=self.reserva.fecha.year, corte=corte, estado=estado)

    def test_quien_opera_el_modulo_reabre_con_motivo_y_la_ejecucion_admite_una_evidencia_nueva(self):
        plan, ejecucion = self.validada()
        respuesta = self.reabrir(plan, motivo=f"  {MOTIVO}  ")
        self.assertRedirects(respuesta, self.url("detalle_planificacion_practica", plan))
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "observada")
        self.assertEqual(ejecucion.observaciones_revision, MOTIVO)
        self.assertFalse(ejecucion.es_efectiva)
        expediente._exigir_ejecucion_editable(ejecucion)

        auditoria = RegistroAuditoriaUnidad.objects.get()
        self.assertEqual(
            (auditoria.accion, auditoria.entidad, auditoria.objeto_id, auditoria.usuario, auditoria.unidad),
            ("observar", EjecucionPractica._meta.label, str(ejecucion.pk), self.operador, self.unidad))
        self.assertEqual(auditoria.descripcion, "Ejecución reabierta para corregir.")
        self.assertEqual(auditoria.datos_anteriores["estado"], "validada")
        self.assertEqual(auditoria.datos_nuevos["estado"], "observada")
        self.assertEqual(auditoria.datos_nuevos["motivo_reapertura"], MOTIVO)

        ficha = self.client.get(self.url("detalle_planificacion_practica", plan))
        self.assertContains(ficha, MOTIVO)
        self.assertContains(ficha, "Ejecución reabierta para corregir.")

        self.client.force_login(self.autor)
        guardado = self.client.post(self.url("editar_ejecucion_practica", plan), self.datos_ejecucion(
            evidencia_tipo="asistencia", evidencia_descripcion="Lista firmada por el grupo de prueba.",
            evidencias=SimpleUploadedFile("lista-firmada.pdf", b"%PDF-1.4 lista", "application/pdf"),
            accion="enviar"))
        self.assertEqual(guardado.status_code, 302, getattr(guardado, "context", None) and guardado.context["form"].errors)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.assertEqual([e.tipo for e in ejecucion.evidencias.all()], ["asistencia"])

    def test_sin_motivo_suficiente_la_ejecucion_sigue_validada(self):
        plan, ejecucion = self.validada()
        for motivo in ("", "   ", "Muy corto"):
            with self.subTest(motivo=motivo):
                respuesta = self.reabrir(plan, motivo=motivo)
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn("motivo de la reapertura", self.mensajes(respuesta))
                ejecucion.refresh_from_db()
                self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_quien_no_opera_el_modulo_no_puede_reabrir(self):
        plan, ejecucion = self.validada()
        for usuario in (self.autor, self.ajeno):
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.reabrir(plan, usuario, motivo=MOTIVO).status_code, 403)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_con_el_informe_semestral_del_periodo_enviado_no_se_reabre(self):
        plan, ejecucion = self.validada()
        informe = self.informe_semestral("B")
        respuesta = self.reabrir(plan, motivo=MOTIVO)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("la Dirección debe devolver primero el informe", self.mensajes(respuesta))
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)
        ficha = self.client.get(self.url("detalle_planificacion_practica", plan))
        self.assertNotContains(ficha, 'value="reabrir"')
        self.assertContains(ficha, "la Dirección debe devolver primero el informe")

        # Cuando la Dirección devuelve el informe, la ejecución vuelve a poder reabrirse.
        informe.estado = "observado"
        informe.save(update_fields=["estado"])
        self.reabrir(plan, motivo=MOTIVO)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "observada")

    def test_el_informe_de_otro_periodo_o_de_otra_unidad_o_sin_enviar_no_impide_reabrir(self):
        plan, ejecucion = self.validada()
        self.informe_semestral("A")
        self.informe_semestral("B", estado="cargado")
        otra = type(self.unidad).objects.create(
            nombre="Laboratorio ajeno a la reapertura", slug="laboratorio-ajeno-reapertura",
            dependencia="laboratorios", fecha_inicio=self.unidad.fecha_inicio)
        DocumentoExpediente.objects.create(
            unidad=otra, exigido=DocumentoExigido.objects.get(codigo="INFORME-SEMESTRAL"),
            anio=self.reserva.fecha.year, corte="B", estado="validado")
        self.reabrir(plan, motivo=MOTIVO)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "observada")

    def test_el_tramo_conservado_del_informe_manda_sobre_el_corte_del_anio(self):
        plan, ejecucion = self.validada()
        informe = self.informe_semestral("A")
        # El tramo que el informe conservó llega hasta la fecha de la práctica.
        DocumentoExpediente.objects.filter(pk=informe.pk).update(
            tramo_inicio=self.reserva.fecha.replace(month=4, day=1), tramo_fin=self.reserva.fecha)
        self.reabrir(plan, motivo=MOTIVO)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")

    def test_solo_una_ejecucion_validada_se_reabre(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="revision")
        for estado in ("borrador", "revision", "observada"):
            EjecucionPractica.objects.filter(pk=ejecucion.pk).update(estado=estado)
            with self.subTest(estado=estado):
                respuesta = self.reabrir(plan, motivo=MOTIVO)
                self.assertIn("Solo una ejecución validada", self.mensajes(respuesta))
                ejecucion.refresh_from_db()
                self.assertEqual((ejecucion.estado, ejecucion.observaciones_revision), (estado, ""))
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_el_boton_de_reabrir_solo_se_muestra_a_quien_opera_y_con_la_ejecucion_validada(self):
        plan, ejecucion = self.validada()
        direccion = self.url("detalle_planificacion_practica", plan)
        self.client.force_login(self.operador)
        self.assertContains(self.client.get(direccion), 'value="reabrir"')
        self.client.force_login(self.autor)
        self.assertNotContains(self.client.get(direccion), 'value="reabrir"')
        self.client.force_login(self.operador)
        for estado in ("borrador", "revision", "observada"):
            EjecucionPractica.objects.filter(pk=ejecucion.pk).update(estado=estado)
            with self.subTest(estado=estado):
                self.assertNotContains(self.client.get(direccion), 'value="reabrir"')

    def ciclo_de_correccion(self, resultado, estado_reserva):
        """Valida, reabre, corrige, reenvía y valida otra vez: la reserva se cierra una sola vez."""
        plan = self.plan()
        ejecucion = self.ejecucion(
            plan, estado="revision", resultado=resultado, motivo="Suspensión ficticia de la sesión.")
        self.client.force_login(self.operador)
        self.client.post(self.url("accion_ejecucion_practica", plan), {"accion": "validar"})
        ejecucion.refresh_from_db()
        self.reserva.refresh_from_db()
        self.assertEqual((ejecucion.estado, self.reserva.estado), ("validada", estado_reserva))
        reserva_cerrada = Reserva.objects.values().get(pk=self.reserva.pk)

        self.reabrir(plan, motivo=MOTIVO)
        self.client.force_login(self.autor)
        enviado = self.client.post(self.url("editar_ejecucion_practica", plan), self.datos_ejecucion(
            resultado=resultado, motivo="Suspensión ficticia de la sesión.",
            detalle_operativo_registrado="1", accion="enviar"))
        self.assertEqual(
            enviado.status_code, 302, getattr(enviado, "context", None) and enviado.context["form"].errors)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")

        self.client.force_login(self.operador)
        validado = self.client.post(self.url("accion_ejecucion_practica", plan), {"accion": "validar"})
        self.assertNotIn("no se validó", self.mensajes(validado))
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(Reserva.objects.values().get(pk=self.reserva.pk), reserva_cerrada)
        self.assertEqual(
            list(RegistroAuditoriaUnidad.objects.filter(entidad=EjecucionPractica._meta.label)
                 .order_by("pk").values_list("accion", flat=True)),
            ["aprobar", "observar", "enviar", "aprobar"])

    def test_una_ejecucion_reabierta_se_corrige_y_se_valida_de_nuevo_sin_completar_dos_veces_la_reserva(self):
        self.ciclo_de_correccion("ejecutada", "completada")

    def test_una_ejecucion_cancelada_y_reabierta_se_valida_de_nuevo_sin_cancelar_dos_veces_la_reserva(self):
        self.ciclo_de_correccion("cancelada", "cancelada")
