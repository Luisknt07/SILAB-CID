import json
from django.core.management.base import BaseCommand, CommandError
from apps.integraciones.concordancia_reglamento import diagnosticar


class Command(BaseCommand):
    help = "Diagnóstico de adscripciones, responsables y capacidades de Laboratorios y Centros; solo lectura."

    def add_arguments(self, parser):
        parser.add_argument(
            "--estricto",
            action="store_true",
            help="Finaliza con error si faltan asignaciones o hay identidades repetidas.",
        )

    def handle(self, *args, **options):
        datos = diagnosticar()
        self.stdout.write(json.dumps(datos, ensure_ascii=False, indent=2))
        claves = (
            'sin_designacion_institucional',
            'adscripciones_sin_validador_designado',
            'centros_sin_designacion_concordante',
            'codigos_coincidentes_entre_inventarios',
            'capacidades_compartidas_no_resueltas',
            "sin_adscripcion",
            "adscripcion_sin_receptor",
            "sin_coordinacion_con_cuenta",
            "centros_sin_responsable",
            "laboratorios_propios_repetidos",
            "areas_propio_y_compartido_a_la_vez",
            "codigos_individuales_repetidos",
            "laboratorios_propios_no_resueltos",
        )
        if options["estricto"] and any(datos[k] for k in claves):
            raise CommandError(
                "Existen asignaciones pendientes o identidades de capacidad por revisar. No se modificaron datos."
            )
