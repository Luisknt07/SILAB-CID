"""Rutas de captura de la planta piloto, el centro experimental y el observatorio.

Es la prueba de cargue de sus anexos propios y de lo común que cambia respecto del laboratorio: con la
cuenta de la unidad (administra y coordina, no es superusuario) se registra por HTTP lo que enviaría cada
pantalla, se lleva el registro hasta el estado en que el anexo lo cuenta y se comprueba que sale en su
tabla y en el borrador al día del anexo.

Lo que no es de estos anexos (los insumos en existencia de la planta, que son del anexo de inventario) se
prepara con el modelo: su ruta de captura se prueba con los anexos de inventario del laboratorio.
"""
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, RegistroProduccion
from apps.core.roles import MODULOS_OPERATIVOS
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.resultados_gestion import CONDICIONES_COMUNES, CONDICIONES_PROPIAS
from apps.documentos.presentation.anexos_evidencia import constructor_de, contexto_del_anexo
from apps.documentos.presentation.documentos_entrega import ruta_borrador
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.observatorios.operacion.models.observatorios import (
    FuenteDatos, IndicadorObservatorio, PublicacionObservatorio, SolicitudDatos, ValorIndicador,
)
from apps.plantas_piloto.operacion.models.calidad import AccionCorrectiva, ControlCalidad, NoConformidad, PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion, Producto, Receta
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar, pdf_legible_prueba


def _plano(valor):
    """El texto de una celda del anexo, sea texto, par o enlace."""
    if isinstance(valor, (list, tuple)):
        return ' '.join(_plano(parte) for parte in valor)
    partes = [getattr(valor, nombre, None) for nombre in ('arriba', 'abajo', 'texto', 'rotulo', 'url')]
    partes = [_plano(parte) for parte in partes if parte not in (None, '')]
    return ' '.join(partes) if partes else str(valor)


def _texto_del_pdf(contenido):
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class _BaseDeRutas(TestCase):
    """Una unidad ficticia del tipo dado y su cuenta, como las `admin.<unidad>` de la plataforma."""
    tipo = ''
    slug = ''

    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.cuenta = get_user_model().objects.create_user(
            f'admin.{cls.slug}', password='clave-ficticia', first_name='Ada', last_name='Administradora')
        identificar(cls.cuenta, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre=f'Unidad ficticia de rutas {cls.tipo}', slug=cls.slug, dependencia=cls.tipo,
            descripcion='Unidad ficticia para la prueba de cargue.',
            fecha_inicio=cls.hoy.replace(year=cls.hoy.year - 1, day=1), administrador=cls.cuenta, activo=True)
        cls.coordinacion = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.cuenta, nombre='Ada Administradora', rol='coordinacion',
            permisos_operativos={modulo: True for modulo in MODULOS_OPERATIVOS}, activo=True)
        cls.periodo = dict(anio=cls.hoy.year, corte='A' if cls.hoy.month <= 6 else 'B')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='rutas-k4-', ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.assertFalse(self.cuenta.is_staff or self.cuenta.is_superuser)
        self.client.force_login(self.cuenta)

    # -- las pantallas, como las usa la unidad --------------------------------------------------

    def operar(self, **datos):
        """Un formulario del panel de la unidad o del ERP de la planta («Guardar» en el cajón lateral)."""
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        return respuesta.json()['registro']['id']

    def editar(self, clave, pk='nuevo', padre='', **campos):
        """El cuadro «Agregar» o «Editar» de las páginas de la unidad (editor de registros)."""
        datos = {f'registro-{nombre}': valor for nombre, valor in campos.items()}
        if padre:
            datos['padre'] = padre
        respuesta = self.client.post(reverse('editar_registro', args=[self.unidad.slug, clave, pk]), datos)
        if respuesta.status_code != 302:
            self.fail(f'{clave} no se guardó: {respuesta.context["formulario"].errors.as_json()}')

    def evidencia(self, tipo, codigo, **datos):
        """«Registrar evidencia» de una meta, marcada como comprobada y con su respaldo."""
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        base = dict(tipo=tipo, codigo=codigo, fecha=self.hoy.isoformat(), titulo=f'Registro ficticio {codigo}',
                    descripcion='Registro ficticio de la prueba de cargue.', responsable=self.cuenta.pk,
                    archivo=SimpleUploadedFile(f'{codigo}.pdf', pdf_legible_prueba(
                        f'Respaldo ficticio {codigo}: acta de prueba sin validez institucional.'),
                        content_type='application/pdf'),
                    verificar='on', **self.periodo)
        respuesta = self.client.post(ruta, base | datos)
        if respuesta.status_code != 302:
            self.fail(f'La evidencia {codigo} no se guardó: {respuesta.context["form"].errors.as_json()}')
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo=codigo)
        self.assertEqual((evidencia.estado, evidencia.validado_por), ('validado', self.cuenta))
        return evidencia

    def panel(self, vista):
        respuesta = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': vista})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    # -- los documentos, como los pide la unidad ------------------------------------------------

    def anexos(self):
        documentos = construir_expediente(self.unidad, self.hoy.year, hoy=self.hoy)
        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL'
                       and tramo_del_documento(d)[0] <= self.hoy <= tramo_del_documento(d)[1])
        return anexos_del(informe, incluir_no_aplica=True)

    def anexo(self, codigo):
        return next(a for a in self.anexos() if a.exigido.codigo == codigo)

    def tablas(self, codigo):
        """{título: filas en texto} del anexo con los registros al día."""
        anexo = self.anexo(codigo)
        registros = constructor_de(codigo)(contexto_del_anexo(anexo, *tramo_del_documento(anexo)))
        return {r.titulo: [' | '.join(_plano(celda) for celda in fila) for fila in r.filas
                           if isinstance(fila, (list, tuple))] for r in registros}

    def fila(self, codigo, titulo, contiene):
        filas = self.tablas(codigo)[titulo]
        encontradas = [fila for fila in filas if contiene in fila]
        self.assertEqual(len(encontradas), 1, f'«{contiene}» en «{titulo}»: {filas}')
        return encontradas[0]

    def pdf_del_anexo(self, codigo):
        """«Borrador al día» del anexo, en el Centro de reportes de la unidad."""
        respuesta = self.client.get(ruta_borrador(self.anexo(codigo)))
        self.assertEqual((respuesta.status_code, respuesta['Content-Type']), (200, 'application/pdf'))
        return _texto_del_pdf(respuesta.content)

    def inspeccion(self, codigo, condiciones):
        """Seguridad → «Registrar inspección»: la evidencia con las condiciones que revisó."""
        return self.evidencia('INSPECCION', codigo, titulo='Inspección mensual ficticia',
                              descripcion='Chequeo completo sin novedades.', area='Área ficticia',
                              condiciones_revisadas=condiciones, estado_condiciones='seguro', sin_hallazgos='on',
                              estado_accion='no_requiere')


# -- planta piloto ------------------------------------------------------------------------------

class RutasDeLaPlantaPilotoTests(_BaseDeRutas):
    tipo = 'plantas_piloto'
    slug = 'planta-rutas-k4'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.linea = EspacioReservable.objects.create(unidad=cls.unidad, codigo='K4-LINEA', nombre='Línea ficticia',
                                                     tipo='linea', capacidad=4)
        # La materia prima en existencia es del anexo de inventario: se prepara con el modelo.
        cls.leche = Consumible.objects.create(unidad=cls.unidad, codigo='K4-LECHE', nombre='Leche ficticia',
                                              clasificacion='insumo', unidad_medida='l', stock_total=300)
        cls.lote_leche = LoteConsumible.objects.create(consumible=cls.leche, codigo='K4-LECHE-L1',
                                                       cantidad_inicial=300, cantidad_actual=300,
                                                       bodega='Tanque ficticio', estado='en_uso')

    def setUp(self):
        super().setUp()
        # Configuración y personal → «Registra producción»: activa el ERP de la planta.
        self.panel('configuracion')
        self.operar(modulo='configuracion', registra_produccion='on', inventario_equipos='on',
                    mantenimiento_equipos='on', consumibles='on', indicadores_reportes='on')

    def receta(self):
        """ERP → Producción: «Nuevo producto» y «Nueva receta» con su materia prima."""
        producto = Producto.objects.get(pk=self.operar(
            modulo='producto', codigo='K4-YOGUR', nombre='Yogur ficticio', tipo='terminado', unidad_medida='kg',
            precio_venta='2.50', vida_util_dias='20', requiere_frio='on', temperatura_maxima='6', activo='on'))
        receta = Receta.objects.get(pk=self.operar(
            modulo='receta', producto_id=producto.pk, codigo='K4-REC-YOGUR', nombre='Yogur ficticio por 100 l',
            cantidad_base='100', unidad_base='l', rendimiento_esperado='95', activa='on',
            insumo_consumible=[str(self.leche.pk)], insumo_cantidad=['100'], insumo_obligatorio=['si'],
            insumo_etapa=[''], insumo_forma_parte=['si']))
        return producto, receta

    def corrida(self, receta):
        """«Planificar orden», «Iniciar» y «Cerrar» con el consumo por lote: nace el lote del producto."""
        orden = OrdenProduccion.objects.get(pk=self.operar(
            modulo='orden_produccion', receta_id=receta.pk, factor='1', fecha_inicio=self.hoy.isoformat(),
            fecha_fin=self.hoy.isoformat(), linea_id=self.linea.pk, responsable_id=self.coordinacion.pk,
            origen='propia', observaciones='Corrida ficticia.'))
        self.operar(modulo='orden_produccion', registro_id=orden.pk, accion_orden='iniciar')
        self.operar(modulo='orden_produccion', registro_id=orden.pk, accion_orden='cerrar', **{
            f'consumo_cantidad_{self.leche.pk}': '100', f'consumo_lote_{self.leche.pk}': self.lote_leche.pk,
            f'salida_cantidad_{receta.producto_id}': '90', 'ubicacion_lotes': 'Cámara ficticia',
            'observaciones_cierre': 'Merma por llenado.'})
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'terminada')
        return orden, LoteProducto.objects.get(orden=orden)

    def plan_de_liberacion(self, producto):
        """ERP → Calidad: «Nuevo plan» de liberación y su parámetro con límites."""
        plan = PlanCalidad.objects.get(pk=self.operar(
            modulo='plan_calidad', codigo='k4-lib', nombre='Liberación ficticia de yogur', momento='liberacion',
            producto_id=producto.pk))
        self.operar(modulo='parametro_calidad', plan_id=plan.pk, orden='1', nombre='pH', tipo='numerico',
                    unidad_medida='pH', minimo='4', maximo='4.6', metodo='Potenciómetro ficticio', critico='on')
        return plan

    def controlar(self, plan, lote, valor):
        """«Controlar» el lote: la hoja de control con el valor de cada parámetro."""
        parametro = plan.parametros_ordenados()[0]
        ruta = reverse('control_calidad', args=[self.unidad.slug]) + f'?lote_producto={lote.pk}&plan={plan.pk}'
        self.assertEqual(self.client.get(ruta).status_code, 200)
        respuesta = self.client.post(ruta, {f'parametro_{parametro.pk}': valor, 'observaciones': 'Control ficticio.'})
        self.assertEqual(respuesta.status_code, 302, respuesta.content.decode()[:500])
        return ControlCalidad.objects.filter(lote_producto=lote).latest('pk')

    def test_el_erp_de_la_planta_ofrece_produccion_y_calidad_a_la_cuenta_de_la_unidad(self):
        erp = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertEqual(erp.status_code, 200)
        for formulario in ('producto', 'receta', 'orden_produccion', 'movimiento_producto', 'plan_calidad',
                           'parametro_calidad', 'no_conformidad', 'accion_correctiva'):
            self.assertContains(erp, f'data-agenda-operation-form="{formulario}"')

    def test_la_orden_cerrada_con_su_consumo_y_la_venta_del_lote_salen_en_el_anexo_de_produccion(self):
        producto, receta = self.receta()
        orden, lote = self.corrida(receta)
        self.assertEqual((lote.estado, lote.control_calidad), ('cuarentena', 'pendiente'))
        # La liberación por el control de calidad deja el lote disponible para salir.
        self.controlar(self.plan_de_liberacion(producto), lote, '4.3')
        lote.refresh_from_db()
        self.assertEqual((lote.estado, lote.control_calidad), ('disponible', 'aprobado'))
        self.operar(modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='10',
                    destino='Feria ficticia', cliente='Cliente ficticio', referencia='FAC-K4-001',
                    temperatura_despacho='4')
        self.assertEqual(MovimientoProducto.objects.get(lote=lote).valor_total, 25)
        self.assertTrue(EntradaInventario.objects.filter(referencia=orden.codigo, motivo='consumo_produccion').exists())

        fila = self.fila('PP-PRODUCCION', 'Órdenes de producción', orden.codigo)
        for dato in ('Yogur ficticio', 'K4-LINEA', 'obtenida 90 kg', 'Ada Administradora'):
            self.assertIn(dato, fila)
        self.assertIn('Cámara ficticia', self.fila('PP-PRODUCCION', 'Lotes producidos', lote.codigo))
        self.assertIn('K4-LECHE-L1', self.fila('PP-PRODUCCION', 'Consumo de materias primas por orden', orden.codigo))
        venta = self.fila('PP-PRODUCCION', 'Salidas de producto', lote.codigo)
        for dato in ('10 kg', 'Feria ficticia', 'USD 25', '4 °C', 'FAC-K4-001'):
            self.assertIn(dato, venta)
        texto = self.pdf_del_anexo('PP-PRODUCCION')
        self.assertIn(orden.codigo, texto)
        self.assertIn('FAC-K4-001', texto)

    def test_la_liberacion_la_no_conformidad_y_su_accion_salen_en_el_anexo_de_calidad(self):
        producto, receta = self.receta()
        plan = self.plan_de_liberacion(producto)
        _orden, liberado = self.corrida(receta)
        self.controlar(plan, liberado, '4.3')
        # Un segundo lote fuera de límite abre su no conformidad, que se decide y se corrige.
        self.lote_leche.refresh_from_db()
        _orden, rechazado = self.corrida(receta)
        control = self.controlar(plan, rechazado, '5.2')
        self.assertEqual(control.resultado, 'no_conforme')
        hallazgo = NoConformidad.objects.get(control=control)
        self.assertEqual(hallazgo.gravedad, 'critica')
        self.operar(modulo='accion_correctiva', no_conformidad_id=hallazgo.pk,
                    descripcion='Recalibrar el potenciómetro ficticio.', responsable=self.cuenta.username,
                    fecha_compromiso=self.hoy.isoformat(), estado='cumplida', verificacion='Calibración verificada.')
        self.operar(modulo='no_conformidad', registro_id=hallazgo.pk, estado='cerrada', disposicion='rechazo',
                    causa='Fermentación prolongada.')
        hallazgo.refresh_from_db()
        rechazado.refresh_from_db()
        self.assertEqual((hallazgo.estado, rechazado.control_calidad), ('cerrada', 'rechazado'))

        controles = self.tablas('PP-CALIDAD')['Controles del período']
        self.assertEqual(len(controles), 2, controles)
        self.assertTrue(any('4,3 pH' in fila and 'mín. 4 pH · máx. 4,6 pH' in fila for fila in controles), controles)
        self.assertIn('Aprobado', self.fila('PP-CALIDAD', 'Liberación de lotes', liberado.codigo))
        self.assertIn('Rechazado', self.fila('PP-CALIDAD', 'Liberación de lotes', rechazado.codigo))
        fila = self.fila('PP-CALIDAD', 'No conformidades', hallazgo.codigo)
        for dato in ('Fermentación prolongada.', 'Crítica', 'Cerrada'):
            self.assertIn(dato, fila)
        accion = self.fila('PP-CALIDAD', 'Acciones correctivas', hallazgo.codigo)
        self.assertIn('Recalibrar el potenciómetro ficticio.', accion)
        self.assertIn('Calibración verificada.', accion)
        self.assertEqual(AccionCorrectiva.objects.get(no_conformidad=hallazgo).estado, 'cumplida')
        self.assertIn(hallazgo.codigo, self.pdf_del_anexo('PP-CALIDAD'))

    def test_la_inspeccion_de_la_planta_revisa_bpm_sanitizacion_plagas_y_cadena_de_frio(self):
        claves = [clave for clave, _ in CONDICIONES_COMUNES + CONDICIONES_PROPIAS['plantas_piloto']]
        formulario = self.client.get(reverse('fuentes_metas_unidad', args=[self.unidad.slug]),
                                     dict(tipo='INSPECCION', **self.periodo))
        for clave in ('bpm', 'sanitizacion', 'plagas', 'cadena_frio'):
            self.assertContains(formulario, f'value="{clave}"')
        self.inspeccion('INS-K4-PP', claves)
        fila = self.fila('INDUCCION-SEGURIDAD', 'Inspecciones de condiciones', 'Área ficticia')
        self.assertIn('11 de 11', fila)
        self.assertIn('cadena de frío', fila)


# -- centro experimental ------------------------------------------------------------------------

class RutasDelCentroExperimentalTests(_BaseDeRutas):
    tipo = 'centro_experimental'
    slug = 'centro-rutas-k4'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parcela = EspacioReservable.objects.create(unidad=cls.unidad, codigo='K4-PARCELA', nombre='Parcela ficticia',
                                                       tipo='area', capacidad=10)

    def eje(self):
        """Ficha del centro → Ejes productivos → «Agregar un eje»."""
        self.editar('eje_productivo', codigo='k4-agricola', titulo='Eje agrícola ficticio', icono='fas fa-seedling',
                    resumen='Cultivos ficticios.', que_produce='Papa ficticia para prácticas.', orden='1',
                    publicado='on')
        return EjeProductivo.objects.get(unidad=self.unidad, codigo='k4-agricola')

    def ciclo(self, eje, nombre, **campos):
        """Producción del centro → «Planificar un ciclo»."""
        base = dict(eje=eje.pk, nombre=nombre, tipo='cultivo', rubro='Papa ficticia', lugar=self.parcela.pk,
                    inicio=self.hoy.isoformat(), fin_previsto=(self.hoy + timedelta(days=120)).isoformat(),
                    superficie_ha='0.50', meta='1000', unidad_medida='kg', estado='en_curso',
                    responsable=self.cuenta.pk)
        self.editar('ciclo_productivo', **(base | campos))
        return CicloProductivo.objects.get(eje=eje, nombre=nombre)

    def registrar(self, ciclo, **campos):
        """Producción del centro → «Registrar» (lo del día: labor, cosecha, entrega, pesaje…)."""
        datos = dict(ciclo=ciclo.pk, fecha=self.hoy.isoformat(), cantidad='', unidad_medida='', destino='',
                     detalle='') | campos
        respuesta = self.client.post(reverse('produccion_centro', args=[self.unidad.slug]), datos)
        if respuesta.status_code != 302:
            self.fail(f'El registro no se guardó: {respuesta.context["formulario"].errors.as_json()}')
        return RegistroProduccion.objects.filter(ciclo=ciclo).latest('pk')

    def test_un_ensayo_con_su_seguimiento_y_su_resultado_sale_en_el_anexo_de_ensayos(self):
        pagina = self.client.get(reverse('produccion_centro', args=[self.unidad.slug]))
        self.assertContains(pagina, reverse('editar_registro', args=[self.unidad.slug, 'ciclo_productivo', 'nuevo']))
        ensayo = self.ciclo(self.eje(), 'Ensayo ficticio de fertilización', es_ensayo='on',
                            objetivo='Comparar dos dosis ficticias.', tratamientos='T1 · Testigo\nT2 · 60 kg N/ha',
                            repeticiones='3', variables='Rendimiento (t/ha)')
        medicion = self.registrar(ensayo, tipo='pesaje', cantidad='12.5', unidad_medida='kg',
                                  detalle='Peso de tubérculos por parcela')
        self.evidencia('ENSAYOS', 'ENS-K4-001', subtipo='ensayo', ciclo_id=ensayo.pk, registros_ids=[medicion.pk],
                       objetivo='Comparar dos dosis ficticias.', metodo='Diseño de bloques ficticio.',
                       resultado='T2 rindió más. Limitaciones: una sola campaña ficticia.')

        fila = self.fila('CE-ENSAYOS', 'Ensayos', 'Ensayo ficticio de fertilización')
        for dato in ('Papa ficticia', 'K4-PARCELA', 'Comparar dos dosis ficticias.', 'Ada Administradora', 'Vigente'):
            self.assertIn(dato, fila)
        self.assertIn('Peso de tubérculos por parcela', self.fila('CE-ENSAYOS', 'Seguimiento y mediciones', '12,5'))
        resultado = self.fila('CE-ENSAYOS', 'Resultados del ensayo', 'ENS-K4-001')
        self.assertIn('una sola campaña ficticia', resultado)
        self.assertNotIn('Ensayo ficticio de fertilización', ' '.join(
            ' '.join(filas) for filas in self.tablas('CE-PRODUCCION').values()))
        self.assertIn('Peso de tubérculos por parcela', self.pdf_del_anexo('CE-ENSAYOS'))

    def test_un_hato_con_sanidad_ordeno_entrega_y_conteo_sale_en_produccion_agropecuaria(self):
        hato = self.ciclo(self.eje(), 'Hato ficticio de ordeño', tipo='hato', rubro='Bovinos ficticios',
                          superficie_ha='', animales='12', meta='3000', unidad_medida='L')
        self.registrar(hato, tipo='sanidad', detalle='Vacuna ficticia contra aftosa')
        self.registrar(hato, tipo='ordeno', cantidad='80', unidad_medida='L', detalle='Ordeño de la mañana')
        self.registrar(hato, tipo='entrega', cantidad='60', unidad_medida='L', destino='planta',
                       detalle='Entrega ficticia a la planta')
        self.registrar(hato, tipo='pesaje', cantidad='11', unidad_medida='animales', detalle='Conteo ficticio del hato')
        self.registrar(hato, tipo='novedad', detalle='Una baja ficticia por venta')

        self.assertIn('80 L', self.fila('CE-PRODUCCION', 'Ciclos productivos', 'Hato ficticio de ordeño'))
        self.assertIn('Vacuna ficticia contra aftosa',
                      self.fila('CE-PRODUCCION', 'Labores, sanidad e insumos aplicados', 'Vacuna'))
        entrega = self.fila('CE-PRODUCCION', 'Producción obtenida y salidas', 'Planta piloto')
        self.assertIn('60 L', entrega)
        animales = self.fila('CE-PRODUCCION', 'Animales al corte', 'Hato ficticio de ordeño')
        self.assertIn('12', animales)
        self.assertIn('Vacuna ficticia contra aftosa', animales)
        self.assertIn('Ordeño de la mañana', self.pdf_del_anexo('CE-PRODUCCION'))

    def test_la_inspeccion_del_centro_revisa_agroquimicos_maquinaria_y_sanidad_animal(self):
        claves = [clave for clave, _ in CONDICIONES_COMUNES + CONDICIONES_PROPIAS['centro_experimental']]
        self.inspeccion('INS-K4-CE', claves)
        fila = self.fila('INDUCCION-SEGURIDAD', 'Inspecciones de condiciones', 'Área ficticia')
        self.assertIn('10 de 10', fila)
        self.assertIn('sanidad animal', fila)


# -- observatorio -------------------------------------------------------------------------------

class RutasDelObservatorioTests(_BaseDeRutas):
    tipo = 'observatorios'
    slug = 'observatorio-rutas-k4'

    def serie(self):
        """Fuentes → «Agregar una fuente»; Indicadores → «Agregar un indicador»; su ficha → «Agregar un valor»."""
        fuentes = self.client.get(reverse('fuentes_observatorio', args=[self.unidad.slug]))
        self.assertContains(fuentes, reverse('editar_registro', args=[self.unidad.slug, 'fuente_datos', 'nuevo']))
        self.editar('fuente_datos', nombre='Encuesta ficticia K4', institucion='Instituto Ficticio',
                    descripcion='Precios ficticios al productor.', url='https://example.org/encuesta-k4',
                    metodo='descarga', acceso='abierto', licencia='CC BY 4.0', periodicidad='Mensual')
        fuente = FuenteDatos.objects.get(nombre='Encuesta ficticia K4')
        indicadores = self.client.get(reverse('indicadores_observatorio', args=[self.unidad.slug]))
        self.assertContains(indicadores, reverse('editar_registro', args=[
            self.unidad.slug, 'indicador_observatorio', 'nuevo']))
        self.editar('indicador_observatorio', nombre='Precio ficticio de la leche', codigo='k4-precio-leche',
                    definicion='Precio ficticio pagado al productor.', formula='Promedio simple',
                    unidad_medida='USD/litro', fuente='Instituto Ficticio, encuesta', tipo_fuente='registro',
                    url_fuente='https://example.org/encuesta-k4', periodicidad='mensual',
                    desagregacion='Cantón', limitaciones='Muestra ficticia pequeña.', sentido='neutro',
                    territorio_principal='Carchi', fuente_datos=fuente.pk, orden='1', publicado='on')
        indicador = IndicadorObservatorio.objects.get(unidad=self.unidad, codigo='k4-precio-leche')
        self.editar('valor_indicador', padre=indicador.pk, periodo=f'{self.hoy:%Y-%m}',
                    fecha=self.hoy.replace(day=1).isoformat(), territorio='Carchi', valor='0.48',
                    nota='Dato ficticio.')
        return indicador, ValorIndicador.objects.get(indicador=indicador)

    def test_una_serie_con_su_ficha_su_fuente_y_sus_datos_sale_en_el_anexo_de_datos(self):
        indicador, valor = self.serie()
        self.evidencia('BOLETINES', 'DAT-K4-001', subtipo='datos', indicador_id=indicador.pk, valores_ids=[valor.pk],
                       objetivo='Actualizar la serie ficticia.', metodo='Descarga y contraste ficticios.',
                       resultado='Serie al día. Limitaciones: dato provisional.')
        ficha = self.fila('OBS-DATOS', 'Ficha metodológica de las series', 'k4-precio-leche')
        for dato in ('Precio ficticio pagado al productor.', 'Promedio simple', 'USD/litro', 'Muestra ficticia'):
            self.assertIn(dato, ficha)
        self.assertIn('Vigente', self.fila('OBS-DATOS', 'Actualización de las series en el semestre',
                                           'k4-precio-leche'))
        self.assertIn('0,48', self.fila('OBS-DATOS', 'Datos incorporados en el semestre', 'k4-precio-leche'))
        self.assertIn('CC BY 4.0', self.fila('OBS-DATOS', 'Fuentes de datos', 'Encuesta ficticia K4'))
        self.assertIn('Encuesta ficticia K4', self.pdf_del_anexo('OBS-DATOS'))

    def test_un_boletin_publicado_sale_en_el_calendario_de_publicaciones(self):
        indicador, _valor = self.serie()
        calendario = self.client.get(reverse('calendario_observatorio', args=[self.unidad.slug]))
        self.assertContains(calendario, reverse('editar_registro', args=[
            self.unidad.slug, 'publicacion_observatorio', 'nuevo']))
        self.editar('publicacion_observatorio', tipo='boletin', titulo='Boletín ficticio de precios',
                    periodo=f'{self.hoy:%Y-%m}', resumen='Resumen ficticio.', fecha_planificada=self.hoy.isoformat(),
                    estado='publicada', fecha_publicada=self.hoy.isoformat(),
                    enlace='https://example.org/boletin-k4', indicadores=[indicador.pk])
        publicacion = PublicacionObservatorio.objects.get(unidad=self.unidad)
        self.evidencia('BOLETINES', 'BOL-K4-001', subtipo='publicacion', publicacion_id=publicacion.pk,
                       objetivo='Difundir los precios ficticios.', metodo='Revisión de cifras ficticia.',
                       resultado='Boletín publicado a tiempo.')
        fila = self.fila('OBS-BOLETINES', 'Calendario de publicaciones', 'Boletín ficticio de precios')
        for dato in ('Publicada', 'k4-precio-leche', 'Vigente'):
            self.assertIn(dato, fila)
        self.assertIn('Boletín ficticio de precios', self.pdf_del_anexo('OBS-BOLETINES'))

    def test_un_evento_con_sus_participantes_sale_en_el_anexo_de_socializacion(self):
        self.evidencia('EVENTOS', 'EVE-K4-001', titulo='Taller ficticio de socialización', subtipo='socializacion',
                       beneficiario='Productores ficticios', participantes='25', fecha_evento=self.hoy.isoformat(),
                       referencia_acta='Acta ficticia 01', objetivo='Presentar la serie ficticia.',
                       metodo='Lista de asistencia ficticia.', resultado='Acuerdos ficticios de difusión.')
        fila = self.fila('OBS-EVENTOS', 'Eventos realizados', 'Taller ficticio de socialización')
        for dato in ('Productores ficticios', '25', 'Acta ficticia 01', 'Vigente'):
            self.assertIn(dato, fila)
        self.assertIn('Taller ficticio de socialización', self.pdf_del_anexo('OBS-EVENTOS'))

    def test_una_solicitud_atendida_sale_en_la_tabla_de_solicitudes_de_informacion(self):
        solicitante = get_user_model().objects.create_user('solicitante.k4', password='clave-ficticia',
                                                           first_name='Sol', last_name='Solicitante')
        self.client.force_login(solicitante)
        self.client.post(reverse('solicitudes_observatorio', args=[self.unidad.slug]), dict(
            tipo='datos', institucion='Cooperativa ficticia', descripcion='Precios ficticios de 2025 en Carchi.',
            finalidad='Plan ficticio de negocios.'))
        solicitud = SolicitudDatos.objects.get(unidad=self.unidad)
        self.client.force_login(self.cuenta)
        bandeja = self.client.get(reverse('solicitudes_observatorio', args=[self.unidad.slug]))
        self.assertContains(bandeja, reverse('editar_registro', args=[self.unidad.slug, 'solicitud_datos', solicitud.pk]))
        self.editar('solicitud_datos', pk=solicitud.pk, estado='atendida', respuesta='Se envió la serie ficticia.')
        solicitud.refresh_from_db()
        self.assertIsNotNone(solicitud.atendida)
        fila = self.fila('TRANSFERENCIA', 'Solicitudes de información atendidas', 'Cooperativa ficticia')
        self.assertIn('Atendida', fila)
        self.assertIn('Se envió la serie ficticia.', fila)
        self.assertIn('Se envió la serie ficticia.', self.pdf_del_anexo('TRANSFERENCIA'))

    def test_el_observatorio_no_lleva_registro_de_uso_practicas_seguridad_ni_desechos(self):
        codigos = {anexo.exigido.codigo for anexo in self.anexos()}
        for ajeno in ('REGISTRO-USO', 'PRACTICAS-FT02', 'GUIAS', 'PRACTICAS-FT03', 'INDUCCION-SEGURIDAD', 'DESECHOS'):
            self.assertNotIn(ajeno, codigos)
        for propio in ('EQUIPAMIENTO', 'INVENTARIO-CORTE', 'OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS'):
            self.assertIn(propio, codigos)

    def test_el_panel_del_observatorio_registra_sus_equipos_y_su_plan_de_mantenimiento(self):
        claves = [seccion['clave'] for seccion in self.panel('obs_indicadores').context['secciones_navegacion']]
        self.assertIn('recursos', claves)
        self.assertIn('mantenimiento', claves)
        recursos = self.panel('recursos')
        self.assertEqual(recursos.context['vista_gestion'], 'recursos')
        self.assertContains(recursos, 'data-management-view="recursos"')
        equipo = UnidadEquipo.objects.get(pk=self.operar(
            modulo='recursos', entidad='equipo', nombre_catalogo='Servidor ficticio de datos', marca='Marca Ficticia',
            modelo='SRV-1', codigo_unidad='K4SRV01', numero_serie='SERIEK4SRV01', codigo_bien='BIENK4SRV01',
            tipo_bien='BLD', clase_bien='Equipo informático ficticio', custodio='Custodia Ficticia',
            ubicacion_bodega='Sala ficticia', valor_contable='900.00', estado_unidad='disponible',
            criticidad='critico', ubicacion_especifica='Rack ficticio', origen_adquisicion='compra_publica',
            fecha_adquisicion=self.unidad.fecha_inicio.isoformat(), documento_adquisicion='Acta ficticia K4',
            activa='on'))
        self.assertContains(self.panel('mantenimiento'), 'data-agenda-operation-open="plan_mantenimiento"')
        plan = PlanMantenimientoEquipo.objects.get(pk=self.operar(
            modulo='plan_mantenimiento', equipo_id=equipo.pk, tipo='preventivo', frecuencia_dias='180',
            responsable=self.cuenta.pk))
        self.assertIn(plan.nombre, self.fila('EQUIPAMIENTO', 'Plan de mantenimiento vigente', 'K4SRV01'))
        self.assertIn('K4SRV01', self.fila('INVENTARIO-CORTE', 'Equipos informáticos', 'K4SRV01'))
