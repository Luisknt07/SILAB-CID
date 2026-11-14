"""Decisiones por excepción y envío nativo sin una segunda aprobación obligatoria."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.automatizacion_documental import procesar_documento
from apps.documentos.presentation.decision_automatica import (
    decidir_atencion, excepcion_resuelta_por_revision,
)
from apps.documentos.presentation.expediente import (
    _generar, anexos_del, construir_expediente, tramo_del_documento, validar_documento,
)
from apps.documentos.presentation.expediente_redaccion import secciones_de
from apps.documentos.presentation.medicion_metas import registrar_evidencia
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad, HorarioOperacionUnidad
from tests.integration.utiles import (
    abrir_entrega, cargar_documento_revisado, contenido_plan_completo, pdf_legible_prueba,
)


class DecisionAutomaticaDocumentalTests(SimpleTestCase):
    def decision(self, codigo='INFORME-SEMESTRAL', *, estado='automatico', hallazgos=None,
                 resumen=None, nota=80, minimo=70, aplicado=True, enviado=True):
        documento = SimpleNamespace(exigido=SimpleNamespace(codigo=codigo),
            estado='validado' if enviado else 'generado')
        return decidir_atencion(documento, estado=estado, hallazgos=hallazgos or [],
            resumen=resumen or {}, nota=nota, minimo=minimo, aplicado=aplicado)

    def test_parcial_por_encima_del_minimo_no_obliga_revision_del_director(self):
        lectura = self.decision(resumen=dict(indicadores_exigibles=[
            dict(codigo='PRACTICAS', porcentaje=80), dict(codigo='GUIAS', porcentaje=100)]))
        self.assertEqual(lectura['destino'], 'automatico')
        self.assertFalse(lectura['requiere_director'])
        self.assertTrue(lectura['resultado_conservado'])

    def test_resultado_bajo_se_acredita_real_y_deriva_seguimiento(self):
        lectura = self.decision(nota=50)
        self.assertEqual(lectura['destino'], 'direccion')
        self.assertTrue(lectura['resultado_conservado'])
        self.assertEqual(lectura['motivos'][0]['regla'], 'resultado_bajo_minimo')

    def test_promedio_alto_no_oculta_un_indicador_obligatorio_bajo(self):
        lectura = self.decision(nota=90, resumen=dict(indicadores_exigibles=[
            dict(codigo='USO-EFECTIVO', nombre='Uso efectivo', porcentaje=40),
            dict(codigo='GUIAS', nombre='Guías', porcentaje=100)]))
        self.assertEqual(lectura['destino'], 'direccion')
        self.assertEqual(lectura['indicadores_bajo_minimo'][0]['codigo'], 'USO-EFECTIVO')

    def test_exactamente_el_minimo_pasa_sin_redondeo_que_infle_el_resultado(self):
        for porcentaje, destino in ((Decimal('70'), 'automatico'), (Decimal('69.99'), 'direccion')):
            with self.subTest(porcentaje=porcentaje):
                self.assertEqual(self.decision(nota=porcentaje)['destino'], destino)

    def test_datos_incompletos_los_corrige_la_unidad_sin_ocupar_revision_humana(self):
        for enviado in (False, True):
            with self.subTest(enviado=enviado):
                lectura = self.decision('PLANIFICACION', estado='bloqueado', aplicado=False,
                    enviado=enviado, hallazgos=[dict(regla='actividad_incompleta',
                        mensaje='Falta el responsable.', severidad='bloqueo')])
                self.assertEqual(lectura['destino'], 'unidad')
                self.assertFalse(lectura['requiere_director'])

    def test_anomalia_o_decision_no_representada_no_se_autoresuelve(self):
        for regla in ('anexo_modificado', 'procedencia_no_comprobada', 'meta_cualitativa',
                      'correccion_por_revisar', 'catalogo_personalizado', 'REGLA_NUEVA'):
            with self.subTest(regla=regla):
                lectura = self.decision('PLANIFICACION', estado='revision', aplicado=False,
                    hallazgos=[dict(regla=regla, mensaje='Revisar la excepción.', severidad='revision')])
                self.assertEqual(lectura['destino'], 'direccion')

    def test_compra_conforme_con_sustento_excepcional_conserva_conformidad(self):
        inversion = dict(aplica=True, requiere_revision=True, estado='habilitacion',
            explicacion='La capacidad inicial requiere comprobar el sustento de inversión.')
        lectura = self.decision('PLAN-COMPRAS-ANUAL', nota=100,
            resumen=dict(conformidad_documental=dict(priorizacion_inversion=inversion)))
        self.assertEqual((lectura['destino'], lectura['resultado_conservado']), ('direccion', True))
        self.assertEqual(lectura['motivos'][0]['regla'], 'sustento_inversion')
        self.assertFalse(lectura['autorizacion_financiera'])

    def test_sin_compras_o_antecedente_favorable_no_obliga_revision(self):
        for estado in ('sin_solicitud', 'favorable'):
            with self.subTest(estado=estado):
                lectura = self.decision('PLAN-COMPRAS-ANUAL', nota=100,
                    resumen=dict(conformidad_documental=dict(priorizacion_inversion=dict(
                        aplica=True, requiere_revision=False, estado=estado))))
                self.assertEqual(lectura['destino'], 'automatico')

    def test_anexo_con_integridad_alterada_no_se_esconde_por_no_tener_nota(self):
        lectura = self.decision('PRESTAMOS-EQUIPOS', estado='bloqueado', nota=None, aplicado=False,
            hallazgos=[dict(regla='procedencia_no_comprobada', mensaje='Cambió el archivo.', severidad='bloqueo')])
        self.assertEqual(lectura['destino'], 'direccion')

    def test_ausencia_simple_del_anexo_la_completa_la_unidad(self):
        lectura = self.decision('PRESTAMOS-EQUIPOS', estado='sin_archivo', nota=None,
            aplicado=False, enviado=False, hallazgos=[dict(regla='archivo_ausente',
                mensaje='Genera el anexo.', severidad='revision')])
        self.assertEqual(lectura['destino'], 'unidad')
        self.assertFalse(lectura['requiere_director'])


class RevisionHumanaResuelveExcepcionTests(SimpleTestCase):
    def documento(self, codigo='PLANIFICACION'):
        recurso = SimpleNamespace(activo=True, estado='vigente', version=2, unidad_id=7,
            archivo='plan.pdf', hash_sha256='a' * 64)
        return SimpleNamespace(pk=12, unidad_id=7, estado='validado', version=2,
            recurso_id=17, recurso=recurso, firma_verificada=True,
            exigido=SimpleNamespace(codigo=codigo, es_anexo=False, requiere_firma=True,
                periodicidad='unica' if codigo == 'RESOLUCION-CREACION' else 'semestral'),
            evaluacion=80 if codigo == 'INFORME-SEMESTRAL' else None,
            evaluacion_version=2, evaluado_por_id=6, evaluado_en=datetime(2026, 10, 18, tzinfo=timezone.utc),
            evaluacion_observacion='', nota=80, resumen_interfaz={},
            integridad_documental=dict(aplica=True, correspondencia_verificada=True),
            _conformidad_plan_registro=SimpleNamespace(unidad_id=7, usuario_id=6,
                datos_nuevos=dict(version=2, recurso_id=17, sha256='a' * 64, alcance='documental'),
                creado_en=datetime(2026, 10, 18, tzinfo=timezone.utc)))

    def control(self, regla='criterio_humano'):
        return dict(vigente=True, estado='revision', aplicado=False,
            hallazgos=[dict(regla=regla, mensaje='Comprobar el contenido.', severidad='revision')],
            resumen=dict(procedencia=dict(archivo_integro=True), decision_automatica=dict(
                version=1, destino='direccion', minimo_cumplimiento='70',
                motivos=[dict(regla=regla, mensaje='Comprobar el contenido.')],
                indicadores_bajo_minimo=[])))

    def test_conformidad_humana_vinculada_al_plan_resuelve_criterio_ya_revisado(self):
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            with self.subTest(codigo=codigo):
                self.assertTrue(excepcion_resuelta_por_revision(self.documento(codigo), self.control()))

    def test_misma_nota_o_actor_no_sustituye_una_conformidad_vinculada(self):
        for cambio in (dict(version=1), dict(recurso_id=18), dict(sha256='b' * 64),
                       dict(alcance='otro')):
            with self.subTest(cambio=cambio):
                documento = self.documento()
                documento._conformidad_plan_registro.datos_nuevos.update(cambio)
                self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))
        documento = self.documento()
        documento._conformidad_plan_registro.unidad_id = 8
        self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))

    def test_resultado_del_informe_revisado_y_correspondiente_resuelve_criterio(self):
        self.assertTrue(excepcion_resuelta_por_revision(
            self.documento('INFORME-SEMESTRAL'), self.control()))

    def test_informe_de_otra_version_o_sin_actor_no_resuelve(self):
        for campo, valor in (('evaluacion_version', 1), ('evaluado_por_id', None), ('recurso_id', None)):
            with self.subTest(campo=campo):
                documento = self.documento('INFORME-SEMESTRAL')
                setattr(documento, campo, valor)
                self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))

    def test_revision_humana_no_borra_un_resultado_actual_inferior_al_minimo(self):
        documento = self.documento('INFORME-SEMESTRAL')
        documento.evaluacion = documento.nota = 50
        self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))

    def test_revision_humana_no_borra_un_indicador_inferior_al_minimo(self):
        control = self.control()
        control['resumen']['decision_automatica']['indicadores_bajo_minimo'] = [
            dict(codigo='USO', porcentaje='40')]
        self.assertFalse(excepcion_resuelta_por_revision(self.documento('INFORME-SEMESTRAL'), control))

    def test_minimo_desconocido_no_resuelve_automaticamente_el_informe(self):
        for minimo in (None, 'NaN', 'no definido'):
            with self.subTest(minimo=minimo):
                control = self.control()
                control['resumen']['decision_automatica']['minimo_cumplimiento'] = minimo
                self.assertFalse(excepcion_resuelta_por_revision(self.documento('INFORME-SEMESTRAL'), control))

    def test_observacion_nueva_o_control_desactualizado_no_se_oculta(self):
        documento = self.documento()
        documento.estado = 'observado'
        self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))
        control = self.control()
        control['vigente'] = False
        self.assertFalse(excepcion_resuelta_por_revision(self.documento(), control))

    def test_integridad_alterada_o_correspondencia_no_confirmada_no_se_resuelve(self):
        documento = self.documento()
        documento.integridad_documental['correspondencia_verificada'] = False
        self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))
        control = self.control()
        control['resumen']['procedencia']['archivo_integro'] = False
        self.assertFalse(excepcion_resuelta_por_revision(self.documento(), control))

    def test_criticos_bajos_inversion_y_reglas_desconocidas_siguen_visibles(self):
        for regla in ('anexo_modificado', 'resultado_bajo_minimo', 'indicadores_bajo_minimo',
                      'sustento_inversion', 'REGLA_NUEVA'):
            with self.subTest(regla=regla):
                self.assertFalse(excepcion_resuelta_por_revision(self.documento(), self.control(regla)))
        control = self.control()
        control['hallazgos'].append(dict(regla='procedencia_no_comprobada',
            mensaje='Los bytes cambiaron.', severidad='bloqueo'))
        self.assertFalse(excepcion_resuelta_por_revision(self.documento(), control))

    def test_documento_permanente_requiere_aprobacion_atribuida_actual(self):
        documento = self.documento('RESOLUCION-CREACION')
        documento.resumen_interfaz = dict(permanente=True,
            aprobacion=dict(vigente=True, actor_id=6))
        self.assertTrue(excepcion_resuelta_por_revision(documento, self.control()))
        documento.resumen_interfaz['aprobacion']['actor_id'] = None
        self.assertFalse(excepcion_resuelta_por_revision(documento, self.control()))


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class EnvioNativoSinDirectorTests(TestCase):
    def setUp(self):
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico

        periodo = PeriodoAcademico.objects.create(codigo='2025-B', anio_referencia=2025, ciclo='B',
            tipo='ordinario', ambito='carreras_centros', estado='publicado')
        VersionCalendarioAcademico.objects.create(periodo=periodo, numero=1, vigente=True,
            fecha_inicio_clases=date(2025, 8, 18), fecha_fin_clases=date(2025, 12, 12),
            fecha_fin_periodo=date(2025, 12, 19))
        carpeta = TemporaryDirectory(prefix='citt-decision-documental-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.actor = get_user_model().objects.create_user(username='coordinacion-envio-objetivo')

    def unidad(self, tipo):
        unidad = Unidad.objects.create(nombre='Unidad de envío objetivo ' + tipo, slug='envio-objetivo-' + tipo,
            dependencia=tipo, administrador=self.actor, fecha_inicio=date(2024, 1, 1))
        EspacioReservable.objects.create(unidad=unidad, codigo='AREA-01', nombre='Espacio operativo',
            politica_reserva='general', capacidad=8)
        for dia in range(5):
            HorarioOperacionUnidad.objects.create(unidad=unidad, dia_semana=dia,
                hora_inicio=time(8), hora_fin=time(12))
        CapacidadOperativaUnidad.objects.create(unidad=unidad, vigente_desde=date(2024, 1, 1),
            aforo_seguridad=8, puestos_mobiliario=8, puestos_equipados=8, capacidad_personal=8,
            fuente='Acta técnica de capacidad, utilizada exclusivamente en pruebas aisladas.')
        return unidad

    def enviar(self, unidad, codigo):
        documentos = construir_expediente(unidad, 2025)
        documento = next(d for d in documentos if d.exigido.codigo == codigo and d.corte in ('', 'B'))
        abrir_entrega(documento)
        if codigo == 'PLANIFICACION':
            contenido = contenido_plan_completo(documento, self.actor, practicas_aprobadas=True)
            if unidad.codigo_base not in ('observatorios', 'laboratorios'):
                inicio, fin = tramo_del_documento(documento)
                # Estas tipologías no programan docencia en este fixture.
                # Un anexo sin prácticas no puede aprobarse por estar vacío.
                # El acta independiente declara cero actividad en el tramo;
                # permite constatar su contenido sin acreditar ejecución.
                registrar_evidencia(unidad, self.actor, dict(tipo='USO',
                    codigo='USO-CERO-' + unidad.slug, fecha=fin, desde=inicio, hasta=fin,
                    total_observado=0, titulo='Acta de ausencia de sesiones de la prueba aislada',
                    descripcion='Conciliación independiente del período sin sesiones registradas; '
                                'no acredita aprovechamiento ni ejecución de las metas.',
                    responsable=self.actor, detalle={}), verificar=True,
                    archivo=SimpleUploadedFile('acta-cero.pdf', pdf_legible_prueba(
                        'Acta de conciliación de cero sesiones observadas en el semestre aislado.')))
        else:
            contenido = {}
            for seccion in secciones_de('compras'):
                for campo in seccion.campos:
                    if campo.requerido:
                        contenido[campo.clave] = ([campo.opciones[0][0]] if campo.tipo == 'marcas' else
                            campo.opciones[0][0] if campo.tipo == 'opcion' else
                            'Programación anual, inventario y responsables identificados para la prueba.')
            contenido['sin_compras_justificacion'] = 'La dotación existente cubre las actividades previstas; no se solicitan compras.'
        DocumentoElaborado.objects.create(documento=documento, contenido=contenido, version=1)
        _generar(documento, self.actor)
        with documento.recurso.archivo.open('rb') as archivo:
            firmado = archivo.read() + b'\n% /Type /Sig /ByteRange [0 100 200 300] /Contents <00>\n'
        cargar_documento_revisado(documento, SimpleUploadedFile('propuesta-firmada.pdf', firmado), self.actor)
        validar_documento(documento, self.actor)
        documento.refresh_from_db()
        return documento, documento.control_automatico

    def test_envio_real_de_planes_en_las_cuatro_tipologias_aplica_sin_actor_director(self):
        self.assertFalse(self.actor.is_superuser)
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(tipo=tipo):
                documento, control = self.enviar(self.unidad(tipo), 'PLANIFICACION')
                self.assertEqual((control.estado, control.aplicado, control.nota), ('automatico', True, Decimal(100)), control.hallazgos)
                self.assertEqual(control.resumen['decision_automatica']['destino'], 'automatico')
                self.assertIsNone(documento.evaluado_por)
                self.assertIsNone(documento.evaluacion)
                self.assertIsNotNone(documento.recibido_en)
                self.assertIsNone(documento.recibido_por)
                for anexo in anexos_del(documento):
                    control_anexo = anexo.control_automatico
                    self.assertTrue(control_anexo.aplicado)
                    self.assertIsNone(control_anexo.nota)
                    # Cobertura del anexo: dos FT02 aprobados y respaldados en
                    # el laboratorio, o ausencia de actividad conciliada en
                    # las tipologías sin docencia. Ninguno recibe una nota.
                    self.assertEqual(control_anexo.resumen.get('cumplimiento'),
                        100 if tipo == 'laboratorios' else None)

    def test_compra_sin_solicitud_se_envia_conforme_sin_evaluacion_de_direccion(self):
        documento, control = self.enviar(self.unidad('laboratorios'), 'PLAN-COMPRAS-ANUAL')
        self.assertEqual((control.estado, control.aplicado), ('automatico', True), control.hallazgos)
        self.assertEqual(control.resumen['decision_automatica']['destino'], 'automatico')
        self.assertFalse(control.resumen['decision_automatica']['autorizacion_financiera'])
        self.assertIsNone(documento.evaluacion)

    def test_nota_final_tardia_bajo_minimo_deriva_y_no_se_inventa_cien(self):
        documento, _ = self.enviar(self.unidad('laboratorios'), 'PLAN-COMPRAS-ANUAL')
        informe = next(d for d in construir_expediente(documento.unidad, 2025)
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')
        informe.recurso, informe.version, informe.estado = documento.recurso, 1, 'validado'
        informe.entregado_tarde = True
        informe.save()
        from apps.documentos.models.expediente import PoliticaDeCalidad
        PoliticaDeCalidad.objects.update_or_create(pk=1,
            defaults=dict(minimo_cumplimiento=70, penalizacion_entrega_tardia=40))
        confianza = dict(confiable=True, archivo_integro=True, motivos=[])
        # Aislamos sólo la penalización posterior al análisis: PDF/firmas se
        # comprueban sin sustituciones en los envíos anteriores.
        with patch('apps.documentos.presentation.automatizacion_documental._analizar', return_value=(
                confianza, [], dict(nota_calculada=100, indicadores_exigibles=[dict(codigo='USO', porcentaje=100)]))):
            control = procesar_documento(informe, usuario=self.actor)
        self.assertEqual(control.nota, 60)
        self.assertTrue(control.aplicado)
        self.assertEqual(control.resumen['decision_automatica']['destino'], 'direccion')
        self.assertTrue(control.resumen['requiere_seguimiento'])
        self.assertEqual(control.politica['minimo_cumplimiento'], 70)
