"""Una decisión binaria sobre el archivo permanente, sin notas ni repetición anual."""
from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.conformidad_permanente import (
    APROBAR, REVOCAR, aprobacion_vigente, aprobar_permanente,
    completar_aprobaciones, es_permanente, revocar_permanente,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso
from tests.integration.utiles import correspondencia_revisada, pdf_legible_prueba


class ConformidadPermanenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.direccion = usuarios.objects.create_superuser('conformidad-direccion', password=None)
        cls.coordinador = usuarios.objects.create_user('conformidad-coordinador', password=None)
        cls.unidad = Unidad.objects.create(nombre='Laboratorio permanente', slug='laboratorio-permanente',
            dependencia='laboratorios', administrador=cls.coordinador, activo=True,
            fecha_inicio=date(2024, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otro laboratorio permanente', slug='otro-laboratorio-permanente',
            dependencia='laboratorios', administrador=cls.coordinador, activo=True,
            fecha_inicio=date(2024, 1, 1))
        cls.exigido, _ = DocumentoExigido.objects.get_or_create(codigo='RESOLUCION-CREACION',
            defaults=dict(nombre='Resolución de creación', carpeta='planeacion',
                          periodicidad='unica', origen='unidad', requiere_firma=False))

    def setUp(self):
        medios = TemporaryDirectory(prefix='citt-conformidad-permanente-')
        self.addCleanup(medios.cleanup)
        ajustes = override_settings(MEDIA_ROOT=medios.name)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.documento = self.crear_documento()

    def crear_documento(self, *, unidad=None, anio=2026, recurso=None, estado='cargado'):
        unidad = unidad or self.unidad
        recurso = recurso or Recurso.objects.create(unidad=unidad, nombre='Resolución institucional',
            descripcion='Acto de creación archivado para la prueba aislada.', tipo_adjunto='norma',
            archivo=ContentFile(pdf_legible_prueba('Resolución de creación del laboratorio.'), name='resolucion.pdf'),
            version=1)
        return DocumentoExpediente.objects.create(unidad=unidad, exigido=self.exigido,
            anio=anio, corte='', recurso=recurso, version=1, estado=estado)

    def aprobar(self, documento=None, usuario=None, **cambios):
        documento = documento or self.documento
        datos = dict(version=documento.version, huella=documento.recurso.hash_sha256,
                     confirmado=True, declaracion_correspondencia=correspondencia_revisada(documento))
        datos.update(cambios)
        return aprobar_permanente(documento, usuario or self.direccion, **datos)

    def test_aceptacion_binaria_conserva_nota_historica_sin_crear_otra(self):
        d = self.documento
        d.evaluacion, d.evaluacion_version = 75, d.version
        d.evaluado_por = self.direccion
        d.save(update_fields=['evaluacion', 'evaluacion_version', 'evaluado_por'])
        aprobacion = self.aprobar()
        d.refresh_from_db()
        self.assertTrue(aprobacion['vigente'])
        self.assertEqual(d.estado, 'validado')
        self.assertEqual(d.recibido_por, self.direccion)
        self.assertEqual((d.evaluacion, d.evaluacion_version), (75, 1))
        self.assertNotIn('nota', aprobacion)
        registro = RegistroAuditoriaUnidad.objects.get(descripcion=APROBAR)
        self.assertEqual(registro.datos_nuevos['sha256'], d.recurso.hash_sha256)
        self.assertEqual(registro.datos_nuevos['actor_id'], self.direccion.pk)

    def test_coordinacion_no_puede_aceptar_el_documento_propio(self):
        with self.assertRaises(ValidationError):
            self.aprobar(usuario=self.coordinador)
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).exists())

        self.documento.refresh_from_db()
        self.assertEqual(self.documento.estado, 'cargado')

    def test_acciones_comunes_aprueban_y_rechazan_un_documento_externo_sin_qr(self):
        from apps.documentos.presentation.revision_documental import decidir_desde_listado
        d = self.documento
        d.estado = 'validado'
        d.save(update_fields=['estado'])
        decidir_desde_listado(d, self.direccion, version=d.version,
            huella=d.recurso.hash_sha256, decision='aprobar')
        self.assertTrue(aprobacion_vigente(d))
        decidir_desde_listado(d, self.direccion, version=d.version,
            huella=d.recurso.hash_sha256, decision='rechazar', observacion='Actualizar el alcance de la resolución.')
        d.refresh_from_db()
        self.assertEqual(d.estado, 'observado')
        self.assertEqual(d.observacion, 'Actualizar el alcance de la resolución.')
        self.assertTrue(d.correccion_abierta)

    def test_accion_comun_no_aprueba_sin_envio_ni_con_identidad_o_rol_incorrecto(self):
        from apps.documentos.presentation.revision_documental import decidir_desde_listado
        d = self.documento
        with self.assertRaises(ValidationError):
            decidir_desde_listado(d, self.direccion, version=d.version,
                huella=d.recurso.hash_sha256, decision='aprobar')
        d.estado = 'validado'
        d.save(update_fields=['estado'])
        for usuario, version in ((self.coordinador, d.version), (self.direccion, d.version+1)):
            with self.assertRaises(ValidationError):
                decidir_desde_listado(d, usuario, version=version,
                    huella=d.recurso.hash_sha256, decision='aprobar')
    def test_admin_aprueba_con_un_solo_envio_y_muestra_vigencia_sin_rubrica(self):
        from tests.integration.utiles import datos_correspondencia_revisada
        d = self.documento
        self.client.force_login(self.direccion)
        url = reverse('admin:reportes-cumplimiento-expediente')
        respuesta = self.client.post(url, dict(accion='aprobar_permanente', documento=d.pk,
            version=d.version, huella=d.recurso.hash_sha256, confirmado='1',
            query=f'anio=2026&revisar={d.pk}', **datos_correspondencia_revisada(d)))
        self.assertEqual(respuesta.status_code, 302)
        d.refresh_from_db()
        self.assertIsNone(d.evaluacion)
        self.assertTrue(aprobacion_vigente(d))
        pagina = self.client.get(url, dict(anio=2026, revisar=d.pk))
        self.assertContains(pagina, 'data-estado-aprobacion="aprobado"')
        self.assertNotContains(pagina, 'name="criterio_0"')
        self.assertNotContains(pagina, 'Guardar evaluación y observaciones')
        self.assertNotContains(pagina, 'name="accion" value="aprobar_permanente"')

    def test_exige_snapshot_actual_y_confirmacion_explicita(self):
        for cambios in (dict(version=2), dict(huella='f' * 64), dict(confirmado=False)):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                self.aprobar(**cambios)
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).exists())

    def test_exige_una_comprobacion_humana_de_correspondencia_externa(self):
        with self.assertRaises(ValidationError):
            self.aprobar(declaracion_correspondencia=None)
        self.assertIsNone(aprobacion_vigente(self.documento))

    def test_misma_aceptacion_sirve_en_otro_anio_sin_recalificar(self):
        origen = self.aprobar()
        heredado = self.crear_documento(anio=2027, recurso=self.documento.recurso, estado='validado')
        aprobacion = aprobacion_vigente(heredado, inspeccionar=True)
        self.assertTrue(aprobacion['vigente'])
        self.assertEqual(aprobacion['auditoria_id'], origen['auditoria_id'])
        self.assertEqual(aprobacion['documento_id'], self.documento.pk)
        self.assertIsNone(heredado.evaluacion)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 1)

    def test_no_acepta_cruce_de_unidad_aunque_copie_recurso_y_version(self):
        self.aprobar()
        cruzado = self.crear_documento(unidad=self.otra, recurso=self.documento.recurso, estado='validado')
        self.assertIsNone(aprobacion_vigente(cruzado))
        with self.assertRaises(ValidationError):
            self.aprobar(cruzado)

    def test_bytes_alterados_invalidan_aceptacion_y_no_se_reaprueban(self):
        self.aprobar()
        d = self.documento
        with d.recurso.archivo.storage.open(d.recurso.archivo.name, 'wb') as archivo:
            archivo.write(pdf_legible_prueba('Contenido reemplazado después de la aceptación.'))
        self.assertIsNone(aprobacion_vigente(d, inspeccionar=True))
        self.assertIsNone(aprobacion_vigente(d))
        with self.assertRaises(ValidationError):
            self.aprobar()
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 1)

    def test_revocacion_impide_revivir_aprobacion_en_cualquier_anio(self):
        self.aprobar()
        futuro = self.crear_documento(anio=2027, recurso=self.documento.recurso, estado='validado')
        revocar_permanente(self.documento, self.direccion, 'El acto institucional fue sustituido.')
        completar_aprobaciones([self.documento, futuro])
        for documento in (self.documento, futuro):
            self.assertTrue(documento.aprobacion_permanente['revocada'])
            self.assertIsNone(aprobacion_vigente(documento))
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=REVOCAR).count(), 1)

    def test_control_bloqueado_persistido_impide_acreditar_una_lectura_nueva(self):
        from apps.documentos.presentation.automatizacion_documental import (
            procesar_documento,
        )
        self.aprobar()
        d = self.documento
        with d.recurso.archivo.storage.open(d.recurso.archivo.name, 'wb') as archivo:
            archivo.write(pdf_legible_prueba('Archivo alterado después de su aceptación.'))
        control = procesar_documento(d, usuario=self.direccion)
        self.assertEqual(control.estado, 'bloqueado')
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=d.pk)
        # La lectura directa debe respetar el bloqueo sin otro proyector previo.
        with self.assertNumQueries(2):
            self.assertIsNone(aprobacion_vigente(fresco))
        with self.assertNumQueries(0):
            self.assertIsNone(aprobacion_vigente(fresco))
            self.assertFalse(fresco.aprobacion_permanente['vigente'])
            self.assertIsNone(fresco.nota)

    def test_aceptar_de_nuevo_el_mismo_archivo_es_idempotente(self):
        primera = self.aprobar()
        segunda = self.aprobar()
        self.assertEqual(primera['auditoria_id'], segunda['auditoria_id'])
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 1)

    def test_restaurar_bytes_y_reaprobar_repara_control_y_conserva_idempotencia(self):
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        from apps.documentos.presentation.automatizacion_documental import procesar_documento

        primera = self.aprobar()
        d = self.documento
        with d.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        with d.recurso.archivo.storage.open(d.recurso.archivo.name, 'wb') as archivo:
            archivo.write(pdf_legible_prueba('Alteración posterior.'))
        self.assertEqual(procesar_documento(d, usuario=self.direccion).estado, 'bloqueado')
        with d.recurso.archivo.storage.open(d.recurso.archivo.name, 'wb') as archivo:
            archivo.write(original)

        reparada = self.aprobar()

        self.assertNotEqual(primera['auditoria_id'], reparada['auditoria_id'])
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=d.pk)
        self.assertEqual(aprobacion_vigente(fresco)['auditoria_id'], reparada['auditoria_id'])
        self.assertEqual(fresco.nota, 100)
        self.assertEqual(ControlAutomaticoDocumento.objects.get(documento=d).estado, 'automatico')
        repetida = self.aprobar(fresco)
        self.assertEqual(repetida['auditoria_id'], reparada['auditoria_id'])
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 2)

    def test_control_actual_positivo_supera_bloqueo_canonico_solo_con_configuracion_vigente(self):
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        from apps.documentos.presentation.automatizacion_documental import procesar_documento

        self.aprobar()
        origen = self.documento
        copia = self.crear_documento(anio=2027, recurso=origen.recurso, estado='validado')
        with origen.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        with origen.recurso.archivo.storage.open(origen.recurso.archivo.name, 'wb') as archivo:
            archivo.write(pdf_legible_prueba('Alteración del archivo compartido.'))
        self.assertEqual(procesar_documento(origen, usuario=self.direccion).estado, 'bloqueado')
        with origen.recurso.archivo.storage.open(origen.recurso.archivo.name, 'wb') as archivo:
            archivo.write(original)

        control = procesar_documento(copia, usuario=self.direccion)

        self.assertEqual((control.estado, control.aplicado), ('automatico', True))
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=copia.pk)
        self.assertIsNotNone(aprobacion_vigente(fresco))
        self.assertEqual(fresco.nota, 100)
        self.assertEqual(ControlAutomaticoDocumento.objects.get(documento=origen).estado, 'bloqueado')
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 1)
        control.resumen['configuracion_sha256'] = 'configuracion-obsoleta'
        control.save(update_fields=['resumen'])
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=copia.pk)
        self.assertIsNone(aprobacion_vigente(fresco))

    def test_recurso_obsoleto_version_nueva_y_estado_observado_no_son_vigentes(self):
        self.aprobar()
        d = self.documento
        d.recurso.activo = False
        self.assertIsNone(aprobacion_vigente(d))
        d.recurso.activo = True
        d.recurso.estado = 'obsoleto'
        self.assertIsNone(aprobacion_vigente(d))
        d.recurso.estado = 'vigente'
        d.version += 1
        self.assertIsNone(aprobacion_vigente(d))
        d.version -= 1
        d.estado = 'observado'
        self.assertIsNone(aprobacion_vigente(d))

    def test_consulta_por_lote_usa_dos_consultas_y_recalcula_tras_heredar(self):
        self.aprobar()
        futuro = self.crear_documento(anio=2027, recurso=self.documento.recurso, estado='pendiente')
        futuros = list(DocumentoExpediente.objects.filter(pk__in=[self.documento.pk, futuro.pk])
                       .select_related('unidad', 'exigido', 'recurso'))
        with self.assertNumQueries(2):
            completar_aprobaciones(futuros)
        destino = next(d for d in futuros if d.pk == futuro.pk)
        self.assertFalse(destino.aprobacion_permanente['vigente'])
        destino.estado = 'validado'
        with self.assertNumQueries(0):
            self.assertTrue(aprobacion_vigente(destino)['vigente'])

    def test_aprobar_con_instancia_antigua_no_omite_una_revocacion_posterior(self):
        primera = self.aprobar()
        anterior = self.documento
        otra_lectura = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=anterior.pk)
        revocar_permanente(otra_lectura, self.direccion, 'Confirmar nuevamente el alcance.')

        nueva = self.aprobar(anterior)

        self.assertNotEqual(nueva['auditoria_id'], primera['auditoria_id'])
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 2)
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=anterior.pk)
        self.assertEqual(aprobacion_vigente(fresco)['auditoria_id'], nueva['auditoria_id'])

    def test_revocar_con_instancia_antigua_no_omite_una_aprobacion_posterior(self):
        self.aprobar()
        anterior = self.documento
        primera = revocar_permanente(anterior, self.direccion, 'Alcance pendiente.')
        otra_lectura = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=anterior.pk)
        nueva = self.aprobar(otra_lectura)

        ultima = revocar_permanente(anterior, self.direccion, 'Alcance pendiente.')

        self.assertNotEqual(ultima['auditoria_id'], primera['auditoria_id'])
        self.assertGreater(ultima['auditoria_id'], nueva['auditoria_id'])
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=REVOCAR).count(), 2)
        fresco = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(pk=anterior.pk)
        self.assertIsNone(aprobacion_vigente(fresco))

    def test_fuera_de_los_dos_documentos_permanentes_no_se_reutiliza(self):
        d = self.documento
        d.exigido = DocumentoExigido(codigo='OTRO-UNICO', periodicidad='unica')
        self.assertFalse(es_permanente(d))
        self.assertIsNone(aprobacion_vigente(d))

    def test_cambio_de_identidad_o_funcion_requiere_confirmar_alcance(self):
        self.aprobar()
        d = self.documento
        for campo, valor in (('codigo', 'NUEVA-IDENTIDAD'),
                ('dependencia', 'observatorios'), ('clasificacion_funcional', 'otra-funcion')):
            with self.subTest(campo=campo):
                anterior = getattr(d.unidad, campo)
                setattr(d.unidad, campo, valor)
                self.assertIsNone(aprobacion_vigente(d))
                self.assertIn('confirma el alcance', d.aprobacion_permanente['aviso'])
                setattr(d.unidad, campo, anterior)
        self.assertIsNotNone(aprobacion_vigente(d))

    def test_ubicacion_del_protocolo_pertenece_al_alcance_aceptado(self):
        d = self.documento
        protocolo, _ = DocumentoExigido.objects.get_or_create(codigo='PROTOCOLO-BIOSEGURIDAD',
            defaults=dict(nombre='Protocolo de seguridad', carpeta='planeacion',
                          periodicidad='unica', origen='unidad', requiere_firma=True))
        d.exigido, d.firma_verificada = protocolo, True
        d.save(update_fields=['exigido', 'firma_verificada'])
        self.aprobar(d)
        d.unidad.ubicacion = 'Nueva instalación con otros riesgos'
        self.assertIsNone(aprobacion_vigente(d))
        self.assertIn('confirma el alcance', d.aprobacion_permanente['aviso'])

    def test_fechas_administrativas_y_ubicacion_no_recalifican_la_resolucion(self):
        self.aprobar()
        d = self.documento
        d.unidad.ubicacion = 'Ubicación administrativa actualizada'
        d.abre_el, d.vence_el = date(2026, 2, 1), date(2026, 12, 31)
        self.assertIsNotNone(aprobacion_vigente(d))
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(descripcion=APROBAR).count(), 1)
