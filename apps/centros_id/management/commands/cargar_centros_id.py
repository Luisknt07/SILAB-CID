"""Carga el catálogo de tres centros con áreas, servicios y articulación interdisciplinaria."""
from django.core.management.base import BaseCommand, CommandError

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import CONTENIDOS


class Command(BaseCommand):
    help = 'Carga los Centros I+D con su organización, áreas, servicios, indicadores, riesgos, articulación y documentos.'

    def add_arguments(self, parser):
        parser.add_argument('--centro', choices=sorted(CONTENIDOS), help='Solo este centro.')
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument('--reescribir', action='store_true', help='Reemplaza los textos con los del archivo.')
        modo.add_argument('--conservar-existentes', action='store_true',
                          help='Crea solo registros faltantes; conserva también campos vacíos y archivos existentes.')
        parser.add_argument('--medios', action='store_true',
                            help='Copia las imágenes del centro y genera sus documentos en PDF.')
        parser.add_argument('--muestra', action='store_true',
                            help='Suma el contenido representativo del centro operando, para que el centro lo valide.')

    def handle(self, *args, **options):
        if options['reescribir'] and options['conservar_existentes']:
            raise CommandError('Conservar existentes y reescribir son modos excluyentes.')
        slugs = [options['centro']] if options['centro'] else sorted(CONTENIDOS)
        if not slugs:
            raise CommandError('No hay contenidos de Centros I+D registrados.')
        for slug in slugs:
            cargador = Cargador(CONTENIDOS[slug], reescribir=options['reescribir'], medios=options['medios'],
                                muestra=options['muestra'], conservar_existentes=options['conservar_existentes'])
            centro = cargador.cargar()
            self.stdout.write(self.style.SUCCESS(f'{centro}: {cargador.resumen()}.'))
