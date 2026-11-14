"""Contenido inmutable para renovar el diseño sin volver a consultar datos operativos."""
import json
import re
from collections import defaultdict
from copy import deepcopy
from datetime import date
from io import BytesIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError


def contenido_pac_enviado(documento):
    """Contenido nativo enviado, ligado al archivo vigente y a sus fuentes fijadas.

    La pertenencia de áreas y activos se comprueba al emitir y enviar. Una
    decisión posterior revisa ese documento, aunque la organización de la
    unidad haya cambiado después; nunca convierte un borrador en antecedente.
    """
    if (getattr(documento, 'estado', '') != 'validado'
            or not getattr(documento, 'verificacion_qr', None)
            or not getattr(documento, 'recurso_id', None)
            or getattr(documento.exigido, 'codigo', '') != 'PLAN-COMPRAS-ANUAL'):
        return None
    recurso = documento.recurso
    if (recurso.unidad_id != documento.unidad_id or recurso.version != documento.version
            or not recurso.activo or recurso.estado == 'obsoleto'):
        return None
    from apps.documentos.models.constancias import ConstanciaDocumento
    constancia = ConstanciaDocumento.objects.filter(documento_id=documento.pk,
        token=documento.verificacion_qr, recurso_id=documento.recurso_id, version=documento.version,
        sha256=recurso.hash_sha256, enviado_en__isnull=False).first()
    if (constancia is None or constancia.observado_en is not None
            or not isinstance(constancia.contenido_emitido, dict)):
        return None
    contenido = constancia.contenido_emitido.get('pac_datos')
    fuentes = contenido.get('diagnostico_compras_fuentes') if isinstance(contenido, dict) else None
    if (not isinstance(contenido, dict) or type(contenido.get('pac_version')) is not int
            or contenido['pac_version'] != 2 or not isinstance(fuentes, dict)
            or type(fuentes.get('version')) is not int or fuentes['version'] != 1
            or type(fuentes.get('unidad')) is not int or type(fuentes.get('anio')) is not int
            or fuentes.get('unidad') != documento.unidad_id or fuentes.get('anio') != documento.anio
            or not isinstance(fuentes.get('areas'), list)):
        return None
    return deepcopy(contenido)


def conservar_compuesto(compuesto):
    from .expediente_archivos import metadatos_documentales
    claves = ('tipo', 'titulo', 'codigo_formato', 'codigo_etiqueta', 'periodo', 'version', 'tramo', 'secciones', 'firmas', 'pac_datos')
    datos = {k: compuesto[k] for k in claves if k in compuesto}
    datos['unidad_nombre'] = compuesto['unidad'].nombre
    datos['trazabilidad'] = metadatos_documentales(compuesto)
    from .validacion_pdf import datos_de_emision
    datos['url_verificacion'] = (datos_de_emision(compuesto.get('documento')) or {}).get('url','')
    return json.loads(json.dumps(datos, default=str, ensure_ascii=False))


def restaurar_compuesto(datos, constancia):
    from .aprobacion_en_linea import url_verificacion
    resultado = dict(datos, documento=constancia.documento, unidad=SimpleNamespace(nombre=constancia.unidad_nombre))
    resultado['tramo'] = tuple(date.fromisoformat(str(v)) for v in datos['tramo'])
    resultado['version'] = constancia.version
    resultado['_trazabilidad_emitida'] = datos.get('trazabilidad')
    resultado['_fecha_elaboracion'] = constancia.emitido_en
    resultado['_validacion'] = dict(url=datos.get('url_verificacion') or url_verificacion(constancia.token), version=constancia.version,
        emisor=constancia.emisor_nombre, emisor_cedula=constancia.emisor_cedula, emitido_en=constancia.emitido_en,
        aprobador=constancia.aprobador_nombre, aprobador_cedula=constancia.aprobador_cedula, aprobado_en=constancia.aprobado_en)
    return resultado


def _punto(x, y, cm):
    return (round(cm[0]*x + cm[2]*y + cm[4], 2), round(cm[1]*x + cm[3]*y + cm[5], 2))


def _pagina(pagina):
    textos, lineas, camino = [], [], []
    ultimo = None
    alto = float(pagina.mediabox.height)
    def texto(valor, cm, tm, fuente, tamano):
        if not valor.strip():
            return
        x, y = _punto(tm[4], tm[5], cm)
        if 52 < y < alto-96:
            textos.append(dict(texto=valor.replace('\x7f','•').strip(), x=x, y=y, size=float(tamano),
                bold='Bold' in str((fuente or {}).get('/BaseFont', ''))))
    def operacion(op, args, cm, tm):
        nonlocal ultimo
        if op == b'n':
            camino.clear()
            ultimo = None
        elif op == b'm':
            ultimo = _punto(float(args[0]), float(args[1]), cm)
        elif op == b'l' and ultimo:
            siguiente = _punto(float(args[0]), float(args[1]), cm)
            camino.append((*ultimo, *siguiente))
            ultimo = siguiente
        elif op == b're':
            x, y, w, h = map(float, args)
            puntos = [_punto(a, b, cm) for a, b in ((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y))]
            camino.extend((*a,*b) for a,b in zip(puntos,puntos[1:]))
        elif op in (b'S', b's', b'B', b'B*', b'b', b'b*'):
            lineas.extend(linea for linea in camino if 52 < min(linea[1], linea[3]) and max(linea[1], linea[3]) < alto-96)
            camino.clear()
            ultimo = None
        elif op in (b'f', b'F', b'f*'):
            camino.clear()
            ultimo = None
    pagina.extract_text(visitor_text=texto, visitor_operand_before=operacion)
    verticales, horizontales = [], []
    for x1,y1,x2,y2 in lineas:
        if abs(x1-x2)<.2 and abs(y1-y2)>3:
            verticales.append((x1,min(y1,y2),max(y1,y2)))
        elif abs(y1-y2)<.2 and abs(x1-x2)>5:
            horizontales.append((y1,min(x1,x2),max(x1,x2)))
    grupos = defaultdict(set)
    for x,y1,y2 in verticales:
        grupos[(round(y1,1),round(y2,1))].add(round(x,1))
    tablas = []
    for (abajo,arriba), xs_completas in grupos.items():
        if len(xs_completas)<2:
            continue
        izq,der = min(xs_completas),max(xs_completas)
        if der-izq<40:
            continue
        ys = sorted({round(y,1) for y,x1,x2 in horizontales if abajo-.3<=y<=arriba+.3 and x1<=izq+.3 and x2>=der-.3},reverse=True)
        xs = sorted({round(x,1) for x,y1,y2 in verticales if izq-.3<=x<=der+.3 and abajo-.3<=y1<y2<=arriba+.3})
        if len(ys)<2 or len(xs)<2:
            continue
        tablas.append(dict(x=izq,y=arriba,abajo=abajo,der=der,xs=xs,ys=ys))
    # Las cuadrículas pequeñas incluidas en otra tabla no duplican sus celdas.
    tablas = [t for t in tablas if not any(t is not otra and otra['x']<=t['x'] and otra['der']>=t['der']
        and otra['abajo']<=t['abajo'] and otra['y']>=t['y'] and (otra['der']-otra['x'])*(otra['y']-otra['abajo'])>
        (t['der']-t['x'])*(t['y']-t['abajo']) for otra in tablas)]
    asignados = set()
    elementos = []
    for tabla in tablas:
        celdas = defaultdict(list)
        for i,t in enumerate(textos):
            if tabla['x']-.2<=t['x']<tabla['der'] and tabla['abajo']<t['y']<tabla['y']:
                col = next((j for j,(a,b) in enumerate(zip(tabla['xs'],tabla['xs'][1:])) if a-.2<=t['x']<b-.2),None)
                fila = next((j for j,(a,b) in enumerate(zip(tabla['ys'],tabla['ys'][1:])) if b<t['y']<a),None)
                if col is not None and fila is not None:
                    celdas[(fila,col)].append(t)
                    asignados.add(i)
        def valor(i,j):
            partes=[t['texto'].replace('\n',' ').strip() for t in sorted(celdas[(i,j)],key=lambda t:(-t['y'],t['x']))]
            if len(partes)>1 and '-' in ''.join(partes) and all(re.fullmatch(r'[A-Z0-9._/\-]+',p) for p in partes):
                return ''.join(partes)
            return ' '.join(partes)
        filas = [[valor(i,j) for j in range(len(tabla['xs'])-1)] for i in range(len(tabla['ys'])-1)]
        if not filas:
            continue
        pares = len(filas[0])==2 and all(any(t['bold'] for t in celdas[(i,0)]) and not any(t['bold'] for t in celdas[(i,1)]) for i in range(len(filas)))
        if pares:
            bloque = dict(tipo='pares',pares=filas,titulo='')
        else:
            cabecera = any(t['bold'] for j in range(len(filas[0])) for t in celdas[(0,j)])
            bloque = dict(tipo='tabla',titulo='',cabecera=filas[0] if cabecera else ['']*len(filas[0]),filas=filas[1:] if cabecera else filas,
                anchos_relativos=[(b-a)/(tabla['der']-tabla['x']) for a,b in zip(tabla['xs'],tabla['xs'][1:])])
        elementos.append(dict(y=tabla['y'],bloque=bloque))
    lineas_texto = defaultdict(list)
    for i,t in enumerate(textos):
        if i not in asignados:
            lineas_texto[round(t['y'])].append(t)
    for y, fragmentos in lineas_texto.items():
        fragmentos.sort(key=lambda t:t['x'])
        elementos.append(dict(y=y,texto=' '.join(t['texto'].replace('\n',' ') for t in fragmentos),
            size=max(t['size'] for t in fragmentos),bold=all(t['bold'] for t in fragmentos)))
    return sorted(elementos,key=lambda t:-t['y'])


def _secciones_del_pdf(pdf, *, conservar_firmas=False):
    """Recupera el cuerpo archivado, sin consultar registros operativos actuales."""
    secciones, actual = [], None
    for pagina in pdf.pages:
        for e in _pagina(pagina):
            texto = e.get('texto','').strip()
            cabecera = re.match(r'^(\d+)\.\s+(.+)',texto) if e.get('bold') and e.get('size',0)>=10 else None
            if cabecera:
                titulo = cabecera[2]
                if 'FIRMAS DE RESPONSABILIDAD' in titulo.upper() or 'VALIDACIÓN DOCUMENTAL' in titulo.upper():
                    if not conservar_firmas:
                        actual = None
                        break
                actual = dict(numero=len(secciones)+1,codigo=f'archivado-{cabecera[1]}',titulo=titulo,bloques=[])
                secciones.append(actual)
            elif actual:
                bloques=actual['bloques']
                if 'bloque' in e:
                    b=e['bloque']
                    if bloques and b['tipo']=='tabla' and bloques[-1]['tipo']=='tabla' and (
                            b['cabecera']==bloques[-1]['cabecera'] or
                            not any(b['cabecera']) and len(b['cabecera'])==len(bloques[-1]['cabecera'])):
                        bloques[-1]['filas'].extend(b['filas'])
                    else:
                        bloques.append(b)
                elif texto and not texto.startswith('Referencia interna de trazabilidad:'):
                    if e.get('bold') and e.get('size',0)>=10 and not bloques:
                        actual['titulo']+=' '+texto
                    elif e.get('bold'):
                        bloques.append(dict(tipo='subtitulo',texto=texto))
                    elif bloques and bloques[-1]['tipo']=='parrafo' and not texto.startswith(('•','●')):
                        bloques[-1]['texto']+=' '+texto
                    else:
                        bloques.append(dict(tipo='parrafo',texto=texto))
    if not secciones:
        raise ValidationError('No se pudieron identificar las secciones del documento archivado.')
    return secciones


def recuperar_del_pdf(contenido, constancia):
    """Sólo interpreta el PDF nativo archivado: no consulta inventario, metas ni calendario actuales."""
    from pypdf import PdfReader
    from .expediente_archivos import MARCA_INTEGRIDAD
    import base64
    pdf = PdfReader(BytesIO(contenido))
    asunto = str((pdf.metadata or {}).get('/Subject',''))
    if not asunto.startswith(MARCA_INTEGRIDAD) or any(v.get('/FT')=='/Sig' for v in (pdf.get_fields() or {}).values()):
        raise ValidationError('El documento no contiene una estructura nativa de reportes.')
    trazabilidad = json.loads(base64.urlsafe_b64decode(asunto[len(MARCA_INTEGRIDAD):]))
    secciones = _secciones_del_pdf(pdf)
    secciones.append(dict(numero=len(secciones)+1,codigo='firmas',titulo='Validación documental',bloques=[]))
    # Las fechas del tramo provienen de la identidad documental conservada.
    from .expediente import tramo_del_documento
    inicio,fin=tramo_del_documento(constancia.documento)
    referencia = re.search(r'\bSLCID-[A-Z0-9-]+', pdf.pages[0].extract_text() or '')
    enlace = next((str(a.get_object().get('/A',{}).get('/URI','')) for p in pdf.pages for a in p.get('/Annots',[])
        if str(constancia.token) in str(a.get_object().get('/A',{}).get('/URI',''))),'')
    return dict(tipo=constancia.documento.exigido.fuente_reporte,titulo=constancia.titulo,
        codigo_formato=referencia[0] if referencia else constancia.documento.exigido.codigo,
        codigo_etiqueta='Código de referencia',periodo=constancia.periodo,version=constancia.version,
        tramo=[inicio.isoformat(),fin.isoformat()],unidad_nombre=constancia.unidad_nombre,
        secciones=secciones,firmas=[],trazabilidad=trazabilidad,url_verificacion=enlace)


def recuperar_preparado_anterior(contenido, documento):
    """Renueva sólo la presentación de una preparación nativa anterior al QR.

    El comando de generación, la identidad del archivo y su hash se comprueban
    antes de recuperar texto y tablas. No crea constancias ni acredita firmas.
    """
    import hashlib
    from datetime import datetime
    from pypdf import PdfReader
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad

    recurso = documento.recurso
    if (documento.estado != 'generado' or documento.verificacion_qr or documento.firma_verificada
            or not recurso or not recurso.activo or recurso.estado != 'vigente'
            or recurso.unidad_id != documento.unidad_id or recurso.version != documento.version):
        return None
    registro = RegistroAuditoriaUnidad.objects.filter(unidad_id=documento.unidad_id,
        entidad=documento._meta.label, objeto_id=str(documento.pk), accion='actualizar',
        descripcion__startswith='_generar:', datos_nuevos__recurso_id=recurso.pk,
        datos_nuevos__version=documento.version, datos_nuevos__estado='generado',
        datos_nuevos__unidad_id=documento.unidad_id, datos_nuevos__exigido_id=documento.exigido_id).first()
    if not registro:
        return None
    if hashlib.sha256(contenido).hexdigest() != recurso.hash_sha256:
        raise ValidationError('El archivo preparado fue modificado.')
    pdf = PdfReader(BytesIO(contenido))
    from .confianza_documental import _campo_firma
    if (pdf.is_encrypted or pdf.trailer['/Root'].get('/Perms')
            or any(v.get('/FT') == '/Sig' for v in (pdf.get_fields() or {}).values())
            or any(_campo_firma(a) for p in pdf.pages for a in p.get('/Annots', []))):
        return None
    if pdf.outline:
        # Los informes que ya tienen portada e índice usan su archivo actual.
        return None
    metadata = pdf.metadata or {}
    if not str(metadata.get('/Producer', '')).startswith('ReportLab'):
        return None
    titulo, separador, unidad = str(metadata.get('/Title', '')).rpartition(' - ')
    if not separador or not titulo or not unidad:
        return None
    primera = pdf.pages[0].extract_text() or ''
    version = re.search(r'Versión del documento:\s*(\d+)', primera)
    fechas = re.search(r'(\d{2}/\d{2}/\d{4})\s*[–-]\s*(\d{2}/\d{2}/\d{4})', primera)
    cobertura = re.search(r'Cobertura:\s*([^\n]+)', primera)
    codigo = re.search(r'(?:Código|Referencia interna):\s*([^\n]+)', primera)
    if (not version or int(version[1]) != documento.version or not fechas or not cobertura
            or not codigo or titulo not in ' '.join(primera.split())):
        return None
    secciones = _secciones_del_pdf(pdf, conservar_firmas=True)
    firmas = []
    cuerpo = []
    for seccion in secciones:
        if 'FIRMAS DE RESPONSABILIDAD' in seccion['titulo'].upper():
            for b in seccion['bloques']:
                if b['tipo'] == 'pares':
                    for rol, persona in b['pares']:
                        nombre, _, cargo = persona.partition(' · ')
                        firmas.append((rol, nombre, cargo))
            continue
        for b in list(seccion['bloques']):
            if b['tipo'] != 'pares':
                continue
            equipo = next((v for k, v in b['pares'] if k == 'Equipo de la unidad'), '')
            if equipo:
                personas = []
                for persona in equipo.split(';'):
                    nombre, _, cargo = persona.strip().partition(' (')
                    personas.append([nombre, cargo.rstrip(')')])
                b['pares'] = [(k, v) for k, v in b['pares'] if k != 'Equipo de la unidad']
                seccion['bloques'].append(dict(tipo='tabla', titulo='Equipo de la unidad',
                    cabecera=['Nombre', 'Cargo'], filas=personas))
        cuerpo.append(seccion)
    return dict(documento=documento, tipo=documento.exigido.fuente_reporte, titulo=titulo,
        unidad=SimpleNamespace(nombre=unidad), codigo_formato=codigo[1].strip(),
        codigo_etiqueta='Código de referencia', periodo=cobertura[1].strip(), version=documento.version,
        tramo=tuple(datetime.strptime(v, '%d/%m/%Y').date() for v in fechas.groups()),
        secciones=cuerpo, firmas=firmas, _trazabilidad_emitida=None,
        _fecha_elaboracion=metadata.creation_date or documento.generado_en,
        _presentacion_archivada=True)


def bloques_de_presentacion(seccion):
    """Presenta el equipo en una tabla, conservando nombres, cargos y funciones."""
    bloques = list(seccion['bloques'])
    resultado=[]
    i=0
    while i<len(bloques):
        bloque=bloques[i]
        if bloque['tipo']=='subtitulo' and bloque.get('texto','').casefold()=='personas registradas en la unidad':
            filas=[]
            j=i+1
            while j<len(bloques) and bloques[j]['tipo']=='parrafo' and bloques[j].get('texto','').startswith(('•','●')):
                partes=bloques[j]['texto'].lstrip('•● ').split(' · ',2)
                filas.append(partes+['']*(3-len(partes)))
                j+=1
            if filas:
                resultado.append(dict(tipo='tabla',titulo='Equipo de la unidad',
                    cabecera=['Nombre','Cargo','Responsabilidades'],filas=filas))
                i=j
                continue
        resultado.append(bloque)
        i+=1
    return resultado
