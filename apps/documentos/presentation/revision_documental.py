"""Acciones comunes para las entregas principales; anexos y consultas conservan su función."""
from apps.core.gobernanza import es_revisor_institucional
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from .expediente_operaciones import comando


@comando
def decidir_desde_listado(documento, usuario, *, version, huella, decision, observacion=''):
    if not es_revisor_institucional(usuario):
        raise ValidationError('La revisión requiere designación institucional vigente.')
    if decision not in ('aprobar', 'rechazar'):
        raise ValidationError('Selecciona aprobar o rechazar.')
    if (documento.exigido.es_anexo or not documento.recurso_id or documento.estado != 'validado'
            or str(documento.version) != str(version) or documento.recurso.hash_sha256 != str(huella or '')):
        raise ValidationError('La entrega cambió o todavía no fue enviada. Abre la versión actual.')
    if documento.verificacion_qr:
        from .aprobacion_en_linea import decidir_documento_qr
        return decidir_documento_qr(documento, usuario, token=documento.verificacion_qr,
            version=version, decision='aprobar' if decision == 'aprobar' else 'observar', observacion=observacion)
    if decision == 'rechazar':
        from .expediente import observar_documento
        return observar_documento(documento, usuario, observacion, hasta=timezone.now() + timedelta(days=14))
    import hashlib
    try:
        with documento.recurso.archivo.open('rb') as archivo:
            if hashlib.sha256(archivo.read()).hexdigest() != huella:
                raise ValidationError('El archivo fue modificado. Revisa su versión vigente.')
    except (OSError, ValueError) as error:
        raise ValidationError('El archivo no está disponible.') from error
    from .expediente_archivos import identidad_documental
    declaracion = dict(identidad_documental(documento), revisado=True, version=str(documento.version))
    from .conformidad_permanente import es_permanente, aprobar_permanente
    if es_permanente(documento):
        return aprobar_permanente(documento, usuario, version, huella, confirmado=True,
            declaracion_correspondencia=declaracion)
    from .conformidad_planes import CODIGOS, confirmar_conformidad
    if documento.exigido.codigo in CODIGOS:
        return confirmar_conformidad(documento, usuario, version, huella, confirmado=True,
            declaracion_correspondencia=declaracion)
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        from .evaluacion_cierre import confirmar_cierre, cierre_archivado
        if not cierre_archivado(documento):
            raise ValidationError('Este informe anterior requiere su evaluación conservada; no dispone de metas archivadas.')
        from .expediente import recibir_documento
        recibir_documento(documento, usuario, declaracion_correspondencia=declaracion)
        return confirmar_cierre(documento, usuario, version, huella, confirmado=True)
    raise ValidationError('Este documento se revisa con su entrega principal.')
