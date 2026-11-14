"""Cálculo institucional de valores estimados para solicitudes y reservas."""

from datetime import datetime
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.usuarios.pertenencia import pertenencia_actual


CENTAVOS = Decimal("0.01")


def _dinero(valor):
    return Decimal(valor or 0).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _cantidad_texto(valor):
    """Serializa cantidades sin ceros decimales artificiales."""
    if valor is None:
        return None
    decimal = Decimal(valor)
    texto = format(decimal.normalize(), "f")
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


def normalizar_cantidades_servicio(valor):
    """``{"id": cantidad}`` indicado por la persona → ``{int: Decimal}``.

    Acepta un dict ya decodificado o su JSON. Las entradas vacías se ignoran;
    una cantidad no numérica o negativa es un error.
    """
    if not valor:
        return {}
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError):
            raise ValueError("Las cantidades de insumos no son válidas")
    if not isinstance(valor, dict):
        raise ValueError("Las cantidades de insumos no son válidas")
    cantidades = {}
    for clave, cantidad in valor.items():
        if cantidad in (None, ""):
            continue
        try:
            consumible_id = int(clave)
            cantidad = Decimal(str(cantidad))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("Las cantidades de insumos no son válidas")
        if cantidad < 0:
            raise ValueError("Las cantidades de insumos no pueden ser negativas")
        cantidades[consumible_id] = cantidad
    return cantidades


def validar_cantidades_servicio(servicios, cantidades):
    """Solo insumos del catálogo técnico de los servicios y dentro de la existencia."""
    if not cantidades:
        return
    catalogo = {}
    for servicio in servicios:
        for relacion in servicio.service_consumibles.all():
            catalogo[relacion.consumible_id] = relacion.consumible
    for consumible_id, cantidad in cantidades.items():
        consumible = catalogo.get(consumible_id)
        if consumible is None:
            raise ValueError("Uno de los insumos indicados no pertenece a los servicios elegidos")
        if cantidad > Decimal(consumible.stock_total or 0):
            raise ValueError(
                f"La cantidad de {consumible.nombre} supera la existencia disponible "
                f"({_cantidad_texto(Decimal(consumible.stock_total or 0))} "
                f"{consumible.unidad_medida or 'unidades'})"
            )


POLITICA_COBRO_PREDETERMINADA = {
    "tarifa_base": False,
    "uso_equipo": False,
    "mano_obra": False,
    "diseno": False,
    "materiales": True,
}
POLITICA_APORTE_UPEC = (
    "La UPEC asume el 100 % de espacios, mobiliario, equipos, software y personal, "
    "incluidos diseño y guías. El usuario paga únicamente los materiales consumidos."
)
NOMBRES_COMPONENTES = {
    "tarifa_base": "Tarifa base del servicio",
    "uso_equipo": "Uso de equipo",
    "mano_obra": "Mano de obra técnica",
    "diseno": "Diseño realizado por el laboratorio",
}


def calcular_iva(configuracion, base):
    """IVA sobre el valor a cargo del usuario; solo cuando la unidad lo activa."""
    aplica = bool(getattr(configuracion, "aplicar_iva", False))
    porcentaje = Decimal(getattr(configuracion, "porcentaje_iva", 0) or 0) if aplica else Decimal("0")
    monto = _dinero(Decimal(base or 0) * porcentaje / Decimal("100")) if aplica else Decimal("0")
    return {
        "aplica": aplica,
        "porcentaje": str(_dinero(porcentaje)),
        "monto": str(_dinero(monto)),
    }


def politica_cobro_servicios(configuracion=None, modalidad=""):
    """Solo materiales, para todo segmento y modalidad de atención.

    Los parámetros se conservan por compatibilidad con los consumidores. Las
    banderas de cobro antiguas no pueden reactivar cargos institucionales.
    """
    return dict(POLITICA_COBRO_PREDETERMINADA)


def normalizar_piezas(valor):
    """Número de piezas o ejemplares del trabajo: entero entre 1 y 10000."""
    if valor in (None, ""):
        return 1
    try:
        piezas = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ValueError("La cantidad de piezas no es válida")
    if piezas < 1 or piezas > 10000:
        raise ValueError("La cantidad de piezas debe estar entre 1 y 10000")
    return piezas


def normalizar_seleccion_servicio(valor):
    """Ids de insumos elegidos (lista o su JSON) → ``set``; ``None`` si no se envió."""
    if valor is None:
        return None
    if isinstance(valor, str):
        if not valor.strip():
            return set()
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError):
            raise ValueError("La selección de insumos no es válida")
    if not isinstance(valor, (list, tuple, set)):
        raise ValueError("La selección de insumos no es válida")
    try:
        return {int(item) for item in valor}
    except (TypeError, ValueError):
        raise ValueError("La selección de insumos no es válida")


def _material_incluido(relacion, seleccion):
    """Sin selección explícita entran todos; con ella, los elegidos y los obligatorios."""
    return seleccion is None or relacion.obligatorio or relacion.consumible_id in seleccion


def consumibles_sugeridos_servicios(servicios, cantidades=None, *, piezas=1, seleccion=None):
    """Consolida los insumos técnicos asociados a uno o varios servicios.

    La cantidad sugerida del catálogo es por pieza y se multiplica por
    ``piezas``. Una cantidad igual a cero significa que el laboratorista debe
    calcularla en la revisión técnica; no se inventa una cantidad para
    completar la solicitud. ``cantidades`` (``{id: Decimal}``) son las
    indicadas por la persona y sustituyen a la sugerida. ``seleccion`` limita
    el resultado a los insumos elegidos más los obligatorios del servicio.
    """
    cantidades = cantidades or {}
    piezas = int(piezas or 1)
    consolidados = {}
    for servicio in servicios:
        for relacion in servicio.service_consumibles.all():
            if not _material_incluido(relacion, seleccion):
                continue
            registro = consolidados.setdefault(
                relacion.consumible_id,
                {
                    "consumible": relacion.consumible,
                    "cantidad": Decimal("0"),
                    "servicios": [],
                },
            )
            registro["cantidad"] += Decimal(relacion.cantidad_sugerida or 0) * piezas
            registro["servicios"].append(servicio.nombre)
    for consumible_id, cantidad in cantidades.items():
        if consumible_id in consolidados:
            consolidados[consumible_id]["cantidad"] = cantidad
    return [
        (
            registro["consumible"],
            registro["cantidad"] if registro["cantidad"] > 0 else None,
            "estimacion" if registro["cantidad"] > 0 else "revision",
        )
        for registro in consolidados.values()
    ]


def clasificar_usuario(usuario):
    """Las solicitudes nuevas requieren pertenencia aprobada y vigente."""
    segmento, display, _fundamento = clasificacion_tarifaria_actual(usuario)
    return segmento, display


def _display_segmento(segmento):
    return {
        'estudiante': _('Estudiante de la institución'),
        'personal': _('Personal de la institución'),
        'externo': _('Usuario externo'),
    }[segmento]


def _segmento_por_tipo(tipo):
    if tipo == 'estudiante':
        return 'estudiante'
    if tipo in {'docente', 'investigador', 'administrativo', 'egresado'}:
        return 'personal'
    return 'externo'


def clasificacion_tarifaria_actual(usuario):
    fundamento = pertenencia_actual(usuario)
    segmento = (
        _segmento_por_tipo(fundamento['tipo_usuario'])
        if fundamento['aprobada'] else 'externo'
    )
    fundamento.update(segmento=segmento, evaluada_en=timezone.now().isoformat())
    return segmento, _display_segmento(segmento), fundamento


def aviso_pertenencia_tarifaria(pertenencia):
    if pertenencia.get('version') == 1 and not pertenencia.get('aprobada'):
        return _(
            'La pertenencia institucional no tiene una aprobación vigente. '
            'Solicita la revisión de tu perfil para acreditar tu pertenencia. '
            'La UPEC asume los recursos y el personal; solo se cobran materiales.'
        )
    return ''


def _clasificacion_historica(reserva):
    """Conserva el segmento emitido, incluso después de cambiar el perfil.

    Para operaciones antiguas sin desglose se usa el tipo guardado en la
    reserva. Sin ninguno de los dos datos no se infiere del perfil actual.
    """
    desglose = reserva.desglose_cotizacion or {}
    segmento = desglose.get('segmento')
    if segmento not in {'estudiante', 'personal', 'externo'}:
        segmento = _segmento_por_tipo(reserva.tipo_usuario_solicitante)
    fundamento = desglose.get('pertenencia_tarifaria')
    if not isinstance(fundamento, dict):
        fundamento = {
            'version': 0, 'estado': 'historica_sin_revision',
            'segmento': segmento, 'reserva_id': reserva.pk,
        }
    return segmento, _display_segmento(segmento), dict(fundamento)


def clasificar_reserva(reserva):
    """Usa el segmento emitido y luego el tipo histórico, nunca el perfil actual."""
    segmento, display, _fundamento = _clasificacion_historica(reserva)
    return segmento, display


def calcular_cotizacion(
    servicios,
    modalidad,
    usuario,
    cantidades=None,
    *,
    configuracion=None,
    piezas=1,
    seleccion=None,
    urgencia="normal",
    reserva_fuente=None,
    materiales_confirmados=None,
):
    """Calcula un valor informativo y devuelve un desglose serializable.

    Cada servicio se descompone en tarifa base, uso de equipo, mano de obra y
    diseño, asumidos por la Universidad en todas las modalidades. Los
    materiales se cobran siempre. Las horas y las cantidades sugeridas del
    catálogo son por pieza y se multiplican por ``piezas``. ``cantidades``
    (``{id: Decimal}``) sustituye la cantidad sugerida por la indicada por la
    persona; se aplica al primer servicio que usa el insumo para no contarla
    dos veces. ``seleccion`` limita los materiales a los elegidos más los
    obligatorios. Al corregir una reserva, ``materiales_confirmados`` sustituye
    las sugerencias por los insumos y cantidades validados en el expediente.
    """
    cantidades = dict(cantidades or {})
    piezas = int(piezas or 1)
    politica = politica_cobro_servicios(configuracion, modalidad)
    segmento, segmento_display, pertenencia = (
        _clasificacion_historica(reserva_fuente)
        if reserva_fuente is not None else clasificacion_tarifaria_actual(usuario)
    )
    conceptos = []
    subtotal_general = Decimal("0")
    aporte_general = Decimal("0")
    descuentos_general = Decimal("0")
    no_cobrado_general = Decimal("0")
    horas_equipo_total = Decimal("0")
    horas_mano_obra_total = Decimal("0")

    materiales_planificados = {}
    total_materiales = Decimal("0")
    aplicadas = set()
    nombres_modalidad = {
        "diseno_asistido": "Diseño con asesoría en la unidad",
        "diseno_completo": "Diseño completo del laboratorio",
    }

    for servicio in servicios:
        detalle_materiales = []
        materiales = Decimal("0")
        relaciones = servicio.service_consumibles.all() if materiales_confirmados is None else ()
        for relacion in relaciones:
            if not _material_incluido(relacion, seleccion):
                continue
            consumible = relacion.consumible
            cantidad = Decimal(relacion.cantidad_sugerida or 0) * piezas
            if consumible.pk in cantidades:
                cantidad = cantidades.pop(consumible.pk)
            elif consumible.pk in aplicadas:
                cantidad = Decimal("0")
            precio = Decimal(consumible.precio_unitario or 0)
            subtotal_material = cantidad * precio
            materiales += subtotal_material
            detalle_materiales.append({
                "id": consumible.pk,
                "nombre": consumible.nombre,
                "cantidad": _cantidad_texto(cantidad) if cantidad > 0 else None,
                "unidad": consumible.unidad_medida or "unidades",
                "precio_unitario": str(_dinero(precio)),
                "subtotal": str(_dinero(subtotal_material)),
                "por_calcular": cantidad <= 0,
                "obligatorio": bool(relacion.obligatorio),
            })
            acumulado = materiales_planificados.setdefault(
                consumible.pk,
                {
                    "id": consumible.pk,
                    "nombre": consumible.nombre,
                    "variante": " · ".join(filter(None, [consumible.variante, consumible.color])),
                    "cantidad_decimal": Decimal("0"),
                    "unidad": consumible.unidad_medida or "unidades",
                    "precio_unitario": precio,
                    "stock": _cantidad_texto(Decimal(consumible.stock_total or 0)),
                    "servicios": [],
                    "por_calcular": False,
                    "obligatorio": bool(relacion.obligatorio),
                },
            )
            acumulado["obligatorio"] = acumulado["obligatorio"] or bool(relacion.obligatorio)
            if consumible.pk in aplicadas:
                acumulado["servicios"].append(servicio.nombre)
                continue
            aplicadas.add(consumible.pk)
            acumulado["cantidad_decimal"] += cantidad
            acumulado["servicios"].append(servicio.nombre)
            acumulado["por_calcular"] = acumulado["por_calcular"] or cantidad <= 0
        total_materiales += materiales
        horas_equipo = Decimal(servicio.horas_equipo_estimadas or 0) * piezas
        horas_mano_obra = Decimal(servicio.horas_mano_obra_estimadas or 0) * piezas
        horas_equipo_total += horas_equipo
        horas_mano_obra_total += horas_mano_obra
        equipo = horas_equipo * Decimal(servicio.costo_hora_equipo or 0)
        mano_obra = horas_mano_obra * Decimal(servicio.costo_hora_mano_obra or 0)
        diseno = Decimal("0")
        if modalidad == "diseno_asistido":
            diseno = Decimal(servicio.costo_diseno_asistido or 0)
        elif modalidad == "diseno_completo":
            diseno = Decimal(servicio.costo_diseno_completo or 0)

        porcentaje = Decimal(
            getattr(servicio, f"descuento_{segmento}", 0) or 0
        )
        componentes = []
        cobrado = Decimal("0")
        no_cobrado = Decimal("0")
        descuento = Decimal("0")
        for clave, valor, cantidad, precio_unitario in (
            ("tarifa_base", Decimal(servicio.tarifa_base or 0), "1 solicitud", "Por solicitud"),
            (
                "uso_equipo",
                equipo,
                f"{_cantidad_texto(horas_equipo)} h",
                f"${_dinero(servicio.costo_hora_equipo)} por hora",
            ),
            (
                "mano_obra",
                mano_obra,
                f"{_cantidad_texto(horas_mano_obra)} h",
                f"${_dinero(servicio.costo_hora_mano_obra)} por hora",
            ),
            (
                "diseno",
                diseno,
                nombres_modalidad.get(modalidad, "No aplica: entregas el modelo listo"),
                "Por trabajo",
            ),
        ):
            se_cobra = bool(politica.get(clave))
            # Lo referencial lo asume la Universidad completo; sobre lo cobrable
            # aplica el descuento del segmento.
            descuento_componente = valor * porcentaje / Decimal("100") if se_cobra else Decimal("0")
            aporte_componente = descuento_componente if se_cobra else valor
            if se_cobra:
                cobrado += valor
                descuento += descuento_componente
            else:
                no_cobrado += valor
            componentes.append({
                "clave": clave,
                "nombre": NOMBRES_COMPONENTES[clave],
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "detalle": f"{cantidad} · {precio_unitario}",
                "valor": str(_dinero(valor)),
                "cobrado": se_cobra,
                "descuento": str(_dinero(descuento_componente)),
                "aporte_institucional": str(_dinero(aporte_componente)),
                "valor_usuario": str(_dinero(valor - aporte_componente)),
            })

        subtotal_aportable = cobrado + no_cobrado
        subtotal = subtotal_aportable + materiales
        aporte = no_cobrado + descuento
        subtotal_general += subtotal
        aporte_general += aporte
        descuentos_general += descuento
        no_cobrado_general += no_cobrado
        conceptos.append(
            {
                "servicio_id": servicio.pk,
                "servicio": servicio.nombre,
                "tarifa_base": str(_dinero(servicio.tarifa_base)),
                "uso_equipo": str(_dinero(equipo)),
                "mano_obra": str(_dinero(mano_obra)),
                "insumos": str(_dinero(materiales)),
                "insumos_detalle": detalle_materiales,
                "diseno": str(_dinero(diseno)),
                "componentes": componentes,
                "horas_equipo": _cantidad_texto(horas_equipo),
                "horas_mano_obra": _cantidad_texto(horas_mano_obra),
                "subtotal": str(_dinero(subtotal)),
                "base_aporte_institucional": str(_dinero(subtotal_aportable)),
                "cobrado": str(_dinero(cobrado)),
                "no_cobrado": str(_dinero(no_cobrado)),
                "descuento_porcentaje": str(_dinero(porcentaje)),
                "descuento": str(_dinero(descuento)),
                "aporte_institucional": str(_dinero(aporte)),
                "total": str(_dinero(subtotal - aporte)),
            }
        )

    if materiales_confirmados is not None:
        for consumible, cantidad, metodo in materiales_confirmados:
            cantidad_decimal = Decimal(cantidad or 0)
            precio = Decimal(consumible.precio_unitario or 0)
            total_materiales += cantidad_decimal * precio
            materiales_planificados[consumible.pk] = {
                "id": consumible.pk,
                "nombre": consumible.nombre,
                "variante": " · ".join(filter(None, [consumible.variante, consumible.color])),
                "cantidad_decimal": cantidad_decimal,
                "unidad": consumible.unidad_medida or "unidades",
                "precio_unitario": precio,
                "por_calcular": cantidad is None or metodo == "revision",
                "obligatorio": False,
                "servicios": [],
            }
        subtotal_general += total_materiales
    subtotal_usuario = _dinero(total_materiales)
    iva = calcular_iva(configuracion, subtotal_usuario)
    total = subtotal_usuario + Decimal(iva["monto"])
    porcentaje_efectivo = (
        aporte_general * Decimal("100") / subtotal_general
        if subtotal_general
        else Decimal("0")
    )
    materiales_resumen = []
    for item in materiales_planificados.values():
        cantidad = item.pop("cantidad_decimal")
        precio = item.pop("precio_unitario")
        item["cantidad"] = _cantidad_texto(cantidad) if cantidad > 0 else None
        item["precio_unitario"] = str(_dinero(precio))
        item["subtotal"] = str(_dinero(cantidad * precio))
        item["aporte_institucional"] = "0.00"
        item["valor_usuario"] = str(_dinero(cantidad * precio))
        materiales_resumen.append(item)

    no_cobrados = [
        NOMBRES_COMPONENTES[clave].lower()
        for clave in ("tarifa_base", "uso_equipo", "mano_obra", "diseno")
        if not politica.get(clave)
    ]
    # Un material sin cantidad no entra en el valor: decirlo evita que la
    # estimación parezca completa cuando todavía falta lo principal.
    pendientes = [item["nombre"] for item in materiales_resumen if item["por_calcular"]]
    aviso_estimacion = (
        "Falta la cantidad de "
        + ", ".join(pendientes)
        + ": ese material no está incluido en el valor. Indícala o pide la "
        "estimación previa del laboratorio para conocer el valor completo."
        if pendientes
        else ""
    )
    return {
        "tipo": "servicio",
        "segmento": segmento,
        "segmento_display": segmento_display,
        "pertenencia_tarifaria": pertenencia,
        "aviso_pertenencia": aviso_pertenencia_tarifaria(pertenencia),
        "modalidad": modalidad,
        "piezas": piezas,
        "urgencia": urgencia,
        "horas_equipo_estimadas": _cantidad_texto(horas_equipo_total),
        "horas_mano_obra_estimadas": _cantidad_texto(horas_mano_obra_total),
        "politica_cobro": politica,
        "conceptos": conceptos,
        "materiales_planificados": materiales_resumen,
        "materiales_por_calcular": pendientes,
        "aviso_estimacion": aviso_estimacion,
        "total_insumos": str(_dinero(total_materiales)),
        "subtotal": str(_dinero(subtotal_general)),
        "descuento": str(_dinero(aporte_general)),
        "descuentos_segmento": str(_dinero(descuentos_general)),
        "no_cobrado": str(_dinero(no_cobrado_general)),
        "valor_referencial": str(_dinero(subtotal_general)),
        "aporte_institucional": str(_dinero(aporte_general)),
        "subtotal_usuario": str(_dinero(subtotal_usuario)),
        "iva": iva,
        "valor_estimado_usuario": str(_dinero(total)),
        "descuento_porcentaje": str(_dinero(porcentaje_efectivo)),
        "total": str(_dinero(total)),
        "requiere_aceptacion": any(servicio.requiere_cotizacion for servicio in servicios),
        "moneda": "USD",
        "advertencia": (
            "Valor estimado sujeto a validación del archivo, consumo real, tiempo de "
            "máquina y aprobación del laboratorista. Los materiales se cobran según "
            "el consumo real"
            + (
                f"; {', '.join(no_cobrados)} se muestran como referencia y los asume la Universidad."
                if no_cobrados else "."
            )
        ),
    }


def calcular_costo_referencial_recursos(
    consumibles,
    usuario,
    *,
    configuracion=None,
    recursos=(),
    software=(),
    espacios=(),
    incluye_espacio=False,
    duracion_horas=0,
    sesiones=1,
    reserva_fuente=None,
    acompanamiento_visita=None,
):
    """Valora toda la reserva y separa lo asumido por la Universidad.

    Una programación semanal se valora completa: la cantidad indicada de cada
    insumo es la de una sesión, así que los apoyos por hora y el consumo se
    multiplican por ``sesiones``.
    """
    segmento, segmento_display, pertenencia = (
        _clasificacion_historica(reserva_fuente)
        if reserva_fuente is not None else clasificacion_tarifaria_actual(usuario)
    )
    sesiones = max(1, int(sesiones or 1))
    conceptos = []
    total_insumos = Decimal("0")
    pendientes = 0
    for consumible, cantidad, metodo in consumibles:
        precio = Decimal(consumible.precio_unitario or 0)
        cantidad_total = Decimal(cantidad or 0) * sesiones
        cantidad_sesion = Decimal(cantidad or 0)
        valor = cantidad_total * precio
        total_insumos += valor
        por_calcular = cantidad is None or metodo == "revision"
        pendientes += int(por_calcular)
        conceptos.append({
            "categoria": "insumo",
            "id": consumible.pk,
            "nombre": consumible.nombre,
            "cantidad": _cantidad_texto(cantidad_total) if cantidad is not None else None,
            "cantidad_por_sesion": (
                _cantidad_texto(cantidad_sesion.quantize(Decimal("0.001")))
                if cantidad is not None else None
            ),
            "sesiones": sesiones,
            "unidad": consumible.unidad_medida or "unidades",
            "precio_unitario": str(_dinero(precio)),
            "subtotal": str(_dinero(valor)),
            "aporte_institucional": "0.00",
            "valor_usuario": str(_dinero(valor)),
            "por_calcular": por_calcular,
        })

    horas = max(Decimal(str(duracion_horas or 0)), Decimal("0"))
    recursos = tuple(recursos or ())
    software = tuple(software or ())
    espacios = tuple(espacios or ())
    incluye_espacio = bool(incluye_espacio or espacios)
    cantidades_apoyo = (
        (
            "espacio",
            "Uso de espacios y mobiliario",
            Decimal("1") if incluye_espacio else Decimal("0"),
            Decimal(getattr(configuracion, "tarifa_referencial_hora_espacio", 0) or 0),
        ),
        (
            "equipo",
            "Uso de equipos o instrumentos",
            Decimal(len(recursos)),
            Decimal(getattr(configuracion, "tarifa_referencial_hora_equipo", 0) or 0),
        ),
        (
            "software",
            "Software y licencias institucionales",
            Decimal(len(software)),
            Decimal(getattr(configuracion, "tarifa_referencial_hora_software", 0) or 0),
        ),
        (
            "acompanamiento",
            "Acompañamiento del personal de la unidad",
            Decimal("1") if (incluye_espacio or recursos or software) else Decimal("0"),
            Decimal(
                getattr(
                    configuracion,
                    "tarifa_referencial_hora_acompanamiento",
                    0,
                ) or 0
            ),
        ),
    )
    componentes_apoyo = []
    total_apoyo = Decimal("0")
    tarifas_pendientes = []
    for categoria, nombre, cantidad, tarifa in cantidades_apoyo:
        if cantidad <= 0:
            continue
        es_guia = categoria == "acompanamiento" and acompanamiento_visita is not None
        if es_guia:
            cantidad, tarifa = map(Decimal, acompanamiento_visita)
            nombre = "Acompañamiento de guías de la unidad"
        subtotal_componente = cantidad * (Decimal("1") if es_guia else horas) * sesiones * tarifa
        total_apoyo += subtotal_componente
        configurada = tarifa > 0
        if not configurada:
            tarifas_pendientes.append(nombre)
        componentes_apoyo.append({
            "categoria": categoria,
            "nombre": nombre,
            "cantidad": _cantidad_texto(cantidad),
            "horas": _cantidad_texto(horas * sesiones),
            "horas_por_sesion": _cantidad_texto(horas),
            "sesiones": sesiones,
            "tarifa_hora": str(_dinero(tarifa)) if not es_guia else None,
            "precio_por_guia": str(_dinero(tarifa)) if es_guia else None,
            "subtotal": str(_dinero(subtotal_componente)),
            "tarifa_configurada": configurada,
        })

    # El tipo de usuario acredita identidad y permisos, nunca genera cargos
    # por patrimonio o personal que ya financia la Universidad.
    porcentaje_aporte = Decimal("100")
    aporte_institucional = total_apoyo * porcentaje_aporte / Decimal("100")
    for componente in componentes_apoyo:
        subtotal_componente = Decimal(componente["subtotal"])
        aporte_componente = subtotal_componente * porcentaje_aporte / Decimal("100")
        componente["aporte_institucional"] = str(_dinero(aporte_componente))
        componente["valor_usuario"] = str(
            _dinero(subtotal_componente - aporte_componente)
        )
        conceptos.append(componente)

    valor_referencial = total_insumos + total_apoyo
    subtotal_usuario = _dinero(total_insumos)
    iva = calcular_iva(configuracion, subtotal_usuario)
    total_usuario = subtotal_usuario + Decimal(iva["monto"])
    porcentaje_efectivo = (
        aporte_institucional * Decimal("100") / valor_referencial
        if valor_referencial
        else Decimal("0")
    )
    return {
        "tipo": "recursos",
        "programa": {
            "sesiones": sesiones,
            "horas_por_sesion": _cantidad_texto(horas),
            "horas_totales": _cantidad_texto(horas * sesiones),
            "insumos_por_sesion": str(_dinero(total_insumos / sesiones)),
            "apoyos_por_sesion": str(_dinero(total_apoyo / sesiones)),
            "usuario_por_sesion": str(_dinero(total_usuario / sesiones)),
        },
        "subtotal_usuario": str(_dinero(subtotal_usuario)),
        "iva": iva,
        "segmento": segmento,
        "segmento_display": segmento_display,
        "pertenencia_tarifaria": pertenencia,
        "aviso_pertenencia": aviso_pertenencia_tarifaria(pertenencia),
        "conceptos": conceptos,
        "componentes_apoyo": componentes_apoyo,
        "total_insumos": str(_dinero(total_insumos)),
        "costo_apoyo_institucional": str(_dinero(total_apoyo)),
        "subtotal": str(_dinero(valor_referencial)),
        "descuento": str(_dinero(aporte_institucional)),
        "descuento_porcentaje": str(_dinero(porcentaje_efectivo)),
        "porcentaje_aporte_institucional": str(_dinero(porcentaje_aporte)),
        "politica_aporte": POLITICA_APORTE_UPEC,
        "valor_referencial": str(_dinero(valor_referencial)),
        "aporte_institucional": str(_dinero(aporte_institucional)),
        "valor_estimado_usuario": str(_dinero(total_usuario)),
        "total": str(_dinero(total_usuario)),
        "moneda": "USD",
        "cantidades_pendientes": pendientes,
        "tarifas_pendientes": tarifas_pendientes,
        "duracion_horas": _cantidad_texto(horas),
        "requiere_aceptacion": False,
        "advertencia": (
            "Estimación informativa: la unidad validará cantidades, consumo real, "
            "duración y política aplicable antes de cualquier valor definitivo; "
            "no constituye un cobro."
        ),
        "aportes_no_valorados": tarifas_pendientes,
    }


def recalcular_estimacion_reserva(reserva):
    """Vuelve a valorar una reserva de recursos con lo que consta hoy en ella.

    Se usa cuando el laboratorio aprueba un cambio del titular (cantidades,
    recursos u horario): la sesión recalculada conserva el número de sesiones
    del programa y queda marcada como modificada para la trazabilidad.
    """
    try:
        configuracion = reserva.laboratorio.configuracion_operativa
    except (AttributeError, ObjectDoesNotExist):
        configuracion = None
    consumibles = [
        (
            item.consumible,
            item.cantidad_aprobada if item.cantidad_aprobada is not None else item.cantidad_solicitada,
            item.metodo_estimacion,
        )
        for item in reserva.consumibles_solicitados.select_related("consumible")
    ]
    if reserva.provision_consumibles != "unidad":
        consumibles = []
    programa_previo = (reserva.desglose_cotizacion or {}).get("programa") or {}
    sesiones = int(programa_previo.get("sesiones") or 1)
    if reserva.tipo_solicitud == "servicio":
        cotizacion = calcular_cotizacion(
            list(reserva.servicios_solicitados.all()), reserva.modalidad_servicio, reserva.usuario,
            configuracion=configuracion, piezas=reserva.cantidad_piezas or 1,
            urgencia=reserva.urgencia_servicio, reserva_fuente=reserva,
            materiales_confirmados=consumibles,
        )
        if "trabajo" in (reserva.desglose_cotizacion or {}):
            cotizacion["trabajo"] = reserva.desglose_cotizacion["trabajo"]
    else:
        cotizacion = calcular_costo_referencial_recursos(
            consumibles,
            reserva.usuario,
            configuracion=configuracion,
            recursos=reserva.get_unidades_seleccionadas_list(),
            software=list(reserva.software_solicitado.all()),
            espacios=list(reserva.espacios_solicitados.all()),
            incluye_espacio=reserva.incluye_espacio,
            duracion_horas=reserva.duracion,
            sesiones=1,
            reserva_fuente=reserva,
            acompanamiento_visita=_referencia_guias_visita(reserva),
        )
    cotizacion.setdefault("programa", {}).update({
        "sesiones": sesiones,
        "sesion_modificada": True,
        "nota": (
            "Esta sesión fue modificada y se valoró por separado; el resto del "
            "programa conserva su estimación original."
            if sesiones > 1 else "Estimación actualizada tras el cambio aprobado."
        ),
    })
    reserva.desglose_cotizacion = cotizacion
    reserva.costo_estimado = Decimal(cotizacion["total"])
    reserva.descuento_aplicado = Decimal(cotizacion["descuento_porcentaje"])
    reserva.save(update_fields=["desglose_cotizacion", "costo_estimado", "descuento_aplicado"])
    return cotizacion


def _referencia_guias_visita(reserva):
    visita = getattr(reserva, "visita", None)
    if visita is None:
        return None
    # Mantener la referencia emitida sin trasladar jamás ese valor al visitante.
    for componente in (reserva.desglose_cotizacion or {}).get("componentes_apoyo", []):
        if componente.get("precio_por_guia") is not None:
            return visita.guias_necesarios, Decimal(componente["precio_por_guia"])
    from apps.laboratorios.operacion.models.fablab import FablabService
    from apps.reservas.presentation.visitas import costo_por_guia

    servicio = FablabService.objects.filter(unidad=reserva.laboratorio, tipo_servicio="visita").first()
    return visita.guias_necesarios, costo_por_guia(servicio)


def _diferencia(actual, estimado):
    return _dinero(Decimal(actual or 0) - Decimal(estimado or 0))


def _valor_estimado(desglose, clave, alterna=None):
    valor = desglose.get(clave)
    if valor in (None, "") and alterna:
        valor = desglose.get(alterna)
    try:
        return Decimal(valor or 0)
    except (TypeError, ValueError):
        return Decimal("0")


def calcular_liquidacion_real(reserva, *, inicio, fin, recursos, consumos):
    """Concilia la cotización inicial con lo realmente ejecutado.

    El cálculo no modifica la cotización original. El material útil se valora
    con el costo conservado en cada movimiento de inventario y el desperdicio
    queda separado como pérdida asumida por el laboratorio.
    """
    minutos = Decimal(
        str(
            (
                datetime.combine(reserva.fecha, fin)
                - datetime.combine(reserva.fecha, inicio)
            ).total_seconds()
            / 60
        )
    )
    horas = max(minutos / Decimal("60"), Decimal("0"))
    costo_material_util = sum(
        (Decimal(item.get("costo_consumido") or 0) for item in consumos),
        Decimal("0"),
    )
    costo_desperdicio = sum(
        (Decimal(item.get("costo_desperdicio") or 0) for item in consumos),
        Decimal("0"),
    )
    conceptos = []
    advertencias = []
    costo_apoyo = Decimal("0")
    aporte = Decimal("0")
    segmento, segmento_display = clasificar_reserva(reserva)

    try:
        configuracion = reserva.laboratorio.configuracion_operativa
    except (AttributeError, ObjectDoesNotExist):
        configuracion = None

    if reserva.tipo_solicitud == "servicio":
        from apps.laboratorios.operacion.models.fablab import FablabService

        politica = politica_cobro_servicios(
            configuracion,
            reserva.modalidad_servicio,
        )
        ids_servicios = {
            int(item["id"])
            for item in recursos.get("servicios", [])
            if str(item.get("id") or "").isdigit()
        }
        servicios = list(FablabService.objects.filter(pk__in=ids_servicios))
        for servicio in servicios:
            uso_equipo = horas * Decimal(servicio.costo_hora_equipo or 0)
            mano_obra = horas * Decimal(servicio.costo_hora_mano_obra or 0)
            diseno = Decimal("0")
            if reserva.modalidad_servicio == "diseno_asistido":
                diseno = Decimal(servicio.costo_diseno_asistido or 0)
            elif reserva.modalidad_servicio == "diseno_completo":
                diseno = Decimal(servicio.costo_diseno_completo or 0)
            componentes = (
                ("tarifa_base", Decimal(servicio.tarifa_base or 0)),
                ("uso_equipo", uso_equipo),
                ("mano_obra", mano_obra),
                ("diseno", diseno),
            )
            subtotal = sum((valor for _clave, valor in componentes), Decimal("0"))
            cobrado = sum(
                (valor for clave, valor in componentes if politica.get(clave)),
                Decimal("0"),
            )
            porcentaje = Decimal(
                getattr(servicio, f"descuento_{segmento}", 0) or 0
            )
            porcentaje = min(max(porcentaje, Decimal("0")), Decimal("100"))
            # Lo no cobrable lo asume la Universidad; sobre lo cobrable aplica el descuento.
            aporte_concepto = (subtotal - cobrado) + cobrado * porcentaje / Decimal("100")
            costo_apoyo += subtotal
            aporte += aporte_concepto
            conceptos.append(
                {
                    "categoria": "servicio",
                    "id": servicio.pk,
                    "nombre": servicio.nombre,
                    "horas_reales": _cantidad_texto(horas),
                    "tarifa_base": str(_dinero(servicio.tarifa_base)),
                    "uso_equipo": str(_dinero(uso_equipo)),
                    "mano_obra": str(_dinero(mano_obra)),
                    "diseno": str(_dinero(diseno)),
                    "subtotal": str(_dinero(subtotal)),
                    "cobrado": str(_dinero(cobrado)),
                    "aporte_institucional": str(_dinero(aporte_concepto)),
                    "valor_usuario": str(_dinero(subtotal - aporte_concepto)),
                }
            )
        if ids_servicios and len(servicios) != len(ids_servicios):
            advertencias.append("Uno de los servicios ejecutados ya no está disponible en el catálogo.")
    else:
        cantidades = (
            (
                "espacio",
                "Uso real de espacios y mobiliario",
                Decimal("1") if recursos.get("espacios") else Decimal("0"),
                Decimal(getattr(configuracion, "tarifa_referencial_hora_espacio", 0) or 0),
            ),
            (
                "equipo",
                "Uso real de equipos o instrumentos",
                Decimal(len(recursos.get("equipos", []))),
                Decimal(getattr(configuracion, "tarifa_referencial_hora_equipo", 0) or 0),
            ),
            (
                "software",
                "Uso real de software y licencias",
                Decimal(len(recursos.get("software", []))),
                Decimal(getattr(configuracion, "tarifa_referencial_hora_software", 0) or 0),
            ),
            (
                "acompanamiento",
                "Acompañamiento técnico real",
                Decimal("1")
                if any(recursos.get(clave) for clave in ("espacios", "equipos", "software"))
                else Decimal("0"),
                Decimal(
                    getattr(configuracion, "tarifa_referencial_hora_acompanamiento", 0)
                    or 0
                ),
            ),
        )
        guias_visita = _referencia_guias_visita(reserva)
        for categoria, nombre, cantidad, tarifa in cantidades:
            if cantidad <= 0:
                continue
            es_guia = categoria == "acompanamiento" and guias_visita is not None
            if es_guia:
                cantidad, tarifa = map(Decimal, guias_visita)
                nombre = "Acompañamiento real de guías de la unidad"
            subtotal = cantidad * (Decimal("1") if es_guia else horas) * tarifa
            aporte_concepto = subtotal
            costo_apoyo += subtotal
            aporte += aporte_concepto
            if tarifa <= 0:
                advertencias.append(f"Falta configurar la tarifa de {nombre.lower()}.")
            conceptos.append(
                {
                    "categoria": categoria,
                    "nombre": nombre,
                    "cantidad": _cantidad_texto(cantidad),
                    "horas_reales": _cantidad_texto(horas),
                    "tarifa_hora": str(_dinero(tarifa)) if not es_guia else None,
                    "precio_por_guia": str(_dinero(tarifa)) if es_guia else None,
                    "subtotal": str(_dinero(subtotal)),
                    "aporte_institucional": str(_dinero(aporte_concepto)),
                    "valor_usuario": str(_dinero(subtotal - aporte_concepto)),
                }
            )

    conceptos.append(
        {
            "categoria": "insumo_util",
            "nombre": "Material útil realmente consumido",
            "subtotal": str(_dinero(costo_material_util)),
            "aporte_institucional": "0.00",
            "valor_usuario": str(_dinero(costo_material_util)),
        }
    )
    if costo_desperdicio:
        conceptos.append(
            {
                "categoria": "desperdicio",
                "nombre": "Desperdicio o pérdida del proceso",
                "subtotal": str(_dinero(costo_desperdicio)),
                "aporte_institucional": str(_dinero(costo_desperdicio)),
                "valor_usuario": "0.00",
                "responsable": "laboratorio",
            }
        )

    valor_facturable = costo_apoyo + costo_material_util
    costo_operativo = valor_facturable + costo_desperdicio
    subtotal_usuario = _dinero(costo_material_util)
    iva = calcular_iva(configuracion, subtotal_usuario)
    valor_usuario = subtotal_usuario + Decimal(iva["monto"])
    estimacion = reserva.desglose_cotizacion or {}
    estimado_referencial = _valor_estimado(estimacion, "valor_referencial", "subtotal")
    estimado_aporte = _valor_estimado(estimacion, "aporte_institucional", "descuento")
    estimado_usuario = _valor_estimado(
        estimacion, "valor_estimado_usuario", "total"
    )
    if not estimacion and reserva.costo_estimado is not None:
        estimado_usuario = Decimal(reserva.costo_estimado)

    return {
        "version": 1,
        "tipo": reserva.tipo_solicitud,
        "moneda": "USD",
        "segmento": segmento,
        "segmento_display": segmento_display,
        "duracion_real_horas": _cantidad_texto(horas),
        "conceptos": conceptos,
        "costo_material_util": str(_dinero(costo_material_util)),
        "costo_desperdicio_laboratorio": str(_dinero(costo_desperdicio)),
        "costo_apoyo_real": str(_dinero(costo_apoyo)),
        "costo_operativo_real": str(_dinero(costo_operativo)),
        "valor_referencial_facturable": str(_dinero(valor_facturable)),
        "aporte_institucional_real": str(_dinero(aporte)),
        "subtotal_usuario": str(_dinero(subtotal_usuario)),
        "iva": iva,
        "valor_final_usuario": str(_dinero(valor_usuario)),
        "estimacion_original": {
            "valor_referencial": str(_dinero(estimado_referencial)),
            "aporte_institucional": str(_dinero(estimado_aporte)),
            "valor_usuario": str(_dinero(estimado_usuario)),
        },
        "variacion": {
            "valor_referencial": str(_diferencia(valor_facturable, estimado_referencial)),
            "aporte_institucional": str(_diferencia(aporte, estimado_aporte)),
            "valor_usuario": str(_diferencia(valor_usuario, estimado_usuario)),
        },
        "advertencias": list(dict.fromkeys(advertencias)),
        "politica": (
            "El material útil se imputa al usuario; el aporte institucional cubre "
            "todos los recursos y componentes de servicio y el laboratorio "
            "asume el desperdicio registrado."
        ),
    }
