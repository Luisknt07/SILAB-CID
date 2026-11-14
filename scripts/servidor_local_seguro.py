"""Servidor de desarrollo local sin credenciales de mantenimiento en su entorno."""
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values


def main():
    raiz = Path(__file__).resolve().parents[1]
    entorno = {**dotenv_values(raiz / '.env'), **os.environ}
    entorno = {clave: str(valor) for clave, valor in entorno.items() if valor is not None}
    for clave in list(entorno):
        if clave.startswith(('DB_MIGRATION_', 'DB_BACKUP_', 'DB_RUNTIME_',
                             'CENTROS_DB_MIGRATION_', 'CENTROS_DB_BACKUP_', 'CENTROS_DB_RUNTIME_')):
            entorno.pop(clave)
    entorno.update(PYTHON_DOTENV_DISABLED='1', PYTHONUTF8='1')
    entorno.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    comando = [sys.executable, str(raiz / 'manage.py')]
    validacion = subprocess.run([*comando, 'verificar_seguridad_bd', '--all'], cwd=raiz, env=entorno)
    if validacion.returncode:
        return validacion.returncode
    return subprocess.call([*comando, 'runserver', '127.0.0.1:8000', '--noreload'], cwd=raiz, env=entorno)


if __name__ == '__main__':
    sys.exit(main())
