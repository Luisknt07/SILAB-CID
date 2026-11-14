"""Vistas de acceso y perfil.

Las rutas públicas permanecen sin cambios; este módulo evita que la gestión de
usuarios dependa del antiguo archivo monolítico ``webcitt.views``.
"""

from django.utils.translation import gettext

from allauth.account.utils import complete_signup, perform_login
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.middleware.csrf import REASON_NO_CSRF_COOKIE, rotate_token
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.csrf import csrf_failure as django_csrf_failure
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.gestion_unidades.presentation.permisos import unidades_gestionables
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.core.models.usuarios_base import UserProfile
from apps.reservas.workflows.reservas import ESTADOS_OCUPAN_AGENDA
from apps.core.usuarios.forms import PerfilInstitucionalForm, RegistroInstitucionalForm
from apps.core.usuarios.vigencia import confirmar_periodo, estado_perfil
from apps.core.usuarios.verificacion import estado_verificacion


# Estados que la persona reconoce en su propio seguimiento, en el orden del
# recorrido de la solicitud.
ETAPAS_RESERVA_PERFIL = (
    ("pendiente", "En revisión", "simple-icon-hourglass"),
    ("confirmada", "Confirmadas", "simple-icon-check"),
    ("en_proceso", "En ejecución", "simple-icon-energy"),
    ("completada", "Completadas", "simple-icon-trophy"),
)


def _perfil_initial(user, profile):
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "telefono": profile.telefono or "",
        "institucion": profile.institucion or "",
        "cargo": profile.cargo or "",
        "tipo_usuario": profile.tipo_usuario or "",
        "facultad": profile.facultad or "",
        "carrera": profile.carrera or "",
        "nivel_academico": profile.nivel_academico or "",
        "cedula": profile.cedula or "",
        "biografia": profile.biografia or "",
    }


def _perfil_publico(usuario, unidades):
    """Quien aparece como personal de una unidad muestra un perfil profesional.

    A un estudiante no se le pide cargo ni biografía: no se publican en
    ninguna parte. A quien atiende una unidad sí, porque su ficha los usa.
    """
    return bool(unidades) or usuario.is_staff


def _reservas_del_perfil(usuario):
    """Lo que la persona tiene en los laboratorios, con su enlace de siempre."""
    reservas = Reserva.objects.filter(usuario=usuario).select_related("laboratorio")
    conteos = {
        fila["estado"]: fila["total"]
        for fila in reservas.values("estado").annotate(total=Count("pk"))
    }
    etapas = [
        {"codigo": codigo, "etiqueta": etiqueta, "icono": icono, "total": conteos.get(codigo, 0)}
        for codigo, etiqueta, icono in ETAPAS_RESERVA_PERFIL
    ]
    proxima = (
        reservas.filter(estado__in=ESTADOS_OCUPAN_AGENDA, fecha__gte=timezone.localdate())
        .order_by("fecha", "hora_inicio")
        .first()
    )
    recientes = list(reservas.order_by("-fecha", "-hora_inicio", "-pk")[:3])
    return {
        "total": sum(conteos.values()),
        "etapas": etapas,
        "abiertas": sum(conteos.get(codigo, 0) for codigo in ESTADOS_OCUPAN_AGENDA),
        "proxima": proxima,
        "recientes": recientes,
    }


def _guias_del_perfil(usuario):
    """Guías escritas por la persona: dónde está cada una del proceso."""
    guias = GuiaActividadReserva.objects.filter(
        actividad__creado_por=usuario,
        es_estructurada=True,
        activo=True,
    ).select_related("actividad", "actividad__unidad")
    conteos = {
        fila["estado_publicacion"]: fila["total"]
        for fila in guias.values("estado_publicacion").annotate(total=Count("pk"))
    }
    unidad = next(
        (guia.actividad.unidad for guia in guias[:1] if guia.actividad.unidad_id),
        None,
    )
    return {
        "total": sum(conteos.values()),
        "en_trabajo": conteos.get("borrador", 0) + conteos.get("rechazada", 0),
        "en_revision": conteos.get("revision", 0),
        "publicadas": conteos.get("publicada", 0),
        "url": (
            reverse("lista_guias_practica", args=[unidad.slug]) if unidad else ""
        ),
    }


# El perfil no rehace el panel: nombra las unidades con trabajo esperando y
# deja el resto al catálogo. Un administrador del sistema las gestiona todas.
UNIDADES_VISIBLES_PERFIL = 3


def _unidades_del_perfil(usuario):
    """Unidades que la persona atiende, con el trabajo que espera decisión."""
    unidades = (
        unidades_gestionables(usuario)
        .annotate(
            pendientes=Count(
                "reservas",
                filter=Q(reservas__estado="pendiente"),
                distinct=True,
            )
        )
        .order_by("-pendientes", "nombre")
    )
    total = unidades.count()
    visibles = [
        {
            "unidad": unidad,
            "pendientes": unidad.pendientes,
            "url_panel": reverse("gestion_unidad", args=[unidad.slug]),
        }
        for unidad in unidades[:UNIDADES_VISIBLES_PERFIL]
    ]
    pendientes = sum(unidad.pendientes for unidad in unidades)
    return visibles, total, pendientes


def _perfil_context(request, profile, form=None, abrir_modal=False):
    # El semestre del período nuevo se propone; la persona lo confirma o lo
    # corrige, porque un estudiante irregular no avanza como el resto.
    vigencia = estado_perfil(request.user)
    inicial = _perfil_initial(request.user, profile)
    propuesta = vigencia.get("propuesta") or {}
    if vigencia["requiere_confirmacion"] and propuesta.get("nivel_academico"):
        inicial["nivel_academico"] = propuesta["nivel_academico"]
    form = form or PerfilInstitucionalForm(initial=inicial)
    # El perfil resume lo que la persona tiene en los laboratorios; sin datos
    # inventados: cada cifra sale de sus solicitudes, guías y unidades.
    unidades_gestionadas, unidades_totales, unidades_pendientes = _unidades_del_perfil(
        request.user
    )
    administra_plataforma = request.user.is_superuser or request.user.is_staff
    roles = []
    if administra_plataforma:
        roles.append("Administrador del sistema")
    elif unidades_gestionadas:
        roles.append(
            "Personal de laboratorio"
            if unidades_totales > 1
            else f"Personal de {unidades_gestionadas[0]['unidad'].nombre}"
        )
    if profile.tipo_usuario:
        roles.append(profile.get_tipo_usuario_display())
    if not roles:
        roles.append("Usuario registrado")
    carreras = [
        {
            "value": value,
            "label": label,
            "facultad": UserProfile.facultad_para_carrera(value),
        }
        for value, label in form.fields["carrera"].choices
        if value
    ]
    return {
        "user": request.user,
        "profile": profile,
        "perfil_form": form,
        "tipos_usuario_perfil": tuple(form.fields["tipo_usuario"].choices)[1:],
        "facultades_perfil": tuple(form.fields["facultad"].choices)[1:],
        "niveles_academicos_perfil": tuple(form.fields["nivel_academico"].choices)[1:],
        "carreras_perfil": carreras,
        "perfil_faltantes": vigencia["faltantes"],
        "perfil_vigencia": vigencia,
        "perfil_verificacion": estado_verificacion(profile),
        # Con datos incompletos el formulario se abre solo: es lo único que
        # puede hacer la persona antes de usar la plataforma.
        "abrir_modal_perfil": (
            abrir_modal
            or not vigencia["vigente"]
            or request.GET.get("completar") == "1"
        ),
        "roles_perfil": roles,
        "reservas_perfil": _reservas_del_perfil(request.user),
        "guias_perfil": _guias_del_perfil(request.user),
        "unidades_perfil": unidades_gestionadas,
        "perfil_publico": _perfil_publico(request.user, unidades_gestionadas),
        "unidades_perfil_total": unidades_totales,
        "unidades_perfil_pendientes": unidades_pendientes,
        "unidades_perfil_titulo": (
            "Unidades de la plataforma" if administra_plataforma else "Unidades que gestiono"
        ),
        "seccion_activa": "profile",
    }


def _destino_seguro(request):
    """Devuelve a dónde iba la persona antes de que se le pidiera la sesión."""
    destino = request.POST.get("next") or request.GET.get("next") or ""
    permitido = url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    return destino if destino and permitido else ""


@never_cache
def login_view(request):
    destino = _destino_seguro(request)
    if request.user.is_authenticated:
        return redirect(destino or "profile")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory":
                return perform_login(request, form.get_user(), email_verification="mandatory",
                                     redirect_url=destino or reverse("home"))
            login(request, form.get_user())
            # Se vuelve a la página que exigió la sesión, no siempre al inicio.
            return redirect(destino or "home")
    else:
        form = AuthenticationForm()
    return render(
        request,
        "registration/login.html",
        {
            "form": form,
            "next": destino,
            "csrf_renovado": request.GET.get("seguridad") == "renovada",
        },
    )


def csrf_failure_view(request, reason=""):
    """Recupera un formulario de acceso que conserva un token anterior.

    El POST rechazado nunca se procesa. Se emite otra cookie y se vuelve a
    mostrar el acceso para que la persona envie de nuevo sus credenciales.
    Las fallas de origen, referer y cualquier otra ruta conservan el 403 de
    Django porque pueden representar una solicitud externa real.
    """
    token_de_acceso_desactualizado = (
        request.method == "POST"
        and request.path == reverse("login")
        and (
            reason == REASON_NO_CSRF_COOKIE
            or reason.startswith("CSRF token from POST")
        )
    )
    if not token_de_acceso_desactualizado:
        return django_csrf_failure(request, reason=reason)

    rotate_token(request)
    return redirect(f'{reverse("login")}?seguridad=renovada')


def register_view(request):
    if request.method == "POST":
        form = RegistroInstitucionalForm(request.POST)
        if form.is_valid():
            user = form.save()
            confirmar_periodo(user)
            if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory":
                return complete_signup(request, user, "mandatory", reverse("profile"))
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, gettext("Tu cuenta y perfil institucional quedaron registrados."))
            return redirect("profile")
    else:
        form = RegistroInstitucionalForm()
    return render(request, "registration/register.html", {"form": form})


@require_POST
def salir(request):
    """Cerrar sesión se pide en primera persona: solo por envío del formulario.

    Con GET bastaría una imagen o un enlace ajeno para sacar a alguien de su
    sesión sin que lo pidiera.
    """
    logout(request)
    messages.success(request, gettext("Cerraste la sesión. Vuelve cuando lo necesites."))
    return redirect("home")


@never_cache
@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(
        request,
        "registration/profile.html",
        _perfil_context(request, profile),
    )


@never_cache
@login_required
def profile_edit_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method != "POST":
        return redirect("profile")

    form = PerfilInstitucionalForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, gettext("Revisa los campos señalados para guardar tu perfil."))
        return render(
            request,
            "registration/profile.html",
            _perfil_context(request, profile, form=form, abrir_modal=True),
        )

    user = request.user
    if (settings.ACCOUNT_EMAIL_VERIFICATION == 'mandatory'
            and form.cleaned_data['email'].casefold() != user.email.casefold()):
        form.add_error('email', 'Cambia y verifica tu correo desde la configuración de correo de tu cuenta.')
        return render(request, 'registration/profile.html',
                      _perfil_context(request, profile, form=form, abrir_modal=True))
    user.first_name = form.cleaned_data["first_name"]
    user.last_name = form.cleaned_data["last_name"]
    user.email = form.cleaned_data["email"]
    user.save()

    campos = [
        "telefono", "institucion", "tipo_usuario", "facultad",
        "carrera", "nivel_academico", "cedula",
    ]
    # El perfil profesional solo se edita donde se muestra; si no, conserva lo
    # que hubiera en vez de borrarlo por no venir en el formulario.
    if _perfil_publico(user, _unidades_del_perfil(user)[0]):
        campos += ["cargo", "biografia"]
    for field in campos:
        setattr(profile, field, form.cleaned_data.get(field, ""))
    if "avatar" in request.FILES:
        profile.avatar = form.cleaned_data["avatar"]
    profile.save()

    # Guardar el perfil es confirmar los datos del período en curso: así queda
    # la vinculación que leen las reservas y los reportes.
    vinculacion = confirmar_periodo(user, profile)
    if vinculacion:
        messages.success(
            request,
            "Datos confirmados para el período "
            f"{vinculacion.periodo.codigo}. Ya puedes reservar.",
        )
    else:
        messages.success(request, gettext("¡Perfil actualizado exitosamente!"))
    return redirect("profile")
