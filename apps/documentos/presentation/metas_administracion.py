"""Las metas del período en una sola tabla: cada indicador por tipo de unidad, editable por Dirección.

El valor inicial de cada meta está en el catálogo de actividades del plan. Lo que Dirección escribe
aquí se guarda como referencia (`ReferenciaIndicadorUnidad`) y lo sustituye en los planes que aún no
se envían; los enviados conservan las metas con las que se firmaron.
"""
from types import SimpleNamespace

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.documentos.models.referencias_indicadores import PORCENTUALES, TIPOS, ReferenciaIndicadorUnidad

from .metas_plan import ANEXOS_AUTOMATICOS, regla_minimo
from .politica_metas_unidades import SEGUN_PROGRAMACION

GRUPOS = (
    ('institucional', 'Obligatorias para toda unidad'),
    ('tipo', 'Según el tipo de unidad'),
    ('programacion', 'Cuando la unidad las programa'),
)
# La meta del plan es el mayor valor entre este mínimo y lo que la unidad programó en su agenda.
SUBEN_CON_LA_AGENDA = frozenset({'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS'})
# Solo los Centros I+D las usan; no son un tipo de unidad de esta tabla.
FUERA_DE_LA_TABLA = frozenset({'PROYECTOS', 'PUBLICACIONES'}) | ANEXOS_AUTOMATICOS


def _actividades_de(tipo):
    """El catálogo que el plan propone a ese tipo de unidad, sin referencias aplicadas."""
    from .expediente_redaccion import actividades_para
    return {a.codigo: a for a in actividades_para(SimpleNamespace(codigo_base=tipo))}


def _campo(tipo, codigo):
    return f'meta__{tipo}__{codigo}'


def _celdas():
    """Cada combinación tipo de unidad × indicador que existe en el plan, con su valor inicial y el vigente."""
    from .expediente_redaccion import ACTIVIDADES_PLAN
    por_tipo = {tipo: _actividades_de(tipo) for tipo, _ in TIPOS}
    referencias = {(r.tipo_unidad, r.codigo): r
                   for r in ReferenciaIndicadorUnidad.objects.filter(nivel_capacidad='')}
    filas = []
    for base in ACTIVIDADES_PLAN:
        if base.codigo in FUERA_DE_LA_TABLA:
            continue
        celdas = []
        for tipo, nombre_tipo in TIPOS:
            actividad = por_tipo[tipo].get(base.codigo)
            if actividad is None:
                celdas.append(dict(tipo=tipo, nombre_tipo=nombre_tipo, aplica=False))
                continue
            regla = regla_minimo(actividad)
            referencia = referencias.get((tipo, base.codigo))
            activa = referencia if referencia is not None and referencia.activo else None
            inicial = int(regla['valor']) if regla else None
            celdas.append(dict(
                tipo=tipo, nombre_tipo=nombre_tipo, aplica=True, campo=_campo(tipo, base.codigo),
                actividad=actividad, referencia=referencia, activa=activa, inicial=inicial,
                inicial_texto=str(inicial) if inicial is not None else actividad.minimo,
                vigente=activa.valor if activa else inicial,
                segun_programacion=actividad.segun_programacion and base.codigo not in SEGUN_PROGRAMACION))
        if not any(c['aplica'] for c in celdas):
            continue
        primera = next(c['actividad'] for c in celdas if c['aplica'])
        filas.append(dict(
            codigo=base.codigo, nombre=primera.nombre, indicador=primera.indicador,
            porcentaje=base.codigo in PORCENTUALES, sube_con_la_agenda=base.codigo in SUBEN_CON_LA_AGENDA,
            grupo=('programacion' if base.codigo in SEGUN_PROGRAMACION else
                   'institucional' if base.obligatoria else 'tipo'),
            celdas=celdas))
    # El mismo orden con que la planificación lista sus indicadores; lo demás, como en el catálogo.
    from .expediente_redaccion import ORDEN_PLAN
    return sorted(filas, key=lambda f: ORDEN_PLAN.index(f['codigo']) if f['codigo'] in ORDEN_PLAN
                  else len(ORDEN_PLAN))


def tabla_de_metas(enviado=None):
    """La tabla para la pantalla. Con `enviado`, conserva lo que la persona escribió y no se pudo guardar."""
    filas = _celdas()
    for fila in filas:
        for celda in fila['celdas']:
            if not celda['aplica']:
                continue
            vigente = celda['vigente']
            celda['valor'] = (enviado.get(celda['campo'], '') if enviado is not None
                              else '' if vigente is None else str(vigente))
            celda['configurada'] = celda['activa'] is not None
            # Solo se señala lo que Dirección dejó distinto del valor inicial.
            celda['ajustada'] = celda['configurada'] and vigente != celda['inicial']
            celda['sin_numero'] = celda['inicial'] is None
    return dict(tipos=TIPOS, total=sum(c['aplica'] for f in filas for c in f['celdas']),
                ajustadas=sum(c['aplica'] and c['ajustada'] for f in filas for c in f['celdas']),
                grupos=[dict(codigo=codigo, nombre=nombre, filas=[f for f in filas if f['grupo'] == codigo])
                        for codigo, nombre in GRUPOS])


def guardar_metas(enviado, usuario):
    """Aplica solo lo que cambió y devuelve la lista de cambios. Vacío vuelve al valor inicial del sistema."""
    fundamento = str(enviado.get('fundamento', '')).strip()
    errores, cambios = [], []
    for fila in _celdas():
        for celda in fila['celdas']:
            # Una casilla que no llegó en el envío no se toca: solo se restablece la que llegó vacía.
            if not celda['aplica'] or celda['campo'] not in enviado:
                continue
            etiqueta = f'{celda["nombre_tipo"]} · {fila["nombre"]}'
            crudo = str(enviado.get(celda['campo'], '')).strip()
            if not crudo:
                if celda['activa'] is not None:
                    cambios.append(dict(celda=celda, fila=fila, etiqueta=etiqueta, valor=None))
                continue
            maximo = 100 if fila['porcentaje'] else 10000
            if not crudo.isdigit() or not 1 <= int(crudo) <= maximo:
                errores.append(f'{etiqueta}: escribe un número entero entre 1 y {maximo}'
                               f'{" (es un porcentaje)" if fila["porcentaje"] else ""}.')
                continue
            if int(crudo) != celda['vigente']:
                cambios.append(dict(celda=celda, fila=fila, etiqueta=etiqueta, valor=int(crudo)))
    if cambios and not fundamento:
        errores.append('Escribe el fundamento del cambio: la decisión o el criterio que lo sustenta.')
    if errores:
        raise ValidationError(errores)
    descripciones = []
    with transaction.atomic():
        for cambio in cambios:
            celda, fila, valor = cambio['celda'], cambio['fila'], cambio['valor']
            unidad = ' %' if fila['porcentaje'] else ''
            anterior = celda['inicial_texto'] if celda['vigente'] is None else f'{celda["vigente"]}{unidad}'
            referencia = celda['referencia']
            if valor is None:
                referencia.activo = False
                nuevo = f'{celda["inicial_texto"]}{unidad if celda["inicial"] is not None else ""} (valor inicial)'
            else:
                if referencia is None:
                    referencia = ReferenciaIndicadorUnidad(tipo_unidad=celda['tipo'], codigo=fila['codigo'],
                                                           nivel_capacidad='')
                referencia.valor, referencia.activo = valor, True
                nuevo = f'{valor}{unidad}'
            referencia.fundamento, referencia.actualizado_por = fundamento, usuario
            creada = referencia.pk is None
            referencia.full_clean()
            referencia.save()
            descripcion = f'{cambio["etiqueta"]}: {anterior} → {nuevo}'
            LogEntry.objects.log_actions(usuario.pk, [referencia], ADDITION if creada else CHANGE, single_object=True,
                                         change_message=f'Metas del período. {descripcion}. Fundamento: {fundamento}')
            descripciones.append(descripcion)
    return descripciones
