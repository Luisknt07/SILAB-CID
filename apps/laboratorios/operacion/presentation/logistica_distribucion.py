"""Práctica guiada y comparación privada del centro de distribución.

Las vistas públicas sólo construyen datos sintéticos. Comparar consulta como
máximo tres resultados terminados, sin cargar estados, eventos ni inventarios.
"""

import csv
import io
import json
from math import isfinite
from uuid import UUID

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.formacion.models.partidas_simulador import PartidaSimulador

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.laboratorios.operacion.presentation.logistica_distribucion_guia import guia
from apps.formacion.presentation.logistica_partidas import ErrorPartida, _base_contexto, unidad_disponible

FAMILIA = "centro-distribucion"
TABLAS = ("productos", "ubicaciones", "pedidos", "recursos")


def _semilla(request):
    try:
        valor = int(request.GET.get("semilla", "42"))
    except (ValueError, TypeError):
        return 42
    return valor if 0 <= valor <= 2147483647 else 42


def _celda(valor):
    if isinstance(valor, (dict, list)):
        valor = json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
    if valor is None:
        return ""
    if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + valor
    return valor


def _csv(nombre, columnas, filas):
    archivo = io.StringIO(newline="")
    escritor = csv.writer(archivo)
    escritor.writerow(columnas)
    escritor.writerows([_celda(celda) for celda in fila] for fila in filas)
    respuesta = HttpResponse(
        "\ufeff" + archivo.getvalue(), content_type="text/csv; charset=utf-8"
    )
    respuesta["Content-Disposition"] = 'attachment; filename="' + nombre + '"'
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


def _dataset(caso, semilla, tabla):
    # Sólo entradas visibles al inicio; no revelar hallazgos de inspección.
    datos = motor.observacion(motor.crear_estado(caso, semilla))["datos"]
    filas = datos[tabla]
    columnas = list(dict.fromkeys(clave for fila in filas for clave in fila))
    return _csv(
        f"{caso}-{semilla}-{tabla}-v{motor.DATASET_VERSION}.csv",
        ["caso", "semilla", "version_dataset", *columnas],
        [
            [
                caso,
                semilla,
                motor.DATASET_VERSION,
                *[fila.get(clave) for clave in columnas],
            ]
            for fila in filas
        ],
    )


@xframe_options_sameorigin
@require_GET
def distribucion_view(request, slug):
    unidad = unidad_disponible(slug)
    caso = request.GET.get("caso", "cd-normal")
    if caso not in motor.CASOS:
        caso = "cd-normal"
    semilla = _semilla(request)
    tabla = request.GET.get("dataset")
    if tabla:
        if tabla not in TABLAS:
            respuesta = JsonResponse({"error": "Dataset no disponible."}, status=400)
            respuesta["Cache-Control"] = "private, no-store"
            return respuesta
        return _dataset(caso, semilla, tabla)
    base = reverse("logistica_distribucion", args=[slug])
    contexto = _base_contexto(unidad, request)
    contexto.update(
        operacion_url=reverse("logistica_operacion", args=[slug])
        + "?caso="
        + caso
        + "&semilla="
        + str(semilla),
        guia=guia(caso),
        caso=caso,
        semilla=semilla,
        version_dataset=motor.DATASET_VERSION,
        catalogo=[
            {**fila, "url": base + "?caso=" + fila["id"] + "&semilla=" + str(semilla)}
            for fila in motor.catalogo()
        ],
        simulador_url=reverse("logistica_operaciones", args=[slug])
        + "?caso="
        + caso
        + "&semilla="
        + str(semilla),
        api_url=reverse("logistica_api_operaciones", args=[slug]),
        datasets=[
            {
                "id": nombre,
                "url": base
                + "?caso="
                + caso
                + "&semilla="
                + str(semilla)
                + "&dataset="
                + nombre,
            }
            for nombre in TABLAS
        ],
    )
    respuesta = render(
        request, "portal/pages/unidades/logistica/distribucion.html", contexto
    )
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


def _identificadores(valor):
    partes = valor.split(",")
    if not 2 <= len(partes) <= 3:
        raise ErrorPartida("Selecciona dos o tres prácticas terminadas.")
    try:
        ids = [UUID(p) for p in partes]
    except (ValueError, TypeError, AttributeError):
        raise ErrorPartida("Identificadores de práctica inválidos.") from None
    if len(set(ids)) != len(ids):
        raise ErrorPartida("Selecciona prácticas diferentes.")
    return ids


def _numero(valor):
    return type(valor) in (int, float) and abs(valor) <= 10**15 and isfinite(valor)


def comparar_partidas(request, unidad):
    ids = _identificadores(request.GET["comparar"])
    filas = list(
        PartidaSimulador.objects.filter(
            unidad=unidad, simulador="operaciones", caso__in=motor.CASOS, pk__in=ids
        )
        .filter(Q(propietario=request.user) | Q(participantes__usuario=request.user))
        .distinct()
        .values(
            "id",
            "nombre",
            "caso",
            "semilla",
            "fase",
            "revision",
            "version_motor",
            "version_caso",
            "resultado",
        )
    )
    if len(filas) != len(ids):
        raise ErrorPartida("Práctica no disponible.", 404)
    mapa = {fila["id"]: fila for fila in filas}
    filas = [mapa[identificador] for identificador in ids]
    if any(fila["fase"] != "terminada" for fila in filas):
        raise ErrorPartida("Termina las prácticas antes de compararlas.", 409)
    if len({fila["semilla"] for fila in filas}) != 1:
        raise ErrorPartida(
            "Usa la misma semilla para comparar estrategias o contingencias.", 409
        )
    for fila in filas:
        resultado_guardado = fila["resultado"]
        if not isinstance(resultado_guardado, dict):
            raise ErrorPartida(
                "Este resultado histórico no tiene un formato comparable; conserva su evidencia original.",
                409,
            )
        if (
            resultado_guardado.get("familia") != FAMILIA
            or resultado_guardado.get("caso") != fila["caso"]
            or resultado_guardado.get("semilla") != fila["semilla"]
            or not _numero(resultado_guardado.get("puntaje"))
            or not 0 <= resultado_guardado["puntaje"] <= 100
        ):
            raise ErrorPartida(
                "La evidencia y su metadata necesitan el mismo caso, semilla y familia, con puntaje válido.",
                409,
            )
        version_dataset = resultado_guardado.get("version_dataset")
        if (
            not isinstance(version_dataset, str)
            or not version_dataset
            or len(version_dataset) > 32
        ):
            raise ErrorPartida(
                "El resultado histórico no declara una versión de dataset comparable.",
                409,
            )
        if (
            resultado_guardado.get("version_motor"),
            resultado_guardado.get("version_caso"),
        ) != (fila["version_motor"], fila["version_caso"]):
            raise ErrorPartida(
                "La metadata y el resultado conservan versiones diferentes; revisa su evidencia original.",
                409,
            )
        kpis = resultado_guardado.get("kpis")
        if not isinstance(kpis, list) or not 1 <= len(kpis) <= 20:
            raise ErrorPartida(
                "El resultado histórico no contiene indicadores comparables.", 409
            )
        ids_kpi = set()
        for kpi in kpis:
            if not isinstance(kpi, dict):
                raise ErrorPartida(
                    "Los indicadores históricos conservan un formato no comparable.",
                    409,
                )
            identificador = kpi.get("id")
            if (
                not isinstance(identificador, str)
                or not identificador
                or identificador in ids_kpi
            ):
                raise ErrorPartida(
                    "Los indicadores históricos necesitan identificadores únicos.", 409
                )
            ids_kpi.add(identificador)
            if (
                not isinstance(kpi.get("unidad", ""), str)
                or not isinstance(kpi.get("titulo", ""), str)
                or not _numero(kpi.get("valor"))
            ):
                raise ErrorPartida(
                    "Los indicadores históricos necesitan unidades y valores numéricos finitos.",
                    409,
                )
    versiones = {
        (f["version_motor"], f["version_caso"], f["resultado"]["version_dataset"])
        for f in filas
    }
    if len(versiones) != 1 or not next(iter(versiones))[2]:
        raise ErrorPartida(
            "Las prácticas necesitan las mismas versiones de motor, caso y dataset.",
            409,
        )
    estrategia = len({fila["caso"] for fila in filas}) == 1
    sesiones = [
        {
            "id": str(f["id"]),
            "nombre": f["nombre"],
            "caso": f["caso"],
            "titulo": motor.CASOS[f["caso"]]["titulo"],
            "semilla": f["semilla"],
            "revision": f["revision"],
            "version_motor": f["version_motor"],
            "version_caso": f["version_caso"],
            "version_dataset": f["resultado"]["version_dataset"],
            "puntaje": f["resultado"].get("puntaje"),
        }
        for f in filas
    ]
    mapas = [
        {
            k["id"]: k
            for k in f["resultado"].get("kpis", [])
            if isinstance(k, dict) and "id" in k
        }
        for f in filas
    ]
    metricas = []
    for identificador, kpi in mapas[0].items():
        if not all(identificador in m for m in mapas):
            continue
        valores = [m[identificador].get("valor") for m in mapas]
        unidades = {m[identificador].get("unidad", "") for m in mapas}
        if len(unidades) != 1 or not all(_numero(v) for v in valores):
            continue
        metricas.append(
            {
                "id": identificador,
                "titulo": kpi.get("titulo", identificador),
                "unidad": kpi.get("unidad", ""),
                "valores": valores,
                "deltas": [round(v - valores[0], 6) for v in valores],
            }
        )
    if not metricas:
        raise ErrorPartida(
            "No hay indicadores comunes con la misma unidad para comparar.", 409
        )
    advertencias = [
        "Datos sintéticos y tiempos de un modelo educativo; los resultados no acreditan uso físico ni un servicio real.",
        "El puntaje didáctico no sustituye la rúbrica ni la evaluación docente.",
        "Las diferencias se calculan respecto a la primera práctica seleccionada; interpreta cada unidad y su denominador.",
    ]
    if not estrategia:
        advertencias.append(
            "Cambian las condiciones del escenario: no atribuyas toda diferencia a la estrategia. Pico cambia demanda y falla restringe un recurso; compara también cada variante con su propia línea base."
        )
    resultado = {
        "schema": "upec.distribucion.comparacion.1",
        "familia": FAMILIA,
        "tipo": "estrategias" if estrategia else "contingencias",
        "sesiones": sesiones,
        "metricas": metricas,
        "advertencias": advertencias,
    }
    formato = request.GET.get("formato", "json")
    if formato == "csv":
        columnas = [
            "tipo_comparacion",
            "practica",
            "caso",
            "semilla",
            "version_motor",
            "version_caso",
            "version_dataset",
            "metrica",
            "unidad",
            "valor",
            "diferencia_primera",
        ]
        datos = [
            [
                resultado["tipo"],
                s["id"],
                s["caso"],
                s["semilla"],
                s["version_motor"],
                s["version_caso"],
                s["version_dataset"],
                m["titulo"],
                m["unidad"],
                m["valores"][i],
                m["deltas"][i],
            ]
            for i, s in enumerate(sesiones)
            for m in metricas
        ]
        return _csv("comparacion-centro-distribucion.csv", columnas, datos)
    if formato != "json":
        raise ErrorPartida("Formato de comparación inválido.")
    return JsonResponse(resultado)
