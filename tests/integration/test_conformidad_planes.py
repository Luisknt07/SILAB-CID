"""Conformidad objetiva, excepciones y separación entre plan y resultados."""
from datetime import date, time
from copy import deepcopy
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.automatizacion_documental import huella, procesar_documento
from apps.documentos.presentation.conformidad_planes import (
    analizar_conformidad, analizar_contenido_plan, confirmar_conformidad,
)
from apps.documentos.presentation.expediente import construir_expediente, tramo_del_documento, evaluar_documento
from apps.documentos.presentation.expediente_redaccion import plan_inicial, secciones_de
from apps.documentos.presentation.preparacion_documental import exigir_preparacion, preparacion_del_editor
from apps.formacion.presentation.evaluacion_rubrica import revisar_documento
from apps.recursos.models.recursos import Recurso
from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad, CapacidadOperativaUnidad
from tests.integration.utiles import pdf_legible_prueba


class EstructuraContenidoPlanTests(SimpleTestCase):
    def setUp(self):
        self.documento = SimpleNamespace(exigido=SimpleNamespace(codigo='PLANIFICACION'),
            unidad=SimpleNamespace(codigo_base='laboratorios'))
        self.contexto = SimpleNamespace(inicio=date(2026, 7, 1), fin=date(2026, 12, 31))
        self.contenido = dict(actividades=dict(minimos_catalogo=3, catalogo={}, otras=[]),
            sin_inversion_justificacion='Las actividades se cubren con recursos existentes.')

    def comprobar(self, contenido):
        return analizar_contenido_plan(self.documento, self.contexto, contenido)[0]

    def test_capacidad_y_referencias_malformadas_se_informan_antes_de_recorrer_filas(self):
        for capacidad in (None, [], ['recurso'], 'recurso', 1,
                          {'referencias_indicadores': {}}, {'referencias_indicadores': [None]}):
            with self.subTest(capacidad=capacidad):
                contenido = deepcopy(self.contenido)
                contenido['actividades']['capacidad'] = capacidad
                self.assertEqual([h['regla'] for h in self.comprobar(contenido)], ['estructura_invalida'])

    def test_funciones_y_programacion_de_uso_malformadas_no_producen_excepciones(self):
        for campo, valores in (
                ('sectores', (None, 'docencia', {}, 1, [None], [{}])),
                ('presupuesto_uso', (None, [], ['mes'], 'mes', 1,
                                     {'horas_por_mes': None}, {'horas_por_mes': []}))):
            for valor in valores:
                with self.subTest(campo=campo, valor=valor):
                    contenido = dict(self.contenido, **{campo: valor})
                    self.assertEqual([h['regla'] for h in self.comprobar(contenido)], ['estructura_invalida'])

    def test_origenes_del_cronograma_malformados_no_se_recogen_como_fechas_validas(self):
        contenido = deepcopy(self.contenido)
        contenido['actividades']['cronograma_auto'] = dict(version=1, meses_por_actividad={}, origenes=[])
        self.assertEqual([h['regla'] for h in self.comprobar(contenido)], ['cronograma_invalido'])

    def test_metas_estandar_malformadas_conservan_su_hallazgo_sin_excepciones(self):
        estandar = dict(version=2, inicio=self.contexto.inicio.isoformat(), fin=self.contexto.fin.isoformat(),
                        metas={}, carga_docente={})
        valores = ([], 'metas', 1, dict(estandar, metas=[]), dict(estandar, carga_docente=[]),
                   dict(estandar, carga_docente={'avisos': {}}),
                   dict(estandar, carga_docente={'horas_por_mes': []}))
        with patch('apps.documentos.presentation.expediente_redaccion.problemas_cronograma', return_value=[]), \
                patch('apps.documentos.presentation.expediente_redaccion.actividades_para', return_value=[]), \
                patch('apps.documentos.presentation.expediente_redaccion.filas_del_plan', return_value=[]):
            for valor in valores:
                with self.subTest(valor=valor):
                    contenido = deepcopy(self.contenido)
                    contenido['actividades']['metas_estandar'] = valor
                    self.assertIn('metas_estandar_invalidas', [h['regla'] for h in self.comprobar(contenido)])

    def test_plan_legado_sin_contenedores_nuevos_conserva_revision_asistida(self):
        contenido = deepcopy(self.contenido)
        contenido['actividades']['minimos_catalogo'] = 2
        hallazgos = self.comprobar(contenido)
        self.assertEqual([h['regla'] for h in hallazgos], ['plan_sin_estructura_vigente'])
        self.assertEqual(hallazgos[0]['severidad'], 'revision')


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class ConformidadPlanesTests(TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-conformidad-planes-')
        self.addCleanup(carpeta.cleanup)
        ajuste = override_settings(MEDIA_ROOT=carpeta.name)
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        self.actor = get_user_model().objects.create_superuser('conformidad-plan-direccion', password=None)
        self.unidad = Unidad.objects.create(nombre='Laboratorio de conformidad', slug='conformidad-plan',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2025, 1, 1))
        periodo = PeriodoAcademico.objects.create(codigo='2025-B', anio_referencia=2025, ciclo='B',
            tipo='ordinario', ambito='carreras_centros', estado='publicado')
        VersionCalendarioAcademico.objects.create(periodo=periodo, numero=1, vigente=True,
            fecha_inicio_clases=date(2025, 8, 18), fecha_fin_clases=date(2025, 12, 12),
            fecha_fin_periodo=date(2025, 12, 19))
        self.docs = construir_expediente(self.unidad, 2025)
        from tests.integration.utiles import programar_carga_academica_prueba
        programar_carga_academica_prueba(next(d for d in self.docs if d.exigido.codigo == 'PLANIFICACION'
            and d.corte == 'B'), self.actor)
        for dia in range(5):
            HorarioOperacionUnidad.objects.create(unidad=self.unidad, dia_semana=dia,
                hora_inicio=time(8), hora_fin=time(12))
        CapacidadOperativaUnidad.objects.create(unidad=self.unidad, vigente_desde=date(2025, 1, 1),
            aforo_seguridad=8, puestos_mobiliario=8, puestos_equipados=8, capacidad_personal=8,
            fuente='Acta técnica de la capacidad utilizada en la prueba.')

    def documento(self, codigo='PLANIFICACION'):
        d = next(d for d in self.docs if d.exigido.codigo == codigo and d.corte in ('B', ''))
        contenido = {}
        # Estas entregas simulan el esquema histórico, sin marcador PAC.
        for seccion in secciones_de(d.exigido.fuente_reporte, contenido={}):
            for campo in seccion.campos:
                if not campo.requerido:
                    continue
                contenido[campo.clave] = ([campo.opciones[0][0]] if campo.tipo == 'marcas' else
                    campo.opciones[0][0] if campo.tipo == 'opcion' else
                    '<p>Descripción documentada de actividades, recursos y responsabilidades.</p>')
        inicio, fin = tramo_del_documento(d)
        if codigo == 'PLANIFICACION':
            contenido['presupuesto_uso'] = dict(version=1, horas_comprometidas='300',
                horas_por_mes={str(m): '50' for m in range(7, 13)},
                justificacion='Carga docente del semestre cubierta por la jornada y la capacidad verificadas.')
            contenido['actividades'] = plan_inicial(d, inicio, fin)
            contenido['actividades']['capacidad']['requiere_revision'] = False
            for fila in contenido['actividades']['catalogo'].values():
                fila['responsable'] = 'Responsable técnico registrado'
            contenido['sin_inversion_justificacion'] = '<p>Se utilizará el equipamiento disponible, sin adquisiciones previstas.</p>'
        else:
            contenido['sin_compras_justificacion'] = '<p>El inventario cubre la programación del año siguiente.</p>'
        DocumentoElaborado.objects.create(documento=d, contenido=contenido, version=1)
        d.recurso = Recurso.objects.create(unidad=self.unidad, nombre='Archivo del plan',
            archivo=ContentFile(pdf_legible_prueba('Plan completo para el período.'), name='plan.pdf'), version=1)
        d.version, d.estado, d.firma_verificada = 1, 'validado', True
        d.save()
        return d, contenido, SimpleNamespace(inicio=inicio, fin=fin)

    def actualizar(self, d, contenido):
        DocumentoElaborado.objects.filter(documento=d).update(contenido=contenido)

    def test_plan_completo_admite_conformidad_sin_cuatro_calificaciones(self):
        d, _, contexto = self.documento()
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['alcance'], 'conformidad_documental')
        self.assertFalse(resumen['resultados_operativos'])

    def test_contenido_explicito_comparte_bloqueos_y_resumen_con_la_conformidad(self):
        for codigo, tabla in (('PLANIFICACION', 'inversion'), ('PLAN-COMPRAS-ANUAL', 'compras')):
            with self.subTest(codigo=codigo):
                d, contenido, contexto = self.documento(codigo)
                contenido[tabla] = [dict(categoria='equipos', item='Instrumento')]
                self.actualizar(d, contenido)
                original = deepcopy(contenido)
                self.assertEqual(analizar_contenido_plan(d, contexto, contenido),
                                 analizar_conformidad(d, contexto))
                self.assertEqual(contenido, original)

    def test_contenido_se_comprueba_antes_del_envio_sin_leer_la_redaccion_guardada(self):
        d, contenido, contexto = self.documento()
        d.estado = 'generado'
        propuesta = deepcopy(contenido)
        propuesta['inversion'] = [dict(categoria='equipos', item='Instrumento')]
        with patch.object(DocumentoElaborado.objects, 'filter',
                          side_effect=AssertionError('El analizador debe usar el contenido recibido.')):
            hallazgos, resumen = analizar_contenido_plan(d, contexto, propuesta)
        self.assertEqual([h['regla'] for h in hallazgos], ['compra_incompleta'])
        self.assertEqual(resumen['redaccion_sha256'], huella(propuesta))
        self.assertEqual([h['regla'] for h in analizar_conformidad(d, contexto)[0]],
                         ['documento_no_enviado'])

    def test_revisiones_de_pertinencia_no_se_convierten_en_bloqueos_del_contenido(self):
        d, contenido, contexto = self.documento()
        contenido['actividades']['capacidad']['requiere_revision'] = True
        d.estado = 'generado'
        hallazgos, _ = analizar_contenido_plan(d, contexto, contenido)
        self.assertTrue(any(h['regla'] == 'capacidad_por_confirmar' for h in hallazgos))
        self.assertTrue(all(h['severidad'] == 'revision' for h in hallazgos))
        self.assertNotIn('documento_no_enviado', [h['regla'] for h in hallazgos])

    def test_preparacion_completa_comprueba_metas_y_cronograma_antes_del_pdf(self):
        from apps.documentos.presentation.expediente_redaccion import avance

        d, contenido, contexto = self.documento()
        self.assertEqual(exigir_preparacion(d, contenido, contexto.inicio, contexto.fin)['porcentaje'], 100)
        metas_invalidas = deepcopy(contenido)
        metas_invalidas['actividades']['metas_estandar']['metas'] = []
        cronograma_invalido = deepcopy(contenido)
        cronograma_invalido['actividades']['cronograma_auto']['meses_por_actividad'] = []
        for propuesta in (metas_invalidas, cronograma_invalido):
            with self.subTest(propuesta=propuesta['actividades']):
                self.assertEqual(avance('planificacion', propuesta)['porcentaje'], 100)
                progreso = preparacion_del_editor(d, propuesta, contexto.inicio, contexto.fin)
                self.assertLess(progreso['porcentaje'], 100)
                self.assertTrue(progreso['detalles'])
                with self.assertRaises(ValidationError):
                    exigir_preparacion(d, propuesta, contexto.inicio, contexto.fin)

    def test_preparacion_no_bloquea_la_revision_humana_de_la_capacidad(self):
        d, contenido, contexto = self.documento()
        contenido['actividades']['capacidad']['requiere_revision'] = True
        hallazgos, _ = analizar_contenido_plan(d, contexto, contenido)
        self.assertTrue(hallazgos)
        self.assertTrue(all(h['severidad'] == 'revision' for h in hallazgos))
        progreso = exigir_preparacion(d, contenido, contexto.inicio, contexto.fin)
        self.assertEqual(progreso['porcentaje'], 100)
        self.assertFalse(progreso['faltantes'])

    def test_preparacion_del_plan_legado_exige_meses_de_sus_actividades(self):
        from apps.documentos.presentation.expediente_redaccion import avance, problemas_cronograma

        d, contenido, contexto = self.documento()
        contenido['actividades']['minimos_catalogo'] = 2
        contenido['actividades']['otras'].append(dict(nombre='Revisión de procedimientos de la unidad',
            indicador='Procedimiento revisado', meta='1', meses=[], responsable='Responsable técnico'))
        problemas = problemas_cronograma(d.unidad, contenido, contexto.inicio, contexto.fin)
        self.assertTrue(any(p['regla'] == 'actividad_incompleta' and p['severidad'] == 'bloqueo'
                            for p in problemas))
        self.assertEqual(avance('planificacion', contenido)['porcentaje'], 100)
        progreso = preparacion_del_editor(d, contenido, contexto.inicio, contexto.fin)
        self.assertLess(progreso['porcentaje'], 100)
        with self.assertRaisesMessage(ValidationError, 'Faltan meses de ejecución'):
            exigir_preparacion(d, contenido, contexto.inicio, contexto.fin)

    def test_horas_previstas_cubren_el_mes_programado_no_solo_el_total_semestral(self):
        d, contenido, contexto = self.documento()
        contenido['presupuesto_uso']['horas_por_mes'].update({'8': '0', '9': '100'})
        self.actualizar(d, contenido)
        self.assertIn('uso_docencia_mes_insuficiente',
            [h['regla'] for h in analizar_conformidad(d, contexto)[0]])

    def test_captura_anterior_sigue_aceptada_sin_recalcular_la_agenda(self):
        d, contenido, contexto = self.documento()
        contenido['actividades']['metas_estandar']['version'] = 1
        self.actualizar(d, contenido)
        self.assertEqual(analizar_conformidad(d, contexto)[0], [])

    def test_carga_mensual_invalida_no_interrumpe_la_revision(self):
        d, contenido, contexto = self.documento()
        contenido['actividades']['metas_estandar']['carga_docente']['horas_por_mes'] = ['8', '9']
        self.actualizar(d, contenido)
        self.assertIn('metas_estandar_invalidas', [h['regla'] for h in analizar_conformidad(d, contexto)[0]])

    def test_compras_sin_adquisiciones_justificadas_no_exige_autorizar_gasto(self):
        d, _, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['presupuesto_referencial'], '0')
        self.assertFalse(resumen['autorizacion_financiera'])

    def test_fila_inicial_de_inversion_no_bloquea_plan_sin_compras_justificado(self):
        d, contenido, contexto = self.documento()
        contenido['inversion'] = [dict(categoria='equipos', item='', cantidad='', justificacion='',
            prioridad='', costo_unitario='', fuente='')]
        self.actualizar(d, contenido)
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['items'], 0)
        self.assertEqual(resumen['presupuesto_referencial'], '0')

    def test_fila_inicial_anual_no_inicia_priorizacion_de_una_compra_inexistente(self):
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        contenido['compras'] = [dict(categoria='equipos')]
        self.actualizar(d, contenido)
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['items'], 0)
        self.assertEqual(resumen['priorizacion_inversion']['estado'], 'sin_solicitud')

    def test_plan_con_inversion_parcial_muestra_un_aviso_claro_y_no_se_aprueba(self):
        d, contenido, contexto = self.documento()
        contenido['inversion'] = [dict(categoria='equipos', item='Instrumento')]
        self.actualizar(d, contenido)
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual([h['regla'] for h in hallazgos], ['compra_incompleta'])
        self.assertIn('Presupuesto del período, ítem 1', hallazgos[0]['mensaje'])
        self.assertEqual(resumen['items'], 1)
        estado = (d.estado, d.evaluacion, d.evaluado_en, d.recurso_id, d.version)
        with self.assertRaisesMessage(ValidationError, 'Presupuesto del período'):
            confirmar_conformidad(d, self.actor, d.version, d.recurso.hash_sha256, confirmado=True)
        d.refresh_from_db()
        self.assertEqual((d.estado, d.evaluacion, d.evaluado_en, d.recurso_id, d.version), estado)

    def test_inversion_semestral_con_costo_cero_admite_conformidad_sin_trimestre(self):
        d, contenido, contexto = self.documento()
        contenido['inversion'] = [dict(categoria='equipos', item='Instrumento en donación', cantidad=1,
            justificacion='Donación para las actividades previstas', prioridad='alta',
            costo_unitario=0, fuente='donacion')]
        self.actualizar(d, contenido)
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(resumen['presupuesto_referencial'], '0')

    def test_fila_inicial_sin_justificacion_muestra_un_solo_aviso_de_presupuesto(self):
        d, contenido, contexto = self.documento()
        contenido['inversion'] = [dict(categoria='equipos')]
        contenido['sin_inversion_justificacion'] = ''
        self.actualizar(d, contenido)
        hallazgos, _ = analizar_conformidad(d, contexto)
        self.assertEqual([h['regla'] for h in hallazgos], ['apartados_incompletos'])
        self.assertIn('Presupuesto del período', hallazgos[0]['mensaje'])

    def test_falta_justificacion_de_ausencia_de_compras_bloquea(self):
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        contenido['sin_compras_justificacion'] = ''
        self.actualizar(d, contenido)
        self.assertIn('apartados_incompletos', [h['regla'] for h in analizar_conformidad(d, contexto)[0]])

    def test_compra_sin_respuesta_a_un_equipo_critico_requiere_revision(self):
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.unidades import UnidadEquipo
        tipo = EquiposServicios.objects.create(codigo='CRIT-COMPRAS', nombre='Equipo crítico')
        UnidadEquipo.objects.create(equipo=tipo, laboratorio=self.unidad, codigo_unidad='CRIT-01',
                                   estado_unidad='dañado', criticidad='critico')
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        hallazgos, _ = analizar_conformidad(d, contexto)
        self.assertTrue(any(h['regla'] == 'necesidad_critica_sin_respuesta' and h['severidad'] == 'revision'
                            for h in hallazgos))
        contenido['capacidad'] = '<p>CRIT-010 se reparará con recursos propios.</p>'
        self.actualizar(d, contenido)
        self.assertIn('necesidad_critica_sin_respuesta', [h['regla'] for h in analizar_conformidad(d, contexto)[0]])
        contenido['capacidad'] = '<p>CRIT-01 se reparará bajo garantía, sin adquisición prevista.</p>'
        self.actualizar(d, contenido)
        self.assertEqual(analizar_conformidad(d, contexto)[0], [])

    def test_compra_presupuestada_con_catalogos_validos_admite_conformidad(self):
        from apps.documentos.presentation.expediente_redaccion import (
            CATEGORIAS_INVERSION, PRIORIDADES, FUENTES_FINANCIAMIENTO,
        )
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        contenido['compras'] = [dict(categoria=CATEGORIAS_INVERSION[0][0], item='Instrumento de medición',
            cantidad='2', justificacion='Reposición para las prácticas previstas', prioridad=PRIORIDADES[0][0],
            costo_unitario='100.50', fuente=FUENTES_FINANCIAMIENTO[0][0], trimestre='2')]
        self.actualizar(d, contenido)
        hallazgos, resumen = analizar_conformidad(d, contexto)
        self.assertEqual(hallazgos, [])
        self.assertEqual(Decimal(resumen['presupuesto_referencial']), Decimal('201.00'))
        self.assertFalse(resumen['autorizacion_financiera'])

    def test_no_se_acepta_reducir_la_meta_por_debajo_del_minimo(self):
        d, contenido, contexto = self.documento()
        contenido['actividades']['catalogo']['USO']['meta'] = '50 %'
        self.actualizar(d, contenido)
        hallazgos, _ = analizar_conformidad(d, contexto)
        self.assertTrue(any(h['regla'] == 'meta_invalida' and h['severidad'] == 'bloqueo' for h in hallazgos))
        with self.assertRaises(ValidationError):
            confirmar_conformidad(d, self.actor, d.version, d.recurso.hash_sha256, confirmado=True)

    def test_responsable_omitido_no_bloquea_y_cronograma_fuera_del_periodo_si(self):
        d, contenido, contexto = self.documento()
        for fila in contenido['actividades']['catalogo'].values():
            fila['responsable'] = ''
        self.actualizar(d, contenido)
        self.assertEqual(analizar_conformidad(d, contexto)[0], [])
        contenido['actividades']['catalogo']['USO'].update(responsable='', meses=[1])
        self.actualizar(d, contenido)
        reglas = {h['regla'] for h in analizar_conformidad(d, contexto)[0]}
        self.assertIn('cronograma_fuera_periodo', reglas)

    def test_json_invalido_no_interrumpe_el_lote(self):
        d, contenido, contexto = self.documento()
        for plan in ([], {'catalogo': []}, {'catalogo': {'USO': []}}, {'minimos_catalogo': '3', 'capacidad': []}):
            with self.subTest(plan=plan):
                contenido['actividades'] = plan
                self.actualizar(d, contenido)
                self.assertTrue(analizar_conformidad(d, contexto)[0])

    def test_importes_negativos_infinitos_y_exponentes_excesivos_no_pasan(self):
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        for cantidad in ('-1', 'Infinity', '1e999999', 'NaN'):
            contenido['compras'] = [dict(categoria='equipos', item='Instrumento', cantidad=cantidad,
                justificacion='Reposición', prioridad='alta', costo_unitario='100', fuente='institucional', trimestre='1')]
            self.actualizar(d, contenido)
            self.assertIn('importe_invalido', [h['regla'] for h in analizar_conformidad(d, contexto)[0]])

    def test_cronograma_con_tipos_invalidos_devuelve_alerta_sin_interrumpir_el_lote(self):
        d, contenido, contexto = self.documento()
        for meses in (8, None, '8', [{}], [True], [0], [13]):
            with self.subTest(meses=meses):
                contenido['actividades']['catalogo']['USO']['meses'] = meses
                self.actualizar(d, contenido)
                self.assertIn('cronograma_invalido', [h['regla'] for h in analizar_conformidad(d, contexto)[0]])

    def test_necesidad_duplicada_se_remite_a_revision(self):
        d, contenido, contexto = self.documento('PLAN-COMPRAS-ANUAL')
        item = dict(categoria='equipos', item='Instrumento', cantidad='1', justificacion='Reposición',
                    prioridad='alta', costo_unitario='100', fuente='institucional', trimestre='1')
        contenido['compras'] = [item, dict(item)]
        self.actualizar(d, contenido)
        self.assertTrue(any(h['regla'] == 'compra_duplicada' and h['severidad'] == 'revision'
                            for h in analizar_conformidad(d, contexto)[0]))

    def test_motor_aplica_conformidad_nativa_y_conserva_fuente_sistema(self):
        d, contenido, _ = self.documento()
        confianza = dict(confiable=True, archivo_integro=True, motivos=[], redaccion_sha256=huella(contenido))
        with patch('apps.documentos.presentation.confianza_documental.comprobar_procedencia', return_value=confianza):
            control = procesar_documento(d, usuario=self.actor)
        self.assertEqual((control.estado, control.aplicado, control.nota), ('automatico', True, Decimal(100)))
        self.assertIsNone(d.evaluacion)
        self.assertIsNone(d.nota)
        self.assertIs(d.cumple, True)

    def test_redaccion_distinta_del_original_no_recibe_conformidad_automatica(self):
        d, _, _ = self.documento()
        confianza = dict(confiable=True, archivo_integro=True, motivos=[], redaccion_sha256='f' * 64)
        with patch('apps.documentos.presentation.confianza_documental.comprobar_procedencia', return_value=confianza):
            control = procesar_documento(d)
        self.assertFalse(control.aplicado)
        self.assertIsNone(control.nota)
        self.assertIn('redaccion_sin_ancla', [h['regla'] for h in control.hallazgos])

    def test_nativo_con_antecedente_noventa_acredita_requisito_sin_bonificar_desempeno(self):
        from io import BytesIO
        from pypdf import PdfReader
        from apps.documentos.presentation.aprobacion_en_linea import generar_y_enviar_qr, comprobar_emision
        from apps.documentos.presentation.progreso_general import progreso_general
        from tests.integration.utiles import abrir_entrega, registrar_antecedente_evaluacion

        d, contenido, _ = self.documento()
        from apps.documentos.presentation.recursos_periodo import preparar_recursos
        contenido = preparar_recursos(contenido)
        contenido['revision_recursos'] = 'revisado'
        self.actualizar(d, contenido)
        d.estado = 'pendiente'
        d.save(update_fields=['estado'])
        # La emisión y el envío reales conservan el PDF nativo y su QR, sin
        # agregar una firma sintética ni sustituir el detector de procedencia.
        abrir_entrega(d)
        generar_y_enviar_qr(d, self.actor)
        constancia = comprobar_emision(d)
        self.assertEqual(constancia.enviado_por_id, self.actor.pk)
        self.assertIsNotNone(constancia.enviado_en)
        self.assertEqual(constancia.sha256, d.recurso.hash_sha256)
        with d.recurso.archivo.open('rb') as archivo:
            pdf = PdfReader(BytesIO(archivo.read()))
        # Sin página de índice: la navegación queda en los marcadores del PDF.
        self.assertTrue(pdf.outline)
        registrar_antecedente_evaluacion(d, self.actor, 90, 'Evaluación histórica conservada.')
        d.entregado_tarde = True
        d.save(update_fields=['entregado_tarde'])
        fecha = d.evaluado_en
        control = procesar_documento(d, usuario=self.actor)
        self.assertEqual((control.estado, control.aplicado, control.nota), ('automatico', True, Decimal(100)))
        self.assertFalse(control.resumen['manual_preservada'])
        self.assertTrue(control.resumen['procedencia']['confiable'])
        self.assertTrue(control.resumen['procedencia']['contenido_equivalente'])
        self.assertEqual(revisar_documento(d)['conformidad']['fuente'], 'Sistema')
        documentos = [d if f.pk == d.pk else f for f in self.docs
                      if not f.exigido.es_anexo and f.corte in ('B', '')]
        resultado = progreso_general(documentos)
        fila = next(f for f in resultado['detalle'] if f['documento'].pk == d.pk)
        self.assertEqual((resultado['total'], fila['aporte'], fila['maximo']), (2, 0, 0))
        self.assertEqual(fila['conformidad']['estado'], 'conforme')
        self.assertTrue(fila['completado'])
        self.assertTrue(fila['prerrequisito'])
        self.assertFalse(fila['puntua'])
        self.assertIsNone(resultado['resultado_porcentaje'])
        d.refresh_from_db()
        self.assertEqual((d.evaluacion, d.evaluacion_observacion, d.evaluado_en),
                         (90, 'Evaluación histórica conservada.', fecha))

    def test_resolucion_ya_no_admite_porcentaje_ni_rubrica(self):
        d = next(d for d in self.docs if d.exigido.codigo == 'RESOLUCION-CREACION')
        with self.assertRaises(ValidationError):
            evaluar_documento(d, self.actor, 75)
        revision = revisar_documento(d)
        self.assertEqual(revision['modalidad'], 'permanente')
