"""Integración de una sola fuente entre reserva, planificación y ejecución."""

from django.db import transaction
from django.utils import timezone

from apps.reservas.models.reservas import GuiaActividadReserva, RegistroParticipanteReserva
from apps.formacion.models.practicas import PlanificacionPractica
from apps.recursos.models.unidades import UnidadEquipo


class DocumentacionReservaPendiente(ValueError):
    """La reserva necesita cerrar su documento antes de avanzar de etapa."""

    def __init__(self, message, *, estado_documental=None):
        super().__init__(message)
        self.estado_documental = estado_documental or {}


def es_reserva_de_practica(reserva):
    """Indica si la solicitud debe alimentar la planificación de uso del laboratorio.

    Toda reserva en la que el solicitante utilizará recursos constituye una
    planificación, aunque no necesite guía o actividad formal. Los servicios
    encargados usan su propia orden de servicio.
    """
    return reserva.tipo_solicitud != "servicio"


def guia_vigente_para(actividad, *, estructurada=None):
    queryset = GuiaActividadReserva.objects.filter(
        actividad=actividad,
        estado_publicacion="publicada",
        activo=True,
    )
    # La guía general del período y las guías de cada sesión no autorizan otra sesión.
    queryset = queryset.filter(sesion__isnull=True).exclude(alcance="periodo")
    if estructurada is not None:
        queryset = queryset.filter(es_estructurada=estructurada)
    return (
        queryset
        .order_by("-es_vigente", "-numero_version", "-pk")
        .first()
    )


def guias_vencidas_sin_enviar(usuario):
    """Guías de prácticas anteriores que el docente aún no envió.

    Solo cuentan reservas que llegaron a una etapa operativa. Las solicitudes
    rechazadas, canceladas o vencidas administrativamente no generan una deuda
    documental para el docente, y reutilizar una guía publicada tampoco crea
    una entrega nueva.
    """
    if not getattr(usuario, 'is_authenticated', False):
        return GuiaActividadReserva.objects.none()
    return (
        GuiaActividadReserva.objects.filter(
            actividad__reservas__usuario=usuario,
            actividad__reservas__tipo_solicitud__in={'equipo', 'espacio', 'software', 'recursos'},
            actividad__reservas__proposito_codigo='docencia_practica',
            actividad__reservas__vinculacion_actividad__in={'manual', 'clonada'},
            actividad__reservas__fecha__lt=timezone.localdate(),
            actividad__reservas__estado__in={'confirmada', 'en_proceso', 'completada'},
            estado_publicacion__in={'borrador', 'rechazada'},
            activo=True,
        )
        .select_related('actividad', 'actividad__unidad')
        .distinct()
    )


def _estado_documental_sesion(reserva):
    """Resume la compuerta documental sin alterar la reserva ni su guía.

    La elección del usuario es la fuente de la obligación: una reserva sin guía
    y una orden de servicio pueden avanzar directamente; una actividad docente
    creada con guía o elegida desde el catálogo necesita una versión
    estructurada aprobada y activa.
    """
    if reserva.tipo_solicitud == "servicio":
        return {
            "aplica": False,
            "requiere_guia": False,
            "lista": True,
            "estado": "no_aplica",
            "etiqueta": "No aplica",
            "detalle": "Las órdenes de servicio utilizan su expediente técnico.",
            "guia_id": None,
            "actividad_id": None,
        }

    plan = (
        PlanificacionPractica.objects.filter(reserva_id=reserva.pk)
        .select_related("actividad", "guia")
        .first()
    )
    actividad = (plan.actividad if plan else None) or reserva.actividad_catalogo
    guia_aprobada = None
    exige_formato_estructurado = reserva.vinculacion_actividad == "manual"
    if plan and plan.guia_id:
        guia_plan = plan.guia
        if (
            guia_plan.activo
            and guia_plan.estado_publicacion == "publicada"
            and (not exige_formato_estructurado or guia_plan.es_estructurada)
        ):
            guia_aprobada = guia_plan
    if guia_aprobada is None and actividad:
        guia_aprobada = guia_vigente_para(
            actividad,
            estructurada=True if exige_formato_estructurado else None,
        )

    requiere_desde_reserva = bool(
        reserva.proposito_codigo == "docencia_practica"
        and reserva.vinculacion_actividad in {"manual", "catalogo"}
    )
    requiere_guia = bool(
        requiere_desde_reserva or (plan and plan.requiere_guia)
    )
    if not requiere_guia:
        return {
            "aplica": True,
            "requiere_guia": False,
            "lista": True,
            "estado": "no_aplica",
            "etiqueta": "No requiere guía",
            "detalle": "El solicitante registró esta actividad como uso sin guía.",
            "guia_id": None,
            "actividad_id": actividad.pk if actividad else None,
        }
    guia_trabajo = None
    if actividad:
        guias_trabajo = GuiaActividadReserva.objects.filter(
            actividad=actividad,
            activo=True,
        )
        if exige_formato_estructurado:
            guias_trabajo = guias_trabajo.filter(es_estructurada=True)
        guia_trabajo = guias_trabajo.order_by('-numero_version', '-pk').first()

    if guia_aprobada:
        return {
            "aplica": True,
            "requiere_guia": True,
            "lista": True,
            "estado": "aprobada",
            "etiqueta": "Guía aprobada",
            "detalle": (
                f"Versión {guia_aprobada.numero_version} aprobada y vinculada al expediente."
            ),
            "guia_id": guia_aprobada.pk,
            "actividad_id": actividad.pk if actividad else None,
            "lista_para_aprobar": True,
        }

    estado = guia_trabajo.estado_publicacion if guia_trabajo else "faltante"
    completa_para_aprobar = bool(
        guia_trabajo
        and estado in {'borrador', 'revision'}
        and not guia_trabajo.secciones_faltantes()
    )
    etiquetas = {
        "borrador": "Guía en borrador",
        "revision": "Guía en revisión",
        "rechazada": "Guía con observaciones",
        "archivada": "Guía archivada",
        "faltante": "Guía pendiente de crear",
    }
    detalles = {
        "borrador": "El autor debe completar la guía y enviarla a revisión.",
        "revision": (
            "La guía fue enviada y espera la decisión del laboratorio. Mientras no se "
            "apruebe puedes corregirla, descargar el PDF, firmarlo con FirmaEC y cargar "
            "la versión firmada."
        ),
        "rechazada": "El autor debe corregir las observaciones y volver a enviarla.",
        "archivada": "Debe existir una versión activa antes de aprobar la reserva.",
        "faltante": "No existe una guía estructurada asociada a esta actividad.",
    }
    return {
        "aplica": True,
        "requiere_guia": True,
        "lista": False,
        "estado": estado,
        "etiqueta": etiquetas.get(estado, "Guía pendiente"),
        "detalle": detalles.get(
            estado,
            "La guía todavía no cuenta con aprobación documental.",
        ),
        "guia_id": guia_trabajo.pk if guia_trabajo else None,
        "actividad_id": actividad.pk if actividad else None,
        "lista_para_aprobar": completa_para_aprobar,
    }


def guia_general_de(reserva):
    """La guía general del período de una sesión programada."""
    programacion = reserva.programacion
    if programacion is None or not reserva.actividad_catalogo_id:
        return None
    return (
        GuiaActividadReserva.objects.filter(
            actividad=reserva.actividad_catalogo,
            alcance="periodo",
            es_estructurada=True,
            activo=True,
        )
        .order_by("-numero_version", "-pk")
        .first()
    )


def estado_documental_reserva(reserva):
    """La compuerta documental con la guía general del período, cuando la hay.

    La guía general aprobada permite aprobar las sesiones del período; la
    guía de cada sesión, aprobada, permite ejecutarla.
    """
    estado = _estado_documental_sesion(reserva)
    general = guia_general_de(reserva)
    if general is None:
        estado["general"] = None
        estado.setdefault("lista_para_aprobar", estado["lista"])
        return estado
    lista_general = general.estado_publicacion == "publicada" and general.activo
    estado["general"] = {
        "guia_id": general.pk,
        "estado": general.estado_publicacion,
        "lista": lista_general,
        "etiqueta": "Guía general aprobada" if lista_general else "Guía general del período pendiente",
        "detalle": (
            f"Versión {general.numero_version} aprobada; cada sesión necesita además su propia guía."
            if lista_general
            else "El docente debe completar la guía general del período y la unidad aprobarla antes de aprobar sesiones."
        ),
    }
    estado["lista_para_aprobar"] = lista_general
    if not estado["lista"]:
        estado["etiqueta"] = f"Guía de la sesión: {estado['etiqueta'].lower()}"
    return estado


def validar_compuerta_documental(reserva, accion):
    """Impide aprobar o ejecutar mientras falte una guía obligatoria."""
    if accion not in {"aprobar", "iniciar", "completar"}:
        return estado_documental_reserva(reserva)
    estado = estado_documental_reserva(reserva)
    if estado["lista_para_aprobar"] if accion == "aprobar" else estado["lista"]:
        return estado
    general = estado.get("general")
    if accion == "aprobar" and general and not general["lista"]:
        raise DocumentacionReservaPendiente(
            f"No se puede aprobar la reserva: {general['etiqueta'].lower()}. {general['detalle']}",
            estado_documental=estado,
        )
    acciones = {
        "aprobar": "aprobar la reserva",
        "iniciar": "iniciar la atención",
        "completar": "completar la ejecución",
    }
    raise DocumentacionReservaPendiente(
        f"No se puede {acciones[accion]}: {estado['etiqueta'].lower()}. "
        f"{estado['detalle']}",
        estado_documental=estado,
    )


def _valor_display(objeto, campo):
    metodo = getattr(objeto, f"get_{campo}_display", None)
    valor = getattr(objeto, campo, "")
    return metodo() if valor and callable(metodo) else valor or ""


def _categoria_desde_reserva(reserva):
    proposito = reserva.proposito_codigo or (
        reserva.actividad_catalogo.proposito_codigo
        if reserva.actividad_catalogo_id
        else ""
    )
    return {
        "docencia_practica": "docencia",
        "investigacion_innovacion": "proyecto",
        "titulacion": "tesis",
        "vinculacion": "proyecto",
        "servicio_cientifico_tecnologico": "servicio",
        "capacitacion": "otro",
    }.get(proposito, "otro")


def _estado_plan_desde_reserva(reserva, *, requiere_guia, guia):
    documentacion_lista = bool(guia) or not requiere_guia
    if reserva.estado in {
        "rechazada", "cancelada", "vencida", "no_presentado", "no_atendida",
    }:
        return "archivada"
    if reserva.estado in {"confirmada", "en_proceso", "completada"}:
        return "aprobada" if documentacion_lista else "borrador"
    return "revision" if documentacion_lista else "borrador"


def datos_planificacion_desde_reserva(reserva, *, actor=None):
    actividad = reserva.actividad_catalogo
    guia = (
        guia_vigente_para(
            actividad,
            estructurada=(
                True if reserva.vinculacion_actividad == "manual" else None
            ),
        )
        if actividad
        else None
    )
    proposito = reserva.proposito_codigo or (
        actividad.proposito_codigo if actividad else ""
    )
    requiere_guia = bool(
        proposito == "docencia_practica"
        and (
            reserva.vinculacion_actividad in {"manual", "catalogo"}
            or guia
        )
    )
    contenido = guia.contenido if guia and isinstance(guia.contenido, dict) else {}
    autor = reserva.usuario or actor
    docente = (
        reserva.responsable_actividad
        or (actividad.responsable if actividad else "")
        or (autor.get_full_name() if autor else "")
        or (autor.username if autor else "Responsable por asignar")
    )
    carrera = (
        _valor_display(reserva, "carrera_beneficiaria")
        or _valor_display(reserva, "carrera_solicitante")
        or (_valor_display(actividad, "carrera") if actividad else "")
    )
    nombre_actividad = (
        reserva.referencia_actividad
        or (actividad.nombre if actividad else "")
        or reserva.titulo_solicitud
        or reserva.equipo_nombre
        or "Uso planificado del laboratorio"
    )
    resultado = (
        contenido.get("resultado_aprendizaje")
        or (actividad.descripcion if actividad else "")
        or reserva.descripcion_proyecto
        or (
            "Resultado por completar antes de enviar la planificación."
            if requiere_guia
            else "Uso de recursos conforme al alcance registrado en la reserva."
        )
    )
    estado = _estado_plan_desde_reserva(
        reserva,
        requiere_guia=requiere_guia,
        guia=guia,
    )
    return {
        "actividad": actividad,
        "guia": guia,
        "requiere_guia": requiere_guia,
        "unidad": reserva.laboratorio,
        "reserva": reserva,
        "fecha": reserva.fecha,
        "hora_inicio": reserva.hora_inicio,
        "hora_fin": reserva.hora_fin,
        "carrera": carrera,
        "semestre": _valor_display(reserva, "nivel_academico_solicitante"),
        # La asignatura la declara el docente en la guia; el nombre de la
        # actividad es la practica, no la asignatura.
        "asignatura": (
            (guia.contenido or {}).get("asignatura")
            if guia is not None and isinstance(guia.contenido, dict)
            else ""
        ) or nombre_actividad,
        "docente_tutor": docente,
        "tema": (reserva.titulo_solicitud or nombre_actividad)[:240],
        "resultado_aprendizaje": resultado,
        "estudiantes_planificados": max(1, reserva.numero_participantes or 1),
        "categoria_uso": _categoria_desde_reserva(reserva),
        "responsable_tecnico": reserva.responsable_asignado,
        "observaciones": reserva.requisitos_especiales or "",
        "creado_por": autor,
        "estado": estado,
    }


@transaction.atomic
def sincronizar_planificacion_reserva(reserva, *, actor=None):
    """Crea la planificación al aprobar o sincroniza sus datos operativos editables."""
    if not es_reserva_de_practica(reserva):
        return None, False, False
    datos = datos_planificacion_desde_reserva(reserva, actor=actor)
    if not datos["creado_por"]:
        return None, False, False
    # Las sesiones recurrentes se crean copiando la reserva principal. Consultar
    # por la clave evita reutilizar accidentalmente la caché de la relación
    # uno-a-uno que pueda venir en una instancia copiada.
    plan = PlanificacionPractica.objects.filter(reserva_id=reserva.pk).first()
    if plan:
        if plan.estado not in {"borrador", "revision", "observada"}:
            return plan, False, False
        cambios = []
        for campo in (
            "fecha",
            "hora_inicio",
            "hora_fin",
            "estudiantes_planificados",
            "responsable_tecnico",
            "requiere_guia",
            "estado",
        ):
            valor = datos[campo]
            if getattr(plan, campo) != valor:
                setattr(plan, campo, valor)
                cambios.append(campo)
        if not plan.actividad_id and datos["actividad"]:
            plan.actividad = datos["actividad"]
            cambios.append("actividad")
        if not plan.guia_id and datos["guia"]:
            plan.guia = datos["guia"]
            cambios.append("guia")
        if cambios:
            plan.full_clean()
            plan.save(update_fields=[*cambios, "actualizado_en"])
        return plan, False, bool(cambios)

    plan = PlanificacionPractica(**datos)
    plan.full_clean()
    plan.save()
    return plan, True, True


def asegurar_participantes_reserva(reserva):
    """Completa registros nominales faltantes sin reemplazar fotografías existentes."""
    usuarios = []
    if reserva.usuario_id:
        usuarios.append((reserva.usuario, "solicitante"))
    usuarios.extend((usuario, "participante") for usuario in reserva.participantes.all())
    for usuario, rol in usuarios:
        perfil = getattr(usuario, "profile", None)
        RegistroParticipanteReserva.objects.get_or_create(
            reserva=reserva,
            usuario=usuario,
            defaults={
                "rol": rol,
                "nombre": usuario.get_full_name() or usuario.username,
                "correo": usuario.email or "",
                "tipo_usuario": getattr(perfil, "tipo_usuario", "") or "",
                "facultad": getattr(perfil, "facultad", "") or "",
                "carrera": getattr(perfil, "carrera", "") or "",
                "nivel_academico": getattr(perfil, "nivel_academico", "") or "",
                "institucion": getattr(perfil, "institucion", "") or "",
            },
        )


def construir_detalle_operativo(reserva, seleccion=None):
    """Devuelve datos serializables de los recursos y personas de la reserva."""
    seleccion = seleccion or {}
    unidades_crudas = [
        item for item in reserva.get_unidades_seleccionadas_list() if isinstance(item, dict)
    ]
    ids = []
    for item in unidades_crudas:
        try:
            ids.append(int(item.get("id")))
        except (TypeError, ValueError):
            continue
    unidades = {
        item.pk: item
        for item in UnidadEquipo.objects.filter(pk__in=ids).select_related("equipo")
    }
    equipos = []
    for item in unidades_crudas:
        try:
            unidad = unidades.get(int(item.get("id")))
        except (TypeError, ValueError):
            unidad = None
        identificador = str(unidad.pk if unidad else item.get("id") or item.get("codigo") or "")
        equipos.append(
            {
                "id": identificador,
                "codigo": unidad.codigo_unidad if unidad else item.get("codigo", ""),
                "nombre": unidad.equipo.nombre if unidad else item.get("nombre") or reserva.equipo_nombre,
                "ubicacion": unidad.ubicacion_especifica if unidad else item.get("ubicacion", ""),
                "estado": unidad.get_estado_unidad_display() if unidad else item.get("estado", "Por verificar"),
            }
        )
    if not equipos and reserva.equipo_codigo not in {"", "ESPACIO", "ESPACIOS", "SOFTWARE", "SERVICIO", "MULTI"}:
        equipos.append(
            {
                "id": f"legacy:{reserva.equipo_codigo}",
                "codigo": reserva.equipo_codigo,
                "nombre": reserva.equipo_nombre,
                "ubicacion": "",
                "estado": "Por verificar",
            }
        )

    def filas(queryset, nombre):
        return [
            {"id": str(item.pk), "nombre": getattr(item, nombre), "codigo": getattr(item, "codigo", "")}
            for item in queryset
        ]

    software = filas(reserva.software_solicitado.all(), "nombre")
    espacios = filas(reserva.espacios_solicitados.all(), "nombre")
    servicios = filas(reserva.servicios_solicitados.all(), "nombre")

    for clave, elementos in (
        ("equipos", equipos),
        ("software", software),
        ("espacios", espacios),
        ("servicios", servicios),
    ):
        elegidos = seleccion.get(clave)
        if elegidos is not None:
            elementos[:] = [item for item in elementos if str(item["id"]) in elegidos]

    participantes = [
        {
            "id": str(item.pk),
            "usuario_id": item.usuario_id,
            "nombre": item.nombre,
            "correo": item.correo,
            "rol": item.get_rol_display(),
            "asistencia": item.get_asistencia_display(),
            "asistencia_codigo": item.asistencia,
        }
        for item in reserva.registros_participantes.order_by("rol", "nombre")
    ]
    consumibles = [
        {
            "id": str(item.pk),
            "nombre": item.consumible.nombre,
            "unidad": item.consumible.unidad_medida or "unidades",
            "solicitada": str(item.cantidad_solicitada) if item.cantidad_solicitada is not None else "",
            "aprobada": str(item.cantidad_aprobada) if item.cantidad_aprobada is not None else "",
            "consumida": str(item.cantidad_consumida),
        }
        for item in reserva.consumibles_solicitados.select_related("consumible")
    ]
    return {
        "equipos": equipos,
        "software": software,
        "espacios": espacios,
        "servicios": servicios,
        "participantes": participantes,
        "consumibles": consumibles,
    }


def resumen_recursos(detalle):
    partes = []
    for clave, etiqueta in (
        ("equipos", "Equipos"),
        ("software", "Software"),
        ("espacios", "Espacios"),
        ("servicios", "Servicios"),
    ):
        nombres = [item.get("nombre", "") for item in detalle.get(clave, []) if item.get("nombre")]
        if nombres:
            partes.append(f"{etiqueta}: {', '.join(nombres)}")
    consumibles = [
        f"{item['nombre']} ({item['consumida']} {item['unidad']})"
        for item in detalle.get("consumibles", [])
        if item.get("consumida") not in {"", "0", "0.000"}
    ]
    if consumibles:
        partes.append(f"Insumos: {', '.join(consumibles)}")
    return "; ".join(partes)
