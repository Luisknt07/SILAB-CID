"""Comprueba adjuntos contra sus huellas guardadas, sin modificar información."""

import hashlib
import re

from django.core.management.base import BaseCommand, CommandError

from apps.reservas.models.reservas import GuiaActividadReserva
from apps.recursos.models.recursos import Recurso


class Command(BaseCommand):
    help = 'Verifica existencia, tamaño y SHA-256 de recursos y guías firmadas; no repara ni escribe.'

    def handle(self, *args, **options):
        verificados = fallos = sin_huella = 0

        def comprobar(identificador, archivo, esperado, tamano=None):
            nonlocal verificados, fallos, sin_huella
            try:
                digest = hashlib.sha256()
                total = 0
                with archivo.storage.open(archivo.name, 'rb') as stream:
                    for bloque in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(bloque)
                        total += len(bloque)
                if not esperado:
                    sin_huella += 1
                    self.stderr.write(f'{identificador}: sin huella completa verificable.')
                elif digest.hexdigest() != esperado or (tamano is not None and tamano != total):
                    fallos += 1
                    self.stderr.write(f'{identificador}: contenido o tamaño distinto al registrado.')
                else:
                    verificados += 1
            except (OSError, ValueError):
                fallos += 1
                self.stderr.write(f'{identificador}: archivo ausente o ilegible.')

        for recurso in Recurso.objects.exclude(archivo='').exclude(archivo__isnull=True).iterator():
            comprobar(f'Recurso {recurso.pk}', recurso.archivo, recurso.hash_sha256, recurso.tamano_bytes)
        for guia in GuiaActividadReserva.objects.exclude(archivo_firmado='').exclude(
                archivo_firmado__isnull=True).iterator():
            huella = re.search(r'SHA-256 ([0-9a-f]{64})\b', guia.firma_certificada_resumen)
            comprobar(f'Guía {guia.pk}', guia.archivo_firmado, huella.group(1) if huella else None)
        self.stdout.write(f'Verificados: {verificados}; fallos: {fallos}; sin huella: {sin_huella}.')
        if fallos or sin_huella:
            raise CommandError('La integridad documental no pudo verificarse completamente.')
