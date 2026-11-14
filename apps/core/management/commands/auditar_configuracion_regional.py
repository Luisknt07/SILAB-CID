from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.presentation.auditoria_regional import auditar_zona_horaria


class Command(BaseCommand):
    help = "Audita el efecto de una zona candidata sobre reservas civiles, sin escrituras ni datos personales."

    def add_arguments(self, parser):
        parser.add_argument("--zona-horaria", default=settings.TIME_ZONE)
        parser.add_argument("--database", default="default")

    def handle(self, *args, **options):
        try:
            resultado = auditar_zona_horaria(options["zona_horaria"], options["database"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        for clave, cantidad in resultado.items():
            self.stdout.write(f"{clave}: {cantidad}")
        if any(v for k, v in resultado.items() if k != "reservas"):
            raise CommandError("Conciliar la agenda antes de cambiar de zona; no se modificaron datos.")
