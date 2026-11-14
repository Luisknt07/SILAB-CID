"""Comprueba consumidores del catalogo con conteos; no modifica ni expone personas."""

from django.apps import apps
from django.db.models import Q

from .catalogos import catalogo_actual, carreras, facultades
from .niveles import niveles


def auditar_catalogo(*, database="default", catalogo=None, niveles_propuestos=None):
    catalogo = catalogo or catalogo_actual()
    opciones = {
        facultades: dict(catalogo.facultades),
        carreras: dict([(c, e) for c, e, _ in catalogo.carreras] + list(catalogo.carreras_historicas)),
    }
    if niveles_propuestos is not None:
        opciones[niveles] = dict(niveles_propuestos.niveles + niveles_propuestos.historicos)
    resultados = []
    for modelo in apps.get_models():
        campos = {}
        for campo in modelo._meta.fields:
            proveedor = campo.deconstruct()[3].get("choices")
            if proveedor in (facultades, carreras, niveles):
                campos[campo.name] = opciones[proveedor] if proveedor in opciones else dict(proveedor())
        if not campos:
            continue
        consulta = modelo._default_manager.using(database)
        for nombre, conocidos in campos.items():
            desconocidos = consulta.exclude(**{f"{nombre}__in": (*conocidos, "")}).exclude(
                **{f"{nombre}__isnull": True}
            ).count()
            resultados.append({"modelo": modelo._meta.label_lower, "campo": nombre,
                               "codigos_desconocidos": desconocidos, "relaciones_incompatibles": 0})
        for nombre in campos:
            if not nombre.startswith("carrera"):
                continue
            facultad = "facultad" + nombre[len("carrera"):]
            if facultad not in campos:
                continue
            compatibles = Q(pk__in=[])
            for codigo, _, dependencia in catalogo.carreras:
                compatibles |= Q(**{nombre: codigo, facultad: dependencia})
            incompatibles = consulta.filter(**{f"{nombre}__in": [codigo for codigo, _, _ in catalogo.carreras]})
            incompatibles = incompatibles.exclude(**{facultad: ""}).exclude(**{f"{facultad}__isnull": True})
            cantidad = incompatibles.exclude(compatibles).count()
            next(fila for fila in resultados if fila["modelo"] == modelo._meta.label_lower
                 and fila["campo"] == nombre)["relaciones_incompatibles"] = cantidad
    return resultados
