"""Consulta y remisión interna de necesidades evaluadas a sus centros de costo."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest, PermissionDenied, ValidationError
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.necesidades import RemisionNecesidades
from .necesidades_decanato import lectura_necesidades, render_necesidades_pdf, render_necesidades_xlsx
from .necesidades_remision import contenido_remision, puede_leer_remision, remitir_necesidades
from .asignacion_necesidades import (presupuesto_actual, comparar_demanda, filas_escenario,
    registrar_presupuesto, registrar_escenario, verificar_captura, excel_escenario)


def _acceso(usuario):
    """Consulta la titularidad actual; no basta con administrar una unidad."""
    if not usuario or not getattr(usuario, 'is_authenticated', False) or not getattr(usuario, 'pk', None):
        raise PermissionDenied('Ingresa con una cuenta institucional activa.')
    vigente = get_user_model().objects.filter(pk=usuario.pk, is_active=True, is_staff=True).first()
    if vigente is None:
        raise PermissionDenied('Esta consulta requiere una cuenta institucional activa.')
    dependencias = DependenciaAcademica.objects.all()
    if not vigente.is_superuser:
        dependencias = dependencias.filter(activa=True, receptores=vigente)
        if not dependencias.exists():
            raise PermissionDenied('La consulta corresponde a Dirección y a los receptores de las dependencias.')
    return vigente, dependencias.distinct().order_by('nombre', 'pk')


def _entero(valor, minimo, maximo, etiqueta):
    texto = str(valor or '')
    if (not texto.isascii() or not texto.isdigit() or len(texto) > len(str(maximo))
            or not minimo <= int(texto) <= maximo):
        raise BadRequest(f'Selecciona {etiqueta} válido.')
    return int(texto)


def _url(request, ejercicio, dependencia=None, remision=None):
    datos = {'ejercicio': ejercicio}
    if dependencia is not None:
        datos['dependencia'] = getattr(dependencia, 'pk', dependencia)
    if remision is not None:
        datos['remision'] = getattr(remision, 'pk', remision)
    return f'{request.path}?{urlencode(datos)}'


@never_cache
@require_http_methods(['GET', 'POST'])
def necesidades_decanato_view(request, *, admin_site):
    """Dirección ve la lectura vigente; el receptor ve únicamente lo remitido."""
    usuario, permitidas = _acceso(request.user)
    direccion = usuario.is_superuser
    seleccion = request.POST if request.method == 'POST' else request.GET
    remision = None
    if seleccion.get('remision'):
        identificador = _entero(seleccion['remision'], 1, 2**63 - 1, 'una remisión')
        remision = RemisionNecesidades.objects.select_related('dependencia', 'remitido_por').filter(pk=identificador).first()
        if remision is None or not puede_leer_remision(usuario, remision):
            raise Http404('La remisión no está disponible.')
    ejercicio = _entero(seleccion.get('ejercicio') or (remision.anio_ejecucion if remision else timezone.localdate().year + 1),
                         2021, 2100, 'un año de compras')
    dependencia_valor = seleccion.get('dependencia') or (remision.dependencia_id if remision else None)
    dependencia = None
    if dependencia_valor is not None:
        dependencia_id = _entero(dependencia_valor, 1, 2**63 - 1, 'una dependencia')
        dependencia = permitidas.filter(pk=dependencia_id).first()
        if dependencia is None:
            raise PermissionDenied('No tienes acceso a la dependencia seleccionada.')
    elif not direccion:
        ultima = RemisionNecesidades.objects.filter(dependencia__in=permitidas, anio_ejecucion=ejercicio).first()
        dependencia = permitidas.filter(pk=ultima.dependencia_id).first() if ultima else permitidas.first()
    if remision and (remision.anio_ejecucion != ejercicio or remision.dependencia_id != getattr(dependencia, 'pk', None)):
        raise Http404('La remisión no corresponde al año y a la dependencia seleccionados.')
    if request.method == 'POST':
        accion = seleccion.get('accion')
        if accion in ('presupuesto', 'escenario'):
            if dependencia is None:
                raise BadRequest('Selecciona una dependencia.')
            try:
                if accion == 'presupuesto':
                    registrar_presupuesto(dependencia, ejercicio, usuario,
                        disponible=seleccion.get('disponible'), referencia=seleccion.get('referencia'),
                        concentracion=seleccion.get('concentracion'))
                    messages.success(request, 'Referencia presupuestaria archivada. Las revisiones anteriores se conservan.')
                    return HttpResponseRedirect(_url(request, ejercicio, dependencia, remision))
                if remision is None:
                    raise BadRequest('Selecciona la copia remitida que servirá de base para el escenario.')
                presupuesto = presupuesto_actual(dependencia, ejercicio)
                if presupuesto is None or str(presupuesto.pk) != seleccion.get('presupuesto_id'):
                    raise ValidationError('Selecciona la referencia presupuestaria actual y recarga el informe.')
                cantidades = {k.removeprefix('cantidad_'): v for k, v in seleccion.items() if k.startswith('cantidad_')}
                escenario = registrar_escenario(remision, presupuesto, usuario, cantidades,
                    distribucion=seleccion.get('distribucion'), excepcion=seleccion.get('excepcion'))
                messages.success(request, 'Escenario archivado para revisión; no reserva fondos ni ejecuta compras.')
                return HttpResponseRedirect(_url(request, ejercicio, dependencia, remision) + f'&escenario={escenario.pk}')
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
        elif accion != 'remitir':
            raise BadRequest('Selecciona una acción válida.')
        else:
            if not direccion:
                raise PermissionDenied('Solo Dirección puede remitir las necesidades evaluadas.')
            if dependencia is None:
                raise BadRequest('Selecciona una dependencia para remitir su informe.')
            if request.GET.get('remision') or seleccion.get('remision'):
                raise BadRequest('Vuelve a la lectura actual antes de preparar otra remisión.')
            try:
                remitida = remitir_necesidades(ejercicio - 1, dependencia, usuario)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
                return HttpResponseRedirect(_url(request, ejercicio, dependencia))
            messages.success(request, 'Informe remitido internamente a la dependencia. La copia queda archivada para su consulta y descarga.')
            return HttpResponseRedirect(_url(request, ejercicio, dependencia, remitida))
    remisiones = RemisionNecesidades.objects.filter(dependencia__in=permitidas, anio_ejecucion=ejercicio)
    if dependencia:
        remisiones = remisiones.filter(dependencia=dependencia)
    remisiones = list(remisiones.select_related('dependencia', 'remitido_por'))
    if not direccion and remision is None:
        remision = remisiones[0] if remisiones else None
    lectura = None
    integridad_error = ''
    if remision:
        try:
            lectura = contenido_remision(remision)
        except ValidationError as error:
            integridad_error = ' '.join(error.messages)
    elif direccion:
        lectura = lectura_necesidades(ejercicio - 1, usuario, dependencia=dependencia)
    presupuesto = None
    try:
        presupuesto = presupuesto_actual(dependencia, ejercicio) if dependencia else None
    except ValidationError as error:
        integridad_error = ' '.join(error.messages)
    comparacion = comparar_demanda(lectura, presupuesto) if lectura else None
    escenarios = list(remision.escenarios.select_related('presupuesto', 'registrado_por')) if remision else []
    escenario = escenarios[0] if escenarios else None
    if request.GET.get('escenario'):
        identificador = _entero(request.GET['escenario'], 1, 2**63 - 1, 'un escenario')
        escenario = next((e for e in escenarios if e.pk == identificador), None)
        if escenario is None:
            raise Http404('El escenario no corresponde a la copia remitida.')
    escenario_datos = None
    try:
        escenario_datos = verificar_captura(escenario) if escenario else None
    except ValidationError as error:
        integridad_error = ' '.join(error.messages)
    formato = request.GET.get('formato', '')
    if formato:
        if formato == 'escenario-xlsx':
            if escenario_datos is None:
                raise Http404('Selecciona un escenario archivado.')
            respuesta = HttpResponse(excel_escenario(escenario), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            respuesta['Content-Disposition'] = f'attachment; filename="escenario-{escenario.pk}-compras-{ejercicio}.xlsx"'
            return respuesta
        if formato not in ('pdf', 'xlsx'):
            raise BadRequest('Selecciona PDF o Excel para descargar.')
        if lectura is None:
            raise Http404('No hay un informe remitido disponible para descargar.')
        render, mime = ((render_necesidades_pdf, 'application/pdf') if formato == 'pdf' else
                        (render_necesidades_xlsx, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
        respuesta = HttpResponse(render(lectura), content_type=mime)
        respuesta['Content-Disposition'] = f'attachment; filename="necesidades-{ejercicio}-centros-de-costo.{formato}"'
        return respuesta
    actual_url = _url(request, ejercicio, dependencia)
    fuente_url = _url(request, ejercicio, dependencia, remision)
    historial = [dict(remision=r, url=_url(request, ejercicio, r.dependencia_id, r)) for r in remisiones]
    tiene_destinatarios = bool(dependencia and dependencia.receptores.filter(is_active=True).exists())
    filas_propuesta = filas_escenario(lectura) if remision and lectura else []
    for fila in filas_propuesta:
        fila['cantidad_propuesta'] = seleccion.get('cantidad_' + fila['clave'], '0') if request.method == 'POST' else '0'
    contexto = dict(admin_site.each_context(request), title='Necesidades de compras por centro de costo',
        es_direccion=direccion, ejercicio=ejercicio, ejercicios=range(2021, 2101),
        dependencias=permitidas, dependencia_seleccionada=dependencia,
        lectura=lectura, remision=remision, historial_remisiones=historial,
        integridad_error=integridad_error, actual_url=actual_url,
        tiene_destinatarios=tiene_destinatarios,
        presupuesto=presupuesto, comparacion=comparacion, filas_propuesta=filas_propuesta,
        escenarios=escenarios, escenario=escenario, escenario_datos=escenario_datos,
        escenario_excel_url=fuente_url + (f'&escenario={escenario.pk}&formato=escenario-xlsx' if escenario else ''),
        formulario=seleccion if request.method == 'POST' else {},
        pdf_url=fuente_url + '&formato=pdf', xlsx_url=fuente_url + '&formato=xlsx',
        puede_remitir=bool(direccion and dependencia and dependencia.activa and tiene_destinatarios and not remision
                          and lectura and lectura.get('resumen', {}).get('evaluadas')))
    return TemplateResponse(request, 'admin/gestion_unidades/reporteoperativounidad/necesidades.html', contexto)
