"""Modelos propios; tablas existentes conservadas por migración de estado."""
from apps.directorio_unidades.models.core import Categoria  # noqa: F401
from apps.directorio_unidades.models.core import TipoLaboratorio  # noqa: F401
from apps.directorio_unidades.models.core import DependenciaAcademica  # noqa: F401
from apps.directorio_unidades.models.core import Unidad  # noqa: F401
from apps.directorio_unidades.models.relaciones import RelacionUnidad  # noqa: F401
from apps.directorio_unidades.models.sedes import SedeInstitucional  # noqa: F401
