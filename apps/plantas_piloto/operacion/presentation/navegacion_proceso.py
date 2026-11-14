"""Accesos y relaciones que acompañan una ficha sin romper la ruta del aula."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse

from apps.core.presentation.identidad import identidad_actual

from apps.gestion_unidades.models.repositorio import ArtefactoExterno
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.reservas.models.reservas import GuiaActividadReserva
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.repositorio import artefactos_vigentes


def metadatos_editoriales(objeto, titulo=None, codigo=None):
    """Código, versión y cita formal de la fuente que realmente genera la ficha."""
    producto, institucion = identidad_actual()
    ficha = FichaContenido.objects.filter(
        content_type=ContentType.objects.get_for_model(objeto), object_id=objeto.pk,
    ).first()
    codigo = (ficha.codigo if ficha else codigo) or getattr(objeto, 'codigo', '')
    titulo = (ficha.titulo if ficha else titulo) or getattr(objeto, 'nombre', str(objeto))
    version = ficha.version if ficha else 1
    fecha = (ficha.actualizado_en if ficha else getattr(objeto, 'actualizado_en', None))
    fecha_texto = fecha.strftime('%d/%m/%Y') if fecha else 'sin fecha de actualización'
    anio = fecha.year if fecha else 's. f.'
    return {
        'codigo': codigo,
        'titulo': titulo,
        'version': version,
        'fecha': fecha_texto,
        'cita': (
            f'{institucion.nombre}. ({anio}). {titulo} '
            f'({codigo}, versión {version}, actualización {fecha_texto}). '
            f'{producto.nombre_corto}.'
        ),
    }


def acciones_del_proceso(unidad, receta, activa):
    """Relaciona ficha, cálculos y documentación sin repetirlos en el árbol."""
    seleccion = f'?receta={receta.pk}'
    destinos = [
        ('producto', 'Ficha del producto', reverse(
            'ficha_producto_publica', args=[unidad.slug, receta.producto_id],
        )),
        ('ficha', 'Ficha del proceso', reverse(
            'ficha_proceso_publica', args=[unidad.slug, receta.pk],
        )),
        ('balance', 'Simular · Balance de materia y energía', reverse(
            'simulador_balance', args=[unidad.slug],
        ) + seleccion),
        ('linea', 'Capacidad y equilibrado', reverse(
            'simulador_linea', args=[unidad.slug],
        ) + seleccion),
        ('documentacion', 'Documentación técnica · Saber y hacer', reverse(
            'documentacion_proceso', args=[unidad.slug, receta.pk],
        )),
        ('datos', 'Datos (CSV)', reverse(
            'datos_proceso_csv', args=[unidad.slug, receta.pk],
        )),
    ]
    destinos.extend(
        (
            f'artefacto-{artefacto.pk}', f'Exportar datos · {artefacto.nombre}',
            reverse('exportar_paquete_artefacto', args=[unidad.slug, artefacto.codigo]),
        )
        for artefacto in artefactos_vigentes(ArtefactoExterno.objects.filter(
            unidad=unidad, receta=receta, estado='publicado', visibilidad='publica',
            nivel_integracion__in=(1, 2),
        )).order_by('nombre')
    )
    return [
        {'clave': clave, 'nombre': nombre, 'url': url, 'activa': clave == activa}
        for clave, nombre, url in destinos
    ]


def fichas_relacionadas_del_proceso(unidad, receta):
    """La red útil del proceso: producto, calidad, guías y equipos en un clic."""
    relacionadas = [{
        'tipo': 'Producto',
        'nombre': receta.producto.nombre,
        'icono': 'fas fa-box-open',
        'url': reverse('ficha_producto_publica', args=[unidad.slug, receta.producto_id]),
    }]
    planes = PlanCalidad.objects.filter(unidad=unidad, activo=True).filter(
        familia_id=receta.familia_id,
    ).order_by('nombre')
    if receta.producto_id:
        planes = planes.filter(Q(producto__isnull=True) | Q(producto_id=receta.producto_id))
    for plan in planes[:4]:
        relacionadas.append({
            'tipo': 'Especificación', 'nombre': plan.nombre, 'icono': 'fas fa-clipboard-check',
            'url': reverse('calidad_publica', args=[unidad.slug]) + f'?familia={receta.familia.codigo}',
        })
    guias = GuiaActividadReserva.objects.filter(
        actividad__unidad=unidad,
        familia_id=receta.familia_id,
        activo=True,
        estado_publicacion='publicada',
        visibilidad='publica',
    ).order_by('-es_vigente', '-numero_version', 'titulo')
    for guia in guias[:3]:
        relacionadas.append({
            'tipo': 'Guía de práctica', 'nombre': guia.titulo, 'icono': 'fas fa-book-open',
            'url': reverse('ver_guia_actividad', args=[guia.pk]),
        })
    for artefacto in artefactos_vigentes(ArtefactoExterno.objects.filter(
        unidad=unidad, receta=receta, estado='publicado', visibilidad='publica',
    )).order_by('nombre')[:3]:
        relacionadas.append({
            'tipo': 'Artefacto externo', 'nombre': artefacto.nombre, 'icono': 'fas fa-cube',
            'url': reverse('artefacto_externo', args=[unidad.slug, artefacto.codigo]),
        })
    equipos_ids = receta.etapas.exclude(equipo_id=None).values_list('equipo_id', flat=True).distinct()
    unidades_equipo = UnidadEquipo.objects.filter(
        equipo_id__in=equipos_ids, activa=True,
    ).filter(laboratorio=unidad).select_related('equipo').order_by('equipo__nombre')
    for unidad_equipo in unidades_equipo:
        relacionadas.append({
            'tipo': 'Equipo', 'nombre': unidad_equipo.equipo.nombre, 'icono': 'fas fa-cogs',
            'url': reverse('ficha_equipo_publica', args=[unidad.slug, unidad_equipo.codigo_unidad]),
        })
    return relacionadas
