"""Las diez maquetas se descargan con sus datos y los mismos permisos."""

from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from apps.laboratorios.operacion.presentation.maquetas_pdf import MaquetaHTML, _texto, render_maqueta_pdf
from apps.reservas.models.visitas import AsistenteVisita, SolicitudVisita
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, MedicionCalidad, PlanCalidad
from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
from apps.plantas_piloto.operacion.models.planificacion import LineaPlanMaestro, PlanMaestro
from apps.recursos.models.consumibles import LoteConsumible
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion
from apps.reservas.models.reservas import Reserva
from tests.integration.test_produccion_planta import BasePlantaProduce


def preparar_documentos(unidad, usuario, receta):
    """Registros pequeños, con contenido en cada formato y sin operar inventario."""
    hoy = timezone.localdate()
    reserva = Reserva.objects.create(
        laboratorio=unidad,
        usuario=usuario,
        receta=receta,
        tipo_solicitud="servicio",
        factor_proceso=Decimal("1"),
        materia_prima_cliente=True,
        fecha=hoy,
        hora_inicio=time(9),
        hora_fin=time(11),
        equipo_codigo="QA-MAQUETAS",
        equipo_nombre="Proceso de prueba",
        nombre_solicitante="Responsable de la prueba",
        institucion="Institución de prueba",
    )
    visita = SolicitudVisita.objects.create(
        unidad=unidad,
        reserva=reserva,
        responsable=usuario,
        institucion="Grupo de prueba",
        personas=2,
        observaciones="Observación guardada de la visita.",
    )
    AsistenteVisita.objects.create(
        visita=visita,
        nombre="Persona presente",
        asistio=True,
        ingreso_en=timezone.now(),
    )
    AsistenteVisita.objects.create(visita=visita, nombre="Persona ausente")
    plan = PlanMaestro.objects.create(
        unidad=unidad, nombre="Plan de prueba", desde=hoy, hasta=hoy + timedelta(days=5)
    )
    LineaPlanMaestro.objects.create(
        plan=plan, receta=receta, fecha=hoy, factor=Decimal("1.5")
    )
    orden = OrdenProduccion.objects.create(
        unidad=unidad,
        receta=receta,
        reserva=reserva,
        origen="maquila",
        fecha_inicio=hoy,
        fecha_fin=hoy,
        estado="terminada",
        cantidad_obtenida=Decimal("12"),
    )
    base = receta.insumos.filter(forma_parte="base").first()
    if base:
        LoteConsumible.objects.create(
            consumible=base.consumible,
            reserva=reserva,
            material_cliente=True,
            codigo=f"QA-MATERIA-{reserva.pk}",
            cantidad_inicial=Decimal("100"),
            cantidad_actual=Decimal("0"),
            observaciones="Materia prima recibida para la prueba.",
            bodega="Recepción de prueba",
        )
    lote = LoteProducto.objects.create(
        unidad=unidad,
        producto=receta.producto,
        orden=orden,
        codigo=f"QA-PDF-{unidad.pk}-{reserva.pk}",
        cantidad_inicial=Decimal("12"),
        cantidad_disponible=Decimal("12"),
        estado="disponible",
        control_calidad="aprobado",
    )
    MovimientoProducto.objects.create(
        unidad=unidad,
        lote=lote,
        tipo="venta",
        cantidad=Decimal("5"),
        precio_unitario=Decimal("0"),
        destino="Cliente de prueba",
        referencia="Acta de prueba",
        registrado_por=usuario,
    )
    ejercicio = EjercicioAula.objects.create(
        unidad=unidad,
        receta=receta,
        nombre="Balance de prueba",
        consigna="Calcula el balance con la escala asignada.",
    )
    IntentoEjercicio.objects.create(
        ejercicio=ejercicio, estudiante=usuario, factor=Decimal("1.5")
    )
    plan_calidad = (
        PlanCalidad.objects.filter(unidad=unidad, producto=receta.producto).first()
        or PlanCalidad.objects.filter(unidad=unidad).first()
    )
    control = None
    if plan_calidad:
        control = ControlCalidad.objects.create(
            unidad=unidad,
            plan=plan_calidad,
            lote_producto=lote,
            registrado_por=usuario,
            resultado="conforme",
        )
        parametro = plan_calidad.parametros.first()
        if parametro:
            MedicionCalidad.objects.create(
                control=control,
                parametro=parametro,
                valor_texto="Medición guardada",
                conforme=True,
            )
    urls = {
        "acta_entrega": reverse("acta_entrega_maquila", args=[unidad.slug, reserva.pk]),
        "maquila": reverse("maquila_expediente", args=[unidad.slug, reserva.pk]),
        "plan_maestro": reverse("plan_maestro", args=[unidad.slug, plan.pk]),
        "control_calidad": reverse("control_calidad", args=[unidad.slug])
        + (
            f"?plan={plan_calidad.pk}&hecho={control.pk}&lote_producto={lote.pk}"
            if control
            else ""
        ),
        "plan_haccp": reverse("plan_haccp", args=[unidad.slug]),
        "resultados_ejercicio": reverse(
            "resultados_ejercicio", args=[unidad.slug, ejercicio.pk]
        ),
        "reporte_institucional": reverse("reporte_institucional")
        + "?desde=2026-01-01&hasta=2026-12-31",
        "trazabilidad_lote": reverse("trazabilidad_lote", args=[unidad.slug, lote.pk]),
        "asistencia": reverse("asistencia_visita", args=[unidad.slug, visita.pk]),
        "oferta": reverse("oferta_visitas", args=[unidad.slug]),
    }
    return urls


class DocumentosOficialesTests(BasePlantaProduce):
    def test_ficha_interna_del_proceso_se_puede_ver_sin_salir_del_panel(self):
        self.client.force_login(self.coordinacion)
        url = reverse('ficha_proceso', args=[self.unidad.slug, self.receta_queso.pk])
        pagina = self.client.get(url)
        self.assertContains(pagina, 'data-ver-pdf')
        documento = self.client.get(url, {'formato': 'pdf'})
        self.assertEqual(documento.status_code, 200)
        self.assertTrue(documento.content.startswith(b'%PDF'))
        self.assertTrue(documento['Content-Disposition'].startswith('inline;'))
        self.client.logout()
        self.assertEqual(self.client.get(url, {'formato': 'pdf'}).status_code, 302)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.urls = preparar_documentos(cls.unidad, cls.docente, cls.receta_queso)

    def pdf(self, url, descargar=False):
        return (
            url
            + ("&" if "?" in url else "?")
            + "formato=pdf"
            + ("&descargar=1" if descargar else "")
        )

    def test_las_diez_paginas_ofrecen_ambas_acciones_y_generan_pdf(self):
        self.client.force_login(self.coordinacion)
        for nombre, url in self.urls.items():
            with self.subTest(documento=nombre):
                pagina = self.client.get(url)
                self.assertContains(pagina, "Ver documento")
                self.assertContains(pagina, "Descargar documento")
                self.assertNotContains(pagina, "window.print()")
                respuesta = self.client.get(self.pdf(url))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta["Content-Type"], "application/pdf")
                self.assertTrue(respuesta["Content-Disposition"].startswith("inline;"))
                self.assertTrue(respuesta.content.startswith(b"%PDF"))
                self.assertIn(b"/Font", respuesta.content)
                self.assertIn(b"/SMask", respuesta.content)
                self.assertIn("no-store", respuesta["Cache-Control"])

    def test_vista_previa_y_descarga_contienen_el_mismo_pdf_con_filtros(self):
        self.client.force_login(self.coordinacion)
        instante = timezone.localtime()
        for nombre, url in self.urls.items():
            with (
                self.subTest(documento=nombre),
                patch("django.utils.timezone.localtime", return_value=instante),
            ):
                vista = self.client.get(self.pdf(url))
                descarga = self.client.get(self.pdf(url, True))
                self.assertEqual(vista.content, descarga.content)
                self.assertTrue(
                    descarga["Content-Disposition"].startswith("attachment;")
                )

    def test_el_pdf_no_amplia_los_permisos_del_panel(self):
        self.client.force_login(self.docente)
        privados = set(self.urls) - {"acta_entrega", "plan_haccp", "oferta"}
        with patch(
            "apps.documentos.presentation.documentos_gestion.render_maqueta_pdf"
        ) as construir:
            for nombre in privados:
                with self.subTest(documento=nombre):
                    respuesta = self.client.get(self.pdf(self.urls[nombre]))
                    self.assertEqual(respuesta.status_code, 403)
            construir.assert_not_called()
        self.assertEqual(
            self.client.get(self.pdf(self.urls["acta_entrega"])).status_code, 200
        )

    def test_sin_sesion_solo_se_publican_haccp_y_la_oferta(self):
        self.client.logout()
        for nombre, url in self.urls.items():
            with self.subTest(documento=nombre):
                respuesta = self.client.get(self.pdf(url))
                self.assertEqual(
                    respuesta.status_code,
                    200 if nombre in ("plan_haccp", "oferta") else 302,
                )
                if nombre in ("plan_haccp", "oferta"):
                    self.assertEqual(respuesta["X-Frame-Options"], "SAMEORIGIN")

    def test_conserva_control_guardado_y_observaciones_de_asistencia(self):
        self.client.force_login(self.coordinacion)
        with patch(
            "apps.documentos.presentation.documentos_gestion.render_maqueta_pdf",
            wraps=render_maqueta_pdf,
        ) as construir:
            self.client.get(self.pdf(self.urls["control_calidad"]))
            html = construir.call_args.args[0]
            self.assertIn("Medición guardada", html)
            self.assertIn("CONTROL REGISTRADO", html)
            self.client.get(self.pdf(self.urls["asistencia"]))
            html = construir.call_args.args[0]
            self.assertIn("Observación guardada de la visita.", html)
            self.assertNotIn('name="nuevos"', html)
            texto = _texto(MaquetaHTML(html).raiz)
            self.assertIn("[X]", texto)
            self.assertIn("[ ]", texto)


class ComposicionDeMaquetasTests(SimpleTestCase):
    def test_una_fila_normal_pasa_completa_a_la_pagina_siguiente(self):
        from apps.laboratorios.operacion.presentation.maquetas_pdf import MaquetaPDF

        html = (
            "<table><tr><th>Registro</th><th>Detalle</th></tr><tr><td>Nombre</td><td>"
            + "Detalle " * 60
            + "</td></tr></table>"
        )
        tabla = MaquetaPDF("asistencia").tabla(
            next(MaquetaHTML(html).raiz.buscar(tag="table"))
        )[0]
        tabla.wrap(780, 500)
        self.assertEqual(tabla.split(780, 40), [])

    def test_una_fila_mayor_que_la_pagina_se_divide_sin_rechazar_el_pdf(self):
        html = (
            "<main><table><tr><th>Registro</th><th>Detalle</th></tr><tr><td>Nombre</td><td>"
            + "Detalle " * 3000
            + '</td></tr></table><footer class="unit-report__footer">UPEC</footer></main><title>Prueba</title>'
        )
        pdf = render_maqueta_pdf(html, "asistencia")
        self.assertGreater(pdf.count(b"/Type /Page\n"), 1)

    def test_texto_hostil_no_se_interpreta_como_marcado_pdf(self):
        arbol = MaquetaHTML(
            '<p>&lt;img src="https://ajeno/"&gt; &amp; contenido<script>alert(1)</script></p>'
        )
        texto = _texto(arbol.raiz)
        self.assertIn("&lt;img", texto)
        self.assertNotIn("alert(1)", texto)

    def test_tabla_larga_se_pagina_sin_perder_la_ultima_fila(self):
        from apps.laboratorios.operacion.presentation.maquetas_pdf import MaquetaPDF

        filas = "".join(
            f"<tr><td>Registro {i}</td><td>{'Detalle ' * 60}</td></tr>"
            for i in range(80)
        )
        html = (
            "<main><table><thead><tr><th>Registro</th><th>Detalle</th></tr></thead><tbody>"
            + filas
            + '</tbody></table><footer class="unit-report__footer">UPEC</footer></main><title>Prueba</title>'
        )
        pdf = render_maqueta_pdf(html, "asistencia")
        self.assertGreater(pdf.count(b"/Type /Page\n"), 1)
        tabla = next(MaquetaHTML(html).raiz.buscar(tag="table"))
        compuesta = MaquetaPDF("asistencia").tabla(tabla)[0]
        self.assertIn("Registro 79", compuesta._cellvalues[-1][0][0].getPlainText())
        self.assertEqual(compuesta.repeatRows, 1)
