"""Programación de asignatura: la guía general del período y las guías por sesión.

El docente programa el período eligiendo su asignatura; el cronograma de
la guía general nace de los temas y cada sesión nace con su guía prellenada
desde el tema y su proceso. Sin la guía general aprobada no se aprueba una
sesión; sin la guía de la sesión aprobada no se inicia. El docente recibe el
aviso una sola vez, y el cumplimiento del cronograma compara lo previsto con
lo que pasó.
"""

import json
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.asignaturas import dias_habiles_hasta, reporte_asignaturas, sesiones_sin_guia, situacion_de_sesion
from apps.reservas.presentation.notificaciones import procesar_recordatorios_reservas
from apps.reservas.presentation.proceso import seleccion_por_proceso
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import GuiaActividadReserva, NotificacionReserva, ProgramacionReserva, Reserva
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.formacion.models.practicas import PlanificacionPractica
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.reservas.models.seguridad import RequisitoAcceso
from tests.integration.test_laboratorios_institucionales import _dia_habil
from tests.integration.test_produccion_planta import BasePlantaProduce


def _lunes_siguiente(fecha):
    return fecha + timedelta(days=(7 - fecha.weekday()) % 7 or 7)


class BaseProgramacion(BasePlantaProduce):
    """La planta con un período de tres semanas y la asignatura del cargador."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Aquí se prueba la guía por sesión; el control de ingreso tiene su propia prueba.
        RequisitoAcceso.objects.filter(unidad=cls.unidad).update(activo=False)
        lunes = _lunes_siguiente(cls.hoy)
        cls.periodo = PeriodoAcademico.objects.create(
            codigo='2026-P', nombre='Período de prueba', anio_referencia=2026, ciclo='B',
            tipo='ordinario', ambito='carreras_centros', semanas_planificadas=3, estado='publicado',
        )
        version = VersionCalendarioAcademico.objects.create(
            periodo=cls.periodo, numero=1, nombre='Calendario de prueba',
            fecha_inicio_clases=lunes, fecha_fin_clases=lunes + timedelta(days=20),
            fecha_fin_periodo=lunes + timedelta(days=27), vigente=True,
        )
        for numero in range(3):
            inicio = lunes + timedelta(days=7 * numero)
            SemanaAcademica.objects.create(
                version_calendario=version, numero=numero + 1,
                fecha_inicio=inicio, fecha_fin=inicio + timedelta(days=6), permite_reservas=True,
            )
        cls.martes = lunes + timedelta(days=1)
        cls.asignatura = Asignatura.objects.get(unidad=cls.unidad, codigo='LAC-ASIG-TECLAC')
        cls.queseria = EspacioReservable.objects.get(codigo='LAC-AREA-QUESERIA')

    def programar(self, **extra):
        datos = self._payload(
            fecha_inicio=f'{self.martes.isoformat()}T09:00',
            fecha_fin=f'{self.martes.isoformat()}T11:00',
            incluye_espacio='1',
            alcance_espacio='areas',
            espacios_solicitados=[str(self.queseria.pk)],
            unidades_seleccionadas=self._seleccion('LAC-EQP-TINA-01'),
            proposito='Docencia',
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            origen_programacion='programada',
            frecuencia_reserva='semanal_periodo',
            referencia_actividad='Prácticas de Tecnología de Lácteos',
            descripcion_proyecto='Un proceso por semana según el sílabo.',
            asignatura_id=str(self.asignatura.pk),
            participantes_seleccionados=json.dumps([self.estudiante.pk]),
            guia_confirmada_solicitante='1',
            guia_formato_contenido='html',
            guia_formato_procedimiento='numerado',
            guia_asignatura=self.asignatura.nombre,
            guia_resultado_aprendizaje='<p>Conduce los procesos de la planta con control de puntos críticos.</p>',
            guia_objetivos='<ul><li>Programar el período completo de prácticas.</li></ul>',
            guia_procedimiento='<ol class="guide-steps"><li><p>Sesión por sesión según el cronograma.</p></li></ol>',
        )
        datos.update(extra)
        self.client.force_login(self.docente)
        return self.client.post(reverse('crear_reserva'), datos)

    def sesiones_de(self, programacion):
        return list(Reserva.objects.filter(programacion=programacion).order_by('fecha', 'pk'))

    def plan_de(self, reserva):
        return PlanificacionPractica.objects.select_related('guia', 'tema_asignatura').get(reserva=reserva)

    def general_de(self, reserva):
        return GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, alcance='periodo')

    def aprobar_guia(self, guia):
        self.client.force_login(self.coordinacion)
        return self.client.post(
            reverse('cambiar_estado_guia_practica', args=[guia.pk]),
            {'accion': 'aprobar', 'observacion': 'Guía verificada.'},
        )

    def accion(self, reserva, accion, **extra):
        self.client.force_login(self.coordinacion)
        datos = {'accion': accion, 'observacion': f'{accion} desde la prueba.'}
        datos.update(extra)
        return self.client.post(reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]), datos)


class ElSilaboDeLaPlantaTests(BaseProgramacion):
    def test_el_cargador_trae_la_asignatura_con_sus_temas_y_procesos(self):
        temas = self.asignatura.temas_ordenados()
        self.assertEqual(len(temas), 12)
        self.assertEqual(temas[0].nombre, 'Recepción y control de calidad de la leche')
        self.assertIsNone(temas[0].receta)
        self.assertEqual(temas[3].receta.codigo, 'LAC-REC-QUESO-100')
        self.assertEqual([programa.codigo for programa in temas[0].software.all()], ['LAC-SW-TRAZA'])
        self.assertEqual(dias_habiles_hasta(self.hoy, self.hoy), 0)
        lunes = _lunes_siguiente(self.hoy)
        self.assertEqual(dias_habiles_hasta(lunes, lunes + timedelta(days=7)), 5)
        # La ficha ofrece la asignatura al docente para programar el período.
        self.client.force_login(self.docente)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'id="asignaturasDocente"')
        self.assertContains(ficha, 'LAC-ASIG-TECLAC')

    def test_el_panel_registra_asignaturas_y_temas(self):
        respuesta = self.operar(
            modulo='asignatura', codigo='lac-asig-calidad', nombre='Control de calidad de lácteos',
            carrera='Agroindustria', semestre='Séptimo semestre', docente=self.docente.username,
            estudiantes='12', periodo_id=str(self.periodo.pk),
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        calidad = Asignatura.objects.get(unidad=self.unidad, codigo='LAC-ASIG-CALIDAD')
        self.assertEqual(calidad.docente, self.docente)
        self.assertEqual(calidad.periodo, self.periodo)
        traza = self.unidad.software_disponible.get(codigo='LAC-SW-TRAZA') if hasattr(self.unidad, 'software_disponible') else None
        tema = self.operar(
            modulo='tema_asignatura', asignatura_id=str(calidad.pk), orden='1',
            nombre='Análisis de la leche cruda', receta_id=str(self.receta_queso.pk),
            ejercicios='Acidez, densidad y prueba de alcohol.', resultado_aprendizaje='Decide si la leche entra al proceso.',
            software_ids=[str(traza.pk)] if traza else [],
        )
        self.assertEqual(tema.status_code, 200, tema.content)
        tema_uno = TemaAsignatura.objects.get(asignatura=calidad, orden=1)
        self.assertEqual(tema_uno.receta, self.receta_queso)
        repetido = self.operar(modulo='tema_asignatura', asignatura_id=str(calidad.pk), orden='1', nombre='Otro tema')
        self.assertEqual(repetido.status_code, 400)
        self.assertIn('semana 1', repetido.json()['error'])
        editado = self.operar(
            modulo='tema_asignatura', registro_id=str(tema_uno.pk), asignatura_id=str(calidad.pk),
            orden='2', nombre='Análisis fisicoquímico de la leche',
        )
        self.assertEqual(editado.status_code, 200, editado.content)
        tema_uno.refresh_from_db()
        self.assertEqual(tema_uno.orden, 2)
        quitado = self.operar(modulo='tema_asignatura', registro_id=str(tema_uno.pk), accion='desactivar')
        self.assertEqual(quitado.status_code, 200, quitado.content)
        self.assertFalse(TemaAsignatura.objects.filter(pk=tema_uno.pk).exists())
        ajeno = self.operar(self.docente, modulo='asignatura', codigo='X', nombre='Sin permiso')
        self.assertEqual(ajeno.status_code, 403)
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=practicas')
        self.assertContains(panel, 'Asignaturas y sus temas')
        self.assertContains(panel, 'LAC-ASIG-CALIDAD')


class ElPeriodoProgramadoTests(BaseProgramacion):
    def test_la_guia_general_lleva_el_cronograma_y_cada_sesion_nace_con_su_guia(self):
        respuesta = self.programar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        datos = respuesta.json()
        self.assertEqual(datos['sesiones_creadas'], 3)
        programacion = ProgramacionReserva.objects.get(pk=datos['programacion_id'])
        self.assertEqual(programacion.asignatura, self.asignatura)
        sesiones = self.sesiones_de(programacion)
        general = self.general_de(sesiones[0])
        self.assertEqual(general.estado_publicacion, 'revision')
        cronograma = general.contenido['cronograma']
        self.assertEqual([fila['sesion'] for fila in cronograma], [1, 2, 3])
        self.assertEqual(
            [fila['tema'] for fila in cronograma],
            ['Recepción y control de calidad de la leche', 'Leche pasteurizada', 'Yogur batido de mora'],
        )
        self.assertEqual(cronograma[1]['proceso'], 'Leche pasteurizada por 100 litros')
        self.assertEqual(cronograma[0]['software'], ['Registro de trazabilidad de lotes'])
        self.assertEqual(general.contenido['asignatura'], self.asignatura.nombre)
        for numero, sesion in enumerate(sesiones, start=1):
            plan = self.plan_de(sesion)
            self.assertEqual(plan.tema_asignatura.orden, numero)
            guia = plan.guia
            self.assertEqual(guia.alcance, 'sesion')
            self.assertEqual(guia.guia_general, general)
            self.assertEqual(guia.sesion, plan)
            self.assertEqual(guia.familia, sesion.receta.familia if sesion.receta_id else None)
            self.assertEqual(guia.estado_publicacion, 'borrador')
            self.assertTrue(guia.codigo_guia.endswith(f'-S{numero:02d}'))
            self.assertTrue(guia.contenido['sesion_programada'].startswith(f'Sesión {numero} de 3'))
            self.assertEqual(guia.contenido['asignatura'], self.asignatura.nombre)
        segunda = self.plan_de(sesiones[1]).guia
        self.assertIn('Pasteuriza', segunda.contenido['procedimiento'])
        self.assertIn('Leche pasteurizada', segunda.contenido['objetivos'])
        primera = self.plan_de(sesiones[0]).guia
        self.assertEqual(primera.contenido['procedimiento'], '')
        self.assertIn('Recepción y control de calidad de la leche', primera.contenido['objetivos'])
        self.assertIn('Ejercicios del aula', primera.contenido['objetivos'])
        # La bandeja: las tres sesiones esperan su guía, con el plazo de dos días hábiles.
        pendientes = sesiones_sin_guia(self.unidad, self.hoy)
        self.assertEqual([fila['reserva'].pk for fila in pendientes], [sesion.pk for sesion in sesiones])
        self.assertEqual(pendientes[0]['margen'], dias_habiles_hasta(self.hoy, self.martes) - 2)
        self.assertEqual(pendientes[0]['tema'].orden, 1)
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=practicas')
        self.assertContains(panel, 'Sesiones sin guía aprobada')
        self.assertContains(panel, sesiones[0].codigo_reserva)
        # El documento de la guía general muestra el cronograma; el de la sesión, su lugar en él.
        documento = self.client.get(reverse('editar_guia_practica', args=[self.unidad.slug, general.pk]))
        self.assertContains(documento, 'Cronograma de sesiones del período')
        self.assertContains(documento, 'Yogur batido de mora')
        de_sesion = self.client.get(reverse('editar_guia_practica', args=[self.unidad.slug, segunda.pk]))
        self.assertContains(de_sesion, 'Sesión 2 de 3')
        pdf = self.client.get(reverse('ver_guia_actividad', args=[general.pk]))
        self.assertIn(pdf.status_code, (200, 302))

    def test_una_asignatura_ajena_o_sin_docencia_no_pasa(self):
        ajena = self.programar(asignatura_id='999999')
        self.assertEqual(ajena.status_code, 400)
        self.assertIn('asignatura', ajena.json()['error'].lower())
        sin_docencia = self.programar(
            proposito_codigo='investigacion_innovacion', subtipo_actividad='proyecto_investigacion',
        )
        self.assertEqual(sin_docencia.status_code, 400)
        self.assertIn('docente', sin_docencia.json()['error'].lower())

    def test_sin_guia_general_no_se_aprueba_y_sin_guia_de_sesion_no_se_inicia(self):
        respuesta = self.programar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        programacion = ProgramacionReserva.objects.get(pk=respuesta.json()['programacion_id'])
        primera, segunda, _tercera = self.sesiones_de(programacion)
        general = self.general_de(primera)
        bloqueada = self.accion(primera, 'aprobar')
        self.assertEqual(bloqueada.status_code, 409, bloqueada.content)
        self.assertIn('guía general', bloqueada.json()['error'].lower())
        self.assertEqual(self.aprobar_guia(general).status_code, 302)
        general.refresh_from_db()
        self.assertEqual(general.estado_publicacion, 'publicada')
        self.assertTrue(general.es_vigente)
        # Con la guía general aprobada las sesiones se aprueban, pero no se inician sin su guía.
        self.assertEqual(self.accion(primera, 'aprobar').status_code, 200)
        self.assertEqual(self.accion(segunda, 'aprobar').status_code, 200)
        sin_guia = self.accion(primera, 'iniciar')
        self.assertEqual(sin_guia.status_code, 409, sin_guia.content)
        self.assertIn('guía', sin_guia.json()['error'].lower())
        expediente = self.client.get(reverse('gestion_reserva_detalle', args=[self.unidad.slug, primera.pk])).json()
        self.assertFalse(expediente['reserva']['documentacion']['lista'])
        self.assertTrue(expediente['reserva']['documentacion']['lista_para_aprobar'])
        # La guía de la segunda sesión, prellenada desde el proceso, se envía y se aprueba.
        guia_segunda = self.plan_de(segunda).guia
        guia_segunda.estado_publicacion = 'revision'
        guia_segunda.save(update_fields=['estado_publicacion', 'actualizado_en'])
        self.assertEqual(self.aprobar_guia(guia_segunda).status_code, 302)
        guia_segunda.refresh_from_db()
        self.assertEqual(guia_segunda.estado_publicacion, 'publicada')
        general.refresh_from_db()
        self.assertTrue(general.es_vigente, 'aprobar la guía de una sesión no desplaza a la guía general')
        self.assertEqual(self.accion(segunda, 'iniciar').status_code, 200)
        segunda.refresh_from_db()
        self.assertEqual(segunda.estado, 'en_proceso')
        # La primera sigue sin guía: en la bandeja y sin poder iniciarse.
        self.assertEqual([fila['reserva'].pk for fila in sesiones_sin_guia(self.unidad, self.hoy)][:1], [primera.pk])
        self.assertEqual(self.accion(primera, 'iniciar').status_code, 409)

    def test_el_aviso_de_guia_pendiente_llega_al_docente_una_sola_vez(self):
        respuesta = self.programar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        programacion = ProgramacionReserva.objects.get(pk=respuesta.json()['programacion_id'])
        sesiones = self.sesiones_de(programacion)
        hoy_aviso = sesiones[0].fecha
        ahora = timezone.make_aware(datetime.combine(hoy_aviso, time.min))
        esperados = sum(1 for sesion in sesiones if dias_habiles_hasta(hoy_aviso, sesion.fecha) <= 4)
        self.assertGreaterEqual(esperados, 1)
        resultados = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)
        self.assertEqual(resultados['guias_sesion_pendientes'], esperados)
        avisos = NotificacionReserva.objects.filter(tipo='guia_sesion_pendiente', usuario=self.docente)
        self.assertEqual(avisos.count(), esperados)
        self.assertIn('Tecnología de Lácteos', avisos.first().mensaje)
        self.assertIn('/guias-practica/', avisos.first().url)
        de_nuevo = procesar_recordatorios_reservas(ahora=ahora, enviar_email=False)
        self.assertEqual(de_nuevo['guias_sesion_pendientes'], 0)

    def test_el_cumplimiento_del_cronograma_compara_lo_previsto_con_lo_que_paso(self):
        respuesta = self.programar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        programacion = ProgramacionReserva.objects.get(pk=respuesta.json()['programacion_id'])
        primera, segunda, tercera = self.sesiones_de(programacion)
        general = self.general_de(primera)
        self.assertEqual(self.aprobar_guia(general).status_code, 302)
        for sesion in (primera, segunda):
            guia = self.plan_de(sesion).guia
            guia.estado_publicacion = 'publicada'
            guia.save(update_fields=['estado_publicacion', 'actualizado_en'])
            self.assertEqual(self.accion(sesion, 'aprobar').status_code, 200)
        # La primera sesión ya pasó y se cierra cumpliendo lo previsto.
        ayer = _dia_habil(self.hoy - timedelta(days=4))
        Reserva.objects.filter(pk=primera.pk).update(fecha=ayer)
        cierre = self.accion(
            primera, 'completar', ejecucion_registrada='1', participantes_seleccionados='[]',
            asistencia_solicitante='asistio', ejecucion_hora_inicio='09:00', ejecucion_hora_fin='11:00',
            ejecucion_asistentes_total='14', ejecucion_cumplimiento='si',
            ejecucion_observaciones='Recepción y análisis de la leche realizados.',
        )
        self.assertEqual(cierre.status_code, 200, cierre.content)
        # La segunda se cancela; la tercera sigue pendiente.
        self.assertEqual(self.accion(segunda, 'cancelar').status_code, 200)
        primera.refresh_from_db()
        segunda.refresh_from_db()
        # El cierre operativo crea FT03 en revisión; todavía no acredita validación.
        self.assertEqual(situacion_de_sesion(primera, self.plan_de(primera), self.hoy), 'ejecutada_pendiente')
        self.assertEqual(situacion_de_sesion(segunda, self.plan_de(segunda), self.hoy), 'no_ejecutada')
        self.assertEqual(situacion_de_sesion(tercera, self.plan_de(tercera), self.hoy), 'pendiente')
        headers, rows, cards, situaciones = reporte_asignaturas(
            self.unidad, self.hoy - timedelta(days=30), self.hoy + timedelta(days=60)
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], f'{self.asignatura.codigo} · {self.asignatura.nombre}')
        self.assertEqual([fila[1] for fila in rows], [1, 2, 3])
        self.assertEqual([fila[-1] for fila in rows], ['Ejecutada; respaldo pendiente', 'No ejecutada', 'Pendiente'])
        self.assertEqual(rows[1][3], 'Leche pasteurizada')
        self.assertEqual({c[0]: c[1] for c in cards}['Ejecutadas con respaldo pendiente'], 1)
        self.assertEqual({c[0]: c[1] for c in cards}['No ejecutadas'], 1)
        _headers, filtradas, _cards, _situaciones = reporte_asignaturas(
            self.unidad, self.hoy - timedelta(days=30), self.hoy + timedelta(days=60), state='pendiente'
        )
        self.assertEqual(len(filtradas), 1)
        self.client.force_login(self.coordinacion)
        reporte = self.client.get(
            reverse('gestion_reporte_unidad', args=[self.unidad.slug])
            + f'?categoria_reporte=asignaturas&desde={(self.hoy - timedelta(days=30)).isoformat()}&hasta={(self.hoy + timedelta(days=60)).isoformat()}'
        )
        self.assertEqual(reporte.status_code, 200)
        self.assertContains(reporte, 'Ejecutada; respaldo pendiente')
        self.assertContains(reporte, 'Yogur batido de mora')


class ElCronogramaPorSesionTests(BaseProgramacion):
    """Al programar varias sesiones, cada una dice su práctica y su proceso."""

    def fechas(self):
        return [self.martes + timedelta(days=7 * numero) for numero in range(3)]

    def cronograma(self, **por_sesion):
        filas = [
            {'fecha': fecha.isoformat(), 'tema': '', 'tema_id': None, 'receta_id': None, 'cantidad': ''}
            for fecha in self.fechas()
        ]
        for clave, datos in por_sesion.items():
            filas[int(clave[1:])].update(datos)
        return json.dumps(filas)

    def test_cada_sesion_nace_con_su_practica_y_su_proceso(self):
        leche = Receta.objects.get(codigo='LAC-REC-LECHE-100')
        yogur = Receta.objects.get(codigo='LAC-REC-YOGUR-100')
        tema_leche = self.asignatura.temas.get(orden=2)
        respuesta = self.programar(cronograma=self.cronograma(
            s0={'tema': 'Recepción y control de calidad de la leche'},
            s1={'tema': 'Leche pasteurizada', 'tema_id': tema_leche.pk, 'receta_id': leche.pk, 'cantidad': '200'},
            s2={'tema': 'Yogur de mora a escala', 'receta_id': yogur.pk},
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        datos = respuesta.json()
        self.assertEqual(datos['sesiones_creadas'], 3)
        self.assertIn('/mis-sesiones/', datos['sesiones_url'])
        programacion = ProgramacionReserva.objects.get(pk=datos['programacion_id'])
        primera, segunda, tercera = self.sesiones_de(programacion)
        self.assertIsNone(primera.receta)
        self.assertEqual(segunda.receta, leche)
        self.assertEqual(segunda.factor_proceso, Decimal('2.000'))
        self.assertEqual(tercera.receta, yogur)
        self.assertEqual(tercera.factor_proceso, Decimal('1.000'))
        # La sesión con proceso lleva lo que el proceso exige; la primera, lo pedido en el asistente.
        seleccion = seleccion_por_proceso(leche, Decimal('2'), personas=2)
        self.assertEqual(
            set(segunda.espacios_solicitados.values_list('pk', flat=True)),
            {espacio['id'] for espacio in seleccion['espacios']},
        )
        self.assertEqual(
            {pedido.consumible_id for pedido in segunda.consumibles_solicitados.all()},
            {insumo['id'] for insumo in seleccion['insumos']},
        )
        self.assertEqual(
            [unidad['equipo_codigo'] for unidad in json.loads(segunda.unidades_seleccionadas)],
            [equipo['equipo_codigo'] for equipo in seleccion['equipos']],
        )
        self.assertEqual(list(primera.espacios_solicitados.values_list('codigo', flat=True)), ['LAC-AREA-QUESERIA'])
        general = self.general_de(primera)
        cronograma = general.contenido['cronograma']
        self.assertEqual(
            [fila['tema'] for fila in cronograma],
            ['Recepción y control de calidad de la leche', 'Leche pasteurizada', 'Yogur de mora a escala'],
        )
        self.assertEqual([fila['proceso'] for fila in cronograma], ['', leche.nombre, yogur.nombre])
        plan_segunda = self.plan_de(segunda)
        self.assertEqual(plan_segunda.tema, 'Leche pasteurizada')
        self.assertEqual(plan_segunda.tema_asignatura, tema_leche)
        self.assertIn('Pasteuriza', plan_segunda.guia.contenido['procedimiento'])
        self.assertEqual(plan_segunda.guia.contenido['origen_proceso'], leche.pk)
        plan_tercera = self.plan_de(tercera)
        self.assertIsNone(plan_tercera.tema_asignatura)
        self.assertEqual(plan_tercera.tema, 'Yogur de mora a escala')
        self.assertIn('Yogur de mora a escala', plan_tercera.guia.contenido['objetivos'])
        self.assertTrue(plan_tercera.guia.contenido['procedimiento'])
        # Un cronograma que no coincide con las sesiones no pasa.
        torcido = self.programar(cronograma=json.dumps([{'fecha': '2020-01-01'}]))
        self.assertEqual(torcido.status_code, 400)
        self.assertIn('cronograma', torcido.json()['error'].lower())

    def test_el_asistente_consulta_las_sesiones_de_la_programacion(self):
        self.client.force_login(self.docente)
        base = {'unidad': self.unidad.slug, 'fecha': self.martes.isoformat()}
        periodo = self.client.get(reverse('fechas_programacion'), {**base, 'frecuencia': 'semanal_periodo'})
        self.assertEqual(periodo.status_code, 200, periodo.content)
        datos = periodo.json()
        self.assertEqual(datos['periodo'], '2026-P')
        self.assertEqual([sesion['numero'] for sesion in datos['sesiones']], [1, 2, 3])
        self.assertEqual(datos['sesiones'][1]['fecha'], (self.martes + timedelta(days=7)).isoformat())
        self.assertEqual(datos['sesiones'][0]['semana'], 1)
        rango = self.client.get(
            reverse('fechas_programacion'),
            {**base, 'frecuencia': 'semanal_rango', 'fin': (self.martes + timedelta(days=7)).isoformat()},
        )
        self.assertEqual(len(rango.json()['sesiones']), 2)
        unica = self.client.get(reverse('fechas_programacion'), {**base, 'frecuencia': 'unica'})
        self.assertEqual(len(unica.json()['sesiones']), 1)
        sin_fecha = self.client.get(reverse('fechas_programacion'), {**base, 'fecha': 'no', 'frecuencia': 'semanal_periodo'})
        self.assertEqual(sin_fecha.status_code, 400)

    def test_la_sesion_pendiente_se_completa_con_su_proceso_y_sus_insumos(self):
        respuesta = self.programar(cronograma=self.cronograma(
            s0={'tema': 'Recepción de la leche'}, s1={'tema': 'Por definir'}, s2={'tema': 'Por definir'},
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        programacion = ProgramacionReserva.objects.get(pk=respuesta.json()['programacion_id'])
        primera, segunda, tercera = self.sesiones_de(programacion)
        mozzarella = Receta.objects.get(codigo='LAC-REC-MOZZARELLA-100')
        self.client.force_login(self.docente)
        pagina = self.client.get(reverse('completar_sesion', args=[segunda.pk]))
        self.assertContains(pagina, 'Sesión 2 de 3')
        self.assertContains(pagina, 'Guardar la sesión')
        seleccion = seleccion_por_proceso(mozzarella, Decimal('0.5'), personas=2)
        opcional = next((insumo for insumo in seleccion['insumos'] if not insumo['obligatorio']), None)
        obligatorio = next(insumo for insumo in seleccion['insumos'] if insumo['obligatorio'])
        datos = {'tema': 'Mozzarella: hilado de la cuajada', 'receta_id': str(mozzarella.pk), 'cantidad': '50'}
        if opcional is not None:
            datos[f"insumo_{opcional['id']}"] = '0'
        guardado = self.client.post(reverse('completar_sesion', args=[segunda.pk]), datos)
        self.assertEqual(guardado.status_code, 302, guardado.content)
        segunda.refresh_from_db()
        self.assertEqual(segunda.receta, mozzarella)
        self.assertEqual(segunda.factor_proceso, Decimal('0.500'))
        pedidos = {pedido.consumible_id for pedido in segunda.consumibles_solicitados.all()}
        self.assertTrue({insumo['id'] for insumo in seleccion['insumos'] if insumo['obligatorio']} <= pedidos)
        if opcional is not None:
            self.assertNotIn(opcional['id'], pedidos)
        plan = self.plan_de(segunda)
        self.assertEqual(plan.tema, 'Mozzarella: hilado de la cuajada')
        self.assertTrue(plan.guia.contenido['sesion_programada'].startswith('Sesión 2 de 3'))
        self.assertEqual(plan.guia.contenido['origen_proceso'], mozzarella.pk)
        self.assertTrue(plan.guia.contenido['procedimiento'])
        general = self.general_de(primera)
        fila = general.contenido['cronograma'][1]
        self.assertEqual((fila['tema'], fila['proceso']), ('Mozzarella: hilado de la cuajada', mozzarella.nombre))
        # Un insumo obligatorio en cero no pasa.
        rechazo = self.client.post(
            reverse('completar_sesion', args=[segunda.pk]), {**datos, f"insumo_{obligatorio['id']}": '0'},
        )
        self.assertEqual(rechazo.status_code, 200)
        self.assertContains(rechazo, 'es obligatorio para el proceso')
        # El estudiante no la completa; la sesión aprobada ya no se edita aquí.
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(reverse('completar_sesion', args=[segunda.pk])).status_code, 403)
        self.assertEqual(self.aprobar_guia(general).status_code, 302)
        self.assertEqual(self.accion(segunda, 'aprobar').status_code, 200)
        self.client.force_login(self.docente)
        aprobada = self.client.get(reverse('completar_sesion', args=[segunda.pk]))
        self.assertContains(aprobada, 'ya fue aprobada')
        self.assertNotContains(aprobada, 'Guardar la sesión')
        bloqueado = self.client.post(reverse('completar_sesion', args=[segunda.pk]), datos)
        self.assertContains(bloqueado, 'pide el cambio desde')
        # La lista, la ficha y el comprobante llevan a completar lo pendiente.
        lista = self.client.get(reverse('mis_sesiones', args=[self.unidad.slug]))
        self.assertContains(lista, 'Mis sesiones programadas')
        self.assertContains(lista, mozzarella.nombre)
        self.assertContains(lista, 'Completar la sesión')
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'Mis sesiones programadas')
        comprobante = self.client.get(reverse('comprobante_reserva', args=[tercera.pk]))
        self.assertContains(comprobante, 'Sesión 3 de 3')
        self.assertContains(comprobante, 'Completar la sesión')
