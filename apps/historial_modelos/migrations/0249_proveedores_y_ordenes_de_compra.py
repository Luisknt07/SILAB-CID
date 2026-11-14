import django.db.models.deletion
import django.db.models.functions.text
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def proveedores_desde_el_texto(apps, schema_editor):
    """Cada nombre escrito en un pedido pasa al maestro de proveedores, una sola vez."""
    Proveedor = apps.get_model('webcitt', 'Proveedor')
    Pedido = apps.get_model('webcitt', 'PedidoAbastecimiento')
    for pedido in Pedido.objects.exclude(proveedor_texto=''):
        nombre = ' '.join(pedido.proveedor_texto.split())[:160]
        if not nombre:
            continue
        proveedor = (
            Proveedor.objects.filter(nombre__iexact=nombre).first()
            or Proveedor.objects.create(nombre=nombre)
        )
        Pedido.objects.filter(pk=pedido.pk).update(proveedor=proveedor)


def texto_desde_los_proveedores(apps, schema_editor):
    Pedido = apps.get_model('webcitt', 'PedidoAbastecimiento')
    for pedido in Pedido.objects.exclude(proveedor=None).select_related('proveedor'):
        Pedido.objects.filter(pk=pedido.pk).update(proveedor_texto=pedido.proveedor.nombre)


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0248_tarifas_costo_corrida'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Proveedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=160)),
                ('ruc', models.CharField(blank=True, max_length=13, verbose_name='RUC o cédula')),
                ('contacto', models.CharField(blank=True, max_length=160, verbose_name='Persona de contacto')),
                ('telefono', models.CharField(blank=True, max_length=40, verbose_name='Teléfono')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Correo')),
                ('direccion', models.CharField(blank=True, max_length=240, verbose_name='Dirección')),
                ('rubro', models.CharField(blank=True, max_length=240, verbose_name='Qué provee')),
                ('activo', models.BooleanField(db_index=True, default=True)),
                ('observaciones', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Proveedor',
                'verbose_name_plural': 'Proveedores',
                'ordering': ('nombre',),
                'constraints': [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower('nombre'), name='proveedor_nombre_unico',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='OrdenCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(blank=True, editable=False, max_length=30, unique=True)),
                ('fecha_emision', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('estado', models.CharField(
                    choices=[('emitida', 'Emitida'), ('confirmada', 'Confirmada por el proveedor'),
                             ('recibida', 'Recibida'), ('anulada', 'Anulada')],
                    db_index=True, default='emitida', max_length=20,
                )),
                ('condiciones', models.TextField(
                    blank=True,
                    help_text='Lo que el proveedor debe cumplir: cadena de frío, documentos de la entrega, forma de pago.',
                    verbose_name='Condiciones de entrega y pago',
                )),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('emitida_por', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ordenes_compra_emitidas', to=settings.AUTH_USER_MODEL,
                )),
                ('proveedor', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='ordenes_compra', to='webcitt.proveedor',
                )),
                ('unidad', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='ordenes_compra', to='webcitt.unidad',
                )),
            ],
            options={
                'verbose_name': 'Orden de compra',
                'verbose_name_plural': 'Órdenes de compra',
                'ordering': ('-fecha_emision', '-pk'),
            },
        ),
        migrations.RenameField(
            model_name='pedidoabastecimiento',
            old_name='proveedor',
            new_name='proveedor_texto',
        ),
        migrations.AddField(
            model_name='pedidoabastecimiento',
            name='proveedor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='pedidos', to='webcitt.proveedor',
            ),
        ),
        migrations.AddField(
            model_name='pedidoabastecimiento',
            name='orden_compra',
            field=models.ForeignKey(
                blank=True, help_text='La orden de compra con la que se envió al proveedor.', null=True,
                on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos', to='webcitt.ordencompra',
            ),
        ),
        migrations.RunPython(proveedores_desde_el_texto, texto_desde_los_proveedores),
        migrations.RemoveField(
            model_name='pedidoabastecimiento',
            name='proveedor_texto',
        ),
    ]
