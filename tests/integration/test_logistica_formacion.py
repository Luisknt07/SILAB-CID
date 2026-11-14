"""Calidad y preservación de programas LOG-FOR: sin matrícula ni operación ficticias."""

import csv
import tempfile
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from unicodedata import normalize

from django.core import serializers
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.formacion.management.cursos_precargados import cursos_logistica_aplicada as datos
from apps.formacion.management.cursos_precargados import odoo
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import MATRIZ_ASIGNATURAS
from apps.formacion.models.cursos import Curso, EdicionCurso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad


class ProgramasLogisticaTests(SimpleTestCase):
    def test_rutas_y_carga_academica_reutilizan_areas_y_asignaturas(self):
        self.assertEqual(len(datos.PROGRAMAS), 7)
        self.assertEqual(
            len({p["codigo_contenido"] for p in datos.PROGRAMAS.values()}), 7
        )
        for p in datos.PROGRAMAS.values():
            self.assertTrue(set(p["areas"]).issubset(AREAS))
            self.assertTrue(set(p["asignaturas"]).issubset(MATRIZ_ASIGNATURAS))
            self.assertEqual(len(p["MODULOS"]), 3)
            minutos = sum(
                v["duracion_min"] for _, _, ls in p["MODULOS"] for _, _, v in ls
            )
            self.assertEqual(minutos, p["CURSO"]["duracion_horas"] * 60)
            self.assertFalse(p["CURSO"]["emite_certificado"])
            self.assertFalse(p["EDICION"]["activa"])
            self.assertTrue(
                set(p["EDICION"]).isdisjoint(
                    {
                        "inicio",
                        "fin",
                        "cupo",
                        "inscripciones_desde",
                        "inscripciones_hasta",
                    }
                )
            )
            for _, _, lecciones in p["MODULOS"]:
                self.assertEqual(lecciones[-1][0], "evaluacion")
                self.assertTrue(any(t == "deber" for t, _, _ in lecciones))
                self.assertTrue(all(v["duracion_min"] > 0 for _, _, v in lecciones))
                for _, _, campos in lecciones:
                    for tipo, enunciado, opciones, explicacion in campos.get(
                        "preguntas", ()
                    ):
                        pregunta = PreguntaEvaluacion(
                            tipo=tipo,
                            enunciado=enunciado,
                            opciones=opciones,
                            explicacion=explicacion,
                        )
                        pregunta.clean()
                        self.assertEqual(
                            sum(correcta for _, correcta in pregunta.lista_opciones), 1
                        )

    def test_html_y_kit_completos_deterministas_sin_contenido_activo(self):
        for clave, p in datos.PROGRAMAS.items():
            with self.subTest(clave=clave):
                html = datos.programa_documento_html(clave)
                self.assertIn("lang='es'", html)
                self.assertIn("<caption>", html)
                self.assertEqual(html.count("<summary>Comprobar</summary>"), 12)
                self.assertNotRegex(
                    html.lower(),
                    r"<(?:script|iframe|object|embed|form)\b|javascript:|onload=",
                )
                self.assertEqual(datos.build_kit(clave), datos.build_kit(clave))
                with ZipFile(BytesIO(datos.build_kit(clave))) as archivo:
                    self.assertIsNone(archivo.testzip())
                    self.assertEqual(archivo.read("index.html").decode(), html)
                    self.assertTrue(
                        set(datos.DATOS[clave]).issubset(archivo.namelist())
                    )
                    self.assertFalse(
                        any(
                            ".." in n
                            or n.startswith("/")
                            or n.endswith((".exe", ".py", ".js"))
                            for n in archivo.namelist()
                        )
                    )
                    for nombre in datos.DATOS[clave]:
                        filas = list(
                            csv.reader(StringIO(archivo.read(nombre).decode()))
                        )
                        self.assertGreater(len(filas), 2)
                        self.assertTrue(
                            all(len(fila) == len(filas[0]) for fila in filas)
                        )

    def test_copia_de_programa_no_muta_el_catalogo(self):
        copia = datos.programa_para("trazabilidad-qr")
        copia["CURSO"]["nombre"] = "Edición manual"
        self.assertNotEqual(
            copia["CURSO"]["nombre"],
            datos.PROGRAMAS["trazabilidad-qr"]["CURSO"]["nombre"],
        )

    def test_balance_trazabilidad_y_deteccion_de_dataset_invalido(self):
        filas = list(
            csv.DictReader(StringIO(datos.DATOS["trazabilidad-qr"]["eventos.csv"]))
        )
        entradas = sum(int(f["cantidad_ud"]) for f in filas if f["tipo"] == "recepcion")
        salidas = sum(int(f["cantidad_ud"]) for f in filas if f["tipo"] == "despacho")
        self.assertEqual((entradas, salidas, entradas - salidas), (160, 50, 110))
        malas = list(
            csv.DictReader(
                StringIO(datos.DATOS["trazabilidad-qr"]["eventos_auditar.csv"])
            )
        )
        self.assertEqual((len(malas), len({f["evento_id"] for f in malas})), (7, 6))
        self.assertEqual(int(malas[-1]["minuto"]) < int(malas[-2]["minuto"]), True)

    def test_indicadores_y_cortes_temporales_independientes_del_texto(self):
        pedidos = list(
            csv.DictReader(StringIO(datos.DATOS["analitica-operativa"]["pedidos.csv"]))
        )
        otif = sum(
            int(f["entregado_ud"]) >= int(f["solicitado_ud"])
            and int(f["entrega_min"]) <= int(f["compromiso_min"])
            for f in pedidos
        )
        self.assertEqual((otif, len(pedidos)), (3, 6))
        demanda = list(
            csv.DictReader(StringIO(datos.DATOS["analitica-operativa"]["demanda.csv"]))
        )
        prueba = [f for f in demanda if int(f["periodo"]) >= 4]
        errores = [
            sum(abs(int(f["demanda_ud"]) - int(f[c])) for f in prueba) / len(prueba)
            for c in ("pronostico_base_ud", "pronostico_alternativo_ud")
        ]
        self.assertEqual(errores[0], 4)
        self.assertAlmostEqual(errores[1], 16 / 3)

    def test_sensores_cuentan_transiciones_y_no_lecturas_repetidas(self):
        filas = list(
            csv.DictReader(
                StringIO(datos.DATOS["automatizacion-logistica"]["eventos_sensor.csv"])
            )
        )
        estado, detecciones = 0, 0
        for fila in filas:
            if fila["sensor"] == "presencia":
                nuevo = int(fila["valor"])
                detecciones += nuevo == 1 and estado == 0
                estado = nuevo
        self.assertEqual(detecciones, 2)
        estaciones = list(
            csv.DictReader(
                StringIO(datos.DATOS["automatizacion-logistica"]["estaciones.csv"])
            )
        )
        tasas = {
            f["estacion"]: 3600
            / float(f["tiempo_ciclo_s"])
            * float(f["disponibilidad_fraccion"])
            for f in estaciones
        }
        self.assertEqual(min(tasas, key=tasas.get), "inspeccion")
        self.assertEqual(tasas["inspeccion"], 108)

    def test_retornos_y_emisiones_conservan_unidades_y_frontera(self):
        retornos = list(
            csv.DictReader(StringIO(datos.DATOS["logistica-circular"]["retornos.csv"]))
        )
        categorias = ("reutilizable_ud", "reparable_ud", "reciclable_ud", "rechazo_ud")
        for fila in retornos:
            self.assertEqual(
                sum(int(fila[c]) for c in categorias), int(fila["retorno_ud"])
            )
        totales = [sum(int(f[c]) for f in retornos) for c in categorias]
        self.assertEqual(totales, [120, 80, 70, 30])
        self.assertEqual([totales[0] + 60, totales[2], totales[3] + 20], [180, 70, 50])
        alternativas = list(
            csv.DictReader(
                StringIO(datos.DATOS["logistica-circular"]["alternativas.csv"])
            )
        )
        emisiones = [
            float(f["distancia_km"]) * float(f["factor_sintetico_kgco2e_km"])
            for f in alternativas
        ]
        self.assertEqual(emisiones, [96, 72, 28.5])
        intensidades = [
            e / (float(f["carga_kg"]) / 1000) for e, f in zip(emisiones, alternativas)
        ]
        for observado, esperado in zip(intensidades, [320, 240, 95]):
            self.assertAlmostEqual(observado, esperado)

    def test_iniciativas_y_beneficios_no_confunden_bruto_con_neto(self):
        iniciativas = list(
            csv.DictReader(
                StringIO(datos.DATOS["transformacion-digital"]["iniciativas.csv"])
            )
        )
        netos = [
            float(f["ahorro_horas_mes"]) * float(f["valor_hora_sintetico_usd"])
            - float(f["costo_mensual_usd"])
            for f in iniciativas
        ]
        self.assertEqual(netos, [100, 62, 60])
        recuperaciones = [
            float(f["costo_inicial_usd"]) / neto for f, neto in zip(iniciativas, netos)
        ]
        for observado, esperado in zip(recuperaciones, [3, 200 / 62, 5000 / 60]):
            self.assertAlmostEqual(observado, esperado)
        procesos = list(
            csv.DictReader(
                StringIO(datos.DATOS["transformacion-digital"]["procesos.csv"])
            )
        )
        ahorro = sum(
            int(f["casos_mes"])
            * (int(f["tiempo_base_min"]) - int(f["tiempo_meta_min"]))
            for f in procesos
        )
        self.assertEqual(ahorro, 900)

    def test_pares_y_pruebas_no_ocultan_fallos_ni_cambian_denominadores(self):
        ensayos = list(
            csv.DictReader(
                StringIO(datos.DATOS["proyectos-replicables"]["ensayos.csv"])
            )
        )
        pares = {
            par: [f for f in ensayos if f["par"] == par]
            for par in {f["par"] for f in ensayos}
        }
        diferencias = []
        for filas in pares.values():
            self.assertEqual(len(filas), 2)
            base = next(f for f in filas if f["politica"] == "base")
            alternativa = next(f for f in filas if f["politica"] == "alternativa")
            self.assertEqual(base["semilla"], alternativa["semilla"])
            diferencias.append(int(base["tiempo_min"]) - int(alternativa["tiempo_min"]))
        self.assertEqual(sum(diferencias) / len(diferencias), 6)
        for politica, esperado in [("base", 0.65), ("alternativa", 0.8)]:
            filas = [f for f in ensayos if f["politica"] == politica]
            self.assertAlmostEqual(
                sum(int(f["otif_ud"]) for f in filas)
                / sum(int(f["pedidos_total"]) for f in filas),
                esperado,
            )
        pruebas = list(
            csv.DictReader(
                StringIO(datos.DATOS["proyectos-replicables"]["pruebas.csv"])
            )
        )
        self.assertEqual(sum(f["esperado"] == f["observado"] for f in pruebas), 4)
        self.assertEqual(len(pruebas), 5)

    def test_actividades_tienen_pasos_y_aceptacion_especificos(self):
        for clave, bloques in datos.TEMARIOS.items():
            for indice, bloque in enumerate(bloques):
                self.assertEqual(len(datos.PROCEDIMIENTOS[clave][indice]), 4)
                self.assertIn("Secuencia reproducible:", bloque["actividad"])
                self.assertIn("Cotejo específico de aceptación:", bloque["actividad"])
                self.assertIn(bloque["contraste"], bloque["actividad"])

    def test_erp_no_inventa_convocatoria_y_conserva_40_horas(self):
        self.assertFalse(odoo.EDICION["activa"])
        self.assertFalse(odoo.CURSO["emite_certificado"])
        self.assertEqual(odoo.CURSO["inscripcion"], "aprobacion")
        self.assertTrue(
            set(odoo.EDICION).isdisjoint(
                {"inicio", "fin", "cupo", "inscripciones_desde", "inscripciones_hasta"}
            )
        )
        self.assertEqual(
            sum(
                v["duracion_min"]
                for _, _, ls in odoo.MODULOS
                for _, _, v in ls
                if v.get("obligatoria", True)
            ),
            2400,
        )
        self.assertTrue(
            all(
                v.get("fecha_hora") is None
                for _, _, ls in odoo.MODULOS
                for t, _, v in ls
                if t == "en_vivo"
            )
        )


class CargaFormacionLogisticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio de Logística",
            slug=SLUG,
            dependencia="laboratorios",
            descripcion="QA",
            fecha_inicio=date(2026, 1, 1),
        )
        cls.otra = Unidad.objects.create(
            nombre="Otra unidad",
            slug="otra-formacion-qa",
            dependencia="laboratorios",
            descripcion="QA",
            fecha_inicio=date(2026, 1, 1),
        )

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory(prefix="citt-log-for-")
        self.addCleanup(self.directorio.cleanup)
        self.ajustes = override_settings(
            BASE_DIR=Path(self.directorio.name),
            MEDIA_ROOT=Path(self.directorio.name) / "media",
        )
        self.ajustes.enable()
        self.addCleanup(self.ajustes.disable)

    def cargar(self, *args):
        salida = StringIO()
        call_command("preparar_logistica_formacion", *args, stdout=salida)
        return salida.getvalue()

    def test_simulacion_solo_select_sin_archivos_ni_generadores(self):
        with (
            patch(
                "apps.laboratorios.operacion.management.commands.preparar_logistica_formacion.guia_pdf",
                side_effect=AssertionError("No generar"),
            ),
            CaptureQueriesContext(connection) as consultas,
        ):
            salida = self.cargar("--simular")
        self.assertIn("7 programas nuevos", salida)
        self.assertTrue(
            all(q["sql"].lstrip().upper().startswith("SELECT") for q in consultas)
        )
        self.assertEqual(Curso.objects.count(), 0)
        self.assertEqual(list(Path(self.directorio.name).iterdir()), [])

    def test_carga_completa_sin_convocatorias_y_respaldo_previo(self):
        self.cargar("--aplicar")
        self.assertEqual(Curso.objects.count(), 7)
        self.assertEqual(ModuloCurso.objects.count(), 21)
        self.assertEqual(LeccionCurso.objects.count(), 112)
        self.assertEqual(PreguntaEvaluacion.objects.count(), 84)
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1
        )
        self.assertEqual(
            RegistroAuditoriaUnidad.objects.get(unidad=self.unidad).datos_nuevos[
                "programas"
            ],
            7,
        )
        self.assertEqual(EdicionCurso.objects.count(), 7)
        self.assertFalse(Curso.objects.filter(publicado=True).exists())
        self.assertFalse(Curso.objects.filter(emite_certificado=True).exists())
        self.assertFalse(EdicionCurso.objects.filter(activa=True).exists())
        self.assertFalse(
            EdicionCurso.objects.exclude(inicio=None, fin=None, cupo=None).exists()
        )
        self.assertEqual(
            len(list((Path(self.directorio.name) / "var" / "backups").glob("*.json"))),
            1,
        )
        self.assertTrue(
            all(
                leccion.archivo
                for leccion in LeccionCurso.objects.filter(tipo="material")
            )
        )

    def test_repeticion_preserva_renombrados_desactivados_y_archivos(self):
        self.cargar("--aplicar")
        curso = Curso.objects.order_by("pk").first()
        curso.nombre, curso.activo = "Nombre editado por el gestor", False
        curso.save(update_fields=["nombre", "activo"])
        modulo = curso.modulos.first()
        modulo.titulo = "Módulo reorganizado"
        modulo.save(update_fields=["titulo"])
        leccion = modulo.lecciones.first()
        leccion.contenido = "Contenido propio de la unidad"
        leccion.save(update_fields=["contenido"])
        objetos = [
            *Curso.objects.all(),
            *ModuloCurso.objects.all(),
            *LeccionCurso.objects.all(),
            *EdicionCurso.objects.all(),
        ]
        antes = serializers.serialize("json", objetos)
        archivos = sorted(
            p.relative_to(self.directorio.name).as_posix()
            for p in Path(self.directorio.name).rglob("*")
            if p.is_file()
        )
        self.assertIn("7 conservados", self.cargar("--simular"))
        self.cargar("--aplicar", "--publicar")
        despues = serializers.serialize(
            "json",
            [
                *Curso.objects.all(),
                *ModuloCurso.objects.all(),
                *LeccionCurso.objects.all(),
                *EdicionCurso.objects.all(),
            ],
        )
        self.assertEqual(antes, despues)
        self.assertEqual(
            archivos,
            sorted(
                p.relative_to(self.directorio.name).as_posix()
                for p in Path(self.directorio.name).rglob("*")
                if p.is_file()
            ),
        )

    def test_publicacion_nueva_no_abre_ediciones_ni_certificados(self):
        self.cargar("--aplicar", "--publicar")
        self.assertEqual(Curso.objects.filter(publicado=True).count(), 7)
        self.assertFalse(EdicionCurso.objects.filter(activa=True).exists())
        self.assertFalse(Curso.objects.filter(emite_certificado=True).exists())

    def test_preserva_cursos_y_eventos_previos_incluso_sin_lecciones(self):
        previo = Curso.objects.create(
            unidad=self.unidad,
            codigo="EXISTENTE-QA",
            nombre="Evento institucional",
            publicado=False,
        )
        duplicado = Curso.objects.create(
            unidad=self.unidad,
            codigo="CODIGO-MANUAL",
            nombre=datos.PROGRAMAS["trazabilidad-qr"]["CURSO"]["nombre"],
        )
        antes = serializers.serialize("json", [previo, duplicado])
        self.cargar("--aplicar")
        self.assertEqual(Curso.objects.count(), 8)
        self.assertEqual(
            antes,
            serializers.serialize(
                "json",
                list(
                    Curso.objects.filter(pk__in=[previo.pk, duplicado.pk]).order_by(
                        "pk"
                    )
                ),
            ),
        )
        self.assertFalse(duplicado.modulos.exists())

    def test_preserva_nombre_manual_con_tildes_mayusculas_y_unicode_equivalente(self):
        nombre = datos.PROGRAMAS["trazabilidad-qr"]["CURSO"]["nombre"]
        manual = Curso.objects.create(
            unidad=self.unidad, codigo="MANUAL-UNICODE",
            nombre=normalize("NFD", "  " + nombre.upper().replace(" ", "\t ") + "  "),
            descripcion="Contenido propio", publicado=True, activo=False,
        )
        antes = serializers.serialize("json", [manual])
        self.assertIn("6 programas nuevos; 1 conservados", self.cargar("--simular"))
        self.cargar("--aplicar")
        self.assertEqual(Curso.objects.count(), 7)
        manual.refresh_from_db()
        self.assertEqual(antes, serializers.serialize("json", [manual]))
        self.assertFalse(manual.modulos.exists())

    def test_colision_codigo_entre_unidades_no_escribe(self):
        Curso.objects.create(
            unidad=self.otra, codigo="LOG-FOR-01", nombre="Curso ajeno"
        )
        with self.assertRaises(CommandError):
            self.cargar("--aplicar")
        self.assertEqual(Curso.objects.count(), 1)
        self.assertFalse((Path(self.directorio.name) / "var").exists())

    def test_fallo_de_material_revierte_filas_y_solo_medios_nuevos(self):
        media = Path(self.directorio.name) / "media"
        media.mkdir()
        anterior = media / "conservar.txt"
        anterior.write_text("Contenido previo", encoding="utf-8")
        with (
            patch(
                "apps.laboratorios.operacion.management.commands.preparar_logistica_formacion.guia_pdf",
                side_effect=RuntimeError("QA fallo"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.cargar("--aplicar")
        self.assertFalse(Curso.objects.exists())
        self.assertEqual([p for p in media.rglob("*") if p.is_file()], [anterior])
        self.assertEqual(anterior.read_text(encoding="utf-8"), "Contenido previo")

    def test_publicar_exige_aplicacion_explicita(self):
        with self.assertRaises(CommandError):
            self.cargar("--publicar")
        self.assertFalse(Curso.objects.exists())
