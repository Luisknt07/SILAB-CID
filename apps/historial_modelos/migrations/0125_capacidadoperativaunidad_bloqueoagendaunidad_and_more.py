from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('webcitt', '0124_reserva_intencion_recursos'),
    ]

    operations = [
        migrations.CreateModel(
            name='CapacidadOperativaUnidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vigente_desde', models.DateField(db_index=True)),
                ('vigente_hasta', models.DateField(blank=True, db_index=True, null=True)),
                ('aforo_seguridad', models.PositiveIntegerField(help_text='Máximo permitido por infraestructura, evacuación y seguridad.')),
                ('puestos_mobiliario', models.PositiveIntegerField(help_text='Puestos con mesa, silla y condiciones mínimas de trabajo.')),
                ('puestos_equipados', models.PositiveIntegerField(help_text='Puestos que cuentan con el equipo o estación necesaria para operar.')),
                ('capacidad_personal', models.PositiveIntegerField(help_text='Personas que el personal disponible puede atender simultáneamente.')),
                ('fuente', models.CharField(blank=True, help_text='Acta, inspección, inventario o criterio técnico que respalda los valores.', max_length=180)),
                ('observaciones', models.TextField(blank=True)),
                ('activo', models.BooleanField(db_index=True, default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='capacidades_operativas_creadas', to=settings.AUTH_USER_MODEL)),
                ('periodo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='capacidades_unidades', to='webcitt.periodoacademico')),
                ('unidad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='capacidades_operativas', to='webcitt.unidad')),
            ],
            options={
                'verbose_name': 'Capacidad operativa de la unidad',
                'verbose_name_plural': 'Capacidades operativas de las unidades',
                'ordering': ['unidad__nombre', '-vigente_desde'],
            },
        ),
        migrations.CreateModel(
            name='BloqueoAgendaUnidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('mantenimiento', 'Mantenimiento programado'), ('feriado', 'Feriado o suspensión institucional'), ('evento', 'Evento institucional'), ('seguridad', 'Cierre por seguridad'), ('limpieza', 'Limpieza o preparación técnica'), ('otro', 'Otra indisponibilidad')], default='mantenimiento', max_length=20)),
                ('titulo', models.CharField(max_length=160)),
                ('motivo', models.TextField(blank=True)),
                ('fecha_inicio', models.DateField(db_index=True)),
                ('fecha_fin', models.DateField(db_index=True)),
                ('dia_completo', models.BooleanField(default=False, help_text='Bloquea toda la jornada operativa durante las fechas indicadas.')),
                ('hora_inicio', models.TimeField(blank=True, null=True)),
                ('hora_fin', models.TimeField(blank=True, null=True)),
                ('alcance', models.CharField(choices=[('unidad_completa', 'Toda la unidad'), ('areas', 'Áreas o espacios seleccionados'), ('equipos', 'Equipos seleccionados')], default='unidad_completa', max_length=20)),
                ('bloquea_recursos', models.BooleanField(default=True)),
                ('bloquea_servicios', models.BooleanField(default=True)),
                ('visible_en_agenda', models.BooleanField(default=True, help_text='Muestra el título y motivo operativo a los usuarios del calendario.')),
                ('activo', models.BooleanField(db_index=True, default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bloqueos_agenda_creados', to=settings.AUTH_USER_MODEL)),
                ('equipos', models.ManyToManyField(blank=True, related_name='bloqueos_agenda', to='webcitt.unidadequipo')),
                ('espacios', models.ManyToManyField(blank=True, related_name='bloqueos_agenda', to='webcitt.espacioreservable')),
                ('unidad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bloqueos_agenda', to='webcitt.unidad')),
            ],
            options={
                'verbose_name': 'Bloqueo de agenda',
                'verbose_name_plural': 'Bloqueos de agenda',
                'ordering': ['-fecha_inicio', 'hora_inicio', 'unidad__nombre'],
            },
        ),
        migrations.AddConstraint(
            model_name='capacidadoperativaunidad',
            constraint=models.UniqueConstraint(fields=('unidad', 'vigente_desde'), name='capacidad_unidad_inicio_unico'),
        ),
        migrations.AddIndex(
            model_name='bloqueoagendaunidad',
            index=models.Index(fields=['unidad', 'fecha_inicio', 'fecha_fin'], name='webcitt_blo_unidad__012048_idx'),
        ),
        migrations.AddIndex(
            model_name='bloqueoagendaunidad',
            index=models.Index(fields=['activo', 'tipo'], name='webcitt_blo_activo_17fb32_idx'),
        ),
    ]
