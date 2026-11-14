"""Un resultado acredita productos comprobables; el uso del laboratorio es otro dato."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import (
    registrar_evidencia, rectificar_evidencia, registros_de_gestion, resultados_documentados,
)


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class ResultadosDocumentadosLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='resultados-responsable')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de resultados QA', slug='resultados-qa',
            dependencia='laboratorios', descripcion='Unidad aislada de pruebas',
            fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Otra unidad QA', slug='otra-resultados-qa',
            dependencia='laboratorios', descripcion='Unidad aislada', fecha_inicio=date(2026, 1, 1))

    def setUp(self):
        self.hoy = date(2026, 10, 16)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)
        self.reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)

    def datos(self, tipo='INVESTIGACION', codigo='RESULTADO-QA'):
        detalle = dict(proyecto='Proyecto QA de materiales', tipo_producto='informe',
                       producto='Informe de validación experimental QA', beneficiario='Comunidad universitaria QA')
        if tipo == 'TRANSFERENCIA':
            detalle.update(aceptacion='aceptado', fecha_aceptacion='2026-10-15',
                           referencia_aceptacion='Acta de entrega y aceptación QA-1')
        return dict(tipo=tipo, codigo=codigo, fecha=self.hoy,
                    titulo='Producto verificable QA', descripcion='Resultado experimental y conclusiones comprobadas.',
                    responsable=self.actor, enlace='https://example.org/resultados/' + codigo, detalle=detalle)

    def lectura(self, tipo='INVESTIGACION'):
        return resultados_documentados(self.unidad, self.inicio, self.fin, tipo)

    def test_reserva_o_descripcion_generica_no_acreditan_un_resultado(self):
        datos = self.datos()
        datos['detalle'] = {}
        with self.assertRaisesMessage(ValidationError, 'producto'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        e = registrar_evidencia(self.unidad, self.actor, datos, verificar=False)
        self.assertEqual(self.lectura()['reales'], 0)
        self.assertEqual(self.lectura()['pendientes'], 1)
        self.assertEqual(self.lectura()['filas'][0]['pk'], e.pk)

    def test_producto_verificado_con_soporte_suma_y_separa_demostracion(self):
        registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True)
        with override_settings(MEDICION_SOLO_DEMO=True):
            registrar_evidencia(self.unidad, self.actor, self.datos(codigo='DEMO-QA'), verificar=True)
        lectura = self.lectura()
        self.assertEqual((lectura['verificados'], lectura['reales'], lectura['demostracion']), (2, 1, 1))
        registros = registros_de_gestion(self.unidad, self.inicio, self.fin)
        self.assertEqual((registros['resultados_verificados'], registros['resultados_reales']), (2, 1))
        self.assertTrue(registros['evidencias_demo'])
        self.assertIn('contenido_sha256', registros['fuentes_gestion']['INVESTIGACION'][0])

    def test_transferencia_requiere_aceptacion_fecha_y_referencia(self):
        for clave, valor in [('aceptacion', 'pendiente'), ('fecha_aceptacion', '2026-10-17'),
                             ('referencia_aceptacion', '')]:
            datos = self.datos('TRANSFERENCIA')
            datos['detalle'][clave] = valor
            with self.assertRaises(ValidationError):
                registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        registrar_evidencia(self.unidad, self.actor, self.datos('TRANSFERENCIA'), verificar=True)
        self.assertEqual(self.lectura('TRANSFERENCIA')['reales'], 1)
        self.assertEqual(self.lectura()['reales'], 0)

    def test_tocar_producto_o_resultado_invalida_la_verificacion_anterior(self):
        e = registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True)
        original = dict(e.detalle)
        e.detalle['producto'] = 'Producto diferente'
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle=e.detalle)
        self.assertEqual(self.lectura()['reales'], 0)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle=original, descripcion='Texto sustituido')
        self.assertEqual(self.lectura()['reales'], 0)

    def test_fuente_legacy_sin_detalle_no_acredita_y_rectificar_preserva_historial(self):
        e = registrar_evidencia(self.unidad, self.actor, self.datos('TRANSFERENCIA'), verificar=True)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle={})
        self.assertEqual(self.lectura('TRANSFERENCIA')['reales'], 0)
        rectificar_evidencia(self.unidad, self.actor, e.pk, 'Falta identificación de entregable')
        self.assertEqual(self.lectura('TRANSFERENCIA')['pendientes'], 0)
        self.assertEqual(self.lectura('TRANSFERENCIA')['filas'][0]['estado_display'], 'Rectificado')

    def test_resultado_ajeno_o_fuera_del_periodo_no_se_mezcla(self):
        e = registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(unidad=self.otra)
        self.assertEqual(self.lectura()['registrados'], 0)
        self.assertEqual(resultados_documentados(self.otra, self.inicio, self.fin, 'INVESTIGACION')['reales'], 0)

    def test_formulario_guarda_campos_y_rechaza_transferencia_sin_aceptacion(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        datos = self.datos()
        respuesta = self.client.post(ruta, dict(anio=2026, corte='B', tipo=datos['tipo'], codigo=datos['codigo'],
            fecha='2026-10-16', titulo=datos['titulo'], descripcion=datos['descripcion'],
            responsable=self.actor.pk, enlace=datos['enlace'], verificar='on', **datos['detalle']))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.lectura()['reales'], 1)
        datos = self.datos('TRANSFERENCIA', 'SERVICIO-QA')
        datos['detalle']['aceptacion'] = 'pendiente'
        respuesta = self.client.post(ruta, dict(anio=2026, corte='B', tipo=datos['tipo'], codigo=datos['codigo'],
            fecha='2026-10-16', titulo=datos['titulo'], descripcion=datos['descripcion'],
            responsable=self.actor.pk, enlace=datos['enlace'], verificar='on', **datos['detalle']))
        self.assertContains(respuesta, 'debe existir aceptación')
        self.assertEqual(self.lectura('TRANSFERENCIA')['registrados'], 0)
