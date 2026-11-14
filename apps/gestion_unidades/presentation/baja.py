"""Retirar una unidad: siempre se puede desactivar; eliminar, solo si no tiene historial.

Desactivada, la unidad deja de aparecer en el portal y todo lo suyo se conserva.
Eliminarla borra en cascada cuanto cuelga de ella, así que solo se permite cuando
lo único que tiene es la configuración con la que nació (una unidad creada por
error): cualquier otro registro es historial y se perdería.
"""
from django.contrib.admin.utils import NestedObjects
from django.db import router

# Lo que la plataforma crea sola con cada unidad, o que solo la configura: no es historial.
CONFIGURACION_INICIAL = frozenset({
    'ModuloUnidad', 'ReglamentoUnidad', 'ConfiguracionOperativaUnidad', 'HorarioOperacionUnidad',
    'PerfilLaboratorio', 'PerfilPlantaPiloto', 'PerfilCentroExperimental', 'PerfilObservatorio',
    'PerfilPlataformaTecnologica', 'AjusteSeccionPlanta',
})


def _es_historial(objeto):
    """Un documento del expediente pendiente, sin nada entregado, lo genera el calendario: no es historial."""
    if objeto._meta.concrete_model.__name__ == 'DocumentoExpediente':
        return objeto.estado != 'pendiente' or bool(objeto.recurso_id)
    return True


def historial_de(unidad):
    """Lo que la unidad acumuló más allá de su configuración inicial, como [(qué, cuántos)]; vacío, se puede eliminar."""
    colector = NestedObjects(using=router.db_for_write(type(unidad)))
    colector.collect([unidad])
    cuentas = {}
    objetos = [objeto for grupo in colector.model_objs.values() for objeto in grupo]
    # Lo protegido tampoco se puede borrar: también es historial.
    for objeto in [*objetos, *colector.protected]:
        opciones = objeto._meta
        if (opciones.concrete_model is unidad._meta.concrete_model or opciones.auto_created
                or opciones.concrete_model.__name__ in CONFIGURACION_INICIAL or not _es_historial(objeto)):
            continue
        nombre = str(opciones.verbose_name_plural)
        cuentas[nombre] = cuentas.get(nombre, 0) + 1
    return sorted(cuentas.items(), key=lambda cuenta: (-cuenta[1], cuenta[0]))
