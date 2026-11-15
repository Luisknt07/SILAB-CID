"""Borra el segundo factor de una cuenta que perdió su teléfono y sus códigos de respaldo."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.core.acceso import segundo_factor


class Command(BaseCommand):
    help = ('Restablece el segundo factor de una cuenta. En su siguiente ingreso al administrador '
            'la persona registra de nuevo su aplicación autenticadora.')

    def add_arguments(self, parser):
        parser.add_argument('usuario', help='Nombre de usuario o correo de la cuenta.')

    def handle(self, *args, **options):
        Usuario = get_user_model()
        referencia = options['usuario']
        cuentas = list(Usuario.objects.filter(username=referencia)) or list(
            Usuario.objects.filter(email__iexact=referencia))
        if len(cuentas) != 1:
            raise CommandError('No hay una única cuenta con ese nombre de usuario o correo.')
        if not segundo_factor.restablecer(cuentas[0]):
            raise CommandError('La cuenta no tenía un segundo factor registrado.')
        self.stdout.write(f'Segundo factor restablecido para la cuenta {cuentas[0].pk}.')
