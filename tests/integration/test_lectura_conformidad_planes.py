"""Conformidad del archivo actual frente a antecedentes numéricos conservados."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace as Dato

from django.test import SimpleTestCase

from apps.documentos.presentation.conformidad_lectura import lectura_conformidad


class LecturaConformidadPlanesTests(SimpleTestCase):
    def documento(self, **cambios):
        exigido = Dato(codigo='PLAN-COMPRAS-ANUAL', es_anexo=False, requiere_firma=True)
        recurso = Dato(pk=4, activo=True, estado='vigente', version=2, unidad_id=7,
            archivo='plan.pdf', hash_sha256='a' * 64)
        documento = Dato(pk=5, exigido=exigido, unidad_id=7, estado='validado', recurso_id=4,
            recurso=recurso, version=2, firma_verificada=True, evaluacion=None,
            evaluacion_version=None, evaluado_en=None, evaluado_por_id=None, evaluacion_observacion='')
        documento.__dict__.update(cambios)
        return documento

    def aprobacion(self, documento):
        documento._conformidad_plan_registro = Dato(unidad_id=7, usuario_id=8,
            creado_en=datetime(2026, 10, 18, tzinfo=timezone.utc), datos_nuevos=dict(
                version=2, recurso_id=4, sha256='a' * 64, alcance='documental'))

    def test_cero_y_cien_historicos_no_se_convierten_en_confirmacion_actual(self):
        for nota in (0, 80, 100):
            d = self.documento(evaluacion=nota, evaluacion_version=2, evaluado_por_id=8)
            lectura = lectura_conformidad(d)
            self.assertEqual(lectura['estado'], 'pendiente')
            self.assertEqual(lectura['historica']['nota'], nota)
            self.assertEqual(d.evaluacion, nota)

    def test_confirmacion_vinculada_al_archivo_actual_acredita_conformidad(self):
        d = self.documento(evaluacion=100, evaluacion_version=2, evaluado_por_id=8)
        self.aprobacion(d)
        lectura = lectura_conformidad(d, integridad=dict(aplica=True, correspondencia_verificada=True))
        self.assertEqual((lectura['estado'], lectura['fuente'], lectura['historica']), ('conforme', 'Dirección', {}))

    def test_version_archivo_huella_y_unidad_distintos_no_reutilizan_confirmacion(self):
        for campo, valor in [('version', 1), ('recurso_id', 3), ('sha256', 'b' * 64)]:
            d = self.documento()
            self.aprobacion(d)
            d._conformidad_plan_registro.datos_nuevos[campo] = valor
            self.assertEqual(lectura_conformidad(d)['estado'], 'pendiente')
        d._conformidad_plan_registro.unidad_id = 99
        self.assertEqual(lectura_conformidad(d)['estado'], 'pendiente')

    def test_control_sin_aplicacion_o_desactualizado_no_confirma_el_plan(self):
        control = dict(vigente=True, aplicado=True, estado='automatico',
            resumen=dict(conformidad_documental=dict(tipo='compras'), manual_preservada=False))
        d = self.documento()
        self.assertEqual(lectura_conformidad(d, control=control)['estado'], 'conforme')
        for clave in ('vigente', 'aplicado'):
            c = deepcopy(control)
            c[clave] = False
            self.assertEqual(lectura_conformidad(d, control=c)['estado'], 'pendiente')
        control['resumen']['manual_preservada'] = True
        self.assertEqual(lectura_conformidad(d, control=control)['estado'], 'pendiente')

    def test_observado_o_correspondencia_pendiente_no_se_presentan_conformes(self):
        d = self.documento(estado='observado')
        self.aprobacion(d)
        self.assertEqual(lectura_conformidad(d)['estado'], 'corregir')
        d.estado = 'validado'
        self.assertEqual(lectura_conformidad(d, integridad=dict(aplica=True,
            correspondencia_verificada=False))['estado'], 'verificar')

    def test_cierre_conserva_su_resultado_operativo_y_no_usa_conformidad_del_plan(self):
        d = self.documento(evaluacion=80)
        d.exigido.codigo = 'INFORME-SEMESTRAL'
        self.assertIsNone(lectura_conformidad(d))
