"""Fichas individuales de equipamiento descrito, sin inventar activos físicos."""

from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.gestion_unidades.presentation.gobierno_editorial import (
    objeto_visible_para,
    visibles_para,
)


def referencias_por_area(areas, usuario=None):
    """Consultas agrupadas para referencias y su gobierno editorial, sin N+1."""
    resultado = {}
    registros = (
        ElementoFichaArea.objects.filter(
            ficha__espacio__in=areas,
            ficha__publicada=True,
            tipo="equipo",
        ).filter(Q(registrado__isnull=True) | Q(solo_referencia=True))
        .select_related("ficha__espacio")
        .order_by("orden", "nombre", "pk")
    )
    filas = list(registros)
    if filas and usuario is not None:
        filas = visibles_para(filas, filas[0].ficha.espacio.unidad, usuario)
    for elemento in filas:
        resultado.setdefault(elemento.ficha.espacio_id, []).append(elemento)
    return resultado


def detalle_de_referencia(elemento, codigo, usuario):
    """Adapta la descripción a la ficha común sin fabricar unidades físicas."""
    pares = elemento.lista_especificaciones
    especificaciones = dict(pares)
    foto = {"credito": "Imagen referencial del tipo de equipamiento", "fuente": ""}
    videos = []
    if elemento.ficha.espacio.unidad.slug == "planta-piloto-cafe":
        from apps.plantas_piloto.operacion.management.plantas.cafe_medios import (
            imagen_de_equipo,
        )

        candidata = imagen_de_equipo(codigo.removeprefix("CAF-REF-"))
        if candidata and candidata["ruta"] == elemento.imagen_estatica:
            foto = candidata
    videos = [
        {
            "id": v.youtube_id,
            "titulo": v.nombre,
            "canal": v.ejemplo,
            "descripcion": v.para_que,
        }
        for v in visibles_para(
            ElementoFichaArea.objects.filter(ficha=elemento.ficha, tipo="video"),
            elemento.ficha.espacio.unidad,
            usuario,
        )
        if v.youtube_id
    ]
    tipo = {
        "nombre": elemento.nombre,
        "codigo": codigo,
        "credito_imagen": foto["credito"] if elemento.es_referencial else "",
        "fuente_imagen": foto.get("fuente", "") if elemento.es_referencial else "",
        "licencia_imagen": foto.get("licencia", "") if elemento.es_referencial else "",
        "origen_datos_tecnicos": "referencia",
    }
    estandar = {
        "grupo": "Equipamiento de la cadena de café"
        if elemento.ficha.espacio.unidad.slug == "planta-piloto-cafe"
        else "Equipamiento de la unidad",
        "especificaciones": [
            {
                "clave": clave,
                "valor": valor,
                "categoria": "Operación y control",
                "icono": elemento.icono or "fas fa-cogs",
            }
            for clave, valor in pares
        ],
        "capacidad": [
            {
                "clave": "Instalación y dimensionamiento",
                "valor": especificaciones["Instalación y dimensionamiento"],
            }
        ]
        if especificaciones.get("Instalación y dimensionamiento")
        else [],
        "descripcion": elemento.para_que
        + "\n\n"
        + especificaciones.get("Principio", ""),
        "componentes": [
            {
                "clave": "repuesto",
                "titulo": "Insumos y materiales",
                "icono": "fas fa-boxes",
                "items": [
                    {
                        "nombre": t,
                        "naturaleza": "consumible",
                        "cantidad": None,
                        "icono": "fas fa-box-open",
                    }
                    for t in elemento.lista_consumibles
                ],
            }
        ],
        "modos": [
            {
                "nombre": "Funcionamiento y flujo",
                "descripcion": especificaciones.get("Principio", elemento.para_que),
                "aplicaciones": [
                    clave + ": " + especificaciones[clave]
                    for clave in ("Entrada", "Salida", "Controles y mediciones")
                    if clave in especificaciones
                ],
                "requisitos": [especificaciones["Aceptación técnica"]]
                if especificaciones.get("Aceptación técnica")
                else [],
            }
        ],
        "requisitos": [
            (k, v)
            for k, v in pares
            if k in ("Instalación y dimensionamiento", "Aceptación técnica")
        ],
        "videos": [{**v, "de_familia": True} for v in videos],
    }
    return {
        "tipo": tipo,
        "es_propuesta": elemento.solo_referencia,
        "cantidad_referencia": elemento.cantidad,
        "imagen": elemento.imagen_url,
        "imagen_referencial": elemento.es_referencial,
        "lema": elemento.para_que,
        "icono": elemento.icono or "fas fa-cogs",
        "nivel": elemento.get_nivel_display(),
        "estandar": estandar,
        "unidades": [],
        "disponibles": 0,
        "cuidados": elemento.lista_cuidados,
        "insumos_de_ficha": elemento.lista_consumibles,
        "uso_propio": elemento.para_que,
        "areas": [
            {
                "nombre": elemento.ficha.espacio.nombre,
                "url": reverse(
                    "area_unidad",
                    args=[
                        elemento.ficha.espacio.unidad.slug,
                        elemento.ficha.espacio.codigo,
                    ],
                ),
                "icono": "fas fa-vector-square",
            }
        ],
        "documentos": [
            {
                "nombre": "Referencia técnica externa",
                "url": elemento.url,
                "icono": "fas fa-book",
            }
        ]
        if elemento.url
        else [],
    }


@require_GET
@xframe_options_sameorigin
def ficha_equipo_referencia(request, slug, elemento_id):
    elemento = get_object_or_404(
        ElementoFichaArea.objects.select_related(
            "ficha__espacio__unidad", "registrado"
        ),
        pk=elemento_id,
        tipo="equipo",
        ficha__espacio__unidad__slug=slug,
        ficha__espacio__unidad__activo=True,
        ficha__espacio__activo=True,
    )
    area, ficha = elemento.ficha.espacio, elemento.ficha
    unidad = area.unidad
    gestor = puede_gestionar_unidad(request.user, unidad)
    if not ficha.publicada and not gestor:
        raise Http404("La ficha no está publicada.")
    if not objeto_visible_para(elemento, unidad, request.user):
        raise Http404("La ficha no está publicada.")
    if elemento.registrado_id and not elemento.solo_referencia:
        return redirect("ficha_equipo_publica", slug, elemento.registrado.codigo_unidad)
    from apps.gestion_unidades.presentation.area_unidad import revisar_ficha

    indice = FichaContenido.objects.filter(
        content_type=ContentType.objects.get_for_model(elemento), object_id=elemento.pk
    ).first()
    codigo = indice.codigo if indice else f"REF-{elemento.pk}"
    from apps.reservas.presentation.proceso import recetas_para_practica

    procesos = visibles_para(recetas_para_practica(unidad), unidad, request.user)

    def nombre_proceso(p):
        return p.nombre_publico

    if unidad.slug == "planta-piloto-cafe":
        from apps.plantas_piloto.operacion.management.plantas.cafe_medios import (
            nombre_de_proceso,
        )

        def nombre_proceso(p):
            return nombre_de_proceso(p, unidad)

    relacionados = [
        {
            "nombre": nombre_proceso(p),
            "tipo": "Proceso",
            "icono": "fas fa-project-diagram",
            "url": reverse("ficha_proceso_publica", args=[slug, p.pk]),
        }
        for p in procesos
        if any(
            "Equipamiento:" in e.instrucciones
            and elemento.nombre
            in [
                n.strip().rstrip(".")
                for n in e.instrucciones.split("Equipamiento:", 1)[1].split("; ")
            ]
            for e in p.etapas.all()
        )
    ]

    return render(
        request,
        "portal/pages/unidades/aula/equipo.html",
        {
            "unidad": unidad,
            "elemento": elemento,
            "es_referencia": True,
            "codigo_referencia": codigo,
            "detalle": detalle_de_referencia(elemento, codigo, request.user),
            "fichas_relacionadas": relacionados,
            "gestor": False,
            "area": area,
            "volver_url": unidad.get_absolute_url() + "#equipos-infraestructura",
            "area_url": reverse("area_unidad", args=[slug, area.codigo]) + "#equipos",
            "generado_en": timezone.localtime(),
            "editar_url": revisar_ficha(unidad, ficha) + "#elementos-group"
            if gestor
            else "",
        },
    )
