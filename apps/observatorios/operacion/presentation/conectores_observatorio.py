"""Las conexiones automáticas que mantienen al día los indicadores de un observatorio desde APIs públicas.

Cada tipo de conexión sabe consultar una clase de fuente y devuelve los valores como (periodo, fecha, valor). Lo que
llega entra con origen «api»: si el valor ya existía y cambió, la corrección queda en el historial de revisiones,
de modo que lo publicado antes nunca se pierde. El periodo en curso (el mes o el año que aún no termina) se marca
como provisional. Las consultas se identifican con el nombre de la plataforma y no envían datos de nadie.
"""
import csv
import io
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone

from apps.observatorios.operacion.models.observatorios import ConectorIndicador, ValorIndicador

AGENTE = 'CITT-Laboratorios/1.0 (plataforma universitaria)'
ESPERA = 40


class ErrorDeConexion(Exception):
    """La fuente no respondió o respondió algo que no se entiende."""


def _leer(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': AGENTE, 'Accept': '*/*'}), timeout=ESPERA) as respuesta:
            return respuesta.read()
    except OSError as error:
        raise ErrorDeConexion(f'La fuente no respondió: {error}') from error


def _json(url):
    try:
        return json.loads(_leer(url).decode('utf-8'))
    except ValueError as error:
        raise ErrorDeConexion('La fuente no devolvió JSON.') from error


def _decimal(texto):
    try:
        return Decimal(str(texto).strip().replace(' ', '').replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _periodo(fecha, por):
    """El periodo publicado y su fecha de referencia: «2025» o «2025-03», con el primer día del periodo."""
    if por == 'anio':
        return f'{fecha.year}', date(fecha.year, 1, 1)
    if por == 'dia':
        return fecha.isoformat(), fecha
    return f'{fecha.year}-{fecha.month:02d}', date(fecha.year, fecha.month, 1)


def _fecha(texto):
    texto = str(texto)[:10]
    if len(texto) == 4:
        return date(int(texto), 1, 1)
    if len(texto) == 7:
        return date(int(texto[:4]), int(texto[5:7]), 1)
    return date.fromisoformat(texto)


# ---------------------------------------------------------------- tipos de conexión
MESES = {nombre: numero for numero, nombre in enumerate(
    ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre',
     'diciembre'), start=1)}


def socrata(p):
    """Un conjunto de datos Socrata (datos.gov.co), agregado por periodo con una consulta SoQL.

    El periodo sale de un campo de fecha (`campo_fecha`, con `por` = anio, mes o dia) o de campos de texto con el año
    y, si existe, el mes en español (`campo_anio`, `campo_mes`), como publica Migración Colombia. Otros parámetros:
    dominio, conjunto, campo_valor (admite conversión, «valor::number»), agregacion (sum, avg…), filtro (cláusula
    $where), escala (divisor), desde (fecha ISO) o desde_anio.
    """
    agregado = f"{p.get('agregacion', 'sum')}({p['campo_valor']}) AS valor"
    condiciones = [p['filtro']] if p.get('filtro') else []
    if p.get('campo_anio'):
        campos = [f"{p['campo_anio']} AS anio"] + ([f"{p['campo_mes']} AS mes"] if p.get('campo_mes') else [])
        consulta = {'$select': ', '.join(campos + [agregado]), '$group': ', '.join(c.split(' AS ')[1] for c in campos)}
        if p.get('desde_anio'):
            condiciones.append(f"{p['campo_anio']} >= '{p['desde_anio']}'")
    else:
        truncar = {'anio': 'date_trunc_y', 'mes': 'date_trunc_ym', 'dia': 'date_trunc_ymd'}[p.get('por', 'mes')]
        consulta = {'$select': f"{truncar}({p['campo_fecha']}) AS periodo, {agregado}", '$group': 'periodo',
                    '$order': 'periodo'}
        if p.get('desde'):
            condiciones.append(f"{p['campo_fecha']} >= '{p['desde']}'")
    if condiciones:
        consulta['$where'] = ' AND '.join(condiciones)
    consulta['$limit'] = 5000
    filas = _json(f"https://{p['dominio']}/resource/{p['conjunto']}.json?{urlencode(consulta)}")
    if not isinstance(filas, list):
        raise ErrorDeConexion(f'Respuesta inesperada de Socrata: {str(filas)[:200]}')
    escala = Decimal(str(p.get('escala', 1)))
    valores = []
    for fila in filas:
        cifra = _decimal(fila.get('valor'))
        if cifra is None:
            continue
        if p.get('campo_anio'):
            anio = int(str(fila.get('anio', ''))[:4] or 0)
            mes = MESES.get(str(fila.get('mes', '')).strip().lower()) if p.get('campo_mes') else 1
            if not anio or not mes:
                continue
            periodo, fecha = _periodo(date(anio, mes, 1), 'mes' if p.get('campo_mes') else 'anio')
        elif fila.get('periodo'):
            periodo, fecha = _periodo(_fecha(fila['periodo']), p.get('por', 'mes'))
        else:
            continue
        valores.append((periodo, fecha, cifra / escala))
    return sorted(valores, key=lambda valor: valor[1])


def csv_publicado(p):
    """Un CSV publicado en la web. Parámetros: url, columna_periodo, columna_valor, filtro ({columna: valor}),
    separador (por defecto «,»), por (anio o mes), desde_anio."""
    texto = _leer(p['url']).decode(p.get('codificacion', 'utf-8-sig'))
    lector = csv.DictReader(io.StringIO(texto), delimiter=p.get('separador', ','))
    filtro = p.get('filtro') or {}
    valores = []
    for fila in lector:
        if any((fila.get(columna) or '').strip() != str(esperado) for columna, esperado in filtro.items()):
            continue
        cifra = _decimal(fila.get(p['columna_valor'], ''))
        crudo = (fila.get(p['columna_periodo']) or '').strip()
        if cifra is None or not crudo:
            continue
        periodo, fecha = _periodo(_fecha(crudo), p.get('por', 'anio'))
        if p.get('desde_anio') and fecha.year < int(p['desde_anio']):
            continue
        valores.append((periodo, fecha, cifra))
    return valores


def focos_de_calor(p):
    """Los focos de calor que detecta el satélite VIIRS (NASA FIRMS) dentro del Carchi, contados por día.

    El archivo regional de los últimos 7 días se descarga sin clave; cada punto se ubica en su cantón con los límites
    cantonales y se cuentan los de la provincia. Los días del archivo sin focos valen cero. Parámetros: url,
    confianza_minima (low, nominal o high; por defecto se aceptan todas).
    """
    from apps.core.presentation.cantones_carchi import canton_de

    texto = _leer(p['url']).decode('utf-8')
    lector = csv.DictReader(io.StringIO(texto))
    aceptadas = {'low': ('low', 'l', 'nominal', 'n', 'high', 'h'), 'nominal': ('nominal', 'n', 'high', 'h'),
                 'high': ('high', 'h')}[p.get('confianza_minima', 'low')]
    por_dia, dias = {}, set()
    for fila in lector:
        try:
            dia = date.fromisoformat(fila['acq_date'])
            latitud, longitud = float(fila['latitude']), float(fila['longitude'])
        except (KeyError, ValueError):
            continue
        dias.add(dia)
        if (fila.get('confidence') or '').strip().lower() in aceptadas and canton_de(latitud, longitud):
            por_dia[dia] = por_dia.get(dia, 0) + 1
    if not dias:
        raise ErrorDeConexion('El archivo de FIRMS llegó sin focos ni fechas.')
    return [(dia.isoformat(), dia, Decimal(por_dia.get(dia, 0))) for dia in sorted(dias)]


TIPOS = {'socrata': socrata, 'csv': csv_publicado, 'firms': focos_de_calor}


def sincronizar(conector, guardar=True):
    """Consulta la fuente del conector y guarda lo que trae. Devuelve (nuevos, corregidos)."""
    indicador = conector.indicador
    hoy = timezone.localdate()
    parametros = conector.parametros
    territorio = parametros.get('territorio') or indicador.territorio_principal
    por = parametros.get('por') or ('mes' if parametros.get('campo_mes') or parametros.get('campo_fecha') else 'anio')
    try:
        valores = TIPOS[conector.tipo](parametros)
    except (ErrorDeConexion, KeyError) as error:
        conector.estado, conector.mensaje = 'error', str(error)[:500]
        conector.ultima_ejecucion = timezone.now()
        if guardar:
            conector.save(update_fields=['estado', 'mensaje', 'ultima_ejecucion'])
        return 0, 0
    nuevos = corregidos = 0
    with transaction.atomic():
        for periodo, fecha, cifra in valores:
            # El periodo que aún no termina puede cambiar: se publica como provisional.
            if por == 'anio':
                en_curso = fecha.year >= hoy.year
            elif por == 'mes':
                en_curso = (fecha.year, fecha.month) >= (hoy.year, hoy.month)
            else:
                en_curso = fecha >= hoy  # El día en curso todavía puede sumar focos.
            cifra = cifra.quantize(Decimal('0.0001'))
            existente = ValorIndicador.objects.filter(indicador=indicador, fecha=fecha, territorio=territorio).first()
            if existente is None:
                nuevos += 1
                if guardar:
                    ValorIndicador.objects.create(
                        indicador=indicador, periodo=periodo, fecha=fecha, territorio=territorio, valor=cifra,
                        provisional=en_curso, origen='api', nota=f'Sincronizado de {conector.get_tipo_display()}')
            elif existente.valor != cifra or existente.provisional != en_curso:
                corregidos += existente.valor != cifra
                if guardar:
                    existente.valor, existente.provisional, existente.origen = cifra, en_curso, 'api'
                    existente.save()
        if not guardar:
            transaction.set_rollback(True)
    conector.estado = 'ok'
    conector.mensaje = (f'{len(valores)} periodos consultados; {nuevos} nuevos y {corregidos} corregidos.'
                        if valores else 'La fuente respondió sin datos para este periodo.')
    conector.nuevos, conector.actualizados = nuevos, corregidos
    conector.ultima_ejecucion = timezone.now()
    if guardar:
        conector.save(update_fields=['estado', 'mensaje', 'nuevos', 'actualizados', 'ultima_ejecucion'])
    return nuevos, corregidos


def pendientes(unidad=None, todos=False):
    """Los conectores activos que toca ejecutar (o todos los activos, si se pide)."""
    conectores = ConectorIndicador.objects.filter(activo=True).select_related('indicador__unidad')
    if unidad is not None:
        conectores = conectores.filter(indicador__unidad=unidad)
    ahora = timezone.now()
    return [conector for conector in conectores if todos or conector.vencido(ahora)]
