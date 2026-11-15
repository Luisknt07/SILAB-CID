"""Editar la página de un área desde la propia página: sus datos, los textos de su ficha, sus fotos y sus videos.

Lo edita quien gestiona los recursos de la unidad. Cada bloque se puede guardar por separado (el visualizador abre
solo el que se va a editar), sin tocar los demás. La ficha queda publicada cuando la unidad lo marca.
"""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.identificadores import youtube_id

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

FILAS_DE_FOTOS_NUEVAS = 4
SECCIONES = {
    'datos': ('Datos del área', 'fas fa-vector-square'),
    'contenido': ('Qué es y cómo funciona', 'fas fa-align-left'),
    'proceso': ('Proceso y distribución', 'fas fa-project-diagram'),
    'aplicaciones': ('Aplicaciones, conexiones y seguridad', 'fas fa-list-ul'),
    'fotos': ('Fotos', 'fas fa-images'),
    'videos': ('Videos', 'fas fa-play-circle'),
}
CAMPOS_DE_FICHA = {
    'contenido': ['que_es', 'como_funciona', 'publicada'],
    'proceso': ['principio', 'distribucion'],
    'aplicaciones': ['aplicaciones', 'conexiones', 'seguridad'],
}


class DatosDelAreaForm(forms.ModelForm):
    class Meta:
        model = EspacioReservable
        fields = ['nombre', 'descripcion_publica', 'capacidad', 'ubicacion', 'caracteristicas', 'mobiliario_incluido', 'imagen']
        labels = {'descripcion_publica': 'Descripción', 'ubicacion': 'Ubicación', 'caracteristicas': 'Características', 'mobiliario_incluido': 'Mobiliario',
                  'imagen': 'Foto de portada'}
        widgets = {campo: forms.Textarea(attrs={'rows': 3}) for campo in ('descripcion_publica', 'caracteristicas', 'mobiliario_incluido')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imagen'].required = False
        self.fields['imagen'].widget = forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'})


class FichaDelAreaForm(forms.ModelForm):
    class Meta:
        model = FichaArea
        fields = ['que_es', 'como_funciona', 'publicada', 'principio', 'distribucion', 'aplicaciones', 'conexiones', 'seguridad']
        labels = {'que_es': 'Qué es', 'como_funciona': 'Cómo funciona', 'publicada': 'Publicar la ficha del área',
                  'principio': 'Pasos del proceso (uno por línea: «Paso | explicación»)',
                  'distribucion': 'Zonas (una por línea: «Zona | para qué | equipo; equipo»)',
                  'aplicaciones': 'Qué se puede hacer (una por línea)', 'conexiones': 'Conexiones e infraestructura (una por línea)',
                  'seguridad': 'Reglas de seguridad (una por línea)'}
        widgets = {campo: forms.Textarea(attrs={'rows': 5}) for campo in
                   ('que_es', 'como_funciona', 'principio', 'distribucion', 'aplicaciones', 'conexiones', 'seguridad')}

    def __init__(self, *args, campos=None, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in list(self.fields):
            if campos is not None and campo not in campos:
                del self.fields[campo]


class FotoDelAreaForm(forms.Form):
    imagen = forms.ImageField(label='Foto', required=False, widget=forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}))
    titulo = forms.CharField(label='Qué muestra', max_length=160, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'Qué muestra la foto'}))


def sin_barra(texto):
    """La barra separa los campos de cada línea de videos: dentro de un título se cambia por un punto medio."""
    return ' '.join((texto or '').replace('|', '·').split())


def videos_del_texto(texto):
    videos, errores = [], []
    for numero, linea in enumerate((texto or '').splitlines(), start=1):
        partes = [parte.strip() for parte in linea.split('|')]
        if not partes[0]:
            continue
        if not youtube_id(partes[0]):
            errores.append(f'Línea {numero}: «{partes[0]}» no es un enlace de YouTube.')
            continue
        videos.append({'url': partes[0], 'titulo': (partes[1] if len(partes) > 1 else '') or 'Video del área',
                       'descripcion': partes[2] if len(partes) > 2 else ''})
    return videos, errores


def _area(slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug)
    espacio = EspacioReservable.objects.filter(unidad=unidad, codigo=codigo).first()
    if espacio is None:
        raise Http404('El área no es de esta unidad.')
    return unidad, espacio


def puede_editar_area(usuario, unidad):
    return puede_operar_modulo_unidad(usuario, unidad, 'recursos')


@login_required
def editar_area_view(request, slug, codigo):
    unidad, espacio = _area(slug, codigo)
    if not puede_editar_area(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona los recursos de la unidad edita sus áreas.')
    ficha = FichaArea.objects.filter(espacio=espacio).first() or FichaArea(espacio=espacio, fuente='Unidad')
    # Una sección sola (el visualizador abre solo la que se edita) o todas.
    seccion = (request.POST.get('seccion') or request.GET.get('seccion') or '').strip()
    solo = seccion if seccion in SECCIONES else ''
    def incluye(nombre):
        return not solo or solo == nombre

    datos, archivos = (request.POST, request.FILES) if request.method == 'POST' else (None, None)
    form_datos = DatosDelAreaForm(datos, archivos, instance=espacio, prefix='area') if incluye('datos') else None
    campos_ficha = [campo for nombre, campos in CAMPOS_DE_FICHA.items() if incluye(nombre) for campo in campos]
    form_ficha = FichaDelAreaForm(datos, instance=ficha, prefix='ficha', campos=campos_ficha) if campos_ficha else None
    fotos = list(MedioInterior.objects.filter(espacio=espacio, tipo='foto').order_by('orden', 'pk')) if incluye('fotos') else []
    fotos_nuevas = [FotoDelAreaForm(datos, archivos, prefix=f'foto{indice}') for indice in range(FILAS_DE_FOTOS_NUEVAS)] if incluye('fotos') else []
    videos_actuales = MedioInterior.objects.filter(espacio=espacio, tipo='video').order_by('orden', 'pk')
    # Sin videos propios se precargan los de referencia de su ficha, para aprobarlos o cambiarlos.
    referencia = [] if videos_actuales.exists() or not ficha.pk else [
        (elemento.url, elemento.nombre, elemento.para_que)
        for elemento in ficha.elementos.filter(tipo='video').order_by('orden', 'pk')]
    texto_videos = (request.POST.get('videos', '') if datos is not None else '\n'.join(
        ' | '.join(filter(None, (url, sin_barra(titulo), sin_barra(descripcion))))
        for url, titulo, descripcion in ([(v.youtube_url, v.titulo, v.descripcion) for v in videos_actuales] or referencia)))
    videos, errores_videos = videos_del_texto(texto_videos) if incluye('videos') else ([], [])
    if request.method == 'POST':
        formularios = [form for form in (form_datos, form_ficha, *fotos_nuevas) if form is not None]
        if all(form.is_valid() for form in formularios) and not errores_videos:
            with transaction.atomic():
                if form_datos:
                    form_datos.save()
                if form_ficha:
                    form_ficha.save()
                if incluye('fotos'):
                    for foto in fotos:
                        if request.POST.get(f'borrar_foto_{foto.pk}'):
                            foto.delete()
                            continue
                        foto.titulo = (request.POST.get(f'titulo_foto_{foto.pk}') or foto.titulo).strip()[:160]
                        foto.publicado = bool(request.POST.get(f'publicada_foto_{foto.pk}'))
                        foto.save(update_fields=['titulo', 'publicado'])
                    orden = max((foto.orden for foto in fotos), default=0)
                    for nueva in fotos_nuevas:
                        if nueva.cleaned_data.get('imagen'):
                            orden += 1
                            MedioInterior.objects.create(unidad=unidad, espacio=espacio, tipo='foto', orden=orden,
                                                         imagen=nueva.cleaned_data['imagen'],
                                                         titulo=nueva.cleaned_data['titulo'] or espacio.nombre)
                if incluye('videos'):
                    vigentes = {video['url'] for video in videos}
                    videos_actuales.exclude(youtube_url__in=vigentes).delete()
                    existentes = {video.youtube_url: video for video in videos_actuales}
                    for posicion, video in enumerate(videos):
                        registro = existentes.get(video['url']) or MedioInterior(unidad=unidad, espacio=espacio, tipo='video',
                                                                                youtube_url=video['url'])
                        registro.titulo, registro.descripcion, registro.orden = video['titulo'][:160], video['descripcion'][:255], posicion
                        registro.full_clean()
                        registro.save()
                registrar_auditoria(request, unidad=unidad, accion='actualizar', objeto=espacio,
                                    descripcion=f'Área editada desde su página: {solo or "todas las secciones"}')
            if request.headers.get('X-Requested-With') == 'fetch':
                return JsonResponse({'ok': True})
            destino = reverse('area_unidad', args=[unidad.slug, espacio.codigo])
            return redirect(f"{destino}#{request.POST.get('volver_a') or 'que-es'}")
    return render(request, 'portal/pages/unidades/detalle/area_editar.html', {
        'unidad': unidad, 'espacio': espacio, 'secciones': SECCIONES, 'solo': solo,
        'form_datos': form_datos, 'form_ficha': form_ficha, 'fotos': fotos, 'fotos_nuevas': fotos_nuevas,
        'texto_videos': texto_videos, 'errores_videos': errores_videos if request.method == 'POST' else [],
        'videos_de_referencia': datos is None and bool(referencia),
        'area_url': reverse('area_unidad', args=[unidad.slug, espacio.codigo]),
        'fragmento': bool(request.GET.get('fragmento') or request.POST.get('fragmento')),
    })
