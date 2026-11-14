"""Control periódico de las cuatro tipologías; nombre conservado por compatibilidad."""
from collections import Counter
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min, F, Q
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.automatizacion_documental import procesar_expediente
from apps.documentos.presentation.expediente import cortes_del_anio, del_periodo, leer_expediente, periodo_vigente
from apps.documentos.presentation.perfil_unidades import es_unidad_auditable


class Command(BaseCommand):
    help = 'Detecta incidencias y valida casos objetivos por tipo de unidad. Sin --aplicar, no guarda cambios.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', help='Slug de una unidad; omitido procesa lotes de las cuatro tipologías.')
        parser.add_argument('--anio', type=int, default=timezone.localdate().year)
        parser.add_argument('--corte', choices=('A', 'B', 'todos'))
        parser.add_argument('--limite', type=int, default=25, help='Máximo de unidades por ejecución (1 a 500).')
        parser.add_argument('--aplicar', action='store_true', help='Guarda controles y aplica únicamente conformidades objetivas.')
        parser.add_argument('--solo-diagnostico', action='store_true', help='Guarda hallazgos sin aprobar ni recibir documentos.')

    def handle(self, *args, **options):
        anio, limite = options['anio'], options['limite']
        if not 2000 <= anio <= 2200 or not 1 <= limite <= 500:
            raise CommandError('Año o límite fuera del rango permitido.')
        if options['aplicar'] and options['solo_diagnostico']:
            raise CommandError('Elige --aplicar o --solo-diagnostico.')
        cortes = cortes_del_anio(anio)
        corte = options['corte'] or periodo_vigente(cortes, timezone.localdate())
        alcance = Q(expediente__anio=anio)
        if corte != 'todos':
            alcance &= Q(expediente__corte__in=('', corte))
        consulta = Unidad.objects.filter(expediente__anio=anio).distinct().annotate(
            ultimo_control=Min('expediente__control_automatico__comprobado_en', filter=alcance)).order_by(
                F('ultimo_control').asc(nulls_first=True), 'pk')
        if options['unidad']:
            consulta = consulta.filter(slug=options['unidad'])
        unidades = [u for u in consulta if es_unidad_auditable(u)][:limite]
        if options['unidad'] and not unidades:
            raise CommandError('No hay una unidad compatible con expediente materializado para ese año.')
        contadores, errores = Counter(), []
        for unidad in unidades:
            try:
                with transaction.atomic():
                    documentos = leer_expediente(unidad, anio)
                    if corte != 'todos':
                        documentos = del_periodo(documentos, corte, cortes)
                    controles = procesar_expediente(documentos, aplicar=options['aplicar'])
                    contadores.update(c.estado for c in controles if c)
                    contadores['aplicados'] += sum(bool(c and c.aplicado) for c in controles)
                    if not (options['aplicar'] or options['solo_diagnostico']):
                        transaction.set_rollback(True)
            except Exception as error:
                errores.append((unidad.slug, type(error).__name__))
                self.stderr.write(f'{unidad.slug}: control no completado ({type(error).__name__}). No se aplicaron cambios parciales.')
        self.stdout.write(f'{datetime.now():%Y-%m-%d %H:%M} · {len(unidades)} unidades · '
            + ('aplicado' if options['aplicar'] else 'diagnóstico guardado' if options['solo_diagnostico'] else 'simulación sin cambios')
            + f' · {dict(contadores)}')
        if errores:
            raise CommandError(f'{len(errores)} unidades requieren corregir el error técnico antes de reintentarlo.')
