"""El reporte institucional de un Centro I+D en PDF: identidad, organización, servicios, áreas, fases, presupuesto,
indicadores, riesgos y articulación, armado en el momento con lo que el centro tiene publicado.

Usa solo la identidad institucional del núcleo (logo, nombre y paleta), sin depender del legado.
"""
from collections import Counter
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.presentation.identidad import identidad_actual, logo_institucional

from .contenidos import Contenidos

ANCHO = A4[0] - 30 * mm


def _paleta():
    paleta = dict(getattr(identidad_actual()[1], 'paleta', {}) or {})
    return colors.HexColor(paleta.get('primario') or '#1d5b3a'), colors.HexColor(paleta.get('oscuro') or '#0b2e28')


def _estilos(primario):
    base = ParagraphStyle('base', fontName='Helvetica', fontSize=9.2, leading=12.6, textColor=colors.HexColor('#1f2d27'))
    return {
        'base': base,
        'titulo': ParagraphStyle('titulo', parent=base, fontName='Helvetica-Bold', fontSize=18, leading=22,
                                 textColor=primario, spaceAfter=4),
        'lema': ParagraphStyle('lema', parent=base, fontSize=10.5, leading=14, textColor=colors.HexColor('#4b5d54')),
        'seccion': ParagraphStyle('seccion', parent=base, fontName='Helvetica-Bold', fontSize=11.5, leading=15,
                                  textColor=primario, spaceBefore=10, spaceAfter=5),
        'celda': ParagraphStyle('celda', parent=base, fontSize=8.4, leading=11),
        'celda_negrita': ParagraphStyle('celda_negrita', parent=base, fontName='Helvetica-Bold', fontSize=8.4, leading=11),
        'nota': ParagraphStyle('nota', parent=base, fontSize=7.8, leading=10, textColor=colors.HexColor('#6b7a72')),
    }


def _p(texto, estilo):
    return Paragraph(escape(str(texto or '—')).replace('\n', '<br/>'), estilo)


def _seccion(texto, estilos):
    """El título de una sección nunca queda solo al pie de una página: si no cabe lo que sigue, pasa a la siguiente."""
    return [CondPageBreak(40 * mm), _p(texto, estilos['seccion'])]


def _tabla(cabecera, filas, anchos, estilos, primario):
    datos = [[_p(c, estilos['celda_negrita']) for c in cabecera]]
    datos += [[_p(valor, estilos['celda']) for valor in fila] for fila in filas]
    tabla = Table(datos, colWidths=[ANCHO * a for a in anchos], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef3f0')),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, primario),
        ('LINEBELOW', (0, 1), (-1, -1), 0.3, colors.HexColor('#dfe7e3')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _usd(monto):
    return f'USD {monto:,.0f}'.replace(',', '.') if monto else 'Por definir'


def reporte_del_centro(centro):
    primario, oscuro = _paleta()
    estilos = _estilos(primario)
    institucion = identidad_actual()[1]
    hoy = timezone.localdate()
    salida = BytesIO()

    def pie(lienzo, documento):
        lienzo.saveState()
        lienzo.setFillColor(oscuro)
        lienzo.rect(0, A4[1] - 18 * mm, A4[0], 18 * mm, stroke=0, fill=1)
        logo = logo_institucional(fondo='oscuro')
        if logo:
            try:
                lienzo.drawImage(str(logo), 15 * mm, A4[1] - 15 * mm, width=38 * mm, height=12 * mm,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:  # noqa: BLE001 - un logo ilegible no impide el reporte
                pass
        lienzo.setFillColor(colors.white)
        lienzo.setFont('Helvetica-Bold', 9)
        lienzo.drawRightString(A4[0] - 15 * mm, A4[1] - 9 * mm, 'REPORTE DEL CENTRO I+D')
        lienzo.setFont('Helvetica', 7.5)
        lienzo.drawRightString(A4[0] - 15 * mm, A4[1] - 13.5 * mm, f'Generado: {hoy:%d/%m/%Y}')
        lienzo.setFillColor(colors.HexColor('#6b7a72'))
        lienzo.setFont('Helvetica', 7.5)
        lienzo.drawString(15 * mm, 10 * mm, f'{getattr(institucion, "nombre", "")} · {centro}')
        lienzo.drawRightString(A4[0] - 15 * mm, 10 * mm, f'Página {documento.page}')
        lienzo.restoreState()

    documento = SimpleDocTemplate(salida, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                                  topMargin=26 * mm, bottomMargin=18 * mm, title=str(centro), author=str(centro))
    flujo = [_p(centro.nombre, estilos['titulo'])]
    flujo.append(_p(f'{centro.sigla} · {centro.estado_publico} · {centro.nombre_area}', estilos['nota']))
    if centro.lema:
        flujo += [Spacer(1, 4), _p(centro.lema, estilos['lema'])]
    if centro.imagen:
        try:
            # Storage remoto no expone un path local. Copiar el flujo permite
            # cerrar el archivo antes de que ReportLab componga las páginas.
            with centro.imagen.open('rb') as archivo:
                imagen = BytesIO(archivo.read())
            flujo += [Spacer(1, 8), Image(imagen, width=ANCHO, height=ANCHO * 0.42, kind='proportional')]
        except Exception:  # noqa: BLE001 - sin la imagen el reporte sigue
            pass
    componentes = list(centro.componentes.filter(publicado=True).annotate(
        servicios_activos=Count('servicios', filter=Q(servicios__activo=True))))
    servicios = list(centro.servicios.filter(activo=True))
    from .escenarios import filtro_contenido
    zonas = list(centro.zonas.filter(**filtro_contenido(centro)))
    cifras = [('Divisiones tecnológicas', sum(1 for c in componentes if c.tipo == 'division')),
              ('Plataformas de validación', sum(1 for c in componentes if c.tipo != 'division')),
              ('Servicios en el portafolio', len(servicios)),
              ('Superficie cubierta', f"{sum((z.area_m2 for z in zonas if not z.nivel.startswith('Exterior')), Decimal(0)):,.0f} m²".replace(',', '.'))]
    flujo += [Spacer(1, 8), _tabla(['Cifra', 'Valor'], cifras, (0.7, 0.3), estilos, primario)]
    flujo += [*_seccion('Qué es', estilos), _p(centro.presentacion or centro.proposito, estilos['base'])]
    if centro.estado_validado:
        flujo += [_p(f'Respaldo del estado: {centro.fuente_estado}', estilos['nota'])]
    if centro.identidad_validada:
        for titulo, texto in (('Adscripción institucional', centro.adscripcion), ('Misión', centro.mision),
                              ('Visión', centro.vision)):
            flujo += [*_seccion(titulo, estilos), _p(texto, estilos['base'])]
        flujo += [_p(f'Respaldo de identidad: {centro.fuente_identidad}', estilos['nota'])]
    else:
        flujo += [_p('Adscripción, misión y visión oficiales pendientes de validación institucional.', estilos['nota'])]
    flujo += [_p('Resumen automático de los registros publicados. No constituye un documento de aprobación institucional.',
                 estilos['nota'])]
    if centro.objetivo_general:
        flujo += [*_seccion('Objetivo general', estilos), _p(centro.objetivo_general, estilos['base'])]
    flujo += [*_seccion('Divisiones y plataformas', estilos),
              _tabla(['Nombre', 'Tipo', 'Área', 'Servicios'],
                     [(c.nombre, c.get_tipo_display(), f'{c.area_m2:.0f} m² · {c.nivel}' if c.area_m2 else c.nivel,
                       c.servicios_activos) for c in componentes],
                     (0.5, 0.2, 0.2, 0.1), estilos, primario)]
    ruta = list(centro.ruta.all())
    if ruta:
        flujo += [*_seccion('Ruta de atención: del reto a la transferencia', estilos),
                  _tabla(['Etapa', 'Propósito', 'Resultado'], [(f'{e.numero}. {e.nombre}', e.proposito, e.resultado) for e in ruta],
                         (0.3, 0.42, 0.28), estilos, primario)]
    if servicios:
        por_linea = Counter(s.linea for s in servicios)
        flujo += [*_seccion('Portafolio de servicios', estilos),
                  _tabla(['Línea de servicio', 'Servicios'], sorted(por_linea.items()), (0.85, 0.15), estilos, primario)]
    if zonas:
        por_nivel = {}
        for zona in zonas:
            por_nivel[zona.nivel] = por_nivel.get(zona.nivel, Decimal(0)) + zona.area_m2
        flujo += [*_seccion('Áreas por nivel', estilos),
                  _tabla(['Nivel', 'Superficie'], [(n, f'{a:,.0f} m²'.replace(',', '.')) for n, a in por_nivel.items()],
                         (0.7, 0.3), estilos, primario)]
    fases = list(centro.fases.all())
    if fases:
        flujo += [KeepTogether([_p('Fases de implementación', estilos['seccion']),
                                _tabla(['Fase', 'Actividades', 'Horizonte', 'Estado'],
                                       [(f'{f.numero}. {f.nombre}', f.actividades, f.horizonte, f.get_estado_display())
                                        for f in fases], (0.28, 0.44, 0.14, 0.14), estilos, primario)])]
    partidas = list(centro.presupuesto.all())
    if partidas:
        flujo += [*_seccion('Presupuesto referencial', estilos),
                  _tabla(['Concepto', 'Qué incluye', 'Monto'], [(p.concepto, p.contenido, _usd(p.monto)) for p in partidas],
                         (0.3, 0.5, 0.2), estilos, primario)]
    # Solo los indicadores con valor registrado: lo que aún no se midió no se publica.
    indicadores = Contenidos(centro).indicadores_medidos
    if indicadores:
        flujo += [*_seccion('Indicadores de resultado e impacto', estilos),
                  _p('Conteos sobre registros institucionales publicados. Cero: sin registros; las muestras se excluyen.',
                     estilos['nota']),
                  _tabla(['Categoría', 'Indicador', 'Valor'],
                         [(i.categoria, i.nombre, f'{i.valor:g}' + (f' ({"consulta" if i.calculado else "medición"}: {i.actualizado:%d/%m/%Y})' if i.actualizado else ''))
                          for i in indicadores], (0.26, 0.5, 0.24), estilos, primario)]
    riesgos = {r['categoria']: r['total'] for r in centro.riesgos.order_by().values('categoria').annotate(total=Count('pk'))}
    if riesgos:
        flujo += [*_seccion('Riesgos identificados con medida de mitigación', estilos),
                  _tabla(['Tipo de riesgo', 'Riesgos'], sorted(riesgos.items()), (0.8, 0.2), estilos, primario)]
    # El reporte público conserva únicamente cantidades por estado. No lee
    # expedientes, identidades de solicitantes ni detalles de su atención.
    from .models import SolicitudCentro
    nombres_estados = dict(SolicitudCentro.ESTADOS)
    solicitudes = {nombres_estados.get(s['estado'], s['estado']): s['total']
                   for s in centro.solicitudes.order_by().values('estado').annotate(total=Count('pk'))}
    if solicitudes:
        flujo += [*_seccion('Solicitudes recibidas (incluye peticiones de acceso)', estilos),
                  _tabla(['Estado', 'Cantidad'], sorted(solicitudes.items()), (0.8, 0.2), estilos, primario)]
    if centro.fuente:
        flujo += [Spacer(1, 10), _p(f'Fuente: {centro.fuente}', estilos['nota'])]
    documento.build(flujo, onFirstPage=pie, onLaterPages=pie)
    respuesta = HttpResponse(salida.getvalue(), content_type='application/pdf')
    respuesta['Content-Disposition'] = f'inline; filename="reporte-{centro.slug}-{hoy:%Y%m%d}.pdf"'
    return respuesta
