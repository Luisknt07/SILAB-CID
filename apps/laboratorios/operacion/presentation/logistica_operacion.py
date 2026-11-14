"""Preparación presencial: consultas acotadas, sin crear uso físico ni partidas."""

from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.formacion.models.practicas import EvidenciaPractica
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.recursos.models.unidades import UnidadEquipo

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.laboratorios.operacion.presentation.logistica_distribucion import _semilla
from apps.laboratorios.operacion.presentation.logistica_distribucion_guia import guia
from apps.formacion.presentation.logistica_partidas import unidad_disponible
from apps.laboratorios.operacion.presentation.logistica_operacion_seguimiento import CAMPOS_PLAN, controles_expediente, planes_visibles, proxima_accion, resumir_plan
from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad, puede_crear_guias_unidad


def actividades_visibles(usuario, unidad, operador=False):
    base = CatalogoActividadReserva.objects.filter(unidad=unidad, activo=True)
    if not operador:
        base = base.filter(
            Q(creado_por=usuario) | Q(participantes_autorizados=usuario)
        ).distinct()
    return base


def _indicador(titulo, valor, detalle, estado="pendiente"):
    return {"titulo": titulo, "valor": valor, "detalle": detalle, "estado": estado}


def _diagnostico(unidad, permisos):
    """Sólo datos de módulos autorizados; presencia de registro no certifica aptitud."""
    filas = []
    if permisos.get("recursos"):
        equipos = UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad)
        ).aggregate(
            registrados=Count("pk", distinct=True),
            verificados=Count(
                "pk", filter=Q(activa=True, existencia_verificada=True), distinct=True
            ),
            disponibles=Count(
                "pk",
                filter=Q(
                    activa=True, existencia_verificada=True, estado_unidad="disponible"
                ),
                distinct=True,
            ),
        )
        filas.extend(
            [
                _indicador(
                    "Equipos catalogados",
                    equipos["registrados"],
                    "El catálogo no acredita existencia física ni funcionamiento.",
                    "registrado",
                ),
                _indicador(
                    "Existencia verificada",
                    equipos["verificados"],
                    "Registros activos con verificación explícita. Revisar mantenimiento, asignación y condiciones de cada sesión.",
                    "verificado" if equipos["verificados"] else "pendiente",
                ),
                _indicador(
                    "Verificados y disponibles",
                    equipos["disponibles"],
                    "Estado registrado; no comprueba compatibilidad con esta práctica, calibración ni ausencia de solapamientos.",
                    "registrado" if equipos["disponibles"] else "pendiente",
                ),
                _indicador(
                    "Espacios reservables activos",
                    EspacioReservable.objects.filter(
                        unidad=unidad, activo=True, reservable=True
                    ).count(),
                    "No se suman capacidades de áreas para inferir aforo general.",
                    "registrado",
                ),
            ]
        )
    if permisos.get("configuracion") or permisos.get("reservas"):
        hoy = timezone.localdate()
        capacidad = (
            CapacidadOperativaUnidad.objects.filter(
                unidad=unidad,
                activo=True,
                vigente_desde__lte=hoy,
            )
            .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy))
            .order_by("-vigente_desde", "-pk")
            .values(
                "aforo_seguridad",
                "puestos_mobiliario",
                "puestos_equipados",
                "capacidad_personal",
                "fuente",
            )
            .first()
        )
        valor = (
            min(
                capacidad[k]
                for k in (
                    "aforo_seguridad",
                    "puestos_mobiliario",
                    "puestos_equipados",
                    "capacidad_personal",
                )
            )
            if capacidad
            else None
        )
        filas.extend(
            [
                _indicador(
                    "Aforo general registrado",
                    unidad.capacidad_personas
                    if unidad.capacidad_personas is not None
                    else "Sin registrar",
                    "Debe confirmarse por la unidad; no se calcula a partir del inventario.",
                    "registrado"
                    if unidad.capacidad_personas is not None
                    else "pendiente",
                ),
                _indicador(
                    "Capacidad operativa vigente",
                    valor if valor is not None else "Sin registrar",
                    "Mínimo de seguridad, mobiliario, puestos equipados y atención de personal. Revisar su respaldo y el alcance de la sesión.",
                    "registrado"
                    if capacidad and capacidad["fuente"].strip()
                    else "pendiente",
                ),
                _indicador(
                    "Responsables con cuenta activa",
                    ResponsableUnidad.objects.filter(
                        unidad=unidad, activo=True, usuario__is_active=True
                    ).count(),
                    "No asigna automáticamente un responsable a la práctica.",
                    "registrado",
                ),
            ]
        )
    if permisos.get("seguridad"):
        requisitos = RequisitoAcceso.objects.filter(
            unidad=unidad, activo=True, obligatorio=True
        ).aggregate(
            total=Count("pk"),
            inducciones=Count("pk", filter=Q(tipo="induccion")),
        )
        filas.extend(
            [
                _indicador(
                    "Requisitos obligatorios",
                    requisitos["total"],
                    "La ausencia de requisitos no equivale a una autorización de ingreso.",
                    "registrado" if requisitos["total"] else "pendiente",
                ),
                _indicador(
                    "Requisitos de inducción",
                    requisitos["inducciones"],
                    "Cada participante necesita la habilitación y vigencia que determine la unidad.",
                    "registrado" if requisitos["inducciones"] else "pendiente",
                ),
            ]
        )
    return filas


def _enlaces(unidad, permisos, adaptar_url, actividad, puede_planificar):
    gestion = reverse("gestion_unidad", args=[unidad.slug])
    enlaces = []
    configuraciones = [
        (
            "recursos",
            "recursos",
            "Verificar recursos",
            "Comprobar existencia, disponibilidad y mantenimiento.",
            "view=recursos&modo_recursos=activos",
        ),
        (
            "seguridad",
            "seguridad",
            "Seguridad e inducción",
            "Configurar requisitos y revisar habilitaciones.",
            "view=seguridad",
        ),
        (
            "configuracion",
            "configuracion",
            "Configuración de la unidad",
            "Confirmar capacidad, responsables y condiciones de operación.",
            "view=configuracion",
        ),
        (
            "reservas",
            "agenda",
            "Agenda y reservas",
            "Solicitudes y asignación efectiva de recursos por horario.",
            "view=reservas&modo_reservas=agenda",
        ),
        (
            "reportes",
            "reportes",
            "Reportes institucionales",
            "Planificación y ejecución real, recursos, seguridad y guías.",
            "view=reportes",
        ),
    ]
    for permiso, clave, titulo, descripcion, query in configuraciones:
        if permisos.get(permiso) or (clave == "agenda" and permisos.get("agenda")):
            enlaces.append(
                {
                    "id": clave,
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "url": gestion + "?" + query,
                }
            )
    if adaptar_url:
        enlaces.append(
            {
                "id": "adaptar",
                "titulo": "Adaptar guía institucional",
                "descripcion": "Abrir contenido completo y editable. Guardar y enviar a revisión mediante el flujo institucional.",
                "url": adaptar_url,
            }
        )
    if puede_planificar:
        enlaces.append(
            {
                "id": "planificar",
                "titulo": "Planificar práctica",
                "descripcion": "Registrar horario, grupo, responsable y resultado; seleccionar una guía aprobada.",
                "url": reverse("nueva_planificacion_practica", args=[unidad.slug])
                + "?actividad="
                + str(actividad.pk),
            }
        )
    if permisos.get("practicas") or actividad:
        enlaces.append(
            {
                "id": "practicas",
                "titulo": "Planificaciones y ejecuciones",
                "descripcion": "Consultar formatos institucionales, evidencias y estados de revisión.",
                "url": reverse("lista_practicas", args=[unidad.slug]),
            }
        )
    return enlaces


@xframe_options_sameorigin
@login_required
@require_GET
def operacion_view(request, slug):
    unidad = unidad_disponible(slug)
    if not request.user.is_active:
        raise PermissionDenied("Cuenta no disponible.")
    permisos = permisos_operativos_unidad(request.user, unidad)
    puede_adaptar = puede_crear_guias_unidad(request.user, unidad)
    actividades = actividades_visibles(
        request.user, unidad, permisos.get("practicas", False)
    )
    if not puede_adaptar and not any(permisos.values()) and not actividades.exists():
        raise PermissionDenied(
            "Esta preparación está disponible para docentes y participantes autorizados de la unidad."
        )
    caso = request.GET.get("caso", "cd-normal")
    if caso not in motor.CASOS:
        caso = "cd-normal"
    semilla = _semilla(request)
    base = reverse("logistica_operacion", args=[slug])
    parametros = {"caso": caso, "semilla": semilla}
    actividad = None
    seleccion = request.GET.get("actividad", "")
    if seleccion:
        if not seleccion.isascii() or not seleccion.isdigit() or len(seleccion) > 10:
            raise Http404("Actividad no disponible.")
        actividad = actividades.filter(pk=int(seleccion)).first()
        if actividad is None:
            raise Http404("Actividad no disponible.")
        parametros["actividad"] = actividad.pk
    plan_seleccionado = None
    seleccion_plan = request.GET.get("plan", "")
    if seleccion_plan:
        if (
            not actividad
            or not seleccion_plan.isascii()
            or not seleccion_plan.isdigit()
            or len(seleccion_plan) > 10
        ):
            raise Http404("Expediente no disponible.")
        plan_seleccionado = int(seleccion_plan)
        parametros["plan"] = plan_seleccionado
    q = request.GET.get("q", "").strip()[:100]
    listado = actividades
    if q:
        listado = listado.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    pagina = Paginator(
        listado.order_by("nombre", "pk").values(
            "id", "nombre", "codigo", "responsable"
        ),
        12,
    ).get_page(request.GET.get("page"))
    filas = [
        {
            **fila,
            "url": base
            + "?"
            + urlencode(
                {"caso": caso, "semilla": semilla, "actividad": fila["id"], "q": q}
            ),
        }
        for fila in pagina.object_list
    ]
    pagina.object_list = filas
    adaptar_url = ""
    if puede_adaptar:
        adaptar_url = (
            reverse("nueva_guia_practica", args=[slug])
            + "?"
            + urlencode({"plantilla": "logistica-cd", **parametros})
        )
    guias, planes = [], []
    guia_publicada = None
    expediente = None
    puede_planificar = bool(
        actividad
        and (
            permisos.get("practicas")
            or actividad.creado_por_id == request.user.pk
            or actividad.participantes_autorizados.filter(pk=request.user.pk).exists()
        )
    )
    if actividad:
        docs = GuiaActividadReserva.objects.filter(
            actividad=actividad, activo=True, es_estructurada=True
        )
        if not permisos.get("practicas") and actividad.creado_por_id != request.user.pk:
            # La actividad seleccionable exige participación explícita; coincide con la consulta de guías.
            docs = docs.filter(
                Q(subido_por=request.user)
                | Q(actividad__participantes_autorizados=request.user)
            ).distinct()
        publicada = (
            docs.filter(estado_publicacion="publicada")
            .order_by("-numero_version", "-pk")
            .values("id", "titulo", "numero_version")
            .first()
        )
        if publicada:
            guia_publicada = {
                "id": publicada["id"],
                "titulo": publicada["titulo"],
                "version": publicada["numero_version"],
                "url": reverse("ver_guia_actividad", args=[publicada["id"]]),
            }
        guias = [
            {
                "id": g["id"],
                "titulo": g["titulo"],
                "estado": g["estado_publicacion"],
                "estado_label": dict(GuiaActividadReserva.ESTADO_CHOICES).get(
                    g["estado_publicacion"], "Estado no reconocido"
                ),
                "version": g["numero_version"],
                "url": reverse("ver_guia_actividad", args=[g["id"]]),
            }
            for g in docs.order_by("-numero_version", "-pk").values(
                "id", "titulo", "estado_publicacion", "numero_version"
            )[:3]
        ]
        ps = planes_visibles(
            request.user, unidad, actividad, permisos.get("practicas", False)
        )
        for fila in ps.order_by("-fecha", "-pk").values(*CAMPOS_PLAN)[:5]:
            resumen = resumir_plan(
                fila, unidad, actividad, request.user, permisos.get("practicas", False)
            )
            resumen["seleccion_url"] = (
                base
                + "?"
                + urlencode(
                    {
                        "caso": caso,
                        "semilla": semilla,
                        "actividad": actividad.pk,
                        "plan": fila["id"],
                        "q": q,
                    }
                )
                + "#expediente"
            )
            resumen["seleccionado"] = fila["id"] == plan_seleccionado
            planes.append(resumen)
        if plan_seleccionado is not None:
            fila = ps.filter(pk=plan_seleccionado).values(*CAMPOS_PLAN).first()
            if fila is None:
                raise Http404("Expediente no disponible.")
            expediente = resumir_plan(
                fila, unidad, actividad, request.user, permisos.get("practicas", False)
            )
            evidencias = []
            if expediente["ejecucion"]:
                tipos = dict(EvidenciaPractica.TIPOS)
                conteos = EvidenciaPractica.objects.filter(
                    ejecucion_id=expediente["ejecucion"]["id"]
                ).aggregate(
                    total=Count("pk"),
                    **{tipo: Count("pk", filter=Q(tipo=tipo)) for tipo in tipos},
                )
                evidencias = [
                    {"titulo": titulo, "total": conteos[tipo]}
                    for tipo, titulo in tipos.items()
                    if conteos[tipo]
                ]
                expediente["evidencias_total"] = conteos["total"]
            else:
                expediente["evidencias_total"] = 0
            expediente["evidencias"] = evidencias
            expediente["proxima_accion"] = proxima_accion(
                expediente, permisos.get("practicas", False)
            )
    controles = controles_expediente(expediente)
    if expediente is None and guia_publicada:
        next(control for control in controles if control["id"] == "guia").update(
            estado="registrado",
            detalle="La actividad tiene una guía publicada. Selecciona un expediente para comprobar cuál utiliza.",
        )
    contexto = {
        "unidad": unidad,
        "caso": caso,
        "semilla": semilla,
        "guia_virtual": guia(caso),
        "volver_url": reverse("logistica_distribucion", args=[slug])
        + "?"
        + urlencode({"caso": caso, "semilla": semilla}),
        "simulador_url": reverse("logistica_operaciones", args=[slug])
        + "?"
        + urlencode({"caso": caso, "semilla": semilla}),
        "adaptar_url": adaptar_url,
        "permisos": permisos,
        "enlaces": _enlaces(unidad, permisos, adaptar_url, actividad, puede_planificar),
        "indicadores": _diagnostico(unidad, permisos),
        "controles": controles,
        "actividades": filas,
        "actividad": actividad,
        "consulta": q,
        "q": q,
        "pagina": pagina,
        "guias": guias,
        "planes": planes,
        "plan_seleccionado": plan_seleccionado,
        "guia_publicada": guia_publicada,
        "expediente": expediente,
        "avisos": [
            "Este panel no autoriza una sesión ni sustituye la verificación de recursos y seguridad.",
            "La guía virtual emplea datos sintéticos. Las partidas no crean reservas, asistencia, consumos ni ejecuciones físicas.",
            "Para FT03 adjunta CSV e informe, o un ZIP con la evidencia JSON. Identifica expresamente qué resultados proceden de simulación.",
        ],
    }
    respuesta = render(
        request, "portal/pages/unidades/logistica/operacion.html", contexto
    )
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta
