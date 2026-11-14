"""Trazabilidad uniforme de las operaciones realizadas fuera del admin."""
from uuid import UUID

from apps.formacion.models.practicas import RegistroAuditoriaUnidad


def registrar_auditoria(
    request=None,
    *,
    unidad,
    accion,
    objeto,
    descripcion,
    anteriores=None,
    nuevos=None,
    usuario=None,
):
    """Registra acciones humanas o procesos automáticos con el mismo formato.

    ``request`` puede omitirse en tareas programadas. En ese caso el usuario
    queda vacío y la interfaz identifica el cambio como realizado por el
    sistema. ``usuario`` permite atribuir procesos internos a una cuenta de
    servicio cuando el despliegue disponga de ella.
    """
    request_user = getattr(request, "user", None)
    if usuario is None and getattr(request_user, "is_authenticated", False):
        usuario = request_user
    meta = getattr(request, "META", {}) or {}
    forwarded = meta.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    ip = forwarded or meta.get("REMOTE_ADDR") or None
    return RegistroAuditoriaUnidad.objects.create(
        unidad=unidad,
        usuario=usuario,
        accion=accion,
        entidad=objeto._meta.label,
        objeto_id=str(objeto.pk or ""),
        descripcion=descripcion[:255],
        datos_anteriores=anteriores or {},
        datos_nuevos=nuevos or {},
        direccion_ip=ip,
    )


def instantanea(objeto, campos):
    data = {}
    for campo in campos:
        valor = getattr(objeto, campo, None)
        if hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        elif isinstance(valor, UUID):
            valor = str(valor)
        elif hasattr(valor, "pk"):
            valor = valor.pk
        data[campo] = valor
    return data
