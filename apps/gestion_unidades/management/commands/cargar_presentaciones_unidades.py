"""Carga «Conoce la unidad» de cada unidad: su presentación, sus líneas de acción y sus hitos.

Los textos están en fichas_area/presentaciones_unidades.py, escritos a partir de lo que cada unidad tiene
registrado (áreas, equipos, software, carreras, fechas), sin nombres de personas ni cifras inventadas. La
presentación se publica. Lo que la unidad ya escribió no se pisa: solo se crea lo que falta, campo por campo;
--reescribir reemplaza los textos cargados por esta orden. --simular muestra lo que haría.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.management.fichas_area.presentaciones_unidades import PRESENTACIONES
from apps.gestion_unidades.models.presentacion import HitoUnidad, LineaAccionUnidad, PresentacionUnidad
from apps.directorio_unidades.models.core import Unidad

CAMPOS_TEXTO = ('lema', 'que_es', 'que_hace', 'capacidades', 'areas_trabajo', 'historia', 'mision', 'vision')
CAMPOS_LISTA = ('objetivos', 'beneficiarios', 'resultados')


class Simulacion(Exception):
    """Deshace todo al final de una simulación."""


class Command(BaseCommand):
    help = 'Carga la presentación («Conoce la unidad»), las líneas de acción y los hitos de cada unidad.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', help='Slug de la unidad; se puede repetir.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')
        parser.add_argument('--reescribir', action='store_true', help='Reemplaza los textos aunque la unidad ya tenga.')

    def handle(self, *args, **opciones):
        unidades = Unidad.objects.filter(slug__in=PRESENTACIONES).order_by('nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
        resumen = Counter()
        try:
            with transaction.atomic():
                for unidad in unidades:
                    self._cargar(unidad, PRESENTACIONES[unidad.slug], opciones['reescribir'], resumen)
                if opciones['simular']:
                    raise Simulacion
        except Simulacion:
            pass
        faltan = set(PRESENTACIONES) - set(Unidad.objects.filter(slug__in=PRESENTACIONES).values_list('slug', flat=True))
        if faltan:
            resumen['unidades del archivo que no existen'] = len(faltan)
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(prefijo + (', '.join(f'{v} {k}' for k, v in sorted(resumen.items())) or 'nada que hacer')))

    @staticmethod
    def _cargar(unidad, datos, reescribir, resumen):
        presentacion, creada = PresentacionUnidad.objects.get_or_create(unidad=unidad)
        cambios = []
        for campo in CAMPOS_TEXTO + CAMPOS_LISTA:
            valor = datos.get(campo, '')
            if isinstance(valor, (list, tuple)):
                valor = '\n'.join(str(linea).strip() for linea in valor if str(linea).strip())
            valor = (valor or '').strip()
            if valor and (reescribir or not getattr(presentacion, campo).strip()):
                setattr(presentacion, campo, valor)
                cambios.append(campo)
        if not presentacion.publicada:
            presentacion.publicada = True
            cambios.append('publicada')
        if cambios:
            presentacion.save()
            resumen['presentaciones creadas' if creada else 'presentaciones completadas'] += 1
        if datos.get('lineas') and (reescribir or not unidad.lineas_accion.exists()):
            unidad.lineas_accion.all().delete()
            for orden, (titulo, icono, descripcion) in enumerate(datos['lineas'], start=1):
                LineaAccionUnidad.objects.create(unidad=unidad, titulo=str(titulo)[:80], icono=icono,
                                                 descripcion=str(descripcion)[:200], orden=orden)
            resumen['líneas de acción'] += len(datos['lineas'])
        if datos.get('hitos') and (reescribir or not unidad.hitos.exists()):
            unidad.hitos.all().delete()
            for hito in datos['hitos']:
                if not isinstance(hito, dict):
                    hito = dict(zip(('anio', 'titulo', 'descripcion'), hito))
                HitoUnidad.objects.create(
                    unidad=unidad, anio=int(hito['anio']), mes=hito.get('mes') or None, tipo=hito.get('tipo') or 'hito',
                    titulo=str(hito['titulo'])[:120], descripcion=str(hito.get('descripcion') or '')[:255],
                    enlace=str(hito.get('enlace') or '')[:500])
            resumen['hitos'] += len(datos['hitos'])
