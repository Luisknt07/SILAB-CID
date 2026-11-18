"""Satisfacción de los usuarios: valoraciones de las reservas atendidas del período.

Es un registro: cuenta, promedia y lista. Los comentarios salen con su fecha y su
valoración, sin el solicitante, la reserva ni otro dato que identifique a quien los escribió.
"""
from collections import Counter

from django.utils import timezone

from apps.gestion_unidades.presentation.reportes_seguimiento_documental import _dataset
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.valoraciones import RESERVA_ATENDIDA, ValoracionReserva

ASPECTOS = (('general', 'Valoración general'), *ValoracionReserva.ASPECTOS)
MESES = ('', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')


def _promedio(valores):
    valores = [valor for valor in valores if valor]
    return f'{sum(valores) / len(valores):.2f}' if valores else '—'


def _porcentaje(parte, total):
    return f'{100 * parte / total:.1f} %' if total else '—'


def reporte_satisfaccion(unit, start_date, end_date, state='', search=''):
    """Respuestas, tasa de respuesta, promedios, distribución, meses y comentarios anónimos.

    El período se lee por la fecha de la reserva: la tasa compara las valoraciones con las
    reservas que la unidad cerró como atendidas en ese mismo rango. La búsqueda solo
    selecciona comentarios.
    """
    atendidas = Counter(
        (fecha.year, fecha.month) for fecha in Reserva.objects.filter(
            laboratorio=unit, fecha__range=(start_date, end_date), **RESERVA_ATENDIDA,
        ).values_list('fecha', flat=True))
    valoraciones = list(ValoracionReserva.objects.filter(
        reserva__laboratorio=unit, reserva__fecha__range=(start_date, end_date),
        **{f'reserva__{campo}': valor for campo, valor in RESERVA_ATENDIDA.items()},
    ).order_by('registrada_en', 'pk').values(
        'general', *(codigo for codigo, _nombre in ValoracionReserva.ASPECTOS),
        'comentario', 'registrada_en', 'reserva__fecha'))
    respuestas, total_atendidas = len(valoraciones), sum(atendidas.values())

    promedios = [[nombre, sum(1 for v in valoraciones if v[codigo]), _promedio(v[codigo] for v in valoraciones)]
                 for codigo, nombre in ASPECTOS]
    distribucion = Counter(v['general'] for v in valoraciones)
    por_mes = {}
    for valoracion in valoraciones:
        fecha = valoracion['reserva__fecha']
        por_mes.setdefault((fecha.year, fecha.month), []).append(valoracion['general'])
    meses = [[f'{MESES[mes]} {anio}', atendidas[(anio, mes)], len(por_mes.get((anio, mes), ())),
              _porcentaje(len(por_mes.get((anio, mes), ())), atendidas[(anio, mes)]),
              _promedio(por_mes.get((anio, mes), ()))]
             for anio, mes in sorted(atendidas)]
    buscar = str(search or '').strip().casefold()
    comentarios = [[timezone.localtime(v['registrada_en']).strftime('%d/%m/%Y'), f'{v["general"]} de 5', v['comentario']]
                   for v in valoraciones if v['comentario'] and buscar in v['comentario'].casefold()]
    return _dataset(
        ['Aspecto', 'Respuestas', 'Promedio (1 a 5)'], promedios,
        [('Respuestas recibidas', respuestas), ('Reservas atendidas', total_atendidas),
         ('Tasa de respuesta', _porcentaje(respuestas, total_atendidas)),
         ('Promedio general', _promedio(v['general'] for v in valoraciones))], (),
        [dict(titulo='Distribución de la valoración general', headers=['Valoración', 'Respuestas', 'Porcentaje'],
              rows=[[f'{valor} de 5', distribucion[valor], _porcentaje(distribucion[valor], respuestas)]
                    for valor in (5, 4, 3, 2, 1)] if respuestas else []),
         dict(titulo='Respuestas por mes',
              headers=['Mes', 'Reservas atendidas', 'Respuestas', 'Tasa de respuesta', 'Promedio general'], rows=meses),
         dict(titulo='Comentarios', headers=['Fecha', 'Valoración', 'Comentario'], rows=comentarios)],
        [])
