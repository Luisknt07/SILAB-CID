"""La aprobación visible respeta la preparación sin confundirla con metas."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from apps.documentos.presentation.progreso_documento import aplicar_bloqueo_preparacion, completar_avances


MENSAJE = 'Documento incompleto. Devuelve a la unidad para corregir y reenviar.'
TEMPLATES = 'admin/gestion_unidades/reporteoperativounidad/'


class BloqueoPreparacionDocumentalTests(SimpleTestCase):
    def documento(self, codigo='PLANIFICACION', **cambios):
        exigido = SimpleNamespace(codigo=codigo, es_anexo=False, periodicidad='semestral',
                                  redactable=True, fuente_reporte='planificacion', generable=True)
        datos = dict(pk=1, exigido=exigido, estado='validado', automatizacion={}, avance_redaccion=93,
            pendientes_redaccion=['Presupuesto del período'], verificacion_qr='token-de-prueba', version=1,
            recurso_id=1, recurso=SimpleNamespace(hash_sha256='huella-de-prueba'), nombre_documental='Planificación',
            unidad=SimpleNamespace(slug='unidad'), anio=2026, corte='B', etiqueta_corte='2026-B')
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def lectura(self, **cambios_qr):
        qr = dict(enviado=True, aprobado=False, rechazado=False, estado='pendiente', color='amarillo',
                  etiqueta='Pendiente de revisión', fecha=None, puede_aprobar=True, puede_rechazar=True,
                  accion_aprobar='aprobar_qr', accion_rechazar='observar_qr')
        qr.update(cambios_qr)
        return dict(aprobacion_qr=dict(qr), revision_simple=dict(qr),
                    conformidad=dict(estado='pendiente'),
                    avance=dict(porcentaje=100, alcance='metas'))

    def test_el_qr_enviado_incompleto_bloquea_aprobar_y_conserva_la_devolucion(self):
        documento, lectura = self.documento(), self.lectura()
        copia = deepcopy(lectura)
        salida = aplicar_bloqueo_preparacion(documento, lectura)
        self.assertFalse(salida['revision_simple']['puede_aprobar'])
        self.assertTrue(salida['revision_simple']['puede_rechazar'])
        self.assertEqual(salida['revision_simple']['mensaje_bloqueo'], MENSAJE)
        self.assertEqual(salida['avance'], copia['avance'])
        self.assertEqual(lectura, copia)
        self.assertEqual((documento.estado, documento.version), ('validado', 1))
        self.assertEqual(aplicar_bloqueo_preparacion(documento, salida), salida)

    def test_no_cambia_una_aprobacion_existente_o_un_documento_ya_devuelto(self):
        for cambios in (dict(aprobado=True, puede_aprobar=False),
                        dict(rechazado=True, puede_aprobar=False)):
            with self.subTest(cambios=cambios):
                lectura = self.lectura(**cambios)
                self.assertIs(aplicar_bloqueo_preparacion(self.documento(), lectura), lectura)
                self.assertNotIn('mensaje_bloqueo', lectura['revision_simple'])

    def test_el_bloqueo_solo_corresponde_a_qr_efectivamente_enviados(self):
        for cambios in (dict(verificacion_qr=None), dict(estado='generado'), dict(estado='observado')):
            with self.subTest(cambios=cambios):
                lectura = self.lectura()
                self.assertIs(aplicar_bloqueo_preparacion(self.documento(**cambios), lectura), lectura)
        lectura = self.lectura(enviado=False)
        self.assertIs(aplicar_bloqueo_preparacion(self.documento(), lectura), lectura)

    def test_protocolo_completo_puede_aprobar_aunque_su_vigencia_sea_cero(self):
        documento = self.documento('PROTOCOLO-BIOSEGURIDAD', avance_redaccion=100, pendientes_redaccion=[])
        documento.exigido.periodicidad = 'unica'
        lectura = self.lectura()
        lectura['avance'] = dict(porcentaje=0, alcance='vigencia')
        salida = aplicar_bloqueo_preparacion(documento, lectura)
        self.assertTrue(salida['revision_simple']['puede_aprobar'])
        self.assertNotIn('mensaje_bloqueo', salida['revision_simple'])

    def test_informe_redactado_no_se_bloquea_por_un_cumplimiento_parcial(self):
        documento = self.documento('INFORME-SEMESTRAL', avance_redaccion=100, pendientes_redaccion=[])
        lectura = self.lectura()
        lectura['avance'] = dict(porcentaje=8.3, alcance='metas')
        self.assertTrue(aplicar_bloqueo_preparacion(documento, lectura)['revision_simple']['puede_aprobar'])

    def test_no_inventa_un_bloqueo_sin_preparacion_medida(self):
        for valor in (None, 'NaN', 'no medido'):
            with self.subTest(valor=valor):
                lectura = self.lectura()
                self.assertIs(aplicar_bloqueo_preparacion(self.documento(avance_redaccion=valor), lectura), lectura)

    def test_el_lote_conserva_los_faltantes_y_bloquea_una_lectura_ya_preparada(self):
        documento = self.documento()
        del documento.pendientes_redaccion
        documento.resumen_interfaz = self.lectura()
        completar_avances([documento], redacciones={})
        self.assertLess(documento.avance_redaccion, 100)
        self.assertTrue(documento.pendientes_redaccion)
        self.assertFalse(documento.resumen_interfaz['revision_simple']['puede_aprobar'])
        self.assertEqual(documento.resumen_interfaz['revision_simple']['mensaje_bloqueo'], MENSAJE)
        # Todos los datos de edición están precargados; repetir no consulta BD.
        completar_avances([documento])

    def test_el_resumen_con_preparacion_precargada_tambien_bloquea_la_aprobacion(self):
        from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
        documento = self.documento(nota=None, evaluado_por_id=None, evaluacion=None, evaluacion_version=None,
            observacion='', evaluacion_observacion='', evaluacion_debilidades='', tardanza_motivo='',
            plazo_entrega=None, prorroga_hasta=None, correccion_hasta=None, ultimatum_hasta=None,
            recibido_por_id=None, recibido_en=None, evaluado_en=None, validado_en=None)
        qr = self.lectura()['aprobacion_qr']
        with patch('apps.documentos.presentation.conformidad_lectura.lectura_conformidad',
                   return_value=dict(estado='pendiente', etiqueta='Pendiente', fecha=None)), \
             patch('apps.documentos.presentation.conformidad_permanente.es_permanente', return_value=False), \
             patch('apps.documentos.presentation.aprobacion_en_linea.lectura_aprobacion_qr', return_value=qr), \
             patch('apps.documentos.presentation.perfil_laboratorios.es_laboratorio', return_value=True), \
             patch('apps.documentos.presentation.perfil_unidades.es_unidad_auditable', return_value=True), \
             patch('apps.documentos.presentation.decision_automatica.excepcion_resuelta_por_revision', return_value=False):
            resumen = resumen_de_entrega(documento)
        self.assertFalse(resumen['revision_simple']['puede_aprobar'])
        self.assertEqual(resumen['revision_simple']['mensaje_bloqueo'], MENSAJE)

    def test_las_acciones_de_tabla_y_dialogo_muestran_el_bloqueo_y_mantienen_rechazar(self):
        documento = self.documento()
        lectura = aplicar_bloqueo_preparacion(documento, self.lectura())
        documento.resumen_interfaz = lectura
        request = RequestFactory().get('/direccion/')
        request.user = SimpleNamespace(is_superuser=True)
        contexto = dict(d=documento, lectura=lectura, revision=SimpleNamespace(documento=documento),
                        request=request, user=request.user, query='anio=2026&corte=B')
        for nombre in ('qr_acciones_fila.html', 'revision_qr.html'):
            with self.subTest(nombre=nombre):
                html = render_to_string(TEMPLATES + nombre, contexto)
                self.assertIn(MENSAJE, html)
                self.assertIn('data-bloqueo-preparacion', html)
                self.assertIn('class="revision-documental__boton is-aprobar" disabled', html)
                self.assertIn('Rechazar', html)

    def test_las_plantillas_no_anaden_aviso_a_documentos_completos(self):
        documento = self.documento(avance_redaccion=100, pendientes_redaccion=[])
        lectura = aplicar_bloqueo_preparacion(documento, self.lectura())
        documento.resumen_interfaz = lectura
        request = RequestFactory().get('/direccion/')
        request.user = SimpleNamespace(is_superuser=True)
        contexto = dict(d=documento, lectura=lectura, revision=SimpleNamespace(documento=documento),
                        request=request, user=request.user, query='anio=2026&corte=B')
        for nombre in ('qr_acciones_fila.html', 'revision_qr.html'):
            with self.subTest(nombre=nombre):
                html = render_to_string(TEMPLATES + nombre, contexto)
                self.assertNotIn('data-bloqueo-preparacion', html)
                self.assertNotIn('class="revision-documental__boton is-aprobar" disabled', html)
