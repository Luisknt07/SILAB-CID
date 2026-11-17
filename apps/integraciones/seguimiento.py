"""Casos de uso de seguimiento por ámbito y versión. No aprueba ciencia ni gasto."""

import hashlib
import json
import re
from datetime import date
from calendar import monthrange

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.gobernanza import tiene_funcion, es_revisor_institucional
from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.documentos.models.expediente import DocumentoExpediente
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.integraciones.models import (
    ConsolidadoSeguimiento,
    EvidenciaSeguimiento,
    EventoSeguimiento,
    CompromisoSeguimiento,
    ReferenciaOficialInvestigacion,
    IdentidadActivoCompartido,
)


def huella(datos):
    return hashlib.sha256(
        json.dumps(
            datos,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


def centro_actual(referencia, *, solo_activos=True):
    from apps.centros_id.models import CentroID

    qs = CentroID.objects.filter(slug=referencia)
    if solo_activos:
        qs = qs.filter(activo=True)
    return qs.get()


def autoridad(usuario, ambito, referencia):
    if ambito == "dependencia":
        return (
            str(referencia).isdigit()
            and DependenciaAcademica.objects.filter(pk=referencia, activa=True).exists()
            and tiene_funcion(usuario, "adscripcion", referencia)
        )
    if ambito == "centro":
        try:
            centro = centro_actual(referencia)
        except ObjectDoesNotExist:
            return False
        return centro.responsable_id == usuario.pk and tiene_funcion(
            usuario, "centro", referencia
        )
    return False


def puede_preparar(usuario, ambito, referencia):
    if autoridad(usuario, ambito, referencia):
        return True
    if (
        not getattr(usuario, "is_authenticated", False)
        or not get_user_model().objects.filter(pk=usuario.pk, is_active=True).exists()
    ):
        return False
    if ambito == "dependencia":
        return Unidad.objects.filter(
            activo=True,
            adscrita_a_id=referencia,
            adscrita_a__activa=True,
            adscrita_a__receptores=usuario,
        ).exists()
    if ambito == "centro":
        try:
            centro = centro_actual(referencia)
        except ObjectDoesNotExist:
            return False
        # La designación del responsable debe estar completa; el superusuario
        # técnico no se convierte en gestor funcional de todos los Centros.
        return bool(
            centro.responsable_id
            and (
                centro.responsable_id == usuario.pk
                or centro.gestores.filter(pk=usuario.pk).exists()
            )
            and tiene_funcion(
                get_user_model().objects.get(pk=centro.responsable_id),
                "centro",
                referencia,
            )
        )
    return False


def puede_consultar(usuario, ambito, referencia):
    return es_revisor_institucional(usuario) or puede_preparar(
        usuario, ambito, referencia
    )


def fuentes_actuales(ambito, referencia, inicio, fin):
    if fin < inicio:
        raise ValidationError("Revise las fechas del período.")
    base = dict(
        ambito=ambito,
        referencia=str(referencia),
        inicio=str(inicio),
        fin=str(fin),
        esquema=1,
    )
    if ambito == "dependencia":
        dependencia = DependenciaAcademica.objects.get(pk=referencia, activa=True)
        unidades = list(
            Unidad.objects.filter(adscrita_a=dependencia, activo=True).order_by("pk")
        )
        registros = []
        for doc in (
            DocumentoExpediente.objects.filter(unidad__in=unidades)
            .select_related("exigido", "recurso")
            .order_by("pk")
        ):
            desde = doc.tramo_inicio or date(doc.anio, 7 if doc.corte == "B" else 1, 1)
            hasta = doc.tramo_fin or date(
                doc.anio, 6 if doc.corte == "A" else 12, 30 if doc.corte == "A" else 31
            )
            if doc.mes and not doc.tramo_inicio:
                desde = date(doc.anio, doc.mes, 1)
                hasta = date(doc.anio, doc.mes, monthrange(doc.anio, doc.mes)[1])
            if doc.exigido.periodicidad != "unica" and (desde > fin or hasta < inicio):
                continue
            registros.append(
                dict(
                    id=doc.pk,
                    unidad=doc.unidad_id,
                    codigo=doc.exigido.codigo,
                    version=doc.version,
                    estado=doc.estado,
                    actualizado=str(doc.actualizado_en),
                    recurso=doc.recurso_id,
                    sha256=doc.recurso.hash_sha256 if doc.recurso_id else "",
                    cargado_por=doc.cargado_por_id,
                    validado_por=doc.validado_por_id,
                    recibido_por=doc.recibido_por_id,
                    evaluado_por=doc.evaluado_por_id,
                    evaluacion=doc.evaluacion,
                    evaluacion_version=doc.evaluacion_version,
                )
            )
        base.update(
            nombre=dependencia.nombre,
            unidades=[
                dict(
                    id=u.pk,
                    nombre=u.nombre,
                    coordinador=u.administrador_id,
                    clasificacion=u.clasificacion_funcional,
                )
                for u in unidades
            ],
            documentos=registros,
            cobertura="Expedientes existentes; no certifica que el catálogo de exigibles esté completo.",
        )
    elif ambito == "centro":
        centro = centro_actual(referencia)
        from apps.centros_id.models import Componente, DocumentoCentro

        areas = list(
            Componente.objects.filter(centro=centro)
            .order_by("pk")
            .values("id", "nombre", "unidad_slug", "unidades_articuladas")
        )
        documentos = list(
            DocumentoCentro.objects.filter(centro=centro)
            .order_by("pk")
            .values(
                "id",
                "tipo",
                "titulo",
                "version",
                "periodo",
                "fecha",
                "estado_documental",
                "archivo",
                "enlace",
                "es_muestra",
                "validado_en",
                "fuente_validacion",
                "validado_por_id",
            )
        )
        almacen = DocumentoCentro._meta.get_field("archivo").storage
        for documento in documentos:
            documento["sha256_archivo"] = ""
            if documento["archivo"]:
                try:
                    with almacen.open(documento["archivo"], "rb") as stream:
                        digest = hashlib.sha256()
                        for bloque in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(bloque)
                        documento["sha256_archivo"] = digest.hexdigest()
                except (OSError, ValueError):
                    documento["archivo_no_disponible"] = True
        ultimas = {}
        for e in EvidenciaSeguimiento.objects.filter(
            centro=referencia, inicio=inicio, fin=fin
        ).order_by("version", "pk"):
            ultimas[e.codigo] = dict(
                id=e.pk,
                codigo=e.codigo,
                version=e.version,
                titulo=e.titulo,
                fuente=e.fuente,
                huella=e.huella_archivo,
                documento=e.documento_centro_id,
                registrado_por=e.registrado_por_id,
            )
        base.update(
            nombre=centro.nombre,
            estado_centro=centro.estado,
            responsable=centro.responsable_id,
            areas=areas,
            documentos_catalogo=documentos,
            evidencias=list(ultimas.values()),
            cobertura="Catálogo de gobierno y evidencias del período; su presencia no acredita aprobación científica.",
        )
    else:
        raise ValidationError("Seleccione dependencia o Centro.")
    # Se conserva JSON estable también para fechas y horas de ambas bases.
    return json.loads(json.dumps(base, default=str))


@transaction.atomic
def preparar(usuario, ambito, referencia, inicio, fin):
    if not puede_preparar(usuario, ambito, referencia):
        raise PermissionDenied("No puede preparar este consolidado.")
    # Serializa versiones por ámbito. Centros permanece como referencia pública
    # en su propia base; el bloqueo está en la designación del núcleo.
    from apps.core.models.gobernanza import AsignacionGobernanza

    list(
        AsignacionGobernanza.objects.select_for_update()
        .filter(rol__in=("adscripcion", "centro"), referencia=str(referencia))
        .order_by("pk")
    )
    datos = fuentes_actuales(ambito, referencia, inicio, fin)
    if ambito == "dependencia" and not datos["unidades"]:
        raise ValidationError(
            "No hay instalaciones activas adscritas a esta dependencia."
        )
    if ambito == "centro" and not datos["evidencias"]:
        raise ValidationError(
            "Registre las evidencias del período antes de preparar el consolidado."
        )
    anteriores = ConsolidadoSeguimiento.objects.filter(
        ambito=ambito, referencia=str(referencia), inicio=inicio, fin=fin
    )
    ultima = anteriores.order_by("-version").first()
    digest = huella(datos)
    if ultima and ultima.sha256 == digest:
        return ultima
    c = ConsolidadoSeguimiento.objects.create(
        ambito=ambito,
        referencia=str(referencia),
        inicio=inicio,
        fin=fin,
        version=(ultima.version + 1 if ultima else 1),
        fuentes=datos,
        sha256=digest,
        creado_por=usuario,
    )
    evento(c, usuario, "preparar")
    return c


def evento(consolidado, usuario, accion, observacion=""):
    EventoSeguimiento.objects.create(
        consolidado=consolidado,
        actor=usuario,
        accion=accion,
        observacion=observacion,
        sha256=consolidado.sha256,
    )


def vigente(consolidado):
    if ConsolidadoSeguimiento.objects.filter(
        ambito=consolidado.ambito,
        referencia=consolidado.referencia,
        inicio=consolidado.inicio,
        fin=consolidado.fin,
        version__gt=consolidado.version,
    ).exists():
        return False
    try:
        return consolidado.sha256 == huella(
            fuentes_actuales(
                consolidado.ambito,
                consolidado.referencia,
                consolidado.inicio,
                consolidado.fin,
            )
        )
    except ObjectDoesNotExist:
        return False


def exigir_vigencia(c, digest):
    if digest != c.sha256 or not vigente(c):
        raise ValidationError(
            "Las fuentes o la versión cambiaron. Prepare y revise el consolidado actualizado."
        )


@transaction.atomic
def validar_adscripcion(usuario, identificador, digest):
    c = ConsolidadoSeguimiento.objects.select_for_update().get(pk=identificador)
    if not autoridad(usuario, c.ambito, c.referencia):
        raise PermissionDenied(
            "Se requiere la designación vigente y el ámbito de adscripción."
        )
    exigir_vigencia(c, digest)
    if c.estado != "preparado":
        raise ValidationError("La validación ya está registrada para esta versión.")
    c.validado_por = usuario
    c.validado_en = timezone.now()
    c.estado = "validado"
    c.save(update_fields=["validado_por", "validado_en", "estado"])
    evento(c, usuario, "validar_adscripcion")
    return c


def exigir_revision_independiente(usuario, c):
    if not es_revisor_institucional(usuario):
        raise PermissionDenied("Se requiere designación de seguimiento institucional.")
    conflicto = usuario.pk == c.validado_por_id
    if c.ambito == "dependencia":
        ids = [u["id"] for u in c.fuentes["unidades"]]
        from apps.documentos.presentation.independencia_revision import (
            exigir_revision_independiente as revisar_autoria,
        )

        for documento in DocumentoExpediente.objects.filter(
            pk__in=[d["id"] for d in c.fuentes["documentos"]]
        ).select_related("unidad"):
            revisar_autoria(documento, usuario, documento.unidad)
        conflicto = (
            conflicto
            or Unidad.objects.filter(pk__in=ids, administrador=usuario).exists()
        )
        conflicto = (
            conflicto
            or ResponsableUnidad.objects.filter(
                unidad_id__in=ids, usuario=usuario, activo=True, rol="coordinacion"
            ).exists()
        )
        conflicto = conflicto or any(
            d["cargado_por"] == usuario.pk
            or (d["validado_por"] == usuario.pk and d["recibido_por"] != usuario.pk)
            for d in c.fuentes["documentos"]
        )
    else:
        centro = centro_actual(c.referencia)
        conflicto = (
            conflicto
            or centro.responsable_id == usuario.pk
            or centro.gestores.filter(pk=usuario.pk).exists()
        )
        conflicto = conflicto or any(
            d.get("validado_por_id") == usuario.pk
            for d in c.fuentes["documentos_catalogo"]
        )
        conflicto = conflicto or any(
            e["registrado_por"] == usuario.pk for e in c.fuentes["evidencias"]
        )
    if conflicto:
        raise ValidationError(
            "La revisión institucional requiere otra persona autorizada, independiente de esta gestión."
        )


@transaction.atomic
def revisar(usuario, identificador, digest, decision, observacion=""):
    c = ConsolidadoSeguimiento.objects.select_for_update().get(pk=identificador)
    exigir_revision_independiente(usuario, c)
    exigir_vigencia(c, digest)
    if c.estado != "validado" or decision not in ("revisado", "observado"):
        raise ValidationError(
            "Revise una versión validada y seleccione una decisión válida."
        )
    if decision == "observado" and not observacion.strip():
        raise ValidationError("Describa las observaciones que deben corregirse.")
    c.estado = decision
    c.save(update_fields=["estado"])
    evento(c, usuario, decision, observacion)
    return c


def validar_enlace(fuente):
    URLValidator(schemes=["https"])(fuente)


@transaction.atomic
def registrar_evidencia(
    usuario,
    centro,
    codigo,
    inicio,
    fin,
    titulo,
    fuente,
    huella_archivo="",
    documento_id=None,
):
    if not puede_preparar(usuario, "centro", centro):
        raise PermissionDenied
    validar_enlace(fuente)
    if (
        not re.fullmatch(r"[a-z0-9_-]{1,100}", codigo)
        or not titulo.strip()
        or fin < inicio
    ):
        raise ValidationError(
            "Revise el código, el título y el período de la evidencia."
        )
    if huella_archivo and not re.fullmatch(r"[0-9a-f]{64}", huella_archivo):
        raise ValidationError(
            "La huella debe ser SHA-256; déjela vacía si no fue verificada."
        )
    from apps.core.models.gobernanza import AsignacionGobernanza

    list(
        AsignacionGobernanza.objects.select_for_update()
        .filter(rol="centro", referencia=centro)
        .order_by("pk")
    )
    if documento_id:
        from apps.centros_id.models import DocumentoCentro

        if not DocumentoCentro.objects.filter(
            pk=documento_id, centro__slug=centro
        ).exists():
            raise ValidationError("El documento no pertenece al Centro indicado.")
    ultimo = (
        EvidenciaSeguimiento.objects.filter(
            centro=centro, codigo=codigo, inicio=inicio, fin=fin
        ).aggregate(n=Max("version"))["n"]
        or 0
    )
    return EvidenciaSeguimiento.objects.create(
        centro=centro,
        codigo=codigo,
        inicio=inicio,
        fin=fin,
        titulo=titulo,
        fuente=fuente,
        huella_archivo=huella_archivo,
        documento_centro_id=documento_id,
        version=ultimo + 1,
        registrado_por=usuario,
    )


@transaction.atomic
def abrir_compromiso(usuario, consolidado_id, descripcion, responsable_id, plazo):
    c = ConsolidadoSeguimiento.objects.select_for_update().get(pk=consolidado_id)
    exigir_revision_independiente(usuario, c)
    exigir_vigencia(c, c.sha256)
    responsable = get_user_model().objects.get(pk=responsable_id, is_active=True)
    if (
        not puede_preparar(responsable, c.ambito, c.referencia)
        or not descripcion.strip()
    ):
        raise ValidationError(
            "Indique una acción y una persona habilitada del ámbito correspondiente."
        )
    if (
        c.estado not in ("observado", "revisado", "validado")
        or plazo < timezone.localdate()
    ):
        raise ValidationError("Revise la versión y el plazo del compromiso.")
    p = CompromisoSeguimiento.objects.create(
        consolidado=c,
        descripcion=descripcion,
        responsable=responsable,
        plazo=plazo,
        abierto_por=usuario,
    )
    evento(c, usuario, "abrir_mejora", f"{p.pk}: {descripcion}")
    return p


@transaction.atomic
def responder_compromiso(usuario, identificador, respuesta, evidencia):
    p = (
        CompromisoSeguimiento.objects.select_for_update()
        .select_related("consolidado")
        .get(pk=identificador)
    )
    if usuario.pk != p.responsable_id or not puede_preparar(
        usuario, p.consolidado.ambito, p.consolidado.referencia
    ):
        raise PermissionDenied
    if p.estado == "verificado" or not respuesta.strip():
        raise ValidationError("El compromiso está cerrado o la respuesta está vacía.")
    validar_enlace(evidencia)
    p.respuesta, p.evidencia, p.estado = respuesta, evidencia, "respondido"
    p.save(update_fields=["respuesta", "evidencia", "estado"])
    evento(
        p.consolidado, usuario, "responder_mejora", f"{p.pk}: {respuesta}\n{evidencia}"
    )
    return p


@transaction.atomic
def verificar_compromiso(usuario, identificador, observacion):
    p = (
        CompromisoSeguimiento.objects.select_for_update()
        .select_related("consolidado")
        .get(pk=identificador)
    )
    exigir_revision_independiente(usuario, p.consolidado)
    if (
        p.estado != "respondido"
        or usuario.pk == p.responsable_id
        or not observacion.strip()
    ):
        raise ValidationError(
            "Se requiere respuesta y una verificación independiente motivada."
        )
    p.estado, p.verificado_por, p.verificado_en = "verificado", usuario, timezone.now()
    p.save(update_fields=["estado", "verificado_por", "verificado_en"])
    evento(p.consolidado, usuario, "verificar_mejora", f"{p.pk}: {observacion}")
    return p


def registrar_referencia(
    usuario, centro, tipo, objeto_id, sistema, identificador, fuente, estado_oficial
):
    if not puede_preparar(usuario, "centro", centro) and not tiene_funcion(
        usuario, "investigacion"
    ):
        raise PermissionDenied
    from apps.centros_id.models import Proyecto, Resultado

    modelo = {"proyecto": Proyecto, "resultado": Resultado}.get(tipo)
    if (
        not modelo
        or not modelo.objects.filter(pk=objeto_id, centro__slug=centro).exists()
    ):
        raise ValidationError("El proyecto o resultado no pertenece a ese Centro.")
    validar_enlace(fuente)
    if not all(str(x).strip() for x in (sistema, identificador, estado_oficial)):
        raise ValidationError(
            "Registre sistema, expediente oficial y estado según su fuente."
        )
    r = ReferenciaOficialInvestigacion.objects.create(
        centro=centro,
        tipo=tipo,
        objeto_id=objeto_id,
        sistema=sistema,
        identificador=identificador,
        fuente=fuente,
        estado_oficial=estado_oficial,
        registrado_por=usuario,
    )
    return r


@transaction.atomic
def verificar_referencia(usuario, identificador):
    if not tiene_funcion(usuario, "investigacion"):
        raise PermissionDenied(
            "Solo Investigación e Innovación verifica la correspondencia con su fuente oficial."
        )
    r = ReferenciaOficialInvestigacion.objects.select_for_update().get(pk=identificador)
    if r.verificado_en:
        raise ValidationError(
            "Esta referencia ya está verificada; un cambio requiere otra constancia."
        )
    r.verificado_por, r.verificado_en = usuario, timezone.now()
    r.save(update_fields=["verificado_por", "verificado_en"])
    return r


def registrar_activo(usuario, codigo, origen, objeto_id, fuente):
    """La identidad se registra una vez, sin crear equipos o agendas paralelas."""
    codigo = codigo.strip().upper()
    validar_enlace(fuente)
    if origen == "directorio":
        from apps.recursos.models.unidades import UnidadEquipo

        equipo = UnidadEquipo.objects.select_related("laboratorio").get(pk=objeto_id)
        unidad = equipo.laboratorio
        if (
            not unidad
            or not unidad.adscrita_a_id
            or not autoridad(usuario, "dependencia", unidad.adscrita_a_id)
        ):
            raise PermissionDenied
        if not equipo.codigo_bien or codigo != equipo.codigo_bien.strip().upper():
            raise ValidationError(
                "El código debe coincidir con el inventario patrimonial registrado."
            )
    elif origen == "centro":
        from apps.centros_id.models import EquipoCentro

        equipo = EquipoCentro.objects.select_related("componente__centro").get(
            pk=objeto_id
        )
        if not autoridad(usuario, "centro", equipo.componente.centro.slug):
            raise PermissionDenied
        if (
            not equipo.es_activo_individual
            or equipo.cantidad != 1
            or not equipo.codigo.strip()
            or codigo != equipo.codigo.strip().upper()
        ):
            raise ValidationError(
                "Se requiere un activo individual identificado, no una categoría propuesta."
            )
    else:
        raise ValidationError("Elija un inventario de origen.")
    obj = IdentidadActivoCompartido(
        codigo_institucional=codigo,
        origen=origen,
        objeto_id=objeto_id,
        fuente=fuente,
        registrado_por=usuario,
    )
    obj.full_clean()
    obj.save()
    return obj
