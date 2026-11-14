"""Modelos propios; tablas existentes conservadas por migración de estado."""
from apps.laboratorios.operacion.models.fablab import FablabService  # noqa: F401
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion  # noqa: F401
from apps.laboratorios.operacion.models.fablab import SolicitudConsumible  # noqa: F401
from apps.laboratorios.operacion.models.fablab import FablabServiceConsumible  # noqa: F401
from apps.laboratorios.operacion.models.perfil import PerfilLaboratorio  # noqa: F401
from apps.laboratorios.operacion.models.perfil import PerfilPlataformaTecnologica  # noqa: F401
