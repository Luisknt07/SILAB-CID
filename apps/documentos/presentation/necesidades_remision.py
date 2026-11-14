"""Remisión interna Dirección–dependencia de un informe anual evaluado.

El contenido se reconstruye en el servidor; la acción no envía correos,
asigna recursos presupuestarios ni registra adquisiciones ejecutadas.
"""
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.necesidades import RemisionNecesidades, contenido_canonico, huella_contenido


def _usuario_activo(usuario):
    return bool(usuario and getattr(usuario, 'is_authenticated', False)
        and getattr(usuario, 'pk', None) and get_user_model().objects.filter(
            pk=usuario.pk, is_active=True).exists())


def _direccion_activa(usuario):
    return bool(_usuario_activo(usuario) and get_user_model().objects.filter(
        pk=usuario.pk, is_active=True, is_superuser=True).exists())


def puede_leer_remision(usuario, remision):
    """La autoridad vigente recibe el antecedente aunque cambien sus titulares."""
    if not _usuario_activo(usuario):
        return False
    if _direccion_activa(usuario):
        return True
    return DependenciaAcademica.objects.filter(pk=remision.dependencia_id, activa=True,
        receptores__pk=usuario.pk).exists()


def contenido_remision(remision):
    """Comprueba la captura antes de producir otra descarga del mismo informe."""
    if remision.sha256 != huella_contenido(remision.contenido):
        raise ValidationError('La captura archivada no coincide con su huella de integridad.')
    return json.loads(contenido_canonico(remision.contenido).decode('utf-8'))


@transaction.atomic
def remitir_necesidades(anio, dependencia, usuario):
    """Archiva una captura por dependencia; repetir el mismo contenido es inocuo."""
    if not _direccion_activa(usuario):
        raise PermissionDenied('Solo Dirección puede remitir las necesidades evaluadas.')
    try:
        texto_anio = str(anio)
        anio_preparacion = int(texto_anio) if texto_anio.isascii() and texto_anio.isdigit() else 0
    except (TypeError, ValueError, OverflowError):
        raise ValidationError('Selecciona un año de preparación válido.') from None
    if isinstance(anio, bool) or not 2020 <= anio_preparacion <= 2099:
        raise ValidationError('Selecciona un año de preparación válido.')
    dependencia_id = getattr(dependencia, 'pk', dependencia)
    try:
        destino = DependenciaAcademica.objects.select_for_update().get(pk=dependencia_id, activa=True)
    except (DependenciaAcademica.DoesNotExist, TypeError, ValueError, OverflowError):
        raise ValidationError('Selecciona una dependencia activa para remitir el informe.') from None
    destinatarios = list(destino.receptores.filter(is_active=True).order_by('pk'))
    if not destinatarios:
        raise ValidationError('Configura al menos un receptor activo de la dependencia antes de remitir.')
    from .necesidades_decanato import lectura_necesidades
    lectura = lectura_necesidades(anio_preparacion, usuario, dependencia=destino)
    resumen = lectura.get('resumen', {})
    if not resumen.get('evaluadas'):
        raise ValidationError('La dependencia todavía no tiene necesidades evaluadas por Dirección para remitir.')
    # Round-trip estricto: no modelos, Decimals ni otros datos vivos en la captura.
    contenido = json.loads(contenido_canonico(lectura).decode('utf-8'))
    huella = huella_contenido(contenido)
    remision, _ = RemisionNecesidades.objects.get_or_create(
        dependencia=destino, anio_preparacion=anio_preparacion, sha256=huella,
        defaults=dict(dependencia_nombre=destino.nombre, anio_ejecucion=anio_preparacion + 1,
            remitido_por=usuario, contenido=contenido,
            destinatarios=[{'id': u.pk, 'nombre': u.get_full_name() or u.get_username()}
                           for u in destinatarios]))
    return remision
