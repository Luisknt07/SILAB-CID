"""Mesa funcional accesible sin convertir a sus responsables en superusuarios."""

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from apps.core.gobernanza import (
    asignaciones_vigentes,
    es_revisor_institucional,
    tiene_funcion,
)
from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.integraciones import seguimiento as servicio
from apps.integraciones.models import (
    ConsolidadoSeguimiento,
    ReferenciaOficialInvestigacion,
    IdentidadActivoCompartido,
)
from apps.integraciones.forms import (
    PeriodoForm,
    EvidenciaForm,
    ReferenciaForm,
    ActivoForm,
)


def opciones(usuario):
    opciones = []
    for d in DependenciaAcademica.objects.filter(activa=True).order_by("nombre"):
        if servicio.puede_consultar(usuario, "dependencia", str(d.pk)):
            opciones.append((f"dependencia:{d.pk}", d.nombre))
    from apps.centros_id.models import CentroID

    for c in CentroID.objects.filter(activo=True).order_by("nombre"):
        if servicio.puede_consultar(usuario, "centro", c.slug):
            opciones.append(
                (f"centro:{c.slug}", f"{c.nombre} ({c.get_estado_display()})")
            )
    return opciones


def error_visible(request, error):
    messages.error(
        request,
        " ".join(error.messages)
        if isinstance(error, ValidationError)
        else "No se pudo completar: compruebe el registro, su vigencia y que no esté duplicado.",
    )


@login_required
@never_cache
def mesa(request):
    opciones_usuario = opciones(request.user)
    if (
        not opciones_usuario
        and not asignaciones_vigentes(request.user).exists()
        and not request.user.is_superuser
    ):
        raise PermissionDenied
    preparables = [
        (clave, nombre)
        for clave, nombre in opciones_usuario
        if servicio.puede_preparar(request.user, *clave.split(":", 1))
    ]
    form = PeriodoForm(request.POST or None, opciones=preparables)
    if request.method == "POST" and form.is_valid():
        ambito, referencia = form.cleaned_data["ambito"].split(":", 1)
        try:
            c = servicio.preparar(
                request.user,
                ambito,
                referencia,
                form.cleaned_data["inicio"],
                form.cleaned_data["fin"],
            )
            return redirect("seguimiento_detalle", pk=c.pk)
        except (ValidationError, IntegrityError, ObjectDoesNotExist) as e:
            error_visible(request, e)
    permitidos = {v for v, _ in opciones_usuario}
    filas = [
        c
        for c in ConsolidadoSeguimiento.objects.all()
        if f"{c.ambito}:{c.referencia}" in permitidos
    ]
    referencias = ReferenciaOficialInvestigacion.objects.all().order_by("-pk")
    if not tiene_funcion(
        request.user, "investigacion"
    ) and not es_revisor_institucional(request.user):
        centros = [v.split(":", 1)[1] for v in permitidos if v.startswith("centro:")]
        referencias = referencias.filter(centro__in=centros)
    return render(
        request,
        "integraciones/seguimiento_mesa.html",
        dict(
            form=form,
            filas=filas,
            referencias=referencias[:100],
            ciencia=tiene_funcion(request.user, "investigacion"),
            institucional=es_revisor_institucional(request.user),
            sin_adscripcion=Unidad.objects.filter(
                activo=True, adscrita_a__isnull=True
            ).count()
            if es_revisor_institucional(request.user)
            else None,
            activos=IdentidadActivoCompartido.objects.count()
            if es_revisor_institucional(request.user)
            else None,
        ),
    )


@login_required
@never_cache
def detalle(request, pk):
    c = get_object_or_404(ConsolidadoSeguimiento, pk=pk)
    if not servicio.puede_consultar(request.user, c.ambito, c.referencia):
        raise PermissionDenied
    if request.method == "POST":
        accion = request.POST.get("accion")
        try:
            if accion == "validar":
                servicio.validar_adscripcion(
                    request.user, pk, request.POST.get("sha256")
                )
            elif accion in ("revisado", "observado"):
                servicio.revisar(
                    request.user,
                    pk,
                    request.POST.get("sha256"),
                    accion,
                    request.POST.get("observacion", ""),
                )
            elif accion == "abrir_mejora":
                servicio.abrir_compromiso(
                    request.user,
                    pk,
                    request.POST.get("descripcion", ""),
                    int(request.POST.get("responsable", "0")),
                    date.fromisoformat(request.POST.get("plazo", "")),
                )
            elif accion in ("responder", "verificar"):
                p = get_object_or_404(c.compromisos, pk=request.POST.get("compromiso"))
                if accion == "responder":
                    servicio.responder_compromiso(
                        request.user,
                        p.pk,
                        request.POST.get("respuesta", ""),
                        request.POST.get("evidencia", ""),
                    )
                else:
                    servicio.verificar_compromiso(
                        request.user, p.pk, request.POST.get("observacion", "")
                    )
            elif accion == "revisar_documento" and c.ambito == "dependencia":
                # Solo referencias de esta instantánea y versión; el servicio
                # documental vuelve a comprobar independencia e integridad.
                from apps.documentos.models.expediente import DocumentoExpediente
                from apps.documentos.presentation.revision_documental import (
                    decidir_desde_listado,
                )

                servicio.exigir_revision_independiente(request.user, c)
                servicio.exigir_vigencia(c, request.POST.get("sha256"))
                fuente = next(
                    (
                        d
                        for d in c.fuentes["documentos"]
                        if str(d["id"]) == request.POST.get("documento")
                    ),
                    None,
                )
                if not fuente:
                    raise PermissionDenied
                doc = DocumentoExpediente.objects.get(pk=fuente["id"])
                decidir_desde_listado(
                    doc,
                    request.user,
                    version=fuente["version"],
                    huella=fuente["sha256"],
                    decision=request.POST.get("decision"),
                    observacion=request.POST.get("observacion", ""),
                )
            else:
                raise ValidationError("Seleccione una acción válida.")
            messages.success(
                request, "Decisión registrada con su versión y responsable."
            )
            return redirect("seguimiento_detalle", pk=pk)
        except (ValidationError, IntegrityError, ObjectDoesNotExist, ValueError) as e:
            error_visible(request, e)
    c.refresh_from_db()
    from django.contrib.auth import get_user_model

    if c.ambito == "dependencia":
        from apps.core.models.gobernanza import AsignacionGobernanza

        dependencia = DependenciaAcademica.objects.filter(pk=c.referencia).first()
        candidatos_ids = (
            list(dependencia.receptores.values_list("pk", flat=True))
            if dependencia
            else []
        )
        candidatos_ids += list(
            AsignacionGobernanza.objects.filter(
                rol="adscripcion", referencia=c.referencia
            ).values_list("usuario_id", flat=True)
        )
    else:
        centro = servicio.centro_actual(c.referencia, solo_activos=False)
        candidatos_ids = list(centro.gestores.values_list("pk", flat=True)) + [
            centro.responsable_id
        ]
    candidatos = [
        u
        for u in get_user_model().objects.filter(pk__in=candidatos_ids, is_active=True)
        if servicio.puede_preparar(u, c.ambito, c.referencia)
    ]
    return render(
        request,
        "integraciones/seguimiento_detalle.html",
        dict(
            c=c,
            candidatos=candidatos,
            vigente=servicio.vigente(c),
            autoridad=servicio.autoridad(request.user, c.ambito, c.referencia),
            institucional=es_revisor_institucional(request.user),
        ),
    )


@login_required
@never_cache
def registrar(request, tipo):
    especificacion = {
        "evidencia": (
            EvidenciaForm,
            servicio.registrar_evidencia,
            "Evidencia del Centro",
        ),
        "referencia": (
            ReferenciaForm,
            servicio.registrar_referencia,
            "Referencia al Portafolio oficial",
        ),
        "activo": (
            ActivoForm,
            servicio.registrar_activo,
            "Identidad de activo compartido",
        ),
    }
    if tipo not in especificacion or not (
        opciones(request.user) or tiene_funcion(request.user, "investigacion")
    ):
        raise PermissionDenied
    clase, guardar, titulo = especificacion[tipo]
    form = clase(request.POST or None)
    centros_permitidos = [
        v.split(":", 1)[1]
        for v, _ in opciones(request.user)
        if v.startswith("centro:")
        and servicio.puede_preparar(request.user, "centro", v.split(":", 1)[1])
    ]
    from apps.centros_id.models import (
        CentroID,
        DocumentoCentro,
        Proyecto,
        Resultado,
        EquipoCentro,
    )

    if tipo == "evidencia":
        form.fields["centro"].choices = list(
            CentroID.objects.filter(slug__in=centros_permitidos).values_list(
                "slug", "nombre"
            )
        )
        form.fields["documento_id"].choices = [("", "Sin documento vinculado")] + [
            (d.pk, f"{d.centro.nombre}: {d.titulo} ({d.version or 'sin versión'})")
            for d in DocumentoCentro.objects.filter(
                centro__slug__in=centros_permitidos
            ).select_related("centro")
        ]
    elif tipo == "referencia":
        centros_ciencia = (
            CentroID.objects.filter(activo=True).values_list("slug", flat=True)
            if tiene_funcion(request.user, "investigacion")
            else centros_permitidos
        )
        registros = []
        for etiqueta, modelo in [("proyecto", Proyecto), ("resultado", Resultado)]:
            registros += [
                (
                    f"{p.centro.slug}:{etiqueta}:{p.pk}",
                    f"{p.centro.nombre} · {etiqueta}: {p.titulo}",
                )
                for p in modelo.objects.filter(
                    centro__slug__in=centros_ciencia
                ).select_related("centro")
            ]
        form.fields["registro"].choices = registros
    else:
        from apps.recursos.models.unidades import UnidadEquipo

        dependencias = [
            v.split(":", 1)[1]
            for v, _ in opciones(request.user)
            if v.startswith("dependencia:")
            and servicio.autoridad(request.user, "dependencia", v.split(":", 1)[1])
        ]
        equipos = [
            (
                f"directorio:{e.pk}",
                f"{e.laboratorio.nombre} · {e.codigo_bien}: {e.equipo.nombre}",
            )
            for e in UnidadEquipo.objects.filter(
                laboratorio__adscrita_a_id__in=dependencias, codigo_bien__isnull=False
            )
            .exclude(codigo_bien="")
            .select_related("laboratorio", "equipo")
        ]
        equipos += [
            (f"centro:{e.pk}", f"{e.componente.centro.nombre} · {e.codigo}: {e.nombre}")
            for e in EquipoCentro.objects.filter(
                componente__centro__slug__in=centros_permitidos,
                es_activo_individual=True,
                cantidad=1,
            )
            .exclude(codigo="")
            .select_related("componente__centro")
            if servicio.autoridad(request.user, "centro", e.componente.centro.slug)
        ]
        form.fields["registro"].choices = equipos
    if request.method == "POST" and form.is_valid():
        try:
            datos = dict(form.cleaned_data)
            if tipo == "referencia":
                centro, clase_registro, identificador = datos.pop("registro").split(
                    ":", 2
                )
                datos.update(
                    centro=centro, tipo=clase_registro, objeto_id=int(identificador)
                )
            elif tipo == "activo":
                origen, identificador = datos.pop("registro").split(":", 1)
                datos.update(origen=origen, objeto_id=int(identificador))
            guardar(request.user, **datos)
            messages.success(
                request, "Registro conservado con su fuente y responsable."
            )
            return redirect("seguimiento_mesa")
        except (ValidationError, IntegrityError, ObjectDoesNotExist) as e:
            error_visible(request, e)
    return render(
        request,
        "integraciones/seguimiento_registro.html",
        dict(form=form, titulo=titulo),
    )


@login_required
@never_cache
@require_POST
def verificar_referencia(request, pk):
    try:
        servicio.verificar_referencia(request.user, pk)
        messages.success(
            request,
            "Correspondencia con la fuente oficial verificada. No se emitió una aprobación científica nueva.",
        )
    except ValidationError as e:
        error_visible(request, e)
    return redirect("seguimiento_mesa")


@login_required
@never_cache
def exportar(request):
    if not es_revisor_institucional(request.user):
        raise PermissionDenied
    try:
        inicio, fin = (
            date.fromisoformat(request.GET["inicio"]),
            date.fromisoformat(request.GET["fin"]),
        )
        if fin < inicio:
            raise ValueError
    except (KeyError, ValueError):
        return JsonResponse(
            {"error": "Indique inicio y fin válidos (AAAA-MM-DD)."}, status=400
        )
    filas, vistas = [], set()
    for c in ConsolidadoSeguimiento.objects.filter(inicio=inicio, fin=fin).order_by(
        "-version"
    ):
        clave = c.ambito, c.referencia
        if clave in vistas:
            continue
        vistas.add(clave)
        filas.append(
            dict(
                id=c.pk,
                ambito=c.ambito,
                referencia=c.referencia,
                version=c.version,
                estado=c.estado,
                vigente=servicio.vigente(c),
                validado_por=c.validado_por_id,
                sha256=c.sha256,
                fuentes=c.fuentes,
            )
        )
    esperadas = [valor for valor, _ in opciones(request.user)]
    return JsonResponse(
        dict(
            inicio=inicio,
            fin=fin,
            consolidados=filas,
            sin_consolidado=[
                a for a in esperadas if tuple(a.split(":", 1)) not in vistas
            ],
            sin_adscripcion=Unidad.objects.filter(
                activo=True, adscrita_a__isnull=True
            ).count(),
            nota="No se suman inventarios vinculados ni se certifica producción científica. Solo las versiones revisadas y vigentes tienen revisión institucional actual.",
        ),
        json_dumps_params={"ensure_ascii": False},
        headers={
            "Content-Disposition": 'attachment; filename="consolidado-seguimiento.json"'
        },
    )


@login_required
@never_cache
def archivo_documental(request, pk, documento_id):
    import hashlib
    from django.http import FileResponse, Http404
    from apps.recursos.models.recursos import Recurso

    c = get_object_or_404(ConsolidadoSeguimiento, pk=pk, ambito="dependencia")
    if not servicio.puede_consultar(request.user, c.ambito, c.referencia):
        raise PermissionDenied
    fuente = next((d for d in c.fuentes["documentos"] if d["id"] == documento_id), None)
    if not fuente or not fuente["recurso"] or not fuente["sha256"]:
        raise Http404
    recurso = get_object_or_404(Recurso, pk=fuente["recurso"])
    try:
        archivo = recurso.archivo.open("rb")
        digest = hashlib.sha256()
        for bloque in archivo.chunks():
            digest.update(bloque)
        if digest.hexdigest() != fuente["sha256"]:
            archivo.close()
            raise Http404("El archivo no coincide con la versión conservada.")
        archivo.seek(0)
    except (OSError, ValueError):
        raise Http404("Archivo no disponible.") from None
    respuesta = FileResponse(
        archivo,
        as_attachment=True,
        filename=f"{fuente['codigo']}-v{fuente['version']}.pdf",
        content_type="application/pdf",
    )
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@login_required
@never_cache
def archivo_centro(request, pk, documento_id):
    import hashlib
    from pathlib import PurePosixPath
    from django.http import FileResponse, Http404
    from apps.centros_id.models import DocumentoCentro

    c = get_object_or_404(ConsolidadoSeguimiento, pk=pk, ambito="centro")
    if not servicio.puede_consultar(request.user, c.ambito, c.referencia):
        raise PermissionDenied
    fuente = next(
        (d for d in c.fuentes["documentos_catalogo"] if d["id"] == documento_id), None
    )
    if not fuente or not fuente.get("archivo") or not fuente.get("sha256_archivo"):
        raise Http404
    almacen = DocumentoCentro._meta.get_field("archivo").storage
    try:
        archivo = almacen.open(fuente["archivo"], "rb")
        digest = hashlib.sha256()
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
        if digest.hexdigest() != fuente["sha256_archivo"]:
            archivo.close()
            raise Http404("El archivo no coincide con la versión conservada.")
        archivo.seek(0)
    except (OSError, ValueError):
        raise Http404("Archivo no disponible.") from None
    respuesta = FileResponse(
        archivo,
        as_attachment=True,
        filename=PurePosixPath(fuente["archivo"]).name,
        content_type="application/octet-stream",
    )
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta
