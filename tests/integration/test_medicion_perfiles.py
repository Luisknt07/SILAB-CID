"""Fuentes nativas, aprobación atribuida y cálculo del semestre, sin notas inventadas."""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.medicion_metas import registrar_evidencia, registros_de_gestion
from apps.documentos.presentation.medicion_vistas import EvidenciaForm
from apps.gestion_unidades.models.espacios import ResponsableUnidad, EspacioReservable
from apps.gestion_unidades.presentation.reportes_perfiles import dataset_perfil
from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio, ValorIndicador, PublicacionObservatorio
from apps.centros_experimentales.operacion.models.centros import EjeProductivo, CicloProductivo, RegistroProduccion
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta, OrdenProduccion, LoteProducto
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad, ParametroCalidad, ControlCalidad, MedicionCalidad


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class MedicionPerfilesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('revisor-perfiles-qa')
        cls.director = get_user_model().objects.create_superuser('direccion-perfiles-qa', 'direccion@example.invalid', 'clave-qa')
        cls.obs = Unidad.objects.create(nombre='Observatorio QA', slug='observatorio-medicion-qa',
            dependencia='observatorios', descripcion='Ensayo aislado', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.planta = Unidad.objects.create(nombre='Planta QA', slug='planta-medicion-qa',
            dependencia='plantas_piloto', descripcion='Ensayo aislado', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.centro = Unidad.objects.create(nombre='Centro QA', slug='centro-medicion-qa',
            dependencia='centro_experimental', descripcion='Ensayo aislado', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.serie = IndicadorObservatorio.objects.create(unidad=cls.obs, codigo='serie-qa', nombre='Serie QA',
            definicion='Producción por unidad territorial', formula='Suma de los registros de la fuente',
            unidad_medida='kg', fuente='Fuente institucional QA', periodicidad='mensual', publicado=True)
        cls.valor1 = ValorIndicador.objects.create(indicador=cls.serie, periodo='2026-08', fecha=date(2026, 8, 1),
            territorio='Carchi', valor=10, nota='Fuente y corte de agosto QA',
            registrado=datetime(2026, 8, 18, 12, tzinfo=dt_timezone.utc))
        cls.valor2 = ValorIndicador.objects.create(indicador=cls.serie, periodo='2026-09', fecha=date(2026, 9, 1),
            territorio='Carchi', valor=12, nota='Fuente y corte de septiembre QA',
            registrado=datetime(2026, 9, 18, 12, tzinfo=dt_timezone.utc))
        cls.publicacion = PublicacionObservatorio.objects.create(unidad=cls.obs, titulo='Boletín QA',
            periodo='2026-B', resumen='Análisis y límites de la fuente QA', fecha_planificada=date(2026, 9, 20),
            fecha_publicada=date(2026, 9, 20), estado='publicada', enlace='https://example.org/boletin-qa')
        cls.publicacion.indicadores.add(cls.serie)
        cls.parcela = EspacioReservable.objects.create(unidad=cls.centro, nombre='Parcela QA', tipo='parcela')
        cls.eje = EjeProductivo.objects.create(unidad=cls.centro, codigo='eje-qa', titulo='Cultivo QA',
            resumen='Ensayo de seguimiento', que_produce='Producto QA')
        cls.ciclo = CicloProductivo.objects.create(eje=cls.eje, nombre='Ensayo plurianual QA', rubro='Cultivo QA',
            lugar=cls.parcela, inicio=date(2026, 8, 1), fin_previsto=date(2027, 3, 1), estado='en_curso',
            meta=Decimal('500'), unidad_medida='kg')
        cls.registro = RegistroProduccion.objects.create(ciclo=cls.ciclo, fecha=date(2026, 9, 10),
            tipo='pesaje', cantidad=25, unidad_medida='kg', detalle='Muestra y observación identificada QA', registrado_por=cls.actor)
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.planta, usuario=cls.actor, rol='responsable_tecnico')
        cls.producto = Producto.objects.create(unidad=cls.planta, codigo='PROD-MED-QA', nombre='Producto QA', unidad_medida='kg')
        cls.receta = Receta.objects.create(unidad=cls.planta, producto=cls.producto, codigo='REC-MED-QA',
            nombre='Proceso QA', cantidad_base=10, unidad_base='kg', rendimiento_esperado=10)
        cls.orden = OrdenProduccion.objects.create(unidad=cls.planta, receta=cls.receta,
            fecha_inicio=date(2026, 9, 10), fecha_fin=date(2026, 9, 10), estado='terminada',
            responsable=cls.responsable, cantidad_obtenida=10,
            cerrada_en=datetime(2026, 9, 10, 18, tzinfo=dt_timezone.utc),
            detalle_cierre={'consumos': [], 'salidas': [{'cantidad': '10'}], 'cerrada_por': cls.actor.username})
        cls.lote = LoteProducto.objects.create(unidad=cls.planta, producto=cls.producto, orden=cls.orden,
            codigo='LOTE-MED-QA', cantidad_inicial=10, cantidad_disponible=10, fecha_produccion=date(2026, 9, 10))
        cls.plan = PlanCalidad.objects.create(unidad=cls.planta, codigo='CAL-MED-QA', nombre='Calidad QA', producto=cls.producto)
        cls.parametro = ParametroCalidad.objects.create(plan=cls.plan, nombre='Temperatura QA',
            minimo=1, maximo=10, unidad_medida='°C', metodo='Lectura de instrumento QA')
        cls.control = ControlCalidad.objects.create(unidad=cls.planta, plan=cls.plan, lote_producto=cls.lote,
            fecha=datetime(2026, 9, 10, 18, tzinfo=dt_timezone.utc), registrado_por=cls.actor, resultado='conforme')
        cls.medicion = MedicionCalidad.objects.create(control=cls.control, parametro=cls.parametro,
            valor_numerico=5, conforme=True)

    def setUp(self):
        self.inicio, self.fin = date(2026, 8, 17), date(2026, 12, 8)
        self.hoy = date(2026, 10, 17)

    def evidencia(self, unidad, tipo, subtipo, codigo='PERFIL-QA', fecha=None, verificar=True, usuario=None, **detalle):
        return registrar_evidencia(unidad, usuario or self.actor, dict(tipo=tipo, codigo=codigo,
            fecha=fecha or self.hoy, titulo='Resultado ' + codigo, descripcion='Resultado comprobable de ensayo QA',
            responsable=self.actor, enlace='https://example.org/ensayo/' + codigo,
            detalle=dict(subtipo=subtipo, objetivo='Objetivo QA', metodo='Comprobación técnica QA',
                         resultado='Resultado y limitaciones QA', **detalle)), verificar=verificar)

    def lectura(self, unidad):
        return registros_de_gestion(unidad, self.inicio, self.fin)

    def test_publicacion_publicada_no_acredita_sin_revision_tecnica(self):
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 1)
        datos = dataset_perfil('boletines', self.obs, self.inicio, self.fin)
        self.assertEqual(datos['cards'][1][1], 1)

    def test_modificar_titulo_o_metodologia_invalida_revision(self):
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        PublicacionObservatorio.objects.filter(pk=self.publicacion.pk).update(titulo='Otro título')
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)

    def test_dos_actualizaciones_reales_y_guardado_repetido_no_suman(self):
        self.evidencia(self.obs, 'BOLETINES', 'datos', codigo='DATOS-1', fecha=date(2026, 8, 20),
            indicador_id=self.serie.pk, valores_ids=[self.valor1.pk])
        self.evidencia(self.obs, 'BOLETINES', 'datos', codigo='DATOS-2', fecha=date(2026, 9, 20),
            indicador_id=self.serie.pk, valores_ids=[self.valor2.pk])
        self.evidencia(self.obs, 'BOLETINES', 'datos', codigo='DATOS-REPETIDOS',
            indicador_id=self.serie.pk, valores_ids=[self.valor2.pk])
        self.assertEqual(self.lectura(self.obs)['gestion_datos_actualizados'], 2)

    def test_datos_provisionales_o_serie_sin_formula_no_acreditan(self):
        ValorIndicador.objects.filter(pk=self.valor1.pk).update(provisional=True)
        with self.assertRaises(ValidationError):
            self.evidencia(self.obs, 'BOLETINES', 'datos', indicador_id=self.serie.pk, valores_ids=[self.valor1.pk])
        IndicadorObservatorio.objects.filter(pk=self.serie.pk).update(formula='')
        with self.assertRaises(ValidationError):
            self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)

    def test_dato_de_periodo_futuro_no_acredita_una_actualizacion_realizada(self):
        ValorIndicador.objects.filter(pk=self.valor1.pk).update(fecha=date(2027, 1, 1))
        with self.assertRaises(ValidationError):
            self.evidencia(self.obs, 'BOLETINES', 'datos', indicador_id=self.serie.pk, valores_ids=[self.valor1.pk])

    def test_un_director_sin_responsabilidad_tecnica_no_suplanta_al_revisor(self):
        with self.assertRaisesMessage(ValidationError, 'responsable técnico'):
            self.evidencia(self.obs, 'BOLETINES', 'publicacion', usuario=self.director, publicacion_id=self.publicacion.pk)

    def test_huella_enviada_por_cliente_se_recalcula_y_alterar_evidencia_invalida(self):
        e = self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk,
            fuente_nativa_sha256='f' * 64)
        self.assertNotEqual(e.detalle['fuente_nativa_sha256'], 'f' * 64)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(descripcion='Contenido cambiado')
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)

    def test_demostracion_no_acredita(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)

    def test_socializacion_requiere_fecha_asistencia_acta_y_revision(self):
        self.evidencia(self.obs, 'EVENTOS', 'socializacion', participantes=12,
            fecha_evento='2026-10-10', beneficiario='Comunidad QA', referencia_acta='ACTA-QA-1')
        self.assertEqual(self.lectura(self.obs)['gestion_eventos'], 1)
        self.assertEqual(dataset_perfil('eventos', self.obs, self.inicio, self.fin)['cards'][1][1], 1)

    def test_acta_actual_no_acredita_publicacion_de_un_semestre_anterior(self):
        PublicacionObservatorio.objects.filter(pk=self.publicacion.pk).update(fecha_publicada=date(2026, 7, 20))
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)
        reporte = dataset_perfil('boletines', self.obs, self.inicio, self.fin)
        self.assertEqual(reporte['cards'][1][1], 0)
        self.assertEqual(reporte['cards'][2][1], 1)

    def test_acta_actual_no_acredita_socializacion_de_un_semestre_anterior(self):
        self.evidencia(self.obs, 'EVENTOS', 'socializacion', participantes=12,
            fecha_evento='2026-07-10', beneficiario='Comunidad QA', referencia_acta='ACTA-ANTERIOR-QA')
        self.assertEqual(self.lectura(self.obs)['gestion_eventos'], 0)
        self.assertEqual(dataset_perfil('eventos', self.obs, self.inicio, self.fin)['cards'][1][1], 0)

    def test_acta_actual_no_acredita_orden_cerrada_en_un_semestre_anterior(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(
            cerrada_en=datetime(2026, 7, 10, 18, tzinfo=dt_timezone.utc))
        LoteProducto.objects.filter(pk=self.lote.pk).update(fecha_produccion=date(2026, 7, 10))
        self.evidencia(self.planta, 'PRODUCCION', 'produccion', orden_id=self.orden.pk)
        self.assertEqual(self.lectura(self.planta)['gestion_produccion'], 0)
        self.assertEqual(dataset_perfil('produccion', self.planta, self.inicio, self.fin)['cards'][1][1], 0)

    def test_ensayo_en_curso_con_seguimiento_semestre_acredita_sin_cosecha_precoz(self):
        self.evidencia(self.centro, 'ENSAYOS', 'ensayo', ciclo_id=self.ciclo.pk, registros_ids=[self.registro.pk])
        self.assertEqual(self.lectura(self.centro)['gestion_ensayos'], 1)
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.estado, 'en_curso')

    def test_modificar_observacion_del_ensayo_invalida(self):
        self.evidencia(self.centro, 'ENSAYOS', 'ensayo', ciclo_id=self.ciclo.pk, registros_ids=[self.registro.pk])
        RegistroProduccion.objects.filter(pk=self.registro.pk).update(detalle='Observación sustituida')
        self.assertEqual(self.lectura(self.centro)['gestion_ensayos'], 0)

    def test_dos_seguimientos_del_mismo_ciclo_no_crean_dos_ensayos(self):
        self.evidencia(self.centro, 'ENSAYOS', 'ensayo', codigo='ENSAYO-1', ciclo_id=self.ciclo.pk,
            registros_ids=[self.registro.pk])
        registro = RegistroProduccion.objects.create(ciclo=self.ciclo, fecha=date(2026, 10, 10),
            tipo='pesaje', cantidad=30, unidad_medida='kg', detalle='Segunda observación QA', registrado_por=self.actor)
        self.evidencia(self.centro, 'ENSAYOS', 'ensayo', codigo='ENSAYO-2', ciclo_id=self.ciclo.pk,
            registros_ids=[registro.pk])
        self.assertEqual(self.lectura(self.centro)['gestion_ensayos'], 1)

    def test_registro_de_otra_unidad_no_se_puede_vincular(self):
        with self.assertRaises(ValidationError):
            self.evidencia(self.planta, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        PublicacionObservatorio.objects.filter(pk=self.publicacion.pk).update(unidad=self.planta)
        with self.assertRaises(ValidationError):
            self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)

    def test_produccion_y_cobertura_calidad_se_miden_por_lote_real(self):
        self.evidencia(self.planta, 'PRODUCCION', 'produccion', codigo='ORDEN-QA', orden_id=self.orden.pk)
        antes = self.lectura(self.planta)
        self.assertEqual(antes['gestion_produccion'], 1)
        self.assertEqual(antes['mediciones_porcentuales']['CONTROL-CALIDAD']['numerador'], 0)
        self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', codigo='CONTROL-QA', control_id=self.control.pk)
        medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertEqual((medida['numerador'], medida['denominador'], medida['pendiente']), (1, 1, False))

    def test_control_incompleto_y_conformidad_forzada_no_acreditan(self):
        MedicionCalidad.objects.filter(pk=self.medicion.pk).update(valor_numerico=20)
        with self.assertRaisesMessage(ValidationError, 'conformidad'):
            self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', control_id=self.control.pk)

    def test_control_anterior_a_la_produccion_del_lote_no_acredita(self):
        ControlCalidad.objects.filter(pk=self.control.pk).update(
            fecha=datetime(2026, 9, 9, 18, tzinfo=dt_timezone.utc))
        with self.assertRaisesMessage(ValidationError, 'anterior a la producción'):
            self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', control_id=self.control.pk)

    def test_control_de_proceso_no_sustituye_control_de_liberacion(self):
        PlanCalidad.objects.filter(pk=self.plan.pk).update(momento='proceso')
        self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', control_id=self.control.pk)
        medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertEqual((medida['numerador'], medida['denominador']), (0, 1))

    def test_plan_de_calidad_de_otro_producto_no_se_puede_usar(self):
        otro = Producto.objects.create(unidad=self.planta, codigo='OTRO-PROD-QA', nombre='Otro producto QA', unidad_medida='kg')
        PlanCalidad.objects.filter(pk=self.plan.pk).update(producto=otro)
        with self.assertRaisesMessage(ValidationError, 'producto controlado'):
            self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', control_id=self.control.pk)

    def test_lote_nuevo_sin_control_reduce_cobertura_y_no_borra_control_anterior(self):
        self.evidencia(self.planta, 'PRODUCCION', 'control_calidad', control_id=self.control.pk)
        LoteProducto.objects.create(unidad=self.planta, producto=self.producto, orden=self.orden,
            codigo='SEGUNDO-LOTE-QA', cantidad_inicial=5, fecha_produccion=date(2026, 9, 10))
        medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertEqual((medida['numerador'], medida['denominador']), (1, 2))

    def test_cero_produccion_es_medicion_pendiente_no_cien_por_ciento(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='planificada')
        LoteProducto.objects.filter(pk=self.lote.pk).delete()
        medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertEqual(medida['denominador'], 0)
        self.assertTrue(medida['pendiente'])

    def test_cero_produccion_justificada_solo_exime_el_tramo_verificado(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='planificada')
        LoteProducto.objects.filter(pk=self.lote.pk).delete()
        self.evidencia(self.planta, 'PRODUCCION', 'sin_produccion', periodo_desde='2026-08-17',
            periodo_hasta=self.hoy.isoformat(), justificacion_sin_produccion='Parada programada y acta verificadas QA')
        # La exención cubre el día del escenario, no los días posteriores a él.
        with patch('django.utils.timezone.localdate', return_value=self.hoy):
            medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertTrue(medida['no_aplica_verificado'])
        self.assertFalse(medida['pendiente'])
        self.assertEqual(medida['denominador'], 0)
        with patch('django.utils.timezone.localdate', return_value=self.hoy + timedelta(days=1)):
            dia_siguiente = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertFalse(dia_siguiente['no_aplica_verificado'])
        self.assertTrue(dia_siguiente['pendiente'])

    def test_no_se_puede_justificar_cero_cuando_existe_produccion(self):
        with self.assertRaisesMessage(ValidationError, 'Hay producción'):
            self.evidencia(self.planta, 'PRODUCCION', 'sin_produccion', periodo_desde='2026-08-17',
                periodo_hasta=self.hoy.isoformat(), justificacion_sin_produccion='Afirmación errónea QA')

    def test_lote_real_sin_orden_tambien_exige_control(self):
        LoteProducto.objects.filter(pk=self.lote.pk).update(orden=None)
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='planificada')
        medida = self.lectura(self.planta)['mediciones_porcentuales']['CONTROL-CALIDAD']
        self.assertEqual((medida['numerador'], medida['denominador']), (0, 1))
        with self.assertRaises(ValidationError):
            self.evidencia(self.planta, 'PRODUCCION', 'sin_produccion', periodo_desde='2026-08-17',
                periodo_hasta=self.hoy.isoformat(), justificacion_sin_produccion='Omisión incorrecta de lote sin orden QA')

    def test_formulario_y_post_guardan_vinculo_nativo(self):
        form = EvidenciaForm(unidad=self.obs, tipo='BOLETINES', inicio=self.inicio, fin=self.fin)
        self.assertIn('valores_ids', form.fields)
        self.client.force_login(self.actor)
        response = self.client.post(reverse('fuentes_metas_unidad', args=[self.obs.slug]), dict(
            anio=2026, corte='B', tipo='DATOS-ACTUALIZADOS', subtipo='datos', codigo='POST-DATOS-QA',
            fecha='2026-10-17', titulo='Actualización QA', descripcion='Comprobación de fuente y serie QA',
            responsable=self.actor.pk, enlace='https://example.org/post-qa', verificar='on',
            objetivo='Actualizar la serie', metodo='Revisar fuente y cálculo', resultado='Dato incorporado QA',
            indicador_id=self.serie.pk, valores_ids=[self.valor1.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.lectura(self.obs)['gestion_datos_actualizados'], 1)

    def test_pdf_y_html_consumen_mismo_dataset_nativo(self):
        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
        from django.test import RequestFactory
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        request = RequestFactory().get('/', dict(categoria_reporte='boletines', desde='2026-08-17', hasta='2026-12-08'))
        report = build_unit_report(request, self.obs)
        self.assertEqual(report['category'], 'boletines')
        pdf = render_unit_report_pdf(report)
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_apagar_registro_produccion_no_oculta_ordenes_ni_cambia_el_anexo_por_reservas(self):
        from django.test import RequestFactory
        from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
        ConfiguracionOperativaUnidad.objects.update_or_create(unidad=self.planta,
            defaults={'registra_produccion': False})
        self.planta.refresh_from_db()
        request = RequestFactory().get('/', dict(categoria_reporte='produccion',
            desde=self.inicio.isoformat(), hasta=self.fin.isoformat()))
        reporte = build_unit_report(request, self.planta)
        self.assertEqual(reporte['category'], 'produccion')
        self.assertTrue(any(self.orden.codigo in str(fila) for fila in reporte['dataset']['rows']))
        self.assertIn('La capacidad de registrar producción no está habilitada', ' '.join(reporte['dataset']['notes']))

    def test_produccion_sin_capacidad_y_sin_registros_informa_el_vacio(self):
        from django.test import RequestFactory
        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
        vacia = Unidad.objects.create(nombre='Planta sin producción QA', slug='planta-sin-produccion-qa',
            dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))
        request = RequestFactory().get('/', dict(categoria_reporte='produccion',
            desde=self.inicio.isoformat(), hasta=self.fin.isoformat()))
        reporte = build_unit_report(request, vacia)
        self.assertEqual(reporte['category'], 'produccion')
        self.assertEqual(reporte['dataset']['rows'], [])
        self.assertIn('La capacidad de registrar producción no está habilitada', ' '.join(reporte['dataset']['notes']))
        self.assertTrue(render_unit_report_pdf(reporte).startswith(b'%PDF'))

    def test_todos_los_reportes_nativos_generan_pdf_estandar(self):
        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
        from django.test import RequestFactory
        import pymupdf
        for unidad, categoria in ((self.obs, 'boletines'), (self.obs, 'datos-observatorio'),
                (self.obs, 'eventos'), (self.centro, 'ensayos'), (self.planta, 'control-calidad')):
            with self.subTest(categoria=categoria):
                request = RequestFactory().get('/', dict(categoria_reporte=categoria, desde='2026-08-17', hasta='2026-12-08'))
                report = build_unit_report(request, unidad)
                self.assertEqual(report['category'], categoria)
                with pymupdf.open(stream=render_unit_report_pdf(report), filetype='pdf') as pdf:
                    self.assertGreaterEqual(len(pdf), 1)
                    self.assertIn(unidad.nombre, ''.join(p.get_text() for p in pdf))

    def test_sello_de_actor_no_puede_trasladarse_a_otro_usuario(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        RegistroAuditoriaUnidad.objects.filter(unidad=self.obs,
            entidad=EvidenciaGestionUnidad._meta.label, accion='crear').update(usuario=self.director)
        self.assertEqual(self.lectura(self.obs)['gestion_boletines'], 0)

    def catalogo_anexo(self, codigo, fuente):
        from apps.documentos.models.expediente import DocumentoExigido
        padre, _ = DocumentoExigido.objects.get_or_create(codigo='INFORME-SEMESTRAL', defaults=dict(nombre='Informe QA'))
        anexo, _ = DocumentoExigido.objects.get_or_create(codigo=codigo, defaults=dict(nombre=codigo))
        anexo.activo, anexo.origen = True, 'sistema'
        anexo.fuente_reporte, anexo.anexo_de = fuente, padre
        anexo.save()

    def test_adapter_automatico_exige_revision_de_todos_los_nativos(self):
        from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
        from apps.documentos.presentation.calidad_automatica_perfiles import analizar_perfil
        self.catalogo_anexo('OBS-BOLETINES', 'boletines')
        antes = analizar_perfil(ContextoCalidad(self.obs, self.inicio, self.fin), 'OBS-BOLETINES')
        self.assertFalse(antes['automatico'])
        self.assertTrue(any(h['regla'] == 'FUENTES_PERFIL_SIN_REVISION' for h in antes['hallazgos']))
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        despues = analizar_perfil(ContextoCalidad(self.obs, self.inicio, self.fin), 'OBS-BOLETINES')
        self.assertTrue(despues['automatico'])
        self.assertEqual(despues['hallazgos'], [])

    def test_adapter_no_aprueba_catalogo_con_fuente_sustituida(self):
        from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
        from apps.documentos.presentation.calidad_automatica_perfiles import analizar_perfil
        self.catalogo_anexo('OBS-BOLETINES', 'reservas')
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        lectura = analizar_perfil(ContextoCalidad(self.obs, self.inicio, self.fin), 'OBS-BOLETINES')
        self.assertFalse(lectura['automatico'])
        self.assertTrue(any(h['regla'] == 'CONTRATO_PERFIL_MODIFICADO' for h in lectura['hallazgos']))

    def test_adapter_calidad_admite_cero_solo_con_justificacion_verificada(self):
        from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
        from apps.documentos.presentation.calidad_automatica_perfiles import analizar_perfil
        self.catalogo_anexo('PP-CALIDAD', 'control-calidad')
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='planificada')
        LoteProducto.objects.filter(pk=self.lote.pk).delete()
        self.evidencia(self.planta, 'PRODUCCION', 'sin_produccion', periodo_desde='2026-08-17',
            periodo_hasta=self.hoy.isoformat(), justificacion_sin_produccion='Parada sin lotes finalizados QA')
        # El control previo de un lote incongruente queda visible y evita la aprobación automática.
        ControlCalidad.objects.filter(pk=self.control.pk).delete()
        with patch('django.utils.timezone.localdate', return_value=self.hoy):
            lectura = analizar_perfil(ContextoCalidad(self.planta, self.inicio, self.fin), 'PP-CALIDAD')
        self.assertTrue(lectura['automatico'])

    def test_adapter_respeta_tipos_del_catalogo_y_rechaza_cruce_de_perfiles(self):
        from apps.documentos.models.expediente import DocumentoExigido
        from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
        from apps.documentos.presentation.calidad_automatica_perfiles import analizar_perfil
        self.catalogo_anexo('OBS-BOLETINES', 'boletines')
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        DocumentoExigido.objects.filter(codigo='OBS-BOLETINES').update(tipos_unidad=['laboratorios'])
        excluido = analizar_perfil(ContextoCalidad(self.obs, self.inicio, self.fin), 'OBS-BOLETINES')
        self.assertFalse(excluido['automatico'])
        self.assertTrue(any(h['regla'] == 'DOCUMENTO_NO_APLICA_AL_PERFIL' for h in excluido['hallazgos']))
        cruzado = analizar_perfil(ContextoCalidad(self.planta, self.inicio, self.fin), 'OBS-BOLETINES')
        self.assertFalse(cruzado['automatico'])
        self.assertEqual(cruzado['hallazgos'][0]['regla'], 'TIPOLOGIA_DE_FUENTE_INCORRECTA')

    def test_busqueda_sin_coincidencia_vacia_tambien_detalles_y_respaldos(self):
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        for unidad, categoria in ((self.obs, 'boletines'), (self.obs, 'datos-observatorio'),
                (self.centro, 'ensayos'), (self.planta, 'control-calidad')):
            with self.subTest(categoria=categoria):
                reporte = dataset_perfil(categoria, unidad, self.inicio, self.fin,
                    buscar='NO-EXISTE-EN-NINGUNA-FUENTE')
                self.assertEqual(reporte['rows'], [])
                self.assertTrue(all(not t['rows'] for t in reporte['tablas']))

    def test_estado_pendiente_no_arrastra_respaldo_de_publicacion_revisada(self):
        self.evidencia(self.obs, 'BOLETINES', 'publicacion', publicacion_id=self.publicacion.pk)
        reporte = dataset_perfil('boletines', self.obs, self.inicio, self.fin, estado='pendiente')
        self.assertEqual(reporte['rows'], [])
        self.assertTrue(all(not t['rows'] for t in reporte['tablas']))

    def test_cantidad_cero_en_seguimiento_no_se_oculta_como_ausente(self):
        RegistroProduccion.objects.filter(pk=self.registro.pk).update(cantidad=Decimal('0'))
        reporte = dataset_perfil('ensayos', self.centro, self.inicio, self.fin)
        cantidad = reporte['tablas'][0]['rows'][0][3]
        self.assertEqual(Decimal(cantidad), Decimal('0'))

    def test_control_de_lote_demostrativo_no_entra_al_informe_operativo(self):
        LoteProducto.objects.filter(pk=self.lote.pk).update(demostrativo=True)
        reporte = dataset_perfil('control-calidad', self.planta, self.inicio, self.fin)
        self.assertEqual(reporte['rows'], [])
        self.assertTrue(all(not t['rows'] for t in reporte['tablas']))

    def test_aula_mide_actividad_del_intento_y_permite_reutilizar_ejercicios(self):
        from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
        from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
        anterior = datetime(2026, 7, 1, 12, tzinfo=dt_timezone.utc)
        durante = datetime(2026, 9, 1, 12, tzinfo=dt_timezone.utc)
        for nombre, asignado, entregado in (('REUTILIZADO', durante, None),
                ('FUERA-DEL-TRAMO', anterior, None), ('ENTREGADO-EN-EL-TRAMO', anterior, durante)):
            ejercicio = EjercicioAula.objects.create(unidad=self.planta, receta=self.receta,
                nombre=nombre, consigna='Resuelve el ejercicio', creado_por=self.actor)
            EjercicioAula.objects.filter(pk=ejercicio.pk).update(creado_en=anterior)
            intento = IntentoEjercicio.objects.create(ejercicio=ejercicio, estudiante=self.actor)
            IntentoEjercicio.objects.filter(pk=intento.pk).update(creado_en=asignado, entregado_en=entregado)
        reporte = _generic_report('aula', self.planta, self.inicio, self.fin)
        texto = str(reporte['rows'])
        self.assertIn('REUTILIZADO', texto)
        self.assertIn('ENTREGADO-EN-EL-TRAMO', texto)
        self.assertNotIn('FUERA-DEL-TRAMO', texto)
        self.assertEqual(reporte['cards'][1][1], 2)
