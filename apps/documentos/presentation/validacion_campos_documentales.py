"""Integridad de los campos del editor, sin generar archivos ni modificar datos.

Las tablas opcionales pueden omitirse. Cuando la unidad declara una fila, sus
datos deben ser completos y válidos antes de emitir o enviar el documento.
Las reglas de presupuesto y de actividades tienen sus propios analizadores.
"""
from decimal import Decimal, DecimalException

from apps.reservas.presentation.guia_html import esta_vacio, sanear


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def _valor_simple(valor):
    return not isinstance(valor, (dict, list, tuple, set, bool))


def _numero_no_negativo(valor):
    if not _valor_simple(valor):
        return False
    try:
        numero = Decimal(_texto(valor).replace(',', '.'))
        return numero.is_finite() and numero >= 0
    except (DecimalException, ValueError):
        return False


def _html(valor):
    # Los primeros borradores guardaban párrafos o viñetas como listas de texto.
    if isinstance(valor, (list, tuple)):
        if not all(isinstance(v, str) for v in valor):
            return None
        return '\n'.join(valor)
    return valor if isinstance(valor, str) else None


def _columnas_exigidas(tipo, campo, fila):
    columnas = campo.columnas
    if tipo == 'informe' and campo.clave == 'ejecucion_presupuestal':
        return [c for c in columnas if c[0] != 'observacion']
    if (tipo == 'protocolo' and fila.get('aplica') == 'no'
            and campo.clave in ('riesgos_protocolo', 'emergencias_protocolo')):
        return [c for c in columnas if c[0] in ('aplica', 'actividad', 'situacion', 'control', 'respuesta')]
    return columnas


def validar_campos(tipo, contenido, secciones):
    """Hallazgos con ``seccion``, ``clave``, ``mensaje`` y ``severidad``.

    ``secciones`` usa las definiciones del editor, para compartir etiquetas y
    opciones sin importar ese módulo ni acceder a la base de datos. No cambia
    el contenido, incluso al ignorar una fila completamente vacía del editor.
    """
    hallazgos = []
    if not isinstance(contenido, dict):
        return [dict(seccion='documento', clave='contenido', severidad='bloqueo',
                     mensaje='El contenido del documento no tiene una estructura válida. Revísalo en el editor.')]

    for seccion in secciones:
        for campo in seccion.campos:
            valor = contenido.get(campo.clave)
            referencia = f'{seccion.titulo} → {campo.etiqueta}'

            def falta(mensaje):
                hallazgos.append(dict(seccion=seccion.codigo, clave=campo.clave,
                                     mensaje=f'{referencia}: {mensaje}', severidad='bloqueo'))

            if campo.tipo == 'tabla':
                # Las compras incluyen una alternativa sin adquisiciones y se
                # comprueban con analizar_presupuesto, compartido por el flujo.
                if campo.clave in ('inversion', 'compras'):
                    continue
                if valor is None or valor == []:
                    if campo.requerido:
                        falta('completa al menos una fila.')
                    continue
                if not isinstance(valor, list):
                    falta('la tabla no tiene una estructura válida. Revísala en el editor.')
                    continue
                filas = []
                for posicion, fila in enumerate(valor, 1):
                    if not isinstance(fila, dict):
                        falta(f'la fila {posicion} no tiene una estructura válida.')
                    elif any(_texto(fila.get(c[0])) for c in campo.columnas):
                        filas.append((posicion, fila))
                if not filas:
                    if campo.requerido:
                        falta('completa al menos una fila.')
                    continue
                if tipo == 'protocolo':
                    from .protocolo_seguridad import campo_completo
                    if campo_completo(campo, [f for _p, f in filas]):
                        continue
                for posicion, fila in filas:
                    columnas = _columnas_exigidas(tipo, campo, fila)
                    vacias = [etiqueta for clave, etiqueta, _t, _o in columnas
                              if not _texto(fila.get(clave))]
                    if vacias:
                        falta(f'fila {posicion}, completa {", ".join(vacias)}.')
                    invalidas = [etiqueta for clave, etiqueta, _t, _o in columnas
                                 if not _valor_simple(fila.get(clave))]
                    if invalidas:
                        falta(f'fila {posicion}, revisa el formato de {", ".join(invalidas)}.')
                    opciones_invalidas = [etiqueta for clave, etiqueta, t, opciones in columnas
                        if t == 'opcion' and _texto(fila.get(clave))
                        and (not _valor_simple(fila.get(clave)) or fila[clave] not in dict(opciones))]
                    if opciones_invalidas:
                        falta(f'fila {posicion}, selecciona {", ".join(opciones_invalidas)} del catálogo.')
                    numeros_invalidos = [etiqueta for clave, etiqueta, t, _o in columnas
                        if t == 'numero' and _texto(fila.get(clave)) and not _numero_no_negativo(fila[clave])]
                    if numeros_invalidos:
                        falta(f'fila {posicion}, {", ".join(numeros_invalidos)} debe ser un número finito no negativo.')
                continue

            if campo.tipo == 'rico':
                html = _html(valor) if valor is not None else ''
                if html is None:
                    falta('el texto no tiene una estructura válida.')
                elif campo.requerido and esta_vacio(sanear(html, 'tablas')[0]):
                    falta('completa este apartado.')
                continue
            if campo.tipo == 'opcion':
                if not _texto(valor):
                    if campo.requerido:
                        falta('selecciona una opción.')
                elif not _valor_simple(valor) or valor not in dict(campo.opciones):
                    falta('selecciona una opción del catálogo.')
                continue
            if campo.tipo == 'marcas':
                if valor is None or valor == []:
                    if campo.requerido:
                        falta('selecciona al menos una opción.')
                elif (not isinstance(valor, (list, tuple)) or
                      any(not _valor_simple(v) or v not in dict(campo.opciones) for v in valor)):
                    falta('selecciona únicamente opciones del catálogo.')
                continue
            if campo.tipo == 'actividades':
                if not isinstance(valor, dict):
                    if campo.requerido or valor is not None:
                        falta('revisa las actividades del período en el editor.')
                    continue
                catalogo, otras = valor.get('catalogo') or {}, valor.get('otras') or []
                if (not isinstance(catalogo, dict) or not all(isinstance(v, dict) for v in catalogo.values())
                        or not isinstance(otras, list) or not all(isinstance(v, dict) for v in otras)):
                    falta('las actividades no tienen una estructura válida.')
                elif campo.requerido and not (any(v.get('aplica') for v in catalogo.values()) or otras):
                    falta('define las actividades del período.')
                continue
            if campo.tipo in ('cumplimiento', 'presupuesto_uso'):
                if valor is not None and not isinstance(valor, dict):
                    falta('los datos no tienen una estructura válida.')
                continue
            if not _valor_simple(valor):
                falta('el texto no tiene una estructura válida.')
            elif campo.requerido and not _texto(valor):
                falta('completa este apartado.')
    firmas = next((s for s in secciones if s.codigo == 'firmas'), None)
    if firmas and any(c.clave == 'revisa_nombre' for c in firmas.campos):
        nombre, cargo = _texto(contenido.get('revisa_nombre')), _texto(contenido.get('revisa_cargo'))
        if bool(nombre) != bool(cargo):
            hallazgos.append(dict(seccion='firmas', clave='revisa_nombre' if not nombre else 'revisa_cargo',
                mensaje='Firmas de responsabilidad: completa el nombre y el cargo de quien revisa, '
                        'o deja ambos vacíos si no corresponde.', severidad='bloqueo'))
    return hallazgos
