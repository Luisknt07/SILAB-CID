import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from .forms import ImportarForm, MovimientoForm, ProductoForm
from .models import Movimiento, Producto
from .services import celda_csv, importar_productos, registrar_movimiento


@login_required
@permission_required("inventario.view_producto", raise_exception=True)
def tablero(request):
    busqueda = request.GET.get("q", "").strip()[:120]
    productos = Producto.objects.all()
    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda) | Q(nombre__icontains=busqueda)
        )
    filas = []
    for producto in productos:
        progreso = (
            min(100, int(producto.existencia / producto.minimo * 100))
            if producto.minimo
            else 100
        )
        filas.append({"producto": producto, "progreso": progreso})
    return render(
        request,
        "inventario/tablero.html",
        {
            "filas": filas,
            "q": busqueda,
            "total": Producto.objects.count(),
            "bajos": Producto.objects.filter(existencia__lt=F("minimo")).count(),
            "sin_stock": Producto.objects.filter(existencia=0).count(),
        },
    )


@login_required
@permission_required("inventario.add_producto", raise_exception=True)
def producto_nuevo(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("codigo", "El código ya existe. Revise el catálogo.")
        else:
            messages.success(
                request, "Producto registrado. El stock se cambia mediante movimientos."
            )
            return redirect("tablero")
    return render(
        request,
        "inventario/formulario.html",
        {"form": form, "titulo": "Registrar producto"},
    )


@login_required
@permission_required(
    ("inventario.add_movimiento", "inventario.view_producto"), raise_exception=True
)
def movimiento_nuevo(request):
    form = MovimientoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            registrar_movimiento(
                usuario=request.user,
                producto_id=datos["producto"].pk,
                tipo=datos["tipo"],
                cantidad=datos["cantidad"],
                motivo=datos["motivo"],
                clave=datos["clave"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(
                None,
                "La operación ya se procesó o entró en conflicto. Consulte el historial antes de reintentar.",
            )
        else:
            messages.success(
                request, "Movimiento procesado. Consulte el historial para comprobarlo."
            )
            return redirect("tablero")
    return render(
        request,
        "inventario/formulario.html",
        {"form": form, "titulo": "Registrar entrada o salida"},
    )


@login_required
@permission_required(
    ("inventario.view_producto", "inventario.view_movimiento"), raise_exception=True
)
def historial(request):
    movimientos = Movimiento.objects.select_related("producto", "usuario")[:200]
    return render(request, "inventario/historial.html", {"movimientos": movimientos})


@login_required
@permission_required("inventario.add_producto", raise_exception=True)
def importar(request):
    form = ImportarForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            cantidad = importar_productos(
                usuario=request.user, contenido=form.cleaned_data["archivo"].read()
            )
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, "Un código ya existe. No se importó ningún producto.")
        else:
            messages.success(
                request,
                f"Se crearon {cantidad} productos, todos con existencia inicial cero.",
            )
            return redirect("tablero")
    return render(
        request,
        "inventario/formulario.html",
        {
            "form": form,
            "titulo": "Importar catálogo CSV",
            "ayuda": "Cabecera exacta: codigo,nombre,unidad,minimo. No actualiza productos existentes ni modifica stock.",
        },
    )


@login_required
@permission_required("inventario.view_producto", raise_exception=True)
def exportar(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="existencias-andina.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        ["codigo", "nombre", "unidad", "minimo", "existencia", "bajo_minimo"]
    )
    for producto in Producto.objects.all():
        writer.writerow(
            [
                celda_csv(producto.codigo),
                celda_csv(producto.nombre),
                producto.unidad,
                str(producto.minimo),
                str(producto.existencia),
                "SI" if producto.bajo_minimo else "NO",
            ]
        )
    return response
