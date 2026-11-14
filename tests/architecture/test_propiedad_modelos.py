"""La extracción conserva tablas, relaciones y estado previo sin SQL destructivo."""
from unittest.mock import MagicMock, patch

from django.db import models
from django.db.migrations.state import ModelState, ProjectState
from django.test import SimpleTestCase

from apps.core.migraciones_propiedad import TransferirPropiedadModelos


class PropiedadModelosTests(SimpleTestCase):
    def estado(self):
        return ProjectState({
            ('webcitt', 'item'): ModelState('webcitt', 'Item', [
                ('id', models.AutoField(primary_key=True)),
                ('tags', models.ManyToManyField('webcitt.Tag')),
            ]),
            ('webcitt', 'tag'): ModelState('webcitt', 'Tag', [
                ('id', models.AutoField(primary_key=True)),
                ('item', models.ForeignKey('webcitt.Item', on_delete=models.PROTECT)),
            ]),
            ('laboratorios', 'item'): ModelState('laboratorios', 'Item', [],
                options={'proxy': True}, bases=('webcitt.item',)),
        })

    def operacion(self):
        return TransferirPropiedadModelos({'item': 'recursos', 'tag': 'formacion'},
            {'item': {'tags': 'webcitt_item_tags'}})

    def test_transfiere_estado_relaciones_m2m_y_bases_proxy_sin_mutar_el_original(self):
        original = self.estado()
        target = original.clone()
        self.operacion().state_forwards('webcitt', target)
        self.assertEqual(set(target.models), {('recursos', 'item'), ('formacion', 'tag'), ('laboratorios', 'item')})
        self.assertEqual(target.models['recursos', 'item'].options['db_table'], 'webcitt_item')
        self.assertEqual(target.models['formacion', 'tag'].fields['item'].remote_field.model.lower(), 'recursos.item')
        self.assertEqual(target.models['recursos', 'item'].fields['tags'].remote_field.model.lower(), 'formacion.tag')
        self.assertEqual(target.models['recursos', 'item'].fields['tags'].db_table, 'webcitt_item_tags')
        self.assertEqual(target.models['laboratorios', 'item'].bases, ('recursos.item',))
        self.assertEqual(original.models['webcitt', 'item'].fields['tags'].remote_field.model, 'webcitt.Tag')
        self.assertEqual(original.models['laboratorios', 'item'].bases, ('webcitt.item',))
        # Renderizar exige que todos los destinos y relaciones sean coherentes.
        item = target.apps.get_model('recursos', 'Item')
        self.assertEqual(item._meta.get_field('tags').remote_field.through._meta.db_table, 'webcitt_item_tags')

    def test_origen_incompleto_o_destino_duplicado_no_cambia_el_estado(self):
        state = self.estado()
        keys = set(state.models)
        operation = TransferirPropiedadModelos({'ausente': 'recursos'}, {})
        with self.assertRaises(ValueError):
            operation.state_forwards('webcitt', state)
        self.assertEqual(set(state.models), keys)
        state.models['recursos', 'item'] = ModelState('recursos', 'Item', [])
        keys = set(state.models)
        with self.assertRaises(ValueError):
            self.operacion().state_forwards('webcitt', state)
        self.assertEqual(set(state.models), keys)

    def schema(self, rows):
        editor = MagicMock()
        editor.connection.alias = 'default'
        cursor = editor.connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = rows
        return editor, cursor

    def test_permisos_conservan_ids_y_no_hay_sql_de_creacion_ni_borrado(self):
        editor, cursor = self.schema([(4,), None, (8,), None])
        with patch('apps.core.migraciones_propiedad.router.allow_migrate', return_value=True):
            self.operacion().database_forwards('webcitt', editor, None, None)
        updates = [c.args for c in cursor.execute.call_args_list if c.args[0].startswith('UPDATE')]
        self.assertEqual(updates, [
            ('UPDATE django_content_type SET app_label=%s WHERE id=%s', ['recursos', 4]),
            ('UPDATE django_content_type SET app_label=%s WHERE id=%s', ['formacion', 8]),
        ])
        self.assertFalse(any(c.args[0].startswith(('CREATE', 'DROP', 'DELETE', 'ALTER')) for c in cursor.execute.call_args_list))

    def test_colision_de_tipo_contenido_se_detecta_antes_de_cambiar_cualquier_id(self):
        editor, cursor = self.schema([(4,), None, (8,), (12,)])
        with patch('apps.core.migraciones_propiedad.router.allow_migrate', return_value=True), self.assertRaises(ValueError):
            self.operacion().database_forwards('webcitt', editor, None, None)
        self.assertFalse(any(c.args[0].startswith('UPDATE') for c in cursor.execute.call_args_list))

    def test_instalacion_nueva_y_alias_centros_no_requieren_tipos_anteriores(self):
        editor, cursor = self.schema([None, None])
        with patch('apps.core.migraciones_propiedad.router.allow_migrate', return_value=True):
            self.operacion().database_forwards('webcitt', editor, None, None)
        self.assertFalse(any(c.args[0].startswith('UPDATE') for c in cursor.execute.call_args_list))
        editor, cursor = self.schema([])
        with patch('apps.core.migraciones_propiedad.router.allow_migrate', return_value=False):
            self.operacion().database_forwards('webcitt', editor, None, None)
        cursor.execute.assert_not_called()
