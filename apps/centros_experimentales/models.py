"""Registro de centros experimentales sin tabla propia.

Las unidades siguen viviendo en una sola tabla heredada mientras dura la
compatibilidad. Este modelo delegado le da a la vertical su propia seccion en
la administracion y sus propios permisos, sin mover datos ni duplicarlos.
"""

from apps.integraciones.unidades import modelo_unidad, modelos_de_funciones


class CentroExperimental(modelo_unidad()):
    class Meta:
        proxy = True
        app_label = 'centros_experimentales'
        verbose_name = 'Centro experimental'
        verbose_name_plural = 'Centros experimentales'


# Un centro experimental agenda, presta equipos y consume insumos; no
# ofrece servicios de fabricacion. Produce en el campo, por ejes productivos,
# no por las ordenes y lotes de una planta.
# Cada funcion es una seccion propia sobre la tabla heredada: mismos nombres
# que en los otros tipos, solo los datos de este.
FUNCIONES = (
    'reservas',
    'actividades',
    'agropecuaria',
    'equipos',
    'areas',
    'mantenimiento',
    'inventario',
    'seguridad',
    'expediente',
    'trazabilidad',
)
MODELOS_DE_FUNCION = modelos_de_funciones('centros_experimentales', FUNCIONES, globals())
