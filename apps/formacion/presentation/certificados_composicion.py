"""Composición V12: papel blanco, ornamentos de borde y formación lateral.

Los snapshots anteriores se dibujan en certificados_diseno sin modificaciones.
"""
import base64
from io import BytesIO

from django.core.exceptions import ValidationError
from django.utils.html import escape
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


def _fondo(lienzo, modelo, diseno, ancho, alto, primario, acento):
    from apps.formacion.presentation import certificados_diseno as base

    # También protege snapshots V12 recibidos de clientes antiguos con modo oscuro.
    decoracion = dict(diseno, modo_fondo="claro", imagen_fondo="")
    if diseno.get("logos_aliados"):
        decoracion["foto"] = ""
    base._fondo_v11(lienzo, modelo, decoracion, ancho, alto, primario, acento)
    if diseno.get("imagen_fondo"):
        fuerza = {"discreta": .35, "media": .65, "alta": 1}.get(diseno.get("intensidad_fondo"), .65)
        base._imagen_ambiental_v11(lienzo, diseno["imagen_fondo"],
                                   (0, 61.5 * mm, ancho, alto - 61.5 * mm), .16 + .06 * fuerza,
                                   encuadre=diseno.get("encuadre_fondo", "centro"))
    if diseno.get("logos_aliados") and diseno.get("foto") and modelo in ("industrial", "editorial", "horizonte", "inmersivo"):
        # La fotografía tiene un espacio propio fuera de los logos y los nombres.
        base._imagen_ambiental_v11(lienzo, diseno["foto"],
                                   (0, 162 * mm, 20 * mm, alto - 162 * mm), .88, zona_lectura=False)
    if modelo in ("tecnologico", "circuitos", "inmersivo", "ia_particulas", "poligonos_digitales"):
        base._poligono(lienzo, [(0, 65 * mm), (7 * mm, 76 * mm),
                               (7 * mm, alto), (0, alto)], primario)
        base._poligono(lienzo, [(ancho, 0), (ancho - 7 * mm, 0),
                               (ancho - 7 * mm, 45 * mm), (ancho, 61 * mm)], primario)
        lienzo.setFillColor(acento)
        lienzo.rect(7 * mm, alto - 28 * mm, 1 * mm, 25 * mm, fill=1, stroke=0)


def _verificacion_lateral(lienzo, certificado, diseno, fuente, negrita, tinta):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from apps.formacion.presentation import certificados_diseno as base

    x, top, lado = 25 * mm, 60 * mm, 28 * mm
    lienzo.setFillColor(white)
    lienzo.roundRect(x - mm, top - lado - mm, lado + 2 * mm, lado + 2 * mm,
                     1 * mm, fill=1, stroke=0)
    url = diseno.get("verificacion_url", "")
    if url:
        qr = QrCodeWidget(url)
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(lado, lado, transform=[lado / (x2 - x1), 0, 0, lado / (y2 - y1), 0, 0])
        dibujo.add(qr)
        renderPDF.draw(dibujo, lienzo, x, top - lado)
        lienzo.linkURL(url, (x, top - lado, x + lado, top), relative=0, thickness=0)
    for texto, techo, altura, tipo, tamano in (
        ("Verificar certificado", 29, 4, fuente, 8),
        (certificado.codigo, 24, 4, negrita, 8.5),
        ("Emisión: " + str(diseno.get("fecha_emision") or diseno.get("fecha", "")), 18, 10, fuente, 7.5),
    ):
        base._texto_pdf(lienzo, texto, 8 * mm, techo * mm, 62 * mm, altura * mm,
                        tinta, tipo, tamano, tamano, "centro", 1.1)


def _firmas_laterales(lienzo, diseno, tinta, fuente, negrita):
    from reportlab.lib.utils import ImageReader
    from apps.formacion.presentation import certificados_diseno as base

    firmas = list(diseno.get("firmantes") or [])[:3]
    for i, firma in enumerate(firmas):
        columna = 183 * mm / len(firmas)
        x, w = 95 * mm + i * columna + 2 * mm, columna - 4 * mm
        if firma.get("imagen"):
            iw = min(w - 4 * mm, 65 * mm)
            lienzo.drawImage(ImageReader(BytesIO(base64.b64decode(firma["imagen"]))),
                              x + (w - iw) / 2, 47 * mm, width=iw, height=13 * mm,
                              preserveAspectRatio=True, anchor="c", mask="auto")
        lienzo.setStrokeColor(base._tinte(tinta, .4))
        lienzo.setLineWidth(.6)
        lienzo.line(x + mm, 46 * mm, x + w - mm, 46 * mm)
        caja = base._texto_pdf(lienzo, firma.get("nombre", ""), x, 44.5 * mm, w,
                               13.5 * mm, tinta, negrita, 10.5, 8.5, interlineado=1.1)
        base._texto_pdf(lienzo, firma.get("cargo", ""), x,
                        caja[1] - 1.5 * mm if caja else 43 * mm,
                        w, 20.5 * mm, HexColor("#526660"), fuente, 9.5, 8, interlineado=1.1)


def _contenido_lateral(lienzo, diseno, x, top, ancho, alto, tinta, fuente, negrita):
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    contenido = escape(str(diseno.get("texto", ""))).replace("\n", "<br/>")
    if diseno.get("formato_contenido") == "competencias" and diseno.get("competencias"):
        contenido += '<br/><br/><font name="' + negrita + '">COMPETENCIAS Y LOGROS</font><br/>'
        contenido += "<br/>".join(str(i) + ". " + escape(str(texto))
                                  for i, texto in enumerate(diseno["competencias"][:6], 1))
    tamano = 12
    while tamano >= 8.5:
        estilo = ParagraphStyle("formacion-lateral", fontName=fuente, fontSize=tamano,
                                leading=tamano * 1.13, textColor=tinta, alignment=TA_LEFT,
                                splitLongWords=True, allowWidows=0, allowOrphans=0)
        parrafo = Paragraph(contenido, estilo)
        _, h = parrafo.wrap(ancho, alto)
        if h <= alto + .01:
            parrafo.drawOn(lienzo, x, top - h)
            return
        tamano -= .25
    raise ValidationError("El contenido no cabe en el formato lateral. Acorte el texto o las competencias para conservar su lectura.")


def _lateral(lienzo, certificado, diseno, ancho, alto, primario, acento, tinta, titulos,
             fuente, negrita, mostrar_documento):
    from apps.formacion.presentation import certificados_diseno as base

    lienzo.setFillColor(white)
    lienzo.rect(0, 0, ancho, alto, fill=1, stroke=0)
    # Una sola banda lateral. La zona académica y todas las firmas son blancas.
    base._poligono(lienzo, [(0, 0), (78 * mm, 13 * mm), (78 * mm, alto), (0, alto)], primario)
    lienzo.setFillColor(acento)
    lienzo.rect(78 * mm, 13 * mm, 1.2 * mm, alto - 13 * mm, fill=1, stroke=0)
    base._motivo_tecnologico_v5(lienzo, diseno.get("tema_fondo", "redes"),
                               (0, 67 * mm, 78 * mm, 65 * mm), white, acento, .18)
    tinta_lateral = base._tinta_v11("", white, primario)
    oscuro_lateral = tinta_lateral == white
    institucional = diseno.get("logo_institucional") or {}
    base._imagen_cabecera_v9(lienzo, institucional, 9 * mm, 180 * mm, 60 * mm, 23 * mm, oscuro_lateral)
    base._texto_pdf(lienzo, institucional.get("nombre") or diseno.get("institucion", ""),
                    8 * mm, 172 * mm, 62 * mm, 22 * mm, tinta_lateral, negrita, 12, 10, "centro", 1.1)
    base._texto_pdf(lienzo, institucional.get("unidad") or diseno.get("emisor", ""),
                    8 * mm, 147 * mm, 62 * mm, 23 * mm, tinta_lateral, negrita, 11, 9.5, "centro", 1.1)
    dependencias = "\n".join(institucional.get(k, "") for k in ("facultad", "carrera") if institucional.get(k))
    caja_dependencias = base._texto_pdf(lienzo, dependencias, 8 * mm, 119 * mm, 62 * mm, 39 * mm,
                    tinta_lateral, fuente, 9, 8, "centro", 1.1)
    if diseno.get("imagen_fondo") or diseno.get("foto"):
        foto_top = min(115 * mm, (caja_dependencias[1] if caja_dependencias else 119 * mm) - 4 * mm)
        base._imagen_ambiental_v11(lienzo, diseno.get("imagen_fondo") or diseno["foto"],
                                   (0, 67 * mm, 78 * mm, foto_top - 67 * mm), .65,
                                   encuadre=diseno.get("encuadre_fondo", "centro"), zona_lectura=False)
    _verificacion_lateral(lienzo, certificado, diseno, fuente, negrita, tinta_lateral)
    x, w = 95 * mm, 183 * mm
    base._texto_pdf(lienzo, institucional.get("nombre") or diseno.get("institucion", ""),
                    x, 207 * mm, w, 13 * mm, titulos, negrita, 14, 12, "centro", 1.1)
    aliados = diseno.get("logos_aliados") or []
    if aliados:
        base._colaboradores_v10(lienzo, diseno, x, 190 * mm, w, 32 * mm,
                                False, titulos, fuente, negrita)
    else:
        base._texto_pdf(lienzo, institucional.get("unidad", ""), x, 184 * mm, w,
                        13 * mm, titulos, fuente, 11, 10, "centro", 1.1)
    techo = 155 if aliados else 164
    base._texto_pdf(lienzo, diseno.get("titulo", "CERTIFICADO"), x, techo * mm, w,
                    15 * mm, titulos, negrita, 24, 17, "centro", 1.05)
    base._texto_pdf(lienzo, diseno.get("subtitulo", ""), x, (techo - 16) * mm, w,
                    4 * mm, titulos, fuente, 9, 8, "centro")
    base._texto_pdf(lienzo, diseno.get("entradilla", "Otorga el presente certificado a"),
                    x, (techo - 22) * mm, w, 5 * mm, tinta, fuente, 10, 9, "centro")
    nombre = base._texto_pdf(lienzo, certificado.nombre, x, (techo - 28) * mm, w,
                             21 * mm, titulos, negrita, 24, 12, "centro", 1.06)
    contenido_top = (techo - 51) * mm
    if mostrar_documento and getattr(certificado, "documento", ""):
        documento_top = min(contenido_top, nombre[1] - mm if nombre else contenido_top)
        base._texto_pdf(lienzo, "Documento de identidad: " + certificado.documento,
                        x, documento_top, w, 4 * mm, tinta, fuente, 8, 8, "centro")
        contenido_top = documento_top - 5 * mm
    _contenido_lateral(lienzo, diseno, x, contenido_top, w, contenido_top - 62 * mm,
                       tinta, fuente, negrita)
    _firmas_laterales(lienzo, diseno, tinta, fuente, negrita)
    if diseno.get("mostrar_pie_tecnologico"):
        estilo = diseno.get("estilo_pie_tecnologico", "circuitos")
        etiquetas = {"circuitos": "INNOVACIÓN · TECNOLOGÍA · CONEXIONES",
                     "fabricacion": "DISEÑO · FABRICACIÓN DIGITAL · INNOVACIÓN",
                     "calidad": "CALIDAD · CONOCIMIENTO · FORMACIÓN"}
        lienzo.saveState()
        lienzo.setStrokeColor(base._tinte(primario, .38))
        lienzo.setFillColor(primario)
        lienzo.setLineWidth(.6)
        for inicio, signo in ((96 * mm, 1), (277 * mm, -1)):
            for j in range(3):
                y = (8 + j * 1.3) * mm
                lienzo.line(inicio, y, inicio + signo * 22 * mm, y)
                lienzo.circle(inicio + signo * 22 * mm, y, .5 * mm, fill=1, stroke=0)
        if estilo != "circuitos":
            base._motivo_tecnologico_v5(lienzo, "robotica" if estilo == "fabricacion" else "investigacion",
                                        (120 * mm, 7 * mm, 7 * mm, 7 * mm), primario, acento, .65)
        base._texto_pdf(lienzo, etiquetas.get(estilo, etiquetas["circuitos"]),
                        130 * mm, 11.8 * mm, 117 * mm, 4 * mm, primario, fuente, 7, 7, "centro")
        lienzo.restoreState()


def dibujar_certificado_v12(certificado, diseno, mostrar_documento=True, vista_previa=False):
    from apps.formacion.presentation import certificados_diseno as base

    salida = BytesIO()
    ancho, alto = landscape(A4)
    lienzo = Canvas(salida, pagesize=(ancho, alto), pageCompression=1)
    lienzo.setTitle(diseno.get("titulo", "Certificado"))
    lienzo.setAuthor(diseno.get("institucion", ""))
    lienzo.setSubject("Certificado verificable de actividad académica")
    modelo = diseno.get("diseno", "clasico")
    if modelo not in (*base.DISENOS_V5, "formacion_lateral"):
        modelo = "clasico"
    primario = HexColor(diseno.get("primario") or "#006633")
    acento = HexColor(diseno.get("acento") or "#FFCE00")
    fuente, negrita = base._fuentes_v11(diseno)
    tinta = base._tinta_v11(diseno.get("color_texto"), HexColor("#263D33"), white)
    titulos = base._tinta_v11(diseno.get("color_titulos"), primario, white)
    secundario = base._tinta_v11(diseno.get("color_texto"), HexColor("#52665A"), white)
    x, w = 24 * mm, ancho - 48 * mm
    if modelo == "formacion_lateral":
        _lateral(lienzo, certificado, diseno, ancho, alto, primario, acento,
                 tinta, titulos, fuente, negrita, mostrar_documento)
    else:
        _fondo(lienzo, modelo, diseno, ancho, alto, primario, acento)
        serif = diseno.get("tipografia") == "clasica"
        base._cabecera_v11(lienzo, diseno, ancho, titulos, fuente, negrita,
                           "Times-Roman" if serif else negrita, serif, False)
        base._texto_pdf(lienzo, diseno.get("subtitulo", ""), x, 146 * mm, w, 4 * mm,
                        titulos, fuente, 10.5, 9, "centro", 1.1)
        base._texto_pdf(lienzo, diseno.get("entradilla", "Otorga el presente certificado a"),
                        x, 140 * mm, w, 5 * mm, secundario, fuente, 11, 9.5, "centro")
        nombre = base._texto_pdf(lienzo, certificado.nombre, x, 135 * mm, w, 18 * mm,
                                 titulos, "Times-Bold" if serif else negrita,
                                 29 if serif else 27, 14, "centro", 1.05)
        documento_top = min(119 * mm, (nombre[1] if nombre else 121 * mm) - 1.5 * mm)
        contenido_top = min(112 * mm, documento_top - 6 * mm)
        if mostrar_documento and getattr(certificado, "documento", ""):
            base._texto_pdf(lienzo, "Documento de identidad: " + certificado.documento,
                            x, documento_top, w, 4 * mm, secundario, fuente, 9, 8.5, "centro")
        base._contenido_v4(lienzo, diseno, x, contenido_top, w, contenido_top - 62 * mm,
                           tinta, secundario, primario, fuente, negrita, False, acento_texto=titulos)
        base._firmas_v6(lienzo, certificado, diseno, x, w,
                        base._tinta_v11(diseno.get("color_texto"), primario, white), acento, fuente, negrita)
        base._pie_tecnologico_v11(lienzo, diseno, ancho, primario, acento, fuente)
    if getattr(certificado, "anulado", False):
        lienzo.saveState()
        lienzo.setFillColor(white)
        lienzo.setFillAlpha(.93)
        lienzo.rect(0, alto / 2 - 12 * mm, ancho, 24 * mm, fill=1, stroke=0)
        lienzo.restoreState()
        base._texto_pdf(lienzo, "CERTIFICADO ANULADO", x, alto / 2 + 7 * mm, w,
                        14 * mm, HexColor("#A62020"), negrita, 25, 22)
    elif vista_previa:
        lienzo.setFillColor(white)
        lienzo.rect(0, 0, ancho, 5.5 * mm, fill=1, stroke=0)
        lienzo.setFillColor(HexColor("#9B2424"))
        lienzo.setFont(negrita, 7)
        lienzo.drawCentredString(ancho / 2, 3 * mm, "VISTA PREVIA - DATOS FICTICIOS - SIN VALIDEZ")
    lienzo.showPage()
    lienzo.save()
    return salida.getvalue()
