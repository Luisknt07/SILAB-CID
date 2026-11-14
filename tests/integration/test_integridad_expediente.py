"""Regresiones de permisos, versiones y transacciones del centro de reportes."""

from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, connections, transaction
from django.test import RequestFactory, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.documentos.presentation.cumplimiento import unidades_auditadas
from apps.documentos.presentation.conformidad_permanente import APROBAR, REVOCAR, aprobar_permanente
from apps.documentos.presentation.expediente import leer_expediente, observar_documento, validar_documento
from apps.documentos.presentation.expediente_redaccion import obtener_redaccion
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente, PoliticaDeCalidad
from apps.recursos.models.recursos import Recurso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import minimo_vigente
from tests.integration.test_direccion_recibe_y_califica import ANIO, BaseDelExpediente
from tests.integration.utiles import abrir_entrega
from tests.integration.utiles import (pdf_legible_prueba, datos_correspondencia_revisada, cargar_documento_revisado, recibir_documento_revisado, evaluar_documento_revisado, correspondencia_revisada)


class IntegridadExpedienteTests(BaseDelExpediente):
    # El menú del admin comprueba también el alcance de Centros I+D. Ambas
    # conexiones deben ser bases de pruebas cuando está activa su separación.
    databases = {'default', 'centros'} if settings.CENTROS_DB_ENABLED else {'default'}

    def test_carga_no_afirma_revision_antivirus_inexistente(self):
        documento = self.entrega()
        self.assertFalse(documento.recurso.seguridad_verificada)

    def entrega(self):
        documento = self.documento(self.laboratorio, 'RESOLUCION-CREACION', '')
        abrir_entrega(documento)
        cargar_documento_revisado(documento, SimpleUploadedFile('resolucion.pdf', pdf_legible_prueba('%PDF-1.4\nprueba')), self.coordinador)
        return documento

    def test_receptor_no_modifica_ni_siquiera_su_documento(self):
        documento = self.entrega()
        with self.assertRaises(ValidationError):
            observar_documento(documento, self.decano, 'Intento de devolución')
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'cargado')

    def test_receptor_no_ejecuta_post_del_tablero(self):
        documento = self.entrega()
        self.client.force_login(self.decano)
        respuesta = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
            'accion': 'observar', 'documento': documento.pk, 'observacion': 'Ajena'})
        self.assertEqual(respuesta.status_code, 403)

    def test_admin_acota_filas_y_no_ofrece_acciones_al_receptor(self):
        propio = self.entrega()
        ajeno = self.documento(self.suelto, 'RESOLUCION-CREACION', '')
        request = RequestFactory().get('/')
        request.user = self.decano
        panel = admin.site._registry[DocumentoExpediente]
        self.assertIn(propio, panel.get_queryset(request))
        self.assertNotIn(ajeno, panel.get_queryset(request))
        self.assertEqual(panel.get_actions(request), {})
        self.assertFalse(panel.has_change_permission(request, propio))
        self.assertFalse(panel.has_delete_permission(request, propio))

    def test_post_masivo_fabricado_no_observa(self):
        documento = self.entrega()
        self.client.force_login(self.decano)
        self.client.post(reverse('admin:documentos_documentoexpediente_changelist'), {
            'action': 'observar_documentos', '_selected_action': [documento.pk], 'index': '0'})
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'cargado')

    def test_dependencia_inactiva_o_receptor_revocado_no_tiene_alcance(self):
        self.decanato.activa = False
        self.decanato.save(update_fields=['activa'])
        self.assertFalse(unidades_auditadas(self.decano).exists())
        self.decanato.activa = True
        self.decanato.save(update_fields=['activa'])
        self.decanato.receptores.remove(self.decano)
        self.assertFalse(unidades_auditadas(self.decano).exists())

    @override_settings(DEBUG=False)
    def test_media_directa_exige_el_mismo_permiso_que_recurso(self):
        documento = self.entrega()
        url = documento.recurso.archivo.url
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.decano)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        b''.join(respuesta.streaming_content)
        self.decanato.receptores.remove(self.decano)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_media_no_expone_archivos_huerfanos_de_adjuntos(self):
        archivo = Path(settings.MEDIA_ROOT, 'recursos', 'adjuntos', 'huerfano.pdf')
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(b'privado')
        self.assertEqual(self.client.get('/media/recursos/adjuntos/huerfano.pdf').status_code, 404)

    def test_media_publica_sigue_disponible(self):
        from apps.recursos.models.recursos import Archivo
        archivo = Path(settings.MEDIA_ROOT, 'recursos/archivos/tour-publico.html')
        archivo.parent.mkdir(parents=True, exist_ok=True)
        Archivo.objects.create(tipo='html', archivo='recursos/archivos/tour-publico.html')
        archivo.write_text('<p>Tour</p>', encoding='utf-8')
        respuesta = self.client.get('/media/recursos/archivos/tour-publico.html')
        self.assertEqual(respuesta.status_code, 200)
        b''.join(respuesta.streaming_content)

    def test_lectura_de_anio_nuevo_no_escribe(self):
        with CaptureQueriesContext(connection) as consultas:
            documentos = leer_expediente(self.laboratorio, ANIO + 1)
        self.assertTrue(documentos)
        self.assertTrue(all(d.pk is None for d in documentos))
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
                             for q in consultas))

    def test_get_nuevo_y_preparacion_post(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        respuesta = self.client.get(url, {'anio': ANIO + 1})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Habilitar expediente del año')
        self.assertFalse(DocumentoExpediente.objects.filter(unidad=self.laboratorio, anio=ANIO + 1).exists())
        respuesta = self.client.post(url, {'anio': ANIO + 1, 'accion': 'preparar'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(DocumentoExpediente.objects.filter(unidad=self.laboratorio, anio=ANIO + 1).exists())
        cantidad = DocumentoExpediente.objects.filter(unidad=self.laboratorio, anio=ANIO + 1).count()
        self.client.post(url, {'anio': ANIO + 1, 'accion': 'preparar'})
        self.assertEqual(DocumentoExpediente.objects.filter(unidad=self.laboratorio, anio=ANIO + 1).count(), cantidad)
        self.assertNotContains(self.client.get(url, {'anio': ANIO + 1}), 'Habilitar expediente del año')

    def test_unicidad_tambien_con_mes_nulo(self):
        documento = self.entrega()
        with self.assertRaises(IntegrityError), transaction.atomic():
            DocumentoExpediente.objects.create(unidad=documento.unidad, exigido=documento.exigido,
                                               anio=documento.anio, corte=documento.corte, mes=None)

    def test_devolver_invalida_nota_y_conserva_evidencia(self):
        documento = self.entrega()
        aprobar_permanente(documento, self.direccion, documento.version,
                           documento.recurso.hash_sha256, confirmado=True,
                           declaracion_correspondencia=correspondencia_revisada(documento))
        self.assertEqual(documento.nota, 100)
        self.assertIsNone(documento.evaluacion)
        aprobacion = RegistroAuditoriaUnidad.objects.get(
            objeto_id=str(documento.pk), descripcion=APROBAR)
        observar_documento(documento, self.direccion, 'Corregir soporte', hasta=timezone.now() + timedelta(days=3))
        self.assertIsNone(documento.nota)
        self.assertIsNone(documento.evaluacion)
        registro = RegistroAuditoriaUnidad.objects.filter(
            objeto_id=str(documento.pk), descripcion__startswith='observar_documento:').latest('pk')
        self.assertIsNone(registro.datos_anteriores['evaluacion'])
        self.assertIsNone(registro.datos_anteriores['evaluacion_version'])
        self.assertEqual(registro.datos_anteriores['recurso_id'], documento.recurso_id)
        revocacion = RegistroAuditoriaUnidad.objects.get(
            objeto_id=str(documento.pk), descripcion=REVOCAR)
        self.assertEqual(aprobacion.datos_nuevos['estado'], 'aprobado')
        self.assertEqual(revocacion.datos_nuevos['estado'], 'revocado')
        self.assertEqual(aprobacion.datos_nuevos['recurso_id'], revocacion.datos_nuevos['recurso_id'])
        self.assertEqual(revocacion.usuario_id, self.direccion.pk)

    def test_objeto_obsoleto_no_sobrescribe_una_validacion(self):
        documento = self.entrega()
        obsoleto = DocumentoExpediente.objects.get(pk=documento.pk)
        recibir_documento_revisado(documento, self.direccion)
        with self.assertRaises(ValidationError):
            cargar_documento_revisado(obsoleto, SimpleUploadedFile('nuevo.pdf', pdf_legible_prueba('%PDF-1.4')), self.coordinador)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'validado')

    def test_antes_de_apertura_no_se_carga(self):
        documento = self.documento(self.laboratorio, 'RESOLUCION-CREACION', '')
        documento.abre_el = timezone.localdate() + timedelta(days=2)
        documento.save(update_fields=['abre_el'])
        with self.assertRaises(ValidationError):
            cargar_documento_revisado(documento, SimpleUploadedFile('archivo.pdf', pdf_legible_prueba('%PDF-1.4')), self.coordinador)

    def test_recepcion_no_penaliza_entrega_puntual(self):
        documento = self.entrega()
        documento.vence_el = timezone.localdate()
        documento.save(update_fields=['vence_el'])
        with patch('apps.documentos.presentation.expediente.timezone.now',
                   return_value=timezone.now() + timedelta(days=3)):
            recibir_documento_revisado(documento, self.direccion)
        self.assertFalse(documento.entregado_tarde)

    def test_cargar_otra_version_no_conserva_fecha_de_generacion_anterior(self):
        documento = self.entrega()
        documento.generado_en = timezone.now() - timedelta(days=1)
        documento.save(update_fields=['generado_en'])
        cargar_documento_revisado(documento, SimpleUploadedFile('reemplazo.pdf', pdf_legible_prueba('%PDF-1.4\nreemplazo')), self.coordinador)
        self.assertEqual(documento.version, 2)
        self.assertIsNone(documento.generado_en)
        self.assertEqual(documento.cargado_por, self.coordinador)

    def test_auditoria_del_comando_conserva_ip_de_la_peticion(self):
        documento = self.entrega()
        self.client.force_login(self.direccion)
        respuesta = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
            'accion': 'recibir', 'documento': documento.pk,
            **datos_correspondencia_revisada(documento)}, REMOTE_ADDR='192.0.2.10')
        self.assertEqual(respuesta.status_code, 302)
        registro = RegistroAuditoriaUnidad.objects.filter(
            objeto_id=str(documento.pk), descripcion__startswith='recibir_documento:').latest('pk')
        self.assertEqual(registro.direccion_ip, '192.0.2.10')
        self.assertEqual(registro.usuario, self.direccion)

    def test_firma_obligatoria_no_se_elude_con_observacion(self):
        documento = self.entrega()
        documento.exigido.requiere_firma = True
        documento.exigido.save(update_fields=['requiere_firma'])
        observar_documento(documento, self.direccion, 'Borrador sin firma', hasta=timezone.now() + timedelta(days=3))
        with self.assertRaises(ValidationError):
            recibir_documento_revisado(documento, self.direccion)
        with self.assertRaises(ValidationError):
            validar_documento(documento, self.coordinador)

    def test_nota_neta_insuficiente_exige_recomendacion(self):
        documento = self.entrega()
        recibir_documento_revisado(documento, self.direccion)
        documento.entregado_tarde = True
        documento.save(update_fields=['entregado_tarde'])
        with self.assertRaises(ValidationError):
            evaluar_documento_revisado(documento, self.direccion, 80)

    def test_politica_valida_porcentajes_y_no_conserva_cache_de_otro_proceso(self):
        with self.assertRaises(ValidationError):
            PoliticaDeCalidad(minimo_cumplimiento=150).full_clean()
        politica, _ = PoliticaDeCalidad.objects.update_or_create(pk=1, defaults={'minimo_cumplimiento': 70})
        self.assertEqual(minimo_vigente(), 70)
        PoliticaDeCalidad.objects.filter(pk=politica.pk).update(minimo_cumplimiento=85)
        self.assertEqual(minimo_vigente(), 85)

    def test_fallo_de_auditoria_revierte_archivo_y_estado(self):
        documento = self.entrega()
        anterior = documento.recurso_id
        archivos = set(Path(settings.MEDIA_ROOT).rglob('*'))
        with patch('apps.documentos.presentation.expediente_operaciones.registrar_auditoria',
                   side_effect=RuntimeError('Fallo de auditoría')):
            with self.assertRaises(RuntimeError):
                cargar_documento_revisado(documento, SimpleUploadedFile('otro.pdf', pdf_legible_prueba('%PDF-1.4\nnuevo')), self.coordinador)
        documento.refresh_from_db()
        self.assertEqual(documento.recurso_id, anterior)
        self.assertEqual(set(Path(settings.MEDIA_ROOT).rglob('*')), archivos)

    def test_editor_get_no_crea_redaccion_y_ajax_audita_y_exige_version(self):
        documento = self.documento(self.laboratorio, 'PLANIFICACION')
        self.assertIsNone(obtener_redaccion(documento).pk)
        self.assertFalse(DocumentoElaborado.objects.filter(documento=documento).exists())
        self.client.force_login(self.coordinador)
        url = reverse('redactar_documento_expediente', args=[self.laboratorio.slug, documento.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(DocumentoElaborado.objects.filter(documento=documento).exists())
        self.assertEqual(self.client.post(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 409)
        respuesta = self.client.post(url, {'version_base': '0'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['version'], 1)
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            entidad='documentos.DocumentoElaborado', usuario=self.coordinador).exists())
        self.assertEqual(self.client.post(url, {'version_base': '0'},
                                         HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 409)

    def test_fallo_con_zip_no_deja_contenido_extraido(self):
        documento = self.entrega()
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as comprimido:
            comprimido.writestr('index.html', '<p>Evidencia</p>')
        archivos = {p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
        with patch('apps.documentos.presentation.expediente_operaciones.registrar_auditoria',
                   side_effect=RuntimeError('Fallo')):
            with self.assertRaises(RuntimeError):
                cargar_documento_revisado(documento, SimpleUploadedFile('evidencias.zip', buffer.getvalue()), self.coordinador)
        self.assertEqual({p for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}, archivos)

    def test_media_conserva_el_zip_original_y_protege_sus_archivos_extraidos(self):
        documento = self.entrega()
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as comprimido:
            comprimido.writestr('index.html', '<p>Evidencia</p>')
        cargar_documento_revisado(documento, SimpleUploadedFile('evidencias.zip', buffer.getvalue()), self.coordinador)
        url = documento.recurso.archivo.url
        extraido = '/media/' + (documento.recurso.directorio_extraido / 'index.html').relative_to(
            settings.MEDIA_ROOT).as_posix()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(extraido).status_code, 404)
        self.client.force_login(self.direccion)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(b''.join(respuesta.streaming_content), buffer.getvalue())
        respuesta = self.client.get(extraido)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertEqual(b''.join(respuesta.streaming_content), b'<p>Evidencia</p>')

    def test_html_del_expediente_se_descarga_sin_ejecutarse_en_la_plataforma(self):
        documento = self.entrega()
        cargar_documento_revisado(documento, SimpleUploadedFile('evidencia.html', b'<script>alert(1)</script>'),
                         self.coordinador)
        self.client.force_login(self.direccion)
        respuesta = self.client.get(documento.recurso.archivo.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertIn('sandbox', respuesta['Content-Security-Policy'])
        b''.join(respuesta.streaming_content)

    def test_fallo_de_auditoria_del_editor_revierte_el_borrador(self):
        documento = self.documento(self.laboratorio, 'PLANIFICACION')
        self.client.force_login(self.coordinador)
        url = reverse('redactar_documento_expediente', args=[self.laboratorio.slug, documento.pk])
        with patch('apps.documentos.presentation.expediente_redaccion.registrar_auditoria',
                   side_effect=RuntimeError('Fallo')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, {'version_base': '0'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(DocumentoElaborado.objects.filter(documento=documento).exists())


class ConcurrenciaExpedienteTests(TransactionTestCase):
    def test_dos_editores_sobre_la_misma_version_no_se_pisan(self):
        from apps.documentos.presentation.expediente_redaccion import redactar_documento_view

        usuario = get_user_model().objects.create_user('editor-concurrente')
        unidad = Unidad.objects.create(nombre='Editor concurrente', slug='editor-concurrente',
                                        administrador=usuario, fecha_inicio=timezone.localdate())
        exigido = DocumentoExigido.objects.create(codigo='PLAN-CONCURRENTE', nombre='Planificación',
                                                  carpeta='planeacion', fuente_reporte='planificacion')
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=exigido, anio=ANIO)
        barrera = Barrier(2)

        def guardar(texto):
            try:
                request = RequestFactory().post('/', {'version_base': '0', 'mision': texto},
                                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                request.user = get_user_model().objects.get(pk=usuario.pk)
                barrera.wait(timeout=15)
                return redactar_documento_view(request, unidad.slug, documento.pk).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            respuestas = list(ejecutor.map(guardar, ['Primera propuesta', 'Segunda propuesta']))
        self.assertEqual(sorted(respuestas), [200, 409])
        self.assertEqual(DocumentoElaborado.objects.get(documento=documento).version, 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(
            unidad=unidad, entidad='documentos.DocumentoElaborado').count(), 1)

    def test_dos_cargas_concurrentes_conservan_ambas_versiones(self):
        usuario = get_user_model().objects.create_user('concurrente')
        unidad = Unidad.objects.create(nombre='Unidad concurrente', slug='unidad-concurrente',
                                        administrador=usuario, fecha_inicio=timezone.localdate())
        exigido = DocumentoExigido.objects.create(codigo='PRUEBA-CONCURRENCIA', nombre='Resolución',
                                                  carpeta='planeacion', origen='unidad')
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=exigido, anio=ANIO)
        barrera = Barrier(2)

        def cargar(numero):
            try:
                copia = DocumentoExpediente.objects.get(pk=documento.pk)
                actor = get_user_model().objects.get(pk=usuario.pk)
                barrera.wait(timeout=15)
                cargar_documento_revisado(copia, SimpleUploadedFile(f'{numero}.pdf',
                                 f'%PDF-1.4\nversion {numero}'.encode()), actor)
                return copia.version
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            versiones = list(ejecutor.map(cargar, [1, 2]))
        self.assertEqual(sorted(versiones), [1, 2])
        documento.refresh_from_db()
        self.assertEqual(documento.version, 2)
        self.assertEqual(Recurso.objects.filter(unidad=unidad).count(), 2)
        self.assertEqual(documento.recurso.reemplaza_a.version, 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=unidad,
                         descripcion__startswith='cargar_documento:').count(), 2)
