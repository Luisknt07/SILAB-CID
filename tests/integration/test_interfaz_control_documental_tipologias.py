"""Las cuatro tipologías pueden confirmar archivos y consultar sus controles desde la misma interfaz."""
from datetime import date
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
from tests.integration import test_automatizacion_documental_interfaz as interfaz_fixture
from tests.integration import test_contexto_reportes_consola as consola_fixture


TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')


class InterfazControlDocumentalTipologiasTests(SimpleTestCase):
    def documento(self, tipo):
        unidad = SimpleNamespace(pk=3, dependencia=tipo, codigo_base=tipo, slug='qa-' + tipo,
            nombre='QA ' + tipo, administrador=None, adscrita_a=None)
        return SimpleNamespace(pk=7, unidad_id=3, unidad=unidad, version=2,
            nombre_documental='Documento QA', etiqueta_corte='Período 2026-B', anio=2026,
            corte='B', mes=None, estado='cargado', recurso_id=12,
            recurso=SimpleNamespace(pk=12, hash_sha256='a' * 64),
            firma_pendiente=False, firma_verificada=True, vencido=False, nota=80,
            exigido=SimpleNamespace(codigo='RESOLUCION-CREACION', cargable=True,
                generable=False, redactable=False, requiere_firma=False),
            integridad_documental=dict(aplica=True, correspondencia_verificada=False,
                aviso='Correspondencia pendiente de comprobación.'))

    def test_formulario_de_carga_envia_checkbox_e_identidad_en_las_cuatro_tipologias(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                d = self.documento(tipo)
                d.estado, d.recurso, d.recurso_id = 'pendiente', None, None
                html = render_to_string('portal/pages/unidades/gestion/includes/expediente_archivo.html',
                    dict(documento=d, unidad=d.unidad, anio=2026, corte='B'))
                self.assertIn('name="correspondencia_confirmada" value="1" required', html)
                for campo, valor in (('unidad_id', 3), ('documento_id', 7),
                        ('codigo', 'RESOLUCION-CREACION'), ('anio', 2026), ('corte', 'B'), ('version', 2)):
                    self.assertIn(f'name="correspondencia_{campo}" value="{valor}"', html)
                self.assertIn('name="enviar" value="1"', html)

    def test_revision_director_conserva_checkbox_y_criterios_para_los_cuatro_tipos(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                d = self.documento(tipo)
                d.estado = 'validado'
                html = render_to_string('admin/gestion_unidades/reporteoperativounidad/revision.html', dict(
                    revision=dict(documento=d, evaluable=True, cierre=None, penalizacion=0, minimo=70,
                        criterios=[dict(nombre='Calidad del respaldo', peso=25, exige='Contrastar el documento.',
                            clave='criterio_1', sugerencia=None)], niveles=[(80, 'Adecuado')]),
                    user=SimpleNamespace(is_superuser=True)))
                self.assertIn('name="correspondencia_confirmada"', html)
                self.assertIn('Calidad del respaldo', html)
                self.assertIn('Comprobaciones automáticas y pendientes', html)
                self.assertIn('Esta comprobación no sustituye la evaluación de calidad.', html)

    def test_resumen_identifica_alcance_comun_y_correspondencia_pendiente(self):
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                d = interfaz_fixture.AutomatizacionDocumentalInterfazTests().documento()
                d.unidad = self.documento(tipo).unidad
                d.integridad_documental = dict(aplica=True, correspondencia_verificada=False)
                lectura = resumen_de_entrega(d)
                self.assertTrue(lectura['control_documental'])
                self.assertEqual(lectura['laboratorio'], tipo == 'laboratorios')
                self.assertIn('comprobar correspondencia', lectura['siguiente_paso'])

    def test_consola_muestra_resumen_y_accion_automatica_para_cada_tipo(self):
        plantilla = 'portal/pages/unidades/gestion/includes/expediente_cuerpo.html'
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                html = render_to_string(plantilla, dict(unidad=self.documento(tipo).unidad,
                    anio=2026, anios=[2026], corte='B', rango_periodo=(date(2026, 8, 17), date(2026, 12, 8)),
                    automatizacion_resumen=dict(total=8, automatico=2, pendientes_unidad=3,
                        pendientes_direccion=1, revisados_humano=2, sin_analizar=0)))
                self.assertIn('name="accion" value="automatizar"', html)
                self.assertIn('Comprobar y validar automáticamente', html)
                self.assertIn('<b>3</b> pendientes de la unidad', html)
                self.assertIn('<b>1</b> pendientes de Dirección', html)
                self.assertIn('<th scope="col">Observaciones</th>', html)

    def test_otro_tipo_no_recibe_formulario_de_correspondencia_ajeno(self):
        d = self.documento('centros_id')
        html = render_to_string('portal/pages/unidades/gestion/includes/correspondencia_documental.html', dict(d=d))
        self.assertNotIn('name="correspondencia_confirmada"', html)

    def test_consola_sigue_pasando_su_contexto_anidado(self):
        html = consola_fixture.ContextoReportesConsolaTests().renderizar()
        self.assertIn('<b>3</b> controles correctos', html)
