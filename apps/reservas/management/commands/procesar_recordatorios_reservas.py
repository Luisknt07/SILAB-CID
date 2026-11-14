from django.core.management.base import BaseCommand, CommandError
from apps.reservas.presentation.notificaciones import procesar_recordatorios_reservas
from apps.directorio_unidades.models.core import Unidad


class Command(BaseCommand):
    help = (
        'Procesa vencimientos, recordatorios, cierres pendientes, asignación y '
        'riesgos operativos de reservas.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-correo',
            action='store_true',
            help='Procesa estados y avisos internos, pero no intenta entregar correos.',
        )
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Calcula el resultado sin guardar cambios ni enviar correos.',
        )
        parser.add_argument(
            '--unidad',
            help='Slug de una unidad; si se omite se procesa el conjunto institucional.',
        )

    def handle(self, *args, **options):
        slug = (options.get('unidad') or '').strip()
        unidad = None
        if slug:
            unidad = Unidad.objects.filter(slug=slug).first()
            if unidad is None:
                raise CommandError(f'No existe una unidad con slug "{slug}".')
        if options['simular']:
            resultados = procesar_recordatorios_reservas(
                enviar_email=False,
                unidad=unidad,
                simular=True,
            )
            prefijo = 'SIMULACIÓN (sin cambios): '
        else:
            resultados = procesar_recordatorios_reservas(
                enviar_email=not options['sin_correo'],
                unidad=unidad,
            )
            prefijo = ''
        detalle = ', '.join(f'{clave}: {valor}' for clave, valor in resultados.items())
        self.stdout.write(self.style.SUCCESS(f'{prefijo}{detalle}'))
