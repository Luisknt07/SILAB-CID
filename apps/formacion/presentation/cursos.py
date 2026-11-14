"""Catálogo de formación de una unidad: navegación acotada y fichas nativas o externas.

Los cursos conservan su aula y sus ediciones; los eventos externos describen la
colaboración y enlazan a su organizador. Los borradores no son convocatorias públicas.
"""
from urllib.parse import urlencode, urlsplit
from zlib import crc32

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.formacion.models.cursos import Curso, EdicionCurso, EntregaDeber
from apps.directorio_unidades.models.core import Unidad

from apps.laboratorios.operacion.presentation.actividad_laboratorio import cursos_de
from apps.gestion_unidades.presentation.altas_en_ficha import _pantalla, _responder
from apps.core.presentation.codigos_sistema import sigla_de_unidad
from apps.gestion_unidades.presentation.conoce import foto_de_portada
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de

ICONOS_DE_CLASIFICACION = {
    'corto': 'fas fa-bolt',
    'largo': 'fas fa-graduation-cap',
    'taller': 'fas fa-tools',
    'capacitacion': 'fas fa-chalkboard-teacher',
    'induccion': 'fas fa-hard-hat',
    'entrenamiento': 'fas fa-cogs',
    'webinar': 'fas fa-laptop',
    'seminario': 'fas fa-book-reader',
    'conferencia': 'fas fa-microphone-alt',
    'congreso': 'fas fa-users',
    'jornada': 'fas fa-calendar-day',
    'encuentro': 'fas fa-handshake',
}
# El plural con que cada clasificación agrupa sus cursos en el menú y en la página por año.
GRUPOS_DE_CLASIFICACION = {
    'corto': 'Cursos cortos',
    'largo': 'Cursos largos',
    'taller': 'Talleres',
    'capacitacion': 'Capacitaciones',
    'induccion': 'Inducciones',
    'entrenamiento': 'Entrenamientos técnicos',
    'webinar': 'Webinars',
    'seminario': 'Seminarios',
    'conferencia': 'Conferencias',
    'congreso': 'Congresos',
    'jornada': 'Jornadas',
    'encuentro': 'Encuentros',
}
MODALIDAD_BREVE = {'autoguiado': 'Autoguiado', 'en_vivo': 'En vivo', 'mixto': 'Mixto'}
INSCRIPCION_BREVE = {'abierta': 'Inscripción abierta', 'aprobacion': 'Inscripción con aprobación'}

GUIA_DE_CURSO = {
    'lema': 'Una frase que invite a inscribirse. Por ejemplo: «Diseña y fabrica tu primer prototipo en 20 horas».',
    'descripcion': 'Cuente en dos o tres párrafos de qué trata el curso, cómo se trabaja y qué se lleva quien lo '
                   'termina.',
    'aprendizajes': 'Un aprendizaje por línea, empezando con un verbo: «Modelar piezas en 3D».\n'
                    'Otro aprendizaje.',
    'dirigido_a': 'A quién va dirigido: estudiantes de qué carreras o semestres, docentes, público externo…',
    'requisitos': 'Un requisito por línea: conocimientos previos, materiales que debe traer, inducción de seguridad.',
    'instructores': 'Nombre del instructor | Lo que enseña o su cargo',
}


def puede_crear_cursos(usuario, unidad):
    return puede_operar_modulo_unidad(usuario, unidad, 'practicas')


def consulta_cursos_visibles(unidad, usuario=None):
    """Consulta sin materializar el catálogo ni sus contenidos académicos."""
    cursos = Curso.objects.filter(unidad=unidad).order_by('orden', 'nombre', 'pk')
    if usuario is None or not puede_gestionar_unidad(usuario, unidad):
        cursos = cursos.filter(publicado=True, activo=True)
    return cursos


def cursos_visibles(unidad, usuario=None):
    """Compatibilidad para las superficies que presentan cursos con sus ediciones."""
    return consulta_cursos_visibles(unidad, usuario).prefetch_related('ediciones')


def resumen_de(curso, hoy=None):
    """Lo que el menú y las tarjetas dicen de un curso: modalidad, horas y en qué está su edición vigente."""
    partes = [MODALIDAD_BREVE[curso.modalidad]]
    if curso.duracion_horas:
        partes.append(f'{curso.duracion_horas} h')
    edicion = curso.edicion_vigente(hoy)
    if curso.es_externo:
        partes.append('Plataforma externa')
    elif edicion and (edicion.inicio or edicion.inscripciones_desde or edicion.inscripciones_hasta):
        partes.append(f'{edicion.nombre}: {edicion.estado(hoy)[1].lower()}')
    return ' · '.join(partes)


def grupos_de_cursos(unidad, usuario):
    """Accesos de tamaño acotado: catálogo, categorías y matrículas personales."""
    from apps.formacion.presentation.aula import _boton
    from apps.formacion.presentation.aula_cursos import mis_inscripciones
    from apps.laboratorios.operacion.presentation.actividad_laboratorio import consulta_cursos_de

    slug = unidad.slug
    cursos = consulta_cursos_visibles(unidad, usuario)
    cuentas = dict(cursos.order_by().values('clasificacion').annotate(total=Count('pk'))
                   .values_list('clasificacion', 'total'))
    total = sum(cuentas.values())
    url = reverse('cursos_unidad', args=[slug])
    herramientas = [_boton(
        'cursos-por-anio', 'Catálogo de cursos y eventos', url, 'fas fa-th-large',
        'Busca formación por categoría, modalidad, año y plataforma',
        subtitulo=f'{total} actividades · búsqueda y filtros')]
    inscripciones = mis_inscripciones(unidad, usuario).count()
    if inscripciones:
        herramientas.append(_boton(
            'mis-cursos', 'Mis cursos', reverse('mis_cursos', args=[slug]), 'fas fa-user-graduate',
            'Tus cursos inscritos y tu avance',
            subtitulo=f'{inscripciones} inscripción' if inscripciones == 1 else f'{inscripciones} inscripciones'))
    grupos = [{'nombre': '', 'clave': 'por-anio', 'botones': herramientas, 'total_formacion': total}]
    categorias = [
        _boton(f'categoria-curso-{clave}', f'{titulo} ({cuentas[clave]})',
               f'{url}?{urlencode({"categoria": clave})}#cursos', ICONOS_DE_CLASIFICACION[clave],
               f'Explorar {titulo.lower()} en el catálogo')
        for clave, titulo in GRUPOS_DE_CLASIFICACION.items() if cuentas.get(clave)
    ]
    if categorias:
        grupos.append({'nombre': 'Explorar por categoría', 'clave': 'categorias', 'botones': categorias})
    catalogo_total = consulta_cursos_de(unidad).exclude(
        pk__in=cursos.exclude(actividad_catalogo_id=None).values('actividad_catalogo_id')).count()
    if catalogo_total:
        grupos.append({'nombre': '', 'clave': 'catalogo-reservas', 'total_formacion': catalogo_total,
                       'botones': [_boton(
                           'cursos-catalogo', f'Actividades con reserva ({catalogo_total})',
                           url + '#catalogo', 'fas fa-calendar-check',
                           'Capacitaciones que se solicitan mediante una reserva en la unidad')]})
    return grupos


def _contexto(unidad, usuario):
    mapa = mapa_de(unidad)
    numero = mapa.numero('cursos') if mapa else ''
    modulo = mapa.modulo_de(numero) if numero else ''
    return {
        'unidad': unidad,
        'seccion': numero,
        'volver_url': f'{unidad.get_absolute_url()}#{modulo}' if modulo else unidad.get_absolute_url(),
        'foto_portada': foto_de_portada(unidad),
        'ediciones': ediciones_de(usuario, unidad),
        'puede_crear': puede_crear_cursos(usuario, unidad),
    }


@xframe_options_sameorigin
def cursos_unidad_view(request, slug):
    """Catálogo filtrable y paginado en SQL; nunca carga todos los cursos en memoria."""
    from apps.laboratorios.operacion.presentation.actividad_laboratorio import completar_cursos_de, consulta_cursos_de

    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    hoy = timezone.localdate()
    gestor = puede_gestionar_unidad(request.user, unidad)
    base = consulta_cursos_visibles(unidad, request.user)
    anios = list(base.filter(ediciones__activa=True).order_by('-ediciones__anio')
                 .values_list('ediciones__anio', flat=True).distinct())
    parametros = request.GET
    categorias = dict(Curso.CLASIFICACIONES)
    origenes = dict(Curso.ORIGENES)
    estados = [('publicado', 'Publicado'), ('borrador', 'Borrador'), ('inactivo', 'Inactivo')] if gestor else []
    anio_bruto = parametros.get('anio', '')
    anio = int(anio_bruto) if len(anio_bruto) == 4 and anio_bruto.isascii() and anio_bruto.isdecimal() else None
    anio = anio if anio in anios else None
    filtros = {
        'q': ' '.join(parametros.get('q', '').split())[:120],
        'categoria': parametros.get('categoria', '') if parametros.get('categoria') in categorias else '',
        'modalidad': parametros.get('modalidad', '') if parametros.get('modalidad') in MODALIDAD_BREVE else '',
        'origen': parametros.get('origen', '') if parametros.get('origen') in origenes else '',
        'anio': str(anio) if anio else '',
        'estado': parametros.get('estado', '') if parametros.get('estado') in dict(estados) else '',
    }
    consulta = base
    if filtros['q']:
        texto = filtros['q']
        consulta = consulta.filter(Q(nombre__icontains=texto) | Q(codigo__icontains=texto)
                                   | Q(lema__icontains=texto) | Q(entidad_organizadora__icontains=texto))
    for campo, filtro in (('clasificacion', 'categoria'), ('modalidad', 'modalidad'), ('origen', 'origen')):
        if filtros[filtro]:
            consulta = consulta.filter(**{campo: filtros[filtro]})
    if anio:
        consulta = consulta.filter(ediciones__activa=True, ediciones__anio=anio).distinct()
    if filtros['estado'] == 'publicado':
        consulta = consulta.filter(publicado=True, activo=True)
    elif filtros['estado'] == 'borrador':
        consulta = consulta.filter(publicado=False, activo=True)
    elif filtros['estado'] == 'inactivo':
        consulta = consulta.filter(activo=False)
    consulta = consulta.prefetch_related(Prefetch('ediciones', queryset=EdicionCurso.objects.filter(activa=True)))
    paginador = Paginator(consulta, 12)
    pagina = paginador.get_page(_numero_pagina(parametros.get('pagina', '1')))
    cursos = list(pagina.object_list)
    for curso in cursos:
        curso.resumen = resumen_de(curso, hoy)
        curso.del_anio = [edicion for edicion in curso.ediciones.all() if edicion.activa and edicion.anio == anio]
        curso.icono_catalogo = ICONOS_DE_CLASIFICACION.get(curso.clasificacion, 'fas fa-graduation-cap')
        curso.modalidad_corta = MODALIDAD_BREVE[curso.modalidad]
        curso.dominio_externo = urlsplit(curso.url_externa_segura).hostname if curso.es_externo else ''
        curso.organizador_catalogo = curso.entidad_organizadora or ('Organizador por confirmar' if curso.es_externo else unidad.nombre)
        curso.participacion_catalogo = curso.get_participacion_unidad_display()
        curso.ficha_catalogo_url = reverse('curso_unidad', args=[unidad.slug, curso.codigo])
        curso.editor_catalogo_url = (
            reverse('editar_registro', args=[unidad.slug, 'curso', curso.pk]) + '?grupo=oferta'
            if curso.es_externo else reverse('editor_curso', args=[unidad.slug, curso.codigo])
        ) if puede_crear_cursos(request.user, unidad) else ''
        curso.estado_catalogo_clave, curso.estado_catalogo = _estado_tarjeta(curso, hoy)
    legados = consulta_cursos_de(unidad).exclude(
        pk__in=base.exclude(actividad_catalogo_id=None).values('actividad_catalogo_id'))
    catalogo_pagina = Paginator(legados, 6).get_page(_numero_pagina(parametros.get('pagina_reservas', '1')))
    catalogo = completar_cursos_de(catalogo_pagina.object_list)
    query_pagina = {clave: valor for clave, valor in filtros.items() if valor}
    if catalogo_pagina.number != 1:
        query_pagina['pagina_reservas'] = catalogo_pagina.number
    query_reservas = {clave: valor for clave, valor in filtros.items() if valor}
    if pagina.number != 1:
        query_reservas['pagina'] = pagina.number
    return render(request, 'portal/pages/unidades/aula/cursos.html', {
        **_contexto(unidad, request.user),
        'cursos': cursos,
        'total_cursos': base.count(),
        'total_filtrado': paginador.count,
        'pagina': pagina,
        'consulta_paginacion': urlencode(query_pagina),
        'consulta_paginacion_reservas': urlencode(query_reservas),
        'filtros': filtros,
        'opciones_categorias': Curso.CLASIFICACIONES,
        'opciones_modalidades': list(MODALIDAD_BREVE.items()),
        'opciones_origenes': Curso.ORIGENES,
        'opciones_estados': estados,
        'hay_filtros': any(filtros.values()),
        'grupos': [{'clave': clave, 'titulo': titulo, 'icono': ICONOS_DE_CLASIFICACION[clave],
                    'cursos': [curso for curso in cursos if curso.clasificacion == clave]}
                   for clave, titulo in GRUPOS_DE_CLASIFICACION.items()
                   if any(curso.clasificacion == clave for curso in cursos)],
        'anios': anios,
        'anio': anio,
        'catalogo': catalogo,
        'catalogo_total': catalogo_pagina.paginator.count,
        'catalogo_pagina': catalogo_pagina,
        'reservar_url': f'{unidad.get_absolute_url()}#reservas-servicios',
    })


def _numero_pagina(valor):
    """Acota antes de convertir: QueryDict puede contener miles de dígitos."""
    return int(valor) if 0 < len(valor) <= 6 and valor.isascii() and valor.isdecimal() and int(valor) > 0 else 1


def _estado_tarjeta(curso, hoy):
    if not curso.activo:
        return 'inactivo', 'Inactivo'
    if not curso.publicado:
        return 'borrador', 'Borrador'
    if curso.es_externo:
        return 'externo', 'Información del organizador'
    vigente = curso.edicion_vigente(hoy)
    if not vigente or not (vigente.inicio or vigente.inscripciones_desde or vigente.inscripciones_hasta):
        return 'por_programar', 'Fechas por confirmar'
    return vigente.estado(hoy)


@xframe_options_sameorigin
def curso_unidad_view(request, slug, codigo):
    """La página de un curso: su presentación, de qué trata, sus ediciones, sus instructores y cómo inscribirse."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    curso = get_object_or_404(cursos_visibles(unidad, request.user), codigo=codigo)
    if curso.es_externo:
        return render(request, 'portal/pages/unidades/aula/curso_externo.html', {
            **_contexto(unidad, request.user), 'curso': curso,
            'icono': ICONOS_DE_CLASIFICACION.get(curso.clasificacion, 'fas fa-graduation-cap'),
            'modalidad': MODALIDAD_BREVE[curso.modalidad],
            'todos_url': reverse('cursos_unidad', args=[unidad.slug]),
            'editor_curso_url': reverse('editar_registro', args=[unidad.slug, 'curso', curso.pk]) + '?grupo=oferta'
                if puede_crear_cursos(request.user, unidad) else '',
        })
    hoy = timezone.localdate()
    # Quien edita el curso ve también las ediciones que dejó de ofrecer, para reactivarlas.
    editor = 'edicion_curso' in ediciones_de(request.user, unidad)
    ediciones = [edicion for edicion in curso.ediciones.all() if edicion.activa or editor]
    for edicion in ediciones:
        edicion.momento = edicion.estado(hoy)
    from apps.formacion.presentation.aula_cursos import edicion_solicitada, estado_para, lecciones_de, lecciones_libres, url_con_edicion
    seleccionada = edicion_solicitada(curso, request)
    vigente = seleccionada or curso.edicion_vigente(hoy)
    # El programa es público (títulos y duración); quien lo edita ve también los módulos vacíos y lo no publicado.
    gestor = puede_gestionar_unidad(request.user, unidad)
    programa = [modulo for modulo in lecciones_de(curso, gestor) if modulo.visibles or editor]
    participar = estado_para(curso, request.user, unidad, edicion=seleccionada)
    abierto = gestor or participar['accion'] == 'aula'
    libres = lecciones_libres(programa)
    for modulo in programa:
        for leccion in modulo.visibles:
            leccion.cerrada = not abierto and leccion.pk not in libres
    proxima_sesion = None
    if curso.actividad_catalogo_id:
        proxima_sesion = next((actividad.proxima_sesion for actividad in cursos_de(unidad)
                               if actividad.pk == curso.actividad_catalogo_id), None)
    return render(request, 'portal/pages/unidades/aula/curso.html', {
        **_contexto(unidad, request.user),
        'curso': curso,
        'icono': ICONOS_DE_CLASIFICACION[curso.clasificacion],
        'modalidad': MODALIDAD_BREVE[curso.modalidad],
        'inscripcion': INSCRIPCION_BREVE[curso.inscripcion],
        'ediciones_curso': ediciones,
        'vigente': vigente,
        'edicion_seleccionada': seleccionada,
        'editor_curso_url': reverse('editor_curso', args=[unidad.slug, curso.codigo]) if puede_crear_cursos(request.user, unidad) else '',
        'grupos_url': reverse('grupos_curso', args=[unidad.slug, curso.codigo]) if puede_crear_cursos(request.user, unidad) else '',
        'diseno_certificado_url': reverse('editar_certificado_curso', args=[unidad.slug, curso.codigo]) if puede_crear_cursos(request.user, unidad) else '',
        'momento': vigente.estado(hoy) if vigente else None,
        'proxima_sesion': proxima_sesion,
        'programa': programa,
        'lecciones_total': sum(len(modulo.visibles) for modulo in programa),
        'participar': participar,
        # Quien no está inscrito ve el programa con candados y entra gratis a la primera unidad.
        'primera_unidad_url': url_con_edicion(reverse('aula_curso', args=[unidad.slug, curso.codigo]), seleccionada) if not abierto and libres else '',
        'inscritos_url': url_con_edicion(reverse('inscritos_curso', args=[unidad.slug, curso.codigo]), seleccionada) if puede_crear_cursos(request.user, unidad) else '',
        'calificaciones_url': url_con_edicion(reverse('calificaciones_curso', args=[unidad.slug, curso.codigo]), seleccionada) if puede_crear_cursos(request.user, unidad) else '',
        'por_revisar': EntregaDeber.objects.filter(leccion__modulo__curso=curso, estado='entregada').count(),
        'otros': list(consulta_cursos_visibles(unidad, request.user)
                      .filter(publicado=True, activo=True).exclude(pk=curso.pk)[:6]),
        'todos_url': reverse('cursos_unidad', args=[unidad.slug]),
    })


class NuevoCursoForm(forms.Form):
    nombre = forms.CharField(label='Nombre del curso o evento', max_length=160,
                             widget=forms.TextInput(attrs={'placeholder': 'Por ejemplo: Taller de trazabilidad digital'}))
    clasificacion = forms.ChoiceField(label='Clasificación', choices=Curso.CLASIFICACIONES, initial='corto')
    origen = forms.ChoiceField(label='Dónde se realiza', choices=Curso.ORIGENES, initial='nativo', required=False)
    url_externa = forms.URLField(label='Enlace de la plataforma externa', max_length=1000, required=False,
                                help_text='Para actividades externas: enlace directo a su ficha o inscripción.')
    entidad_organizadora = forms.CharField(label='Institución organizadora', max_length=200, required=False)
    participacion_unidad = forms.ChoiceField(label='Participación de la unidad', choices=Curso.PARTICIPACIONES,
                                           initial='organizador', required=False)
    modalidad = forms.ChoiceField(label='Modalidad', choices=Curso.MODALIDADES, initial='autoguiado')
    duracion_horas = forms.IntegerField(label='Duración (horas)', min_value=1, max_value=2000, required=False)
    anio = forms.IntegerField(label='Año de la primera edición', min_value=2000, max_value=2100, required=False,
                             help_text='Para formación nativa. Los externos gestionan sus convocatorias en su plataforma.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['anio'].initial = timezone.localdate().year

    def clean(self):
        from apps.formacion.models.cursos import validar_enlace_formacion

        datos = super().clean()
        datos['origen'] = datos.get('origen') or 'nativo'
        datos['participacion_unidad'] = datos.get('participacion_unidad') or 'organizador'
        if datos['origen'] == 'nativo' and not datos.get('anio'):
            self.add_error('anio', 'Indica el año de la primera edición.')
        if datos.get('url_externa'):
            try:
                validar_enlace_formacion(datos['url_externa'])
            except forms.ValidationError as error:
                self.add_error('url_externa', error)
        return datos


def codigo_de_curso_nuevo(unidad):
    """SIGLA-CUR-NNN, el siguiente número libre."""
    base = f'{sigla_de_unidad(unidad)}-CUR-'
    # Dos unidades pueden compartir sigla. La cerradura dura hasta guardar la
    # oferta completa y protege también al cargador, que usa transaction.atomic.
    if connection.vendor == 'postgresql' and connection.in_atomic_block:
        llave = crc32(base.encode('utf-8'))
        if llave >= 2**31:
            llave -= 2**32
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s, %s)', [1129665108, llave])
    usados = {codigo.removeprefix(base) for codigo in Curso.objects.filter(codigo__startswith=base).values_list('codigo', flat=True)}
    numero = 1
    while f'{numero:03d}' in usados:
        numero += 1
    return f'{base}{numero:03d}'


@transaction.atomic
def crear_curso(unidad, nombre, clasificacion, modalidad, duracion_horas, anio=None,
                origen='nativo', url_externa='', entidad_organizadora='', participacion_unidad='organizador'):
    unidad = Unidad.objects.select_for_update().get(pk=unidad.pk)
    orden = (Curso.objects.filter(unidad=unidad).order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
    curso = Curso.objects.create(unidad=unidad, codigo=codigo_de_curso_nuevo(unidad), nombre=nombre,
                                 clasificacion=clasificacion, modalidad=modalidad, duracion_horas=duracion_horas,
                                  origen=origen, url_externa=url_externa, entidad_organizadora=entidad_organizadora,
                                  participacion_unidad=participacion_unidad,
                                  emite_certificado=origen == 'nativo', pago_transferencia=origen == 'nativo',
                                 orden=orden, publicado=False, **GUIA_DE_CURSO)
    if origen == 'nativo':
        EdicionCurso.objects.create(curso=curso, nombre=str(anio), anio=anio)
        if clasificacion not in ('webinar', 'seminario', 'conferencia', 'congreso', 'jornada', 'encuentro'):
            crear_esqueleto(curso)
    return curso


# La estructura estándar con que nace todo curso: cada módulo con una lectura breve, uno o dos videos y una actividad
# calificada; al final, el proyecto y la evaluación final, que se habilita al aprobar todo lo demás.
ESQUELETO = [
    ('Bienvenida', 'Cómo funciona el curso y lo indispensable para empezar.', [
        ('texto', 'Cómo funciona el curso', {'contenido': (
            'Cuente en pocas líneas cómo se avanza (en orden; cada evaluación se habilita al terminar lo anterior), qué se '
            'necesita para aprobar y cómo se obtiene el certificado. Agregue lo indispensable para empezar, por ejemplo '
            'las normas de seguridad del área.'), 'duracion_min': 10}),
    ]),
    ('Módulo 1', 'Cambie el título por el tema del módulo y agregue los módulos que necesite con «Nuevo módulo».', [
        ('texto', 'Lectura del tema', {'contenido': (
            'Una lectura breve (una pantalla) con lo esencial del tema y los enlaces a la documentación oficial.'),
            'duracion_min': 15}),
        ('video', 'Video del tema', {'contenido': 'Qué debe observar quien ve el video.', 'publicada': False,
                                     'duracion_min': 10}),
        ('evaluacion', 'Evaluación del módulo', {'contenido': 'Agregue 3 a 5 preguntas con «Nueva pregunta» y publíquela.',
                                                 'nota_minima': 70, 'intentos': 3, 'publicada': False}),
    ]),
    ('Proyecto final y evaluación final', 'El cierre del curso.', [
        ('deber', 'Proyecto final', {'contenido': 'Describa el proyecto que integra lo aprendido y qué se entrega.',
                                     'nota_minima': 70}),
        ('evaluacion', 'Evaluación final', {'contenido': 'Agregue 8 a 10 preguntas que integren todo el curso y publíquela.',
                                            'nota_minima': 70, 'intentos': 3, 'publicada': False}),
    ]),
]


def crear_esqueleto(curso):
    from apps.formacion.models.cursos import LeccionCurso, ModuloCurso

    for orden, (titulo, descripcion, lecciones) in enumerate(ESQUELETO, start=1):
        modulo = ModuloCurso.objects.create(curso=curso, orden=orden, titulo=titulo, descripcion=descripcion)
        for posicion, (tipo, titulo_leccion, datos) in enumerate(lecciones, start=1):
            LeccionCurso.objects.create(modulo=modulo, orden=posicion, tipo=tipo, titulo=titulo_leccion, **datos)


@login_required
def nuevo_curso_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona las prácticas y la docencia de la unidad agrega cursos.')
    formulario = NuevoCursoForm(request.POST or None)
    if request.method == 'POST' and formulario.is_valid():
        with transaction.atomic():
            curso = crear_curso(unidad, **formulario.cleaned_data)
        messages.success(request, 'Actividad creada como borrador. Completa su información antes de publicarla.')
        return _responder(request, reverse('curso_unidad', args=[unidad.slug, curso.codigo]))
    return _pantalla(request, unidad, formulario, 'Nuevo curso o evento',
                     'Elige si se realiza aquí o en una plataforma externa. Los cursos nativos incluyen una estructura '
                     'de aula; los eventos tienen su ficha y convocatoria. Los externos enlazan al organizador y no '
                     'generan un aula ni matrículas locales. La actividad queda como borrador.',
                     reverse('nuevo_curso', args=[unidad.slug]), 'Crear actividad')
