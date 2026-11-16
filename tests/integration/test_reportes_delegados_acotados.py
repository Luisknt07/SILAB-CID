"""Detalle limitado y totales completos también en los reportes delegados."""
import gc
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from weakref import WeakSet

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.formacion.presentation.asignaturas import reporte_asignaturas
from apps.plantas_piloto.operacion.presentation.gestion_produccion import reporte_procesos, reporte_produccion
from apps.gestion_unidades.presentation.reportes_evidencias import reporte_desechos, reporte_equipamiento, reporte_guias, reporte_investigacion, reporte_prestamos, reporte_seguridad, reporte_transferencia
from apps.formacion.models.asignaturas import Asignatura
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ProgramacionReserva, Reserva
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.recursos.models.equipos import EquiposServicios
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, LoteProducto, OrdenProduccion, Producto, Receta
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.recursos.models.desechos import RegistroDesecho
from apps.reservas.models.seguridad import RegistroIngreso
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_reportes_evidencias import BaseDeReportes


def medir_modelos(modelo, funcion):
    gc.collect()
    vivas, pico = WeakSet(), 0
    original = modelo.from_db

    def cargar(cls, *args):
        nonlocal pico
        objeto = original(*args)
        vivas.add(objeto)
        pico = max(pico, len(vivas))
        return objeto

    with patch.object(modelo, 'from_db', new=classmethod(cargar)):
        resultado = funcion()
    return resultado, pico


class EvidenciasDeReservasAcotadasTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for prefijo, proposito in [('TRANS', 'capacitacion'), ('INV', 'investigacion_innovacion')]:
            Reserva.objects.bulk_create([
                Reserva(laboratorio=cls.unidad, usuario=cls.coordinador, fecha=cls.desde + timedelta(days=3),
                    codigo_reserva=f'QA-{prefijo}-{i:04}', hora_inicio=time(9), hora_fin=time(11),
                    proposito_codigo=proposito, tipo_usuario_solicitante='externo', estado='completada')
                for i in range(1201)], batch_size=200)
        SolicitudFabricacion.objects.bulk_create([
            SolicitudFabricacion(unidad=cls.unidad, solicitante=cls.coordinador,
                nombre_proyecto=f'QA-Servicio-{i:04}', fecha_solicitud=cls.desde + timedelta(days=i % 3),
                tipo_trabajo='investigacion', estado='completada')
            for i in range(550)], batch_size=200)

    def test_transferencia_limita_fuentes_ordenadas_sin_recortar_tarjetas(self):
        with CaptureQueriesContext(connection) as consultas:
            (_headers, filas, tarjetas, _estados), pico = medir_modelos(Reserva, lambda: reporte_transferencia(self.unidad, self.desde, self.hasta))
        esperado = list(SolicitudFabricacion.objects.order_by('fecha_solicitud', 'pk').values_list('fecha_solicitud', 'nombre_proyecto'))
        self.assertEqual(len(filas), 501)
        self.assertEqual([f[2] for f in filas], [nombre for _fecha, nombre in esperado[:501]])
        self.assertEqual([t[1] for t in tarjetas], [550, 550, 1201, 1201])
        self.assertLessEqual(pico, 501)
        sql_reservas = [q['sql'] for q in consultas if 'FROM "webcitt_reserva"' in q['sql'] and 'COUNT(' not in q['sql']]
        self.assertTrue(sql_reservas)
        self.assertTrue(all('LIMIT 501' in sql for sql in sql_reservas))

    def test_investigacion_conserva_orden_historico_de_servicios_y_totales(self):
        (_headers, filas, tarjetas, _estados), pico = medir_modelos(Reserva, lambda: reporte_investigacion(self.unidad, self.desde, self.hasta))
        esperado = list(SolicitudFabricacion.objects.order_by('-fecha_solicitud', 'pk').values_list('fecha_solicitud', 'nombre_proyecto'))
        esperado.sort(key=lambda fila: fila[0])
        self.assertEqual([f[2] for f in filas], [nombre for _fecha, nombre in esperado[:501]])
        self.assertEqual([t[1] for t in tarjetas], [1201, 0, 550, 1])
        self.assertLessEqual(pico, 501)
        self.assertEqual(filas[0][0], self.desde.strftime('%d/%m/%Y'))

    def test_filtros_preservan_sus_cifras_y_no_muestran_la_fuente_excluida(self):
        for proveedor, estado, indice_tipo in [(reporte_transferencia, 'reservas', 1), (reporte_investigacion, 'completada', 1)]:
            with self.subTest(proveedor=proveedor.__name__):
                _headers, filas, tarjetas, _estados = proveedor(self.unidad, self.desde, self.hasta, estado)
                self.assertEqual(len(filas), 501)
                self.assertTrue(all(f[indice_tipo] == 'Reserva' for f in filas))
                self.assertIn(550, [t[1] for t in tarjetas])

    def test_empates_mayores_al_limite_tienen_desempate_sql_y_detalle_repetible(self):
        for proveedor, estado, prefijo in [
            (reporte_transferencia, 'reservas', 'TRANS'),
            (reporte_investigacion, 'completada', 'INV'),
        ]:
            with self.subTest(proveedor=proveedor.__name__):
                with CaptureQueriesContext(connection) as consultas:
                    primero = proveedor(self.unidad, self.desde, self.hasta, estado)
                    segundo = proveedor(self.unidad, self.desde, self.hasta, estado)
                self.assertEqual(primero, segundo)
                self.assertEqual([f[2] for f in primero[1]], [f'QA-{prefijo}-{i:04}' for i in range(501)])
                detalles = [q['sql'] for q in consultas if 'FROM "webcitt_reserva"' in q['sql'] and 'LIMIT 501' in q['sql']]
                self.assertEqual(len(detalles), 2)
                self.assertTrue(all('"webcitt_reserva"."id" ASC' in sql.split('ORDER BY')[-1] for sql in detalles))
        with CaptureQueriesContext(connection) as consultas:
            reporte_transferencia(self.unidad, self.desde, self.hasta)
        detalles = [q['sql'] for q in consultas if 'FROM "webcitt_solicitudfabricacion"' in q['sql'] and 'LIMIT 501' in q['sql']]
        self.assertEqual(len(detalles), 1)
        self.assertIn('"webcitt_solicitudfabricacion"."id" ASC', detalles[0].split('ORDER BY')[-1])


class AsignaturasAcotadasTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for letra, nombre in [('Z', 'Zeta'), ('A', 'Alfa')]:
            asignatura = Asignatura.objects.create(unidad=cls.unidad, codigo=letra, nombre=nombre)
            programa = ProgramacionReserva.objects.create(laboratorio=cls.unidad, solicitante=cls.coordinador,
                asignatura=asignatura, fecha_inicio=cls.desde - timedelta(days=2), fecha_fin=cls.hasta,
                dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
            Reserva.objects.bulk_create([
                Reserva(laboratorio=cls.unidad, usuario=cls.coordinador, programacion=programa,
                    codigo_reserva=f'QA-ASIG-{letra}-{i:04}', fecha=cls.desde if i >= 0 else cls.desde + timedelta(days=i),
                    hora_inicio=time(9), hora_fin=time(11), estado='completada')
                for i in range(-2, 625)], batch_size=200)
        programas = ProgramacionReserva.objects.bulk_create([
            ProgramacionReserva(laboratorio=cls.unidad, solicitante=cls.coordinador,
                fecha_inicio=cls.desde, fecha_fin=cls.hasta, dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
            for _ in range(100)], batch_size=200)
        Reserva.objects.bulk_create([
            Reserva(laboratorio=cls.unidad, usuario=cls.coordinador, programacion_id=programa.pk,
                codigo_reserva=f'QA-ASIG-EXTRA-{i:04}', fecha=cls.desde, hora_inicio=time(9), hora_fin=time(11), estado='completada')
            for i, programa in enumerate(programas)], batch_size=200)

    def test_numeracion_global_y_totales_sin_pk_ilimitados_ni_query_por_programa(self):
        with CaptureQueriesContext(connection) as consultas:
            (_headers, filas, tarjetas, _estados), pico = medir_modelos(Reserva, lambda: reporte_asignaturas(self.unidad, self.desde, self.hasta))
        self.assertEqual(len(filas), 501)
        self.assertTrue(filas[0][0].startswith('A · Alfa'))
        self.assertEqual([f[1] for f in filas], list(range(3, 504)))
        self.assertEqual(tarjetas[0][1], 1350)
        # Una reserva completada no equivale a un FT02 ni a un FT03 respaldado.
        self.assertEqual(tarjetas[1], ('Planificaciones con respaldo completo', 0))
        self.assertEqual(tarjetas[2], ('Ejecuciones con respaldo completo', 0))
        self.assertEqual(tarjetas[3], ('Ejecuciones registradas', 1350))
        self.assertEqual(tarjetas[-1][1], 1350)
        self.assertLessEqual(pico, 402)
        self.assertLessEqual(len(consultas), 20)

    def test_busqueda_de_sesion_tardia_conserva_numero_y_filtra_los_pendientes(self):
        _headers, filas, tarjetas, _estados = reporte_asignaturas(self.unidad, self.desde, self.hasta, search='QA-ASIG-Z-0624')
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][1], 627)
        self.assertEqual(tarjetas[0][1], 1)
        # Los pendientes corresponden a las sesiones que cumplen la búsqueda.
        self.assertEqual(tarjetas[-1][1], 1)

    def test_semestre_con_1350_ft02_y_ft03_no_retiene_todos_los_modelos_por_relaciones(self):
        reservas = Reserva.objects.filter(laboratorio=self.unidad, fecha__range=(self.desde, self.hasta))
        planes = PlanificacionPractica.objects.bulk_create([
            PlanificacionPractica(codigo=f'QA-ASIG-FT02-{pk}', unidad=self.unidad, reserva_id=pk, fecha=fecha,
                hora_inicio=time(9), hora_fin=time(11), asignatura='Materiales', docente_tutor='Docente',
                tema='Ensayo de materiales', resultado_aprendizaje='Evalúa las propiedades del material',
                requiere_guia=False, estado='aprobada', creado_por=self.coordinador)
            for pk, fecha in reservas.values_list('pk', 'fecha')
        ], batch_size=200)
        EjecucionPractica.objects.bulk_create([
            EjecucionPractica(planificacion=plan, fecha_ejecucion=plan.fecha,
                hora_inicio_real=time(9), hora_fin_real=time(11), estado='validada', resultado='ejecutada',
                cumplimiento_resultado='si', creado_por=self.coordinador)
            for plan in planes
        ], batch_size=200)
        del planes
        (((reporte, pico_ejecuciones), pico_planes), pico_reservas) = medir_modelos(Reserva,
            lambda: medir_modelos(PlanificacionPractica,
                lambda: medir_modelos(EjecucionPractica,
                    lambda: reporte_asignaturas(self.unidad, self.desde, self.hasta))))
        _headers, filas, tarjetas, _estados = reporte
        self.assertEqual(len(filas), 501)
        self.assertEqual(tarjetas[0], ('Sesiones previstas', 1350))
        self.assertEqual(tarjetas[1], ('Planificaciones con respaldo completo', 0))
        self.assertEqual(tarjetas[2], ('Ejecuciones con respaldo completo', 0))
        self.assertEqual(tarjetas[3], ('Ejecuciones registradas', 1350))
        self.assertLessEqual(pico_reservas, 402)
        self.assertLessEqual(pico_planes, 402)
        self.assertLessEqual(pico_ejecuciones, 402)


class ProduccionAcotadaTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        producto = Producto.objects.create(unidad=cls.unidad, codigo='QA-PRD', nombre='Producto QA', unidad_medida='kg')
        receta = Receta.objects.create(unidad=cls.unidad, producto=producto, codigo='QA-REC', nombre='Receta QA',
            cantidad_base=Decimal('1'), unidad_base='kg', rendimiento_esperado=Decimal('1'))
        insumo = Consumible.objects.create(unidad=cls.unidad, codigo='QA-INS', nombre='Insumo QA', precio_unitario=Decimal('3'), unidad_medida='kg')
        InsumoReceta.objects.create(receta=receta, consumible=insumo, cantidad=Decimal('3'))
        entrada = EntradaInventario.objects.create(unidad=cls.unidad, consumible=insumo,
            tipo='ingreso', cantidad=Decimal('4000'), costo_unitario=Decimal('2'))
        ordenes = OrdenProduccion.objects.bulk_create([
            OrdenProduccion(unidad=cls.unidad, receta=receta, producto=producto, codigo=f'QA-ORD-{i:04}',
                fecha_inicio=cls.desde, fecha_fin=cls.hasta, estado='terminada', cantidad_planificada=1,
                cantidad_obtenida=1, detalle_cierre={'consumos': [{'entrada_id': entrada.pk if i % 2 else None,
                    'consumible_id': insumo.pk, 'consumible': insumo.nombre, 'consumido': '3', 'unidad': 'kg'}]})
            for i in range(1201)], batch_size=200)
        LoteProducto.objects.bulk_create([
            LoteProducto(unidad=cls.unidad, producto=producto, orden=ordenes[-1], codigo=f'QA-LOTE-{i}',
                cantidad_inicial=1, cantidad_disponible=1, fecha_produccion=cls.desde)
            for i in range(3)])

    def test_costos_historicos_completos_se_concilian_por_bloques_y_lotes_sin_n_mas_uno(self):
        from apps.plantas_piloto.operacion.presentation import gestion_produccion
        original = gestion_produccion.costos_de_entradas
        tamanos = []

        def costos(lote):
            tamanos.append(len(lote))
            return original(lote)

        with patch.object(gestion_produccion, 'costos_de_entradas', new=costos), CaptureQueriesContext(connection) as consultas:
            (_headers, filas, tarjetas, _estados), pico = medir_modelos(OrdenProduccion, lambda: reporte_produccion(self.unidad, self.desde, self.hasta))
        self.assertEqual(len(filas), 501)
        self.assertEqual([t[1] for t in tarjetas], [1201, 1201, 3, '$0.00', '$9009.00'])
        self.assertEqual(filas[0][0], 'QA-ORD-1200')
        self.assertEqual(filas[0][10], 3)
        self.assertEqual(sum(tamanos), 1201)
        self.assertLessEqual(max(tamanos), 200)
        self.assertLessEqual(pico, 602)
        self.assertLessEqual(len(consultas), 40)


class Evidencias501Tests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Actividad QA')
        GuiaActividadReserva.objects.bulk_create([
            GuiaActividadReserva(actividad=actividad, titulo=f'Guía QA {i:04}', codigo_guia=f'QA-GUIA-{i:04}',
                es_vigente=True, estado_publicacion='publicada')
            for i in range(550)], batch_size=200)
        reserva = Reserva.objects.create(laboratorio=cls.unidad, usuario=cls.coordinador,
            fecha=cls.desde, hora_inicio=time(9), hora_fin=time(11))
        RegistroIngreso.objects.bulk_create([
            RegistroIngreso(reserva=reserva, nombre=f'Persona QA {i:04}', ingresa=bool(i % 2))
            for i in range(550)], batch_size=200)
        RegistroDesecho.objects.bulk_create([
            RegistroDesecho(unidad=cls.unidad, nombre=f'Desecho QA {i:04}', clase='especial',
                fecha_generacion=cls.desde, cantidad=Decimal('2'), unidad_medida='kg' if i % 2 else 'l',
                etapa='entregado' if i % 3 == 0 else 'almacenado')
            for i in range(550)], batch_size=200)
        modelo = EquiposServicios.objects.create(nombre='Equipo QA')
        equipos = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(laboratorio=cls.unidad, equipo=modelo, codigo_unidad=f'QA-EQP-{i:04}', estado_unidad='disponible')
            for i in range(550)], batch_size=200)
        fecha = timezone.make_aware(datetime.combine(cls.desde, time(10)))
        PrestamoEquipo.objects.bulk_create([
            PrestamoEquipo(unidad=cls.unidad, equipo=equipos[0], codigo=f'QA-PRE-{i:04}',
                fecha_salida=fecha, fecha_retorno_previsto=fecha + timedelta(days=1),
                fecha_retorno_real=fecha + timedelta(days=2) if i % 2 else None,
                estado='devuelto' if i % 2 else 'entregado', tipo='externo' if i % 3 == 0 else 'interno',
                condicion_retorno='observado' if i % 5 == 0 else 'bueno',
                acta='' if i % 4 else 'qa/acta-ficticia.pdf', proposito='Prueba QA')
            for i in range(550)], batch_size=200)
        producto = Producto.objects.create(unidad=cls.unidad, codigo='QA-PROC-PRD', nombre='Producto QA', unidad_medida='kg')
        receta = Receta.objects.create(unidad=cls.unidad, producto=producto, codigo='QA-PROC-REC', nombre='Proceso QA',
            cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        EtapaReceta.objects.bulk_create([
            EtapaReceta(receta=receta, orden=i + 1, nombre=f'Etapa QA {i:04}', duracion_min=1, espera_min=1,
                punto_critico=bool(i % 2), punto_control=not bool(i % 2))
            for i in range(550)], batch_size=200)

    def verificar(self, proveedor, tabla):
        with CaptureQueriesContext(connection) as consultas:
            _headers, filas, tarjetas, _estados = proveedor(self.unidad, self.desde, self.hasta)
        self.assertEqual(len(filas), 501)
        selecciones = [q['sql'] for q in consultas if f'FROM "{tabla}"' in q['sql'] and 'COUNT(' not in q['sql'] and 'SUM(' not in q['sql']]
        self.assertTrue(selecciones)
        self.assertTrue(all('LIMIT 501' in sql for sql in selecciones), selecciones)
        return filas, tarjetas

    def test_guias_preservan_conteos_completos_y_orden(self):
        filas, tarjetas = self.verificar(reporte_guias, 'webcitt_guiaactividadreserva')
        self.assertEqual([t[1] for t in tarjetas], [550, 550, 0, 0])
        self.assertEqual(filas[0][0], 'QA-GUIA-0000')

    def test_seguridad_preserva_ingresos_y_rechazos_completos(self):
        _filas, tarjetas = self.verificar(reporte_seguridad, 'webcitt_registroingreso')
        self.assertEqual([t[1] for t in tarjetas], [275, 275, 0, 0])

    def test_desechos_suma_solo_kg_sin_recortar_las_tarjetas(self):
        _filas, tarjetas = self.verificar(reporte_desechos, 'webcitt_registrodesecho')
        self.assertEqual([t[1] for t in tarjetas[:3]], [550, 184, 366])
        self.assertEqual(Decimal(tarjetas[3][1]), Decimal('550'))

    def test_prestamos_conservan_vencimientos_actas_y_novedades_completos(self):
        _filas, tarjetas = self.verificar(reporte_prestamos, 'webcitt_prestamoequipo')
        self.assertEqual([t[1] for t in tarjetas], [550, 275, 138, 55])
        self.assertEqual(tarjetas[0][2], '184 externos')
        self.assertEqual(tarjetas[1][2], '275 vencidos sin devolver')
        self.assertEqual(tarjetas[3][2], 'sobre 275 devueltos')

    def test_procesos_conservan_tiempo_y_cardinalidad_completos(self):
        filas, tarjetas = self.verificar(reporte_procesos, 'webcitt_etapareceta')
        self.assertEqual([t[1] for t in tarjetas], [1, 550, '18.3', 275, 275])
        self.assertEqual([f[1] for f in filas], list(range(1, 502)))

    def test_equipamiento_conserva_media_y_conteo_de_todos_los_activos(self):
        _headers, filas, tarjetas, _estados = reporte_equipamiento(self.unidad, self.desde, self.hasta)
        self.assertEqual(len(filas), 501)
        self.assertEqual([t[1] for t in tarjetas], [550, '100.0 %', 0, 0])
        self.assertEqual(filas[0][0], 'QA-EQP-0000')

    def test_suma_de_tiempos_no_desborda_una_fila_historica_de_32_bits(self):
        EtapaReceta.objects.filter(orden=1).update(duracion_min=2147483647, espera_min=2147483647)
        _headers, _filas, tarjetas, _estados = reporte_procesos(self.unidad, self.desde, self.hasta)
        self.assertEqual(tarjetas[2][1], f'{(2147483647 * 2 + 549 * 2) / 60:.1f}')
