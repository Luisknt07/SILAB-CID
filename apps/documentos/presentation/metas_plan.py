"""Mínimos del catálogo y metas del período, validados también en el servidor."""
import re
from decimal import Decimal

from django.core.exceptions import ValidationError


def regla_minimo(actividad):
    texto = actividad.minimo.strip()
    numero = re.fullmatch(r'(?:≥|>=)?\s*(\d+(?:[.,]\d+)?)\s*(%.*|por\s+\w+)?', texto)
    if not numero:
        return None
    valor = Decimal(numero[1].replace(',', '.'))
    porcentaje = bool(numero[2] and numero[2].startswith('%'))
    return dict(valor=valor, porcentaje=porcentaje)


def meta_con_minimo(actividad, texto):
    """Vacío usa el mínimo existente; una meta distinta debe igualarlo o superarlo."""
    texto = str(texto or '').strip()
    regla = regla_minimo(actividad)
    if not regla:
        return texto
    if not texto or texto == actividad.minimo:
        return actividad.minimo
    patron = (r'(?:≥|>=)?\s*(\d+(?:[.,]\d+)?)\s*(?:%.*)?' if regla['porcentaje'] else
              r'(?:≥|>=|al menos)?\s*(\d+(?:[.,]\d+)?)\s*(?:por\s+\w+)?')
    numero = re.fullmatch(patron, texto, re.I)
    if not numero:
        raise ValidationError(f'{actividad.nombre}: indica una meta numérica; mínimo {actividad.minimo}.')
    valor = Decimal(numero[1].replace(',', '.'))
    if valor < regla['valor']:
        raise ValidationError(f'{actividad.nombre}: la meta no puede ser menor al mínimo de referencia del plan '
                              f'({actividad.minimo}).')
    if regla['porcentaje'] and valor > 100:
        raise ValidationError(f'{actividad.nombre}: la meta porcentual no puede superar 100 %.')
    if not regla['porcentaje'] and valor != valor.to_integral_value():
        raise ValidationError(f'{actividad.nombre}: la meta debe ser una cantidad entera.')
    return f'{valor.normalize():f}' + (' %' if regla['porcentaje'] else '')


ANEXOS_AUTOMATICOS = frozenset(('PRESTAMOS', 'EQUIPAMIENTO', 'INSUMOS', 'MEJORA'))


def obligatoria_por_tipo(actividad, version=2):
    """Exige los mínimos numéricos del catálogo aplicable, sin inventar cupos de demanda."""
    if getattr(actividad, 'segun_programacion', False):
        return False
    regla = regla_minimo(actividad)
    if version == 1:
        if actividad.codigo == 'PRACTICAS-PLAN':
            return False
        return bool(actividad.tipos and regla and not regla['porcentaje'])
    return bool(regla)


def control_meta(actividad, meta, aplica, *, proponer=True):
    """Datos del control HTML, sin modificar lo que está guardado en el plan."""
    regla = regla_minimo(actividad)
    datos = dict(numerica=bool(regla), valor=meta, error='')
    if not regla:
        return datos
    datos.update(minimo=f"{regla['valor']:f}", porcentaje=regla['porcentaje'],
                 fija=regla['porcentaje'] and regla['valor'] == 100)
    texto = str(meta or '').strip()
    if not texto and aplica:
        texto = actividad.minimo
    numero = re.search(r'\d+(?:[.,]\d+)?', texto)
    datos['valor'] = numero[0].replace(',', '.') if numero else ''
    if aplica:
        try:
            meta_con_minimo(actividad, meta)
        except ValidationError as error:
            datos['error'] = ' '.join(error.messages)
            if proponer and numero and Decimal(datos['valor']) < regla['valor']:
                datos.update(valor=datos['minimo'], ajustada=True,
                             error=f'La meta guardada era inferior al mínimo. Se propone {actividad.minimo}; '
                                   'guarda para aplicar este compromiso.')
    return datos
