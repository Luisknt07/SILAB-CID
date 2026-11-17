"""La revisión institucional no puede ser una evaluación de la propia gestión.

Control transversal de los comandos auditados. No concede funciones por tener
una cuenta técnica ni cambia el régimen de autorización de la plataforma.
"""

from django.core.exceptions import ValidationError

COMANDOS_DE_REVISION = frozenset(
    {
        "anotar_observacion",
        "observar_documento",
        "recibir_documento",
        "habilitar_entrega_tardia",
        "evaluar_documento",
        "decidir_desde_listado",
        "decidir_documento_qr",
        "aprobar_permanente",
        "revocar_permanente",
        "confirmar_conformidad",
        "confirmar_cierre",
    }
)


def conflicto_directo(documento, usuario, unidad):
    """Motivo verificable; recibir administrativamente no convierte en autor."""
    actor = getattr(usuario, "pk", None)
    if actor is None:
        return ""
    if getattr(unidad, "administrador_id", None) == actor:
        return "administra el laboratorio o instalación evaluada"
    if getattr(documento, "cargado_por_id", None) == actor:
        return "cargó el documento evaluado"
    # En un documento devuelto, validado_por guarda a quien lo observó desde la revisión, no a
    # quien envió la entrega: esa persona sigue pudiendo habilitar la corrección que devolvió.
    if (
        getattr(documento, "estado", "") != "observado"
        and getattr(documento, "validado_por_id", None) == actor
        and getattr(documento, "recibido_por_id", None) != actor
    ):
        return "validó la entrega de la unidad"
    return ""


def exigir_revision_independiente(documento, usuario, unidad):
    motivo = conflicto_directo(documento, usuario, unidad)
    if not motivo and getattr(usuario, "pk", None):
        from apps.gestion_unidades.models.espacios import ResponsableUnidad

        if ResponsableUnidad.objects.filter(
            unidad_id=unidad.pk, usuario_id=usuario.pk, activo=True, rol="coordinacion"
        ).exists():
            motivo = "coordina el laboratorio o instalación evaluada"
    if not motivo and getattr(documento, 'pk', None) and getattr(usuario, 'pk', None):
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.models.constancias import ConstanciaDocumento
        if DocumentoElaborado.objects.filter(documento_id=documento.pk, actualizado_por_id=usuario.pk).exists():
            motivo = 'redactó el documento evaluado'
        elif ConstanciaDocumento.objects.filter(documento_id=documento.pk, version=documento.version,
                                                emitido_por_id=usuario.pk).exists():
            motivo = 'emitió la versión documental evaluada'
    if motivo:
        raise ValidationError(
            "Esta revisión requiere otra persona autorizada: quien revisa "
            + motivo
            + ". La cuenta de superadministración no elimina este conflicto."
        )
