"""Fichas explicativas de las áreas de todas las unidades, por grupo de unidades.

Cada módulo define `FICHAS = {slug de la unidad: {código del área: ficha}}` con el esquema que
lee `cargar_fichas_area`. Los laboratorios salen de la investigación de equipamiento de octubre
de 2026; las plantas piloto y el centro experimental, de los datos que la plataforma ya tiene de
ellos y de referencias técnicas generales. Ninguna se publica sin que la unidad la revise.
"""
from importlib import import_module

GRUPOS = ('fablab', 'robotica_xr', 'ia_ciber_multimedia', 'alimentos', 'micro_vet', 'salud_educacion', 'gestion',
          'plantas_a', 'plantas_b')

FUENTE = ('Referencia preparada por la plataforma (octubre de 2026) a partir de la investigación de equipamiento '
          'y de los datos de la unidad; la unidad la valida antes de publicarla.')
# Las fuentes que dejan los cargadores: solo esas fichas se pueden rehacer mientras sigan sin publicar.
FUENTES_DE_CARGADOR = (FUENTE, 'Investigación de equipamiento por laboratorio, octubre de 2026')

FICHAS = {}
for _grupo in GRUPOS:
    FICHAS.update(import_module(f'{__name__}.{_grupo}').FICHAS)
