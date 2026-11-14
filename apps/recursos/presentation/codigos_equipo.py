"""Cómo se identifica un equipo: el código oficial de la bodega y los códigos del sistema.

La Universidad identifica cada bien con el código que asigna su bodega y que va impreso, con un
prefijo institucional, en la etiqueta de código de barras pegada en el equipo (por ejemplo
«23300000000-37881242»). Ese es el código principal. El sistema conserva además su código interno
(codigo_unidad, legible y por unidad), los códigos anteriores y el número de serie del fabricante:
un lector puede recibir cualquiera de ellos, con o sin prefijo, o la dirección que guarda un QR.
"""
import re
from urllib.parse import parse_qs, urlparse

from django.db.models import Q

from apps.recursos.models.identificadores import PREFIJO_INSTITUCIONAL, limpiar_codigo_bien  # noqa: F401 - la regla vive con los modelos

_RUTA_DE_EQUIPO = re.compile(r'/equipos/(?:codigo/)?([^/]+)/?$')


def codigo_leido(texto):
    """Lo que interesa de una lectura: el código de una URL de QR o el de la etiqueta, sin prefijo."""
    texto = (texto or '').strip()
    if texto.lower().startswith(('http://', 'https://', '/')):
        direccion = urlparse(texto)
        consulta = parse_qs(direccion.query)
        for clave in ('codigo', 'scan'):
            if consulta.get(clave):
                return limpiar_codigo_bien(consulta[clave][0])
        ruta = _RUTA_DE_EQUIPO.search(direccion.path)
        if ruta:
            return limpiar_codigo_bien(ruta.group(1))
    return limpiar_codigo_bien(texto)


def buscar_equipo(texto, equipos=None):
    """El equipo que corresponde a una lectura: por código del bien, del sistema, anterior o de serie."""
    from apps.recursos.models.unidades import UnidadEquipo

    codigo = codigo_leido(texto)
    if not codigo:
        return None
    equipos = UnidadEquipo.objects.all() if equipos is None else equipos
    for filtro in (Q(codigo_bien__iexact=codigo), Q(codigo_unidad__iexact=codigo),
                   Q(codigos_anteriores__codigo__iexact=codigo), Q(numero_serie__iexact=codigo)):
        encontrado = equipos.filter(filtro).select_related('equipo', 'laboratorio').first()
        if encontrado:
            return encontrado
    return None


def ve_datos_patrimoniales(usuario, equipo):
    """Custodio, valor contable e historia: solo quien opera los recursos o el mantenimiento de la unidad dueña."""
    from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

    unidad = equipo.laboratorio
    if unidad is None or not getattr(usuario, 'is_authenticated', False):
        return False
    return (puede_operar_modulo_unidad(usuario, unidad, 'recursos')
            or puede_operar_modulo_unidad(usuario, unidad, 'mantenimiento'))


def etiqueta_de(equipo):
    """El texto de la etiqueta: el oficial con su prefijo o, si la bodega aún no lo asignó, el del sistema."""
    return equipo.codigo_etiqueta
