"""Una lectura para la tabla, gráfica y PDF de estadísticas de reservas."""

from io import BytesIO

from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.utils import timezone

from apps.reservas.workflows.reservas import ESTADOS_APROBADOS


def estadisticas_reservas(consulta, *, anio=None, por_unidad=False, alcance='Reservas'):
    consulta = consulta.order_by()
    anios = sorted({d.year for d in consulta.dates('fecha', 'year')}, reverse=True)
    if anio:
        consulta = consulta.filter(fecha__year=anio)
    if por_unidad:
        grupos = consulta.values('laboratorio_id', 'laboratorio__nombre')
    else:
        grupos = consulta.annotate(semana=TruncWeek('fecha')).values('semana').order_by('semana')
    grupos = grupos.annotate(total=Count('pk'), aprobadas=Count('pk', filter=Q(estado__in=ESTADOS_APROBADOS)))
    if por_unidad:
        grupos = grupos.order_by('-total', 'laboratorio_id')
    filas = []
    for grupo in grupos:
        nombre = (grupo['laboratorio__nombre'] or 'Sin unidad') if por_unidad else grupo['semana'].strftime('%d/%m/%Y')
        total, aprobadas = grupo['total'], grupo['aprobadas']
        filas.append((nombre, aprobadas, total - aprobadas, round(100 * aprobadas / total, 1) if total else 0))
    titulo = 'Reservas por unidad' if por_unidad else 'Reservas por semana'
    seleccion = [('Agrupación', 'Unidad' if por_unidad else 'Semana'), ('Año', anio or 'Todo el historial')]
    return {
        'filas': filas, 'years_list': anios, 'titulo_estadisticas': titulo,
        'category_label': titulo, 'scope_label': alcance, 'generated_at': timezone.localtime(),
        'periodo': False, 'filter_summary': seleccion, 'is_generic': True,
        'detail_truncated': False,
        'dataset': {'headers': ['Unidad' if por_unidad else 'Semana', 'Aprobadas', 'No aprobadas', 'Aprobación (%)'],
                    'rows': filas, 'cards': [('Solicitudes', sum(f[1] + f[2] for f in filas))],
                    'truncated': False},
    }


def grafica_estadisticas(filas, titulo, *, por_unidad=False):
    """Una figura por petición, sin estado compartido de pyplot."""
    from matplotlib.figure import Figure

    seleccion = filas[:5] if por_unidad else filas
    fig = Figure(figsize=(10, 5))
    ax = fig.subplots()
    posiciones = list(range(len(seleccion)))
    ancho = .35
    ax.bar([x - ancho / 2 for x in posiciones], [f[1] for f in seleccion], ancho,
           label='Aprobadas', color='#28a745')
    ax.bar([x + ancho / 2 for x in posiciones], [f[2] for f in seleccion], ancho,
           label='No aprobadas', color='#dc3545')
    ax.set_title(titulo, fontsize=16, fontweight='bold', color='#007bff')
    ax.set_ylabel('Total reservas')
    ax.set_xticks(posiciones, [f[0][:28] for f in seleccion], rotation=45, ha='right')
    ax.legend(frameon=False)
    ax.grid(axis='y', linestyle='--', alpha=.3)
    fig.tight_layout()
    salida = BytesIO()
    fig.savefig(salida, format='png')
    return salida.getvalue()
