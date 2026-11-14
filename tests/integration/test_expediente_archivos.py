"""Versiones, retirada reversible y evaluación en el mismo centro de reportes."""

from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from tests.integration.utiles import (cargar_documento_revisado)
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.documentos.presentation.expediente_archivos import (
    retirar_archivo,
    versiones_del_documento,
)
from apps.documentos.models.expediente import DocumentoExpediente
from apps.formacion.presentation.evaluacion_rubrica import criterios_de
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente, ANIO
from tests.integration.test_cumplimiento_expediente import PDF_FIRMADO


class ArchivosDelExpedienteTests(BaseDelExpediente):
    def archivado(self, unidad, corte=None):
        documento, url = super().archivado(unidad, corte)
        # Este grupo necesita dos archivos reales para comprobar el historial;
        # el fixture común legado ya no genera un borrador nativo previo.
        cargar_documento_revisado(documento,
            SimpleUploadedFile('segunda-entrega.pdf', PDF_FIRMADO + unidad.slug.encode() + b' segunda entrega QA'),
            self.coordinador)
        return documento, url

    def datos(self, documento):
        return dict(version=documento.version, huella=documento.recurso.hash_sha256)

    def ruta_archivo(self, documento, recurso):
        base = reverse("gestion_expediente_unidad", args=[documento.unidad.slug])
        return f"{base}?anio={ANIO}&corte={documento.corte}&gestionar={documento.pk}&archivo={recurso.pk}"

    def test_historial_conserva_v1_y_receptor_puede_consultarla(self):
        d, _ = self.enviado(self.laboratorio)
        versiones = versiones_del_documento(d)
        self.assertEqual([v["recurso"].version for v in versiones], [2, 1])
        self.client.force_login(self.decano)
        r = self.client.get(self.ruta_archivo(d, versiones[-1]["recurso"]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        b"".join(r.streaming_content)
        d.refresh_from_db()
        self.assertEqual(d.estado, "validado")
        self.assertEqual(d.version, 2)

    def test_no_se_puede_consultar_un_archivo_de_otro_documento(self):
        d, _ = self.archivado(self.laboratorio)
        ajeno, _ = self.archivado(self.suelto)
        self.assertEqual(
            self.client.get(self.ruta_archivo(d, ajeno.recurso)).status_code, 404
        )
        self.client.force_login(self.decano)
        self.assertEqual(
            self.client.get(self.ruta_archivo(ajeno, ajeno.recurso)).status_code, 403
        )

    def test_retiro_de_enviado_es_solo_de_direccion_y_no_borra_archivo(self):
        d, _ = self.enviado(self.laboratorio)
        recurso = d.recurso
        archivo = Path(recurso.archivo.path)
        original = archivo.read_bytes()
        datos = self.datos(d)
        with self.assertRaises(ValidationError):
            retirar_archivo(d, self.coordinador, "Documento equivocado", **datos)
        retirar_archivo(d, self.direccion, "Documento de otra unidad", **datos)
        d.refresh_from_db()
        recurso.refresh_from_db()
        self.assertEqual((d.estado, d.recurso_id, d.version), ("pendiente", None, 2))
        self.assertFalse(d.firma_verificada)
        self.assertIsNone(d.recibido_en)
        self.assertIsNone(d.evaluacion)
        self.assertEqual(recurso.estado, "obsoleto")
        self.assertEqual(archivo.read_bytes(), original)
        self.assertTrue(versiones_del_documento(d)[0]["retirado"])
        self.client.force_login(self.decano)
        r = self.client.get(self.ruta_archivo(d, recurso))
        self.assertEqual(r.status_code, 200)
        b"".join(r.streaming_content)

    def test_retiro_exige_motivo_y_version_exacta(self):
        d, _ = self.archivado(self.laboratorio)
        id_original = d.recurso_id
        for motivo, version, huella in [
            ("", d.version, d.recurso.hash_sha256),
            ("Incorrecto", d.version - 1, d.recurso.hash_sha256),
            ("Incorrecto", d.version, "ajena"),
        ]:
            with (
                self.subTest(motivo=motivo, version=version),
                self.assertRaises(ValidationError),
            ):
                retirar_archivo(d, self.coordinador, motivo, version, huella)
        d.refresh_from_db()
        self.assertEqual(d.recurso_id, id_original)

    def test_retiro_no_altera_un_archivo_vigente_en_otro_anio(self):
        d, _ = self.archivado(self.laboratorio)
        heredado = DocumentoExpediente.objects.create(
            unidad=d.unidad,
            exigido=d.exigido,
            anio=d.anio + 1,
            corte=d.corte,
            recurso=d.recurso,
            version=d.version,
            estado=d.estado,
        )
        recurso = d.recurso
        retirar_archivo(d, self.coordinador, "Revisar esta entrega", **self.datos(d))
        heredado.refresh_from_db()
        recurso.refresh_from_db()
        self.assertEqual(heredado.recurso_id, recurso.pk)
        self.assertEqual(recurso.estado, "vigente")
        self.assertTrue(versiones_del_documento(d)[0]["retirado"])

    def test_retiro_y_nueva_carga_conservan_cadena_y_numeracion(self):
        d, _ = self.archivado(self.laboratorio)
        anterior = d.recurso_id
        retirar_archivo(d, self.coordinador, "Adjunto incorrecto", **self.datos(d))
        self.abrir_plazo(d)
        cargar_documento_revisado(
            d,
            SimpleUploadedFile("correcto.pdf", PDF_FIRMADO + b" archivo nuevo"),
            self.coordinador,
        )
        self.assertEqual(d.version, 3)
        self.assertEqual(d.recurso.reemplaza_a_id, anterior)
        self.assertEqual(
            [v["recurso"].version for v in versiones_del_documento(d)], [3, 2, 1]
        )

    def test_si_falla_auditoria_se_revierte_retiro_sin_tocar_archivos(self):
        d, _ = self.archivado(self.laboratorio)
        recurso = d.recurso
        with patch(
            "apps.documentos.presentation.expediente_operaciones.registrar_auditoria",
            side_effect=RuntimeError,
        ):
            with self.assertRaises(RuntimeError):
                retirar_archivo(d, self.coordinador, "Equivocado", **self.datos(d))
        d.refresh_from_db()
        recurso.refresh_from_db()
        self.assertEqual(d.recurso_id, recurso.pk)
        self.assertEqual(recurso.estado, "vigente")
        self.assertTrue(Path(recurso.archivo.path).is_file())

    def test_retiro_por_http_exige_confirmacion(self):
        d, ruta = self.archivado(self.laboratorio)
        datos = dict(
            anio=ANIO,
            corte=d.corte,
            documento=d.pk,
            accion="retirar_archivo",
            motivo="Otro documento",
            **self.datos(d),
        )
        self.client.post(ruta, datos)
        d.refresh_from_db()
        self.assertIsNotNone(d.recurso_id)
        self.client.post(ruta, {**datos, "confirmar_retiro": "1"})
        d.refresh_from_db()
        self.assertIsNone(d.recurso_id)

    def test_rubrica_solo_en_admin_y_guardado_permanece_en_admin(self):
        d, ruta = self.enviado(self.laboratorio)
        self.client.force_login(self.direccion)
        r = self.client.get(
            ruta,
            dict(
                anio=ANIO,
                corte=d.corte,
                gestionar=d.pk,
                paso="evaluacion",
                fragment="1",
            ),
        )
        self.assertNotContains(r, "data-rubrica")
        self.assertNotContains(r, "citt-cumplimiento")
        self.assertContains(
            self.client.get(
                reverse("admin:reportes-cumplimiento-expediente"),
                dict(anio=ANIO, corte=d.corte, revisar=d.pk),
            ),
            "data-cierre-indicadores",
        )
        datos = {c["clave"]: "100" for c in criterios_de(d)}
        volver = f"{ruta}?anio={ANIO}&corte={d.corte}"
        datos.update(
            documento=d.pk,
            accion="evaluar_rubrica",
            confirmado="1",
            volver=volver,
            **self.datos(d),
        )
        r = self.client.post(reverse("admin:reportes-cumplimiento-expediente"), datos)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            r.url.startswith(reverse("admin:reportes-cumplimiento-expediente") + "?")
        )
        d.refresh_from_db()
        self.assertIsNone(d.nota)  # Falta la recepción de Dirección para confirmar el cierre.
        self.client.force_login(self.decano)
        r = self.client.get(
            ruta, dict(anio=ANIO, corte=d.corte, gestionar=d.pk, fragment="1")
        )
        self.assertNotContains(r, "data-rubrica")
        self.assertNotContains(r, 'value="retirar_archivo"')

    def test_regreso_de_evaluacion_rechaza_host_externo_y_otra_unidad(self):
        d, ruta = self.enviado(self.laboratorio)
        self.client.force_login(self.direccion)
        admin = reverse("admin:reportes-cumplimiento-expediente")
        for volver in [
            "https://ejemplo.ec/",
            "//ejemplo.ec/",
            reverse("gestion_expediente_unidad", args=[self.suelto.slug]),
        ]:
            with self.subTest(volver=volver):
                r = self.client.post(
                    admin,
                    dict(
                        documento=d.pk,
                        accion="evaluar_rubrica",
                        volver=volver,
                        confirmado="1",
                        version=0,
                        huella="ajena",
                    ),
                )
                self.assertTrue(r.url.startswith(admin + "?"))
        d.refresh_from_db()
        self.assertIsNone(d.nota)
