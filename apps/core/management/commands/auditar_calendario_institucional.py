"""Puerta de compatibilidad antes de cambiar politica de calendario."""

import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.core.management.base import BaseCommand, CommandError

from apps.core.presentation.auditoria_calendario import auditar_calendario
from apps.core.presentation.calendario_institucional import con_calendario_institucional


class Command(BaseCommand):
    help = "Audita calendario y semanas con conteos, sin modificar datos."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", choices=tuple(settings.DATABASES))

    def handle(self, *args, **options):
        try:
            with con_calendario_institucional(database=options['database'], estricto=True):
                resultado = auditar_calendario(database=options["database"])
        except (DatabaseError, ValueError, ValidationError, TypeError):
            raise CommandError('No se pudo auditar la politica de calendario publicada; revisa su integridad.') from None
        self.stdout.write(json.dumps(resultado))
        if any(valor for clave, valor in resultado.items() if clave not in {"periodos", "semanas"}):
            raise CommandError("Calendario incompatible: conserve codigos y limites o concilie los datos antes del cambio.")
        self.stdout.write(self.style.SUCCESS("Calendario compatible; ninguna escritura."))
