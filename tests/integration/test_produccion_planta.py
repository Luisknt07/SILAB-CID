"""La planta produce: productos, recetas, órdenes, lotes y salidas.

Sobre la Planta Piloto de Lácteos cargada: lo que entra por receta se
descuenta del inventario por lote, lo que sale se convierte en lotes de
producto con vencimiento y control de calidad, y cada lote sale por venta,
transferencia a otra unidad o baja. El módulo es propio de las unidades que
producen; un laboratorio no lo ve.
"""

from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion, Producto, Receta
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.recursos import create_default_modules
from tests.integration.test_laboratorios_institucionales import BaseLaboratorioCargado, _dia_habil


class BasePlantaProduce(BaseLaboratorioCargado):
    slug = 'planta-piloto-lacteos'
    nombre = 'Planta Piloto de Lácteos'
    laboratorio = 'lacteos'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unidad.dependencia = 'plantas_piloto'
        cls.unidad.clasificacion_funcional = 'planta_piloto'
        cls.unidad.save(update_fields=['dependencia', 'clasificacion_funcional'])
        # Las pestañas de la ficha son las de una planta, como en la base real.
        cls.unidad.modulos_contenido.all().delete()
        create_default_modules(cls.unidad)
        FichaContenido.objects.update_or_create(
            codigo='LAC-DOC-CORRIDAS-RESUMEN',
            defaults={
                'unidad': cls.unidad, 'tipo': 'documento', 'titulo': 'Corridas y lotes',
                'descripcion': 'Agregado público de actividad.', 'estado': 'publicada',
                'visibilidad': 'publica',
            },
        )
        FichaContenido.objects.update_or_create(
            codigo='LAC-DOC-CORRIDAS-DETALLE',
            defaults={
                'unidad': cls.unidad, 'tipo': 'documento',
                'titulo': 'Detalle operativo de corridas y lotes',
                'descripcion': 'Detalle interno de actividad.', 'estado': 'publicada',
                'visibilidad': 'interna',
            },
        )
        Usuario = get_user_model()
        cls.coordinacion = Usuario.objects.get(username='coordinacion.lacteos')
        cls.laboratorista = Usuario.objects.get(username='laboratorista.lacteos')
        cls.receta_queso = Receta.objects.get(codigo='LAC-REC-QUESO-100')
        cls.linea = EspacioReservable.objects.get(codigo='LAC-LINEA-PROCESO')
        cls.hoy = timezone.localdate()
        cls.inicio = _dia_habil(cls.hoy + timedelta(days=5))

    def operar(self, usuario=None, unidad=None, **datos):
        self.client.force_login(usuario or self.coordinacion)
        return self.client.post(
            reverse('gestion_operacion_accion', args=[(unidad or self.unidad).slug]), datos
        )

    def planificar_queso(self, usuario=None, **extra):
        datos = {
            'modulo': 'orden_produccion',
            'receta_id': self.receta_queso.pk,
            'factor': '2',
            'fecha_inicio': self.inicio.isoformat(),
            'fecha_fin': (self.inicio + timedelta(days=1)).isoformat(),
            'linea_id': self.linea.pk,
            'origen': 'propia',
            'equipos': [
                str(self._unidad_equipo('LAC-EQP-PAST-01').pk),
                str(self._unidad_equipo('LAC-EQP-TINA-01').pk),
            ],
            'observaciones': 'Corrida de queso fresco para la feria.',
        }
        datos.update(extra)
        return self.operar(usuario=usuario, **datos)

    def orden_de(self, respuesta):
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return OrdenProduccion.objects.get(pk=respuesta.json()['registro']['id'])

    def cerrar_queso(self, orden, **extra):
        insumo = {codigo: Consumible.objects.get(codigo=codigo) for codigo in (
            'LAC-INS-LECHE', 'LAC-INS-CUAJO', 'LAC-INS-CLORURO', 'LAC-INS-SAL',
            'LAC-EMP-FUNDA-QUESO', 'LAC-EMP-ETIQUETA', 'LAC-MAT-PANO',
        )}
        lote = {codigo: LoteConsumible.objects.get(codigo=codigo).pk for codigo in (
            'LAC-LECHE-L1', 'LAC-CUAJO-L1', 'LAC-CLORURO-L1', 'LAC-SAL-L1',
            'LAC-FUNDA-P1', 'LAC-ETIQ-R1',
        )}
        producto = {codigo: Producto.objects.get(codigo=codigo) for codigo in (
            'LAC-PRD-QUESO-FRESCO', 'LAC-PRD-SUERO', 'LAC-PRD-AGUA-LAVADO',
        )}
        datos = {
            'modulo': 'orden_produccion',
            'registro_id': orden.pk,
            'accion_orden': 'cerrar',
            f'consumo_cantidad_{insumo["LAC-INS-LECHE"].pk}': '200',
            f'consumo_lote_{insumo["LAC-INS-LECHE"].pk}': lote['LAC-LECHE-L1'],
            f'consumo_cantidad_{insumo["LAC-INS-CUAJO"].pk}': '20',
            f'consumo_lote_{insumo["LAC-INS-CUAJO"].pk}': lote['LAC-CUAJO-L1'],
            f'consumo_cantidad_{insumo["LAC-INS-CLORURO"].pk}': '40',
            f'consumo_lote_{insumo["LAC-INS-CLORURO"].pk}': lote['LAC-CLORURO-L1'],
            f'consumo_cantidad_{insumo["LAC-INS-SAL"].pk}': '0.8',
            f'consumo_lote_{insumo["LAC-INS-SAL"].pk}': lote['LAC-SAL-L1'],
            f'consumo_cantidad_{insumo["LAC-EMP-FUNDA-QUESO"].pk}': '44',
            f'consumo_lote_{insumo["LAC-EMP-FUNDA-QUESO"].pk}': lote['LAC-FUNDA-P1'],
            f'consumo_cantidad_{insumo["LAC-EMP-ETIQUETA"].pk}': '44',
            f'consumo_lote_{insumo["LAC-EMP-ETIQUETA"].pk}': lote['LAC-ETIQ-R1'],
            f'consumo_cantidad_{insumo["LAC-MAT-PANO"].pk}': '0',
            f'salida_cantidad_{producto["LAC-PRD-QUESO-FRESCO"].pk}': '22',
            f'salida_cantidad_{producto["LAC-PRD-SUERO"].pk}': '170',
            f'salida_cantidad_{producto["LAC-PRD-AGUA-LAVADO"].pk}': '120',
            'ubicacion_lotes': 'Cámara de frío · estantería 1',
            'observaciones_cierre': 'Dos kilos menos por una cuajada blanda en el segundo lote.',
        }
        datos.update(extra)
        return self.operar(**datos)

    def queso_disponible(self):
        """Una corrida cerrada hoy con su lote de queso aprobado por calidad."""
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=2)).isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        lote = LoteProducto.objects.get(orden=orden, producto__codigo='LAC-PRD-QUESO-FRESCO')
        respuesta = self.operar(
            modulo='lote_producto', registro_id=lote.pk, decision_calidad='aprobar',
            ubicacion='Cámara de frío · estantería 1', observaciones='Acidez y humedad dentro del rango.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        lote.refresh_from_db()
        return orden, lote


class LaPlantaDeclaraLoQueProduceTests(BasePlantaProduce):
    def test_la_carga_trae_productos_de_los_cuatro_tipos_y_sus_recetas(self):
        tipos = dict(Producto.objects.filter(unidad=self.unidad).values_list('codigo', 'tipo'))
        self.assertEqual(tipos['LAC-PRD-QUESO-FRESCO'], 'terminado')
        self.assertEqual(tipos['LAC-PRD-CREMA'], 'intermedio')
        self.assertEqual(tipos['LAC-PRD-SUERO'], 'subproducto')
        self.assertEqual(tipos['LAC-PRD-AGUA-LAVADO'], 'residuo')
        self.assertTrue(self.configuracion.registra_produccion)
        self.assertEqual(Receta.objects.filter(unidad=self.unidad, origen='referencia').count(), 11)
        self.assertEqual(Receta.objects.filter(unidad=self.unidad, origen='derivado').count(), 4)
        self.assertEqual(self.receta_queso.insumos.count(), 7)
        # Dos corridas base: doscientos litros de leche dan 24 kg de queso y 170 de suero.
        insumos = {item['consumible'].codigo: item['cantidad'] for item in self.receta_queso.insumos_para(2)}
        salidas = {item['producto'].codigo: item['cantidad'] for item in self.receta_queso.salidas_para(2)}
        self.assertEqual(insumos['LAC-INS-LECHE'], Decimal('200.000'))
        self.assertEqual(insumos['LAC-INS-SAL'], Decimal('0.800'))
        self.assertEqual(salidas['LAC-PRD-QUESO-FRESCO'], Decimal('24.000'))
        self.assertEqual(salidas['LAC-PRD-SUERO'], Decimal('170.000'))
        # La carga se repite sin duplicar nada.
        from django.core.management import call_command
        productos_antes = Producto.objects.filter(unidad=self.unidad).count()
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        self.assertEqual(Producto.objects.filter(unidad=self.unidad).count(), productos_antes)
        self.assertEqual(self.receta_queso.insumos.count(), 7)

    def test_el_panel_muestra_produccion_a_la_planta_y_no_a_un_laboratorio(self):
        self.client.force_login(self.coordinacion)
        # La producción se opera en el ERP de la planta.
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertEqual(panel.status_code, 200)
        secciones = {item['clave']: item['habilitada'] for item in panel.context['secciones_gestion']}
        self.assertTrue(secciones['produccion'])
        self.assertContains(panel, 'data-management-view="produccion"')
        self.assertContains(panel, 'data-content-visibility="interna"')
        self.assertContains(panel, 'data-agenda-operation-form="orden_produccion"')
        self.assertContains(panel, 'data-agenda-operation-form="avance_produccion"')
        self.assertContains(panel, 'Queso fresco por 100 litros de leche')
        # Los permisos y la activación de la producción se administran en la consola.
        consola = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'configuracion'})
        self.assertContains(consola, 'name="permiso_produccion"')
        self.assertContains(consola, 'name="registra_produccion"')
        self.assertEqual(
            [item['titulo'] for item in consola.context['secciones_navegacion']],
            [
                'Tablero', 'Programación', 'Reservas', 'Visitas', 'Prácticas', 'Ejercicios',
                'Activos e inventario', 'Mantenimiento', 'Seguridad', 'Cursos', 'Reportes', 'Configuración y personal',
            ],
        )
        # La formación también pertenece a la planta y conserva el permiso de
        # prácticas; su presencia no habilita producción en los laboratorios.
        self.assertTrue(consola.context['permisos_operativos']['practicas'])
        self.assertContains(consola, 'data-management-target="cursos"')
        cursos = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'cursos'})
        self.assertContains(cursos, 'data-management-view="cursos"')
        tablero = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'indicadores'})
        self.assertContains(tablero, 'data-management-view="indicadores"')
        self.assertNotContains(tablero, 'Visitas a la ficha pública')
        # Los números que vuelven a un formulario van sin la coma decimal del
        # sitio: una corrida y media se edita como 1.500, no como «1,500».
        self.orden_de(self.planificar_queso(factor='1.5'))
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertContains(panel, 'data-field-factor="1.500"')
        self.assertContains(panel, 'data-field-cantidad_base="100"')
        self.assertContains(panel, 'data-base-cantidad="100"')
        self.assertContains(panel, '× 1,5')
        # Un laboratorio no produce: ni pestaña ni formularios.
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin producción', descripcion='Solo reserva.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            slug='laboratorio-sin-produccion', administrador=self.coordinacion,
        )
        panel_lab = self.client.get(reverse('gestion_unidad', args=[laboratorio.slug]))
        self.assertEqual(panel_lab.status_code, 200)
        claves = [item['clave'] for item in panel_lab.context['secciones_gestion']]
        self.assertNotIn('produccion', claves)
        self.assertNotContains(panel_lab, 'data-management-view="produccion"')
        self.assertNotContains(panel_lab, 'data-agenda-operation-form="orden_produccion"')

    def test_la_ficha_publica_muestra_los_productos_sin_residuos_ni_existencias(self):
        pagina = self.client.get(reverse('produccion_publica', args=[self.unidad.slug]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Lo que produce la planta')
        self.assertContains(pagina, 'Queso fresco')
        # Los precios se muestran con la coma decimal del sitio (es-ec).
        self.assertContains(pagina, '$6,50 / kg')
        self.assertContains(pagina, 'Suero de quesería')
        self.assertNotContains(pagina, 'Agua de lavado')
        self.assertContains(
            pagina,
            reverse('ficha_producto_publica', args=[self.unidad.slug, self.receta_queso.producto_id]),
        )


class LaCorridaOcupaLaLineaTests(BasePlantaProduce):
    def test_una_orden_planificada_bloquea_la_linea_y_una_reserva_no_cabe(self):
        orden = self.orden_de(self.planificar_queso())
        self.assertEqual(orden.codigo, f'OP{self.unidad.pk:03d}-{orden.pk:06d}')
        self.assertEqual(orden.estado, 'planificada')
        self.assertEqual(orden.producto.codigo, 'LAC-PRD-QUESO-FRESCO')
        self.assertEqual(orden.cantidad_planificada, Decimal('24.000'))
        self.assertEqual(orden.equipos.count(), 2)
        bloqueo = orden.bloqueo
        self.assertEqual(bloqueo.tipo, 'produccion')
        self.assertEqual(bloqueo.alcance, 'areas')
        self.assertTrue(bloqueo.dia_completo)
        self.assertEqual(list(bloqueo.espacios.all()), [self.linea])
        self.assertEqual(bloqueo.equipos.count(), 2)
        self.assertTrue(bloqueo.bloquea_recursos)
        self.assertFalse(bloqueo.bloquea_servicios)
        self.assertIn(orden.codigo, bloqueo.titulo)

        # Un estudiante que quiere la línea ese día recibe el motivo.
        self.client.force_login(self.estudiante)
        payload = self._payload(
            fecha_inicio=f'{self.inicio.isoformat()}T09:00',
            fecha_fin=f'{self.inicio.isoformat()}T11:00',
            espacios_solicitados=[str(self.linea.pk)],
            incluye_espacio='1',
            unidades_seleccionadas=self._seleccion('LAC-EQP-PAST-01'),
        )
        rechazo = self.client.post(reverse('crear_reserva'), payload)
        self.assertEqual(rechazo.status_code, 400, rechazo.content)
        self.assertIn('Corrida de producción', rechazo.json()['error'])
        self.assertIn(orden.codigo, rechazo.json()['error'])
        # La sala de capacitación no forma parte de la corrida y sigue libre
        # (sin el pasteurizador, que pertenece a la línea).
        sala = EspacioReservable.objects.get(codigo='LAC-SALA-CAPACITACION')
        payload['espacios_solicitados'] = [str(sala.pk)]
        payload['unidades_seleccionadas'] = '[]'
        acepta = self.client.post(reverse('crear_reserva'), payload)
        self.assertEqual(acepta.status_code, 200, acepta.content)

    def test_la_corrida_no_pisa_una_reserva_vigente_de_la_linea(self):
        self.client.force_login(self.estudiante)
        payload = self._payload(
            fecha_inicio=f'{self.inicio.isoformat()}T09:00',
            fecha_fin=f'{self.inicio.isoformat()}T11:00',
            espacios_solicitados=[str(self.linea.pk)],
            incluye_espacio='1',
            unidades_seleccionadas=self._seleccion('LAC-EQP-PAST-01'),
        )
        reserva = self.client.post(reverse('crear_reserva'), payload)
        self.assertEqual(reserva.status_code, 200, reserva.content)
        codigo = Reserva.objects.get(pk=reserva.json()['reserva_id']).codigo_reserva
        respuesta = self.planificar_queso()
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(codigo, respuesta.json()['error'])
        self.assertFalse(OrdenProduccion.objects.filter(unidad=self.unidad).exists())
        # Fuera de esas horas la corrida sí cabe: de 13:00 a 17:00 no hay conflicto.
        cabe = self.planificar_queso(hora_inicio='13:00', hora_fin='17:00')
        orden = self.orden_de(cabe)
        self.assertFalse(orden.bloqueo.dia_completo)
        self.assertEqual(orden.bloqueo.hora_inicio.hour, 13)

    def test_cancelar_la_orden_libera_la_linea(self):
        orden = self.orden_de(self.planificar_queso())
        respuesta = self.operar(
            modulo='orden_produccion', registro_id=orden.pk, accion='desactivar',
            observacion='La leche no llegó.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'cancelada')
        self.assertFalse(orden.bloqueo.activo)
        self.assertIn('La leche no llegó.', orden.observaciones)


class ElCierreDescuentaYCreaLotesTests(BasePlantaProduce):
    def test_iniciar_y_cerrar_descuenta_por_lote_y_crea_lotes_con_vencimiento_y_merma(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=2)).isoformat(),
        ))
        inicio = self.operar(modulo='orden_produccion', registro_id=orden.pk, accion_orden='iniciar')
        self.assertEqual(inicio.status_code, 200, inicio.content)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'en_proceso')

        leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        lote_leche = LoteConsumible.objects.get(codigo='LAC-LECHE-L1')
        self.assertEqual(leche.stock_total, Decimal('400.000'))
        self.assertEqual(lote_leche.cantidad_actual, Decimal('200.000'))

        cierre = self.cerrar_queso(orden)
        self.assertEqual(cierre.status_code, 200, cierre.content)
        self.assertIn('3 lotes', cierre.json()['message'])
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'terminada')
        self.assertIsNotNone(orden.cerrada_en)
        self.assertEqual(orden.cantidad_obtenida, Decimal('22.000'))
        self.assertEqual(orden.merma, Decimal('2.000'))
        self.assertEqual(orden.rendimiento_real_pct, Decimal('91.67'))
        self.assertEqual(len(orden.detalle_cierre['consumos']), 6)
        self.assertEqual(orden.detalle_cierre['cerrada_por'], 'coordinacion.lacteos')

        # La leche salió del lote del tanque, que quedó agotado.
        leche.refresh_from_db()
        lote_leche.refresh_from_db()
        self.assertEqual(leche.stock_total, Decimal('200.000'))
        self.assertEqual(lote_leche.cantidad_actual, Decimal('0.000'))
        self.assertEqual(lote_leche.estado, 'agotado')
        consumos = EntradaInventario.objects.filter(referencia=orden.codigo)
        self.assertEqual(consumos.count(), 6)
        self.assertEqual(set(consumos.values_list('motivo', flat=True)), {'consumo_produccion'})
        self.assertTrue(all(c.clave_idempotencia.startswith('orden-produccion-') for c in consumos))
        self.assertEqual(LoteConsumible.objects.get(codigo='LAC-SAL-L1').cantidad_actual, Decimal('49.200'))

        # Tres lotes: el queso en cuarentena, el suero disponible y el residuo retirado.
        lotes = {lote.producto.codigo: lote for lote in LoteProducto.objects.filter(orden=orden)}
        self.assertEqual(len(lotes), 3)
        queso = lotes['LAC-PRD-QUESO-FRESCO']
        self.assertEqual(queso.codigo, f'LAC-PRD-QUESO-FRESCO-{self.hoy:%y%m%d}-01')
        self.assertEqual(queso.estado, 'cuarentena')
        self.assertEqual(queso.control_calidad, 'pendiente')
        self.assertEqual(queso.cantidad_disponible, Decimal('22.000'))
        self.assertEqual(queso.fecha_vencimiento, self.hoy + timedelta(days=15))
        self.assertEqual(queso.ubicacion, 'Cámara de frío · estantería 1')
        suero = lotes['LAC-PRD-SUERO']
        self.assertEqual(suero.estado, 'disponible')
        self.assertEqual(suero.control_calidad, 'no_aplica')
        self.assertEqual(suero.fecha_vencimiento, self.hoy + timedelta(days=2))
        residuo = lotes['LAC-PRD-AGUA-LAVADO']
        self.assertEqual(residuo.estado, 'retirado')
        self.assertEqual(residuo.cantidad_inicial, Decimal('120.000'))
        self.assertEqual(residuo.cantidad_disponible, Decimal('0.000'))
        self.assertIsNone(residuo.fecha_vencimiento)

        # La línea vuelve a la agenda hoy mismo, aunque la corrida estaba prevista hasta pasado mañana.
        orden.bloqueo.refresh_from_db()
        self.assertEqual(orden.bloqueo.fecha_fin, self.hoy)
        # Cerrar dos veces no descuenta dos veces.
        repetido = self.cerrar_queso(orden)
        self.assertEqual(repetido.status_code, 400)
        self.assertEqual(EntradaInventario.objects.filter(referencia=orden.codigo).count(), 6)

    def test_el_cierre_exige_el_producto_principal_y_un_lote_abierto(self):
        orden = self.orden_de(self.planificar_queso())
        queso = Producto.objects.get(codigo='LAC-PRD-QUESO-FRESCO')
        sin_queso = self.cerrar_queso(orden, **{f'salida_cantidad_{queso.pk}': '0'})
        self.assertEqual(sin_queso.status_code, 400)
        self.assertIn('Queso fresco', sin_queso.json()['error'])
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'planificada')
        self.assertFalse(EntradaInventario.objects.filter(referencia=orden.codigo).exists())
        self.assertFalse(LoteProducto.objects.filter(orden=orden).exists())
        # Un lote en bodega no se descuenta: primero hay que abrirlo.
        leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        en_bodega = LoteConsumible.objects.get(codigo='LAC-LECHE-L2')
        cerrado = self.cerrar_queso(orden, **{f'consumo_lote_{leche.pk}': en_bodega.pk})
        self.assertEqual(cerrado.status_code, 400)
        self.assertIn('LAC-LECHE-L2', cerrado.json()['error'])


class LosLotesSalenTests(BasePlantaProduce):
    def test_el_control_de_calidad_libera_el_lote_y_la_venta_entra_a_finanzas(self):
        orden, lote = self.queso_disponible()
        self.assertEqual(lote.estado, 'disponible')
        self.assertEqual(lote.control_calidad, 'aprobado')
        venta = self.operar(
            modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='10',
            destino='Feria agroproductiva UPEC', referencia='F-001-2026', temperatura_despacho='3',
        )
        self.assertEqual(venta.status_code, 200, venta.content)
        movimiento = MovimientoProducto.objects.get(lote=lote, tipo='venta')
        self.assertEqual(movimiento.precio_unitario, Decimal('6.50'))
        self.assertEqual(movimiento.valor_total, Decimal('65.00'))
        self.assertEqual(movimiento.registrado_por, self.coordinacion)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_disponible, Decimal('12.000'))
        finanzas = movimiento.movimiento_financiero
        self.assertEqual(finanzas.unidad, self.unidad)
        self.assertEqual(finanzas.tipo, 'ingreso')
        self.assertEqual(finanzas.categoria, 'producto')
        self.assertEqual(finanzas.estado, 'confirmado')
        self.assertEqual(finanzas.monto, Decimal('65.00'))
        self.assertEqual(finanzas.referencia, 'F-001-2026')
        # No se vende más de lo que hay.
        exceso = self.operar(modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='100',
                             temperatura_despacho='3')
        self.assertEqual(exceso.status_code, 400)
        self.assertIn('supera', exceso.json()['error'])
        # Una salida registrada no se corrige.
        edicion = self.operar(modulo='movimiento_producto', registro_id=movimiento.pk, lote_id=lote.pk, tipo='venta', cantidad='1')
        self.assertEqual(edicion.status_code, 400)
        self.assertEqual(Producto.objects.get(codigo='LAC-PRD-QUESO-FRESCO').existencia_disponible, Decimal('12.000'))

    def test_un_lote_en_cuarentena_no_se_vende_y_rechazado_se_retira(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=self.hoy.isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        lote = LoteProducto.objects.get(orden=orden, producto__codigo='LAC-PRD-QUESO-FRESCO')
        venta = self.operar(modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='5',
                            temperatura_despacho='3')
        self.assertEqual(venta.status_code, 400)
        self.assertIn('control de calidad', venta.json()['error'])
        rechazo = self.operar(
            modulo='lote_producto', registro_id=lote.pk, decision_calidad='rechazar',
            observaciones='Acidez fuera de rango.',
        )
        self.assertEqual(rechazo.status_code, 200, rechazo.content)
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'retirado')
        self.assertEqual(lote.control_calidad, 'rechazado')
        self.assertEqual(lote.cantidad_disponible, Decimal('0.000'))
        baja = MovimientoProducto.objects.get(lote=lote, tipo='baja')
        self.assertEqual(baja.cantidad, Decimal('22.000'))
        self.assertEqual(baja.motivo, 'Acidez fuera de rango.')

    def test_la_transferencia_entrega_el_producto_como_insumo_de_otra_unidad(self):
        centro = Unidad.objects.create(
            nombre='Centro Experimental San Francisco', descripcion='Produce la leche del hato.',
            fecha_inicio=date(2026, 1, 1), dependencia='centro_experimental',
            slug='centro-experimental-san-francisco-prueba', administrador=self.coordinacion,
        )
        configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=centro)
        configuracion.registra_produccion = True
        configuracion.save(update_fields=['registra_produccion'])
        leche_cruda = Producto.objects.create(
            unidad=centro, codigo='CESF-PRD-LECHE', nombre='Leche cruda del hato', tipo='terminado',
            unidad_medida='litro', precio_venta=Decimal('0.45'), vida_util_dias=3, requiere_frio=True,
        )
        lote = LoteProducto.objects.create(
            unidad=centro, producto=leche_cruda, codigo=f'CESF-PRD-LECHE-{self.hoy:%y%m%d}-01',
            cantidad_inicial=Decimal('300'), cantidad_disponible=Decimal('300'),
            fecha_produccion=self.hoy, fecha_vencimiento=self.hoy + timedelta(days=3),
            estado='disponible', control_calidad='aprobado',
        )
        leche_planta = Consumible.objects.get(codigo='LAC-INS-LECHE')
        self.assertEqual(leche_planta.stock_total, Decimal('400.000'))
        self.assertEqual(leche_planta.lotes_inventario.count(), 2)

        respuesta = self.operar(
            unidad=centro, modulo='movimiento_producto', lote_id=lote.pk, tipo='transferencia',
            cantidad='200', unidad_destino_id=self.unidad.pk, consumible_destino_id=leche_planta.pk,
            referencia='Acta de entrega 12', temperatura_despacho='4',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        movimiento = MovimientoProducto.objects.get(lote=lote, tipo='transferencia')
        self.assertEqual(movimiento.destino, self.unidad.nombre)
        self.assertEqual(movimiento.valor_total, Decimal('0.00'))
        self.assertIsNone(movimiento.movimiento_financiero)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_disponible, Decimal('100.000'))

        # La planta recibe la leche como un lote nuevo en bodega, con el mismo vencimiento.
        entrada = movimiento.entrada_destino
        self.assertEqual(entrada.unidad, self.unidad)
        self.assertEqual(entrada.motivo, 'recepcion')
        self.assertEqual(entrada.cantidad, Decimal('200.000'))
        leche_planta.refresh_from_db()
        self.assertEqual(leche_planta.stock_total, Decimal('600.000'))
        recibido = entrada.lote_inventario
        self.assertEqual(recibido.codigo, f'{lote.codigo}-{self.unidad.pk:03d}')
        self.assertEqual(recibido.estado, 'bodega')
        self.assertEqual(recibido.cantidad_actual, Decimal('200.000'))
        self.assertEqual(recibido.fecha_vencimiento, self.hoy + timedelta(days=3))
        self.assertEqual(recibido.costo_unitario, Decimal('0.45'))
        # Una transferencia va a otra unidad, nunca a la misma.
        misma = self.operar(
            unidad=centro, modulo='movimiento_producto', lote_id=lote.pk, tipo='transferencia',
            cantidad='10', unidad_destino_id=centro.pk, temperatura_despacho='4',
        )
        self.assertEqual(misma.status_code, 400)


class PermisosYReportesTests(BasePlantaProduce):
    def test_el_personal_sin_permiso_de_produccion_la_consulta_sin_operarla(self):
        responsable = ResponsableUnidad.objects.get(unidad=self.unidad, usuario=self.laboratorista)
        permisos = dict(responsable.permisos_operativos or {})
        permisos['produccion'] = False
        responsable.permisos_operativos = permisos
        responsable.save(update_fields=['permisos_operativos'])
        self.assertEqual(self.planificar_queso(usuario=self.laboratorista).status_code, 403)
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        secciones = {item['clave']: item['habilitada'] for item in panel.context['secciones_gestion']}
        # Como en un ERP, el personal de la planta consulta la producción; sin el permiso no la opera.
        self.assertTrue(secciones['produccion'])
        self.assertContains(panel, 'data-management-view="produccion"')
        self.assertNotContains(panel, 'data-agenda-operation-open="orden_produccion"')
        # Con el permiso, la misma persona planifica.
        permisos['produccion'] = True
        responsable.permisos_operativos = permisos
        responsable.save(update_fields=['permisos_operativos'])
        self.assertEqual(self.planificar_queso(usuario=self.laboratorista).status_code, 200)

    def test_el_reporte_de_produccion_sale_en_html_y_hoja_de_calculo_solo_en_la_planta(self):
        orden, lote = self.queso_disponible()
        self.operar(modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='10', temperatura_despacho='3')
        consulta = '?categoria_reporte=produccion'
        html = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]) + consulta)
        self.assertEqual(html.status_code, 200)
        self.assertContains(html, orden.codigo)
        self.assertContains(html, 'Queso fresco')
        self.assertContains(html, '22 kg')
        self.assertContains(html, '91.67%')
        self.assertContains(html, '$65.00')
        xlsx = self.client.get(reverse('gestion_reporte_unidad_xlsx', args=[self.unidad.slug]) + consulta)
        self.assertEqual(xlsx.status_code, 200)
        with ZipFile(BytesIO(xlsx.content)) as libro:
            contenido = b''.join(libro.read(nombre) for nombre in libro.namelist() if nombre.endswith('.xml'))
        self.assertIn(orden.codigo.encode(), contenido)
        # Una categoría ajena al alcance de la unidad se rechaza explícitamente.
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin producción', descripcion='Solo reserva.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            slug='laboratorio-sin-produccion', administrador=self.coordinacion,
        )
        reporte = self.client.get(reverse('gestion_reporte_unidad', args=[laboratorio.slug]) + consulta)
        self.assertEqual(reporte.status_code, 400)
        reporte = self.client.get(reverse('gestion_reporte_unidad', args=[laboratorio.slug]))
        categorias = dict(reporte.context['reporte_gestion']['choices']['categories'])
        self.assertNotIn('produccion', categorias)
