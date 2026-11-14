"""Inspecciones respaldadas y seguimiento, independientes de la habilitación de acceso."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import (
    inspecciones_documentadas, registrar_evidencia, registros_de_gestion,
)
from apps.reservas.models.seguridad import HabilitacionAcceso


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class InspeccionesDocumentadasLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='inspecciones-responsable')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio inspección QA', slug='inspeccion-qa',
            dependencia='laboratorios', descripcion='Unidad aislada', fecha_inicio=date(2026, 1, 1),
            administrador=cls.actor)

    def setUp(self):
        self.hoy = date(2026, 10, 16)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)
        self.reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)

    def datos(self, codigo='INSPECCION-QA', hallazgos=False):
        detalle = dict(area='Área de impresión QA', condiciones_revisadas=['equipos', 'emergencias'],
            sin_hallazgos=True, hallazgos='', accion_correctiva='', estado_condiciones='seguro',
            estado_accion='no_requiere', plazo_accion='')
        if hallazgos:
            detalle.update(sin_hallazgos=False, hallazgos='Protección de un equipo deteriorada.',
                accion_correctiva='Retirar de uso y reemplazar la protección.', estado_condiciones='no_operar',
                estado_accion='pendiente', plazo_accion='2026-10-20')
        return dict(tipo='INSPECCION', codigo=codigo, fecha=self.hoy,
            titulo='Chequeo de condiciones de operación QA', descripcion='Revisión de equipos y rutas de evacuación.',
            responsable=self.actor, enlace='https://example.org/inspecciones/' + codigo, detalle=detalle)

    def lectura(self):
        return inspecciones_documentadas(self.unidad, self.inicio, self.fin)

    def test_sin_hallazgos_exige_declaracion_explicita_y_soporte(self):
        datos = self.datos()
        datos['detalle']['sin_hallazgos'] = False
        with self.assertRaisesMessage(ValidationError, 'marca explícitamente'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        datos = self.datos()
        datos['enlace'] = ''
        with self.assertRaisesMessage(ValidationError, 'Adjunta un archivo'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True)
        self.assertEqual(self.lectura()['reales'], 1)

    def test_hallazgo_pendiente_exige_accion_responsable_y_plazo(self):
        for clave, valor in [('accion_correctiva', ''), ('plazo_accion', ''),
                             ('plazo_accion', '2026-10-15'), ('estado_accion', 'no_requiere')]:
            datos = self.datos(hallazgos=True)
            datos['detalle'][clave] = valor
            with self.assertRaises(ValidationError):
                registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        registrar_evidencia(self.unidad, self.actor, self.datos(hallazgos=True), verificar=True)
        fila = self.lectura()['filas'][0]
        self.assertEqual((fila['estado_condiciones'], fila['estado_accion'], fila['plazo_accion']),
                         ('no_operar', 'pendiente', '2026-10-20'))

    def test_no_se_puede_ocultar_hallazgo_declarando_revision_segura(self):
        datos = self.datos(hallazgos=True)
        datos['detalle']['estado_condiciones'] = 'seguro'
        with self.assertRaisesMessage(ValidationError, 'Si existen hallazgos'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        datos = self.datos(hallazgos=True)
        datos['detalle']['sin_hallazgos'] = True
        with self.assertRaisesMessage(ValidationError, 'contradictorios'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)

    def test_verificar_chequeo_no_crea_habilitaciones_ni_metas_adicionales(self):
        antes = HabilitacionAcceso.objects.count()
        registrar_evidencia(self.unidad, self.actor, self.datos(), verificar=True)
        self.assertEqual(HabilitacionAcceso.objects.count(), antes)
        registros = registros_de_gestion(self.unidad, self.inicio, self.fin)
        self.assertEqual(registros['gestion_inspeccion'], 1)
        self.assertIn('detalle', registros['fuentes_gestion']['INSPECCION'][0])

    def test_alterar_estado_condiciones_invalida_la_verificacion(self):
        e = registrar_evidencia(self.unidad, self.actor, self.datos(hallazgos=True), verificar=True)
        e.detalle['estado_condiciones'] = 'observado'
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle=e.detalle)
        self.assertEqual(self.lectura()['reales'], 0)
        self.assertEqual(self.lectura()['pendientes'], 1)

    def test_formulario_disponible_sin_actividad_numerica_nueva(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        self.assertContains(self.client.get(ruta, {'anio': 2026, 'corte': 'B', 'tipo': 'INSPECCION'}),
                            'Condiciones revisadas')
        datos = self.datos()
        respuesta = self.client.post(ruta, dict(anio=2026, corte='B', tipo='INSPECCION', codigo=datos['codigo'],
            fecha='2026-10-16', titulo=datos['titulo'], descripcion=datos['descripcion'], responsable=self.actor.pk,
            enlace=datos['enlace'], verificar='on', **datos['detalle']))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.lectura()['reales'], 1)
        self.assertContains(self.client.get(respuesta.url), 'Sin hallazgos declarados')

    def test_inventario_integral_exige_reactivos_e_insumos(self):
        datos = dict(tipo='INVENTARIO', codigo='INVENTARIO-QA', fecha=self.hoy,
            titulo='Revisión integral QA', descripcion='Conciliación del inventario y sus cuatro componentes.',
            responsable=self.actor, enlace='https://example.org/inventario/QA',
            alcance=['equipos', 'software', 'espacios'])
        with self.assertRaisesMessage(ValidationError, 'reactivos e insumos'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        datos['alcance'].append('insumos')
        registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        self.assertEqual(registros_de_gestion(self.unidad, self.inicio, self.fin)['inventarios_verificados'], 1)
