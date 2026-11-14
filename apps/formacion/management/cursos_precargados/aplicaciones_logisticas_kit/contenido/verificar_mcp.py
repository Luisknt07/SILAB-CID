"""Prueba de protocolo sin modelo de IA, suscripción ni API. Requiere requirements-mcp."""

import asyncio
import hashlib
from pathlib import Path
import sys
from mcp import Client, StdioServerParameters

BASE = Path(__file__).resolve().parent


async def verificar():
    ruta = BASE / "db.sqlite3"
    if not ruta.is_file():
        raise SystemExit(
            "Ejecute primero python manage.py migrate y python manage.py preparar_demo."
        )
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    servidor = StdioServerParameters(
        command=sys.executable, args=["-X", "utf8", str(BASE / "servidor_mcp.py")]
    )
    async with Client(servidor) as cliente:
        listado = await cliente.list_tools()
        nombres = {tool.name for tool in listado.tools}
        assert nombres == {"consultar_existencias", "productos_bajo_minimo"}, nombres
        resultado = await cliente.call_tool(
            "consultar_existencias", {"codigo": "AD-001"}
        )
        assert not resultado.is_error, resultado
        assert resultado.structured_content["solo_lectura"] is True
        productos = resultado.structured_content["productos"]
        assert len(productos) == 1 and productos[0]["codigo"] == "AD-001", productos
        bajos = await cliente.call_tool("productos_bajo_minimo", {})
        assert not bajos.is_error, bajos
        for producto in bajos.structured_content["productos"]:
            from decimal import Decimal

            assert Decimal(producto["existencia"]) < Decimal(producto["minimo"])
        invalido = await cliente.call_tool(
            "consultar_existencias", {"codigo": "' OR 1=1 --"}
        )
        assert invalido.is_error, "El código inválido debe rechazarse."
    despues = hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert antes == despues, "La consulta no debe modificar la base de datos."
    print(
        "MCP verificado: dos herramientas de consulta, entrada inválida rechazada y base sin cambios."
    )


if __name__ == "__main__":
    asyncio.run(verificar())
