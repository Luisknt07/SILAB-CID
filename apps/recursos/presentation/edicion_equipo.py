"""Editar la ficha de un equipo desde la propia ficha: la unidad física, el modelo, sus imágenes y sus videos.

Lo edita quien gestiona los recursos de la unidad, sin pasar por el administrador. El modelo (ficha técnica,
componentes, cómo funciona, descripción, imágenes, documentos y videos) es común a todas sus unidades: solo se edita
si quien lo hace gestiona los recursos de todas las unidades que lo tienen. Los contenidos de referencia (los de su
familia) se precargan para revisarlos y, al guardar, quedan como propios del modelo: así se aprueban. Cada sección se
puede abrir y guardar sola (el visualizador abre la que se va a editar) sin tocar las demás.
"""
import re

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.recursos.models.equipos import EquiposServicios, FotoEquipo, VideoEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.models.identificadores import youtube_id
from apps.recursos.presentation.referencia_editor import ReferenciaComercialMixin, firma_video

from apps.gestion_unidades.presentation.edicion_area import sin_barra
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.gestion_unidades.presentation.plantillas_ficha import GENERAL, accesorios_de, ficha_estandar, pares_de, plantilla_de

FILAS_DE_FOTOS_NUEVAS = 4
SECCIONES = {
    'unidad': ('Esta unidad', 'fas fa-id-card'),
    'modelo': ('Modelo', 'fas fa-tag'),
    'especificaciones': ('Especificaciones', 'fas fa-list-ul'),
    'componentes': ('Componentes', 'fas fa-box-open'),
    'funcionamiento': ('Cómo funciona', 'fas fa-cogs'),
    'descripcion': ('Descripción y uso', 'fas fa-align-left'),
    'imagenes': ('Imágenes', 'fas fa-images'),
    'videos': ('Videos', 'fas fa-play-circle'),
    'documentos': ('Documentos', 'fas fa-file-pdf'),
}
CAMPOS_DEL_MODELO = {
    'modelo': ['nombre', 'marca', 'modelo', 'origen_datos_tecnicos', 'fecha_ultima_calibracion', 'proxima_calibracion'],
    'componentes': ['accesorios_incluidos_texto', 'accesorios_opcionales_texto', 'repuestos_texto'],
    'funcionamiento': ['modos_texto'],
    'descripcion': ['descripcion', 'uso_publico', 'instrucciones_publicas'],
    'imagenes': ['imagen'],
    'documentos': ['ficha_tecnica', 'manual_operacion'],
}


def texto_de_accesorios(lista):
    lineas = []
    for item in accesorios_de(lista):
        nombre = f"{item['cantidad']} × {item['nombre']}" if item['cantidad'] > 1 else item['nombre']
        lineas.append(f"{nombre} | {item['uso']}" if item['uso'] else nombre)
    return '\n'.join(lineas)


def accesorios_del_texto(texto):
    return [{'nombre': item['nombre'], 'uso': item['uso'], 'cantidad': item['cantidad']}
            for item in accesorios_de((texto or '').splitlines())]


def texto_de_modos(modos):
    """Los modos de uso como texto editable: «## Nombre | ícono», descripción y las listas «Para qué» y «Necesita»."""
    bloques = []
    for modo in modos or []:
        if not isinstance(modo, dict) or not modo.get('nombre'):
            continue
        lineas = [f"## {modo['nombre']}" + (f" | {modo['icono']}" if modo.get('icono') else ''), modo.get('descripcion', '')]
        if modo.get('aplicaciones'):
            lineas += ['Para qué:'] + [f'- {item}' for item in modo['aplicaciones']]
        if modo.get('requisitos'):
            lineas += ['Necesita:'] + [f'- {item}' for item in modo['requisitos']]
        bloques.append('\n'.join(linea for linea in lineas if linea is not None))
    return '\n\n'.join(bloques)


def modos_del_texto(texto):
    modos, actual, lista = [], None, None
    for linea in (texto or '').splitlines():
        limpia = linea.strip()
        if limpia.startswith('## '):
            nombre, _barra, icono = limpia[3:].partition('|')
            actual = {'nombre': nombre.strip(), 'icono': icono.strip() if re.fullmatch(r'fas fa-[a-z0-9-]+', icono.strip()) else 'fas fa-cogs',
                      'descripcion': '', 'aplicaciones': [], 'requisitos': []}
            modos.append(actual)
            lista = None
        elif actual is None or not limpia:
            continue
        elif limpia.lower().rstrip(':') in ('para qué', 'para que', 'aplicaciones'):
            lista = 'aplicaciones'
        elif limpia.lower().rstrip(':') in ('necesita', 'requisitos', 'lo que necesita'):
            lista = 'requisitos'
        elif lista and limpia.startswith(('-', '•', '*')):
            actual[lista].append(limpia.lstrip('-•* ').strip())
        else:
            actual['descripcion'] = f"{actual['descripcion']} {limpia}".strip()
    return [modo for modo in modos if modo['nombre']]


class EspecificacionesMixin(forms.Form):
    """Las especificaciones de la plantilla del grupo como campos y los accesorios como «Cantidad × Nombre | uso».

    Lo usan el administrador y el editor de la ficha: una sola manera de leer y guardar la ficha técnica.
    """

    accesorios_incluidos_texto = forms.CharField(
        label='Lo que viene con el equipo', required=False, widget=forms.Textarea(attrs={'rows': 6}),
        help_text='Una línea por componente: «Cantidad × Nombre | cómo se usa». Ej.: «2 × Controles táctiles | Se emparejan al encender el visor».')
    accesorios_opcionales_texto = forms.CharField(
        label='Complementos (no obligatorios)', required=False, widget=forms.Textarea(attrs={'rows': 5}),
        help_text='Lo que amplía o mejora su uso (correa con batería, cable de enlace…), con el mismo formato.')
    otras_especificaciones = forms.CharField(
        label='Otras especificaciones', required=False, widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Lo que la plantilla no nombra: una línea «Clave: valor» por especificación.')
    # Un campo por especificación de la plantilla (la más larga tiene 10); el rótulo lo pone __init__.
    espec_0, espec_1, espec_2, espec_3, espec_4, espec_5, espec_6, espec_7, espec_8, espec_9, espec_10, espec_11 = (
        forms.CharField(required=False) for _indice in range(12))

    def iniciar_especificaciones(self, instancia, precargar_familia=False):
        _grupo, self.plantilla = plantilla_de(instancia) if instancia else ('Otros', GENERAL)
        estandar = ficha_estandar(instancia, gestor=True) if instancia else {'especificaciones': []}
        valores = {item['clave']: item['valor'] for item in estandar['especificaciones']}
        claves = [clave for clave, _palabras, _capacidad in self.plantilla]
        for indice, clave in enumerate(claves):
            self.fields[f'espec_{indice}'] = forms.CharField(label=clave, required=False, initial=valores.get(clave, ''))
        for indice in range(len(claves), 12):
            self.fields.pop(f'espec_{indice}', None)
        self.fields['otras_especificaciones'].initial = '\n'.join(
            f'{clave}: {valor}' for clave, valor in valores.items() if clave not in claves)
        self.precargado_de_familia = False
        if not instancia:
            return
        incluidos, opcionales = instancia.get_accesorios_incluidos_crudos(), instancia.get_accesorios_opcionales_crudos()
        if precargar_familia and not incluidos and not opcionales and instancia.familia_id:
            # Lo de la familia se ofrece para revisarlo: al guardar queda aprobado como del modelo.
            referencia = instancia.familia.componentes or []
            incluidos = [item for item in referencia if isinstance(item, dict) and item.get('tipo') == 'incluido']
            opcionales = [item for item in referencia if isinstance(item, dict) and item.get('tipo') == 'complementario']
            self.precargado_de_familia = bool(incluidos or opcionales)
        self.fields['accesorios_incluidos_texto'].initial = texto_de_accesorios(incluidos)
        self.fields['accesorios_opcionales_texto'].initial = texto_de_accesorios(opcionales)

    def aplicar_especificaciones(self, tipo):
        # Solo lo que el formulario trae: guardar una sección no borra las demás.
        if 'otras_especificaciones' in self.fields:
            especificaciones = {}
            for indice, (clave, _palabras, _capacidad) in enumerate(self.plantilla):
                valor = (self.cleaned_data.get(f'espec_{indice}') or '').strip()
                if valor:
                    especificaciones[clave] = valor
            pares, _prosa = pares_de(self.cleaned_data.get('otras_especificaciones') or '')
            especificaciones.update({clave: valor for clave, valor in pares})
            tipo.especificaciones = especificaciones
        if 'accesorios_incluidos_texto' in self.fields:
            tipo.accesorios_incluidos = accesorios_del_texto(self.cleaned_data['accesorios_incluidos_texto'])
            tipo.accesorios_opcionales = accesorios_del_texto(self.cleaned_data['accesorios_opcionales_texto'])


class FichaDelModeloForm(ReferenciaComercialMixin, EspecificacionesMixin, forms.ModelForm):
    repuestos_texto = forms.CharField(
        label='Repuestos y consumibles propios del equipo', required=False, widget=forms.Textarea(attrs={'rows': 4}),
        help_text='Lo que se cambia o se gasta con el uso (almohadillas, boquillas, fresas…), con el mismo formato. '
                  'Los insumos del inventario de la unidad se suman solos.')
    modos_texto = forms.CharField(
        label='Modos de uso', required=False, widget=forms.Textarea(attrs={'rows': 14}),
        help_text='Un bloque por modo: «## Nombre | fas fa-ícono», la descripción, «Para qué:» y «Necesita:» con una línea «- …» por elemento.')

    class Meta:
        model = EquiposServicios
        fields = ['nombre', 'marca', 'modelo', 'descripcion', 'uso_publico', 'instrucciones_publicas', 'origen_datos_tecnicos',
                  'imagen', 'ficha_tecnica', 'manual_operacion', 'fecha_ultima_calibracion', 'proxima_calibracion']
        labels = {'descripcion': 'Descripción', 'uso_publico': 'Para qué se usa',
                  'instrucciones_publicas': 'Cuidados y uso seguro (una regla por línea)',
                  'origen_datos_tecnicos': 'Los datos técnicos son', 'imagen': 'Imagen principal',
                  'ficha_tecnica': 'Ficha técnica del fabricante (PDF)', 'manual_operacion': 'Manual de operación (PDF)',
                  'fecha_ultima_calibracion': 'Última calibración', 'proxima_calibracion': 'Próxima calibración'}
        help_texts = {'proxima_calibracion': 'Con estas dos fechas el equipo sale en «Calibración de equipos» del '
                                             'Centro de reportes. Vacías: el equipo no se calibra.'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4}), 'uso_publico': forms.Textarea(attrs={'rows': 3}),
                   'instrucciones_publicas': forms.Textarea(attrs={'rows': 4}),
                   'fecha_ultima_calibracion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'proxima_calibracion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, campos=None, **kwargs):
        super().__init__(*args, habilitar_referencia=(campos is None or any(
            campo in campos for campo in ('marca', 'modelo'))), **kwargs)
        instancia = self.instance if self.instance.pk else None
        self.iniciar_especificaciones(instancia, precargar_familia=True)
        self.fields['imagen'].required = False
        self.fields['imagen'].widget = forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'})
        for campo in ('ficha_tecnica', 'manual_operacion'):
            self.fields[campo].required = False
            self.fields[campo].widget = forms.ClearableFileInput(attrs={'accept': 'application/pdf'})
        if instancia:
            repuestos = instancia.repuestos or []
            modos = instancia.modos_uso or []
            self.modos_de_familia = not modos and bool(instancia.familia_id and instancia.familia.modos_uso)
            if not repuestos and instancia.familia_id:
                repuestos = [item for item in (instancia.familia.componentes or []) if isinstance(item, dict) and item.get('tipo') == 'repuesto']
            self.fields['repuestos_texto'].initial = texto_de_accesorios(repuestos)
            self.fields['modos_texto'].initial = texto_de_modos(modos or (instancia.familia.modos_uso if instancia.familia_id else []))
        if campos is not None:
            for campo in list(self.fields):
                if campo not in campos and campo not in self.referencia_nombres:
                    del self.fields[campo]

    def save(self, commit=True):
        tipo = super().save(commit=False)
        self.aplicar_especificaciones(tipo)
        self.aplicar_referencia(tipo)
        if 'repuestos_texto' in self.fields:
            tipo.repuestos = accesorios_del_texto(self.cleaned_data['repuestos_texto'])
        if 'modos_texto' in self.fields:
            tipo.modos_uso = modos_del_texto(self.cleaned_data['modos_texto'])
        if self.cleaned_data.get('imagen'):
            # La foto propia reemplaza a la de referencia: deja de mostrarse el crédito ajeno.
            tipo.credito_imagen, tipo.fuente_imagen = '', ''
        if commit:
            with transaction.atomic():
                tipo.save()
                self._save_m2m()
                self.auditar_referencia(tipo)
        return tipo


class UnidadFisicaForm(forms.ModelForm):
    espacios_asociados = forms.ModelMultipleChoiceField(
        label='Áreas donde está', queryset=EspacioReservable.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = UnidadEquipo
        fields = ['codigo_bien', 'tipo_bien', 'numero_serie', 'estado_unidad', 'criticidad', 'ubicacion_especifica',
                  'version_sistema', 'sistema_actualizado', 'fecha_ultimo_mantenimiento', 'proximo_mantenimiento',
                  'garantia_hasta', 'espacios_asociados']
        labels = {'codigo_bien': 'Código del bien (bodega)', 'numero_serie': 'Número de serie', 'estado_unidad': 'Estado',
                  'ubicacion_especifica': 'Lugar dentro del área', 'fecha_ultimo_mantenimiento': 'Último mantenimiento',
                  'proximo_mantenimiento': 'Próximo mantenimiento', 'garantia_hasta': 'Garantía hasta'}
        widgets = {campo: forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
                   for campo in ('sistema_actualizado', 'fecha_ultimo_mantenimiento', 'proximo_mantenimiento',
                                 'garantia_hasta')}

    def __init__(self, *args, unidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['espacios_asociados'].queryset = EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')
        self.fields['espacios_asociados'].initial = list(self.instance.espacios_asociados.filter(unidad=unidad)) if self.instance.pk else []

    def save_espacios(self, unidad):
        ajenos = list(self.instance.espacios_asociados.exclude(unidad=unidad))
        self.instance.espacios_asociados.set(ajenos + list(self.cleaned_data['espacios_asociados']))


class FotoNuevaForm(forms.Form):
    imagen = forms.ImageField(label='Foto', required=False, widget=forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}))
    titulo = forms.CharField(label='Qué muestra', max_length=160, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'Qué muestra (p. ej., Controles táctiles)'}),
                             help_text='Para un componente, su nombre: la ficha la pone junto a él.')
    tipo = forms.ChoiceField(label='Tipo', choices=FotoEquipo.TIPOS, initial='accesorio')


def puede_editar_modelo(usuario, tipo):
    """El modelo es común a sus unidades: lo edita quien gestiona los recursos de todas las que lo tienen."""
    activos = UnidadEquipo.objects.filter(equipo=tipo, activa=True)
    unidades = Unidad.objects.filter(Q(pk__in=activos.values('laboratorio')) |
                                     Q(pk__in=activos.values('laboratorios')))
    return all(puede_operar_modulo_unidad(usuario, unidad, 'recursos') for unidad in unidades)


def _videos_del_texto(texto):
    videos, errores = [], []
    for numero, linea in enumerate((texto or '').splitlines(), start=1):
        partes = [parte.strip() for parte in linea.split('|')]
        if not partes[0]:
            continue
        if not youtube_id(partes[0]):
            errores.append(f'Línea {numero}: «{partes[0]}» no es un enlace de YouTube.')
            continue
        videos.append({'url': partes[0], 'titulo': (partes[1] if len(partes) > 1 else '') or 'Video de manejo',
                       'canal': partes[2] if len(partes) > 2 else ''})
    return videos, errores


def _texto_de_videos(tipo):
    """Los videos del modelo o, si no tiene, los de su tipo de equipo, para aprobarlos o cambiarlos."""
    videos = list(tipo.videos.all()) or (list(tipo.familia.videos.all()) if tipo.familia_id else [])
    return '\n'.join(' | '.join(filter(None, (video.url, sin_barra(video.titulo), sin_barra(video.canal)))) for video in videos)


def _unidad_equipo(slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug)
    equipo = (UnidadEquipo.objects.filter(laboratorio=unidad, codigo_unidad=codigo).select_related('equipo__familia').first())
    if equipo is None:
        raise Http404('El equipo no es de esta unidad.')
    return unidad, equipo


def _guardar_fotos(request, tipo, fotos, fotos_nuevas):
    for foto in fotos:
        if request.POST.get(f'borrar_foto_{foto.pk}'):
            foto.delete()
            continue
        foto.titulo = (request.POST.get(f'titulo_foto_{foto.pk}') or '').strip()[:160]
        if request.POST.get(f'tipo_foto_{foto.pk}') in dict(FotoEquipo.TIPOS):
            foto.tipo = request.POST[f'tipo_foto_{foto.pk}']
        foto.save(update_fields=['titulo', 'tipo'])
    orden = max((foto.orden for foto in fotos), default=0)
    for nueva in fotos_nuevas:
        if nueva.cleaned_data.get('imagen'):
            orden += 1
            FotoEquipo.objects.create(equipo=tipo, imagen=nueva.cleaned_data['imagen'], orden=orden,
                                      titulo=nueva.cleaned_data['titulo'], tipo=nueva.cleaned_data['tipo'])


def _guardar_videos(tipo, videos, *, confirmar_referencia=True, request=None, unidad=None):
    vigentes = {video['url'] for video in videos}
    tipo.videos.exclude(url__in=vigentes).delete()
    existentes = {video.url: video for video in tipo.videos.all()}
    for posicion, video in enumerate(videos):
        registro = existentes.get(video['url']) or VideoEquipo(equipo=tipo, url=video['url'])
        registro.titulo, registro.canal, registro.orden = video['titulo'], video['canal'], posicion
        registro.full_clean()
        registro.save()
    pendientes = (tipo.medios_referencia or {}).get('videos_por_revisar')
    if not confirmar_referencia:
        # Un guardado completo puede cambiar también título/canal o añadir un
        # video. Sus nuevas firmas siguen pendientes hasta revisar Videos aparte.
        actualizados = list(pendientes) if isinstance(pendientes, list) else []
        for registro in tipo.videos.all():
            firma = firma_video(registro)
            if firma not in actualizados:
                actualizados.append(firma)
        if actualizados != pendientes:
            tipo.medios_referencia = {**tipo.medios_referencia, 'videos_por_revisar': actualizados}
            tipo.save(update_fields=['medios_referencia'])
        return
    if pendientes and confirmar_referencia:
        # Guardar esta sección es una revisión explícita del conjunto de videos.
        # No se eliminan por el solo hecho de cambiar una propuesta comercial.
        tipo.medios_referencia = {**tipo.medios_referencia, 'videos_por_revisar': []}
        tipo.save(update_fields=['medios_referencia'])
        if unidad is not None:
            from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
            registrar_auditoria(request, unidad=unidad, accion='actualizar', objeto=tipo,
                descripcion='Videos del equipo revisados después de cambiar la referencia comercial',
                anteriores={'videos_por_revisar': pendientes}, nuevos={'videos_por_revisar': []})


@login_required
def editar_equipo_view(request, slug, codigo):
    unidad, equipo = _unidad_equipo(slug, codigo)
    if not puede_operar_modulo_unidad(request.user, unidad, 'recursos'):
        raise PermissionDenied('Solo quien gestiona los recursos de la unidad edita la ficha de sus equipos.')
    tipo = equipo.equipo
    edita_modelo = puede_editar_modelo(request.user, tipo)
    seccion = (request.POST.get('seccion') or request.GET.get('seccion') or '').strip()
    solo = seccion if seccion in SECCIONES else ''
    if solo and solo != 'unidad' and not edita_modelo:
        solo = 'unidad'

    def incluye(nombre):
        return not solo or solo == nombre

    datos, archivos = (request.POST, request.FILES) if request.method == 'POST' else (None, None)
    form_unidad = UnidadFisicaForm(datos, instance=equipo, unidad=unidad, prefix='unidad') if incluye('unidad') else None
    form_modelo = None
    if edita_modelo:
        campos = [campo for nombre, lista in CAMPOS_DEL_MODELO.items() if incluye(nombre) for campo in lista]
        if incluye('especificaciones'):
            campos += [f'espec_{indice}' for indice in range(12)] + ['otras_especificaciones']
        if campos:
            form_modelo = FichaDelModeloForm(datos, archivos, instance=tipo, prefix='modelo', campos=campos,
                referencia_request=request, referencia_unidad=unidad)
    fotos = list(tipo.fotos.all()) if edita_modelo and incluye('imagenes') else []
    fotos_nuevas = ([FotoNuevaForm(datos, archivos, prefix=f'foto{indice}') for indice in range(FILAS_DE_FOTOS_NUEVAS)]
                    if edita_modelo and incluye('imagenes') else [])
    edita_videos = edita_modelo and incluye('videos')
    texto_videos = (request.POST.get('videos', '') if datos is not None else _texto_de_videos(tipo)) if edita_videos else ''
    videos, errores_videos = _videos_del_texto(texto_videos) if edita_videos else ([], [])
    if request.method == 'POST':
        formularios = [form for form in (form_unidad, form_modelo, *fotos_nuevas) if form is not None]
        if all(formulario.is_valid() for formulario in formularios) and not errores_videos:
            with transaction.atomic():
                if form_unidad:
                    form_unidad.save()
                    form_unidad.save_espacios(unidad)
                if form_modelo:
                    form_modelo.save()
                if fotos or fotos_nuevas:
                    _guardar_fotos(request, tipo, fotos, fotos_nuevas)
                if edita_videos:
                    _guardar_videos(tipo, videos, confirmar_referencia=not (
                        form_modelo and form_modelo.referencia_identidad_cambiada), request=request, unidad=unidad)
            if request.headers.get('X-Requested-With') == 'fetch':
                return JsonResponse({'ok': True})
            destino = reverse('ficha_equipo_publica', args=[unidad.slug, equipo.codigo_unidad])
            return redirect(f"{destino}#{request.POST.get('volver_a') or 'identidad'}")
    return render(request, 'portal/pages/unidades/aula/equipo_editar.html', {
        'unidad': unidad, 'unidad_equipo': equipo, 'tipo': tipo, 'edita_modelo': edita_modelo, 'secciones': SECCIONES,
        'solo': solo, 'form_unidad': form_unidad, 'form_modelo': form_modelo, 'fotos': fotos, 'fotos_nuevas': fotos_nuevas,
        'edita_videos': edita_videos, 'texto_videos': texto_videos,
        'videos_de_referencia': edita_videos and datos is None and bool(texto_videos) and not tipo.videos.exists(),
        'errores_videos': errores_videos if request.method == 'POST' else [],
        'ficha_url': reverse('ficha_equipo_publica', args=[unidad.slug, equipo.codigo_unidad]),
        'fragmento': bool(request.GET.get('fragmento') or request.POST.get('fragmento')),
        'unidades_del_modelo': UnidadEquipo.objects.filter(equipo=tipo, activa=True).values('laboratorio').distinct().count(),
    })
