"""Compatibilidad exclusiva para la migración histórica 0128.

Los modelos académicos experimentales fueron retirados. Estas funciones se
conservan porque Django debe poder importar las rutas de carga serializadas en
esa migración antes de ejecutar la migración correctiva que elimina sus tablas.
"""


def silabo_upload_to(instance, filename):
    periodo = getattr(getattr(instance, "periodo", None), "codigo", "sin-periodo")
    codigo = getattr(instance, "codigo_asignatura", "sin-codigo") or "sin-codigo"
    return f"academico/silabos/{periodo}/{codigo}/{filename}"


def guia_practica_upload_to(instance, filename):
    practica_id = getattr(instance, "practica_id", None) or "sin-practica"
    numero = getattr(instance, "numero", None) or 1
    return f"academico/practicas/{practica_id}/versiones/{numero}/{filename}"
