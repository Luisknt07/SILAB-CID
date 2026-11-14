"""Límite físico de Centros I+D; identidad y permisos canónicos son centrales."""
from django.conf import settings


class RouterCentros:
    @staticmethod
    def _alias(app_label):
        return 'centros' if app_label == 'centros_id' and settings.CENTROS_DB_ENABLED else 'default'

    def db_for_read(self, model, **hints):
        return self._alias(model._meta.app_label)

    def db_for_write(self, model, **hints):
        return self._alias(model._meta.app_label)

    def allow_relation(self, obj1, obj2, **hints):
        # También bloquear objetos cargados explícitamente desde la copia
        # anterior: el flag no convierte relaciones entre bases en relaciones SQL.
        alias1 = obj1._state.db or self._alias(obj1._meta.app_label)
        alias2 = obj2._state.db or self._alias(obj2._meta.app_label)
        return alias1 == alias2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'centros':
            return app_label == 'centros_id'
        if db == 'default':
            return app_label != 'centros_id' or not settings.CENTROS_DB_ENABLED
        return False
