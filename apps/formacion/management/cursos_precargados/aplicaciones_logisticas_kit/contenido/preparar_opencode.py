"""Genera configuración local con rutas reales; no añade ni solicita claves de modelos."""

import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
DESTINO = BASE / "opencode.json"
if importlib.util.find_spec("mcp") is None:
    raise SystemExit(
        "Instale primero python -m pip install -r requirements-mcp.txt en su entorno virtual."
    )
if DESTINO.exists():
    raise SystemExit(
        "opencode.json ya existe. Revíselo; el script no sobrescribe su configuración."
    )
configuracion = {
    "$schema": "https://opencode.ai/config.json",
    "mcp": {
        "andina": {
            "type": "local",
            "command": [sys.executable, "-X", "utf8", str(BASE / "servidor_mcp.py")],
            "cwd": str(BASE),
            "enabled": True,
            "timeout": 10000,
        }
    },
    "permission": {"edit": "ask", "bash": "ask", "andina_*": "ask"},
}
DESTINO.write_text(
    json.dumps(configuracion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    "Configuración generada: opencode.json. Abra OpenCode desde esta carpeta y elija un modelo disponible."
)
