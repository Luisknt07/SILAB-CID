"""Lista compacta: datos oficiales, permisos y detalle completo de una entrega."""

from datetime import timedelta
from html.parser import HTMLParser
from unittest.mock import patch
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from apps.documentos.presentation.expediente_interfaz import observacion_breve, resumen_de_entrega, siguiente_paso
from apps.documentos.presentation.expediente import anexos_del, observar_documento
from tests.integration import test_direccion_recibe_y_califica as base


class ReportesHTML(HTMLParser):
    """Comprueba accesibilidad inicial sin depender de CSS o de JavaScript."""

    def __init__(self, html):
        super().__init__()
        self.desplegables = []
        self.reportes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == 'details':
            self.desplegables.append('open' in atributos)
        if 'data-reporte-anexo' in atributos:
            self.reportes.append((atributos.get('id'), all(self.desplegables)))

    def handle_endtag(self, tag):
        if tag == 'details':
            self.desplegables.pop()


class ExperienciaReportesTests(base.BaseDelExpediente):
    def test_abrir_tabla_no_escribe_y_muestra_pdf_observacion_y_ruta(self):
        self.client.force_login(self.coordinador)
        with CaptureQueriesContext(connection) as consultas:
            r = self.client.get(
                reverse("gestion_expediente_unidad", args=[self.laboratorio.slug])
            )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "data-entregas-panel")
        self.assertContains(r, "data-entregas-buscar")
        self.assertContains(r, 'data-estado-entrega="pendientes"')
        self.assertContains(r, 'class="entregas__tabla entregas__tabla--simple"')
        self.assertContains(r, 'data-progreso-general')
        self.assertNotContains(r, '<details class="entregas__fila"')
        self.assertNotContains(r, 'class="nivel__tabla"')
        self.assertNotContains(r, 'data-estado-entrega="pendientes" open')
        self.assertNotContains(r, "revisar=")
        self.assertFalse(
            any(
                q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                for q in consultas
            )
        )

    def test_firma_envio_recepcion_y_nota_son_estados_distintos(self):
        d = self.documento(self.laboratorio)
        d.recurso_id = 123
        self.assertEqual(resumen_de_entrega(d)["estado"], "Falta firma")
        d.firma_verificada = True
        self.assertEqual(resumen_de_entrega(d)["estado"], "Por validar")
        d.estado = "validado"
        self.assertEqual(resumen_de_entrega(d)["estado"], "Enviado")
        d.recibido_en = timezone.now()
        self.assertEqual(resumen_de_entrega(d)["estado"], "Recibido")
        d.evaluacion = 0
        d.evaluacion_version = d.version
        self.assertEqual(resumen_de_entrega(d)["estado"], "Evaluado")
        self.assertEqual(resumen_de_entrega(d)["nota"], 0)

    def test_calificacion_cero_sin_entrega_no_afirma_envio(self):
        d = self.documento(self.laboratorio)
        d.evaluacion = 0
        d.evaluacion_version = d.version
        r = resumen_de_entrega(d)
        self.assertEqual(r["estado"], "Pendiente")
        self.assertEqual(r["grupo"], "pendientes")
        self.assertEqual(r["nota"], 0)

    def test_plazo_resumen_usa_reapertura_y_conserva_plazo_original(self):
        d = self.documento(self.laboratorio)
        original = d.plazo_original
        d.prorroga_hasta = timezone.now() + timedelta(days=3)
        r = resumen_de_entrega(d)
        self.assertEqual(r["plazo"], d.prorroga_hasta)
        self.assertEqual(r["tipo_plazo"], "Reapertura")
        self.assertFalse(r["vencido"])
        self.assertEqual(d.plazo_original, original)

    def test_evaluacion_solo_en_administrador_incluso_para_superadmin(self):
        self.documento(self.laboratorio)
        ruta = reverse("gestion_expediente_unidad", args=[self.laboratorio.slug])
        self.client.force_login(self.direccion)
        self.assertNotContains(self.client.get(ruta), '>Evaluar</a>')
        self.assertContains(self.client.get(reverse('admin:reportes-cumplimiento-expediente')), 'data-evaluar-documento')
        self.client.force_login(self.decano)
        r = self.client.get(ruta)
        self.assertContains(r, "Sin envío")
        self.assertNotContains(r, "revisar=")
        self.assertNotContains(r, 'name="accion" value="cargar"')

    def test_redireccion_regresa_a_la_entrega_sin_eludir_permiso(self):
        d = self.documento(self.laboratorio)
        self.client.force_login(self.coordinador)
        ruta = reverse("gestion_expediente_unidad", args=[self.laboratorio.slug])
        with patch(
            "apps.documentos.presentation.expediente.observar_documento",
            wraps=observar_documento,
        ):
            r = self.client.post(
                ruta,
                {
                    "anio": base.ANIO,
                    "corte": self.corte,
                    "documento": d.pk,
                    "accion": "observar",
                    "observacion": "Revisar evidencia",
                },
            )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.endswith(f"#entrega-{d.pk}"))
        self.client.force_login(self.decano)
        self.assertEqual(
            self.client.post(
                ruta, {"documento": d.pk, "accion": "observar"}
            ).status_code,
            403,
        )

    def test_todos_los_anexos_archivados_son_visibles_y_conservan_sus_enlaces(self):
        documento, ruta = self.archivado(self.laboratorio)
        anexos = anexos_del(documento)
        originales = [(a.pk, a.recurso_id, a.version, a.estado) for a in anexos]
        self.assertGreater(len(anexos), 0)
        for vista, params in (
            (ruta, {}),
            (reverse('gestion_unidad', args=[self.laboratorio.slug]),
             {'view': 'reportes', 'fragment': '1', 'modal': '1'}),
        ):
            with self.subTest(vista=vista):
                r = self.client.get(vista, {'anio': base.ANIO, 'corte': self.corte, **params})
                self.assertEqual(r.status_code, 200)
                html = (r.json()['html'] if r['Content-Type'].startswith('application/json')
                        else r.content.decode('utf8'))
                reportes = ReportesHTML(html).reportes
                ids = [f'entrega-{a.pk}' for a in anexos]
                self.assertTrue(all(visible for _, visible in reportes))
                for a in anexos:
                    self.assertEqual([pk for pk, _ in reportes].count(f'entrega-{a.pk}'), 1)
                    # Antes del envío, el cierre muestra el borrador al día del anexo.
                    self.assertIn(f'&amp;anexo={a.pk}&amp;borrador=1', html)
                self.assertTrue(set(ids).issubset(pk for pk, _ in reportes))
                self.assertIn(f'&amp;gestionar={documento.pk}" data-entrega-abrir', html)
                self.assertIn('id="informes-gestion"', html)
        self.assertEqual(originales, [(a.pk, a.recurso_id, a.version, a.estado)
                                     for a in anexos_del(documento)])

    def test_receptor_consulta_anexos_sin_poder_modificarlos(self):
        documento, ruta = self.archivado(self.laboratorio)
        self.client.force_login(self.decano)
        r = self.client.get(ruta, {'anio': base.ANIO, 'corte': self.corte})
        self.assertTrue(all(visible for _, visible in ReportesHTML(r.content.decode()).reportes))
        for a in anexos_del(documento):
            self.assertContains(r, f'&amp;anexo={a.pk}&amp;borrador=1')
        self.assertNotContains(r, 'value="validar_anexo"')
        self.assertNotContains(r, 'value="anexos"')

    def test_actualizar_y_validar_anexos_regresa_a_su_lista_en_la_consola(self):
        documento, ruta = self.archivado(self.laboratorio)
        volver = reverse('gestion_unidad', args=[self.laboratorio.slug]) + '?view=reportes#reportes'
        datos = {'anio': base.ANIO, 'corte': self.corte, 'volver': volver}
        r = self.client.post(ruta, {**datos, 'documento': documento.pk, 'accion': 'anexos'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, volver.split('#')[0] + f'#anexos-{documento.pk}')
        anexo = anexos_del(documento)[0]
        r = self.client.post(ruta, {**datos, 'documento': anexo.pk, 'accion': 'validar_anexo'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, volver.split('#')[0] + f'#entrega-{anexo.pk}')
        anexo.refresh_from_db()
        self.assertEqual(anexo.estado, 'validado')

    def test_observacion_breve_conserva_el_comentario_y_el_texto_oficial(self):
        d = self.documento(self.laboratorio)
        texto = ('Requiere mejora: 0/100 en la rúbrica; descuento por tardanza: 0; nota final: 0/100.'
                 ' Nota de la Dirección: Falta identificar el responsable.'
                 ' Incumplimiento documental: entrega ausente, sin firma o pendiente de recepción.')
        d.evaluacion_observacion = texto
        self.assertEqual(observacion_breve(d), 'Falta identificar el responsable.')
        self.assertEqual(d.evaluacion_observacion, texto)
        d.evaluacion_observacion = texto.split(' Nota de la Dirección:')[0]
        self.assertEqual(observacion_breve(d), 'Requiere mejora.')
        d.observacion = 'Corregir la firma.'
        self.assertEqual(observacion_breve(d), d.observacion)

    def test_ruta_no_confunde_calificacion_con_envio_y_respeta_la_habilitacion(self):
        d = self.documento(self.laboratorio)
        self.abrir_plazo(d)
        d.recurso_id = 123
        d.evaluacion = 0
        d.evaluacion_version = d.version
        self.assertEqual(siguiente_paso(d), 'Cargar PDF firmado')
        d.firma_verificada = True
        self.assertEqual(siguiente_paso(d), 'Revisar anexos, validar y enviar')
        d.estado = 'validado'
        self.assertEqual(siguiente_paso(d), 'Aplicar acciones de mejora')
        d.evaluacion = None
        self.assertEqual(siguiente_paso(d), 'Dirección: recibir y confirmar el cierre')
        d.recibido_en = timezone.now()
        self.assertEqual(siguiente_paso(d), 'Dirección: confirmar el cierre')

    def test_detalle_sin_javascript_es_solo_lectura_y_no_expone_otra_unidad(self):
        d = self.documento(self.laboratorio)
        ajeno = self.documento(self.suelto)
        self.client.force_login(self.decano)
        ruta = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        r = self.client.get(ruta, {'anio': base.ANIO, 'corte': self.corte, 'gestionar': d.pk})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Volver a la tabla de entregas')
        self.assertContains(r, 'data-documento-vista="gestion"')
        self.assertNotContains(r, 'name="accion" value="cargar"')
        self.assertEqual(self.client.get(ruta, {'anio': base.ANIO, 'corte': self.corte,
                                               'gestionar': ajeno.pk}).status_code, 404)
