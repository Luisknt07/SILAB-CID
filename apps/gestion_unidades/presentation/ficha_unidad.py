"""«Ficha de la unidad»: identidad, operación, creación, contacto y equipo, de un vistazo.

Cada dato aparece solo si la unidad lo tiene cargado. El contacto se puede usar
directamente: llamar, escribir o abrir su página. La resolución de creación
sale del expediente con las mismas reglas de acceso que cualquier recurso, y
solo se ve en el visor: la ficha no ofrece descargarla.
"""
import re

from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.detalle import resumir_horario_operativo
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.formacion.presentation.recursos_publicos import resolucion_de_creacion


def iniciales(nombre):
    """Dos iniciales para el avatar, sin contar títulos como «Ing.» o «Tlgo.»."""
    palabras = [palabra for palabra in nombre.split() if not palabra.endswith('.')]
    return ''.join(palabra[0] for palabra in palabras[:2]).upper()


def enlace_telefonico(numero):
    """`tel:` con los dígitos del número; la extensión va tras una pausa, como la marcan los teléfonos."""
    partes = re.split(r'(?i)\s*ext\.?\s*', numero, maxsplit=1)
    digitos = re.sub(r'[^\d+]', '', partes[0])
    extension = re.sub(r'\D', '', partes[1]) if len(partes) > 1 else ''
    return f'tel:{digitos},{extension}' if extension else f'tel:{digitos}'


def equipo_de_la_unidad(unidad):
    """Quien coordina primero y luego el equipo; el responsable asignado entra si no figura ya como contacto."""
    responsables = list(ResponsableUnidad.objects.filter(unidad=unidad, activo=True, publico=True)
                        .select_related('usuario').order_by('orden', 'nombre', 'id'))
    personas = [{
        'pk': responsable.pk,
        'nombre': responsable.nombre_publico,
        'rol': responsable.get_rol_display(),
        'descripcion': responsable.descripcion,
        'email': responsable.email_publico,
        'telefono': responsable.telefono_publico,
        'enlace_telefono': enlace_telefonico(responsable.telefono_publico) if responsable.telefono_publico else '',
        'horario': responsable.horario_atencion,
        'foto': responsable.foto_publica_url,
        'iniciales': iniciales(responsable.nombre_publico),
        'coordina': responsable.rol == 'coordinacion',
    } for responsable in responsables]
    administrador = unidad.administrador
    if administrador and administrador.pk not in {responsable.usuario_id for responsable in responsables}:
        nombre = administrador.get_full_name() or administrador.get_username()
        personas.insert(0, {'pk': None, 'nombre': nombre, 'rol': 'Responsable de la unidad', 'descripcion': '', 'email': '',
                            'telefono': '', 'enlace_telefono': '', 'horario': '', 'foto': '',
                            'iniciales': iniciales(nombre), 'coordina': True})
    return sorted(personas, key=lambda persona: not persona['coordina'])


def contactos_de(unidad, equipo):
    """Los medios de contacto que la unidad tiene, listos para usar."""
    coordinacion = next((persona['email'] for persona in equipo
                         if persona['coordina'] and persona['email'] and persona['email'] != unidad.contacto_email), '')
    contactos = (
        ('fa-phone-alt', 'Teléfono', unidad.telefono, enlace_telefonico(unidad.telefono) if unidad.telefono else ''),
        ('fa-mobile-alt', 'Celular', unidad.celular, enlace_telefonico(unidad.celular) if unidad.celular else ''),
        ('fa-envelope', 'Correo de la unidad', unidad.contacto_email, f'mailto:{unidad.contacto_email}'),
        ('fa-user-tie', 'Correo de coordinación', coordinacion, f'mailto:{coordinacion}'),
        ('fa-globe', 'Página web', unidad.sitio_web, unidad.sitio_web),
    )
    # La página web es la única que sale de la plataforma: se abre aparte.
    return [{'icono': icono, 'etiqueta': etiqueta, 'valor': valor, 'enlace': enlace, 'externo': enlace == unidad.sitio_web}
            for icono, etiqueta, valor, enlace in contactos if valor]


@xframe_options_sameorigin
def ficha_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    equipo = equipo_de_la_unidad(unidad)
    horarios = HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True).select_related('periodo').order_by(
        'periodo__codigo', 'dia_semana', 'hora_inicio')
    presentacion = getattr(unidad, 'presentacion', None)
    # Las líneas de trabajo son parte de la presentación: se ven con ella.
    presentacion_visible = bool(presentacion and (presentacion.publicada or gestor))
    resolucion = resolucion_de_creacion(unidad, request.user, gestor)
    return render(request, 'portal/pages/unidades/detalle/ficha_unidad.html', {
        'unidad': unidad,
        'equipo': equipo,
        'contactos': contactos_de(unidad, equipo),
        'horario': resumir_horario_operativo(list(horarios)) or unidad.horario_atencion,
        'resolucion': resolucion,
        'adscrita_aparte': bool(unidad.adscrita_a and str(unidad.adscrita_a) != unidad.facultad),
        'lineas_accion': list(unidad.lineas_accion.all()) if presentacion_visible else [],
        'areas_trabajo': presentacion.areas_trabajo if presentacion_visible else '',
        'gestor': gestor,
        'ubicacion_url': reverse('ubicacion_unidad', args=[unidad.slug]),
        'expediente_url': reverse('gestion_expediente_unidad', args=[unidad.slug]) if gestor else '',
        'ediciones': ediciones_de(request.user, unidad),
    })
