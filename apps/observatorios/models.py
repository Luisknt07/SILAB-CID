"""Registro de observatorios sin tabla propia.

Las unidades siguen viviendo en una sola tabla heredada mientras dura la
compatibilidad. Este modelo delegado le da a la vertical su propia seccion en
la administracion y sus propios permisos, sin mover datos ni duplicarlos.
"""

from apps.integraciones.unidades import modelo_unidad, modelos_de_funciones


class Observatorio(modelo_unidad()):
    class Meta:
        proxy = True
        app_label = 'observatorios'
        verbose_name = 'Observatorio'
        verbose_name_plural = 'Observatorios'


# Un observatorio produce informacion para decidir: indicadores, series,
# publicaciones y alertas (observacion). Conserva la agenda, los equipos de
# monitoreo y los insumos; no ofrece servicios de fabricacion ni produce.
# Cada funcion es una seccion propia sobre la tabla heredada: mismos nombres
# que en los otros tipos, solo los datos de este.
FUNCIONES = (
    'observacion',
    'reservas',
    'actividades',
    'equipos',
    'mantenimiento',
    'inventario',
    'seguridad',
    'expediente',
    'trazabilidad',
)
MODELOS_DE_FUNCION = modelos_de_funciones('observatorios', FUNCIONES, globals())
