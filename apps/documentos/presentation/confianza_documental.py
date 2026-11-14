"""Procedencia comprobable de un PDF nativo, sin simular confianza criptográfica.

La marca del PDF es orientativa: el origen debe existir en la auditoría y el
archivo archivado debe conservar sus bytes. Una firma añadida puede cambiar
la estructura del contenedor, nunca las páginas o sus recursos.
"""
import hashlib
import json
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from pypdf import PdfReader
from pypdf.generic import (
    ArrayObject, BooleanObject, ByteStringObject, DictionaryObject, FloatObject,
    IndirectObject, NameObject, NullObject, NumberObject, StreamObject, TextStringObject,
)

from apps.documentos.presentation.expediente_archivos import (
    AUDITORIA_INTEGRIDAD, _contexto_actual, _identidad_coincide, _leer_archivo,
)
from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.models.recursos import Recurso
from apps.reservas.presentation.guia_firma_certificada import validar_pdf_firmado


MAXIMO_BYTES = 25 * 1024 * 1024
CLAVES_ACTIVAS = {'/JS', '/JavaScript', '/OpenAction', '/AA', '/Launch', '/EmbeddedFiles',
                 '/EF', '/AF', '/EmbeddedFile', '/XFA', '/RichMediaContent', '/Collection',
                 '/Movie', '/Sound', '/3DD'}
AUDITORIA_PROCEDENCIA = 'procedencia_nativa:generar'


def _resolver(valor):
    return valor.get_object() if isinstance(valor, IndirectObject) else valor


def _campo_firma(valor):
    vistos = set()
    for _ in range(12):
        valor = _resolver(valor)
        if not isinstance(valor, DictionaryObject) or id(valor) in vistos:
            return False
        vistos.add(id(valor))
        if '/FT' in valor:
            return valor['/FT'] == '/Sig'
        valor = valor.get('/Parent')
    return False


def _sin_contenido_activo(reader):
    """Recorre también catálogo, nombres, formularios y recursos indirectos."""
    pendientes, vistos, total = [reader.trailer], set(), 0
    while pendientes:
        valor = _resolver(pendientes.pop())
        if not isinstance(valor, (dict, list, tuple, ArrayObject)) or id(valor) in vistos:
            continue
        vistos.add(id(valor))
        total += 1
        if total > 100000:
            raise ValidationError('El PDF excede el límite de objetos comprobables automáticamente.')
        if isinstance(valor, dict):
            if CLAVES_ACTIVAS.intersection(str(k) for k in valor):
                raise ValidationError('El PDF contiene acciones, contenido activo o archivos adjuntos no admitidos.')
            if valor.get('/Type') == '/EmbeddedFile' or valor.get('/S') in (
                    '/JavaScript', '/Launch', '/SubmitForm', '/ImportData', '/GoToR'):
                raise ValidationError('El PDF contiene una acción o un archivo externo no admitido.')
            if isinstance(valor, StreamObject) and '/F' in valor:
                raise ValidationError('El PDF depende de un flujo externo no verificable.')
            pendientes.extend(valor.values())
        else:
            pendientes.extend(valor)
    acroform = _resolver(reader.trailer['/Root'].get('/AcroForm'))
    if acroform:
        for campo in _resolver(acroform.get('/Fields', [])):
            if not _campo_firma(campo):
                raise ValidationError('El PDF contiene campos editables ajenos a una firma.')


def _canonico(valor, pila=None, nivel=0, *, paginas=None, indice=False):
    """Normaliza referencias y compresión; conserva contenido y recursos completos."""
    if nivel > 64:
        raise ValidationError('La estructura del PDF excede la profundidad comprobable.')
    valor = _resolver(valor)
    if paginas is not None and isinstance(valor, DictionaryObject) and valor.get('/Type') == '/Page':
        if id(valor) not in paginas:
            raise ValidationError('El índice del PDF apunta a una página ajena al documento.')
        return {'pagina': paginas[id(valor)]}
    pila = set() if pila is None else pila
    compuesto = isinstance(valor, (dict, list, tuple, ArrayObject))
    if compuesto and id(valor) in pila:
        raise ValidationError('El PDF contiene recursos cíclicos no comprobables automáticamente.')
    siguiente = pila | {id(valor)} if compuesto else pila
    if isinstance(valor, StreamObject):
        return {'flujo_sha256': hashlib.sha256(valor.get_data()).hexdigest(),
                'atributos': {str(k): _canonico(v, siguiente, nivel + 1, paginas=paginas, indice=indice) for k, v in sorted(valor.items())
                              if k not in ('/Length', '/Filter', '/DecodeParms')}}
    if isinstance(valor, dict):
        # El árbol de marcadores tiene referencias inversas legítimas. Sus
        # hijos y hermanos se conservan por /First, /Last y /Next; los recursos
        # de página siguen rechazando ciclos como antes.
        return {str(k): _canonico(v, siguiente, nivel + 1, paginas=paginas, indice=indice)
                for k, v in sorted(valor.items()) if not (indice and k in ('/Parent', '/Prev'))}
    if isinstance(valor, (list, tuple, ArrayObject)):
        return [_canonico(v, siguiente, nivel + 1, paginas=paginas, indice=indice) for v in valor]
    if isinstance(valor, BooleanObject):
        return {'booleano': bool(valor.value)}
    if isinstance(valor, (NullObject, type(None))):
        return None
    if isinstance(valor, (FloatObject, NumberObject, int, float, Decimal)):
        return {'numero': format(Decimal(str(valor)).normalize(), 'f')}
    if isinstance(valor, ByteStringObject):
        return {'bytes': bytes(valor).hex()}
    if isinstance(valor, NameObject):
        return {'nombre': str(valor)}
    if isinstance(valor, (TextStringObject, str)):
        return {'texto': str(valor)}
    raise ValidationError('El PDF contiene un tipo de recurso no comprobable automáticamente.')


def _enlace_uri_nativo(anotacion):
    """Sólo admite enlaces web simples; su equivalencia se comprueba aparte.

    Un enlace nuevo, eliminado o modificado cambia la huella de la página.
    No se permite usar este caso para introducir otras acciones PDF o una
    cadena de acciones a través de ``/Next``.
    """
    if not isinstance(anotacion, DictionaryObject) or anotacion.get('/Subtype') != '/Link':
        return False
    accion = _resolver(anotacion.get('/A'))
    if (not isinstance(accion, DictionaryObject) or accion.get('/S') != '/URI' or
            '/Dest' in anotacion or set(accion) - {'/Type', '/S', '/URI', '/IsMap'}):
        return False
    uri = _resolver(accion.get('/URI'))
    if not isinstance(uri, (TextStringObject, str)) or any(ord(c) < 32 for c in uri):
        return False
    try:
        destino = urlsplit(str(uri))
        return destino.scheme.lower() in {'http', 'https'} and bool(destino.hostname)
    except ValueError:
        return False


def _referencias_paginas(reader):
    # PdfReader.pages expone PageObject; el destino puede resolver al
    # DictionaryObject original del mismo objeto indirecto.
    referencias = {}
    for i, pagina in enumerate(reader.pages):
        referencias[id(pagina)] = i
        if pagina.indirect_reference is not None:
            referencias[id(_resolver(pagina.indirect_reference))] = i
    return referencias


def _enlace_interno_nativo(anotacion, paginas):
    """Destinos locales del índice, sin acciones; se comparan con el original."""
    if (not isinstance(anotacion, DictionaryObject) or anotacion.get('/Subtype') != '/Link'
            or '/A' in anotacion):
        return False
    destino = _resolver(anotacion.get('/Dest'))
    if not isinstance(destino, ArrayObject) or len(destino) < 2 or id(_resolver(destino[0])) not in paginas:
        return False
    longitudes = {'/Fit': 2, '/FitB': 2, '/FitH': 3, '/FitBH': 3, '/FitV': 3,
                  '/FitBV': 3, '/XYZ': 5, '/FitR': 6}
    return (longitudes.get(str(destino[1])) == len(destino) and
            all(isinstance(_resolver(v), (NumberObject, FloatObject, NullObject)) for v in destino[2:]))


def _enlaces_de_pagina(pagina, paginas):
    enlaces = []
    for referencia in _resolver(pagina.get('/Annots', [])):
        anotacion = _resolver(referencia)
        if isinstance(anotacion, DictionaryObject) and anotacion.get('/Subtype') == '/Link':
            if not (_enlace_uri_nativo(anotacion) or _enlace_interno_nativo(anotacion, paginas)):
                raise ValidationError('El PDF contiene un enlace o una acción web no admitidos.')
            # /P es exclusivamente la referencia inversa a la página: puede
            # cambiar al reescribir el contenedor y produce un ciclo legítimo.
            enlaces.append(DictionaryObject({k: v for k, v in anotacion.items() if k != '/P'}))
    return _canonico(enlaces, paginas=paginas)


def _widgets_firma(reader):
    widgets = []
    paginas = _referencias_paginas(reader)
    for indice, pagina in enumerate(reader.pages):
        rectangulos = []
        for referencia in _resolver(pagina.get('/Annots', [])):
            anotacion = _resolver(referencia)
            if _enlace_uri_nativo(anotacion) or _enlace_interno_nativo(anotacion, paginas):
                continue
            if anotacion.get('/Subtype') != '/Widget' or not _campo_firma(anotacion):
                raise ValidationError('El PDF contiene anotaciones ajenas a una firma.')
            rect = [float(v) for v in _resolver(anotacion.get('/Rect', []))]
            if len(rect) != 4:
                raise ValidationError('No se puede comprobar el área ocupada por la firma.')
            rectangulos.append(tuple(rect))
        widgets.append((indice, rectangulos))
    return widgets


def _huella_paginas(reader):
    paginas = []
    referencias = _referencias_paginas(reader)
    for pagina in reader.pages:
        contenido = pagina.get_contents()
        paginas.append(dict(contenido=hashlib.sha256(contenido.get_data() if contenido is not None else b'').hexdigest(),
            recursos=_canonico(pagina.get('/Resources', DictionaryObject())),
            enlaces=_enlaces_de_pagina(pagina, referencias),
            atributos=_canonico(DictionaryObject({k: v for k, v in pagina.items()
                if k not in ('/Parent', '/Contents', '/Resources', '/Annots', '/Metadata', '/StructParents')}))))
    catalogo = DictionaryObject({k: v for k, v in reader.trailer['/Root'].items()
        if k not in ('/Pages', '/Outlines', '/Metadata', '/AcroForm', '/Perms', '/DSS', '/Extensions')})
    indice = _canonico(reader.trailer['/Root'].get('/Outlines'), paginas=referencias, indice=True)
    return hashlib.sha256(json.dumps(dict(paginas=paginas, catalogo=_canonico(catalogo), indice=indice),
        sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def comparar_pdf_nativo(original, cargado):
    """Comparación estricta y conservadora: una excepción requiere revisión."""
    lectores = [PdfReader(BytesIO(datos), strict=False) for datos in (original, cargado)]
    for lector in lectores:
        if lector.is_encrypted or not lector.pages or len(lector.pages) > 500:
            raise ValidationError('El PDF debe ser legible, sin cifrado y de hasta 500 páginas.')
        _sin_contenido_activo(lector)
    origen, actual = lectores
    widgets_original, widgets_actual = _widgets_firma(origen), _widgets_firma(actual)
    for (indice, permitidos), (_, presentes) in zip(widgets_original, widgets_actual):
        for rect in presentes:
            if rect[0] != rect[2] and rect[1] != rect[3] and rect not in permitidos:
                raise ValidationError(f'La firma visible añadida en la página {indice + 1} requiere revisión: '
                                      'no había un campo de firma reservado en el original.')
    if len(origen.pages) != len(actual.pages) or _huella_paginas(origen) != _huella_paginas(actual):
        raise ValidationError('Las páginas o sus recursos no coinciden con el original preparado por el sistema.')
    return True


def _bytes_del_recurso(recurso):
    if not recurso.archivo:
        raise ValidationError('El archivo archivado no está disponible.')
    with recurso.archivo.open('rb') as archivo:
        datos = archivo.read(MAXIMO_BYTES + 1)
    if not datos or len(datos) > MAXIMO_BYTES:
        raise ValidationError('El archivo debe tener contenido y no superar 25 MB.')
    huella = hashlib.sha256(datos).hexdigest()
    if huella != recurso.hash_sha256:
        raise ValidationError('Los bytes del archivo no coinciden con su huella archivada.')
    return datos, huella


def registrar_procedencia_nativa(documento, usuario):
    """Ancla del servidor llamada sólo dentro del comando nativo de generación.

    No recibe una declaración del navegador ni concede firma o aprobación.
    Debe ejecutarse en la misma transacción que `_generar`.
    """
    if not es_unidad_auditable(documento.unidad) or not documento.recurso_id:
        return None
    from apps.documentos.presentation.expediente_archivos import identidad_documental
    if documento.estado != 'generado' or documento.recurso.version != documento.version:
        raise ValidationError('Sólo se registra la procedencia de la versión nativa recién generada.')
    datos, huella = _bytes_del_recurso(documento.recurso)
    _, metadatos = _leer_archivo(ContentFile(datos, name='origen.pdf'))
    contenido = dict(identidad_documental(documento), version=documento.version,
                     recurso_id=documento.recurso_id, sha256=huella, metadatos=metadatos)
    if documento.exigido.redactable:
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.presentation.automatizacion_documental import huella as huella_datos
        redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).values_list('contenido', flat=True).first()
        contenido['redaccion_sha256'] = huella_datos(redaccion or {})
    fuentes = getattr(documento, '_fuentes_control_generacion', None)
    if isinstance(fuentes, dict):
        contenido.update(fuentes_sha256=fuentes['sha256'], metodo_fuentes=fuentes['metodo'])
    return registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='archivar',
        objeto=documento, descripcion=AUDITORIA_PROCEDENCIA, nuevos=contenido)


def comprobar_procedencia(documento):
    """Lee archivos y auditoría; nunca modifica notas, revisiones ni estados."""
    resultado = dict(confiable=False, archivo_integro=False, origen_recurso=None, origen_version=None,
        sha256='', origen_sha256='', motivos=[], firma_estructural=False,
        fuentes_sha256='', metodo_fuentes='',
        firma_criptografica={'estado': 'no_comprobada' if documento.exigido.requiere_firma else 'no_requerida',
            'detalle': 'La detección de firma no acredita el certificado, su cadena ni su revocación.',
            'motor_disponible': False}, identidad_verificada=False, contexto_verificado=False,
        contenido_equivalente=False)
    if not es_unidad_auditable(documento.unidad):
        resultado['motivos'].append('La comprobación automática sólo está habilitada para laboratorios.')
        return resultado
    if not documento.recurso_id:
        resultado['motivos'].append('Falta el archivo de la entrega.')
        return resultado
    try:
        actual = documento.recurso
        if (actual.unidad_id != documento.unidad_id or not actual.activo or actual.estado == 'obsoleto'
                or actual.version != documento.version):
            raise ValidationError('El recurso vigente no pertenece a la unidad o está retirado.')
        datos_actuales, huella_actual = _bytes_del_recurso(actual)
        resultado.update(archivo_integro=True, sha256=huella_actual)
        registros = list(RegistroAuditoriaUnidad.objects.filter(unidad_id=documento.unidad_id,
            entidad=documento._meta.label, objeto_id=str(documento.pk)).order_by('-pk'))
        preparados = [r for r in registros if r.accion == 'archivar' and
                      r.descripcion == AUDITORIA_INTEGRIDAD + 'preparar']
        generados = [r for r in registros if r.accion == 'actualizar' and
                    r.descripcion.startswith('_generar:') and r.datos_nuevos.get('estado') == 'generado']
        anclas = [r for r in registros if r.accion == 'archivar' and r.descripcion == AUDITORIA_PROCEDENCIA]
        if anclas:
            base = anclas[0].datos_nuevos
        elif not documento.exigido.es_anexo:
            if not preparados:
                raise ValidationError('No existe una preparación nativa archivada para esta entrega; los metadatos solos no acreditan origen.')
            base = preparados[0].datos_nuevos
        else:
            # Un cierre previamente preparado también conserva SHA y versión
            # de cada anexo nativo. No se infiere del recurso actual mutable.
            from apps.documentos.presentation.evaluacion_cierre import VERSIONES
            cierres = RegistroAuditoriaUnidad.objects.filter(unidad_id=documento.unidad_id,
                entidad=documento._meta.label, accion__in=('archivar', 'enviar'),
                datos_nuevos__metodo__in=VERSIONES, datos_nuevos__anexos__isnull=False).order_by('-pk')
            base = next((a for r in cierres for a in r.datos_nuevos['anexos']
                         if a.get('documento') == documento.pk and a.get('recurso') == actual.pk), None)
            if base:
                base = dict(base, recurso_id=base['recurso'])
            else:
                raise ValidationError('No existe una preparación nativa con huella archivada para este anexo.')
        origen_id, version = base.get('recurso_id'), base.get('version')
        resultado.update(redaccion_sha256=base.get('redaccion_sha256') or '',
                         fuentes_sha256=base.get('fuentes_sha256') or '',
                         metodo_fuentes=base.get('metodo_fuentes') or '')
        if type(origen_id) is not int or type(version) is not int or version > documento.version:
            raise ValidationError('La versión o el recurso de preparación no son comprobables.')
        comando = next((r for r in generados if r.datos_nuevos.get('recurso_id') == origen_id and
                        r.datos_nuevos.get('version') == version and
                        r.datos_nuevos.get('unidad_id') == documento.unidad_id and
                        r.datos_nuevos.get('exigido_id') == documento.exigido_id), None)
        if comando is None:
            raise ValidationError('La preparación no está vinculada a un comando nativo de generación.')
        origen = Recurso.objects.filter(pk=origen_id, unidad_id=documento.unidad_id, version=version).first()
        if not origen:
            raise ValidationError('No se encuentra el original preparado de esta unidad y versión.')
        cadena, siguiente = set(), actual
        while siguiente and siguiente.pk not in cadena and len(cadena) < 64:
            cadena.add(siguiente.pk)
            if siguiente.pk == origen_id:
                break
            siguiente = Recurso.objects.filter(pk=siguiente.reemplaza_a_id, unidad_id=documento.unidad_id).first()
        if origen_id not in cadena:
            raise ValidationError('La entrega no conserva la cadena de versiones del original preparado.')
        bytes_origen, huella_origen = _bytes_del_recurso(origen)
        if base.get('sha256') != huella_origen:
            raise ValidationError('El original no conserva la huella registrada durante su preparación.')
        if actual.pk != origen_id and not any(r.accion == 'actualizar' and
                r.descripcion.startswith('cargar_documento:') and
                r.datos_nuevos.get('recurso_id') == actual.pk and
                r.datos_nuevos.get('version') == documento.version and
                r.datos_nuevos.get('unidad_id') == documento.unidad_id and
                r.datos_nuevos.get('exigido_id') == documento.exigido_id for r in registros):
            raise ValidationError('La versión cargada no conserva su operación de carga auditada.')
        resultado.update(origen_recurso=origen.pk, origen_version=version, origen_sha256=huella_origen)
        _, metadatos_origen = _leer_archivo(ContentFile(bytes_origen, name='origen.pdf'))
        _, metadatos_actuales = _leer_archivo(ContentFile(datos_actuales, name='actual.pdf'))
        if not documento.exigido.es_anexo:
            if (not metadatos_origen or base.get('metadatos') != metadatos_origen or
                    metadatos_actuales != metadatos_origen or not _identidad_coincide(documento, metadatos_origen)
                    or metadatos_origen.get('borrador') is not False):
                raise ValidationError('La identidad o el contexto del PDF no coincide con la preparación nativa archivada.')
            if (documento.estado != 'validado' and documento.exigido.redactable and
                    metadatos_origen.get('contexto_sha256') != _contexto_actual(documento)):
                raise ValidationError('El contexto del editor o de sus fuentes cambió después de preparar el PDF.')
        resultado.update(identidad_verificada=True, contexto_verificado=True)
        if documento.exigido.requiere_firma:
            if documento.verificacion_qr:
                from .aprobacion_en_linea import comprobar_emision
                comprobar_emision(documento)
                if bytes_origen != datos_actuales:
                    raise ValidationError('La emisión en plataforma no conserva el archivo original.')
                resultado['aprobacion_en_plataforma'] = True
            elif not documento.firma_verificada:
                raise ValidationError('Falta la comprobación estructural del PDF firmado cargado.')
            else:
                validar_pdf_firmado(ContentFile(datos_actuales, name='firmado.pdf'))
                resultado['firma_estructural'] = True
        elif bytes_origen != datos_actuales:
            raise ValidationError('El documento sin firma no conserva los bytes exactos del original nativo.')
        # La igualdad exacta ya demuestra equivalencia con el original nativo
        # cuya generación, identidad y huella se comprobaron arriba. Una carga
        # distinta conserva la comparación estructural completa.
        if bytes_origen != datos_actuales:
            comparar_pdf_nativo(bytes_origen, datos_actuales)
        resultado.update(contenido_equivalente=True, confiable=True)
    except Exception as error:
        resultado['motivos'].extend(error.messages if isinstance(error, ValidationError) else
                                   [str(error) if isinstance(error, ValueError) else 'No se pudo comprobar el archivo y su procedencia.'])
    return resultado
