"""Cuentas con un papel institucional fuera de las unidades.

Los tres tipos de usuario de la plataforma no viven aquí: el superusuario es
el de Django, el personal de una unidad se registra en `ResponsableUnidad` y
el resto son usuarios con su perfil. Decanato es la excepción que revisa y
amortiza las órdenes de servicio del FabLab desde el administrador.
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver


class Decanato(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='decanato_profile',
    )
    cargo = models.CharField(max_length=100, default='Decano')

    class Meta:
        db_table = 'webcitt_decanato'
        verbose_name = 'Usuario de Decanato'
        verbose_name_plural = 'Usuarios de Decanato'

    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        return f"{nombre} - {self.cargo}"


@receiver(post_save, sender=Decanato)
def configurar_usuario_decanato(sender, instance, **kwargs):
    """Mantiene el acceso administrativo mínimo requerido por Decanato."""
    usuario = instance.usuario
    if not usuario.is_staff:
        usuario.is_staff = True
        usuario.save(update_fields=['is_staff'])

    grupo, _ = Group.objects.get_or_create(name='Decanato')
    permisos = Permission.objects.filter(
        content_type__app_label='laboratorios_operacion',
        content_type__model='solicitudfabricacion',
        codename__in=[
            'view_solicitudfabricacion',
            'change_solicitudfabricacion',
        ],
    )
    grupo.permissions.add(*permisos)
    usuario.groups.add(grupo)

