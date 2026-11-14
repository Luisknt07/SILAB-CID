"""Contratos de despliegue v1; no importan Django, verticales ni modelos.

El registro describe codigo y dependencias. No concede acceso, habilita
operaciones ni modifica INSTALLED_APPS o datos institucionales.
"""

from dataclasses import dataclass
import re
from types import MappingProxyType


IDENTIFICADOR = re.compile(r'[a-z][a-z0-9_]*\Z')
RUTA_PYTHON = re.compile(r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*\Z')
VERSION = re.compile(r'(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\Z')


@dataclass(frozen=True, slots=True)
class ManifiestoModulo:
    """Version del manifiesto independiente de la version de sus contratos."""

    identificador: str
    version: str
    paquete: str
    etapa: str
    dependencias: tuple[str, ...] = ()
    integraciones_opcionales: tuple[str, ...] = ()
    app_django: str = ''
    rutas: tuple[str, ...] = ()
    administracion: tuple[str, ...] = ()
    migraciones: tuple[str, ...] = ()
    comandos: tuple[str, ...] = ()
    tareas: tuple[str, ...] = ()
    salud: tuple[str, ...] = ()
    capacidades: tuple[str, ...] = ()
    contratos: tuple[str, ...] = ()
    version_esquema: int = 1

    def __post_init__(self):
        if (type(self.version_esquema) is not int or self.version_esquema != 1
                or not isinstance(self.identificador, str) or not IDENTIFICADOR.fullmatch(self.identificador)
                or not isinstance(self.version, str) or not VERSION.fullmatch(self.version)
                or not isinstance(self.paquete, str) or not RUTA_PYTHON.fullmatch(self.paquete)
                or self.etapa not in ('nucleo', 'propio', 'heredado', 'presentacion')):
            raise ValueError('El manifiesto requiere identificador, version, paquete y etapa validos.')
        for campo in ('dependencias', 'integraciones_opcionales', 'capacidades', 'contratos'):
            valores = getattr(self, campo)
            if (type(valores) is not tuple or any(not isinstance(v, str) or not IDENTIFICADOR.fullmatch(v)
                                                 for v in valores) or len(set(valores)) != len(valores)):
                raise ValueError('Las referencias del manifiesto deben ser tuplas de identificadores unicos.')
        if (self.identificador in self.dependencias + self.integraciones_opcionales
                or set(self.dependencias) & set(self.integraciones_opcionales)):
            raise ValueError('Una dependencia no puede ser propia ni obligatoria y opcional a la vez.')
        if (not isinstance(self.app_django, str)
                or self.app_django and self.app_django != self.paquete):
            raise ValueError('La app Django debe corresponder al paquete propietario.')
        for campo in ('rutas', 'administracion', 'migraciones', 'comandos', 'tareas', 'salud'):
            valores = getattr(self, campo)
            if (type(valores) is not tuple or any(not isinstance(v, str) or not RUTA_PYTHON.fullmatch(v)
                                                 or not v.startswith(self.paquete + '.') for v in valores)
                    or len(set(valores)) != len(valores)):
                raise ValueError('Los puntos de entrada deben pertenecer al paquete propietario.')
        if self.migraciones and not self.app_django:
            raise ValueError('Un paquete con migraciones requiere una app Django declarada.')


class RegistroModulos:
    """Catalogo inmutable y orden topologico de dependencias obligatorias.

Las integraciones opcionales ausentes no agregan dependencias al plan.
Planificar no equivale a instalar o autorizar una seleccion de modulos.
"""

    def __init__(self, manifiestos):
        entradas = {}
        for manifiesto in manifiestos:
            if not isinstance(manifiesto, ManifiestoModulo):
                raise ValueError('El registro solo admite manifiestos validados.')
            if manifiesto.identificador in entradas:
                raise ValueError('El registro contiene un identificador duplicado.')
            entradas[manifiesto.identificador] = manifiesto
        if not entradas:
            raise ValueError('El registro no puede estar vacio.')
        paquetes = [m.paquete for m in entradas.values()]
        if len(set(paquetes)) != len(paquetes):
            raise ValueError('Cada paquete debe tener un unico propietario.')
        if any(d not in entradas for m in entradas.values() for d in m.dependencias):
            raise ValueError('Falta una dependencia obligatoria en el registro.')
        self._entradas = MappingProxyType(entradas)
        self.plan(tuple(entradas))  # Comprueba ciclos antes de exponer el registro.

    @property
    def manifiestos(self):
        return self._entradas

    def plan(self, seleccion):
        if (not isinstance(seleccion, (tuple, list)) or not seleccion
                or any(not isinstance(i, str) or i not in self._entradas for i in seleccion)):
            raise ValueError('La seleccion requiere identificadores registrados.')
        pendientes, resueltos, orden = set(), set(), []

        def visitar(identificador):
            if identificador in pendientes:
                raise ValueError('Existe un ciclo de dependencias obligatorias.')
            if identificador in resueltos:
                return
            pendientes.add(identificador)
            for dependencia in sorted(self._entradas[identificador].dependencias):
                visitar(dependencia)
            pendientes.remove(identificador)
            resueltos.add(identificador)
            orden.append(identificador)

        for identificador in sorted(set(seleccion)):
            visitar(identificador)
        return tuple(orden)

    def validar_apps(self, instaladas):
        """Recibe nombres de apps resueltas, no paths de clases AppConfig."""
        if any(m.app_django and m.app_django not in instaladas for m in self._entradas.values()):
            raise ValueError('Falta una app Django requerida por el registro de despliegue.')
