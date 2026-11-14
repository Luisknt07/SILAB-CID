"""Crea cuentas locales para comprobar los perfiles del panel de laboratorio."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.gestion_unidades.presentation.permisos import MODULOS_OPERATIVOS
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile


class Command(BaseCommand):
    help = (
        "Crea usuarios de prueba de coordinación, laboratorista y solicitante "
        "sin reemplazar al administrador principal de la unidad."
    )

    DEFAULT_SLUG = "laboratorio-fabricacion-digital-prototipado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--unidad",
            default=self.DEFAULT_SLUG,
            help="Slug del laboratorio donde se asociará el personal de prueba.",
        )
        parser.add_argument(
            "--password",
            required=True,
            help="Contraseña local que se asignará a las tres cuentas de prueba.",
        )

    @staticmethod
    def _permisos(**activos):
        permisos = {modulo: False for modulo in MODULOS_OPERATIVOS}
        permisos.update(activos)
        return permisos

    def _crear_usuario(self, *, username, password, nombres, apellidos, email, perfil):
        User = get_user_model()
        usuario, creado = User.objects.update_or_create(
            username=username,
            defaults={
                "first_name": nombres,
                "last_name": apellidos,
                "email": email,
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        usuario.set_password(password)
        usuario.save(update_fields=[
            "password", "first_name", "last_name", "email",
            "is_active", "is_staff", "is_superuser",
        ])
        UserProfile.objects.update_or_create(user=usuario, defaults=perfil)
        return usuario, creado

    @staticmethod
    def _asociar_responsable(unidad, usuario, **defaults):
        responsable = (
            ResponsableUnidad.objects.filter(unidad=unidad, usuario=usuario)
            .order_by("pk")
            .first()
        )
        if responsable is None:
            responsable = ResponsableUnidad(unidad=unidad, usuario=usuario)
        for campo, valor in defaults.items():
            setattr(responsable, campo, valor)
        responsable.full_clean()
        responsable.save()
        return responsable

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            unidad = Unidad.objects.select_related("administrador").get(
                slug=options["unidad"]
            )
        except Unidad.DoesNotExist as error:
            raise CommandError(
                f'No existe una unidad con slug "{options["unidad"]}".'
            ) from error

        password = options["password"]
        if len(password) < 10:
            raise CommandError("La contraseña de prueba debe tener al menos 10 caracteres.")

        personal = [
            {
                "username": "demo.coordinador.fablab",
                "nombres": "Carolina",
                "apellidos": "Coordinadora Demo",
                "email": "coordinador.fablab@citt.test",
                "perfil": {
                    "tipo_usuario": "administrativo",
                    "facultad": "administracion_central",
                    "carrera": "administrativo",
                    "nivel_academico": "administrativo",
                    "institucion": "Universidad Politécnica Estatal del Carchi",
                    "cargo": "Coordinación operativa de laboratorio · cuenta de prueba",
                },
                "responsable": {
                    "nombre": "Carolina Coordinadora Demo",
                    "rol": "coordinacion",
                    "email": "coordinador.fablab@citt.test",
                    "descripcion": "Supervisa solicitudes, agenda y operación del laboratorio.",
                    "horario_atencion": "Cuenta local para pruebas funcionales",
                    "publico": False,
                    "recibe_reservas": True,
                    "activo": True,
                    "orden": 900,
                    "permisos_operativos": self._permisos(
                        reservas=True,
                        agenda=True,
                        recursos=True,
                        mantenimiento=True,
                        inventario=True,
                        finanzas=True,
                        practicas=True,
                        reportes=True,
                    ),
                },
            },
            {
                "username": "demo.laboratorista.fablab",
                "nombres": "Leonardo",
                "apellidos": "Laboratorista Demo",
                "email": "laboratorista.fablab@citt.test",
                "perfil": {
                    "tipo_usuario": "administrativo",
                    "facultad": "administracion_central",
                    "carrera": "administrativo",
                    "nivel_academico": "administrativo",
                    "institucion": "Universidad Politécnica Estatal del Carchi",
                    "cargo": "Laboratorista · cuenta de prueba",
                },
                "responsable": {
                    "nombre": "Leonardo Laboratorista Demo",
                    "rol": "laboratorista",
                    "email": "laboratorista.fablab@citt.test",
                    "descripcion": "Atiende reservas y registra la operación técnica diaria.",
                    "horario_atencion": "Cuenta local para pruebas funcionales",
                    "publico": False,
                    "recibe_reservas": True,
                    "activo": True,
                    "orden": 901,
                    "permisos_operativos": self._permisos(
                        reservas=True,
                        recursos=True,
                        mantenimiento=True,
                        inventario=True,
                        practicas=True,
                        reportes=True,
                    ),
                },
            },
            {
                "username": "demo.solicitante.fablab",
                "nombres": "Sofía",
                "apellidos": "Solicitante Demo",
                "email": "solicitante.fablab@citt.test",
                "perfil": {
                    "tipo_usuario": "docente",
                    "facultad": "agropecuarias_ambientales",
                    "carrera": "computacion",
                    "nivel_academico": "docente",
                    "institucion": "Universidad Politécnica Estatal del Carchi",
                    "cargo": "Docente solicitante · cuenta de prueba",
                },
            },
        ]

        creados = []
        for datos in personal:
            responsable_data = datos.pop("responsable", None)
            usuario, creado = self._crear_usuario(password=password, **datos)
            if responsable_data:
                self._asociar_responsable(unidad, usuario, **responsable_data)
            creados.append((usuario, creado))

        administrador = unidad.administrador
        if administrador:
            self._asociar_responsable(
                unidad,
                administrador,
                nombre=administrador.get_full_name() or administrador.username,
                rol="coordinacion",
                email=administrador.email,
                descripcion="Administrador principal del laboratorio.",
                horario_atencion="Administración de la unidad",
                publico=False,
                recibe_reservas=True,
                activo=True,
                orden=0,
                permisos_operativos={modulo: True for modulo in MODULOS_OPERATIVOS},
            )
            principal = administrador.username
        else:
            principal = "sin asignar"
            self.stdout.write(self.style.WARNING(
                "La unidad no tiene administrador principal; asígnalo desde la ficha de la unidad."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Usuarios de prueba listos para {unidad.nombre}."
        ))
        for usuario, creado in creados:
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"- {usuario.username}: {estado}")
        self.stdout.write(f"- Administrador principal conservado: {principal}")
