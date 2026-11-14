"""Actualiza exclusivamente campos de la precarga Odoo que conservan su original.

No invoca el cargador de cursos, no genera adjuntos y no crea, retira, reordena ni
publica entidades. La línea base versionada permite desplegar sin acceso a Git.
--simular (o sin opciones) realiza únicamente SELECT y no escribe archivos.
"""

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.formacion.management.cursos_precargados import odoo
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import SLUG
from apps.formacion.models.cursos import Curso, EdicionCurso, LeccionCurso, ModuloCurso
from apps.directorio_unidades.models.core import Unidad

BASELINE = (
    Path(__file__).resolve().parents[1] / "laboratorios" / "logistica_erp_baseline.json"
)
CODIGO_REFERENCIA = "LOG-CUR-001"
CAMPOS_CURSO = (
    "lema",
    "descripcion",
    "aprendizajes",
    "dirigido_a",
    "requisitos",
    "instructores",
    "video_url",
    "duracion_horas",
    "inscripcion",
    "emite_certificado",
    "clasificacion",
    "modalidad",
)
CONDICIONES_CURSO = frozenset(
    ("duracion_horas", "inscripcion", "emite_certificado", "clasificacion", "modalidad")
)
CAMPOS_EDICION = (
    "inicio",
    "fin",
    "inscripciones_desde",
    "inscripciones_hasta",
    "cupo",
    "horario",
    "lugar",
)
CAMPOS_MODULO = ("descripcion",)
CAMPOS_LECCION = (
    "contenido",
    "video_url",
    "enlace",
    "lugar",
    "duracion_min",
    "fecha_hora",
    "fecha_limite",
    "sala",
    "reunion_url",
    "nota_minima",
    "intentos",
    "obligatoria",
)
CONDICIONES_LECCION = frozenset(
    (
        "fecha_hora",
        "fecha_limite",
        "lugar",
        "duracion_min",
        "sala",
        "reunion_url",
        "enlace",
        "nota_minima",
        "intentos",
        "obligatoria",
    )
)
CAMPOS_FECHA = frozenset(
    ("inicio", "fin", "inscripciones_desde", "inscripciones_hasta")
)
CAMPOS_DATETIME = frozenset(("fecha_hora", "fecha_limite"))


def normalizar_valor(valor, campo=""):
    """Representación canónica: instantes equivalentes, fechas y JSON comparables."""
    if valor is not None and campo in CAMPOS_DATETIME and isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor is not None and campo in CAMPOS_FECHA and isinstance(valor, str):
        valor = date.fromisoformat(valor)
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=ZoneInfo("America/Guayaquil"))
        return {
            "datetime_utc": valor.astimezone(datetime_timezone.utc).isoformat(
                timespec="microseconds"
            )
        }
    if isinstance(valor, date):
        return {"date": valor.isoformat()}
    if isinstance(valor, Decimal):
        return {"decimal": format(valor.normalize(), "f")}
    if isinstance(valor, dict):
        return {str(clave): normalizar_valor(dato) for clave, dato in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar_valor(dato) for dato in valor]
    return valor


def huella_valor(valor, campo=""):
    texto = json.dumps(
        normalizar_valor(valor, campo),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cargar_baseline():
    try:
        datos = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError(
            "No se puede leer la línea base versionada de Odoo."
        ) from exc
    if (
        datos.get("version") != 1
        or datos.get("slug") != SLUG
        or datos.get("curso_nombre") != odoo.CURSO["nombre"]
        or len(datos.get("modulos", [])) != len(odoo.MODULOS)
    ):
        raise CommandError(
            "La línea base no corresponde a este paquete Odoo; revisar antes de actualizar."
        )
    return datos


class Command(BaseCommand):
    help = "Actualiza la precarga ERP de Logística preservando ediciones manuales, participantes e historial."

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument(
            "--simular",
            action="store_true",
            help="Sólo consulta; no crea archivos ni bloqueos.",
        )
        modo.add_argument(
            "--aplicar",
            action="store_true",
            help="Actualiza campos reconocidos con respaldo previo.",
        )

    def handle(self, *args, **opciones):
        baseline = cargar_baseline()
        if not opciones["aplicar"]:
            unidad, curso, objetos = self._obtener(baseline, bloquear=False)
            cambios, resumen, avisos = self._planificar(curso, objetos, baseline)
            self._informar(curso, resumen, avisos, simular=True)
            return
        with transaction.atomic():
            unidad, curso, objetos = self._obtener(baseline, bloquear=True)
            cambios, resumen, avisos = self._planificar(curso, objetos, baseline)
            if cambios:
                respaldo = self._respaldar(
                    [
                        unidad,
                        curso,
                        *objetos["ediciones"],
                        *objetos["modulos"],
                        *objetos["lecciones"],
                    ],
                    baseline,
                )
                self.stdout.write("Respaldo previo: " + str(respaldo))
                anteriores, nuevos = [], []
                for objeto, valores in cambios:
                    anteriores.append(
                        {
                            "entidad": objeto._meta.label,
                            "id": objeto.pk,
                            "campos": {
                                campo: normalizar_valor(getattr(objeto, campo), campo)
                                for campo in valores
                            },
                        }
                    )
                    nuevos.append(
                        {
                            "entidad": objeto._meta.label,
                            "id": objeto.pk,
                            "campos": {
                                campo: normalizar_valor(valor, campo)
                                for campo, valor in valores.items()
                            },
                        }
                    )
                    for campo, valor in valores.items():
                        setattr(objeto, campo, valor)
                    # Sólo campos autorizados: sin auto_now, orden, relaciones ni estado.
                    objeto.save(update_fields=list(valores))
                registrar_auditoria(
                    unidad=unidad,
                    accion="actualizar",
                    objeto=curso,
                    descripcion="LOG-ERP: revisión de precarga propia; conserva edición manual e historial",
                    anteriores={
                        "campos": anteriores,
                        "baseline": baseline["source_git_commit"],
                    },
                    nuevos={"campos": nuevos},
                )
        self._informar(curso, resumen, avisos, simular=False)

    @staticmethod
    def _obtener(baseline, *, bloquear):
        def consultar(queryset):
            return queryset.select_for_update() if bloquear else queryset

        unidad = consultar(Unidad.objects.filter(slug=SLUG)).first()
        if unidad is None or unidad.codigo_base != "laboratorios":
            raise CommandError(
                "No existe el laboratorio de Logística con su tipo institucional; no se crea otra unidad."
            )
        candidatos = list(
            consultar(
                Curso.objects.filter(
                    unidad=unidad, nombre=baseline["curso_nombre"]
                ).order_by("pk")
            )
        )
        if len(candidatos) != 1:
            raise CommandError(
                "Debe existir un único curso Odoo con su nombre original en esta unidad; no se crean ni renombran cursos."
            )
        curso = candidatos[0]
        if curso.origen != "nativo":
            raise CommandError(
                "El curso ahora es externo; se conserva y requiere revisión manual."
            )
        objetos = {
            "ediciones": list(
                consultar(EdicionCurso.objects.filter(curso=curso).order_by("pk"))
            ),
            "modulos": list(
                consultar(ModuloCurso.objects.filter(curso=curso).order_by("pk"))
            ),
            "lecciones": list(
                consultar(
                    LeccionCurso.objects.filter(modulo__curso=curso).order_by("pk")
                )
            ),
        }
        return unidad, curso, objetos

    @staticmethod
    def _campos(objeto, originales, nuevos, permitidos, *, bloqueados=frozenset()):
        cambios, resumen, avisos = {}, Counter(), []
        for campo in permitidos:
            anterior_hash = originales.get(campo)
            if not anterior_hash:
                continue
            field = objeto._meta.get_field(campo)
            nuevo = nuevos.get(campo, field.get_default())
            nuevo = field.to_python(nuevo)
            actual = getattr(objeto, campo)
            if huella_valor(actual, campo) == huella_valor(nuevo, campo):
                continue
            if campo in bloqueados:
                resumen["campos conservados por oferta vigente o historial"] += 1
                avisos.append(
                    str(objeto)
                    + " · "
                    + campo
                    + ": se conserva por publicación, participantes o historial."
                )
            elif huella_valor(actual, campo) != anterior_hash:
                resumen["campos editados conservados"] += 1
                avisos.append(
                    str(objeto)
                    + " · "
                    + campo
                    + ": edición manual o valor de otra versión conservado."
                )
            else:
                # Valida el campo nuevo sin invalidar otros datos históricos del objeto.
                cambios[campo] = field.clean(nuevo, objeto)
                resumen["campos actualizables"] += 1
        return cambios, resumen, avisos

    def _planificar(self, curso, objetos, baseline):
        resumen, avisos, cambios = Counter(), [], []
        lecciones_usadas = set(
            LeccionCurso.objects.filter(modulo__curso=curso)
            .filter(
                Q(progresos__isnull=False)
                | Q(intentos_rendidos__isnull=False)
                | Q(entregas__isnull=False)
                | Q(comentarios__isnull=False)
            )
            .values_list("pk", flat=True)
            .distinct()
        )
        con_historial = curso.tiene_historial() or bool(lecciones_usadas)
        proteger_condiciones = con_historial or curso.publicado

        def agregar(objeto, originales, nuevos, permitidos, bloqueados=frozenset()):
            valores, conteo, advertencias = self._campos(
                objeto, originales, nuevos, permitidos, bloqueados=bloqueados
            )
            resumen.update(conteo)
            avisos.extend(advertencias)
            if valores:
                cambios.append((objeto, valores))
                resumen["registros actualizables"] += 1

        agregar(
            curso,
            baseline["curso_campos"],
            odoo.CURSO,
            CAMPOS_CURSO,
            CONDICIONES_CURSO if proteger_condiciones else frozenset(),
        )
        ediciones = [
            x for x in objetos["ediciones"] if x.nombre == baseline["edicion_nombre"]
        ]
        if len(ediciones) == 1:
            agregar(
                ediciones[0],
                baseline["edicion_campos"],
                odoo.EDICION,
                CAMPOS_EDICION,
                frozenset(CAMPOS_EDICION) if proteger_condiciones else frozenset(),
            )
        else:
            resumen["identidades ausentes conservadas"] += 1
            avisos.append(
                "La edición original no está disponible de forma unívoca; no se crea ni modifica otra edición."
            )
        for original, nuevo in zip(baseline["modulos"], odoo.MODULOS, strict=True):
            titulo, descripcion, lecciones_nuevas = nuevo
            if titulo != original["titulo"] or len(lecciones_nuevas) != len(
                original["lecciones"]
            ):
                raise CommandError(
                    "Cambió la estructura fuente del curso; esta actualización no puede insertar ni reordenar módulos/lecciones."
                )
            modulos = [x for x in objetos["modulos"] if x.titulo == original["titulo"]]
            if len(modulos) != 1:
                resumen["identidades ausentes conservadas"] += 1
                avisos.append(
                    "Módulo ausente, renombrado o duplicado conservado: "
                    + original["titulo"]
                )
                continue
            modulo = modulos[0]
            agregar(
                modulo, original["campos"], {"descripcion": descripcion}, CAMPOS_MODULO
            )
            for leccion_original, leccion_nueva in zip(
                original["lecciones"], lecciones_nuevas, strict=True
            ):
                tipo, titulo_leccion, campos = leccion_nueva
                if (
                    titulo_leccion != leccion_original["titulo"]
                    or tipo != leccion_original["tipo"]
                ):
                    raise CommandError(
                        "Cambió la identidad fuente de una lección; se requiere una actualización editorial revisada."
                    )
                lecciones = [
                    x
                    for x in objetos["lecciones"]
                    if x.modulo_id == modulo.pk
                    and x.titulo == leccion_original["titulo"]
                ]
                if len(lecciones) != 1 or lecciones[0].tipo != tipo:
                    resumen["identidades ausentes conservadas"] += 1
                    avisos.append(
                        "Lección ausente, movida, renombrada, duplicada o de otro tipo conservada: "
                        + titulo_leccion
                    )
                    continue
                leccion = lecciones[0]
                bloqueados = set(CONDICIONES_LECCION) if proteger_condiciones else set()
                if leccion.pk in lecciones_usadas:
                    bloqueados.update(CAMPOS_LECCION)
                agregar(
                    leccion,
                    leccion_original["campos"],
                    campos,
                    CAMPOS_LECCION,
                    bloqueados,
                )
        return cambios, resumen, avisos

    @staticmethod
    def _respaldar(objetos, baseline):
        carpeta = Path(settings.BASE_DIR) / "var" / "backups"
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / (
            "logistica-erp-" + timezone.now().strftime("%Y%m%dT%H%M%S%f") + ".json"
        )
        respaldo = {
            "baseline_commit": baseline["source_git_commit"],
            "baseline_source_sha256": baseline["source_sha256"],
            "registros": json.loads(
                serializers.serialize("json", objetos, ensure_ascii=False)
            ),
        }
        with destino.open("x", encoding="utf-8") as archivo:
            json.dump(respaldo, archivo, ensure_ascii=False, indent=2)
        return destino

    def _informar(self, curso, resumen, avisos, *, simular):
        for aviso in avisos:
            self.stdout.write(self.style.WARNING(aviso))
        if curso.codigo != CODIGO_REFERENCIA:
            self.stdout.write(
                "Identificado por nombre original en la unidad; código actual conservado: "
                + curso.codigo
            )
        detalle = (
            ", ".join(
                str(cantidad) + " " + nombre
                for nombre, cantidad in sorted(resumen.items())
                if cantidad
            )
            or "sin cambios"
        )
        prefijo = "[simulación SELECT] " if simular else ""
        self.stdout.write(
            self.style.SUCCESS(prefijo + curso.codigo + " · " + detalle + ".")
        )
