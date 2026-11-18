"""Respaldo para auditoría: un documento propio por cada tema que pide una revisión externa.

Son registros de lo que la unidad ya capturó: cuentan y listan, sin texto de análisis. Salen del
Centro de reportes para un rango de fechas, en pantalla, PDF, Excel y Word; no se entregan ni
puntúan. El personal y las sustancias sujetas a control son el estado actual de la unidad y no
dependen del rango. El reglamento de uso ya no es una consulta: es un documento principal del
expediente (REGLAMENTO-USO).
"""
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.gestion_unidades.presentation.reportes_seguimiento_documental import LIMITE, _contiene, _dataset, _fecha

ESTADO_ACTUAL = 'Estado actual de la unidad al generar el documento; no depende del rango de fechas.'
SIN_REGISTRAR = 'Sin registrar'
SIN_RESPALDO = 'Sin respaldo'
SIN_AUTORIZACION = 'Sin autorización registrada'
# Las dos metas del plan que no tienen anexo: su respaldo es este documento.
ACTIVIDADES = (('CAPACITACION', 'Capacitación'), ('DIFUSION', 'Difusión'))
# Una calibración está por vencer si vence dentro de estos días contados desde el corte.
DIAS_DE_AVISO_DE_CALIBRACION = 30
LARGO_DE_CELDA = 500


def _texto(valor, largo=LARGO_DE_CELDA):
    """Texto de una celda: en una línea, con «—» si está vacío y recortado si es muy largo."""
    limpio = ' '.join(str(valor if valor not in (None, '') else '—').split())
    return limpio if len(limpio) <= largo else limpio[:largo - 1].rstrip() + '…'


def _buscar(search):
    return str(search or '').strip().casefold()


def _nombre_de(usuario):
    if not usuario:
        return '—'
    return (usuario.get_full_name() or usuario.get_username()).strip() or '—'


def _archivo(archivo):
    """El nombre del archivo guardado, sin su carpeta; '' si no hay archivo."""
    nombre = getattr(archivo, 'name', '') if archivo else ''
    return nombre.rsplit('/', 1)[-1]


def _cantidad(valor, unidad=''):
    """Cantidad con su unidad de medida y sin ceros de relleno: «2.5 kg»."""
    return f'{valor.normalize():f} {unidad or ""}'.strip()


def _documento(headers, rows, cards, *, vacio, notas=(), tablas=(), respaldos=()):
    """El documento con la forma que consume el generador genérico; `vacio` es lo que dice sin registros."""
    datos = _dataset(headers, rows, cards, (), list(tablas), list(notas))
    datos['vacio'] = vacio
    for tabla, origen in zip(datos['tablas'], tablas):
        tabla['vacio'] = origen.get('vacio') or tabla['vacio']
    datos['supporting_documents'] = list(respaldos)[:LIMITE]
    return datos


# -- evidencias de gestión: capacitación, difusión y simulacros ----------------------------------

def _evidencias(unit, tipos, start_date, end_date):
    """Evidencias de gestión de esos tipos en el rango, sin las anuladas, por fecha."""
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    return list(EvidenciaGestionUnidad.objects.filter(unidad=unit, tipo__in=tipos, fecha__range=(start_date, end_date))
                .exclude(estado='anulado').select_related('responsable', 'recurso', 'validado_por')
                .order_by('fecha', 'pk'))


def _verificacion(evidencia):
    """Estado de una evidencia en palabras: verificada, borrador o demostración."""
    return 'Demostración; no acredita' if evidencia.demostracion else evidencia.get_estado_display()


def _pendientes_de_verificar(unit, evidencias, start_date, end_date):
    """Las evidencias marcadas como verificadas que la medición de la meta todavía no cuenta.

    Con la medición activa, «verificada» es la evidencia que la meta contó; las demás quedan pendientes.
    """
    from apps.documentos.presentation.medicion_metas import evidencias_verificadas, habilitada
    if not habilitada():
        return set()
    from apps.documentos.models.respaldo_medicion import corte_efectivo
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable

    inicio = max(start_date, unit.fecha_inicio) if es_unidad_auditable(unit) and unit.fecha_inicio else start_date
    fin = corte_efectivo(unit, end_date)
    # El mismo orden de la medición: ante dos evidencias con el mismo respaldo cuenta la más reciente.
    medibles = sorted((e for e in evidencias if e.estado == 'validado' and inicio <= e.fecha <= fin),
                      key=lambda e: (e.fecha, e.pk), reverse=True)
    contadas = {e.pk for e in evidencias_verificadas(unit, medibles, inicio, fin)}
    return {e.pk for e in evidencias if e.estado == 'validado' and not e.demostracion and e.pk not in contadas}


def _respaldo(evidencia):
    """El archivo o el enlace de la evidencia, por su nombre; el acceso va en «Consultar los respaldos»."""
    if evidencia.recurso_id:
        return 'Archivo: ' + (_archivo(evidencia.recurso.archivo) or evidencia.recurso.nombre)
    return 'Enlace' if evidencia.enlace else SIN_RESPALDO


def _acceso_al_respaldo(evidencia):
    """La fila de «Consultar los respaldos»: la descarga protegida del archivo o el enlace registrado."""
    return dict(pk=evidencia.pk, codigo=evidencia.codigo, titulo=evidencia.titulo,
                recurso=evidencia.recurso if evidencia.recurso_id else None, enlace=evidencia.enlace)


def reporte_capacitacion(unit, start_date, end_date, state='', search=''):
    """Capacitaciones del personal y acciones de difusión del rango, con su verificación y su respaldo."""
    buscar = _buscar(search)
    evidencias = _evidencias(unit, [codigo for codigo, _nombre in ACTIVIDADES], start_date, end_date)
    pendientes = _pendientes_de_verificar(unit, evidencias, start_date, end_date)
    filas, respaldos, cuenta = [], [], Counter()
    for codigo, actividad in ACTIVIDADES:
        for evidencia in (e for e in evidencias if e.tipo == codigo):
            fila = [
                actividad, _fecha(evidencia.fecha),
                f'{_texto(evidencia.titulo, 180)} ({_texto(evidencia.codigo)}). {_texto(evidencia.descripcion)}',
                _nombre_de(evidencia.responsable),
                'Verificación pendiente' if evidencia.pk in pendientes else _verificacion(evidencia),
                _respaldo(evidencia),
            ]
            if not _contiene(buscar, *fila):
                continue
            filas.append(fila)
            cuenta[codigo] += 1
            if evidencia.recurso_id or evidencia.enlace:
                respaldos.append(_acceso_al_respaldo(evidencia))
    return _documento(
        ['Actividad', 'Fecha', 'Descripción', 'Responsable', 'Verificación', 'Respaldo'], filas,
        [('Capacitaciones', cuenta['CAPACITACION']), ('Acciones de difusión', cuenta['DIFUSION'])],
        vacio='No se registraron capacitaciones ni acciones de difusión en el período.', respaldos=respaldos)


def reporte_simulacros(unit, start_date, end_date, state='', search=''):
    """Simulacros y prácticas de emergencia del rango: constancia de que se ensayaron, sin meta."""
    from apps.documentos.models.resultados_gestion import EMERGENCIAS_SIMULACRO, TIPO_SIMULACRO

    buscar = _buscar(search)
    emergencias = dict(EMERGENCIAS_SIMULACRO)
    filas, respaldos, participantes = [], [], 0
    for evidencia in _evidencias(unit, [TIPO_SIMULACRO], start_date, end_date):
        detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
        personas = detalle.get('participantes')
        personas = personas if isinstance(personas, int) and not isinstance(personas, bool) and personas > 0 else None
        fila = [
            _fecha(evidencia.fecha),
            f'{emergencias.get(detalle.get("emergencia"), "—")} · {_texto(evidencia.titulo, 180)}',
            personas if personas is not None else '—',
            _texto(evidencia.descripcion),
            _texto(detalle.get('accion_mejora'), 300),
            _nombre_de(evidencia.responsable),
            f'{_respaldo(evidencia)} · {_verificacion(evidencia)}',
        ]
        if not _contiene(buscar, *fila):
            continue
        filas.append(fila)
        participantes += personas or 0
        if evidencia.recurso_id or evidencia.enlace:
            respaldos.append(_acceso_al_respaldo(evidencia))
    return _documento(
        ['Fecha', 'Emergencia ensayada', 'Participantes', 'Resultado u observaciones', 'Acción de mejora',
         'Responsable', 'Respaldo'], filas,
        [('Simulacros', len(filas)), ('Participantes', participantes)],
        vacio='No se registraron simulacros ni prácticas de emergencia en el período.', respaldos=respaldos)


# -- calibración de equipos -------------------------------------------------------------------------

def _vigencia_de_calibracion(proxima, corte):
    """La situación de la calibración de un equipo al corte, según la fecha de su próxima calibración."""
    if not proxima:
        return 'Sin programar'
    if proxima < corte:
        return 'Vencida'
    return 'Por vencer' if proxima <= corte + timedelta(days=DIAS_DE_AVISO_DE_CALIBRACION) else 'Vigente'


def reporte_calibracion(unit, start_date, end_date, state='', search=''):
    """Un equipo activo por fila: los que tienen fecha de calibración o una orden de calibración en el rango.

    Las fechas de calibración son de cada equipo físico (las completa la orden de calibración al terminarse).
    Las órdenes son las de mantenimiento de tipo calibración programadas, iniciadas o terminadas en el rango,
    sin las canceladas. Respaldo: el certificado del equipo o, si no lo tiene, el informe de la última orden.
    """
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    from apps.recursos.models.mantenimiento import MantenimientoEquipo

    buscar = _buscar(search)
    corte = min(end_date, timezone.localdate())
    periodo = (start_date, end_date)
    # Un equipo dado de baja después del corte todavía estaba en el inventario de ese corte.
    equipos = (equipos_del_alcance(unit).filter(Q(activa=True, fecha_baja__isnull=True) | Q(fecha_baja__gt=corte))
               .select_related('equipo').order_by('codigo_unidad', 'pk'))
    ordenes = defaultdict(list)
    for orden in (MantenimientoEquipo.objects
                  .filter(Q(unidad=unit) | Q(unidad__isnull=True, equipo__in=equipos_del_alcance(unit).values('pk')))
                  .filter(Q(fecha_programada__date__range=periodo) | Q(fecha_inicio__date__range=periodo)
                          | Q(fecha_fin__date__range=periodo))
                  .filter(tipo='calibracion').exclude(estado='cancelado').order_by('fecha_programada', 'pk')):
        ordenes[orden.equipo_id].append(orden)
    filas, vigencias = [], Counter()
    for equipo in equipos:
        modelo, suyas = equipo.equipo, ordenes[equipo.pk]
        if not (equipo.ultima_calibracion or equipo.proxima_calibracion or suyas):
            continue
        vigencia = _vigencia_de_calibracion(equipo.proxima_calibracion, corte)
        completadas = sum(orden.estado == 'completado' for orden in suyas)
        cuantas = '0'
        if suyas:
            cuantas = f'{len(suyas)} ({", ".join(orden.codigo for orden in suyas)})'
            if completadas != len(suyas):
                cuantas += f' · completadas: {completadas}'
        # El respaldo es el certificado del equipo o, si no hay, el informe de la calibración más reciente del rango.
        con_informe = next((orden for orden in reversed(suyas) if orden.informe), None)
        if equipo.certificado_calibracion:
            respaldo = f'Certificado: {_archivo(equipo.certificado_calibracion)}'
        elif con_informe:
            respaldo = f'Informe de {con_informe.codigo}: {_archivo(con_informe.informe)}'
        else:
            respaldo = SIN_RESPALDO
        fila = [
            f'{equipo.codigo_unidad} · {_texto(modelo.nombre, 120)}',
            _fecha(equipo.ultima_calibracion), _fecha(equipo.proxima_calibracion), vigencia, cuantas, respaldo,
        ]
        if not _contiene(buscar, *fila):
            continue
        filas.append(fila)
        vigencias[vigencia] += 1
    return _documento(
        ['Código / nombre', 'Última calibración', 'Próxima calibración', 'Vigencia al corte',
         'Calibraciones del período', 'Respaldo'], filas,
        [('Equipos con calibración registrada', len(filas)), ('Vigentes', vigencias['Vigente']),
         (f'Por vencer en {DIAS_DE_AVISO_DE_CALIBRACION} días', vigencias['Por vencer']),
         ('Vencidas', vigencias['Vencida']), ('Sin programar', vigencias['Sin programar'])],
        vacio='Ningún equipo activo tiene fechas de calibración ni órdenes de calibración en el período.',
        notas=[f'Vigencia al {_fecha(corte)}. «Por vencer» es la calibración que vence en los '
               f'{DIAS_DE_AVISO_DE_CALIBRACION} días siguientes; «sin programar», el equipo sin próxima calibración.'])


# -- sustancias sujetas a control ----------------------------------------------------------------

def reporte_sustancias(unit, start_date, end_date, state='', search=''):
    """Los insumos activos marcados como sustancia sujeta a control: autorización, existencia, lotes y ficha."""
    from apps.recursos.models.consumibles import Consumible, LoteConsumible

    buscar = _buscar(search)
    hoy = timezone.localdate()
    articulos = list(Consumible.objects.filter(unidad=unit, activo=True, sustancia_controlada=True).order_by('codigo'))
    lotes = defaultdict(list)
    for lote in (LoteConsumible.objects.filter(consumible__in=articulos, cantidad_actual__gt=0)
                 .select_related('equipo_en_uso').order_by('fecha_vencimiento', 'codigo')):
        lotes[lote.consumible_id].append(lote)

    def vencimiento(dia):
        if not dia:
            return 'Sin vencimiento registrado'
        return _fecha(dia) + (' · vencido' if dia < hoy else '')

    filas, detalle, sin_autorizacion = [], [], 0
    for articulo in articulos:
        suyos = lotes[articulo.pk]
        autorizacion = (articulo.autorizacion_control or '').strip()
        proximo = min((lote.fecha_vencimiento for lote in suyos if lote.fecha_vencimiento),
                      default=articulo.fecha_vencimiento)
        nombre = f'{articulo.codigo} · {_texto(articulo.nombre, 120)}'
        fila = [
            nombre, articulo.get_clasificacion_display(), _texto(autorizacion) if autorizacion else SIN_AUTORIZACION,
            _cantidad(articulo.stock_total, articulo.unidad_medida), len(suyos), vencimiento(proximo),
            _archivo(articulo.ficha_tecnica) or 'Sin ficha registrada',
        ]
        if not _contiene(buscar, *fila, *[lote.codigo for lote in suyos]):
            continue
        filas.append(fila)
        sin_autorizacion += not autorizacion
        detalle.extend([nombre, _texto(lote.codigo), _cantidad(lote.cantidad_actual, articulo.unidad_medida),
                        vencimiento(lote.fecha_vencimiento), _texto(lote.ubicacion_completa, 120),
                        lote.get_estado_display()] for lote in suyos)
    return _documento(
        ['Código / nombre', 'Clasificación', 'Autorización o licencia', 'Existencia', 'Lotes con saldo',
         'Vencimiento más próximo', 'Ficha de seguridad'], filas,
        [('Sustancias sujetas a control', len(filas)), (SIN_AUTORIZACION, sin_autorizacion)],
        vacio='La unidad no tiene sustancias sujetas a control en su inventario.', notas=[ESTADO_ACTUAL],
        tablas=[dict(titulo='Lotes con saldo de las sustancias sujetas a control',
                     headers=['Sustancia', 'Lote', 'Cantidad', 'Vencimiento', 'Ubicación', 'Estado del lote'],
                     rows=detalle, vacio='Ninguna sustancia sujeta a control tiene lotes con saldo.')])


# -- personal --------------------------------------------------------------------------------------

def reporte_personal(unit, start_date, end_date, state='', search=''):
    """Los responsables activos de la unidad, con su formación y el acto con que fueron designados."""
    from apps.gestion_unidades.models.espacios import ResponsableUnidad

    buscar = _buscar(search)
    filas, designados, formados = [], 0, 0
    for persona in (ResponsableUnidad.objects.filter(unidad=unit, activo=True).select_related('usuario', 'unidad')
                    .order_by('orden', 'nombre', 'pk')):
        formacion, acto = (persona.formacion or '').strip(), (persona.acto_designacion or '').strip()
        if acto or persona.fecha_designacion:
            designacion = (f'{_texto(acto, 200) if acto else "Acto sin registrar"} · '
                           f'{_fecha(persona.fecha_designacion) if persona.fecha_designacion else "fecha sin registrar"}')
        else:
            designacion = SIN_REGISTRAR
        horario = (persona.horario_atencion or '').strip()
        fila = [
            _texto(persona.nombre_publico, 160),
            persona.get_rol_display() + (' · responsable de la unidad' if persona.es_administrador_principal else ''),
            _texto(formacion, 200) if formacion else SIN_REGISTRAR, designacion,
            _texto(horario, 120) if horario else SIN_REGISTRAR,
        ]
        if not _contiene(buscar, *fila):
            continue
        filas.append(fila)
        designados += bool(acto)
        formados += bool(formacion)
    return _documento(
        ['Nombre', 'Rol', 'Formación', 'Designación', 'Horario de atención'], filas,
        [('Personas', len(filas)), ('Con designación registrada', designados),
         ('Con formación registrada', formados)],
        vacio='La unidad no tiene personal registrado.', notas=[ESTADO_ACTUAL])


REPORTES_DE_RESPALDO = {
    'capacitacion': reporte_capacitacion, 'calibracion': reporte_calibracion, 'sustancias': reporte_sustancias,
    'personal': reporte_personal, 'simulacros': reporte_simulacros,
}
