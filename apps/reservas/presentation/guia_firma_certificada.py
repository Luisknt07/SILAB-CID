"""Versión firmada con certificado electrónico (FirmaEC) de una guía aprobada.

Dentro de la plataforma la guía ya queda validada por dos firmas internas con
huella SHA-256: la aceptación electrónica de la persona autora al enviar y la
aprobación del responsable de la unidad. Cuando se necesita validez externa
(archivo institucional, auditoría, entrega a terceros), la persona autora
descarga el PDF aprobado, lo firma con FirmaEC —o con cualquier certificado
acreditado en Ecuador— y carga aquí el archivo firmado.

Se comprueba que el archivo sea un PDF con una firma digital embebida
(PAdES: ``/ByteRange`` y un diccionario ``/Type /Sig`` o un sello de tiempo
``/DocTimeStamp``) y se guarda su huella SHA-256 para la trazabilidad. La
validez del certificado frente a la autoridad certificadora se verifica con
la propia herramienta FirmaEC; la plataforma no custodia claves privadas.
"""

import hashlib
import re
import logging
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

TAMANO_MAXIMO = 20 * 1024 * 1024
PATRON_FIRMA = re.compile(rb'/Type\s*/Sig\b')
PATRON_SELLO = re.compile(rb'/Type\s*/DocTimeStamp\b')


def validar_pdf_firmado(archivo):
    """Devuelve ``{"firmas", "sha256", "tamano"}`` o lanza ``ValueError``."""
    nombre = str(getattr(archivo, 'name', '') or '')
    if not nombre.lower().endswith('.pdf'):
        raise ValueError('Carga el PDF firmado (archivo con extensión .pdf).')
    tamano = getattr(archivo, 'size', None)
    if tamano and tamano > TAMANO_MAXIMO:
        raise ValueError('El PDF firmado no puede superar 20 MB.')
    archivo.seek(0)
    try:
        datos = archivo.read(TAMANO_MAXIMO + 1)
    finally:
        archivo.seek(0)
    if len(datos) > TAMANO_MAXIMO:
        raise ValueError('El PDF firmado no puede superar 20 MB.')
    if not datos.startswith(b'%PDF'):
        raise ValueError('El archivo no es un PDF válido.')
    firmas = len(PATRON_FIRMA.findall(datos)) + len(PATRON_SELLO.findall(datos))
    if not firmas or b'/ByteRange' not in datos:
        raise ValueError(
            'El PDF no contiene una firma electrónica. Fírmalo con FirmaEC y vuelve a cargarlo.'
        )
    return {
        'firmas': firmas,
        'sha256': hashlib.sha256(datos).hexdigest(),
        'tamano': len(datos),
    }


def registrar_pdf_firmado(guia, archivo, usuario, *, request=None):
    """Conserva la carga anterior y confirma el nuevo archivo junto a su auditoría.

    La detección de firma es estructural; no certifica su validez criptográfica.
    """
    from apps.reservas.models.reservas import GuiaActividadReserva
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.gestion_unidades.presentation.permisos import puede_cargar_guia_firmada

    detalle = validar_pdf_firmado(archivo)
    nuevo = None
    try:
        with transaction.atomic():
            actual = GuiaActividadReserva.objects.select_for_update().get(pk=guia.pk)
            if not actual.activo or not actual.es_estructurada or not puede_cargar_guia_firmada(usuario, actual):
                raise ValueError('No tienes permiso para cargar la versión firmada de esta guía.')
            if actual.estado_publicacion not in {'revision', 'publicada'}:
                raise ValueError('La guía debe estar en revisión o aprobada.')
            anteriores = {
                'archivo_firmado': actual.archivo_firmado.name,
                'firmado_por': actual.firmado_por_id,
                'firmado_en': actual.firmado_en.isoformat() if actual.firmado_en else None,
                'resumen': actual.firma_certificada_resumen,
            }
            actual.archivo_firmado.save(f'firma-{uuid4().hex}.pdf', archivo, save=False)
            nuevo = actual.archivo_firmado
            actual.firmado_por = usuario
            actual.firmado_en = timezone.now()
            plural = 's' if detalle['firmas'] != 1 else ''
            actual.firma_certificada_resumen = (
                f"{detalle['firmas']} firma{plural} detectada{plural} · SHA-256 {detalle['sha256']}"
            )
            actual.save(update_fields=[
                'archivo_firmado', 'firmado_por', 'firmado_en',
                'firma_certificada_resumen', 'actualizado_en',
            ])
            registrar_auditoria(
                request, usuario=usuario, unidad=actual.actividad.unidad, accion='actualizar', objeto=actual,
                descripcion=f'PDF firmado cargado para la guía v{actual.numero_version}.',
                anteriores=anteriores,
                nuevos={'archivo_firmado': nuevo.name, 'sha256': detalle['sha256'],
                        'tamano': detalle['tamano'], 'firmas_detectadas': detalle['firmas']},
            )
    except Exception:
        if nuevo is not None:
            nuevo.close()
            try:
                nuevo.storage.delete(nuevo.name)
            except OSError:
                logging.getLogger(__name__).exception('No se pudo retirar una carga fallida de guía.')
        raise
    guia.refresh_from_db()
    return detalle
