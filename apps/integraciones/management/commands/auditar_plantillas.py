"""Compila plantillas y comprueba referencias literales, sin renderizar ni consultar datos."""
import json
import subprocess
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError
from django.forms.renderers import get_default_renderer
from django.template import engines, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates
from django.template.base import Lexer, TokenType


def directorios_activos(backend):
    """Raíces que los loaders configurados pueden leer, incluidas apps y wrappers."""
    directorios = set()

    def visitar(loader):
        if hasattr(loader, 'get_dirs'):
            directorios.update(Path(directorio).resolve() for directorio in loader.get_dirs())
        for hijo in getattr(loader, 'loaders', ()):
            visitar(hijo)

    for loader in backend.engine.template_loaders:
        visitar(loader)
    return directorios


class Command(BaseCommand):
    help = 'Compila plantillas de las raíces Django activas y resuelve static/include/extends literales.'

    def handle(self, *args, **options):
        paths = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
            cwd=settings.BASE_DIR).decode().strip('\0').split('\0')
        errors, revisadas = [], set()
        for backend in engines.all():
            if not isinstance(backend, DjangoTemplates):
                continue
            directorios = directorios_activos(backend)
            for name in paths:
                path = (Path(settings.BASE_DIR) / name).resolve()
                if (not name.endswith('.html') or not path.is_file()
                        or not any(path.is_relative_to(directorio) for directorio in directorios)):
                    continue
                revisadas.add(name)
                try:
                    source = path.read_text(encoding=backend.engine.file_charset)
                    backend.from_string(source)
                    for token in Lexer(source).tokenize():
                        if token.token_type != TokenType.BLOCK:
                            continue
                        bits = token.split_contents()
                        if len(bits) < 2 or bits[0] not in {'static', 'include', 'extends'}:
                            continue
                        quoted = bits[1]
                        if not quoted.startswith(('"', "'")):
                            continue
                        target = quoted[1:-1]
                        if bits[0] == 'static':
                            if not finders.find(target):
                                raise ValueError('Estático inexistente: ' + target)
                        else:
                            try:
                                backend.get_template(target)
                            except TemplateDoesNotExist:
                                if not target.startswith('django/forms/'):
                                    raise
                                # Los widgets usan un renderer propio con las plantillas
                                # incorporadas de Django, fuera del motor de páginas.
                                get_default_renderer().get_template(target)
                except Exception as error:
                    errors.append({'archivo': name, 'motor': backend.name, 'error': str(error)})
        self.stdout.write(json.dumps({'plantillas': len(revisadas), 'errores': errors}, ensure_ascii=False, indent=2))
        if errors:
            raise CommandError('Existen plantillas o referencias inválidas.')
