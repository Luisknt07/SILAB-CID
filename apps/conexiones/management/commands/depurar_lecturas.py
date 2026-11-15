"""Elimina las lecturas que superaron los días de conservación de su canal."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.conexiones.models import CanalMedicion, LecturaCanal


class Command(BaseCommand):
    help = 'Depura las lecturas más antiguas que la retención definida en cada canal.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Cuenta lo que se eliminaría, sin borrar.')

    def handle(self, *args, **options):
        ahora = timezone.now()
        total = 0
        for canal_id, dias in CanalMedicion.objects.values_list('pk', 'retencion_dias'):
            vencidas = LecturaCanal.objects.filter(canal_id=canal_id, instante__lt=ahora - timedelta(days=dias))
            total += vencidas.count() if options['simular'] else vencidas.delete()[0]
        verbo = 'Se eliminarían' if options['simular'] else 'Eliminadas'
        self.stdout.write(f'{verbo} {total} lecturas fuera de su periodo de conservación.')
