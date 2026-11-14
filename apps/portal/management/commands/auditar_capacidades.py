"""Diagnostico local sin datos de usuarios ni permisos concedidos."""
from dataclasses import asdict
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from config.capacidades import controles_de_despliegue


class Command(BaseCommand):
    help = 'Muestra controles de capacidades implementadas; no cambia datos ni concede permisos.'

    def handle(self, *args, **options):
        try:
            controles = controles_de_despliegue(getattr(settings, 'CAPABILITY_CONTROLS', {}))
        except ValueError:
            raise CommandError('La politica de capacidades no es valida.') from None
        self.stdout.write(json.dumps({
            'version_esquema': 1, 'no_concede_permisos': True,
            'controles': {clave: asdict(control) for clave, control in controles.items()},
        }, ensure_ascii=False, indent=2))
