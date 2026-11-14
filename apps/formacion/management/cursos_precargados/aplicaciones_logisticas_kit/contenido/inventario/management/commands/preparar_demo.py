"""Carga idempotente: no borra datos y no crea contraseñas compartidas."""

from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Producto
from inventario.services import registrar_movimiento


def preparar_grupos():
    consulta, _ = Group.objects.get_or_create(name="Consulta")
    operacion, _ = Group.objects.get_or_create(name="Operación")
    permisos = Permission.objects.filter(content_type__app_label="inventario")
    consulta.permissions.set(
        permisos.filter(codename__in=["view_producto", "view_movimiento"])
    )
    operacion.permissions.set(
        permisos.filter(
            codename__in=[
                "view_producto",
                "add_producto",
                "view_movimiento",
                "add_movimiento",
            ]
        )
    )
    return consulta, operacion


class Command(BaseCommand):
    help = "Prepara grupos y cuatro productos ficticios de Andina Distribución sin borrar registros."

    @transaction.atomic
    def handle(self, *args, **options):
        _, operacion = preparar_grupos()
        usuario, creado = get_user_model().objects.get_or_create(
            username="carga_docente"
        )
        if creado:
            usuario.set_unusable_password()
            usuario.save()
        elif usuario.has_usable_password():
            self.stderr.write(
                "Existe carga_docente con acceso: no se altera su contraseña."
            )
        usuario.groups.add(operacion)
        catalogo = [
            ("AD-001", "Caja corrugada mediana", "UN", "10.00"),
            ("AD-002", "Etiqueta adhesiva", "UN", "30.00"),
            ("AD-003", "Film de embalaje", "KG", "5.00"),
            ("AD-004", "Cinta de empaque", "UN", "8.00"),
        ]
        for codigo, nombre, unidad, minimo in catalogo:
            producto, _ = Producto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "unidad": unidad,
                    "minimo": Decimal(minimo),
                },
            )
        operaciones = [
            ("AD-001", "E", "25.00"),
            ("AD-001", "S", "8.00"),
            ("AD-002", "E", "20.00"),
            ("AD-003", "E", "12.50"),
            ("AD-003", "S", "3.25"),
            ("AD-004", "E", "4.00"),
        ]
        for orden, (codigo, tipo, cantidad) in enumerate(operaciones, 1):
            registrar_movimiento(
                usuario=usuario,
                producto_id=Producto.objects.get(codigo=codigo).pk,
                tipo=tipo,
                cantidad=cantidad,
                motivo="Carga docente ficticia",
                clave=uuid.uuid5(uuid.NAMESPACE_URL, f"andina-docente-v1/{orden}"),
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Demo preparada: 4 productos; saldos 17.00, 20.00, 9.25 y 4.00. Dos bajo mínimo en una base nueva."
            )
        )
