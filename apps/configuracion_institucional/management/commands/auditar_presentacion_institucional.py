"""Auditoria agregada, sin identidades personales ni contenido de configuracion."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.configuracion_institucional.models import PublicacionInstitucional, RevisionPresentacion
from apps.configuracion_institucional.selectors import identidad_de_revision
from apps.core.presentation.identidad import identidad_de_despliegue


class Command(BaseCommand):
    help = 'Audita la presentacion activa sin cambiar datos ni mostrar PII.'

    def handle(self, *args, **options):
        base = identidad_de_despliegue()
        try:
            total = RevisionPresentacion.objects.count()
            compatibles = RevisionPresentacion.objects.filter(
                producto_codigo=base[0].codigo, institucion_codigo=base[1].siglas,
            ).count()
            puntero = PublicacionInstitucional.objects.select_related('revision').filter(pk=1).first()
        except DatabaseError:
            raise CommandError('Presentacion no disponible: revisa la base y la migracion de configuracion_institucional.') from None
        self.stdout.write(f'Revisiones: {total}; compatibles: {compatibles}; de otras identidades: {total - compatibles}.')
        if not puntero or not puntero.revision:
            self.stdout.write('Sin publicacion activa; se usa la identidad del despliegue.')
            return
        revision = puntero.revision
        try:
            if revision.estado != 'publicada':
                raise ValueError
            identidad_de_revision(revision, *base)
        except (ValueError, ValidationError):
            raise CommandError('Publicacion activa incompatible o invalida; se usa la identidad del despliegue.') from None
        self.stdout.write('Publicacion activa compatible y valida; no se modificaron datos.')
