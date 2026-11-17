"""Aceptación binaria de documentos permanentes, sin notas ni rúbricas.

La decisión humana se vincula al archivo y a la unidad, no al año de la fila
que lo muestra. Una revocación posterior impide recuperar una aprobación
antigua. La huella acredita integridad; no certifica autoridad ni firma.
"""
from apps.core.gobernanza import es_revisor_institucional
import hashlib
import re

from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from apps.documentos.presentation.expediente_operaciones import comando
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria


ESQUEMA = 1
APROBAR = 'conformidad_permanente:aprobar'
REVOCAR = 'conformidad_permanente:revocar'
CODIGOS = frozenset(('RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD'))
ENTIDAD = 'documentos.DocumentoExpediente'


def es_permanente(documento):
    exigido = getattr(documento, 'exigido', None)
    return bool(getattr(exigido, 'codigo', None) in CODIGOS
                and getattr(exigido, 'periodicidad', None) == 'unica'
                and not getattr(exigido, 'es_anexo', False))


def _alcance_unidad(documento):
    """Identidad institucional mínima; no recopila inventarios ni relaciones."""
    campos = ('codigo', 'dependencia', 'clasificacion_funcional')
    if documento.exigido.codigo == 'PROTOCOLO-BIOSEGURIDAD':
        campos += ('ubicacion',)
    return {campo: str(getattr(documento.unidad, campo, '') or '').strip() for campo in campos}


def _decision(registro, documento):
    if registro is None:
        return None
    datos = registro.datos_nuevos
    if not isinstance(datos, dict):
        return dict(estado='invalida', auditoria_id=registro.pk)
    estado = 'aprobado' if registro.descripcion == APROBAR else 'revocado'
    valida = (type(datos.get('esquema')) is int and datos['esquema'] == ESQUEMA
        and datos.get('estado') == estado
        and type(datos.get('unidad_id')) is int
        and datos['unidad_id'] == registro.unidad_id == documento.unidad_id
        and type(datos.get('exigido_id')) is int
        and datos['exigido_id'] == documento.exigido_id
        and datos.get('codigo') == documento.exigido.codigo
        and type(datos.get('version')) is int
        and type(datos.get('actor_id')) is int
        and datos['actor_id'] == registro.usuario_id)
    if estado == 'aprobado':
        valida = (valida and type(datos.get('recurso_id')) is int
                  and isinstance(datos.get('sha256'), str)
                  and re.fullmatch(r'[0-9a-f]{64}', datos['sha256']) is not None)
    if not valida:
        return dict(estado='invalida', auditoria_id=registro.pk)
    return dict(datos, auditoria_id=registro.pk,
                registrado_en=registro.creado_en.isoformat())


def _bloqueo_persistido(documento, registro, recurso):
    """Una comprobación positiva posterior puede superar una incidencia reparada."""
    if registro is None:
        return False
    controles = (getattr(documento, '_control_automatico', None),
                 getattr(documento, '_aprobacion_permanente_control_origen', None))
    bloqueos = [c for c in controles if c and c.estado == 'bloqueado'
        and c.comprobado_en >= registro.creado_en
        and c.version_documento == documento.version and c.recurso_id == documento.recurso_id
        and c.sha256 == (recurso.hash_sha256 if recurso else '')]
    if not bloqueos:
        return False
    actual = getattr(documento, '_control_automatico', None)
    if (actual and actual.estado == 'automatico' and actual.aplicado
            and documento.estado == 'validado' and actual.version_documento == documento.version
            and actual.recurso_id == documento.recurso_id
            and actual.sha256 == (recurso.hash_sha256 if recurso else '')):
        # No llama _vigente, que consulta a su vez la aprobación permanente.
        from apps.documentos.presentation.automatizacion_documental import METODO, _configuracion
        if (actual.metodo == METODO
                and actual.resumen.get('configuracion_sha256') == _configuracion(documento)):
            return any(c.comprobado_en >= actual.comprobado_en for c in bloqueos)
    return True


def _adjuntar(documento, registro):
    datos = _decision(registro, documento)
    salida = dict(datos or {}, estado=(datos or {}).get('estado', 'sin_aprobacion'),
                  aprobada=False, vigente=False, revocada=False)
    if datos:
        salida['revocada'] = datos['estado'] == 'revocado'
        recurso = documento.recurso if documento.recurso_id else None
        salida['aprobada'] = bool(datos['estado'] == 'aprobado')
        salida['vigente'] = bool(salida['aprobada'] and recurso
            and documento.estado == 'validado' and recurso.activo
            and recurso.estado == 'vigente' and recurso.archivo
            and recurso.version == documento.version
            and recurso.unidad_id == documento.unidad_id
            and datos.get('recurso_id') == documento.recurso_id
            and datos.get('version') == documento.version
            and datos.get('sha256') == recurso.hash_sha256
            and (not documento.exigido.requiere_firma or documento.firma_verificada
                 or _aprobacion_nativa(documento, datos)))
        if salida['aprobada'] and datos.get('alcance_unidad') != _alcance_unidad(documento):
            salida.update(vigente=False,
                aviso='Cambió la identidad, función o instalación de la unidad; confirma el alcance del documento.')
        inspeccion = getattr(documento, '_aprobacion_permanente_inspeccion', None)
        ancla = (documento.recurso_id, documento.version, recurso.hash_sha256 if recurso else '')
        if inspeccion and inspeccion['ancla'] == ancla and not inspeccion['integro']:
            salida.update(vigente=False, aviso=inspeccion['aviso'])
        # El listado no vuelve a abrir archivos. Un control persistido que ya
        # detectó una alteración conserva su efecto en las instancias nuevas.
        # Leer la caché directamente evita recursión con control_vigente y no
        # añade consultas por documento cuando el lote todavía no la cargó.
        if (_bloqueo_persistido(documento, registro, recurso)
                and not (inspeccion and inspeccion['ancla'] == ancla and inspeccion['integro'])):
            salida.update(vigente=False,
                aviso='El control del archivo vigente detectó incidencias; compruébalas antes de reutilizar su aceptación.')
    documento._aprobacion_permanente_registro = registro
    documento.aprobacion_permanente = salida
    return salida


def _aprobacion_nativa(documento, decision):
    """La aprobación QR es distinta de una firma PDF y también se hereda por archivo."""
    clave = (documento.unidad_id, documento.exigido_id, documento.recurso_id,
             documento.version, decision.get('sha256'), decision.get('actor_id'))
    ancla = (documento.recurso_id, documento.version)
    if (hasattr(documento, '_aprobaciones_permanentes_qr')
            and getattr(documento, '_aprobaciones_qr_ancla', None) == ancla):
        return clave in documento._aprobaciones_permanentes_qr
    from apps.documentos.models.constancias import ConstanciaDocumento
    aprobada = ConstanciaDocumento.objects.filter(
        documento__unidad_id=documento.unidad_id, documento__exigido_id=documento.exigido_id,
        documento__estado='validado', documento__verificacion_qr=F('token'),
        recurso_id=documento.recurso_id, version=documento.version,
        sha256=decision.get('sha256'), enviado_en__isnull=False,
        aprobado_por_id=decision.get('actor_id'), aprobado_en__isnull=False,
        observado_en__isnull=True).exists()
    documento._aprobaciones_permanentes_qr = {clave} if aprobada else set()
    documento._aprobaciones_qr_ancla = ancla
    return aprobada


def completar_aprobaciones(documentos):
    """Carga por lote: decisión, controles y, si corresponde, aprobaciones QR.

    Los llamadores de listados precargan ``unidad``, ``exigido`` y ``recurso`` mediante
    select_related, igual que los demás proyectores del expediente. No se
    abren archivos ni se escribe al consultar.
    """
    documentos = list(documentos)
    permanentes = [d for d in documentos if es_permanente(d)]
    unidades = {d.unidad_id for d in permanentes}
    exigidos = {d.exigido_id for d in permanentes}
    ultimos = {}
    if unidades and exigidos:
        registros = RegistroAuditoriaUnidad.objects.filter(
            unidad_id__in=unidades, entidad=ENTIDAD,
            descripcion__in=(APROBAR, REVOCAR),
            datos_nuevos__exigido_id__in=list(exigidos),
        ).only('pk', 'unidad_id', 'usuario_id', 'descripcion', 'datos_nuevos',
               'creado_en').order_by('-pk')
        for registro in registros:
            datos = registro.datos_nuevos
            exigido_id = datos.get('exigido_id') if isinstance(datos, dict) else None
            if type(exigido_id) is int:
                ultimos.setdefault((registro.unidad_id, exigido_id), registro)
    # Una copia anual no puede eludir una incidencia persistida de su original.
    # Se cargan las filas actuales y las canónicas juntas; no se invoca
    # completar_controles porque éste utiliza a su vez este proyector.
    from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
    ids = {d.pk for d in permanentes if d.pk}
    for registro in ultimos.values():
        origen_id = registro.datos_nuevos.get('documento_id')
        if type(origen_id) is int:
            ids.add(origen_id)
    controles = {c.documento_id: c for c in ControlAutomaticoDocumento.objects.filter(
        documento_id__in=ids)} if ids else {}
    nativos = [d for d in permanentes if d.recurso_id and d.exigido.requiere_firma
               and not d.firma_verificada]
    aprobaciones_qr = set()
    if nativos:
        from apps.documentos.models.constancias import ConstanciaDocumento
        aprobaciones_qr = set(ConstanciaDocumento.objects.filter(
            documento__unidad_id__in=unidades, documento__exigido_id__in=exigidos,
            documento__estado='validado', documento__verificacion_qr=F('token'),
            recurso_id__in={d.recurso_id for d in nativos}, enviado_en__isnull=False,
            aprobado_en__isnull=False, observado_en__isnull=True).values_list(
                'documento__unidad_id', 'documento__exigido_id', 'recurso_id',
                'version', 'sha256', 'aprobado_por_id'))
    for documento in permanentes:
        registro = ultimos.get((documento.unidad_id, documento.exigido_id))
        origen_id = registro.datos_nuevos.get('documento_id') if registro else None
        documento._control_automatico = controles.get(documento.pk)
        documento._aprobacion_permanente_control_origen = controles.get(origen_id)
        documento._aprobaciones_permanentes_qr = aprobaciones_qr
        documento._aprobaciones_qr_ancla = (documento.recurso_id, documento.version)
    for documento in documentos:
        _adjuntar(documento, ultimos.get((documento.unidad_id, documento.exigido_id))
                  if es_permanente(documento) else None)
    return documentos


def aprobacion_vigente(documento, inspeccionar=False):
    if not es_permanente(documento):
        return None
    if not hasattr(documento, '_aprobacion_permanente_registro'):
        completar_aprobaciones([documento])
    salida = _adjuntar(documento, documento._aprobacion_permanente_registro)
    if inspeccionar and salida['aprobada']:
        recurso = documento.recurso if documento.recurso_id else None
        ancla = (documento.recurso_id, documento.version, recurso.hash_sha256 if recurso else '')
        integro, aviso = False, 'El archivo aprobado no está disponible o cambió respecto a su huella.'
        if recurso and recurso.archivo:
            try:
                with recurso.archivo.open('rb') as archivo:
                    integro = hashlib.file_digest(archivo, 'sha256').hexdigest() == salida.get('sha256')
            except (OSError, ValueError):
                pass
        documento._aprobacion_permanente_inspeccion = dict(
            ancla=ancla, integro=integro, aviso='' if integro else aviso)
        salida = _adjuntar(documento, documento._aprobacion_permanente_registro)
    return salida if salida['vigente'] else None


def _autoridad(usuario):
    if not es_revisor_institucional(usuario) or not getattr(usuario, 'is_active', False):
        raise ValidationError('Solo el responsable institucional designado puede aceptar o revocar un documento permanente.')


def _datos(documento, usuario, estado, comentario):
    return dict(esquema=ESQUEMA, estado=estado, unidad_id=documento.unidad_id,
        exigido_id=documento.exigido_id, documento_id=documento.pk,
        codigo=documento.exigido.codigo, recurso_id=documento.recurso_id,
        alcance_unidad=_alcance_unidad(documento),
        version=documento.version,
        sha256=documento.recurso.hash_sha256 if documento.recurso_id else '',
        actor_id=usuario.pk, actor_nombre=usuario.get_full_name() or usuario.get_username(),
        decidido_en=timezone.now().isoformat(), comentario=comentario)


@comando
def aprobar_permanente(documento, usuario, version, huella, confirmado=False,
                      comentario='', declaracion_correspondencia=None):
    """Una revisión atribuida del archivo vigente, reutilizable entre años."""
    _autoridad(usuario)
    if not es_permanente(documento):
        raise ValidationError('Este documento no tiene aceptación permanente.')
    if not confirmado:
        raise ValidationError('Confirma que revisaste el documento y su autoridad, alcance y vigencia.')
    if (not documento.recurso_id or str(documento.version) != str(version)
            or not huella or documento.recurso.hash_sha256 != huella):
        raise ValidationError('El archivo o la versión cambiaron. Abre de nuevo su revisión.')
    if documento.estado == 'no_aplica':
        raise ValidationError('Reactiva el documento antes de aceptar su archivo.')
    if documento.recurso.unidad_id != documento.unidad_id:
        raise ValidationError('El archivo pertenece a otra unidad.')
    # Los comandos pueden recibir una instancia leída antes de otra decisión.
    # El bloqueo de unidad protege esta nueva lectura de la última aprobación.
    documento.__dict__.pop('_aprobacion_permanente_inspeccion', None)
    completar_aprobaciones([documento])
    vigente = aprobacion_vigente(documento, inspeccionar=True)
    if vigente and not _bloqueo_persistido(documento, documento._aprobacion_permanente_registro,
                                         documento.recurso):
        return vigente
    from apps.documentos.presentation.expediente import recibir_documento
    recibir_documento(documento, usuario, declaracion_correspondencia=declaracion_correspondencia)
    datos = _datos(documento, usuario, 'aprobado', str(comentario or '').strip()[:2000])
    registro = registrar_auditoria(unidad=documento.unidad, usuario=usuario,
        accion='aprobar', objeto=documento, descripcion=APROBAR, nuevos=datos)
    documento.__dict__.pop('_aprobacion_permanente_inspeccion', None)
    documento.__dict__.pop('_aprobaciones_permanentes_qr', None)
    _adjuntar(documento, registro)
    from apps.documentos.presentation.automatizacion_documental import procesar_documento
    procesar_documento(documento, usuario=usuario)
    return aprobacion_vigente(documento)


@comando
def revocar_permanente(documento, usuario, motivo):
    """Se invoca dentro del comando de observación o retirada de la unidad."""
    if not es_permanente(documento):
        return None
    _autoridad(usuario)
    motivo = str(motivo or '').strip()[:2000]
    if not motivo:
        raise ValidationError('Indica el motivo por el que retiras la aceptación permanente.')
    documento.__dict__.pop('_aprobacion_permanente_inspeccion', None)
    completar_aprobaciones([documento])
    actual = _adjuntar(documento, documento._aprobacion_permanente_registro)
    datos = _datos(documento, usuario, 'revocado', motivo)
    if (actual['revocada'] and all(actual.get(k) == datos[k]
            for k in ('recurso_id', 'version', 'sha256', 'comentario'))):
        return actual
    registro = registrar_auditoria(unidad=documento.unidad, usuario=usuario,
        accion='observar', objeto=documento, descripcion=REVOCAR,
        nuevos=dict(datos, motivo=motivo))
    documento.__dict__.pop('_aprobacion_permanente_inspeccion', None)
    return _adjuntar(documento, registro)


def aceptacion_obligatoria(documento):
    """Si la Dirección aceptó un documento de cumplimiento obligatorio, que no recibe porcentaje.

    El permanente se acepta con su aprobación vigente; el plan, con su conformidad documental; los demás, cuando
    la Dirección recibe la entrega tras comprobar su correspondencia.
    """
    if es_permanente(documento):
        return bool(aprobacion_vigente(documento))
    from .conformidad_lectura import completar_conformidades, es_plan, lectura_conformidad
    if es_plan(documento):
        # Los listados cargan la conformidad por lote; un documento leído suelto la trae aquí.
        if not hasattr(documento, '_conformidad_plan_registro'):
            completar_conformidades([documento])
        return (lectura_conformidad(documento) or {}).get('estado') == 'conforme'
    return documento.estado == 'validado' and documento.recibido_en is not None
