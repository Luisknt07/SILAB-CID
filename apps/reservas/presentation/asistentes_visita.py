"""Valida la tabla de visitantes sin crear cuentas para sus integrantes."""

import json

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from apps.reservas.models.visitas import AsistenteVisita


def asistentes_desde_json(texto):
    if not isinstance(texto, str) or len(texto) > 200000:
        raise ValidationError('La lista de asistentes excede el tamaño permitido.')
    try:
        datos = json.loads(texto)
    except (TypeError, ValueError) as error:
        raise ValidationError('La tabla de asistentes no tiene un formato válido.') from error
    if not isinstance(datos, list) or len(datos) > 200:
        raise ValidationError('La tabla admite hasta 200 asistentes por solicitud.')
    roles = dict(AsistenteVisita.ROLES)
    limites = {'documento': 40, 'nombre': 150, 'rol': 20, 'telefono': 30, 'correo': 254}
    filas, documentos = [], set()
    for indice, dato in enumerate(datos, 1):
        if not isinstance(dato, dict):
            raise ValidationError(f'Revisa el formato del asistente de la fila {indice}.')
        fila = {}
        for campo, limite in limites.items():
            valor = dato.get(campo, '')
            if not isinstance(valor, str) or len(valor.strip()) > limite:
                raise ValidationError(f'Revisa {campo} en la fila {indice}: admite hasta {limite} caracteres.')
            fila[campo] = valor.strip()
        if not any(fila.values()):
            continue
        if not fila['nombre']:
            raise ValidationError(f'Escribe los nombres completos del asistente de la fila {indice}.')
        if fila['rol'] not in roles:
            raise ValidationError(f'Selecciona el rol del asistente de la fila {indice}.')
        if fila['correo']:
            try:
                validate_email(fila['correo'])
            except ValidationError as error:
                raise ValidationError(f'Revisa el correo del asistente de la fila {indice}.') from error
        documento = fila['documento'].casefold()
        if documento and documento in documentos:
            raise ValidationError(f'La cédula o documento de la fila {indice} ya está en la lista.')
        if documento:
            documentos.add(documento)
        filas.append(fila)
    return filas
