"""Imágenes y videos de las áreas: lo que la página muestra mientras la unidad no sube los suyos.

Las imágenes son las ilustraciones temáticas que el portal ya usa; la página las rotula como
referenciales. Los videos son de YouTube, de canales confiables, y cada uno se verificó con el
servicio oEmbed de YouTube (existe y permite insertarse) antes de agregarlo.
"""
from importlib import import_module

# Cada tema con sus imágenes: (ruta en los estáticos, pie de foto).
IMAGENES = {
    'fabricacion': [
        ('img/generated/home-hero/hero-fabricacion-avanzada.png', 'Fabricación digital y prototipado'),
        ('img/pilares/Estructura_fablab.jpg', 'Espacio de trabajo de un laboratorio de fabricación'),
        ('img/generated/multimedia-fabricacion-v2.png', 'Prototipos y piezas fabricadas'),
        ('img/generated/industria40-fabricacion-vr.png', 'Diseño y fabricación asistidos por computador'),
        ('img/generated/connected-units/centro-industria-digital.png', 'Industria digital'),
    ],
    'robotica': [
        ('img/generated/connected-units/laboratorio-robotica.png', 'Laboratorio de robótica'),
        ('img/generated/industria40-robotica.png', 'Robótica industrial y colaborativa'),
        ('img/generated/multimedia-robotica-v2.png', 'Programación y control de robots'),
        ('img/pilares/robotica.jpeg', 'Robótica educativa'),
        ('img/generated/connected-units/centro-drones-vision.png', 'Drones y visión artificial'),
    ],
    'xr': [
        ('img/generated/home-hero/hero-realidad-extendida.png', 'Realidad extendida'),
        ('img/generated/connected-units/laboratorio-realidad-extendida.png', 'Experiencias con visores'),
        ('img/generated/multimedia-inmersiva-v2.png', 'Contenidos inmersivos'),
        ('img/generated/platforms/xr-digital-twin.png', 'Gemelo digital'),
        ('img/pilares/labrealidad.jpg', 'Laboratorio de realidad virtual'),
    ],
    'datos': [
        ('img/generated/industria40-ia-analitica-v2.png', 'Inteligencia artificial y analítica'),
        ('img/generated/platforms/software-analytics.png', 'Tableros de análisis de datos'),
        ('img/generated/home-hero/hero-laboratorio-conectado.png', 'Laboratorio conectado'),
        ('img/generated/observatorios/tableros-indicadores.webp', 'Tableros de indicadores'),
        ('img/generated/observatorios/bases-datos.webp', 'Bases de datos abiertas'),
    ],
    'redes': [
        ('img/generated/home-hero/hero-laboratorio-conectado.png', 'Redes y laboratorio conectado'),
        ('img/generated/centros-id-tecnologia.png', 'Infraestructura tecnológica'),
        ('img/generated/connected-platforms-v2/centro-innovacion-tecnologia.png', 'Centro de tecnología'),
        ('img/generated/platforms/software-analytics.png', 'Monitoreo y análisis'),
    ],
    'multimedia': [
        ('img/pilares/medialab.jpg', 'Laboratorio de medios'),
        ('img/generated/multimedia-inmersiva-v2.png', 'Producción multimedia'),
        ('img/generated/hero-noticias-v2.png', 'Comunicación y contenidos'),
        ('img/generated/multimedia-alimentos-v2.png', 'Producción audiovisual de procesos'),
    ],
    'alimentos': [
        ('img/generated/connected-units/laboratorio-alimentos.png', 'Laboratorio de alimentos'),
        ('img/generated/home-hero/hero-alimentos-biotecnologia.png', 'Análisis de alimentos'),
        ('img/generated/connected-platforms-v2/centro-investigacion-alimentos.png', 'Investigación en alimentos'),
        ('img/generated/multimedia-alimentos-v2.png', 'Procesos de alimentos'),
        ('img/generated/home-hero/hero-laboratorio-ambiental.png', 'Análisis de suelos y aguas'),
    ],
    'biotecnologia': [
        ('img/generated/connected-units/centro-biotecnologia.png', 'Biotecnología'),
        ('img/generated/home-hero/hero-microscopia-docencia.png', 'Microscopía y docencia'),
        ('img/generated/industria40-biotecnologia-v2.png', 'Biotecnología aplicada'),
        ('img/generated/home-hero/hero-biotecnologia-vegetal.png', 'Biotecnología vegetal'),
    ],
    'clinico': [
        ('img/generated/home-hero/hero-analisis-clinico.png', 'Análisis clínico'),
        ('img/generated/home-hero/hero-microscopia-docencia.png', 'Microscopía'),
        ('img/generated/connected-units/centro-biotecnologia.png', 'Laboratorio biomédico'),
    ],
    'simulacion': [
        ('img/generated/home-hero/hero-analisis-clinico.png', 'Formación en salud'),
        ('img/generated/connected-platforms-v2/laboratorios-docencia.png', 'Laboratorios de docencia'),
        ('img/generated/multimedia-inmersiva-v2.png', 'Simulación inmersiva'),
    ],
    'educacion': [
        ('img/generated/laboratorios-docencia.png', 'Laboratorios de docencia'),
        ('img/generated/connected-platforms-v2/laboratorios-docencia.png', 'Aprendizaje activo'),
        ('img/pilares/bloomberg_lab.webp', 'Espacio de innovación educativa'),
        ('img/pilares/robotica.jpeg', 'Robótica educativa'),
    ],
    'logistica': [
        ('img/generated/home-hero/hero-simulacion-logistica.png', 'Simulación logística'),
        ('img/generated/industria40-logistica-v2.png', 'Logística inteligente'),
        ('img/cards/portuaria.png', 'Comercio exterior y puertos'),
        ('img/cards/flexsim.png', 'Simulación de procesos logísticos'),
    ],
    'emprendimiento': [
        ('img/cards/coworking.png', 'Espacio de trabajo colaborativo'),
        ('img/cards/networking.png', 'Encuentros y redes de emprendedores'),
        ('img/generated/home-hero/hero-innovacion-interdisciplinaria.png', 'Innovación interdisciplinaria'),
        ('img/generated/connected-platforms-v2/centros-interdisciplinarios.png', 'Trabajo interdisciplinario'),
    ],
    'gobierno': [
        ('img/generated/observatorios/tableros-indicadores.webp', 'Indicadores públicos'),
        ('img/generated/observatorios/reportes-boletines.webp', 'Reportes y boletines'),
        ('img/generated/observatorios/documentacion-metodologias.webp', 'Documentación y metodologías'),
        ('img/generated/observatorios/alertas-tendencias.webp', 'Alertas y tendencias'),
    ],
    'turismo': [
        ('img/generated/observatorios/mapas-territoriales.webp', 'Mapas territoriales'),
        ('img/cards/tulcan.png', 'Tulcán y su patrimonio'),
        ('img/generated/connected-platforms-v2/observatorios.png', 'Observación del territorio'),
        ('img/generated/home-hero/hero-energia-sostenible.png', 'Territorio y sostenibilidad'),
    ],
    'plantas': [
        ('img/generated/connected-platforms-v2/plantas-piloto.png', 'Plantas piloto'),
        ('img/generated/home-hero/hero-alimentos-biotecnologia.png', 'Procesamiento de alimentos'),
        ('img/generated/connected-units/laboratorio-alimentos.png', 'Control de calidad de alimentos'),
        ('img/generated/connected-platforms-v2/centro-investigacion-alimentos.png', 'Desarrollo de productos'),
    ],
    'lacteos': [
        ('img/pilares/LabLactesos.png', 'Planta de lácteos'),
        ('img/cards/lacteos.png', 'Productos lácteos'),
        ('img/generated/connected-platforms-v2/plantas-piloto.png', 'Plantas piloto'),
        ('img/generated/connected-units/laboratorio-alimentos.png', 'Control de calidad de la leche'),
    ],
    'agro': [
        ('img/generated/home-hero/hero-agricultura-precision.png', 'Agricultura de precisión'),
        ('img/generated/home-hero/hero-agrotecnologia.png', 'Agrotecnología'),
        ('img/generated/connected-units/unidad-invernadero.png', 'Invernadero'),
        ('img/pilares/sistemas-de-produccion-agricola.jpg', 'Sistemas de producción agrícola'),
        ('img/generated/connected-platforms-v2/centro-investigacion-agropecuaria.png', 'Investigación agropecuaria'),
        ('img/generated/industria40-drones-agro.png', 'Drones en el agro'),
    ],
}

# El tema de cada unidad; las áreas que trabajan otra cosa lo cambian abajo.
TEMA_DE_UNIDAD = {
    'laboratorio-fabricacion-digital-prototipado': 'fabricacion',
    'laboratorio-robotica-electronica-automatizacion': 'robotica',
    'laboratorio-realidad-extendida': 'xr',
    'laboratorio-inteligencia-artificial-ciencia-datos': 'datos',
    'laboratorio-ciberseguridad-redes': 'redes',
    'laboratorio-multimedia-produccion-audiovisual': 'multimedia',
    'laboratorio-analisis-calidad-alimentos-suelos-aguas': 'alimentos',
    'laboratorio-reologia-textura-alimentos': 'alimentos',
    'laboratorio-analisis-sensorial-desarrollo-alimentos': 'alimentos',
    'laboratorio-microbiologia-biotecnologia-aplicada': 'biotecnologia',
    'laboratorio-diagnostico-veterinario-biologia-molecular': 'biotecnologia',
    'laboratorio-clinico': 'clinico',
    'laboratorio-simulacion-clinica-enfermeria': 'simulacion',
    'laboratorio-innovacion-educativa': 'educacion',
    'laboratorio-logistica-comercio-internacional': 'logistica',
    'laboratorio-emprendimiento-innovacion-empresarial': 'emprendimiento',
    'laboratorio-asuntos-publicos-gobierno': 'gobierno',
    'laboratorio-energias-renovables-territorio': 'turismo',
    'planta-piloto-lacteos': 'lacteos',
    'planta-piloto-carnicos': 'plantas',
    'planta-piloto-cereales': 'plantas',
    'planta-piloto-frutas-vegetales': 'plantas',
    'planta-extraccion-almidon-biotecnologia': 'plantas',
    'centro-experimental-san-francisco': 'agro',
}
TEMA_DE_AREA = {
    'FAB-AREA-ROBOTICA': 'robotica',
    'FAB-AREA-SCAN3D': 'xr',
    'ANC-AREA-SUELOS': 'agro',
    'ANC-AREA-AMBIENTAL': 'agro',
    'ROB-AREA-IOT': 'redes',
    'XR-AREA-SIM': 'datos',
    'TUR-AREA-SIG': 'turismo',
    'EDU-AREA-ROBOTICA': 'robotica',
    'ALM-AREA-DERIVADOS': 'biotecnologia',
}
# Cuántas imágenes lleva el collage de cada área.
IMAGENES_POR_AREA = 5

GRUPOS_DE_VIDEOS = ('videos_fab_rob_xr', 'videos_ia_ciber_media_edu', 'videos_alimentos_micro_vet',
                    'videos_salud_gestion', 'videos_plantas')
VIDEOS = {}
for _grupo in GRUPOS_DE_VIDEOS:
    for _slug, _areas in import_module(f'{__package__}.{_grupo}').VIDEOS.items():
        VIDEOS.setdefault(_slug, {}).update(_areas)


def imagenes_de(slug, codigo):
    """Las imágenes referenciales del área, con su tema primero y, si faltan, las de su unidad."""
    propias = IMAGENES[TEMA_DE_AREA.get(codigo, TEMA_DE_UNIDAD[slug])]
    de_la_unidad = [imagen for imagen in IMAGENES[TEMA_DE_UNIDAD[slug]] if imagen not in propias]
    return (propias + de_la_unidad)[:IMAGENES_POR_AREA]


def videos_de(slug, codigo):
    return VIDEOS.get(slug, {}).get(codigo, [])
