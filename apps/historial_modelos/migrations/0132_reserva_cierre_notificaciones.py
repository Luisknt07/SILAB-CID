from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('webcitt', '0131_practicas_planificacion_ejecucion_auditoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reserva',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmada', 'Confirmada'),
                    ('en_proceso', 'En Proceso'),
                    ('completada', 'Completada'),
                    ('rechazada', 'Rechazada'),
                    ('cancelada', 'Cancelada'),
                    ('no_presentado', 'No se Presentó'),
                    ('no_atendida', 'No atendida por la unidad'),
                    ('vencida', 'Vencida sin aprobación'),
                ],
                default='pendiente',
                help_text='Estado actual de la reserva',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='fecha_inicio_atencion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reserva',
            name='fecha_cierre',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reserva',
            name='resultado_cierre',
            field=models.CharField(
                blank=True,
                choices=[
                    ('atendida', 'Atendida y completada'),
                    ('no_presentado', 'El usuario no se presentó'),
                    ('no_atendida', 'No atendida por la unidad'),
                    ('vencida', 'Vencida sin aprobación'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='detalle_cierre',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='NotificacionReserva',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('estado', 'Cambio de estado'), ('informacion', 'Información solicitada'), ('recordatorio_24h', 'Recordatorio 24 horas'), ('recordatorio_2h', 'Recordatorio 2 horas'), ('cierre_pendiente', 'Cierre operativo pendiente'), ('vencimiento', 'Solicitud vencida')], db_index=True, max_length=30)),
                ('titulo', models.CharField(max_length=180)),
                ('mensaje', models.TextField()),
                ('url', models.CharField(blank=True, max_length=500)),
                ('clave', models.CharField(max_length=180, unique=True)),
                ('leida', models.BooleanField(db_index=True, default=False)),
                ('enviada_email', models.BooleanField(default=False)),
                ('fecha_email', models.DateTimeField(blank=True, null=True)),
                ('error_email', models.TextField(blank=True)),
                ('creada_en', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('reserva', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='webcitt.reserva')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones_reservas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notificación de reserva',
                'verbose_name_plural': 'Notificaciones de reservas',
                'ordering': ['-creada_en', '-pk'],
            },
        ),
    ]
