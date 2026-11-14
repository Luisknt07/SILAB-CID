"""Nonces solo en scripts de plantillas de código confiable, antes de renderizar datos."""
from html.parser import HTMLParser

from django.template.loaders.app_directories import Loader as AppLoader
from django.template.loaders.filesystem import Loader as FileLoader


class _Scripts(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.edits = []

    def handle_starttag(self, tag, attrs):
        line, column = self.getpos()
        at = self.offsets[line - 1] + column
        if tag == 'script' and not any(key == 'nonce' for key, _ in attrs):
            self.edits.append((at + 7, ' nonce="{{ request.csp_nonce }}"'))

    def handle_endtag(self, tag):
        if tag == 'head':
            line, column = self.getpos()
            self.edits.append((self.offsets[line - 1] + column,
                '{% load static %}<script nonce="{{ request.csp_nonce }}" defer '
                'src="{% static "portal/js/components/acciones_seguras.js" %}?v=20261008-seguridad-v1"></script>'))


def asegurar_scripts(source):
    parser = _Scripts(source)
    parser.feed(source)
    for at, text in sorted(parser.edits, reverse=True):
        source = source[:at] + text + source[at:]
    return source


class NonceLoaderMixin:
    def get_contents(self, origin):
        return asegurar_scripts(super().get_contents(origin))


class FilesystemLoader(NonceLoaderMixin, FileLoader):
    pass


class AppDirectoriesLoader(NonceLoaderMixin, AppLoader):
    pass
