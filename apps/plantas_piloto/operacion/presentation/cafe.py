"""Herramienta educativa sin escrituras, dispositivos ni servicios externos."""

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.directorio_unidades.models.core import Unidad
from apps.plantas_piloto.operacion.management.plantas.cafe import SLUG

NODOS_CADENA = (
    (
        "Finca, recepción y selección de cereza",
        "Identificar cosecha, pesar, muestrear y retirar fruta no apta.",
        "PPCA-BENEFICIO",
    ),
    (
        "Despulpado, fermentación y lavado",
        "La ruta lavado remueve mucílago; honey retiene el tratamiento definido y natural conserva fruto entero.",
        "PPCA-BENEFICIO",
    ),
    (
        "Secado solar o en horno/secador",
        "Elegir alternativa probada y controlar humedad por matriz, uniformidad y condición.",
        "PPCA-BENEFICIO",
    ),
    (
        "Recepción y pesaje de café seco",
        "Conciliar entrega, origen, propietario y condición antes de alimentar la línea.",
        "PPCA-RECEPCION-SECO",
    ),
    (
        "Muestreo y aceptación del laboratorio",
        "Evaluar humedad, integridad, defectos y preparación física; aceptar, retener o rechazar.",
        "PPCA-CALIDAD",
    ),
    (
        "Tolva, transporte y silo de alimentación",
        "Mantener el lote identificado, su saldo y flujo hacia la trilladora.",
        "PPCA-RECEPCION-SECO",
    ),
    (
        "Trilla o descascarado",
        "Retirar cubierta con ajuste para pergamino o fruto natural y pesar fracciones.",
        "PPCA-RECEPCION-SECO",
    ),
    (
        "Clasificación por tamaños",
        "Zarandas integradas o en serie separan tamaños; no confundir con selección de defectos.",
        "PPCA-RECEPCION-SECO",
    ),
    (
        "Selección por calidad en banda",
        "Retirar defectos visibles y cuerpos extraños y verificar la preparación mediante muestreo.",
        "PPCA-RECEPCION-SECO",
    ),
    (
        "Tostión por curvas y enfriamiento",
        "Aplicar perfil/version del equipo y lote, registrar eventos, masa y condición final.",
        "PPCA-TORREFACCION",
    ),
    (
        "Catación y control del perfil",
        "Comparar muestras y decidir aceptación; el laboratorio registra método y resultado.",
        "PPCA-CALIDAD",
    ),
    (
        "Silo de café tostado",
        "Recibir café enfriado, conservar identidad y dividir hacia grano o molino.",
        "PPCA-TORREFACCION",
    ),
    (
        "Molienda por tamaños, si se vende molido",
        "Regular y comprobar granulometría; registrar purga, masa y remanente. Grano entero evita esta operación.",
        "PPCA-TORREFACCION",
    ),
    (
        "Empaque en 250, 500 o 1.000 g",
        "Dosificar y comprobar peso neto, integridad y sello en la presentación elegida.",
        "PPCA-EMPAQUE",
    ),
    (
        "Etiquetado y empaque secundario",
        "Relacionar arte, lote y origen; conciliar bolsas por caja y pedido.",
        "PPCA-EMPAQUE",
    ),
    (
        "Bodega y despacho de producto liberado",
        "Ubicar, contar y despachar existencias aceptadas; retener devoluciones hasta evaluación.",
        "PPCA-EMPAQUE",
    ),
)


def resumen_cadena_cafe(unidad):
    if unidad.slug != SLUG:
        return None
    from apps.gestion_unidades.models.espacios import EspacioReservable

    if not EspacioReservable.objects.filter(
        unidad=unidad, codigo="PPCA-CALIDAD", activo=True
    ).exists():
        return None
    from django.urls import reverse

    return {
        "nombre": "Cadena completa: beneficiadero, planta y calidad",
        "url": reverse("cadena_cafe", args=[unidad.slug]),
    }


@require_GET
@xframe_options_sameorigin
def cadena_cafe(request, slug):
    unidad = get_object_or_404(
        Unidad, slug=slug, activo=True, dependencia="plantas_piloto"
    )
    if unidad.slug != SLUG:
        from django.http import Http404

        raise Http404("La cadena corresponde a la planta de café.")
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.recursos.presentation.equipo_referencia import referencias_por_area

    areas = list(
        EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by(
            "orden", "nombre", "pk"
        )
    )
    if not {
        "PPCA-BENEFICIO",
        "PPCA-RECEPCION-SECO",
        "PPCA-TORREFACCION",
        "PPCA-EMPAQUE",
        "PPCA-CALIDAD",
    }.issubset({a.codigo for a in areas}):
        from django.http import Http404

        raise Http404("La cadena necesita las cinco áreas publicadas.")
    from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

    # El equipamiento que la planta solo describe no existe: lo revisa quien la gestiona, el público no lo ve.
    referencias = referencias_por_area(areas, request.user) if puede_gestionar_unidad(request.user, unidad) else {}
    return render(
        request,
        "plantas_piloto/cafe_cadena.html",
        {
            "unidad": unidad,
            "volver_url": unidad.get_absolute_url() + "#procesos-protocolos",
            "generado_en": timezone.localtime(),
            "nodos": NODOS_CADENA,
            "grupos": [(a, referencias[a.pk]) for a in areas if referencias.get(a.pk)],
        },
    )


def herramientas_de_cafe(unidad):
    if unidad.slug != SLUG:
        return []
    from django.urls import reverse

    return [
        {
            "id": "cafe-calculadora",
            "nombre": "Café: rendimientos, secado, bolsas y costos",
            "url": reverse("calculadora_cafe", args=[unidad.slug]),
            "descripcion": "Explora escenarios de café de origen sin modificar existencias ni controlar equipos.",
        }
    ]


@require_GET
@xframe_options_sameorigin
def calculadora_cafe(request, slug):
    unidad = get_object_or_404(
        Unidad, slug=slug, activo=True, dependencia="plantas_piloto"
    )
    if unidad.slug != SLUG:
        from django.http import Http404

        raise Http404("La herramienta corresponde a la planta de café.")
    return render(
        request,
        "plantas_piloto/cafe_calculadora.html",
        {
            "unidad": unidad,
            "volver_url": unidad.get_absolute_url() + "#procesos-protocolos",
            "generado_en": timezone.localtime(),
        },
    )
