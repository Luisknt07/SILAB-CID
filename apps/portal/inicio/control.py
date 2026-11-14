"""La suspension de edicion no revoca lectura administrativa del historial."""
from apps.core.presentation.capacidades import control_actual


def inicio_activo():
    # Visibilidad publica de contenido editorial: no requiere permiso de usuario.
    return control_actual('portal', 'portada_inicio').autoriza(True)
