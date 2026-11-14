"""Retiro operativo documentado, sin sustituir la autorización patrimonial."""

from io import BytesIO
from pathlib import Path

from django import forms
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.recursos.models.unidades import UnidadEquipo


PREFIJO_CICLO = 'Retiro/sustitución: '
ALCANCE_RETIRO = 'Retiro de operación; no constituye autorización administrativa o patrimonial.'
CAMPOS_CICLO = ('fecha_baja', 'motivo_baja', 'observacion_baja', 'reemplazado_por_id')
SALT_CICLO = 'recursos.retiro.snapshot.v1'
VIGENCIA_SNAPSHOT = 24 * 60 * 60


def firmar_snapshot_ciclo(equipo, usuario):
    return signing.dumps({
        'esquema': 1, 'equipo_id': equipo.pk, 'actor_id': getattr(usuario, 'pk', None),
        'campos': instantanea(equipo, CAMPOS_CICLO) if equipo.pk else {},
    }, salt=SALT_CICLO, compress=True)


def leer_snapshot_ciclo(token, equipo, usuario):
    try:
        datos = signing.loads(token, salt=SALT_CICLO, max_age=VIGENCIA_SNAPSHOT)
        campos = datos.get('campos') if isinstance(datos, dict) else None
        if (not isinstance(datos, dict) or datos.get('esquema') != 1
                or datos.get('equipo_id') != equipo.pk or datos.get('actor_id') != getattr(usuario, 'pk', None)
                or not isinstance(campos, dict) or set(campos) != (set(CAMPOS_CICLO) if equipo.pk else set())):
            raise signing.BadSignature('El snapshot pertenece a otro activo o actor.')
    except (signing.BadSignature, TypeError, ValueError) as exc:
        raise ValidationError('La ficha de retiro perdió su vigencia o fue alterada. Recarga la página antes de guardar.') from exc
    return campos


def requiere_rectificacion(anteriores, nuevos):
    if not anteriores or not anteriores.get('fecha_baja'):
        return False
    return any(anteriores.get(campo) != nuevos.get(campo) for campo in CAMPOS_CICLO[:3]) or bool(
        anteriores.get('reemplazado_por_id')
        and anteriores.get('reemplazado_por_id') != nuevos.get('reemplazado_por_id'))


def validar_respaldo_retiro(archivo):
    """Un respaldo legible, sin presentar su mera carga como firma o aprobación."""
    if not archivo:
        return archivo
    if archivo.size > 25 * 1024 * 1024:
        raise ValidationError('El respaldo no puede superar 25 MB.')
    extension = Path(archivo.name).suffix.lower()
    posicion = archivo.tell()
    try:
        archivo.seek(0)
        if extension == '.pdf':
            from pypdf import PdfReader

            lector = PdfReader(archivo, strict=True)
            if lector.is_encrypted or not len(lector.pages):
                raise ValueError('PDF sin páginas accesibles')
        elif extension in ('.png', '.jpg', '.jpeg'):
            from PIL import Image

            with Image.open(BytesIO(archivo.read())) as imagen:
                if imagen.format not in ('PNG', 'JPEG'):
                    raise ValueError('Formato incorrecto')
                imagen.verify()
        else:
            raise ValueError('Extensión incorrecta')
    except Exception as exc:
        raise ValidationError('Adjunta un PDF sin contraseña o una imagen PNG/JPEG legible.') from exc
    finally:
        archivo.seek(posicion)
    return archivo


def guardar_ciclo_vida(equipo, usuario, *, evidencia=None, justificacion='', esperados=None):
    """Guarda el retiro/sustitución y conserva cada decisión como un evento nuevo.

    ``esperados`` es la instantánea del formulario: una edición concurrente
    exige recargarlo en vez de borrar silenciosamente una decisión posterior.
    """
    if not equipo.laboratorio_id:
        raise ValidationError('Asigna la unidad principal antes de documentar el retiro.')
    if not puede_operar_modulo_unidad(usuario, equipo.laboratorio, 'recursos'):
        raise PermissionDenied('Solo quien gestiona los recursos de la unidad documenta su retiro.')
    validar_respaldo_retiro(evidencia)
    archivo_creado = None
    try:
        with transaction.atomic():
            Unidad.objects.select_for_update().get(pk=equipo.laboratorio_id)
            previo = (UnidadEquipo.objects.select_for_update().get(pk=equipo.pk) if equipo.pk else None)
            if previo and previo.laboratorio_id != equipo.laboratorio_id:
                raise ValidationError('Transfiere el activo en una operación separada antes de registrar su retiro.')
            anteriores = instantanea(previo, CAMPOS_CICLO) if previo else {}
            nuevos = instantanea(equipo, CAMPOS_CICLO)
            if esperados is not None and anteriores != esperados:
                raise ValidationError('El ciclo de vida cambió mientras editabas. Recarga la ficha para revisarlo.')
            if requiere_rectificacion(anteriores, nuevos) and not str(justificacion or '').strip():
                raise ValidationError('Explica la rectificación del retiro o de la sustitución anterior.')
            if evidencia and not equipo.fecha_baja:
                raise ValidationError('El respaldo se adjunta a un retiro operativo registrado.')
            equipo._usuario_ciclo_vida = usuario
            equipo._justificacion_ciclo_vida = str(justificacion or '').strip()
            equipo._evidencia_ciclo_vida = evidencia
            equipo.save()
            archivo_creado = getattr(equipo, '_archivo_ciclo_vida_creado', None)
            registrar_auditoria(
                usuario=usuario, unidad=equipo.laboratorio, objeto=equipo, accion='actualizar' if previo else 'crear',
                descripcion=PREFIJO_CICLO + equipo.codigo_unidad,
                anteriores=anteriores,
                nuevos={**nuevos, 'justificacion_rectificacion': equipo._justificacion_ciclo_vida,
                        'alcance': ALCANCE_RETIRO, 'respaldo': archivo_creado[1] if archivo_creado else ''},
            )
    except Exception:
        archivo_creado = archivo_creado or getattr(equipo, '_archivo_ciclo_vida_creado', None)
        if archivo_creado:
            archivo_creado[0].delete(archivo_creado[1])
        raise
    finally:
        for atributo in ('_usuario_ciclo_vida', '_justificacion_ciclo_vida', '_evidencia_ciclo_vida',
                         '_archivo_ciclo_vida_creado'):
            equipo.__dict__.pop(atributo, None)
    return equipo


class UnidadEquipoCicloVidaForm(forms.ModelForm):
    ciclo_version = forms.CharField(required=False, widget=forms.HiddenInput)
    respaldo_retiro = forms.FileField(
        required=False, label='Respaldo del retiro o sustitución', validators=[validar_respaldo_retiro],
        help_text='Opcional: PDF, PNG o JPEG, hasta 25 MB. Se conserva en un evento con tu autoría; no acredita por sí solo autorización patrimonial.',
    )
    justificacion_rectificacion = forms.CharField(
        required=False, label='Motivo de rectificación', widget=forms.Textarea(attrs={'rows': 2}),
        help_text='Obligatorio si corriges o retiras un dato de baja ya registrado o cambias un sustituto anterior. El historial se conserva.',
    )

    class Meta:
        model = UnidadEquipo
        fields = '__all__'
        labels = {'fecha_baja': 'Fecha de retiro operativo', 'motivo_baja': 'Motivo técnico del retiro',
                  'observacion_baja': 'Justificación y referencia del retiro', 'reemplazado_por': 'Activo sustituto'}
        help_texts = {'observacion_baja': 'Documenta el diagnóstico, la referencia del respaldo y el destino previsto. El sistema no autoriza la baja patrimonial.'}

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.ciclo_actual = instantanea(self.instance, CAMPOS_CICLO) if self.instance.pk else {}
        self.ciclo_inicial = self.ciclo_actual
        self._error_snapshot = None
        if 'ciclo_version' in self.fields:
            if self.is_bound:
                try:
                    self.ciclo_inicial = leer_snapshot_ciclo(
                        self.data.get(self.add_prefix('ciclo_version'), ''), self.instance, usuario)
                except ValidationError as exc:
                    self._error_snapshot = exc
            else:
                self.initial['ciclo_version'] = firmar_snapshot_ciclo(self.instance, usuario)
        if 'reemplazado_por' not in self.fields:
            return
        unidad_id = self.instance.laboratorio_id
        if self.is_bound:
            try:
                unidad_id = int(self.data.get(self.add_prefix('laboratorio')) or 0) or None
            except (ValueError, TypeError):
                unidad_id = None
        sustitutos = UnidadEquipo.objects.filter(
            laboratorio_id=unidad_id, fecha_baja__isnull=True, activa=True,
            estado_unidad__in=('disponible', 'en_uso'),
        ) if unidad_id else UnidadEquipo.objects.none()
        if self.instance.reemplazado_por_id:
            sustitutos = UnidadEquipo.objects.filter(Q(pk__in=sustitutos.values('pk'))
                                                    | Q(pk=self.instance.reemplazado_por_id))
        if self.instance.pk:
            sustitutos = sustitutos.exclude(pk=self.instance.pk)
        self.fields['reemplazado_por'].queryset = sustitutos.select_related('equipo', 'laboratorio')

    def clean(self):
        datos = super().clean()
        self.instance._justificacion_ciclo_vida = datos.get('justificacion_rectificacion', '').strip()
        nuevos = dict(self.ciclo_inicial)
        for campo in CAMPOS_CICLO[:3]:
            if campo in datos:
                valor = datos[campo]
                nuevos[campo] = valor.isoformat() if hasattr(valor, 'isoformat') else valor
        if 'reemplazado_por' in datos:
            nuevos['reemplazado_por_id'] = getattr(datos['reemplazado_por'], 'pk', None)
        if requiere_rectificacion(self.ciclo_inicial, nuevos) and not self.instance._justificacion_ciclo_vida:
            self.add_error('justificacion_rectificacion', 'Explica por qué se rectifica el registro anterior.')
        unidad = datos.get('laboratorio')
        cambio = any(campo in self.changed_data for campo in (*CAMPOS_CICLO[:3], 'reemplazado_por', 'respaldo_retiro'))
        if cambio:
            if self._error_snapshot:
                self.add_error(None, self._error_snapshot)
            elif self.ciclo_inicial != self.ciclo_actual:
                self.add_error(None, 'El ciclo de vida cambió desde que abriste esta ficha. Recarga la página y revisa los cambios.')
        if cambio and self.usuario is not None and (not unidad or not puede_operar_modulo_unidad(self.usuario, unidad, 'recursos')):
            raise ValidationError('No tienes permiso para documentar el retiro de equipos de esta unidad.')
        if datos.get('respaldo_retiro') and not datos.get('fecha_baja'):
            self.add_error('respaldo_retiro', 'Registra primero la fecha del retiro operativo.')
        return datos
