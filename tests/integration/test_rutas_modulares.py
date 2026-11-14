"""Compatibilidad publica y aislamiento de carga de las nuevas fronteras."""

import ast
from dataclasses import FrozenInstanceError, asdict
from datetime import date
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

from django.test import TestCase
from django.urls import get_resolver, resolve, reverse

from apps.directorio_unidades.contracts import IdentidadUnidad, TipoUnidad
from apps.directorio_unidades.selectors import obtener_identidad_publica
from apps.integraciones.inventario import inventario_del_proyecto, rutas_de
from apps.directorio_unidades.models.core import Unidad


ROOT = Path(__file__).resolve().parents[2]
CONTEXTOS = (
    "portal",
    "centros_id",
    "laboratorios",
    "plantas_piloto",
    "centros_experimentales",
    "observatorios",
)
BASELINE = json.loads(
    (Path(__file__).parent / "fixtures/rutas_antes_reestructura.json").read_text(
        encoding="utf-8"
    )
)


# TestCase y no SimpleTestCase: el puente consulta el catalogo institucional de
# tipologias para saber si la puerta del directorio sigue abierta.
class RutasModularesTests(TestCase):
    def test_todas_las_rutas_conservan_path_nombre_y_controlador(self):
        actuales = list(rutas_de(get_resolver("config.rutas_aplicaciones").url_patterns))
        # Ninguna ruta anterior a la reestructura se pierde ni cambia de nombre; las nuevas se suman.
        conservadas = {(r["ruta"], r["nombre"]) for r in actuales}
        self.assertEqual(
            [(r["ruta"], r["nombre"]) for r in BASELINE if (r["ruta"], r["nombre"]) not in conservadas],
            [],
        )
        for anterior in BASELINE:
            with self.subTest(ruta=anterior["ruta"]):
                if anterior["regex"]:
                    muestra = "/media/prueba.pdf"
                else:
                    muestra = "/" + re.sub(
                        r"<(\w+):(\w+)>",
                        lambda m: "1" if m[1] == "int" else "prueba",
                        anterior["ruta"],
                    )
                match = resolve(muestra, urlconf="config.rutas_aplicaciones")
                self.assertEqual(match.url_name, anterior["nombre"])
                if anterior["nombre"]:
                    self.assertEqual(
                        reverse(
                            anterior["nombre"],
                            kwargs=match.kwargs,
                            urlconf="config.rutas_aplicaciones",
                        ),
                        muestra,
                    )
                callback = getattr(match.func, "view_class", match.func)
                if anterior["propietario_ruta"] == "heredadas":
                    self.assertEqual(
                        callback.__name__, anterior["callback_anterior"].split(".")[-1]
                    )
                    from config.rutas_operativas import PROVEEDORES
                    propietarios = {
                        (str(r.pattern), r.name): proveedor.rsplit('.presentation.', 1)[0]
                        for proveedor in PROVEEDORES
                        for r in importlib.import_module(proveedor).urlpatterns
                    }
                    self.assertTrue(callback.__module__.startswith(
                        propietarios[(anterior['ruta'], anterior['nombre'])] + '.'
                    ))
                else:
                    self.assertEqual(
                        callback.__module__,
                        f"apps.{anterior['propietario_ruta']}.presentation.views",
                    )

    def test_cada_contexto_carga_sin_django_setup_ni_otras_verticales(self):
        for contexto in CONTEXTOS:
            with self.subTest(contexto=contexto):
                script = f"""
import importlib
import sys
import importlib.abc
class Bloqueo(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith("webcitt") or any(fullname == "apps." + other or fullname.startswith("apps." + other + ".") for other in {CONTEXTOS!r} if other != {contexto!r}):
            raise ImportError("Dependencia prohibida: " + fullname)
sys.meta_path.insert(0, Bloqueo())
module = importlib.import_module("apps.{contexto}.presentation.urls")
assert module.urlpatterns
from django.apps import apps
assert not apps.ready
"""
                result = subprocess.run(
                    [sys.executable, "-c", script],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_verticales_no_importan_internos_heredados_ni_otra_vertical(self):
        for contexto in CONTEXTOS:
            for path in (ROOT / "apps" / contexto / "presentation").rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        imports.append(node.module or "")
                allowed = (
                    f"apps.{contexto}",
                    "apps.core.",
                    "apps.directorio_unidades.contracts",
                    "apps.integraciones.unidades",
                )
                self.assertFalse(
                    any(
                        name.startswith("webcitt")
                        or (name.startswith("apps.") and not name.startswith(allowed))
                        for name in imports
                    ),
                    path,
                )

    def test_adaptadores_preservan_parametros_y_respuestas(self):
        for tipo in TipoUnidad:
            module = importlib.import_module(f"apps.{tipo.contexto}.presentation.views")
            with (
                self.subTest(tipo=tipo),
                patch(
                    "apps.directorio_unidades.presentation.catalogo.catalogo_unidades"
                ) as catalogo,
            ):
                request = object()
                self.assertIs(module.catalogo(request), catalogo.return_value)
                catalogo.assert_called_once_with(
                    request, tipo.value, tipo.contexto, tipo.titulo
                )
            with patch(
                "apps.gestion_unidades.presentation.detalle.proyecto_detalle_view"
            ) as detalle:
                self.assertIs(
                    module.detalle(request, "slug-historico"), detalle.return_value
                )
                detalle.assert_called_once_with(request, "slug-historico")

    def test_contrato_de_identidad_es_inmutable_y_serializable(self):
        identidad = IdentidadUnidad(
            1,
            "Laboratorio",
            "laboratorio",
            TipoUnidad.LABORATORIO,
            "publico@upec.edu.ec",
        )
        with self.assertRaises(FrozenInstanceError):
            identidad.nombre = "Cambio"
        datos = json.loads(json.dumps(asdict(identidad)))
        self.assertEqual(datos["tipo"], "laboratorios")
        self.assertEqual(datos["version_contrato"], 1)
        with self.assertRaises(ValueError):
            TipoUnidad("centros_id")

    def test_inventario_cubre_modelos_y_archivos_sin_consultar_la_base(self):
        from django.apps import apps

        inventario = inventario_del_proyecto()
        self.assertEqual(len(inventario["rutas"]), len(list(rutas_de(get_resolver("config.rutas_aplicaciones").url_patterns))))
        self.assertEqual(
            {m["modelo"] for m in inventario["modelos"]},
            {m._meta.label for m in apps.get_app_config("webcitt").get_models()},
        )
        for modelo in inventario["modelos"]:
            self.assertTrue(modelo["tabla"])
            self.assertTrue(modelo["permisos_declarados"])
        self.assertEqual(
            {m['modelo'] for m in inventario['modelos_propios']},
            {m._meta.label for a in apps.get_app_configs() if a.name.startswith('apps.') for m in a.get_models()},
        )
        for modelo in inventario['modelos_propios']:
            self.assertTrue(modelo['propietario_actual'].startswith('apps.'))
            self.assertTrue((ROOT / modelo['archivo']).is_file())
        for rutas in inventario["archivos"].values():
            self.assertTrue(rutas)
            self.assertTrue(all((ROOT / ruta).is_file() for ruta in rutas))


class RecorridosVerticalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidades = {
            tipo: Unidad.objects.create(
                nombre=f"Unidad {tipo.contexto}",
                slug=tipo.contexto,
                descripcion="Unidad de auditoria",
                fecha_inicio=date(2026, 1, 1),
                dependencia=tipo.value,
                modo_operacion="lotes" if tipo is TipoUnidad.PLANTA_PILOTO else "",
                contacto_email=f"{tipo.contexto}@upec.edu.ec",
            )
            for tipo in TipoUnidad
        }

    def test_cuatro_catalogos_muestran_solo_sus_unidades(self):
        nombres = {
            TipoUnidad.LABORATORIO: "laboratorios_unidades",
            TipoUnidad.PLANTA_PILOTO: "plantas-piloto",
            TipoUnidad.CENTRO_EXPERIMENTAL: "centros-experimentales",
            TipoUnidad.OBSERVATORIO: "observatorios",
        }
        for tipo, nombre in nombres.items():
            with self.subTest(tipo=tipo):
                response = self.client.get(reverse(nombre))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, self.unidades[tipo].nombre)
                for otro, unidad in self.unidades.items():
                    if otro is not tipo:
                        self.assertNotContains(response, unidad.nombre)

    def test_cuatro_identidades_publicas_sin_exponer_datos_operativos(self):
        for tipo, unidad in self.unidades.items():
            with self.subTest(tipo=tipo):
                identidad = obtener_identidad_publica(unidad.slug, tipo)
                self.assertEqual(identidad.unidad_id, unidad.pk)
                self.assertIs(identidad.tipo, tipo)
                self.assertEqual(identidad.contacto_email, unidad.contacto_email)
                for otro in TipoUnidad:
                    if otro is not tipo:
                        self.assertIsNone(obtener_identidad_publica(unidad.slug, otro))
        unidad.activo = False
        unidad.save(update_fields=["activo"])
        self.assertIsNone(obtener_identidad_publica(unidad.slug))
        self.assertIsNone(obtener_identidad_publica("no-existe"))

    def test_cuatro_detalles_conservan_identidad_y_aliases_publicados(self):
        nombres = {
            TipoUnidad.LABORATORIO: "laboratorio_detalle",
            TipoUnidad.PLANTA_PILOTO: "planta_piloto_detalle",
            TipoUnidad.CENTRO_EXPERIMENTAL: "centro_experimental_detalle",
            TipoUnidad.OBSERVATORIO: "observatorio_detalle",
        }
        for tipo, nombre in nombres.items():
            unidad = self.unidades[tipo]
            with self.subTest(tipo=tipo):
                response = self.client.get(
                    reverse(nombre, kwargs={"slug": unidad.slug})
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, unidad.nombre)
                alias = self.client.get(
                    reverse("laboratorio_detalle", kwargs={"slug": unidad.slug})
                )
                self.assertEqual(alias.status_code, 200)
                self.assertContains(alias, unidad.nombre)
                unidad.refresh_from_db()
                self.assertEqual(unidad.visitas, 1)
        self.assertEqual(self.client.get("/observatorio/no-existe/").status_code, 404)

    def test_fallo_operativo_no_impide_atender_portal_y_centros_id(self):
        with patch(
            "apps.directorio_unidades.presentation.catalogo.catalogo_unidades",
            side_effect=RuntimeError("Fallo simulado"),
        ):
            with self.assertRaisesMessage(RuntimeError, "Fallo simulado"):
                self.client.get(reverse("plantas-piloto"))
            for nombre in (
                "home",
                "quienes_somos",
                "servicios_portal",
                "normativa",
                "noticias",
                "centros_id",
            ):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
