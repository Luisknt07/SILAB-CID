"""Contrasta revision manual, codigo y conexiones; no envia ninguna señal."""
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
from pathlib import Path
import sys
import weakref

from .contratos_senales import HUELLAS_REVISION, registro_contratos
from .superficies import _sin_sql, archivo_local, senales


def huella_revision(contenido):
    # Git puede cambiar LF/CRLF; esto no requiere una revision de negocio.
    return hashlib.sha256(contenido.replace(b'\r\n', b'\n')).hexdigest()


def conexiones_modelos():
    """Lectura acotada del dispatcher Django 5.2; nunca llama send/live_receivers.

    Resuelve weakrefs, no ejecuta receivers. No publica IDs de proceso o UIDs.
    Una estructura incompatible falla el diagnostico, no se ignora.
    """
    from django.db.models import signals

    return _conexiones((nombre, getattr(signals, nombre)) for nombre in (
        'pre_init', 'post_init', 'pre_save', 'post_save', 'pre_delete',
        'post_delete', 'm2m_changed', 'class_prepared'))


def conexiones_cuentas():
    """Inspecciona autenticacion/confirmacion sin emitir señales de cuentas."""
    from allauth.account.signals import email_confirmed
    from django.contrib.auth.signals import user_logged_in

    return _conexiones((('email_confirmed', email_confirmed), ('user_logged_in', user_logged_in)))


def _conexiones(senales):
    resultado = []
    for nombre, senal in senales:
        with senal.lock:
            entradas = tuple(senal.receivers)
        for entrada in entradas:
            if len(entrada) != 3 or len(entrada[0]) != 2:
                raise ValueError('Formato de dispatcher no soportado; revisar adaptador.')
            clave, referencia, asincrona = entrada
            funcion = referencia() if isinstance(referencia, weakref.ReferenceType) else referencia
            if funcion is None:
                continue
            modulo = getattr(funcion, '__module__', '')
            if modulo == 'webcitt' or modulo.startswith(('webcitt.', 'apps.')):
                resultado.append((nombre, clave[1], funcion, asincrona))
    return resultado


def _sender(modelo):
    from django.apps import apps

    if modelo == '*':
        return None  # Registro global explicito, no cualquier sender de modelo.
    partes = modelo.split('.')
    sender = apps.get_model('.'.join(partes[:2]))
    if len(partes) == 4 and partes[3] == 'through':
        return sender._meta.get_field(partes[2]).remote_field.through
    if len(partes) != 2:
        raise ValueError('Sender de contrato no soportado.')
    return sender


def auditar_contratos_senales():
    from django.conf import settings
    from django.db import connections

    with ExitStack() as pila:
        for conexion in connections.all():
            pila.enter_context(conexion.execute_wrapper(_sin_sql))
        return _auditar(Path(settings.BASE_DIR))


def _auditar(raiz):
    contratos = registro_contratos()
    observadas = senales(raiz)
    claves = [(s['archivo'], s['funcion'], s['senal'], s['sender'] or '*') for s in observadas]
    hallazgos = []
    for clave in sorted(set(claves) - set(contratos)):
        hallazgos.append({'tipo': 'sin_contrato', 'archivo': clave[0], 'funcion': clave[1]})
    for clave in sorted(set(contratos) - set(claves)):
        hallazgos.append({'tipo': 'contrato_sin_decorador', 'archivo': clave[0], 'funcion': clave[1]})
    for clave in sorted(set(claves)):
        if claves.count(clave) != 1:
            hallazgos.append({'tipo': 'decorador_duplicado', 'archivo': clave[0], 'funcion': clave[1]})
    archivos = []
    for archivo in sorted({s['archivo'] for s in observadas} - set(HUELLAS_REVISION)):
        hallazgos.append({'tipo': 'codigo_sin_revision', 'archivo': archivo})
    for archivo, revisada in HUELLAS_REVISION.items():
        ruta = raiz / archivo
        if archivo_local(ruta, raiz) != archivo:
            raise ValueError('El inventario solo lee codigo local.')
        actual = huella_revision(ruta.read_bytes())
        archivos.append({'archivo': archivo, 'sha256_revision': revisada,
                         'sha256_actual': actual, 'revision_vigente': actual == revisada})
        if actual != revisada:
            hallazgos.append({'tipo': 'codigo_pendiente_revision', 'archivo': archivo})
    conexiones = conexiones_modelos() + conexiones_cuentas()
    cubiertas = set()
    detalle = []
    for contrato in contratos.values():
        modulo = sys.modules.get(contrato.modulo)
        funcion = vars(modulo).get(contrato.funcion) if modulo else None
        sender = _sender(contrato.modelo_sender)
        registros = [i for i, (senal, sender_id, callback, asincrona) in enumerate(conexiones)
                     if funcion is not None and callback is funcion and senal == contrato.senal
                     and sender_id == id(sender)]
        cubiertas.update(registros)
        if len(registros) != 1:
            hallazgos.append({'tipo': 'registro_ausente_o_duplicado', 'funcion': contrato.funcion,
                             'cantidad': len(registros)})
        if any(conexiones[i][3] for i in registros):
            hallazgos.append({'tipo': 'registro_asincrono_no_revisado', 'funcion': contrato.funcion})
        detalle.append({**asdict(contrato), 'registros_efectivos': len(registros)})
    for i, (senal, sender_id, callback, asincrona) in enumerate(conexiones):
        if i not in cubiertas:
            hallazgos.append({'tipo': 'conexion_sin_contrato', 'senal': senal,
                             'callback': f'{callback.__module__}.{callback.__name__}'})
    return {'version_contrato': 1, 'alcance': 'revision_de_senales_heredadas_no_aislamiento',
            'no_consulta_datos': True, 'no_ejecuta_receivers': True,
            'contratos': detalle, 'archivos_revisados': archivos, 'hallazgos': hallazgos,
            'resumen': {'contratos': len(contratos), 'decoradores': len(observadas),
                        'conexiones_propias': len(conexiones), 'hallazgos': len(hallazgos),
                        'fallos_descartados': sum(c.fallo == 'descarta_excepcion' for c in contratos.values()),
                        'fallos_no_bloqueantes_observables': sum(
                            c.fallo == 'registra_fallo_no_bloqueante' for c in contratos.values())}}
