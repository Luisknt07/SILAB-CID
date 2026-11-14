"""Carga las asignaturas de grado que se practican en cada laboratorio, con su carrera, su nivel y el área donde se
practican, desde las mallas curriculares oficiales (ver `apps/laboratorios/operacion/management/laboratorios/asignaturas.py`).

Es idempotente: cada asignatura se encuentra por su código dentro de la unidad, y una que la unidad haya editado o
desactivado se respeta. `--simular` muestra lo que haría sin guardar nada.
"""
import hashlib
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.gestion_unidades.presentation.fusion_areas import area_vigente
from apps.integraciones.management.commands.reorganizar_unidades import LABORATORIOS
from apps.laboratorios.operacion.management.laboratorios.asignaturas import ASIGNATURAS, FUENTE, SIGLAS
from apps.formacion.models.asignaturas import Asignatura
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad

# El prefijo de los códigos de área de cada laboratorio, el mismo que usa la reforma.
PREFIJOS = {definicion['slug']: definicion['prefijo'] for definicion in LABORATORIOS}


class Simulacion(Exception):
    """Deshace la carga al final de una simulación."""


def codigo_de(carrera, nombre):
    """El código de la asignatura dentro de la unidad: la sigla de la carrera y el nombre abreviado; si no cabe, el
    nombre se acorta y se le suma una huella corta para que «… I» y «… II» no compartan código."""
    codigo = f'{SIGLAS[carrera]}-{slugify(nombre).upper()}'
    if len(codigo) <= 40:
        return codigo
    huella = hashlib.sha1(nombre.encode('utf-8')).hexdigest()[:6].upper()
    return f'{codigo[:33].rstrip("-")}-{huella}'


class Command(BaseCommand):
    help = 'Carga las asignaturas de grado que se practican en cada laboratorio.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', help='Slug de una unidad (se puede repetir).')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        unidades = Unidad.objects.filter(slug__in=ASIGNATURAS, activo=True).order_by('nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
        total = Counter()
        try:
            with transaction.atomic():
                for unidad in unidades:
                    resumen = self._cargar(unidad, ASIGNATURAS[unidad.slug])
                    total.update(resumen)
                    detalle = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in sorted(resumen.items()))
                    self.stdout.write(f'{unidad.nombre}: {detalle or "al día"}.')
                if opciones['simular']:
                    raise Simulacion
        except Simulacion:
            pass
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefijo}{total["creadas"]} asignaturas creadas y {total["actualizadas"]} actualizadas.'))

    @staticmethod
    def _cargar(unidad, filas):
        resumen = Counter()
        prefijo = PREFIJOS.get(unidad.slug, '')
        areas = {area.codigo: area_vigente(area) for area in EspacioReservable.objects.filter(unidad=unidad)}
        for carrera, nivel, nombre, sufijo in filas:
            area = areas.get(f'{prefijo}-{sufijo}')
            descripcion = (f'Se practica en el área «{area.nombre}». ' if area else '') + f'Fuente: {FUENTE}'
            asignatura, creada = Asignatura.objects.get_or_create(
                unidad=unidad, codigo=codigo_de(carrera, nombre),
                defaults={'nombre': nombre, 'carrera': carrera, 'semestre': nivel, 'descripcion': descripcion},
            )
            if creada:
                resumen['creadas'] += 1
                continue
            # Lo que la unidad corrigió se respeta; solo se completa lo que falte.
            cambios = {campo: valor for campo, valor in
                       (('carrera', carrera), ('semestre', nivel), ('descripcion', descripcion))
                       if valor and not getattr(asignatura, campo)}
            if cambios:
                Asignatura.objects.filter(pk=asignatura.pk).update(**cambios)
                resumen['actualizadas'] += 1
        return resumen
