"""Servicios industriales de una planta: lo que consumen sus equipos y lo que descargan sus procesos.

Energía eléctrica, vapor, agua de proceso, aire comprimido, refrigeración y
efluentes, desde los datos técnicos de cada equipo y las salidas de cada proceso.
Si los datos técnicos son de referencia, la página lo dice: sirven para validar
el dimensionamiento, no reemplazan el levantamiento de la planta.
"""
import re
from decimal import Decimal

from django.db.models import Q

from apps.plantas_piloto.operacion.models.produccion import SalidaReceta
from apps.recursos.models.unidades import UnidadEquipo

# Frío: cámaras, congeladores y túneles; una cámara de fermentación trabaja en caliente.
_FRIO = re.compile(r'c[aá]mara|congel|refriger|t[uú]nel', re.I)
_CALIENTE = re.compile(r'fermentaci', re.I)


def _texto(valor):
    valor = Decimal(valor).quantize(Decimal('0.01')).normalize()
    return format(valor, 'f')


def _equipos_de(unidad):
    """Cada equipo con cuántas unidades activas tiene la planta."""
    equipos = {}
    for unidad_equipo in (
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True)
        .select_related('equipo').distinct()
    ):
        fila = equipos.setdefault(unidad_equipo.equipo_id, {'equipo': unidad_equipo.equipo, 'unidades': 0})
        fila['unidades'] += 1
    return sorted(equipos.values(), key=lambda fila: fila['equipo'].nombre)


def _consumo(equipos, campo, unidad_medida):
    filas, total = [], Decimal('0')
    for fila in equipos:
        valor = getattr(fila['equipo'], campo)
        if valor is None:
            continue
        subtotal = valor * fila['unidades']
        total += subtotal
        filas.append({
            'equipo': fila['equipo'], 'unidades': fila['unidades'],
            'valor': f'{_texto(valor)} {unidad_medida}', 'subtotal': f'{_texto(subtotal)} {unidad_medida}',
        })
    return filas, total


def servicios_industriales(unidad):
    equipos = _equipos_de(unidad)
    servicios = []

    filas, total = _consumo(equipos, 'potencia_kw', 'kW')
    servicios.append({
        'clave': 'electricidad', 'nombre': 'Energía eléctrica', 'icono': 'fas fa-bolt',
        'total': f'{_texto(total)} kW instalados' if filas else '', 'filas': filas,
        'nota': 'Potencia instalada: la suma de la placa de cada equipo por sus unidades.',
    })

    filas, total = _consumo(equipos, 'consumo_vapor', 'kg/h')
    generadores = [
        fila for fila in equipos
        if 'vapor' in (fila['equipo'].unidad_capacidad or '').lower() and fila['equipo'].capacidad_nominal
    ]
    capacidad = sum((fila['equipo'].capacidad_nominal * fila['unidades'] for fila in generadores), Decimal('0'))
    if generadores:
        cobertura = (
            f'Generación propia: {_texto(capacidad)} kg/h ({", ".join(f["equipo"].nombre for f in generadores)}); '
            + ('cubre la demanda instalada.' if capacidad >= total else 'no alcanza si todos operan a la vez.')
        )
    else:
        cobertura = 'La planta no declara un generador de vapor propio: lo recibe de la red de la universidad.'
    servicios.append({
        'clave': 'vapor', 'nombre': 'Vapor', 'icono': 'fas fa-cloud',
        'total': f'{_texto(total)} kg/h de demanda' if filas else '', 'filas': filas, 'nota': cobertura,
    })

    filas, total = _consumo(equipos, 'consumo_agua', 'L/ciclo')
    servicios.append({
        'clave': 'agua', 'nombre': 'Agua de proceso y limpieza', 'icono': 'fas fa-tint',
        'total': f'{_texto(total)} L por ciclo de todos los equipos' if filas else '', 'filas': filas,
        'nota': 'Lo que usa cada equipo por ciclo de proceso y de limpieza.',
    })

    filas, total = _consumo(equipos, 'consumo_aire', 'm³/h')
    servicios.append({
        'clave': 'aire', 'nombre': 'Aire comprimido', 'icono': 'fas fa-wind',
        'total': f'{_texto(total)} m³/h' if filas else '', 'filas': filas,
        'nota': 'Caudal de aire de los equipos neumáticos y de secado.',
    })

    filas = [
        {
            'equipo': fila['equipo'], 'unidades': fila['unidades'],
            'valor': (
                f"{_texto(fila['equipo'].capacidad_nominal)} {fila['equipo'].unidad_capacidad}"
                if fila['equipo'].capacidad_nominal else '—'
            ),
            'subtotal': f"{_texto(fila['equipo'].potencia_kw)} kW" if fila['equipo'].potencia_kw else '—',
        }
        for fila in equipos
        if _FRIO.search(fila['equipo'].nombre) and not _CALIENTE.search(fila['equipo'].nombre)
    ]
    servicios.append({
        'clave': 'frio', 'nombre': 'Refrigeración y congelación', 'icono': 'fas fa-snowflake',
        'total': f'{sum(fila["unidades"] for fila in filas)} equipos de frío' if filas else '', 'filas': filas,
        'nota': 'La cadena de frío de la planta: capacidad de cada cámara o congelador y su potencia.',
    })

    efluentes = (
        SalidaReceta.objects.filter(
            receta__unidad=unidad, receta__activa=True, receta__origen='referencia',
            externa_al_flujo=True, producto__tipo='residuo',
        )
        .select_related('receta__producto', 'producto')
        .order_by('receta__producto__nombre')
    )
    filas = [
        {
            'equipo': None, 'proceso': salida.receta.producto.nombre, 'unidades': salida.producto.nombre,
            'valor': f'{_texto(salida.cantidad)} {salida.producto.unidad_medida}',
            'subtotal': f'{_texto(salida.receta.cantidad_base)} {salida.receta.unidad_base}',
        }
        for salida in efluentes
    ]
    servicios.append({
        'clave': 'efluentes', 'nombre': 'Efluentes y aguas residuales', 'icono': 'fas fa-water',
        'total': f'{len(filas)} procesos declaran su descarga' if filas else '', 'filas': filas,
        'nota': 'Agua de lavado y limpieza que sale del flujo en cada corrida base, hacia tratamiento.',
    })

    return {
        'servicios': servicios,
        'con_datos': sum(1 for servicio in servicios if servicio['filas']),
        'de_referencia': sum(1 for fila in equipos if fila['equipo'].origen_datos_tecnicos == 'referencia'),
        'total_equipos': len(equipos),
    }
