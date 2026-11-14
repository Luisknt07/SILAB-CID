"""Carga casos de ejemplo del inventario para probar el lector, la ficha del equipo, la historia y el tablero.

Crea equipos de ejemplo con código estándar y la marca [Ejemplo de inventario] en sus observaciones (nunca
toca el inventario real), cada uno con un caso:
prestado, con una incidencia que detiene la operación, con la vida útil cumplida, con el mantenimiento
vencido y transferido a otra unidad (con su cambio de código). Suma reservas atendidas de ejemplo a las
impresoras 3D FDM de la unidad para que el tablero institucional muestre uso y su diagnóstico, e indica
un código de bodega libre para probar el registro con el lector. Todo lleva la marca [Ejemplo de inventario]
y --eliminar lo borra. No corre en producción.
"""
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.presentation.codigos_sistema import siguiente_codigo_unidad
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, PlanMantenimientoEquipo
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad

MARCA = '[Ejemplo de inventario]'
PREFIJO = 'EJ-INV-'  # códigos de los ejemplos anteriores al estándar; --eliminar también los retira
CODIGO_LIBRE = '23300000000-99009901'


class Command(BaseCommand):
    help = 'Carga (o elimina con --eliminar) casos de ejemplo del inventario para probar el sistema.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', default='laboratorio-fabricacion-digital-prototipado')
        parser.add_argument('--destino', default='laboratorio-robotica-electronica-automatizacion',
                            help='Unidad a la que se transfiere el equipo de ejemplo.')
        parser.add_argument('--eliminar', action='store_true', help='Borra todos los ejemplos cargados.')

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError('Los ejemplos de inventario solo se cargan en desarrollo (DEBUG activo).')
        with transaction.atomic():
            self._eliminar()
            if opciones['eliminar']:
                self.stdout.write(self.style.SUCCESS('Ejemplos de inventario eliminados.'))
                return
            unidad = Unidad.objects.filter(slug=opciones['unidad']).first()
            destino = Unidad.objects.filter(slug=opciones['destino']).first()
            if unidad is None or destino is None:
                raise CommandError('No existen la unidad o la unidad de destino.')
            casos = self._casos(unidad, destino)
            horas = self._uso(unidad)
        self.stdout.write(self.style.SUCCESS('Ejemplos de inventario cargados:'))
        for codigo, caso in casos:
            self.stdout.write(f'  {codigo:22} {caso}')
        self.stdout.write(f'  Uso de ejemplo: {horas} h en reservas atendidas de las impresoras 3D FDM.')
        self.stdout.write(f'  Para probar el registro con el lector, escanea o escribe {CODIGO_LIBRE} (no está registrado).')
        self.stdout.write('  Cuentas: demo.coordinador.fablab, demo.laboratorista.fablab y demo.solicitante.fablab '
                          '(crear_usuarios_prueba_gestion).')

    @staticmethod
    def _eliminar():
        Reserva.objects.filter(titulo_solicitud__startswith=MARCA).delete()
        ejemplos = UnidadEquipo.objects.filter(Q(codigo_unidad__startswith=PREFIJO) | Q(observaciones__startswith=MARCA))
        PrestamoEquipo.objects.filter(equipo__in=ejemplos).delete()
        IncidenciaEquipo.objects.filter(equipo__in=ejemplos).delete()
        PlanMantenimientoEquipo.objects.filter(equipo__in=ejemplos).delete()
        AliasCodigoUnidadEquipo.objects.filter(unidad_equipo__in=ejemplos).delete()
        EventoCicloVidaEquipo.objects.filter(equipo__in=ejemplos).delete()
        for equipo in ejemplos:
            equipo.espacios_asociados.clear()
        ejemplos.delete()

    def _equipo(self, unidad, nombre_tipo, caso, **campos):
        """Una unidad física de ejemplo de un tipo que la unidad ya tiene, en su misma área y con código estándar."""
        modelo = (UnidadEquipo.objects.filter(laboratorio=unidad, activa=True, equipo__nombre__icontains=nombre_tipo)
                  .exclude(observaciones__startswith=MARCA).select_related('equipo').first())
        tipo = modelo.equipo if modelo else EquiposServicios.objects.filter(nombre__icontains=nombre_tipo).first()
        if tipo is None:
            raise CommandError(f'La unidad no tiene un equipo «{nombre_tipo}» para el ejemplo.')
        area = modelo.espacios_asociados.filter(unidad=unidad).order_by('orden', 'nombre').first() if modelo else None
        area = area or EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre').first()
        equipo = UnidadEquipo(
            codigo_unidad=siguiente_codigo_unidad(unidad, area, tipo), equipo=tipo, laboratorio=unidad,
            estado_unidad='disponible', criticidad='normal', observaciones=f'{MARCA} {caso}', custodio='Custodio de ejemplo',
            tipo_bien='BLD', ubicacion_especifica=modelo.ubicacion_especifica if modelo else '', **campos,
        )
        equipo.save()
        equipo.laboratorios.add(unidad)
        if area:
            area.equipos_asociados.add(equipo)
        return equipo

    def _casos(self, unidad, destino):
        ahora = timezone.now()
        hoy = timezone.localdate()
        casos = []
        prestado = self._equipo(unidad, 'Portátil', 'Equipo prestado.', codigo_bien='99009001')
        PrestamoEquipo.objects.create(
            equipo=prestado, unidad=unidad, tipo='interno', estado='entregado', nombre_solicitante='Estudiante de ejemplo',
            proposito=f'{MARCA} Proyecto de titulación fuera del laboratorio.', fecha_salida=ahora - timedelta(days=2),
            fecha_retorno_previsto=ahora + timedelta(days=5))
        casos.append((prestado.codigo_unidad, 'prestado: estado «Prestado» y préstamo en su historia'))
        averiado = self._equipo(unidad, 'Impresora 3D FDM', 'Equipo con incidencia.', codigo_bien='99009002')
        IncidenciaEquipo.objects.create(
            equipo=averiado, titulo=f'{MARCA} Extrusor obstruido',
            descripcion='La boquilla no deja pasar el filamento; la impresora no puede usarse hasta limpiarla.',
            tipo='falla', prioridad='alta', estado='abierta', detiene_operacion=True)
        casos.append((averiado.codigo_unidad, 'incidencia abierta que detiene la operación: semáforo crítico'))
        antiguo = self._equipo(unidad, 'Fresadora', 'Equipo con vida útil cumplida.', codigo_bien='99009003',
                               fecha_adquisicion=hoy - timedelta(days=365 * 9), vida_util_anios=6)
        casos.append((antiguo.codigo_unidad, 'vida útil cumplida: el lector sugiere planificar su reemplazo'))
        sin_mantenimiento = self._equipo(unidad, 'Cortadora', 'Equipo con mantenimiento vencido.',
                                         codigo_bien='99009004')
        PlanMantenimientoEquipo.objects.create(
            equipo=sin_mantenimiento, nombre=f'{MARCA} Limpieza de lentes y espejos', tipo='preventivo',
            proxima_ejecucion=hoy - timedelta(days=20))
        casos.append((sin_mantenimiento.codigo_unidad, 'mantenimiento vencido hace 20 días: requiere atención'))
        viajero = self._equipo(unidad, 'Secador', 'Equipo transferido entre unidades.', codigo_bien='99009005')
        anterior = viajero.codigo_unidad
        viajero.espacios_asociados.clear()
        viajero.laboratorio = destino
        area_destino = EspacioReservable.objects.filter(unidad=destino, activo=True).order_by('orden', 'nombre').first()
        # En la unidad de destino toma el código estándar de allá; el anterior queda como alias.
        viajero.codigo_unidad = siguiente_codigo_unidad(destino, area_destino, viajero.equipo)
        viajero.save()
        viajero.laboratorios.set([destino])
        if area_destino:
            area_destino.equipos_asociados.add(viajero)
        casos.append((anterior, f'transferido a {destino.nombre} con el código {viajero.codigo_unidad}; el anterior sigue funcionando'))
        return casos

    @staticmethod
    def _uso(unidad):
        """Reservas atendidas de ejemplo para las impresoras FDM: el tablero muestra horas y su diagnóstico."""
        impresoras = list(UnidadEquipo.objects.filter(laboratorio=unidad, activa=True, equipo__familia__nombre__icontains='FDM')
                          .exclude(observaciones__startswith=MARCA).order_by('codigo_unidad')[:3])
        if not impresoras:
            return 0
        usuario = (get_user_model().objects.filter(username='demo.solicitante.fablab').first()
                   or get_user_model().objects.filter(is_superuser=True).first())
        seleccion = '[' + ', '.join(f'{{"codigo": "{equipo.codigo_unidad}"}}' for equipo in impresoras) + ']'
        hoy = timezone.localdate()
        for dia in range(110):
            Reserva.objects.create(
                laboratorio=unidad, usuario=usuario, equipo_nombre=impresoras[0].equipo.nombre,
                unidades_seleccionadas=seleccion, fecha=hoy - timedelta(days=2 + dia * 3), hora_inicio=time(7, 0),
                hora_fin=time(19, 0), estado='completada', proposito_codigo='docencia_practica',
                titulo_solicitud=f'{MARCA} Práctica de impresión 3D', numero_participantes=12)
        return 12 * 110 * len(impresoras)
