"""Consultas publicas sobre Unidad durante la transicion de sus tablas."""

from apps.directorio_unidades.contracts import IdentidadUnidad, TipoUnidad


def obtener_identidad_publica(slug, tipo=None):
    """Devuelve valores copiados de una unidad activa o None; nunca su modelo."""
    from apps.directorio_unidades.models.core import Unidad

    unidades = Unidad.objects.filter(slug=slug, activo=True)
    if tipo is not None:
        unidades = unidades.filter(dependencia=TipoUnidad(tipo).value)
    datos = unidades.values(
        "id", "nombre", "slug", "dependencia", "contacto_email"
    ).first()
    if datos is None or datos["dependencia"] not in {tipo.value for tipo in TipoUnidad}:
        return None
    return IdentidadUnidad(
        unidad_id=datos["id"],
        nombre=datos["nombre"],
        slug=datos["slug"],
        tipo=TipoUnidad(datos["dependencia"]),
        contacto_email=datos["contacto_email"],
    )


def oferta_publica_para_centros(slugs):
    """DTO de cursos y accesos canónicos; conserva matrícula y agenda en su unidad propietaria."""
    from django.urls import reverse
    from django.core.exceptions import ValidationError
    from django.db.models import Count, F, Prefetch, Window
    from django.db.models.functions import RowNumber
    from apps.formacion.models.cursos import Curso, EdicionCurso
    from apps.directorio_unidades.models.core import Unidad
    from apps.formacion.models.enlaces_formacion import validar_enlace_formacion
    from apps.formacion.presentation.aforo_cursos import cupos_por_edicion

    unidades = list(Unidad.objects.filter(slug__in=set(slugs), activo=True)
                    .only('id', 'nombre', 'slug', 'dependencia'))
    publicas = [u for u in unidades if u.dependencia in {tipo.value for tipo in TipoUnidad}]
    cursos = []
    ediciones_publicas = EdicionCurso.objects.filter(activa=True)
    # Las dos ventanas se calculan antes del filtro de posición: seis fichas
    # por unidad conservan el total real sin materializar el catálogo entero.
    oferta = list(Curso.objects.filter(unidad__in=publicas, publicado=True, activo=True)
                  .annotate(
                      _posicion_catalogo=Window(RowNumber(), partition_by=[F('unidad_id')],
                          order_by=[F('orden').asc(), F('nombre').asc(), F('pk').asc()]),
                      _total_catalogo=Window(Count('pk'), partition_by=[F('unidad_id')]),
                  ).filter(_posicion_catalogo__lte=6).order_by('unidad_id', 'orden', 'nombre', 'pk')
                  .select_related('unidad')
                  .only('id', 'nombre', 'descripcion', 'modalidad', 'duracion_horas', 'codigo',
                        'origen', 'url_externa', 'entidad_organizadora', 'participacion_unidad', 'clasificacion',
                        'unidad__id', 'unidad__nombre', 'unidad__slug')
                  .prefetch_related(Prefetch('ediciones', queryset=ediciones_publicas, to_attr='ediciones_publicas')))
    cuentas = {curso.unidad_id: curso._total_catalogo for curso in oferta}
    resumen = [{'nombre': u.nombre, 'slug': u.slug, 'cursos_total': cuentas.get(u.pk, 0),
                'agenda_url': reverse('agenda_disponibilidad_unidad', args=[u.slug])
                    if u.dependencia in ('laboratorios', 'plantas_piloto') else '',
                'cursos_url': reverse('cursos_unidad', args=[u.slug])} for u in publicas]
    cupos = cupos_por_edicion(e for curso in oferta if not curso.es_externo for e in curso.ediciones_publicas)
    for curso in oferta:
        ediciones = [{'nombre': e.nombre, 'estado': e.estado()[1], 'inicio': e.inicio, 'fin': e.fin,
                      'horario': e.horario, 'lugar': e.lugar, 'cupos': cupos.get(e.pk)}
                     for e in curso.ediciones_publicas]
        enlace_externo = curso.url_externa if curso.es_externo else ''
        try:
            validar_enlace_formacion(enlace_externo)
        except ValidationError:
            enlace_externo = ''
        cursos.append({'nombre': curso.nombre, 'descripcion': curso.descripcion, 'modalidad': curso.get_modalidad_display(),
                       'horas': curso.duracion_horas, 'unidad': curso.unidad.nombre,
                       'url': reverse('curso_unidad', args=[curso.unidad.slug, curso.codigo]), 'ediciones': ediciones,
                       'es_externo': curso.es_externo, 'url_externa': enlace_externo,
                       'categoria': curso.get_clasificacion_display(), 'organizador': curso.entidad_organizadora,
                       'participacion': curso.get_participacion_unidad_display()})
    return {'unidades': resumen, 'cursos': cursos}
