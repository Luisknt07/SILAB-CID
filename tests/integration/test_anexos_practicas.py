"""Los tres anexos de prácticas: planificación semestral, guías, y asistencia y evidencias.

Fija lo acordado en docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.5 a 4.7:
- las tablas y columnas de cada anexo, en el orden de la especificación;
- los llevan el laboratorio, la planta piloto y el centro experimental (no el observatorio) y se arman
  aunque la unidad no tenga registros;
- cada tabla presenta todos los registros del período, en cualquier estado, sin lo eliminado ni lo archivado;
- el respaldo de una práctica y el contenido mínimo de una guía salen de los diagnósticos que mide el informe;
- los archivos se abren con la vista protegida de la plataforma, nunca con la ruta pública de medios.
"""
from contextlib import ExitStack
from datetime import date, datetime, time
from datetime import timezone as zona
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.anexos_evidencia import (
    Enlace, Grupo, Par, anexos_numerados, componer_anexo, constructor_de, contexto_del_anexo, fecha, pdf_del_anexo,
)
from apps.documentos.presentation.anexos_practicas import REQUISITOS_CORTOS, _incidente
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import (
    CatalogoActividadReserva, GuiaActividadReserva, ProgramacionReserva, RegistroParticipanteReserva, Reserva,
)

IDENTIDAD = (SimpleNamespace(codigo='PRUEBA'), SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={}))
CON_PRACTICAS = ('laboratorios', 'plantas_piloto', 'centro_experimental')
# Las tablas de cada anexo y sus columnas, tal como las fija la especificación.
TABLAS = {
    'PRACTICAS-FT02': [
        ('Prácticas planificadas',
         ('Código / versión', 'Fecha / horario', 'Unidad / tema', 'Resultado de aprendizaje', 'Escenario',
          'Responsable técnico', 'Estudiantes previstos', 'Guía', 'Estado / revisión')),
        ('Sesiones programadas sin planificación',
         ('Asignatura', 'Sesión / fecha', 'Tema previsto', 'Escenario', 'Situación')),
        ('Resumen por asignatura',
         ('Asignatura', 'Carrera / nivel', 'Prácticas planificadas', 'Aprobadas', 'Con guía aprobada',
          'Con responsable técnico', 'Estudiantes previstos')),
    ],
    'GUIAS': [
        ('Guías vigentes',
         ('Código / versión', 'Título', 'Alcance', 'Asignatura / tema', 'Resultado de aprendizaje', 'Estado',
          'Aprobación', 'Prácticas que la usan')),
        ('Contenido mínimo de cada guía',
         ('Guía', 'Objetivos y resultado', 'Fundamento teórico', 'Procedimiento', 'Medidas de seguridad',
          'Manejo de residuos', 'Criterios de evaluación', 'Bibliografía', 'Pendiente')),
        ('Versiones sustituidas en el período',
         ('Guía', 'Versión anterior', 'Versión vigente', 'Fecha', 'Aprobada por')),
    ],
    'PRACTICAS-FT03': [
        ('Ejecución de las prácticas',
         ('Práctica / sesión', 'Fecha / horario real', 'Resultado / motivo', 'Asistentes / previstos',
          'Recursos utilizados', 'Logro del resultado de aprendizaje', 'Incidente', 'Responsable técnico',
          'Validación')),
        ('Asistencia nominal', ('Práctica', 'Participante', 'Tipo / carrera · nivel', 'Asistencia', 'Observación')),
        ('Índice de evidencias por práctica',
         ('Práctica', 'Asistencia firmada', 'Bitácora', 'Fotografías identificadas', 'Capturas de simulador',
          'Informes de estudiantes', 'Productos desarrollados', 'Respaldo')),
        ('Evidencias', ('Práctica', 'Tipo', 'Descripción', 'Archivo', 'Subida por / fecha')),
    ],
}
# Una guía estructurada con todos los apartados que comprueba su diagnóstico.
CONTENIDO = {campo: 'Texto revisado de prueba' for campo in (
    'asignatura', 'carrera_semestre', 'docente_responsable', 'laboratorio', 'categoria_uso', 'duracion',
    'resultado_aprendizaje', 'objetivos', 'procedimiento', 'fundamento_teorico', 'medidas_seguridad',
    'resultados_esperados', 'criterios_evaluacion', 'manejo_residuos', 'bibliografia')} | {'maximo_estudiantes': 12}
EN_EL_PERIODO = datetime(2026, 9, 5, 15, tzinfo=zona.utc)


def _sin_identidad_real(pila):
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional',
                   'apps.documentos.presentation.expediente_pdf'):
        pila.enter_context(patch(modulo + '.identidad_actual', return_value=IDENTIDAD))
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional'):
        pila.enter_context(patch(modulo + '.logo_institucional', return_value=None))


def _informe(unidad):
    documentos = construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))
    return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')


def _anexo(unidad, codigo):
    return next(a for a in anexos_del(_informe(unidad), incluir_no_aplica=True) if a.exigido.codigo == codigo)


def _direccion(nombre, *argumentos, consulta=''):
    return settings.SITE_URL.rstrip('/') + reverse(nombre, args=argumentos) + consulta


class TablasDeLaEspecificacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad sin prácticas ' + tipo, slug='sin-practicas-' + tipo,
                                                    dependencia=tipo, fecha_inicio=date(2025, 1, 1))
                        for tipo in (*CON_PRACTICAS, 'observatorios')}

    def test_cada_anexo_lleva_las_tablas_y_columnas_de_la_especificacion(self):
        for tipo in CON_PRACTICAS:
            for codigo, tablas in TABLAS.items():
                with self.subTest(tipo=tipo, anexo=codigo):
                    anexo = _anexo(self.unidades[tipo], codigo)
                    registros = componer_anexo(anexo, *tramo_del_documento(anexo))['registros']
                    self.assertEqual([(r.titulo, tuple(r.cabecera)) for r in registros], tablas)
                    for registro in registros:
                        # Sin registros, la tabla se presenta vacía para que la falta se vea.
                        self.assertEqual(registro.filas, [], registro.titulo)
                        self.assertTrue(registro.vacio)
                        self.assertIsNone(registro.suma)

    def test_una_unidad_sin_registros_de_cada_tipo_arma_los_tres_anexos_en_pdf(self):
        for tipo in CON_PRACTICAS:
            numeros = {a.exigido.codigo: n for n, a in anexos_numerados(_informe(self.unidades[tipo]))}
            for codigo, tablas in TABLAS.items():
                with self.subTest(tipo=tipo, anexo=codigo):
                    anexo = _anexo(self.unidades[tipo], codigo)
                    with ExitStack() as pila:
                        _sin_identidad_real(pila)
                        pdf = pdf_del_anexo(anexo, *tramo_del_documento(anexo), codigo_documento='SLCID-PRUEBA',
                                            version=1)
                    texto = ' '.join('\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages).split())
                    for posicion, (titulo, _columnas) in enumerate(tablas, 1):
                        self.assertIn(f'{numeros[codigo]}.{posicion} {titulo.upper()}', texto)

    def test_el_observatorio_no_lleva_anexos_de_practicas(self):
        codigos = {a.exigido.codigo for a in anexos_del(_informe(self.unidades['observatorios']),
                                                         incluir_no_aplica=True)}
        self.assertFalse(codigos & set(TABLAS))


class _ConUnidad(TestCase):
    """Un laboratorio con su responsable técnico, un escenario, una asignatura con un tema y una actividad."""

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user('coordinadora-anexos-practicas', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user('tecnico-anexos-practicas', first_name='Tomás', last_name='Técnico')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de anexos de prácticas', slug='anexos-practicas',
                                           dependencia='laboratorios', fecha_inicio=date(2025, 1, 1),
                                           administrador=cls.coordinadora)
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.tecnico)
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='PRA-TALLER', nombre='Taller')
        cls.asignatura = Asignatura.objects.create(unidad=cls.unidad, codigo='PRA-101', nombre='Diseño asistido',
                                                   carrera='Computación', semestre='Quinto')
        cls.tema = TemaAsignatura.objects.create(
            asignatura=cls.asignatura, orden=1, unidad_tematica='Unidad 2. Modelado 3D', nombre='Modelado de piezas',
            resultado_aprendizaje='Modela una pieza funcional.')
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Práctica de modelado')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='anexos-practicas-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)

    def reserva(self, dia, **datos):
        reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.coordinadora, fecha=dia,
                                         hora_inicio=time(8), hora_fin=time(10), **datos)
        reserva.refresh_from_db()
        self.assertTrue(reserva.codigo_reserva)
        return reserva

    def plan(self, **datos):
        base = dict(unidad=self.unidad, fecha=date(2026, 9, 10), hora_inicio=time(8), hora_fin=time(10),
                    carrera='Computación', semestre='Quinto', asignatura='Diseño asistido',
                    docente_tutor='Dora Docente', tema='Modelado de piezas',
                    resultado_aprendizaje='Modela una pieza funcional.', estudiantes_planificados=12,
                    creado_por=self.coordinadora)
        return PlanificacionPractica.objects.create(**(base | datos))

    def guia(self, **datos):
        base = dict(actividad=self.actividad, titulo='Guía de modelado', codigo_guia='PRA-G-01', es_estructurada=True,
                    contenido=dict(CONTENIDO))
        guia = GuiaActividadReserva.objects.create(**(base | datos))
        # La fecha de actualización es automática: se fija dentro del período para no depender del día de la prueba.
        GuiaActividadReserva.objects.filter(pk=guia.pk).update(actualizado_en=EN_EL_PERIODO)
        return guia

    def contexto(self, codigo):
        anexo = _anexo(self.unidad, codigo)
        inicio, fin = tramo_del_documento(anexo)
        self.assertTrue(inicio <= date(2026, 9, 1) and date(2026, 11, 30) <= fin)
        return contexto_del_anexo(anexo, inicio, fin)

    def registros(self, codigo):
        anexo = _anexo(self.unidad, codigo)
        return componer_anexo(anexo, *tramo_del_documento(anexo))['registros']

    def consultas(self, codigo):
        """Las consultas que hace el constructor, sin contar la lectura de metas que comparte con el informe."""
        contexto = self.contexto(codigo)
        with CaptureQueriesContext(connection) as consultas:
            constructor_de(codigo)(contexto)
        return len(consultas)


class PlanificacionDeLasPracticasTests(_ConUnidad):
    def planificar(self):
        """Tres prácticas de dos asignaturas y cuatro planificaciones que no se presentan."""
        sesion = self.reserva(date(2026, 9, 10))
        sesion.espacios_solicitados.add(self.espacio)
        guia = self.guia(numero_version=2, es_vigente=True, estado_publicacion='publicada',
                         aprobado_por=self.coordinadora, aprobado_en=EN_EL_PERIODO)
        aprobada = self.plan(reserva=sesion, actividad=self.actividad, guia=guia, tema_asignatura=self.tema,
                             responsable_tecnico=self.responsable, estado='aprobada',
                             revisado_por=self.coordinadora, revisado_en=datetime(2026, 9, 1, 15, tzinfo=zona.utc))
        en_revision = self.plan(fecha=date(2026, 9, 17), estado='revision', tema='<p>Ensamble del conjunto</p>',
                                resultado_aprendizaje='<p>Ensambla el conjunto.</p>')
        otra = self.plan(asignatura='Robótica', carrera='Mecatrónica', semestre='Séptimo', docente_tutor='Rita Robles',
                         requiere_guia=False, estudiantes_planificados=8)
        self.plan(asignatura='Archivada', estado='archivada')
        self.plan(asignatura='Eliminada', eliminado_en=timezone.now(), es_version_vigente=False)
        self.plan(asignatura='Versión anterior', es_version_vigente=False)
        self.plan(asignatura='Otro período', fecha=date(2026, 5, 5))
        return aprobada, en_revision, otra

    def test_las_practicas_se_presentan_en_cualquier_estado_y_agrupadas_por_asignatura(self):
        aprobada, en_revision, otra = self.planificar()
        tabla = self.registros('PRACTICAS-FT02')[0]
        self.assertEqual(tabla.filas, [
            Grupo('Diseño asistido · Computación · Quinto · Dora Docente'),
            [Par(aprobada.codigo, 'v1'), Par('10/09/2026', '08:00–10:00'),
             Par('Unidad 2. Modelado 3D', 'Modelado de piezas'), 'Modela una pieza funcional.', 'PRA-TALLER',
             'Tomás Técnico', '12', Par('PRA-G-01', 'v2'), Par('Aprobada', 'Carla Coordinadora · 01/09/2026')],
            # Sin unidad del syllabus, sin escenario y sin responsable: la falta se ve en la celda.
            [Par(en_revision.codigo, 'v1'), Par('17/09/2026', '08:00–10:00'), Par('—', 'Ensamble del conjunto'),
             'Ensambla el conjunto.', '—', '—', '12', 'Sin guía', 'Pendiente de revisión'],
            Grupo('Robótica · Mecatrónica · Séptimo · Rita Robles'),
            [Par(otra.codigo, 'v1'), Par('10/09/2026', '08:00–10:00'), Par('—', 'Modelado de piezas'),
             'Modela una pieza funcional.', '—', '—', '8', 'No requiere', 'Borrador'],
        ])
        self.assertEqual(tabla.total,
                         'Total: 3 prácticas · aprobadas: 1 · en revisión: 1 · observadas: 0 · borradores: 1')

    def test_el_resumen_cuenta_por_asignatura_carrera_y_nivel(self):
        self.planificar()
        resumen = self.registros('PRACTICAS-FT02')[2]
        self.assertEqual(resumen.filas, [
            ['Diseño asistido', Par('Computación', 'Quinto'), '2', '1', '1', '1', '24'],
            ['Robótica', Par('Mecatrónica', 'Séptimo'), '1', '0', '0', '0', '8'],
        ])
        self.assertEqual(resumen.suma, ['Total', '', '3', '1', '1', '1', '32'])

    def test_una_sesion_programada_sin_planificacion_vigente_se_lista_y_la_cancelada_no(self):
        programa = ProgramacionReserva.objects.create(
            laboratorio=self.unidad, solicitante=self.coordinadora, asignatura=self.asignatura,
            fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 11, 30), dia_semana=3, hora_inicio=time(8),
            hora_fin=time(10))
        planificada = self.reserva(date(2026, 9, 17), programacion=programa, estado='confirmada')
        self.plan(reserva=planificada, fecha=planificada.fecha)
        sin_plan = self.reserva(date(2026, 9, 24), programacion=programa, estado='confirmada',
                                titulo_solicitud='Impresión de la pieza')
        sin_plan.espacios_solicitados.add(self.espacio)
        archivada = self.reserva(date(2026, 10, 1), programacion=programa, estado='confirmada')
        self.plan(reserva=archivada, fecha=archivada.fecha, estado='archivada')
        self.reserva(date(2026, 10, 8), programacion=programa, estado='cancelada')
        self.reserva(date(2026, 10, 15), estado='confirmada')  # Sin programación no es una sesión programada.
        tabla = self.registros('PRACTICAS-FT02')[1]
        situacion = Par('Sin planificación vigente', 'sesión confirmada')
        self.assertEqual(tabla.filas, [
            ['Diseño asistido', Par(sin_plan.codigo_reserva, '24/09/2026 · 08:00–10:00'), 'Impresión de la pieza',
             'PRA-TALLER', situacion],
            ['Diseño asistido', Par(archivada.codigo_reserva, '01/10/2026 · 08:00–10:00'), 'Sin tema previsto', '—',
             situacion],
        ])
        self.assertEqual(tabla.total, 'Total: 2 sesiones · canceladas, rechazadas o vencidas, que no se listan: 1')

    def test_no_hace_una_consulta_por_practica(self):
        def practica(dia):
            sesion = self.reserva(dia)
            sesion.espacios_solicitados.add(self.espacio)
            self.plan(reserva=sesion, fecha=dia, tema_asignatura=self.tema, responsable_tecnico=self.responsable,
                      revisado_por=self.coordinadora, asignatura=f'Asignatura del día {dia.day}')
        practica(date(2026, 9, 1))
        practica(date(2026, 9, 2))
        pocas = self.consultas('PRACTICAS-FT02')
        for dia in range(3, 9):
            practica(date(2026, 9, dia))
        self.assertEqual(self.consultas('PRACTICAS-FT02'), pocas)


class GuiasDePracticasTests(_ConUnidad):
    def otra_actividad(self, nombre):
        return CatalogoActividadReserva.objects.create(unidad=self.unidad, nombre=nombre)

    def test_guias_vigentes_contenido_minimo_y_versiones_sustituidas(self):
        self.guia(numero_version=1, estado_publicacion='publicada', aprobado_por=self.coordinadora,
                  aprobado_en=datetime(2026, 7, 10, 15, tzinfo=zona.utc))
        vigente = self.guia(numero_version=2, es_vigente=True, estado_publicacion='publicada',
                            aprobado_por=self.coordinadora, aprobado_en=EN_EL_PERIODO)
        vigente.archivo_firmado.save('firmada.pdf', ContentFile(b'%PDF-1.4 firmada'), save=False)
        vigente.firmado_en = datetime(2026, 9, 6, 15, tzinfo=zona.utc)
        vigente.save()
        borrador = self.guia(numero_version=3, estado_publicacion='borrador')
        incompleta = self.guia(actividad=self.otra_actividad('Práctica de ensamble'), titulo='Guía de ensamble',
                               codigo_guia='PRA-G-02', estado_publicacion='revision',
                               contenido={c: v for c, v in CONTENIDO.items()
                                          if c not in ('fundamento_teorico', 'bibliografia')})
        importada = GuiaActividadReserva(actividad=self.otra_actividad('Práctica importada'), titulo='Guía importada',
                                         estado_publicacion='revision')
        importada.archivo.save('importada.pdf', ContentFile(b'%PDF-1.4 importada'), save=True)
        # No se presentan: la archivada y la guía de una sesión de otro período.
        self.guia(actividad=self.otra_actividad('Práctica retirada'), codigo_guia='PRA-G-03', activo=False,
                  estado_publicacion='archivada')
        self.guia(actividad=self.otra_actividad('Práctica de otro período'), codigo_guia='PRA-G-04', es_vigente=True,
                  estado_publicacion='publicada', sesion=self.plan(fecha=date(2026, 5, 5)))
        practica = self.plan(actividad=self.actividad, guia=vigente, tema_asignatura=self.tema, estado='aprobada')

        vigentes, contenido, sustituidas = self.registros('GUIAS')
        sin_vinculo = Par('Texto revisado de prueba', 'sin tema del syllabus')
        self.assertEqual(vigentes.filas, [
            [Par('Sin código', 'v1'),
             Par('Guía importada', Enlace('Abrir PDF', _direccion('ver_guia_actividad', importada.pk,
                                                                   consulta='?preview=pdf'))),
             'Una sesión', 'Sin vincular', '—', 'Pendiente de revisión', '—', '—'],
            [Par('PRA-G-01', 'v2'),
             Par('Guía de modelado', Enlace('Abrir PDF', _direccion('ver_guia_actividad', vigente.pk,
                                                                     consulta='?preview=pdf'))),
             'Una sesión', Par('Diseño asistido', 'Modelado de piezas'), 'Modela una pieza funcional.',
             'Aprobada y publicada', Par('Carla Coordinadora · 05/09/2026', 'firmada el 06/09/2026'), practica.codigo],
            [Par('PRA-G-01', 'v3'),
             Par('Guía de modelado', Enlace('Abrir PDF', _direccion('ver_guia_actividad', borrador.pk,
                                                                     consulta='?preview=pdf'))),
             'Una sesión', sin_vinculo, 'Texto revisado de prueba', 'Borrador', '—', '—'],
            [Par('PRA-G-02', 'v1'),
             Par('Guía de ensamble', Enlace('Abrir PDF', _direccion('ver_guia_actividad', incompleta.pk,
                                                                     consulta='?preview=pdf'))),
             'Una sesión', sin_vinculo, 'Texto revisado de prueba', 'Pendiente de revisión', '—', '—'],
        ])
        self.assertEqual(vigentes.total,
                         'Total: 4 guías · aprobadas y publicadas: 1 · vinculadas al syllabus: 1 · firmadas: 1')

        sin_aprobar = 'Falta: aprobación, versión vigente, responsable de la aprobación'
        self.assertEqual(contenido.filas, [
            # De una guía importada solo se comprueban el archivo, la aprobación y el vínculo académico.
            [Par('Guía importada', 'v1 · PDF importado'), *['—'] * 7, sin_aprobar + ', vínculo con el syllabus'],
            [Par('PRA-G-01', 'v2'), *['Sí'] * 7, 'Completo'],
            [Par('PRA-G-01', 'v3'), *['Sí'] * 7, sin_aprobar + ', vínculo con el syllabus'],
            [Par('PRA-G-02', 'v1'), 'Sí', 'Falta', 'Sí', 'Sí', 'Sí', 'Sí', 'Falta',
             sin_aprobar + ', fundamento teórico, bibliografía, vínculo con el syllabus'],
        ])
        self.assertEqual(contenido.total, 'Total: 4 guías · con respaldo completo: 1 · importadas en PDF, sin '
                                          'comprobación por apartados: 1')
        self.assertEqual(sustituidas.filas, [
            [Par('PRA-G-01', 'Guía de modelado'), 'v1', 'v2', '05/09/2026', 'Carla Coordinadora'],
        ])

    def test_cada_apartado_que_falta_en_el_diagnostico_deja_su_columna_en_falta(self):
        apartados = ('objetivos', 'fundamento_teorico', 'procedimiento', 'medidas_seguridad', 'manejo_residuos',
                     'criterios_evaluacion', 'bibliografia')
        for posicion, apartado in enumerate(apartados, 1):
            self.guia(actividad=self.otra_actividad(f'Práctica sin {apartado}'), codigo_guia=f'PRA-SIN-{posicion}',
                      estado_publicacion='revision',
                      contenido={c: v for c, v in CONTENIDO.items() if c != apartado})
        contenido = self.registros('GUIAS')[1]
        self.assertEqual(len(contenido.filas), len(apartados))
        for posicion, fila in enumerate(contenido.filas, 1):
            with self.subTest(apartado=apartados[posicion - 1]):
                self.assertEqual(fila[0], Par(f'PRA-SIN-{posicion}', 'v1'))
                self.assertEqual([i for i, celda in enumerate(fila[1:8], 1) if celda == 'Falta'], [posicion])
                self.assertNotIn(' o justificación', fila[8])  # El pendiente va abreviado.

    def test_una_version_aprobada_fuera_del_periodo_no_consta_como_sustituida_en_el(self):
        self.guia(numero_version=1, estado_publicacion='publicada', aprobado_por=self.coordinadora,
                  aprobado_en=datetime(2026, 2, 10, 15, tzinfo=zona.utc))
        self.guia(numero_version=2, es_vigente=True, estado_publicacion='publicada', aprobado_por=self.coordinadora,
                  aprobado_en=datetime(2026, 5, 10, 15, tzinfo=zona.utc))
        vigentes, _contenido, sustituidas = self.registros('GUIAS')
        self.assertEqual([fila[0] for fila in vigentes.filas], [Par('PRA-G-01', 'v2')])
        self.assertEqual(sustituidas.filas, [])

    def test_no_hace_una_consulta_por_guia(self):
        def guia(numero):
            actividad = self.otra_actividad(f'Práctica {numero}')
            guia = self.guia(actividad=actividad, codigo_guia=f'PRA-N-{numero}', es_vigente=True,
                             estado_publicacion='publicada', aprobado_por=self.coordinadora, aprobado_en=EN_EL_PERIODO)
            self.plan(actividad=actividad, guia=guia, tema_asignatura=self.tema)
        guia(1)
        guia(2)
        pocas = self.consultas('GUIAS')
        for numero in range(3, 9):
            guia(numero)
        self.assertEqual(self.consultas('GUIAS'), pocas)


class AsistenciaYEvidenciasTests(_ConUnidad):
    def ejecutar(self, plan, **datos):
        base = dict(planificacion=plan, fecha_ejecucion=plan.fecha, hora_inicio_real=time(8, 5),
                    hora_fin_real=time(9, 50), estudiantes_asistentes=3, recursos_utilizados='Impresora 3D y PLA.',
                    responsable_tecnico=self.responsable, cumplimiento_resultado='parcial',
                    creado_por=self.coordinadora)
        return EjecucionPractica.objects.create(**(base | datos))

    def adjuntar(self, ejecucion, tipo, nombre, descripcion):
        evidencia = EvidenciaPractica(ejecucion=ejecucion, tipo=tipo, nombre_original=nombre,
                                      extension='.' + nombre.rsplit('.', 1)[-1], descripcion=descripcion,
                                      subido_por=self.coordinadora)
        evidencia.archivo.save(nombre, ContentFile(b'Respaldo exclusivo de prueba.'), save=True)
        return evidencia

    def participante(self, reserva, nombre, **datos):
        return RegistroParticipanteReserva.objects.create(reserva=reserva, nombre=nombre, **(
            dict(rol='participante', tipo_usuario='estudiante', carrera='veterinaria',
                 nivel_academico='quinto_semestre', asistencia='asistio') | datos))

    def practicas(self):
        """Una práctica validada con su respaldo, una cancelada y una en revisión sin lista en la ejecución."""
        sesion = self.reserva(date(2026, 9, 10), estado='completada')
        ana = self.participante(sesion, 'Ana Andrade')
        beto = self.participante(sesion, 'Beto Bravo', asistencia='no_asistio')
        dora = self.participante(sesion, 'Dora Docente', rol='solicitante', tipo_usuario='docente', carrera='',
                                 nivel_academico='')
        # En la sesión quedó sin asistir; la lista que se guardó con la ejecución dice que asistió.
        elena = self.participante(sesion, 'Elena Externa', tipo_usuario='externo', carrera='', nivel_academico='',
                                  institucion='Colegio Carchi', asistencia='no_asistio')
        equipo = UnidadEquipo.objects.create(
            codigo_unidad='PRA-EQ-01', laboratorio=self.unidad,
            equipo=EquiposServicios.objects.create(nombre='Impresora de prueba', codigo='PRA-MODELO-01'))
        incidencia = IncidenciaEquipo.objects.create(
            equipo=equipo, unidad=self.unidad, titulo='Quemadura leve', descripcion='Contacto con la boquilla.',
            tipo='seguridad', reportada_por=self.coordinadora)
        validada = self.ejecutar(
            self.plan(reserva=sesion, requiere_guia=False), estado='validada', validado_por=self.coordinadora,
            validado_en=datetime(2026, 9, 11, 15, tzinfo=zona.utc), tuvo_incidente=True, incidencia=incidencia,
            detalle_operativo={'participantes': [
                {'id': str(registro.pk), 'nombre': registro.nombre, 'asistencia_codigo': asistencia}
                for registro, asistencia in ((ana, 'asistio'), (beto, 'no_asistio'), (dora, 'asistio'),
                                             (elena, 'asistio'))]})
        adjuntos = [self.adjuntar(validada, tipo, nombre, descripcion) for tipo, nombre, descripcion in (
            ('asistencia', 'asistencia.pdf', 'Registro firmado por los tres asistentes.'),
            ('fotografia', 'foto-1.jpg', 'Ana Andrade prepara la impresora, 10/09/2026.'),
            ('fotografia', 'foto-2.jpg', 'Elena Externa retira la pieza, 10/09/2026.'),
            ('informe', 'informe.docx', 'Informe de Ana Andrade con parámetros y conclusiones.'),
            ('otro', 'acta.pdf', 'Acta de entrega de la pieza.'))]
        cancelada = self.ejecutar(
            self.plan(fecha=date(2026, 9, 17), requiere_guia=False), resultado='cancelada',
            motivo='Corte de energía.', hora_inicio_real=None, hora_fin_real=None, estudiantes_asistentes=0,
            recursos_utilizados='', responsable_tecnico=None, cumplimiento_resultado='')
        otra_sesion = self.reserva(date(2026, 9, 24), estado='completada')
        prevista = self.participante(otra_sesion, 'Fabio Flores', asistencia='prevista')
        en_revision = self.ejecutar(self.plan(reserva=otra_sesion, fecha=date(2026, 9, 24), requiere_guia=False),
                                    estado='revision', estudiantes_asistentes=1)
        # No se presenta: la ejecución eliminada.
        self.ejecutar(self.plan(fecha=date(2026, 10, 1), asignatura='Eliminada'), eliminado_en=timezone.now())
        return SimpleNamespace(sesion=sesion, otra_sesion=otra_sesion, validada=validada, cancelada=cancelada,
                               en_revision=en_revision, adjuntos=adjuntos, incidencia=incidencia,
                               personas=(ana, beto, dora, elena, prevista))

    def test_ejecucion_de_las_practicas_en_cualquier_estado(self):
        p = self.practicas()
        numeros = {a.exigido.codigo: n for n, a in anexos_numerados(_informe(self.unidad))}
        tabla = self.registros('PRACTICAS-FT03')[0]
        self.assertEqual(tabla.filas, [
            # El incidente se cita por el equipo y la fecha del reporte, y por el anexo que lo presenta.
            [Par(p.validada.planificacion.codigo, p.sesion.codigo_reserva), Par('10/09/2026', '08:05–09:50'),
             'Ejecutada', Par('3', 'previstos 12'), 'Impresora 3D y PLA.', 'Parcial',
             Par('Sí', f"PRA-EQ-01 · {fecha(p.incidencia.fecha_reporte)} · anexo {numeros['INDUCCION-SEGURIDAD']}"),
             'Tomás Técnico', Par('Validada y cerrada', 'Carla Coordinadora · 11/09/2026')],
            [p.cancelada.planificacion.codigo, '17/09/2026', Par('Cancelada', 'Corte de energía.'),
             Par('0', 'previstos 12'), '—', '—', 'No', '—', 'Borrador'],
            [Par(p.en_revision.planificacion.codigo, p.otra_sesion.codigo_reserva), Par('24/09/2026', '08:05–09:50'),
             'Ejecutada', Par('1', 'previstos 12'), 'Impresora 3D y PLA.', 'Parcial', 'No', 'Tomás Técnico',
             'Pendiente de revisión'],
        ])
        self.assertEqual(tabla.total, 'Total: 3 prácticas · ejecutadas: 2 · reprogramadas: 0 · canceladas: 1 · '
                                      'validadas: 1 · asistentes: 4')

    def test_asistencia_nominal_de_la_ejecucion_o_en_su_falta_de_la_sesion(self):
        p = self.practicas()
        ana, _beto, dora, elena, _prevista = p.personas
        estudiante = Par(ana.get_tipo_usuario_display(),
                         f'{ana.get_carrera_display()} · {ana.get_nivel_academico_display()}')
        codigo, otro = p.validada.planificacion.codigo, p.en_revision.planificacion.codigo
        tabla = self.registros('PRACTICAS-FT03')[1]
        self.assertEqual(tabla.filas, [
            [codigo, 'Ana Andrade', estudiante, 'Asistió', '—'],
            [codigo, 'Beto Bravo', estudiante, 'No asistió', '—'],
            [codigo, 'Dora Docente', dora.get_tipo_usuario_display(), 'Asistió', 'solicitante de la sesión'],
            [codigo, 'Elena Externa', elena.get_tipo_usuario_display(), 'Asistió',
             'Colegio Carchi; en la sesión consta: no asistió'],
            [otro, 'Fabio Flores', estudiante, 'Sin registrar', '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 5 participantes · asistieron: 3 · no asistieron: 1 · sin registrar: 1 · '
                                      'prácticas ejecutadas con lista nominal: 2 de 2 · tomadas del registro de la '
                                      'sesión, por no constar en la ejecución: 1')

    def test_el_indice_cuenta_las_evidencias_por_tipo_y_toma_el_respaldo_del_diagnostico(self):
        p = self.practicas()
        contexto = self.contexto('PRACTICAS-FT03')
        indice = constructor_de('PRACTICAS-FT03')(contexto)[2]
        asignatura = 'Diseño asistido'
        self.assertEqual(indice.filas, [
            [Par(p.validada.planificacion.codigo, asignatura), '1', '0', '2', '0', '1', '0', 'Completo'],
            # Una práctica que no se realizó no tiene desarrollo que respaldar.
            [Par(p.cancelada.planificacion.codigo, asignatura), '0', '0', '0', '0', '0', '0', 'No aplica: cancelada'],
            [Par(p.en_revision.planificacion.codigo, asignatura), '0', '0', '0', '0', '0', '0',
             'Falta: validación de la ejecución, responsable de la validación, asistencia, evidencia'],
        ])
        self.assertEqual(indice.total,
                         'Total: 3 prácticas · con respaldo completo: 1 · evidencias: 5 · de ellas, de otro tipo: 1')
        # El respaldo es el del informe: sus mismos requisitos, solo abreviados.
        diagnosticos = {d['id']: d for d in contexto.registros['diagnostico_practicas']}
        self.assertTrue(diagnosticos[p.validada.pk]['cumple'])
        for requisito in diagnosticos[p.en_revision.pk]['faltantes']:
            self.assertIn(REQUISITOS_CORTOS[requisito], indice.filas[2][-1])

    def test_cada_evidencia_se_abre_con_la_vista_protegida(self):
        p = self.practicas()
        tabla = self.registros('PRACTICAS-FT03')[3]
        codigo = p.validada.planificacion.codigo
        quien = Par('Carla Coordinadora', fecha(p.adjuntos[0].creado_en))
        tipos = dict(EvidenciaPractica.TIPOS)

        def archivo(evidencia, formato):
            return Par(Enlace('Abrir', _direccion('evidencia_practica', self.unidad.slug, evidencia.pk)), formato)
        asistencia, foto_1, foto_2, informe, acta = p.adjuntos
        self.assertEqual(tabla.filas, [
            [codigo, tipos['asistencia'], 'Registro firmado por los tres asistentes.', archivo(asistencia, 'PDF'),
             quien],
            [codigo, tipos['fotografia'], 'Ana Andrade prepara la impresora, 10/09/2026.', archivo(foto_1, 'JPG'),
             quien],
            [codigo, tipos['fotografia'], 'Elena Externa retira la pieza, 10/09/2026.', archivo(foto_2, 'JPG'), quien],
            [codigo, tipos['informe'], 'Informe de Ana Andrade con parámetros y conclusiones.',
             archivo(informe, 'DOCX'), quien],
            [codigo, tipos['otro'], 'Acta de entrega de la pieza.', archivo(acta, 'PDF'), quien],
        ])
        for fila in tabla.filas:
            self.assertNotIn(settings.MEDIA_URL, fila[3].principal.url)

    def test_no_hace_una_consulta_por_practica_ni_por_evidencia(self):
        def practica(dia):
            sesion = self.reserva(dia, estado='completada')
            registro = self.participante(sesion, f'Participante del día {dia.day}')
            ejecucion = self.ejecutar(
                self.plan(reserva=sesion, fecha=dia, requiere_guia=False), estado='validada',
                validado_por=self.coordinadora, validado_en=timezone.now(), detalle_operativo={'participantes': [
                    {'id': str(registro.pk), 'nombre': registro.nombre, 'asistencia_codigo': 'asistio'}]})
            self.adjuntar(ejecucion, 'bitacora', 'bitacora.pdf', 'Bitácora de la sesión.')
            self.adjuntar(ejecucion, 'producto', 'producto.zip', 'Producto entregado.')
        practica(date(2026, 9, 1))
        practica(date(2026, 9, 2))
        pocas = self.consultas('PRACTICAS-FT03')
        for dia in range(3, 9):
            practica(date(2026, 9, dia))
        self.assertEqual(self.consultas('PRACTICAS-FT03'), pocas)


class CitaDelIncidenteTests(SimpleTestCase):
    """La incidencia no tiene código propio: se cita por su equipo, su fecha y el anexo que la presenta."""

    def ejecucion(self, tipo=None, tuvo=True):
        incidencia = tipo and SimpleNamespace(tipo=tipo, equipo=SimpleNamespace(codigo_unidad='EQ-07'),
                                              fecha_reporte=date(2026, 9, 10))
        return SimpleNamespace(tuvo_incidente=tuvo, incidencia_id=1 if incidencia else None, incidencia=incidencia)

    def test_seguridad_va_a_su_anexo_y_una_falla_al_de_equipamiento(self):
        numeros = {'EQUIPAMIENTO': 2, 'INDUCCION-SEGURIDAD': 8}
        self.assertEqual(_incidente(self.ejecucion('seguridad'), numeros), Par('Sí', 'EQ-07 · 10/09/2026 · anexo 8'))
        self.assertEqual(_incidente(self.ejecucion('falla'), numeros), Par('Sí', 'EQ-07 · 10/09/2026 · anexo 2'))
        self.assertEqual(_incidente(self.ejecucion('falla'), {}),
                         Par('Sí', 'EQ-07 · 10/09/2026 · anexo de equipamiento'))

    def test_un_incidente_sin_registro_vinculado_se_dice_y_sin_incidente_es_no(self):
        self.assertEqual(_incidente(self.ejecucion(), {}), Par('Sí', 'sin incidencia vinculada'))
        self.assertEqual(_incidente(self.ejecucion(tuvo=False), {}), 'No')
