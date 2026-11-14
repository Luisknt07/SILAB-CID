"""Evidencias de una práctica ejecutada: fotografías, informes, productos.

Se reciben desde el formulario de ejecución (FT03) y se sirven solo a quien
puede ver la planificación: aparecen estudiantes identificados, así que no se
enlazan por la ruta pública de medios.
"""

from collections import Counter
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from apps.formacion.models.practicas import EvidenciaPractica

EXTENSIONES_EVIDENCIA = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.heic', '.mp4', '.webm',
    '.doc', '.docx', '.xls', '.xlsx', '.pptx', '.csv', '.txt', '.zip',
}
MAXIMO_BYTES_EVIDENCIA = 25 * 1024 * 1024
MAXIMO_EVIDENCIAS = 30
TIPOS_VALIDOS = {clave for clave, _ in EvidenciaPractica.TIPOS}


def registrar_evidencias(request, ejecucion):
    """Aplica lo que trae el formulario: archivos nuevos y bajas marcadas.

    Lanza ValidationError con un mensaje para la persona; no guarda nada si
    algo no pasa.
    """
    nuevos = list(request.FILES.getlist('evidencias'))
    tipo = request.POST.get('evidencia_tipo') or 'otro'
    descripcion = (request.POST.get('evidencia_descripcion') or '').strip()
    try:
        eliminar = {int(valor) for valor in request.POST.getlist('evidencias_eliminar') if valor}
    except (TypeError, ValueError) as error:
        raise ValidationError('Una de las evidencias marcadas para retirar no es válida.') from error

    if tipo not in TIPOS_VALIDOS:
        raise ValidationError('Elige el tipo de evidencia que estás adjuntando.')
    if nuevos and not descripcion:
        raise ValidationError('Describe la evidencia: qué muestra, quiénes aparecen y cuándo se tomó.')
    if len(descripcion) > 255:
        raise ValidationError('La descripción de la evidencia no puede superar 255 caracteres.')
    for archivo in nuevos:
        if Path(archivo.name).suffix.lower() not in EXTENSIONES_EVIDENCIA:
            raise ValidationError(f'El archivo {archivo.name} no tiene un formato admitido como evidencia.')
        if archivo.size > MAXIMO_BYTES_EVIDENCIA:
            raise ValidationError(f'El archivo {archivo.name} supera el máximo de 25 MB.')

    existentes = ejecucion.evidencias.filter(pk__in=eliminar)
    if existentes.count() != len(eliminar):
        raise ValidationError('Una de las evidencias marcadas ya no pertenece a esta ejecución.')
    if ejecucion.evidencias.count() - len(eliminar) + len(nuevos) > MAXIMO_EVIDENCIAS:
        raise ValidationError(f'Una ejecución conserva como máximo {MAXIMO_EVIDENCIAS} evidencias.')

    existentes.delete()
    for archivo in nuevos:
        EvidenciaPractica.objects.create(
            ejecucion=ejecucion,
            tipo=tipo,
            archivo=archivo,
            nombre_original=archivo.name[:255],
            extension=Path(archivo.name).suffix.lower(),
            tipo_contenido=(getattr(archivo, 'content_type', '') or '')[:120],
            tamano=archivo.size,
            descripcion=descripcion,
            subido_por=request.user,
        )


def resumen_evidencias(ejecucion):
    """«2 fotografías identificadas, 1 informe de estudiante» o «Sin evidencias»."""
    conteo = Counter(evidencia.get_tipo_display() for evidencia in ejecucion.evidencias.all())
    if not conteo:
        return 'Sin evidencias'
    return ', '.join(f'{cantidad} × {nombre}' for nombre, cantidad in sorted(conteo.items()))


@login_required
def ver_evidencia_view(request, slug, evidencia_id):
    """Entrega el archivo a quien puede ver la planificación de la práctica."""
    from apps.formacion.presentation.practicas import _obtener_plan_visible

    evidencia = get_object_or_404(
        EvidenciaPractica.objects.select_related('ejecucion__planificacion__unidad'),
        pk=evidencia_id, ejecucion__planificacion__unidad__slug=slug,
    )
    _obtener_plan_visible(request, slug, evidencia.ejecucion.planificacion_id)
    return FileResponse(
        evidencia.archivo.open('rb'),
        as_attachment=request.GET.get('descargar') == '1',
        filename=evidencia.nombre_original,
    )
