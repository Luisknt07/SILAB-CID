"""Secciones nuevas de la ficha, creadas desde una plantilla estándar y editadas en su propia página.

Si a una pestaña le falta una sección, quien coordina la unidad la crea eligiendo una plantilla (tarjetas, tabla,
pasos o texto). Nace con tres elementos de muestra que solo ve quien gestiona; al editarlos pasan a ser contenido
real. La página usa el mismo encabezado, tipografía y tarjetas que las secciones comunes, y en el menú aparece
como una sección más de su pestaña, después de las comunes.
"""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.secciones_propias import ElementoSeccionPropia, SeccionPropia
from apps.recursos.models.recursos import ModuloUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria

from apps.gestion_unidades.presentation.permisos import puede_administrar_personal_unidad, puede_operar_modulo_unidad

MUESTRAS = {
    'tarjetas': [('Tipo (por ejemplo, Servicio)', 'Nombre del primer elemento', 'Explique qué es, para quién sirve y qué obtiene quien lo usa, en dos o tres frases.', 'Un dato clave: cómo se solicita, duración o responsable'),
                 ('Tipo', 'Nombre del segundo elemento', 'Cada tarjeta presenta una sola cosa: un servicio, un producto, un proyecto o un convenio.', 'Un dato clave'),
                 ('Tipo', 'Nombre del tercer elemento', 'Puede agregar una imagen o un enlace, o quitar las tarjetas que no use.', 'Un dato clave')],
    'tabla': [('Categoría', 'Primera fila', 'Para qué sirve o qué contiene.', 'Dato de la última columna'),
              ('Categoría', 'Segunda fila', 'Cada fila es un registro de la tabla.', 'Cantidad, estado o fecha'),
              ('Categoría', 'Tercera fila', 'Edítela o quítela; puede agregar todas las filas que necesite.', 'Dato')],
    'pasos': [('Etapa', 'Primer paso', 'Qué se hace en este paso y con qué.', '30 min'),
              ('Etapa', 'Segundo paso', 'Los pasos se muestran numerados, en el orden de la lista.', '45 min'),
              ('Etapa', 'Tercer paso', 'Agregue los pasos que falten o reordénelos.', '15 min')],
    'texto': [('', 'Primer bloque', 'Un párrafo que explica un tema de la sección. Puede llevar una imagen al lado.', ''),
              ('', 'Segundo bloque', 'Use un bloque por tema: objetivos, alcance, a quién va dirigido…', ''),
              ('', 'Tercer bloque', 'Edite o quite los bloques que no necesite.', '')],
}


def puede_editar_secciones(usuario, unidad):
    """Crear y editar secciones es contenido de la ficha: la coordinación de la unidad o quien tiene configuración."""
    return bool(usuario.is_authenticated and (puede_administrar_personal_unidad(usuario, unidad)
                                              or puede_operar_modulo_unidad(usuario, unidad, 'configuracion')))


def crear_seccion(unidad, modulo, titulo, plantilla):
    """La sección al final de su pestaña, con tres elementos de muestra según la plantilla."""
    orden = (SeccionPropia.objects.filter(modulo=modulo).aggregate(Max('orden'))['orden__max'] or 0) + 1
    seccion = SeccionPropia.objects.create(unidad=unidad, modulo=modulo, titulo=titulo, plantilla=plantilla, orden=orden,
                                           resumen='Escriba aquí, en una frase, qué encuentra el visitante en esta sección.')
    ElementoSeccionPropia.objects.bulk_create([
        ElementoSeccionPropia(seccion=seccion, etiqueta=etiqueta, titulo=nombre, descripcion=texto, detalle=detalle,
                              orden=posicion, es_ejemplo=True)
        for posicion, (etiqueta, nombre, texto, detalle) in enumerate(MUESTRAS[plantilla], start=1)
    ])
    return seccion


def numero_de(seccion, mapa):
    """En una pestaña común sigue la numeración de sus secciones (2.5 después de la 2.4); en una propia, no lleva."""
    if mapa is None or seccion.modulo.clave not in mapa.pestanas:
        return ''
    comunes = mapa.pestanas[seccion.modulo.clave][1]
    if not comunes:
        return ''
    prefijo = comunes[0][0].split('.')[0]
    hermanas = list(SeccionPropia.objects.filter(modulo=seccion.modulo).order_by('orden', 'pk').values_list('pk', flat=True))
    return f'{prefijo}.{len(comunes) + hermanas.index(seccion.pk) + 1}'


def secciones_visibles(unidad, usuario=None):
    """Las secciones que el menú ofrece: las activas con contenido real, y todas para quien las edita."""
    secciones = SeccionPropia.objects.filter(unidad=unidad, modulo__activo=True).select_related('modulo')
    if usuario is not None and puede_editar_secciones(usuario, unidad):
        return list(secciones)
    return [seccion for seccion in secciones.filter(activa=True) if seccion.elementos_publicos().exists()]


def carpetas_de_secciones(unidad, claves, usuario=None):
    """Una carpeta del menú por sección propia, con su botón; después de las comunes de su pestaña."""
    carpetas = []
    for seccion in secciones_visibles(unidad, usuario):
        if seccion.modulo.clave not in claves:
            continue
        total = seccion.elementos_publicos().count()
        carpetas.append({
            'modulo': seccion.modulo.clave, 'id': f'SeccionPropia{seccion.pk}', 'titulo': seccion.titulo,
            'icono': seccion.icono, 'abierta': False, 'numero': '', 'seccion': False, 'propia': True,
            'orden_propio': seccion.orden, 'total': total, 'pendiente': False,
            'grupos': [{'nombre': '', 'botones': [{
                'id': f'seccion-propia-{seccion.pk}', 'nombre': f'{seccion.titulo} ({total})',
                'url': reverse('seccion_propia', args=[unidad.slug, seccion.pk]), 'icono': seccion.icono,
                'titulo': seccion.resumen or seccion.titulo, 'estado': '' if seccion.activa else 'pendiente',
                'subtitulo': '' if seccion.activa else 'Oculta: solo la ve quien gestiona', 'imagen': '',
            }]}],
        })
    return carpetas


def _seccion(slug, pk):
    unidad = get_object_or_404(Unidad, slug=slug)
    seccion = SeccionPropia.objects.filter(unidad=unidad, pk=pk).select_related('modulo').first()
    if seccion is None:
        raise Http404('La sección no es de esta unidad.')
    return unidad, seccion


@xframe_options_sameorigin
def seccion_propia_view(request, slug, pk):
    unidad, seccion = _seccion(slug, pk)
    edita = puede_editar_secciones(request.user, unidad)
    if not edita and (not seccion.activa or not seccion.modulo.activo):
        raise Http404('La sección no está publicada.')
    from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de
    elementos = list(seccion.elementos.all() if edita else seccion.elementos_publicos())
    return render(request, 'portal/pages/unidades/detalle/seccion_propia.html', {
        'unidad': unidad, 'seccion': seccion, 'numero': numero_de(seccion, mapa_de(unidad)), 'elementos': elementos,
        'editar_url': reverse('editar_seccion_propia', args=[unidad.slug, seccion.pk]) if edita else '',
        'hay_muestras': edita and any(elemento.es_ejemplo for elemento in elementos),
    })


# ------------------------------------------------------------------ edición
class DatosDeSeccionForm(forms.ModelForm):
    class Meta:
        model = SeccionPropia
        fields = ['titulo', 'resumen', 'descripcion', 'plantilla', 'icono', 'imagen', 'activa']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class ElementoForm(forms.ModelForm):
    eliminar = forms.BooleanField(label='Eliminar este elemento', required=False)

    class Meta:
        model = ElementoSeccionPropia
        fields = ['etiqueta', 'titulo', 'descripcion', 'detalle', 'imagen', 'enlace', 'orden', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class NuevaSeccionForm(forms.Form):
    titulo = forms.CharField(label='Título de la sección', max_length=120)
    plantilla = forms.ChoiceField(label='Plantilla', choices=SeccionPropia.PLANTILLAS, widget=forms.RadioSelect,
                                  initial='tarjetas')
    modulo = forms.ModelChoiceField(label='Pestaña', queryset=ModuloUnidad.objects.none(), empty_label=None)

    def __init__(self, *args, unidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modulo'].queryset = ModuloUnidad.objects.filter(unidad=unidad).order_by('orden', 'pk')


def _responder(request, destino):
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({'ok': True})
    return redirect(destino)


def _fragmento(request):
    return bool(request.GET.get('fragmento') or request.POST.get('fragmento'))


@login_required
def editar_seccion_view(request, slug, pk):
    """Los datos de la sección o, con `elemento`, uno de sus elementos (o uno nuevo)."""
    unidad, seccion = _seccion(slug, pk)
    if not puede_editar_secciones(request.user, unidad):
        raise PermissionDenied('Solo la coordinación de la unidad edita sus secciones.')
    pagina = reverse('seccion_propia', args=[unidad.slug, seccion.pk])
    clave = (request.POST.get('elemento') or request.GET.get('elemento') or '').strip()
    datos, archivos = (request.POST, request.FILES) if request.method == 'POST' else (None, None)
    if clave:
        elemento = (ElementoSeccionPropia(seccion=seccion, orden=(seccion.elementos.aggregate(Max('orden'))['orden__max'] or 0) + 1)
                    if clave == 'nuevo' else get_object_or_404(ElementoSeccionPropia, seccion=seccion, pk=clave))
        formulario = ElementoForm(datos, archivos, instance=elemento, prefix='elemento')
        if request.method == 'POST' and formulario.is_valid():
            identificador = elemento.pk
            if formulario.cleaned_data.get('eliminar') and identificador:
                elemento.delete()
                elemento.pk = identificador  # delete() lo vacía; el registro conserva a qué objeto se refiere
                hecho = 'eliminar'
            else:
                elemento = formulario.save(commit=False)
                elemento.es_ejemplo = False  # editado, deja de ser muestra
                elemento.save()
                hecho = 'actualizar' if identificador else 'crear'
            registrar_auditoria(request, unidad=unidad, accion=hecho, objeto=elemento,
                                descripcion=f'Elemento de la sección «{seccion.titulo}»: {hecho} desde su página')
            return _responder(request, pagina)
    else:
        elemento = None
        formulario = DatosDeSeccionForm(datos, archivos, instance=seccion, prefix='seccion')
        if request.method == 'POST' and formulario.is_valid():
            formulario.save()
            registrar_auditoria(request, unidad=unidad, accion='actualizar', objeto=seccion,
                                descripcion='Sección propia editada desde su página',
                                nuevos={'campos': sorted(formulario.changed_data)})
            return _responder(request, pagina)
    nuevo = clave == 'nuevo'
    return render(request, 'portal/pages/unidades/detalle/editor_formulario.html', {
        'antetitulo': seccion.titulo, 'titulo': unidad.nombre, 'formulario': formulario, 'volver_url': pagina,
        'accion_url': reverse('editar_seccion_propia', args=[unidad.slug, seccion.pk]),
        'ocultos': [('elemento', clave)] if clave else [], 'fragmento': _fragmento(request),
        'anchos': 'titulo descripcion resumen enlace',
        'tarjeta_titulo': ('Nuevo elemento' if nuevo else 'Elemento') if clave else 'Datos de la sección',
        'tarjeta_ayuda': ('Al guardar, el elemento se muestra en la sección; «Visible» desmarcado lo oculta sin borrarlo.'
                          if clave else 'Título, introducción, plantilla, ícono e imagen de portada.'),
        'aviso': ('Es un elemento de muestra: al guardarlo pasa a ser contenido de la sección.'
                  if elemento is not None and elemento.es_ejemplo else ''),
    })


@login_required
def nueva_seccion_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_editar_secciones(request.user, unidad):
        raise PermissionDenied('Solo la coordinación de la unidad crea secciones.')
    inicial = {'modulo': request.GET.get('modulo')} if request.GET.get('modulo', '').isdigit() else {}
    formulario = NuevaSeccionForm(request.POST or None, unidad=unidad, initial=inicial)
    if request.method == 'POST' and formulario.is_valid():
        with transaction.atomic():
            seccion = crear_seccion(unidad, formulario.cleaned_data['modulo'], formulario.cleaned_data['titulo'],
                                    formulario.cleaned_data['plantilla'])
            registrar_auditoria(request, unidad=unidad, accion='crear', objeto=seccion,
                                descripcion='Sección propia creada desde la página de la unidad')
        return _responder(request, reverse('seccion_propia', args=[unidad.slug, seccion.pk]))
    return render(request, 'portal/pages/unidades/detalle/editor_formulario.html', {
        'antetitulo': 'Nueva sección', 'titulo': unidad.nombre, 'formulario': formulario,
        'volver_url': unidad.get_absolute_url(), 'accion_url': reverse('nueva_seccion_propia', args=[unidad.slug]),
        'ocultos': [], 'fragmento': _fragmento(request), 'anchos': 'titulo modulo',
        'tarjeta_titulo': 'Nueva sección con plantilla', 'boton': 'Crear la sección',
        'tarjeta_ayuda': ('Se agrega al final de la pestaña elegida, con el mismo estilo que las demás secciones y tres '
                          'elementos de muestra para completar.'),
        'aviso': '',
    })
