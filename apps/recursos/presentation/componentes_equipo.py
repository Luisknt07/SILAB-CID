"""Cómo se presentan los componentes y las especificaciones de un equipo: con foto o ícono y por categoría.

Lo fijo es lo que viene con el equipo y sus complementos: se inventarían con él. Lo consumible se gasta y se repone
desde el inventario de insumos de la unidad; los repuestos de referencia que el inventario ya tiene no se repiten.
"""
import re
import unicodedata

CATEGORIAS_DE_ESPECIFICACION = (
    (('procesador', 'cpu', 'plataforma', 'chip'), 'Procesamiento', 'fas fa-microchip'),
    (('memoria', 'ram'), 'Memoria', 'fas fa-memory'),
    (('almacenamiento', 'disco', 'ssd'), 'Almacenamiento', 'fas fa-hdd'),
    (('grafica', 'gpu'), 'Gráficos', 'fas fa-tv'),
    (('precision', 'velocidad', 'exactitud', 'rango', 'resolucion'), 'Rendimiento', 'fas fa-tachometer-alt'),
    (('pantalla', 'display', 'monitor', 'campo visual'), 'Pantalla', 'fas fa-desktop'),
    (('bateria', 'autonomia', 'energia', 'potencia', 'voltaje', 'alimentacion', 'consumo'), 'Energía', 'fas fa-bolt'),
    (('conectividad', 'puerto', 'wi-fi', 'wifi', 'bluetooth', 'red', 'interfaz'), 'Conectividad', 'fas fa-wifi'),
    (('seguimiento', 'sensor', 'camara', 'deteccion', 'profundidad', 'escaneo'), 'Sensores', 'fas fa-crosshairs'),
    (('peso', 'dimension', 'tamano', 'medida'), 'Físico', 'fas fa-ruler-combined'),
    (('volumen', 'capacidad', 'area de trabajo', 'area de corte', 'cama', 'carga'), 'Capacidad', 'fas fa-cube'),
    (('temperatura', 'calor', 'frio'), 'Temperatura', 'fas fa-thermometer-half'),
    (('material', 'compatible'), 'Materiales', 'fas fa-layer-group'),
    (('modelo', 'referencia', 'marca'), 'Identificación', 'fas fa-tag'),
    (('sistema', 'software', 'firmware'), 'Software', 'fas fa-code'),
    (('funcion', 'uso', 'aplicacion'), 'Funciones', 'fas fa-magic'),
)

ICONOS_DE_COMPONENTE = (
    # Lo más específico primero: «Pilas AA para los controles» son pilas, no un mando.
    (('pila', 'bateria'), 'fas fa-battery-full'),
    (('cargador', 'estacion de carga', 'base de carga', 'base o estacion'), 'fas fa-charging-station'),
    (('cable', 'adaptador', 'conector', 'extension'), 'fas fa-plug'),
    (('lente', 'separador', 'gafa protectora'), 'fas fa-glasses'),
    (('visor', 'casco de realidad', 'gafas de realidad'), 'fas fa-vr-cardboard'),
    (('mando', 'control tactil', 'controles', 'joystick'), 'fas fa-gamepad'),
    (('correa', 'arnes', 'banda'), 'fas fa-link'),
    (('almohadilla', 'interfaz facial', 'mascara', 'acolchado'), 'fas fa-mask'),
    (('estuche', 'maleta', 'funda', 'bolso', 'caja de transporte'), 'fas fa-briefcase'),
    (('pano', 'limpieza', 'toallita', 'cepillo'), 'fas fa-broom'),
    (('router', 'punto de acceso', 'wi-fi', 'wifi'), 'fas fa-wifi'),
    (('teclado',), 'fas fa-keyboard'),
    (('mouse', 'raton'), 'fas fa-mouse'),
    (('monitor', 'pantalla', 'proyector'), 'fas fa-desktop'),
    (('camara', 'webcam'), 'fas fa-camera'),
    (('microfono',), 'fas fa-microphone'),
    (('audifono', 'auricular', 'parlante', 'altavoz'), 'fas fa-headphones'),
    (('sensor', 'sonda', 'electrodo'), 'fas fa-microchip'),
    (('filtro',), 'fas fa-filter'),
    (('boquilla', 'nozzle', 'extrusor'), 'fas fa-tint'),
    (('fresa', 'cuchilla', 'hoja', 'broca'), 'fas fa-cut'),
    (('llave', 'herramienta', 'destornillador', 'pinza', 'espatula', 'kit de mantenimiento'), 'fas fa-tools'),
    (('manual', 'guia', 'documentacion'), 'fas fa-book'),
    (('licencia', 'software', 'programa'), 'fas fa-compact-disc'),
    (('memoria', 'tarjeta sd', 'usb'), 'fas fa-sd-card'),
    (('tubo', 'vial', 'cubeta', 'frasco', 'recipiente'), 'fas fa-vial'),
    (('bandeja', 'placa', 'cama'), 'fas fa-th'),
    (('guante', 'proteccion', 'protector'), 'fas fa-hand-paper'),
    (('ups', 'regulador', 'fuente de poder', 'fuente de alimentacion'), 'fas fa-bolt'),
)


def normal(texto):
    """Minúsculas sin tildes ni signos: para comparar nombres escritos de distinta forma."""
    texto = unicodedata.normalize('NFKD', str(texto or '').lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 -]', ' ', texto)).strip()


def coinciden(uno, otro):
    a, b = normal(uno), normal(otro)
    return bool(a and b) and (a == b or (len(a) > 5 and a in b) or (len(b) > 5 and b in a))


def categoria_de(clave):
    texto = normal(clave)
    for palabras, categoria, icono in CATEGORIAS_DE_ESPECIFICACION:
        if any(palabra in texto for palabra in palabras):
            return categoria, icono
    return 'General', 'fas fa-cog'


def icono_de_componente(nombre):
    texto = normal(nombre)
    for palabras, icono in ICONOS_DE_COMPONENTE:
        if any(palabra in texto for palabra in palabras):
            return icono
    return 'fas fa-puzzle-piece'


def componentes_con_inventario(grupos, insumos, insumos_de_ficha, fotos):
    """Los grupos de componentes con foto (o ícono) y los consumibles del inventario unidos a los repuestos.

    `insumos` son las relaciones ConsumiblePorEquipo de la unidad; `fotos`, las fotos del modelo ({url, titulo}).
    """
    def foto_de(nombre):
        return next((foto['url'] for foto in fotos if foto.get('titulo') and coinciden(foto['titulo'], nombre)), '')

    por_clave = {grupo['clave']: dict(grupo, items=list(grupo['items'])) for grupo in grupos}
    for grupo in por_clave.values():
        for item in grupo['items']:
            item['imagen'] = item.get('imagen') or foto_de(item['nombre'])
            item['icono'] = icono_de_componente(item['nombre'])
            item['naturaleza'] = 'repuesto' if grupo['clave'] == 'repuesto' else 'fijo'
    consumibles = []
    for relacion in insumos:
        insumo = relacion.consumible
        consumibles.append({
            'nombre': insumo.nombre, 'uso': insumo.presentacion or insumo.get_clasificacion_display(), 'cantidad': None,
            'tipo': 'repuesto', 'naturaleza': 'consumible', 'codigo': insumo.codigo, 'en_inventario': True,
            'existencia': insumo.stock_total, 'unidad_medida': insumo.unidad_medida or '',
            'imagen': insumo.imagen_publica_url or foto_de(insumo.nombre), 'icono': insumo.icono or icono_de_componente(insumo.nombre),
            'de_familia': False,
        })
    for nombre in insumos_de_ficha:
        if not any(coinciden(nombre, item['nombre']) for item in consumibles):
            consumibles.append({'nombre': nombre, 'uso': '', 'cantidad': None, 'tipo': 'repuesto', 'naturaleza': 'consumible',
                                'en_inventario': False, 'imagen': foto_de(nombre), 'icono': icono_de_componente(nombre),
                                'de_familia': False})
    if consumibles:
        from apps.gestion_unidades.presentation.plantillas_ficha import TIPOS_DE_COMPONENTE

        repuestos = por_clave.get('repuesto', {}).get('items', [])
        restantes = [item for item in repuestos if not any(coinciden(item['nombre'], consumible['nombre']) for consumible in consumibles)]
        _clave, titulo, icono = next(tipo for tipo in TIPOS_DE_COMPONENTE if tipo[0] == 'repuesto')
        por_clave['repuesto'] = {'clave': 'repuesto', 'titulo': titulo, 'icono': icono, 'items': consumibles + restantes}
    orden = ('incluido', 'complementario', 'repuesto')
    return [por_clave[clave] for clave in orden if clave in por_clave and por_clave[clave]['items']]
