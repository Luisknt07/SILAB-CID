"""Detalle público e interactivo de una Unidad."""

from apps.core.presentation.calendario import ambitos_operacion

from apps.core.presentation.catalogos import facultades, carreras


from django.db.models import F, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.core.presentation.tipologias import tipologia_activa
from django.templatetags.static import static
from django.urls import reverse

from apps.gestion_unidades.models.operaciones import ventana_atencion
from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva, Reserva
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.recursos import ReglamentoUnidad
from apps.core.models.usuarios_base import UserProfile
from apps.core.models.periodos import VersionCalendarioAcademico

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.gestion_unidades.presentation.altas_en_ficha import acciones_de_seccion
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.secciones_propias import puede_editar_secciones
from apps.reservas.presentation.proceso import catalogo_para_reserva, recetas_para_practica
from apps.formacion.presentation.asignaturas import asignaturas_para
from apps.formacion.presentation.aula import contexto_aula
from apps.gestion_unidades.presentation.conoce import equipos_de_la_unidad, se_muestra
from apps.gestion_unidades.presentation.interior import interior_de_la_planta
from apps.gestion_unidades.presentation.portadas import portadas_de
from apps.formacion.presentation.recursos_publicos import carpetas_publicables
from apps.reservas.presentation.visitas import oferta_de_visitas
from apps.reservas.presentation.rutas import icono_espacio_reserva, imagen_espacio_reserva, textos_rutas_reserva
from apps.directorio_unidades.presentation.relaciones import relaciones_de
from apps.reservas.presentation.seguridad import acceso_de_usuario, resumen_requisitos
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de


# Los Centros I+D que integran una unidad: la vertical expone nombres y enlaces, no sus modelos.
def centros_id_que_integran(slug):
    from django.apps import apps
    if not apps.is_installed('apps.centros_id'):
        return []
    from apps.centros_id.vinculos import centros_que_integran
    return centros_que_integran(slug)


# El catálogo público agrupa por clase; los nombres y descripciones viven
# en el modelo para que el panel y el catálogo digan lo mismo.
CATALOGO_INVENTARIO_META = {
    clave: {"nombre": nombre, "descripcion": descripcion}
    for clave, (nombre, descripcion) in Consumible.CLASIFICACION_DETALLE.items()
}


def resumir_horario_operativo(horarios):
    """Presenta el horario general sin ocultar que puede variar por período."""
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    generales = [horario for horario in horarios if horario.periodo_id is None]
    especiales = any(horario.periodo_id is not None for horario in horarios)
    por_dia = {}
    for horario in generales:
        por_dia.setdefault(horario.dia_semana, []).append(
            f"{horario.hora_inicio:%H:%M}–{horario.hora_fin:%H:%M}"
        )

    bloques = []
    inicio = None
    fin = None
    rangos_actuales = None
    for dia in range(8):
        rangos = tuple(sorted(por_dia.get(dia, []))) if dia < 7 else None
        if rangos and rangos == rangos_actuales:
            fin = dia
            continue
        if rangos_actuales:
            etiqueta_dias = dias[inicio] if inicio == fin else f"{dias[inicio]}–{dias[fin]}"
            bloques.append(f"{etiqueta_dias} {' / '.join(rangos_actuales)}")
        inicio = fin = dia if rangos else None
        rangos_actuales = rangos

    if not bloques:
        resumen = "Consultar disponibilidad"
    else:
        resumen = " · ".join(bloques)
    if especiales:
        resumen += " · Puede variar según el período"
    return resumen


def _agrupar_catalogo_inventario(elementos):
    """Organiza el catálogo público por tipo principal y familia técnica."""
    grupos = {}
    for elemento in elementos:
        tipo = elemento.clasificacion
        meta = CATALOGO_INVENTARIO_META.get(tipo, CATALOGO_INVENTARIO_META["material"])
        grupo = grupos.setdefault(
            tipo,
            {
                "codigo": tipo,
                "nombre": meta["nombre"],
                "descripcion": meta["descripcion"],
                "familias": {},
                "total": 0,
            },
        )
        familia = elemento.familia.strip() if elemento.familia else "Sin familia asignada"
        grupo["familias"].setdefault(familia, []).append(elemento)
        grupo["total"] += 1

    orden_tipos = {"insumo": 0, "material": 1}
    resultado = []
    for grupo in sorted(grupos.values(), key=lambda item: orden_tipos.get(item["codigo"], 99)):
        grupo["familias"] = [
            {"nombre": nombre, "items": items, "total": len(items)}
            for nombre, items in sorted(grupo["familias"].items(), key=lambda item: item[0].lower())
        ]
        resultado.append(grupo)
    return resultado


def _imagen_consumible(consumible):
    """Imagen publicada del insumo, con el mismo criterio en toda la reserva.

    Se usa la fotografía cargada o la del catálogo institucional; cuando no
    hay ninguna se deja vacío para que la tarjeta muestre su marco neutro, en
    vez de inventar una imagen que no corresponde al material.
    """
    if consumible.imagen:
        try:
            return consumible.imagen.url
        except ValueError:
            return ''
    if consumible.imagen_catalogo:
        return static(consumible.imagen_catalogo)
    return ''


def _registrar_visita(request, unidad):
    """Una visita por persona y sesión; quien gestiona la unidad o el sitio no cuenta como visitante."""
    if request.user.is_staff or request.user.is_superuser or puede_gestionar_unidad(request.user, unidad):
        return
    visitados = request.session.get("unidades_visitadas", [])
    if unidad.id in visitados:
        return
    Unidad.objects.filter(pk=unidad.pk).update(visitas=F("visitas") + 1)
    unidad.visitas += 1
    visitados.append(unidad.id)
    request.session["unidades_visitadas"] = visitados


def proyecto_detalle_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if unidad.dependencia and not tipologia_activa(unidad.dependencia):
        # Una tipologia desactivada retira su superficie publica en el
        # servidor; la unidad y su historial permanecen intactos.
        raise Http404
    # Lo mismo una unidad desactivada; quien la gestiona la sigue viendo para prepararla.
    if not unidad.activo and not puede_gestionar_unidad(request.user, unidad):
        raise Http404
    _registrar_visita(request, unidad)
    configuracion_operativa, _ = ConfiguracionOperativaUnidad.objects.get_or_create(
        unidad=unidad
    )

    modulos = (
        unidad.modulos_contenido.filter(activo=True)
        .prefetch_related("carpetas__recursos")
        .order_by("orden", "id")
    )
    unidades_equipo, equipos = equipos_de_la_unidad(unidad)
    # Plantas y laboratorios tienen ficha numerada; centros y observatorios, pestañas libres.
    tiene_mapa = mapa_de(unidad) is not None
    seccion_activa = {
        "laboratorios": "laboratorios",
        "observatorios": "observatorios",
        "centro_experimental": "centros_experimentales",
        "plantas_piloto": "plantas_piloto",
    }.get(unidad.codigo_base, "laboratorios")

    reglamento, _ = ReglamentoUnidad.objects.get_or_create(unidad=unidad)
    reglamento_data = {
        "activo": reglamento.activo,
        "titulo": reglamento.titulo,
        "subtitulo": reglamento.subtitulo,
        "normas_generales": reglamento.normas_generales,
        "reservas_horarios": reglamento.reservas_horarios,
        "equipos_materiales": reglamento.equipos_materiales,
        "seguridad": reglamento.seguridad,
        "contacto_texto": reglamento.contacto_texto,
        "contacto_email": reglamento.contacto_email,
    }
    consumibles_reserva = []
    if configuracion_operativa.consumibles:
        consumibles_reserva = list(
            Consumible.objects.filter(
                unidad=unidad,
                activo=True,
                visible_en_reservas=True,
            )
            .prefetch_related("por_equipo")
            .order_by("clasificacion", "familia", "nombre")
        )
    servicios_reserva = list(
        FablabService.objects.filter(
            unidad=unidad,
            activo=True,
            publico=True,
        )
        .exclude(tipo_servicio='visita')
        .prefetch_related("service_consumibles__consumible__por_equipo__equipo")
        .order_by("code", "nombre")
    )
    software_reserva = list(
        SoftwareDisponible.objects.filter(
            unidad=unidad,
            activo=True,
            requiere_reserva=True,
        )
        .prefetch_related("equipos_instalados__equipo")
        .order_by("nombre", "version")
    )
    espacios_reserva = list(
        EspacioReservable.objects.filter(
            unidad=unidad,
            activo=True,
            reservable=True,
        )
        .prefetch_related(
            "equipos_asociados__equipo",
            "equipos_asociados__software_instalado",
        )
        .order_by("orden", "nombre", "id")
    )
    for espacio in espacios_reserva:
        espacio.icono_reserva = icono_espacio_reserva(espacio)
        espacio.imagen_reserva_url = imagen_espacio_reserva(espacio)
    responsables_reserva = list(
        ResponsableUnidad.objects.filter(
            unidad=unidad,
            usuario__isnull=False,
            activo=True,
            publico=True,
            recibe_reservas=True,
        )
        .select_related("usuario", "usuario__profile")
        .order_by("orden", "nombre", "id")
    )
    perfil_reserva = None
    perfil_reserva_faltantes = []
    if request.user.is_authenticated:
        perfil_reserva = getattr(request.user, "profile", None)
        if perfil_reserva:
            perfil_reserva_faltantes = perfil_reserva.campos_faltantes_reserva()
    from apps.gestion_unidades.presentation.permisos import puede_crear_guias_unidad, puede_operar_modulo_unidad
    from apps.reservas.presentation.cotizaciones import aviso_pertenencia_tarifaria, clasificacion_tarifaria_actual

    puede_crear_guias_reserva = puede_crear_guias_unidad(request.user, unidad)
    segmento_tarifario, _, pertenencia_tarifaria = clasificacion_tarifaria_actual(request.user)
    servicios_por_consumible = {}
    for servicio in servicios_reserva:
        relaciones_consumibles = list(servicio.service_consumibles.all())
        ids_consumibles = [
            relacion.consumible_id for relacion in relaciones_consumibles
        ]
        servicio.consumibles_ids_csv = ",".join(map(str, ids_consumibles))
        servicio.consumibles_planificados = [
            {
                "id": relacion.consumible_id,
                "nombre": relacion.consumible.nombre,
                # Identidad idéntica a la del catálogo de insumos de la
                # reserva: quien pide el servicio reconoce el material.
                "clasificacion": relacion.consumible.get_clasificacion_display(),
                "variante": relacion.consumible.variante,
                "color": relacion.consumible.color,
                "detalle": " · ".join(
                    filter(None, [relacion.consumible.variante, relacion.consumible.color])
                ),
                "imagen": _imagen_consumible(relacion.consumible),
                # Orientación del inventario para calcular la cantidad.
                "instrucciones": relacion.consumible.instrucciones_solicitud,
                "cantidad": relacion.cantidad_sugerida,
                "unidad": relacion.consumible.unidad_medida or "unidades",
                "por_calcular": not bool(relacion.cantidad_sugerida),
                "obligatorio": bool(relacion.obligatorio),
                "precio_unitario": relacion.consumible.precio_unitario or 0,
                "stock": relacion.consumible.stock_total or 0,
                # Equipos compatibles del insumo: opciones de equipo del trabajo.
                "equipos_ids_csv": ",".join(
                    str(item.equipo_id) for item in relacion.consumible.por_equipo.all()
                ),
                "equipos_nombres": " / ".join(
                    item.equipo.nombre for item in relacion.consumible.por_equipo.all()
                ),
            }
            for relacion in relaciones_consumibles
        ]
        for consumible_id in ids_consumibles:
            servicios_por_consumible.setdefault(consumible_id, []).append(servicio.pk)
    # El catalogo agrupa los servicios afines (Impresion 3D, Corte y mecanizado...)
    # para que la persona elija la opcion que mejor se ajusta a su necesidad.
    familias = {}
    for servicio in servicios_reserva:
        familias.setdefault(servicio.familia_catalogo, []).append(servicio)
    servicios_por_familia = [
        {"nombre": nombre, "servicios": lista} for nombre, lista in familias.items()
    ]
    for consumible in consumibles_reserva:
        consumible.servicios_ids_csv = ",".join(
            map(str, servicios_por_consumible.get(consumible.pk, []))
        )
        consumible.equipos_compatibles_ids_csv = ",".join(
            str(relacion.equipo_id) for relacion in consumible.por_equipo.all()
        )
    catalogo_inventario_reserva = _agrupar_catalogo_inventario(consumibles_reserva)
    # Lo que la unidad produce se publica sin existencias: nombre, presentación y precio.
    # Los procesos que se pueden practicar: el asistente los ofrece al elegir la actividad.
    catalogo_procesos_reserva = catalogo_para_reserva(unidad)
    # Lo que la unidad exige para entrar: la ficha lo publica y el asistente lo
    # muestra con el estado de quien solicita.
    requisitos_ingreso = resumen_requisitos(unidad)
    acceso_reserva = acceso_de_usuario(unidad, request.user) if requisitos_ingreso else None
    # Las asignaturas que el docente puede elegir al programar el período.
    asignaturas_docente = asignaturas_para(unidad, request.user)
    # Las sesiones que quien entra programó aquí: la ficha ofrece completarlas.
    tiene_sesiones_programadas = bool(
        request.user.is_authenticated
        and Reserva.objects.filter(
            laboratorio=unidad, usuario=request.user, programacion__isnull=False
        ).exists()
    )
    actividades_query = CatalogoActividadReserva.objects.filter(
        Q(unidad__isnull=True) | Q(unidad=unidad),
        activo=True,
    )
    guias_query = GuiaActividadReserva.objects.filter(activo=True)
    if puede_operar_modulo_unidad(request.user, unidad, 'practicas'):
        pass
    elif request.user.is_authenticated:
        actividades_query = actividades_query.filter(
            Q(estado_publicacion='publicado', visibilidad__in=['unidad', 'institucional'])
            | Q(creado_por=request.user)
            | Q(participantes_autorizados=request.user)
        )
        acceso_actividad_aprobada = (
            Q(actividad__creado_por=request.user)
            | Q(actividad__participantes_autorizados=request.user)
        ) & Q(
            actividad__reservas__estado__in=['confirmada', 'en_proceso', 'completada']
        )
        guias_query = guias_query.filter(
            Q(estado_publicacion='publicada', visibilidad__in=['unidad', 'publica'])
            | acceso_actividad_aprobada
        ).distinct()
    else:
        actividades_query = actividades_query.filter(
            estado_publicacion='publicado',
            visibilidad__in=['unidad', 'institucional'],
        )
        guias_query = guias_query.filter(
            estado_publicacion='publicada',
            visibilidad='publica',
        )
    # El selector de la reserva solo puede ofrecer versiones institucionales
    # aprobadas. Los borradores propios permanecen en el módulo documental.
    guias_aprobadas_reserva = GuiaActividadReserva.objects.filter(
        activo=True,
        estado_publicacion="publicada",
    )
    if not request.user.is_authenticated:
        # La vista de la guia cierra con 404 al visitante todo lo que no sea
        # publico; enlazarselo era darle enlaces rotos. Quien ha iniciado
        # sesion conserva su alcance (autor, participante, comunidad).
        guias_aprobadas_reserva = guias_aprobadas_reserva.filter(visibilidad='publica')
    actividades_reserva = list(
        actividades_query.select_related('periodo', 'creado_por')
        .prefetch_related(
            Prefetch(
                'guias',
                queryset=guias_aprobadas_reserva,
                to_attr='guias_visibles',
            )
        )
        .distinct()
        .order_by('proposito_codigo', 'orden', 'nombre')
    )
    guias_clonables_reserva = [
        {
            'guia_id': guia.pk,
            'actividad_id': actividad.pk,
            'actividad': actividad.nombre,
            'codigo': actividad.codigo,
            'contenido': guia.contenido or {},
        }
        for actividad in actividades_reserva
        for guia in actividad.guias_visibles
        if guia.es_estructurada
    ]
    for actividad in actividades_reserva:
        guia_referencia = next(
            (guia for guia in actividad.guias_visibles if guia.es_estructurada),
            actividad.guias_visibles[0] if actividad.guias_visibles else None,
        )
        actividad.familia_guia_id = (
            guia_referencia.familia_id if guia_referencia else None
        )
        contenido_guia = (
            guia_referencia.contenido
            if guia_referencia and isinstance(guia_referencia.contenido, dict)
            else {}
        )
        actividad.asignatura_guia = str(contenido_guia.get('asignatura') or '')
    guias_consultables = list(
        guias_query.filter(
            Q(actividad__unidad__isnull=True) | Q(actividad__unidad=unidad),
            actividad__activo=True,
        )
        .select_related('actividad', 'actividad__periodo')
        .distinct()
        .order_by('actividad__nombre', 'orden', 'titulo')
    )
    guias_publicadas_query = GuiaActividadReserva.objects.filter(
        activo=True,
        estado_publicacion='publicada',
        actividad__activo=True,
    ).filter(
        Q(actividad__unidad__isnull=True) | Q(actividad__unidad=unidad),
    )
    if not request.user.is_authenticated:
        guias_publicadas_query = guias_publicadas_query.filter(visibilidad='publica')
    else:
        guias_publicadas_query = guias_publicadas_query.filter(
            visibilidad__in=['unidad', 'publica'],
        )
    guias_publicadas = sorted(
        guias_publicadas_query.select_related('actividad', 'familia')
        .order_by('actividad__nombre', 'orden', 'titulo'),
        key=lambda guia: (
            guia.familia_id is None,
            guia.familia.orden if guia.familia_id else 0,
            guia.actividad.nombre.lower(),
            guia.orden,
            guia.titulo.lower(),
        ),
    )
    procesos_publicados = list(recetas_para_practica(unidad))
    procesos_por_familia = {}
    for proceso in procesos_publicados:
        if proceso.familia_id:
            procesos_por_familia.setdefault(proceso.familia_id, []).append(proceso.nombre)
    guias_por_familia = []
    for guia in guias_publicadas:
        familia_id = guia.familia_id
        nombre_familia = guia.familia.nombre if familia_id else 'Guías generales'
        if not guias_por_familia or guias_por_familia[-1]['familia_id'] != familia_id:
            guias_por_familia.append({
                'familia_id': familia_id,
                'nombre': nombre_familia,
                'procesos': procesos_por_familia.get(familia_id, []),
                'guias': [],
            })
        guias_por_familia[-1]['guias'].append(guia)

    gestor_unidad = puede_gestionar_unidad(request.user, unidad)
    recursos_configurados = carpetas_publicables(unidad, request.user)
    carpetas_publicas = recursos_configurados['raices']
    periodos_calendario_reserva = [
        {
            "id": version.periodo_id,
            "version_id": version.pk,
            "codigo": version.periodo.codigo,
            "nombre": str(version.periodo),
            "inicio": version.fecha_inicio_clases.isoformat(),
            "fin_clases": version.fecha_fin_clases.isoformat(),
            "fin": version.fecha_fin_periodo.isoformat(),
            "semanas": version.periodo.semanas_planificadas,
            "tipo": version.periodo.tipo,
        }
        for version in VersionCalendarioAcademico.objects.filter(
            vigente=True,
            periodo__estado__in=['publicado', 'cerrado'],
            periodo__ambito__in=ambitos_operacion(),
        ).select_related('periodo').order_by('-periodo__anio_referencia', '-periodo__ciclo')
    ]
    horarios_operacion = list(
        HorarioOperacionUnidad.objects.filter(
            unidad=unidad,
            activo=True,
        ).select_related("periodo").order_by(
            "periodo__codigo", "dia_semana", "hora_inicio"
        )
    )
    horarios_operacion_reserva = [
        {
            "id": horario.pk,
            "periodo_id": horario.periodo_id,
            "periodo_codigo": horario.periodo.codigo if horario.periodo_id else "",
            "dia_semana": horario.dia_semana,
            "hora_inicio": horario.hora_inicio.strftime("%H:%M"),
            "hora_fin": horario.hora_fin.strftime("%H:%M"),
            "permite_recursos": horario.permite_recursos,
            "permite_servicios": horario.permite_servicios,
            "tipos_usuario": horario.tipos_usuario_habilitados,
            "propositos": horario.propositos_habilitados,
        }
        for horario in horarios_operacion
    ]
    tipos_usuario_por_periodo = {}
    if request.user.is_authenticated:
        tipos_usuario_por_periodo = {
            str(periodo_id): tipo_usuario
            for periodo_id, tipo_usuario in request.user.vinculaciones_academicas.filter(
                estado="activa",
            ).values_list("periodo_id", "tipo_usuario")
        }

    # El aula se arma una sola vez: sus carpetas alimentan la ficha y también
    # la portada con que cada pestaña se presenta cuando no hay nada abierto.
    contexto_del_aula = contexto_aula(unidad, modulos, request.user)
    if tiene_mapa:
        por_seccion = recursos_configurados['por_seccion']
        for carpeta in contexto_del_aula['aula']['carpetas']:
            personalizadas = por_seccion.get(carpeta.get('numero'), [])
            carpeta['carpetas_personalizadas'] = personalizadas
            carpeta['total'] += sum(item.total_recursos for item in personalizadas)
            if personalizadas:
                carpeta['pendiente'] = False
        for seccion in contexto_del_aula['secciones_planta'].values():
            personalizadas = por_seccion.get(seccion['numero'], [])
            seccion['carpetas_personalizadas'] = personalizadas
            seccion['total_personalizado'] = sum(item.total_recursos for item in personalizadas)
        if not gestor_unidad:
            # Una sección sin contenido es tarea de la unidad: el público no ve el hueco.
            carpetas = [c for c in contexto_del_aula['aula']['carpetas'] if not c.get('pendiente')]
            contexto_del_aula['aula']['carpetas'] = carpetas
            contexto_del_aula['aula']['modulos_con_carpetas'] = sorted({c['modulo'] for c in carpetas})
        # Una pestaña sin nada publicado tampoco se ofrece al público; quien gestiona la ve marcada.
        mapa = mapa_de(unidad)
        con_contenido = {'informacion-general', mapa.modulo_reservas,
                         *(c['modulo'] for c in contexto_del_aula['aula']['carpetas'] if not c.get('pendiente')),
                         *recursos_configurados['por_modulo']}
        if guias_publicadas:
            con_contenido.add(contexto_del_aula['guias_modulo_clave'])
        modulos = list(modulos)
        for modulo in modulos:
            modulo.oculta_al_publico = modulo.clave not in con_contenido
        if not gestor_unidad:
            modulos = [modulo for modulo in modulos if not modulo.oculta_al_publico]
    # Cada sección ofrece, a quien puede, agregar su elemento con su plantilla y una carpeta propia; una pestaña
    # propia, una carpeta directo en ella.
    ediciones = ediciones_de(request.user, unidad)
    if gestor_unidad:
        mapa_unidad = mapa_de(unidad)
        if mapa_unidad is not None:
            for carpeta in contexto_del_aula['aula']['carpetas']:
                numero = carpeta.get('numero')
                if numero in mapa_unidad.secciones:
                    carpeta['agregar'] = acciones_de_seccion(unidad, mapa_unidad.secciones[numero]['clave'], numero,
                                                             ediciones, request.user)
            for clave, seccion in contexto_del_aula['secciones_planta'].items():
                seccion['agregar'] = acciones_de_seccion(unidad, clave, seccion['numero'], ediciones, request.user)
        if 'carpeta' in ediciones:
            for modulo in modulos:
                if mapa_unidad is None or modulo.clave not in mapa_unidad.pestanas:
                    modulo.agregar = [{'rotulo': 'Nueva carpeta', 'icono': 'fas fa-folder-plus', 'url': reverse(
                        'editar_registro', args=[unidad.slug, 'carpeta', 'nuevo']) + f'?padre=m:{modulo.pk}'}]
    identidad_logistica_visible = (
        unidad.slug == 'laboratorio-logistica-comercio-internacional'
        and unidad.dependencia == 'laboratorios'
        and any(modulo.clave == 'informacion-general' for modulo in modulos)
        and not (contexto_del_aula['secciones_planta'].get('interior') or {}).get('oculta', True)
    )
    contexto = {
        "unidad": unidad,
        "identidad_logistica_visible": identidad_logistica_visible,
        "configuracion_operativa": configuracion_operativa,
        "modulos": modulos,
        "equipos_servicios": equipos,
        "seccion_activa": seccion_activa,
        "unidades_laboratorio": unidades_equipo,
        "total_equipos": equipos.count(),
        "total_unidades_equipo": unidades_equipo.count(),
        "total_software": unidad.software_disponible.filter(activo=True).count(),
        "video_presentacion_id": unidad.video_unidad_youtube_id or 'IJxxIxTuMb8',
        "video_presentacion_propio": bool(unidad.video_unidad_youtube_id),
        "guias_por_familia": guias_por_familia,
        "total_guias_publicadas": len(guias_publicadas),
        "carpetas_publicas": carpetas_publicas,
        "interior": interior_de_la_planta(unidad, request.user, gestor_unidad) if tiene_mapa else None,
        "conoce_la_unidad": tiene_mapa and se_muestra(unidad, gestor_unidad),
        "reglamento_data": reglamento_data,
        "consumibles_reserva": consumibles_reserva,
        "catalogo_inventario_reserva": catalogo_inventario_reserva,
        "catalogo_procesos_reserva": catalogo_procesos_reserva,
        "requisitos_ingreso": requisitos_ingreso,
        "acceso_reserva": acceso_reserva,
        "asignaturas_docente": asignaturas_docente,
        "tiene_sesiones_programadas": tiene_sesiones_programadas,
        "oferta_visitas": oferta_de_visitas(unidad),
        **contexto_del_aula,
        "portadas_modulo": portadas_de(
            unidad,
            modulos,
            contexto_del_aula["aula"]["carpetas"],
            carpetas_contenido=recursos_configurados['por_modulo'],
        ),
        "servicios_reserva": servicios_reserva,
        "textos_rutas_reserva": textos_rutas_reserva(configuracion_operativa, servicios_reserva, software_reserva),
        "servicios_por_familia": servicios_por_familia,
        "software_reserva": software_reserva,
        "espacios_reserva": espacios_reserva,
        "responsables_reserva": responsables_reserva,
        "perfil_reserva": perfil_reserva,
        "perfil_reserva_completo": bool(perfil_reserva and not perfil_reserva_faltantes),
        "perfil_reserva_faltantes": perfil_reserva_faltantes,
        "actividades_reserva": actividades_reserva,
        "guias_clonables_reserva": guias_clonables_reserva,
        "guias_actividad_reserva": guias_consultables,
        "periodos_calendario_reserva": periodos_calendario_reserva,
        "horarios_operacion_reserva": horarios_operacion_reserva,
        "palabras_trabajo_reserva": configuracion_operativa.formas_trabajo,
        # Lo que esta unidad quiere que se escriba al pedirle algo.
        "ejemplos_solicitud_reserva": EjemploSolicitudUnidad.publicados(unidad),
        "ventana_atencion_reserva": dict(
            zip(
                ("apertura", "cierre"),
                ventana_atencion(configuracion_operativa),
            )
        ),
        "horario_operacion_resumen": resumir_horario_operativo(
            horarios_operacion
        ),
        "tipo_usuario_reserva": (
            perfil_reserva.tipo_usuario if perfil_reserva else ""
        ),
        # Las cifras del inventario son internas: existencias y precios se
        # muestran a quien se identifica; sin sesión el catálogo solo dice si
        # el material está disponible.
        "mostrar_existencias_reserva": request.user.is_authenticated,
        "puede_crear_guias_reserva": puede_crear_guias_reserva,
        "segmento_tarifario_reserva": segmento_tarifario,
        "aviso_pertenencia_reserva": aviso_pertenencia_tarifaria(pertenencia_tarifaria),
        "tipos_usuario_por_periodo": tipos_usuario_por_periodo,
        "propositos_reserva": Reserva.PROPOSITO_INSTITUCIONAL_CHOICES,
        "facultades_reserva": facultades(),
        "carreras_reserva": [
            {
                "codigo": codigo,
                "nombre": nombre,
                "facultad": UserProfile.facultad_para_carrera(codigo),
            }
            for codigo, nombre in carreras()
            if UserProfile.facultad_para_carrera(codigo)
        ],
        "puede_gestionar_unidad": gestor_unidad,
        # Con quién se relaciona: dónde funciona, de dónde le llega la materia prima, quién analiza sus muestras.
        "relaciones_unidad": relaciones_de(unidad),
        # Los Centros I+D que integran esta unidad (su vertical expone nombres y enlaces, no sus modelos).
        "centros_id_integran": centros_id_que_integran(unidad.slug),
        # Quien coordina agrega al menú secciones nuevas con plantilla, en la pestaña que elija.
        "nueva_seccion_url": (reverse("nueva_seccion_propia", args=[unidad.slug])
                              if puede_editar_secciones(request.user, unidad) else ""),
        "ediciones": ediciones,
        "subir_archivo_url": (reverse("admin:recursos_recurso_add")
                              if request.user.has_perm("recursos.add_recurso") else ""),
    }
    response = render(
        request,
        "portal/pages/unidades/detalle/detalle_unidad.html",
        contexto,
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response
