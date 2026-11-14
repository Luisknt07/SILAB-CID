"""Inversión: antecedente operativo, ausencia de compras y revisión motivada."""
from datetime import date, datetime, time
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import (
    DocumentoExigido, DocumentoExpediente, PoliticaDeCalidad,
)
from apps.documentos.presentation.evaluacion_cierre import VERSION
from apps.documentos.presentation.expediente_archivos import (
    identidad_documental, registrar_integridad_documental,
)
from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso
from tests.integration.utiles import pdf_legible_prueba


@override_settings(MEDICION_SOLO_DEMO=False, MEDICION_METAS_HABILITADA=True)
class PriorizacionComprasTests(TestCase):
    hoy = date(2026, 10, 18)

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-priorizacion-compras-')
        self.addCleanup(carpeta.cleanup)
        ajuste = override_settings(MEDIA_ROOT=carpeta.name)
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        self.actor = get_user_model().objects.create_superuser('priorizacion-direccion', password=None)
        self.unidad = Unidad.objects.create(nombre='Laboratorio de aprovechamiento', slug='priorizacion-compras',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2020, 1, 1))
        self.exigidos = {}
        for codigo, fuente, periodicidad in (
                ('PLAN-COMPRAS-ANUAL', 'compras', 'anual'),
                ('PLANIFICACION', 'planificacion', 'semestral'),
                ('INFORME-SEMESTRAL', 'informe', 'semestral'),
                ('REGISTRO-USO', 'reservas', 'semestral')):
            self.exigidos[codigo], _ = DocumentoExigido.objects.get_or_create(codigo=codigo,
                defaults=dict(nombre=codigo, fuente_reporte=fuente, periodicidad=periodicidad,
                              requiere_firma=codigo != 'REGISTRO-USO', carpeta='planeacion'))
        self.exigidos['REGISTRO-USO'].anexo_de = self.exigidos['INFORME-SEMESTRAL']
        self.exigidos['REGISTRO-USO'].save()
        self.compras = DocumentoExpediente.objects.create(unidad=self.unidad,
            exigido=self.exigidos['PLAN-COMPRAS-ANUAL'], anio=2026)
        self.contenido = dict(compras=[dict(item='Equipo para la programación del siguiente año')])

    def entrega(self, codigo, *, anio=2026, corte='A', nota=100, unidad=None):
        unidad = unidad or self.unidad
        recurso = Recurso.objects.create(unidad=unidad, nombre=f'{codigo} {anio}-{corte}',
            archivo=ContentFile(pdf_legible_prueba(f'{unidad.slug}: {codigo} {anio}-{corte}'), name='antecedente.pdf'))
        fecha = timezone.make_aware(datetime.combine(
            date(anio, 7, 1) if corte == 'A' else date(anio + 1, 1, 1), time(10)))
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=self.exigidos[codigo],
            anio=anio, corte=corte, version=1, recurso=recurso, estado='validado',
            firma_verificada=True, evaluacion=nota, evaluacion_version=1,
            evaluado_por=self.actor, validado_en=fecha, evaluado_en=fecha)
        registrar_integridad_documental(documento, self.actor,
            dict(identidad_documental(documento), sha256=recurso.hash_sha256,
                 director_revisado=True, declaracion_unidad=True), etapa='evaluar')
        RegistroAuditoriaUnidad.objects.filter(unidad=unidad, objeto_id=str(documento.pk),
            entidad=documento._meta.label, descripcion='integridad_documental:evaluar').update(creado_en=fecha)
        if codigo == 'PLANIFICACION':
            # El antecedente tiene una conformidad objetiva persistida de
            # esta versión; la cifra histórica por sí sola nunca la concede.
            self.control(documento, fecha)
        return documento

    def antecedente(self, porcentaje=70, *, anio=2026, corte='A', unidad=None, nota_final=None):
        unidad = unidad or self.unidad
        plan = self.entrega('PLANIFICACION', anio=anio, corte=corte, unidad=unidad)
        cierre = self.entrega('INFORME-SEMESTRAL', anio=anio, corte=corte, unidad=unidad,
                             nota=porcentaje if nota_final is None else nota_final)
        anexo = self.entrega('REGISTRO-USO', anio=anio, corte=corte, unidad=unidad)
        captura = dict(metodo=VERSION, version=cierre.version, recurso=cierre.recurso_id,
            sha256=cierre.recurso.hash_sha256, congelado=True, nota=porcentaje,
            plan=dict(documento=plan.pk, version=plan.version, recurso=plan.recurso_id),
            plan_aprobado=True, completo=True, demostracion=False,
            filas=[dict(codigo='PRACTICAS', porcentaje=porcentaje, exigible=True, registrado=1,
                        pendiente=False, definida=True)],
            anexos=[dict(documento=anexo.pk, version=anexo.version,
                         recurso=anexo.recurso_id, sha256=anexo.recurso.hash_sha256)])
        registro = RegistroAuditoriaUnidad.objects.create(unidad=unidad, usuario=self.actor,
            accion='enviar', entidad=cierre._meta.label, objeto_id=str(cierre.pk),
            descripcion='Cálculo y evidencias del cierre de la prueba aislada', datos_nuevos=captura)
        RegistroAuditoriaUnidad.objects.filter(pk=registro.pk).update(creado_en=cierre.validado_en)
        # Las variaciones de la captura conservan la fecha del antecedente;
        # guardar la instancia no debe restaurar la fecha real de la prueba.
        registro.refresh_from_db(fields=['creado_en'])
        return plan, cierre, anexo, registro

    def lectura(self, **kwargs):
        return analizar_priorizacion(self.compras, self.contenido, hoy=kwargs.pop('hoy', self.hoy), **kwargs)

    def enviado(self, fecha=None):
        self.compras.estado = 'validado'
        self.compras.validado_en = fecha or timezone.make_aware(datetime(2026, 7, 2, 12))
        self.compras.save()

    def control(self, documento, fecha, *, correspondencia=False):
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        from apps.documentos.presentation.automatizacion_documental import METODO, _configuracion
        control, _ = ControlAutomaticoDocumento.objects.update_or_create(documento=documento, defaults=dict(
            metodo=METODO, version_documento=documento.version, recurso=documento.recurso,
            sha256=documento.recurso.hash_sha256, estado='automatico', aplicado=True, nota=100,
            comprobado_en=fecha, resumen=dict(configuracion_sha256=_configuracion(documento),
                correspondencia_automatica=correspondencia, manual_preservada=False,
                conformidad_documental=dict(tipo='planificacion', alcance='conformidad_documental'))))
        return control

    def test_sin_compras_justificadas_no_penaliza_ni_exige_historial(self):
        self.contenido = dict(compras=[], sin_compras_justificacion='<p>Inventario suficiente y operativo.</p>')
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'sin_solicitud')
        self.assertFalse(datos['requiere_revision'])
        self.assertFalse(datos['afecta_conformidad'])
        self.assertFalse(datos['autoriza_fondos'])
        self.assertIsNone(datos['porcentaje'])

    def test_sin_compras_y_sin_justificacion_no_declara_conformidad(self):
        self.contenido = dict(compras=[], sin_compras_justificacion='<p>&nbsp;</p>')
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_pac_por_areas_revisa_sustento_sin_exigir_ensayos_globales_retirados(self):
        self.contenido = dict(pac_version=2, compras=[dict(item='Equipo para el área de análisis')])
        with patch('apps.documentos.presentation.priorizacion_compras._periodo_anterior',
                   side_effect=AssertionError('El esquema nuevo conserva el diagnóstico por áreas.')):
            datos = self.lectura()
        self.assertEqual(datos['estado'], 'revision_tecnica')
        self.assertEqual(datos['metodo'], 'diagnostico_areas')
        self.assertIsNone(datos['umbral'])
        self.assertFalse(datos['autoriza_fondos'])
        self.assertFalse(datos['afecta_conformidad'])
        self.assertTrue(datos['requiere_revision'])

    def test_fila_de_categoria_inicial_no_se_interpreta_como_solicitud_de_inversion(self):
        self.contenido = dict(compras=[dict(categoria='equipos')],
            sin_compras_justificacion='<p>El inventario actual cubre las necesidades del año.</p>')
        self.assertEqual(self.lectura()['estado'], 'sin_solicitud')

    def test_tabla_malformada_no_se_convierte_en_declaracion_de_no_compras(self):
        self.contenido = dict(compras='tabla inválida',
            sin_compras_justificacion='<p>El inventario actual cubre las necesidades del año.</p>')
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_setenta_con_plan_y_cierre_congelado_es_antecedente_favorable(self):
        plan, cierre, _, _ = self.antecedente(70)
        datos = self.lectura()
        self.assertEqual((datos['estado'], datos['porcentaje'], datos['umbral']), ('favorable', 70, 70))
        self.assertEqual(datos['periodo']['etiqueta'], '2026-A')
        self.assertEqual(datos['plan']['documento'], plan.pk)
        self.assertEqual(datos['cierre']['documento'], cierre.pk)
        self.assertFalse(datos['requiere_revision'])
        self.assertTrue(datos['huellas']['cierre_archivado_sha256'])
        for accion in datos['acciones']:
            self.assertEqual(resolve(accion['url'].split('?')[0]).url_name, 'gestion_expediente_unidad')

    def test_sesenta_y_nueve_exige_mejora_sin_rebajar_nota_del_plan(self):
        plan, cierre, _, _ = self.antecedente(69)
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'condicionada_mejora')
        self.assertEqual(datos['porcentaje'], 69)
        plan.refresh_from_db()
        cierre.refresh_from_db()
        self.compras.refresh_from_db()
        self.assertEqual((plan.evaluacion, cierre.evaluacion, self.compras.evaluacion), (100, 69, None))

    def test_plan_con_nota_antigua_sin_conformidad_no_prioriza(self):
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        plan, _, _, _ = self.antecedente(100)
        ControlAutomaticoDocumento.objects.filter(documento=plan).delete()
        DocumentoExpediente.objects.filter(pk=plan.pk).update(evaluacion=80)
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertFalse(datos['plan']['conforme'])
        self.assertIsNone(datos['plan']['porcentaje'])
        plan.refresh_from_db()
        self.assertEqual(plan.evaluacion, 80)

    def test_nota_historica_baja_no_rebaja_la_conformidad_automatica_del_plan(self):
        plan, _, _, _ = self.antecedente(70)
        DocumentoExpediente.objects.filter(pk=plan.pk).update(evaluacion=30, entregado_tarde=True)
        datos = self.lectura()
        self.assertEqual((datos['estado'], datos['plan']['porcentaje']), ('favorable', 100))
        plan.refresh_from_db()
        self.assertEqual(plan.evaluacion, 30)

    def test_marcos_distintos_no_se_combinan_aunque_las_fechas_coincidan(self):
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        plan, _, _, _ = self.antecedente(70)
        fecha = ControlAutomaticoDocumento.objects.get(documento=plan).comprobado_en
        plan.marco_periodo = 'academico_legacy'
        plan.tramo_inicio, plan.tramo_fin = date(2026, 1, 1), date(2026, 6, 30)
        plan.save(update_fields=['marco_periodo', 'tramo_inicio', 'tramo_fin'])
        self.control(plan, fecha)
        datos = self.lectura()
        self.assertTrue(datos['plan']['conforme'])
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertTrue(any('marcos de período distintos' in m for m in datos['motivos']))

    def test_usa_umbral_configurado_en_lugar_de_un_setenta_fijo(self):
        PoliticaDeCalidad.objects.update_or_create(pk=1, defaults=dict(minimo_cumplimiento=80))
        self.antecedente(75)
        datos = self.lectura()
        self.assertEqual((datos['estado'], datos['umbral']), ('condicionada_mejora', 80))

    def test_falta_de_cierre_no_equivale_a_cero_ni_a_antecedente_favorable(self):
        self.entrega('PLANIFICACION')
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['porcentaje'])

    def test_calificacion_humana_sin_medicion_archivada_no_acredita_desempeno(self):
        self.entrega('PLANIFICACION')
        self.entrega('INFORME-SEMESTRAL')
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_no_busca_un_cierre_viejo_bueno_si_falta_el_ultimo(self):
        self.antecedente(100, anio=2025, corte='B')
        datos = self.lectura()
        self.assertEqual(datos['periodo']['etiqueta'], '2026-A')
        self.assertEqual(datos['estado'], 'por_justificar')

    def test_cierre_del_semestre_futuro_no_compensa_un_cierre_bajo(self):
        self.antecedente(69)
        self.antecedente(100, anio=2026, corte='B')
        datos = self.lectura()
        self.assertEqual((datos['periodo']['etiqueta'], datos['porcentaje']), ('2026-A', 69))

    def test_compras_en_mayo_usa_b_anterior_no_exige_a_o_b_del_futuro(self):
        self.antecedente(70, anio=2025, corte='B')
        datos = self.lectura(hoy=date(2026, 5, 15))
        self.assertEqual((datos['periodo']['etiqueta'], datos['estado']), ('2025-B', 'favorable'))

    def test_un_plan_historico_no_se_apoya_en_resultados_de_anios_posteriores(self):
        self.compras.anio = 2025
        self.compras.save()
        self.antecedente(70, anio=2025, corte='B')
        self.antecedente(100, anio=2026, corte='A')
        datos = self.lectura()
        self.assertEqual(datos['periodo']['etiqueta'], '2025-B')

    def test_calendario_academico_no_redefine_el_antecedente_de_gestion(self):
        self.antecedente(70)
        cortes = {'A': (date(2026, 3, 9), date(2026, 7, 10)),
                  'B': (date(2026, 8, 17), date(2026, 12, 8))}
        with patch('apps.documentos.presentation.expediente.cortes_academicos_del_anio', return_value=cortes):
            datos = self.lectura()
        self.assertEqual((datos['periodo']['inicio'], datos['periodo']['fin']), ('2026-01-01', '2026-06-30'))

    def test_el_resultado_de_otra_unidad_nunca_se_utiliza(self):
        otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-priorizacion', dependencia='laboratorios',
                                     administrador=self.actor, fecha_inicio=date(2020, 1, 1))
        self.antecedente(100, unidad=otra)
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['plan'])
        self.assertIsNone(datos['cierre'])

    def test_nueva_unidad_puede_argumentar_habilitacion_sin_inventar_historial(self):
        self.unidad.fecha_inicio = date(2026, 9, 1)
        self.unidad.save()
        self.contenido.update(fundamento_inversion='inicio',
            justificacion_inversion='<p>Estación mínima y capacitación para abrir el servicio de fabricación.</p>')
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'habilitacion_inicial')
        self.assertTrue(datos['requiere_revision'])
        self.assertFalse(datos['autoriza_fondos'])
        self.assertIsNone(datos['porcentaje'])

    def test_capacidad_seguridad_y_recuperacion_son_revision_no_aprobacion(self):
        self.antecedente(40)
        esperados = {'capacidad': 'capacidad_limitada', 'seguridad': 'continuidad_seguridad',
                     'recuperacion': 'recuperacion'}
        for fundamento, estado in esperados.items():
            with self.subTest(fundamento=fundamento):
                self.contenido.update(fundamento_inversion=fundamento,
                    justificacion_inversion='La reparación indispensable permite retomar las actividades programadas.')
                datos = self.lectura()
                self.assertEqual((datos['estado'], datos['porcentaje']), (estado, 40))
                self.assertTrue(datos['requiere_revision'])
                self.assertFalse(datos['autoriza_fondos'])

    def test_continuidad_ordinaria_no_se_convierte_en_excepcion_de_seguridad(self):
        self.antecedente(40)
        self.contenido.update(fundamento_inversion='continuidad',
            justificacion_inversion='Se solicita ampliar la capacidad de trabajo del siguiente año.')
        self.assertEqual(self.lectura()['estado'], 'condicionada_mejora')

    def test_marcar_excepcion_sin_argumento_no_borra_la_baja_ejecucion(self):
        self.antecedente(40)
        self.contenido['fundamento_inversion'] = 'seguridad'
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'condicionada_mejora')
        self.assertTrue(any('justificación' in m for m in datos['motivos']))

    def test_una_nota_documental_alta_no_sustituye_las_metas_congeladas(self):
        self.antecedente(40, nota_final=100)
        datos = self.lectura()
        self.assertEqual((datos['estado'], datos['porcentaje']), ('condicionada_mejora', 40))

    def test_la_nota_final_inferior_tambien_se_conserva(self):
        self.antecedente(90, nota_final=60)
        self.assertEqual(self.lectura()['porcentaje'], 60)

    def test_versiones_de_plan_cierre_y_anexo_no_se_confunden(self):
        plan, cierre, anexo, _ = self.antecedente(100)
        for documento in (plan, cierre, anexo):
            with self.subTest(codigo=documento.exigido.codigo):
                DocumentoExpediente.objects.filter(pk=documento.pk).update(version=2)
                datos = self.lectura()
                self.assertNotEqual(datos['estado'], 'favorable')
                self.assertIsNone(datos['porcentaje'])
                DocumentoExpediente.objects.filter(pk=documento.pk).update(version=1)

    def test_captura_sintetica_nunca_acredita_desempeno(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['demostracion'] = True
        registro.save()
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['porcentaje'])

    @override_settings(MEDICION_SOLO_DEMO=True)
    def test_contexto_de_prueba_nunca_emite_antecedente_favorable(self):
        self.antecedente(100)
        self.assertNotEqual(self.lectura()['estado'], 'favorable')

    def test_correspondencia_sin_comprobar_no_prioriza(self):
        _, cierre, _, _ = self.antecedente(100)
        RegistroAuditoriaUnidad.objects.filter(objeto_id=str(cierre.pk),
            descripcion__startswith='integridad_documental:').delete()
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_cifra_congelada_inconsistente_no_prioriza(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['nota'] = 70
        registro.save()
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_recurso_de_respaldo_retirado_necesita_revision(self):
        _, _, anexo, _ = self.antecedente(100)
        Recurso.objects.filter(pk=anexo.recurso_id).update(activo=False)
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_controles_y_capacitacion_cumplidos_no_compensan_practicas_sin_ejecucion(self):
        _, _, _, registro = self.antecedente(75)
        registro.datos_nuevos['filas'] = [
            dict(codigo=codigo, porcentaje=porcentaje, exigible=True, pendiente=False, definida=True)
            for codigo, porcentaje in (('INVENTARIO', 100), ('CAPACITACION', 100),
                ('SEGURIDAD', 100), ('PRACTICAS', 0))]
        registro.save()
        datos = self.lectura()
        self.assertEqual(datos['porcentaje'], 75)
        self.assertEqual(datos['estado'], 'condicionada_mejora')
        self.assertFalse(datos['actividad_principal']['cumple'])

    def test_cien_por_ciento_de_registros_sin_sesiones_no_acredita_uso(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['filas'] = [dict(codigo='USO', porcentaje=100,
            registrado=0, exigible=True, pendiente=False, definida=True)]
        registro.save()
        self.assertEqual(self.lectura()['estado'], 'condicionada_mejora')

    def test_cobertura_de_uso_exige_numerador_positivo_y_no_solo_un_porcentaje(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['filas'] = [dict(codigo='USO', porcentaje=100,
            registrado=3, exigible=True, pendiente=False, definida=True)]
        registro.save()
        self.assertEqual(self.lectura()['estado'], 'favorable')

    def test_planificar_practicas_sin_ejecucion_no_es_actividad_principal(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['filas'] = [dict(codigo='PRACTICAS-PLAN', porcentaje=100,
            registrado=2, exigible=True, pendiente=False, definida=True)]
        registro.save()
        self.assertEqual(self.lectura()['estado'], 'condicionada_mejora')

    def test_no_impone_investigacion_o_practicas_si_no_fueron_comprometidas(self):
        self.unidad.dependencia = 'observatorios'
        self.unidad.save()
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['filas'] = [
            dict(codigo='BOLETINES', porcentaje=100, registrado=1,
                exigible=True, pendiente=False, definida=True),
            dict(codigo='INVESTIGACION', porcentaje=None, registrado=0,
                exigible=False, pendiente=False, definida=True)]
        registro.save()
        self.assertEqual(self.lectura()['estado'], 'favorable')
        self.assertEqual([f['codigo'] for f in self.lectura()['actividad_principal']['filas']], ['BOLETINES'])

    def test_envio_en_mayo_conserva_antecedente_anterior_aunque_se_consulte_en_octubre(self):
        self.antecedente(70, anio=2025, corte='B')
        self.antecedente(40, anio=2026, corte='A')
        self.compras.estado = 'validado'
        self.compras.validado_en = timezone.make_aware(datetime(2026, 5, 15, 10))
        self.compras.save()
        datos = self.lectura()
        self.assertEqual((datos['fecha_referencia'], datos['origen_referencia']), ('2026-05-15', 'envio'))
        self.assertEqual((datos['periodo']['etiqueta'], datos['porcentaje']), ('2025-B', 70))

    def test_borrador_usa_fecha_actual_de_consulta(self):
        self.antecedente(70)
        datos = self.lectura()
        self.assertEqual((datos['fecha_referencia'], datos['origen_referencia']), ('2026-10-18', 'consulta'))

    def test_enero_puede_usar_b_que_termino_en_diciembre_del_anio_del_plan(self):
        self.antecedente(70, anio=2026, corte='B')
        datos = self.lectura(hoy=date(2027, 1, 15))
        self.assertEqual((datos['periodo']['etiqueta'], datos['estado']), ('2026-B', 'favorable'))

    def test_antecedente_legado_no_extiende_resultados_fuera_de_su_alcance(self):
        plan, cierre, _, _ = self.antecedente(100)
        DocumentoExpediente.objects.filter(pk__in=[plan.pk, cierre.pk]).update(
            marco_periodo='academico_legacy', tramo_inicio=date(2026, 3, 9), tramo_fin=date(2026, 7, 10))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertTrue(any('alcance histórico distinto' in m for m in datos['motivos']))

    def test_captura_con_otro_rango_no_acredita_el_semestre_natural(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['periodo_documental'] = dict(
            marco='academico_legacy', inicio='2026-03-09', fin='2026-07-10')
        registro.save()
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['porcentaje'])

    def test_uso_efectivo_bajo_no_se_oculta_por_cobertura_completa(self):
        _, _, _, registro = self.antecedente(75)
        registro.datos_nuevos['filas'] = [
            dict(codigo='USO', porcentaje=100, registrado=3, exigible=True, pendiente=False, definida=True),
            dict(codigo='USO-EFECTIVO', porcentaje=50, registrado=3, exigible=True, pendiente=False, definida=True)]
        registro.save()
        datos = self.lectura()
        self.assertEqual((datos['estado'], datos['porcentaje']), ('condicionada_mejora', 75))

    def test_excepcion_por_seguridad_permite_revisar_uso_nulo_sin_acreditarlo(self):
        _, _, _, registro = self.antecedente(100)
        registro.datos_nuevos['filas'] = [dict(codigo='USO', porcentaje=100,
            registrado=0, exigible=True, pendiente=False, definida=True)]
        registro.save()
        self.contenido.update(fundamento_inversion='seguridad',
            justificacion_inversion='Reposición del enclavamiento necesario para reabrir el área de corte.')
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'continuidad_seguridad')
        self.assertFalse(datos['actividad_principal']['cumple'])
        self.assertTrue(datos['requiere_revision'])

    def test_correspondencia_verificada_despues_del_envio_no_se_atribuye_al_pasado(self):
        plan, _, _, _ = self.antecedente(70)
        self.enviado()
        RegistroAuditoriaUnidad.objects.filter(objeto_id=str(plan.pk), entidad=plan._meta.label,
            descripcion='integridad_documental:evaluar').update(
                creado_en=timezone.make_aware(datetime(2026, 7, 3, 10)))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertFalse(datos['plan']['conforme'])
        self.assertTrue(any('retroactivamente' in m for m in datos['motivos']))

    def test_captura_archivada_despues_del_envio_no_sustenta_favorabilidad_historica(self):
        _, _, _, registro = self.antecedente(70)
        self.enviado()
        RegistroAuditoriaUnidad.objects.filter(pk=registro.pk).update(
            creado_en=timezone.make_aware(datetime(2026, 7, 3, 10)))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['porcentaje'])
        self.assertTrue(any('captura posterior' in m for m in datos['motivos']))

    def test_la_hora_del_envio_tambien_acota_la_captura_del_mismo_dia(self):
        _, _, _, registro = self.antecedente(70)
        self.enviado()
        RegistroAuditoriaUnidad.objects.filter(pk=registro.pk).update(
            creado_en=timezone.make_aware(datetime(2026, 7, 2, 13)))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIn('12:00:00', datos['instante_referencia'])

    def test_evaluacion_humana_posterior_no_se_lee_como_resultado_al_envio(self):
        _, cierre, _, _ = self.antecedente(70)
        self.enviado()
        DocumentoExpediente.objects.filter(pk=cierre.pk).update(
            evaluado_en=timezone.make_aware(datetime(2026, 7, 3, 10)))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['porcentaje'])

    def test_control_automatico_posterior_no_acredita_el_plan_en_la_fecha_del_envio(self):
        plan, _, _, _ = self.antecedente(70)
        self.enviado()
        DocumentoExpediente.objects.filter(pk=plan.pk).update(evaluacion=None)
        self.control(plan, timezone.make_aware(datetime(2026, 7, 3, 10)))
        datos = self.lectura()
        self.assertEqual(datos['estado'], 'por_justificar')
        self.assertIsNone(datos['plan']['porcentaje'])

    def test_recontrol_actual_conserva_sello_automatico_identico_anterior_al_envio(self):
        plan, _, _, _ = self.antecedente(70)
        self.enviado()
        DocumentoExpediente.objects.filter(pk=plan.pk).update(evaluacion=None)
        control = self.control(plan, timezone.make_aware(datetime(2026, 7, 3, 10)))
        registro = RegistroAuditoriaUnidad.objects.create(unidad=self.unidad, usuario=self.actor,
            entidad=plan._meta.label, objeto_id=str(plan.pk), accion='actualizar',
            descripcion='Control automático: automatico', datos_nuevos=dict(
                metodo=control.metodo, version=plan.version, recurso=plan.recurso_id,
                sha256=plan.recurso.hash_sha256, estado='automatico', aplicado=True, nota='100',
                resumen=control.resumen))
        RegistroAuditoriaUnidad.objects.filter(pk=registro.pk).update(
            creado_en=timezone.make_aware(datetime(2026, 7, 1, 11)))
        self.assertEqual(self.lectura()['estado'], 'favorable')
        # La misma constancia sólo posterior al envío deja de acreditar ese corte.
        RegistroAuditoriaUnidad.objects.filter(pk=registro.pk).update(
            creado_en=timezone.make_aware(datetime(2026, 7, 3, 11)))
        self.assertEqual(self.lectura()['estado'], 'por_justificar')

    def test_correspondencia_nativa_tardia_necesita_un_sello_previo_real(self):
        plan, _, _, _ = self.antecedente(70)
        self.enviado()
        RegistroAuditoriaUnidad.objects.filter(objeto_id=str(plan.pk), entidad=plan._meta.label,
            descripcion='integridad_documental:evaluar').delete()
        control = self.control(plan, timezone.make_aware(datetime(2026, 7, 3, 10)), correspondencia=True)
        self.assertEqual(self.lectura()['estado'], 'por_justificar')
        type(control).objects.filter(pk=control.pk).update(
            comprobado_en=timezone.make_aware(datetime(2026, 7, 1, 11)))
        self.assertEqual(self.lectura()['estado'], 'favorable')

    def test_la_lectura_no_crea_calificaciones_controles_ni_auditorias(self):
        self.antecedente(70)
        from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
        antes = (DocumentoExpediente.objects.count(), Recurso.objects.count(),
                 RegistroAuditoriaUnidad.objects.count(), ControlAutomaticoDocumento.objects.count())
        self.lectura()
        self.lectura()
        despues = (DocumentoExpediente.objects.count(), Recurso.objects.count(),
                   RegistroAuditoriaUnidad.objects.count(), ControlAutomaticoDocumento.objects.count())
        self.assertEqual(antes, despues)
        self.compras.refresh_from_db()
        self.assertIsNone(self.compras.evaluacion)
        self.assertEqual(self.compras.estado, 'pendiente')
