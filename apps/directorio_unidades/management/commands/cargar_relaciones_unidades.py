"""Registra cómo se relacionan las unidades: los centros alojan plantas y les proveen materia prima, los laboratorios
analizan sus muestras y los observatorios siguen su producción con datos.

Es idempotente: crea lo que falta y no pisa lo que la unidad ajustó, salvo con --reescribir. Una unidad que todavía
no existe se omite con aviso (correr antes reorganizar_unidades).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.directorio_unidades.models.relaciones import RelacionUnidad
from apps.directorio_unidades.models.core import Unidad

SF, AT = 'centro-experimental-san-francisco', 'centro-experimental-alonso-tadeo'
LACTEOS, CARNICOS, FRUTAS = 'planta-piloto-lacteos', 'planta-piloto-carnicos', 'planta-piloto-frutas-vegetales'
CEREALES, ALMIDON = 'planta-piloto-cereales', 'planta-extraccion-almidon-biotecnologia'
CAFE, CITRICOS = 'planta-piloto-cafe', 'planta-piloto-citricos-frutales'
ANALISIS = 'laboratorio-analisis-calidad-alimentos-suelos-aguas'
MICROBIOLOGIA = 'laboratorio-microbiologia-biotecnologia-aplicada'
VETERINARIO = 'laboratorio-diagnostico-veterinario-biologia-molecular'
SENSORIAL = 'laboratorio-analisis-sensorial-desarrollo-alimentos'
OCL = 'observatorio-cadena-lactea-carchi'

# (origen, relación, destino, qué pasa de una a otra, para qué)
RELACIONES = (
    # San Francisco aloja las cinco plantas piloto y les provee lo que produce.
    *((SF, 'aloja', planta, '', 'La planta funciona dentro del centro y usa sus servicios.')
      for planta in (LACTEOS, CARNICOS, FRUTAS, CEREALES, ALMIDON)),
    (SF, 'abastece', LACTEOS, 'Leche cruda del hato del centro', 'Quesos, yogur y prácticas de lácteos.'),
    (SF, 'abastece', FRUTAS, 'Mora, uvilla, tomate de árbol, fresa y hortalizas de invernadero',
     'Mermeladas, pulpas, conservas y prácticas de frutas y vegetales.'),
    (SF, 'abastece', CEREALES, 'Trigo y granos andinos', 'Harinas, panificación y prácticas de cereales.'),
    (SF, 'abastece', ALMIDON, 'Papa', 'Extracción de almidón y ensayos de biotecnología.'),
    # Alonso Tadeo aloja las plantas que transformarán su café y sus frutales.
    (AT, 'aloja', CAFE, '', 'La planta se forma con los equipos de beneficio y torrefacción del centro.'),
    (AT, 'aloja', CITRICOS, '', 'Propuesta para transformar los frutales del centro.'),
    (AT, 'abastece', CAFE, 'Café cereza del cultivo del centro', 'Beneficio, secado, tostado y café de origen.'),
    (AT, 'abastece', CITRICOS, 'Limón, naranja y frutales de clima cálido', 'Jugos, pulpas, concentrados y deshidratados.'),
    # Los laboratorios analizan lo que producen los centros y las plantas.
    (ANALISIS, 'analiza', SF, 'Suelos, agua de riego y pastos', 'Fertilización, riego y calidad del forraje.'),
    (ANALISIS, 'analiza', AT, 'Suelos y agua de riego', 'Fertilización y riego de café y frutales.'),
    (ANALISIS, 'analiza', LACTEOS, 'Leche y productos lácteos', 'Control de calidad de la materia prima y del producto.'),
    (MICROBIOLOGIA, 'analiza', LACTEOS, 'Leche cruda y productos lácteos', 'Calidad microbiológica e inocuidad.'),
    (VETERINARIO, 'analiza', SF, 'Muestras del hato lechero y de los cuyes', 'Sanidad animal y diagnóstico.'),
    (VETERINARIO, 'analiza', AT, 'Muestras de las gallinas y los cerdos', 'Sanidad animal y diagnóstico.'),
    (SENSORIAL, 'analiza', LACTEOS, 'Productos lácteos', 'Evaluación sensorial y desarrollo de producto.'),
    (SENSORIAL, 'analiza', FRUTAS, 'Productos de frutas y vegetales', 'Evaluación sensorial y desarrollo de producto.'),
    (SENSORIAL, 'analiza', CAFE, 'Café tostado', 'Catación y perfil de taza.'),
    # El observatorio agroalimentario sigue la producción de leche y papa del Carchi, donde está el centro.
    (OCL, 'sigue', SF, 'Producción de leche y papa', 'El centro es referencia de la producción de clima frío.'),
)


class Command(BaseCommand):
    help = 'Registra las relaciones entre centros, plantas, laboratorios y observatorios.'

    def add_arguments(self, parser):
        parser.add_argument('--reescribir', action='store_true', help='Reemplaza los textos con los del archivo.')

    @transaction.atomic
    def handle(self, *args, **options):
        unidades = {unidad.slug: unidad for unidad in Unidad.objects.filter(
            slug__in={slug for origen, _tipo, destino, *_resto in RELACIONES for slug in (origen, destino)})}
        nuevas = revisadas = 0
        omitidas = set()
        for orden, (origen, tipo, destino, que_fluye, descripcion) in enumerate(RELACIONES, start=1):
            faltan = {slug for slug in (origen, destino) if slug not in unidades}
            if faltan:
                omitidas |= faltan
                continue
            relacion = RelacionUnidad.objects.filter(
                origen=unidades[origen], tipo=tipo, destino=unidades[destino]).first()
            if relacion is None:
                # Se valida antes de guardar: un laboratorio no «aloja» ni un centro «analiza».
                relacion = RelacionUnidad(origen=unidades[origen], tipo=tipo, destino=unidades[destino],
                                          que_fluye=que_fluye, descripcion=descripcion, orden=orden)
                relacion.full_clean()
                relacion.save()
                nuevas += 1
            elif options['reescribir'] and (relacion.que_fluye, relacion.descripcion) != (que_fluye, descripcion):
                relacion.que_fluye, relacion.descripcion = que_fluye, descripcion
                relacion.save(update_fields=['que_fluye', 'descripcion'])
                revisadas += 1
        for slug in sorted(omitidas):
            self.stdout.write(self.style.WARNING(f'Omitida: {slug} no está registrada.'))
        self.stdout.write(self.style.SUCCESS(f'Relaciones: {nuevas} nuevas y {revisadas} revisadas.'))
