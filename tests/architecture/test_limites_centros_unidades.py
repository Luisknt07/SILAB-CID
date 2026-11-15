"""El límite entre Centros I+D y las unidades queda escrito y no puede crecer sin decidirlo.

Centros I+D solo conoce el núcleo. El resto del sistema solo lo nombra en los
puntos enumerados aquí, siempre dentro de una función: así una instalación
sin Centros I+D tiene una lista cerrada de lugares que adaptar. Añadir una
dependencia nueva exige ampliar esta lista a propósito.
"""
import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

# Composición del despliegue y la prueba de separación física de bases.
COMPOSICION = {'config/modulos.py', 'config/tests_multibase.py'}
# Consultas puntuales a Centros I+D desde otras aplicaciones, todas diferidas.
PUNTOS_QUE_CONSULTAN_CENTROS = {
    'apps/core/admin/site.py',
    'apps/gestion_unidades/admin/reportes.py',
    'apps/gestion_unidades/presentation/detalle.py',
    'apps/integraciones/management/commands/auditar_huerfanos.py',
    'apps/plantas_piloto/operacion/presentation/trazabilidad.py',
    'apps/recursos/entrega/archivos_acceso.py',
}


def importaciones(ruta):
    """Devuelve (aplicación importada, línea, si está a nivel de módulo) de un archivo."""
    arbol = ast.parse(ruta.read_text(encoding='utf-8-sig'))
    encontradas = []
    for padre in ast.walk(arbol):
        for nodo in ast.iter_child_nodes(padre):
            if isinstance(nodo, ast.ImportFrom) and nodo.module and not nodo.level:
                modulos = [nodo.module]
            elif isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            else:
                continue
            for modulo in modulos:
                partes = modulo.split('.')
                if partes[0] == 'apps' and len(partes) > 1:
                    encontradas.append((partes[1], nodo.lineno, isinstance(padre, ast.Module)))
    return encontradas


def fuentes(*carpetas):
    raiz = Path(settings.BASE_DIR)
    for carpeta in carpetas:
        for ruta in (raiz / carpeta).rglob('*.py'):
            relativa = ruta.relative_to(raiz).as_posix()
            if '/migrations/' in relativa or '/tests/' in relativa:
                continue
            yield relativa, ruta


class LimitesCentrosUnidadesTests(SimpleTestCase):
    def test_centros_id_solo_depende_del_nucleo(self):
        ajenas = sorted(
            (relativa, linea, aplicacion)
            for relativa, ruta in fuentes('apps/centros_id')
            for aplicacion, linea, _ in importaciones(ruta)
            if aplicacion not in {'centros_id', 'core'}
        )
        self.assertEqual(ajenas, [], 'Centros I+D no importa aplicaciones de unidades; use un contrato del núcleo.')

    def test_el_resto_solo_consulta_centros_en_los_puntos_declarados(self):
        consultan, a_nivel_de_modulo = set(), []
        for relativa, ruta in fuentes('apps', 'config'):
            if relativa.startswith('apps/centros_id/'):
                continue
            for aplicacion, linea, en_modulo in importaciones(ruta):
                if aplicacion != 'centros_id':
                    continue
                consultan.add(relativa)
                if en_modulo and relativa not in COMPOSICION:
                    a_nivel_de_modulo.append((relativa, linea))
        self.assertEqual(consultan - COMPOSICION, PUNTOS_QUE_CONSULTAN_CENTROS)
        self.assertEqual(a_nivel_de_modulo, [],
                         'Fuera de la composición, Centros I+D se consulta dentro de la función que lo necesita.')
