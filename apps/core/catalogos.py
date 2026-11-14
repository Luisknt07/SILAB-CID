"""Catalogo academico inmutable: datos y politica, sin Django ni verticales."""

from dataclasses import dataclass
import re

from .identidad import validar_texto


# Codigos estables de clasificacion; no son grupos ni permisos de acceso.
TIPOS_USUARIO = (
    ("estudiante", "Estudiante"), ("docente", "Docente"),
    ("investigador", "Investigador"), ("administrativo", "Personal administrativo"),
    ("egresado", "Egresado"), ("externo", "Usuario externo"),
)


@dataclass(frozen=True, slots=True)
class CatalogoAcademico:
    facultades: tuple
    carreras: tuple
    carreras_historicas: tuple
    tipos_con_carrera: tuple

    def facultad_para_carrera(self, codigo):
        return next((facultad for carrera, _, facultad in self.carreras if carrera == codigo), "")


def _filas(valor, columnas, limite):
    if not isinstance(valor, (list, tuple)) or len(valor) > limite:
        raise ValueError("El catalogo requiere listas con limites definidos.")
    filas = []
    codigos = set()
    for fila in valor:
        if not isinstance(fila, (list, tuple)) or len(fila) != columnas:
            raise ValueError("La estructura del catalogo no es valida.")
        codigo, etiqueta = fila[:2]
        if not isinstance(codigo, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", codigo):
            raise ValueError("El codigo academico no es valido.")
        validar_texto(etiqueta, obligatorio=True)
        if codigo in codigos:
            raise ValueError("El catalogo contiene codigos duplicados.")
        codigos.add(codigo)
        filas.append(tuple(fila))
    return tuple(filas)


def catalogo_academico(datos):
    """Rechaza estructura desconocida y relaciones inexistentes, sin exponer datos."""
    permitidas = {"facultades", "carreras", "carreras_historicas", "tipos_con_carrera"}
    if not isinstance(datos, dict) or set(datos) - permitidas:
        raise ValueError("La estructura del catalogo no es valida.")
    facultades = _filas(datos.get("facultades", ()), 2, 201)
    if sum(codigo != 'externo' for codigo, _ in facultades) > 200:
        raise ValueError("El catalogo supera el limite de dependencias internas.")
    if "externo" not in dict(facultades):
        facultades += (("externo", "Externo a la institución"),)
    carreras = _filas(datos.get("carreras", ()), 3, 2000)
    historicas = _filas(datos.get("carreras_historicas", ()), 2, 2000)
    internos = set(dict(facultades)) - {"externo"}
    if any(not isinstance(facultad, str) or facultad not in internos for _, _, facultad in carreras):
        raise ValueError("Cada carrera debe pertenecer a una dependencia interna existente.")
    if {codigo for codigo, _, _ in carreras} & set(dict(historicas)):
        raise ValueError("Un codigo no puede ser academico e historico a la vez.")
    tipos = datos.get("tipos_con_carrera", ())
    internos = {codigo for codigo, _ in TIPOS_USUARIO} - {"externo"}
    if (not isinstance(tipos, (list, tuple)) or any(not isinstance(tipo, str) or tipo not in internos for tipo in tipos)
            or len(set(tipos)) != len(tipos) or (tipos and not carreras)):
        raise ValueError("La politica de carrera obligatoria no es valida.")
    return CatalogoAcademico(facultades, carreras, historicas, tuple(tipos))


def datos_catalogo(catalogo):
    """Serializacion explicita de campos publicos; nunca serializa un modelo."""
    return {'facultades': [list(fila) for fila in catalogo.facultades],
            'carreras': [list(fila) for fila in catalogo.carreras],
            'carreras_historicas': [list(fila) for fila in catalogo.carreras_historicas],
            'tipos_con_carrera': list(catalogo.tipos_con_carrera)}


def relaciones_para_publicar(anterior, nuevo, reservadas):
    """Conserva codigos y significado, incluso para solicitudes aun en curso."""
    if not set(dict(anterior.facultades)) <= set(dict(nuevo.facultades)):
        raise ValueError('No retires códigos de dependencias existentes; conserva sus referencias.')
    previos = {c for c, _, _ in anterior.carreras} | set(dict(anterior.carreras_historicas))
    actuales = {c for c, _, _ in nuevo.carreras} | set(dict(nuevo.carreras_historicas))
    if not previos <= actuales:
        raise ValueError('Conserva los códigos anteriores; las carreras retiradas deben pasar a históricas.')
    relaciones = dict(reservadas)
    relaciones.update({c: f for c, _, f in anterior.carreras})
    historicos = set(dict(anterior.carreras_historicas))
    for codigo, _, facultad in nuevo.carreras:
        if codigo in historicos and codigo not in relaciones:
            raise ValueError('Una clasificación histórica no académica no puede reutilizarse como carrera.')
        if codigo in relaciones and relaciones[codigo] != facultad:
            raise ValueError('No reasignes una carrera existente a otra dependencia; utiliza un código nuevo.')
        relaciones[codigo] = facultad
    return relaciones
