"""Corridas demostrativas de las plantas piloto: validan el flujo completo sin tocar la operación real.

Por cada proceso de referencia crea una corrida marcada demostrativa, rotando los
ámbitos (académico, investigación y producción real): la planifica, la cierra con
las cantidades de la receta y un rendimiento variable, controla el lote con su
especificación (una de cada cinco sale no conforme para ejercitar la no
conformidad) y registra su despacho. Nada de esto descuenta inventario, genera
ingresos, bloquea la agenda ni entra en los indicadores. Deja además una corrida
demostrativa planificada por planta. Se puede repetir sin duplicar, y
``--limpiar`` borra lo demostrativo antes de crearlo de nuevo.
"""
import math
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.plantas_piloto.operacion.presentation.calidad import plan_para_lote_producto, registrar_control
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion, Receta
from apps.plantas_piloto.operacion.models.erp import SesionERP
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.management.datos_demo import exigir_entorno_datos_demo
from apps.recursos.models.unidades import UnidadEquipo

AMBITOS = ('practica', 'investigacion', 'propia')
RENDIMIENTOS = (Decimal('0.97'), Decimal('1.00'), Decimal('0.94'), Decimal('1.02'), Decimal('0.96'))
MARCA = '[DEMO]'
CUENTA = 'sistema.demostrativo'
MIL = Decimal('0.001')


def _valor(parametro, fuera=False):
    """Un valor de ejemplo dentro del límite del parámetro, o fuera si se pide."""
    if parametro.tipo == 'cualitativo':
        return 'no conforme' if fuera else (parametro.valor_esperado or 'conforme')
    minimo, maximo = parametro.minimo, parametro.maximo
    if fuera:
        if maximo is not None:
            return str(maximo + max(abs(maximo) * Decimal('0.1'), Decimal('1')))
        return str(minimo - max(abs(minimo) * Decimal('0.1'), Decimal('1')))
    if minimo is not None and maximo is not None:
        return str((minimo + maximo) / 2)
    if maximo is not None:
        return str(maximo * Decimal('0.8') if maximo > 0 else maximo - 2)
    if minimo is not None:
        return str(minimo * Decimal('1.1') if minimo > 0 else minimo + 1)
    return '0'


def _cantidad(valor, producto):
    paso = Decimal('1') if producto.unidad_medida == 'unidad' else MIL
    return Decimal(valor).quantize(paso, rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = 'Crea corridas demostrativas completas en las plantas piloto, sin tocar la operación real.'

    def add_arguments(self, parser):
        parser.add_argument('--planta', help='Slug de una planta; sin él, las cinco.')
        parser.add_argument('--limpiar', action='store_true', help='Borra lo demostrativo antes de crearlo.')

    def handle(self, *args, **options):
        exigir_entorno_datos_demo()
        plantas = Unidad.objects.filter(dependencia='plantas_piloto').order_by('slug')
        if options['planta']:
            plantas = plantas.filter(slug=options['planta'])
            if not plantas.exists():
                raise CommandError(f'No existe la planta {options["planta"]}.')
        usuario = self._cuenta()
        for unidad in plantas:
            with transaction.atomic():
                if options['limpiar']:
                    self._limpiar(unidad)
                creadas = self._corridas(unidad, usuario)
            self.stdout.write(f'{unidad.nombre}: {creadas} corridas demostrativas nuevas.')

    def _cuenta(self):
        """Los registros demostrativos no se atribuyen a una persona real."""
        usuario, creada = get_user_model().objects.get_or_create(
            username=CUENTA,
            defaults={'first_name': 'Datos', 'last_name': 'demostrativos', 'is_active': False},
        )
        if creada:
            usuario.set_unusable_password()
            usuario.save(update_fields=['password'])
        return usuario

    def _limpiar(self, unidad):
        ordenes = OrdenProduccion.objects.filter(unidad=unidad, demostrativa=True)
        lotes = LoteProducto.objects.filter(unidad=unidad, demostrativo=True)
        NoConformidad.objects.filter(Q(lote_producto__in=lotes) | Q(control__orden__in=ordenes)).delete()
        ControlCalidad.objects.filter(Q(lote_producto__in=lotes) | Q(orden__in=ordenes)).delete()
        MovimientoProducto.objects.filter(lote__in=lotes).delete()
        lotes.delete()
        ordenes.delete()

    def _orden(self, receta, usuario, *, origen, inicio, fin, observacion):
        etapas = list(receta.etapas.select_related('espacio', 'equipo').order_by('orden'))
        linea = next((e.espacio for e in etapas if e.espacio_id and e.espacio.tipo == 'linea'), None)
        orden = OrdenProduccion(
            unidad=receta.unidad, receta=receta, factor=Decimal('1'), origen=origen,
            sesion=SesionERP.demostrativa_de(receta.unidad),
            fecha_inicio=inicio, fecha_fin=fin, linea=linea, creada_por=usuario,
            observaciones=f'{MARCA} {observacion}',
        )
        orden.planificar_cantidades()
        orden.full_clean()
        orden.save()
        equipos = {e.equipo_id for e in etapas if e.equipo_id}
        orden.equipos.set([
            unidad_equipo for unidad_equipo in UnidadEquipo.objects.filter(equipo_id__in=equipos, activa=True)
            .order_by('equipo_id', 'codigo_unidad').distinct('equipo_id')
        ])
        return orden

    def _corridas(self, unidad, usuario):
        hoy = timezone.localdate()
        recetas = list(
            Receta.objects.filter(unidad=unidad, activa=True, origen='referencia')
            .select_related('producto', 'unidad').order_by('codigo')
        )
        creadas = 0
        for indice, receta in enumerate(recetas):
            if OrdenProduccion.objects.filter(unidad=unidad, receta=receta, demostrativa=True).exists():
                continue
            dias = max(1, min(30, math.ceil(float(receta.duracion_horas or 8) / 24)))
            fin = hoy - timedelta(days=3 + indice * 2)
            orden = self._orden(
                receta, usuario, origen=AMBITOS[indice % len(AMBITOS)], inicio=fin - timedelta(days=dias - 1),
                fin=fin, observacion=f'Corrida demostrativa de {receta.producto.nombre.lower()} para validar el flujo.',
            )
            self._cerrar(orden, usuario, RENDIMIENTOS[indice % len(RENDIMIENTOS)])
            self._liberar_y_despachar(orden, usuario, no_conforme=indice % 5 == 4)
            creadas += 1
        # Una corrida planificada por planta, para ejercitar el inicio y el cierre desde el panel.
        if recetas and not OrdenProduccion.objects.filter(
            unidad=unidad, demostrativa=True, estado__in=OrdenProduccion.ESTADOS_ABIERTOS,
        ).exists():
            self._orden(
                recetas[0], usuario, origen='practica', inicio=hoy + timedelta(days=7), fin=hoy + timedelta(days=7),
                observacion='Corrida demostrativa planificada: iníciala y ciérrala desde el panel.',
            )
            creadas += 1
        return creadas

    def _cerrar(self, orden, usuario, rendimiento):
        consumos = [
            {'consumible_id': item['consumible'].pk, 'lote_id': None, 'cantidad': item['cantidad']}
            for item in orden.insumos_planificados()
        ]
        salidas = [
            {
                'producto_id': item['producto'].pk,
                'cantidad': _cantidad(item['cantidad'] * rendimiento if item['principal'] else item['cantidad'],
                                      item['producto']),
            }
            for item in orden.salidas_planificadas()
        ]
        orden.cerrar(
            usuario=usuario, consumos=consumos, salidas=salidas,
            observaciones='Cierre demostrativo con las cantidades de la receta.',
        )
        # Los lotes llevan la fecha de la corrida, no la del día en que se cargó el ejemplo.
        for lote in orden.lotes.select_related('producto'):
            lote.fecha_produccion = orden.fecha_fin
            vida = lote.producto.vida_util_dias
            lote.fecha_vencimiento = orden.fecha_fin + timedelta(days=vida) if vida else None
            lote.save(update_fields=['fecha_produccion', 'fecha_vencimiento', 'actualizado_en'])

    def _liberar_y_despachar(self, orden, usuario, *, no_conforme):
        lote = orden.lotes.filter(producto=orden.producto).first()
        if lote is None:
            return
        plan = plan_para_lote_producto(lote)
        if plan is not None:
            parametros = plan.parametros_ordenados()
            fallido = next((p for p in parametros if p.critico and p.tipo == 'numerico'), None) if no_conforme else None
            datos = {f'parametro_{p.pk}': _valor(p, fuera=p is fallido) for p in parametros}
            datos['observaciones'] = 'Control demostrativo.'
            registrar_control(orden.unidad, plan, datos, usuario, lote_producto=lote)
            lote.refresh_from_db()
        elif lote.control_calidad == 'pendiente':
            lote.aprobar_calidad()
        if lote.estado != 'disponible' or lote.cantidad_disponible <= 0:
            return
        venta = _cantidad(lote.cantidad_disponible * Decimal('0.4'), lote.producto)
        # Lo refrigerado sale un grado por debajo de su límite, como en un despacho correcto.
        limite = lote.producto.limite_frio
        frio = limite - 1 if limite is not None else None
        if venta > 0:
            MovimientoProducto.objects.create(
                unidad=orden.unidad, lote=lote, tipo='venta', cantidad=venta,
                destino='Cliente demostrativo', registrado_por=usuario, temperatura_despacho=frio,
            )
        muestra = min(_cantidad('1', lote.producto), lote.cantidad_disponible - venta)
        if muestra > 0:
            MovimientoProducto.objects.create(
                unidad=orden.unidad, lote=lote, tipo='muestra', cantidad=muestra,
                destino='Degustación demostrativa', registrado_por=usuario, temperatura_despacho=frio,
            )
