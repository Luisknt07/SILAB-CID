"""Árbol y entrega controlada de los recursos configurables de una unidad."""

import mimetypes
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from django.contrib.auth.views import redirect_to_login
from django.db.models import F, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.recursos.entrega.media import es_contenido_activo
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.documentos.models.expediente import DocumentoExpediente

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.plantas_piloto.operacion.presentation.secciones_plantas import secciones_ocultas


NIVEL_VISIBILIDAD = {'publica': 0, 'restringida': 1, 'interna': 2}
RESOLUCION_CREACION = 'RESOLUCION-CREACION'


@dataclass(frozen=True)
class _ContextoAccesoUnidad:
    """Decisiones compartidas únicamente durante la construcción de un árbol."""
    unidad_id: int
    usuario: object
    gestor: bool
    ocultas: frozenset


def _visibilidad_mas_restrictiva(*valores):
    return max(valores, key=lambda valor: NIVEL_VISIBILIDAD.get(valor, 2))


def _visibilidad_de_carpeta(carpeta):
    valores = [carpeta.visibilidad]
    ancestro = carpeta.carpeta_padre
    visitados = {carpeta.pk}
    while ancestro and ancestro.pk not in visitados:
        visitados.add(ancestro.pk)
        valores.append(ancestro.visibilidad)
        ancestro = ancestro.carpeta_padre
    return _visibilidad_mas_restrictiva(*valores)


def _jerarquia_activa(carpeta):
    visitados = set()
    actual = carpeta
    while actual and actual.pk not in visitados:
        visitados.add(actual.pk)
        if not actual.activa:
            return False
        actual = actual.carpeta_padre
    return actual is None


def _seccion_de_carpeta(carpeta):
    """La sección numerada de la que cuelga la carpeta; la subcarpeta hereda la de su superior."""
    return carpeta.seccion_planta or (carpeta.carpeta_padre.seccion_planta if carpeta.carpeta_padre_id else '')


def _acceso_recurso(recurso, usuario, *, contexto=None):
    if contexto is not None and (
        not isinstance(contexto, _ContextoAccesoUnidad)
        or contexto.unidad_id != recurso.unidad_id or contexto.usuario is not usuario
    ):
        raise ValueError('El contexto de acceso debe pertenecer a la misma unidad y persona.')
    if recurso.carpeta_id and not _jerarquia_activa(recurso.carpeta):
        return 'denegado'
    expediente_interno = False
    gestor = contexto.gestor if contexto is not None else puede_gestionar_unidad(usuario, recurso.unidad)
    # Una sección oculta se lleva sus carpetas: solo quien gestiona la unidad sigue abriendo sus archivos.
    seccion = _seccion_de_carpeta(recurso.carpeta) if recurso.carpeta_id else ''
    if seccion and not gestor:
        ocultas = contexto.ocultas if contexto is not None else secciones_ocultas(recurso.unidad_id)
        if seccion in ocultas:
            return 'denegado'
    if hasattr(recurso, 'informe_mejora'):
        from apps.documentos.presentation.mejora_seguimiento import puede_leer_mejora

        if (recurso.informe_mejora.unidad_id != recurso.unidad_id
                or not puede_leer_mejora(usuario, recurso.informe_mejora)):
            return 'denegado'
        gestor = True
        expediente_interno = recurso.visibilidad == 'interna'
    documentos = getattr(recurso, '_documentos_acceso', None)
    if documentos is None:
        documentos = list(recurso.documentos_expediente.select_related('exigido'))
    # La resolución de creación validada es un acto público de la unidad: la ve cualquiera,
    # siempre que su archivo haya pasado la verificación de seguridad.
    if documentos and all(
        documento.exigido.codigo == RESOLUCION_CREACION and documento.estado == 'validado' for documento in documentos
    ):
        return 'permitido' if recurso.seguridad_verificada or gestor else 'denegado'
    if documentos:
        from apps.gestion_unidades.presentation.permisos import puede_leer_expediente

        if not puede_leer_expediente(usuario, recurso.unidad):
            return 'denegado'
        gestor = True
        expediente_interno = recurso.visibilidad == 'interna'
    # La revisión de una entrega interna exige acceso al archivo por personal
    # autorizado. Eso no certifica antivirus ni habilita su publicación. Un archivo sin revisar nunca se
    # publica, tenga o no descripción: los adjuntos antiguos sin descripción también pasan por la revisión.
    if not recurso.seguridad_verificada and not expediente_interno and not recurso.es_microproyecto:
        return 'denegado'
    visibilidad = recurso.visibilidad
    if recurso.carpeta_id:
        visibilidad = _visibilidad_mas_restrictiva(
            visibilidad,
            _visibilidad_de_carpeta(recurso.carpeta),
        )
    if visibilidad == 'interna' and not gestor:
        return 'denegado'
    if visibilidad == 'restringida' and not usuario.is_authenticated:
        return 'identificacion'
    return 'permitido'


def resolucion_de_creacion(unidad, usuario, gestor):
    """La resolución de creación cargada en el expediente, para la ficha: validada la ve cualquiera."""
    documento = (
        DocumentoExpediente.objects.filter(unidad=unidad, exigido__codigo=RESOLUCION_CREACION, recurso__isnull=False)
        .exclude(estado__in=('pendiente', 'no_aplica'))
        .select_related('recurso')
        .order_by('-anio', '-version', '-pk')
        .first()
    )
    if documento is None or (documento.estado != 'validado' and not gestor):
        return None
    return {
        'documento': documento,
        'validada': documento.estado == 'validado',
        'fecha': documento.validado_en or documento.cargado_en,
        'nombre': documento.recurso.nombre or 'Resolución de creación',
        'url': (
            reverse('recurso_unidad', args=[documento.recurso_id])
            if _acceso_recurso(documento.recurso, usuario) == 'permitido' else ''
        ),
    }


def carpetas_publicables(unidad, usuario):
    """Devuelve una jerarquía sin carpetas vacías, separada por sección y módulo."""
    gestor = puede_gestionar_unidad(usuario, unidad)
    carpetas = list(
        CarpetaRecurso.objects.filter(unidad=unidad, activa=True, modulo_config__isnull=False, del_expediente=False)
        .select_related('modulo_config', 'carpeta_padre')
        .order_by('orden', 'nombre', 'pk')
    )
    ocultas = secciones_ocultas(unidad)
    contexto = _ContextoAccesoUnidad(unidad.pk, usuario, gestor, frozenset(ocultas))
    visibles = {
        carpeta.pk: carpeta
        for carpeta in carpetas
        if _jerarquia_activa(carpeta) and (gestor or _visibilidad_de_carpeta(carpeta) != 'interna')
        and _seccion_de_carpeta(carpeta) not in ocultas
    }
    for carpeta in visibles.values():
        carpeta.subcarpetas_publicas = []
        carpeta.recursos_publicos = []
        carpeta.total_recursos = 0

    recursos = (
        Recurso.objects.filter(unidad=unidad, activo=True, carpeta_id__in=visibles)
        .filter(Q(archivo__isnull=False) & ~Q(archivo='') | ~Q(url=''))
        .select_related('carpeta', 'carpeta__carpeta_padre', 'informe_mejora__unidad')
        .prefetch_related(Prefetch(
            'documentos_expediente',
            queryset=DocumentoExpediente.objects.select_related('exigido'),
            to_attr='_documentos_acceso',
        ))
        .order_by('orden', 'nombre', 'pk')
    )
    for recurso in recursos:
        # Todos proceden del filtro por esta unidad; reutilizarla no hace una lectura por archivo.
        recurso.unidad = unidad
        acceso = _acceso_recurso(recurso, usuario, contexto=contexto)
        if acceso == 'denegado':
            continue
        recurso.acceso_restringido = acceso == 'identificacion'
        recurso.url_contenido = reverse('recurso_unidad', args=[recurso.pk])
        visibles[recurso.carpeta_id].recursos_publicos.append(recurso)

    raices = []
    for carpeta in visibles.values():
        if carpeta.carpeta_padre_id in visibles:
            visibles[carpeta.carpeta_padre_id].subcarpetas_publicas.append(carpeta)
        else:
            raices.append(carpeta)

    def podar(carpeta):
        carpeta.subcarpetas_publicas = [
            hija for hija in carpeta.subcarpetas_publicas if podar(hija)
        ]
        carpeta.total_recursos = len(carpeta.recursos_publicos) + sum(
            hija.total_recursos for hija in carpeta.subcarpetas_publicas
        )
        return bool(carpeta.total_recursos)

    raices = [carpeta for carpeta in raices if podar(carpeta)]
    por_seccion = {}
    por_modulo = {}
    for carpeta in raices:
        if carpeta.seccion_planta:
            por_seccion.setdefault(carpeta.seccion_planta, []).append(carpeta)
        por_modulo.setdefault(carpeta.modulo_config.clave, []).append(carpeta)
    return {'raices': raices, 'por_seccion': por_seccion, 'por_modulo': por_modulo}


def _auditar_expediente(request, recurso, descargar):
    """Un documento del expediente no se abre sin dejar rastro: quién, cuándo y cuál."""
    documento = recurso.documentos_expediente.select_related('exigido').first()
    if documento is None:
        if hasattr(recurso, 'informe_mejora'):
            registrar_auditoria(
                request, unidad=recurso.unidad, accion='consultar', objeto=recurso.informe_mejora,
                descripcion=f"{'Descargó' if descargar else 'Abrió'} informe de mejora v{recurso.version}.")
        return
    registrar_auditoria(
        request, unidad=recurso.unidad, accion='consultar', objeto=documento,
        descripcion=(f"{'Descargó' if descargar else 'Abrió'} {documento.exigido.nombre} "
                     f"({documento.etiqueta_corte}, v{documento.version}) del expediente."),
    )


@require_POST
def navegador_recurso_view(request, recurso_id):
    """Abre, mantiene o cierra la sesión de navegador remoto del usuario para un sitio."""
    from apps.recursos.presentation import navegador_remoto
    from apps.recursos.models.recursos import SesionNavegador
    recurso = get_object_or_404(Recurso.objects.select_related('carpeta', 'carpeta__carpeta_padre'),
                                pk=recurso_id, activo=True, carpeta__activa=True)
    if _acceso_recurso(recurso, request.user) == 'denegado' or not navegador_remoto.disponible(recurso):
        raise Http404()
    if not request.user.is_authenticated:
        return JsonResponse({'estado': 'identificacion'}, status=401)
    accion = request.POST.get('accion', 'abrir')
    if accion == 'abrir':
        try:
            return JsonResponse(navegador_remoto.estado(navegador_remoto.abrir_sesion(recurso, request.user)))
        except navegador_remoto.LimiteAlcanzado:
            return JsonResponse({'estado': 'ocupado'}, status=429)
    sesion = get_object_or_404(SesionNavegador, token=request.POST.get('token', ''), usuario=request.user,
                               recurso=recurso)
    if accion == 'cerrar':
        navegador_remoto.cerrar(sesion)
        return JsonResponse({'estado': 'terminada'})
    navegador_remoto.registrar_actividad(sesion)
    return JsonResponse(navegador_remoto.estado(sesion))


def recurso_unidad_view(request, recurso_id, ruta='', *, original=False, nombre_url=None):
    """Sirve archivos y ZIP sin exponer los recursos restringidos en MEDIA_URL."""
    # El ID identifica el recurso; el nombre facilita compartirlo. Los enlaces
    # anteriores siguen funcionando aunque se cambie el título del contenido.
    # Lo que se publica vive en una carpeta activa; el recorrido 360° tiene su propia
    # entrada en «La planta por dentro» y no la necesita.
    recurso = get_object_or_404(
        Recurso.objects.select_related('unidad', 'carpeta', 'carpeta__carpeta_padre').filter(
            Q(carpeta__activa=True) | Q(carpeta__isnull=True, tipo_adjunto='recorrido_360')),
        pk=recurso_id,
        activo=True,
    )
    acceso = _acceso_recurso(recurso, request.user)
    if acceso == 'denegado':
        raise Http404()
    if acceso == 'identificacion':
        return redirect_to_login(request.get_full_path())
    if recurso.es_microproyecto:
        if ruta or original or request.GET.get('download'):
            raise Http404()
        destino = (recurso.microproyecto_url if recurso.microproyecto_hash == recurso.hash_sha256
                   and recurso.visibilidad == 'publica' and _visibilidad_de_carpeta(recurso.carpeta) == 'publica' else '')
        from apps.recursos.presentation.despliegue_microproyectos import estado_visible
        respuesta = render(request, 'portal/pages/unidades/microproyecto.html',
                           {'recurso': recurso, 'destino': destino, 'estado': estado_visible(recurso)['estado']})
        respuesta['X-Frame-Options'] = 'SAMEORIGIN'
        respuesta['Cache-Control'] = 'private, no-store'
        return respuesta
    if recurso.url:
        if ruta:
            raise Http404()
        if request.GET.get('visor') != '1':
            return redirect(recurso.url)
        # Dentro del visor: el sitio incrustado si su política lo permite; si no, un acceso directo.
        from apps.recursos.presentation import navegador_remoto
        from apps.recursos.presentation.sitios_externos import permite_incrustar
        es_pdf = urlsplit(recurso.url).path.lower().endswith('.pdf')
        incrustable = not es_pdf and permite_incrustar(recurso.url, f'{request.scheme}://{request.get_host()}')
        respuesta = render(request, 'portal/pages/unidades/sitio_externo.html', {
            'recurso': recurso, 'anfitrion': urlsplit(recurso.url).hostname, 'incrustable': incrustable,
            'es_pdf': es_pdf,
            'navegador': not es_pdf and not incrustable and navegador_remoto.disponible(recurso),
        })
        respuesta['X-Frame-Options'] = 'SAMEORIGIN'
        respuesta['Cache-Control'] = 'private, no-store'
        return respuesta
    if not recurso.archivo:
        raise Http404()

    # Los kits de datos revisados pueden descargarse explícitamente como paquete.
    # El visor sigue abriendo index.html; la autorización se comprobó antes de
    # resolver cualquier archivo y no cambia para los ZIP interactivos.
    descargar_dataset = (
        request.GET.get('download') == '1' and recurso.descargar and recurso.es_zip
        and recurso.tipo_adjunto == 'dataset' and recurso.seguridad_verificada
    )
    if descargar_dataset and ruta:
        raise Http404()
    if recurso.es_zip and not original and not descargar_dataset:
        relativa = PurePosixPath(ruta or 'index.html')
        if relativa.is_absolute() or '..' in relativa.parts:
            raise Http404()
        raiz = recurso.directorio_extraido.resolve()
        archivo = (raiz / Path(*relativa.parts)).resolve()
        if archivo != raiz and raiz not in archivo.parents:
            raise Http404()
    else:
        if ruta:
            raise Http404()
        archivo = Path(recurso.archivo.path).resolve()
    if not archivo.is_file():
        raise Http404()

    descargar = descargar_dataset or (
        request.GET.get('download') == '1' and recurso.descargar and not recurso.es_zip
    )
    # Una evidencia cargada por la unidad no ejecuta HTML/SVG/JS en el origen
    # de la plataforma cuando la Dirección la abre para revisarla.
    evidencia = recurso.documentos_expediente.exists()
    contenido_activo = es_contenido_activo(archivo.name)
    adjunto = descargar or (evidencia and contenido_activo)
    tipo, _ = mimetypes.guess_type(archivo.name)
    if descargar_dataset:
        tipo = 'application/zip'
    copia = None
    if evidencia and archivo.suffix.lower() == '.pdf':
        from apps.documentos.presentation.validacion_pdf import copia_para_recurso
        from django.core.exceptions import ValidationError
        try:
            copia = copia_para_recurso(recurso)
        except ValidationError as error:
            raise Http404('No se pudo verificar el documento aprobado.') from error
    if descargar:
        Recurso.objects.filter(pk=recurso.pk).update(veces_descargado=F('veces_descargado') + 1)
    _auditar_expediente(request, recurso, descargar)
    respuesta = FileResponse(
        BytesIO(copia) if copia is not None else archivo.open('rb'),
        as_attachment=adjunto,
        filename=archivo.name,
        content_type=tipo or 'application/octet-stream',
    )
    respuesta['X-Frame-Options'] = 'SAMEORIGIN'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store'
    if evidencia:
        respuesta['Content-Security-Policy'] = "sandbox; default-src 'none'"
    elif contenido_activo:
        # Los recorridos y recursos interactivos revisados ejecutan su contenido
        # en un origen opaco: nunca reciben acceso al DOM o la sesión del portal.
        # El backend rechaza Origin:null; no se permite enviar formularios.
        respuesta['Content-Security-Policy'] = (
            "sandbox allow-scripts allow-downloads; default-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'"
        )
    return respuesta
