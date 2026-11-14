"""Identidad editorial portable de precargas; no se importa al atender páginas."""
from unicodedata import normalize

from apps.formacion.models.cursos import Curso


def nombre_normalizado(nombre):
    """Conserva tildes, ignora caja y espaciado, unifica Unicode equivalente."""
    return normalize('NFC', ' '.join(nombre.split())).casefold()


def cursos_por_nombres(unidad, nombres):
    """Localiza sólo los candidatos: memoria acotada, sin cargar contenido LMS.

    No depende de UPPER/ILIKE de la base: una colación C puede no convertir
    mayúsculas acentuadas. El orden conserva el primer registro preexistente.
    """
    buscados = {nombre_normalizado(nombre) for nombre in nombres}
    encontrados = {}
    ultimo = 0
    while buscados - encontrados.keys():
        filas = list(Curso.objects.filter(unidad=unidad, pk__gt=ultimo).order_by('pk')
                     .values_list('pk', 'nombre')[:1000])
        for pk, nombre in filas:
            clave = nombre_normalizado(nombre)
            if clave in buscados:
                encontrados.setdefault(clave, pk)
        if len(filas) < 1000:
            break
        ultimo = filas[-1][0]
    return encontrados
