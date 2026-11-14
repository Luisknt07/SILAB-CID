from django.db import migrations, models
from django.utils.text import slugify


def asignar_codigos(apps, schema_editor):
    """Codigo estable derivado del nombre, unico por catalogo."""
    for nombre_modelo in ('Categoria', 'TipoLaboratorio'):
        modelo = apps.get_model('webcitt', nombre_modelo)
        usados = set()
        for fila in modelo.objects.order_by('pk'):
            base = slugify(fila.nombre)[:90] or 'clasificacion'
            candidato, sufijo = base, 2
            while candidato in usados:
                candidato = f'{base}-{sufijo}'
                sufijo += 1
            usados.add(candidato)
            fila.codigo = candidato
            fila.save(update_fields=['codigo'])


class Migration(migrations.Migration):

    dependencies = [
        ('webcitt', '0205_unidad_dependencia_catalogo_tipologias'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='categoria',
            options={'ordering': ('orden', 'nombre'), 'verbose_name': 'Subárea', 'verbose_name_plural': 'Subáreas'},
        ),
        migrations.AlterModelOptions(
            name='tipolaboratorio',
            options={'ordering': ('orden', 'nombre'), 'verbose_name': 'Modo de uso', 'verbose_name_plural': 'Modos de uso'},
        ),
        # Sin indice en el alta: al volverse unico, PostgreSQL crearia el
        # indice `_like` dos veces con el mismo nombre.
        migrations.AddField(
            model_name='categoria',
            name='codigo',
            field=models.SlugField(blank=True, db_index=False, help_text='Identificador estable generado del nombre; se usa en los filtros públicos y no cambia.', max_length=100, null=True, verbose_name='Código'),
        ),
        migrations.AddField(
            model_name='tipolaboratorio',
            name='codigo',
            field=models.SlugField(blank=True, db_index=False, help_text='Identificador estable generado del nombre; se usa en los filtros públicos y no cambia.', max_length=100, null=True, verbose_name='Código'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='orden',
            field=models.PositiveSmallIntegerField(default=100, verbose_name='Orden'),
        ),
        migrations.AddField(
            model_name='tipolaboratorio',
            name='orden',
            field=models.PositiveSmallIntegerField(default=100, verbose_name='Orden'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='activa',
            field=models.BooleanField(default=True, help_text='Una clasificación archivada deja de ofrecerse en filtros y unidades nuevas; las unidades que ya la tienen la conservan.', verbose_name='Activa'),
        ),
        migrations.AddField(
            model_name='tipolaboratorio',
            name='activa',
            field=models.BooleanField(default=True, help_text='Una clasificación archivada deja de ofrecerse en filtros y unidades nuevas; las unidades que ya la tienen la conservan.', verbose_name='Activa'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='tipologias',
            field=models.JSONField(blank=True, default=list, help_text='Códigos de tipología donde se ofrece; vacío significa todas.', verbose_name='Tipologías'),
        ),
        migrations.AddField(
            model_name='tipolaboratorio',
            name='tipologias',
            field=models.JSONField(blank=True, default=list, help_text='Códigos de tipología donde se ofrece; vacío significa todas.', verbose_name='Tipologías'),
        ),
        migrations.RunPython(asignar_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='categoria',
            name='codigo',
            field=models.SlugField(blank=True, help_text='Identificador estable generado del nombre; se usa en los filtros públicos y no cambia.', max_length=100, unique=True, verbose_name='Código'),
        ),
        migrations.AlterField(
            model_name='tipolaboratorio',
            name='codigo',
            field=models.SlugField(blank=True, help_text='Identificador estable generado del nombre; se usa en los filtros públicos y no cambia.', max_length=100, unique=True, verbose_name='Código'),
        ),
    ]
