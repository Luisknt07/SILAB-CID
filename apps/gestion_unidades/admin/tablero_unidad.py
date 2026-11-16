"""Tablero de una unidad de cualquier tipo: todo lo suyo, con cada lista ya filtrada a ella.

Cada fila dice qué es el registro, cuántos tiene esa unidad y lleva a su lista; en
una planta piloto, además, en qué sección de su ficha pública aparece. El área de
cada tipo entra por unidad con `resumen_de_unidades`. Solo se muestra lo que la
cuenta puede abrir.
"""
from django.apps import apps
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, reverse

from apps.integraciones.unidades import FUNCIONES_DE_UNIDAD, modelos_de

from apps.gestion_unidades.admin.contenidos_ficha import url_contenidos
from apps.gestion_unidades.admin.estado_unidad import url_estado

# Qué es cada herramienta, en una frase; también rotula las tarjetas del área.
DESCRIPCIONES = {
    'Reserva': 'Solicitudes de uso de la unidad: fecha, espacio, equipos y estado.',
    'RevisionReserva': 'Historial de aprobaciones, observaciones y rechazos de cada reserva.',
    'SolicitudCambioReserva': 'Pedidos de cambio de fecha, hora o recursos de una reserva.',
    'NotificacionReserva': 'Avisos enviados a solicitantes y responsables.',
    'RegistroParticipanteReserva': 'Personas inscritas en cada reserva y su asistencia.',
    'ReservaAdjunto': 'Archivos técnicos que acompañan una reserva.',
    'ProgramacionReserva': 'Sesiones programadas de una práctica en el calendario.',
    'CatalogoActividadReserva': 'Actividades que se pueden solicitar en la unidad.',
    'GuiaActividadReserva': 'Guías de práctica (FT04) con su versión y estado de aprobación.',
    'EjemploSolicitudUnidad': 'Ejemplos de redacción que orientan al solicitante.',
    'Asignatura': 'Asignaturas que usan la unidad.',
    'TemaAsignatura': 'Temas de cada asignatura vinculados a prácticas.',
    'Curso': 'Cursos y capacitaciones con su presentación y sus ediciones por año.',
    'PlanificacionPractica': 'Planificación de las prácticas: qué, cuándo y con qué guía.',
    'EjecucionPractica': 'Ejecución de las prácticas: asistencia, bitácora y evidencias.',
    'UnidadEquipo': 'Equipos físicos de la unidad: código, ubicación y disponibilidad.',
    'EquiposServicios': 'Ficha técnica de cada modelo de equipo.',
    'PiezaEquipo': 'Piezas y accesorios de los equipos.',
    'PrestamoEquipo': 'Salidas de equipos y su devolución.',
    'IncidenciaEquipo': 'Fallas reportadas en equipos y su atención.',
    'PlanMantenimientoEquipo': 'Mantenimientos preventivos programados por equipo.',
    'MantenimientoEquipo': 'Órdenes de mantenimiento realizadas.',
    'EventoCicloVidaEquipo': 'Altas, traslados y bajas de cada equipo.',
    'Consumible': 'Insumos y reactivos: existencias y mínimo de alerta.',
    'ConsumiblePorEquipo': 'Qué insumos usa cada equipo.',
    'LoteConsumible': 'Lotes de insumos con su vencimiento.',
    'EntradaInventario': 'Ingresos de insumos al inventario.',
    'MovimientoFinancieroUnidad': 'Ingresos y gastos de la unidad.',
    'RegistroDesecho': 'Desechos generados y su entrega a gestor autorizado.',
    'DocumentoExpediente': 'Documentos que la institución exige y su validación.',
    'DocumentoElaborado': 'Documentos redactados con el editor guiado.',
    'FamiliaProducto': 'Líneas de producto; agrupan procesos, guías y catálogo.',
    'FichaContenido': 'Estado de publicación de cada producto, proceso, equipo y simulador.',
    'Producto': 'Productos de la planta; sin receta se muestran como ficha del producto.',
    'Receta': 'Procesos técnicos: etapas, insumos y salidas de cada producto.',
    'PlanCalidad': 'Controles de calidad y HACCP por familia, con sus parámetros.',
    'OrdenProduccion': 'Corridas de producción planificadas y ejecutadas.',
    'LoteProducto': 'Lotes producidos, con su control de calidad y vencimiento.',
    'MovimientoProducto': 'Salidas de producto: ventas, donaciones y mermas.',
    'FablabService': 'Servicios que la unidad ofrece, con sus tarifas.',
    'SolicitudFabricacion': 'Pedidos de servicio recibidos.',
    'ReporteOperativoUnidad': 'Reporte operativo del período.',
    'RegistroAuditoriaUnidad': 'Registro de quién hizo qué en la unidad.',
    'Adjunto': 'Documentos gobernados del repositorio: planos, normas, datasets, plantillas.',
    'ArtefactoExterno': 'Simuladores y herramientas externas vinculadas a una familia.',
    'ResultadoArtefacto': 'Resultados importados desde los artefactos externos.',
    'DespliegueMicroproyecto': 'Puestas en marcha de microproyectos Django.',
    'SesionNavegador': 'Sesiones del navegador remoto para sitios externos.',
    **dict.fromkeys(('Laboratorio', 'PlantaPiloto', 'CentroExperimental', 'Observatorio'),
                    'La lista de unidades del tipo: cada una abre su ficha; «Nuevo» crea otra, que aparece con su tablero.'),
    # Configuración institucional, portal, calendario, usuarios y catálogos.
    'RevisionPresentacion': 'Nombre, marca y presentación pública de la institución, con borradores e historial.',
    'RevisionCatalogoAcademico': 'Facultades, carreras y asignaturas que usa la plataforma, por revisiones.',
    'RevisionNivelesAcademicos': 'Niveles académicos (grado, posgrado…) y a quiénes aplican, por revisiones.',
    'RevisionPoliticaCalendario': 'Reglas del calendario: días hábiles, feriados y plazos, por revisiones.',
    'EstadoCapacidad': 'Qué funciones de la plataforma están habilitadas en la institución.',
    'CambioCapacidad': 'Quién habilitó o retiró cada función, cuándo y por qué.',
    'RevisionInicio': 'La portada del portal: mensajes, destacados y accesos, con borradores e historial.',
    'CentroID': 'Los centros de investigación y desarrollo, con su propósito y área prioritaria.',
    'PeriodoAcademico': 'Los períodos académicos (PAO) y su estado de publicación.',
    'VersionCalendarioAcademico': 'Versiones aprobadas del calendario de cada período, con sus reformas.',
    'SemanaAcademica': 'Las semanas de cada período: clases, evaluación, recuperación o vacaciones.',
    'VinculacionUsuarioPeriodo': 'Cómo se clasifica cada persona en cada período, sin reescribir reportes pasados.',
    'Decanato': 'Las cuentas de decanato y la dependencia que representa cada una.',
    'DependenciaAcademica': 'Decanatos y dependencias a los que se adscriben las unidades y que reciben su informe.',
    'TipologiaUnidad': 'Los tipos de unidad de la institución y la implementación que usa cada uno.',
    'Categoria': 'Subáreas de conocimiento con que se clasifican las unidades.',
    'TipoLaboratorio': 'Modos de uso de una unidad: docencia, investigación, innovación, servicios.',
    'Site': 'El dominio del sitio: lo usan los inicios de sesión externos y los enlaces de los correos.',
    'CategoriaEquipo': 'Categorías con que se agrupan los equipos de todas las unidades.',
    'DocumentoExigido': 'Los documentos que la institución exige a las unidades cada año y su periodicidad.',
    'PoliticaDeCalidad': 'Con qué se mide el cumplimiento del expediente: mínimo y penalización por atraso.',
    'SedeInstitucional': 'Las sedes y campus, con su contorno y edificios en el mapa de ubicación.',
}

# Las cifras de cada tarjeta del área, por tipo de unidad.
CIFRAS_COMUNES = (('UnidadEquipo', 'equipos'), ('Reserva', 'reservas'), ('Consumible', 'insumos'))
CIFRAS = {
    'plantas_piloto': (('Producto', 'productos'), ('Receta', 'procesos'), ('UnidadEquipo', 'equipos'),
                       ('Reserva', 'reservas')),
}

# El ícono de cada pestaña de la ficha en el tablero.
ICONOS_DE_PESTANA = {
    'informacion-general': 'file', 'procesos-protocolos': 'production', 'equipos-infraestructura': 'equipment',
    'produccion-lotes': 'inventory', 'calidad-inocuidad': 'shield', 'reservas-servicios': 'calendar',
    'areas-equipos': 'equipment', 'procesos-productos': 'production', 'docencia-capacitacion': 'academic',
    'investigacion-formativa': 'reports',
}

# La ficha pública de un laboratorio, pestaña por pestaña: qué la alimenta y en qué sección aparece.
FICHA_LABORATORIO = (
    ('informacion-general', 'Información general', '1.1 a 1.6',
     (('Adjunto', '1.5 Repositorio y descargas'),)),
    ('areas-equipos', 'Áreas y equipos', '2.1 a 2.4',
     (('UnidadEquipo', '2.1 y 2.2'), ('EquiposServicios', '2.2 Equipos y fichas técnicas'))),
    ('procesos-productos', 'Procesos y productos', '3.1 a 3.3',
     (('Receta', '3.1 Procesos y 3.2 Métodos'), ('Producto', '3.3 Productos y servicios'))),
    ('docencia-capacitacion', 'Docencia y capacitación', '4.1 a 4.4',
     (('GuiaActividadReserva', '4.1 (las publicadas)'), ('Asignatura', '4.2 Asignaturas y carreras'),
      ('Curso', '4.3 Cursos y capacitaciones'), ('ArtefactoExterno', '4.4 Recursos de aprendizaje y simuladores'))),
    ('reservas-servicios', 'Reservas y servicios', '5.1 a 5.7',
     (('FablabService', '5.2 Servicios y tarifas'), ('Reserva', '5.1 y 5.3'))),
)

# La ficha pública de una planta, pestaña por pestaña: qué la alimenta y en qué sección aparece.
FICHA_PUBLICA = (
    ('informacion-general', 'Información general', '1.1 a 1.6',
     (('Adjunto', '1.5 Repositorio y descargas'),)),
    ('procesos-protocolos', 'Procesos y protocolos', '2.1 a 2.6',
     (('FamiliaProducto', 'Subcarpetas de 2.1 y 2.6'), ('Receta', '2.1 a 2.5'),
      ('ArtefactoExterno', '2.4 Simuladores'), ('GuiaActividadReserva', '2.6 (las publicadas)'))),
    ('equipos-infraestructura', 'Equipos e infraestructura', '3.1 a 3.4',
     (('UnidadEquipo', '3.1 y 3.2'), ('EquiposServicios', '3.2 Fichas de equipo'))),
    ('produccion-lotes', 'Producción y lotes', '4.1 a 4.6',
     (('Producto', '4.1 y, sin receta, 2.1'), ('OrdenProduccion', '4.5 Corridas'), ('LoteProducto', '4.5 Lotes'))),
    ('calidad-inocuidad', 'Calidad e inocuidad', '5.1 a 5.5',
     (('PlanCalidad', '5.1, 5.3 y 5.4'),)),
    ('reservas-servicios', 'Reservas y servicios', '6.1 a 6.7',
     (('FablabService', '6.2 Catálogo de servicios'), ('Reserva', '6.1 y 6.3'))),
)
FICHAS_PUBLICAS = {'plantas_piloto': FICHA_PUBLICA, 'laboratorios': FICHA_LABORATORIO}


def _panel(app_label, nombre):
    """El panel de una herramienta en la sección de un tipo, o None si ese tipo no la tiene."""
    try:
        return admin.site._registry.get(apps.get_model(app_label, nombre))
    except LookupError:
        return None


def fila_de_expediente(request, unidad, app_label, nombre, seccion='', icono='file'):
    panel = _panel(app_label, nombre)
    if panel is None or not panel.has_view_or_change_permission(request):
        return None
    modelo = panel.model
    etiqueta = modelo._meta.model_name
    nuevo = ''
    if panel.has_add_permission(request):
        try:
            nuevo = reverse(f'admin:{app_label}_{etiqueta}_add')
        except NoReverseMatch:
            nuevo = ''
        # Si la unidad es un campo directo, el formulario llega con la unidad elegida.
        if nuevo and '__' not in panel.ruta:
            nuevo += f'?{panel.ruta}={unidad.pk}'
    return {
        'nombre': str(modelo._meta.verbose_name_plural).capitalize(),
        'icono': icono,
        'descripcion': DESCRIPCIONES.get(nombre, ''),
        'seccion': seccion,
        'total': panel.get_queryset(request).filter(**{panel.ruta: unidad}).count(),
        'lista': reverse(f'admin:{app_label}_{etiqueta}_changelist') + f'?{panel.parametro_unidad}={unidad.pk}',
        'nuevo': nuevo,
    }


def estado_de_la_ficha(unidad, *, revisar_pendientes=True):
    """La revisión editorial completa se solicita aparte del tablero operativo."""
    from apps.recursos.models.recursos import ModuloUnidad
    modulos = list(ModuloUnidad.objects.filter(unidad=unidad).order_by('orden'))
    estado = {'desactivados': [m.nombre for m in modulos if not m.activo],
              'pendientes': [], 'revisado': revisar_pendientes}
    if revisar_pendientes:
        from apps.formacion.presentation.aula import contexto_aula
        carpetas = contexto_aula(unidad, [m for m in modulos if m.activo])['aula']['carpetas']
        estado['pendientes'] = [f"{c['numero']} {c['titulo']}" for c in carpetas
                                if c.get('numero') and c.get('pendiente')]
    return estado


def tablero(request, unidad, app_label):
    """Grupos del tablero: en una planta, su ficha pública por pestaña; después, la operación de la unidad."""
    mostrados = set()
    ficha = []
    for clave, titulo, secciones, modelos in FICHAS_PUBLICAS.get(app_label, ()):
        filas = [f for f in (fila_de_expediente(request, unidad, app_label, nombre, seccion,
                                                ICONOS_DE_PESTANA[clave]) for nombre, seccion in modelos) if f]
        mostrados.update(nombre for nombre, _ in modelos)
        ficha.append({'titulo': titulo, 'secciones': secciones, 'filas': filas})
    operacion = []
    for clave in apps.get_app_config(app_label).models_module.FUNCIONES:
        funcion = FUNCIONES_DE_UNIDAD[clave]
        filas = [f for f in (fila_de_expediente(request, unidad, app_label, nombre, icono=funcion.icono)
                             for nombre in modelos_de(funcion) if nombre not in mostrados) if f]
        if clave == 'cursos':
            from apps.formacion.admin.cursos import consultas_formacion_de_unidad
            filas.extend(consultas_formacion_de_unidad(request, unidad))
        if filas:
            operacion.append({'titulo': funcion.nombre, 'secciones': funcion.descripcion, 'filas': filas})
    return {'ficha': ficha, 'operacion': operacion}


def _conteos(request, app_label, nombre):
    """Cuántos registros tiene cada unidad en una herramienta, en una sola consulta; None si no se ve."""
    panel = _panel(app_label, nombre)
    if panel is None or not panel.has_view_or_change_permission(request):
        return None
    return dict(panel.get_queryset(request).order_by().values_list(panel.ruta)
                .annotate(total=Count('pk', distinct=True)).values_list(panel.ruta, 'total'))


def url_tablero(modelo_admin, unidad):
    opciones = modelo_admin.model._meta
    return reverse(f'admin:{opciones.app_label}_{opciones.model_name}_tablero', args=[unidad.pk])


def resumen_de_unidades(request, modelo_admin):
    """Una tarjeta por unidad visible para la cuenta, con sus cifras clave; None si no puede ver las unidades."""
    if not modelo_admin.has_view_or_change_permission(request):
        return None
    opciones = modelo_admin.model._meta
    conteos = [(rotulo, conteo) for nombre, rotulo in CIFRAS.get(opciones.app_label, CIFRAS_COMUNES)
               if (conteo := _conteos(request, opciones.app_label, nombre)) is not None]
    return [{
        'nombre': unidad.nombre,
        'activa': unidad.activo,
        'cifras': [(conteo.get(unidad.pk, 0), rotulo) for rotulo, conteo in conteos],
        'tablero': url_tablero(modelo_admin, unidad),
        'contenidos': url_contenidos(modelo_admin, unidad),
        'ficha': reverse(f'admin:{opciones.app_label}_{opciones.model_name}_change', args=[unidad.pk]),
    } for unidad in modelo_admin.get_queryset(request).order_by('nombre')]


def vista_tablero(modelo_admin, request, object_id):
    """La página del tablero; fuera del alcance de la cuenta, la unidad no existe."""
    unidad = get_object_or_404(modelo_admin.get_queryset(request), pk=object_id)
    if not modelo_admin.has_view_or_change_permission(request, unidad):
        raise PermissionDenied
    opciones = modelo_admin.model._meta
    return TemplateResponse(request, 'admin/unidades/tablero.html', {
        **modelo_admin.admin_site.each_context(request), **tablero(request, unidad, opciones.app_label),
        'title': f'Tablero · {unidad.nombre}', 'unidad': unidad, 'opts': opciones,
        'estado': estado_de_la_ficha(unidad, revisar_pendientes=request.GET.get('revisar_ficha') == '1'),
        'contenidos_url': url_contenidos(modelo_admin, unidad),
        'ficha_url': reverse(f'admin:{opciones.app_label}_{opciones.model_name}_change', args=[unidad.pk]),
        'estado_unidad_url': url_estado(modelo_admin, unidad),
    })
