from django.db import migrations, models

import apps.configuracion_institucional.tipologias.models
from apps.configuracion_institucional.tipologias.models import sembrar_bases
from apps.core.tipologias import CODIGOS_BASE


def sembrar_tipologias_base(apps, schema_editor):
    sembrar_bases(apps.get_model('configuracion_institucional', 'TipologiaUnidad'))


def retirar_tipologias_base(apps, schema_editor):
    TipologiaUnidad = apps.get_model('configuracion_institucional', 'TipologiaUnidad')
    TipologiaUnidad.objects.filter(codigo__in=CODIGOS_BASE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('configuracion_institucional', '0007_habilitacion_capacidades'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipologiaUnidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador estable en minúsculas; no cambia después de crear la tipología.', max_length=50, unique=True, validators=[apps.configuracion_institucional.tipologias.models.validar_codigo_modelo], verbose_name='Código')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('nombre_plural', models.CharField(max_length=100, verbose_name='Nombre en plural')),
                ('nombre_en', models.CharField(blank=True, max_length=100, verbose_name='Nombre en inglés')),
                ('nombre_plural_en', models.CharField(blank=True, max_length=100, verbose_name='Nombre en plural en inglés')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('icono', models.CharField(default='iconsminds-microscope', help_text='Clase del icono institucional, por ejemplo iconsminds-microscope.', max_length=60, validators=[apps.configuracion_institucional.tipologias.models.validar_icono_modelo], verbose_name='Icono')),
                ('orden', models.PositiveSmallIntegerField(default=100, verbose_name='Orden')),
                ('base', models.CharField(choices=[('laboratorios', 'Laboratorios'), ('observatorios', 'Observatorios'), ('centro_experimental', 'Centros Experimentales'), ('plantas_piloto', 'Plantas Piloto')], default='laboratorios', help_text='Implementación cuyo catálogo, detalle, módulos y reserva reutiliza esta tipología.', max_length=50, verbose_name='Base operativa')),
                ('activa', models.BooleanField(default=True, help_text='Una tipología inactiva sale del catálogo público y no se asigna a unidades nuevas; sus unidades conservan datos e historial.', verbose_name='Activa')),
            ],
            options={
                'verbose_name': 'Tipología de unidad',
                'verbose_name_plural': 'Tipologías de unidad',
                'ordering': ('orden', 'codigo'),
            },
        ),
        migrations.RunPython(sembrar_tipologias_base, retirar_tipologias_base),
    ]
