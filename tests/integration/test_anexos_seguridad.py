"""Contenido de los anexos de reportes de seguridad y de gestión de desechos.

Fija lo acordado en docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.8 y 4.9:
- las tablas de cada anexo, en el orden y con las columnas de la especificación;
- los llevan el laboratorio, la planta piloto y el centro experimental (no el observatorio);
- una inspección se lee contra las condiciones de su tipo de unidad: siete en el laboratorio, once
  en la planta piloto y diez en el centro experimental;
- un incidente de seguridad va en la 8.6 y no en la tabla de fallas técnicas del anexo de equipamiento;
- lo que sigue almacenado al corte se presenta aunque se haya generado antes del período;
- lo anulado y lo de sesiones canceladas no se presenta.
"""
from datetime import date, datetime, time
from datetime import timezone as zona
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.resultados_gestion import CONDICIONES_COMUNES, CONDICIONES_PROPIAS
from apps.documentos.presentation.anexos_evidencia import Enlace, Par, constructor_de, contexto_del_anexo, fecha
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso

CON_SEGURIDAD = ('laboratorios', 'plantas_piloto', 'centro_experimental')
# Las tablas de cada anexo y sus columnas, tal como las fija la especificación.
TABLAS = {
    'INDUCCION-SEGURIDAD': [
        ('Requisitos de acceso',
         ('Código / requisito', 'Tipo', 'Aplica a', 'Cuándo se exige', 'Obligatorio', 'Vigencia',
          'Protección por persona')),
        ('Inducciones y habilitaciones del período',
         ('Fecha', 'Persona', 'Requisito', 'Vence', 'Origen', 'Otorgada por', 'Documento', 'Estado al corte')),
        ('Inspecciones de condiciones',
         ('Mes / fecha', 'Área', 'Condiciones revisadas', 'Hallazgos', 'Estado', 'Acción correctiva / plazo',
          'Estado de la acción', 'Responsable', 'Respaldo')),
        ('Cobertura mensual de inspecciones',
         ('Mes', 'Exigible', 'Inspecciones registradas', 'Verificadas', 'Situación')),
        ('Control de ingresos',
         ('Fecha / hora', 'Sesión', 'Persona / categoría', 'Ingresó', 'Protección verificada',
          'Restricciones verificadas', 'Habilitaciones vigentes', 'Pendientes')),
        ('Incidentes de seguridad',
         ('Fecha', 'Lugar o equipo', 'Descripción', 'Prioridad', 'Práctica o sesión', 'Acción / solución', 'Estado',
          'Reportado por')),
    ],
    'DESECHOS': [
        ('Generación y almacenamiento',
         ('Fecha', 'Desecho / clave', 'Clase / estado físico', 'Origen', 'Cantidad', 'Envase / etiquetado',
          'Almacenamiento temporal', 'Etapa', 'Responsable')),
        ('Entregas al gestor autorizado',
         ('Fecha de entrega', 'Desechos', 'Cantidad', 'Gestor / licencia', 'Manifiesto', 'Documento')),
        ('Almacenado al corte',
         ('Desecho', 'Cantidad pendiente de entrega', 'Desde', 'Días almacenado', 'Lugar')),
    ],
}
COMUNES = [clave for clave, _etiqueta in CONDICIONES_COMUNES]


def _al_mediodia(dia):
    """Un instante del día dado: las 10:00 en Ecuador."""
    return datetime(dia.year, dia.month, dia.day, 15, tzinfo=zona.utc)


def _informe(unidad):
    documentos = construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))
    return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')


def _anexo(unidad, codigo):
    return next(a for a in anexos_del(_informe(unidad), incluir_no_aplica=True) if a.exigido.codigo == codigo)


class _ConUnidades(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user('coordinadora-anexos-seguridad', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user('tecnico-anexos-seguridad', first_name='Tomás', last_name='Técnico')
        cls.estudiante = usuarios.create_user('estudiante-anexos-seguridad', first_name='Ana', last_name='Andrade')
        cls.unidades = {tipo: Unidad.objects.create(
            nombre=f'Unidad de seguridad {tipo}', slug=f'anexos-seguridad-{tipo}', dependencia=tipo,
            fecha_inicio=date(2025, 1, 1), administrador=cls.coordinadora)
            for tipo in (*CON_SEGURIDAD, 'observatorios')}
        cls.unidad = cls.unidades['laboratorios']
        cls.cortadora = UnidadEquipo.objects.create(
            codigo_unidad='SEG-EQ-01', laboratorio=cls.unidad,
            equipo=EquiposServicios.objects.create(nombre='Cortadora láser', codigo='SEG-MODELO-01'))

    def contexto(self, codigo, tipo='laboratorios'):
        anexo = _anexo(self.unidades[tipo], codigo)
        inicio, fin = tramo_del_documento(anexo)
        self.assertEqual((inicio, fin), (date(2026, 7, 1), date(2026, 12, 31)))
        return contexto_del_anexo(anexo, inicio, fin)

    def registros(self, codigo, tipo='laboratorios'):
        return constructor_de(codigo)(self.contexto(codigo, tipo))

    def reserva(self, dia, **datos):
        reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.estudiante, fecha=dia,
                                         hora_inicio=time(8), hora_fin=time(10), **datos)
        reserva.refresh_from_db()
        return reserva

    def inspeccion(self, codigo, dia, unidad=None, **detalle):
        base = dict(area='Área de corte', condiciones_revisadas=COMUNES, sin_hallazgos=True, hallazgos='',
                    estado_condiciones='seguro', accion_correctiva='', estado_accion='no_requiere', plazo_accion='')
        return EvidenciaGestionUnidad.objects.create(
            unidad=unidad or self.unidad, tipo='INSPECCION', codigo=codigo, fecha=dia, titulo='Inspección ' + codigo,
            descripcion='Inspección mensual.', responsable=self.tecnico, creado_por=self.coordinadora,
            enlace=f'https://example.org/{codigo.lower()}', estado='validado', detalle=base | detalle)


class TablasDeLaEspecificacionTests(_ConUnidades):
    def test_cada_anexo_lleva_las_tablas_y_columnas_de_la_especificacion(self):
        for tipo in CON_SEGURIDAD:
            for codigo, tablas in TABLAS.items():
                with self.subTest(tipo=tipo, anexo=codigo):
                    registros = self.registros(codigo, tipo)
                    self.assertEqual([(r.titulo, tuple(r.cabecera)) for r in registros], tablas)
                    for registro in registros:
                        self.assertEqual(registro.filas, [], registro.titulo)
                        self.assertTrue(registro.vacio, registro.titulo)

    def test_el_observatorio_no_lleva_seguridad_ni_desechos(self):
        codigos = {a.exigido.codigo for a in anexos_del(_informe(self.unidades['observatorios']),
                                                         incluir_no_aplica=True)}
        self.assertFalse(codigos & set(TABLAS))


class ReportesDeSeguridadTests(_ConUnidades):
    def test_requisitos_de_acceso_activos_con_su_proteccion_por_persona(self):
        guantes = Consumible.objects.create(unidad=self.unidad, codigo='SEG-GUANTES', nombre='Guantes de nitrilo',
                                            clasificacion='proteccion', unidad_medida='par', stock_total=50)
        induccion = RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND-01', nombre='Inducción general',
                                                   tipo='induccion', aplica_a=['estudiante', 'docente'],
                                                   momento='reservar', vigencia_dias=365, orden=1)
        proteccion = RequisitoAcceso.objects.create(unidad=self.unidad, codigo='EPP-01', nombre='Bata y guantes',
                                                    tipo='proteccion', momento='ingresar', consumible=guantes,
                                                    cantidad_por_persona=Decimal('1'), orden=2)
        RequisitoAcceso.objects.create(unidad=self.unidad, codigo='RET-01', nombre='Retirado', tipo='documento',
                                       activo=False)
        tabla = self.registros('INDUCCION-SEGURIDAD')[0]
        self.assertEqual(tabla.filas, [
            [Par('IND-01', 'Inducción general'), 'Inducción', 'Estudiantes, Docentes e investigadores',
             induccion.get_momento_display(), 'Sí', '365 días', '—'],
            [Par('EPP-01', 'Bata y guantes'), 'Protección', 'Todas las personas', proteccion.get_momento_display(),
             'Sí', 'Cada ingreso', Par('SEG-GUANTES', '1 par por persona')],
        ])
        self.assertEqual(tabla.total, 'Total: 2 requisitos · obligatorios: 2')

    def test_habilitaciones_del_periodo_con_su_estado_al_corte(self):
        requisito = RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND-01', nombre='Inducción general',
                                                   tipo='induccion', vigencia_dias=365)
        sesion = self.reserva(date(2026, 7, 5), estado='completada')
        HabilitacionAcceso.objects.create(usuario=self.estudiante, requisito=requisito, fecha=date(2026, 7, 5),
                                          origen='sesion', reserva=sesion, otorgada_por=self.tecnico,
                                          documento='https://example.org/certificado-ana')
        HabilitacionAcceso.objects.create(usuario=self.tecnico, requisito=requisito, fecha=date(2026, 7, 10),
                                          vence=date(2026, 8, 9), origen='documento', documento='Certificado 45-2026',
                                          otorgada_por=self.coordinadora)
        HabilitacionAcceso.objects.create(usuario=self.estudiante, requisito=requisito, fecha=date(2026, 8, 1),
                                          activa=False, otorgada_por=self.coordinadora)
        HabilitacionAcceso.objects.create(usuario=self.estudiante, requisito=requisito, fecha=date(2026, 5, 1))
        origenes = dict(HabilitacionAcceso.ORIGENES)
        tabla = self.registros('INDUCCION-SEGURIDAD')[1]
        self.assertEqual(tabla.filas, [
            ['05/07/2026', 'Ana Andrade', 'Inducción general', '05/07/2027',
             Par(origenes['sesion'], sesion.codigo_reserva), 'Tomás Técnico',
             Enlace('Abrir enlace', 'https://example.org/certificado-ana'), 'Vigente'],
            ['10/07/2026', 'Tomás Técnico', 'Inducción general', '09/08/2026', origenes['documento'],
             'Carla Coordinadora', 'Certificado 45-2026', 'Vencida'],
            ['01/08/2026', 'Ana Andrade', 'Inducción general', '01/08/2027', origenes['manual'], 'Carla Coordinadora',
             '—', 'Revocada'],
        ])
        self.assertEqual(tabla.total, 'Total: 3 habilitaciones · personas: 2 · vigentes al corte: 1')

    def test_inspecciones_con_su_seguimiento_y_sin_las_anuladas(self):
        self.inspeccion('INS-09', date(2026, 9, 12), sin_hallazgos=False, hallazgos='Extintor vencido.',
                        estado_condiciones='observado', accion_correctiva='Recargar el extintor.',
                        plazo_accion='2026-09-30', estado_accion='pendiente')
        anulada = self.inspeccion('INS-09-BIS', date(2026, 9, 13))
        EvidenciaGestionUnidad.objects.filter(pk=anulada.pk).update(estado='anulado')
        tabla = self.registros('INDUCCION-SEGURIDAD')[2]
        self.assertEqual(tabla.filas, [
            [Par('Septiembre 2026', '12/09/2026'), 'Área de corte',
             Par('7 de 7', 'infraestructura, equipos, emergencias, protección personal, almacenamiento, orden y '
                           'limpieza, desechos'),
             'Extintor vencido.', 'Observado', Par('Recargar el extintor.', 'plazo 30/09/2026'), 'Pendiente',
             'Tomás Técnico', Par(Enlace('Abrir', 'https://example.org/ins-09'), 'Evidencia verificada')],
        ])
        self.assertEqual(tabla.total,
                         'Total: 1 inspección · verificadas: 1 · con hallazgos: 1 · acciones pendientes: 1')

    def test_cada_tipo_de_unidad_revisa_sus_condiciones_propias(self):
        exigidas = {'laboratorios': 7, 'plantas_piloto': 11, 'centro_experimental': 10}
        for tipo, total in exigidas.items():
            with self.subTest(tipo=tipo):
                propias = [clave for clave, _etiqueta in CONDICIONES_PROPIAS.get(tipo, ())]
                self.inspeccion(f'INS-{tipo}', date(2026, 9, 12), unidad=self.unidades[tipo],
                                condiciones_revisadas=COMUNES + propias[:1])
                celda = self.registros('INDUCCION-SEGURIDAD', tipo)[2].filas[0][2]
                revisadas = 7 + bool(propias)
                self.assertEqual(celda.principal, f'{revisadas} de {total}')
        # La planta piloto anota en palabras su condición propia.
        celda = self.registros('INDUCCION-SEGURIDAD', 'plantas_piloto')[2].filas[0][2]
        self.assertTrue(celda.secundario.endswith('desechos, buenas prácticas de manufactura'))

    def test_la_cobertura_mensual_es_la_que_mide_el_informe(self):
        contexto = self.contexto('INDUCCION-SEGURIDAD')
        contexto.registros['cobertura_inspecciones'] = {'meses': [
            {'mes': '2026-07', 'exigible': True, 'cumple': True, 'revisiones': 1, 'verificadas_reales': 1},
            {'mes': '2026-08', 'exigible': True, 'cumple': False, 'revisiones': 2, 'verificadas_reales': 0},
            {'mes': '2026-09', 'exigible': True, 'cumple': False, 'revisiones': 0, 'verificadas_reales': 0},
            {'mes': '2026-10', 'exigible': False, 'cumple': False, 'revisiones': 0, 'verificadas_reales': 0},
        ]}
        tabla = constructor_de('INDUCCION-SEGURIDAD')(contexto)[3]
        self.assertEqual(tabla.filas, [
            ['Julio 2026', 'Sí', '1', '1', 'Cubierto'],
            ['Agosto 2026', 'Sí', '2', '0', 'Sin inspección verificada'],
            ['Septiembre 2026', 'Sí', '0', '0', 'Sin inspección'],
            ['Octubre 2026', 'Aún en plazo', '0', '0', 'Sin inspección'],
        ])
        self.assertEqual(tabla.total, 'Total: 4 meses · exigibles al corte: 3 · cubiertos: 1')

    def test_control_de_ingresos_sin_las_sesiones_canceladas(self):
        sesion = self.reserva(date(2026, 9, 10), estado='confirmada')
        RegistroIngreso.objects.create(reserva=sesion, nombre='Ana Andrade', categoria='estudiante',
                                       hora_ingreso=time(8, 5), hora_salida=time(9, 55), proteccion_verificada=True,
                                       restricciones_verificadas=True, habilitaciones_vigentes=True)
        RegistroIngreso.objects.create(reserva=sesion, nombre='Pedro Externo', categoria='externo', ingresa=False,
                                       motivo='Sin inducción vigente.', pendientes=['Inducción general'])
        cancelada = self.reserva(date(2026, 9, 17), estado='cancelada')
        RegistroIngreso.objects.create(reserva=cancelada, nombre='Sesión cancelada', categoria='estudiante')
        tabla = self.registros('INDUCCION-SEGURIDAD')[4]
        self.assertEqual(tabla.filas, [
            [Par('10/09/2026', 'ingreso 08:05 · salida 09:55'), sesion.codigo_reserva, Par('Ana Andrade', 'Estudiante'),
             'Sí', 'Sí', 'Sí', 'Sí', '—'],
            ['10/09/2026', sesion.codigo_reserva, Par('Pedro Externo', 'Persona externa'),
             Par('No', 'Sin inducción vigente.'), 'No', 'No', 'No', 'Inducción general'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 registros · ingresaron: 1 · no ingresaron: 1 · con pendientes: 1 · de '
                                      'sesiones canceladas, rechazadas o vencidas, que no se listan: 1')

    def test_un_incidente_de_seguridad_va_en_la_86_y_no_en_las_fallas_tecnicas(self):
        sesion = self.reserva(date(2026, 9, 10), estado='completada')
        incidente = IncidenciaEquipo.objects.create(
            equipo=self.cortadora, reserva=sesion, titulo='Quemadura leve', descripcion='Contacto con la boquilla.',
            tipo='seguridad', prioridad='alta', estado='resuelta', solucion='Primeros auxilios y guarda instalada.',
            reportada_por=self.coordinadora)
        IncidenciaEquipo.objects.filter(pk=incidente.pk).update(fecha_reporte=_al_mediodia(date(2026, 9, 10)))
        falla = IncidenciaEquipo.objects.create(equipo=self.cortadora, titulo='No corta', descripcion='Lente sucio.',
                                                tipo='falla', reportada_por=self.coordinadora)
        IncidenciaEquipo.objects.filter(pk=falla.pk).update(fecha_reporte=_al_mediodia(date(2026, 9, 11)))
        practica = PlanificacionPractica.objects.create(
            unidad=self.unidad, reserva=sesion, fecha=sesion.fecha, hora_inicio=time(8), hora_fin=time(10),
            asignatura='Prototipado', creado_por=self.coordinadora)
        EjecucionPractica.objects.create(planificacion=practica, fecha_ejecucion=sesion.fecha, tuvo_incidente=True,
                                         incidencia=incidente, creado_por=self.coordinadora)
        incidentes = self.registros('INDUCCION-SEGURIDAD')[5]
        self.assertEqual(incidentes.filas, [
            ['10/09/2026', Par('SEG-EQ-01', 'Cortadora láser'), Par('Quemadura leve', 'Contacto con la boquilla.'),
             incidente.get_prioridad_display(), Par(practica.codigo, sesion.codigo_reserva),
             'Primeros auxilios y guarda instalada.', incidente.get_estado_display(), 'Carla Coordinadora'],
        ])
        self.assertEqual(incidentes.total, 'Total: 1 incidente · sin cerrar: 0')
        fallas = constructor_de('EQUIPAMIENTO')(self.contexto('EQUIPAMIENTO'))[3]
        self.assertEqual([fila[3] for fila in fallas.filas], [Par('No corta', 'Lente sucio.')])


class DesechosTests(_ConUnidades):
    def desecho(self, nombre, generado, **datos):
        base = dict(unidad=self.unidad, fecha_generacion=generado, clase='peligroso', nombre=nombre, cantidad=1,
                    registrado_por=self.coordinadora, responsable=self.tecnico)
        return RegistroDesecho.objects.create(**(base | datos))

    def desechos(self):
        """Uno almacenado del período, uno entregado en el período y dos de antes: uno sin entregar."""
        self.desecho('Solventes halogenados', date(2026, 9, 5), clave_listado='Q.71.06', origen='Práctica PL-26-0001',
                     estado_fisico='liquido', cantidad=Decimal('2.5'), unidad_medida='l', envase='Bidón HDPE 5 L',
                     etiquetado=True, almacenamiento='Cuarto de residuos', etapa='almacenado')
        self.desecho('Envases contaminados', date(2026, 8, 10), clase='especial', cantidad=Decimal('8.1'),
                     etapa='entregado', fecha_entrega=date(2026, 9, 20), gestor_autorizado='Gestora Ambiental Norte',
                     licencia_gestor='MAE-123', manifiesto='M-0045', almacenamiento='Bodega de residuos')
        self.desecho('Lodos de revelado', date(2026, 5, 20), estado_fisico='lodo', cantidad=Decimal('3'),
                     almacenamiento='Cuarto de residuos', etapa='almacenado')
        self.desecho('Baterías usadas', date(2026, 4, 2), clase='especial', cantidad=Decimal('2'),
                     unidad_medida='unidad', etapa='entregado', fecha_entrega=date(2026, 7, 15),
                     gestor_autorizado='Gestora Ambiental Norte', manifiesto='M-0031')

    def test_generacion_del_periodo_con_su_etapa(self):
        self.desechos()
        tabla = self.registros('DESECHOS')[0]
        self.assertEqual(tabla.filas, [
            ['10/08/2026', 'Envases contaminados', Par('Especial', 'Sólido'), '—', '8,1 kg', Par('—', 'Sin etiquetar'),
             'Bodega de residuos', 'Entregado', 'Tomás Técnico'],
            ['05/09/2026', Par('Solventes halogenados', 'Q.71.06'), Par('Peligroso', 'Líquido'), 'Práctica PL-26-0001',
             '2,5 L', Par('Bidón HDPE 5 L', 'Etiquetado'), 'Cuarto de residuos', 'Almacenado', 'Tomás Técnico'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 registros · 8,1 kg · 2,5 L · almacenados: 1 · entregados: 1 · '
                                      'tratados: 0')

    def test_entregas_del_periodo_al_gestor(self):
        self.desechos()
        tabla = self.registros('DESECHOS')[1]
        self.assertEqual(tabla.filas, [
            ['15/07/2026', 'Baterías usadas', '2 unidades', 'Gestora Ambiental Norte', 'M-0031', '—'],
            ['20/09/2026', 'Envases contaminados', '8,1 kg', Par('Gestora Ambiental Norte', 'MAE-123'), 'M-0045', '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 entregas · 2 unidades · 8,1 kg · manifiestos: 2 · con documento: 0')

    def test_lo_generado_antes_del_periodo_y_sin_entregar_sigue_almacenado_al_corte(self):
        self.desechos()
        contexto = self.contexto('DESECHOS')
        tabla = constructor_de('DESECHOS')(contexto)[2]
        self.assertEqual(tabla.filas, [
            [Par('Lodos de revelado', 'Peligroso'), '3 kg', '20/05/2026',
             str((contexto.corte - date(2026, 5, 20)).days), 'Cuarto de residuos'],
            [Par('Solventes halogenados', 'Peligroso'), '2,5 L', '05/09/2026',
             str((contexto.corte - date(2026, 9, 5)).days), 'Cuarto de residuos'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 registros · 3 kg · 2,5 L')
        self.assertEqual(tabla.vacio, f'No hay desechos almacenados al {fecha(contexto.corte)}.')
