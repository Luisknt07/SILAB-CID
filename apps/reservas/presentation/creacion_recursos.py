"""Selección validada de recursos y catálogos para crear una reserva.

Las funciones reciben estructuras de formulario, archivos y objetos del dominio;
no construyen respuestas HTTP ni escriben reservas. Esto mantiene en la vista la
adaptación del protocolo y permite probar las reglas de cada unidad directamente.
"""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import ReservaConsumible
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo

from apps.reservas.presentation.adjuntos import validar_archivos_tecnicos
from apps.reservas.presentation.proceso import validar_cobertura_del_proceso


@dataclass(frozen=True)
class RecursosFisicosSolicitud:
    responsable: Any
    recursos: list[dict]
    equipos: list[Any]
    software: list[Any]
    espacios: list[Any]
    espacios_publicados: list[Any]
    alcance_espacio: str
    requiere_espacio: bool
    reserva_unidad_completa: bool
    solicito_software: bool
    solicito_equipo: bool
    solicito_espacio: bool
    requisitos_especiales: str


@dataclass(frozen=True)
class CatalogosSolicitud:
    consumibles: list[tuple]
    servicios: list[Any]
    tiene_catalogo_servicios: bool
    archivos: list[Any]
    indicaciones_archivos: list[str]


def normalizar_ids_post(post, nombre):
    """Acepta campos repetidos o una lista JSON y devuelve ids únicos ordenados."""
    valores = post.getlist(nombre)
    if len(valores) == 1:
        try:
            decodificado = json.loads(valores[0])
        except (TypeError, ValueError, json.JSONDecodeError):
            decodificado = None
        if isinstance(decodificado, list):
            valores = decodificado
    try:
        ids = [int(valor) for valor in valores if str(valor).strip()]
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"La selección de {nombre.replace('_', ' ')} no es válida"
        ) from error
    if len(ids) != len(set(ids)):
        raise ValueError(
            f"No se puede seleccionar dos veces el mismo {nombre.replace('_', ' ')}"
        )
    return ids


def validar_responsable(valor, unidad):
    if valor:
        raise ValueError(
            "La asignación del responsable corresponde a la administración del laboratorio"
        )
    # La asignación usa disponibilidad y carga activa de la unidad al aprobar.
    return None


def normalizar_recursos(unidades_json, unidad, tipo_solicitud, modalidad_servicio=""):
    requiere_equipo = tipo_solicitud == "equipo"
    permite_equipo = tipo_solicitud in {
        "equipo",
        "espacio",
        "software",
        "recursos",
    } or (tipo_solicitud == "servicio" and modalidad_servicio == "diseno_asistido")
    if requiere_equipo and not unidades_json:
        raise ValueError("Debe seleccionar al menos una unidad para la reserva")
    try:
        unidades = json.loads(unidades_json or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("Error en el formato de las unidades seleccionadas") from error
    if not isinstance(unidades, list) or (requiere_equipo and not unidades):
        raise ValueError("Debe seleccionar al menos una unidad para la reserva")
    if unidades and not permite_equipo:
        raise ValueError(
            "Los equipos solo pueden reservarse como recursos o como apoyo de un diseño asistido"
        )
    try:
        unidades_ids = [int(item["id"]) for item in unidades]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Error en el formato de las unidades seleccionadas") from error
    if len(unidades_ids) != len(set(unidades_ids)):
        raise ValueError("No se puede seleccionar dos veces el mismo recurso")

    recursos = list(
        UnidadEquipo.objects.publicos().filter(
            Q(laboratorios=unidad) | Q(laboratorio=unidad),
            id__in=unidades_ids,
            estado_unidad="disponible",
            activa=True,
        )
        .select_related("equipo")
        .distinct()
    )
    if len(recursos) != len(unidades_ids):
        ids_validos = {item.pk for item in recursos}
        raise ValueError(
            "Algunas unidades ya no están disponibles: "
            f"{sorted(set(unidades_ids) - ids_validos)}"
        )

    recursos_por_id = {item.pk: item for item in recursos}
    normalizados = []
    equipos_por_id = {}
    for recurso_id in unidades_ids:
        recurso = recursos_por_id[recurso_id]
        equipo = recurso.equipo
        equipos_por_id[equipo.pk] = equipo
        normalizados.append(
            {
                "id": recurso.pk,
                "codigo": recurso.codigo_unidad,
                "ubicacion": recurso.ubicacion_especifica or "No especificada",
                "equipo_id": equipo.pk,
                "equipo_codigo": equipo.codigo,
                "equipo_nombre": equipo.nombre,
            }
        )
    return normalizados, list(equipos_por_id.values())


def validar_software(post, unidad, tipo_solicitud, modalidad_servicio=""):
    valores = post.getlist("software_solicitado")
    permite_software = tipo_solicitud in {"espacio", "software", "recursos"} or (
        tipo_solicitud == "servicio" and modalidad_servicio == "diseno_asistido"
    )
    if not permite_software:
        if valores:
            raise ValueError(
                "El software solo puede reservarse como recurso o como apoyo de un diseño asistido"
            )
        return []
    if tipo_solicitud == "software" and not valores:
        raise ValueError("Selecciona al menos un software o licencia")
    try:
        ids = [int(value) for value in valores]
    except (TypeError, ValueError) as error:
        raise ValueError("La selección de software no es válida") from error
    if len(ids) != len(set(ids)):
        raise ValueError("No se puede seleccionar dos veces el mismo software")
    software = list(
        SoftwareDisponible.objects.filter(
            pk__in=ids,
            unidad=unidad,
            activo=True,
            requiere_reserva=True,
            licencias_disponibles__gt=0,
        ).prefetch_related("equipos_instalados")
    )
    if len(software) != len(ids):
        raise ValueError("Una licencia seleccionada no está disponible en esta unidad")
    return software


def incluir_software_propio_de_equipos(unidad, software, recursos):
    if not recursos:
        return software
    recursos_ids = {int(recurso["id"]) for recurso in recursos}
    conocidos = {programa.pk for programa in software}
    propios = (
        SoftwareDisponible.objects.filter(
            unidad=unidad,
            activo=True,
            uso_en_equipo="obligatorio",
            equipos_instalados__pk__in=recursos_ids,
        )
        .distinct()
        .order_by("nombre", "pk")
        .prefetch_related("equipos_instalados")
    )
    return list(software) + [
        programa for programa in propios if programa.pk not in conocidos
    ]


def validar_equipos_para_software(software, recursos):
    if not software:
        return
    recursos_ids = {int(recurso["id"]) for recurso in recursos or []}
    for programa in software:
        equipos_ids = {equipo.pk for equipo in programa.equipos_existentes}
        if programa.tipo_acceso == "instalacion" and not equipos_ids:
            raise ValueError(
                f"{programa.nombre} todavía no tiene configurado el equipo donde "
                "está instalado. Solicita al administrador completar esta relación"
            )
        if not equipos_ids:
            continue
        if not recursos_ids:
            raise ValueError(f"Selecciona el equipo donde ejecutarás {programa.nombre}")
        if recursos_ids.isdisjoint(equipos_ids):
            raise ValueError(
                f"Selecciona un equipo donde esté disponible {programa.nombre}"
            )


def validar_espacios(ids, unidad, *, permitido, requerido):
    publicados = EspacioReservable.objects.filter(
        unidad=unidad,
        activo=True,
        reservable=True,
    ).prefetch_related("equipos_asociados")
    if ids and not permitido:
        raise ValueError(
            "Las áreas o estaciones solo pueden reservarse como recursos o "
            "como apoyo de un servicio con diseño asistido"
        )
    espacios = list(publicados.filter(pk__in=ids))
    if len(espacios) != len(ids):
        raise ValueError("Un área o estación seleccionada ya no está disponible")
    if requerido and publicados.exists() and not espacios:
        raise ValueError("Selecciona el área o estación de trabajo que utilizarás")
    return espacios


def validar_equipos_para_espacios(espacios, recursos, *, reserva_unidad_completa=False):
    recursos_ids = {int(recurso["id"]) for recurso in recursos}
    if reserva_unidad_completa:
        return
    for espacio in espacios:
        if not espacio.requiere_recurso_tecnico:
            continue
        equipos_ids = {equipo.pk for equipo in espacio.equipos_existentes}
        if not equipos_ids:
            raise ValueError(
                f"{espacio.nombre} está configurada como área técnica, pero todavía "
                "no tiene equipos asociados. Solicita al administrador corregirla"
            )
        if recursos_ids.isdisjoint(equipos_ids):
            raise ValueError(
                f"Selecciona un equipo o software asociado a {espacio.nombre}. "
                "El mobiliario básico ya está incluido con el espacio"
            )


def validar_ubicacion_de_equipos(
    espacios,
    recursos,
    *,
    reserva_unidad_completa=False,
    espacios_publicados=(),
):
    if reserva_unidad_completa or not recursos:
        return
    espacios_ids = {espacio.pk for espacio in espacios}
    for recurso in recursos:
        recurso_id = int(recurso["id"])
        ubicaciones = [
            espacio
            for espacio in espacios_publicados
            if recurso_id
            in {equipo.pk for equipo in espacio.equipos_asociados.all()}
        ]
        if not ubicaciones or espacios_ids.intersection(
            espacio.pk for espacio in ubicaciones
        ):
            continue
        nombre = recurso.get("equipo_nombre") or "el equipo seleccionado"
        opciones = ", ".join(espacio.nombre for espacio in ubicaciones)
        raise ValueError(
            f"Selecciona el área donde utilizarás {nombre}. Ubicaciones válidas: "
            f"{opciones}"
        )


def intencion_recurso(post, nombre, *, disponible, respaldo=False):
    if nombre not in post:
        return bool(respaldo and disponible)
    declarado = post.get(nombre) in {"1", "true", "on", "si", "sí"}
    return bool(declarado and disponible)


def resolver_recursos_fisicos(
    post,
    *,
    unidad,
    configuracion,
    tipo_solicitud,
    modalidad_servicio,
    proposito_codigo,
    incluye_espacio_solicitado,
    requisitos_especiales,
):
    """Resuelve equipos, software y ocupación física sin escribir el expediente."""
    espacios_ids = normalizar_ids_post(post, "espacios_solicitados")
    alcance_espacio = post.get("alcance_espacio", "").strip()
    if alcance_espacio not in {
        "",
        "sin_espacio",
        "areas",
        "espacio_unico",
        "unidad_completa",
    }:
        raise ValueError("Selecciona un alcance válido para el espacio")
    servicio_asistido = (
        tipo_solicitud == "servicio" and modalidad_servicio == "diseno_asistido"
    )
    permite_espacios = tipo_solicitud in {
        "equipo",
        "espacio",
        "software",
        "recursos",
    } or servicio_asistido
    responsable = validar_responsable(post.get("responsable_asignado"), unidad)
    recursos, equipos = normalizar_recursos(
        post.get("unidades_seleccionadas"),
        unidad,
        tipo_solicitud,
        modalidad_servicio,
    )
    software = incluir_software_propio_de_equipos(
        unidad,
        validar_software(post, unidad, tipo_solicitud, modalidad_servicio),
        recursos,
    )
    software_adicional_ids = set(normalizar_ids_post(post, "software_adicional"))
    software_adicional = [
        programa for programa in software if programa.pk in software_adicional_ids
    ]
    validar_equipos_para_software(
        [
            programa
            for programa in software
            if programa.pk not in software_adicional_ids
        ],
        recursos,
    )
    if software_adicional and not recursos:
        raise ValueError(
            "Selecciona el equipo donde el laboratorio deberá habilitar el software adicional"
        )
    texto_software_adicional = post.get("software_adicional_texto", "").strip()[:300]
    if software_adicional or texto_software_adicional:
        partes = [programa.nombre for programa in software_adicional]
        if texto_software_adicional:
            partes.append(f"otro: {texto_software_adicional}")
        nota_software = "Software adicional por habilitar: " + ", ".join(partes)
        requisitos_especiales = (
            nota_software
            if not requisitos_especiales
            or requisitos_especiales == "Sin requisitos adicionales"
            else f"{requisitos_especiales} · {nota_software}"
        )

    requiere_espacio = bool(
        permite_espacios
        and (
            tipo_solicitud == "espacio"
            or servicio_asistido
            or recursos
            or software
            or incluye_espacio_solicitado
            or espacios_ids
        )
    )
    espacios_publicados = list(
        EspacioReservable.objects.filter(
            unidad=unidad,
            activo=True,
            reservable=True,
        )
        .prefetch_related("equipos_asociados")
        .order_by("orden", "nombre", "pk")
    )
    if (
        tipo_solicitud == "recursos"
        and permite_espacios
        and configuracion.reservas_espacios
        and espacios_publicados
    ):
        requiere_espacio = True
    if requiere_espacio and not configuracion.reservas_espacios:
        raise ValueError(
            "El equipo o recurso seleccionado requiere presencia física, pero "
            "la reserva de espacios no está habilitada para esta unidad"
        )
    if requiere_espacio:
        if not espacios_publicados:
            if alcance_espacio != "unidad_completa":
                alcance_espacio = "espacio_unico"
            espacios_ids = []
        elif len(espacios_publicados) == 1:
            if alcance_espacio == "unidad_completa":
                if espacios_ids:
                    raise ValueError(
                        "Para reservar la unidad completa no selecciones áreas individuales"
                    )
                espacios_ids = []
            else:
                alcance_espacio = "areas"
                if not espacios_ids:
                    espacios_ids = [espacios_publicados[0].pk]
        elif alcance_espacio == "unidad_completa":
            if espacios_ids:
                raise ValueError(
                    "Para reservar la unidad completa no selecciones áreas individuales"
                )
            espacios_ids = []
        else:
            alcance_espacio = "areas"
            if not espacios_ids:
                raise ValueError(
                    "Selecciona una o varias áreas, o indica que necesitas la unidad completa"
                )
    else:
        alcance_espacio = "sin_espacio"
        espacios_ids = []

    reserva_unidad_completa = alcance_espacio == "unidad_completa"
    if reserva_unidad_completa and proposito_codigo != "docencia_practica":
        raise ValueError(
            "La unidad completa se reserva para actividades docentes que ocupan todo el "
            "laboratorio; para otros usos selecciona las áreas que ocuparás y el sistema "
            "compartirá la capacidad disponible"
        )
    espacios = validar_espacios(
        espacios_ids,
        unidad,
        permitido=permite_espacios,
        requerido=requiere_espacio and alcance_espacio == "areas",
    )
    validar_equipos_para_espacios(
        espacios,
        recursos,
        reserva_unidad_completa=reserva_unidad_completa,
    )
    validar_ubicacion_de_equipos(
        espacios,
        recursos,
        reserva_unidad_completa=reserva_unidad_completa,
        espacios_publicados=espacios_publicados,
    )
    solicito_software = intencion_recurso(
        post,
        "solicito_software",
        disponible=bool(software),
        respaldo=bool(software),
    )
    solicito_equipo = intencion_recurso(
        post,
        "solicito_equipo",
        disponible=bool(recursos),
        respaldo=bool(recursos) and not software,
    )
    solicito_espacio = intencion_recurso(
        post,
        "solicito_espacio",
        disponible=requiere_espacio,
        respaldo=bool(incluye_espacio_solicitado and not recursos and not software),
    )
    return RecursosFisicosSolicitud(
        responsable=responsable,
        recursos=recursos,
        equipos=equipos,
        software=software,
        espacios=espacios,
        espacios_publicados=espacios_publicados,
        alcance_espacio=alcance_espacio,
        requiere_espacio=requiere_espacio,
        reserva_unidad_completa=reserva_unidad_completa,
        solicito_software=solicito_software,
        solicito_equipo=solicito_equipo,
        solicito_espacio=solicito_espacio,
        requisitos_especiales=requisitos_especiales,
    )


def validar_consumibles(valor_json, unidad):
    if not valor_json:
        return []
    try:
        items = json.loads(valor_json)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("El formato de materiales y consumibles no es válido") from error
    if not isinstance(items, list):
        raise ValueError("El formato de materiales y consumibles no es válido")

    cantidades = {}
    metodos_validos = {
        choice[0] for choice in ReservaConsumible.METODO_ESTIMACION_CHOICES
    }
    for item in items:
        try:
            consumible_id = int(item["id"])
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            raise ValueError("Hay una selección de material no válida") from error
        if consumible_id in cantidades:
            raise ValueError("No se puede seleccionar dos veces el mismo material")
        metodo = item.get("metodo_estimacion", "estimacion")
        if metodo not in metodos_validos:
            raise ValueError("El método de estimación del material no es válido")
        valor_cantidad = item.get("cantidad")
        if metodo == "revision" and valor_cantidad in (None, "", 0, "0"):
            cantidad = None
        else:
            try:
                cantidad = Decimal(str(valor_cantidad))
            except (TypeError, ValueError, InvalidOperation) as error:
                raise ValueError(
                    "Indica la cantidad calculada o solicita que la determine el laboratorista"
                ) from error
            if cantidad <= 0:
                raise ValueError("Las cantidades solicitadas deben ser mayores que cero")
        cantidades[consumible_id] = (cantidad, metodo)

    catalogo = {
        item.pk: item
        for item in Consumible.objects.filter(
            pk__in=cantidades,
            unidad=unidad,
            activo=True,
            visible_en_reservas=True,
        ).prefetch_related("por_equipo")
    }
    if len(catalogo) != len(cantidades):
        raise ValueError("Uno de los materiales no pertenece al catálogo de esta unidad")
    resultado = []
    for consumible_id, (cantidad, metodo) in cantidades.items():
        consumible = catalogo[consumible_id]
        if cantidad is not None and cantidad > consumible.stock_total:
            raise ValueError(
                f"La cantidad solicitada de {consumible.nombre} supera la existencia disponible"
            )
        resultado.append((consumible, cantidad, metodo))
    return resultado


def validar_compatibilidad_consumibles(consumibles, equipos):
    if not consumibles or not equipos:
        return
    equipos_seleccionados = {equipo.pk for equipo in equipos}
    incompatibles = []
    for consumible, _cantidad, _metodo in consumibles:
        autorizados = {relacion.equipo_id for relacion in consumible.por_equipo.all()}
        if autorizados and equipos_seleccionados.isdisjoint(autorizados):
            incompatibles.append(consumible.nombre)
    if incompatibles:
        raise ValueError(
            "Los siguientes insumos no son compatibles con los equipos seleccionados: "
            + ", ".join(incompatibles)
        )


def validar_servicios(post, unidad, tipo_solicitud):
    configurados = FablabService.objects.filter(
        unidad=unidad,
        activo=True,
        publico=True,
    )
    valores = post.getlist("servicios_solicitados")
    if tipo_solicitud != "servicio":
        if valores:
            raise ValueError("Los servicios solo corresponden a una solicitud de servicio")
        return [], configurados.exists()
    if configurados.exists() and not valores:
        raise ValueError("Selecciona al menos un servicio técnico del laboratorio")
    try:
        ids = [int(value) for value in valores]
    except (TypeError, ValueError) as error:
        raise ValueError("La selección de servicios no es válida") from error
    if len(ids) != len(set(ids)):
        raise ValueError("No se puede seleccionar dos veces el mismo servicio")
    servicios = list(configurados.filter(pk__in=ids))
    if len(servicios) != len(ids):
        raise ValueError("Uno de los servicios no pertenece a esta unidad")
    return servicios, configurados.exists()


def validar_catalogo_consumibles_servicios(servicios, unidad_id):
    inconsistentes = []
    for servicio in servicios:
        for relacion in servicio.service_consumibles.all():
            consumible = relacion.consumible
            if not consumible.activo or consumible.unidad_id not in {None, unidad_id}:
                inconsistentes.append(f"{servicio.nombre}: {consumible.nombre}")
    if inconsistentes:
        raise ValueError(
            "La unidad debe corregir la vinculación de insumos antes de cotizar: "
            + ", ".join(inconsistentes)
        )


def validar_indicaciones_archivos(post, archivos):
    if not archivos:
        return []
    valor = post.get("indicaciones_archivos", "[]")
    try:
        registros = json.loads(valor or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "Las indicaciones de los archivos no tienen un formato válido"
        ) from error
    if not isinstance(registros, list):
        raise ValueError("Las indicaciones de los archivos no tienen un formato válido")

    indicaciones = []
    for indice, archivo in enumerate(archivos):
        registro = registros[indice] if indice < len(registros) else ""
        if isinstance(registro, dict):
            nombre = str(registro.get("nombre", "")).strip()
            texto = str(registro.get("indicaciones", "")).strip()
            if nombre and nombre != archivo.name:
                texto = ""
        elif isinstance(registro, str):
            texto = registro.strip()
        else:
            raise ValueError(
                "Las indicaciones de los archivos no tienen un formato válido"
            )
        if len(texto) > 1200:
            raise ValueError(
                f"Las indicaciones de {archivo.name} no pueden superar 1200 caracteres"
            )
        indicaciones.append(texto)
    return indicaciones


def resolver_catalogos_solicitud(
    post,
    files,
    *,
    unidad,
    tipo_solicitud,
    modalidad_servicio,
    equipos,
    receta_proceso,
    espacios,
):
    """Valida consumibles, servicios y adjuntos antes de cotizar o escribir."""
    consumibles = validar_consumibles(
        post.get("consumibles_seleccionados", "[]"),
        unidad,
    )
    validar_compatibilidad_consumibles(consumibles, equipos)
    if receta_proceso is not None:
        validar_cobertura_del_proceso(
            receta_proceso,
            equipos,
            espacios,
            consumibles,
        )
    servicios, tiene_catalogo_servicios = validar_servicios(
        post,
        unidad,
        tipo_solicitud,
    )
    if tipo_solicitud == "servicio":
        validar_catalogo_consumibles_servicios(servicios, unidad.pk)
    archivos = validar_archivos_tecnicos(
        files.getlist("archivos_tecnicos"),
        requeridos=(
            tipo_solicitud == "servicio"
            and modalidad_servicio == "modelo_listo"
            and any(servicio.requiere_archivos for servicio in servicios)
        ),
    )
    indicaciones_archivos = validar_indicaciones_archivos(post, archivos)
    return CatalogosSolicitud(
        consumibles=consumibles,
        servicios=servicios,
        tiene_catalogo_servicios=tiene_catalogo_servicios,
        archivos=archivos,
        indicaciones_archivos=indicaciones_archivos,
    )
