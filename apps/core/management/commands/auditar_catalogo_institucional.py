"""Puerta de compatibilidad de catalogos, ejecutada con acceso administrativo local."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import DatabaseError

from apps.core.presentation.auditoria_catalogos import auditar_catalogo
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional
from apps.core.presentation.niveles_institucionales import con_niveles_institucionales


class Command(BaseCommand):
    help = "Audita codigos academicos y sus relaciones en perfiles, reservas y periodos sin cambiar datos."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", choices=tuple(settings.DATABASES))

    def handle(self, *args, **options):
        try:
            with con_catalogo_institucional(database=options['database'], estricto=True), con_niveles_institucionales(database=options['database'], estricto=True):
                resultados = auditar_catalogo(database=options["database"])
        except (DatabaseError, ValueError, ValidationError, TypeError):
            raise CommandError('Catalogo activo no disponible o invalido; revisa su publicacion y migracion.') from None
        self.stdout.write(json.dumps(resultados, ensure_ascii=False))
        total = sum(fila["codigos_desconocidos"] + fila["relaciones_incompatibles"] for fila in resultados)
        if total:
            raise CommandError("El catalogo no es compatible con todos los datos. Conserve los codigos o revise su relacion antes de cambiarlo.")
        self.stdout.write(self.style.SUCCESS(f"Catalogo compatible: {len(resultados)} campos revisados; ninguna escritura."))
