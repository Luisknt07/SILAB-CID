"""Diseño autocontenido del certificado, sin depender de archivos editables tras emitirlo."""
import base64
from io import BytesIO
from types import SimpleNamespace
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.formacion.models.cursos_certificacion import TEXTO_APROBACION, TEXTO_ASISTENCIA, TEXTO_ORGANIZADOR, TEXTO_PARTICIPACION, TEXTO_PONENTE
from apps.formacion.presentation.notas_cursos import nota_sobre_diez


def imagen_png(origen, maximo=(1000, 400)):
    """Normaliza imágenes raster; no conserva metadatos ni referencias a archivos externos."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not origen:
        return ''
    # FieldFile abre un descriptor al accederlo: cerramos sólo el que abre este helper.
    # Consultar .read de FieldFile ya abriría .file; comprobar .closed antes de ello.
    estaba_cerrado = getattr(origen, 'closed', False)
    from os import PathLike
    es_archivo = hasattr(origen, 'open') and not isinstance(origen, (str, bytes, PathLike))
    abierto_por_helper = es_archivo and estaba_cerrado
    try:
        if es_archivo:
            origen.open('rb')
        if hasattr(origen, 'seek'):
            origen.seek(0)
        with Image.open(origen) as imagen:
            if imagen.width * imagen.height > 12_000_000:
                raise ValidationError('La imagen es demasiado grande. Use hasta 12 megapíxeles.')
            imagen = ImageOps.exif_transpose(imagen).convert('RGBA')
            imagen.thumbnail(maximo, Image.Resampling.LANCZOS)
            salida = BytesIO()
            imagen.save(salida, format='PNG', optimize=True)
        return base64.b64encode(salida.getvalue()).decode('ascii')
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValidationError('La imagen no se puede leer. Use una imagen PNG o JPEG válida.') from exc
    finally:
        if abierto_por_helper:
            origen.close()
        elif hasattr(origen, 'seek'):
            try:
                origen.seek(0)
            except (ValueError, OSError):
                pass


def _horas_v1(valor):
    from decimal import Decimal
    return format(Decimal(str(valor or 0)).normalize(), 'f')


def _crear_diseno_v1(certificado, configuracion=None, firmante_base=None):
    """Congela texto resuelto, institución, colores, imágenes y verificación en un JSON."""
    # Textos históricos congelados: los nuevos valores predeterminados no cambian emisiones previas.
    TEXTO_APROBACION = ('Aprobó el {tipo} «{curso}», con una duración de {horas} horas, '
                        'dictado por {unidad}, en su edición {edicion}.')
    TEXTO_PARTICIPACION = ('Participó y completó el {tipo} «{curso}», con una duración de {horas} horas, '
                           'dictado por {unidad}, en su edición {edicion}.')
    from apps.core.presentation.identidad import identidad_actual, logo_institucional
    from apps.formacion.presentation.certificados_cursos import direccion_de_verificacion

    institucion = identidad_actual()[1]
    paleta = dict(institucion.paleta)
    configuracion = configuracion or SimpleNamespace()
    mostrar_nota = getattr(configuracion, 'mostrar_nota', True)
    nota = nota_sobre_diez(certificado.nota_final) if certificado.nota_final is not None else None
    fecha = timezone.localtime(certificado.emitido_en).strftime('%d/%m/%Y')
    variables = {
        'nombre': certificado.nombre, 'curso': certificado.curso_nombre,
        'horas': _horas_v1(certificado.horas), 'edicion': certificado.edicion,
        'unidad': certificado.unidad_nombre, 'fecha': fecha,
        'nota': (f'{nota:.3f}'.rstrip('0').rstrip('.').replace('.', ',') + '/10' if nota is not None and mostrar_nota else 'No aplica'),
        'tipo': certificado.clasificacion.lower(),
    }
    aprobacion = certificado.tipo == 'aprobacion'
    titulo = getattr(configuracion, 'titulo_aprobacion' if aprobacion else 'titulo_participacion',
                     'CERTIFICADO DE APROBACIÓN' if aprobacion else 'CERTIFICADO DE PARTICIPACIÓN')
    texto = getattr(configuracion, 'texto_aprobacion' if aprobacion else 'texto_participacion',
                    TEXTO_APROBACION if aprobacion else TEXTO_PARTICIPACION)
    # La configuración pasa por validación de llaves/variables antes de llegar aquí.
    titulo, texto = titulo.format_map(variables), texto.format_map(variables)
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    if not certificado.horas and texto in (TEXTO_APROBACION.format_map(variables), TEXTO_PARTICIPACION.format_map(variables)):
        texto = texto.replace(', con una duración de 0 horas', '')
    firma_base, cargo_base = firmante_base or (certificado.firma_nombre, certificado.firma_cargo)
    if not getattr(configuracion, 'usar_firmante_curso', True):
        firma_base, cargo_base = '', ''
    primer_firmante = {
        'nombre': getattr(configuracion, 'firma_nombre', '') or firma_base,
        'cargo': getattr(configuracion, 'firma_cargo', '') or cargo_base,
        'imagen': imagen_png(getattr(configuracion, 'firma_imagen', None), (800, 300)),
    }
    firmantes = [primer_firmante] if any(primer_firmante.values()) else []
    if getattr(configuracion, 'segunda_firma_nombre', ''):
        firmantes.append({
            'nombre': configuracion.segunda_firma_nombre, 'cargo': configuracion.segunda_firma_cargo,
            'imagen': imagen_png(configuracion.segunda_firma_imagen, (800, 300)),
        })
    logo = logo_institucional(fondo='oscuro')
    return {
        'version': 1, 'titulo': titulo, 'texto': texto,
        'diseno': getattr(configuracion, 'diseno', 'clasico'),
        'primario': getattr(configuracion, 'color_primario', '') or paleta.get('primario', '#1E5A3D'),
        'acento': getattr(configuracion, 'color_acento', '') or paleta.get('acento', '#E1B93F'),
        'institucion': institucion.nombre, 'siglas': institucion.siglas,
        'logo': imagen_png(str(logo)) if logo else '', 'firmantes': firmantes,
        'mostrar_nota': mostrar_nota, 'fecha': fecha,
        'verificacion_url': direccion_de_verificacion(certificado),
    }


def _parrafo(lienzo, texto, x, techo, ancho, altura, color, *, tamano=13, minimo=9.5, negrita=False):
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    while tamano >= minimo:
        estilo = ParagraphStyle('Certificado', fontName='Helvetica-Bold' if negrita else 'Helvetica',
                                 fontSize=tamano, leading=tamano * 1.3, alignment=TA_CENTER, textColor=color)
        parrafo = Paragraph(escape(str(texto)).replace('\n', '<br/>'), estilo)
        _, alto = parrafo.wrap(ancho, altura)
        if alto <= altura:
            parrafo.drawOn(lienzo, x, techo - alto)
            return
        tamano -= .5
    raise ValidationError('El texto no cabe de forma legible. Acórtelo o reduzca las variables repetidas y vuelva a previsualizar.')


def _dibujar_certificado_v1(certificado, mostrar_documento=True, vista_previa=False):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import createBarcodeDrawing
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    diseno = getattr(certificado, 'diseno_certificado', None) or _crear_diseno_v1(certificado)
    primario, acento, oscuro, tenue = (HexColor(diseno['primario']), HexColor(diseno['acento']),
                                       HexColor('#102A25'), HexColor('#526660'))
    ancho, alto = landscape(A4)
    salida = BytesIO()
    lienzo = Canvas(salida, pagesize=(ancho, alto))
    lienzo.setTitle(('Vista previa - ' if vista_previa else '') + f'Certificado {certificado.codigo}')
    lienzo.setAuthor(diseno['institucion'])
    lienzo.setFillColor(white)
    lienzo.rect(0, 0, ancho, alto, fill=1, stroke=0)
    if diseno.get('diseno') == 'sobrio':
        lienzo.setFillColor(primario)
        lienzo.rect(0, alto - 8 * mm, ancho, 8 * mm, fill=1, stroke=0)
        lienzo.setFillColor(acento)
        lienzo.rect(0, alto - 10 * mm, ancho, 2 * mm, fill=1, stroke=0)
        izquierda, derecha = 20 * mm, ancho - 20 * mm
    else:
        lienzo.setFillColor(primario)
        lienzo.rect(0, 0, 13 * mm, alto, fill=1, stroke=0)
        lienzo.setFillColor(acento)
        lienzo.rect(13 * mm, 0, 2 * mm, alto, fill=1, stroke=0)
        izquierda, derecha = 27 * mm, ancho - 17 * mm
    centro, util = (izquierda + derecha) / 2, derecha - izquierda
    lienzo.setStrokeColor(HexColor('#BCCBC3'))
    lienzo.setLineWidth(.7)
    lienzo.rect(izquierda - 5 * mm, 9 * mm, util + 10 * mm, alto - 22 * mm, fill=0, stroke=1)
    lienzo.setFillColor(primario)
    lienzo.roundRect(centro - 38 * mm, 176 * mm, 76 * mm, 22 * mm, 2 * mm, fill=1, stroke=0)
    if diseno.get('logo'):
        imagen = ImageReader(BytesIO(base64.b64decode(diseno['logo'])))
        lienzo.drawImage(imagen, centro - 34 * mm, 179 * mm, 68 * mm, 16 * mm,
                         preserveAspectRatio=True, anchor='c', mask='auto')
    else:
        lienzo.setFillColor(white)
        lienzo.setFont('Helvetica-Bold', 20)
        lienzo.drawCentredString(centro, 183 * mm, diseno.get('siglas', ''))
    _parrafo(lienzo, diseno['institucion'].upper(), izquierda, 172 * mm, util, 9 * mm,
              tenue, tamano=10, minimo=8, negrita=True)
    _parrafo(lienzo, diseno['titulo'], izquierda, 160 * mm, util, 21 * mm,
              oscuro, tamano=27, minimo=17, negrita=True)
    lienzo.setFillColor(acento)
    lienzo.rect(centro - 27 * mm, 136 * mm, 54 * mm, 1.1 * mm, fill=1, stroke=0)
    _parrafo(lienzo, 'Se certifica que', izquierda, 132 * mm, util, 8 * mm, tenue, tamano=11)
    _parrafo(lienzo, certificado.nombre, izquierda + 5 * mm, 123 * mm, util - 10 * mm, 23 * mm,
              primario, tamano=25, minimo=15, negrita=True)
    if mostrar_documento and certificado.documento:
        _parrafo(lienzo, f'Documento de identidad: {certificado.documento}', izquierda, 98 * mm,
                  util, 6 * mm, tenue, tamano=9.5)
    _parrafo(lienzo, diseno['texto'], izquierda + 3 * mm, 89 * mm, util - 6 * mm, 30 * mm,
              oscuro, tamano=12.5, minimo=9.5)
    nota = nota_sobre_diez(certificado.nota_final) if certificado.nota_final is not None else None
    pie = f'Emitido el {diseno["fecha"]}'
    if diseno.get('mostrar_nota', True) and nota is not None:
        pie += '   |   Calificación final: ' + f'{nota:.3f}'.rstrip('0').rstrip('.').replace('.', ',') + '/10'
    _parrafo(lienzo, pie, izquierda, 56 * mm, util, 7 * mm, tenue, tamano=9.5)
    firmantes = diseno.get('firmantes', [])[:2]
    zona_firmas = util - 46 * mm
    ancho_firma = zona_firmas / max(len(firmantes), 1)
    for indice, firma in enumerate(firmantes):
        x = izquierda + indice * ancho_firma
        margen = 5 * mm
        if firma.get('imagen'):
            imagen = ImageReader(BytesIO(base64.b64decode(firma['imagen'])))
            lienzo.drawImage(imagen, x + margen, 40 * mm, ancho_firma - 2 * margen, 11 * mm,
                             preserveAspectRatio=True, anchor='c', mask='auto')
        lienzo.setStrokeColor(oscuro)
        lienzo.line(x + margen, 38 * mm, x + ancho_firma - margen, 38 * mm)
        _parrafo(lienzo, firma.get('nombre', ''), x + margen, 36 * mm,
                  ancho_firma - 2 * margen, 12 * mm, oscuro, tamano=10.5, minimo=8, negrita=True)
        _parrafo(lienzo, firma.get('cargo', ''), x + margen, 22 * mm,
                  ancho_firma - 2 * margen, 13 * mm, tenue, tamano=9, minimo=7.5)
    qr_x = derecha - 35 * mm
    qr = createBarcodeDrawing('QR', value=diseno['verificacion_url'], width=29 * mm, height=29 * mm)
    renderPDF.draw(qr, lienzo, qr_x, 23 * mm)
    _parrafo(lienzo, 'Verifique este certificado', qr_x - 4 * mm, 21 * mm, 37 * mm, 5 * mm,
              tenue, tamano=7.5, minimo=7)
    _parrafo(lienzo, certificado.codigo, qr_x - 4 * mm, 16 * mm, 37 * mm, 5 * mm,
              oscuro, tamano=8, minimo=7, negrita=True)
    if certificado.anulado:
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(.88)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor('#A12B2B'))
        lienzo.setFont('Helvetica-Bold', 25)
        lienzo.drawCentredString(ancho / 2, alto / 2, 'CERTIFICADO ANULADO')
        lienzo.restoreState()
    elif vista_previa:
        # Aviso visible que permite revisar todo el texto del ejemplo.
        lienzo.setFillColor(HexColor('#A12B2B'))
        lienzo.setFont('Helvetica-Bold', 8)
        lienzo.drawCentredString(centro, 4 * mm, 'VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ')
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


# La versión forma parte de la emisión: editar un diseño nunca recompone un PDF anterior.
DISENOS_CERTIFICADO = ('clasico', 'sobrio', 'tecnologico', 'geometrico', 'elegante', 'congreso')


def _fecha_texto(valor):
    if not valor:
        return ''
    return valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor)


def _horas_texto(valor):
    from decimal import Decimal, InvalidOperation
    try:
        return format(Decimal(str(valor or 0)).normalize(), 'f').replace('.', ',')
    except (InvalidOperation, ValueError):
        return str(valor or 0)


def _fondo_logo(imagen):
    """Los logos blancos transparentes necesitan una placa oscura para conservar contraste."""
    from PIL import Image
    with Image.open(BytesIO(base64.b64decode(imagen))) as logo:
        logo = logo.convert('RGBA')
        logo.thumbnail((64, 32))
        pixeles = list(logo.getdata())
    visibles = [(r, g, b) for r, g, b, a in pixeles if a > 128]
    transparencia = sum(a < 128 for _, _, _, a in pixeles) / max(1, len(pixeles))
    luminancia = sum(.2126*r + .7152*g + .0722*b for r, g, b in visibles) / max(1, len(visibles)) / 255
    return 'oscuro' if transparencia > .15 and luminancia > .72 else 'claro'


def _crear_diseno_base_v3(certificado, configuracion=None, firmante_base=None):
    """Congela texto, imágenes y datos de la nueva composición, sin consultas al renderizar."""
    # Defaults históricos V3–V5, independientes de nuevas variables del editor.
    TEXTO_APROBACION = ('Aprobó satisfactoriamente «{curso}» ({tipo}), con una duración de {horas} horas. '
                        'La actividad se desarrolló {periodo}, bajo la organización de {emisor}.')
    TEXTO_PARTICIPACION = ('Participó y completó «{curso}» ({tipo}), con una duración de {horas} horas. '
                           'La actividad se desarrolló {periodo}, bajo la organización de {emisor}.')
    TEXTO_ASISTENCIA = ('Asistió a «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                        'La actividad se desarrolló {periodo}, bajo la organización de {emisor}.')
    TEXTO_PONENTE = ('Participó en calidad de ponente en «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                     'La actividad se desarrolló {periodo}, bajo la organización de {emisor}.')
    TEXTO_ORGANIZADOR = ('Participó en la organización de «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                          'La actividad se desarrolló {periodo}, bajo la organización de {emisor}.')
    from apps.core.presentation.identidad import identidad_actual, logo_institucional
    from apps.formacion.presentation.certificados_cursos import direccion_de_verificacion, periodo_actividad, presentar_fecha

    _, institucion = identidad_actual()
    paleta = dict(institucion.paleta)
    configuracion = configuracion or SimpleNamespace()
    tipo = getattr(certificado, 'tipo', 'participacion')
    tipos = {
        'aprobacion': ('APROBACIÓN', 'participante', TEXTO_APROBACION),
        'participacion': ('PARTICIPACIÓN', 'participante', TEXTO_PARTICIPACION),
        'asistencia': ('ASISTENCIA', 'asistente', TEXTO_ASISTENCIA),
        'ponente': ('PONENTE', 'ponente', TEXTO_PONENTE),
        'organizador': ('ORGANIZACIÓN', 'organizador', TEXTO_ORGANIZADOR),
    }
    etiqueta, rol, texto_base = tipos.get(tipo, tipos['participacion'])
    fecha = presentar_fecha(timezone.localtime(certificado.emitido_en).date())
    inicio = getattr(certificado, 'fecha_inicio', None) or getattr(configuracion, 'fecha_inicio', None)
    final = getattr(certificado, 'fecha_fin', None) or getattr(configuracion, 'fecha_fin', None)
    fecha_inicio, fecha_fin = presentar_fecha(inicio), presentar_fecha(final)
    periodo = periodo_actividad(inicio, final)
    emisor = str(getattr(configuracion, 'emisor', '') or certificado.unidad_nombre).strip()
    entradilla = str(getattr(configuracion, 'entradilla', '') or 'Otorga el presente certificado a').strip()
    from apps.formacion.models.cursos_certificacion import CATEGORIAS_EVENTO
    categoria_clave = str(getattr(certificado, 'categoria_evento', '') or getattr(configuracion, 'categoria_evento', '') or certificado.clasificacion).strip()
    categoria = dict(CATEGORIAS_EVENTO).get(categoria_clave, categoria_clave)
    horas = _horas_texto(certificado.horas)
    variables = {
        'nombre': certificado.nombre, 'curso': certificado.curso_nombre, 'horas': horas,
        'edicion': certificado.edicion, 'unidad': certificado.unidad_nombre, 'fecha': fecha,
        'nota': '', 'tipo': categoria.lower(), 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin,
        'categoria_evento': categoria, 'rol': rol, 'emisor': emisor,
        'periodo': periodo, 'fecha_emision': fecha,
    }
    titulo = str(getattr(configuracion, 'titulo_' + tipo, '') or 'CERTIFICADO DE ' + etiqueta).format_map(variables)
    texto_plantilla = str(getattr(configuracion, 'texto_' + tipo, '') or texto_base)
    texto = texto_plantilla.format_map(variables).replace('\r\n', '\n').replace('\r', '\n')
    # Las plantillas personalizadas también incorporan los datos de la actividad en el relato.
    if periodo and '{periodo}' not in texto_plantilla and not all(llave in texto_plantilla for llave in ('{fecha_inicio}', '{fecha_fin}')):
        texto = texto.rstrip(' .') + '. La actividad se desarrolló ' + periodo + '.'
    if '{horas}' not in texto_plantilla and certificado.horas:
        texto = texto.rstrip(' .') + '. Duración acreditada: ' + horas + ' horas.'
    if not periodo:
        texto = texto.replace('La actividad se desarrolló , bajo la organización de ', 'Organizada por ')
    firma_nombre, firma_cargo = firmante_base or (certificado.firma_nombre, certificado.firma_cargo)
    if not getattr(configuracion, 'usar_firmante_curso', True):
        firma_nombre = firma_cargo = ''
    firmantes = []
    for prefijo in ('', 'segunda_', 'tercera_'):
        nombre = str(getattr(configuracion, prefijo + 'firma_nombre', '') or (firma_nombre if not prefijo else '')).strip()
        cargo = str(getattr(configuracion, prefijo + 'firma_cargo', '') or (firma_cargo if not prefijo else '')).strip()
        imagen = imagen_png(getattr(configuracion, prefijo + 'firma_imagen', None), (800, 300))
        if nombre or cargo or imagen:
            firmantes.append({'nombre': nombre, 'cargo': cargo, 'imagen': imagen})
    logos = []
    logo = ''
    for indice in range(1, 5):
        imagen = imagen_png(getattr(configuracion, f'logo_{indice}_imagen', None), (1000, 500))
        if indice == 1 and not imagen:
            # El primer espacio representa a la institución; un logo cargado allí la reemplaza.
            origen = logo_institucional(fondo='claro')
            logo = imagen_png(str(origen), (1000, 500)) if origen else ''
            imagen, fondo = logo, _fondo_logo(logo) if logo else 'claro'
        else:
            fondo = _fondo_logo(imagen) if imagen else 'claro'
        if imagen:
            logos.append({'imagen': imagen, 'posicion': getattr(configuracion, f'logo_{indice}_posicion', 'auto'), 'fondo': fondo})
    return {
        'version': 3, 'titulo': titulo, 'texto': texto,
        'alineacion_contenido': 'izquierda' if getattr(configuracion, 'diseno', 'clasico') == 'sobrio' else 'centro',
        'emisor': emisor, 'entradilla': entradilla,
        'diseno': getattr(configuracion, 'diseno', 'clasico'),
        'primario': getattr(configuracion, 'color_primario', '') or paleta.get('primario', '#1E5A3D'),
        'acento': getattr(configuracion, 'color_acento', '') or paleta.get('acento', '#E1B93F'),
        'institucion': institucion.nombre, 'siglas': institucion.siglas, 'logo': logo, 'logos': logos,
        'disposicion_logos': getattr(configuracion, 'disposicion_logos', 'auto'),
        'firmantes': firmantes, 'mostrar_nota': False, 'fecha': fecha, 'fecha_emision': fecha, 'periodo': periodo,
        'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'horas': horas,
        'categoria_evento': categoria, 'rol': rol, 'verificacion_url': direccion_de_verificacion(certificado),
    }




def _logo_institucional_claro_v4(imagen, color):
    """Adapta únicamente el blanco de la identidad institucional a un fondo claro.

    Conserva el canal alfa y los colores del emblema; nunca se usa sobre marcas subidas.
    """
    from PIL import Image
    from reportlab.lib.colors import HexColor

    tinta = HexColor(color)
    rgb = tuple(round(c * 255) for c in (tinta.red, tinta.green, tinta.blue))
    with Image.open(BytesIO(base64.b64decode(imagen))) as original:
        rgba = original.convert("RGBA")
        if rgba.getextrema()[3][0] == 255:
            return imagen
        rgba.putdata(
            [
                (rgb[0], rgb[1], rgb[2], a)
                if a and min(r, g, b) > 220 and max(r, g, b) - min(r, g, b) < 24
                else (r, g, b, a)
                for r, g, b, a in rgba.getdata()
            ]
        )
        salida = BytesIO()
        rgba.save(salida, format="PNG", optimize=True)
    return base64.b64encode(salida.getvalue()).decode("ascii")



def _foto_certificado_v4(origen):
    """Fotografía congelada a resolución de impresión y peso acotado; no cambia logos."""
    from PIL import Image

    png = imagen_png(origen, (1600, 1000))
    if not png:
        return ""
    with Image.open(BytesIO(base64.b64decode(png))) as imagen:
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, "white")
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        salida = BytesIO()
        fondo.save(salida, format="JPEG", quality=86, optimize=True)
    return base64.b64encode(salida.getvalue()).decode("ascii")


def _crear_diseno_base_v4(certificado, configuracion=None, firmante_base=None):
    """Congela la composición V4; las versiones históricas nunca consultan estos campos."""
    from apps.core.presentation.identidad import logo_institucional

    configuracion = configuracion or SimpleNamespace()
    diseno = _crear_diseno_base_v3(certificado, configuracion, firmante_base)
    diseno.update(
        {
            "version": 4,
            "alineacion_contenido": getattr(
                configuracion, "alineacion_contenido", "centro"
            ),
            "formato_contenido": getattr(
                configuracion, "formato_contenido", "institucional"
            ),
            "subtitulo": str(getattr(configuracion, "subtitulo", "") or "").strip(),
            "competencias": [
                linea.strip()
                for linea in str(
                    getattr(configuracion, "competencias", "") or ""
                ).splitlines()
                if linea.strip()
            ][:6],
        }
    )
    variables = {
        "nombre": certificado.nombre,
        "curso": certificado.curso_nombre,
        "horas": diseno["horas"],
        "edicion": certificado.edicion,
        "unidad": certificado.unidad_nombre,
        "fecha": diseno["fecha"],
        "tipo": diseno["categoria_evento"].lower(),
        "categoria_evento": diseno["categoria_evento"],
        "fecha_inicio": diseno["fecha_inicio"],
        "fecha_fin": diseno["fecha_fin"],
        "periodo": diseno["periodo"],
        "fecha_emision": diseno["fecha_emision"],
        "emisor": diseno["emisor"],
        "rol": diseno["rol"],
    }
    for campo in ("subtitulo", "emisor", "entradilla"):
        diseno[campo] = diseno[campo].format_map(variables)
    diseno["competencias"] = [
        linea.format_map(variables) for linea in diseno["competencias"]
    ]
    # Sólo las variantes institucionales autorizadas cambian según el fondo; las marcas
    # subidas se conservan exactamente, con transparencia y sin colorearlas de nuevo.
    if (
        diseno.get("logos")
        and not getattr(configuracion, "logo_1_imagen", None)
        and diseno.get("logo")
    ):
        principal = diseno["logos"][0]
        principal["institucional"] = True
        principal["variantes"] = {
            "claro": (
                _logo_institucional_claro_v4(principal["imagen"], diseno["primario"])
                if _fondo_logo(principal["imagen"]) == "oscuro"
                else principal["imagen"]
            )
        }
        oscuro = logo_institucional(fondo="oscuro")
        if oscuro:
            principal["variantes"]["oscuro"] = imagen_png(str(oscuro), (1000, 500))
    foto = getattr(configuracion, "foto_alusiva", None)
    origen_foto = "personalizada" if foto else ""
    if not foto and getattr(configuracion, "usar_foto_unidad", True):
        curso = getattr(configuracion, "curso", None)
        unidad = getattr(curso, "unidad", None) if curso else None
        if not unidad:
            curso_origen = getattr(certificado, "curso_origen", None)
            unidad = getattr(curso_origen, "unidad", None) if curso_origen else None
        if not unidad:
            inscripcion = getattr(certificado, "inscripcion", None)
            edicion = getattr(inscripcion, "edicion", None) if inscripcion else None
            curso = getattr(edicion, "curso", None) if edicion else None
            unidad = getattr(curso, "unidad", None) if curso else None
        foto = getattr(unidad, "imagen", None) if unidad else None
        origen_foto = "unidad" if foto else ""
    diseno["foto"] = _foto_certificado_v4(foto) if foto else ""
    diseno["origen_foto"] = origen_foto
    return diseno



DISENOS_NUEVOS_V5 = ('ia_particulas', 'red_cientifica', 'poligonos_digitales', 'ondas_tecnologicas')


def _tema_automatico_v5(certificado, modelo):
    import unicodedata

    nombre = (
        unicodedata.normalize(
            "NFKD", str(certificado.curso_nombre) + " " + str(certificado.unidad_nombre)
        )
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    if modelo in DISENOS_NUEVOS_V5:
        return {
            "ia_particulas": "ia_datos",
            "red_cientifica": "investigacion",
            "poligonos_digitales": "redes",
            "ondas_tecnologicas": "ia_datos",
        }[modelo]
    if any(
        p in nombre for p in ("agro", "alimento", "biodivers", "sostenib", "ambient")
    ):
        return "sostenibilidad"
    if any(p in nombre for p in ("robot", "fabric", "prototip", "manufact")):
        return "robotica"
    if any(
        p in nombre
        for p in ("logistica", "comput", "datos", "software", "inteligencia")
    ):
        return "ia_datos"
    if getattr(certificado, "categoria_evento", "") in (
        "congreso",
        "evento_cientifico",
    ):
        return "investigacion"
    return "redes"


def _imagen_fondo_v5(origen):
    from PIL import Image

    png = imagen_png(origen, (1600, 1200))
    if not png:
        return ""
    with Image.open(BytesIO(base64.b64decode(png))) as imagen:
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, "white")
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        salida = BytesIO()
        fondo.save(salida, format="JPEG", quality=86, optimize=True)
    return base64.b64encode(salida.getvalue()).decode("ascii")


def _crear_diseno_base_v5(certificado, configuracion=None, firmante_base=None):
    """Congela fondo, encuadre y contenido V5; nunca altera los snapshots V1–V4."""
    configuracion = configuracion or SimpleNamespace()
    diseno = _crear_diseno_base_v4(certificado, configuracion, firmante_base)
    modelo = diseno["diseno"]
    tema = getattr(configuracion, "tema_fondo", "auto")
    modo = getattr(configuracion, "modo_fondo", "auto")
    intensidad = getattr(configuracion, "intensidad_fondo", "media")
    diseno.update(
        version=5,
        tema_fondo=_tema_automatico_v5(certificado, modelo) if tema == "auto" else tema,
        modo_fondo=(
            "oscuro"
            if modelo
            in (
                "ia_particulas",
                "poligonos_digitales",
                "tecnologico",
                "circuitos",
                "inmersivo",
            )
            else "claro"
        )
        if modo == "auto"
        else modo,
        intensidad_fondo=intensidad,
        encuadre_fondo=getattr(configuracion, "encuadre_fondo", "centro"),
        preferencias_fondo={"tema": tema, "modo": modo, "intensidad": intensidad},
    )
    if modelo in DISENOS_NUEVOS_V5:
        if not getattr(configuracion, "color_primario", ""):
            diseno["primario"] = "#164B72"
        if not getattr(configuracion, "color_acento", ""):
            diseno["acento"] = "#38B9CF"
        for logo in diseno.get("logos", []):
            if (
                logo.get("institucional")
                and _fondo_logo(logo.get("imagen", "")) == "oscuro"
            ):
                logo["variantes"]["claro"] = _logo_institucional_claro_v4(
                    logo["imagen"], diseno["primario"]
                )
    fondo = getattr(configuracion, "imagen_fondo", None)
    diseno["imagen_fondo"] = _imagen_fondo_v5(fondo) if fondo else ""
    return diseno


def _contraste_logo_v6(imagen, contraste, oscuro, color):
    """Adapta sólo siluetas monocromas transparentes; conserva marcas de color y opacas."""
    from PIL import Image
    from reportlab.lib.colors import HexColor

    if not imagen or contraste == "original":
        return imagen
    with Image.open(BytesIO(base64.b64decode(imagen))) as origen:
        logo = origen.convert("RGBA")
        if logo.getchannel("A").getextrema()[0] == 255:
            return imagen
        pixels = list(logo.getdata())
        visibles = [(r, g, b) for r, g, b, a in pixels if a > 48]
        if not visibles:
            return imagen
        blancos = sum(
            min(r, g, b) >= 205 and max(r, g, b) - min(r, g, b) <= 20
            for r, g, b in visibles
        ) / len(visibles)
        negros = sum(
            max(r, g, b) <= 65 and max(r, g, b) - min(r, g, b) <= 20
            for r, g, b in visibles
        ) / len(visibles)
        if max(blancos, negros) < 0.97:
            return imagen
        fondo_oscuro = oscuro if contraste == "auto" else contraste == "oscuro"
        if (blancos >= 0.97 and fondo_oscuro) or (negros >= 0.97 and not fondo_oscuro):
            return imagen
        tinta = HexColor("#FFFFFF" if fondo_oscuro else color)
        if (
            not fondo_oscuro
            and (0.2126 * tinta.red + 0.7152 * tinta.green + 0.0722 * tinta.blue) > 0.6
        ):
            tinta = HexColor("#163D5C")
        rgb = tuple(round(v * 255) for v in (tinta.red, tinta.green, tinta.blue))
        adaptada = Image.new("RGBA", logo.size)
        adaptada.putdata([(*rgb, a) for r, g, b, a in pixels])
        salida = BytesIO()
        adaptada.save(salida, "PNG", optimize=True)
        return base64.b64encode(salida.getvalue()).decode("ascii")


def _lista_organizadores_v6(nombres):
    unicos = []
    for valor in nombres:
        texto = str(valor or "").strip()
        if texto and texto.casefold() not in [n.casefold() for n in unicos]:
            unicos.append(texto)
    return (
        ", ".join(unicos[:-1]) + " y " + unicos[-1]
        if len(unicos) > 1
        else (unicos[0] if unicos else "")
    )


def _crear_diseno_base_v6(certificado, configuracion=None, firmante_base=None):
    """Identidad institucional separada de aliados; composición V6 congelada al emitir."""
    from apps.core.presentation.identidad import logo_institucional

    config = configuracion or SimpleNamespace()
    nombres = [getattr(config, f"logo_{i}_nombre", "") for i in range(1, 5)]
    organizadores = _lista_organizadores_v6(
        [getattr(config, "emisor", "") or certificado.unidad_nombre, *nombres]
    )
    sustituto = organizadores.replace("{", "{{").replace("}", "}}")
    defaults = {
        "aprobacion": TEXTO_APROBACION,
        "participacion": TEXTO_PARTICIPACION,
        "asistencia": TEXTO_ASISTENCIA,
        "ponente": TEXTO_PONENTE,
        "organizador": TEXTO_ORGANIZADOR,
    }
    es_muestra = bool(getattr(certificado, "es_muestra_editor", False))
    sin_periodo = es_muestra and (
        not getattr(certificado, "fecha_inicio", None)
        or not getattr(certificado, "fecha_fin", None)
    )
    sin_horas = es_muestra and not getattr(certificado, "horas", None)

    def preparar(valor):
        texto = str(valor or "").replace("{organizadores}", sustituto)
        if sin_periodo:
            texto = texto.replace("{periodo}", "en un período por definir")
        if sin_periodo:
            from apps.formacion.presentation.certificados_cursos import presentar_fecha

            for campo in ("fecha_inicio", "fecha_fin"):
                texto = texto.replace(
                    "{" + campo + "}",
                    presentar_fecha(getattr(certificado, campo, None))
                    or "fecha por definir",
                )
        if sin_horas:
            texto = (
                texto.replace(
                    "una duración acreditada de {horas} horas", "duración por definir"
                )
                .replace("una duración de {horas} horas", "duración por definir")
                .replace("{horas} horas", "duración por definir")
                .replace("{horas}", "por definir")
            )
        return texto

    overrides = {}
    for tipo, default in defaults.items():
        for prefijo in ("titulo", "texto"):
            campo = prefijo + "_" + tipo
            valor = getattr(config, campo, "")
            if prefijo == "texto" and (not valor or valor == default):
                valor = default.replace("{emisor}", "{organizadores}")
            overrides[campo] = preparar(valor)
    for campo in ("subtitulo", "emisor", "entradilla", "competencias"):
        overrides[campo] = preparar(getattr(config, campo, ""))

    class Contexto:
        def __getattr__(self, nombre):
            return overrides[nombre] if nombre in overrides else getattr(config, nombre)

    class CertificadoContexto:
        def __getattr__(self, nombre):
            return (
                None
                if sin_periodo and nombre in ("fecha_inicio", "fecha_fin")
                else getattr(certificado, nombre)
            )

    if sin_periodo:
        overrides.update(fecha_inicio=None, fecha_fin=None)
    diseno = _crear_diseno_base_v5(CertificadoContexto(), Contexto(), firmante_base)
    if sin_periodo:
        from apps.formacion.presentation.certificados_cursos import presentar_fecha

        diseno["periodo"] = "Período por definir"
        for campo in ("fecha_inicio", "fecha_fin"):
            diseno[campo] = (
                presentar_fecha(getattr(certificado, campo, None))
                or "Fecha por definir"
            )
    if sin_horas:
        diseno["horas"] = "Duración por definir"
    primario = diseno["primario"]
    claro = logo_institucional(fondo="claro")
    oscuro = logo_institucional(fondo="oscuro")
    imagen = imagen_png(str(claro or oscuro), (1000, 500)) if claro or oscuro else ""
    variantes = {}
    if imagen:
        variantes["claro"] = (
            _logo_institucional_claro_v4(imagen, primario)
            if _fondo_logo(imagen) == "oscuro"
            else imagen
        )
        variantes["oscuro"] = (
            imagen_png(str(oscuro), (1000, 500))
            if oscuro
            else _contraste_logo_v6(imagen, "auto", True, primario)
        )
    institucional = {
        "imagen": imagen,
        "variantes": variantes,
        "nombre": diseno["institucion"],
        "unidad": certificado.unidad_nombre,
        "facultad": str(getattr(config, "facultad_nombre", "") or "").strip()
        if getattr(config, "mostrar_facultad", False)
        else "",
        "carrera": str(getattr(config, "carrera_nombre", "") or "").strip()
        if getattr(config, "mostrar_carrera", False)
        else "",
    }
    aliados = []
    for i in range(1, 5):
        original = imagen_png(getattr(config, f"logo_{i}_imagen", None), (1000, 500))
        nombre = str(getattr(config, f"logo_{i}_nombre", "") or "").strip()
        if not original and not nombre:
            continue
        contraste = getattr(config, f"logo_{i}_contraste", "auto")
        aliados.append(
            {
                "imagen": original,
                "nombre": nombre,
                "contraste": contraste,
                "posicion": getattr(config, f"logo_{i}_posicion", "auto"),
                "variantes": {
                    modo: _contraste_logo_v6(
                        original, contraste, modo == "oscuro", primario
                    )
                    for modo in ("claro", "oscuro")
                },
            }
        )
    diseno.update(
        version=6,
        logo_institucional=institucional,
        logos_aliados=aliados,
        logos=aliados,
        organizadores=organizadores,
    )
    return diseno


def _crear_diseno_base_v7(certificado, configuracion=None, firmante_base=None):
    """La composición V7 mantiene el modelo y una fila institucional común."""
    diseno = _crear_diseno_base_v6(certificado, configuracion, firmante_base)
    diseno["version"] = 7
    return diseno


def _crear_diseno_base_v8(certificado, configuracion=None, firmante_base=None):
    """V8 conserva los colores decorativos y garantiza la lectura de sus textos."""
    diseno = _crear_diseno_base_v7(certificado, configuracion, firmante_base)
    diseno["version"] = 8
    return diseno


def _crear_diseno_base_v9(certificado, configuracion=None, firmante_base=None):
    """V9 distingue a la institución emisora de sus entidades colaboradoras."""
    diseno = _crear_diseno_base_v8(certificado, configuracion, firmante_base)
    diseno["version"] = 9
    diseno["jerarquia_institucional"] = "upec_principal"
    return diseno


def _crear_diseno_base_v10(certificado, configuracion=None, firmante_base=None):
    """V10 centra la institución y presenta las marcas colaboradoras con su nombre debajo."""
    from apps.core.presentation.identidad import identidad_actual

    config = configuracion or SimpleNamespace()
    institucion = identidad_actual()[1]
    paleta = dict(institucion.paleta)
    colores = {
        "color_primario": getattr(config, "color_primario", "")
        or paleta.get("primario") or "#006633",
        "color_acento": getattr(config, "color_acento", "")
        or paleta.get("acento") or "#ffce00",
    }

    class ContextoPaleta:
        def __getattr__(self, nombre):
            return colores[nombre] if nombre in colores else getattr(config, nombre)

    diseno = _crear_diseno_base_v9(certificado, ContextoPaleta(), firmante_base)
    diseno["version"] = 10
    diseno["colaboradores_disposicion"] = "logo_sobre_nombre"
    return diseno


def _crear_diseno_base_v11(certificado, configuracion=None, firmante_base=None):
    """V11 congela colores de texto, tipografía y el ornamento opcional del pie."""
    config = configuracion or SimpleNamespace()
    diseno = _crear_diseno_base_v10(certificado, config, firmante_base)
    diseno.update(
        version=11,
        color_texto=getattr(config, "color_texto", "") or "",
        color_titulos=getattr(config, "color_titulos", "") or "",
        tipografia=getattr(config, "tipografia", "poppins") or "poppins",
        mostrar_pie_tecnologico=bool(getattr(config, "mostrar_pie_tecnologico", False)),
        estilo_pie_tecnologico=getattr(config, "estilo_pie_tecnologico", "circuitos"),
    )
    # Las opciones describen el color del logo, no el del fondo.
    for aliado in diseno.get("logos_aliados") or []:
        contraste = aliado.get("contraste", "auto")
        if contraste in ("claro", "oscuro"):
            modo_compatibilidad = "oscuro" if contraste == "claro" else "claro"
            aliado["variantes"] = {
                modo: _contraste_logo_v6(aliado.get("imagen", ""), modo_compatibilidad, modo == "oscuro", diseno["primario"])
                for modo in ("claro", "oscuro")
            }
    return diseno


def crear_diseno(certificado, configuracion=None, firmante_base=None):
    """V12 reserva una superficie blanca; el color sólo decora el certificado."""
    config = configuracion or SimpleNamespace()

    class SuperficieBlanca:
        def __getattr__(self, nombre):
            if nombre == "modo_fondo":
                return "claro"
            return getattr(config, nombre)

    diseno = _crear_diseno_base_v11(certificado, SuperficieBlanca(), firmante_base)
    diseno.update(version=12, modo_fondo="claro")
    diseno["preferencias_fondo"]["modo"] = "claro"
    return diseno


def _color_texto_v8(color, fondo):
    """Contraste de texto de 4.5:1 sin cambiar la paleta decorativa configurada."""
    from reportlab.lib.colors import HexColor

    def luminancia(c):
        lineales = [
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            for v in (c.red, c.green, c.blue)
        ]
        return sum(v * peso for v, peso in zip(lineales, (0.2126, 0.7152, 0.0722)))

    def contraste(a, b):
        la, lb = luminancia(a), luminancia(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    if contraste(color, fondo) >= 4.5:
        return color
    claro = HexColor("#F3F7F8")
    oscuro = HexColor("#163D5C")
    elegido = claro if contraste(claro, fondo) >= contraste(oscuro, fondo) else oscuro
    if contraste(elegido, fondo) >= 4.5:
        return elegido
    blanco, negro = HexColor("#FFFFFF"), HexColor("#000000")
    return blanco if contraste(blanco, fondo) >= contraste(negro, fondo) else negro


def _fondo_v8(lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura):
    """La cabecera termina con la franja del modelo; no sobresale hacia el cuerpo."""
    from reportlab.lib.units import mm

    oscuro = _fondo_v7(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    _, _, base, _ = _paleta_v7(diseno, modelo)
    hx = (94 if modelo == "ia_particulas" else 75 if modelo == "editorial" else 24) * mm
    hw = 186 * mm if modelo == "red_cientifica" else ancho - hx - 24 * mm
    lienzo.setFillColor(base)
    lienzo.rect(hx - 2 * mm, 147 * mm, hw + 4 * mm, 4 * mm, fill=1, stroke=0)
    return oscuro


def _cabecera_v8(
    lienzo,
    diseno,
    hx,
    hw,
    cabecera_oscura,
    tinta,
    fuente,
    negrita,
    fuente_titulo,
    serif,
):
    return _cabecera_v7(
        lienzo,
        diseno,
        hx,
        hw,
        cabecera_oscura,
        tinta,
        fuente,
        negrita,
        fuente_titulo,
        serif,
        subtitulo_cuerpo=True,
    )


def _fondo_v9(lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura):
    """La cabecera institucional tiene su propia zona; conserva el arte lateral."""
    from reportlab.lib.units import mm

    oscuro = _fondo_v8(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    _, _, _, color = _paleta_v7(diseno, modelo)
    lienzo.setFillColor(color)
    lienzo.rect(22 * mm, 147 * mm, ancho - 44 * mm, 57.5 * mm, fill=1, stroke=0)
    return oscuro


def _parrafos_institucion_v9(institucion, diseno, ancho, alto, fuente, negrita, tinta):
    """Ajusta el bloque completo y conserva un renglón propio por dependencia."""
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph

    campos = [
        (institucion.get("nombre") or diseno.get("institucion", ""), negrita, 14, 12),
        (institucion.get("unidad", ""), negrita, 11, 10),
        (institucion.get("facultad", ""), fuente, 9.5, 9),
        (institucion.get("carrera", ""), fuente, 9.5, 9),
    ]
    campos = [(str(texto).strip(), tipografia, tamano, minimo)
              for texto, tipografia, tamano, minimo in campos if texto]
    separacion = 0.8 * mm
    reduccion = 0
    while True:
        parrafos = []
        for texto, tipografia, tamano, minimo in campos:
            tamano = max(minimo, tamano - reduccion)
            estilo = ParagraphStyle(
                "institucion-v9", fontName=tipografia, fontSize=tamano,
                leading=tamano * 1.1, textColor=tinta, alignment=TA_LEFT, splitLongWords=True,
                allowWidows=0, allowOrphans=0,
            )
            parrafo = Paragraph(escape(texto).replace("\n", "<br/>"), estilo)
            _, altura = parrafo.wrap(ancho, alto)
            parrafos.append((parrafo, altura))
        altura_total = sum(altura for _, altura in parrafos)
        altura_total += separacion * max(0, len(parrafos) - 1)
        if altura_total <= alto + 0.01:
            return parrafos, altura_total, separacion
        if all(tamano - reduccion <= minimo for _, _, tamano, minimo in campos):
            raise ValidationError(
                "El nombre de la institución o sus dependencias no cabe de forma "
                "legible en la cabecera. Revise los nombres y vuelva a previsualizar."
            )
        reduccion += 0.25


def _imagen_cabecera_v9(lienzo, logo, x, y, ancho, alto, oscuro):
    """Dibuja cada marca sin placa y conserva su proporción y contraste."""
    from reportlab.lib.utils import ImageReader

    archivo = (logo.get("variantes") or {}).get(
        "oscuro" if oscuro else "claro"
    ) or logo.get("imagen", "")
    if archivo:
        lienzo.drawImage(
            ImageReader(BytesIO(base64.b64decode(archivo))),
            x, y, width=ancho, height=alto, preserveAspectRatio=True,
            anchor="c", mask="auto",
        )
    return bool(archivo)


def _colaboradores_v9(lienzo, diseno, x, top, ancho, alto, oscuro, tinta, fuente, negrita):
    """Los aliados se organizan únicamente dentro de su columna secundaria."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph

    aliados = list(diseno.get("logos_aliados") or [])[:4]
    if not aliados:
        return
    _texto_pdf(
        lienzo, "En colaboración con", x, top, ancho, 4 * mm,
        tinta, negrita, 8.5, 8.5, "izquierda", 1.05,
    )
    top -= 6 * mm
    fila = min(11 * mm, (alto - 6 * mm) / len(aliados))
    disposicion = diseno.get("disposicion_logos", "auto")
    for numero, logo in enumerate(aliados):
        fila_top = top - numero * fila
        posicion = logo.get("posicion", "auto")
        if posicion == "auto" and disposicion in ("izquierda", "centro", "derecha"):
            posicion = disposicion
        elif posicion == "auto" and disposicion == "entre_extremos":
            posicion = "derecha" if numero % 2 else "izquierda"
        imagen = (logo.get("variantes") or {}).get(
            "oscuro" if oscuro else "claro"
        ) or logo.get("imagen", "")
        nombre = str(logo.get("nombre", "") or "").strip()
        logo_ancho = (22 if nombre else 36) * mm
        logo_alto = min((7 if nombre else 10) * mm, fila - mm)
        texto_x, texto_ancho = x, ancho
        if imagen and nombre:
            # Los nombres largos ganan ancho sin reducir la letra por debajo de7.5pt.
            estilo = ParagraphStyle(
                "aliado-v9", fontName=fuente, fontSize=7.5, leading=7.5,
                splitLongWords=True, allowWidows=0, allowOrphans=0,
            )
            parrafo = Paragraph(escape(nombre).replace("\n", "<br/>"), estilo)
            for medida in (22, 20, 18, 16, 14):
                logo_ancho = medida * mm
                _, altura_nombre = parrafo.wrap(ancho - logo_ancho - 2 * mm, fila)
                if altura_nombre <= fila - 0.3 * mm:
                    break
            # La posición se aplica a la marca dentro de la región de aliados.
            derecha = posicion == "derecha"
            logo_x = x + ancho - logo_ancho if derecha else x
            texto_x = x if derecha else x + logo_ancho + 2 * mm
            texto_ancho = ancho - logo_ancho - 2 * mm
        elif imagen:
            logo_x = (
                x + ancho - logo_ancho if posicion == "derecha"
                else x + (ancho - logo_ancho) / 2 if posicion == "centro"
                else x
            )
        if imagen:
            _imagen_cabecera_v9(
                lienzo, logo, logo_x, fila_top - (fila + logo_alto) / 2,
                logo_ancho, logo_alto, oscuro,
            )
        if nombre:
            _texto_pdf(
                lienzo, nombre, texto_x, fila_top, texto_ancho, fila - 0.3 * mm,
                tinta, fuente, 8, 7.5,
                "centro" if posicion == "centro" else "izquierda",
                1.0,
            )


def _cabecera_v9(lienzo, diseno, ancho, tinta, fuente, negrita, fuente_titulo, serif, oscuro):
    """UPEC y su unidad encabezan; la colaboración ocupa un bloque independiente."""
    from reportlab.lib.units import mm

    x, top, alto = 24 * mm, 204 * mm, 43 * mm
    institucional = diseno.get("logo_institucional") or {}
    aliados = list(diseno.get("logos_aliados") or [])[:4]
    ancho_principal = 151 * mm if aliados else ancho - 48 * mm
    imagen = (institucional.get("variantes") or {}).get(
        "oscuro" if oscuro else "claro"
    ) or institucional.get("imagen", "")
    logo_ancho = (44 if aliados else 56) * mm
    texto_x = x + logo_ancho + 5 * mm if imagen else x
    texto_ancho = ancho_principal - (texto_x - x)
    parrafos, altura_texto, separacion = _parrafos_institucion_v9(
        institucional, diseno, texto_ancho, alto, fuente, negrita, tinta
    )
    texto_top = top - (alto - altura_texto) / 2
    if imagen:
        logo_alto = min(26 * mm, alto)
        _imagen_cabecera_v9(
            lienzo, institucional, x, top - (alto + logo_alto) / 2,
            logo_ancho, logo_alto, oscuro,
        )
    for parrafo, altura in parrafos:
        parrafo.drawOn(lienzo, texto_x, texto_top - altura)
        texto_top -= altura + separacion
    if aliados:
        lienzo.saveState()
        lienzo.setStrokeColor(tinta)
        lienzo.setStrokeAlpha(0.18)
        lienzo.setLineWidth(0.5)
        lienzo.line(179 * mm, 163 * mm, 179 * mm, 202 * mm)
        lienzo.restoreState()
        _colaboradores_v9(
            lienzo, diseno, 183 * mm, 203 * mm, ancho - 207 * mm,
            42 * mm, oscuro, tinta, fuente, negrita,
        )
    _texto_pdf(
        lienzo, diseno.get("titulo", "CERTIFICADO"), x, 159 * mm,
        ancho - 48 * mm, 12 * mm, tinta, fuente_titulo,
        31 if serif else 27, 18, "centro", 1.08,
    )



def _parrafos_institucion_v10(
    institucion, diseno, ancho, alto, fuente, negrita, tinta, *, centrado=False
):
    """Ajusta el bloque completo y conserva un renglón propio por dependencia."""
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph

    campos = [
        (institucion.get("nombre") or diseno.get("institucion", ""), negrita, 14, 12),
        (institucion.get("unidad", ""), negrita, 11, 10),
        (institucion.get("facultad", ""), fuente, 9.5, 9),
        (institucion.get("carrera", ""), fuente, 9.5, 9),
    ]
    campos = [(str(texto).strip(), tipografia, tamano, minimo)
              for texto, tipografia, tamano, minimo in campos if texto]
    separacion = 0.8 * mm
    reduccion = 0
    while True:
        parrafos = []
        for texto, tipografia, tamano, minimo in campos:
            tamano = max(minimo, tamano - reduccion)
            estilo = ParagraphStyle(
                "institucion-v10", fontName=tipografia, fontSize=tamano,
                leading=tamano * 1.1, textColor=tinta, alignment=TA_CENTER if centrado else TA_LEFT, splitLongWords=True,
                allowWidows=0, allowOrphans=0,
            )
            parrafo = Paragraph(escape(texto).replace("\n", "<br/>"), estilo)
            _, altura = parrafo.wrap(ancho, alto)
            parrafos.append((parrafo, altura))
        altura_total = sum(altura for _, altura in parrafos)
        altura_total += separacion * max(0, len(parrafos) - 1)
        if altura_total <= alto + 0.01:
            return parrafos, altura_total, separacion
        if all(tamano - reduccion <= minimo for _, _, tamano, minimo in campos):
            raise ValidationError(
                "El nombre de la institución o sus dependencias no cabe de forma "
                "legible en la cabecera. Revise los nombres y vuelva a previsualizar."
            )
        reduccion += 0.25


def _tarjetas_colaboradores_v10(diseno, x, top, ancho, alto):
    """Distribuye de una a cuatro tarjetas; una tercera entidad ocupa el centro."""
    from reportlab.lib.units import mm

    aliados = list(diseno.get("logos_aliados") or [])[:4]
    columnas = 1 if len(aliados) == 1 else 2
    filas = 1 if len(aliados) <= 2 else 2
    margen = 2 * mm
    tarjeta_ancho = (ancho - margen * (columnas - 1)) / columnas
    tarjeta_alto = alto / filas
    for indice, logo in enumerate(aliados):
        fila, columna = divmod(indice, columnas)
        tarjeta_x = (
            x + (ancho - tarjeta_ancho) / 2
            if len(aliados) == 3 and indice == 2
            else x + columna * (tarjeta_ancho + margen)
        )
        yield logo, tarjeta_x, top - fila * tarjeta_alto, tarjeta_ancho, tarjeta_alto


def _colaboradores_v10(lienzo, diseno, x, top, ancho, alto, oscuro, tinta, fuente, negrita):
    """Cada entidad tiene logo arriba y nombre debajo, dentro de su propia tarjeta."""
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph

    aliados = list(diseno.get("logos_aliados") or [])[:4]
    if not aliados:
        return
    _texto_pdf(
        lienzo, "En colaboración con", x, top, ancho, 4 * mm,
        tinta, negrita, 8.5, 8.5, "centro", 1.05,
    )
    grid_top = top - 5.5 * mm
    grid_alto = alto - 5.5 * mm
    disposicion = diseno.get("disposicion_logos", "auto")
    for indice, (logo, tx, tt, tw, th) in enumerate(
        _tarjetas_colaboradores_v10(diseno, x, grid_top, ancho, grid_alto)
    ):
        posicion = logo.get("posicion", "auto")
        if posicion == "auto":
            posicion = (
                disposicion if disposicion in ("izquierda", "centro", "derecha")
                else "derecha" if disposicion == "entre_extremos" and indice % 2
                else "izquierda" if disposicion == "entre_extremos"
                else "centro"
            )
        alineacion = (
            TA_LEFT if posicion == "izquierda"
            else TA_RIGHT if posicion == "derecha"
            else TA_CENTER
        )
        archivo = (logo.get("variantes") or {}).get(
            "oscuro" if oscuro else "claro"
        ) or logo.get("imagen", "")
        nombre = str(logo.get("nombre", "") or "").strip()
        altura_nombre = 0
        parrafo = None
        separacion = 0.5 * mm if archivo and nombre else 0
        alto_minimo_logo = 4.5 * mm if archivo else 0
        for tamano in (8, 7.75, 7.5):
            if nombre:
                estilo = ParagraphStyle(
                    "aliado-v10", fontName=fuente, fontSize=tamano, leading=tamano,
                    textColor=tinta, alignment=alineacion, splitLongWords=True,
                    allowWidows=0, allowOrphans=0,
                )
                parrafo = Paragraph(escape(nombre).replace("\n", "<br/>"), estilo)
                _, altura_nombre = parrafo.wrap(tw, th)
            if altura_nombre + alto_minimo_logo + separacion <= th - 0.1 * mm:
                break
        else:
            raise ValidationError(
                "El nombre de una entidad colaboradora no cabe de forma legible "
                "debajo de su logo. Revíselo y vuelva a previsualizar."
            )
        alto_logo = (
            min((12 if len(aliados) <= 2 else 8) * mm, th - altura_nombre - separacion)
            if archivo else 0
        )
        altura_total = alto_logo + separacion + altura_nombre
        bloque_top = tt - (th - altura_total) / 2
        if archivo:
            imagen = ImageReader(BytesIO(base64.b64decode(archivo)))
            original_ancho, original_alto = imagen.getSize()
            maximo_ancho = min((36 if len(aliados) <= 2 else 28) * mm, tw)
            escala = min(maximo_ancho / original_ancho, alto_logo / original_alto)
            logo_ancho, logo_alto = original_ancho * escala, original_alto * escala
            logo_x = (
                tx if posicion == "izquierda"
                else tx + tw - logo_ancho if posicion == "derecha"
                else tx + (tw - logo_ancho) / 2
            )
            lienzo.drawImage(
                imagen, logo_x, bloque_top - (alto_logo + logo_alto) / 2,
                width=logo_ancho, height=logo_alto, mask="auto",
            )
        if parrafo:
            parrafo.drawOn(
                lienzo, tx, bloque_top - alto_logo - separacion - altura_nombre
            )


def _cabecera_v10(lienzo, diseno, ancho, tinta, fuente, negrita, fuente_titulo, serif, oscuro):
    """La institución protagoniza la cabecera y los colaboradores forman su propio bloque."""
    from reportlab.lib.units import mm

    x, top, alto = 24 * mm, 204 * mm, 43 * mm
    institucional = diseno.get("logo_institucional") or {}
    aliados = list(diseno.get("logos_aliados") or [])[:4]
    imagen = (institucional.get("variantes") or {}).get(
        "oscuro" if oscuro else "claro"
    ) or institucional.get("imagen", "")
    if aliados:
        ancho_principal = 151 * mm
        logo_ancho = 44 * mm
        texto_x = x + logo_ancho + 5 * mm if imagen else x
        texto_ancho = ancho_principal - (texto_x - x)
        parrafos, altura_texto, separacion = _parrafos_institucion_v10(
            institucional, diseno, texto_ancho, alto, fuente, negrita, tinta
        )
        texto_top = top - (alto - altura_texto) / 2
        if imagen:
            logo_alto = 26 * mm
            _imagen_cabecera_v9(
                lienzo, institucional, x, top - (alto + logo_alto) / 2,
                logo_ancho, logo_alto, oscuro,
            )
        lienzo.saveState()
        lienzo.setStrokeColor(tinta)
        lienzo.setStrokeAlpha(0.18)
        lienzo.setLineWidth(0.5)
        lienzo.line(179 * mm, 161 * mm, 179 * mm, 202 * mm)
        lienzo.restoreState()
        _colaboradores_v10(
            lienzo, diseno, 183 * mm, 203 * mm, ancho - 207 * mm,
            43 * mm, oscuro, tinta, fuente, negrita,
        )
    else:
        texto_x, texto_ancho = x, ancho - 48 * mm
        parrafos, altura_texto, separacion = _parrafos_institucion_v10(
            institucional, diseno, texto_ancho,
            alto - 13.5 * mm if imagen else alto, fuente, negrita, tinta,
            centrado=True,
        )
        espacio_logo = 1.5 * mm if imagen else 0
        logo_alto = min(18 * mm, alto - altura_texto - espacio_logo) if imagen else 0
        bloque_top = top - (alto - altura_texto - espacio_logo - logo_alto) / 2
        if imagen:
            _imagen_cabecera_v9(
                lienzo, institucional, (ancho - 60 * mm) / 2,
                bloque_top - logo_alto, 60 * mm, logo_alto, oscuro,
            )
        texto_top = bloque_top - logo_alto - espacio_logo
    for parrafo, altura in parrafos:
        parrafo.drawOn(lienzo, texto_x, texto_top - altura)
        texto_top -= altura + separacion
    _texto_pdf(
        lienzo, diseno.get("titulo", "CERTIFICADO"), x, 159 * mm,
        ancho - 48 * mm, 12 * mm, tinta, fuente_titulo,
        31 if serif else 27, 18, "centro", 1.08,
    )



def _paleta_v7(diseno, modelo):
    from reportlab.lib.colors import HexColor, white

    modo = (diseno.get("preferencias_fondo") or {}).get("modo", "auto")
    oscuro = diseno.get("modo_fondo") == "oscuro"
    nuevos = modelo in DISENOS_NUEVOS_V5
    cabecera_oscura = (
        oscuro
        if nuevos or modo != "auto"
        else modelo
        in (
            "tecnologico",
            "congreso",
            "industrial",
            "circuitos",
            "horizonte",
            "inmersivo",
        )
    )
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    base = (
        HexColor(
            "#071C30" if nuevos else "#13142F" if modelo == "inmersivo" else "#081D2A"
        )
        if oscuro
        else (HexColor("#FAFCFE") if nuevos else white)
    )
    cabecera = (
        base
        if nuevos or modelo in ("tecnologico", "circuitos", "inmersivo")
        else primario
        if cabecera_oscura
        else _tinte(primario, 0.035)
    )
    return oscuro, cabecera_oscura, base, cabecera


def _fondo_v7(lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura):
    """Modo, tema e imagen personalizan el fondo sin sustituir la forma del modelo."""
    from reportlab.lib.colors import Color
    from reportlab.lib.units import mm

    if modelo in DISENOS_NUEVOS_V5:
        oscuro = _fondo_v5(
            lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
        )
        _zona_cabecera_v7(lienzo, modelo, diseno, ancho)
        return oscuro
    oscuro, _, base, _ = _paleta_v7(diseno, modelo)
    fuerza = {"discreta": 0.32, "media": 0.62, "alta": 0.95}.get(
        diseno.get("intensidad_fondo"), 0.62
    )

    class LienzoPaleta:
        def __getattr__(self, nombre):
            return getattr(lienzo, nombre)

        def color(self, valor):
            rgb = (round(valor.red, 5), round(valor.green, 5), round(valor.blue, 5))
            if rgb in (
                (1, 1, 1),
                (0.03137, 0.11373, 0.16471),
                (0.07451, 0.07843, 0.18431),
            ):
                return base
            if oscuro and min(rgb) > 0.82:
                return Color(
                    *(
                        getattr(base, c) * 0.78 + getattr(valor, c) * 0.22
                        for c in ("red", "green", "blue")
                    )
                )
            return valor

        def setFillColor(self, valor, *args, **kwargs):
            lienzo.setFillColor(self.color(valor), *args, **kwargs)

        def setStrokeColor(self, valor, *args, **kwargs):
            color = self.color(valor)
            if oscuro and max(color.red, color.green, color.blue) < 0.25:
                color = Color(
                    color.red * 0.6 + 0.16,
                    color.green * 0.6 + 0.22,
                    color.blue * 0.6 + 0.25,
                )
            lienzo.setStrokeColor(color, *args, **kwargs)
            lienzo.setStrokeAlpha(
                0.65 if diseno.get("intensidad_fondo") == "discreta" else 1
            )

    _fondo_v4(
        LienzoPaleta(), modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    # Capas opcionales sólo en márgenes y área artística; el texto y las marcas siguen limpios.
    lienzo.saveState()
    zona = lienzo.beginPath()
    zona.rect(0, 0, 19 * mm, alto)
    zona.rect(ancho - 19 * mm, 0, 19 * mm, alto)
    zona.rect(0, 0, ancho, 5.5 * mm)
    if modelo == "editorial":
        zona.rect(0, 151 * mm, 65 * mm, alto - 151 * mm)
    lienzo.clipPath(zona, stroke=0)
    if diseno.get("imagen_fondo"):
        _imagen_encuadrada_v5(
            lienzo,
            diseno["imagen_fondo"],
            (0, 0, ancho, alto),
            diseno.get("encuadre_fondo", "centro"),
            0.12 + fuerza * 0.18,
        )
    preferencias = diseno.get("preferencias_fondo") or {}
    if preferencias.get("tema", "auto") != "auto":
        motivo = acento if oscuro else primario
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "redes"),
            (-21 * mm, 68 * mm, 48 * mm, 92 * mm),
            motivo,
            acento,
            fuerza * 0.22,
        )
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "redes"),
            (ancho - 27 * mm, 60 * mm, 48 * mm, 96 * mm),
            motivo,
            acento,
            fuerza * 0.22,
        )
    lienzo.restoreState()
    _zona_cabecera_v7(lienzo, modelo, diseno, ancho)
    return oscuro


def _zona_cabecera_v7(lienzo, modelo, diseno, ancho):
    """Una zona continua protege contexto, logos y título; el arte queda alrededor."""
    from reportlab.lib.units import mm

    _, _, _, color = _paleta_v7(diseno, modelo)
    hx = (94 if modelo == "ia_particulas" else 75 if modelo == "editorial" else 24) * mm
    hw = 186 * mm if modelo == "red_cientifica" else ancho - hx - 24 * mm
    lienzo.setFillColor(color)
    lienzo.rect(hx - 2 * mm, 147 * mm, hw + 4 * mm, 57.5 * mm, fill=1, stroke=0)


def _cajas_fila_v7(diseno, x, top, ancho, alto):
    """UPEC y aliados comparten fila; el número real determina su espacio."""
    from reportlab.lib.units import mm

    institucional = dict(diseno.get("logo_institucional") or {}, institucional=True)
    aliados = [dict(logo) for logo in (diseno.get("logos_aliados") or [])[:4]]
    logos = [institucional, *aliados]
    n = len(logos)
    if n == 1:
        return _cajas_logos(logos, x, top, ancho, alto, "centro")
    caja = min(56 * mm, (ancho - 6 * mm * (n - 1)) / n)
    disposicion = diseno.get("disposicion_logos", "auto")
    if (
        n == 2
        or disposicion == "entre_extremos"
        or (
            disposicion == "auto"
            and all(logo.get("posicion", "auto") == "auto" for logo in aliados)
        )
    ):
        return [
            (logo, x + i * (ancho - caja) / (n - 1), top - alto, caja, alto)
            for i, logo in enumerate(logos)
        ]
    resto = _cajas_logos(
        aliados, x + caja + 6 * mm, top, ancho - caja - 6 * mm, alto, disposicion
    )
    return [(institucional, x, top - alto, caja, alto), *resto]


def _cabecera_v7(
    lienzo,
    diseno,
    hx,
    hw,
    cabecera_oscura,
    tinta,
    fuente,
    negrita,
    fuente_titulo,
    serif,
    *,
    subtitulo_cuerpo=False,
):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    institucional = diseno.get("logo_institucional") or {}
    aliados = list(diseno.get("logos_aliados") or [])[:4]
    extras = " · ".join(
        n
        for n in (institucional.get("facultad", ""), institucional.get("carrera", ""))
        if n
    )
    compacto = bool(aliados or extras)
    if compacto:
        _texto_pdf(
            lienzo,
            institucional.get("nombre", diseno.get("institucion", "")),
            hx,
            204 * mm,
            hw,
            4 * mm,
            tinta,
            negrita,
            9.5,
            8,
            "centro",
            1.08,
        )
        _texto_pdf(
            lienzo,
            institucional.get("unidad", ""),
            hx,
            199.5 * mm,
            hw,
            4 * mm,
            tinta,
            fuente,
            9,
            8,
            "centro",
            1.08,
        )
        _texto_pdf(
            lienzo,
            extras,
            hx,
            195 * mm,
            hw,
            3 * mm,
            tinta,
            fuente,
            8,
            7,
            "centro",
            1.08,
        )
        cantidad = len(aliados) + 1
        altura = (12 if cantidad <= 2 else 10 if cantidad == 3 else 7.5) * mm
        top = 191 * mm
        nombre_top = top - altura - mm
        for logo, lx, ly, lw, lh in _cajas_fila_v7(diseno, hx, top, hw, altura):
            archivo = (logo.get("variantes") or {}).get(
                "oscuro" if cabecera_oscura else "claro"
            ) or logo.get("imagen", "")
            if archivo:
                lienzo.drawImage(
                    ImageReader(BytesIO(base64.b64decode(archivo))),
                    lx,
                    ly,
                    width=lw,
                    height=lh,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
            if not logo.get("institucional"):
                _texto_pdf(
                    lienzo,
                    logo.get("nombre", ""),
                    lx - mm,
                    nombre_top,
                    lw + 2 * mm,
                    nombre_top - 166.5 * mm,
                    tinta,
                    fuente,
                    8.5,
                    6.5,
                    "centro",
                    1.08,
                )
        _texto_pdf(
            lienzo,
            diseno.get("titulo", "CERTIFICADO"),
            hx,
            165.5 * mm,
            hw,
            13 * mm,
            tinta,
            fuente_titulo,
            31 if serif else 27,
            18,
            "centro",
            1.08,
        )
        _texto_pdf(
            lienzo,
            diseno.get("subtitulo", ""),
            hx,
            (150.5 if subtitulo_cuerpo else 151.5) * mm,
            hw,
            4 * mm,
            _color_texto_v8(
                tinta, _paleta_v7(diseno, diseno.get("diseno", "clasico"))[2]
            )
            if subtitulo_cuerpo
            else tinta,
            fuente,
            10.5,
            9,
            "centro",
            1.1,
        )
        return True
    return _cabecera_v6(
        lienzo,
        diseno,
        hx,
        hw,
        cabecera_oscura,
        tinta,
        fuente,
        negrita,
        fuente_titulo,
        serif,
    )


def _fuentes_pdf():
    """Fuentes TTF del proyecto, independientes de las fuentes instaladas en el servidor."""
    from pathlib import Path
    from django.conf import settings
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    carpeta = Path(settings.BASE_DIR) / 'apps' / 'portal' / 'static' / 'font' / 'nunito'
    for nombre, archivo in (('CertNunito', 'nunito-regular.ttf'), ('CertNunitoBold', 'nunito-700.ttf')):
        if nombre not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nombre, str(carpeta / archivo)))
    return 'CertNunito', 'CertNunitoBold'


def _texto_pdf(canvas, texto, x, top, ancho, alto, color, fuente, tamano, minimo=None, alineacion='centro', interlineado=1.2):
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    texto = str(texto or '').strip()
    if not texto:
        return None
    minimo = tamano if minimo is None else minimo
    while tamano >= minimo - .01:
        estilo = ParagraphStyle('certificado-v2', fontName=fuente, fontSize=tamano,
                                leading=tamano * interlineado, textColor=color,
                                alignment=TA_LEFT if alineacion == 'izquierda' else TA_CENTER,
                                splitLongWords=True, allowWidows=0, allowOrphans=0)
        parrafo = Paragraph(escape(texto).replace('\n', '<br/>'), estilo)
        _, altura = parrafo.wrap(ancho, alto)
        if altura <= alto + .01:
            parrafo.drawOn(canvas, x, top - altura)
            return (x, top - altura, ancho, altura)
        tamano -= .25
    raise ValidationError('El texto no cabe de forma legible. Acórtelo o reduzca las variables repetidas y vuelva a previsualizar.')


def _tinte(color, intensidad=.12):
    from reportlab.lib.colors import Color
    return Color(1 - (1 - color.red) * intensidad, 1 - (1 - color.green) * intensidad,
                 1 - (1 - color.blue) * intensidad)


def _poligono(canvas, puntos, color):
    canvas.setFillColor(color)
    trazado = canvas.beginPath()
    trazado.moveTo(*puntos[0])
    for punto in puntos[1:]:
        trazado.lineTo(*punto)
    trazado.close()
    canvas.drawPath(trazado, fill=1, stroke=0)


def _fondo_pdf(canvas, modelo, ancho, alto, primario, acento):
    """Cada modelo tiene una silueta propia; todos dejan intactas las zonas de lectura."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm

    canvas.setFillColor(white)
    canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
    if modelo == 'sobrio':
        canvas.setFillColor(primario)
        canvas.rect(0, alto - 7 * mm, ancho, 7 * mm, fill=1, stroke=0)
        canvas.setFillColor(acento)
        canvas.rect(18 * mm, alto - 8.3 * mm, 42 * mm, 1.3 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(_tinte(primario, .25))
        canvas.setLineWidth(.65)
        canvas.line(18 * mm, 59.5 * mm, ancho - 18 * mm, 59.5 * mm)
    elif modelo == 'tecnologico':
        canvas.setFillColor(primario)
        canvas.rect(0, 0, 12 * mm, alto, fill=1, stroke=0)
        canvas.setStrokeColor(_tinte(primario, .16))
        canvas.setLineWidth(.6)
        for y in (26, 47, 165, 185):
            canvas.line(14 * mm, y * mm, 22 * mm, y * mm)
            canvas.line(22 * mm, y * mm, 27 * mm, (y + 5) * mm)
            canvas.circle(27 * mm, (y + 5) * mm, 1.2 * mm, fill=0)
        for x in range(250, 294, 8):
            for y in range(163, 208, 8):
                canvas.setFillColor(_tinte(primario, .16))
                canvas.circle(x * mm, y * mm, .45 * mm, fill=1, stroke=0)
        _poligono(canvas, [(ancho - 20 * mm, 0), (ancho, 0), (ancho, 20 * mm)], acento)
        canvas.setStrokeColor(acento)
        canvas.setLineWidth(1.5)
        canvas.line(20 * mm, alto - 12 * mm, 57 * mm, alto - 12 * mm)
    elif modelo == 'geometrico':
        _poligono(canvas, [(0, alto), (54 * mm, alto), (0, alto - 47 * mm)], primario)
        _poligono(canvas, [(0, alto - 29 * mm), (0, alto - 47 * mm), (21 * mm, alto - 29 * mm)], acento)
        _poligono(canvas, [(ancho - 55 * mm, 0), (ancho, 0), (ancho, 47 * mm)], primario)
        _poligono(canvas, [(ancho - 33 * mm, 0), (ancho - 16 * mm, 0), (ancho, 16 * mm), (ancho, 33 * mm)], acento)
        canvas.setFillColor(_tinte(primario, .045))
        canvas.rect(25 * mm, 62 * mm, ancho - 50 * mm, 36 * mm, fill=1, stroke=0)
    elif modelo == 'elegante':
        canvas.setFillColor(HexColor('#FFFEFA'))
        canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
        for distancia, grosor, color in ((8, .9, primario), (10, .35, acento), (12, .35, primario)):
            canvas.setStrokeColor(color)
            canvas.setLineWidth(grosor)
            canvas.rect(distancia * mm, distancia * mm, ancho - 2 * distancia * mm, alto - 2 * distancia * mm)
        for x in (12 * mm, ancho - 12 * mm):
            for y in (12 * mm, alto - 12 * mm):
                canvas.setFillColor(acento)
                canvas.circle(x, y, 1.1 * mm, fill=1, stroke=0)
    elif modelo == 'congreso':
        canvas.setFillColor(_tinte(primario, .07))
        canvas.rect(0, alto - 48 * mm, ancho, 48 * mm, fill=1, stroke=0)
        canvas.setFillColor(acento)
        canvas.rect(16 * mm, 62 * mm, 2 * mm, 84 * mm, fill=1, stroke=0)
        canvas.setFillColor(primario)
        canvas.rect(0, 0, ancho, 5 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(_tinte(primario, .17))
        canvas.setLineWidth(1)
        for radio in (30, 39, 48):
            canvas.circle(ancho + 12 * mm, alto - 64 * mm, radio * mm, fill=0, stroke=1)
    else:
        canvas.setStrokeColor(primario)
        canvas.setLineWidth(1.4)
        canvas.rect(9 * mm, 9 * mm, ancho - 18 * mm, alto - 18 * mm)
        canvas.setStrokeColor(acento)
        canvas.setLineWidth(.65)
        canvas.rect(11 * mm, 11 * mm, ancho - 22 * mm, alto - 22 * mm)
        canvas.setFillColor(primario)
        canvas.rect(0, 0, 5 * mm, alto, fill=1, stroke=0)
        canvas.rect(ancho - 5 * mm, 0, 5 * mm, alto, fill=1, stroke=0)


def _cajas_logos(logos, x, top, ancho, alto, disposicion='auto'):
    """Alinea cada grupo y resuelve límites comunes sin estirar ni superponer imágenes."""
    from reportlab.lib.units import mm

    cantidad = len(logos)
    if not cantidad:
        return []
    hueco = 6 * mm
    caja = min(56 * mm, (ancho - hueco * (cantidad - 1)) / cantidad)
    por_defecto = disposicion if disposicion in ('izquierda', 'derecha') else 'centro'
    posiciones = [logo.get('posicion', 'auto') for logo in logos]
    if disposicion == 'entre_extremos' or (disposicion == 'auto' and all(p == 'auto' for p in posiciones)):
        if cantidad == 1:
            coordenadas = [(0, x + (ancho - caja) / 2)]
        else:
            coordenadas = [(i, x + i * (ancho - caja) / (cantidad - 1)) for i in range(cantidad)]
    else:
        grupos = {'izquierda': [], 'centro': [], 'derecha': []}
        for indice, posicion in enumerate(posiciones):
            grupos[posicion if posicion in grupos else por_defecto].append(indice)
        coordenadas = []
        for posicion, indices in grupos.items():
            bloque = len(indices) * caja + max(0, len(indices) - 1) * hueco
            inicio = x if posicion == 'izquierda' else x + (ancho - bloque) / (1 if posicion == 'derecha' else 2)
            coordenadas.extend((indice, inicio + lugar * (caja + hueco)) for lugar, indice in enumerate(indices))
        coordenadas.sort(key=lambda elemento: (elemento[1], elemento[0]))
        ajustadas = []
        limite = x
        for indice, deseado in coordenadas:
            izquierda = max(limite, deseado)
            ajustadas.append([indice, izquierda])
            limite = izquierda + caja + hueco
        limite = x + ancho - caja
        for elemento in reversed(ajustadas):
            elemento[1] = min(limite, elemento[1])
            limite = elemento[1] - caja - hueco
        coordenadas = ajustadas
    return [(logos[indice], izquierda, top - alto, caja, alto) for indice, izquierda in coordenadas]


def _dibujar_logos(canvas, diseno, x, top, ancho, alto, primario):
    from reportlab.lib.colors import white
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    logos = list(diseno.get('logos') or [])[:4]
    if not logos and diseno.get('logo'):
        logos = [{'imagen': diseno['logo'], 'fondo': 'oscuro', 'posicion': 'auto'}]
    for logo, lx, ly, lw, lh in _cajas_logos(logos, x, top, ancho, alto, diseno.get('disposicion_logos', 'auto')):
        canvas.setFillColor(primario if logo.get('fondo') == 'oscuro' else white)
        canvas.roundRect(lx, ly, lw, lh, 2 * mm, fill=1, stroke=0)
        imagen = ImageReader(BytesIO(base64.b64decode(logo['imagen'])))
        canvas.drawImage(imagen, lx + 3 * mm, ly + 2 * mm, width=lw - 6 * mm, height=lh - 4 * mm,
                         preserveAspectRatio=True, anchor='c', mask='auto')


def _datos_evento(canvas, certificado, diseno, x, top, ancho, primario, fuente, negrita, modelo):
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor

    datos = []
    if diseno.get('fecha_inicio'):
        datos.append(('INICIO', diseno['fecha_inicio']))
    if diseno.get('fecha_fin'):
        datos.append(('FINALIZACIÓN', diseno['fecha_fin']))
    datos.append(('EMISIÓN', diseno.get('fecha', '')))
    datos.append(('DURACIÓN', f"{diseno.get('horas', _horas_texto(certificado.horas))} horas"))
    alto = 12 * mm
    canvas.setFillColor(_tinte(primario, .065))
    canvas.roundRect(x, top - alto, ancho, alto, 2 * mm, fill=1, stroke=0)
    columna = ancho / len(datos)
    for indice, (etiqueta, valor) in enumerate(datos):
        dx = x + columna * indice
        _texto_pdf(canvas, etiqueta, dx + 2 * mm, top - 1.6 * mm, columna - 4 * mm, 4 * mm,
                   HexColor('#526660'), fuente, 8.5)
        _texto_pdf(canvas, valor, dx + 2 * mm, top - 5.4 * mm, columna - 4 * mm, 5.5 * mm,
                   primario, negrita, 11, 10)


def _firmas_y_verificacion(canvas, certificado, diseno, x, top, ancho, primario, acento, fuente, negrita):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    muted = HexColor('#526660')
    qr_ancho = 28 * mm
    qr_x = x + ancho - qr_ancho
    qr_top = top - 3 * mm
    # QR y código viven fuera de las columnas de firmas, incluso con tres firmantes.
    canvas.setFillColor(white)
    canvas.roundRect(qr_x - 4 * mm, qr_top - qr_ancho - 11 * mm, qr_ancho + 8 * mm, qr_ancho + 13 * mm, 2 * mm, fill=1, stroke=0)
    url = diseno.get('verificacion_url', '')
    if url:
        qr = QrCodeWidget(url)
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(qr_ancho, qr_ancho, transform=[qr_ancho / (x2-x1), 0, 0, qr_ancho / (y2-y1), 0, 0])
        dibujo.add(qr)
        renderPDF.draw(dibujo, canvas, qr_x, qr_top - qr_ancho)
        canvas.linkURL(url, (qr_x, qr_top - qr_ancho, qr_x + qr_ancho, qr_top), relative=0, thickness=0)
    _texto_pdf(canvas, 'Verificar certificado', qr_x - 3 * mm, qr_top - qr_ancho - 1.4 * mm,
               qr_ancho + 6 * mm, 4 * mm, muted, fuente, 8.5, 8.5)
    _texto_pdf(canvas, certificado.codigo, qr_x - 3 * mm, qr_top - qr_ancho - 5.6 * mm,
               qr_ancho + 6 * mm, 4 * mm, primario, negrita, 8.5, 8)
    firmantes = list(diseno.get('firmantes') or [])[:3]
    espacio = ancho - qr_ancho - 9 * mm
    if not firmantes:
        return
    columna = espacio / len(firmantes)
    for indice, firma in enumerate(firmantes):
        fx = x + indice * columna + 2 * mm
        fw = columna - 4 * mm
        if firma.get('imagen'):
            canvas.drawImage(ImageReader(BytesIO(base64.b64decode(firma['imagen']))),
                             fx + 3 * mm, top - 9 * mm, width=fw - 6 * mm, height=9 * mm,
                             preserveAspectRatio=True, anchor='c', mask='auto')
        canvas.setStrokeColor(_tinte(primario, .65))
        canvas.setLineWidth(.6)
        canvas.line(fx + 2 * mm, top - 10 * mm, fx + fw - 2 * mm, top - 10 * mm)
        nombre_caja = _texto_pdf(canvas, firma.get('nombre', ''), fx, top - 11.2 * mm, fw, 13.8 * mm,
                                primario, negrita, 10, 8.25, interlineado=1.12)
        cargo_top = nombre_caja[1] - 1.5 * mm if nombre_caja else top - 12 * mm
        _texto_pdf(canvas, firma.get('cargo', ''), fx, cargo_top, fw, 17.4 * mm,
                   muted, fuente, 9.5, 8, interlineado=1.1)


def _dibujar_certificado_v2(certificado, diseno, mostrar_documento=True, vista_previa=False):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    fuente, negrita = _fuentes_pdf()
    modelo = diseno.get('diseno', 'clasico')
    if modelo not in DISENOS_CERTIFICADO:
        modelo = 'clasico'
    serif = modelo in ('clasico', 'elegante')
    titulo_fuente = 'Times-Roman' if serif else negrita
    nombre_fuente = 'Times-Bold' if serif else negrita
    primario = HexColor(diseno.get('primario', '#1E5A3D'))
    acento = HexColor(diseno.get('acento', '#E1B93F'))
    tinta, secundario = HexColor('#18332C'), HexColor('#526660')
    ancho, alto = landscape(A4)
    salida = BytesIO()
    lienzo = canvas.Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(('Vista previa - ' if vista_previa else '') + 'Certificado ' + certificado.codigo)
    lienzo.setAuthor(diseno.get('institucion', ''))
    _fondo_pdf(lienzo, modelo, ancho, alto, primario, acento)
    izquierda = (28 if modelo == 'tecnologico' else 23) * mm
    derecha = ancho - 23 * mm
    espacio = derecha - izquierda
    alineacion = 'izquierda' if modelo in ('sobrio', 'congreso') else 'centro'
    _dibujar_logos(lienzo, diseno, izquierda, 195 * mm, espacio, 22 * mm, primario)
    _texto_pdf(lienzo, diseno.get('institucion', '').upper(), izquierda, 172 * mm, espacio, 8 * mm,
               primario, negrita, 10, 8.5, alineacion=alineacion)
    _texto_pdf(lienzo, diseno['titulo'], izquierda, (160 if modelo == 'congreso' else 163) * mm, espacio, 19 * mm,
               primario, titulo_fuente, 28 if serif else 25, 18, alineacion=alineacion)
    if modelo in ('clasico', 'elegante'):
        centro = izquierda + espacio / 2
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(1)
        lienzo.line(centro - 24 * mm, 143 * mm, centro + 24 * mm, 143 * mm)
        if modelo == 'elegante':
            lienzo.setFillColor(acento)
            _poligono(lienzo, [(centro, 141.5 * mm), (centro + 1.5 * mm, 143 * mm),
                              (centro, 144.5 * mm), (centro - 1.5 * mm, 143 * mm)], acento)
    elif modelo in ('sobrio', 'congreso'):
        lienzo.setFillColor(acento)
        lienzo.rect(izquierda, 143 * mm, 25 * mm, mm, fill=1, stroke=0)
    _texto_pdf(lienzo, 'Se certifica que', izquierda, 140 * mm, espacio, 6 * mm,
               secundario, fuente, 11, alineacion=alineacion)
    _texto_pdf(lienzo, certificado.nombre, izquierda, 130 * mm, espacio, 23 * mm,
               tinta, nombre_fuente, 26 if serif else 24, 14, alineacion=alineacion, interlineado=1.14)
    if mostrar_documento and getattr(certificado, 'documento', ''):
        _texto_pdf(lienzo, 'Documento de identidad: ' + certificado.documento, izquierda,
                   105 * mm, espacio, 5.5 * mm, secundario, fuente, 9.5, 9, alineacion=alineacion)
    _texto_pdf(lienzo, diseno['texto'], izquierda + 2 * mm, 98 * mm, espacio - 4 * mm, 23.5 * mm,
               tinta, fuente, 12, 9.75, alineacion=alineacion, interlineado=1.2)
    _datos_evento(lienzo, certificado, diseno, izquierda, 73 * mm, espacio,
                  primario, fuente, negrita, modelo)
    _firmas_y_verificacion(lienzo, certificado, diseno, izquierda, 58 * mm, espacio,
                           primario, acento, fuente, negrita)
    if getattr(certificado, 'anulado', False):
        lienzo.saveState()
        lienzo.setFillColor(HexColor('#FFFFFF'))
        lienzo.setFillAlpha(.92)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(lienzo, 'CERTIFICADO ANULADO', 15 * mm, alto / 2 + 7 * mm, ancho - 30 * mm,
                   14 * mm, HexColor('#A62020'), negrita, 25, 22)
    elif vista_previa:
        lienzo.setFillColor(HexColor('#9B2424'))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(ancho / 2, (7 if modelo == 'congreso' else 3) * mm, 'VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ')
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()



def _onda_v3(canvas, puntos, color):
    """Superficie curva vectorial original; no usa ilustraciones ni recursos remotos."""
    canvas.setFillColor(color)
    camino = canvas.beginPath()
    camino.moveTo(*puntos[0])
    for segmento in puntos[1:]:
        if len(segmento) == 2:
            camino.lineTo(*segmento)
        else:
            camino.curveTo(*segmento)
    camino.close()
    canvas.drawPath(camino, fill=1, stroke=0)


def _fondo_pdf_v3(canvas, modelo, ancho, alto, primario, acento, siglas):
    from math import cos, pi, sin
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm

    canvas.setFillColor(white)
    canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
    if modelo == "clasico":
        canvas.setStrokeColor(_tinte(primario, 0.38))
        canvas.setLineWidth(0.55)
        canvas.rect(12 * mm, 9 * mm, ancho - 24 * mm, alto - 18 * mm)
        canvas.setStrokeColor(acento)
        canvas.rect(14 * mm, 11 * mm, ancho - 28 * mm, alto - 22 * mm)
        _poligono(canvas, [(0, alto), (72 * mm, alto), (0, alto - 39 * mm)], primario)
        _poligono(
            canvas,
            [
                (0, alto - 26 * mm),
                (66 * mm, alto),
                (76 * mm, alto),
                (0, alto - 43 * mm),
            ],
            acento,
        )
        _poligono(
            canvas,
            [
                (0, alto - 47 * mm),
                (81 * mm, alto),
                (92 * mm, alto),
                (0, alto - 51 * mm),
            ],
            _tinte(primario, 0.13),
        )
        _poligono(
            canvas, [(ancho, 0), (ancho - 77 * mm, 0), (ancho, 44 * mm)], primario
        )
        _poligono(
            canvas,
            [
                (ancho - 78 * mm, 0),
                (ancho - 67 * mm, 0),
                (ancho, 38 * mm),
                (ancho, 44 * mm),
            ],
            acento,
        )
        _poligono(
            canvas, [(0, 0), (0, 41 * mm), (7 * mm, 38 * mm), (7 * mm, 0)], primario
        )
        # Una marca de agua tipográfica usa la identidad congelada, sin inventar un sello.
        canvas.saveState()
        canvas.setFillColor(primario)
        canvas.setFillAlpha(0.035)
        from reportlab.pdfbase.pdfmetrics import stringWidth

        marca = str(siglas or "")
        tamano = min(102, 205 * mm / max(stringWidth(marca, "Times-Bold", 1), 1))
        canvas.setFont("Times-Bold", tamano)
        canvas.drawCentredString(ancho / 2, 87 * mm, marca)
        canvas.restoreState()
    elif modelo == "sobrio":
        canvas.setFillColor(primario)
        canvas.rect(0, 0, 48 * mm, alto, fill=1, stroke=0)
        canvas.setFillColor(acento)
        canvas.rect(48 * mm, 0, 1.6 * mm, alto, fill=1, stroke=0)
        canvas.setStrokeColor(_tinte(primario, 0.17))
        canvas.setLineWidth(0.55)
        canvas.line(62 * mm, 60 * mm, ancho - 20 * mm, 60 * mm)
        canvas.setFillColor(_tinte(primario, 0.05))
        canvas.rect(62 * mm, 65 * mm, ancho - 82 * mm, 32 * mm, fill=1, stroke=0)
        # Trazado editorial en la franja, separado del código y de los logos.
        canvas.saveState()
        canvas.setStrokeColor(acento)
        canvas.setStrokeAlpha(0.32)
        canvas.setLineWidth(0.7)
        for delta in range(0, 25, 5):
            camino = canvas.beginPath()
            camino.moveTo(0, (91 + delta) * mm)
            camino.curveTo(
                13 * mm,
                (100 + delta) * mm,
                35 * mm,
                (83 + delta) * mm,
                48 * mm,
                (94 + delta) * mm,
            )
            canvas.drawPath(camino, stroke=1, fill=0)
        canvas.restoreState()
    elif modelo == "tecnologico":
        fondo = HexColor("#0A1C24")
        canvas.setFillColor(fondo)
        canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
        canvas.saveState()
        canvas.setStrokeColor(_tinte(primario, 0.56))
        canvas.setStrokeAlpha(0.32)
        canvas.setLineWidth(0.45)
        for x in range(6, 298, 12):
            canvas.line(x * mm, 0, x * mm, alto)
        for y in range(6, 211, 12):
            canvas.line(0, y * mm, ancho, y * mm)
        canvas.restoreState()
        nodos = [
            (2, 151),
            (13, 162),
            (5, 181),
            (20, 202),
            (42, 204),
            (76, 207),
            (279, 201),
            (290, 185),
            (284, 160),
            (295, 145),
            (287, 123),
            (296, 105),
            (7, 53),
            (18, 39),
            (8, 20),
            (24, 7),
            (278, 8),
            (287, 25),
            (297, 39),
        ]
        canvas.setStrokeColor(acento)
        canvas.setLineWidth(0.65)
        for inicio, final in zip(nodos, nodos[1:]):
            if abs(inicio[0] - final[0]) < 48:
                canvas.line(
                    inicio[0] * mm, inicio[1] * mm, final[0] * mm, final[1] * mm
                )
        for x, y in nodos:
            canvas.setFillColor(fondo)
            canvas.circle(x * mm, y * mm, 1.15 * mm, fill=1, stroke=1)
            canvas.setFillColor(acento)
            canvas.circle(x * mm, y * mm, 0.38 * mm, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.roundRect(
            19 * mm, 65 * mm, ancho - 38 * mm, 81 * mm, 4 * mm, fill=1, stroke=0
        )
        canvas.roundRect(
            19 * mm, 10 * mm, ancho - 38 * mm, 50 * mm, 3 * mm, fill=1, stroke=0
        )
        _poligono(
            canvas,
            [
                (21 * mm, 146 * mm),
                (51 * mm, 146 * mm),
                (47 * mm, 144 * mm),
                (21 * mm, 144 * mm),
            ],
            acento,
        )
    elif modelo == "geometrico":
        # Facetas de color y una retícula hexagonal tenue, fuera de las zonas de firma.
        _poligono(
            canvas,
            [(0, alto), (57 * mm, alto), (22 * mm, 174 * mm), (0, 181 * mm)],
            primario,
        )
        _poligono(
            canvas,
            [(0, 181 * mm), (22 * mm, 174 * mm), (12 * mm, 150 * mm), (0, 155 * mm)],
            _tinte(primario, 0.5),
        )
        _poligono(
            canvas, [(57 * mm, alto), (77 * mm, alto), (22 * mm, 174 * mm)], acento
        )
        _poligono(canvas, [(0, 155 * mm), (12 * mm, 150 * mm), (0, 121 * mm)], acento)
        _poligono(
            canvas,
            [
                (ancho, 0),
                (ancho - 64 * mm, 0),
                (ancho - 25 * mm, 25 * mm),
                (ancho, 63 * mm),
            ],
            primario,
        )
        _poligono(
            canvas,
            [(ancho - 64 * mm, 0), (ancho - 83 * mm, 0), (ancho - 25 * mm, 25 * mm)],
            acento,
        )
        _poligono(
            canvas,
            [(ancho, 63 * mm), (ancho - 25 * mm, 25 * mm), (ancho - 12 * mm, 72 * mm)],
            _tinte(primario, 0.35),
        )
        canvas.saveState()
        canvas.setStrokeColor(primario)
        canvas.setStrokeAlpha(0.12)
        canvas.setLineWidth(0.4)
        for columna in range(6):
            for fila in range(4):
                cx = (215 + columna * 11) * mm
                cy = (94 + fila * 10 + (columna % 2) * 5) * mm
                camino = canvas.beginPath()
                for indice in range(6):
                    punto = (
                        cx + 6 * mm * cos(indice * pi / 3),
                        cy + 6 * mm * sin(indice * pi / 3),
                    )
                    (camino.moveTo if indice == 0 else camino.lineTo)(*punto)
                camino.close()
                canvas.drawPath(camino, stroke=1, fill=0)
        canvas.restoreState()
        canvas.setStrokeColor(_tinte(primario, 0.25))
        canvas.setLineWidth(0.6)
        canvas.line(21 * mm, 60 * mm, ancho - 21 * mm, 60 * mm)
    elif modelo == "elegante":
        canvas.setFillColor(HexColor("#FBF8EE"))
        canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
        for distancia, grosor, color in (
            (8, 0.7, primario),
            (10, 0.3, acento),
            (12, 0.35, primario),
        ):
            canvas.setStrokeColor(color)
            canvas.setLineWidth(grosor)
            canvas.rect(
                distancia * mm,
                distancia * mm,
                ancho - 2 * distancia * mm,
                alto - 2 * distancia * mm,
            )
        # Filetes ondulados y rosetas abstractas: ornamento, sin afirmación de acreditación.
        canvas.saveState()
        canvas.setStrokeColor(acento)
        canvas.setStrokeAlpha(0.36)
        canvas.setLineWidth(0.4)
        for dx in (15, 17, 280, 282):
            camino = canvas.beginPath()
            camino.moveTo(dx * mm, 20 * mm)
            for y in range(20, 188, 12):
                camino.curveTo(
                    (dx + 1.1) * mm,
                    (y + 3) * mm,
                    (dx - 1.1) * mm,
                    (y + 9) * mm,
                    dx * mm,
                    (y + 12) * mm,
                )
            canvas.drawPath(camino, stroke=1, fill=0)
        for cx, cy in ((15, 195), (282, 195), (15, 15), (282, 15)):
            for radio in (1.4, 2.4, 3.4):
                canvas.circle(cx * mm, cy * mm, radio * mm, stroke=1, fill=0)
        canvas.restoreState()
    else:  # Congreso: ondas orgánicas, distintas de la red tecnológica.
        oscuro = HexColor("#102C27")
        canvas.setFillColor(oscuro)
        canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
        _onda_v3(
            canvas,
            [
                (0, 0),
                (ancho, 0),
                (ancho, 64 * mm),
                (225 * mm, 45 * mm, 180 * mm, 17 * mm, 120 * mm, 31 * mm),
                (70 * mm, 44 * mm, 32 * mm, 17 * mm, 0, 29 * mm),
            ],
            primario,
        )
        _onda_v3(
            canvas,
            [
                (0, 0),
                (ancho, 0),
                (ancho, 35 * mm),
                (226 * mm, 15 * mm, 190 * mm, 5 * mm, 127 * mm, 19 * mm),
                (65 * mm, 32 * mm, 30 * mm, 5 * mm, 0, 18 * mm),
            ],
            acento,
        )
        _onda_v3(
            canvas,
            [
                (0, alto),
                (ancho, alto),
                (ancho, 179 * mm),
                (232 * mm, 185 * mm, 226 * mm, 201 * mm, 160 * mm, 199 * mm),
                (90 * mm, 196 * mm, 66 * mm, 177 * mm, 0, 191 * mm),
            ],
            _tinte(primario, 0.7),
        )
        canvas.saveState()
        canvas.setStrokeColor(acento)
        canvas.setStrokeAlpha(0.24)
        canvas.setLineWidth(0.65)
        for delta in (0, 4, 8):
            camino = canvas.beginPath()
            camino.moveTo(0, (166 + delta) * mm)
            camino.curveTo(
                62 * mm,
                (193 + delta) * mm,
                104 * mm,
                (180 + delta) * mm,
                160 * mm,
                (189 + delta) * mm,
            )
            camino.curveTo(
                225 * mm,
                (199 + delta) * mm,
                250 * mm,
                (169 + delta) * mm,
                ancho,
                (180 + delta) * mm,
            )
            canvas.drawPath(camino, stroke=1, fill=0)
        canvas.restoreState()
        # La placa curva reserva el centro completo para nombres, relato y firmas.
        _onda_v3(
            canvas,
            [
                (20 * mm, 14 * mm),
                (20 * mm, 137 * mm),
                (20 * mm, 144 * mm, 24 * mm, 146 * mm, 31 * mm, 146 * mm),
                (266 * mm, 146 * mm),
                (273 * mm, 146 * mm, 277 * mm, 141 * mm, 277 * mm, 134 * mm),
                (277 * mm, 22 * mm),
                (277 * mm, 12 * mm, 271 * mm, 9 * mm, 261 * mm, 10 * mm),
                (94 * mm, 10 * mm, 69 * mm, 20 * mm, 20 * mm, 14 * mm),
            ],
            white,
        )


def _logo_en_caja_v3(canvas, logo, x, y, ancho, alto, primario):
    from reportlab.lib.colors import white
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    canvas.setFillColor(primario if logo.get("fondo") == "oscuro" else white)
    canvas.roundRect(x, y, ancho, alto, 1.8 * mm, fill=1, stroke=0)
    canvas.drawImage(
        ImageReader(BytesIO(base64.b64decode(logo["imagen"]))),
        x + 2.5 * mm,
        y + 2 * mm,
        width=ancho - 5 * mm,
        height=alto - 4 * mm,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )


def _logos_v3(canvas, diseno, modelo, x, ancho, primario, acento):
    from reportlab.lib.units import mm

    logos = list(diseno.get("logos") or [])[:4]
    if not logos and diseno.get("logo"):
        logos = [{"imagen": diseno["logo"], "fondo": "oscuro", "posicion": "auto"}]
    disposicion = diseno.get("disposicion_logos", "auto")
    # Las ubicaciones explícitas prevalecen. La composición especial sólo usa el modo automático.
    especial = bool(
        logos
        and disposicion == "auto"
        and all(logo.get("posicion", "auto") == "auto" for logo in logos)
    )
    if especial and modelo == "sobrio":
        _logo_en_caja_v3(
            canvas, logos.pop(0), 6 * mm, 171 * mm, 36 * mm, 24 * mm, primario
        )
    elif especial and modelo == "elegante":
        # Lazo abstracto y marco circular; el logo real se contiene sin deformarlo.
        _poligono(
            canvas,
            [
                (253 * mm, 179 * mm),
                (258 * mm, 157 * mm),
                (264 * mm, 162 * mm),
                (270 * mm, 158 * mm),
                (275 * mm, 180 * mm),
            ],
            acento,
        )
        canvas.setFillColor(primario)
        canvas.circle(264 * mm, 184 * mm, 17 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(acento)
        canvas.setLineWidth(0.65)
        canvas.circle(264 * mm, 184 * mm, 15.5 * mm, fill=0, stroke=1)
        _logo_en_caja_v3(
            canvas, logos.pop(0), 250 * mm, 176 * mm, 28 * mm, 16 * mm, primario
        )
        ancho = min(ancho, 215 * mm)
    for logo, lx, ly, lw, lh in _cajas_logos(
        logos, x, 195 * mm, ancho, 19 * mm, disposicion
    ):
        _logo_en_caja_v3(canvas, logo, lx, ly, lw, lh, primario)


def _qr_v3(canvas, certificado, diseno, x, top, primario, fuente, negrita):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm

    tamano = 28 * mm
    canvas.setFillColor(white)
    canvas.roundRect(
        x - 3 * mm,
        top - tamano - 11 * mm,
        tamano + 6 * mm,
        tamano + 13 * mm,
        2 * mm,
        fill=1,
        stroke=0,
    )
    url = diseno.get("verificacion_url", "")
    if url:
        qr = QrCodeWidget(url)
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(
            tamano,
            tamano,
            transform=[tamano / (x2 - x1), 0, 0, tamano / (y2 - y1), 0, 0],
        )
        dibujo.add(qr)
        renderPDF.draw(dibujo, canvas, x, top - tamano)
        canvas.linkURL(url, (x, top - tamano, x + tamano, top), relative=0, thickness=0)
    _texto_pdf(
        canvas,
        "Verificar certificado",
        x - 3 * mm,
        top - tamano - 1.4 * mm,
        tamano + 6 * mm,
        4 * mm,
        HexColor("#526660"),
        fuente,
        8.5,
        8.5,
    )
    _texto_pdf(
        canvas,
        certificado.codigo,
        x - 3 * mm,
        top - tamano - 5.6 * mm,
        tamano + 6 * mm,
        4 * mm,
        primario,
        negrita,
        8.5,
        8,
    )


def _firmas_v3(
    canvas,
    certificado,
    diseno,
    modelo,
    x,
    top,
    ancho,
    primario,
    acento,
    fuente,
    negrita,
):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    if modelo != "sobrio":
        return _firmas_y_verificacion(
            canvas,
            certificado,
            diseno,
            x,
            top,
            ancho,
            primario,
            acento,
            fuente,
            negrita,
        )
    # El panel lateral contiene la verificación; las tres firmas comparten el ancho editorial.
    _qr_v3(canvas, certificado, diseno, 10 * mm, 58 * mm, primario, fuente, negrita)
    firmantes = list(diseno.get("firmantes") or [])[:3]
    for indice, firma in enumerate(firmantes):
        columna = ancho / max(len(firmantes), 1)
        fx = x + indice * columna + 2 * mm
        fw = columna - 4 * mm
        if firma.get("imagen"):
            canvas.drawImage(
                ImageReader(BytesIO(base64.b64decode(firma["imagen"]))),
                fx + 3 * mm,
                top - 9 * mm,
                width=fw - 6 * mm,
                height=9 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        canvas.setStrokeColor(_tinte(primario, 0.65))
        canvas.setLineWidth(0.6)
        canvas.line(fx + 2 * mm, top - 10 * mm, fx + fw - 2 * mm, top - 10 * mm)
        caja = _texto_pdf(
            canvas,
            firma.get("nombre", ""),
            fx,
            top - 11.2 * mm,
            fw,
            13.8 * mm,
            primario,
            negrita,
            10,
            8.25,
            interlineado=1.12,
        )
        cargo_top = caja[1] - 1.5 * mm if caja else top - 12 * mm
        _texto_pdf(
            canvas,
            firma.get("cargo", ""),
            fx,
            cargo_top,
            fw,
            17.4 * mm,
            HexColor("#526660"),
            fuente,
            9.5,
            8,
            interlineado=1.1,
        )


def _dibujar_certificado_v3(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    fuente, negrita = _fuentes_pdf()
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_CERTIFICADO:
        modelo = "clasico"
    serif = modelo in ("clasico", "elegante")
    oscuro = modelo in ("tecnologico", "congreso")
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    tinta = HexColor("#18332C")
    secundario = HexColor("#526660")
    ancho, alto = landscape(A4)
    salida = BytesIO()
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(
        ("Vista previa - " if vista_previa else "")
        + "Certificado "
        + certificado.codigo
    )
    lienzo.setAuthor(diseno.get("institucion", ""))
    _fondo_pdf_v3(
        lienzo, modelo, ancho, alto, primario, acento, diseno.get("siglas", "")
    )
    izquierda = (62 if modelo == "sobrio" else 24) * mm
    derecha = ancho - (20 if modelo == "sobrio" else 24) * mm
    espacio = derecha - izquierda
    # Los snapshots V3 anteriores no incluían esta clave y conservan su composición.
    alineacion_anterior = "izquierda" if modelo in ("sobrio", "geometrico") else "centro"
    alineacion = diseno.get("alineacion_contenido", alineacion_anterior)
    if alineacion not in ("centro", "izquierda"):
        alineacion = alineacion_anterior
    _logos_v3(lienzo, diseno, modelo, izquierda, espacio, primario, acento)
    texto_header = white if oscuro else primario
    ancho_header = min(espacio, 215 * mm) if modelo == "elegante" else espacio
    _texto_pdf(
        lienzo,
        diseno.get("institucion", "").upper(),
        izquierda,
        175 * mm,
        ancho_header,
        5 * mm,
        texto_header,
        negrita,
        9.5,
        8.5,
        alineacion=alineacion,
        interlineado=1.05,
    )
    _texto_pdf(
        lienzo,
        diseno.get("emisor", ""),
        izquierda,
        169 * mm,
        ancho_header,
        7 * mm,
        white if oscuro else secundario,
        fuente,
        10,
        8.5,
        alineacion=alineacion,
        interlineado=1.08,
    )
    titulo_ancho = min(espacio, 226 * mm) if modelo == "elegante" else espacio
    _texto_pdf(
        lienzo,
        diseno["titulo"],
        izquierda,
        160 * mm,
        titulo_ancho,
        19 * mm,
        texto_header,
        "Times-Roman" if serif else negrita,
        34 if serif else 28,
        18,
        alineacion=alineacion,
        interlineado=1.08,
    )
    if modelo in ("clasico", "elegante"):
        centro = izquierda + espacio / 2
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.75)
        lienzo.line(centro - 23 * mm, 141 * mm, centro - 3 * mm, 141 * mm)
        lienzo.line(centro + 3 * mm, 141 * mm, centro + 23 * mm, 141 * mm)
        _poligono(
            lienzo,
            [
                (centro, 139.8 * mm),
                (centro + 1.2 * mm, 141 * mm),
                (centro, 142.2 * mm),
                (centro - 1.2 * mm, 141 * mm),
            ],
            acento,
        )
    _texto_pdf(
        lienzo,
        diseno.get("entradilla") or "Otorga el presente certificado a",
        izquierda,
        138 * mm,
        espacio,
        8 * mm,
        secundario,
        fuente,
        11,
        9.5,
        alineacion=alineacion,
        interlineado=1.1,
    )
    _texto_pdf(
        lienzo,
        certificado.nombre,
        izquierda,
        128 * mm,
        espacio,
        23 * mm,
        primario,
        "Times-Bold" if serif else negrita,
        31 if serif else 28,
        14,
        alineacion=alineacion,
        interlineado=1.12,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo,
            "Documento de identidad: " + certificado.documento,
            izquierda,
            103 * mm,
            espacio,
            5 * mm,
            secundario,
            fuente,
            9.5,
            9,
            alineacion=alineacion,
        )
    _texto_pdf(
        lienzo,
        diseno["texto"],
        izquierda + 2 * mm,
        96 * mm,
        espacio - 4 * mm,
        31 * mm,
        tinta,
        fuente,
        13.5,
        10.5,
        alineacion=alineacion,
        interlineado=1.17,
    )
    _texto_pdf(
        lienzo,
        "Emitido el " + diseno.get("fecha_emision", diseno.get("fecha", "")),
        izquierda,
        (64 if modelo == "tecnologico" or (modelo == "geometrico" and alineacion == "centro") else 62) * mm,
        espacio,
        3.5 * mm,
        white if modelo == "tecnologico" else secundario,
        fuente,
        8.5,
        8.5,
        alineacion=alineacion,
        interlineado=1.0,
    )
    _firmas_v3(
        lienzo,
        certificado,
        diseno,
        modelo,
        izquierda,
        57 * mm,
        espacio,
        primario,
        acento,
        fuente,
        negrita,
    )
    if modelo == "sobrio":
        caja = _texto_pdf(
            lienzo,
            diseno.get("institucion", ""),
            7 * mm,
            156 * mm,
            34 * mm,
            35 * mm,
            white,
            negrita,
            11,
            8.5,
            interlineado=1.15,
        )
        siglas_top = min(124 * mm, caja[1] - 3 * mm) if caja else 124 * mm
        _texto_pdf(
            lienzo,
            diseno.get("siglas", ""),
            7 * mm,
            siglas_top,
            34 * mm,
            14 * mm,
            acento,
            negrita,
            18,
            9.5,
        )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.92)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo,
            "CERTIFICADO ANULADO",
            15 * mm,
            alto / 2 + 7 * mm,
            ancho - 30 * mm,
            14 * mm,
            HexColor("#A62020"),
            negrita,
            25,
            22,
        )
    elif vista_previa:
        lienzo.setFillColor(HexColor("#FFD1D1") if oscuro else HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()



DISENOS_V4 = ('clasico', 'sobrio', 'tecnologico', 'geometrico', 'elegante', 'congreso',
              'industrial', 'circuitos', 'horizonte', 'editorial', 'academico', 'inmersivo')


def _foto_pdf_v4(lienzo, foto, caja, opacidad=1, puntos=None):
    """Recorta una fotografía local congelada conservando su proporción, sin deformarla."""
    from reportlab.lib.utils import ImageReader

    if not foto:
        return
    imagen = ImageReader(BytesIO(base64.b64decode(foto)))
    iw, ih = imagen.getSize()
    x, y, ancho, alto = caja
    escala = max(ancho / iw, alto / ih)
    lienzo.saveState()
    recorte = lienzo.beginPath()
    if puntos:
        recorte.moveTo(*puntos[0])
        for punto in puntos[1:]:
            recorte.lineTo(*punto)
        recorte.close()
    else:
        recorte.rect(x, y, ancho, alto)
    lienzo.clipPath(recorte, stroke=0)
    lienzo.setFillAlpha(opacidad)
    lienzo.drawImage(
        imagen,
        x + (ancho - iw * escala) / 2,
        y + (alto - ih * escala) / 2,
        width=iw * escala,
        height=ih * escala,
        mask="auto",
    )
    lienzo.restoreState()


def _fondo_v4(lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura):
    from math import cos, sin, pi
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm

    oscuro = modelo in ("tecnologico", "circuitos", "inmersivo")
    noche = HexColor("#081D2A") if modelo != "inmersivo" else HexColor("#13142F")
    lienzo.setFillColor(noche if oscuro else white)
    lienzo.rect(0, 0, ancho, alto, fill=1, stroke=0)
    cabecera = (
        noche if oscuro else primario if cabecera_oscura else _tinte(primario, 0.035)
    )
    lienzo.setFillColor(cabecera)
    lienzo.rect(0, 151 * mm, ancho, alto - 151 * mm, fill=1, stroke=0)
    foto = diseno.get("foto", "")
    if modelo == "clasico":
        lienzo.setLineWidth(1.1)
        lienzo.setStrokeColor(acento)
        lienzo.rect(8 * mm, 8 * mm, ancho - 16 * mm, alto - 16 * mm, stroke=1, fill=0)
        lienzo.setLineWidth(0.35)
        lienzo.rect(10 * mm, 10 * mm, ancho - 20 * mm, alto - 20 * mm, stroke=1, fill=0)
        for izquierda in (True, False):
            x = 0 if izquierda else ancho
            s = 1 if izquierda else -1
            _poligono(lienzo, [(x, 0), (x + s * 34 * mm, 0), (x, 34 * mm)], primario)
            _poligono(
                lienzo,
                [(x, alto), (x + s * 23 * mm, alto), (x, alto - 23 * mm)],
                acento,
            )
        lienzo.setFillColor(acento)
        lienzo.rect(ancho / 2 - 23 * mm, 150 * mm, 46 * mm, 1 * mm, fill=1, stroke=0)
    elif modelo == "sobrio":
        lienzo.setFillColor(primario)
        lienzo.rect(0, 0, 10 * mm, alto, fill=1, stroke=0)
        lienzo.setFillColor(acento)
        lienzo.rect(10 * mm, 0, 1.5 * mm, alto, fill=1, stroke=0)
        lienzo.setStrokeColor(_tinte(primario, 0.25))
        lienzo.setLineWidth(0.5)
        lienzo.line(20 * mm, 151 * mm, ancho - 20 * mm, 151 * mm)
        lienzo.line(20 * mm, 59 * mm, ancho - 20 * mm, 59 * mm)
    elif modelo == "tecnologico":
        lienzo.setStrokeColor(HexColor("#173B47"))
        lienzo.setLineWidth(0.35)
        for x in range(0, 300, 12):
            lienzo.line(x * mm, 0, x * mm, alto)
        for y in range(0, 216, 12):
            lienzo.line(0, y * mm, ancho, y * mm)
        for x, s in ((0, 1), (ancho, -1)):
            lienzo.setStrokeColor(acento)
            lienzo.setLineWidth(1.15)
            for j in range(6):
                p = lienzo.beginPath()
                p.moveTo(x, (16 + j * 15) * mm)
                p.lineTo(x + s * (11 + j % 3 * 5) * mm, (16 + j * 15) * mm)
                p.lineTo(x + s * (21 + j % 3 * 5) * mm, (26 + j * 15) * mm)
                p.lineTo(x + s * (21 + j % 3 * 5) * mm, (34 + j * 15) * mm)
                lienzo.drawPath(p, stroke=1)
                lienzo.circle(
                    x + s * (21 + j % 3 * 5) * mm,
                    (34 + j * 15) * mm,
                    1.2 * mm,
                    stroke=1,
                )
        lienzo.setFillColor(noche)
        lienzo.roundRect(
            21 * mm, 60 * mm, ancho - 42 * mm, 85 * mm, 3 * mm, fill=1, stroke=0
        )
        lienzo.setStrokeColor(HexColor("#355D67"))
        lienzo.roundRect(
            21 * mm, 60 * mm, ancho - 42 * mm, 85 * mm, 3 * mm, fill=0, stroke=1
        )
        lienzo.setFillColor(acento)
        lienzo.rect(ancho / 2 - 22 * mm, 150 * mm, 44 * mm, 0.8 * mm, fill=1, stroke=0)
    elif modelo == "geometrico":
        _poligono(lienzo, [(0, alto), (43 * mm, alto), (0, 151 * mm)], acento)
        _poligono(
            lienzo, [(ancho, 0), (ancho - 47 * mm, 0), (ancho, 54 * mm)], primario
        )
        _poligono(
            lienzo,
            [(ancho, 12 * mm), (ancho - 29 * mm, 0), (ancho - 16 * mm, 28 * mm)],
            _tinte(acento, 0.6),
        )
        lienzo.setStrokeColor(_tinte(primario, 0.13))
        lienzo.setLineWidth(0.45)
        for cx, cy, r in ((16, 105, 14), (281, 117, 18), (24, 47, 11)):
            pts = [
                ((cx + r * cos(i * pi / 3)) * mm, (cy + r * sin(i * pi / 3)) * mm)
                for i in range(7)
            ]
            p = lienzo.beginPath()
            p.moveTo(*pts[0])
            for punto in pts[1:]:
                p.lineTo(*punto)
            lienzo.drawPath(p, stroke=1)
        lienzo.setFillColor(acento)
        lienzo.rect(ancho / 2 - 20 * mm, 150 * mm, 40 * mm, 1 * mm, fill=1, stroke=0)
    elif modelo == "elegante":
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.65)
        lienzo.rect(9 * mm, 9 * mm, ancho - 18 * mm, alto - 18 * mm, stroke=1, fill=0)
        lienzo.rect(11 * mm, 11 * mm, ancho - 22 * mm, alto - 22 * mm, stroke=1, fill=0)
        for lado in (17 * mm, ancho - 17 * mm):
            for i in range(11):
                yy = (50 + i * 9) * mm
                lienzo.saveState()
                lienzo.translate(lado, yy)
                lienzo.rotate(35 if lado < ancho / 2 else -35)
                lienzo.setFillColor(_tinte(acento, 0.45))
                lienzo.ellipse(-1.5 * mm, -4 * mm, 1.5 * mm, 4 * mm, fill=1, stroke=0)
                lienzo.restoreState()
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.8)
        lienzo.line(ancho / 2 - 32 * mm, 150.5 * mm, ancho / 2 - 4 * mm, 150.5 * mm)
        lienzo.line(ancho / 2 + 4 * mm, 150.5 * mm, ancho / 2 + 32 * mm, 150.5 * mm)
        _poligono(
            lienzo,
            [
                (ancho / 2, 153 * mm),
                (ancho / 2 + 2.5 * mm, 150.5 * mm),
                (ancho / 2, 148 * mm),
                (ancho / 2 - 2.5 * mm, 150.5 * mm),
            ],
            acento,
        )
    elif modelo == "congreso":
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(1.4)
        p = lienzo.beginPath()
        p.moveTo(0, 152 * mm)
        p.curveTo(85 * mm, 151 * mm, 190 * mm, 151 * mm, ancho, 152 * mm)
        lienzo.drawPath(p, stroke=1)
        _poligono(lienzo, [(0, 0), (ancho, 0), (ancho, 5 * mm), (0, 12 * mm)], primario)
        lienzo.setStrokeColor(_tinte(acento, 0.3))
        lienzo.setLineWidth(0.5)
        for j in range(4):
            p = lienzo.beginPath()
            p.moveTo(0, (26 + j * 3) * mm)
            p.curveTo(
                90 * mm,
                (4 + j * 3) * mm,
                210 * mm,
                (48 + j * 3) * mm,
                ancho,
                (20 + j * 3) * mm,
            )
            lienzo.drawPath(p, stroke=1)
    elif modelo == "industrial":
        if foto:
            _foto_pdf_v4(
                lienzo,
                foto,
                (ancho * 0.48, 151 * mm, ancho * 0.52, alto - 151 * mm),
                0.88,
                [
                    (ancho * 0.43, 151 * mm),
                    (ancho, 151 * mm),
                    (ancho, alto),
                    (ancho * 0.61, alto),
                ],
            )
            lienzo.saveState()
            lienzo.setFillColor(primario)
            lienzo.setFillAlpha(0.45)
            lienzo.rect(0, 151 * mm, ancho, alto - 151 * mm, fill=1, stroke=0)
            lienzo.restoreState()
        _poligono(
            lienzo,
            [
                (0, alto),
                (15 * mm, alto),
                (ancho * 0.18, 151 * mm),
                (ancho * 0.18 - 15 * mm, 151 * mm),
            ],
            acento,
        )
        lienzo.setFillColor(acento)
        lienzo.rect(0, 148.8 * mm, ancho, 2.2 * mm, fill=1, stroke=0)
        lienzo.setStrokeColor(_tinte(primario, 0.18))
        lienzo.setLineWidth(0.55)
        for j in range(3):
            x = (13 + j * 5) * mm
            lienzo.line(x, 17 * mm, x, 44 * mm)
            lienzo.line(x, 44 * mm, x + 18 * mm, 44 * mm)
        _poligono(
            lienzo, [(ancho, 0), (ancho - 35 * mm, 0), (ancho, 35 * mm)], primario
        )
    elif modelo == "circuitos":
        lienzo.setStrokeColor(HexColor("#234656"))
        lienzo.setLineWidth(0.8)
        for j in range(14):
            x = (9 + j * 22) * mm
            p = lienzo.beginPath()
            p.moveTo(x, alto)
            p.lineTo(x, (193 - j % 3 * 6) * mm)
            p.lineTo(x + 8 * mm, (185 - j % 3 * 6) * mm)
            p.lineTo(x + 8 * mm, 152 * mm)
            lienzo.drawPath(p, stroke=1)
            lienzo.setFillColor(HexColor("#4BCAD0"))
            lienzo.circle(x + 8 * mm, 152 * mm, 1.1 * mm, fill=1, stroke=0)
        lienzo.setStrokeColor(HexColor("#245968"))
        lienzo.setLineWidth(0.55)
        for j in range(4):
            yy = (65 + j * 19) * mm
            lienzo.line(0, yy, 15 * mm, yy)
            lienzo.line(15 * mm, yy, 21 * mm, yy + 6 * mm)
            lienzo.line(ancho, yy, ancho - 15 * mm, yy)
            lienzo.line(ancho - 15 * mm, yy, ancho - 21 * mm, yy + 6 * mm)
        lienzo.setFillColor(acento)
        lienzo.rect(
            ancho / 2 - 15 * mm, 149.5 * mm, 30 * mm, 0.65 * mm, fill=1, stroke=0
        )
    elif modelo == "horizonte":
        if foto:
            _foto_pdf_v4(lienzo, foto, (0, 151 * mm, ancho, alto - 151 * mm), 0.9)
            lienzo.saveState()
            lienzo.setFillColor(primario)
            lienzo.setFillAlpha(0.64)
            lienzo.rect(0, 151 * mm, ancho, alto - 151 * mm, fill=1, stroke=0)
            lienzo.restoreState()
        lienzo.setFillColor(white)
        p = lienzo.beginPath()
        p.moveTo(0, 160 * mm)
        p.curveTo(95 * mm, 148 * mm, 201 * mm, 148 * mm, ancho, 160 * mm)
        p.lineTo(ancho, 140 * mm)
        p.lineTo(0, 140 * mm)
        p.close()
        lienzo.drawPath(p, fill=1, stroke=0)
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(1.3)
        p = lienzo.beginPath()
        p.moveTo(0, 160 * mm)
        p.curveTo(95 * mm, 148 * mm, 201 * mm, 148 * mm, ancho, 160 * mm)
        lienzo.drawPath(p, stroke=1)
        lienzo.setFillColor(primario)
        lienzo.rect(0, 0, ancho, 4 * mm, fill=1, stroke=0)
    elif modelo == "editorial":
        if foto:
            _foto_pdf_v4(lienzo, foto, (0, 151 * mm, 65 * mm, alto - 151 * mm), 0.6)
        lienzo.setFillColor(acento)
        lienzo.rect(65 * mm, 151 * mm, 1.5 * mm, alto - 151 * mm, fill=1, stroke=0)
        lienzo.setStrokeColor(_tinte(primario, 0.2))
        lienzo.setLineWidth(0.6)
        lienzo.line(22 * mm, 151 * mm, ancho - 22 * mm, 151 * mm)
        lienzo.setFillColor(primario)
        lienzo.rect(0, 0, 5 * mm, 151 * mm, fill=1, stroke=0)
        lienzo.setFillColor(acento)
        lienzo.rect(5 * mm, 0, 8 * mm, 3 * mm, fill=1, stroke=0)
    elif modelo == "academico":
        lienzo.setStrokeColor(_tinte(acento, 0.8))
        lienzo.setLineWidth(0.65)
        lienzo.rect(7 * mm, 7 * mm, ancho - 14 * mm, alto - 14 * mm, fill=0, stroke=1)
        lienzo.setFillColor(acento)
        lienzo.rect(0, 151 * mm, ancho, 1.5 * mm, fill=1, stroke=0)
        for s in (-1, 1):
            cx = ancho / 2 + s * 136 * mm
            _poligono(
                lienzo,
                [
                    (cx - 3 * mm, alto),
                    (cx + 3 * mm, alto),
                    (cx + 3 * mm, 151 * mm),
                    (cx, 154 * mm),
                    (cx - 3 * mm, 151 * mm),
                ],
                acento,
            )
        # Ornamento abstracto; no es un sello de acreditación ni representa a otra entidad.
        lienzo.setStrokeColor(_tinte(acento, 0.22))
        lienzo.setLineWidth(0.6)
        for r in (35, 37, 41):
            lienzo.circle(ancho / 2, 106 * mm, r * mm, stroke=1, fill=0)
    elif modelo == "inmersivo":
        if foto:
            _foto_pdf_v4(lienzo, foto, (0, 151 * mm, ancho, alto - 151 * mm), 0.4)
            lienzo.saveState()
            lienzo.setFillColor(noche)
            lienzo.setFillAlpha(0.55)
            lienzo.rect(0, 151 * mm, ancho, alto - 151 * mm, fill=1, stroke=0)
            lienzo.restoreState()
        lienzo.saveState()
        zona = lienzo.beginPath()
        zona.rect(0, 0, ancho, 8 * mm)
        zona.rect(0, 8 * mm, 19 * mm, 143 * mm)
        zona.rect(ancho - 19 * mm, 8 * mm, 19 * mm, 143 * mm)
        lienzo.clipPath(zona, stroke=0)
        for j in range(12):
            lienzo.setStrokeColor(HexColor("#27415A") if j % 3 else HexColor("#318B9B"))
            lienzo.setLineWidth(0.55)
            p = lienzo.beginPath()
            p.moveTo(0, (15 + j * 3) * mm)
            p.curveTo(
                75 * mm,
                (81 + j * 2) * mm,
                170 * mm,
                (-22 + j * 3) * mm,
                ancho,
                (50 + j * 3) * mm,
            )
            lienzo.drawPath(p, stroke=1)
        lienzo.restoreState()
        lienzo.saveState()
        zona = lienzo.beginPath()
        zona.rect(0, 151 * mm, ancho, alto - 151 * mm)
        lienzo.clipPath(zona, stroke=0)
        for j in range(4):
            lienzo.setStrokeColor(HexColor("#2B8391"))
            lienzo.setLineWidth(0.6)
            p = lienzo.beginPath()
            p.moveTo(0, (152 + j * 3) * mm)
            p.curveTo(
                92 * mm,
                (170 + j * 3) * mm,
                198 * mm,
                (130 + j * 3) * mm,
                ancho,
                (159 + j * 3) * mm,
            )
            lienzo.drawPath(p, stroke=1)
        lienzo.restoreState()
    return oscuro


def _logos_v4(lienzo, diseno, x, top, ancho, alto, oscuro):
    """Logos sin placa ni contenedor; sólo el logo institucional tiene variantes autorizadas."""
    from reportlab.lib.utils import ImageReader

    logos = [
        dict(logo) for logo in (diseno.get("logos") or [])[:4] if logo.get("imagen")
    ]
    for logo in logos:
        if logo.get("institucional"):
            variantes = logo.get("variantes") or {}
            logo["imagen"] = (
                variantes.get("oscuro" if oscuro else "claro") or logo["imagen"]
            )
    for logo, lx, ly, lw, lh in _cajas_logos(
        logos, x, top, ancho, alto, diseno.get("disposicion_logos", "auto")
    ):
        lienzo.drawImage(
            ImageReader(BytesIO(base64.b64decode(logo["imagen"]))),
            lx,
            ly,
            width=lw,
            height=lh,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )


def _firmas_v4(
    lienzo, certificado, diseno, x, top, ancho, tinta, acento, fuente, negrita, oscuro
):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    muted = HexColor("#C1D4DA") if oscuro else HexColor("#526660")
    qw = 25 * mm
    qx = x + ancho - qw
    qt = top - 2 * mm
    url = diseno.get("verificacion_url", "")
    lienzo.setFillColor(white)
    lienzo.rect(
        qx - 1.5 * mm, qt - qw - 1.5 * mm, qw + 3 * mm, qw + 3 * mm, fill=1, stroke=0
    )
    if url:
        qr = QrCodeWidget(url)
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(qw, qw, transform=[qw / (x2 - x1), 0, 0, qw / (y2 - y1), 0, 0])
        dibujo.add(qr)
        renderPDF.draw(dibujo, lienzo, qx, qt - qw)
        lienzo.linkURL(url, (qx, qt - qw, qx + qw, qt), relative=0, thickness=0)
    _texto_pdf(
        lienzo,
        "Verificar certificado",
        qx - 3 * mm,
        qt - qw - 2.5 * mm,
        qw + 6 * mm,
        4 * mm,
        muted,
        fuente,
        8.5,
        8.5,
    )
    _texto_pdf(
        lienzo,
        certificado.codigo,
        qx - 3 * mm,
        qt - qw - 6.5 * mm,
        qw + 6 * mm,
        4 * mm,
        tinta,
        negrita,
        8.5,
        8,
    )
    firmantes = list(diseno.get("firmantes") or [])[:3]
    espacio = ancho - qw - 12 * mm
    for i, firma in enumerate(firmantes):
        columna = espacio / len(firmantes)
        fx = x + i * columna + 2 * mm
        fw = columna - 4 * mm
        if firma.get("imagen"):
            lienzo.drawImage(
                ImageReader(BytesIO(base64.b64decode(firma["imagen"]))),
                fx + 3 * mm,
                top - 9 * mm,
                width=fw - 6 * mm,
                height=9 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        lienzo.setStrokeColor(HexColor("#69818D") if oscuro else _tinte(tinta, 0.45))
        lienzo.setLineWidth(0.5)
        lienzo.line(fx + 2 * mm, top - 10 * mm, fx + fw - 2 * mm, top - 10 * mm)
        caja = _texto_pdf(
            lienzo,
            firma.get("nombre", ""),
            fx,
            top - 11.2 * mm,
            fw,
            13.8 * mm,
            tinta,
            negrita,
            10,
            8.25,
            interlineado=1.12,
        )
        _texto_pdf(
            lienzo,
            firma.get("cargo", ""),
            fx,
            caja[1] - 1.5 * mm if caja else top - 12 * mm,
            fw,
            17.4 * mm,
            muted,
            fuente,
            9.5,
            8,
            interlineado=1.1,
        )



def _altura_texto_v4(texto, ancho, alto, fuente, tamano=12.5, minimo=10.5):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    while tamano >= minimo - 0.01:
        estilo = ParagraphStyle(
            "medicion-v4", fontName=fuente, fontSize=tamano, leading=tamano * 1.18
        )
        parrafo = Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilo)
        _, h = parrafo.wrap(ancho, alto)
        if h <= alto + 0.01:
            return h
        tamano -= 0.25
    return alto


def _contenido_v4(
    lienzo,
    diseno,
    x,
    top,
    ancho,
    alto,
    tinta,
    secundario,
    acento,
    fuente,
    negrita,
    oscuro,
    *,
    acento_texto=None,
):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import mm

    alineacion = diseno.get("alineacion_contenido", "centro")
    formato = diseno.get("formato_contenido", "institucional")
    texto = diseno.get("texto", "")
    if formato == "competencias" and diseno.get("competencias"):
        gap = 8 * mm
        izquierda = (ancho - gap) * 0.45
        derecha = ancho - gap - izquierda
        lienzo.setStrokeColor(HexColor("#365361") if oscuro else _tinte(tinta, 0.18))
        lienzo.setLineWidth(0.5)
        lienzo.line(x + izquierda + gap / 2, top, x + izquierda + gap / 2, top - alto)
        _texto_pdf(
            lienzo,
            texto,
            x,
            top,
            izquierda,
            alto,
            tinta,
            fuente,
            12,
            9.5,
            alineacion,
            1.1,
        )
        dx = x + izquierda + gap
        _texto_pdf(
            lienzo,
            "COMPETENCIAS Y LOGROS",
            dx,
            top,
            derecha,
            4.5 * mm,
            acento if acento_texto is None else acento_texto,
            negrita,
            9.5,
            9.5,
            "izquierda",
        )
        listado = "\n".join(
            "• " + str(linea) for linea in diseno.get("competencias", [])[:6]
        )
        _texto_pdf(
            lienzo,
            listado,
            dx,
            top - 6 * mm,
            derecha,
            alto - 6 * mm,
            tinta,
            fuente,
            11.5,
            9.5,
            "izquierda",
            1.03,
        )
    elif formato == "breve":
        _texto_pdf(
            lienzo,
            texto,
            x + 5 * mm,
            top - 2 * mm,
            ancho - 10 * mm,
            alto - 2 * mm,
            tinta,
            fuente,
            13.5,
            10.5,
            alineacion,
            1.2,
        )
    else:
        altura_bloque = min(
            alto,
            max(
                23 * mm,
                _altura_texto_v4(texto, ancho - 6 * mm, alto - 9 * mm, fuente)
                + 12 * mm,
            ),
        )
        techo = top - (alto - altura_bloque) / 2
        lienzo.setFillColor(HexColor("#102B39") if oscuro else _tinte(tinta, 0.035))
        lienzo.roundRect(
            x - 3 * mm,
            techo - altura_bloque - 1 * mm,
            ancho + 6 * mm,
            altura_bloque + 2 * mm,
            2 * mm,
            fill=1,
            stroke=0,
        )
        lienzo.setFillColor(acento)
        lienzo.rect(
            x - 3 * mm,
            techo - altura_bloque - 1 * mm,
            1 * mm,
            altura_bloque + 2 * mm,
            fill=1,
            stroke=0,
        )
        _texto_pdf(
            lienzo,
            "RECONOCIMIENTO DE LA ACTIVIDAD",
            x + 3 * mm,
            techo - 2 * mm,
            ancho - 6 * mm,
            4 * mm,
            secundario,
            negrita,
            9,
            9,
            alineacion,
        )
        _texto_pdf(
            lienzo,
            texto,
            x + 3 * mm,
            techo - 8 * mm,
            ancho - 6 * mm,
            altura_bloque - 9 * mm,
            tinta,
            fuente,
            12.5,
            10.5,
            alineacion,
            1.18,
        )


def _dibujar_certificado_v4(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V4:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_pdf()
    serif = modelo in ("clasico", "elegante", "academico")
    fuente_titulo = "Times-Roman" if serif else negrita
    cabecera_oscura = modelo in (
        "tecnologico",
        "congreso",
        "industrial",
        "circuitos",
        "horizonte",
        "inmersivo",
    )
    oscuro = _fondo_v4(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    tinta = HexColor("#F3F7F8") if oscuro else HexColor("#18392F")
    secundario = HexColor("#B6CAD2") if oscuro else HexColor("#546A63")
    cabecera_tinta = white if cabecera_oscura else primario
    x = 24 * mm
    w = ancho - 48 * mm
    hx = 75 * mm if modelo == "editorial" else x
    hw = ancho - hx - 24 * mm
    _logos_v4(lienzo, diseno, hx, 199 * mm, hw, 12.5 * mm, cabecera_oscura)
    _texto_pdf(
        lienzo,
        diseno.get("institucion", ""),
        hx,
        184.5 * mm,
        hw,
        4 * mm,
        cabecera_tinta,
        negrita,
        10,
        8.5,
        "centro",
    )
    _texto_pdf(
        lienzo,
        diseno.get("emisor", ""),
        hx,
        179.5 * mm,
        hw,
        4.5 * mm,
        cabecera_tinta,
        fuente,
        10,
        9,
        "centro",
    )
    _texto_pdf(
        lienzo,
        diseno.get("titulo", "CERTIFICADO"),
        hx,
        173.5 * mm,
        hw,
        15 * mm,
        cabecera_tinta,
        fuente_titulo,
        31 if serif else 27,
        18,
        "centro",
        1.08,
    )
    _texto_pdf(
        lienzo,
        diseno.get("subtitulo", ""),
        hx,
        157 * mm,
        hw,
        6 * mm,
        cabecera_tinta,
        fuente,
        10.5,
        9,
        "centro",
        1.1,
    )
    _texto_pdf(
        lienzo,
        diseno.get("entradilla", "Otorga el presente certificado a"),
        x,
        149 * mm,
        w,
        5 * mm,
        secundario,
        fuente,
        11,
        9.5,
        "centro",
    )
    _texto_pdf(
        lienzo,
        certificado.nombre,
        x,
        142 * mm,
        w,
        19 * mm,
        tinta,
        "Times-Bold" if serif else negrita,
        29 if serif else 27,
        14,
        "centro",
        1.05,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo,
            "Documento de identidad: " + certificado.documento,
            x,
            121 * mm,
            w,
            4 * mm,
            secundario,
            fuente,
            9,
            8.5,
            "centro",
        )
    _contenido_v4(
        lienzo,
        diseno,
        x,
        115 * mm,
        w,
        53 * mm,
        tinta,
        secundario,
        acento,
        fuente,
        negrita,
        oscuro,
    )
    _texto_pdf(
        lienzo,
        "Emisión: " + str(diseno.get("fecha_emision") or diseno.get("fecha", "")),
        x,
        60.5 * mm,
        w,
        4 * mm,
        secundario,
        fuente,
        8.5,
        8.5,
        "centro",
    )
    _firmas_v4(
        lienzo,
        certificado,
        diseno,
        x,
        54.5 * mm,
        w,
        tinta,
        acento,
        fuente,
        negrita,
        oscuro,
    )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo,
            "CERTIFICADO ANULADO",
            x,
            alto / 2 + 7 * mm,
            w,
            14 * mm,
            HexColor("#A62020"),
            negrita,
            25,
            22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


DISENOS_V5 = DISENOS_V4 + DISENOS_NUEVOS_V5


def _fondo_original_v5(diseno, modelo):
    preferencias = diseno.get("preferencias_fondo") or {}
    return (
        modelo in DISENOS_V4
        and preferencias.get("tema", "auto") == "auto"
        and preferencias.get("modo", "auto") == "auto"
        and diseno.get("intensidad_fondo", "media") == "media"
        and not diseno.get("imagen_fondo")
    )


def _imagen_encuadrada_v5(lienzo, imagen, caja, encuadre="centro", opacidad=0.3):
    from reportlab.lib.utils import ImageReader

    if not imagen:
        return
    lector = ImageReader(BytesIO(base64.b64decode(imagen)))
    iw, ih = lector.getSize()
    x, y, w, h = caja
    escala = max(w / iw, h / ih)
    dx = w - iw * escala
    dy = h - ih * escala
    ox = 0 if encuadre == "izquierda" else dx if encuadre == "derecha" else dx / 2
    oy = dy if encuadre == "superior" else 0 if encuadre == "inferior" else dy / 2
    lienzo.saveState()
    p = lienzo.beginPath()
    p.rect(x, y, w, h)
    lienzo.clipPath(p, stroke=0)
    lienzo.setFillAlpha(opacidad)
    lienzo.drawImage(
        lector, x + ox, y + oy, width=iw * escala, height=ih * escala, mask="auto"
    )
    lienzo.restoreState()


def _motivo_tecnologico_v5(lienzo, tema, caja, color, secundario, intensidad=1):
    """Ilustración vectorial propia, reproducible: no usa imágenes de stock ni emblemas."""
    from math import sin, cos, pi

    x, y, w, h = caja

    def xy(a, b):
        return x + a * w, y + b * h

    lienzo.saveState()
    lienzo.setStrokeColor(color)
    lienzo.setFillColor(color)
    lienzo.setStrokeAlpha(intensidad)
    lienzo.setFillAlpha(intensidad)
    lienzo.setLineWidth(0.65)
    if tema == "ia_datos":
        # Perfil humano de Bézier y nube determinista de partículas, sin malla repetitiva.
        p = lienzo.beginPath()
        p.moveTo(*xy(0.32, 0.03))
        p.lineTo(*xy(0.59, 0.03))
        p.curveTo(*xy(0.58, 0.11), *xy(0.58, 0.17), *xy(0.65, 0.20))
        p.curveTo(*xy(0.72, 0.21), *xy(0.77, 0.24), *xy(0.77, 0.29))
        p.curveTo(*xy(0.77, 0.31), *xy(0.73, 0.33), *xy(0.76, 0.35))
        p.curveTo(*xy(0.81, 0.36), *xy(0.83, 0.38), *xy(0.79, 0.40))
        p.curveTo(*xy(0.77, 0.41), *xy(0.77, 0.43), *xy(0.79, 0.44))
        p.curveTo(*xy(0.83, 0.44), *xy(0.88, 0.45), *xy(0.89, 0.47))
        p.curveTo(*xy(0.90, 0.49), *xy(0.85, 0.53), *xy(0.82, 0.57))
        p.curveTo(*xy(0.79, 0.61), *xy(0.80, 0.65), *xy(0.80, 0.69))
        p.curveTo(*xy(0.79, 0.87), *xy(0.67, 0.97), *xy(0.48, 0.97))
        p.curveTo(*xy(0.22, 0.98), *xy(0.10, 0.80), *xy(0.15, 0.59))
        p.curveTo(*xy(0.18, 0.47), *xy(0.27, 0.42), *xy(0.30, 0.32))
        p.curveTo(*xy(0.34, 0.23), *xy(0.34, 0.12), *xy(0.32, 0.03))
        p.close()
        lienzo.setStrokeAlpha(intensidad * 0.42)
        lienzo.setLineWidth(0.35)
        lienzo.drawPath(p, stroke=1, fill=0)
        lienzo.saveState()
        lienzo.clipPath(p, stroke=0)
        puntos = []
        for j in range(690):
            a = (j * 0.61803398875 + 0.13 * sin(j * 1.73)) % 1
            b = (j * 0.75487766625 + 0.09 * cos(j * 0.91)) % 1
            brillo = 0.25 + 0.75 * (0.5 + 0.5 * sin(j * 2.17))
            radio = 0.35 + 1.05 * (0.5 + 0.5 * cos(j * 1.41)) ** 3
            px, py = xy(a, b)
            puntos.append((px, py, brillo, radio))
        for j in range(0, len(puntos) - 29, 11):
            px, py, brillo, _ = puntos[j]
            vecinos = sorted(
                puntos[j + 1 : j + 29],
                key=lambda q: (q[0] - px) ** 2 + (q[1] - py) ** 2,
            )
            for qx, qy, _, _ in vecinos[:2]:
                lienzo.setStrokeAlpha(intensidad * (0.11 + 0.16 * brillo))
                lienzo.setLineWidth(0.25)
                lienzo.line(px, py, qx, qy)
        for j, (px, py, brillo, radio) in enumerate(puntos):
            if j % 37 == 0:
                lienzo.setFillAlpha(intensidad * 0.055)
                lienzo.circle(px, py, radio * 4.5, fill=1, stroke=0)
            lienzo.setFillAlpha(intensidad * (0.2 + 0.78 * brillo))
            lienzo.circle(px, py, radio, fill=1, stroke=0)
        lienzo.restoreState()
        lienzo.setStrokeColor(secundario)
        lienzo.setStrokeAlpha(intensidad * 0.42)
        for j in range(3):
            p = lienzo.beginPath()
            p.moveTo(*xy(0.01, 0.18 + j * 0.15))
            p.curveTo(
                *xy(0.18, 0.16 + j * 0.15),
                *xy(0.10, 0.35 + j * 0.13),
                *xy(0.27, 0.38 + j * 0.12),
            )
            lienzo.drawPath(p, stroke=1)
    elif tema == "robotica":
        pts = [
            xy(0.20, 0.08),
            xy(0.20, 0.24),
            xy(0.55, 0.51),
            xy(0.37, 0.78),
            xy(0.67, 0.91),
        ]
        lienzo.setLineWidth(max(2, w * 0.045))
        for a, b in zip(pts, pts[1:]):
            lienzo.line(*a, *b)
        lienzo.setLineWidth(0.8)
        for px, py in pts[1:]:
            lienzo.circle(px, py, w * 0.055, stroke=1, fill=0)
            lienzo.circle(px, py, w * 0.022, stroke=0, fill=1)
        lienzo.line(*xy(0.07, 0.07), *xy(0.36, 0.07))
        lienzo.line(*xy(0.07, 0.12), *xy(0.36, 0.12))
        lienzo.setLineWidth(1.5)
        lienzo.line(*xy(0.67, 0.91), *xy(0.81, 0.89))
        lienzo.line(*xy(0.81, 0.89), *xy(0.86, 0.77))
        lienzo.line(*xy(0.67, 0.91), *xy(0.68, 0.77))
        for j in range(4):
            px, py = xy(0.63 + j * 0.07, 0.26)
            lienzo.rect(px, py, w * 0.055, h * 0.08, stroke=1, fill=0)
    elif tema == "sostenibilidad":
        p = lienzo.beginPath()
        p.moveTo(*xy(0.17, 0.12))
        p.curveTo(*xy(0.09, 0.84), *xy(0.51, 0.98), *xy(0.90, 0.93))
        p.curveTo(*xy(0.90, 0.35), *xy(0.62, 0.10), *xy(0.17, 0.12))
        lienzo.drawPath(p, stroke=1)
        lienzo.line(*xy(0.17, 0.12), *xy(0.83, 0.86))
        for j in range(1, 7):
            a = 0.17 + j * 0.09
            b = 0.12 + j * 0.10
            lienzo.line(*xy(a, b), *xy(a - 0.11, b + 0.16))
            lienzo.line(*xy(a, b), *xy(a + 0.18, b - 0.04))
            lienzo.circle(*xy(a, b), w * 0.014, fill=1, stroke=0)
    else:
        puntos = [
            xy(0.5 + 0.41 * cos(i * pi / 6), 0.5 + 0.42 * sin(i * pi / 6))
            for i in range(12)
        ]
        puntos += [xy(0.5, 0.5), xy(0.34, 0.37), xy(0.65, 0.66), xy(0.31, 0.72)]
        for i, a in enumerate(puntos):
            for j, b in enumerate(puntos[i + 1 :], i + 1):
                if (i * 3 + j) % 4 == 0:
                    lienzo.setLineWidth(0.4)
                    lienzo.line(*a, *b)
            lienzo.circle(
                *a, w * (0.012 if i % 3 else 0.021), stroke=1, fill=i % 4 == 0
            )
        if tema == "investigacion":
            lienzo.setStrokeColor(secundario)
            lienzo.ellipse(
                x + w * 0.15, y + h * 0.15, x + w * 0.85, y + h * 0.85, stroke=1, fill=0
            )
            lienzo.ellipse(
                x + w * 0.31, y + h * 0.06, x + w * 0.69, y + h * 0.94, stroke=1, fill=0
            )
            lienzo.line(*xy(0.08, 0.5), *xy(0.92, 0.5))
    lienzo.restoreState()


def _fondo_v5(lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm

    if _fondo_original_v5(diseno, modelo):
        return _fondo_v4(
            lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
        )
    oscuro = diseno.get("modo_fondo") == "oscuro"
    base = HexColor("#071C30") if oscuro else HexColor("#FAFCFE")
    tinta = HexColor("#55C8E2") if oscuro else primario
    suave = HexColor("#809BB4") if oscuro else _tinte(primario, 0.14)
    fuerza = {"discreta": 0.32, "media": 0.62, "alta": 0.95}.get(
        diseno.get("intensidad_fondo"), 0.62
    )
    lienzo.setFillColor(base)
    lienzo.rect(0, 0, ancho, alto, fill=1, stroke=0)
    imagen = diseno.get("imagen_fondo", "")
    if imagen:
        _imagen_encuadrada_v5(
            lienzo,
            imagen,
            (0, 0, ancho, alto),
            diseno.get("encuadre_fondo", "centro"),
            0.16 + fuerza * 0.23,
        )
    elif diseno.get("foto") and modelo in DISENOS_NUEVOS_V5:
        foto_caja = (
            (0, 151 * mm, 86 * mm, alto - 151 * mm)
            if modelo == "ia_particulas"
            else (222 * mm, 151 * mm, 75 * mm, alto - 151 * mm)
            if modelo == "red_cientifica"
            else (0, 151 * mm, ancho, alto - 151 * mm)
        )
        _imagen_encuadrada_v5(lienzo, diseno["foto"], foto_caja, "centro", 0.16)
    if modelo == "ia_particulas":
        _poligono(
            lienzo,
            [(0, 0), (13 * mm, 0), (87 * mm, alto), (0, alto)],
            HexColor("#0D2942") if oscuro else _tinte(primario, 0.08),
        )
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "ia_datos"),
            (10 * mm, 151 * mm, 70 * mm, 55 * mm),
            tinta,
            acento,
            fuerza,
        )
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(1)
        lienzo.line(88 * mm, 155 * mm, 88 * mm, 200 * mm)
        for j in range(5):
            lienzo.setStrokeColor(suave)
            lienzo.setLineWidth(0.35)
            lienzo.line((6 + j * 3) * mm, 0, (80 + j * 3) * mm, 151 * mm)
    elif modelo == "red_cientifica":
        _poligono(
            lienzo,
            [
                (218 * mm, alto),
                (ancho, alto),
                (ancho, 0),
                (274 * mm, 0),
                (211 * mm, 151 * mm),
            ],
            HexColor("#0F3D60") if oscuro else _tinte(primario, 0.09),
        )
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "investigacion"),
            (220 * mm, 153 * mm, 73 * mm, 56 * mm),
            tinta,
            acento,
            fuerza,
        )
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.75)
        lienzo.line(216 * mm, 152 * mm, 243 * mm, 207 * mm)
        _motivo_tecnologico_v5(
            lienzo,
            "redes",
            (-20 * mm, 25 * mm, 95 * mm, 90 * mm),
            tinta,
            acento,
            fuerza * 0.18,
        )
    elif modelo == "poligonos_digitales":
        colores = [
            HexColor("#145271"),
            HexColor("#1D728C"),
            HexColor("#204D70"),
            HexColor("#365D83"),
        ]
        for j in range(7):
            yy = (j * 33 - 8) * mm
            lado = (22 + (j % 3) * 9) * mm
            _poligono(
                lienzo,
                [(0, yy), (lado, yy + 15 * mm), (0, yy + 38 * mm)],
                colores[j % 4] if oscuro else _tinte(colores[j % 4], 0.13),
            )
            _poligono(
                lienzo,
                [(ancho, yy), (ancho - lado, yy + 19 * mm), (ancho, yy + 41 * mm)],
                colores[(j + 1) % 4] if oscuro else _tinte(colores[(j + 1) % 4], 0.13),
            )
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.85)
        p = lienzo.beginPath()
        p.moveTo(16 * mm, alto - 9 * mm)
        p.lineTo(ancho - 22 * mm, alto - 9 * mm)
        p.lineTo(ancho - 9 * mm, alto - 22 * mm)
        p.lineTo(ancho - 9 * mm, 13 * mm)
        lienzo.drawPath(p, stroke=1)
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "redes"),
            (226 * mm, 157 * mm, 69 * mm, 52 * mm),
            tinta,
            acento,
            fuerza * 0.16,
        )
    else:
        # Ondas continuas con profundidad; también sirven al personalizar un modelo clásico.
        for j in range(16):
            color = acento if j % 4 == 0 else tinta
            lienzo.setStrokeColor(color)
            lienzo.setStrokeAlpha(fuerza * (0.7 if oscuro else 0.3))
            lienzo.setLineWidth(0.7 if j % 4 else 1.2)
            p = lienzo.beginPath()
            p.moveTo(0, (185 + j * 2) * mm)
            p.curveTo(
                83 * mm,
                (150 + j * 2) * mm,
                190 * mm,
                (245 - j) * mm,
                ancho,
                (180 + j * 2) * mm,
            )
            lienzo.drawPath(p, stroke=1)
        lienzo.setStrokeAlpha(1)
        _motivo_tecnologico_v5(
            lienzo,
            diseno.get("tema_fondo", "ia_datos"),
            (232 * mm, 20 * mm, 80 * mm, 80 * mm),
            tinta,
            acento,
            fuerza * 0.18,
        )
        for j in range(9):
            lienzo.setStrokeColor(tinta)
            lienzo.setStrokeAlpha(fuerza * 0.22)
            lienzo.setLineWidth(0.55)
            p = lienzo.beginPath()
            p.moveTo(0, (6 + j * 2) * mm)
            p.curveTo(
                76 * mm, (70 + j) * mm, 150 * mm, (-24 + j) * mm, ancho, (12 + j) * mm
            )
            lienzo.drawPath(p, stroke=1)
        lienzo.setStrokeAlpha(1)
    # Zonas sólidas de lectura: ningún fondo ni trama entra en nombres, descripción o firmas.
    lienzo.setFillColor(base)
    if modelo == "poligonos_digitales":
        _poligono(
            lienzo,
            [
                (21 * mm, 147 * mm),
                (ancho - 27 * mm, 147 * mm),
                (ancho - 21 * mm, 141 * mm),
                (ancho - 21 * mm, 54.5 * mm),
                (21 * mm, 54.5 * mm),
            ],
            base,
        )
        lienzo.setStrokeColor(acento)
        lienzo.setLineWidth(0.55)
        lienzo.line(21 * mm, 147 * mm, 21 * mm, 54.5 * mm)
        lienzo.line(21 * mm, 152 * mm, ancho - 27 * mm, 152 * mm)
    else:
        lienzo.rect(21 * mm, 54.5 * mm, ancho - 42 * mm, 93.5 * mm, fill=1, stroke=0)
    # La cabecera protege texto y logos, conservando el área artística reservada.
    hx = 94 * mm if modelo == "ia_particulas" else 24 * mm
    hw = (
        179 * mm
        if modelo == "ia_particulas"
        else 186 * mm
        if modelo == "red_cientifica"
        else ancho - 48 * mm
    )
    lienzo.saveState()
    lienzo.setFillColor(base)
    lienzo.setFillAlpha(0.96)
    lienzo.rect(hx - 2 * mm, 151 * mm, hw + 4 * mm, 52 * mm, fill=1, stroke=0)
    lienzo.restoreState()
    lienzo.setFillColor(white)
    lienzo.rect(0, 5.5 * mm, ancho, 49 * mm, fill=1, stroke=0)
    lienzo.setStrokeColor(acento)
    lienzo.setLineWidth(0.65)
    lienzo.line(24 * mm, 54.5 * mm, ancho - 24 * mm, 54.5 * mm)
    return oscuro


def _dibujar_certificado_v5(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V5:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_pdf()
    serif = modelo in ("clasico", "elegante", "academico")
    fuente_titulo = "Times-Roman" if serif else negrita
    cabecera_oscura = modelo in (
        "tecnologico",
        "congreso",
        "industrial",
        "circuitos",
        "horizonte",
        "inmersivo",
    )
    if not _fondo_original_v5(diseno, modelo):
        cabecera_oscura = diseno.get("modo_fondo") == "oscuro"
    oscuro = _fondo_v5(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    tinta = HexColor("#F3F7F8") if oscuro else HexColor("#163D5C")
    secundario = HexColor("#B6CAD2") if oscuro else HexColor("#546A63")
    cabecera_tinta = white if cabecera_oscura else primario
    x = 24 * mm
    w = ancho - 48 * mm
    hx = (
        94 * mm
        if modelo == "ia_particulas"
        else 75 * mm
        if modelo == "editorial"
        else x
    )
    hw = 186 * mm if modelo == "red_cientifica" else ancho - hx - 24 * mm
    _logos_v4(lienzo, diseno, hx, 199 * mm, hw, 12.5 * mm, cabecera_oscura)
    _texto_pdf(
        lienzo,
        diseno.get("institucion", ""),
        hx,
        184.5 * mm,
        hw,
        4 * mm,
        cabecera_tinta,
        negrita,
        10,
        8.5,
        "centro",
    )
    _texto_pdf(
        lienzo,
        diseno.get("emisor", ""),
        hx,
        179.5 * mm,
        hw,
        4.5 * mm,
        cabecera_tinta,
        fuente,
        10,
        9,
        "centro",
    )
    _texto_pdf(
        lienzo,
        diseno.get("titulo", "CERTIFICADO"),
        hx,
        173.5 * mm,
        hw,
        15 * mm,
        cabecera_tinta,
        fuente_titulo,
        31 if serif else 27,
        18,
        "centro",
        1.08,
    )
    _texto_pdf(
        lienzo,
        diseno.get("subtitulo", ""),
        hx,
        157 * mm,
        hw,
        6 * mm,
        cabecera_tinta,
        fuente,
        10.5,
        9,
        "centro",
        1.1,
    )
    _texto_pdf(
        lienzo,
        diseno.get("entradilla", "Otorga el presente certificado a"),
        x,
        149 * mm,
        w,
        5 * mm,
        secundario,
        fuente,
        11,
        9.5,
        "centro",
    )
    _texto_pdf(
        lienzo,
        certificado.nombre,
        x,
        142 * mm,
        w,
        19 * mm,
        tinta,
        "Times-Bold" if serif else negrita,
        29 if serif else 27,
        14,
        "centro",
        1.05,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo,
            "Documento de identidad: " + certificado.documento,
            x,
            121 * mm,
            w,
            4 * mm,
            secundario,
            fuente,
            9,
            8.5,
            "centro",
        )
    _contenido_v4(
        lienzo,
        diseno,
        x,
        115 * mm,
        w,
        53 * mm,
        tinta,
        secundario,
        acento if oscuro else primario,
        fuente,
        negrita,
        oscuro,
    )
    _texto_pdf(
        lienzo,
        "Emisión: " + str(diseno.get("fecha_emision") or diseno.get("fecha", "")),
        x,
        60.5 * mm,
        w,
        4 * mm,
        secundario,
        fuente,
        8.5,
        8.5,
        "centro",
    )
    firmas_oscuras = oscuro and _fondo_original_v5(diseno, modelo)
    tinta_firma = tinta if firmas_oscuras or not oscuro else HexColor("#163D5C")
    _firmas_v4(
        lienzo,
        certificado,
        diseno,
        x,
        52.5 * mm,
        w,
        tinta_firma,
        acento,
        fuente,
        negrita,
        firmas_oscuras,
    )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo,
            "CERTIFICADO ANULADO",
            x,
            alto / 2 + 7 * mm,
            w,
            14 * mm,
            HexColor("#A62020"),
            negrita,
            25,
            22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def _cabecera_v6(
    lienzo,
    diseno,
    hx,
    hw,
    cabecera_oscura,
    tinta,
    fuente,
    negrita,
    fuente_titulo,
    serif,
):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    institucional = diseno.get("logo_institucional") or {}
    aliados = list(diseno.get("logos_aliados") or [])[:4]
    imagen = (institucional.get("variantes") or {}).get(
        "oscuro" if cabecera_oscura else "claro"
    ) or institucional.get("imagen", "")
    extras = " · ".join(
        n
        for n in (institucional.get("facultad", ""), institucional.get("carrera", ""))
        if n
    )
    compacto = bool(aliados or extras)
    if aliados:
        if imagen:
            lienzo.drawImage(
                ImageReader(BytesIO(base64.b64decode(imagen))),
                hx,
                190 * mm,
                width=40 * mm,
                height=12 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        tx = hx + 45 * mm
        tw = hw - 45 * mm
        _texto_pdf(
            lienzo,
            institucional.get("nombre", diseno.get("institucion", "")),
            tx,
            203 * mm,
            tw,
            4 * mm,
            tinta,
            negrita,
            9.5,
            8,
            "centro",
            1.08,
        )
        _texto_pdf(
            lienzo,
            institucional.get("unidad", ""),
            tx,
            198 * mm,
            tw,
            4 * mm,
            tinta,
            fuente,
            9,
            8,
            "centro",
            1.08,
        )
        _texto_pdf(
            lienzo,
            extras,
            tx,
            193 * mm,
            tw,
            4 * mm,
            tinta,
            fuente,
            8,
            7,
            "centro",
            1.08,
        )
        for logo, lx, ly, lw, lh in _cajas_logos(
            aliados, hx, 188.5 * mm, hw, 8 * mm, diseno.get("disposicion_logos", "auto")
        ):
            archivo = (logo.get("variantes") or {}).get(
                "oscuro" if cabecera_oscura else "claro"
            ) or logo.get("imagen", "")
            if archivo:
                lienzo.drawImage(
                    ImageReader(BytesIO(base64.b64decode(archivo))),
                    lx,
                    ly,
                    width=lw,
                    height=lh,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
            _texto_pdf(
                lienzo,
                logo.get("nombre", ""),
                lx - 1 * mm,
                179.5 * mm,
                lw + 2 * mm,
                13 * mm,
                tinta,
                fuente,
                8.5,
                6.5,
                "centro",
                1.08,
            )
    else:
        if imagen:
            lienzo.drawImage(
                ImageReader(BytesIO(base64.b64decode(imagen))),
                hx,
                186.5 * mm,
                width=hw,
                height=12.5 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        _texto_pdf(
            lienzo,
            institucional.get("nombre", diseno.get("institucion", "")),
            hx,
            184.5 * mm,
            hw,
            4 * mm,
            tinta,
            negrita,
            10,
            8.5,
            "centro",
        )
        _texto_pdf(
            lienzo,
            institucional.get("unidad", ""),
            hx,
            179.5 * mm,
            hw,
            4.5 * mm,
            tinta,
            fuente,
            10,
            9,
            "centro",
        )
        if extras:
            _texto_pdf(
                lienzo,
                extras,
                hx,
                174.5 * mm,
                hw,
                5.5 * mm,
                tinta,
                fuente,
                8.5,
                7.5,
                "centro",
                1.08,
            )
    _texto_pdf(
        lienzo,
        diseno.get("titulo", "CERTIFICADO"),
        hx,
        (165.5 if compacto else 173.5) * mm,
        hw,
        (13 if compacto else 15) * mm,
        tinta,
        fuente_titulo,
        31 if serif else 27,
        18,
        "centro",
        1.08,
    )
    _texto_pdf(
        lienzo,
        diseno.get("subtitulo", ""),
        hx,
        (151.5 if compacto else 157) * mm,
        hw,
        (4 if compacto else 6) * mm,
        tinta,
        fuente,
        10.5,
        9,
        "centro",
        1.1,
    )
    return compacto


def _firmas_v6(lienzo, certificado, diseno, x, ancho, tinta, acento, fuente, negrita):
    """Firmas protagonistas y un bloque separado de verificación y emisión."""
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    muted = HexColor("#526660")
    top = 59.5 * mm
    qw = 25 * mm
    qx = x + ancho - qw
    qt = top - 2 * mm
    url = diseno.get("verificacion_url", "")
    lienzo.setFillColor(white)
    lienzo.rect(
        qx - 1.5 * mm, qt - qw - 1.5 * mm, qw + 3 * mm, qw + 3 * mm, fill=1, stroke=0
    )
    if url:
        qr = QrCodeWidget(url)
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(qw, qw, transform=[qw / (x2 - x1), 0, 0, qw / (y2 - y1), 0, 0])
        dibujo.add(qr)
        renderPDF.draw(dibujo, lienzo, qx, qt - qw)
        lienzo.linkURL(url, (qx, qt - qw, qx + qw, qt), relative=0, thickness=0)
    _texto_pdf(
        lienzo,
        "Verificar certificado",
        qx - 3 * mm,
        30.5 * mm,
        qw + 6 * mm,
        3.5 * mm,
        muted,
        fuente,
        8,
        7.5,
    )
    _texto_pdf(
        lienzo,
        certificado.codigo,
        qx - 3 * mm,
        26.5 * mm,
        qw + 6 * mm,
        4 * mm,
        tinta,
        negrita,
        8.5,
        8,
    )
    _texto_pdf(
        lienzo,
        "Emisión:\n" + str(diseno.get("fecha_emision") or diseno.get("fecha", "")),
        qx - 3 * mm,
        21 * mm,
        qw + 6 * mm,
        10 * mm,
        muted,
        fuente,
        7.5,
        7.5,
        "centro",
        1.15,
    )
    firmantes = list(diseno.get("firmantes") or [])[:3]
    espacio = ancho - qw - 12 * mm
    for i, firma in enumerate(firmantes):
        columna = espacio / len(firmantes)
        fx = x + i * columna + 2 * mm
        fw = columna - 4 * mm
        if firma.get("imagen"):
            iw = min(fw - 6 * mm, 70 * mm)
            lienzo.drawImage(
                ImageReader(BytesIO(base64.b64decode(firma["imagen"]))),
                fx + (fw - iw) / 2,
                top - 12.5 * mm,
                width=iw,
                height=12.5 * mm,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        lienzo.setStrokeColor(_tinte(tinta, 0.45))
        lienzo.setLineWidth(0.6)
        lienzo.line(fx + 2 * mm, 46 * mm, fx + fw - 2 * mm, 46 * mm)
        caja = _texto_pdf(
            lienzo,
            firma.get("nombre", ""),
            fx,
            44.5 * mm,
            fw,
            13.5 * mm,
            tinta,
            negrita,
            11.5,
            8.5,
            interlineado=1.1,
        )
        _texto_pdf(
            lienzo,
            firma.get("cargo", ""),
            fx,
            caja[1] - 1.5 * mm if caja else 43 * mm,
            fw,
            20.5 * mm,
            muted,
            fuente,
            10.25,
            8,
            interlineado=1.1,
        )


def _dibujar_certificado_moderno(
    certificado,
    diseno,
    mostrar_documento=True,
    vista_previa=False,
    *,
    fondo,
    cabecera,
    composicion_v7=False,
    composicion_v8=False,
):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V5:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_pdf()
    serif = modelo in ("clasico", "elegante", "academico")
    fuente_titulo = "Times-Roman" if serif else negrita
    cabecera_oscura = modelo in (
        "tecnologico",
        "congreso",
        "industrial",
        "circuitos",
        "horizonte",
        "inmersivo",
    )
    if not _fondo_original_v5(diseno, modelo):
        cabecera_oscura = diseno.get("modo_fondo") == "oscuro"
    if composicion_v7:
        _, cabecera_oscura, _, _ = _paleta_v7(diseno, modelo)
    oscuro = fondo(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    tinta = HexColor("#F3F7F8") if oscuro else HexColor("#163D5C")
    secundario = HexColor("#B6CAD2") if oscuro else HexColor("#546A63")
    cabecera_tinta = white if cabecera_oscura else primario
    if composicion_v8:
        cabecera_tinta = _color_texto_v8(cabecera_tinta, _paleta_v7(diseno, modelo)[3])
    x = 24 * mm
    w = ancho - 48 * mm
    hx = (
        94 * mm
        if modelo == "ia_particulas"
        else 75 * mm
        if modelo == "editorial"
        else x
    )
    hw = 186 * mm if modelo == "red_cientifica" else ancho - hx - 24 * mm
    institucion = diseno.get("logo_institucional") or {}
    requiere_compacto = bool(
        diseno.get("logos_aliados")
        or institucion.get("facultad")
        or institucion.get("carrera")
    )
    if requiere_compacto and not composicion_v8:
        if composicion_v7:
            _, _, _, color_franja = _paleta_v7(diseno, modelo)
        elif _fondo_original_v5(diseno, modelo):
            color_franja = (
                HexColor("#13142F" if modelo == "inmersivo" else "#081D2A")
                if oscuro
                else primario
                if cabecera_oscura
                else _tinte(primario, 0.035)
            )
        else:
            color_franja = HexColor("#071C30" if oscuro else "#FAFCFE")
        lienzo.setFillColor(color_franja)
        if modelo == "congreso" and (
            composicion_v7 or _fondo_original_v5(diseno, modelo)
        ):
            lienzo.rect(0, 147 * mm, ancho, 7.5 * mm, fill=1, stroke=0)
        else:
            lienzo.rect(hx - 2 * mm, 147 * mm, hw + 4 * mm, 7.5 * mm, fill=1, stroke=0)
        lienzo.rect(hx - 2 * mm, 189.5 * mm, hw + 4 * mm, 15 * mm, fill=1, stroke=0)
    compacto = cabecera(
        lienzo,
        diseno,
        hx,
        hw,
        cabecera_oscura,
        cabecera_tinta,
        fuente,
        negrita,
        fuente_titulo,
        serif,
    )
    lienzo.setFillColor(white)
    lienzo.rect(0, 5.5 * mm, ancho, 56 * mm, fill=1, stroke=0)
    _texto_pdf(
        lienzo,
        diseno.get("entradilla", "Otorga el presente certificado a"),
        x,
        (146 if compacto else 149) * mm,
        w,
        5 * mm,
        secundario,
        fuente,
        11,
        9.5,
        "centro",
    )
    _texto_pdf(
        lienzo,
        certificado.nombre,
        x,
        (139 if compacto else 142) * mm,
        w,
        19 * mm,
        tinta,
        "Times-Bold" if serif else negrita,
        29 if serif else 27,
        14,
        "centro",
        1.05,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo,
            "Documento de identidad: " + certificado.documento,
            x,
            (118 if compacto else 121) * mm,
            w,
            4 * mm,
            secundario,
            fuente,
            9,
            8.5,
            "centro",
        )
    _contenido_v4(
        lienzo,
        diseno,
        x,
        (112 if compacto else 115) * mm,
        w,
        (50 if compacto else 53) * mm,
        tinta,
        secundario,
        acento if oscuro else primario,
        fuente,
        negrita,
        oscuro,
        acento_texto=_color_texto_v8(
            acento if oscuro else primario, _paleta_v7(diseno, modelo)[2]
        )
        if composicion_v8
        else None,
    )
    _firmas_v6(
        lienzo, certificado, diseno, x, w, HexColor("#163D5C"), acento, fuente, negrita
    )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo,
            "CERTIFICADO ANULADO",
            x,
            alto / 2 + 7 * mm,
            w,
            14 * mm,
            HexColor("#A62020"),
            negrita,
            25,
            22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def _dibujar_certificado_v6(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    return _dibujar_certificado_moderno(
        certificado,
        diseno,
        mostrar_documento,
        vista_previa,
        fondo=_fondo_v5,
        cabecera=_cabecera_v6,
    )


def _dibujar_certificado_v7(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    return _dibujar_certificado_moderno(
        certificado,
        diseno,
        mostrar_documento,
        vista_previa,
        fondo=_fondo_v7,
        cabecera=_cabecera_v7,
        composicion_v7=True,
    )


def _dibujar_certificado_v8(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    return _dibujar_certificado_moderno(
        certificado,
        diseno,
        mostrar_documento,
        vista_previa,
        fondo=_fondo_v8,
        cabecera=_cabecera_v8,
        composicion_v7=True,
        composicion_v8=True,
    )


def _dibujar_certificado_v9(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    """Composición institucional V9; las versiones anteriores permanecen congeladas."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V5:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_pdf()
    serif = modelo in ("clasico", "elegante", "academico")
    fuente_titulo = "Times-Roman" if serif else negrita
    _, cabecera_oscura, base, fondo_cabecera = _paleta_v7(diseno, modelo)
    oscuro = _fondo_v9(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    tinta = HexColor("#F3F7F8") if oscuro else HexColor("#163D5C")
    secundario = HexColor("#B6CAD2") if oscuro else HexColor("#546A63")
    cabecera_tinta = _color_texto_v8(
        white if cabecera_oscura else primario, fondo_cabecera
    )
    x, w = 24 * mm, ancho - 48 * mm
    _cabecera_v9(
        lienzo, diseno, ancho, cabecera_tinta, fuente, negrita,
        fuente_titulo, serif, cabecera_oscura,
    )
    _texto_pdf(
        lienzo, diseno.get("subtitulo", ""), x, 146 * mm, w, 4 * mm,
        _color_texto_v8(tinta, base), fuente, 10.5, 9, "centro", 1.1,
    )
    lienzo.setFillColor(white)
    lienzo.rect(0, 5.5 * mm, ancho, 56 * mm, fill=1, stroke=0)
    _texto_pdf(
        lienzo, diseno.get("entradilla", "Otorga el presente certificado a"),
        x, 140 * mm, w, 5 * mm, secundario, fuente, 11, 9.5, "centro",
    )
    _texto_pdf(
        lienzo, certificado.nombre, x, 135 * mm, w, 14 * mm, tinta,
        "Times-Bold" if serif else negrita, 29 if serif else 27, 14, "centro", 1.05,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo, "Documento de identidad: " + certificado.documento,
            x, 119 * mm, w, 4 * mm, secundario, fuente, 9, 8.5, "centro",
        )
    _contenido_v4(
        lienzo, diseno, x, 112 * mm, w, 50 * mm, tinta, secundario,
        acento if oscuro else primario, fuente, negrita, oscuro,
        acento_texto=_color_texto_v8(acento if oscuro else primario, base),
    )
    _firmas_v6(
        lienzo, certificado, diseno, x, w, HexColor("#163D5C"), acento, fuente, negrita
    )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo, "CERTIFICADO ANULADO", x, alto / 2 + 7 * mm, w,
            14 * mm, HexColor("#A62020"), negrita, 25, 22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def _dibujar_certificado_v10(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    """Composición institucional V10; las versiones anteriores permanecen congeladas."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V5:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_pdf()
    serif = modelo in ("clasico", "elegante", "academico")
    fuente_titulo = "Times-Roman" if serif else negrita
    _, cabecera_oscura, base, fondo_cabecera = _paleta_v7(diseno, modelo)
    oscuro = _fondo_v9(
        lienzo, modelo, diseno, ancho, alto, primario, acento, cabecera_oscura
    )
    tinta = HexColor("#F3F7F8") if oscuro else HexColor("#163D5C")
    secundario = HexColor("#B6CAD2") if oscuro else HexColor("#546A63")
    cabecera_tinta = _color_texto_v8(
        white if cabecera_oscura else primario, fondo_cabecera
    )
    x, w = 24 * mm, ancho - 48 * mm
    _cabecera_v10(
        lienzo, diseno, ancho, cabecera_tinta, fuente, negrita,
        fuente_titulo, serif, cabecera_oscura,
    )
    _texto_pdf(
        lienzo, diseno.get("subtitulo", ""), x, 146 * mm, w, 4 * mm,
        _color_texto_v8(tinta, base), fuente, 10.5, 9, "centro", 1.1,
    )
    lienzo.setFillColor(white)
    lienzo.rect(0, 5.5 * mm, ancho, 56 * mm, fill=1, stroke=0)
    _texto_pdf(
        lienzo, diseno.get("entradilla", "Otorga el presente certificado a"),
        x, 140 * mm, w, 5 * mm, secundario, fuente, 11, 9.5, "centro",
    )
    _texto_pdf(
        lienzo, certificado.nombre, x, 135 * mm, w, 14 * mm, tinta,
        "Times-Bold" if serif else negrita, 29 if serif else 27, 14, "centro", 1.05,
    )
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo, "Documento de identidad: " + certificado.documento,
            x, 119 * mm, w, 4 * mm, secundario, fuente, 9, 8.5, "centro",
        )
    _contenido_v4(
        lienzo, diseno, x, 112 * mm, w, 50 * mm, tinta, secundario,
        acento if oscuro else primario, fuente, negrita, oscuro,
        acento_texto=_color_texto_v8(acento if oscuro else primario, base),
    )
    _firmas_v6(
        lienzo, certificado, diseno, x, w, HexColor("#163D5C"), acento, fuente, negrita
    )
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo, "CERTIFICADO ANULADO", x, alto / 2 + 7 * mm, w,
            14 * mm, HexColor("#A62020"), negrita, 25, 22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def _mezcla_v11(color, otro, cantidad):
    from reportlab.lib.colors import Color
    return Color(*(a * (1 - cantidad) + b * cantidad for a, b in zip(color.rgb(), otro.rgb())))


def _paleta_v11(diseno):
    """El modo oscuro deriva del color elegido, sin un azul fijo oculto."""
    from reportlab.lib.colors import HexColor, black, white
    primario = HexColor(diseno.get("primario") or "#006633")
    oscuro = diseno.get("modo_fondo") == "oscuro"
    base = _mezcla_v11(primario, black, 0.70) if oscuro else white
    return oscuro, base


def _tinta_v11(valor, defecto, fondo):
    from reportlab.lib.colors import HexColor, black, white
    def luminancia(color):
        canales = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in color.rgb()]
        return sum(a * b for a, b in zip(canales, (.2126, .7152, .0722)))
    def contraste(a, b):
        claros, oscuros = sorted((luminancia(a), luminancia(b)), reverse=True)
        return (claros + .05) / (oscuros + .05)
    color = HexColor(valor) if valor else defecto
    if contraste(color, fondo) >= 4.5:
        return color
    return white if contraste(white, fondo) > contraste(black, fondo) else black


def _fuentes_v11(diseno):
    """Poppins y Nunito incrustadas; la clásica utiliza la fuente serif estándar PDF."""
    from pathlib import Path
    from django.conf import settings
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if diseno.get("tipografia") == "clasica":
        return "Times-Roman", "Times-Bold"
    if diseno.get("tipografia") == "nunito":
        return _fuentes_pdf()
    carpeta = Path(settings.BASE_DIR) / 'apps' / 'portal' / 'static' / 'font' / 'institucional'
    for nombre, archivo in (("CertPoppins", "poppins-latin-400.ttf"), ("CertPoppinsBold", "poppins-latin-700.ttf")):
        if nombre not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nombre, str(carpeta / archivo)))
    return "CertPoppins", "CertPoppinsBold"


def _imagen_ambiental_v11(lienzo, imagen, caja, opacidad, *, encuadre="centro", zona_lectura=True):
    """Difumina la propia imagen; nunca añade una placa sobre fotos o logos."""
    from PIL import Image, ImageChops
    with Image.open(BytesIO(base64.b64decode(imagen))) as original:
        foto = original.convert("RGBA")
        foto.thumbnail((1600, 1100), Image.Resampling.LANCZOS)
        ancho, alto = foto.size
        alpha = Image.new("L", (ancho, 1))
        valores = []
        for x in range(ancho):
            distancia = min(x / max(1, ancho - 1), 1 - x / max(1, ancho - 1))
            borde = max(0, 1 - distancia / .28)
            fuerza = (.18 + .82 * borde ** 1.5) if zona_lectura else 1
            valores.append(round(255 * opacidad * fuerza))
        alpha.putdata(valores)
        alpha = alpha.resize(foto.size)
        foto.putalpha(ImageChops.multiply(foto.getchannel("A"), alpha))
        datos = BytesIO()
        foto.save(datos, "PNG")
    # Conserva el mismo encuadre del formulario y la relación de aspecto.
    _imagen_encuadrada_v5(lienzo, base64.b64encode(datos.getvalue()).decode("ascii"), caja, encuadre, 1)


def _fondo_v11(lienzo, modelo, diseno, ancho, alto, primario, acento):
    from reportlab.lib.colors import white
    from reportlab.lib.units import mm
    oscuro, base = _paleta_v11(diseno)
    lienzo.setFillColor(base)
    lienzo.rect(0, 0, ancho, alto, fill=1, stroke=0)
    fuerza = {"discreta": .35, "media": .65, "alta": 1}.get(diseno.get("intensidad_fondo"), .65)
    if diseno.get("imagen_fondo"):
        _imagen_ambiental_v11(lienzo, diseno["imagen_fondo"], (0, 61.5 * mm, ancho, alto - 61.5 * mm),
                             .28 + .32 * fuerza, encuadre=diseno.get("encuadre_fondo", "centro"))
    foto = diseno.get("foto")
    if foto and modelo in ("industrial", "editorial", "horizonte", "inmersivo"):
        if modelo == "editorial" and not diseno.get("logos_aliados"):
            caja = (0, 162 * mm, 68 * mm, alto - 162 * mm)
            _imagen_ambiental_v11(lienzo, foto, caja, .90, zona_lectura=False)
            lienzo.setFillColor(acento)
            lienzo.rect(68 * mm, 162 * mm, 1 * mm, alto - 162 * mm, fill=1, stroke=0)
        elif modelo == "industrial" and not diseno.get("logos_aliados"):
            caja = (222 * mm, 162 * mm, 75 * mm, alto - 162 * mm)
            _imagen_ambiental_v11(lienzo, foto, caja, .88, zona_lectura=False)
            lienzo.setFillColor(acento)
            lienzo.rect(221 * mm, 162 * mm, 1 * mm, alto - 162 * mm, fill=1, stroke=0)
        else:
            _imagen_ambiental_v11(lienzo, foto, (0, 162 * mm, ancho, alto - 162 * mm), .76)
    # Los motivos de cada modelo viven en los bordes; no se borran con rectángulos posteriores.
    class LienzoPaleta:
        def __getattr__(self, nombre):
            return getattr(lienzo, nombre)
        def color(self, valor):
            rgb = valor.rgb()
            if all(abs(a - b) < .005 for a, b in zip(rgb, primario.rgb())):
                return primario
            if all(abs(a - b) < .005 for a, b in zip(rgb, acento.rgb())):
                return acento
            if min(rgb) > .94 or max(rgb) < .20:
                return base
            if rgb[2] > rgb[0] and rgb[1] >= rgb[0]:
                return _mezcla_v11(primario, white, .35) if oscuro else _tinte(primario, .22)
            return valor
        def setFillColor(self, valor, *args, **kwargs):
            lienzo.setFillColor(self.color(valor), *args, **kwargs)
        def setStrokeColor(self, valor, *args, **kwargs):
            lienzo.setStrokeColor(self.color(valor), *args, **kwargs)
    lienzo.saveState()
    recorte = lienzo.beginPath()
    recorte.rect(0, 0, 22 * mm, alto)
    recorte.rect(ancho - 22 * mm, 0, 22 * mm, alto)
    recorte.rect(0, alto - 4 * mm, ancho, 4 * mm)
    recorte.rect(0, 0, ancho, 5.5 * mm)
    lienzo.clipPath(recorte, stroke=0)
    # No redibuja fondos sólidos ni fotografías: sólo conserva la geometría original.
    class Arte(LienzoPaleta):
        def rect(self, x, y, w, h, *args, **kwargs):
            if kwargs.get("fill") and w > ancho * .5 and h > 30 * mm:
                return
            return lienzo.rect(x, y, w, h, *args, **kwargs)
    decoracion = dict(diseno, foto="", imagen_fondo="")
    if modelo in DISENOS_NUEVOS_V5:
        _fondo_v5(Arte(), modelo, decoracion, ancho, alto, primario, acento, oscuro)
    else:
        _fondo_v4(Arte(), modelo, decoracion, ancho, alto, primario, acento, oscuro)
    lienzo.restoreState()
    lienzo.saveState()
    recorte = lienzo.beginPath()
    recorte.rect(0, 62 * mm, 20 * mm, 88 * mm)
    recorte.rect(ancho - 20 * mm, 62 * mm, 20 * mm, 88 * mm)
    lienzo.clipPath(recorte, stroke=0)
    _motivo_tecnologico_v5(lienzo, diseno.get("tema_fondo", "redes"),
                          (0, 65 * mm, ancho, 80 * mm), primario, acento, fuerza * .18)
    lienzo.restoreState()
    # Motivos completos y tenues: el perfil de IA y las conexiones no se recortan a una franja.
    if modelo in DISENOS_NUEVOS_V5:
        tema = {"ia_particulas": "ia_datos", "red_cientifica": "investigacion",
                "poligonos_digitales": "redes", "ondas_tecnologicas": "redes"}[modelo]
        caja = (0, 66 * mm, 72 * mm, 78 * mm) if modelo == "ia_particulas" else (224 * mm, 66 * mm, 73 * mm, 78 * mm)
        _motivo_tecnologico_v5(lienzo, tema, caja,
                              _mezcla_v11(primario, white, .6) if oscuro else primario,
                              acento, fuerza * (.16 if oscuro else .10))
    return oscuro, base


def _pie_tecnologico_v11(lienzo, diseno, ancho, primario, acento, fuente):
    """Ornamento vectorial opcional, separado de firmas y verificación."""
    from reportlab.lib.units import mm
    if not diseno.get("mostrar_pie_tecnologico"):
        return
    estilo = diseno.get("estilo_pie_tecnologico", "circuitos")
    textos = {"circuitos": "INNOVACIÓN · TECNOLOGÍA · CONEXIONES",
              "fabricacion": "DISEÑO · FABRICACIÓN DIGITAL · INNOVACIÓN",
              "calidad": "CALIDAD · CONOCIMIENTO · FORMACIÓN"}
    lienzo.saveState()
    lienzo.setStrokeColor(_tinte(primario, .38))
    lienzo.setFillColor(primario)
    lienzo.setLineWidth(.6)
    for lado, signo in ((24 * mm, 1), (232 * mm, -1)):
        for j in range(3):
            y = (8 + j * 1.3) * mm
            p = lienzo.beginPath()
            p.moveTo(lado, y)
            p.lineTo(lado + signo * 20 * mm, y)
            p.lineTo(lado + signo * 24 * mm, y + (j - 1) * 1.2 * mm)
            p.lineTo(lado + signo * 40 * mm, y + (j - 1) * 1.2 * mm)
            lienzo.drawPath(p, stroke=1)
            lienzo.circle(lado + signo * 40 * mm, y + (j - 1) * 1.2 * mm, .55 * mm, fill=1, stroke=0)
    if estilo != "circuitos":
        _motivo_tecnologico_v5(lienzo, "robotica" if estilo == "fabricacion" else "investigacion",
                              (59 * mm, 7 * mm, 8 * mm, 7 * mm), primario, acento, .65)
    _texto_pdf(lienzo, textos.get(estilo, textos["circuitos"]), 70 * mm, 11.8 * mm,
               116 * mm, 4 * mm, primario, fuente, 7, 6.5, "centro")
    lienzo.restoreState()


def _cabecera_v11(lienzo, diseno, ancho, tinta, fuente, negrita, fuente_titulo, serif, oscuro):
    """La institución protagoniza la cabecera y los colaboradores forman su propio bloque."""
    from reportlab.lib.units import mm

    x, top, alto = 24 * mm, 204 * mm, 43 * mm
    institucional = diseno.get("logo_institucional") or {}
    aliados = list(diseno.get("logos_aliados") or [])[:4]
    imagen = (institucional.get("variantes") or {}).get(
        "oscuro" if oscuro else "claro"
    ) or institucional.get("imagen", "")
    if aliados:
        ancho_principal = 133 * mm
        logo_ancho = 44 * mm
        texto_x = x + logo_ancho + 5 * mm if imagen else x
        texto_ancho = ancho_principal - (texto_x - x)
        parrafos, altura_texto, separacion = _parrafos_institucion_v10(
            institucional, diseno, texto_ancho, alto, fuente, negrita, tinta
        )
        texto_top = top - (alto - altura_texto) / 2
        if imagen:
            logo_alto = 26 * mm
            _imagen_cabecera_v9(
                lienzo, institucional, x, top - (alto + logo_alto) / 2,
                logo_ancho, logo_alto, oscuro,
            )
        lienzo.saveState()
        lienzo.setStrokeColor(tinta)
        lienzo.setStrokeAlpha(0.18)
        lienzo.setLineWidth(0.5)
        lienzo.line(161 * mm, 161 * mm, 161 * mm, 202 * mm)
        lienzo.restoreState()
        _colaboradores_v10(
            lienzo, diseno, 165 * mm, 203 * mm, ancho - 189 * mm,
            43 * mm, oscuro, tinta, fuente, negrita,
        )
    else:
        texto_x, texto_ancho = x, ancho - 48 * mm
        if diseno.get("foto") and diseno.get("diseno") == "editorial":
            texto_x, texto_ancho = 76 * mm, ancho - 88 * mm
        elif diseno.get("foto") and diseno.get("diseno") == "industrial":
            texto_x, texto_ancho = 16 * mm, 198 * mm
        parrafos, altura_texto, separacion = _parrafos_institucion_v10(
            institucional, diseno, texto_ancho,
            alto - 13.5 * mm if imagen else alto, fuente, negrita, tinta,
            centrado=True,
        )
        espacio_logo = 1.5 * mm if imagen else 0
        logo_alto = min(18 * mm, alto - altura_texto - espacio_logo) if imagen else 0
        bloque_top = top - (alto - altura_texto - espacio_logo - logo_alto) / 2
        if imagen:
            _imagen_cabecera_v9(
                lienzo, institucional, texto_x + (texto_ancho - 60 * mm) / 2,
                bloque_top - logo_alto, 60 * mm, logo_alto, oscuro,
            )
        texto_top = bloque_top - logo_alto - espacio_logo
    for parrafo, altura in parrafos:
        parrafo.drawOn(lienzo, texto_x, texto_top - altura)
        texto_top -= altura + separacion
    _texto_pdf(
        lienzo, diseno.get("titulo", "CERTIFICADO"), x, 159 * mm,
        ancho - 48 * mm, 12 * mm, tinta, fuente_titulo,
        31 if serif else 27, 18, "centro", 1.08,
    )



def _dibujar_certificado_v11(
    certificado, diseno, mostrar_documento=True, vista_previa=False
):
    """Composición institucional V11; las versiones anteriores permanecen congeladas."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in DISENOS_V5:
        modelo = "clasico"
    primario = HexColor(diseno.get("primario", "#1E5A3D"))
    acento = HexColor(diseno.get("acento", "#E1B93F"))
    fuente, negrita = _fuentes_v11(diseno)
    serif = diseno.get("tipografia") == "clasica"
    fuente_titulo = "Times-Roman" if serif else negrita
    oscuro, base = _fondo_v11(lienzo, modelo, diseno, ancho, alto, primario, acento)
    tinta = _tinta_v11(diseno.get("color_texto"), white if oscuro else HexColor("#263D33"), base)
    titulos = _tinta_v11(diseno.get("color_titulos"), white if oscuro else primario, base)
    secundario = _tinta_v11(diseno.get("color_texto"), HexColor("#C5D8CF") if oscuro else HexColor("#52665A"), base)
    cabecera_tinta = titulos
    cabecera_oscura = oscuro
    x, w = 24 * mm, ancho - 48 * mm
    _cabecera_v11(
        lienzo, diseno, ancho, cabecera_tinta, fuente, negrita,
        fuente_titulo, serif, cabecera_oscura,
    )
    _texto_pdf(
        lienzo, diseno.get("subtitulo", ""), x, 146 * mm, w, 4 * mm,
        titulos, fuente, 10.5, 9, "centro", 1.1,
    )
    lienzo.setFillColor(white)
    lienzo.rect(0, 5.5 * mm, ancho, 56 * mm, fill=1, stroke=0)
    _texto_pdf(
        lienzo, diseno.get("entradilla", "Otorga el presente certificado a"),
        x, 140 * mm, w, 5 * mm, secundario, fuente, 11, 9.5, "centro",
    )
    nombre_caja = _texto_pdf(
        lienzo, certificado.nombre, x, 135 * mm, w, 18 * mm, titulos,
        "Times-Bold" if serif else negrita, 29 if serif else 27, 14, "centro", 1.05,
    )
    documento_top = min(119 * mm, (nombre_caja[1] if nombre_caja else 121 * mm) - 1.5 * mm)
    contenido_top = min(112 * mm, documento_top - 6 * mm)
    if mostrar_documento and getattr(certificado, "documento", ""):
        _texto_pdf(
            lienzo, "Documento de identidad: " + certificado.documento,
            x, documento_top, w, 4 * mm, secundario, fuente, 9, 8.5, "centro",
        )
    _contenido_v4(
        lienzo, diseno, x, contenido_top, w, contenido_top - 62 * mm, tinta, secundario,
        acento if oscuro else primario, fuente, negrita, oscuro,
        acento_texto=titulos,
    )
    _firmas_v6(
        lienzo, certificado, diseno, x, w, _tinta_v11(diseno.get("color_texto"), primario, white), acento, fuente, negrita
    )
    _pie_tecnologico_v11(lienzo, diseno, ancho, primario, acento, fuente)
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(0.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        _texto_pdf(
            lienzo, "CERTIFICADO ANULADO", x, alto / 2 + 7 * mm, w,
            14 * mm, HexColor("#A62020"), negrita, 25, 22,
        )
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(
            ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ"
        )
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()


def dibujar_certificado(certificado, mostrar_documento=True, vista_previa=False):
    """Los snapshots sin versión o versión 1 conservan exactamente su composición histórica."""
    diseno = getattr(certificado, 'diseno_certificado', None) or {}
    if diseno.get('version', 1) < 2:
        return _dibujar_certificado_v1(certificado, mostrar_documento, vista_previa)
    if diseno.get('version') == 2:
        return _dibujar_certificado_v2(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 3:
        return _dibujar_certificado_v3(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 4:
        return _dibujar_certificado_v4(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 5:
        return _dibujar_certificado_v5(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 6:
        return _dibujar_certificado_v6(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 7:
        return _dibujar_certificado_v7(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 8:
        return _dibujar_certificado_v8(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 9:
        return _dibujar_certificado_v9(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 10:
        return _dibujar_certificado_v10(certificado, diseno, mostrar_documento, vista_previa)
    if diseno.get('version') == 11:
        return _dibujar_certificado_v11(certificado, diseno, mostrar_documento, vista_previa)
    from apps.formacion.presentation.certificados_composicion import dibujar_certificado_v12
    return dibujar_certificado_v12(certificado, diseno, mostrar_documento, vista_previa)
