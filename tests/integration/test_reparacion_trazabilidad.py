from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.forms_reparacion import DiagnosticoIncidenciaForm
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, PiezaEquipo
from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, RepuestoMantenimiento, ServicioReparacionEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.reparacion_equipo import lectura_falla, recomendacion_compra_incidencia, seguimiento_reparacion


class ReparacionTrazableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.usuario = get_user_model().objects.create_user('reparacion-gestor', password='prueba')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de reparación', slug='laboratorio-reparacion-test', dependencia='laboratorios', administrador=cls.usuario, fecha_inicio=date(2024, 1, 1), descripcion='Unidad para probar decisiones de reparación.')
        cls.familia = FamiliaEquipo.objects.create(nombre='Familia electrónica de reparación', slug='familia-reparacion-test')
        cls.modelo = EquiposServicios.objects.create(nombre='Impresora de prueba', codigo='REPAR-MODELO-01', familia=cls.familia)
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='REPAR-ACTIVO-01', equipo=cls.modelo, laboratorio=cls.unidad, fecha_adquisicion=cls.hoy - timedelta(days=90), vida_util_anios=5, garantia_meses=12)
        cls.pieza = PiezaEquipo.objects.create(equipo=cls.modelo, nombre='Sensor térmico', clase='componente')

    def incidencia(self, **kwargs):
        return IncidenciaEquipo.objects.create(equipo=self.equipo, titulo='Sensor inestable', descripcion='No alcanza la temperatura.', tipo='accesorio', reportada_por=self.usuario, **kwargs)

    def diagnostico(self, incidencia=None, **kwargs):
        datos = dict(incidencia=incidencia or self.incidencia(), causa='Sensor abierto en prueba eléctrica.', impacto='Dos prácticas afectadas; existe equipo alternativo.', evaluada_por=self.usuario, garantia_revision='no_cubre', garantia_respaldo='Proveedor excluye la pieza por desgaste, consulta REF-01.', decision='repuesto', pieza=self.pieza, cantidad_componente=Decimal('1'), especificacion_componente='Sensor compatible con el modelo y rango de temperatura.', justificacion_decision='El cuerpo del equipo funciona; cambiar solo el sensor reduce costo y plazo.')
        datos.update(kwargs)
        return DiagnosticoIncidenciaEquipo.objects.create(**datos)

    def test_falla_temprana_con_garantia_no_es_reposicion_automatica(self):
        incidencia = self.incidencia()
        lectura = lectura_falla(self.equipo, self.hoy)
        self.assertTrue(lectura['falla_temprana'])
        self.assertTrue(lectura['garantia_vigente'])
        self.assertIsNone(recomendacion_compra_incidencia(incidencia))

    def test_decision_requiere_revision_real_de_garantia_y_fundamento(self):
        with self.assertRaises(ValidationError) as capturado:
            self.diagnostico(garantia_revision='pendiente', garantia_respaldo='', justificacion_decision='')
        self.assertIn('garantia_revision', capturado.exception.message_dict)
        self.assertIn('justificacion_decision', capturado.exception.message_dict)

    def test_accesorio_exige_nombre_cantidad_y_compatibilidad(self):
        with self.assertRaises(ValidationError) as capturado:
            self.diagnostico(pieza=None, componente='', cantidad_componente=None, especificacion_componente='')
        self.assertIn('componente', capturado.exception.message_dict)
        self.assertIn('cantidad_componente', capturado.exception.message_dict)

    def test_compra_solo_del_componente_con_activo_padre_y_evidencia(self):
        diagnostico = self.diagnostico(cantidad_componente=Decimal('2'), costo_estimado=Decimal('35.50'))
        propuesta = recomendacion_compra_incidencia(diagnostico.incidencia)
        self.assertEqual(propuesta['item'], 'Sensor térmico')
        self.assertEqual(Decimal(propuesta['cantidad']), Decimal('2'))
        self.assertEqual(propuesta['equipo_id'], self.equipo.pk)
        self.assertEqual(propuesta['decision'], 'repuesto')
        self.assertEqual(propuesta['diagnostico_id'], diagnostico.pk)
        self.assertTrue(propuesta['falla_temprana'])

    def test_servicio_interno_necesita_cobertura_por_familia_explicita(self):
        servicio = ServicioReparacionEquipo.objects.create(nombre='Centro informático', alcance='Solo soporte informático.', capacidad_mensual=4)
        otra = FamiliaEquipo.objects.create(nombre='Computadoras de centro de prueba', slug='computadoras-centro-test')
        servicio.familias.add(otra)
        with self.assertRaises(ValidationError) as capturado:
            self.diagnostico(ruta='centro', servicio=servicio)
        self.assertIn('servicio', capturado.exception.message_dict)
        servicio.familias.add(self.familia)
        diagnostico = self.diagnostico(ruta='centro', servicio=servicio)
        self.assertEqual(diagnostico.servicio, servicio)

    def test_garantia_confirmada_e_inventario_no_crean_compra_duplicada(self):
        garantia = self.diagnostico(garantia_revision='cubre', ruta='garantia')
        self.assertIsNone(recomendacion_compra_incidencia(garantia.incidencia))
        inventario = self.diagnostico(fuente_financiamiento='inventario')
        self.assertIsNone(recomendacion_compra_incidencia(inventario.incidencia))

    def test_autogestion_no_equivale_a_revision_ni_autorizacion(self):
        diagnostico = self.diagnostico(fuente_financiamiento='autogestion')
        propuesta = recomendacion_compra_incidencia(diagnostico.incidencia)
        self.assertEqual(propuesta['revision_adquisicion'], 'pendiente')
        diagnostico.revision_adquisicion = 'revisado'
        with self.assertRaises(ValidationError):
            diagnostico.save()

    def test_cada_revision_conserva_el_diagnostico_anterior_en_historial(self):
        diagnostico = self.diagnostico()
        original = EventoCicloVidaEquipo.objects.get(incidencia=diagnostico.incidencia, tipo='diagnostico').descripcion
        diagnostico.causa = 'Segunda revisión: falla del conector.'
        diagnostico.save()
        eventos = EventoCicloVidaEquipo.objects.filter(incidencia=diagnostico.incidencia, tipo='diagnostico')
        self.assertEqual(eventos.count(), 2)
        self.assertTrue(eventos.filter(descripcion=original).exists())

    def test_evaluacion_futura_o_posterior_al_corte_no_se_usa(self):
        with self.assertRaises(ValidationError):
            self.diagnostico(fecha_evaluacion=self.hoy + timedelta(days=1))
        diagnostico = self.diagnostico()
        self.assertIsNone(recomendacion_compra_incidencia(diagnostico.incidencia, hoy=self.hoy - timedelta(days=1)))

    def test_no_se_resuelve_una_reparacion_diagnosticada_sin_prueba_apta(self):
        diagnostico = self.diagnostico()
        incidencia = diagnostico.incidencia
        incidencia.estado = 'resuelta'
        incidencia.solucion = 'Se cambió la pieza.'
        with self.assertRaises(ValidationError):
            incidencia.save()
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, incidencia=incidencia, titulo='Cambio de sensor', tipo='correctivo', fecha_programada=timezone.now(), estado='en_proceso')
        orden.estado = 'completado'
        orden.resultado = 'Sensor cambiado.'
        with self.assertRaises(ValidationError):
            orden.save()
        orden.prueba_funcionamiento = 'Técnico valida temperatura estable en tres ciclos.'
        orden.resultado_operativo = 'apto'
        orden.save()
        incidencia.save()
        self.assertIsNone(recomendacion_compra_incidencia(incidencia))

    def test_orden_completada_no_apta_no_libera_el_equipo(self):
        diagnostico = self.diagnostico()
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, incidencia=diagnostico.incidencia, titulo='Evaluación de sensor', tipo='correctivo', fecha_programada=timezone.now(), estado='en_proceso')
        orden.estado = 'completado'
        orden.resultado = 'La falla persiste.'
        orden.prueba_funcionamiento = 'Temperatura no alcanza rango seguro.'
        orden.resultado_operativo = 'no_apto'
        orden.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'no_disponible')

    def test_repuesto_rechaza_otra_familia_y_cantidades_invalidas(self):
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, titulo='Atención', fecha_programada=timezone.now())
        otro = EquiposServicios.objects.create(nombre='Otro modelo', codigo='REPAR-OTRO-01')
        pieza = PiezaEquipo.objects.create(equipo=otro, nombre='Pieza ajena')
        with self.assertRaises(ValidationError):
            RepuestoMantenimiento.objects.create(mantenimiento=orden, descripcion='Pieza', pieza=pieza)
        with self.assertRaises(ValidationError):
            RepuestoMantenimiento.objects.create(mantenimiento=orden, descripcion='Pieza', cantidad=0)

    def test_repuesto_vincula_pieza_y_conserva_correcciones_en_historial(self):
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, titulo='Atención con repuesto', fecha_programada=timezone.now())
        repuesto = RepuestoMantenimiento.objects.create(mantenimiento=orden, descripcion='Sensor térmico', pieza=self.pieza, cantidad=1, costo_unitario=5, referencia_adquisicion='GAR-01')
        self.assertTrue(self.equipo.eventos_ciclo_vida.filter(tipo='actualizacion', descripcion__contains=orden.codigo).exists())
        repuesto.cantidad = Decimal('2')
        repuesto.referencia_adquisicion = 'GAR-02'
        repuesto.save()
        self.assertEqual(self.equipo.eventos_ciclo_vida.filter(tipo='actualizacion').count(), 2)
        self.assertTrue(self.equipo.eventos_ciclo_vida.filter(descripcion__contains='GAR-01').exists())

    def test_pieza_registrada_en_portal_queda_vinculada_al_equipo(self):
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, titulo='Orden de portal', fecha_programada=timezone.now())
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {'modulo': 'repuesto_mantenimiento', 'mantenimiento_id': orden.pk, 'pieza': self.pieza.pk, 'descripcion': 'Sensor térmico', 'cantidad': '1', 'costo_unitario': '0', 'procedencia': 'garantia', 'referencia_adquisicion': 'GAR-PORTAL-01'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(orden.repuestos.get().pieza, self.pieza)

    def test_cola_informa_demanda_sin_inventar_cobertura_del_centro(self):
        incidencia = self.incidencia(detiene_operacion=True, prioridad='alta')
        diagnostico = self.diagnostico(incidencia=incidencia, fecha_derivacion=self.hoy-timedelta(days=3), respuesta_prevista=self.hoy-timedelta(days=1))
        panel = seguimiento_reparacion(self.unidad)
        self.assertEqual(panel['fallas_tempranas'], 1)
        self.assertEqual(panel['sin_cobertura_interna'], 1)
        self.assertEqual(panel['respuestas_vencidas'], 1)
        self.assertEqual(panel['filas'][0]['diagnostico'], diagnostico)

    def test_formulario_no_admite_pieza_de_otro_modelo(self):
        otro = EquiposServicios.objects.create(nombre='Modelo ajeno', codigo='REPAR-AJENO-02')
        ajena = PiezaEquipo.objects.create(equipo=otro, nombre='Accesorio ajeno')
        formulario = DiagnosticoIncidenciaForm({'pieza': ajena.pk}, incidencia=self.incidencia())
        self.assertFalse(formulario.is_valid())
        self.assertIn('pieza', formulario.errors)

    def test_operacion_diagnostico_no_permite_incidente_de_otra_unidad(self):
        ajeno = get_user_model().objects.create_user('reparacion-ajeno', password='prueba')
        otra = Unidad.objects.create(nombre='Unidad ajena', slug='unidad-ajena-reparacion', dependencia='laboratorios', administrador=ajeno, fecha_inicio=date(2025, 1, 1), descripcion='Ajena')
        equipo = UnidadEquipo.objects.create(codigo_unidad='REPAR-AJENO-03', equipo=self.modelo, laboratorio=otra)
        incidencia = IncidenciaEquipo.objects.create(equipo=equipo, titulo='Falla ajena', descripcion='No accesible.')
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {'modulo': 'diagnostico_equipo', 'incidencia_id': incidencia.pk})
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(DiagnosticoIncidenciaEquipo.objects.exists())

    def test_compartir_equipo_no_permite_editar_registros_de_otra_unidad(self):
        ajeno = get_user_model().objects.create_user('reparacion-compartida-ajeno')
        otra = Unidad.objects.create(nombre='Unidad compartida ajena', slug='unidad-compartida-ajena',
            dependencia='laboratorios', administrador=ajeno, fecha_inicio=date(2025, 1, 1), descripcion='QA')
        self.equipo.laboratorios.add(otra)
        incidencia = IncidenciaEquipo.objects.create(equipo=self.equipo, unidad=otra,
            titulo='Incidencia de otra unidad', descripcion='No se debe modificar.', reportada_por=ajeno)
        orden = MantenimientoEquipo.objects.create(equipo=self.equipo, unidad=otra,
            titulo='Orden de otra unidad', tipo='correctivo', fecha_programada=timezone.now(), estado='planificado')
        self.client.force_login(self.usuario)
        url = reverse('gestion_operacion_accion', args=[self.unidad.slug])
        for datos in (
            dict(modulo='incidencia', registro_id=incidencia.pk, titulo='Cambio ajeno', descripcion='Cambio ajeno'),
            dict(modulo='diagnostico_equipo', incidencia_id=incidencia.pk),
            dict(modulo='mantenimiento', registro_id=orden.pk, equipo_id=self.equipo.pk, titulo='Cambio ajeno'),
            dict(modulo='repuesto_mantenimiento', mantenimiento_id=orden.pk, descripcion='Pieza ajena'),
        ):
            with self.subTest(modulo=datos['modulo']):
                self.assertEqual(self.client.post(url, datos).status_code, 404)
        incidencia.refresh_from_db()
        orden.refresh_from_db()
        self.assertEqual(incidencia.titulo, 'Incidencia de otra unidad')
        self.assertEqual(orden.titulo, 'Orden de otra unidad')
        self.assertFalse(DiagnosticoIncidenciaEquipo.objects.filter(incidencia=incidencia).exists())
        self.assertFalse(orden.repuestos.exists())

    def test_plantillas_muestran_diagnostico_y_componentes_con_datos_reales(self):
        self.diagnostico()
        html = render_to_string('portal/pages/unidades/gestion/includes/reparacion_seguimiento.html', {'unidad': self.unidad, 'seguimiento_reparacion': seguimiento_reparacion(self.unidad), 'puede_operar_mantenimiento': True, 'fecha_hoy_reparacion': self.hoy.isoformat()})
        self.assertIn('Sensor térmico', html)
        self.assertIn('data-agenda-operation-open="diagnostico_equipo"', html)
        self.assertIn('Sin cobertura interna declarada', html)
