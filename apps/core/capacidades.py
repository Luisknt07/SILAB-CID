"""Control de capacidad v1, sin ORM ni configuracion de institucion concreta."""
from dataclasses import dataclass

from .modulos import IDENTIFICADOR


@dataclass(frozen=True, slots=True)
class ControlCapacidad:
    modulo: str
    capacidad: str
    disponible: bool = True
    habilitada: bool = True
    derecho: bool = True

    def __post_init__(self):
        if (any(not isinstance(i, str) or not IDENTIFICADOR.fullmatch(i)
                for i in (self.modulo, self.capacidad))
                or any(type(v) is not bool for v in (self.disponible, self.habilitada, self.derecho))):
            raise ValueError('El control requiere identificadores y booleanos validos.')

    def autoriza(self, permiso):
        """El permiso debe venir de la autoridad local, nunca del formulario."""
        return permiso is True and self.disponible and self.habilitada and self.derecho
