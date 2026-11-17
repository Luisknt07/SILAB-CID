"""Modelos propios; tablas existentes conservadas por migración de estado."""
from apps.core.models.limites import ContadorPeticion  # noqa: F401
from apps.core.models.segundo_factor import SegundoFactor  # noqa: F401
from apps.core.models.usuarios_base import UserProfile  # noqa: F401
from apps.core.models.usuarios import Decanato  # noqa: F401
from apps.core.models.verificaciones import VerificacionInstitucional  # noqa: F401
from apps.core.models.periodos import PeriodoAcademico  # noqa: F401
from apps.core.models.periodos import VersionCalendarioAcademico  # noqa: F401
from apps.core.models.periodos import SemanaAcademica  # noqa: F401
from apps.core.models.periodos import VinculacionUsuarioPeriodo  # noqa: F401

from apps.core.models.gobernanza import AsignacionGobernanza  # noqa: F401
