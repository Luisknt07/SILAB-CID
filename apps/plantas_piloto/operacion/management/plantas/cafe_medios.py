"""Catálogo visual de café, con procedencia y sin afirmar activos instalados."""

from apps.gestion_unidades.management.fichas_area.medios_familias import MEDIOS

RAIZ = "plantas_piloto/cafe/equipos/"
GENERADAS = (
    "silo",
    "fermentacion",
    "molino",
    "tolva",
    "empacadora",
    "actividad-agua",
    "muestreo",
    "catacion",
    "bodega",
    "trilladora",
    "despedradora",
    "desmucilaginador",
    "tamices",
)
FOTOS = {
    k: {
        "ruta": RAIZ + k + ".webp",
        "credito": "Ilustración referencial generada con IA · no es una fotografía de la planta",
        "fuente": "",
        "licencia": "",
    }
    for k in GENERADAS
}
for clave, archivo, autor in (
    ("trillado", "Coffee_hulling.jpg", "Vincent Mugaba"),
    ("secado", "Coffee_Bean_Drying_Table_-_Tanzania.jpg", "Harald Ulver"),
    (
        "despulpado",
        "Coffee_Pulping_Machine_with_Washing_Tank_-_Tanzania.jpg",
        "Harald Ulver",
    ),
    ("tostador", "Chinook25Kg1C_coffee_roaster.jpg", "Coffea"),
    ("seleccion", "Coffee_Bean_Manual_Sorting_-_Tanzania.jpg", "Harald Ulver"),
    ("cereza", "Freshly_picked_coffee_beans_-_Tanzania.jpg", "Harald Ulver"),
    ("verde", "High_Quality_Coffee_Beans_Closeup_-_Tanzania.jpg", "Harald Ulver"),
):
    FOTOS[clave] = {
        "ruta": RAIZ + clave + ".webp",
        "credito": autor
        + " · CC BY-SA 4.0 · Wikimedia Commons · imagen reducida/convertida a WebP",
        "fuente": "https://commons.wikimedia.org/wiki/File:" + archivo,
        "licencia": "https://creativecommons.org/licenses/by-sa/4.0/",
    }

FAMILIAS = {
    "bascula": "Balanzas de plataforma industrial",
    "balanza": "Balanzas de precisión",
    "balanza-lab": "Balanzas analíticas",
    "secador": "Deshidratadores de bandejas",
    "termometro": "Termómetros y registradores de temperatura",
    "clasificador": "Tamices y cernidores vibratorios industriales",
    "banda": "Cintas transportadoras y celdas de manufactura",
    "polvo": "Extractores y colectores de polvo y humos",
    "registro": "Computadoras y estaciones de trabajo",
    "etiqueta": "Impresoras de etiquetas",
    "humedad": "Analizadores de humedad",
    "estufa": "Estufas y hornos de secado",
    "ph": "Medidores de pH y conductividad",
    "brix": "Refractómetros",
    "color": "Colorímetros de laboratorio",
    "agua": "Sistemas de agua ultrapura y purificada",
    "recipientes": "Gavetas y pallets de producto",
}
for clave, familia in FAMILIAS.items():
    ruta, credito, fuente = MEDIOS[familia]["foto"]
    FOTOS[clave] = {
        "ruta": ruta,
        "credito": "Foto del tipo de equipo · " + credito,
        "fuente": fuente,
        "licencia": "",
    }

IMAGENES_EQUIPOS = {
    "BAS-CER": "bascula",
    "SEL-CER": "seleccion",
    "FLOT": "despulpado",
    "DESP": "despulpado",
    "PULPA": "recipientes",
    "FERM": "fermentacion",
    "LAVA": "despulpado",
    "DESM": "desmucilaginador",
    "CAMAS": "secado",
    "SECADOR": "secador",
    "HORNO": "secador",
    "TEMP": "termometro",
    "BAS-SECO": "bascula",
    "TOLVA": "tolva",
    "ELEVADOR": "tolva",
    "SILO-SECO": "silo",
    "TRILLA": "trilladora",
    "CLASIF": "clasificador",
    "BANDA": "banda",
    "DESPED": "despedradora",
    "POLVO": "polvo",
    "BODEGA-SECO": "bodega",
    "TOSTADOR": "tostador",
    "CURVAS": "registro",
    "CICLON": "polvo",
    "ENFRIADOR": "tostador",
    "SILO-TOST": "silo",
    "MOLINO": "molino",
    "SILO-MOL": "tolva",
    "EMPACADORA": "empacadora",
    "PESO": "balanza",
    "SELLO": "empacadora",
    "ETIQUETADORA": "etiqueta",
    "CODIFICADOR": "etiqueta",
    "ATMOSFERA": "empacadora",
    "CAJAS": "bodega",
    "BODEGA": "bodega",
    "CALADOR": "muestreo",
    "DIVISOR": "muestreo",
    "BAL-LAB": "balanza-lab",
    "HUMEDAD": "humedad",
    "ESTUFA": "estufa",
    "AW": "actividad-agua",
    "PH": "ph",
    "BRIX": "brix",
    "TRILLA-MUE": "trillado",
    "TAMIZ-VER": "tamices",
    "DEFECTOS": "seleccion",
    "DENSIDAD": "muestreo",
    "TOST-MUE": "catacion",
    "COLOR": "color",
    "MOL-MUE": "molino",
    "TAMIZ-MOL": "tamices",
    "CATACION": "catacion",
    "AGUA-LAB": "agua",
    "RETENCION": "muestreo",
}

GALERIAS = {
    "PPCA-BENEFICIO": [
        ("despulpado", "Despulpado y lavado"),
        ("fermentacion", "Fermentación por microlote"),
        ("secado", "Secado solar en camas"),
        ("secador", "Secado mecánico por aire"),
        ("seleccion", "Selección del café"),
    ],
    "PPCA-RECEPCION-SECO": [
        ("tolva", "Recepción y alimentación de la línea"),
        ("silo", "Silo de café seco"),
        ("trillado", "Trilla o descascarado"),
        ("clasificador", "Clasificación por tamaños"),
        ("seleccion", "Selección por calidad"),
    ],
    "PPCA-TORREFACCION": [
        ("tostador", "Torrefacción y enfriamiento"),
        ("registro", "Registro y comparación de curvas"),
        ("silo", "Silo de café tostado"),
        ("molino", "Molienda por granulometría"),
        ("catacion", "Control sensorial del perfil"),
    ],
    "PPCA-EMPAQUE": [
        ("empacadora", "Empaque de grano y molido"),
        ("balanza", "Control del peso neto"),
        ("etiqueta", "Etiquetado y lote"),
        ("bodega", "Empaque secundario y bodega"),
    ],
    "PPCA-CALIDAD": [
        ("catacion", "Laboratorio de calidad y catación"),
        ("muestreo", "Muestreo y división de la muestra"),
        ("balanza-lab", "Pesaje analítico"),
        ("actividad-agua", "Actividad de agua"),
        ("humedad", "Medición de humedad"),
    ],
}

VIDEOS = {
    "solar": (
        "n95my9Zy59s",
        "Manejo del café en el secado solar",
        "Cenicafé FNC",
        "Muestra cuidados del secado solar. El lote se libera mediante mediciones y procedimiento aprobado.",
    ),
    "trilla": (
        "JIe7XqLPKKI",
        "Compacta trilladora de café Pinhalense",
        "COMERSA TRADING",
        "Demostración de una línea de trilla; su modelo y capacidad no se atribuyen a la planta.",
    ),
    "trilla-integrada": (
        "BtUxrqUS2k0",
        "Trilladora conjugada Pinhalense",
        "COMERSA TRADING",
        "Permite reconocer limpieza, separación y trilla integradas; comparar con el flujo de la unidad.",
    ),
    "tueste": (
        "UaSO05HMSYc",
        "Tueste por receta y control de perfil",
        "Probat USA",
        "Demostración del registro y ajuste de una receta de tueste. Cada equipo requiere su propio perfil probado.",
    ),
    "grano": (
        "GM1qh3_FG4k",
        "Empaque de café en grano con válvula",
        "Rovema GmbH",
        "Demuestra dosificación, formación y sellado de bolsas. Presentaciones de la unidad: 250, 500 y 1.000 g.",
    ),
    "molido": (
        "a1yCE276EAo",
        "Línea automatizada de empaque de café molido",
        "Rovema GmbH",
        "Demostración de alimentación, dosificación y empaque, sin atribuir rendimiento comercial a la planta.",
    ),
    "cva": (
        "RFkj2Y4yc2Q",
        "Evaluación del Café de la SCA: introducción",
        "Specialty Coffee Association",
        "Introducción en español a Coffee Value Assessment; declarar el protocolo empleado al evaluar cada lote.",
    ),
}
VIDEOS_AREAS = {
    "PPCA-BENEFICIO": ["solar"],
    "PPCA-RECEPCION-SECO": ["trilla", "trilla-integrada"],
    "PPCA-TORREFACCION": ["tueste"],
    "PPCA-EMPAQUE": ["grano", "molido"],
    "PPCA-CALIDAD": ["cva"],
}


def imagen_de_equipo(clave):
    return FOTOS.get(IMAGENES_EQUIPOS.get(clave))


IMAGENES_INSUMOS = {
    "CEREZA": "cereza",
    "PER-LAV": "secado",
    "PER-HON": "secado",
    "CER-NAT": "secado",
    "VER-LAV": "verde",
    "VER-HON": "verde",
    "VER-NAT": "verde",
    "TOSTADO": "catacion",
    "BOL250": "bolsa-metalizada",
    "BOL500": "bolsa-metalizada",
    "BOL1000": "bolsa-metalizada",
    "ETIQUETA": "etiquetas-codigo-barras",
    "LINER": "bolsas-plasticas",
    "AGUA": "agua-potable",
    "DETERGENTE": "detergente",
    "EPP": "epp-laboratorio",
    "MUESTRA": "bolsa-evidencia",
}


def imagen_de_insumo(clave):
    from apps.gestion_unidades.management.fichas_area.imagenes_insumos import CLASES

    imagen = IMAGENES_INSUMOS[clave]
    if imagen in FOTOS:
        return FOTOS[imagen]
    ruta, credito, fuente = CLASES[imagen]
    return {"ruta": ruta, "credito": credito, "fuente": fuente}


def videos_de_area(codigo):
    return [
        {"id": v[0], "titulo": v[1], "canal": v[2], "descripcion": v[3]}
        for c in VIDEOS_AREAS.get(codigo, [])
        for v in [VIDEOS[c]]
    ]


def nombre_de_proceso(receta, unidad):
    """El menú identifica la operación, sin renombrar productos o ids de recetas."""
    if unidad.slug == "planta-piloto-cafe" and receta.codigo in (
        "CAF-R-VER-LAV",
        "CAF-R-VER-HON",
        "CAF-R-VER-NAT",
    ):
        return "Trilla, clasificación y selección · " + receta.nombre_publico
    return receta.nombre_publico
