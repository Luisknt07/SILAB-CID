"""Escala de genealogía y fechas explícitas en el consolidado."""
from datetime import datetime, time, timedelta
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.plantas_piloto.operacion.presentation.trazabilidad import _consumos_de_la_orden, consolidado_institucional
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad, PlanCalidad
from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
from apps.plantas_piloto.operacion.models.planificacion import EntregaPedido, PedidoAbastecimiento
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, OrdenProduccion, Producto, Receta
from tests.integration.test_reportes_evidencias import BaseDeReportes


class TrazabilidadEscalaTests(BaseDeReportes):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.producto = Producto.objects.create(unidad=cls.unidad, codigo='QA-TRAZA-P', nombre='Producto', unidad_medida='kg')
        cls.receta = Receta.objects.create(unidad=cls.unidad, producto=cls.producto,
            codigo='QA-TRAZA-R', nombre='Proceso', cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        cls.orden = OrdenProduccion.objects.create(unidad=cls.unidad, receta=cls.receta,
            producto=cls.producto, fecha_inicio=cls.desde, fecha_fin=cls.hasta, estado='terminada')
        cls.insumo = Consumible.objects.create(unidad=cls.unidad, nombre='Insumo trazable', codigo='QA-TRAZA-I')
        cls.lote = LoteConsumible.objects.create(consumible=cls.insumo, codigo='QA-TRAZA-L', cantidad_inicial=100, cantidad_actual=50, bodega='Bodega QA')
        cls.plan = PlanCalidad.objects.create(unidad=cls.unidad, codigo='QA-TRAZA-C', nombre='Recepción')

    def test_consumos_no_consultan_por_fila_y_conservan_entrega_y_ultimo_control(self):
        pedido = PedidoAbastecimiento.objects.create(unidad=self.unidad, consumible=self.insumo,
            cantidad=100, fecha_entrega_prevista=self.desde)
        entrada = EntradaInventario.objects.bulk_create([EntradaInventario(unidad=self.unidad,
            consumible=self.insumo, lote_inventario=self.lote, tipo='ingreso', cantidad=100)])[0]
        EntregaPedido.objects.create(pedido=pedido, entrada=entrada, fecha=self.hasta, cantidad=50)
        primera = EntregaPedido.objects.create(pedido=pedido, entrada=entrada, fecha=self.desde, cantidad=50)
        momento = timezone.make_aware(datetime.combine(self.desde, time(12)))
        ControlCalidad.objects.create(unidad=self.unidad, plan=self.plan, lote_consumible=self.lote, fecha=momento)
        ultimo = ControlCalidad.objects.create(unidad=self.unidad, plan=self.plan, lote_consumible=self.lote,
            fecha=momento + timedelta(hours=1), resultado='no_conforme')
        EntradaInventario.objects.bulk_create([EntradaInventario(unidad=self.unidad,
            consumible=self.insumo, lote_inventario=self.lote, tipo='salida', cantidad=1,
            clave_idempotencia=f'orden-produccion-{self.orden.pk}-QA-{i}') for i in range(40)])
        with CaptureQueriesContext(connection) as consultas:
            filas = _consumos_de_la_orden(self.orden)
            datos = [(f['entrega'].pk, f['pedido'].codigo, f['control'].pk,
                      f['control'].plan.nombre, f['consumible'].nombre) for f in filas]
        self.assertEqual(len(filas), 40)
        self.assertLessEqual(len(consultas), 3, f'{len(consultas)} consultas para 40 consumos')
        self.assertTrue(all(f[0] == primera.pk and f[2] == ultimo.pk for f in datos))

    def test_salida_sin_lote_no_hereda_pedido_ni_control(self):
        EntradaInventario.objects.bulk_create([EntradaInventario(unidad=self.unidad,
            consumible=self.insumo, tipo='salida', cantidad=1,
            clave_idempotencia=f'orden-produccion-{self.orden.pk}-sin-lote')])
        with CaptureQueriesContext(connection) as consultas:
            fila = _consumos_de_la_orden(self.orden)[0]
        self.assertEqual(len(consultas), 1)
        self.assertIsNone(fila['lote'])
        self.assertIsNone(fila['entrega'])
        self.assertIsNone(fila['control'])

    def test_no_conformidad_solo_vinculada_a_control_demostrativo_no_es_operativa(self):
        # El modelo permite enlazar el control sin repetir su lote en el hallazgo.
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(demostrativa=True)
        lote = LoteProducto.objects.create(unidad=self.unidad, producto=self.producto, orden=self.orden,
            codigo='QA-TRAZA-DEMO', cantidad_inicial=1, fecha_produccion=self.desde, demostrativo=True)
        control = ControlCalidad.objects.create(unidad=self.unidad, plan=self.plan, lote_producto=lote)
        hallazgo = NoConformidad.objects.create(unidad=self.unidad, control=control,
            descripcion='Hallazgo docente vinculado únicamente al control')
        operativo = NoConformidad.objects.create(unidad=self.unidad, descripcion='Hallazgo operativo independiente')
        self.assertFalse(NoConformidad.objects.reales().filter(pk=hallazgo.pk).exists())
        self.assertTrue(NoConformidad.objects.reales().filter(pk=operativo.pk).exists())
        cifras = consolidado_institucional(self.coordinador, self.desde, self.hasta, unidades=[self.unidad])['totales']
        self.assertEqual(cifras['no_conformidades'], 1)
        self.assertEqual(NoConformidad.objects.count(), 2)

    def test_produccion_y_aula_declaran_sus_fechas_en_pantalla_y_documentos(self):
        # Una corrida iniciada antes puede producir lotes dentro del período.
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(fecha_inicio=self.desde-timedelta(days=1))
        LoteProducto.objects.create(unidad=self.unidad, producto=self.producto, orden=self.orden,
            codigo='QA-TRAZA-PRD', cantidad_inicial=1, fecha_produccion=self.desde)
        ejercicio = EjercicioAula.objects.create(unidad=self.unidad, receta=self.receta, nombre='Ejercicio anterior')
        anterior = timezone.make_aware(datetime.combine(self.desde-timedelta(days=1), time(12)))
        dentro = timezone.make_aware(datetime.combine(self.desde, time(12)))
        EjercicioAula.objects.filter(pk=ejercicio.pk).update(creado_en=anterior)
        intento = IntentoEjercicio.objects.create(ejercicio=ejercicio, estudiante=self.coordinador,
            estado='calificado', calificado_en=dentro)
        IntentoEjercicio.objects.filter(pk=intento.pk).update(creado_en=dentro)
        cifras = consolidado_institucional(self.coordinador, self.desde, self.hasta, unidades=[self.unidad])['totales']
        self.assertEqual((cifras['corridas'], cifras['lotes'], cifras['ejercicios'], cifras['entregas']), (0, 1, 1, 1))
        url = reverse('reporte_institucional')
        filtros = {'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()}
        pagina = self.client.get(url, filtros)
        self.assertContains(pagina, 'Ejercicios con actividad')
        criterios = ['Producción: corridas terminadas iniciadas en el período; lotes por fecha de producción.',
                     'Aula: ejercicios con intentos asignados, entregados o calificados en el período; entregas por fecha de calificación.']
        for criterio in criterios:
            self.assertContains(pagina, criterio)
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato):
                salida = self.client.get(url, {**filtros, 'formato': formato})
                self.assertEqual(salida.status_code, 200)
                if formato == 'xlsx':
                    libro = load_workbook(BytesIO(salida.content), data_only=True)
                    texto = ' '.join(str(celda) for hoja in libro for fila in hoja.values for celda in fila if celda is not None)
                elif formato == 'docx':
                    with ZipFile(BytesIO(salida.content)) as paquete:
                        texto = ''.join(ET.fromstring(paquete.read('word/document.xml')).itertext())
                else:
                    import pymupdf
                    with pymupdf.open(stream=salida.content, filetype='pdf') as pdf:
                        texto = ' '.join(''.join(p.get_text() for p in pdf).split())
                self.assertIn('Ejercicios con actividad', texto)
                for criterio in criterios:
                    self.assertIn(criterio, texto)
