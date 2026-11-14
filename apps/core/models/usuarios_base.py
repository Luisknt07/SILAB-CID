from apps.core.presentation.niveles import niveles, niveles_actuales


from apps.core.presentation.catalogos import (
    catalogo_actual,
    carreras,
    facultades,
    tipos_con_carrera,
    tipos_usuario,
)


from django.db import models


from django.dispatch import receiver


from django.contrib.auth.models import User


from django.core.exceptions import ValidationError


from django.db.models.signals import post_save


class UserProfile(models.Model):
    """Perfil extendido del usuario"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    tipo_usuario = models.CharField(
        max_length=20,
        choices=tipos_usuario,
        blank=True,
        verbose_name="Tipo de usuario",
        help_text="Clasificación institucional usada para validación y reportes.",
    )
    facultad = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
        verbose_name="Facultad o dependencia",
    )
    telefono = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Teléfono"
    )
    institucion = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Institución"
    )
    cargo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Cargo"
    )

    # Información académica específica (SIN campo facultad)
    carrera = models.CharField(
        max_length=50, choices=carreras, blank=True, null=True, verbose_name="Carrera"
    )
    nivel_academico = models.CharField(
        max_length=30,
        choices=niveles,
        blank=True,
        null=True,
        verbose_name="Nivel Académico",
    )
    cedula = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Cédula o documento de identidad",
        help_text=(
            "Documento con el que la Universidad identifica a la persona. "
            "Obligatorio para estudiantes; admite pasaporte o documento extranjero."
        ),
    )
    biografia = models.TextField(blank=True, null=True, verbose_name="Biografía")
    avatar = models.ImageField(
        upload_to="profiles/avatars/",
        blank=True,
        null=True,
        verbose_name="Foto de Perfil",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webcitt_userprofile"
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"Perfil de {self.user.get_full_name() or self.user.username}"

    def get_carrera_display_custom(self):
        """Método personalizado para mostrar la carrera"""
        if self.carrera:
            return dict(carreras()).get(self.carrera, self.carrera)
        return "No especificado"

    @classmethod
    def facultad_para_carrera(cls, carrera):
        return catalogo_actual().facultad_para_carrera(carrera)

    def clean(self):
        super().clean()
        esperada = self.facultad_para_carrera(self.carrera)
        if esperada and self.facultad and self.facultad != esperada:
            raise ValidationError(
                {"facultad": "La facultad no corresponde a la carrera seleccionada."}
            )

    def campos_faltantes_reserva(self):
        """Devuelve los datos institucionales que impiden solicitar una reserva."""
        faltantes = []
        if not self.user.first_name or not self.user.last_name:
            faltantes.append("nombres y apellidos")
        if not self.user.email:
            faltantes.append("correo electrónico")
        if not self.tipo_usuario:
            faltantes.append("tipo de usuario")
            return faltantes

        if self.tipo_usuario == "externo":
            if not self.institucion or self.institucion.strip().lower() in {
                "gmail",
                "externo",
            }:
                faltantes.append("institución de procedencia")
        else:
            if self.facultad not in dict(facultades()) or self.facultad == "externo":
                faltantes.append("facultad o dependencia")
            if self.tipo_usuario in tipos_con_carrera():
                esperada = self.facultad_para_carrera(self.carrera)
                if not esperada:
                    faltantes.append("carrera")
                elif (
                    self.facultad != esperada
                    and "facultad o dependencia" not in faltantes
                ):
                    faltantes.append("facultad o dependencia")
            if self.tipo_usuario == "estudiante":
                if self.nivel_academico not in niveles_actuales().estudiantes:
                    faltantes.append(niveles_actuales().etiqueta_faltante)
                if not self.cedula:
                    faltantes.append("cédula o documento de identidad")
        return faltantes

    @property
    def perfil_reserva_completo(self):
        return not self.campos_faltantes_reserva()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)
