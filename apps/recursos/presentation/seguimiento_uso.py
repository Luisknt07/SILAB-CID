"""Seguimiento de uso por fechas naturales y compromisos explícitos del plan."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import unescape

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import strip_tags

from apps.recursos.presentation.capacidad_uso import dias_del_tramo, precargar_uso_unidad
from apps.recursos.presentation.utilizacion import calculate_unit_utilization


def _numero(valor):
    if isinstance(valor, bool):
        raise ValueError
    try:
        texto = str(valor).strip().replace(',', '.')
        if len(texto) > 64:
            raise ValueError
        numero = Decimal(texto)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError from error
    if not numero.is_finite() or numero < 0 or numero > Decimal('1000000'):
        raise ValueError
    return numero


def normalizar_presupuesto_uso(presupuesto, inicio, fin, *, estricto=False):
    """Suma horas mensuales declaradas; nunca inventa cuotas semanales.

    Se admite el total anterior sin distribución para informar únicamente el
    cumplimiento del tramo completo. El total redundante debe concordar con
    los meses cuando ambos se aportan.
    """
    original = presupuesto if isinstance(presupuesto, dict) else {}
    horas_por_mes, errores = {}, []
    fundamento = str(original.get('justificacion') or original.get('fundamento') or '').strip()
    permitidos = {d.month for d in dias_del_tramo(inicio, fin)}
    mensual = original.get('horas_por_mes')
    if mensual is not None and not isinstance(mensual, dict):
        errores.append('Distribuye las horas por mes mediante valores numéricos válidos.')
    for clave, valor in (mensual.items() if isinstance(mensual, dict) else ()):
        try:
            mes = int(clave)
            if str(mes) != str(clave).strip() or mes not in permitidos:
                raise ValueError
            cantidad = _numero(valor)
        except (ValueError, TypeError):
            errores.append(f'El mes {clave} no pertenece al tramo o sus horas no son válidas.')
            continue
        horas_por_mes[str(mes)] = format(cantidad.normalize(), 'f')
    total = sum((Decimal(v) for v in horas_por_mes.values()), Decimal(0)) if horas_por_mes else None
    declarado = original.get('horas_comprometidas')
    if declarado not in (None, ''):
        try:
            numero = _numero(declarado)
            if total is not None and numero != total:
                errores.append('Las horas totales deben coincidir con la suma mensual del plan.')
            elif total is None:
                total = numero
        except ValueError:
            errores.append('Indica un total de horas válido y no negativo.')
    if total is not None and not unescape(strip_tags(fundamento)).replace('\xa0', '').strip():
        errores.append('Explica el fundamento del compromiso de uso frente a la capacidad y actividades previstas.')
    if estricto and errores:
        raise ValidationError(errores)
    return dict(horas_comprometidas=format(total.normalize(), 'f') if total is not None else '',
        horas_por_mes=horas_por_mes, justificacion=fundamento,
        definido=total is not None and not errores, distribuido=bool(horas_por_mes), errores=errores)


def _lectura_presupuesto(presupuesto, medida, inicio, fin, hoy, *, parcial=False):
    normalizado = normalizar_presupuesto_uso(presupuesto, inicio, fin)
    objetivo = Decimal(normalizado['horas_comprometidas'] or '0')
    realizado = Decimal(str(medida['occupied_hours']))
    capacidad = Decimal(str(medida['available_hours_period']))
    alertas = list(normalizado['errores'])
    if normalizado['definido'] and objetivo == 0:
        alertas.append('Un compromiso de cero horas no acredita aprovechamiento; requiere justificar el alcance y seguimiento.')
    sin_jornada = any(not d['jornada_conocida'] for d in medida['daily'])
    if normalizado['definido'] and objetivo > capacidad and not sin_jornada:
        alertas.append('Las horas comprometidas superan la jornada declarada del tramo; revisa la programación o la disponibilidad.')
    cumplimiento = min(Decimal(100), realizado * 100 / objetivo) if objetivo > 0 and normalizado['definido'] else None
    dentro = hoy <= fin
    estado = ('Sin meta de uso' if not normalizado['definido'] else
              'Alcance por justificar' if not objetivo else
              'Por verificar' if medida['pending'] else
              'Meta alcanzada' if cumplimiento == 100 else
              'En curso' if dentro else 'Compromiso no alcanzado')
    return dict(normalizado, horas_realizadas=float(realizado), capacidad_horas=float(capacidad),
        cumplimiento=round(float(cumplimiento), 2) if cumplimiento is not None else None,
        excedente=float(max(Decimal(0), realizado - objetivo)) if objetivo else None,
        excede_capacidad=bool(objetivo > capacidad and not sin_jornada), capacidad_pendiente=sin_jornada,
        dentro_plazo=dentro, parcial=parcial, estado=estado, alertas=alertas,
        pendiente_verificacion=medida['pending'],
        acredita_cumplimiento_institucional=False)


def _tramos_mensuales(inicio, fin):
    actual = inicio
    while actual <= fin:
        hasta = min(fin, date(actual.year, actual.month, monthrange(actual.year, actual.month)[1]))
        yield actual, hasta
        actual = hasta + timedelta(days=1)


def seguimiento_uso_unidad(unidad, inicio, fin, *, presupuesto=None, hoy=None, periodo=None, context=None):
    """Una precarga sirve a semestre, semanas y meses; sin escrituras ni cuotas de ocupación."""
    hoy = hoy or timezone.localdate()
    contexto = context or precargar_uso_unidad(unidad, inicio, fin, periodo=periodo)
    medida = calculate_unit_utilization(unidad, inicio, fin, period=periodo, context=contexto, hoy=hoy)
    compromiso = _lectura_presupuesto(presupuesto, medida, inicio, fin, hoy)
    semanas, meses = [], []
    desde = inicio
    while desde <= fin:
        hasta = min(fin, desde + timedelta(days=6 - desde.weekday()))
        lectura = calculate_unit_utilization(unidad, desde, hasta, period=periodo, context=contexto, hoy=hoy)
        semanas.append(dict(inicio=desde, fin=hasta, etiqueta=f'{desde:%d/%m} – {hasta:%d/%m}',
            medida=lectura, presupuesto=None, meta=None,
            nota='Seguimiento semanal informativo; no se prorratea una cuota mensual sin agenda comprometida.'))
        desde = hasta + timedelta(days=1)
    for desde, hasta in _tramos_mensuales(inicio, fin):
        lectura = calculate_unit_utilization(unidad, desde, hasta, period=periodo, context=contexto, hoy=hoy)
        valor = compromiso['horas_por_mes'].get(str(desde.month)) if compromiso['definido'] else None
        mensual = None if valor is None else _lectura_presupuesto(dict(horas_comprometidas=valor,
            justificacion=compromiso['justificacion']), lectura, desde, hasta, hoy, parcial=True)
        meses.append(dict(inicio=desde, fin=hasta, etiqueta=f'{desde:%m/%Y}', medida=lectura,
            presupuesto=mensual, meta=valor))
    # No se promedian porcentajes: la medida principal agrega duraciones y
    # capacidad del tramo completo, incluso cuando la capacidad cambia.
    alertas = [*medida['alertas'], *[dict(codigo='presupuesto_uso', mensaje=m, cantidad=1, registros=[])
                                 for m in compromiso['alertas']]]
    return dict(semestre=medida, semanas=semanas, meses=meses, presupuesto=compromiso,
        fuentes=medida['fuentes'], alertas=alertas, inicio=inicio, fin=fin, corte=min(fin, hoy))
