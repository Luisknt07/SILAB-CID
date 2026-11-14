"""La fecha de presentación posterior al cierre no prolonga el período medido."""
from datetime import date, time
from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.template import engines
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.admin.expediente import DocumentoExigidoAdmin
from apps.documentos.models.expediente import DocumentoExigido
from apps.documentos.presentation.cumplimiento import _meta_de


class PlazosCierreInterfazTests(SimpleTestCase):
    def exigido(self, **cambios):
        datos = dict(plazo_regla='cierre', plazo_dias=15, apertura_dias=15,
                     hora_limite=time(23, 59), requiere_firma=True)
        datos.update(cambios)
        return DocumentoExigido(**datos)

    def test_admin_y_resumen_distinguen_cierre_posterior_del_previo(self):
        administrador = DocumentoExigidoAdmin(DocumentoExigido, AdminSite())
        cierre = self.exigido()
        anterior = self.exigido(plazo_regla='fin')
        self.assertIn('15 días después del cierre del semestre de gestión', administrador.plazo(cierre))
        self.assertNotIn('antes del cierre', administrador.plazo(cierre))
        self.assertIn('15 días antes del cierre', administrador.plazo(anterior))
        self.assertEqual(_meta_de(SimpleNamespace(exigido=cierre)),
                         '15 días después del cierre del semestre de gestión · firmado')

    def test_fecha_explicita_conserva_prioridad_en_la_presentacion(self):
        administrador = DocumentoExigidoAdmin(DocumentoExigido, AdminSite())
        exigido = self.exigido(fecha_limite=date(2027, 1, 20))
        self.assertEqual(administrador.plazo(exigido), '20/01/2027 · 23:59')
        self.assertEqual(exigido.fecha_limite, date(2027, 1, 20))
        self.assertEqual(exigido.plazo_dias, 15)

    def test_plazo_explicado_no_confunde_periodo_y_fecha_de_envio(self):
        documento = SimpleNamespace(exigido=self.exigido(), plazo_original=None,
            ultimatum_hasta=None, prorroga_hasta=None, correccion_hasta=None)
        html = render_to_string('portal/pages/unidades/gestion/includes/plazo_documento.html',
                                dict(documento=documento, parte='institucional'))
        self.assertIn('15 días para presentar el informe', html)
        self.assertIn('El período de actividad reportado se conserva', html)
        self.assertNotIn('15 días antes', html)

    def test_libreria_seguimiento_es_descubierta_por_el_motor_de_plantillas(self):
        motor = engines['django'].engine
        self.assertIn('seguimiento_indicadores', motor.template_libraries)
        plantilla = engines['django'].from_string('{% load seguimiento_indicadores %}'
            '{% ficha_meta_conservada indicador as ficha %}{{ ficha.titulo }}')
        html = plantilla.render(dict(indicador=dict(codigo='PRACTICAS', meta='6',
                                                   indicador='Prácticas con respaldo')))
        self.assertIn('Origen y cálculo · Prácticas con respaldo', html)
