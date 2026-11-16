"""Contenido de los anexos propios de la planta piloto, el centro experimental y el observatorio.

Fija lo acordado en docs/estructura-anexos-por-tipo-de-unidad.md, sección 5:
- cada tipo de unidad lleva solo sus anexos propios, con las tablas y columnas de la especificación;
- planta piloto: la producción real con sus corridas demostrativas marcadas, sus consumos y salidas;
  el control de calidad con la liberación de los lotes, las no conformidades y sus acciones;
- centro experimental: un ciclo marcado como ensayo va en el anexo de ensayos y no en el de
  producción agropecuaria, y al revés;
- observatorio: la ficha y la actualización de cada serie, los valores del semestre agrupados por
  indicador, sus fuentes, el calendario de publicaciones y los eventos de socialización;
- la revisión técnica es la evidencia verificada que mide el informe; lo anulado no se presenta.
"""
from datetime import date, datetime
from datetime import timezone as zona
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, RegistroProduccion
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import Enlace, Grupo, Par, constructor_de, contexto_del_anexo
from apps.documentos.presentation.anexos_propios import codigo_de_ensayo
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.observatorios.operacion.models.observatorios import (
    FuenteDatos, IndicadorObservatorio, PublicacionObservatorio, ValorIndicador,
)
from apps.plantas_piloto.operacion.models.calidad import (
    AccionCorrectiva, ControlCalidad, MedicionCalidad, NoConformidad, ParametroCalidad, PlanCalidad,
)
from apps.plantas_piloto.operacion.models.produccion import (
    LoteProducto, MovimientoProducto, OrdenProduccion, Producto, Receta,
)
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible

# Las tablas de cada anexo propio y sus columnas, tal como las fija la especificación.
TABLAS = {
    'PP-PRODUCCION': [
        ('Órdenes de producción',
         ('Orden', 'Producto / receta', 'Origen', 'Fechas', 'Línea', 'Cantidad', 'Rendimiento / merma', 'Estado',
          'Responsable')),
        ('Lotes producidos',
         ('Lote', 'Producto', 'Orden', 'Producción / vencimiento', 'Cantidad', 'Control de calidad', 'Estado',
          'Ubicación')),
        ('Consumo de materias primas por orden',
         ('Orden', 'Materia prima', 'Lote', 'Cantidad', 'Desperdicio', 'Propia o del cliente')),
        ('Salidas de producto',
         ('Fecha', 'Lote / producto', 'Tipo', 'Cantidad', 'Destino / cliente', 'Valor', 'Temperatura al despacho',
          'Referencia')),
    ],
    'PP-CALIDAD': [
        ('Controles del período',
         ('Fecha', 'Plan / momento', 'Lote u orden', 'Parámetro', 'Límites', 'Valor medido', 'Conforme',
          'Resultado del control', 'Registrado por')),
        ('Liberación de lotes', ('Lote', 'Producto', 'Controles realizados', 'Decisión', 'Fecha', 'Responsable')),
        ('No conformidades',
         ('Código', 'Detección', 'Lote o proceso', 'Hallazgo / causa', 'Gravedad', 'Disposición', 'Estado',
          'Cierre')),
        ('Acciones correctivas',
         ('No conformidad', 'Acción', 'Responsable', 'Compromiso / cierre', 'Estado', 'Verificación')),
    ],
    'CE-ENSAYOS': [
        ('Ensayos',
         ('Código / nombre', 'Eje / rubro', 'Parcela o área', 'Objetivo', 'Diseño', 'Inicio / fin previsto', 'Estado',
          'Responsable', 'Revisión técnica')),
        ('Seguimiento y mediciones', ('Ensayo', 'Fecha', 'Variable / registro', 'Valor', 'Detalle', 'Registrado por')),
        ('Resultados del ensayo', ('Ensayo', 'Resultado', 'Limitaciones', 'Respaldo', 'Producto de investigación')),
    ],
    'CE-PRODUCCION': [
        ('Ciclos productivos', ('Ciclo', 'Tipo', 'Eje / rubro', 'Área', 'Inicio / fin', 'Meta', 'Obtenido', 'Estado')),
        ('Labores, sanidad e insumos aplicados',
         ('Fecha', 'Ciclo', 'Registro', 'Detalle', 'Cantidad', 'Registrado por')),
        ('Producción obtenida y salidas', ('Fecha', 'Ciclo', 'Movimiento', 'Cantidad', 'Destino', 'Registrado por')),
        ('Animales al corte', ('Hato o lote', 'Rubro', 'Animales', 'Novedades del período', 'Sanidad')),
    ],
    'OBS-DATOS': [
        ('Ficha metodológica de las series',
         ('Código / indicador', 'Definición', 'Fórmula o método', 'Unidad', 'Desagregación / territorio',
          'Periodicidad', 'Fuente', 'Limitaciones')),
        ('Actualización de las series en el semestre',
         ('Indicador', 'Datos incorporados', 'Período más reciente', 'Última actualización', 'Provisionales',
          'Revisión técnica')),
        ('Datos incorporados en el semestre',
         ('Indicador', 'Período', 'Fecha de referencia', 'Territorio', 'Valor', 'Provisional', 'Cómo entró',
          'Registrado')),
        ('Fuentes de datos',
         ('Fuente / institución', 'Qué contiene', 'Cómo se obtiene', 'Acceso / licencia', 'Periodicidad',
          'Dónde está')),
    ],
    'OBS-BOLETINES': [
        ('Calendario de publicaciones',
         ('Publicación', 'Tipo', 'Período que cubre', 'Fecha prevista / publicada', 'Estado', 'Indicadores',
          'Revisión técnica', 'Documento')),
    ],
    'OBS-EVENTOS': [
        ('Eventos realizados',
         ('Fecha', 'Actividad', 'Propósito / público', 'Productos difundidos', 'Destinatarios',
          'Participantes comprobados', 'Resultado', 'Acta', 'Revisión técnica')),
    ],
}
PROPIOS_DEL_TIPO = {
    'laboratorios': (),
    'plantas_piloto': ('PP-PRODUCCION', 'PP-CALIDAD'),
    'centro_experimental': ('CE-ENSAYOS', 'CE-PRODUCCION'),
    'observatorios': ('OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS'),
}


def _al_mediodia(dia):
    """Un instante del día dado: las 10:00 en Ecuador."""
    return datetime(dia.year, dia.month, dia.day, 15, tzinfo=zona.utc)


def _informe(unidad):
    documentos = construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))
    return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')


def _anexo(unidad, codigo):
    return next(a for a in anexos_del(_informe(unidad), incluir_no_aplica=True) if a.exigido.codigo == codigo)


class _ConUnidades(TestCase):
    tipo = 'laboratorios'

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user(f'coordinadora-propios-{cls.__name__.lower()}', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user(f'tecnico-propios-{cls.__name__.lower()}', first_name='Tomás',
                                           last_name='Técnico')
        cls.unidad = Unidad.objects.create(nombre=f'Unidad propia {cls.tipo}', slug=f'anexos-propios-{cls.tipo}',
                                           dependencia=cls.tipo, fecha_inicio=date(2025, 1, 1),
                                           administrador=cls.coordinadora)
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.tecnico,
                                                           rol='responsable_tecnico')

    def contexto(self, codigo):
        anexo = _anexo(self.unidad, codigo)
        inicio, fin = tramo_del_documento(anexo)
        self.assertEqual((inicio, fin), (date(2026, 7, 1), date(2026, 12, 31)))
        return contexto_del_anexo(anexo, inicio, fin)

    def registros(self, codigo, contexto=None):
        return constructor_de(codigo)(contexto or self.contexto(codigo))

    def evidencia(self, tipo, codigo, dia, **datos):
        base = dict(unidad=self.unidad, tipo=tipo, codigo=codigo, fecha=dia, titulo=f'Registro {codigo}',
                    descripcion='Registro de prueba.', responsable=self.tecnico, creado_por=self.coordinadora,
                    enlace=f'https://example.org/{codigo.lower()}')
        return EvidenciaGestionUnidad.objects.create(**(base | datos))


class TablasDeLaEspecificacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad propia vacía ' + tipo, slug='propios-vacia-' + tipo,
                                                    dependencia=tipo, fecha_inicio=date(2025, 1, 1))
                        for tipo in PROPIOS_DEL_TIPO}

    def test_cada_tipo_lleva_solo_sus_anexos_propios(self):
        for tipo, propios in PROPIOS_DEL_TIPO.items():
            with self.subTest(tipo=tipo):
                codigos = [a.exigido.codigo for a in anexos_del(_informe(self.unidades[tipo]), incluir_no_aplica=True)]
                self.assertEqual([c for c in codigos if c in TABLAS], list(propios))

    def test_cada_anexo_lleva_las_tablas_y_columnas_de_la_especificacion(self):
        for tipo, propios in PROPIOS_DEL_TIPO.items():
            for codigo in propios:
                with self.subTest(tipo=tipo, anexo=codigo):
                    anexo = _anexo(self.unidades[tipo], codigo)
                    registros = constructor_de(codigo)(contexto_del_anexo(anexo, *tramo_del_documento(anexo)))
                    self.assertEqual([(r.titulo, tuple(r.cabecera)) for r in registros], TABLAS[codigo])
                    for registro in registros:
                        self.assertEqual(registro.filas, [], registro.titulo)
                        self.assertTrue(registro.vacio, registro.titulo)


# -- planta piloto -------------------------------------------------------------------------

class _ConPlanta(_ConUnidades):
    tipo = 'plantas_piloto'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.linea = EspacioReservable.objects.create(unidad=cls.unidad, codigo='PP-LIN-01', nombre='Línea de yogur',
                                                     tipo='linea')
        cls.producto = Producto.objects.create(unidad=cls.unidad, codigo='PP-YOG', nombre='Yogur natural',
                                               unidad_medida='kg', requiere_frio=True, precio_venta=Decimal('2.5'))
        cls.receta = Receta.objects.create(unidad=cls.unidad, producto=cls.producto, codigo='PP-REC-YOG',
                                           nombre='Yogur batido', cantidad_base=100, unidad_base='l',
                                           rendimiento_esperado=100)
        cls.orden = OrdenProduccion.objects.create(unidad=cls.unidad, receta=cls.receta, fecha_inicio=date(2026, 9, 10),
                                                   fecha_fin=date(2026, 9, 11), linea=cls.linea,
                                                   responsable=cls.responsable, estado='terminada')
        OrdenProduccion.objects.filter(pk=cls.orden.pk).update(cantidad_obtenida=95, merma=5, rendimiento_real_pct=95)
        cls.orden.refresh_from_db()
        cls.lote = LoteProducto.objects.create(
            unidad=cls.unidad, producto=cls.producto, orden=cls.orden, codigo='LOTE-YOG-01', cantidad_inicial=95,
            cantidad_disponible=80, fecha_produccion=date(2026, 9, 11), fecha_vencimiento=date(2026, 10, 11),
            estado='disponible', control_calidad='aprobado', ubicacion='Cámara 2')


class ProduccionDeLaPlantaTests(_ConPlanta):
    def test_ordenes_reales_y_corridas_demostrativas_marcadas(self):
        demostrativa = OrdenProduccion.objects.create(unidad=self.unidad, receta=self.receta, demostrativa=True,
                                                      fecha_inicio=date(2026, 9, 15), fecha_fin=date(2026, 9, 15))
        OrdenProduccion.objects.create(unidad=self.unidad, receta=self.receta, fecha_inicio=date(2026, 5, 15),
                                       fecha_fin=date(2026, 5, 15))  # De otro período.
        tabla = self.registros('PP-PRODUCCION')[0]
        self.assertEqual(tabla.filas, [
            [self.orden.codigo, Par('Yogur natural', 'Yogur batido'), self.orden.get_origen_display(),
             Par('10/09/2026', 'al 11/09/2026'), 'PP-LIN-01', Par('100 kg', 'obtenida 95 kg'),
             Par('95 %', 'merma 5 kg'), self.orden.get_estado_display(), 'Tomás Técnico'],
            [demostrativa.codigo, Par('Yogur natural', 'Yogur batido'),
             Par(demostrativa.get_origen_display(), 'Corrida demostrativa'), Par('15/09/2026', 'al 15/09/2026'), '—',
             '100 kg', '—', demostrativa.get_estado_display(), '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 1 orden de producción real · terminadas: 1 · cantidad obtenida: 95 kg · '
                                      'rendimiento medio: 95 % · corridas demostrativas, que no cuentan para la '
                                      'meta: 1')

    def test_lotes_producidos_sin_los_demostrativos(self):
        LoteProducto.objects.create(unidad=self.unidad, producto=self.producto, codigo='LOTE-DEMO', cantidad_inicial=5,
                                    cantidad_disponible=5, fecha_produccion=date(2026, 9, 15), demostrativo=True)
        tabla = self.registros('PP-PRODUCCION')[1]
        self.assertEqual(tabla.filas, [
            ['LOTE-YOG-01', 'Yogur natural', self.orden.codigo, Par('11/09/2026', 'vence 11/10/2026'),
             Par('95 kg', 'disponible 80 kg'), self.lote.get_control_calidad_display(), self.lote.get_estado_display(),
             'Cámara 2'],
        ])
        self.assertTrue(tabla.total.endswith('que no son existencia real y no se listan: 1'))

    def test_consumo_de_materias_primas_por_orden_con_su_desperdicio(self):
        leche = Consumible.objects.create(unidad=self.unidad, codigo='PP-LECHE', nombre='Leche cruda',
                                          clasificacion='insumo', unidad_medida='l', stock_total=150)
        del_cliente = LoteConsumible.objects.create(consumible=leche, codigo='LECHE-CLI', cantidad_inicial=150,
                                                    cantidad_actual=150, bodega='Cámara 1', material_cliente=True)
        for motivo, cantidad in (('consumo_produccion', 100), ('desperdicio_calidad', 2)):
            EntradaInventario.objects.create(consumible=leche, tipo='salida', motivo=motivo, cantidad=cantidad,
                                             lote_inventario=del_cliente, referencia=self.orden.codigo,
                                             fecha=_al_mediodia(date(2026, 9, 10)))
        tabla = self.registros('PP-PRODUCCION')[2]
        self.assertEqual(tabla.filas, [
            [self.orden.codigo, Par('PP-LECHE', 'Leche cruda'), 'LECHE-CLI', '100 l',
             Par('2 l', 'por calidad o proceso'), 'Del cliente'],
        ])
        self.assertEqual(tabla.total, 'Total: 1 consumo · órdenes: 1 · con desperdicio: 1 · de materia prima del '
                                      'cliente: 1')

    def test_salidas_de_producto_con_su_valor_y_su_temperatura(self):
        MovimientoProducto.objects.create(unidad=self.unidad, lote=self.lote, tipo='venta', cantidad=10,
                                          fecha=_al_mediodia(date(2026, 9, 15)), destino='Tienda universitaria',
                                          temperatura_despacho=Decimal('4'), referencia='Factura 120',
                                          registrado_por=self.coordinadora)
        MovimientoProducto.objects.create(unidad=self.unidad, lote=self.lote, tipo='muestra', cantidad=1,
                                          fecha=_al_mediodia(date(2026, 9, 16)), destino='Laboratorio de análisis')
        tipos = dict(MovimientoProducto._meta.get_field('tipo').choices)
        tabla = self.registros('PP-PRODUCCION')[3]
        self.assertEqual(tabla.filas, [
            ['15/09/2026', Par('LOTE-YOG-01', 'Yogur natural'), tipos['venta'], '10 kg', 'Tienda universitaria',
             'USD 25', '4 °C', 'Factura 120'],
            ['16/09/2026', Par('LOTE-YOG-01', 'Yogur natural'), tipos['muestra'], '1 kg', 'Laboratorio de análisis',
             '—', 'Sin registrar', '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 salidas · ventas: 1 · valor total: USD 25')


class CalidadDeLaPlantaTests(_ConPlanta):
    def control(self):
        plan = PlanCalidad.objects.create(unidad=self.unidad, codigo='CAL-YOG', nombre='Liberación de yogur',
                                          momento='liberacion', producto=self.producto)
        acidez = ParametroCalidad.objects.create(plan=plan, orden=1, nombre='pH', unidad_medida='pH',
                                                 minimo=Decimal('4'), maximo=Decimal('4.6'))
        sabor = ParametroCalidad.objects.create(plan=plan, orden=2, nombre='Sabor', tipo='cualitativo',
                                                valor_esperado='Característico')
        control = ControlCalidad.objects.create(unidad=self.unidad, plan=plan, lote_producto=self.lote,
                                                fecha=_al_mediodia(date(2026, 9, 12)), registrado_por=self.coordinadora)
        MedicionCalidad.objects.create(control=control, parametro=acidez, valor_numerico=Decimal('4.3'))
        MedicionCalidad.objects.create(control=control, parametro=sabor, valor_texto='Característico')
        return plan, control

    def test_cada_medicion_del_control_en_su_fila(self):
        plan, control = self.control()
        tabla = self.registros('PP-CALIDAD')[0]
        comunes = ['12/09/2026', Par('Liberación de yogur', plan.get_momento_display()),
                   Par('LOTE-YOG-01', 'Lote de producto')]
        self.assertEqual(tabla.filas, [
            [*comunes, 'pH', 'mín. 4 pH · máx. 4,6 pH', '4,3 pH', 'Sí', control.get_resultado_display(),
             'Carla Coordinadora'],
            [*comunes, 'Sabor', 'Característico', 'Característico', 'Sí', control.get_resultado_display(),
             'Carla Coordinadora'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 mediciones de 1 control · controles conformes: 1 · no conformes: 0')

    def test_la_liberacion_la_decide_el_ultimo_control_de_liberacion(self):
        self.control()
        pendiente = LoteProducto.objects.create(unidad=self.unidad, producto=self.producto, orden=self.orden,
                                                codigo='LOTE-YOG-02', cantidad_inicial=10, cantidad_disponible=10,
                                                fecha_produccion=date(2026, 9, 20))
        tabla = self.registros('PP-CALIDAD')[1]
        self.assertEqual(tabla.filas, [
            ['LOTE-YOG-01', 'Yogur natural', '1', self.lote.get_control_calidad_display(), '12/09/2026',
             'Carla Coordinadora'],
            ['LOTE-YOG-02', 'Yogur natural', '0', pendiente.get_control_calidad_display(), '—', '—'],
        ])

    def test_no_conformidades_abiertas_de_antes_y_sus_acciones(self):
        hallazgo = NoConformidad.objects.create(
            unidad=self.unidad, lote_producto=self.lote, descripcion='Acidez fuera de rango.',
            causa='Temperatura de incubación baja.', gravedad='mayor', disposicion='reproceso',
            estado='en_tratamiento', detectada_en=_al_mediodia(date(2026, 9, 13)), detectada_por=self.coordinadora)
        AccionCorrectiva.objects.create(no_conformidad=hallazgo, descripcion='Recalibrar la incubadora.',
                                        responsable=self.tecnico, fecha_compromiso=date(2026, 9, 30))
        anterior = NoConformidad.objects.create(unidad=self.unidad, descripcion='Etiqueta sin lote.',
                                                detectada_en=_al_mediodia(date(2026, 5, 2)))
        NoConformidad.objects.create(unidad=self.unidad, descripcion='Cerrada antes.', estado='cerrada',
                                     detectada_en=_al_mediodia(date(2026, 4, 2)),
                                     cerrada_en=_al_mediodia(date(2026, 4, 10)))
        no_conformidades, acciones = self.registros('PP-CALIDAD')[2:]
        self.assertEqual(no_conformidades.filas, [
            [anterior.codigo, '02/05/2026', 'Proceso', 'Etiqueta sin lote.', anterior.get_gravedad_display(),
             anterior.get_disposicion_display(), anterior.get_estado_display(), '—'],
            [hallazgo.codigo, Par('13/09/2026', 'Carla Coordinadora'), 'LOTE-YOG-01',
             Par('Acidez fuera de rango.', 'Temperatura de incubación baja.'), hallazgo.get_gravedad_display(),
             hallazgo.get_disposicion_display(), hallazgo.get_estado_display(), '—'],
        ])
        self.assertTrue(no_conformidades.total.endswith('detectadas antes del período y abiertas o cerradas en él: 1'))
        self.assertEqual(acciones.filas, [
            [hallazgo.codigo, 'Recalibrar la incubadora.', 'Tomás Técnico', '30/09/2026',
             dict(AccionCorrectiva._meta.get_field('estado').choices)['pendiente'], '—'],
        ])


# -- centro experimental -------------------------------------------------------------------

class _ConCentro(_ConUnidades):
    tipo = 'centro_experimental'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parcela = EspacioReservable.objects.create(unidad=cls.unidad, codigo='CE-P07', nombre='Parcela 7',
                                                       tipo='parcela')
        cls.eje = EjeProductivo.objects.create(unidad=cls.unidad, codigo='cultivos-andinos', titulo='Cultivos andinos',
                                               resumen='Papa y quinua.', que_produce='Semilla y tubérculo.')
        cls.ensayo = CicloProductivo.objects.create(
            eje=cls.eje, nombre='Fertilización orgánica en papa', rubro='Papa', lugar=cls.parcela,
            superficie_ha=Decimal('0.5'), inicio=date(2026, 8, 1), fin_previsto=date(2027, 1, 30), estado='en_curso',
            meta=Decimal('1000'), es_ensayo=True, objetivo='Comparar compost y fertilización química.',
            tratamientos='T1 testigo\nT2 compost', repeticiones=4, variables='rendimiento, altura de planta',
            responsable=cls.tecnico)
        cls.cultivo = CicloProductivo.objects.create(
            eje=cls.eje, nombre='Papa Superchola 2026-B', rubro='Papa', lugar=cls.parcela, superficie_ha=Decimal('1.2'),
            inicio=date(2026, 6, 1), fin_previsto=date(2026, 11, 30), estado='en_curso', meta=Decimal('5000'),
            referencia='14 t/ha, INIAP')

    def registro(self, ciclo, dia, tipo, **datos):
        return RegistroProduccion.objects.create(ciclo=ciclo, fecha=dia, tipo=tipo, registrado_por=self.coordinadora,
                                                 **datos)


class EnsayosTests(_ConCentro):
    def test_un_ensayo_va_en_ensayos_y_no_en_produccion_y_al_reves(self):
        ensayos = self.registros('CE-ENSAYOS')[0]
        ciclos = self.registros('CE-PRODUCCION')[0]
        self.assertEqual([fila[0].principal for fila in ensayos.filas], [codigo_de_ensayo(self.ensayo)])
        self.assertEqual([fila[0] for fila in ciclos.filas], ['Papa Superchola 2026-B'])

    def test_el_ensayo_con_su_diseno_y_su_responsable(self):
        tabla = self.registros('CE-ENSAYOS')[0]
        self.assertEqual(tabla.filas, [
            [Par(codigo_de_ensayo(self.ensayo), 'Fertilización orgánica en papa'), Par('Cultivos andinos', 'Papa'),
             Par('CE-P07', '0,5 ha'), 'Comparar compost y fertilización química.',
             Par('T1 testigo; T2 compost · 4 repeticiones', 'Variables: rendimiento, altura de planta'),
             Par('01/08/2026', 'hasta 30/01/2027'), self.ensayo.get_estado_display(), 'Tomás Técnico', 'Pendiente'],
        ])
        self.assertEqual(tabla.total, 'Total: 1 ensayo · planificados: 0 · en curso: 1 · cerrados: 0 · con revisión '
                                      'técnica vigente: 0')

    def test_la_revision_tecnica_es_la_evidencia_verificada_que_mide_el_informe(self):
        contexto = self.contexto('CE-ENSAYOS')
        contexto.registros['fuentes_gestion'] = {
            'ENSAYOS': [{'codigo': 'ENS-REV-01', 'origen': {'id': self.ensayo.pk}}]}
        tabla = self.registros('CE-ENSAYOS', contexto)[0]
        self.assertEqual(tabla.filas[0][8], Par('Vigente', 'ENS-REV-01'))

    def test_seguimiento_del_periodo_y_resultados_documentados(self):
        self.registro(self.ensayo, date(2026, 9, 10), 'pesaje', cantidad=Decimal('25'), unidad_medida='kg',
                      detalle='Muestra de 10 plantas por tratamiento.')
        self.registro(self.cultivo, date(2026, 9, 11), 'labor', detalle='Aporque.')
        self.evidencia('ENSAYOS', 'ENS-EV-01', date(2026, 10, 15), detalle={
            'subtipo': 'ensayo', 'ciclo_id': self.ensayo.pk,
            'resultado': 'El compost aumentó el rendimiento 12 %. Limitaciones: una sola localidad.'})
        self.evidencia('ENSAYOS', 'ENS-EV-02', date(2026, 10, 16), detalle={
            'subtipo': 'ensayo', 'ciclo_id': self.cultivo.pk, 'resultado': 'No es un ensayo.'})
        self.evidencia('ENSAYOS', 'ENS-EV-03', date(2026, 10, 17), estado='anulado', detalle={
            'subtipo': 'ensayo', 'ciclo_id': self.ensayo.pk, 'resultado': 'Anulado.'})
        _ensayos, seguimiento, resultados = self.registros('CE-ENSAYOS')
        codigo = codigo_de_ensayo(self.ensayo)
        self.assertEqual(seguimiento.filas, [
            [codigo, '10/09/2026', 'Pesaje o conteo', '25 kg', 'Muestra de 10 plantas por tratamiento.',
             'Carla Coordinadora'],
        ])
        self.assertEqual(resultados.filas, [
            [codigo, Par('El compost aumentó el rendimiento 12 %.', 'ENS-EV-01 · 15/10/2026'), 'una sola localidad.',
             Par(Enlace('Abrir', 'https://example.org/ens-ev-01'), 'Borrador'), '—'],
        ])
        self.assertTrue(resultados.total.endswith('que no están marcados como ensayo, que no se listan: 1'))


class ProduccionAgropecuariaTests(_ConCentro):
    def test_ciclo_con_su_meta_y_lo_obtenido(self):
        self.registro(self.cultivo, date(2026, 6, 20), 'cosecha', cantidad=Decimal('300'), unidad_medida='kg')
        self.registro(self.cultivo, date(2026, 9, 20), 'cosecha', cantidad=Decimal('1200'), unidad_medida='kg',
                      destino='planta')
        tabla = self.registros('CE-PRODUCCION')[0]
        self.assertEqual(tabla.filas, [
            ['Papa Superchola 2026-B', 'Campaña de cultivo', Par('Cultivos andinos', 'Papa'), Par('CE-P07', '1,2 ha'),
             Par('01/06/2026', 'previsto 30/11/2026'), Par('5.000 kg', '14 t/ha, INIAP'),
             Par('1.500 kg', 'en el período 1.200 kg'), self.cultivo.get_estado_display()],
        ])

    def test_labores_y_produccion_van_en_tablas_distintas(self):
        self.registro(self.cultivo, date(2026, 9, 5), 'labor', detalle='Aporque.')
        self.registro(self.cultivo, date(2026, 9, 8), 'sanidad', detalle='Control de tizón.', cantidad=Decimal('2'),
                      unidad_medida='L')
        self.registro(self.cultivo, date(2026, 9, 20), 'cosecha', cantidad=Decimal('1200'), unidad_medida='kg',
                      destino='planta', detalle='Lote para la planta de procesados.')
        self.registro(self.ensayo, date(2026, 9, 21), 'labor', detalle='Labor del ensayo.')
        _ciclos, manejo, movimientos, _animales = self.registros('CE-PRODUCCION')
        self.assertEqual(manejo.filas, [
            ['05/09/2026', 'Papa Superchola 2026-B', 'Labor', 'Aporque.', '—', 'Carla Coordinadora'],
            ['08/09/2026', 'Papa Superchola 2026-B', 'Sanidad', 'Control de tizón.', '2 L', 'Carla Coordinadora'],
        ])
        self.assertEqual(movimientos.filas, [
            ['20/09/2026', 'Papa Superchola 2026-B', 'Cosecha', '1.200 kg',
             Par('Planta piloto', 'Lote para la planta de procesados.'), 'Carla Coordinadora'],
        ])

    def test_animales_al_corte_con_su_ultimo_conteo_novedades_y_sanidad(self):
        hato = CicloProductivo.objects.create(eje=self.eje, nombre='Hato lechero 2026', tipo='hato',
                                              rubro='Bovino Holstein', inicio=date(2026, 1, 1),
                                              fin_previsto=date(2026, 12, 31), estado='en_curso', meta=Decimal('20000'),
                                              unidad_medida='L', animales=20)
        self.registro(hato, date(2026, 9, 10), 'sanidad', detalle='Vacuna contra aftosa.')
        self.registro(hato, date(2026, 9, 15), 'pesaje', cantidad=Decimal('22'), unidad_medida='animales')
        self.registro(hato, date(2026, 9, 18), 'salida', cantidad=Decimal('2'), unidad_medida='animales',
                      detalle='Venta de terneros.')
        animales = self.registros('CE-PRODUCCION')[3]
        self.assertEqual(animales.filas, [
            ['Hato lechero 2026', 'Bovino Holstein', Par('20 al inicio', 'último conteo: 22 (15/09/2026)'),
             Par('Salidas: 2 animales', '18/09 Venta de terneros.'), '10/09/2026 Vacuna contra aftosa.'],
        ])


# -- observatorio --------------------------------------------------------------------------

class _ConObservatorio(_ConUnidades):
    tipo = 'observatorios'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fuente = FuenteDatos.objects.create(nombre='Sistema de precios agrícolas', institucion='MAG',
                                                descripcion='Precios mayoristas semanales.', metodo='pagina',
                                                acceso='abierto', licencia='Uso libre con cita',
                                                periodicidad='Semanal', url='https://example.org/precios')
        cls.papa = IndicadorObservatorio.objects.create(
            unidad=cls.unidad, codigo='OBS-PAPA', nombre='Precio de la papa',
            definicion='Precio mayorista del quintal.', formula='Promedio de los precios semanales del mes.',
            unidad_medida='USD/qq', fuente='MAG', tipo_fuente='registro', url_fuente='https://example.org/mag',
            periodicidad='mensual', desagregacion='Cantonal', territorio_principal='Carchi',
            limitaciones='Solo mercados mayoristas.', fuente_datos=cls.fuente, publicado=True, orden=1)
        cls.leche = IndicadorObservatorio.objects.create(
            unidad=cls.unidad, codigo='OBS-LECHE', nombre='Precio de la leche', unidad_medida='USD/L',
            periodicidad='mensual', publicado=False, orden=2)
        for indicador, periodo, dia, valor, provisional, registrado in (
                (cls.papa, '2026-08', date(2026, 8, 1), '18.5', False, date(2026, 9, 3)),
                (cls.papa, '2026-09', date(2026, 9, 1), '19.25', True, date(2026, 10, 2)),
                (cls.leche, '2026-09', date(2026, 9, 1), '0.45', False, date(2026, 10, 5)),
                (cls.leche, '2026-03', date(2026, 3, 1), '0.42', False, date(2026, 4, 5))):
            ValorIndicador.objects.create(indicador=indicador, periodo=periodo, fecha=dia, valor=Decimal(valor),
                                          provisional=provisional, origen='manual', registrado=_al_mediodia(registrado))


class DatosDelObservatorioTests(_ConObservatorio):
    def test_ficha_metodologica_de_cada_serie(self):
        tabla = self.registros('OBS-DATOS')[0]
        self.assertEqual(tabla.filas[0], [
            Par('OBS-PAPA', 'Precio de la papa'), 'Precio mayorista del quintal.',
            'Promedio de los precios semanales del mes.', 'USD/qq', Par('Cantonal', 'Carchi'),
            self.papa.get_periodicidad_display(),
            Par(Enlace('MAG', 'https://example.org/mag'), self.papa.get_tipo_fuente_display()),
            'Solo mercados mayoristas.'])
        self.assertEqual(tabla.filas[1][0], Par('OBS-LECHE', 'Precio de la leche (no publicado)'))
        self.assertEqual(tabla.total, 'Total: 2 series · publicadas: 1')

    def test_actualizacion_de_cada_serie_en_el_semestre(self):
        tabla = self.registros('OBS-DATOS')[1]
        self.assertEqual(tabla.filas, [
            ['OBS-PAPA', '2', '2026-09', '02/10/2026', '1', 'Pendiente'],
            ['OBS-LECHE', '1', '2026-09', '05/10/2026', '0', 'Pendiente'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 series · con datos incorporados en el semestre: 2 · datos '
                                      'incorporados: 3 · provisionales: 1 · con revisión técnica vigente: 0')

    def test_la_revision_tecnica_de_una_serie_es_la_evidencia_verificada(self):
        contexto = self.contexto('OBS-DATOS')
        contexto.registros['fuentes_gestion'] = {
            'DATOS-ACTUALIZADOS': [{'codigo': 'DAT-REV-01', 'origen': {'id': self.papa.pk}}]}
        tabla = self.registros('OBS-DATOS', contexto)[1]
        self.assertEqual([fila[5] for fila in tabla.filas], [Par('Vigente', 'DAT-REV-01'), 'Pendiente'])

    def test_los_valores_del_semestre_se_agrupan_por_indicador(self):
        tabla = self.registros('OBS-DATOS')[2]
        self.assertEqual(tabla.filas, [
            Grupo('OBS-PAPA · Precio de la papa · USD/qq · 2 datos'),
            ['OBS-PAPA', '2026-08', '01/08/2026', 'Carchi', '18,5', 'No', 'Manual', '03/09/2026'],
            ['OBS-PAPA', '2026-09', '01/09/2026', 'Carchi', '19,25', 'Sí', 'Manual', '02/10/2026'],
            Grupo('OBS-LECHE · Precio de la leche · USD/L · 1 dato'),
            ['OBS-LECHE', '2026-09', '01/09/2026', 'Carchi', '0,45', 'No', 'Manual', '05/10/2026'],
        ])
        self.assertEqual(tabla.total, 'Total: 3 datos de 2 series')

    def test_las_fuentes_de_sus_series(self):
        tabla = self.registros('OBS-DATOS')[3]
        self.assertEqual(tabla.filas, [
            [Par('Sistema de precios agrícolas', 'MAG'), 'Precios mayoristas semanales.',
             self.fuente.get_metodo_display(), Par(self.fuente.get_acceso_display(), 'Uso libre con cita'), 'Semanal',
             Enlace('Abrir', 'https://example.org/precios')],
        ])
        self.assertEqual(tabla.total, 'Total: 1 fuente · series sin fuente del catálogo, descritas solo en su ficha: 1')


class PublicacionesYSocializacionTests(_ConObservatorio):
    def publicacion(self, titulo, prevista, **datos):
        return PublicacionObservatorio.objects.create(unidad=self.unidad, titulo=titulo, fecha_planificada=prevista,
                                                      **datos)

    def test_calendario_de_publicaciones_con_su_puntualidad(self):
        atrasada = self.publicacion('Boletín de precios 2', date(2026, 8, 15), periodo='2026-T2', estado='publicada',
                                    fecha_publicada=date(2026, 8, 30), enlace='https://example.org/boletin-2')
        a_tiempo = self.publicacion('Boletín de precios 3', date(2026, 9, 20), periodo='2026-T3', estado='publicada',
                                    fecha_publicada=date(2026, 9, 18), enlace='https://example.org/boletin-3')
        a_tiempo.indicadores.add(self.papa, self.leche)
        cancelada = self.publicacion('Perfil cantonal', date(2026, 10, 15), tipo='perfil', estado='cancelada')
        pendiente = self.publicacion('Boletín de precios 4', date(2026, 11, 30), periodo='2026-T4')
        self.publicacion('Boletín de precios 1', date(2026, 5, 10), estado='publicada',
                         fecha_publicada=date(2026, 5, 12))
        tabla = self.registros('OBS-BOLETINES')[0]

        def fila(publicacion, publicada, indicadores, revision, documento):
            return [publicacion.titulo, publicacion.get_tipo_display(), publicacion.periodo or '—',
                    Par(publicacion.fecha_planificada.strftime('%d/%m/%Y'), publicada) if publicada
                    else publicacion.fecha_planificada.strftime('%d/%m/%Y'),
                    publicacion.get_estado_display(), indicadores, revision, documento]
        self.assertEqual(tabla.filas, [
            fila(atrasada, 'publicada 30/08/2026', '—', 'Pendiente', Enlace('Abrir', 'https://example.org/boletin-2')),
            fila(a_tiempo, 'publicada 18/09/2026', 'OBS-PAPA, OBS-LECHE', 'Pendiente',
                 Enlace('Abrir', 'https://example.org/boletin-3')),
            fila(cancelada, '', '—', '—', '—'),
            fila(pendiente, '', '—', '—', '—'),
        ])
        self.assertEqual(tabla.total, 'Total: 4 publicaciones · previstas en el período: 4 · publicadas a tiempo: 1 · '
                                      'publicadas con atraso: 1 · pendientes: 1 · canceladas: 1')

    def test_eventos_de_socializacion_sin_los_anulados(self):
        detalle = {'subtipo': 'socializacion', 'fecha_evento': '2026-10-10', 'objetivo': 'Presentar el boletín 3.',
                   'productos_difundidos': 'Boletín de precios 3', 'beneficiario': 'Productores de Montúfar',
                   'participantes': 35, 'resultado': 'Acuerdo para difundir el boletín.',
                   'referencia_acta': 'ACTA-EV-1'}
        evento = self.evidencia('EVENTOS', 'EV-01', date(2026, 10, 11), detalle=detalle, estado='validado')
        self.evidencia('EVENTOS', 'EV-02', date(2026, 10, 12), detalle=detalle, estado='anulado')
        self.evidencia('EVENTOS', 'EV-03', date(2026, 10, 13), detalle=detalle | {'subtipo': 'otro'})
        tabla = self.registros('OBS-EVENTOS')[0]
        self.assertEqual(tabla.filas, [
            ['10/10/2026', 'Registro EV-01', 'Presentar el boletín 3.', 'Boletín de precios 3',
             'Productores de Montúfar', '35', 'Acuerdo para difundir el boletín.',
             Par(Enlace('Abrir', 'https://example.org/ev-01'), 'ACTA-EV-1'),
             Par('Pendiente', 'Verificación no vigente')],
        ])
        self.assertEqual(tabla.total,
                         'Total: 1 evento · participantes comprobados: 35 · con revisión técnica vigente: 0')
        # Con la evidencia vigente en la medición del informe, la revisión técnica queda vigente.
        contexto = self.contexto('OBS-EVENTOS')
        contexto.registros['fuentes_gestion'] = {'EVENTOS': [{'evidencia': evento.pk}]}
        self.assertEqual(self.registros('OBS-EVENTOS', contexto)[0].filas[0][8], 'Vigente')
