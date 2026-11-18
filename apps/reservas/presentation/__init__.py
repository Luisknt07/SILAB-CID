"""Entradas p?blicas de reservas; se cargan al utilizar cada caso de uso."""
from importlib import import_module

_ENTRADAS = {'buscar_usuarios_reserva': 'apps.reservas.presentation.views.buscar_usuarios_reserva', 'cancelar_reserva_usuario': 'apps.reservas.presentation.views.cancelar_reserva_usuario', 'valorar_reserva_usuario': 'apps.reservas.presentation.valoraciones.valorar_reserva_usuario', 'cotizar_servicios_reserva': 'apps.reservas.presentation.views.cotizar_servicios_reserva', 'proponer_entrega_servicio': 'apps.reservas.presentation.views.proponer_entrega_servicio', 'crear_reserva': 'apps.reservas.presentation.views.crear_reserva', 'obtener_reservas_usuario': 'apps.reservas.presentation.views.obtener_reservas_usuario', 'seleccion_por_proceso_view': 'apps.reservas.presentation.proceso.seleccion_por_proceso_view', 'completar_sesion_view': 'apps.reservas.presentation.cronograma.completar_sesion_view', 'fechas_programacion_view': 'apps.reservas.presentation.cronograma.fechas_programacion_view', 'mis_sesiones_view': 'apps.reservas.presentation.cronograma.mis_sesiones_view', 'cambiar_estado_guia_practica': 'apps.reservas.presentation.guias.cambiar_estado_guia_practica', 'editar_guia_practica': 'apps.reservas.presentation.guias.editar_guia_practica', 'formatear_bibliografia_guia': 'apps.reservas.presentation.guias.formatear_bibliografia_guia', 'guardar_contenido_guia': 'apps.reservas.presentation.guias.guardar_contenido_guia', 'lista_guias_practica': 'apps.reservas.presentation.guias.lista_guias_practica', 'subir_figura_guia': 'apps.reservas.presentation.guias.subir_figura_guia', 'subir_guia_firmada': 'apps.reservas.presentation.guias.subir_guia_firmada', 'vista_previa_pdf_guia': 'apps.reservas.presentation.guias.vista_previa_pdf_guia', 'ver_guia_actividad': 'apps.reservas.presentation.guias.ver_guia_actividad', 'comprobante_reserva': 'apps.reservas.presentation.notificaciones_views.comprobante_reserva', 'comprobante_reserva_pdf': 'apps.reservas.presentation.notificaciones_views.comprobante_reserva_pdf', 'subir_comprobante_pago': 'apps.reservas.presentation.notificaciones_views.subir_comprobante_pago', 'marcar_notificaciones_leidas': 'apps.reservas.presentation.notificaciones_views.marcar_notificaciones_leidas', 'editar_solicitud_cambio_reserva': 'apps.reservas.presentation.cambios_views.editar_solicitud_cambio_reserva', 'gestion_solicitud_cambio_reserva_accion': 'apps.reservas.presentation.cambios_views.gestion_solicitud_cambio_reserva_accion', 'retirar_solicitud_cambio_reserva': 'apps.reservas.presentation.cambios_views.retirar_solicitud_cambio_reserva', 'solicitar_cambio_reserva': 'apps.reservas.presentation.cambios_views.solicitar_cambio_reserva'}


def __getattr__(nombre):
    ruta = _ENTRADAS.get(nombre)
    if ruta is None:
        raise AttributeError(nombre)
    modulo, atributo = ruta.rsplit('.', 1)
    return getattr(import_module(modulo), atributo)


__all__ = tuple(_ENTRADAS)
