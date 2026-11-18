"""Carga en una unidad un registro de prueba válido por cada documento del Centro de reportes, y lo retira.

Recorre las mismas pantallas que las pruebas de captura (``tests/integration/test_rutas_de_captura_*.py``) con las
cuentas reales de la unidad. Todo texto libre empieza con «[PRUEBA] » y todo código elegible con «PRUEBA-».

Sin ``--aplicar`` solo ensaya: hace todo dentro de una transacción, informa y la revierte (y borra los archivos que
subió). Con ``--aplicar --base <base>`` confirma y guarda el manifiesto en ``var/registros_de_prueba/``: lo creado
(modelo y pk), lo que cambió en registros que ya existían y los documentos del expediente que cambiaron de estado.
``--retirar <manifiesto>`` borra lo creado en orden inverso y devuelve lo cambiado a su valor anterior si nadie lo
tocó después; también ensaya salvo con ``--aplicar --base``.
"""
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, connection, models, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_save
from django.test.utils import override_settings
from django.utils import timezone

from apps.integraciones.carga_de_prueba import NOMBRES, CargaDePrueba

UNIDAD = 'laboratorio-fabricacion-digital-prototipado'
# Lo que la sesión de consola crea o toca y no es dato de la carga.
NO_RASTREAR = {'sessions.Session'}
CAMPOS_IGNORADOS = {'auth.User': {'last_login'}, 'core.UserProfile': {'fecha_actualizacion'}}
# Filas de la unidad que se fotografían antes y después: así se ve también lo que se cambia con update().
DE_LA_UNIDAD = (
    ('directorio_unidades.Unidad', 'pk'), ('gestion_unidades.EspacioReservable', 'unidad'),
    ('gestion_unidades.ResponsableUnidad', 'unidad'), ('gestion_unidades.ConfiguracionOperativaUnidad', 'unidad'),
    ('recursos.ReglamentoUnidad', 'unidad'), ('recursos.UnidadEquipo', 'laboratorio'),
    ('recursos.Consumible', 'unidad'), ('documentos.DocumentoExpediente', 'unidad'),
    ('formacion.Asignatura', 'unidad'), ('reservas.GuiaActividadReserva', 'actividad__unidad'),
)


def _etiqueta(modelo):
    return modelo._meta.concrete_model._meta.label


def _valores(modelo, pks):
    """Los valores de los campos concretos, ya serializables, por pk."""
    campos = [c for c in modelo._meta.concrete_fields if not c.primary_key]
    ignorados = CAMPOS_IGNORADOS.get(_etiqueta(modelo), set())
    filas = modelo._base_manager.filter(pk__in=list(pks)).values('pk', *[c.attname for c in campos])
    return {fila.pop('pk'): json.loads(json.dumps({k: v for k, v in fila.items() if k not in ignorados},
                                                  cls=DjangoJSONEncoder)) for fila in filas}


class Rastreo:
    """Lo que la carga crea (también por bulk_create) y lo que cambia en filas que ya existían."""

    def __init__(self):
        self.creados, self.claves, self.tocados = [], set(), []
        self._antes = {}
        self._bulk = None

    def marca(self):
        return len(self.creados), len(self.tocados)

    def volver(self, marca):
        creados, tocados = marca
        for etiqueta, pk in self.creados[creados:]:
            self.claves.discard((etiqueta, pk))
        for clave in self.tocados[tocados:]:
            self._antes.pop(clave, None)
        del self.creados[creados:]
        del self.tocados[tocados:]

    def _crear(self, instancia, alias):
        etiqueta = _etiqueta(type(instancia))
        if etiqueta in NO_RASTREAR or instancia.pk is None:
            return
        if alias != 'default':
            raise CommandError(f'{etiqueta} se escribió en la base «{alias}»: la carga solo admite la principal.')
        clave = (etiqueta, instancia.pk)
        if clave not in self.claves:
            self.claves.add(clave)
            self.creados.append(clave)

    def _al_guardar(self, sender, instance, created, using, raw=False, **kwargs):
        if created and not raw:
            self._crear(instance, using)

    def _antes_de_guardar(self, sender, instance, using, raw=False, **kwargs):
        if raw or instance._state.adding or instance.pk is None:
            return
        etiqueta = _etiqueta(sender)
        clave = (etiqueta, instance.pk)
        if etiqueta in NO_RASTREAR or clave in self.claves or clave in self._antes:
            return
        valores = _valores(sender._meta.concrete_model, [instance.pk]).get(instance.pk)
        if valores is not None:
            self._antes[clave] = valores
            self.tocados.append(clave)

    def conectar(self):
        post_save.connect(self._al_guardar, weak=False, dispatch_uid='carga_de_prueba_creados')
        pre_save.connect(self._antes_de_guardar, weak=False, dispatch_uid='carga_de_prueba_tocados')
        original = QuerySet.bulk_create
        rastreo = self

        def bulk_create(consulta, objetos, *args, **kwargs):
            creados = original(consulta, objetos, *args, **kwargs)
            for objeto in creados:
                rastreo._crear(objeto, consulta.db)
            return creados

        self._bulk = original
        QuerySet.bulk_create = bulk_create

    def desconectar(self):
        post_save.disconnect(dispatch_uid='carga_de_prueba_creados')
        pre_save.disconnect(dispatch_uid='carga_de_prueba_tocados')
        if self._bulk is not None:
            QuerySet.bulk_create = self._bulk
            self._bulk = None

    def antes(self):
        return dict(self._antes)


@contextmanager
def _contexto_de_pantallas():
    """Las respuestas guardan su contexto (como en las pruebas), sin correos reales ni límite de peticiones."""
    from django.template import base
    from django.test.utils import instrumented_test_render

    original = base.Template._render
    base.Template._render = instrumented_test_render
    try:
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                               RATE_LIMIT_ENABLED=False):
            yield
    finally:
        base.Template._render = original


def _fotografia(unidad):
    """Las filas de la unidad que la carga podría cambiar sin save(): {(modelo, pk): valores}."""
    foto = {}
    for etiqueta, campo in DE_LA_UNIDAD:
        try:
            modelo = apps.get_model(etiqueta)
        except LookupError:
            continue
        pks = modelo._base_manager.filter(**{campo: unidad.pk if campo == 'pk' else unidad}).values_list('pk', flat=True)
        for pk, valores in _valores(modelo, pks).items():
            foto[(etiqueta, pk)] = valores
    return foto


def _maximos():
    """El mayor pk de cada tabla con clave entera, para ver después qué filas nuevas no se rastrearon."""
    maximos = {}
    for modelo in apps.get_models():
        if (modelo._meta.proxy or not modelo._meta.managed or _etiqueta(modelo) in NO_RASTREAR
                or not isinstance(modelo._meta.pk, models.AutoField) or modelo._meta.app_label == 'centros_id'):
            continue
        maximos[modelo] = modelo._base_manager.aggregate(m=models.Max('pk'))['m'] or 0
    return maximos


def _archivos_de(etiqueta, pks):
    modelo = apps.get_model(etiqueta)
    campos = [c.attname for c in modelo._meta.concrete_fields if isinstance(c, models.FileField)]
    if not campos:
        return []
    return [nombre for fila in modelo._base_manager.filter(pk__in=pks).values_list(*campos) for nombre in fila if nombre]


class Command(BaseCommand):
    help = ('Carga en la unidad un registro de prueba por cada documento del Centro de reportes, por sus pantallas. '
            'Sin --aplicar solo ensaya. --retirar <manifiesto> lo retira.')

    def add_arguments(self, parser):
        parser.add_argument('--unidad', default=UNIDAD, help='Identificador (slug) de la unidad.')
        parser.add_argument('--cuenta-unidad', default='admin.fablab', help='Cuenta que administra y coordina.')
        parser.add_argument('--usuario', default='estudiante.fablab01', help='Cuenta que reserva y valora.')
        parser.add_argument('--direccion', default='direccion.seguimiento',
                            help='Superusuario con la función de seguimiento vigente.')
        parser.add_argument('--validador', default='',
                            help='Quien valida lo que registró la cuenta de la unidad. Por omisión, otra persona '
                                 'activa del equipo humano con cuenta y permiso de prácticas.')
        parser.add_argument('--abrir-con-ultimatum', action='store_true',
                            help='Si un plazo venció sin ultimátum, la Dirección lo fija (colectivo: afecta a todas '
                                 'las unidades). Pensado para ensayar en una copia.')
        parser.add_argument('--aplicar', action='store_true', help='Confirma los cambios. Sin esta opción solo ensaya.')
        parser.add_argument('--base', default='', help='Nombre de la base sobre la que se espera actuar.')
        parser.add_argument('--retirar', default='', help='Manifiesto de una carga aplicada que se quiere retirar.')
        parser.add_argument('--carpeta', default='', help='Carpeta de los manifiestos (var/registros_de_prueba).')

    def handle(self, *args, **opciones):
        base = connection.settings_dict['NAME']
        aplicar = opciones['aplicar']
        if aplicar and opciones['base'] != base:
            raise CommandError(f'Esta conexión usa la base «{base}». Para aplicar indique --base {base}')
        self.stdout.write(f'Base: {base} · modo: {"APLICAR" if aplicar else "ensayo (se revierte)"}')
        if opciones['retirar']:
            return self._retirar(Path(opciones['retirar']), aplicar)
        return self._cargar(opciones, base, aplicar)

    # ---- carga ---------------------------------------------------------------------------------------

    def _cuentas(self, opciones, unidad):
        from apps.gestion_unidades.models.espacios import ResponsableUnidad
        from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

        usuarios = get_user_model()._base_manager
        cuentas = {}
        for clave in ('cuenta_unidad', 'usuario', 'direccion'):
            usuario = usuarios.filter(username=opciones[clave], is_active=True).first()
            if usuario is None:
                raise CommandError(f'No existe la cuenta activa «{opciones[clave]}».')
            cuentas[clave] = usuario
        if not cuentas['direccion'].is_superuser:
            raise CommandError(f'«{cuentas["direccion"].username}» no es superusuario: no decide por la Dirección.')
        if opciones['validador']:
            validador = usuarios.filter(username=opciones['validador'], is_active=True).first()
        else:
            candidatos = (ResponsableUnidad.objects.filter(unidad=unidad, activo=True, usuario__is_active=True)
                          .exclude(usuario=None).exclude(usuario=cuentas['cuenta_unidad'])
                          .select_related('usuario').order_by('usuario__is_superuser', 'pk'))
            validador = next((r.usuario for r in candidatos
                              if puede_operar_modulo_unidad(r.usuario, unidad, 'practicas')), None)
        if validador is None:
            raise CommandError('No hay otra persona activa del equipo humano con cuenta y permiso de prácticas para '
                               'validar lo que registra la cuenta de la unidad. Indíquela con --validador.')
        cuentas['validador'] = validador
        return cuentas

    def _cargar(self, opciones, base, aplicar):
        from apps.directorio_unidades.models.core import Unidad
        from apps.recursos.models.unidades import UnidadEquipo

        unidad = Unidad.objects.filter(slug=opciones['unidad']).first()
        if unidad is None:
            raise CommandError(f'No existe la unidad «{opciones["unidad"]}».')
        if UnidadEquipo.objects.filter(laboratorio=unidad, codigo_unidad='PRUEBA-EQ-01').exists():
            raise CommandError('La unidad ya tiene una carga de prueba (equipo PRUEBA-EQ-01). Retírela antes con '
                               '--retirar <manifiesto>.')
        cuentas = self._cuentas(opciones, unidad)
        self.stdout.write(f'Unidad: {unidad.nombre} ({unidad.slug}) · cuenta de la unidad: '
                          f'{cuentas["cuenta_unidad"].username} · usuario: {cuentas["usuario"].username} · '
                          f'valida: {cuentas["validador"].username} · Dirección: {cuentas["direccion"].username}')
        host = next((h for h in settings.ALLOWED_HOSTS if h not in ('*',) and not h.startswith('.')), 'localhost')
        rastreo = Rastreo()
        inicio = timezone.now()
        with _contexto_de_pantallas():
            try:
                with transaction.atomic():
                    maximos = _maximos()
                    foto_antes = _fotografia(unidad)
                    rastreo.conectar()
                    carga = CargaDePrueba(unidad, admin=cuentas['cuenta_unidad'], usuario=cuentas['usuario'],
                                          direccion=cuentas['direccion'], validador=cuentas['validador'], host=host,
                                          abrir_con_ultimatum=opciones['abrir_con_ultimatum'], rastreo=rastreo)
                    carga.ejecutar()
                    carga.verificar()
                    carga.cerrar_sesiones()
                    rastreo.desconectar()
                    sin_rastrear = self._sin_rastrear(maximos, rastreo)
                    modificados = self._modificados(rastreo, foto_antes, unidad)
                    archivos = sorted({n for etiqueta, pks in self._por_modelo(rastreo.creados).items()
                                       for n in _archivos_de(etiqueta, pks)}
                                      | {v for m in modificados for c, v in m['despues'].items()
                                         if v and self._es_archivo(m['modelo'], c)})
                    with connection.cursor() as cursor:
                        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                        cursor.execute('SET CONSTRAINTS ALL DEFERRED')
                    if not aplicar:
                        transaction.set_rollback(True)
            finally:
                rastreo.desconectar()
        self._informe(carga, rastreo, modificados, sin_rastrear)
        if not aplicar:
            borrados = sum(1 for nombre in archivos if self._borrar_archivo(nombre))
            self.stdout.write(f'Archivos subidos en el ensayo y borrados de MEDIA_ROOT: {borrados} de {len(archivos)}')
            self.stdout.write(self.style.WARNING('Ensayo terminado: no se cambió nada.'))
            return
        manifiesto = self._guardar_manifiesto(opciones, base, unidad, cuentas, inicio, carga, rastreo, modificados,
                                              archivos)
        self.stdout.write(self.style.SUCCESS(f'Carga aplicada. Manifiesto: {manifiesto}'))

    @staticmethod
    def _por_modelo(claves):
        grupos = {}
        for etiqueta, pk in claves:
            grupos.setdefault(etiqueta, []).append(pk)
        return grupos

    @staticmethod
    def _es_archivo(etiqueta, attname):
        modelo = apps.get_model(etiqueta)
        return any(c.attname == attname and isinstance(c, models.FileField) for c in modelo._meta.concrete_fields)

    def _sin_rastrear(self, maximos, rastreo):
        """Filas nuevas que la carga no vio crear. Las que señalan a lo creado son suyas y entran al manifiesto."""
        nuevas = {}
        for modelo, maximo in maximos.items():
            etiqueta = _etiqueta(modelo)
            pks = set(modelo._base_manager.filter(pk__gt=maximo).values_list('pk', flat=True))
            pks -= {pk for e, pk in rastreo.claves if e == etiqueta}
            if pks:
                nuevas[modelo] = pks
        cambio = True
        while cambio:
            cambio = False
            for modelo, pks in list(nuevas.items()):
                for campo in modelo._meta.concrete_fields:
                    destino = getattr(campo, 'remote_field', None) and campo.remote_field.model
                    if not destino or not pks:
                        continue
                    propios = [pk for e, pk in rastreo.claves if e == _etiqueta(destino)]
                    if not propios:
                        continue
                    suyos = set(modelo._base_manager.filter(pk__in=pks, **{f'{campo.attname}__in': propios})
                                .values_list('pk', flat=True))
                    for pk in sorted(suyos):
                        rastreo.claves.add((_etiqueta(modelo), pk))
                        rastreo.creados.append((_etiqueta(modelo), pk))
                    pks -= suyos
                    cambio = cambio or bool(suyos)
        return {_etiqueta(m): sorted(p) for m, p in nuevas.items() if p}

    def _modificados(self, rastreo, foto_antes, unidad):
        """Lo que cambió en filas que ya existían: lo visto al guardar y lo que difiere en la fotografía."""
        antes = dict(foto_antes)
        for clave, valores in rastreo.antes().items():
            antes.setdefault(clave, valores)
        modificados = []
        for etiqueta, pks in self._por_modelo(antes).items():
            ahora = _valores(apps.get_model(etiqueta), pks)
            for pk in pks:
                previo, actual = antes[(etiqueta, pk)], ahora.get(pk)
                if actual is None:
                    continue
                cambiados = sorted(c for c in actual if previo.get(c) != actual.get(c))
                if cambiados:
                    modificados.append(dict(modelo=etiqueta, pk=pk, antes={c: previo.get(c) for c in cambiados},
                                            despues={c: actual[c] for c in cambiados}))
        return modificados

    def _informe(self, carga, rastreo, modificados, sin_rastrear):
        self.stdout.write('')
        self.stdout.write('PASOS')
        for paso in carga.pasos:
            self.stdout.write(f'  [{paso.resultado}] {paso.nombre}' + (f' — {paso.detalle}' if paso.detalle else ''))
        self.stdout.write('')
        self.stdout.write('DOCUMENTO · TABLA · REGISTRO CARGADO · ESTADO ALCANZADO · APARECE · DÓNDE VERLO')
        for registro in carga.tabla():
            self.stdout.write(f'  {NOMBRES.get(registro.documento, registro.documento)} · {registro.tabla} · '
                              f'{registro.codigo} · {registro.estado} · {registro.aparece or "—"} · '
                              f'{registro.donde or "—"}')
        self.stdout.write('')
        self.stdout.write(f'Filas creadas: {len(rastreo.creados)} en {len(self._por_modelo(rastreo.creados))} tablas · '
                          f'filas que ya existían y cambiaron: {len(modificados)}')
        for modificado in modificados:
            self.stdout.write(f'  cambia {modificado["modelo"]} {modificado["pk"]}: {", ".join(modificado["despues"])}')
        for etiqueta, pks in sin_rastrear.items():
            self.stdout.write(self.style.WARNING(f'  filas nuevas ajenas a la carga (no se retiran): {etiqueta} {pks}'))

    def _guardar_manifiesto(self, opciones, base, unidad, cuentas, inicio, carga, rastreo, modificados, archivos):
        carpeta = Path(opciones['carpeta'] or Path(settings.BASE_DIR) / 'var' / 'registros_de_prueba')
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f'{timezone.localdate():%Y-%m-%d}-{unidad.slug}.json'
        numero = 2
        while ruta.exists():
            ruta = carpeta / f'{timezone.localdate():%Y-%m-%d}-{unidad.slug}-{numero}.json'
            numero += 1
        documentos = [dict(pk=m['pk'], antes=m['antes'], despues=m['despues']) for m in modificados
                      if m['modelo'] == 'documentos.DocumentoExpediente']
        contenido = dict(
            base=base, unidad=unidad.slug, aplicado_en=inicio.isoformat(),
            cuentas={clave: usuario.username for clave, usuario in cuentas.items()},
            creados=[dict(modelo=e, pk=pk) for e, pk in rastreo.creados],
            modificados=modificados, documentos_del_expediente=documentos, archivos=archivos,
            registros=[dict(documento=r.documento, tabla=r.tabla, codigo=r.codigo, estado=r.estado,
                            aparece=r.aparece, donde=r.donde) for r in carga.tabla()])
        ruta.write_text(json.dumps(contenido, cls=DjangoJSONEncoder, ensure_ascii=False, indent=1), encoding='utf-8')
        return ruta

    @staticmethod
    def _borrar_archivo(nombre):
        try:
            if default_storage.exists(nombre):
                default_storage.delete(nombre)
                return True
        except (OSError, ValueError):
            pass
        return False

    # ---- retiro --------------------------------------------------------------------------------------

    def _retirar(self, ruta, aplicar):
        if not ruta.is_file():
            raise CommandError(f'No existe el manifiesto {ruta}.')
        manifiesto = json.loads(ruta.read_text(encoding='utf-8'))
        if manifiesto.get('base') != connection.settings_dict['NAME']:
            raise CommandError(f'El manifiesto es de la base «{manifiesto.get("base")}» y esta conexión usa '
                               f'«{connection.settings_dict["NAME"]}».')
        if manifiesto.get('retirado_en'):
            raise CommandError(f'Esa carga ya se retiró el {manifiesto["retirado_en"]}.')
        propios = {(c['modelo'], c['pk']) for c in manifiesto['creados']}
        archivos, restaurados, intactos, borrados = [], 0, [], 0
        try:
            with transaction.atomic():
                # 1. Lo que ya existía vuelve a su valor anterior, si nadie lo cambió después.
                for cambio in reversed(manifiesto['modificados']):
                    modelo = apps.get_model(cambio['modelo'])
                    actual = _valores(modelo, [cambio['pk']]).get(cambio['pk'])
                    if actual is None:
                        intactos.append(f'{cambio["modelo"]} {cambio["pk"]}: ya no existe')
                        continue
                    if any(actual.get(c) != v for c, v in cambio['despues'].items()):
                        intactos.append(f'{cambio["modelo"]} {cambio["pk"]}: cambió después de la carga; no se toca')
                        continue
                    valores = {c: self._python(modelo, c, v) for c, v in cambio['antes'].items()}
                    modelo._base_manager.filter(pk=cambio['pk']).update(**valores)
                    restaurados += 1
                # 2. Lo creado se borra en orden inverso; nada ajeno puede caer con ello. Lo protegido por otra
                #    fila de la carga espera a que esa se borre primero.
                pendientes = list(reversed(manifiesto['creados']))
                while pendientes:
                    esperan = []
                    for creado in pendientes:
                        modelo = apps.get_model(creado['modelo'])
                        objeto = modelo._base_manager.filter(pk=creado['pk']).first()
                        if objeto is None:
                            continue
                        recolector = Collector(using=connection.alias)
                        try:
                            recolector.collect([objeto])
                        except (ProtectedError, RestrictedError) as error:
                            ajenos = sorted(f'{_etiqueta(type(o))} {o.pk}' for o in error.args[1]
                                            if (_etiqueta(type(o)), o.pk) not in propios)
                            if ajenos:
                                raise CommandError(f'{creado["modelo"]} {creado["pk"]} está protegido por filas que '
                                                   f'no son de la carga: {", ".join(ajenos)[:400]}. '
                                                   'No se retiró nada.') from error
                            esperan.append(creado)
                            continue
                        ajenos = self._ajenos(recolector, propios)
                        if ajenos:
                            raise CommandError(f'Borrar {creado["modelo"]} {creado["pk"]} arrastraría filas que no '
                                               f'son de la carga: {", ".join(ajenos)[:400]}. No se retiró nada.')
                        for instancias in recolector.data.values():
                            for instancia in instancias:
                                archivos.extend(_archivos_de(_etiqueta(type(instancia)), [instancia.pk]))
                        recolector.delete()
                        borrados += 1
                    if len(esperan) == len(pendientes):
                        raise CommandError('Lo creado se protege entre sí sin un orden posible de borrado: '
                                           + ', '.join(f'{c["modelo"]} {c["pk"]}' for c in esperan[:10]))
                    pendientes = esperan
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                    cursor.execute('SET CONSTRAINTS ALL DEFERRED')
                if not aplicar:
                    transaction.set_rollback(True)
        except IntegrityError as error:
            raise CommandError(f'Quedan referencias hacia lo retirado; no se cambió nada. {str(error)[:400]}') from error
        self.stdout.write(f'Restaurados a su valor anterior: {restaurados} · borrados: {borrados} de '
                          f'{len(manifiesto["creados"])} creados')
        for aviso in intactos:
            self.stdout.write(self.style.WARNING(f'  {aviso}'))
        if not aplicar:
            self.stdout.write(self.style.WARNING('Ensayo del retiro terminado: no se cambió nada.'))
            return
        en_uso = self._archivos_en_uso(set(archivos) | set(manifiesto.get('archivos', [])))
        retirados = sum(1 for nombre in sorted(set(archivos) | set(manifiesto.get('archivos', [])))
                        if nombre not in en_uso and self._borrar_archivo(nombre))
        manifiesto['retirado_en'] = timezone.now().isoformat()
        manifiesto['retiro'] = dict(restaurados=restaurados, borrados=borrados, sin_tocar=intactos,
                                    archivos_retirados=retirados)
        ruta.write_text(json.dumps(manifiesto, cls=DjangoJSONEncoder, ensure_ascii=False, indent=1), encoding='utf-8')
        self.stdout.write(f'Archivos retirados de MEDIA_ROOT: {retirados}')
        self.stdout.write(self.style.SUCCESS('Carga de prueba retirada.'))

    @staticmethod
    def _python(modelo, attname, valor):
        campo = next(c for c in modelo._meta.concrete_fields if c.attname == attname)
        if valor is None:
            return None
        if isinstance(campo, models.ForeignKey):
            return campo.target_field.to_python(valor)
        if isinstance(campo, models.DateTimeField) and isinstance(valor, str):
            return datetime.fromisoformat(valor.replace('Z', '+00:00'))
        return campo.to_python(valor)

    @staticmethod
    def _ajenos(recolector, propios):
        ajenos = []
        for modelo, instancias in recolector.data.items():
            if modelo._meta.auto_created:
                continue
            ajenos.extend(f'{_etiqueta(modelo)} {i.pk}' for i in instancias if (_etiqueta(modelo), i.pk) not in propios)
        for consulta in recolector.fast_deletes:
            modelo = consulta.model
            if modelo._meta.auto_created:
                continue
            ajenos.extend(f'{_etiqueta(modelo)} {pk}' for pk in consulta.values_list('pk', flat=True)
                          if (_etiqueta(modelo), pk) not in propios)
        for (campo, _valor), grupos in recolector.field_updates.items():
            for grupo in grupos:
                ajenos.extend(f'{_etiqueta(campo.model)} {i.pk} (pierde {campo.name})' for i in grupo
                              if (_etiqueta(campo.model), i.pk) not in propios)
        return ajenos

    @staticmethod
    def _archivos_en_uso(nombres):
        """Un archivo que todavía nombra otra fila no se borra."""
        en_uso = set()
        if not nombres:
            return en_uso
        for modelo in apps.get_models():
            for campo in modelo._meta.concrete_fields:
                if isinstance(campo, models.FileField):
                    en_uso.update(modelo._base_manager.filter(**{f'{campo.attname}__in': list(nombres)})
                                  .values_list(campo.attname, flat=True))
        return en_uso
