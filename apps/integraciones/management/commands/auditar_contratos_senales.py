"""Entrada de compatibilidad para revision de contratos heredados."""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.integraciones.auditoria_senales import auditar_contratos_senales


class Command(BaseCommand):
    help = 'Contrasta contratos de señales con codigo y conexiones sin SQL o ejecutar receivers.'

    def add_arguments(self, parser):
        parser.add_argument('--resumen', action='store_true')
        parser.add_argument('--estricto', action='store_true', help='Salida no cero si falta revisar codigo o conexiones.')

    def handle(self, *args, **options):
        try:
            datos = auditar_contratos_senales()
        except (ValueError, OSError, UnicodeError, LookupError):
            raise CommandError('No se pudo revisar contratos; verifica codigo y adaptador de dispatcher.') from None
        salida = {k: datos[k] for k in ('version_contrato', 'alcance', 'resumen')} if options['resumen'] else datos
        self.stdout.write(json.dumps(salida, ensure_ascii=False, indent=2))
        if options['estricto'] and datos['hallazgos']:
            raise CommandError('Hay contratos, codigo o conexiones pendientes de revision.')
