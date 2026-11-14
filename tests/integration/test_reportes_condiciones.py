"""El respaldo documental se distingue de un contador operativo o un estado."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import registrar_evidencia
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.reportes_condiciones import (
    acciones_condiciones, pendientes_desecho, reporte_desechos, reporte_seguridad, tablas_condiciones,
)
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import MantenimientoEquipo, RepuestoMantenimiento
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from tests.integration.test_reportes_evidencias import BaseDeReportes


class CondicionesDocumentalesTests(BaseDeReportes):
    def registro_desecho(self, **campos):
        datos = dict(unidad=self.unidad, fecha_generacion=date(2026, 3, 3),
                     clase='peligroso', clave_listado='QA-001', nombre='Solvente',
                     origen='Limpieza', estado_fisico='liquido', cantidad=Decimal('4.5'),
                     unidad_medida='l', envase='Bidón', almacenamiento='Bodega',
                     etiquetado=True, responsable=self.coordinador)
        datos.update(campos)
        return RegistroDesecho.objects.create(**datos)

    def test_entrega_exige_respaldo_licencia_y_responsable(self):
        registro = self.registro_desecho(etapa='entregado', fecha_entrega=date(2026, 3, 4),
            gestor_autorizado='Gestor de prueba', manifiesto='QA-M-01', responsable=None)
        with self.assertRaises(ValidationError) as resultado:
            registro.full_clean()
        self.assertTrue({'licencia_gestor', 'documento', 'responsable'} <= set(resultado.exception.message_dict))
        registro.licencia_gestor = 'QA-LIC-01'
        registro.documento = SimpleUploadedFile('manifiesto.pdf', b'%PDF-1.4', 'application/pdf')
        registro.responsable = self.coordinador
        registro.full_clean()

    def test_desechos_incluye_salida_de_existencias_anteriores_y_no_mezcla_unidades(self):
        self.registro_desecho()
        self.registro_desecho(nombre='Partida kg', cantidad=12, unidad_medida='kg')
        self.registro_desecho(nombre='Entregado de febrero', fecha_generacion=date(2026, 2, 1),
                             etapa='entregado', fecha_entrega=date(2026, 3, 4), cantidad=50)
        self.registro_desecho(nombre='Almacenado de enero', fecha_generacion=date(2026, 1, 1), cantidad=10)
        self.registro_desecho(nombre='Fuera de período', fecha_generacion=date(2026, 2, 1),
                             etapa='entregado', fecha_entrega=date(2026, 2, 4))
        headers, rows, cards, _ = reporte_desechos(self.unidad, self.desde, self.hasta)
        texto = str(rows)
        self.assertIn('Entregado de febrero', texto)
        self.assertIn('Almacenado de enero', texto)
        self.assertNotIn('Fuera de período', texto)
        totales = {c[0]: c[1] for c in cards}
        self.assertEqual(totales['Litros registrados'], '4.5')
        self.assertEqual(totales['Kilogramos registrados'], '12')
        self.assertEqual(totales['Entregados a gestor'], 1)
        self.assertTrue(all(len(row) == len(headers) for row in rows))

    def test_entrega_posterior_no_aparece_cumplida_en_un_corte_anterior(self):
        self.registro_desecho(etapa='entregado', fecha_entrega=date(2026, 4, 1))
        _, rows, cards, _ = reporte_desechos(self.unidad, self.desde, self.hasta)
        self.assertIn('Almacenado al cierre consultado', str(rows))
        self.assertEqual({c[0]: c[1] for c in cards}['Entregados a gestor'], 0)

    def test_archivo_faltante_licencia_almacenamiento_y_observaciones_se_exponen(self):
        registro = self.registro_desecho(etapa='entregado', fecha_entrega=date(2026, 3, 4),
            gestor_autorizado='Gestor de prueba', licencia_gestor='LIC-QA', manifiesto='M-QA',
            documento='privado/manifiesto-qa.pdf', observaciones='Retiro documentado')
        self.assertIn('archivo del manifiesto o acta legible y disponible', pendientes_desecho(registro))
        detalle = tablas_condiciones('desechos', self.unidad, self.desde, self.hasta)
        self.assertIn('LIC-QA', str(detalle))
        self.assertIn('Archivo no disponible: manifiesto-qa.pdf', str(detalle))
        self.assertNotIn('privado/', str(detalle))
        self.assertIn('Retiro documentado', str(detalle))

    def test_ingresos_no_acreditan_protocolo_ni_inspecciones(self):
        RegistroIngreso.objects.create(reserva=self.reserva(), nombre='Persona QA',
                                        ingresa=True, proteccion_verificada=True)
        _, rows, cards, _ = reporte_seguridad(self.unidad, self.desde, self.hasta)
        valores = {c[0]: c[1] for c in cards}
        self.assertEqual(valores['Ingresos registrados'], 1)
        self.assertEqual(valores['Protocolo con archivo'], 'Pendiente')
        self.assertEqual(valores['Inspecciones con archivo'], 0)
        self.assertIn('Persona QA', str(rows))
        self.assertIn('Cargar y validar el protocolo', str(tablas_condiciones(
            'seguridad', self.unidad, self.desde, self.hasta)))

    def test_habilitaciones_tienen_vigencia_origen_y_referencia(self):
        requisito = RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND-QA',
            nombre='Inducción de seguridad', tipo='induccion', obligatorio=True)
        HabilitacionAcceso.objects.create(usuario=self.coordinador, requisito=requisito,
            fecha=self.desde, vence=date(2026, 3, 5), documento='CERT-QA-01', otorgada_por=self.coordinador)
        _, _, cards, _ = reporte_seguridad(self.unidad, self.desde, self.hasta)
        self.assertEqual({c[0]: c[1] for c in cards}['Habilitaciones vigentes'], 0)
        tablas = tablas_condiciones('seguridad', self.unidad, self.desde, self.hasta)
        self.assertIn('CERT-QA-01', str(tablas))
        self.assertIn('Vencida o inactiva', str(tablas))

    def test_inspeccion_historica_sin_archivo_no_se_cuenta_como_respaldada(self):
        exigido, _ = DocumentoExigido.objects.get_or_create(codigo='CHEQUEO-SEGURIDAD', defaults={
            'nombre': 'Lista de chequeo', 'carpeta': 'ejecucion', 'periodicidad': 'mensual', 'activo': False})
        DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido,
            anio=2026, mes=3, estado='validado')
        _, _, cards, _ = reporte_seguridad(self.unidad, self.desde, self.hasta)
        self.assertEqual({c[0]: c[1] for c in cards}['Inspecciones con archivo'], 0)
        tablas = tablas_condiciones('seguridad', self.unidad, self.desde, self.hasta)
        fila = next(fila for fila in tablas[0]['rows'] if fila[0] == exigido.nombre)
        self.assertEqual(fila[2], 'Validado')
        self.assertEqual(fila[3], 'Sin archivo de esta unidad')
        self.assertEqual(fila[-1], 'Sin respaldo disponible')

    @override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
    def test_inspeccion_con_huella_muestra_hallazgos_y_separa_demo_y_no_verificado(self):
        datos = dict(tipo='INSPECCION', codigo='INS-QA-01', fecha=self.desde,
            titulo='Revisión de ventilación', descripcion='Inspección realizada y documentada',
            responsable=self.coordinador, enlace='https://example.org/inspeccion-qa-01',
            detalle=dict(area='Área de impresión', condiciones_revisadas=['infraestructura'],
                sin_hallazgos=False, hallazgos='Filtro por revisar', accion_correctiva='Reemplazar filtro',
                estado_condiciones='observado', estado_accion='pendiente', plazo_accion='2026-03-10'))
        real = registrar_evidencia(self.unidad, self.coordinador, datos, verificar=True)
        with override_settings(MEDICION_SOLO_DEMO=True):
            registrar_evidencia(self.unidad, self.coordinador,
                dict(datos, codigo='INS-QA-02', enlace='https://example.org/inspeccion-qa-02'), verificar=True)
        _, _, cards, _ = reporte_seguridad(self.unidad, self.desde, self.hasta)
        valores = {c[0]: c[1] for c in cards}
        self.assertEqual(valores['Inspecciones verificadas reales'], 1)
        self.assertEqual(valores['Inspecciones de demostración'], 1)
        detalle = tablas_condiciones('seguridad', self.unidad, self.desde, self.hasta)
        self.assertIn('Reemplazar filtro', str(detalle))
        self.assertIn('Demostración; no acredita', str(detalle))
        self.assertIn('INSPECCION', acciones_condiciones('seguridad', self.unidad, self.desde, self.hasta)[0]['url'])
        EvidenciaGestionUnidad.objects.filter(pk=real.pk).update(detalle=dict(datos['detalle'], area='Área alterada'))
        _, _, cards, _ = reporte_seguridad(self.unidad, self.desde, self.hasta)
        self.assertEqual({c[0]: c[1] for c in cards}['Inspecciones verificadas reales'], 0)

    def test_inventario_muestra_saldo_lotes_ubicacion_vencimiento_y_conciliacion(self):
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='INS-COND-QA', nombre='Reactivo QA',
            clasificacion='reactivo', stock_total=12, unidad_medida='kg', ubicacion='Bodega QA')
        LoteConsumible.objects.create(consumible=insumo, codigo='LOTE-QA', cantidad_inicial=12,
            cantidad_actual=10, bodega='Bodega QA', fecha_ingreso=self.desde,
            fecha_vencimiento=date(2026, 3, 5), documento_recepcion='ACTA-QA-01')
        tablas = tablas_condiciones('inventario', self.unidad, self.desde, self.hasta)
        self.assertIn('Diferencia: 2 kg', str(tablas))
        self.assertIn('LOTE-QA', str(tablas))
        self.assertIn('ACTA-QA-01', str(tablas))
        self.assertIn('05/03/2026', str(tablas))


class PeriodoMantenimientoDocumentalTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        tipo = EquiposServicios.objects.create(codigo='EQ-COND-QA', nombre='Equipo de prueba')
        cls.equipo = UnidadEquipo.objects.create(equipo=tipo, laboratorio=cls.unidad,
                                                  codigo_unidad='UE-COND-QA')

    def instante(self, dia, hora=9):
        return timezone.make_aware(datetime(2026, 3, dia, hora))

    def orden(self, codigo, programada, inicio, fin, costo=0):
        orden = MantenimientoEquipo(codigo=codigo, equipo=self.equipo, unidad=self.unidad,
            titulo='Intervención de prueba', estado='completado', fecha_programada=programada,
            fecha_inicio=inicio, fecha_fin=fin, resultado='Resultado QA', costo=costo,
            responsable=self.coordinador)
        MantenimientoEquipo.objects.bulk_create([orden])
        return orden

    def test_periodo_iguala_filas_costos_y_no_incluye_ejecucion_posterior(self):
        vieja = timezone.make_aware(datetime(2026, 2, 10, 9))
        self.orden('QA-ANTERIOR', vieja, vieja, vieja, 100)
        actual = self.orden('QA-ACTUAL', self.instante(4), self.instante(4), self.instante(4, 11), 20)
        self.orden('QA-POSTERIOR', self.instante(5), self.instante(5), self.instante(15), 90)
        RepuestoMantenimiento.objects.create(mantenimiento=actual, descripcion='Repuesto',
                                              cantidad=2, costo_unitario=Decimal('3.00'))
        headers, rows, cards, _ = reporte_mantenimiento(self.unidad, self.desde, self.hasta)
        fila = dict(zip(headers, rows[0]))
        self.assertEqual(fila['Hechos'], '1/2')
        self.assertEqual(fila['Costo USD'], '26.00')
        self.assertEqual({c[0]: c[1] for c in cards}['Costo del período (USD)'], '26.00')

    def test_sin_programacion_no_inventa_cumplimiento_y_muestra_faltantes_inventario(self):
        _, _, cards, _ = reporte_mantenimiento(self.unidad, self.desde, self.hasta)
        self.assertEqual({c[0]: c[1] for c in cards}['Ejecución operativa de órdenes'], 'Sin programación')
        tablas = tablas_condiciones('recursos', self.unidad, self.desde, self.hasta)
        self.assertIn('verificación física', str(tablas))
        self.assertIn('Sin actas de revisión', str(tablas))

    def test_intervalos_superpuestos_no_duplican_dias_de_intervencion(self):
        self.orden('QA-UNO', self.instante(4), self.instante(4), self.instante(4, 13))
        self.orden('QA-DOS', self.instante(4, 11), self.instante(4, 11), self.instante(4, 15))
        headers, rows, _, _ = reporte_mantenimiento(self.unidad, self.desde, self.hasta)
        self.assertEqual(dict(zip(headers, rows[0]))['Días fuera'], '0.25')

    def test_equipo_compartido_no_duplica_costos_ni_incluye_ordenes_de_otra_unidad(self):
        otra = Unidad.objects.create(nombre='Unidad compartida QA', slug='unidad-compartida-condiciones',
                                      dependencia='laboratorios', fecha_inicio=self.desde)
        self.equipo.laboratorios.add(otra)
        self.orden('QA-PROPIA', self.instante(4), self.instante(4), self.instante(4, 11), 25)
        ajena = self.orden('QA-AJENA', self.instante(5), self.instante(5), self.instante(5, 11), 90)
        MantenimientoEquipo.objects.filter(pk=ajena.pk).update(unidad=otra)
        headers, rows, cards, _ = reporte_mantenimiento(self.unidad, self.desde, self.hasta)
        fila = dict(zip(headers, rows[0]))
        self.assertEqual(fila['Hechos'], '1/1')
        self.assertEqual(fila['Costo USD'], '25.00')
        self.assertEqual({c[0]: c[1] for c in cards}['Costo del período (USD)'], '25.00')
