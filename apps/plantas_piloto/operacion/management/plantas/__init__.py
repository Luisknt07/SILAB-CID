"""Las definiciones de carga de las plantas piloto, una por archivo.

El cargador institucional las lee igual que a los laboratorios. Viven aparte
porque cada planta trae sus propios procesos, con sus etapas, sus puntos
críticos y sus planes de calidad, y el comando ya es bastante largo con la de
lácteos dentro.
"""

from apps.plantas_piloto.operacion.management.plantas.almidones import ALMIDONES
from apps.plantas_piloto.operacion.management.plantas.carnicos import CARNICOS
from apps.plantas_piloto.operacion.management.plantas.hortofruticola import HORTOFRUTICOLA
from apps.plantas_piloto.operacion.management.plantas.panificacion import PANIFICACION

PLANTAS = {
    'carnicos': CARNICOS,
    'panificacion': PANIFICACION,
    'hortofruticola': HORTOFRUTICOLA,
    'almidones': ALMIDONES,
}

__all__ = ['ALMIDONES', 'CARNICOS', 'HORTOFRUTICOLA', 'PANIFICACION', 'PLANTAS']
