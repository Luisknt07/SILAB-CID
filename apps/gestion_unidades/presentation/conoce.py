"""«Conoce la unidad»: la presentación que la unidad escribe sobre sí misma.

Qué es, qué hace, su historia, misión, visión, objetivos y líneas de acción,
con el video en el que su responsable la presenta. Las cifras no se escriben a
mano: salen de lo que la unidad tiene registrado en la plataforma.
"""
from datetime import date

from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.interior import MedioInterior
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.linea_tiempo import linea_de_tiempo
from apps.recursos.presentation.miniaturas import recorte_cuadrado
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad


def equipos_de_la_unidad(unidad):
    """Las unidades de equipo en servicio de la unidad (propias o compartidas) y los tipos de equipo que suman."""
    unidades_equipo = UnidadEquipo.objects.publicos().filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad)
    ).select_related('equipo').prefetch_related('espacios_asociados').distinct()
    equipos = EquiposServicios.objects.filter(
        id__in=unidades_equipo.values_list('equipo_id', flat=True).distinct()
    ).order_by('nombre')
    return unidades_equipo, equipos


def cifras_de_la_unidad(unidad):
    """Lo que la unidad tiene registrado, para leerlo de un vistazo; se omite lo que está en cero."""
    _, equipos = equipos_de_la_unidad(unidad)
    anios = date.today().year - unidad.fecha_inicio.year if unidad.fecha_inicio else 0
    cifras = (
        (equipos.count(), 'Equipos especializados', 'fa-cogs'),
        (EspacioReservable.objects.filter(unidad=unidad, activo=True).count(), 'Áreas y espacios', 'fa-th-large'),
        (SoftwareDisponible.objects.filter(unidad=unidad, activo=True).count(), 'Programas especializados', 'fa-laptop-code'),
        (unidad.capacidad_personas or 0, 'Personas de aforo', 'fa-users'),
        (anios, f'Años de trayectoria, desde {unidad.fecha_inicio.year}' if anios else '', 'fa-history'),
    )
    return [{'valor': valor, 'etiqueta': etiqueta, 'icono': icono} for valor, etiqueta, icono in cifras if valor]


def foto_de_portada(unidad):
    """La foto de la unidad o, si no tiene, la primera de su galería: vista general primero."""
    if unidad.imagen:
        return unidad.imagen.url
    foto = (MedioInterior.objects.filter(unidad=unidad, tipo='foto', publicado=True).exclude(imagen='')
            .order_by(F('espacio').asc(nulls_first=True), 'orden', 'pk').first())
    return foto.imagen.url if foto else ''


def muestra_de_la_galeria(unidad, cantidad=3):
    """Algunas fotos de «La planta por dentro» y cuántos medios tiene, para invitar a verla completa."""
    publicados = MedioInterior.objects.filter(unidad=unidad, publicado=True)
    fotos = publicados.filter(tipo='foto').exclude(imagen='').order_by(F('espacio').asc(nulls_first=True), 'orden', 'pk')
    return [recorte_cuadrado(foto.imagen, 'interior', lado=480) or foto.imagen.url for foto in fotos[:cantidad]], publicados.count()


def acepta_reservas(unidad):
    configuracion = ConfiguracionOperativaUnidad.objects.filter(unidad=unidad).first()
    return bool(configuracion and (configuracion.reservas_equipos or configuracion.reservas_espacios
                                   or configuracion.solicitudes_servicio))


def se_muestra(unidad, gestor):
    """El público ve la presentación publicada; el personal también el borrador, para revisarla."""
    presentacion = getattr(unidad, 'presentacion', None)
    return gestor or bool(presentacion and presentacion.publicada)


# «Quiénes somos» muestra un tema a la vez: la página no se carga de texto.
PESTANAS = (
    ('que_es', 'Qué es', 'fa-building'),
    ('que_hace', 'Qué hace', 'fa-cog'),
    ('capacidades', 'Capacidades', 'fa-tools'),
    ('areas_trabajo', 'Áreas de trabajo', 'fa-project-diagram'),
)


def contenido_de(unidad, presentacion):
    """Lo que la página muestra: cada bloque solo si la unidad lo llenó, y el índice que lleva a ellos."""
    listas = {campo: presentacion.lista(campo) for campo in ('objetivos', 'beneficiarios', 'resultados')}
    lineas, hitos = list(unidad.lineas_accion.all()), list(unidad.hitos.all())
    pestanas = [{'clave': campo, 'titulo': titulo, 'icono': icono, 'texto': getattr(presentacion, campo)}
                for campo, titulo, icono in PESTANAS if getattr(presentacion, campo).strip()]
    indice = [(ancla, titulo) for ancla, titulo, hay in (
        ('quienes', 'Quiénes somos', pestanas),
        ('video', 'Video', presentacion.video_id),
        ('rumbo', 'Misión y visión', presentacion.mision or presentacion.vision or listas['objetivos']),
        ('lineas', 'Líneas de acción', lineas),
        ('historia', 'Historia', presentacion.historia or hitos),
        ('impacto', 'Impacto', listas['beneficiarios'] or listas['resultados']),
    ) if hay]
    fotos, total_medios = muestra_de_la_galeria(unidad)
    return {**listas, 'pestanas': pestanas, 'lineas_accion': lineas, 'hitos': hitos, 'indice': indice,
            'linea_tiempo': linea_de_tiempo(hitos),
            'cifras': cifras_de_la_unidad(unidad), 'foto_portada': foto_de_portada(unidad),
            'fotos_interior': fotos, 'total_medios': total_medios}


@xframe_options_sameorigin
def conoce_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    presentacion = getattr(unidad, 'presentacion', None)
    visible = bool(presentacion and (presentacion.publicada or gestor))
    return render(request, 'portal/pages/unidades/detalle/conoce_unidad.html', {
        'unidad': unidad,
        'presentacion': presentacion if visible else None,
        'borrador': visible and not presentacion.publicada,
        **(contenido_de(unidad, presentacion) if visible else {}),
        'acepta_reservas': acepta_reservas(unidad),
        'ubicacion_url': reverse('ubicacion_unidad', args=[unidad.slug]),
        'ediciones': ediciones_de(request.user, unidad),
    })
