"""Crea propuestas editoriales sin sustituir contenidos ni abrir convocatorias.

--simular solo consulta y valida: no inserta filas para luego revertirlas, no
consume secuencias y no genera archivos. La carga real crea exclusivamente
fichas Curso; nunca ediciones, participantes, lecciones o medios de pago.
"""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.presentation.codigos_sistema import sigla_de_unidad
from apps.formacion.management.cursos_precargados.ejemplos_formacion import UNIDAD_PREDETERMINADA, propuestas_para
from apps.formacion.management.cursos_precargados.identidad import cursos_por_nombres, nombre_normalizado
from apps.formacion.models.cursos import Curso
from apps.directorio_unidades.models.core import Unidad


def codigo_ejemplo(unidad, numero, sigla):
    """El PK separa unidades que comparten sigla; el número identifica la propuesta."""
    return f'{sigla[:5]}-{unidad.pk}-EJ-FOR-{numero:02d}'


class Command(BaseCommand):
    help = 'Crea siete propuestas de cursos y eventos como borradores editables, sin convocatorias.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', default=UNIDAD_PREDETERMINADA,
                            help='Slug de la unidad que revisará y administrará las propuestas.')
        parser.add_argument('--simular', action='store_true',
                            help='Muestra las propuestas sin escribir en la base ni crear archivos.')

    def handle(self, *args, **opciones):
        slug = opciones['unidad']
        if opciones['simular']:
            unidad = self._unidad(slug)
            creados, conservados = self._cargar(unidad, simular=True)
            self.stdout.write(self.style.WARNING(
                f'Simulación: se crearían {creados} borradores y se conservarían {conservados} fichas. '
                'No se guardó nada ni se generaron archivos.'
            ))
            return
        with transaction.atomic():
            # Dos ejecuciones del comando para la misma unidad no compiten por
            # fichas con nombres iguales o por un prefijo institucional cambiado.
            unidad = self._unidad(slug, bloquear=True)
            creados, conservados = self._cargar(unidad)
        self.stdout.write(self.style.SUCCESS(
            f'{unidad.nombre}: {creados} borradores creados; {conservados} fichas conservadas sin cambios. '
            'Revisa las propuestas antes de publicarlas; no se crearon convocatorias ni inscripciones.'
        ))

    @staticmethod
    def _unidad(slug, bloquear=False):
        consulta = Unidad.objects.select_for_update() if bloquear else Unidad.objects.all()
        try:
            return consulta.get(slug=slug)
        except Unidad.DoesNotExist as error:
            raise CommandError(f'No existe la unidad «{slug}».') from error

    def _cargar(self, unidad, simular=False):
        creados = conservados = 0
        sigla = sigla_de_unidad(unidad)
        propuestas = propuestas_para(unidad)
        por_nombre = cursos_por_nombres(unidad, [p['nombre'] for p in propuestas])
        for propuesta in propuestas:
            datos = {**propuesta}
            numero = datos.pop('numero')
            codigo = codigo_ejemplo(unidad, numero, sigla)
            # El sufijo conserva la identidad aunque cambien la sigla o el
            # nombre de una ficha; un nombre previo también impide duplicarla.
            identidad = f'-{unidad.pk}-EJ-FOR-{numero:02d}'
            existente = (Curso.objects.filter(unidad=unidad, codigo__endswith=identidad)
                         .order_by('pk').first())
            if existente is None:
                pk = por_nombre.get(nombre_normalizado(datos['nombre']))
                existente = Curso.objects.filter(unidad=unidad, pk=pk).first() if pk else None
            if existente is not None:
                conservados += 1
                self.stdout.write(f'Conservar: {existente.codigo} · {existente.nombre}')
                continue
            candidato = Curso(unidad=unidad, codigo=codigo, orden=100 + numero, **datos)
            try:
                candidato.full_clean()
            except ValidationError as error:
                raise CommandError(f'No se pudo validar la propuesta «{datos["nombre"]}»: {error}') from error
            if simular:
                creados += 1
                self.stdout.write(f'Crear borrador: {codigo} · {datos["nombre"]}')
                continue
            curso, nuevo = Curso.objects.get_or_create(
                codigo=codigo, defaults={'unidad': unidad, 'orden': 100 + numero, **datos})
            if curso.unidad_id != unidad.pk:
                raise CommandError(f'El código «{codigo}» ya pertenece a otra unidad; no se modificó esa ficha.')
            creados += int(nuevo)
            conservados += int(not nuevo)
            accion = 'Crear borrador' if nuevo else 'Conservar'
            self.stdout.write(f'{accion}: {curso.codigo} · {curso.nombre}')
        return creados, conservados
