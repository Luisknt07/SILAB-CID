"""Emisión, envío autenticado y aprobación documental sin descargar ni volver a cargar."""
from apps.core.gobernanza import es_revisor_institucional
import hashlib
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.presentation.expediente_operaciones import comando


def admite_aprobacion_en_linea(documento):
    from .perfil_unidades import es_unidad_auditable
    return bool(documento.exigido.requiere_firma and documento.exigido.generable
                and not documento.exigido.es_anexo and es_unidad_auditable(documento.unidad))


def url_verificacion(token):
    from .expediente_operaciones import _peticion_actual
    ruta = reverse('verificar_documento_qr', args=[token])
    request = _peticion_actual.get()
    return request.build_absolute_uri(ruta) if request else settings.SITE_URL.rstrip('/') + ruta


def preparar_emision(documento, usuario):
    documento.__dict__.pop('_contexto_protocolo', None)
    if admite_aprobacion_en_linea(documento):
        documento._token_emision = uuid4()
        documento._emisor_emision = usuario


def sellar_documento(contenido, documento, usuario):
    """El bloque QR se integra con los responsables dentro del propio documento."""
    if not getattr(documento, '_token_emision', None):
        return contenido
    from pypdf import PdfReader
    from .validacion_pdf import _formulario
    if not any(_formulario(p) for p in PdfReader(BytesIO(contenido)).pages):
        raise ValidationError('No se generó el bloque de validación del documento.')
    return contenido

def registrar_emision(documento, usuario):
    token = getattr(documento, '_token_emision', None)
    if not token:
        return
    documento._constancia_qr = ConstanciaDocumento.objects.create(token=token, documento=documento, recurso=documento.recurso,
        version=documento.version, sha256=documento.recurso.hash_sha256, titulo=documento.nombre_documental,
        unidad_nombre=documento.unidad.nombre,
        periodo=('Documento permanente' if documento.exigido.fuente_reporte in ('protocolo', 'reglamento')
                 else documento.etiqueta_corte),
        emitido_por=usuario,
        emisor_nombre=usuario.get_full_name() or usuario.get_username(), emisor_cedula=cedula_del_usuario(usuario),
        contenido_emitido=getattr(documento, '_contenido_emitido', {}))
    documento.verificacion_qr = token
    documento.save(update_fields=['verificacion_qr'])


def cedula_del_usuario(usuario):
    from django.core.exceptions import ObjectDoesNotExist
    try:
        return str(usuario.profile.cedula or '').strip()
    except ObjectDoesNotExist:
        return ''


def comprobar_emision(documento, *, inspeccionar=True):
    if not documento.verificacion_qr or not documento.recurso_id:
        raise ValidationError('Genera el documento actualizado para enviarlo desde la plataforma.')
    constancia = ConstanciaDocumento.objects.filter(token=documento.verificacion_qr,
        documento=documento, recurso_id=documento.recurso_id, version=documento.version).first()
    if not constancia or constancia.sha256 != documento.recurso.hash_sha256:
        raise ValidationError('La constancia no corresponde a la versión actual del documento.')
    if not documento.recurso.activo or documento.recurso.estado == 'obsoleto':
        raise ValidationError('Esta versión está retirada; genera la versión vigente.')
    if inspeccionar:
        try:
            with documento.recurso.archivo.open('rb') as archivo:
                if hashlib.sha256(archivo.read()).hexdigest() != constancia.sha256:
                    raise ValidationError('El archivo fue modificado después de su emisión.')
        except (OSError, ValueError) as error:
            raise ValidationError('El archivo emitido no está disponible. Revisa el documento antes de continuar.') from error
    return constancia


def completar_constancias(documentos):
    """Una carga por listado, sin abrir archivos ni recalcular aprobaciones."""
    pendientes = [d for d in documentos if getattr(d, 'verificacion_qr', None)
        and (not hasattr(d, '_constancia_qr') or
             getattr(d._constancia_qr, 'token', None) != d.verificacion_qr)]
    if pendientes:
        constancias = {c.token: c for c in ConstanciaDocumento.objects.filter(
            token__in=[d.verificacion_qr for d in pendientes])}
        for d in pendientes:
            d._constancia_qr = constancias.get(d.verificacion_qr)


def lectura_aprobacion_qr(documento):
    """Estado de la versión actual; los listados precargan su constancia."""
    if not getattr(documento, 'verificacion_qr', None):
        return None
    c = getattr(documento, '_constancia_qr', None)
    actual = bool(c and c.documento_id == documento.pk and c.token == documento.verificacion_qr
        and c.version == documento.version and c.recurso_id == documento.recurso_id
        and documento.recurso_id and c.sha256 == documento.recurso.hash_sha256
        and documento.recurso.activo and documento.recurso.estado == 'vigente')
    rechazado = bool(actual and (documento.estado == 'observado' or c.observado_en))
    aprobado = bool(actual and not rechazado and c.aprobado_en and documento.estado == 'validado')
    enviado = bool(actual and c.enviado_en and documento.estado == 'validado')
    estado = 'aprobado' if aprobado else 'rechazado' if rechazado else 'pendiente' if enviado else 'preparado'
    etiqueta = {'aprobado': 'Aprobado', 'rechazado': 'Rechazado',
        'pendiente': 'Pendiente de revisión', 'preparado': 'Sin envío vigente'}[estado]
    return dict(estado=estado, etiqueta=etiqueta, aprobado=aprobado, rechazado=rechazado,
        enviado=enviado, puede_aprobar=enviado and not aprobado, puede_rechazar=enviado,
        color='verde' if aprobado else 'rojo' if rechazado else 'amarillo',
        fecha=(c.observado_en or documento.validado_en) if rechazado else c.aprobado_en if aprobado else None,
        actor=c.aprobador_nombre if aprobado else '')


def declaracion_nativa(documento):
    from .expediente_archivos import identidad_documental
    return dict(identidad_documental(documento), revisado=True, version=str(documento.version))


@comando
def enviar_documento_qr(documento, usuario, *, token, version):
    if str(documento.verificacion_qr) != str(token) or str(documento.version) != str(version):
        raise ValidationError('La versión cambió. Abre el documento actual antes de enviarlo.')
    comprobar_emision(documento)
    if documento.estado == 'validado':
        return
    from .expediente import validar_documento
    validar_documento(documento, usuario, declaracion_correspondencia=declaracion_nativa(documento))


@comando
def generar_y_enviar_qr(documento, usuario):
    from .expediente import generar_documento
    generar_documento(documento, usuario)
    enviar_documento_qr(documento, usuario, token=documento.verificacion_qr, version=documento.version)


@comando
def decidir_documento_qr(documento, usuario, *, token, version, decision, observacion=''):
    if not es_revisor_institucional(usuario):
        raise ValidationError('La revisión requiere designación institucional vigente.')
    if str(documento.verificacion_qr) != str(token) or str(documento.version) != str(version):
        raise ValidationError('La versión cambió. Vuelve a abrir la revisión.')
    constancia = comprobar_emision(documento)
    if documento.estado != 'validado' or constancia.enviado_en is None:
        raise ValidationError('La unidad debe enviar esta versión antes de su aprobación.')
    if decision == 'observar':
        from .expediente import observar_documento
        observar_documento(documento, usuario, observacion, hasta=timezone.now() + timedelta(days=14))
        constancia.observado_en = timezone.now()
        constancia.save(update_fields=['observado_en'])
        documento._constancia_qr = constancia
        return
    if decision != 'aprobar':
        raise ValidationError('Selecciona aprobar u observar.')
    if constancia.aprobado_en and not constancia.observado_en:
        return
    from .expediente import anexos_sin_revisar
    if documento.exigido.codigo != 'INFORME-SEMESTRAL' and anexos_sin_revisar(documento):
        raise ValidationError('Hay anexos con incidencias. Devuelve la observación para que la unidad los corrija antes de aprobar.')
    from .conformidad_planes import CODIGOS, confirmar_conformidad
    from .conformidad_permanente import es_permanente, aprobar_permanente
    from .expediente import recibir_documento
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        from .evaluacion_cierre import cierre_archivado
        cierre = cierre_archivado(documento)
        if not cierre or not cierre.get('plan_aprobado') or not cierre.get('completo') or cierre.get('demostracion'):
            raise ValidationError('Antes de aprobar el cierre, comprueba la planificación del mismo semestre '
                'y los apartados del informe. Puedes devolver una observación a la unidad.')
    if documento.exigido.codigo in CODIGOS:
        confirmar_conformidad(documento, usuario, documento.version, constancia.sha256, confirmado=True,
            declaracion_correspondencia=declaracion_nativa(documento))
    elif not es_permanente(documento):
        recibir_documento(documento, usuario, declaracion_correspondencia=declaracion_nativa(documento))
        if documento.exigido.codigo == 'INFORME-SEMESTRAL':
            from .evaluacion_cierre import confirmar_cierre
            confirmar_cierre(documento, usuario, documento.version, constancia.sha256, confirmado=True)
    constancia.aprobado_por = usuario
    constancia.aprobador_nombre = usuario.get_full_name() or usuario.get_username()
    constancia.aprobador_cedula = cedula_del_usuario(usuario)
    constancia.aprobado_en = timezone.now()
    constancia.save(update_fields=['aprobado_por', 'aprobador_nombre', 'aprobador_cedula', 'aprobado_en'])
    if es_permanente(documento):
        aprobar_permanente(documento, usuario, documento.version, constancia.sha256, confirmado=True,
            declaracion_correspondencia=declaracion_nativa(documento))
    from .validacion_pdf import copia_aprobada
    with documento.recurso.archivo.open('rb') as archivo:
        copia_aprobada(archivo.read(), constancia)
    documento._constancia_qr = constancia
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='aprobar', objeto=constancia,
        descripcion='aprobacion_en_plataforma', nuevos=dict(documento_id=documento.pk,
            recurso_id=documento.recurso_id, version=documento.version, sha256=constancia.sha256,
            sha256_aprobado=constancia.sha256_aprobado,
            aprobado_en=constancia.aprobado_en.isoformat(), aprobador_nombre=constancia.aprobador_nombre))


def estado_constancia(constancia):
    d = constancia.documento
    if not d.recurso_id:
        return 'RETIRADO'
    if d.verificacion_qr != constancia.token or d.recurso_id != constancia.recurso_id or d.version != constancia.version:
        return 'SUSTITUIDO'
    if not constancia.recurso.activo or constancia.recurso.estado == 'obsoleto':
        return 'RETIRADO'
    if constancia.recurso.hash_sha256 != constancia.sha256:
        return 'NO VERIFICABLE'
    if d.estado == 'observado' or constancia.observado_en:
        return 'OBSERVADO'
    if constancia.aprobado_en:
        return 'VIGENTE'
    return 'PENDIENTE DE APROBACIÓN' if constancia.enviado_en else 'PREPARADO · SIN ENVÍO'
