"""Compromiso explícito de horas de uso; no presupone una ocupación universal."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from apps.reservas.presentation.guia_html import sanear


def meses_entre(inicio, fin):
    actual = date(inicio.year, inicio.month, 1)
    while actual <= fin:
        yield actual.month
        actual = date(actual.year + (actual.month == 12), actual.month % 12 + 1, 1)


def leer_presupuesto(post, inicio, fin):
    """El total nunca se acepta del cliente; se suma desde los meses del tramo."""
    mensual = {}
    for mes in meses_entre(inicio, fin):
        texto = post.get(f'uso_horas__{mes}', '').strip()
        if not texto:
            continue
        try:
            valor = Decimal(texto.replace(',', '.'))
            maximo = Decimal(monthrange(inicio.year, mes)[1] * 24)
            if not valor.is_finite() or valor < 0 or valor > maximo or valor.as_tuple().exponent < -2:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            raise ValidationError('Indica horas mensuales válidas, con hasta dos decimales y dentro del tiempo del mes.') from None
        mensual[str(mes)] = format(valor, 'f')
    justificacion = sanear(post.get('uso_justificacion', ''), 'texto')[0]
    return dict(horas_por_mes=mensual, horas_comprometidas=format(sum((Decimal(v) for v in mensual.values()), Decimal(0)), 'f'),
        justificacion=justificacion, version=1, inicio=inicio.isoformat(), fin=fin.isoformat())


def datos_presupuesto(valor, inicio, fin):
    valor = valor if isinstance(valor, dict) else {}
    mensual = valor.get('horas_por_mes') or {}
    nombres = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
               'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    return dict(valor=valor, meses=[dict(numero=m, nombre=nombres[m], horas=mensual.get(str(m), ''))
        for m in meses_entre(inicio, fin)], total=valor.get('horas_comprometidas', ''),
        justificacion=valor.get('justificacion', ''))


def comprobar_presupuesto(valor, inicio, fin, *, unidad=None):
    problemas = []
    valor = valor if isinstance(valor, dict) else {}
    mensual = valor.get('horas_por_mes') or {}
    esperados = {str(m) for m in meses_entre(inicio, fin)}
    lectura = dict(horas_comprometidas=None, horas_por_mes=mensual)
    if not isinstance(mensual, dict) or set(mensual) != esperados:
        problemas.append(('uso_sin_programacion', 'Programa las horas de cada mes del semestre; indica 0 y explica los meses sin actividad.', 'bloqueo'))
        return problemas, lectura
    try:
        valores = [Decimal(str(v)) for v in mensual.values()]
        total = Decimal(str(valor.get('horas_comprometidas', '')))
        if (any(not v.is_finite() or v < 0 for v in valores) or not total.is_finite()
                or total != sum(valores, Decimal(0))):
            raise InvalidOperation
        for mes, horas in mensual.items():
            if Decimal(str(horas)) > monthrange(inicio.year, int(mes))[1] * 24:
                raise InvalidOperation
    except (InvalidOperation, ValueError, TypeError):
        problemas.append(('uso_programacion_invalida', 'El total de horas debe concordar con meses válidos y cantidades no negativas.', 'bloqueo'))
        return problemas, lectura
    lectura['horas_comprometidas'] = str(total)
    if not strip_tags(str(valor.get('justificacion') or '')).strip():
        problemas.append(('uso_sin_fundamento', 'Explica las actividades, horarios, personal y recursos que sustentan las horas comprometidas.', 'bloqueo'))
    if total == 0:
        problemas.append(('uso_cero_por_revisar', 'El semestre no programa uso. Justifica la puesta en funcionamiento, suspensión o limitación para revisión; cero no acredita aprovechamiento.', 'revision'))
    if unidad is not None and total > 0:
        from apps.recursos.presentation.utilizacion import calculate_unit_utilization
        medida = calculate_unit_utilization(unidad, inicio, fin, hoy=fin)
        jornadas = medida['daily']
        conocida = bool(jornadas) and all(d['jornada_conocida'] for d in jornadas)
        capacidad_conocida = conocida and all(d['capacidad_conocida'] and d['capacidad_respaldada']
            for d in jornadas if d['disponible_segundos'])
        lectura.update(capacidad_horas=medida['available_hours_period'], capacidad_confirmada=capacidad_conocida,
            fuentes_capacidad=medida['fuentes'])
        if not capacidad_conocida:
            problemas.append(('uso_capacidad_por_confirmar', 'Declara jornadas y capacidad operativa con su fundamento, incluidos los días fuera de clases. La capacidad incompleta requiere revisión.', 'revision'))
        if conocida:
            for mes, objetivo in mensual.items():
                disponible = sum(d['disponible_segundos'] for d in jornadas if d['fecha'].month == int(mes)) / 3600
                if Decimal(str(objetivo)) > Decimal(str(round(disponible, 4))):
                    problemas.append(('uso_supera_capacidad', f'El mes {mes} compromete más horas que su jornada disponible; revisa horarios, bloqueos y programación.', 'bloqueo'))
    return problemas, lectura
