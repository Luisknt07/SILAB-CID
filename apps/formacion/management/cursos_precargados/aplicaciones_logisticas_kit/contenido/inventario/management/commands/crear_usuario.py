from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from .preparar_demo import preparar_grupos


class Command(BaseCommand):
    help = (
        "Crea un usuario de práctica sin guardar contraseñas en argumentos ni archivos."
    )

    def add_arguments(self, parser):
        parser.add_argument("usuario")
        parser.add_argument("--rol", choices=["consulta", "operacion"], required=True)

    def handle(self, *args, **options):
        modelo = get_user_model()
        if modelo.objects.filter(username=options["usuario"]).exists():
            raise CommandError("El usuario ya existe. No se modifica.")
        usuario = modelo(username=options["usuario"])
        password = getpass("Contraseña nueva (no se muestra): ")
        if password != getpass("Repita la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")
        try:
            validate_password(password, usuario)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages))
        usuario.set_password(password)
        usuario.full_clean()
        usuario.save()
        consulta, operacion = preparar_grupos()
        usuario.groups.add(consulta if options["rol"] == "consulta" else operacion)
        self.stdout.write(self.style.SUCCESS("Usuario creado; ingrese por /acceso/."))
