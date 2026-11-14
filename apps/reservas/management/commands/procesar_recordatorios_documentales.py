from django.core.management.base import BaseCommand

from apps.documentos.presentation.avisos_documentales import preparar_avisos, enviar_pendientes
from apps.documentos.presentation.incumplimiento_documental import evaluar_vencimientos


class Command(BaseCommand):
    help = 'Evalúa no entregas vencidas, crea recordatorios de 7 días y 24 horas y envía avisos pendientes.'

    def add_arguments(self, parser):
        parser.add_argument('--solo-sistema', action='store_true')
        parser.add_argument('--anio', type=int)

    def handle(self, *args, **options):
        from django.utils import timezone
        from apps.documentos.presentation.cumplimiento import unidades_auditadas
        from apps.documentos.presentation.expediente import construir_expediente
        anio = options['anio'] or timezone.localdate().year
        for unidad in unidades_auditadas():
            construir_expediente(unidad, anio)
        evaluados = evaluar_vencimientos()
        cantidad = preparar_avisos()
        if not options['solo_sistema']:
            enviar_pendientes()
        self.stdout.write(f'Avisos internos creados: {cantidad}.')
        self.stdout.write(f'Evaluaciones automáticas por no entrega: {evaluados}.')
