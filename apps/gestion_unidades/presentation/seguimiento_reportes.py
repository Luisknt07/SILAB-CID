"""Descargas privadas del seguimiento: PDF personal y CSV del grupo gestionado."""
import csv
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.utils.text import slugify


def _nota(valor):
    return format(valor, 'f').rstrip('0').rstrip('.') if valor is not None and '.' in format(valor, 'f') else str(valor) if valor is not None else '-'


def _respuesta_privada(contenido, tipo, nombre):
    respuesta = HttpResponse(contenido, content_type=tipo)
    respuesta['Content-Disposition'] = content_disposition_header(True, nombre)
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


def celda_csv_segura(valor):
    """Neutraliza fórmulas incluso tras blancos; citar la celda no las desactiva."""
    texto = str(valor if valor is not None else '').replace('\x00', '')
    if texto.startswith(('\t', '\r', '\n')) or texto.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + texto
    return texto


def csv_del_libro(curso, edicion, inscritos):
    """Un registro por intento, o por deber, limitado al listado ya autorizado."""
    respuesta = _respuesta_privada('\ufeff', 'text/csv; charset=utf-8',
        f'calificaciones-{slugify(curso.codigo)}-grupo-{edicion.pk if edicion else 0}.csv')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(['Curso', 'Código', 'Grupo', 'Persona', 'Documento', 'Estado académico', 'Avance (%)',
        'Actividad', 'Obligatoria', 'Nota / 10', 'Mínimo / 10', 'Estado actividad', 'Intento',
        'Intentos permitidos', 'Restantes por límite', 'Estado del intento', 'Fecha', 'Certificado'])
    for inscrito in inscritos:
        seguimiento = inscrito.seguimiento
        base = [curso.nombre, curso.codigo, edicion.nombre if edicion else '', seguimiento['nombre'],
                seguimiento['documento'], seguimiento['rotulo'], seguimiento['avance']['porcentaje']]
        certificado = seguimiento['certificado'].codigo if seguimiento['certificado'] else seguimiento['certificado_rotulo']
        for fila in seguimiento['calificadas'] or [None]:
            if fila is None:
                escritor.writerow([celda_csv_segura(valor) for valor in base + [''] * 10 + [certificado]])
                continue
            actividad = [fila['leccion'].titulo, 'Sí' if fila['obligatoria'] else 'No']
            for intento in fila['intentos'] or [None]:
                nota = intento['nota_10'] if intento else fila['nota_10']
                fecha = intento['fecha'] if intento else getattr(fila.get('entrega'), 'entregada_en', None)
                valores = base + actividad + [_nota(nota), _nota(fila['minima_10']), fila['rotulo'],
                    intento['numero'] if intento else '', fila['limite'] if fila['usados'] is not None else '',
                    fila['restantes'] if fila['usados'] is not None else '',
                    ('Aprobado' if intento['aprobado'] else 'No aprobado') if intento else '',
                    timezone.localtime(fecha).strftime('%d/%m/%Y %H:%M') if fecha else '', certificado]
                escritor.writerow([celda_csv_segura(valor) for valor in valores])
    return respuesta


def pdf_del_seguimiento(curso, seguimiento):
    """PDF en memoria, con el marco institucional y notas de todos los intentos."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.pdf_institucional import marco_institucional

    inscripcion = seguimiento['inscripcion']
    ahora = timezone.localtime()
    dibujar, lienzo, medidas = marco_institucional(formato='REPORTE PERSONAL DE SEGUIMIENTO',
        metadatos=[f'Curso: {curso.codigo}', f'Grupo: {inscripcion.edicion.nombre}',
                   f'Fecha: {ahora:%d/%m/%Y}'], pie='Seguimiento académico')
    tinta = medidas['colores']
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=medidas['pagesize'],
        leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f'Seguimiento - {curso.nombre}', author=curso.unidad.nombre)
    cuerpo = ParagraphStyle('SeguimientoCuerpo', fontName='Helvetica', fontSize=9, leading=12,
                            textColor=tinta['oscuro'], spaceAfter=5)
    titulo = ParagraphStyle('SeguimientoTitulo', parent=cuerpo, fontName='Helvetica-Bold', fontSize=15, leading=18,
                            spaceAfter=10, textColor=tinta['primario'])
    subtitulo = ParagraphStyle('SeguimientoSubtitulo', parent=cuerpo, fontName='Helvetica-Bold', fontSize=11, leading=14,
                               spaceBefore=10, spaceAfter=6, keepWithNext=True)
    pequeno = ParagraphStyle('SeguimientoPequeno', parent=cuerpo, fontSize=7.5, leading=10, spaceAfter=0)
    blanco = ParagraphStyle('SeguimientoCabecera', parent=pequeno, fontName='Helvetica-Bold', textColor=colors.white)

    def p(texto, estilo=cuerpo):
        return Paragraph(escape(str(texto)).replace('\n', '<br/>'), estilo)

    def tabla(filas, anchos):
        datos = [[p(valor, blanco if indice == 0 else pequeno) for valor in fila]
                 for indice, fila in enumerate(filas)]
        bloque = Table(datos, colWidths=anchos, repeatRows=1, hAlign='LEFT')
        bloque.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), tinta['primario']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, tinta['suave']]),
            ('GRID', (0, 0), (-1, -1), .4, tinta['linea']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return bloque

    ancho = medidas['ancho_util']
    elementos = [p(curso.nombre, titulo), p(seguimiento['nombre']),
        p(f"Documento: {seguimiento['documento'] or 'No registrado'}"),
        p(f"Grupo / edición: {inscripcion.edicion.nombre}"),
        p(f"Estado de inscripción: {seguimiento.get('inscripcion_rotulo', 'Inscrito')}"),
        p(f"Avance obligatorio: {seguimiento['avance']['completadas']} de {seguimiento['avance']['total']} "
          f"actividades ({seguimiento['avance']['porcentaje']} %). Estado: {seguimiento['rotulo']}."),
        p(f"{'Promedio' if seguimiento['promedio_completo'] else 'Promedio parcial'}: {_nota(seguimiento['promedio_10'])} / 10. "
          f"Oportunidades de evaluación disponibles: {seguimiento['oportunidades']}."),
        p('El mínimo y el número de intentos se configuran por actividad. El promedio parcial incluye sólo '
          'calificaciones registradas; no reemplaza completar todas las actividades obligatorias.', pequeno), Spacer(1, 4 * mm)]
    for bloque in seguimiento['modulos']:
        elementos.append(p(f"{bloque['modulo'].orden}. {bloque['modulo'].titulo}", subtitulo))
        filas = [['Actividad', 'Estado', 'Nota / 10', 'Intentos / mínimo']]
        for fila in bloque['actividades']:
            detalle = f"{fila['usados']} / {fila['limite']} usados; {fila['restantes']} restantes por límite" if fila['usados'] is not None else 'Revisión del instructor' if fila['leccion'].tipo == 'deber' else '-'
            if fila['leccion'].calificada:
                detalle += f"\nMínimo: {_nota(fila['minima_10'])} / 10"
            filas.append([fila['leccion'].titulo + (' (opcional)' if not fila['obligatoria'] else ''),
                          fila['rotulo'], _nota(fila['nota_10']) if fila['leccion'].calificada else '-', detalle])
        if len(filas) > 1:
            elementos.append(tabla(filas, [ancho * .40, ancho * .22, ancho * .12, ancho * .26]))
        for fila in bloque['actividades']:
            if fila['intentos']:
                titulo_intentos = p(f"Intentos: {fila['leccion'].titulo}", subtitulo)
                historial = [['Intento', 'Nota / 10', 'Resultado', 'Fecha']]
                for intento in fila['intentos']:
                    historial.append([intento['numero'], _nota(intento['nota_10']),
                        'Aprobado' if intento['aprobado'] else 'No aprobado',
                        timezone.localtime(intento['fecha']).strftime('%d/%m/%Y %H:%M')])
                tabla_intentos = tabla(historial, [ancho * .12, ancho * .18, ancho * .30, ancho * .40])
                if len(historial) <= 5:
                    elementos.append(KeepTogether([titulo_intentos, tabla_intentos]))
                else:
                    elementos.extend([titulo_intentos, tabla_intentos])
            if fila.get('entrega') and fila['entrega'].retroalimentacion:
                elementos.append(p(f"Retroalimentación: {fila['leccion'].titulo}", subtitulo))
                elementos.append(p(fila['entrega'].retroalimentacion))
    elementos.extend([p('Estado del certificado', subtitulo), p(seguimiento['certificado_rotulo'])])
    if seguimiento['certificado']:
        certificado = seguimiento['certificado']
        elementos.append(p(f"Código: {certificado.codigo}. Emitido: {timezone.localtime(certificado.emitido_en):%d/%m/%Y}."))
    elementos.append(p('Este reporte informa el seguimiento del grupo consultado. No sustituye al certificado '
                       'verificable que emite la institución. El avance usa las actividades publicadas actuales; '
                       'el certificado conserva los datos de su emisión.', pequeno))
    documento.build(elementos, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=lienzo)
    return salida.getvalue()


def respuesta_pdf_seguimiento(curso, seguimiento):
    return _respuesta_privada(pdf_del_seguimiento(curso, seguimiento), 'application/pdf',
        f'seguimiento-{slugify(curso.codigo)}-grupo-{seguimiento["inscripcion"].edicion_id}.pdf')
