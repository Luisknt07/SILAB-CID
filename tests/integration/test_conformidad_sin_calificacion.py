"""Los planes son de cumplimiento obligatorio: conformidad sin porcentaje; las notas antiguas sólo se conservan."""
from datetime import date, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.conformidad_planes import confirmar_conformidad
from apps.documentos.presentation.expediente import evaluar_documento
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.formacion.presentation.evaluacion_rubrica import revisar_documento
from apps.recursos.models.recursos import Recurso
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import (
    correspondencia_revisada, pdf_legible_prueba, registrar_antecedente_evaluacion,
)


class ConformidadSinCalificacionTests(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory(prefix='citt-conformidad-binaria-')
        self.addCleanup(temporal.cleanup)
        ajustes = override_settings(MEDIA_ROOT=temporal.name, MEDICION_SOLO_DEMO=False)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        asegurar_catalogo()
        self.direccion = get_user_model().objects.create_superuser('direccion-conformidad-binaria', password=None)
        # Quien revisa tiene la función de seguimiento y no administra la unidad que evalúa.
        designar(self.direccion)
        responsable = get_user_model().objects.create_user('responsable-conformidad-binaria', password=None)
        self.unidad = Unidad.objects.create(nombre='Unidad de conformidad', slug='conformidad-binaria',
            dependencia='laboratorios', administrador=responsable, fecha_inicio=date(2024, 1, 1))

    def documento(self, codigo):
        exigido = DocumentoExigido.objects.get(codigo=codigo)
        recurso = Recurso.objects.create(unidad=self.unidad, nombre=exigido.nombre,
            archivo=ContentFile(pdf_legible_prueba('Archivo para comprobar el canal de conformidad.',
                                                 firmado=True), name=codigo + '.pdf'))
        return DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido,
            anio=2025, corte='B' if codigo == 'PLANIFICACION' else '', version=1,
            estado='validado', firma_verificada=True, recurso=recurso,
            abre_el=date(2025, 1, 1), vence_el=timezone.localdate() + timedelta(days=1))

    def test_servicio_rechaza_porcentajes_libres_incluso_cien_y_cero(self):
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            documento = self.documento(codigo)
            registrar_antecedente_evaluacion(documento, self.direccion, 75, 'Antecedente conservado.')
            fecha = documento.evaluado_en
            for porcentaje in (0, 50, 100):
                with self.subTest(codigo=codigo, porcentaje=porcentaje):
                    with self.assertRaisesMessage(ValidationError, 'es de cumplimiento obligatorio'):
                        evaluar_documento(documento, self.direccion, porcentaje,
                            observacion='Intento de nota nueva.', recomendaciones='Completar la entrega.')
                    documento.refresh_from_db()
                    self.assertEqual((documento.evaluacion, documento.evaluado_en,
                                      documento.evaluacion_observacion),
                                     (75, fecha, 'Antecedente conservado.'))

    def test_capacidad_interna_no_es_un_booleano_ni_un_valor_serializable(self):
        documento = self.documento('PLANIFICACION')
        for valor in (True, '1', '100', object()):
            with self.subTest(valor=type(valor).__name__):
                with self.assertRaisesMessage(ValidationError, 'es de cumplimiento obligatorio'):
                    evaluar_documento(documento, self.direccion, 100, _registro_conformidad=valor)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

    def test_ruta_admin_evaluar_no_acepta_notas_ni_flags_internos(self):
        self.client.force_login(self.direccion)
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            documento = self.documento(codigo)
            respuesta = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
                'accion': 'evaluar', 'documento': documento.pk, 'evaluacion': '100',
                'version': documento.version, 'huella': documento.recurso.hash_sha256,
                'confirmado': '1', '_registro_conformidad': '1',
            })
            self.assertEqual(respuesta.status_code, 302)
            documento.refresh_from_db()
            self.assertIsNone(documento.evaluacion)
            self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad,
                objeto_id=str(documento.pk), descripcion='conformidad_documental:confirmar').exists())

    def test_accion_admin_desconocida_no_recae_en_evaluar(self):
        documento = self.documento('PLAN-COMPRAS-ANUAL')
        self.client.force_login(self.direccion)
        with patch('apps.documentos.presentation.expediente.evaluar_documento') as evaluar:
            respuesta = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
                'accion': 'accion_inexistente', 'documento': documento.pk, 'evaluacion': '100',
            })
        self.assertEqual(respuesta.status_code, 302)
        evaluar.assert_not_called()
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

    def test_la_administracion_tampoco_califica_los_dos_planes(self):
        self.client.force_login(self.direccion)
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            documento = self.documento(codigo)
            self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
                'accion': 'evaluar_rubrica', 'documento': documento.pk, 'version': documento.version,
                'huella': documento.recurso.hash_sha256, 'confirmado': '1', 'query': 'anio=2026'})
            documento.refresh_from_db()
            self.assertIsNone(documento.evaluacion)

    def test_confirmacion_legitima_conserva_el_registro_documental_y_su_huella(self):
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            documento = self.documento(codigo)
            # Las reglas de contenido tienen sus propias pruebas. Este caso
            # verifica el canal transaccional real y la capacidad que concede.
            with patch('apps.documentos.presentation.conformidad_planes.analizar_conformidad',
                       return_value=([], {})):
                confirmar_conformidad(documento, self.direccion, documento.version,
                    documento.recurso.hash_sha256, confirmado=True,
                    declaracion_correspondencia=correspondencia_revisada(documento))
            documento.refresh_from_db()
            self.assertIsNone(documento.evaluacion)
            self.assertIsNone(documento.nota)
            rastro = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad,
                objeto_id=str(documento.pk), descripcion='conformidad_documental:confirmar')
            self.assertEqual(rastro.datos_nuevos['sha256'], documento.recurso.hash_sha256)
            self.assertEqual(rastro.datos_nuevos['version'], documento.version)
            self.assertFalse(rastro.datos_nuevos['autorizacion_financiera'])
            revision = revisar_documento(documento)
            self.assertTrue(revision['conforme'], repr((revision['conformidad'], documento.recurso.estado,
                documento.recurso.version, documento.version, documento.recurso.unidad_id, documento.unidad_id,
                getattr(documento, '_conformidad_plan_registro', None))))

    def test_confirmacion_invalida_no_registra_ninguna_nota(self):
        documento = self.documento('PLANIFICACION')
        with patch('apps.documentos.presentation.conformidad_planes.analizar_conformidad',
                   return_value=([dict(severidad='bloqueo', mensaje='Falta la programación.')], {})):
            with self.assertRaisesMessage(ValidationError, 'Falta la programación'):
                confirmar_conformidad(documento, self.direccion, documento.version,
                    documento.recurso.hash_sha256, confirmado=True)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

    def test_la_no_entrega_de_un_plan_no_se_registra_como_cero(self):
        # La no entrega de un plan la registra el vencimiento como incumplimiento, sin porcentaje.
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            documento = self.documento(codigo)
            documento.estado = 'pendiente'
            documento.save(update_fields=['estado'])
            with self.assertRaisesMessage(ValidationError, 'es de cumplimiento obligatorio'):
                evaluar_documento(documento, self.direccion, 0,
                    observacion='No se presentó la entrega.', recomendaciones='Completar y enviar el documento.',
                    registrar_incumplimiento=True)
            documento.refresh_from_db()
            self.assertIsNone(documento.evaluacion)
            self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad,
                objeto_id=str(documento.pk), descripcion='conformidad_documental:confirmar').exists())
