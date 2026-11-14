"""Revisa el uso de todos los equipos y abre o cierra las alertas de equipos sin uso.

Pensado para una tarea programada (por ejemplo, cada lunes). Es idempotente: no duplica alertas vigentes.

    python manage.py detectar_equipos_sin_uso [--simular]
"""
from django.core.management.base import BaseCommand

from apps.recursos.presentation.traspasos import detectar_equipos_sin_uso


class Command(BaseCommand):
    help = 'Revisa equipos y cierres reales, conserva la evidencia y actualiza alertas sin ejecutar traspasos.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        resultado = detectar_equipos_sin_uso(simular=opciones['simular'])
        prefijo = 'Simulación: ' if opciones['simular'] else ''
        if resultado.get('politica_pendiente'):
            self.stdout.write(f'{prefijo}sin política de uso configurada; no se abren alertas institucionales.')
            return
        self.stdout.write(f"{prefijo}{resultado['revisados']} equipos revisados, {resultado['nuevas']} alertas nuevas, "
                          f"{resultado['cerradas']} cerradas porque volvieron a usarse.")
