"""Composición entre unidades y capacidades de aplicaciones propietarias.

Las entradas publicas no cargan el controlador comun hasta recibir una
peticion. El detalle conserva los aliases por slug historicos, incluido el
prefijo laboratorio usado por plantas, para no romper enlaces publicados.
"""

from dataclasses import dataclass

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.presentation.tipologias import tipologia_activa, tipologias_publicas
from apps.directorio_unidades.contracts import ENTRADA_DIRECTORIO, TipoUnidad


@dataclass(frozen=True)
class Funcion:
    """Un grupo de expedientes que una unidad administra como bloque.

    Cada entrada de `modelos` es el nombre del modelo propietario o una terna
    (nombre, singular, plural) cuando la seccion lo llama de otra manera.
    """

    nombre: str
    descripcion: str
    modelos: tuple
    # El ícono con que se presenta el bloque (admin/includes/category_icon.html).
    icono: str = 'file'


def modelos_de(funcion):
    """Nombres de los modelos propietarios de una funcion, sin sus alias."""
    return tuple(entrada[0] if isinstance(entrada, tuple) else entrada
                 for entrada in funcion.modelos)


# Lo que una unidad administra, por bloques, con los modelos heredados que lo
# sostienen. Cada vertical declara cuales de estos bloques le aplican; los
# nombres se repiten entre tipos, los datos no: cada seccion solo ve lo suyo.
FUNCIONES_DE_UNIDAD = {
    'reservas': Funcion(
        'Reservas y agenda',
        'El expediente de cada solicitud: revisiones, cambios, avisos, participantes, '
        'archivos y programaciones.',
        ('Reserva', 'RevisionReserva', 'SolicitudCambioReserva', 'NotificacionReserva',
         'RegistroParticipanteReserva', 'ReservaAdjunto', 'ProgramacionReserva'),
        icono='calendar',
    ),
    'actividades': Funcion(
        'Actividades y prácticas',
        'Qué se puede pedir y con qué guía; asignaturas, temas y prácticas previstas '
        'frente a las realizadas.',
        ('CatalogoActividadReserva', 'GuiaActividadReserva', 'EjemploSolicitudUnidad',
         'Asignatura', 'TemaAsignatura', 'PlanificacionPractica', 'EjecucionPractica'),
        icono='academic',
    ),
    'cursos': Funcion(
        'Cursos y capacitaciones',
        'Cada curso con su presentación, sus ediciones por año, su programa de módulos y lecciones, '
        'y quienes se inscriben; se edita también en la página del curso.',
        ('Curso', 'ModuloCurso', 'InscripcionCurso'),
        icono='academic',
    ),
    'observacion': Funcion(
        'Indicadores y publicaciones',
        'Lo que produce un observatorio: indicadores con su ficha metodológica y sus valores, publicaciones '
        'con su calendario, encuestas propias, aliados, las solicitudes de datos que recibe, sus tableros y '
        'visores externos, su política de datos, cuántas veces se descargan, sus líneas temáticas, las '
        'conexiones automáticas que actualizan los indicadores y el historial de correcciones.',
        ('IndicadorObservatorio', 'PublicacionObservatorio', 'EncuestaObservatorio', 'AliadoObservatorio',
         'SolicitudDatos', 'TableroObservatorio', 'VisorExterno', 'PoliticaDatosObservatorio', 'DescargaDatos',
         'LineaObservatorio', 'ConectorIndicador', 'RevisionValor'),
        icono='reports',
    ),
    'agropecuaria': Funcion(
        'Producción agropecuaria',
        'Los ejes productivos de un centro experimental: qué produce cada uno, cómo trabaja, en qué temporada, con '
        'qué áreas, a dónde va lo que produce, para quién sirve, qué le falta para producir más, sus fotos y videos; '
        'y su gestión productiva: los ciclos con su meta y lo que se registra cada día.',
        (('EjeProductivo', 'Eje productivo', 'Ejes productivos'),
         ('CicloProductivo', 'Ciclo productivo', 'Ciclos productivos'),
         ('RegistroProduccion', 'Registro de producción', 'Registros de producción')),
        icono='production',
    ),
    'equipos': Funcion(
        'Equipos',
        'Los equipos que tiene cada unidad, con su ubicación y disponibilidad, y la ficha '
        'técnica de cada uno. Setenta y nueve de ochenta fichas pertenecen a una sola unidad.',
        (('UnidadEquipo', 'Equipo de la unidad', 'Equipos de la unidad'),
         ('EquiposServicios', 'Ficha técnica de equipo', 'Fichas técnicas de equipos'),
         ('PiezaEquipo', 'Pieza o accesorio del equipo', 'Piezas y accesorios de los equipos'),
         ('PrestamoEquipo', 'Préstamo de equipo', 'Préstamos de equipos')),
        icono='equipment',
    ),
    'mantenimiento': Funcion(
        'Mantenimiento y seguridad',
        'Incidencias, planes preventivos, órdenes y ciclo de vida de los equipos.',
        ('IncidenciaEquipo', 'PlanMantenimientoEquipo', 'MantenimientoEquipo',
         'EventoCicloVidaEquipo'),
        icono='maintenance',
    ),
    'inventario': Funcion(
        'Inventario e insumos',
        'Existencias, compatibilidad con equipos, lotes, entradas y movimientos financieros.',
        ('Consumible', 'ConsumiblePorEquipo', 'LoteConsumible', 'EntradaInventario',
         'MovimientoFinancieroUnidad'),
        icono='inventory',
    ),
    'produccion': Funcion(
        'Producción',
        'Familias, fichas, productos, recetas, planes de calidad, órdenes, lotes y salidas.',
        ('FamiliaProducto', 'FichaContenido', 'Producto', 'Receta', 'PlanCalidad', 'OrdenProduccion',
         'LoteProducto', 'MovimientoProducto'),
        icono='production',
    ),
    'areas': Funcion(
        'Fichas de las áreas',
        'Qué es cada área, cómo funciona, qué se puede hacer y con qué equipos, software y '
        'documentación; se publica en la página del área.',
        (('FichaArea', 'Ficha del área', 'Fichas de las áreas'),),
        icono='inventory',
    ),
    # Un laboratorio no produce por lotes: sus procesos son la forma de trabajar de cada área
    # y sus productos, lo que entrega. Son las mismas tablas de la producción, sin órdenes ni lotes.
    'procesos': Funcion(
        'Procesos y productos',
        'Los procesos que sigue la unidad, paso a paso, con sus equipos, insumos y controles, '
        'y los productos o servicios que entrega.',
        (('Producto', 'Producto o servicio', 'Productos y servicios'),
         ('Receta', 'Proceso', 'Procesos')),
        icono='production',
    ),
    'servicios': Funcion(
        'Servicios y fabricación',
        'Catálogo de servicios y solicitudes de fabricación.',
        ('FablabService', 'SolicitudFabricacion'),
        icono='services',
    ),
    'seguridad': Funcion(
        'Seguridad y desechos',
        'Registro de desechos peligrosos y especiales: qué se generó, cuánto, y a qué gestor autorizado '
        'se entregó con qué manifiesto.',
        ('RegistroDesecho',),
        icono='shield',
    ),
    'expediente': Funcion(
        'Expediente de calidad',
        'Los documentos que la institución exige a la unidad por año de gestión, en sus cuatro carpetas: '
        'aquí se validan u observan los que la unidad cargó, y se lee lo que redactó con el editor guiado.',
        ('DocumentoExpediente', 'DocumentoElaborado'),
        icono='file',
    ),
    'trazabilidad': Funcion(
        'Indicadores y trazabilidad',
        'Reporte operativo, registro de lo que se hizo, adjuntos gobernados, artefactos, '
        'puestas en marcha de microproyectos y sesiones de navegador remoto.',
        ('ReporteOperativoUnidad', 'RegistroAuditoriaUnidad', 'Adjunto', 'ArtefactoExterno',
         'ResultadoArtefacto', 'DespliegueMicroproyecto', 'SesionNavegador'),
        icono='reports',
    ),
}


def catalogo_unidades(request, tipo: TipoUnidad):
    from apps.directorio_unidades.presentation.catalogo import catalogo_unidades as heredado

    if tipo is ENTRADA_DIRECTORIO and not tipologia_activa(tipo.value):
        return _primer_catalogo_publico()
    return heredado(request, tipo.value, tipo.contexto, tipo.titulo)


def _primer_catalogo_publico():
    """Redirige al primer tipo activo; sin ninguno, la puerta si se cierra."""
    publicas = tipologias_publicas()
    if not publicas:
        raise Http404
    primera = publicas[0]
    if primera.codigo in {tipo.value for tipo in TipoUnidad}:
        return redirect(reverse(TipoUnidad(primera.codigo).ruta_catalogo))
    return redirect(reverse('catalogo_tipologia', kwargs={'tipologia': primera.codigo}))


def detalle_unidad(request, slug):
    from apps.gestion_unidades.presentation.detalle import proyecto_detalle_view

    return proyecto_detalle_view(request, slug)


def modelo_unidad():
    """Modelo del directorio común, para declarar un registro delegado por tipo.

    Las verticales acceden mediante este contrato al catálogo común de unidades.
    Sus expedientes operativos conservan los propietarios definidos en apps/.
    """
    from apps.directorio_unidades.models.core import Unidad

    return Unidad


def administracion_por_tipologia():
    """Seccion de administracion acotada a las tipologias de una vertical."""
    from apps.directorio_unidades.admin.unidades import UnidadDeTipologiaAdmin

    return UnidadDeTipologiaAdmin


def modelos_de_funciones(app_label, funciones, espacio):
    """Un modelo delegado por cada expediente de las funciones declaradas.

    Se crean en el modulo de modelos de la vertical (`espacio` son sus
    globals) con el mismo nombre que el heredado: `plantas_piloto.Reserva`
    es la seccion de reservas de las plantas, con sus propios permisos y su
    propia URL, sobre la misma tabla. Sin datos copiados ni sincronizados.
    """
    import apps.integraciones.modelos as heredados

    creados = []
    for clave in funciones:
        for entrada in FUNCIONES_DE_UNIDAD[clave].modelos:
            nombre, singular, plural = entrada if isinstance(entrada, tuple) else (entrada, None, None)
            base = getattr(heredados, nombre)
            meta = type('Meta', (), {
                'proxy': True,
                'app_label': app_label,
                'verbose_name': singular or base._meta.verbose_name,
                'verbose_name_plural': plural or base._meta.verbose_name_plural,
            })
            proxy = type(nombre, (base,), {
                '__module__': espacio['__name__'], 'Meta': meta, 'funcion': clave,
            })
            espacio[nombre] = proxy
            creados.append(proxy)
    return tuple(creados)


def administracion_de_funciones(modulo_modelos, base_tipologia):
    """Registra un panel por cada modelo delegado, acotado a la tipologia.

    El panel hereda del que ya administra el modelo heredado (mismas
    columnas, filtros, acciones y formularios) y solo anade el recorte por
    tipo de unidad.
    """
    from django.contrib import admin

    import apps.directorio_unidades.admin.catalogos  # noqa: F401 - registra los paneles heredados primero
    from apps.integraciones.admin.por_tipo import panel_acotado

    for proxy in modulo_modelos.MODELOS_DE_FUNCION:
        # El heredado inmediato: algun expediente ya es delegado de otro modelo.
        original = admin.site._registry[proxy._meta.proxy_for_model].__class__
        admin.site.register(proxy, panel_acotado(original, proxy, base_tipologia))
