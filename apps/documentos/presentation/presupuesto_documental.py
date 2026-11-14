"""Reglas compartidas del presupuesto declarado, sin autorizar adquisiciones."""
import re
from decimal import Decimal, DecimalException, InvalidOperation
from html import unescape

from django.utils.html import strip_tags


CATEGORIAS_INVERSION = (
    ('equipos', 'Equipos'), ('software', 'Software y licencias'), ('insumos', 'Insumos y materiales'),
    ('mobiliario', 'Mobiliario e infraestructura'), ('mantenimiento', 'Mantenimiento'),
    ('capacitacion', 'Capacitación'), ('otro', 'Otro'),
)
PRIORIDADES = (('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja'))
FUENTES_FINANCIAMIENTO = (
    ('institucional', 'Presupuesto institucional'), ('proyecto', 'Proyecto de investigación o vinculación'),
    ('autogestion', 'Autogestión de la unidad'), ('donacion', 'Donación o cooperación'), ('otro', 'Otra'),
)

_ETIQUETAS = dict(categoria='categoría', item='ítem', cantidad='cantidad', justificacion='justificación',
    prioridad='prioridad', costo_unitario='costo unitario', fuente='fuente de financiamiento', trimestre='trimestre')


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def _fila_inicial(fila):
    """El selector inicial de categoría no constituye una adquisición declarada."""
    return (not _texto(fila.get('categoria')) or _texto(fila.get('categoria')) == 'equipos') and not any(
        _texto(valor) for clave, valor in fila.items() if clave != 'categoria')


def analizar_presupuesto(tipo, contenido, *, unidad=None):
    """Lee filas significativas y faltantes sin cambiar la redacción guardada.

    ``completo`` exige filas válidas o una justificación de que no se proyectan
    compras. Los hallazgos de revisión, como una necesidad repetida, se conservan
    sin impedir por sí solos la conformidad documental.
    """
    if tipo not in ('planificacion', 'compras'):
        return dict(hallazgos=[], total=Decimal(0), filas=[], completo=True)
    contenido = contenido if isinstance(contenido, dict) else {}
    if tipo == 'planificacion' and contenido.get('recursos_periodo_version') == 1:
        # El semestre revisa cobertura; la solicitud cuantificada pertenece al anual.
        return dict(hallazgos=[], total=Decimal(0), filas=[], completo=True)
    tabla = 'inversion' if tipo == 'planificacion' else 'compras'
    justificacion = 'sin_inversion_justificacion' if tipo == 'planificacion' else 'sin_compras_justificacion'
    seccion = 'Presupuesto del período' if tipo == 'planificacion' else 'Compras del año'
    hallazgos, filas, vistos, total = [], [], set(), Decimal(0)

    def falta(regla, mensaje, severidad='bloqueo'):
        hallazgos.append(dict(regla=regla, mensaje=mensaje, severidad=severidad))

    guardadas = contenido.get(tabla)
    if guardadas is None:
        guardadas = []
    if not isinstance(guardadas, list):
        falta('presupuesto_invalido', f'{seccion}: la tabla no tiene una estructura válida. Revísala en el editor.')
        return dict(hallazgos=hallazgos, total=total, filas=filas, completo=False)
    for posicion, fila in enumerate(guardadas, 1):
        if not isinstance(fila, dict):
            falta('presupuesto_invalido', f'{seccion}, ítem {posicion}: la fila no tiene una estructura válida.')
            continue
        if _fila_inicial(fila):
            continue
        filas.append(fila)
        indice = len(filas)
        referencia = f'{seccion}, ítem {indice}'
        pac = tipo == 'compras' and contenido.get('pac_version') in (1, 2)
        campos = (['item', 'cantidad', 'justificacion', 'costo_unitario'] if pac else
                  ['categoria', 'item', 'cantidad', 'justificacion', 'prioridad', 'costo_unitario', 'fuente'])
        if tipo == 'compras' and not pac:
            campos.append('trimestre')
        vacios = [c for c in campos if not _texto(fila.get(c))]
        if vacios:
            falta('compra_incompleta', f'{referencia}: completa {", ".join(_ETIQUETAS[c] for c in vacios)}.')
        catalogos = dict(categoria=CATEGORIAS_INVERSION, prioridad=PRIORIDADES, fuente=FUENTES_FINANCIAMIENTO)
        invalidos = [c for c, opciones in catalogos.items()
                     if _texto(fila.get(c)) and _texto(fila.get(c)) not in dict(opciones)]
        if invalidos:
            falta('clasificacion_compra_invalida',
                f'{referencia}: selecciona {", ".join(_ETIQUETAS[c] for c in invalidos)} del catálogo.')
        valores, importes_invalidos = {}, []
        for campo in ('cantidad', 'costo_unitario'):
            texto = _texto(fila.get(campo)).replace(',', '.')
            if not texto:
                continue
            try:
                if len(texto) > 32:
                    raise InvalidOperation
                valor = Decimal(texto)
                if (not valor.is_finite() or valor > Decimal('1e12')
                        or (valor <= 0 if campo == 'cantidad' else valor < 0)):
                    raise InvalidOperation
                valores[campo] = valor
            except (DecimalException, ValueError):
                importes_invalidos.append(campo)
        if importes_invalidos:
            falta('importe_invalido', f'{referencia}: revisa {", ".join(_ETIQUETAS[c] for c in importes_invalidos)}; '
                'la cantidad debe ser positiva y el costo no negativo, con valores finitos de hasta 1 000 000 000 000.')
        if len(valores) == 2:
            importe = valores['cantidad'] * valores['costo_unitario']
            if tipo == 'compras' and contenido.get('compras_resumen_version') == 1:
                from decimal import ROUND_HALF_UP
                importe = importe.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total += importe
        clave = re.sub(r'\s+', ' ', _texto(fila.get('item')).casefold())
        if clave and contenido.get('pac_version') == 2:
            clave = (clave, _texto(fila.get('area_id')), _texto(fila.get('mes_compra')))
        if clave and clave in vistos:
            falta('compra_duplicada', f'{referencia}: revisa la necesidad repetida antes de consolidar el presupuesto.', 'revision')
        vistos.add(clave)
        trimestre = _texto(fila.get('trimestre'))
        if tipo == 'compras' and trimestre and trimestre not in ('1', '2', '3', '4'):
            falta('trimestre_invalido', f'{referencia}: selecciona un trimestre del año planificado.')
    if not filas and not hallazgos and not unescape(strip_tags(_texto(contenido.get(justificacion)))).strip():
        falta('apartados_incompletos', f'{seccion}: añade las adquisiciones previstas o justifica por qué la unidad no requiere compras.')
    if tipo == 'compras' and contenido.get('pac_version') in (1, 2):
        from .pac_universitario import validar_pac
        hallazgos.extend(validar_pac(contenido, unidad=unidad))
    return dict(hallazgos=hallazgos, total=total, filas=filas,
                completo=not any(h['severidad'] == 'bloqueo' for h in hallazgos))
