"""Inventario por naturaleza del recurso, sin sumar cantidades incompatibles."""
from collections import defaultdict


CLASES = (
    ('equipos', 'Equipos físicos'), ('software', 'Software y licencias'),
    ('materiales', 'Materiales'), ('insumos', 'Insumos'), ('reactivos', 'Reactivos'),
    ('repuestos', 'Piezas y accesorios de referencia'),
)


def clase_existencia(clasificacion):
    return {'material': 'materiales', 'reactivo': 'reactivos'}.get(clasificacion, 'insumos')


def inventario_por_clase(unidad, equipos, areas_equipo, areas_insumos, areas_software, nombres):
    from apps.recursos.models.consumibles import Consumible
    from apps.recursos.models.software import SoftwareDisponible
    from apps.recursos.models.equipos import PiezaEquipo
    grupos = {clave: dict(clave=clave, nombre=nombre, filas=[]) for clave, nombre in CLASES}

    def areas(ids):
        return ' · '.join(nombres.get(pk, str(pk)) for pk in sorted(ids)) or 'Sin área asignada'

    for equipo in equipos:
        if not equipo.activa or equipo.fecha_baja:
            continue
        grupos['equipos']['filas'].append(dict(id=equipo.pk, nombre=equipo.equipo.nombre,
            codigo=equipo.codigo_unidad, cantidad='1', unidad_medida='activo',
            areas=areas(areas_equipo[equipo.pk]), areas_ids=sorted(areas_equipo[equipo.pk]),
            estado=equipo.get_estado_unidad_display(),
            detalle='Baja registrada' if equipo.fecha_baja else 'Activo físico identificado individualmente.'))
    for software in SoftwareDisponible.objects.filter(unidad=unidad, activo=True).prefetch_related('equipos_instalados').order_by('nombre', 'pk'):
        ids = set(areas_software.get(software.pk, set()))
        instalados = [equipo.pk for equipo in software.equipos_instalados.all() if equipo.activa and not equipo.fecha_baja]
        for equipo_id in instalados:
            ids.update(areas_equipo.get(equipo_id, set()))
        es_licencia = software.tipo_recurso == 'licencia'
        grupos['software']['filas'].append(dict(id=software.pk, nombre=software.nombre,
            codigo=software.codigo, cantidad=str(software.licencias_totales) if es_licencia else str(len(instalados)),
            unidad_medida='licencias declaradas' if es_licencia else 'equipos con instalación registrada',
            areas=areas(ids), areas_ids=sorted(ids), estado='Activo' if software.activo else 'Inactivo',
            detalle=(f'{software.licencias_disponibles} licencias disponibles registradas. ' if es_licencia else '')
                + software.get_tipo_acceso_display() + (f' · Versión {software.version}' if software.version else ''),
            tipo_recurso=software.tipo_recurso, licencias_totales=software.licencias_totales if es_licencia else None,
            licencias_disponibles=software.licencias_disponibles if es_licencia else None))
    for recurso in Consumible.objects.filter(unidad=unidad, activo=True).order_by('clasificacion', 'nombre', 'pk'):
        clave = clase_existencia(recurso.clasificacion)
        grupos[clave]['filas'].append(dict(id=recurso.pk, nombre=recurso.nombre, codigo=recurso.codigo,
            cantidad=str(recurso.stock_total), unidad_medida=recurso.unidad_medida or 'Unidad por confirmar',
            areas=areas(areas_insumos.get(recurso.pk, set())), areas_ids=sorted(areas_insumos.get(recurso.pk, set())),
            estado=recurso.estado_stock if recurso.activo else 'Inactivo',
            detalle=' · '.join(v for v in (recurso.get_clasificacion_display(), recurso.presentacion,
                recurso.variante, recurso.especificacion_tecnica) if v),
            clasificacion=recurso.clasificacion))
    por_modelo = defaultdict(list)
    for equipo in equipos:
        if equipo.activa and not equipo.fecha_baja:
            por_modelo[equipo.equipo_id].append(equipo)
    for pieza in PiezaEquipo.objects.filter(equipo_id__in=por_modelo).select_related('equipo').order_by('nombre', 'pk'):
        ids = {area for equipo in por_modelo[pieza.equipo_id] for area in areas_equipo[equipo.pk]}
        grupos['repuestos']['filas'].append(dict(id=pieza.pk, nombre=pieza.nombre, codigo='',
            cantidad=str(pieza.cantidad), unidad_medida='por equipo del modelo',
            areas=areas(ids), areas_ids=sorted(ids), estado='Referencia técnica',
            detalle=f'{pieza.equipo.nombre}. {pieza.descripcion} '
                + ('Declara repuesto disponible; confirmar existencias.' if pieza.repuesto_disponible else
                   'No declara repuesto disponible. Esto no cuantifica stock ni obliga a comprar.'),
            es_referencia=True))
    for grupo in grupos.values():
        grupo['registros'] = len(grupo['filas'])
    return list(grupos.values())


def bloques_existencias(grupos):
    """Resumen para el informe; las cantidades permanecen por recurso y unidad."""
    return [dict(tipo='tabla', titulo='Recursos registrados por clase',
        cabecera=['Clase', 'Registros', 'Alcance de las cantidades'],
        filas=[[g['nombre'], str(g['registros']),
            'Cantidad de referencia por modelo; no representa stock.' if g['clave'] == 'repuestos' else
            'Licencias e instalaciones diferenciadas por recurso.' if g['clave'] == 'software' else
            'Existencias por artículo y unidad de medida; no se suman entre artículos.' if g['clave'] != 'equipos' else
            'Un activo identificado por registro.'] for g in grupos])]
