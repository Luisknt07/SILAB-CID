from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models.limites import ContadorPeticion


class Command(BaseCommand):
    help = 'Elimina contadores de abuso vencidos; no contiene ni modifica datos de usuarios.'

    def handle(self, *args, **options):
        total, _ = ContadorPeticion.objects.filter(vence__lt=timezone.now()).delete()
        self.stdout.write(f'{total} contadores vencidos eliminados.')
