"""La prioridad nueva distingue gestión, evidencia incompleta y decisiones financieras."""
from copy import deepcopy
from datetime import date, datetime
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from django.http import QueryDict

from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
from apps.documentos.presentation.priorizacion_necesidades import (
    analizar_gestion_inversion, fijar_gestion_inversion, lectura_gestion_inversion,
    requisitos_gestion_inversion,
)
from tests.integration import test_priorizacion_compras as antecedentes


@override_settings(MEDICION_SOLO_DEMO=False, MEDICION_METAS_HABILITADA=True)
class PriorizacionNecesidadesTests(TestCase):
    hoy = date(2026, 10, 18)
    setUp = antecedentes.PriorizacionComprasTests.setUp
    entrega = antecedentes.PriorizacionComprasTests.entrega
    antecedente = antecedentes.PriorizacionComprasTests.antecedente
    control = antecedentes.PriorizacionComprasTests.control

    def datos(self, **cambios):
        return dict(pac_version=2, inversion_gestion_version=1,
            compras=[dict(item='Estación de trabajo del área de diseño', cantidad='1', costo_unitario='100')],
            **cambios)

    def uso(self, *, pendiente=False, cero=False):
        return dict(semestres=[dict(periodo='2026-A', nombre='Enero–junio 2026',
            atenciones=0 if cero else 5, horas_efectivas=0 if cero else 20,
            horas_disponibles=None if pendiente else 100, utilizacion=None if pendiente else 20,
            pendiente=pendiente, fuentes_medicion={})], medicion_pendiente=pendiente,
            sin_actividad_efectiva=cero, equipos_sin_trazas=[], diagnostico_sha256='a' * 64)

    def plan(self):
        documento = self.entrega('PLANIFICACION', corte='B')
        instante = timezone.make_aware(datetime(2026, 10, 1, 10))
        documento.validado_en = documento.evaluado_en = instante
        documento.save(update_fields=['validado_en', 'evaluado_en'])
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad, objeto_id=str(documento.pk),
            entidad=documento._meta.label).update(creado_en=instante)
        self.control(documento, instante)
        return documento

    def analizar(self, contenido=None, *, uso=None, al_dia=True, **kwargs):
        documentacion = dict(estado='al_dia' if al_dia else 'pendientes_entrega', al_dia=al_dia,
            obligatorias_al_corte=2, pendientes_entrega=0 if al_dia else 1, pendientes_revision=0, filas=[])
        with patch('apps.documentos.presentation.priorizacion_necesidades._uso', return_value=uso or self.uso()), \
             patch('apps.documentos.presentation.priorizacion_necesidades._documentacion', return_value=documentacion):
            return analizar_gestion_inversion(self.compras, contenido or self.datos(), hoy=self.hoy, **kwargs)

    def test_plan_vigente_y_cierre_con_fuentes_dan_antecedente_no_fondos(self):
        self.antecedente(85)
        plan = self.plan()
        lectura = self.analizar()
        self.assertEqual(lectura['estado'], 'favorable')
        self.assertEqual(lectura['porcentaje'], 85)
        self.assertTrue(lectura['plan']['conforme'])
        self.assertEqual(lectura['plan']['referencia']['documento'], plan.pk)
        self.assertFalse(lectura['autoriza_fondos'])
        self.assertFalse(lectura['afecta_conformidad'])
        self.assertEqual({c['codigo'] for c in lectura['criterios']}, {'plan', 'reportes', 'cumplimiento', 'uso'})

    def test_plan_actual_faltante_no_se_sustituye_con_cierre_antiguo_alto(self):
        self.antecedente(100)
        lectura = self.analizar()
        self.assertEqual(lectura['estado'], 'pendiente_plan')
        self.assertFalse(lectura['plan']['conforme'])
        self.assertTrue(lectura['requiere_compromiso'])
        self.assertTrue(lectura['requisitos'])

    def test_incumplimiento_acreditado_exige_compromiso_sin_prohibir_peticion(self):
        self.antecedente(40)
        self.plan()
        datos = self.datos()
        lectura = self.analizar(datos)
        self.assertEqual(lectura['estado'], 'condicionada_mejora')
        self.assertTrue(lectura['requiere_compromiso'])
        self.assertEqual({r['regla'] for r in lectura['requisitos']},
                         {'justificacion_uso_existente', 'acciones_cumplimiento'})
        datos.update(justificacion_uso_existente='<p>Se reprogramarán las prácticas con el equipo reparado.</p>',
            acciones_cumplimiento=[dict(accion='Programar y ejecutar las prácticas pendientes',
                responsable='Coordinación de la unidad', plazo='2027-03-31',
                resultado='Completar las prácticas comprometidas y registrar horario real y asistencia.')])
        mejorada = self.analizar(datos)
        self.assertEqual(mejorada['estado'], 'condicionada_mejora')
        self.assertFalse(mejorada['requisitos'])
        self.assertFalse(mejorada['autoriza_fondos'])

    def test_ausencia_de_datos_o_cero_de_trazas_no_es_incumplimiento_acreditado(self):
        self.plan()
        lectura = self.analizar(uso=self.uso(pendiente=True, cero=True))
        self.assertEqual(lectura['estado'], 'por_justificar')
        self.assertIsNone(lectura['porcentaje'])
        self.assertFalse(lectura['requiere_compromiso'])
        self.assertFalse(lectura['requisitos'])

    def test_unidad_nueva_presenta_puesta_en_funcionamiento_con_acciones(self):
        self.unidad.fecha_inicio = date(2026, 8, 1)
        self.unidad.save(update_fields=['fecha_inicio'])
        lectura = self.analizar()
        self.assertTrue(lectura['nueva']['es_nueva'])
        self.assertEqual(lectura['estado'], 'habilitacion_inicial')
        self.assertTrue(lectura['requiere_compromiso'])
        self.assertFalse(lectura['desempeno_insuficiente'])
        self.assertTrue(lectura['requisitos'])

    def test_documentos_vencidos_impiden_antecedente_favorable_sin_castigar_historial(self):
        self.antecedente(100)
        self.plan()
        lectura = self.analizar(al_dia=False)
        self.assertEqual(lectura['estado'], 'por_justificar')
        self.assertEqual(lectura['porcentaje'], 100)
        self.assertFalse(lectura['requisitos'])

    def test_no_compras_justificadas_no_exigen_antecedentes_ni_compromisos(self):
        contenido = self.datos()
        contenido.update(compras=[], sin_compras_justificacion='<p>Los activos operativos cubren la programación.</p>')
        with patch('apps.documentos.presentation.priorizacion_necesidades._antecedente', side_effect=AssertionError):
            lectura = analizar_gestion_inversion(self.compras, contenido, hoy=self.hoy)
        self.assertEqual(lectura['estado'], 'sin_solicitud')
        self.assertFalse(lectura['requiere_compromiso'])
        self.assertFalse(lectura['requisitos'])

    def test_captura_se_conserva_y_cambio_real_de_datos_exige_nueva_lectura(self):
        self.antecedente(90)
        self.plan()
        contenido = self.datos()
        with patch('apps.documentos.presentation.priorizacion_necesidades._uso', return_value=self.uso()), \
             patch('apps.documentos.presentation.priorizacion_necesidades._documentacion', return_value=dict(al_dia=True, estado='al_dia', filas=[])):
            congelado = fijar_gestion_inversion(self.compras, contenido, hoy=self.hoy)
        original = deepcopy(congelado['inversion_gestion_fuentes'])
        with patch('apps.documentos.presentation.priorizacion_necesidades.analizar_gestion_inversion', side_effect=AssertionError):
            self.assertEqual(lectura_gestion_inversion(self.compras, congelado, hoy=date(2027, 5, 1)), original)
            self.assertEqual(analizar_priorizacion(self.compras, congelado, hoy=date(2027, 5, 1)), original)
        congelado['compras'][0]['cantidad'] = '2'
        with patch('apps.documentos.presentation.priorizacion_necesidades.analizar_gestion_inversion', return_value={'nueva': True}) as calcular:
            self.assertEqual(lectura_gestion_inversion(self.compras, congelado, hoy=self.hoy), {'nueva': True})
            calcular.assert_called_once()

    def test_revision_actual_es_explicita_y_no_reescribe_la_fecha_del_envio(self):
        self.antecedente(90)
        self.plan()
        enviado = timezone.make_aware(datetime(2026, 8, 1, 10))
        self.compras.estado, self.compras.validado_en = 'validado', enviado
        self.compras.save(update_fields=['estado', 'validado_en'])
        congelada = self.analizar()
        actual = self.analizar(actual=True)
        self.assertEqual(congelada['fecha_referencia'], '2026-08-01')
        self.assertEqual(actual['fecha_referencia'], self.hoy.isoformat())
        self.assertEqual(actual['origen_referencia'], 'revision_actual')
        self.compras.refresh_from_db()
        self.assertEqual(self.compras.validado_en, enviado)

    def test_compromisos_no_aceptan_tablas_rotas_fechas_imposibles_o_sin_resultado(self):
        lectura = dict(requiere_compromiso=True, solicita_compras=True, anio=2026)
        datos = dict(justificacion_uso_existente='El cierre demuestra prácticas pendientes.',
            acciones_cumplimiento=[dict(accion='Reprogramar', responsable='Coordinación',
                plazo='2028-02-31', resultado='')])
        errores = requisitos_gestion_inversion(lectura, datos)
        self.assertTrue(any('resultado' in r['mensaje'] for r in errores))
        self.assertTrue(any('plazo válido' in r['mensaje'] for r in errores))

    def test_formulario_conserva_compromiso_y_descarta_fuentes_enviadas_por_cliente(self):
        from apps.documentos.presentation.expediente_redaccion import leer_formulario
        post = QueryDict(mutable=True)
        post.update(dict(justificacion_uso_existente='<p>Reprogramar el aprovechamiento del inventario.</p>',
            firma_nombre='Responsable institucional', firma_cargo='Coordinación',
            inversion_gestion_fuentes='una captura enviada por navegador no es evidencia'))
        for clave, valor in dict(accion='Ejecutar la programación mensual', responsable='Coordinación',
                                plazo='2027-04-30', resultado='Registrar las prácticas realizadas y sus asistentes').items():
            post.setlist('acciones_cumplimiento__' + clave, [valor])
        contenido = leer_formulario('compras', post, self.unidad, documento=self.compras,
            contenido_anterior=self.datos())
        self.assertEqual(contenido['inversion_gestion_version'], 1)
        self.assertIn('Reprogramar el aprovechamiento', contenido['justificacion_uso_existente'])
        self.assertEqual(contenido['acciones_cumplimiento'][0]['plazo'], '2027-04-30')
        self.assertNotIn('inversion_gestion_fuentes', contenido)

    def test_preparacion_bloquea_compromiso_faltante_y_permite_solicitar_con_mejora(self):
        from apps.documentos.presentation.pac_universitario import preparar_pac
        from apps.documentos.presentation.preparacion_documental import preparacion_del_editor
        self.antecedente(40)
        contenido = preparar_pac(dict(compras=[dict(item='Licencia de diseño del área',
            cantidad='1', costo_unitario='100', area_id='unidad', tipo_necesidad='dotacion',
            clase_bien='software', mes_compra='3', justificacion='Permite ejecutar las prácticas programadas.',
            clasificacion_pac='por_definir')], firma_nombre='Responsable institucional',
            firma_cargo='Coordinación'), unidad=self.unidad)
        with patch('apps.documentos.presentation.priorizacion_necesidades._uso', return_value=self.uso()):
            preparacion = preparacion_del_editor(self.compras, contenido, date(2026, 1, 1), date(2026, 12, 31))
        self.assertTrue(any('Explica el uso de los recursos actuales' in d for d in preparacion['detalles']))
        contenido.update(justificacion_uso_existente='Se corregirá la programación y el registro de prácticas.',
            acciones_cumplimiento=[dict(accion='Ejecutar las prácticas pendientes', responsable='Coordinación',
                plazo='2027-03-31', resultado='Cumplir las prácticas comprometidas y conservar sus registros.')])
        with patch('apps.documentos.presentation.priorizacion_necesidades._uso', return_value=self.uso()):
            preparacion = preparacion_del_editor(self.compras, contenido, date(2026, 1, 1), date(2026, 12, 31))
        self.assertFalse([d for d in preparacion['detalles'] if 'acciones' in d or 'Explica el uso' in d])
        self.assertFalse(preparacion['faltantes'])

    def test_snapshot_invalido_no_se_recupera_como_congelado_y_no_hay_compras_ficticias(self):
        from apps.documentos.presentation.priorizacion_necesidades import captura_gestion_inversion
        datos = self.datos()
        datos['inversion_gestion_fuentes'] = dict(version=1, metodo='gestion_inversion_1',
            huellas='dato incorrecto', unidad=self.unidad.pk, anio=2026, documento=self.compras.pk)
        self.assertIsNone(captura_gestion_inversion(self.compras, datos))
        rotos = self.datos()
        rotos.update(compras='tabla incorrecta', sin_compras_justificacion='Inventario suficiente')
        lectura = analizar_gestion_inversion(self.compras, rotos, hoy=self.hoy)
        self.assertEqual(lectura['estado'], 'por_justificar')
        self.assertFalse(lectura['autoriza_fondos'])

    def test_fila_vacia_del_expediente_no_sustituye_un_plan_con_compromisos(self):
        from apps.documentos.models.expediente import DocumentoExpediente
        DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigidos['PLANIFICACION'],
            anio=2026, corte='B')
        lectura = self.analizar()
        self.assertEqual(lectura['plan']['estado'], 'sin_plan')
        self.assertTrue(lectura['requiere_compromiso'])
        self.assertEqual({r['regla'] for r in lectura['requisitos']},
                         {'justificacion_uso_existente', 'acciones_cumplimiento'})

    def test_plan_redactado_pendiente_de_conformidad_no_se_repite_en_otra_tabla(self):
        from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
        documento = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigidos['PLANIFICACION'],
            anio=2026, corte='B')
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido=dict(actividades=dict(
            catalogo=dict(PRACTICAS=dict(aplica=True, meta='6', responsable='Coordinación', meses=[8, 9, 10])))))
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(
            actualizado_en=timezone.make_aware(datetime(2026, 10, 1, 10)))
        lectura = self.analizar()
        self.assertEqual(lectura['plan']['estado'], 'pendiente_conformidad')
        self.assertFalse(lectura['plan']['conforme'])
        self.assertFalse(lectura['requiere_compromiso'])
        self.assertFalse(lectura['requisitos'])
        self.assertEqual(lectura['plan']['borrador']['version'], 1)

    def test_unidad_sin_fecha_de_inicio_y_sin_plan_tambien_presenta_compromisos(self):
        # La lectura admite un contexto importado incompleto; el modelo de la
        # aplicación conserva su fecha obligatoria y no se altera la base.
        self.unidad.fecha_inicio = None
        lectura = self.analizar()
        self.assertFalse(lectura['nueva']['es_nueva'])
        self.assertEqual(lectura['estado'], 'pendiente_plan')
        self.assertTrue(lectura['requiere_compromiso'])

    def test_borrador_posterior_no_exime_compromisos_de_una_solicitud_antes_de_su_fecha(self):
        from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
        documento = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigidos['PLANIFICACION'],
            anio=2026, corte='B')
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=1, contenido=dict(actividades=dict(
            catalogo=dict(PRACTICAS=dict(aplica=True, meta='6', responsable='Coordinación', meses=[8, 9, 10])))))
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(
            actualizado_en=timezone.make_aware(datetime(2026, 10, 19, 10)))
        lectura = self.analizar()
        self.assertEqual(lectura['plan']['estado'], 'sin_plan')
        self.assertIsNone(lectura['plan']['borrador'])
        self.assertTrue(lectura['requiere_compromiso'])

    def test_archivo_de_plan_preparado_en_el_futuro_no_sustituye_el_plan_al_corte(self):
        from apps.documentos.models.expediente import DocumentoExpediente
        documento = self.entrega('PLANIFICACION', corte='B')
        futuro = timezone.make_aware(datetime(2026, 10, 19, 10))
        DocumentoExpediente.objects.filter(pk=documento.pk).update(
            estado='generado', validado_en=None, generado_en=futuro)
        from apps.recursos.models.recursos import Recurso
        Recurso.objects.filter(pk=documento.recurso_id).update(fecha_subida=futuro)
        lectura = self.analizar()
        self.assertEqual(lectura['plan']['estado'], 'sin_plan')
        self.assertTrue(lectura['requiere_compromiso'])
