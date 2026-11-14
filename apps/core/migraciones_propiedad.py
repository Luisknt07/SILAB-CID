"""Traslado de propiedad Django conservando tablas, filas e identidad de permisos.

Operación histórica estable: no importar modelos de ejecución ni servicios.
"""
from copy import deepcopy

from django.db import router
from django.db.migrations.operations.base import Operation


class TransferirPropiedadModelos(Operation):
    """Mueve el estado completo a sus apps y conserva los ContentType existentes."""

    reduces_to_sql = False
    reversible = True
    atomic = True

    def __init__(self, propietarios, tablas_m2m, origen='webcitt', tablas=None):
        self.propietarios = dict(propietarios)
        self.tablas_m2m = dict(tablas_m2m)
        self.origen = origen
        self.tablas = dict(tablas or {})

    def deconstruct(self):
        return (self.__class__.__name__, [], {
            'propietarios': self.propietarios,
            'tablas_m2m': self.tablas_m2m,
            'origen': self.origen,
            'tablas': self.tablas,
        })

    def describe(self):
        return 'Transferir modelos a sus aplicaciones conservando tablas y permisos'

    def _referencia(self, value):
        if not isinstance(value, str) or '.' not in value:
            return value
        app_label, name = value.split('.', 1)
        owner = self.propietarios.get(name.lower()) if app_label == self.origen else None
        return f'{owner}.{name}' if owner else value

    def state_forwards(self, app_label, state):
        # Modificar un clon completo evita estados intermedios con relaciones o
        # bases proxy sin resolver. No se renderizan modelos hasta acabar.
        moved = {}
        for key, model in state.models.items():
            clone = model.clone()
            clone.fields = {name: field.clone() for name, field in model.fields.items()}
            owner = self.propietarios.get(key[1]) if key[0] == self.origen else None
            if owner:
                clone.app_label = owner
                clone.options = deepcopy(clone.options)
                clone.options.setdefault('db_table', self.tablas.get(key[1], f'{self.origen}_{key[1]}'))
            clone.bases = tuple(self._referencia(base) for base in clone.bases)
            for field_name, field in clone.fields.items():
                remote = getattr(field, 'remote_field', None)
                if remote:
                    remote.model = self._referencia(remote.model)
                    if getattr(remote, 'through', None):
                        remote.through = self._referencia(remote.through)
                if owner and field.many_to_many and not remote.through:
                    field.db_table = self.tablas_m2m.get(key[1], {}).get(field_name)
            target = (owner or key[0], key[1])
            if target in moved:
                raise ValueError('Destino de modelo duplicado durante la transferencia')
            moved[target] = clone
        expected = {(self.origen, name) for name in self.propietarios}
        if not expected.issubset(state.models):
            raise ValueError('Faltan modelos de origen para transferir el estado completo')
        state.models = moved
        state._relations = None
        state.__dict__.pop('apps', None)

    def _transferir_permisos(self, schema_editor, invertir=False):
        alias = schema_editor.connection.alias
        if not router.allow_migrate(alias, self.origen):
            return
        with schema_editor.connection.cursor() as cursor:
            # Validar todos los destinos antes de cambiar una sola identidad.
            changes = []
            for name, owner in self.propietarios.items():
                source, target = (owner, self.origen) if invertir else (self.origen, owner)
                cursor.execute('SELECT id FROM django_content_type WHERE app_label=%s AND model=%s', [source, name])
                row = cursor.fetchone()
                if row is None:
                    continue  # Instalación nueva: post_migrate crea su registro final.
                cursor.execute('SELECT id FROM django_content_type WHERE app_label=%s AND model=%s', [target, name])
                if cursor.fetchone():
                    raise ValueError('Existe un tipo de contenido de destino; reconciliar antes de migrar')
                changes.append((target, row[0]))
            for target, pk in changes:
                cursor.execute('UPDATE django_content_type SET app_label=%s WHERE id=%s', [target, pk])
        # IDs de permisos, grupos, Guardian, referencias genéricas e historial
        # administrativo permanecen iguales; solo cambia el prefijo de su dueño.

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._transferir_permisos(schema_editor)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._transferir_permisos(schema_editor, invertir=True)


class TransferirCapacidadReservas(Operation):
    """Conserva suspensión, versiones y cambios de la capacidad de reservas."""

    reduces_to_sql = False
    reversible = True
    atomic = True

    def state_forwards(self, app_label, state):
        pass

    def describe(self):
        return 'Asignar la capacidad de reservas a su aplicación manteniendo historial'

    def _cambiar(self, schema_editor, origen, destino):
        if not router.allow_migrate(schema_editor.connection.alias, 'configuracion_institucional'):
            return
        with schema_editor.connection.cursor() as cursor:
            cursor.execute('''SELECT a.id FROM configuracion_institucional_estadocapacidad a
                JOIN configuracion_institucional_estadocapacidad b
                ON a.producto_codigo=b.producto_codigo AND a.institucion_codigo=b.institucion_codigo
                AND a.capacidad=b.capacidad WHERE a.modulo=%s AND b.modulo=%s''', [origen, destino])
            if cursor.fetchone():
                raise ValueError('Hay dos estados de reservas; reconciliar antes de migrar')
            cursor.execute('''UPDATE configuracion_institucional_estadocapacidad SET modulo=%s
                WHERE modulo=%s AND capacidad=%s''', [destino, origen, 'reservas_operativas'])

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._cambiar(schema_editor, 'legado_webcitt', 'reservas')

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._cambiar(schema_editor, 'reservas', 'legado_webcitt')
