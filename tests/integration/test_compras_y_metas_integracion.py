"""Las decisiones de compras y metas conservan su separación en los flujos reales."""
from datetime import date
from io import BytesIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.urls import reverse
from pypdf import PdfReader

from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.conformidad_planes import analizar_conformidad
from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
from apps.documentos.presentation.expediente_redaccion import (
    componer, leer_formulario, filas_del_plan, _campos_para_editor,
)
from apps.documentos.presentation.expediente_pdf import render_documento_pdf
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.documentos.presentation.expediente import evaluar_documento
from apps.gestion_unidades.models.espacios import EspacioReservable
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes


class ComprasYMetasIntegracionTests(BaseAlcanceReportes):
    def compra(self, tipo='laboratorios'):
        documento = DocumentoExpediente.objects.create(unidad=self.unidades[tipo],
            exigido=DocumentoExigido.objects.get(codigo='PLAN-COMPRAS-ANUAL'), anio=2026)
        contenido = dict(compras=[], sin_compras_justificacion='<p>Inventario suficiente y revisado.</p>',
            capacidad='<p>Los recursos registrados permiten ejecutar el plan sin adquisiciones.</p>',
            firma_nombre='Coordinación de la unidad', firma_cargo='Coordinación')
        DocumentoElaborado.objects.create(documento=documento, contenido=contenido, version=1)
        return documento, contenido

    def test_editor_de_los_cuatro_tipos_presenta_sin_solicitud_sin_crear_aprobaciones(self):
        for tipo in self.unidades:
            documento, _ = self.compra(tipo)
            self.client.force_login(self.usuarios[tipo])
            cantidad = RegistroAuditoriaUnidad.objects.count()
            respuesta = self.client.get(reverse('redactar_documento_expediente',
                args=[documento.unidad.slug, documento.pk]))
            with self.subTest(tipo=tipo):
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['priorizacion_inversion']['estado'], 'sin_solicitud')
                self.assertContains(respuesta, 'Sin compras justificadas')
                self.assertFalse(respuesta.context['priorizacion_inversion']['autoriza_fondos'])
                self.assertContains(respuesta, 'no autoriza la compra')
                documento.refresh_from_db()
                self.assertIsNone(documento.evaluacion)
                self.assertEqual(RegistroAuditoriaUnidad.objects.count(), cantidad)

    def test_sin_compras_conserva_conformidad_y_el_pdf_explica_que_no_solicita_fondos(self):
        documento, contenido = self.compra()
        _, resumen = analizar_conformidad(documento, SimpleNamespace(inicio=date(2026, 1, 1), fin=date(2026, 12, 8)))
        self.assertEqual(resumen['priorizacion_inversion']['estado'], 'sin_solicitud')
        self.assertFalse(resumen['priorizacion_inversion']['afecta_conformidad'])
        compuesto = componer(documento, contenido, date(2026, 1, 1), date(2026, 12, 8))
        archivo = PdfReader(BytesIO(render_documento_pdf(compuesto)))
        texto = ' '.join(p.extract_text() or '' for p in archivo.pages)
        self.assertIn('Sin solicitud de inversión', texto)
        self.assertIn('fundamento y prioridad de la inversión', texto.casefold())
        self.assertIn('no autoriza financiamiento', texto)
        self.assertNotIn('Umbral de referencia', texto)
        self.assertNotIn('Sin resultado acreditado', texto)

    def test_compromiso_de_aprovechamiento_se_conserva_en_el_formulario_sin_autoaprobar(self):
        datos = QueryDict('', mutable=True)
        datos.update(justificacion_uso_existente='<p>Equipo mínimo para dos prácticas, con responsable y fecha.</p>')
        accion = dict(accion='Programar y registrar las dos prácticas.', responsable='Coordinación de la unidad',
            plazo='2027-02-15', resultado='Dos prácticas ejecutadas y registradas.')
        for clave, valor in accion.items():
            datos.setlist('acciones_cumplimiento__' + clave, [valor])
        contenido = leer_formulario('compras', datos, self.unidades['laboratorios'])
        self.assertEqual(contenido['inversion_gestion_version'], 1)
        self.assertIn('dos prácticas', contenido['justificacion_uso_existente'])
        self.assertEqual(contenido['acciones_cumplimiento'], [accion])
        self.assertNotIn('fundamento_inversion', contenido)
        self.assertNotIn('autoriza_fondos', contenido)

    def test_planes_y_compras_no_admiten_nuevas_rubricas_ni_borran_su_historia(self):
        compra, _ = self.compra()
        plan = self.documentos['laboratorios']
        for documento in (compra, plan):
            DocumentoExpediente.objects.filter(pk=documento.pk).update(
                version=1, evaluacion=75, evaluacion_version=1, evaluado_por=self.direccion)
            documento.refresh_from_db()
            cantidad = RegistroAuditoriaUnidad.objects.count()
            with self.subTest(codigo=documento.exigido.codigo), self.assertRaisesMessage(
                    ValidationError, 'es de cumplimiento obligatorio'):
                evaluar_documento(documento, self.direccion, 90, 'Bien.')
            documento.refresh_from_db()
            self.assertEqual(documento.evaluacion, 75)
            self.assertEqual(RegistroAuditoriaUnidad.objects.count(), cantidad)

    def test_apertura_tardia_usa_piso_servidor_y_editor_explicable_sin_confiar_en_post(self):
        unidad = self.unidades['laboratorios']
        unidad.fecha_inicio = date(2026, 11, 1)
        unidad.save(update_fields=['fecha_inicio'])
        EspacioReservable.objects.create(unidad=unidad, nombre='Escenario mínimo',
            tipo='aula', politica_reserva='general')
        post = QueryDict('', mutable=True)
        post.update(sectores='docencia', act__PRACTICAS__meta='1', act__PRACTICAS_PLAN__meta='1')
        post['act__PRACTICAS-PLAN__meta'] = '1'
        contenido = leer_formulario('planificacion', post, unidad,
            inicio=date(2026, 8, 17), fin=date(2026, 12, 8))
        capacidad = contenido['actividades']['capacidad']
        self.assertEqual(capacidad['practicas_minimas'], 1)
        self.assertTrue(capacidad['requiere_revision'])
        filas = filas_del_plan(unidad, contenido, date(2026, 8, 17), date(2026, 12, 8))
        self.assertEqual(next(f for f in filas if f['codigo'] == 'PRACTICAS')['meta'], '1')
        secciones = _campos_para_editor('planificacion', contenido, unidad, self.documentos['laboratorios'],
            date(2026, 8, 17), date(2026, 12, 8), {})
        dato = next(c for s in secciones for c in s['campos'] if c['campo'].tipo == 'actividades')
        fila = next(f for f in dato['filas'] if f['codigo'] == 'PRACTICAS')
        self.assertEqual(fila['control_meta']['minimo'], '1')
        self.assertTrue(fila['ficha_indicador']['pares'])
        post['act__PRACTICAS__meta'] = '0'
        alterado = leer_formulario('planificacion', post, unidad,
            inicio=date(2026, 8, 17), fin=date(2026, 12, 8))
        # El editor muestra la regla central: el POST no cambia su mínimo.
        self.assertEqual(alterado['actividades']['catalogo']['PRACTICAS']['meta'], '1')

    def test_tabla_de_compras_identifica_conformidad_sin_presentar_prioridad_como_nota(self):
        documento, _ = self.compra()
        lectura = resumen_de_entrega(documento)
        self.assertTrue(lectura['conformidad_plan'])
        self.assertIsNone(lectura['nota'])
