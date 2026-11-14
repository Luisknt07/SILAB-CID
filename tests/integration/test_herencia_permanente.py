"""La resolución vigente se reutiliza sin decisiones duplicadas ni resurrecciones."""

from datetime import date, timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.conformidad_permanente import (
    APROBAR,
    aprobar_permanente,
    aprobacion_vigente,
    completar_aprobaciones,
    revocar_permanente,
)
from apps.documentos.presentation.expediente import (
    _heredar,
    carpeta_del_expediente,
    construir_expediente,
    leer_expediente,
    observar_documento,
    recibir_documento,
    validar_documento,
)
from apps.documentos.presentation.expediente_archivos import retirar_archivo
from apps.documentos.presentation.automatizacion_documental import procesar_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_expediente_calidad import BaseDelExpediente
from tests.integration.utiles import (
    abrir_entrega,
    cargar_documento_revisado,
    correspondencia_revisada,
    pdf_legible_prueba,
)


class HerenciaPermanenteTests(BaseDelExpediente):
    def resolucion(self, anio):
        return DocumentoExpediente.objects.get(
            unidad=self.unidad, exigido__codigo='RESOLUCION-CREACION', anio=anio)

    def resolucion_aprobada(self, anio=2025):
        documento = self.documento('RESOLUCION-CREACION', anio=anio)
        cargar_documento_revisado(abrir_entrega(documento), SimpleUploadedFile(
            'resolucion.pdf', pdf_legible_prueba('Resolución de creación, autoridad y alcance.')),
            self.coordinador)
        validar_documento(documento, self.coordinador)
        recibir_documento(documento, self.direccion,
                          declaracion_correspondencia=correspondencia_revisada(documento))
        aprobar_permanente(documento, self.direccion, documento.version,
                           documento.recurso.hash_sha256, confirmado=True,
                           declaracion_correspondencia=correspondencia_revisada(documento))
        return documento

    @staticmethod
    def proyectada(documentos):
        return next(d for d in documentos if d.exigido.codigo == 'RESOLUCION-CREACION')

    def test_reconcilia_ano_preparado_antes_de_la_aprobacion_sin_clonar_decision(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        self.assertIsNone(self.resolucion(2026).recurso_id)
        origen = self.resolucion_aprobada()

        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual = self.resolucion(2026)
        self.assertEqual(actual.recurso_id, origen.recurso_id)
        self.assertEqual(actual.validado_en, origen.validado_en)
        self.assertEqual(actual.validado_por_id, origen.validado_por_id)
        self.assertIsNone(actual.evaluacion)
        self.assertIsNone(actual.evaluado_por_id)
        aprobacion = aprobacion_vigente(actual)
        self.assertIsNotNone(aprobacion)
        self.assertEqual(aprobacion['documento_id'], origen.pk)
        self.assertEqual(aprobacion['actor_id'], self.direccion.pk)

    def test_aprobacion_posterior_reconcilia_copia_cargada_sin_repetir_la_decision(self):
        origen = self.documento('RESOLUCION-CREACION', anio=2026)
        cargar_documento_revisado(abrir_entrega(origen), SimpleUploadedFile(
            'resolucion-por-aprobar.pdf', pdf_legible_prueba('Resolución pendiente de aceptar.')),
            self.coordinador)
        construir_expediente(self.unidad, 2027, hoy=date(2027, 9, 22))
        copia = self.resolucion(2027)
        self.assertEqual(copia.estado, 'cargado')
        self.assertEqual(copia.recurso_id, origen.recurso_id)
        self.assertEqual(copia.observacion, 'Heredado del año 2026.')
        aprobar_permanente(origen, self.direccion, origen.version, origen.recurso.hash_sha256,
                           confirmado=True, declaracion_correspondencia=correspondencia_revisada(origen))
        aprobaciones = RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count()

        with CaptureQueriesContext(connection) as consultas:
            proyectada = self.proyectada(leer_expediente(self.unidad, 2027))
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
                             for q in consultas))
        self.assertEqual(proyectada.estado, 'validado')
        self.assertIsNotNone(aprobacion_vigente(proyectada))
        self.assertEqual(proyectada.validado_en, origen.validado_en)
        self.assertEqual(proyectada.recibido_en, origen.recibido_en)
        copia.refresh_from_db()
        self.assertEqual(copia.estado, 'cargado')

        construir_expediente(self.unidad, 2027, hoy=date(2027, 9, 22))
        copia.refresh_from_db()
        self.assertEqual(copia.estado, 'validado')
        self.assertIsNotNone(aprobacion_vigente(copia))
        self.assertIsNone(copia.evaluacion)
        self.assertIsNone(copia.evaluado_por_id)
        self.assertEqual(copia.validado_por_id, origen.validado_por_id)
        self.assertEqual(copia.validado_en, origen.validado_en)
        self.assertEqual(copia.recibido_en, origen.recibido_en)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), aprobaciones)

    def test_marcador_heredado_no_convierte_una_carga_propia_en_aprobada(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        propia = self.resolucion(2026)
        cargar_documento_revisado(abrir_entrega(propia), SimpleUploadedFile(
            'carga-propia.pdf', pdf_legible_prueba('Documento propio del expediente.')),
            self.coordinador)
        origen = self.resolucion_aprobada()
        # Un dato importado/copied no sustituye la trazabilidad de su carga real.
        DocumentoExpediente.objects.filter(pk=propia.pk).update(
            recurso_id=origen.recurso_id, version=origen.version,
            cargado_en=origen.cargado_en, cargado_por_id=origen.cargado_por_id,
            observacion='Heredado del año 2025.')
        proyectada = self.proyectada(leer_expediente(self.unidad, 2026))
        self.assertEqual(proyectada.estado, 'cargado')
        self.assertIsNone(aprobacion_vigente(proyectada))

    def test_nota_local_en_copia_cargada_conserva_revision_pendiente(self):
        origen = self.documento('RESOLUCION-CREACION', anio=2025)
        cargar_documento_revisado(abrir_entrega(origen), SimpleUploadedFile(
            'resolucion.pdf', pdf_legible_prueba('Resolución aún pendiente de aceptación.')),
            self.coordinador)
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        copia = self.resolucion(2026)
        copia.observacion = 'Confirmar el alcance particular de este período.'
        copia.save(update_fields=['observacion'])
        aprobar_permanente(origen, self.direccion, origen.version, origen.recurso.hash_sha256,
                           confirmado=True, declaracion_correspondencia=correspondencia_revisada(origen))
        proyectada = self.proyectada(leer_expediente(self.unidad, 2026))
        self.assertEqual(proyectada.estado, 'cargado')
        self.assertEqual(proyectada.observacion, copia.observacion)
        self.assertIsNone(aprobacion_vigente(proyectada))

    def test_control_bloqueado_del_origen_no_reconcilia_su_copia_cargada(self):
        origen = self.documento('RESOLUCION-CREACION', anio=2025)
        cargar_documento_revisado(abrir_entrega(origen), SimpleUploadedFile(
            'resolucion.pdf', pdf_legible_prueba('Resolución antes de su aceptación.')),
            self.coordinador)
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        aprobar_permanente(origen, self.direccion, origen.version, origen.recurso.hash_sha256,
                           confirmado=True, declaracion_correspondencia=correspondencia_revisada(origen))
        archivo = Path(origen.recurso.archivo.path)
        archivo.write_bytes(archivo.read_bytes() + b'alteracion posterior a la aprobacion')
        control = procesar_documento(origen, usuario=self.coordinador)
        self.assertEqual(control.estado, 'bloqueado')

        proyectada = self.proyectada(leer_expediente(self.unidad, 2026))
        self.assertEqual(proyectada.estado, 'cargado')
        self.assertIsNone(aprobacion_vigente(proyectada))

    def test_origen_bloqueado_se_conserva_sin_vigencia_al_heredar_marcador_vacio(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        anterior = self.documento('RESOLUCION-CREACION', anio=2024)
        cargar_documento_revisado(abrir_entrega(anterior), SimpleUploadedFile(
            'resolucion-antigua.pdf', pdf_legible_prueba('Antecedente anterior del expediente.')),
            self.coordinador)
        origen = self.resolucion_aprobada()
        self.assertNotEqual(origen.recurso_id, anterior.recurso_id)
        archivo = Path(origen.recurso.archivo.path)
        archivo.write_bytes(archivo.read_bytes() + b'alteracion detectada en origen')
        self.assertEqual(procesar_documento(origen, usuario=self.coordinador).estado, 'bloqueado')

        for anio in (2026, 2027):
            with self.subTest(anio=anio):
                cantidad = DocumentoExpediente.objects.count()
                with CaptureQueriesContext(connection) as consultas:
                    copia = self.proyectada(leer_expediente(self.unidad, anio))
                self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
                                     for q in consultas))
                self.assertEqual(DocumentoExpediente.objects.count(), cantidad)
                self.assertEqual(copia.recurso_id, origen.recurso_id)
                self.assertNotEqual(copia.recurso_id, anterior.recurso_id)
                self.assertIsNone(aprobacion_vigente(copia))
                self.assertIsNone(copia.nota)

                construir_expediente(self.unidad, anio, hoy=date(anio, 9, 22))
                guardada = self.resolucion(anio)
                self.assertEqual(guardada.recurso_id, origen.recurso_id)
                self.assertIsNone(aprobacion_vigente(guardada))
                self.assertIsNone(guardada.nota)

    def test_lectura_reconcilia_fila_vacia_sin_guardar_nada(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        origen = self.resolucion_aprobada()
        anterior = self.resolucion(2026)
        filas = DocumentoExpediente.objects.count()

        actual = self.proyectada(leer_expediente(self.unidad, 2026))
        self.assertEqual(actual.recurso_id, origen.recurso_id)
        self.assertIsNotNone(aprobacion_vigente(actual))
        anterior.refresh_from_db()
        self.assertIsNone(anterior.recurso_id)
        self.assertEqual(anterior.version, 0)
        self.assertEqual(anterior.estado, 'pendiente')
        self.assertEqual(DocumentoExpediente.objects.count(), filas)

    def test_lectura_virtual_no_crea_documentos_ni_repite_aprobacion(self):
        origen = self.resolucion_aprobada()
        filas = DocumentoExpediente.objects.count()
        actual = self.proyectada(leer_expediente(self.unidad, 2027))
        self.assertIsNone(actual.pk)
        self.assertEqual(actual.recurso_id, origen.recurso_id)
        self.assertIsNotNone(aprobacion_vigente(actual))
        self.assertEqual(DocumentoExpediente.objects.count(), filas)

    def test_no_pisa_observacion_local_en_fila_preparada(self):
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual = self.resolucion(2026)
        actual.observacion = 'Revisar el alcance de esta unidad antes de adjuntar.'
        actual.save(update_fields=['observacion'])
        self.resolucion_aprobada()

        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual.refresh_from_db()
        self.assertIsNone(actual.recurso_id)
        self.assertIn('Revisar el alcance', actual.observacion)

    def test_ultima_revision_observada_impide_recuperar_archivo_mas_antiguo(self):
        origen = self.resolucion_aprobada()
        DocumentoExpediente.objects.create(
            unidad=self.unidad, exigido=origen.exigido, anio=2026,
            version=origen.version + 1, estado='observado',
            observacion='La versión más reciente no está aceptada.')

        actual = self.proyectada(leer_expediente(self.unidad, 2027))
        self.assertIsNone(actual.recurso_id)
        self.assertEqual(actual.estado, 'pendiente')

    def test_retiro_no_resucita_copia_compartida_del_ano_anterior(self):
        origen = self.resolucion_aprobada()
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual = self.resolucion(2026)
        retirar_archivo(actual, self.direccion, 'Resolución retirada para reemplazarla.',
                        actual.version, actual.recurso.hash_sha256)

        origen.recurso.refresh_from_db()
        self.assertEqual(origen.recurso.estado, 'vigente')
        futuro = self.proyectada(leer_expediente(self.unidad, 2027))
        self.assertIsNone(futuro.recurso_id)
        construir_expediente(self.unidad, 2027, hoy=date(2027, 9, 22))
        self.assertIsNone(self.resolucion(2027).recurso_id)

    def test_revocacion_global_no_la_pospone_una_copia_de_ano_futuro(self):
        origen = self.resolucion_aprobada()
        revocar_permanente(origen, self.direccion, 'La autoridad revocó su vigencia.')
        # Una fila anual antigua o importada no es una decisión nueva.
        DocumentoExpediente.objects.create(
            unidad=self.unidad, exigido=origen.exigido, anio=2030,
            estado='validado', recurso=origen.recurso, version=origen.version,
            validado_en=origen.validado_en, validado_por=origen.validado_por)
        for anio in (2026, 2031):
            with self.subTest(anio=anio):
                actual = self.proyectada(leer_expediente(self.unidad, anio))
                self.assertIsNone(actual.recurso_id)
                self.assertTrue(actual.aprobacion_permanente['revocada'])
                self.assertIsNone(aprobacion_vigente(actual))

    def test_sustitucion_en_otro_ano_conserva_archivo_historico_compartido(self):
        origen = self.resolucion_aprobada()
        recurso_original = origen.recurso
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual = self.resolucion(2026)
        observar_documento(actual, self.direccion, 'Reemplazar la resolución por la vigente.',
                           hasta=timezone.now() + timedelta(days=7))
        cargar_documento_revisado(actual, SimpleUploadedFile(
            'resolucion-nueva.pdf', pdf_legible_prueba('Resolución actualizada con nuevo alcance.')),
            self.coordinador)
        recurso_nuevo = actual.recurso_id
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))

        recurso_original.refresh_from_db()
        origen.refresh_from_db()
        actual.refresh_from_db()
        self.assertEqual(recurso_original.estado, 'vigente')
        self.assertTrue(recurso_original.activo)
        self.assertEqual(origen.recurso_id, recurso_original.pk)
        self.assertEqual(actual.recurso_id, recurso_nuevo)
        self.assertNotEqual(recurso_nuevo, recurso_original.pk)
        self.assertEqual(actual.estado, 'cargado')
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]), {
            'anio': 2025, 'gestionar': origen.pk, 'archivo': recurso_original.pk,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(respuesta.streaming_content), pdf_legible_prueba(
            'Resolución de creación, autoridad y alcance.'))

    def test_no_pisa_archivo_propio_ni_atribuye_evaluacion_al_heredar(self):
        origen = self.resolucion_aprobada()
        construir_expediente(self.unidad, 2026, hoy=date(2026, 9, 22))
        actual = self.resolucion(2026)
        actual.observacion = 'Archivo propio ya recibido.'
        actual.save(update_fields=['observacion'])
        completar_aprobaciones([actual])
        _heredar(actual)
        actual.refresh_from_db()
        self.assertEqual(actual.recurso_id, origen.recurso_id)
        self.assertEqual(actual.observacion, 'Archivo propio ya recibido.')
        self.assertIsNone(actual.evaluacion)
        self.assertIsNone(actual.evaluado_por_id)

    def test_carpetas_de_dos_anos_son_distintas_y_se_reutilizan_sin_mover_archivos(self):
        antigua = carpeta_del_expediente(self.unidad, 2025, 'planeacion')
        actual = carpeta_del_expediente(self.unidad, 2026, 'planeacion')
        self.assertNotEqual(antigua.pk, actual.pk)
        self.assertEqual(antigua.nombre, 'Planeación')
        self.assertEqual(actual.nombre, 'Planeación 2026')
        self.assertEqual(antigua.carpeta_padre.nombre, 'Expediente de calidad 2025')
        self.assertEqual(actual.carpeta_padre.nombre, 'Expediente de calidad 2026')
        self.assertEqual(carpeta_del_expediente(self.unidad, 2025, 'planeacion').pk, antigua.pk)
        self.assertEqual(carpeta_del_expediente(self.unidad, 2026, 'planeacion').pk, actual.pk)

    def test_sustitucion_sin_referencias_ajenas_retira_la_version_anterior(self):
        documento = self.documento('RESOLUCION-CREACION', anio=2025)
        cargar_documento_revisado(abrir_entrega(documento), SimpleUploadedFile(
            'resolucion-inicial.pdf', pdf_legible_prueba('Carga inicial aún no enviada.')),
            self.coordinador)
        anterior = documento.recurso
        cargar_documento_revisado(documento, SimpleUploadedFile(
            'resolucion-corregida.pdf', pdf_legible_prueba('Carga corregida antes de enviar.')),
            self.coordinador)
        anterior.refresh_from_db()
        self.assertEqual(anterior.estado, 'obsoleto')
        self.assertFalse(anterior.activo)
        self.assertEqual(documento.recurso.reemplaza_a_id, anterior.pk)
