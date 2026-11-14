"""Datos compartidos entre la reserva y la guía estructurada de práctica."""

from copy import deepcopy
from datetime import datetime, timedelta

from django.db import transaction

from apps.reservas.models.reservas import GuiaActividadReserva


def _nombre_usuario(usuario):
    if not usuario:
        return ""
    return usuario.get_full_name() or usuario.get_username()


def _duracion_reserva(reserva):
    if not reserva or not reserva.hora_inicio or not reserva.hora_fin:
        return ""
    inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
    fin = datetime.combine(reserva.fecha, reserva.hora_fin)
    if fin <= inicio:
        fin += timedelta(days=1)
    minutos = int((fin - inicio).total_seconds() // 60)
    horas, resto = divmod(minutos, 60)
    if resto:
        return f"{horas} h {resto} min" if horas else f"{resto} min"
    return f"{horas} hora" if horas == 1 else f"{horas} horas"


def _codigo_guia(actividad):
    base = (actividad.codigo or f"ACT-{actividad.pk:04d}").strip().upper()
    return base if base.startswith(("GP-", "GUIA-", "GUÍA-")) else f"GP-{base}"


def _lista_equipos(reserva):
    if not reserva:
        return []
    resultado = []
    for item in reserva.get_unidades_seleccionadas_list():
        if not isinstance(item, dict):
            continue
        nombre = (item.get("nombre") or "").strip()
        codigo = (item.get("codigo") or "").strip()
        texto = " · ".join(valor for valor in (codigo, nombre) if valor)
        if texto and texto not in resultado:
            resultado.append(texto)
    if not resultado and reserva.equipo_codigo not in {
        "", "ESPACIO", "ESPACIOS", "SOFTWARE", "SERVICIO", "MULTI"
    }:
        resultado.append(
            " · ".join(
                valor for valor in (reserva.equipo_codigo, reserva.equipo_nombre) if valor
            )
        )
    return resultado


def _lista_software(reserva):
    if not reserva:
        return []
    return list(
        reserva.software_solicitado.order_by("nombre", "pk").values_list("nombre", flat=True)
    )


def _lista_materiales(reserva):
    if not reserva:
        return []
    resultado = []
    for solicitud in reserva.consumibles_solicitados.select_related("consumible"):
        cantidad = solicitud.cantidad_aprobada or solicitud.cantidad_solicitada
        unidad = solicitud.consumible.unidad_medida or "unidad(es)"
        detalle = f" — {cantidad:g} {unidad}" if cantidad is not None else ""
        resultado.append(f"{solicitud.consumible.nombre}{detalle}")
    if not resultado and reserva.provision_consumibles == "propios":
        declaracion = next(
            (
                linea.strip()
                for linea in (reserva.requisitos_especiales or "").splitlines()
                if linea.strip().lower().startswith("material propio declarado")
            ),
            "",
        )
        resultado.append(
            declaracion
            or "Material propio declarado por el solicitante y pendiente de aprobación técnica"
        )
    if not resultado and reserva.provision_consumibles == "revision":
        resultado.append("Insumos por determinar durante la revisión técnica")
    return resultado


def _lineas_politica(valor):
    return [linea.strip() for linea in str(valor or "").splitlines() if linea.strip()]


def politicas_guia_desde_reserva(reserva):
    """Devuelve políticas que pertenecen a la unidad, no al autor de la guía."""
    reglamento = None
    if reserva and reserva.laboratorio_id:
        try:
            reglamento = reserva.laboratorio.reglamento_publico
        except Exception:
            reglamento = None
    seguridad = []
    if reglamento and reglamento.activo:
        seguridad.extend(_lineas_politica(reglamento.seguridad))
        seguridad.extend(_lineas_politica(reglamento.equipos_materiales))
    if not seguridad:
        seguridad = [
            "Cumplir la inducción y utilizar los elementos de protección requeridos.",
            "Verificar el estado del recurso antes de operarlo y reportar cualquier novedad.",
            "Detener la actividad y comunicar inmediatamente incidentes o condiciones inseguras.",
        ]

    provision = reserva.provision_consumibles if reserva else "ninguno"
    if provision == "unidad" and _lista_materiales(reserva):
        residuos = [
            "El laboratorio clasificará, registrará y dispondrá remanentes y residuos según los insumos aprobados y su procedimiento interno."
        ]
    elif provision == "propios":
        residuos = [
            "El ingreso, uso, retiro y disposición del material propio quedan sujetos a la aprobación e instrucciones del responsable técnico."
        ]
    elif provision == "revision":
        residuos = [
            "El responsable técnico definirá el manejo de residuos cuando determine los insumos autorizados para la actividad."
        ]
    else:
        residuos = [
            "No se prevén residuos asociados a insumos; se mantienen las obligaciones de orden, limpieza y reporte de novedades."
        ]
    return {"seguridad": seguridad, "manejo_residuos": residuos}


def datos_autocompletado_guia(actividad, reserva=None):
    """Construye datos verificables desde actividad, reserva y políticas de unidad."""
    carrera = actividad.get_carrera_display() if actividad.carrera else ""
    semestre = ""
    if reserva:
        carrera = (
            reserva.get_carrera_beneficiaria_display()
            if reserva.carrera_beneficiaria
            else carrera
        ) or (
            reserva.get_carrera_solicitante_display()
            if reserva.carrera_solicitante else ""
        )
        semestre = (
            reserva.get_nivel_academico_solicitante_display()
            if reserva.nivel_academico_solicitante else ""
        )
    carrera_semestre = " · ".join(valor for valor in (carrera, semestre) if valor)
    docente = (
        (reserva.responsable_actividad if reserva else "")
        or actividad.responsable
        or _nombre_usuario(actividad.creado_por)
    )
    asignatura = (
        (reserva.referencia_actividad if reserva else "") or actividad.nombre
    )
    categoria = (
        reserva.get_proposito_codigo_display()
        if reserva and reserva.proposito_codigo
        else actividad.get_proposito_codigo_display()
    )
    datos = {
        "titulo": f"Guía de práctica: {actividad.nombre}",
        "codigo_guia": _codigo_guia(actividad),
        "asignatura": asignatura,
        "carrera_semestre": carrera_semestre,
        "docente_responsable": docente,
        "categoria_uso": categoria,
        "duracion": _duracion_reserva(reserva),
        "maximo_estudiantes": reserva.numero_participantes if reserva else "",
        "equipos": _lista_equipos(reserva),
        "software": _lista_software(reserva),
        "materiales": _lista_materiales(reserva),
        "reactivos": [],
        "laboratorio": actividad.unidad.nombre if actividad.unidad else "",
        "reserva_fuente_id": reserva.pk if reserva else None,
        "reserva_fuente_codigo": reserva.codigo_reserva if reserva else "",
    }
    if reserva:
        datos.update(politicas_guia_desde_reserva(reserva))
    return datos


@transaction.atomic
def asegurar_borrador_guia_desde_reserva(reserva, *, usuario=None, guia_origen=None):
    """Crea el formato editable cuando una práctica nace desde una reserva."""
    actividad = reserva.actividad_catalogo
    if not actividad or reserva.proposito_codigo != "docencia_practica":
        return None, False
    guias = (
        GuiaActividadReserva.objects.select_for_update()
        .filter(actividad=actividad, es_estructurada=True, activo=True)
        .order_by("-numero_version", "-pk")
    )
    if reserva.vinculacion_actividad not in {"manual", "clonada"}:
        # Quien reserva una actividad del catálogo se apoya en la versión
        # publicada. Los borradores posteriores son trabajo de su autor: no se
        # atribuyen a la reserva ni mandan a nadie a terminarlos.
        return guias.filter(estado_publicacion="publicada").first(), False
    existente = guias.first()
    if existente:
        return existente, False

    datos = datos_autocompletado_guia(actividad, reserva)
    contenido = deepcopy(guia_origen.contenido) if guia_origen else {}
    contenido.update({
        clave: datos.get(clave, "")
        for clave in (
            "asignatura", "carrera_semestre", "docente_responsable",
            "categoria_uso", "duracion", "maximo_estudiantes", "equipos", "software",
            "materiales", "reactivos", "laboratorio", "reserva_fuente_id",
            "reserva_fuente_codigo",
        )
    })
    contenido.pop('firma_elaborador', None)
    valores_iniciales = {
        "resultado_aprendizaje": "",
        "objetivos": "",
        "fundamento_teorico": "",
        "medidas_seguridad": datos.get("seguridad", []),
        "formato_procedimiento": "numerado",
        "procedimiento": [],
        "resultados_esperados": "",
        "criterios_evaluacion": "",
        "manejo_residuos": datos.get("manejo_residuos", []),
        "bibliografia": [],
    }
    for clave, valor in valores_iniciales.items():
        contenido.setdefault(clave, valor)
    contenido["origen_campos"] = {
        clave: "reserva" for clave in (
            "asignatura", "carrera_semestre", "docente_responsable",
            "categoria_uso", "duracion", "maximo_estudiantes",
            "equipos", "software", "materiales", "laboratorio",
        )
    }
    guia = GuiaActividadReserva.objects.create(
        actividad=actividad,
        titulo=datos["titulo"],
        descripcion=actividad.descripcion,
        codigo_guia=datos["codigo_guia"],
        numero_version=1,
        es_estructurada=True,
        guia_origen=guia_origen,
        contenido=contenido,
        estado_publicacion="borrador",
        visibilidad="participantes",
        subido_por=usuario or reserva.usuario,
    )
    return guia, True
