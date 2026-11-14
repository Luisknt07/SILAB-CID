"""Contrato de identidad v1: valores inmutables, sin Django ni objetos ORM."""

from dataclasses import dataclass
from enum import Enum


class TipoUnidad(str, Enum):
    LABORATORIO = "laboratorios"
    PLANTA_PILOTO = "plantas_piloto"
    CENTRO_EXPERIMENTAL = "centro_experimental"
    OBSERVATORIO = "observatorios"

    @property
    def contexto(self):
        if self is TipoUnidad.CENTRO_EXPERIMENTAL:
            return "centros_experimentales"
        return self.value

    @property
    def titulo(self):
        return {
            self.LABORATORIO: "Laboratorios",
            self.PLANTA_PILOTO: "Plantas Piloto",
            self.CENTRO_EXPERIMENTAL: "Centros Experimentales",
            self.OBSERVATORIO: "Observatorios",
        }[self]

    @property
    def ruta_catalogo(self):
        """Nombre de la ruta publica historica del catalogo de cada implementacion.

        Laboratorios conserva el alias `hublab`, que es el enlace publicado en
        las pestanas y recorridos aceptados.
        """
        return {
            self.LABORATORIO: "hublab",
            self.PLANTA_PILOTO: "plantas-piloto",
            self.CENTRO_EXPERIMENTAL: "centros-experimentales",
            self.OBSERVATORIO: "observatorios",
        }[self]


# La puerta publica del directorio (menu, portada, perfil y el «volver» de cada
# ficha) es la ruta historica de Laboratorios. Desactivar ese tipo cierra su
# catalogo, no la puerta: esta sigue abriendo con el primer tipo activo.
ENTRADA_DIRECTORIO = TipoUnidad.LABORATORIO


@dataclass(frozen=True, slots=True)
class IdentidadUnidad:
    """Proyeccion publica: excluye responsables privados, permisos y reservas."""

    unidad_id: int
    nombre: str
    slug: str
    tipo: TipoUnidad
    contacto_email: str
    version_contrato: int = 1
