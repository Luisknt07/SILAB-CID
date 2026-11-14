"""Archivos versionados a los que nadie hace referencia.

No borra nada: señala. Un archivo se considera referenciado cuando otro archivo
de texto del repositorio menciona su ruta de plantilla, su ruta estática o su
nombre. Lo que un paquete externo pide por su nombre -las plantillas de
allauth, por ejemplo- se declara aquí como excepción, con el motivo.
"""
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management import get_commands
from django.core.management.base import BaseCommand, CommandError

TEXTO = {'.py', '.html', '.css', '.js', '.md', '.txt', '.json', '.yml', '.sh', '.cfg', '.toml'}
# Archivos sin extensión que también citan rutas: el Dockerfile llama a un script.
SIN_EXTENSION = {'Dockerfile', 'Makefile', 'Procfile'}

# Inventarios y transcripciones nombran todo el árbol; si contaran como
# referencia, ningún archivo parecería huérfano.
NO_CUENTAN = {
    'docs/inventario-arquitectura.json',
    'docs/historial/CODEX_CONTEXT.md',
    'docs/historial/TRASPASO-CODEX.md',
}

# Archivos que nadie menciona en el repositorio y aun así se usan.
JUSTIFICADOS = {
    'apps/core/templates/account/password_change.html': 'allauth la pide por su nombre',
    'apps/core/templates/account/password_reset.html': 'allauth la pide por su nombre',
    'apps/core/templates/account/password_reset_done.html': 'allauth la pide por su nombre',
    'apps/core/templates/account/password_reset_from_key.html': 'allauth la pide por su nombre',
    'apps/core/templates/account/password_reset_from_key_done.html': 'allauth la pide por su nombre',
    'apps/core/templates/account/password_set.html': 'allauth la pide por su nombre',
    'apps/portal/static/font/simple-line-icons/LICENSE.md': 'licencia de la tipografía',
    'apps/portal/static/font/iconsmind-s/README.txt': 'condiciones de uso de la tipografía',
    'docker-compose.yml': 'se invoca desde la línea de órdenes, no desde el código',
    'config/asgi.py': 'entrada estándar de Django; este despliegue sirve por WSGI',
    'apps/formacion/management/cursos_precargados/aplicaciones_logisticas_kit/contenido/guias/unidad_02.md':
        'builder.source_files la distribuye en el ZIP docente; README indica las unidades 01 a 05',
    'apps/formacion/management/cursos_precargados/aplicaciones_logisticas_kit/contenido/guias/unidad_04.md':
        'builder.source_files la distribuye en el ZIP docente; README indica las unidades 01 a 05',
    'apps/formacion/management/cursos_precargados/aplicaciones_logisticas_kit/contenido/templates/403.html':
        'builder.source_files la distribuye en el ZIP; Django del proyecto docente la pide por convención',
}

# Las imágenes suelen cargarse por rutas construidas en ejecución -los mosaicos
# de un recorrido 360, las portadas generadas-, así que no se auditan aquí.
SIN_AUDITAR = {'.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif', '.ico',
               '.woff', '.woff2', '.ttf', '.eot', '.otf', '.mp4', '.pdf'}


def _agujas(ruta):
    """Por qué nombres puede buscarse un archivo."""
    partes = ruta.split('/')
    nombres = {Path(ruta).name}
    for carpeta in ('templates', 'static'):
        if carpeta in partes:
            nombres.add('/'.join(partes[partes.index(carpeta) + 1:]))
    if ruta.endswith('.py'):
        modulo = Path(ruta).stem
        nombres.update({ruta[:-3].replace('/', '.'), f'.{modulo}', f' {modulo}', f'"{modulo}"',
                        f"'{modulo}'"})
    return nombres


class Command(BaseCommand):
    help = 'Señala archivos versionados sin ninguna referencia; no borra nada.'

    def add_arguments(self, parser):
        parser.add_argument('--estricto', action='store_true',
                            help='Termina con error si aparece algún huérfano.')

    def handle(self, *args, **options):
        try:
            seguidos = subprocess.run(
                ['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=settings.BASE_DIR, capture_output=True,
                text=True, check=True).stdout.split('\n')
        except (OSError, subprocess.CalledProcessError) as error:
            raise CommandError(f'No se pudo listar el repositorio: {error}') from None

        # Las eliminaciones intencionales aún no preparadas en Git no son archivos
        # del árbol actual. El auditor de repositorio las enumera por separado.
        seguidos = [ruta for ruta in seguidos if ruta and (Path(settings.BASE_DIR) / ruta).is_file()]
        corpus = {}
        for ruta in seguidos:
            if ruta in NO_CUENTAN:
                continue
            if Path(ruta).suffix.lower() not in TEXTO and Path(ruta).name not in SIN_EXTENSION:
                continue
            archivo = Path(settings.BASE_DIR) / ruta
            try:
                corpus[ruta] = archivo.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue

        # Los destinos reales del visor se construyen por clave: enumerarlos
        # desde los mismos registros evita falsos positivos sin ocultar archivos nuevos.
        from apps.centros_id.presentation.secciones import PLANTILLAS, SECCIONES, SUBPAGINAS_VISTAS, FRAGMENTOS
        dinamicas = {f'apps/centros_id/templates/centros_id/visor/{PLANTILLAS.get(clave, clave)}.html'
                     for clave in (*SECCIONES, *SUBPAGINAS_VISTAS)}
        dinamicas.update(f'apps/centros_id/templates/centros_id/visor/fragmentos/{tipo}.html' for tipo in FRAGMENTOS)
        # Django descubre estos puntos de entrada por convención, no por imports.
        dinamicas.update(
            f'{modulo.replace(".", "/")}/management/commands/{nombre}.py'
            for nombre, modulo in get_commands().items()
            if isinstance(modulo, str) and modulo.startswith('apps.')
        )
        huerfanos = []
        for ruta in seguidos:
            sufijo = Path(ruta).suffix.lower()
            if sufijo in SIN_AUDITAR or ruta in JUSTIFICADOS or ruta in NO_CUENTAN or ruta in dinamicas:
                continue
            if sufijo not in TEXTO:
                continue
            if '/migrations/' in ruta or Path(ruta).name.startswith(('__init__', 'test_')):
                continue
            agujas = _agujas(ruta)
            if any(any(aguja in texto for aguja in agujas)
                   for origen, texto in corpus.items() if origen != ruta):
                continue
            huerfanos.append(ruta)

        for ruta in huerfanos:
            self.stdout.write(self.style.WARNING(f'sin referencia: {ruta}'))
        resumen = f'{len(huerfanos)} archivos sin referencia de {len(seguidos)} en el árbol de trabajo.'
        self.stdout.write(self.style.SUCCESS(resumen) if not huerfanos else resumen)
        if huerfanos and options['estricto']:
            raise CommandError('Hay archivos sin referencia.')
