"""Completa los insumos con lo deducible y, si se pide, les da existencias y consumos demostrativos.

Sin opciones: unidad de medida y contenido por presentación deducidos de la presentación, niveles de reposición
básicos (4, 2 y 1 presentaciones) y plazo de reposición. Con --demostrativo, a los insumos sin movimientos les crea
un lote «DEMO-…» recibido hace 60 días y cuatro consumos trazables, para ver las gráficas y los niveles con datos;
algunos quedan por debajo del punto de reposición para ver las alertas. Es idempotente.

    python manage.py completar_inventario_de_referencia [--unidad SLUG] [--demostrativo] [--simular]
"""
import zlib
from datetime import time, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.recursos.presentation.inventario_referencia import completar
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible

DIAS_CONSUMO = (50, 35, 20, 7)
UNIDADES_CONTINUAS = {"g", "mL", "m"}


class Command(BaseCommand):
    help = 'Completa los insumos con lo deducible y, con --demostrativo, crea existencias y consumos de prueba.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', help='Slug de una sola unidad.')
        parser.add_argument('--demostrativo', action='store_true', help='Crea lotes y consumos demostrativos trazables.')
        parser.add_argument('--confirmar-datos-demo', action='store_true', help='Confirma la carga ficticia en la unidad indicada.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        if opciones['demostrativo']:
            if not getattr(settings, 'ALLOW_DEMO_DATA_COMMANDS', False):
                raise CommandError('Los datos demostrativos están deshabilitados en este entorno.')
            if not opciones['unidad'] or not opciones['confirmar_datos_demo']:
                raise CommandError('Indica --unidad y --confirmar-datos-demo para acotar y confirmar la carga ficticia.')
        consumibles = Consumible.objects.filter(activo=True, unidad__isnull=False).select_related('unidad')
        if opciones['unidad']:
            consumibles = consumibles.filter(unidad__slug=opciones['unidad'])
        completados = demostrativos = 0
        with transaction.atomic():
            for consumible in consumibles:
                cambiados = completar(consumible)
                if cambiados:
                    completados += 1
                    if not opciones['simular']:
                        consumible.save(update_fields=cambiados + ['fecha_actualizacion'])
                if (opciones['demostrativo'] and consumible.stock_total == 0
                        and not consumible.lotes_inventario.exists()
                        and not EntradaInventario.objects.filter(consumible=consumible).exists()):
                    demostrativos += 1
                    if not opciones['simular']:
                        self._demostrar(consumible)
            if opciones['simular']:
                transaction.set_rollback(True)
        prefijo = 'Simulación: ' if opciones['simular'] else ''
        self.stdout.write(f'{prefijo}{completados} insumos completados con lo deducible; '
                          f'{demostrativos} con existencias y consumos demostrativos.')

    @staticmethod
    def _demostrar(consumible):
        """Un lote recibido hace 60 días y cuatro consumos; uno de cada cinco queda bajo el punto de reposición."""
        semilla = zlib.crc32(consumible.codigo.encode())
        presentacion = Decimal(consumible.cantidad_por_presentacion or 1)
        presentaciones = Decimal(3 + semilla % 4)
        recibido = (presentacion * presentaciones).quantize(Decimal('0.001'))
        bajo = semilla % 5 == 0
        # Lo que se cuenta por piezas (unidades, rollos, frascos…) se consume en cantidades enteras.
        enteros = (consumible.unidad_medida or '') not in UNIDADES_CONTINUAS
        a_consumir = recibido - (presentacion * Decimal('0.5') if bajo else presentacion * Decimal('2.2'))
        a_consumir = max(Decimal('0'), a_consumir).quantize(Decimal('1') if enteros else Decimal('0.001'), ROUND_FLOOR)
        hoy = timezone.localdate()
        fecha = timezone.make_aware(timezone.datetime.combine(hoy - timedelta(days=60), time(9, 0)))
        codigo = f'DEMO-{consumible.codigo}-001'
        lote = LoteConsumible.objects.create(
            consumible=consumible, codigo=codigo, cantidad_inicial=recibido, cantidad_actual=Decimal('0'),
            bodega='Bodega de la unidad', estanteria='Estantería demostrativa', posicion='Nivel 1',
            fecha_ingreso=hoy - timedelta(days=60), costo_unitario=consumible.precio_unitario,
            documento_recepcion=f'ACTA-{codigo}', observaciones='Lote demostrativo para revisar niveles y consumo.')
        EntradaInventario.objects.create(
            consumible=consumible, unidad=consumible.unidad, tipo='ingreso', motivo='recepcion', cantidad=recibido,
            lote_inventario=lote, fecha=fecha, referencia=f'REC-{codigo}', nota='Recepción demostrativa.')
        if a_consumir <= 0:
            return
        partes = (Decimal('0.35'), Decimal('0.25'), Decimal('0.25'), Decimal('0.15'))
        restante = a_consumir
        for indice, (dias, parte) in enumerate(zip(DIAS_CONSUMO, partes), start=1):
            cantidad = restante if indice == len(partes) else (a_consumir * parte).quantize(
                Decimal('1') if enteros else Decimal('0.001'), ROUND_FLOOR if enteros else ROUND_HALF_UP)
            restante -= cantidad
            if cantidad <= 0:
                continue
            EntradaInventario.objects.create(
                consumible=consumible, unidad=consumible.unidad, tipo='salida', motivo='consumo_practica', cantidad=cantidad,
                lote_inventario=lote, fecha=timezone.make_aware(timezone.datetime.combine(hoy - timedelta(days=dias), time(15, 0))),
                referencia=f'DEMO-CONSUMO-{consumible.codigo}-{indice:02d}', nota='Consumo demostrativo en práctica.')
