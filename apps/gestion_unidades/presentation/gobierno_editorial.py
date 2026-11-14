"""El gobierno editorial de las plantas piloto: qué contenido ve el público y qué queda en revisión.

Un objeto de una planta (equipo, proceso, producto…) se publica según su ficha editorial
(FichaContenido): «publicada» o «en revisión» con visibilidad pública lo ve cualquiera; restringida,
quien inicia sesión; lo demás, solo quien gestiona la unidad. Las demás unidades no tienen este
gobierno. visibles_para filtra una lista con una sola consulta, para las páginas con cientos de equipos.
"""
from django.contrib.contenttypes.models import ContentType

from apps.gestion_unidades.models.fichas import FichaContenido

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

ESTADOS_PUBLICOS = ('publicada', 'en_revision')


def _ficha_permite(ficha, usuario):
    # Contenido heredado anterior al índice editorial conserva su publicación;
    # toda alta nueva en una planta ya recibe su ficha mediante las señales.
    if ficha is None:
        return True
    if ficha.estado not in ESTADOS_PUBLICOS:
        return False
    if ficha.visibilidad == 'publica':
        return True
    return ficha.visibilidad == 'restringida' and usuario.is_authenticated


def objeto_visible_para(objeto, unidad, usuario):
    """Aplica el gobierno editorial sin afectar unidades que no son plantas."""
    if unidad.dependencia != 'plantas_piloto' or usuario is None:
        return True
    if puede_gestionar_unidad(usuario, unidad):
        return True
    ficha = FichaContenido.objects.filter(
        content_type=ContentType.objects.get_for_model(objeto), object_id=objeto.pk,
    ).only('estado', 'visibilidad').first()
    return _ficha_permite(ficha, usuario)


def visibles_para(objetos, unidad, usuario):
    """Los objetos de la lista que el usuario puede ver, con una sola consulta a las fichas editoriales."""
    objetos = list(objetos)
    if not objetos or unidad.dependencia != 'plantas_piloto' or usuario is None or puede_gestionar_unidad(usuario, unidad):
        return objetos
    fichas = {
        ficha.object_id: ficha for ficha in FichaContenido.objects.filter(
            content_type=ContentType.objects.get_for_model(objetos[0]), object_id__in=[objeto.pk for objeto in objetos],
        ).only('object_id', 'estado', 'visibilidad')
    }
    return [objeto for objeto in objetos if _ficha_permite(fichas.get(objeto.pk), usuario)]
