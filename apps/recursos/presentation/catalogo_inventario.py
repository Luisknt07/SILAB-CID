"""Ayudantes del catálogo del inventario: nombres comparables, familia de producto y foto de familia.

Los usan la sincronización de las fichas de área, el importador del reporte de bienes de bodega y el
lector: un mismo criterio para saber cuándo dos nombres son el mismo equipo o el mismo programa.
"""
import re
import unicodedata

from apps.gestion_unidades.management.fichas_area.familias_equipo import FAMILIAS, familia_de


def normalizar(texto):
    sin_tildes = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', sin_tildes.lower())).strip()


def clave_de_programa(nombre):
    """El nombre del programa sin lo que no lo distingue: el texto entre paréntesis y la versión o el año
    final («Autodesk Fusion 2026» y «Autodesk Fusion (por verificar)» son el mismo programa)."""
    palabras = normalizar(re.sub(r'\([^)]*\)', ' ', nombre or '')).split()
    while len(palabras) > 1 and re.fullmatch(r'v?\d+[a-z]?', palabras[-1]):
        palabras.pop()
    return ' '.join(palabras)


def asignar_familia(tipo, resumen, *nombres):
    """La familia de producto del tipo, por su nombre o el de su ficha; la que puso la unidad se respeta."""
    from django.utils.text import slugify

    from apps.recursos.models.equipos import FamiliaEquipo

    if tipo.familia_id:
        return
    nombre = next((familia_de(candidato) for candidato in nombres if familia_de(candidato)), '')
    if not nombre:
        return
    icono, grupo = FAMILIAS[nombre]
    familia, _creada = FamiliaEquipo.objects.get_or_create(
        nombre=nombre, defaults={'slug': slugify(nombre)[:140], 'icono': icono, 'grupo': grupo})
    tipo.familia = familia
    tipo.save(update_fields=['familia'])
    resumen['tipos con familia'] += 1


FOTO_DE_LA_FAMILIA = 'Foto de otro equipo de su familia'
FOTO_DEL_TIPO = 'Foto del tipo de equipo'  # la que cargar_medios_familias pone a toda la familia


def credito_heredado(credito):
    """«Foto de otro equipo de su familia», con el crédito original si lo tiene, sin repetir el aviso."""
    original = (credito or '').strip()
    while original.startswith(FOTO_DE_LA_FAMILIA):
        original = original[len(FOTO_DE_LA_FAMILIA):].lstrip(' ·').strip()
    return (f'{FOTO_DE_LA_FAMILIA} · {original}' if original else FOTO_DE_LA_FAMILIA)[:300]


def heredar_foto(tipo, resumen):
    """Un equipo sin foto (registrado desde bodega o el lector) toma la de catálogo de otro de su familia."""
    tipo.refresh_from_db(fields=['familia', 'imagen', 'imagen_catalogo'])
    if tipo.imagen or tipo.imagen_catalogo or not tipo.familia_id:
        return
    from apps.recursos.models.equipos import EquiposServicios

    # Solo de una foto original de la familia: heredar de una heredada repetía el aviso en el crédito.
    modelo = (EquiposServicios.objects.filter(familia_id=tipo.familia_id).exclude(imagen_catalogo='')
              .exclude(credito_imagen__startswith=FOTO_DE_LA_FAMILIA).exclude(credito_imagen__startswith=FOTO_DEL_TIPO)
              .exclude(pk=tipo.pk).order_by('codigo').first())
    if modelo is None:
        return
    # El crédito dice que la foto es de otro equipo de la familia, no de este modelo.
    tipo.imagen_catalogo, tipo.credito_imagen, tipo.fuente_imagen = (
        modelo.imagen_catalogo, credito_heredado(modelo.credito_imagen), modelo.fuente_imagen)
    tipo.save(update_fields=['imagen_catalogo', 'credito_imagen', 'fuente_imagen'])
    resumen['tipos con foto de su familia'] += 1


# Palabras que no distinguen un equipo de otro al comparar nombres.
VACIAS = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'o', 'con', 'para', 'por', 'en', 'a', 'maquina', 'equipo',
          'escritorio', 'portatil', 'digital'}
# Distintas palabras para lo mismo, llevadas a una sola.
SINONIMOS = {'gafa': 'visor', 'casco': 'visor', 'headset': 'visor', 'lente': 'visor', 'scanner': 'escaner',
             'escanner': 'escaner', 'secadora': 'secador', 'computador': 'computadora', 'workstation': 'estacion',
             'work': 'estacion', 'station': '', 'cortadora': 'laser', 'grabadora': 'laser', 'tactil': 'pantalla',
             'monitor': 'pantalla'}
# Rasgos que separan tecnologías: si el bien tiene uno y el candidato otro del mismo grupo, no son el mismo.
EXCLUYENTES = (
    {'resina', 'fdm', 'filamento', 'sls', 'uv', 'dtf'},
    {'fibra', 'co2', 'diodo'},
    {'escaner', 'laser'},
    {'virtual', 'mixta', 'aumentada', 'pantalla'},
)


def raiz(palabra):
    """La palabra en singular y sin variantes («secadoras» → «secador», «gafas» → «visor»)."""
    for sufijo in ('es', 's'):
        if len(palabra) > 4 and palabra.endswith(sufijo) and not palabra.endswith('ss'):
            palabra = palabra[:-len(sufijo)]
            break
    return SINONIMOS.get(palabra, palabra)


def palabras(texto):
    return {raiz(palabra) for palabra in normalizar(texto).split()
            if palabra not in VACIAS and len(palabra) > 1} - {''}


def nucleo(texto):
    """La palabra que dice qué es el equipo: la primera que cuenta («Cortadora láser de fibra» → «laser»)."""
    return next((raiz(palabra) for palabra in normalizar(texto).split()
                 if palabra not in VACIAS and len(palabra) > 1 and raiz(palabra)), '')


def se_excluyen(bien, candidato):
    return any((bien & grupo) and (candidato & grupo) and not (bien & candidato & grupo) for grupo in EXCLUYENTES)


def semejanza(buscadas, nombre, extra=frozenset(), referencia=frozenset()):
    """Cuánto se parece un nombre a lo buscado (0 a 1,3): palabras en común y, además, marca o modelo."""
    comunes = len(buscadas & nombre) / max(1, len(buscadas | nombre))
    return comunes + (0.3 if extra and extra & referencia else 0)
