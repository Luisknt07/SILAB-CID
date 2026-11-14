"""Carga programas LOG-FOR sin sustituir formación o eventos existentes.

--simular sólo SELECT; no transacciones, locks, secuencias ni generación de medios.
--aplicar respalda y bloquea Unidad antes de crear. Nunca retira ni sobrescribe.
--publicar sólo publica programas nuevos; no activa ediciones ni certificación.
"""

from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.formacion.management.commands.cargar_curso_precargado import guia_pdf
from apps.formacion.management.cursos_precargados.cursos_logistica_aplicada import PROGRAMAS
from apps.formacion.management.cursos_precargados.identidad import cursos_por_nombres, nombre_normalizado
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import SLUG
from apps.formacion.models.cursos import Curso, EdicionCurso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.directorio_unidades.models.core import Unidad


class Command(BaseCommand):
    help = "Carga siete programas metodológicos completos de logística con respaldo y preservación editorial."

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument(
            "--simular", action="store_true", help="Sólo SELECT; no genera medios."
        )
        modo.add_argument(
            "--aplicar",
            action="store_true",
            help="Crea sólo programas ausentes con respaldo previo.",
        )
        parser.add_argument(
            "--publicar",
            action="store_true",
            help="Publica sólo los nuevos; edición permanece inactiva.",
        )

    def handle(self, *args, **opciones):
        if opciones["publicar"] and not opciones["aplicar"]:
            raise CommandError(
                "--publicar requiere --aplicar; no cambia cursos existentes."
            )
        if not opciones["aplicar"]:
            unidad = self._unidad()
            nuevos, preservados = self._plan(unidad)
            self.stdout.write(
                f"[simulación SELECT] {len(nuevos)} programas nuevos; {len(preservados)} conservados íntegros. Sin archivos, convocatorias ni inscripciones."
            )
            return
        archivos_nuevos = []
        try:
            with transaction.atomic():
                unidad = self._unidad(bloquear=True)
                nuevos, preservados = self._plan(unidad)
                if nuevos:
                    respaldo = self._respaldar(unidad)
                    self.stdout.write("Respaldo previo: " + str(respaldo))
                    for programa in nuevos:
                        self._crear(
                            unidad, programa, opciones["publicar"], archivos_nuevos
                        )
                    registrar_auditoria(
                        unidad=unidad,
                        accion="crear",
                        objeto=unidad,
                        descripcion="LOG-FOR: programas metodológicos creados; sin matrícula ni certificación.",
                        nuevos={
                            "programas": len(nuevos),
                            "codigos": [p["codigo_contenido"] for p in nuevos],
                            "publicados": opciones["publicar"],
                        },
                    )
        except Exception:
            for storage, nombre in archivos_nuevos:
                storage.delete(nombre)
            raise
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(nuevos)} programas creados; {len(preservados)} conservados íntegros. Ediciones inactivas sin fechas ni cupo; certificación deshabilitada."
            )
        )

    @staticmethod
    def _unidad(bloquear=False):
        consulta = (
            Unidad.objects.select_for_update() if bloquear else Unidad.objects.all()
        )
        try:
            unidad = consulta.get(slug=SLUG)
        except Unidad.DoesNotExist as error:
            raise CommandError(
                "No existe el laboratorio de Logística; no se crea otra unidad."
            ) from error
        if unidad.codigo_base != "laboratorios":
            raise CommandError("La unidad debe conservar su tipo laboratorio.")
        return unidad

    @staticmethod
    def _plan(unidad):
        nuevos, preservados = [], []
        por_nombre = cursos_por_nombres(unidad, [p["CURSO"]["nombre"] for p in PROGRAMAS.values()])
        for programa in PROGRAMAS.values():
            codigo = programa["codigo_contenido"]
            existente = Curso.objects.filter(codigo=codigo).first()
            if existente and existente.unidad_id != unidad.pk:
                raise CommandError(
                    f"El código {codigo} pertenece a otra unidad; no se modifica."
                )
            if existente is None:
                pk = por_nombre.get(nombre_normalizado(programa["CURSO"]["nombre"]))
                existente = Curso.objects.filter(unidad=unidad, pk=pk).first() if pk else None
            if existente:
                preservados.append(existente)
            else:
                nuevos.append(programa)
        return nuevos, preservados

    @staticmethod
    def _respaldar(unidad):
        cursos = list(Curso.objects.filter(unidad=unidad))
        modulos = list(ModuloCurso.objects.filter(curso__unidad=unidad))
        lecciones = list(LeccionCurso.objects.filter(modulo__curso__unidad=unidad))
        preguntas = list(
            PreguntaEvaluacion.objects.filter(leccion__modulo__curso__unidad=unidad)
        )
        ediciones = list(EdicionCurso.objects.filter(curso__unidad=unidad))
        carpeta = Path(settings.BASE_DIR) / "var" / "backups"
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / (
            "logistica-formacion-"
            + timezone.now().strftime("%Y%m%dT%H%M%S%f")
            + ".json"
        )
        destino.write_text(
            serializers.serialize(
                "json",
                [unidad, *cursos, *modulos, *lecciones, *preguntas, *ediciones],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return destino

    @staticmethod
    def _crear(unidad, programa, publicar, archivos_nuevos):
        datos = {**programa["CURSO"], "publicado": publicar}
        curso = Curso(
            unidad=unidad,
            codigo=programa["codigo_contenido"],
            orden=200 + programa["numero_propuesta"],
            **datos,
        )
        curso.full_clean()
        curso.save()
        edicion = EdicionCurso(curso=curso, **programa["EDICION"])
        edicion.full_clean()
        edicion.save()
        textos = {
            titulo: campos.get("contenido", "")
            for _, _, lecciones in programa["MODULOS"]
            for _, titulo, campos in lecciones
        }
        for orden, (titulo, descripcion, lecciones) in enumerate(
            programa["MODULOS"], 1
        ):
            modulo = ModuloCurso(
                curso=curso, orden=orden, titulo=titulo, descripcion=descripcion
            )
            modulo.full_clean()
            modulo.save()
            for posicion, (tipo, titulo_leccion, campos) in enumerate(lecciones, 1):
                valores = {
                    k: v
                    for k, v in campos.items()
                    if k not in ("preguntas", "guia_pdf", "archivo_generado")
                }
                leccion = LeccionCurso(
                    modulo=modulo,
                    orden=posicion,
                    tipo=tipo,
                    titulo=titulo_leccion,
                    **valores,
                )
                if campos.get("archivo_generado"):
                    nombre, generar = campos["archivo_generado"]
                    leccion.archivo.save(nombre, ContentFile(generar()), save=False)
                    archivos_nuevos.append(
                        (leccion.archivo.storage, leccion.archivo.name)
                    )
                elif campos.get("guia_pdf"):
                    contenido = guia_pdf(
                        curso, titulo_leccion, campos["guia_pdf"], textos
                    )
                    leccion.archivo.save(
                        f"{curso.codigo.lower()}-{orden}.pdf",
                        ContentFile(contenido),
                        save=False,
                    )
                    archivos_nuevos.append(
                        (leccion.archivo.storage, leccion.archivo.name)
                    )
                leccion.full_clean()
                leccion.save()
                for numero, (tipo_p, enunciado, opciones, explicacion) in enumerate(
                    campos.get("preguntas", ()), 1
                ):
                    pregunta = PreguntaEvaluacion(
                        leccion=leccion,
                        orden=numero,
                        tipo=tipo_p,
                        enunciado=enunciado,
                        opciones=opciones,
                        explicacion=explicacion,
                    )
                    pregunta.full_clean()
                    pregunta.save()
