"""Inventario reproducible de archivos fuente; no lee .env ni imprime valores de secretos."""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = {'.py', '.html', '.js', '.mjs', '.cjs', '.css', '.md', '.toml', '.yml', '.yaml', '.sh', '.ps1', '.txt', '.json'}


def archivo_privado(path):
    return (path.name == '.secreto-local' or (path.name.startswith('.env') and path.name != '.env-example')
            or path.suffix.lower() in {'.pfx', '.p12', '.key', '.pem', '.dump', '.sqlite3'})


def modulos_canonicos(files):
    modules = {}
    for name in files:
        if not name.endswith('.py'):
            continue
        parts = name[:-3].split('/')
        if parts[-1] == '__init__':
            parts.pop()
        for n in range(1, len(parts) + 1):
            module = '.'.join(parts[:n])
            modules[module.casefold()] = module
    return modules


def revisar_imports(tree, name, modules):
    package = name[:-3].split('/')[:-1]
    errors = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = ['.'.join(package[:len(package) - node.level + 1]
                              + ([node.module] if node.module else []))
                     if node.level else (node.module or '')]
        for module in names:
            canonical = modules.get(module.casefold())
            if canonical and canonical != module:
                errors.append({'tipo': 'mayusculas_import_linux', 'archivo': name,
                               'linea': node.lineno, 'modulo': module, 'correcto': canonical})
    return errors


def audit():
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, capture_output=True, check=True)
    listed = set(result.stdout.decode('utf-8').strip('\0').split('\0')) - {''}
    removed = subprocess.run(['git', 'ls-files', '--deleted', '-z'], cwd=ROOT, capture_output=True, check=True)
    deleted = set(removed.stdout.decode('utf-8').strip('\0').split('\0')) - {''}
    files = sorted(listed - deleted)
    modules = modulos_canonicos(files)
    errors, notices = [], []
    hashes, cases = defaultdict(list), defaultdict(list)
    total = 0
    for name in files:
        path = ROOT / name
        if not path.is_file():
            errors.append({'tipo': 'archivo_ausente', 'archivo': name})
            continue
        cases[name.casefold()].append(name)
        # No leer ni calcular hashes de secretos, aunque alguien los añada al
        # índice de Git por error. El nombre basta para bloquear el inventario.
        if archivo_privado(path):
            errors.append({'tipo': 'artefacto_privado', 'archivo': name})
            continue
        data = path.read_bytes()
        total += len(data)
        if data and path.name != '__init__.py':
            hashes[hashlib.sha256(data).hexdigest()].append(name)
        if re.search(r'(?:copia|copy|backup|\.bak|\.tmp|~$)', path.name, re.I) and path.suffix in SOURCE:
            notices.append({'tipo': 'nombre_para_revisar', 'archivo': name})
        if path.suffix not in SOURCE:
            continue
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            errors.append({'tipo': 'codificacion_no_utf8', 'archivo': name})
            continue
        if path.suffix == '.py':
            try:
                tree = ast.parse(text, filename=name)
                errors.extend(revisar_imports(tree, name, modules))
            except SyntaxError as exc:
                errors.append({'tipo': 'sintaxis_python', 'archivo': name, 'linea': exc.lineno})
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r'AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', line):
                errors.append({'tipo': 'secreto_probable', 'archivo': name, 'linea': number})
            if '/tests/' not in name and path.suffix in {'.py', '.js', '.sh', '.ps1'}:
                match = re.search(r'''(?i)(?:SECRET_KEY|PASSWORD|CLIENT_SECRET|API_KEY|ACCESS_TOKEN)\s*=\s*["']([^"'\n]{20,})["']''', line)
                if match and not match[1].startswith('$') and not any(word in match[1].lower() for word in ('replace', 'example', 'demo', 'prueba', 'test', 'clave', 'aleatoria', 'inexistente')):
                    errors.append({'tipo': 'credencial_literal_revisar', 'archivo': name, 'linea': number})
    return {'archivos': len(files), 'bytes': total, 'raices': sorted({p.split('/')[0] for p in files}),
            'errores': errors, 'eliminados_del_arbol': sorted(deleted),
            'colisiones_linux_windows': [names for names in cases.values() if len(names) > 1],
            'duplicados_exactos': [names for names in hashes.values() if len(names) > 1],
            'avisos': notices}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    parser.add_argument('--estricto', action='store_true')
    args = parser.parse_args()
    report = audit()
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(output + '\n', encoding='utf-8')
    print(f"{report['archivos']} archivos; {len(report['errores'])} errores; "
          f"{len(report['duplicados_exactos'])} grupos duplicados; "
          f"{len(report['colisiones_linux_windows'])} colisiones de nombre.")
    for error in report['errores']:
        print(json.dumps(error, ensure_ascii=False))
    if args.estricto and (report['errores'] or report['colisiones_linux_windows']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
