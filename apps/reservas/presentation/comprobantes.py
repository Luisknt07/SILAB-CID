"""Construcción única del contenido mostrado y enviado al confirmar una reserva."""

from apps.core.presentation.identidad import identidad_actual
from apps.core.presentation.pdf_institucional import colores_institucionales, marco_institucional

import json
from io import BytesIO
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from django.utils import timezone

from apps.formacion.presentation.practicas_integracion import estado_documental_reserva


def _texto(valor, predeterminado="No registrado"):
    valor = str(valor or "").strip()
    return valor or predeterminado


def texto_cancelacion(reserva):
    """Quién, cuándo y por qué se canceló; vacío si la reserva sigue vigente."""
    if reserva.estado != "cancelada":
        return ""
    momento = reserva.cancelada_en
    if momento and timezone.is_aware(momento):
        momento = timezone.localtime(momento)
    quien = {
        "solicitante": "el solicitante",
        "laboratorio": "el laboratorio",
    }.get(reserva.origen_cancelacion, "")
    nombre = ""
    if reserva.cancelada_por_id:
        nombre = (
            reserva.cancelada_por.get_full_name() or reserva.cancelada_por.username
        )
    partes = ["Cancelada"]
    if momento:
        partes.append(f"el {momento:%d/%m/%Y %H:%M}")
    if quien:
        partes.append(f"por {quien}" + (f" ({nombre})" if nombre else ""))
    texto = " ".join(partes) + "."
    if reserva.motivo_cancelacion:
        texto += f" Motivo: {reserva.motivo_cancelacion}"
    return texto


def _descripcion_sin_intencion(reserva):
    """Descripción trazable sin la intención, que el comprobante muestra aparte."""
    texto = reserva.descripcion_proyecto or ""
    intencion = (reserva.intencion_solicitud or "").strip()
    if intencion:
        for etiqueta in ("Finalidad", "Intención"):
            texto = texto.replace(f" {etiqueta}: {intencion}", "")
    return texto


def _cantidad(valor):
    if valor is None:
        return "Por definir"
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return str(valor)
    return format(numero, "f").rstrip("0").rstrip(".") or "0"


def _unidades_fisicas(reserva):
    try:
        unidades = json.loads(reserva.unidades_seleccionadas or "[]")
    except (json.JSONDecodeError, TypeError):
        unidades = []
    resultado = []
    for unidad in unidades if isinstance(unidades, list) else []:
        if not isinstance(unidad, dict):
            continue
        codigo = _texto(unidad.get("codigo"), "Sin código")
        ubicacion = _texto(unidad.get("ubicacion"), "Ubicación por confirmar")
        resultado.append({
            "categoria": "Equipo",
            "nombre": _texto(unidad.get("equipo_nombre"), reserva.equipo_nombre),
            "detalle": f"{codigo} · {ubicacion}",
        })
    return resultado


def _dinero(valor):
    try:
        numero = Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return "$0.00"
    signo = "-" if numero < 0 else ""
    return f"{signo}${abs(numero):.2f}"


def _construir_cierre(reserva):
    detalle = reserva.detalle_ejecucion or {}
    liquidacion = reserva.desglose_liquidacion or detalle.get("liquidacion") or {}
    if not detalle and not liquidacion:
        return {"disponible": False}

    horario = detalle.get("horario_real") or {}
    consumos = []
    for item in detalle.get("consumibles") or []:
        consumos.append({
            "nombre": _texto(item.get("nombre"), "Insumo registrado"),
            "consumida": _cantidad(item.get("consumida")),
            "desperdiciada": _cantidad(item.get("desperdiciada")),
            "total": _cantidad(item.get("total_retirado")),
            "unidad": _texto(item.get("unidad"), "unidad"),
            "lote": _texto(item.get("lote"), "Sin lote"),
            "equipo": _texto(item.get("equipo"), "Sin equipo"),
            "costo_util": _dinero(item.get("costo_consumido")),
            "costo_desperdicio": _dinero(item.get("costo_desperdicio")),
        })

    conceptos = []
    for item in liquidacion.get("conceptos") or []:
        conceptos.append({
            "nombre": _texto(item.get("nombre"), "Concepto operativo"),
            "detalle": " · ".join(filter(None, [
                (
                    f"{_cantidad(item.get('cantidad'))} "
                    + ("guía(s)" if item.get("precio_por_guia") is not None else "recurso(s)")
                    if item.get("cantidad") not in (None, "") else ""
                ),
                (
                    f"{_cantidad(item.get('horas_reales'))} h reales"
                    if item.get("horas_reales") not in (None, "") else ""
                ),
            ])),
            "subtotal": _dinero(item.get("subtotal")),
            "aporte": _dinero(item.get("aporte_institucional")),
            "usuario": _dinero(item.get("valor_usuario")),
            "es_desperdicio": item.get("categoria") == "desperdicio",
        })

    ingreso = detalle.get("ingreso") or {}
    conciliacion = ingreso.get("conciliacion") or {}
    fecha_cierre = reserva.fecha_cierre
    if fecha_cierre and timezone.is_aware(fecha_cierre):
        fecha_cierre = timezone.localtime(fecha_cierre)
    cumplimiento = {
        "si": "Sí",
        "parcial": "Parcial",
        "no": "No",
    }.get(detalle.get("cumplimiento_resultado"), "No registrado")
    estado_ingreso = {
        "confirmado": "Pago verificado",
        "pendiente": "Pendiente de verificación",
        "anulado": "Anulado",
    }.get(ingreso.get("estado"), "No aplica")
    estimacion = liquidacion.get("estimacion_original") or {}
    variacion = liquidacion.get("variacion") or {}
    return {
        "disponible": True,
        "codigo": f"CIERRE-{(reserva.codigo_reserva or reserva.pk)}",
        "fecha": fecha_cierre.strftime("%d/%m/%Y %H:%M") if fecha_cierre else "Sin fecha registrada",
        "registrado_por": _texto(detalle.get("registrada_por"), "Responsable no identificado"),
        "horario": (
            f"{horario.get('inicio')}–{horario.get('fin')}"
            if horario.get("inicio") and horario.get("fin") else "No registrado"
        ),
        "duracion": f"{_cantidad(liquidacion.get('duracion_real_horas'))} h",
        "asistentes": detalle.get("asistentes_total", 0),
        "cumplimiento": cumplimiento,
        "observaciones": _texto(detalle.get("observaciones"), "Sin observaciones de cierre"),
        "incidencia": detalle.get("incidencia"),
        "consumos": consumos,
        "conceptos": conceptos,
        "costo_material_util": _dinero(liquidacion.get("costo_material_util")),
        "costo_desperdicio": _dinero(liquidacion.get("costo_desperdicio_laboratorio")),
        "costo_operativo": _dinero(liquidacion.get("costo_operativo_real")),
        "aporte_institucional": _dinero(liquidacion.get("aporte_institucional_real")),
        "valor_final_usuario": _dinero(liquidacion.get("valor_final_usuario")),
        "estimado_usuario": _dinero(estimacion.get("valor_usuario")),
        "variacion_usuario": _dinero(variacion.get("valor_usuario")),
        "politica": _texto(liquidacion.get("politica"), "Liquidación basada en la ejecución registrada."),
        "advertencias": liquidacion.get("advertencias") or [],
        "pago": {
            "aplica": bool(ingreso),
            "estado": estado_ingreso,
            "monto": _dinero(ingreso.get("monto")),
            "referencia": _texto(ingreso.get("referencia"), "Sin referencia"),
            "monto_calculado": _dinero(conciliacion.get("monto_calculado")),
            "ajuste": _dinero(conciliacion.get("ajuste")),
            "justificacion": _texto(conciliacion.get("justificacion"), "Sin ajuste manual"),
        },
    }


def _palabra_trabajo(reserva, cantidad):
    """Piezas, muestras o ensayos: lo decide la unidad que atiende."""
    configuracion = getattr(reserva.laboratorio, "configuracion_operativa", None)
    singular, plural = (
        configuracion.palabras_trabajo if configuracion else ("pieza", "piezas")
    )
    return singular if cantidad == 1 else plural


def _construir_trabajo(reserva):
    """Lo que se va a producir: piezas y precisiones escritas por la persona.

    En el servicio incluye urgencia y entrega; en la reserva de recursos basta
    con las piezas y el detalle que se escribió en la tarjeta de cada equipo.
    """
    if reserva.tipo_solicitud != "servicio":
        detalle = _texto(reserva.detalle_trabajo, "")
        piezas = reserva.cantidad_piezas or 1
        if not detalle and piezas <= 1:
            return {"aplica": False}
        return {
            "aplica": True,
            "recursos": True,
            "piezas": piezas,
            "palabra": _palabra_trabajo(reserva, piezas),
            "detalle": detalle or "Sin precisiones adicionales",
        }
    trabajo = (reserva.desglose_cotizacion or {}).get("trabajo") or {}
    equipo = trabajo.get("equipo") or {}
    return {
        "aplica": True,
        "recursos": False,
        "piezas": reserva.cantidad_piezas or 1,
        "palabra": _palabra_trabajo(reserva, reserva.cantidad_piezas or 1),
        "urgencia": (
            reserva.get_urgencia_servicio_display()
            if reserva.urgencia_servicio else "Atención normal según la cola de trabajo"
        ),
        "entrega": (
            reserva.fecha_entrega_prevista.strftime("%d/%m/%Y")
            if reserva.fecha_entrega_prevista else "Por confirmar en la revisión técnica"
        ),
        "equipo": _texto(equipo.get("nombre"), ""),
        "detalle": _texto(reserva.detalle_trabajo, "Sin precisiones adicionales"),
    }


def _construir_economia(reserva):
    """Detalle económico estimado: qué paga la persona y qué asume la Universidad."""
    desglose = reserva.desglose_cotizacion or {}
    filas = []
    if reserva.tipo_solicitud == "servicio":
        for concepto in desglose.get("conceptos") or []:
            for componente in concepto.get("componentes") or []:
                filas.append({
                    "concepto": f"{concepto.get('servicio')} · {componente.get('nombre')}",
                    "detalle": _texto(componente.get("cantidad"), "") or _texto(componente.get("detalle"), ""),
                    "cantidad": _texto(componente.get("cantidad"), "—"),
                    "subtotal": _dinero(componente.get("valor")),
                    "aporte": _dinero(componente.get("aporte_institucional")),
                    "usuario": _dinero(componente.get("valor_usuario")),
                    "condicion": (
                        "Se cobra" if componente.get("cobrado")
                        else f"Referencial · lo asume la {identidad_actual()[1].siglas}"
                    ),
                })
        for material in desglose.get("materiales_planificados") or []:
            filas.append({
                "concepto": _texto(material.get("nombre"), "Material"),
                "detalle": _texto(material.get("variante"), ""),
                "cantidad": (
                    f"{material['cantidad']} {material.get('unidad', 'unidades')}"
                    if material.get("cantidad") else "Por calcular"
                ),
                "subtotal": _dinero(material.get("subtotal")),
                "aporte": _dinero(0),
                "usuario": _dinero(material.get("valor_usuario", material.get("subtotal"))),
                "condicion": "Se cobra según consumo real",
            })
        politica = (
            "Los materiales se cobran según el consumo real registrado en el cierre. "
            "La UPEC asume íntegramente equipos, diseño, espacios y personal."
        )
    else:
        programa = desglose.get("programa") or {}
        sesiones = int(programa.get("sesiones") or 1)
        for concepto in desglose.get("conceptos") or []:
            cantidad = concepto.get("cantidad")
            horas = concepto.get("horas")
            es_insumo = concepto.get("categoria") == "insumo"
            if es_insumo:
                unidad = concepto.get("unidad", "unidades")
                por_sesion = concepto.get("cantidad_por_sesion")
                if not cantidad:
                    cantidad_texto = "Por calcular"
                elif sesiones > 1 and por_sesion:
                    cantidad_texto = f"{por_sesion} {unidad} × {sesiones} sesiones = {cantidad} {unidad}"
                else:
                    cantidad_texto = f"{cantidad} {unidad}"
            elif concepto.get("precio_por_guia") is not None:
                cantidad_texto = f"{cantidad or 0} guía(s)"
            else:
                horas_sesion = concepto.get("horas_por_sesion")
                cantidad_texto = (
                    f"{cantidad or 0} × {horas_sesion} h × {sesiones} sesiones"
                    if sesiones > 1 and horas_sesion else f"{cantidad or 0} × {horas or 0} h"
                )
            filas.append({
                "concepto": _texto(concepto.get("nombre"), "Concepto"),
                "detalle": "",
                "cantidad": cantidad_texto,
                "subtotal": _dinero(concepto.get("subtotal")),
                "aporte": _dinero(concepto.get("aporte_institucional")),
                "usuario": _dinero(concepto.get("valor_usuario")),
                "condicion": (
                    "Se cobra según consumo real" if es_insumo else "Apoyo institucional"
                ),
            })
        politica = (
            "Los insumos y materiales se cobran según el consumo real; el uso de "
            "espacios, equipos, software y acompañamiento se valora como referencia "
            "asumida íntegramente por la UPEC. Los recursos reservados deben "
            "utilizarse: una reserva no usada sin cancelación previa se registra como "
            "incumplimiento y reduce la prioridad en futuras reservas y servicios."
        )
    if not filas:
        return {"aplica": False}
    iva = desglose.get("iva") or {}
    programa = desglose.get("programa") or {}
    sesiones = int(programa.get("sesiones") or 1)
    return {
        "aplica": True,
        "filas": filas,
        "sesiones": sesiones,
        "programa": (
            {
                "texto": (
                    f"Programa de {sesiones} sesiones de {programa.get('horas_por_sesion') or 0} h "
                    f"({programa.get('horas_totales') or 0} h en total) · las cantidades de insumos "
                    f"son por sesión · por sesión {_dinero(programa.get('usuario_por_sesion'))} a tu cargo"
                ),
                "modificada": bool(programa.get("sesion_modificada")),
                "nota": _texto(programa.get("nota"), ""),
            }
            if sesiones > 1 or programa.get("sesion_modificada") else None
        ),
        "referencia": _dinero(desglose.get("valor_referencial") or desglose.get("subtotal")),
        "aporte": _dinero(desglose.get("aporte_institucional") or desglose.get("descuento")),
        "subtotal_usuario": _dinero(desglose.get("subtotal_usuario") or desglose.get("valor_estimado_usuario")),
        "iva_aplica": bool(iva.get("aplica")),
        "iva_porcentaje": _texto(iva.get("porcentaje"), "0.00"),
        "iva": _dinero(iva.get("monto")),
        "usuario": _dinero(desglose.get("valor_estimado_usuario") or desglose.get("total")),
        "politica": politica,
    }


def _construir_trazabilidad(reserva):
    """Revisiones y cambios aprobados: la persona sabe si lo que ve ya fue modificado."""
    revisiones = reserva.revisiones.count()
    aprobados = reserva.solicitudes_cambio.filter(estado="aprobada").order_by("-revisada_en")
    ultimo = aprobados.first()
    fecha = ultimo.revisada_en if ultimo else None
    if fecha and timezone.is_aware(fecha):
        fecha = timezone.localtime(fecha)
    return {
        "revisiones": revisiones,
        "cambios_aprobados": aprobados.count(),
        "ultimo_cambio": fecha.strftime("%d/%m/%Y %H:%M") if fecha else "",
        "texto": (
            f"Revisión {revisiones} · {aprobados.count()} cambio(s) aprobado(s)"
            + (f" · último el {fecha.strftime('%d/%m/%Y %H:%M')}" if fecha else "")
            if aprobados.exists() else "Sin cambios posteriores a la solicitud original"
        ),
    }


def construir_comprobante_reserva(reserva):
    """Devuelve los mismos datos normalizados para la vista HTML y el correo."""
    documentacion = estado_documental_reserva(reserva)
    recursos = _unidades_fisicas(reserva)
    recursos.extend({
        "categoria": "Espacio",
        "nombre": espacio.nombre,
        "detalle": " · ".join(filter(None, [espacio.codigo, espacio.ubicacion])),
    } for espacio in reserva.espacios_solicitados.all())
    recursos.extend({
        "categoria": "Software",
        "nombre": software.nombre,
        "detalle": " · ".join(filter(None, [software.version, software.get_tipo_acceso_display()])),
    } for software in reserva.software_solicitado.all())
    recursos.extend({
        "categoria": "Servicio",
        "nombre": servicio.nombre,
        "detalle": servicio.code or "Servicio técnico",
    } for servicio in reserva.servicios_solicitados.all())
    piezas_trabajo = reserva.cantidad_piezas or 1
    for solicitud in reserva.consumibles_solicitados.select_related("consumible"):
        cantidad = _cantidad(solicitud.cantidad_solicitada)
        unidad = solicitud.consumible.unidad_medida or "unidades"
        recursos.append({
            "categoria": "Insumo o material",
            "nombre": solicitud.consumible.nombre,
            # Las piezas explican la cantidad: quien revisa ve de dónde sale.
            "detalle": (
                "Cantidad por definir durante la revisión técnica"
                if solicitud.cantidad_solicitada is None
                else f"{cantidad} {unidad} solicitados"
                + (f" · {piezas_trabajo} piezas" if piezas_trabajo > 1 else "")
            ),
        })
    if not recursos:
        recursos.append({
            "categoria": "Unidad",
            "nombre": reserva.laboratorio.nombre,
            "detalle": "Alcance y recursos por confirmar durante la revisión técnica",
        })

    participantes = [{
        "nombre": participante.get_full_name() or participante.username,
        "correo": participante.email or "Correo no registrado",
    } for participante in reserva.participantes.all()]

    sesiones = []
    if reserva.programacion_id:
        sesiones_qs = reserva.programacion.sesiones.order_by("fecha", "hora_inicio", "pk")
        for sesion in sesiones_qs[:8]:
            sesiones.append({
                "codigo": sesion.codigo_reserva or f"RES-{sesion.pk:06d}",
                "fecha": sesion.fecha.strftime("%d/%m/%Y"),
                "horario": f"{sesion.hora_inicio:%H:%M}–{sesion.hora_fin:%H:%M}",
            })
        total_sesiones = sesiones_qs.count()
    else:
        total_sesiones = 1

    responsable = reserva.responsable_asignado
    contacto_unidad = (
        reserva.laboratorio.contacto_email
        or getattr(reserva.laboratorio.administrador, "email", "")
        or "Se informará dentro del sistema"
    )
    proposito = (
        reserva.get_proposito_codigo_display()
        if reserva.proposito_codigo
        else reserva.proposito
    )
    actividad = (
        reserva.referencia_actividad
        or reserva.descripcion_proyecto
        or reserva.titulo_solicitud
    )
    nombre_solicitante = (
        reserva.nombre_solicitante
        or (reserva.usuario.get_full_name() if reserva.usuario_id else "")
        or (reserva.usuario.username if reserva.usuario_id else "Solicitante")
    )
    primer_nombre = nombre_solicitante.split()[0] if nombre_solicitante else ""
    fecha_registro = reserva.fecha_reserva
    if fecha_registro and timezone.is_aware(fecha_registro):
        fecha_registro = timezone.localtime(fecha_registro)

    es_servicio = reserva.tipo_solicitud == "servicio"
    tiene_costo_referencial = bool(
        reserva.costo_estimado is not None
        and (
            es_servicio
            or (reserva.desglose_cotizacion or {}).get("conceptos")
        )
    )
    return {
        "codigo": reserva.codigo_reserva or f"RES-{reserva.pk:06d}",
        "titulo": reserva.titulo_solicitud or reserva.equipo_nombre or "Solicitud al laboratorio",
        "unidad": reserva.laboratorio.nombre,
        "solicitante": nombre_solicitante,
        "saludo": f"Hola, {primer_nombre}" if primer_nombre else "Hola",
        "correo_solicitante": reserva.correo_solicitante or getattr(reserva.usuario, "email", ""),
        "telefono_solicitante": reserva.telefono_solicitante or "No registrado",
        "fecha": reserva.fecha.strftime("%d/%m/%Y"),
        "horario": f"{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}",
        "estado": reserva.get_estado_display(),
        # La reserva cancelada sigue siendo registro y evidencia.
        "cancelacion": texto_cancelacion(reserva),
        "tipo_solicitud": reserva.get_tipo_solicitud_display(),
        "proposito": _texto(proposito),
        "actividad": _texto(actividad),
        "descripcion": _texto(_descripcion_sin_intencion(reserva), "Sin descripción adicional"),
        # Lo que la persona pidió realizar, en fila propia (no se repite en la descripción).
        "solicitud": _texto(reserva.intencion_solicitud, ""),
        "requisitos": _texto(reserva.requisitos_especiales, "Sin requisitos especiales"),
        "participantes_total": reserva.numero_participantes or 1,
        "participantes": participantes,
        "responsable": responsable.nombre_publico if responsable else "Por asignar",
        "contacto_unidad": contacto_unidad,
        "recursos": recursos,
        "fecha_registro": fecha_registro.strftime("%d/%m/%Y %H:%M"),
        "es_programacion": bool(reserva.programacion_id),
        "sesiones": sesiones,
        "total_sesiones": total_sesiones,
        "sesiones_adicionales": max(0, total_sesiones - len(sesiones)),
        "costo_estimado": (
            f"${reserva.costo_estimado:.2f}"
            if tiene_costo_referencial else "No aplica"
        ),
        "costo_etiqueta": (
            "Valor estimado y forma de pago"
            if es_servicio else "Estimación económica de la reserva"
        ),
        "costo_detalle": (
            reserva.get_metodo_pago_display()
            if es_servicio and reserva.metodo_pago
            else (
                "referencia ${referencia} · aporte {institucion} ${aporte}; sujeto a validación técnica"
            ).format(
                institucion=identidad_actual()[1].siglas,
                referencia=(reserva.desglose_cotizacion or {}).get(
                    "valor_referencial", "0.00"
                ),
                aporte=(reserva.desglose_cotizacion or {}).get(
                    "aporte_institucional", "0.00"
                ),
            )
        ),
        "metodo_pago": (
            reserva.get_metodo_pago_display() if reserva.metodo_pago else "No aplica"
        ),
        "documentacion": documentacion,
        "trabajo": _construir_trabajo(reserva),
        "economia": _construir_economia(reserva),
        "trazabilidad": _construir_trazabilidad(reserva),
        "cierre": _construir_cierre(reserva),
    }


def render_comprobante_reserva_pdf(comprobante):
    """Genera el comprobante institucional desde la misma fuente de la vista HTML."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        LongTable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    tinta = colores_institucionales()
    verde, verde_oscuro = tinta['primario'], tinta['oscuro']
    verde_claro = tinta['suave']
    gris, borde, fondo = tinta['tenue'], tinta['linea'], tinta['suave']
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("ReceiptNormal", parent=estilos["Normal"], fontName="Helvetica", fontSize=8.2, leading=11, textColor=verde_oscuro)
    pequeno = ParagraphStyle("ReceiptSmall", parent=normal, fontSize=7, leading=9, textColor=gris)
    etiqueta = ParagraphStyle("ReceiptLabel", parent=pequeno, fontName="Helvetica-Bold", fontSize=6.6, leading=8, textColor=verde)
    titulo = ParagraphStyle("ReceiptTitle", parent=normal, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=TA_CENTER)
    seccion = ParagraphStyle("ReceiptSection", parent=normal, fontName="Helvetica-Bold", fontSize=9.2, leading=11, textColor=colors.white)
    dinero = ParagraphStyle("ReceiptMoney", parent=normal, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    def p(valor, estilo=normal, *, markup=False):
        contenido = str(valor or "—")
        return Paragraph(contenido if markup else escape(contenido), estilo)

    def bloque_titulo(texto):
        tabla = Table([[p(texto, seccion)]], splitInRow=1, colWidths=[181 * mm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), verde),
            ("BOX", (0, 0), (-1, -1), .6, verde),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tabla

    def tabla_datos(filas, anchos=(48 * mm, 133 * mm)):
        contenido = [[p(nombre, etiqueta), p(valor)] for nombre, valor in filas]
        tabla = Table(contenido, splitInRow=1, colWidths=list(anchos), repeatRows=0)
        tabla.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), .55, borde),
            ("INNERGRID", (0, 0), (-1, -1), .35, borde),
            ("BACKGROUND", (0, 0), (0, -1), verde_claro),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tabla

    memoria = BytesIO()
    dibujar_marco, CanvasNumerado, medidas = marco_institucional(
        formato="COMPROBANTE DE RESERVA Y ATENCIÓN",
        metadatos=(
            f"Referencia: {comprobante['codigo']}",
            f"Estado: {comprobante['estado']}",
            f"Fecha: {comprobante['fecha']}",
        ),
        pie="Gestión y reserva de laboratorios",
    )
    documento = SimpleDocTemplate(
        memoria,
        pagesize=medidas['pagesize'],
        rightMargin=medidas['margen'],
        leftMargin=medidas['margen'],
        topMargin=medidas['margen_superior'],
        bottomMargin=medidas['margen_inferior'],
        title=f"Comprobante {comprobante['codigo']}",
        author=identidad_actual()[1].nombre,
    )
    historia = [p(comprobante["titulo"], titulo), Spacer(1, 4 * mm)]
    historia.extend([
        bloque_titulo("1. Identificación de la solicitud"),
        tabla_datos([
            ("Laboratorio", comprobante["unidad"]),
            ("Solicitante", f"{comprobante['solicitante']} · {comprobante['correo_solicitante'] or 'Correo no registrado'}"),
            ("Actividad", comprobante["actividad"]),
            *([("Lo que se solicita realizar", comprobante["solicitud"])] if comprobante["solicitud"] else []),
            ("Programación solicitada", f"{comprobante['fecha']} · {comprobante['horario']}"),
            ("Tipo y propósito", f"{comprobante['tipo_solicitud']} · {comprobante['proposito']}"),
            ("Estado", comprobante["estado"]),
            *([("Cancelación", comprobante["cancelacion"])] if comprobante["cancelacion"] else []),
            ("Trazabilidad", comprobante["trazabilidad"]["texto"]),
        ]),
        Spacer(1, 3 * mm),
        bloque_titulo("2. Recursos y condiciones solicitadas"),
    ])
    recursos = [[p("Categoría", etiqueta), p("Recurso o condición", etiqueta)]]
    recursos.extend([[p(item["categoria"], pequeno), p(f"<b>{escape(item['nombre'])}</b><br/>{escape(item['detalle'])}", normal, markup=True)] for item in comprobante["recursos"]])
    tabla_recursos = LongTable(recursos, splitInRow=1, colWidths=[43 * mm, 138 * mm], repeatRows=1)
    tabla_recursos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), verde_claro),
        ("BOX", (0, 0), (-1, -1), .55, borde),
        ("INNERGRID", (0, 0), (-1, -1), .35, borde),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    historia.extend([tabla_recursos, Spacer(1, 3 * mm)])

    numero = 3
    trabajo = comprobante["trabajo"]
    economia = comprobante["economia"]
    if trabajo["aplica"] or economia["aplica"]:
        historia.append(bloque_titulo(f"{numero}. Trabajo y detalle económico estimado"))
        numero += 1
        if trabajo["aplica"]:
            historia.extend([
                tabla_datos([
                    ("Piezas y urgencia", f"{trabajo['piezas']} pieza(s) · {trabajo['urgencia']}"),
                    ("Entrega prevista", trabajo["entrega"]),
                    ("Equipo previsto", trabajo["equipo"] or "Lo define la unidad en la revisión"),
                    ("Precisiones del trabajo", trabajo["detalle"]),
                ]),
                Spacer(1, 2 * mm),
            ])
        if economia["aplica"]:
            if economia.get("programa"):
                historia.extend([
                    p(economia["programa"]["texto"], pequeno),
                    Spacer(1, 1 * mm),
                ])
                if economia["programa"]["nota"]:
                    historia.extend([p(economia["programa"]["nota"], pequeno), Spacer(1, 1 * mm)])
            historia.extend([
                tabla_datos([
                    ("Valor estimado a tu cargo", f"{economia['usuario']}" + (
                        f" (incluye IVA {economia['iva_porcentaje']} %: {economia['iva']})"
                        if economia["iva_aplica"] else ""
                    )),
                    (f"Lo asume la {identidad_actual()[1].siglas}", economia["aporte"]),
                    ("Valor de referencia", economia["referencia"]),
                ]),
                Spacer(1, 2 * mm),
            ])
            filas = [[
                p("Concepto", etiqueta), p("Cantidad", etiqueta), p("Subtotal", etiqueta),
                p(f"Lo asume la {identidad_actual()[1].siglas}", etiqueta), p("A tu cargo", etiqueta),
            ]]
            for fila in economia["filas"]:
                filas.append([
                    p(
                        f"<b>{escape(fila['concepto'])}</b><br/>{escape(fila['condicion'])}",
                        normal,
                        markup=True,
                    ),
                    p(fila["cantidad"], pequeno),
                    p(fila["subtotal"], dinero),
                    p(f"−{fila['aporte']}" if fila["aporte"] != "$0.00" else "$0.00", dinero),
                    p(fila["usuario"], dinero),
                ])
            if economia["iva_aplica"]:
                filas.append([
                    p(f"<b>IVA {escape(economia['iva_porcentaje'])} %</b>", normal, markup=True),
                    p("Sobre lo que pagas", pequeno), p(economia["iva"], dinero), p("$0.00", dinero),
                    p(economia["iva"], dinero),
                ])
            filas.append([
                p("<b>Total</b>", normal, markup=True),
                p("", pequeno),
                p(economia["referencia"], dinero),
                p(f"−{economia['aporte']}", dinero),
                p(f"<b>{escape(economia['usuario'])}</b>", dinero, markup=True),
            ])
            tabla = LongTable(filas, splitInRow=1, colWidths=[71 * mm, 30 * mm, 26 * mm, 28 * mm, 26 * mm], repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), verde_claro),
                ("BOX", (0, 0), (-1, -1), .55, borde),
                ("INNERGRID", (0, 0), (-1, -1), .35, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            historia.extend([tabla, Spacer(1, 2 * mm), p(economia["politica"], pequeno), Spacer(1, 3 * mm)])

    cierre = comprobante["cierre"]
    if cierre["disponible"]:
        historia.extend([
            bloque_titulo(f"{numero}. Ejecución real y trazabilidad"),
            tabla_datos([
                ("Código de cierre", cierre["codigo"]),
                ("Horario y duración reales", f"{cierre['horario']} · {cierre['duracion']}"),
                ("Asistencia y cumplimiento", f"{cierre['asistentes']} asistentes · resultado {cierre['cumplimiento']}"),
                ("Registrado por", f"{cierre['registrado_por']} · {cierre['fecha']}"),
                ("Observaciones", cierre["observaciones"]),
                ("Incidencia", (
                    f"{cierre['incidencia'].get('titulo')} · {cierre['incidencia'].get('equipo')} · prioridad {cierre['incidencia'].get('prioridad')}"
                    if cierre["incidencia"] else "No se registraron incidentes"
                )),
            ]),
            Spacer(1, 3 * mm),
        ])
        if cierre["consumos"]:
            historia.append(bloque_titulo(f"{numero + 1}. Consumos reales"))
            filas = [[p(x, etiqueta) for x in ("Insumo / trazabilidad", "Útil", "Desperdicio", "Costo útil", "Pérdida")]]
            for item in cierre["consumos"]:
                filas.append([
                    p(f"<b>{escape(item['nombre'])}</b><br/>{escape(item['lote'])} · {escape(item['equipo'])}", normal, markup=True),
                    p(f"{item['consumida']} {item['unidad']}", pequeno),
                    p(f"{item['desperdiciada']} {item['unidad']}", pequeno),
                    p(item["costo_util"], dinero),
                    p(item["costo_desperdicio"], dinero),
                ])
            tabla = LongTable(filas, splitInRow=1, colWidths=[73 * mm, 27 * mm, 29 * mm, 26 * mm, 26 * mm], repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), verde_claro),
                ("BOX", (0, 0), (-1, -1), .55, borde),
                ("INNERGRID", (0, 0), (-1, -1), .35, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            historia.extend([tabla, Spacer(1, 3 * mm)])

        historia.append(bloque_titulo(f"{numero + 2}. Liquidación del cierre"))
        filas = [[p(x, etiqueta) for x in ("Concepto", "Costo", f"Aporte {identidad_actual()[1].siglas}", "Usuario")]]
        for item in cierre["conceptos"]:
            filas.append([
                p(f"<b>{escape(item['nombre'])}</b>{('<br/>' + escape(item['detalle'])) if item['detalle'] else ''}", normal, markup=True),
                p(item["subtotal"], dinero),
                p(item["aporte"], dinero),
                p(item["usuario"], dinero),
            ])
        filas.append([
            p("TOTAL DEL CIERRE", etiqueta),
            p(cierre["costo_operativo"], dinero),
            p(cierre["aporte_institucional"], dinero),
            p(cierre["valor_final_usuario"], dinero),
        ])
        tabla = LongTable(filas, splitInRow=1, colWidths=[91 * mm, 30 * mm, 30 * mm, 30 * mm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), verde_claro),
            ("BACKGROUND", (0, -1), (-1, -1), fondo),
            ("LINEABOVE", (0, -1), (-1, -1), 1, verde),
            ("BOX", (0, 0), (-1, -1), .55, borde),
            ("INNERGRID", (0, 0), (-1, -2), .35, borde),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        historia.extend([
            tabla,
            Spacer(1, 2.5 * mm),
            tabla_datos([
                ("Estimación inicial del usuario", cierre["estimado_usuario"]),
                ("Valor final del usuario", cierre["valor_final_usuario"]),
                ("Variación", cierre["variacion_usuario"]),
                ("Desperdicio asumido por el laboratorio", cierre["costo_desperdicio"]),
                ("Estado del pago", (
                    f"{cierre['pago']['estado']} · {cierre['pago']['monto']} · {cierre['pago']['referencia']}"
                    if cierre["pago"]["aplica"] else "No aplica"
                )),
                ("Criterio", cierre["politica"]),
            ]),
        ])
    else:
        historia.extend([
            bloque_titulo(f"{numero}. Estado operativo"),
            tabla_datos([
                ("Atención", "La ejecución todavía no ha sido cerrada por el laboratorio."),
                ("Estimación", f"{comprobante['costo_estimado']} · {comprobante['costo_detalle']}"),
            ]),
        ])

    historia.extend([Spacer(1, 5 * mm), p(
        f"Documento generado por {identidad_actual()[0].nombre_corto}. No reemplaza una factura ni un comprobante tributario; conserva la trazabilidad institucional de la solicitud y su atención.",
        pequeno,
    )])

    documento.build(historia, onFirstPage=dibujar_marco, onLaterPages=dibujar_marco,
                    canvasmaker=CanvasNumerado)
    return memoria.getvalue()
