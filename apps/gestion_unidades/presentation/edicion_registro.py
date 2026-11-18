"""Editar en la propia página lo que muestra el visualizador de una unidad, con un mismo cuadro de edición.

Cada página (software, insumos, procesos, productos, la presentación de la unidad, su identidad, novedades,
asignaturas, cursos…) ofrece «Editar» en cada elemento y «Agregar» donde se puede crear, solo a quien tiene el
permiso de la unidad para esa parte. El cuadro muestra los campos que esa página dibuja; lo que necesita más
controles (crear procesos completos, dar permisos al personal) sigue en el panel de gestión.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Max, Q
from django.forms import modelform_factory
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.formacion.models.asignaturas import Asignatura
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso, ReglamentoUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.formacion.models.cursos_inscripcion import CodigoDescuento
from apps.formacion.models.cursos import Curso, EdicionCurso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.gestion_unidades.models.portadas import PortadaPestana
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, Producto, Receta
from apps.gestion_unidades.models.presentacion import HitoUnidad, LineaAccionUnidad, PresentacionUnidad
from apps.gestion_unidades.models.novedades import NovedadUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.referencia_editor import ReferenciaComercialForm
from apps.observatorios.operacion.models.observatorios import AliadoObservatorio, EncuestaObservatorio, IndicadorObservatorio, LineaObservatorio, PoliticaDatosObservatorio, PublicacionObservatorio, SolicitudDatos, TableroObservatorio, ValorIndicador, VisorExterno
from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de
from apps.gestion_unidades.presentation.secciones_propias import puede_editar_secciones


@dataclass(frozen=True)
class Edicion:
    nombre: str
    modelo: type
    campos: tuple
    permiso: str  # un módulo operativo de la unidad, o «contenido» (coordinación o configuración)
    consulta: Callable
    nuevo: Optional[Callable] = None  # cómo nace uno nuevo; sin esto no se crea desde la página
    unico: Optional[Callable] = None  # el registro único de la unidad (su presentación, sus datos) o de una pestaña
    eliminable: bool = False
    grupos: dict = field(default_factory=dict)  # partes de un registro que cada sección de la página edita aparte
    campos_nuevo: tuple = ()  # los campos para crearlo, si son más que los de editarlo
    validar: Optional[Callable] = None  # una regla más, que el modelo no expresa, antes de guardar
    pagina: Optional[Callable] = None  # la página donde se ve lo creado, para abrirla después de crearlo


def _carpeta_nueva(unidad, padre):
    """Una carpeta nace en una sección («s:2.4»), en una pestaña propia («m:12») o dentro de una carpeta de primer
    nivel, en su mismo lugar de la ficha."""
    tipo, _, valor = str(padre or '').partition(':')
    if tipo == 's':
        mapa = mapa_de(unidad)
        if mapa is None or valor not in mapa.secciones:
            raise Http404('Esa sección no existe en esta unidad.')
        modulo = get_object_or_404(ModuloUnidad, unidad=unidad, clave=mapa.modulo_de(valor))
        hermanas = CarpetaRecurso.objects.filter(unidad=unidad, seccion_planta=valor, carpeta_padre__isnull=True)
        return CarpetaRecurso(unidad=unidad, modulo_config=modulo, seccion_planta=valor, orden=_siguiente(hermanas))
    if tipo == 'm':
        modulo = get_object_or_404(ModuloUnidad, unidad=unidad, pk=valor if valor.isdigit() else 0)
        mapa = mapa_de(unidad)
        if mapa is not None and modulo.clave in mapa.pestanas:
            raise Http404('En una pestaña común, la carpeta va dentro de una de sus secciones.')
        hermanas = CarpetaRecurso.objects.filter(unidad=unidad, modulo_config=modulo, carpeta_padre__isnull=True)
        return CarpetaRecurso(unidad=unidad, modulo_config=modulo, orden=_siguiente(hermanas))
    superior = get_object_or_404(CarpetaRecurso, unidad=unidad, del_expediente=False, carpeta_padre__isnull=True,
                                 pk=padre if str(padre).isdigit() else 0)
    return CarpetaRecurso(unidad=unidad, carpeta_padre=superior, modulo_config=superior.modulo_config,
                          seccion_planta=superior.seccion_planta, ficha=superior.ficha, visibilidad=superior.visibilidad,
                          orden=_siguiente(superior.subcarpetas.all()))


def _nombre_de_carpeta_libre(formulario, instancia, unidad):
    nombre = formulario.cleaned_data.get('nombre')
    if CarpetaRecurso.objects.filter(unidad=unidad, nombre=nombre).exclude(pk=instancia.pk).exists():
        raise ValidationError({'nombre': f'Ya hay una carpeta «{nombre}» en esta unidad: los nombres no se repiten.'})


def _portada_de(unidad, pk):
    modulo = get_object_or_404(ModuloUnidad, unidad=unidad, pk=pk if str(pk).isdigit() else 0)
    return PortadaPestana.objects.filter(modulo=modulo).first() or PortadaPestana(modulo=modulo)


def _siguiente(consulta, campo='orden'):
    return (consulta.aggregate(Max(campo))[f'{campo}__max'] or 0) + 1


def _hijo(modelo, padres, padre, campo, relacion):
    """Un módulo dentro de su curso o una lección dentro de su módulo, al final de sus hermanos."""
    superior = get_object_or_404(padres, pk=padre if str(padre).isdigit() else 0)
    return modelo(**{campo: superior, 'orden': _siguiente(getattr(superior, relacion).all())})


def _valor_nuevo(unidad, padre):
    """Un valor nace dentro de su indicador, que debe ser de este observatorio."""
    indicador = get_object_or_404(IndicadorObservatorio, unidad=unidad, pk=padre if str(padre).isdigit() else 0)
    return ValorIndicador(indicador=indicador, territorio=indicador.territorio_principal)


def _solicitud_atendida(formulario, instancia, unidad):
    """Al cerrar una solicitud queda la fecha en que se atendió."""
    if instancia.estado in ('atendida', 'rechazada') and not instancia.atendida:
        instancia.atendida = timezone.now()


def _codigo_libre(formulario, instancia):
    """Un código no se repite en el mismo curso (sin importar mayúsculas)."""
    codigo = (formulario.cleaned_data.get('codigo') or '').strip().upper()
    if CodigoDescuento.objects.filter(curso=instancia.curso, codigo=codigo).exclude(pk=instancia.pk).exists():
        raise ValidationError({'codigo': f'El curso ya tiene un código «{codigo}».'})
    if formulario.cleaned_data.get('eliminar') and instancia.pk and instancia.pagos.exists():
        raise ValidationError('Ese código ya se usó: no se elimina. Desmarque «Activo» para que no se use más.')


def _edicion_valida(formulario, instancia):
    """El nombre de la edición no se repite en el curso, y una edición con inscritos no se elimina."""
    nombre = (formulario.cleaned_data.get('nombre') or '').strip()
    if EdicionCurso.objects.filter(curso=instancia.curso, nombre__iexact=nombre).exclude(pk=instancia.pk).exists():
        raise ValidationError({'nombre': f'El curso ya tiene una edición «{nombre}».'})
    if instancia.pk:
        ocupadas = (instancia.inscripciones.filter(estado='aceptada').count()
                    + instancia.invitaciones.filter(activa=True, inscripcion__isnull=True).count())
        if instancia.cupo is not None and instancia.cupo < ocupadas:
            raise ValidationError({'cupo': f'Ya hay {ocupadas} plazas ocupadas o reservadas; el cupo no puede ser menor.'})
        if formulario.cleaned_data.get('eliminar') and instancia.invitaciones.filter(activa=True, inscripcion__isnull=True).exists():
            raise ValidationError('Tiene invitaciones pendientes: desactive el grupo en lugar de eliminarlo.')
    _sin_inscritos(formulario, instancia.inscripciones.all() if instancia.pk else None)
    if instancia.pk and formulario.cleaned_data.get('eliminar') and (
            instancia.participantes_evento.exists() or instancia.invitaciones.exists()):
        raise ValidationError('Este grupo tiene participantes o invitaciones registradas. Desactívalo para conservar el historial.')


def _sin_inscritos(formulario, inscripciones):
    """Lo que ya tiene inscritos no se elimina: se deja de ofrecer o se despublica."""
    if formulario.cleaned_data.get('eliminar') and inscripciones is not None and inscripciones.exists():
        raise ValidationError('Tiene personas inscritas: no se elimina. Déjelo sin publicar o desmarque «Se ofrece».')


def _curso_valido(formulario, instancia, unidad):
    """La edición de la ficha conserva todas las identidades y evidencias."""
    if formulario.cleaned_data.get('eliminar'):
        instancia.validar_eliminacion()


def _contenido_academico_valido(formulario, instancia, unidad):
    """Conserva los registros de aprendizaje al editar el programa de un curso."""
    if not instancia.pk:
        if isinstance(instancia, PreguntaEvaluacion) and instancia.leccion.intentos_rendidos.exists():
            raise ValidationError('Esta evaluación ya fue rendida. Crea otra evaluación para agregar preguntas y conservar el historial.')
        return
    eliminar = formulario.cleaned_data.get('eliminar')
    if isinstance(instancia, ModuloCurso):
        if eliminar and instancia.lecciones.filter(
            Q(progresos__isnull=False) | Q(intentos_rendidos__isnull=False) | Q(entregas__isnull=False)
        ).exists():
            raise ValidationError('Este módulo tiene actividad académica registrada. Conserva sus lecciones y déjalas sin publicar si ya no se utilizan.')
    elif isinstance(instancia, LeccionCurso):
        actividad = (instancia.progresos.exists() or instancia.intentos_rendidos.exists()
                     or instancia.entregas.exists())
        if eliminar and actividad:
            raise ValidationError('Esta lección tiene avances, intentos o entregas registrados. Déjala sin publicar en lugar de eliminarla.')
        if actividad and 'tipo' in formulario.changed_data:
            original = LeccionCurso.objects.only('tipo').get(pk=instancia.pk)
            if original.tipo != instancia.tipo:
                raise ValidationError({'tipo': 'Esta lección ya tiene actividad académica. Crea otra lección para utilizar un tipo diferente.'})
    elif isinstance(instancia, PreguntaEvaluacion):
        evaluada = instancia.leccion.intentos_rendidos.exists()
        respuestas = {'tipo', 'opciones', 'respuestas_aceptadas', 'puntos'}
        if evaluada and (eliminar or respuestas.intersection(formulario.changed_data)):
            raise ValidationError('Esta pregunta pertenece a una evaluación que ya fue rendida. Conserva sus respuestas y puntuación para mantener el historial.')


REGISTRO = {
    'software': Edicion(
        'Programa', SoftwareDisponible,
        ('nombre', 'version', 'descripcion', 'tipo_recurso', 'tipo_acceso', 'uso_en_equipo', 'licencias_totales',
         'licencias_disponibles', 'requiere_reserva', 'sitio_web', 'logo', 'instrucciones_acceso', 'activo'),
        'recursos', lambda unidad: SoftwareDisponible.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: SoftwareDisponible(unidad=unidad, licencias_totales=1, licencias_disponibles=1),
        pagina=lambda unidad, instancia: reverse('software_unidad', args=[unidad.slug])),
    'insumo': Edicion(
        'Insumo o material', Consumible,
        ('nombre', 'codigo', 'clasificacion', 'familia', 'marca', 'descripcion', 'presentacion',
         'cantidad_por_presentacion', 'unidad_medida', 'especificacion_tecnica', 'ubicacion', 'instrucciones_solicitud',
         'sustancia_controlada', 'autorizacion_control', 'imagen', 'visible_en_reservas', 'activo'),
        'inventario', lambda unidad: Consumible.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: Consumible(unidad=unidad),
        pagina=lambda unidad, instancia: reverse('insumos_unidad', args=[unidad.slug])),
    'proceso': Edicion(
        'Proceso', Receta, ('nombre', 'instrucciones', 'duracion_horas', 'activa'),
        'produccion', lambda unidad: Receta.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: Receta(unidad=unidad, cantidad_base=1, rendimiento_esperado=100, activa=False),
        campos_nuevo=('nombre', 'codigo', 'producto', 'cantidad_base', 'unidad_base', 'rendimiento_esperado',
                      'instrucciones', 'duracion_horas'),
        pagina=lambda unidad, instancia: reverse('proceso_laboratorio', args=[unidad.slug, instancia.pk])),
    'etapa': Edicion(
        'Etapa del proceso', EtapaReceta,
        ('orden', 'nombre', 'tipo', 'espacio', 'equipo', 'duracion_min', 'personas', 'instrucciones', 'parametro',
         'limite', 'punto_control'),
        'produccion', lambda unidad: EtapaReceta.objects.filter(receta__unidad=unidad),
        nuevo=lambda unidad, padre: EtapaReceta(
            receta=get_object_or_404(Receta, unidad=unidad, pk=padre or 0),
            orden=_siguiente(EtapaReceta.objects.filter(receta_id=padre or 0))),
        eliminable=True),
    'producto': Edicion(
        'Producto o servicio', Producto,
        ('nombre', 'codigo', 'tipo', 'descripcion', 'presentacion', 'unidad_medida', 'publico', 'activo'),
        'produccion', lambda unidad: Producto.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: Producto(unidad=unidad, unidad_medida='unidad'),
        pagina=lambda unidad, instancia: reverse('productos_laboratorio', args=[unidad.slug])),
    'presentacion': Edicion(
        'Presentación de la unidad', PresentacionUnidad,
        ('lema', 'que_es', 'que_hace', 'capacidades', 'areas_trabajo', 'video_url', 'video_presenta', 'mision',
         'vision', 'objetivos', 'historia', 'beneficiarios', 'resultados', 'publicada'),
        'contenido', lambda unidad: PresentacionUnidad.objects.filter(unidad=unidad),
        unico=lambda unidad, pk: PresentacionUnidad.objects.filter(unidad=unidad).first() or PresentacionUnidad(unidad=unidad),
        grupos={
            'quienes': ('Quiénes somos', ('lema', 'que_es', 'que_hace', 'capacidades', 'areas_trabajo', 'publicada')),
            'video': ('Video de presentación', ('video_url', 'video_presenta')),
            'rumbo': ('Misión, visión y objetivos', ('mision', 'vision', 'objetivos')),
            'historia': ('Historia', ('historia',)),
            'impacto': ('Beneficiarios y resultados', ('beneficiarios', 'resultados')),
        }),
    'linea': Edicion(
        'Línea de acción', LineaAccionUnidad, ('titulo', 'descripcion', 'icono', 'orden'),
        'contenido', lambda unidad: LineaAccionUnidad.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: LineaAccionUnidad(unidad=unidad, orden=_siguiente(unidad.lineas_accion.all())),
        eliminable=True),
    'hito': Edicion(
        'Hito de la historia', HitoUnidad, ('anio', 'mes', 'tipo', 'titulo', 'descripcion', 'enlace'),
        'contenido', lambda unidad: HitoUnidad.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: HitoUnidad(unidad=unidad), eliminable=True),
    'unidad': Edicion(
        'Datos de la unidad', Unidad,
        ('descripcion_corta', 'area_conocimiento', 'modo_operacion', 'carreras', 'horario_atencion',
         'capacidad_personas', 'ubicacion', 'piso', 'direccion', 'contacto_email', 'telefono', 'celular', 'sitio_web',
         'resolucion_numero', 'fecha_resolucion', 'fecha_inicio'),
        'contenido', lambda unidad: Unidad.objects.filter(pk=unidad.pk), unico=lambda unidad, pk: unidad,
        grupos={
            'identidad': ('Identidad', ('descripcion_corta', 'area_conocimiento', 'modo_operacion', 'carreras')),
            'atencion': ('Operación y contacto', ('horario_atencion', 'capacidad_personas', 'ubicacion', 'piso',
                                                  'direccion', 'contacto_email', 'telefono', 'celular', 'sitio_web')),
            'creacion': ('Creación y trayectoria', ('resolucion_numero', 'fecha_resolucion', 'fecha_inicio')),
        }),
    # La portada animada de una pestaña: su frase, su texto, su estilo, su imagen o una escena 3D publicada.
    'portada': Edicion(
        'Portada de la pestaña', PortadaPestana, ('lema', 'descripcion', 'tema', 'imagen', 'escena_3d'),
        'contenido', lambda unidad: PortadaPestana.objects.filter(modulo__unidad=unidad),
        unico=lambda unidad, pk: _portada_de(unidad, pk)),
    # El rol y los permisos del personal se gestionan en el panel: aquí solo lo que el público ve de cada persona.
    'responsable': Edicion(
        'Persona del equipo', ResponsableUnidad,
        ('nombre', 'email', 'telefono', 'foto', 'descripcion', 'horario_atencion', 'publico', 'orden'),
        'contenido', lambda unidad: ResponsableUnidad.objects.filter(unidad=unidad)),
    # El reglamento de uso: la unidad lo escribe y lo publica; publicado, se ve en la ficha y es el documento
    # «Reglamento de uso de la unidad» del Centro de reportes.
    'reglamento': Edicion(
        'Reglamento de uso', ReglamentoUnidad,
        ('titulo', 'subtitulo', 'normas_generales', 'reservas_horarios', 'equipos_materiales', 'seguridad',
         'contacto_texto', 'contacto_email', 'activo'),
        'contenido', lambda unidad: ReglamentoUnidad.objects.filter(unidad=unidad),
        unico=lambda unidad, pk: ReglamentoUnidad.objects.get_or_create(unidad=unidad)[0]),
    'novedad': Edicion(
        'Novedad', NovedadUnidad,
        ('titulo', 'categoria', 'resumen', 'cuerpo', 'imagen', 'enlace', 'fecha_publicacion', 'fecha_evento', 'lugar',
         'cierre', 'publicada', 'destacada'),
        'contenido', lambda unidad: NovedadUnidad.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: NovedadUnidad(unidad=unidad), eliminable=True,
        pagina=lambda unidad, instancia: reverse('novedades_unidad', args=[unidad.slug])),
    'asignatura': Edicion(
        'Asignatura', Asignatura,
        ('nombre', 'codigo', 'carrera', 'semestre', 'periodo', 'docente', 'estudiantes', 'descripcion', 'activa'),
        'practicas', lambda unidad: Asignatura.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: Asignatura(unidad=unidad),
        pagina=lambda unidad, instancia: reverse('asignaturas_unidad', args=[unidad.slug])),
    # Carpetas y archivos propios del menú: aquí se renombran y se decide quién los ve; ocultarlos, moverlos o
    # eliminarlos se hace en el organizador de contenidos, donde lo oculto sigue a la vista. Los archivos se suben
    # por el formulario que valida tipo, tamaño y seguridad.
    'carpeta': Edicion(
        'Carpeta', CarpetaRecurso, ('nombre', 'visibilidad'),
        'contenido', lambda unidad: CarpetaRecurso.objects.filter(unidad=unidad, del_expediente=False),
        nuevo=lambda unidad, padre: _carpeta_nueva(unidad, padre), validar=lambda *datos: _nombre_de_carpeta_libre(*datos)),
    'archivo': Edicion(
        'Archivo o enlace', Recurso, ('nombre', 'descripcion', 'visibilidad', 'descargar'),
        'contenido', lambda unidad: Recurso.objects.filter(unidad=unidad).exclude(carpeta__del_expediente=True)),
    # Cada curso se edita en su página, por partes; sus ediciones por año se agregan desde la misma página.
    'curso': Edicion(
        'Curso o capacitación', Curso,
        ('nombre', 'lema', 'clasificacion', 'modalidad', 'imagen', 'video_url', 'publicado', 'activo',
         'origen', 'url_externa', 'entidad_organizadora', 'participacion_unidad', 'descripcion',
         'aprendizajes', 'dirigido_a', 'requisitos', 'duracion_horas', 'costo', 'inscripcion', 'emite_certificado',
         'firma_nombre', 'firma_cargo', 'actividad_catalogo', 'instructores', 'pago_transferencia', 'pago_ventanilla',
         'pago_enlace', 'enlace_pago', 'datos_pago', 'orden'),
        'practicas', lambda unidad: Curso.objects.filter(unidad=unidad), eliminable=True,
        validar=_curso_valido,
        grupos={
            'presentacion': ('Presentación del curso', ('nombre', 'lema', 'clasificacion', 'modalidad', 'imagen',
                                                        'video_url', 'publicado', 'activo')),
            'oferta': ('Plataforma y entidad organizadora', ('origen', 'url_externa', 'entidad_organizadora',
                                                           'participacion_unidad')),
            'contenido': ('De qué trata', ('descripcion', 'aprendizajes', 'dirigido_a', 'requisitos')),
            'datos': ('Duración, inscripción y certificado', ('duracion_horas', 'inscripcion', 'emite_certificado',
                                                        'firma_nombre', 'firma_cargo', 'actividad_catalogo', 'orden')),
            'duracion': ('Duración de la actividad externa', ('duracion_horas', 'orden')),
            'instructores': ('Instructores', ('instructores',)),
            'pagos': ('Costo y medios de pago', ('costo', 'pago_transferencia', 'pago_ventanilla', 'pago_enlace', 'enlace_pago',
                                                 'datos_pago')),
        }),
    'edicion_curso': Edicion(
        'Edición del curso', EdicionCurso,
        ('nombre', 'tipo_grupo', 'destinatario', 'anio', 'inicio', 'fin', 'horas_certificadas', 'inscripciones_desde',
         'inscripciones_hasta', 'cupo', 'horario', 'lugar', 'activa'),
        'practicas', lambda unidad: EdicionCurso.objects.filter(curso__unidad=unidad),
        nuevo=lambda unidad, padre: EdicionCurso(curso=get_object_or_404(Curso, unidad=unidad,
                                                                         pk=padre if str(padre).isdigit() else 0),
                                                 anio=timezone.localdate().year),
        eliminable=True,
        validar=lambda formulario, instancia, unidad: _edicion_valida(formulario, instancia)),
    # Los códigos de descuento de un curso se crean desde su página de inscritos; al 100 %, el curso queda gratis.
    'codigo_descuento': Edicion(
        'Código de descuento', CodigoDescuento,
        ('codigo', 'descripcion', 'porcentaje', 'usos_maximos', 'vigente_hasta', 'activo'),
        'practicas', lambda unidad: CodigoDescuento.objects.filter(curso__unidad=unidad),
        nuevo=lambda unidad, padre: CodigoDescuento(curso=get_object_or_404(Curso, unidad=unidad,
                                                                            pk=padre if str(padre).isdigit() else 0)),
        eliminable=True,
        validar=lambda formulario, instancia, unidad: _codigo_libre(formulario, instancia)),
    'modulo_curso': Edicion(
        'Módulo del curso', ModuloCurso, ('orden', 'titulo', 'descripcion'),
        'practicas', lambda unidad: ModuloCurso.objects.filter(curso__unidad=unidad),
        nuevo=lambda unidad, padre: _hijo(ModuloCurso, Curso.objects.filter(unidad=unidad), padre, 'curso', 'modulos'),
        eliminable=True, validar=_contenido_academico_valido),
    'leccion_curso': Edicion(
        'Lección del curso', LeccionCurso,
        ('orden', 'titulo', 'tipo', 'contenido', 'video_url', 'archivo', 'sala', 'enlace', 'reunion_url', 'fecha_hora',
         'lugar',
         'duracion_min', 'grabacion_url', 'nota_minima', 'intentos', 'fecha_limite', 'obligatoria', 'publicada'),
        'practicas', lambda unidad: LeccionCurso.objects.filter(modulo__curso__unidad=unidad),
        nuevo=lambda unidad, padre: _hijo(LeccionCurso, ModuloCurso.objects.filter(curso__unidad=unidad), padre,
                                          'modulo', 'lecciones'),
        eliminable=True, validar=_contenido_academico_valido),
    # Las preguntas de una evaluación se agregan y editan desde la vista previa del aula.
    'pregunta_curso': Edicion(
        'Pregunta de la evaluación', PreguntaEvaluacion,
        ('orden', 'enunciado', 'tipo', 'opciones', 'respuestas_aceptadas', 'puntos', 'explicacion'),
        'practicas', lambda unidad: PreguntaEvaluacion.objects.filter(leccion__modulo__curso__unidad=unidad),
        nuevo=lambda unidad, padre: _hijo(PreguntaEvaluacion, LeccionCurso.objects.filter(
            modulo__curso__unidad=unidad, tipo='evaluacion'), padre, 'leccion', 'preguntas'),
        eliminable=True, validar=_contenido_academico_valido),
    # Lo propio de un observatorio: lo edita quien coordina su contenido, desde las páginas donde se ve.
    'indicador_observatorio': Edicion(
        'Indicador del observatorio', IndicadorObservatorio,
        ('nombre', 'codigo', 'pregunta', 'definicion', 'formula', 'unidad_medida', 'fuente', 'tipo_fuente', 'url_fuente',
         'periodicidad', 'desagregacion', 'limitaciones', 'sentido', 'umbral_bajo', 'umbral_alto', 'alerta_variacion', 'mensaje_alerta',
         'territorio_principal', 'linea', 'fuente_datos', 'orden', 'publicado'),
        'contenido', lambda unidad: IndicadorObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: IndicadorObservatorio(
            unidad=unidad, orden=_siguiente(IndicadorObservatorio.objects.filter(unidad=unidad))),
        eliminable=True,
        pagina=lambda unidad, instancia: reverse('indicador_observatorio', args=[unidad.slug, instancia.codigo])),
    'valor_indicador': Edicion(
        'Valor del indicador', ValorIndicador, ('periodo', 'fecha', 'territorio', 'valor', 'provisional', 'nota'),
        'contenido', lambda unidad: ValorIndicador.objects.filter(indicador__unidad=unidad),
        nuevo=_valor_nuevo, eliminable=True,
        pagina=lambda unidad, instancia: reverse('indicador_observatorio', args=[unidad.slug, instancia.indicador.codigo])),
    'publicacion_observatorio': Edicion(
        'Publicación del observatorio', PublicacionObservatorio,
        ('tipo', 'titulo', 'periodo', 'resumen', 'fecha_planificada', 'estado', 'fecha_publicada', 'archivo', 'enlace',
         'indicadores'),
        'contenido', lambda unidad: PublicacionObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: PublicacionObservatorio(unidad=unidad), eliminable=True,
        pagina=lambda unidad, instancia: reverse('calendario_observatorio', args=[unidad.slug])),
    'encuesta_observatorio': Edicion(
        'Encuesta del observatorio', EncuestaObservatorio,
        ('nombre', 'objetivo', 'poblacion', 'muestra', 'periodicidad', 'ultimo_levantamiento', 'instrumento',
         'proteccion_datos', 'orden', 'activa'),
        'contenido', lambda unidad: EncuestaObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: EncuestaObservatorio(
            unidad=unidad, orden=_siguiente(EncuestaObservatorio.objects.filter(unidad=unidad))),
        eliminable=True, pagina=lambda unidad, instancia: reverse('encuestas_observatorio', args=[unidad.slug])),
    'aliado_observatorio': Edicion(
        'Aliado del observatorio', AliadoObservatorio,
        ('nombre', 'tipo', 'rol', 'aporte', 'convenio', 'enlace', 'orden', 'activo'),
        'contenido', lambda unidad: AliadoObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: AliadoObservatorio(
            unidad=unidad, orden=_siguiente(AliadoObservatorio.objects.filter(unidad=unidad))),
        eliminable=True, pagina=lambda unidad, instancia: reverse('aliados_observatorio', args=[unidad.slug])),
    # La respuesta a una solicitud: el estado y lo que se le contesta a quien la hizo.
    'solicitud_datos': Edicion(
        'Solicitud de datos', SolicitudDatos, ('estado', 'respuesta'),
        'contenido', lambda unidad: SolicitudDatos.objects.filter(unidad=unidad),
        validar=_solicitud_atendida,
        pagina=lambda unidad, instancia: reverse('solicitudes_observatorio', args=[unidad.slug])),
    # Los ejes temáticos del observatorio, como las áreas de un laboratorio: su ficha, sus fotos y sus videos.
    'linea_observatorio': Edicion(
        'Eje temático del observatorio', LineaObservatorio,
        ('titulo', 'icono', 'resumen', 'que_estudia', 'por_que_importa', 'preguntas', 'como_trabaja', 'productos',
         'usuarios', 'carreras', 'temas_investigacion', 'pendiente', 'videos', 'orden', 'publicada'),
        'contenido', lambda unidad: LineaObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: LineaObservatorio(
            unidad=unidad, orden=_siguiente(LineaObservatorio.objects.filter(unidad=unidad))),
        campos_nuevo=('codigo', 'titulo', 'icono', 'resumen', 'que_estudia', 'por_que_importa', 'preguntas',
                      'como_trabaja', 'productos', 'usuarios', 'carreras', 'temas_investigacion', 'pendiente', 'videos', 'orden',
                      'publicada'),
        eliminable=True, pagina=lambda unidad, instancia: reverse('linea_observatorio', args=[unidad.slug, instancia.codigo])),
    # Los ejes productivos de un centro experimental, como las áreas de un laboratorio: su ficha y sus videos.
    'eje_productivo': Edicion(
        'Eje productivo del centro', EjeProductivo,
        ('titulo', 'icono', 'resumen', 'que_produce', 'rubros', 'como_trabaja', 'calendario', 'destino', 'para_quien',
         'practicas', 'temas_investigacion', 'para_producir_mas', 'videos', 'espacios', 'orden', 'publicado'),
        'contenido', lambda unidad: EjeProductivo.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: EjeProductivo(
            unidad=unidad, orden=_siguiente(EjeProductivo.objects.filter(unidad=unidad))),
        campos_nuevo=('codigo', 'titulo', 'icono', 'resumen', 'que_produce', 'rubros', 'como_trabaja', 'calendario',
                      'destino', 'para_quien', 'practicas', 'temas_investigacion', 'para_producir_mas', 'videos',
                      'espacios', 'orden', 'publicado'),
        eliminable=True, pagina=lambda unidad, instancia: reverse('eje_centro', args=[unidad.slug, instancia.codigo])),
    # Los ciclos de la gestión productiva: los planifica quien tiene el módulo de producción del centro. Un ciclo
    # marcado como ensayo declara además su objetivo, sus tratamientos, sus repeticiones y lo que se mide.
    'ciclo_productivo': Edicion(
        'Ciclo productivo', CicloProductivo,
        ('nombre', 'tipo', 'rubro', 'lugar', 'inicio', 'fin_previsto', 'fin', 'superficie_ha', 'animales', 'meta',
         'unidad_medida', 'referencia', 'estado', 'responsable', 'es_ensayo', 'objetivo', 'tratamientos',
         'repeticiones', 'variables', 'notas'),
        'produccion', lambda unidad: CicloProductivo.objects.filter(eje__unidad=unidad),
        nuevo=lambda unidad, padre: CicloProductivo(),
        campos_nuevo=('eje', 'nombre', 'tipo', 'rubro', 'lugar', 'inicio', 'fin_previsto', 'superficie_ha', 'animales',
                      'meta', 'unidad_medida', 'referencia', 'estado', 'responsable', 'es_ensayo', 'objetivo',
                      'tratamientos', 'repeticiones', 'variables', 'notas'),
        eliminable=True, pagina=lambda unidad, instancia: reverse('produccion_centro', args=[unidad.slug])),
    # Los tableros nativos, los visores externos y la política de datos del observatorio.
    'tablero_observatorio': Edicion(
        'Tablero del observatorio', TableroObservatorio,
        ('titulo', 'descripcion', 'linea', 'vista', 'indicadores', 'orden', 'publicado'),
        'contenido', lambda unidad: TableroObservatorio.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: TableroObservatorio(
            unidad=unidad, orden=_siguiente(TableroObservatorio.objects.filter(unidad=unidad))),
        eliminable=True, pagina=lambda unidad, instancia: reverse('tableros_observatorio', args=[unidad.slug])),
    'visor_externo': Edicion(
        'Visor externo del observatorio', VisorExterno,
        ('titulo', 'descripcion', 'linea', 'plataforma', 'institucion', 'url', 'url_datos', 'responsable',
         'fecha_corte', 'orden', 'publicado'),
        'contenido', lambda unidad: VisorExterno.objects.filter(unidad=unidad),
        nuevo=lambda unidad, padre: VisorExterno(
            unidad=unidad, orden=_siguiente(VisorExterno.objects.filter(unidad=unidad))),
        eliminable=True, pagina=lambda unidad, instancia: reverse('tableros_observatorio', args=[unidad.slug])),
    'politica_datos': Edicion(
        'Política de datos', PoliticaDatosObservatorio,
        ('licencia', 'abiertos', 'por_solicitud', 'por_convenio', 'reservados', 'servicios_pagados', 'cita'),
        'contenido', lambda unidad: PoliticaDatosObservatorio.objects.filter(unidad=unidad),
        unico=lambda unidad, pk: (PoliticaDatosObservatorio.objects.filter(unidad=unidad).first()
                                  or PoliticaDatosObservatorio(unidad=unidad)),
        pagina=lambda unidad, instancia: reverse('politica_observatorio', args=[unidad.slug])),
    # Las capacitaciones que solo existen como actividad del catálogo de reservas.
    'actividad_curso': Edicion(
        'Capacitación del catálogo de reservas', CatalogoActividadReserva,
        ('nombre', 'descripcion', 'responsable', 'activo'),
        'practicas', lambda unidad: CatalogoActividadReserva.objects.filter(unidad=unidad)),
}


def _permitido(usuario, unidad, permiso):
    if permiso == 'contenido':
        return puede_editar_secciones(usuario, unidad)
    return puede_operar_modulo_unidad(usuario, unidad, permiso)


def ediciones_de(usuario, unidad):
    """Las partes de la ficha que esta persona puede editar en la página de esta unidad."""
    if usuario is None or not usuario.is_authenticated:
        return frozenset()
    permisos = {permiso: _permitido(usuario, unidad, permiso) for permiso in {e.permiso for e in REGISTRO.values()}}
    return frozenset(clave for clave, edicion in REGISTRO.items() if permisos[edicion.permiso])


def personal_de(unidad, conservar=None):
    """Las cuentas que pueden responder por un registro de la unidad: sus responsables activos y su administrador.

    «conservar» es quien ya responde por el registro que se edita: sigue en la lista aunque haya dejado la unidad,
    para que editar otro dato no lo borre.
    """
    cuentas = Q(responsabilidades_en_unidades__unidad=unidad, responsabilidades_en_unidades__activo=True)
    for pk in (unidad.administrador_id, conservar):
        if pk:
            cuentas |= Q(pk=pk)
    return get_user_model().objects.filter(cuentas).distinct().order_by('first_name', 'last_name', 'username')


def _nombre_de_persona(usuario):
    return usuario.get_full_name() or usuario.username


def _campo(db_field, unidad, **kwargs):
    """Cada campo con el control adecuado y, si apunta a otro registro, solo los de esta unidad."""
    if isinstance(db_field, models.DateTimeField):
        kwargs['widget'] = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    elif isinstance(db_field, models.DateField):
        kwargs['widget'] = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
    elif isinstance(db_field, models.TextField):
        kwargs['widget'] = forms.Textarea(attrs={'rows': 4})
    campo = db_field.formfield(**kwargs)
    if (campo is not None and isinstance(db_field, models.ManyToManyField)
            and db_field.related_model is IndicadorObservatorio):
        campo.queryset = IndicadorObservatorio.objects.filter(unidad=unidad).order_by('orden', 'nombre')
    if (campo is not None and isinstance(db_field, models.ManyToManyField)
            and db_field.related_model is EspacioReservable):
        campo.queryset = EspacioReservable.objects.filter(unidad=unidad).order_by('orden', 'nombre')
    if campo is not None and isinstance(db_field, models.ForeignKey):
        destino = db_field.related_model
        if destino is EspacioReservable:
            campo.queryset = EspacioReservable.objects.filter(unidad=unidad).order_by('orden', 'nombre')
        elif destino is EjeProductivo:
            campo.queryset = EjeProductivo.objects.filter(unidad=unidad).order_by('orden', 'titulo')
        elif destino is LineaObservatorio:
            campo.queryset = LineaObservatorio.objects.filter(unidad=unidad).order_by('orden', 'titulo')
        elif destino is EquiposServicios:
            tipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).values('equipo_id')
            campo.queryset = EquiposServicios.objects.filter(pk__in=tipos).order_by('nombre')
        elif destino is Producto:
            campo.queryset = Producto.objects.filter(unidad=unidad).order_by('nombre')
        elif destino is CatalogoActividadReserva:
            campo.queryset = CatalogoActividadReserva.objects.filter(
                unidad=unidad, proposito_codigo='capacitacion').order_by('nombre')
        elif destino is get_user_model() and db_field.name == 'responsable':
            # Un responsable es del personal de la unidad, no cualquier cuenta de la plataforma.
            campo.queryset = personal_de(unidad)
            campo.label_from_instance = _nombre_de_persona
            campo.help_text = 'Solo el personal registrado de la unidad y su administrador.'
    return campo


# Lo que se escribe en cada campo, a la vista mientras está vacío.
GUIAS = {
    'nombre': 'El nombre como lo conoce quien lo usa', 'titulo': 'Un título corto y claro',
    'descripcion': 'Para qué sirve, quién lo usa y qué obtiene, en dos o tres frases',
    'instrucciones': 'Cómo se hace, paso a paso', 'resumen': 'Una o dos frases que inviten a leer más',
    'presentacion': 'Cómo se entrega o se compra: caja, rollo, licencia…', 'ubicacion': 'Dónde se guarda o se encuentra',
    'que_es': 'Qué es la unidad, en dos o tres frases', 'que_hace': 'Qué hace: docencia, servicios, investigación…',
    'objetivos': 'Un objetivo por línea', 'beneficiarios': 'A quién atiende, uno por línea',
    'resultados': 'Un resultado o aporte por línea', 'parametro': 'Qué se mide o controla en esta etapa',
    'limite': 'El valor que no se debe pasar', 'sitio_web': 'https://…', 'enlace': 'https://…',
    'instrucciones_acceso': 'Cómo se pide o se entra al programa',
    'lema': 'Por ejemplo: «Tecnología para aprender haciendo»', 'escena_3d': 'https://my.spline.design/…',
    'video_url': 'https://www.youtube.com/watch?v=…', 'aprendizajes': 'Un aprendizaje por línea, empezando con un verbo',
    'dirigido_a': 'Estudiantes de qué carreras, docentes, público externo…', 'requisitos': 'Un requisito por línea',
    'instructores': 'Nombre | Lo que enseña o su cargo, uno por línea', 'horario': 'Martes y jueves, 15:00 a 17:00',
    'lugar': 'Un área de la unidad, un aula o «Virtual»',
    'contenido': 'El texto de la lectura o, en un video, material o clase, qué hacer con él',
    'enunciado': '¿Qué pregunta debe responder quien rinde la evaluación?',
    'opciones': '*La opción correcta\nOtra opción\nOtra opción más',
    'respuestas_aceptadas': 'Cada forma válida de escribir la respuesta, una por línea',
    'explicacion': 'Por qué esa es la respuesta: se muestra después de responder',
    # «Modelo.campo»: solo en ese modelo (otro modelo usa el mismo nombre de campo para otra cosa).
    'CicloProductivo.objetivo': 'Qué se quiere comprobar. Por ejemplo: «Comparar el rendimiento de la papa con tres '
                                'dosis de nitrógeno»',
    'CicloProductivo.tratamientos': 'Uno por línea:\nT1 · Testigo sin fertilizar\nT2 · 60 kg de N/ha\nT3 · 120 kg de N/ha',
    'CicloProductivo.variables': 'Una por línea, con su unidad: altura de planta (cm), rendimiento (t/ha)…',
}

# Rótulos que algunos modelos traen sin tilde o con el nombre interno del campo. «Modelo.campo» vale solo en ese modelo.
ROTULOS = {
    'version': 'Versión', 'descripcion': 'Descripción', 'tipo_recurso': 'Tipo de recurso', 'tipo_acceso': 'Tipo de acceso',
    'uso_en_equipo': 'Uso en el equipo', 'instrucciones_acceso': 'Instrucciones de acceso', 'codigo': 'Código',
    'clasificacion': 'Clasificación', 'presentacion': 'Presentación', 'unidad_medida': 'Unidad de medida',
    'cantidad_por_presentacion': 'Cantidad por presentación', 'especificacion_tecnica': 'Especificación técnica',
    'ubicacion': 'Ubicación', 'instrucciones_solicitud': 'Instrucciones para solicitarlo',
    'visible_en_reservas': 'Se ofrece en las reservas', 'duracion_horas': 'Duración (horas)',
    'duracion_min': 'Duración (minutos)', 'parametro': 'Parámetro que se controla', 'limite': 'Límite',
    'punto_control': 'Punto de control', 'que_es': 'Qué es', 'que_hace': 'Qué hace', 'areas_trabajo': 'Áreas de trabajo',
    'mision': 'Misión', 'vision': 'Visión', 'video_url': 'Enlace del video', 'anio': 'Año', 'icono': 'Ícono',
    'telefono': 'Teléfono', 'celular': 'Celular', 'contacto_email': 'Correo de contacto', 'horario_atencion': 'Horario de atención',
    'capacidad_personas': 'Capacidad (personas)', 'direccion': 'Dirección', 'resolucion_numero': 'Resolución de creación',
    'fecha_resolucion': 'Fecha de la resolución', 'fecha_inicio': 'Funciona desde', 'descripcion_corta': 'Descripción corta',
    'area_conocimiento': 'Área de conocimiento', 'modo_operacion': 'Modo de operación', 'publico': 'Visible al público',
    'publicada': 'Publicada', 'activa': 'Activa', 'activo': 'Activo', 'semestre': 'Semestre', 'periodo': 'Período',
    'escena_3d': 'Escena 3D (opcional)', 'lema': 'Frase de portada',
    'CicloProductivo.responsable': 'Responsable del ciclo o del ensayo',
    'CicloProductivo.es_ensayo': 'Es un ensayo experimental (compara tratamientos o evalúa una tecnología)',
    'CicloProductivo.objetivo': 'Objetivo del ensayo', 'CicloProductivo.tratamientos': 'Tratamientos que se comparan',
    'CicloProductivo.repeticiones': 'Repeticiones por tratamiento',
    'CicloProductivo.variables': 'Variables que se miden',
    'ReglamentoUnidad.titulo': 'Título', 'ReglamentoUnidad.subtitulo': 'Subtítulo',
    'ReglamentoUnidad.normas_generales': 'Normas generales (una por línea)',
    'ReglamentoUnidad.reservas_horarios': 'Reservas y horarios (una condición por línea)',
    'ReglamentoUnidad.equipos_materiales': 'Equipos y materiales (una indicación por línea)',
    'ReglamentoUnidad.seguridad': 'Seguridad (una medida por línea)',
    'ReglamentoUnidad.contacto_texto': 'A quién acudir', 'ReglamentoUnidad.contacto_email': 'Correo de contacto',
    'ReglamentoUnidad.activo': 'Publicado: se ve en la ficha y sale en el documento «Reglamento de uso de la unidad»',
}


def _del_modelo(tabla, modelo, nombre):
    """El rótulo o la guía propios de ese campo en ese modelo; si no tiene, el común a todos."""
    return tabla.get(f'{modelo.__name__}.{nombre}') or tabla.get(nombre)


def formulario_de(edicion, unidad, campos, datos=None, archivos=None, instancia=None, request=None):
    if edicion.modelo is Curso and datos is not None:
        datos = datos.copy()
        for nombre in ('origen', 'participacion_unidad'):
            if nombre in campos and 'registro-' + nombre not in datos:
                datos['registro-' + nombre] = getattr(instancia, nombre, '') or Curso._meta.get_field(nombre).default
    referencia = edicion.modelo in (SoftwareDisponible, Consumible)
    clase = modelform_factory(edicion.modelo, fields=campos,
                              form=ReferenciaComercialForm if referencia else forms.ModelForm,
                              formfield_callback=lambda db_field, **kwargs: _campo(db_field, unidad, **kwargs))
    if (edicion.modelo is Curso and datos is not None and 'activo' in campos
            and 'registro-estado_presente' not in datos and 'registro-activo' not in datos):
        # Formularios abiertos antes de una actualización no desactivan la oferta
        # por omitir un campo nuevo. La acción de estado permite desactivar explícitamente.
        datos = datos.copy()
        if instancia is None or instancia.activo:
            datos['registro-activo'] = 'on'
    if edicion.modelo is LeccionCurso and 'nota_minima' in campos:
        from apps.formacion.presentation.notas_cursos import nota_desde_diez, nota_sobre_diez

        class FormularioLeccionSobreDiez(clase):
            nota_minima = forms.DecimalField(
                label='Nota mínima para aprobar /10', min_value=0, max_value=10, decimal_places=1,
                help_text='Por ejemplo: 7 equivale a siete puntos sobre diez.',
                widget=forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '10'}))

            def clean_nota_minima(self):
                return int(nota_desde_diez(self.cleaned_data['nota_minima']))

        clase = FormularioLeccionSobreDiez
    if (edicion.eliminable and instancia is not None and instancia.pk
            and (edicion.modelo is not Curso or 'publicado' in campos)):
        clase = type('FormularioConEliminar', (clase,), {
            'eliminar': forms.BooleanField(label='Eliminar este registro', required=False)})
    contexto = {'referencia_request': request, 'referencia_unidad': unidad} if referencia else {}
    formulario = clase(datos, archivos, instance=instancia, prefix='registro', **contexto)
    if edicion.modelo is LeccionCurso and 'nota_minima' in campos:
        formulario.initial['nota_minima'] = nota_sobre_diez(formulario.instance.nota_minima)
    responsable = formulario.fields.get('responsable')
    if (isinstance(responsable, forms.ModelChoiceField) and responsable.queryset.model is get_user_model()
            and getattr(instancia, 'responsable_id', None)):
        responsable.queryset = personal_de(unidad, conservar=instancia.responsable_id)
    for nombre, campo in formulario.fields.items():
        rotulo = _del_modelo(ROTULOS, edicion.modelo, nombre)
        if rotulo:
            campo.label = rotulo
        guia = _del_modelo(GUIAS, edicion.modelo, nombre)
        if guia and isinstance(campo.widget, (forms.TextInput, forms.Textarea, forms.URLInput)):
            campo.widget.attrs.setdefault('placeholder', guia)
    return formulario


def _valida(edicion, formulario, instancia, unidad):
    if edicion.validar is None:
        return True
    try:
        edicion.validar(formulario, instancia, unidad)
    except ValidationError as error:
        formulario.add_error(None, error)
        return False
    return True


@login_required
def editar_registro_view(request, slug, clave, pk):
    unidad = get_object_or_404(Unidad, slug=slug)
    edicion = REGISTRO.get(clave)
    if edicion is None:
        raise Http404('No se edita eso desde la página.')
    if not _permitido(request.user, unidad, edicion.permiso):
        raise PermissionDenied('No tienes permiso para editar esta parte de la unidad.')
    padre = request.POST.get('padre') or request.GET.get('padre') or ''
    if edicion.unico is not None:
        instancia = edicion.unico(unidad, pk)
    elif pk == 'nuevo':
        if edicion.nuevo is None:
            raise Http404('Esto no se crea desde la página.')
        instancia = edicion.nuevo(unidad, padre)
    else:
        instancia = get_object_or_404(edicion.consulta(unidad), pk=pk)
    grupo = request.POST.get('grupo') or request.GET.get('grupo') or ''
    nuevo = pk == 'nuevo' and edicion.unico is None
    titulo_grupo, campos = edicion.grupos.get(grupo, (edicion.nombre, (nuevo and edicion.campos_nuevo) or edicion.campos))
    datos, archivos = (request.POST, request.FILES) if request.method == 'POST' else (None, None)
    formulario = formulario_de(edicion, unidad, campos, datos, archivos, instancia, request=request)
    volver = request.POST.get('volver') or request.GET.get('volver') or ''
    # Solo se vuelve a una página de este mismo sitio (ni otro dominio ni «javascript:»).
    if not url_has_allowed_host_and_scheme(volver, {request.get_host()}, require_https=request.is_secure()):
        volver = unidad.get_absolute_url()
    if request.method == 'POST' and formulario.is_valid() and _valida(edicion, formulario, instancia, unidad):
        eliminado = bool(formulario.cleaned_data.get('eliminar'))
        identificador = instancia.pk
        try:
            if eliminado:
                instancia.delete()
                if clave == 'curso':
                    volver = reverse('gestion_unidad', args=[unidad.slug]) + '?view=cursos'
            else:
                formulario.save()
        except ValidationError as error:
            # La protección vuelve a comprobarse al escribir, bajo bloqueo.
            # Un participante incorporado desde otra solicitud se informa en
            # el formulario, sin convertir la concurrencia en un error 500.
            formulario.add_error(None, error.messages)
        else:
            # La edición directa deja el mismo rastro que el panel de gestión.
            hecho = 'eliminar' if eliminado else 'actualizar' if identificador else 'crear'
            if eliminado:
                instancia.pk = identificador  # delete() lo vacía; el registro conserva a qué objeto se refiere
            # El formulario de referencia comercial ya anota su propio registro, con el detalle del cambio.
            if not getattr(formulario, '_referencia_auditada', False):
                registrar_auditoria(
                    request, unidad=unidad, accion=hecho, objeto=instancia,
                    descripcion=f'{edicion.nombre}: {hecho} desde la página de la unidad',
                    nuevos={} if eliminado else {'campos': sorted(formulario.changed_data)})
            if request.headers.get('X-Requested-With') == 'fetch':
                # Lo creado desde el menú se abre en el visualizador después de recargar.
                abrir = edicion.pagina(unidad, instancia) if nuevo and edicion.pagina else ''
                return JsonResponse({'ok': True, **({'abrir': abrir} if abrir else {}),
                                     **({'redirigir': volver} if eliminado and clave == 'curso' else {})})
            if clave == 'curso':
                messages.success(request, 'Curso eliminado correctamente.' if eliminado else 'Curso actualizado correctamente.')
            return redirect(volver)
    anchos = ' '.join(nombre for nombre, campo in formulario.fields.items()
                      if isinstance(campo.widget, forms.Textarea) or nombre in ('nombre', 'titulo', 'resumen'))
    nuevo = pk == 'nuevo' and edicion.unico is None
    return render(request, 'portal/pages/unidades/detalle/editor_formulario.html', {
        'antetitulo': f'{"Nuevo registro" if nuevo else "Editar"} · {edicion.nombre}', 'titulo': unidad.nombre,
        'formulario': formulario, 'volver_url': volver,
        'accion_url': reverse('editar_registro', args=[unidad.slug, clave, pk]),
        'ocultos': [(nombre, valor) for nombre, valor in (('grupo', grupo), ('padre', padre), ('volver', volver)) if valor],
        'fragmento': bool(request.GET.get('fragmento') or request.POST.get('fragmento')), 'anchos': anchos,
        'tarjeta_titulo': f'Nuevo: {edicion.nombre.lower()}' if nuevo else titulo_grupo,
        'tarjeta_ayuda': 'Al guardar, la página se actualiza con los cambios.', 'aviso': '',
        'boton': 'Agregar' if nuevo else '',
    })
