"""Crea la cuenta de administración de cada unidad activa y la deja lista en el admin.

Una cuenta por unidad, nombrada por la unidad (admin.fablab, admin.planta-lacteos…), sin
staff ni superusuario: su alcance nace de ser el administrador de esa unidad, igual que las
cuentas que se dan de alta desde «Usuarios». Queda además como coordinación de la unidad con
todos los módulos operativos, para que la ficha, el panel y el expediente la reconozcan. Si
la unidad tenía otro administrador, este queda como coordinación (salvo el superusuario, que
no lo necesita) y el cambio se registra en la auditoría de la unidad.

Se puede repetir: no cambia contraseñas de cuentas que ya existen salvo con --restablecer.
Imprime usuario y contraseña de cada cuenta creada o restablecida: guárdelos, no se vuelven a
mostrar.
"""
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.roles import MODULOS_OPERATIVOS
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile

# slug de la unidad → nombre de la cuenta
CUENTAS = {
    'laboratorio-fabricacion-digital-prototipado': 'admin.fablab',
    'laboratorio-robotica-electronica-automatizacion': 'admin.robotica',
    'laboratorio-realidad-extendida': 'admin.realidad-extendida',
    'laboratorio-inteligencia-artificial-ciencia-datos': 'admin.ia-datos',
    'laboratorio-ciberseguridad-redes': 'admin.ciberseguridad',
    'laboratorio-multimedia-produccion-audiovisual': 'admin.multimedia',
    'laboratorio-logistica-comercio-internacional': 'admin.logistica',
    'laboratorio-emprendimiento-innovacion-empresarial': 'admin.emprendimiento',
    'laboratorio-asuntos-publicos-gobierno': 'admin.asuntos-publicos',
    'laboratorio-energias-renovables-territorio': 'admin.turismo',
    'laboratorio-analisis-calidad-alimentos-suelos-aguas': 'admin.analisis-calidad',
    'laboratorio-reologia-textura-alimentos': 'admin.reologia',
    'laboratorio-microbiologia-biotecnologia-aplicada': 'admin.microbiologia',
    'laboratorio-diagnostico-veterinario-biologia-molecular': 'admin.diagnostico-veterinario',
    'laboratorio-analisis-sensorial-desarrollo-alimentos': 'admin.analisis-sensorial',
    'laboratorio-clinico': 'admin.clinico',
    'laboratorio-simulacion-clinica-enfermeria': 'admin.simulacion-clinica',
    'laboratorio-innovacion-educativa': 'admin.innovacion-educativa',
    'planta-piloto-lacteos': 'admin.planta-lacteos',
    'planta-piloto-carnicos': 'admin.planta-carnicos',
    'planta-piloto-frutas-vegetales': 'admin.planta-frutas-vegetales',
    'planta-piloto-cereales': 'admin.planta-cereales',
    'planta-extraccion-almidon-biotecnologia': 'admin.planta-almidon',
    'centro-experimental-san-francisco': 'admin.san-francisco',
    'observatorio-turismo': 'admin.observatorio-turismo',
    'observatorio-osezif': 'admin.osezif',
    'observatorio-cadena-lactea-carchi': 'admin.ocl-carchi',
    'observatorio-ambiental-agua-clima': 'admin.observatorio-ambiental',
    'observatorio-social-frontera': 'admin.observatorio-social',
}
PERFIL = {
    'tipo_usuario': 'administrativo', 'facultad': 'administracion_central', 'carrera': 'administrativo',
    'nivel_academico': 'administrativo', 'institucion': 'Universidad Politécnica Estatal del Carchi',
}


def contrasena():
    return secrets.token_urlsafe(9)


class Command(BaseCommand):
    help = 'Crea la cuenta de administración de cada unidad activa y la deja lista en el admin.'

    def add_arguments(self, parser):
        parser.add_argument('--restablecer', action='store_true',
                            help='Asigna una contraseña nueva también a las cuentas que ya existían.')

    @transaction.atomic
    def handle(self, *args, **options):
        Usuario = get_user_model()
        filas, creadas = [], 0
        for unidad in Unidad.objects.filter(activo=True, slug__in=CUENTAS).order_by('dependencia', 'nombre'):
            nombre_cuenta = CUENTAS[unidad.slug]
            usuario, creado = Usuario.objects.get_or_create(username=nombre_cuenta, defaults={
                'first_name': 'Administración', 'last_name': unidad.nombre_corto or unidad.nombre,
                'email': f'{nombre_cuenta}@upec.edu.ec', 'is_staff': False, 'is_superuser': False, 'is_active': True,
            })
            clave = ''
            if creado or options['restablecer']:
                clave = contrasena()
                usuario.set_password(clave)
                usuario.save(update_fields=['password'])
            creadas += creado
            UserProfile.objects.update_or_create(user=usuario, defaults={
                **PERFIL, 'cargo': f'Administración de {unidad.nombre_corto or unidad.nombre}'})
            self._asignar(unidad, usuario)
            filas.append((unidad, usuario, clave))
        sin_cuenta = Unidad.objects.filter(activo=True).exclude(slug__in=CUENTAS)
        for unidad in sin_cuenta:
            self.stdout.write(self.style.WARNING(f'Sin cuenta definida: {unidad.nombre} ({unidad.slug}).'))
        self.stdout.write(f'{creadas} cuentas creadas, {len(filas) - creadas} ya existían.')
        self.stdout.write('tipo | unidad | usuario | contraseña')
        for unidad, usuario, clave in filas:
            self.stdout.write(f'{unidad.nombre_tipologia} | {unidad.nombre} | {usuario.username} | '
                              f'{clave or "(sin cambio)"}')

    def _asignar(self, unidad, usuario):
        """La cuenta pasa a administrar la unidad; quien la administraba queda como coordinación."""
        anterior = unidad.administrador
        if anterior != usuario:
            unidad.administrador = usuario
            unidad.save(update_fields=['administrador'])
            registrar_auditoria(
                None, unidad=unidad, accion='actualizar', objeto=unidad,
                descripcion='Asignación de la cuenta de administración de la unidad',
                anteriores={'administrador': anterior.pk if anterior else None}, nuevos={'administrador': usuario.pk},
            )
            if anterior and not anterior.is_superuser:
                self._coordinacion(unidad, anterior, 'Administró la unidad antes de la cuenta de administración.')
                self.stdout.write(f'  {unidad.nombre}: {anterior.username} pasa a coordinación.')
        self._coordinacion(unidad, usuario, 'Administración de la unidad.', orden=0)

    @staticmethod
    def _coordinacion(unidad, usuario, descripcion, orden=1):
        responsable = (ResponsableUnidad.objects.filter(unidad=unidad, usuario=usuario).order_by('pk').first()
                       or ResponsableUnidad(unidad=unidad, usuario=usuario))
        responsable.nombre = usuario.get_full_name() or usuario.username
        responsable.rol = 'coordinacion'
        responsable.email = usuario.email
        responsable.descripcion = descripcion
        responsable.horario_atencion = 'Administración de la unidad'
        responsable.publico = False
        responsable.recibe_reservas = True
        responsable.activo = True
        responsable.orden = orden
        responsable.permisos_operativos = {modulo: True for modulo in MODULOS_OPERATIVOS}
        responsable.full_clean()
        responsable.save()
