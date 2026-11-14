"""Consultas científicas públicas: filtrar y contar antes de materializar páginas.

Los expedientes y las credenciales no forman parte de estas consultas. Los
catálogos pueden exportarse completos; la paginación pertenece a la presentación.
"""
from decimal import Decimal

from django.db.models import Count, Exists, OuterRef, Q, Sum, Max, Value, TextField
from django.db.models.functions import Concat, ExtractYear
from django.utils import timezone

from .escenarios import filtro_contenido
from .models import Proyecto, Resultado


def proyectos_publicos(centro):
    return centro.proyectos.filter(publicado=True, **filtro_contenido(centro))


def resultados_publicos(centro, catalogo):
    tipos = Resultado.CIENTIFICOS if catalogo == 'produccion' else Resultado.INNOVACION
    return centro.resultados.filter(publicado=True, confidencial=False,
                                    tipo__in=tipos, **filtro_contenido(centro))


def filtros(parametros, campos):
    return {campo: parametros.get(campo, '').strip()[:200] for campo in campos}


def _numero(consulta, campo, valor):
    # No pasar enteros enormes a PostgreSQL ni transformar una entrada inválida
    # en una consulta sin filtro.
    if not valor.isascii() or not valor.isdigit() or len(valor) > 18:
        return consulta.none()
    if campo.endswith('__year') and not 1 <= int(valor) <= 9999:
        return consulta.none()
    return consulta.filter(**{campo: int(valor)})


def _buscar(consulta, texto, campos):
    if not texto:
        return consulta
    if len(campos) == 1:
        return consulta.filter(**{campos[0] + '__icontains': texto})
    partes = []
    for campo in campos:
        if partes:
            partes.append(Value(' '))
        partes.append(campo)
    return consulta.alias(_texto_busqueda=Concat(*partes, output_field=TextField())).filter(
        _texto_busqueda__icontains=texto)


def filtrar_proyectos(consulta, parametros):
    for campo in ('estado', 'sector'):
        if parametros.get(campo):
            consulta = consulta.filter(**{campo: parametros[campo]})
    for parametro, campo in (('linea', 'linea_id'), ('anio', 'inicio__year')):
        if parametros.get(parametro):
            consulta = _numero(consulta, campo, parametros[parametro])
    if parametros.get('area'):
        consulta = consulta.filter(componentes__codigo=parametros['area']).distinct()
    return _buscar(consulta, parametros.get('q', ''), ('titulo', 'codigo', 'resumen'))


def _respaldo(consulta, campos, fecha):
    consulta = consulta.filter(**{fecha + '__lte': timezone.localdate()})
    for campo in campos:
        consulta = consulta.filter(**{campo + '__regex': r'\S'})
    return consulta


def trl_documentados(consulta):
    return _respaldo(consulta.filter(trl__isnull=False).exclude(trl=0),
                    ('trl_evaluador', 'trl_alcance', 'trl_evidencia'), 'trl_fecha')


def pi_documentada(consulta):
    return _respaldo(consulta, ('estado_pi', 'pi_modalidad', 'pi_titular', 'pi_evidencia'), 'pi_fecha')


def casos_documentados(centro):
    return _respaldo(centro.casos.filter(publicado=True, **filtro_contenido(centro)),
                    ('receptor', 'mecanismo', 'evidencia', 'autorizacion_publicacion'), 'fecha_transferencia')


def filtrar_resultados(consulta, parametros, centro):
    for campo in ('tipo', 'sector', 'tecnologia'):
        if parametros.get(campo):
            consulta = consulta.filter(**{campo: parametros[campo]})
    for parametro, campo in (('anio', 'anio'), ('proyecto', 'proyecto_id'), ('linea', 'proyecto__linea_id')):
        if parametros.get(parametro):
            consulta = _numero(consulta, campo, parametros[parametro])
            if parametro in ('proyecto', 'linea'):
                # Una referencia oculta se elimina también en la ficha. No usarla
                # indirectamente como filtro del catálogo público.
                consulta = consulta.filter(proyecto__in=proyectos_publicos(centro).values('pk'))
    if parametros.get('trl'):
        consulta = _numero(trl_documentados(consulta), 'trl', parametros['trl'])
    return _buscar(consulta, parametros.get('q', ''), ('titulo', 'descripcion', 'autores_texto', 'doi'))


def distintos(consulta, campo, vacios=False):
    if not vacios:
        consulta = consulta.exclude(**{campo: ''})
    return list(consulta.order_by(campo).values_list(campo, flat=True).distinct())


def opciones_proyectos(consulta, texto='', seleccionado=''):
    """Acotar el selector sin limitar los resultados ni perder la selección actual."""
    texto = texto.strip()[:200]
    opciones = list(_buscar(consulta, texto, ('titulo',)).order_by('titulo', 'pk').values('pk', 'titulo')[:201])
    hay_mas = len(opciones) > 200
    opciones = opciones[:200]
    if seleccionado and seleccionado.isascii() and seleccionado.isdigit() and len(seleccionado) <= 18:
        identificador = int(seleccionado)
        if identificador not in {o['pk'] for o in opciones}:
            actual = consulta.filter(pk=identificador).values('pk', 'titulo').first()
            if actual:
                opciones.append(actual)
    return {'opciones': opciones, 'hay_mas': hay_mas, 'q': texto}


def anios_proyectos(consulta):
    return list(consulta.filter(inicio__isnull=False).annotate(_anio=ExtractYear('inicio'))
                .order_by('-_anio').values_list('_anio', flat=True).distinct())


def financiado_publico(consulta):
    return consulta.filter(monto_publico=True).aggregate(total=Sum('monto'))['total'] or Decimal(0)


def cifras_proyectos(centro):
    casos = casos_documentados(centro).filter(proyecto_id=OuterRef('pk'))
    consulta = proyectos_publicos(centro).alias(_transferido=Exists(casos))
    return consulta.aggregate(total=Count('pk'), activos=Count('pk', filter=Q(estado__in=Proyecto.ACTIVOS)),
        concluidos=Count('pk', filter=Q(estado='finalizado') | Q(estado='transferido', _transferido=True)),
        financiados=Count('pk', filter=~Q(financiador='')))


def proyectos_para_pagina(consulta, centro):
    casos = casos_documentados(centro).filter(proyecto_id=OuterRef('pk'))
    return consulta.select_related('linea', 'responsable').annotate(transferencia_catalogo=Exists(casos))


def cifras_resultados(centro, catalogo):
    consulta = resultados_publicos(centro, catalogo)
    if catalogo == 'produccion':
        return consulta.aggregate(total=Count('pk'), tipos=Count('tipo', distinct=True), anios=Count('anio', distinct=True))
    pi = pi_documentada(consulta).values('pk')
    trl = trl_documentados(consulta).values('pk')
    return consulta.aggregate(prototipos=Count('pk', filter=Q(tipo='prototipo')),
        propiedad=Count('pk', filter=Q(tipo='propiedad_intelectual', pk__in=pi)),
        trl=Max('trl', filter=Q(pk__in=trl)))
