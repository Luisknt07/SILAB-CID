"""Reglas centrales del semestre, archivo firmable y consulta de avance de Dirección."""
from copy import deepcopy
from datetime import date, time, timedelta
from io import BytesIO

from django.urls import reverse
from pypdf import PdfReader

from apps.documentos.presentation.expediente_redaccion import obtener_redaccion, filas_del_plan
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import PlanificacionPractica
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ProgramacionReserva, Reserva
from tests.integration.test_expediente_redaccion import BaseDeRedaccion, PLAN_COMPLETO
from tests.integration.utiles import abrir_entrega


class PlanificacionEstandarTests(BaseDeRedaccion):
    def setUp(self):
        self.client.force_login(self.coordinador)
        self.plan = abrir_entrega(self.documento('PLANIFICACION'))
        for numero in range(2):
            asignatura = Asignatura.objects.create(unidad=self.unidad, codigo=f'CURSO-{numero}', nombre=f'Curso {numero}')
            for tema in range(2):
                TemaAsignatura.objects.create(asignatura=asignatura, orden=tema + 1, nombre=f'Tema {tema}')

    def test_carga_del_semestre_fija_meta_y_el_editor_no_muestra_ejecucion(self):
        redaccion = obtener_redaccion(self.plan)
        redaccion.save()
        anterior = deepcopy(redaccion.contenido)
        respuesta = self.client.get(self.ruta_editor(self.plan))
        self.assertEqual(respuesta.status_code, 200)
        dato = next(d for s in respuesta.context['secciones'] for d in s['campos'] if d['campo'].tipo == 'actividades')
        filas = {f['codigo']: f for f in dato['filas']}
        self.assertEqual(filas['PRACTICAS']['meta'], '2')  # Referencia de unidad; el catálogo no es programación.
        self.assertEqual(filas['GUIAS']['meta'], '1')
        self.assertEqual(dato['metas_estandar']['carga_docente']['sesiones_programadas'], 0)
        self.assertTrue(dato['metas_estandar']['carga_docente']['avisos'])
        # La ejecución va en el anexo de prácticas académicas (documentos.0025).
        self.assertEqual(filas['PRACTICAS']['nombre_reporte'], 'Prácticas académicas: planificación, ejecución y guías')
        self.assertNotContains(respuesta, 'Seguimiento al corte')
        self.assertNotContains(respuesta, 'data-plan-seguimiento')
        self.assertNotContains(respuesta, 'type="number" name="act__')
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido, anterior)

    def test_el_servidor_ignora_numeros_enviados_y_conserva_la_regla_guardada(self):
        redaccion = obtener_redaccion(self.plan)
        redaccion.save()
        respuesta = self.client.post(self.ruta_editor(self.plan), dict(version_base=redaccion.version,
            act__PRACTICAS__meta='1', act__GUIAS__meta='9999', act__MANTENIMIENTO__meta='1'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200)
        redaccion.refresh_from_db()
        plan = redaccion.contenido['actividades']
        self.assertEqual(plan['catalogo']['PRACTICAS']['meta'], '2')
        self.assertEqual(plan['catalogo']['GUIAS']['meta'], '1')
        self.assertEqual(plan['catalogo']['MANTENIMIENTO']['meta'], '80 %')
        self.assertEqual(plan['metas_estandar']['version'], 2)
        ReferenciaIndicadorUnidad.objects.update_or_create(tipo_unidad='laboratorios', codigo='PRACTICAS-SEMANA',
            nivel_capacidad='', defaults=dict(valor=2, fundamento='Dos sesiones por semana aprobadas por Dirección.'))
        filas = {f['codigo']: f for f in filas_del_plan(self.unidad, redaccion.contenido,
            date(2026, 1, 1), date(2026, 6, 30))}
        self.assertEqual(filas['PRACTICAS']['meta'], '2')

    def test_generar_abre_archivo_para_firma_sin_marca_y_no_regenera_en_conflicto(self):
        self.programar(date(2026, 3, 9))
        self.programar(date(2026, 3, 16), curso=1)
        redaccion = obtener_redaccion(self.plan)
        redaccion.contenido = deepcopy(PLAN_COMPLETO)
        from apps.documentos.presentation.expediente_redaccion import plan_inicial
        from apps.documentos.presentation.expediente import tramo_del_documento
        from apps.documentos.presentation.presupuesto_uso import meses_entre
        inicio, fin = tramo_del_documento(self.plan)
        redaccion.contenido['actividades'] = plan_inicial(self.plan, inicio, fin)
        meses = list(meses_entre(inicio, fin))
        redaccion.contenido['presupuesto_uso'].update(horas_por_mes={str(m): '4' for m in meses},
            horas_comprometidas=str(4 * len(meses)))
        redaccion.contenido['revision_recursos'] = 'revisado'
        redaccion.save()
        datos = dict(version_base=redaccion.version, accion='generar_guardado')
        respuesta = self.client.post(self.ruta_editor(self.plan), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.plan.refresh_from_db()
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.generado_version, redaccion.version)
        self.assertEqual(respuesta.json()['url'], reverse('recurso_unidad', args=[self.plan.recurso_id]))
        with self.plan.recurso.archivo.open('rb') as archivo:
            texto = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(archivo.read())).pages)
        self.assertNotIn('BORRADOR', texto)
        self.assertNotIn('DATOS AL DÍA', texto)
        self.assertIn('Carga programada por asignatura', texto)
        self.assertIn('Curso 0', texto)
        borrador = self.client.get(reverse('pdf_borrador_documento_expediente', args=[self.unidad.slug, self.plan.pk]))
        self.assertIn('BORRADOR', '\n'.join(p.extract_text() for p in PdfReader(BytesIO(borrador.content)).pages))
        recurso = self.plan.recurso_id
        conflicto = self.client.post(self.ruta_editor(self.plan), dict(datos, version_base='999'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(conflicto.status_code, 409)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.recurso_id, recurso)

    def test_director_consulta_avance_de_una_unidad_sin_abrir_otra_pagina(self):
        self.coordinador.is_staff = self.coordinador.is_superuser = True
        self.coordinador.save()
        url = reverse('admin:reportes-cumplimiento-expediente')
        respuesta = self.client.get(url, dict(anio=2026, corte='A', unidad=self.unidad.slug, fragmento='avance'))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertIn('data-progreso-general', datos['progreso'])
        self.assertIn(str(self.plan.pk), datos['avances'])
        self.coordinador.is_staff = self.coordinador.is_superuser = False
        self.coordinador.save()
        self.assertEqual(self.client.get(url, dict(anio=2026, corte='A', unidad=self.unidad.slug,
            fragmento='avance')).status_code, 403)

    def test_una_referencia_central_mayor_no_inventa_sesiones_ni_horas(self):
        ReferenciaIndicadorUnidad.objects.update_or_create(tipo_unidad='laboratorios', codigo='PRACTICAS',
            nivel_capacidad='', defaults=dict(valor=100, fundamento='Piso central de cien sesiones para la prueba.'))
        respuesta = self.client.get(self.ruta_editor(self.plan))
        dato = next(d for s in respuesta.context['secciones'] for d in s['campos'] if d['campo'].tipo == 'actividades')
        practica = next(f for f in dato['filas'] if f['codigo'] == 'PRACTICAS')
        self.assertEqual(practica['meta'], '100')
        self.assertEqual(dato['metas_estandar']['carga_docente']['horas_requeridas'], '0')
        self.assertTrue(dato['metas_estandar']['carga_docente']['avisos'])

    def programar(self, fecha, *, curso=0, tema=0, inicio=time(8), fin=time(10), **datos):
        syllabus = TemaAsignatura.objects.get(asignatura__unidad=self.unidad,
            asignatura__codigo=f'CURSO-{curso}', orden=tema + 1)
        return PlanificacionPractica.objects.create(unidad=self.unidad, fecha=fecha,
            hora_inicio=inicio, hora_fin=fin, tema_asignatura=syllabus,
            asignatura=syllabus.asignatura.nombre, tema=syllabus.nombre,
            docente_tutor='Docente de prueba', creado_por=self.coordinador, **datos)

    def carga(self):
        from apps.documentos.presentation.expediente_redaccion import plan_inicial
        return plan_inicial(self.plan, date(2026, 1, 1), date(2026, 6, 30))['metas_estandar']['carga_docente']

    def test_frecuencias_variables_una_sesion_y_varias_practicas_por_asignatura(self):
        # Ocho semanas, no todo el semestre. Una asignatura puede repetir una
        # práctica y también tener otro tema en una sesión independiente.
        for semana in range(8):
            self.programar(date(2026, 3, 9) + timedelta(weeks=semana))
        self.programar(date(2026, 5, 4), tema=1, inicio=time(9), fin=time(10, 30))
        self.programar(date(2026, 5, 5), curso=1, inicio=time(9), fin=time(10))
        carga = self.carga()
        self.assertEqual(carga['practicas'], 10)
        self.assertEqual(carga['guias'], 3)
        self.assertEqual(carga['horas_requeridas'], '18.5')
        self.assertEqual(carga['horas_por_mes'], {'3': '8', '4': '8', '5': '2.5'})
        self.assertEqual(sorted(c['sesiones'] for c in carga['asignaturas']), [1, 9])
        self.assertEqual(sorted(c['horas'] for c in carga['asignaturas']), ['1', '17.5'])

    def test_agenda_recurrente_y_ft02_no_duplican_sesiones_ni_horas(self):
        curso = Asignatura.objects.get(unidad=self.unidad, codigo='CURSO-0')
        programa = ProgramacionReserva.objects.create(laboratorio=self.unidad, solicitante=self.coordinador,
            asignatura=curso, frecuencia='semanal_rango', fecha_inicio=date(2026, 3, 9),
            fecha_fin=date(2026, 4, 27), dia_semana=0, hora_inicio=time(8), hora_fin=time(10), total_sesiones=8)
        for semana in range(8):
            fecha = date(2026, 3, 9) + timedelta(weeks=semana)
            reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.coordinador,
                programacion=programa, proposito_codigo='docencia_practica', fecha=fecha,
                hora_inicio=time(8), hora_fin=time(10))
            if semana == 0:
                self.programar(fecha, reserva=reserva)
        carga = self.carga()
        self.assertEqual(carga['sesiones_programadas'], 8)
        self.assertEqual(carga['horas_requeridas'], '16')
        self.assertEqual(len([s for s in carga['sesiones'] if s['origen'] == 'FT02']), 1)
        self.assertEqual(carga['asignaturas'][0]['sesiones'], 8)

    def test_sesiones_simultaneas_no_duplican_ocupacion_de_la_unidad(self):
        self.programar(date(2026, 3, 9))
        self.programar(date(2026, 3, 9), curso=1, inicio=time(9), fin=time(11))
        carga = self.carga()
        self.assertEqual(carga['sesiones_programadas'], 2)
        self.assertEqual(carga['horas_sesiones'], '4')
        self.assertEqual(carga['horas_requeridas'], '3')

    def test_una_guia_para_la_misma_practica_no_se_duplica_por_sesion(self):
        actividad = CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre='Práctica curricular')
        guia = GuiaActividadReserva.objects.create(actividad=actividad, titulo='Guía reutilizable')
        self.programar(date(2026, 3, 9), guia=guia, actividad=actividad)
        self.programar(date(2026, 3, 16))
        self.assertEqual(self.carga()['guias'], 1)

    def test_revision_ft02_con_reserva_en_version_anterior_cuenta_una_vez(self):
        curso = Asignatura.objects.get(unidad=self.unidad, codigo='CURSO-0')
        programa = ProgramacionReserva.objects.create(laboratorio=self.unidad, solicitante=self.coordinador,
            asignatura=curso, fecha_inicio=date(2026, 3, 9), fecha_fin=date(2026, 3, 9),
            dia_semana=0, hora_inicio=time(8), hora_fin=time(10))
        reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.coordinador,
            programacion=programa, proposito_codigo='docencia_practica', fecha=date(2026, 3, 9),
            hora_inicio=time(8), hora_fin=time(10))
        anterior = self.programar(reserva.fecha, reserva=reserva)
        PlanificacionPractica.objects.filter(pk=anterior.pk).update(es_version_vigente=False)
        nueva = self.programar(reserva.fecha, grupo_version=anterior.grupo_version, numero_version=2)
        # El comando de nueva versión conserva la reserva en el antecedente.
        PlanificacionPractica.objects.filter(pk=nueva.pk).update(tema_asignatura=None)
        carga = self.carga()
        self.assertEqual(carga['sesiones_programadas'], 1)
        self.assertEqual(carga['horas_sesiones'], '2')
        self.assertEqual(carga['asignaturas'][0]['id'], curso.pk)
        self.assertEqual(carga['sesiones'][0]['reserva'], reserva.pk)
        self.assertEqual(carga['sesiones'][0]['version'], 2)

    def test_solo_version_vigente_y_tramo_y_no_cancelaciones_o_servicios(self):
        plan = self.programar(date(2026, 3, 9))
        PlanificacionPractica.objects.filter(pk=plan.pk).update(es_version_vigente=False)
        self.programar(date(2026, 3, 9), grupo_version=plan.grupo_version, numero_version=2)
        self.programar(date(2026, 7, 9))  # Fuera del tramo de este documento.
        self.programar(date(2026, 3, 10), estado='archivada')
        for estado, proposito in [('cancelada', 'docencia_practica'), ('rechazada', 'docencia_practica'),
                                   ('pendiente', 'servicio_cientifico_tecnologico')]:
            Reserva.objects.create(laboratorio=self.unidad, usuario=self.coordinador,
                fecha=date(2026, 3, 11), hora_inicio=time(8), hora_fin=time(10),
                estado=estado, proposito_codigo=proposito)
        self.assertEqual(self.carga()['sesiones_programadas'], 1)

    def test_siete_asignaturas_no_generan_ciento_doce_practicas(self):
        for numero in range(2, 7):
            Asignatura.objects.create(unidad=self.unidad, codigo=f'CURSO-{numero}', nombre=f'Curso {numero}')
        ReferenciaIndicadorUnidad.objects.update_or_create(tipo_unidad='laboratorios', codigo='PRACTICAS-SEMANA',
            nivel_capacidad='', defaults=dict(valor=99, fundamento='Referencia histórica que ya no multiplica el catálogo.'))
        carga = self.carga()
        self.assertEqual(carga['asignaturas_catalogo_total'], 7)
        self.assertEqual(carga['asignaturas_total'], 0)
        self.assertEqual(carga['practicas'], 2)
        self.assertEqual(carga['horas_requeridas'], '0')

    def test_uso_sin_vinculo_y_practicas_no_curriculares_no_imponen_cuota_docente(self):
        PlanificacionPractica.objects.create(unidad=self.unidad, fecha=date(2026, 3, 9),
            hora_inicio=time(8), hora_fin=time(10), asignatura='Texto pendiente de vincular',
            tema='Práctica solicitada', creado_por=self.coordinador)
        self.programar(date(2026, 3, 10), categoria_uso='servicio')
        carga = self.carga()
        self.assertEqual(carga['sesiones_programadas'], 0)
        self.assertEqual(len(carga['sesiones_sin_vinculo']), 1)
        self.assertEqual(carga['horas_sin_vinculo'], '2')
        self.assertEqual(carga['practicas'], 2)
        self.assertTrue(any('vincular' in a for a in carga['avisos']))

    def test_plan_aprobado_conserva_meta_y_fuentes_aunque_cambie_la_agenda(self):
        self.programar(date(2026, 3, 9))
        self.programar(date(2026, 3, 16))
        redaccion = obtener_redaccion(self.plan)
        redaccion.save()
        anterior = deepcopy(redaccion.contenido)
        self.plan.estado = 'validado'
        self.plan.save(update_fields=['estado'])
        self.programar(date(2026, 3, 23))
        respuesta = self.client.get(self.ruta_editor(self.plan))
        dato = next(d for s in respuesta.context['secciones'] for d in s['campos'] if d['campo'].tipo == 'actividades')
        self.assertEqual(dato['metas_estandar']['carga_docente']['sesiones_programadas'], 2)
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido, anterior)

    def test_plan_firmado_en_revision_no_recalcula_ni_acepta_otras_metas(self):
        self.programar(date(2026, 3, 9))
        self.programar(date(2026, 3, 16))
        redaccion = obtener_redaccion(self.plan)
        redaccion.save()
        anterior = deepcopy(redaccion.contenido)
        self.plan.estado = 'cargado'
        self.plan.save(update_fields=['estado'])
        self.programar(date(2026, 3, 23))
        respuesta = self.client.get(self.ruta_editor(self.plan))
        dato = next(d for s in respuesta.context['secciones'] for d in s['campos'] if d['campo'].tipo == 'actividades')
        self.assertEqual(dato['metas_estandar']['carga_docente']['sesiones_programadas'], 2)
        respuesta = self.client.post(self.ruta_editor(self.plan), dict(version_base=redaccion.version,
            act__PRACTICAS__meta='99'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 409)
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido, anterior)
