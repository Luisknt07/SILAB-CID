"""Formularios del flujo institucional de guías de práctica."""

import re

from django import forms
from django.db.models import Q

from apps.reservas.models.reservas import PROPOSITO_INSTITUCIONAL_CHOICES, SUBTIPO_ACTIVIDAD_CHOICES, CatalogoActividadReserva, Reserva

from apps.reservas.presentation.guia_automatizacion import datos_autocompletado_guia, politicas_guia_desde_reserva
from apps.reservas.presentation.guia_contenido import parrafos_procedimiento, texto_procedimiento_parrafos
from apps.reservas.presentation.guia_html import CAMPOS_RICOS, FORMATO_HTML, sanear_campo
from apps.reservas.presentation.guia_referencias import materiales_a_texto, normalizar_bibliografia, normalizar_materiales_complementarios


class GuiaPracticaForm(forms.Form):
    # Datos operativos: la reserva es la unica fuente valida y el autor de
    # la guia no puede reescribirlos como texto libre.
    CAMPOS_AUTOMATICOS_RESERVA = (
        'carrera_semestre', 'docente_responsable', 'categoria_uso',
        'duracion', 'maximo_estudiantes', 'equipos', 'software', 'materiales',
        'reactivos', 'manejo_residuos',
    )
    # Contenido academico que la reserva propone pero que redacta el docente:
    # el nombre oficial de la asignatura y las precauciones propias de la
    # actividad, que se suman a la politica de seguridad de la unidad.
    CAMPOS_ACADEMICOS_PROPUESTOS = ('asignatura', 'medidas_seguridad')
    actividad_existente = forms.ModelChoiceField(
        label='Actividad existente',
        queryset=CatalogoActividadReserva.objects.none(),
        required=False,
        empty_label='Crear una actividad nueva con esta guía',
    )
    proposito_codigo = forms.ChoiceField(
        label='Propósito institucional',
        choices=PROPOSITO_INSTITUCIONAL_CHOICES,
        required=False,
    )
    subtipo_actividad = forms.ChoiceField(
        label='Tipo de actividad',
        choices=SUBTIPO_ACTIVIDAD_CHOICES,
        required=False,
    )
    nombre_actividad = forms.CharField(
        label='Nombre de la actividad o práctica', max_length=220, required=False
    )
    codigo_actividad = forms.CharField(label='Código de la actividad', max_length=80, required=False)
    descripcion_actividad = forms.CharField(
        label='Descripción breve', required=False, widget=forms.Textarea(attrs={'rows': 2})
    )

    reserva_referencia = forms.ModelChoiceField(
        label='Reserva de referencia',
        queryset=Reserva.objects.none(),
        required=False,
        empty_label='Sin reserva: usar solo los datos de la actividad',
        help_text=(
            'Permite traer horario, participantes, equipos, software e insumos '
            'ya solicitados. La reserva no se modifica.'
        ),
    )

    titulo = forms.CharField(label='Título de la guía', max_length=220, required=False)
    codigo_guia = forms.CharField(label='Código de la guía', max_length=80, required=False)
    asignatura = forms.CharField(label='Asignatura o actividad formativa', max_length=220, required=False)
    carrera_semestre = forms.CharField(label='Carrera y semestre', max_length=220, required=False)
    docente_responsable = forms.CharField(label='Docente responsable', max_length=180, required=False)
    categoria_uso = forms.CharField(label='Categoría de uso', max_length=180, required=False)
    duracion = forms.CharField(label='Duración estimada', max_length=80, required=False)
    maximo_estudiantes = forms.IntegerField(
        label='Máximo de estudiantes', min_value=1, max_value=10000, required=False
    )
    resultado_aprendizaje = forms.CharField(
        label='Resultado de aprendizaje relacionado', required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    objetivos = forms.CharField(
        label='Objetivos de la práctica', required=False, widget=forms.Textarea(attrs={'rows': 4})
    )
    fundamento_teorico = forms.CharField(
        label='Fundamento teórico', required=False,
        help_text=(
            'Admite subtítulos (## Título), listas, tablas (líneas que empiezan con |) '
            'y figuras cargadas abajo (![Figura 1: título](figura:1)).'
        ),
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    equipos = forms.CharField(
        label='Equipos', required=False,
        help_text='Se completa desde la reserva; puedes ajustar un elemento por línea.',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    software = forms.CharField(
        label='Software y licencias', required=False,
        help_text='Se completa desde el software seleccionado en la reserva.',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    materiales = forms.CharField(
        label='Materiales e insumos', required=False,
        help_text='Escribe un elemento por línea.', widget=forms.Textarea(attrs={'rows': 4}),
    )
    reactivos = forms.CharField(
        label='Reactivos', required=False,
        help_text='Escribe un elemento por línea; deja vacío si no aplica.',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    medidas_seguridad = forms.CharField(
        label='Precauciones específicas de esta actividad', required=False,
        help_text=(
            'Escribe solo los riesgos propios de la práctica. La política de '
            'seguridad de la unidad se antepone automáticamente.'
        ),
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    procedimiento = forms.CharField(
        label='Procedimiento', required=False,
        help_text=(
            'En pasos o viñetas, escribe un elemento por línea. '
            'En párrafos, separa cada bloque con una línea vacía. '
            'Debajo de un paso puedes añadir una tabla (líneas que empiezan con |) '
            'o una figura (![Figura 1: título](figura:1)).'
        ),
        widget=forms.Textarea(attrs={'rows': 7}),
    )
    formato_procedimiento = forms.ChoiceField(
        label='Presentación del procedimiento',
        choices=(
            ('numerado', 'Pasos numerados (recomendado por el FT04)'),
            ('vinetas', 'Viñetas'),
            ('parrafos', 'Párrafos'),
        ),
        initial='numerado',
        required=False,
        widget=forms.RadioSelect,
    )
    resultados_esperados = forms.CharField(
        label='Resultados esperados', required=False, widget=forms.Textarea(attrs={'rows': 4})
    )
    criterios_evaluacion = forms.CharField(
        label='Criterios de evaluación', required=False, widget=forms.Textarea(attrs={'rows': 4})
    )
    manejo_residuos = forms.CharField(
        label='Manejo de residuos', required=False,
        help_text='Indica «No aplica» cuando corresponda.', widget=forms.Textarea(attrs={'rows': 3}),
    )
    bibliografia = forms.CharField(
        label='Bibliografía', required=False,
        help_text=(
            'Una referencia por línea o entradas BibTeX (@article{...}, @book{...}); '
            'se presentan numeradas en estilo IEEE.'
        ),
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    materiales_complementarios = forms.CharField(
        label='Materiales complementarios', required=False,
        help_text='Un recurso por línea: Título | https://enlace (videos, lecturas, datos, simuladores).',
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    permite_descarga = forms.BooleanField(label='Permitir descarga del PDF aprobado', required=False)
    solicita_publicacion = forms.BooleanField(
        label='Solicitar publicación para la comunidad de la unidad', required=False
    )
    # "html": los apartados de redaccion llegan del editor visual como HTML
    # acotado; vacio: formato de texto anterior (compatibilidad).
    formato_contenido = forms.CharField(required=False, widget=forms.HiddenInput)

    CONTENT_FIELDS = (
        'asignatura', 'carrera_semestre', 'docente_responsable', 'categoria_uso',
        'duracion', 'maximo_estudiantes', 'resultado_aprendizaje', 'objetivos',
        'fundamento_teorico', 'equipos', 'software', 'materiales', 'reactivos',
        'medidas_seguridad', 'formato_procedimiento', 'procedimiento', 'resultados_esperados',
        'criterios_evaluacion', 'manejo_residuos', 'bibliografia',
        'materiales_complementarios',
    )
    LIST_FIELDS = {
        'equipos', 'software', 'materiales', 'reactivos', 'procedimiento', 'bibliografia'
    }

    def __init__(
        self, *args, unidad, usuario, guia=None, operador=False, figuras_permitidas=(), **kwargs,
    ):
        self.unidad = unidad
        self.usuario = usuario
        self.guia = guia
        self.operador = operador
        # Figuras que el contenido HTML puede citar (las de la guia y las del
        # borrador de esta persona); cualquier otra se elimina al sanear.
        self.figuras_permitidas = set(figuras_permitidas or ())
        super().__init__(*args, **kwargs)
        actividades = CatalogoActividadReserva.objects.filter(unidad=unidad, activo=True)
        if not operador:
            actividades = actividades.filter(
                Q(creado_por=usuario)
                | Q(participantes_autorizados=usuario)
                | Q(estado_publicacion='publicado', visibilidad__in={'unidad', 'institucional'})
            ).distinct()
        actividades = actividades.select_related('creado_por').order_by('-actualizado_en', 'nombre')
        if guia:
            actividades = CatalogoActividadReserva.objects.filter(pk=guia.actividad_id)
        self.fields['actividad_existente'].queryset = actividades

        reservas = Reserva.objects.filter(
            laboratorio=unidad,
            actividad_catalogo__isnull=False,
        ).select_related('actividad_catalogo', 'actividad_catalogo__creado_por', 'usuario')
        if guia:
            reservas = reservas.filter(actividad_catalogo=guia.actividad)
        elif not operador:
            reservas = reservas.filter(
                Q(usuario=usuario)
                | Q(actividad_catalogo__creado_por=usuario)
                | Q(participantes=usuario)
            ).distinct()
        reservas = reservas.prefetch_related(
            'software_solicitado', 'consumibles_solicitados__consumible'
        ).order_by('-fecha', '-hora_inicio', '-pk')
        self.fields['reserva_referencia'].queryset = reservas

        for field in self.fields.values():
            css = 'guia-form__control'
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'guia-form__check'
            field.widget.attrs['class'] = css

        if guia and not self.is_bound:
            actividad = guia.actividad
            contenido_guia = guia.contenido or {}
            self.initial.update({
                'actividad_existente': actividad,
                'proposito_codigo': actividad.proposito_codigo,
                'subtipo_actividad': actividad.subtipo_actividad,
                'nombre_actividad': actividad.nombre,
                'codigo_actividad': actividad.codigo,
                'descripcion_actividad': actividad.descripcion,
                'titulo': guia.titulo,
                'codigo_guia': guia.codigo_guia,
                'permite_descarga': guia.permite_descarga,
                'solicita_publicacion': guia.solicita_publicacion,
                'reserva_referencia': contenido_guia.get('reserva_fuente_id'),
                'formato_procedimiento': contenido_guia.get('formato_procedimiento') or 'numerado',
                'formato_contenido': contenido_guia.get('formato_contenido', ''),
            })
            for key in self.CONTENT_FIELDS:
                value = contenido_guia.get(key, '')
                if key == 'bibliografia' and contenido_guia.get('bibliografia_fuente'):
                    # Se edita la fuente (BibTeX o texto), no el resultado IEEE.
                    value = contenido_guia['bibliografia_fuente']
                elif key == 'materiales_complementarios':
                    value = materiales_a_texto(value)
                if key in self.LIST_FIELDS and isinstance(value, list):
                    if key == 'procedimiento' and contenido_guia.get('formato_procedimiento') == 'parrafos':
                        value = texto_procedimiento_parrafos(value)
                    else:
                        value = '\n'.join(str(item) for item in value)
                self.initial[key] = value

        if not self.is_bound:
            self.initial.setdefault('formato_procedimiento', 'numerado')

        if not self.is_bound:
            reserva_inicial = self.initial.get('reserva_referencia')
            if reserva_inicial:
                reserva = (
                    reserva_inicial
                    if isinstance(reserva_inicial, Reserva)
                    else reservas.filter(pk=reserva_inicial).first()
                )
                if reserva:
                    self.initial['reserva_referencia'] = reserva
                    self.initial['actividad_existente'] = reserva.actividad_catalogo
                    self._aplicar_inicial_automatico(
                        datos_autocompletado_guia(reserva.actividad_catalogo, reserva)
                    )

        self.reserva_bloqueada = bool(
            guia
            and isinstance(guia.contenido, dict)
            and guia.contenido.get('reserva_fuente_id')
        )
        if self.reserva_bloqueada:
            contenido_guia = guia.contenido or {}
            # Un documento vinculado no puede separarse de su solicitud ni
            # convertir datos operativos en texto libre. Django ignora incluso
            # un POST manipulado para los campos marcados como ``disabled``.
            self.fields['reserva_referencia'].disabled = True
            self.initial['reserva_referencia'] = contenido_guia.get('reserva_fuente_id')
            for clave in self.CAMPOS_AUTOMATICOS_RESERVA:
                self.fields[clave].disabled = True
                valor = contenido_guia.get(clave, '')
                if clave in self.LIST_FIELDS and isinstance(valor, list):
                    valor = '\n'.join(str(item) for item in valor)
                self.initial[clave] = valor
            # La seguridad se guarda ya combinada. El formulario muestra
            # unicamente las precauciones escritas por el autor para que no
            # vuelva a editar ni duplicar la politica de la unidad. En el
            # formato HTML el apartado ya contiene solo lo que escribio el autor.
            if contenido_guia.get('formato_contenido') != FORMATO_HTML:
                self.initial['medidas_seguridad'] = '\n'.join(
                    self._precauciones_del_autor(contenido_guia.get('medidas_seguridad'))
                )

        self.autocompletado = {
            'actividades': {
                str(actividad.pk): datos_autocompletado_guia(actividad, None)
                for actividad in actividades
            },
            'reservas': {
                str(reserva.pk): {
                    **datos_autocompletado_guia(reserva.actividad_catalogo, reserva),
                    'actividad_id': reserva.actividad_catalogo_id,
                    'etiqueta': str(reserva),
                }
                for reserva in reservas
            },
        }

    def _precauciones_del_autor(self, valor, *, institucionales=None):
        """Separa lo que escribio el autor de la politica de la unidad.

        El apartado de seguridad se almacena combinado. Para volver a mostrarlo
        o guardarlo sin duplicar, se descartan las lineas que ya pertenecen a la
        politica institucional vigente de la unidad.
        """
        if isinstance(valor, (list, tuple)):
            lineas = [str(item).strip() for item in valor]
        else:
            lineas = [linea.strip() for linea in str(valor or '').splitlines()]
        if institucionales is None:
            institucionales = []
            reserva = getattr(self, 'guia', None)
            contenido = getattr(reserva, 'contenido', None) if reserva else None
            if isinstance(contenido, dict):
                politicas = self._politicas_institucionales_de(contenido)
                institucionales = politicas
        conocidas = {str(item).strip() for item in institucionales if str(item).strip()}
        return [linea for linea in lineas if linea and linea not in conocidas]

    def _politicas_institucionales_de(self, contenido):
        """Politica de seguridad vigente de la unidad para la guia en edicion."""
        reserva_id = contenido.get('reserva_fuente_id')
        if not reserva_id:
            return []
        reserva = Reserva.objects.filter(pk=reserva_id).first()
        if not reserva:
            return []
        return [
            str(item).strip()
            for item in politicas_guia_desde_reserva(reserva).get('seguridad', [])
            if str(item).strip()
        ]

    def _aplicar_inicial_automatico(self, datos):
        for clave in (
            'titulo', 'codigo_guia', 'asignatura', 'carrera_semestre',
            'docente_responsable', 'categoria_uso', 'duracion',
            'maximo_estudiantes', 'equipos', 'software', 'materiales', 'reactivos',
        ):
            if self.initial.get(clave) not in (None, '', []):
                continue
            valor = datos.get(clave, '')
            if clave in self.LIST_FIELDS and isinstance(valor, list):
                valor = '\n'.join(str(item) for item in valor)
            self.initial[clave] = valor

    def clean(self):
        cleaned = super().clean()
        actividad = cleaned.get('actividad_existente')
        reserva = cleaned.get('reserva_referencia')
        if reserva:
            if reserva.laboratorio_id != self.unidad.pk:
                self.add_error('reserva_referencia', 'La reserva no pertenece a esta unidad.')
            if actividad and reserva.actividad_catalogo_id != actividad.pk:
                self.add_error(
                    'reserva_referencia',
                    'La reserva elegida no corresponde a la actividad seleccionada.',
                )
            elif not actividad:
                actividad = reserva.actividad_catalogo
                cleaned['actividad_existente'] = actividad
        if actividad and actividad.unidad_id != self.unidad.pk:
            self.add_error('actividad_existente', 'La actividad no pertenece a esta unidad.')
        if not actividad:
            for key in ('proposito_codigo', 'subtipo_actividad', 'nombre_actividad'):
                if not cleaned.get(key):
                    self.add_error(key, 'Este dato es necesario para crear la actividad.')
        if actividad:
            automaticos = datos_autocompletado_guia(actividad, reserva)
            for clave in (
                'titulo', 'codigo_guia', 'asignatura', 'carrera_semestre',
                'docente_responsable', 'categoria_uso', 'duracion',
                'maximo_estudiantes', 'equipos', 'software', 'materiales', 'reactivos',
            ):
                if cleaned.get(clave) in (None, '', []):
                    valor = automaticos.get(clave, '')
                    if clave in self.LIST_FIELDS and isinstance(valor, list):
                        valor = '\n'.join(str(item) for item in valor)
                    cleaned[clave] = valor
            if reserva:
                # La reserva es la fuente de verdad. Los recursos, personas,
                # horarios y políticas de la unidad no son declaración libre
                # del autor de la guía.
                for clave in self.CAMPOS_AUTOMATICOS_RESERVA:
                    valor = automaticos.get(clave, '')
                    if clave in self.LIST_FIELDS and isinstance(valor, list):
                        valor = '\n'.join(str(item) for item in valor)
                    cleaned[clave] = valor
                cleaned['reactivos'] = ''
                residuos = automaticos.get('manejo_residuos', [])
                cleaned['manejo_residuos'] = (
                    '\n'.join(str(item) for item in residuos)
                    if isinstance(residuos, list) else residuos
                )
                # La politica de la unidad encabeza siempre el apartado y
                # despues se agregan las precauciones propias de la
                # actividad. Se descartan las lineas institucionales que ya
                # venian en el texto para que reeditar la guia no las duplique.
                institucionales = automaticos.get('seguridad', [])
                if not isinstance(institucionales, (list, tuple)):
                    institucionales = [
                        linea.strip()
                        for linea in str(institucionales or '').splitlines()
                        if linea.strip()
                    ]
                institucionales = [str(item).strip() for item in institucionales if str(item).strip()]
                if cleaned.get('formato_contenido') == FORMATO_HTML:
                    # El editor visual guarda aparte la politica institucional;
                    # el apartado conserva solo lo que redacta el autor.
                    cleaned['seguridad_institucional'] = institucionales
                else:
                    propias = self._precauciones_del_autor(
                        cleaned.get('medidas_seguridad'), institucionales=institucionales
                    )
                    cleaned['medidas_seguridad'] = '\n'.join([*institucionales, *propias])
        if not cleaned.get('titulo'):
            self.add_error('titulo', 'Escribe o genera el título de la guía.')
        return cleaned

    def contenido_normalizado(self):
        contenido = {}
        formato_procedimiento = self.cleaned_data.get('formato_procedimiento') or 'numerado'
        es_html = self.cleaned_data.get('formato_contenido') == FORMATO_HTML
        for key in self.CONTENT_FIELDS:
            value = self.cleaned_data.get(key)
            if es_html and key in CAMPOS_RICOS:
                # Saneado por lista blanca; nunca se guarda HTML sin pasar por aqui.
                value = sanear_campo(key, value or '', self.figuras_permitidas)
                if key == 'procedimiento' and formato_procedimiento == 'parrafos':
                    value = sanear_campo('fundamento_teorico', self.cleaned_data.get(key) or '', self.figuras_permitidas)
            elif key == 'procedimiento':
                texto = value or ''
                if formato_procedimiento == 'parrafos':
                    value = parrafos_procedimiento(texto)
                else:
                    value = [
                        re.sub(r'^\s*(?:\d+[.)]|[-*\u2022])\s*', '', linea).strip()
                        for linea in texto.splitlines()
                        if re.sub(r'^\s*(?:\d+[.)]|[-*\u2022])\s*', '', linea).strip()
                    ]
            elif key == 'bibliografia':
                contenido['bibliografia_fuente'] = value or ''
                value = normalizar_bibliografia(value)
            elif key == 'materiales_complementarios':
                value = normalizar_materiales_complementarios(value)
            elif key in self.LIST_FIELDS:
                value = [line.strip() for line in (value or '').splitlines() if line.strip()]
            contenido[key] = value or ''
        contenido['laboratorio'] = self.unidad.nombre
        if es_html:
            contenido['formato_contenido'] = FORMATO_HTML
            contenido['seguridad_institucional'] = list(self.cleaned_data.get('seguridad_institucional') or [])
        reserva = self.cleaned_data.get('reserva_referencia')
        actividad = self.cleaned_data.get('actividad_existente')
        automaticos = datos_autocompletado_guia(actividad, reserva) if actividad else {}
        contenido['reserva_fuente_id'] = reserva.pk if reserva else None
        contenido['reserva_fuente_codigo'] = reserva.codigo_reserva if reserva else ''
        contenido['origen_campos'] = {
            clave: (
                'reserva' if reserva and automaticos.get(clave) not in (None, '', [])
                else 'actividad' if automaticos.get(clave) not in (None, '', [])
                else 'manual'
            )
            for clave in self.CONTENT_FIELDS
        }
        return contenido
