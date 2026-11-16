"""Contenido de los anexos de uso, mantenimiento, inventario y fichas técnicas.

Fija lo acordado en docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.1 a 4.4:
- las tablas de cada anexo, en el orden y con las columnas de la especificación;
- los ajustes por tipo de unidad: la planta piloto anota la receta en la sesión y separa los
  consumos de producción; el centro experimental titula la 3.4 «Reactivos, agroquímicos y
  medicamentos veterinarios» y lleva el eje y el ciclo en sus espacios; el observatorio usa la
  versión reducida del inventario;
- cada tabla presenta lo del período en cualquier estado, sin lo cancelado ni lo anulado.
"""
from datetime import date, datetime, time
from datetime import timezone as zona
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import (
    Enlace, Grupo, Par, constructor_de, contexto_del_anexo, fecha,
)
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.formacion.models.asignaturas import Asignatura
from apps.formacion.models.practicas import PlanificacionPractica
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
from apps.reservas.models.visitas import SolicitudVisita

TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')
EQUIPOS = ('Código / nombre', 'Marca / modelo', 'Serie', 'Código del bien / clase', 'Custodio / ubicación',
           'Estado / criticidad', 'Adquisición', 'Verificación física', 'Ficha técnica')
ACTA = ('Acta de revisión física del período',
        ('Código', 'Fecha', 'Alcance', 'Responsable', 'Observaciones', 'Respaldo'))
BAJAS = ('Bajas y traspasos del período', ('Equipo', 'Movimiento', 'Fecha', 'Motivo', 'Destino / reemplazo', 'Acta'))
REACTIVOS = ('Código / nombre', 'Presentación / marca', 'Lote', 'Cantidad', 'Vencimiento', 'Ubicación',
             'Estado del lote', 'Ficha de seguridad')
# Las tablas de cada anexo y sus columnas, tal como las fija la especificación.
TABLAS = {
    'REGISTRO-USO': [
        ('Sesiones del período',
         ('Código', 'Fecha / horario', 'Espacio o recurso', 'Propósito', 'Actividad o asignatura',
          'Solicitante / perfil', 'Participantes', 'Cierre', 'Horas efectivas')),
        ('Sesiones por propósito',
         ('Propósito', 'Registradas', 'Atendidas', 'Sin cierre', 'Horas efectivas', 'Participantes')),
        ('Sesiones por mes', ('Mes', 'Registradas', 'Atendidas', 'Horas efectivas', 'Participantes')),
        ('Visitas',
         ('Fecha / sesión', 'Institución o grupo', 'Categoría / propósito', 'Personas / edades', 'Recorrido',
          'Guía de la visita', 'Responsable')),
    ],
    'EQUIPAMIENTO': [
        ('Plan de mantenimiento vigente',
         ('Equipo', 'Criticidad', 'Plan', 'Tipo', 'Frecuencia', 'Última / próxima', 'Ejecutor / proveedor',
          'Responsable')),
        ('Mantenimientos del período',
         ('Orden', 'Equipo', 'Tipo / origen', 'Programada / ejecutada', 'Estado', 'Ejecutor / costo', 'Resultado',
          'Resultado operativo', 'Informe')),
        ('Cumplimiento del plan en equipos críticos',
         ('Equipo crítico', 'Programadas exigibles', 'Ejecutadas con respaldo', 'Pendientes', 'Situación')),
        ('Disponibilidad: fallas e incidencias técnicas',
         ('Reporte', 'Equipo', 'Tipo / prioridad', 'Descripción', 'Detuvo la operación', 'Días fuera de servicio',
          'Solución', 'Estado')),
        ('Funcionalidad: pruebas funcionales',
         ('Fecha', 'Equipo', 'Procedimiento', 'Criterio de aceptación', 'Resultado', 'Hallazgos', 'Responsable',
          'Respaldo')),
        ('Estado de los equipos al corte', ('Estado', 'Equipos', 'De ellos, críticos')),
        ('Mantenimiento de infraestructura y espacios',
         ('Espacio o instalación', 'Intervención', 'Programada / ejecutada', 'Responsable', 'Estado', 'Respaldo')),
    ],
    'INVENTARIO-CORTE': [
        ACTA,
        ('Equipos', EQUIPOS),
        BAJAS,
        ('Reactivos', REACTIVOS),
        ('Insumos y materiales',
         ('Código / nombre', 'Tipo', 'Existencia', 'Mínimo / objetivo', 'Lotes vigentes', 'Próximo vencimiento',
          'Ubicación', 'Origen')),
        ('Movimientos del período',
         ('Fecha', 'Artículo', 'Movimiento / motivo', 'Cantidad', 'Saldo', 'Lote', 'Referencia', 'Responsable')),
    ],
    'FICHAS-TECNICAS': [
        ('Ficha de la unidad', ('Dato', 'Valor')),
        ('Espacios y talleres',
         ('Código / nombre', 'Tipo', 'Ubicación', 'Capacidad', 'Mobiliario e infraestructura', 'Equipos asociados',
          'Responsable', 'Reservable / visitable', 'Uso en el período')),
        ('Software y simuladores',
         ('Código / nombre', 'Versión', 'Tipo', 'Acceso', 'Licencias', 'Instalado en', 'Uso en equipo',
          'Uso en el período')),
    ],
}
# El centro experimental nombra así la tabla de reactivos.
REACTIVOS_DEL_CENTRO = 'Reactivos, agroquímicos y medicamentos veterinarios'
# El observatorio lleva la versión reducida del inventario: equipos informáticos, software y espacios.
INVENTARIO_DEL_OBSERVATORIO = [
    ACTA,
    ('Equipos informáticos', EQUIPOS),
    BAJAS,
    ('Software y licencias', ('Código / nombre', 'Versión', 'Tipo / acceso', 'Licencias', 'Instalado en')),
    ('Espacios', ('Código / nombre', 'Tipo', 'Capacidad', 'Ubicación')),
]
DATOS_DE_LA_FICHA = ['Nombre y tipo', 'Ubicación', 'Responsable', 'Horario de operación', 'Aforo de seguridad',
                     'Puestos con mobiliario / equipados', 'Personal', 'Carreras que atiende']
# Qué anexos de esta sección lleva cada tipo de unidad.
ANEXOS_DEL_TIPO = {
    'laboratorios': ('REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS'),
    'plantas_piloto': ('REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS'),
    'centro_experimental': ('REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS'),
    'observatorios': ('EQUIPAMIENTO', 'INVENTARIO-CORTE'),
}


def _al_mediodia(dia):
    """Un instante del día dado: las 10:00 en Ecuador."""
    return datetime(dia.year, dia.month, dia.day, 15, tzinfo=zona.utc)


def _informe(unidad):
    documentos = construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))
    return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')


def _anexo(unidad, codigo):
    return next(a for a in anexos_del(_informe(unidad), incluir_no_aplica=True) if a.exigido.codigo == codigo)


def _tablas_esperadas(tipo, codigo):
    if codigo == 'INVENTARIO-CORTE' and tipo == 'observatorios':
        return INVENTARIO_DEL_OBSERVATORIO
    tablas = list(TABLAS[codigo])
    if codigo == 'INVENTARIO-CORTE' and tipo == 'centro_experimental':
        tablas[3] = (REACTIVOS_DEL_CENTRO, REACTIVOS)
    return tablas


class _ConUnidades(TestCase):
    """Una unidad de cada tipo, con su coordinadora y su responsable técnico."""

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user('coordinadora-anexos-recursos', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user('tecnico-anexos-recursos', first_name='Tomás', last_name='Técnico')
        cls.estudiante = usuarios.create_user('estudiante-anexos-recursos', first_name='Ana', last_name='Andrade')
        cls.unidades = {tipo: Unidad.objects.create(
            nombre=f'Unidad de recursos {tipo}', slug=f'anexos-recursos-{tipo}', dependencia=tipo,
            fecha_inicio=date(2025, 1, 1), administrador=cls.coordinadora) for tipo in TIPOS}
        cls.unidad = cls.unidades['laboratorios']
        cls.responsable = ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.tecnico,
                                                           rol='responsable_tecnico')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='anexos-recursos-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)

    def contexto(self, codigo, tipo='laboratorios'):
        anexo = _anexo(self.unidades[tipo], codigo)
        inicio, fin = tramo_del_documento(anexo)
        self.assertTrue(inicio <= date(2026, 7, 1) and date(2026, 12, 31) <= fin)
        return contexto_del_anexo(anexo, inicio, fin)

    def registros(self, codigo, tipo='laboratorios'):
        return constructor_de(codigo)(self.contexto(codigo, tipo))

    def tabla(self, codigo, titulo, tipo='laboratorios'):
        return next(r for r in self.registros(codigo, tipo) if r.titulo == titulo)

    @classmethod
    def equipo(cls, codigo, nombre, unidad=None, **datos):
        modelo = EquiposServicios.objects.create(nombre=nombre, codigo='MOD-' + codigo,
                                                 **{c: datos.pop(c) for c in ('marca', 'modelo') if c in datos})
        return UnidadEquipo.objects.create(codigo_unidad=codigo, laboratorio=unidad or cls.unidad, equipo=modelo,
                                           **datos)

    def evidencia(self, tipo, codigo, dia, unidad=None, **datos):
        base = dict(unidad=unidad or self.unidad, tipo=tipo, codigo=codigo, fecha=dia, titulo=f'Registro {codigo}',
                    descripcion='Registro de prueba.', responsable=self.tecnico, creado_por=self.coordinadora,
                    enlace=f'https://example.org/{codigo.lower()}')
        return EvidenciaGestionUnidad.objects.create(**(base | datos))

    def reserva(self, dia, unidad=None, **datos):
        base = dict(laboratorio=unidad or self.unidad, usuario=self.estudiante, fecha=dia, hora_inicio=time(8),
                    hora_fin=time(10))
        reserva = Reserva.objects.create(**(base | datos))
        reserva.refresh_from_db()
        self.assertTrue(reserva.codigo_reserva)
        return reserva


class TablasDeLaEspecificacionTests(_ConUnidades):
    def test_cada_anexo_lleva_las_tablas_y_columnas_de_la_especificacion(self):
        for tipo, codigos in ANEXOS_DEL_TIPO.items():
            for codigo in codigos:
                with self.subTest(tipo=tipo, anexo=codigo):
                    registros = self.registros(codigo, tipo)
                    self.assertEqual([(r.titulo, tuple(r.cabecera)) for r in registros],
                                     _tablas_esperadas(tipo, codigo))

    def test_en_una_unidad_vacia_las_tablas_se_presentan_sin_filas(self):
        for tipo, codigos in ANEXOS_DEL_TIPO.items():
            for codigo in codigos:
                with self.subTest(tipo=tipo, anexo=codigo):
                    for registro in self.registros(codigo, tipo):
                        if registro.ficha:
                            continue
                        self.assertEqual(registro.filas, [], registro.titulo)
                        self.assertTrue(registro.vacio, registro.titulo)

    def test_la_ficha_de_la_unidad_lleva_los_datos_de_la_especificacion(self):
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental'):
            with self.subTest(tipo=tipo):
                ficha = self.registros('FICHAS-TECNICAS', tipo)[0]
                self.assertTrue(ficha.ficha)
                self.assertEqual([dato for dato, _valor in ficha.filas], DATOS_DE_LA_FICHA)

    def test_el_observatorio_no_lleva_registro_de_uso_ni_fichas(self):
        codigos = {a.exigido.codigo for a in anexos_del(_informe(self.unidades['observatorios']),
                                                         incluir_no_aplica=True)}
        self.assertFalse(codigos & {'REGISTRO-USO', 'FICHAS-TECNICAS'})


class RegistrosDeUsoTests(_ConUnidades):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='USO-ESP-01', nombre='Mesa de corte')
        cls.actividad = CatalogoActividadReserva.objects.create(unidad=cls.unidad, nombre='Corte láser guiado')

    def sesiones(self):
        """Una sesión atendida con horario real, una confirmada y una cancelada que no se lista."""
        atendida = self.reserva(
            date(2026, 9, 10), estado='completada', resultado_cierre='atendida', proposito_codigo='docencia_practica',
            actividad_catalogo=self.actividad, numero_participantes=12, tipo_usuario_solicitante='estudiante',
            carrera_solicitante='veterinaria', nivel_academico_solicitante='quinto_semestre',
            detalle_ejecucion={'registrada_en': '2026-09-10T10:00:00-05:00', 'asistentes_total': 10,
                               'horario_real': {'inicio': '08:15', 'fin': '09:45'}})
        atendida.espacios_solicitados.add(self.espacio)
        confirmada = self.reserva(date(2026, 10, 5), estado='confirmada', proposito_codigo='investigacion_innovacion',
                                  titulo_solicitud='Ensayo de materiales', hora_inicio=time(9), hora_fin=time(11),
                                  numero_participantes=2)
        self.reserva(date(2026, 9, 12), estado='cancelada', proposito_codigo='docencia_practica')
        self.reserva(date(2026, 5, 12), estado='completada')  # De otro período.
        return atendida, confirmada

    def test_las_sesiones_se_presentan_en_cualquier_estado_salvo_las_descartadas(self):
        atendida, confirmada = self.sesiones()
        tabla = self.tabla('REGISTRO-USO', 'Sesiones del período')
        self.assertEqual(tabla.filas, [
            [atendida.codigo_reserva, Par('10/09/2026', 'previsto 08:00–10:00 · real 08:15–09:45'), 'USO-ESP-01',
             atendida.get_proposito_codigo_display(), 'Corte láser guiado',
             Par('Ana Andrade', ' · '.join((atendida.get_tipo_usuario_solicitante_display(),
                                           atendida.get_carrera_solicitante_display(),
                                           atendida.get_nivel_academico_solicitante_display()))),
             Par('12', 'asistieron 10'), Par(atendida.get_estado_display(), atendida.get_resultado_cierre_display()),
             '1,5'],
            [confirmada.codigo_reserva, Par('05/10/2026', 'previsto 09:00–11:00'), '—',
             confirmada.get_proposito_codigo_display(), 'Ensayo de materiales', 'Ana Andrade', '2',
             confirmada.get_estado_display(), '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 sesiones · atendidas: 1 · horas efectivas: 1,5 · participantes: 10 · '
                                      'canceladas, rechazadas o vencidas, que no se listan: 1')

    def test_los_resumenes_cuentan_por_proposito_y_por_mes(self):
        atendida, confirmada = self.sesiones()
        _sesiones, por_proposito, por_mes, _visitas = self.registros('REGISTRO-USO')
        self.assertEqual(por_proposito.filas, [
            [atendida.get_proposito_codigo_display(), '1', '1', '0', '1,5', '10'],
            [confirmada.get_proposito_codigo_display(), '1', '0', '1', '0', '0'],
        ])
        self.assertEqual(por_proposito.suma, ['Total', '2', '1', '1', '1,5', '10'])
        # Las columnas de la 1.3 las fija la prueba de estructura; aquí, el mes y lo que se cuenta en él.
        self.assertEqual([fila[:3] for fila in por_mes.filas],
                         [['Septiembre 2026', '1', '1'], ['Octubre 2026', '1', '0']])

    def test_una_visita_se_presenta_con_su_sesion_y_su_recorrido(self):
        sesion = self.reserva(date(2026, 9, 20), estado='confirmada')
        visita = SolicitudVisita.objects.create(unidad=self.unidad, reserva=sesion, responsable=self.coordinadora,
                                                categoria='externa', institucion='Colegio Nacional Tulcán',
                                                proposito='academica', personas=25, rango_edades='15 a 17 años',
                                                guia=self.tecnico)
        visita.recorrido.add(self.espacio)
        cancelada = self.reserva(date(2026, 9, 27), estado='cancelada')
        SolicitudVisita.objects.create(unidad=self.unidad, reserva=cancelada, institucion='Visita cancelada',
                                       personas=10)
        tabla = self.tabla('REGISTRO-USO', 'Visitas')
        self.assertEqual(tabla.filas, [
            [Par('20/09/2026', sesion.codigo_reserva), 'Colegio Nacional Tulcán',
             Par(visita.get_categoria_display(), visita.get_proposito_display()), Par('25', '15 a 17 años'),
             # La guía de la visita: quién guía y cuántos guías pide.
             'USO-ESP-01', Par('Tomás Técnico', 'guías necesarios: 1'), 'Carla Coordinadora'],
        ])

    def test_en_la_planta_piloto_la_actividad_lleva_la_receta(self):
        from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
        planta = self.unidades['plantas_piloto']
        producto = Producto.objects.create(unidad=planta, codigo='USO-YOG', nombre='Yogur natural', unidad_medida='kg')
        receta = Receta.objects.create(unidad=planta, producto=producto, codigo='USO-REC-YOG', nombre='Yogur batido',
                                       cantidad_base=10, unidad_base='kg', rendimiento_esperado=10)
        sesion = self.reserva(date(2026, 9, 15), unidad=planta, estado='confirmada', receta=receta,
                              titulo_solicitud='Práctica de fermentación')
        fila = self.tabla('REGISTRO-USO', 'Sesiones del período', 'plantas_piloto').filas[0]
        self.assertEqual(fila[0], sesion.codigo_reserva)
        self.assertEqual(fila[4], Par('Práctica de fermentación', str(receta)))


class MantenimientoYEquipamientoTests(_ConUnidades):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.balanza = cls.equipo('MAN-EQ-01', 'Balanza analítica', criticidad='critico',
                                 fecha_ultimo_mantenimiento=date(2026, 1, 10))
        cls.horno = cls.equipo('MAN-EQ-02', 'Horno de secado', criticidad='critico')
        cls.agitador = cls.equipo('MAN-EQ-03', 'Agitador magnético', estado_unidad='mantenimiento')
        cls.plan = PlanMantenimientoEquipo.objects.create(
            equipo=cls.balanza, nombre='Calibración anual', tipo='calibracion', frecuencia_dias=365,
            fecha_inicio=date(2026, 1, 10), proxima_ejecucion=date(2027, 1, 10), ejecutor='externo',
            proveedor='Metrología Andina', responsable=cls.tecnico)

    def ordenes_y_fallas(self):
        """Una orden del plan sin ejecutar y una falla reparada con su orden correctiva."""
        programada = MantenimientoEquipo.objects.create(
            equipo=self.balanza, plan=self.plan, tipo='calibracion', estado='programado', titulo='Calibración',
            fecha_programada=_al_mediodia(date(2026, 9, 1)))
        falla = IncidenciaEquipo.objects.create(
            equipo=self.agitador, titulo='No enciende', descripcion='El equipo no enciende al conectarlo.',
            tipo='falla', prioridad='alta', detiene_operacion=True, estado='resuelta',
            solucion='Se cambió el fusible.', reportada_por=self.coordinadora)
        IncidenciaEquipo.objects.filter(pk=falla.pk).update(
            fecha_reporte=datetime(2026, 9, 18, 13, tzinfo=zona.utc),
            fecha_resolucion=datetime(2026, 9, 21, 13, tzinfo=zona.utc))
        anterior = IncidenciaEquipo.objects.create(
            equipo=self.horno, titulo='Deriva de temperatura', descripcion='Marca 5 °C de más.', tipo='calibracion',
            reportada_por=self.coordinadora)
        IncidenciaEquipo.objects.filter(pk=anterior.pk).update(fecha_reporte=datetime(2026, 6, 20, 13, tzinfo=zona.utc))
        # Un incidente de seguridad es del anexo de seguridad, no de disponibilidad.
        IncidenciaEquipo.objects.create(equipo=self.agitador, titulo='Quemadura leve', descripcion='Contacto.',
                                        tipo='seguridad', reportada_por=self.coordinadora)
        correctiva = MantenimientoEquipo.objects.create(
            equipo=self.agitador, incidencia=falla, tipo='correctivo', estado='completado', titulo='Cambio de fusible',
            fecha_programada=_al_mediodia(date(2026, 9, 20)), fecha_inicio=_al_mediodia(date(2026, 9, 20)),
            fecha_fin=datetime(2026, 9, 21, 20, tzinfo=zona.utc), ejecutor='externo',
            proveedor='Servicio Técnico Norte', costo=Decimal('120.50'), resultado='Cambio de fusible y cableado.',
            prueba_funcionamiento='Enciende y agita a 600 rpm.', resultado_operativo='apto')
        return programada, falla, anterior, correctiva

    def test_plan_vigente_por_equipo_con_los_criticos_sin_plan(self):
        tabla = self.registros('EQUIPAMIENTO')[0]
        self.assertEqual(tabla.filas, [
            [Par('MAN-EQ-01', 'Balanza analítica'), 'Crítico', 'Calibración anual',
             self.plan.get_tipo_display(), 'Cada 365 días', Par('10/01/2026', '10/01/2027'),
             Par('Externo', 'Metrología Andina'), 'Tomás Técnico'],
        ])
        self.assertEqual(tabla.total, 'Total: 1 plan vigente · equipos con plan: 1 · equipos críticos sin plan: 1')

    def test_mantenimientos_del_periodo_con_su_origen_y_resultado(self):
        programada, falla, _anterior, correctiva = self.ordenes_y_fallas()
        tipos = dict(MantenimientoEquipo.TIPOS)
        tabla = self.registros('EQUIPAMIENTO')[1]
        self.assertEqual(tabla.filas, [
            [programada.codigo, Par('MAN-EQ-01', 'Balanza analítica'),
             Par(tipos['calibracion'], 'Plan: Calibración anual'), '01/09/2026', programada.get_estado_display(),
             'Interno', '—', '—', '—'],
            [correctiva.codigo, Par('MAN-EQ-03', 'Agitador magnético'),
             Par(tipos['correctivo'], 'Incidencia del 18/09/2026'),
             Par('20/09/2026', 'real 20/09/2026–21/09/2026'), correctiva.get_estado_display(),
             Par('Externo · Servicio Técnico Norte', 'USD 120,50'),
             Par('Cambio de fusible y cableado.', 'Prueba: Enciende y agita a 600 rpm.'), 'Apto', '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 órdenes · completadas: 1 · preventivas: 0 · correctivas: 1 · de otro '
                                      'tipo: 1 · costo total: USD 120,50')

    def test_cumplimiento_en_equipos_criticos_al_corte(self):
        self.ordenes_y_fallas()
        contexto = self.contexto('EQUIPAMIENTO')
        tabla = constructor_de('EQUIPAMIENTO')(contexto)[2]
        self.assertEqual(tabla.filas, [
            [Par('MAN-EQ-01', 'Balanza analítica'), '1', '0', '1', 'Atrasado'],
            [Par('MAN-EQ-02', 'Horno de secado'), '0', '0', '0', 'Sin plan'],
        ])
        self.assertEqual(tabla.suma, ['Total', '1', '0', '1', f'Programa anual 2026, al {fecha(contexto.corte)}'])

    def test_disponibilidad_sin_los_incidentes_de_seguridad(self):
        _programada, _falla, _anterior, correctiva = self.ordenes_y_fallas()
        tipos, prioridades = dict(IncidenciaEquipo.TIPOS), dict(IncidenciaEquipo.PRIORIDADES)
        tabla = self.registros('EQUIPAMIENTO')[3]
        self.assertEqual(tabla.filas, [
            # La anterior al período sigue abierta: también resta disponibilidad.
            [Par('20/06/2026', 'Carla Coordinadora'), Par('MAN-EQ-02', 'Horno de secado'),
             Par(tipos['calibracion'], prioridades['media']), Par('Deriva de temperatura', 'Marca 5 °C de más.'), 'No',
             '—', '—', dict(IncidenciaEquipo.ESTADOS)['abierta']],
            [Par('18/09/2026', 'Carla Coordinadora'), Par('MAN-EQ-03', 'Agitador magnético'),
             Par(tipos['falla'], prioridades['alta']), Par('No enciende', 'El equipo no enciende al conectarlo.'), 'Sí',
             '3', Par('Se cambió el fusible.', correctiva.codigo), dict(IncidenciaEquipo.ESTADOS)['resuelta']],
        ])
        self.assertEqual(tabla.total, 'Total: 2 incidencias · detuvieron la operación: 1 · días fuera de servicio: 3 · '
                                      'abiertas desde antes del período: 1')

    def test_pruebas_funcionales_sin_las_anuladas(self):
        detalle = {'equipo_id': self.balanza.pk, 'procedimiento': 'Pesaje de masas patrón de 1 g a 200 g.',
                   'criterio': 'Error menor a 0,1 mg.', 'resultado_funcional': 'operativo',
                   'hallazgos_funcionales': 'Sin hallazgos.'}
        self.evidencia('FUNCIONALIDAD', 'FUN-01', date(2026, 9, 15), detalle=detalle, estado='validado')
        self.evidencia('FUNCIONALIDAD', 'FUN-02', date(2026, 9, 16), estado='anulado',
                       detalle=detalle | {'resultado_funcional': 'no_operativo'})
        tabla = self.registros('EQUIPAMIENTO')[4]
        self.assertEqual(tabla.filas, [
            ['15/09/2026', Par('MAN-EQ-01', 'Balanza analítica'), 'Pesaje de masas patrón de 1 g a 200 g.',
             'Error menor a 0,1 mg.', 'Operativo', 'Sin hallazgos.', 'Tomás Técnico',
             Par(Enlace('Abrir', 'https://example.org/fun-01'), 'Evidencia verificada')],
        ])
        self.assertEqual(tabla.total, 'Total: 1 prueba · equipos probados: 1 de 3 activos · operativos: 1 · con '
                                      'observaciones: 0 · no operativos: 0')

    def test_estado_de_los_equipos_al_corte(self):
        tabla = self.registros('EQUIPAMIENTO')[5]
        self.assertEqual(tabla.filas, [
            ['Disponible', '2', '2'], ['En uso', '0', '0'], ['En mantenimiento', '1', '0'], ['Dañado', '0', '0'],
            ['Prestado', '0', '0'], ['No disponible', '0', '0'], ['No localizado', '0', '0'],
        ])
        self.assertEqual(tabla.suma, ['Total', '3', '2'])

    def test_infraestructura_programada_con_su_ejecucion_y_sin_lo_anulado(self):
        taller = EspacioReservable.objects.create(unidad=self.unidad, codigo='MAN-TALLER', nombre='Taller de secado')
        plan = self.evidencia('PLAN-INFRA', 'INFRA-PLAN-01', date(2026, 7, 1), estado='validado', detalle={
            'espacio_id': taller.pk, 'intervencion': 'Revisión del sistema de extracción',
            'fecha_programada': '2026-08-01', 'frecuencia_dias': 90})
        self.evidencia('EJECUCION-INFRA', 'INFRA-EJE-01', date(2026, 8, 3), estado='validado', detalle={
            'plan_id': plan.pk, 'fecha_programada': '2026-08-01', 'fecha_inicio': '2026-08-02',
            'fecha_fin': '2026-08-03', 'resultado': 'Filtros cambiados.'})
        self.evidencia('PLAN-INFRA', 'INFRA-PLAN-02', date(2026, 7, 2), estado='anulado', detalle={
            'espacio_id': taller.pk, 'intervencion': 'Plan rectificado', 'fecha_programada': '2026-08-15',
            'frecuencia_dias': 0})
        contexto = self.contexto('EQUIPAMIENTO')
        self.assertGreater(contexto.corte, date(2026, 10, 30))
        tabla = constructor_de('EQUIPAMIENTO')(contexto)[6]
        self.assertEqual(tabla.filas, [
            [Par('MAN-TALLER', 'Taller de secado'), Par('Revisión del sistema de extracción', 'Filtros cambiados.'),
             Par('01/08/2026', 'ejecutada 02/08/2026–03/08/2026'), 'Tomás Técnico', 'Ejecutada',
             Par(Enlace('Abrir', 'https://example.org/infra-eje-01'), 'Evidencia verificada')],
            # La segunda fecha del plan ya pasó y no tiene ejecución: queda pendiente.
            [Par('MAN-TALLER', 'Taller de secado'), 'Revisión del sistema de extracción', '30/10/2026',
             'Tomás Técnico', 'Pendiente',
             Par(Enlace('Abrir', 'https://example.org/infra-plan-01'), 'Evidencia verificada')],
        ])
        self.assertEqual(tabla.total, 'Total: 2 intervenciones · ejecutadas: 1 · pendientes: 1 · programadas: 0')

    def test_la_infraestructura_del_centro_y_del_observatorio_nombra_su_alcance(self):
        centro = self.registros('EQUIPAMIENTO', 'centro_experimental')[6]
        self.assertIn('(riego, invernaderos, establos y cercas)', centro.vacio)
        observatorio = self.registros('EQUIPAMIENTO', 'observatorios')[6]
        self.assertIn('(red, servidores y respaldos de la sala)', observatorio.vacio)


class InventarioTests(_ConUnidades):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.balanza = cls.equipo(
            'INV-EQ-01', 'Balanza analítica', marca='Ohaus', modelo='PX224', numero_serie='SN-4455',
            codigo_bien='37881242', tipo_bien='BLD', clase_bien='Equipo de laboratorio', custodio='María Custodia',
            ubicacion_especifica='Mesón 2', criticidad='critico', origen_adquisicion='compra_publica',
            fecha_adquisicion=date(2024, 3, 15), valor_contable=Decimal('1500.00'), existencia_verificada=True,
            existencia_verificada_en=_al_mediodia(date(2026, 8, 20)), existencia_verificada_por=cls.coordinadora,
            garantia_hasta=date(2027, 3, 15))
        cls.reactivo = Consumible.objects.create(
            unidad=cls.unidad, codigo='INV-REA-01', nombre='Etanol absoluto', clasificacion='reactivo',
            unidad_medida='l', presentacion='Frasco 1 L', marca='Merck', stock_total=Decimal('2.5'))
        LoteConsumible.objects.create(consumible=cls.reactivo, codigo='L-2026-01', cantidad_inicial=3,
                                      cantidad_actual=Decimal('2.5'), fecha_vencimiento=date(2026, 8, 1),
                                      bodega='Bodega A', estanteria='E1', posicion='P3')
        cls.filamento = Consumible.objects.create(
            unidad=cls.unidad, codigo='INV-INS-01', nombre='Filamento PLA', clasificacion='insumo', unidad_medida='kg',
            stock_total=4, minimo=5, stock_objetivo=10, ubicacion='Estante 3', origen_abastecimiento='compra_publica')
        cls.lote_pla = LoteConsumible.objects.create(consumible=cls.filamento, codigo='LOTE-PLA-1', cantidad_inicial=4,
                                                     cantidad_actual=4, bodega='Bodega B')

    def test_un_equipo_aparece_con_su_serie_y_su_custodio(self):
        self.balanza.refresh_from_db()
        tabla = self.tabla('INVENTARIO-CORTE', 'Equipos')
        self.assertEqual(tabla.filas, [
            [Par('INV-EQ-01', 'Balanza analítica'), Par('Ohaus', 'PX224'), 'SN-4455',
             Par(self.balanza.codigo_bien, 'BLD · Equipo de laboratorio'), Par('María Custodia', 'Mesón 2'),
             Par('Disponible', 'Crítico'), Par('Compra pública · 15/03/2024', 'USD 1.500'),
             Par('20/08/2026 · Carla Coordinadora', 'garantía hasta 15/03/2027'), '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 1 equipo activo · verificados: 1 · críticos: 1 · valor contable total: '
                                      'USD 1.500')

    def test_un_equipo_dado_de_baja_va_en_bajas_y_no_en_equipos(self):
        baja = self.equipo('INV-EQ-09', 'Centrífuga', fecha_baja=date(2026, 9, 5), motivo_baja='obsolescencia',
                           observacion_baja='Acta de baja 12-2026.')
        equipos = self.tabla('INVENTARIO-CORTE', 'Equipos')
        self.assertEqual([fila[0] for fila in equipos.filas], [Par('INV-EQ-01', 'Balanza analítica')])
        self.assertTrue(equipos.total.endswith('inactivos o dados de baja, que no se listan: 1'))
        bajas = self.tabla('INVENTARIO-CORTE', 'Bajas y traspasos del período')
        self.assertEqual(bajas.filas, [
            [Par('INV-EQ-09', 'Centrífuga'), 'Baja', '05/09/2026', baja.get_motivo_baja_display(), '—',
             'Acta de baja 12-2026.'],
        ])

    def test_un_traspaso_ejecutado_consta_en_la_unidad_que_entrega_y_en_la_que_recibe(self):
        from apps.recursos.models.redistribucion import EquipoEnTraspaso, TraspasoEquipo
        planta = self.unidades['plantas_piloto']
        microscopio = self.equipo('PP-EQ-05', 'Microscopio', unidad=planta)
        ejecutado = TraspasoEquipo.objects.create(unidad_origen=self.unidad, unidad_destino=planta, motivo='necesidad',
                                                  justificacion='Lo necesita la planta.', estado='ejecutado',
                                                  fecha_ejecucion=_al_mediodia(date(2026, 9, 25)))
        EquipoEnTraspaso.objects.create(traspaso=ejecutado, equipo=microscopio, codigo_anterior='INV-EQ-05',
                                        codigo_nuevo='PP-EQ-05')
        anulado = TraspasoEquipo.objects.create(unidad_origen=self.unidad, unidad_destino=planta, estado='anulado',
                                                justificacion='Se anuló.')
        EquipoEnTraspaso.objects.create(traspaso=anulado, equipo=self.balanza, codigo_anterior='INV-EQ-01')
        motivo = ejecutado.get_motivo_display()
        equipo = Par('INV-EQ-05', 'Microscopio · ahora PP-EQ-05')
        entrega = self.tabla('INVENTARIO-CORTE', 'Bajas y traspasos del período')
        self.assertEqual(entrega.filas, [
            [equipo, Par('Traspaso entregado', ejecutado.get_estado_display()), '25/09/2026', motivo,
             'Unidad de recursos plantas_piloto', ejecutado.codigo],
        ])
        recibe = self.tabla('INVENTARIO-CORTE', 'Bajas y traspasos del período', 'plantas_piloto')
        self.assertEqual(recibe.filas, [
            [equipo, Par('Traspaso recibido', ejecutado.get_estado_display()), '25/09/2026', motivo,
             Par('Unidad de recursos plantas_piloto', 'recibido de Unidad de recursos laboratorios'), ejecutado.codigo],
        ])
        self.assertEqual(entrega.total, 'Total: 1 movimiento · bajas: 0 · traspasos: 1')

    def test_el_acta_de_revision_fisica_sin_las_anuladas(self):
        self.evidencia('INVENTARIO', 'ACTA-INV-01', date(2026, 8, 25), alcance=['equipos', 'software', 'espacios'],
                       descripcion='Sin diferencias.', estado='validado')
        self.evidencia('INVENTARIO', 'ACTA-INV-02', date(2026, 8, 26), estado='anulado')
        tabla = self.tabla('INVENTARIO-CORTE', 'Acta de revisión física del período')
        self.assertEqual(tabla.filas, [
            ['ACTA-INV-01', '25/08/2026', 'Equipos, software, espacios', 'Tomás Técnico', 'Sin diferencias.',
             Par(Enlace('Abrir', 'https://example.org/acta-inv-01'), 'Evidencia verificada')],
        ])
        self.assertEqual(tabla.total, 'Total: 1 acta · verificadas: 1')

    def test_un_reactivo_con_lote_y_vencimiento_va_en_reactivos_y_no_en_insumos(self):
        reactivos = self.tabla('INVENTARIO-CORTE', 'Reactivos')
        self.assertEqual(reactivos.filas, [
            [Par('INV-REA-01', 'Etanol absoluto'), Par('Frasco 1 L', 'Merck'), 'L-2026-01', '2,5 l',
             Par('01/08/2026', 'vencido'), 'Bodega A · E1 · P3', 'En bodega', '—'],
        ])
        self.assertEqual(reactivos.total, 'Total: 1 reactivo · lotes: 1 · vencidos con saldo: 1 · vencen en 90 días: 0')
        insumos = self.tabla('INVENTARIO-CORTE', 'Insumos y materiales')
        self.assertEqual(insumos.filas, [
            [Par('INV-INS-01', 'Filamento PLA'), 'Insumo', '4 kg', Par('5 kg', '10 kg'), '1', '—', 'Estante 3',
             'Compra pública'],
        ])
        self.assertEqual(insumos.total, 'Total: 1 artículo · bajo el mínimo: 1 · sin lotes localizables: 0')

    def test_movimientos_del_periodo_con_su_referencia(self):
        sesion = self.reserva(date(2026, 9, 10), estado='completada')
        EntradaInventario.objects.create(consumible=self.filamento, tipo='ingreso', motivo='recepcion', cantidad=2,
                                         fecha=_al_mediodia(date(2026, 9, 2)), usuario=self.coordinadora,
                                         referencia='Factura 001')
        EntradaInventario.objects.create(consumible=self.filamento, tipo='salida', motivo='consumo_practica',
                                         cantidad=1, lote_inventario=self.lote_pla, reserva=sesion,
                                         fecha=_al_mediodia(date(2026, 9, 10)), usuario=self.coordinadora)
        EntradaInventario.objects.create(consumible=self.filamento, tipo='ingreso', motivo='recepcion', cantidad=1,
                                         fecha=_al_mediodia(date(2026, 5, 2)))  # De otro período.
        motivos = dict(EntradaInventario.MOTIVO_CHOICES)
        tabla = self.tabla('INVENTARIO-CORTE', 'Movimientos del período')
        self.assertEqual(tabla.filas, [
            ['02/09/2026', Par('INV-INS-01', 'Filamento PLA'), Par('Ingreso', motivos['recepcion']), '2 kg', '6 kg',
             '—', 'Factura 001', 'Carla Coordinadora'],
            ['10/09/2026', Par('INV-INS-01', 'Filamento PLA'), Par('Salida', motivos['consumo_practica']), '1 kg',
             '5 kg', 'LOTE-PLA-1', sesion.codigo_reserva, 'Carla Coordinadora'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 movimientos · ingresos: 1 · salidas: 1 · por motivo: '
                                      f'{motivos["recepcion"].lower()} 1, {motivos["consumo_practica"].lower()} 1')

    def test_en_la_planta_los_lotes_del_cliente_se_marcan_y_los_consumos_de_produccion_van_aparte(self):
        planta = self.unidades['plantas_piloto']
        leche = Consumible.objects.create(unidad=planta, codigo='PP-LECHE', nombre='Leche cruda',
                                          clasificacion='insumo', unidad_medida='l', stock_total=100)
        LoteConsumible.objects.create(consumible=leche, codigo='LECHE-PROPIA', cantidad_inicial=60, cantidad_actual=60,
                                      bodega='Cámara 1')
        lote_cliente = LoteConsumible.objects.create(consumible=leche, codigo='LECHE-CLIENTE', cantidad_inicial=40,
                                                     cantidad_actual=40, bodega='Cámara 1', material_cliente=True)
        EntradaInventario.objects.create(consumible=leche, tipo='salida', motivo='consumo_produccion', cantidad=10,
                                         lote_inventario=lote_cliente, referencia='OP-PRUEBA',
                                         fecha=_al_mediodia(date(2026, 9, 3)))
        insumos = self.tabla('INVENTARIO-CORTE', 'Insumos y materiales', 'plantas_piloto')
        self.assertEqual(insumos.filas[0][4], Par('2', 'del cliente: 1'))
        movimientos = self.tabla('INVENTARIO-CORTE', 'Movimientos del período', 'plantas_piloto')
        self.assertEqual(movimientos.filas, [])
        self.assertIn('Consumos de producción, que se presentan en el anexo de producción: 1', movimientos.vacio)

    def test_en_el_centro_experimental_la_34_reune_agroquimicos_y_medicamentos_veterinarios(self):
        centro = self.unidades['centro_experimental']
        Consumible.objects.create(unidad=centro, codigo='CE-AGRO-01', nombre='Fungicida cúprico',
                                  clasificacion='agroquimico', unidad_medida='kg', stock_total=3,
                                  presentacion='Saco 1 kg', ubicacion='Bodega de agroquímicos')
        Consumible.objects.create(unidad=centro, codigo='CE-VET-01', nombre='Vacuna triple',
                                  clasificacion='veterinario', unidad_medida='unidad', stock_total=20,
                                  presentacion='Frasco de 50 dosis')
        Consumible.objects.create(unidad=centro, codigo='CE-SEM-01', nombre='Semilla de papa', clasificacion='insumo',
                                  unidad_medida='kg', stock_total=200)
        reactivos = self.tabla('INVENTARIO-CORTE', REACTIVOS_DEL_CENTRO, 'centro_experimental')
        detalle = Consumible.CLASIFICACION_DETALLE
        self.assertEqual(reactivos.filas, [
            Grupo(detalle['agroquimico'][0]),
            [Par('CE-AGRO-01', 'Fungicida cúprico'), 'Saco 1 kg', 'Sin lote registrado', '3 kg', '—',
             'Bodega de agroquímicos', '—', '—'],
            Grupo(detalle['veterinario'][0]),
            [Par('CE-VET-01', 'Vacuna triple'), 'Frasco de 50 dosis', 'Sin lote registrado', '20 unidad', '—', '—', '—',
             '—'],
        ])
        self.assertTrue(reactivos.total.startswith('Total: 2 artículos · lotes: 0'))
        insumos = self.tabla('INVENTARIO-CORTE', 'Insumos y materiales', 'centro_experimental')
        self.assertEqual([fila[0] for fila in insumos.filas], [Par('CE-SEM-01', 'Semilla de papa')])

    def test_el_observatorio_lleva_software_y_espacios_en_lugar_de_reactivos(self):
        observatorio = self.unidades['observatorios']
        computadores = [self.equipo(f'OBS-PC-0{n}', f'Computador {n}', unidad=observatorio) for n in (1, 2, 3)]
        programa = SoftwareDisponible.objects.create(unidad=observatorio, nombre='R', codigo='OBS-SW-01', version='4.4',
                                                     tipo_recurso='software', tipo_acceso='instalacion',
                                                     licencias_totales=5, licencias_disponibles=3)
        programa.equipos_instalados.add(*computadores)
        SoftwareDisponible.objects.create(unidad=observatorio, nombre='Retirado', codigo='OBS-SW-02', activo=False)
        EspacioReservable.objects.create(unidad=observatorio, codigo='OBS-SALA', nombre='Sala de análisis', tipo='sala',
                                         capacidad=12, ubicacion='Bloque B')
        registros = self.registros('INVENTARIO-CORTE', 'observatorios')
        self.assertEqual([r.titulo for r in registros], [t for t, _c in INVENTARIO_DEL_OBSERVATORIO])
        self.assertEqual(len(registros[1].filas), 3)
        self.assertEqual(registros[3].filas, [
            [Par('OBS-SW-01', 'R'), '4.4', Par('Software', 'Instalado'), Par('5', 'disponibles: 3'),
             Par('3 equipos', 'OBS-PC-01 a 03')],
        ])
        self.assertEqual(registros[4].filas, [[Par('OBS-SALA', 'Sala de análisis'), 'Sala', '12 personas', 'Bloque B']])


class FichasTecnicasTests(_ConUnidades):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fresadora = cls.equipo('FIC-EQ-01', 'Fresadora CNC')
        cls.cortadora = cls.equipo('FIC-EQ-02', 'Cortadora láser')
        cls.taller = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='FIC-TALLER', nombre='Taller de prototipos', tipo='taller',
            ubicacion='Planta baja', capacidad=10, superficie_m2=Decimal('42.5'),
            mobiliario_incluido='Mesas de trabajo', caracteristicas='Extracción de gases', responsable=cls.responsable,
            reservable=True, visitable=False)
        cls.taller.equipos_asociados.add(cls.fresadora, cls.cortadora)
        cls.simulador = SoftwareDisponible.objects.create(
            unidad=cls.unidad, nombre='Simulador de circuitos', codigo='FIC-SIM-01', version='2026',
            tipo_recurso='simulador', tipo_acceso='remoto', uso_en_equipo='opcional', licencias_totales=10,
            licencias_disponibles=10)

    def test_la_ficha_de_la_unidad_reune_capacidad_horario_y_carreras(self):
        CapacidadOperativaUnidad.objects.create(unidad=self.unidad, vigente_desde=date(2026, 1, 1), aforo_seguridad=20,
                                                puestos_mobiliario=16, puestos_equipados=12, capacidad_personal=2)
        # La jornada que la unidad recibe al crearse se reemplaza por la de mañana, de lunes a viernes.
        HorarioOperacionUnidad.objects.filter(unidad=self.unidad).delete()
        for dia in range(5):
            HorarioOperacionUnidad.objects.create(unidad=self.unidad, dia_semana=dia, hora_inicio=time(8),
                                                  hora_fin=time(12))
        # El sábado tiene una jornada desactivada: no se presenta.
        HorarioOperacionUnidad.objects.create(unidad=self.unidad, dia_semana=5, hora_inicio=time(8), hora_fin=time(12),
                                              activo=False)
        for codigo, carrera in (('FIC-101', 'Mecatrónica'), ('FIC-102', 'Computación'), ('FIC-103', 'Computación')):
            Asignatura.objects.create(unidad=self.unidad, codigo=codigo, nombre='Asignatura ' + codigo, carrera=carrera)
        datos = dict(self.registros('FICHAS-TECNICAS')[0].filas)
        self.assertEqual(datos['Nombre y tipo'], 'Unidad de recursos laboratorios · Laboratorio')
        self.assertEqual(datos['Responsable'],
                         'Carla Coordinadora (responsable de la unidad); Tomás Técnico (Responsable técnico)')
        self.assertEqual(datos['Horario de operación'], 'Lunes a viernes 08:00–12:00')
        self.assertEqual(datos['Aforo de seguridad'], '20 personas')
        self.assertEqual(datos['Puestos con mobiliario / equipados'], '16 / 12')
        self.assertEqual(datos['Personal'], 'Atiende a 2 personas a la vez')
        self.assertEqual(datos['Carreras que atiende'], 'Computación; Mecatrónica')

    def test_un_espacio_con_su_superficie_sus_equipos_y_su_uso(self):
        sesion = self.reserva(date(2026, 9, 10), estado='confirmada')
        sesion.espacios_solicitados.add(self.taller)
        PlanificacionPractica.objects.create(unidad=self.unidad, reserva=sesion, fecha=sesion.fecha,
                                             hora_inicio=time(8), hora_fin=time(10), asignatura='Prototipado',
                                             creado_por=self.coordinadora)
        cancelada = self.reserva(date(2026, 9, 17), estado='cancelada')
        cancelada.espacios_solicitados.add(self.taller)
        EspacioReservable.objects.create(unidad=self.unidad, codigo='FIC-VIEJO', nombre='Bodega antigua',
                                         activo=False)
        tabla = self.tabla('FICHAS-TECNICAS', 'Espacios y talleres')
        self.assertEqual(tabla.filas, [
            [Par('FIC-TALLER', 'Taller de prototipos'), 'Taller', 'Planta baja', Par('10 personas', '42,5 m²'),
             'Mesas de trabajo · Extracción de gases', Par('2 equipos', 'FIC-EQ-01/02'), 'Tomás Técnico',
             Par('Sí', 'visitable: no'), Par('1 práctica', '1 sesión')],
        ])
        self.assertEqual(tabla.total, 'Total: 1 espacio · reservables: 1 · visitables: 0')

    def test_un_simulador_usado_en_el_periodo_y_sin_el_software_retirado(self):
        sesion = self.reserva(date(2026, 9, 10), estado='confirmada')
        sesion.software_solicitado.add(self.simulador)
        SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Programa retirado', codigo='FIC-SW-VIEJO',
                                          activo=False)
        tabla = self.tabla('FICHAS-TECNICAS', 'Software y simuladores')
        self.assertEqual(tabla.filas, [
            [Par('FIC-SIM-01', 'Simulador de circuitos'), '2026', 'Simulador', 'Remoto', Par('10', 'disponibles: 10'),
             '—', 'Opcional', Par('0 prácticas', '1 sesión')],
        ])
        self.assertEqual(tabla.total, 'Total: 1 programa · software: 0 · licencias: 0 · simuladores: 1')

    def test_en_el_centro_experimental_el_espacio_lleva_su_eje_y_su_ciclo_en_curso(self):
        from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo
        centro = self.unidades['centro_experimental']
        parcela = EspacioReservable.objects.create(unidad=centro, codigo='CE-P07', nombre='Parcela 7', tipo='parcela')
        eje = EjeProductivo.objects.create(unidad=centro, codigo='cultivos-andinos', titulo='Cultivos andinos',
                                           resumen='Papa y quinua.', que_produce='Semilla y tubérculo.')
        eje.espacios.add(parcela)
        CicloProductivo.objects.create(eje=eje, nombre='Papa Superchola 2026-B', rubro='Papa', lugar=parcela,
                                       inicio=date(2026, 8, 1), fin_previsto=date(2027, 1, 30), estado='en_curso',
                                       meta=Decimal('5000'))
        fila = self.tabla('FICHAS-TECNICAS', 'Espacios y talleres', 'centro_experimental').filas[0]
        self.assertEqual(fila[0], Par('CE-P07', 'Parcela 7'))
        self.assertEqual(fila[4], Par('Eje: Cultivos andinos', 'Ciclo en curso: Papa Superchola 2026-B'))
