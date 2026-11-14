"""Identidades locales de Centros I+D; la autenticación sigue en su base canónica.

La proyección conserva el ID institucional y los datos de presentación, nunca
contraseñas, grupos ni privilegios. Las FK de Centros solo apuntan a esta copia.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, models, router
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor
from django.utils.functional import cached_property

CAMPOS_PUBLICOS = ('username', 'first_name', 'last_name', 'email', 'is_active')


def alias_identidades():
    return router.db_for_read(get_user_model()) or DEFAULT_DB_ALIAS


def alias_centros(instancia=None):
    from .models import CuentaCentro
    return router.db_for_write(CuentaCentro, instance=instancia) or DEFAULT_DB_ALIAS


def principal_vigente(principal):
    """Resuelve autorización en auth; una proyección o un objeto falso no la concede."""
    Usuario = get_user_model()
    if isinstance(principal, Usuario):
        if (not principal.pk or principal._state.adding or not principal.is_authenticated
                or not principal.is_active):
            return None
        identificador = principal.pk
    elif isinstance(principal, int) and not isinstance(principal, bool) and principal > 0:
        identificador = principal
    else:
        return None
    return (Usuario._default_manager.using(alias_identidades()).filter(pk=identificador, is_active=True)
            .only('pk', 'is_active', 'is_superuser').first())


def identidad_de(principal, *, using=None):
    """Proyecta explícitamente una cuenta guardada; solo consulta campos de presentación."""
    from .models import CuentaCentro
    destino = using or alias_centros()
    if isinstance(principal, CuentaCentro):
        if principal.pk and not principal._state.adding and principal._state.db == destino:
            return principal
        raise ValidationError('La identidad local debe existir en la base del centro.')
    Usuario = get_user_model()
    if not isinstance(principal, Usuario) or not principal.pk or principal._state.adding:
        raise ValidationError('Seleccione una cuenta institucional guardada.')
    datos = (Usuario._default_manager.using(alias_identidades()).filter(pk=principal.pk)
             .values(*CAMPOS_PUBLICOS).first())
    if datos is None:
        raise ValidationError('La cuenta institucional ya no existe.')
    cuenta, creada = CuentaCentro.objects.using(destino).get_or_create(pk=principal.pk, defaults=datos)
    modificados = [nombre for nombre, valor in datos.items() if getattr(cuenta, nombre) != valor]
    if not creada and modificados:
        for nombre in modificados:
            setattr(cuenta, nombre, datos[nombre])
        cuenta.save(using=destino, update_fields=modificados + ['actualizada_en'])
    return cuenta


def _id_canonico(valor):
    """Compatibilidad de consultas antiguas: usar el ID nunca crea una relación a auth."""
    if isinstance(valor, get_user_model()):
        if not valor.pk or valor._state.adding:
            raise ValueError('No se puede consultar con una cuenta sin guardar.')
        return valor.pk
    if isinstance(valor, models.QuerySet) and valor.model is get_user_model():
        raise ValueError('Use IDs materializados; una subconsulta entre bases no es válida.')
    if isinstance(valor, (tuple, list, set)):
        return type(valor)(_id_canonico(v) for v in valor)
    return valor


def _consulta_canonica(condicion):
    if isinstance(condicion, models.Q):
        copia = condicion.copy()
        copia.children = [_consulta_canonica(c) for c in condicion.children]
        return copia
    if isinstance(condicion, tuple) and len(condicion) == 2 and isinstance(condicion[0], str):
        return condicion[0], _id_canonico(condicion[1])
    return condicion


class ConsultaIdentidades(models.QuerySet):
    def _filter_or_exclude(self, negate, args, kwargs):
        return super()._filter_or_exclude(negate, tuple(_consulta_canonica(a) for a in args),
                                         {k: _id_canonico(v) for k, v in kwargs.items()})


GestorIdentidades = models.Manager.from_queryset(ConsultaIdentidades)


class _ReferenciaCuenta(ForwardManyToOneDescriptor):
    def __set__(self, instancia, valor):
        # Puente de escritura para integraciones anteriores. El objeto almacenado
        # siempre es CuentaCentro, jamás una relación ORM entre bases.
        if isinstance(valor, get_user_model()):
            valor = identidad_de(valor, using=alias_centros(instancia))
        super().__set__(instancia, valor)


class ReferenciaCuenta(models.ForeignKey):
    forward_related_accessor_class = _ReferenciaCuenta

    def deconstruct(self):
        nombre, _, args, kwargs = super().deconstruct()
        return nombre, 'django.db.models.ForeignKey', args, kwargs

    def formfield(self, **kwargs):
        from .formularios import CuentaChoiceField
        kwargs.update(form_class=CuentaChoiceField,
                      queryset=get_user_model()._default_manager.using(alias_identidades()).filter(is_active=True))
        return super().formfield(**kwargs)


class _GestoresDescriptor(ManyToManyDescriptor):
    @cached_property
    def related_manager_cls(self):
        base = super().related_manager_cls

        class CuentasRelacionadas(base):
            def add(self, *objs, through_defaults=None):
                destino = alias_centros(self.instance)
                cuentas = [identidad_de(o, using=destino) if isinstance(o, get_user_model()) else o for o in objs]
                return super().add(*cuentas, through_defaults=through_defaults)

            def set(self, objs, *, clear=False, through_defaults=None):
                destino = alias_centros(self.instance)
                cuentas = [identidad_de(o, using=destino) if isinstance(o, get_user_model()) else o for o in objs]
                return super().set(cuentas, clear=clear, through_defaults=through_defaults)

            def remove(self, *objs):
                return super().remove(*(_id_canonico(o) for o in objs))

        return CuentasRelacionadas


class GestoresCampo(models.ManyToManyField):
    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, _GestoresDescriptor(self.remote_field, reverse=False))

    def deconstruct(self):
        nombre, _, args, kwargs = super().deconstruct()
        return nombre, 'django.db.models.ManyToManyField', args, kwargs

    def formfield(self, **kwargs):
        from .formularios import CuentasChoiceField
        kwargs.update(form_class=CuentasChoiceField,
                      queryset=get_user_model()._default_manager.using(alias_identidades()).filter(is_active=True))
        return super().formfield(**kwargs)
