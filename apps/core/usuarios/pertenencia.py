"""Pertenencia vigente para nuevas decisiones, sin conceder roles operativos."""

from apps.core.models.usuarios_base import UserProfile

from apps.core.usuarios.verificacion import estado_verificacion


def pertenencia_actual(usuario):
    """Consulta identidad y decisión actuales; no confía en el perfil en caché.

    El resumen puede conservarse en una cotización privada. No incluye la
    identidad revisada, documentos, fundamento ni referencia del revisor.
    """
    resumen = {
        'version': 1, 'estado': 'pendiente', 'revision_id': None,
        'tipo_usuario': '', 'institucion_codigo': '',
        'aprobada': False, 'vigente_hasta': None,
    }
    if not usuario or not usuario.is_authenticated or usuario.pk is None:
        return resumen
    perfil = UserProfile.objects.select_related('user').filter(user_id=usuario.pk).first()
    if perfil is None:
        return resumen
    estado = estado_verificacion(perfil)
    ultima = estado['ultima']
    resumen.update(
        estado=estado['codigo'], tipo_usuario=perfil.tipo_usuario,
        aprobada=estado['verificada'],
    )
    if ultima:
        identidad = ultima.identidad_revisada if isinstance(ultima.identidad_revisada, dict) else {}
        resumen.update(
            revision_id=ultima.pk,
            institucion_codigo=identidad.get('institucion_codigo', ''),
            vigente_hasta=ultima.vigente_hasta.isoformat() if ultima.vigente_hasta else None,
        )
    return resumen


def es_docente_verificado(usuario):
    pertenencia = pertenencia_actual(usuario)
    return pertenencia['aprobada'] and pertenencia['tipo_usuario'] == 'docente'
