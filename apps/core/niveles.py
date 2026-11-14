"""Niveles y rutas de avance institucionales, sin dependencias de Django."""

from dataclasses import dataclass

from .catalogos import _filas
from .identidad import validar_texto


@dataclass(frozen=True, slots=True)
class NivelesAcademicos:
    niveles: tuple
    historicos: tuple
    estudiantes: tuple
    secuencias: tuple
    etiqueta_faltante: str

    def siguiente(self, codigo):
        for secuencia in self.secuencias:
            if codigo in secuencia:
                posicion = secuencia.index(codigo)
                return secuencia[min(posicion + 1, len(secuencia) - 1)]
        return codigo


def niveles_academicos(datos):
    permitidas = {"niveles", "historicos", "estudiantes", "secuencias", "etiqueta_faltante"}
    if not isinstance(datos, dict) or set(datos) - permitidas:
        raise ValueError("La estructura de niveles academicos no es valida.")
    niveles = _filas(datos.get("niveles", ()), 2, 200)
    historicos = _filas(datos.get("historicos", ()), 2, 200)
    activos = set(dict(niveles))
    if activos & set(dict(historicos)) or any(len(codigo) > 30 for codigo, _ in niveles + historicos):
        raise ValueError("Los codigos de niveles deben ser unicos y tener hasta 30 caracteres.")
    estudiantes = datos.get("estudiantes", ())
    if (not isinstance(estudiantes, (list, tuple))
            or any(not isinstance(codigo, str) or codigo not in activos for codigo in estudiantes)
            or len(set(estudiantes)) != len(estudiantes)):
        raise ValueError("Los niveles de estudiantes deben estar activos y no repetirse.")
    secuencias = datos.get("secuencias", ())
    if not isinstance(secuencias, (list, tuple)) or len(secuencias) > 200:
        raise ValueError("Las rutas de avance no son validas.")
    usados = set()
    for ruta in secuencias:
        if (not isinstance(ruta, (list, tuple)) or not 2 <= len(ruta) <= 200
                or any(not isinstance(codigo, str) or codigo not in estudiantes for codigo in ruta)
                or len(set(ruta)) != len(ruta) or usados.intersection(ruta)):
            raise ValueError("Las rutas requieren niveles estudiantiles unicos, sin ciclos ni bifurcaciones.")
        usados.update(ruta)
    etiqueta = datos.get("etiqueta_faltante", "nivel académico")
    validar_texto(etiqueta, obligatorio=True)
    return NivelesAcademicos(niveles, historicos, tuple(estudiantes),
                            tuple(tuple(ruta) for ruta in secuencias), etiqueta)


def datos_niveles(niveles):
    """Representacion explicita para publicaciones y formularios."""
    return {'niveles': [list(f) for f in niveles.niveles],
            'historicos': [list(f) for f in niveles.historicos],
            'estudiantes': list(niveles.estudiantes),
            'secuencias': [list(r) for r in niveles.secuencias],
            'etiqueta_faltante': niveles.etiqueta_faltante}


def validar_transicion_niveles(anterior, nuevo):
    anteriores = set(dict(anterior.niveles + anterior.historicos))
    nuevos = set(dict(nuevo.niveles + nuevo.historicos))
    if not anteriores <= nuevos:
        raise ValueError('Conserva los codigos anteriores; retira niveles como historicos.')
