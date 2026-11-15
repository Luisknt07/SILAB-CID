"""Composición de aplicaciones propietarias; solo metadatos, sin vistas."""

from apps.core.modulos import RegistroModulos
from apps.core.manifiesto import MANIFIESTO as M0
from apps.directorio_unidades.manifiesto import MANIFIESTO as M1
from apps.gestion_unidades.manifiesto import MANIFIESTO as M2
from apps.recursos.manifiesto import MANIFIESTO as M3
from apps.reservas.manifiesto import MANIFIESTO as M4
from apps.formacion.manifiesto import MANIFIESTO as M5
from apps.documentos.manifiesto import MANIFIESTO as M6
from apps.finanzas.manifiesto import MANIFIESTO as M7
from apps.laboratorios.operacion.manifiesto import MANIFIESTO as M8
from apps.plantas_piloto.operacion.manifiesto import MANIFIESTO as M9
from apps.centros_experimentales.operacion.manifiesto import MANIFIESTO as M10
from apps.observatorios.operacion.manifiesto import MANIFIESTO as M11
from apps.configuracion_institucional.manifiesto import MANIFIESTO as M12
from apps.portal.manifiesto import MANIFIESTO as M13
from apps.integraciones.manifiesto import MANIFIESTO as M14
from apps.centros_id.manifiesto import MANIFIESTO as M15
from apps.laboratorios.manifiesto import MANIFIESTO as M16
from apps.plantas_piloto.manifiesto import MANIFIESTO as M17
from apps.centros_experimentales.manifiesto import MANIFIESTO as M18
from apps.observatorios.manifiesto import MANIFIESTO as M19
from apps.historial_modelos.manifiesto import MANIFIESTO as M20


def manifiestos_opcionales():
    """Módulos que cada instalación decide en su entorno; ausentes, el registro no los nombra."""
    # El registro se carga sin Django: la decisión se lee del entorno, como en la configuración.
    from config.opcionales import conexiones_activo

    if conexiones_activo():
        from apps.conexiones.manifiesto import MANIFIESTO

        yield MANIFIESTO


def registro_de_despliegue():
    return RegistroModulos(
        (
            M0,
            M1,
            M2,
            M3,
            M4,
            M5,
            M6,
            M7,
            M8,
            M9,
            M10,
            M11,
            M12,
            M13,
            M14,
            M15,
            M16,
            M17,
            M18,
            M19,
            M20,
            *manifiestos_opcionales(),
        )
    )
