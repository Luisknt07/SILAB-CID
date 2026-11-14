"""Metadatos del despliegue sin leer filas, adjuntos, credenciales o settings."""
from dataclasses import asdict
import json

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from config.modulos import registro_de_despliegue


class Command(BaseCommand):
    help = 'Audita manifiestos y dependencias declaradas; no habilita ni autoriza modulos.'

    def add_arguments(self, parser):
        parser.add_argument('--modulo', action='append', help='Plan de dependencias; se puede repetir.')

    def handle(self, *args, **options):
        try:
            registro = registro_de_despliegue()
            registro.validar_apps({config.name for config in apps.get_app_configs()})
            plan = registro.plan(options['modulo'] or tuple(registro.manifiestos))
        except ValueError as error:
            raise CommandError(str(error)) from None
        self.stdout.write(json.dumps({
            'version_esquema': 1,
            'alcance': 'metadatos_de_despliegue_no_autorizacion',
            'plan_dependencias': plan,
            'modulos': [asdict(registro.manifiestos[i]) for i in plan],
        }, ensure_ascii=False, indent=2))
