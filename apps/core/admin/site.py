"""Organización visual del administrador institucional."""

from functools import lru_cache
from types import MethodType

from django.apps import apps
from django.contrib import admin
from django.urls import reverse
from django.utils.translation import gettext, gettext_lazy

from apps.core.presentation.tipologias import idioma_actual, tipologias_actuales
from apps.integraciones.unidades import FUNCIONES_DE_UNIDAD, modelos_de


# Registrados y accesibles por URL, pero sin sitio propio en el indice: cada
# tipo de unidad tiene ya su area y la lista combinada volveria a mezclarlas.
# A este conjunto se suman, en `fuera_del_indice`, los expedientes que cada
# tipo lista por su cuenta.
MODELOS_FUERA_DEL_INDICE = frozenset({
    "directorio_unidades.Unidad",
    # Se administran dentro del formulario de su unidad, donde se ve a quien
    # pertenece cada fila. Listarlos aparte mezcla otra vez todas las unidades
    # y obliga a adivinar. Siguen registrados: las URL y los selectores de
    # otros formularios los necesitan.
    "gestion_unidades.HorarioOperacionUnidad",
    "gestion_unidades.CapacidadOperativaUnidad",
    "gestion_unidades.BloqueoAgendaUnidad",
    "gestion_unidades.EspacioReservable",
    "recursos.ReglamentoUnidad",
    "recursos.ModuloUnidad",
    "gestion_unidades.ResponsableUnidad",
    "recursos.CarpetaRecurso",
    "recursos.Recurso",
    # Registro heredado de archivos sin unidad ni uso: los archivos viven en las carpetas de cada unidad.
    "recursos.ArchivoRecurso",
    # La bandeja ya tiene tarjeta explícita en Reportes e indicadores.
    "documentos.InformeMejora",
    # Las metas se editan en una sola tabla, «Metas del período», en Reportes e indicadores;
    # desde ella se abre este listado con el historial y las propuestas por capacidad.
    "documentos.ReferenciaIndicadorUnidad",
    # Consultas de formación: pertenecen al tablero de cada unidad y al curso.
    # Se conservan sus URL y permisos; no se mezclan identidades de todas las unidades en el índice.
    "formacion.CertificadoCurso",
    "formacion.ConfiguracionCertificadoCurso",
    "formacion.ParticipanteEvento",
})

# Areas transversales que preceden a los tipos de unidad.
_ANTES_DE_LOS_TIPOS = (
    {
        "slug": "formacion",
        "name": "Formación y simulación",
        "description": "Evidencias de las partidas, sus participantes y eventos; consulta de solo lectura con filtros por unidad.",
        "icon": "academic",
        "models": ("formacion.PartidaSimulador", "formacion.ParticipantePartida", "formacion.EventoPartida"),
    },
    {
        "slug": "institucion",
        "name": "Configuración institucional",
        "description": "Presentación pública y catálogos académicos con borradores e historial.",
        "icon": "settings",
        "models": ("configuracion_institucional.RevisionPresentacion",
                   "configuracion_institucional.RevisionCatalogoAcademico",
                   "configuracion_institucional.RevisionNivelesAcademicos",
                   "configuracion_institucional.RevisionPoliticaCalendario",
                   "configuracion_institucional.EstadoCapacidad",
                   "configuracion_institucional.CambioCapacidad"),
    },
    {
        "slug": "portal",
        "name": "Portal institucional",
        "description": "Contenido público por sección, con borradores, vista previa e historial.",
        "icon": "file",
        "models": ("portal.RevisionInicio",),
    },
)

# Tipos de unidad con area propia: vertical, modelo de unidad, icono y como se
# presenta. Lo que cada area contiene sale de las FUNCIONES que declara la
# vertical: mismos nombres de bloque entre tipos, datos solo del suyo.
TIPOS_EN_EL_INDICE = (
    ("laboratorios", "Laboratorio", "building",
     "Todo lo de los laboratorios y nada de otros tipos: agenda, prácticas, equipos, "
     "mantenimiento, insumos, servicios y trazabilidad."),
    ("plantas_piloto", "PlantaPiloto", "inventory",
     "Todo lo de las plantas piloto: agenda, prácticas, equipos, mantenimiento, insumos, "
     "producción, servicios y trazabilidad."),
    ("centros_experimentales", "CentroExperimental", "maintenance",
     "Todo lo de los centros experimentales: agenda, prácticas, equipos, mantenimiento, "
     "insumos y trazabilidad."),
    ("observatorios", "Observatorio", "reports",
     "Todo lo de los observatorios: agenda, prácticas, equipos, mantenimiento, insumos "
     "y trazabilidad."),
)

# Areas transversales que complementan a los tipos: no pertenecen a una unidad.
_DESPUES_DE_LOS_TIPOS = (
    {
        "slug": "centros_id",
        "name": "Centros de Investigación y Desarrollo",
        "description": "Cada centro con sus áreas (equipos y procesos), su equipo humano, sus proyectos y resultados, sus casos de éxito y aliados, su portafolio, sus solicitudes, sus convocatorias, noticias, documentos y carpetas de contenido.",
        "icon": "chart",
        "models": ("centros_id.CentroID", "centros_id.Componente", "centros_id.EquipoCentro", "centros_id.ProcesoArea",
                   "centros_id.Integrante", "centros_id.Grupo", "centros_id.Proyecto", "centros_id.Resultado",
                   "centros_id.CasoExito", "centros_id.Aliado", "centros_id.Servicio", "centros_id.SolicitudCentro",
                   "centros_id.Convocatoria", "centros_id.Novedad", "centros_id.DocumentoCentro",
                   "centros_id.CarpetaCentro", "centros_id.Zona", "centros_id.HerramientaCentro",
                   "centros_id.HorarioRecurso", "centros_id.BloqueoRecurso",
                   "centros_id.HabilitacionEquipo", "centros_id.LineaInvestigacion"),
    },
    {
        # Un solo sitio para todos los reportes del administrador. Son vistas
        # propias, no modelos: se declaran como enlaces y se muestran segun el
        # permiso de lectura del expediente que resumen.
        "slug": "reportes",
        "name": "Reportes e indicadores",
        "description": "Dos módulos independientes: Unidades y Centros I+D. Cada columna reúne su reporte principal y sus accesos de seguimiento.",
        "icon": "reports",
        # La auditoría del uso de los equipos y su redistribución entre unidades, junto al equipamiento por familia.
        "models": (
            "recursos.AlertaUsoEquipo",
            "recursos.TraspasoEquipo",
        ),
        "enlaces": (
            {
                "nombre": "Transparencia en el uso de equipos",
                "descripcion": "Consulta el uso acreditado de cada activo, los cierres pendientes y las alertas que requieren atención.",
                "ruta": "admin:recursos_unidadequipo_transparencia",
                "permiso": "recursos.view_unidadequipo",
            },
            {
                "nombre": "Reportes de Centros I+D",
                "descripcion": "Consulta los proyectos, la producción científica, la transferencia y la actividad de los centros de investigación y desarrollo.",
                "ruta": "reportes_centros_id",
                "acceso_centros": True,
            },
            {
                "nombre": "Reporte institucional",
                "descripcion": "Resume la actividad, atención, producción e ingresos de las unidades durante el período.",
                "ruta": "admin:reportes-institucional",
                "permiso": "gestion_unidades.view_reporteoperativounidad",
            },
            {
                "nombre": "Reportes operativos por unidad",
                "descripcion": "Consulta la condición actual de los equipos, las incidencias, el mantenimiento y los consumibles críticos.",
                "ruta": "admin:gestion_unidades_reporteoperativounidad_changelist",
                "permiso": "gestion_unidades.view_reporteoperativounidad",
            },
            {
                "nombre": "Expedientes de las unidades",
                "descripcion": "Selecciona una unidad para consultar sus documentos y entregas.",
                "ruta": "admin:reportes-evidencias-por-tipo",
                "permiso": "gestion_unidades.view_reporteoperativounidad",
                "solo_sin_expediente": True,
            },
            {
                "nombre": "Cumplimiento del expediente por unidad",
                "descripcion": "Revisa cada unidad, sus documentos y resultados. Dirección aprueba o devuelve las entregas desde esta pantalla.",
                "ruta": "admin:reportes-cumplimiento-expediente",
                "permiso": "documentos.view_documentoexpediente",
            },
            {
                "nombre": "Metas del período",
                "descripcion": "Define la meta de cada indicador por tipo de unidad: una sola tabla, editable. "
                               "Los planes que aún no se envían toman el valor nuevo.",
                "ruta": "admin:metas-del-periodo",
                "permiso": "documentos.change_referenciaindicadorunidad",
            },
            {
                "nombre": "Resumen anual de entregas",
                "descripcion": "Compara las entregas de los períodos A y B y los documentos del año; entra a Cumplimiento para evaluarlas.",
                "ruta": "admin:reportes-expediente-por-tipo",
                "permiso": "documentos.view_documentoexpediente",
            },
            {
                'nombre': 'Necesidades de compras por centro de costo',
                'descripcion': 'Revisa las necesidades de las unidades y remite el informe y el Excel al Decanato o dependencia que gestiona las compras.',
                'ruta': 'admin:reportes-necesidades-decanato',
                'acceso_necesidades': True,
            },
            {
                "nombre": "Remisión y seguimiento de mejora",
                "descripcion": "Da seguimiento a los informes de mejora remitidos y a sus acciones, responsables y plazos.",
                "ruta": "admin:documentos_informemejora_changelist",
                "permiso": "documentos.view_documentoexpediente",
            },
            {
                "nombre": "Estadísticas de reservas",
                "descripcion": "Compara las reservas por estado, unidad y fecha para conocer su demanda.",
                "ruta": "admin:reservas-estadisticas",
                "permiso": "reservas.view_reserva",
            },
            {
                "nombre": "Reporte de uso por carreras y usuarios",
                "descripcion": "Identifica quién utiliza las unidades y desde qué carrera o programa, según las solicitudes registradas.",
                "ruta": "admin:reservas-reporte-uso",
                "permiso": "reservas.view_reserva",
            },
            {
                "nombre": "Listado de solicitudes de reserva",
                "descripcion": "Consulta las solicitudes individuales y sus filtros; permite obtener el listado en PDF.",
                "ruta": "admin:reservas-reporte-listado",
                "permiso": "reservas.view_reserva",
            },
            {
                "nombre": "Equipamiento institucional",
                "descripcion": "Compara equipos por familia: cuántos hay, dónde están y cuánto se utilizan para valorar recursos compartidos antes de comprar.",
                "ruta": "equipamiento_institucional",
                "permiso": "recursos.view_unidadequipo",
            },
            {
                "nombre": "Lector de equipos",
                "descripcion": "Busca un equipo mediante su etiqueta de bodega o código QR y abre su ficha.",
                "ruta": "lector_equipos",
                "permiso": "recursos.view_unidadequipo",
            },
        ),
    },
    {
        "slug": "calendario-academico",
        "name": "Calendario académico",
        "description": "Períodos, semanas lectivas y versiones del calendario institucional.",
        "icon": "academic",
        "models": (
            "core.PeriodoAcademico",
            "core.VersionCalendarioAcademico",
            "core.SemanaAcademica",
            "core.VinculacionUsuarioPeriodo",
        ),
    },
    {
        "slug": "usuarios",
        "name": "Usuarios, responsables y acceso",
        "description": "Cuentas, perfiles, equipos humanos y permisos institucionales.",
        "icon": "users",
        "grupos": (
            {"name": "1. Cuentas y administradores de unidad",
             "description": "Crea la cuenta y selecciona una unidad sin administrador para asignar su gesti\u00f3n autom\u00e1ticamente. Para reasignar una unidad, abre su ficha.",
             "models": ("auth.User", "core.UserProfile")},
            {"name": "2. Identidad y auditor\u00eda institucional",
             "description": "Revisa tipo de usuario, pertenencia y correo. La verificaci\u00f3n de identidad no otorga permisos de gesti\u00f3n.",
             "models": ("core.VerificacionInstitucional", "account.EmailAddress")},
            {"name": "3. Autoridades y dependencias",
             "description": "Define qui\u00e9n recibe y consulta los informes institucionales y qui\u00e9n tiene designada cada funci\u00f3n de seguimiento.",
             "models": ("core.Decanato", "directorio_unidades.DependenciaAcademica", "core.AsignacionGobernanza")},
            {"name": "4. Configuraci\u00f3n t\u00e9cnica de acceso",
             "description": "Grupos y conexiones de inicio de sesi\u00f3n. No se necesitan para dar acceso a un administrador de unidad.",
             "models": ("auth.Group", "socialaccount.SocialAccount", "socialaccount.SocialApp", "socialaccount.SocialToken")},
        ),
    },
    {
        "slug": "soporte-tecnico",
        "name": "Soporte técnico de equipos",
        "description": "Diagnósticos por unidad y servicios compartidos de reparación.",
        "icon": "maintenance",
        "models": ("recursos.DiagnosticoIncidenciaEquipo", "recursos.ServicioReparacionEquipo"),
    },
    {
        "slug": "catalogos",
        "name": "Catálogos institucionales",
        "description": "Clasificaciones compartidas y parámetros de organización.",
        "icon": "catalog",
        "models": (
            "configuracion_institucional.TipologiaUnidad",
            "directorio_unidades.Categoria",
            "directorio_unidades.TipoLaboratorio",
            "sites.Site",
            "recursos.CategoriaEquipo",
            "recursos.FamiliaEquipo",
            "documentos.DocumentoExigido",
            # El mínimo con el que se mide a todas las unidades va junto al catálogo
            # que dice qué se les exige: las dos cosas son la regla del expediente.
            "documentos.PoliticaDeCalidad",
            "recursos.PoliticaUsoEquipo",
            # Dónde está cada sede: el mapa de ubicación de las unidades las resalta.
            "directorio_unidades.SedeInstitucional",
            # Las bases y fuentes de datos son comunes a todos los observatorios: el INEC alimenta a varios.
            "observacion.FuenteDatos",
        ),
    },
)


def _area_de_tipo(app_label, modelo_unidad, icono, descripcion):
    """Area de un tipo de unidad: su lista de unidades y un bloque por funcion."""
    config = apps.get_app_config(app_label)
    unidad = config.get_model(modelo_unidad)
    # Los tipos de unidad se administran una sola vez, en Catálogos institucionales.
    grupos = [{
        "name": "Fichas de unidad",
        "icon": "building",
        "description": "Abre una unidad para administrar todo lo suyo: horarios, espacios, "
                       "aforo, cierres, reglamento, responsables y contenido.",
        "models": (f"{app_label}.{modelo_unidad}",),
    }]
    for clave in config.models_module.FUNCIONES:
        funcion = FUNCIONES_DE_UNIDAD[clave]
        grupos.append({
            "name": funcion.nombre,
            "icon": funcion.icono,
            "description": funcion.descripcion,
            "models": tuple(f"{app_label}.{nombre}" for nombre in modelos_de(funcion)),
        })
    return {
        "slug": app_label,
        "name": str(unidad._meta.verbose_name_plural),
        "description": descripcion,
        "icon": icono,
        "grupos": tuple(grupos),
        "base_tipologia": admin.site._registry[unidad].base_tipologia,
        "modelo_unidad": unidad,
    }


def _cuenta_de_unidades(unidades, modelo_unidad):
    """«13 laboratorios», «1 observatorio»: lo que el menú dice de un área que entra por unidad."""
    if unidades is None:
        return ""
    nombre = modelo_unidad._meta.verbose_name if len(unidades) == 1 else modelo_unidad._meta.verbose_name_plural
    return f"{len(unidades)} {str(nombre).lower()}"


def _enlaces_visibles(request, enlaces):
    """Tarjetas de vistas propias (reportes), con la forma de una tarjeta de modelo."""
    # Alguna auditoria arma la lista con una peticion sin usuario: sin usuario, sin enlaces.
    usuario = getattr(request, "user", None)

    def autorizado(enlace):
        if usuario is None:
            return False
        if enlace.get('solo_sin_expediente') and usuario.has_perm('documentos.view_documentoexpediente'):
            return False
        if enlace.get("acceso_centros"):
            from apps.centros_id.informes import puede_reportar_centros
            return puede_reportar_centros(usuario)
        if enlace.get('acceso_necesidades'):
            return bool(usuario.is_active and usuario.is_staff and (usuario.is_superuser
                or usuario.dependencias_que_recibe.filter(activa=True).exists()))
        return usuario.has_perm(enlace["permiso"])

    return [{
        "name": gettext(enlace["nombre"]),
        "object_name": enlace["ruta"].split(":")[-1],
        "admin_url": reverse(enlace["ruta"]),
        "add_url": None,
        "descripcion": gettext(enlace["descripcion"]),
        "perms": {"view": True},
    } for enlace in enlaces if autorizado(enlace)]


def _publicacion_del_tipo(request, base):
    """Casilla por tipologia del area: publicada o retirada del publico.

    Solo para quien puede editar tipologias; los demas no ven la casilla.
    """
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.has_perm("configuracion_institucional.change_tipologiaunidad"):
        return []
    idioma = idioma_actual()
    return [{
        "codigo": tipologia.codigo,
        "nombre": tipologia.etiqueta(idioma, plural=True),
        "activa": tipologia.activa,
        "url": reverse("admin:configuracion_institucional_tipologiaunidad_publicacion",
                       args=[tipologia.codigo]),
    } for tipologia in tipologias_actuales() if tipologia.base == base]


@lru_cache(maxsize=None)
def categorias_admin():
    """Orden de lectura del indice: transversales, un area por tipo, complementos."""
    return (*_ANTES_DE_LOS_TIPOS,
            *(_area_de_tipo(*tipo) for tipo in TIPOS_EN_EL_INDICE),
            *_DESPUES_DE_LOS_TIPOS)


@lru_cache(maxsize=None)
def fuera_del_indice():
    """Los expedientes heredados salen del indice: cada tipo lista los suyos."""
    from apps.integraciones.propiedad_modelos import PROPIETARIOS_MODELOS
    heredados = {f"{PROPIETARIOS_MODELOS[nombre]}.{nombre}" for funcion in FUNCIONES_DE_UNIDAD.values()
                 for nombre in modelos_de(funcion)}
    return MODELOS_FUERA_DEL_INDICE | heredados


def _lista_aplicaciones_agrupada(self, request, app_label=None):
    """Agrupa el índice sin alterar las URLs ni los ModelAdmin registrados."""
    aplicaciones = self._citt_original_get_app_list(request, app_label)
    for aplicacion in aplicaciones:
        for modelo in aplicacion["models"]:
            modelo["name"] = gettext(str(modelo["name"]))
    if app_label:
        return aplicaciones

    modelos_visibles = {}
    for aplicacion in aplicaciones:
        for modelo in aplicacion["models"]:
            clave = f'{aplicacion["app_label"]}.{modelo["object_name"]}'
            ayudas = {
                'auth.User': ('Cuentas y administradores de unidad', 'Crear cuentas, asignar una unidad y auditar su alcance, estado y acceso reciente.'),
                'core.UserProfile': ('Datos y tipo de usuario', 'Identidad, contacto y clasificaci\u00f3n del usuario; no concede privilegios administrativos.'),
                'core.VerificacionInstitucional': ('Historial de verificaciones', 'Decisiones, evidencia, revisor y vigencia de la pertenencia institucional.'),
                'account.EmailAddress': ('Correos y verificaci\u00f3n', 'Direcciones vinculadas a las cuentas y estado de verificaci\u00f3n del correo.'),
                'auth.Group': ('Grupos de permisos institucionales', 'Permisos globales avanzados. Las unidades usan su propia asignaci\u00f3n y delegaciones.'),
                'socialaccount.SocialAccount': ('Conexiones Google / Microsoft', 'Cuentas externas vinculadas al inicio de sesi\u00f3n.'),
                'socialaccount.SocialApp': ('Proveedores de inicio de sesi\u00f3n', 'Configuraci\u00f3n t\u00e9cnica de los proveedores externos.'),
                'socialaccount.SocialToken': ('Credenciales de proveedores', 'Tokens t\u00e9cnicos de las conexiones externas; no son roles ni cuentas de unidad.'),
            }
            if clave in ayudas:
                modelo['name'], modelo['descripcion'] = ayudas[clave]
            modelos_visibles[clave] = modelo

    # La ficha ya está en la entrada de cada unidad: no repetirla por tipología.
    from apps.gestion_unidades.admin.autonomia import areas_operativas
    areas_unidad = areas_operativas(request)
    if areas_unidad:
        from apps.directorio_unidades.admin.unidades import UnidadAdmin
        fichas = {f'{modelo._meta.app_label}.{modelo.__name__}'
                  for modelo, administrador in self._registry.items()
                  if isinstance(administrador, UnidadAdmin)}
        modelos_visibles = {clave: modelo for clave, modelo in modelos_visibles.items()
                            if clave not in fichas}

    # Cada herramienta dice qué es en una frase, en cualquier área.
    from apps.gestion_unidades.admin.tablero_unidad import DESCRIPCIONES
    modelos_visibles = {clave: {**modelo, "descripcion": modelo.get("descripcion")
                                or DESCRIPCIONES.get(modelo["object_name"], "")}
                        for clave, modelo in modelos_visibles.items()}
    resultado = []
    clasificados = set()
    # Se resuelve una vez por peticion: tres bucles lo consultan.
    for categoria in categorias_admin():
        # Una categoria declara sus modelos en una lista o repartidos en
        # grupos; el orden de los grupos es el orden de lectura del area.
        declarados = categoria.get("models") or tuple(
            clave for grupo in categoria.get("grupos", ()) for clave in grupo["models"]
        )
        modelos = [
            modelos_visibles[clave]
            for clave in declarados
            if clave in modelos_visibles and clave not in fuera_del_indice()
        ] + _enlaces_visibles(request, categoria.get("enlaces", ()))
        if not modelos:
            continue
        clasificados.update(declarados)
        grupos = [
            {
                "name": gettext(grupo["name"]),
                "icon": grupo.get("icon", categoria["icon"]),
                "description": gettext(grupo.get("description", "")),
                "models": [modelos_visibles[clave] for clave in grupo["models"]
                           if clave in modelos_visibles
                           and clave not in fuera_del_indice()],
            }
            for grupo in categoria.get("grupos", ())
        ]
        unidades = None
        lista_unidades = None
        modelo_unidad = categoria.get("modelo_unidad")
        if modelo_unidad is not None:
            # Se entra por unidad: su tablero reúne lo suyo con cada lista ya filtrada. Del área
            # solo queda lo que es de todas, su lista y el alta de otra, en la cabecera.
            from apps.gestion_unidades.admin.tablero_unidad import resumen_de_unidades
            unidades = resumen_de_unidades(request, self._registry[modelo_unidad])
            lista_unidades = modelos_visibles.get(f"{categoria['slug']}.{modelo_unidad.__name__}")
        menu_reportes = None
        if categoria['slug'] == 'reportes':
            from .reportes_menu import organizar_reportes
            menu_reportes = organizar_reportes(modelos)
        resultado.append({
            "menu_reportes": menu_reportes,
            "unidades": unidades,
            "lista_unidades": lista_unidades,
            "unidad_singular": str(modelo_unidad._meta.verbose_name) if modelo_unidad else "",
            "rotulo_unidades": _cuenta_de_unidades(unidades, modelo_unidad),
            "publicacion": _publicacion_del_tipo(request, categoria["base_tipologia"])
            if categoria.get("base_tipologia") else [],
            "grupos": [grupo for grupo in grupos if grupo["models"]],
            "name": gettext(categoria["name"]),
            "app_label": categoria["slug"],
            "app_url": f'#{categoria["slug"]}',
            "has_module_perms": True,
            "models": modelos,
            "description": gettext(categoria["description"]),
            "icon": categoria["icon"],
            "slug": categoria["slug"],
        })

    otros = [
        modelo
        for clave, modelo in modelos_visibles.items()
        if clave not in clasificados and clave not in fuera_del_indice()
    ]
    if otros:
        resultado.append({
            "name": gettext("Configuración complementaria"),
            "app_label": "configuracion",
            "app_url": "#configuracion",
            "has_module_perms": True,
            "models": otros,
            "description": gettext("Registros auxiliares disponibles según los permisos del usuario."),
            "icon": "settings",
            "slug": "configuracion",
        })
    # Los expedientes del tipo se integran en la misma área de la unidad.
    # Así cada herramienta conserva su formulario completo sin repetir menús.
    if areas_unidad:
        from apps.gestion_unidades.admin.acceso import unidades_editables
        from apps.integraciones.admin.por_tipo import AcotadoPorTipologia
        for area in areas_unidad:
            unidad_id = int(area['slug'].removeprefix('mi_unidad_'))
            unidad = unidades_editables(request.user).get(pk=unidad_id)
            grupos = [{'name': 'Unidad', 'models': area['models'], 'description': ''}]
            for categoria in resultado:
                for grupo in categoria.get('grupos', []):
                    tarjetas = []
                    for tarjeta in grupo['models']:
                        candidatos = [a for m, a in self._registry.items()
                                      if m.__name__ == tarjeta['object_name']
                                      and m._meta.app_label == categoria['slug']
                                      and isinstance(a, AcotadoPorTipologia)]
                        if not candidatos or unidad.dependencia not in candidatos[0].codigos():
                            continue
                        administrador = candidatos[0]
                        copia = dict(tarjeta)
                        copia['admin_url'] += f'?{administrador.parametro_unidad}={unidad.pk}'
                        tarjetas.append(copia)
                    if tarjetas:
                        grupos.append({**grupo, 'models': tarjetas})
            area['grupos'] = grupos
            area['models'] = [modelo for grupo in grupos for modelo in grupo['models']]
        tipos = {m._meta.app_label for m, a in self._registry.items()
                 if isinstance(a, AcotadoPorTipologia)}
        resultado = [area for area in resultado
                     if area['slug'] not in tipos]
    return resultado + areas_unidad


def configurar_sitio_admin():
    """Aplica identidad y agrupación una sola vez al AdminSite predeterminado."""
    from apps.core.presentation.identidad import identidad_actual
    from django.utils.functional import lazy
    from apps.gestion_unidades.admin.acceso import acceso_admin, indice_admin, permiso_entrada_admin

    admin.site.login = acceso_admin
    admin.site.has_permission = permiso_entrada_admin
    if not getattr(admin.site, '_indice_unidad_configurado', False):
        admin.site.index = indice_admin(admin.site.index)
        admin.site._indice_unidad_configurado = True

    admin.site.site_header = lazy(lambda: f"{gettext('Administración')} · {identidad_actual()[0].nombre_corto}", str)()
    admin.site.site_title = lazy(lambda: f"{gettext('Administración')} {identidad_actual()[1].siglas}", str)()
    admin.site.index_title = gettext_lazy("Centro de administración")
    if not hasattr(admin.site, "_citt_original_get_app_list"):
        admin.site._citt_original_get_app_list = admin.site.get_app_list
        admin.site.get_app_list = MethodType(
            _lista_aplicaciones_agrupada,
            admin.site,
        )
