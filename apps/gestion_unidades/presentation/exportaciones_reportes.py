"""Adaptación explícita del reporte de unidad al contrato puro de exportación."""
from django.core.exceptions import BadRequest

from apps.core.reportes import FORMATOS, respuesta_reporte


def formato_reporte(request, *, permitir_csv=True):
    formato = (request.GET.get('formato') or '').strip()
    admitidos = FORMATOS | ({'csv'} if permitir_csv else set())
    if formato and formato not in admitidos:
        raise BadRequest('Formato de reporte no admitido.')
    return formato


def tablas_complementarias(reporte):
    """Incluye los respaldos que se consultan en HTML en todas las descargas."""
    from django.urls import reverse

    datos = reporte.get('dataset') or {}
    tablas = list(datos.get('tablas', ()))
    fuentes = datos.get('supporting_documents') or ()
    if fuentes:
        filas = []
        for fuente in fuentes:
            enlace = (reverse('respaldo_meta_unidad', args=[reporte['unit'].slug, fuente['pk']])
                      if fuente.get('recurso') else fuente.get('enlace') or 'Sin respaldo')
            filas.append([fuente.get('codigo', ''), fuente.get('titulo', ''), enlace])
        tablas.append({'titulo': 'Consultar los respaldos',
            'headers': ['Código', 'Evidencia', 'Documento'], 'rows': filas})
    return tablas


def contrato_unidad(reporte):
    metricas, secciones, notas = [], [], []
    if reporte['is_generic']:
        datos = reporte['dataset']
        for tarjeta in datos['cards']:
            metricas.append({'nombre': tarjeta[0], 'valor': tarjeta[1],
                'periodo': tarjeta[2] if len(tarjeta) > 2 else 'Período seleccionado'})
        secciones.append({'titulo': reporte['category_label'], 'headers': datos['headers'], 'rows': datos['rows']})
        if datos.get('structured'):
            for registro in datos.get('records', ()):
                for seccion in registro.get('sections', ()):
                    secciones.append({'titulo': f"{registro['code']} · {seccion['title']}",
                        'headers': ['Campo', 'Contenido'],
                        'rows': [[campo['label'], campo['value']] for campo in seccion.get('fields', ())]})
        for tabla in tablas_complementarias(reporte):
            secciones.append({'titulo': tabla['titulo'], 'headers': tabla['headers'], 'rows': tabla['rows']})
        notas.extend(datos.get('notes', ()))
        if datos.get('truncated'):
            notas.append('Detalle limitado como en la pantalla. Refina los filtros para consultar todos los registros.')
    else:
        for etiqueta, clave in [('Solicitudes', 'total'), ('Atenciones efectivas', 'confirmed'),
                               ('Horas efectivas', 'hours'), ('Participantes atendidos', 'participants')]:
            metricas.append({'nombre': etiqueta, 'valor': reporte['metrics'][clave], 'periodo': 'Período seleccionado'})
        secciones.append({'titulo': 'Resumen por ' + reporte['group_label'],
            'headers': [reporte['group_label'], 'Solicitudes', 'Atenciones efectivas', 'Horas', 'Participantes'],
            'rows': [[f['label'], f['total'], f['effective'], f['hours'], f['participants']] for f in reporte['rows']]})
        from apps.gestion_unidades.presentation.reportes_excel import _hojas_de_reservas
        _nombre, titulo, headers, filas = _hojas_de_reservas(reporte)[1]
        secciones.append({'titulo': titulo, 'headers': headers, 'rows': filas})
        notas.extend(reporte.get('notes', ()))
        if reporte.get('detail_truncated'):
            notas.append('El detalle muestra los primeros 150 registros, igual que la pantalla y el PDF. Las métricas abarcan todos los resultados filtrados.')
    return {'title': reporte['category_label'], 'scope': reporte['scope_label'],
            'generated_at': reporte['generated_at'], 'filter_summary': reporte['filter_summary'],
            'metrics': metricas, 'sections': secciones, 'notes': notas}


def marco_pdf_unidad(reporte):
    """La vista previa y la descarga comparten identidad, márgenes y paginación."""
    from apps.core.presentation.pdf_institucional import marco_institucional, metadatos_documento

    datos = (reporte.get('dataset') or {}).get('document_meta') or {}
    # Un anexo generado para el expediente lleva código, revisión, período y versión;
    # una consulta muestra su período y cuándo se generó.
    expediente = reporte.get('expediente') or {}
    periodo = expediente.get('periodo') or (
        f"{reporte['start_date']:%d/%m/%Y} – {reporte['end_date']:%d/%m/%Y}" if reporte.get('periodo', True) else None)
    metadatos = metadatos_documento(
        datos.get('code') or expediente.get('codigo'), revision=datos.get('revision', '01'), periodo=periodo,
        generado=None if expediente else reporte['generated_at'])
    dibujar, lienzo, medidas = marco_institucional(
        formato=datos.get('title') or reporte['category_label'], metadatos=metadatos,
        pie='Centro de reportes', apaisado=True,
    )
    if reporte.get('borrador'):
        from apps.documentos.presentation.documentos_entrega import con_marca_borrador
        dibujar = con_marca_borrador(dibujar)
    return dibujar, lienzo, medidas


def descargar_unidad(reporte, formato):
    if formato == 'csv':
        import csv
        from django.http import HttpResponse
        from django.utils.http import content_disposition_header
        from django.utils.text import slugify
        from .seguimiento_reportes import celda_csv_segura

        datos = contrato_unidad(reporte)
        respuesta = HttpResponse('\ufeff', content_type='text/csv; charset=utf-8')
        nombre = f"reporte-{reporte['unit'].slug}-{reporte['start_date'].isoformat()}-{reporte['end_date'].isoformat()}.csv"
        respuesta['Content-Disposition'] = content_disposition_header(True, slugify(nombre[:-4]) + '.csv')
        respuesta['Cache-Control'] = 'private, no-store'
        respuesta['X-Content-Type-Options'] = 'nosniff'
        escritor = csv.writer(respuesta, delimiter=';')
        def fila(valores):
            escritor.writerow([celda_csv_segura(v) for v in valores])
        fila([datos['title'], datos['scope']])
        fila(['Generado', datos['generated_at']])
        for criterio in datos['filter_summary']:
            fila(criterio)
        for metrica in datos['metrics']:
            fila([metrica['nombre'], metrica['valor'], metrica['periodo']])
        for nota in datos['notes']:
            fila(['Nota', nota])
        for seccion in datos['sections']:
            escritor.writerow([])
            fila([seccion['titulo']])
            fila(seccion['headers'])
            for registro in seccion['rows']:
                fila(registro)
        return respuesta
    # Un solo renderizador evita que formato=pdf pierda matrices, diagramas o
    # detalles respecto al visor y que la planilla use columnas diferentes.
    if formato in ('pdf', 'xlsx'):
        from django.http import HttpResponse
        from django.utils.cache import patch_cache_control
        from django.utils.text import slugify
        from apps.core.reportes import TIPOS
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
        from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx

        contenido = (render_unit_report_pdf(reporte) if formato == 'pdf'
                     else render_unit_report_xlsx(reporte))
        nombre = f"reporte-{reporte['unit'].slug}-{reporte['start_date'].isoformat()}-{reporte['end_date'].isoformat()}"
        respuesta = HttpResponse(contenido, content_type=TIPOS[formato])
        respuesta['Content-Disposition'] = f'attachment; filename="{slugify(nombre)}.{formato}"'
        respuesta['X-Content-Type-Options'] = 'nosniff'
        patch_cache_control(respuesta, private=True, no_store=True)
        return respuesta
    return respuesta_reporte(contrato_unidad(reporte), formato,
        f"reporte-{reporte['unit'].slug}-{reporte['start_date'].isoformat()}-{reporte['end_date'].isoformat()}",
        marco_pdf=marco_pdf_unidad(reporte) if formato == 'pdf' else None)
