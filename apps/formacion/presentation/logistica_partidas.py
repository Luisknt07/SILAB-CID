"""API acotada de partidas: identidad central, estado privado y turnos atómicos.

HTTP condicional evita transferir el estado en cada sondeo. No requiere cargar
simuladores, expedientes ni datos de otras unidades en la ficha del laboratorio.
"""

from copy import deepcopy
import hashlib
import json
import uuid
from urllib.parse import urlencode

from apps.core.presentation.tipologias import tipologia_activa
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, resolve_url
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from apps.formacion.models.partidas_simulador import EventoPartida, PartidaSimulador, ParticipantePartida
from apps.directorio_unidades.models.core import Unidad

from apps.laboratorios.operacion.presentation import logistica_cerveza_servidor as cerveza
from apps.laboratorios.operacion.presentation import logistica_motores as operaciones
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.plantas_piloto.operacion.presentation.secciones_plantas import secciones_ocultas


class ErrorPartida(ValueError):
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.codigo = codigo


def unidad_disponible(slug):
    if slug != SLUG_LOGISTICA:
        raise Http404("Simuladores no disponibles en esta unidad.")
    unidad = get_object_or_404(
        Unidad, slug=slug, activo=True, dependencia="laboratorios"
    )
    if not tipologia_activa("laboratorios"):
        raise Http404("Tipología no disponible.")
    if not unidad.modulos_contenido.filter(
        clave="docencia-capacitacion", activo=True
    ).exists():
        raise Http404("Módulo docente no disponible.")
    if "4.4" in secciones_ocultas(unidad):
        raise Http404("Sección de aprendizaje no disponible.")
    return unidad


def _base_contexto(unidad, request):
    return {
        "unidad": unidad,
        "login_url": resolve_url("login")
        + "?"
        + urlencode({"next": request.get_full_path()}),
        "volver_url": unidad.get_absolute_url() + "#docencia-capacitacion",
    }


@xframe_options_sameorigin
@ensure_csrf_cookie
@require_GET
def cerveza_multijugador_view(request, slug):
    unidad = unidad_disponible(slug)
    contexto = _base_contexto(unidad, request)
    contexto.update(
        api_url=reverse("logistica_api_cerveza", args=[slug]),
        individual_url=reverse("logistica_juego_cerveza", args=[slug]),
        operaciones_url=reverse("logistica_operaciones", args=[slug]),
        catalogo_cerveza={
            "version": cerveza.VERSION,
            "casos": [
                {
                    "codigo": "cerveza-" + clave,
                    "nombre": datos.get("titulo", datos.get("nombre", clave)),
                    "descripcion": datos.get("descripcion", ""),
                    **datos,
                }
                for clave, datos in cerveza.CASOS.items()
            ],
        },
    )
    respuesta = render(
        request, "portal/pages/unidades/logistica/cerveza_multijugador.html", contexto
    )
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@xframe_options_sameorigin
@ensure_csrf_cookie
@require_GET
def operaciones_logistica_view(request, slug):
    unidad = unidad_disponible(slug)
    caso = request.GET.get("caso", "almacen-trazabilidad")
    if caso not in operaciones.CASOS:
        caso = "almacen-trazabilidad"
    try:
        semilla = int(request.GET.get("semilla", "42"))
    except (ValueError, TypeError):
        semilla = 42
    if not 0 <= semilla <= 2147483647:
        semilla = 42
    contexto = _base_contexto(unidad, request)
    contexto.update(
        distribucion_url=reverse("logistica_distribucion", args=[slug])
        + "?caso="
        + (caso if caso.startswith("cd-") else "cd-normal")
        + "&semilla="
        + str(semilla),
        comparador_url=reverse("logistica_distribucion", args=[slug]) + "#comparador",
        semilla_inicial=semilla,
        api_url=reverse("logistica_api_operaciones", args=[slug]),
        cerveza_url=reverse("logistica_cerveza_multijugador", args=[slug]),
        catalogo=operaciones.catalogo(),
        caso_inicial=caso,
        datos_iniciales={
            "caso": caso,
            "estado": operaciones.observacion(operaciones.crear_estado(caso, semilla)),
        },
    )
    respuesta = render(
        request, "portal/pages/unidades/logistica/operaciones.html", contexto
    )
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


def _motor_vigente(partida):
    if partida.simulador == "cerveza":
        return (
            partida.version_motor == cerveza.VERSION and partida.version_caso == "1.0.0"
        )
    if not operaciones.vigente(
        partida.caso, partida.version_motor, partida.version_caso
    ):
        return False
    if partida.caso in operaciones.distribucion.CASOS:
        vistas = partida.observaciones
        vista = vistas.get("operador") if isinstance(vistas, dict) else None
        if (
            not isinstance(vista, dict)
            or vista.get("version_dataset") != operaciones.distribucion.DATASET_VERSION
        ):
            return False
        if "estado" not in partida.get_deferred_fields():
            estado = partida.estado
            if (
                not isinstance(estado, dict)
                or estado.get("version_dataset")
                != operaciones.distribucion.DATASET_VERSION
            ):
                return False
    return True


def _firma_motor(partida):
    if partida.simulador == "cerveza":
        return cerveza.VERSION + ":1.0.0"
    if partida.caso not in operaciones.CASOS:
        return "historico-no-disponible"
    motor = operaciones.motor(partida.caso)
    return ":".join(
        (motor.VERSION, motor.VERSION_CASO, getattr(motor, "DATASET_VERSION", ""))
    )


def _entero(valor, nombre, minimo, maximo):
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ErrorPartida(f"{nombre}: usa un entero entre {minimo} y {maximo}.")
    return valor


def _limitar(usuario, unidad, accion, limite):
    """Cota de abuso complementaria; la corrección depende de SQL, no de caché."""
    from django.utils import timezone

    ventana = int(timezone.now().timestamp()) // 60
    clave = f"logistica:{usuario.pk}:{unidad.pk}:{accion}:{ventana}"
    if cache.add(clave, 1, timeout=70):
        return
    try:
        valor = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, timeout=70)
        return
    if valor > limite:
        raise ErrorPartida(
            "Demasiadas solicitudes. Espera un minuto antes de continuar.", 429
        )


def _identificador(valor):
    try:
        return uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        raise ErrorPartida("Identificador de partida inválido.") from None


def _partida(request, unidad, simulador, identificador, bloquear=False):
    consulta = PartidaSimulador.objects.filter(unidad=unidad, simulador=simulador)
    if not bloquear:
        consulta = consulta.defer("estado")
        if request.headers.get("If-None-Match") and not (
            request.GET.get("exportar") or request.GET.get("verificar")
        ):
            consulta = consulta.defer("observaciones", "resultado")
    if bloquear:
        consulta = consulta.select_for_update()
    partida = get_object_or_404(consulta, pk=_identificador(identificador))
    participantes = list(partida.participantes.order_by("rol"))
    propio = next((p for p in participantes if p.usuario_id == request.user.pk), None)
    if partida.propietario_id != request.user.pk and propio is None:
        raise Http404("Partida no disponible.")
    return partida, participantes, propio


def _serializar(partida, participantes, propio, usuario):
    # Una observación histórica incompatible se conserva para exportación; no
    # se reinterpreta ni debe convertirse en un AttributeError de la API.
    vistas = partida.observaciones
    if not isinstance(vistas, dict):
        raise ErrorPartida(
            "La vista guardada tiene un formato histórico incompatible; conserva su evidencia original.",
            409,
        )
    rol = propio.rol if propio else None
    vista = (
        vistas.get(rol) if partida.simulador == "cerveza" else vistas.get("operador")
    )
    if (
        (partida.simulador != "cerveza" or propio is not None)
        and not isinstance(vista, dict)
    ) or (partida.fase == "terminada" and not isinstance(partida.resultado, dict)):
        raise ErrorPartida(
            "La vista o el resultado guardado no tiene un formato compatible; conserva su evidencia original.",
            409,
        )
    propietario = partida.propietario_id == usuario.pk
    datos = {
        "id": str(partida.pk),
        "nombre": partida.nombre,
        "caso": partida.caso,
        "simulador": partida.simulador,
        "revision": partida.revision,
        "fase": partida.fase,
        "propietario": propietario,
        "rol": propio.rol if propio else None,
        "semilla": partida.semilla,
        "version_motor": partida.version_motor,
        "version_caso": partida.version_caso,
        "solo_lectura": not _motor_vigente(partida),
        "actualizada_en": partida.actualizada_en.isoformat(),
    }
    if partida.simulador == "cerveza":
        # El código se comparte únicamente dentro de la sala de espera.
        datos["codigo"] = partida.codigo if partida.fase == "sala" else ""
        mapa = {p.rol: p for p in participantes}
        datos["participantes"] = [
            {
                "rol": rol,
                "ocupado": rol in mapa,
                "propio": propio is not None and propio.rol == rol,
                "listo": rol in mapa and mapa[rol].pedido is not None,
                "automatico": partida.fase != "sala" and rol not in mapa,
            }
            for rol in cerveza.ROLES
        ]
        datos["decision_enviada"] = propio is not None and propio.pedido is not None
        datos["observacion"] = deepcopy(vista) if propio else None
        if datos["observacion"] is not None:
            datos["observacion"]["decision_enviada"] = datos["decision_enviada"]
        datos["resultado"] = partida.resultado if partida.fase == "terminada" else None
    else:
        datos["estado"] = deepcopy(vista)
        datos["resultado"] = partida.resultado if partida.fase == "terminada" else None
    return datos


def _evento(partida, tipo, datos):
    if (
        tipo == "crear"
        or (tipo == "pedido" and datos.get("turno_resuelto"))
        or tipo == "decision"
    ):
        partida.observaciones = (
            {rol: cerveza.observacion(partida.estado, rol) for rol in cerveza.ROLES}
            if partida.simulador == "cerveza"
            else {"operador": operaciones.observacion(partida.estado)}
        )
    partida.revision += 1
    partida.save(
        update_fields=[
            "estado",
            "observaciones",
            "resultado",
            "fase",
            "revision",
            "actualizada_en",
        ]
    )
    EventoPartida.objects.create(
        partida=partida, revision=partida.revision, tipo=tipo, datos=datos
    )


def _listar(request, unidad, simulador):
    try:
        pagina = max(1, min(1000, int(request.GET.get("pagina", 1))))
    except (ValueError, TypeError):
        raise ErrorPartida("Página inválida.") from None
    consulta = (
        PartidaSimulador.objects.filter(unidad=unidad, simulador=simulador)
        .filter(Q(propietario=request.user) | Q(participantes__usuario=request.user))
        .distinct()
        .annotate(puntaje_lista=F("resultado__puntaje"))
        .defer("estado", "observaciones", "resultado")
        .prefetch_related("participantes")
    )
    familia = request.GET.get("familia", "")
    if familia:
        if familia != "centro-distribucion" or simulador != "operaciones":
            raise ErrorPartida("Familia de escenarios inválida.")
        consulta = consulta.filter(caso__in=operaciones.distribucion.CASOS)
    filas = list(consulta[(pagina - 1) * 20 : pagina * 20 + 1])
    sesiones = []
    for partida in filas[:20]:
        propio = next(
            (p for p in partida.participantes.all() if p.usuario_id == request.user.pk),
            None,
        )
        sesiones.append(
            {
                "id": str(partida.pk),
                "nombre": partida.nombre,
                "caso": partida.caso,
                "codigo": partida.codigo if partida.fase == "sala" else "",
                "revision": partida.revision,
                "fase": partida.fase,
                "propietario": partida.propietario_id == request.user.pk,
                "rol": propio.rol if propio else None,
                "puntaje": partida.puntaje_lista,
                "semilla": partida.semilla,
                "version_motor": partida.version_motor,
                "version_caso": partida.version_caso,
                "actualizada_en": partida.actualizada_en.isoformat(),
            }
        )
    return JsonResponse(
        {
            "sesiones": sesiones,
            "pagina": pagina,
            "siguiente": len(filas) > 20,
            "anterior": pagina > 1,
        }
    )


def _crear(request, unidad, simulador, datos):
    caso = datos.get(
        "caso", "cerveza-base" if simulador == "cerveza" else "almacen-trazabilidad"
    )
    semilla = _entero(datos.get("semilla", 42), "Semilla", 0, 2147483647)
    if not isinstance(caso, str):
        raise ErrorPartida("Selecciona un caso válido.")
    if simulador == "cerveza":
        clave = caso.removeprefix("cerveza-")
        if caso != "cerveza-" + clave or clave not in cerveza.CASOS:
            raise ErrorPartida("Caso de cadena de suministro inválido.")
        estado = cerveza.crear_estado(clave, semilla)
        version = cerveza.VERSION
        titulo = cerveza.CASOS[clave].get("titulo", clave)
    else:
        if caso not in operaciones.CASOS:
            raise ErrorPartida("Caso de operaciones inválido.")
        estado, version, titulo = (
            operaciones.crear_estado(caso, semilla),
            operaciones.version(caso),
            operaciones.CASOS[caso]["titulo"],
        )
    nombre = datos.get("nombre", titulo)
    if not isinstance(nombre, str) or len(nombre) > 120:
        raise ErrorPartida("El nombre debe tener hasta 120 caracteres.")
    nombre = " ".join(nombre.split()) or titulo
    # Bloqueo por autor: dos peticiones simultáneas no eluden el cupo.
    get_user_model().objects.select_for_update().only("pk").get(pk=request.user.pk)
    if (
        PartidaSimulador.objects.filter(
            propietario=request.user, unidad=unidad, fase__in=["sala", "activa"]
        ).count()
        >= 20
    ):
        raise ErrorPartida(
            "Tienes 20 partidas abiertas. Termina o archiva alguna para crear otra.",
            409,
        )
    partida = PartidaSimulador.objects.create(
        unidad=unidad,
        propietario=request.user,
        simulador=simulador,
        caso=caso,
        nombre=nombre,
        semilla=semilla,
        version_motor=version,
        version_caso="1.0.0"
        if simulador == "cerveza"
        else operaciones.version_caso(caso),
        estado=estado,
        fase="sala" if simulador == "cerveza" else "activa",
    )
    propio = None
    if simulador == "operaciones":
        propio = ParticipantePartida.objects.create(
            partida=partida, usuario=request.user, rol="operador"
        )
    _evento(
        partida, "crear", {"caso": caso, "semilla": semilla, "version_motor": version}
    )
    return partida, list(partida.participantes.all()), propio


def _unirse(request, unidad, datos):
    codigo, rol = datos.get("codigo", ""), datos.get("rol")
    if (
        not isinstance(codigo, str)
        or len(codigo.strip()) != 12
        or rol not in cerveza.ROLES
    ):
        raise ErrorPartida("Usa el código de 12 caracteres y selecciona un rol.")
    partida = get_object_or_404(
        PartidaSimulador.objects.select_for_update(),
        unidad=unidad,
        simulador="cerveza",
        codigo=codigo.strip().upper(),
        fase="sala",
    )
    if partida.version_motor != cerveza.VERSION or partida.version_caso != "1.0.0":
        raise ErrorPartida(
            "Sala histórica: solo permite consultar la evidencia existente.", 409
        )
    participantes = list(partida.participantes.all())
    if any(p.usuario_id == request.user.pk for p in participantes):
        raise ErrorPartida("Ya tienes un rol en esta partida.", 409)
    if any(p.rol == rol for p in participantes):
        raise ErrorPartida("Ese rol acaba de ser ocupado. Selecciona otro.", 409)
    propio = ParticipantePartida.objects.create(
        partida=partida, usuario=request.user, rol=rol
    )
    participantes.append(propio)
    _evento(partida, "unirse", {"rol": rol})
    return partida, participantes, propio


def _mutar(request, unidad, simulador, datos):
    accion = datos.get("accion")
    if accion == "crear":
        return _crear(request, unidad, simulador, datos)
    if accion == "unirse" and simulador == "cerveza":
        return _unirse(request, unidad, datos)
    partida, participantes, propio = _partida(
        request, unidad, simulador, datos.get("sesion"), bloquear=True
    )
    if accion in ("actuar", "iniciar") and not _motor_vigente(partida):
        raise ErrorPartida(
            "Motor histórico: conserva la evidencia; no puede reanudarse con otra versión.",
            409,
        )
    revision = _entero(datos.get("revision"), "Revisión", 0, 10000)
    decision_semana = datos.get("decision")
    misma_semana = (
        simulador == "cerveza"
        and accion == "actuar"
        and isinstance(decision_semana, dict)
        and type(decision_semana.get("semana")) is int
        and decision_semana["semana"] == partida.estado["semana"] + 1
        and revision <= partida.revision
    )
    if revision != partida.revision and not misma_semana:
        raise ErrorPartida(
            "La partida cambió. Actualiza antes de enviar de nuevo.", 409
        )
    if (
        simulador == "cerveza"
        and accion == "actuar"
        and isinstance(decision_semana, dict)
        and "semana" in decision_semana
        and not misma_semana
    ):
        raise ErrorPartida("Esa semana ya cambió. Actualiza la partida.", 409)
    if accion == "cerrar":
        if partida.propietario_id != request.user.pk:
            raise ErrorPartida("Solo quien creó la partida puede archivarla.", 403)
        if partida.fase not in ("sala", "activa"):
            raise ErrorPartida("La partida ya terminó o fue archivada.", 409)
        partida.fase = "cerrada"
        _evento(partida, "cerrar", {})
    elif accion == "iniciar" and simulador == "cerveza":
        if partida.propietario_id != request.user.pk:
            raise ErrorPartida("Solo quien creó la sala puede iniciar.", 403)
        if partida.fase != "sala" or not participantes:
            raise ErrorPartida(
                "La sala necesita al menos un participante y no debe haber iniciado.",
                409,
            )
        partida.fase = "activa"
        _evento(partida, "iniciar", {"humanos": [p.rol for p in participantes]})
    elif accion == "actuar":
        if partida.fase != "activa" or propio is None:
            raise ErrorPartida(
                "Necesitas un rol en una partida activa para decidir.", 409
            )
        decision = datos.get("decision")
        if not isinstance(decision, dict):
            raise ErrorPartida("La decisión debe ser un objeto válido.")
        if simulador == "cerveza":
            if partida.version_motor != cerveza.VERSION:
                raise ErrorPartida(
                    "Motor histórico: conserva la evidencia; no puede reanudarse con otra versión.",
                    409,
                )
            if set(decision) - {"pedido", "semana"}:
                raise ErrorPartida("La decisión acepta únicamente pedido y semana.")
            if propio.pedido is not None:
                raise ErrorPartida("Tu decisión ya fue registrada en esta semana.", 409)
            propio.pedido = _entero(decision.get("pedido"), "Pedido", 0, 200)
            propio.save(update_fields=["pedido"])
            # select_for_update(partida) serializa todas las decisiones y uniones.
            for participante in participantes:
                if participante.pk == propio.pk:
                    participante.pedido = propio.pedido
            pendientes = {p.rol: p.pedido for p in participantes}
            evento = {
                "rol": propio.rol,
                "pedido": propio.pedido,
                "semana": partida.estado["semana"] + 1,
            }
            if all(pedido is not None for pedido in pendientes.values()):
                partida.estado = cerveza.avanzar(partida.estado, pendientes)
                evento["turno_resuelto"] = True
                evento["decisiones"] = pendientes
                ParticipantePartida.objects.filter(partida=partida).update(pedido=None)
                for participante in participantes:
                    participante.pedido = None
                if partida.estado["semana"] >= partida.estado["parametros"]["semanas"]:
                    partida.fase, partida.resultado = (
                        "terminada",
                        cerveza.resultado(partida.estado),
                    )
            _evento(partida, "pedido", evento)
        else:
            if not _motor_vigente(partida):
                raise ErrorPartida(
                    "Motor histórico: conserva la evidencia; no puede reanudarse con otra versión.",
                    409,
                )
            partida.estado = operaciones.actuar(partida.estado, decision)
            if partida.estado["terminada"]:
                partida.fase, partida.resultado = (
                    "terminada",
                    operaciones.resultado(partida.estado),
                )
            _evento(partida, "decision", {"decision": decision})
    else:
        raise ErrorPartida("Acción no disponible.")
    return partida, participantes, propio


def _evidencia(partida):
    if partida.fase != "terminada":
        raise ErrorPartida(
            "La evidencia completa estará disponible al terminar la partida.", 409
        )
    return {
        "schema": "upec.simulacion.1",
        "simulador": partida.simulador,
        "caso": partida.caso,
        "version_motor": partida.version_motor,
        "version_caso": partida.version_caso,
        "semilla": partida.semilla,
        "resultado": partida.resultado,
        "eventos": list(partida.eventos.values("revision", "tipo", "datos")),
        "estado_final": partida.estado,
        "datos": "Sintéticos; puntaje didáctico, no calificación académica automática.",
    }


def _eventos_verificables(partida):
    """Valida el registro completo antes de interpretar sus decisiones.

    La proyección y el límite SQL evitan leer una bitácora arbitrariamente
    grande. Una revisión perdida, repetida o adicional invalida la evidencia.
    """
    if partida.simulador == "cerveza":
        limite = 2 + len(cerveza.ROLES) + cerveza.MAX_SEMANAS * len(cerveza.ROLES)
        tipos = {"crear", "unirse", "iniciar", "pedido"}
    else:
        limite = 1 + operaciones.motor(partida.caso).MAX_DECISIONES
        tipos = {"crear", "decision"}
    if type(partida.revision) is not int or not 1 <= partida.revision <= limite:
        return None
    eventos = list(
        partida.eventos.order_by("revision").values("revision", "tipo", "datos")[
            : partida.revision + 1
        ]
    )
    if len(eventos) != partida.revision:
        return None
    for revision, evento in enumerate(eventos, 1):
        datos = evento["datos"]
        tipo = evento["tipo"]
        if (
            evento["revision"] != revision
            or tipo not in tipos
            or not isinstance(datos, dict)
        ):
            return None
        if revision == 1:
            if tipo != "crear" or datos != {
                "caso": partida.caso,
                "semilla": partida.semilla,
                "version_motor": partida.version_motor,
            }:
                return None
        elif tipo == "crear":
            return None
        elif tipo == "decision":
            if set(datos) != {"decision"} or not isinstance(datos["decision"], dict):
                return None
        elif tipo == "unirse":
            if set(datos) != {"rol"} or datos["rol"] not in cerveza.ROLES:
                return None
        elif tipo == "iniciar":
            roles = datos.get("humanos")
            if (
                set(datos) != {"humanos"}
                or not isinstance(roles, list)
                or not 1 <= len(roles) <= len(cerveza.ROLES)
                or any(
                    not isinstance(rol, str) or rol not in cerveza.ROLES
                    for rol in roles
                )
                or len(set(roles)) != len(roles)
            ):
                return None
        elif tipo == "pedido":
            if (
                set(datos) - {"rol", "pedido", "semana", "turno_resuelto", "decisiones"}
                or datos.get("rol") not in cerveza.ROLES
                or type(datos.get("pedido")) is not int
                or not 0 <= datos["pedido"] <= cerveza.MAX_PEDIDO
                or type(datos.get("semana")) is not int
                or not 1 <= datos["semana"] <= cerveza.MAX_SEMANAS
                or (
                    "turno_resuelto" in datos
                    and type(datos["turno_resuelto"]) is not bool
                )
                or (
                    datos.get("turno_resuelto")
                    and not isinstance(datos.get("decisiones"), dict)
                )
                or (not datos.get("turno_resuelto") and "decisiones" in datos)
            ):
                return None
    return eventos


def _verificar(partida):
    motor = cerveza if partida.simulador == "cerveza" else operaciones
    if not _motor_vigente(partida):
        raise ErrorPartida(
            "La evidencia conserva su versión; este motor no permite verificar una versión distinta.",
            409,
        )
    eventos = _eventos_verificables(partida)
    if eventos is None:
        return False
    try:
        estado = motor.crear_estado(
            partida.caso.removeprefix("cerveza-"), partida.semilla
        )
        for evento in eventos:
            datos = evento["datos"]
            if evento["tipo"] == "pedido" and datos.get("turno_resuelto"):
                estado = motor.avanzar(estado, datos["decisiones"])
            elif evento["tipo"] == "decision":
                estado = motor.actuar(estado, datos["decision"])
        vistas = (
            {rol: cerveza.observacion(estado, rol) for rol in cerveza.ROLES}
            if partida.simulador == "cerveza"
            else {"operador": operaciones.observacion(estado)}
        )
        return (
            estado == partida.estado
            and motor.resultado(estado) == partida.resultado
            and vistas == partida.observaciones
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        # JSON histórico o decisiones alteradas siguen siendo exportables,
        # pero no constituyen una reproducción válida con el motor vigente.
        return False


def _api(request, slug, simulador):
    try:
        unidad = unidad_disponible(slug)
        if not request.user.is_authenticated:
            raise ErrorPartida(
                "Inicia sesión para guardar y participar en partidas.", 401
            )
        if request.method == "GET":
            _limitar(request.user, unidad, "lectura", 100)
            if request.GET.get("comparar"):
                if simulador != "operaciones":
                    raise ErrorPartida(
                        "La comparación corresponde al centro de distribución."
                    )
                from apps.laboratorios.operacion.presentation.logistica_distribucion import comparar_partidas

                respuesta = comparar_partidas(request, unidad)
            elif not request.GET.get("sesion"):
                respuesta = _listar(request, unidad, simulador)
            else:
                partida, participantes, propio = _partida(
                    request, unidad, simulador, request.GET["sesion"]
                )
                if request.GET.get("exportar") == "1":
                    respuesta = JsonResponse(_evidencia(partida))
                    respuesta["Content-Disposition"] = (
                        'attachment; filename="partida-' + str(partida.pk) + '.json"'
                    )
                elif request.GET.get("verificar") == "1":
                    # No reconstruir ni cargar la evidencia completa dos veces.
                    if partida.fase != "terminada":
                        raise ErrorPartida(
                            "La evidencia completa estará disponible al terminar la partida.",
                            409,
                        )
                    respuesta = JsonResponse(
                        {
                            "verificada": _verificar(partida),
                            "version_motor": partida.version_motor,
                        }
                    )
                else:
                    etag = (
                        '"'
                        + hashlib.sha256(
                            f"simulacion.2:{partida.pk}:{partida.revision}:{request.user.pk}:{_firma_motor(partida)}".encode()
                        ).hexdigest()[:32]
                        + '"'
                    )
                    if request.headers.get("If-None-Match") == etag:
                        respuesta = HttpResponse(status=304)
                    else:
                        respuesta = JsonResponse(
                            {
                                "sesion": _serializar(
                                    partida, participantes, propio, request.user
                                )
                            }
                        )
                    respuesta["ETag"] = etag
        else:
            _limitar(request.user, unidad, "escritura", 60)
            if request.content_type != "application/json" or len(request.body) > 4096:
                raise ErrorPartida("Envía un objeto JSON de hasta 4 KB.")
            try:
                datos = json.loads(request.body)
            except (ValueError, UnicodeDecodeError, RecursionError):
                raise ErrorPartida("JSON inválido.") from None
            if not isinstance(datos, dict):
                raise ErrorPartida("Envía un objeto JSON válido.")
            accion = datos.get("accion")
            if not isinstance(accion, str):
                raise ErrorPartida("Selecciona una acción válida.")
            if accion in ("crear", "unirse"):
                _limitar(request.user, unidad, accion, 15)
            with transaction.atomic():
                partida, participantes, propio = _mutar(
                    request, unidad, simulador, datos
                )
                datos_respuesta = _serializar(
                    partida, participantes, propio, request.user
                )
            respuesta = JsonResponse(
                {"sesion": datos_respuesta}, status=201 if accion == "crear" else 200
            )
    except Http404:
        respuesta = JsonResponse({"error": "Partida no disponible."}, status=404)
    except ErrorPartida as exc:
        respuesta = JsonResponse({"error": str(exc)}, status=exc.codigo)
        if exc.codigo == 429:
            respuesta["Retry-After"] = "60"
    except ValueError as exc:
        respuesta = JsonResponse({"error": str(exc)}, status=400)
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["Vary"] = "Cookie"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


@csrf_protect
@require_http_methods(["GET", "POST"])
def api_cerveza_view(request, slug):
    return _api(request, slug, "cerveza")


@csrf_protect
@require_http_methods(["GET", "POST"])
def api_operaciones_view(request, slug):
    return _api(request, slug, "operaciones")
