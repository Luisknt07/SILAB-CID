"""Integridad del archivo anexo, independiente de su contenido y sus metas."""
import hashlib

from django.core.exceptions import ValidationError

from apps.recursos.models.recursos import Recurso


def exigir_archivo_anexo(anexo):
    """Comprueba el respaldo vigente sin conceder una revisión de contenido.

    También admite anexos personalizados y archivos externos: no exige una
    procedencia nativa ni que las actividades hayan alcanzado sus metas.
    """
    if not anexo.recurso_id:
        raise ValidationError('Primero genera o carga el anexo: falta su archivo de respaldo.')
    # La instancia del documento puede conservar una relación en caché leída
    # antes de retirar el recurso. Se comprueban sus datos vigentes.
    recurso = Recurso.objects.filter(pk=anexo.recurso_id).first()
    if recurso is None:
        raise ValidationError('El archivo del anexo ya no está disponible.')
    if recurso.unidad_id != anexo.unidad_id:
        raise ValidationError('El archivo del anexo pertenece a otra unidad.')
    if not recurso.activo or recurso.estado == 'obsoleto':
        raise ValidationError('El archivo del anexo está retirado u obsoleto; prepara el respaldo vigente.')
    if recurso.version != anexo.version:
        raise ValidationError('La versión del archivo no corresponde a la del anexo. Revisa el respaldo vigente.')
    if not recurso.archivo:
        raise ValidationError('El anexo no tiene un archivo disponible para revisar.')
    resumen, tamano = hashlib.sha256(), 0
    try:
        with recurso.archivo.open('rb') as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
                resumen.update(bloque)
                tamano += len(bloque)
    except (OSError, ValueError) as error:
        raise ValidationError('El archivo del anexo no está disponible. Revisa su respaldo antes de continuar.') from error
    if not tamano:
        raise ValidationError('El archivo del anexo está vacío; prepara un respaldo con contenido.')
    if resumen.hexdigest() != recurso.hash_sha256:
        raise ValidationError('El archivo del anexo fue modificado y no coincide con su huella archivada.')
    return recurso
