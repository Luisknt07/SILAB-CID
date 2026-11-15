"""Actualización conservadora, fichas individuales y cadena de café completa."""

from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.plantas_piloto.operacion.models.produccion import (
    EtapaReceta,
    LoteProducto,
    OrdenProduccion,
    Producto,
    Receta,
)
from apps.plantas_piloto.operacion.presentation.procesos import (
    balance_de_masa,
    datos_de_receta,
)
from apps.plantas_piloto.tests import test_cafe as base_cafe
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.equipo_referencia import referencias_por_area


class CafeCadenaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        base_cafe.CafeContenidoTests.setUpTestData.__func__(cls)

    setUp = base_cafe.CafeContenidoTests.setUp

    def inicial(self):
        call_command("preparar_planta_cafe", aplicar=True, stdout=StringIO())

    def ampliar(self):
        salida = StringIO()
        call_command("completar_planta_cafe", aplicar=True, stdout=salida)
        return salida.getvalue()

    def test_conserva_ids_y_completa_maquinaria_lab_y_seis_presentaciones(self):
        self.inicial()
        ids_recetas = set(
            Receta.objects.filter(unidad=self.unidad).values_list("pk", flat=True)
        )
        ids_etapas = set(
            EtapaReceta.objects.filter(receta__unidad=self.unidad).values_list(
                "pk", flat=True
            )
        )
        ids_equipos = set(
            ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=self.unidad
            ).values_list("pk", flat=True)
        )
        self.ampliar()
        self.assertEqual(
            EspacioReservable.objects.filter(unidad=self.unidad).count(), 5
        )
        self.assertEqual(Receta.objects.filter(unidad=self.unidad).count(), 15)
        self.assertEqual(
            EtapaReceta.objects.filter(receta__unidad=self.unidad).count(), 118
        )
        self.assertEqual(
            ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=self.unidad, tipo="equipo"
            ).count(),
            56,
        )
        self.assertTrue(
            ids_recetas.issubset(
                set(
                    Receta.objects.filter(unidad=self.unidad).values_list(
                        "pk", flat=True
                    )
                )
            )
        )
        self.assertTrue(
            ids_etapas.issubset(
                set(
                    EtapaReceta.objects.filter(receta__unidad=self.unidad).values_list(
                        "pk", flat=True
                    )
                )
            )
        )
        self.assertTrue(
            ids_equipos.issubset(
                set(
                    ElementoFichaArea.objects.filter(
                        ficha__espacio__unidad=self.unidad
                    ).values_list("pk", flat=True)
                )
            )
        )
        for tipo in ("GRA", "MOL"):
            for peso in (250, 500, 1000):
                self.assertTrue(
                    Producto.objects.filter(
                        unidad=self.unidad, codigo=f"CAF-P-{tipo}-{peso}"
                    ).exists()
                )
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.unidad).exists())
        self.assertFalse(
            Consumible.objects.filter(unidad=self.unidad)
            .exclude(stock_total=0)
            .exists()
        )
        self.assertFalse(OrdenProduccion.objects.filter(unidad=self.unidad).exists())
        self.assertFalse(LoteProducto.objects.filter(unidad=self.unidad).exists())

    def test_repetir_no_duplica_y_preserva_ediciones_posteriores(self):
        self.inicial()
        self.ampliar()
        self.assertIn("sin cambios", self.ampliar())
        indice = FichaContenido.objects.get(codigo="CAF-REF-SILO-SECO")
        equipo = indice.objeto
        equipo.nombre = "Silo configurado por administración"
        equipo.cuidados = "Procedimiento propio autorizado"
        equipo.save()
        receta = Receta.objects.get(codigo="CAF-R-VER-LAV")
        etapa = receta.etapas.get(orden=3)
        etapa.instrucciones = "Cambio propio de la planta"
        etapa.save()
        cantidad = ElementoFichaArea.objects.filter(
            ficha__espacio__unidad=self.unidad
        ).count()
        self.ampliar()
        equipo.refresh_from_db()
        etapa.refresh_from_db()
        self.assertEqual(equipo.nombre, "Silo configurado por administración")
        self.assertEqual(etapa.instrucciones, "Cambio propio de la planta")
        self.assertEqual(
            ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=self.unidad
            ).count(),
            cantidad,
        )

    def test_simulacion_sin_carga_inicial_solo_select(self):
        with CaptureQueriesContext(connection) as consultas:
            call_command("completar_planta_cafe", simular=True, stdout=StringIO())
        self.assertTrue(
            all(q["sql"].lstrip().upper().startswith("SELECT") for q in consultas),
            [q["sql"][:100] for q in consultas],
        )
        self.assertFalse(Receta.objects.filter(unidad=self.unidad).exists())

    def test_fallo_revierte_reordenamiento_y_altas_sin_borrar_ids(self):
        self.inicial()
        antes = list(
            EtapaReceta.objects.filter(receta__unidad=self.unidad)
            .order_by("pk")
            .values_list("pk", "orden", "nombre")
        )
        metodo = EtapaReceta.save

        def fallo(obj, *args, **kwargs):
            if obj.nombre == "Clasificación por tamaños mediante zarandas":
                raise RuntimeError("Fallo de prueba")
            return metodo(obj, *args, **kwargs)

        with patch.object(EtapaReceta, "save", fallo), self.assertRaises(RuntimeError):
            self.ampliar()
        self.assertEqual(
            antes,
            list(
                EtapaReceta.objects.filter(receta__unidad=self.unidad)
                .order_by("pk")
                .values_list("pk", "orden", "nombre")
            ),
        )
        self.assertEqual(
            EspacioReservable.objects.filter(unidad=self.unidad).count(), 2
        )

    def test_fichas_individuales_visibilidad_aislamiento_y_sin_escritura(self):
        self.inicial()
        self.ampliar()
        elemento = FichaContenido.objects.get(codigo="CAF-REF-SILO-SECO").objeto
        url = reverse("ficha_equipo_referencia", args=[self.unidad.slug, elemento.pk])
        # El silo no está registrado en la planta: el público no lo ve; quien la gestiona revisa su ficha.
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(get_user_model().objects.create_superuser(
            "gestor_cafe_silo", "gestor@example.test", "clave-solo-fixture"))
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Silo de alimentación de café seco")
        self.assertContains(respuesta, "Controles y mediciones")
        self.assertFalse(
            any(
                q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                for q in consultas
            )
        )
        self.assertEqual(self.client.post(url).status_code, 405)
        otra = Unidad.objects.create(
            nombre="Otra",
            slug="otra",
            dependencia="plantas_piloto",
            fecha_inicio=date(2026, 1, 1),
        )
        self.assertEqual(
            self.client.get(
                reverse("ficha_equipo_referencia", args=[otra.slug, elemento.pk])
            ).status_code,
            404,
        )
        indice = FichaContenido.objects.get(codigo="CAF-REF-SILO-SECO")
        indice.estado = "archivada"
        indice.save()
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)
        area_url = reverse(
            "area_unidad", args=[self.unidad.slug, elemento.ficha.espacio.codigo]
        )
        self.assertNotContains(self.client.get(area_url), elemento.nombre)
        areas = list(EspacioReservable.objects.filter(unidad=self.unidad))
        self.assertNotIn(
            elemento.pk,
            [
                e.pk
                for es in referencias_por_area(areas, AnonymousUser()).values()
                for e in es
            ],
        )

    def test_gestor_edita_ficha_nativa_y_carga_inicial_completa(self):
        self.ampliar()
        self.assertEqual(Receta.objects.filter(unidad=self.unidad).count(), 15)
        self.assertIn("sin cambios", self.ampliar())
        usuario = get_user_model().objects.create_superuser(
            "gestor_cafe", "gestor@example.test", "clave-solo-fixture"
        )
        self.client.force_login(usuario)
        elemento = FichaContenido.objects.get(codigo="CAF-REF-CATACION").objeto
        respuesta = self.client.get(
            reverse("ficha_equipo_referencia", args=[self.unidad.slug, elemento.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            reverse("admin:plantas_piloto_fichaarea_change", args=[elemento.ficha_id]),
        )

    def test_menu_tiene_56_fichas_y_laboratorio_con_consultas_agrupadas(self):
        self.inicial()
        self.ampliar()
        areas = list(EspacioReservable.objects.filter(unidad=self.unidad))
        with CaptureQueriesContext(connection) as consultas:
            fichas = referencias_por_area(areas, AnonymousUser())
        self.assertEqual(sum(len(x) for x in fichas.values()), 56)
        self.assertLessEqual(len(consultas), 8)
        response = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(response, "Laboratorio de calidad, muestreo y catación")
        # La planta no registró esos equipos: el visor no los muestra como si existieran.
        self.assertNotContains(response, "equipamiento-referencia")
        self.assertContains(response, "cafe-cadena")

    def test_cadena_y_balances_no_confunden_trilla_molino_o_envase(self):
        self.inicial()
        self.ampliar()
        respuesta = self.client.get(reverse("cadena_cafe", args=[self.unidad.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "250, 500 y 1.000 g")
        for receta in Receta.objects.filter(unidad=self.unidad):
            self.assertEqual(
                balance_de_masa(datos_de_receta(receta))["diferencia"],
                "0",
                receta.codigo,
            )
        grano = Receta.objects.get(codigo="CAF-R-GRA500")
        molido = Receta.objects.get(codigo="CAF-R-MOL500")
        self.assertFalse(grano.etapas.filter(nombre__startswith="Molienda,").exists())
        self.assertTrue(molido.etapas.filter(nombre__startswith="Molienda,").exists())
        trilla = Receta.objects.get(codigo="CAF-R-VER-LAV")
        nombres = list(trilla.etapas.values_list("nombre", flat=True))
        self.assertLess(
            nombres.index("Trilla o descascarado y aspiración"),
            nombres.index("Clasificación por tamaños mediante zarandas"),
        )
        self.assertLess(
            nombres.index("Clasificación por tamaños mediante zarandas"),
            nombres.index("Selección por calidad en banda transportadora"),
        )

    def test_proceso_validado_o_decision_editorial_manual_no_se_reescribe(self):
        self.inicial()
        receta = Receta.objects.get(codigo="CAF-R-LAVADO")
        ficha = FichaContenido.objects.get(
            tipo="proceso", unidad=self.unidad, object_id=receta.pk
        )
        ficha.estado_validacion = "validada"
        ficha.save()
        nombres = list(receta.etapas.values_list("nombre", flat=True))
        self.ampliar()
        self.assertEqual(nombres, list(receta.etapas.values_list("nombre", flat=True)))
