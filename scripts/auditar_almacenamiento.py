"""Mide archivos locales sin leer contenidos, seguir enlaces ni borrar datos."""

import argparse
import json
import os
import stat
from collections import defaultdict
from pathlib import Path


def inventario(raiz):
    raiz = Path(raiz).resolve()
    carpetas = defaultdict(lambda: [0, 0])
    grandes, errores, enlaces = [], [], []
    pendientes = [(raiz, ())]
    total = cantidad = 0
    while pendientes:
        directorio, partes = pendientes.pop()
        try:
            with os.scandir(directorio) as entradas:
                for entrada in entradas:
                    ruta = partes + (entrada.name,)
                    nombre = '/'.join(ruta)
                    try:
                        info = entrada.stat(follow_symlinks=False)
                        if (stat.S_ISLNK(info.st_mode) or
                                getattr(info, 'st_file_attributes', 0) & 1024):
                            enlaces.append(nombre)
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            pendientes.append((Path(entrada.path), ruta))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        total += info.st_size
                        cantidad += 1
                        for nivel in range(1, min(3, len(ruta)) + 1):
                            grupo = carpetas['/'.join(ruta[:nivel])]
                            grupo[0] += info.st_size
                            grupo[1] += 1
                        grandes.append({'ruta': nombre, 'bytes': info.st_size})
                        if len(grandes) > 50:
                            grandes.sort(key=lambda r: r['bytes'], reverse=True)
                            del grandes[25:]
                    except OSError as exc:
                        errores.append({'ruta': nombre, 'tipo': type(exc).__name__})
        except OSError as exc:
            errores.append({'ruta': '/'.join(partes), 'tipo': type(exc).__name__})
    filas = [{'ruta': k, 'bytes': v[0], 'archivos': v[1]} for k, v in carpetas.items()]
    filas.sort(key=lambda r: (-r['bytes'], r['ruta']))
    return {
        'bytes': total, 'archivos': cantidad, 'completo': not errores,
        'raices': [r for r in filas if '/' not in r['ruta']],
        'detalle': [r for r in filas if '/' in r['ruta']][:60],
        'mayores': sorted(grandes, key=lambda r: -r['bytes'])[:25],
        'enlaces_omitidos': sorted(enlaces), 'errores': errores,
        'criterio': 'Bytes lógicos; no equivale a espacio asignado ni incluye Docker Desktop.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    informe = inventario(args.raiz)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{informe['archivos']} archivos; {informe['bytes'] / 10**9:.3f} GB lógicos")
    for fila in informe['raices']:
        print(f"{fila['bytes'] / 10**9:8.3f} GB  {fila['archivos']:7d}  {fila['ruta']}")
    if informe['errores']:
        print(f"Inventario incompleto: {len(informe['errores'])} rutas no legibles.")
        raise SystemExit(1)


if __name__ == '__main__':
    main()
