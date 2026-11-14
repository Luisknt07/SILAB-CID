"""Perfil local del ensayo integral en la interfaz habitual de FabLab.

Usa exclusivamente las copias de ensayo. No cambia el entorno, el reloj ni
la configuración de desarrollo o producción de otros procesos.
"""
from copy import deepcopy

from .ensayo_fablab import bases_de_ensayo_fablab
from .settings import *  # noqa: F403


DATABASES = bases_de_ensayo_fablab(DATABASES, DEBUG)  # noqa: F405
CENTROS_DB_ENABLED = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
ESCENARIO_IDEAL_AISLADO = True
ENSAYO_FABLAB_ACTIVO = True
REVISION_TIPOLOGIAS_ACTIVA = True
REVISION_TIPOLOGIAS_CASOS = (
    ('fablab-prueba-reportes-2026b', 'FabLab (prueba)'),
    ('qa-hipotesis-plantas-piloto-revision2026b', 'Planta piloto'),
    ('qa-hipotesis-centro-experimental-revision2026b', 'Centro experimental'),
    ('qa-hipotesis-observatorios-revision2026b', 'Observatorio'),
)
# Los enlaces del administrador admiten el identificador, además del slug.
# Este mapa pertenece exclusivamente a la copia local de los cuatro casos.
REVISION_TIPOLOGIAS_IDENTIFICADORES = {
    '49': 'fablab-prueba-reportes-2026b',
    '50': 'qa-hipotesis-plantas-piloto-revision2026b',
    '51': 'qa-hipotesis-centro-experimental-revision2026b',
    '52': 'qa-hipotesis-observatorios-revision2026b',
}
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
MEDICION_METAS_HABILITADA = True
MEDICION_SOLO_DEMO = False
MEDIA_ROOT = BASE_DIR / 'var/ensayo-operativo-fablab-20261017/media'  # noqa: F405

# Copiar antes de ampliar evita modificar la lista del módulo común en los
# procesos que importen ambos perfiles durante una comprobación.
TEMPLATES = deepcopy(TEMPLATES)  # noqa: F405
TEMPLATES[0]['OPTIONS']['context_processors'].append(
    'apps.core.presentation.ensayo_fablab.contexto_ensayo_fablab')
