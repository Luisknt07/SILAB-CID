"""Registro de laboratorios sin tabla propia.

Las unidades siguen viviendo en una sola tabla heredada mientras dura la
compatibilidad. Este modelo delegado le da a la vertical su propia seccion en
la administracion y sus propios permisos, sin mover datos ni duplicarlos.
"""

from apps.integraciones.unidades import modelo_unidad, modelos_de_funciones


class Laboratorio(modelo_unidad()):
    class Meta:
        proxy = True
        app_label = 'laboratorios'
        verbose_name = 'Laboratorio'
        verbose_name_plural = 'Laboratorios'


# Un laboratorio agenda, dicta cursos, presta equipos, consume insumos, sigue sus procesos y ofrece servicios.
# Cada funcion es una seccion propia sobre la tabla heredada: mismos nombres
# que en los otros tipos, solo los datos de este.
FUNCIONES = (
    'reservas',
    'actividades',
    'cursos',
    'equipos',
    'areas',
    'mantenimiento',
    'inventario',
    'seguridad',
    'expediente',
    'procesos',
    'servicios',
    'trazabilidad',
)
MODELOS_DE_FUNCION = modelos_de_funciones('laboratorios', FUNCIONES, globals())
