"""Series, gráficas e indicadores del panel de una unidad.

Todo lo que resume el movimiento de inventario, el uso de activos y las finanzas
de la unidad para dibujarlo sin dependencias externas.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_time

from apps.recursos.models.consumibles import EntradaInventario
from apps.core.models.periodos import PeriodoAcademico
from apps.reservas.models.reservas import Reserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad

from apps.reservas.presentation.gestion_agenda import _desplazar_mes


def _nombre_presentacion(consumible):
    """Devuelve un nombre corto y consistente para la unidad comercial."""
    texto = (consumible.presentacion or "").lower()
    nombres = (
        ("bobina", "bobinas"),
        ("rollo", "rollos"),
        ("botella", "botellas"),
        ("envase", "envases"),
        ("paquete", "paquetes"),
        ("caja", "cajas"),
        ("lamina", "láminas"),
        ("lámina", "láminas"),
        ("plancha", "planchas"),
        ("unidad", "unidades"),
    )
    return next((nombre for palabra, nombre in nombres if palabra in texto), "presentaciones")


def _nombre_presentacion_singular(consumible):
    """Devuelve el nombre comercial singular sin inferirlo desde el plural."""
    texto = (consumible.presentacion or "").lower()
    nombres = (
        ("bobina", "bobina"),
        ("rollo", "rollo"),
        ("botella", "botella"),
        ("envase", "envase"),
        ("paquete", "paquete"),
        ("caja", "caja"),
        ("lamina", "lámina"),
        ("lámina", "lámina"),
        ("plancha", "plancha"),
        ("unidad", "unidad"),
    )
    return next((nombre for palabra, nombre in nombres if palabra in texto), "presentación")


def _presentaciones_equivalentes(movimiento):
    contenido = Decimal(movimiento.consumible.cantidad_por_presentacion or 1)
    if contenido <= 0:
        contenido = Decimal("1")
    return Decimal(movimiento.cantidad or 0) / contenido


def _serie_movimientos_inventario(movimientos, periodos):
    """Agrupa movimientos normalizados a presentaciones comerciales."""
    serie = []
    maximo = Decimal("0")
    for etiqueta, inicio, fin in periodos:
        entradas = Decimal("0")
        salidas = Decimal("0")
        desperdicio = Decimal("0")
        for movimiento in movimientos:
            fecha = timezone.localtime(movimiento.fecha).date()
            if not inicio <= fecha <= fin:
                continue
            cantidad = _presentaciones_equivalentes(movimiento)
            if movimiento.tipo == "ingreso":
                entradas += cantidad
            else:
                salidas += cantidad
                if movimiento.es_desperdicio:
                    desperdicio += cantidad
        maximo = max(maximo, entradas, salidas)
        serie.append(
            {
                "etiqueta": etiqueta,
                "rango": f"{inicio:%d/%m/%Y} – {fin:%d/%m/%Y}",
                "entradas": round(entradas, 2),
                "salidas": round(salidas, 2),
                "desperdicio": round(desperdicio, 2),
            }
        )
    for punto in serie:
        punto["altura_entradas"] = round(
            Decimal(punto["entradas"]) / maximo * 100, 1
        ) if maximo else 0
        punto["altura_salidas"] = round(
            Decimal(punto["salidas"]) / maximo * 100, 1
        ) if maximo else 0
        punto["altura_desperdicio"] = round(
            Decimal(punto["desperdicio"]) / maximo * 100, 1
        ) if maximo else 0
    return serie


def _numero_svg(valor):
    """Serializa coordenadas SVG sin depender de la localización activa."""
    numero = Decimal(str(valor)).quantize(Decimal("0.01"))
    return format(numero, "f")


def _geometria_grafica_series(serie, claves):
    """Prepara coordenadas SVG localización-seguras para varias series positivas."""
    ancho = Decimal("820")
    izquierda = Decimal("52")
    derecha = Decimal("18")
    superior = Decimal("18")
    inferior = Decimal("176")
    alto_util = inferior - superior
    ancho_util = ancho - izquierda - derecha
    maximo = max(
        (
            Decimal(str(valor))
            for punto in serie
            for valor in (punto[clave] for clave in claves)
        ),
        default=Decimal("0"),
    )
    escala = maximo if maximo > 0 else Decimal("1")
    cantidad_puntos = len(serie)
    divisor_x = max(cantidad_puntos - 1, 1)

    puntos_svg = []
    for indice, punto in enumerate(serie):
        x = (
            izquierda + (ancho_util / 2)
            if cantidad_puntos == 1
            else izquierda + (ancho_util * Decimal(indice) / Decimal(divisor_x))
        )

        def coordenada_y(valor):
            cantidad = Decimal(str(valor))
            return inferior - (cantidad / escala * alto_util)

        punto_svg = {**punto, "x_svg": _numero_svg(x)}
        for clave in claves:
            punto_svg[f"y_{clave}_svg"] = _numero_svg(coordenada_y(punto[clave]))
        puntos_svg.append(punto_svg)

    divisiones = Decimal("4")
    rejilla = []
    for indice in range(5):
        fraccion = Decimal(indice) / divisiones
        rejilla.append(
            {
                "y_svg": _numero_svg(superior + alto_util * fraccion),
                "valor": round(maximo * (Decimal("1") - fraccion), 2),
            }
        )

    def linea(clave):
        return " ".join(
            f'{punto["x_svg"]},{punto[f"y_{clave}_svg"]}' for punto in puntos_svg
        )

    return {
        "puntos": puntos_svg,
        "rejilla": rejilla,
        "lineas": {clave: linea(clave) for clave in claves},
        "tiene_datos": maximo > 0,
        "maximo": round(maximo, 2),
    }


def _geometria_grafica_inventario(serie):
    """Conserva nombres explícitos para las tres líneas del kardex."""
    grafica = _geometria_grafica_series(
        serie,
        ("entradas", "salidas", "desperdicio"),
    )
    grafica.update(
        {
            "linea_entradas": grafica["lineas"]["entradas"],
            "linea_salidas": grafica["lineas"]["salidas"],
            "linea_desperdicio": grafica["lineas"]["desperdicio"],
        }
    )
    return grafica


def _analitica_inventario(unidad, consumibles, hoy):
    """Calcula tendencias, clasificación ABC y existencias físicas legibles."""
    desde_anual = hoy - timedelta(days=364)
    movimientos = list(
        EntradaInventario.objects.filter(
            Q(unidad=unidad) | Q(consumible__unidad=unidad),
            fecha__date__gte=desde_anual,
        )
        .select_related("consumible")
        .distinct()
        .order_by("fecha", "pk")
    )

    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    semanas = []
    for retroceso in range(7, -1, -1):
        inicio = inicio_semana_actual - timedelta(days=retroceso * 7)
        semanas.append((f"{inicio:%d %b}", inicio, min(inicio + timedelta(days=6), hoy)))

    meses = []
    for retroceso in range(5, -1, -1):
        inicio = _desplazar_mes(date(hoy.year, hoy.month, 1), -retroceso)
        fin = min(_desplazar_mes(inicio, 1) - timedelta(days=1), hoy)
        meses.append((inicio.strftime("%b %Y"), inicio, fin))

    version = None
    for periodo in PeriodoAcademico.objects.prefetch_related("versiones").all():
        candidata = periodo.version_vigente
        if candidata and candidata.fecha_inicio_clases <= hoy <= candidata.fecha_fin_periodo:
            version = candidata
            break
    inicio_periodo = version.fecha_inicio_clases if version else date(hoy.year, 1, 1)
    periodos_academicos = []
    cursor = inicio_periodo - timedelta(days=inicio_periodo.weekday())
    numero = 1
    while cursor <= hoy:
        fin = min(cursor + timedelta(days=6), hoy)
        periodos_academicos.append((f"S{numero}", max(cursor, inicio_periodo), fin))
        cursor += timedelta(days=7)
        numero += 1
    periodos_academicos = periodos_academicos[-12:]

    valores = defaultdict(Decimal)
    cantidades = defaultdict(Decimal)
    mensuales_por_consumible = defaultdict(lambda: defaultdict(Decimal))
    for movimiento in movimientos:
        if movimiento.tipo != "salida":
            continue
        costo = movimiento.costo_unitario
        if costo is None:
            costo = movimiento.consumible.precio_unitario or Decimal("0")
        valores[movimiento.consumible_id] += Decimal(movimiento.cantidad) * Decimal(costo)
        cantidades[movimiento.consumible_id] += Decimal(movimiento.cantidad)
        fecha = timezone.localtime(movimiento.fecha).date()
        mensuales_por_consumible[movimiento.consumible_id][(fecha.year, fecha.month)] += (
            _presentaciones_equivalentes(movimiento)
        )

    orden_abc = sorted(consumibles, key=lambda item: valores[item.pk], reverse=True)
    valor_total = sum((valores[item.pk] for item in orden_abc), Decimal("0"))
    acumulado = Decimal("0")
    resumen_abc = {"A": 0, "B": 0, "C": 0}
    for consumible in orden_abc:
        valor = valores[consumible.pk]
        previo = acumulado / valor_total * 100 if valor_total else Decimal("100")
        clase = "A" if previo < 80 and valor > 0 else ("B" if previo < 95 and valor > 0 else "C")
        acumulado += valor
        consumible.clase_abc = clase
        consumible.valor_consumo_anual = valor
        consumible.cantidad_consumo_anual = cantidades[consumible.pk]
        consumible.participacion_consumo = round(valor / valor_total * 100, 1) if valor_total else 0
        resumen_abc[clase] += 1

        contenido = Decimal(consumible.cantidad_por_presentacion or 1)
        lotes = list(consumible.lotes_inventario.all())
        lotes_bodega = [
            lote for lote in lotes
            if lote.estado == "bodega" and Decimal(lote.cantidad_actual or 0) > 0
        ]
        lotes_en_uso = [
            lote for lote in lotes
            if lote.estado == "en_uso" and Decimal(lote.cantidad_actual or 0) > 0
        ]
        cantidad_bodega = sum(
            (Decimal(lote.cantidad_actual) for lote in lotes_bodega), Decimal("0")
        )
        cantidad_en_uso = sum(
            (Decimal(lote.cantidad_actual) for lote in lotes_en_uso), Decimal("0")
        )
        cantidad_utilizada_en_uso = sum(
            (
                max(
                    Decimal("0"),
                    Decimal(lote.cantidad_inicial or 0) - Decimal(lote.cantidad_actual or 0),
                )
                for lote in lotes_en_uso
            ),
            Decimal("0"),
        )
        unidades_bodega = sum(
            int(Decimal(lote.cantidad_actual or 0) // contenido)
            for lote in lotes_bodega
        )
        cantidad_bodega_empaquetada = contenido * unidades_bodega
        cantidad_bodega_irregular = max(
            Decimal("0"), cantidad_bodega - cantidad_bodega_empaquetada
        )
        consumible.cantidad_bodega = cantidad_bodega
        consumible.cantidad_en_uso = cantidad_en_uso
        consumible.cantidad_utilizada_en_uso = cantidad_utilizada_en_uso
        consumible.unidades_bodega = unidades_bodega
        consumible.unidades_en_uso = len(lotes_en_uso)
        consumible.cantidad_bodega_empaquetada = cantidad_bodega_empaquetada
        consumible.cantidad_bodega_irregular = cantidad_bodega_irregular
        consumible.tiene_saldo_bodega_irregular = cantidad_bodega_irregular > 0
        consumible.cantidad_sin_lote = max(
            Decimal("0"),
            Decimal(consumible.stock_total or 0) - cantidad_bodega - cantidad_en_uso,
        )
        consumible.presentaciones_totales = Decimal(consumible.stock_total or 0) / contenido
        # Las existencias cerradas son unidades físicas enteras. Los decimales
        # solo representan el contenido restante de una presentación abierta.
        consumible.presentaciones_bodega = unidades_bodega
        consumible.presentaciones_en_uso = len(lotes_en_uso)
        consumible.presentaciones_sin_lote = consumible.cantidad_sin_lote / contenido
        consumible.nombre_presentacion = _nombre_presentacion(consumible)
        consumible.nombre_presentacion_singular = _nombre_presentacion_singular(consumible)

        for lote in lotes:
            actual = Decimal(lote.cantidad_actual or 0)
            inicial = Decimal(lote.cantidad_inicial or 0)
            lote.cantidad_utilizada = max(Decimal("0"), inicial - actual)
            lote.unidades_cerradas = (
                int(actual // contenido) if lote.estado == "bodega" else 0
            )
            lote.remanente_bodega = (
                actual % contenido if lote.estado == "bodega" else Decimal("0")
            )
            lote.tiene_remanente_bodega = lote.remanente_bodega > 0
            lote.es_presentacion_abierta = lote.estado == "en_uso"

        mini = []
        max_consumo = max(
            (
                mensuales_por_consumible[consumible.pk].get((inicio.year, inicio.month), Decimal("0"))
                for _, inicio, _ in meses
            ),
            default=Decimal("0"),
        )
        for etiqueta, inicio, _fin in meses:
            valor_mes = mensuales_por_consumible[consumible.pk].get(
                (inicio.year, inicio.month), Decimal("0")
            )
            mini.append(
                {
                    "etiqueta": etiqueta,
                    "valor": round(valor_mes, 2),
                    "altura": round(valor_mes / max_consumo * 100, 1) if max_consumo else 0,
                }
            )
        consumible.serie_consumo_mensual = mini

    total_fichas = max(len(consumibles), 1)
    resumen_abc_lista = [
        {
            "clase": clase,
            "total": resumen_abc[clase],
            "porcentaje": round(resumen_abc[clase] / total_fichas * 100, 1),
        }
        for clase in ("A", "B", "C")
    ]
    serie_semanal = _serie_movimientos_inventario(movimientos, semanas)
    serie_mensual = _serie_movimientos_inventario(movimientos, meses)
    serie_periodo = _serie_movimientos_inventario(movimientos, periodos_academicos)
    return {
        "semanal": serie_semanal,
        "mensual": serie_mensual,
        "periodo": serie_periodo,
        "graficas": {
            "semanal": _geometria_grafica_inventario(serie_semanal),
            "mensual": _geometria_grafica_inventario(serie_mensual),
            "periodo": _geometria_grafica_inventario(serie_periodo),
        },
        "periodo_nombre": version.periodo.nombre if version else f"Año {hoy.year}",
        "abc": resumen_abc_lista,
        "abc_total_valor": valor_total,
        "abc_principales": orden_abc[:5],
        "unidad_grafica": "presentaciones comerciales equivalentes",
    }


def _periodos_semanales(hoy, cantidad=8):
    inicio_actual = hoy - timedelta(days=hoy.weekday())
    return [
        (
            f"{inicio:%d %b}",
            inicio,
            min(inicio + timedelta(days=6), hoy),
        )
        for retroceso in range(cantidad - 1, -1, -1)
        for inicio in (inicio_actual - timedelta(days=retroceso * 7),)
    ]


def _periodos_mensuales(hoy, cantidad=6, desde_inicio_anio=False):
    inicio_mes = date(hoy.year, hoy.month, 1)
    retrocesos = (
        range(inicio_mes.month - 1, -1, -1)
        if desde_inicio_anio
        else range(cantidad - 1, -1, -1)
    )
    return [
        (
            inicio.strftime("%b %Y"),
            inicio,
            min(_desplazar_mes(inicio, 1) - timedelta(days=1), hoy),
        )
        for retroceso in retrocesos
        for inicio in (_desplazar_mes(inicio_mes, -retroceso),)
    ]


def _horas_reserva(reserva):
    ejecucion = reserva.detalle_ejecucion or {}
    horario_real = ejecucion.get("horario_real") or {}
    hora_inicio = parse_time(str(horario_real.get("inicio") or "")) or reserva.hora_inicio
    hora_fin = parse_time(str(horario_real.get("fin") or "")) or reserva.hora_fin
    inicio = datetime.combine(reserva.fecha, hora_inicio)
    fin = datetime.combine(reserva.fecha, hora_fin)
    return max(Decimal("0"), Decimal(str((fin - inicio).total_seconds() / 3600)))


def _recursos_reales(reserva, clave):
    """Distingue una captura real vacía de una reserva antigua sin conciliación."""
    ejecucion = reserva.detalle_ejecucion or {}
    if ejecucion.get("registrada_en") and isinstance(ejecucion.get(clave), list):
        return ejecucion[clave]
    return None


def _serie_uso_activos(reservas, periodos):
    """Cuenta horas-recurso efectivamente atendidas por tipo de activo."""
    serie = []
    codigos_genericos = {"", "MULTI", "SERVICIO", "SOFTWARE", "ESPACIOS", "ESPACIO"}
    for etiqueta, inicio, fin in periodos:
        equipos = Decimal("0")
        espacios = Decimal("0")
        software = Decimal("0")
        for reserva in reservas:
            if not inicio <= reserva.fecha <= fin:
                continue
            horas = _horas_reserva(reserva) or Decimal("1")
            equipos_reales = _recursos_reales(reserva, "equipos")
            espacios_reales = _recursos_reales(reserva, "espacios")
            software_real = _recursos_reales(reserva, "software")
            if equipos_reales is not None:
                cantidad_equipos = len(equipos_reales)
            else:
                unidades = [
                    item
                    for item in reserva.get_unidades_seleccionadas_list()
                    if isinstance(item, dict)
                ]
                cantidad_equipos = len(unidades)
                if not cantidad_equipos and (
                    reserva.solicito_equipo
                    or reserva.tipo_solicitud == "equipo"
                    or (reserva.equipo_codigo or "").upper() not in codigos_genericos
                ):
                    cantidad_equipos = 1
            if espacios_reales is not None:
                cantidad_espacios = len(espacios_reales)
            else:
                cantidad_espacios = len(reserva.espacios_solicitados.all())
                if not cantidad_espacios and (
                    reserva.solicito_espacio
                    or reserva.incluye_espacio
                    or reserva.tipo_solicitud == "espacio"
                ):
                    cantidad_espacios = 1
            if software_real is not None:
                cantidad_software = len(software_real)
            else:
                cantidad_software = len(reserva.software_solicitado.all())
                if not cantidad_software and (
                    reserva.solicito_software or reserva.tipo_solicitud == "software"
                ):
                    cantidad_software = 1
            equipos += horas * cantidad_equipos
            espacios += horas * cantidad_espacios
            software += horas * cantidad_software
        serie.append(
            {
                "etiqueta": etiqueta,
                "rango": f"{inicio:%d/%m/%Y} – {fin:%d/%m/%Y}",
                "equipos": round(equipos, 2),
                "espacios": round(espacios, 2),
                "software": round(software, 2),
            }
        )
    return serie


def _analitica_activos(unidad, reservas, equipos, espacios, software, hoy, *, disponibilidad_actual=None):
    """Resume uso histórico y disponibilidad actual de los recursos técnicos."""
    desde = _desplazar_mes(date(hoy.year, hoy.month, 1), -5)
    reservas_efectivas = list(
        reservas.filter(
            estado="completada",
            fecha__range=(desde, hoy),
        )
        .prefetch_related("espacios_solicitados", "software_solicitado")
    )
    reservas_efectivas = [
        reserva for reserva in reservas_efectivas if reserva.es_efectiva
    ]
    semanal = _serie_uso_activos(reservas_efectivas, _periodos_semanales(hoy))
    mensual = _serie_uso_activos(reservas_efectivas, _periodos_mensuales(hoy))

    equipos_disponibles = sum(
        equipo.activa and equipo.estado_unidad == "disponible" for equipo in equipos
    )
    espacios_reservables = sum(espacio.reservable for espacio in espacios)
    licencias_totales = sum(programa.licencias_totales or 0 for programa in software)
    licencias_disponibles = sum(
        programa.licencias_disponibles or 0 for programa in software
    )

    total_equipos, total_espacios = len(equipos), len(espacios)
    if disponibilidad_actual is not None:
        equipos_disponibles = disponibilidad_actual["equipos"]["disponibles"]
        total_equipos = disponibilidad_actual["equipos"]["total"]
        espacios_reservables = disponibilidad_actual["espacios"]["disponibles"]
        total_espacios = disponibilidad_actual["espacios"]["total"]
        licencias_totales = disponibilidad_actual["software"]["total"]
        licencias_disponibles = disponibilidad_actual["software"]["disponibles"]

    def disponibilidad(nombre, disponible, total, detalle):
        porcentaje = Decimal(disponible) / Decimal(total) * 100 if total else Decimal("0")
        return {
            "nombre": nombre,
            "disponible": disponible,
            "total": total,
            "detalle": detalle,
            "porcentaje": round(porcentaje, 1),
            "porcentaje_css": _numero_svg(min(Decimal("100"), porcentaje)),
        }

    return {
        "graficas": {
            "semanal": _geometria_grafica_series(
                semanal, ("equipos", "espacios", "software")
            ),
            "mensual": _geometria_grafica_series(
                mensual, ("equipos", "espacios", "software")
            ),
        },
        "disponibilidad": [
            disponibilidad(
                "Equipos operativos",
                equipos_disponibles,
                total_equipos,
                "unidades disponibles",
            ),
            disponibilidad(
                "Espacios reservables",
                espacios_reservables,
                total_espacios,
                "espacios habilitados",
            ),
            disponibilidad(
                "Licencias disponibles",
                licencias_disponibles,
                licencias_totales,
                "licencias de software",
            ),
        ],
        "reservas_efectivas": len(reservas_efectivas),
        "unidad_grafica": "horas-recurso efectivamente atendidas",
    }


def _serie_financiera(movimientos, periodos, acumulada=False):
    """Agrupa ingresos y egresos confirmados por intervalo contable."""
    serie = []
    acumulado_ingresos = Decimal("0")
    acumulado_egresos = Decimal("0")
    for etiqueta, inicio, fin in periodos:
        ingresos = sum(
            (
                Decimal(movimiento.monto)
                for movimiento in movimientos
                if movimiento.tipo == "ingreso"
                and inicio <= movimiento.fecha_movimiento <= fin
            ),
            Decimal("0"),
        )
        egresos = sum(
            (
                Decimal(movimiento.monto)
                for movimiento in movimientos
                if movimiento.tipo == "egreso"
                and inicio <= movimiento.fecha_movimiento <= fin
            ),
            Decimal("0"),
        )
        acumulado_ingresos += ingresos
        acumulado_egresos += egresos
        if acumulada:
            ingresos = acumulado_ingresos
            egresos = acumulado_egresos
        serie.append(
            {
                "etiqueta": etiqueta,
                "rango": f"{inicio:%d/%m/%Y} – {fin:%d/%m/%Y}",
                "ingresos": round(ingresos, 2),
                "egresos": round(egresos, 2),
            }
        )
    return serie


def _analitica_financiera(movimientos, fuentes, hoy):
    """Construye flujo mensual/acumulado y comparación gráfica de fuentes."""
    periodos_mensuales = _periodos_mensuales(hoy)
    periodos_anuales = _periodos_mensuales(hoy, desde_inicio_anio=True)
    mensual = _serie_financiera(movimientos, periodos_mensuales)
    acumulada = _serie_financiera(movimientos, periodos_anuales, acumulada=True)
    maximo_fuente = max(
        (
            Decimal(valor)
            for fuente in fuentes
            for valor in (fuente["ingresos"], fuente["egresos"])
        ),
        default=Decimal("0"),
    )
    for fuente in fuentes:
        fuente["porcentaje_ingresos_css"] = _numero_svg(
            Decimal(fuente["ingresos"]) / maximo_fuente * 100
            if maximo_fuente
            else 0
        )
        fuente["porcentaje_egresos_css"] = _numero_svg(
            Decimal(fuente["egresos"]) / maximo_fuente * 100
            if maximo_fuente
            else 0
        )
    return {
        "graficas": {
            "mensual": _geometria_grafica_series(mensual, ("ingresos", "egresos")),
            "acumulada": _geometria_grafica_series(
                acumulada, ("ingresos", "egresos")
            ),
        },
        "unidad_grafica": "dólares registrados y confirmados",
    }


def _ranking_indicador(valores, limite=5):
    items = sorted(
        (
            {"nombre": nombre, "total": round(total, 2)}
            for nombre, total in valores.items()
            if nombre and total
        ),
        key=lambda item: (-item["total"], item["nombre"]),
    )[:limite]
    maximo = max((item["total"] for item in items), default=0)
    for item in items:
        item["porcentaje"] = round(item["total"] / maximo * 100, 1) if maximo else 0
    return items


def _preparar_trazabilidad_lotes(unidad, consumibles):
    lotes = [lote for consumible in consumibles for lote in consumible.lotes_inventario.all()]
    auditorias = defaultdict(list)
    if lotes:
        for registro in (
            RegistroAuditoriaUnidad.objects.filter(
                unidad=unidad,
                entidad="recursos.LoteConsumible",
                objeto_id__in=[str(lote.pk) for lote in lotes],
            )
            .select_related("usuario")
            .order_by("creado_en", "pk")
        ):
            auditorias[registro.objeto_id].append(registro)

    for lote in lotes:
        movimientos = list(lote.movimientos.all())
        salidas = [movimiento for movimiento in movimientos if movimiento.tipo == "salida"]
        tuvo_asignacion = lote.estado == "en_uso" or any(
            movimiento.equipo_id for movimiento in movimientos
        )
        cerrado = lote.estado in {"agotado", "caducado", "extraviado", "retirado"}
        lote.etapas_trazabilidad = [
            {"nombre": "Recibido", "activo": True, "icono": "truck-loading"},
            {
                "nombre": "Almacenado",
                "activo": bool(lote.bodega or lote.estanteria or lote.posicion),
                "icono": "warehouse",
            },
            {"nombre": "Asignado", "activo": tuvo_asignacion, "icono": "tools"},
            {"nombre": "Consumido", "activo": bool(salidas), "icono": "weight"},
            {"nombre": "Cerrado", "activo": cerrado, "icono": "flag-checkered"},
        ]
        eventos = []
        for movimiento in movimientos:
            eventos.append(
                {
                    "fecha": movimiento.fecha,
                    "titulo": movimiento.get_motivo_display(),
                    "detalle": (
                        f"{movimiento.get_tipo_display()} {movimiento.cantidad} "
                        f"{lote.consumible.unidad_medida or 'unidades'}"
                    ),
                    "usuario": (
                        movimiento.usuario.get_full_name()
                        or movimiento.usuario.username
                        if movimiento.usuario_id
                        else "Sistema"
                    ),
                    "tono": "salida" if movimiento.tipo == "salida" else "ingreso",
                }
            )
        for registro in auditorias[str(lote.pk)]:
            eventos.append(
                {
                    "fecha": registro.creado_en,
                    "titulo": registro.descripcion,
                    "detalle": registro.get_accion_display(),
                    "usuario": (
                        registro.usuario.get_full_name()
                        or registro.usuario.username
                        if registro.usuario_id
                        else "Sistema"
                    ),
                    "tono": "auditoria",
                }
            )
        lote.eventos_trazabilidad = sorted(
            eventos, key=lambda evento: evento["fecha"], reverse=True
        )
    return lotes


def _distribuciones_reservas(reservas):
    estados_totales = {
        item["estado"]: item["total"]
        for item in reservas.values("estado").annotate(total=Count("pk"))
    }
    colores_estado = {
        "pendiente": "#d4a72c",
        "confirmada": "#2f7854",
        "en_proceso": "#3f79a8",
        "completada": "#5c8f95",
        "rechazada": "#ad5148",
        "cancelada": "#ad5148",
        "no_presentado": "#7b8580",
        "no_atendida": "#ad5148",
        "vencida": "#8c6f2d",
    }
    total_estados = sum(estados_totales.values())
    por_estado = [
        {
            "codigo": codigo,
            "nombre": nombre,
            "total": estados_totales.get(codigo, 0),
            "color": colores_estado[codigo],
            "porcentaje": round(
                estados_totales.get(codigo, 0) / total_estados * 100,
                1,
            ) if total_estados else 0,
        }
        for codigo, nombre in Reserva.ESTADO_CHOICES
        if estados_totales.get(codigo, 0)
    ]
    propositos_totales = {
        item["proposito_codigo"]: item["total"]
        for item in reservas.exclude(proposito_codigo="")
        .values("proposito_codigo")
        .annotate(total=Count("pk"))
    }
    nombres_proposito = dict(Reserva.PROPOSITO_INSTITUCIONAL_CHOICES)
    por_proposito = sorted(
        (
            {
                "codigo": codigo,
                "nombre": nombres_proposito.get(
                    codigo,
                    codigo.replace("_", " ").title(),
                ),
                "total": total,
            }
            for codigo, total in propositos_totales.items()
        ),
        key=lambda item: (-item["total"], item["nombre"]),
    )
    return por_estado, por_proposito
