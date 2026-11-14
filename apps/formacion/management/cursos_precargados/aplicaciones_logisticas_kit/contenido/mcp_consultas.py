"""Lectura acotada: SQLite abre la base en modo ro y sólo admite consultas fijas."""

from decimal import Decimal
from pathlib import Path
import re
import sqlite3

BASE_DATOS = Path(__file__).resolve().parent / "db.sqlite3"


def leer_existencias(*, codigo="", solo_bajos=False, ruta=None):
    codigo = codigo.strip().upper()
    if codigo and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,23}", codigo):
        raise ValueError("Use un código de producto válido, por ejemplo AD-001.")
    path = Path(ruta or BASE_DATOS).resolve()
    if not path.is_file():
        raise ValueError(
            "Primero ejecute migrate y preparar_demo en la carpeta del proyecto."
        )
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        where, parametros = [], []
        if codigo:
            where.append("codigo = ?")
            parametros.append(codigo)
        if solo_bajos:
            where.append("existencia < minimo")
        consulta = (
            "SELECT codigo,nombre,unidad,existencia,minimo FROM inventario_producto"
        )
        if where:
            consulta += " WHERE " + " AND ".join(where)
        consulta += " ORDER BY codigo LIMIT 100"
        filas = connection.execute(consulta, parametros).fetchall()
    except sqlite3.OperationalError as error:
        raise ValueError(
            "La base docente no está preparada o no es accesible. Revise migrate y preparar_demo."
        ) from error
    finally:
        connection.close()
    productos = [
        {
            "codigo": f["codigo"],
            "nombre": f["nombre"],
            "unidad": f["unidad"],
            "existencia": format(Decimal(str(f["existencia"])), ".2f"),
            "minimo": format(Decimal(str(f["minimo"])), ".2f"),
        }
        for f in filas
    ]
    return {
        "origen": "Andina Distribución · datos ficticios locales",
        "solo_lectura": True,
        "limite": 100,
        "productos": productos,
    }
