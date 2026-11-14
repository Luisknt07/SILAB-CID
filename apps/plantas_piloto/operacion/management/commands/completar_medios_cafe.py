"""Publica medios referenciales conservando archivos propios y fichas existentes."""

from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.staticfiles import finders
from django.contrib.contenttypes.models import ContentType
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.models.consumibles import Consumible
from apps.plantas_piloto.operacion.management.plantas.cafe_medios import (
    FOTOS,
    GALERIAS,
    IMAGENES_EQUIPOS,
    videos_de_area,
    IMAGENES_INSUMOS,
    imagen_de_insumo,
)


class Command(BaseCommand):
    help = "Completa imágenes de equipos y galerías/videos de las cinco áreas de café."

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument("--aplicar", action="store_true")
        modo.add_argument("--simular", action="store_true")

    def handle(self, *args, **opciones):
        self.aplicar = opciones["aplicar"]
        self.resumen = Counter()
        if self.aplicar:
            with transaction.atomic():
                unidad = Unidad.objects.select_for_update().get(
                    slug="planta-piloto-cafe", dependencia="plantas_piloto"
                )
                self.cargar(unidad)
        else:
            unidad = Unidad.objects.get(
                slug="planta-piloto-cafe", dependencia="plantas_piloto"
            )
            self.cargar(unidad)
        self.stdout.write(
            ("Aplicado: " if self.aplicar else "Simulación (SELECT): ")
            + (", ".join(f"{k}: {v}" for k, v in self.resumen.items()) or "sin cambios")
        )

    def cargar(self, unidad):
        for foto in FOTOS.values():
            if not finders.find(foto["ruta"]):
                raise CommandError("Falta la imagen local: " + foto["ruta"])
        indices = {
            f.codigo: f
            for f in FichaContenido.objects.filter(
                unidad=unidad, codigo__startswith="CAF-REF-"
            ).select_related("content_type")
        }
        for clave, imagen in IMAGENES_EQUIPOS.items():
            indice = indices.get("CAF-REF-" + clave)
            equipo = indice.objeto if indice else None
            if (
                not isinstance(equipo, ElementoFichaArea)
                or equipo.ficha.espacio.unidad_id != unidad.pk
            ):
                raise CommandError(
                    "Primero complete la ficha individual: CAF-REF-" + clave
                )
            anteriores = {
                "TRILLA": "trillado",
                "DESM": "despulpado",
                "DESPED": "clasificador",
                "TAMIZ-VER": "clasificador",
                "TAMIZ-MOL": "clasificador",
            }
            anterior = FOTOS[anteriores[clave]]["ruta"] if clave in anteriores else None
            if not equipo.foto and (
                not equipo.imagen_estatica or equipo.imagen_estatica == anterior
            ):
                self.resumen["Imágenes de equipo"] += 1
                if self.aplicar:
                    equipo.imagen_estatica = FOTOS[imagen]["ruta"]
                    equipo.save(update_fields=["imagen_estatica"])
        for clave in IMAGENES_INSUMOS:
            insumo = Consumible.objects.get(unidad=unidad, codigo="CAF-I-" + clave)
            if not insumo.imagen and not insumo.imagen_catalogo:
                foto = imagen_de_insumo(clave)
                if not finders.find(foto["ruta"]):
                    raise CommandError(
                        "Falta la imagen local del insumo: " + foto["ruta"]
                    )
                self.resumen["Imágenes de insumo"] += 1
                if self.aplicar:
                    insumo.imagen_catalogo = foto["ruta"]
                    insumo.credito_imagen = foto["credito"]
                    insumo.fuente_imagen = foto["fuente"]
                    insumo.full_clean()
                    insumo.save(
                        update_fields=[
                            "imagen_catalogo",
                            "credito_imagen",
                            "fuente_imagen",
                        ]
                    )
        for codigo, fotos in GALERIAS.items():
            ficha = FichaArea.objects.filter(
                espacio__unidad=unidad, espacio__codigo=codigo
            ).first()
            if not ficha:
                raise CommandError("Primero complete el área: " + codigo)
            for orden, (clave, titulo) in enumerate(fotos, 100):
                foto = FOTOS[clave]
                self.alta(
                    ficha,
                    "imagen",
                    titulo,
                    dict(
                        imagen_estatica=foto["ruta"],
                        para_que="Imagen referencial de la función; no acredita instalación en la unidad.",
                        ejemplo=foto["credito"],
                        url=foto["fuente"],
                        orden=orden,
                    ),
                )
            for orden, video in enumerate(videos_de_area(codigo), 200):
                self.alta(
                    ficha,
                    "video",
                    video["titulo"],
                    dict(
                        url="https://www.youtube.com/watch?v=" + video["id"],
                        ejemplo=video["canal"],
                        para_que=video["descripcion"],
                        orden=orden,
                    ),
                )

    def alta(self, ficha, tipo, nombre, valores):
        # Un medio renombrado conserva identidad por su URL/ruta: no se duplica.
        qs = ElementoFichaArea.objects.filter(ficha=ficha, tipo=tipo)
        identidad = (
            {"imagen_estatica": valores["imagen_estatica"]}
            if tipo == "imagen"
            else {"url": valores["url"]}
        )
        codigo = f"CAF-MED-{ficha.espacio.codigo}-{tipo}-{valores['orden']}"
        if FichaContenido.objects.filter(
            codigo=codigo, unidad=ficha.espacio.unidad
        ).exists():
            return
        obj = qs.filter(**identidad).first() or qs.filter(nombre=nombre).first()
        if not obj:
            self.resumen["Galerías" if tipo == "imagen" else "Videos"] += 1
            obj = ElementoFichaArea(ficha=ficha, tipo=tipo, nombre=nombre, **valores)
            if self.aplicar:
                obj.full_clean()
                obj.save()
        self.resumen["Índices de medios"] += 1
        if self.aplicar:
            indice = FichaContenido(
                unidad=ficha.espacio.unidad,
                codigo=codigo,
                tipo="documento",
                titulo=obj.nombre,
                descripcion="Medio referencial de la función; no acredita instalaciones ni resultados de la unidad.",
                estado="publicada",
                visibilidad="publica",
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.pk,
            )
            indice.full_clean()
            indice.save()
