"""Reglas verificables del inventario. La IA no decide cantidades ni permisos."""

import csv
import io
import uuid
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from .models import Movimiento, Producto

MAX_CANTIDAD = Decimal("9999999999.99")
CAMPOS_CSV = ["codigo", "nombre", "unidad", "minimo"]


def cantidad_decimal(value, *, permite_cero=False):
    """No redondeamos silenciosamente; punto decimal y hasta dos decimales."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number > MAX_CANTIDAD:
            raise ValueError
        if number < 0 or (number == 0 and not permite_cero):
            raise ValueError
        if number != number.quantize(Decimal("0.01")):
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            "Cantidad inválida: use un número positivo con hasta dos decimales y punto decimal."
        )
    return number.quantize(Decimal("0.01"))


def comprobar_permiso(usuario, permiso):
    if not usuario or not usuario.is_active or not usuario.has_perm(permiso):
        raise PermissionDenied("Su usuario no tiene permiso para esta operación.")


@transaction.atomic
def registrar_movimiento(*, usuario, producto_id, tipo, cantidad, motivo, clave=None):
    comprobar_permiso(usuario, "inventario.add_movimiento")
    cantidad = cantidad_decimal(cantidad)
    if tipo not in {"E", "S"}:
        raise ValidationError("Seleccione entrada o salida.")
    motivo = str(motivo).strip()
    if not motivo:
        raise ValidationError("Explique el motivo del movimiento.")
    try:
        clave = uuid.UUID(str(clave)) if clave else uuid.uuid4()
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("Identificador de operación inválido.")
    existente = Movimiento.objects.filter(clave=clave).first()
    if existente:
        # Un doble clic no descuenta dos veces; otra solicitud no puede reutilizar la clave.
        if (
            existente.usuario_id == usuario.pk
            and existente.producto_id == producto_id
            and existente.tipo == tipo
            and existente.cantidad == cantidad
            and existente.motivo == motivo
        ):
            return existente
        raise ValidationError(
            "El identificador ya corresponde a una operación distinta."
        )
    try:
        producto = Producto.objects.select_for_update().get(pk=producto_id)
    except (Producto.DoesNotExist, ValueError, TypeError):
        raise ValidationError("El producto no existe.")
    movimiento = Movimiento(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
        usuario=usuario,
        clave=clave,
    )
    movimiento.full_clean()
    productos = Producto.objects.filter(pk=producto.pk)
    if tipo == "S":
        # El filtro y la actualización se ejecutan juntos en la base de datos.
        actualizados = productos.filter(existencia__gte=cantidad).update(
            existencia=F("existencia") - cantidad
        )
        if not actualizados:
            raise ValidationError("Stock insuficiente. No se registró la salida.")
    else:
        actualizados = productos.filter(existencia__lte=MAX_CANTIDAD - cantidad).update(
            existencia=F("existencia") + cantidad
        )
        if not actualizados:
            raise ValidationError(
                "La entrada supera la capacidad numérica del prototipo."
            )
    movimiento.save()
    return movimiento


@transaction.atomic
def importar_productos(*, usuario, contenido):
    """Alta de catálogo solamente: los CSV no alteran existencias ni productos existentes."""
    comprobar_permiso(usuario, "inventario.add_producto")
    if len(contenido) > 1_048_576:
        raise ValidationError("El archivo supera 1 MB.")
    try:
        text = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("Guarde el archivo como CSV UTF-8, separado por comas.")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != CAMPOS_CSV:
        raise ValidationError(
            "Cabecera requerida: codigo,nombre,unidad,minimo (en ese orden)."
        )
    productos, errores, codigos = [], [], set()
    for fila, datos in enumerate(reader, start=2):
        if fila > 101:
            raise ValidationError("Se permiten hasta 100 productos por archivo.")
        if None in datos or any(value is None for value in datos.values()):
            errores.append(f"Fila {fila}: el número de columnas es incorrecto.")
            continue
        try:
            codigo = datos["codigo"].strip().upper()
            if codigo in codigos:
                raise ValidationError("Código repetido dentro del archivo.")
            codigos.add(codigo)
            producto = Producto(
                codigo=codigo,
                nombre=datos["nombre"].strip(),
                unidad=datos["unidad"].strip().upper(),
                minimo=cantidad_decimal(datos["minimo"], permite_cero=True),
            )
            producto.full_clean()
            productos.append(producto)
        except ValidationError as error:
            errores.append(f"Fila {fila}: " + " ".join(error.messages))
    if errores:
        raise ValidationError(errores)
    if not productos:
        raise ValidationError("El archivo no contiene productos.")
    for producto in productos:
        producto.save()
    return len(productos)


def celda_csv(value):
    """Impide que Excel interprete textos del usuario como fórmulas."""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def existencias_para_consulta(*, solo_bajos=False, codigo=""):
    """Lectura compartida por la web y MCP; no ejecuta SQL recibido de un modelo."""
    productos = Producto.objects.all()
    if solo_bajos:
        productos = productos.filter(existencia__lt=F("minimo"))
    if codigo:
        productos = productos.filter(codigo=codigo.strip().upper())
    return [
        {
            "codigo": p.codigo,
            "nombre": p.nombre,
            "unidad": p.unidad,
            "existencia": str(p.existencia),
            "minimo": str(p.minimo),
            "bajo_minimo": p.bajo_minimo,
        }
        for p in productos[:100]
    ]
