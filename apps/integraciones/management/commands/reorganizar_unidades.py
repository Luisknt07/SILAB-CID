"""Pasa al sistema la reforma de laboratorios: nombres oficiales, áreas y unidades que se integran.

Deja las unidades como las definió la reforma: 18 laboratorios, 5 plantas piloto, el
Centro Experimental San Francisco y 3 observatorios, cada uno con su nombre largo y su
nombre corto, su área de conocimiento, sus carreras titulares y usuarias, su resolución,
su ubicación, sus áreas internas reservables (las «futuras» quedan inactivas hasta tener
equipo) y el responsable que consta en el inventario. Toda unidad queda con su slug
definitivo (las sembradas con «-prueba» lo cambian y las plantas toman el de su nombre
oficial). Las unidades que la reforma integra en otra le pasan sus equipos y espacios y se
eliminan; solo se desactivan las que tienen historial y la reforma no mandó borrar. No crea
los tres laboratorios propuestos: esperan su acto de creación.

Se puede repetir: encuentra cada unidad por su slug actual o por el anterior y completa lo
que falte sin duplicar áreas ni responsables. Con --simular muestra lo que haría y no
guarda nada.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.fusion_areas import fusionar_area
from apps.plantas_piloto.operacion.presentation.secciones_plantas import PESTANA_INVESTIGACION, mapa_de
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS as AREAS_LOGISTICA, DESCRIPCION as DESCRIPCION_LOGISTICA, DESCRIPCION_CORTA as LEMA_LOGISTICA, NOMBRE as NOMBRE_LOGISTICA, NOMBRE_CORTO as CORTO_LOGISTICA
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import TipoLaboratorio, Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.models.recursos import DEFAULT_MODULES_BY_DEPENDENCIA

FUTURA = {'futura': True}
DESCRIPCION_DE_FUTURA = 'Se crea cuando tenga equipo.'
TIPOS = {'D': 'Docencia', 'I': 'Investigación', 'S': 'Servicios'}
POLITICA_POR_TIPO = {
    'area': 'tecnico', 'estacion': 'tecnico', 'sala': 'general', 'cabina': 'mixto', 'puesto': 'general',
    'camara': 'general', 'otro': 'general', 'parcela': 'mixto', 'invernadero': 'mixto', 'establo': 'mixto',
}

# Qué abarca cada área: se muestra en su descripción pública mientras la unidad no escriba la suya.
ALCANCE_DE_AREAS = {
    'FAB-AREA-IMP3D': 'Impresión 3D de filamento y resina, materiales técnicos, posprocesado y acabados',
    'FAB-AREA-LASER': 'Corte y grabado láser, fresado CNC, PCB y corte de vinilo',
    'FAB-EST-DISENO': 'Modelado paramétrico y de mallas, simulación, diseño para fabricación y CAM',
    'FAB-AREA-SCAN3D': 'Escaneo 3D, ingeniería inversa, inspección dimensional y control de calidad',
    'FAB-AREA-ELEC': 'Soldadura, ensamble de placas, instrumentación y prototipos electrónicos',
    'FAB-SALA-CAP': 'Atención de pedidos, almacén y entrega de trabajos, talleres y capacitación',
    'FAB-AREA-ROBOTICA': 'Espacio que ocupa el Laboratorio de Robótica mientras no tenga sala propia',
    'ROB-AREA-COBOTS': 'Cobots, celdas, visión artificial y trabajo conjunto entre personas y robots',
    'ROB-AREA-MOVIL': 'Navegación con ROS 2, drones, arena de pruebas y competencias',
    'ROB-AREA-PLC': 'PLC, HMI, SCADA, neumática, simulación de planta y gemelo digital de procesos',
    'ROB-AREA-IOT': 'Microcontroladores, LoRaWAN, MQTT, tableros y visión en el borde',
    'ROB-AREA-BANCOS': 'Bancos de prueba, instrumentación, motores, convertidores y calidad de energía',
    'XR-AREA-RV': 'Unity, Unreal, OpenXR, visores autónomos y profesionales, RA móvil y WebXR',
    'XR-AREA-SIM': 'Simuladores de entrenamiento, gemelos digitales con IoT, Omniverse y Pixel Streaming',
    'XR-AREA-3D': 'Modelado, fotogrametría, escaneo, captura corporal y facial, video volumétrico',
    'XR-AREA-META': 'Mundos virtuales, aulas y eventos inmersivos',
    'XR-SALA-EXP': 'Área libre de movimiento, pruebas con usuarios, confort y cinetosis',
    'IA-SALA-COMPUTO': 'Python, R, estadística y aprendizaje automático para todas las carreras',
    'IA-NODO-GPU': 'Aprendizaje profundo, IA generativa, visión por computador y modelos locales',
    'IA-SALA-ANALITICA': 'Tableros, analítica colaborativa y apoyo a la toma de decisiones',
    'IA-DATOS-ABIERTOS': 'Bases de datos, flujos de datos, portal CKAN y servicio a los observatorios',
    'CYB-AREA-REDES': 'Enrutamiento y conmutación, redes definidas por software, virtualización y nube privada',
    'CYB-AREA-RANGE': 'Cyber range aislado, pruebas de penetración, ejercicios y competencias CTF',
    'CYB-AREA-SOC': (
        'Monitoreo, detección, respuesta e inteligencia de amenazas, incluida la seguridad de IoT y '
        'sistemas industriales'
    ),
    'CYB-AREA-FORENSE': 'Adquisición de evidencia, análisis forense, móviles y malware en entorno aislado',
    'MED-EST-TV': 'Estudio multicámara, transmisión en vivo y ciclorama con escenarios virtuales',
    'MED-EST-RADIO': 'Radio en línea, podcast, sonido directo y diseño sonoro',
    'MED-AREA-POST': 'Edición, color, mezcla, motion graphics y animación',
    'MED-EST-FOTO': 'Estudio de luz, fotografía de producto y revelado digital',
    'MED-AREA-CAMPO': 'Cámaras de cine, estabilización, sonido de campo y préstamo de equipos',
    **{codigo: area['descripcion'] for codigo, area in AREAS_LOGISTICA.items()},
    'EMP-SALA-COWORK': 'Cowork, mentorías, comité de evaluación y seguimiento de emprendimientos',
    'EMP-AREA-PROTOTIPO': 'Modelo de negocio, prototipos rápidos y pruebas con usuarios',
    'EMP-AREA-SOFTWARE': 'Contabilidad, facturación electrónica, ERP, simuladores de negocio y finanzas',
    'EMP-CABINA-PITCH': 'Pitch y grabación, marca, vitrina, punto de venta y comercio electrónico',
    'GOB-AREA-GESTION': 'Simulación de gestión, presupuesto, planificación y evaluación de políticas públicas',
    'GOB-AREA-DATOS': 'Portales de datos abiertos, transparencia fiscal y analítica pública',
    'GOB-SALA-DELIBERACION': 'Deliberación, consultas, presupuestos participativos y laboratorios ciudadanos',
    'GOB-AREA-TRAMITES': 'Diseño de servicios, trámites en línea, firma electrónica, accesibilidad y atención ciudadana',
    'TUR-AREA-SIG': 'Ordenamiento territorial, recurso solar, catastro y visores web',
    'TUR-AREA-CAMPO': 'GNSS RTK, drones, sensores ambientales y levantamientos',
    'TUR-AREA-EFICIENCIA': 'Auditorías energéticas, medición de consumo y monitoreo con IoT',
    'TUR-AREA-SOLAR': 'Solar fotovoltaica y térmica, almacenamiento, microrredes y biogás en San Francisco',
    'TUR-AREA-OPERACION': 'Operación turística simulada, interpretación del patrimonio y guianza',
    'ANC-AREA-ALIMENTOS': 'Análisis proximal, leche, etiquetado nutricional, inocuidad y apoyo a las plantas piloto',
    'ANC-AREA-SUELOS': 'Fertilidad de suelos, calidad del agua, descargas y monitoreo ambiental',
    'ANC-AREA-INSTRUMENTAL': (
        'Cromatografía HPLC y GC, espectrofotometría, absorción atómica, digestión y validación de '
        'métodos'
    ),
    'ANC-AREA-BIOQUIMICA': 'Bioquímica experimental y química y física de primeros semestres',
    'ANC-RECEPCION': 'Recepción y custodia de muestras, LIMS, ISO 17025, balanzas y reactivos, residuos químicos',
    'REO-AREA-REOLOGIA': 'Viscosidad, reología oscilatoria y empastado de almidones',
    'REO-AREA-TEXTURA': 'Perfil de textura, colorimetría, espectrofotometría de color y análisis de imagen',
    'REO-AREA-MUESTRAS': 'Preparación normalizada, actividad de agua, cámara climática y estudios de estabilidad',
    'BIO-AREA-MICRO': 'Siembra, recuentos, indicadores e identificación',
    'BIO-AREA-MOLECULAR': 'Extracción de ácidos nucleicos, PCR, qPCR, electroforesis y bioinformática',
    'BIO-AREA-CEPARIO': 'Biorreactor, fermentaciones, conservación de cepas y bioinsumos',
    'BIO-AREA-CULTIVO': 'Cultivo de células, conteo y viabilidad',
    'BIO-CABINAS': 'Cabinas de bioseguridad, preparación de medios, autoclaves y residuos biológicos',
    'VET-RECEPCION': 'Registro y cadena de frío de muestras, banco de muestras y criopreservación',
    'VET-AREA-SEROLOGIA': 'ELISA y pruebas serológicas para sanidad animal',
    'VET-AREA-MOLECULAR': 'PCR, qPCR, secuencias y bioinformática para enfermedades del hato',
    'VET-AREA-PARASITOLOGIA': 'Diagnóstico parasitológico, microbiología veterinaria, mastitis y células somáticas',
    'VET-AREA-ANATOMIA': 'Anatomía, necropsia y patología; se habilita con su equipamiento',
    'SEN-CABINAS': 'Cabinas ISO 8589, pruebas discriminativas y afectivas con registro digital',
    'SEN-SALA-PANEL': 'Selección y entrenamiento de jueces, análisis descriptivo y estadística sensorial',
    'SEN-COCINA': 'Formulación, prototipos, preparación estandarizada de muestras y escalado a las plantas piloto',
    'SEN-SALA-CONSUMIDORES': 'Pruebas con consumidores, grupos focales, aceptación y posicionamiento de productos',
    'CLI-TOMA-MUESTRAS': 'Flebotomía, recepción, rechazo y trazabilidad de muestras con código de barras',
    'CLI-AREA-HEMATOLOGIA': 'Analizadores hematológicos y de química, coagulación, electrolitos, control de calidad Westgard',
    'CLI-AREA-MICRO': 'Cultivo, identificación, antibiograma y vigilancia de la resistencia',
    'CLI-AREA-INMUNOLOGIA': 'ELISA, quimioluminiscencia, PCR en tiempo real y pruebas rápidas',
    'CLI-AREA-UROANALISIS': 'Orina automatizada, parasitología, atlas y microscopía con cámara',
    'CLI-BANCO': (
        'Sistema de información del laboratorio (LIS), ISO 15189, residuos, cadena de frío y banco de '
        'muestras'
    ),
    'SIM-AREA-MORFO': 'Modelos anatómicos, mesa de disección virtual, atlas 3D e histología',
    'SIM-AREA-HABILIDADES': 'Entrenadores de tareas, venopunción, sondaje, curaciones, suturas y RCP',
    'SIM-SALA-CLINICA': 'Paciente hospitalizado, medicación segura, instrumentación quirúrgica, paro y paciente grave',
    'SIM-SALA-MATERNO': 'Parto, recién nacido, neonatología y pediatría',
    'SIM-SALA-COMUNITARIA': 'Hogar simulado, adulto mayor, valoración domiciliaria y atención a distancia con telepresencia',
    'SIM-CONTROL': 'Cuarto de control, grabación, pacientes virtuales, realidad virtual y análisis de desempeño',
    'EDU-ZONAS': 'Seis zonas de aprendizaje, metodologías activas y producción de recursos',
    'EDU-AREA-ROBOTICA': 'Programación, robótica educativa, sensores y ciencia en el aula',
    'EDU-AREA-LECTOESCRITURA': 'Lectoescritura, narración interactiva y recursos accesibles',
    'EDU-AREA-EMERGENTES': 'Inteligencia artificial, realidad extendida y analítica del aprendizaje en el aula',
}

# Cada área: (sufijo del código, nombre, tipo, capacidad[, extra]). El código es PREFIJO-sufijo, y
# conserva el de las áreas que ya existían para no duplicarlas.
LABORATORIOS = (
    {
        'slug': 'laboratorio-fabricacion-digital-prototipado', 'prefijo': 'FAB',
        'anteriores': ('laboratorio-manufactura-digital-prototipado-prueba',),
        'nombre': 'Laboratorio de Fabricación Digital y Prototipado', 'corto': 'FabLab UPEC',
        'area': 'ingenieria', 'nivel': 'A', 'tipo': 'D+I+S', 'resolucion': 'DIN-2022-02-INVLAB',
        'ubicacion': 'Aulas 2 PB, aula 404', 'titular': 'Computación',
        'usuarias': 'Logística, Multimedia, Administración de Empresas, Educación',
        'responsables': ('MSc. Jeffery Naranjo',),
        'descripcion_corta': 'Fabricación digital, prototipado y electrónica: diez áreas al servicio de cuatro '
                             'carreras y de terceros.',
        'descripcion': 'Plataforma compartida de fabricación digital: impresión 3D, corte láser, mecanizado CNC, '
                       'escaneo 3D, diseño y electrónica, con almacén de materiales y sala de capacitación. '
                       'Hospeda al Laboratorio de Robótica hasta que tenga sala propia y presta servicios de '
                       'prototipado a la comunidad.',
        'areas': (
            ('AREA-IMP3D', 'Manufactura aditiva', 'area', 6, {'absorbe': ('AREA-ACABADOS',)}),
            ('AREA-LASER', 'Manufactura sustractiva: láser y CNC', 'area', 4, {'absorbe': ('AREA-CNC', 'AREA-VINILO')}),
            ('EST-DISENO', 'Diseño e ingeniería CAD/CAM', 'estacion', 8),
            ('AREA-SCAN3D', 'Digitalización 3D y metrología', 'area', 4),
            ('AREA-ELEC', 'Electrónica y prototipado de hardware', 'area', 6),
            ('SALA-CAP', 'Servicios, materiales y formación', 'sala', 20, {'absorbe': ('ALMACEN',)}),
            ('AREA-ROBOTICA', 'Área hospedada: Robótica y Automatización', 'area', 8),
        ),
    },
    {
        'slug': 'laboratorio-robotica-electronica-automatizacion', 'prefijo': 'ROB',
        'anteriores': ('laboratorio-robotica-automatizacion-prueba',),
        'nombre': 'Laboratorio de Robótica, Electrónica y Automatización', 'corto': 'Robótica y Automatización',
        'area': 'ingenieria', 'nivel': 'B', 'tipo': 'D+I',
        'resolucion': 'DIIN-2023-04L · RCI-SVO-001-N°006.3-2023',
        'ubicacion': 'Aulas 2 PB, aula 404 (área delimitada en el FabLab) hasta tener sala',
        'titular': 'Computación', 'usuarias': 'Logística, Energías', 'responsables': (),
        'descripcion_corta': 'Robótica móvil y colaborativa, automatización industrial, IoT y electrónica aplicada.',
        'descripcion': 'Laboratorio de robótica, electrónica y automatización con resolución propia y compra de '
                       'equipos en curso. Opera como área hospedada en el FabLab hasta contar con sala; sus '
                       'áreas cubren robots móviles y drones, manipuladores y cobots, PLC y SCADA, IoT y '
                       'sistemas embebidos.',
        'areas': (
            ('AREA-COBOTS', 'Robótica colaborativa y manufactura 5.0', 'area', 4),
            ('AREA-MOVIL', 'Robótica móvil, drones y sistemas autónomos', 'area', 6, {'absorbe': ('ARENA',)}),
            ('AREA-PLC', 'Automatización industrial e Industria 4.0', 'area', 6),
            ('AREA-IOT', 'Sistemas embebidos, IoT e IA en el borde', 'area', 8),
            ('AREA-BANCOS', 'Electrónica aplicada y de potencia', 'area', 6),
        ),
    },
    {
        'slug': 'laboratorio-realidad-extendida', 'prefijo': 'XR',
        'anteriores': ('laboratorio-realidad-extendida-medios-interactivos-prueba',),
        'nombre': 'Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales', 'corto': 'Realidad Extendida',
        'area': 'comunicacion', 'nivel': 'A', 'tipo': 'D+I', 'resolucion': 'DIIN-2022-01L',
        'ubicacion': 'Aulas 3 PB, aula 015', 'titular': 'Computación y Logística (cotitulares)',
        'usuarias': 'Enfermería, Turismo, Multimedia, Educación', 'responsables': ('PhD. Luis Omar Alpala',),
        'descripcion_corta': 'Realidad virtual, aumentada y mixta, simulación, gemelos digitales y captura de '
                             'movimiento para seis carreras.',
        'descripcion': 'Reúne en una sola sede la realidad virtual, la realidad aumentada y la simulación con '
                       'gemelos digitales. Produce contenidos inmersivos para Enfermería, Turismo y Educación, '
                       'y da soporte a las prácticas de Computación y Logística.',
        'areas': (
            ('AREA-RV', 'Desarrollo de experiencias XR: virtual, aumentada y mixta', 'area', 8, {'absorbe': ('AREA-RA',)}),
            ('AREA-SIM', 'Simulación y gemelos digitales', 'area', 8),
            ('AREA-3D', 'Contenidos 3D, captura de movimiento y volumetría', 'estacion', 6, {'absorbe': ('AREA-MOCAP',)}),
            ('AREA-META', 'Metaverso y entornos colaborativos', 'area', 12),
            ('SALA-EXP', 'Sala de experiencias y evaluación de usuarios', 'sala', 12),
        ),
    },
    {
        'slug': 'laboratorio-inteligencia-artificial-ciencia-datos', 'prefijo': 'IA',
        'anteriores': ('laboratorio-ia-datos',),
        'nombre': 'Laboratorio de Inteligencia Artificial y Ciencia de Datos', 'corto': 'IA y Ciencia de Datos',
        'area': 'ia', 'nivel': 'B', 'tipo': 'D+I', 'resolucion': '',
        'ubicacion': 'Aulas 4 PB, laboratorio 9', 'titular': 'Computación',
        'usuarias': 'Los tres observatorios, Administración, Comercio', 'responsables': ('MSc. Samuel Lascano',),
        'descripcion_corta': 'Sala de cómputo, nodo GPU y analítica colaborativa; sirve de infraestructura de '
                             'datos a los observatorios.',
        'descripcion': 'Sala de cómputo con licencias concurrentes, nodo de GPU y servidores, y espacio de '
                       'analítica colaborativa. Mantiene el repositorio de datos abiertos y atiende a los tres '
                       'observatorios con un ingeniero de datos compartido.',
        'areas': (
            ('SALA-COMPUTO', 'Ciencia de datos y estadística aplicada', 'sala', 20),
            ('NODO-GPU', 'Inteligencia artificial y cómputo de alto rendimiento', 'otro', 2),
            ('SALA-ANALITICA', 'Visualización e inteligencia de negocios', 'sala', 12),
            ('DATOS-ABIERTOS', 'Ingeniería de datos y datos abiertos', 'otro', 4),
        ),
    },
    {
        'slug': 'laboratorio-ciberseguridad-redes', 'prefijo': 'CYB',
        'anteriores': ('laboratorio-ciberseguridad-redes-inteligentes-prueba',),
        'nombre': 'Laboratorio de Ciberseguridad y Redes Inteligentes', 'corto': 'Ciberseguridad y Redes',
        'area': 'ia', 'nivel': 'B', 'tipo': 'D+I', 'resolucion': '',
        'ubicacion': 'Aulas 4 PB', 'titular': 'Computación', 'usuarias': '',
        'responsables': ('Ing. Milton Del Hierro', 'MSc. Jairo Hidalgo'),
        'descripcion_corta': 'Redes, cyber range aislado, SOC académico y forense digital en una sede única.',
        'descripcion': 'Une las antiguas salas de Redes y de Ciberseguridad en una sede con red aislada: '
                       'racks y conmutación, cyber range de ataque y defensa, SOC académico y análisis forense '
                       'de malware.',
        'areas': (
            ('AREA-REDES', 'Redes, nube e infraestructura', 'area', 16, {'absorbe': ('AREA-INALAMBRICAS',)}),
            ('AREA-RANGE', 'Ciberdefensa: ataque y defensa', 'area', 12),
            ('AREA-SOC', 'Centro de operaciones de seguridad', 'area', 8),
            ('AREA-FORENSE', 'Informática forense y análisis de malware', 'area', 4),
        ),
    },
    {
        'slug': 'laboratorio-multimedia-produccion-audiovisual', 'prefijo': 'MED',
        'nombre': 'Laboratorio de Multimedia y Producción Audiovisual', 'corto': 'Multimedia y Audiovisual',
        'area': 'comunicacion', 'nivel': 'B', 'tipo': 'D+S',
        'resolucion': 'RCI-SVO-001-N°036-2024 · DIIN-2024-01L',
        'ubicacion': 'Posgrado: aula 210 y estudios del 4.º piso', 'titular': 'Multimedia y Producción Audiovisual',
        'usuarias': 'Turismo, Administración de Empresas', 'responsables': ('MSc. Fernando Pazmiño',),
        'descripcion_corta': 'Estudios de televisión, radio y posproducción, fotografía y producción de campo.',
        'descripcion': 'Laboratorio con resolución propia que reúne los estudios de televisión y radio, la '
                       'posproducción, la fotografía y el préstamo de equipos de campo. Produce contenidos para '
                       'las demás unidades y presta servicios de producción.',
        'areas': (
            ('EST-TV', 'Televisión, streaming y producción virtual', 'sala', 12, {'absorbe': ('EST-CHROMA',)}),
            ('EST-RADIO', 'Audio, radio y podcast', 'cabina', 4),
            ('AREA-POST', 'Posproducción, animación y efectos visuales', 'estacion', 8),
            ('EST-FOTO', 'Fotografía e imagen', 'sala', 8),
            ('AREA-CAMPO', 'Producción de campo, cine y documental', 'otro', 6),
        ),
    },
    {
        'slug': 'laboratorio-logistica-comercio-internacional', 'prefijo': 'LOG',
        'anteriores': ('smart-logistics-lab',),
        'nombre': NOMBRE_LOGISTICA,
        'corto': CORTO_LOGISTICA,
        'area': 'gestion', 'nivel': 'B', 'tipo': 'D',
        'resolucion': 'DIIN-2023-05L · RCI-SVO-001-N°006.4-2023 (Business Lab)',
        'ubicacion': 'Aulas 3 PB, aula 016', 'titular': 'Logística y Comercio Exterior (cotitulares)',
        'usuarias': 'Administración de Empresas', 'responsables': ('PhD. Luis Omar Alpala', 'PhD. Jaime Moreno'),
        'descripcion_corta': LEMA_LOGISTICA,
        'descripcion': DESCRIPCION_LOGISTICA,
        'areas': (
            ('ALMACEN', AREAS_LOGISTICA['LOG-ALMACEN']['nombre'], 'area', 10),
            ('AREA-SIM', AREAS_LOGISTICA['LOG-AREA-SIM']['nombre'], 'estacion', 16),
            ('AREA-TMS', AREAS_LOGISTICA['LOG-AREA-TMS']['nombre'], 'estacion', 8),
            ('AREA-PRODUCCION', AREAS_LOGISTICA['LOG-AREA-PRODUCCION']['nombre'], 'area', 10,
             {'equipos': ('Minifábrica', 'Kit de muestras de carga', 'Mesa de packing')}),
            ('AREA-COMERCIO', AREAS_LOGISTICA['LOG-AREA-COMERCIO']['nombre'], 'estacion', 16, {'absorbe': ('SALA-NEGOCIACION',)}),
            ('AREA-ERP', AREAS_LOGISTICA['LOG-AREA-ERP']['nombre'], 'estacion', 16),
        ),
    },
    {
        'slug': 'laboratorio-emprendimiento-innovacion-empresarial', 'prefijo': 'EMP',
        'anteriores': ('laboratorio-emprendimiento-innovacion-prueba',),
        'nombre': 'Laboratorio de Emprendimiento e Innovación Empresarial', 'corto': 'Emprendimiento e Innovación',
        'area': 'gestion', 'nivel': 'B', 'tipo': 'D+I', 'resolucion': 'RCI-SVO-001-N°047-2024 · DIIN-2024-02L',
        'ubicacion': 'Por asignar (sala liberada en Aulas 2)', 'titular': 'Administración de Empresas',
        'usuarias': 'Contabilidad, Comercio Exterior', 'responsables': ('MSc. Freddy Quinde', 'MSc. Jeaneth Bastidas'),
        'descripcion_corta': 'Cowork e incubación, mentorías, software empresarial y vitrina de emprendimientos.',
        'descripcion': 'Espacio donde los equipos emprendedores dan forma a una idea: cowork e incubación, sala '
                       'de juntas y comité, cabina de pitch, prototipado de baja fidelidad y software empresarial, '
                       'contable y financiero. La ruta sigue en el FabLab para el prototipo físico.',
        'areas': (
            ('SALA-COWORK', 'Incubación y aceleración de emprendimientos', 'sala', 24, {'absorbe': ('SALA-JUNTAS',)}),
            ('AREA-PROTOTIPO', 'Diseño, prototipado y validación', 'area', 16),
            ('AREA-SOFTWARE', 'Finanzas y gestión empresarial digital', 'estacion', 16),
            ('CABINA-PITCH', 'Marketing digital, pitch y comercialización', 'cabina', 3, {'absorbe': ('VITRINA',)}),
        ),
    },
    {
        'slug': 'laboratorio-asuntos-publicos-gobierno', 'prefijo': 'GOB',
        'nombre': 'Laboratorio de Asuntos Públicos y de Gobierno', 'corto': 'Asuntos Públicos',
        'area': 'gestion', 'nivel': 'C', 'tipo': 'D', 'resolucion': 'RCI-SVO-001-N°006-2023 · DIIN-2023-01L',
        'ubicacion': 'Aulas 1 PB, aula 01', 'titular': 'Administración Pública', 'usuarias': '',
        'responsables': ('Mike Coral Erazo',),
        'descripcion_corta': 'Simulación de gestión pública, datos abiertos, participación ciudadana y trámites '
                             'digitales.',
        'descripcion': 'Laboratorio docente de Administración Pública con resolución y sala propias: simula la '
                       'gestión y el presupuesto públicos, trabaja con datos abiertos y transparencia, y ensaya '
                       'la participación ciudadana y los trámites digitales.',
        'areas': (
            ('AREA-GESTION', 'Gestión pública, presupuesto y políticas', 'estacion', 16),
            ('AREA-DATOS', 'Gobierno abierto, datos y transparencia', 'estacion', 12),
            ('SALA-DELIBERACION', 'Participación ciudadana e innovación social', 'sala', 20),
            ('AREA-TRAMITES', 'Gobierno digital y servicios al ciudadano', 'estacion', 12),
        ),
    },
    {
        # El Laboratorio de Turismo se une con el de Energías Renovables propuesto en la reforma: conserva su
        # sala, sus equipos y el prefijo de sus áreas, y atiende a Turismo hasta el cierre de la carrera.
        'slug': 'laboratorio-energias-renovables-territorio', 'prefijo': 'TUR',
        'anteriores': ('laboratorio-turismo',),
        'nombre': 'Laboratorio de Energías Renovables y Territorio', 'corto': 'Energías y Territorio',
        'area': 'ingenieria', 'nivel': 'C', 'tipo': 'D+I+S', 'resolucion': 'DIN-2022-03-INVLAB · 275-CSUP-2022',
        'ubicacion': 'Aulas 1 PB; sede de campo en el Centro Experimental San Francisco', 'titular': 'Turismo (hasta el cierre de la carrera)',
        'usuarias': 'Agropecuaria, Administración Pública y Computación; base para una futura carrera de energías',
        'responsables': ('PhD. Jaime Iturralde',),
        'descripcion_corta': 'Eficiencia energética, energía solar, SIG y trabajo de campo para el territorio; '
                             'atiende a Turismo hasta el cierre de la carrera.',
        'descripcion': 'Nace de unir el Laboratorio de Turismo con el de Energías Renovables que propuso la '
                       'reforma. Conserva la sala de las Aulas 1 y sus equipos de SIG, GNSS RTK, drones y '
                       'sensores ambientales, y suma eficiencia energética, energía solar y microrredes. Su sede '
                       'de campo es la planta demostrativa de energías del Centro Experimental San Francisco. '
                       'Mientras haya cohortes de Turismo, mantiene sus áreas de operación turística y patrimonio.',
        'reescribir_descripcion': True,
        'areas': (
            ('AREA-SIG', 'Planificación territorial y SIG', 'estacion', 12),
            ('AREA-CAMPO', 'Monitoreo ambiental y trabajo de campo', 'otro', 6),
            ('AREA-EFICIENCIA', 'Eficiencia y gestión de la energía', 'estacion', 8, {'futura': True}),
            ('AREA-SOLAR', 'Energías renovables y microrredes', 'area', 8, {'futura': True}),
            ('AREA-OPERACION', 'Turismo y patrimonio (hasta el cierre de la carrera)', 'area', 8, {'absorbe': ('AREA-PATRIMONIO',)}),
        ),
    },
    {
        'slug': 'laboratorio-analisis-calidad-alimentos-suelos-aguas', 'prefijo': 'ANC',
        'anteriores': ('laboratorio-agroindustria-calidad-alimentaria-prueba',),
        'nombre': 'Laboratorio de Análisis y Calidad de Alimentos, Suelos y Aguas', 'corto': 'Análisis y Calidad',
        'area': 'agro', 'nivel': 'A', 'tipo': 'D+I+S', 'resolucion': '',
        'ubicacion': 'Edificio de Laboratorios, salas 201–203', 'titular': 'Alimentos',
        'usuarias': 'Agropecuaria, Veterinaria, primeros semestres; carreras ambientales futuras',
        'responsables': ('MSc. Vinicio Revelo',),
        'descripcion_corta': 'Bioquímica, suelos y aguas, análisis de alimentos y control de calidad, con '
                             'servicios acreditables.',
        'descripcion': 'Une las salas 201, 202 y 203 en una plataforma de análisis: bioquímica, suelos y aguas, '
                       'alimentos y control de calidad, más calidad ambiental e instrumental compartido. '
                       'Atiende la docencia de primeros semestres y servicios bajo ISO/IEC 17025.',
        'areas': (
            ('AREA-ALIMENTOS', 'Análisis de alimentos, inocuidad y control de calidad', 'area', 16, {'ubicacion': 'Sala 203'}),
            ('AREA-SUELOS', 'Suelos, aguas y calidad ambiental', 'area', 16, {'ubicacion': 'Sala 202', 'absorbe': ('AREA-AMBIENTAL',)}),
            ('AREA-INSTRUMENTAL', 'Instrumentación analítica avanzada', 'area', 4),
            ('AREA-BIOQUIMICA', 'Bioquímica y ciencias básicas', 'area', 16, {'ubicacion': 'Sala 201'}),
            ('RECEPCION', 'Servicios analíticos y gestión de calidad', 'otro', 2, {'absorbe': ('AREA-PREPARACION', 'RESIDUOS')}),
        ),
    },
    {
        'slug': 'laboratorio-reologia-textura-alimentos', 'prefijo': 'REO',
        'nombre': 'Laboratorio de Reología y Textura de Alimentos', 'corto': 'Reología y Textura',
        'area': 'agro', 'nivel': 'B', 'tipo': 'D+I+S', 'resolucion': 'No. 26-SVO-CI-2025 · DIIN-2025-01L',
        'ubicacion': 'Edificio de Laboratorios, sala 206', 'titular': 'Alimentos',
        'usuarias': 'Las 5 plantas piloto', 'responsables': ('MSc. Carlos Paredes',),
        'descripcion_corta': 'Reología y análisis de textura de alimentos para las cinco plantas piloto.',
        'descripcion': 'Laboratorio con resolución de 2025 y equipo especializado de uso intermitente: reología, '
                       'análisis de textura y acondicionamiento de muestras. Tiene su sede en la sala 206 y '
                       'atiende los productos de las plantas piloto.',
        'areas': (
            ('AREA-REOLOGIA', 'Reología y comportamiento de flujo', 'area', 4),
            ('AREA-TEXTURA', 'Textura, color e imagen de alimentos', 'area', 4, {'absorbe': ('AREA-COLOR',)}),
            ('AREA-MUESTRAS', 'Acondicionamiento de muestras y vida útil', 'area', 6),
        ),
    },
    {
        'slug': 'laboratorio-microbiologia-biotecnologia-aplicada', 'prefijo': 'BIO',
        'anteriores': ('laboratorio-biotecnologia-aplicada-prueba',),
        'nombre': 'Laboratorio de Microbiología y Biotecnología Aplicada', 'corto': 'Microbiología y Biotecnología',
        'area': 'biotecnologia', 'nivel': 'B', 'tipo': 'D+I', 'resolucion': '',
        'ubicacion': 'Edificio de Laboratorios, salas 204–205', 'titular': 'Alimentos', 'usuarias': 'Agropecuaria',
        'responsables': ('MSc. Vinicio Revelo',),
        'descripcion_corta': 'Microbiología, biología molecular, cepario, fermentaciones y cultivo celular con '
                             'bioseguridad BSL-2.',
        'descripcion': 'Laboratorio húmedo que une las salas 204 y 205: siembra e incubación, PCR, cepario y '
                       'fermentaciones, cultivo celular y preparación de medios. Su bioseguridad lo separa de la '
                       'fisicoquímica y exige laboratorista propio.',
        'areas': (
            ('AREA-MICRO', 'Microbiología de alimentos y ambiental', 'area', 12, {'ubicacion': 'Sala 204'}),
            ('AREA-MOLECULAR', 'Biología molecular y genómica', 'area', 8, {'ubicacion': 'Sala 205'}),
            ('AREA-CEPARIO', 'Bioprocesos, fermentaciones y cepario', 'area', 6),
            ('AREA-CULTIVO', 'Cultivo celular y biotecnología avanzada', 'area', 6),
            ('CABINAS', 'Bioseguridad, medios y esterilización', 'cabina', 2, {'absorbe': ('MESON-PREPARACION',)}),
        ),
    },
    {
        'slug': 'laboratorio-diagnostico-veterinario-biologia-molecular', 'prefijo': 'VET',
        'nombre': 'Laboratorio de Diagnóstico Veterinario y Biología Molecular', 'corto': 'Diagnóstico Veterinario',
        'area': 'biotecnologia', 'nivel': 'B', 'tipo': 'D+I+S',
        'resolucion': 'No. 39-SVE-CI-2025 · DIIN-2025-02L · DIN-2022-01-INVLAB',
        'ubicacion': 'Por asignar (Edificio de Laboratorios o San Francisco)',
        'titular': 'Medicina Veterinaria y Agropecuaria (cotitulares)', 'usuarias': 'Alimentos',
        'responsables': ('Dr. Martin Campos', 'MSc. Marcelo Ibarra'),
        'descripcion_corta': 'Serología, biología molecular animal, parasitología y banco de muestras; '
                             'diagnóstico para ganaderos.',
        'descripcion': 'Une Biología Molecular Veterinaria y Diagnóstico Serológico Molecular en un laboratorio '
                       'animal completo: recepción de muestras, serología e inmunodiagnóstico, PCR, parasitología '
                       'y banco de muestras. Presta servicios de diagnóstico a la cadena láctea.',
        'areas': (
            ('RECEPCION', 'Recepción, bioseguridad y biobanco', 'otro', 2, {'absorbe': ('BANCO',)}),
            ('AREA-SEROLOGIA', 'Inmunodiagnóstico y serología', 'area', 6),
            ('AREA-MOLECULAR', 'Diagnóstico molecular y genómica animal', 'area', 6),
            ('AREA-PARASITOLOGIA', 'Parasitología, microbiología y calidad de leche', 'area', 8),
            ('AREA-ANATOMIA', 'Anatomía y patología veterinaria', 'sala', 12, {'futura': True}),
        ),
    },
    {
        'slug': 'laboratorio-analisis-sensorial-desarrollo-alimentos', 'prefijo': 'SEN',
        'anteriores': ('laboratorio-analisis-sensorial-alimentos-prueba',),
        'nombre': 'Laboratorio de Análisis Sensorial y Desarrollo de Alimentos', 'corto': 'Análisis Sensorial',
        'area': 'agro', 'nivel': 'B', 'tipo': 'D+I+S', 'resolucion': 'DIIN-2022-02L · RCI-SVO-009-N°114-2022',
        'ubicacion': 'Edificio de Laboratorios, salas 101–102', 'titular': 'Alimentos',
        'usuarias': 'Las 5 plantas piloto', 'responsables': ('PhD. Marco Burbano',),
        'descripcion_corta': 'Cabinas de evaluación ISO 8589, cocina de muestras, panel entrenado y grupos de '
                             'consumidores.',
        'descripcion': 'Laboratorio con resolución, salas propias y paneles programados: cabinas de evaluación '
                       'sensorial, cocina y preparación de muestras, sala de panel y entrenamiento, y sala de '
                       'consumidores. Desarrolla y valida los productos de las plantas piloto.',
        'areas': (
            ('CABINAS', 'Evaluación sensorial instrumentada', 'cabina', 8, {'absorbe': ('AREA-INSTRUMENTAL',)}),
            ('SALA-PANEL', 'Panel entrenado y perfiles sensoriales', 'sala', 12),
            ('COCINA', 'Desarrollo de productos y cocina experimental', 'area', 6),
            ('SALA-CONSUMIDORES', 'Ciencia del consumidor y estudios de mercado', 'sala', 20),
        ),
    },
    {
        'slug': 'laboratorio-clinico', 'prefijo': 'CLI',
        'nombre': 'Laboratorio Clínico', 'corto': 'Laboratorio Clínico',
        'area': 'salud', 'nivel': 'A', 'tipo': 'D+I', 'resolucion': '',
        'ubicacion': 'Edificio de Laboratorios, salas 301–304', 'titular': 'Laboratorio Clínico',
        'usuarias': 'Enfermería', 'responsables': ('MSc. Miguel Ger',),
        'descripcion_corta': 'Hematología, microbiología clínica, inmunología y uroanálisis con muestras humanas '
                             'bajo ISO 15189.',
        'descripcion': 'Reúne las cuatro salas del Clínico (301–304) en una unidad con toma de muestras, '
                       'hematología y química sanguínea, microbiología clínica, inmunología y biología '
                       'molecular, uroanálisis y parasitología, y banco de muestras con bioseguridad.',
        'areas': (
            ('TOMA-MUESTRAS', 'Fase preanalítica y toma de muestras', 'area', 4),
            ('AREA-HEMATOLOGIA', 'Hematología y química clínica automatizadas', 'area', 12, {'ubicacion': 'Sala 303'}),
            ('AREA-MICRO', 'Microbiología clínica y resistencia antimicrobiana', 'area', 12, {'ubicacion': 'Sala 304'}),
            ('AREA-INMUNOLOGIA', 'Inmunodiagnóstico y diagnóstico molecular', 'area', 12, {'ubicacion': 'Sala 302'}),
            ('AREA-UROANALISIS', 'Uroanálisis, parasitología y microscopía digital', 'area', 12, {'ubicacion': 'Sala 301'}),
            ('BANCO', 'Calidad, bioseguridad y biobanco', 'camara', 2),
        ),
    },
    {
        'slug': 'laboratorio-simulacion-clinica-enfermeria', 'prefijo': 'SIM',
        'nombre': 'Laboratorio de Simulación Clínica de Enfermería', 'corto': 'Simulación Clínica',
        'area': 'salud', 'nivel': 'A', 'tipo': 'D', 'resolucion': '',
        'ubicacion': 'Edificio de Laboratorios', 'titular': 'Enfermería', 'usuarias': 'Laboratorio Clínico',
        'responsables': ('MSc. Sonia Cárdenas',),
        'descripcion_corta': 'Centro de simulación clínica organizado por tipo de simulación, con control, '
                             'grabación y debriefing.',
        'descripcion': 'Reorganiza los seis laboratorios de Enfermería por tipo de simulación: morfofunción, '
                       'habilidades y procedimientos, simulación básica y clínica, quirúrgica y cuidados '
                       'críticos, materno-infantil y comunitaria, con cuarto de control, grabación y debriefing.',
        'areas': (
            ('AREA-MORFO', 'Morfofisiología y anatomía digital', 'area', 16),
            ('AREA-HABILIDADES', 'Habilidades clínicas y procedimientos', 'area', 12),
            ('SALA-CLINICA', 'Hospitalización, quirófano y cuidados críticos', 'sala', 12, {'absorbe': ('SALA-QUIRURGICA', 'FARMACIA')}),
            ('SALA-MATERNO', 'Salud materno-infantil', 'sala', 8),
            ('SALA-COMUNITARIA', 'Salud comunitaria, domiciliaria y telesalud', 'sala', 10),
            ('CONTROL', 'Simulación virtual, control y debriefing', 'sala', 16),
        ),
    },
    {
        'slug': 'laboratorio-innovacion-educativa', 'prefijo': 'EDU',
        'nombre': 'Laboratorio de Innovación Educativa y Tecnologías para el Aprendizaje',
        'corto': 'Innovación Educativa',
        'area': 'Educacion', 'nivel': 'B', 'tipo': 'D+I', 'resolucion': '',
        'ubicacion': 'Por asignar (sala liberada en Aulas 2)', 'titular': 'Educación Básica e Inicial',
        'usuarias': '', 'responsables': ('Dr. César Enríquez', 'Dra. Cecilia Yacelga'),
        'descripcion_corta': 'Aula del futuro con seis zonas de aprendizaje, robótica educativa y lectoescritura '
                             'digital.',
        'descripcion': 'Nace del proyecto de Investigación de Lectoescritura y sigue el modelo Future Classroom '
                       'Lab: zonas para investigar, crear, presentar, interactuar, intercambiar y desarrollar, '
                       'más robótica educativa y pensamiento computacional. Hasta tener sala trabaja en el '
                       'FabLab y en Realidad Extendida.',
        'areas': (
            ('ZONAS', 'Aula del futuro y diseño de experiencias de aprendizaje', 'sala', 30),
            ('AREA-ROBOTICA', 'Pensamiento computacional, robótica y STEAM', 'area', 16),
            ('AREA-LECTOESCRITURA', 'Alfabetización y recursos digitales inclusivos', 'area', 16),
            ('AREA-EMERGENTES', 'Tecnologías emergentes en educación', 'area', 12,
             {'equipos': ('Visores de realidad virtual', 'Mesa interactiva', 'Pantalla interactiva táctil')}),
        ),
    },
)

PLANTAS = (
    {'slug': 'planta-piloto-lacteos', 'nombre': 'Planta Piloto de Procesamiento de Lácteos', 'corto': 'Lácteos',
     'resolucion': 'RCI-SVO-001-N°006.1-2023 · DIIN-2023-02L'},
    {'slug': 'planta-piloto-carnicos', 'nombre': 'Planta Piloto de Procesamiento de Cárnicos', 'corto': 'Cárnicos'},
    {'slug': 'planta-piloto-frutas-vegetales', 'anteriores': ('planta-piloto-hortofruticola',),
     'nombre': 'Planta Piloto de Procesamiento de Frutas y Vegetales', 'corto': 'Frutas y Vegetales'},
    {'slug': 'planta-piloto-cereales', 'anteriores': ('planta-piloto-panificacion',),
     'nombre': 'Planta Piloto de Procesamiento de Cereales', 'corto': 'Cereales'},
    {'slug': 'planta-extraccion-almidon-biotecnologia', 'anteriores': ('planta-piloto-almidones',),
     'nombre': 'Planta de Extracción de Almidón y Biotecnología', 'corto': 'Almidón y Biotecnología'},
    # Plantas que nacen en el Centro Experimental Alonso Tadeo para transformar lo que produce.
    {'slug': 'planta-piloto-cafe', 'prefijo': 'PPCA', 'estado_catalogo': 'en_creacion',
     'nombre': 'Planta Piloto de Beneficio y Torrefacción de Café', 'corto': 'Café', 'area': 'agro',
     'ubicacion': 'Centro Experimental Alonso Tadeo, La Concepción–Mira', 'titular': 'Alimentos',
     'usuarias': 'Agropecuaria',
     'descripcion_corta': 'Beneficio, secado y tostado del café del Centro Experimental Alonso Tadeo; en formación.',
     'descripcion': 'Planta en formación en el Centro Experimental Alonso Tadeo. Ya cuenta con equipos de beneficio y '
                    'torrefacción de café; falta constituirla (resolución, áreas, protocolos y responsable) para procesar '
                    'el café del centro, ofrecer prácticas a Alimentos y Agropecuaria y desarrollar un café de origen.',
     'areas': (('BENEFICIO', 'Beneficio y secado', 'area', 6),
               ('TORREFACCION', 'Torrefacción y molienda', 'area', 4))},
    {'slug': 'planta-piloto-citricos-frutales', 'prefijo': 'PPCF', 'estado_catalogo': 'en_creacion',
     'nombre': 'Planta Piloto de Cítricos y Frutales Tropicales', 'corto': 'Cítricos y Frutales', 'area': 'agro',
     'ubicacion': 'Centro Experimental Alonso Tadeo, La Concepción–Mira (propuesta)', 'titular': 'Alimentos',
     'usuarias': 'Agropecuaria',
     'descripcion_corta': 'Propuesta para transformar el limón, la naranja y los frutales del Centro Experimental Alonso Tadeo.',
     'descripcion': 'Propuesta de planta para transformar el limón, la naranja y los demás frutales de clima cálido del '
                    'Centro Experimental Alonso Tadeo en jugos, pulpas, concentrados y deshidratados, de modo que la '
                    'cosecha de temporada alta no se pierda y sirva a prácticas de Alimentos.',
     'areas': (('PROCESO', 'Área de proceso de frutas', 'area', 6, FUTURA),)},
)

# Los dos centros experimentales: el de clima frío (Huaca) y el de clima cálido (Mira).
CENTROS = ({
    'slug': 'centro-experimental-san-francisco', 'prefijo': 'CESF',
    'anteriores': ('centro-experimental-san-francisco-prueba',), 'dependencia': 'centro_experimental',
    'nombre': 'Centro Experimental San Francisco', 'corto': 'San Francisco',
    'area': 'agro', 'resolucion': '', 'ubicacion': 'La Calera–Huaca', 'titular': 'Agropecuaria',
    'usuarias': 'Alimentos, Medicina Veterinaria, plantas piloto',
    'responsables': (('PhD. Hernán Benavides', 'Área de Producción láctea (DIIN-2024-03L)'),
                     ('MSc. Jeysonn Palma', 'Área de Tecnologías agropecuarias')),
    'descripcion_corta': 'Sede de campo de clima frío: ganadería de leche, cultivos andinos, frutales, invernaderos y '
                         'herbario; aloja las cinco plantas piloto.',
    'descripcion': 'Centro de producción y experimentación de clima frío en La Calera–Huaca, a 2834 m s. n. m., con '
                   '45 hectáreas: ganadería de leche con establo y ordeño mecánico, cultivos andinos (papa, trigo, haba, '
                   'arveja, chocho), frutales de altura (mora, uvilla, tomate de árbol, fresa), invernaderos de hortalizas, '
                   'cuyes y un herbario de plantas medicinales que maneja Enfermería. Aloja las cinco plantas piloto, que '
                   'transforman lo que produce, y recibe recorridos agroturísticos.',
    'reescribir_descripcion': True,
    'areas': (
        ('LACTEA', 'Producción láctea (hato y sala de ordeño)', 'establo', 10),
        ('AGROPECUARIA', 'Tecnologías agropecuarias', 'area', 12),
        ('AGROECOLOGIA', 'Agroecología y bioinsumos', 'area', 10),
        ('PARCELAS', 'Cultivos andinos y parcelas de ensayo', 'parcela', 15),
        ('FRUTALES', 'Frutales de clima frío', 'parcela', 10),
        ('INVERNADEROS', 'Invernaderos', 'invernadero', 10),
        ('CUYES', 'Galpón de cuyes', 'establo', 6),
        ('HERBARIO', 'Herbario y plantas medicinales', 'area', 10),
        ('ENERGIAS', 'Planta demostrativa de energías', 'otro', 8, FUTURA),
    ),
}, {
    'slug': 'centro-experimental-alonso-tadeo', 'prefijo': 'CEAT', 'dependencia': 'centro_experimental',
    'nombre': 'Centro Experimental Alonso Tadeo', 'corto': 'Alonso Tadeo',
    'area': 'agro', 'resolucion': '', 'ubicacion': 'La Concepción–Mira', 'titular': 'Agropecuaria',
    'usuarias': 'Alimentos, Medicina Veterinaria',
    'descripcion_corta': 'Sede de campo de clima cálido: café, cítricos y frutales, invernaderos, gallinas ponedoras '
                         'y cerdos.',
    'descripcion': 'Centro de producción y experimentación de clima cálido en La Concepción (Mira), a 1373 m s. n. m.: '
                   'cultivo de café con equipos de beneficio y torrefacción, cítricos y frutales (limón, naranja, tomate), '
                   'dos invernaderos de producción, una granja de gallinas ponedoras, cerdos de engorde, vivero y un '
                   'jardín botánico de especies alimenticias. Tiene capacidad para producir más de lo que hoy produce.',
    'areas': (
        ('CAFE', 'Cultivo de café', 'parcela', 10),
        ('FRUTALES', 'Cítricos y frutales', 'parcela', 10),
        ('INVERNADEROS', 'Invernaderos de producción', 'invernadero', 10),
        ('AVICOLA', 'Granja de gallinas ponedoras', 'establo', 6),
        ('PORCINO', 'Cerdos de engorde', 'establo', 6),
        ('VIVERO', 'Vivero y jardín botánico', 'area', 10),
    ),
})

OBSERVATORIOS = (
    {
        'slug': 'observatorio-turismo', 'anteriores': ('laboratorio-agroalimentario',), 'dependencia': 'observatorios',
        'nombre': 'Observatorio de Turismo del Carchi (ODETUR)', 'corto': 'ODETUR', 'area': 'gestion',
        'resolucion': '276-CSUP-2022',
        'ubicacion': 'Aulas 1 PB, sala de Turismo', 'titular': 'Turismo', 'usuarias': 'Administración Pública',
        'responsables': ('MSc. Diego Caicedo',),
        'descripcion_corta': 'Visitantes, perfil del turista, alojamiento, feriados y eventos.',
        'descripcion': 'Observatorio con resolución propia que publica indicadores y boletines del turismo de la '
                       'provincia. No depende de la carrera: al cerrarse esta, se fusiona con el OSEZIF en el '
                       'Observatorio Territorial de la Frontera Norte y conserva su antecedente.',
        'reescribir_descripcion': True,
    },
    {
        'slug': 'observatorio-osezif', 'dependencia': 'observatorios',
        'nombre': 'Observatorio Socioeconómico de la Zona de Integración Fronteriza', 'corto': 'OSEZIF',
        'area': 'gestion', 'resolucion': '', 'ubicacion': '', 'titular': 'Comercio Exterior (FCIIAEE)',
        'usuarias': 'Administración Pública, IA y Ciencia de Datos', 'responsables': ('MSc. Gerardo Mera',),
        'descripcion_corta': 'Comercio, empleo, pobreza, empresas y gobiernos locales.',
        'descripcion': 'Observatorio de la Facultad de Comercio Internacional, Integración, Administración y '
                       'Economía Empresarial que produce series de datos, publicaciones y vinculación con el '
                       'territorio fronterizo. Consta en el Plan 2025 y espera su resolución de creación.',
    },
    {
        'slug': 'observatorio-cadena-lactea-carchi', 'dependencia': 'observatorios',
        # Nació como Observatorio de la Cadena Láctea (OCL); conserva la sigla de su resolución.
        'nombre': 'Observatorio Agroalimentario del Carchi (OCL)', 'corto': 'OCL',
        'area': 'agro', 'resolucion': '027-CSUP-2025', 'ubicacion': '', 'titular': 'Medicina Veterinaria',
        'usuarias': 'Agropecuaria, Alimentos', 'responsables': ('MSc. Marcelo Ibarra',),
        'descripcion_corta': 'Papa, leche y hato ganadero, con sus precios al productor.',
        'descripcion': 'Observatorio con resolución de 2025 (027-CSUP-2025) que nació como Observatorio de la Cadena '
                       'Láctea, de ahí su sigla, y amplía su mirada a la '
                       'papa, de la que el Carchi produce más de la mitad del país: precio al productor, producción, '
                       'calidad de la leche y sanidad, con datos del Laboratorio de Diagnóstico Veterinario, la '
                       'Planta Piloto de Lácteos y el Centro Experimental San Francisco.',
        'reescribir_descripcion': True,
    },
    # Propuestos en la reorganización de octubre de 2026: nacen «En creación» hasta su resolución.
    {
        'slug': 'observatorio-ambiental-agua-clima', 'dependencia': 'observatorios', 'estado_catalogo': 'en_creacion',
        'nombre': 'Observatorio Ambiental del Carchi', 'corto': 'Ambiental',
        'area': 'agro', 'resolucion': '', 'ubicacion': '', 'titular': 'Agropecuaria',
        'usuarias': 'Turismo, Computación', 'responsables': (),
        'descripcion_corta': 'Páramo, bosques, incendios por satélite, agua, energía y clima.',
        'descripcion': 'Observatorio en creación que sigue el páramo que da agua a Tulcán y El Ángel, la pérdida de '
                       'bosque y los focos de calor que detecta el satélite, el acceso y la calidad del agua, la '
                       'energía y el clima, con la estación meteorológica y el Herbario de la UPEC.',
        'reescribir_descripcion': True,
    },
    {
        'slug': 'observatorio-social-frontera', 'dependencia': 'observatorios', 'estado_catalogo': 'en_creacion',
        'nombre': 'Observatorio Social de Frontera', 'corto': 'Social de Frontera',
        'area': 'salud', 'resolucion': '', 'ubicacion': '', 'titular': 'Enfermería, Laboratorio Clínico',
        'usuarias': 'Educación Básica, Educación Inicial, Administración Pública', 'responsables': (),
        'descripcion_corta': 'Movilidad humana, salud infantil, educación y seguridad en la frontera.',
        'descripcion': 'Observatorio en creación que sigue los cruces por Rumichaca y los pasos informales, la '
                       'desnutrición y la anemia infantil, el agua segura y el acceso a la educación de la población '
                       'en movilidad, con datos oficiales y de organismos internacionales, siempre agregados y anónimos.',
    },
)

# (slug de la unidad que se integra, slug de la que la recibe o None, por qué, se elimina aunque tenga historial)
INTEGRACIONES = (
    ('laboratorio-simulacion-gemelos-digitales-prueba', 'laboratorio-realidad-extendida',
     'su función es el área «Simulación y gemelos digitales» de Realidad Extendida', False),
    ('laboratorio-multimedia-inmersiva', 'laboratorio-realidad-extendida',
     'duplicaba la realidad virtual de Realidad Extendida', False),
    # Su expediente era de demostración: la reforma decidió eliminarlas del todo.
    ('fablab-impresion-3d', 'laboratorio-fabricacion-digital-prototipado',
     'la impresión 3D es un área del FabLab', True),
    ('bioinnovacion-aplicada', None, 'no consta en ningún inventario ni tiene carrera que lo reconozca', True),
)


def clasificacion(definicion):
    """Nivel A: plataforma compartida; con investigación: mixto; solo docencia: académico."""
    if definicion.get('nivel') == 'A':
        return 'plataforma_tecnologica'
    return 'laboratorio_mixto' if 'I' in definicion.get('tipo', '') else 'laboratorio_academico'


def carreras(definicion):
    titular = f"Titular: {definicion['titular']}"
    return f"{titular}. Usuarias: {definicion['usuarias']}." if definicion.get('usuarias') else f'{titular}.'


class Command(BaseCommand):
    help = 'Aplica la reforma de laboratorios: nombres oficiales, áreas y unidades que se integran.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría y no guarda nada.')

    @transaction.atomic
    def handle(self, *args, **options):
        self.creadas = self.renombradas = 0
        for definicion in LABORATORIOS:
            self._unidad({**definicion, 'dependencia': 'laboratorios'})
        for planta in PLANTAS:
            self._unidad({**planta, 'dependencia': 'plantas_piloto'})
        for centro in CENTROS:
            self._unidad(centro)
        for definicion in OBSERVATORIOS:
            self._unidad(definicion)
        for origen, destino, motivo, eliminar in INTEGRACIONES:
            self._integrar(origen, destino, motivo, eliminar)
        self.stdout.write(self.style.SUCCESS(
            f'{self.creadas} unidades creadas y {self.renombradas} actualizadas; '
            f'{Unidad.objects.filter(dependencia="laboratorios", activo=True).count()} laboratorios activos.'))
        if options['simular']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('Simulación: no se guardó nada.'))

    # ------------------------------------------------------------------ unidades
    def _buscar(self, definicion):
        slugs = [definicion['slug'], *definicion.get('anteriores', ())]
        unidades = {unidad.slug: unidad for unidad in Unidad.objects.filter(slug__in=slugs)}
        return next((unidades[slug] for slug in slugs if slug in unidades), None)

    def _unidad(self, definicion):
        unidad = self._buscar(definicion)
        nueva = unidad is None
        if nueva and 'descripcion' not in definicion:
            # Las plantas nacen con su propio cargador; aquí solo se renombran.
            self.stdout.write(f"Omitida: {definicion['nombre']} (no está registrada).")
            return
        if nueva:
            unidad = Unidad(slug=definicion['slug'], dependencia=definicion['dependencia'],
                            fecha_inicio=timezone.localdate(), descripcion=definicion['descripcion'],
                            # Una unidad propuesta nace «En creación»; su resolución la cambia desde el admin.
                            estado_catalogo=definicion.get('estado_catalogo', 'disponible'))
            self.creadas += 1
        else:
            self.renombradas += 1
            if unidad.slug != definicion['slug'] and not Unidad.objects.filter(slug=definicion['slug']).exists():
                unidad.slug = definicion['slug']
        anterior = unidad.nombre
        unidad.nombre = definicion['nombre']
        unidad.nombre_corto = definicion.get('corto', '')
        if definicion.get('resolucion'):
            unidad.resolucion_numero = definicion['resolucion']
        if 'area' in definicion:
            unidad.area_conocimiento = definicion['area']
            unidad.clasificacion_funcional = (Unidad.CLASIFICACION_PREDETERMINADA[definicion['dependencia']]
                                              if definicion['dependencia'] != 'laboratorios'
                                              else clasificacion(definicion))
            unidad.carreras = carreras(definicion)
            unidad.descripcion_corta = definicion['descripcion_corta']
            if definicion.get('ubicacion') or not unidad.ubicacion:
                unidad.ubicacion = definicion.get('ubicacion', '')
            # La descripción escrita a mano se respeta; la vacía o de relleno se reemplaza.
            if definicion.get('reescribir_descripcion') or len((unidad.descripcion or '').strip()) < 40:
                unidad.descripcion = definicion['descripcion']
        unidad.activo = True
        unidad.save()
        self._pestanas(unidad, definicion.get('tipo', ''))
        if definicion['dependencia'] == 'observatorios':
            self._sin_reservas(unidad)
            # Las categorías y el tipo de laboratorio que heredó el registro reutilizado no describen a un observatorio.
            unidad.categorias.clear()
            unidad.tipos_laboratorio.clear()
        self._tipos(unidad, definicion.get('tipo', ''))
        self._areas(unidad, definicion)
        self._responsables(unidad, definicion)
        accion = 'Creada' if nueva else ('Renombrada' if anterior != unidad.nombre else 'Al día')
        detalle = f' (antes «{anterior}»)' if not nueva and anterior != unidad.nombre else ''
        self.stdout.write(f'{accion}: {unidad.nombre}{detalle}')

    def _pestanas(self, unidad, letras=''):
        """Las pestañas del mapa de su tipo existen y se ven, en su orden; las ajenas al mapa se ocultan.

        La de investigación formativa solo se ve si el laboratorio investiga (o ya publicó en ella).
        """
        mapa = mapa_de(unidad)
        if mapa is None:
            return
        comunes = {clave: (nombre, icono, reservas)
                   for clave, nombre, icono, reservas in DEFAULT_MODULES_BY_DEPENDENCIA[mapa.tipo]}
        for orden, clave in enumerate(mapa.pestanas, start=1):
            nombre, icono, reservas = comunes[clave]
            modulo, _ = ModuloUnidad.objects.get_or_create(
                unidad=unidad, clave=clave,
                defaults={'nombre': nombre, 'icono': icono, 'orden': orden, 'mostrar_herramientas_reserva': reservas})
            activo = (clave != PESTANA_INVESTIGACION or 'I' in letras.split('+')
                      or modulo.carpetas.filter(activa=True).exists())
            # Las pestañas de un observatorio llevan el nombre de su mapa: no se personalizan.
            renombrar = mapa.tipo == 'observatorios' and modulo.nombre != nombre
            if modulo.activo != activo or modulo.orden != orden or renombrar:
                modulo.activo, modulo.orden, modulo.nombre = activo, orden, nombre if renombrar else modulo.nombre
                modulo.save()
        if mapa.tipo == 'observatorios':
            # El monitoreo se unió a los datos: lo publicado en la pestaña retirada pasa a «Datos y monitoreo».
            datos = ModuloUnidad.objects.get(unidad=unidad, clave='datos-indicadores')
            CarpetaRecurso.objects.filter(unidad=unidad, modulo_config__clave='monitoreo-alertas').update(
                modulo_config=datos, seccion_planta='')
        ModuloUnidad.objects.filter(unidad=unidad, activo=True).exclude(clave__in=list(mapa.pestanas)).update(activo=False)

    def _sin_reservas(self, unidad):
        """Un observatorio produce datos, no presta equipos: no ofrece la agenda de reservas, consumibles ni
        cotizaciones de un laboratorio, aunque tenga sala o equipos. Su sala se pide con una solicitud de datos y
        las visitas siguen como la unidad las configuró."""
        ConfiguracionOperativaUnidad.objects.update_or_create(unidad=unidad, defaults={
            'solicitudes_servicio': False, 'reservas_espacios': False, 'reservas_equipos': False,
            'consumibles': False, 'cotizacion_costos': False})

    def _tipos(self, unidad, letras):
        for letra in letras.split('+'):
            tipo = TipoLaboratorio.objects.filter(nombre=TIPOS.get(letra, '')).first()
            if tipo:
                unidad.tipos_laboratorio.add(tipo)

    def _areas(self, unidad, definicion):
        for orden, area in enumerate(definicion.get('areas', ()), start=1):
            sufijo, nombre, tipo, capacidad, *resto = area
            extra = resto[0] if resto else {}
            futura = extra.get('futura', False)
            espacio, creado = EspacioReservable.objects.get_or_create(
                unidad=unidad, codigo=f"{definicion['prefijo']}-{sufijo}",
                defaults={'nombre': nombre, 'tipo': tipo, 'capacidad': capacidad,
                          'politica_reserva': POLITICA_POR_TIPO.get(tipo, 'mixto'),
                          'ubicacion': extra.get('ubicacion', ''),
                          'descripcion_publica': DESCRIPCION_DE_FUTURA if futura else ''})
            espacio.nombre, espacio.tipo, espacio.orden = nombre, tipo, orden
            if futura:
                espacio.activo = espacio.reservable = False
            elif creado:
                espacio.activo = espacio.reservable = True
            # Lo que abarca el área va en su descripción mientras la unidad no haya escrito la suya.
            alcance = ALCANCE_DE_AREAS.get(espacio.codigo, '')
            if alcance and espacio.descripcion_publica.strip() in ('', DESCRIPCION_DE_FUTURA):
                espacio.descripcion_publica = f'{alcance}. {DESCRIPCION_DE_FUTURA}' if futura else f'{alcance}.'
            espacio.save()
            # Un área nueva toma, la primera vez, los equipos de la unidad que ya sirven a su campo.
            if extra.get('equipos') and not espacio.equipos_asociados.exists():
                filtro = Q()
                for nombre_equipo in extra['equipos']:
                    filtro |= Q(equipo__nombre__icontains=nombre_equipo)
                espacio.equipos_asociados.add(*UnidadEquipo.objects.filter(
                    Q(laboratorio=unidad) | Q(laboratorios=unidad), filtro, activa=True).distinct())
            # Las áreas que esta reúne le pasan sus equipos, ficha, fotos, reservas y procesos, y quedan inactivas.
            for absorbida in extra.get('absorbe', ()):
                origen = EspacioReservable.objects.filter(
                    unidad=unidad, codigo=f"{definicion['prefijo']}-{absorbida}").first()
                if origen is None or (origen.integrada_en_id == espacio.pk and not origen.activo
                                      and not origen.equipos_asociados.exists()):
                    continue
                trasladado = fusionar_area(origen, espacio)
                detalle = ', '.join(f'{cantidad} {nombre}' for nombre, cantidad in trasladado.items()) or 'sin contenido'
                self.stdout.write(f'  Fusionada: {origen.nombre} en {espacio.nombre} ({detalle})')

    def _responsables(self, unidad, definicion):
        # Solo cuando la unidad no tiene a nadie: no se mezcla con lo que ya registró.
        if not definicion.get('responsables') or ResponsableUnidad.objects.filter(unidad=unidad).exists():
            return
        for orden, persona in enumerate(definicion['responsables'], start=1):
            nombre, descripcion = persona if isinstance(persona, tuple) else (persona, '')
            ResponsableUnidad.objects.create(
                unidad=unidad, nombre=nombre, rol='coordinacion', orden=orden,
                descripcion=descripcion or 'Responsable según el inventario de laboratorios (15/5/2025).')

    # ------------------------------------------------------------------ integraciones
    def _integrar(self, slug_origen, slug_destino, motivo, eliminar):
        origen = Unidad.objects.filter(slug=slug_origen).first()
        if origen is None:
            return
        destino = Unidad.objects.filter(slug=slug_destino).first() if slug_destino else None
        if destino is not None:
            movidos = UnidadEquipo.objects.filter(laboratorio=origen).update(laboratorio=destino)
            for espacio in EspacioReservable.objects.filter(unidad=origen):
                if EspacioReservable.objects.filter(unidad=destino, codigo=espacio.codigo).exists():
                    espacio.codigo = f'{espacio.codigo}-{origen.pk}'
                espacio.unidad = destino
                espacio.save()
            if movidos:
                self.stdout.write(f'  {movidos} equipos de «{origen.nombre}» pasan a «{destino.nombre}».')
        documentos = Recurso.objects.filter(unidad=origen).count()
        tiene_historial = documentos or Reserva.objects.filter(laboratorio=origen).exists()
        if tiene_historial and not eliminar:
            return self._desactivar(origen, f'{motivo}; conserva su historial')
        nombre = origen.nombre
        try:
            with transaction.atomic():
                # La auditoría sobrevive a la unidad: el histórico queda con su nombre y esta última entrada.
                registrar_auditoria(
                    None, unidad=origen, accion='eliminar', objeto=origen,
                    descripcion=f'Unidad eliminada por la reforma: {motivo}'[:255],
                    anteriores={'nombre': origen.nombre, 'slug': origen.slug, 'dependencia': origen.dependencia},
                )
                origen.delete()
        except ProtectedError as error:
            # Desechos, movimientos financieros o informes de mejora son registros que no se borran con la unidad.
            protegen = Counter(str(obj._meta.verbose_name_plural).lower() for obj in error.protected_objects)
            detalle = ', '.join(f'{total} {nombre_modelo}' for nombre_modelo, total in protegen.items())
            return self._desactivar(origen, f'{motivo}; no se puede eliminar porque la protegen {detalle}')
        historial = f'; se borraron sus {documentos} documentos' if documentos else '; no tenía historial'
        self.stdout.write(f'Eliminada: {nombre} ({motivo}{historial}).')

    def _desactivar(self, unidad, detalle):
        unidad.activo = False
        unidad.save(update_fields=['activo'])
        self.stdout.write(f'Desactivada: {unidad.nombre} ({detalle}).')
