"""El ERP de la planta: sus secciones, su menú y el mapa de sus módulos.

El ERP opera la cadena productiva (planificar, comprar, producir, controlar y
despachar) en su propia pestaña; «Gestionar laboratorio» administra la unidad
(uso, recursos, mantenimiento, seguridad, personal y reportes). Comparten la
consola y cada una pinta solo sus secciones. El tablero del ERP muestra cada
módulo con sus indicadores reales (lo demostrativo nunca se cuenta), a qué
alimenta y el acceso de quien mira; los módulos de la administración se abren en
su pestaña. El flujo paso a paso recorre la cadena, del plan a la venta.
"""
from datetime import timedelta

from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.plantas_piloto.operacion.models.erp import ExistenciaSesion
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo
from apps.plantas_piloto.operacion.models.planificacion import LineaPlanMaestro, PedidoAbastecimiento
from apps.finanzas.models.compras import OrdenCompra
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.plantas_piloto.operacion.models.calidad import NoConformidad
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.gestion_unidades.models.espacios import ResponsableUnidad

# clave: (nombre, icono, permiso que habilita operarlo, sección de la consola, qué gestiona, a qué alimenta)
MODULOS = {
    'direccion': ('Dirección y organización', 'iconsminds-network', 'configuracion', 'configuracion',
                  'Responsables, roles y el permiso de cada uno sobre los módulos.', ('planificacion',)),
    'planificacion': ('Planificación', 'iconsminds-calendar-4', 'produccion', 'planificacion',
                      'Plan de ventas, plan maestro y requerimiento de materiales.', ('abastecimiento', 'produccion')),
    'abastecimiento': ('Abastecimiento', 'iconsminds-box-close', 'produccion', 'planificacion',
                       'Proveedores, órdenes de compra y entregas, que entran al inventario con su lote.',
                       ('inventario',)),
    'inventario': ('Inventario y almacén', 'iconsminds-shop-4', 'inventario', 'recursos',
                   'Existencias, lotes de insumo, vencimientos y conteos.', ('produccion',)),
    'produccion': ('Producción', 'iconsminds-factory', 'produccion', 'produccion',
                   'Órdenes, corridas, lotes y rendimientos.', ('calidad',)),
    'calidad': ('Calidad', 'iconsminds-check', 'produccion', 'calidad',
                'Planes, controles, liberación de lotes y no conformidades.', ('logistica',)),
    'mantenimiento': ('Mantenimiento', 'iconsminds-wrench', 'mantenimiento', 'mantenimiento',
                      'Mantenimientos programados e incidencias de los equipos.', ('produccion',)),
    'logistica': ('Logística y despacho', 'iconsminds-jeep', 'produccion', 'produccion',
                  'Salidas de producto: ventas, muestras, consumo interno y transferencias.', ('servicios',)),
    'servicios': ('Servicios y reservas', 'iconsminds-calendar-4', 'reservas', 'reservas',
                  'Solicitudes de servicio, maquila y reservas de la planta.', ('finanzas',)),
    'seguridad': ('Seguridad y ambiente', 'iconsminds-security-settings', 'seguridad', 'seguridad',
                  'Requisitos de acceso, habilitaciones e ingresos.', ('formacion',)),
    'formacion': ('Formación', 'iconsminds-notepad', 'practicas', 'practicas',
                  'Guías de práctica, planificación y ejecución de las prácticas.', ('produccion',)),
    'finanzas': ('Finanzas y costos', 'iconsminds-money-bag', 'finanzas', 'recursos',
                 'Ingresos, gastos y costo de las corridas.', ()),
    'documentacion': ('Reportes y expediente', 'fas fa-file-alt', 'reportes', 'reportes',
                      'Expediente del período, reportes y fichas publicadas.', ()),
}

# Los módulos de la cadena productiva: el personal de la planta los consulta aunque no los opere.
CONSULTA_ABIERTA = {'planificacion', 'abastecimiento', 'produccion', 'calidad', 'logistica'}

# La cadena de la planta, de la planificación a la venta.
FLUJO = ('planificacion', 'abastecimiento', 'inventario', 'produccion', 'calidad', 'logistica', 'servicios')

ACCESOS = {'opera': 'Operas', 'consulta': 'Solo consulta', 'sin_acceso': 'Sin acceso'}

# Las secciones de la consola que pinta el ERP; las demás son de Gestionar laboratorio.
SECCIONES_ERP = {'mapa', 'sesiones', 'planificacion', 'produccion', 'calidad', 'supervision'}
NAVEGACION_ERP = (
    ('mapa', 'Tablero', 'Inicio'),
    ('sesiones', 'Sesiones de práctica', 'Inicio'),
    ('planificacion', 'Planificación y compras', 'Planificar'),
    ('produccion', 'Producción y despacho', 'Producir'),
    ('calidad', 'Calidad', 'Producir'),
    ('supervision', 'Supervisión', 'Producir'),
)
NAVEGACION_GESTION_PLANTA = (
    ('indicadores', 'Tablero', 'Inicio'),
    ('programacion', 'Programación', 'Uso de la unidad'),
    ('reservas', 'Reservas', 'Uso de la unidad'),
    ('visitas', 'Visitas', 'Uso de la unidad'),
    ('practicas', 'Prácticas', 'Formación'),
    ('ejercicios', 'Ejercicios', 'Formación'),
    ('recursos', 'Activos e inventario', 'Recursos'),
    ('mantenimiento', 'Mantenimiento', 'Recursos'),
    ('seguridad', 'Seguridad', 'Administrar'),
    ('reportes', 'Reportes', 'Administrar'),
    ('configuracion', 'Configuración y personal', 'Administrar'),
)


def _indicadores(unidad, sesion):
    hoy = timezone.localdate()
    hace_30 = timezone.now() - timedelta(days=30)
    ordenes = OrdenProduccion.objects.en_sesion(sesion).filter(unidad=unidad)
    lotes = LoteProducto.objects.en_sesion(sesion).filter(unidad=unidad)
    # En una sesión lo bajo el mínimo se mide con sus existencias.
    bajo_minimo = (
        ExistenciaSesion.objects.filter(
            sesion=sesion, consumible__activo=True, consumible__minimo__gt=0, cantidad__lt=F('consumible__minimo'),
        ) if sesion is not None else Consumible.objects.filter(
            unidad=unidad, activo=True, minimo__gt=0, stock_total__lt=F('minimo'),
        )
    )
    ingresos = (
        MovimientoFinancieroUnidad.objects.filter(
            unidad=unidad, tipo='ingreso', fecha_movimiento__gte=hoy.replace(day=1),
        ).exclude(estado='anulado').aggregate(total=Sum('monto'))['total'] or 0
    )
    return {
        'direccion': [('Responsables activos', ResponsableUnidad.objects.filter(unidad=unidad, activo=True).count())],
        'planificacion': [('Líneas del plan maestro', LineaPlanMaestro.objects.filter(
            plan__unidad=unidad, plan__sesion=sesion,
        ).count())],
        'abastecimiento': [
            ('Insumos bajo su mínimo', bajo_minimo.count()),
            ('Pedidos en camino', PedidoAbastecimiento.objects.filter(
                unidad=unidad, sesion=sesion, estado__in=PedidoAbastecimiento.ESTADOS_EN_CAMINO,
            ).count()),
            ('Órdenes de compra abiertas', OrdenCompra.objects.filter(
                unidad=unidad, sesion=sesion, estado__in=('emitida', 'confirmada'),
            ).count()),
        ],
        'inventario': [
            ('Insumos activos', Consumible.objects.filter(unidad=unidad, activo=True).count()),
            ('Lotes de insumo en uso', LoteConsumible.objects.filter(consumible__unidad=unidad, estado='en_uso').count()),
        ],
        'produccion': [
            ('Órdenes abiertas', ordenes.filter(estado__in=OrdenProduccion.ESTADOS_ABIERTOS).count()),
            ('Corridas del mes', ordenes.filter(estado='terminada', fecha_fin__gte=hoy.replace(day=1)).count()),
        ],
        'calidad': [
            ('Lotes por liberar', lotes.filter(control_calidad='pendiente').count()),
            ('No conformidades abiertas', NoConformidad.objects.en_sesion(sesion).filter(unidad=unidad).exclude(
                estado='cerrada',
            ).count()),
        ],
        'mantenimiento': [
            ('Mantenimientos pendientes', MantenimientoEquipo.objects.filter(
                unidad=unidad, estado__in=('planificado', 'programado', 'en_proceso'),
            ).count()),
            ('Incidencias abiertas', IncidenciaEquipo.objects.filter(unidad=unidad).exclude(
                estado__in=IncidenciaEquipo.ESTADOS_CERRADOS,
            ).count()),
        ],
        'logistica': [
            ('Salidas en 30 días', MovimientoProducto.objects.en_sesion(sesion).filter(
                unidad=unidad, fecha__gte=hace_30,
            ).count()),
            ('Lotes disponibles', lotes.filter(estado='disponible').count()),
        ],
        'servicios': [
            ('Servicios pendientes', Reserva.objects.filter(
                laboratorio=unidad, tipo_solicitud='servicio', estado='pendiente',
            ).count()),
            ('Ventas en 30 días', MovimientoProducto.objects.reales().filter(
                unidad=unidad, tipo='venta', fecha__gte=hace_30,
            ).count()),
        ],
        'seguridad': [('Requisitos vigentes', RequisitoAcceso.objects.filter(unidad=unidad, activo=True).count())],
        'formacion': [('Guías publicadas', GuiaActividadReserva.objects.filter(
            actividad__unidad=unidad, activo=True, estado_publicacion='publicada',
        ).count())],
        'finanzas': [('Ingresos del mes', f'${ingresos:.2f}')],
        'documentacion': [('Fichas publicadas', FichaContenido.objects.filter(unidad=unidad, estado='publicada').count())],
    }


def mapa_de_la_planta(unidad, permisos, vistas_disponibles, sesion=None):
    """Los módulos de la planta con su acceso para quien mira y el flujo de su cadena, en la sesión."""
    indicadores = _indicadores(unidad, sesion)
    consola = reverse('gestion_unidad', args=[unidad.slug])
    modulos = []
    for clave, (nombre, icono, permiso, vista, descripcion, alimenta) in MODULOS.items():
        if permisos.get(permiso):
            acceso = 'opera'
        elif clave in CONSULTA_ABIERTA and vista in vistas_disponibles:
            acceso = 'consulta'
        else:
            acceso = 'sin_acceso'
        en_erp = vista in SECCIONES_ERP
        modulos.append({
            'clave': clave, 'nombre': nombre, 'icono': icono, 'descripcion': descripcion,
            'acceso': acceso, 'acceso_texto': ACCESOS[acceso], 'en_erp': en_erp,
            'vista': vista if en_erp and acceso != 'sin_acceso' and vista in vistas_disponibles else '',
            # Lo que se administra en Gestionar laboratorio se abre en su pestaña, con su permiso.
            'enlace': f'{consola}?view={vista}' if not en_erp and acceso == 'opera' else '',
            # Sin acceso no se muestran sus cifras: las finanzas no son de todos.
            'indicadores': indicadores[clave] if acceso != 'sin_acceso' else [],
            'alimenta': [MODULOS[destino][0] for destino in alimenta],
        })
    por_clave = {modulo['clave']: modulo for modulo in modulos}
    return {
        'modulos': modulos,
        'modulos_erp': [modulo for modulo in modulos if modulo['en_erp']],
        'modulos_gestion': [modulo for modulo in modulos if not modulo['en_erp']],
        'flujo': [{'paso': indice, **por_clave[clave]} for indice, clave in enumerate(FLUJO, start=1)],
    }
