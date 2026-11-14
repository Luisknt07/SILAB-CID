"""El estándar de los códigos del sistema: UNIDAD-ÁREA-MODELO-N.º, igual en todas las unidades.

El código del bien (bodega) sigue siendo el principal cuando existe; el del sistema lo acompaña y dice dónde
está y qué es:

    FAB-IMP3D-05      modelo (ficha técnica): sigla de la unidad, sigla del área y número del modelo en el área
    FAB-IMP3D-05-02   unidad física: el mismo modelo en esa área y su número correlativo

La sigla de la unidad es el prefijo de los códigos de sus áreas (FAB-AREA-IMP3D → FAB); la del área, lo que sigue
sin las palabras genéricas (AREA, EST, SALA…), con lo que quepa en el código de modelo (20 caracteres). Un equipo sin área va en GEN. Los códigos
anteriores quedan como alias: las etiquetas y los QR ya impresos siguen abriendo el equipo.
"""
import re
from collections import Counter

from django.db.models import Q

GENERICAS = {'AREA', 'EST', 'ZONA', 'LAB', 'SALA', 'LINEA', 'MESON'}
SIN_AREA = 'GEN'


def sigla_de_unidad(unidad):
    """El prefijo común de los códigos de las áreas de la unidad; sin áreas, el de sus equipos o su slug."""
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.recursos.models.unidades import UnidadEquipo

    prefijos = Counter(codigo.split('-')[0].upper() for codigo in
                       EspacioReservable.objects.filter(unidad=unidad).values_list('codigo', flat=True) if codigo)
    if not prefijos:
        prefijos = Counter(codigo.split('-')[0].upper() for codigo in
                           UnidadEquipo.objects.filter(laboratorio=unidad).values_list('codigo_unidad', flat=True))
    if prefijos:
        return re.sub(r'[^A-Z0-9]', '', prefijos.most_common(1)[0][0])[:5] or 'UNI'
    return ''.join(parte[0] for parte in unidad.slug.split('-') if parte)[:5].upper() or 'UNI'


def sigla_de_area(espacio):
    """FAB-AREA-IMP3D → IMP3D; FAB-SALA-CAP → CAP; sin área → GEN."""
    if espacio is None:
        return SIN_AREA
    prefijo, *partes = [re.sub(r'[^A-Z0-9]', '', parte.upper()) for parte in espacio.codigo.split('-')]
    propias = [parte for parte in partes if parte and parte not in GENERICAS] or [parte for parte in partes if parte]
    # El código de modelo es UNIDAD-ÁREA-NN y la ficha técnica admite 20 caracteres.
    return ''.join(propias)[:max(4, 16 - len(prefijo[:5]))] or SIN_AREA


def area_principal(equipo, unidad=None):
    """El área que manda en el código: la primera (por orden) de la unidad dueña entre las asociadas."""
    unidad = unidad or equipo.laboratorio
    return (equipo.espacios_asociados.filter(unidad=unidad).order_by('orden', 'nombre').first()
            if equipo.pk else None)


def _numeros_en_uso(prefijo):
    """Los números ya tomados con ese prefijo, en códigos vigentes y anteriores (un alias no se reutiliza)."""
    from apps.recursos.models.equipos import AliasCodigoEquipoServicio, EquiposServicios
    from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo

    patron = re.compile(rf'^{re.escape(prefijo)}(\d+)')
    codigos = [*EquiposServicios.objects.filter(codigo__startswith=prefijo).values_list('codigo', flat=True),
               *AliasCodigoEquipoServicio.objects.filter(codigo__startswith=prefijo).values_list('codigo', flat=True),
               *UnidadEquipo.objects.filter(codigo_unidad__startswith=prefijo).values_list('codigo_unidad', flat=True),
               *AliasCodigoUnidadEquipo.objects.filter(codigo__startswith=prefijo).values_list('codigo', flat=True)]
    return {int(coincidencia.group(1)) for coincidencia in map(patron.match, codigos) if coincidencia}


def _siguiente(prefijo):
    numero = 1
    usados = _numeros_en_uso(prefijo)
    while numero in usados:
        numero += 1
    return f'{prefijo}{numero:02d}'


def siguiente_codigo_modelo(unidad, espacio):
    """El próximo código de modelo libre en esa área: FAB-IMP3D-06."""
    return _siguiente(f'{sigla_de_unidad(unidad)}-{sigla_de_area(espacio)}-')


def siguiente_codigo_unidad(unidad, espacio, tipo):
    """El próximo código de unidad física para ese modelo en esa área: FAB-IMP3D-05-03.

    Si el modelo ya tiene unidades con código estándar en el área, sigue su numeración; si su ficha técnica ya
    es de esa área, usa su número; si no, el modelo recibe un número nuevo en el área.
    """
    from apps.recursos.models.unidades import UnidadEquipo

    base = f'{sigla_de_unidad(unidad)}-{sigla_de_area(espacio)}-'
    patron = re.compile(rf'^{re.escape(base)}(\d{{2,}})-\d{{2,}}$')
    for codigo in (UnidadEquipo.objects.filter(equipo=tipo, codigo_unidad__startswith=base)
                   .order_by('codigo_unidad').values_list('codigo_unidad', flat=True)):
        coincidencia = patron.match(codigo)
        if coincidencia:
            return _siguiente(f'{base}{coincidencia.group(1)}-')
    modelo = tipo.codigo if re.fullmatch(rf'{re.escape(base)}\d{{2,}}', tipo.codigo or '') else siguiente_codigo_modelo(unidad, espacio)
    return _siguiente(f'{modelo}-')


def es_estandar(codigo, unidad, espacio, unidad_fisica=True):
    base = f'{sigla_de_unidad(unidad)}-{sigla_de_area(espacio)}-'
    patron = rf'{re.escape(base)}\d{{2,}}-\d{{2,}}' if unidad_fisica else rf'{re.escape(base)}\d{{2,}}'
    return bool(re.fullmatch(patron, codigo or ''))


def unidad_vigente(codigo):
    """La unidad física con ese código o con ese código como anterior (para los cargadores)."""
    from apps.recursos.models.unidades import UnidadEquipo

    return (UnidadEquipo.objects.filter(Q(codigo_unidad=codigo) | Q(codigos_anteriores__codigo=codigo))
            .distinct().first())


def modelo_vigente(codigo):
    """El modelo con ese código de ficha técnica o con ese código como anterior."""
    from apps.recursos.models.equipos import EquiposServicios

    return (EquiposServicios.objects.filter(Q(codigo=codigo) | Q(codigos_anteriores__codigo=codigo))
            .distinct().first())


def actualizar_o_crear(modelo_vigente_de, clase, campo, codigo, defaults):
    """update_or_create que reconoce los códigos anteriores: un cargador no duplica lo que se estandarizó."""
    objeto = modelo_vigente_de(codigo)
    if objeto is None:
        return clase.objects.create(**{campo: codigo}, **defaults), True
    for nombre, valor in defaults.items():
        setattr(objeto, nombre, valor)
    objeto.save()
    return objeto, False
