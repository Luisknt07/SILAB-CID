"""Registro anterior al traslado, para probar RunPython históricos con sus tablas."""
from functools import lru_cache
from django.db.migrations.loader import MigrationLoader

@lru_cache(maxsize=1)
def registro_anterior():
    return MigrationLoader(None).project_state(
        [('webcitt', '0329_vistas_historicas_partidas')]
    ).apps
