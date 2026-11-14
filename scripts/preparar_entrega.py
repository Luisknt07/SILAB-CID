"""Entrega verificable del código confirmado en Git, sin historial ni datos privados.

Incluye los contenidos reales de Git LFS del árbol local; rechaza punteros sin
descargar. No consulta Django, PostgreSQL o Docker ni despliega la aplicación.
"""

import argparse
import gzip
import hashlib
import io
import json
import stat
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

OMITIR_RAICES = {'var', 'tmp', 'output', 'media', 'backups', 'static', 'staticfiles', 'logs'}
PRIVADOS = {'.git', '.aws', '.ssh', '.agents', '.codex', '.venv', '.venv_linux',
            'venv', 'node_modules', '.qa', '__pycache__', '.secreto-local'}
EXTENSIONES_PRIVADAS = {'.key', '.pem', '.p12', '.pfx', '.dump', '.sqlite3', '.pyc'}
PUNTERO_LFS = b'version https://git-lfs.github.com/spec/v1'


class LectorVerificado:
    def __init__(self, archivo):
        self.archivo = archivo
        self.digest = hashlib.sha256()

    def read(self, cantidad):
        bloque = self.archivo.read(cantidad)
        self.digest.update(bloque)
        return bloque


def git(raiz, *args):
    return subprocess.check_output(['git', *args], cwd=raiz, stderr=subprocess.PIPE)


def exigir_limpio(raiz):
    if git(raiz, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('Hay cambios versionados sin confirmar; hacer commit antes de empaquetar.')


def huella(ruta):
    digest = hashlib.sha256()
    with ruta.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    return digest.hexdigest()


def archivos_entrega(raiz):
    archivos = []
    for registro in git(raiz, 'ls-tree', '-rz', '--full-tree', 'HEAD').split(b'\0'):
        if not registro:
            continue
        meta, nombre = registro.split(b'\t', 1)
        modo, tipo, _ = meta.decode('ascii').split()
        nombre = nombre.decode('utf-8')
        partes = PurePosixPath(nombre).parts
        if partes[0] in OMITIR_RAICES:
            continue
        if (PurePosixPath(nombre).is_absolute() or '..' in partes or
                any(p in PRIVADOS or (p.startswith('.env') and p != '.env-example') for p in partes) or
                PurePosixPath(nombre).suffix.lower() in EXTENSIONES_PRIVADAS):
            raise ValueError(f'Archivo privado o no distribuible versionado: {nombre}')
        ruta = raiz.joinpath(*partes)
        if (tipo != 'blob' or modo not in {'100644', '100755'} or
                not ruta.resolve().is_relative_to(raiz) or ruta.is_symlink() or
                not stat.S_ISREG(ruta.stat().st_mode)):
            raise ValueError(f'Entrada sin archivo regular seguro: {nombre}')
        with ruta.open('rb') as archivo:
            if archivo.read(len(PUNTERO_LFS)) == PUNTERO_LFS:
                raise ValueError(f'Falta descargar Git LFS: {nombre}; ejecutar git lfs pull.')
        archivos.append({'ruta': nombre, 'bytes': ruta.stat().st_size,
                         'sha256': huella(ruta), 'modo': int(modo[-3:], 8)})
    return sorted(archivos, key=lambda fila: fila['ruta'])


def preparar(raiz, destino):
    raiz = Path(raiz).resolve()
    exigir_limpio(raiz)
    commit = git(raiz, 'rev-parse', 'HEAD').decode().strip()
    fecha = int(git(raiz, 'show', '-s', '--format=%ct', 'HEAD'))
    archivos = archivos_entrega(raiz)
    informe = {'commit': commit, 'archivos': archivos, 'bytes_codigo': sum(f['bytes'] for f in archivos),
               'datos_incluidos': False, 'historial_incluido': False}
    manifiesto = (json.dumps(informe, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    destino = Path(destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    paquete = destino / f'slcid-{commit[:12]}.tar.gz'
    # Creación exclusiva: nunca reemplazar una entrega previamente verificada.
    with paquete.open('xb') as salida:
        try:
            with gzip.GzipFile(filename='', mode='wb', fileobj=salida, mtime=0) as comprimido:
                with tarfile.open(fileobj=comprimido, mode='w|') as tar:
                    for fila in archivos:
                        info = tarfile.TarInfo('slcid/' + fila['ruta'])
                        info.size, info.mode, info.mtime = fila['bytes'], fila['modo'], fecha
                        with (raiz / fila['ruta']).open('rb') as archivo:
                            lector = LectorVerificado(archivo)
                            tar.addfile(info, lector)
                            if lector.digest.hexdigest() != fila['sha256'] or archivo.read(1):
                                raise ValueError(f"Cambió el archivo durante la entrega: {fila['ruta']}")
                    info = tarfile.TarInfo('slcid/ENTREGA.json')
                    info.size, info.mode, info.mtime = len(manifiesto), 0o644, fecha
                    tar.addfile(info, io.BytesIO(manifiesto))
            exigir_limpio(raiz)
            if git(raiz, 'rev-parse', 'HEAD').decode().strip() != commit:
                raise ValueError('Cambió HEAD durante la entrega; repetir desde una versión estable.')
        except BaseException:
            salida.close()
            paquete.unlink(missing_ok=True)
            raise
    checksum = paquete.with_name(paquete.name + '.sha256')
    checksum.write_text(f'{huella(paquete)}  {paquete.name}\n', encoding='ascii')
    return {'paquete': str(paquete), 'sha256': str(checksum), 'commit': commit,
            'archivos': len(archivos), 'bytes_codigo': informe['bytes_codigo'],
            'bytes_comprimidos': paquete.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    raiz = Path(__file__).resolve().parent.parent
    parser.add_argument('--destino', type=Path, default=raiz / 'var' / 'entregas')
    args = parser.parse_args()
    try:
        resultado = preparar(raiz, args.destino)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'No se creó la entrega: {exc}\n')
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
