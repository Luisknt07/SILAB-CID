"""Anexos de reportes de seguridad y de gestión de desechos.

Tablas y columnas: docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.8 y 4.9. Cada
función recibe un :class:`~apps.documentos.presentation.anexos_evidencia.Contexto` y devuelve
la lista de :class:`~apps.documentos.presentation.anexos_evidencia.Registro` del anexo, en el
orden de la especificación. El motor numera las tablas y dibuja el PDF.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from .anexos_evidencia import (
    Registro, celda, cifra, enlace, enlace_archivo, enlace_recurso, evidencias_de_gestion, fecha, mes, nombre_de,
    par, plural, si_no, texto, verificacion,
)

TIPOS_REQUISITO = {'induccion': 'Inducción', 'sanitario': 'Sanitario', 'documento': 'Documento',
                   'proteccion': 'Protección', 'restriccion': 'Restricción'}
ESTADOS_CONDICIONES = {'seguro': 'Seguro', 'observado': 'Observado', 'no_operar': 'No operar'}
ESTADOS_ACCION = {'no_requiere': 'No requiere', 'pendiente': 'Pendiente', 'resuelta': 'Atendida'}
ETAPAS_DESECHO = {'almacenado': 'Almacenado', 'entregado': 'Entregado', 'tratado': 'Tratado'}
# La categoría de una persona, en singular (el catálogo la nombra en plural para los requisitos).
CATEGORIAS_PERSONA = {'estudiante': 'Estudiante', 'docente': 'Docente o investigador',
                      'personal': 'Personal de la unidad', 'externo': 'Persona externa', 'visitante': 'Visitante'}


def _hora(valor):
    return f'{valor:%H:%M}' if valor else '—'


def _fecha_iso(valor):
    """Una fecha guardada como texto «aaaa-mm-dd», en la escritura local; '' si no es una fecha."""
    try:
        return fecha(date.fromisoformat(str(valor or '')))
    except ValueError:
        return ''


def _decimal(valor):
    """Cantidad con hasta tres decimales, sin ceros de relleno: 2,8 y 0,125."""
    numero = cifra(valor, 3)
    return numero.rstrip('0').rstrip(',') if ',' in numero else numero


def protocolo_vigente(contexto):
    """El protocolo que rige la unidad al corte: referencia, versión y vigencia.

    Es el documento principal de la exigencia; el anexo de seguridad lo cita en sus datos generales.
    """
    from apps.documentos.presentation.cumplimiento import vigencia_exportada
    from apps.gestion_unidades.presentation.reportes_condiciones import _documentos_seguridad
    from .perfil_laboratorios import referencia_interna

    protocolo, _chequeos = _documentos_seguridad(contexto.unidad, contexto.inicio, contexto.fin)
    if protocolo is None or not protocolo.recurso_id:
        return 'Sin protocolo registrado al corte.'
    vigencia = vigencia_exportada(protocolo) or protocolo.get_estado_display()
    return f'{referencia_interna(protocolo)} · versión {protocolo.version} · {vigencia.lower()}'


# -- seguridad -----------------------------------------------------------------------------

def _requisitos(contexto):
    from apps.reservas.models.seguridad import RequisitoAcceso

    filas = []
    obligatorios = 0
    for requisito in (RequisitoAcceso.objects.filter(unidad=contexto.unidad, activo=True)
                      .select_related('consumible').order_by('orden', 'nombre', 'pk')):
        obligatorios += requisito.obligatorio
        if not requisito.habilitable:
            vigencia = 'Cada ingreso'
        else:
            vigencia = f'{cifra(requisito.vigencia_dias)} días' if requisito.vigencia_dias else 'Sin vencimiento'
        # El insumo es del inventario: se cita por su código.
        insumo = requisito.consumible
        proteccion = par(texto(insumo.codigo or insumo.nombre, 60),
                         f'{_decimal(requisito.cantidad_por_persona)} {insumo.unidad_medida} por persona'
                         ) if insumo else '—'
        filas.append([
            par(texto(requisito.codigo), texto(requisito.nombre, 90)),
            TIPOS_REQUISITO.get(requisito.tipo, requisito.get_tipo_display()),
            texto(requisito.categorias_display, 90),
            requisito.get_momento_display(),
            si_no(requisito.obligatorio),
            vigencia,
            proteccion,
        ])
    return Registro('Requisitos de acceso',
                    ('Código / requisito', 'Tipo', 'Aplica a', 'Cuándo se exige', 'Obligatorio', 'Vigencia',
                     'Protección por persona'),
                    filas, pesos=(28, 10, 18, 13, 8, 10, 18),
                    total=f'Total: {plural(len(filas), "requisito", "requisitos")} · obligatorios: {cifra(obligatorios)}',
                    vacio='La unidad no tiene requisitos de acceso configurados.')


def _habilitaciones(contexto):
    from apps.reservas.models.seguridad import HabilitacionAcceso

    filas = []
    personas = set()
    vigentes = 0
    for habilitacion in (HabilitacionAcceso.objects
                         .filter(requisito__unidad=contexto.unidad, fecha__range=(contexto.inicio, contexto.fin))
                         .select_related('requisito', 'usuario', 'otorgada_por', 'reserva').order_by('fecha', 'pk')):
        personas.add(habilitacion.usuario_id)
        if not habilitacion.activa:
            estado = 'Revocada'
        elif habilitacion.vence and habilitacion.vence < contexto.corte:
            estado = 'Vencida'
        else:
            estado = 'Vigente'
            vigentes += 1
        sesion = habilitacion.reserva.codigo_reserva if habilitacion.reserva_id else ''
        filas.append([
            fecha(habilitacion.fecha),
            nombre_de(habilitacion.usuario),
            texto(habilitacion.requisito.nombre, 80),
            fecha(habilitacion.vence) if habilitacion.vence else 'Sin vencimiento',
            par(habilitacion.get_origen_display(), texto(sesion) if sesion else ''),
            nombre_de(habilitacion.otorgada_por),
            celda(habilitacion.documento) if habilitacion.documento.strip() else '—',
            estado,
        ])
    return Registro('Inducciones y habilitaciones del período',
                    ('Fecha', 'Persona', 'Requisito', 'Vence', 'Origen', 'Otorgada por', 'Documento',
                     'Estado al corte'),
                    filas, pesos=(9, 16, 20, 10, 15, 13, 9, 8),
                    total=(f'Total: {plural(len(filas), "habilitación", "habilitaciones")} · '
                           f'personas: {cifra(len(personas))} · vigentes al corte: {cifra(vigentes)}'),
                    vacio='No se otorgaron inducciones ni habilitaciones en el período.')


def _inspecciones(contexto):
    from apps.documentos.models.resultados_gestion import lectura_condiciones

    filas = []
    verificadas = con_hallazgos = pendientes = 0
    for evidencia in evidencias_de_gestion(contexto.unidad, 'INSPECCION', contexto.inicio, contexto.fin):
        detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
        revisadas, exigidas, cuales = lectura_condiciones(contexto.unidad, detalle.get('condiciones_revisadas'))
        sin_hallazgos = detalle.get('sin_hallazgos') is True
        hallazgos = str(detalle.get('hallazgos') or '').strip()
        verificadas += evidencia.estado == 'validado' and not evidencia.demostracion
        con_hallazgos += bool(hallazgos) and not sin_hallazgos
        pendientes += detalle.get('estado_accion') == 'pendiente'
        plazo = _fecha_iso(detalle.get('plazo_accion'))
        respaldo = enlace_recurso(evidencia.recurso) if evidencia.recurso_id else enlace(evidencia.enlace)
        filas.append([
            par(mes(f'{evidencia.fecha:%Y-%m}'), fecha(evidencia.fecha)),
            texto(detalle.get('area'), 90),
            par(f'{revisadas} de {exigidas}', texto(', '.join(cuales), 200) if cuales else ''),
            'Sin hallazgos' if sin_hallazgos else texto(hallazgos, 200),
            ESTADOS_CONDICIONES.get(detalle.get('estado_condiciones'), '—'),
            par(texto(detalle.get('accion_correctiva'), 160), f'plazo {plazo}' if plazo else ''),
            ESTADOS_ACCION.get(detalle.get('estado_accion'), '—'),
            nombre_de(evidencia.responsable),
            par(respaldo, verificacion(evidencia)),
        ])
    return Registro('Inspecciones de condiciones',
                    ('Mes / fecha', 'Área', 'Condiciones revisadas', 'Hallazgos', 'Estado',
                     'Acción correctiva / plazo', 'Estado de la acción', 'Responsable', 'Respaldo'),
                    filas, pesos=(11, 12, 18, 14, 8, 13, 8, 9, 10),
                    total=(f'Total: {plural(len(filas), "inspección", "inspecciones")} · '
                           f'verificadas: {cifra(verificadas)} · con hallazgos: {cifra(con_hallazgos)} · '
                           f'acciones pendientes: {cifra(pendientes)}'),
                    vacio='No se registraron inspecciones en el período.')


def _cobertura(contexto):
    """La cobertura mensual tal como la mide la meta de inspecciones del informe."""
    meses = (contexto.registros.get('cobertura_inspecciones') or {}).get('meses') or ()
    filas = []
    for m in meses:
        if m.get('cumple'):
            situacion = 'Cubierto'
        else:
            situacion = 'Sin inspección verificada' if m.get('revisiones') else 'Sin inspección'
        filas.append([mes(m['mes']), 'Sí' if m.get('exigible') else 'Aún en plazo', cifra(m.get('revisiones')),
                      cifra(m.get('verificadas_reales')), situacion])
    exigibles = sum(bool(m.get('exigible')) for m in meses)
    cubiertos = sum(bool(m.get('cumple')) for m in meses)
    return Registro('Cobertura mensual de inspecciones',
                    ('Mes', 'Exigible', 'Inspecciones registradas', 'Verificadas', 'Situación'),
                    filas, pesos=(24, 16, 20, 16, 24),
                    total=(f'Total: {plural(len(filas), "mes", "meses")} · exigibles al corte: {cifra(exigibles)} · '
                           f'cubiertos: {cifra(cubiertos)}'),
                    vacio='El período aún no tiene meses que revisar.')


def _ingresos(contexto):
    from apps.reservas.models.seguridad import RegistroIngreso
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    todos = RegistroIngreso.objects.filter(reserva__laboratorio=contexto.unidad,
                                           reserva__fecha__range=(contexto.inicio, contexto.fin))
    descartados = todos.filter(reserva__estado__in=ESTADOS_RESERVA_DESCARTADOS).count()
    filas = []
    ingresaron = con_pendientes = 0
    for registro in (todos.exclude(reserva__estado__in=ESTADOS_RESERVA_DESCARTADOS).select_related('reserva')
                     .order_by('reserva__fecha', 'reserva__hora_inicio', 'reserva_id', 'hora_ingreso', 'nombre', 'pk')):
        pendientes = registro.pendientes if isinstance(registro.pendientes, list) else [registro.pendientes]
        pendientes = [str(p).strip() for p in pendientes if str(p or '').strip()]
        ingresaron += registro.ingresa
        con_pendientes += bool(pendientes)
        horas = ''
        if registro.hora_ingreso or registro.hora_salida:
            horas = f'ingreso {_hora(registro.hora_ingreso)} · salida {_hora(registro.hora_salida)}'
        filas.append([
            par(fecha(registro.reserva.fecha), horas),
            texto(registro.reserva.codigo_reserva),
            par(texto(registro.nombre, 60),
                CATEGORIAS_PERSONA.get(registro.categoria, registro.get_categoria_display())),
            par(si_no(registro.ingresa), texto(registro.motivo, 120) if registro.motivo.strip() else ''),
            si_no(registro.proteccion_verificada),
            si_no(registro.restricciones_verificadas),
            si_no(registro.habilitaciones_vigentes),
            texto(', '.join(pendientes), 120),
        ])
    pie = (f'Total: {plural(len(filas), "registro", "registros")} · ingresaron: {cifra(ingresaron)} · '
           f'no ingresaron: {cifra(len(filas) - ingresaron)} · con pendientes: {cifra(con_pendientes)}')
    if descartados:
        pie += f' · de sesiones canceladas, rechazadas o vencidas, que no se listan: {cifra(descartados)}'
    return Registro('Control de ingresos',
                    ('Fecha / hora', 'Sesión', 'Persona / categoría', 'Ingresó', 'Protección verificada',
                     'Restricciones verificadas', 'Habilitaciones vigentes', 'Pendientes'),
                    filas, pesos=(15, 11, 17, 17, 9, 10, 10, 11), total=pie,
                    vacio='No hay ingresos registrados en el período.')


def _incidentes(contexto):
    from django.db.models import Q

    from apps.recursos.models.mantenimiento import IncidenciaEquipo

    unidad = contexto.unidad
    incidencias = (IncidenciaEquipo.objects
                   .filter(Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad)
                           | Q(unidad__isnull=True, equipo__laboratorios=unidad),
                           tipo='seguridad', fecha_reporte__date__range=(contexto.inicio, contexto.fin))
                   .distinct().select_related('equipo__equipo', 'reserva', 'reportada_por')
                   .prefetch_related('ejecuciones_practica__planificacion').order_by('fecha_reporte', 'pk'))
    filas = []
    abiertos = 0
    for incidencia in incidencias:
        abiertos += incidencia.estado not in IncidenciaEquipo.ESTADOS_CERRADOS
        practicas = ', '.join(dict.fromkeys(
            e.planificacion.codigo for e in incidencia.ejecuciones_practica.all()
            if e.eliminado_en is None and e.planificacion.codigo))
        sesion = incidencia.reserva.codigo_reserva if incidencia.reserva_id else ''
        filas.append([
            fecha(incidencia.fecha_reporte),
            par(texto(incidencia.equipo.codigo_unidad), texto(incidencia.equipo.equipo.nombre, 60)),
            par(texto(incidencia.titulo, 90), texto(incidencia.descripcion, 200)),
            incidencia.get_prioridad_display(),
            par(texto(practicas), texto(sesion) if sesion else '') if practicas else texto(sesion),
            texto(incidencia.solucion, 200),
            incidencia.get_estado_display(),
            nombre_de(incidencia.reportada_por),
        ])
    return Registro('Incidentes de seguridad',
                    ('Fecha', 'Lugar o equipo', 'Descripción', 'Prioridad', 'Práctica o sesión',
                     'Acción / solución', 'Estado', 'Reportado por'),
                    filas, pesos=(9, 15, 24, 8, 12, 14, 8, 10),
                    total=f'Total: {plural(len(filas), "incidente", "incidentes")} · sin cerrar: {cifra(abiertos)}',
                    vacio='No se reportaron incidentes de seguridad en el período.')


def seguridad(contexto):
    """Anexo de reportes de seguridad y condiciones de operación (sección 4.8).

    Requisitos de acceso, habilitaciones, inspecciones con su cobertura mensual, control de
    ingresos e incidentes de seguridad. Las condiciones que revisa una inspección son las
    comunes y las propias del tipo de unidad.
    """
    return [_requisitos(contexto), _habilitaciones(contexto), _inspecciones(contexto), _cobertura(contexto),
            _ingresos(contexto), _incidentes(contexto)]


# -- desechos ------------------------------------------------------------------------------

def _cantidad(desecho):
    return f'{_decimal(desecho.cantidad)} {desecho.get_unidad_medida_display()}'


def _por_unidad(desechos):
    """Las cantidades sumadas por unidad de medida: «8,1 kg · 8,5 L»."""
    sumas = defaultdict(Decimal)
    for desecho in desechos:
        sumas[desecho.get_unidad_medida_display()] += desecho.cantidad
    return ' · '.join(f'{_decimal(cantidad)} {unidad}' for unidad, cantidad in sumas.items())


def desechos(contexto):
    """Anexo de gestión de desechos peligrosos y especiales (sección 4.9).

    Lo generado en el período, las entregas del período al gestor y lo que sigue almacenado
    al corte, también lo generado antes del período.
    """
    from django.db.models import Q

    from apps.recursos.models.desechos import RegistroDesecho

    de_la_unidad = RegistroDesecho.objects.filter(unidad=contexto.unidad).select_related('responsable')
    generados = list(de_la_unidad.filter(fecha_generacion__range=(contexto.inicio, contexto.fin))
                     .order_by('fecha_generacion', 'pk'))
    entregados = list(de_la_unidad.filter(etapa='entregado', fecha_entrega__range=(contexto.inicio, contexto.fin))
                      .order_by('fecha_entrega', 'manifiesto', 'pk'))
    almacenados = list(de_la_unidad.filter(fecha_generacion__lte=contexto.corte)
                       .filter(Q(etapa='almacenado') | Q(etapa='entregado', fecha_entrega__gt=contexto.corte))
                       .order_by('fecha_generacion', 'pk'))

    generacion = [[
        fecha(d.fecha_generacion),
        par(texto(d.nombre, 90), texto(d.clave_listado) if d.clave_listado else ''),
        par(d.get_clase_display(), d.get_estado_fisico_display()),
        texto(d.origen, 120),
        _cantidad(d),
        par(texto(d.envase, 80), 'Etiquetado' if d.etiquetado else 'Sin etiquetar'),
        texto(d.almacenamiento, 90),
        ETAPAS_DESECHO.get(d.etapa, d.get_etapa_display()),
        nombre_de(d.responsable),
    ] for d in generados]
    por_etapa = defaultdict(int)
    for d in generados:
        por_etapa[d.etapa] += 1
    pie_generacion = (f'Total: {plural(len(generados), "registro", "registros")} · {_por_unidad(generados)} · '
                      f'almacenados: {cifra(por_etapa["almacenado"])} · entregados: {cifra(por_etapa["entregado"])} · '
                      f'tratados: {cifra(por_etapa["tratado"])}')

    entregas = [[
        fecha(d.fecha_entrega),
        par(texto(d.nombre, 90), texto(d.clave_listado) if d.clave_listado else ''),
        _cantidad(d),
        par(texto(d.gestor_autorizado, 90), texto(d.licencia_gestor) if d.licencia_gestor else ''),
        texto(d.manifiesto),
        enlace_archivo(d.documento),
    ] for d in entregados]
    manifiestos = len({d.manifiesto.strip() for d in entregados if d.manifiesto.strip()})
    con_documento = sum(bool(d.documento) for d in entregados)
    pie_entregas = (f'Total: {plural(len(entregados), "entrega", "entregas")} · {_por_unidad(entregados)} · '
                    f'manifiestos: {cifra(manifiestos)} · con documento: {cifra(con_documento)}')

    al_corte = [[
        par(texto(d.nombre, 90), d.get_clase_display()),
        _cantidad(d),
        fecha(d.fecha_generacion),
        cifra((contexto.corte - d.fecha_generacion).days),
        texto(d.almacenamiento, 90),
    ] for d in almacenados]
    pie_corte = f'Total: {plural(len(almacenados), "registro", "registros")} · {_por_unidad(almacenados)}'

    return [
        Registro('Generación y almacenamiento',
                 ('Fecha', 'Desecho / clave', 'Clase / estado físico', 'Origen', 'Cantidad', 'Envase / etiquetado',
                  'Almacenamiento temporal', 'Etapa', 'Responsable'),
                 generacion, pesos=(8, 17, 10, 16, 7, 14, 12, 8, 10), total=pie_generacion,
                 vacio='Sin registros en el período.'),
        Registro('Entregas al gestor autorizado',
                 ('Fecha de entrega', 'Desechos', 'Cantidad', 'Gestor / licencia', 'Manifiesto', 'Documento'),
                 entregas, pesos=(12, 30, 10, 24, 14, 10), total=pie_entregas,
                 vacio='No hubo entregas al gestor autorizado en el período.'),
        Registro('Almacenado al corte',
                 ('Desecho', 'Cantidad pendiente de entrega', 'Desde', 'Días almacenado', 'Lugar'),
                 al_corte, pesos=(34, 16, 12, 12, 26), total=pie_corte,
                 vacio=f'No hay desechos almacenados al {fecha(contexto.corte)}.'),
    ]
