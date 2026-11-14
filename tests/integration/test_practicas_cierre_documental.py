"""La corrección documental de FT03 conserva la operación ya cerrada.

Estos casos reutilizan los datos y ayudantes del expediente institucional,
sin heredar sus tests ni ejecutar dos veces la batería original.
"""

from copy import deepcopy
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.formacion.presentation.practicas_integracion import construir_detalle_operativo, resumen_recursos
from apps.recursos.models.consumibles import Consumible
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica
from apps.reservas.models.reservas import NotificacionReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration import test_practicas_integridad_expediente as expediente


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class EdicionDocumentalTrasCierreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        expediente.IntegridadExpedientePracticasTests.setUpTestData.__func__(cls)

    plan = expediente.IntegridadExpedientePracticasTests.plan
    ejecucion = expediente.IntegridadExpedientePracticasTests.ejecucion
    datos_ejecucion = expediente.IntegridadExpedientePracticasTests.datos_ejecucion
    url = expediente.IntegridadExpedientePracticasTests.url

    def setUp(self):
        carpeta = TemporaryDirectory(prefix="citt-ft03-cerrada-")
        self.addCleanup(carpeta.cleanup)
        configuracion = override_settings(MEDIA_ROOT=carpeta.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.client.force_login(self.autor)

    def expediente_cerrado(
        self,
        *,
        estado_ft03="observada",
        estado_reserva="completada",
        participantes=True,
        crear_ft03=True,
    ):
        plan = self.plan()
        insumo = Consumible.objects.create(
            unidad=self.unidad,
            codigo="QA-CIERRE-ETIQUETA",
            nombre="Etiqueta de conciliación histórica",
            clasificacion="empaque",
            unidad_medida="unidad",
        )
        consumo = ReservaConsumible.objects.create(
            reserva=self.reserva,
            consumible=insumo,
            cantidad_solicitada=2,
            cantidad_aprobada=2,
            cantidad_consumida=1,
        )
        if participantes:
            RegistroParticipanteReserva.objects.create(
                reserva=self.reserva,
                usuario=self.autor,
                nombre="Docente del registro histórico",
                rol="solicitante",
                asistencia="asistio",
            )
        self.reserva.estado = estado_reserva
        self.reserva.resultado_cierre = (
            "atendida" if estado_reserva == "completada" else "no_atendida"
        )
        self.reserva.fecha_cierre = timezone.now()
        self.reserva.equipo_codigo = "CD-HIST-01"
        self.reserva.equipo_nombre = "Maqueta histórica utilizada"
        detalle = construir_detalle_operativo(self.reserva)
        detalle["origen_qa"] = "Cierre operativo histórico"
        self.reserva.detalle_ejecucion = detalle
        self.reserva.save(
            update_fields=[
                "estado",
                "resultado_cierre",
                "fecha_cierre",
                "equipo_codigo",
                "equipo_nombre",
                "detalle_ejecucion",
            ]
        )
        ejecucion = None
        if crear_ft03:
            detalle_ft03 = deepcopy(detalle)
            detalle_ft03["origen_qa"] = "FT03 documental histórico"
            ejecucion = self.ejecucion(
                plan,
                estado=estado_ft03,
                detalle_operativo=detalle_ft03,
                recursos_utilizados="Resumen histórico de recursos revisado por el operador.",
            )
        return plan, ejecucion, consumo

    def operacion(self, ejecucion=None):
        datos = {
            "reserva": Reserva.objects.values().get(pk=self.reserva.pk),
            "participantes": list(
                self.reserva.registros_participantes.order_by("pk").values()
            ),
            "consumos": list(
                self.reserva.consumibles_solicitados.order_by("pk").values()
            ),
            "avisos": NotificacionReserva.objects.count(),
        }
        if ejecucion is not None:
            ejecucion.refresh_from_db()
            datos.update(
                detalle=deepcopy(ejecucion.detalle_operativo),
                recursos=ejecucion.recursos_utilizados,
                generales={
                    campo: getattr(ejecucion, campo)
                    for campo in (
                        "fecha_ejecucion",
                        "hora_inicio_real",
                        "hora_fin_real",
                        "resultado",
                        "motivo",
                        "estudiantes_asistentes",
                        "tuvo_incidente",
                        "incidencia_id",
                        "responsable_tecnico_id",
                    )
                },
            )
        return datos

    def guardar_documentacion(self, plan, **extra):
        respuesta = self.client.post(
            self.url("editar_ejecucion_practica", plan),
            self.datos_ejecucion(
                observaciones_docente="Se aclara la conciliación histórica del inventario.",
                cumplimiento_resultado="parcial",
                **extra,
            ),
        )
        errores = (
            respuesta.context["form"].errors
            if respuesta.status_code == 200 and respuesta.context
            else respuesta.content[:300]
        )
        self.assertEqual(respuesta.status_code, 302, errores)
        return EjecucionPractica.objects.get(planificacion=plan)

    def test_formulario_cerrado_permita_documentar_y_protege_datos_operativos(self):
        plan, ejecucion, consumo = self.expediente_cerrado()
        antes = self.operacion(ejecucion)
        for estado in ("observada", "borrador"):
            EjecucionPractica.objects.filter(pk=ejecucion.pk).update(estado=estado)
            with self.subTest(estado=estado):
                respuesta = self.client.get(self.url("editar_ejecucion_practica", plan))
                self.assertEqual(respuesta.status_code, 200)
                form = respuesta.context["form"]
                for campo in (
                    "fecha_ejecucion",
                    "hora_inicio_real",
                    "hora_fin_real",
                    "resultado",
                    "estudiantes_asistentes",
                    "equipos_utilizados",
                    "participantes_asistentes",
                    f"consumo_{consumo.pk}",
                ):
                    self.assertTrue(form.fields[campo].disabled, campo)
                for campo in ("observaciones_docente", "cumplimiento_resultado"):
                    self.assertFalse(form.fields[campo].disabled, campo)
        self.assertEqual(self.operacion(ejecucion), antes)

    def test_post_no_reescribe_operacion_pero_admite_correccion_y_evidencia(self):
        plan, ejecucion, consumo = self.expediente_cerrado()
        anterior = EvidenciaPractica.objects.create(
            ejecucion=ejecucion,
            tipo="bitacora",
            archivo="practicas/qa/bitacora-historica.csv",
            nombre_original="bitacora-historica.csv",
            descripcion="Referencia histórica del cierre.",
            subido_por=self.autor,
        )
        antes = self.operacion(ejecucion)
        ejecucion = self.guardar_documentacion(
            plan,
            fecha_ejecucion="2026-10-09",
            hora_inicio_real="12:00",
            hora_fin_real="12:05",
            resultado="cancelada",
            motivo="Intento de cambiar la operación cerrada.",
            estudiantes_asistentes="0",
            tuvo_incidente="1",
            incidencia="99999999",
            responsable_tecnico="99999999",
            detalle_operativo_registrado="1",
            equipos_utilizados=[],
            participantes_asistentes=[],
            evidencias=SimpleUploadedFile(
                "aclaracion.csv", b"sku,diferencia\nSKU-A,0\n", "text/csv"
            ),
            evidencia_tipo="informe",
            evidencia_descripcion="Aclaración documental sin modificar el cierre.",
            **{f"consumo_{consumo.pk}": "0"},
        )
        self.assertEqual(self.operacion(ejecucion), antes)
        self.assertEqual(ejecucion.estado, "borrador")
        self.assertEqual(ejecucion.cumplimiento_resultado, "parcial")
        self.assertEqual(
            ejecucion.observaciones_docente,
            "Se aclara la conciliación histórica del inventario.",
        )
        self.assertEqual(ejecucion.evidencias.count(), 2)
        self.assertTrue(ejecucion.evidencias.filter(pk=anterior.pk).exists())

    def test_lista_nominal_vacia_se_conserva_en_get_y_post_cerrados(self):
        plan, ejecucion, _ = self.expediente_cerrado(participantes=False)
        self.reserva.participantes.add(self.ajeno)
        antes = self.operacion(ejecucion)
        respuesta = self.client.get(self.url("editar_ejecucion_practica", plan))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.reserva.registros_participantes.count(), 0)
        ejecucion = self.guardar_documentacion(
            plan,
            detalle_operativo_registrado="1",
            participantes_asistentes=[],
        )
        self.assertEqual(self.operacion(ejecucion), antes)
        self.assertEqual(self.reserva.registros_participantes.count(), 0)

    def test_recurso_y_persona_historicos_retirados_no_impiden_correccion(self):
        plan, ejecucion, _ = self.expediente_cerrado()
        responsable = ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=self.operador,
            nombre="Técnico histórico retirado de la operación actual",
            rol="responsable_tecnico",
            activo=False,
        )
        ejecucion.responsable_tecnico = responsable
        ejecucion.save(update_fields=["responsable_tecnico"])
        self.reserva.registros_participantes.all().delete()
        self.reserva.equipo_codigo = ""
        self.reserva.equipo_nombre = ""
        self.reserva.unidades_seleccionadas = "null"
        self.reserva.save(
            update_fields=["equipo_codigo", "equipo_nombre", "unidades_seleccionadas"]
        )
        antes = self.operacion(ejecucion)
        ejecucion = self.guardar_documentacion(
            plan,
            detalle_operativo_registrado="1",
            equipos_utilizados=["recurso-actual-inexistente"],
            participantes_asistentes=["persona-actual-inexistente"],
        )
        self.assertEqual(self.operacion(ejecucion), antes)
        self.assertEqual(
            ejecucion.detalle_operativo["equipos"][0]["codigo"], "CD-HIST-01"
        )
        self.assertEqual(
            ejecucion.detalle_operativo["participantes"][0]["asistencia_codigo"],
            "asistio",
        )

    def test_consumo_historico_mayor_a_autorizacion_actual_no_bloquea_documentacion(
        self,
    ):
        plan, ejecucion, consumo = self.expediente_cerrado()
        ReservaConsumible.objects.filter(pk=consumo.pk).update(
            cantidad_aprobada="0.500"
        )
        antes = self.operacion(ejecucion)
        ejecucion = self.guardar_documentacion(plan, **{f"consumo_{consumo.pk}": "0"})
        self.assertEqual(self.operacion(ejecucion), antes)
        consumo.refresh_from_db()
        self.assertGreater(consumo.cantidad_consumida, consumo.cantidad_aprobada)

    def test_snapshot_vacio_existente_no_se_reconstruye_con_datos_actuales(self):
        plan, ejecucion, _ = self.expediente_cerrado()
        EjecucionPractica.objects.filter(pk=ejecucion.pk).update(
            detalle_operativo={}, recursos_utilizados="Resumen legado sin snapshot."
        )
        antes = self.operacion(ejecucion)
        ejecucion = self.guardar_documentacion(plan, detalle_operativo_registrado="1")
        self.assertEqual(self.operacion(ejecucion), antes)
        self.assertEqual(ejecucion.detalle_operativo, {})

    def test_nueva_ft03_retrospectiva_documenta_sin_reescribir_el_cierre(self):
        plan, _, consumo = self.expediente_cerrado(
            crear_ft03=False, participantes=False
        )
        historico = deepcopy(self.reserva.detalle_ejecucion)
        antes = self.operacion()
        respuesta = self.client.get(self.url("editar_ejecucion_practica", plan))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(EjecucionPractica.objects.exists())
        self.assertEqual(self.operacion(), antes)
        ejecucion = self.guardar_documentacion(
            plan,
            detalle_operativo_registrado="1",
            equipos_utilizados=[],
            participantes_asistentes=["inexistente"],
            **{f"consumo_{consumo.pk}": "0"},
        )
        self.assertEqual(self.operacion(), antes)
        self.assertEqual(ejecucion.detalle_operativo, historico)
        self.assertEqual(ejecucion.recursos_utilizados, resumen_recursos(historico))
        self.assertEqual(ejecucion.estado, "borrador")

    def test_nueva_ft03_sin_snapshot_no_inventa_recursos_historicos(self):
        plan, _, consumo = self.expediente_cerrado(
            crear_ft03=False, participantes=False
        )
        self.reserva.detalle_ejecucion = {}
        self.reserva.save(update_fields=["detalle_ejecucion"])
        antes = self.operacion()
        ejecucion = self.guardar_documentacion(
            plan,
            detalle_operativo_registrado="1",
            equipos_utilizados=["legacy:CD-HIST-01"],
            **{f"consumo_{consumo.pk}": "0"},
        )
        self.assertEqual(self.operacion(), antes)
        self.assertEqual(ejecucion.detalle_operativo, {})
        self.assertEqual(ejecucion.recursos_utilizados, "")

    def test_cancelacion_terminal_no_reabre_asistencia_o_consumo(self):
        plan, ejecucion, consumo = self.expediente_cerrado(
            estado_reserva="cancelada", estado_ft03="borrador"
        )
        antes = self.operacion(ejecucion)
        ejecucion = self.guardar_documentacion(
            plan,
            detalle_operativo_registrado="1",
            participantes_asistentes=[],
            **{f"consumo_{consumo.pk}": "0"},
        )
        self.assertEqual(self.operacion(ejecucion), antes)
