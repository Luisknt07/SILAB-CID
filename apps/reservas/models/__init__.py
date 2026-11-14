"""Modelos propios; tablas existentes conservadas por migración de estado."""
from apps.reservas.models.reservas import EjemploSolicitudUnidad  # noqa: F401
from apps.reservas.models.reservas import CatalogoActividadReserva  # noqa: F401
from apps.reservas.models.reservas import GuiaActividadReserva  # noqa: F401
from apps.reservas.models.reservas import ProgramacionReserva  # noqa: F401
from apps.reservas.models.reservas import Reserva  # noqa: F401
from apps.reservas.models.reservas import NotificacionReserva  # noqa: F401
from apps.reservas.models.reservas import RegistroParticipanteReserva  # noqa: F401
from apps.reservas.models.reservas import ReservaConsumible  # noqa: F401
from apps.reservas.models.reservas import RevisionReserva  # noqa: F401
from apps.reservas.models.reservas import SolicitudCambioReserva  # noqa: F401
from apps.reservas.models.reservas import ReservaAdjunto  # noqa: F401
from apps.reservas.models.reservas import ImagenGuiaActividad  # noqa: F401
from apps.reservas.models.seguridad import RequisitoAcceso  # noqa: F401
from apps.reservas.models.seguridad import HabilitacionAcceso  # noqa: F401
from apps.reservas.models.seguridad import RegistroIngreso  # noqa: F401
from apps.reservas.models.visitas import SolicitudVisita  # noqa: F401
from apps.reservas.models.visitas import AsistenteVisita  # noqa: F401
