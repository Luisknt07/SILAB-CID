"""Relaciones de lectura entre la planificación y sus respaldos ya existentes.

No crea documentos, metas ni resultados. Los documentos y sus relaciones se
reciben precargados por el expediente; ordenar la pantalla no consulta fuentes.
"""
from urllib.parse import urlencode

from django.urls import reverse


def _alcance(documento):
    return (getattr(documento, 'unidad_id', None), documento.anio, documento.corte,
            getattr(documento, 'marco_periodo', ''))


def contextualizar_soportes_planificacion(documentos):
    """Enlaza soportes del mismo plan, unidad, semestre y marco conservado.

    El catálogo distribuido ya no da anexos a la planificación (documentos.0024):
    la carga por asignatura y los mantenimientos previstos son secciones de su
    PDF. Un anexo que la institución agregue al plan se presenta aquí como
    respaldo, sin meta ni aporte propio al expediente.
    """
    documentos = list(documentos)
    planes = {_alcance(d): d for d in documentos if d.exigido.codigo == 'PLANIFICACION'}
    for plan in planes.values():
        plan.anexos_integrados = []
    for documento in documentos:
        documento.soporte_planificacion = None
        if not documento.exigido.es_anexo or documento.estado == 'no_aplica':
            continue
        padre = planes.get(_alcance(documento))
        padre_id = getattr(padre, 'exigido_id', None) if padre is not None else None
        if padre_id is None or getattr(documento.exigido, 'anexo_de_id', None) != padre_id:
            continue
        # Las fechas históricas no se mezclan con el semestre natural aunque
        # compartan la letra A/B. Un respaldo anual conserva su alcance anual.
        if documento.exigido.periodicidad == 'semestral' and any(
                getattr(documento, campo, None) and getattr(padre, campo, None)
                and getattr(documento, campo) != getattr(padre, campo)
                for campo in ('tramo_inicio', 'tramo_fin')):
            continue
        unidad = padre.unidad
        parametros = dict(anio=padre.anio, corte=padre.corte,
                          gestionar=padre.pk or padre.exigido.codigo)
        documento.soporte_planificacion = dict(
            documento=padre, codigo=padre.exigido.codigo, nombre=padre.nombre_documental,
            url=reverse('gestion_expediente_unidad', args=[unidad.slug]) + '?' + urlencode(parametros),
            url_director=reverse('admin:reportes-cumplimiento-expediente') + '?' + urlencode(dict(
                unidad=unidad.slug, anio=padre.anio, corte=padre.corte,
                **({'revisar': padre.pk} if padre.pk else {}))),
            etiqueta='Soporte de la planificación semestral', es_soporte=True, aporta_puntos=False,
            meta_codigo='', unidad_medida='Documento de respaldo',
            descripcion=('Respalda el plan semestral y conserva su propio alcance; no añade una obligación, '
                         'una meta ni puntos independientes.'),
        )
        padre.anexos_integrados.append(documento)
    for plan in planes.values():
        plan.anexos_integrados.sort(key=lambda d: (d.exigido.orden, d.exigido.codigo))
    return documentos


def casilla_de_soporte_planificacion(anexo):
    """Fila consultable del director; nunca se transforma en una obligación."""
    documento = anexo['documento']
    soporte = getattr(documento, 'soporte_planificacion', None)
    return dict(anexo, es_soporte_planificacion=True, es_anexo=True,
                documento_padre=soporte['documento'], soporte_planificacion=soporte,
                aporta_puntos=False)
