from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.gobernanza import es_revisor_institucional
from apps.core.models.gobernanza import AsignacionGobernanza
from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.integraciones import seguimiento as s
from apps.integraciones.models import ConsolidadoSeguimiento


def designar(usuario, rol="seguimiento", referencia="", **kwargs):
    return AsignacionGobernanza.objects.create(
        usuario=usuario,
        rol=rol,
        referencia=str(referencia),
        acto="Acto ficticio exclusivamente de prueba",
        dedicacion="Cobertura de prueba",
        desde=timezone.localdate() - timedelta(days=1),
        registrado_por=usuario,
        **kwargs,
    )


class SeguimientoGobernanzaTests(TestCase):
    databases = {"default", "centros"}

    @classmethod
    def setUpTestData(cls):
        from apps.centros_id.models import CentroID
        from apps.centros_id.identidades import identidad_de

        usuarios = get_user_model()
        cls.tecnico = usuarios.objects.create_superuser("gob-tecnico", password=None)
        cls.central = usuarios.objects.create_user("gob-central", password=None)
        cls.decano = usuarios.objects.create_user("gob-decano", password=None)
        cls.otro = usuarios.objects.create_user("gob-otro", password=None)
        cls.coordinador = usuarios.objects.create_user("gob-coordinador", password=None)
        cls.responsable = usuarios.objects.create_user(
            "gob-responsable-centro", password=None
        )
        cls.ciencia = usuarios.objects.create_user("gob-investigacion", password=None)
        cls.dep = DependenciaAcademica.objects.create(
            nombre="Facultad prueba", tipo="decanato"
        )
        cls.dep.receptores.add(cls.decano)
        cls.otra_dep = DependenciaAcademica.objects.create(
            nombre="Otra Facultad prueba"
        )
        cls.unidad = Unidad.objects.create(
            nombre="XR académico prueba",
            slug="xr-gob-prueba",
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
            adscrita_a=cls.dep,
            administrador=cls.coordinador,
            activo=True,
        )
        cls.exigido, _ = DocumentoExigido.objects.get_or_create(
            codigo="GOB-INFORME",
            defaults=dict(
                nombre="Informe de prueba",
                carpeta="planeacion",
                periodicidad="semestral",
                origen="unidad",
            ),
        )
        cls.doc = DocumentoExpediente.objects.create(
            unidad=cls.unidad,
            exigido=cls.exigido,
            anio=2026,
            corte="A",
            tramo_inicio=date(2026, 1, 1),
            tramo_fin=date(2026, 6, 30),
        )
        cls.centro = CentroID.objects.create(
            slug="centro-gob-prueba",
            nombre="Centro prueba",
            responsable=identidad_de(cls.responsable),
        )
        designar(cls.central)
        designar(cls.decano, "adscripcion", cls.dep.pk)
        designar(cls.responsable, "centro", cls.centro.slug)
        designar(cls.ciencia, "investigacion")

    def preparar(self):
        return s.preparar(
            self.decano,
            "dependencia",
            str(self.dep.pk),
            date(2026, 1, 1),
            date(2026, 6, 30),
        )

    def validado(self):
        c = self.preparar()
        return s.validar_adscripcion(self.decano, c.pk, c.sha256)

    def test_superusuario_no_equivale_a_designacion(self):
        self.assertFalse(es_revisor_institucional(self.tecnico))
        c = self.validado()
        with self.assertRaises(PermissionDenied):
            s.revisar(self.tecnico, c.pk, c.sha256, "revisado")

    def test_vigencia_revocacion_e_inactivacion_se_comprueban_sin_cache(self):
        self.assertTrue(es_revisor_institucional(self.central))
        AsignacionGobernanza.objects.filter(usuario=self.central).update(
            hasta=timezone.localdate() - timedelta(days=1),
            desde=timezone.localdate() - timedelta(days=5),
        )
        self.assertFalse(es_revisor_institucional(self.central))
        AsignacionGobernanza.objects.filter(usuario=self.central).update(
            hasta=None, activa=False
        )
        self.assertFalse(es_revisor_institucional(self.central))
        AsignacionGobernanza.objects.filter(usuario=self.central).update(activa=True)
        get_user_model().objects.filter(pk=self.central.pk).update(is_active=False)
        self.assertFalse(es_revisor_institucional(self.central))

    def test_funcion_no_concede_operacion_local_ni_practicas(self):
        from apps.gestion_unidades.presentation.permisos import (
            puede_operar_modulo_unidad,
            puede_leer_expediente,
        )

        self.assertTrue(puede_leer_expediente(self.central, self.unidad))
        for modulo in ("reservas", "finanzas", "practicas", "personal", "reportes"):
            self.assertFalse(
                puede_operar_modulo_unidad(self.central, self.unidad, modulo)
            )

    def test_adscripcion_no_cruza_facultades_ni_es_receptor_suficiente(self):
        c = self.preparar()
        self.dep.receptores.add(self.otro)
        with self.assertRaises(PermissionDenied):
            s.validar_adscripcion(self.otro, c.pk, c.sha256)
        with self.assertRaises(PermissionDenied):
            s.preparar(
                self.decano, "dependencia", str(self.otra_dep.pk), c.inicio, c.fin
            )

    def test_version_idempotente_validacion_unica_y_eventos(self):
        c = self.preparar()
        self.assertEqual(c.pk, self.preparar().pk)
        s.validar_adscripcion(self.decano, c.pk, c.sha256)
        with self.assertRaises(ValidationError):
            s.validar_adscripcion(self.decano, c.pk, c.sha256)
        s.revisar(self.central, c.pk, c.sha256, "revisado")
        self.assertEqual(
            ["preparar", "validar_adscripcion", "revisado"],
            list(c.eventos.values_list("accion", flat=True)),
        )

    def test_fuentes_modificadas_exigen_otra_version_sin_borrar_historial(self):
        c = self.validado()
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(version=2)
        with self.assertRaises(ValidationError):
            s.revisar(self.central, c.pk, c.sha256, "revisado")
        nueva = self.preparar()
        self.assertEqual(nueva.version, 2)
        self.assertFalse(s.vigente(c))
        self.assertEqual(ConsolidadoSeguimiento.objects.count(), 2)

    def test_digest_manipulado_no_valida(self):
        c = self.preparar()
        with self.assertRaises(ValidationError):
            s.validar_adscripcion(self.decano, c.pk, "0" * 64)
        c.refresh_from_db()
        self.assertIsNone(c.validado_por_id)

    def test_institucional_no_revisa_su_adscripcion_o_gestion(self):
        designar(self.decano)
        c = self.validado()
        with self.assertRaises(ValidationError):
            s.revisar(self.decano, c.pk, c.sha256, "revisado")
        Unidad.objects.filter(pk=self.unidad.pk).update(administrador=self.central)
        c = self.preparar()
        s.validar_adscripcion(self.decano, c.pk, c.sha256)
        with self.assertRaises(ValidationError):
            s.revisar(self.central, c.pk, c.sha256, "revisado")

    def test_observacion_requiere_motivo(self):
        c = self.validado()
        with self.assertRaises(ValidationError):
            s.revisar(self.central, c.pk, c.sha256, "observado")
        s.revisar(
            self.central, c.pk, c.sha256, "observado", "Completar cobertura y fuentes."
        )

    def test_centro_evidencias_versionadas_y_validacion_por_su_responsable(self):
        inicio, fin = date(2026, 1, 1), date(2026, 6, 30)
        with self.assertRaises(ValidationError):
            s.preparar(self.responsable, "centro", self.centro.slug, inicio, fin)
        for version in (1, 2):
            e = s.registrar_evidencia(
                self.responsable,
                self.centro.slug,
                "informe",
                inicio,
                fin,
                "Informe del Centro",
                "https://ejemplo.upec.edu.ec/informe",
            )
            self.assertEqual(e.version, version)
        c = s.preparar(self.responsable, "centro", self.centro.slug, inicio, fin)
        self.assertEqual(len(c.fuentes["evidencias"]), 1)
        self.assertEqual(c.fuentes["evidencias"][0]["version"], 2)
        s.validar_adscripcion(self.responsable, c.pk, c.sha256)
        s.revisar(self.central, c.pk, c.sha256, "revisado")

    def test_centro_no_autoriza_solo_por_privilegio_tecnico(self):
        self.assertFalse(s.puede_preparar(self.tecnico, "centro", self.centro.slug))
        self.assertFalse(s.autoridad(self.decano, "centro", self.centro.slug))

    def test_evidencia_no_admite_url_ejecutable_o_periodo_invertido(self):
        for url in ("javascript:alert(1)", "http://ejemplo.upec.edu.ec/documento"):
            with self.assertRaises(ValidationError):
                s.registrar_evidencia(
                    self.responsable,
                    self.centro.slug,
                    "informe",
                    date(2026, 1, 1),
                    date(2026, 6, 30),
                    "Informe",
                    url,
                )

    def test_mejora_responde_solo_responsable_y_cierra_otro_revisor(self):
        c = self.validado()
        p = s.abrir_compromiso(
            self.central,
            c.pk,
            "Documentar uso compartido XR.",
            self.decano.pk,
            timezone.localdate() + timedelta(days=15),
        )
        with self.assertRaises(PermissionDenied):
            s.responder_compromiso(
                self.otro, p.pk, "Hecho", "https://ejemplo.upec.edu.ec/evidencia"
            )
        s.responder_compromiso(
            self.decano,
            p.pk,
            "Se incorporó la evidencia.",
            "https://ejemplo.upec.edu.ec/evidencia",
        )
        with self.assertRaises(PermissionDenied):
            s.verificar_compromiso(self.tecnico, p.pk, "Comprobado")
        s.verificar_compromiso(
            self.central, p.pk, "Verificada la correspondencia y programación."
        )
        p.refresh_from_db()
        self.assertEqual(p.estado, "verificado")

    def test_ciencia_no_se_confunde_con_validacion_de_contenido(self):
        from apps.integraciones.models import ReferenciaOficialInvestigacion

        r = ReferenciaOficialInvestigacion.objects.create(
            centro=self.centro.slug,
            tipo="proyecto",
            objeto_id=1,
            sistema="Portafolio de prueba",
            identificador="PR-1",
            fuente="https://ejemplo.upec.edu.ec/PR-1",
            estado_oficial="Según fuente",
            registrado_por=self.responsable,
        )
        for usuario in (self.tecnico, self.responsable, self.central):
            with self.assertRaises(PermissionDenied):
                s.verificar_referencia(usuario, r.pk)
        s.verificar_referencia(self.ciencia, r.pk)
        r.refresh_from_db()
        self.assertEqual(r.verificado_por_id, self.ciencia.pk)

    def test_interfaz_funcional_sin_staff_y_rechazo_de_ambito_ajeno(self):
        c = self.preparar()
        self.client.force_login(self.decano)
        respuesta = self.client.get(reverse("seguimiento_mesa"))
        self.assertContains(respuesta, "Seguimiento de Laboratorios y Centros")
        self.assertEqual(
            self.client.get(reverse("seguimiento_detalle", args=[c.pk])).status_code,
            200,
        )
        self.client.force_login(self.otro)
        self.assertEqual(
            self.client.get(reverse("seguimiento_detalle", args=[c.pk])).status_code,
            403,
        )

    def test_csrf_y_metodos_para_decisiones(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.decano)
        c = self.preparar()
        self.assertEqual(
            cliente.post(
                reverse("seguimiento_detalle", args=[c.pk]),
                {"accion": "validar", "sha256": c.sha256},
            ).status_code,
            403,
        )
        self.client.force_login(self.ciencia)
        self.assertEqual(
            self.client.get(
                reverse("seguimiento_verificar_referencia", args=[1])
            ).status_code,
            405,
        )

    def test_exportacion_separa_fuentes_y_declara_cobertura(self):
        self.validado()
        self.client.force_login(self.central)
        response = self.client.get(
            reverse("seguimiento_exportar"),
            {"inicio": "2026-01-01", "fin": "2026-06-30"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["consolidados"]), 1)
        self.assertIn("centro:" + self.centro.slug, response.json()["sin_consolidado"])
        self.client.force_login(self.decano)
        self.assertEqual(
            self.client.get(reverse("seguimiento_exportar")).status_code, 403
        )

    def test_identidad_de_activo_no_se_duplica_ni_fusiona_por_nombre(self):
        from apps.centros_id.models import Componente, EquipoCentro

        area = Componente.objects.create(
            centro=self.centro,
            codigo="xr",
            nombre="XR",
            tipo="laboratorio",
            resumen="Pruebas",
            descripcion="Investigación especializada",
        )
        equipo = EquipoCentro.objects.create(
            componente=area,
            categoria="XR",
            nombre="Visor especializado",
            codigo="GOB-PAT-001",
            cantidad=1,
            es_activo_individual=True,
        )
        registro = s.registrar_activo(
            self.responsable,
            "gob-pat-001",
            "centro",
            equipo.pk,
            "https://ejemplo.upec.edu.ec/patrimonio/GOB-PAT-001",
        )
        self.assertEqual(registro.codigo_institucional, "GOB-PAT-001")
        with self.assertRaises(ValidationError):
            s.registrar_activo(
                self.responsable,
                "GOB-PAT-001",
                "centro",
                equipo.pk,
                "https://ejemplo.upec.edu.ec/patrimonio/GOB-PAT-001",
            )
        with self.assertRaises(PermissionDenied):
            s.registrar_activo(
                self.tecnico,
                "GOB-PAT-001",
                "centro",
                equipo.pk,
                "https://ejemplo.upec.edu.ec/patrimonio/GOB-PAT-001",
            )

    def test_referencia_oficial_valida_el_centro_del_registro(self):
        from apps.centros_id.models import Proyecto

        proyecto = Proyecto.objects.create(
            centro=self.centro, titulo="Investigación XR", codigo="GOB-PR-1"
        )
        r = s.registrar_referencia(
            self.responsable,
            self.centro.slug,
            "proyecto",
            proyecto.pk,
            "Portafolio de prueba",
            "GOB-PR-1",
            "https://ejemplo.upec.edu.ec/GOB-PR-1",
            "En ejecución",
        )
        self.assertIsNone(r.verificado_en)
        with self.assertRaises(ValidationError):
            s.registrar_referencia(
                self.ciencia,
                "otro-centro",
                "proyecto",
                proyecto.pk,
                "Portafolio de prueba",
                "GOB-PR-1",
                "https://ejemplo.upec.edu.ec/GOB-PR-1",
                "En ejecución",
            )

    def test_fuente_documental_se_descarga_solo_en_ambito_autorizado(self):
        from django.core.files.base import ContentFile
        from apps.recursos.models.recursos import Recurso
        from tests.integration.utiles import pdf_legible_prueba

        recurso = Recurso.objects.create(
            unidad=self.unidad,
            nombre="Informe conservado",
            tipo_adjunto="norma",
            archivo=ContentFile(
                pdf_legible_prueba("Informe del laboratorio"), name="gob-informe.pdf"
            ),
            version=1,
        )
        self.doc.recurso, self.doc.version = recurso, 1
        self.doc.save(update_fields=["recurso", "version"])
        c = self.preparar()
        ruta = reverse("seguimiento_archivo_documental", args=[c.pk, self.doc.pk])
        self.client.force_login(self.central)
        response = self.client.get(ruta)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content))
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_version_de_periodo_distinto_no_contamina_consolidado(self):
        otro = DocumentoExpediente.objects.create(
            unidad=self.unidad,
            exigido=self.exigido,
            anio=2025,
            corte="A",
            tramo_inicio=date(2025, 1, 1),
            tramo_fin=date(2025, 6, 30),
        )
        c = self.preparar()
        self.assertNotIn(otro.pk, [d["id"] for d in c.fuentes["documentos"]])

    def test_formulario_evidencia_selecciona_centro_y_registra_sin_ids_manuales(self):
        from apps.integraciones.models import EvidenciaSeguimiento

        self.client.force_login(self.responsable)
        url = reverse("seguimiento_registrar", args=["evidencia"])
        self.assertContains(self.client.get(url), self.centro.nombre)
        response = self.client.post(
            url,
            dict(
                centro=self.centro.slug,
                codigo="informe-gestion",
                inicio="2026-01-01",
                fin="2026-06-30",
                titulo="Informe de gestión del Centro",
                fuente="https://ejemplo.upec.edu.ec/informe-centro",
                huella_archivo="",
                documento_id="",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            EvidenciaSeguimiento.objects.get(codigo="informe-gestion").version, 1
        )

    def test_formulario_no_acepta_centro_fuera_del_selector_autorizado(self):
        from apps.centros_id.models import CentroID
        from apps.integraciones.models import EvidenciaSeguimiento

        otro = CentroID.objects.create(
            slug="otro-centro-formulario", nombre="Otro Centro"
        )
        self.client.force_login(self.responsable)
        response = self.client.post(
            reverse("seguimiento_registrar", args=["evidencia"]),
            dict(
                centro=otro.slug,
                codigo="informe",
                inicio="2026-01-01",
                fin="2026-06-30",
                titulo="Informe",
                fuente="https://ejemplo.upec.edu.ec/informe",
                huella_archivo="",
                documento_id="",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EvidenciaSeguimiento.objects.exists())

    def test_formulario_referencia_vincula_proyecto_existente_sin_aprobar_ciencia(self):
        from apps.centros_id.models import Proyecto
        from apps.integraciones.models import ReferenciaOficialInvestigacion

        p = Proyecto.objects.create(
            centro=self.centro, titulo="Proyecto XR para formulario", codigo="XR-FORM"
        )
        self.client.force_login(self.responsable)
        response = self.client.post(
            reverse("seguimiento_registrar", args=["referencia"]),
            dict(
                registro=f"{self.centro.slug}:proyecto:{p.pk}",
                sistema="Portafolio oficial de prueba",
                identificador="XR-FORM",
                fuente="https://ejemplo.upec.edu.ec/portafolio/XR-FORM",
                estado_oficial="En ejecución",
            ),
        )
        self.assertEqual(response.status_code, 302)
        r = ReferenciaOficialInvestigacion.objects.get(identificador="XR-FORM")
        self.assertEqual(r.objeto_id, p.pk)
        self.assertIsNone(r.verificado_por_id)

    def test_diagnostico_detecta_revocacion_y_se_mantiene_solo_lectura(self):
        from apps.integraciones.concordancia_reglamento import diagnosticar

        self.assertFalse(diagnosticar()["sin_designacion_institucional"])
        AsignacionGobernanza.objects.filter(usuario=self.central).update(activa=False)
        self.assertTrue(diagnosticar()["sin_designacion_institucional"])

    def test_documento_privado_centro_se_revisa_sin_publicarlo(self):
        from django.core.files.base import ContentFile
        from apps.centros_id.models import DocumentoCentro

        documento = DocumentoCentro.objects.create(
            centro=self.centro,
            titulo="Plan interno de prueba",
            tipo="plan_desarrollo",
            publico=False,
            archivo=ContentFile(
                b"contenido interno de prueba", name="plan-interno.txt"
            ),
        )
        inicio, fin = date(2026, 1, 1), date(2026, 6, 30)
        s.registrar_evidencia(
            self.responsable,
            self.centro.slug,
            "plan",
            inicio,
            fin,
            "Plan del Centro",
            "https://ejemplo.upec.edu.ec/plan",
        )
        c = s.preparar(self.responsable, "centro", self.centro.slug, inicio, fin)
        self.client.force_login(self.central)
        url = reverse("seguimiento_archivo_centro", args=[c.pk, documento.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content), b"contenido interno de prueba"
        )
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url).status_code, 403)
        documento.refresh_from_db()
        self.assertFalse(documento.publico)

    def test_archivo_centro_alterado_no_se_sirve_como_version_conservada(self):
        from django.core.files.base import ContentFile
        from apps.centros_id.models import DocumentoCentro

        documento = DocumentoCentro.objects.create(
            centro=self.centro,
            titulo="Plan controlado",
            tipo="plan_desarrollo",
            publico=False,
            archivo=ContentFile(b"original", name="plan-controlado.txt"),
        )
        inicio, fin = date(2026, 1, 1), date(2026, 6, 30)
        s.registrar_evidencia(
            self.responsable,
            self.centro.slug,
            "plan",
            inicio,
            fin,
            "Plan del Centro",
            "https://ejemplo.upec.edu.ec/plan",
        )
        c = s.preparar(self.responsable, "centro", self.centro.slug, inicio, fin)
        with documento.archivo.storage.open(documento.archivo.name, "wb") as archivo:
            archivo.write(b"alterado")
        self.assertFalse(s.vigente(c))
        self.client.force_login(self.central)
        response = self.client.get(
            reverse("seguimiento_archivo_centro", args=[c.pk, documento.pk])
        )
        self.assertEqual(response.status_code, 404)
