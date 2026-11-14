"""Completa el escenario operativo local, preservando las ediciones existentes."""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.centros_id.escenario_operativo import construir_escenario
from apps.centros_id.models import CentroID


class Command(BaseCommand):
    help = 'Construye contenido operativo representativo del CIDT en desarrollo local.'

    def add_arguments(self, parser):
        parser.add_argument('--centro', default='cidt-upec')

    def handle(self, *args, **options):
        try:
            centro = CentroID.objects.get(slug=options['centro'])
            resumen = construir_escenario(centro)
        except (CentroID.DoesNotExist, ValidationError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(resumen))
