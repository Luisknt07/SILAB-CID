"""Cursos que el sistema puede precargar en una unidad, con su contenido completo."""


def load_tests(loader, suite, pattern):
    """El código de los proyectos docentes se prueba en su propio entorno.

    Estos paquetes son fuentes de los ZIP del curso, no apps instaladas del
    portal. Sus modelos no deben importarse al descubrir la regresión global.
    La construcción e integridad de los ZIP se comprueba en tests/integration.
    """
    return suite
