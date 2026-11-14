"""Carga en cada familia de producto sus componentes, sus modos de uso y el sistema con el que funciona.

Son datos de referencia de la familia (fichas_area/componentes_familias): la ficha técnica de cada modelo los
muestra mientras el modelo no registre los suyos, y suma a sus accesorios propios los de la familia que no
tenga. Es idempotente: vuelve a escribir los datos de referencia de cada familia, nunca los del modelo.

    python manage.py cargar_componentes_familias [--simular]
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.management.fichas_area.componentes_familias import COMPONENTES
from apps.recursos.models.equipos import FamiliaEquipo


def normalizar(entrada):
    """Las tuplas del archivo de datos como diccionarios, que es como se guardan."""
    return {
        'componentes': [{'tipo': tipo, 'cantidad': cantidad, 'nombre': nombre, 'uso': uso}
                        for tipo, cantidad, nombre, uso in entrada.get('componentes', [])],
        'modos': [dict(modo) for modo in entrada.get('modos', [])],
        'sistema': entrada.get('sistema', ''),
    }


class Command(BaseCommand):
    help = 'Carga los componentes, modos de uso y sistema de referencia de cada familia de equipos.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        familias = {familia.nombre: familia for familia in FamiliaEquipo.objects.all()}
        actualizadas, sin_datos = 0, [nombre for nombre in familias if nombre not in COMPONENTES]
        desconocidas = [nombre for nombre in COMPONENTES if nombre not in familias]
        with transaction.atomic():
            for nombre, entrada in COMPONENTES.items():
                familia = familias.get(nombre)
                if familia is None:
                    continue
                datos = normalizar(entrada)
                if (familia.componentes, familia.modos_uso, familia.sistema) != (datos['componentes'], datos['modos'], datos['sistema']):
                    familia.componentes, familia.modos_uso, familia.sistema = datos['componentes'], datos['modos'], datos['sistema']
                    if not opciones['simular']:
                        familia.save(update_fields=['componentes', 'modos_uso', 'sistema'])
                    actualizadas += 1
        prefijo = 'Simulación: ' if opciones['simular'] else ''
        self.stdout.write(f'{prefijo}{actualizadas} familias actualizadas; {len(sin_datos)} sin datos de referencia; '
                          f'{len(desconocidas)} nombres de los datos sin familia en la base.')
        for nombre in desconocidas[:20]:
            self.stdout.write(f'  Sin familia: {nombre}')
