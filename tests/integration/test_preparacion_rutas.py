"""La emisión, el envío y la recepción comparten los requisitos del editor."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
from apps.documentos.presentation.aprobacion_en_linea import enviar_documento_qr
from apps.documentos.presentation.expediente import generar_documento, recibir_documento, validar_documento
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.recursos import Recurso
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.test_protocolo_seguridad import protocolo_completo
from tests.integration.utiles import abrir_entrega, correspondencia_revisada


class PreparacionEnRutasDeEntregaTests(BaseDeRedaccion):
    def setUp(self):
        self.director = get_user_model().objects.create_superuser(
            username='direccion-preparacion-rutas-qa', password=None)
        designar(self.director)

    def compras_preparadas_sin_qr(self):
        documento = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido={
            'capacidad': '<p>Los equipos y las existencias actuales cubren las actividades previstas; '
                         'el personal y los espacios permiten sostener la operación sin adquisiciones.</p>',
            'firma_nombre': self.coordinador.get_full_name(),
            'firma_cargo': 'Responsable de la unidad',
            'sin_compras_justificacion': '<p>El inventario y los materiales disponibles cubren el año siguiente; '
                                        'no se solicitan adquisiciones ni contratación adicional.</p>',
        })
        generar_documento(documento, self.coordinador)
        redaccion.refresh_from_db()
        self.assertIsNotNone(redaccion.generado_en)
        self.assertEqual(documento.estado, 'generado')
        self.assertTrue(documento.recurso_id)
        # Representa la ruta anterior de firma fuera de la plataforma, cuya
        # preparación nativa debe conservar las mismas comprobaciones.
        DocumentoExpediente.objects.filter(pk=documento.pk).update(
            verificacion_qr=None, estado='cargado', firma_verificada=True)
        documento.refresh_from_db()
        # En PAC por áreas, el sustento se exige por necesidad; el ensayo
        # global de capacidad ya no es un campo obligatorio del formulario.
        redaccion.contenido = dict(redaccion.contenido, sin_compras_justificacion='')
        redaccion.version += 1
        redaccion.save(update_fields=['contenido', 'version'])
        return documento

    @staticmethod
    def estado_documental(documento):
        return (documento.estado, documento.recurso_id, documento.version, documento.recibido_en,
                documento.recibido_por_id, documento.validado_en, documento.validado_por_id,
                documento.entregado_en, documento.verificacion_qr)

    def comprobar_rechazo_sin_cambios(self, documento, operacion, mensaje):
        anterior = self.estado_documental(documento)
        recursos = Recurso.objects.count()
        with self.assertRaisesMessage(ValidationError, mensaje):
            operacion()
        documento.refresh_from_db()
        self.assertEqual(self.estado_documental(documento), anterior)
        self.assertEqual(Recurso.objects.count(), recursos)

    def test_envio_firmado_sin_qr_revalida_los_campos_del_editor(self):
        documento = self.compras_preparadas_sin_qr()
        self.comprobar_rechazo_sin_cambios(documento,
            lambda: validar_documento(documento, self.coordinador,
                declaracion_correspondencia=correspondencia_revisada(documento)),
            'justifica por qué la unidad no requiere compras')

    def test_recepcion_director_sin_qr_revalida_los_campos_del_editor(self):
        documento = self.compras_preparadas_sin_qr()
        self.comprobar_rechazo_sin_cambios(documento,
            lambda: recibir_documento(documento, self.director,
                declaracion_correspondencia=correspondencia_revisada(documento)),
            'justifica por qué la unidad no requiere compras')

    def protocolo_preparado_con_fuentes_nuevas(self):
        documento = abrir_entrega(self.documento('PROTOCOLO-BIOSEGURIDAD', corte=''))
        DocumentoElaborado.objects.create(documento=documento, version=1,
            contenido=protocolo_completo(documento))
        generar_documento(documento, self.coordinador)
        self.assertTrue(documento.verificacion_qr)
        Consumible.objects.create(unidad=self.unidad, codigo='RUTA-PROTOCOLO-REACTIVO-QA',
            nombre='Reactivo añadido después de preparar el protocolo', clasificacion='reactivo')
        return documento

    def test_envio_protocolo_pide_revisar_propuestas_si_cambian_los_registros(self):
        preparado = self.protocolo_preparado_con_fuentes_nuevas()
        documento = DocumentoExpediente.objects.get(pk=preparado.pk)
        self.comprobar_rechazo_sin_cambios(documento,
            lambda: enviar_documento_qr(documento, self.coordinador,
                token=documento.verificacion_qr, version=documento.version),
            'Revisión del contenido propuesto')

    def test_envio_protocolo_no_reutiliza_el_contexto_previo_de_la_misma_instancia(self):
        documento = self.protocolo_preparado_con_fuentes_nuevas()
        self.comprobar_rechazo_sin_cambios(documento,
            lambda: enviar_documento_qr(documento, self.coordinador,
                token=documento.verificacion_qr, version=documento.version),
            'Revisión del contenido propuesto')
