"""Recorre todas las pantallas del administrador con los datos reales, sin escribir.

Abre como superusuario la lista, el alta, la ficha del primer registro y las
rutas propias de cada panel registrado, además del índice y cada área. Solo
hace GET: no crea sesiones, no deja rastro en el historial ni toca filas.
Una pantalla que lance una excepción o responda distinto de 200 es una falla.
"""

import traceback
from urllib.parse import urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.base import SessionBase
from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory
from django.urls import NoReverseMatch, resolve, reverse

from apps.integraciones.admin.por_tipo import TODAS


class SesionVolatil(SessionBase):
    """Sesión en memoria: las vistas la piden, nadie la guarda."""

    def load(self):
        return {}

    def exists(self, session_key):
        return False

    def create(self):
        self._session_key = None

    def save(self, must_create=False):
        pass

    def delete(self, session_key=None):
        pass


class Command(BaseCommand):
    help = 'Abre cada lista, alta, ficha y ruta propia del admin como superusuario y reporta las que fallan.'

    def add_arguments(self, parser):
        parser.add_argument('--detalle', action='store_true', help='Imprime el rastro completo de cada falla.')
        parser.add_argument('--solo', default='', help='Limita la auditoría a una app (por ejemplo plantas_piloto).')

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        self.usuario = Usuario.objects.filter(is_superuser=True, is_active=True, is_staff=True).first()
        if self.usuario is None:
            raise CommandError('No hay un superusuario activo con el que recorrer el administrador.')
        self.fabrica = RequestFactory()
        self.detalle = opciones['detalle']
        self.fallas = []
        self.abiertas = 0

        self.abrir(reverse('admin:index'))
        etiquetas = sorted({modelo._meta.app_label for modelo in admin.site._registry})
        for etiqueta in etiquetas:
            if opciones['solo'] and etiqueta != opciones['solo']:
                continue
            self.abrir(reverse('admin:app_list', kwargs={'app_label': etiqueta}))

        for modelo, panel in sorted(admin.site._registry.items(), key=lambda par: par[0]._meta.label):
            if opciones['solo'] and modelo._meta.app_label != opciones['solo']:
                continue
            self.auditar_panel(modelo, panel)

        self.stdout.write('')
        self.stdout.write(f'Pantallas abiertas: {self.abiertas}. Fallas: {len(self.fallas)}.')
        for url, motivo in self.fallas:
            self.stdout.write(self.style.ERROR(f'  {url}  ->  {motivo}'))
        if self.fallas:
            raise CommandError('El administrador tiene pantallas que fallan.')
        self.stdout.write(self.style.SUCCESS('Todas las pantallas del administrador responden.'))

    # -- recorrido ---------------------------------------------------------

    def auditar_panel(self, modelo, panel):
        opts = modelo._meta
        base = f'admin:{opts.app_label}_{opts.model_name}_'
        peticion = self.peticion('/admin/')
        lista = reverse(base + 'changelist')
        self.abrir(lista)
        if hasattr(panel, 'ruta'):
            # La puerta por unidad y la lista completa son dos pantallas distintas.
            self.abrir(lista, {TODAS: '1'})
        if panel.has_add_permission(peticion):
            self.abrir(reverse(base + 'add'))
        try:
            primero = panel.get_queryset(peticion).order_by('pk').first()
        except Exception as error:  # noqa: BLE001 - la consulta rota es en si una falla
            self.registrar(lista, error)
            primero = None
        if primero is not None:
            self.abrir(reverse(base + 'change', args=[primero.pk]))
        for patron in panel.get_urls():
            ruta = str(patron.pattern)
            if not patron.name or '<' in ruta or ruta.endswith(('add/', 'changelist/')) or ruta == '':
                continue
            try:
                self.abrir(reverse(f'admin:{patron.name}'))
            except NoReverseMatch:
                continue

    def peticion(self, url, parametros=None):
        peticion = self.fabrica.get(url, parametros or {})
        peticion.user = self.usuario
        peticion.session = SesionVolatil()
        peticion._messages = FallbackStorage(peticion)
        return peticion

    def abrir(self, url, parametros=None):
        self.abiertas += 1
        try:
            destino, vistos = url, set()
            for salto in range(6):
                if destino in vistos:
                    raise ValueError('La redirección administrativa forma un ciclo.')
                vistos.add(destino)
                partes = urlsplit(destino)
                if partes.scheme or partes.netloc or not partes.path.startswith('/'):
                    raise ValueError('La redirección debe permanecer dentro del administrador local.')
                coincidencia = resolve(partes.path)
                if salto and (coincidencia.namespace != 'admin' or coincidencia.url_name in ('login', 'logout')):
                    raise ValueError('La redirección abandona la pantalla administrativa autorizada.')
                peticion = self.peticion(destino, parametros if not salto else None)
                peticion.resolver_match = coincidencia
                respuesta = coincidencia.func(peticion, *coincidencia.args, **coincidencia.kwargs)
                if respuesta.status_code not in (301, 302, 303, 307, 308):
                    break
                destino = respuesta['Location']
            else:
                raise ValueError('Demasiadas redirecciones administrativas.')
            if hasattr(respuesta, 'render'):
                respuesta.render()
        except Exception as error:  # noqa: BLE001 - se informa, no se interrumpe
            self.registrar(url if not parametros else f'{url}?{TODAS}=1', error)
            return
        if respuesta.status_code != 200:
            self.registrar(url if not parametros else f'{url}?{TODAS}=1',
                           f'respondió {respuesta.status_code}')

    def registrar(self, url, error):
        motivo = error if isinstance(error, str) else f'{type(error).__name__}: {error}'
        self.fallas.append((url, str(motivo)[:200]))
        self.stdout.write(self.style.ERROR(f'FALLA {url}: {motivo}'))
        if self.detalle and not isinstance(error, str):
            self.stdout.write(''.join(traceback.format_exception(error)))
