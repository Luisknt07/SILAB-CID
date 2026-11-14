"""Componentes, modos de uso y sistema de referencia de cada familia de producto, por grupo.

Cada entrada: 'componentes' como (tipo, cantidad, nombre, uso) con tipo incluido, complementario o repuesto;
'modos' con nombre, icono, descripcion, aplicaciones y requisitos (la computadora recomendada va en los
requisitos del modo que la usa); y 'sistema', el firmware o software con el que funciona. Los carga
cargar_componentes_familias.
"""
from apps.gestion_unidades.management.fichas_area.componentes_familias.alimentos import COMPONENTES as _ALIMENTOS
from apps.gestion_unidades.management.fichas_area.componentes_familias.analitico import COMPONENTES as _ANALITICO
from apps.gestion_unidades.management.fichas_area.componentes_familias.fabricacion import COMPONENTES as _FABRICACION
from apps.gestion_unidades.management.fichas_area.componentes_familias.medios_xr_computo import COMPONENTES as _MEDIOS_XR_COMPUTO
from apps.gestion_unidades.management.fichas_area.componentes_familias.robotica_agro_redes import COMPONENTES as _ROBOTICA_AGRO_REDES
from apps.gestion_unidades.management.fichas_area.componentes_familias.salud_micro import COMPONENTES as _SALUD_MICRO

COMPONENTES = {**_ALIMENTOS, **_ANALITICO, **_FABRICACION, **_MEDIOS_XR_COMPUTO, **_SALUD_MICRO, **_ROBOTICA_AGRO_REDES}
