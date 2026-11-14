"""Los formularios de presupuesto y reparto respetan ámbito e integridad."""
from copy import deepcopy
from html.parser import HTMLParser
from io import BytesIO
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.documentos.models.asignacion import EscenarioAsignacionNecesidades, MarcoPresupuestoNecesidades
from tests.integration import test_asignacion_necesidades as soporte


class ControlesFormulario(HTMLParser):
    def __init__(self, contenido):
        super().__init__()
        self.controles = {}
        self.feed(contenido)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == 'input' and atributos.get('name'):
            self.controles.setdefault(atributos['name'], []).append(atributos.get('value', ''))


class AsignacionNecesidadesVistasTests(TestCase):
    setUpTestData = classmethod(soporte.AsignacionNecesidadesTests.setUpTestData.__func__)
    remision = soporte.AsignacionNecesidadesTests.remision
    presupuesto = soporte.AsignacionNecesidadesTests.presupuesto
    escenario = soporte.AsignacionNecesidadesTests.escenario

    def lectura(self):
        lectura = soporte.AsignacionNecesidadesTests.lectura(self)
        lectura.update(anio_compras=2027, alcance='Necesidades por dependencia', grupos=[])
        lectura['resumen'].update(con_compras=2, sin_compras=0, pendientes=0)
        return lectura

    def setUp(self):
        self.url = reverse('admin:reportes-necesidades-decanato')
        self.client.force_login(self.direccion)

    def seleccion(self, **extra):
        return dict(ejercicio='2027', dependencia=str(self.dependencia.pk), **extra)

    def test_get_dependencia_sin_presupuesto_renderiza_campos_vacios_sin_escribir(self):
        respuesta = self.client.get(self.url, self.seleccion())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Configurar presupuesto disponible')
        campos = ControlesFormulario(respuesta.content.decode()).controles
        self.assertEqual(campos['disponible'], [''])
        self.assertEqual(campos['concentracion'], [''])
        self.assertNotIn('None', campos['disponible'])
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 0)
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 0)

    def test_get_no_ejecuta_accion_de_registro_ni_toma_importe_de_query(self):
        respuesta = self.client.get(self.url, self.seleccion(accion='presupuesto', disponible='999', referencia='No registrar'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 0)
        self.assertEqual(ControlesFormulario(respuesta.content.decode()).controles['disponible'], [''])

    def test_post_presupuesto_del_receptor_se_limita_a_su_dependencia(self):
        self.client.force_login(self.decanato)
        respuesta = self.client.post(self.url, self.seleccion(accion='presupuesto', disponible='350', referencia='Oficio confirmado', concentracion=''))
        self.assertEqual(respuesta.status_code, 302)
        registro = MarcoPresupuestoNecesidades.objects.get()
        self.assertEqual(registro.dependencia_id, self.dependencia.pk)
        self.assertEqual(registro.contenido['disponible'], '350')
        self.assertIsNone(registro.contenido['porcentaje_maximo_unidad'])
        ajena = self.client.post(self.url, dict(ejercicio='2027', dependencia=self.otra_dependencia.pk,
            accion='presupuesto', disponible='900', referencia='Referencia ajena'))
        self.assertEqual(ajena.status_code, 403)
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 1)

    def test_post_invalido_preserva_vacio_explicito_sin_reponer_importe_anterior(self):
        presupuesto = self.presupuesto(disponible='400', concentracion='50')
        respuesta = self.client.post(self.url, self.seleccion(accion='presupuesto', disponible='', referencia='', concentracion=''))
        self.assertEqual(respuesta.status_code, 200)
        campos = ControlesFormulario(respuesta.content.decode()).controles
        self.assertEqual(campos['disponible'], [''])
        self.assertEqual(campos['concentracion'], [''])
        self.assertContains(respuesta, 'Presupuesto disponible: introduce un valor no negativo')
        presupuesto.refresh_from_db()
        self.assertEqual(presupuesto.contenido['disponible'], '400')
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 1)

    def test_post_sin_csrf_es_rechazado_antes_del_registro(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.direccion)
        respuesta = cliente.post(self.url, self.seleccion(accion='presupuesto', disponible='100', referencia='Oficio'))
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 0)

    def test_post_sin_dependencia_y_acciones_desconocidas_no_crean_registros(self):
        for datos in (dict(ejercicio='2027', accion='presupuesto', disponible='100', referencia='Oficio'),
                      self.seleccion(accion='accion_ajena')):
            with self.subTest(datos=datos):
                self.assertEqual(self.client.post(self.url, datos).status_code, 400)
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 0)

    def test_escenario_renderiza_cantidades_cero_y_preserva_cantidades_tras_error(self):
        remision, presupuesto = self.remision(), self.presupuesto()
        datos = self.seleccion(remision=str(remision.pk))
        respuesta = self.client.get(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        controles = ControlesFormulario(respuesta.content.decode()).controles
        self.assertEqual(controles['cantidad_301:1'], ['0'])
        self.assertEqual(controles['cantidad_302:1'], ['0'])
        datos.update(accion='escenario', presupuesto_id=str(presupuesto.pk), distribucion='Distribuir por fases.',
            excepcion='', **{'cantidad_301:1': '3', 'cantidad_302:1': '1'})
        respuesta = self.client.post(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no puede superar la cantidad solicitada')
        self.assertEqual(ControlesFormulario(respuesta.content.decode()).controles['cantidad_301:1'], ['3'])
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 0)

    def test_post_escenario_usa_fuentes_archivadas_y_get_excel_no_lo_modifica(self):
        remision, presupuesto = self.remision(), self.presupuesto()
        original = deepcopy(remision.contenido)
        datos = self.seleccion(remision=str(remision.pk), accion='escenario', presupuesto_id=str(presupuesto.pk),
            distribucion='Cubrir una unidad de cada fase en ambas unidades.', excepcion='',
            **{'cantidad_301:1': '1', 'cantidad_302:1': '1'})
        with patch('apps.documentos.presentation.asignacion_necesidades._revision_actual',
                   return_value=dict(estado='favorable', label='Cumplimiento acreditado')):
            respuesta = self.client.post(self.url, datos)
        self.assertEqual(respuesta.status_code, 302)
        escenario = EscenarioAsignacionNecesidades.objects.get()
        self.assertEqual(escenario.contenido['total'], '200.00')
        descarga = self.client.get(self.url, self.seleccion(remision=str(remision.pk),
            escenario=str(escenario.pk), formato='escenario-xlsx'))
        self.assertEqual(descarga.status_code, 200)
        libro = load_workbook(BytesIO(descarga.content))
        try:
            self.assertIn('DISTRIBUCION', libro.sheetnames)
        finally:
            libro.close()
        remision.refresh_from_db()
        self.assertEqual(remision.contenido, original)
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 1)

    def test_presupuesto_sustituido_no_se_admite_para_nuevo_escenario(self):
        remision, anterior = self.remision(), self.presupuesto(disponible='300')
        self.presupuesto(disponible='400')
        respuesta = self.client.post(self.url, self.seleccion(remision=str(remision.pk), accion='escenario',
            presupuesto_id=str(anterior.pk), distribucion='Reparto por fases.', **{'cantidad_301:1': '1'}))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'referencia presupuestaria actual')
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 0)

    def test_capturas_corruptas_dan_error_visible_y_no_exportan_escenario(self):
        remision, presupuesto = self.remision(), self.presupuesto()
        escenario = self.escenario(remision, presupuesto)
        # Corrupción deliberada sólo en la base de pruebas; la API ordinaria
        # impide editar capturas archivadas incluso mediante actualización masiva.
        EscenarioAsignacionNecesidades._base_manager.filter(pk=escenario.pk).update(contenido={'total': '999999'})
        datos = self.seleccion(remision=str(remision.pk), escenario=str(escenario.pk))
        respuesta = self.client.get(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no supera la verificación de integridad')
        self.assertNotContains(respuesta, 'Descargar reparto en Excel')
        self.assertEqual(self.client.get(self.url, dict(datos, formato='escenario-xlsx')).status_code, 404)
        MarcoPresupuestoNecesidades._base_manager.filter(pk=presupuesto.pk).update(contenido={'disponible': '999999'})
        respuesta = self.client.get(self.url, self.seleccion(remision=str(remision.pk)))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no supera la verificación de integridad')

    def test_escenario_ajeno_y_permiso_retirado_no_exponen_su_contenido(self):
        remision, presupuesto = self.remision(), self.presupuesto()
        escenario = self.escenario(remision, presupuesto)
        self.client.force_login(self.otro)
        respuesta = self.client.get(self.url, self.seleccion(remision=str(remision.pk), escenario=str(escenario.pk)))
        self.assertEqual(respuesta.status_code, 404)
        self.client.force_login(self.decanato)
        self.dependencia.receptores.remove(self.decanato)
        respuesta = self.client.get(self.url, self.seleccion(remision=str(remision.pk)))
        self.assertEqual(respuesta.status_code, 403)
