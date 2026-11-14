"""Archivos del expediente: versiones consultables y retirada con trazabilidad."""
import mimetypes
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F
from django.db.models import Q
from django.http import FileResponse, Http404

from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import Recurso
from apps.documentos.presentation.expediente_operaciones import comando
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria


MARCA_INTEGRIDAD = 'SLCID-DOC-1:'
AUDITORIA_INTEGRIDAD = 'integridad_documental:'


def _requiere_integridad(documento):
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    return es_unidad_auditable(documento.unidad) and not documento.exigido.es_anexo


def identidad_documental(documento):
    return dict(unidad_id=documento.unidad_id, documento_id=documento.pk,
                codigo=documento.exigido.codigo, anio=documento.anio,
                corte=documento.corte or '', mes=documento.mes)


def _normalizar_contexto(valor):
    if isinstance(valor, dict):
        return {k: _normalizar_contexto(v) for k, v in valor.items()
                if k not in ('calculado_en', 'generado_en', 'consultado_en', 'tiempo_restante')}
    if isinstance(valor, (tuple, list)):
        # La fecha de emisión no vuelve obsoleto por sí sola un PDF de ayer.
        return [_normalizar_contexto(v) for v in valor if not (
            isinstance(v, (tuple, list)) and v and v[0] == 'Fecha de elaboración')]
    return valor


def huella_contexto_pdf(compuesto):
    datos = {k: compuesto.get(k) for k in ('tipo', 'tramo', 'secciones', 'firmas')}
    return hashlib.sha256(json.dumps(_normalizar_contexto(datos), sort_keys=True,
        ensure_ascii=True, default=str).encode()).hexdigest()


def metadatos_documentales(compuesto):
    """Identificación interna, sin afirmar aprobación, firma ni código institucional."""
    documento = compuesto.get('documento')
    if documento is None or not _requiere_integridad(documento):
        return None
    datos = dict(identidad_documental(documento), esquema=1,
                 contexto_sha256=huella_contexto_pdf(compuesto), borrador=bool(compuesto.get('borrador')))
    if documento.marco_periodo == 'gestion_v1':
        from apps.documentos.presentation.expediente import instantanea_periodo
        datos['periodo_documental'] = instantanea_periodo(documento)
    return datos


def codificar_metadatos(datos):
    return MARCA_INTEGRIDAD + base64.urlsafe_b64encode(
        json.dumps(datos, sort_keys=True, ensure_ascii=True).encode()).decode()


def _leer_archivo(archivo):
    archivo.seek(0)
    contenido = archivo.read(25 * 1024 * 1024 + 1)
    archivo.seek(0)
    if not contenido or len(contenido) > 25 * 1024 * 1024:
        raise ValidationError('El respaldo debe tener contenido y no superar 25 MB.')
    datos = None
    if Path(archivo.name).suffix.lower() == '.pdf':
        from pypdf import PdfReader
        try:
            pdf = PdfReader(BytesIO(contenido))
            if pdf.is_encrypted or not pdf.pages:
                raise ValueError
            asunto = str((pdf.metadata or {}).get('/Subject', ''))
            if asunto.startswith(MARCA_INTEGRIDAD):
                datos = json.loads(base64.urlsafe_b64decode(asunto[len(MARCA_INTEGRIDAD):]))
                if not isinstance(datos, dict) or datos.get('esquema') != 1:
                    raise ValueError
        except Exception as error:
            raise ValidationError('El PDF no es legible o su referencia documental está dañada. Adjunta el documento correcto.') from error
    return hashlib.sha256(contenido).hexdigest(), datos


def _contexto_actual(documento):
    from apps.documentos.models.expediente import DocumentoElaborado
    from apps.documentos.presentation.expediente import tramo_del_documento
    from apps.documentos.presentation.expediente_redaccion import componer
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    inicio, fin = tramo_del_documento(documento)
    return huella_contexto_pdf(componer(documento, redaccion.contenido if redaccion else {}, inicio, fin))


def _identidad_coincide(documento, datos):
    esperado = identidad_documental(documento)
    if all(type(datos.get(k)) is type(v) and datos.get(k) == v for k, v in esperado.items()):
        return True
    if (documento.exigido.periodicidad != 'unica' or
            any(type(datos.get(k)) is not type(esperado[k]) or datos.get(k) != esperado[k]
                for k in ('unidad_id', 'codigo', 'corte', 'mes')) or
            type(datos.get('anio')) is not int or datos['anio'] > documento.anio or
            type(datos.get('documento_id')) is not int or not documento.recurso_id):
        return False
    from apps.documentos.models.expediente import DocumentoExpediente
    if hasattr(documento, '_integridad_herencias_validas'):
        return datos['documento_id'] in documento._integridad_herencias_validas
    return DocumentoExpediente.objects.filter(pk=datos['documento_id'], unidad_id=documento.unidad_id,
        exigido_id=documento.exigido_id, anio=datos['anio'], recurso_id=documento.recurso_id).exists()


def _contrastar_pdf(documento, datos, *, comprobar_actual=True):
    if datos is None:
        return
    if not _identidad_coincide(documento, datos):
        raise ValidationError('El PDF corresponde a otro documento, unidad o período. Carga el archivo de esta entrega.')
    if datos.get('borrador'):
        raise ValidationError('La vista previa es un borrador. Genera el documento para firma y firma esa versión.')
    if comprobar_actual and documento.exigido.redactable and datos.get('contexto_sha256') != _contexto_actual(documento):
        raise ValidationError('El PDF preparado está desactualizado respecto al editor o a los registros de la unidad. '
                              'Genera una nueva versión y fírmala antes de cargarla o enviarla.')


def declaracion_de_correspondencia(documento, datos):
    """La confirmación identifica la entrega y su versión; no equivale a aprobarla."""
    esperado = identidad_documental(documento)
    declaracion = {'revisado': datos.get('correspondencia_confirmada') == '1'}
    for clave, valor in esperado.items():
        enviado = datos.get('correspondencia_' + clave)
        declaracion[clave] = int(enviado) if enviado and clave in ('unidad_id', 'documento_id', 'anio', 'mes') and str(enviado).isdecimal() else enviado
    declaracion['mes'] = declaracion['mes'] or None
    declaracion['version'] = str(datos.get('correspondencia_version') or '')
    return declaracion


def _comprobar_declaracion(documento, declaracion):
    if not isinstance(declaracion, dict) or declaracion.get('revisado') is not True:
        raise ValidationError('Confirma que abriste el archivo y comprobaste que corresponde al documento, unidad y período indicados.')
    if any(type(declaracion.get(k)) is not type(v) or declaracion.get(k) != v
           for k, v in identidad_documental(documento).items()):
        raise ValidationError('La declaración de correspondencia pertenece a otra entrega. Vuelve a abrir la revisión.')
    if str(declaracion.get('version')) != str(documento.version):
        raise ValidationError('La versión cambió desde que abriste la revisión. Comprueba el archivo vigente antes de continuar.')


def comprobar_correspondencia(documento, archivo, *, declaracion=None):
    if not _requiere_integridad(documento):
        return None
    _comprobar_declaracion(documento, declaracion)
    huella, metadatos = _leer_archivo(archivo)
    _contrastar_pdf(documento, metadatos)
    return dict(identidad_documental(documento), sha256=huella, metadatos=metadatos,
                declaracion_unidad=True, director_revisado=False,
                aviso='Archivo externo o histórico: Dirección debe comprobar la correspondencia.' if metadatos is None else '')


def registrar_integridad_documental(documento, usuario, datos, *, etapa):
    if datos is None or not _requiere_integridad(documento):
        return
    datos = dict(datos, recurso_id=documento.recurso_id, version=documento.version, etapa=etapa)
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='archivar', objeto=documento,
        descripcion=AUDITORIA_INTEGRIDAD + etapa, nuevos=datos)
    documento._integridad_registro = datos


def registrar_preparacion_documental(documento, usuario):
    if not _requiere_integridad(documento) or not documento.recurso_id:
        return
    with documento.recurso.archivo.open('rb') as archivo:
        huella, metadatos = _leer_archivo(archivo)
    registrar_integridad_documental(documento, usuario,
        dict(identidad_documental(documento), sha256=huella, metadatos=metadatos,
             declaracion_unidad=False, director_revisado=False), etapa='preparar')


def completar_integridad_documental(documentos):
    """Una sola consulta de auditoría para un listado; nunca abre sus archivos PDF."""
    documentos = list(documentos)
    from apps.documentos.presentation.automatizacion_documental import completar_controles
    if any(_requiere_integridad(d) and not hasattr(d, '_control_automatico') for d in documentos):
        completar_controles(documentos)
    def clave(d):
        return str(d.pk) if d.pk else f'virtual:{d.unidad_id}:{d.exigido_id}:{d.anio}:{d.corte}:{d.mes}'
    pendientes = {clave(d): d for d in documentos if _requiere_integridad(d) and d.recurso_id}
    heredables = {}
    for d in pendientes.values():
        if d.exigido.periodicidad == 'unica':
            heredables.setdefault(d.recurso_id, []).append(d)
    for d in documentos:
        d._integridad_registro = None
    registros = list(RegistroAuditoriaUnidad.objects.filter(
            Q(objeto_id__in=[str(d.pk) for d in pendientes.values() if d.pk])
            | Q(datos_nuevos__recurso_id__in=list(heredables)),
            entidad='documentos.DocumentoExpediente', descripcion__startswith=AUDITORIA_INTEGRIDAD,
            accion='archivar').only('objeto_id', 'unidad_id', 'datos_nuevos').order_by('-pk'))
    if heredables:
        from apps.documentos.models.expediente import DocumentoExpediente
        ids = [r.datos_nuevos.get('documento_id') for r in registros
               if type(r.datos_nuevos.get('documento_id')) is int]
        origenes = list(DocumentoExpediente.objects.filter(pk__in=ids).values(
            'pk', 'unidad_id', 'exigido_id', 'anio', 'recurso_id'))
        for lista in heredables.values():
            for d in lista:
                d._integridad_herencias_validas = {o['pk'] for o in origenes
                    if o['unidad_id'] == d.unidad_id and o['exigido_id'] == d.exigido_id
                    and o['anio'] <= d.anio and o['recurso_id'] == d.recurso_id}
    for r in registros:
        candidatos = [pendientes[r.objeto_id]] if r.objeto_id in pendientes else []
        candidatos += heredables.get(r.datos_nuevos.get('recurso_id'), [])
        for d in candidatos:
            if (clave(d) in pendientes and r.unidad_id == d.unidad_id
                    and r.datos_nuevos.get('recurso_id') == d.recurso_id
                    and r.datos_nuevos.get('version') == d.version
                    and _identidad_coincide(d, r.datos_nuevos)):
                d._integridad_registro = r.datos_nuevos
                pendientes.pop(clave(d))
    for d in documentos:
        d.integridad_documental = estado_integridad_documental(d)


def estado_integridad_documental(documento, *, inspeccionar=False):
    """Aviso de correspondencia sin alterar versiones, firmas o notas históricas."""
    if not _requiere_integridad(documento):
        return dict(aplica=False, apto_enviar=True, correspondencia_verificada=True, aviso='')
    if not documento.recurso_id:
        return dict(aplica=True, apto_enviar=False, correspondencia_verificada=False, aviso='Falta el documento.')
    if not hasattr(documento, '_integridad_registro'):
        completar_integridad_documental([documento])
        if not inspeccionar:
            return documento.integridad_documental
    datos = documento._integridad_registro or {}
    problema = ''
    if documento.recurso.unidad_id != documento.unidad_id:
        problema = 'El archivo pertenece a otra unidad; no acredita esta entrega.'
    elif documento.recurso.estado == 'obsoleto' or not documento.recurso.activo:
        problema = 'El archivo está retirado u obsoleto; conserva el historial y carga el vigente.'
    elif datos and (datos.get('sha256') != documento.recurso.hash_sha256
                    or datos.get('version') != documento.version or not _identidad_coincide(documento, datos)):
        problema = 'La referencia, huella o correspondencia del archivo cambió; requiere una nueva revisión.'
    if inspeccionar and not problema:
        try:
            with documento.recurso.archivo.open('rb') as archivo:
                huella, metadatos = _leer_archivo(archivo)
            if huella != documento.recurso.hash_sha256:
                raise ValidationError('El contenido del archivo no coincide con su huella registrada.')
            _contrastar_pdf(documento, metadatos, comprobar_actual=documento.estado != 'validado')
        except (ValidationError, OSError, ValueError) as error:
            problema = ' '.join(error.messages) if isinstance(error, ValidationError) else 'El archivo no está disponible.'
    from apps.documentos.presentation.automatizacion_documental import control_vigente
    control = control_vigente(documento)
    nativa = bool(control and control.resumen.get('correspondencia_automatica') and not problema)
    verificada = bool((datos.get('director_revisado') or nativa) and not problema)
    apto = bool(datos.get('declaracion_unidad') and not problema)
    aviso = problema or ('' if verificada else
        'Correspondencia pendiente de revisión de Dirección: abrir el archivo y comprobar documento, unidad y período.')
    if documento.estado == 'generado' and not datos.get('metadatos'):
        aviso = 'PDF preparado anterior: comprueba los datos actuales en el editor y genera una nueva versión antes de firmar.'
        apto = False
    return dict(aplica=True, apto_enviar=apto, correspondencia_verificada=verificada,
                aviso=aviso, bloqueado=bool(problema), legado=not bool(datos.get('metadatos')),
                fuente_correspondencia='sistema' if nativa and not datos.get('director_revisado') else 'direccion' if verificada else '')


def exigir_integridad_documental(documento, usuario, *, etapa, declaracion=None):
    if not _requiere_integridad(documento):
        return
    if not documento.recurso_id:
        raise ValidationError('No hay archivo para comprobar su correspondencia.')
    # La comprobación de contenido se hace al operar, no al listar filas.
    estado = estado_integridad_documental(documento, inspeccionar=True)
    if estado.get('bloqueado'):
        raise ValidationError(estado['aviso'])
    if declaracion is not None:
        _comprobar_declaracion(documento, declaracion)
        with documento.recurso.archivo.open('rb') as archivo:
            huella, metadatos = _leer_archivo(archivo)
        datos = dict(identidad_documental(documento), sha256=huella, metadatos=metadatos,
            declaracion_unidad=True, director_revisado=bool(usuario.is_superuser and etapa in ('recibir', 'evaluar')))
        registrar_integridad_documental(documento, usuario, datos, etapa=etapa)
        estado = estado_integridad_documental(documento)
    if etapa in ('recibir', 'evaluar') and not estado['correspondencia_verificada']:
        raise ValidationError('Dirección debe abrir el documento y confirmar su correspondencia con esta unidad, tipo y período antes de recibirlo o calificarlo.')
    if etapa == 'enviar' and not estado['apto_enviar']:
        raise ValidationError(estado['aviso'])


def versiones_del_documento(documento):
    if not documento.pk:
        return []
    ids = {documento.recurso_id} if documento.recurso_id else set()
    retirados = set()
    estados = {}
    registros = RegistroAuditoriaUnidad.objects.filter(
        unidad_id=documento.unidad_id, entidad=documento._meta.label, objeto_id=str(documento.pk))
    for registro in registros.only('descripcion', 'datos_anteriores', 'datos_nuevos'):
        for datos in (registro.datos_anteriores, registro.datos_nuevos):
            valor = datos.get('recurso_id')
            if isinstance(valor, int) and not isinstance(valor, bool):
                ids.add(valor)
                estados.setdefault(valor, set()).add(datos.get('estado'))
        if registro.descripcion.startswith('retirar_archivo:'):
            retirados.add(registro.datos_anteriores.get('recurso_id'))
    encontrados = {}
    pendientes = ids
    while pendientes:
        recursos = Recurso.objects.filter(pk__in=pendientes, unidad_id=documento.unidad_id)
        siguientes = set()
        for recurso in recursos:
            encontrados[recurso.pk] = recurso
            if recurso.reemplaza_a_id and recurso.reemplaza_a_id not in encontrados:
                siguientes.add(recurso.reemplaza_a_id)
        pendientes = siguientes - encontrados.keys()
    if documento.recurso_id:
        estados.setdefault(documento.recurso_id, set()).add(documento.estado)
    return [dict(recurso=r, actual=r.pk == documento.recurso_id,
                 retirado=r.pk in retirados, enviado='validado' in estados.get(r.pk, ()),
                 borrador='generado' in estados.get(r.pk, ()) and 'validado' not in estados.get(r.pk, ())) for r in sorted(
                     encontrados.values(), key=lambda r: (r.version, r.pk), reverse=True)]


@comando
def retirar_archivo(documento, usuario, motivo, version, huella):
    from apps.documentos.presentation.expediente import _invalidar_evaluacion, reabrir_anexos

    if documento.exigido.es_anexo:
        raise ValidationError('Retira el archivo de la entrega principal, no sus anexos.')
    if not documento.recurso_id:
        raise ValidationError('No hay archivo vigente que retirar.')
    if documento.estado == 'validado' and not usuario.is_superuser:
        raise ValidationError('Solo la Dirección retira un archivo que ya fue enviado o recibido.')
    if str(documento.version) != str(version) or documento.recurso.hash_sha256 != huella:
        raise ValidationError('El archivo cambió. Revisa la versión vigente antes de retirarlo.')
    if not str(motivo or '').strip():
        raise ValidationError('Indica por qué el archivo no corresponde a la entrega.')
    if usuario.is_superuser:
        from apps.documentos.presentation.conformidad_permanente import revocar_permanente
        revocar_permanente(documento, usuario, motivo)
    # Los actos permanentes pueden compartir archivo entre años. Retirar una
    # entrega no altera el recurso todavía vigente en otro expediente.
    if not documento.recurso.documentos_expediente.exclude(pk=documento.pk).exists():
        Recurso.objects.filter(pk=documento.recurso_id).update(estado='obsoleto')
    documento.recurso = None
    documento.estado = 'pendiente'
    documento.firma_verificada = False
    documento.verificacion_qr = None
    for campo in ('entregado_en', 'cargado_en', 'cargado_por', 'generado_en',
                  'validado_en', 'validado_por', 'recibido_en', 'recibido_por'):
        setattr(documento, campo, None)
    documento.entregado_tarde = False
    _invalidar_evaluacion(documento)
    documento.observacion = 'Archivo retirado: ' + str(motivo).strip()[:1200]
    documento.save()
    reabrir_anexos(documento)


def servir_version(request, documento, recurso_id):
    fila = next((v for v in versiones_del_documento(documento)
                 if str(v['recurso'].pk) == str(recurso_id)), None)
    if fila is None:
        raise Http404('Archivo fuera del historial del documento.')
    recurso = fila['recurso']
    if not recurso.archivo:
        raise Http404('Archivo no disponible.')
    archivo = Path(recurso.archivo.path).resolve()
    if Path(settings.MEDIA_ROOT).resolve() not in archivo.parents or not archivo.is_file():
        raise Http404('Archivo no disponible.')
    descarga = request.GET.get('download') == '1'
    registrar_auditoria(request, unidad=documento.unidad, accion='consultar', objeto=documento,
                       descripcion=f"{'Descargó' if descarga else 'Abrió'} archivo v{recurso.version} del expediente.",
                       nuevos={'recurso_id': recurso.pk, 'version_archivo': recurso.version})
    if descarga:
        Recurso.objects.filter(pk=recurso.pk).update(veces_descargado=F('veces_descargado') + 1)
    tipo = mimetypes.guess_type(archivo.name)[0] or 'application/octet-stream'
    respuesta = FileResponse(archivo.open('rb'), as_attachment=descarga or tipo != 'application/pdf',
                             filename=recurso.nombre_original or archivo.name, content_type=tipo)
    respuesta['X-Frame-Options'] = 'SAMEORIGIN'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['Content-Security-Policy'] = "sandbox; default-src 'none'"
    return respuesta
