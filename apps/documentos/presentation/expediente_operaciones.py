"""Transacciones, autorización y evidencia de los comandos del expediente."""

from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps
from inspect import signature
from pathlib import Path
import shutil

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.documentos.models.expediente import DocumentoExpediente
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad


_archivos_creados = ContextVar('archivos_creados_expediente', default=None)
_peticion_actual = ContextVar('peticion_expediente', default=None)


def declaracion_actual(documento, declaracion=None, *, etapa=None):
    """Propaga solo una confirmación explícita; una operación interna no inventa revisiones."""
    if declaracion is not None:
        return declaracion
    request = _peticion_actual.get()
    if request is None or request.POST.get('correspondencia_confirmada') != '1':
        return None
    registro = getattr(documento, '_integridad_registro', None) or {}
    if (etapa == 'enviar' and request.POST.get('accion') == 'cargar'
            and registro.get('etapa') == 'cargar' and registro.get('version') == documento.version
            and registro.get('recurso_id') == documento.recurso_id):
        # La confirmación se hizo contra la versión anterior antes de crear la
        # nueva; su huella ya quedó ligada al archivo recién cargado.
        return None
    from apps.documentos.presentation.expediente_archivos import declaracion_de_correspondencia
    return declaracion_de_correspondencia(documento, request.POST)


def recordar_archivo(archivo):
    archivos = _archivos_creados.get()
    if archivos is not None:
        archivos.append((archivo.storage, archivo.name))


def recordar_extraccion(recurso):
    if not recurso.es_zip:
        return
    raiz = Path(settings.MEDIA_ROOT, 'recursos', 'archivos').resolve()
    destino = recurso.directorio_extraido.resolve()
    if raiz not in destino.parents or destino.exists():
        raise ValidationError('El directorio del archivo comprimido ya existe o no es válido.')
    archivos = _archivos_creados.get()
    if archivos is not None:
        archivos.append((None, destino))


@contextmanager
def operacion_de_unidad(unidad_id, usuario, *, revision=False):
    principal = _archivos_creados.get() is None
    token = _archivos_creados.set([]) if principal else None
    try:
        with transaction.atomic():
            unidad = Unidad.objects.select_for_update().get(pk=unidad_id)
            from apps.core.gobernanza import es_revisor_institucional
            if not ((revision and es_revisor_institucional(usuario)) or
                    (not revision and puede_operar_modulo_unidad(usuario, unidad, 'reportes'))):
                raise ValidationError('No tienes permiso para modificar el expediente de esta unidad.')
            yield unidad
    except Exception:
        if principal:
            for almacenamiento, nombre in reversed(_archivos_creados.get()):
                if almacenamiento is not None:
                    almacenamiento.delete(nombre)
                else:
                    raiz = Path(settings.MEDIA_ROOT, 'recursos', 'archivos').resolve()
                    destino = nombre.resolve()
                    if raiz in destino.parents and destino.is_dir():
                        shutil.rmtree(destino)
        raise
    finally:
        if principal:
            _archivos_creados.reset(token)


def comando(funcion):
    """Serializa por unidad y confirma el cambio junto con su auditoría.

    La unidad es el bloqueo común a un documento y todos sus anexos. Las
    instantáneas conservan la evaluación de cada versión aunque se devuelva.
    Los archivos nuevos se compensan si falla el comando, nunca los históricos.
    """
    firma = signature(funcion)

    @wraps(funcion)
    def ejecutar(*args, request=None, **kwargs):
        argumentos = firma.bind(*args, **kwargs).arguments
        documento = next(iter(argumentos.values()))
        usuario = argumentos['usuario']
        token = _peticion_actual.set(request) if request is not None else None
        try:
            from .independencia_revision import COMANDOS_DE_REVISION
            with operacion_de_unidad(documento.unidad_id, usuario,
                    revision=funcion.__name__ in COMANDOS_DE_REVISION) as unidad:
                actual = DocumentoExpediente.objects.select_for_update().get(pk=documento.pk)
                documento.__dict__.update(actual.__dict__)
                campos = [campo.attname for campo in documento._meta.concrete_fields]
                anteriores = instantanea(documento, campos)
                fuentes_previas = None
                if funcion.__name__ == '_generar' and documento.exigido.es_anexo:
                    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
                    if es_unidad_auditable(documento.unidad):
                        from apps.documentos.presentation.expediente import tramo_del_documento
                        from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad, VERSION_REGLAS
                        from apps.documentos.presentation.automatizacion_documental import huella
                        inicio, fin = tramo_del_documento(documento)
                        fuentes_previas = huella(ContextoCalidad(documento.unidad, inicio, fin).analizar(
                            documento.exigido.codigo)['fuentes'])
                if funcion.__name__ == '_generar':
                    from .aprobacion_en_linea import preparar_emision
                    preparar_emision(documento, usuario)
                from .independencia_revision import COMANDOS_DE_REVISION, exigir_revision_independiente
                if funcion.__name__ in COMANDOS_DE_REVISION:
                    exigir_revision_independiente(documento, usuario, unidad)
                resultado = funcion(*args, **kwargs)
                if fuentes_previas is not None:
                    # Un contexto nuevo vuelve a leer las fuentes. Reutilizar
                    # su caché escondería una modificación durante el render.
                    fuentes_posteriores = huella(ContextoCalidad(documento.unidad, inicio, fin).analizar(
                        documento.exigido.codigo)['fuentes'])
                    if fuentes_previas != fuentes_posteriores:
                        raise ValidationError('Las fuentes cambiaron durante la generación del anexo. '
                                              'Vuelve a generarlo para conservar una versión coherente.')
                    documento._fuentes_control_generacion = dict(sha256=fuentes_posteriores,
                        metodo=f'calidad-laboratorios-{VERSION_REGLAS}')
                if funcion.__name__ == '_generar':
                    from .aprobacion_en_linea import registrar_emision
                    registrar_emision(documento, usuario)
                    from apps.documentos.presentation.expediente_archivos import registrar_preparacion_documental
                    registrar_preparacion_documental(documento, usuario)
                    from apps.documentos.presentation.confianza_documental import registrar_procedencia_nativa
                    registrar_procedencia_nativa(documento, usuario)
                nuevos = instantanea(documento, campos)
                if anteriores != nuevos:
                    registrar_auditoria(
                        _peticion_actual.get(), unidad=unidad, usuario=usuario, accion='actualizar', objeto=documento,
                        descripcion=f'{funcion.__name__}: {documento.exigido.codigo} '
                                    f'({documento.etiqueta_corte}, v{documento.version})',
                        anteriores=anteriores, nuevos=nuevos,
                    )
                return resultado
        except Exception:
            if documento.pk:
                documento.refresh_from_db()
                documento.__dict__.pop('_constancia_qr', None)
            raise
        finally:
            documento.__dict__.pop('_fuentes_control_generacion', None)
            documento.__dict__.pop('_token_emision', None)
            documento.__dict__.pop('_emisor_emision', None)
            if token is not None:
                _peticion_actual.reset(token)

    return ejecutar


@contextmanager
def edicion_desde_unidad(documento, usuario, *, rectificar_anexo=False):
    """En el panel de la unidad, incluso Dirección actúa como remitente.

    El bloqueo cubre la comprobación y el comando nativo: un envío concurrente
    no permite que una edición atrasada vuelva a modificar su archivo.
    """
    with operacion_de_unidad(documento.unidad_id, usuario):
        actual = DocumentoExpediente.objects.select_for_update().get(pk=documento.pk)
        documento.__dict__.update(actual.__dict__)
        if documento.exigido.es_anexo:
            entrega = entrega_del_anexo(documento)
        else:
            entrega = documento
        if entrega.estado == 'validado' or (documento.estado == 'validado' and not (
                rectificar_anexo and documento.exigido.es_anexo)):
            raise ValidationError(
                'La entrega ya fue enviada y no se reemplaza desde la unidad. Aquí solo puedes consultarla; '
                'Dirección debe devolverla desde el administrador para corregirla.')
        yield


def entrega_del_anexo(anexo):
    """Resuelve y bloquea la entrega propietaria bajo el bloqueo de su unidad."""
    if not anexo.exigido.es_anexo:
        raise ValidationError('Este documento no es un anexo.')
    entrega = DocumentoExpediente.objects.select_for_update().filter(
        unidad_id=anexo.unidad_id, anio=anexo.anio, corte=anexo.corte,
        mes__isnull=True, exigido_id=anexo.exigido.anexo_de_id,
    ).first()
    if entrega is None:
        raise ValidationError('No se encontró la entrega a la que pertenece el anexo.')
    return entrega
