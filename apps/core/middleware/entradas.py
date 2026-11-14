"""Límites estructurales. El saneado HTML y las reglas de negocio pertenecen al dominio."""
import json
import math

from django.http import JsonResponse


def numero_no_finito(_value):
    raise ValueError('Número no finito.')


def validar_estructura(value):
    pending = [(value, 0)]
    visited = 0
    while pending:
        item, depth = pending.pop()
        visited += 1
        if depth > 32 or visited > 100000:
            raise ValueError('Estructura demasiado compleja.')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Número fuera de rango.')
        if isinstance(item, str) and '\x00' in item:
            raise ValueError('El texto contiene caracteres no permitidos.')
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for pair in item.items() for v in pair)
        elif isinstance(item, (tuple, list)):
            pending.extend((v, depth + 1) for v in item)


class ValidacionEntradaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body, parse_constant=numero_no_finito)
                    if not isinstance(data, dict):
                        raise ValueError('El cuerpo JSON debe ser un objeto.')
                    validar_estructura(data)
                elif request.content_type in {'application/x-www-form-urlencoded', 'multipart/form-data'}:
                    validar_estructura(dict(request.POST.lists()))
            except (ValueError, UnicodeDecodeError, RecursionError):
                return JsonResponse({'error': 'Datos inválidos: revisa el formato y tamaño del contenido.'}, status=400)
        return self.get_response(request)
