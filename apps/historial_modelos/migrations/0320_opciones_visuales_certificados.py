import apps.formacion.models.cursos_certificacion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webcitt", "0319_certificados_profesionales")]
    operations = [
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="alineacion_contenido",
            field=models.CharField(
                choices=[("centro", "Centrado"), ("izquierda", "A la izquierda")],
                default="centro",
                max_length=12,
                verbose_name="Alineación del contenido",
            ),
        ),
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="competencias",
            field=models.TextField(
                blank=True,
                help_text="Una competencia por línea, hasta seis. Sólo aparece en el formato de competencias.",
                max_length=600,
                validators=[
                    apps.formacion.models.cursos_certificacion.validar_texto_certificado
                ],
                verbose_name="Competencias o logros",
            ),
        ),
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="formato_contenido",
            field=models.CharField(
                choices=[
                    ("breve", "Texto breve"),
                    ("institucional", "Bloque institucional"),
                    ("competencias", "Texto y competencias o logros"),
                ],
                default="institucional",
                max_length=16,
                verbose_name="Organización del contenido",
            ),
        ),
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="foto_alusiva",
            field=models.ImageField(
                blank=True,
                help_text="Fotografía propia o autorizada del laboratorio. PNG o JPEG, hasta 2 MB.",
                upload_to=apps.formacion.models.cursos_certificacion.ruta_foto_certificado,
                verbose_name="Fotografía alusiva",
            ),
        ),
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="subtitulo",
            field=models.CharField(
                blank=True,
                max_length=180,
                validators=[
                    apps.formacion.models.cursos_certificacion.validar_texto_certificado
                ],
                verbose_name="Subtítulo opcional",
            ),
        ),
        migrations.AddField(
            model_name="configuracioncertificadocurso",
            name="usar_foto_unidad",
            field=models.BooleanField(
                default=True,
                help_text="Se usa cuando no carga una fotografía específica y la unidad tiene una imagen propia.",
                verbose_name="Usar la fotografía de la unidad",
            ),
        ),
        migrations.AlterField(
            model_name="configuracioncertificadocurso",
            name="diseno",
            field=models.CharField(
                choices=[
                    ("clasico", "Clásico institucional"),
                    ("sobrio", "Sobrio"),
                    ("tecnologico", "Tecnológico"),
                    ("geometrico", "Geométrico"),
                    ("elegante", "Elegante"),
                    ("congreso", "Congreso"),
                    ("industrial", "Industrial · laboratorio"),
                    ("circuitos", "Circuitos · innovación"),
                    ("horizonte", "Horizonte · fotografía"),
                    ("editorial", "Editorial · contenidos"),
                    ("academico", "Académico · reconocimiento"),
                    ("inmersivo", "Inmersivo · tecnología"),
                ],
                default="clasico",
                max_length=12,
                verbose_name="Diseño",
            ),
        ),
    ]
