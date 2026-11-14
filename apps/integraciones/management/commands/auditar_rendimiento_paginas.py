"""Mide páginas públicas bajo una transacción PostgreSQL de solo lectura."""
from contextlib import ExitStack

import json
import re
import statistics
import sys
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections, transaction
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse


RUTAS_PREDETERMINADAS = ('home', 'quienes_somos', 'servicios_portal', 'normativa', 'centros_id', 'laboratorios_unidades')


def validar_ruta(ruta):
    partes = urlsplit(ruta)
    if not ruta.startswith('/') or ruta.startswith('//') or partes.scheme or partes.netloc or partes.fragment:
        raise CommandError('Use rutas locales que comiencen con /, sin dominio ni fragmento.')
    return ruta


class Command(BaseCommand):
    help = 'Audita consultas/tiempos de páginas públicas sin permitir escrituras SQL. No sustituye una prueba de carga.'

    def add_arguments(self, parser):
        parser.add_argument('--ruta', action='append', help='Ruta pública local; puede repetirse. No ejecuta POST.')
        parser.add_argument('--repeticiones', type=int, default=3)
        parser.add_argument('--max-consultas', type=int)
        parser.add_argument('--json', dest='salida_json')

    def handle(self, *args, **opciones):
        aliases = ('default', 'centros') if getattr(settings, 'CENTROS_DB_ENABLED', False) else ('default',)
        if any(connections[alias].vendor != 'postgresql' for alias in aliases):
            raise CommandError('Esta auditoría requiere PostgreSQL para garantizar READ ONLY.')
        repeticiones = opciones['repeticiones']
        if not 1 <= repeticiones <= 10:
            raise CommandError('Use entre 1 y 10 repeticiones.')
        limite = opciones.get('max_consultas')
        if limite is not None and limite < 0:
            raise CommandError('El límite de consultas no puede ser negativo.')
        rutas = [validar_ruta(r) for r in (opciones.get('ruta') or [reverse(n) for n in RUTAS_PREDETERMINADAS])]
        resultados = []
        # El cliente es interno: no realiza solicitudes de red, no inicia sesión
        # ni lee registros personales. READ ONLY bloquea también writes en GET.
        with override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False):
            for ruta in rutas:
                muestras = []
                for _ in range(repeticiones):
                    inicio = perf_counter()
                    try:
                        with ExitStack() as transacciones:
                            for alias in aliases:
                                transacciones.enter_context(transaction.atomic(using=alias))
                                with connections[alias].cursor() as cursor:
                                    cursor.execute('SET TRANSACTION READ ONLY')
                            with ExitStack() as capturas:
                                por_base = {alias: capturas.enter_context(CaptureQueriesContext(connections[alias]))
                                            for alias in aliases}
                                respuesta = Client().get(ruta)
                            consultas = [q for captura in por_base.values() for q in captura]
                            muestra = {
                                'estado': respuesta.status_code, 'consultas': len(consultas),
                                'por_base': {alias: len(captura) for alias, captura in por_base.items()},
                                'ms': round((perf_counter() - inicio) * 1000, 2),
                                'bytes_html': None if respuesta.streaming else len(respuesta.content),
                                'tablas': sorted(set(m.group(1) for q in consultas for m in re.finditer(r'(?:FROM|JOIN) "([^"]+)"', q['sql']))),
                            }
                            # No conserva modificaciones de este contexto; el motor
                            # rechaza las escrituras en tablas persistentes.
                            for alias in aliases:
                                transaction.set_rollback(True, using=alias)
                        muestras.append(muestra)
                    except Exception as error:
                        # No volcar SQL, mensajes de conexión ni identificadores.
                        muestras.append({'error': type(error).__name__})
                buenas = [m for m in muestras if 'error' not in m]
                resultado = {'ruta': ruta, 'muestras': muestras}
                if buenas:
                    resultado.update(ms_mediana=round(statistics.median(m['ms'] for m in buenas), 2),
                                     consultas_max=max(m['consultas'] for m in buenas))
                resultados.append(resultado)
        informe = {
            'solo_lectura': True, 'perfil': 'anónimo, cliente Django local; sin red, TLS ni descarga de recursos',
            'repeticiones': repeticiones, 'resultados': resultados,
            'modulos_negocio_importados': len([m for m in sys.modules if m.startswith('apps.gestion_unidades.')]),
        }
        contenido = json.dumps(informe, ensure_ascii=False, indent=2)
        if opciones.get('salida_json'):
            salida = Path(opciones['salida_json'])
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_text(contenido + '\n', encoding='utf-8')
        self.stdout.write(contenido)
        errores = any('error' in m or m.get('estado') != 200 for r in resultados for m in r['muestras'])
        if errores:
            raise CommandError('Una ruta no respondió 200 o intentó una operación incompatible con solo lectura. Revise el informe.')
        if limite is not None and any(r.get('consultas_max', 0) > limite for r in resultados):
            raise CommandError('Se superó el presupuesto de consultas.')
