"""Una fila operativa no sustituye el respaldo pedido por la Universidad."""

from datetime import date, time
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.cumplimiento_practicas import (
    conteos_del_periodo, diagnostico_ejecucion, diagnostico_guia, diagnostico_planificacion,
)
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica
from apps.formacion.presentation.asignaturas import situacion_de_sesion
from apps.formacion.presentation.reportes_guias_cumplimiento import reporte_guias_cumplimiento
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva


class CumplimientoDocumentalPracticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('qa-acreditacion-practicas')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio QA acreditación', slug='qa-acreditacion-practicas',
                                          dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Actividad QA acreditación')
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.usuario)
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='QA-ACR-ESP', nombre='Área QA')
        cls.asignatura = Asignatura.objects.create(unidad=cls.unidad, codigo='QA-ACR-AS', nombre='Asignatura QA')
        cls.tema = TemaAsignatura.objects.create(asignatura=cls.asignatura, nombre='Tema verificable',
                                                resultado_aprendizaje='Comprueba un resultado verificable.')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-acreditacion-qa-')
        self.addCleanup(carpeta.cleanup)
        configuracion = override_settings(MEDIA_ROOT=carpeta.name)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        contenido = {campo: 'Información revisada de prueba' for campo in (
            'asignatura', 'carrera_semestre', 'docente_responsable', 'laboratorio', 'categoria_uso',
            'duracion', 'resultado_aprendizaje', 'objetivos', 'procedimiento', 'fundamento_teorico',
            'medidas_seguridad', 'resultados_esperados', 'criterios_evaluacion', 'manejo_residuos', 'bibliografia',
        )}
        contenido['maximo_estudiantes'] = 2
        self.guia = GuiaActividadReserva.objects.create(
            actividad=self.actividad, titulo='Guía QA acreditación', codigo_guia='QA-ACR-G',
            es_estructurada=True, es_vigente=True, estado_publicacion='publicada',
            aprobado_por=self.usuario, aprobado_en=timezone.now(), contenido=contenido,
        )
        self.reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.usuario, actividad_catalogo=self.actividad,
            fecha=date(2026, 10, 10), hora_inicio=time(8), hora_fin=time(10), estado='completada',
        )
        self.reserva.espacios_solicitados.add(self.espacio)
        self.plan = PlanificacionPractica.objects.create(
            unidad=self.unidad, actividad=self.actividad, guia=self.guia, tema_asignatura=self.tema,
            reserva=self.reserva, fecha=self.reserva.fecha, hora_inicio=time(8), hora_fin=time(10),
            carrera='Carrera QA', semestre='Primero', asignatura='Asignatura QA', docente_tutor='Docente QA',
            tema='Tema verificable', resultado_aprendizaje=self.tema.resultado_aprendizaje,
            estudiantes_planificados=2, responsable_tecnico=self.responsable, estado='aprobada', creado_por=self.usuario,
        )
        self.ejecucion = EjecucionPractica.objects.create(
            planificacion=self.plan, fecha_ejecucion=self.plan.fecha, hora_inicio_real=time(8), hora_fin_real=time(10),
            estudiantes_asistentes=2, recursos_utilizados='Área de prueba', responsable_tecnico=self.responsable,
            cumplimiento_resultado='parcial', estado='validada', validado_por=self.usuario,
            validado_en=timezone.now(), creado_por=self.usuario,
            detalle_operativo={'participantes': [
                {'id': str(i), 'nombre': f'Participante QA {i}', 'asistencia_codigo': 'asistio'} for i in (1, 2)
            ]},
        )

    def evidencia(self, tipo='bitacora'):
        evidencia = EvidenciaPractica(ejecucion=self.ejecucion, tipo=tipo, nombre_original='evidencia-qa.txt',
                                     descripcion='Desarrollo identificado de la práctica QA.')
        evidencia.archivo.save('evidencia-qa.txt', ContentFile(b'Respaldo exclusivo de prueba.'), save=True)
        return evidencia

    def test_guia_publicada_sin_vigencia_o_syllabus_no_acredita(self):
        self.assertTrue(diagnostico_guia(self.guia)['cumple'])
        self.guia.es_vigente = False
        self.plan.tema_asignatura = None
        self.plan.save(update_fields=['tema_asignatura'])
        lectura = diagnostico_guia(self.guia)
        self.assertFalse(lectura['cumple'])
        self.assertFalse(lectura['syllabus'])
        self.assertIn('Versión vigente', lectura['faltantes'])

    def test_plan_archivado_no_acredita_vinculo_ni_aumenta_meta(self):
        self.plan.estado = 'archivada'
        self.plan.save(update_fields=['estado'])
        self.assertFalse(diagnostico_guia(self.guia)['syllabus'])
        conteos = conteos_del_periodo(self.unidad, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(conteos['planificaciones_acreditables'], 0)
        self.assertEqual(conteos['guias_acreditables'], 0)

    def test_plan_informa_escenario_y_responsable_sin_inventarlos(self):
        self.assertTrue(diagnostico_planificacion(self.plan)['cumple'])
        self.reserva.espacios_solicitados.clear()
        self.plan.responsable_tecnico = None
        lectura = diagnostico_planificacion(self.plan)
        self.assertIn('Escenario o espacio asignado', lectura['faltantes'])
        self.assertIn('Responsable técnico asignado', lectura['faltantes'])

    def test_ejecucion_validada_sin_adjunto_sigue_con_respaldo_pendiente(self):
        lectura = diagnostico_ejecucion(self.ejecucion)
        self.assertFalse(lectura['cumple'])
        self.assertTrue(lectura['asistencia'])
        self.evidencia('captura')
        self.assertTrue(diagnostico_ejecucion(self.ejecucion)['cumple'])
        # Parcial/no se conserva: documentar no obliga a falsear el resultado.
        self.ejecucion.refresh_from_db()
        self.assertEqual(self.ejecucion.cumplimiento_resultado, 'parcial')

    def test_asistencia_duplicada_no_demuestra_dos_alumnos_y_archivo_faltante_no_cuenta(self):
        self.ejecucion.detalle_operativo['participantes'][1] = self.ejecucion.detalle_operativo['participantes'][0]
        evidencia = self.evidencia()
        evidencia.archivo.storage.delete(evidencia.archivo.name)
        lectura = diagnostico_ejecucion(self.ejecucion)
        self.assertFalse(lectura['asistencia'])
        self.assertFalse(lectura['desarrollo'])
        self.assertEqual(lectura['evidencias_disponibles'], 0)

    def test_conteo_no_modifica_estados_y_reporte_muestra_pendientes_reales(self):
        self.evidencia('producto')
        antes = list(EjecucionPractica.objects.values())
        conteos = conteos_del_periodo(self.unidad, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(conteos['planificaciones_acreditables'], 1)
        self.assertEqual(conteos['guias_acreditables'], 1)
        self.assertEqual(conteos['practicas_acreditables'], 1)
        self.assertEqual(antes, list(EjecucionPractica.objects.values()))
        headers, rows, cards, _ = reporte_guias_cumplimiento(self.unidad, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(len(headers), len(rows[0]))
        self.assertIn('Tema verificable', rows[0][4])
        self.assertEqual(rows[0][-1], 'Respaldo completo')
        self.assertEqual({card[0]: card[1] for card in cards}['Con respaldo completo'], 1)

    def test_reserva_completada_o_ft03_borrador_no_se_presenta_como_validada(self):
        self.ejecucion.estado = 'borrador'
        self.ejecucion.save(update_fields=['estado'])
        self.plan.refresh_from_db()
        self.assertEqual(situacion_de_sesion(self.reserva, self.plan), 'ejecutada_pendiente')
        self.ejecucion.delete()
        self.plan.refresh_from_db()
        self.assertEqual(situacion_de_sesion(self.reserva, self.plan), 'ejecutada_pendiente')

    def test_pdf_importado_ausente_no_se_cuenta_como_guia_acreditable(self):
        self.guia.es_estructurada = False
        self.guia.archivo = 'guias/qa-no-existe.pdf'
        lectura = diagnostico_guia(self.guia)
        self.assertFalse(lectura['cumple'])
        self.assertIn('Archivo PDF de la guía disponible', lectura['faltantes'])

    def test_reemplazar_bytes_del_adjunto_exige_nueva_preparacion_sin_cambiar_conteo(self):
        evidencia = self.evidencia('producto')
        antes = conteos_del_periodo(self.unidad, date(2026, 1, 1), date(2026, 12, 31))
        with evidencia.archivo.storage.open(evidencia.archivo.name, 'wb') as archivo:
            archivo.write(b'Otro producto QA en la misma ruta, mismo conteo.')
        despues = conteos_del_periodo(self.unidad, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(antes['practicas_acreditables'], despues['practicas_acreditables'])
        self.assertNotEqual(antes['fuentes_practicas'], despues['fuentes_practicas'])

    def test_texto_de_muestra_o_html_vacio_no_acredita_apartado(self):
        self.guia.contenido['medidas_seguridad'] = '<p>&nbsp;</p>'
        self.guia.contenido['bibliografia'] = ['']
        self.guia.contenido['fundamento_teorico'] = 'Por definir'
        pendientes = diagnostico_guia(self.guia)['faltantes']
        self.assertIn('Precauciones específicas de seguridad', pendientes)
        self.assertIn('Bibliografía', pendientes)
        self.assertIn('Fundamento teórico', pendientes)

    def test_fuentes_estables_y_cambiar_resultado_del_syllabus_invalida_preparacion(self):
        self.evidencia('producto')
        periodo = self.unidad, date(2026, 1, 1), date(2026, 12, 31)
        antes = conteos_del_periodo(*periodo)
        repetida = conteos_del_periodo(*periodo)
        self.assertEqual(antes['fuentes_practicas'], repetida['fuentes_practicas'])
        self.tema.resultado_aprendizaje = 'Otro resultado de aprendizaje revisado, igualmente completo.'
        self.tema.save(update_fields=['resultado_aprendizaje'])
        despues = conteos_del_periodo(*periodo)
        self.assertEqual(antes['guias_acreditables'], despues['guias_acreditables'])
        for grupo in ('planificaciones', 'guias', 'ejecuciones'):
            self.assertNotEqual(antes['fuentes_practicas'][grupo], despues['fuentes_practicas'][grupo])

    def test_guia_reutilizable_firma_vinculo_a_plan_fuera_del_tramo(self):
        periodo = self.unidad, date(2026, 10, 11), date(2026, 12, 31)
        antes = conteos_del_periodo(*periodo)
        self.assertEqual(antes['guias_acreditables'], 1)
        self.assertEqual(antes['fuentes_practicas']['planificaciones'], [])
        self.asignatura.nombre = 'Asignatura de nombre actualizado'
        self.asignatura.save(update_fields=['nombre'])
        despues = conteos_del_periodo(*periodo)
        self.assertEqual(despues['guias_acreditables'], 1)
        self.assertNotEqual(antes['fuentes_practicas']['guias'], despues['fuentes_practicas']['guias'])

    def test_guia_vigente_anterior_se_consulta_pero_no_suma_como_nueva_del_periodo(self):
        periodo = self.unidad, date(2026, 1, 1), date(2026, 12, 31)
        actual = conteos_del_periodo(*periodo)
        self.assertEqual(actual['guias_periodo_acreditables'], 1)
        anterior = timezone.now().replace(year=2025, month=10, day=10)
        GuiaActividadReserva.objects.filter(pk=self.guia.pk).update(actualizado_en=anterior, aprobado_en=anterior)
        lectura = conteos_del_periodo(*periodo)
        self.assertEqual(lectura['guias_acreditables'], 1)
        self.assertEqual(lectura['guias_periodo_acreditables'], 0)
        self.assertEqual(lectura['fuentes_practicas']['guias'][0]['actualizado_en'], anterior.isoformat())
        _, filas, _, _ = reporte_guias_cumplimiento(*periodo)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][1], self.guia.titulo)
