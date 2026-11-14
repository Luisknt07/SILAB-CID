"""Archiva la remisión interna sin autorizar fondos ni ejecutar compras."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('documentos', '0020_convocatoria_necesidades_mayo'),
        ('directorio_unidades', '0002_centro_costo_dependencia'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.CreateModel(
        name='RemisionNecesidades',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('dependencia_nombre', models.CharField(max_length=220)),
            ('anio_preparacion', models.PositiveSmallIntegerField()),
            ('anio_ejecucion', models.PositiveSmallIntegerField()),
            ('remitido_en', models.DateTimeField(auto_now_add=True)),
            ('destinatarios', models.JSONField(default=list, editable=False)),
            ('contenido', models.JSONField(editable=False)),
            ('sha256', models.CharField(editable=False, max_length=64)),
            ('dependencia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name='remisiones_necesidades', to='directorio_unidades.dependenciaacademica')),
            ('remitido_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name='remisiones_necesidades', to=settings.AUTH_USER_MODEL)),
        ],
        options={
            'ordering': ['-remitido_en', '-pk'],
            'verbose_name': 'Remisión de necesidades',
            'verbose_name_plural': 'Remisiones de necesidades',
            'constraints': [models.UniqueConstraint(fields=('dependencia', 'anio_preparacion', 'sha256'),
                name='remision_necesidades_captura_unica')],
        },
    )]
