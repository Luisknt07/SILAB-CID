"""Contrato, seguridad y procedencia de la precarga docente del FT04."""

import ast
import inspect
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.laboratorios.operacion.presentation import logistica_distribucion_guia as docente
from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor
from apps.laboratorios.operacion.presentation import logistica_operacion_contenido as adaptador


# Cargar los normalizadores puros por archivo evita el __init__ legado de
# reservas, que importa vistas y modelos aunque no se utilice la base de datos.
def _modulo_puro(nombre):
    ruta = Path(__file__).resolve().parents[2] / "apps" / "reservas" / "presentation" / (nombre + ".py")
    especificacion = importlib.util.spec_from_file_location("_qa_" + nombre, ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


html = _modulo_puro("guia_html")
referencias = _modulo_puro("guia_referencias")
CAMPOS_RICOS = html.CAMPOS_RICOS
POLITICA_POR_CAMPO = html.POLITICA_POR_CAMPO
sanear = html.sanear
normalizar_bibliografia = referencias.normalizar_bibliografia
normalizar_materiales_complementarios = (
    referencias.normalizar_materiales_complementarios
)


class PrecargaOperacionLogisticaTests(unittest.TestCase):
    def test_contrato_usa_solo_campos_reales_y_privacidad_sin_publicacion(self):
        ruta = Path(__file__).resolve().parents[2] / "apps" / "reservas" / "presentation" / "forms.py"
        modulo = ast.parse(ruta.read_text(encoding="utf-8"))
        clase = next(
            n
            for n in modulo.body
            if isinstance(n, ast.ClassDef) and n.name == "GuiaPracticaForm"
        )
        campos = {
            n.targets[0].id
            for n in clase.body
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and isinstance(n.value.func.value, ast.Name)
            and n.value.func.value.id == "forms"
        }
        for caso in docente.CASOS:
            inicial = adaptador.inicial_guia(caso, 73)
            self.assertTrue(set(inicial) <= campos, set(inicial) - campos)
            self.assertEqual(inicial["formato_contenido"], "html")
            self.assertEqual(inicial["formato_procedimiento"], "numerado")
            self.assertFalse(inicial["permite_descarga"])
            self.assertFalse(inicial["solicita_publicacion"])
            self.assertEqual(inicial["proposito_codigo"], "docencia_practica")
            self.assertEqual(inicial["subtipo_actividad"], "practica_curricular")
            for clave, valor in inicial.items():
                if clave not in ("permite_descarga", "solicita_publicacion"):
                    self.assertIsInstance(valor, str)
                    self.assertTrue(valor.strip(), clave)
            for clave in ("titulo", "nombre_actividad", "asignatura"):
                self.assertLessEqual(len(inicial[clave]), 220)
            for clave in ("codigo_guia", "codigo_actividad"):
                self.assertLessEqual(len(inicial[clave]), 80)

    def test_no_precarga_identidad_reserva_aforo_recursos_ni_aprobacion(self):
        inicial = adaptador.inicial_guia()
        prohibidos = {
            "reserva_referencia",
            "actividad_existente",
            "reserva_fuente_id",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "maximo_estudiantes",
            "docente_responsable",
            "carrera_semestre",
            "categoria_uso",
            "duracion",
            "equipos",
            "software",
            "materiales",
            "reactivos",
            "manejo_residuos",
            "estado_publicacion",
            "visibilidad",
            "aprobado_por",
            "aprobado_en",
            "es_vigente",
            "estudiantes_asistentes",
            "firmas",
        }
        self.assertFalse(set(inicial) & prohibidos)
        self.assertFalse(adaptador.procedencia_guia()["autoriza_presencial"])
        for campo in (
            "descripcion_actividad",
            "fundamento_teorico",
            "medidas_seguridad",
        ):
            self.assertIn("Datos sintéticos", inicial[campo])
            self.assertIn("no autoriza", inicial[campo])
        self.assertIn(
            "Una partida o captura digital no demuestra asistencia",
            inicial["procedimiento"],
        )

    def test_semilla_exacta_y_extremos_preservados_sin_conversion_silenciosa(self):
        for semilla in (0, 42, 2147483647):
            self.assertEqual(
                adaptador.procedencia_guia("cd-pico", semilla)["semilla"], semilla
            )
            self.assertIn(
                str(semilla),
                adaptador.inicial_guia("cd-pico", semilla)["fundamento_teorico"],
            )
        for semilla in (True, False, None, "42", 42.0, -1, 2147483648, [], {}):
            for funcion in (adaptador.inicial_guia, adaptador.procedencia_guia):
                self.assertRaises(ValueError, funcion, "cd-normal", semilla)

    def test_casos_invalidos_no_usan_normal_por_defecto(self):
        for caso in (None, 1, True, [], {}, "cd-futuro", "CD-NORMAL", ""):
            for funcion in (adaptador.inicial_guia, adaptador.procedencia_guia):
                self.assertRaises(ValueError, funcion, caso)

    def test_procedencia_corresponde_a_versiones_y_asignaturas_reales(self):
        for caso in docente.CASOS:
            fuente = docente.guia(caso)
            metadatos = adaptador.procedencia_guia(caso, 73)
            self.assertEqual(metadatos["caso"], caso)
            self.assertEqual(metadatos["version_adaptador"], adaptador.VERSION)
            self.assertEqual(metadatos["version_guia"], docente.GUIA_VERSION)
            self.assertEqual(metadatos["version_motor"], motor.VERSION)
            self.assertEqual(metadatos["version_caso"], motor.VERSION_CASO)
            self.assertEqual(metadatos["version_dataset"], motor.DATASET_VERSION)
            self.assertEqual(metadatos["area"], fuente["area"])
            self.assertEqual(metadatos["asignaturas"], fuente["asignaturas"])
            self.assertEqual(metadatos["datos"], "sinteticos")
            self.assertEqual(
                json.loads(json.dumps(metadatos, allow_nan=False)), metadatos
            )

    def test_copia_independiente_y_determinismo_sin_consultar_estado_de_partidas(self):
        esperado = adaptador.inicial_guia("cd-falla", 73)
        metadatos = adaptador.procedencia_guia("cd-falla", 73)
        metadatos["asignaturas"][0]["codigo"] = "alterado"
        metadatos["area"]["codigo"] = "otra"
        primero = adaptador.inicial_guia("cd-falla", 73)
        primero["procedimiento"] = "alterado"
        with patch.object(
            motor, "crear_estado", side_effect=AssertionError("No interpretar estados")
        ):
            self.assertEqual(adaptador.inicial_guia("cd-falla", 73), esperado)
        self.assertEqual(
            adaptador.procedencia_guia("cd-falla", 73)["area"]["codigo"], "LOG-ALMACEN"
        )
        self.assertEqual(
            docente.guia("cd-falla")["asignaturas"][0]["codigo"],
            "LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A",
        )

    def test_rubrica_completa_y_diccionario_conservan_la_evidencia_docente(self):
        for caso in docente.CASOS:
            inicial = adaptador.inicial_guia(caso)
            ficha = docente.guia(caso)
            for criterio in ficha["rubrica_docente"]["criterios"]:
                self.assertIn(criterio["titulo"], inicial["criterios_evaluacion"])
                self.assertIn(criterio["evidencia"], inicial["criterios_evaluacion"])
                for nivel in criterio["niveles"]:
                    self.assertIn(nivel["descriptor"], inicial["criterios_evaluacion"])
            self.assertEqual(
                sum(x["puntos"] for x in ficha["rubrica_docente"]["criterios"]), 100
            )
            for nombre, dataset in ficha["diccionario_datos"].items():
                self.assertIn(nombre, inicial["fundamento_teorico"])
                for campo in dataset["campos"]:
                    self.assertIn(campo["campo"], inicial["fundamento_teorico"])
            self.assertIn(
                ficha["hipotesis"]["enunciado"], inicial["fundamento_teorico"]
            )
            for entregable in ficha["entregables"]:
                self.assertIn(entregable, inicial["resultados_esperados"])

    def test_fuentes_son_originales_y_normalizables_por_editor(self):
        for caso in docente.CASOS:
            inicial = adaptador.inicial_guia(caso)
            bibliografia = normalizar_bibliografia(inicial["bibliografia"])
            materiales = normalizar_materiales_complementarios(
                inicial["materiales_complementarios"]
            )
            self.assertEqual(len(bibliografia), 4)
            self.assertEqual(len(materiales), 4)
            self.assertEqual(
                {x["url"] for x in materiales},
                {x["url"] for x in docente.guia(caso)["fuentes"]},
            )
            for fuente in docente.guia(caso)["fuentes"]:
                self.assertIn(fuente["url"], inicial["bibliografia"])
                self.assertIn(fuente["consulta"], inicial["bibliografia"])
            self.assertNotIn("<", inicial["bibliografia"])

    def test_html_compatible_con_saneador_institucional_sin_perdida_semantica(self):
        for caso in docente.CASOS:
            inicial = adaptador.inicial_guia(caso)
            for campo in CAMPOS_RICOS:
                limpio, avisos = sanear(inicial[campo], POLITICA_POR_CAMPO[campo], ())
                self.assertFalse(avisos, (caso, campo, avisos))
                self.assertTrue(limpio)
                self.assertLess(len(limpio), 400000)
                self.assertEqual(
                    sanear(limpio, POLITICA_POR_CAMPO[campo], ())[0], limpio
                )
                self.assertNotIn("<script", limpio)
            self.assertIn("FIFO", inicial["fundamento_teorico"])
            self.assertIn(
                "No generar reservas desde resultados", inicial["procedimiento"]
            )

    def test_escape_texto_y_tablas_no_insertan_html_desde_contenido(self):
        ficha = docente.guia()
        ataque = '<script>alert("x")</script><img src=x onerror=alert(1)>'
        ficha["contexto"] = ataque
        ficha["hipotesis"]["enunciado"] = ataque
        ficha["objetivos"][0]["criterio"] = ataque
        ficha["procedimiento"][0]["pasos"][0] = ataque
        ficha["rubrica_docente"]["criterios"][0]["niveles"][0]["descriptor"] = ataque
        with patch.object(docente, "guia", return_value=ficha):
            inicial = adaptador.inicial_guia()
        for campo in CAMPOS_RICOS:
            self.assertNotIn("<script", inicial[campo])
            self.assertNotIn("<img", inicial[campo])
        for campo in (
            "fundamento_teorico",
            "objetivos",
            "procedimiento",
            "criterios_evaluacion",
        ):
            self.assertIn("&lt;script&gt;", inicial[campo])
            self.assertIn("&quot;x&quot;", inicial[campo])

    def test_adaptador_no_importa_django_modelos_archivos_o_red(self):
        arbol = ast.parse(inspect.getsource(adaptador))
        imports = [
            n for n in ast.walk(arbol) if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        nombres = [
            getattr(n, "module", "") or " ".join(x.name for x in n.names)
            for n in imports
        ]
        for prohibido in (
            "django",
            "models",
            "requests",
            "urllib",
            "pathlib",
            "os",
            "socket",
        ):
            self.assertFalse(
                any(prohibido in nombre.split(".") for nombre in nombres), nombres
            )
        llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)]
        self.assertFalse(
            any(
                isinstance(n.func, ast.Name) and n.func.id in ("open", "exec", "eval")
                for n in llamadas
            )
        )


if __name__ == "__main__":
    unittest.main()
