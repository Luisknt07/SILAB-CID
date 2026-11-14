"""Habilitación explícita e idempotente, sin abrir áreas ni cambiar requisitos."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad


class Command(BaseCommand):
    help = 'Habilita solicitudes de visita en laboratorios, centros experimentales y plantas piloto.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Sin este argumento solo muestra el plan.')
        parser.add_argument('--respaldo', type=Path, help='Archivo JSON nuevo para conservar la configuración previa.')

    @transaction.atomic
    def handle(self, *args, **options):
        unidades = [u for u in Unidad.objects.filter(activo=True).order_by('pk')
                    if u.codigo_base in {'laboratorios', 'centro_experimental', 'plantas_piloto'}]
        anteriores = list(ConfiguracionOperativaUnidad.objects.select_for_update().filter(
            unidad__in=unidades,
        ).values('unidad_id', 'acepta_visitas'))
        por_unidad = {c['unidad_id']: c['acepta_visitas'] for c in anteriores}
        pendientes = [u for u in unidades if not por_unidad.get(u.pk, False)]
        self.stdout.write(f'Unidades: {len(unidades)}; por habilitar: {len(pendientes)}.')
        if not options['aplicar'] or not pendientes:
            return
        respaldo = options['respaldo'] or (
            Path(settings.BASE_DIR) / 'var' / 'backups' / 'visitas' /
            f'configuracion-{timezone.now():%Y%m%d-%H%M%S-%f}.json'
        )
        respaldo.parent.mkdir(parents=True, exist_ok=True)
        with respaldo.open('x', encoding='utf-8') as archivo:
            json.dump({'configuraciones': anteriores,
                       'sin_configuracion': [u.pk for u in unidades if u.pk not in por_unidad]}, archivo, indent=2)
        for unidad in pendientes:
            configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=unidad)
            configuracion.acepta_visitas = True
            configuracion.save(update_fields=['acepta_visitas'])
        self.stdout.write(self.style.SUCCESS(f'Habilitadas: {len(pendientes)}. Respaldo: {respaldo}'))
