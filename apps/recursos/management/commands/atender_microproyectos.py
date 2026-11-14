"""Servicio de puesta en marcha: el único proceso con acceso a Docker; no recibe tráfico web."""
import threading
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.recursos.presentation.despliegue_microproyectos import atender_siguiente, retirar_huerfanos
from apps.recursos.presentation.navegador_remoto import atender_sesiones


class Command(BaseCommand):
    help = ('Atiende las puestas en marcha de microproyectos Django y las sesiones de navegador remoto; '
            'retira lo que dejó de publicarse o de usarse.')

    def add_arguments(self, parser):
        parser.add_argument('--una-vez', action='store_true', help='Atiende las colas una vez y termina.')
        parser.add_argument('--intervalo', type=int, default=5, help='Segundos entre revisiones de las colas.')

    def handle(self, *args, **opciones):
        if opciones['una_vez']:
            self.navegadores()
            self.microproyectos()
            return
        # Una construcción larga no debe hacer esperar a quien abre un sitio.
        threading.Thread(target=self.repetir, args=(self.navegadores, 2), daemon=True).start()
        self.repetir(self.microproyectos, opciones['intervalo'])

    def repetir(self, tarea, intervalo):
        while True:
            close_old_connections()
            try:
                tarea()
            except Exception as exc:  # noqa: BLE001 - Docker o la base caídos no detienen el servicio.
                self.stderr.write(f'No se pudo revisar la cola: {exc}')
            time.sleep(intervalo)

    def microproyectos(self):
        for retirado in retirar_huerfanos():
            self.stdout.write(f'Contenedor {retirado} retirado.')
        while despliegue := atender_siguiente():
            estilo = self.style.SUCCESS if despliegue.estado == 'completado' else self.style.ERROR
            self.stdout.write(estilo(f'Microproyecto {despliegue.recurso_id}: {despliegue.get_estado_display()}. '
                                     f'{despliegue.detalle}'))

    def navegadores(self):
        for sesion in atender_sesiones():
            self.stdout.write(f'Navegador remoto para «{sesion.recurso}»: {sesion.get_estado_display()}. '
                              f'{sesion.detalle}')
