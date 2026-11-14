"""Actualización conservadora del ERP: fixtures sintéticos y sin base operativa."""

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.laboratorios.operacion.management.commands.actualizar_logistica_erp import BASELINE, CAMPOS_CURSO, CAMPOS_EDICION, CAMPOS_LECCION, Command, cargar_baseline, huella_valor, normalizar_valor
from apps.formacion.management.cursos_precargados import odoo
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import SLUG
from apps.formacion.models.cursos import ComentarioLeccion, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ParticipanteEvento, PreguntaEvaluacion
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.directorio_unidades.models.core import Unidad

INSTRUCTORES_ORIGINALES = (
    "Equipo del Laboratorio de Logística y Negocios Internacionales | ERP, inventarios y comercio exterior\n"
    "Apoyo del Laboratorio de Inteligencia Artificial y Ciencia de Datos | Programación en Python y API"
)
HORARIO_ORIGINAL = "Clases en vivo los miércoles de 18:00 a 19:30 en la sala del aula; prácticas presenciales el 10 de diciembre y el 14 de enero; receso del 21 de diciembre al 3 de enero"
LUGAR_ORIGINAL = "Virtual y Área de Logística 4.0 y 5.0: ERP, analítica e IA del Laboratorio de Logística y Negocios Internacionales"


class BaselineErpTests(SimpleTestCase):
    def test_baseline_portable_cubre_identidades_y_campos_originales(self):
        baseline = cargar_baseline()
        self.assertTrue(BASELINE.is_file())
        self.assertEqual(
            baseline["source_git_commit"], "27a715c2f5742a357cae22f90d6e61051163ba9d"
        )
        self.assertEqual(len(baseline["modulos"]), 15)
        self.assertEqual(sum(len(x["lecciones"]) for x in baseline["modulos"]), 79)
        self.assertEqual(
            baseline["curso_campos"]["instructores"],
            huella_valor(INSTRUCTORES_ORIGINALES, "instructores"),
        )
        self.assertEqual(
            baseline["edicion_campos"]["horario"],
            huella_valor(HORARIO_ORIGINAL, "horario"),
        )
        self.assertEqual(
            baseline["edicion_campos"]["lugar"], huella_valor(LUGAR_ORIGINAL, "lugar")
        )
        prohibidos = {
            "pk",
            "id",
            "codigo",
            "orden",
            "activo",
            "activa",
            "publicado",
            "publicada",
            "archivo",
            "preguntas",
            "tipo",
            "titulo",
            "modulo",
            "curso",
        }
        self.assertFalse(
            prohibidos & set(CAMPOS_CURSO + CAMPOS_EDICION + CAMPOS_LECCION)
        )

    def test_datetime_equivalente_utc_y_json_normalizan_sin_perder_datos(self):
        local = datetime(2026, 11, 11, 18, 0, tzinfo=ZoneInfo("America/Guayaquil"))
        utc = datetime(2026, 11, 11, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(
            huella_valor(local, "fecha_hora"), huella_valor(utc, "fecha_hora")
        )
        self.assertEqual(
            huella_valor("2026-11-11T23:00:00Z", "fecha_hora"),
            huella_valor(local, "fecha_hora"),
        )
        self.assertEqual(
            huella_valor("2026-11-09", "inicio"),
            huella_valor(date(2026, 11, 9), "inicio"),
        )
        self.assertEqual(
            huella_valor({"b": [2, 3], "a": 1}), huella_valor({"a": 1, "b": (2, 3)})
        )
        self.assertNotEqual(huella_valor(None), huella_valor(""))
        self.assertNotEqual(huella_valor(True), huella_valor(1))
        self.assertNotEqual(huella_valor("texto "), huella_valor("texto"))
        self.assertEqual(
            normalizar_valor(utc), {"datetime_utc": "2026-11-11T23:00:00.000000+00:00"}
        )


class ActualizarLogisticaErpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            "erp-revision", password="clave"
        )
        cls.unidad = Unidad.objects.create(
            slug=SLUG,
            nombre="Laboratorio logístico",
            dependencia="laboratorios",
            descripcion="Ficha institucional",
            fecha_inicio=date(2026, 1, 1),
        )
        cls.curso = Curso.objects.create(
            unidad=cls.unidad,
            codigo="LOG-CUR-001",
            publicado=False,
            activo=False,
            orden=9,
            **{
                **odoo.CURSO,
                "instructores": INSTRUCTORES_ORIGINALES,
                "inscripcion": "abierta",
                "emite_certificado": True,
            },
        )
        cls.edicion = EdicionCurso.objects.create(
            curso=cls.curso,
            nombre="2026-II",
            anio=2026,
            inicio=date(2026, 11, 9),
            fin=date(2027, 1, 29),
            inscripciones_desde=date(2026, 10, 5),
            inscripciones_hasta=date(2026, 11, 6),
            cupo=20,
            horario=HORARIO_ORIGINAL,
            lugar=LUGAR_ORIGINAL,
            activa=True,
        )
        for orden, (titulo, descripcion, lecciones) in enumerate(odoo.MODULOS, 1):
            modulo = ModuloCurso.objects.create(
                curso=cls.curso,
                titulo=titulo,
                descripcion=descripcion,
                orden=orden + 10,
            )
            for posicion, (tipo, nombre, campos) in enumerate(lecciones, 1):
                datos = {k: v for k, v in campos.items() if k in CAMPOS_LECCION}
                LeccionCurso.objects.create(
                    modulo=modulo,
                    tipo=tipo,
                    titulo=nombre,
                    orden=posicion + 20,
                    publicada=False,
                    **datos,
                )
        cls.lectura = LeccionCurso.objects.get(
            modulo__curso=cls.curso,
            titulo="Cómo funciona el curso y la empresa del caso",
        )
        cls.clase = LeccionCurso.objects.get(
            modulo__curso=cls.curso, titulo="Clase en vivo 1: el ERP de Andina Trade"
        )
        cls.clase.fecha_hora = datetime(2026, 11, 11, 23, 0, tzinfo=timezone.utc)
        cls.clase.save(update_fields=["fecha_hora"])
        cls.evaluacion = LeccionCurso.objects.filter(
            modulo__curso=cls.curso, tipo="evaluacion"
        ).first()
        cls.pregunta = PreguntaEvaluacion.objects.create(
            leccion=cls.evaluacion,
            orden=1,
            tipo="unica",
            enunciado="Pregunta manual que se conserva",
            opciones="*Correcta\nOtra",
            explicacion="Explicación propia",
        )

    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)
        self.enterContext(
            override_settings(BASE_DIR=self.base, MEDIA_ROOT=self.base / "media")
        )

    def correr(self, **opciones):
        salida = StringIO()
        call_command("actualizar_logistica_erp", stdout=salida, **opciones)
        return salida.getvalue()

    def test_simular_y_default_solo_select_sin_lock_archivos_ni_auditoria(self):
        for opciones in ({}, {"simular": True}):
            with CaptureQueriesContext(connection) as consultas:
                salida = self.correr(**opciones)
            self.assertIn("simulación SELECT", salida)
            self.assertTrue(consultas.captured_queries)
            self.assertTrue(
                all(x["sql"].lstrip().upper().startswith("SELECT") for x in consultas)
            )
            self.assertFalse(any("FOR UPDATE" in x["sql"].upper() for x in consultas))
            self.assertLess(len(consultas), 15)
        self.assertFalse((self.base / "var").exists())
        self.assertFalse((self.base / "media").exists())
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.instructores, INSTRUCTORES_ORIGINALES)

    def test_actualiza_solo_campos_originales_y_conserva_estados_orden_preguntas_archivo(
        self,
    ):
        modulo_ids = list(self.curso.modulos.values_list("pk", "orden", "titulo"))
        leccion_ids = list(
            LeccionCurso.objects.filter(modulo__curso=self.curso).values_list(
                "pk", "modulo_id", "orden", "titulo", "tipo", "publicada", "archivo"
            )
        )
        self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.edicion.refresh_from_db()
        self.clase.refresh_from_db()
        self.pregunta.refresh_from_db()
        self.assertEqual(self.curso.instructores, odoo.CURSO["instructores"])
        self.assertEqual(self.curso.inscripcion, "aprobacion")
        self.assertFalse(self.curso.emite_certificado)
        self.assertEqual(
            (self.curso.publicado, self.curso.activo, self.curso.orden),
            (False, False, 9),
        )
        self.assertEqual(
            (
                self.edicion.inicio,
                self.edicion.fin,
                self.edicion.inscripciones_desde,
                self.edicion.inscripciones_hasta,
                self.edicion.cupo,
            ),
            (None, None, None, None, None),
        )
        self.assertTrue(self.edicion.activa)
        self.assertEqual(self.edicion.horario, odoo.EDICION["horario"])
        self.assertIsNone(self.clase.fecha_hora)
        self.assertEqual(
            list(self.curso.modulos.values_list("pk", "orden", "titulo")), modulo_ids
        )
        self.assertEqual(
            list(
                LeccionCurso.objects.filter(modulo__curso=self.curso).values_list(
                    "pk", "modulo_id", "orden", "titulo", "tipo", "publicada", "archivo"
                )
            ),
            leccion_ids,
        )
        self.assertEqual(self.pregunta.enunciado, "Pregunta manual que se conserva")
        self.assertEqual(self.pregunta.opciones, "*Correcta\nOtra")
        self.assertEqual(
            self.pregunta.lista_opciones, [("Correcta", True), ("Otra", False)]
        )
        self.assertEqual(PreguntaEvaluacion.objects.count(), 1)
        self.assertEqual(Curso.objects.count(), 1)
        self.assertEqual(EdicionCurso.objects.count(), 1)
        self.assertEqual(ModuloCurso.objects.count(), 15)
        self.assertEqual(LeccionCurso.objects.count(), 79)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        self.assertFalse((self.base / "media").exists())

    def test_respaldo_previo_contiene_originales_y_ids_sin_incluir_otras_unidades(self):
        otra = Unidad.objects.create(
            slug="otra-erp",
            nombre="Otra",
            dependencia="laboratorios",
            descripcion="Original",
            fecha_inicio=date(2026, 1, 1),
        )
        ajeno = Curso.objects.create(
            unidad=otra,
            codigo="OTRA-ERP",
            nombre=odoo.CURSO["nombre"],
            instructores="Docente ajeno",
        )
        self.correr(aplicar=True)
        respaldos = list((self.base / "var" / "backups").glob("logistica-erp-*.json"))
        self.assertEqual(len(respaldos), 1)
        respaldo = json.loads(respaldos[0].read_text("utf-8"))
        originales = [x for x in respaldo["registros"] if x["model"] == "formacion.curso"]
        self.assertEqual(len(originales), 1)
        self.assertEqual(originales[0]["pk"], self.curso.pk)
        self.assertEqual(
            originales[0]["fields"]["instructores"], INSTRUCTORES_ORIGINALES
        )
        self.assertEqual(originales[0]["fields"]["inscripcion"], "abierta")
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.instructores, "Docente ajeno")

    def test_ediciones_manuales_se_conservan_campo_por_campo(self):
        self.curso.instructores = "Docente confirmado por la unidad"
        self.curso.descripcion = "Descripción manual institucional"
        self.curso.save(update_fields=["instructores", "descripcion"])
        self.edicion.horario = "Horario propio verificado"
        self.edicion.cupo = 30
        self.edicion.save(update_fields=["horario", "cupo"])
        self.clase.fecha_hora = datetime(2026, 12, 5, 15, 0, tzinfo=timezone.utc)
        self.clase.contenido = "Consigna manual"
        self.clase.save(update_fields=["fecha_hora", "contenido"])
        salida = self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.edicion.refresh_from_db()
        self.clase.refresh_from_db()
        self.assertIn("editados conservados", salida)
        self.assertEqual(self.curso.instructores, "Docente confirmado por la unidad")
        self.assertEqual(self.curso.descripcion, "Descripción manual institucional")
        self.assertEqual(self.edicion.horario, "Horario propio verificado")
        self.assertEqual(self.edicion.cupo, 30)
        self.assertEqual(
            self.clase.fecha_hora, datetime(2026, 12, 5, 15, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(self.clase.contenido, "Consigna manual")
        self.assertEqual(self.curso.inscripcion, "aprobacion")

    def test_repetir_no_modifica_ni_crea_respaldo_o_auditoria(self):
        self.correr(aplicar=True)
        with CaptureQueriesContext(connection) as consultas:
            salida = self.correr(aplicar=True)
        self.assertIn("sin cambios", salida)
        self.assertFalse(
            any(
                x["sql"].lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
                for x in consultas
            )
        )
        self.assertEqual(len(list((self.base / "var" / "backups").glob("*.json"))), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)

    def test_matricula_retirada_protege_condiciones_fecha_y_edicion(self):
        InscripcionCurso.objects.create(
            edicion=self.edicion, usuario=self.usuario, estado="retirada"
        )
        salida = self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.edicion.refresh_from_db()
        self.clase.refresh_from_db()
        self.assertIn("historial", salida)
        self.assertEqual(self.curso.inscripcion, "abierta")
        self.assertTrue(self.curso.emite_certificado)
        self.assertEqual(self.edicion.inicio, date(2026, 11, 9))
        self.assertEqual(self.edicion.cupo, 20)
        self.assertEqual(
            self.clase.fecha_hora, datetime(2026, 11, 11, 23, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(self.curso.instructores, odoo.CURSO["instructores"])
        self.assertEqual(InscripcionCurso.objects.count(), 1)

    def test_invitacion_y_participante_evento_tambien_conservan_condiciones(self):
        for tipo in ("invitacion", "participante"):
            with self.subTest(tipo=tipo):
                if tipo == "invitacion":
                    registro = InvitacionCurso.objects.create(
                        edicion=self.edicion,
                        creada_por=self.usuario,
                        correo="invitado@example.org",
                        activa=False,
                    )
                else:
                    registro = ParticipanteEvento.objects.create(
                        edicion=self.edicion,
                        documento="DOC-ERP",
                        nombres_completos="Persona sintética",
                    )
                self.correr(aplicar=True)
                self.edicion.refresh_from_db()
                self.assertEqual(self.edicion.cupo, 20)
                registro.delete()

    def test_comentario_protege_condiciones_aun_sin_inscripcion(self):
        ComentarioLeccion.objects.create(
            leccion=self.clase,
            usuario=self.usuario,
            texto="Comentario que se preserva",
        )
        salida = self.correr(aplicar=True)
        self.clase.refresh_from_db()
        self.edicion.refresh_from_db()
        self.assertIn("historial", salida)
        self.assertIsNotNone(self.clase.fecha_hora)
        self.assertEqual(self.edicion.cupo, 20)
        self.assertEqual(ComentarioLeccion.objects.count(), 1)

    def test_codigo_distinto_se_identifica_por_nombre_y_no_se_reescribe(self):
        self.curso.codigo = "LOG-ERP-LOCAL"
        self.curso.save(update_fields=["codigo"])
        salida = self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.assertIn("código actual conservado", salida)
        self.assertEqual(self.curso.codigo, "LOG-ERP-LOCAL")
        self.assertEqual(self.curso.instructores, odoo.CURSO["instructores"])

    def test_identidad_duplicada_o_nombre_manual_no_se_adivina(self):
        duplicado = Curso.objects.create(
            unidad=self.unidad, codigo="LOG-ERP-DUP", nombre=self.curso.nombre
        )
        with self.assertRaisesMessage(CommandError, "único curso Odoo"):
            self.correr(aplicar=True)
        duplicado.delete()
        self.curso.nombre = "Curso renombrado manualmente"
        self.curso.save(update_fields=["nombre"])
        with self.assertRaisesMessage(CommandError, "único curso Odoo"):
            self.correr(aplicar=True)
        self.assertFalse((self.base / "var").exists())

    def test_modulo_y_leccion_renombrados_no_se_recrean_ni_mueven(self):
        self.lectura.titulo = "Lectura editada por docente"
        self.lectura.save(update_fields=["titulo"])
        modulo = self.clase.modulo
        modulo.titulo = "Módulo propio de la unidad"
        modulo.save(update_fields=["titulo"])
        salida = self.correr(aplicar=True)
        self.assertIn("conservado", salida)
        self.assertEqual(ModuloCurso.objects.count(), 15)
        self.assertEqual(LeccionCurso.objects.count(), 79)
        self.lectura.refresh_from_db()
        self.clase.refresh_from_db()
        self.assertEqual(self.lectura.titulo, "Lectura editada por docente")
        self.assertIsNotNone(self.clase.fecha_hora)

    def test_fuente_reestructurada_falla_antes_de_respaldo_y_escritura(self):
        modulos = deepcopy(odoo.MODULOS)
        titulo, descripcion, lecciones = modulos[0]
        modulos[0] = (titulo + " cambiado", descripcion, lecciones)
        with (
            patch.object(odoo, "MODULOS", modulos),
            self.assertRaisesMessage(CommandError, "estructura fuente"),
        ):
            self.correr(aplicar=True)
        self.assertFalse((self.base / "var").exists())
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.instructores, INSTRUCTORES_ORIGINALES)

    def test_fallo_desde_auditoria_revierte_todos_los_datos_y_conserva_respaldo(self):
        with patch(
            "apps.laboratorios.operacion.management.commands.actualizar_logistica_erp.registrar_auditoria",
            side_effect=RuntimeError("Fallo de auditoría"),
        ):
            with self.assertRaisesMessage(RuntimeError, "Fallo de auditoría"):
                self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.edicion.refresh_from_db()
        self.clase.refresh_from_db()
        self.assertEqual(self.curso.instructores, INSTRUCTORES_ORIGINALES)
        self.assertEqual(self.edicion.cupo, 20)
        self.assertIsNotNone(self.clase.fecha_hora)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertEqual(len(list((self.base / "var" / "backups").glob("*.json"))), 1)

    def test_fallo_respaldo_impide_actualizacion(self):
        with patch.object(Command, "_respaldar", side_effect=OSError("Sin espacio")):
            with self.assertRaisesMessage(OSError, "Sin espacio"):
                self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.inscripcion, "abierta")
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())

    def test_oferta_publicada_congela_condiciones_y_fechas_aun_sin_historial(self):
        self.curso.publicado = True
        self.curso.save(update_fields=["publicado"])
        self.assertFalse(self.curso.tiene_historial())
        salida = self.correr(aplicar=True)
        self.curso.refresh_from_db()
        self.edicion.refresh_from_db()
        self.clase.refresh_from_db()
        self.assertIn("oferta vigente", salida)
        self.assertTrue(self.curso.publicado)
        self.assertEqual(self.curso.inscripcion, "abierta")
        self.assertTrue(self.curso.emite_certificado)
        self.assertEqual(self.edicion.cupo, 20)
        self.assertEqual(self.edicion.inicio, date(2026, 11, 9))
        self.assertEqual(
            self.clase.fecha_hora, datetime(2026, 11, 11, 23, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(self.curso.instructores, odoo.CURSO["instructores"])
