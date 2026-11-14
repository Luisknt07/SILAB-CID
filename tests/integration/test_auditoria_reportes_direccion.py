"""Formatos explícitos y actividad del aula coherente entre unidad y Dirección."""
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
from apps.gestion_unidades.admin.reportes import ReporteOperativoUnidadAdmin
from apps.gestion_unidades.models.operaciones import ReporteOperativoUnidad
from apps.gestion_unidades.presentation.exportaciones_reportes import formato_reporte
from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
from apps.gestion_unidades.presentation.reportes_excel import _hoja_de_criterios
from apps.gestion_unidades.presentation.reportes_perfiles import dataset_perfil
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.plantas_piloto.operacion.presentation import trazabilidad


class FormatosDireccionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def solicitud(self, formato):
        request = self.factory.get('/reportes/institucional/', {'formato': formato})
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True, is_staff=False)
        return request

    def test_csv_sigue_admitido_en_reportes_de_unidad_y_no_en_institucional(self):
        request = self.solicitud('csv')
        self.assertEqual(formato_reporte(request), 'csv')
        with self.assertRaises(BadRequest):
            formato_reporte(request, permitir_csv=False)
        for formato in ('', 'pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato):
                self.assertEqual(formato_reporte(self.solicitud(formato), permitir_csv=False), formato)

    def test_institucional_rechaza_csv_antes_de_consultar_o_exportar(self):
        with patch.object(trazabilidad, 'contexto_institucional') as contexto, \
                patch.object(trazabilidad, 'exportar_institucional') as exportar:
            with self.assertRaises(BadRequest):
                trazabilidad.reporte_institucional_view(self.solicitud('csv'))
        contexto.assert_not_called()
        exportar.assert_not_called()
        with patch.object(trazabilidad, 'unidades_reportables') as unidades:
            with self.assertRaises(BadRequest):
                trazabilidad.contexto_institucional(self.solicitud('csv'))
        unidades.assert_not_called()

    def test_institucional_admite_y_conserva_los_tres_formatos_documentales(self):
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato), \
                    patch.object(trazabilidad, 'contexto_institucional', return_value={'alcance': 'unidad propia'}) as contexto, \
                    patch.object(trazabilidad, 'exportar_institucional', return_value=HttpResponse('exportado')) as exportar:
                request = self.solicitud(formato)
                respuesta = trazabilidad.reporte_institucional_view(request)
                self.assertEqual(respuesta.status_code, 200)
                contexto.assert_called_once_with(request)
                exportar.assert_called_once_with({'alcance': 'unidad propia'}, formato, False)

    def test_direccion_rechaza_csv_sin_invocar_el_consolidado(self):
        modelo_admin = ReporteOperativoUnidadAdmin(ReporteOperativoUnidad, admin.site)
        with patch.object(modelo_admin, 'has_view_permission', return_value=True), \
                patch.object(trazabilidad, 'contexto_institucional') as contexto:
            with self.assertRaises(BadRequest):
                modelo_admin.reporte_institucional(self.solicitud('csv'))
        contexto.assert_not_called()


class LimitesReportesPerfilesTests(SimpleTestCase):
    def test_serie_con_mas_de_500_datos_declara_el_limite_en_dataset_y_excel(self):
        inicio, fin = date(2026, 3, 1), date(2026, 3, 10)
        registrado = timezone.make_aware(datetime.combine(fin, time(12)))
        unidad = SimpleNamespace(pk=1, slug='observatorio-qa', nombre='Observatorio QA')
        for numero in (500, 501):
            valores = [SimpleNamespace(pk=i, fecha=fin, periodo='2026-03', territorio='Territorio QA',
                valor=i, provisional=False, nota='Referencia QA', registrado=registrado) for i in range(numero)]
            indicador = SimpleNamespace(pk=3, codigo='SERIE-QA', nombre='Serie de prueba',
                periodicidad='mensual', unidad_medida='personas', fuente='Fuente registrada',
                publicado=True, definicion='Definición registrada', formula='Conteo', desagregacion='Territorio',
                url_fuente='', limitaciones='', get_periodicidad_display=lambda: 'Mensual',
                valores=SimpleNamespace(all=lambda: valores))
            with self.subTest(numero=numero), \
                    patch('apps.gestion_unidades.presentation.reportes_perfiles.habilitada', return_value=False), \
                    patch('apps.gestion_unidades.presentation.reportes_perfiles.base_perfil', return_value='observatorios'), \
                    patch('apps.gestion_unidades.presentation.reportes_perfiles.EvidenciaGestionUnidad.objects') as evidencias, \
                    patch('apps.observatorios.operacion.models.observatorios.IndicadorObservatorio.objects') as indicadores:
                evidencias.filter.return_value.select_related.return_value = []
                indicadores.filter.return_value.prefetch_related.return_value = [indicador]
                dataset = dataset_perfil('datos-observatorio', unidad, inicio, fin)
            tabla = next(t for t in dataset['tablas'] if t['titulo'] == 'Datos incorporados durante el semestre')
            self.assertEqual(dataset['rows'][0][4], numero)
            self.assertEqual(len(tabla['rows']), 500)
            self.assertEqual(tabla['total'], numero)
            self.assertEqual(tabla['truncated'], numero > 500)
            self.assertEqual(dataset['truncated'], numero > 500)
            self.assertEqual(len(valores), numero)
            reporte = dict(unit=unidad, category_label='Datos del observatorio', filter_summary=[],
                generated_at=registrado, is_generic=True, metrics={}, dataset=dataset,
                detail_truncated=dataset['truncated'])
            criterios = _hoja_de_criterios(reporte)[3]
            aviso = ' '.join(valor for etiqueta, valor in criterios if etiqueta == 'Alcance del detalle')
            if numero > 500:
                self.assertIn('Datos incorporados durante el semestre', aviso)
                self.assertIn('500 de 501 registros', aviso)
                self.assertNotIn('primeros 1 registros', aviso)
            else:
                self.assertEqual(aviso, '')


class ActividadAulaDireccionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.desde, cls.hasta = date(2026, 3, 1), date(2026, 3, 10)
        cls.usuario = get_user_model().objects.create_user('direccion-actividad-aula-qa')
        cls.otro = get_user_model().objects.create_user('segunda-participacion-aula-qa')
        cls.unidad = Unidad.objects.create(nombre='Unidad aula para Dirección', slug='aula-direccion-qa',
            dependencia='laboratorios', fecha_inicio=cls.desde, administrador=cls.usuario)
        cls.ajena = Unidad.objects.create(nombre='Otra unidad de aula', slug='aula-ajena-direccion-qa',
            dependencia='laboratorios', fecha_inicio=cls.desde)
        cls.producto = Producto.objects.create(unidad=cls.unidad, codigo='AULA-DIR-P', nombre='Producto', unidad_medida='kg')
        cls.receta = Receta.objects.create(unidad=cls.unidad, producto=cls.producto, codigo='AULA-DIR-R',
            nombre='Proceso', cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        producto_ajeno = Producto.objects.create(unidad=cls.ajena, codigo='AULA-DIR-A-P', nombre='Producto ajeno', unidad_medida='kg')
        cls.receta_ajena = Receta.objects.create(unidad=cls.ajena, producto=producto_ajeno, codigo='AULA-DIR-A-R',
            nombre='Proceso ajeno', cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)

    def momento(self, dia):
        return timezone.make_aware(datetime.combine(dia, time(12)))

    def intento(self, nombre, *, unidad=None, estado='asignado', entregado=None, calificado=None, creado=None):
        unidad = unidad or self.unidad
        ejercicio = EjercicioAula.objects.create(unidad=unidad,
            receta=self.receta if unidad.pk == self.unidad.pk else self.receta_ajena, nombre=nombre)
        intento = IntentoEjercicio.objects.create(ejercicio=ejercicio, estudiante=self.usuario, estado=estado,
            entregado_en=self.momento(entregado) if entregado else None,
            calificado_en=self.momento(calificado) if calificado else None)
        IntentoEjercicio.objects.filter(pk=intento.pk).update(creado_en=self.momento(creado or self.desde - timedelta(days=1)))
        return ejercicio

    def test_intentos_anteriores_entregados_o_calificados_ahora_cuentan_sin_duplicar_ejercicio(self):
        entregado = self.intento('Entregado durante el período', estado='entregado', entregado=self.desde)
        self.intento('Calificado durante el período', estado='calificado', calificado=self.hasta)
        self.intento('Asignado durante el período', creado=self.desde)
        self.intento('Fuera del período')
        self.intento('Actividad ajena', unidad=self.ajena, creado=self.desde)
        segundo = IntentoEjercicio.objects.create(ejercicio=entregado, estudiante=self.otro,
            estado='entregado', entregado_en=self.momento(self.hasta))
        IntentoEjercicio.objects.filter(pk=segundo.pk).update(creado_en=self.momento(self.desde - timedelta(days=2)))
        detalle = _generic_report('aula', self.unidad, self.desde, self.hasta)
        consolidado = trazabilidad.consolidado_institucional(self.usuario, self.desde, self.hasta,
            unidades=[self.unidad])
        self.assertEqual(detalle['cards'][0], ('Ejercicios', 3))
        self.assertEqual(len(detalle['rows']), 4)
        self.assertEqual(consolidado['totales']['ejercicios'], 3)
        self.assertEqual(consolidado['totales']['entregas'], 1)
        self.assertEqual([f['unidad'].pk for f in consolidado['filas']], [self.unidad.pk])

    def test_ultimo_instante_se_incluye_y_el_dia_siguiente_no_es_actividad_del_periodo(self):
        limite = self.intento('Actividad en el límite', estado='entregado', entregado=self.hasta)
        posterior = self.intento('Actividad posterior', estado='entregado', entregado=self.hasta + timedelta(days=1))
        IntentoEjercicio.objects.filter(ejercicio=limite).update(entregado_en=timezone.make_aware(
            datetime.combine(self.hasta, time.max)))
        IntentoEjercicio.objects.filter(ejercicio=posterior).update(entregado_en=timezone.make_aware(
            datetime.combine(self.hasta + timedelta(days=1), time.min)))
        datos = trazabilidad.consolidado_institucional(self.usuario, self.desde, self.hasta,
            unidades=[self.unidad])['totales']
        self.assertEqual(datos['ejercicios'], 1)
