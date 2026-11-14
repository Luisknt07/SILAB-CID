"""Elimina las figuras cargadas desde el editor visual que nunca se asociaron a una guía.

Una imagen se sube antes de guardar la solicitud (``borrador_token``); si la
persona abandona el asistente, el archivo queda huérfano. Se conservan las
recientes por si el borrador sigue abierto.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.reservas.models.reservas import ImagenGuiaActividad


class Command(BaseCommand):
    help = 'Borra las figuras de guía en borrador que superan la antigüedad indicada (horas).'

    def add_arguments(self, parser):
        parser.add_argument('--horas', type=int, default=48, help='Antigüedad mínima para borrar (por defecto 48).')

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=max(1, options['horas']))
        huerfanas = ImagenGuiaActividad.objects.filter(guia__isnull=True, creado_en__lt=limite)
        total = 0
        for identificador in huerfanas.values_list('pk', flat=True).iterator(chunk_size=200):
            with transaction.atomic():
                # Una figura puede haberse asociado mientras se recorrían los candidatos.
                imagen = huerfanas.select_for_update().filter(pk=identificador).first()
                if imagen is None:
                    continue
                nombre, almacen = imagen.imagen.name, imagen.imagen.storage
                imagen.delete()
                if nombre:
                    transaction.on_commit(lambda ruta=nombre, storage=almacen: storage.delete(ruta), robust=True)
                total += 1
        self.stdout.write(self.style.SUCCESS(f'Figuras huérfanas eliminadas: {total}'))
