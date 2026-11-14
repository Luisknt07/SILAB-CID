"""Actualiza los indicadores de los observatorios desde sus fuentes con API pública.

Ejecuta los conectores que ya cumplieron su frecuencia (o todos con `--todos`). Con `--continuo` queda atendiendo
como servicio y revisa cada `--intervalo` segundos, igual que el servicio que atiende navegadores y microproyectos.
`--simular` consulta las fuentes y cuenta lo que cambiaría sin guardar nada.
"""
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.observatorios.operacion.presentation.conectores_observatorio import pendientes, sincronizar
from apps.directorio_unidades.models.core import Unidad


class Command(BaseCommand):
    help = 'Actualiza los indicadores de los observatorios desde sus fuentes con API pública.'

    def add_arguments(self, parser):
        parser.add_argument('--observatorio', help='Solo este observatorio (su slug).')
        parser.add_argument('--todos', action='store_true', help='Ejecuta todos los conectores, aunque no les toque.')
        parser.add_argument('--simular', action='store_true', help='Consulta y cuenta sin guardar.')
        parser.add_argument('--continuo', action='store_true', help='Queda atendiendo como servicio.')
        parser.add_argument('--intervalo', type=int, default=3600, help='Segundos entre revisiones en modo continuo.')

    def handle(self, *args, **opciones):
        unidad = None
        if opciones['observatorio']:
            unidad = Unidad.objects.filter(slug=opciones['observatorio'], dependencia='observatorios').first()
            if unidad is None:
                self.stderr.write(f"No existe el observatorio {opciones['observatorio']}.")
                return
        while True:
            close_old_connections()
            self.ronda(unidad, opciones['todos'], not opciones['simular'])
            if not opciones['continuo']:
                return
            time.sleep(opciones['intervalo'])

    def ronda(self, unidad, todos, guardar):
        conectores = pendientes(unidad, todos)
        if not conectores:
            self.stdout.write('Ningún conector pendiente.')
        for conector in conectores:
            nuevos, corregidos = sincronizar(conector, guardar=guardar)
            estilo = self.style.SUCCESS if conector.estado == 'ok' else self.style.ERROR
            prefijo = '[simulación] ' if not guardar else ''
            self.stdout.write(estilo(f'{prefijo}{conector.indicador.unidad.nombre_corto or conector.indicador.unidad}'
                                     f' · {conector.indicador.nombre}: {conector.mensaje}'))
