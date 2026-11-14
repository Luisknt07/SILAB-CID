"""Registro de plantas piloto sin tabla propia.

Las unidades siguen viviendo en una sola tabla heredada mientras dura la
compatibilidad. Este modelo delegado le da a la vertical su propia seccion en
la administracion y sus propios permisos, sin mover datos ni duplicarlos.
"""

from apps.integraciones.unidades import modelo_unidad, modelos_de_funciones


class PlantaPiloto(modelo_unidad()):
    class Meta:
        proxy = True
        app_label = 'plantas_piloto'
        verbose_name = 'Planta piloto'
        verbose_name_plural = 'Plantas piloto'


# Una planta hace todo lo de un laboratorio y ademas produce: es la unica
# con familias, fichas, recetas, ordenes y lotes.
# Cada funcion es una seccion propia sobre la tabla heredada: mismos nombres
# que en los otros tipos, solo los datos de este.
FUNCIONES = (
    'reservas',
    'actividades',
    'equipos',
    'areas',
    'mantenimiento',
    'inventario',
    'seguridad',
    'expediente',
    'produccion',
    'servicios',
    'trazabilidad',
)
MODELOS_DE_FUNCION = modelos_de_funciones('plantas_piloto', FUNCIONES, globals())
