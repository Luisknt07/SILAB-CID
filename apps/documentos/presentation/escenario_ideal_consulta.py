"""Consulta local de una prueba ya ejecutada, sin escribir registros operativos."""
import hashlib
import json
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.escenario_ideal_exportacion import directorio_escenario
from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
from apps.gestion_unidades.presentation.permisos import es_receptor_de, puede_operar_modulo_unidad


def _manifiesto(slug, anio, corte):
    if (not settings.DEBUG or getattr(settings, 'REVISION_TIPOLOGIAS_ACTIVA', False)
            or corte not in ('A', 'B') or not 2000 <= anio <= 2200):
        return None
    ruta = directorio_escenario(slug, anio, corte) / 'manifiesto.json'
    try:
        datos = json.loads(ruta.read_text(encoding='utf8'))
    except (OSError, ValueError):
        return None
    if not (isinstance(datos, dict) and datos.get('version') == 1 and datos.get('es_prueba') is True
            and isinstance(datos.get('unidad'), dict) and datos['unidad'].get('slug') == slug and datos.get('anio') == anio
            and datos.get('corte') == corte):
        return None
    documentos = datos.get('documentos')
    if not isinstance(documentos, list) or not documentos:
        return None
    codigos = set()
    for documento in documentos:
        if not (isinstance(documento, dict) and isinstance(documento.get('codigo'), str)
                and re.fullmatch(r'[A-Z0-9-]+', documento['codigo'])
                and isinstance(documento.get('archivo'), str) and documento['archivo']
                and isinstance(documento.get('sha256'), str)
                and re.fullmatch(r'[a-f0-9]{64}', documento['sha256'])
                and documento['codigo'] not in codigos):
            return None
        codigos.add(documento['codigo'])
    return datos


def escenario_disponible(unidad, anio, corte):
    return bool(es_laboratorio(unidad) and _manifiesto(unidad.slug, anio, corte))


def _consulta(request, slug):
    if not settings.DEBUG:
        raise Http404
    unidad = get_object_or_404(Unidad, slug=slug)
    if not es_laboratorio(unidad):
        raise Http404
    if not (puede_operar_modulo_unidad(request.user, unidad, 'reportes') or es_receptor_de(request.user, unidad)):
        raise PermissionDenied('No tienes acceso a los reportes de este laboratorio.')
    try:
        anio = int(request.GET.get('anio', 2026))
    except ValueError:
        raise Http404 from None
    corte = request.GET.get('corte') or 'B'
    datos = _manifiesto(slug, anio, corte)
    if datos is None:
        raise Http404('No hay un ensayo completo disponible para este período.')
    return unidad, datos


@login_required
@require_GET
def escenario_ideal_view(request, slug):
    unidad, datos = _consulta(request, slug)
    return render(request, 'portal/pages/unidades/gestion/escenario_ideal.html',
                  dict(unidad=unidad, escenario=datos))


@login_required
@require_GET
def escenario_ideal_pdf_view(request, slug, codigo):
    unidad, datos = _consulta(request, slug)
    documento = next((d for d in datos['documentos'] if d['codigo'] == codigo), None)
    if documento is None:
        raise Http404
    carpeta = directorio_escenario(slug, datos['anio'], datos['corte']).resolve()
    archivo = (carpeta / documento['archivo']).resolve()
    if carpeta not in archivo.parents or not archivo.is_file():
        raise Http404
    with archivo.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != documento['sha256']:
            raise Http404('La copia de prueba cambió; vuelve a generar el ensayo.')
    respuesta = FileResponse(archivo.open('rb'), content_type='application/pdf',
        as_attachment=request.GET.get('descargar') == '1', filename='PRUEBA-' + codigo + '.pdf')
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta
