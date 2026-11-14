"""2.3 · Los simuladores de producción de un centro experimental: cuánta leche, cuánta cosecha, cuántos huevos y cuánto
café tostado se puede esperar, con los rendimientos publicados como valor de partida.

Cada simulador declara sus datos con su valor de partida y de dónde sale; quien lo usa los cambia por los suyos. Un
valor sin fuente sólida (la postura de las gallinas) se dice así. Los cálculos son del servidor, como los simuladores
de las plantas piloto: la página funciona sin JavaScript y cada resultado se puede comprobar.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.directorio_unidades.presentation.catalogos_publicos import _contexto
from apps.centros_experimentales.operacion.presentation.centro_experimental import _centro, ejes_publicados


@dataclass(frozen=True)
class Dato:
    campo: str
    nombre: str
    valor: Decimal
    paso: str = '1'
    fuente: str = ''
    minimo: Decimal = Decimal('0')
    maximo: Decimal = None


# Rendimientos con fuente para el simulador de cosecha: «clave, cultivo, t/ha, fuente».
RENDIMIENTOS = (
    ('mora', 'Mora de Castilla, manejo tecnificado', Decimal('14'), 'INIAP, El cultivo de la mora en el Ecuador'),
    ('andimora', 'Mora INIAP Andimora 2013', Decimal('18'), 'INIAP, ficha técnica de la variedad Andimora 2013'),
    ('tomate-arbol', 'Tomate de árbol', Decimal('15.2'), 'Agronomía Mesoamericana 31(1), 2020'),
    ('uvilla', 'Uvilla bajo invernadero (Alonso Tadeo)', Decimal('10.05'), 'Ensayo del centro, DOI 10.32645/26028131.1029'),
)
CENICAFE = 'Cenicafé, Avance Técnico 370 (2008)'


def _numero(texto, dato):
    """El valor que escribió quien simula, dentro de sus límites; el de partida si no sirve."""
    try:
        valor = Decimal(str(texto).replace(',', '.'))
    except (InvalidOperation, TypeError):
        return dato.valor
    if not valor.is_finite() or valor < dato.minimo or (dato.maximo is not None and valor > dato.maximo):
        return dato.valor
    return valor


def _leche(v):
    diario = v['vacas'] * v['litros']
    periodo = diario * v['dias']
    planta = periodo * v['planta'] / 100
    return [('Leche al día', diario, 'L'), ('Leche en el periodo', periodo, 'L'),
            ('A la planta piloto de lácteos', planta, 'L'), ('Para prácticas, terneras y consumo', periodo - planta, 'L')]


def _cosecha(v, rendimiento):
    bruta = v['superficie'] * rendimiento * 1000
    perdida = bruta * v['perdida'] / 100
    semanas = v['semanas'] or Decimal('1')
    return [('Cosecha esperada', bruta, 'kg'), ('Pérdida en poscosecha', perdida, 'kg'),
            ('Fruta que llega a su destino', bruta - perdida, 'kg'), ('Por semana de cosecha', (bruta - perdida) / semanas,
                                                                     'kg')]


def _postura(v):
    diarios = v['gallinas'] * v['postura'] / 100
    periodo = diarios * v['dias']
    return [('Huevos al día', diarios, 'huevos'), ('Huevos en el periodo', periodo, 'huevos'),
            ('Cubetas de 30', periodo / 30, 'cubetas')]


def _cafe(v):
    pergamino = v['cereza'] * Decimal('0.20')
    verde = pergamino * Decimal('0.80')
    tostado = verde * (100 - v['merma']) / 100
    return [('Café pergamino seco', pergamino, 'kg'), ('Café verde (almendra)', verde, 'kg'),
            ('Café tostado', tostado, 'kg')]


SIMULADORES = (
    {
        'clave': 'leche', 'nombre': 'Producción de leche', 'icono': 'fas fa-tint', 'ejes': ('leche',),
        'pregunta': '¿Cuánta leche produce el hato y cuánta llega a la planta de lácteos?',
        'datos': (Dato('vacas', 'Vacas en ordeño', Decimal('20'), fuente='Valor de ejemplo: pon las del centro'),
                  Dato('litros', 'Litros por vaca al día', Decimal('7.9'), '0.1', 'ESPAC 2024, promedio de la Sierra'),
                  Dato('dias', 'Días del periodo', Decimal('30'), maximo=Decimal('366')),
                  Dato('planta', 'Porcentaje que va a la planta', Decimal('80'), maximo=Decimal('100'),
                       fuente='Lo decide la administración del centro')),
        'calcular': _leche,
    },
    {
        'clave': 'cosecha', 'nombre': 'Cosecha esperada', 'icono': 'fas fa-apple-alt',
        'ejes': ('frutales-altura', 'invernaderos', 'citricos-frutales'),
        'pregunta': '¿Cuánto debería cosechar un lote según su superficie y el rendimiento de referencia?',
        'datos': (Dato('superficie', 'Superficie (ha)', Decimal('0.5'), '0.01'),
                  Dato('perdida', 'Pérdida en poscosecha (%)', Decimal('10'), maximo=Decimal('100'),
                       fuente='Valor de partida: mídelo en el centro'),
                  Dato('semanas', 'Semanas de cosecha', Decimal('20'), maximo=Decimal('52'))),
        # Su rendimiento lo elige quien simula entre los de RENDIMIENTOS.
    },
    {
        'clave': 'postura', 'nombre': 'Postura de las gallinas', 'icono': 'fas fa-egg', 'ejes': ('gallinas',),
        'pregunta': '¿Cuántos huevos se recogen al día y en el mes?',
        'datos': (Dato('gallinas', 'Gallinas en postura', Decimal('100'), fuente='El centro tiene más de 100'),
                  Dato('postura', 'Postura (%)', Decimal('80'), maximo=Decimal('100'),
                       fuente='Sin fuente sólida: valor de partida editable; regístralo con la postura real'),
                  Dato('dias', 'Días del periodo', Decimal('30'), maximo=Decimal('366'))),
        'calcular': _postura,
    },
    {
        'clave': 'cafe', 'nombre': 'Del café cereza al café tostado', 'icono': 'fas fa-coffee', 'ejes': ('cafe',),
        'pregunta': '¿Cuánto café pergamino, verde y tostado sale de una cosecha de cereza?',
        'datos': (Dato('cereza', 'Café cereza cosechado (kg)', Decimal('100'), '0.1'),
                  Dato('merma', 'Pérdida de peso en el tueste (%)', Decimal('15.5'), '0.1', maximo=Decimal('30'),
                       fuente='Cenicafé: tueste medio, 15 a 16 %')),
        'calcular': _cafe,
        'nota': f'De cereza a pergamino seco ×0,20 y de pergamino a verde ×0,80 ({CENICAFE}).',
    },
)


def simuladores_de(unidad):
    """Los simuladores que aplican a los ejes publicados del centro."""
    codigos = {eje.codigo for eje in ejes_publicados(unidad)}
    return [simulador for simulador in SIMULADORES if codigos & set(simulador['ejes'])]


def resolver(simulador, parametros):
    """Los datos del simulador con lo que escribió quien simula, y su resultado."""
    prefijo = simulador['clave']
    datos = [{'dato': dato, 'nombre': f'{prefijo}-{dato.campo}', 'valor': _numero(parametros.get(f'{prefijo}-{dato.campo}'), dato)}
             for dato in simulador['datos']]
    valores = {fila['dato'].campo: fila['valor'] for fila in datos}
    extra = {}
    if simulador['clave'] == 'cosecha':
        elegido = next((fila for fila in RENDIMIENTOS if fila[0] == parametros.get('cosecha-cultivo')), RENDIMIENTOS[0])
        extra = {'cultivos': RENDIMIENTOS, 'cultivo': elegido}
        resultado = _cosecha(valores, elegido[2])
    else:
        resultado = simulador['calcular'](valores)
    return {**simulador, 'datos': datos, 'resultado': resultado, **extra}


@xframe_options_sameorigin
def simuladores_view(request, slug):
    """2.3 · Los simuladores del centro, cada uno con sus datos de partida, su fuente y su resultado."""
    unidad = _centro(slug)
    return render(request, 'portal/pages/unidades/centro/simuladores.html', {
        **_contexto(unidad, 'simuladores_campo', request.user),
        'simuladores': [resolver(simulador, request.GET) for simulador in simuladores_de(unidad)],
    })
