"""Endpoints de creación y consulta del asistente único de reservas."""

from apps.core.presentation.identidad import identidad_actual
from apps.core.presentation.regional import validar_intervalo_institucional

import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from math import ceil
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.formacion.models.asignaturas import Asignatura
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.core.models.periodos import PeriodoAcademico
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile
from apps.gestion_unidades.models.operaciones import ventana_atencion
from apps.reservas.workflows.reservas import ESTADOS_CERRADOS, ESTADOS_OCUPAN_AGENDA, REGLAS_TRANSICION

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.creacion_entrada import normalizar_entrada_basica, normalizar_intervalo, resolver_seleccion_proceso
from apps.reservas.presentation.creacion_recursos import resolver_catalogos_solicitud, resolver_recursos_fisicos, validar_catalogo_consumibles_servicios
from apps.reservas.presentation.creacion_servicio import parametros_trabajo_servicio, preparar_solicitud
from apps.reservas.presentation.creacion_transaccion import ComandoCreacionReserva, crear_expediente_reserva
from apps.reservas.presentation.cronograma import fechas_de_programacion, normalizar_cronograma, recursos_de_sesion
from apps.reservas.presentation.solicitudes_propias import cancelar_reserva_propia
from apps.gestion_unidades.presentation.permisos import puede_administrar_personal_unidad, puede_operar_modulo_unidad
from apps.reservas.presentation.seguridad import pendientes_al_reservar
from apps.reservas.presentation.horarios import jornadas_habilitadas as _jornadas_habilitadas, validar_horario_operativo as _validar_horario_operativo
from apps.formacion.presentation.practicas_integracion import estado_documental_reserva, guias_vencidas_sin_enviar
from apps.reservas.presentation.cotizaciones import calcular_cotizacion, normalizar_cantidades_servicio, validar_cantidades_servicio
from apps.reservas.presentation.forms import GuiaPracticaForm
from apps.reservas.presentation.participantes import datos_usuario_para_periodo as _datos_usuario_para_periodo, validar_participantes as _validar_participantes
from apps.reservas.presentation.guia_automatizacion import politicas_guia_desde_reserva
from apps.reservas.presentation.guia_contenido import adjuntar_figuras_borrador, figuras_permitidas, guardar_imagenes_guia, validar_imagenes_guia
from apps.reservas.presentation.guia_firmas import firmar_contenido_guia, normalizar_firmas
from apps.reservas.presentation.guias import puede_editar_guia
from apps.reservas.presentation.guia_contrato import GUIA_INTEGRADA_CAMPOS, GUIA_INTEGRADA_OBLIGATORIOS
from apps.reservas.presentation.guia_html import CAMPOS_RICOS, FORMATO_HTML, esta_vacio
from apps.reservas.presentation.comprobantes import texto_cancelacion
from apps.reservas.presentation.seguimiento import linea_tiempo_reserva
from apps.reservas.presentation.conflictos import validar_conflictos_recursos
from apps.reservas.presentation.periodos import resolver_periodo_reserva


def _respuesta_error(mensaje, status=400):
    return JsonResponse({"success": False, "error": gettext(mensaje)}, status=status)


def _requiere_guia_integrada(tipo_solicitud, proposito_codigo, contexto_actividad):
    return bool(
        tipo_solicitud != "servicio"
        and proposito_codigo == "docencia_practica"
        and contexto_actividad.get("vinculacion_actividad") in {"manual", "clonada"}
    )


def _validar_guia_integrada(request, *, requerida):
    """Valida la guía antes de crear cualquier reserva o actividad asociada."""
    if not requerida:
        return
    confirmada = request.POST.get("guia_confirmada_solicitante", "").lower() in {
        "1", "true", "on", "si", "sí",
    }
    if not confirmada:
        raise ValueError(
            "Revisa la vista previa de la guía y confirma su contenido antes de enviar"
        )
    faltantes = []
    es_html = request.POST.get("guia_formato_contenido", "") == FORMATO_HTML
    for campo, etiqueta in GUIA_INTEGRADA_OBLIGATORIOS.items():
        valor = request.POST.get(f"guia_{campo}", "").strip()
        # Del editor visual puede llegar solo etiquetas vacias ("<p></p>").
        if not valor or (es_html and campo in CAMPOS_RICOS and esta_vacio(valor)):
            faltantes.append(etiqueta)
    if faltantes:
        raise ValueError(
            "Completa la guía de práctica antes de enviar: " + ", ".join(faltantes)
        )
    validar_imagenes_guia(request.FILES.getlist("guia_imagenes"))


def _errores_formulario_en_texto(form):
    mensajes = []
    for campo, errores in form.errors.items():
        etiqueta = form.fields.get(campo).label if campo in form.fields else "Guía"
        mensajes.extend(f"{etiqueta}: {error}" for error in errores)
    return "; ".join(mensajes)


def _completar_guia_integrada(request, *, guia, reserva):
    """Completa el formato institucional desde la solicitud y lo envía a revisión."""
    datos = {
        "actividad_existente": str(reserva.actividad_catalogo_id),
        "reserva_referencia": str(reserva.pk),
        "descripcion_actividad": reserva.actividad_catalogo.descripcion,
        "permite_descarga": request.POST.get("guia_permite_descarga", ""),
        "solicita_publicacion": request.POST.get("guia_solicitar_publicacion", ""),
    }
    for campo in GUIA_INTEGRADA_CAMPOS:
        datos[campo] = request.POST.get(f"guia_{campo}", "").strip()
    datos["formato_procedimiento"] = datos["formato_procedimiento"] or "numerado"
    datos["formato_contenido"] = request.POST.get("guia_formato_contenido", "").strip()
    # Figuras cargadas desde el editor antes de existir la guia.
    token_borrador = request.POST.get("guia_imagenes_token", "").strip()[:40]
    adjuntar_figuras_borrador(guia, token_borrador, request.user)
    # Reactivos, materiales y manejo de residuos pertenecen al inventario y a
    # las políticas verificadas de la unidad; el autor no los vuelve a digitar.
    politicas = politicas_guia_desde_reserva(reserva)
    if datos["formato_contenido"] != FORMATO_HTML:
        # Formato de texto: la politica de la unidad encabeza el apartado.
        # En el formato HTML el formulario la guarda aparte
        # (seguridad_institucional) y la zona conserva solo lo del autor.
        precauciones_especificas = datos.get("medidas_seguridad", "")
        datos["medidas_seguridad"] = "\n".join(
            [*politicas["seguridad"], *(
                linea.strip()
                for linea in precauciones_especificas.splitlines()
                if linea.strip()
            )]
        )
    datos["manejo_residuos"] = "\n".join(politicas["manejo_residuos"])
    datos["reactivos"] = ""

    form = GuiaPracticaForm(
        datos,
        unidad=reserva.laboratorio,
        usuario=request.user,
        guia=guia,
        figuras_permitidas=figuras_permitidas(guia, "", request.user),
    )
    if not form.is_valid():
        raise ValueError(
            "La guía contiene datos no válidos: " + _errores_formulario_en_texto(form)
        )

    anteriores = {
        "estado_publicacion": guia.estado_publicacion,
        "contenido": guia.contenido,
    }
    guia.titulo = form.cleaned_data["titulo"]
    guia.codigo_guia = form.cleaned_data.get("codigo_guia", "")
    guia.descripcion = form.cleaned_data.get("descripcion_actividad", "")
    guia.contenido = form.contenido_normalizado()
    # Quien elabora firma siempre; revisión y aprobación solo si el autor las incluyó.
    guia.contenido["firmas"] = normalizar_firmas(request.POST.get("guia_firmas", ""))
    guia.permite_descarga = form.cleaned_data.get("permite_descarga", False)
    guia.solicita_publicacion = form.cleaned_data.get("solicita_publicacion", False)
    faltantes = guia.secciones_faltantes()
    if faltantes:
        raise ValueError(
            "No fue posible completar la guía: " + ", ".join(faltantes)
        )
    guia.contenido = firmar_contenido_guia(
        guia.contenido,
        guia=guia,
        usuario=request.user,
        reserva=reserva,
    )
    guia.estado_publicacion = "revision"
    guia.observaciones_revision = ""
    guia.full_clean()
    guia.save()
    guardar_imagenes_guia(
        guia,
        request.FILES.getlist("guia_imagenes"),
        request.POST.getlist("guia_imagenes_titulos"),
    )

    actividad = reserva.actividad_catalogo
    actividad.estado_publicacion = "revision"
    actividad.save(update_fields=["estado_publicacion", "actualizado_en"])
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="enviar",
        objeto=guia,
        descripcion=(
            f"Guía v{guia.numero_version} completada dentro de la solicitud "
            f"{reserva.codigo_reserva or reserva.pk} y enviada a revisión."
        ),
        anteriores=anteriores,
        nuevos={
            "estado_publicacion": guia.estado_publicacion,
            "contenido": guia.contenido,
        },
    )
    return guia


def _perfil_valido_para_reserva(usuario):
    perfil = getattr(usuario, "profile", None)
    if not perfil:
        raise ValueError("Completa tu perfil institucional antes de realizar una solicitud")
    faltantes = perfil.campos_faltantes_reserva()
    if faltantes:
        raise ValueError(
            "Completa tu perfil antes de continuar. Faltan: " + ", ".join(faltantes)
        )
    return perfil


def _puede_crear_guia(usuario, laboratorio):
    from apps.gestion_unidades.presentation.permisos import puede_crear_guias_unidad

    return puede_crear_guias_unidad(usuario, laboratorio)


def _validar_contexto_actividad(
    request,
    laboratorio,
    perfil,
    proposito_codigo,
    *,
    tipo_solicitud="recursos",
    validacion_completa=True,
):
    """Valida las dimensiones institucionales necesarias para indicadores."""
    permitidos = Reserva.SUBTIPOS_POR_PROPOSITO[proposito_codigo]
    subtipo = (
        request.POST.get('subtipo_actividad')
        or Reserva.SUBTIPO_PREDETERMINADO[proposito_codigo]
    )
    if subtipo not in permitidos:
        raise ValueError('Selecciona un tipo de actividad compatible con el propósito')

    alcances = dict(Reserva.ALCANCE_BENEFICIARIO_CHOICES)
    alcance = request.POST.get('alcance_beneficiario') or 'perfil_solicitante'
    if alcance not in alcances:
        raise ValueError('Selecciona para quién se realizará la actividad')

    facultad = ''
    carrera = ''
    entidad = ''
    if alcance == 'perfil_solicitante':
        facultad = perfil.facultad or ''
        carrera = perfil.carrera or ''
        entidad = perfil.institucion or identidad_actual()[1].siglas
    elif alcance == 'otra_carrera':
        carrera = request.POST.get('carrera_beneficiaria', '').strip()
        facultad = UserProfile.facultad_para_carrera(carrera)
        if not facultad:
            raise ValueError('Selecciona la carrera institucional beneficiaria de la actividad')
        entidad = identidad_actual()[1].siglas
    else:
        entidad = request.POST.get('entidad_beneficiaria', '').strip()
        if not entidad:
            raise ValueError(
                'Identifica la dependencia, proyecto, centro, institución o comunidad beneficiaria'
            )
        if alcance == 'externo':
            facultad = 'externo'

    es_servicio = tipo_solicitud == "servicio"
    actividad_id = '' if es_servicio else request.POST.get('actividad_catalogo', '').strip()
    referencia_manual = '' if es_servicio else request.POST.get('referencia_actividad', '').strip()
    vinculacion = 'no_aplica' if es_servicio else request.POST.get(
        'vinculacion_actividad', ''
    ).strip()
    vinculaciones = dict(Reserva.VINCULACION_ACTIVIDAD_CHOICES)
    if not vinculacion:
        # Compatibilidad con formularios anteriores y clientes de la API.
        if actividad_id:
            vinculacion = 'catalogo'
        elif referencia_manual:
            vinculacion = 'manual'
        elif validacion_completa and proposito_codigo in {
            'servicio_cientifico_tecnologico', 'otro',
        }:
            vinculacion = 'no_aplica'
        else:
            vinculacion = 'no_aplica'
    if vinculacion not in vinculaciones:
        raise ValueError('Indica si la reserva pertenece a una actividad formal')

    actividad = None
    if vinculacion in {'catalogo', 'clonada'} and actividad_id:
        actividades_permitidas = CatalogoActividadReserva.objects.filter(
            activo=True,
            proposito_codigo=proposito_codigo,
        )
        if not puede_operar_modulo_unidad(request.user, laboratorio, 'practicas'):
            actividades_permitidas = actividades_permitidas.filter(
                Q(estado_publicacion='publicado', visibilidad__in=['unidad', 'institucional'])
                | Q(creado_por=request.user)
                | Q(participantes_autorizados=request.user)
            ).distinct()
        try:
            actividad = actividades_permitidas.get(pk=int(actividad_id))
        except (CatalogoActividadReserva.DoesNotExist, TypeError, ValueError):
            raise ValueError('La actividad institucional seleccionada ya no está disponible')
        if actividad.unidad_id and actividad.unidad_id != laboratorio.pk:
            raise ValueError('La actividad institucional pertenece a otra unidad')
    elif vinculacion in {'catalogo', 'clonada'} and validacion_completa:
        raise ValueError('Selecciona una actividad publicada en el catálogo institucional')

    # Toda actividad docente (cualquier subtipo) requiere guia de practica.
    es_docencia = not es_servicio and proposito_codigo == 'docencia_practica'
    if es_docencia and vinculacion == 'independiente':
        raise ValueError(
            'Toda actividad docente debe vincular una guía institucional aprobada '
            'o crear una guía nueva con esta reserva'
        )
    if (
        proposito_codigo == 'docencia_practica'
        and vinculacion in {'manual', 'clonada'}
        and not _puede_crear_guia(request.user, laboratorio)
    ):
        raise ValueError(
            'Tu perfil no puede crear guías de práctica. Selecciona una guía '
            'institucional aprobada por un docente'
        )
    if es_docencia and vinculacion in {'catalogo', 'clonada'} and actividad:
        tiene_guia_aprobada = actividad.guias.filter(
            activo=True,
            estado_publicacion='publicada',
        ).exists()
        if not tiene_guia_aprobada:
            raise ValueError(
                'La actividad seleccionada no tiene una guía institucional aprobada y vigente'
            )

    if vinculacion in {'manual', 'clonada'} and validacion_completa and not referencia_manual:
        if proposito_codigo == 'docencia_practica':
            raise ValueError('Escribe un nombre corto para identificar la actividad o guía')
        raise ValueError('Escribe el nombre oficial del proyecto o actividad formal')
    if (
        vinculacion == 'manual'
        and proposito_codigo == 'docencia_practica'
        and len(referencia_manual) > 120
    ):
        raise ValueError(
            'El nombre de la práctica admite hasta 120 caracteres'
        )
    if (
        vinculacion == 'manual'
        and proposito_codigo == 'docencia_practica'
        and re.search(r'\[[^\]]*\]', referencia_manual)
    ):
        # El asistente ofrece patrones como "[Problema real]: [Técnica]".
        raise ValueError(
            'Reemplaza los corchetes del patrón por el contenido real de la práctica'
        )
    if (
        vinculacion == 'no_aplica'
        and validacion_completa
        and not es_servicio
        and proposito_codigo not in {'servicio_cientifico_tecnologico', 'otro'}
    ):
        raise ValueError(
            'Indica si usarás una actividad registrada, una referencia manual o un uso autónomo'
        )

    referencia = actividad.nombre if actividad and vinculacion == 'catalogo' else (
        referencia_manual if vinculacion == 'manual' else ''
    )
    if vinculacion == 'clonada' and actividad:
        referencia = referencia_manual or f'{actividad.nombre} adaptada'
    codigo_referencia = actividad.codigo if actividad and vinculacion == 'catalogo' else (
        request.POST.get('codigo_referencia_actividad', '').strip()
        if vinculacion in {'manual', 'clonada'} else ''
    )
    periodo = actividad.periodo_academico if actividad else request.POST.get(
        'periodo_academico', ''
    ).strip()
    responsable = actividad.responsable if actividad else (
        request.POST.get('responsable_actividad', '').strip()
        if vinculacion == 'manual' else ''
    )
    if vinculacion == 'manual' and not responsable and request.user.is_authenticated:
        responsable = request.user.get_full_name() or request.user.username

    origen = request.POST.get('origen_programacion', 'no_aplica')
    if es_servicio:
        origen = 'no_aplica'
    elif proposito_codigo == 'docencia_practica' and vinculacion == 'independiente':
        # Una reserva sin actividad formal, única o recurrente, no debe contarse
        # como una actividad docente adicional en los indicadores institucionales.
        origen = 'no_aplica'
    elif proposito_codigo == 'docencia_practica' and validacion_completa:
        if origen not in dict(Reserva.ORIGEN_PROGRAMACION_CHOICES) or origen == 'no_aplica':
            raise ValueError('Indica si la actividad docente fue programada o es adicional')
    else:
        origen = 'no_aplica'

    detalle_otro = request.POST.get('detalle_otro_proposito', '').strip()
    if validacion_completa and proposito_codigo == 'otro' and len(detalle_otro) < 10:
        raise ValueError('Explica brevemente el propósito institucional de la solicitud')

    if actividad:
        facultad = actividad.facultad or facultad
        carrera = actividad.carrera or carrera

    return {
        'subtipo_actividad': subtipo,
        'alcance_beneficiario': alcance,
        'facultad_beneficiaria': facultad,
        'carrera_beneficiaria': carrera,
        'entidad_beneficiaria': entidad,
        'vinculacion_actividad': vinculacion,
        'actividad_catalogo': actividad,
        'referencia_actividad': referencia,
        'codigo_referencia_actividad': codigo_referencia,
        'periodo_academico': periodo,
        'responsable_actividad': responsable,
        'origen_programacion': origen,
        'detalle_otro_proposito': detalle_otro,
    }


def _validar_guias_actividad(request, *, permite_carga, requerida=False):
    """Valida las guías de una actividad nueva sin mezclarlas con archivos técnicos."""
    archivos = request.FILES.getlist('guias_actividad')
    if archivos and not permite_carga:
        raise ValueError('Las guías solo pueden cargarse al registrar una actividad nueva')
    if requerida and not archivos:
        raise ValueError(
            'Adjunta al menos una guía PDF para registrar la actividad docente o práctica'
        )
    if len(archivos) > 10:
        raise ValueError('Puedes adjuntar un máximo de diez guías PDF por actividad')
    for archivo in archivos:
        if Path(archivo.name).suffix.lower() != '.pdf':
            raise ValueError(f'La guía {archivo.name} debe estar en formato PDF')
        if archivo.size > 20 * 1024 * 1024:
            raise ValueError(f'La guía {archivo.name} supera el máximo de 20 MB')
    return archivos


def _permisos_descarga_guias(request, cantidad):
    """Lee una decisión de descarga por PDF; ante datos ausentes protege el archivo."""
    try:
        valores = json.loads(request.POST.get('permisos_descarga_guias', '[]'))
    except (TypeError, ValueError, json.JSONDecodeError):
        valores = []
    if not isinstance(valores, list):
        valores = []
    return [indice < len(valores) and valores[indice] is True for indice in range(cantidad)]


def _fechas_de_programacion(request, primera_fecha, contexto_actividad, tipo_solicitud):
    """Construye las sesiones semanales concretas que alimentarán calendario y reportes."""
    return fechas_de_programacion(
        (request.POST.get('frecuencia_reserva') or 'unica').strip() or 'unica',
        primera_fecha,
        (request.POST.get('fecha_fin_recurrencia') or '').strip(),
        contexto_actividad,
        tipo_solicitud,
    )


def _recursos_para_validar(indice, recursos_por_sesion, recursos, software, espacios, incluye_espacio, alcance_espacio):
    """Lo que se valida en cada fecha: lo del proceso propio de la sesión o lo pedido en el asistente."""
    propios = recursos_por_sesion.get(indice)
    if propios is None:
        return recursos, software, espacios, incluye_espacio, alcance_espacio
    return propios['recursos'], propios['software'], propios['espacios'], True, 'areas'


def _nombres_recursos(
    equipos,
    software,
    incluye_espacio,
    laboratorio,
    espacios=(),
):
    nombres = [equipo.nombre for equipo in equipos]
    nombres.extend(programa.nombre for programa in software)
    nombres.extend(espacio.nombre for espacio in espacios)
    if incluye_espacio and not espacios:
        nombres.append(f"espacio de {laboratorio.nombre}")
    if not nombres:
        return "recursos por definir"
    if len(nombres) <= 3:
        return " + ".join(nombres)
    return " + ".join(nombres[:3]) + f" + {len(nombres) - 3} más"


def _generar_titulo(
    tipo_solicitud,
    proposito,
    equipos,
    software,
    servicios,
    laboratorio,
    *,
    incluye_espacio=False,
    modalidad_servicio="",
    espacios=(),
):
    if tipo_solicitud == "equipo":
        recurso = equipos[0].nombre if len(equipos) == 1 else "equipos del laboratorio"
        prefijo = "Reserva de equipo"
    elif tipo_solicitud == "software":
        recurso = software[0].nombre if len(software) == 1 else "software y licencias"
        prefijo = "Reserva de software"
    elif tipo_solicitud == "servicio":
        recurso = servicios[0].nombre if len(servicios) == 1 else "servicios técnicos"
        prefijo = "Solicitud de servicio"
        modalidad = dict(Reserva.MODALIDAD_SERVICIO_CHOICES).get(
            modalidad_servicio, "modalidad por definir"
        )
        if modalidad_servicio == "diseno_asistido":
            complementos = _nombres_recursos(
                equipos,
                software,
                incluye_espacio,
                laboratorio,
                espacios,
            )
            recurso = f"{recurso} · {modalidad} · {complementos}"
        else:
            recurso = f"{recurso} · {modalidad}"
    elif tipo_solicitud == "recursos":
        recurso = _nombres_recursos(
            equipos,
            software,
            incluye_espacio,
            laboratorio,
            espacios,
        )
        prefijo = "Solicitud de recursos"
    else:
        recurso = _nombres_recursos(
            equipos,
            software,
            incluye_espacio,
            laboratorio,
            espacios,
        )
        prefijo = "Reserva de espacio"
    return f"{prefijo}: {recurso} · {proposito}"[:255]


def _generar_descripcion(
    tipo_solicitud,
    proposito,
    equipos,
    software,
    servicios,
    laboratorio,
    *,
    incluye_espacio=False,
    modalidad_servicio="",
    espacios=(),
    intencion="",
):
    """Reconstruye una descripción trazable; la intención de la persona la complementa."""
    if tipo_solicitud == "servicio":
        nombres = ", ".join(servicio.nombre for servicio in servicios)
        modalidad = dict(Reserva.MODALIDAD_SERVICIO_CHOICES).get(
            modalidad_servicio, "Por definir"
        )
        texto = f"Servicio solicitado: {nombres}. Modalidad: {modalidad}. Propósito: {proposito}."
        if intencion:
            texto += f" Finalidad: {intencion}"
        if modalidad_servicio == "diseno_asistido":
            texto += (
                " Recursos complementarios para uso del solicitante: "
                + _nombres_recursos(
                    equipos,
                    software,
                    incluye_espacio,
                    laboratorio,
                    espacios,
                )
                + "."
            )
        return texto
    recursos = _nombres_recursos(
        equipos,
        software,
        incluye_espacio,
        laboratorio,
        espacios,
    )
    texto = f"Uso de recursos solicitado para {proposito}: {recursos}."
    if intencion:
        texto += f" Intención: {intencion}"
    return texto


@require_http_methods(["GET"])
@never_cache
def buscar_usuarios_reserva(request):
    """Busca participantes o cuentas activas con autorización de personal por unidad."""
    if not request.user.is_authenticated:
        return _respuesta_error("Usuario no autenticado", status=401)
    contexto = request.GET.get("contexto") or "participantes"
    if contexto not in {"participantes", "responsables", "visitas_internas"}:
        return _respuesta_error("El contexto de búsqueda no es válido", status=400)
    if contexto == 'visitas_internas' and getattr(getattr(request.user, 'profile', None), 'tipo_usuario', '') in {'', 'externo'}:
        return _respuesta_error('La búsqueda de visitantes internos requiere una cuenta institucional interna.', status=403)
    if contexto == "responsables":
        unidad = Unidad.objects.only("pk", "administrador_id").filter(
            slug=request.GET.get("unidad") or ""
        ).first()
        if unidad is None:
            return _respuesta_error("Unidad no encontrada", status=404)
        if not puede_administrar_personal_unidad(request.user, unidad):
            return _respuesta_error("No puedes administrar el personal de esta unidad", status=403)
        termino = (request.GET.get("q") or "").strip()[:120]
        if len(termino) < 2:
            return JsonResponse({"success": True, "usuarios": []})
        usuarios = get_user_model().objects.filter(is_active=True)
        for palabra in termino.split()[:8]:
            usuarios = usuarios.filter(
                Q(first_name__icontains=palabra)
                | Q(last_name__icontains=palabra)
                | Q(username__icontains=palabra)
                | Q(email__icontains=palabra)
            )
        filas = usuarios.order_by("first_name", "last_name", "username", "pk").values(
            "pk", "first_name", "last_name", "username", "email"
        )[:10]
        return JsonResponse({"success": True, "usuarios": [{
            "id": fila["pk"],
            "nombre": (fila["first_name"] + " " + fila["last_name"]).strip() or fila["username"],
            "usuario": fila["username"],
            "correo": fila["email"],
        } for fila in filas]})
    termino = (request.GET.get("q") or "").strip()
    if len(termino) < 2:
        return JsonResponse({"success": True, "usuarios": []})
    usuarios = get_user_model().objects.filter(is_active=True)
    if contexto == 'visitas_internas':
        usuarios = usuarios.exclude(profile__tipo_usuario__in=['', 'externo']).filter(profile__isnull=False)
    else:
        usuarios = usuarios.exclude(pk=request.user.pk)
    for palabra in termino.split():
        usuarios = usuarios.filter(
            Q(first_name__icontains=palabra)
            | Q(last_name__icontains=palabra)
            | Q(username__icontains=palabra)
            | Q(email__icontains=palabra)
        )
    usuarios = usuarios.select_related("profile").order_by(
        "first_name", "last_name", "username"
    )[:10]
    resultados = []
    for usuario in usuarios:
        perfil = getattr(usuario, "profile", None)
        faltantes = perfil.campos_faltantes_reserva() if perfil else ["perfil institucional"]
        resultados.append({
            "id": usuario.pk,
            "nombre": usuario.get_full_name() or usuario.username,
            "usuario": usuario.username,
            "correo": usuario.email,
            "tipo": perfil.get_tipo_usuario_display() if perfil and perfil.tipo_usuario else "Tipo no registrado",
            "tipo_codigo": perfil.tipo_usuario if perfil else "",
            "documento": (perfil.cedula or "") if perfil else "",
            "telefono": (perfil.telefono or "") if perfil else "",
            "facultad": perfil.get_facultad_display() if perfil and perfil.facultad else "No especificada",
            "carrera": perfil.get_carrera_display_custom() if perfil else "No especificado",
            "nivel": perfil.get_nivel_academico_display() if perfil and perfil.nivel_academico else "No especificado",
            "institucion": (perfil.institucion if perfil else "") or "No especificada",
            "habilitado": not faltantes,
            "faltantes": faltantes,
        })
    return JsonResponse({"success": True, "usuarios": resultados})


@require_http_methods(["GET"])
def cotizar_servicios_reserva(request):
    """Genera la estimación oficial visible antes de enviar la solicitud."""
    if not request.user.is_authenticated:
        return _respuesta_error("Usuario no autenticado", status=401)
    try:
        _perfil_valido_para_reserva(request.user)
    except ValueError as error:
        return _respuesta_error(str(error))

    modalidad = request.GET.get("modalidad", "modelo_listo")
    modalidades = {choice[0] for choice in Reserva.MODALIDAD_SERVICIO_CHOICES}
    if modalidad not in modalidades:
        return _respuesta_error("La modalidad del servicio no es válida")
    try:
        unidad_id, servicios = _servicios_solicitados(request.GET)
        validar_catalogo_consumibles_servicios(servicios, unidad_id)
    except ValueError as error:
        return _respuesta_error(str(error))
    campo_modalidad = {
        "modelo_listo": "permite_modelo_listo",
        "diseno_asistido": "permite_diseno_asistido",
        "diseno_completo": "permite_diseno_completo",
    }[modalidad]
    incompatibles = [
        servicio.nombre
        for servicio in servicios
        if not getattr(servicio, campo_modalidad)
    ]
    if incompatibles:
        return _respuesta_error(
            "La modalidad elegida no está disponible para: "
            + ", ".join(incompatibles)
        )
    try:
        cantidades = normalizar_cantidades_servicio(request.GET.get("cantidades"))
        validar_cantidades_servicio(servicios, cantidades)
        trabajo = parametros_trabajo_servicio(request.GET)
    except ValueError as error:
        return _respuesta_error(str(error))
    configuracion = ConfiguracionOperativaUnidad.objects.filter(unidad_id=unidad_id).first()
    return JsonResponse({"success": True, "cotizacion": calcular_cotizacion(
        servicios,
        modalidad,
        request.user,
        cantidades,
        configuracion=configuracion,
        piezas=trabajo["piezas"],
        seleccion=trabajo["seleccion"],
        urgencia=trabajo["urgencia"],
    )})


def _servicios_solicitados(datos):
    """Servicios publicados de la unidad indicados en la petición."""
    try:
        unidad_id = int(datos.get("unidad_id", ""))
        ids = [int(value) for value in datos.getlist("servicios")]
    except (TypeError, ValueError):
        raise ValueError("La selección de servicios no es válida")
    if not ids:
        raise ValueError("Selecciona al menos un servicio para calcular el valor")
    servicios = list(
        FablabService.objects.filter(
            pk__in=ids,
            unidad_id=unidad_id,
            activo=True,
            publico=True,
        ).prefetch_related("service_consumibles__consumible")
    )
    if len(servicios) != len(set(ids)):
        raise ValueError("Uno de los servicios no pertenece a esta unidad")
    return unidad_id, servicios


JORNADA_REFERENCIAL_HORAS = 8
DIAS_INCUMPLIMIENTO = 180
HORIZONTE_PROPUESTA_DIAS = 90


def _incumplimientos_recientes(usuario):
    """Reservas cerradas sin uso en los últimos seis meses: pierden prioridad."""
    desde = timezone.localdate() - timedelta(days=DIAS_INCUMPLIMIENTO)
    return Reserva.objects.filter(
        usuario=usuario,
        fecha__gte=desde,
        detalle_ejecucion__cumplimiento_resultado="no",
    ).count()


def _horas_enteras(valores):
    horas = set()
    for valor in valores or []:
        try:
            horas.add(int(valor))
        except (TypeError, ValueError):
            continue
    return horas


def _siguiente_dia_habil(fecha, es_administrador=False):
    fecha += timedelta(days=1)
    while fecha.weekday() >= 5 and not es_administrador:
        fecha += timedelta(days=1)
    return fecha


@require_http_methods(["GET"])
def proponer_entrega_servicio(request):
    """Propone día, hora y entrega según la cola de servicios y la jornada.

    Las horas de máquina del catálogo son por pieza; una solicitud urgente
    entra al día siguiente y una normal después de la cola pendiente de la
    unidad. Quien no utilizó reservas recientes pierde la atención urgente.
    """
    if not request.user.is_authenticated:
        return _respuesta_error("Usuario no autenticado", status=401)
    try:
        _perfil_valido_para_reserva(request.user)
        unidad_id, servicios = _servicios_solicitados(request.GET)
        trabajo = parametros_trabajo_servicio(request.GET)
    except ValueError as error:
        return _respuesta_error(str(error))
    unidad = Unidad.objects.filter(pk=unidad_id).first()
    if unidad is None:
        return _respuesta_error("La unidad indicada no existe")
    modalidad = request.GET.get("modalidad", "modelo_listo")
    proposito_codigo = request.GET.get("proposito", "")
    piezas = trabajo["piezas"]
    urgencia = trabajo["urgencia"]
    horas_equipo = sum(
        (Decimal(servicio.horas_equipo_estimadas or 0) for servicio in servicios),
        Decimal("0"),
    ) * piezas
    if horas_equipo <= 0:
        # Sin horas configuradas: una hora de referencia por pieza.
        horas_equipo = Decimal(piezas)
    horas_totales = max(1, int(ceil(horas_equipo)))

    hoy = timezone.localdate()
    es_administrador = request.user.is_staff
    avisos = []
    incumplimientos = _incumplimientos_recientes(request.user)
    if urgencia == "urgente" and incumplimientos:
        urgencia = "normal"
        avisos.append(
            f"Tienes {incumplimientos} reserva(s) no utilizada(s) en los últimos "
            f"{DIAS_INCUMPLIMIENTO // 30} meses: la atención urgente no está disponible "
            "y la solicitud entra en la cola normal."
        )
    cola = Reserva.objects.filter(
        laboratorio=unidad,
        tipo_solicitud="servicio",
        estado__in=ESTADOS_OCUPAN_AGENDA,
        fecha__gte=hoy,
    )
    cola_solicitudes = cola.count()
    cola_horas = sum(len(_horas_enteras(item.get_horas_seleccionadas_list())) for item in cola)
    desplazamiento = 1 if urgencia == "urgente" else 2 + min(
        20, int(ceil(cola_horas / JORNADA_REFERENCIAL_HORAS))
    )
    fecha = hoy + timedelta(days=desplazamiento)
    datos_usuario = _datos_usuario_para_periodo(request.user, None)
    for _intento in range(HORIZONTE_PROPUESTA_DIAS):
        if fecha.weekday() >= 5 and not es_administrador:
            fecha += timedelta(days=1)
            continue
        periodo = (
            PeriodoAcademico.objects.para_fecha(fecha)
            .operativos()
            .first()
        )
        semana = periodo.semana_para_fecha(fecha) if periodo else None
        jornadas, _contexto = _jornadas_habilitadas(
            unidad,
            periodo=periodo,
            fecha=fecha,
            tipo_solicitud="servicio",
            modalidad_servicio=modalidad,
            tipo_usuario=datos_usuario["tipo_usuario"],
            proposito_codigo=proposito_codigo,
            es_administrador=es_administrador,
        )
        apertura, cierre = ventana_atencion(
            getattr(unidad, 'configuracion_operativa', None),
            es_administrador,
        )
        habilitadas = sorted({
            hora
            for jornada in jornadas
            for hora in range(jornada.hora_inicio.hour, jornada.hora_fin.hour)
            if apertura <= hora < cierre
        })
        if (semana and not semana.permite_reservas) or not habilitadas:
            fecha += timedelta(days=1)
            continue
        ocupadas = set()
        for item in cola.filter(fecha=fecha):
            ocupadas |= _horas_enteras(item.get_horas_seleccionadas_list())
        bloque = min(horas_totales, len(habilitadas))
        corrida = []
        for hora in habilitadas:
            if hora in ocupadas:
                corrida = []
                continue
            if corrida and hora != corrida[-1] + 1:
                corrida = []
            corrida.append(hora)
            if len(corrida) >= bloque:
                break
        if len(corrida) < bloque:
            fecha += timedelta(days=1)
            continue
        seleccion = corrida[:bloque]
        restantes = horas_totales - bloque
        entrega = fecha
        while restantes > 0:
            entrega = _siguiente_dia_habil(entrega, es_administrador)
            restantes -= len(habilitadas)
        return JsonResponse({"success": True, "propuesta": {
            "fecha": fecha.isoformat(),
            "hora_inicio": f"{seleccion[0]:02d}:00",
            "hora_fin": f"{seleccion[-1] + 1:02d}:00",
            "horas_seleccionadas": seleccion,
            "horas_estimadas": horas_totales,
            "horas_equipo": f"{horas_equipo.normalize():f}",
            "piezas": piezas,
            "fecha_entrega": entrega.isoformat(),
            "urgencia": urgencia,
            "avisos": avisos,
            "cola": {"solicitudes": cola_solicitudes, "horas": cola_horas},
            "jornada": f"{habilitadas[0]:02d}:00–{habilitadas[-1] + 1:02d}:00",
        }})
    return _respuesta_error(
        "No se encontró una jornada disponible en los próximos 90 días; la unidad "
        "coordinará la fecha en la revisión técnica."
    )


@require_http_methods(["POST"])
def crear_reserva(request):
    """Registra equipos, espacios, software o servicios desde flujos diferenciados."""
    if request.POST.get('tipo_solicitud') == 'visita':
        from apps.reservas.presentation.visita_modal import crear_visita_desde_modal
        return crear_visita_desde_modal(request)
    if not request.user.is_authenticated:
        return _respuesta_error(
            "Debe iniciar sesión para enviar una solicitud de reserva.",
            status=401,
        )

    try:
        perfil_solicitante = _perfil_valido_para_reserva(request.user)
    except ValueError as error:
        return _respuesta_error(str(error))

    try:
        entrada = normalizar_entrada_basica(request.POST)
    except ValueError as error:
        return _respuesta_error(str(error))
    unidad_id = entrada.unidad_id
    tipo_solicitud = entrada.tipo_solicitud
    provision_consumibles = entrada.provision_consumibles
    piezas_por_sesion = entrada.piezas_por_sesion
    requisitos_especiales = entrada.requisitos_especiales
    modalidad_servicio = entrada.modalidad_servicio
    intencion_solicitud = entrada.intencion_solicitud
    incluye_espacio_solicitado = entrada.incluye_espacio_solicitado
    metodo_pago = entrada.metodo_pago
    cotizacion_aceptada = entrada.cotizacion_aceptada
    proposito_codigo = entrada.proposito_codigo
    proposito = entrada.proposito
    fecha_inicio_texto = entrada.fecha_inicio_texto
    fecha_fin_texto = entrada.fecha_fin_texto

    try:
        laboratorio = Unidad.objects.get(id=unidad_id)
    except (Unidad.DoesNotExist, TypeError, ValueError):
        return _respuesta_error("Laboratorio no encontrado")

    try:
        contexto_actividad = _validar_contexto_actividad(
            request,
            laboratorio,
            perfil_solicitante,
            proposito_codigo,
            tipo_solicitud=tipo_solicitud,
            validacion_completa=bool(request.POST.get('proposito_codigo')),
        )
        _validar_guia_integrada(
            request,
            requerida=_requiere_guia_integrada(
                tipo_solicitud,
                proposito_codigo,
                contexto_actividad,
            ),
        )
        if (
            proposito_codigo == 'docencia_practica'
            and contexto_actividad['vinculacion_actividad'] in {'manual', 'clonada'}
            and not request.user.is_staff
            and getattr(perfil_solicitante, 'tipo_usuario', '') == 'docente'
        ):
            vencida = guias_vencidas_sin_enviar(request.user).first()
            if vencida:
                raise ValueError(
                    'Antes de solicitar otra práctica, envía a revisión la guía '
                    f'vencida "{vencida.titulo}".'
                )
    except ValueError as error:
        return _respuesta_error(str(error))

    configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(
        unidad=laboratorio
    )
    capacidades = {
        "recursos": any((
            configuracion.reservas_equipos,
            configuracion.reservas_espacios,
            SoftwareDisponible.objects.filter(
                unidad=laboratorio,
                activo=True,
                requiere_reserva=True,
            ).exists(),
        )),
        "equipo": configuracion.reservas_equipos,
        "espacio": configuracion.reservas_espacios,
        "software": SoftwareDisponible.objects.filter(
            unidad=laboratorio,
            activo=True,
            requiere_reserva=True,
        ).exists(),
        "servicio": configuracion.solicitudes_servicio,
    }
    if not capacidades[tipo_solicitud]:
        return _respuesta_error("Este tipo de solicitud no está habilitado para la unidad")
    if provision_consumibles == "unidad" and not configuracion.consumibles:
        return _respuesta_error(
            "Este laboratorio no tiene habilitada la provisión de consumibles"
        )

    materia_prima_cliente = False
    try:
        seleccion_proceso = resolver_seleccion_proceso(
            request.POST,
            laboratorio,
            tipo_solicitud,
        )
        intervalo = normalizar_intervalo(
            request.POST,
            fecha_inicio_texto,
            fecha_fin_texto,
        )
    except ValueError as error:
        return _respuesta_error(str(error))
    receta_proceso = seleccion_proceso.receta
    producto_solicitado = seleccion_proceso.producto
    factor_proceso = seleccion_proceso.factor
    fecha_inicio = intervalo.fecha_inicio
    horas = intervalo.horas
    hora_inicio = intervalo.hora_inicio
    hora_fin = intervalo.hora_fin
    duracion = intervalo.duracion

    try:
        contexto_actividad.update(
            resolver_periodo_reserva(
                fecha_inicio.date(),
                contexto_actividad,
                proposito_codigo,
            )
        )
    except ValueError as error:
        return _respuesta_error(str(error))
    try:
        frecuencia_reserva, fechas_programadas, fechas_omitidas = _fechas_de_programacion(
            request,
            fecha_inicio.date(),
            contexto_actividad,
            tipo_solicitud,
        )
        for fecha_programada in fechas_programadas:
            validar_intervalo_institucional(
                datetime.combine(fecha_programada, hora_inicio),
                datetime.combine(fecha_programada, hora_fin),
            )
    except ValueError as error:
        return _respuesta_error(str(error))
    datos_solicitante_periodo = _datos_usuario_para_periodo(
        request.user,
        contexto_actividad['periodo'],
    )
    # La asignatura del período: el cronograma y las guías por sesión nacen de sus temas.
    asignatura = None
    asignatura_id = (request.POST.get("asignatura_id") or "").strip()
    if asignatura_id:
        if proposito_codigo != "docencia_practica":
            return _respuesta_error("La asignatura solo acompaña a una práctica docente")
        asignatura = (
            Asignatura.objects.filter(pk=asignatura_id, unidad=laboratorio, activa=True).first()
            if asignatura_id.isdigit()
            else None
        )
        if asignatura is None:
            return _respuesta_error("La asignatura seleccionada no está disponible en esta unidad")
    # El cronograma: qué práctica y qué proceso lleva cada sesión programada.
    try:
        filas_cronograma = normalizar_cronograma(
            request.POST.get("cronograma"),
            fechas_programadas,
            laboratorio,
            receta_principal=receta_proceso,
            factor_principal=factor_proceso,
        )
    except ValueError as error:
        return _respuesta_error(str(error))
    try:
        for fecha_programada in fechas_programadas:
            periodo_sesion = resolver_periodo_reserva(
                fecha_programada,
                contexto_actividad,
                proposito_codigo,
            )
            _validar_horario_operativo(
                laboratorio,
                periodo=periodo_sesion['periodo'],
                semana=periodo_sesion['semana_academica'],
                fecha=fecha_programada,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                tipo_solicitud=tipo_solicitud,
                modalidad_servicio=modalidad_servicio,
                tipo_usuario=datos_solicitante_periodo['tipo_usuario'],
                proposito_codigo=proposito_codigo,
                es_administrador=request.user.is_staff,
                # Un proceso no se detiene al mediodía: la sesión cruza el almuerzo.
                permitir_almuerzo=receta_proceso is not None,
            )
    except ValueError as error:
        return _respuesta_error(str(error))

    try:
        seleccion_recursos = resolver_recursos_fisicos(
            request.POST,
            unidad=laboratorio,
            configuracion=configuracion,
            tipo_solicitud=tipo_solicitud,
            modalidad_servicio=modalidad_servicio,
            proposito_codigo=proposito_codigo,
            incluye_espacio_solicitado=incluye_espacio_solicitado,
            requisitos_especiales=requisitos_especiales,
        )
        responsable = seleccion_recursos.responsable
        recursos = seleccion_recursos.recursos
        equipos = seleccion_recursos.equipos
        software = seleccion_recursos.software
        espacios = seleccion_recursos.espacios
        alcance_espacio = seleccion_recursos.alcance_espacio
        requiere_espacio = seleccion_recursos.requiere_espacio
        solicito_software = seleccion_recursos.solicito_software
        solicito_equipo = seleccion_recursos.solicito_equipo
        solicito_espacio = seleccion_recursos.solicito_espacio
        requisitos_especiales = seleccion_recursos.requisitos_especiales
        participantes = _validar_participantes(
            request.POST.get("participantes_seleccionados", "[]"),
            request.user,
        )
        if (
            frecuencia_reserva in {"semanal_periodo", "semanal_rango"}
            and proposito_codigo == "docencia_practica"
            and not participantes
        ):
            return _respuesta_error(
                "Agrega al menos un estudiante o participante registrado en el paso "
                "Datos y actividad antes de programar la actividad docente semanal o "
                "de todo el período"
            )
        guias_actividad = _validar_guias_actividad(
            request,
            permite_carga=(
                tipo_solicitud != 'servicio'
                and
                proposito_codigo == 'docencia_practica'
                and contexto_actividad['vinculacion_actividad'] in {'manual', 'clonada'}
            ),
            requerida=False,
        )
        permisos_descarga_guias = _permisos_descarga_guias(
            request,
            len(guias_actividad),
        )
        seleccion_catalogos = resolver_catalogos_solicitud(
            request.POST,
            request.FILES,
            unidad=laboratorio,
            tipo_solicitud=tipo_solicitud,
            modalidad_servicio=modalidad_servicio,
            equipos=equipos,
            receta_proceso=receta_proceso,
            espacios=espacios,
        )
        consumibles = seleccion_catalogos.consumibles
        servicios = seleccion_catalogos.servicios
        archivos = seleccion_catalogos.archivos
        indicaciones_archivos = seleccion_catalogos.indicaciones_archivos
    except ValueError as error:
        return _respuesta_error(str(error))

    try:
        preparacion = preparar_solicitud(
            request.POST,
            usuario=request.user,
            unidad=laboratorio,
            configuracion=configuracion,
            tipo_solicitud=tipo_solicitud,
            modalidad_servicio=modalidad_servicio,
            metodo_pago=metodo_pago,
            cotizacion_aceptada=cotizacion_aceptada,
            provision_consumibles=provision_consumibles,
            incluye_espacio_solicitado=incluye_espacio_solicitado,
            requiere_espacio=requiere_espacio,
            recursos=recursos,
            equipos=equipos,
            software=software,
            espacios=espacios,
            servicios=servicios,
            consumibles=consumibles,
            fecha_inicio=fecha_inicio,
            hora_fin=hora_fin,
            duracion=duracion,
            sesiones_programa=len(fechas_programadas),
            receta_proceso=receta_proceso,
            factor_proceso=factor_proceso,
        )
    except ValueError as error:
        return _respuesta_error(str(error))
    consumibles_a_registrar = preparacion.consumibles_a_registrar
    provision_consumibles = preparacion.provision_consumibles
    modalidad_servicio = preparacion.modalidad_servicio
    metodo_pago = preparacion.metodo_pago
    cotizacion_aceptada = preparacion.cotizacion_aceptada
    incluye_espacio = preparacion.incluye_espacio
    trabajo_servicio = preparacion.trabajo_servicio
    fecha_entrega_prevista = preparacion.fecha_entrega_prevista
    fin_servicio_programado = preparacion.fin_servicio_programado
    equipo_servicio = preparacion.equipo_servicio
    detalle_trabajo = preparacion.detalle_trabajo
    receta_proceso = preparacion.receta_proceso
    factor_proceso = preparacion.factor_proceso
    materia_prima_cliente = preparacion.materia_prima_cliente
    cotizacion = preparacion.cotizacion

    # Cada sesión con un proceso propio se valida y nace con lo que ese proceso exige.
    recursos_por_sesion = {}
    for indice, fila in enumerate(filas_cronograma):
        if indice == 0 or fila['receta'] is None:
            continue
        if receta_proceso is not None and fila['receta'].pk == receta_proceso.pk and fila['factor'] == factor_proceso:
            continue
        recursos_por_sesion[indice] = recursos_de_sesion(
            fila['receta'], fila['factor'], personas=1 + len(participantes)
        )

    conflictos = []
    for indice, fecha_programada in enumerate(fechas_programadas):
        recursos_fecha, software_fecha, espacios_fecha, incluye_fecha, alcance_fecha = _recursos_para_validar(
            indice, recursos_por_sesion, recursos, software, espacios, incluye_espacio, alcance_espacio,
        )
        try:
            validar_conflictos_recursos(
                laboratorio,
                fecha_programada,
                hora_inicio,
                hora_fin,
                recursos_fecha,
                software_fecha,
                espacios_fecha,
                incluye_espacio=incluye_fecha,
                alcance_espacio=alcance_fecha,
                tipo_solicitud=tipo_solicitud,
                modalidad_servicio=modalidad_servicio,
                proposito_codigo=proposito_codigo,
                numero_participantes=1 + len(participantes),
            )
        except ValueError as error:
            conflictos.append(f'{fecha_programada:%d/%m/%Y}: {error}')
    if conflictos:
        detalle_conflictos = ' | '.join(conflictos[:5])
        if len(conflictos) > 5:
            detalle_conflictos += f' | y {len(conflictos) - 5} conflicto(s) más'
        return _respuesta_error(
            'No se puede crear toda la programación porque existen conflictos: '
            + detalle_conflictos
        )

    if len(equipos) == 1:
        equipo_codigo, equipo_nombre = equipos[0].codigo, equipos[0].nombre
    elif equipos:
        equipo_codigo, equipo_nombre = "MULTI", "Múltiples equipos"
    elif tipo_solicitud == "servicio" and len(servicios) == 1:
        equipo_codigo, equipo_nombre = servicios[0].code, servicios[0].nombre
    elif tipo_solicitud == "servicio":
        equipo_codigo, equipo_nombre = "SERVICIO", "Servicios técnicos solicitados"
    elif tipo_solicitud in {"software", "recursos"} and len(software) == 1:
        equipo_codigo, equipo_nombre = software[0].codigo or "SOFTWARE", software[0].nombre
    elif tipo_solicitud in {"software", "recursos"} and software:
        equipo_codigo, equipo_nombre = "SOFTWARE", "Software y licencias"
    elif len(espacios) == 1:
        equipo_codigo, equipo_nombre = espacios[0].codigo, espacios[0].nombre
    elif espacios:
        equipo_codigo, equipo_nombre = "ESPACIOS", "Múltiples áreas o estaciones"
    elif tipo_solicitud == "recursos":
        equipo_codigo, equipo_nombre = "ESPACIO", "Espacio de la unidad"
    else:
        equipo_codigo, equipo_nombre = "ESPACIO", "Espacio solicitado"

    titulo_solicitud = _generar_titulo(
        tipo_solicitud,
        proposito,
        equipos,
        software,
        servicios,
        laboratorio,
        incluye_espacio=incluye_espacio,
        modalidad_servicio=modalidad_servicio,
        espacios=espacios,
    )
    if producto_solicitado is not None:
        titulo_solicitud = (
            f'{titulo_solicitud} · Producto: {producto_solicitado.nombre}'
        )[:255]
    descripcion = _generar_descripcion(
        tipo_solicitud,
        proposito,
        equipos,
        software,
        servicios,
        laboratorio,
        incluye_espacio=incluye_espacio,
        modalidad_servicio=modalidad_servicio,
        espacios=espacios,
        intencion=intencion_solicitud,
    )

    comando = ComandoCreacionReserva(
        actor=request.user,
        unidad=laboratorio,
        perfil_solicitante=perfil_solicitante,
        datos_solicitante_periodo=datos_solicitante_periodo,
        contexto_actividad=contexto_actividad,
        tipo_solicitud=tipo_solicitud,
        proposito=proposito,
        proposito_codigo=proposito_codigo,
        frecuencia_reserva=frecuencia_reserva,
        fechas_programadas=fechas_programadas,
        fechas_omitidas=fechas_omitidas,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        duracion=duracion,
        horas=horas,
        horas_seleccionadas_texto=request.POST.get("horas_seleccionadas"),
        receta_proceso=receta_proceso,
        producto_solicitado=producto_solicitado,
        factor_proceso=factor_proceso,
        provision_consumibles=provision_consumibles,
        incluye_espacio=incluye_espacio,
        solicito_espacio=solicito_espacio,
        solicito_equipo=solicito_equipo,
        solicito_software=solicito_software,
        alcance_espacio=alcance_espacio,
        responsable=responsable,
        recursos=recursos,
        software=software,
        espacios=espacios,
        servicios=servicios,
        participantes=participantes,
        consumibles_a_registrar=consumibles_a_registrar,
        archivos=archivos,
        indicaciones_archivos=indicaciones_archivos,
        guias_actividad=guias_actividad,
        permisos_descarga_guias=permisos_descarga_guias,
        solicita_publicacion_guias=(
            request.POST.get("solicitar_publicacion_guias")
            in {"1", "true", "on", "si", "sí"}
        ),
        modalidad_servicio=modalidad_servicio,
        materia_prima_cliente=materia_prima_cliente,
        cotizacion=cotizacion,
        cotizacion_aceptada=cotizacion_aceptada,
        metodo_pago=metodo_pago,
        trabajo_servicio=trabajo_servicio,
        piezas_por_sesion=piezas_por_sesion,
        detalle_trabajo=detalle_trabajo,
        fecha_entrega_prevista=fecha_entrega_prevista,
        fin_servicio_programado=fin_servicio_programado,
        equipo_servicio=equipo_servicio,
        filas_cronograma=filas_cronograma,
        recursos_por_sesion=recursos_por_sesion,
        asignatura=asignatura,
        equipo_codigo=equipo_codigo,
        equipo_nombre=equipo_nombre,
        titulo_solicitud=titulo_solicitud,
        descripcion=descripcion,
        requisitos_especiales=requisitos_especiales,
        intencion_solicitud=intencion_solicitud,
        institucion_solicitada=request.POST.get("institucion", ""),
        siglas_institucion=identidad_actual()[1].siglas,
        requiere_guia_integrada=_requiere_guia_integrada(
            tipo_solicitud,
            proposito_codigo,
            contexto_actividad,
        ),
    )
    try:
        resultado_creacion = crear_expediente_reserva(
            comando,
            completar_guia=lambda **datos: _completar_guia_integrada(
                request,
                **datos,
            ),
            auditar=lambda **datos: registrar_auditoria(request, **datos),
        )
    except PermissionDenied as error:
        return _respuesta_error(str(error), status=403)
    except (TypeError, ValueError) as error:
        return _respuesta_error(f"Datos de la solicitud no válidos: {error}")
    except Exception as error:
        return _respuesta_error(f"Error al guardar en base de datos: {error}")

    reserva = resultado_creacion.reserva
    reserva_principal = resultado_creacion.reserva_principal
    reservas_creadas = resultado_creacion.reservas_creadas
    programacion = resultado_creacion.programacion
    guia_estructurada = resultado_creacion.guia_estructurada
    guia_estructurada_creada = resultado_creacion.guia_estructurada_creada
    planificacion_principal = resultado_creacion.planificacion_principal
    planificaciones_creadas = resultado_creacion.planificaciones_creadas
    comprobante_url = resultado_creacion.comprobante_url

    guia_edicion_url = ""
    # Solo se manda a terminar la guía a quien puede editarla: si el formato
    # pendiente es de otra persona, la solicitud sigue su curso con el
    # comprobante y la unidad resuelve la documentación.
    puede_editar = bool(
        guia_estructurada and puede_editar_guia(request.user, guia_estructurada)
    )
    requiere_accion_documental = bool(
        puede_editar
        and guia_estructurada.estado_publicacion in {"borrador", "rechazada"}
    )
    if requiere_accion_documental:
        guia_edicion_url = (
            reverse(
                "editar_guia_practica",
                args=[laboratorio.slug, guia_estructurada.pk],
            )
            + f"?reserva={reserva_principal.pk}&reserva_creada=1"
        )

    return JsonResponse({
        "success": True,
        "reserva_id": reserva.id,
        "numero_referencia": reserva.codigo_reserva or f"RES-{reserva.id:06d}",
        # Lo que la unidad exige y la persona aún no cumple: se avisa, no se bloquea.
        "acceso_pendiente": pendientes_al_reservar(laboratorio, request.user, reserva.fecha),
        "unidades_reservadas": len(recursos),
        "equipos_reservados": len(equipos),
        "consumibles_solicitados": len(consumibles_a_registrar),
        "servicios_solicitados": len(servicios),
        "software_solicitado": len(software),
        "espacios_solicitados": len(espacios),
        "responsable_asignado": (
            {
                "id": responsable.pk,
                "nombre": responsable.nombre_publico,
                "rol": responsable.get_rol_display(),
            }
            if responsable else None
        ),
        "participantes": 1 + len(participantes),
        "titulo_solicitud": titulo_solicitud,
        "costo_estimado": cotizacion.get("total") if cotizacion else None,
        "archivos_tecnicos": len(archivos),
        "guias_actividad": len(guias_actividad),
        "guia_estructurada": (
            {
                "id": guia_estructurada.pk,
                "creada": guia_estructurada_creada,
                "estado": guia_estructurada.estado_publicacion,
                "url_html": reverse(
                    "ver_guia_actividad",
                    args=[guia_estructurada.pk],
                ),
                "url_edicion": (
                    reverse(
                        "editar_guia_practica",
                        args=[laboratorio.slug, guia_estructurada.pk],
                    )
                    if puede_editar else ""
                ),
            }
            if guia_estructurada else None
        ),
        "programacion_id": programacion.pk if programacion else None,
        "sesiones_creadas": len(reservas_creadas),
        "sesiones_url": (
            reverse('mis_sesiones', args=[laboratorio.slug]) if len(reservas_creadas) > 1 else ""
        ),
        "planificacion_id": (
            planificacion_principal.pk if planificacion_principal else None
        ),
        "planificaciones_creadas": planificaciones_creadas,
        "fechas_omitidas": [fecha.isoformat() for fecha in fechas_omitidas],
        "comprobante_url": comprobante_url,
        "siguiente_url": guia_edicion_url or comprobante_url,
        "siguiente_paso": "guia" if requiere_accion_documental else "comprobante",
        "requiere_accion_documental": requiere_accion_documental,
        "message": "Solicitud registrada correctamente para revisión.",
    })


def _documentacion_solicitante(reserva):
    """Guía de práctica de la reserva con los enlaces que abre el titular."""
    documentacion = dict(estado_documental_reserva(reserva))
    documentacion["url"] = ""
    documentacion["fragmento_url"] = ""
    documentacion["pdf_url"] = ""
    documentacion["descarga_url"] = ""
    documentacion["accion"] = ""
    documentacion["puede_firmar"] = False
    documentacion["subir_firmada_url"] = ""
    documentacion["firmada"] = ""
    guia_id = documentacion.get("guia_id")
    if guia_id:
        vista = reverse("ver_guia_actividad", args=[guia_id])
        # Firmar con FirmaEC y cargar el PDF se hace desde el expediente.
        guia = GuiaActividadReserva.objects.filter(pk=guia_id).first()
        if guia and guia.estado_publicacion in {"revision", "publicada"}:
            documentacion["puede_firmar"] = True
            documentacion["subir_firmada_url"] = reverse(
                "subir_guia_firmada",
                args=[guia_id],
            )
            if guia.archivo_firmado:
                documentacion["firmada"] = guia.firma_certificada_resumen
        documentacion["fragmento_url"] = f"{vista}?fragmento=1"
        documentacion["pdf_url"] = f"{vista}?preview=pdf"
        documentacion["descarga_url"] = f"{vista}?download=1"
        # Solo se sale del expediente para corregir una guía propia, y se
        # puede hacer mientras el laboratorio no la valide para publicar.
        if guia and puede_editar_guia(reserva.usuario, guia):
            documentacion["url"] = reverse(
                "editar_guia_practica",
                args=[reserva.laboratorio.slug, guia_id],
            )
            documentacion["accion"] = (
                "Corregir la guía enviada"
                if guia.estado_publicacion == "revision"
                else "Corregir la guía"
            )
    elif documentacion.get("requiere_guia") and documentacion.get("actividad_id"):
        documentacion["url"] = (
            reverse("nueva_guia_practica", args=[reserva.laboratorio.slug])
            + f"?actividad={documentacion['actividad_id']}&reserva={reserva.pk}"
        )
        documentacion["accion"] = "Crear la guía"
    return documentacion


@require_http_methods(["GET"])
def obtener_reservas_usuario(request):
    """Lista las reservas y los materiales solicitados por el usuario autenticado."""
    if not request.user.is_authenticated:
        return _respuesta_error("Usuario no autenticado")
    filtros = {"usuario": request.user}
    laboratorio_id = request.GET.get("laboratorio_id")
    if laboratorio_id:
        filtros["laboratorio_id"] = laboratorio_id

    datos = []
    reservas = (
        Reserva.objects.filter(**filtros)
        .select_related(
            "laboratorio",
            "producto_solicitado",
            "responsable_asignado",
            "responsable_asignado__usuario",
        )
        .prefetch_related(
            "consumibles_solicitados__consumible",
            "servicios_solicitados",
            "software_solicitado",
            "espacios_solicitados",
            "participantes__profile",
            "archivos_tecnicos",
            "solicitudes_cambio__revision_aplicada",
        )
        .order_by("-fecha_reserva")
    )
    for reserva in reservas:
        from apps.reservas.presentation.cambios_views import serializar_solicitud_cambio

        solicitud_cambio = reserva.solicitudes_cambio.first()
        observaciones_seguimiento = [
            linea.strip()
            for linea in (reserva.observaciones_validacion or "").splitlines()
            if linea.strip()
        ]
        try:
            unidades = json.loads(reserva.unidades_seleccionadas or "[]")
        except (json.JSONDecodeError, TypeError):
            unidades = []
        try:
            horas = json.loads(reserva.horas_seleccionadas or "[]")
        except (json.JSONDecodeError, TypeError):
            horas = []
        materiales = [
            {
                "id": item.consumible_id,
                "nombre": item.consumible.nombre,
                "cantidad_solicitada": (
                    str(item.cantidad_solicitada)
                    if item.cantidad_solicitada is not None
                    else None
                ),
                "cantidad_por_definir": item.cantidad_solicitada is None,
                "metodo_estimacion": item.metodo_estimacion,
                "metodo_estimacion_display": item.get_metodo_estimacion_display(),
                "cantidad_aprobada": str(item.cantidad_aprobada) if item.cantidad_aprobada is not None else None,
                "unidad_medida": item.consumible.unidad_medida or "unidades",
            }
            for item in reserva.consumibles_solicitados.all()
        ]
        datos.append({
            "id": reserva.id,
            "codigo_reserva": reserva.codigo_reserva or f"RES-{reserva.id:06d}",
            "tipo_solicitud": reserva.tipo_solicitud,
            "tipo_solicitud_display": reserva.get_tipo_solicitud_display(),
            "titulo_solicitud": reserva.titulo_solicitud,
            "resumen_solicitud": reserva.resumen_solicitud,
            "producto_solicitado": (
                reserva.producto_solicitado.nombre
                if reserva.producto_solicitado_id else ""
            ),
            "incluye_espacio": reserva.incluye_espacio,
            "provision_consumibles": reserva.provision_consumibles,
            "provision_consumibles_display": reserva.get_provision_consumibles_display(),
            "equipo_nombre": reserva.equipo_nombre,
            "equipo_codigo": reserva.equipo_codigo,
            "fecha": reserva.fecha.isoformat() if reserva.fecha else None,
            "hora_inicio": reserva.hora_inicio.strftime("%H:%M") if reserva.hora_inicio else None,
            "hora_fin": reserva.hora_fin.strftime("%H:%M") if reserva.hora_fin else None,
            "estado": reserva.estado,
            "estado_display": reserva.get_estado_display(),
            "es_cerrada": reserva.estado in ESTADOS_CERRADOS,
            "ocupa_agenda": reserva.estado in ESTADOS_OCUPAN_AGENDA,
            # Mismas condiciones que aplican cancelar_reserva_usuario y
            # solicitar_cambio_reserva al recibir la peticion.
            "puede_cancelar": reserva.estado == "pendiente",
            "cancelacion": texto_cancelacion(reserva),
            "puede_solicitar_cambio": (
                reserva.estado in REGLAS_TRANSICION["actualizar"].origenes
            ),
            "numero_participantes": reserva.numero_participantes or 1,
            "proposito": reserva.proposito,
            "proposito_codigo": reserva.proposito_codigo,
            "proposito_display": (
                reserva.get_proposito_codigo_display()
                if reserva.proposito_codigo else reserva.proposito
            ),
            "subtipo_actividad": reserva.subtipo_actividad,
            "subtipo_actividad_display": (
                reserva.get_subtipo_actividad_display()
                if reserva.subtipo_actividad else ""
            ),
            "alcance_beneficiario": reserva.alcance_beneficiario,
            "alcance_beneficiario_display": reserva.get_alcance_beneficiario_display(),
            "facultad_beneficiaria": reserva.facultad_beneficiaria,
            "carrera_beneficiaria": reserva.carrera_beneficiaria,
            "entidad_beneficiaria": reserva.entidad_beneficiaria,
            "vinculacion_actividad": reserva.vinculacion_actividad,
            "vinculacion_actividad_display": reserva.get_vinculacion_actividad_display(),
            "referencia_actividad": reserva.referencia_actividad,
            "codigo_referencia_actividad": reserva.codigo_referencia_actividad,
            "periodo_academico": reserva.periodo_academico,
            "periodo_academico_id": reserva.periodo_id,
            "semana_academica": reserva.semana_academica_numero,
            "responsable_actividad": reserva.responsable_actividad,
            "origen_programacion": reserva.origen_programacion,
            "origen_programacion_display": reserva.get_origen_programacion_display(),
            "descripcion_proyecto": reserva.descripcion_proyecto,
            "unidades_seleccionadas": [
                f"{item.get('codigo', 'N/A')} - {item.get('ubicacion', 'N/A')}"
                for item in unidades
            ],
            "horas_seleccionadas": [f"{hora}:00" for hora in horas],
            "total_unidades": len(unidades),
            "consumibles": materiales,
            "servicios": [
                {"id": item.pk, "codigo": item.code, "nombre": item.nombre}
                for item in reserva.servicios_solicitados.all()
            ],
            "software": [
                {
                    "id": item.pk,
                    "nombre": item.nombre,
                    "version": item.version,
                    "tipo_acceso": item.get_tipo_acceso_display(),
                }
                for item in reserva.software_solicitado.all()
            ],
            "espacios": [
                {
                    "id": item.pk,
                    "codigo": item.codigo,
                    "nombre": item.nombre,
                    "tipo": item.get_tipo_display(),
                    "ubicacion": item.ubicacion,
                }
                for item in reserva.espacios_solicitados.all()
            ],
            "responsable": (
                {
                    "id": reserva.responsable_asignado.pk,
                    "nombre": reserva.responsable_asignado.nombre_publico,
                    "rol": reserva.responsable_asignado.get_rol_display(),
                    "correo": reserva.responsable_asignado.email_publico,
                    "telefono": reserva.responsable_asignado.telefono,
                }
                if reserva.responsable_asignado else None
            ),
            "participantes": [
                {
                    "id": item.pk,
                    "nombre": item.get_full_name() or item.username,
                    "correo": item.email,
                }
                for item in reserva.participantes.all()
            ],
            "modalidad_servicio": reserva.modalidad_servicio,
            "modalidad_servicio_display": (
                reserva.get_modalidad_servicio_display()
                if reserva.modalidad_servicio else ""
            ),
            "costo_estimado": (
                str(reserva.costo_estimado) if reserva.costo_estimado is not None else None
            ),
            "descuento_aplicado": str(reserva.descuento_aplicado),
            "cotizacion_aceptada": reserva.cotizacion_aceptada,
            "metodo_pago": reserva.metodo_pago,
            "metodo_pago_display": (
                reserva.get_metodo_pago_display() if reserva.metodo_pago else ""
            ),
            "urgencia_servicio": reserva.urgencia_servicio,
            "urgencia_servicio_display": (
                reserva.get_urgencia_servicio_display() if reserva.urgencia_servicio else ""
            ),
            "cantidad_piezas": reserva.cantidad_piezas,
            "detalle_trabajo": reserva.detalle_trabajo,
            "fecha_entrega_prevista": (
                reserva.fecha_entrega_prevista.isoformat()
                if reserva.fecha_entrega_prevista else None
            ),
            "desglose_cotizacion": reserva.desglose_cotizacion,
            "archivos_tecnicos": [
                {
                    "id": item.pk,
                    "nombre": item.nombre_original,
                    "extension": item.extension,
                    "tamano": item.tamano,
                    "indicaciones_visualizacion": item.indicaciones_visualizacion,
                }
                for item in reserva.archivos_tecnicos.all()
            ],
            "fecha_creacion": reserva.fecha_reserva.isoformat() if reserva.fecha_reserva else None,
            "motivo": reserva.motivo,
            "laboratorio_nombre": reserva.laboratorio.nombre,
            "nombre_solicitante": reserva.nombre_solicitante,
            "correo_solicitante": reserva.correo_solicitante,
            "institucion": reserva.institucion or "",
            "telefono_solicitante": reserva.telefono_solicitante or "",
            "requisitos_especiales": reserva.requisitos_especiales or "",
            "observaciones_seguimiento": observaciones_seguimiento,
            "informacion_adicional_solicitada": any(
                linea.startswith("Información adicional solicitada:")
                for linea in observaciones_seguimiento
            ),
            "duracion": reserva.duracion,
            "fecha_actualizacion": reserva.fecha_actualizacion.isoformat() if reserva.fecha_actualizacion else None,
            "comprobante_url": reverse(
                "comprobante_reserva",
                args=[reserva.pk],
            ),
            "solicitar_cambio_url": reverse(
                "solicitar_cambio_reserva",
                args=[reserva.pk],
            ),
            "solicitud_cambio": serializar_solicitud_cambio(solicitud_cambio),
            # El expediente completo vive en «Mis reservas»: recorrido del
            # estado, comprobante y guía sin salir del panel.
            "linea_tiempo": linea_tiempo_reserva(
                reserva,
                nota_cierre=texto_cancelacion(reserva),
            ),
            "documentacion": _documentacion_solicitante(reserva),
            "comprobante_fragmento_url": (
                f"{reverse('comprobante_reserva', args=[reserva.pk])}?fragmento=1"
            ),
            "comprobante_pdf_url": (
                f"{reverse('comprobante_reserva_pdf', args=[reserva.pk])}?inline=1"
            ),
        })
    return JsonResponse({
        "success": True,
        "reservas": datos,
        "total": len(datos),
        "usuario": request.user.username,
        "laboratorio_id": laboratorio_id,
    })


@require_http_methods(["POST"])
def cancelar_reserva_usuario(request, reserva_id):
    """Adaptador HTTP de cancelacion propia; conserva respuesta de Mis reservas."""
    if not request.user.is_authenticated:
        return _respuesta_error("Usuario no autenticado", status=401)
    reserva = Reserva.objects.filter(pk=reserva_id, usuario=request.user).first()
    if reserva is None:
        return _respuesta_error("La reserva no existe o no pertenece al usuario.", status=404)
    try:
        reserva = cancelar_reserva_propia(
            reserva, actor=request.user, motivo=request.POST.get('motivo', ''),
            request=request, unidad_esperada=reserva.laboratorio_id)
    except PermissionDenied as error:
        return _respuesta_error(str(error), status=403)
    except ValidationError as error:
        codigo = getattr(error, 'code', None)
        estado_http = 400 if codigo == 'motivo_invalido' else 404 if codigo == 'no_disponible' else 409
        return _respuesta_error(' '.join(error.messages), status=estado_http)
    return JsonResponse({
        "cancelacion": texto_cancelacion(reserva),
        "success": True,
        "reserva_id": reserva.pk,
        "estado": reserva.estado,
        "estado_display": reserva.get_estado_display(),
        "message": gettext("Reserva cancelada correctamente."),
    })
