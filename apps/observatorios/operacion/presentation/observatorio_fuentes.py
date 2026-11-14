"""De dónde salen los datos de un observatorio y cómo se mantienen al día, a la vista de todos.

La página de fuentes es el catálogo de bases y fuentes que alimentan los indicadores, con su nivel de acceso
(abierto, por solicitud, por convenio o con costo), su licencia, si tienen API y el estado de cada conexión
automática. Las actualizaciones recientes muestran qué valores entraron, cuándo y por qué vía. El historial de
correcciones se descarga en CSV: lo que se publicó y luego cambió nunca se borra.
"""
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.observatorios.operacion.models.observatorios import DescargaDatos, FuenteDatos, RevisionValor, ValorIndicador
from apps.directorio_unidades.models.core import Unidad

from apps.directorio_unidades.presentation.catalogos_publicos import _contexto
from apps.observatorios.operacion.presentation.observatorio import LICENCIA, _observatorio, indicadores_publicados
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

# Cómo entra un dato al observatorio, de la fuente a la descarga: la página de fuentes lo explica paso a paso.
FLUJO_DEL_DATO = (
    ('Captura', 'Se consulta sola una API pública (datos.gov.co, Global Forest Watch), se descarga el archivo '
                'del registro oficial (INEC, Banco Central, ministerios), se levanta una encuesta propia o llega el '
                'resultado de un laboratorio de la Universidad.'),
    ('Validación', 'Se revisa contra la fuente, se anonimiza lo que tenga datos personales y se marca como provisional '
                   'lo que la fuente aún puede corregir o el periodo que no ha terminado.'),
    ('Carga', 'La conexión automática guarda lo nuevo; lo demás se registra uno a uno o con la plantilla CSV desde el '
              'panel de gestión. Cada valor recuerda por qué vía entró.'),
    ('Publicación', 'Aparece al instante en los indicadores, los tableros, el boletín, los reportes por eje y los '
                    'datos abiertos (CSV, JSON y API) con licencia abierta.'),
    ('Historial', 'Si un valor publicado se corrige, la versión anterior queda en el historial de correcciones, que '
                  'cualquiera puede descargar.'),
    ('Medición de uso', 'Se cuentan las descargas y las solicitudes, sin guardar quién descarga.'),
)


@xframe_options_sameorigin
def fuentes_view(request, slug):
    """3.4 · El catálogo de fuentes y bases de datos, su nivel de acceso y el estado de sus conexiones automáticas."""
    unidad = _observatorio(slug)
    indicadores = list(indicadores_publicados(unidad).select_related('fuente_datos', 'linea', 'conector'))
    por_fuente = {}
    sin_catalogo = []
    for indicador in indicadores:
        if indicador.fuente_datos_id:
            por_fuente.setdefault(indicador.fuente_datos_id, []).append(indicador)
        else:
            sin_catalogo.append(indicador)
    fuentes = [{'fuente': fuente, 'indicadores': por_fuente[fuente.pk]}
               for fuente in FuenteDatos.objects.filter(pk__in=por_fuente).order_by('acceso', 'institucion', 'nombre')]
    conectores = [indicador.conector for indicador in indicadores if hasattr(indicador, 'conector')]
    accesos = {clave: sum(1 for fila in fuentes if fila['fuente'].acceso == clave) for clave, _ in FuenteDatos.ACCESOS}
    return render(request, 'portal/pages/unidades/observatorio/fuentes.html', {
        **_contexto(unidad, 'fuentes', request.user),
        'fuentes': fuentes,
        'sin_catalogo': sin_catalogo,
        'conectores': conectores,
        'accesos': [(titulo, accesos[clave]) for clave, titulo in FuenteDatos.ACCESOS],
        'flujo': FLUJO_DEL_DATO,
        'encuestas': unidad.encuestas_observatorio.filter(activa=True),
        'puede_sincronizar': puede_gestionar_unidad(request.user, unidad),
    })


@xframe_options_sameorigin
def actualizaciones_view(request, slug):
    """3.3 · Los últimos valores que entraron y las últimas correcciones, con su vía de entrada."""
    unidad = _observatorio(slug)
    valores = (ValorIndicador.objects.filter(indicador__unidad=unidad, indicador__publicado=True)
               .select_related('indicador').order_by('-modificado')[:40])
    revisiones = (RevisionValor.objects.filter(valor__indicador__unidad=unidad, valor__indicador__publicado=True)
                  .select_related('valor__indicador')[:20])
    por_origen = {}
    for valor in ValorIndicador.objects.filter(indicador__unidad=unidad, indicador__publicado=True).only('origen'):
        por_origen[valor.get_origen_display()] = por_origen.get(valor.get_origen_display(), 0) + 1
    return render(request, 'portal/pages/unidades/observatorio/actualizaciones.html', {
        **_contexto(unidad, 'actualizaciones', request.user),
        'valores': valores,
        'revisiones': revisiones,
        'por_origen': sorted(por_origen.items(), key=lambda par: -par[1]),
    })


def historial_csv_view(request, slug):
    """El historial de correcciones en CSV: qué valor se publicó, a qué cambió, cuándo y por qué vía."""
    unidad = _observatorio(slug)
    DescargaDatos.registrar(unidad, 'csv', 'historial')
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{unidad.slug}-historial-de-correcciones.csv"'
    respuesta.write('﻿')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(['fecha_correccion', 'indicador', 'codigo', 'periodo', 'territorio', 'valor_anterior',
                       'valor_nuevo', 'via'])
    for revision in (RevisionValor.objects.filter(valor__indicador__unidad=unidad, valor__indicador__publicado=True)
                     .select_related('valor__indicador').order_by('fecha')):
        valor = revision.valor
        escritor.writerow([revision.fecha.isoformat(timespec='minutes'), valor.indicador.nombre, valor.indicador.codigo,
                           valor.periodo, valor.territorio, str(revision.anterior.normalize()).replace('.', ','),
                           str(revision.nuevo.normalize()).replace('.', ','), revision.get_origen_display()])
    escritor.writerow([])
    escritor.writerow([f'Fuente: {unidad.nombre}. Licencia {LICENCIA[0]} ({LICENCIA[1]}).'])
    return respuesta


@login_required
@require_POST
def sincronizar_view(request, slug):
    """Quien gestiona el observatorio ejecuta ahora sus conexiones automáticas y vuelve a donde estaba."""
    from apps.observatorios.operacion.presentation.conectores_observatorio import pendientes, sincronizar

    unidad = get_object_or_404(Unidad, slug=slug, dependencia='observatorios')
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona el observatorio actualiza sus datos.')
    conectores = pendientes(unidad, todos=True)
    nuevos = corregidos = errores = 0
    for conector in conectores:
        n, c = sincronizar(conector)
        nuevos, corregidos, errores = nuevos + n, corregidos + c, errores + (conector.estado == 'error')
    texto = f'{len(conectores)} conexiones consultadas: {nuevos} valores nuevos y {corregidos} corregidos.'
    (messages.warning if errores else messages.success)(
        request, texto + (f' {errores} con error: revise su resultado en Fuentes.' if errores else ''))
    destino = request.POST.get('volver', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destino = f"{reverse('gestion_unidad', args=[slug])}?view=obs_indicadores"
    return redirect(destino)
