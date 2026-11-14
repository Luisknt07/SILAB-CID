"""MCP opcional del curso. No contiene herramientas para escribir ni ejecutar código."""

from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_consultas import leer_existencias

mcp = MCPServer("Andina Distribución · consulta docente")


@mcp.tool()
def consultar_existencias(codigo: str = "") -> dict[str, Any]:
    """Consulta hasta 100 productos ficticios; código vacío lista todos. No cambia inventario."""
    try:
        return leer_existencias(codigo=codigo)
    except ValueError as error:
        raise ToolError(str(error)) from None


@mcp.tool()
def productos_bajo_minimo() -> dict[str, Any]:
    """Lista productos ficticios cuya existencia es menor que el mínimo. No crea compras."""
    try:
        return leer_existencias(solo_bajos=True)
    except ValueError as error:
        raise ToolError(str(error)) from None


if __name__ == "__main__":
    mcp.run(transport="stdio")
