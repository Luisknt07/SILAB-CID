"""Control privado de cursos de una unidad, sin emitir certificados al consultar.

Los indicadores se agregan en la base de datos. El seguimiento detallado se
calcula sólo para la página visible o por lotes al pedir un reporte explícito.
"""
import copy
import csv
import re
from io import BytesIO
from itertools import islice
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.aula_cursos import ICONOS_DE_LECCION
from apps.formacion.presentation.cursos import _numero_pagina, puede_crear_cursos
from apps.formacion.presentation.seguimiento_cursos import seguimiento_de
from apps.gestion_unidades.presentation.seguimiento_reportes import _nota, _respuesta_privada, celda_csv_segura

ESTADOS = (
    ('', 'Todos los estados'),
    ('pendiente', 'Por aceptar'),
    ('aceptada', 'Inscripciones aceptadas'),
    ('rechazada', 'Inscripciones rechazadas'),
    ('retirada', 'Inscripciones retiradas'),
    ('aprobado', 'Curso aprobado'),
    ('reprobado', 'Sin oportunidades para aprobar'),
    ('por_calificar', 'Con entregas por revisar'),
    ('certificado', 'Con certificado vigente'),
)
PARAMETROS = ('curso_cursos', 'grupo_cursos', 'estado_cursos', 'q_cursos')
POR_PAGINA = 25


def _permiso(request, unidad):
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Sólo quien gestiona los cursos de esta unidad puede consultar su control y reportes.')


def _identificador(valor):
    if not re.fullmatch(r'[0-9]{1,18}', valor) or int(valor) < 1:
        raise Http404('El curso o grupo solicitado no es válido.')
    return int(valor)


def _filtros(request, unidad):
    """Resuelve todos los objetos dentro de la unidad antes de usarlos."""
    cursos = Curso.objects.filter(unidad=unidad)
    grupos = EdicionCurso.objects.filter(curso__unidad=unidad).select_related('curso')
    curso_id = (request.GET.get('curso_cursos') or '').strip()
    grupo_id = (request.GET.get('grupo_cursos') or '').strip()
    curso = get_object_or_404(cursos, pk=_identificador(curso_id)) if curso_id else None
    grupo = get_object_or_404(grupos, pk=_identificador(grupo_id)) if grupo_id else None
    if grupo and curso and grupo.curso_id != curso.pk:
        raise Http404('El grupo no pertenece al curso seleccionado.')
    estado = (request.GET.get('estado_cursos') or '').strip()
    if estado not in dict(ESTADOS):
        raise Http404('El estado de inscripción solicitado no es válido.')
    texto = ''.join(caracter for caracter in (request.GET.get('q_cursos') or '')
                    if ord(caracter) >= 32 and ord(caracter) != 127)
    busqueda = ' '.join(texto.split())[:120]
    return {'curso': str(curso.pk) if curso else '', 'grupo': str(grupo.pk) if grupo else '',
            'estado': estado, 'q': busqueda, 'curso_objeto': curso, 'grupo_objeto': grupo}


def _inscripciones_anotadas(unidad):
    """La aprobación exige matrícula aceptada y todas las obligatorias actuales.

    Las subconsultas evitan multiplicar progresos por intentos o certificados.
    Un progreso o deber de otro curso nunca contribuye a este resumen.
    """
    obligatorias = (LeccionCurso.objects.filter(modulo__curso_id=OuterRef('edicion__curso_id'),
                       publicada=True, obligatoria=True).order_by().values('modulo__curso_id')
                       .annotate(cantidad=Count('pk')).values('cantidad')[:1])
    completadas = (ProgresoLeccion.objects.filter(inscripcion_id=OuterRef('pk'),
                       leccion__modulo__curso_id=OuterRef('edicion__curso_id'),
                       leccion__publicada=True, leccion__obligatoria=True)
                       .order_by().values('inscripcion_id').annotate(cantidad=Count('pk'))
                       .values('cantidad')[:1])
    entregas = (EntregaDeber.objects.filter(inscripcion_id=OuterRef('pk'), estado='entregada',
                    leccion__modulo__curso_id=OuterRef('edicion__curso_id'),
                    leccion__publicada=True, leccion__tipo='deber')
                    .order_by().values('inscripcion_id').annotate(cantidad=Count('pk'))
                    .values('cantidad')[:1])
    certificados = CertificadoCurso.objects.filter(inscripcion_id=OuterRef('pk'), anulado=False)
    # El intento corresponde al examen de la subconsulta y a la matrícula exterior.
    intentos = IntentoEvaluacion.objects.filter(leccion_id=OuterRef('pk'),
                    inscripcion_id=OuterRef(OuterRef('pk')))
    cantidad_intentos = (intentos.order_by().values('leccion_id')
                        .annotate(cantidad=Count('pk')).values('cantidad')[:1])
    sin_oportunidades = (LeccionCurso.objects.filter(modulo__curso_id=OuterRef('edicion__curso_id'),
                            publicada=True, obligatoria=True, tipo='evaluacion')
        .annotate(intento_aprobado=Exists(intentos.filter(aprobado=True)),
                  intentos_usados=Coalesce(Subquery(cantidad_intentos, output_field=IntegerField()), 0))
        .filter(intento_aprobado=False)
        .filter(Q(intentos_usados__gte=F('intentos')) | Q(fecha_limite__lt=timezone.now())))
    return (InscripcionCurso.objects.filter(edicion__curso__unidad=unidad)
            .annotate(total_obligatorias=Coalesce(Subquery(obligatorias, output_field=IntegerField()), 0),
                      completadas_obligatorias=Coalesce(Subquery(completadas, output_field=IntegerField()), 0),
                      entregas_por_calificar=Coalesce(Subquery(entregas, output_field=IntegerField()), 0),
                      certificado_vigente=Exists(certificados),
                      evaluacion_sin_oportunidades=Exists(sin_oportunidades)))


def _aprobadas():
    return Q(estado='aceptada', total_obligatorias__gt=0,
             completadas_obligatorias=F('total_obligatorias'))


def _reprobadas():
    # seguimiento_de prioriza completar el curso sobre intentos históricos fallidos.
    return Q(estado='aceptada', evaluacion_sin_oportunidades=True) & ~_aprobadas()


def _datos(request, unidad):
    _permiso(request, unidad)
    filtros = _filtros(request, unidad)
    curso, grupo = filtros['curso_objeto'], filtros['grupo_objeto']
    cursos = Curso.objects.filter(unidad=unidad).select_related('unidad')
    grupos = EdicionCurso.objects.filter(curso__unidad=unidad)
    inscritos = _inscripciones_anotadas(unidad)
    if curso:
        cursos, grupos = cursos.filter(pk=curso.pk), grupos.filter(curso=curso)
        inscritos = inscritos.filter(edicion__curso=curso)
    if grupo:
        cursos, grupos = cursos.filter(pk=grupo.curso_id), grupos.filter(pk=grupo.pk)
        inscritos = inscritos.filter(edicion=grupo)
    if filtros['q']:
        q = filtros['q']
        inscritos = inscritos.filter(Q(nombres_completos__icontains=q) | Q(documento__icontains=q)
            | Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q)
            | Q(usuario__email__icontains=q) | Q(usuario__username__icontains=q)
            | Q(edicion__curso__nombre__icontains=q) | Q(edicion__curso__codigo__icontains=q)
            | Q(edicion__nombre__icontains=q))
    estado = filtros['estado']
    if estado in dict(InscripcionCurso.ESTADOS):
        inscritos = inscritos.filter(estado=estado)
    elif estado == 'aprobado':
        inscritos = inscritos.filter(_aprobadas())
    elif estado == 'reprobado':
        inscritos = inscritos.filter(_reprobadas())
    elif estado == 'por_calificar':
        inscritos = inscritos.filter(estado='aceptada', entregas_por_calificar__gt=0)
    elif estado == 'certificado':
        inscritos = inscritos.filter(certificado_vigente=True)
    return filtros, cursos, grupos, inscritos


def _resumen(cursos, grupos, inscritos):
    resumen = cursos.aggregate(cursos=Count('pk'), publicados=Count('pk', filter=Q(publicado=True)),
                               borradores=Count('pk', filter=Q(publicado=False)))
    resumen['grupos'] = grupos.count()
    resumen.update(inscritos.aggregate(inscripciones=Count('pk'),
        aceptadas=Count('pk', filter=Q(estado='aceptada')),
        pendientes=Count('pk', filter=Q(estado='pendiente')),
        por_calificar=Coalesce(Sum('entregas_por_calificar', filter=Q(estado='aceptada')), 0),
        aprobados=Count('pk', filter=_aprobadas()),
        reprobados=Count('pk', filter=_reprobadas()),
        certificados=Count('pk', filter=Q(certificado_vigente=True))))
    return resumen


def _consulta_url(nombre, unidad, filtros=None, **extras):
    parametros = {clave: valor for clave, valor in zip(PARAMETROS,
        (filtros['curso'], filtros['grupo'], filtros['estado'], filtros['q'])) if valor} if filtros else {}
    parametros.update(extras)
    base = reverse(nombre, args=[unidad.slug])
    return base + ('?' + urlencode(parametros) if parametros else '')


def _curso_url(nombre, curso, grupo=None, **extras):
    parametros = dict(extras)
    if grupo and grupo.curso_id == curso.pk:
        parametros['edicion'] = grupo.pk
    base = reverse(nombre, args=[curso.unidad.slug, curso.codigo])
    return base + ('?' + urlencode(parametros) if parametros else '')


def _filas(inscritos):
    """Precarga por lotes; tampoco los reportes consultan por participante."""
    consulta = (inscritos.select_related('usuario', 'edicion__curso__unidad')
        .prefetch_related('progresos', 'intentos', 'entregas',
            Prefetch('certificados', queryset=CertificadoCurso.objects.defer('diseno_certificado')))
        .order_by('edicion__curso__orden', 'edicion__curso__nombre', 'edicion__nombre',
                  'nombres_completos', 'usuario__last_name', 'usuario__first_name', 'pk'))
    lecciones = LeccionCurso.objects.only('pk', 'modulo_id', 'orden', 'titulo', 'tipo',
        'publicada', 'obligatoria', 'nota_minima', 'intentos', 'fecha_limite')
    modulos = {}
    iterador = consulta.iterator(chunk_size=200)
    while lote := list(islice(iterador, 200)):
        faltantes = {inscrito.edicion.curso_id for inscrito in lote} - modulos.keys()
        for curso_id in faltantes:
            modulos[curso_id] = []
        if faltantes:
            for modulo in (ModuloCurso.objects.filter(curso_id__in=faltantes)
                           .prefetch_related(Prefetch('lecciones', queryset=lecciones))):
                modulo.visibles = [leccion for leccion in modulo.lecciones.all() if leccion.publicada]
                for leccion in modulo.visibles:
                    leccion.icono = ICONOS_DE_LECCION[leccion.tipo]
                modulos[modulo.curso_id].append(modulo)
        for inscrito in lote:
            curso = inscrito.edicion.curso
            seguimiento = seguimiento_de(inscrito, copy.deepcopy(modulos[curso.pk]))
            # El progreso histórico no convierte una retirada o solicitud en aprobación vigente.
            seguimiento['estado_academico'] = seguimiento['estado'] if inscrito.estado == 'aceptada' else 'no_aplica'
            seguimiento['academico_rotulo'] = seguimiento['rotulo'] if inscrito.estado == 'aceptada' else 'Sin matrícula activa'
            seguimiento.update(curso=curso, grupo=inscrito.edicion, email=inscrito.usuario.email,
                por_calificar=inscrito.entregas_por_calificar if inscrito.estado == 'aceptada' else 0,
                reporte_url=reverse('seguimiento_participante_curso',
                    args=[curso.unidad.slug, curso.codigo, inscrito.pk]))
            seguimiento['reporte_pdf_url'] = seguimiento['reporte_url'] + '?formato=pdf'
            seguimiento['certificado_url'] = (reverse('certificado_curso_gestor',
                args=[curso.unidad.slug, curso.codigo, seguimiento['certificado'].pk])
                if seguimiento['certificado'] else '')
            yield seguimiento


def contexto_cursos(request, unidad):
    """Contexto de la pestaña Cursos y sus enlaces de gestión existentes."""
    filtros, cursos, grupos, inscritos = _datos(request, unidad)
    resumen = _resumen(cursos, grupos, inscritos)
    pagina_oferta = Paginator(cursos.order_by('orden', 'nombre', 'pk'), 12).get_page(
        _numero_pagina(request.GET.get('pagina_oferta_cursos', '1')))
    cursos_visibles = list(pagina_oferta.object_list)
    ids_oferta = [curso.pk for curso in cursos_visibles]
    opciones_cursos = list(Curso.objects.filter(unidad=unidad).only('pk', 'nombre', 'codigo'))
    opciones_grupos = EdicionCurso.objects.filter(curso__unidad=unidad).select_related('curso')
    totales_curso = {fila['edicion__curso_id']: fila for fila in inscritos.filter(edicion__curso_id__in=ids_oferta).order_by()
        .values('edicion__curso_id').annotate(inscripciones=Count('pk'),
            pendientes=Count('pk', filter=Q(estado='pendiente')),
            por_calificar=Coalesce(Sum('entregas_por_calificar', filter=Q(estado='aceptada')), 0))}
    cantidades_grupos = dict(grupos.filter(curso_id__in=ids_oferta).order_by().values('curso_id').annotate(total=Count('pk'))
                              .values_list('curso_id', 'total'))
    tarjetas = []
    for curso in cursos_visibles:
        totales = totales_curso.get(curso.pk, {})
        tarjetas.append({'curso': curso, 'grupos': cantidades_grupos.get(curso.pk, 0),
            'inscripciones': totales.get('inscripciones', 0), 'pendientes': totales.get('pendientes', 0),
            'por_calificar': totales.get('por_calificar', 0), 'urls': {
                'editar': reverse('editor_curso', args=[unidad.slug, curso.codigo]),
                'estado': reverse('estado_curso', args=[unidad.slug, curso.codigo]),
                'grupos': _curso_url('grupos_curso', curso, filtros['grupo_objeto']),
                'inscritos': _curso_url('inscritos_curso', curso, filtros['grupo_objeto']),
                'calificaciones': _curso_url('calificaciones_curso', curso, filtros['grupo_objeto']),
                'certificado': _curso_url('editar_certificado_curso', curso, embed=1),
                'aula': _curso_url('aula_curso', curso, filtros['grupo_objeto']),
                'ver': _curso_url('curso_unidad', curso, filtros['grupo_objeto']),
            }})
    # La consulta paginada se evalúa antes del seguimiento para acotar memoria y trabajo.
    ordenados = inscritos.order_by('-fecha_inscripcion', '-pk')
    pagina = Paginator(ordenados, POR_PAGINA).get_page(request.GET.get('pagina_cursos', 1))
    ids = [inscrito.pk for inscrito in pagina.object_list]
    filas = {fila['inscripcion'].pk: fila for fila in _filas(inscritos.filter(pk__in=ids))} if ids else {}
    participantes = [filas[pk] for pk in ids]
    paginacion = [{'numero': numero, 'actual': numero == pagina.number,
        'url': _consulta_url('gestion_unidad', unidad, filtros, view='cursos',
                            modo_cursos='participantes', pagina_cursos=numero,
                            pagina_oferta_cursos=pagina_oferta.number)}
        for numero in range(max(1, pagina.number - 2), min(pagina.paginator.num_pages, pagina.number + 2) + 1)]
    modo = request.GET.get('modo_cursos')
    if modo not in ('cursos', 'participantes'):
        modo = ('participantes' if any(filtros[clave] for clave in ('curso', 'grupo', 'estado', 'q'))
                or pagina.number > 1 else 'cursos')

    def url_oferta(numero):
        return _consulta_url('gestion_unidad', unidad, filtros, view='cursos', modo_cursos='cursos',
                             pagina_oferta_cursos=numero, pagina_cursos=pagina.number)

    return {'cursos_gestion': {'resumen': resumen, 'cursos': tarjetas, 'participantes': participantes,
        'pagina_oferta': pagina_oferta,
        'anterior_oferta_url': url_oferta(pagina_oferta.previous_page_number()) if pagina_oferta.has_previous() else '',
        'siguiente_oferta_url': url_oferta(pagina_oferta.next_page_number()) if pagina_oferta.has_next() else '',
        'catalogo_url': reverse('cursos_unidad', args=[unidad.slug]),
        'pagina': pagina, 'filtros': filtros, 'opciones_cursos': opciones_cursos,
        'opciones_grupos': list(opciones_grupos), 'estados': ESTADOS, 'modo': modo,
        'crear_url': reverse('nuevo_curso', args=[unidad.slug]),
        'csv_url': _consulta_url('gestion_cursos_csv', unidad, filtros),
        'pdf_url': _consulta_url('gestion_cursos_pdf', unidad, filtros),
        'docx_url': _consulta_url('gestion_cursos_pdf', unidad, filtros, formato='docx'),
        'xlsx_url': _consulta_url('gestion_cursos_pdf', unidad, filtros, formato='xlsx'),
        'limpiar_url': _consulta_url('gestion_unidad', unidad, view='cursos', modo_cursos='participantes'),
        'paginacion': paginacion}}


def _unidad_del_reporte(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    _permiso(request, unidad)
    return unidad


@login_required
@require_GET
@never_cache
def reporte_cursos_csv_view(request, slug):
    unidad = _unidad_del_reporte(request, slug)
    _filtros_actuales, _cursos, _grupos, inscritos = _datos(request, unidad)
    respuesta = _respuesta_privada('\ufeff', 'text/csv; charset=utf-8',
                                   f'cursos-{slugify(unidad.slug)}.csv')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(['Curso', 'Código', 'Grupo', 'Persona', 'Documento', 'Correo',
        'Estado de inscripción', 'Estado académico', 'Avance (%)', 'Actividades completadas',
        'Actividades obligatorias', 'Promedio / 10', 'Promedio completo',
        'Entregas por revisar', 'Intentos utilizados', 'Oportunidades de evaluación',
        'Certificado', 'Estado del certificado', 'Fecha de inscripción'])
    for fila in _filas(inscritos):
        certificado = fila['certificado']
        valores = [fila['curso'].nombre, fila['curso'].codigo, fila['grupo'].nombre,
            fila['nombre'], fila['documento'], fila['email'], fila['inscripcion_rotulo'],
            fila['academico_rotulo'], fila['avance']['porcentaje'], fila['avance']['completadas'],
            fila['avance']['total'], _nota(fila['promedio_10']),
            'Sí' if fila['promedio_completo'] else 'No: promedio parcial', fila['por_calificar'],
            fila['intentos_usados'], fila['oportunidades'], certificado.codigo if certificado else '',
            fila['certificado_rotulo'], timezone.localtime(fila['inscripcion'].fecha_inscripcion).strftime('%d/%m/%Y %H:%M')]
        escritor.writerow([celda_csv_segura(valor) for valor in valores])
    return respuesta


def pdf_control_cursos(unidad, resumen, filas, filtros):
    """Reporte institucional compacto; los detalles de intentos quedan en el reporte personal."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.pdf_institucional import marco_institucional

    ahora = timezone.localtime()
    dibujar, lienzo, medidas = marco_institucional(formato='CONTROL DE CURSOS Y PARTICIPANTES',
        metadatos=[f'Fecha: {ahora:%d/%m/%Y}', f'Inscripciones: {resumen["inscripciones"]}'],
        pie='Gestión privada de cursos', apaisado=True)
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=medidas['pagesize'],
        leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f'Control de cursos - {unidad.nombre}', author=unidad.nombre)
    tinta = medidas['colores']
    cuerpo = ParagraphStyle('ControlCursos', fontName='Helvetica', fontSize=9, leading=12,
                            textColor=tinta['oscuro'], spaceAfter=5)
    titulo = ParagraphStyle('ControlCursosTitulo', parent=cuerpo, fontName='Helvetica-Bold',
                            fontSize=14, leading=17, spaceAfter=9)
    pequeno = ParagraphStyle('ControlCursosCelda', parent=cuerpo, fontSize=7.2, leading=9, spaceAfter=0)
    cabecera = ParagraphStyle('ControlCursosCabecera', parent=pequeno,
                             fontName='Helvetica-Bold', textColor=colors.white)

    def p(texto, estilo=cuerpo):
        return Paragraph(escape(str(texto)), estilo)

    seleccion = []
    if filtros['curso_objeto']:
        seleccion.append('Curso: ' + filtros['curso_objeto'].nombre)
    if filtros['grupo_objeto']:
        seleccion.append('Grupo: ' + filtros['grupo_objeto'].nombre)
    if filtros['estado']:
        seleccion.append('Estado: ' + dict(ESTADOS)[filtros['estado']])
    if filtros['q']:
        seleccion.append('Búsqueda: ' + filtros['q'])
    elementos = [p(unidad.nombre, titulo), p(' · '.join(seleccion) or 'Todos los cursos y grupos de la unidad'),
        p(f'Inscripciones: {resumen["inscripciones"]} · Aceptadas: {resumen["aceptadas"]} · '
          f'Por aceptar: {resumen["pendientes"]} · Entregas por revisar: {resumen["por_calificar"]} · '
          f'Aprobados: {resumen["aprobados"]} · Sin oportunidades: {resumen["reprobados"]} · '
          f'Certificados vigentes: {resumen["certificados"]}'),
        p('La aprobación exige inscripción aceptada y completar todas las actividades obligatorias publicadas. '
          'El promedio parcial incluye únicamente notas registradas. Los certificados conservan los datos de su emisión.', pequeno),
        Spacer(1, 4 * mm)]
    cabeceras = ['Curso / grupo', 'Participante / documento', 'Matrícula', 'Avance',
                 'Estado académico', 'Nota / 10', 'Certificado']
    datos = [[p(valor, cabecera) for valor in cabeceras]]
    for fila in filas:
        certificado = fila['certificado']
        valores = [f'{fila["curso"].codigo}: {fila["curso"].nombre} / {fila["grupo"].nombre}',
            f'{fila["nombre"]} / {fila["documento"] or "Sin documento"}', fila['inscripcion_rotulo'],
            f'{fila["avance"]["porcentaje"]} % ({fila["avance"]["completadas"]}/{fila["avance"]["total"]})',
            fila['academico_rotulo'], _nota(fila['promedio_10']) + (' (parcial)' if not fila['promedio_completo'] else ''),
            certificado.codigo if certificado else fila['certificado_rotulo']]
        datos.append([p(valor, pequeno) for valor in valores])
    if len(datos) == 1:
        elementos.append(p('No hay inscripciones que coincidan con los filtros.'))
    else:
        ancho = medidas['ancho_util']
        tabla = Table(datos, colWidths=[ancho * proporcion for proporcion in (.25, .22, .10, .09, .11, .08, .15)],
                      repeatRows=1, hAlign='LEFT')
        tabla.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), tinta['primario']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, tinta['suave']]),
            ('GRID', (0, 0), (-1, -1), .4, tinta['linea']), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        elementos.append(tabla)
    documento.build(elementos, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=lienzo)
    return salida.getvalue()


@login_required
@require_GET
@never_cache
def reporte_cursos_pdf_view(request, slug):
    unidad = _unidad_del_reporte(request, slug)
    filtros, cursos, grupos, inscritos = _datos(request, unidad)
    resumen = _resumen(cursos, grupos, inscritos)
    from apps.gestion_unidades.presentation.exportaciones_reportes import formato_reporte
    formato = formato_reporte(request)
    if formato in ('docx', 'xlsx'):
        from django.core.exceptions import BadRequest
        from apps.core.reportes import respuesta_reporte
        if resumen['inscripciones'] > 5000:
            raise BadRequest('La descarga supera 5000 inscripciones. Selecciona un curso, grupo o búsqueda más específica.')
        criterios = []
        for etiqueta, valor in [('Curso', filtros['curso_objeto']), ('Grupo', filtros['grupo_objeto']),
                                ('Estado', dict(ESTADOS).get(filtros['estado'])), ('Búsqueda', filtros['q'])]:
            if valor:
                criterios.append((etiqueta, str(valor)))
        filas = []
        for fila in _filas(inscritos):
            certificado = fila['certificado']
            filas.append([fila['curso'].nombre, fila['curso'].codigo, fila['grupo'].nombre,
                fila['nombre'], fila['documento'], fila['email'], fila['inscripcion_rotulo'],
                fila['academico_rotulo'], fila['avance']['porcentaje'], _nota(fila['promedio_10']),
                'Completo' if fila['promedio_completo'] else 'Parcial', fila['por_calificar'],
                certificado.codigo if certificado else '', fila['certificado_rotulo'],
                timezone.localtime(fila['inscripcion'].fecha_inscripcion)])
        reporte = {'title': 'Control de cursos y participantes', 'scope': unidad.nombre,
            'generated_at': timezone.localtime(), 'filter_summary': criterios,
            'metrics': [{'nombre': nombre, 'valor': resumen[clave], 'periodo': 'Estado actual de la selección'}
                for clave, nombre in [('cursos', 'Cursos y eventos'), ('grupos', 'Grupos'),
                    ('inscripciones', 'Inscripciones'), ('aceptadas', 'Aceptadas'), ('pendientes', 'Por aceptar'),
                    ('aprobados', 'Aprobados'), ('certificados', 'Inscripciones con certificado vigente')]],
            'notes': ['Reporte privado. La selección y el estado académico coinciden con el control de cursos.',
                      'Las inscripciones son matrículas, no personas únicas; el promedio parcial solo incluye notas registradas.'],
            'sections': [{'titulo': 'Participantes', 'headers': ['Curso', 'Código', 'Grupo', 'Persona',
                'Documento', 'Correo', 'Inscripción', 'Estado académico', 'Avance (%)', 'Promedio / 10',
                'Promedio', 'Entregas por revisar', 'Certificado', 'Estado certificado', 'Inscripción registrada'], 'rows': filas}]}
        return respuesta_reporte(reporte, formato, f'cursos-{unidad.slug}')
    return _respuesta_privada(pdf_control_cursos(unidad, resumen, _filas(inscritos), filtros),
        'application/pdf', f'cursos-{slugify(unidad.slug)}.pdf')
