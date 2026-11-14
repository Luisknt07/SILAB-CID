"""Expone el inventario como JSON para compararlo antes y despues de migrar."""

import json

from django.core.management.base import BaseCommand

from apps.integraciones.inventario import inventario_del_proyecto


class Command(BaseCommand):
    help = "Inventaria rutas, tablas, permisos, admin, plantillas, estaticos y tareas sin leer datos."

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(inventario_del_proyecto(), ensure_ascii=False, indent=2)
        )
