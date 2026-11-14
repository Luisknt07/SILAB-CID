"""Servicios: política de cobro, materiales elegidos, piezas, urgencia y entrega."""

from tests.integration.utiles import verificar_pertenencia
import json
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.reservas.presentation.comprobantes import construir_comprobante_reserva, render_comprobante_reserva_pdf
from apps.reservas.presentation.cotizaciones import calcular_costo_referencial_recursos
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.laboratorios.operacion.models.fablab import FablabService, FablabServiceConsumible, SolicitudFabricacion
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


INTENCION_SERVICIO = (
    "Necesito fabricar la carcasa de un prototipo de sensor de humedad para el proyecto de "
    "investigación sobre riego inteligente. Son dos piezas de 80 × 40 × 20 mm en PLA rojo, con "
    "tapa a presión y dos orificios laterales para el paso de cables; requiero acabado natural "
    "sin soportes visibles y una tolerancia de 0,3 mm para el ensamblaje con la placa "
    "electrónica. Adjunto el modelo STL ya laminado y necesito la entrega antes de la feria."
)


def _dia_habil_desde(fecha):
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha


def _siguiente_dia_habil(fecha):
    return _dia_habil_desde(fecha + timedelta(days=1))


class ServiciosTrabajoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="estudiante.servicios",
            email="estudiante.servicios@upec.edu.ec",
            password="prueba-segura",
            first_name="Rosa",
            last_name="Cadena",
        )
        perfil = cls.usuario.profile
        perfil.carrera = "computacion"
        perfil.tipo_usuario = "estudiante"
        perfil.facultad = "agropecuarias_ambientales"
        perfil.nivel_academico = "quinto_semestre"
        perfil.cedula = "2026-0101"
        perfil.institucion = "UPEC"
        perfil.save()
        verificar_pertenencia(cls.usuario)
        cls.laboratorio = Unidad.objects.create(
            nombre="Laboratorio de servicios",
            descripcion="Unidad usada para verificar el flujo de servicios.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-servicios-trabajo",
        )
        cls.equipo = EquiposServicios.objects.create(codigo="EQ-SRV-FDM", nombre="Impresora FDM")
        cls.unidad_equipo = UnidadEquipo.objects.create(
            codigo_unidad="UE-SRV-001",
            equipo=cls.equipo,
            laboratorio=cls.laboratorio,
            estado_unidad="disponible",
            activa=True,
        )
        cls.material = Consumible.objects.create(
            unidad=cls.laboratorio,
            codigo="MAT-SRV-PLA",
            nombre="Filamento PLA",
            color="Rojo",
            unidad_medida="kg",
            stock_total=Decimal("20"),
            precio_unitario=Decimal("2.0000"),
        )
        cls.opcional = Consumible.objects.create(
            unidad=cls.laboratorio,
            codigo="MAT-SRV-CINTA",
            nombre="Cinta de enmascarar",
            unidad_medida="rollo",
            stock_total=Decimal("10"),
            precio_unitario=Decimal("1.0000"),
        )
        cls.servicio = FablabService.objects.create(
            code="SRV-TRABAJO",
            nombre="Impresión 3D FDM",
            unidad=cls.laboratorio,
            activo=True,
            publico=True,
            requiere_cotizacion=True,
            tarifa_base=Decimal("10.00"),
            horas_equipo_estimadas=Decimal("2.00"),
            costo_hora_equipo=Decimal("3.00"),
            horas_mano_obra_estimadas=Decimal("1.00"),
            costo_hora_mano_obra=Decimal("4.00"),
            costo_diseno_completo=Decimal("20.00"),
            descuento_estudiante=Decimal("40.00"),
        )
        FablabServiceConsumible.objects.create(
            service=cls.servicio,
            consumible=cls.material,
            cantidad_sugerida=Decimal("1.250"),
            obligatorio=True,
        )
        FablabServiceConsumible.objects.create(
            service=cls.servicio,
            consumible=cls.opcional,
            cantidad_sugerida=Decimal("2"),
            obligatorio=False,
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def _cotizar(self, **extra):
        parametros = {
            "unidad_id": self.laboratorio.pk,
            "servicios": [self.servicio.pk],
            "modalidad": "diseno_completo",
        }
        parametros.update(extra)
        respuesta = self.client.get(reverse("cotizar_servicios_reserva"), parametros)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()["cotizacion"]

    def _proponer(self, **extra):
        parametros = {
            "unidad_id": self.laboratorio.pk,
            "servicios": [self.servicio.pk],
            "modalidad": "modelo_listo",
            "urgencia": "urgente",
        }
        parametros.update(extra)
        return self.client.get(reverse("proponer_entrega_servicio"), parametros)

    def _ocupar(self, fecha, horas, **extra):
        datos = {
            "laboratorio": self.laboratorio,
            "usuario": self.usuario,
            "tipo_solicitud": "servicio",
            "fecha": fecha,
            "hora_inicio": time(horas[0], 0),
            "hora_fin": time(horas[-1] + 1, 0),
            "horas_seleccionadas": json.dumps(horas),
            "proposito": "Servicio",
            "equipo_codigo": "SRV",
            "equipo_nombre": "Servicio ocupado",
            "estado": "pendiente",
        }
        datos.update(extra)
        return Reserva.objects.create(**datos)

    # ------------------------------------------------------------ cotización
    def test_politica_predeterminada_cobra_solo_materiales(self):
        """La UPEC asume equipo, diseño, tarifa base y personal."""
        cotizacion = self._cotizar()

        # Referencia: base 10 + equipo 6 + mano de obra 4 + diseño 20 + PLA 2.50 + cinta 2.
        self.assertEqual(cotizacion["valor_referencial"], "44.50")
        self.assertEqual(cotizacion["no_cobrado"], "40.00")
        self.assertEqual(cotizacion["descuentos_segmento"], "0.00")
        self.assertEqual(cotizacion["aporte_institucional"], "40.00")
        self.assertEqual(cotizacion["total_insumos"], "4.50")
        self.assertEqual(cotizacion["valor_estimado_usuario"], "4.50")
        componentes = {item["clave"]: item for item in cotizacion["conceptos"][0]["componentes"]}
        self.assertFalse(componentes["tarifa_base"]["cobrado"])
        self.assertFalse(componentes["uso_equipo"]["cobrado"])
        self.assertFalse(componentes["mano_obra"]["cobrado"])
        self.assertFalse(componentes["diseno"]["cobrado"])
        self.assertEqual(componentes["uso_equipo"]["detalle"], "2 h · $3.00 por hora")
        self.assertEqual(cotizacion["horas_equipo_estimadas"], "2")
        self.assertIn("se muestran como referencia", cotizacion["advertencia"])
        materiales = {item["id"]: item for item in cotizacion["materiales_planificados"]}
        self.assertTrue(materiales[self.material.pk]["obligatorio"])
        self.assertFalse(materiales[self.opcional.pk]["obligatorio"])
        self.assertEqual(materiales[self.material.pk]["variante"], "Rojo")

    def test_la_upec_asume_la_maquina_en_todas_las_modalidades(self):
        completo = self._cotizar(modalidad="diseno_completo")
        listo = self._cotizar(modalidad="modelo_listo")
        asistido = self._cotizar(modalidad="diseno_asistido")

        self.assertFalse(completo["politica_cobro"]["uso_equipo"])
        self.assertFalse(listo["politica_cobro"]["uso_equipo"])
        self.assertFalse(asistido["politica_cobro"]["uso_equipo"])
        componentes = {item["clave"]: item for item in completo["conceptos"][0]["componentes"]}
        self.assertEqual(componentes["uso_equipo"]["valor_usuario"], "0.00")

        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.laboratorio)
        configuracion.cobrar_uso_equipo_ejecucion = False
        configuracion.save()

        apagado = self._cotizar(modalidad="diseno_completo")
        self.assertFalse(apagado["politica_cobro"]["uso_equipo"])
        self.assertEqual(apagado["valor_estimado_usuario"], "4.50")

    def test_la_cotizacion_avisa_cuando_falta_la_cantidad_de_un_material(self):
        """Sin cantidad no hay valor: decirlo evita una estimación engañosa."""
        cotizacion = self._cotizar(
            cantidades=json.dumps({str(self.material.pk): "0"}),
        )

        self.assertEqual(cotizacion["materiales_por_calcular"], [self.material.nombre])
        self.assertIn("Falta la cantidad de", cotizacion["aviso_estimacion"])
        self.assertIn("estimación previa", cotizacion["aviso_estimacion"])
        # Ese material no suma al valor mientras no se conozca la cantidad.
        self.assertEqual(cotizacion["total_insumos"], "2.00")

        completa = self._cotizar()
        self.assertEqual(completa["materiales_por_calcular"], [])
        self.assertEqual(completa["aviso_estimacion"], "")

    def test_banderas_antiguas_no_reactivan_cobros_institucionales(self):
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.laboratorio)
        configuracion.cobrar_tarifa_base = True
        configuracion.cobrar_uso_equipo = True
        configuracion.save()

        cotizacion = self._cotizar()

        self.assertEqual(cotizacion["no_cobrado"], "40.00")
        self.assertEqual(cotizacion["descuentos_segmento"], "0.00")
        self.assertEqual(cotizacion["aporte_institucional"], "40.00")
        self.assertEqual(cotizacion["valor_estimado_usuario"], "4.50")
        self.assertFalse(cotizacion["politica_cobro"]["tarifa_base"])
        self.assertFalse(cotizacion["politica_cobro"]["mano_obra"])

    def test_iva_configurable_se_suma_solo_al_valor_del_usuario(self):
        sin_iva = self._cotizar()
        self.assertFalse(sin_iva["iva"]["aplica"])
        self.assertEqual(sin_iva["subtotal_usuario"], sin_iva["valor_estimado_usuario"])
        componentes = {item["clave"]: item for item in sin_iva["conceptos"][0]["componentes"]}
        # Todos los componentes institucionales quedan cubiertos completos.
        self.assertEqual(componentes["tarifa_base"]["aporte_institucional"], "10.00")
        self.assertEqual(componentes["tarifa_base"]["valor_usuario"], "0.00")
        self.assertEqual(componentes["uso_equipo"]["aporte_institucional"], "6.00")
        self.assertEqual(componentes["uso_equipo"]["valor_usuario"], "0.00")
        self.assertEqual(componentes["diseno"]["descuento"], "0.00")
        self.assertEqual(componentes["diseno"]["valor_usuario"], "0.00")
        self.assertEqual(componentes["uso_equipo"]["cantidad"], "2 h")
        self.assertEqual(componentes["uso_equipo"]["precio_unitario"], "$3.00 por hora")

        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.laboratorio)
        configuracion.aplicar_iva = True
        configuracion.porcentaje_iva = Decimal("15.00")
        configuracion.save()
        con_iva = self._cotizar()
        self.assertTrue(con_iva["iva"]["aplica"])
        self.assertEqual(con_iva["subtotal_usuario"], "4.50")
        self.assertEqual(con_iva["iva"]["monto"], "0.68")
        self.assertEqual(con_iva["valor_estimado_usuario"], "5.18")
        self.assertEqual(con_iva["valor_referencial"], "44.50")

        recursos = calcular_costo_referencial_recursos(
            [(self.material, Decimal("2"), "estimacion")],
            self.usuario,
            configuracion=configuracion,
            recursos=[{"id": self.unidad_equipo.pk}],
            duracion_horas=2,
        )
        self.assertEqual(recursos["subtotal_usuario"], "4.00")
        self.assertEqual(recursos["iva"]["monto"], "0.60")
        self.assertEqual(recursos["valor_estimado_usuario"], "4.60")

    def test_seleccion_explicita_y_piezas(self):
        solo_obligatorios = self._cotizar(seleccion="[]")
        ids = [item["id"] for item in solo_obligatorios["materiales_planificados"]]
        self.assertEqual(ids, [self.material.pk])
        self.assertEqual(solo_obligatorios["total_insumos"], "2.50")

        con_opcional = self._cotizar(seleccion=json.dumps([self.opcional.pk]), piezas="3")
        materiales = {item["id"]: item for item in con_opcional["materiales_planificados"]}
        self.assertEqual(materiales[self.material.pk]["cantidad"], "3.75")
        self.assertEqual(materiales[self.opcional.pk]["cantidad"], "6")
        self.assertEqual(con_opcional["piezas"], 3)
        self.assertEqual(con_opcional["horas_equipo_estimadas"], "6")
        self.assertEqual(con_opcional["conceptos"][0]["uso_equipo"], "18.00")

        invalida = self.client.get(
            reverse("cotizar_servicios_reserva"),
            {
                "unidad_id": self.laboratorio.pk,
                "servicios": [self.servicio.pk],
                "modalidad": "modelo_listo",
                "piezas": "0",
            },
        )
        self.assertEqual(invalida.status_code, 400)
        self.assertIn("piezas", invalida.json()["error"])

    # ------------------------------------------------------------ entrega
    def test_propuesta_urgente_usa_el_siguiente_dia_habil_y_evita_la_cola(self):
        hoy = timezone.localdate()
        esperada = _siguiente_dia_habil(hoy)

        propuesta = self._proponer().json()["propuesta"]
        self.assertEqual(propuesta["fecha"], esperada.isoformat())
        self.assertEqual(propuesta["hora_inicio"], "08:00")
        self.assertEqual(propuesta["hora_fin"], "10:00")
        self.assertEqual(propuesta["horas_seleccionadas"], [8, 9])
        self.assertEqual(propuesta["fecha_entrega"], esperada.isoformat())
        self.assertEqual(propuesta["urgencia"], "urgente")
        self.assertEqual(propuesta["cola"], {"solicitudes": 0, "horas": 0})

        self._ocupar(esperada, [7, 8, 9])
        desplazada = self._proponer().json()["propuesta"]
        self.assertEqual(desplazada["fecha"], esperada.isoformat())
        self.assertEqual(desplazada["hora_inicio"], "10:00")
        self.assertEqual(desplazada["cola"]["solicitudes"], 1)

    def test_propuesta_normal_respeta_la_cola_y_reparte_piezas_en_varios_dias(self):
        hoy = timezone.localdate()
        # La cola se ocupa lejos del día propuesto: lo que desplaza la entrega
        # son sus horas, y llenarlas en el propio día propuesto hacía que la
        # prueba dependiera del día de la semana en que se ejecutara.
        self._ocupar(_dia_habil_desde(hoy + timedelta(days=20)), [7, 8, 9])

        # Cola de 3 h → 2 días base + 1 día por la cola.
        propuesta = self._proponer(urgencia="normal", piezas="10").json()["propuesta"]
        esperada = _dia_habil_desde(hoy + timedelta(days=3))
        self.assertEqual(propuesta["fecha"], esperada.isoformat())
        # 20 h de máquina en jornadas de 10 h (08:00–18:00): bloque completo y
        # entrega al día siguiente.
        self.assertEqual(propuesta["horas_estimadas"], 20)
        self.assertEqual(propuesta["hora_inicio"], "08:00")
        self.assertEqual(propuesta["hora_fin"], "18:00")
        self.assertEqual(propuesta["fecha_entrega"], _siguiente_dia_habil(esperada).isoformat())
        self.assertEqual(propuesta["urgencia"], "normal")

    def test_incumplimiento_reciente_retira_la_atencion_urgente(self):
        hoy = timezone.localdate()
        self._ocupar(
            hoy - timedelta(days=10),
            [9, 10],
            estado="completada",
            detalle_ejecucion={"cumplimiento_resultado": "no"},
        )

        propuesta = self._proponer().json()["propuesta"]
        self.assertEqual(propuesta["urgencia"], "normal")
        self.assertTrue(propuesta["avisos"])
        self.assertIn("no utilizada", propuesta["avisos"][0])
        self.assertEqual(propuesta["fecha"], _dia_habil_desde(hoy + timedelta(days=2)).isoformat())

    # ------------------------------------------------------------ creación
    def test_el_material_del_servicio_se_ve_como_en_el_catalogo_de_insumos(self):
        """La misma ficha en los dos caminos: imagen, tipo, variante y color.

        Quien encarga un servicio ve el material tal como lo vería al reservar
        recursos, y en ambos casos la cantidad es obligatoria.
        """
        Consumible.objects.filter(pk=self.material.pk).update(
            clasificacion="material",
            variante="Estándar 1,75 mm",
            imagen_catalogo="img/catalogo/fablab/filamentos-pla-colores.png",
        )

        respuesta = self.client.get(
            reverse("laboratorio_detalle", args=[self.laboratorio.slug])
        )

        self.assertEqual(respuesta.status_code, 200)
        servicio = next(
            item
            for item in respuesta.context["servicios_reserva"]
            if item.pk == self.servicio.pk
        )
        ficha = next(
            item
            for item in servicio.consumibles_planificados
            if item["id"] == self.material.pk
        )
        self.assertEqual(ficha["clasificacion"], "Material")
        self.assertEqual(ficha["variante"], "Estándar 1,75 mm")
        self.assertEqual(ficha["color"], "Rojo")
        self.assertEqual(ficha["detalle"], "Estándar 1,75 mm · Rojo")
        self.assertEqual(
            ficha["imagen"],
            static("img/catalogo/fablab/filamentos-pla-colores.png"),
        )
        # La fila del trabajo usa las mismas piezas visuales que la tarjeta del
        # catálogo de insumos, no una lista aparte.
        self.assertContains(respuesta, "reservation-service-material__quantity")
        self.assertContains(respuesta, "reservation-consumable__variants")
        self.assertContains(respuesta, "reservation-consumable__stock")
        self.assertContains(respuesta, "Referencia del catálogo:")
        # La cantidad es obligatoria en los dos caminos: no se puede dejar vacía.
        self.assertNotContains(respuesta, "No conozco la cantidad")
        self.assertNotContains(respuesta, "estimación previa")

    def test_creacion_guarda_trabajo_entrega_y_orden_urgente(self):
        fecha = _dia_habil_desde(timezone.localdate() + timedelta(days=7))
        entrega = _siguiente_dia_habil(fecha)
        respuesta = self.client.post(reverse("crear_reserva"), {
            "unidad_id": self.laboratorio.pk,
            "fecha_inicio": f"{fecha.isoformat()}T09:00",
            "fecha_fin": f"{fecha.isoformat()}T13:00",
            "horas_seleccionadas": json.dumps([9, 10, 11, 12]),
            "proposito": "Investigación",
            "proposito_codigo": "investigacion_innovacion",
            "descripcion_proyecto": "Carcasa de sensor para prueba de campo.",
            "participantes_seleccionados": "[]",
            "aceptar_terminos": "on",
            "tipo_solicitud": "servicio",
            "modalidad_servicio": "diseno_completo",
            "provision_consumibles": "ninguno",
            "unidades_seleccionadas": "[]",
            "servicios_solicitados": [str(self.servicio.pk)],
            "cotizacion_aceptada": "true",
            "metodo_pago": "transferencia",
            "cantidad_piezas": "2",
            "urgencia_servicio": "urgente",
            "detalle_trabajo": "Dos carcasas de 80 × 40 × 20 mm, acabado natural.",
            "fecha_entrega_prevista": entrega.isoformat(),
            "materiales_seleccionados": "[]",
            "consumibles_servicio": "{}",
            "equipo_servicio": str(self.equipo.pk),
            "intencion_solicitud": INTENCION_SERVICIO,
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.content)

        reserva = Reserva.objects.get(pk=respuesta.json()["reserva_id"])
        self.assertIn("Finalidad: Necesito fabricar la carcasa", reserva.descripcion_proyecto)
        self.assertEqual(reserva.intencion_solicitud, INTENCION_SERVICIO)
        self.assertEqual(reserva.cantidad_piezas, 2)
        self.assertEqual(reserva.urgencia_servicio, "urgente")
        self.assertEqual(reserva.fecha_entrega_prevista, entrega)
        self.assertIn("80 × 40 × 20", reserva.detalle_trabajo)
        self.assertEqual(reserva.desglose_cotizacion["trabajo"]["equipo"]["id"], self.equipo.pk)
        # Solo el material obligatorio (1.25 kg × 2 piezas); la cinta opcional no se pidió.
        solicitado = reserva.consumibles_solicitados.get()
        self.assertEqual(solicitado.consumible, self.material)
        self.assertEqual(solicitado.cantidad_solicitada, Decimal("2.500"))
        # Solo el PLA se traslada al usuario: 2.5 kg a $2.
        self.assertEqual(reserva.costo_estimado, Decimal("5.00"))

        orden = SolicitudFabricacion.objects.get(reserva=reserva)
        self.assertEqual(orden.prioridad, "urgente")
        self.assertEqual(orden.tiempo_estimado_horas, Decimal("6.00"))
        self.assertEqual(orden.fecha_programada_inicio.date(), fecha)
        self.assertEqual(orden.fecha_programada_fin.date(), entrega)
        self.assertEqual(list(orden.maquinas_requeridas.all()), [self.equipo])
        self.assertIn("Filamento PLA (2.5 kg)", orden.materiales_principales)

        comprobante = self.client.get(reverse("comprobante_reserva", args=[reserva.pk]))
        self.assertEqual(comprobante.status_code, 200)
        self.assertContains(comprobante, "Detalle económico estimado")
        self.assertContains(comprobante, "2 piezas · Urgente")
        self.assertContains(comprobante, entrega.strftime("%d/%m/%Y"))
        self.assertContains(comprobante, "Referencial · lo asume la UPEC")
        self.assertContains(comprobante, "Se cobra según consumo real")
        self.assertContains(comprobante, "Valor estimado a tu cargo")
        self.assertContains(comprobante, "Lo asume la UPEC")
        # Un servicio: sus cuatro componentes y su material, sin repeticiones.
        contenido = comprobante.content.decode()
        self.assertEqual(contenido.count("Impresión 3D FDM · Tarifa base del servicio"), 1)
        self.assertEqual(contenido.count("Impresión 3D FDM · Uso de equipo"), 1)
        pdf = render_comprobante_reserva_pdf(construir_comprobante_reserva(reserva))
        self.assertTrue(pdf.startswith(b"%PDF"))

        detalle = self.client.get(reverse("obtener_reservas_usuario")).json()
        registro = next(item for item in detalle["reservas"] if item["id"] == reserva.pk)
        self.assertEqual(registro["cantidad_piezas"], 2)
        self.assertEqual(registro["fecha_entrega_prevista"], entrega.isoformat())
        self.assertEqual(registro["urgencia_servicio_display"], "Urgente: 1 a 2 días laborables")

    def test_la_descripcion_del_trabajo_exige_entre_50_y_200_palabras(self):
        fecha = _dia_habil_desde(timezone.localdate() + timedelta(days=7))
        base = {
            "unidad_id": self.laboratorio.pk,
            "fecha_inicio": f"{fecha.isoformat()}T09:00",
            "fecha_fin": f"{fecha.isoformat()}T11:00",
            "horas_seleccionadas": json.dumps([9, 10]),
            "proposito": "Investigación",
            "proposito_codigo": "investigacion_innovacion",
            "descripcion_proyecto": "Validación.",
            "participantes_seleccionados": "[]",
            "aceptar_terminos": "on",
            "tipo_solicitud": "servicio",
            "modalidad_servicio": "diseno_completo",
            "provision_consumibles": "ninguno",
            "unidades_seleccionadas": "[]",
            "servicios_solicitados": [str(self.servicio.pk)],
            "cotizacion_aceptada": "true",
            "metodo_pago": "transferencia",
        }
        corta = self.client.post(reverse("crear_reserva"), {**base, "intencion_solicitud": "Una carcasa."})
        self.assertEqual(corta.status_code, 400)
        self.assertIn("al menos 50 palabras", corta.json()["error"])
        larga = self.client.post(reverse("crear_reserva"), {**base, "intencion_solicitud": "palabra " * 201})
        self.assertEqual(larga.status_code, 400)
        self.assertIn("hasta 200 palabras", larga.json()["error"])

    def test_creacion_rechaza_entrega_anterior_y_equipo_ajeno(self):
        fecha = _dia_habil_desde(timezone.localdate() + timedelta(days=7))
        base = {
            "unidad_id": self.laboratorio.pk,
            "fecha_inicio": f"{fecha.isoformat()}T09:00",
            "fecha_fin": f"{fecha.isoformat()}T11:00",
            "horas_seleccionadas": json.dumps([9, 10]),
            "proposito": "Investigación",
            "proposito_codigo": "investigacion_innovacion",
            "descripcion_proyecto": "Validación.",
            "participantes_seleccionados": "[]",
            "aceptar_terminos": "on",
            "tipo_solicitud": "servicio",
            "modalidad_servicio": "diseno_completo",
            "provision_consumibles": "ninguno",
            "unidades_seleccionadas": "[]",
            "servicios_solicitados": [str(self.servicio.pk)],
            "cotizacion_aceptada": "true",
            "metodo_pago": "transferencia",
        }
        anterior = self.client.post(reverse("crear_reserva"), {
            **base,
            "fecha_entrega_prevista": (fecha - timedelta(days=1)).isoformat(),
        })
        self.assertEqual(anterior.status_code, 400)
        self.assertIn("anterior", anterior.json()["error"])

        ajeno = self.client.post(reverse("crear_reserva"), {**base, "equipo_servicio": "999999"})
        self.assertEqual(ajeno.status_code, 400)
        self.assertIn("no pertenece", ajeno.json()["error"])
