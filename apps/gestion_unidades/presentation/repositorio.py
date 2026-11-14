"""Repositorio público, adjuntos de ficha y artefactos externos."""

import csv
import io
import json
import zipfile
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.repositorio import ArtefactoExterno, ResultadoArtefacto
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.formacion.presentation.recursos_publicos import _acceso_recurso


def _ficha_de(objeto):
    if objeto is None or not getattr(objeto, 'pk', None):
        return None
    return FichaContenido.objects.filter(
        content_type=ContentType.objects.get_for_model(objeto),
        object_id=objeto.pk,
    ).first()


def adjuntos_de_ficha(objeto, unidad, usuario):
    """Documentos visibles que respaldan el objeto sin duplicar sus datos."""
    ficha = _ficha_de(objeto)
    if ficha is None:
        return []
    adjuntos = Recurso.objects.filter(
        unidad=unidad,
        ficha=ficha,
        activo=True,
        estado='vigente',
    ).select_related('carpeta', 'carpeta__carpeta_padre').order_by('tipo_adjunto', 'orden', 'nombre')
    gestor = puede_gestionar_unidad(usuario, unidad)
    visibles = []
    for adjunto in adjuntos:
        if not gestor and (not adjunto.seguridad_verificada or not adjunto.metadatos_completos):
            continue
        acceso = _acceso_recurso(adjunto, usuario)
        if acceso == 'denegado':
            continue
        adjunto.acceso_restringido = acceso == 'identificacion'
        adjunto.url_contenido = reverse('recurso_unidad', args=[adjunto.pk])
        visibles.append(adjunto)
    return visibles


def contexto_adjuntos(objeto, unidad, usuario):
    ficha = _ficha_de(objeto)
    return {
        'adjuntos_ficha': adjuntos_de_ficha(objeto, unidad, usuario),
        'ficha_adjuntos': ficha,
        'puede_subir_adjuntos': puede_gestionar_unidad(usuario, unidad),
        'subir_adjunto_url': (
            reverse('admin:gestion_unidades_adjunto_add')
            + f'?unidad={unidad.pk}&ficha={ficha.pk}'
            if ficha else ''
        ),
    }


def artefactos_publicos(unidad, usuario, receta=None):
    gestor = puede_gestionar_unidad(usuario, unidad)
    autenticado = getattr(usuario, 'is_authenticated', False)
    consulta = ArtefactoExterno.objects.filter(unidad=unidad)
    if receta is not None:
        consulta = consulta.filter(receta=receta)
    if not gestor:
        visibilidad = Q(visibilidad='publica')
        if autenticado:
            visibilidad |= Q(visibilidad='restringida')
        consulta = artefactos_vigentes(consulta.filter(estado='publicado')).filter(visibilidad)
    return consulta.select_related('familia', 'receta', 'equipo', 'area').prefetch_related('archivos')


def artefactos_vigentes(queryset):
    """Aplica la misma vigencia efectiva a todas las superficies públicas."""
    hoy = timezone.localdate()
    return queryset.filter(
        posiblemente_desactualizado=False,
        vigente_desde__lte=hoy,
    ).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy))


def _valor_contrato(artefacto, campo):
    receta = artefacto.receta
    if receta is None:
        return None
    simples = {
        'Receta.codigo': receta.codigo,
        'Receta.cantidad_base': str(receta.cantidad_base),
        'Receta.unidad_base': receta.unidad_base,
        'Receta.rendimiento_esperado': str(receta.rendimiento_esperado),
        'Receta.duracion_estandar_min': receta.duracion_estandar_min,
        'Operacion.tiempo_maquina': [
            {'orden': etapa.orden, 'valor_min': etapa.duracion_min}
            for etapa in receta.etapas.all()
        ],
        'Operacion.tiempo_setup': [
            {
                'orden': etapa.orden,
                'valor_min': str(etapa.equipo.tiempo_setup) if etapa.equipo and etapa.equipo.tiempo_setup is not None else None,
            }
            for etapa in receta.etapas.select_related('equipo')
        ],
        'OperacionSalida.rendimiento_pct': [
            {'orden': etapa.orden, 'valor': str(etapa.rendimiento_pct)}
            for etapa in receta.etapas.all()
        ],
        'Equipo.capacidad_util_max': [
            {'equipo': etapa.equipo.codigo, 'valor': str(etapa.equipo.capacidad_util_max)}
            for etapa in receta.etapas.select_related('equipo')
            if etapa.equipo and etapa.equipo.capacidad_util_max is not None
        ],
        'Equipo.MTBF': [
            {'equipo': etapa.equipo.codigo, 'valor_h': str(etapa.equipo.mtbf)}
            for etapa in receta.etapas.select_related('equipo')
            if etapa.equipo and etapa.equipo.mtbf is not None
        ],
        'Equipo.MTTR': [
            {'equipo': etapa.equipo.codigo, 'valor_h': str(etapa.equipo.mttr)}
            for etapa in receta.etapas.select_related('equipo')
            if etapa.equipo and etapa.equipo.mttr is not None
        ],
    }
    return simples.get(campo)


def paquete_entrada(artefacto):
    """Solo exporta los campos declarados en el contrato del artefacto."""
    return {
        'artefacto': artefacto.codigo,
        'version': artefacto.version,
        'proceso': artefacto.receta.codigo if artefacto.receta_id else None,
        'contrato': {
            campo: _valor_contrato(artefacto, campo)
            for campo in artefacto.entradas_esperadas
        },
        'salidas_esperadas': artefacto.salidas_devueltas,
        'esquema': artefacto.esquema,
    }


def _xlsx_contrato(datos):
    """Crea un XLSX mínimo y estándar sin obligar a instalar otra biblioteca."""
    filas = [('Campo', 'Valor JSON')] + [
        (campo, json.dumps(valor, ensure_ascii=False))
        for campo, valor in datos['contrato'].items()
    ]
    def celda(valor, columna, fila):
        return f'<c r="{columna}{fila}" t="inlineStr"><is><t>{escape(str(valor))}</t></is></c>'
    filas_xml = ''.join(
        f'<row r="{indice}">{celda(a, "A", indice)}{celda(b, "B", indice)}</row>'
        for indice, (a, b) in enumerate(filas, start=1)
    )
    archivos = {
        '[Content_Types].xml': '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Contrato" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': f'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{filas_xml}</sheetData></worksheet>',
    }
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as libro:
        for nombre, contenido in archivos.items():
            libro.writestr(nombre, contenido.encode('utf-8'))
    return salida.getvalue()


@xframe_options_sameorigin
def repositorio_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    adjuntos = Recurso.objects.filter(
        unidad=unidad,
        activo=True,
        estado='vigente',
        ficha__isnull=True,
    ).select_related('carpeta').order_by('tipo_adjunto', 'nombre')
    visibles = []
    for adjunto in adjuntos:
        gobernado = adjunto.seguridad_verificada and adjunto.metadatos_completos
        if gestor or (gobernado and _acceso_recurso(adjunto, request.user) == 'permitido'):
            adjunto.url_contenido = reverse('recurso_unidad', args=[adjunto.pk])
            visibles.append(adjunto)
    artefactos = list(artefactos_publicos(unidad, request.user).filter(
        receta__isnull=True, equipo__isnull=True, area__isnull=True,
    ))
    return render(request, 'portal/pages/unidades/repositorio/unidad.html', {
        'unidad': unidad,
        'adjuntos': visibles,
        'artefactos': artefactos,
        'puede_gestionar': gestor,
        'subir_url': reverse('admin:gestion_unidades_adjunto_add') + f'?unidad={unidad.pk}',
    })


@xframe_options_sameorigin
def artefacto_externo_view(request, slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    artefacto = get_object_or_404(ArtefactoExterno.objects.select_related(
        'unidad', 'familia', 'receta', 'equipo', 'area', 'evidencia_validacion',
    ).prefetch_related('archivos'), unidad=unidad, codigo=codigo)
    gestor = puede_gestionar_unidad(request.user, unidad)
    if not gestor and not artefacto.publicable:
        raise Http404()
    if artefacto.visibilidad == 'restringida' and not request.user.is_authenticated:
        return redirect(f'{reverse("account_login")}?next={request.get_full_path()}')
    archivos_visibles = []
    for archivo in artefacto.archivos.all():
        if gestor or (
            archivo.seguridad_verificada and archivo.metadatos_completos
            and _acceso_recurso(archivo, request.user) != 'denegado'
        ):
            archivos_visibles.append(archivo)
    evidencia_url = ''
    evidencia = artefacto.evidencia_validacion
    if evidencia and (
        gestor
        or (
            evidencia.seguridad_verificada
            and evidencia.metadatos_completos
            and _acceso_recurso(evidencia, request.user) != 'denegado'
        )
    ):
        evidencia_url = reverse('recurso_unidad', args=[evidencia.pk])
    return render(request, 'portal/pages/unidades/repositorio/artefacto.html', {
        'unidad': unidad,
        'artefacto': artefacto,
        'archivos_visibles': archivos_visibles,
        'puede_gestionar': gestor,
        'evidencia_url': evidencia_url,
        'resultados_visibles': artefacto.resultados.select_related('importado_por').all() if gestor else (),
    })


def exportar_paquete_artefacto_view(request, slug, codigo):
    artefacto = get_object_or_404(
        ArtefactoExterno.objects.select_related('unidad', 'receta'),
        unidad__slug=slug,
        codigo=codigo,
    )
    gestor = puede_gestionar_unidad(request.user, artefacto.unidad)
    if not gestor and not artefacto.publicable:
        raise Http404()
    if artefacto.visibilidad == 'restringida' and not request.user.is_authenticated:
        return redirect(f'{reverse("account_login")}?next={request.get_full_path()}')
    if artefacto.nivel_integracion not in (1, 2):
        raise Http404('Los artefactos depositados no tienen contrato de datos.')
    datos = paquete_entrada(artefacto)
    if artefacto.formato_intercambio == 'csv':
        respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
        respuesta['Content-Disposition'] = f'attachment; filename="{artefacto.codigo}-entrada.csv"'
        respuesta.write('\ufeff')
        escritor = csv.writer(respuesta, delimiter=';')
        escritor.writerow(('Campo', 'Valor JSON'))
        for campo, valor in datos['contrato'].items():
            escritor.writerow((campo, json.dumps(valor, ensure_ascii=False)))
    elif artefacto.formato_intercambio == 'xlsx':
        respuesta = HttpResponse(
            _xlsx_contrato(datos),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        respuesta['Content-Disposition'] = f'attachment; filename="{artefacto.codigo}-entrada.xlsx"'
    else:
        respuesta = JsonResponse(datos, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        respuesta['Content-Disposition'] = f'attachment; filename="{artefacto.codigo}-entrada.json"'
    ArtefactoExterno.objects.filter(pk=artefacto.pk).update(veces_descargado=F('veces_descargado') + 1)
    return respuesta


@login_required
def importar_resultado_artefacto_view(request, slug, codigo):
    artefacto = get_object_or_404(ArtefactoExterno, unidad__slug=slug, codigo=codigo)
    if not puede_gestionar_unidad(request.user, artefacto.unidad):
        raise PermissionDenied
    if request.method != 'POST' or 'archivo' not in request.FILES:
        return redirect('artefacto_externo', slug=slug, codigo=codigo)
    resultado = ResultadoArtefacto(
        artefacto=artefacto,
        archivo=request.FILES['archivo'],
        importado_por=request.user,
    )
    try:
        resultado.full_clean()
    except ValidationError as error:
        messages.error(request, 'No se importó el resultado: ' + ' '.join(error.messages))
        return redirect('artefacto_externo', slug=slug, codigo=codigo)
    resultado.save()
    ArtefactoExterno.objects.filter(pk=artefacto.pk).update(
        ultima_ejecucion=resultado.importado_en,
    )
    return redirect('artefacto_externo', slug=slug, codigo=codigo)


@login_required
def candidatos_promocion_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied
    duplicados = list(
        Recurso.objects.filter(unidad=unidad).exclude(hash_sha256='')
        .values('hash_sha256').annotate(total=Count('pk')).filter(total__gt=1)
        .order_by('-total')
    )
    titulos = list(
        Recurso.objects.filter(unidad=unidad).values('nombre')
        .annotate(total=Count('ficha', distinct=True)).filter(total__gt=5)
        .order_by('-total', 'nombre')
    )
    descargados = Recurso.objects.filter(unidad=unidad).order_by('-veces_descargado', 'nombre')[:20]
    return render(request, 'portal/pages/unidades/repositorio/candidatos.html', {
        'unidad': unidad,
        'duplicados': duplicados,
        'titulos': titulos,
        'descargados': descargados,
    })
