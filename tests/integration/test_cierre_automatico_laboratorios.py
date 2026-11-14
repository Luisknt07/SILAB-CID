"""Orquestación de cierre: fuentes conformes no bastan sin envío, firma y metas.

Procedencia PDF, congelación del cálculo y detectores de datos tienen sus suites
propias. Aquí se sustituyen esas fronteras, manteniendo _analizar y la escritura
real de controles para comprobar cuándo se concede (o retiene) una nota.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import io
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.automatizacion_documental import (
    _analizar, huella, procesar_documento, procesar_expediente,
)
from apps.documentos.presentation.expediente import tramo_del_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class CierreAutomaticoLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='cierre-orquestacion-responsable-qa')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio cierre orquestación QA', slug='cierre-orquestacion-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2025, 1, 1))
        cls.exigido, _ = DocumentoExigido.objects.update_or_create(codigo='INFORME-SEMESTRAL', defaults=dict(
            nombre='Informe semestral QA', carpeta='evaluacion', periodicidad='semestral', origen='ambos',
            fuente_reporte='informe', requiere_firma=True, activo=True, anexo_de=None))
        cls.catalogo_anexos = []
        for codigo, fuente in (('REGISTRO-USO', 'reservas'), ('GUIAS', 'guias')):
            exigido, _ = DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(
                nombre=codigo + ' QA', carpeta='ejecucion', periodicidad='semestral', origen='sistema',
                fuente_reporte=fuente, requiere_firma=False, activo=True, anexo_de=cls.exigido))
            cls.catalogo_anexos.append(exigido)

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-cierre-orquestacion-qa-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.doc = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigido,
            anio=2026, corte='B', estado='validado', version=2, firma_verificada=True)
        self.doc.recurso = self.recurso('Informe firmado de prueba aislada QA')
        self.doc.save(update_fields=['recurso'])
        self.anexos = []
        for exigido in self.catalogo_anexos:
            self.anexos.append(DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido,
                anio=2026, corte='B', estado='validado', version=1, recurso=self.recurso(exigido.codigo)))
        self.inicio, self.fin = tramo_del_documento(self.doc)
        self.hoy = self.fin + timedelta(days=1)
        self.instante = timezone.make_aware(datetime.combine(self.hoy, time(10)))
        self.doc.entregado_en = self.instante
        self.doc.save(update_fields=['entregado_en'])
        self.calidades = {a.exigido.codigo: dict(automatico=True, hallazgos=[], cumplimiento=100,
            fuentes=dict(unidad=self.unidad.pk, codigo=a.exigido.codigo, inicio=self.inicio.isoformat(),
                         fin=self.fin.isoformat(), registros=[dict(id=a.pk, sha256='a' * 64)])) for a in self.anexos}
        self.fuentes_congeladas = {codigo: huella(lectura['fuentes']) for codigo, lectura in self.calidades.items()}
        self.cierre = dict(metodo='metas-laboratorios-4', version=self.doc.version, recurso=self.doc.recurso_id,
            sha256=self.doc.recurso.hash_sha256, huella_medicion='c' * 64, nota=100,
            plan=dict(documento=321, version=1, recurso=654), plan_aprobado=True, completo=True,
            demostracion=False, alertas=[],
            filas=[dict(clave='USO', exigible=True, pendiente=False, definida=True, porcentaje=100),
                   dict(clave='GUIAS', exigible=True, pendiente=False, definida=True, porcentaje=100)],
            anexos=[dict(documento=a.pk, recurso=a.recurso_id, version=a.version,
                         sha256=a.recurso.hash_sha256) for a in self.anexos])
        self.contexto = SimpleNamespace(unidad=self.unidad, inicio=self.inicio, fin=self.fin,
            analizar=Mock(side_effect=lambda codigo: deepcopy(self.calidades[codigo])))
        self.confianzas = {}
        self.fronteras = ExitStack()
        self.addCleanup(self.fronteras.close)
        self.fronteras.enter_context(patch('django.utils.timezone.localdate', side_effect=lambda *args, **kwargs: self.hoy))
        self.fronteras.enter_context(patch('django.utils.timezone.now', side_effect=lambda: self.instante))
        self.procedencia = self.fronteras.enter_context(patch(
            'apps.documentos.presentation.confianza_documental.comprobar_procedencia', side_effect=self.confianza))
        self.archivado = self.fronteras.enter_context(patch(
            'apps.documentos.presentation.evaluacion_cierre.cierre_archivado', side_effect=lambda d: deepcopy(self.cierre)))
        self.leer_anexos = self.fronteras.enter_context(patch(
            'apps.documentos.presentation.expediente.anexos_del', side_effect=lambda d: self.anexos))
        self.crear_contexto = self.fronteras.enter_context(patch(
            'apps.documentos.presentation.calidad_automatica_laboratorios.ContextoCalidad', return_value=self.contexto))

    def recurso(self, texto):
        salida = io.BytesIO()
        pagina = Canvas(salida)
        pagina.drawString(35, 780, texto + ': contenido nativo de la prueba de orquestación; no es un documento institucional.')
        pagina.save()
        recurso = Recurso(unidad=self.unidad, nombre=texto, visibilidad='interna')
        recurso.archivo.save('cierre-orquestacion-qa.pdf', ContentFile(salida.getvalue()), save=False)
        recurso.save()
        return recurso

    def confianza(self, documento):
        datos = dict(confiable=True, archivo_integro=True, motivos=[], origen='sistema',
            fuentes_sha256=self.fuentes_congeladas.get(documento.exigido.codigo, ''))
        datos.update(self.confianzas.get(documento.pk, {}))
        return datos

    def reglas(self, control):
        return {h['regla'] for h in control.hallazgos}

    def comprobar_retenida(self, regla, estado='bloqueado'):
        control = procesar_documento(self.doc)
        self.assertEqual(control.estado, estado, control.hallazgos)
        self.assertIn(regla, self.reglas(control))
        self.assertFalse(control.aplicado)
        self.assertIsNone(control.nota)
        self.doc.refresh_from_db()
        self.assertIsNone(self.doc.evaluacion)
        self.assertIsNone(self.doc.evaluado_por_id)
        self.assertIsNone(self.doc.nota)
        return control

    def test_analizar_real_identifica_cierre_completo_sin_escribir_ni_suplanta_revision(self):
        antes = (DocumentoExpediente.objects.count(), ControlAutomaticoDocumento.objects.count(),
                 RegistroAuditoriaUnidad.objects.count())
        confianza, hallazgos, resumen = _analizar(self.doc, self.contexto)
        self.assertTrue(confianza['confiable'])
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['nota_calculada'], 100)
        self.assertEqual((DocumentoExpediente.objects.count(), ControlAutomaticoDocumento.objects.count(),
                         RegistroAuditoriaUnidad.objects.count()), antes)
        self.assertEqual({c.args[0] for c in self.contexto.analizar.call_args_list}, {'REGISTRO-USO', 'GUIAS'})

    def test_envio_firmado_periodo_terminado_y_todas_metas_completas_concede_cien_del_sistema(self):
        control = procesar_documento(self.doc)
        self.assertEqual((control.estado, control.aplicado, control.nota), ('automatico', True, Decimal('100.00')))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.estado, 'validado')
        self.assertEqual(self.doc.nota, Decimal('100.00'))
        self.assertIsNone(self.doc.evaluacion)
        self.assertIsNone(self.doc.evaluado_por_id)
        self.assertIsNone(self.doc.evaluado_en)
        self.assertIsNone(self.doc.validado_por_id)
        self.assertIsNotNone(self.doc.recibido_en)
        self.assertIsNone(self.doc.recibido_por_id)
        evento = RegistroAuditoriaUnidad.objects.get(entidad=self.doc._meta.label, objeto_id=str(self.doc.pk))
        self.assertIsNone(evento.usuario_id)
        self.assertEqual(evento.datos_nuevos['nota'], '100.00')

    def test_control_conforme_es_idempotente_y_no_duplica_auditoria(self):
        primero = procesar_documento(self.doc)
        total = RegistroAuditoriaUnidad.objects.count()
        segundo = procesar_documento(self.doc)
        self.assertEqual(segundo.pk, primero.pk)
        self.assertEqual(segundo.nota, Decimal('100.00'))
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), total)

    def test_solo_analisis_no_aplica_nota_ni_recibe_una_entrega(self):
        control = procesar_documento(self.doc, aplicar=False)
        self.assertEqual(control.estado, 'automatico')
        self.assertFalse(control.aplicado)
        self.assertIsNone(control.nota)
        self.doc.refresh_from_db()
        self.assertIsNone(self.doc.recibido_en)
        self.assertIsNone(self.doc.nota)

    def test_plan_sin_aprobar_informe_incompleto_y_demo_no_reciben_cien(self):
        base = deepcopy(self.cierre)
        for cambios in (dict(plan_aprobado=False), dict(completo=False), dict(demostracion=True)):
            with self.subTest(cambios=cambios), transaction.atomic():
                self.cierre = dict(deepcopy(base), **cambios)
                self.comprobar_retenida('cierre_incompleto')
                transaction.set_rollback(True)

    def test_metas_obligatorias_pendientes_o_sin_definir_impiden_automatico(self):
        base = deepcopy(self.cierre)
        for cambios in (dict(pendiente=True), dict(definida=False)):
            with self.subTest(cambios=cambios), transaction.atomic():
                self.cierre = deepcopy(base)
                self.cierre['filas'][0].update(cambios)
                self.comprobar_retenida('medicion_incompleta')
                transaction.set_rollback(True)

    def test_cero_metas_exigibles_no_es_un_cien_por_ciento(self):
        self.cierre['filas'] = [dict(exigible=False, pendiente=False, definida=True, porcentaje=100)]
        self.comprobar_retenida('medicion_incompleta')

    def test_nota_archivada_incoherente_con_meta_parcial_no_se_acredita(self):
        self.cierre['filas'][0]['porcentaje'] = 50
        self.comprobar_retenida('nota_cierre_inconsistente')

    def test_nota_invalida_se_bloquea_incluso_si_todas_las_metas_dicen_cien(self):
        for nota in (75, 101, -1, 'NaN', 'Infinity', None, 'incorrecta'):
            with self.subTest(nota=nota), transaction.atomic():
                self.cierre['nota'] = nota
                self.comprobar_retenida('nota_cierre_inconsistente')
                transaction.set_rollback(True)

    def test_resultado_parcial_comprobado_recibe_nota_proporcional_sin_suplir_a_direccion(self):
        self.cierre['filas'][0]['porcentaje'] = 50
        self.cierre['nota'] = 75
        control = procesar_documento(self.doc)
        self.assertEqual((control.estado, control.aplicado, control.nota), ('automatico', True, Decimal('75.00')))
        self.assertIn('metas_pendientes', self.reglas(control))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.nota, Decimal('75.00'))
        self.assertIsNone(self.doc.evaluado_por_id)

    def test_resultado_bajo_con_evidencia_completa_conserva_nota_y_escala_seguimiento(self):
        from apps.documentos.presentation.cumplimiento import clasificacion_bandeja_automatizacion
        self.cierre['filas'][0]['porcentaje'] = 0
        self.cierre['nota'] = 50
        control = procesar_documento(self.doc)
        self.assertEqual(control.nota, Decimal('50.00'))
        self.assertTrue(control.resumen['requiere_seguimiento'])
        self.assertEqual(clasificacion_bandeja_automatizacion(self.doc), 'excepciones')

    def test_periodo_en_curso_no_acredita_cumplimiento_anticipado(self):
        self.hoy = self.fin - timedelta(days=1)
        self.comprobar_retenida('periodo_en_curso', 'revision')

    def test_ultimo_dia_no_acredita_un_periodo_que_aun_no_ha_cerrado(self):
        self.hoy = self.fin
        self.comprobar_retenida('periodo_en_curso', 'revision')

    def test_firma_no_verificada_impide_nota_aunque_procedencia_pdf_sea_conforme(self):
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(firma_verificada=False)
        self.comprobar_retenida('firma_ausente')

    def test_documento_preparado_o_cargado_sin_envio_no_usa_cierre_archivado(self):
        for estado in ('generado', 'cargado', 'pendiente'):
            with self.subTest(estado=estado), transaction.atomic():
                self.archivado.reset_mock()
                DocumentoExpediente.objects.filter(pk=self.doc.pk).update(estado=estado)
                self.comprobar_retenida('cierre_no_enviado', 'revision')
                self.archivado.assert_not_called()
                transaction.set_rollback(True)

    def test_envio_legacy_sin_estructura_congelada_no_reconstruye_nota(self):
        self.cierre = None
        self.comprobar_retenida('cierre_no_enviado', 'revision')

    def test_cambio_version_recurso_o_hash_de_anexo_impide_cierre(self):
        base = deepcopy(self.cierre)
        for campo, valor in (('version', 9), ('recurso', 999999), ('sha256', '0' * 64)):
            with self.subTest(campo=campo), transaction.atomic():
                self.cierre = deepcopy(base)
                self.cierre['anexos'][0][campo] = valor
                self.comprobar_retenida('anexo_modificado')
                transaction.set_rollback(True)

    def test_fuentes_de_anexo_difieren_del_pdf_aunque_cantidades_siguen_iguales(self):
        self.calidades['REGISTRO-USO']['fuentes']['registros'][0]['sha256'] = 'b' * 64
        self.comprobar_retenida('fuentes_anexo_modificadas')

    def test_anexo_sin_fuentes_congeladas_necesita_actualizarse(self):
        self.fuentes_congeladas['REGISTRO-USO'] = ''
        self.comprobar_retenida('fuentes_anexo_modificadas')

    def test_anexos_omitidos_agregados_o_lista_vacia_no_pasan(self):
        base = deepcopy(self.cierre)
        for anexos in ([], base['anexos'][1:], base['anexos'] + [dict(documento=999999)]):
            with self.subTest(cantidad=len(anexos)), transaction.atomic():
                self.cierre = deepcopy(base)
                self.cierre['anexos'] = anexos
                self.comprobar_retenida('anexos_incompletos')
                transaction.set_rollback(True)

    def test_no_haber_anexos_actuales_tampoco_es_conforme(self):
        self.anexos = []
        self.comprobar_retenida('anexos_incompletos')

    def test_anexo_no_conforme_propaga_hallazgos_sin_convertirlo_en_nota(self):
        self.calidades['GUIAS'].update(automatico=False, hallazgos=[dict(regla='syllabus_pendiente',
            severidad='revision', mensaje='Falta revisar el vínculo académico.', url='', entidad='', id=None)])
        self.comprobar_retenida('syllabus_pendiente', 'revision')

    def test_detectores_no_automatizables_sin_hallazgos_tambien_requieren_revision(self):
        self.calidades['GUIAS']['automatico'] = False
        self.comprobar_retenida('anexo_por_revisar', 'revision')

    def test_pdf_anexo_sin_procedencia_confiable_bloquea_aunque_datos_estan_completos(self):
        self.confianzas[self.anexos[0].pk] = dict(confiable=False, archivo_integro=False,
            motivos=['El contenido del archivo difiere de su original.'])
        self.comprobar_retenida('respaldo_anexo')

    def test_pdf_principal_sin_procedencia_identica_no_recibe_cien(self):
        self.confianzas[self.doc.pk] = dict(confiable=False, archivo_integro=False,
            motivos=['El informe corresponde a contenido distinto.'])
        self.comprobar_retenida('procedencia_no_comprobada')

    def test_correccion_fijada_por_director_retiene_su_revision_humana(self):
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(correccion_hasta=self.instante + timedelta(days=3))
        self.comprobar_retenida('correccion_por_revisar', 'revision')

    def test_catalogo_de_cierre_modificado_no_hereda_regla_estandar(self):
        base = dict(origen='ambos', fuente_reporte='informe', requiere_firma=True, periodicidad='semestral')
        for cambios in (dict(origen='sistema'), dict(fuente_reporte='otro_reporte'), dict(requiere_firma=False),
                        dict(periodicidad='anual')):
            with self.subTest(cambios=cambios), transaction.atomic():
                DocumentoExigido.objects.filter(pk=self.exigido.pk).update(**dict(base, **cambios))
                self.doc.refresh_from_db()
                self.contexto.inicio, self.contexto.fin = tramo_del_documento(self.doc)
                self.comprobar_retenida('catalogo_personalizado', 'revision')
                transaction.set_rollback(True)

    def test_evaluacion_humana_de_la_version_se_preserva_con_su_actor(self):
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(evaluacion=75, evaluacion_version=self.doc.version,
            evaluado_por=self.actor, evaluado_en=self.instante)
        control = procesar_documento(self.doc)
        self.assertTrue(control.resumen['manual_preservada'])
        self.assertFalse(control.aplicado)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.nota, 75)
        self.assertEqual(self.doc.evaluado_por_id, self.actor.pk)

    def test_contexto_de_otra_unidad_o_periodo_se_rechaza_antes_de_aplicar(self):
        self.contexto.fin -= timedelta(days=1)
        with self.assertRaisesMessage(ValueError, 'contexto de control'):
            procesar_documento(self.doc)
        self.assertFalse(ControlAutomaticoDocumento.objects.filter(documento=self.doc).exists())

    def test_modo_demostracion_no_concede_nota_aunque_todos_los_limites_esten_conformes(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            self.comprobar_retenida('modo_demostracion')

    def prohibir_recalculo_vivo(self):
        self.contexto.analizar.reset_mock()
        self.contexto.analizar.side_effect = AssertionError('Un cierre histórico aceptado no consulta el inventario vivo.')

    def test_cierre_aceptado_conserva_cien_tras_movimiento_posterior_sin_recalcular_fuentes_vivas(self):
        from apps.recursos.models.consumibles import Consumible
        primero = procesar_documento(self.doc)
        self.assertEqual(primero.nota, Decimal('100.00'))
        cierre_original = deepcopy(self.cierre)
        Consumible.objects.create(unidad=self.unidad, codigo='NUEVA-COMPRA-DESPUES-CIERRE-QA',
            nombre='Material adquirido después del cierre aceptado', stock_total=Decimal('25'),
            unidad_medida='kg', ubicacion='Nueva bodega QA')
        self.calidades['REGISTRO-USO']['fuentes']['inventario_actual'] = {'saldo': 25, 'compras_posteriores': 1}
        self.calidades['GUIAS'].update(automatico=False, hallazgos=[dict(regla='nuevo_periodo_sin_guia',
            severidad='revision', mensaje='Actividad del período siguiente, ajena al cierre aceptado.')])
        self.prohibir_recalculo_vivo()
        segundo = procesar_documento(self.doc)
        self.assertEqual((segundo.estado, segundo.aplicado, segundo.nota), ('automatico', True, Decimal('100.00')))
        self.contexto.analizar.assert_not_called()
        self.assertEqual(self.cierre, cierre_original)
        self.assertEqual(segundo.resumen['cierre_archivado_sha256'], huella(cierre_original))
        self.assertEqual(segundo.resumen['fuentes_anexos'], primero.resumen['fuentes_anexos'])

    def test_lote_con_anexos_primero_reutiliza_cierre_aceptado_sin_consultar_fuentes_vivas(self):
        aceptado = procesar_documento(self.doc)
        self.assertEqual(aceptado.nota, Decimal('100.00'))
        self.prohibir_recalculo_vivo()
        self.crear_contexto.reset_mock()
        controles = procesar_expediente([*self.anexos, self.doc])
        self.assertEqual([c.documento_id for c in controles], [self.doc.pk, *[a.pk for a in self.anexos]])
        self.assertTrue(all(c.estado == 'automatico' and c.aplicado for c in controles))
        self.assertEqual(controles[0].nota, Decimal('100.00'))
        self.assertTrue(all(c.nota is None for c in controles[1:]))
        for control in controles[1:]:
            self.assertEqual(control.resumen['fuentes_sha256'],
                aceptado.resumen['fuentes_anexos'][str(control.documento_id)])
        self.crear_contexto.assert_called_once_with(self.unidad, self.inicio, self.fin)
        self.contexto.analizar.assert_not_called()

    def test_cierre_archivado_alterado_sigue_bloqueado_en_rechequeos_sin_fallback_vivo(self):
        procesar_documento(self.doc)
        # No cambia cantidades, porcentaje ni nota: basta alterar una parte del
        # cálculo que ya sustentaba la aceptación para perder la correspondencia.
        self.cierre['filas'][0]['detalle'] = 'Texto añadido después de aceptar el cierre'
        self.prohibir_recalculo_vivo()
        primero = self.comprobar_retenida('cierre_archivado_modificado')
        segundo = self.comprobar_retenida('cierre_archivado_modificado')
        self.assertEqual(segundo.pk, primero.pk)
        self.contexto.analizar.assert_not_called()

    def test_cierre_aceptado_sigue_comprobando_integridad_de_principal_y_anexos(self):
        for cual in ('principal', 'anexo'):
            with self.subTest(cual=cual), transaction.atomic():
                self.confianzas = {}
                self.contexto.analizar.side_effect = lambda codigo: deepcopy(self.calidades[codigo])
                procesar_documento(self.doc)
                objeto = self.doc if cual == 'principal' else self.anexos[0]
                self.confianzas[objeto.pk] = dict(confiable=False, archivo_integro=False,
                    motivos=['El archivo aceptado fue sustituido o dejó de estar disponible.'])
                self.prohibir_recalculo_vivo()
                self.comprobar_retenida('procedencia_no_comprobada' if cual == 'principal' else 'respaldo_anexo')
                self.contexto.analizar.assert_not_called()
                transaction.set_rollback(True)

    def test_archivo_de_fuente_congelada_alterado_o_desaparecido_retira_conformidad_historica(self):
        base = deepcopy(self.calidades)
        for situacion in ('alterado', 'desaparecido'):
            with self.subTest(situacion=situacion), transaction.atomic():
                self.calidades = deepcopy(base)
                self.contexto.analizar.side_effect = lambda codigo: deepcopy(self.calidades[codigo])
                respaldo = self.recurso('Respaldo original congelado ' + situacion)
                self.calidades['REGISTRO-USO']['fuentes']['archivo_respaldo'] = dict(
                    nombre=respaldo.archivo.name, sha256=respaldo.hash_sha256, disponible=True)
                self.fuentes_congeladas = {c: huella(r['fuentes']) for c, r in self.calidades.items()}
                aceptado = procesar_documento(self.doc)
                self.assertEqual(aceptado.nota, Decimal('100.00'))
                self.assertEqual(aceptado.resumen['archivos_fuentes'], [dict(
                    nombre=respaldo.archivo.name, sha256=respaldo.hash_sha256)])
                if situacion == 'desaparecido':
                    respaldo.archivo.storage.delete(respaldo.archivo.name)
                else:
                    with respaldo.archivo.storage.open(respaldo.archivo.name, 'wb') as archivo:
                        archivo.write(b'Contenido sustituido despues de la aceptacion.')
                self.prohibir_recalculo_vivo()
                self.comprobar_retenida('respaldo_archivado_modificado')
                self.contexto.analizar.assert_not_called()
                transaction.set_rollback(True)

    def test_cambio_de_fuente_de_anexo_aceptado_no_se_disfraza_de_inventario_posterior(self):
        procesar_documento(self.doc)
        self.fuentes_congeladas['REGISTRO-USO'] = 'f' * 64
        self.prohibir_recalculo_vivo()
        self.comprobar_retenida('fuentes_anexo_modificadas')
        self.contexto.analizar.assert_not_called()

    def test_recurso_de_acta_congelada_comprueba_sus_bytes_sin_ruta_en_la_fuente(self):
        respaldo = self.recurso('Acta de inventario respaldada por Recurso QA')
        self.calidades['REGISTRO-USO']['fuentes']['acta'] = dict(
            recurso=respaldo.pk, sha256=respaldo.hash_sha256)
        self.fuentes_congeladas = {c: huella(r['fuentes']) for c, r in self.calidades.items()}
        aceptado = procesar_documento(self.doc)
        self.assertEqual(aceptado.nota, Decimal('100.00'))
        self.assertEqual(aceptado.resumen['archivos_fuentes'], [dict(
            recurso=respaldo.pk, sha256=respaldo.hash_sha256)])
        with respaldo.archivo.storage.open(respaldo.archivo.name, 'wb') as archivo:
            archivo.write(b'Acta sustituida conservando el identificador y hash declarado.')
        self.prohibir_recalculo_vivo()
        self.comprobar_retenida('respaldo_archivado_modificado')
        self.contexto.analizar.assert_not_called()

    def test_manifiesto_prefiere_ruta_archivo_al_nombre_original_del_adjunto(self):
        respaldo = self.recurso('Adjunto con nombre original distinto de su ruta QA')
        self.calidades['REGISTRO-USO']['fuentes']['adjunto'] = dict(
            archivo=respaldo.archivo.name, nombre='Nombre original del usuario.pdf',
            sha256=respaldo.hash_sha256, disponible=True)
        self.fuentes_congeladas = {c: huella(r['fuentes']) for c, r in self.calidades.items()}
        aceptado = procesar_documento(self.doc)
        self.assertEqual(aceptado.nota, Decimal('100.00'))
        self.assertEqual(aceptado.resumen['archivos_fuentes'], [dict(
            nombre=respaldo.archivo.name, sha256=respaldo.hash_sha256)])
        self.prohibir_recalculo_vivo()
        sin_cambio = procesar_documento(self.doc)
        self.assertEqual((sin_cambio.estado, sin_cambio.nota), ('automatico', Decimal('100.00')))
        with respaldo.archivo.storage.open(respaldo.archivo.name, 'wb') as archivo:
            archivo.write(b'Adjunto modificado en la ruta real de almacenamiento.')
        self.comprobar_retenida('respaldo_archivado_modificado')
        self.contexto.analizar.assert_not_called()

    def test_nota_y_penalizacion_aceptadas_no_cambian_por_politica_o_tardanza_posterior(self):
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(entregado_tarde=True)
        with patch('apps.documentos.models.expediente.penalizacion_vigente', return_value=10):
            aceptado = procesar_documento(self.doc)
        self.assertEqual(aceptado.nota, Decimal('90.00'))
        self.assertEqual(aceptado.politica, dict(penalizacion_tardia=10, minimo_cumplimiento=70))
        ancla = deepcopy(aceptado.resumen['aceptacion_archivada'])
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(entregado_tarde=False)
        self.prohibir_recalculo_vivo()
        with patch('apps.documentos.models.expediente.penalizacion_vigente', return_value=50):
            posterior = procesar_documento(self.doc)
        self.assertEqual((posterior.estado, posterior.aplicado, posterior.nota),
                         ('automatico', True, Decimal('90.00')))
        self.assertEqual(posterior.politica, dict(penalizacion_tardia=10, minimo_cumplimiento=70))
        self.assertEqual(posterior.resumen['aceptacion_archivada'], ancla)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.nota, Decimal('90.00'))
        self.contexto.analizar.assert_not_called()

    def test_manual_nueva_y_catalogo_modificado_no_reutilizan_aprobacion_anterior(self):
        for cambio in ('manual', 'catalogo'):
            with self.subTest(cambio=cambio), transaction.atomic():
                self.contexto.analizar.side_effect = lambda codigo: deepcopy(self.calidades[codigo])
                procesar_documento(self.doc)
                if cambio == 'manual':
                    DocumentoExpediente.objects.filter(pk=self.doc.pk).update(evaluacion=73,
                        evaluacion_version=self.doc.version, evaluado_por=self.actor, evaluado_en=self.instante)
                else:
                    DocumentoExigido.objects.filter(pk=self.exigido.pk).update(origen='sistema')
                self.contexto.analizar.reset_mock()
                control = procesar_documento(self.doc)
                self.assertTrue(self.contexto.analizar.called)
                self.assertFalse(control.aplicado)
                self.doc.refresh_from_db()
                if cambio == 'manual':
                    self.assertTrue(control.resumen['manual_preservada'])
                    self.assertEqual(self.doc.nota, 73)
                    self.assertEqual(self.doc.evaluado_por_id, self.actor.pk)
                else:
                    self.assertIn('catalogo_personalizado', self.reglas(control))
                    self.assertIsNone(self.doc.nota)
                transaction.set_rollback(True)

    def test_version_nueva_sin_calculo_enviado_no_hereda_nota_del_cierre_anterior(self):
        procesar_documento(self.doc)
        DocumentoExpediente.objects.filter(pk=self.doc.pk).update(version=self.doc.version + 1)
        self.cierre = None  # cierre_archivado exige la versión y recurso exactos del envío.
        self.comprobar_retenida('cierre_no_enviado', 'revision')
