"""Monitor optativo para instalaciones sin el scheduler de producción."""
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, close_old_connections

from apps.recursos.presentation.traspasos import detectar_equipos_sin_uso


class Command(BaseCommand):
    help = 'Actualiza alertas de uso periódicamente según la política configurada, sin enviar mensajes ni mover activos.'

    def add_arguments(self, parser):
        parser.add_argument('--intervalo', type=int, default=60, help='Segundos entre revisiones; mínimo 5. No es un umbral de uso.')
        parser.add_argument('--una-vez', action='store_true', help='Revisa una vez y termina.')

    def handle(self, *args, **opciones):
        intervalo = opciones['intervalo']
        if intervalo < 5:
            raise CommandError('El intervalo de revisión debe ser de al menos 5 segundos.')
        try:
            while True:
                close_old_connections()
                try:
                    resultado = detectar_equipos_sin_uso()
                except DatabaseError as error:
                    if opciones['una_vez']:
                        raise CommandError('No se pudo revisar el uso de equipos; verifica la conexión y las migraciones.') from error
                    self.stderr.write('No se pudo revisar el uso de equipos; se reintentará en el próximo intervalo.')
                    time.sleep(intervalo)
                    continue
                if resultado.get('politica_pendiente'):
                    self.stdout.write('Sin política de uso configurada: no se abren alertas institucionales.')
                else:
                    self.stdout.write(f"{resultado['revisados']} equipos revisados; {resultado['nuevas']} alertas nuevas; {resultado['cerradas']} cerradas.")
                if opciones['una_vez']:
                    break
                time.sleep(intervalo)
        except KeyboardInterrupt:
            self.stdout.write('Monitor de uso detenido.')
        finally:
            close_old_connections()
