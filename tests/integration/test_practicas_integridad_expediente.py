"""Integridad del expediente al conectar prácticas virtuales y presenciales."""

from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.practicas import _exigir_ejecucion_editable
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.reservas.models.reservas import CatalogoActividadReserva, NotificacionReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible
from apps.recursos.models.consumibles import Consumible
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad


class IntegridadExpedientePracticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.autor = usuario.objects.create_user("autor-integridad-practica")
        cls.operador = usuario.objects.create_user("operador-integridad-practica")
        cls.ajeno = usuario.objects.create_user("ajeno-integridad-practica")
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio de integridad de prácticas",
            slug="laboratorio-integridad-practicas",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.operador,
        )
        cls.actividad = CatalogoActividadReserva.objects.create(
            unidad=cls.unidad,
            nombre="Práctica de trazabilidad",
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            creado_por=cls.autor,
        )
        cls.reserva = Reserva.objects.create(
            laboratorio=cls.unidad,
            usuario=cls.autor,
            actividad_catalogo=cls.actividad,
            fecha=date(2026, 10, 10),
            hora_inicio=time(8),
            hora_fin=time(10),
            numero_participantes=4,
            estado="confirmada",
        )

    def plan(self, *, actividad=True, reserva=True, **extra):
        datos = {
            "unidad": self.unidad,
            "actividad": self.actividad if actividad else None,
            "reserva": self.reserva if reserva else None,
            "fecha": self.reserva.fecha,
            "hora_inicio": time(8),
            "hora_fin": time(10),
            "asignatura": "Logística de almacenamiento",
            "docente_tutor": "Docente de prueba",
            "tema": "Trazabilidad del inventario",
            "resultado_aprendizaje": "Conserva el balance de inventario.",
            "estudiantes_planificados": 4,
            "estado": "aprobada",
            "requiere_guia": False,
            "creado_por": self.autor,
        }
        datos.update(extra)
        return PlanificacionPractica.objects.create(**datos)

    def ejecucion(self, plan, estado="borrador", **extra):
        datos = {
            "planificacion": plan,
            "fecha_ejecucion": self.reserva.fecha,
            "hora_inicio_real": time(8, 5),
            "hora_fin_real": time(9, 55),
            "resultado": "ejecutada",
            "estudiantes_asistentes": 4,
            "cumplimiento_resultado": "si",
            "estado": estado,
            "creado_por": self.autor,
        }
        datos.update(extra)
        return EjecucionPractica.objects.create(**datos)

    def datos_ejecucion(self, **extra):
        datos = {
            "fecha_ejecucion": self.reserva.fecha.isoformat(),
            "hora_inicio_real": "08:05",
            "hora_fin_real": "09:55",
            "resultado": "ejecutada",
            "estudiantes_asistentes": "3",
            "cumplimiento_resultado": "si",
            "observaciones_docente": "Comprobación del balance.",
            "accion": "guardar",
        }
        datos.update(extra)
        return datos

    def url(self, nombre, plan):
        return reverse(nombre, args=[self.unidad.slug, plan.pk])

    def test_plan_sin_actividad_rechaza_a_tercero_sin_error_interno(self):
        plan = self.plan(actividad=False, reserva=False)
        self.client.force_login(self.ajeno)
        for nombre in (
            "detalle_planificacion_practica",
            "planificacion_practica_pdf",
            "editar_planificacion_practica",
            "editar_ejecucion_practica",
        ):
            with self.subTest(vista=nombre):
                self.assertEqual(
                    self.client.get(self.url(nombre, plan)).status_code, 403
                )
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_plan_sin_actividad_sigue_visible_para_autor_y_operador(self):
        plan = self.plan(actividad=False, reserva=False)
        for usuario in (self.autor, self.operador):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.username):
                self.assertContains(
                    self.client.get(self.url("detalle_planificacion_practica", plan)),
                    plan.tema,
                )

    def test_participante_autorizado_conserva_acceso_sin_poder_editar(self):
        plan = self.plan()
        self.actividad.participantes_autorizados.add(self.ajeno)
        self.client.force_login(self.ajeno)
        self.assertEqual(
            self.client.get(
                self.url("detalle_planificacion_practica", plan)
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                self.url("editar_ejecucion_practica", plan), self.datos_ejecucion()
            ).status_code,
            403,
        )
        self.assertFalse(EjecucionPractica.objects.exists())

    def test_nueva_version_conserva_obligacion_documental_y_tema_del_silabo(self):
        asignatura = Asignatura.objects.create(
            unidad=self.unidad,
            codigo="QA-LOG",
            nombre="Logística de almacenamiento",
        )
        tema = TemaAsignatura.objects.create(
            asignatura=asignatura, nombre="Balance y trazabilidad"
        )
        plan = self.plan(tema_asignatura=tema)
        self.ejecucion(plan, estado="validada")
        self.client.force_login(self.operador)
        respuesta = self.client.post(
            self.url("accion_planificacion_practica", plan),
            {"accion": "nueva_version"},
        )
        self.assertEqual(respuesta.status_code, 302)
        nueva = PlanificacionPractica.objects.exclude(pk=plan.pk).get()
        self.assertFalse(nueva.requiere_guia)
        self.assertEqual(nueva.tema_asignatura_id, tema.pk)
        self.assertEqual(nueva.estado, "borrador")
        self.assertEqual(nueva.grupo_version, plan.grupo_version)
        self.assertEqual(nueva.numero_version, plan.numero_version + 1)
        self.assertIsNone(nueva.reserva_id)
        self.assertFalse(EjecucionPractica.objects.filter(planificacion=nueva).exists())
        plan.refresh_from_db()
        self.assertFalse(plan.es_version_vigente)
        self.assertEqual(plan.reserva_id, self.reserva.pk)

    def test_nueva_version_preserva_tambien_requiere_guia_verdadero(self):
        plan = self.plan(requiere_guia=True)
        self.client.force_login(self.operador)
        self.client.post(
            self.url("accion_planificacion_practica", plan),
            {"accion": "nueva_version"},
        )
        self.assertTrue(
            PlanificacionPractica.objects.exclude(pk=plan.pk).get().requiere_guia
        )

    def test_repetir_nueva_version_desde_version_reemplazada_no_duplica(self):
        plan = self.plan()
        self.client.force_login(self.operador)
        for _ in range(2):
            respuesta = self.client.post(
                self.url("accion_planificacion_practica", plan),
                {"accion": "nueva_version"},
            )
            self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(PlanificacionPractica.objects.count(), 2)
        self.assertEqual(
            PlanificacionPractica.objects.filter(es_version_vigente=True).count(), 1
        )
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)

    def test_revision_no_admite_get_ni_post_del_autor_o_del_operador(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="revision")
        antes = EjecucionPractica.objects.values().get(pk=ejecucion.pk)
        for usuario in (self.autor, self.operador):
            self.client.force_login(usuario)
            for metodo in ("get", "post"):
                with self.subTest(usuario=usuario.username, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(
                        self.url("editar_ejecucion_practica", plan),
                        self.datos_ejecucion(),
                    )
                    self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(EjecucionPractica.objects.values().get(pk=ejecucion.pk), antes)
        self.assertEqual(self.reserva.registros_participantes.count(), 0)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_validada_conserva_asistencia_evidencias_y_datos_frente_a_edicion(self):
        plan = self.plan()
        ejecucion = self.ejecucion(
            plan,
            estado="validada",
            validado_por=self.operador,
            validado_en=timezone.now(),
        )
        antes = EjecucionPractica.objects.values().get(pk=ejecucion.pk)
        for usuario in (self.autor, self.operador):
            self.client.force_login(usuario)
            for metodo in ("get", "post"):
                with self.subTest(usuario=usuario.username, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(
                        self.url("editar_ejecucion_practica", plan),
                        self.datos_ejecucion(accion="enviar"),
                    )
                    self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(EjecucionPractica.objects.values().get(pk=ejecucion.pk), antes)
        self.assertTrue(EjecucionPractica.objects.get(pk=ejecucion.pk).es_efectiva)
        self.assertEqual(EvidenciaPractica.objects.count(), 0)
        self.assertEqual(self.reserva.registros_participantes.count(), 0)

    def test_revision_se_devuelve_corrige_y_valida_mediante_flujo_existente(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="revision")
        self.client.force_login(self.operador)
        self.client.post(
            self.url("accion_ejecucion_practica", plan),
            {"accion": "observar", "observaciones": "Verifica el total real."},
        )
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "observada")
        self.client.force_login(self.autor)
        respuesta = self.client.post(
            self.url("editar_ejecucion_practica", plan), self.datos_ejecucion()
        )
        self.assertEqual(respuesta.status_code, 302)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "borrador")
        self.assertEqual(ejecucion.estudiantes_asistentes, 3)
        self.client.post(
            self.url("editar_ejecucion_practica", plan),
            self.datos_ejecucion(accion="enviar"),
        )
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.client.force_login(self.operador)
        self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
        )
        ejecucion.refresh_from_db()
        self.reserva.refresh_from_db()
        self.assertTrue(ejecucion.es_efectiva)
        self.assertEqual(self.reserva.estado, "completada")
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.filter(accion="observar").count(), 1
        )

    def test_devolucion_exige_motivo_y_solo_operador_puede_realizarla(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="revision")
        self.client.force_login(self.autor)
        respuesta = self.client.post(
            self.url("accion_ejecucion_practica", plan),
            {"accion": "observar", "observaciones": "Corrección"},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.client.force_login(self.operador)
        self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "observar"}
        )
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_validada_no_se_reabre_ni_valida_nuevamente_por_accion_directa(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="validada")
        self.client.force_login(self.operador)
        for accion in ("observar", "validar"):
            with self.subTest(accion=accion):
                respuesta = self.client.post(
                    self.url("accion_ejecucion_practica", plan),
                    {"accion": accion, "observaciones": "Intento de reapertura"},
                )
                self.assertEqual(respuesta.status_code, 403)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_edicion_relee_estado_bajo_bloqueo_antes_de_escribir(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan)
        llamadas = 0

        def intercalar_revision(objeto):
            nonlocal llamadas
            _exigir_ejecucion_editable(objeto)
            llamadas += 1
            if llamadas == 1:
                EjecucionPractica.objects.filter(pk=ejecucion.pk).update(
                    estado="revision"
                )

        self.client.force_login(self.autor)
        with patch(
            "apps.formacion.presentation.practicas._exigir_ejecucion_editable",
            side_effect=intercalar_revision,
        ):
            respuesta = self.client.post(
                self.url("editar_ejecucion_practica", plan), self.datos_ejecucion()
            )
        self.assertEqual(respuesta.status_code, 403)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.assertEqual(ejecucion.estudiantes_asistentes, 4)
        self.assertEqual(self.reserva.registros_participantes.count(), 0)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_ejecucion_archivada_no_admite_cambios(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, eliminado_en=timezone.now())
        self.client.force_login(self.autor)
        respuesta = self.client.post(
            self.url("editar_ejecucion_practica", plan), self.datos_ejecucion()
        )
        self.assertEqual(respuesta.status_code, 403)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estudiantes_asistentes, 4)

    def test_listado_precarga_ejecuciones_sin_consulta_por_plan(self):
        for indice in range(8):
            plan = self.plan(reserva=False, tema=f"Práctica {indice}")
            if indice % 2:
                self.ejecucion(plan, estado="revision")
        self.client.force_login(self.operador)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(
                reverse("lista_practicas", args=[self.unidad.slug])
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["planes"]), 8)
        consultas_ejecuciones = [
            item["sql"]
            for item in consultas
            if "webcitt_ejecucionpractica" in item["sql"].lower()
            and item["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertEqual(len(consultas_ejecuciones), 1)
        self.assertIn("JOIN", consultas_ejecuciones[0].upper())
        self.assertNotIn(
            '"webcitt_ejecucionpractica"."detalle_operativo"', consultas_ejecuciones[0]
        )
        self.assertContains(respuesta, "Pendiente de revisión")

    def test_cierre_operativo_se_valida_documentalmente_sin_repetir_cierre(self):
        plan = self.plan()
        self.client.force_login(self.operador)
        cierre = self.client.post(
            reverse("gestion_reserva_accion", args=[self.unidad.slug, self.reserva.pk]),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "08:05",
                "ejecucion_hora_fin": "09:55",
                "ejecucion_asistentes_total": "3",
                "ejecucion_cumplimiento": "si",
                "ejecucion_consumibles_json": "[]",
                "ejecucion_observaciones": "Balance físico verificado.",
            },
        )
        self.assertEqual(cierre.status_code, 200, cierre.content)
        self.assertTrue(cierre.json()["success"], cierre.content)
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual(ejecucion.estado, "revision")
        reserva_antes = Reserva.objects.values().get(pk=self.reserva.pk)
        detalle_antes = ejecucion.detalle_operativo
        avisos_antes = NotificacionReserva.objects.filter(reserva=self.reserva).count()
        cierres_antes = RegistroAuditoriaUnidad.objects.filter(
            accion="completar"
        ).count()
        asistentes_antes = list(self.reserva.registros_participantes.values())
        with patch(
            "apps.formacion.presentation.practicas.notificar_cambio_reserva"
        ) as notificar:
            respuesta = self.client.post(
                self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
            )
        self.assertEqual(respuesta.status_code, 302)
        notificar.assert_not_called()
        ejecucion.refresh_from_db()
        self.assertTrue(ejecucion.es_efectiva)
        self.assertEqual(ejecucion.detalle_operativo, detalle_antes)
        self.assertEqual(
            Reserva.objects.values().get(pk=self.reserva.pk), reserva_antes
        )
        self.assertEqual(
            list(self.reserva.registros_participantes.values()), asistentes_antes
        )
        self.assertEqual(
            NotificacionReserva.objects.filter(reserva=self.reserva).count(),
            avisos_antes,
        )
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.filter(accion="completar").count(),
            cierres_antes,
        )
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.filter(
                entidad=EjecucionPractica._meta.label, accion="aprobar"
            ).count(),
            1,
        )

    def test_validacion_documental_preserva_consumos_asistencia_y_evidencias(self):
        plan = self.plan()
        Reserva.objects.filter(pk=self.reserva.pk).update(
            estado="completada",
            resultado_cierre="atendida",
            fecha_cierre=timezone.now(),
            detalle_ejecucion={
                "version": 2,
                "asistentes_total": 3,
                "consumibles": [{"cantidad": "1"}],
            },
        )
        consumible = Consumible.objects.create(
            unidad=self.unidad,
            codigo="QA-ETIQUETA-01",
            nombre="Etiqueta trazable",
            clasificacion="empaque",
            unidad_medida="unidad",
        )
        ReservaConsumible.objects.create(
            reserva=self.reserva,
            consumible=consumible,
            cantidad_solicitada=2,
            cantidad_aprobada=2,
            cantidad_consumida=1,
        )
        RegistroParticipanteReserva.objects.create(
            reserva=self.reserva,
            usuario=self.autor,
            nombre="Docente de prueba",
            rol="solicitante",
            asistencia="asistio",
        )
        ejecucion = self.ejecucion(
            plan,
            estado="revision",
            detalle_operativo={"consumibles": [{"cantidad": "1"}]},
        )
        EvidenciaPractica.objects.create(
            ejecucion=ejecucion,
            tipo="bitacora",
            archivo="practicas/qa/evidencia.csv",
            nombre_original="evidencia.csv",
            descripcion="Balance físico identificado.",
            subido_por=self.autor,
        )
        antes = {
            "reserva": Reserva.objects.values().get(pk=self.reserva.pk),
            "asistencia": list(self.reserva.registros_participantes.values()),
            "consumos": list(self.reserva.consumibles_solicitados.values()),
            "evidencias": list(ejecucion.evidencias.values()),
            "detalle": ejecucion.detalle_operativo,
        }
        self.client.force_login(self.operador)
        respuesta = self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
        )
        self.assertEqual(respuesta.status_code, 302)
        ejecucion.refresh_from_db()
        self.assertTrue(ejecucion.es_efectiva)
        self.assertEqual(
            Reserva.objects.values().get(pk=self.reserva.pk), antes["reserva"]
        )
        self.assertEqual(
            list(self.reserva.registros_participantes.values()), antes["asistencia"]
        )
        self.assertEqual(
            list(self.reserva.consumibles_solicitados.values()), antes["consumos"]
        )
        self.assertEqual(list(ejecucion.evidencias.values()), antes["evidencias"])
        self.assertEqual(ejecucion.detalle_operativo, antes["detalle"])

    def test_cierre_previo_otro_motivo_o_cancelado_no_autoriza_validacion(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan, estado="revision")
        self.client.force_login(self.operador)
        for estado, cierre, resultado in (
            ("completada", "no_atendida", "ejecutada"),
            ("completada", "", "ejecutada"),
            ("cancelada", "atendida", "ejecutada"),
            ("completada", "atendida", "cancelada"),
        ):
            with self.subTest(estado=estado, cierre=cierre, resultado=resultado):
                Reserva.objects.filter(pk=self.reserva.pk).update(
                    estado=estado, resultado_cierre=cierre
                )
                EjecucionPractica.objects.filter(pk=ejecucion.pk).update(
                    resultado=resultado, motivo="Motivo documentado."
                )
                respuesta = self.client.post(
                    self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
                )
                self.assertEqual(respuesta.status_code, 302)
                ejecucion.refresh_from_db()
                self.reserva.refresh_from_db()
                self.assertEqual(ejecucion.estado, "revision")
                self.assertFalse(ejecucion.es_efectiva)
                self.assertEqual(
                    (self.reserva.estado, self.reserva.resultado_cierre),
                    (estado, cierre),
                )
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)

    def test_cierre_atendido_no_omite_compuerta_documental_obligatoria(self):
        plan = self.plan(requiere_guia=True)
        Reserva.objects.filter(pk=self.reserva.pk).update(
            estado="completada",
            resultado_cierre="atendida",
            proposito_codigo="docencia_practica",
            vinculacion_actividad="manual",
        )
        ejecucion = self.ejecucion(plan, estado="revision")
        self.client.force_login(self.operador)
        respuesta = self.client.post(
            self.url("accion_ejecucion_practica", plan), {"accion": "validar"}
        )
        self.assertEqual(respuesta.status_code, 302)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.assertFalse(ejecucion.es_efectiva)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 0)
