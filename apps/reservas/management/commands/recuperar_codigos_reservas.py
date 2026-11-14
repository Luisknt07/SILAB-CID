"""Reconciliacion administrativa por unidad, con diagnostico predeterminado."""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.models import Q

from apps.reservas.services.codigos_reserva import EVENTO_RECUPERACION_FALLIDA, ReservaFueraDeAlcance, asegurar_codigo_reserva, logger
from apps.reservas.presentation.capacidad import CapacidadReservasSuspendida, bloquear_operacion_reservas


class Command(BaseCommand):
    help = 'Cuenta codigos faltantes; --aplicar --unidad ID reconcilia sin reemplazar existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default', choices=tuple(connections))
        parser.add_argument('--unidad', type=int, help='ID de unidad; obligatorio para aplicar.')
        parser.add_argument('--aplicar', action='store_true', help='Escritura explicita, solo en la unidad indicada.')

    def handle(self, *args, **options):
        unidad = options['unidad']
        if (unidad is not None and unidad <= 0) or (options['aplicar'] and unidad is None):
            raise CommandError('Para aplicar indica una unidad positiva; sin --aplicar solo se audita.')
        alias = options['database']
        from django.apps import apps

        modelo = apps.get_model('reservas', 'Reserva')
        candidatas = modelo._base_manager.using(alias).filter(
            Q(codigo_reserva__isnull=True) | Q(codigo_reserva='')).order_by('pk')
        if unidad is not None:
            candidatas = candidatas.filter(laboratorio_id=unidad)
        resumen = {'modo': 'aplicacion' if options['aplicar'] else 'auditoria',
                   'pendientes_observados': 0, 'asignados': 0, 'ya_existentes': 0,
                   'fuera_de_alcance': 0, 'fallidos': 0}
        try:
            resumen['pendientes_observados'] = candidatas.count()
            if options['aplicar']:
                try:
                    with bloquear_operacion_reservas():
                        for reserva in candidatas.only('pk').iterator(chunk_size=100):
                            try:
                                resultado = asegurar_codigo_reserva(
                                    reserva,
                                    using=alias,
                                    unidad_esperada=unidad,
                                )
                                clave = (
                                    'asignados'
                                    if resultado.asignado
                                    else 'ya_existentes'
                                )
                                resumen[clave] += 1
                            except ReservaFueraDeAlcance:
                                resumen['fuera_de_alcance'] += 1
                            except Exception:
                                logger.warning(EVENTO_RECUPERACION_FALLIDA)
                                resumen['fallidos'] += 1
                except CapacidadReservasSuspendida as error:
                    raise CommandError(str(error)) from None
        except CommandError:
            raise
        except Exception:
            logger.warning(EVENTO_RECUPERACION_FALLIDA)
            raise CommandError('No se pudo completar la reconciliacion; revisa el registro operativo seguro.') from None
        self.stdout.write(json.dumps(resumen, indent=2))
        if resumen['fallidos'] or resumen['fuera_de_alcance']:
            raise CommandError('Reconciliacion parcial; revisar y reintentar dentro del alcance autorizado.')
