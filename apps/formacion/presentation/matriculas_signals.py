"""Vinculación de invitaciones sólo después de verificar la titularidad del correo."""
from allauth.account.signals import email_confirmed
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.formacion.presentation.matriculas_cursos import aplicar_invitaciones


@receiver(email_confirmed, dispatch_uid='cursos_vincular_correo_confirmado')
def vincular_correo_confirmado(sender, request, email_address, **kwargs):
    aplicar_invitaciones(email_address.user)


@receiver(user_logged_in, dispatch_uid='cursos_vincular_al_ingresar')
def vincular_al_ingresar(sender, request, user, **kwargs):
    aplicar_invitaciones(user)
