"""Referencias operativas proporcionales, propuestas al aprobar cada plan.

No son cuotas emitidas por la Universidad ni alteran compromisos firmados.
La dotación orienta una propuesta; Dirección decide su pertinencia al revisar
el diagnóstico, los recursos y el cronograma de la unidad.
"""
import re
from dataclasses import replace
from datetime import timedelta
from math import ceil


VERSION_POLITICA = 3
MINIMOS = {'PRACTICAS': '≥ 2 por período', 'PRACTICAS-PLAN': '≥ 2 por período',
           'GUIAS': '≥ 1 por período', 'PRODUCCION': '≥ 2 por período',
           'ENSAYOS': '≥ 1 por período', 'BOLETINES': '≥ 1 por período',
           'DATOS-ACTUALIZADOS': '≥ 2 por período', 'EVENTOS': '≥ 1 por período',
           'CONTROL-CALIDAD': '100 % de lotes finalizados'}
SEGUN_PROGRAMACION = frozenset({'INVESTIGACION', 'TRANSFERENCIA', 'SERVICIOS'})


def capacidad_de(unidad, inicio=None, fin=None):
    """Capacidad declarada y tiempo efectivo; nunca acredita funcionalidad por contar bienes."""
    from django.db.models import Q
    from django.utils import timezone
    from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.recursos.models.software import SoftwareDisponible
    inicio = inicio or timezone.localdate()
    fin = fin or inicio + timedelta(days=119)
    apertura = getattr(unidad, 'fecha_inicio', None)
    efectivo = max(inicio, apertura) if apertura else inicio
    dias = max(0, (fin - efectivo).days + 1)
    duracion = max(0, (fin - inicio).days + 1)
    asignados = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()
    activos = asignados.filter(activa=True, fecha_baja__isnull=True)
    utilizables = activos.filter(estado_unidad__in=('disponible', 'en_uso'))
    equipos, equipos_utilizables = activos.count(), utilizables.count()
    programas = SoftwareDisponible.objects.filter(unidad=unidad, activo=True)
    software = programas.count()
    software_utilizable = programas.filter(licencias_disponibles__gt=0).filter(
        ~Q(tipo_acceso='instalacion') | Q(equipos_instalados__in=utilizables)).distinct().count()
    areas = EspacioReservable.objects.filter(unidad=unidad, activo=True)
    espacios = areas.count()
    espacios_generales = areas.filter(politica_reserva__in=('general', 'mixto')).count()
    personas = set(ResponsableUnidad.objects.filter(unidad=unidad, activo=True,
        usuario__is_active=True).values_list('usuario_id', flat=True))
    if getattr(unidad, 'administrador_id', None) and unidad.administrador.is_active:
        personas.add(unidad.administrador_id)
    personal = len(personas)
    reciente = bool(apertura and apertura <= fin and (inicio - apertura).days < 120)
    recursos = equipos_utilizables + software_utilizable
    operacion = bool(personal and espacios and (recursos or espacios_generales))
    nivel = 'inicial' if reciente or not personal or not recursos else (
        'consolidada' if recursos >= 3 and personal >= 2 else 'limitada')
    tardia = bool(apertura and inicio < apertura <= fin and dias <= 60)
    minimo = 0 if not dias else 1 if tardia and operacion else 2
    propuesta = {'inicial': 2, 'limitada': 4, 'consolidada': 6}[nivel]
    from .referencias_indicadores import referencias_para, referencia
    referencias = {'referencias_indicadores': referencias_para(unidad)}
    base_practicas = referencia(referencias, 'PRACTICAS')
    propuesta_practicas = referencia(referencias, 'PRACTICAS', nivel)
    if dias and base_practicas:
        minimo = min(base_practicas['valor'], 1) if tardia and operacion else base_practicas['valor']
    if propuesta_practicas:
        propuesta = propuesta_practicas['valor']
    recomendadas = max(minimo, ceil(propuesta * min(dias, 120) / 120)) if dias else 0
    return dict(version=VERSION_POLITICA, nivel=nivel, fecha=inicio.isoformat(), equipos=equipos,
        referencias_indicadores=referencias['referencias_indicadores'],
        software=software, espacios=espacios, personal=personal, apertura_reciente=reciente,
        equipos_registrados=asignados.count(), equipos_utilizables=equipos_utilizables,
        equipos_no_utilizables=equipos - equipos_utilizables, software_utilizable=software_utilizable,
        inicio=inicio.isoformat(), fin=fin.isoformat(), inicio_efectivo=efectivo.isoformat(),
        dias_periodo=duracion, dias_efectivos=dias, apertura_tardia=tardia,
        fuera_periodo=not dias, operacion_posible=operacion,
        practicas_minimas=minimo, practicas_recomendadas=recomendadas,
        requiere_revision=not operacion or tardia or not dias,
        aviso=('Referencia interna de actividad docente, calibrada sobre hasta 120 días y acotada '
               'al tramo del plan; no es una cuota emitida por la Universidad ni aumenta automáticamente '
               'por abarcar seis meses de gestión. Los recursos registrados como utilizables no sustituyen '
               'su verificación funcional y de seguridad. Una apertura tardía o limitación requiere '
               'justificación; no elimina por sí sola la función docente ni cambia compromisos firmados.'))


def actividades_proporcionales(actividades, base, *, funciones=None, capacidad=None):
    """Mínimos del semestre; las funciones opcionales no se convierten en cupos."""
    salida = []
    funciones = set(funciones or ())
    for actividad in actividades:
        codigo = actividad.codigo
        # El observatorio acredita monitoreo, datos y productos analíticos;
        # no necesita reservas de sesiones ni inducciones de laboratorio.
        if base == 'observatorios' and codigo in {'USO', 'SEGURIDAD', 'INSPECCIONES',
                                                  'DESECHOS', 'INSUMOS'}:
            continue
        cambios = {}
        if codigo == 'INSPECCIONES' and base in {'laboratorios', 'plantas_piloto', 'centro_experimental'}:
            cambios['tipos'] = ('laboratorios', 'plantas_piloto', 'centro_experimental')
        if codigo in MINIMOS:
            cambios['minimo'] = MINIMOS[codigo]
        from .referencias_indicadores import referencia
        configurada = referencia(capacidad, codigo)
        if configurada:
            vigente = cambios.get('minimo', actividad.minimo)
            # Una cobertura conserva su redacción («% de las sesiones»); solo cambia el número.
            cambios['minimo'] = (re.sub(r'\d+(?:[.,]\d+)?', str(configurada['valor']), vigente, count=1)
                if '%' in vigente else f'≥ {configurada["valor"]} por período')
        if codigo in {'PRACTICAS', 'PRACTICAS-PLAN'} and isinstance(capacidad, dict):
            # Fuera del período se requiere revisión, no una exención automática.
            piso = capacidad.get('practicas_minimas')
            if configurada and not capacidad.get('apertura_tardia'):
                piso = configurada['valor']
            if type(piso) is int and piso >= 1:
                cambios['minimo'] = f'≥ {piso} por período'
        if codigo in SEGUN_PROGRAMACION:
            cambios['segun_programacion'] = True
        if codigo in {'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS'} and (
                base in {'plantas_piloto', 'centro_experimental'} or funciones and 'docencia' not in funciones):
            cambios['segun_programacion'] = True
        if codigo == 'GUIAS':
            cambios['nombre'] = 'Guías vigentes utilizadas en las prácticas del semestre'
        if codigo == 'ENSAYOS':
            cambios.update(nombre='Ensayos y parcelas con seguimiento del semestre',
                           indicador='Ciclos experimentales con seguimiento y respaldo técnico')
        if codigo == 'MANTENIMIENTO' and base == 'observatorios':
            cambios.update(segun_programacion=True, obligatoria=False)
        salida.append(replace(actividad, **cambios) if cambios else actividad)
    return salida


def propuesta_del_semestre(capacidad, actividad):
    """Una sugerencia editable puede superar el mínimo sin volverlo obligatorio."""
    if actividad.codigo in {'PRACTICAS', 'PRACTICAS-PLAN'}:
        from .referencias_indicadores import referencia
        valor = referencia(capacidad, actividad.codigo, capacidad.get('nivel', ''))
        base = referencia(capacidad, actividad.codigo)
        piso = (base['valor'] if base and not capacidad.get('apertura_tardia')
                else capacidad.get('practicas_minimas', 2))
        if valor:
            return str(max(piso, valor['valor']))
        return str(max(piso, capacidad.get('practicas_recomendadas', 2)))
    return actividad.minimo


def capacidad_archivada(plan):
    valor = plan.get('capacidad')
    return valor if isinstance(valor, dict) and valor.get('version') == VERSION_POLITICA else None


def ficha_indicador(actividad, capacidad=None):
    """Explica la referencia propuesta; no atribuye cuotas internas a la Universidad."""
    capacidad = capacidad if isinstance(capacidad, dict) else {}
    codigo = actividad.codigo
    especificas = {
        'USO': ('Sesiones efectivas registradas / sesiones observadas y conciliadas × 100.',
                'Conciliación independiente que cubra todo el tramo y cierres de atención efectivos.'),
        'SEGURIDAD': ('Usuarios nuevos con inducción vigente / usuarios nuevos identificados × 100.',
                      'Ingresos identificados, primera entrada e inducción vigente; cero nuevos requiere cobertura documentada.'),
        'DESECHOS': ('Partidas con trazabilidad completa / partidas generadas y conciliadas × 100.',
                    'Acta de conciliación y trazabilidad; cero generación debe estar verificada, no se presume 100 %.'),
        'MANTENIMIENTO': ('Intervenciones críticas concluidas con respaldo / intervenciones críticas exigibles × 100.',
                         'Inventario y criticidad revisados, planes, órdenes e informes de equipos e infraestructura.'),
        'INSPECCIONES': ('Meses exigibles con inspección respaldada / meses exigibles desde la apertura × 100.',
                        'Inspecciones verificadas de cada mes; el mes actual no vencido se informa como provisional.'),
        'PRACTICAS-PLAN': ('Prácticas aprobadas y respaldadas / meta comprometida × 100, hasta 100 %.',
                          'Planificación vigente, escenario, responsable, resultado de aprendizaje y guía aplicable.'),
        'PRACTICAS': ('Prácticas ejecutadas y validadas / meta comprometida × 100, hasta 100 %.',
                     'Ejecución ligada a su planificación, asistencia, bitácora y evidencias identificadas.'),
        'CONTROL-CALIDAD': ('Lotes finalizados con control conforme respaldado / lotes finalizados × 100.',
                           'Lotes y controles nativos; sin producción exige justificación verificada.'),
        'INVENTARIO': ('Revisiones integrales verificadas / meta comprometida × 100, hasta 100 %.',
                       'Acta de existencia y condición del inventario aplicable; generar el PDF no acredita revisión.'),
    }
    formula, evidencia = especificas.get(codigo, (
        'Resultados válidos y respaldados / meta comprometida × 100, hasta 100 %.',
        'Registros reales del período, responsables y respaldo verificable de los resultados.'))
    piso = capacidad.get('practicas_minimas', 2)
    regla = (f'Referencia de {piso} prácticas; propuesta de {capacidad.get("practicas_recomendadas", piso)} '
             'según recursos utilizables y días efectivos. Ajustes y limitaciones deben argumentarse.'
             if codigo in {'PRACTICAS', 'PRACTICAS-PLAN'} else
             'Exigible cuando existe un compromiso justificado en la planificación; no hay cuota universal.'
             if codigo in SEGUN_PROGRAMACION or actividad.segun_programacion else
             'Cobertura del universo realmente observado; cero sin respaldo no acredita cumplimiento.'
             if '%' in actividad.minimo else
             f'Referencia operativa propuesta: {actividad.minimo}; se adapta al alcance y compromiso del plan.')
    ficha = dict(codigo=codigo, fuente='Referencia operativa interna; no es una cuota universitaria confirmada.',
        regla=regla, formula=formula, duracion=('Tramo conservado del plan. Los nuevos semestres de gestión '
            'cubren enero–junio o julio–diciembre; la docencia sigue su calendario académico.'),
        frecuencia='Seguimiento al corte; resultado final al cierre del período.', evidencia=evidencia,
        inicio=capacidad.get('inicio', ''), fin=capacidad.get('fin', ''),
        dias_efectivos=capacidad.get('dias_efectivos'),
        ajuste='La propuesta admite metas mayores; un piso excepcional requiere justificación y revisión.')
    ficha.update(titulo=actividad.indicador, pares=[
        ('Origen de la referencia', ficha['fuente']), ('Regla y alcance', regla),
        ('Cálculo', formula), ('Duración', ficha['duracion']),
        ('Cuándo se mide', ficha['frecuencia']), ('Respaldo necesario', evidencia),
        ('Ajuste de la meta', ficha['ajuste']),
    ])
    from .referencias_indicadores import referencia
    configurada = referencia(capacidad, codigo)
    if configurada:
        ficha['pares'].extend([('Fundamento configurado', configurada['fundamento']),
            ('Referencia conservada', f'Registro {configurada["id"]} · {configurada["actualizado_en"]}')])
    if capacidad.get('inicio') and capacidad.get('fin'):
        ficha['pares'].append(('Tramo de la propuesta',
            f"{capacidad['inicio']} – {capacidad['fin']}; {capacidad.get('dias_efectivos', 0)} días efectivos desde "
            f"{capacidad.get('inicio_efectivo', capacidad['inicio'])}."))
    return ficha
