"""Procesos derivados: cada producto sin proceso parte de uno de referencia de su planta.

El derivado copia etapas, equipos, controles, insumos y salidas del proceso más
cercano de su familia como punto de partida. Queda marcado «derivado, por
validar» hasta que la planta ajuste formulación, tiempos y límites y lo valide.
Una nueva carga no pisa lo que ya se haya derivado o editado.
"""
import re

from django.db import transaction

from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, Producto, Receta, SalidaReceta

# Palabras que no distinguen un producto de otro al elegir la plantilla.
_VACIAS = {'de', 'del', 'la', 'el', 'los', 'las', 'con', 'en', 'y', 'por', 'a', 'al'}


def _palabras(texto):
    return {palabra for palabra in re.findall(r'\w+', texto.lower()) if palabra not in _VACIAS}


def _copiar_campos(objeto, excluir):
    return {
        campo.name: getattr(objeto, campo.name)
        for campo in objeto._meta.concrete_fields
        if not campo.primary_key and campo.name not in excluir
    }


@transaction.atomic
def copiar_proceso(receta, *, producto, codigo, nombre, origen, instrucciones):
    """Copia completa de un proceso para otro producto: etapas, insumos, salidas y programas."""
    copia = Receta.objects.create(
        **_copiar_campos(receta, {'codigo', 'nombre', 'producto', 'familia', 'instrucciones', 'origen',
                                  'derivado_de', 'creado_en', 'actualizado_en'}),
        codigo=codigo, nombre=nombre, producto=producto, familia=producto.familia,
        instrucciones=instrucciones, origen=origen, derivado_de=receta,
    )
    copia.software.set(receta.software.all())
    etapas = {}
    for etapa in receta.etapas.order_by('orden'):
        etapas[etapa.pk] = EtapaReceta.objects.create(receta=copia, **_copiar_campos(etapa, {'receta'}))
    for insumo in receta.insumos.all():
        InsumoReceta.objects.create(
            receta=copia, etapa=etapas.get(insumo.etapa_id), **_copiar_campos(insumo, {'receta', 'etapa'}),
        )
    for salida in receta.salidas.exclude(producto=producto):
        SalidaReceta.objects.create(
            receta=copia, etapa=etapas.get(salida.etapa_id), **_copiar_campos(salida, {'receta', 'etapa'}),
        )
    return copia


def _raices(texto):
    """Las palabras sin plural, para que «Néctares» y «Néctar de tomate» se reconozcan."""
    raices = set()
    for palabra in _palabras(texto):
        if palabra.endswith('es') and len(palabra) > 4:
            palabra = palabra[:-2]
        elif palabra.endswith('s') and len(palabra) > 3:
            palabra = palabra[:-1]
        raices.add(palabra)
    return raices


def _es_nombre_generico(producto, familia):
    """«Chorizo» ya está en «Chorizo parrillero»: es el mismo producto con su nombre de catálogo."""
    raices = _raices(producto.nombre)
    return any(otro.pk != producto.pk and raices < _raices(otro.nombre) for otro in familia)


def plantilla_para(producto, recetas):
    """El proceso de referencia de su familia que más se parece al producto: por nombre y, a igual nombre, por unidad."""
    candidatas = sorted(
        (receta for receta in recetas if receta.familia_id == producto.familia_id),
        key=lambda receta: receta.codigo,
    )
    if not candidatas:
        return None
    palabras = _palabras(producto.nombre)
    return max(candidatas, key=lambda receta: (
        len(palabras & _palabras(f'{receta.producto.nombre} {receta.nombre}')),
        receta.producto.unidad_medida == producto.unidad_medida,
    ))


def procesos_por_derivar(unidad, plantillas=None, sin_derivar=()):
    """Productos terminados sin proceso y la plantilla de la que partirían.

    plantillas: {nombre del producto: código del proceso} cuando el de su familia
    no le corresponde. sin_derivar: nombres que la planta no puede fabricar.
    """
    plantillas = plantillas or {}
    recetas = list(
        Receta.objects.filter(unidad=unidad, activa=True, origen__in=('referencia', 'validado'))
        .select_related('producto')
    )
    por_codigo = {receta.codigo: receta for receta in recetas}
    con_proceso = set(Receta.objects.filter(unidad=unidad).values_list('producto_id', flat=True))
    familias = {}
    for producto in Producto.objects.filter(unidad=unidad, activo=True, familia__isnull=False):
        familias.setdefault(producto.familia_id, []).append(producto)
    pendientes = []
    productos = (
        Producto.objects.filter(unidad=unidad, tipo='terminado', activo=True, publico=True, familia__isnull=False)
        .exclude(pk__in=con_proceso)
        .select_related('familia')
        .order_by('familia__orden', 'codigo')
    )
    for producto in productos:
        if producto.nombre in sin_derivar:
            continue
        if producto.nombre in plantillas:
            plantilla = por_codigo.get(plantillas[producto.nombre])
        elif _es_nombre_generico(producto, familias[producto.familia_id]):
            continue
        else:
            plantilla = plantilla_para(producto, recetas)
        if plantilla is not None:
            pendientes.append((producto, plantilla))
    return pendientes


def derivar_procesos(unidad, plantillas=None, sin_derivar=()):
    """Crea el proceso derivado de cada producto que no tiene; devuelve los creados."""
    creados = []
    for producto, plantilla in procesos_por_derivar(unidad, plantillas, sin_derivar):
        codigo = producto.codigo.replace('-PRD-', '-REC-DER-', 1)[:50]
        if Receta.objects.filter(codigo=codigo).exists():
            continue
        creados.append(copiar_proceso(
            plantilla,
            producto=producto,
            codigo=codigo,
            nombre=f'{producto.nombre} · derivado de {plantilla.producto.nombre.lower()}',
            origen='derivado',
            instrucciones=(
                f'Proceso derivado de «{plantilla.nombre}»: conserva sus etapas, equipos y controles como punto '
                f'de partida. Ajusta la formulación, los tiempos, los rendimientos y los límites a '
                f'{producto.nombre.lower()} y pide a la planta que lo valide antes de producir.'
            ),
        ))
    return creados
