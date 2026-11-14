"""Unidad remitente, Dirección evaluadora y archivos históricos independientes."""

from pathlib import Path
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.expediente import anexos_del, validar_anexo
from apps.documentos.presentation.expediente_archivos import versiones_del_documento
from apps.formacion.presentation.evaluacion_rubrica import criterios_de
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente, ANIO
from tests.integration.test_cumplimiento_expediente import PDF_FIRMADO
from tests.integration.utiles import datos_correspondencia_revisada


class SeparacionReportesTests(BaseDelExpediente):
    def seleccionar(self, d, vista="gestion"):
        return self.client.get(
            reverse("gestion_expediente_unidad", args=[d.unidad.slug]),
            dict(anio=ANIO, corte=d.corte, gestionar=d.pk, vista=vista, fragment="1"),
        )

    def enviar(self, d, ruta, usuario):
        for anexo in anexos_del(d):
            validar_anexo(anexo, self.coordinador)
        self.client.force_login(usuario)
        r = self.client.post(
            ruta, dict(anio=ANIO, corte=d.corte, documento=d.pk, accion="validar")
        )
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.estado, "validado")
        self.assertIsNone(d.recibido_en)
        self.assertIsNone(d.evaluacion)

    def test_unidad_prepara_en_modal_sin_evaluacion_incluso_superadmin(self):
        d, ruta = self.archivado(self.laboratorio)
        for usuario in [self.coordinador, self.direccion]:
            self.client.force_login(usuario)
            for destino, datos in [
                (ruta, {}),
                (
                    reverse("gestion_unidad", args=[d.unidad.slug]),
                    dict(view="reportes", fragment="1", modal="1"),
                ),
            ]:
                r = self.client.get(destino, dict(anio=ANIO, corte=d.corte, **datos))
                html = (
                    r.json()["html"]
                    if r["Content-Type"].startswith("application/json")
                    else r.content.decode()
                )
                self.assertIn("data-entrega-dialogo", html)
                self.assertNotIn("data-rubrica", html)
                self.assertNotIn(">Evaluar</a>", html)
                self.assertNotIn('<th scope="col">Nota</th>', html)
            r = self.seleccionar(d)
            self.assertContains(r, 'name="enviar" value="1"')
            self.assertContains(r, 'name="archivo"')
            self.assertNotContains(r, "data-entrega-versiones")
            self.assertNotContains(r, "data-rubrica")
            self.assertNotContains(r, 'value="recibir"')
            self.assertNotContains(r, 'value="habilitar_tardia"')

    def test_acciones_de_direccion_no_se_admiten_en_endpoint_de_unidad(self):
        d, ruta = self.archivado(self.laboratorio)
        self.client.force_login(self.direccion)
        original = (d.estado, d.recurso_id, d.version)
        for accion in [
            "evaluar",
            "evaluar_rubrica",
            "recibir",
            "habilitar_tardia",
            "ultimatum",
            "asignar_plazo",
        ]:
            with self.subTest(accion=accion):
                r = self.client.post(
                    ruta, dict(documento=d.pk, accion=accion, anio=ANIO, corte=d.corte)
                )
                self.assertEqual(r.status_code, 403)
        d.refresh_from_db()
        self.assertEqual((d.estado, d.recurso_id, d.version), original)
        self.assertIsNone(d.recibido_en)
        self.assertIsNone(d.evaluacion)

    def test_envio_desde_unidad_es_inmutable_para_superadmin_y_no_recibe_solo(self):
        d, ruta = self.archivado(self.laboratorio)
        self.enviar(d, ruta, self.direccion)
        original = (d.recurso_id, d.version, d.estado, d.validado_en)
        pdf = Path(d.recurso.archivo.path).read_bytes()
        r = self.seleccionar(d)
        self.assertContains(r, "Documento enviado.")
        self.assertNotContains(r, "<form")
        for accion in ["observar", "retirar_archivo", "reactivar", "generar", "anexos"]:
            r = self.client.post(
                ruta,
                dict(
                    documento=d.pk,
                    accion=accion,
                    anio=ANIO,
                    corte=d.corte,
                    confirmar_retiro="1",
                    motivo="Equivocado",
                    observacion="Corregir",
                    version=d.version,
                    huella=d.recurso.hash_sha256,
                ),
            )
            self.assertEqual(r.status_code, 302)
            d.refresh_from_db()
            self.assertEqual(
                (d.recurso_id, d.version, d.estado, d.validado_en), original
            )
        self.assertEqual(Path(d.recurso.archivo.path).read_bytes(), pdf)

    def test_director_recibe_evalua_en_admin_y_unidad_solo_consulta_respuesta(self):
        d, ruta = self.archivado(self.laboratorio)
        self.enviar(d, ruta, self.coordinador)
        self.client.force_login(self.direccion)
        admin = reverse("admin:reportes-cumplimiento-expediente")
        query = f"anio={ANIO}&corte={d.corte}&revisar={d.pk}"
        self.assertContains(
            self.client.get(admin, dict(anio=ANIO, corte=d.corte, revisar=d.pk)),
            "data-cierre-indicadores",
        )
        self.client.post(admin, dict(documento=d.pk, accion="recibir", query=query,
                                     **datos_correspondencia_revisada(d)))
        d.refresh_from_db()
        self.assertIsNotNone(d.recibido_en)
        datos = {c["clave"]: "100" for c in criterios_de(d)}
        r = self.client.post(
            admin,
            dict(
                documento=d.pk,
                accion="confirmar_cierre",
                query=query,
                confirmado="1",
                version=d.version,
                huella=d.recurso.hash_sha256,
                **datos,
            ),
        )
        self.assertTrue(r.url.startswith(admin))
        d.refresh_from_db()
        self.assertEqual(d.nota, 0)
        self.client.force_login(self.coordinador)
        r = self.seleccionar(d, "observaciones")
        self.assertContains(r, "Cumplimiento calculado de metas: 0")
        self.assertNotContains(r, 'name="accion" value="evaluar_rubrica"')
        self.assertNotContains(r, "data-rubrica")

    def test_director_devuelve_y_unidad_corrige_conservando_el_enviado(self):
        d, ruta = self.archivado(self.laboratorio)
        self.enviar(d, ruta, self.coordinador)
        enviado = d.recurso_id
        version_enviada = d.version
        self.client.force_login(self.direccion)
        self.client.post(
            reverse("admin:reportes-cumplimiento-expediente"),
            dict(documento=d.pk, accion="observar", observacion="Corregir contenido",
                 hasta_correccion=(timezone.now() + timedelta(days=3)).isoformat()),
        )
        d.refresh_from_db()
        self.assertEqual(d.estado, "observado")
        self.client.force_login(self.coordinador)
        self.assertContains(self.seleccionar(d), 'name="archivo"')
        self.abrir_plazo(d)
        respuesta_carga = self.client.post(
            ruta,
            dict(
                documento=d.pk,
                accion="cargar",
                anio=ANIO,
                corte=d.corte,
                **datos_correspondencia_revisada(d),
                archivo=SimpleUploadedFile("corregido.pdf", PDF_FIRMADO + b" nuevo"),
            ),
        )
        self.assertEqual(respuesta_carga.status_code, 302)
        d.refresh_from_db()
        from django.contrib.messages import get_messages
        self.assertEqual(d.version, version_enviada + 1,
            '; '.join(str(m) for m in get_messages(respuesta_carga.wsgi_request)))
        self.assertEqual(d.recurso.reemplaza_a_id, enviado)
        anteriores = versiones_del_documento(d)
        self.assertTrue(
            next(v for v in anteriores if v["recurso"].pk == enviado)["enviado"]
        )
        # Este fixture carga archivos externos; no crea un PDF nativo previo.
        self.assertEqual(len(anteriores), 2)
        self.assertTrue(anteriores[0]['actual'])
        self.assertFalse(anteriores[0]['enviado'])
        self.assertFalse(any(v['borrador'] for v in anteriores))

    def test_versiones_aparte_y_retiro_del_enviado_solo_desde_admin(self):
        d, ruta = self.enviado(self.laboratorio)
        self.client.force_login(self.direccion)
        r = self.seleccionar(d, "versiones")
        self.assertContains(r, "data-entrega-versiones")
        self.assertNotContains(r, "<form")
        self.assertContains(r, "Borrador del sistema")
        self.assertContains(r, "Documento firmado enviado")
        admin = reverse("admin:reportes-cumplimiento-expediente")
        r = self.client.get(admin, dict(anio=ANIO, corte=d.corte, archivos=d.pk))
        self.assertContains(r, 'id="archivos-documento"')
        self.assertContains(r, 'value="retirar_archivo"')
        self.assertNotContains(r, "data-rubrica")
        anterior = d.recurso_id
        datos = dict(
            documento=d.pk,
            accion="retirar_archivo",
            motivo="Documento incorrecto",
            version=d.version,
            huella=d.recurso.hash_sha256,
            query=f"anio={ANIO}&corte={d.corte}&archivos={d.pk}",
        )
        self.client.post(admin, datos)
        d.refresh_from_db()
        self.assertEqual(d.recurso_id, anterior)
        self.client.post(admin, {**datos, "confirmar_retiro": "1"})
        d.refresh_from_db()
        self.assertIsNone(d.recurso_id)
        self.assertTrue(versiones_del_documento(d)[0]["retirado"])

    def test_admin_no_consulta_versiones_fuera_del_alcance_seleccionado(self):
        self.archivado(self.laboratorio)
        ajeno, _ = self.archivado(self.suelto)
        self.client.force_login(self.direccion)
        r = self.client.get(
            reverse("admin:reportes-cumplimiento-expediente"),
            dict(
                anio=ANIO,
                corte=ajeno.corte,
                unidad=self.laboratorio.slug,
                archivos=ajeno.pk,
            ),
        )
        self.assertEqual(r.status_code, 400)
