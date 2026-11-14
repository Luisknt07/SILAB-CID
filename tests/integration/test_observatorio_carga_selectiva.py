"""La consola consulta la sección activa y conserva totales sin cargar series completas."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.observatorios.operacion.presentation.gestion_observatorio import contexto_gestion_observatorio
from apps.observatorios.operacion.presentation.observatorio import cumplimiento
from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio, PublicacionObservatorio, SolicitudDatos, ValorIndicador
from apps.directorio_unidades.models.core import Unidad


class CargaSelectivaObservatorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obs = Unidad.objects.create(nombre='Observatorio selectivo', descripcion='Datos propios',
            fecha_inicio=date(2026, 1, 1), slug='observatorio-selectivo', dependencia='observatorios',
            clasificacion_funcional='observatorio')
        cls.otro = Unidad.objects.create(nombre='Otro observatorio', descripcion='Datos ajenos',
            fecha_inicio=date(2026, 1, 1), slug='observatorio-otro-selectivo', dependencia='observatorios',
            clasificacion_funcional='observatorio')
        cls.user = get_user_model().objects.create_superuser('obs-selectivo', 'obs@example.org', 'prueba')
        cls.indicador = IndicadorObservatorio.objects.create(unidad=cls.obs, codigo='principal',
            nombre='Indicador principal', definicion='Indicador', unidad_medida='%', fuente='Registro',
            periodicidad='mensual', territorio_principal='Carchi')

    def test_otra_seccion_no_consulta_datos_cientificos(self):
        with self.assertNumQueries(0):
            self.assertEqual(contexto_gestion_observatorio(self.obs, vista='configuracion'), {})

    def test_indicadores_resumen_ultimo_territorio_sin_cargar_historico(self):
        hoy = timezone.localdate()
        ValorIndicador.objects.create(indicador=self.indicador, fecha=hoy-timedelta(days=1),
            periodo='Último propio', territorio='Carchi', valor=Decimal('1'))
        ValorIndicador.objects.create(indicador=self.indicador, fecha=hoy,
            periodo='Otro territorio', territorio='Pichincha', valor=Decimal('99'))
        with CaptureQueriesContext(connection) as antes:
            inicial = contexto_gestion_observatorio(self.obs, vista='obs_indicadores')
        ValorIndicador.objects.bulk_create([ValorIndicador(indicador=self.indicador,
            fecha=hoy-timedelta(days=i+2), periodo=str(i), territorio='Carchi', valor=Decimal('2')) for i in range(500)])
        with CaptureQueriesContext(connection) as despues:
            contexto = contexto_gestion_observatorio(self.obs, vista='obs_indicadores')
        self.assertEqual(len(antes), len(despues))
        self.assertEqual(contexto['obs_filas'][0]['ultimo'].periodo, 'Último propio')
        self.assertEqual(contexto['obs_filas'][0]['estado'], 'al_dia')
        self.assertEqual(contexto['obs_filas'][0]['valores'], 502)
        self.assertEqual(inicial['obs_totales'], contexto['obs_totales'])
        self.assertFalse(any('webcitt_solicituddatos' in q['sql'] or 'webcitt_publicacionobservatorio' in q['sql'] for q in despues))

    def test_paginacion_indicadores_con_totales_globales_y_aislamiento(self):
        IndicadorObservatorio.objects.bulk_create([IndicadorObservatorio(unidad=self.obs, codigo=f'i-{i}',
            nombre=f'Indicador {i:02d}', definicion='D', unidad_medida='%', fuente='R') for i in range(29)])
        IndicadorObservatorio.objects.create(unidad=self.otro, codigo='ajeno', nombre='Ajeno',
            definicion='D', unidad_medida='%', fuente='R')
        contexto = contexto_gestion_observatorio(self.obs, vista='obs_indicadores', pagina=2)
        self.assertEqual(contexto['obs_totales']['indicadores'], 30)
        self.assertEqual(contexto['obs_totales']['sin_datos'], 30)
        self.assertEqual(len(contexto['obs_filas']), 5)
        self.assertEqual(contexto['obs_pagina'].number, 2)
        self.assertTrue(all(f['indicador'].unidad_id == self.obs.pk for f in contexto['obs_filas']))

    def test_solicitudes_totales_y_promedio_son_del_conjunto_no_solo_la_pagina(self):
        ahora = timezone.now()
        for i in range(30):
            solicitud = SolicitudDatos.objects.create(unidad=self.obs, usuario=self.user,
                descripcion=f'Solicitud {i}', finalidad='Investigación',
                estado='atendida' if i < 2 else 'recibida',
                atendida=ahora + timedelta(days=1 if i == 0 else 3) if i < 2 else None)
            SolicitudDatos.objects.filter(pk=solicitud.pk).update(creada=ahora)
        SolicitudDatos.objects.create(unidad=self.otro, usuario=self.user, descripcion='Ajena', finalidad='Ajena')
        with CaptureQueriesContext(connection) as captura:
            contexto = contexto_gestion_observatorio(self.obs, vista='obs_solicitudes', pagina=2)
            filas = list(contexto['obs_solicitudes'])
        self.assertEqual(contexto['obs_solicitudes_total'], 30)
        self.assertEqual(contexto['obs_solicitudes_abiertas'], 28)
        self.assertEqual(contexto['obs_dias_atencion'], 2)
        self.assertEqual(len(filas), 5)
        self.assertTrue(all(f.unidad_id == self.obs.pk for f in filas))
        self.assertFalse(any('webcitt_valorindicador' in q['sql'] or 'webcitt_publicacionobservatorio' in q['sql'] for q in captura))

    def test_cumplimiento_agregado_conserva_reglas_y_excluye_canceladas(self):
        hoy = timezone.localdate()
        for estado, publicada in [('publicada', hoy-timedelta(days=2)), ('publicada', hoy),
                                   ('planificada', None), ('cancelada', None)]:
            PublicacionObservatorio.objects.create(unidad=self.obs, titulo=estado,
                fecha_planificada=hoy-timedelta(days=1), fecha_publicada=publicada, estado=estado)
        with self.assertNumQueries(1):
            resumen = cumplimiento(self.obs)
        self.assertEqual(resumen, {'vencidas': 3, 'cumplidas': 2, 'a_tiempo': 1, 'porcentaje': 67})

    def test_publicaciones_no_consulta_series_ni_solicitudes(self):
        with CaptureQueriesContext(connection) as captura:
            contexto = contexto_gestion_observatorio(self.obs, vista='obs_publicaciones')
            list(contexto['obs_proximas'])
            list(contexto['obs_atrasadas'])
            list(contexto['obs_publicadas'])
        self.assertFalse(any('webcitt_valorindicador' in q['sql'] or 'webcitt_solicituddatos' in q['sql'] for q in captura))

    def test_cada_pestana_renderiza_un_solo_panel(self):
        self.client.force_login(self.user)
        for vista in ('obs_indicadores', 'obs_publicaciones', 'obs_solicitudes', 'configuracion'):
            with self.subTest(vista=vista):
                respuesta = self.client.get(reverse('gestion_unidad', args=[self.obs.slug]), {'view': vista})
                self.assertEqual(respuesta.status_code, 200)
                html = respuesta.content.decode()
                self.assertEqual(html.count('data-management-view='), 1)
                self.assertIn(f'data-management-view="{vista}"', html)
