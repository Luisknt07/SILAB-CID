"""Identidad de quien organiza y cuentas del grupo de una visita."""

import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email


def categoria_visita(responsable, datos):
    tipo = getattr(getattr(responsable, 'profile', None), 'tipo_usuario', '')
    categoria = (datos.get('categoria') or 'externa').strip()
    if categoria not in {'interna', 'externa'}:
        raise ValidationError('Selecciona visita interna o externa.')
    if categoria == 'interna' and not responsable:
        raise PermissionDenied('Inicia sesión para solicitar una visita interna.')
    if categoria == 'interna' and tipo == 'externo':
        raise PermissionDenied('Las visitas internas requieren una cuenta institucional interna.')
    return categoria


def contacto_externo(datos):
    contacto = {}
    for clave, limite in (('nombre', 100), ('correo', 254), ('telefono', 20)):
        valor = (datos.get(f'responsable_{clave}') or '').strip()
        if not valor or len(valor) > limite:
            raise ValidationError(f'Completa {clave} del responsable externo (máximo {limite} caracteres).')
        contacto[clave] = valor
    validate_email(contacto['correo'])
    if get_user_model().objects.filter(email__iexact=contacto['correo'], is_active=True).exclude(
        profile__tipo_usuario='externo',
    ).exists():
        raise PermissionDenied('Ese correo corresponde a una cuenta interna. Inicia sesión para solicitar la visita.')
    return contacto


def asistentes_internos(texto):
    if texto is not None and (not isinstance(texto, str) or len(texto) > 5000):
        raise ValidationError('La selección de usuarios internos excede el tamaño permitido.')
    try:
        ids = json.loads(texto or '[]')
    except (TypeError, ValueError) as error:
        raise ValidationError('La selección de usuarios internos no es válida.') from error
    if (not isinstance(ids, list) or len(ids) > 200
            or any(type(pk) is not int or not 0 < pk < 2 ** 63 for pk in ids)
            or len(set(ids)) != len(ids)):
        raise ValidationError('Selecciona hasta 200 usuarios internos sin duplicados.')
    usuarios = {usuario.pk: usuario for usuario in get_user_model().objects.filter(
        pk__in=ids, is_active=True,
    ).select_related('profile')}
    if len(usuarios) != len(ids):
        raise ValidationError('Un usuario seleccionado ya no está activo o no existe.')
    filas = []
    for pk in ids:
        usuario = usuarios[pk]
        perfil = getattr(usuario, 'profile', None)
        if not perfil or perfil.tipo_usuario in {'', 'externo'} or perfil.campos_faltantes_reserva():
            raise ValidationError('Cada visitante interno necesita una cuenta interna activa y un perfil completo.')
        filas.append({
            'usuario': usuario,
            'nombre': (usuario.get_full_name() or usuario.username)[:150],
            'documento': perfil.cedula or '',
            'rol': perfil.tipo_usuario if perfil.tipo_usuario in {'estudiante', 'docente', 'administrativo'} else 'otro',
            'telefono': perfil.telefono or '',
            'correo': usuario.email or '',
        })
    return filas
