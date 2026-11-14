"""Agregar desde el visualizador un elemento nuevo a una sección estándar, con la plantilla que esa sección ya usa.

Cada sección del menú ofrece su «Agregar» a quien puede editarla: una nueva área nace con la página de las demás
áreas, un equipo con la ficha técnica de los demás equipos, un programa, un insumo, un proceso o un producto con su
propio editor. Lo nuevo trae texto guía que explica qué escribir en cada parte, y no se publica hasta que la unidad
lo completa: el área queda en borrador y el equipo como no disponible.
"""
import re

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.core.presentation.codigos_sistema import sigla_de_unidad, siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

GUIA_DE_AREA = {
    'que_es': 'Explique en dos o tres frases qué es esta área y qué se hace en ella. Por ejemplo: «Espacio donde se '
              'diseñan y prueban…».',
    'como_funciona': 'Cuente cómo se trabaja aquí: qué equipos se usan, en qué orden y qué debe saber quien llega por '
                     'primera vez.',
    'principio': 'Preparar | Qué se alista antes de empezar.\nRealizar | Qué se hace con los equipos del área.\n'
                 'Revisar | Cómo se comprueba el resultado.\nCerrar | Cómo se deja el área al terminar.',
    'distribucion': 'Zona de trabajo | Qué se hace en esta zona y con qué equipos. | ',
    'aplicaciones': 'Una práctica o proyecto que se hace aquí, con la carrera que lo usa.\nOtra aplicación, una por línea.',
    'conexiones': 'Tomas eléctricas, red, agua, aire o ventilación que necesita el área, una por línea.',
    'seguridad': 'Una norma de seguridad por línea: equipo de protección, aforo, qué hacer ante un incidente.',
}
GUIA_DE_EQUIPO = {
    'descripcion': 'Describa en dos o tres frases para qué sirve este equipo y qué se puede hacer con él.',
    'uso_publico': 'Para qué lo usan estudiantes y docentes: prácticas, proyectos o servicios.',
    'instrucciones_publicas': 'Pasos básicos para usarlo de forma segura, uno por línea.',
}


class NuevaAreaForm(forms.Form):
    nombre = forms.CharField(label='Nombre del área', max_length=160,
                             widget=forms.TextInput(attrs={'placeholder': 'Por ejemplo: Metaverso y mundos virtuales'}))
    tipo = forms.ChoiceField(label='Tipo de espacio', choices=EspacioReservable.TIPO_CHOICES, initial='area')
    capacidad = forms.IntegerField(label='Personas a la vez', min_value=1, max_value=500, initial=6)


class NuevoEquipoForm(forms.Form):
    nombre = forms.CharField(label='Nombre del equipo', max_length=100,
                             widget=forms.TextInput(attrs={'placeholder': 'Por ejemplo: Visor autónomo de realidad virtual'}))
    area = forms.ModelChoiceField(label='Área donde está', queryset=EspacioReservable.objects.none(), empty_label=None)
    marca = forms.CharField(label='Marca', max_length=100, required=False)
    modelo = forms.CharField(label='Modelo', max_length=100, required=False)
    cantidad = forms.IntegerField(label='Unidades físicas', min_value=1, max_value=20, initial=1,
                                  help_text='Cada una recibe su código; el número de serie y la etiqueta de bodega se '
                                            'completan después en su ficha.')

    def __init__(self, *args, unidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area'].queryset = EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')


def codigo_de_area_nueva(unidad, nombre):
    """SIGLA-AREA-NOMBRE, sin repetir uno existente."""
    base = f"{sigla_de_unidad(unidad)}-AREA-{re.sub(r'[^A-Z0-9]', '', slugify(nombre).upper())[:10] or 'NUEVA'}"
    codigo, numero = base, 2
    while EspacioReservable.objects.filter(codigo=codigo).exists():
        codigo, numero = f'{base}{numero}', numero + 1
    return codigo


def crear_area(unidad, nombre, tipo, capacidad):
    orden = (EspacioReservable.objects.filter(unidad=unidad).order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
    espacio = EspacioReservable.objects.create(
        unidad=unidad, codigo=codigo_de_area_nueva(unidad, nombre), nombre=nombre, tipo=tipo, capacidad=capacidad,
        orden=orden, descripcion_publica='Una frase que presente el área en su portada.')
    FichaArea.objects.create(espacio=espacio, publicada=False, fuente='Plantilla para completar por la unidad',
                             **GUIA_DE_AREA)
    return espacio


def crear_equipo(unidad, espacio, nombre, marca, modelo, cantidad):
    tipo = EquiposServicios.objects.create(codigo=siguiente_codigo_modelo(unidad, espacio), nombre=nombre, marca=marca,
                                           modelo=modelo, estado='disponible', rol='principal', **GUIA_DE_EQUIPO)
    unidades = []
    for _ in range(cantidad):
        fisica = UnidadEquipo.objects.create(
            codigo_unidad=siguiente_codigo_unidad(unidad, espacio, tipo), equipo=tipo, laboratorio=unidad,
            estado_unidad='no_disponible', ubicacion_especifica=espacio.nombre[:200],
            observaciones='Registrado desde el visualizador: complete su ficha y márquelo disponible para publicarlo.')
        fisica.laboratorios.add(unidad)
        espacio.equipos_asociados.add(fisica)
        unidades.append(fisica)
    return unidades


def _responder(request, destino):
    """En el cuadro de edición, la página se recarga y abre lo creado; sin él, se va directo."""
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({'ok': True, 'abrir': destino})
    return redirect(destino)


def _pantalla(request, unidad, formulario, titulo, ayuda, accion, boton):
    return render(request, 'portal/pages/unidades/detalle/editor_formulario.html', {
        'antetitulo': titulo, 'titulo': unidad.nombre, 'formulario': formulario, 'volver_url': unidad.get_absolute_url(),
        'accion_url': accion, 'ocultos': [], 'anchos': 'nombre', 'tarjeta_titulo': titulo, 'tarjeta_ayuda': ayuda,
        'aviso': '', 'boton': boton, 'fragmento': bool(request.GET.get('fragmento') or request.POST.get('fragmento')),
    })


def _unidad_con_recursos(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, 'recursos'):
        raise PermissionDenied('Solo quien gestiona los recursos de la unidad agrega áreas y equipos.')
    return unidad


@login_required
def nueva_area_view(request, slug):
    unidad = _unidad_con_recursos(request, slug)
    formulario = NuevaAreaForm(request.POST or None)
    if request.method == 'POST' and formulario.is_valid():
        with transaction.atomic():
            espacio = crear_area(unidad, **formulario.cleaned_data)
        return _responder(request, reverse('area_unidad', args=[unidad.slug, espacio.codigo]))
    return _pantalla(request, unidad, formulario, 'Nueva área',
                     'Nace con la misma página que las demás áreas y con texto guía en cada parte; queda en borrador '
                     'hasta que la complete y la publique.', reverse('nueva_area', args=[unidad.slug]), 'Crear el área')


@login_required
def nuevo_equipo_view(request, slug):
    unidad = _unidad_con_recursos(request, slug)
    formulario = NuevoEquipoForm(request.POST or None, unidad=unidad)
    if request.method == 'POST' and formulario.is_valid():
        datos = formulario.cleaned_data
        with transaction.atomic():
            unidades = crear_equipo(unidad, datos['area'], datos['nombre'], datos['marca'], datos['modelo'],
                                    datos['cantidad'])
        return _responder(request, reverse('ficha_equipo_publica', args=[unidad.slug, unidades[0].codigo_unidad]))
    return _pantalla(request, unidad, formulario, 'Nuevo equipo',
                     'Nace con la misma ficha técnica que los demás equipos y con texto guía; queda como no disponible '
                     'hasta que complete su ficha.', reverse('nuevo_equipo', args=[unidad.slug]), 'Crear el equipo')


# Lo que cada sección estándar del menú permite agregar: rótulo, cómo llegar al formulario y quién puede.
AGREGAR_POR_SECCION = {
    'areas_equipos': ('Nueva área', 'nueva_area', 'recursos'),
    'fichas_equipo': ('Nuevo equipo', 'nuevo_equipo', 'recursos'),
    'software': ('Nuevo programa', 'software', None),
    'materiales': ('Nuevo insumo o material', 'insumo', None),
    'procesos': ('Nuevo proceso', 'proceso', None),
    'productos': ('Nuevo producto o servicio', 'producto', None),
    'asignaturas': ('Nueva asignatura', 'asignatura', None),
    'cursos': ('Nuevo curso', 'nuevo_curso', 'practicas'),
    'novedades': ('Nueva novedad', 'novedad', None),
}


def acciones_de_seccion(unidad, clave, numero, ediciones, usuario):
    """Los «Agregar» de una sección del menú: su elemento propio y, en todas, una carpeta propia."""
    acciones = []
    rotulo, destino, permiso = AGREGAR_POR_SECCION.get(clave, (None, None, None))
    if rotulo and permiso and puede_operar_modulo_unidad(usuario, unidad, permiso):
        acciones.append({'rotulo': rotulo, 'url': reverse(destino, args=[unidad.slug]), 'icono': 'fas fa-plus'})
    elif rotulo and permiso is None and destino in ediciones:
        acciones.append({'rotulo': rotulo, 'url': reverse('editar_registro', args=[unidad.slug, destino, 'nuevo']),
                         'icono': 'fas fa-plus'})
    if numero and 'carpeta' in ediciones:
        acciones.append({'rotulo': 'Nueva carpeta', 'icono': 'fas fa-folder-plus',
                         'url': reverse('editar_registro', args=[unidad.slug, 'carpeta', 'nuevo']) + f'?padre=s:{numero}'})
    return acciones
