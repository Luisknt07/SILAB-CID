from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.presentation.codigos_sistema import actualizar_o_crear, modelo_vigente, unidad_vigente
from apps.gestion_unidades.presentation.fusion_areas import area_vigente, integrada
from apps.gestion_unidades.management.datos_demo import ComandoDatosDemostrativosMixin
from apps.reservas.presentation.capacidad import comando_reservas
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, CapacidadOperativaUnidad
from apps.reservas.models.reservas import CatalogoActividadReserva, ProgramacionReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService, FablabServiceConsumible
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.core.models.usuarios_base import UserProfile



# La estación de diseño según el acta de entrega (Allping L&D): HP Z8 Fury G5.
WORKSTATION_DESCRIPCION = (
    'Estación de trabajo HP Z8 Fury G5 en formato torre para cargas intensivas: modelado CAD y CAM, simulación, '
    'renderizado, procesamiento de mallas 3D y desarrollo de realidad virtual (VR Ready). Combina un procesador '
    'Intel Xeon de 12 núcleos, 256 GB de memoria DDR5 y una tarjeta profesional NVIDIA RTX A4000 de 16 GB con '
    'corrección de errores, por lo que sostiene proyectos grandes sin cuellos de botella. En la estación de diseño '
    'se preparan los archivos que luego van a las impresoras 3D, la cortadora láser y el escáner.'
)
WORKSTATION_ESPECIFICACIONES = '\n'.join((
    'Procesador: Intel Xeon w5-3425 de 12 núcleos a 3,20 GHz',
    'Memoria RAM: 256 GB DDR5 SDRAM, ampliable a 2 TB',
    'Almacenamiento: SSD PCIe NVMe 4.0 x4 de 4 TB',
    'Tarjeta gráfica: NVIDIA RTX A4000 de 16 GB GDDR6 con ECC, 4 DisplayPort 1.4, PCIe Gen 4, 140 W, VR Ready',
    'Pantalla o monitor: monitor HP de 27 pulgadas',
    'Puertos y conectividad: 14 puertos USB (incluido USB Type-C con Power Delivery 3.0) y 4 salidas DisplayPort',
    'Red: Ethernet Gigabit dual',
    'Sistema operativo: Windows 11 Pro',
    'Alimentación y consumo: UPS de 3000 VA',
    'Certificaciones: EPEAT Gold y Energy Star',
))
WORKSTATION_INCLUYE = [
    {'nombre': 'Monitor HP de 27 pulgadas', 'uso': 'Conéctalo a una salida DisplayPort de la tarjeta gráfica, no a la placa.'},
    {'nombre': 'Teclado y mouse', 'uso': 'Por USB; sin ellos no se inicia la sesión del equipo.'},
    {'nombre': 'UPS de 3000 VA', 'uso': 'Enciende primero la UPS y luego la workstation; ante un corte, guarda y apaga.'},
]

class Command(ComandoDatosDemostrativosMixin, BaseCommand):
    help = (
        'Carga cinco conjuntos demostrativos de equipos, servicios y materiales '
        'para probar reservas en el laboratorio de Manufactura Digital/FabLab.'
    )

    EQUIPOS = [
        {
            'codigo': 'FAB-EQ-FDM',
            'codigo_unidad': 'FAB-UNIT-FDM-01',
            'unidades': ['FAB-UNIT-FDM-01', 'FAB-UNIT-FDM-02', 'FAB-UNIT-FDM-03'],
            'nombre': 'Impresora 3D FDM',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/impresora-3d-fdm.png',
            'categoria_codigo': 'FAB-IMP3D',
            'categoria': 'Impresión 3D',
            'icono': '🧊',
            'descripcion': (
                'Equipo demostrativo para fabricar prototipos por deposición de '
                'filamento. Requiere archivo STL o 3MF y revisión técnica previa.'
            ),
            'caracteristicas_publicas': (
                'Fabricación aditiva con filamento de 1,75 mm; admite piezas desde '
                'archivos STL o 3MF preparados en un laminador.'
            ),
            'uso_publico': 'Prototipos funcionales, maquetas, carcasas y validaciones de forma.',
            'instrucciones_publicas': (
                'Prepara o solicita la revisión del modelo, estima gramos y tiempo en '
                'el laminador y selecciona el color de PLA disponible.'
            ),
            'software': 'Laminador compatible con archivos STL y 3MF',
            'accesorios': ['Placa de impresión', 'Espátula', 'Kit de limpieza'],
            'requiere_insumos': True,
            'insumos': 'Filamento PLA de 1,75 mm.',
            'ubicacion': 'Zona de impresión 3D — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-SLA',
            'codigo_unidad': 'FAB-UNIT-SLA-01',
            'nombre': 'Impresora 3D de resina',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/impresora-3d-resina.png',
            'categoria_codigo': 'FAB-RESINA',
            'categoria': 'Impresión en resina',
            'icono': '💧',
            'descripcion': (
                'Equipo demostrativo de alta resolución para piezas pequeñas y '
                'prototipos detallados. Requiere resina y postprocesado.'
            ),
            'caracteristicas_publicas': (
                'Impresión de alta resolución con resina fotopolimérica y proceso '
                'posterior de lavado y curado.'
            ),
            'uso_publico': 'Piezas pequeñas, modelos detallados y prototipos de alta precisión visual.',
            'instrucciones_publicas': (
                'Entrega el modelo STL o 3MF e indica dimensiones y nivel de detalle; '
                'el uso de resina requiere supervisión y protección.'
            ),
            'software': 'Laminador compatible con archivos STL y 3MF',
            'accesorios': ['Plataforma de impresión', 'Cubeta de resina', 'Espátula'],
            'requiere_insumos': True,
            'insumos': 'Resina fotopolimérica y elementos de protección.',
            'ubicacion': 'Zona de impresión en resina — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-LASER',
            'codigo_unidad': 'FAB-UNIT-LASER-01',
            'nombre': 'Cortadora y grabadora láser',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/cortadora-laser.png',
            'categoria_codigo': 'FAB-LASER',
            'categoria': 'Corte y grabado láser',
            'icono': '✴️',
            'descripcion': (
                'Equipo demostrativo para cortar y grabar materiales planos. '
                'Requiere archivo vectorial y validación del material.'
            ),
            'caracteristicas_publicas': (
                'Corte y grabado sobre materiales planos compatibles, con mesa tipo '
                'panal y extracción localizada.'
            ),
            'uso_publico': 'Maquetas, señalética, plantillas, empaques y grabados personalizados.',
            'instrucciones_publicas': (
                'Prepara geometría vectorial a escala e indica material y espesor; '
                'el responsable valida la compatibilidad antes de reservar.'
            ),
            'software': 'Editor vectorial compatible con SVG, DXF y PDF',
            'accesorios': ['Sistema de extracción', 'Mesa tipo panal'],
            'requiere_insumos': True,
            'insumos': 'Láminas compatibles, por ejemplo MDF o acrílico.',
            'ubicacion': 'Zona de corte láser — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-CNC',
            'codigo_unidad': 'FAB-UNIT-CNC-01',
            'nombre': 'Fresadora CNC de escritorio',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/fresadora-cnc.png',
            'categoria_codigo': 'FAB-CNC',
            'categoria': 'Mecanizado CNC',
            'icono': '⚙️',
            'descripcion': (
                'Equipo demostrativo para mecanizado sustractivo de placas y '
                'piezas de prototipado. Requiere trayectoria CAM validada.'
            ),
            'caracteristicas_publicas': (
                'Mecanizado sustractivo de escritorio con sujeción de material, juego '
                'básico de fresas y aspiración.'
            ),
            'uso_publico': 'Relieves, placas, moldes y componentes rígidos de prototipado.',
            'instrucciones_publicas': (
                'Adjunta geometría o plano e indica material y tolerancias; la '
                'trayectoria CAM y la herramienta requieren aprobación técnica.'
            ),
            'software': 'Software CAD/CAM compatible con DXF y código G',
            'accesorios': ['Juego básico de fresas', 'Mordazas', 'Aspiración'],
            'requiere_insumos': True,
            'insumos': 'Material mecanizable y herramienta adecuada.',
            'ubicacion': 'Zona de mecanizado CNC — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-SCAN',
            'codigo_unidad': 'FAB-UNIT-SCAN-01',
            'nombre': 'Escáner 3D de objetos',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/escaner-3d.png',
            'categoria_codigo': 'FAB-SCAN3D',
            'categoria': 'Digitalización 3D',
            'icono': '📐',
            'descripcion': (
                'Equipo demostrativo para capturar geometría de objetos y generar '
                'mallas digitales editables para prototipado.'
            ),
            'caracteristicas_publicas': (
                'Captura de geometría con base giratoria y marcadores de referencia; '
                'genera mallas para edición y documentación.'
            ),
            'uso_publico': 'Digitalización, documentación e ingeniería inversa de objetos físicos.',
            'instrucciones_publicas': (
                'Describe dimensiones, superficie y acabado del objeto para confirmar '
                'la técnica de captura y el formato de entrega.'
            ),
            'software': 'Software de captura y limpieza de mallas 3D',
            'accesorios': ['Base giratoria', 'Marcadores de referencia'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Zona de digitalización — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-CAD',
            'codigo_unidad': 'FAB-UNIT-CAD-01',
            'unidades': ['FAB-UNIT-CAD-01', 'FAB-UNIT-CAD-02', 'FAB-UNIT-CAD-03'],
            'nombre': 'Computadora especializada para diseño',
            'imagen_catalogo': 'img/generated/platforms/software-analytics.png',
            'categoria_codigo': 'FAB-COMP-CAD',
            'categoria': 'Computación especializada',
            'icono': '🖥️',
            'marca': 'HP',
            'modelo': 'Z8 Fury G5 Workstation',
            'descripcion': WORKSTATION_DESCRIPCION,
            'caracteristicas_publicas': WORKSTATION_ESPECIFICACIONES,
            'uso_publico': 'Diseño, preparación de archivos, simulación y revisión técnica previa.',
            'instrucciones_publicas': (
                'Selecciona además el software que utilizarás para comprobar la '
                'licencia y la disponibilidad concurrente.'
            ),
            'admite_software_adicional': True,
            'software': 'Autodesk Fusion, SOLIDWORKS, Blender, Cura y MeshLab',
            'accesorios': WORKSTATION_INCLUYE,
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Zona de diseño y preproducción — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-VINIL',
            'codigo_unidad': 'FAB-UNIT-VINIL-01',
            'nombre': 'Plotter de corte de vinilo',
            'categoria_codigo': 'FAB-PLOTTER',
            'categoria': 'Corte y grabado',
            'icono': '✂️',
            'descripcion': (
                'Equipo demostrativo para corte de vinilos adhesivos, plantillas y '
                'rotulación a partir de archivos vectoriales.'
            ),
            'caracteristicas_publicas': (
                'Corte por cuchilla de vinilos y papeles de hasta 60 cm de ancho; '
                'acepta archivos SVG y DXF.'
            ),
            'uso_publico': 'Rotulación, plantillas, stickers y máscaras de corte.',
            'instrucciones_publicas': (
                'Prepara el diseño en vectores (SVG o DXF) e indica el material y los '
                'metros estimados.'
            ),
            'software': 'Software de corte con vectores SVG/DXF',
            'accesorios': ['Cuchilla 45°', 'Espátula', 'Regla de corte'],
            'requiere_insumos': True,
            'insumos': 'Vinilo adhesivo en rollo.',
            'ubicacion': 'Zona de corte láser — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-ELEC',
            'codigo_unidad': 'FAB-UNIT-ELEC-01',
            'nombre': 'Estación de soldadura y electrónica',
            'categoria_codigo': 'FAB-ELEC',
            'categoria': 'Electrónica e instrumentación',
            'icono': '🔌',
            'descripcion': (
                'Puesto demostrativo con estación de soldadura, fuente regulada y '
                'multímetro para ensamblar y probar prototipos electrónicos.'
            ),
            'caracteristicas_publicas': (
                'Estación de soldadura con control de temperatura, fuente de poder '
                'regulada de 0 a 30 V y multímetro digital.'
            ),
            'uso_publico': 'Ensamblaje de circuitos, pruebas de continuidad y alimentación de prototipos.',
            'instrucciones_publicas': (
                'Trae el esquema del circuito y la lista de componentes; el laboratorio '
                'provee estaño, flux y herramientas básicas.'
            ),
            'software': 'No aplica',
            'accesorios': ['Punta cónica', 'Esponja limpiadora', 'Pinzas antiestáticas'],
            'requiere_insumos': True,
            'insumos': 'Estaño y flux.',
            'ubicacion': 'Zona de electrónica — dato de prueba',
        },
        {
            'codigo': 'FAB-EQ-SECADOR',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '🌡️',
            'nombre': 'Secador de filamento',
            'rol': 'auxiliar',
            'apoya_a': ['FAB-EQ-FDM'],
            'unidades': ['UE-FAB-SEC-01'],
            'descripcion': (
                'Cámara de secado que quita la humedad del filamento antes de '
                'imprimir; acompaña a la impresora FDM.'
            ),
            'caracteristicas_publicas': 'Dos bobinas a la vez, control de temperatura y temporizador.',
            'uso_publico': 'Secar filamento higroscópico antes de una impresión larga.',
            'instrucciones_publicas': 'No se reserva aparte: está disponible junto a la impresora FDM.',
            'software': 'No requiere software',
            'accesorios': ['Bandeja para dos bobinas'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Área de impresión 3D',
        },
        {
            'codigo': 'FAB-EQ-CURADO',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '💡',
            'nombre': 'Estación de lavado y curado',
            'rol': 'auxiliar',
            'apoya_a': ['FAB-EQ-SLA'],
            'unidades': ['UE-FAB-CUR-01'],
            'descripcion': (
                'Lava con alcohol isopropílico y cura con luz ultravioleta las '
                'piezas impresas en resina; acompaña a la impresora de resina.'
            ),
            'caracteristicas_publicas': 'Cubeta de lavado con agitación y cámara de curado ultravioleta.',
            'uso_publico': 'Posprocesado de piezas de resina.',
            'instrucciones_publicas': 'No se reserva aparte: acompaña a la impresora de resina.',
            'software': 'No requiere software',
            'accesorios': ['Canasta de lavado', 'Plataforma giratoria'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Área de impresión 3D',
        },
    ]

    CONSUMIBLES = [
        {
            'codigo': 'FAB-MAT-PLA',
            'nombre': 'Filamento PLA blanco 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'Estándar 1,75 mm',
            'color': 'Blanco',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('3200.000'),
            'precio_unitario': Decimal('0.025'),
            'minimo': Decimal('500.000'),
            'descripcion': (
                'Existencia demostrativa de PLA blanco para impresión 3D FDM.'
            ),
            'instrucciones_solicitud': (
                'Carga el modelo en el laminador y escribe los gramos estimados. '
                'Si todavía no hiciste el cálculo, ábrelo en el laminador antes de reservar.'
            ),
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PLA-NEG',
            'nombre': 'Filamento PLA negro 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'Estándar 1,75 mm',
            'color': 'Negro',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('2750.000'),
            'precio_unitario': Decimal('0.025'),
            'minimo': Decimal('500.000'),
            'descripcion': 'Existencia demostrativa de PLA negro para impresión 3D FDM.',
            'instrucciones_solicitud': 'Indica los gramos que calculó el laminador para una pieza.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PLA-ROJ',
            'nombre': 'Filamento PLA rojo 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'Estándar 1,75 mm',
            'color': 'Rojo',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('1800.000'),
            'precio_unitario': Decimal('0.025'),
            'minimo': Decimal('500.000'),
            'descripcion': 'Existencia demostrativa de PLA rojo para impresión 3D FDM.',
            'instrucciones_solicitud': 'Indica los gramos que calculó el laminador para una pieza.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PLA-AZU',
            'nombre': 'Filamento PLA azul 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'Estándar 1,75 mm',
            'color': 'Azul',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('2100.000'),
            'precio_unitario': Decimal('0.025'),
            'minimo': Decimal('500.000'),
            'descripcion': 'Existencia demostrativa de PLA azul para impresión 3D FDM.',
            'instrucciones_solicitud': 'Indica los gramos que calculó el laminador para una pieza.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PLA-GRI',
            'nombre': 'Filamento PLA gris 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'Estándar 1,75 mm',
            'color': 'Gris',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('1500.000'),
            'precio_unitario': Decimal('0.025'),
            'minimo': Decimal('500.000'),
            'descripcion': 'Existencia demostrativa de PLA gris para impresión 3D FDM.',
            'instrucciones_solicitud': 'Indica los gramos que calculó el laminador para una pieza.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-RESINA',
            'nombre': 'Resina fotopolimérica estándar',
            'clasificacion': 'insumo',
            'familia': 'Resinas para impresión 3D',
            'variante': 'Estándar',
            'color': 'Gris',
            'presentacion': 'Botella de 1 L; existencia disponible por volumen',
            'unidad_medida': 'mL',
            'stock_total': Decimal('3000.000'),
            'precio_unitario': Decimal('0.060'),
            'minimo': Decimal('500.000'),
            'descripcion': (
                'Consumible demostrativo para impresión 3D de resina. Requiere '
                'manipulación supervisada y elementos de protección.'
            ),
            'instrucciones_solicitud': 'Indica los mililitros estimados por el laminador o solicita revisión técnica.',
            'imagen_catalogo': 'img/catalogo/fablab/resina-fotopolimerica.png',
            'ubicacion': 'Gabinete de resinas — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-MDF3',
            'nombre': 'Lámina MDF de 3 mm',
            'clasificacion': 'insumo',
            'familia': 'Materiales planos',
            'variante': 'Espesor 3 mm',
            'color': 'Natural',
            'presentacion': 'Lámina',
            'unidad_medida': 'lámina',
            'stock_total': Decimal('25.000'),
            'precio_unitario': Decimal('4.50'),
            'minimo': Decimal('5.000'),
            'descripcion': (
                'Material demostrativo para corte láser y mecanizado ligero. '
                'La compatibilidad y dimensiones se validan antes de aprobar.'
            ),
            'instrucciones_solicitud': 'Indica el número de láminas según el anidado de piezas.',
            'imagen_catalogo': 'img/catalogo/fablab/laminas-mdf-3mm.png',
            'ubicacion': 'Rack de materiales planos — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-ACR3',
            'nombre': 'Lámina de acrílico de 3 mm',
            'clasificacion': 'insumo',
            'familia': 'Materiales planos',
            'variante': 'Espesor 3 mm',
            'color': 'Transparente',
            'presentacion': 'Lámina',
            'unidad_medida': 'lámina',
            'stock_total': Decimal('18.000'),
            'precio_unitario': Decimal('8.00'),
            'minimo': Decimal('4.000'),
            'descripcion': (
                'Material demostrativo para corte o grabado láser. El color y '
                'las dimensiones se confirman durante la revisión.'
            ),
            'instrucciones_solicitud': 'Indica el número de láminas según el anidado de piezas.',
            'imagen_catalogo': 'img/catalogo/fablab/laminas-acrilico-3mm.png',
            'ubicacion': 'Rack de materiales planos — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-CINTA',
            'nombre': 'Cinta de enmascarar para prototipado',
            'clasificacion': 'material',
            'familia': 'Insumos auxiliares',
            'variante': 'Uso general',
            'color': 'Crema',
            'presentacion': 'Rollo',
            'unidad_medida': 'rollo',
            'stock_total': Decimal('12.000'),
            'precio_unitario': Decimal('1.50'),
            'minimo': Decimal('3.000'),
            'descripcion': (
                'Consumible demostrativo de apoyo para fijación, protección y '
                'preparación de piezas durante el prototipado.'
            ),
            'instrucciones_solicitud': 'Selecciona solo si el proceso requiere fijación o protección adicional.',
            'imagen_catalogo': 'img/catalogo/fablab/cinta-enmascarar.png',
            'ubicacion': 'Gabinete de herramientas — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PETG-NEG',
            'nombre': 'Filamento PETG negro 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'PETG 1,75 mm',
            'color': 'Negro',
            'presentacion': 'Bobinas de 1 kg; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('2400.000'),
            'precio_unitario': Decimal('0.032'),
            'minimo': Decimal('500.000'),
            'descripcion': 'PETG para piezas funcionales con mayor resistencia térmica y mecánica que el PLA.',
            'instrucciones_solicitud': 'Indica los gramos que calculó el laminador para una pieza.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-TPU',
            'nombre': 'Filamento TPU flexible 1,75 mm',
            'clasificacion': 'insumo',
            'familia': 'Filamentos para impresión 3D',
            'variante': 'TPU 95A',
            'color': 'Natural',
            'presentacion': 'Bobinas de 500 g; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('900.000'),
            'precio_unitario': Decimal('0.045'),
            'minimo': Decimal('250.000'),
            'descripcion': 'Filamento flexible para juntas, protectores y piezas elásticas; requiere velocidad reducida.',
            'instrucciones_solicitud': 'Indica los gramos estimados; el laboratorista confirmará la velocidad de impresión.',
            'imagen_catalogo': 'img/catalogo/fablab/filamentos-pla-colores.png',
            'ubicacion': 'Estante FDM — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-RESINA-TR',
            'nombre': 'Resina fotopolimérica transparente',
            'clasificacion': 'insumo',
            'familia': 'Resinas para impresión 3D',
            'variante': 'Transparente',
            'color': 'Transparente',
            'presentacion': 'Botella de 500 mL; existencia disponible por volumen',
            'unidad_medida': 'mL',
            'stock_total': Decimal('1500.000'),
            'precio_unitario': Decimal('0.075'),
            'minimo': Decimal('300.000'),
            'descripcion': 'Resina translúcida para piezas ópticas, carcasas y prototipos de detalle.',
            'instrucciones_solicitud': 'Indica los mililitros estimados por el laminador o solicita revisión técnica.',
            'imagen_catalogo': 'img/catalogo/fablab/resina-fotopolimerica.png',
            'ubicacion': 'Gabinete de resinas — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-IPA',
            'nombre': 'Alcohol isopropílico 99 %',
            'clasificacion': 'reactivo',
            'familia': 'Posprocesado de resina',
            'variante': 'Grado técnico',
            'color': '',
            'presentacion': 'Garrafa de 5 L; existencia disponible por volumen',
            'unidad_medida': 'mL',
            'stock_total': Decimal('5000.000'),
            'precio_unitario': Decimal('0.006'),
            'minimo': Decimal('1000.000'),
            'descripcion': 'Lavado de piezas impresas en resina antes del curado; uso con guantes y ventilación.',
            'instrucciones_solicitud': 'Estima unos 150 mL por pieza pequeña; el laboratorista ajusta la cantidad.',
            'ubicacion': 'Gabinete de resinas — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-FEP',
            'nombre': 'Película FEP para tanque de resina',
            'clasificacion': 'material',
            'familia': 'Posprocesado de resina',
            'variante': 'Espesor 0,15 mm',
            'color': '',
            'presentacion': 'Unidad',
            'unidad_medida': 'unidad',
            'stock_total': Decimal('4.000'),
            'precio_unitario': Decimal('12.00'),
            'minimo': Decimal('1.000'),
            'descripcion': 'Repuesto del tanque de la impresora de resina; se solicita solo si el laboratorista lo indica.',
            'instrucciones_solicitud': 'Solicítala únicamente con indicación técnica; normalmente la repone el laboratorio.',
            'ubicacion': 'Gabinete de resinas — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-MDF5',
            'nombre': 'Lámina MDF de 5 mm',
            'clasificacion': 'insumo',
            'familia': 'Materiales planos',
            'variante': 'Espesor 5 mm',
            'color': 'Natural',
            'presentacion': 'Lámina de 60 × 40 cm',
            'unidad_medida': 'lámina',
            'stock_total': Decimal('15.000'),
            'precio_unitario': Decimal('6.80'),
            'minimo': Decimal('4.000'),
            'descripcion': 'MDF de mayor espesor para estructuras, cajas y bases mecanizadas.',
            'instrucciones_solicitud': 'Indica el número de láminas según el anidado o solicita revisión.',
            'imagen_catalogo': 'img/catalogo/fablab/laminas-mdf-3mm.png',
            'ubicacion': 'Rack de materiales planos — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-ACR5',
            'nombre': 'Lámina de acrílico de 5 mm',
            'clasificacion': 'insumo',
            'familia': 'Materiales planos',
            'variante': 'Espesor 5 mm',
            'color': 'Transparente',
            'presentacion': 'Lámina de 60 × 40 cm',
            'unidad_medida': 'lámina',
            'stock_total': Decimal('8.000'),
            'precio_unitario': Decimal('14.50'),
            'minimo': Decimal('2.000'),
            'descripcion': 'Acrílico transparente para corte y grabado láser; no apto para CNC sin autorización.',
            'instrucciones_solicitud': 'Indica el número de láminas según el anidado de piezas.',
            'imagen_catalogo': 'img/catalogo/fablab/laminas-acrilico-3mm.png',
            'ubicacion': 'Rack de materiales planos — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-TRIPLEX3',
            'nombre': 'Lámina de contrachapado de 3 mm',
            'clasificacion': 'insumo',
            'familia': 'Materiales planos',
            'variante': 'Espesor 3 mm',
            'color': 'Natural',
            'presentacion': 'Lámina de 60 × 40 cm',
            'unidad_medida': 'lámina',
            'stock_total': Decimal('12.000'),
            'precio_unitario': Decimal('5.20'),
            'minimo': Decimal('3.000'),
            'descripcion': 'Madera contrachapada para maquetas, engranajes y ensambles por encastre.',
            'instrucciones_solicitud': 'Indica el número de láminas según el anidado o solicita revisión.',
            'imagen_catalogo': 'img/catalogo/fablab/laminas-mdf-3mm.png',
            'ubicacion': 'Rack de materiales planos — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-FRESA',
            'nombre': 'Fresa de corte de 1/8 pulgada, doble filo',
            'clasificacion': 'material',
            'familia': 'Herramientas de corte CNC',
            'variante': 'Doble filo, 1/8"',
            'color': '',
            'presentacion': 'Unidad',
            'unidad_medida': 'unidad',
            'stock_total': Decimal('10.000'),
            'precio_unitario': Decimal('6.50'),
            'minimo': Decimal('3.000'),
            'descripcion': 'Herramienta de desgaste para la fresadora CNC; se registra el consumo por trabajo.',
            'instrucciones_solicitud': 'Normalmente una por trabajo; el laboratorista confirma la herramienta según el material.',
            'ubicacion': 'Gabinete CNC — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-LIJA',
            'nombre': 'Lija de agua grano 220',
            'clasificacion': 'material',
            'familia': 'Acabado y ensamblaje',
            'variante': 'Grano 220',
            'color': '',
            'presentacion': 'Pliego',
            'unidad_medida': 'pliego',
            'stock_total': Decimal('40.000'),
            'precio_unitario': Decimal('0.60'),
            'minimo': Decimal('10.000'),
            'descripcion': 'Lijado fino de piezas impresas, cortadas o mecanizadas.',
            'instrucciones_solicitud': 'Indica el número de pliegos; uso general del laboratorio.',
            'ubicacion': 'Mesa de acabado — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-CIANO',
            'nombre': 'Adhesivo cianoacrilato 20 g',
            'clasificacion': 'insumo',
            'familia': 'Acabado y ensamblaje',
            'variante': '20 g',
            'color': '',
            'presentacion': 'Frasco',
            'unidad_medida': 'unidad',
            'stock_total': Decimal('12.000'),
            'precio_unitario': Decimal('2.80'),
            'minimo': Decimal('3.000'),
            'descripcion': 'Adhesivo instantáneo para ensamblar piezas de PLA, resina y madera.',
            'instrucciones_solicitud': 'Indica los frascos necesarios; uso general del laboratorio.',
            'ubicacion': 'Mesa de acabado — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-GUANTES',
            'nombre': 'Guantes de nitrilo talla M',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Talla M',
            'color': 'Azul',
            'presentacion': 'Par',
            'unidad_medida': 'par',
            'stock_total': Decimal('100.000'),
            'precio_unitario': Decimal('0.35'),
            'minimo': Decimal('20.000'),
            'descripcion': 'Protección para manipular resinas, adhesivos y solventes.',
            'instrucciones_solicitud': 'Indica los pares por participante; uso general del laboratorio.',
            'ubicacion': 'Estación de seguridad — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-VINILO',
            'nombre': 'Vinilo adhesivo brillante 60 cm',
            'clasificacion': 'insumo',
            'familia': 'Vinilos y rotulación',
            'variante': 'Rollo de 60 cm',
            'color': 'Blanco',
            'presentacion': 'Rollo; existencia disponible por metro',
            'unidad_medida': 'm',
            'stock_total': Decimal('30.000'),
            'precio_unitario': Decimal('3.20'),
            'minimo': Decimal('5.000'),
            'descripcion': 'Vinilo adhesivo para rotulación, stickers y plantillas de corte.',
            'instrucciones_solicitud': 'Indica los metros lineales según el diseño anidado.',
            'ubicacion': 'Zona de corte láser — dato de prueba',
        },
        {
            'codigo': 'FAB-CON-ESTANO',
            'nombre': 'Estaño 60/40 de 0,8 mm',
            'clasificacion': 'insumo',
            'familia': 'Electrónica',
            'variante': '60/40, 0,8 mm',
            'color': '',
            'presentacion': 'Carrete de 500 g; existencia disponible por peso',
            'unidad_medida': 'g',
            'stock_total': Decimal('500.000'),
            'precio_unitario': Decimal('0.09'),
            'minimo': Decimal('100.000'),
            'descripcion': 'Estaño con núcleo de flux para soldadura de componentes electrónicos.',
            'instrucciones_solicitud': 'Estima los gramos según el número de uniones; el laboratorista ajusta.',
            'ubicacion': 'Zona de electrónica — dato de prueba',
        },
        {
            'codigo': 'FAB-MAT-PROTO',
            'nombre': 'Protoboard de 830 puntos',
            'clasificacion': 'material',
            'familia': 'Electrónica',
            'variante': '830 puntos',
            'color': 'Blanco',
            'presentacion': 'Unidad',
            'unidad_medida': 'unidad',
            'stock_total': Decimal('15.000'),
            'precio_unitario': Decimal('4.90'),
            'minimo': Decimal('3.000'),
            'descripcion': 'Placa de pruebas sin soldadura para montar circuitos de prototipo.',
            'instrucciones_solicitud': 'Indica las unidades por equipo de trabajo.',
            'ubicacion': 'Zona de electrónica — dato de prueba',
        },
    ]

    # Compatibilidad insumo -> equipos (cantidad sugerida). Un insumo con un
    # solo equipo aparece en la tarjeta de ese equipo; con varios, en el
    # catalogo general; sin equipo es de uso general.
    COMPATIBILIDAD_EQUIPOS = [
        ('FAB-MAT-PETG-NEG', ['FAB-EQ-FDM'], '80'),
        ('FAB-MAT-TPU', ['FAB-EQ-FDM'], '60'),
        ('FAB-MAT-RESINA-TR', ['FAB-EQ-SLA'], '90'),
        ('FAB-CON-IPA', ['FAB-EQ-SLA'], '150'),
        ('FAB-CON-FEP', ['FAB-EQ-SLA'], '1'),
        ('FAB-MAT-MDF5', ['FAB-EQ-LASER', 'FAB-EQ-CNC'], '1'),
        ('FAB-MAT-ACR5', ['FAB-EQ-LASER'], '1'),
        ('FAB-MAT-TRIPLEX3', ['FAB-EQ-LASER', 'FAB-EQ-CNC'], '1'),
        ('FAB-CON-FRESA', ['FAB-EQ-CNC'], '1'),
        ('FAB-MAT-VINILO', ['FAB-EQ-VINIL'], '2'),
        ('FAB-CON-ESTANO', ['FAB-EQ-ELEC'], '25'),
        # Insumos de uso general: tambien se ligan a las estaciones donde se usan.
        ('FAB-CON-CINTA', ['FAB-EQ-FDM', 'FAB-EQ-LASER', 'FAB-EQ-CNC'], '1'),
        ('FAB-CON-LIJA', ['FAB-EQ-FDM', 'FAB-EQ-LASER', 'FAB-EQ-CNC'], '1'),
        ('FAB-CON-CIANO', ['FAB-EQ-FDM', 'FAB-EQ-LASER', 'FAB-EQ-ELEC'], '1'),
        ('FAB-CON-GUANTES', ['FAB-EQ-SLA', 'FAB-EQ-LASER', 'FAB-EQ-CNC', 'FAB-EQ-ELEC'], '2'),
        ('FAB-MAT-PROTO', ['FAB-EQ-ELEC'], '1'),
    ]

    SERVICIOS = [
        {
            'code': 'FAB-SRV-FDM',
            'familia': 'Impresión 3D',
            'nombre': 'Impresión 3D FDM',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/impresora-3d-fdm.png',
            'descripcion': (
                'Preparación, laminado y fabricación de prototipos por deposición '
                'de filamento termoplástico, con revisión de orientación, soportes '
                'y parámetros básicos de impresión.'
            ),
            'resultado_entregado': (
                'Pieza física impresa en 3D con soportes retirados y registro de los '
                'parámetros principales utilizados en la fabricación.'
            ),
            'cuando_elegirlo': (
                'Elígelo para prototipos funcionales, maquetas, carcasas o validaciones '
                'de forma que prioricen rapidez y costo accesible.'
            ),
            'tiempo_estimado_texto': '1 a 3 días laborables, según tamaño y ocupación',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tipo_servicio': 'fabricacion',
            'equipo': 'FAB-EQ-FDM',
            'requiere_archivos': True,
            'requisitos_usuario': 'Indica dimensiones, cantidad de piezas, material y acabado. Si ya tienes el modelo, adjunta STL o 3MF.',
            'formatos_archivo': 'STL, 3MF, OBJ, STEP, PDF o imagen de referencia',
            'tarifa_base': '2.00', 'horas_equipo': '3.00', 'costo_equipo': '3.00',
            'horas_mano_obra': '1.00', 'costo_mano_obra': '4.00',
            'diseno_asistido': '8.00', 'diseno_completo': '20.00',
            'consumibles': [
                ('FAB-MAT-PLA', '120.000', False),
                ('FAB-MAT-PLA-NEG', '120.000', False),
                ('FAB-MAT-PLA-ROJ', '120.000', False),
                ('FAB-MAT-PLA-AZU', '120.000', False),
                ('FAB-MAT-PLA-GRI', '120.000', False),
                ('FAB-CON-CINTA', '1.000', False),
            ],
        },
        {
            'code': 'FAB-SRV-SLA',
            'familia': 'Impresión 3D',
            'nombre': 'Impresión 3D de alta resolución',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/impresora-3d-resina.png',
            'descripcion': (
                'Preparación y fabricación de piezas detalladas mediante resina '
                'fotopolimérica, incluyendo orientación, soportes, lavado y curado.'
            ),
            'resultado_entregado': (
                'Pieza de alta resolución lavada y curada, adecuada para inspección '
                'visual, maquetas de detalle o validación geométrica.'
            ),
            'cuando_elegirlo': (
                'Elígelo cuando necesites detalles finos, superficies más uniformes o '
                'geometrías pequeñas que no se resuelven bien mediante FDM.'
            ),
            'tiempo_estimado_texto': '2 a 4 días laborables, incluido el poscurado',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tipo_servicio': 'fabricacion',
            'equipo': 'FAB-EQ-SLA',
            'requiere_archivos': True,
            'requisitos_usuario': 'Indica dimensiones, nivel de detalle, cantidad y uso final de la pieza.',
            'formatos_archivo': 'STL, 3MF, OBJ, STEP, PDF o imagen de referencia',
            'tarifa_base': '3.00', 'horas_equipo': '3.00', 'costo_equipo': '4.00',
            'horas_mano_obra': '1.50', 'costo_mano_obra': '4.00',
            'diseno_asistido': '8.00', 'diseno_completo': '22.00',
            'consumibles': [('FAB-MAT-RESINA', '150.000', False)],
        },
        {
            'code': 'FAB-SRV-LASER',
            'familia': 'Corte y mecanizado',
            'nombre': 'Corte y grabado láser',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/cortadora-laser.png',
            'descripcion': (
                'Preparación y ejecución supervisada de cortes, marcas o grabados sobre '
                'materiales planos compatibles, con verificación de escala y parámetros.'
            ),
            'resultado_entregado': (
                'Piezas planas cortadas o grabadas según el archivo aprobado y el material '
                'seleccionado, conservando el registro de potencia y velocidad.'
            ),
            'cuando_elegirlo': (
                'Elígelo para maquetas ensamblables, señalética, plantillas, empaques o '
                'grabados que parten de geometría vectorial bidimensional.'
            ),
            'tiempo_estimado_texto': '1 a 2 días laborables tras validar el material',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tipo_servicio': 'fabricacion',
            'equipo': 'FAB-EQ-LASER',
            'requiere_archivos': True,
            'requisitos_usuario': 'Define material, espesor, dimensiones y si necesitas corte, grabado o ambos.',
            'formatos_archivo': 'SVG, DXF, DWG, PDF o archivo vectorial',
            'tarifa_base': '2.00', 'horas_equipo': '1.00', 'costo_equipo': '8.00',
            'horas_mano_obra': '1.00', 'costo_mano_obra': '4.00',
            'diseno_asistido': '6.00', 'diseno_completo': '15.00',
            'consumibles': [('FAB-MAT-MDF3', '1.000', False), ('FAB-MAT-ACR3', '1.000', False)],
        },
        {
            'code': 'FAB-SRV-CNC',
            'familia': 'Corte y mecanizado',
            'nombre': 'Mecanizado CNC para prototipos',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/fresadora-cnc.png',
            'descripcion': (
                'Revisión geométrica, preparación CAM, selección de herramientas y '
                'mecanizado supervisado de piezas de prueba en materiales autorizados.'
            ),
            'resultado_entregado': (
                'Prototipo mecanizado y verificado de forma básica, acompañado por la '
                'referencia del proceso CAM aprobado para su fabricación.'
            ),
            'cuando_elegirlo': (
                'Elígelo para piezas, relieves o componentes que requieren remoción de '
                'material, mayor rigidez o dimensiones controladas.'
            ),
            'tiempo_estimado_texto': '3 a 5 días laborables después de la revisión CAM',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tipo_servicio': 'fabricacion',
            'equipo': 'FAB-EQ-CNC',
            'requiere_archivos': True,
            'requisitos_usuario': 'Indica material, medidas, tolerancias y acabado esperado. Adjunta geometría o plano.',
            'formatos_archivo': 'STEP, STL, DXF, DWG, PDF o ZIP del proyecto CAM',
            'tarifa_base': '5.00', 'horas_equipo': '2.00', 'costo_equipo': '10.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '5.00',
            'diseno_asistido': '10.00', 'diseno_completo': '25.00',
            'consumibles': [('FAB-MAT-MDF3', '1.000', False), ('FAB-CON-CINTA', '0.100', False)],
        },
        {
            'code': 'FAB-SRV-SCAN',
            'familia': 'Digitalización 3D',
            'nombre': 'Escaneo y digitalización 3D',
            'imagen_catalogo': 'img/catalogo/fablab/equipos/escaner-3d.png',
            'descripcion': (
                'Captura supervisada de la geometría de un objeto, limpieza inicial de '
                'datos y generación de una malla digital editable.'
            ),
            'resultado_entregado': (
                'Malla digital limpia en el formato acordado, junto con una copia de la '
                'captura base cuando sea técnicamente viable.'
            ),
            'cuando_elegirlo': (
                'Elígelo para documentación, reproducción, análisis de forma o ingeniería '
                'inversa de objetos físicos que puedan escanearse con seguridad.'
            ),
            'tiempo_estimado_texto': '1 a 3 días laborables según tamaño y superficie',
            'permite_modelo_listo': False,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tipo_servicio': 'uso_equipo',
            'equipo': 'FAB-EQ-SCAN',
            'requiere_archivos': False,
            'requisitos_usuario': 'Describe el objeto, sus dimensiones, superficie y formato de entrega requerido.',
            'formatos_archivo': 'PDF o imágenes de referencia (opcionales)',
            'tarifa_base': '3.00', 'horas_equipo': '1.00', 'costo_equipo': '6.00',
            'horas_mano_obra': '1.00', 'costo_mano_obra': '4.00',
            'diseno_asistido': '5.00', 'diseno_completo': '12.00',
            'consumibles': [],
        },
    ]

    ESPACIOS = [
        {
            'codigo': 'FAB-AREA-IMP3D',
            'nombre': 'Área de impresión 3D',
            'tipo': 'area',
            'ubicacion': 'Zona de fabricación aditiva',
            'capacidad': 6,
            'equipos_asociados': ['FAB-EQ-FDM', 'FAB-EQ-SLA'],
            'mobiliario': 'Mesa de preparación, seis puestos de apoyo, tomas eléctricas y almacenamiento básico.',
            'descripcion': (
                'Zona preparada para impresión FDM y resina, retirada de piezas y '
                'verificación básica de prototipos.'
            ),
            'caracteristicas': (
                'Puestos para impresoras 3D, superficies de preparación y ventilación '
                'controlada para los procesos autorizados.'
            ),
            'instrucciones': (
                'Selecciona esta área si operarás una impresora o trabajarás junto al '
                'responsable durante la preparación y revisión de la pieza.'
            ),
        },
        {
            'codigo': 'FAB-AREA-LASER',
            'nombre': 'Área de corte y grabado láser',
            'tipo': 'area',
            'ubicacion': 'Zona de corte láser',
            'capacidad': 4,
            'equipos_asociados': ['FAB-EQ-LASER', 'FAB-EQ-VINIL'],
            'mobiliario': 'Mesa de preparación, cuatro puestos, extracción fija y superficie para revisión de materiales.',
            'descripcion': (
                'Espacio de preparación, corte y grabado de materiales planos '
                'previamente autorizados.'
            ),
            'caracteristicas': (
                'Cortadora láser, mesa de preparación, extracción localizada y área de '
                'verificación del material.'
            ),
            'instrucciones': (
                'Requiere inducción de seguridad y validación del tipo y espesor del '
                'material antes de utilizar el equipo.'
            ),
        },
        {
            'codigo': 'FAB-AREA-CNC',
            'nombre': 'Área de fresado y mecanizado CNC',
            'tipo': 'area',
            'ubicacion': 'Zona de mecanizado CNC',
            'capacidad': 3,
            'equipos_asociados': ['FAB-EQ-CNC'],
            'mobiliario': 'Banco de trabajo, tres puestos, almacenamiento de herramientas y conexión eléctrica protegida.',
            'descripcion': (
                'Zona controlada para preparar y ejecutar operaciones de fresado de '
                'prototipos en materiales compatibles.'
            ),
            'caracteristicas': (
                'Fresadora CNC de escritorio, sistema de sujeción, aspiración y mesa de '
                'revisión de herramientas.'
            ),
            'instrucciones': (
                'La trayectoria CAM, la herramienta y la fijación deben ser aprobadas '
                'por el responsable técnico.'
            ),
        },
        {
            'codigo': 'FAB-AREA-SCAN3D',
            'nombre': 'Área de digitalización y escaneo 3D',
            'tipo': 'area',
            'ubicacion': 'Zona de digitalización',
            'capacidad': 4,
            'equipos_asociados': ['FAB-EQ-SCAN'],
            'mobiliario': 'Mesa de captura, cuatro puestos, iluminación regulable y fondo neutro.',
            'descripcion': (
                'Espacio para capturar objetos, revisar nubes de puntos y preparar '
                'mallas digitales.'
            ),
            'caracteristicas': (
                'Escáner 3D, base giratoria, iluminación controlable y estación de '
                'procesamiento de mallas.'
            ),
            'instrucciones': (
                'Indica dimensiones, material y acabado del objeto para confirmar que '
                'puede digitalizarse con seguridad.'
            ),
        },
        {
            'codigo': 'FAB-EST-DISENO',
            'nombre': 'Estaciones de diseño y preparación digital',
            'tipo': 'estacion',
            'ubicacion': 'Zona de diseño y preproducción',
            'capacidad': 8,
            'equipos_asociados': ['FAB-EQ-CAD'],
            'mobiliario': 'Ocho puestos con mesa y silla, energía regulada, red institucional y pantalla de apoyo.',
            'descripcion': (
                'Puestos para modelado CAD, laminado, preparación CAM y revisión de '
                'archivos antes de fabricar.'
            ),
            'caracteristicas': (
                'Computadores con software de diseño, laminado y procesamiento de '
                'mallas disponible en el FabLab.'
            ),
            'instrucciones': (
                'Reserva una estación cuando necesites diseñar, corregir o preparar '
                'archivos dentro del laboratorio.'
            ),
        },
        {
            'codigo': 'FAB-SALA-CAP',
            'nombre': 'Sala multipropósito y capacitación',
            'tipo': 'sala',
            'ubicacion': 'Zona de formación y reuniones',
            'capacidad': 20,
            'politica_reserva': 'general',
            'equipos_asociados': [],
            'mobiliario': (
                'Veinte sillas, mesas modulares, pizarra, tomas eléctricas, red '
                'institucional y pantalla de apoyo.'
            ),
            'descripcion': (
                'Sala configurable para reuniones, inducciones, capacitaciones o '
                'trabajo colaborativo que no requiere operar equipos técnicos.'
            ),
            'caracteristicas': (
                'Mobiliario móvil, conectividad y apoyo audiovisual considerado '
                'infraestructura del espacio.'
            ),
            'instrucciones': (
                'Puede reservarse únicamente con su mobiliario. Si necesitas un '
                'equipo técnico adicional, selecciónalo expresamente al iniciar.'
            ),
        },
        {
            'codigo': 'FAB-AREA-ELEC',
            'nombre': 'Área de electrónica y ensamblaje',
            'tipo': 'area',
            'ubicacion': 'Zona de electrónica',
            'capacidad': 6,
            'equipos_asociados': ['FAB-EQ-ELEC'],
            'mobiliario': 'Mesa antiestática, seis puestos, iluminación puntual y extracción de humos de soldadura.',
            'descripcion': (
                'Zona para soldar, ensamblar y probar circuitos de prototipos con '
                'herramientas básicas del laboratorio.'
            ),
            'caracteristicas': (
                'Estación de soldadura, fuente regulada, multímetro y almacenamiento '
                'de componentes de uso común.'
            ),
            'instrucciones': (
                'Trae el esquema y la lista de componentes; el laboratorio provee estaño, '
                'flux y herramientas.'
            ),
        },
    ]

    RESPONSABLES = [
        {
            'nombre': 'Ing. Daniela Andrade',
            'rol': 'coordinacion',
            'email': 'fablab@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2800',
            'foto_referencial': 'img/cards/mentor3.png',
            'descripcion': 'Coordina la agenda, la seguridad y la asignación técnica de las solicitudes del FabLab.',
            'horario_atencion': 'Lunes a viernes · 08:00–17:00',
            'orden': 1,
        },
        {
            'nombre': 'Ing. Carlos Benavides',
            'rol': 'responsable_tecnico',
            'email': 'soporte.fablab@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2800',
            'foto_referencial': 'img/profiles/l-3.jpg',
            'descripcion': 'Brinda acompañamiento en equipos de fabricación digital, software y preparación de archivos.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ]

    SOFTWARE = [
        {
            'codigo': 'FAB-SW-CURA', 'nombre': 'Ultimaker Cura', 'version': '5',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 15,
            'descripcion': 'Laminado y preparación de modelos para impresión 3D FDM.',
            'instrucciones': 'Disponible en los puestos de diseño del FabLab.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
        {
            'codigo': 'FAB-SW-FUSION', 'nombre': 'Autodesk Fusion', 'version': '2026',
            'tipo_recurso': 'licencia', 'tipo_acceso': 'licencia', 'licencias': 20,
            'descripcion': 'Diseño CAD, manufactura CAM y preparación de prototipos.',
            'instrucciones': 'Licencia educativa asignada durante el horario reservado.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
        {
            'codigo': 'FAB-SW-SOLIDWORKS', 'nombre': 'SOLIDWORKS', 'version': '2026',
            'tipo_recurso': 'licencia', 'tipo_acceso': 'red', 'licencias': 10,
            'descripcion': 'Modelado paramétrico y documentación técnica.',
            'instrucciones': 'Acceso concurrente desde la red del laboratorio.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
        {
            'codigo': 'FAB-SW-BLENDER', 'nombre': 'Blender', 'version': '4',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 15,
            'descripcion': 'Modelado, escultura y preparación de mallas 3D.',
            'instrucciones': 'Instalado en los puestos de diseño y digitalización.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
        {
            'codigo': 'FAB-SW-MESHLAB', 'nombre': 'MeshLab', 'version': '2025',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 15,
            'descripcion': 'Limpieza, reparación y conversión de mallas escaneadas.',
            'instrucciones': 'Disponible para prácticas de escaneo y reconstrucción.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
        {
            'codigo': 'FAB-SW-PRUSA', 'nombre': 'PrusaSlicer', 'version': '2.9',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 15,
            'descripcion': 'Laminado alternativo para impresión 3D FDM con perfiles del laboratorio.',
            'instrucciones': 'Programa propio de las impresoras FDM: laminado con los perfiles calibrados del laboratorio; se incluye al reservar la impresora.',
            'equipos_instalados': ['FAB-EQ-FDM'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-CHITUBOX', 'nombre': 'Chitubox', 'version': '2',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 15,
            'descripcion': 'Preparación de soportes y laminado para impresión 3D en resina.',
            'instrucciones': 'Programa propio de la impresora de resina: se incluye al reservarla; los soportes se revisan con el técnico.',
            'equipos_instalados': ['FAB-EQ-SLA'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-LIGHTBURN', 'nombre': 'LightBurn', 'version': '1.7',
            'tipo_recurso': 'licencia', 'tipo_acceso': 'licencia', 'licencias': 3,
            'descripcion': 'Preparación de trayectorias de corte y grabado láser.',
            'instrucciones': 'Programa propio de la cortadora láser: la licencia queda asignada al reservar el equipo.',
            'equipos_instalados': ['FAB-EQ-LASER'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-CANDLE', 'nombre': 'Candle (GRBL)', 'version': '1.2',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 1,
            'descripcion': 'Controlador de la fresadora CNC: envío del código G y control manual de ejes.',
            'instrucciones': 'Programa propio de la fresadora CNC: se incluye al reservarla y lo opera el técnico junto con la persona usuaria.',
            'equipos_instalados': ['FAB-EQ-CNC'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-EXSCAN', 'nombre': 'EXScan Pro', 'version': '4', 'tipo_recurso': 'licencia',
            'tipo_acceso': 'licencia', 'licencias': 1,
            'descripcion': 'Captura, alineación y exportación de mallas del escáner 3D.',
            'instrucciones': 'Programa propio del escáner 3D: la licencia está ligada al equipo y se incluye al reservarlo.',
            'equipos_instalados': ['FAB-EQ-SCAN'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-SILHOUETTE', 'nombre': 'Silhouette Studio', 'version': '4.5',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 1,
            'descripcion': 'Preparación de trazados y envío al plotter de corte de vinilo.',
            'instrucciones': 'Programa propio del plotter de vinilo: se incluye al reservar el equipo.',
            'equipos_instalados': ['FAB-EQ-VINIL'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'FAB-SW-INKSCAPE', 'nombre': 'Inkscape', 'version': '1.4',
            'tipo_recurso': 'software', 'tipo_acceso': 'red', 'licencias': 30,
            'descripcion': 'Edición vectorial para corte láser, plotter y rotulación; disponible en todos los puestos.',
            'instrucciones': 'Instalado en las computadoras de diseño; úsalo para preparar vectores antes de cortar o rotular.',
            'equipos_instalados': ['FAB-EQ-CAD'],
        },
    ]

    # Ficha de cada insumo tal como la ve la persona usuaria (marca, presentacion,
    # caracteristicas). Proveedor, ubicacion, lotes y umbrales son de la gestion.
    FICHA_INSUMOS = {
        'FAB-MAT-PLA': {'marca': 'eSUN', 'especificacion_tecnica': 'PLA+ de 1,75 mm ± 0,03 mm; temperatura de boquilla 205-225 °C; cama 60 °C; densidad 1,24 g/cm³.', 'proveedor_referencia': 'Distribuidor nacional de filamentos'},
        'FAB-MAT-PLA-NEG': {'marca': 'eSUN', 'especificacion_tecnica': 'PLA+ de 1,75 mm ± 0,03 mm; boquilla 205-225 °C; cama 60 °C.', 'proveedor_referencia': 'Distribuidor nacional de filamentos'},
        'FAB-MAT-PLA-ROJ': {'marca': 'eSUN', 'especificacion_tecnica': 'PLA+ de 1,75 mm ± 0,03 mm; boquilla 205-225 °C; cama 60 °C.', 'proveedor_referencia': 'Distribuidor nacional de filamentos'},
        'FAB-MAT-PLA-AZU': {'marca': 'eSUN', 'especificacion_tecnica': 'PLA+ de 1,75 mm ± 0,03 mm; boquilla 205-225 °C; cama 60 °C.', 'proveedor_referencia': 'Distribuidor nacional de filamentos'},
        'FAB-MAT-PLA-GRI': {'marca': 'eSUN', 'especificacion_tecnica': 'PLA+ de 1,75 mm ± 0,03 mm; boquilla 205-225 °C; cama 60 °C.', 'proveedor_referencia': 'Distribuidor nacional de filamentos'},
        'FAB-MAT-PETG-NEG': {'marca': 'Prusament', 'especificacion_tecnica': 'PETG de 1,75 mm ± 0,02 mm; boquilla 230-250 °C; cama 85 °C; resistente a impacto y humedad.', 'proveedor_referencia': 'Importador autorizado'},
        'FAB-MAT-TPU': {'marca': 'NinjaTek', 'especificacion_tecnica': 'TPU 95A flexible de 1,75 mm; boquilla 225-235 °C; velocidad máxima 30 mm/s.', 'proveedor_referencia': 'Importador autorizado'},
        'FAB-MAT-RESINA': {'marca': 'Elegoo', 'especificacion_tecnica': 'Resina estándar 405 nm, viscosidad 150-200 mPa·s, exposición 2-3 s por capa de 50 µm.', 'proveedor_referencia': 'Distribuidor de impresión 3D'},
        'FAB-MAT-RESINA-TR': {'marca': 'Elegoo', 'especificacion_tecnica': 'Resina transparente 405 nm; requiere poscurado de 5 min para mayor claridad.', 'proveedor_referencia': 'Distribuidor de impresión 3D'},
        'FAB-CON-IPA': {'marca': 'Grado técnico', 'especificacion_tecnica': 'Alcohol isopropílico al 99 % para lavado de piezas de resina; usar con guantes y ventilación.', 'proveedor_referencia': 'Proveedor químico local'},
        'FAB-CON-FEP': {'marca': 'Elegoo', 'especificacion_tecnica': 'Película FEP de 0,15 mm, 200 × 140 mm, para tanques de impresoras LCD.', 'proveedor_referencia': 'Distribuidor de impresión 3D'},
        'FAB-MAT-MDF3': {'marca': 'Masisa', 'especificacion_tecnica': 'Tablero MDF de 3 mm, 600 × 400 mm, apto para corte y grabado láser.', 'proveedor_referencia': 'Maderera local'},
        'FAB-MAT-MDF5': {'marca': 'Masisa', 'especificacion_tecnica': 'Tablero MDF de 5 mm, 600 × 400 mm, apto para corte láser y fresado CNC.', 'proveedor_referencia': 'Maderera local'},
        'FAB-MAT-ACR3': {'marca': 'Plexiglas', 'especificacion_tecnica': 'Acrílico colado transparente de 3 mm, 600 × 400 mm; corte láser limpio sin llama.', 'proveedor_referencia': 'Distribuidor de plásticos'},
        'FAB-MAT-ACR5': {'marca': 'Plexiglas', 'especificacion_tecnica': 'Acrílico colado transparente de 5 mm, 600 × 400 mm.', 'proveedor_referencia': 'Distribuidor de plásticos'},
        'FAB-MAT-TRIPLEX3': {'marca': 'Arauco', 'especificacion_tecnica': 'Contrachapado de 3 mm, 600 × 400 mm, cara lijada.', 'proveedor_referencia': 'Maderera local'},
        'FAB-CON-CINTA': {'marca': '3M', 'especificacion_tecnica': 'Cinta de enmascarar de 24 mm × 40 m, adhesión media.', 'proveedor_referencia': 'Ferretería'},
        'FAB-CON-FRESA': {'marca': 'Amana Tool', 'especificacion_tecnica': 'Fresa de carburo de 1/8", doble filo, corte ascendente, longitud de corte 12 mm.', 'proveedor_referencia': 'Importador de herramientas'},
        'FAB-CON-LIJA': {'marca': '3M', 'especificacion_tecnica': 'Lija de agua grano 220, pliego de 230 × 280 mm.', 'proveedor_referencia': 'Ferretería'},
        'FAB-CON-CIANO': {'marca': 'Loctite', 'especificacion_tecnica': 'Adhesivo cianoacrilato de 20 g, fraguado en 10-30 s.', 'proveedor_referencia': 'Ferretería'},
        'FAB-CON-GUANTES': {'marca': 'Ambiderm', 'especificacion_tecnica': 'Guantes de nitrilo sin polvo, talla M, caja de 100 unidades.', 'proveedor_referencia': 'Distribuidor de seguridad industrial'},
        'FAB-MAT-VINILO': {'marca': 'Oracal 651', 'especificacion_tecnica': 'Vinilo adhesivo brillante de 60 cm de ancho, 70 µm, duración exterior 6 años.', 'proveedor_referencia': 'Distribuidor de rotulación'},
        'FAB-CON-ESTANO': {'marca': 'Kester', 'especificacion_tecnica': 'Estaño 60/40 con núcleo de resina, 0,8 mm de diámetro.', 'proveedor_referencia': 'Distribuidor de electrónica'},
        'FAB-MAT-PROTO': {'marca': 'Elegoo', 'especificacion_tecnica': 'Protoboard de 830 puntos con rieles de alimentación.', 'proveedor_referencia': 'Distribuidor de electrónica'},
    }

    # Reservas de ejemplo en el periodo, una por caso que puede darse en la
    # cascada: software propio obligatorio, software opcional y adicional,
    # insumos ligados y transversales, sala sin equipo, docencia con guia,
    # solicitud rechazada y cancelada.
    RESERVAS_EJEMPLO = [
        {
            'titulo': 'Investigación · impresión SLA de piezas microfluídicas',
            'fecha': date(2026, 9, 10), 'horas': [10, 11], 'estado': 'pendiente',
            'proposito_codigo': 'investigacion_innovacion', 'subtipo_actividad': 'proyecto_investigacion',
            'tipo_uso': 'experimentacion', 'equipo': 'FAB-EQ-SLA', 'espacios': ['FAB-AREA-IMP3D'],
            'software': ['FAB-SW-CHITUBOX'], 'consumibles': [('FAB-MAT-RESINA', '250')],
            'participantes': 2,
            'descripcion': 'Caso: equipo con programa propio (Chitubox incluido) e insumo ligado al equipo.',
        },
        {
            'titulo': 'Capacitación · corte láser de señalética interna',
            'fecha': date(2026, 9, 11), 'horas': [14, 15], 'estado': 'confirmada',
            'proposito_codigo': 'capacitacion', 'subtipo_actividad': 'entrenamiento_tecnico',
            'tipo_uso': 'capacitacion', 'equipo': 'FAB-EQ-LASER', 'espacios': ['FAB-AREA-LASER'],
            'software': ['FAB-SW-LIGHTBURN', 'FAB-SW-INKSCAPE'], 'consumibles': [('FAB-MAT-MDF5', '2')],
            'participantes': 6,
            'descripcion': 'Caso: programa propio (LightBurn) más software de uso general (Inkscape) y material transversal.',
        },
        {
            'titulo': 'Vinculación · fresado CNC de molde para artesanos',
            'fecha': date(2026, 9, 15), 'horas': [8, 9, 10], 'estado': 'confirmada',
            'proposito_codigo': 'vinculacion', 'subtipo_actividad': 'proyecto_vinculacion',
            'tipo_uso': 'produccion', 'equipo': 'FAB-EQ-CNC', 'espacios': ['FAB-AREA-CNC'],
            'software': ['FAB-SW-CANDLE'], 'consumibles': [('FAB-MAT-MDF5', '1')],
            'participantes': 3,
            'descripcion': 'Caso: equipo operado con el técnico y su controlador propio (Candle).',
        },
        {
            'titulo': 'Titulación · rotulado en vinilo del prototipo',
            'fecha': date(2026, 9, 17), 'horas': [15, 16], 'estado': 'pendiente',
            'proposito_codigo': 'titulacion', 'subtipo_actividad': 'trabajo_titulacion',
            'tipo_uso': 'experimentacion', 'equipo': 'FAB-EQ-VINIL', 'espacios': ['FAB-AREA-LASER'],
            'software': ['FAB-SW-SILHOUETTE'], 'consumibles': [('FAB-MAT-VINILO', '1.5')],
            'participantes': 1,
            'descripcion': 'Caso: plotter con programa propio e insumo por metro.',
        },
        {
            'titulo': 'Docencia · clase demostrativa de soldadura de componentes',
            'fecha': date(2026, 9, 18), 'horas': [9, 10], 'estado': 'confirmada',
            'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'simulacion_demostracion',
            'tipo_uso': 'practica', 'equipo': 'FAB-EQ-ELEC', 'espacios': ['FAB-AREA-ELEC'],
            'software': [], 'consumibles': [('FAB-MAT-PROTO', '4')],
            'participantes': 8, 'docente_con_actividad': True,
            'descripcion': 'Caso: docencia con guía aprobada, equipo sin software e insumo ligado.',
        },
        {
            'titulo': 'Investigación · modelado CAD con programa adicional',
            'fecha': date(2026, 9, 22), 'horas': [10, 11], 'estado': 'pendiente',
            'proposito_codigo': 'investigacion_innovacion', 'subtipo_actividad': 'investigacion_formativa',
            'tipo_uso': 'experimentacion', 'equipo': 'FAB-EQ-CAD', 'unidad_posicion': 1,
            'espacios': ['FAB-EST-DISENO'], 'software': ['FAB-SW-FUSION'], 'consumibles': [],
            'participantes': 2,
            'requisitos_especiales': 'Instalación o configuración de software · Software adicional por habilitar: otro: Estación de diseño CAD: KiCad 8',
            'descripcion': 'Caso: computadora con programas opcionales (Fusion marcado) y pedido de instalar KiCad.',
        },
        {
            'titulo': 'Reunión · revisión de avances de proyectos de aula',
            'fecha': date(2026, 9, 23), 'horas': [11, 12], 'estado': 'confirmada',
            'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'proyecto_asignatura',
            'tipo_uso': 'practica', 'equipo': None, 'espacios': ['FAB-SALA-CAP'],
            'software': [], 'consumibles': [], 'participantes': 12, 'docente_con_actividad': True,
            'descripcion': 'Caso: sala de uso general reservada sola, con su mobiliario.',
        },
        {
            'titulo': 'Investigación · impresión FDM en PETG (rechazada)',
            'fecha': date(2026, 9, 24), 'horas': [16, 17], 'estado': 'rechazada',
            'proposito_codigo': 'investigacion_innovacion', 'subtipo_actividad': 'proyecto_investigacion',
            'tipo_uso': 'experimentacion', 'equipo': 'FAB-EQ-FDM', 'espacios': ['FAB-AREA-IMP3D'],
            'software': ['FAB-SW-PRUSA'], 'consumibles': [('FAB-MAT-PETG-NEG', '300')],
            'participantes': 1,
            'observaciones_validacion': 'La impresora FDM-01 estará en calibración ese día; reprogramar.',
            'descripcion': 'Caso: solicitud rechazada por el laboratorio; no ocupa agenda.',
        },
        {
            'titulo': 'Titulación · pruebas de flexibilidad en TPU (cancelada)',
            'fecha': date(2026, 9, 25), 'horas': [8, 9], 'estado': 'cancelada',
            'proposito_codigo': 'titulacion', 'subtipo_actividad': 'trabajo_titulacion',
            'tipo_uso': 'experimentacion', 'equipo': 'FAB-EQ-FDM', 'espacios': ['FAB-AREA-IMP3D'],
            'software': ['FAB-SW-PRUSA'], 'consumibles': [('FAB-MAT-TPU', '200')],
            'participantes': 1,
            'descripcion': 'Caso: cancelada por la persona solicitante; libera la agenda.',
        },
    ]

    ACTIVIDADES_INSTITUCIONALES = [
        {
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'nombre': 'Práctica curricular de fabricación digital',
            'codigo': 'FAB-DOC-001',
            'periodo_academico': '2026-B',
            'responsable': 'Docente responsable de la asignatura',
        },
        {
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'innovacion_prototipado',
            'nombre': 'Proyecto de innovación y prototipado digital',
            'codigo': 'FAB-IDI-001',
            'responsable': 'Dirección del proyecto de investigación',
        },
        {
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'nombre': 'Taller de fabricación digital con la comunidad',
            'codigo': 'FAB-VIN-001',
            'responsable': 'Responsable del proyecto de vinculación',
        },
        {
            'proposito_codigo': 'capacitacion',
            'subtipo_actividad': 'curso',
            'nombre': 'Curso de introducción a la fabricación digital',
            'codigo': 'FAB-CAP-001',
            'responsable': 'Coordinación técnica FabLab',
        },
        {
            'proposito_codigo': 'titulacion',
            'subtipo_actividad': 'trabajo_titulacion',
            'nombre': 'Desarrollo experimental para trabajo de titulación',
            'codigo': 'FAB-TIT-001',
            'responsable': 'Tutor del trabajo de titulación',
        },
    ]

    def add_arguments(self, parser):
        self.agregar_argumentos_datos_demo(parser)

    @transaction.atomic
    @comando_reservas
    def handle(self, *args, **options):
        slug = self.validar_opciones_datos_demo(options)
        try:
            unidad = Unidad.objects.select_for_update(of=('self',)).get(slug=slug)
        except Unidad.DoesNotExist as exc:
            raise CommandError(f'No existe una unidad con slug "{slug}".') from exc

        unidad.recorrido_espacios_youtube_url = (
            'https://www.youtube.com/watch?v=Vcxz9ss2MAs'
        )
        unidad.recorrido_360_ruta = 'img/360/lacteos1/index.html'
        unidad.capacidad_personas = unidad.capacidad_personas or 24
        unidad.save(update_fields=[
            'recorrido_espacios_youtube_url',
            'recorrido_360_ruta',
            'capacidad_personas',
        ])

        equipos = {}
        unidades_equipo = {}
        for orden, datos in enumerate(self.EQUIPOS, start=1):
            categoria, _ = CategoriaEquipo.objects.update_or_create(
                codigo=datos['categoria_codigo'],
                defaults={
                    'nombre': datos['categoria'],
                    'descripcion': 'Categoría demostrativa para pruebas de reserva FabLab.',
                    'icono': datos['icono'],
                    'color': '#2f6f57',
                    'activa': True,
                    'orden': orden,
                },
            )
            equipo, _ = actualizar_o_crear(
                modelo_vigente, EquiposServicios, 'codigo', datos['codigo'],
                {
                    'nombre': datos['nombre'],
                    'descripcion': datos['descripcion'],
                    'imagen_catalogo': datos.get('imagen_catalogo', ''),
                    'caracteristicas_publicas': datos['caracteristicas_publicas'],
                    'uso_publico': datos['uso_publico'],
                    'instrucciones_publicas': datos['instrucciones_publicas'],
                    'marca': datos.get('marca', 'Demostración'),
                    'modelo': datos.get('modelo', 'Registro de prueba'),
                    'estado': 'disponible',
                    'software': datos['software'],
                    'admite_software_adicional': datos.get('admite_software_adicional', False),
                    'rol': datos.get('rol', 'principal'),
                    'cantidad': len(datos.get('unidades') or [datos['codigo_unidad']]),
                    'accesorios_incluidos': datos['accesorios'],
                    'accesorios_opcionales': [],
                },
            )
            equipo.categorias.set([categoria])
            # Varias unidades fisicas del mismo equipo comparten catalogo, software
            # instalado y area; el asistente las muestra en una sola tarjeta.
            for posicion, codigo_unidad in enumerate(datos.get('unidades') or [datos['codigo_unidad']], start=1):
                unidad_equipo, _ = actualizar_o_crear(
                    unidad_vigente, UnidadEquipo, 'codigo_unidad', codigo_unidad,
                    {
                        'equipo': equipo,
                        'laboratorio': unidad,
                        'estado_unidad': 'disponible',
                        'numero_serie': f'DEMO-{orden:03d}-{posicion}',
                        'observaciones': 'Registro demostrativo para pruebas de reserva.',
                        'requiere_insumos': datos['requiere_insumos'],
                        'insumos_necesarios': datos['insumos'] or None,
                        'ubicacion_especifica': datos['ubicacion'],
                        'activa': True,
                    },
                )
                unidad_equipo.laboratorios.set([unidad])
                unidades_equipo.setdefault(datos['codigo'], []).append(unidad_equipo)
            equipos[datos['codigo']] = equipo
        # Los auxiliares se enlazan cuando ya existen todos los principales.
        for datos in self.EQUIPOS:
            if datos.get('rol') == 'auxiliar':
                equipos[datos['codigo']].apoya_a.set(
                    [equipos[codigo] for codigo in datos.get('apoya_a', [])]
                )

        consumibles = {}
        for datos in self.CONSUMIBLES:
            ficha = self.FICHA_INSUMOS.get(datos['codigo'], {})
            consumible, _ = Consumible.objects.update_or_create(
                codigo=datos['codigo'],
                defaults={
                    'unidad': unidad,
                    'nombre': datos['nombre'],
                    'marca': datos.get('marca', ficha.get('marca', '')),
                    'especificacion_tecnica': datos.get('especificacion_tecnica', ficha.get('especificacion_tecnica', '')),
                    'proveedor_referencia': datos.get('proveedor_referencia', ficha.get('proveedor_referencia', '')),
                    'clasificacion': datos['clasificacion'],
                    'familia': datos.get('familia', ''),
                    'variante': datos.get('variante', ''),
                    'color': datos.get('color', ''),
                    'presentacion': datos.get('presentacion', ''),
                    'cantidad_por_presentacion': datos.get(
                        'cantidad_por_presentacion',
                        Decimal('1000')
                        if datos['unidad_medida'] in {'g', 'mL'}
                        else Decimal('1'),
                    ),
                    'unidad_medida': datos['unidad_medida'],
                    'descripcion': datos['descripcion'],
                    'instrucciones_solicitud': datos.get('instrucciones_solicitud', ''),
                    'imagen_catalogo': datos.get('imagen_catalogo', ''),
                    'stock_total': datos['stock_total'],
                    'minimo': datos['minimo'],
                    # Coherentes con la regla del inventario (seguridad <= minimo <= objetivo)
                    # aunque un escenario anterior haya movido estos umbrales.
                    'stock_seguridad': (datos['minimo'] / 2).quantize(Decimal('0.001')),
                    'stock_objetivo': max(datos['stock_total'], datos['minimo']),
                    'precio_unitario': datos.get('precio_unitario'),
                    'ubicacion': datos['ubicacion'],
                    'visible_en_reservas': True,
                    'activo': True,
                },
            )
            consumibles[datos['codigo']] = consumible

        for codigo_consumible, codigos_equipo, cantidad in self.COMPATIBILIDAD_EQUIPOS:
            consumible = consumibles[codigo_consumible]
            for codigo_equipo in codigos_equipo:
                ConsumiblePorEquipo.objects.update_or_create(
                    consumible=consumible,
                    equipo=equipos[codigo_equipo],
                    defaults={
                        'cantidad': Decimal(cantidad),
                        'minimo_alerta': consumible.minimo,
                        'ubicacion': consumible.ubicacion,
                    },
                )

        Consumible.objects.filter(
            unidad=unidad,
            codigo='EQ00234',
            nombre='Rollo PLA',
        ).update(
            activo=False,
            visible_en_reservas=False,
            descripcion='Registro demostrativo anterior, reemplazado por variantes de PLA por color y peso.',
        )

        for datos in self.SERVICIOS:
            servicio, _ = FablabService.objects.update_or_create(
                code=datos['code'],
                defaults={
                    'nombre': datos['nombre'],
                    'descripcion': datos['descripcion'],
                    'imagen_catalogo': datos.get('imagen_catalogo', ''),
                    'resultado_entregado': datos.get('resultado_entregado', ''),
                    'cuando_elegirlo': datos.get('cuando_elegirlo', ''),
                    'tiempo_estimado_texto': datos.get('tiempo_estimado_texto', ''),
                    # Los tutoriales son dos guías genéricas por unidad y se
                    # configuran en Configuración operativa, no por servicio.
                    'tutorial_titulo': '',
                    'tutorial_youtube_url': '',
                    'permite_modelo_listo': datos.get('permite_modelo_listo', True),
                    'permite_diseno_asistido': datos.get(
                        'permite_diseno_asistido', True
                    ),
                    'permite_diseno_completo': datos.get(
                        'permite_diseno_completo', True
                    ),
                    'unidad': unidad,
                    'tipo_servicio': datos['tipo_servicio'],
                    'familia': datos.get('familia', ''),
                    'activo': True,
                    'publico': True,
                    'requiere_reserva': True,
                    'requiere_revision_tecnica': True,
                    'requiere_cotizacion': True,
                    'requiere_archivos': datos.get('requiere_archivos', False),
                    'requisitos_usuario': datos.get('requisitos_usuario', ''),
                    'formatos_archivo': datos.get('formatos_archivo', ''),
                    'tarifa_base': Decimal(datos.get('tarifa_base', '0')),
                    'horas_equipo_estimadas': Decimal(datos.get('horas_equipo', '0')),
                    'costo_hora_equipo': Decimal(datos.get('costo_equipo', '0')),
                    'horas_mano_obra_estimadas': Decimal(datos.get('horas_mano_obra', '0')),
                    'costo_hora_mano_obra': Decimal(datos.get('costo_mano_obra', '0')),
                    'costo_diseno_asistido': Decimal(datos.get('diseno_asistido', '0')),
                    'costo_diseno_completo': Decimal(datos.get('diseno_completo', '0')),
                    'descuento_estudiante': Decimal('40'),
                    'descuento_personal': Decimal('25'),
                    'descuento_externo': Decimal('0'),
                },
            )
            for codigo_consumible, cantidad, obligatorio in datos['consumibles']:
                consumible = consumibles[codigo_consumible]
                FablabServiceConsumible.objects.update_or_create(
                    service=servicio,
                    consumible=consumible,
                    defaults={
                        'cantidad_sugerida': Decimal(cantidad),
                        'obligatorio': obligatorio,
                        'notas': 'Cantidad orientativa para una prueba; debe validarla el responsable.',
                    },
                )
                ConsumiblePorEquipo.objects.update_or_create(
                    consumible=consumible,
                    equipo=equipos[datos['equipo']],
                    defaults={
                        'cantidad': cantidad,
                        'minimo_alerta': consumible.minimo,
                        'ubicacion': consumible.ubicacion,
                    },
                )

        for datos in self.SOFTWARE:
            programa, _ = SoftwareDisponible.objects.update_or_create(
                unidad=unidad,
                nombre=datos['nombre'],
                defaults={
                    'codigo': datos['codigo'],
                    'version': datos['version'],
                    'descripcion': datos['descripcion'],
                    'tipo_recurso': datos['tipo_recurso'],
                    'tipo_acceso': datos['tipo_acceso'],
                    'licencias_totales': datos['licencias'],
                    'licencias_disponibles': datos['licencias'],
                    'requiere_reserva': True,
                    'instrucciones_acceso': datos['instrucciones'],
                    'uso_en_equipo': datos.get('uso_en_equipo', 'opcional'),
                    'activo': True,
                },
            )
            programa.equipos_instalados.set([
                unidad_equipo
                for codigo in datos.get('equipos_instalados', [])
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ])

        espacios, integradas = {}, []
        for orden, datos in enumerate(self.ESPACIOS, start=1):
            vieja = integrada(unidad, datos['codigo'])
            if vieja is not None:
                # El área se fusionó en otra: no se reactiva; sus equipos y reservas van a la que la integró.
                espacios[datos['codigo']] = area_vigente(vieja)
                integradas.append((espacios[datos['codigo']], datos))
                continue
            espacio, _ = EspacioReservable.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'nombre': datos['nombre'],
                    'tipo': datos['tipo'],
                    'descripcion_publica': datos['descripcion'],
                    'ubicacion': datos['ubicacion'],
                    'capacidad': datos['capacidad'],
                    'mobiliario_incluido': datos.get('mobiliario', ''),
                    'politica_reserva': datos.get(
                        'politica_reserva',
                        'tecnico' if datos.get('equipos_asociados') else 'general',
                    ),
                    'caracteristicas': datos['caracteristicas'],
                    'instrucciones_uso': datos['instrucciones'],
                    'activo': True,
                    'reservable': True,
                    'orden': orden,
                },
            )
            # Los equipos que el área recibió de su ficha (incluidos los de un área que se le integró) se conservan.
            de_su_ficha = espacio.equipos_asociados.filter(
                equipo__unidades__elementos_de_ficha__ficha__espacio=espacio,
            ).distinct()
            espacio.equipos_asociados.set([
                unidad_equipo
                for codigo in datos.get('equipos_asociados', [])
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ] + list(de_su_ficha))
            espacios[datos['codigo']] = espacio
        for vigente, datos in integradas:
            vigente.equipos_asociados.add(*[
                unidad_equipo
                for codigo in datos.get('equipos_asociados', [])
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ])

        for datos in self.RESPONSABLES:
            ResponsableUnidad.objects.update_or_create(
                unidad=unidad,
                email=datos['email'],
                defaults={
                    'nombre': datos['nombre'],
                    'rol': datos['rol'],
                    'telefono': datos['telefono'],
                    'foto_referencial': datos.get('foto_referencial', ''),
                    'descripcion': datos.get('descripcion', ''),
                    'horario_atencion': datos.get('horario_atencion', ''),
                    'publico': True,
                    'recibe_reservas': False,
                    'permisos_operativos': {},
                    'activo': True,
                    'orden': datos['orden'],
                },
            )

        periodo_demo, _ = PeriodoAcademico.objects.update_or_create(
            codigo='2026-B',
            defaults={
                'nombre': 'Período académico ordinario 2026-B',
                'anio_referencia': 2026,
                'ciclo': 'B',
                'tipo': 'ordinario',
                'ambito': 'carreras_centros',
                'semanas_planificadas': 16,
                'estado': 'borrador',
                'observaciones': (
                    'Período demostrativo completo para probar reservas, '
                    'recurrencias semanales e indicadores. No corresponde a '
                    'una resolución académica oficial.'
                ),
            },
        )
        version_demo, _ = VersionCalendarioAcademico.objects.update_or_create(
            periodo=periodo_demo,
            numero=1,
            defaults={
                'nombre': 'Calendario inicial de pruebas 2026-B',
                'fecha_inicio_clases': date(2026, 8, 17),
                'fecha_fin_clases': date(2026, 12, 6),
                'fecha_fin_periodo': date(2026, 12, 8),
                'fecha_publicacion': date(2026, 8, 10),
                'resolucion': 'UPEC-DEMO-2026-B',
                'fuente_url': 'https://www.upec.edu.ec/',
                'motivo_reforma': (
                    'Versión inicial demostrativa para validación funcional; '
                    'sin valor de resolución oficial.'
                ),
                'vigente': True,
            },
        )
        for numero in range(1, periodo_demo.semanas_planificadas + 1):
            inicio_semana = version_demo.fecha_inicio_clases + timedelta(
                days=(numero - 1) * 7
            )
            SemanaAcademica.objects.update_or_create(
                version_calendario=version_demo,
                numero=numero,
                defaults={
                    'fecha_inicio': inicio_semana,
                    'fecha_fin': min(
                        inicio_semana + timedelta(days=6),
                        version_demo.fecha_fin_clases,
                    ),
                    'tipo': 'clases',
                    'parcial': 1 if numero <= 8 else 2,
                    'reportable': True,
                    'permite_reservas': True,
                    'observaciones': (
                        f'Semana {numero} de clases del período demostrativo 2026-B.'
                    ),
                },
            )
        periodo_demo.estado = 'publicado'
        periodo_demo.full_clean()
        periodo_demo.save(update_fields=['estado', 'actualizado_en'])

        for orden, datos in enumerate(self.ACTIVIDADES_INSTITUCIONALES, start=1):
            CatalogoActividadReserva.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'proposito_codigo': datos['proposito_codigo'],
                    'subtipo_actividad': datos['subtipo_actividad'],
                    'nombre': datos['nombre'],
                    'periodo': periodo_demo,
                    'periodo_academico': periodo_demo.codigo,
                    'responsable': datos['responsable'],
                    'activo': True,
                    'orden': orden,
                },
            )

        # Escenario integral de agenda, concurrencia y capacidad para pruebas.
        User = get_user_model()
        docente, creado = User.objects.get_or_create(
            username='docente.demo.fablab',
            defaults={
                'first_name': 'María Elena',
                'last_name': 'Guerrero',
                'email': 'maria.guerrero.demo@upec.edu.ec',
                'is_active': True,
            },
        )
        if creado:
            docente.set_unusable_password()
            docente.save(update_fields=['password'])
        UserProfile.objects.update_or_create(
            user=docente,
            defaults={
                'tipo_usuario': 'docente',
                'facultad': 'agropecuarias_ambientales',
                'carrera': 'docente',
                'nivel_academico': 'docente',
                'institucion': 'Universidad Politécnica Estatal del Carchi',
                'cargo': 'Docente responsable de práctica',
            },
        )

        estudiantes = []
        for index, (nombre, apellido) in enumerate((
            ('Ana', 'Mora'), ('Luis', 'Enríquez'), ('Sofía', 'Ruano')
        ), start=1):
            usuario, creado = User.objects.get_or_create(
                username=f'estudiante.demo.fablab{index}',
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'email': f'estudiante.demo.fablab{index}@upec.edu.ec',
                    'is_active': True,
                },
            )
            if creado:
                usuario.set_unusable_password()
                usuario.save(update_fields=['password'])
            UserProfile.objects.update_or_create(
                user=usuario,
                defaults={
                    'tipo_usuario': 'estudiante',
                    'facultad': 'agropecuarias_ambientales',
                    'carrera': 'computacion',
                    'nivel_academico': 'sexto_semestre',
                    'cedula': f'DEMO-2026-{index:03d}',
                    'institucion': 'Universidad Politécnica Estatal del Carchi',
                },
            )
            estudiantes.append(usuario)

        CapacidadOperativaUnidad.objects.update_or_create(
            unidad=unidad,
            vigente_desde=date(2026, 8, 17),
            defaults={
                'periodo': periodo_demo,
                'vigente_hasta': date(2026, 12, 8),
                'aforo_seguridad': 24,
                'puestos_mobiliario': 20,
                'puestos_equipados': 12,
                'capacidad_personal': 16,
                'fuente': 'Escenario demostrativo: inspección, inventario y disponibilidad de personal',
                'observaciones': 'Capacidad efectiva: 12 puestos, limitada por estaciones equipadas.',
                'activo': True,
                'creado_por': docente,
            },
        )

        cierre, _ = BloqueoAgendaUnidad.objects.update_or_create(
            unidad=unidad,
            titulo='Cierre institucional demostrativo',
            fecha_inicio=date(2026, 9, 3),
            defaults={
                'tipo': 'feriado',
                'motivo': 'Ejemplo visible de feriado o suspensión: bloquea toda la jornada y todos los recursos.',
                'fecha_fin': date(2026, 9, 3),
                'dia_completo': True,
                'hora_inicio': None,
                'hora_fin': None,
                'alcance': 'unidad_completa',
                'bloquea_recursos': True,
                'bloquea_servicios': True,
                'visible_en_agenda': True,
                'activo': True,
                'creado_por': docente,
            },
        )
        mantenimiento, _ = BloqueoAgendaUnidad.objects.update_or_create(
            unidad=unidad,
            titulo='Mantenimiento de cortadora láser',
            fecha_inicio=date(2026, 9, 2),
            defaults={
                'tipo': 'mantenimiento',
                'motivo': 'Limpieza de óptica y verificación del sistema de extracción. El resto del laboratorio permanece disponible.',
                'fecha_fin': date(2026, 9, 2),
                'dia_completo': False,
                'hora_inicio': time(11, 0),
                'hora_fin': time(13, 0),
                'alcance': 'equipos',
                'bloquea_recursos': True,
                'bloquea_servicios': False,
                'visible_en_agenda': True,
                'activo': True,
                'creado_por': docente,
            },
        )
        mantenimiento.equipos.set(unidades_equipo['FAB-EQ-LASER'])

        actividad_docente = CatalogoActividadReserva.objects.get(
            unidad=unidad,
            codigo='FAB-DOC-001',
        )
        programacion, _ = ProgramacionReserva.objects.update_or_create(
            laboratorio=unidad,
            solicitante=docente,
            actividad=actividad_docente,
            frecuencia='semanal_periodo',
            fecha_inicio=date(2026, 8, 17),
            defaults={
                'periodo': periodo_demo,
                'fecha_fin': date(2026, 12, 8),
                'dia_semana': 0,
                'hora_inicio': time(9, 0),
                'hora_fin': time(11, 0),
                'horas_seleccionadas': [9, 10],
                'fechas_omitidas': [],
                'total_sesiones': 16,
                'estado': 'activa',
            },
        )
        session_date = date(2026, 8, 17)
        while session_date <= date(2026, 12, 8):
            semana = periodo_demo.semana_para_fecha(session_date)
            reserva, _ = Reserva.objects.update_or_create(
                programacion=programacion,
                fecha=session_date,
                defaults={
                    'laboratorio': unidad,
                    'actividad_catalogo': actividad_docente,
                    'usuario': docente,
                    'tipo_solicitud': 'recursos',
                    'incluye_espacio': True,
                    'solicito_espacio': True,
                    'solicito_equipo': False,
                    'solicito_software': False,
                    'alcance_espacio': 'unidad_completa',
                    'hora_inicio': time(9, 0),
                    'hora_fin': time(11, 0),
                    'horas_seleccionadas': '[9, 10]',
                    'duracion': 2,
                    'equipo_codigo': 'UNIDAD-COMPLETA',
                    'equipo_nombre': 'Laboratorio completo',
                    'unidades_seleccionadas': '[]',
                    'nombre_solicitante': docente.get_full_name(),
                    'correo_solicitante': docente.email,
                    'tipo_usuario_solicitante': 'docente',
                    'facultad_solicitante': 'agropecuarias_ambientales',
                    'carrera_solicitante': 'docente',
                    'nivel_academico_solicitante': 'docente',
                    'tipo_uso': 'practica',
                    'proposito': 'Práctica curricular semanal durante todo el período.',
                    'proposito_codigo': 'docencia_practica',
                    'subtipo_actividad': 'practica_curricular',
                    'alcance_beneficiario': 'perfil_solicitante',
                    'vinculacion_actividad': 'catalogo',
                    'referencia_actividad': actividad_docente.nombre,
                    'periodo_academico': periodo_demo.codigo,
                    'periodo': periodo_demo,
                    'version_calendario': version_demo,
                    'semana_academica': semana,
                    'semana_academica_numero': semana.numero if semana else None,
                    'responsable_actividad': docente.get_full_name(),
                    'origen_programacion': 'programada',
                    'descripcion_proyecto': 'Sesión demostrativa recurrente con ocupación de la unidad completa.',
                    'titulo_solicitud': 'Docencia · Diseño y fabricación digital · período completo',
                    'numero_participantes': 4,
                    'estado': 'confirmada',
                },
            )
            reserva.participantes.set(estudiantes)
            RegistroParticipanteReserva.objects.update_or_create(
                reserva=reserva,
                usuario=docente,
                defaults={
                    'rol': 'solicitante', 'nombre': docente.get_full_name(),
                    'correo': docente.email, 'tipo_usuario': 'docente',
                    'facultad': 'agropecuarias_ambientales', 'carrera': 'docente',
                    'nivel_academico': 'docente', 'institucion': 'UPEC',
                },
            )
            for estudiante in estudiantes:
                RegistroParticipanteReserva.objects.update_or_create(
                    reserva=reserva,
                    usuario=estudiante,
                    defaults={
                        'rol': 'participante', 'nombre': estudiante.get_full_name(),
                        'correo': estudiante.email, 'tipo_usuario': 'estudiante',
                        'facultad': 'agropecuarias_ambientales', 'carrera': 'computacion',
                        'nivel_academico': 'sexto_semestre', 'institucion': 'UPEC',
                    },
                )
            session_date += timedelta(days=7)

        # Dos usos simultáneos parciales: recursos diferentes, por tanto compatibles.
        Reserva.objects.filter(
            laboratorio=unidad,
            fecha=date(2026, 9, 1),
            titulo_solicitud='Vinculación · piezas de señalética',
        ).delete()
        partial_examples = (
            ('Investigación · prototipo FDM', 'investigacion_innovacion', 'proyecto_investigacion', 'FAB-EQ-FDM', 'FAB-AREA-IMP3D'),
            ('Titulación · validación de pieza CAD', 'titulacion', 'trabajo_titulacion', 'FAB-EQ-LASER', 'FAB-AREA-LASER'),
        )
        for title, purpose, subtype, equipment_code, space_code in partial_examples:
            equipment_unit = unidades_equipo[equipment_code][0]
            reservation, _ = Reserva.objects.update_or_create(
                laboratorio=unidad,
                fecha=date(2026, 9, 1),
                titulo_solicitud=title,
                defaults={
                    'usuario': docente,
                    'tipo_solicitud': 'recursos',
                    'incluye_espacio': True,
                    'solicito_espacio': True,
                    'solicito_equipo': True,
                    'alcance_espacio': 'areas',
                    'hora_inicio': time(15, 0), 'hora_fin': time(17, 0),
                    'horas_seleccionadas': '[15, 16]', 'duracion': 2,
                    'equipo_codigo': equipment_unit.codigo_unidad,
                    'equipo_nombre': equipment_unit.equipo.nombre,
                    'unidades_seleccionadas': f'[{{"id": {equipment_unit.pk}, "codigo": "{equipment_unit.codigo_unidad}"}}]',
                    'nombre_solicitante': docente.get_full_name(),
                    'correo_solicitante': docente.email,
                    'tipo_usuario_solicitante': 'docente',
                    'tipo_uso': 'experimentacion',
                    'proposito': title,
                    'proposito_codigo': purpose,
                    'subtipo_actividad': subtype,
                    'vinculacion_actividad': 'manual',
                    'referencia_actividad': title,
                    'periodo_academico': periodo_demo.codigo,
                    'periodo': periodo_demo,
                    'version_calendario': version_demo,
                    'numero_participantes': 2,
                    'descripcion_proyecto': 'Ejemplo de ocupación parcial compatible con otros recursos.',
                    'estado': 'confirmada',
                },
            )
            reservation.espacios_solicitados.set([espacios[space_code]])

        self._crear_reservas_ejemplo(
            unidad, docente, estudiantes, unidades_equipo, espacios, periodo_demo, version_demo,
            actividad_docente,
        )

        self.finalizar_simulacion_datos_demo(options)
        prefijo = self.prefijo_simulacion_datos_demo(options)
        self.stdout.write(self.style.SUCCESS(
            f'{prefijo}Datos FabLab listos en "{unidad.nombre}": '
            f'{len(self.EQUIPOS)} equipos, {len(self.SERVICIOS)} servicios y '
            f'{len(self.CONSUMIBLES)} insumos/materiales, '
            f'{len(self.SOFTWARE)} recursos de software, '
            f'{len(self.ESPACIOS)} espacios y '
            f'{len(self.RESPONSABLES)} responsables, y '
            f'{len(self.ACTIVIDADES_INSTITUCIONALES)} actividades institucionales, '
            f'16 sesiones docentes, 2 reservas parciales, {len(self.RESERVAS_EJEMPLO)} reservas '
            'de ejemplo, 2 bloqueos y 1 capacidad histórica.'
        ))

    def _crear_reservas_ejemplo(
        self, unidad, docente, estudiantes, unidades_equipo, espacios, periodo, version,
        actividad_docente,
    ):
        """Una reserva por caso de la cascada, con sus espacios, software e insumos."""
        for datos in self.RESERVAS_EJEMPLO:
            equipment_unit = None
            if datos['equipo']:
                equipment_unit = unidades_equipo[datos['equipo']][datos.get('unidad_posicion', 0)]
            horas = datos['horas']
            es_docencia = datos.get('docente_con_actividad', False)
            defaults = {
                'usuario': docente,
                'tipo_solicitud': 'recursos',
                'incluye_espacio': True,
                'solicito_espacio': True,
                'solicito_equipo': equipment_unit is not None,
                'solicito_software': bool(datos['software']),
                'alcance_espacio': 'areas',
                'hora_inicio': time(horas[0], 0),
                'hora_fin': time(horas[-1] + 1, 0),
                'horas_seleccionadas': str(horas),
                'duracion': len(horas),
                'equipo_codigo': equipment_unit.codigo_unidad if equipment_unit else 'ESPACIO',
                'equipo_nombre': equipment_unit.equipo.nombre if equipment_unit else 'Espacio',
                'unidades_seleccionadas': (
                    f'[{{"id": {equipment_unit.pk}, "codigo": "{equipment_unit.codigo_unidad}", '
                    f'"nombre": "{equipment_unit.equipo.nombre}"}}]'
                    if equipment_unit else '[]'
                ),
                'nombre_solicitante': docente.get_full_name(),
                'correo_solicitante': docente.email,
                'tipo_usuario_solicitante': 'docente',
                'facultad_solicitante': 'agropecuarias_ambientales',
                'carrera_solicitante': 'docente',
                'nivel_academico_solicitante': 'docente',
                'tipo_uso': datos['tipo_uso'],
                'proposito': datos['titulo'],
                'proposito_codigo': datos['proposito_codigo'],
                'subtipo_actividad': datos['subtipo_actividad'],
                'alcance_beneficiario': 'perfil_solicitante',
                'vinculacion_actividad': 'catalogo' if es_docencia else 'manual',
                'actividad_catalogo': actividad_docente if es_docencia else None,
                'referencia_actividad': actividad_docente.nombre if es_docencia else datos['titulo'],
                'periodo_academico': periodo.codigo,
                'periodo': periodo,
                'version_calendario': version,
                'responsable_actividad': docente.get_full_name(),
                'origen_programacion': 'adicional',
                'numero_participantes': datos['participantes'],
                'provision_consumibles': 'unidad' if datos['consumibles'] else 'ninguno',
                'requisitos_especiales': datos.get('requisitos_especiales', 'Sin requisitos adicionales'),
                'observaciones_validacion': datos.get('observaciones_validacion', ''),
                'descripcion_proyecto': datos['descripcion'],
                'estado': datos['estado'],
            }
            reserva, _ = Reserva.objects.update_or_create(
                laboratorio=unidad,
                fecha=datos['fecha'],
                titulo_solicitud=datos['titulo'],
                defaults=defaults,
            )
            reserva.espacios_solicitados.set([espacios[codigo] for codigo in datos['espacios']])
            reserva.software_solicitado.set(
                SoftwareDisponible.objects.filter(unidad=unidad, codigo__in=datos['software'])
            )
            reserva.participantes.set(estudiantes[:max(0, datos['participantes'] - 1)])
            reserva.consumibles_solicitados.exclude(
                consumible__codigo__in=[codigo for codigo, _ in datos['consumibles']]
            ).delete()
            for codigo, cantidad in datos['consumibles']:
                ReservaConsumible.objects.update_or_create(
                    reserva=reserva,
                    consumible=Consumible.objects.get(unidad=unidad, codigo=codigo),
                    defaults={
                        'cantidad_solicitada': Decimal(cantidad),
                        'metodo_estimacion': 'estimacion',
                    },
                )
