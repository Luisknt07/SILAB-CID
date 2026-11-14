"""Revisión FabLab 2026: datos declarados y referencias técnicas, sin stock supuesto.

Los máximos del fabricante no constituyen productividad ni tolerancia de pieza.
Las ampliaciones son opciones que deben contrastarse con demanda e infraestructura.
"""

SLUG = 'laboratorio-fabricacion-digital-prototipado'
FECHA_REVISION = '2026-10-21'
FUENTE = 'Revisión técnica FabLab 2026; dotación propuesta, no recepción patrimonial.'
X1_FUENTE = 'https://public-cdn.bambulab.com/store/bambulab-X1-carbon-tech-specs.pdf'
H2C_FUENTE = 'https://csm.bblcdn.com/hub/eff78da43720461787dc8bbe5fa0372d.pdf'
H2D_FUENTE = 'https://csm.bblcdn.com/hub/4668d0ca43994ff3bff4b37f1a65c2e7.pdf'
MEGA_FUENTE = 'https://drive.google.com/file/d/13hGH6_5x4iELyqkURTVaChUewx2xc3V2/view'

DECLARADOS = (
    dict(clave='h2c', marca='Bambu Lab', modelo='H2C', cantidad=4,
         nombre='Impresora 3D FDM multimaterial H2C', fuente=H2C_FUENTE,
         especificaciones={
             'Tecnología': 'FDM; sistema multimaterial Vortek',
             'Volumen nominal combinado': '330 × 320 × 325 mm; no es el volumen común de ambas boquillas',
             'Cabezal izquierdo': '325 × 320 × 320 mm; X de 0 a 325 mm',
             'Cabezal derecho': '305 × 320 × 325 mm; X de 25 a 330 mm',
             'Zona común de dos cabezales': '300 × 320 mm en XY; altura común 320 mm',
             'Temperaturas máximas': 'Boquilla 350 °C; cama 120 °C; cámara 65 °C',
             'Diámetro de filamento': '1,75 mm',
             'Restricción de materiales': 'TPU 95A HF: sólo cabezal derecho, sin AMS. PET-CF/PPA-CF/PPS-CF: sólo izquierdo, sin AMS; revisar tabla del manual.',
             'Validación del trabajo': 'Revisar volumen efectivo, perfil, secado y cabezal en Bambu Studio antes de autorizar la pieza.',
         }, cuidados=('Inspeccionar placa, boquillas, alimentadores y limpieza antes de cada trabajo.',
                     'Revisar manual de la variante y compatibilidad AMS; no asumir que incluye láser ni corte.',
                     'Registrar horas, material utilizado, cambio de boquilla y resultado de la pieza.'),
         repuestos=('Hotend y boquillas compatibles H2C', 'Limpiadores y cortadores de filamento', 'Placa de impresión compatible')),
    dict(clave='h2d', marca='Bambu Lab', modelo='H2D', cantidad=4,
         nombre='Impresora 3D FDM de doble extrusión H2D', fuente=H2D_FUENTE,
         especificaciones={
             'Tecnología': 'FDM de doble boquilla',
             'Volumen nominal combinado': '350 × 320 × 325 mm; no es utilizable completo por ambas boquillas',
             'Cabezal izquierdo': 'X de 0 a 325 mm; Y de 0 a 320 mm; altura máxima 320 mm',
             'Cabezal derecho': 'X de 25 a 350 mm; Y de 0 a 320 mm; altura máxima 325 mm',
             'Zona común de dos cabezales': '300 × 320 mm en XY; altura común 320 mm',
             'Temperaturas máximas': 'Boquilla 350 °C; cama 120 °C; cámara 65 °C',
             'Diámetro de filamento': '1,75 mm',
             'Material flexible': 'TPU sólo cabezal derecho; TPU 95A o inferior no se alimenta con AMS 2 Pro.',
             'Accesorios': 'Confirmar variante y módulos recibidos; la impresora declarada no acredita módulo láser instalado.',
             'Validación del trabajo': 'Comprobar volumen útil por boquilla y perfil de material en el laminador.',
         }, cuidados=('Mantener limpia la placa y revisar alineación de boquillas según el manual.',
                     'Respetar las restricciones de alimentación y el secado del material.',
                     'Registrar horas, incidencias, piezas fallidas y repuestos cambiados.'),
         repuestos=('Hotend y boquillas compatibles H2D', 'Limpiadores y cortadores de filamento', 'Placa de impresión compatible')),
    dict(clave='mega-s', marca='Anycubic', modelo='i3 Mega S', cantidad=4,
         nombre='Impresora 3D FDM abierta i3 Mega S', fuente=MEGA_FUENTE,
         especificaciones={
             'Tecnología': 'FDM de estructura abierta',
             'Volumen nominal': '210 × 210 × 205 mm',
             'Temperatura máxima de boquilla': '260 °C según manual; no equivale a autorizar cualquier material',
             'Temperatura máxima de cama': '110 °C según manual',
             'Diámetro de filamento': '1,75 mm',
             'Preparación del trabajo': 'Perfil específico de Mega S en UltiMaker Cura; revisar nivelación y primera capa.',
             'Uso recomendado': 'Docencia y prototipado en PLA/PETG con perfil validado; no deducir desgaste por antigüedad.',
         }, cuidados=('Verificar nivelación, cama, cableado y protección de elementos calientes.',
                     'Revisar correas, ruedas y extrusor según manual y registrar las intervenciones.',
                     'No trasladar automáticamente perfiles ni velocidades de las Bambu Lab.'),
         repuestos=('Boquilla compatible Mega S', 'Hotend y termistor compatibles Mega S', 'Correas y superficie de impresión compatibles')),
)

X1_ESPECIFICACIONES = {
    'Tecnología': 'FDM CoreXY', 'Volumen nominal': '256 × 256 × 256 mm',
    'Temperatura máxima de boquilla': '300 °C',
    'Temperatura máxima de cama': '110 °C a 220 V; 120 °C a 110 V',
    'Boquilla incluida': '0,4 mm, acero endurecido', 'Diámetro de filamento': '1,75 mm',
    'Velocidad máxima de movimiento': '500 mm/s; no es una tasa garantizada de fabricación',
    'Software': 'Bambu Studio; verificar perfil y material',
    'Límites efectivos': 'Bambu Studio puede reservar zonas de cama y limitar altura a 250 mm; validar la pieza en el perfil oficial.',
    'Código de modelo del fabricante': 'PF001-P (declaración UE de X1-Carbon)',
}

# La compatibilidad inicial se limita a materias y perfiles comunes. No supone
# stock, compra, licencia instalada ni habilitación operativa del activo.
MATERIALES_COMUNES = ('Filamento PLA', 'Filamento PETG')
SOFTWARE = (
    dict(nombre='Bambu Studio', url='https://bambulab.com/en/download/studio',
         licencia='Código abierto; revisar licencia del repositorio y conectores antes del despliegue institucional.',
         modelos=('h2c', 'h2d', 'x1'), uso='Preparar y verificar impresiones con el perfil exacto del modelo.'),
    dict(nombre='UltiMaker Cura', url='https://ultimaker.com/software/ultimaker-cura/',
         licencia='Código abierto; instalación y perfil deben ser validados por el responsable.',
         modelos=('mega-s',), uso='Preparar G-code específico para Anycubic i3 Mega S.'),
)

MATERIALES = (
    ('FAB-AREA-IMP3D', 'material', 'Repuestos FDM', 'Boquilla compatible H2C', 'unidad', 'Referencia de repuesto; confirmar diámetro, material y cabezal.', ('h2c',)),
    ('FAB-AREA-IMP3D', 'material', 'Repuestos FDM', 'Boquilla compatible H2D', 'unidad', 'Referencia de repuesto; confirmar variante y cabezal.', ('h2d',)),
    ('FAB-AREA-IMP3D', 'material', 'Repuestos FDM', 'Boquilla compatible i3 Mega S', 'unidad', 'Referencia de repuesto; comprobar rosca, longitud y diámetro.', ('mega-s',)),
    ('FAB-AREA-IMP3D', 'insumo', 'Filamentos técnicos', 'Filamento PA seco 1,75 mm', 'g', 'Propuesta: validar polímero, perfil, secado y ruta de alimentación antes de enlazar compatibilidad.', ()),
    ('FAB-AREA-IMP3D', 'insumo', 'Filamentos técnicos', 'Filamento de soporte compatible 1,75 mm', 'g', 'Seleccionar soporte según polímero principal y compatibilidad del sistema; no mezclar perfiles genéricos.', ()),
    ('FAB-AREA-LASER', 'material', 'Extracción y filtración', 'Filtro de extracción específico del equipo', 'unidad', 'Validar modelo, caudal y criterio de sustitución; un filtro genérico no acredita control de emisiones.', ()),
    ('FAB-AREA-VINILO', 'insumo', 'Impresión DTF', 'Tinta DTF compatible con el modelo instalado', 'mL', 'Confirmar cabezal, sistema de tinta, lote, vencimiento y SDS. No intercambiar con tinta UV.', ()),
    ('FAB-AREA-VINILO', 'insumo', 'Impresión DTF', 'Película de transferencia DTF', 'm', 'Confirmar ancho, cara de impresión y compatibilidad del proceso.', ()),
    ('FAB-AREA-VINILO', 'insumo', 'Impresión DTF', 'Polvo adhesivo para transferencia DTF', 'g', 'Confirmar formulación, almacenamiento, SDS y extracción del curado.', ()),
    ('FAB-AREA-VINILO', 'insumo', 'Impresión UV', 'Tinta UV compatible con el modelo instalado', 'mL', 'Confirmar composición, cabezal, lote, vencimiento y SDS antes de recibir.', ()),
    ('FAB-AREA-VINILO', 'limpieza', 'Impresión UV', 'Limpiador compatible con el circuito de tinta UV', 'mL', 'Validar SDS y compatibilidad del fabricante; no sustituir por solvente genérico.', ()),
    ('FAB-AREA-CNC', 'material', 'Herramientas de mecanizado', 'Fresa de corte con geometría especificada', 'unidad', 'Definir diámetro, número de filos, material, portaherramienta y parámetros para la máquina concreta.', ()),
    ('FAB-AREA-SCAN3D', 'material', 'Escaneo y metrología', 'Marcadores de escaneo compatibles', 'unidad', 'Validar diámetro, adhesión y sistema de seguimiento; no acreditan exactitud por sí solos.', ()),
    ('FAB-AREA-SCAN3D', 'material', 'Escaneo y metrología', 'Patrón dimensional de referencia', 'unidad', 'Seleccionar rango e incertidumbre con metrología antes de comprar; registrar certificado y verificación.', ()),
    ('FAB-AREA-ELEC', 'insumo', 'Ensamble electrónico', 'Pasta de soldadura con formulación especificada', 'g', 'Confirmar aleación, tamaño de partícula, perfil térmico, SDS, lote y condiciones de conservación.', ()),
    ('FAB-AREA-ELEC', 'material', 'Protección ESD', 'Pulsera y superficie de trabajo ESD verificables', 'unidad', 'Comprobar sistema de puesta a tierra y procedimiento; no dar por instalada la protección.', ()),
    ('FAB-AREA-ACABADOS', 'insumo', 'Moldeo', 'Silicona de moldeo con ficha de mezcla', 'g', 'Registrar compatibilidad, proporción, vida de mezcla, curado y SDS.', ()),
    ('FAB-ALMACEN', 'material', 'Trazabilidad', 'Etiquetas de identificación de lotes', 'unidad', 'Seleccionar soporte y adhesivo acordes al envase y almacenamiento; el código enlaza el kardex.', ()),
)

# Equipos descritos en los documentos aportados: no hay actas ni cantidades
# por máquina. Sólo se completa un modelo ya identificado en el inventario.
CATALOGOS_APORTADOS = (
    ('FAB-IMP3D-05', 'HALOT-MAGE S 14K', '6_3 CATALOGO DE BIENES-signed.pdf',
     '223 × 126 × 230 mm nominales; resolución de pantalla y tamaño de píxel no son tolerancia de pieza.',
     'https://store.creality.com/products/halot-mage-s-14k-resin-3d-printer'),
    ('FAB-IMP3D-02', 'HALOT-MAGE S 14K', '6_3 CATALOGO DE BIENES-signed.pdf',
     'El registro comparte modelo con otra ficha; conciliar por número de serie antes de sumar capacidad.',
     'https://store.creality.com/products/halot-mage-s-14k-resin-3d-printer'),
    ('FAB-ACABADOS-07', 'UW-03', '6_3 CATALOGO DE BIENES-signed.pdf',
     'Lavado y curado auxiliar de resina. Verificar recipientes, solvente admitido y enclavamientos en manual.',
     'https://store.creality.com/products/uw-03-washing-curing-machine'),
    ('FAB-LASER-09', 'Falcon2 Pro', '6_3 CATALOGO DE BIENES-signed.pdf',
     'El documento solicita variante 60 W; confirmar módulo recibido y placa antes de registrar potencia instalada.',
     'https://www.crealityfalcon.com/products/falcon2-pro-60w'),
    ('FAB-IMP3D-06', 'Space Pi', '6_3 CATALOGO DE BIENES-signed.pdf',
     'Secado auxiliar. El catálogo describe 45–70 °C; confirmar variante y temperaturas admisibles de cada bobina.',
     'https://store.creality.com/products/creality-space-pi-filament-dryer'),
    ('FAB-ELEC-09', 'AD409 Pro', '6_2 CATALOGO DE BIENES-signed.pdf',
     'Microscopio digital con pantalla de 10,1 pulgadas y endoscopio según catálogo. Verificar variante Pro y software recibido.',
     'https://andonstar.com/product/ad409-pro-hdmi-digital-microscope-10-1-inch-lcd-screen/'),
    ('FAB-ELEC-10', 'T-962', '6_2 CATALOGO DE BIENES-signed.pdf',
     'El catálogo mezcla bandejas mínimas y máximas: medir área real y caracterizar perfil térmico; no prometer 300 × 320 mm.', ''),
    ('FAB-DISENO-08', 'HP Z8 Fury G5', '6_2 CATALOGO DE BIENES-signed.pdf',
     'Configuración ofertada: Xeon w5-3425, 256 GB DDR5, SSD 4 TB y RTX A4000 16 GB. Verificar configuración por activo; no extender a otros PC.',
     'https://www.hp.com/us-en/workstations/z8-fury.html'),
    ('FAB-LASER-07', 'Láser de fibra JPT', '6_2 CATALOGO DE BIENES-signed.pdf',
     'El catálogo indica 50 W y contiene longitud de onda «1064 µm». El registro HM-60WJPT difiere: verificar placa, unidad y fuente antes de fijar potencia o protección.', ''),
    ('FAB-LASER-10', 'UV 60 × 90', '6_2 CATALOGO DE BIENES-signed.pdf',
     'Modelo y RIP por confirmar. Tintas, limpiadores, lámparas y sustratos requieren compatibilidad específica y SDS; no extrapolar materiales al láser.', ''),
    ('FAB-LASER-11', 'DTF A3 Plus XP600', '6_2 CATALOGO DE BIENES-signed.pdf',
     'El catálogo mezcla parámetros de impresora fotográfica y línea DTF. Confirmar cabezal, agitador/secador, RIP, ancho y alimentación reales.', ''),
    ('FAB-SCAN3D-01', 'Creality Raptor Pro', '6_2 CATALOGO DE BIENES P1 (1).pdf',
     'El catálogo menciona Raptor Pro. El registro CRS07R requiere validar variante; no mezclar resolución, precisión local e incertidumbre volumétrica.',
     'https://www.creality.com/support/creality-raptor-pro'),
    ('FAB-DISENO-07', 'Meta Quest 3', '6_3 CATALOGO DE BIENES-signed.pdf',
     'Confirmar almacenamiento, accesorios, usuarios y licencias recibidas. El catálogo no acredita acceso abierto ni todas las aplicaciones.',
     'https://www.meta.com/quest/quest-3/'),
)

# No son mínimos universales ni órdenes de compra. Cada referencia expone una
# capacidad, una alternativa y las condiciones para evaluarla.
PROPUESTAS = (
    ('FAB-AREA-IMP3D', 'Reciclaje y extrusión de filamento con control de diámetro', 'alta',
     'Investigar recuperación de material limpio y trazable. Primero medir residuos y ensayar calidad; no alimentar mezclas sin caracterización.',
     'https://www.preciousplastic.com/machines/basic', 'Medir masa recuperable, composición, humedad, diámetro y propiedades de probetas; extruir reciclado no garantiza filamento imprimible.'),
    ('FAB-AREA-IMP3D', 'Impresión 3D de gran formato por pellet', 'alta',
     'Fabricar utillajes y prototipos grandes cuando la envolvente actual y el ensamblaje por partes resulten insuficientes.',
     'https://fablabbcn.org/', 'Comparar demanda anual con servicios externos, ventilación, potencia, espacio y costo por pieza.'),
    ('FAB-AREA-IMP3D', 'Secado y almacenamiento con medición de humedad', 'basico',
     'Verificar que los secadores y armarios existentes cubran el material y el número real de máquinas; evitar comprar auxiliares repetidos.',
     H2C_FUENTE, 'Contrastar secadores actuales, temperaturas por polímero, uso simultáneo y registro de humedad.'),
    ('FAB-AREA-CNC', 'Sujeción modular y medición de herramienta para CNC', 'basico',
     'Completar la capacidad de los routers y fresadoras existentes antes de ampliar el parque.',
     'https://fab.cba.mit.edu/about/fab/inv.html', 'Comprobar máquina, control, pinzas, herramientas, extracción, resguardos y formación antes de operar.'),
    ('FAB-AREA-CNC', 'Mecanizado de precisión y fabricación metálica especializada', 'alta',
     'Comparar mecanizado interno, acceso compartido y contratación externa para tolerancias o materiales no cubiertos.',
     'https://studios.aalto.fi/fablab/', 'Requiere demanda y tolerancias medibles; el precio o la novedad de la tecnología no justifican por sí solos la adquisición.'),
    ('FAB-AREA-LASER', 'Verificación de extracción e interbloqueos láser', 'basico',
     'Diagnosticar extracción y protecciones de CO2, diodo y fibra por separado; priorizar capacidad segura ya instalada.',
     'https://support.epiloglaser.com/laser-machine/fibermark/usage-and-operation/faq/material-safety-and-your-laser/', 'Verificar variante, clasificación real con cerramiento, longitudes de onda, materiales autorizados y manual específico.'),
    ('FAB-AREA-VINILO', 'Cadena de impresión textil y curado con extracción', 'basico',
     'Revisar impresoras DTF/UV, prensas, consumibles, perfiles y extracción como un proceso completo.',
     'https://fablabbcn.org/', 'Confirmar modelo, RIP/licencias y fichas de seguridad de tintas y polvo; no confundir impresión UV con autorización para corte láser de PVC.'),
    ('FAB-AREA-ACABADOS', 'Moldeo y vacío con gestión de mezclas', 'basico',
     'Contrastar cámara de vacío, balanza y termoformado existentes con los trabajos solicitados.',
     'https://fab.cba.mit.edu/about/fab/inv.html', 'Validar volumen, compatibilidad química, moldes, extracción y tratamiento de residuos antes de ampliar.'),
    ('FAB-AREA-SCAN3D', 'Calibración y patrones dimensionales trazables', 'basico',
     'Sustentar tolerancias de escaneo y piezas fabricadas con patrones y procedimientos; resolver primero equipos sin identificación.',
     'https://studios.aalto.fi/fablab/', 'Revisar certificados y presupuesto de incertidumbre; resolución de escáner y altura de capa no equivalen a exactitud de pieza.'),
    ('FAB-AREA-SCAN3D', 'Fotogrametría y digitalización por imagen', 'alta',
     'Complementar el escáner con cámaras y estaciones de trabajo existentes cuando textura o escala lo justifiquen.',
     'https://alicevision.org/', 'Ensayar iluminación, escala, GPU, formatos de salida y comparación con mediciones de referencia.'),
    ('FAB-AREA-ELEC', 'Instrumentación de validación y protección ESD', 'basico',
     'Revisar osciloscopios, fuentes, multímetros y microscopio existentes; completar accesorios, patrones y protección antes de duplicar equipos.',
     'https://fab.cba.mit.edu/about/fab/inv.html', 'Medir necesidades por grupo y simultaneidad; comprobar calibración, puntas, sondas y consumibles de soldadura.'),
    ('FAB-AREA-ELEC', 'Ensamble de PCB y trazabilidad de perfiles térmicos', 'alta',
     'Integrar fresado PCB, microscopio y horno existentes con inspección y registro; comparar el pick-and-place compartido antes de comprar.',
     'https://studios.aalto.fi/fablab/', 'Caracterizar perfiles con el hardware real y controlar extracción, ESD, pasta, almacenamiento y retrabajo.'),
    ('FAB-EST-DISENO', 'Simulación y diseño generativo con validación física', 'alta',
     'Evaluar herramientas CAD/CAE y modelos generativos como apoyo; las geometrías requieren validación técnica y ensayo.',
     'https://fablabbcn.org/', 'Comprobar licencias educativas y restricciones de uso comercial, hardware y competencia del equipo humano.'),
    ('FAB-EST-DISENO', 'Gemelo digital y documentación versionada de fabricación', 'alta',
     'Relacionar diseño, versiones, parámetros, mediciones y resultados mediante recursos existentes antes de añadir infraestructura.',
     'https://fablabbcn.org/', 'Definir formatos abiertos, control de versiones, respaldo, permisos y protección de datos de proyectos.'),
    ('FAB-AREA-ROBOTICA', 'Fabricación robotizada y sensorización de procesos', 'alta',
     'Evaluar junto al laboratorio de Robótica el uso del equipamiento hospedado, evitando duplicar la capacidad de otra unidad.',
     'https://fablabbcn.org/', 'Primero establecer custodia, acceso compartido, integración y seguridad de celda; ampliar sólo con proyectos respaldados.'),
    ('FAB-ALMACEN', 'Trazabilidad de materiales y almacenamiento segregado', 'basico',
     'Completar lotes, fichas de seguridad, ubicación y compatibilidad de materiales sin inventar cantidades.',
     'https://rules.fablabbcn.org/', 'Separar filamentos, resinas, solventes, tintas y residuos; contrastar almacenamiento existente y consumo por semestre.'),
    ('FAB-SALA-CAP', 'Formación y habilitación por proceso', 'basico',
     'Organizar inducción, competencias, tutoriales y proyectos antes del uso autónomo de cada familia de equipos.',
     'https://fabfoundation.org/getting-started/', 'Definir responsables, autorización, aforo, supervisión y evidencias; una reserva no acredita competencia técnica.'),
)
