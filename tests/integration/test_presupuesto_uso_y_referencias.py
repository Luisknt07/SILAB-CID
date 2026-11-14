from copy import deepcopy
from datetime import date
from io import BytesIO
from pypdf import PdfReader

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.template.loader import render_to_string
from django.urls import reverse

from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad
from apps.documentos.presentation.expediente_redaccion import filas_del_plan, secciones_de
from apps.documentos.presentation.politica_metas_unidades import capacidad_de, actividades_proporcionales
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN
from apps.documentos.presentation.presupuesto_uso import leer_presupuesto, comprobar_presupuesto, datos_presupuesto
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes


class PresupuestoUsoYReferenciasTests(BaseAlcanceReportes):
    inicio, fin = date(2026, 7, 1), date(2026, 12, 31)

    def presupuesto(self, total='12'):
        return dict(version=1, horas_comprometidas=total, justificacion='Seis sesiones de dos horas con responsable y recursos disponibles.',
            horas_por_mes={str(m): '2' for m in range(7, 13)})

    def test_total_se_suma_en_servidor_y_no_acepta_total_del_cliente(self):
        post = QueryDict('', mutable=True)
        post.update(uso_horas__7='1.5', uso_horas__8='2.25', horas_comprometidas='999',
            uso_justificacion='<p>Prácticas de dos asignaturas.</p>')
        dato = leer_presupuesto(post, self.inicio, self.fin)
        self.assertEqual(dato['horas_comprometidas'], '3.75')
        self.assertEqual(dato['horas_por_mes'], {'7': '1.5', '8': '2.25'})

    def test_numeros_invalidos_no_se_convierten_en_compromisos(self):
        for texto in ('-1', 'NaN', 'Infinity', '745', '0.001'):
            post = QueryDict('', mutable=True)
            post['uso_horas__7'] = texto
            with self.subTest(texto=texto), self.assertRaises(ValidationError):
                leer_presupuesto(post, self.inicio, self.fin)

    def test_programacion_requiere_todos_los_meses_y_fundamento(self):
        errores, lectura = comprobar_presupuesto(self.presupuesto(), self.inicio, self.fin)
        self.assertEqual(errores, [])
        self.assertEqual(lectura['horas_comprometidas'], '12')
        dato = self.presupuesto()
        dato['horas_por_mes'].pop('12')
        self.assertTrue(comprobar_presupuesto(dato, self.inicio, self.fin)[0])
        dato = self.presupuesto()
        dato['justificacion'] = '<p><br></p>'
        self.assertTrue(comprobar_presupuesto(dato, self.inicio, self.fin)[0])

    def test_total_alterado_no_se_acredita_y_cero_exige_revision(self):
        self.assertTrue(comprobar_presupuesto(self.presupuesto('100'), self.inicio, self.fin)[0])
        dato = self.presupuesto('0')
        dato['horas_por_mes'] = {str(m): '0' for m in range(7, 13)}
        errores, lectura = comprobar_presupuesto(dato, self.inicio, self.fin)
        self.assertEqual(lectura['horas_comprometidas'], '0')
        self.assertEqual(errores[0][2], 'revision')

    def test_uso_efectivo_se_evalua_aparte_de_la_cobertura_de_registro(self):
        contenido = dict(presupuesto_uso=self.presupuesto())
        filas = filas_del_plan(self.unidades['laboratorios'], contenido, self.inicio, self.fin)
        uso = next(f for f in filas if f['codigo'] == 'USO-EFECTIVO')
        self.assertEqual(uso['meta'], '12')
        self.assertEqual(uso['contador'], 'horas_uso_efectivo')
        self.assertTrue(uso['obligatoria'])
        self.assertIn('USO', {f['codigo'] for f in filas})

    def test_presupuesto_fisico_no_se_impone_al_observatorio(self):
        self.assertNotIn('uso_capacidad', {s.codigo for s in secciones_de('planificacion', self.unidades['observatorios'])})
        self.assertNotIn('USO-EFECTIVO', {f['codigo'] for f in filas_del_plan(
            self.unidades['observatorios'], dict(presupuesto_uso=self.presupuesto()), self.inicio, self.fin)})

    def test_pdf_nativo_incluye_todos_los_meses_y_el_fundamento(self):
        from apps.documentos.presentation.expediente_redaccion import componer
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        contenido = dict(presupuesto_uso=self.presupuesto())
        contenido['presupuesto_uso']['horas_por_mes']['12'] = '0'
        pdf = render_documento_pdf(componer(self.documentos['laboratorios'], contenido, self.inicio, self.fin))
        texto = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn('Fundamento de la programación', texto)
        self.assertIn('Seis sesiones de dos horas', texto)
        self.assertIn('Julio', texto)
        self.assertIn('Diciembre', texto)

    def test_referencias_configurables_quedan_conservadas_sin_reescribir_el_plan(self):
        unidad = self.unidades['laboratorios']
        r, _ = ReferenciaIndicadorUnidad.objects.update_or_create(
            tipo_unidad='laboratorios', codigo='GUIAS', nivel_capacidad='',
            defaults=dict(valor=3, fundamento='Tres asignaturas requieren guías distintas.'))
        capacidad = capacidad_de(unidad, self.inicio, self.fin)
        anterior = deepcopy(capacidad)
        r.valor = 4
        r.save()
        originales = actividades_proporcionales(ACTIVIDADES_PLAN, 'laboratorios', capacidad=anterior)
        nuevas = actividades_proporcionales(ACTIVIDADES_PLAN, 'laboratorios', capacidad=capacidad_de(unidad, self.inicio, self.fin))
        self.assertEqual(next(a.minimo for a in originales if a.codigo == 'GUIAS'), '≥ 3 por período')
        self.assertEqual(next(a.minimo for a in nuevas if a.codigo == 'GUIAS'), '≥ 4 por período')

    def test_configuracion_exige_fundamento_y_no_redefine_coberturas_de_seguridad(self):
        r = ReferenciaIndicadorUnidad(tipo_unidad='laboratorios', codigo='GUIAS', valor=3, fundamento='')
        with self.assertRaises(ValidationError):
            r.full_clean()
        r.codigo, r.fundamento = 'SEGURIDAD', 'Intento de reducir cobertura'
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_editor_mensual_y_acceso_a_configuracion_respetan_permisos(self):
        html = render_to_string('portal/pages/unidades/gestion/includes/presupuesto_uso_editor.html',
            dict(presupuesto=datos_presupuesto(self.presupuesto(), self.inicio, self.fin)))
        self.assertEqual(html.count('name="uso_horas__'), 6)
        self.assertIn('Fundamento de la programación', html)
        ruta = reverse('admin:documentos_referenciaindicadorunidad_changelist')
        self.client.force_login(self.usuarios['laboratorios'])
        self.assertNotEqual(self.client.get(ruta).status_code, 200)
        self.client.force_login(self.direccion)
        self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_guardado_sin_campo_nuevo_conserva_compromiso_existente(self):
        d = self.documentos['laboratorios']
        DocumentoElaborado.objects.create(documento=d, version=1, contenido=dict(presupuesto_uso=self.presupuesto()))
        self.client.force_login(self.usuarios['laboratorios'])
        respuesta = self.client.post(reverse('redactar_documento_expediente', args=[d.unidad.slug, d.pk]),
            dict(version_base='1', accion='guardar'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(DocumentoElaborado.objects.get(documento=d).contenido['presupuesto_uso'], self.presupuesto())
