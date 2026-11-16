"""Proyección acotada del expediente; no autoriza equipos ni modifica registros."""

from django.db.models import Q
from django.urls import reverse

from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.reservas.models.reservas import Reserva

CAMPOS_PLAN = (
    "id",
    "codigo",
    "tema",
    "estado",
    "fecha",
    "hora_inicio",
    "hora_fin",
    "creado_por_id",
    "requiere_guia",
    "es_version_vigente",
    "guia_id",
    "guia__titulo",
    "guia__numero_version",
    "guia__estado_publicacion",
    "guia__activo",
    "guia__actividad_id",
    "reserva_id",
    "reserva__codigo_reserva",
    "reserva__estado",
    "reserva__resultado_cierre",
    "reserva__laboratorio_id",
    "reserva__actividad_catalogo_id",
    "ejecucion__id",
    "ejecucion__estado",
    "ejecucion__resultado",
    "ejecucion__eliminado_en",
    "ejecucion__fecha_ejecucion",
    "ejecucion__estudiantes_asistentes",
    "ejecucion__tuvo_incidente",
)


def planes_visibles(usuario, unidad, actividad, operador=False):
    planes = PlanificacionPractica.objects.filter(
        unidad=unidad, actividad=actividad, eliminado_en__isnull=True
    )
    if not operador:
        planes = planes.filter(
            Q(creado_por=usuario) | Q(actividad__participantes_autorizados=usuario)
        ).distinct()
    return planes


def resumir_plan(fila, unidad, actividad, usuario, operador=False):
    """Mantiene la misma autorización de escritura que el expediente institucional."""
    reserva_valida = bool(
        fila["reserva_id"]
        and fila["reserva__laboratorio_id"] == unidad.pk
        and fila["reserva__actividad_catalogo_id"] in {None, actividad.pk}
    )
    guia_valida = bool(fila["guia_id"] and fila["guia__actividad_id"] == actividad.pk)
    hay_ejecucion = bool(
        fila["ejecucion__id"] and fila["ejecucion__eliminado_en"] is None
    )
    url = reverse("detalle_planificacion_practica", args=[unidad.slug, fila["id"]])
    editable = bool(
        fila["estado"] == "aprobada"
        and reserva_valida
        and (operador or fila["creado_por_id"] == usuario.pk)
        and (
            not fila["ejecucion__id"]
            or (
                hay_ejecucion and fila["ejecucion__estado"] in {"borrador", "observada"}
            )
        )
    )
    guia = (
        {
            "titulo": fila["guia__titulo"],
            "version": fila["guia__numero_version"],
            "estado": fila["guia__estado_publicacion"],
            "activa": fila["guia__activo"],
            "estado_label": "Publicada"
            if fila["guia__estado_publicacion"] == "publicada"
            else "Pendiente de publicación",
            "url": reverse("ver_guia_actividad", args=[fila["guia_id"]]),
        }
        if guia_valida
        else None
    )
    reserva = (
        {
            "codigo": fila["reserva__codigo_reserva"],
            "estado": fila["reserva__estado"],
            "estado_label": dict(Reserva.ESTADO_CHOICES).get(
                fila["reserva__estado"], "Estado no reconocido"
            ),
            "resultado_label": dict(Reserva.RESULTADO_CIERRE_CHOICES).get(
                fila["reserva__resultado_cierre"], "Sin cierre"
            ),
        }
        if reserva_valida
        else None
    )
    ejecucion = (
        {
            "id": fila["ejecucion__id"],
            "estado": fila["ejecucion__estado"],
            "estado_label": dict(EjecucionPractica.ESTADOS).get(
                fila["ejecucion__estado"], "Estado no reconocido"
            ),
            "resultado": fila["ejecucion__resultado"],
            "resultado_label": dict(EjecucionPractica.RESULTADOS).get(
                fila["ejecucion__resultado"], "Sin resultado"
            ),
            "fecha": fila["ejecucion__fecha_ejecucion"],
            "asistentes": fila["ejecucion__estudiantes_asistentes"],
            "incidente": fila["ejecucion__tuvo_incidente"],
            "efectiva": fila["ejecucion__estado"] == "validada"
            and fila["ejecucion__resultado"] == "ejecutada",
        }
        if hay_ejecucion
        else None
    )
    return {
        **{
            k: fila[k]
            for k in (
                "id",
                "codigo",
                "tema",
                "fecha",
                "hora_inicio",
                "hora_fin",
                "estado",
            )
        },
        "estado_label": dict(PlanificacionPractica.ESTADOS).get(
            fila["estado"], "Estado no reconocido"
        ),
        "vigente": fila["es_version_vigente"],
        "requiere_guia": fila["requiere_guia"],
        "url": url,
        "ejecucion_url": reverse(
            "editar_ejecucion_practica", args=[unidad.slug, fila["id"]]
        )
        if editable
        else "",
        "guia": guia,
        "reserva": reserva,
        "ejecucion": ejecucion,
        "reserva_codigo": reserva["codigo"] if reserva else "Sin vincular",
        "reserva_estado_label": reserva["estado_label"] if reserva else "Pendiente",
        "ejecucion_estado_label": ejecucion["estado_label"]
        if ejecucion
        else "Sin registro",
    }


def controles_expediente(expediente):
    """Estados documentales de una sesión, distintos de una autorización física."""
    plan = expediente or {}
    reserva, guia, ejecucion = (
        plan.get("reserva"),
        plan.get("guia"),
        plan.get("ejecucion"),
    )
    publicada = bool(guia and guia["activa"] and guia["estado"] == "publicada")
    cerrado = bool(ejecucion and ejecucion["estado"] == "validada")
    efectivo = bool(ejecucion and ejecucion["efectiva"])
    inicio = bool(reserva and reserva["estado"] in {"en_proceso", "completada"})
    return [
        {
            "id": "recursos",
            "titulo": "Verificar maquetas y recursos",
            "estado": "registrado" if inicio else "pendiente",
            "detalle": "La reserva registra inicio o cierre; consulta los recursos y condiciones de esa sesión. No acredita aptitud para una sesión futura."
            if inicio
            else "Revisar existencia, disponibilidad, mantenimiento y condiciones antes del inicio. Esta pantalla no autoriza equipos.",
        },
        {
            "id": "seguridad",
            "titulo": "Seguridad e inducción",
            "estado": "registrado" if inicio else "pendiente",
            "detalle": "Consulta los ingresos y habilitaciones correspondientes a la reserva iniciada. El estado documental no certifica seguridad física."
            if inicio
            else "Revisar riesgos, supervisión y habilitaciones individuales de la sesión antes del ingreso.",
        },
        {
            "id": "guia",
            "titulo": "Actividad y guía institucional",
            "estado": "registrado"
            if publicada
            else "no_aplica"
            if plan and not plan.get("requiere_guia")
            else "pendiente",
            "detalle": "Guía publicada vinculada al expediente seleccionado."
            if publicada
            else "La planificación no exige guía."
            if plan and not plan.get("requiere_guia")
            else "Seleccionar una guía publicada de la actividad; una guía de otro expediente no completa esta condición.",
        },
        {
            "id": "plan",
            "titulo": "Reserva y planificación",
            "estado": "registrado"
            if plan.get("estado") == "aprobada" and reserva
            else "pendiente",
            "detalle": "Planificación aprobada con reserva vinculada; su estado y horario se muestran en el expediente."
            if plan.get("estado") == "aprobada" and reserva
            else "Seleccionar una planificación aprobada y vincular su reserva. Tener un borrador no programa una sesión.",
        },
        {
            "id": "ejecucion",
            "titulo": "Ejecución y evidencias",
            "estado": "verificado"
            if cerrado
            else "registrado"
            if ejecucion
            else "pendiente",
            "detalle": "Ejecución validada; el resultado puede ser realizado, reprogramado o cancelado. Las evidencias se consultan por el expediente."
            if cerrado
            else "Ejecución registrada y pendiente de validación; consulta su estado y adjuntos."
            if ejecucion
            else "Registrar lo ocurrido y aportar evidencias mediante el expediente seleccionado.",
        },
        {
            "id": "reporte",
            "titulo": "Cierre y reportes",
            "estado": "verificado"
            if efectivo
            else "registrado"
            if cerrado
            else "pendiente",
            "detalle": "Sólo las ejecuciones validadas y realizadas integran el uso efectivo. Este expediente cumple ambas condiciones."
            if efectivo
            else "Cierre validado sin uso efectivo: se conserva como cancelación o reprogramación."
            if cerrado
            else "Sólo las ejecuciones validadas y realizadas integran el uso efectivo; los estados pendientes no se contabilizan como práctica realizada.",
        },
    ]


def proxima_accion(expediente, operador=False):
    if not expediente:
        return None
    estado, ejecucion = expediente["estado"], expediente["ejecucion"]
    if estado in {"borrador", "observada"}:
        titulo, detalle = (
            "Completar la planificación",
            "Revisar la guía, la reserva y las observaciones antes de enviar la planificación.",
        )
    elif estado == "revision":
        titulo, detalle = (
            "Revisar la planificación" if operador else "Consultar la revisión",
            "La aprobación se realiza en el expediente institucional por el personal autorizado.",
        )
    elif estado == "archivada" or not expediente["vigente"]:
        titulo, detalle = (
            "Consultar el histórico",
            "Esta versión conserva su documentación; selecciona la vigente para continuar.",
        )
    elif not expediente["reserva"]:
        titulo, detalle = (
            "Vincular la reserva",
            "Completar la vinculación antes de registrar la ejecución.",
        )
    elif ejecucion and ejecucion["estado"] == "validada":
        titulo, detalle = (
            "Revisar cierre y evidencias",
            "Consulta el resultado validado y sus adjuntos; una cancelación no constituye uso efectivo.",
        )
    elif ejecucion and ejecucion["estado"] == "revision":
        titulo, detalle = (
            "Validar la ejecución" if operador else "Consultar la revisión de la ejecución",
            "Revisar resultado y evidencias por el circuito institucional.",
        )
    elif expediente["ejecucion_url"]:
        return {
            "titulo": "Registrar ejecución" if not ejecucion else "Completar ejecución",
            "detalle": "Registrar observaciones y evidencias reales de la sesión; no convierte la simulación en uso físico.",
            "url": expediente["ejecucion_url"],
            "target_top": True,
        }
    else:
        titulo, detalle = (
            "Consultar el expediente",
            "El autor o el personal autorizado completa el registro.",
        )
    return {
        "titulo": titulo,
        "detalle": detalle,
        "url": expediente["url"],
        "target_top": True,
    }
