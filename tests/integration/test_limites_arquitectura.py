"""Reglas de transicion hacia el monolito modular.

El modelo legado conserva las dependencias enumeradas mientras se extraen
servicios. Esta prueba no las legitima: las congela para que ningun cambio
nuevo aumente el acoplamiento y permite reducir la lista una a una.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]
LEGACY_MODEL_DOMAIN_IMPORTS = {
    # Lecturas documentales ya presentes en ae31fca2, revisadas en la auditoría
    # del 09/11/2026: perfiles de catálogo, conformidad y notas calculadas.
    # No son controladores HTTP. Se conserva su contrato durante la extracción
    # del dominio documental; la lista explícita impide añadir nuevas aristas.
    ('apps/documentos/models/funcionalidad.py', 'apps.documentos.presentation.perfil_unidades'),
    ('apps/documentos/models/infraestructura.py', 'apps.documentos.presentation.perfil_unidades'),
    ('apps/documentos/models/respaldo_medicion.py', 'apps.documentos.presentation.perfil_unidades'),
    ('apps/documentos/models/respaldo_medicion.py', 'apps.documentos.presentation.perfil_laboratorios'),
    ('apps/documentos/models/expediente.py', 'apps.documentos.presentation.perfil_unidades'),
    ('apps/documentos/models/expediente.py', 'apps.documentos.presentation.perfil_laboratorios'),
    ('apps/documentos/models/expediente.py', 'apps.documentos.presentation.conformidad_permanente'),
    ('apps/documentos/models/expediente.py', 'apps.documentos.presentation.automatizacion_documental'),
    ('apps/documentos/models/expediente.py', 'apps.documentos.presentation.aprobacion_en_linea'),
    (
        "apps/recursos/models/recursos.py",
        "apps.plantas_piloto.operacion.presentation.secciones_plantas",
    ),
    (
        "apps/reservas/models/reservas.py",
        "apps.formacion.presentation.practicas_integracion",
    ),
    (
        "apps/reservas/models/reservas.py",
        "apps.reservas.presentation.guia_firmas",
    ),
    (
        "apps/reservas/models/reservas.py",
        "apps.reservas.presentation.guia_html",
    ),
    # Validación de paquetes (microproyectos, recorridos 360) dentro de clean() del recurso.
    (
        "apps/recursos/models/recursos.py",
        "apps.recursos.presentation.despliegue_microproyectos",
    ),
    (
        "apps/recursos/models/recursos.py",
        "apps.recursos.presentation.microproyectos",
    ),
    (
        "apps/recursos/models/recursos.py",
        "apps.recursos.presentation.tipos_adjunto",
    ),
    # Las secciones propias validan su número contra el mapa de la unidad.
    (
        "apps/gestion_unidades/models/secciones.py",
        "apps.plantas_piloto.operacion.presentation.secciones_plantas",
    ),
}


def domain_imports_in_models():
    found = set()
    for path in (ROOT / "apps").rglob("models/*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(module):
            if isinstance(node, ast.ImportFrom):
                imported = node.module or ""
                if imported.startswith("apps.") and ".presentation." in imported and not imported.startswith("apps.core."):
                    found.add((relative, imported))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("apps.") and ".presentation." in alias.name and not alias.name.startswith("apps.core."):
                        found.add((relative, alias.name))
    return found


class ArchitectureBoundaryTests(SimpleTestCase):
    def test_el_modelo_no_adquiere_nuevas_dependencias_de_aplicacion(self):
        self.assertEqual(domain_imports_in_models(), LEGACY_MODEL_DOMAIN_IMPORTS)

    def test_configuracion_no_importa_dominios_de_negocio(self):
        for path in (ROOT / "config").glob("*.py"):
            if path.name.startswith('tests_'):
                continue  # Los escenarios de integración importan sus fixtures.
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = []
            for node in ast.walk(module):
                if isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
            self.assertFalse(
                any(name.startswith("apps.") and any(
                    parte in name.split('.') for parte in ('presentation', 'models', 'services', 'admin')
                ) for name in imports),
                path.name,
            )

    def test_negocio_de_unidades_no_importa_la_vista_monolitica_de_reservas(self):
        dominio = ROOT / "apps"
        infracciones = []
        for path in dominio.rglob("*.py"):
            if path == dominio / "reservas" / "__init__.py":
                continue
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(module):
                if not isinstance(node, ast.ImportFrom):
                    continue
                referencia = "." * node.level + (node.module or "")
                if referencia == 'apps.reservas.presentation.views' or (
                    path.parent == ROOT / 'apps' / 'reservas' / 'presentation'
                    and referencia == '.views'
                ):
                    infracciones.append(
                        (path.relative_to(ROOT).as_posix(), node.lineno, referencia)
                    )
        self.assertEqual(infracciones, [])
