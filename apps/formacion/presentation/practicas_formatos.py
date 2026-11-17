"""Formatos imprimibles de la práctica: lista de asistencia y bitácora.

Se descargan desde la ficha de la práctica antes de la sesión, se llenan y firman a
mano y vuelven al sistema escaneados, como evidencias de la ejecución («Registro de
asistencia firmado» y «Bitácora»).
"""

from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.presentation.estilo_reportes import estilos_informe
from apps.core.presentation.pdf_institucional import marco_institucional, metadatos_documento
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria

CODIGO_ASISTENCIA = "SLCID-PRACTICAS-ASISTENCIA"
CODIGO_BITACORA = "SLCID-PRACTICAS-BITACORA"
# Filas en blanco que se suman a los estudiantes previstos: siempre llega alguien más.
FILAS_ADICIONALES = 5
MAXIMO_FILAS = 300
# Cada apartado de la bitácora y los renglones en blanco que deja para escribir.
APARTADOS_BITACORA = (
    ("Actividades realizadas", 5),
    ("Equipos, materiales y software utilizados", 4),
    ("Resultados u observaciones", 4),
    ("Incidentes o novedades", 3),
)


def datos_cabecera(plan):
    """Lo que el sistema ya sabe de la práctica; nadie vuelve a escribirlo a mano."""
    escenario = ""
    if plan.reserva_id:
        escenario = ", ".join(espacio.nombre for espacio in plan.reserva.espacios_solicitados.all())
    tema = plan.tema_asignatura
    tematica = " · ".join(parte for parte in (tema.unidad_tematica, tema.nombre) if parte) if tema else plan.tema
    return [
        ("Unidad", plan.unidad.nombre),
        ("Asignatura · carrera · nivel", " · ".join((plan.asignatura, plan.carrera or "—", plan.semestre or "—"))),
        ("Práctica", f"{plan.codigo} · {plan.tema}"),
        ("Unidad temática o tema", tematica),
        ("Fecha y horario previstos", f"{plan.fecha:%d/%m/%Y} · {plan.hora_inicio:%H:%M}–{plan.hora_fin:%H:%M}"),
        # El escenario es el espacio de la reserva; sin reserva, la unidad misma.
        ("Escenario o espacio", escenario or plan.unidad.nombre),
        ("Docente", plan.docente_tutor),
        ("Responsable técnico", plan.responsable_tecnico.nombre_publico if plan.responsable_tecnico else ""),
    ]


def filas_asistencia(plan):
    """Nombre y «carrera / nivel» de cada fila: primero los registrados, después las filas en blanco."""
    filas = []
    if plan.reserva_id:
        for participante in plan.reserva.registros_participantes.order_by("nombre", "pk"):
            procedencia = " / ".join(parte for parte in (
                participante.get_carrera_display(), participante.get_nivel_academico_display()) if parte)
            filas.append((participante.nombre, procedencia))
    total = min(max(len(filas), plan.estudiantes_planificados) + FILAS_ADICIONALES, MAXIMO_FILAS)
    return filas + [("", "")] * max(0, total - len(filas))


def _documento(plan, *, formato, codigo, tipo_evidencia, contenido):
    """Marco, datos de la práctica, el contenido propio del formato, firmas e instrucción."""
    dibujar, CanvasNumerado, medidas = marco_institucional(
        formato=formato,
        metadatos=(*metadatos_documento(codigo), f"Expediente: {plan.codigo}"),
        pie=formato,
    )
    tinta, ancho = medidas["colores"], medidas["ancho_util"]
    estilos = estilos_informe(tinta)

    def celda(valor, estilo="celda"):
        return Paragraph(escape(str(valor)), estilos[estilo])

    datos = datos_cabecera(plan)
    rotulo, valor = 30 * mm, ancho / 2 - 30 * mm
    cabecera = Table(
        [[celda(datos[i][0], "celda_b"), celda(datos[i][1]), celda(datos[i + 1][0], "celda_b"), celda(datos[i + 1][1])]
         for i in range(0, len(datos), 2)],
        colWidths=[rotulo, valor, rotulo, valor],
    )
    cabecera.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .35, tinta["linea"]),
        ("BACKGROUND", (0, 0), (0, -1), tinta["suave"]), ("BACKGROUND", (2, 0), (2, -1), tinta["suave"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    def firma(nombre, cargo):
        return Paragraph(f"{escape(nombre)}<br/><b>{escape(cargo)}</b>", estilos["firma"])

    tecnico = plan.responsable_tecnico.nombre_publico if plan.responsable_tecnico else ""
    firmas = Table(
        [[firma(plan.docente_tutor, "Docente"), "", firma(tecnico, "Responsable técnico")]],
        colWidths=[ancho * .42, ancho * .16, ancho * .42],
    )
    firmas.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), .7, tinta["oscuro"]), ("LINEABOVE", (2, 0), (2, 0), .7, tinta["oscuro"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    instruccion = Paragraph(
        "Una vez lleno y firmado, escanea o fotografía este formato y súbelo en «Registrar ejecución → "
        f"Evidencias de la práctica», con el tipo «{tipo_evidencia}».",
        estilos["meta"],
    )
    historia = [
        cabecera, Spacer(1, 4 * mm),
        *contenido(ancho, tinta, celda),
        # Las firmas y la instrucción no se separan: una línea de firma sola en otra hoja no sirve.
        KeepTogether([Spacer(1, 14 * mm), firmas, Spacer(1, 3 * mm), instruccion]),
    ]
    salida = BytesIO()
    SimpleDocTemplate(
        salida, pagesize=medidas["pagesize"], leftMargin=medidas["margen"], rightMargin=medidas["margen"],
        topMargin=medidas["margen_superior"], bottomMargin=medidas["margen_inferior"],
        title=f"{formato} · {plan.codigo}",
    ).build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return salida.getvalue()


def render_lista_asistencia_pdf(plan):
    """Lista para firmar: los participantes ya registrados y filas en blanco para el resto."""
    def contenido(ancho, tinta, celda):
        columnas = ("N.º", "Nombres y apellidos", "Cédula o código", "Carrera / nivel", "Firma")
        filas = [[celda(columna, "cabecera") for columna in columnas]]
        filas += [[celda(numero), celda(nombre), "", celda(procedencia), ""]
                  for numero, (nombre, procedencia) in enumerate(filas_asistencia(plan), 1)]
        anchos = [10 * mm, 62 * mm, 28 * mm, 40 * mm]
        tabla = Table(filas, colWidths=[*anchos, ancho - sum(anchos)], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), tinta["primario"]), ("LINEBELOW", (0, 0), (-1, 0), .8, tinta["acento"]),
            # Líneas que se ven al imprimir y alto de renglón para firmar a mano.
            ("GRID", (0, 0), (-1, -1), .4, tinta["tenue"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, -1), 6.5), ("BOTTOMPADDING", (0, 1), (-1, -1), 6.5),
        ]))
        return [tabla]

    return _documento(
        plan, formato="Lista de asistencia de la práctica", codigo=CODIGO_ASISTENCIA,
        tipo_evidencia="Registro de asistencia firmado", contenido=contenido,
    )


def render_bitacora_pdf(plan):
    """Bitácora para llenar a mano: un recuadro con renglones por cada apartado."""
    def contenido(ancho, tinta, celda):
        bloques = []
        for titulo, renglones in APARTADOS_BITACORA:
            tabla = Table([[celda(titulo, "celda_b")]] + [[""]] * renglones, colWidths=[ancho],
                          rowHeights=[6.5 * mm] + [7 * mm] * renglones, spaceAfter=3 * mm)
            tabla.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), .5, tinta["tenue"]), ("BACKGROUND", (0, 0), (-1, 0), tinta["suave"]),
                ("LINEBELOW", (0, 0), (-1, 0), .8, tinta["primario"]),
                ("LINEBELOW", (0, 1), (-1, -2), .3, tinta["tenue"]), ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ]))
            bloques.append(tabla)
        return bloques

    return _documento(
        plan, formato="Bitácora de la práctica", codigo=CODIGO_BITACORA,
        tipo_evidencia="Bitácora", contenido=contenido,
    )


def _descargar(request, slug, plan_id, *, render, descripcion, archivo):
    # Mismo acceso que el PDF de la planificación, en cualquier estado de la práctica.
    from apps.formacion.presentation.practicas import _obtener_plan_visible

    plan = _obtener_plan_visible(request, slug, plan_id)
    registrar_auditoria(request, unidad=plan.unidad, accion="descargar", objeto=plan,
                        descripcion=f"{descripcion} de {plan.codigo}")
    respuesta = HttpResponse(render(plan), content_type="application/pdf")
    respuesta["Content-Disposition"] = f'attachment; filename="{plan.codigo}-{archivo}.pdf"'
    return respuesta


@login_required
def lista_asistencia_pdf_view(request, slug, plan_id):
    return _descargar(request, slug, plan_id, render=render_lista_asistencia_pdf,
                      descripcion="Formato de lista de asistencia", archivo="lista-asistencia")


@login_required
def bitacora_pdf_view(request, slug, plan_id):
    return _descargar(request, slug, plan_id, render=render_bitacora_pdf,
                      descripcion="Formato de bitácora", archivo="bitacora")
