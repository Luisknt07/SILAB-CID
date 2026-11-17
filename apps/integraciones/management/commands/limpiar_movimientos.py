"""Deja la base sin movimientos de prueba para empezar a registrar los reales.

Borra lo que las unidades registran al operar (reservas, prácticas, documentos generados, evidencias,
mantenimientos, producción, auditoría) y conserva lo que describe a la institución (unidades, espacios,
equipos, existencias, software, asignaturas, guías, catálogos, cursos, portal y cuentas reales).

Sin ``--aplicar`` solo ensaya: hace todo dentro de una transacción, informa y la revierte.
"""
import shutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, models, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError

FRASE = 'BORRAR-MOVIMIENTOS'
# Todo lo que una unidad registra al operar. Se vacía la tabla completa.
MOVIMIENTOS = (
    # Expediente: documentos y anexos generados, su control y sus constancias.
    'documentos.ControlAutomaticoDocumento', 'documentos.PresentacionDocumento', 'documentos.ConstanciaDocumento',
    'documentos.AvisoDocumental', 'documentos.UltimatumDocumental', 'documentos.SeguimientoMejora',
    'documentos.AccionMejora', 'documentos.InformeMejora', 'documentos.DocumentoElaborado',
    'documentos.EvidenciaGestionUnidad', 'documentos.DocumentoExpediente',
    # Prácticas, aula y simulador.
    'formacion.EvidenciaPractica', 'formacion.EjecucionPractica', 'formacion.PlanificacionPractica',
    'formacion.IntentoEjercicio', 'formacion.EjercicioAula', 'formacion.EventoPartida',
    'formacion.ParticipantePartida', 'formacion.PartidaSimulador', 'formacion.SimulacionGuardada',
    'formacion.ComentarioLeccion',
    # Equipos: agenda bloqueada, alertas, préstamos, mantenimiento con su plan, incidencias y desechos.
    'gestion_unidades.BloqueoAgendaUnidad', 'recursos.AlertaUsoEquipo', 'recursos.RepuestoMantenimiento',
    'recursos.PrestamoEquipo', 'recursos.MantenimientoEquipo', 'recursos.PlanMantenimientoEquipo',
    'recursos.DiagnosticoIncidenciaEquipo', 'recursos.ServicioReparacionEquipo', 'recursos.IncidenciaEquipo',
    'recursos.RegistroDesecho', 'recursos.SesionNavegador', 'recursos.EquipoEnTraspaso', 'recursos.TraspasoEquipo',
    'recursos.LineaConteo', 'recursos.ConteoInventario', 'recursos.SolicitudAdquisicionRecurso',
    # Fabricación y servicios.
    'laboratorios_operacion.SolicitudConsumible', 'laboratorios_operacion.SolicitudFabricacion',
    # Plantas piloto: planes, órdenes, lotes, calidad y abastecimiento.
    'plantas_operacion.MedicionCalidad', 'plantas_operacion.AccionCorrectiva', 'plantas_operacion.NoConformidad',
    'plantas_operacion.ControlCalidad', 'plantas_operacion.EntregaPedido', 'plantas_operacion.PedidoAbastecimiento',
    'plantas_operacion.LineaPlanMaestro', 'plantas_operacion.PlanMaestro', 'plantas_operacion.LineaPlanVentas',
    'plantas_operacion.PlanVentas', 'plantas_operacion.SesionERP', 'plantas_operacion.MovimientoProducto',
    'plantas_operacion.LoteProducto', 'plantas_operacion.OrdenProduccion',
    # Finanzas.
    'finanzas.MovimientoFinancieroUnidad', 'finanzas.OrdenCompra',
    # Reservas, visitas e ingresos.
    'reservas.RegistroIngreso', 'reservas.HabilitacionAcceso', 'reservas.AsistenteVisita', 'reservas.SolicitudVisita',
    'reservas.ProgramacionReserva', 'reservas.NotificacionReserva', 'reservas.RegistroParticipanteReserva',
    'reservas.ReservaConsumible', 'reservas.RevisionReserva', 'reservas.SolicitudCambioReserva',
    'reservas.ReservaAdjunto', 'reservas.Reserva',
    # Rastro de lo anterior.
    'formacion.RegistroAuditoriaUnidad', 'admin.LogEntry', 'observacion.DescargaDatos',
)
# Cuentas de demostración: se reconocen por su nombre de usuario.
CUENTAS_DEMO = ('demo.', '.demo.', 'estudiante.prueba', 'sistema.demostrativo')
# Lo que una cuenta arrastra sin ser dato de la institución.
PROPIO_DE_LA_CUENTA = {'auth.User', 'core.UserProfile', 'account.EmailAddress', 'core.VinculacionUsuarioPeriodo',
                       'gestion_unidades.ResponsableUnidad', 'socialaccount.SocialAccount', 'socialaccount.SocialToken'}


def _modelo(etiqueta):
    try:
        modelo = apps.get_model(etiqueta)
    except LookupError as error:
        raise CommandError(f'No existe el modelo {etiqueta}: revise la lista de movimientos.') from error
    if modelo._meta.proxy:
        raise CommandError(f'{etiqueta} es un modelo proxy; use el modelo que tiene la tabla.')
    return modelo


def _tabla(modelo):
    return connection.ops.quote_name(modelo._meta.db_table)


class Command(BaseCommand):
    help = 'Borra los movimientos de prueba y conserva catálogos y configuración. Sin --aplicar solo ensaya.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Confirma los cambios. Sin esta opción solo ensaya.')
        parser.add_argument('--confirmar', default='', help=f'Frase exacta para aplicar: {FRASE}')
        parser.add_argument('--base', default='', help='Nombre de la base sobre la que se espera actuar.')
        parser.add_argument('--retirar-archivos-a', default='',
                            help='Carpeta adonde se mueven los archivos de lo borrado. Sin ella, los archivos se dejan.')
        parser.add_argument('--listar-archivos', action='store_true',
                            help='Escribe la ruta de cada archivo de lo borrado, para retirarlos después.')

    def handle(self, *args, **opciones):
        base = connection.settings_dict['NAME']
        aplicar = opciones['aplicar']
        if aplicar and opciones['confirmar'] != FRASE:
            raise CommandError(f'Para aplicar escriba --confirmar {FRASE}')
        if aplicar and opciones['base'] != base:
            raise CommandError(f'Esta conexión usa la base «{base}». Para aplicar indique --base {base}')
        self.stdout.write(f'Base: {base} · modo: {"APLICAR" if aplicar else "ensayo (se revierte)"}')
        movimientos = [_modelo(etiqueta) for etiqueta in MOVIMIENTOS]
        if len(set(movimientos)) != len(movimientos):
            raise CommandError('La lista de movimientos repite un modelo.')
        self.objetivos = set(movimientos)
        archivos, vaciadas = [], []
        try:
            with transaction.atomic():
                conservados = self._conteo_de_conservados()
                recursos = self._recursos_del_expediente(movimientos)
                archivos = self._archivos(movimientos, recursos)
                self._soltar_referencias()
                self._vaciar_relaciones_multiples()
                for modelo in movimientos:
                    filas = modelo._base_manager.count()
                    if filas:
                        modelo._base_manager.all()._raw_delete(connection.alias)
                        vaciadas.append(modelo)
                    self.stdout.write(f'  {modelo._meta.label:48} {filas:>6} filas borradas')
                Recurso = apps.get_model('recursos.Recurso')
                Recurso._base_manager.filter(pk__in=recursos)._raw_delete(connection.alias)
                self.stdout.write(f'  {"recursos.Recurso (archivos del expediente)":48} {len(recursos):>6} filas borradas')
                # Cualquier referencia que quede hacia algo borrado detiene todo aquí, antes de confirmar.
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                    cursor.execute('SET CONSTRAINTS ALL DEFERRED')
                cuentas = self._retirar_cuentas_demo()
                self._comprobar_conservados(conservados, recursos=len(recursos), cuentas=cuentas)
                if not aplicar:
                    transaction.set_rollback(True)
        except IntegrityError as error:
            raise CommandError(f'Quedan referencias hacia lo borrado; no se cambió nada. {str(error)[:400]}') from error
        self.stdout.write(f'Archivos de lo borrado: {len(archivos)}')
        if opciones['listar_archivos']:
            for nombre in archivos:
                self.stdout.write(f'ARCHIVO {nombre}')
        if not aplicar:
            self.stdout.write(self.style.WARNING('Ensayo terminado: no se cambió nada.'))
            return
        self._reiniciar_numeracion(vaciadas)
        if opciones['retirar_archivos_a']:
            self._retirar_archivos(archivos, Path(opciones['retirar_archivos_a']))
        self.stdout.write(self.style.SUCCESS('Limpieza aplicada.'))

    # ---- Lo que se conserva -------------------------------------------------------------------

    def _modelos_conservados(self):
        return [m for m in apps.get_models()
                if not m._meta.proxy and m._meta.managed and m not in self.objetivos
                and m._meta.app_label not in ('centros_id', 'sessions', 'contenttypes')]

    def _conteo_de_conservados(self):
        return {m: m._base_manager.count() for m in self._modelos_conservados()}

    def _comprobar_conservados(self, antes, *, recursos, cuentas):
        """Nada fuera de la lista puede perder filas, salvo los archivos del expediente y las cuentas demo."""
        permitido = dict(cuentas)
        permitido['recursos.Recurso'] = permitido.get('recursos.Recurso', 0) + recursos
        diferencias = []
        for modelo, cantidad in antes.items():
            perdidas = cantidad - modelo._base_manager.count()
            if perdidas != permitido.get(modelo._meta.label, 0):
                diferencias.append(f'{modelo._meta.label}: {perdidas} filas menos; se esperaban '
                                   f'{permitido.get(modelo._meta.label, 0)}')
        if diferencias:
            raise CommandError('La limpieza tocaría datos que deben conservarse; no se cambió nada. '
                               + ' | '.join(diferencias))
        self.stdout.write(f'Conservados sin cambios: {len(antes)} tablas de catálogos y configuración.')

    # ---- Referencias hacia lo que se borra -----------------------------------------------------

    def _soltar_referencias(self):
        """Una fila que se conserva deja de señalar al movimiento borrado; si no puede, se detiene."""
        for modelo in self._modelos_conservados():
            for campo in modelo._meta.concrete_fields:
                destino = getattr(campo, 'remote_field', None) and campo.remote_field.model
                if destino not in self.objetivos:
                    continue
                filas = modelo._base_manager.exclude(**{campo.name: None})
                cantidad = filas.count()
                if not cantidad:
                    continue
                if not campo.null:
                    raise CommandError(f'{modelo._meta.label}.{campo.name} es obligatorio y señala a '
                                       f'{destino._meta.label} ({cantidad} filas). Decida si ese modelo es un movimiento.')
                filas.update(**{campo.name: None})
                self.stdout.write(f'  {modelo._meta.label}.{campo.name}: {cantidad} filas dejan de señalar a '
                                  f'{destino._meta.label}')

    def _vaciar_relaciones_multiples(self):
        vistas = set()
        for modelo in apps.get_models():
            if modelo._meta.proxy:
                continue
            for campo in modelo._meta.local_many_to_many:
                tabla = campo.remote_field.through
                if tabla in vistas or not tabla._meta.auto_created:
                    continue
                if modelo in self.objetivos or campo.remote_field.model in self.objetivos:
                    vistas.add(tabla)
                    tabla._base_manager.all()._raw_delete(connection.alias)

    # ---- Archivos ------------------------------------------------------------------------------

    def _recursos_del_expediente(self, movimientos):
        """Los archivos que solo existen por un documento, una evidencia o un informe que se borra."""
        Recurso = apps.get_model('recursos.Recurso')
        ids = set()
        # Solo estos movimientos son dueños de su archivo. Una sesión de navegador o un control también
        # señalan a un recurso, pero es de la biblioteca de la unidad y se conserva.
        for etiqueta in ('documentos.DocumentoExpediente', 'documentos.InformeMejora'):
            ids.update(apps.get_model(etiqueta)._base_manager.exclude(recurso=None)
                       .values_list('recurso_id', flat=True))
        # Una evidencia puede citar un recurso de la biblioteca: solo se borra el que se subió como evidencia.
        de_evidencias = (apps.get_model('documentos.EvidenciaGestionUnidad')._base_manager.exclude(recurso=None)
                         .values_list('recurso_id', flat=True))
        ids.update(Recurso._base_manager.filter(pk__in=de_evidencias, tipo_adjunto='evidencia')
                   .values_list('pk', flat=True))
        ids.update(Recurso._base_manager.filter(palabras_clave__startswith='expediente')
                   .values_list('pk', flat=True))
        frontera = set(ids)
        while frontera:
            frontera = set(Recurso._base_manager.filter(pk__in=frontera).exclude(reemplaza_a=None)
                           .values_list('reemplaza_a_id', flat=True)) - ids
            ids |= frontera
        return ids

    def _archivos(self, movimientos, recursos):
        Recurso = apps.get_model('recursos.Recurso')
        nombres = []
        for modelo, filas in [(m, m._base_manager.all()) for m in movimientos] + [
                (Recurso, Recurso._base_manager.filter(pk__in=recursos))]:
            for campo in modelo._meta.concrete_fields:
                if isinstance(campo, models.FileField):
                    nombres.extend(n for n in filas.exclude(**{campo.name: ''}).values_list(campo.name, flat=True) if n)
        # Un archivo que también usa un recurso que se conserva no se retira.
        en_uso = set(Recurso._base_manager.exclude(pk__in=recursos).exclude(archivo='')
                     .values_list('archivo', flat=True))
        return sorted(set(nombres) - en_uso)

    def _retirar_archivos(self, archivos, destino):
        raiz = Path(settings.MEDIA_ROOT).resolve()
        movidos = 0
        for nombre in archivos:
            origen = (raiz / nombre).resolve()
            if raiz not in origen.parents or not origen.is_file():
                continue
            final = destino / nombre
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origen), str(final))
            movidos += 1
        self.stdout.write(f'Archivos movidos a {destino}: {movidos} de {len(archivos)}')

    # ---- Cuentas de demostración -----------------------------------------------------------------

    def _retirar_cuentas_demo(self):
        """Borra la cuenta si solo arrastra lo suyo; si está ligada a datos que se conservan, la desactiva."""
        borradas = {}
        for usuario in get_user_model()._base_manager.order_by('username'):
            nombre = usuario.username or ''
            if not any(marca in nombre for marca in CUENTAS_DEMO):
                continue
            recolector = Collector(using=connection.alias)
            try:
                recolector.collect([usuario])
            except (ProtectedError, RestrictedError) as error:
                ajenos = sorted({type(o)._meta.label for o in error.args[1]})
            else:
                afectados = {m._meta.label: len(objetos) for m, objetos in recolector.data.items()}
                for consulta in recolector.fast_deletes:
                    etiqueta = consulta.model._meta.label
                    cantidad = consulta.count()
                    if cantidad:
                        afectados[etiqueta] = afectados.get(etiqueta, 0) + cantidad
                ajenos = sorted(e for e in afectados if e not in PROPIO_DE_LA_CUENTA
                                and not apps.get_model(e)._meta.auto_created)
                if not ajenos:
                    # Lo que se conserva y la nombraba (autor, administrador) queda sin esa referencia.
                    sueltas = []
                    for (campo, _valor), grupos in recolector.field_updates.items():
                        total = sum(len(grupo) for grupo in grupos)
                        if total:
                            sueltas.append(f'{campo.model._meta.label}.{campo.name}: {total}')
                    usuario.delete()
                    for etiqueta, cantidad in afectados.items():
                        if not apps.get_model(etiqueta)._meta.auto_created:
                            borradas[etiqueta] = borradas.get(etiqueta, 0) + cantidad
                    self.stdout.write(f'  cuenta {nombre}: borrada'
                                      + (f' (quedan sin esa referencia: {", ".join(sorted(sueltas))})' if sueltas else ''))
                    continue
            if usuario.is_active:
                get_user_model()._base_manager.filter(pk=usuario.pk).update(is_active=False)
            self.stdout.write(f'  cuenta {nombre}: desactivada (la usan {", ".join(ajenos)[:160]})')
        return borradas

    # ---- Numeración ------------------------------------------------------------------------------

    def _reiniciar_numeracion(self, vaciadas):
        """Una tabla que quedó vacía vuelve a numerar desde 1 (fuera de la transacción: no se revierte)."""
        with connection.cursor() as cursor:
            for modelo in vaciadas:
                clave = modelo._meta.pk
                if not isinstance(clave, models.AutoField):
                    continue
                cursor.execute('SELECT pg_get_serial_sequence(%s, %s)', [modelo._meta.db_table, clave.column])
                secuencia = cursor.fetchone()[0]
                if secuencia:
                    cursor.execute('SELECT setval(%s, 1, false)', [secuencia])
        self.stdout.write(f'Numeración reiniciada en {len(vaciadas)} tablas.')
