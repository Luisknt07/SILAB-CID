"""Textos de entrada a reservas según la oferta publicada de cada unidad."""

import re
from unicodedata import combining, normalize

from django.templatetags.static import static
from django.utils.translation import gettext as _


def icono_espacio_reserva(espacio):
    """Identifica la actividad del área sin recurrir a imágenes de muestra."""
    referencia = normalize('NFKD', f'{espacio.codigo} {espacio.nombre}'.casefold())
    referencia = ''.join(letra for letra in referencia if not combining(letra))
    if re.search(r'\b(?:cad|cam)\b', referencia):
        return 'fa-drafting-compass'
    actividades = (
        (('aditiva', 'imp3d', 'fdm', 'resina'), 'fa-cube'),
        (('digitalizacion', 'metrologia', 'scan'), 'fa-vector-square'),
        (('diseno',), 'fa-drafting-compass'),
        (('electronica', 'hardware', 'elec'), 'fa-microchip'),
        (('robot', 'automatizacion'), 'fa-robot'),
        (('laser', 'vinilo', 'textil'), 'fa-cut'),
        (('cnc', 'mecanizado', 'fresado'), 'fa-cogs'),
        (('acabado', 'posproces'), 'fa-tools'),
        (('almacen', 'bodega'), 'fa-boxes'),
    )
    for palabras, icono in actividades:
        if any(palabra in referencia for palabra in palabras):
            return icono
    return {
        'estacion': 'fa-desktop',
        'sala': 'fa-chalkboard-teacher',
        'puesto': 'fa-chair',
        'cabina': 'fa-door-open',
        'linea': 'fa-industry',
        'camara': 'fa-temperature-low',
        'parcela': 'fa-tractor',
        'invernadero': 'fa-seedling',
        'establo': 'fa-warehouse',
    }.get(espacio.tipo, 'fa-th-large')


def imagen_espacio_reserva(espacio):
    """Conserva las portadas del área y evita la misma escena genérica repetida."""
    if espacio.imagen_propia_url:
        return espacio.imagen_propia_url
    referencias = {
        'fa-drafting-compass': 'computadoras-y-estaciones-de-trabajo.jpg',
        'fa-desktop': 'computadoras-y-estaciones-de-trabajo.jpg',
        'fa-microchip': 'estaciones-de-soldadura-electronica.jpg',
        'fa-robot': 'brazos-roboticos-y-cobots.jpg',
        'fa-chalkboard-teacher': 'mesas-y-sillas-modulares.jpg',
        'fa-boxes': 'estanterias-de-bodega-y-almacenamiento-de-laboratorio.jpg',
    }
    foto = referencias.get(espacio.icono_reserva)
    if foto:
        return static(f'img/catalogo/familias/{foto}')
    for activo in espacio.equipos_asociados.all():
        modelo = activo.equipo
        if (modelo.imagen or modelo.fuente_imagen) and modelo.imagen_publica_url:
            return modelo.imagen_publica_url
    return ''


def textos_rutas_reserva(configuracion, servicios, software):
    recursos = []
    if configuracion.reservas_espacios:
        recursos.append(_('espacios'))
    if configuracion.reservas_equipos:
        recursos.append(_('equipos e instrumentos'))
    if software:
        recursos.append(_('software'))
    enumeracion = _(' y ').join(recursos) if len(recursos) < 3 else (
        ', '.join(recursos[:-1]) + _(' y ') + recursos[-1]
    )
    nombres = list(dict.fromkeys(
        servicio.nombre for servicio in servicios if servicio.tipo_servicio != 'visita'
    ))[:3]
    return {
        'recursos': _(
            'Tú o tu grupo utilizan %(recursos)s de esta unidad para prácticas, '
            'investigación o trabajo autónomo.'
        ) % {'recursos': enumeracion} if recursos else _(
            'Esta unidad no tiene reservas de recursos habilitadas.'
        ),
        'servicios': _(
            'El equipo de la unidad realiza el trabajo por ti. Servicios publicados: %(servicios)s.'
        ) % {'servicios': '; '.join(nombres)} if nombres else _(
            'Solicita al equipo de la unidad un trabajo especializado, '
            'según sus capacidades y la revisión técnica de tu solicitud.'
        ),
    }
