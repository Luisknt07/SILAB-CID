"""Inventario de entradas y autoridad declarada; nunca evalua permisos efectivos.

La operacion compartida se conserva como tal: un nombre de ruta o archivo no
demuestra que pertenezca a una categoria ni que se pueda suspender con seguridad.
"""
import ast
from contextlib import ExitStack
import hashlib
import inspect
import os
from pathlib import Path
import re


def nombre_ast(nodo):
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        base = nombre_ast(nodo.value)
        return f'{base}.{nodo.attr}' if base else nodo.attr
    if isinstance(nodo, ast.Call):
        return nombre_ast(nodo.func)
    return ''


def archivo_local(archivo, raiz):
    if not archivo:
        return None
    ruta = Path(archivo).resolve()
    try:
        return ruta.relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return None


def origen(objeto, raiz):
    objeto = inspect.unwrap(getattr(objeto, 'view_class', objeto))
    try:
        archivo = archivo_local(inspect.getsourcefile(objeto), raiz)
        linea = inspect.getsourcelines(objeto)[1] if archivo else None
    except (TypeError, OSError):
        archivo, linea = None, None
    return {'archivo': archivo, 'linea': linea}


def rutas(patterns, raiz, prefijo=''):
    from django.urls import URLResolver

    for patron in patterns:
        ruta = prefijo + str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from rutas(patron.url_patterns, raiz, ruta)
        else:
            callback = getattr(patron.callback, 'view_class', patron.callback)
            yield {'ruta': ruta, 'nombre': patron.name,
                   'callback': f'{callback.__module__}.{callback.__name__}',
                   **origen(callback, raiz)}


def analizar_python(ruta, raiz):
    archivo = archivo_local(ruta, raiz)
    if archivo is None:
        raise ValueError('El inventario solo lee codigo dentro del proyecto.')
    contenido = ruta.read_bytes()
    try:
        arbol = ast.parse(contenido, filename=archivo)
    except (SyntaxError, UnicodeError):
        raise ValueError(f'No se pudo analizar el archivo de codigo {archivo}.') from None
    return {'archivo': archivo, 'sha256': hashlib.sha256(contenido).hexdigest()}, arbol


def senales(raiz):
    resultado = []
    # Los kits docentes pueden contener su propio entorno de QA. Podar antes
    # de recorrer evita analizar dependencias de terceros como codigo propio.
    excluidas = {'tests', 'migrations', '__pycache__', '.qa', '.venv', 'venv',
                 'site-packages', 'node_modules', '.git'}
    for carpeta in (raiz / 'apps',):
        for directorio, subcarpetas, archivos in os.walk(carpeta):
            subcarpetas[:] = sorted(c for c in subcarpetas if c not in excluidas)
            for archivo in sorted(a for a in archivos if a.endswith('.py')):
                ruta = Path(directorio) / archivo
                datos, arbol = analizar_python(ruta, raiz)
                for nodo in ast.walk(arbol):
                    if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for decorador in nodo.decorator_list:
                        if not isinstance(decorador, ast.Call) or nombre_ast(decorador.func).split('.')[-1] != 'receiver':
                            continue
                        resultado.append({**datos, 'funcion': nodo.name, 'linea': nodo.lineno,
                            'senal': nombre_ast(decorador.args[0]) if decorador.args else '',
                            'sender': next((nombre_ast(k.value) for k in decorador.keywords if k.arg == 'sender'), ''),
                            'revisar_efectos_transitivos': True})
    return sorted(resultado, key=lambda s: (s['archivo'], s['linea']))


def comandos_y_scripts(raiz, paquetes):
    from django.core.management import get_commands

    comandos = []
    for nombre, paquete in sorted(get_commands().items()):
        if paquete not in paquetes:
            continue
        ruta = raiz.joinpath(*paquete.split('.'), 'management', 'commands', nombre + '.py')
        datos, arbol = analizar_python(ruta, raiz)
        # Nombres de llamadas, sin argumentos, literales o ejecucion del handler.
        llamadas = sorted({nombre_ast(n.func) for n in ast.walk(arbol) if isinstance(n, ast.Call)} - {''})
        comandos.append({**datos, 'nombre': nombre, 'paquete': paquete,
                         'referencias_estaticas': llamadas, 'autoridad_requiere_revision': True})
    scripts = []
    candidatos = sorted(p for p in (raiz / 'scripts').iterdir() if p.suffix in ('.sh', '.ps1', '.py'))
    for ruta in candidatos:
        archivo = archivo_local(ruta, raiz)
        if archivo is None:
            raise ValueError('El inventario solo lee codigo dentro del proyecto.')
        contenido = ruta.read_bytes()
        texto = contenido.decode('utf-8-sig')
        scripts.append({'archivo': archivo, 'sha256': hashlib.sha256(contenido).hexdigest(),
            'referencias_comandos': [c['nombre'] for c in comandos
                                    if re.search(r'\b' + re.escape(c['nombre']) + r'\b', texto)],
            'referencias_scripts': [p.name for p in candidatos if p != ruta and p.name in texto],
            'autoridad_requiere_revision': True})
    return comandos, scripts


def _sin_sql(execute, sql, params, many, context):
    raise ValueError('El inventario no permite consultas ni escrituras de base de datos.')


def inventario_superficies(seleccion=None):
    """Bloquea SQL en todos los aliases durante la inspeccion de codigo confiable.

    No ejecuta callbacks HTTP, comprobaciones de permisos, comandos operativos,
    scripts ni receivers. La configuracion Django de arranque queda fuera del
    alcance del wrapper; no es una sandbox para codigo Python privilegiado.
    """
    from django.db import connections

    with ExitStack() as pila:
        for conexion in connections.all():
            pila.enter_context(conexion.execute_wrapper(_sin_sql))
        return _inventario_superficies(seleccion)


def _inventario_superficies(seleccion):
    from django.apps import apps
    from django.conf import settings
    from django.contrib import admin
    from django.urls import get_resolver

    from config.capacidades import CAPACIDADES_CONTROLADAS
    from config.modulos import registro_de_despliegue
    from .inventario import inventario_del_proyecto

    registro = registro_de_despliegue()
    seleccion = tuple(sorted(registro.manifiestos)) if seleccion is None else seleccion
    registro.plan(seleccion)  # Valida sin confundir seleccion con habilitacion.
    raiz = Path(settings.BASE_DIR)
    base = inventario_del_proyecto()
    modulos = []
    for identificador in sorted(set(seleccion)):
        manifiesto = registro.manifiestos[identificador]
        entradas = [dict(r, urlconf=urlconf) for urlconf in manifiesto.rutas
                    for r in rutas(get_resolver(urlconf).url_patterns, raiz)]
        modelos = [m for m in base['modelos_propios'] if m['propietario_actual'] == manifiesto.paquete]
        modulos.append({'identificador': identificador, 'etapa': manifiesto.etapa,
            'paquete': manifiesto.paquete, 'dependencias': list(manifiesto.dependencias),
            'capacidades': [{'identificador': c, 'registrada_en_politica': (identificador, c) in CAPACIDADES_CONTROLADAS}
                            for c in manifiesto.capacidades],
            'rutas_propias': entradas, 'modelos': modelos,
            'asignacion_ruta_a_capacidad': 'requiere_revision_manual',
            'operacion_por_tipo': 'aplicacion_propietaria_y_capacidades_compartidas' if identificador in
                 ('observatorios', 'laboratorios', 'plantas_piloto', 'centros_experimentales') else 'segun_alcance_declarado'})
    administracion = []
    for modelo, administrador in sorted(admin.site._registry.items(), key=lambda item: item[0]._meta.label):
        if not modelo.__module__.startswith('apps.'):
            continue
        clase = type(administrador)
        administracion.append({'modelo': modelo._meta.label,
            'clase': f'{clase.__module__}.{clase.__name__}', **origen(clase, raiz),
            'rutas': list(rutas(administrador.get_urls(), raiz)),
            'acciones_declaradas': None if administrador.actions is None else [
                a if isinstance(a, str) else {'nombre': a.__name__, **origen(a, raiz)}
                for a in administrador.actions],
            'revisar_permisos_objeto_y_acciones_dinamicas': True})
    paquetes = {a.name for a in apps.get_app_configs() if a.name.startswith('apps.')}
    comandos, scripts = comandos_y_scripts(raiz, paquetes)
    heredadas = list(rutas(get_resolver('config.rutas_operativas').url_patterns, raiz))
    receptores = senales(raiz)
    return {'version_inventario': 1, 'alcance': 'codigo_declarado_no_autorizacion_efectiva',
        'no_concede_permisos': True, 'no_consulta_datos': True,
        'seleccion_modulos': sorted(set(seleccion)), 'modulos': modulos,
        'superficies_compartidas': {'nota': 'No se atribuyen a un tipo por su URL; aplicabilidad y autoridad requieren revision.',
            'rutas_heredadas': heredadas, 'administracion': administracion,
            'acciones_globales_admin': [{'nombre': nombre, **origen(accion, raiz)}
                                       for nombre, accion in admin.site.actions],
            'comandos': comandos, 'scripts': scripts, 'senales': receptores},
        'resumen': {'modulos_seleccionados': len(modulos), 'rutas_heredadas': len(heredadas),
            'modelos_heredados': len(base['modelos']), 'modelos_propios': len(base['modelos_propios']),
            'administradores': len(administracion), 'comandos': len(comandos),
            'scripts': len(scripts), 'receivers_decorados': len(receptores)}}
