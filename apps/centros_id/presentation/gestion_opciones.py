"""Opciones por demanda del editor: misma autorización y validación completa."""
from django import forms
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.centros_id.gestion_catalogo import REGISTROS


def acotar_relacion(campo, centro):
    """Comparte exactamente el alcance del formulario y de su búsqueda."""
    from .gestion import _consulta

    if campo.queryset.model._meta.app_label == 'centros_id':
        campo.queryset = _consulta(campo.queryset.model, centro)
    else:
        campo.queryset = campo.queryset.filter(is_active=True)


def _id(valor):
    valor = str(valor).strip()
    if not valor.isascii() or not valor.isdigit() or len(valor) > 19:
        raise ValueError('Identificador no válido.')
    numero = int(valor)
    if not 1 <= numero <= 9223372036854775807:
        raise ValueError('Identificador no válido.')
    return numero


def preparar_opciones(formulario, modelo, centro):
    """Limita sólo el widget; ``campo.queryset`` sigue íntegro para ``clean``."""
    tipo = next((clave for clave, spec in REGISTROS.items() if spec[1] == modelo.__name__), '')
    for nombre, campo in formulario.fields.items():
        if not isinstance(campo, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
            continue
        valores = formulario[nombre].value()
        valores = valores if isinstance(valores, (list, tuple)) else [valores]
        ids = set()
        for valor in valores:
            try:
                ids.add(_id(valor))
            except ValueError:
                pass  # La validación del campo conserva el error; nunca se amplía su queryset.
        actuales = campo.queryset.filter(pk__in=ids).select_related() if ids else campo.queryset.none()
        opciones = [(objeto.pk, campo.label_from_instance(objeto)) for objeto in actuales]
        if not isinstance(campo, forms.ModelMultipleChoiceField) and campo.empty_label is not None:
            opciones.insert(0, ('', campo.empty_label))
        campo.widget.choices = opciones
        if tipo and not campo.disabled:
            campo.widget.attrs.update({
                'data-resource-select': f'{tipo}.{nombre}',
                'data-resource-search-url': reverse('opciones_gestion_centro_id', args=[centro.slug]),
            })


def _respuesta(items=(), *, pagina=1, paginas=1, total=0, error='', estado=200):
    contenido = {'items': list(items), 'pagina': pagina, 'paginas': paginas, 'total': total}
    if error:
        contenido['error'] = error
    respuesta = JsonResponse(contenido, status=estado)
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


@never_cache
@login_required
@require_GET
def opciones_view(request, slug):
    from .gestion import FormularioGestion, _modelo
    from .views import _centro

    centro = _centro(slug)
    if not centro.puede_gestionar(request.user):
        raise PermissionDenied
    tipo, separador, nombre = request.GET.get('tipo', '').partition('.')
    spec = REGISTROS.get(tipo)
    if not separador or spec is None or nombre not in spec[4].split():
        return _respuesta(error='Catálogo no disponible.', estado=400)
    clase = forms.modelform_factory(_modelo(spec[1]), form=FormularioGestion, fields=[nombre])
    campo = clase.base_fields.get(nombre)
    if not isinstance(campo, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
        return _respuesta(error='Catálogo no disponible.', estado=400)
    acotar_relacion(campo, centro)
    consulta = campo.queryset
    if 'ids' in request.GET:
        valores = request.GET.get('ids', '').split(',')
        if not valores or len(valores) > 50:
            return _respuesta(error='Solicita entre uno y cincuenta identificadores.', estado=400)
        try:
            ids = {_id(valor) for valor in valores}
        except ValueError:
            return _respuesta(error='Identificadores no válidos.', estado=400)
        objetos = list(consulta.filter(pk__in=ids).select_related().order_by('pk'))
        if len(objetos) != len(ids):
            return _respuesta(error='Hay opciones fuera del alcance o no disponibles.', estado=400)
        return _respuesta([{'id': objeto.pk, 'text': campo.label_from_instance(objeto)} for objeto in objetos],
                          total=len(objetos))
    texto = request.GET.get('q', '')
    if '\x00' in texto:
        return _respuesta(error='Búsqueda no válida.', estado=400)
    texto = texto.strip()[:120]
    if len(texto) < 2:
        return _respuesta()
    try:
        numero = _id(request.GET.get('pagina', '1'))
    except ValueError:
        return _respuesta(error='Página no válida.', estado=400)
    columnas = {f.name for f in consulta.model._meta.fields}
    nombres = ('username', 'first_name', 'last_name') if consulta.model._meta.app_label == 'auth' else (
        'nombre', 'nombre_corto', 'titulo', 'codigo', 'sigla')
    criterio = Q()
    for columna in nombres:
        if columna in columnas:
            criterio |= Q(**{columna + '__icontains': texto})
    if not criterio:
        return _respuesta()
    paginador = Paginator(consulta.filter(criterio).order_by('pk'), 50)
    if numero > paginador.num_pages:
        return _respuesta(error='Página fuera del catálogo.', estado=400)
    pagina = paginador.page(numero)
    items = [{'id': objeto.pk, 'text': campo.label_from_instance(objeto)}
             for objeto in pagina.object_list.select_related()]
    return _respuesta(items, pagina=pagina.number, paginas=paginador.num_pages, total=paginador.count)
