"""Formularios de los formatos institucionales de prácticas."""

from copy import deepcopy

from django import forms
from django.db.models import Q

from apps.formacion.models.asignaturas import TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.gestion_unidades.models.espacios import ResponsableUnidad

from apps.reservas.workflows.reservas import ESTADOS_CERRADOS

from apps.formacion.presentation.practicas_integracion import construir_detalle_operativo, resumen_recursos


DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
TIME_INPUT = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


class PlanificacionPracticaForm(forms.ModelForm):
    CAMPOS_ORIGEN = ("actividad", "guia", "reserva")
    CAMPOS_PROGRAMACION = ("fecha", "hora_inicio", "hora_fin", "categoria_uso")
    CAMPOS_CONTEXTO = ("carrera", "semestre", "asignatura", "docente_tutor")
    CAMPOS_PRACTICA = (
        "tema_asignatura",
        "tema",
        "resultado_aprendizaje",
        "estudiantes_planificados",
    )
    CAMPOS_OPERACION = ("responsable_tecnico", "observaciones")

    class Meta:
        model = PlanificacionPractica
        fields = (
            "actividad",
            "guia",
            "reserva",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "carrera",
            "semestre",
            "asignatura",
            "docente_tutor",
            "tema_asignatura",
            "tema",
            "resultado_aprendizaje",
            "estudiantes_planificados",
            "categoria_uso",
            "responsable_tecnico",
            "observaciones",
        )
        widgets = {
            "fecha": DATE_INPUT,
            "hora_inicio": TIME_INPUT,
            "hora_fin": TIME_INPUT,
            "resultado_aprendizaje": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, unidad, actividades, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidad = unidad
        self.fields["actividad"].queryset = actividades.order_by("nombre")
        actividad_id = (
            self.data.get("actividad")
            or self.initial.get("actividad")
            or getattr(self.instance, "actividad_id", None)
        )
        self.fields["guia"].queryset = GuiaActividadReserva.objects.filter(
            actividad_id=actividad_id,
            es_estructurada=True,
            estado_publicacion="publicada",
            activo=True,
        ).order_by("-numero_version")
        self.fields["reserva"].queryset = (
            Reserva.objects.filter(
                laboratorio=unidad,
                actividad_catalogo_id=actividad_id,
            )
            .exclude(estado__in=("rechazada", "cancelada"))
            .order_by("fecha", "hora_inicio")
        )
        self.fields["responsable_tecnico"].queryset = ResponsableUnidad.objects.filter(
            unidad=unidad,
            usuario__isnull=False,
            activo=True,
        ).order_by("orden", "nombre")
        self.fields["guia"].required = False
        self.fields["reserva"].required = False
        self.fields["responsable_tecnico"].required = False
        # El vínculo con el syllabus: obligatorio en cuanto la unidad tiene
        # asignaturas con temas; sin ellas, la planificación sigue como antes.
        temas = (
            TemaAsignatura.objects.filter(
                asignatura__unidad=unidad,
                asignatura__activa=True,
            )
            .select_related("asignatura")
            .order_by("asignatura__nombre", "orden")
        )
        self.fields["tema_asignatura"].queryset = temas
        self.fields["tema_asignatura"].required = temas.exists()
        if temas.exists():
            # El tema del syllabus rellena tema, resultado, asignatura, carrera y
            # semestre; lo que siga vacío se exige en clean().
            for campo in ("tema", "resultado_aprendizaje", "asignatura"):
                self.fields[campo].required = False
        self.fields["tema_asignatura"].label = "Tema de la asignatura (syllabus)"
        # Con la unidad del syllabus delante, cuando el tema la tiene registrada.
        self.fields["tema_asignatura"].label_from_instance = lambda tema: " · ".join(
            parte
            for parte in (tema.asignatura.nombre, tema.unidad_tematica.strip(), tema.nombre)
            if parte
        )

    def _bound_fields(self, names):
        return [self[name] for name in names]

    @property
    def campos_origen(self):
        return self._bound_fields(self.CAMPOS_ORIGEN)

    @property
    def campos_programacion(self):
        return self._bound_fields(self.CAMPOS_PROGRAMACION)

    @property
    def campos_contexto(self):
        return self._bound_fields(self.CAMPOS_CONTEXTO)

    @property
    def campos_practica(self):
        return self._bound_fields(self.CAMPOS_PRACTICA)

    @property
    def campos_operacion(self):
        return self._bound_fields(self.CAMPOS_OPERACION)

    def clean(self):
        cleaned = super().clean()
        actividad = cleaned.get("actividad")
        if actividad and actividad.unidad_id not in {None, self.unidad.pk}:
            self.add_error("actividad", "La actividad no pertenece a esta unidad.")
        tema = cleaned.get("tema_asignatura")
        if tema is not None:
            # El tema del syllabus rellena lo que el docente no escribió: la
            # práctica queda con su asignatura, carrera y semestre, sin casillas vacías.
            asignatura = tema.asignatura
            heredados = (
                ("tema", tema.nombre[:240]),
                ("resultado_aprendizaje", tema.resultado_aprendizaje),
                ("asignatura", asignatura.nombre[:180]),
                ("carrera", asignatura.carrera),
                ("semestre", asignatura.semestre),
            )
            for campo, valor in heredados:
                if not (cleaned.get(campo) or "").strip() and valor:
                    cleaned[campo] = valor
        for campo in ("tema", "resultado_aprendizaje", "asignatura"):
            if (
                not self.fields[campo].required
                and not (cleaned.get(campo) or "").strip()
                and campo not in self.errors
            ):
                self.add_error(
                    campo, "Escríbelo o elige un tema del syllabus que lo traiga."
                )
        return cleaned


class EjecucionPracticaForm(forms.ModelForm):
    CAMPOS_GENERALES = (
        "fecha_ejecucion",
        "hora_inicio_real",
        "hora_fin_real",
        "resultado",
        "motivo",
        "estudiantes_asistentes",
        "tuvo_incidente",
        "incidencia",
        "cumplimiento_resultado",
        "responsable_tecnico",
        "observaciones_docente",
    )
    CAMPOS_RECURSOS = (
        "equipos_utilizados",
        "software_utilizado",
        "espacios_utilizados",
        "servicios_realizados",
    )

    class Meta:
        model = EjecucionPractica
        fields = (
            "fecha_ejecucion",
            "hora_inicio_real",
            "hora_fin_real",
            "resultado",
            "motivo",
            "estudiantes_asistentes",
            "tuvo_incidente",
            "incidencia",
            "observaciones_docente",
            "cumplimiento_resultado",
            "responsable_tecnico",
        )
        widgets = {
            "fecha_ejecucion": DATE_INPUT,
            "hora_inicio_real": TIME_INPUT,
            "hora_fin_real": TIME_INPUT,
            "motivo": forms.Textarea(attrs={"rows": 3}),
            "observaciones_docente": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, planificacion, **kwargs):
        super().__init__(*args, **kwargs)
        self.planificacion = planificacion
        unidad = planificacion.unidad
        reserva = planificacion.reserva
        self.cierre_operativo = reserva.estado in ESTADOS_CERRADOS
        self.fields["incidencia"].queryset = IncidenciaEquipo.objects.filter(
            unidad=unidad
        ).order_by("-fecha_reporte")
        self.fields["responsable_tecnico"].queryset = ResponsableUnidad.objects.filter(
            unidad=unidad,
            usuario__isnull=False,
            activo=True,
        ).order_by("orden", "nombre")
        self.fields["incidencia"].required = False
        self.fields["responsable_tecnico"].required = False
        self.fields["estudiantes_asistentes"].label = "Total real de asistentes"
        self.fields[
            "estudiantes_asistentes"
        ].help_text = "Incluye participantes nominales y, si aplica, estudiantes del grupo sin cuenta individual."

        detalle = {} if self.cierre_operativo else construir_detalle_operativo(reserva)
        guardado = self.instance.detalle_operativo if self.instance.pk else {}
        guardado = guardado if isinstance(guardado, dict) else {}
        cierre = (
            reserva.detalle_ejecucion
            if isinstance(reserva.detalle_ejecucion, dict)
            else {}
        )
        if self.cierre_operativo and not self.instance.pk:
            guardado = cierre
        self._detalle_cierre = deepcopy(guardado)
        self._recursos_cierre = (
            self.instance.recursos_utilizados
            if self.instance.pk
            else resumen_recursos(guardado)
        )
        if self.cierre_operativo and self.instance.responsable_tecnico_id:
            self.fields["responsable_tecnico"].queryset = (
                ResponsableUnidad.objects.filter(
                    unidad=unidad,
                )
                .filter(
                    Q(activo=True, usuario__isnull=False)
                    | Q(pk=self.instance.responsable_tecnico_id)
                )
                .order_by("orden", "nombre")
            )

        configuracion = (
            ("equipos_utilizados", "Equipos utilizados", "equipos"),
            ("software_utilizado", "Software utilizado", "software"),
            ("espacios_utilizados", "Espacios utilizados", "espacios"),
            ("servicios_realizados", "Servicios realizados", "servicios"),
        )
        for nombre_campo, etiqueta, clave in configuracion:
            elementos = (guardado if self.cierre_operativo else detalle).get(clave, [])
            choices = [
                (
                    str(item["id"]),
                    " · ".join(
                        value
                        for value in (
                            item.get("codigo", ""),
                            item.get("nombre", ""),
                            item.get("ubicacion", ""),
                        )
                        if value
                    ),
                )
                for item in elementos
            ]
            guardados = {
                str(item.get("id"))
                for item in guardado.get(clave, [])
                if item.get("id") is not None
            }
            self.fields[nombre_campo] = forms.MultipleChoiceField(
                label=etiqueta,
                choices=choices,
                required=False,
                widget=forms.CheckboxSelectMultiple,
                initial=sorted(guardados)
                if self.cierre_operativo
                else sorted(guardados) or [choice[0] for choice in choices],
            )

        participantes = (guardado if self.cierre_operativo else detalle).get(
            "participantes", []
        )
        asistieron = {
            str(item.get("id"))
            for item in guardado.get("participantes", [])
            if item.get("asistencia_codigo") == "asistio"
        }
        if not asistieron and not self.cierre_operativo:
            asistieron = {
                str(item["id"])
                for item in participantes
                if item.get("asistencia_codigo") != "no_asistio"
            }
        self.fields["participantes_asistentes"] = forms.MultipleChoiceField(
            label="Participantes que asistieron",
            choices=[
                (
                    str(item["id"]),
                    f"{item['nombre']} · {item['rol']}"
                    + (f" · {item['correo']}" if item.get("correo") else ""),
                )
                for item in participantes
            ],
            required=False,
            widget=forms.CheckboxSelectMultiple,
            initial=sorted(asistieron),
        )

        self._campos_consumibles = []
        for item in reserva.consumibles_solicitados.select_related("consumible"):
            nombre = f"consumo_{item.pk}"
            limite = item.cantidad_aprobada or item.cantidad_solicitada
            self.fields[nombre] = forms.DecimalField(
                label=f"{item.consumible.nombre} ({item.consumible.unidad_medida or 'unidades'})",
                required=False,
                min_value=0,
                max_digits=12,
                decimal_places=3,
                initial=item.cantidad_consumida,
                help_text=(
                    f"Máximo autorizado: {limite} {item.consumible.unidad_medida or 'unidades'}"
                    if limite is not None
                    else "Cantidad por confirmar durante la ejecución."
                ),
            )
            self._campos_consumibles.append(nombre)

        if self.cierre_operativo:
            protegidos = (
                set(self.CAMPOS_RECURSOS)
                | {"participantes_asistentes"}
                | set(self._campos_consumibles)
            )
            if self.instance.pk:
                protegidos.update(
                    set(self.CAMPOS_GENERALES)
                    - {"observaciones_docente", "cumplimiento_resultado"}
                )
            for nombre in protegidos:
                self.fields[nombre].disabled = True
                self.fields[
                    nombre
                ].help_text = "Dato conservado del cierre operativo; esta edición sólo completa documentación."

    @property
    def campos_generales(self):
        return [self[nombre] for nombre in self.CAMPOS_GENERALES]

    @property
    def campos_recursos(self):
        return [
            self[nombre]
            for nombre in self.CAMPOS_RECURSOS
            if self.fields[nombre].choices
        ]

    @property
    def campo_participantes(self):
        return self["participantes_asistentes"]

    @property
    def campos_consumibles(self):
        return [self[nombre] for nombre in self._campos_consumibles]

    def clean(self):
        cleaned = super().clean()
        if self.cierre_operativo:
            return cleaned
        for nombre in self._campos_consumibles:
            valor = cleaned.get(nombre)
            if valor is None:
                continue
            registro = self.planificacion.reserva.consumibles_solicitados.get(
                pk=int(nombre.rsplit("_", 1)[-1])
            )
            limite = registro.cantidad_aprobada or registro.cantidad_solicitada
            if limite is not None and valor > limite:
                self.add_error(nombre, f"El consumo no puede superar {limite}.")
        asistentes_identificados = len(cleaned.get("participantes_asistentes") or [])
        total = cleaned.get("estudiantes_asistentes") or 0
        if total < asistentes_identificados:
            self.add_error(
                "estudiantes_asistentes",
                "El total no puede ser menor que las personas marcadas como asistentes.",
            )
        return cleaned

    def aplicar_detalle_operativo(self, ejecucion):
        reserva = self.planificacion.reserva
        if self.cierre_operativo:
            ejecucion.detalle_operativo = deepcopy(self._detalle_cierre)
            ejecucion.recursos_utilizados = self._recursos_cierre
            return ejecucion.detalle_operativo
        if "detalle_operativo_registrado" in self.data:
            seleccion = {
                "equipos": set(self.cleaned_data.get("equipos_utilizados") or []),
                "software": set(self.cleaned_data.get("software_utilizado") or []),
                "espacios": set(self.cleaned_data.get("espacios_utilizados") or []),
                "servicios": set(self.cleaned_data.get("servicios_realizados") or []),
            }
            asistentes = set(self.cleaned_data.get("participantes_asistentes") or [])
            for participante in reserva.registros_participantes.all():
                participante.asistencia = (
                    "asistio" if str(participante.pk) in asistentes else "no_asistio"
                )
                participante.save(update_fields=["asistencia"])
        else:
            seleccion = None

        for nombre in self._campos_consumibles:
            if nombre not in self.data:
                continue
            registro = reserva.consumibles_solicitados.get(
                pk=int(nombre.rsplit("_", 1)[-1])
            )
            registro.cantidad_consumida = self.cleaned_data.get(nombre) or 0
            registro.save(update_fields=["cantidad_consumida"])
            registro.full_clean()

        detalle = construir_detalle_operativo(reserva, seleccion=seleccion)
        ejecucion.detalle_operativo = detalle
        ejecucion.recursos_utilizados = resumen_recursos(detalle)
        return detalle
