from django.core.management.base import BaseCommand, CommandError

from apps.reservas.presentation.mantenimiento import sincronizar_planificaciones_unidad
from apps.reservas.presentation.capacidad import comando_reservas
from apps.directorio_unidades.models.core import Unidad


class Command(BaseCommand):
    help = (
        "Genera de forma idempotente la planificación FT02 de las reservas de "
        "recursos existentes. Las solicitudes de servicio conservan su orden propia."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--unidad",
            help="Slug obligatorio de la unidad que se reconciliará.",
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Calcula el resultado y revierte la transacción al terminar.",
        )

    @comando_reservas
    def handle(self, *args, **options):
        slug = (options.get("unidad") or "").strip()
        if not slug:
            raise CommandError("Indica --unidad para acotar la reconciliación.")
        try:
            resultado = sincronizar_planificaciones_unidad(
                unidad_slug=slug,
                simular=options["simular"],
            )
        except Unidad.DoesNotExist as error:
            raise CommandError(f'No existe una unidad con slug "{slug}".') from error

        prefijo = "SIMULACIÓN: " if options["simular"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefijo}{resultado.creadas} planificación(es) creadas, "
                f"{resultado.actualizadas} actualizadas y "
                f"{resultado.omitidas} sin cambios."
            )
        )
