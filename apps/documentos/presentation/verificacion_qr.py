import hashlib
from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoExpediente
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from .aprobacion_en_linea import estado_constancia, enviar_documento_qr


@require_GET
@xframe_options_sameorigin
def verificar_documento_view(request, token):
    c = get_object_or_404(ConstanciaDocumento.objects.select_related('documento__unidad', 'recurso'), token=token)
    estado = estado_constancia(c)
    hashes = [c.sha256]
    try:
        with c.recurso.archivo.open('rb') as f:
            contenido = f.read()
            if hashlib.sha256(contenido).hexdigest() != c.sha256:
                estado = 'NO VERIFICABLE'
            else:
                from .validacion_pdf import copia_aprobada, copia_preparada
                copia=copia_aprobada(contenido,c) if c.aprobado_en else copia_preparada(contenido,c)
                hashes.append(hashlib.sha256(copia).hexdigest())
                hashes.extend([c.sha256_aprobado, *c.presentaciones.values_list('sha256', flat=True)])
    except (OSError, ValueError, ValidationError):
        estado = 'NO VERIFICABLE'
    puede_ver = request.user.is_authenticated and puede_operar_modulo_unidad(request.user, c.documento.unidad, 'reportes')
    respuesta = render(request, 'documentos/verificar_documento.html', dict(constancia=c, estado=estado,
        puede_ver=puede_ver, archivo_integro=estado != 'NO VERIFICABLE', hashes=' '.join(hashes)))
    respuesta['Cache-Control'] = 'no-store'
    respuesta['X-Robots-Tag'] = 'noindex, nofollow'
    respuesta['Referrer-Policy'] = 'no-referrer'
    return respuesta


@login_required
@require_POST
def enviar_documento_view(request, slug, documento_id):
    d = get_object_or_404(DocumentoExpediente.objects.select_related('unidad', 'exigido'),
        pk=documento_id, unidad__slug=slug)
    try:
        enviar_documento_qr(d, request.user, token=request.POST.get('token'), version=request.POST.get('version'), request=request)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, 'Documento enviado a Dirección. Puedes consultar su aprobación con el código QR.')
    return redirect(reverse('gestion_expediente_unidad', args=[slug]) + '?' + urlencode(dict(anio=d.anio, corte=d.corte)))
