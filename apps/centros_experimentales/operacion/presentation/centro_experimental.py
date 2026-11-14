"""La ficha de un centro experimental: cómo funciona, sus ejes productivos, su calendario y a dónde va lo que produce.

Un centro no es un laboratorio grande: es una finca que produce y experimenta a la vez. Lo cuidan familias
cuidadoras, lo administra una persona que lleva sus necesidades, y lo usan docentes, estudiantes y las plantas piloto
que transforman lo que cosecha. Su trabajo se organiza en ejes productivos (ganadería de leche, cultivos andinos,
café…), cada uno con su página como las áreas de un laboratorio. La ficha pública nombra roles, nunca personas.
"""
import csv

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, RegistroProduccion
from apps.directorio_unidades.models.core import Unidad

from apps.directorio_unidades.presentation.catalogos_publicos import _contexto
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.directorio_unidades.presentation.relaciones import relaciones_de
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_CENTRO

# Quién hace qué en un centro, por rol.
ROLES = (
    ('fas fa-user-tie', 'Administración del centro',
     'Planifica qué se produce, cuánto y cuándo; lleva las necesidades de insumos, mantenimiento y personal; aprueba '
     'las reservas y responde por los registros de producción.'),
    ('fas fa-home', 'Familias cuidadoras',
     'Viven en el centro y cuidan a diario los animales y los cultivos: ordeño, alimentación, riego, sanidad y '
     'cosecha. Registran lo que pasa cada día para que nada dependa de la memoria.'),
    ('fas fa-chalkboard-teacher', 'Docentes y carreras',
     'Planifican prácticas y ensayos en los ejes del centro con sus guías, y dirigen las tesis que se hacen en sus lotes.'),
    ('fas fa-user-graduate', 'Estudiantes',
     'Hacen prácticas de campo, ensayos de titulación y vinculación, con inducción de bioseguridad previa.'),
    ('fas fa-industry', 'Plantas piloto',
     'Reciben la materia prima del centro (leche, frutas, granos, café) y la transforman en productos y prácticas.'),
    ('fas fa-users', 'Visitantes',
     'Colegios, productores y turistas que recorren la finca con guía, en las fechas y los grupos que el centro abre.'),
)
# El ciclo con el que el centro deja de producir solo en temporada de prácticas.
CICLO = (
    ('Planificar', 'Cada eje fija qué producir, en qué lote o con qué animales, cuánto y cuándo, y qué necesita.'),
    ('Cuidar y producir', 'Las familias cuidadoras y el personal ejecutan las labores del calendario.'),
    ('Registrar', 'Cada labor, cosecha, ordeño o novedad sanitaria queda registrada el mismo día.'),
    ('Entregar', 'La producción va a su destino: una planta piloto, la venta, la semilla o las prácticas.'),
    ('Evaluar', 'Se compara lo producido con lo planificado y se ajusta el plan del siguiente ciclo.'),
)


def _centro(slug):
    return get_object_or_404(Unidad, slug=slug, dependencia='centro_experimental', activo=True)


def ejes_publicados(unidad):
    return unidad.ejes_productivos.filter(publicado=True).prefetch_related('imagenes').order_by('orden', 'titulo')


def _ficha(unidad):
    """Los datos con fuente y los usos del centro, del contenido documentado de cada uno."""
    from apps.centros_experimentales.operacion.management.centros.contenidos import CENTROS

    return CENTROS.get(unidad.slug, {})


def reservar_url(unidad):
    """La pestaña de reservas de la ficha, donde se piden prácticas, recorridos y servicios."""
    return f'{unidad.get_absolute_url()}#{MAPA_CENTRO.modulo_reservas}'


@xframe_options_sameorigin
def funcionamiento_view(request, slug):
    """1.4 · Cómo funciona el centro: quién hace qué, el ciclo de producción, sus datos, sus ejes y cómo se usa."""
    unidad = _centro(slug)
    ficha = _ficha(unidad)
    return render(request, 'portal/pages/unidades/centro/funcionamiento.html', {
        **_contexto(unidad, 'funcionamiento', request.user),
        'datos': ficha.get('datos', ()),
        'fuente_datos': ficha.get('fuente_datos', ''),
        'usos': ficha.get('usos', ()),
        'roles': ROLES,
        'ciclo': CICLO,
        'ejes': list(ejes_publicados(unidad)),
        'reservar_url': reservar_url(unidad),
    })


@xframe_options_sameorigin
def ejes_view(request, slug):
    """2.1 · Los ejes productivos del centro, cada uno con su foto, lo que produce y sus rubros."""
    unidad = _centro(slug)
    ejes = [{'eje': eje, 'portada': next(iter(eje.imagenes.all()), None)} for eje in ejes_publicados(unidad)]
    return render(request, 'portal/pages/unidades/centro/ejes.html', {
        **_contexto(unidad, 'ejes', request.user),
        'ejes': ejes,
    })


@xframe_options_sameorigin
def calendario_view(request, slug):
    """2.2 · Lo que hace cada eje en cada temporada, para planificar prácticas, visitas y cosechas."""
    unidad = _centro(slug)
    return render(request, 'portal/pages/unidades/centro/calendario.html', {
        **_contexto(unidad, 'calendario_productivo', request.user),
        'ejes': [eje for eje in ejes_publicados(unidad) if eje.temporadas],
    })


@xframe_options_sameorigin
def destino_view(request, slug):
    """3.4 · A dónde va lo que produce el centro: las plantas que abastece, con qué, y el destino de cada eje."""
    unidad = _centro(slug)
    return render(request, 'portal/pages/unidades/centro/destino.html', {
        **_contexto(unidad, 'destino', request.user),
        'abastece': _abastece(unidad),
        'ejes': [eje for eje in ejes_publicados(unidad) if eje.destinos],
    })


@xframe_options_sameorigin
def temas_view(request, slug):
    """5.1 · Los temas de investigación abiertos en los ejes del centro, con las prácticas de cada eje."""
    unidad = _centro(slug)
    ejes = [eje for eje in ejes_publicados(unidad) if eje.lista_temas]
    return render(request, 'portal/pages/unidades/centro/temas.html', {
        **_contexto(unidad, 'temas_investigacion', request.user),
        'ejes': ejes,
        'total': sum(len(eje.lista_temas) for eje in ejes),
        'reservar_url': reservar_url(unidad),
    })


@xframe_options_sameorigin
def eje_view(request, slug, codigo):
    """La página de un eje productivo, como la de un área de laboratorio: portada con foto, qué produce, cómo trabaja,
    su calendario, sus áreas, a dónde va lo que produce, para quién sirve, qué le falta, su investigación y sus videos."""
    from apps.gestion_unidades.presentation.edicion_registro import ediciones_de

    unidad = _centro(slug)
    eje = get_object_or_404(EjeProductivo, unidad=unidad, codigo=codigo, publicado=True)
    imagenes = list(eje.imagenes.all())
    return render(request, 'portal/pages/unidades/centro/eje.html', {
        'unidad': unidad,
        'eje': eje,
        'portada': imagenes[0] if imagenes else None,
        'galeria': imagenes,
        'videos': eje.lista_videos,
        'espacios': list(eje.espacios.filter(activo=True).order_by('orden', 'nombre')),
        'otros': list(ejes_publicados(unidad).exclude(pk=eje.pk)),
        'reservar_url': reservar_url(unidad),
        'puede_editar': 'eje_productivo' in ediciones_de(request.user, unidad),
    })


# --------------------------------------------------------------------- la gestión productiva (3.1)
class RegistroForm(forms.ModelForm):
    """Lo que se anota el mismo día: una cosecha, un ordeño, una postura, una labor, una entrega o una novedad."""

    class Meta:
        model = RegistroProduccion
        fields = ('ciclo', 'fecha', 'tipo', 'cantidad', 'unidad_medida', 'destino', 'detalle')
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, unidad, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ciclo'].queryset = (CicloProductivo.objects.filter(eje__unidad=unidad)
                                         .exclude(estado='cerrado').select_related('eje').order_by('eje__orden', 'nombre'))


def puede_registrar(usuario, unidad):
    """Registra la producción quien tiene el módulo de producción del centro (la administración, o quien ella delegue)."""
    return puede_operar_modulo_unidad(usuario, unidad, 'produccion')


def resumen_ciclo(ciclo):
    """Lo producido frente a la meta y el rendimiento por hectárea o por animal al día."""
    producido = ciclo.producido
    dias = max(((ciclo.fin or timezone.localdate()) - ciclo.inicio).days, 1)
    return {
        'ciclo': ciclo, 'producido': producido, 'cumplimiento': ciclo.cumplimiento,
        'barra': min(ciclo.cumplimiento or 0, 100),
        'por_ha': float(producido) / float(ciclo.superficie_ha) if producido and ciclo.superficie_ha else None,
        'por_animal_dia': (float(producido) / ciclo.animales / dias
                           if producido and ciclo.animales and not ciclo.superficie_ha else None),
    }


def _referencias(unidad):
    from apps.centros_experimentales.operacion.management.centros.contenidos import REFERENCIAS

    return [{'eje': eje, 'filas': REFERENCIAS[(unidad.slug, eje.codigo)]}
            for eje in ejes_publicados(unidad) if (unidad.slug, eje.codigo) in REFERENCIAS]


@xframe_options_sameorigin
def produccion_view(request, slug):
    """3.1 · El plan y los registros de producción: cada ciclo con su meta, lo producido y su cumplimiento, a dónde fue
    lo entregado en el año y las referencias con fuente para fijar metas. Los registros uno a uno, y quién los anotó,
    solo los ve quien gestiona la producción del centro; desde aquí mismo los anota."""
    unidad = _centro(slug)
    gestor = puede_registrar(request.user, unidad)
    if request.method == 'POST' and not gestor:
        raise PermissionDenied
    formulario = (RegistroForm(request.POST or None, unidad=unidad, initial={'fecha': timezone.localdate()})
                  if gestor else None)
    if request.method == 'POST' and formulario.is_valid():
        registro = formulario.save(commit=False)
        registro.registrado_por = request.user
        registro.save()
        messages.success(request, 'Registro guardado.')
        return redirect(f"{reverse('produccion_centro', args=[slug])}#registrar")
    ejes, total = [], 0
    for eje in ejes_publicados(unidad):
        ciclos = [resumen_ciclo(ciclo) for ciclo in eje.ciclos.select_related('lugar').order_by('estado', '-inicio')]
        total += len(ciclos)
        if ciclos or gestor:
            ejes.append({'eje': eje, 'ciclos': ciclos})
    anio = timezone.localdate().year
    destinos = dict(RegistroProduccion.DESTINOS)
    entregas = (RegistroProduccion.objects.filter(ciclo__eje__unidad=unidad, tipo='entrega', fecha__year=anio)
                .values('destino', 'unidad_medida').annotate(total=Sum('cantidad')).order_by('destino'))
    return render(request, 'portal/pages/unidades/centro/produccion.html', {
        **_contexto(unidad, 'registros_produccion', request.user),
        'ejes': ejes,
        'total_ciclos': total,
        'entregas': [{**fila, 'destino': destinos.get(fila['destino'], fila['destino'])} for fila in entregas],
        'anio': anio,
        'referencias': _referencias(unidad),
        'gestor': gestor,
        'formulario': formulario,
        'recientes': (RegistroProduccion.objects.filter(ciclo__eje__unidad=unidad)
                      .select_related('ciclo', 'registrado_por')[:30]) if gestor else (),
    })


def produccion_csv_view(request, slug):
    """Todos los registros de producción del centro en CSV, para quien gestiona su producción o sus reportes."""
    unidad = _centro(slug)
    if not (puede_registrar(request.user, unidad) or puede_operar_modulo_unidad(request.user, unidad, 'reportes')):
        raise PermissionDenied
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="produccion-{unidad.slug}.csv"'
    respuesta.write('\ufeff')
    escritor = csv.writer(respuesta)
    escritor.writerow(['Fecha', 'Eje', 'Ciclo', 'Rubro', 'Registro', 'Cantidad', 'Unidad', 'Destino', 'Detalle'])
    for registro in (RegistroProduccion.objects.filter(ciclo__eje__unidad=unidad)
                     .select_related('ciclo__eje').order_by('fecha', 'pk')):
        escritor.writerow([registro.fecha.isoformat(), registro.ciclo.eje.titulo, registro.ciclo.nombre,
                           registro.ciclo.rubro, registro.get_tipo_display(),
                           '' if registro.cantidad is None else registro.cantidad, registro.unidad_medida,
                           registro.get_destino_display() if registro.destino else '', registro.detalle])
    return respuesta


# --------------------------------------------------------------------- los cursos del centro (5.2)
def cursos_recomendados(unidad):
    """Los cursos que el centro debería dictar, por eje, con el curso del aula si ya está armado."""
    from apps.centros_experimentales.operacion.management.centros.contenidos import CURSOS_RECOMENDADOS
    from apps.formacion.models.cursos import Curso

    ejes = {eje.codigo: eje for eje in ejes_publicados(unidad)}
    armados = {curso.nombre: curso for curso in Curso.objects.filter(unidad=unidad, publicado=True, activo=True)}
    return [{'titulo': titulo, 'eje': ejes.get(codigo), 'horas': horas, 'para_quien': para_quien, 'por_que': por_que,
             'curso': armados.get(titulo)}
            for titulo, codigo, horas, para_quien, por_que in CURSOS_RECOMENDADOS.get(unidad.slug, ())]


def grupo_cursos_recomendados(unidad):
    """El grupo que la sección de cursos suma en un centro: los cursos que debería dictar."""
    from apps.formacion.presentation.aula import _boton

    recomendados = cursos_recomendados(unidad)
    if not recomendados:
        return None
    return {'nombre': 'Cursos recomendados', 'clave': 'cursos-recomendados', 'botones': [_boton(
        'cursos-recomendados', f'Cursos recomendados ({len(recomendados)})', reverse('cursos_centro', args=[unidad.slug]),
        'fas fa-list-ol', 'Los cursos que el centro debería dictar, uno o más por eje, y cómo pedirlos',
        subtitulo='Por eje productivo')]}


@xframe_options_sameorigin
def cursos_view(request, slug):
    """5.2 · Los cursos del centro: cómo se piden, se dictan y se certifican, y los recomendados por eje."""
    from apps.gestion_unidades.presentation.secciones_propias import puede_editar_secciones

    unidad = _centro(slug)
    return render(request, 'portal/pages/unidades/centro/cursos.html', {
        **_contexto(unidad, 'cursos', request.user),
        'recomendados': cursos_recomendados(unidad),
        'reservar_url': reservar_url(unidad),
        'gestor': puede_editar_secciones(request.user, unidad),
    })


@xframe_options_sameorigin
def como_reservar_view(request, slug):
    """6.1 · Cómo se reserva el centro: qué se reserva en cada eje, para quién, en qué áreas y temporada, los pasos,
    los recorridos guiados y lo que se cuida al entrar."""
    from apps.centros_experimentales.operacion.management.centros.contenidos import CUIDADOS, PASOS_RESERVA, USOS_RESERVABLES

    from apps.reservas.presentation.visitas import oferta_de_visitas

    unidad = _centro(slug)
    ejes = []
    for eje in ejes_publicados(unidad):
        espacios = list(eje.espacios.filter(activo=True).order_by('orden', 'nombre'))
        ejes.append({'eje': eje, 'espacios': espacios, 'visitable': any(espacio.visitable for espacio in espacios)})
    return render(request, 'portal/pages/unidades/centro/como_reservar.html', {
        **_contexto(unidad, 'como_reservar', request.user),
        'usos': USOS_RESERVABLES,
        'pasos': PASOS_RESERVA,
        'cuidados': CUIDADOS,
        'ejes': ejes,
        'visitas': oferta_de_visitas(unidad),
        'reservar_url': reservar_url(unidad),
    })


def _abastece(unidad):
    return list(unidad.relaciones_salientes.filter(tipo='abastece', activa=True, destino__activo=True)
                .select_related('destino'))


def carpetas_de_centro(unidad, mapa, claves, usuario):
    """Las secciones propias del mapa de los centros; las comunes (áreas, equipos, guías, cursos, reservas) las arma
    el aula. Ninguna sección se arma vacía: las que dependen de los ejes aparecen cuando el centro los define."""
    from apps.formacion.presentation.aula import _boton, _carpeta, _icono

    slug = unidad.slug
    carpetas = []

    def agregar(clave, identificador, botones):
        numero = mapa.numero(clave)
        if numero and mapa.modulo_de(numero) in claves and botones:
            carpetas.append(_carpeta(mapa.modulo_de(numero), identificador, '', _icono(mapa, numero),
                                     [{'nombre': '', 'botones': botones}], abierta=False, numero=numero,
                                     seccion=True, mapa=mapa))

    ejes = list(ejes_publicados(unidad))
    agregar('funcionamiento', 'ComoFunciona', [
        _boton('funcionamiento-centro', 'Cómo funciona el centro', reverse('funcionamiento_centro', args=[slug]),
               'fas fa-sitemap', 'Quién hace qué, el ciclo de producción, sus ejes y cómo se usa'),
    ])
    agregar('ejes', 'EjesProductivos', [
        _boton('ejes-centro', f'Todos los ejes ({len(ejes)})', reverse('ejes_centro', args=[slug]),
               'fas fa-layer-group', 'Qué produce cada eje, cómo trabaja y a dónde va'),
        *[_boton(f'eje-{eje.codigo}', eje.titulo, reverse('eje_centro', args=[slug, eje.codigo]), eje.icono,
                 eje.resumen, subtitulo='Eje productivo') for eje in ejes],
    ] if ejes else [])
    agregar('calendario_productivo', 'CalendarioProductivo', [
        _boton('calendario-centro', 'Calendario productivo', reverse('calendario_centro', args=[slug]),
               'fas fa-calendar-alt', 'Qué hace cada eje en cada temporada'),
    ] if any(eje.temporadas for eje in ejes) else [])
    abastece = _abastece(unidad)
    agregar('destino', 'DestinoProduccion', [
        _boton('destino-centro', 'A dónde va lo que produce', reverse('destino_centro', args=[slug]),
               'fas fa-truck-loading', 'Las plantas piloto que abastece y el destino de cada eje',
               subtitulo=f'{len(abastece)} planta{"s" if len(abastece) != 1 else ""} piloto' if abastece else ''),
    ] if abastece or any(eje.destinos for eje in ejes) else [])
    from apps.centros_experimentales.operacion.presentation.centro_simuladores import simuladores_de

    simuladores = simuladores_de(unidad)
    agregar('simuladores_campo', 'SimuladoresProduccion', [
        _boton('simuladores-centro', f'Simuladores de producción ({len(simuladores)})',
               reverse('simuladores_centro', args=[slug]), 'fas fa-calculator',
               'Cuánta leche, cosecha, huevos o café se puede esperar, con rendimientos publicados',
               subtitulo=' · '.join(simulador['nombre'] for simulador in simuladores)),
    ] if simuladores else [])
    gestor = usuario is not None and puede_registrar(usuario, unidad)
    ciclos = CicloProductivo.objects.filter(eje__unidad=unidad, eje__publicado=True).count()
    referencias = _referencias(unidad)
    agregar('registros_produccion', 'PlanRegistrosProduccion', [
        _boton('produccion-centro', 'Plan y registros de producción', reverse('produccion_centro', args=[slug]),
               'fas fa-clipboard-list', 'La meta de cada ciclo frente a lo producido, y a dónde fue lo entregado',
               subtitulo=f'{ciclos} ciclo{"s" if ciclos != 1 else ""}' if ciclos else 'Referencias para planificar'),
    ] if ciclos or referencias or gestor else [])
    agregar('temas_investigacion', 'TemasInvestigacion', [
        _boton('temas-centro', 'Temas de investigación abiertos', reverse('temas_centro', args=[slug]),
               'fas fa-search', 'Preguntas abiertas en los ejes, para tesis, prácticas y proyectos'),
    ] if any(eje.lista_temas for eje in ejes) else [])
    agregar('como_reservar', 'ComoReservar', [
        _boton('como-reservar-centro', 'Cómo se reserva, por eje', reverse('como_reservar_centro', args=[slug]),
               'fas fa-route', 'Prácticas, ensayos, recorridos y cursos: qué se reserva en cada eje y cómo'),
    ] if ejes else [])
    agregar('relaciones', 'UnidadesRelacionadas', [
        _boton('red-centro', 'Unidades relacionadas', f"{reverse('red_unidades')}?unidad={slug}",
               'fas fa-project-diagram', 'Las plantas que aloja y abastece, y los laboratorios que analizan sus muestras'),
    ] if relaciones_de(unidad) else [])
    return carpetas
