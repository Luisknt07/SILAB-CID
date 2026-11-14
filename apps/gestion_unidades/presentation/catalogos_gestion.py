"""Catálogos operativos paginados; los selectores conservan el alcance completo."""

from django.conf import settings
from django.core.exceptions import BadRequest, PermissionDenied, ValidationError
from django.core.paginator import Page, Paginator
from django.db.models import Case, Count, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.urls import reverse

from apps.recursos.models.redistribucion import AlertaUsoEquipo
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad
from apps.gestion_unidades.presentation.agrupacion_catalogos import filtrar_area_catalogo
from apps.gestion_unidades.presentation.categorias_catalogos import filtrar_categoria_catalogo
from apps.recursos.presentation.areas_recursos import SIN_AREA, areas_ordenadas_de

TAMANO_PAGINA = 50
TAMANO_PAGINA_TARJETAS = 12


def equipos_de(unidad):
    return UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad)
    ).distinct()


def consulta_catalogo(unidad, tipo):
    equipos = equipos_de(unidad)
    if tipo == "equipos":
        return (
            equipos,
            ("equipo__nombre", "codigo_unidad", "codigo_bien", "numero_serie"),
            "equipo__nombre",
        )
    if tipo in {"modelos", "modelos_unidad", "principales"}:
        consulta = EquiposServicios.objects.all()
        if tipo != "modelos":
            consulta = consulta.filter(pk__in=equipos.values("equipo_id"))
        if tipo == "principales":
            consulta = consulta.filter(rol="principal")
        return consulta, ("nombre", "codigo", "marca", "modelo"), "nombre"
    if tipo == "espacios":
        return (
            EspacioReservable.objects.filter(unidad=unidad),
            ("nombre", "codigo", "equipos_asociados__equipo__nombre"),
            "nombre",
        )
    if tipo == "software":
        return (
            SoftwareDisponible.objects.filter(unidad=unidad),
            ("nombre", "codigo", "version", "equipos_instalados__equipo__nombre"),
            "nombre",
        )
    if tipo == "insumos":
        return (
            Consumible.objects.filter(unidad=unidad),
            ("nombre", "codigo", "familia"),
            "nombre",
        )
    raise ValidationError("Catálogo no válido.")


def ordenar(consulta, tipo, campo):
    campos = {
        "equipos": ("equipo__nombre", "codigo_unidad", "pk"),
        "espacios": ("orden", "nombre", "pk"),
        "software": ("nombre", "version", "pk"),
        "insumos": ("clasificacion", "familia", "nombre", "pk"),
    }
    return consulta.order_by(*campos.get(tipo, (campo, "pk")))


def buscar(consulta, campos, texto):
    if texto:
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{f"{campo}__icontains": texto})
        consulta = consulta.filter(condicion)
    return consulta.distinct()


def texto_busqueda(valor):
    if "\0" in valor:
        raise ValidationError("La búsqueda contiene caracteres no válidos.")
    return valor.strip()[:120]


def _areas_del_inventario(consulta, unidad, valor):
    """La misma primera área del agrupador, resuelta en SQL antes del límite.

    El orden se calcula con el criterio común de Python para no depender de la
    intercalación de texto de la base de datos. Las áreas ajenas no participan.
    """
    areas = areas_ordenadas_de(unidad)
    valor = str(valor or '').strip()
    if valor and valor != 'sin_area' and valor not in {str(area.pk) for area in areas}:
        raise BadRequest('Selecciona un área de esta unidad.')
    if areas:
        prioridad = Case(*(When(pk=area.pk, then=Value(indice)) for indice, area in enumerate(areas)),
                         output_field=IntegerField())
        primera = EspacioReservable.objects.filter(
            unidad=unidad, equipos_asociados__pk=OuterRef('pk'),
        ).order_by(prioridad).values('pk')[:1]
        consulta = consulta.annotate(_inventario_area_id=Subquery(primera))
    else:
        consulta = consulta.annotate(_inventario_area_id=Value(None, output_field=IntegerField()))
    return consulta, valor, areas


def _modelos_del_inventario(consulta):
    return consulta.order_by('equipo__nombre', 'equipo_id').values_list('equipo_id', flat=True).distinct()


def _pagina_por_modelos(consulta, numero):
    """Una página de modelos entrega todas sus unidades físicas coincidentes.

    La colección sigue siendo un QuerySet de UnidadEquipo; los índices y el
    contador del paginador se expresan en modelos, no en unidades físicas.
    """
    modelos = Paginator(_modelos_del_inventario(consulta), TAMANO_PAGINA).get_page(numero)
    fisicos = consulta.filter(equipo_id__in=list(modelos.object_list))
    return Page(fisicos, modelos.number, modelos.paginator), modelos


def contexto_pagina(request, unidad, modo):
    tipo = {
        "activos": "equipos",
        "espacios": "espacios",
        "software": "software",
        "insumos": "insumos",
    }[modo]
    consulta, campos, orden = consulta_catalogo(unidad, tipo)
    try:
        texto = texto_busqueda(request.GET.get("busqueda_recursos", ""))
    except ValidationError as error:
        raise BadRequest("Búsqueda no válida.") from error
    # Gestión conserva la referencia en su sitio al desactivarla. Los totales
    # reales y las consultas públicas siguen usando exclusivamente los activos.
    estado = request.GET.get("estado_recursos", "todos")
    if estado not in {"activos", "inactivos", "todos"}:
        estado = "todos"
    if estado != "todos":
        if tipo == "equipos":
            vigente = Q(activa=True, fecha_baja__isnull=True)
            consulta = consulta.filter(vigente if estado == "activos" else ~vigente)
        else:
            consulta = consulta.filter(activo=estado == "activos")
    filtro = request.GET.get("filtro_recursos", "") if modo == "activos" else ""
    if filtro in {"servicio", "fuera"}:
        publico = Q(activa=True, fecha_baja__isnull=True, estado_unidad__in=UnidadEquipo.ESTADOS_PUBLICOS)
        if getattr(settings, "CITT_EXIGIR_EQUIPOS_VERIFICADOS", False):
            publico &= Q(existencia_verificada=True)
        consulta = consulta.filter(publico if filtro == "servicio" else (
            Q(activa=True, fecha_baja__isnull=True) & ~publico))
    elif filtro == "verificar":
        consulta = consulta.filter(activa=True, fecha_baja__isnull=True, existencia_verificada=False)
    elif filtro == "alerta":
        consulta = consulta.filter(activa=True, fecha_baja__isnull=True).filter(
            pk__in=AlertaUsoEquipo.objects.filter(
                estado__in=AlertaUsoEquipo.VIGENTES
            ).values("equipo_id")
        )
    else:
        filtro = ""
    area, areas = '', []
    if modo in {'software', 'insumos'}:
        consulta, area, areas = filtrar_area_catalogo(
            consulta, unidad, tipo, request.GET.get('area_recursos', ''),
        )
    elif modo == 'activos':
        consulta, area, areas = _areas_del_inventario(consulta, unidad, request.GET.get('area_recursos', ''))
    consulta = ordenar(buscar(consulta, campos, texto), tipo, orden)
    datos_categoria = {}
    if modo in {'software', 'insumos'}:
        consulta, datos_categoria = filtrar_categoria_catalogo(consulta, request, unidad, tipo)

    def con_area(consulta):
        if not area:
            return consulta
        return consulta.filter(_inventario_area_id=None if area == 'sin_area' else int(area))

    completa = consulta
    if modo == 'activos':
        consulta = con_area(consulta)
    pagina_pedida = request.GET.get("pagina_recursos")
    foco = request.GET.get("enfocar_recurso", "").strip()
    foco = int(foco) if (foco.isascii() and foco.isdecimal() and len(foco) <= 19
                        and 0 < int(foco) <= 2**63 - 1) else None
    edicion = request.GET.get("editar_equipo", "").strip() or str(foco or '')
    if (
        modo == "activos"
        and edicion
        and len(edicion) <= 19
        and edicion.isascii()
        and edicion.isdecimal()
        and 0 < int(edicion) <= 2**63 - 1
    ):
        destino = (
            equipos_de(unidad)
            .filter(pk=int(edicion))
            .values("pk", "equipo_id", "equipo__nombre", "codigo_unidad")
            .first()
        )
        if destino:
            if not consulta.filter(pk=destino["pk"]).exists():
                consulta, _, orden = consulta_catalogo(unidad, "equipos")
                consulta, area, areas = _areas_del_inventario(consulta, unidad, '')
                consulta = ordenar(consulta, "equipos", orden)
                completa = consulta
                estado, texto, filtro = "todos", "", ""
            nombre = destino["equipo__nombre"]
            posicion = _modelos_del_inventario(consulta).filter(
                Q(equipo__nombre__lt=nombre)
                | Q(equipo__nombre=nombre, equipo_id__lte=destino["equipo_id"])
            ).count()
            pagina_pedida = (posicion - 1) // TAMANO_PAGINA + 1
    datos_equipos = {}
    if modo == 'activos':
        pagina, modelos_pagina = _pagina_por_modelos(consulta, pagina_pedida)
        conteos = {fila['_inventario_area_id']: fila for fila in completa.order_by().values(
            '_inventario_area_id',
        ).annotate(total=Count('pk', distinct=True), modelos=Count('equipo_id', distinct=True))}
        datos_equipos = {
            'recursos_unidad_paginacion': 'modelos',
            'recursos_modelos_pagina': modelos_pagina,
            'recursos_total_fisicos': consulta.count(),
            'recursos_total_modelos': pagina.paginator.count,
            'recursos_total_fisicos_todas_areas': sum(fila['total'] for fila in conteos.values()),
            'recursos_total_modelos_todas_areas': _modelos_del_inventario(completa).count(),
            'recursos_area_nombre': SIN_AREA if area == 'sin_area' else next(
                (espacio.nombre for espacio in areas if str(espacio.pk) == area), ''),
        }
    else:
        tamano = TAMANO_PAGINA_TARJETAS if modo in {'software', 'insumos'} else TAMANO_PAGINA
        if foco and consulta.filter(pk=foco).exists():
            posicion = next(i for i, pk in enumerate(consulta.values_list('pk', flat=True)) if pk == foco)
            pagina_pedida = posicion // tamano + 1
        pagina = Paginator(consulta, tamano).get_page(pagina_pedida)
    parametros_actuales = request.GET.copy()
    parametros_actuales["pagina_recursos"] = pagina.number
    parametros_actuales["estado_recursos"] = estado
    parametros_actuales["busqueda_recursos"] = texto
    parametros_actuales["filtro_recursos"] = filtro
    if modo in {'activos', 'software', 'insumos'}:
        parametros_actuales['area_recursos'] = area
    else:
        parametros_actuales.pop('area_recursos', None)
    parametros_actuales.pop("editar_equipo", None)
    parametros_actuales.pop("enfocar_recurso", None)

    def enlace(numero, area_elegida=None):
        parametros = parametros_actuales.copy()
        parametros["view"] = "recursos"
        parametros["modo_recursos"] = modo
        parametros["pagina_recursos"] = numero
        if area_elegida is not None:
            parametros['area_recursos'] = area_elegida
        return (
            f"{reverse('gestion_unidad', args=[unidad.slug])}?{parametros.urlencode()}"
        )

    if modo == 'activos':
        navegacion = []
        for espacio in areas:
            cantidades = conteos.get(espacio.pk, {})
            valor = str(espacio.pk)
            navegacion.append({'valor': valor, 'nombre': espacio.nombre, 'codigo': espacio.codigo,
                'activa': espacio.activo, 'total': cantidades.get('total', 0), 'modelos': cantidades.get('modelos', 0),
                'url': enlace(1, valor), 'seleccionada': area == valor})
        if None in conteos:
            navegacion.append({'valor': 'sin_area', 'nombre': SIN_AREA, 'codigo': '', 'activa': True,
                'total': conteos[None]['total'], 'modelos': conteos[None]['modelos'],
                'url': enlace(1, 'sin_area'), 'seleccionada': area == 'sin_area'})
        datos_equipos.update(recursos_navegacion_areas=navegacion, recursos_todas_areas_url=enlace(1, ''))

    return pagina, {
        **datos_equipos,
        **datos_categoria,
        "catalogos_remotos": True,
        "recursos_tamano_pagina": pagina.paginator.per_page,
        "recursos_query": parametros_actuales.urlencode(),
        "recursos_pagina": pagina,
        "recursos_busqueda": texto,
        "recursos_estado": estado,
        "recursos_filtro": filtro,
        "recursos_area": area,
        "recursos_areas": areas,
        "recursos_anterior": enlace(pagina.previous_page_number())
        if pagina.has_previous()
        else "",
        "recursos_siguiente": enlace(pagina.next_page_number())
        if pagina.has_next()
        else "",
    }


def disponibilidad_global(unidad):
    equipos = equipos_de(unidad).filter(activa=True, fecha_baja__isnull=True)
    espacios = EspacioReservable.objects.filter(unidad=unidad, activo=True)
    programas = SoftwareDisponible.objects.filter(unidad=unidad, activo=True)
    e = equipos.aggregate(
        total=Count("pk", distinct=True),
        disponibles=Count("pk", filter=Q(estado_unidad="disponible"), distinct=True),
    )
    a = espacios.aggregate(
        total=Count("pk"), disponibles=Count("pk", filter=Q(reservable=True))
    )
    s = programas.aggregate(
        total=Sum("licencias_totales"), disponibles=Sum("licencias_disponibles")
    )
    return {"equipos": e, "espacios": a, "software": {k: v or 0 for k, v in s.items()}}


def resultados_selector(request, unidad):
    tipo = request.GET.get("tipo", "")
    permisos = permisos_operativos_unidad(request.user, unidad)
    if not (
        permisos.get("recursos") or (tipo != "modelos" and permisos.get("inventario"))
    ):
        raise PermissionDenied
    consulta, campos, orden = consulta_catalogo(unidad, tipo)
    seleccion = request.GET.get("ids", "")
    if seleccion:
        valores = seleccion.split(",")
        if len(valores) > TAMANO_PAGINA or any(
            len(v) > 19
            or not v.isascii()
            or not v.isdecimal()
            or not 0 < int(v) <= 2**63 - 1
            for v in valores
        ):
            raise ValidationError("Selección no válida.")
        consulta = consulta.filter(pk__in=[int(v) for v in valores])
    else:
        texto = texto_busqueda(request.GET.get("q", ""))
        if len(texto) < 2:
            return {"items": [], "pagina": 1, "paginas": 1, "total": 0}
        consulta = buscar(consulta, campos, texto)
    if tipo == "equipos":
        consulta = consulta.select_related("equipo").only(
            "pk", "codigo_unidad", "equipo__nombre"
        )
    else:
        campos_visibles = (
            ("pk", "nombre", "codigo", "version")
            if tipo == "software"
            else ("pk", "nombre", "codigo")
        )
        consulta = consulta.only(*campos_visibles)
    pagina = Paginator(ordenar(consulta, tipo, orden), TAMANO_PAGINA).get_page(
        request.GET.get("pagina")
    )
    if tipo == "equipos":
        objetos = pagina.object_list.select_related("equipo")
    else:
        objetos = pagina.object_list
    items = []
    for objeto in objetos:
        if tipo == "equipos":
            texto = f"{objeto.codigo_unidad} · {objeto.equipo.nombre}"
        else:
            codigo = getattr(objeto, "codigo", "") or getattr(objeto, "version", "")
            texto = f"{objeto.nombre} · {codigo}" if codigo else objeto.nombre
        items.append({"id": objeto.pk, "text": texto})
    return {
        "items": items,
        "pagina": pagina.number,
        "paginas": pagina.paginator.num_pages,
        "total": pagina.paginator.count,
    }
