"""Resultados verificables y su trazabilidad, separados de solicitudes y reservas."""
from apps.documentos.presentation.medicion_metas import resultados_documentados
from apps.documentos.models.resultados_gestion import TIPOS_PRODUCTO
from django.urls import reverse


def dataset_resultados(unidad, inicio, fin, tipo, estado='', buscar=''):
    datos = resultados_documentados(unidad, inicio, fin, tipo)
    opciones = (('borrador', 'Borradores'), ('validado', 'Con verificación vigente'),
                ('pendiente', 'Verificación pendiente'), ('anulado', 'Rectificados'))
    filas = datos['filas']
    if estado == 'validado':
        filas = [f for f in filas if f['verificada']]
    elif estado == 'pendiente':
        filas = [f for f in filas if f['estado'] == 'validado' and not f['verificada']]
    elif estado in dict(opciones):
        filas = [f for f in filas if f['estado'] == estado]
    if buscar:
        texto = buscar.casefold()
        filas = [f for f in filas if texto in ' '.join(str(f[k]) for k in
            ('codigo', 'titulo', 'proyecto', 'producto', 'beneficiario', 'resultado', 'responsable')).casefold()]
    titulo = 'Resultados documentados' if tipo == 'INVESTIGACION' else 'Transferencias y servicios documentados'
    headers = ['Código', 'Fecha', 'Proyecto / convenio', 'Producto / entregable', 'Resultado obtenido',
               'Responsable', 'Estado documental', 'Acreditación']
    rows = [[f['codigo'], f['fecha'].strftime('%d/%m/%Y'), f['proyecto'] or 'Sin vincular',
             f['producto'] or 'Sin documentar', f['resultado'], f['responsable'], f['estado_display'],
             'Sí' if f['acredita'] else 'Ejemplo · no oficial' if f['demostracion'] else 'Pendiente'] for f in filas[:501]]
    reales = sum(f['acredita'] for f in filas)
    demos = sum(f['verificada'] and f['demostracion'] for f in filas)
    pendientes = sum(not f['verificada'] and f['estado'] != 'anulado' for f in filas)
    cards = [(titulo, len(filas)), ('Con respaldo verificado real', reales),
             ('Pendientes de completar / verificar', pendientes), ('Ejemplos verificados', demos, 'no acreditan entrega oficial')]
    respaldo = dict(titulo='Destinatarios, aceptación y respaldos',
        headers=['Código', 'Tipo de producto / servicio', 'Destinatario / beneficiario',
                 'Aceptación / uso', 'Fecha de aceptación', 'Referencia de aceptación', 'Respaldo'],
        rows=[[f['codigo'], dict(TIPOS_PRODUCTO).get(f['tipo_producto'], 'Sin especificar'), f['beneficiario'] or 'Sin identificar',
               'Aceptado' if f['aceptacion'] == 'aceptado' else ('No corresponde' if tipo == 'INVESTIGACION' else 'Pendiente'),
               f['fecha_aceptacion'] or '—', f['referencia_aceptacion'] or '—',
               (reverse('respaldo_meta_unidad', args=[unidad.slug, f['pk']]) + ' · SHA-256: ' + f['sha256'])
               if f['recurso'] else f['enlace'] or 'Sin respaldo'] for f in filas[:500]],
        vacio='No hay resultados documentados para este período y selección.')
    return dict(headers=headers, rows=rows, cards=cards, state_choices=opciones, tablas=[respaldo],
                supporting_documents=[f for f in filas[:500] if f['recurso'] or f['enlace']])
