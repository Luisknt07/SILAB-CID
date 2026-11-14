"""Reportes privados de Centros I+D sobre su propia base de datos.

Auth solo aporta un principal canónico vigente. Los filtros, agregados y
subconsultas científicos se resuelven dentro de la base de Centros; nunca se
unen tablas institucionales con ella. No se exportan expedientes personales.
"""
from datetime import date

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import router
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.utils import timezone

from .identidades import principal_vigente
from .models import (
    CasoExito, CentroID, Convocatoria, GestorCentro, Integrante, Novedad, Proyecto, Resultado,
    Servicio, SesionAcompanamiento, SolicitudCentro,
)
from .selectors_cientificos import pi_documentada, trl_documentados
from .informes_catalogos import CATALOGOS

CATEGORIAS = (
    ('resumen', 'Resumen por centro'), ('proyectos', 'Proyectos I+D+i'),
    ('produccion', 'Producción científica y tecnológica'),
    ('transferencias', 'Transferencias documentadas'),
    ('servicios', 'Solicitudes y servicios'), ('formacion', 'Formación y capacitación'),
    ('agenda', 'Agenda y acompañamiento'),
) + CATALOGOS
MAX_EXPORTACION = 5000
TAMANO_PAGINA = 25


def alcance_reportes_centros(usuario):
    """Administración principal: todos; responsables/gestores: solo asignados.

    Ni staff, ni permisos centrales de modelos, ni una CuentaCentro local
    conceden acceso global. La baja canónica revoca también sesiones antiguas.
    """
    if not getattr(usuario, 'is_authenticated', False):
        raise PermissionDenied('Inicia sesión para consultar reportes de Centros I+D.')
    principal = principal_vigente(usuario)
    if principal is None:
        raise PermissionDenied('La cuenta institucional no está vigente.')
    alias = router.db_for_read(CentroID)
    centros = CentroID.objects.using(alias).all()
    if not principal.is_superuser:
        asignado = GestorCentro.objects.using(alias).filter(centro_id=OuterRef('pk'), cuenta_id=principal.pk)
        centros = centros.alias(_gestor_reporte=Exists(asignado)).filter(
            Q(responsable_id=principal.pk) | Q(_gestor_reporte=True))
    if not principal.is_superuser and not centros.exists():
        raise PermissionDenied('No tienes centros asignados para consultar reportes.')
    return centros, principal.is_superuser


def puede_reportar_centros(usuario):
    """Puerta del centro de reportes, evaluada por demanda, nunca en cada página."""
    try:
        alcance_reportes_centros(usuario)
    except PermissionDenied:
        return False
    return True


class FiltrosReporteCentros(forms.Form):
    categoria = forms.ChoiceField(choices=CATEGORIAS, required=False, label='Contenido')
    centro = forms.IntegerField(required=False, min_value=1, max_value=9223372036854775807,
                                label='Centro', widget=forms.Select)
    anio = forms.IntegerField(required=False, min_value=1, max_value=9999, label='Año calendario')
    q = forms.CharField(required=False, max_length=200, label='Buscar en el contenido')
    centro_q = forms.CharField(required=False, max_length=100, label='Buscar centro')
    tipo_resultado = forms.ChoiceField(required=False, choices=(('', 'Todos los tipos'), *Resultado.TIPOS))
    estado = forms.CharField(required=False, max_length=30)
    pagina = forms.IntegerField(required=False, min_value=1, max_value=100000000, widget=forms.HiddenInput)

    def __init__(self, parametros, centros):
        super().__init__(parametros)
        self.centros = centros

    def clean_categoria(self):
        return self.cleaned_data['categoria'] or 'resumen'

    def clean_centro(self):
        identificador = self.cleaned_data['centro']
        if identificador and not self.centros.filter(pk=identificador).exists():
            raise forms.ValidationError('Selecciona uno de tus centros autorizados.')
        return identificador

    def clean(self):
        datos = super().clean()
        categoria = datos.get('categoria')
        opciones = estados_reporte(categoria)
        if opciones and datos.get('estado') and datos['estado'] not in dict(opciones):
            self.add_error('estado', 'Selecciona un estado válido para este contenido.')
        if not opciones:
            datos['estado'] = ''
        if categoria != 'produccion':
            datos['tipo_resultado'] = ''
        return datos


def estados_reporte(categoria):
    from .models import Componente, DocumentoCentro, EquipoCentro, Fase, HitoProyecto
    modelos = {'proyectos': Proyecto, 'servicios': SolicitudCentro, 'formacion': SolicitudCentro,
               'agenda': SesionAcompanamiento, 'hitos': HitoProyecto, 'equipamiento': EquipoCentro,
               'capacidades': Componente, 'planificacion': Fase, 'repositorio': DocumentoCentro}
    modelo = modelos.get(categoria)
    campo = 'estado_documental' if categoria == 'repositorio' else 'estado'
    return tuple(modelo._meta.get_field(campo).choices) if modelo else ()


def _registrados(modelo, centros, *, relacion='centro', contenido=False):
    consulta = modelo.objects.using(centros.db).filter(**{relacion + '__in': centros.values('pk')})
    return consulta.filter(es_muestra=False) if contenido else consulta


def _por_anio(consulta, campo, anio):
    return consulta.filter(**{campo + '__year': anio}) if anio else consulta


def _proyectos(centros, anio):
    consulta = _registrados(Proyecto, centros, contenido=True)
    # Intersección del proyecto con el año: no equivale a proyectos creados ese año.
    # Los registros sin inicio no se atribuyen a un período que no está documentado.
    if anio:
        consulta = consulta.filter(inicio__lte=date(anio, 12, 31)).filter(
            Q(fin__isnull=True) | Q(fin__gte=date(anio, 1, 1)))
    return consulta


def _resultados(centros, anio):
    consulta = _registrados(Resultado, centros, contenido=True).filter(confidencial=False)
    return consulta.filter(anio=anio) if anio else consulta


def _transferencias(centros, anio):
    consulta = _registrados(CasoExito, centros, contenido=True).filter(
        fecha_transferencia__lte=timezone.localdate())
    for campo in ('receptor', 'mecanismo', 'evidencia', 'autorizacion_publicacion'):
        consulta = consulta.filter(**{campo + '__regex': r'\S'})
    return _por_anio(consulta, 'fecha_transferencia', anio)


def _solicitudes(centros, anio):
    return _por_anio(_registrados(SolicitudCentro, centros), 'creada', anio)


def _sesiones(centros, anio):
    return _por_anio(_registrados(SesionAcompanamiento, centros, relacion='solicitud__centro'), 'inicio', anio)


def _busqueda(consulta, texto, campos):
    if texto:
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{campo + '__icontains': texto})
        consulta = consulta.filter(condicion)
    return consulta


def _agrupados(consulta, campo='centro_id'):
    return dict(consulta.order_by().values(campo).annotate(total=Count('pk')).values_list(campo, 'total'))


def _pagina(consulta, numero, exportar):
    paginador = Paginator(consulta, TAMANO_PAGINA)
    if exportar:
        if paginador.count > MAX_EXPORTACION:
            raise ValidationError(f'El reporte supera {MAX_EXPORTACION} filas. Selecciona un centro, año o búsqueda para exportar.')
        filas = list(consulta)
        paginacion = {'number': 1, 'num_pages': 1, 'count': paginador.count, 'previous': None, 'next': None}
    else:
        pagina = paginador.get_page(numero or 1)
        filas = list(pagina.object_list)
        paginacion = {'number': pagina.number, 'num_pages': paginador.num_pages, 'count': paginador.count,
                      'previous': pagina.previous_page_number() if pagina.has_previous() else None,
                      'next': pagina.next_page_number() if pagina.has_next() else None}
    return filas, paginacion


def _fecha(valor):
    if valor is None:
        return 'Sin registrar'
    if hasattr(valor, 'hour'):
        valor = timezone.localtime(valor)
        return valor.strftime('%d/%m/%Y %H:%M')
    return valor.strftime('%d/%m/%Y')


def _opciones_centros(centros, filtros):
    consulta = _busqueda(centros, filtros['centro_q'], ('nombre', 'sigla')).order_by('nombre', 'pk')
    opciones = list(consulta.values_list('pk', 'nombre')[:201])
    mas = len(opciones) > 200
    opciones = opciones[:200]
    elegido = filtros['centro']
    if elegido and elegido not in {pk for pk, _ in opciones}:
        opciones.append(centros.values_list('pk', 'nombre').get(pk=elegido))
    return opciones, mas


def construir_reporte_centros(usuario, parametros=None, *, exportar=False):
    """Contrato común de exportación, con autorización y filtros inseparables.

    Solo se consulta la categoría solicitada. Las tablas HTML paginan en SQL;
    la exportación es completa dentro de un límite explícito y nunca se trunca.
    """
    autorizados, macro = alcance_reportes_centros(usuario)
    formulario = FiltrosReporteCentros(parametros or {}, autorizados)
    if not formulario.is_valid():
        raise ValidationError(dict(formulario.errors))
    filtros = formulario.cleaned_data
    categoria, anio, texto = filtros['categoria'], filtros['anio'], filtros['q']
    centros = autorizados.filter(pk=filtros['centro']) if filtros['centro'] else autorizados
    alcance = 'Todos los Centros I+D' if macro else 'Centros I+D asignados'
    if filtros['centro']:
        alcance = centros.values_list('nombre', flat=True).get()
    if categoria == 'resumen':
        centros = _busqueda(centros, texto, ('nombre', 'sigla'))
    periodo = str(anio) if anio else 'Todos los años registrados'
    metricas = []

    def metrica(clave, nombre, valor, unidad='registros', periodo_metrica=periodo):
        metricas.append({'clave': clave, 'nombre': nombre, 'valor': valor,
                         'unidad': unidad, 'periodo': periodo_metrica, 'scope': alcance})

    notas = ['Se excluyen los contenidos demostrativos y los resultados confidenciales.',
             'Los conteos son registros institucionales; no acreditan por sí solos impacto ni aprobación de cursos.']
    if categoria in dict(CATALOGOS):
        from .informes_catalogos import construir_catalogo
        cifras, columnas, filas, paginacion, notas_catalogo = construir_catalogo(categoria, centros, filtros, exportar)
        for clave, nombre, valor, unidad, temporal in cifras:
            metrica(clave, nombre, valor, unidad, temporal)
        notas.extend(notas_catalogo)
    elif categoria == 'resumen':
        proyectos, resultados = _proyectos(centros, anio), _resultados(centros, anio)
        transferencias, solicitudes = _transferencias(centros, anio), _solicitudes(centros, anio)
        formacion = solicitudes.filter(tipo='capacitacion')
        sesiones = _sesiones(centros, anio).filter(estado='realizada')
        metrica('centros', 'Centros incluidos', centros.count(), 'centros', 'Situación actual')
        metrica('proyectos', 'Proyectos I+D+i registrados', proyectos.count())
        metrica('resultados', 'Resultados no confidenciales', resultados.count())
        metrica('transferencias', 'Transferencias documentadas', transferencias.count())
        metrica('solicitudes', 'Solicitudes recibidas', solicitudes.count())
        metrica('formacion', 'Solicitudes de capacitación', formacion.count())
        metrica('sesiones', 'Acompañamientos realizados', sesiones.count())
        objetos, paginacion = _pagina(centros.only('pk', 'nombre', 'estado').order_by('nombre', 'pk'), filtros['pagina'], exportar)
        pagina_centros = centros.filter(pk__in=[c.pk for c in objetos])
        conteos = [_agrupados(q.filter(centro__in=pagina_centros.values('pk'))) for q in
                   (proyectos, resultados, transferencias, solicitudes, formacion)]
        conteos.append(_agrupados(sesiones.filter(solicitud__centro__in=pagina_centros.values('pk')), 'solicitud__centro_id'))
        columnas = ['Centro', 'Estado declarado', 'Proyectos', 'Resultados', 'Transferencias documentadas',
                    'Solicitudes', 'Capacitaciones solicitadas', 'Acompañamientos realizados']
        filas = [[c.nombre, str(c.get_estado_display()), *[cuenta.get(c.pk, 0) for cuenta in conteos]] for c in objetos]
        notas.append('Proyectos: actividad que intersecta el año; resultados: año de producción; transferencias: fecha de aceptación; solicitudes: recepción; acompañamientos: inicio. Sin año se incluyen registros sin fecha.')
    elif categoria == 'proyectos':
        consulta = _busqueda(_proyectos(centros, anio), texto, ('titulo', 'codigo', 'sector'))
        if filtros['estado']:
            consulta = consulta.filter(estado=filtros['estado'])
        cifras = consulta.aggregate(total=Count('pk'), activos=Count('pk', filter=Q(estado__in=Proyecto.ACTIVOS)),
                                    finalizados=Count('pk', filter=Q(estado='finalizado')))
        metrica('proyectos', 'Proyectos registrados', cifras['total'])
        metrica('activos', 'En formulación o ejecución', cifras['activos'])
        metrica('finalizados', 'Estado finalizado registrado', cifras['finalizados'])
        detalle = consulta.select_related('centro', 'linea').only(
            'pk', 'centro__nombre', 'codigo', 'titulo', 'categoria', 'estado', 'linea__nombre', 'linea__centro_id', 'inicio', 'fin')
        objetos, paginacion = _pagina(detalle.order_by('centro__nombre', 'titulo', 'pk'), filtros['pagina'], exportar)
        columnas = ['Centro', 'Código', 'Proyecto', 'Categoría', 'Estado declarado', 'Línea', 'Inicio', 'Fin']
        filas = [[p.centro.nombre, p.codigo, p.titulo, str(p.get_categoria_display()), str(p.get_estado_display()),
                  p.linea.nombre if p.linea_id and p.linea.centro_id == p.centro_id else 'Sin asignar',
                  _fecha(p.inicio), _fecha(p.fin)] for p in objetos]
        notas.append('El filtro anual incluye proyectos con inicio documentado que intersectan el año. Estado y avance son la situación registrada actual; seleccionar «transferido» no acredita una transferencia.')
    elif categoria == 'produccion':
        consulta = _busqueda(_resultados(centros, anio), texto, ('titulo', 'doi', 'tecnologia'))
        if filtros['tipo_resultado']:
            consulta = consulta.filter(tipo=filtros['tipo_resultado'])
        metrica('resultados', 'Resultados no confidenciales', consulta.count())
        metrica('cientificos', 'Producción científica registrada', consulta.filter(tipo__in=Resultado.CIENTIFICOS).count())
        metrica('prototipos', 'Prototipos registrados', consulta.filter(tipo='prototipo').count())
        metrica('trl', 'Resultados con TRL documentado', trl_documentados(consulta).count())
        metrica('pi', 'Protección documentada', pi_documentada(consulta).count())
        detalle = consulta.annotate(
            _trl_documentado=Exists(trl_documentados(consulta.filter(pk=OuterRef('pk')))),
            _pi_documentada=Exists(pi_documentada(consulta.filter(pk=OuterRef('pk')))),
        ).select_related('centro').only('pk', 'centro__nombre', 'titulo', 'tipo', 'anio', 'acceso',
                                       'embargo_hasta', 'publicado', 'trl', 'estado_pi')
        objetos, paginacion = _pagina(detalle.order_by('centro__nombre', '-anio', 'titulo', 'pk'), filtros['pagina'], exportar)
        columnas = ['Centro', 'Resultado', 'Tipo', 'Año', 'Condición de acceso', 'Publicado', 'TRL documentado', 'Protección documentada']
        filas = [[r.centro.nombre, r.titulo, str(r.get_tipo_display()), r.anio, str(r.estado_acceso_publico),
                  'Sí' if r.publicado else 'No', r.trl if r._trl_documentado else 'Sin documentar',
                  str(r.get_estado_pi_display()) if r._pi_documentada else 'Sin documentar'] for r in objetos]
        notas.append('El período corresponde al año registrado de producción. TRL y protección solo se cuentan con fecha y respaldos documentados; no se infieren del tipo del resultado.')
    elif categoria == 'transferencias':
        consulta = _busqueda(_transferencias(centros, anio), texto, ('titulo', 'sector'))
        metrica('transferencias', 'Transferencias documentadas', consulta.count())
        impacto = consulta
        for campo in ('referencia', 'unidad_medida', 'periodo_medicion', 'metodo_medicion'):
            impacto = impacto.filter(**{campo + '__regex': r'\S'})
        metrica('impacto', 'Casos con medición documentada', impacto.count())
        detalle = consulta.annotate(_impacto_documentado=Exists(impacto.filter(pk=OuterRef('pk')))).select_related('centro').only(
            'pk', 'centro__nombre', 'titulo', 'sector', 'fecha_transferencia')
        objetos, paginacion = _pagina(detalle.order_by('centro__nombre', '-fecha_transferencia', 'pk'), filtros['pagina'], exportar)
        columnas = ['Centro', 'Caso', 'Sector', 'Fecha de aceptación', 'Medición documentada']
        filas = [[c.centro.nombre, c.titulo, c.sector, _fecha(c.fecha_transferencia),
                  'Sí' if c._impacto_documentado else 'No'] for c in objetos]
        notas.append('Solo casos con receptor, mecanismo, aceptación no futura, evidencia y autorización de divulgación. Una medición documentada no demuestra atribución causal al centro.')
    elif categoria in ('servicios', 'formacion'):
        consulta = _solicitudes(centros, anio)
        if categoria == 'formacion':
            consulta = consulta.filter(tipo='capacitacion')
        consulta = _busqueda(consulta, texto, ('titulo',))
        if filtros['estado']:
            consulta = consulta.filter(estado=filtros['estado'])
        cifras = consulta.aggregate(total=Count('pk'), entregadas=Count('pk', filter=Q(estado__in=('entregada', 'cerrada'))),
                                    participantes_total=Sum('participantes'), sin_participantes=Count('pk', filter=Q(participantes__isnull=True)))
        metrica('solicitudes', 'Solicitudes de capacitación' if categoria == 'formacion' else 'Solicitudes recibidas', cifras['total'])
        metrica('entregadas', 'Entregadas o cerradas', cifras['entregadas'])
        metrica('participantes', 'Participantes declarados en solicitudes', cifras['participantes_total'] or 0, 'participaciones')
        metrica('sin_participantes', 'Solicitudes sin cifra de participantes', cifras['sin_participantes'])
        if categoria == 'servicios':
            metrica('portafolio', 'Servicios activos del portafolio', _registrados(Servicio, centros).filter(activo=True).count(), periodo_metrica='Situación actual, sin filtro de búsqueda ni año')
        else:
            integrantes = _registrados(Integrante, centros, contenido=True).filter(vigente=True, rol__in=('tesista', 'estudiante'))
            metrica('formacion_actual', 'Tesistas y estudiantes vinculados vigentes', integrantes.count(), 'personas registradas', 'Situación actual, sin filtro de búsqueda ni año')
            oportunidades = _registrados(Convocatoria, centros, contenido=True).filter(activa=True).filter(
                Q(cierre__isnull=True) | Q(cierre__gte=timezone.localdate()))
            metrica('oportunidades', 'Convocatorias y oportunidades vigentes', oportunidades.count(),
                    periodo_metrica='Situación actual, sin filtro de búsqueda ni año')
        detalle = consulta.select_related('centro').only(
            'pk', 'centro__nombre', 'centro__sigla', 'titulo', 'tipo', 'creada', 'estado', 'participantes')
        objetos, paginacion = _pagina(detalle.order_by('-creada', '-pk'), filtros['pagina'], exportar)
        columnas = ['Centro', 'Referencia', 'Solicitud', 'Tipo', 'Recepción', 'Estado', 'Participantes declarados']
        filas = [[s.centro.nombre, s.referencia, s.titulo, str(s.get_tipo_display()), _fecha(s.creada),
                  str(s.get_estado_display()), s.participantes if s.participantes is not None else 'Sin registrar'] for s in objetos]
        notas.append('Período por recepción de la solicitud. Participaciones declaradas, sin deduplicar personas, no acreditan asistencia, aprobación ni certificados; los cursos de laboratorios se reportan en su propio módulo.')
    else:
        consulta = _busqueda(_sesiones(centros, anio), texto, ('modalidad', 'solicitud__titulo'))
        if filtros['estado']:
            consulta = consulta.filter(estado=filtros['estado'])
        cifras = consulta.aggregate(total=Count('pk'), realizadas=Count('pk', filter=Q(estado='realizada')),
                                    programadas=Count('pk', filter=Q(estado='programada')))
        metrica('sesiones', 'Sesiones de acompañamiento', cifras['total'])
        metrica('realizadas', 'Sesiones realizadas', cifras['realizadas'])
        metrica('programadas', 'Sesiones programadas', cifras['programadas'])
        eventos = _por_anio(_registrados(Novedad, centros, contenido=True).filter(tipo='evento'), 'fecha', anio)
        metrica('eventos', 'Eventos registrados', eventos.count(), periodo_metrica=periodo + ', sin filtro de búsqueda')
        detalle = consulta.select_related('solicitud__centro').only(
            'pk', 'solicitud__id', 'solicitud__centro__nombre', 'solicitud__centro__sigla', 'inicio', 'fin', 'modalidad', 'estado')
        objetos, paginacion = _pagina(detalle.order_by('-inicio', '-pk'), filtros['pagina'], exportar)
        columnas = ['Centro', 'Referencia de solicitud', 'Inicio', 'Fin', 'Modalidad', 'Estado']
        filas = [[s.solicitud.centro.nombre, s.solicitud.referencia, _fecha(s.inicio), _fecha(s.fin), s.modalidad,
                  str(s.get_estado_display())] for s in objetos]
        notas.append('Período por inicio de sesión o evento. No se incluyen nombres de solicitantes, acuerdos, diagnósticos ni notas internas.')
    opciones, hay_mas = _opciones_centros(autorizados, filtros)
    criterios = [('Alcance', alcance), ('Contenido', dict(CATEGORIAS)[categoria]), ('Período', periodo),
                 ('Búsqueda de contenido', texto or 'Sin filtro'), ('Filas encontradas', paginacion['count'])]
    if filtros['tipo_resultado']:
        criterios.append(('Tipo de resultado', str(dict(Resultado.TIPOS)[filtros['tipo_resultado']])))
    if filtros['estado']:
        criterios.append(('Estado', str(dict(estados_reporte(categoria))[filtros['estado']])))
    return {'title': 'Reportes de Centros I+D', 'scope': alcance, 'generated_at': timezone.localtime(),
            'filter_summary': criterios, 'metrics': metricas,
            'sections': [{'clave': categoria, 'titulo': dict(CATEGORIAS)[categoria], 'headers': columnas, 'rows': filas}],
            'notes': notas, 'pagination': paginacion, 'filters': filtros,
            'center_options': opciones, 'more_centers': hay_mas, 'categories': CATEGORIAS, 'macro': macro,
            'state_options': estados_reporte(categoria), 'result_types': Resultado.TIPOS}
