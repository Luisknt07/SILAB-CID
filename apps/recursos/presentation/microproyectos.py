"""Paquetes Python: inspección sin importar ni ejecutar su código en CITT."""
from pathlib import PurePosixPath
import stat
import zipfile

from django.core.exceptions import ValidationError

OMITIR = {'.venv', 'venv', '.git', '__pycache__', 'node_modules'}


def contiene_django(archivo):
    posicion = archivo.tell()
    try:
        with zipfile.ZipFile(archivo) as paquete:
            return any(PurePosixPath(n).name == 'manage.py' and not any(
                parte in OMITIR for parte in PurePosixPath(n).parts) for n in paquete.namelist())
    finally:
        archivo.seek(posicion)


def inspeccionar_paquete(archivo):
    posicion = archivo.tell()
    try:
        with zipfile.ZipFile(archivo) as paquete:
            miembros = paquete.infolist()
            if len(miembros) > 20000 or sum(x.file_size for x in miembros) > 512 * 1024 * 1024:
                raise ValidationError('El paquete supera el límite de 20.000 entradas o 512 MB descomprimidos.')
            seleccion = []
            for info in miembros:
                ruta = PurePosixPath(info.filename)
                if (ruta.is_absolute() or '..' in ruta.parts or '\\' in info.filename
                        or ':' in info.filename or stat.S_ISLNK(info.external_attr >> 16)):
                    raise ValidationError('El ZIP contiene rutas no permitidas o enlaces simbólicos.')
                if (info.is_dir() or any(p in OMITIR for p in ruta.parts)
                        or ruta.name.startswith('.env') or ruta.suffix in {'.pyc', '.pyo'}):
                    continue
                seleccion.append(info.filename)
            raices = [PurePosixPath(n).parent for n in seleccion if PurePosixPath(n).name == 'manage.py']
            if len(raices) != 1:
                raise ValidationError('El ZIP debe contener un único proyecto con manage.py.')
            raiz = raices[0]
            nombres = {str(PurePosixPath(n).relative_to(raiz)): n for n in seleccion
                       if PurePosixPath(n).is_relative_to(raiz)}
            if 'requirements.txt' not in nombres:
                raise ValidationError('Falta requirements.txt junto a manage.py.')
            return nombres
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValidationError('No se pudo leer el ZIP del microproyecto.') from exc
    finally:
        archivo.seek(posicion)
