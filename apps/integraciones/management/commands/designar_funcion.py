"""Registra o revoca una designación funcional documentada; sin --aplicar solo ensaya."""
from datetime import date

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models.gobernanza import AsignacionGobernanza

ROLES = dict(AsignacionGobernanza.ROLES)


def _fecha(texto, nombre):
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise CommandError(f'{nombre} debe escribirse como AAAA-MM-DD.') from None


def _cuenta(nombre, *, etiqueta):
    cuenta = get_user_model().objects.filter(username=nombre).first()
    if cuenta is None:
        raise CommandError(f'No existe la cuenta «{nombre}» ({etiqueta}).')
    if not cuenta.is_active:
        raise CommandError(f'La cuenta «{nombre}» ({etiqueta}) está inactiva.')
    return cuenta


def unidades_que_no_puede_revisar(cuenta):
    """La revisión es independiente: nadie evalúa la unidad que administra o coordina."""
    from apps.directorio_unidades.models.core import Unidad
    return list(Unidad.objects.filter(
        Q(administrador=cuenta) | Q(responsables_unidad__usuario=cuenta, responsables_unidad__activo=True,
                                    responsables_unidad__rol='coordinacion')
    ).distinct().order_by('nombre').values_list('nombre', flat=True))


class Command(BaseCommand):
    help = ('Registra o revoca una designación funcional documentada (seguimiento, adscripción, Centro, '
            'investigación). Sin --aplicar solo muestra lo que haría.')

    def add_arguments(self, parser):
        parser.add_argument('--listar', action='store_true', help='Muestra las designaciones registradas.')
        parser.add_argument('--usuario', help='Cuenta que recibe o pierde la función.')
        parser.add_argument('--rol', choices=sorted(ROLES), help='Función que se designa.')
        parser.add_argument('--referencia', default='',
                            help='ID de la dependencia (adscripcion) o identificador público del Centro (centro).')
        parser.add_argument('--acto', default='', help='Acto de asignación y su alcance.')
        parser.add_argument('--dedicacion', default='', help='Dedicación y cobertura autorizadas.')
        parser.add_argument('--desde', help='Inicio de la vigencia, AAAA-MM-DD. Por omisión, hoy.')
        parser.add_argument('--hasta', help='Fin de la vigencia, AAAA-MM-DD. Por omisión, sin fecha final.')
        parser.add_argument('--registra', help='Superusuario que registra el acto. Por omisión, el único activo.')
        parser.add_argument('--revocar', action='store_true', help='Deja sin efecto la designación vigente.')
        parser.add_argument('--aplicar', action='store_true', help='Escribe el cambio. Sin esta opción solo ensaya.')

    def handle(self, *args, **opciones):
        if opciones['listar']:
            return self._listar()
        if not opciones['usuario'] or not opciones['rol']:
            raise CommandError('Indique --usuario y --rol, o use --listar.')
        cuenta = _cuenta(opciones['usuario'], etiqueta='quien recibe la función')
        registra = self._quien_registra(opciones['registra'])
        referencia = opciones['referencia'].strip()
        hoy = timezone.localdate()
        opciones['desde'] = _fecha(opciones['desde'], '--desde') if opciones['desde'] else hoy
        opciones['hasta'] = _fecha(opciones['hasta'], '--hasta') if opciones['hasta'] else None
        vigentes = (AsignacionGobernanza.objects
                    .filter(usuario=cuenta, rol=opciones['rol'], referencia=referencia, activa=True)
                    .filter(Q(hasta__isnull=True) | Q(hasta__gte=hoy)))
        with transaction.atomic():
            if opciones['revocar']:
                self._revocar(vigentes, cuenta, registra, opciones)
            else:
                self._designar(vigentes, cuenta, registra, referencia, hoy, opciones)
            if not opciones['aplicar']:
                transaction.set_rollback(True)
                self.stdout.write('ENSAYO: no se escribió nada. Repita con --aplicar para registrarlo.')

    # ---- Casos ---------------------------------------------------------------------------------

    def _designar(self, vigentes, cuenta, registra, referencia, hoy, opciones):
        etiqueta = ROLES[opciones['rol']]
        if vigentes.exists():
            self.stdout.write(f'«{cuenta.username}» ya tiene registrada y activa la función «{etiqueta}». '
                              'No se duplica.')
            return
        designacion = AsignacionGobernanza(
            usuario=cuenta, rol=opciones['rol'], referencia=referencia, acto=opciones['acto'].strip(),
            dedicacion=opciones['dedicacion'].strip(), activa=True, registrado_por=registra,
            desde=opciones['desde'], hasta=opciones['hasta'])
        try:
            designacion.full_clean()
        except ValidationError as error:
            raise CommandError(' '.join(error.messages)) from None
        designacion.save()
        LogEntry.objects.log_actions(registra.pk, [designacion], ADDITION, single_object=True,
                                     change_message=f'Designación registrada por comando: {designacion.acto}')
        self.stdout.write(f'Designación: «{cuenta.username}» · {etiqueta}'
                          f'{" · " + referencia if referencia else ""} · desde {designacion.desde:%d/%m/%Y}'
                          f'{f" hasta {designacion.hasta:%d/%m/%Y}" if designacion.hasta else ""} · '
                          f'registra «{registra.username}».')
        if opciones['rol'] == 'seguimiento':
            propias = unidades_que_no_puede_revisar(cuenta)
            if propias:
                self.stdout.write(self.style.WARNING(
                    'Aviso: esta cuenta administra o coordina ' + ', '.join(propias) +
                    '. No podrá revisar los documentos de esas unidades: la revisión exige otra persona.'))
            if designacion.desde > hoy:
                self.stdout.write(self.style.WARNING('Aviso: la función empieza a regir en la fecha indicada.'))

    def _revocar(self, vigentes, cuenta, registra, opciones):
        etiqueta = ROLES[opciones['rol']]
        designaciones = list(vigentes)
        if not designaciones:
            self.stdout.write(f'«{cuenta.username}» no tiene vigente la función «{etiqueta}». Nada que revocar.')
            return
        for designacion in designaciones:
            designacion.activa = False
            designacion.save(update_fields=['activa', 'actualizado_en'])
            LogEntry.objects.log_actions(registra.pk, [designacion], CHANGE, single_object=True,
                                         change_message='Designación revocada por comando.')
        self.stdout.write(f'Revocada la función «{etiqueta}» de «{cuenta.username}» '
                          f'({len(designaciones)} designación). El historial se conserva.')

    def _listar(self):
        hoy = timezone.localdate()
        designaciones = AsignacionGobernanza.objects.select_related('usuario').order_by('rol', 'usuario__username')
        if not designaciones:
            self.stdout.write('No hay designaciones registradas: nadie puede revisar documentos.')
        for d in designaciones:
            vigente = d.activa and d.usuario.is_active and d.desde <= hoy and (d.hasta is None or d.hasta >= hoy)
            self.stdout.write(f'{"VIGENTE " if vigente else "sin efecto"} · {d.usuario.username} · '
                              f'{d.get_rol_display()}{" · " + d.referencia if d.referencia else ""} · '
                              f'desde {d.desde:%d/%m/%Y}{f" hasta {d.hasta:%d/%m/%Y}" if d.hasta else ""} · {d.acto}')

    def _quien_registra(self, nombre):
        if nombre:
            cuenta = _cuenta(nombre, etiqueta='quien registra')
            if not cuenta.is_superuser:
                raise CommandError('Solo la administración técnica (superusuario) registra designaciones.')
            return cuenta
        activos = list(get_user_model().objects.filter(is_superuser=True, is_active=True)[:2])
        if len(activos) != 1:
            raise CommandError('Indique con --registra el superusuario que registra el acto.')
        return activos[0]
