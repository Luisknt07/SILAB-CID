"""Politica institucional de periodos, independiente de Django y de verticales."""

from dataclasses import dataclass
import re

from .catalogos import _filas
from .identidad import validar_texto


TIPOS_PERIODO = (("ordinario", "Período académico ordinario"),
                 ("extraordinario", "Período académico extraordinario"),
                 ("interperiodo", "Interperíodo institucional"))


@dataclass(frozen=True, slots=True)
class PoliticaCalendario:
    ciclos: tuple
    ciclos_historicos: tuple
    ambitos: tuple
    ambitos_historicos: tuple
    ambitos_operacion: tuple
    ambito_predeterminado: str
    semanas_minimas: int
    semanas_maximas: int
    semanas_predeterminadas: int

    def tipo_para_ciclo(self, codigo):
        return next((tipo for ciclo, _, tipo in self.ciclos + self.ciclos_historicos if ciclo == codigo), "")


def _ciclos(filas):
    if not isinstance(filas, (list, tuple)) or len(filas) > 36:
        raise ValueError("Los ciclos del calendario no son validos.")
    resultado = []
    usados = set()
    for fila in filas:
        if not isinstance(fila, (list, tuple)) or len(fila) != 3:
            raise ValueError("Cada ciclo requiere codigo, etiqueta y tipo.")
        codigo, etiqueta, tipo = fila
        if (not isinstance(codigo, str) or not re.fullmatch(r"[A-Z0-9]", codigo)
                or codigo in usados or not isinstance(tipo, str) or tipo not in dict(TIPOS_PERIODO)):
            raise ValueError("Los ciclos requieren codigos unicos de un caracter y tipos conocidos.")
        validar_texto(etiqueta, obligatorio=True)
        usados.add(codigo)
        resultado.append(tuple(fila))
    return tuple(resultado)


def politica_calendario(datos):
    claves = {"ciclos", "ciclos_historicos", "ambitos", "ambitos_historicos", "ambitos_operacion",
              "ambito_predeterminado", "semanas_minimas", "semanas_maximas", "semanas_predeterminadas"}
    if not isinstance(datos, dict) or set(datos) - claves:
        raise ValueError("La estructura de politica de calendario no es valida.")
    ciclos = _ciclos(datos.get("ciclos", ()))
    historicos = _ciclos(datos.get("ciclos_historicos", ()))
    ambitos = _filas(datos.get("ambitos", ()), 2, 200)
    anteriores = _filas(datos.get("ambitos_historicos", ()), 2, 200)
    activos = dict(ambitos)
    if (not ciclos or not ambitos or {c for c, _, _ in ciclos} & {c for c, _, _ in historicos}
            or set(activos) & set(dict(anteriores)) or any(len(c) > 30 for c, _ in ambitos + anteriores)):
        raise ValueError("Los ciclos y ambitos activos e historicos deben ser distintos y compatibles.")
    operacion = datos.get("ambitos_operacion", ())
    predeterminado = datos.get("ambito_predeterminado")
    if (not isinstance(operacion, (list, tuple))
            or any(not isinstance(c, str) or c not in activos for c in operacion)
            or len(set(operacion)) != len(operacion)
            or not isinstance(predeterminado, str) or predeterminado not in activos):
        raise ValueError("El ambito predeterminado y los de operacion deben estar activos.")
    minimo, maximo, defecto = (datos.get("semanas_minimas", 1), datos.get("semanas_maximas", 24),
                               datos.get("semanas_predeterminadas", 16))
    if any(type(v) is not int for v in (minimo, maximo, defecto)) or not 1 <= minimo <= defecto <= maximo <= 24:
        raise ValueError("Las semanas requieren enteros dentro del limite compatible de 1 a 24.")
    return PoliticaCalendario(ciclos, historicos, ambitos, anteriores, tuple(operacion),
                             predeterminado, minimo, maximo, defecto)


def datos_calendario(politica):
    """Contrato JSON explicito; excluye metadatos y atributos ajenos."""
    return {
        'ciclos': [list(f) for f in politica.ciclos],
        'ciclos_historicos': [list(f) for f in politica.ciclos_historicos],
        'ambitos': [list(f) for f in politica.ambitos],
        'ambitos_historicos': [list(f) for f in politica.ambitos_historicos],
        'ambitos_operacion': list(politica.ambitos_operacion),
        'ambito_predeterminado': politica.ambito_predeterminado,
        'semanas_minimas': politica.semanas_minimas,
        'semanas_maximas': politica.semanas_maximas,
        'semanas_predeterminadas': politica.semanas_predeterminadas,
    }


def validar_transicion_calendario(anterior, propuesto):
    """Conservar codigos y significado, incluso antes de su primer uso."""
    ciclos = {c: t for c, _, t in anterior.ciclos + anterior.ciclos_historicos}
    nuevos = {c: t for c, _, t in propuesto.ciclos + propuesto.ciclos_historicos}
    ambitos = {c for c, _ in anterior.ambitos + anterior.ambitos_historicos}
    destinos = {c for c, _ in propuesto.ambitos + propuesto.ambitos_historicos}
    if not ambitos <= destinos or any(nuevos.get(c) != t for c, t in ciclos.items()):
        raise ValueError('Conserva los codigos anteriores y el tipo de cada ciclo; retira como historico.')
