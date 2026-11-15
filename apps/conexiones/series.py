"""Lectura de series: el punto único del que parten tableros, reportes y análisis.

Quien necesite los datos de un canal (una gráfica, un indicador de uso, un
modelo de análisis) los pide aquí y no consulta la tabla de lecturas por su
cuenta: así la agregación y sus límites se deciden en un solo lugar.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Max, Min
from django.db.models.functions import Trunc
from django.utils import timezone

from apps.conexiones.models import DispositivoConectado, LecturaCanal

INTERVALOS = {'minuto': 'minute', 'hora': 'hour', 'dia': 'day'}
MAX_PUNTOS = 5000
PERIODO_PREDETERMINADO = timedelta(days=1)
PERIODO_MAXIMO = timedelta(days=366)
# Sin envíos en este tiempo un dispositivo se muestra como sin señal.
SIN_SENAL = timedelta(minutes=15)


class ConsultaInvalida(ValueError):
    pass


def periodo(desde=None, hasta=None, ahora=None):
    """Normaliza el periodo pedido; sin fechas, las últimas veinticuatro horas."""
    hasta = hasta or ahora or timezone.now()
    desde = desde or hasta - PERIODO_PREDETERMINADO
    if timezone.is_naive(desde) or timezone.is_naive(hasta):
        raise ConsultaInvalida('Las fechas deben indicar su zona horaria.')
    if desde >= hasta:
        raise ConsultaInvalida('El inicio debe ser anterior al final.')
    if hasta - desde > PERIODO_MAXIMO:
        raise ConsultaInvalida('El periodo consultado no puede superar un año.')
    return desde, hasta


def serie(canal, desde=None, hasta=None, intervalo='hora'):
    """Devuelve los puntos de un canal: crudos o resumidos por minuto, hora o día."""
    desde, hasta = periodo(desde, hasta)
    lecturas = LecturaCanal.objects.filter(canal=canal, instante__gte=desde, instante__lt=hasta)
    if intervalo == 'crudo':
        puntos = [{'instante': instante.isoformat(), 'valor': valor}
                  for instante, valor in lecturas.order_by('instante').values_list('instante', 'valor')[:MAX_PUNTOS + 1]]
    elif intervalo in INTERVALOS:
        puntos = [
            {'instante': fila['tramo'].isoformat(), 'promedio': fila['promedio'], 'minimo': fila['minimo'],
             'maximo': fila['maximo'], 'lecturas': fila['lecturas']}
            for fila in lecturas.annotate(tramo=Trunc('instante', INTERVALOS[intervalo]))
            .values('tramo').annotate(promedio=Avg('valor'), minimo=Min('valor'), maximo=Max('valor'),
                                      lecturas=Count('pk')).order_by('tramo')[:MAX_PUNTOS + 1]
        ]
    else:
        raise ConsultaInvalida('El intervalo debe ser crudo, minuto, hora o dia.')
    if len(puntos) > MAX_PUNTOS:
        raise ConsultaInvalida('El periodo produce demasiados puntos; use un intervalo mayor o un periodo menor.')
    return {'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'intervalo': intervalo, 'puntos': puntos}


def resumen(canal, desde=None, hasta=None):
    """Totales de un canal en el periodo; base para indicadores y alertas."""
    desde, hasta = periodo(desde, hasta)
    datos = LecturaCanal.objects.filter(canal=canal, instante__gte=desde, instante__lt=hasta).aggregate(
        lecturas=Count('pk'), promedio=Avg('valor'), minimo=Min('valor'), maximo=Max('valor'),
        primera=Min('instante'), ultima=Max('instante'))
    return {clave: valor.isoformat() if hasattr(valor, 'isoformat') else valor for clave, valor in datos.items()}


def estado_de_unidad(unidad, ahora=None):
    """Dispositivos de la unidad con la última lectura de cada canal, en dos consultas."""
    ahora = ahora or timezone.now()
    dispositivos = list(DispositivoConectado.objects.filter(unidad=unidad)
                        .prefetch_related('canales').order_by('codigo'))
    ultimas = {lectura.canal_id: lectura for lectura in LecturaCanal.objects.filter(
        canal__dispositivo__unidad=unidad).order_by('canal_id', '-instante').distinct('canal_id')}
    estado = []
    for dispositivo in dispositivos:
        canales = []
        for canal in dispositivo.canales.all():
            ultima = ultimas.get(canal.pk)
            canales.append({
                'canal': canal, 'valor': ultima.valor if ultima else None,
                'instante': ultima.instante if ultima else None,
                'fuera_de_rango': bool(ultima and canal.fuera_de_rango(ultima.valor)),
            })
        estado.append({
            'dispositivo': dispositivo, 'canales': canales,
            'en_linea': bool(dispositivo.activo and dispositivo.ultima_senal
                             and ahora - dispositivo.ultima_senal <= SIN_SENAL),
        })
    return estado
