"""Compila plantillas y comprueba referencias literales, sin renderizar ni consultar datos."""
import json
import re
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


# Panel de gestión de la unidad: sus botones «editar» pasan los valores al formulario en atributos.
PANEL_DE_GESTION = '/unidades/gestion/'
_ATRIBUTO_CON_VARIABLE = re.compile(r'\b(data-[\w-]+|value)="([^"]*\{\{[^"]*)"')
_VARIABLE = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
_CONTROL_NUMERICO = re.compile(r'<(?:input\b[^>]*type="number"|progress\b|meter\b)')
_SIN_FORMATO_LOCAL = re.compile(r"^(unlocalize|stringformat|floatformat:['\"][^'\"]*u['\"])")


def campos_decimales():
    """Nombres de los campos decimales o flotantes de los modelos instalados."""
    from django.apps import apps
    from django.db import models
    return {campo.name for modelo in apps.get_models() for campo in modelo._meta.get_fields()
            if isinstance(campo, (models.DecimalField, models.FloatField))}


def decimales_localizados(source, decimales):
    """Atributos del panel que recibirían un decimal con coma («1000,000»).

    Con el idioma español las plantillas imprimen los decimales con coma; un `<input type="number">` no la
    acepta y queda vacío, y el JavaScript que lee el atributo no puede calcular. Todo `data-*` del panel, y
    todo `value` de un control numérico, cuya variable termina en el nombre de un campo decimal debe pasar
    por `unlocalize` (o `floatformat` con sufijo «u»).
    """
    problemas = []
    for hallazgo in _ATRIBUTO_CON_VARIABLE.finditer(source):
        atributo, valor = hallazgo.groups()
        if atributo == 'value':
            etiqueta = source[source.rfind('<', 0, hallazgo.start()):hallazgo.start()]
            if not _CONTROL_NUMERICO.match(etiqueta):
                continue
        for expresion in _VARIABLE.findall(valor):
            base, *filtros = (parte.strip() for parte in expresion.split('|'))
            if base.split('.')[-1] not in decimales:
                continue
            if not any(_SIN_FORMATO_LOCAL.match(filtro) for filtro in filtros):
                problemas.append(f'{atributo}="{{{{ {expresion} }}}}"')
    return problemas


class Command(BaseCommand):
    help = 'Compila plantillas de las raíces Django activas y resuelve static/include/extends literales.'

    def handle(self, *args, **options):
        paths = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
            cwd=settings.BASE_DIR).decode().strip('\0').split('\0')
        errors, revisadas = [], set()
        decimales = campos_decimales()
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
                    if PANEL_DE_GESTION in name:
                        localizados = decimales_localizados(source, decimales)
                        if localizados:
                            raise ValueError(
                                'Decimal con formato local en un atributo numérico; aplica |unlocalize: '
                                + '; '.join(localizados))
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
