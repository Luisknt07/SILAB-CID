"""Registro explícito de medios: una ruta existente no concede acceso."""
from functools import lru_cache
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.http import Http404

from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

# Solo campos destinados a la ficha pública. Los demás se deniegan por defecto.
PUBLICOS = {
    'Unidad': ('imagen', 'plano_espacios'), 'SoftwareDisponible': ('logo',),
    'EquiposServicios': ('imagen', 'manual_operacion', 'ficha_tecnica', 'video_montaje_cuidados', 'explicacion_drivers'),
    'FotoEquipo': ('imagen',), 'Consumible': ('imagen', 'ficha_tecnica'),
    'VersionCalendarioAcademico': ('documento',), 'EspacioReservable': ('imagen',),
    'ResponsableUnidad': ('foto',), 'ImagenEje': ('imagen',), 'MedioInterior': ('imagen',),
    'NovedadUnidad': ('imagen',), 'ElementoFichaArea': ('foto',), 'SeccionPropia': ('imagen',),
    'ElementoSeccionPropia': ('imagen',), 'PortadaPestana': ('imagen',), 'Curso': ('imagen',),
    'FablabService': ('imagen_referencial',), 'ImagenLinea': ('imagen',),
    'PublicacionObservatorio': ('archivo',), 'CentroID': ('imagen',), 'ImagenCentro': ('imagen',),
    'PlanoCentro': ('imagen',), 'EquipoCentro': ('imagen',), 'Integrante': ('foto',),
    'Aliado': ('logo',), 'Proyecto': ('imagen',), 'Resultado': ('archivo',), 'CasoExito': ('imagen',),
    'Novedad': ('imagen',), 'DocumentoCentro': ('archivo',), 'RecursoCentro': ('archivo',),
}
PRIVADOS = {
    'UserProfile': ('avatar',), 'PrestamoEquipo': ('acta',),
    'MovimientoFinancieroUnidad': ('comprobante',), 'GuiaActividadReserva': ('archivo',),
    'ReservaAdjunto': ('archivo',), 'ImagenGuiaActividad': ('imagen',),
    'SolicitudFabricacion': ('comprobante_pago',), 'IncidenciaEquipo': ('evidencia',),
    'MantenimientoEquipo': ('informe',), 'EventoCicloVidaEquipo': ('evidencia',),
    'RegistroDesecho': ('documento',), 'TraspasoEquipo': ('acta_firmada',),
    'EvidenciaPractica': ('archivo',), 'ResultadoArtefacto': ('archivo',),
}
MODULOS = {
    'PrestamoEquipo': 'recursos', 'MovimientoFinancieroUnidad': 'finanzas',
    'IncidenciaEquipo': 'mantenimiento', 'MantenimientoEquipo': 'mantenimiento',
    'EventoCicloVidaEquipo': 'mantenimiento', 'RegistroDesecho': 'seguridad',
    'TraspasoEquipo': 'recursos', 'ResultadoArtefacto': 'recursos',
}


@lru_cache(maxsize=1)
def _registro():
    filas = []
    for modelo in apps.get_models():
        if modelo._meta.proxy:
            continue
        nombre = modelo.__name__
        for campo in PUBLICOS.get(nombre, ()) + PRIVADOS.get(nombre, ()):
            subida = modelo._meta.get_field(campo).upload_to
            # Las funciones históricas también pueden conservar rutas de importación.
            prefijo = subida if isinstance(subida, str) else ''
            filas.append((modelo, campo, prefijo, nombre in PRIVADOS))
    return tuple(sorted(filas, key=lambda fila: not fila[3]))


def _propietario(usuario, objeto, *campos):
    return bool(usuario.is_authenticated and usuario.is_active and any(
        getattr(objeto, campo + '_id', None) == usuario.pk for campo in campos))


def _operador(usuario, unidad, modulo):
    return bool(unidad and puede_operar_modulo_unidad(usuario, unidad, modulo))


def _privado_permitido(request, objeto):
    nombre = type(objeto).__name__
    usuario = request.user
    if nombre == 'UserProfile':
        return _propietario(usuario, objeto, 'user')
    if nombre == 'GuiaActividadReserva':
        from apps.reservas.presentation.guias import _puede_ver_guia
        return objeto.activo and _puede_ver_guia(usuario, objeto)
    if nombre == 'ImagenGuiaActividad':
        return (_propietario(usuario, objeto, 'subido_por') if not objeto.guia_id
                else _privado_permitido(request, objeto.guia))
    if nombre == 'ReservaAdjunto':
        reserva = objeto.reserva
        return (_propietario(usuario, reserva, 'usuario')
                or _operador(usuario, reserva.laboratorio, 'reservas'))
    if nombre == 'SolicitudFabricacion':
        return (_propietario(usuario, objeto, 'solicitante')
                or _operador(usuario, objeto.unidad, 'reservas'))
    if nombre == 'EvidenciaPractica':
        from apps.formacion.presentation.practicas import _obtener_plan_visible
        plan = objeto.ejecucion.planificacion
        if not usuario.is_authenticated or not usuario.is_active:
            return False
        _obtener_plan_visible(request, plan.unidad.slug, plan.pk)
        return True
    if nombre == 'TraspasoEquipo':
        return any(_operador(usuario, unidad, MODULOS[nombre])
                   for unidad in (objeto.unidad_origen, objeto.unidad_destino))
    if nombre == 'EventoCicloVidaEquipo' and (
        objeto.tipo in ('baja', 'disposicion')
        or (objeto.tipo == 'actualizacion' and objeto.descripcion.startswith('Retiro/sustitución: '))
    ):
        return any(_operador(usuario, objeto.unidad, modulo) for modulo in ('recursos', 'mantenimiento'))
    unidad = objeto.artefacto.unidad if nombre == 'ResultadoArtefacto' else objeto.unidad
    return (_operador(usuario, unidad, MODULOS[nombre])
            or (nombre == 'PrestamoEquipo' and _propietario(usuario, objeto, 'solicitante')))


def _publico_permitido(request, objeto):
    nombre = type(objeto).__name__
    if nombre == 'ResponsableUnidad':
        from apps.gestion_unidades.presentation.secciones_propias import puede_editar_secciones

        return objeto.activo and (
            (objeto.publico and objeto.unidad.activo)
            or _propietario(request.user, objeto, 'usuario')
            or puede_editar_secciones(request.user, objeto.unidad)
        )
    componente = getattr(objeto, 'componente', None)
    centro = getattr(objeto, 'centro', None) or getattr(componente, 'centro', None)
    if nombre == 'CentroID':
        centro = objeto
    if nombre == 'RecursoCentro':
        carpeta = objeto.carpeta
        return objeto.activo and carpeta.activa and (
            (carpeta.visibilidad == 'publica' and carpeta.centro.activo)
            or carpeta.centro.puede_gestionar(request.user))
    if centro:
        from apps.centros_id.escenarios import contenido_admitido
        gestor = centro.puede_gestionar(request.user)
        if not centro.activo and not gestor:
            return False
        if nombre == 'DocumentoCentro':
            return gestor or (objeto.publico and objeto.estado_documental != 'borrador' and contenido_admitido(objeto))
        if nombre == 'Resultado':
            return gestor or (objeto.publicado and contenido_admitido(objeto)
                              and not objeto.confidencial and objeto.acceso_abierto)
        if not gestor and ((componente and not componente.publicado)
                           or (nombre == 'Integrante' and objeto.rol in {'tesista', 'estudiante'})):
            return False
        if not gestor and hasattr(objeto, 'es_muestra') and not contenido_admitido(objeto):
            return False
    if nombre == 'PublicacionObservatorio':
        return objeto.estado == 'publicada' or _operador(request.user, objeto.unidad, 'recursos')
    return all(getattr(objeto, campo, True) for campo in ('activo', 'activa', 'publicado', 'publicada', 'vigente'))


def autorizar_archivo(request, relativa):
    """Requiere registro y aplica su política antes de abrir el archivo.

    Devuelve si el archivo está publicado para cualquier visitante. Lo que se
    entrega por un permiso (titular, gestor, operador) nunca lo está.
    """
    for modelo, campo, prefijo, privado in _registro():
        if prefijo and '%' not in prefijo and not relativa.startswith(prefijo):
            continue
        objeto = modelo.objects.filter(**{campo: relativa}).first()
        if objeto is None:
            continue
        permitido = _privado_permitido(request, objeto) if privado else _publico_permitido(request, objeto)
        if not permitido:
            raise Http404()
        if privado:
            return False
        return bool(request.user.is_anonymous
                    or _publico_permitido(SimpleNamespace(user=AnonymousUser()), objeto))
    raise Http404()
