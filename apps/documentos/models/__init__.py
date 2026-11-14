"""Modelos propios; tablas existentes conservadas por migración de estado."""
from apps.documentos.models.expediente import DocumentoExigido  # noqa: F401
from apps.documentos.models.expediente import PoliticaDeCalidad  # noqa: F401
from apps.documentos.models.expediente import DocumentoExpediente  # noqa: F401
from apps.documentos.models.expediente import DocumentoElaborado  # noqa: F401
from apps.documentos.models.mejora import InformeMejora  # noqa: F401
from apps.documentos.models.mejora import AccionMejora  # noqa: F401
from apps.documentos.models.mejora import SeguimientoMejora  # noqa: F401
from apps.documentos.models.avisos_documentales import AvisoDocumental  # noqa: F401
from apps.documentos.models.avisos_documentales import UltimatumDocumental  # noqa: F401
from apps.documentos.models.medicion import EvidenciaGestionUnidad  # noqa: F401
from apps.documentos.models.control_automatico import ControlAutomaticoDocumento  # noqa: F401
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad  # noqa: F401
from apps.documentos.models.constancias import ConstanciaDocumento  # noqa: F401
from apps.documentos.models.constancias import PresentacionDocumento  # noqa: F401
from apps.documentos.models.necesidades import RemisionNecesidades  # noqa: F401
from apps.documentos.models.asignacion import MarcoPresupuestoNecesidades, EscenarioAsignacionNecesidades  # noqa: F401
