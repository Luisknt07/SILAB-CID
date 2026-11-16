"""Contenido de los anexos de resultados de investigación y de transferencia y servicios.

Fija lo acordado en docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.10 y 4.11:
- las tablas de cada anexo, en el orden y con las columnas de la especificación; los llevan los
  cuatro tipos de unidad y el observatorio suma sus solicitudes de información atendidas;
- una sesión de investigación se cita por su código: es uso, no resultado;
- un servicio cancelado, rechazado o vencido no se presenta;
- en la planta piloto, la maquila sin solicitud de servicio se cita por el código de su orden;
- las evidencias anuladas no se presentan.
"""
from datetime import date, datetime, time
from datetime import timezone as zona
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import Enlace, Par, constructor_de, contexto_del_anexo
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.reservas.models.reservas import Reserva

TIPOS = ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')
# Las tablas de cada anexo y sus columnas, tal como las fija la especificación.
TABLAS = {
    'INVESTIGACION': [
        ('Resultados',
         ('Código', 'Fecha', 'Proyecto', 'Tipo de producto', 'Producto / resultado', 'Responsable', 'Beneficiario',
          'Verificación', 'Respaldo')),
        ('Uso de la unidad para investigación',
         ('Sesión', 'Fecha', 'Proyecto o actividad', 'Responsable', 'Horas efectivas')),
    ],
    'TRANSFERENCIA': [
        ('Transferencias',
         ('Código', 'Fecha', 'Entidad destinataria', 'Tipo', 'Entregable', 'Aceptación', 'Verificación',
          'Respaldo')),
        ('Servicios especializados',
         ('Solicitud', 'Fecha', 'Solicitante / entidad', 'Tipo de trabajo / modalidad', 'Descripción', 'Estado',
          'Horas', 'Valor', 'Orden o sesión')),
    ],
}
# Solo el observatorio: lo que se le pidió y lo que respondió.
SOLICITUDES_DE_INFORMACION = (
    'Solicitudes de información atendidas',
    ('Recibida / atendida', 'Solicitante / institución', 'Qué necesita', 'Detalle', 'Finalidad', 'Estado',
     'Respuesta'))
EFECTIVA = {'registrada_en': '2026-09-10T10:00:00-05:00'}


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
        cls.coordinadora = usuarios.create_user('coordinadora-anexos-resultados', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user('tecnico-anexos-resultados', first_name='Tomás', last_name='Técnico')
        cls.cliente = usuarios.create_user('cliente-anexos-resultados', first_name='Rosa', last_name='Ruiz')
        cls.unidades = {tipo: Unidad.objects.create(
            nombre=f'Unidad de resultados {tipo}', slug=f'anexos-resultados-{tipo}', dependencia=tipo,
            fecha_inicio=date(2025, 1, 1), administrador=cls.coordinadora) for tipo in TIPOS}
        cls.unidad = cls.unidades['laboratorios']

    def contexto(self, codigo, tipo='laboratorios'):
        anexo = _anexo(self.unidades[tipo], codigo)
        inicio, fin = tramo_del_documento(anexo)
        self.assertEqual((inicio, fin), (date(2026, 7, 1), date(2026, 12, 31)))
        return contexto_del_anexo(anexo, inicio, fin)

    def registros(self, codigo, tipo='laboratorios'):
        return constructor_de(codigo)(self.contexto(codigo, tipo))

    def evidencia(self, tipo, codigo, dia, **datos):
        base = dict(unidad=self.unidad, tipo=tipo, codigo=codigo, fecha=dia, titulo=f'Registro {codigo}',
                    descripcion='Registro de prueba.', responsable=self.tecnico, creado_por=self.coordinadora,
                    enlace=f'https://example.org/{codigo.lower()}')
        return EvidenciaGestionUnidad.objects.create(**(base | datos))

    def reserva(self, dia, unidad=None, **datos):
        reserva = Reserva.objects.create(**(dict(laboratorio=unidad or self.unidad, usuario=self.cliente, fecha=dia,
                                                 hora_inicio=time(8), hora_fin=time(10)) | datos))
        reserva.refresh_from_db()
        return reserva


class TablasDeLaEspecificacionTests(_ConUnidades):
    def test_cada_anexo_lleva_las_tablas_y_columnas_de_la_especificacion(self):
        for tipo in TIPOS:
            for codigo, tablas in TABLAS.items():
                with self.subTest(tipo=tipo, anexo=codigo):
                    esperadas = tablas + ([SOLICITUDES_DE_INFORMACION]
                                          if codigo == 'TRANSFERENCIA' and tipo == 'observatorios' else [])
                    registros = self.registros(codigo, tipo)
                    self.assertEqual([(r.titulo, tuple(r.cabecera)) for r in registros], esperadas)
                    for registro in registros:
                        self.assertEqual(registro.filas, [], registro.titulo)
                        self.assertTrue(registro.vacio, registro.titulo)


class InvestigacionTests(_ConUnidades):
    def test_resultados_del_periodo_en_cualquier_estado_salvo_anulados(self):
        detalle = {'proyecto': 'Secadores solares', 'tipo_producto': 'prototipo',
                   'producto': 'Prototipo de secador solar', 'beneficiario': 'Asociación de productores'}
        self.evidencia('INVESTIGACION', 'INV-01', date(2026, 9, 15), detalle=detalle, estado='validado',
                       descripcion='Seca 20 kg de grano por jornada.')
        self.evidencia('INVESTIGACION', 'INV-02', date(2026, 10, 3), detalle=detalle | {'tipo_producto': 'informe',
                                                                                          'producto': ''})
        self.evidencia('INVESTIGACION', 'INV-03', date(2026, 10, 4), detalle=detalle, estado='anulado')
        self.evidencia('INVESTIGACION', 'INV-04', date(2026, 5, 4), detalle=detalle, estado='validado')
        tabla = self.registros('INVESTIGACION')[0]
        self.assertEqual(tabla.filas, [
            ['INV-01', '15/09/2026', 'Secadores solares', 'Prototipo o desarrollo tecnológico',
             Par('Prototipo de secador solar', 'Seca 20 kg de grano por jornada.'), 'Tomás Técnico',
             'Asociación de productores', 'Evidencia verificada', Enlace('Abrir', 'https://example.org/inv-01')],
            # Sin producto escrito, la celda lleva el título del registro.
            ['INV-02', '03/10/2026', 'Secadores solares', 'Informe técnico o de investigación',
             Par('Registro INV-02', 'Registro de prueba.'), 'Tomás Técnico', 'Asociación de productores', 'Borrador',
             Enlace('Abrir', 'https://example.org/inv-02')],
        ])
        self.assertEqual(tabla.total, 'Total: 2 resultados · verificados: 1')

    def test_una_demostracion_se_marca_y_no_cuenta_como_verificada(self):
        self.evidencia('INVESTIGACION', 'INV-DEMO', date(2026, 9, 15), estado='validado', demostracion=True)
        tabla = self.registros('INVESTIGACION')[0]
        self.assertEqual(tabla.filas[0][7], 'Demostración; no acredita')
        self.assertEqual(tabla.total, 'Total: 1 resultado · verificados: 0')

    def test_las_sesiones_de_investigacion_se_citan_por_su_codigo(self):
        atendida = self.reserva(date(2026, 9, 12), estado='completada', resultado_cierre='atendida',
                                detalle_ejecucion=EFECTIVA, proposito_codigo='investigacion_innovacion',
                                referencia_actividad='Proyecto Secadores solares',
                                intencion_solicitud='Medición de humedad del grano.',
                                responsable_actividad='Dra. Rosa Ruiz')
        pendiente = self.reserva(date(2026, 10, 2), estado='confirmada', proposito_codigo='investigacion_innovacion',
                                 titulo_solicitud='Ensayo de secado')
        self.reserva(date(2026, 10, 9), estado='cancelada', proposito_codigo='investigacion_innovacion')
        self.reserva(date(2026, 10, 9), estado='confirmada', proposito_codigo='docencia_practica')
        tabla = self.registros('INVESTIGACION')[1]
        self.assertEqual(tabla.filas, [
            [atendida.codigo_reserva, '12/09/2026', Par('Proyecto Secadores solares', 'Medición de humedad del grano.'),
             'Dra. Rosa Ruiz', '2'],
            [pendiente.codigo_reserva, '02/10/2026', 'Ensayo de secado', 'Rosa Ruiz', '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 sesiones · atendidas: 1 · horas efectivas: 2')


class TransferenciaYServiciosTests(_ConUnidades):
    def test_transferencias_con_su_aceptacion_y_sin_las_anuladas(self):
        detalle = {'beneficiario': 'GAD de Montúfar', 'tipo_producto': 'transferencia',
                   'producto': 'Protocolo de compostaje', 'aceptacion': 'aceptado', 'fecha_aceptacion': '2026-10-02',
                   'referencia_aceptacion': 'Acta 7-2026'}
        self.evidencia('TRANSFERENCIA', 'TRA-01', date(2026, 9, 20), detalle=detalle, estado='validado')
        self.evidencia('TRANSFERENCIA', 'TRA-02', date(2026, 10, 1),
                       detalle=detalle | {'aceptacion': 'pendiente', 'producto': 'Guía de riego'})
        self.evidencia('TRANSFERENCIA', 'TRA-03', date(2026, 10, 5), detalle=detalle, estado='anulado')
        tabla = self.registros('TRANSFERENCIA')[0]
        self.assertEqual(tabla.filas, [
            ['TRA-01', '20/09/2026', 'GAD de Montúfar', 'Tecnología o conocimiento transferido',
             'Protocolo de compostaje', Par('02/10/2026', 'Acta 7-2026'), 'Evidencia verificada',
             Enlace('Abrir', 'https://example.org/tra-01')],
            ['TRA-02', '01/10/2026', 'GAD de Montúfar', 'Tecnología o conocimiento transferido', 'Guía de riego',
             'Pendiente', 'Borrador', Enlace('Abrir', 'https://example.org/tra-02')],
        ])
        self.assertEqual(tabla.total, 'Total: 2 transferencias · aceptadas: 1 · verificadas: 1')

    def test_un_servicio_atendido_con_su_valor_y_uno_cancelado_que_no_aparece(self):
        servicio = self.reserva(
            date(2026, 9, 10), tipo_solicitud='servicio', estado='completada', resultado_cierre='atendida',
            detalle_ejecucion=EFECTIVA, nombre_solicitante='Rosa Ruiz', entidad_beneficiaria='Taller Ruiz',
            modalidad_servicio='diseno_asistido', titulo_solicitud='Corte de piezas acrílicas',
            detalle_trabajo='Veinte piezas de 5 mm.', costo_estimado=Decimal('50'), valor_final_usuario=Decimal('45'),
            aporte_institucional_real=Decimal('5'), fecha_cierre=_al_mediodia(date(2026, 9, 12)))
        self.reserva(date(2026, 9, 18), tipo_solicitud='servicio', estado='cancelada',
                     titulo_solicitud='Servicio cancelado')
        tabla = self.registros('TRANSFERENCIA')[1]
        self.assertEqual(tabla.filas, [
            [servicio.codigo_reserva, Par('10/09/2026', 'entregado 12/09/2026'), Par('Rosa Ruiz', 'Taller Ruiz'),
             Par('—', servicio.get_modalidad_servicio_display()),
             Par('Corte de piezas acrílicas', 'Veinte piezas de 5 mm.'),
             Par(servicio.get_estado_display(), servicio.get_resultado_cierre_display()), Par('2', 'efectivas'),
             Par('50 USD', 'final 45 USD · aporte institucional 5 USD'), servicio.codigo_reserva],
        ])
        self.assertEqual(tabla.total, 'Total: 1 servicio · completados: 1 · cancelados, rechazados o vencidos, que no '
                                      'se listan: 1')

    def test_una_solicitud_operativa_presenta_su_estado_y_sus_horas_estimadas(self):
        sesion = self.reserva(date(2026, 10, 6), tipo_solicitud='servicio', estado='confirmada',
                              titulo_solicitud='Prototipo de carcasa', fecha_entrega_prevista=date(2026, 10, 20))
        solicitud = SolicitudFabricacion.objects.create(
            unidad=self.unidad, reserva=sesion, solicitante=self.cliente, departamento='Carrera de Computación',
            fecha_solicitud=date(2026, 10, 1), tipo_trabajo='investigacion', nombre_proyecto='Carcasa del sensor',
            descripcion_general='Carcasa impresa en PETG.', tiempo_estimado_horas=Decimal('6'),
            estado='en_fabricacion')
        SolicitudFabricacion.objects.create(unidad=self.unidad, solicitante=self.cliente,
                                            fecha_solicitud=date(2026, 9, 1), nombre_proyecto='Rechazada',
                                            estado='rechazada')
        tabla = self.registros('TRANSFERENCIA')[1]
        self.assertEqual(tabla.filas, [
            [sesion.codigo_reserva, Par('01/10/2026', 'entrega prevista 20/10/2026'), 'Rosa Ruiz',
             solicitud.get_tipo_trabajo_display(), Par('Prototipo de carcasa', 'Carcasa impresa en PETG.'),
             Par(solicitud.get_estado_display(), f'sesión {sesion.get_estado_display().lower()}'),
             Par('6', 'estimadas'), '—', sesion.codigo_reserva],
        ])
        self.assertEqual(tabla.total, 'Total: 1 servicio · completados: 0 · cancelados, rechazados o vencidos, que no '
                                      'se listan: 1')

    def test_una_solicitud_rechazada_no_se_presenta_aunque_su_sesion_siga_pendiente(self):
        # Rechazar la solicitud en su revisión no toca la sesión reservada: sigue pendiente.
        sesion = self.reserva(date(2026, 10, 7), tipo_solicitud='servicio', estado='pendiente',
                              titulo_solicitud='Impresión rechazada')
        SolicitudFabricacion.objects.create(unidad=self.unidad, reserva=sesion, solicitante=self.cliente,
                                            fecha_solicitud=date(2026, 10, 2), nombre_proyecto='Rechazada',
                                            revision_laboratorista='rechazada',
                                            observaciones_laboratorista='El material no es apto.')
        self.assertEqual(self.registros('TRANSFERENCIA')[1].filas, [])

    def test_en_la_planta_la_maquila_se_cita_por_el_codigo_de_su_orden(self):
        from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Producto, Receta
        planta = self.unidades['plantas_piloto']
        producto = Producto.objects.create(unidad=planta, codigo='RES-QUESO', nombre='Queso fresco', unidad_medida='kg')
        receta = Receta.objects.create(unidad=planta, producto=producto, codigo='RES-REC-QUESO', nombre='Queso fresco',
                                       cantidad_base=10, unidad_base='l', rendimiento_esperado=Decimal('1.2'))
        servicio = self.reserva(date(2026, 9, 8), unidad=planta, tipo_solicitud='servicio', estado='confirmada',
                                titulo_solicitud='Procesamiento de leche')
        orden_del_servicio = OrdenProduccion.objects.create(unidad=planta, receta=receta, origen='maquila',
                                                            reserva=servicio, fecha_inicio=date(2026, 9, 8),
                                                            fecha_fin=date(2026, 9, 8))
        maquila = OrdenProduccion.objects.create(unidad=planta, receta=receta, origen='maquila',
                                                 fecha_inicio=date(2026, 9, 14), fecha_fin=date(2026, 9, 15))
        OrdenProduccion.objects.create(unidad=planta, receta=receta, origen='maquila', fecha_inicio=date(2026, 9, 20),
                                       fecha_fin=date(2026, 9, 20), estado='cancelada')
        tabla = self.registros('TRANSFERENCIA', 'plantas_piloto')[1]
        self.assertEqual([fila[0] for fila in tabla.filas], [servicio.codigo_reserva, '—'])
        self.assertEqual(tabla.filas[0][-1], orden_del_servicio.codigo)
        self.assertEqual(tabla.filas[1], [
            '—', Par('14/09/2026', 'fin 15/09/2026'), '—', maquila.get_origen_display(),
            Par('Queso fresco', 'Queso fresco'), maquila.get_estado_display(), '—', '—', maquila.codigo])
        self.assertEqual(tabla.total, 'Total: 1 servicio · completados: 0 · órdenes de maquila sin solicitud de '
                                      'servicio: 1')

    def test_el_observatorio_presenta_sus_solicitudes_de_informacion(self):
        from apps.observatorios.operacion.models.observatorios import SolicitudDatos
        observatorio = self.unidades['observatorios']
        atendida = SolicitudDatos.objects.create(
            unidad=observatorio, usuario=self.cliente, tipo='datos', institucion='GAD de Tulcán',
            descripcion='Precios de la papa en Carchi, 2020-2026.', finalidad='Plan de desarrollo cantonal.',
            estado='atendida', respuesta='Se entregó la serie en CSV.',
            atendida=_al_mediodia(date(2026, 9, 12)))
        recibida = SolicitudDatos.objects.create(unidad=observatorio, usuario=self.cliente, tipo='asesoria',
                                                 descripcion='Diseño de una encuesta.', finalidad='Tesis.')
        anterior = SolicitudDatos.objects.create(unidad=observatorio, usuario=self.cliente, descripcion='Anterior.',
                                                 finalidad='Otro período.')
        SolicitudDatos.objects.filter(pk=atendida.pk).update(creada=_al_mediodia(date(2026, 9, 5)))
        SolicitudDatos.objects.filter(pk=recibida.pk).update(creada=_al_mediodia(date(2026, 10, 1)))
        SolicitudDatos.objects.filter(pk=anterior.pk).update(creada=_al_mediodia(date(2026, 5, 1)))
        tabla = self.registros('TRANSFERENCIA', 'observatorios')[2]
        tipos, estados = dict(SolicitudDatos.TIPOS), dict(SolicitudDatos.ESTADOS)
        self.assertEqual(tabla.filas, [
            [Par('05/09/2026', 'atendida 12/09/2026'), Par('Rosa Ruiz', 'GAD de Tulcán'), tipos['datos'],
             'Precios de la papa en Carchi, 2020-2026.', 'Plan de desarrollo cantonal.', estados['atendida'],
             'Se entregó la serie en CSV.'],
            ['01/10/2026', 'Rosa Ruiz', tipos['asesoria'], 'Diseño de una encuesta.', 'Tesis.', estados['recibida'],
             '—'],
        ])
        self.assertEqual(tabla.total, 'Total: 2 solicitudes · atendidas: 1')
