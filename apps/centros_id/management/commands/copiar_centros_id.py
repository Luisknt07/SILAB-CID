"""Copia verificable y no destructiva entre las bases de Centros y plataforma."""
import hashlib
import tempfile

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, transaction
from django.db.migrations.executor import MigrationExecutor


def tablas_centros():
    """Incluye tablas puente automáticas, sin auth, sesiones ni migraciones."""
    modelos = apps.get_app_config('centros_id').get_models(include_auto_created=True)
    return {m._meta.db_table: m for m in modelos if m._meta.managed and not m._meta.proxy}


def estructura(conexion, tablas):
    with conexion.cursor() as cursor:
        existentes = set(conexion.introspection.table_names(cursor))
        faltantes = set(tablas) - existentes
        if faltantes:
            raise CommandError('Faltan tablas de Centros; ejecute sus migraciones antes de copiar.')
        salida = {}
        for tabla in sorted(tablas):
            cursor.execute(
                'SELECT column_name, udt_schema, udt_name, is_nullable, '
                'character_maximum_length, numeric_precision, numeric_scale, datetime_precision '
                'FROM information_schema.columns WHERE table_schema = current_schema() '
                'AND table_name = %s ORDER BY column_name', [tabla],
            )
            columnas = cursor.fetchall()
            # Las instalaciones anteriores y la baseline pueden tener nombres
            # y posiciones físicas distintos. La equivalencia exige las mismas
            # columnas y restricciones lógicas, incluidas sus FK y CHECK.
            cursor.execute(
                'SELECT c.contype, pg_get_constraintdef(c.oid), c.convalidated, '
                'c.condeferrable, c.condeferred FROM pg_constraint c '
                'JOIN pg_class t ON t.oid = c.conrelid '
                'JOIN pg_namespace n ON n.oid = t.relnamespace '
                'WHERE n.nspname = current_schema() AND t.relname = %s '
                'ORDER BY c.contype, pg_get_constraintdef(c.oid), c.convalidated, '
                'c.condeferrable, c.condeferred', [tabla],
            )
            salida[tabla] = {'columnas': columnas, 'restricciones': cursor.fetchall()}
    return salida


def resumen(conexion, tabla, columnas, primaria):
    """Digest ordenado, en lotes; no expone registros ni carga tablas en memoria."""
    q = conexion.ops.quote_name
    campos = ', '.join(q(c[0]) for c in columnas)
    sql = f'SELECT row_to_json(fila)::text FROM (SELECT {campos} FROM {q(tabla)} ORDER BY {q(primaria)}) fila'
    digest = hashlib.sha256()
    cantidad = 0
    # Cursor de servidor: también las tablas grandes se leen por bloques.
    with conexion.connection.cursor(name='centros_digest') as cursor:
        cursor.itersize = 1000
        cursor.execute(sql)
        for fila in cursor:
            dato = fila[0].encode('utf-8')
            digest.update(len(dato).to_bytes(8, 'big'))
            digest.update(dato)
            cantidad += 1
    return {'filas': cantidad, 'sha256': digest.hexdigest()}


FUNCION_SELLO = 'centros_id_impedir_escritura_legacy'
TRIGGER_SELLO = 'centros_id_origen_solo_lectura'


def sellar_origen(conexion, tablas):
    """Bloquea escrituras antiguas sin borrar tablas, filas ni archivos."""
    q = conexion.ops.quote_name
    with conexion.cursor() as cursor:
        cursor.execute('SELECT current_schema()')
        esquema = cursor.fetchone()[0]
        funcion = f'{q(esquema)}.{q(FUNCION_SELLO)}'
        cursor.execute(
            f'CREATE OR REPLACE FUNCTION {funcion}() RETURNS trigger LANGUAGE plpgsql AS $sello$ '
            "BEGIN RAISE EXCEPTION USING ERRCODE='55000', "
            "MESSAGE='Centros I+D se administra en su base independiente; origen conservado en solo lectura.'; "
            'RETURN NULL; END; $sello$'
        )
        for tabla in sorted(tablas):
            nombre = f'{q(esquema)}.{q(tabla)}'
            cursor.execute(
                f'CREATE OR REPLACE TRIGGER {q(TRIGGER_SELLO)} BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE '
                f'ON {nombre} FOR EACH STATEMENT EXECUTE FUNCTION {funcion}()'
            )
            # El sello también rige para sesiones en modo replica. El rol de
            # aplicación no debe ser dueño de tablas ni poder desactivar triggers.
            cursor.execute(f'ALTER TABLE {nombre} ENABLE ALWAYS TRIGGER {q(TRIGGER_SELLO)}')


class Command(BaseCommand):
    help = ('Comprueba o copia todas las tablas de Centros a otra base PostgreSQL vacía; '
            'conserva el origen y verifica IDs, relaciones y contenido antes del commit.')

    def add_arguments(self, parser):
        parser.add_argument('--origen', default='default')
        parser.add_argument('--destino', default='centros')
        parser.add_argument('--copiar', action='store_true', help='Copia en transacción; sin esta opción solo compara.')
        parser.add_argument('--sellar-origen', action='store_true',
                            help='Después de copiar y verificar, bloquea INSERT/UPDATE/DELETE/TRUNCATE en el origen.')
        parser.add_argument('--espera-bloqueo', type=int, default=5000, help='Espera máxima de locks en milisegundos (1–60000).')

    def handle(self, *args, **opciones):
        origen, destino = opciones['origen'], opciones['destino']
        if origen == destino or origen not in connections or destino not in connections:
            raise CommandError('Seleccione dos alias configurados y diferentes.')
        a, b = connections[origen], connections[destino]
        if a.vendor != 'postgresql' or b.vendor != 'postgresql':
            raise CommandError('Esta transferencia verificada requiere PostgreSQL en ambas bases.')
        # Nombres distintos incluso si se usan hosts o roles alternativos para
        # el mismo servidor. Nunca arriesgar una copia sobre su propio origen.
        if a.settings_dict['NAME'] == b.settings_dict['NAME']:
            raise CommandError('Origen y destino deben tener nombres de base diferentes.')
        espera = opciones['espera_bloqueo']
        if not 1 <= espera <= 60000:
            raise CommandError('La espera de bloqueo debe estar entre 1 y 60000 ms.')
        if opciones['sellar_origen'] and not opciones['copiar']:
            raise CommandError('--sellar-origen requiere --copiar y una transferencia verificada.')
        tablas = tablas_centros()
        destino_confirmado = False
        destino_por_confirmar = False
        try:
            with transaction.atomic(using=origen):
                with transaction.atomic(using=destino):
                    for conexion in (a, b):
                        with conexion.cursor() as cursor:
                            # En copia, los locks protegen el estado actual: fijar un
                            # snapshot antes de adquirirlos podría omitir una escritura
                            # confirmada mientras se esperaba el bloqueo.
                            aislamiento = 'READ COMMITTED' if opciones['copiar'] else 'REPEATABLE READ'
                            cursor.execute(f'SET TRANSACTION ISOLATION LEVEL {aislamiento}')
                            cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                            cursor.execute("SELECT set_config('lock_timeout', %s, true)", [f'{espera}ms'])
                    for alias in (origen, destino):
                        ejecutor = MigrationExecutor(connections[alias])
                        pendientes = ejecutor.migration_plan(ejecutor.loader.graph.leaf_nodes('centros_id'))
                        if pendientes:
                            raise CommandError('Hay migraciones de Centros pendientes; no se puede copiar un esquema incompleto.')
                    if opciones['copiar']:
                        # El origen conserva su información. SHARE detiene sus
                        # escritores hasta confirmar la transferencia; no basta
                        # una fotografía que pudiera quedar obsoleta durante COPY.
                        for conexion, modo in ((a, 'SHARE'), (b, 'ACCESS EXCLUSIVE')):
                            nombres = ', '.join(conexion.ops.quote_name(t) for t in sorted(tablas))
                            with conexion.cursor() as cursor:
                                cursor.execute(f'LOCK TABLE {nombres} IN {modo} MODE')
                    sa, sb = estructura(a, tablas), estructura(b, tablas)
                    if sa != sb:
                        raise CommandError('Los esquemas de las dos bases no coinciden; la copia no se inició.')
                    if opciones['copiar']:
                        with b.cursor() as cursor:
                            for tabla in sorted(tablas):
                                cursor.execute(f'SELECT EXISTS(SELECT 1 FROM {b.ops.quote_name(tabla)} LIMIT 1)')
                                if cursor.fetchone()[0]:
                                    raise CommandError('El destino contiene registros; no se sobrescribirá ni mezclará información.')
                            cursor.execute('SET CONSTRAINTS ALL DEFERRED')
                        for tabla in sorted(tablas):
                            campos = ', '.join(a.ops.quote_name(c[0]) for c in sa[tabla]['columnas'])
                            nombre = a.ops.quote_name(tabla)
                            # Derrama a disco a partir de 8 MiB; el consumo de RAM
                            # permanece acotado y el temporal se elimina al cerrar.
                            with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as archivo:
                                with a.cursor() as cursor:
                                    cursor.copy_expert(f'COPY {nombre} ({campos}) TO STDOUT WITH (FORMAT BINARY)', archivo)
                                archivo.seek(0)
                                with b.cursor() as cursor:
                                    cursor.copy_expert(f'COPY {nombre} ({campos}) FROM STDIN WITH (FORMAT BINARY)', archivo)
                    total = 0
                    for tabla, modelo in sorted(tablas.items()):
                        ra = resumen(a, tabla, sa[tabla]['columnas'], modelo._meta.pk.column)
                        rb = resumen(b, tabla, sb[tabla]['columnas'], modelo._meta.pk.column)
                        if ra != rb:
                            raise CommandError(f'El contenido de {tabla} difiere; la transferencia se revierte.')
                        total += ra['filas']
                    if opciones['copiar']:
                        with b.cursor() as cursor:
                            # Obliga a comprobar las FK antes del commit y reajusta
                            # secuencias para que las siguientes altas no colisionen.
                            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                            for sql in b.ops.sequence_reset_sql(no_style(), list(tablas.values())):
                                cursor.execute(sql)
                        if opciones['sellar_origen']:
                            sellar_origen(a, tablas)
                    destino_por_confirmar = opciones['copiar']
                destino_confirmado = opciones['copiar']
        except CommandError:
            raise
        except Exception as error:
            # No existe commit atómico distribuido. El destino se confirma
            # manteniendo el lock del origen; un fallo posterior no puede
            # deshacer aquella confirmación y exige comprobar ambas bases.
            if destino_confirmado:
                raise CommandError(
                    'El destino ya confirmó la copia, pero no se pudo confirmar el cierre del origen '
                    f'({type(error).__name__}). No active el corte: compare ambas bases y verifique '
                    'el sello de origen antes de continuar.'
                ) from None
            if destino_por_confirmar:
                raise CommandError(
                    'No se pudo verificar la confirmación del destino '
                    f'({type(error).__name__}). El resultado puede ser parcial: compare ambas bases '
                    'y verifique el sello de origen antes de repetir la copia o activar el corte.'
                ) from None
            # Drivers pueden incluir DSN, fragmentos de filas o nombres de
            # personas. El operador recibe categoría y rollback, sin secretos.
            raise CommandError(f'La operación se revirtió ({type(error).__name__}). Revise conexión, permisos y bloqueos.') from None
        accion = 'Copia confirmada' if opciones['copiar'] else 'Comparación correcta'
        sello = ' Origen sellado contra escrituras antiguas.' if opciones['sellar_origen'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{accion}: {len(tablas)} tablas, {total} registros; digest íntegro. Origen conservado. '
            'Los archivos mantienen sus rutas; respalde también MEDIA y almacenamiento privado.' + sello
        ))
