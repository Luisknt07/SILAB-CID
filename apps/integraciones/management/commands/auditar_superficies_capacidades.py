"""Entrada de compatibilidad para la auditoria del adaptador de integraciones."""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.integraciones.superficies import inventario_superficies


class Command(BaseCommand):
    help = 'Inventaria superficies de capacidades sin SQL ni ejecutar operaciones; no certifica permisos.'

    def add_arguments(self, parser):
        parser.add_argument('--modulo', action='append', help='Modulo registrado; repetible. Las superficies compartidas se conservan.')
        parser.add_argument('--resumen', action='store_true', help='Muestra solo alcance, seleccion y cantidades.')

    def handle(self, *args, **options):
        try:
            datos = inventario_superficies(options.get('modulo'))
        except (ValueError, OSError, UnicodeError):
            raise CommandError('No se pudo inventariar el codigo; revisa seleccion y archivos del proyecto.') from None
        if options.get('resumen'):
            datos = {clave: datos[clave] for clave in ('version_inventario', 'alcance', 'no_concede_permisos',
                                                     'no_consulta_datos', 'seleccion_modulos', 'resumen')}
        self.stdout.write(json.dumps(datos, ensure_ascii=False, indent=2))
