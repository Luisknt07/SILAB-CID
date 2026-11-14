"""Puesta en marcha inmediata desde consola, con el mismo procedimiento que el servicio."""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.recursos.presentation.despliegue_microproyectos import MODULO, ErrorDespliegue, desplegar
from apps.recursos.models.recursos import DespliegueMicroproyecto, Recurso


class Command(BaseCommand):
    help = 'Pone en marcha un microproyecto Django en Docker local, conservando su SQLite.'

    def add_arguments(self, parser):
        parser.add_argument('recurso', type=int)
        parser.add_argument('--project-settings', default='',
                            help='Solo si manage.py no declara DJANGO_SETTINGS_MODULE. Ejemplo: config.settings.base')

    def handle(self, *args, **opciones):
        recurso = Recurso.objects.filter(pk=opciones['recurso']).first()
        if recurso is None:
            raise CommandError('No existe ese recurso.')
        modulo = opciones['project_settings']
        if modulo and not MODULO.fullmatch(modulo):
            raise CommandError('Módulo de configuración inválido.')
        registro = DespliegueMicroproyecto.objects.create(
            recurso=recurso, hash_sha256=recurso.hash_sha256, origen='consola', estado='en_curso',
            iniciado=timezone.now())
        try:
            url = desplegar(recurso, modulo_forzado=modulo)
        except ErrorDespliegue as exc:
            registro.estado, registro.detalle = 'error', str(exc)
            raise CommandError(str(exc)) from exc
        else:
            registro.estado, registro.detalle = 'completado', url
        finally:
            registro.terminado = timezone.now()
            registro.save(update_fields=['estado', 'detalle', 'terminado'])
        self.stdout.write(self.style.SUCCESS(f'Microproyecto en funcionamiento: {url}'))
