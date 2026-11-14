"""Diagnostica diferencias y restaura solo contadores demostrablemente obsoletos."""
import json
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import F, Sum

from apps.recursos.models.consumibles import Consumible
from apps.recursos.presentation.conciliacion import conciliar_saldo


class Command(BaseCommand):
    help = 'Contrasta stock, lotes y kardex. Por defecto no cambia datos; --aplicar exige respaldo previo.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true')
        parser.add_argument('--articulos', nargs='+', type=int)

    def handle(self, *args, **options):
        articulos = Consumible.objects.filter(lotes_inventario__isnull=False).annotate(
            total_lotes=Sum('lotes_inventario__cantidad_actual')).exclude(stock_total=F('total_lotes'))
        if options['articulos']:
            articulos = articulos.filter(pk__in=options['articulos'])
        estados = Counter(conciliar_saldo(pk, aplicar=options['aplicar'])['estado']
                          for pk in articulos.order_by('pk').values_list('pk', flat=True))
        self.stdout.write(json.dumps({'aplicado': options['aplicar'], 'resultados': dict(estados)}, ensure_ascii=False))
