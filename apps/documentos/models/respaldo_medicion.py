"""Comprobación básica de contenido antes de acreditar una evidencia."""
import io
import hashlib
import json
from datetime import datetime, timezone as datetime_timezone
from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils import timezone

ESQUEMA_VERIFICACION = 2


def es_unidad_auditable(unidad):
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable as auditable
    return auditable(unidad)


def requiere_inspecciones_fisicas(unidad):
    from apps.documentos.presentation.perfil_unidades import base_de
    return base_de(unidad) in ('laboratorios', 'plantas_piloto', 'centro_experimental')


def alcances_inventario(unidad):
    """El observatorio revisa su infraestructura digital, sin exigir insumos químicos."""
    from apps.documentos.presentation.perfil_unidades import base_de
    return ('equipos', 'software', 'espacios') if base_de(unidad) == 'observatorios' else (
        'equipos', 'software', 'espacios', 'insumos')


def fecha_verificacion(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = valor.astimezone(datetime_timezone.utc)
    return valor.isoformat()


def huella_verificacion(evidencia):
    """Congela lo que revisó el responsable, incluidos universo, tramo y atribución.

    El sello se genera en el servicio al registrar la auditoría. Una edición SQL
    posterior o promover un borrador no equivale a una nueva comprobación.
    """
    contenido = {campo: getattr(evidencia, campo) for campo in (
        'unidad_id', 'codigo', 'tipo', 'titulo', 'descripcion', 'responsable_id',
        'recurso_id', 'enlace', 'total_observado', 'alcance', 'detalle', 'estado',
        'demostracion', 'creado_por_id', 'validado_por_id')}
    contenido.update({campo: fecha_verificacion(getattr(evidencia, campo)) for campo in (
        'fecha', 'desde', 'hasta', 'creado_en', 'validado_en')})
    contenido['sha256'] = evidencia.recurso.hash_sha256 if evidencia.recurso_id else ''
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def es_laboratorio(unidad):
    """Incluye tipologías institucionales que reutilizan la base de laboratorios."""
    from apps.documentos.presentation.perfil_laboratorios import es_laboratorio as laboratorio
    return laboratorio(unidad)


def corte_efectivo(unidad, fin):
    return min(fin, timezone.localdate()) if es_unidad_auditable(unidad) else fin


def huella_acta_inventario(evidencia):
    """El alcance revisado no puede ampliarse después de verificar el acta."""
    contenido = dict(codigo=evidencia.codigo, fecha=evidencia.fecha.isoformat(),
                     titulo=evidencia.titulo, descripcion=evidencia.descripcion,
                     responsable=evidencia.responsable_id, alcance=evidencia.alcance,
                     revision_criticidad={k: evidencia.detalle.get(k) for k in (
                         'revision_criticidad', 'revision_criticidad_en', 'equipos_criticidad')}
                     if isinstance(evidencia.detalle, dict) else {})
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def fotografia_criticidad(unidad):
    """Universo actual revisable, con la asignación que determina su alcance."""
    from django.db.models import Q
    from apps.recursos.models.unidades import UnidadEquipo
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True, fecha_baja__isnull=True).distinct().prefetch_related('laboratorios').order_by('pk')
    return [dict(equipo=e.pk, codigo=e.codigo_unidad, criticidad=e.criticidad,
                 laboratorio=e.laboratorio_id,
                 laboratorios=sorted(u.pk for u in e.laboratorios.all()),
                 ubicacion=e.ubicacion_especifica or e.ubicacion_bodega or '') for e in equipos]


def faltantes_desecho(desecho, *, validar_archivo=False, al_corte=None):
    """Trazabilidad declarada; no certifica permisos ni la autorización del gestor."""
    faltantes = []
    for campo, etiqueta in (('clave_listado', 'clave del listado aplicable'), ('origen', 'origen'),
                            ('envase', 'envase')):
        if not str(getattr(desecho, campo) or '').strip():
            faltantes.append(etiqueta)
    if desecho.cantidad is None or desecho.cantidad <= 0:
        faltantes.append('cantidad positiva')
    if not desecho.etiquetado:
        faltantes.append('etiquetado sin confirmar')
    if not desecho.responsable_id:
        faltantes.append('responsable')
    etapa = desecho.etapa
    if al_corte and desecho.fecha_entrega and desecho.fecha_entrega > al_corte:
        etapa = 'almacenado'
    if etapa == 'almacenado' and not desecho.almacenamiento.strip():
        faltantes.append('almacenamiento')
    if etapa == 'entregado':
        for campo, etiqueta in (('fecha_entrega', 'fecha de entrega'), ('gestor_autorizado', 'gestor'),
                                ('licencia_gestor', 'licencia del gestor'), ('manifiesto', 'manifiesto')):
            if not getattr(desecho, campo) or not str(getattr(desecho, campo)).strip():
                faltantes.append(etiqueta)
        if desecho.fecha_entrega and desecho.fecha_entrega < desecho.fecha_generacion:
            faltantes.append('fechas de generación y entrega coherentes')
    if etapa == 'tratado' and not desecho.observaciones.strip():
        faltantes.append('procedimiento y resultado del tratamiento')
    if etapa in ('entregado', 'tratado'):
        etiqueta = 'archivo del manifiesto o acta' if etapa == 'entregado' else 'acta del tratamiento'
        if not desecho.documento:
            faltantes.append(etiqueta)
        elif validar_archivo:
            try:
                validar_respaldo(desecho.documento)
            except ValidationError:
                faltantes.append(etiqueta + ' legible y disponible')
    return faltantes


def validar_respaldo(archivo):
    """Rechaza archivos vacíos, corruptos y páginas sin texto ni imágenes.

    Comprueba contenido legible; la correspondencia con la actividad la confirma
    el responsable y queda registrada en la auditoría.
    """
    try:
        archivo.open('rb')
        datos = archivo.read(25 * 1024 * 1024 + 1)
        archivo.seek(0)
        if not datos or len(datos) > 25 * 1024 * 1024:
            raise ValueError
        extension = Path(archivo.name).suffix.lower()
        if extension == '.pdf':
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(datos), strict=False)
            if pdf.is_encrypted or not pdf.pages or not any(
                    len(''.join((p.extract_text() or '').split())) >= 40 or bool(p.images) for p in pdf.pages):
                raise ValueError
        elif extension in ('.png', '.jpg', '.jpeg'):
            from PIL import Image
            with Image.open(io.BytesIO(datos)) as imagen:
                imagen.verify()
            with Image.open(io.BytesIO(datos)) as imagen:
                extremos = imagen.convert('RGB').getextrema()
                if not any(minimo != maximo for minimo, maximo in extremos):
                    raise ValueError
        else:
            raise ValueError
        return hashlib.sha256(datos).hexdigest()
    except Exception as error:
        raise ValidationError('El respaldo debe ser un PDF o imagen legible con contenido; un archivo vacío no acredita la meta.') from error
    finally:
        archivo.close()
