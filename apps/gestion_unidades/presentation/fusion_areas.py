"""Fusión de áreas: una pasa a otra sus equipos, su ficha, sus fotos, sus reservas y sus procesos, y queda inactiva
señalando adónde se integró. No se borra nada: el código viejo sigue existiendo para que los cargadores no lo
vuelvan a crear, y su página lleva al área que lo recibió."""
from collections import Counter

from django.db import transaction
from django.db.models import Max

from apps.gestion_unidades.models.repositorio import ArtefactoExterno
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, OrdenProduccion
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.interior import MedioInterior
from apps.recursos.models.redistribucion import TraspasoEquipo

# Los textos de la ficha que se suman cuando el área absorbida tenía los suyos.
TEXTOS_DE_FICHA = ('que_es', 'como_funciona', 'principio', 'distribucion', 'aplicaciones', 'conexiones', 'seguridad')


def area_vigente(espacio):
    """El área donde hoy vive lo que se cargó para este código: la propia o la que la integró."""
    vistos = set()
    unidad_id = espacio.unidad_id if espacio is not None else None
    while espacio is not None and espacio.integrada_en_id:
        if espacio.pk in vistos or espacio.unidad_id != unidad_id:
            return None
        vistos.add(espacio.pk)
        espacio = espacio.integrada_en
    if espacio is not None and espacio.unidad_id != unidad_id:
        return None
    return espacio


def integrada(unidad, codigo):
    """El área con este código si ya se fusionó en otra; los cargadores no la reactivan y dirigen lo suyo a la que
    la recibió."""
    return EspacioReservable.objects.filter(unidad=unidad, codigo=codigo, integrada_en__isnull=False).first()


def _unir_fichas(origen, destino, resumen):
    ficha = FichaArea.objects.filter(espacio=origen).first()
    if ficha is None:
        return
    recibe = FichaArea.objects.filter(espacio=destino).first()
    if recibe is None:
        ficha.espacio = destino
        ficha.save(update_fields=['espacio'])
        resumen['fichas'] += 1
        return
    desde = recibe.elementos.aggregate(ultimo=Max('orden'))['ultimo'] or 0
    for elemento in ficha.elementos.order_by('orden', 'pk'):
        elemento.ficha, elemento.orden = recibe, desde + elemento.orden
        elemento.save(update_fields=['ficha', 'orden'])
        resumen['elementos de ficha'] += 1
    for campo in TEXTOS_DE_FICHA:
        propio, ajeno = getattr(recibe, campo).strip(), getattr(ficha, campo).strip()
        if ajeno and ajeno not in propio:
            setattr(recibe, campo, f'{propio}\n{ajeno}'.strip())
    recibe.save()
    ficha.delete()
    resumen['fichas'] += 1


@transaction.atomic
def fusionar_area(origen, destino):
    """Pasa todo lo de «origen» a «destino» y deja «origen» inactiva e integrada en «destino». Se puede repetir:
    lo que un cargador haya vuelto a poner en el área vieja se traslada de nuevo."""
    if origen.pk == destino.pk or origen.unidad_id != destino.unidad_id:
        raise ValueError('Solo se fusionan dos áreas distintas de la misma unidad.')
    # El orden de bloqueo es estable incluso ante dos fusiones inversas.
    areas = {a.pk: a for a in EspacioReservable.objects.select_for_update().filter(
        pk__in=(origen.pk, destino.pk),
    ).order_by('pk')}
    origen, destino = areas.get(origen.pk), areas.get(destino.pk)
    if origen is None or destino is None or origen.unidad_id != destino.unidad_id:
        raise ValueError('Las dos áreas deben existir y pertenecer a la misma unidad.')
    if destino.integrada_en_id or not destino.activo:
        raise ValueError('Selecciona un área de destino activa que no esté integrada en otra.')
    if origen.integrada_en_id and area_vigente(origen) != destino:
        raise ValueError('El área de origen ya está integrada en otro destino.')
    resumen = Counter()
    equipos = list(origen.equipos_asociados.all())
    if equipos:
        destino.equipos_asociados.add(*equipos)
        origen.equipos_asociados.remove(*equipos)
        resumen['equipos'] += len(equipos)
    for relacion in ('reservas', 'bloqueos_agenda', 'visitas'):
        for objeto in getattr(origen, relacion).all():
            campo = {'reservas': 'espacios_solicitados', 'bloqueos_agenda': 'espacios', 'visitas': 'recorrido'}[relacion]
            getattr(objeto, campo).add(destino)
            getattr(objeto, campo).remove(origen)
            resumen[relacion] += 1
    resumen['fotos'] += MedioInterior.objects.filter(espacio=origen).update(espacio=destino)
    resumen['etapas'] += EtapaReceta.objects.filter(espacio=origen).update(espacio=destino)
    resumen['órdenes'] += OrdenProduccion.objects.filter(linea=origen).update(linea=destino)
    resumen['traspasos'] += TraspasoEquipo.objects.filter(area_destino=origen).update(area_destino=destino)
    resumen['recursos en línea'] += ArtefactoExterno.objects.filter(area=origen).update(area=destino)
    _unir_fichas(origen, destino, resumen)
    origen.activo = origen.reservable = origen.visitable = False
    origen.integrada_en = destino
    origen.save(update_fields=['activo', 'reservable', 'visitable', 'integrada_en'])
    return +resumen
