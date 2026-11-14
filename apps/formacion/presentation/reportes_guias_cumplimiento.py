"""Guías y su evidencia académica: publicar no equivale a acreditar el syllabus."""

from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.html import strip_tags

from apps.documentos.presentation.cumplimiento_practicas import diagnostico_guia
from apps.formacion.models.practicas import PlanificacionPractica
from apps.reservas.models.reservas import GuiaActividadReserva


def reporte_guias_cumplimiento(unit, start_date, end_date, state='', search=''):
    es_laboratorio = unit.dependencia == 'laboratorios'
    planes = PlanificacionPractica.objects.filter(
        unidad=unit, eliminado_en__isnull=True, es_version_vigente=True,
    ).exclude(estado='archivada').select_related('tema_asignatura__asignatura')
    queryset = GuiaActividadReserva.objects.filter(actividad__unidad=unit, activo=True).filter(
        Q(actualizado_en__date__range=(start_date, end_date)) | Q(es_vigente=True),
    ).select_related('actividad', 'aprobado_por').prefetch_related(
        Prefetch('planificaciones_practica', queryset=planes, to_attr='_planes_syllabus'),
    ).order_by('actividad__nombre', 'titulo', '-numero_version', 'pk')
    choices = GuiaActividadReserva.ESTADO_CHOICES
    if state in dict(choices):
        queryset = queryset.filter(estado_publicacion=state)
    if search:
        queryset = queryset.filter(
            Q(titulo__icontains=search) | Q(codigo_guia__icontains=search)
            | Q(actividad__nombre__icontains=search)
            | Q(planificaciones_practica__tema_asignatura__asignatura__nombre__icontains=search),
        ).distinct()
    headers = ['Código', 'Guía de práctica', 'Versión', 'Estado', 'Asignatura y tema del syllabus',
               'Resultado de aprendizaje', 'Aprobación', 'Respaldo', 'Pendientes documentales']
    if es_laboratorio:
        headers[0], headers[1] = 'Código de la guía', 'Guía de práctica · formato FT04'
    rows, cache = [], {}
    total = publicadas = vinculadas = acreditables = pendientes = nuevas_acreditables = 0
    # También las tarjetas cubren el conjunto completo; el límite solo afecta
    # las filas que puede presentar/exportar el Centro de reportes.
    for guia in queryset.iterator(chunk_size=200):
        diagnostico = diagnostico_guia(guia, planes=guia._planes_syllabus, cache_archivos=cache)
        total += 1
        publicadas += guia.estado_publicacion == 'publicada' and guia.es_vigente
        vinculadas += diagnostico['syllabus']
        acreditables += diagnostico['cumple']
        nuevas_acreditables += diagnostico['cumple'] and start_date <= timezone.localdate(guia.actualizado_en) <= end_date
        pendientes += not diagnostico['cumple']
        if len(rows) >= 501:
            continue
        temas, resultados = set(), set()
        for plan in guia._planes_syllabus:
            if plan.tema_asignatura_id:
                tema = plan.tema_asignatura
                temas.add(f'{tema.asignatura.nombre} · {tema.nombre}')
                if tema.resultado_aprendizaje.strip():
                    resultados.add(strip_tags(tema.resultado_aprendizaje).strip())
        contenido = guia.contenido if isinstance(guia.contenido, dict) else {}
        resultado_guia = strip_tags(str(contenido.get('resultado_aprendizaje') or '')).strip()
        if resultado_guia:
            resultados.add(resultado_guia)
        aprobacion = 'Sin aprobación registrada'
        if guia.aprobado_por_id and guia.aprobado_en:
            aprobacion = (f'{guia.aprobado_por.get_full_name() or guia.aprobado_por.get_username()} · '
                          f'{timezone.localtime(guia.aprobado_en):%d/%m/%Y}')
        respaldo = ('Formato institucional' if guia.es_estructurada else
                    'PDF importado' if guia.archivo else 'Sin PDF')
        if es_laboratorio and guia.es_estructurada:
            respaldo = 'Formato UPEC-P10-S01-FT04'
        if 'Archivo PDF de la guía disponible' in diagnostico['faltantes']:
            respaldo = 'PDF no disponible'
        rows.append([
            guia.codigo_guia or 'Sin código', guia.titulo,
            f'v{guia.numero_version} (' + ('vigente)' if guia.es_vigente else 'no vigente)'),
            guia.get_estado_publicacion_display(), '; '.join(sorted(temas)) or 'Sin vincular',
            '; '.join(sorted(resultados)) or 'Sin resultado vinculado', aprobacion, respaldo,
            '; '.join(diagnostico['faltantes']) or 'Respaldo completo',
        ])
    cards = [('Guías registradas', total), ('Aprobadas y vigentes', publicadas),
             ('Vinculadas al syllabus', vinculadas), ('Con respaldo completo', acreditables),
             ('Pendientes documentales', pendientes)]
    if es_laboratorio:
        cards.insert(4, ('Nuevas o actualizadas con respaldo', nuevas_acreditables,
                         'actualizadas dentro del período; las vigentes anteriores se conservan para consulta'))
    return headers, rows, cards, choices
