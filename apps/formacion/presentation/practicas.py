"""Flujo actividad → guía → planificación → reserva → ejecución → reporte."""

from contextlib import nullcontext

from apps.core.identificadores import id_solicitado

from django.utils.translation import gettext

from apps.core.presentation.pdf_institucional import encabezado_en_flujo, pie_institucional

from io import BytesIO

from xml.sax.saxutils import escape
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad

from apps.reservas.workflows.reservas import ESTADOS_CERRADOS, TransicionReservaNoPermitida, validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.reservas.presentation.capacidad import bloquear_operacion_reservas
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.formacion.presentation.practicas_evidencias import registrar_evidencias
from apps.formacion.presentation.practicas_forms import EjecucionPracticaForm, PlanificacionPracticaForm
from apps.formacion.presentation.practicas_excel import render_practices_xlsx
from apps.formacion.presentation.practicas_integracion import asegurar_participantes_reserva, construir_detalle_operativo, datos_planificacion_desde_reserva, estado_documental_reserva, resumen_recursos, DocumentacionReservaPendiente, validar_compuerta_documental
from apps.core.presentation.pdf_institucional import fuentes_documento, hoja_de_estilos


PLAN_FIELDS_AUDIT = (
    "estado", "fecha", "hora_inicio", "hora_fin", "tema",
    "estudiantes_planificados", "guia_id", "requiere_guia", "reserva_id",
)
EXEC_FIELDS_AUDIT = (
    "estado", "resultado", "fecha_ejecucion", "hora_inicio_real",
    "hora_fin_real", "estudiantes_asistentes", "cumplimiento_resultado",
    "detalle_operativo",
)
# Reabrir una ejecución validada exige decir qué se va a corregir.
MINIMO_MOTIVO_REAPERTURA = 15
INFORME_SEMESTRAL_ENVIADO = (
    "El informe semestral del período de esta práctica ya fue enviado: "
    "la Dirección debe devolver primero el informe para poder reabrir la ejecución."
)


def _informe_semestral_enviado(unidad, fecha):
    """El informe semestral ya enviado cuyo tramo contiene la fecha; ``None`` si no lo hay."""
    from apps.documentos.models.expediente import DocumentoExpediente
    from apps.documentos.presentation.expediente import tramo_del_documento

    for documento in DocumentoExpediente.objects.filter(
        unidad=unidad, exigido__codigo="INFORME-SEMESTRAL", estado="validado",
    ).select_related("exigido", "unidad"):
        inicio, fin = tramo_del_documento(documento)
        if inicio <= fecha <= fin:
            return documento
    return None


def _actividades_para(usuario, unidad):
    base = CatalogoActividadReserva.objects.filter(unidad=unidad, activo=True)
    if puede_operar_modulo_unidad(usuario, unidad, "practicas"):
        return base
    return base.filter(
        Q(creado_por=usuario) | Q(participantes_autorizados=usuario)
    ).distinct()


def _puede_editar_plan(usuario, plan):
    return plan.creado_por_id == usuario.pk or puede_operar_modulo_unidad(
        usuario, plan.unidad, "practicas"
    )


def _obtener_plan_visible(request, slug, plan_id):
    plan = get_object_or_404(
        PlanificacionPractica.objects.select_related(
            "unidad", "actividad", "guia", "reserva", "creado_por", "responsable_tecnico"
        ),
        pk=plan_id,
        unidad__slug=slug,
        eliminado_en__isnull=True,
    )
    if not (
        _puede_editar_plan(request.user, plan)
        or (
            plan.actividad_id
            and plan.actividad.participantes_autorizados.filter(pk=request.user.pk).exists()
        )
    ):
        raise PermissionDenied("No tienes autorización para consultar esta planificación.")
    return plan


@login_required
def lista_practicas_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    actividades = _actividades_para(request.user, unidad)
    operador = puede_operar_modulo_unidad(request.user, unidad, "practicas")
    planes = PlanificacionPractica.objects.filter(
        unidad=unidad,
        eliminado_en__isnull=True,
    ).select_related(
        "actividad", "guia", "reserva", "creado_por", "responsable_tecnico", "ejecucion"
    ).defer(
        "ejecucion__detalle_operativo", "ejecucion__recursos_utilizados",
        "ejecucion__observaciones_docente", "ejecucion__motivo",
        "ejecucion__observaciones_revision",
    )
    if not operador:
        planes = planes.filter(
            Q(creado_por=request.user) | Q(actividad__participantes_autorizados=request.user)
        ).distinct()
    estado = request.GET.get("estado", "")
    categoria = request.GET.get("categoria", "")
    buscar = request.GET.get("q", "").strip()
    if estado in dict(PlanificacionPractica.ESTADOS):
        planes = planes.filter(estado=estado)
    if categoria in dict(PlanificacionPractica.CATEGORIAS_USO):
        planes = planes.filter(categoria_uso=categoria)
    if buscar:
        planes = planes.filter(
            Q(codigo__icontains=buscar)
            | Q(tema__icontains=buscar)
            | Q(asignatura__icontains=buscar)
            | Q(docente_tutor__icontains=buscar)
        )
    return render(
        request,
        "portal/pages/unidades/practicas/lista.html",
        {
            "unidad": unidad,
            "planes": planes[:250],
            "actividades": actividades,
            "es_operador": operador,
            "estados": PlanificacionPractica.ESTADOS,
            "categorias": PlanificacionPractica.CATEGORIAS_USO,
            "filtros": {"estado": estado, "categoria": categoria, "q": buscar},
        },
    )


@login_required
def editar_planificacion_view(request, slug, plan_id=None):
    unidad = get_object_or_404(Unidad, slug=slug)
    actividades = _actividades_para(request.user, unidad)
    if plan_id:
        plan = _obtener_plan_visible(request, slug, plan_id)
        if not _puede_editar_plan(request.user, plan):
            raise PermissionDenied("No puedes modificar esta planificación.")
        if plan.estado not in {"borrador", "observada"} and not puede_operar_modulo_unidad(request.user, unidad, "practicas"):
            raise PermissionDenied("La planificación ya fue enviada a revisión.")
    else:
        reserva_id = request.GET.get("reserva")
        reserva = None
        if reserva_id:
            reserva = get_object_or_404(
                Reserva.objects.select_related(
                    "laboratorio",
                    "actividad_catalogo",
                    "usuario",
                    "responsable_asignado",
                ),
                pk=id_solicitado(reserva_id),
                laboratorio=unidad,
            )
            existente = PlanificacionPractica.objects.filter(
                reserva=reserva,
                eliminado_en__isnull=True,
            ).first()
            if existente:
                return redirect(
                    "detalle_planificacion_practica",
                    slug=slug,
                    plan_id=existente.pk,
                )
            if not actividades.filter(pk=reserva.actividad_catalogo_id).exists():
                raise PermissionDenied("No puedes planificar la actividad de esta reserva.")
        actividad = (
            reserva.actividad_catalogo
            if reserva
            else get_object_or_404(actividades, pk=id_solicitado(request.GET.get("actividad")))
            if request.GET.get("actividad")
            else actividades.first()
        )
        if not actividad:
            # Una página 403 en blanco no decía qué hacer: la actividad nace con su guía.
            messages.error(request, gettext(
                "Para planificar una práctica primero crea su guía: al guardarla queda registrada "
                "la actividad. Usa «+ Nueva guía» y vuelve a «Nueva planificación»."
            ))
            return redirect("lista_guias_practica", slug=slug)
        if reserva:
            plan = PlanificacionPractica(
                **datos_planificacion_desde_reserva(reserva, actor=request.user)
            )
        else:
            plan = PlanificacionPractica(
                unidad=unidad,
                actividad=actividad,
                creado_por=request.user,
                fecha=timezone.localdate(),
                asignatura=actividad.nombre,
                docente_tutor=actividad.responsable or request.user.get_full_name() or request.user.username,
                tema=actividad.nombre,
            )

    if request.method == "POST":
        anteriores = instantanea(plan, PLAN_FIELDS_AUDIT) if plan.pk else {}
        form = PlanificacionPracticaForm(
            request.POST,
            instance=plan,
            unidad=unidad,
            actividades=actividades,
        )
        if form.is_valid():
            with transaction.atomic():
                objeto = form.save(commit=False)
                objeto.unidad = unidad
                objeto.creado_por_id = objeto.creado_por_id or request.user.pk
                accion = "enviar" if request.POST.get("accion") == "enviar" else ("actualizar" if objeto.pk else "crear")
                if accion == "enviar":
                    objeto.estado = "revision"
                    try:
                        objeto.full_clean()
                    except ValidationError as error:
                        form.add_error(None, error)
                    else:
                        objeto.save()
                else:
                    objeto.estado = "borrador" if objeto.estado == "observada" else objeto.estado
                    objeto.save()
                if not form.errors:
                    registrar_auditoria(
                        request,
                        unidad=unidad,
                        accion=accion,
                        objeto=objeto,
                        descripcion=f"Planificación {objeto.codigo}: {objeto.tema}",
                        anteriores=anteriores,
                        nuevos=instantanea(objeto, PLAN_FIELDS_AUDIT),
                    )
                    messages.success(request, "Planificación guardada y enviada a revisión." if accion == "enviar" else "Borrador de planificación guardado.")
                    return redirect("detalle_planificacion_practica", slug=slug, plan_id=objeto.pk)
    else:
        form = PlanificacionPracticaForm(
            instance=plan,
            unidad=unidad,
            actividades=actividades,
        )
    return render(
        request,
        "portal/pages/unidades/practicas/form_planificacion.html",
        {"unidad": unidad, "plan": plan, "form": form},
    )


@login_required
@require_POST
def accion_planificacion_view(request, slug, plan_id):
    plan = _obtener_plan_visible(request, slug, plan_id)
    if not puede_operar_modulo_unidad(request.user, plan.unidad, "practicas"):
        raise PermissionDenied("Solo un responsable de la unidad puede revisar planificaciones.")
    accion = request.POST.get("accion", "")
    anteriores = instantanea(plan, PLAN_FIELDS_AUDIT)
    with transaction.atomic():
        if accion == "aprobar":
            documentacion_lista = bool(
                plan.guia_id
                and plan.guia.activo
                and plan.guia.estado_publicacion == "publicada"
            )
            documentacion = None
            if plan.reserva_id:
                documentacion = estado_documental_reserva(plan.reserva)
                documentacion_lista = documentacion["lista"]
                if documentacion_lista and documentacion.get("guia_id"):
                    plan.guia_id = documentacion["guia_id"]
            if plan.requiere_guia and not documentacion_lista:
                etiqueta = (
                    documentacion["etiqueta"]
                    if documentacion else "Guía pendiente de aprobación"
                )
                messages.error(
                    request,
                    f"No se puede aprobar la planificación: {etiqueta.lower()}.",
                )
                return redirect(
                    "detalle_planificacion_practica",
                    slug=slug,
                    plan_id=plan.pk,
                )
            plan.estado = "aprobada"
            plan.observaciones_revision = request.POST.get("observaciones", "").strip()
            plan.revisado_por = request.user
            plan.revisado_en = timezone.now()
            plan.full_clean()
            plan.save()
            audit_action = "aprobar"
            mensaje = "Planificación aprobada."
        elif accion == "observar":
            observaciones = request.POST.get("observaciones", "").strip()
            if not observaciones:
                messages.error(request, gettext("Registra las observaciones que debe corregir el autor."))
                return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
            plan.estado = "observada"
            plan.observaciones_revision = observaciones
            plan.revisado_por = request.user
            plan.revisado_en = timezone.now()
            plan.save()
            audit_action = "observar"
            mensaje = "Planificación devuelta con observaciones."
        elif accion == "archivar":
            plan.eliminar_logicamente(request.user)
            audit_action = "archivar"
            mensaje = "Planificación archivada sin eliminar su historial."
        elif accion == "nueva_version":
            # Mantiene el orden unidad → plan, también para las FK de la copia.
            Unidad.objects.select_for_update().only("pk").get(pk=plan.unidad_id)
            # Dos pestañas no pueden reemplazar a la vez la misma versión.
            plan = PlanificacionPractica.objects.select_for_update().get(pk=plan.pk)
            if not plan.es_version_vigente or plan.eliminado_en is not None:
                messages.error(request, gettext("Esta planificación ya tiene una versión posterior."))
                return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
            plan.es_version_vigente = False
            plan.save(update_fields=["es_version_vigente", "actualizado_en"])
            copia = PlanificacionPractica.objects.create(
                grupo_version=plan.grupo_version,
                numero_version=plan.numero_version + 1,
                actividad=plan.actividad,
                guia=plan.guia,
                requiere_guia=plan.requiere_guia,
                tema_asignatura=plan.tema_asignatura,
                unidad=plan.unidad,
                fecha=plan.fecha,
                hora_inicio=plan.hora_inicio,
                hora_fin=plan.hora_fin,
                carrera=plan.carrera,
                semestre=plan.semestre,
                asignatura=plan.asignatura,
                docente_tutor=plan.docente_tutor,
                tema=plan.tema,
                resultado_aprendizaje=plan.resultado_aprendizaje,
                estudiantes_planificados=plan.estudiantes_planificados,
                categoria_uso=plan.categoria_uso,
                responsable_tecnico=plan.responsable_tecnico,
                observaciones=plan.observaciones,
                creado_por=request.user,
            )
            registrar_auditoria(
                request,
                unidad=plan.unidad,
                accion="crear",
                objeto=copia,
                descripcion=f"Nueva versión de {plan.codigo}",
                anteriores=anteriores,
                nuevos=instantanea(copia, PLAN_FIELDS_AUDIT),
            )
            messages.success(request, gettext("Se creó una nueva versión editable."))
            return redirect("editar_planificacion_practica", slug=slug, plan_id=copia.pk)
        else:
            messages.error(request, gettext("Selecciona una acción válida."))
            return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
        evento_aprobacion = registrar_auditoria(
            request,
            unidad=plan.unidad,
            accion=audit_action,
            objeto=plan,
            descripcion=mensaje,
            anteriores=anteriores,
            nuevos=instantanea(plan, PLAN_FIELDS_AUDIT),
        )
        if accion == 'aprobar':
            from apps.documentos.presentation.aprobacion_tecnica_laboratorios import registrar_aprobacion_tecnica
            registrar_aprobacion_tecnica(plan, request.user, evento=evento_aprobacion)
    messages.success(request, mensaje)
    return redirect("lista_practicas", slug=slug) if accion == "archivar" else redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)


def _exigir_ejecucion_editable(ejecucion):
    """La revisión y el cierre conservan la evidencia que recibió el revisor."""
    if ejecucion.pk and (
        ejecucion.eliminado_en is not None
        or ejecucion.estado not in {"borrador", "observada"}
    ):
        raise PermissionDenied(
            "La ejecución está en revisión o cerrada. "
            "Solo una ejecución en borrador o devuelta con observaciones admite cambios."
        )


@login_required
def editar_ejecucion_view(request, slug, plan_id):
    plan = _obtener_plan_visible(request, slug, plan_id)
    if not _puede_editar_plan(request.user, plan):
        raise PermissionDenied("No puedes registrar esta ejecución.")
    if plan.estado != "aprobada":
        messages.error(request, gettext("La planificación debe estar aprobada antes de registrar la ejecución."))
        return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
    if not plan.reserva_id:
        messages.error(request, gettext("Vincula una reserva antes de registrar la ejecución."))
        return redirect("editar_planificacion_practica", slug=slug, plan_id=plan.pk)
    try:
        ejecucion = plan.ejecucion
        _exigir_ejecucion_editable(ejecucion)
    except EjecucionPractica.DoesNotExist:
        if plan.reserva.estado in ESTADOS_CERRADOS:
            detalle_inicial = plan.reserva.detalle_ejecucion
            detalle_inicial = detalle_inicial if isinstance(detalle_inicial, dict) else {}
        else:
            detalle_inicial = construir_detalle_operativo(plan.reserva)
        ejecucion = EjecucionPractica(
            planificacion=plan,
            fecha_ejecucion=plan.reserva.fecha,
            hora_inicio_real=plan.reserva.hora_inicio,
            hora_fin_real=plan.reserva.hora_fin,
            estudiantes_asistentes=plan.reserva.numero_participantes,
            responsable_tecnico=plan.responsable_tecnico,
            detalle_operativo=detalle_inicial,
            recursos_utilizados=resumen_recursos(detalle_inicial),
            creado_por=request.user,
        )
    if request.method == "POST":
        with transaction.atomic():
            # Mismo orden que reservas: unidad → reserva → plan → ejecución.
            # El plan serializa también la primera ejecución.
            Unidad.objects.select_for_update().only("pk").get(pk=plan.unidad_id)
            reserva_bloqueada = Reserva.objects.select_for_update().get(pk=plan.reserva_id)
            plan = PlanificacionPractica.objects.select_for_update().get(pk=plan.pk)
            if (
                plan.eliminado_en is not None or plan.estado != "aprobada"
                or plan.reserva_id != reserva_bloqueada.pk
            ):
                raise PermissionDenied("La planificación ya no está disponible para registrar la ejecución.")
            actor_actual = get_user_model().objects.filter(pk=request.user.pk, is_active=True).first()
            if actor_actual is None or not _puede_editar_plan(actor_actual, plan):
                raise PermissionDenied("Ya no tienes autorización para editar esta ejecución.")
            guardada = EjecucionPractica.objects.select_for_update().filter(planificacion=plan).first()
            if guardada is not None:
                ejecucion = guardada
            _exigir_ejecucion_editable(ejecucion)
            if reserva_bloqueada.estado not in ESTADOS_CERRADOS:
                asegurar_participantes_reserva(plan.reserva)
            anteriores = instantanea(ejecucion, EXEC_FIELDS_AUDIT) if ejecucion.pk else {}
            form = EjecucionPracticaForm(request.POST, instance=ejecucion, planificacion=plan)
            if form.is_valid():
                objeto = form.save(commit=False)
                objeto.planificacion = plan
                objeto.creado_por_id = objeto.creado_por_id or request.user.pk
                accion = "enviar" if request.POST.get("accion") == "enviar" else ("actualizar" if objeto.pk else "crear")
                objeto.estado = "revision" if accion == "enviar" else ("borrador" if objeto.estado == "observada" else objeto.estado)
                form.aplicar_detalle_operativo(objeto)
                objeto.full_clean()
                objeto.save()
                registrar_auditoria(
                    request,
                    unidad=plan.unidad,
                    accion=accion,
                    objeto=objeto,
                    descripcion=f"Ejecución de {plan.codigo}",
                    anteriores=anteriores,
                    nuevos=instantanea(objeto, EXEC_FIELDS_AUDIT),
                )
                try:
                    registrar_evidencias(request, objeto)
                except ValidationError as error:
                    # Nada de la ejecución se guarda si la evidencia no pasa.
                    form.add_error(None, error)
                    transaction.set_rollback(True)
            if not form.errors:
                messages.success(request, "Ejecución enviada a revisión." if accion == "enviar" else "Borrador de ejecución guardado.")
                return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
    else:
        if plan.reserva.estado not in ESTADOS_CERRADOS:
            asegurar_participantes_reserva(plan.reserva)
        form = EjecucionPracticaForm(instance=ejecucion, planificacion=plan)
    return render(
        request,
        "portal/pages/unidades/practicas/form_ejecucion.html",
        {
            "unidad": plan.unidad, "plan": plan, "ejecucion": ejecucion, "form": form,
            "evidencias": list(ejecucion.evidencias.all()) if ejecucion.pk else [],
            "tipos_evidencia": EvidenciaPractica.TIPOS,
        },
    )


@login_required
@require_POST
def accion_ejecucion_view(request, slug, plan_id):
    plan = _obtener_plan_visible(request, slug, plan_id)
    if not puede_operar_modulo_unidad(request.user, plan.unidad, "practicas"):
        raise PermissionDenied("Solo un responsable puede validar la ejecución.")
    ejecucion = get_object_or_404(EjecucionPractica, planificacion=plan, eliminado_en__isnull=True)
    accion = request.POST.get("accion", "")
    proteccion_reserva = (
        bloquear_operacion_reservas()
        if accion == "validar"
        and plan.reserva_id
        else nullcontext()
    )
    with proteccion_reserva, transaction.atomic():
        # Comparte unidad → reserva → plan → ejecución con el editor y las reservas.
        Unidad.objects.select_for_update().only("pk").get(pk=plan.unidad_id)
        reserva_bloqueada = (
            Reserva.objects.select_for_update().get(pk=plan.reserva_id)
            if plan.reserva_id else None
        )
        plan = PlanificacionPractica.objects.select_for_update().get(pk=plan.pk)
        if (
            plan.eliminado_en is not None
            or plan.reserva_id != (reserva_bloqueada.pk if reserva_bloqueada else None)
        ):
            raise PermissionDenied("La planificación cambió; vuelve a abrir el expediente.")
        ejecucion = get_object_or_404(
            EjecucionPractica.objects.select_for_update(),
            planificacion=plan, eliminado_en__isnull=True,
        )
        anteriores = instantanea(ejecucion, EXEC_FIELDS_AUDIT)
        datos_reapertura = {}
        if ejecucion.estado == "validada" and accion in {"validar", "observar"}:
            raise PermissionDenied("Una ejecución validada conserva su cierre y no puede volver a editarse.")
        if accion == "validar":
            ejecucion.estado = "validada"
            ejecucion.observaciones_revision = request.POST.get("observaciones", "").strip()
            ejecucion.validado_por = request.user
            ejecucion.validado_en = timezone.now()
            ejecucion.full_clean()
            ejecucion.save()
            if plan.reserva_id:
                accion_reserva = {
                    "ejecutada": "completar",
                    "cancelada": "cancelar",
                }.get(ejecucion.resultado)
                if accion_reserva:
                    # La reserva se cierra por la misma maquina de estados que
                    # usa el panel: mismas transiciones, misma compuerta
                    # documental, misma notificacion y misma bitacora.
                    reserva = Reserva.objects.select_for_update().get(pk=plan.reserva_id)
                    motivo_cierre = (
                        ejecucion.observaciones_docente
                        or f"Ejecución validada desde {plan.codigo}."
                    )
                    # La reserva puede estar ya cerrada: desde el panel, o porque la
                    # ejecución se reabrió después de validarse. No se cierra dos veces.
                    cierre_ya_registrado = (
                        accion_reserva == "completar"
                        and reserva.estado == "completada"
                        and reserva.resultado_cierre == "atendida"
                    ) or (accion_reserva == "cancelar" and reserva.estado == "cancelada")
                    try:
                        validar_compuerta_documental(reserva, accion_reserva)
                        if not cierre_ya_registrado:
                            nuevo_estado = validar_accion_reserva(
                                reserva.estado, accion_reserva, motivo=motivo_cierre,
                            )
                    except (TransicionReservaNoPermitida, DocumentacionReservaPendiente) as error:
                        messages.error(
                            request,
                            f"La ejecución no se validó: la reserva {reserva.codigo_reserva or reserva.pk} "
                            f"no admite esa transición. {error}",
                        )
                        transaction.set_rollback(True)
                        return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
                    # El cierre operativo puede haber dejado la ejecución en revisión.
                    # Su aprobación documental conserva la instantánea física.
                    if not cierre_ya_registrado:
                        estado_previo = reserva.estado
                        reserva.estado = nuevo_estado
                        reserva.validada_por = request.user
                        reserva.fecha_validacion = timezone.now()
                        if nuevo_estado == "completada":
                            reserva.resultado_cierre = "atendida"
                            reserva.fecha_cierre = timezone.now()
                            reserva.detalle_cierre = motivo_cierre
                        reserva.save()
                        registrar_auditoria(
                            request,
                            unidad=plan.unidad,
                            accion=accion_reserva,
                            objeto=reserva,
                            descripcion=f"Cierre desde la validación de {plan.codigo}.",
                            anteriores={"estado": estado_previo},
                            nuevos={"estado": nuevo_estado},
                        )
                        notificar_cambio_reserva(reserva, accion_reserva, motivo_cierre)
            audit_action, mensaje = "aprobar", "Ejecución validada y cerrada."
        elif accion == "observar":
            observaciones = request.POST.get("observaciones", "").strip()
            if not observaciones:
                messages.error(request, gettext("Registra las observaciones de revisión."))
                return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
            ejecucion.estado = "observada"
            ejecucion.observaciones_revision = observaciones
            ejecucion.validado_por = request.user
            ejecucion.validado_en = timezone.now()
            ejecucion.save()
            audit_action, mensaje = "observar", "Ejecución devuelta con observaciones."
        elif accion == "reabrir":
            # Vuelve a «devuelta con observaciones»: quien la registró corrige, agrega
            # evidencias y la envía otra vez a revisión por el flujo de siempre.
            motivo = request.POST.get("motivo", "").strip()
            if ejecucion.estado != "validada":
                error = gettext("Solo una ejecución validada y cerrada se reabre para corregir.")
            elif len(motivo) < MINIMO_MOTIVO_REAPERTURA:
                error = gettext(
                    "Escribe el motivo de la reapertura: qué se va a corregir (al menos %(minimo)s caracteres)."
                ) % {"minimo": MINIMO_MOTIVO_REAPERTURA}
            elif _informe_semestral_enviado(plan.unidad, ejecucion.fecha_ejecucion):
                error = gettext(INFORME_SEMESTRAL_ENVIADO)
            else:
                error = ""
            if error:
                messages.error(request, error)
                return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
            ejecucion.estado = "observada"
            ejecucion.observaciones_revision = motivo
            ejecucion.validado_por = request.user
            ejecucion.validado_en = timezone.now()
            ejecucion.save()
            audit_action, mensaje = "observar", "Ejecución reabierta para corregir."
            datos_reapertura = {"motivo_reapertura": motivo}
        elif accion == "archivar":
            ejecucion.eliminar_logicamente(request.user)
            audit_action, mensaje = "archivar", "Ejecución archivada sin eliminar su historial."
        else:
            messages.error(request, gettext("Selecciona una acción válida."))
            return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)
        evento_aprobacion = registrar_auditoria(
            request,
            unidad=plan.unidad,
            accion=audit_action,
            objeto=ejecucion,
            descripcion=mensaje,
            anteriores=anteriores,
            nuevos=instantanea(ejecucion, EXEC_FIELDS_AUDIT) | datos_reapertura,
        )
        if accion == 'validar':
            from apps.documentos.presentation.aprobacion_tecnica_laboratorios import registrar_aprobacion_tecnica
            registrar_aprobacion_tecnica(ejecucion, request.user, evento=evento_aprobacion)
    messages.success(request, mensaje)
    return redirect("detalle_planificacion_practica", slug=slug, plan_id=plan.pk)


@login_required
def detalle_planificacion_view(request, slug, plan_id):
    plan = _obtener_plan_visible(request, slug, plan_id)
    ejecucion = EjecucionPractica.objects.filter(planificacion=plan, eliminado_en__isnull=True).select_related("responsable_tecnico", "validado_por").first()
    auditoria = RegistroAuditoriaUnidad.objects.filter(
        unidad=plan.unidad,
        objeto_id__in=[str(plan.pk), str(ejecucion.pk) if ejecucion else ""],
    ).select_related("usuario")[:20]
    detalle_ejecucion = {}
    if ejecucion:
        detalle_ejecucion = ejecucion.detalle_operativo or (
            construir_detalle_operativo(plan.reserva) if plan.reserva_id else {}
        )
    es_operador = puede_operar_modulo_unidad(request.user, plan.unidad, "practicas")
    # Quien valida puede reabrir lo validado, salvo que el informe del período ya se haya enviado.
    reapertura = ""
    if ejecucion and es_operador and ejecucion.estado == "validada":
        reapertura = (
            "bloqueada"
            if _informe_semestral_enviado(plan.unidad, ejecucion.fecha_ejecucion)
            else "disponible"
        )
    return render(
        request,
        "portal/pages/unidades/practicas/detalle.html",
        {
            "unidad": plan.unidad,
            "plan": plan,
            "ejecucion": ejecucion,
            "evidencias": list(ejecucion.evidencias.all()) if ejecucion else [],
            "detalle_ejecucion": detalle_ejecucion,
            "auditoria": auditoria,
            "es_operador": es_operador,
            "puede_editar": _puede_editar_plan(request.user, plan),
            "reapertura": reapertura,
            "minimo_motivo_reapertura": MINIMO_MOTIVO_REAPERTURA,
            "informe_semestral_enviado": INFORME_SEMESTRAL_ENVIADO,
        },
    )


def _render_practice_pdf(plan, ejecucion):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    # Los dos formatos comparten hoja: cada uno abre con su encabezado y su código.
    pie_pagina, CanvasNumerado, medidas = pie_institucional(pie="Formatos de práctica", apaisado=True)
    tinta = medidas["colores"]
    green, dark, gold = tinta["primario"], tinta["oscuro"], tinta["acento"]
    pale, line = tinta["suave"], tinta["linea"]
    ancho_util = medidas["ancho_util"]
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=medidas["pagesize"], leftMargin=medidas["margen"], rightMargin=medidas["margen"],
        topMargin=12 * mm, bottomMargin=medidas["margen_inferior"], title=f"Expediente {plan.codigo}",
    )
    styles = hoja_de_estilos()
    body = ParagraphStyle("PracticeBody", parent=styles["BodyText"], fontSize=8, textColor=dark, leading=11)
    small = ParagraphStyle("PracticeSmall", parent=body, fontSize=6.7, leading=9)
    story = []

    def institutional_head(document_label, document_code):
        """Mismo encabezado que el resto de la documentación, con el código de cada formato."""
        return encabezado_en_flujo(
            formato=document_label,
            metadatos=(
                f"Código: {document_code}",
                "Revisión: 01",
                f"Expediente: {plan.codigo}",
                f"Versión: {plan.numero_version}",
            ),
            ancho=ancho_util,
        )

    story.extend([
        institutional_head("PLANIFICACIÓN DE PRÁCTICAS ACADÉMICAS", "SLCID-PRACTICAS-PLAN"),
        Spacer(1, 5*mm),
    ])

    def section(label):
        table = Table([[label]], splitInRow=1, colWidths=[ancho_util])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),green),("TEXTCOLOR",(0,0),(-1,-1),colors.white),("FONTNAME",(0,0),(-1,-1),fuentes_documento()[1]),("FONTSIZE",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LINEBELOW",(0,0),(-1,-1),2,gold)]))
        return table

    def data_table(rows, widths):
        normalized = [[Paragraph(escape(str(a)), small), Paragraph(escape(str(b or "—")), body)] for a,b in rows]
        table = Table(normalized, splitInRow=1, colWidths=widths)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),pale),("FONTNAME",(0,0),(0,-1),fuentes_documento()[1]),("GRID",(0,0),(-1,-1),.35,line),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        return table

    story.extend([
        section("F1 · PLANIFICACIÓN"),
        data_table([
            ("N.º planificación", plan.codigo), ("Fecha y horario", f"{plan.fecha:%d/%m/%Y} · {plan.hora_inicio:%H:%M}–{plan.hora_fin:%H:%M}"),
            ("Carrera / semestre", f"{plan.carrera or '—'} · {plan.semestre or '—'}"), ("Asignatura", plan.asignatura),
            ("Docente / tutor", plan.docente_tutor), ("N.º práctica / guía", f"{plan.guia.codigo_guia or plan.guia.titulo} · v{plan.guia.numero_version}" if plan.guia else "Pendiente" if plan.requiere_guia else "No aplica"),
            ("Tema", plan.tema), ("Resultado de aprendizaje", plan.resultado_aprendizaje),
            ("Estudiantes", plan.estudiantes_planificados), ("Categoría de uso", plan.get_categoria_uso_display()),
            ("Laboratorio", plan.unidad.nombre), ("Responsable técnico", plan.responsable_tecnico.nombre_publico if plan.responsable_tecnico else "—"),
            ("Reserva vinculada", plan.reserva.codigo_reserva if plan.reserva else "Pendiente de vincular"), ("Estado", plan.get_estado_display()),
        ], [55*mm, ancho_util - 55*mm]),
    ])
    if ejecucion:
        detalle = ejecucion.detalle_operativo if isinstance(ejecucion.detalle_operativo, dict) else {}
        participantes = ", ".join(
            f"{item.get('nombre', '—')} ({item.get('asistencia', '—')})"
            for item in detalle.get("participantes", [])
        )
        consumibles = ", ".join(
            f"{item.get('nombre', '—')}: {item.get('consumida', '0')} {item.get('unidad', '')}"
            for item in detalle.get("consumibles", [])
        )
        story.extend([PageBreak(), institutional_head("EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS ACADÉMICAS", "SLCID-PRACTICAS-EJECUCION"), Spacer(1, 5*mm), section("F2 · EJECUCIÓN"), data_table([
            ("N.º referencia", plan.codigo), ("Fecha de ejecución", f"{ejecucion.fecha_ejecucion:%d/%m/%Y}"),
            ("Horario real", f"{ejecucion.hora_inicio_real:%H:%M}–{ejecucion.hora_fin_real:%H:%M}" if ejecucion.hora_inicio_real and ejecucion.hora_fin_real else "—"),
            ("Resultado", ejecucion.get_resultado_display()), ("Motivo", ejecucion.motivo),
            ("Estudiantes asistentes", ejecucion.estudiantes_asistentes), ("Recursos utilizados", ejecucion.recursos_utilizados),
            ("Asistencia nominal", participantes or "Sin detalle nominal"), ("Insumos consumidos", consumibles or "No registra consumo"),
            ("Incidente o accidente", "Sí" if ejecucion.tuvo_incidente else "No"), ("Observaciones del docente", ejecucion.observaciones_docente),
            ("Cumplimiento del resultado", ejecucion.get_cumplimiento_resultado_display() if ejecucion.cumplimiento_resultado else "—"),
            ("Responsable técnico", ejecucion.responsable_tecnico.nombre_publico if ejecucion.responsable_tecnico else "—"), ("Estado documental", ejecucion.get_estado_display()),
        ], [55*mm, ancho_util - 55*mm])])

    doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina, canvasmaker=CanvasNumerado)
    return buffer.getvalue()


@login_required
def planificacion_pdf_view(request, slug, plan_id):
    plan = _obtener_plan_visible(request, slug, plan_id)
    ejecucion = EjecucionPractica.objects.filter(planificacion=plan, eliminado_en__isnull=True).first()
    registrar_auditoria(request, unidad=plan.unidad, accion="descargar", objeto=plan, descripcion=f"PDF del expediente {plan.codigo}")
    response = HttpResponse(_render_practice_pdf(plan, ejecucion), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{plan.codigo}-practica.pdf"'
    return response


@login_required
def exportar_practicas_xlsx_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "practicas"):
        raise PermissionDenied("No tienes autorización para exportar esta unidad.")
    plans = PlanificacionPractica.objects.filter(
        unidad=unidad, eliminado_en__isnull=True
    ).select_related(
        "guia", "responsable_tecnico", "unidad", "ejecucion",
        "ejecucion__responsable_tecnico",
        "responsable_tecnico__usuario", "ejecucion__responsable_tecnico__usuario",
    ).defer("ejecucion__detalle_operativo").order_by("fecha", "hora_inicio")
    state = request.GET.get("estado", "")
    if state in dict(PlanificacionPractica.ESTADOS):
        plans = plans.filter(estado=state)
    content = render_practices_xlsx(plans, unidad=unidad)
    registrar_auditoria(request, unidad=unidad, accion="descargar", objeto=unidad, descripcion="Exportación XLSX de planificación y ejecución")
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="practicas-{unidad.slug}.xlsx"'
    return response
