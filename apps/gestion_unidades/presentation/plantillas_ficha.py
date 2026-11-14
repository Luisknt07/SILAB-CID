"""La ficha técnica estándar de los equipos: las mismas secciones, en el mismo orden, para todos.

Cada grupo de producto (Cómputo, Impresión y fabricación digital, Laboratorio analítico…) tiene su plantilla de
especificaciones: una computadora muestra procesador, memoria, almacenamiento, tarjeta gráfica, monitor,
puertos, sistema operativo…; una impresora 3D, tecnología, volumen de trabajo, resolución, materiales… Lo que
la unidad no ha registrado no se inventa: el público ve lo que hay y quien gestiona ve qué falta.

ficha_estandar(tipo) reúne, de lo ya guardado, la descripción, las especificaciones (de la plantilla, del texto
«Clave: valor» de las características y de los datos estructurados), la capacidad de producción, lo que
incluye y los accesorios con su uso, las fotos, los videos de manejo (los del modelo o, si no tiene, los de su
familia), lo que necesita para operar y qué tan completa está la ficha.
"""
import unicodedata
import re

from apps.recursos.models.identificadores import youtube_id  # noqa: F401 - la misma regla que valida el modelo

from apps.recursos.presentation.catalogo_inventario import normalizar
from apps.recursos.presentation.componentes_equipo import categoria_de
from apps.recursos.presentation.referencia_editor import videos_vigentes

# (clave, palabras con que suele venir escrita, ¿es capacidad de producción?)
PLANTILLAS = {
    'Cómputo': [
        ('Procesador', ('procesador', 'cpu', 'nucleos'), False),
        ('Memoria RAM', ('memoria ram', 'memoria', 'ram'), False),
        ('Almacenamiento', ('almacenamiento', 'disco', 'ssd'), False),
        ('Tarjeta gráfica', ('tarjeta grafica', 'grafica', 'gpu', 'aceleradora'), False),
        ('Pantalla o monitor', ('monitor', 'pantalla'), False),
        ('Puertos y conectividad', ('puertos', 'conectividad', 'usb', 'conexion'), False),
        ('Red', ('red', 'ethernet', 'wifi', 'wi fi'), False),
        ('Sistema operativo', ('sistema operativo', 'windows', 'linux'), False),
        ('Alimentación y consumo', ('alimentacion', 'consumo', 'fuente', 'ups'), False),
        ('Certificaciones', ('certificacion', 'energy star', 'epeat'), False),
    ],
    'Impresión y fabricación digital': [
        ('Tecnología', ('tecnologia', 'tipo'), False),
        ('Área o volumen de trabajo', ('volumen', 'area de trabajo', 'area de corte', 'cama', 'capacidad'), True),
        ('Resolución o precisión', ('resolucion', 'precision', 'capa'), False),
        ('Velocidad', ('velocidad',), True),
        ('Materiales compatibles', ('materiales', 'material', 'filamento', 'resina'), False),
        ('Potencia', ('potencia', 'laser', 'husillo'), False),
        ('Conectividad', ('conectividad', 'conexion', 'wifi', 'usb'), False),
        ('Software de preparación', ('software', 'laminador', 'slicer'), False),
    ],
    'Realidad extendida': [
        ('Tipo de visor', ('tipo', 'visor'), False),
        ('Resolución por ojo', ('resolucion',), False),
        ('Campo de visión', ('campo de vision', 'fov'), False),
        ('Tasa de refresco', ('refresco', 'hz'), False),
        ('Seguimiento', ('seguimiento', 'tracking'), False),
        ('Controles', ('controles', 'mandos'), False),
        ('Procesador o plataforma', ('procesador', 'plataforma', 'chip'), False),
        ('Almacenamiento', ('almacenamiento', 'memoria'), False),
        ('Autonomía de batería', ('bateria', 'autonomia'), True),
        ('Conectividad', ('conectividad', 'conexion', 'usb', 'wifi'), False),
    ],
    'Robótica y electrónica': [
        ('Tipo', ('tipo',), False),
        ('Grados de libertad o canales', ('grados', 'ejes', 'canales'), False),
        ('Carga útil o alcance', ('carga', 'alcance', 'capacidad'), True),
        ('Precisión', ('precision', 'repetibilidad', 'resolucion'), False),
        ('Controlador', ('controlador', 'microcontrolador', 'placa'), False),
        ('Interfaces y comunicación', ('interfaz', 'comunicacion', 'protocolo', 'conectividad'), False),
        ('Software o lenguaje', ('software', 'lenguaje', 'programacion'), False),
        ('Alimentación', ('alimentacion', 'voltaje', 'bateria'), False),
    ],
    'Audio y video': [
        ('Tipo', ('tipo',), False),
        ('Resolución o formato', ('resolucion', 'formato'), False),
        ('Sensor u óptica', ('sensor', 'optica', 'lente'), False),
        ('Conectividad', ('conectividad', 'conexion', 'salidas', 'hdmi', 'xlr'), False),
        ('Montaje', ('montaje', 'tripode', 'soporte'), False),
        ('Software', ('software',), False),
        ('Alimentación', ('alimentacion', 'bateria'), False),
    ],
    'Redes y ciberseguridad': [
        ('Tipo', ('tipo',), False),
        ('Puertos', ('puertos',), False),
        ('Velocidad', ('velocidad', 'gbps', 'mbps'), True),
        ('Protocolos', ('protocolo',), False),
        ('Gestión y seguridad', ('gestion', 'seguridad', 'firewall'), False),
        ('Alimentación o PoE', ('alimentacion', 'poe'), False),
        ('Montaje', ('montaje', 'rack'), False),
    ],
    'Laboratorio analítico': [
        ('Principio de medición', ('principio', 'metodo', 'tecnica'), False),
        ('Rango de medición', ('rango', 'escala'), True),
        ('Resolución', ('resolucion', 'legibilidad'), False),
        ('Exactitud', ('exactitud', 'precision', 'incertidumbre'), False),
        ('Capacidad de muestras', ('capacidad', 'muestras', 'posiciones'), True),
        ('Calibración', ('calibracion',), False),
        ('Software y exportación de datos', ('software', 'datos', 'exportacion'), False),
        ('Alimentación', ('alimentacion', 'voltaje'), False),
    ],
    'Microbiología y biología molecular': [
        ('Tipo', ('tipo',), False),
        ('Capacidad', ('capacidad', 'volumen', 'posiciones', 'muestras'), True),
        ('Rango de temperatura', ('temperatura',), False),
        ('Control y precisión', ('control', 'precision', 'uniformidad'), False),
        ('Clase de seguridad', ('clase', 'bioseguridad', 'seguridad'), False),
        ('Alimentación', ('alimentacion', 'voltaje'), False),
    ],
    'Procesamiento de alimentos': [
        ('Tipo de proceso', ('proceso', 'tipo'), False),
        ('Capacidad de producción', ('capacidad', 'carga', 'volumen'), True),
        ('Rendimiento por hora', ('rendimiento', 'produccion', 'kg h', 'l h'), True),
        ('Material de construcción', ('material', 'acero'), False),
        ('Potencia y alimentación', ('potencia', 'motor', 'alimentacion', 'voltaje'), False),
        ('Servicios que requiere', ('servicios', 'agua', 'vapor', 'aire', 'gas'), False),
        ('Controles', ('control', 'tablero', 'temporizador'), False),
        ('Normas sanitarias', ('norma', 'sanitari', 'inocuidad'), False),
    ],
    'Refrigeración y conservación': [
        ('Tipo', ('tipo',), False),
        ('Capacidad', ('capacidad', 'volumen', 'litros'), True),
        ('Rango de temperatura', ('temperatura',), False),
        ('Control y alarmas', ('control', 'alarma', 'registro'), False),
        ('Refrigerante', ('refrigerante', 'gas'), False),
        ('Alimentación', ('alimentacion', 'voltaje'), False),
    ],
    'Salud y simulación clínica': [
        ('Tipo', ('tipo',), False),
        ('Procedimientos que permite', ('procedimiento', 'practica', 'permite'), False),
        ('Fidelidad', ('fidelidad', 'realismo'), False),
        ('Monitoreo y software', ('monitor', 'software', 'control'), False),
        ('Alimentación', ('alimentacion', 'bateria'), False),
    ],
    'Agropecuario': [
        ('Tipo', ('tipo',), False),
        ('Capacidad', ('capacidad', 'volumen', 'area'), True),
        ('Rendimiento', ('rendimiento', 'produccion'), True),
        ('Potencia o motor', ('potencia', 'motor'), False),
        ('Alimentación o combustible', ('alimentacion', 'combustible', 'bateria'), False),
    ],
    'Mobiliario e infraestructura': [
        ('Tipo', ('tipo',), False),
        ('Dimensiones', ('dimension', 'medidas'), False),
        ('Material', ('material',), False),
        ('Capacidad', ('capacidad', 'puestos', 'personas'), True),
        ('Configuración', ('configuracion', 'modular'), False),
    ],
}
GENERAL = [
    ('Tipo', ('tipo',), False),
    ('Capacidad', ('capacidad',), True),
    ('Características principales', ('caracteristicas', 'funciones'), False),
    ('Alimentación', ('alimentacion', 'voltaje', 'bateria'), False),
]
DESCRIPCION_COMPLETA = 160  # caracteres desde los que la descripción se considera detallada


def plantilla_de(tipo):
    grupo = tipo.familia.grupo if tipo.familia_id else ''
    return grupo or 'Otros', PLANTILLAS.get(grupo, GENERAL)


def pares_de(texto):
    """Las características «Clave: valor» del texto, en líneas o separadas por « / »; el resto es prosa."""
    pares, prosa = [], []
    for trozo in re.split(r'\n|\s/\s', texto or ''):
        trozo = trozo.strip(' -•\t')
        if not trozo:
            continue
        clave, separador, valor = trozo.partition(':')
        if separador and valor.strip() and len(clave) <= 40:
            pares.append((clave.strip(), valor.strip()))
        else:
            prosa.append(trozo)
    return pares, ' '.join(prosa)


def _corresponde(clave, palabras):
    texto = normalizar(clave)
    return any(re.search(rf'\b{re.escape(palabra)}', texto) for palabra in palabras)


def accesorios_de(lista):
    """Cada accesorio como {nombre, uso, cantidad}: admite textos sueltos, «2 × Nombre | cómo se usa» o diccionarios."""
    resultado = []
    for item in lista or []:
        if isinstance(item, dict):
            nombre, uso = str(item.get('nombre') or '').strip(), str(item.get('uso') or '').strip()
            cantidad = item.get('cantidad') or 1
        else:
            nombre, _barra, uso = str(item).partition('|')
            nombre, uso = nombre.strip(), uso.strip()
            coincidencia = re.match(r'^(\d+)\s*[×xX]\s+(.+)$', nombre)
            cantidad, nombre = (int(coincidencia.group(1)), coincidencia.group(2).strip()) if coincidencia else (1, nombre)
        if nombre:
            resultado.append({'nombre': nombre, 'uso': uso, 'cantidad': int(cantidad) if str(cantidad).isdigit() else 1})
    return resultado


TIPOS_DE_COMPONENTE = (
    ('incluido', 'Viene con el equipo', 'fas fa-box-open'),
    ('complementario', 'Complementos (no obligatorios)', 'fas fa-puzzle-piece'),
    ('repuesto', 'Repuestos y consumibles', 'fas fa-sync-alt'),
)


def _clave_de(nombre):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', nombre.lower()).encode('ascii', 'ignore').decode())[:24]


def componentes_de(tipo, incluye, opcionales):
    """Lo del modelo primero (incluido u opcional) y luego lo de su familia que el modelo no nombra."""
    componentes = ([{**item, 'tipo': 'incluido', 'de_familia': False} for item in incluye]
                   + [{**item, 'tipo': 'complementario', 'de_familia': False} for item in opcionales]
                   + [{**item, 'tipo': 'repuesto', 'de_familia': False} for item in accesorios_de(tipo.repuestos or [])])
    propios = {_clave_de(item['nombre']) for item in componentes}
    for item in (tipo.familia.componentes or []) if tipo.familia_id else []:
        if isinstance(item, dict) and item.get('nombre') and _clave_de(item['nombre']) not in propios:
            componentes.append({'nombre': item['nombre'], 'uso': item.get('uso', ''), 'cantidad': item.get('cantidad') or 1,
                                'tipo': item.get('tipo') if item.get('tipo') in dict((t[0], t) for t in TIPOS_DE_COMPONENTE) else 'complementario',
                                'de_familia': True})
    return [{'clave': clave, 'titulo': titulo, 'icono': icono, 'items': [item for item in componentes if item['tipo'] == clave]}
            for clave, titulo, icono in TIPOS_DE_COMPONENTE if any(item['tipo'] == clave for item in componentes)]


def _numero(valor):
    if valor is None:
        return ''
    texto = f'{valor:f}'.rstrip('0').rstrip('.') if hasattr(valor, 'as_tuple') else str(valor)
    return texto.replace('.', ',')


def ficha_estandar(tipo, gestor=False):
    """Las secciones de la ficha técnica estándar del modelo, con lo que falta registrar."""
    grupo, plantilla = plantilla_de(tipo)
    guardadas = {clave: str(valor).strip() for clave, valor in (tipo.especificaciones or {}).items() if str(valor).strip()}
    pares, prosa = pares_de(tipo.caracteristicas_publicas)
    especificaciones, usados, faltan = [], set(), []
    for clave, palabras, capacidad in plantilla:
        valor = guardadas.get(clave, '')
        if not valor:
            encontrado = next(((i, v) for i, (k, v) in enumerate(pares) if i not in usados and _corresponde(k, palabras)), None)
            if encontrado:
                usados.add(encontrado[0])
                valor = encontrado[1]
        if valor:
            especificaciones.append({'clave': clave, 'valor': valor, 'capacidad': capacidad})
        else:
            faltan.append(clave)
    # Lo registrado que la plantilla no nombra también se muestra: nada de lo que la unidad escribió se pierde.
    extra = [{'clave': k, 'valor': v, 'capacidad': False} for i, (k, v) in enumerate(pares) if i not in usados]
    extra += [{'clave': k, 'valor': v, 'capacidad': False} for k, v in guardadas.items() if k not in {c for c, _p, _x in plantilla}]
    generales = [(etiqueta, valor) for etiqueta, valor in (
        ('Marca', tipo.marca or ''), ('Modelo', tipo.modelo or ''),
        ('Dimensiones', ' × '.join(f'{_numero(medida)} mm' for medida in (tipo.largo_mm, tipo.ancho_mm, tipo.alto_mm) if medida)),
        ('Peso', f'{_numero(tipo.peso_kg)} kg' if tipo.peso_kg else ''),
    ) if valor]
    # La capacidad que ya está en la hoja de especificaciones (marcada) no se repite: aquí va solo lo de producción.
    capacidad_en_hoja = [item for item in especificaciones if item['capacidad']]
    capacidad = []
    if tipo.capacidad_nominal:
        capacidad.insert(0, {'clave': 'Capacidad nominal', 'valor': f'{_numero(tipo.capacidad_nominal)} {tipo.unidad_capacidad}'.strip(),
                             'capacidad': True})
    if tipo.capacidad_util_min or tipo.capacidad_util_max:
        capacidad.append({'clave': 'Rango útil', 'valor': f'{_numero(tipo.capacidad_util_min) or "—"} a {_numero(tipo.capacidad_util_max) or "—"} {tipo.unidad_capacidad}'.strip(),
                          'capacidad': True})
    for clave, valor in (('Preparación', tipo.tiempo_setup), ('Limpieza', tipo.tiempo_limpieza)):
        if valor:
            capacidad.append({'clave': clave, 'valor': f'{_numero(valor)} min', 'capacidad': True})
    energia = ', '.join(filter(None, (
        f'{_numero(tipo.voltaje)} V' if tipo.voltaje else '', f'{tipo.fases} fase{"s" if tipo.fases and tipo.fases > 1 else ""}' if tipo.fases else '',
        f'{_numero(tipo.potencia_kw)} kW' if tipo.potencia_kw else '')))
    servicios = ', '.join(filter(None, (
        f'agua {_numero(tipo.consumo_agua)} L/ciclo' if tipo.consumo_agua else '',
        f'aire {_numero(tipo.consumo_aire)} m³/h' if tipo.consumo_aire else '',
        f'vapor {_numero(tipo.consumo_vapor)} kg/h' if tipo.consumo_vapor else '')))
    if servicios and tipo.origen_datos_tecnicos == 'referencia':
        servicios += ' (consumo de referencia, por verificar en planta)'
    medios_por_revisar = bool(getattr(tipo, 'medios_publicos', {}).get('medios_por_revisar'))
    fotos = [{'url': foto.url, 'titulo': foto.titulo, 'tipo': foto.get_tipo_display(), 'credito': foto.credito}
             for foto in tipo.fotos.all() if foto.url and (not medios_por_revisar or foto.imagen)]
    videos = videos_vigentes(tipo)
    incluye, opcionales = accesorios_de(tipo.get_accesorios_incluidos_crudos()), accesorios_de(tipo.get_accesorios_opcionales_crudos())
    descripcion = (tipo.descripcion or '').strip()
    descripcion_familia = (tipo.familia.descripcion or '').strip() if tipo.familia_id else ''
    puntos = {
        # La del modelo más la del tipo de equipo: entre las dos, la ficha explica qué es y cómo se usa.
        'Descripción detallada': len(descripcion) + len(descripcion_familia) >= DESCRIPCION_COMPLETA,
        'Especificaciones técnicas': len(especificaciones) >= max(1, (len(plantilla) + 1) // 2),
        'Marca y modelo': bool(tipo.marca and tipo.modelo),
        'Foto del equipo': bool(tipo.imagen or tipo.imagen_catalogo or fotos),
        'Componentes y accesorios': bool(incluye or opcionales or (tipo.familia_id and tipo.familia.componentes)),
        'Modos de uso': bool(tipo.modos_uso or (tipo.familia_id and tipo.familia.modos_uso)),
        'Video de manejo': bool(videos),
        'Uso y cuidados': bool((tipo.uso_publico or '').strip() and (tipo.instrucciones_publicas or '').strip()),
    }
    if any(capacidad_ for _c, _p, capacidad_ in plantilla):
        puntos['Capacidad de producción'] = bool(capacidad or capacidad_en_hoja)
    return {
        'grupo': grupo,
        'descripcion': descripcion,
        'descripcion_familia': descripcion_familia,
        'otras_caracteristicas': prosa,
        'generales': generales,
        # Cada especificación con su categoría e ícono, como la ficha del fabricante.
        'especificaciones': [{**item, 'categoria': categoria_de(item['clave'])[0], 'icono': categoria_de(item['clave'])[1]}
                             for item in especificaciones + extra],
        'faltan': faltan if gestor else [],
        'capacidad': capacidad,
        'incluye': incluye,
        'opcionales': opcionales,
        'componentes': componentes_de(tipo, incluye, opcionales),
        'modos': [modo for modo in (tipo.modos_uso or (tipo.familia.modos_uso if tipo.familia_id else []) or [])
                  if isinstance(modo, dict) and modo.get('nombre')],
        'modos_de_familia': not tipo.modos_uso and bool(tipo.familia_id and tipo.familia.modos_uso),
        'sistema': tipo.familia.sistema if tipo.familia_id else '',
        'fotos': fotos,
        'videos': [{'id': video.youtube_id, 'titulo': video.titulo, 'canal': video.canal,
                    'de_familia': video.familia_id is not None} for video in videos if video.youtube_id],
        'requisitos': [(etiqueta, valor) for etiqueta, valor in (('Energía', energia), ('Servicios', servicios)) if valor],
        'completitud': {
            'porcentaje': round(100 * sum(puntos.values()) / len(puntos)),
            'falta': [nombre for nombre, cumple in puntos.items() if not cumple],
        },
    }
