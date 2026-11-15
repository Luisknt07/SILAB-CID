"""Barreras comunes para comandos que instalan datos demostrativos."""

from django.conf import settings
from django.core.management.base import CommandError


def exigir_entorno_datos_demo():
    """Barrera mínima para comandos con otra forma de acotar su alcance."""
    if not getattr(settings, "ALLOW_DEMO_DATA_COMMANDS", False):
        raise CommandError(
            "Los cargadores demostrativos están deshabilitados en este entorno."
        )


class ComandoDatosDemostrativosMixin:
    """Exige entorno, alcance y confirmación antes de crear datos ficticios."""

    def agregar_argumentos_datos_demo(self, parser):
        parser.add_argument(
            "--unidad",
            help="Slug obligatorio de la unidad de demostración.",
        )
        parser.add_argument(
            "--confirmar-datos-demo",
            action="store_true",
            help="Confirma que se instalarán datos ficticios en la unidad indicada.",
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Ejecuta todas las validaciones y revierte la transacción al terminar.",
        )

    def validar_opciones_datos_demo(self, options):
        exigir_entorno_datos_demo()
        slug = (options.get("unidad") or "").strip()
        if not slug:
            raise CommandError("Indica --unidad para acotar los datos demostrativos.")
        if not options.get("confirmar_datos_demo"):
            raise CommandError(
                "Añade --confirmar-datos-demo para autorizar esta carga ficticia."
            )
        return slug

    @staticmethod
    def finalizar_simulacion_datos_demo(options):
        if options.get("simular"):
            from django.db import transaction

            transaction.set_rollback(True)

    @staticmethod
    def prefijo_simulacion_datos_demo(options):
        return "SIMULACIÓN: " if options.get("simular") else ""
