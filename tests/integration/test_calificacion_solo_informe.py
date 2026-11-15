"""Solo el informe semestral se califica, con el cumplimiento de sus metas; lo demás es de cumplimiento obligatorio."""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.expediente import CODIGO_CALIFICABLE, DocumentoExigido
from apps.documentos.presentation.expediente import construir_expediente
from apps.documentos.presentation.expediente_catalogo import CATALOGO, CATALOGO_PERFILES
from apps.documentos.presentation.incumplimiento_documental import evaluar_vencimientos
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_cumplimiento_expediente import BaseDeCumplimiento
from tests.integration.utiles import registrar_antecedente_evaluacion


class SoloElInformeSeCalificaTests(BaseDeCumplimiento):
    def documento(self, codigo, corte='A'):
        return next(d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
                    if d.exigido.codigo == codigo and (d.corte == corte or not d.corte))

    def test_solo_el_informe_es_calificable(self):
        calificables = {e.codigo for e in DocumentoExigido.objects.all() if e.calificable}
        self.assertEqual(calificables, {CODIGO_CALIFICABLE})

    def test_ningun_documento_de_cumplimiento_obligatorio_recibe_porcentaje(self):
        from apps.documentos.presentation.expediente import evaluar_documento

        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL', 'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD'):
            with self.subTest(codigo=codigo):
                documento = self.documento(codigo)
                with self.assertRaises(ValidationError):
                    evaluar_documento(documento, self.direccion, 90, 'Bien.')
                documento.refresh_from_db()
                self.assertIsNone(documento.evaluacion)

    def test_la_nota_del_informe_no_se_escribe_a_mano(self):
        from apps.documentos.presentation.expediente import evaluar_documento

        informe = self.documento('INFORME-SEMESTRAL')
        informe.estado = 'validado'
        informe.save(update_fields=['estado'])
        with self.assertRaisesMessage(ValidationError, 'sale del cumplimiento de las metas'):
            evaluar_documento(informe, self.direccion, 95, 'Muy bien.')
        informe.refresh_from_db()
        self.assertIsNone(informe.evaluacion)

    def test_una_nota_antigua_de_un_plan_no_cuenta_como_calificacion(self):
        plan = self.documento('PLANIFICACION')
        registrar_antecedente_evaluacion(plan, self.direccion, 40, 'Calificación anterior a la regla.')
        plan.refresh_from_db()
        self.assertIsNone(plan.nota)
        self.assertIsNone(plan.cumple)

    def test_la_administracion_no_califica_a_mano(self):
        plan = self.documento('PLANIFICACION')
        self.client.force_login(self.direccion)
        respuesta = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), {
            'documento': plan.pk, 'accion': 'evaluar', 'evaluacion': '90', 'query': 'anio=2026'}, follow=True)
        self.assertContains(respuesta, 'es de cumplimiento obligatorio')
        plan.refresh_from_db()
        self.assertIsNone(plan.evaluacion)

    def test_el_vencimiento_registra_incumplimiento_y_solo_el_informe_vale_cero(self):
        plan, informe = self.documento('PLANIFICACION'), self.documento('INFORME-SEMESTRAL')
        vencido = timezone.localdate() - timedelta(days=3)
        for documento in (plan, informe):
            documento.vence_el = vencido
            documento.abre_el = vencido - timedelta(days=30)
            documento.save(update_fields=['vence_el', 'abre_el'])
        evaluar_vencimientos()
        plan.refresh_from_db()
        informe.refresh_from_db()
        self.assertIsNone(plan.evaluacion)
        self.assertIsNotNone(plan.incumplimiento_procesado_hasta)
        self.assertIs(plan.cumple, False)
        self.assertIn('Incumplimiento por no entrega', plan.evaluacion_observacion)
        self.assertEqual(informe.evaluacion, 0)
        self.assertIs(informe.cumple, False)
        # Repetir no vuelve a avisar ni a registrar el mismo incumplimiento.
        registros = RegistroAuditoriaUnidad.objects.filter(unidad=self.laboratorio).count()
        evaluar_vencimientos()
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.laboratorio).count(), registros)


class LosAnexosDicenLoQueContienenTests(BaseDeCumplimiento):
    def test_cada_anexo_y_documento_tiene_una_descripcion_que_dice_como_se_juzga(self):
        for fila in (*CATALOGO, *CATALOGO_PERFILES):
            codigo, descripcion, anexo_de = fila[0], fila[11], fila[12]
            with self.subTest(codigo=codigo):
                self.assertTrue(descripcion.strip(), f'{codigo} sin descripción')
                if anexo_de:
                    self.assertTrue('Respalda' in descripcion or 'meta propia' in descripcion, codigo)
                elif codigo == CODIGO_CALIFICABLE:
                    self.assertIn('único documento que se califica', descripcion)
                else:
                    self.assertIn('Cumplimiento obligatorio', descripcion)

    def test_el_equipamiento_no_repite_el_inventario(self):
        from apps.gestion_unidades.presentation.reportes_condiciones import tablas_condiciones

        inventario = {t['titulo'] if isinstance(t, dict) else t[0]
                      for t in tablas_condiciones('recursos', self.laboratorio, date(2026, 1, 1), date(2026, 6, 30))}
        equipamiento = {t['titulo'] if isinstance(t, dict) else t[0]
                        for t in tablas_condiciones('equipamiento', self.laboratorio, date(2026, 1, 1), date(2026, 6, 30))}
        self.assertTrue(inventario)
        self.assertFalse(inventario & equipamiento)

    def test_la_vista_previa_de_acciones_de_mejora_es_el_documento_que_se_archiva(self):
        anexo = next(d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
                     if d.exigido.codigo == 'ACCIONES-MEJORA' and d.corte == 'A')
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('pdf_borrador_documento_expediente', args=[self.laboratorio.slug, anexo.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
