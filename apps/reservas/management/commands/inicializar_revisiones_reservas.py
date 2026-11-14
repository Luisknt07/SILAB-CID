from django.core.management.base import BaseCommand, CommandError

from apps.reservas.presentation.mantenimiento import inicializar_revisiones_unidad
from apps.reservas.presentation.capacidad import comando_reservas
from apps.directorio_unidades.models.core import Unidad


class Command(BaseCommand):
    help = (
        'Crea una línea base inmutable para las reservas existentes que todavía '
        'no tienen historial de versiones.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--unidad',
            help='Slug obligatorio de la unidad que se reconciliará.',
        )
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Informa cuántas versiones crearía sin guardar cambios.',
        )

    @comando_reservas
    def handle(self, *args, **options):
        slug = (options.get('unidad') or '').strip()
        if not slug:
            raise CommandError('Indica --unidad para acotar la reconciliación.')
        try:
            resultado = inicializar_revisiones_unidad(
                unidad_slug=slug,
                simular=options['simular'],
            )
        except Unidad.DoesNotExist as error:
            raise CommandError(f'No existe una unidad con slug "{slug}".') from error

        prefijo = 'SIMULACIÓN: ' if options['simular'] else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefijo}{resultado.creadas} reserva(s) con línea base generada.'
            )
        )
