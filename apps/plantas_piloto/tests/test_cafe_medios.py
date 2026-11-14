"""Plantilla común, medios con procedencia y conservación de edición manual."""

from io import StringIO
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from apps.plantas_piloto.tests import test_cafe as base_cafe
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.unidades import UnidadEquipo
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.formacion.presentation.aula import contexto_aula
from apps.recursos.models.recursos import ModuloUnidad


class CafeMediosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        base_cafe.CafeContenidoTests.setUpTestData.__func__(cls)

    setUp = base_cafe.CafeContenidoTests.setUp

    def inicial(self):
        call_command("completar_planta_cafe", aplicar=True, stdout=StringIO())
        self.unidad.refresh_from_db()

    def medios(self, aplicar=True):
        salida = StringIO()
        call_command("completar_medios_cafe", aplicar=aplicar, stdout=salida)
        return salida.getvalue()

    def test_simular_solo_select_sin_imagenes_o_medios_nuevos(self):
        self.inicial()
        with CaptureQueriesContext(connection) as consultas:
            self.medios(False)
        self.assertTrue(
            all(q["sql"].lstrip().upper().startswith("SELECT") for q in consultas)
        )
        self.assertFalse(ElementoFichaArea.objects.exclude(imagen_estatica="").exists())

    def test_carga_todos_los_medios_sin_crear_activos_o_existencias(self):
        self.inicial()
        ids = set(
            ElementoFichaArea.objects.filter(tipo="equipo").values_list("pk", flat=True)
        )
        self.medios()
        self.assertEqual(
            ids,
            set(
                ElementoFichaArea.objects.filter(tipo="equipo").values_list(
                    "pk", flat=True
                )
            ),
        )
        self.assertEqual(ElementoFichaArea.objects.filter(tipo="imagen").count(), 24)
        self.assertEqual(ElementoFichaArea.objects.filter(tipo="video").count(), 7)
        self.assertEqual(
            ElementoFichaArea.objects.filter(tipo="equipo")
            .exclude(imagen_estatica="")
            .count(),
            56,
        )
        self.assertEqual(Consumible.objects.exclude(imagen_catalogo="").count(), 17)
        for e in ElementoFichaArea.objects.exclude(imagen_estatica=""):
            self.assertTrue(finders.find(e.imagen_estatica), e.nombre)
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.unidad).exists())
        self.assertFalse(Consumible.objects.exclude(stock_total=0).exists())
        self.assertEqual(Receta.objects.filter(unidad=self.unidad).count(), 15)

    def test_ficha_usa_la_misma_plantilla_y_relaciona_trilla(self):
        self.inicial()
        self.medios()
        elemento = FichaContenido.objects.get(codigo="CAF-REF-TRILLA").objeto
        with CaptureQueriesContext(connection) as consultas:
            r = self.client.get(
                reverse("ficha_equipo_referencia", args=[self.unidad.slug, elemento.pk])
            )
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "portal/pages/unidades/aula/equipo.html")
        for texto in (
            "Identificación del equipo",
            "Visualización del equipo",
            "Especificaciones técnicas",
            "Videos del área y del proceso",
            "Procesos que lo usan",
            "Trilla, clasificación y selección",
            "trilladora.webp",
        ):
            self.assertContains(r, texto)
        self.assertNotContains(r, 'data-accion="reservar"')
        self.assertNotContains(r, "Imprimir etiqueta")
        self.assertFalse(
            any(
                q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                for q in consultas
            )
        )
        self.assertLessEqual(len(consultas), 20)

    def test_repetir_conserva_foto_y_medios_renombrados_o_archivados(self):
        self.inicial()
        self.medios()
        self.assertIn("sin cambios", self.medios())
        equipo = FichaContenido.objects.get(codigo="CAF-REF-TRILLA").objeto
        equipo.imagen_estatica = "img/pilares/LabLactesos.png"
        equipo.save()
        indice = FichaContenido.objects.filter(codigo__contains="-video-").first()
        video = indice.objeto
        video.nombre = "Video propio editado"
        video.url = "https://www.youtube.com/watch?v=UaSO05HMSYc"
        video.save()
        indice.estado = "archivada"
        indice.save()
        cantidad = ElementoFichaArea.objects.count()
        self.medios()
        equipo.refresh_from_db()
        video.refresh_from_db()
        indice.refresh_from_db()
        self.assertEqual(equipo.imagen_estatica, "img/pilares/LabLactesos.png")
        self.assertEqual(video.nombre, "Video propio editado")
        self.assertEqual(indice.estado, "archivada")
        self.assertEqual(ElementoFichaArea.objects.count(), cantidad)

    def test_fallo_revierte_imagenes_insumos_y_galerias(self):
        self.inicial()
        original = FichaContenido.save

        def fallar(obj, *args, **kwargs):
            if obj.codigo.startswith("CAF-MED-"):
                raise RuntimeError("Fallo simulado")
            return original(obj, *args, **kwargs)

        with (
            patch.object(FichaContenido, "save", fallar),
            self.assertRaises(RuntimeError),
        ):
            self.medios()
        self.assertFalse(ElementoFichaArea.objects.exclude(imagen_estatica="").exists())
        self.assertFalse(Consumible.objects.exclude(imagen_catalogo="").exists())
        self.assertEqual(ElementoFichaArea.objects.count(), 56)

    def test_menu_identifica_trilla_y_video_archivado_no_sale_en_equipo(self):
        self.inicial()
        self.medios()
        contexto = contexto_aula(
            self.unidad,
            ModuloUnidad.objects.filter(unidad=self.unidad),
            AnonymousUser(),
        )
        procesos = next(
            c for c in contexto["aula"]["carpetas"] if c["id"] == "SistemasProduccion"
        )
        self.assertEqual(procesos["total"], 15)
        self.assertTrue(
            any(
                g["nombre"] == "Trilla, clasificación y café verde"
                for g in procesos["grupos"]
            )
        )
        indice = FichaContenido.objects.get(codigo="CAF-MED-PPCA-CALIDAD-video-200")
        video = indice.objeto
        indice.estado = "archivada"
        indice.save()
        equipo = FichaContenido.objects.get(codigo="CAF-REF-CATACION").objeto
        r = self.client.get(
            reverse("ficha_equipo_referencia", args=[self.unidad.slug, equipo.pk])
        )
        self.assertNotContains(r, video.youtube_id)
