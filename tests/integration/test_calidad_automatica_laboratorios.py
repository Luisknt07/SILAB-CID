"""El paso técnico exige fuentes completas; un número de meta no las sustituye.

Sólo usa la base de pruebas y archivos temporales. El motor nunca altera la
fuente ni atribuye al Director una revisión que ya hizo el responsable.
"""
import io
import json
from copy import deepcopy
from datetime import date, datetime, time, timezone as dt_timezone
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen.canvas import Canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad, FUENTES_STOCK, _json_seguro
from apps.documentos.presentation.aprobacion_tecnica_laboratorios import registrar_aprobacion_tecnica
from apps.documentos.presentation.medicion_metas import registrar_evidencia
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.consumibles import Consumible, LoteConsumible, EntradaInventario
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva


MODULO = 'apps.documentos.presentation.calidad_automatica_laboratorios.'


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class CalidadAutomaticaLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='calidad-automatica-qa')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio calidad automática QA', slug='calidad-automatica-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Laboratorio ajeno QA', slug='calidad-automatica-ajena-qa',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        cls.externa = Unidad.objects.create(nombre='Centro I+D fuera de alcance QA', slug='calidad-automatica-externa-qa',
            dependencia='centros_id', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
        for codigo in ('PLANIFICACION', 'INFORME-SEMESTRAL'):
            DocumentoExigido.objects.update_or_create(codigo=codigo,
                defaults=dict(nombre=codigo, carpeta='planeacion', activo=True))
        for codigo, (fuente, padre) in FUENTES_STOCK.items():
            DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(nombre=codigo,
                carpeta='ejecucion', origen='sistema', fuente_reporte=fuente, activo=True, tipos_unidad=[],
                anexo_de=DocumentoExigido.objects.get(codigo=padre)))
        tipo = EquiposServicios.objects.create(codigo='TIPO-CALIDAD-QA', nombre='Equipo calidad QA',
            caracteristicas_publicas='Especificación técnica de referencia del equipo QA.')
        cls.equipo = UnidadEquipo.objects.create(equipo=tipo, laboratorio=cls.unidad,
            codigo_unidad='EQUIPO-CALIDAD-QA', numero_serie='SERIE-CALIDAD-QA')
        cls.ajeno = UnidadEquipo.objects.create(equipo=tipo, laboratorio=cls.otra, codigo_unidad='EQUIPO-CALIDAD-AJENO-QA')
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.actor)
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ESP-CALIDAD-QA', nombre='Área QA')
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Actividad calidad QA')
        cls.asignatura = Asignatura.objects.create(unidad=cls.unidad, codigo='AS-CALIDAD-QA', nombre='Asignatura QA')
        cls.tema = TemaAsignatura.objects.create(asignatura=cls.asignatura, nombre='Tema de syllabus QA',
            resultado_aprendizaje='Comprueba el procedimiento y resultado de referencia.')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-calidad-automatica-qa-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        for ruta, valor in (
            ('django.utils.timezone.localdate', date(2026, 10, 17)),
            ('django.utils.timezone.now', datetime(2026, 10, 17, 12, tzinfo=dt_timezone.utc)),
        ):
            reloj = patch(ruta, return_value=valor)
            reloj.start()
            self.addCleanup(reloj.stop)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)

    def contexto(self, unidad=None, **cambios):
        return ContextoCalidad(unidad or self.unidad, cambios.get('inicio', self.inicio), cambios.get('fin', self.fin))

    def reglas(self, lectura):
        return {h['regla'] for h in lectura['hallazgos']}

    def pdf(self, codigo):
        salida = io.BytesIO()
        pagina = Canvas(salida)
        pagina.drawString(35, 780, codigo + ': respaldo real de prueba aislada, procedimiento, alcance y resultado verificables.')
        pagina.save()
        return SimpleUploadedFile(codigo + '.pdf', salida.getvalue(), 'application/pdf')

    def evidencia(self, tipo='INVESTIGACION', codigo='CALIDAD-RESULTADO-QA', *, verificar=True, enlace='', **cambios):
        detalle = dict(proyecto='Proyecto de laboratorio QA', tipo_producto='informe',
            producto='Informe de resultados obtenidos QA', beneficiario='Comunidad universitaria QA')
        if tipo == 'TRANSFERENCIA':
            detalle.update(aceptacion='aceptado', fecha_aceptacion='2026-10-16', referencia_aceptacion='Acta de aceptación QA')
        datos = dict(tipo=tipo, codigo=codigo, fecha=date(2026, 10, 17), titulo='Resultado documentado ' + codigo,
            descripcion='Resultado ocurrido, revisado y atribuido al responsable de la unidad QA.',
            responsable=self.actor, detalle=detalle)
        datos.update(cambios)
        if enlace:
            datos['enlace'] = enlace
        return registrar_evidencia(self.unidad, self.actor, datos, verificar=verificar,
            archivo=None if enlace else self.pdf(codigo))

    def acta_uso(self, total=0):
        return self.evidencia('USO', 'CALIDAD-USO-QA', detalle={}, desde=self.inicio,
            hasta=date(2026, 10, 17), total_observado=total)

    def sellar(self, objeto):
        from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
        evento = registrar_auditoria(unidad=self.unidad, usuario=self.actor, accion='aprobar', objeto=objeto,
            descripcion='Aprobación fuente realizada en el escenario aislado QA.')
        registrar_aprobacion_tecnica(objeto, self.actor, evento=evento)
        return evento

    def acta_inventario(self):
        return self.evidencia('INVENTARIO', 'CALIDAD-INVENTARIO-QA', detalle={},
            alcance=['equipos', 'software', 'espacios', 'insumos'])

    def reserva(self, **cambios):
        datos = dict(laboratorio=self.unidad, usuario=self.actor, actividad_catalogo=self.actividad,
            fecha=date(2026, 10, 10), hora_inicio=time(8), hora_fin=time(10), estado='completada',
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            resultado_cierre='atendida', detalle_ejecucion={'registrada_en': '2026-10-10T10:00:00-05:00'})
        datos.update(cambios)
        reserva = Reserva.objects.create(**datos)
        reserva.espacios_solicitados.add(self.espacio)
        return reserva

    def plan(self, reserva=None, **cambios):
        # Sin la constancia de ejecución, la sesión no cuenta como atendida y no exige su registro.
        reserva = reserva or self.reserva(detalle_ejecucion={})
        datos = dict(unidad=self.unidad, actividad=self.actividad, tema_asignatura=self.tema,
            reserva=reserva, fecha=reserva.fecha, hora_inicio=time(8), hora_fin=time(10),
            asignatura='Asignatura QA', docente_tutor='Docente QA', carrera='Carrera QA', semestre='Primero',
            tema='Tema de syllabus QA', resultado_aprendizaje=self.tema.resultado_aprendizaje,
            estudiantes_planificados=1, responsable_tecnico=self.responsable, estado='aprobada',
            creado_por=self.actor, revisado_por=self.actor, revisado_en=timezone.now(), requiere_guia=False)
        datos.update(cambios)
        plan = PlanificacionPractica.objects.create(**datos)
        if plan.estado == 'aprobada' and plan.revisado_por_id and plan.revisado_en:
            self.sellar(plan)
        return plan

    def guia(self, plan):
        contenido = {campo: 'Contenido revisado y aprobado de referencia QA' for campo in (
            'asignatura', 'carrera_semestre', 'docente_responsable', 'laboratorio', 'categoria_uso',
            'duracion', 'resultado_aprendizaje', 'objetivos', 'procedimiento', 'fundamento_teorico',
            'medidas_seguridad', 'resultados_esperados', 'criterios_evaluacion', 'manejo_residuos', 'bibliografia')}
        contenido['maximo_estudiantes'] = 1
        guia = GuiaActividadReserva.objects.create(actividad=self.actividad, titulo='Guía aprobada QA',
            codigo_guia='GUIA-CALIDAD-QA', es_estructurada=True, es_vigente=True,
            estado_publicacion='publicada', aprobado_por=self.actor, aprobado_en=timezone.now(), contenido=contenido)
        plan.guia = guia
        plan.requiere_guia = True
        plan.save(update_fields=['guia', 'requiere_guia'])
        self.sellar(guia)
        self.sellar(plan)
        return guia

    def test_los_anexos_retirados_no_se_automatizan(self):
        # Lo que salió del expediente (documentos.0024) y lo que absorbieron los cinco anexos del informe
        # (documentos.0025) ya no tiene reglas propias: lo revisa el anexo que lo reúne.
        for codigo in ('INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE',
                       'PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA', 'ACCIONES-MEJORA'):
            with self.subTest(codigo=codigo):
                self.assertNotIn(codigo, FUENTES_STOCK)
                lectura = self.contexto().analizar(codigo)
                self.assertEqual(self.reglas(lectura), {'DOCUMENTO_NO_AUTOMATIZABLE'})
                self.assertFalse(lectura['automatico'])

    def test_ft02_detecta_cambio_de_programacion_aprobada(self):
        plan = self.plan()
        self.guia(plan)
        inicial = self.contexto().analizar('PRACTICAS-FT02')
        plan.tema = 'Tema modificado después de la aprobación'
        plan.save(update_fields=['tema'])
        modificado = self.contexto().analizar('PRACTICAS-FT02')
        self.assertFalse(modificado['automatico'])
        self.assertNotEqual(inicial['fuentes'], modificado['fuentes'])
        self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(modificado))
        self.sellar(plan)
        revisado = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(revisado['automatico'], revisado['hallazgos'])

    def test_huella_ignora_indicador_visual_de_plazo_pero_conserva_datos_del_control(self):
        inicial = dict(mes='2026-12', dentro_plazo=True, verificada=True, fuente=dict(id=21, sha256='a'))
        siguiente = dict(inicial, dentro_plazo=False)
        self.assertEqual(_json_seguro(inicial), _json_seguro(siguiente))
        siguiente['fuente'] = dict(id=21, sha256='b')
        self.assertNotEqual(_json_seguro(inicial), _json_seguro(siguiente))

    def test_base_fuera_de_las_cuatro_no_consulta_fuentes_ni_cambia_su_politica(self):
        # El proveedor institucional de tipologías puede leer su propio catálogo.
        # Lo que esta política no debe leer son fuentes documentales ajenas.
        self.externa.codigo_base
        with self.assertNumQueries(0):
            lectura = self.contexto(self.externa).analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['fuera_alcance'])
        self.assertFalse(lectura['automatico'])

    def test_codigo_desconocido_principal_y_fuente_personalizada_nunca_pasan(self):
        for codigo in ('PERSONALIZADO-QA', 'PLANIFICACION', 'INFORME-SEMESTRAL'):
            with self.subTest(codigo=codigo):
                lectura = self.contexto().analizar(codigo)
                self.assertEqual(self.reglas(lectura), {'DOCUMENTO_NO_AUTOMATIZABLE'})
                self.assertFalse(lectura['automatico'])
        DocumentoExigido.objects.filter(codigo='REGISTRO-USO').update(fuente_reporte='cursos')
        self.assertIn('DOCUMENTO_NO_AUTOMATIZABLE', self.reglas(self.contexto().analizar('REGISTRO-USO')))

    def test_origen_padre_y_aplicabilidad_se_comprueban_adicionalmente_al_codigo(self):
        for cambios in (dict(origen='unidad'), dict(anexo_de=None), dict(tipos_unidad=['observatorios']), dict(activo=False)):
            with self.subTest(cambios=cambios):
                with self.atomic_subtest():
                    DocumentoExigido.objects.filter(codigo='PRACTICAS-FT02').update(**cambios)
                    self.assertFalse(self.contexto().analizar('PRACTICAS-FT02')['automatico'])

    def atomic_subtest(self):
        """Cada mutación de catálogo se revierte sin interferir en el siguiente caso."""
        from contextlib import contextmanager
        from django.db import transaction
        @contextmanager
        def contexto():
            with transaction.atomic():
                yield
                transaction.set_rollback(True)
        return contexto()

    def test_periodo_futuro_no_pasa_como_universo_vacio(self):
        lectura = self.contexto(inicio=date(2027, 1, 1), fin=date(2027, 6, 30)).analizar('REGISTRO-USO')
        self.assertIn('PERIODO_NO_MEDIBLE', self.reglas(lectura))

    def test_datos_demo_o_motor_desactivado_impiden_auto_aunque_la_fuente_este_completa(self):
        self.evidencia()
        self.assertTrue(self.contexto().analizar('INVESTIGACION')['automatico'])
        for configuracion in (dict(MEDICION_SOLO_DEMO=True), dict(MEDICION_METAS_HABILITADA=False)):
            with self.subTest(configuracion=configuracion), override_settings(**configuracion):
                self.assertFalse(self.contexto().analizar('INVESTIGACION')['automatico'])
        self.unidad.nombre = '[DEMO REPORTES] Laboratorio QA'
        self.assertIn('MODO_DEMO', self.reglas(self.contexto().analizar('INVESTIGACION')))

    def test_fuente_revisada_de_investigacion_y_transferencia_no_duplica_revision_director(self):
        # Con un resultado revisado basta: la transferencia vacía no exige declararse aparte.
        self.evidencia('INVESTIGACION', codigo='CALIDAD-INVESTIGACION')
        lectura = self.contexto().analizar('INVESTIGACION')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        self.evidencia('TRANSFERENCIA', codigo='CALIDAD-TRANSFERENCIA')
        lectura = self.contexto().analizar('INVESTIGACION')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        for parte in ('investigacion', 'transferencia'):
            self.assertEqual(lectura['fuentes']['datos'][parte]['resultados']['reales'], 1)
        self.assertIsNone(lectura['cumplimiento'])

    def test_resultado_vacio_o_solo_enlace_requiere_excepcion_identificable(self):
        self.assertIn('RESULTADOS_SIN_DECLARACION', self.reglas(self.contexto().analizar('INVESTIGACION')))
        self.evidencia(enlace='https://example.org/resultado-revisado-qa')
        lectura = self.contexto().analizar('INVESTIGACION')
        self.assertEqual(lectura['fuentes']['datos']['investigacion']['resultados']['reales'], 1)
        self.assertIn('RESULTADO_ENLACE_EXTERNO', self.reglas(lectura))

    def test_un_registro_anulado_no_cuenta_como_resultado_declarado(self):
        # Como en el FabLab 2026-B: la única transferencia era de demostración y se anuló.
        from apps.documentos.presentation.medicion_metas import rectificar_evidencia
        transferencia = self.evidencia('TRANSFERENCIA', codigo='CALIDAD-TRANSFERENCIA-ANULADA', verificar=False)
        rectificar_evidencia(self.unidad, self.actor, transferencia.pk, 'Registro de demostración.')
        lectura = self.contexto().analizar('INVESTIGACION')
        self.assertIn('RESULTADOS_SIN_DECLARACION', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_borrador_y_promocion_directa_sin_auditoria_no_son_verificacion(self):
        e = self.evidencia(verificar=False)
        self.assertIn('FUENTE_SIN_VERIFICAR', self.reglas(self.contexto().analizar('INVESTIGACION')))
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(estado='validado', validado_por=self.actor,
            validado_en=timezone.now())
        self.assertFalse(self.contexto().analizar('INVESTIGACION')['automatico'])

    def test_demo_verificado_no_se_vuelve_real_al_quitar_la_bandera(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            e = self.evidencia()
        self.assertIn('FUENTE_DEMO', self.reglas(self.contexto().analizar('INVESTIGACION')))
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(demostracion=False)
        self.assertIn('FUENTE_SIN_VERIFICAR', self.reglas(self.contexto().analizar('INVESTIGACION')))

    def test_archivo_alterado_o_detalle_sustituido_bloquea_resultado_previamente_verificado(self):
        e = self.evidencia()
        e.detalle['producto'] = 'Producto distinto de lo que se revisó'
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle=e.detalle)
        self.assertFalse(self.contexto().analizar('INVESTIGACION')['automatico'])
        e = self.evidencia(codigo='CALIDAD-OTRO-RESULTADO')
        with e.recurso.archivo.storage.open(e.recurso.archivo.name, 'wb') as archivo:
            archivo.write(self.pdf('Resultado sustituido').read())
        self.assertIn('FUENTE_SIN_VERIFICAR', self.reglas(self.contexto().analizar('INVESTIGACION')))

    def test_sesion_docente_sin_ft02_y_atendida_sin_ft03_son_anomalias(self):
        reserva = self.reserva()
        self.assertIn('SESION_SIN_FT02', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))
        self.plan(reserva=reserva)
        self.assertIn('SESION_ATENDIDA_SIN_FT03', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))

    def test_ft02_completo_y_aprobacion_atribuida_permiten_consolidado_nativo(self):
        self.plan()
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        self.assertEqual(lectura['cumplimiento'], 100)

    def test_estado_aprobado_sin_quien_y_cuando_no_autoacredita_ft02(self):
        self.plan(revisado_por=None, revisado_en=None)
        self.assertIn('FT02_APROBACION_SIN_RESPONSABLE', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))

    def test_guia_aprobada_con_syllabus_no_exige_revision_repetida_del_director(self):
        plan = self.plan()
        self.guia(plan)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        plan.tema_asignatura = None
        plan.save(update_fields=['tema_asignatura'])
        self.assertIn('RESPALDO_PRACTICA_INCOMPLETO', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))

    def test_ft03_validado_sin_adjunto_no_pasa_aunque_tenga_asistencia(self):
        plan = self.plan()
        ejecucion = EjecucionPractica.objects.create(planificacion=plan, fecha_ejecucion=plan.fecha,
            hora_inicio_real=time(8), hora_fin_real=time(10), estudiantes_asistentes=1,
            responsable_tecnico=self.responsable, recursos_utilizados='Equipo QA', cumplimiento_resultado='si',
            estado='validada', validado_por=self.actor, validado_en=timezone.now(), creado_por=self.actor,
            detalle_operativo={'participantes': [dict(id='QA-1', nombre='Participante QA', asistencia_codigo='asistio')]})
        self.assertIn('RESPALDO_PRACTICA_INCOMPLETO', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))
        evidencia = EvidenciaPractica(ejecucion=ejecucion, tipo='bitacora', nombre_original='bitacora-qa.pdf',
            descripcion='Bitácora identificada de la práctica y comprobación de resultado.')
        evidencia.archivo.save('bitacora-qa.pdf', self.pdf('FT03 respaldado'), save=True)
        self.sellar(ejecucion)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])

    def test_anexo_vacio_no_es_conforme_sin_universo_observado_independiente(self):
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertIn('UNIVERSO_SIN_CONCILIAR', self.reglas(lectura))
        self.acta_uso()
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        self.assertIsNone(lectura['cumplimiento'])

    def test_cien_por_ciento_con_fuente_demo_no_autoriza_uso(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            acta = self.acta_uso()
        medicion = dict(mediciones_porcentuales={'USO': dict(numerador=4, denominador=4, pendiente=False,
            fuentes=[dict(evidencia=acta.pk)])})
        with patch(MODULO + 'registros_de_gestion', return_value=medicion):
            lectura = self.contexto().analizar('REGISTRO-USO')
        self.assertEqual(lectura['cumplimiento'], 100)
        self.assertIn('CONCILIACION_SIN_FUENTE_REAL', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_inventario_exige_acta_custodio_localizacion_y_verificacion_fisica(self):
        self.acta_inventario()
        lectura = self.contexto().analizar('EQUIPAMIENTO')
        self.assertIn('EQUIPO_SIN_IDENTIFICACION', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(codigo_bien='BIEN-QA', custodio='Custodio QA',
            ubicacion_especifica='Área QA', existencia_verificada=True, existencia_verificada_por=self.actor,
            existencia_verificada_en=timezone.now())
        lectura = self.contexto().analizar('EQUIPAMIENTO')
        self.assertFalse({'EQUIPO_SIN_IDENTIFICACION', 'FALTA_ACTA_INTEGRAL'} & self.reglas(lectura))
        self.assertIn('inventario', lectura['fuentes']['datos'])

    def test_saldo_lotes_y_licencias_inconsistentes_no_se_ocultan_por_acta_verificada(self):
        self.acta_inventario()
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='CALIDAD-INSUMO-QA', nombre='Material QA',
            stock_total=Decimal('5'), unidad_medida='kg', ubicacion='Bodega QA')
        lote = LoteConsumible.objects.create(consumible=insumo, codigo='LOTE-CALIDAD-QA', cantidad_inicial=Decimal('5'),
            cantidad_actual=Decimal('4'), bodega='Bodega QA', documento_recepcion='Acta recepción QA')
        LoteConsumible.objects.filter(pk=lote.pk).update(fecha_vencimiento=date(2026, 9, 1))
        software = SoftwareDisponible.objects.create(unidad=self.unidad, codigo='SW-CALIDAD-QA', nombre='Software QA',
            licencias_totales=1, licencias_disponibles=1)
        SoftwareDisponible.objects.filter(pk=software.pk).update(licencias_disponibles=2)
        lectura = self.contexto().analizar('EQUIPAMIENTO')
        self.assertTrue({'SALDO_NO_CONCILIADO', 'LOTE_INCONSISTENTE', 'LICENCIAS_INCONSISTENTES'} <= self.reglas(lectura))

    def test_solo_equipos_de_la_unidad_o_compartidos_entran_en_el_alcance(self):
        self.acta_inventario()
        primera = self.contexto().analizar('EQUIPAMIENTO')['fuentes']['datos']['inventario']['equipos']
        self.assertEqual({e['id'] for e in primera}, {self.equipo.pk})
        self.ajeno.laboratorios.add(self.unidad)
        segunda = self.contexto().analizar('EQUIPAMIENTO')['fuentes']['datos']['inventario']['equipos']
        self.assertEqual({e['id'] for e in segunda}, {self.equipo.pk, self.ajeno.pk})

    def test_mantenimiento_cien_con_espacio_sin_cobertura_no_autoaprueba(self):
        medicion = dict(mediciones_porcentuales={'MANTENIMIENTO': dict(numerador=1, denominador=1,
            pendiente=False, equipos={}, programadas_futuras=0)})
        infra = dict(planes=[], ejecuciones=[], pendientes=[], espacios_sin_cobertura=[dict(pk=self.espacio.pk)])
        with patch(MODULO + 'registros_de_gestion', return_value=medicion), patch(MODULO + 'infraestructura_documentada', return_value=infra):
            lectura = self.contexto().analizar('EQUIPAMIENTO')
        # El anexo del equipamiento respalda la meta de mantenimiento: su cumplimiento es el del programa crítico.
        self.assertEqual(lectura['cumplimiento'], 100)
        self.assertIn('INFRA_SIN_COBERTURA', self.reglas(lectura))
        self.assertIn('mantenimiento', lectura['fuentes']['datos'])
        self.assertIn('funcionalidad', lectura['fuentes']['datos'])

    def test_programacion_futura_completa_no_equivale_a_mora_ni_cien_por_ciento(self):
        medida = dict(numerador=0, denominador=0, pendiente=True, programadas_futuras=1,
            equipos=dict(universo_conocido=True, equipos_sin_plan=0, equipos_sin_responsable=0,
                equipos_sin_programacion=0))
        infra = dict(alcance_declarado=True, alcance_contradictorio=False, espacios_sin_cobertura=[],
            planes=[], ejecuciones=[], pendientes=[])
        # La funcionalidad se aísla: un equipo con prueba operativa vigente no deja hallazgos propios.
        funcionalidad = dict(universo_equipos=1, filas=[], ultimas=[dict(equipo_id=self.equipo.pk, pendiente=False,
            resultado_funcional='operativo', no_apto=False)])
        # El inventario del mismo anexo está completo: acta verificada y equipo identificado.
        self.acta_inventario()
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(codigo_bien='BIEN-QA', custodio='Custodio QA',
            ubicacion_especifica='Área QA', existencia_verificada=True, existencia_verificada_por=self.actor,
            existencia_verificada_en=timezone.now())
        with patch(MODULO + 'registros_de_gestion', return_value=dict(mediciones_porcentuales={'MANTENIMIENTO': medida})), patch(
                MODULO + 'infraestructura_documentada', return_value=infra), patch(
                MODULO + 'funcionalidad_documentada', return_value=funcionalidad):
            lectura = self.contexto().analizar('EQUIPAMIENTO')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        self.assertIsNone(lectura['cumplimiento'])

    def test_equipamiento_sin_programacion_critica_pide_revision_en_los_dos_periodos(self):
        # Sin el plan de mantenimiento aparte, la meta de mantenimiento tiene anexo en A y en B.
        for inicio, fin in ((date(2026, 1, 1), date(2026, 6, 30)), (self.inicio, self.fin)):
            with self.subTest(inicio=inicio):
                lectura = self.contexto(inicio=inicio, fin=fin).analizar('EQUIPAMIENTO')
                self.assertIn('MANTENIMIENTO_SIN_UNIVERSO', self.reglas(lectura))
                self.assertFalse(lectura['automatico'])

    def test_prueba_no_operativa_en_equipo_disponible_es_bloqueo_sin_cambiar_estado(self):
        self.evidencia('FUNCIONALIDAD', 'CALIDAD-FUNC-QA', detalle=dict(equipo_id=self.equipo.pk,
            procedimiento='Ciclo completo de ensayo con carga de referencia.', criterio='Concluir sin alarmas.',
            resultado_funcional='no_operativo', hallazgos_funcionales='Interrumpe el ciclo por sobretemperatura.'))
        anterior = UnidadEquipo.objects.filter(pk=self.equipo.pk).values().get()
        lectura = self.contexto().analizar('EQUIPAMIENTO')
        self.assertIn('NO_OPERATIVO_DISPONIBLE', self.reglas(lectura))
        self.assertEqual(UnidadEquipo.objects.filter(pk=self.equipo.pk).values().get(), anterior)
        self.assertIsNone(lectura['cumplimiento'])

    def test_cambiar_nombre_de_cuenta_impreso_en_movimiento_cambia_fuente_sin_exponer_credenciales(self):
        # Los préstamos ya no son anexo; la identidad impresa se comprueba en los movimientos del inventario.
        self.acta_inventario()
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='INSUMO-IDENTIDAD-QA', nombre='Material QA',
            unidad_medida='kg', ubicacion='Bodega QA')
        EntradaInventario.objects.create(unidad=self.unidad, consumible=insumo, tipo='ingreso',
            cantidad=Decimal('1'), usuario=self.actor, nota='Recepción QA', referencia='ACTA-ID-QA')
        fuente = self.contexto().analizar('EQUIPAMIENTO')['fuentes']
        get_user_model().objects.filter(pk=self.actor.pk).update(first_name='Nombre actualizado')
        otra = self.contexto().analizar('EQUIPAMIENTO')['fuentes']
        self.assertNotEqual(fuente, otra)
        identidad = otra['datos']['inventario']['movimientos'][0]['usuario']
        self.assertEqual(set(identidad), {'id', 'username', 'nombre'})
        self.assertNotIn('password', json.dumps(otra))

    def test_drift_de_ficha_catalogo_software_espacios_y_articulo_invalida_fuentes_de_inventario(self):
        self.acta_inventario()
        software = SoftwareDisponible.objects.create(unidad=self.unidad, codigo='SW-DRIFT-QA',
            nombre='Software de referencia QA', tipo_acceso='instalacion')
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='INSUMO-DRIFT-QA', nombre='Material de referencia',
            unidad_medida='kg', ubicacion='Bodega QA')
        fuente = self.contexto().analizar('EQUIPAMIENTO')['fuentes']
        casos = (
            (EquiposServicios, self.equipo.equipo_id, 'especificaciones', {'resolucion': 'Valor técnico distinto'}),
            (EquiposServicios, self.equipo.equipo_id, 'caracteristicas_publicas', 'Otras características técnicas'),
            (EquiposServicios, self.equipo.equipo_id, 'marca', 'Marca distinta'),
            (SoftwareDisponible, software.pk, 'tipo_acceso', 'red'),
            (EspacioReservable, self.espacio.pk, 'reservable', False),
            (Consumible, insumo.pk, 'nombre', 'Otro artículo mostrado'),
            (Consumible, insumo.pk, 'presentacion', 'Otro envase de recepción'),
        )
        for modelo, pk, campo, valor in casos:
            with self.subTest(modelo=modelo.__name__, campo=campo), self.atomic_subtest():
                modelo.objects.filter(pk=pk).update(**{campo: valor})
                self.assertNotEqual(self.contexto().analizar('EQUIPAMIENTO')['fuentes'], fuente)

    def test_movimiento_cambia_respaldo_aunque_cantidad_y_saldo_se_conservan(self):
        self.acta_inventario()
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='INSUMO-MOV-DRIFT-QA', nombre='Material QA',
            unidad_medida='kg', ubicacion='Bodega QA')
        lote = LoteConsumible.objects.create(consumible=insumo, codigo='LOTE-MOV-DRIFT-QA',
            cantidad_inicial=Decimal('5'), cantidad_actual=0, bodega='Bodega QA', documento_recepcion='Recepción QA')
        movimiento = EntradaInventario.objects.create(unidad=self.unidad, consumible=insumo, lote_inventario=lote,
            tipo='ingreso', cantidad=Decimal('5'), usuario=self.actor, nota='Recepción comprobada', referencia='ACTA-QA')
        # Los movimientos de insumos viajan en el inventario: su respaldo cambia la fuente del mismo anexo.
        fuente = self.contexto().analizar('EQUIPAMIENTO')['fuentes']
        EntradaInventario.objects.filter(pk=movimiento.pk).update(nota='Referencia corregida sin alterar el saldo')
        otra = self.contexto().analizar('EQUIPAMIENTO')['fuentes']
        self.assertNotEqual(fuente, otra)
        self.assertEqual(fuente['datos']['inventario']['insumos'][0]['saldo'], otra['datos']['inventario']['insumos'][0]['saldo'])
        self.assertEqual(len(otra['datos']['inventario']['movimientos']), 1)

    def test_seguridad_falta_control_mensual_y_protocolo_no_equivale_a_cero_usuarios(self):
        lectura = self.contexto().analizar('INDUCCION-SEGURIDAD')
        self.assertTrue({'CONTROL_MENSUAL_FALTANTE', 'PROTOCOLO_SIN_VALIDAR'} <= self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_protocolo_cargado_despues_del_corte_no_respalda_mes_anterior(self):
        exigido, _ = DocumentoExigido.objects.get_or_create(codigo='PROTOCOLO-BIOSEGURIDAD',
            defaults=dict(nombre='Protocolo QA', carpeta='ejecucion'))
        evidencia = self.evidencia()
        DocumentoExpediente.objects.create(unidad=self.unidad, exigido=exigido, anio=2026,
            estado='validado', firma_verificada=True, recurso=evidencia.recurso, version=1,
            cargado_en=timezone.make_aware(datetime(2026, 10, 17, 8)))
        lectura = self.contexto(fin=date(2026, 9, 30)).analizar('INDUCCION-SEGURIDAD')
        self.assertIn('PROTOCOLO_SIN_VALIDAR', self.reglas(lectura))

    def test_desechos_incompletos_y_traslado_antes_de_generacion_generan_excepcion(self):
        desecho = RegistroDesecho.objects.create(unidad=self.unidad, fecha_generacion=date(2026, 10, 10),
            clase='especial', nombre='Residuo QA', cantidad=Decimal('1'), registrado_por=self.actor)
        RegistroDesecho.objects.filter(pk=desecho.pk).update(etapa='entregado', fecha_entrega=date(2026, 10, 1))
        lectura = self.contexto().analizar('INDUCCION-SEGURIDAD')
        self.assertTrue({'DESECHO_INCOMPLETO', 'TRASLADO_ANTERIOR_GENERACION', 'UNIVERSO_SIN_CONCILIAR'} <= self.reglas(lectura))

    def test_lectura_cacheada_es_json_estable_y_no_modifica_datos_ni_auditoria(self):
        evidencia = self.evidencia()
        antes = (EvidenciaGestionUnidad.objects.filter(pk=evidencia.pk).values().get(),
                 RegistroAuditoriaUnidad.objects.count(), DocumentoExpediente.objects.count())
        contexto = self.contexto()
        primera = contexto.analizar('INVESTIGACION')
        serializado = json.dumps(primera, sort_keys=True)
        with self.assertNumQueries(0):
            segunda = contexto.analizar('INVESTIGACION')
        self.assertEqual(serializado, json.dumps(segunda, sort_keys=True))
        primera['fuentes']['datos']['investigacion']['resultados']['filas'][0]['producto'] = 'Mutación ajena al contexto'
        self.assertEqual(contexto.analizar('INVESTIGACION'), segunda)
        self.assertEqual(antes, (EvidenciaGestionUnidad.objects.filter(pk=evidencia.pk).values().get(),
            RegistroAuditoriaUnidad.objects.count(), DocumentoExpediente.objects.count()))

    def test_fuente_canonica_de_practicas_se_lee_una_vez_en_el_anexo(self):
        self.plan()
        from apps.documentos.presentation.cumplimiento_practicas import conteos_del_periodo
        from apps.documentos.presentation.aprobacion_tecnica_laboratorios import capturas_tecnicas
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with patch(MODULO + 'conteos_del_periodo', wraps=conteos_del_periodo) as fuente, patch(
                MODULO + 'capturas_tecnicas', wraps=capturas_tecnicas) as capturas, CaptureQueriesContext(connection) as consultas:
            contexto = self.contexto()
            # Planificación, ejecución y guías se revisan con una sola lectura de la fuente.
            contexto.analizar('PRACTICAS-FT02')
            self.assertEqual(fuente.call_count, 1)
            self.assertEqual(capturas.call_count, 1)
        self.assertEqual(sum('aprobacion_tecnica' in q['sql'] for q in consultas), 1)

    def test_aprobacion_parcial_legacy_no_se_reconstruye_automaticamente(self):
        plan = self.plan()
        evento = RegistroAuditoriaUnidad.objects.get(entidad=plan._meta.label, objeto_id=str(plan.pk), accion='aprobar')
        evento.datos_nuevos = {'estado': 'aprobada', 'tema': plan.tema}
        evento.save(update_fields=['datos_nuevos'])
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_cambiar_syllabus_o_agregar_vinculo_sin_revision_no_habilita_guia(self):
        plan = self.plan()
        self.guia(plan)
        self.assertTrue(self.contexto().analizar('PRACTICAS-FT02')['automatico'])
        TemaAsignatura.objects.filter(pk=self.tema.pk).update(resultado_aprendizaje='Resultado académico sustituido.')
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertIn('VINCULO_SYLLABUS_SIN_REVISION', self.reglas(lectura))
        # Una revisión nueva y atribuida del FT02 sí respalda el nuevo vínculo;
        # no se obliga al Director a volver a revisar la misma guía.
        self.sellar(plan)
        self.assertTrue(self.contexto().analizar('PRACTICAS-FT02')['automatico'])

    def test_contacto_o_permisos_del_responsable_no_cambian_identidad_documentada(self):
        self.plan()
        ResponsableUnidad.objects.filter(pk=self.responsable.pk).update(
            telefono='0999999999', permisos_operativos={'practicas': True})
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])

    def test_cambiar_docente_escenario_o_estado_invalida_aprobacion_completa(self):
        plan = self.plan()
        self.assertTrue(self.contexto().analizar('PRACTICAS-FT02')['automatico'])
        for cambios in (dict(docente_tutor='Otro docente'), dict(estado='observada')):
            with self.subTest(cambios=cambios), self.atomic_subtest():
                PlanificacionPractica.objects.filter(pk=plan.pk).update(**cambios)
                self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))
        plan.reserva.espacios_solicitados.clear()
        self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))

    def test_flujo_real_de_aprobacion_ft02_captura_huella_dentro_del_evento(self):
        plan = self.plan(estado='revision', revisado_por=None, revisado_en=None)
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('accion_planificacion_practica', args=[self.unidad.slug, plan.pk]),
            {'accion': 'aprobar'})
        self.assertEqual(respuesta.status_code, 302)
        evento = RegistroAuditoriaUnidad.objects.filter(entidad=plan._meta.label,
            objeto_id=str(plan.pk), accion='aprobar').get()
        self.assertEqual(evento.datos_nuevos['aprobacion_tecnica']['actor'], self.actor.pk)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])

    def test_flujo_real_de_guia_captura_contenido_y_cambio_posterior_exige_revision(self):
        plan = self.plan()
        guia = self.guia(plan)
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(estado_publicacion='revision')
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('cambiar_estado_guia_practica', args=[guia.pk]), {'accion': 'aprobar'})
        self.assertEqual(respuesta.status_code, 302)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        guia.refresh_from_db()
        guia.contenido['procedimiento'] = 'Procedimiento sustituido después de aprobar.'
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(contenido=guia.contenido)
        self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(self.contexto().analizar('PRACTICAS-FT02')))

    def test_validar_ft03_por_flujo_real_firma_adjuntos_y_sustituir_bytes_invalida(self):
        plan = self.plan()
        self.guia(plan)
        ejecucion = EjecucionPractica.objects.create(planificacion=plan, fecha_ejecucion=plan.fecha,
            hora_inicio_real=time(8), hora_fin_real=time(10), estudiantes_asistentes=1,
            responsable_tecnico=self.responsable, recursos_utilizados='Equipo QA', cumplimiento_resultado='si',
            estado='revision', creado_por=self.actor,
            detalle_operativo={'participantes': [dict(id='QA-1', nombre='Participante QA', asistencia_codigo='asistio')]})
        adjunto = EvidenciaPractica(ejecucion=ejecucion, tipo='bitacora', nombre_original='ensayo-qa.pdf',
            descripcion='Desarrollo identificado y resultado verificado del ensayo.')
        adjunto.archivo.save('ensayo-qa.pdf', self.pdf('Bitácora revisión FT03'), save=True)
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('accion_ejecucion_practica', args=[self.unidad.slug, plan.pk]),
            {'accion': 'validar'})
        self.assertEqual(respuesta.status_code, 302)
        ejecucion.refresh_from_db()
        self.assertEqual(ejecucion.estado, 'validada')
        evento = RegistroAuditoriaUnidad.objects.filter(entidad=ejecucion._meta.label,
            objeto_id=str(ejecucion.pk), accion='aprobar').get()
        self.assertEqual(len(evento.datos_nuevos['aprobacion_tecnica']['captura']['adjuntos']), 1)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertTrue(lectura['automatico'], lectura['hallazgos'])
        with adjunto.archivo.storage.open(adjunto.archivo.name, 'wb') as archivo:
            archivo.write(self.pdf('Bitácora sustituida después de la revisión').read())
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertIn('APROBACION_TECNICA_NO_VERIFICABLE', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_guia_pdf_respaldo_aprobada_en_flujo_real_congela_archivo_y_actor(self):
        plan = self.plan()
        guia = self.guia(plan)
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(estado_publicacion='revision')
        respaldo = GuiaActividadReserva.objects.create(actividad=self.actividad, titulo='PDF de respaldo QA',
            codigo_guia='PDF-CALIDAD-QA', estado_publicacion='revision', es_estructurada=False,
            archivo=self.pdf('Guía PDF externa revisada'))
        self.client.force_login(self.actor)
        respuesta = self.client.post(reverse('cambiar_estado_guia_practica', args=[guia.pk]), {'accion': 'aprobar'})
        self.assertEqual(respuesta.status_code, 302)
        evento = RegistroAuditoriaUnidad.objects.get(entidad=respaldo._meta.label,
            objeto_id=str(respaldo.pk), accion='aprobar')
        sello = evento.datos_nuevos['aprobacion_tecnica']
        self.assertEqual(sello['actor'], self.actor.pk)
        self.assertTrue(sello['captura']['campos']['archivo']['disponible'])
        self.assertEqual(len(sello['captura']['campos']['archivo']['sha256']), 64)

    def test_sello_demo_no_se_promueve_a_real_al_cambiar_configuracion(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            self.plan()
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        self.assertIn('APROBACION_TECNICA_DEMO', self.reglas(lectura))
        self.assertFalse(lectura['automatico'])

    def test_sucesora_no_invalida_contenido_de_guia_y_ft02_usados_en_ft03_historico(self):
        plan = self.plan()
        guia = self.guia(plan)
        ejecucion = EjecucionPractica.objects.create(planificacion=plan, fecha_ejecucion=plan.fecha,
            hora_inicio_real=time(8), hora_fin_real=time(10), estudiantes_asistentes=1,
            responsable_tecnico=self.responsable, recursos_utilizados='Equipo QA', cumplimiento_resultado='si',
            estado='validada', validado_por=self.actor, validado_en=timezone.now(), creado_por=self.actor,
            detalle_operativo={'participantes': [dict(id='QA-1', nombre='Participante QA', asistencia_codigo='asistio')]})
        adjunto = EvidenciaPractica(ejecucion=ejecucion, tipo='bitacora', nombre_original='historica-qa.pdf',
            descripcion='Desarrollo identificado con la versión utilizada en la práctica.')
        adjunto.archivo.save('historica-qa.pdf', self.pdf('Versión histórica FT03'), save=True)
        self.sellar(ejecucion)
        self.assertTrue(self.contexto().analizar('PRACTICAS-FT02')['automatico'])
        PlanificacionPractica.objects.filter(pk=plan.pk).update(es_version_vigente=False)
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(es_vigente=False)
        lectura = self.contexto().analizar('PRACTICAS-FT02')
        # No se simula una nueva reserva: la sesión existente apunta a su FT02
        # histórico. La aprobación de la ejecución sigue verificable con el contenido que usó;
        # el anexo revisa aparte la planificación y la guía sustituidas.
        self.assertFalse([h for h in lectura['hallazgos'] if h['regla'] == 'APROBACION_TECNICA_NO_VERIFICABLE'
                          and h['entidad'] == ejecucion._meta.label])

    def test_aprobacion_tecnica_antigua_no_se_completa_y_actor_ajeno_no_puede_registrarla(self):
        from django.core.exceptions import ValidationError
        plan = self.plan()
        evento = RegistroAuditoriaUnidad.objects.get(entidad=plan._meta.label, objeto_id=str(plan.pk), accion='aprobar')
        RegistroAuditoriaUnidad.objects.filter(pk=evento.pk).update(creado_en=timezone.make_aware(datetime(2025, 1, 1)))
        evento.refresh_from_db()
        with self.assertRaises(ValidationError):
            registrar_aprobacion_tecnica(plan, self.actor, evento=evento)
        ajeno = get_user_model().objects.create_user(username='calidad-aprobador-ajeno')
        with self.assertRaises(ValidationError):
            registrar_aprobacion_tecnica(plan, ajeno, evento=evento)

    def test_fuentes_eliminan_solo_tiempos_de_consulta_y_conservan_fechas_de_evidencia(self):
        datos = dict(calculado_en=timezone.now(), consultado_en=timezone.now(),
            fecha=date(2026, 10, 17), contenido=dict(sha256='a' * 64, cantidad=Decimal('1.50')))
        fuente = _json_seguro(deepcopy(datos))
        self.assertEqual(fuente, dict(fecha='2026-10-17', contenido=dict(sha256='a' * 64, cantidad='1.50')))
        self.assertIn('calculado_en', datos)
