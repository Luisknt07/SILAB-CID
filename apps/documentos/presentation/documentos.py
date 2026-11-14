"""Cada página del aula se ve en pantalla y se baja ya formateada.

Las páginas del aula son documentos: la ficha de un proceso, su documentación,
lo que la planta produce, el resultado de un simulador. Hasta ahora la única
manera de bajarlos era el «Imprimir» del navegador, que escribe la dirección, la
fecha y el número de página en los bordes, corta las tablas donde caiga y no
sabe nada del formato institucional: una fotografía de la pantalla con otro
nombre.

Aquí cada página declara qué lleva su documento y lo arma el mismo presentador
que ya hacía bien los reportes de laboratorio. Con «formato=pdf» la página
devuelve el archivo en vez de la pantalla: sin `descargar` lo abre en el visor
del navegador, para revisarlo antes de bajarlo, y con `descargar=1` lo baja.
"""

from django.http import HttpResponse
from django.utils import timezone

from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf


def documento(*, titulo, alcance, criterios=(), notas='', tarjetas=(), headers=(), filas=(), tablas=(), dibujos=()):
    """El diccionario que consume el presentador institucional.

    Es la misma forma que usan el reporte de una unidad y el listado de reservas,
    así que un documento nuevo no inventa su propio formato: hereda la cabecera
    con el logo, la banda de criterios, las tarjetas y las tablas.
    """
    hoy = timezone.localdate()
    cabeceras = list(headers)
    return {
        'scope_label': alcance,
        'generated_at': timezone.localtime(),
        'start_date': hoy,
        'end_date': hoy,
        'category_label': titulo,
        'filter_summary': list(criterios),
        'is_generic': True,
        # Estas páginas no cubren un rango de fechas: describen cómo está la
        # unidad hoy, así que la cabecera no anuncia un período.
        'periodo': False,
        'notas': notas,
        'dataset': {
            'headers': cabeceras,
            'rows': [list(fila) for fila in filas],
            'cards': list(tarjetas),
            'tablas': list(tablas),
            # (título, Lienzo): diagramas en vectores, la misma geometría que la página.
            'dibujos': list(dibujos),
            'matrix': False,
            'matrix_kind': '',
            'structured': False,
            'records': [],
            'document_meta': {},
            'truncated': False,
            'state_choices': (),
            'column_count': max(1, len(cabeceras)),
        },
    }


def tabla(titulo, headers, filas, vacio):
    """Una tabla más dentro del mismo documento."""
    return {
        'titulo': titulo,
        'headers': list(headers),
        'rows': [list(fila) for fila in filas],
        'vacio': vacio,
    }


def formato_pedido(request):
    """Qué pidió la dirección: la página, el documento para verlo o para bajarlo."""
    if (request.GET.get('formato') or '').strip() != 'pdf':
        return ''
    return 'descargar' if request.GET.get('descargar') == '1' else 'ver'


def respuesta_pdf(reporte, nombre, formato):
    """El PDF, abierto en el visor del navegador o bajado como archivo."""
    respuesta = HttpResponse(render_unit_report_pdf(reporte), content_type='application/pdf')
    disposicion = 'attachment' if formato == 'descargar' else 'inline'
    respuesta['Content-Disposition'] = f'{disposicion}; filename="{nombre}"'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


def enlaces_de_documento(request):
    """Las dos acciones del documento, conservando los filtros que tenga la página.

    Se ve primero y se baja después: el mismo archivo, con la misma dirección y
    un parámetro de diferencia, para que lo revisado sea exactamente lo bajado.
    """
    consulta = request.GET.copy()
    consulta.pop('formato', None)
    consulta.pop('descargar', None)
    base = consulta.urlencode()
    prefijo = f'?{base}&' if base else '?'
    return {
        'ver_documento_url': f'{prefijo}formato=pdf',
        'descargar_documento_url': f'{prefijo}formato=pdf&descargar=1',
    }
