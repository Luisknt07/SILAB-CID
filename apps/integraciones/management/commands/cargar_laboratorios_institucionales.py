"""Deja listos para reservar tres laboratorios más allá del FabLab.

El FabLab ya prueba la fabricación: piezas, materiales por equipo y servicios
con archivo. Estos tres ejercitan lo que aquel no toca.

* **IA y Ciencia de Datos** es una sala de cómputo: licencias concurrentes,
  puestos con cupo compartido y reservas que no consumen material.
* **Biotecnología Aplicada** es un laboratorio húmedo: reactivos con lote y
  vencimiento, áreas técnicas con inducción y prácticas docentes por grupo.
* **Emprendimiento e Innovación Empresarial** atiende a las carreras
  administrativas: su oferta son salas, mentorías y licencias en la nube, casi
  sin máquinas, y trabaja hasta las 20:00.
* **Planta Piloto de Lácteos** es la primera planta: produce lotes en líneas
  de proceso, con leche cruda de tres días de vida, cultivos, cuajo, reactivos
  de control de calidad, empaque y limpieza de inocuidad. Declara lo que
  produce (leche pasteurizada, yogur, queso fresco, mozzarella, semimaduro,
  mantequilla, manjar y crema, con suero, mazada, leche descremada y
  residuos) con sus recetas por etapas y el software de cada proceso, para
  que las órdenes de producción descuenten insumos y creen lotes.

La carga es idempotente: puede repetirse sin duplicar registros.
"""

from datetime import date, time as hora_del_dia, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.presentation.codigos_sistema import actualizar_o_crear, modelo_vigente, unidad_vigente
from apps.gestion_unidades.presentation.permisos import MODULOS_OPERATIVOS
from apps.plantas_piloto.operacion.presentation.derivacion_procesos import derivar_procesos
from apps.gestion_unidades.presentation.fusion_areas import area_vigente, integrada
from apps.documentos.presentation.guias_referencia import crear_guias_de_referencia
from apps.plantas_piloto.operacion.management.plantas import PLANTAS
from apps.plantas_piloto.operacion.management.plantas.ampliacion import AMPLIACIONES, ampliar
from apps.plantas_piloto.operacion.management.plantas.cadena_frio import temperatura_de_conservacion
from apps.plantas_piloto.operacion.management.plantas.catalogo_fichas import FICHAS
from apps.plantas_piloto.operacion.management.plantas.costos_referencia import COSTO_HORA_PERSONA, TARIFA_ENERGIA_KWH
from apps.plantas_piloto.operacion.management.plantas.especificaciones import ESPECIFICACIONES
from apps.plantas_piloto.operacion.management.plantas.referencia_equipos import datos_de_referencia
from apps.plantas_piloto.operacion.management.plantas.taxonomia import PRODUCTOS_TAXONOMIA, TAXONOMIA_FAMILIAS
from apps.plantas_piloto.operacion.presentation.maquila import sincronizar_insumos_del_proceso
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, LoteConsumible
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, InsumoReceta, Producto, Receta, SalidaReceta
from apps.laboratorios.operacion.models.fablab import FablabService, FablabServiceConsumible
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.plantas_piloto.operacion.models.calidad import ParametroCalidad, PlanCalidad
from apps.core.models.periodos import PeriodoAcademico
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile

IA = {
    'slug': 'laboratorio-inteligencia-artificial-ciencia-datos',
    'prefijo': 'IA',
    'capacidad_personas': 24,
    'horario_atencion': ('08:00', '18:00'),
    'unidad_de_trabajo': 'ensayos',
    'equipos': [
        {
            'codigo': 'IA-EQ-GPU',
            'nombre': 'Estación de trabajo con GPU',
            'categoria_codigo': 'IA-COMPUTO',
            'categoria': 'Cómputo de alto rendimiento',
            'icono': '🖥️',
            'unidades': ['IA-UNIT-GPU-01', 'IA-UNIT-GPU-02', 'IA-UNIT-GPU-03'],
            'descripcion': (
                'Puesto de trabajo con tarjeta gráfica dedicada para entrenar y '
                'evaluar modelos de aprendizaje automático.'
            ),
            'caracteristicas_publicas': (
                'Procesador de escritorio, 32 GB de memoria y GPU dedicada para '
                'entrenamiento y visualización de datos.'
            ),
            'uso_publico': (
                'Entrenamiento de modelos, análisis exploratorio y visualización '
                'de conjuntos de datos grandes.'
            ),
            'instrucciones_publicas': (
                'Trae tu conjunto de datos y el cuaderno de trabajo. El puesto se '
                'entrega con el entorno de Python del laboratorio.'
            ),
            'software': 'Entorno de análisis instalado por el laboratorio',
            'accesorios': ['Monitor adicional', 'Teclado y ratón', 'Auriculares'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de cómputo A',
        },
        {
            'codigo': 'IA-EQ-SERVIDOR',
            'nombre': 'Servidor de entrenamiento',
            'categoria_codigo': 'IA-COMPUTO',
            'categoria': 'Cómputo de alto rendimiento',
            'icono': '🗄️',
            'unidades': ['IA-UNIT-SRV-01'],
            'descripcion': (
                'Servidor compartido para trabajos de entrenamiento largos que no '
                'caben en una estación de escritorio.'
            ),
            'caracteristicas_publicas': (
                'Dos GPU de cómputo, 128 GB de memoria y almacenamiento rápido '
                'para conjuntos de datos de gran tamaño.'
            ),
            'uso_publico': (
                'Entrenamientos que superan las horas de una sesión o que exigen '
                'más memoria que un puesto de escritorio.'
            ),
            'instrucciones_publicas': (
                'Indica el tamaño del conjunto de datos y las horas estimadas: el '
                'laboratorio confirma la ventana y prepara el acceso remoto.'
            ),
            'software': 'Acceso remoto con las herramientas del laboratorio',
            'accesorios': ['Acceso remoto', 'Almacenamiento temporal'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Rack del laboratorio',
        },
        {
            'codigo': 'IA-EQ-ETIQUETADO',
            'nombre': 'Puesto de etiquetado de datos',
            'categoria_codigo': 'IA-ANALISIS',
            'categoria': 'Puestos de análisis',
            'icono': '🏷️',
            'unidades': ['IA-UNIT-ETQ-01', 'IA-UNIT-ETQ-02', 'IA-UNIT-ETQ-03', 'IA-UNIT-ETQ-04'],
            'descripcion': (
                'Puesto para preparar, depurar y etiquetar conjuntos de datos '
                'antes de entrenar un modelo.'
            ),
            'caracteristicas_publicas': (
                'Computador de escritorio con dos pantallas y las herramientas de '
                'etiquetado y limpieza del laboratorio.'
            ),
            'uso_publico': (
                'Depuración de datos, etiquetado de imágenes o texto y preparación '
                'de conjuntos para prácticas.'
            ),
            'instrucciones_publicas': (
                'Reserva un puesto por persona. Si la práctica es grupal, elige la '
                'sala de cómputo e indica cuántos puestos necesitas.'
            ),
            'software': 'Herramientas de etiquetado y ofimática de datos',
            'accesorios': ['Dos pantallas', 'Tableta de anotación'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de cómputo A',
        },
        {
            'codigo': 'IA-EQ-PIZARRA',
            'nombre': 'Pizarra interactiva',
            'categoria_codigo': 'IA-ANALISIS',
            'categoria': 'Puestos de análisis',
            'icono': '📊',
            'unidades': ['IA-UNIT-PIZ-01'],
            'descripcion': (
                'Pantalla interactiva para revisar resultados en grupo y conducir '
                'sesiones de analítica colaborativa.'
            ),
            'caracteristicas_publicas': (
                'Pantalla táctil de 75 pulgadas con lápiz, proyección inalámbrica '
                'y exportación de la sesión.'
            ),
            'uso_publico': (
                'Revisión de resultados, tutorías de proyectos y sesiones de '
                'análisis con el equipo de investigación.'
            ),
            'instrucciones_publicas': (
                'Se reserva junto con la sala de analítica. Requiere el archivo o '
                'el tablero que se va a proyectar.'
            ),
            'software': 'Proyección inalámbrica y anotación',
            'accesorios': ['Lápiz interactivo', 'Control de proyección'],
            'requiere_insumos': True,
            'insumos': 'Marcadores de pizarra cuando se usa la superficie blanca.',
            'ubicacion': 'Sala de analítica colaborativa',
        },
    ],
    'espacios': [
        {
            'codigo': 'IA-SALA-COMPUTO',
            'nombre': 'Sala de cómputo A',
            'tipo': 'sala',
            'ubicacion': 'Bloque de laboratorios, segundo piso',
            'capacidad': 20,
            'equipos_asociados': ['IA-EQ-GPU', 'IA-EQ-ETIQUETADO'],
            'politica_reserva': 'mixto',
            'mobiliario': 'Veinte puestos con computador, dos pantallas de apoyo y red cableada.',
            'descripcion': (
                'Sala con veinte puestos para prácticas de analítica, programación '
                'y entrenamiento de modelos.'
            ),
            'caracteristicas': (
                'Puestos individuales, red cableada, proyector y climatización '
                'para sesiones largas.'
            ),
            'instrucciones': (
                'Indica cuántos puestos necesitas: la sala se comparte por cupo y '
                'otra práctica puede ocupar el resto.'
            ),
        },
        {
            'codigo': 'IA-SALA-ANALITICA',
            'nombre': 'Sala de analítica colaborativa',
            'tipo': 'sala',
            'ubicacion': 'Bloque de laboratorios, segundo piso',
            'capacidad': 12,
            'equipos_asociados': ['IA-EQ-PIZARRA'],
            'politica_reserva': 'general',
            'mobiliario': 'Mesa para doce personas, pizarra interactiva y pizarra blanca.',
            'descripcion': (
                'Espacio de trabajo en grupo para revisar resultados, planificar '
                'proyectos y conducir tutorías.'
            ),
            'caracteristicas': (
                'Mesa de reuniones, pizarra interactiva, pizarra blanca y conexión '
                'para equipos portátiles.'
            ),
            'instrucciones': (
                'Puede reservarse sola, sin equipos del laboratorio, si solo '
                'necesitas el espacio de trabajo.'
            ),
        },
    ],
    'software': [
        {
            'codigo': 'IA-SW-MATLAB', 'nombre': 'MATLAB', 'version': 'R2026a',
            'tipo_recurso': 'licencia', 'tipo_acceso': 'red', 'licencias': 5,
            'descripcion': 'Cálculo numérico, análisis de señales y prototipado de algoritmos.',
            'instrucciones': 'Licencia concurrente de la Universidad: cinco personas a la vez.',
            'equipos_instalados': ['IA-EQ-GPU'],
        },
        {
            'codigo': 'IA-SW-SPSS', 'nombre': 'IBM SPSS Statistics', 'version': '30',
            'tipo_recurso': 'licencia', 'tipo_acceso': 'red', 'licencias': 3,
            'descripcion': 'Análisis estadístico para investigación y trabajos de titulación.',
            'instrucciones': 'Licencia concurrente: tres sesiones simultáneas como máximo.',
            'equipos_instalados': ['IA-EQ-ETIQUETADO'],
        },
        {
            'codigo': 'IA-SW-PYTHON', 'nombre': 'Entorno Python del laboratorio', 'version': '2026.1',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 20,
            'descripcion': 'Python con las bibliotecas de análisis y aprendizaje automático del laboratorio.',
            'instrucciones': 'Viene instalado en la estación: se incluye al reservar el equipo.',
            'equipos_instalados': ['IA-EQ-GPU'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'IA-SW-POWERBI', 'nombre': 'Power BI Desktop', 'version': '2026',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 20,
            'descripcion': 'Tableros y visualización de datos para informes institucionales.',
            'instrucciones': 'Instalado en los puestos de etiquetado y análisis.',
            'equipos_instalados': ['IA-EQ-ETIQUETADO'],
        },
    ],
    'consumibles': [
        {
            'codigo': 'IA-MAT-MARCADOR',
            'nombre': 'Marcador para pizarra blanca',
            'clasificacion': 'material',
            'familia': 'Material de trabajo',
            'variante': 'Punta gruesa',
            'color': 'Surtido',
            'presentacion': 'Cajas de cuatro colores',
            'cantidad_por_presentacion': Decimal('4'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('48'),
            'minimo': Decimal('12'),
            'precio_unitario': Decimal('0.90'),
            'descripcion': 'Marcadores para las sesiones de trabajo en la sala de analítica.',
            'instrucciones_solicitud': 'Indica cuántos necesitas para la sesión.',
            'ubicacion': 'Armario de la sala de analítica',
            'equipos': [],
        },
        {
            'codigo': 'IA-MAT-ETIQUETA',
            'nombre': 'Etiquetas adhesivas para medios de almacenamiento',
            'clasificacion': 'material',
            'familia': 'Material de trabajo',
            'variante': 'Hoja de 24 etiquetas',
            'color': 'Blanco',
            'presentacion': 'Paquetes de 10 hojas',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'hoja',
            'stock_total': Decimal('60'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('0.35'),
            'descripcion': 'Identificación de discos y medios que salen del laboratorio.',
            'instrucciones_solicitud': 'Una hoja alcanza para veinticuatro etiquetas.',
            'ubicacion': 'Armario de la sala de cómputo',
            'equipos': [],
        },
        {
            'codigo': 'IA-MAT-PAPEL',
            'nombre': 'Papel bond A4 para informes',
            'clasificacion': 'material',
            'familia': 'Material de trabajo',
            'variante': '75 g',
            'color': 'Blanco',
            'presentacion': 'Resmas de 500 hojas',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'hoja',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.02'),
            'descripcion': 'Impresión de resultados y tableros para revisión en mesa.',
            'instrucciones_solicitud': 'Calcula las hojas del informe que vas a imprimir.',
            'ubicacion': 'Armario de la sala de cómputo',
            'equipos': [],
        },
    ],
    'servicios': [
        {
            'code': 'IA-SRV-ENTRENAMIENTO',
            'familia': 'Analítica y modelos',
            'nombre': 'Entrenamiento de modelos en el servidor',
            'descripcion': (
                'El laboratorio prepara el entorno, ejecuta el entrenamiento en su '
                'servidor y entrega el modelo con sus métricas.'
            ),
            'resultado_entregado': (
                'Modelo entrenado, registro de métricas y cuaderno con los pasos '
                'reproducibles.'
            ),
            'cuando_elegirlo': (
                'Elígelo cuando el entrenamiento supera la capacidad de un puesto '
                'o necesitas dejarlo corriendo varias horas.'
            ),
            'tiempo_estimado_texto': '2 a 5 días laborables según el tamaño del conjunto',
            'tipo_servicio': 'analisis',
            'equipo': 'IA-EQ-SERVIDOR',
            'requiere_archivos': True,
            'requisitos_usuario': (
                'Entrega el conjunto de datos, la definición del problema y la '
                'métrica con la que se evaluará el resultado.'
            ),
            'formatos_archivo': 'CSV, Parquet, ZIP o cuaderno .ipynb',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '6.00', 'costo_equipo': '2.50',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '10.00', 'diseno_completo': '30.00',
            'consumibles': [],
        },
        {
            'code': 'IA-SRV-TABLERO',
            'familia': 'Analítica y modelos',
            'nombre': 'Tablero de indicadores a la medida',
            'descripcion': (
                'Construcción de un tablero de indicadores con los datos que '
                'entrega la dependencia o el proyecto solicitante.'
            ),
            'resultado_entregado': (
                'Tablero publicado, documento con la fuente de cada indicador y '
                'una sesión de entrega.'
            ),
            'cuando_elegirlo': (
                'Para informes periódicos, seguimiento de proyectos o rendición '
                'de cuentas con datos propios.'
            ),
            'tiempo_estimado_texto': '5 a 10 días laborables',
            'tipo_servicio': 'analisis',
            'equipo': 'IA-EQ-ETIQUETADO',
            'requiere_archivos': True,
            'requisitos_usuario': (
                'Entrega los datos en hoja de cálculo o base de datos e indica qué '
                'preguntas debe responder el tablero.'
            ),
            'formatos_archivo': 'XLSX, CSV o acceso a la base de datos',
            'permite_modelo_listo': False,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '2.00', 'costo_equipo': '1.50',
            'horas_mano_obra': '6.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '12.00', 'diseno_completo': '40.00',
            'consumibles': [('IA-MAT-PAPEL', '40.000', False)],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Paola Chamorro',
            'rol': 'coordinacion',
            'email': 'ia.datos@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2810',
            'descripcion': 'Coordina la agenda del laboratorio, las licencias y la asignación de puestos.',
            'horario_atencion': 'Lunes a viernes · 08:00–18:00',
            'orden': 1,
        },
        {
            'nombre': 'Ing. Marco Villarreal',
            'rol': 'responsable_tecnico',
            'email': 'soporte.ia@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2811',
            'descripcion': 'Acompaña el uso del servidor, los entornos de trabajo y la preparación de datos.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.ia',
            'nombres': 'Paola',
            'apellidos': 'Chamorro',
            'email': 'coordinacion.ia@citt.test',
            'cargo': 'Coordinación del Laboratorio de IA y Ciencia de Datos',
            'rol': 'coordinacion',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.ia',
            'nombres': 'Marco',
            'apellidos': 'Villarreal',
            'email': 'laboratorista.ia@citt.test',
            'cargo': 'Laboratorista de IA y Ciencia de Datos',
            'rol': 'laboratorista',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'inventario': True, 'practicas': True,
            },
        },
    ],
    'ejemplos': [
        {
            'proposito': 'servicio',
            'ejemplo': (
                'Necesito que el laboratorio entrene y evalúe el modelo de '
                'clasificación de mi proyecto con el conjunto de datos que '
                'entrego. Son unos ochenta mil registros ya depurados, con la '
                'variable objetivo marcada. Pido que se prueben al menos tres '
                'algoritmos y que el informe compare la exactitud y la matriz '
                'de confusión de cada uno. El conjunto contiene información de '
                'personas, así que lo entrego en un medio cifrado y necesito '
                'que se elimine del servidor cuando se cierre el trabajo.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de sexto semestre de Minería de Datos haremos la '
                'práctica de árboles de decisión. Cada estudiante ocupará un '
                'puesto de etiquetado para depurar el conjunto de datos de la '
                'asignatura y entrenará su modelo en la estación. Buscamos que '
                'interpreten la matriz de confusión y expliquen por qué un '
                'modelo con buena exactitud puede ser inservible. Somos veinte; '
                'necesitamos la sala de cómputo dos horas por sesión durante '
                'cuatro semanas y las tres licencias de SPSS se turnarán por '
                'grupos en la primera hora.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de detección de plagas por imágenes '
                'necesitamos el servidor de entrenamiento durante dos sesiones '
                'de tres horas. Somos dos investigadores; traemos el conjunto '
                'de imágenes ya etiquetado y el cuaderno de trabajo. '
                'Entrenaremos tres variantes del modelo y compararemos su '
                'desempeño; al terminar dejaremos registrados los tiempos de '
                'cómputo y el resultado de cada corrida.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación necesito una estación con GPU '
                'durante dos sesiones de tres horas y la licencia de MATLAB '
                'para el procesamiento de señales. Traigo mi conjunto de datos '
                'y el cuaderno con el preprocesamiento resuelto. En la primera '
                'sesión ajustaré los parámetros y en la segunda ejecutaré los '
                'ensayos definitivos que sustentan mi capítulo de resultados.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'IA-ACT-APRENDIZAJE',
            'nombre': 'Práctica de aprendizaje automático',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Inteligencia Artificial',
        },
        {
            'codigo': 'IA-ACT-TITULACION',
            'nombre': 'Trabajo de titulación con datos institucionales',
            'proposito_codigo': 'titulacion',
            'subtipo_actividad': 'trabajo_titulacion',
            'responsable': 'Tutor del trabajo de titulación',
        },
    ],
}

BIOTECNOLOGIA = {
    'slug': 'laboratorio-microbiologia-biotecnologia-aplicada',
    'prefijo': 'BIO',
    'capacidad_personas': 18,
    'horario_atencion': ('07:00', '18:00'),
    'unidad_de_trabajo': 'muestras',
    'equipos': [
        {
            'codigo': 'BIO-EQ-AUTOCLAVE',
            'nombre': 'Autoclave de laboratorio',
            'categoria_codigo': 'BIO-ESTERIL',
            'categoria': 'Esterilización y preparación',
            'icono': '♨️',
            'unidades': ['BIO-UNIT-AUT-01'],
            'descripcion': (
                'Esteriliza medios de cultivo, material de vidrio y desechos '
                'biológicos antes de su disposición.'
            ),
            'caracteristicas_publicas': (
                'Cámara de 50 litros, ciclos programables de esterilización y '
                'registro de temperatura y presión.'
            ),
            'uso_publico': (
                'Preparación de medios, esterilización de material y tratamiento '
                'de residuos biológicos.'
            ),
            'instrucciones_publicas': (
                'Requiere inducción previa. Indica el volumen y el tipo de carga '
                'para programar el ciclo correcto.'
            ),
            'software': '',
            'accesorios': ['Canastillas', 'Indicadores de esterilidad'],
            'requiere_insumos': True,
            'insumos': 'Cinta indicadora y agua destilada.',
            'ubicacion': 'Área de preparación de medios',
        },
        {
            'codigo': 'BIO-EQ-CABINA',
            'nombre': 'Cabina de flujo laminar',
            'categoria_codigo': 'BIO-CULTIVO',
            'categoria': 'Cultivo y manipulación estéril',
            'icono': '🧫',
            'unidades': ['BIO-UNIT-CAB-01', 'BIO-UNIT-CAB-02'],
            'descripcion': (
                'Área estéril para sembrar, repicar y manipular cultivos sin '
                'contaminar la muestra ni al operador.'
            ),
            'caracteristicas_publicas': (
                'Flujo laminar vertical con filtro HEPA, lámpara ultravioleta y '
                'superficie de trabajo en acero inoxidable.'
            ),
            'uso_publico': (
                'Siembra y repique de cultivos, preparación de muestras estériles '
                'y manipulación de cepas autorizadas.'
            ),
            'instrucciones_publicas': (
                'Reserva quince minutos adicionales para el encendido de la '
                'lámpara y la desinfección de la superficie.'
            ),
            'software': '',
            'accesorios': ['Mechero de seguridad', 'Gradilla', 'Lámpara ultravioleta'],
            'requiere_insumos': True,
            'insumos': 'Etanol al 96 %, guantes y puntas estériles.',
            'ubicacion': 'Área de cultivo celular',
        },
        {
            'codigo': 'BIO-EQ-TERMOCICLADOR',
            'nombre': 'Termociclador para PCR',
            'categoria_codigo': 'BIO-MOLECULAR',
            'categoria': 'Biología molecular',
            'icono': '🧬',
            'unidades': ['BIO-UNIT-PCR-01'],
            'descripcion': (
                'Amplifica fragmentos de ADN mediante reacción en cadena de la '
                'polimerasa con programas configurables.'
            ),
            'caracteristicas_publicas': (
                'Bloque para 96 pozos, tapa calefactada y programas guardados por '
                'el laboratorio.'
            ),
            'uso_publico': (
                'Amplificación de ADN para prácticas de biología molecular, '
                'investigación y trabajos de titulación.'
            ),
            'instrucciones_publicas': (
                'Indica el programa y el número de muestras. La mezcla se prepara '
                'antes en la cabina de flujo laminar.'
            ),
            'software': '',
            'accesorios': ['Gradilla para tubos', 'Tapa calefactada'],
            'requiere_insumos': True,
            'insumos': 'Kit de amplificación, puntas y tubos de 0,2 mL.',
            'ubicacion': 'Área de biología molecular',
        },
        {
            'codigo': 'BIO-EQ-CENTRIFUGA',
            'nombre': 'Centrífuga refrigerada',
            'categoria_codigo': 'BIO-MOLECULAR',
            'categoria': 'Biología molecular',
            'icono': '🌀',
            'unidades': ['BIO-UNIT-CEN-01'],
            'descripcion': (
                'Separa componentes de una muestra por densidad manteniendo la '
                'temperatura de trabajo.'
            ),
            'caracteristicas_publicas': (
                'Rotor para tubos de 1,5 y 15 mL, refrigeración de 4 °C y control '
                'de velocidad y tiempo.'
            ),
            'uso_publico': (
                'Separación de fases, lavado de células y preparación de extractos '
                'para análisis.'
            ),
            'instrucciones_publicas': (
                'Equilibra siempre los tubos por peso e indica la velocidad y el '
                'tiempo que necesita tu protocolo.'
            ),
            'software': '',
            'accesorios': ['Rotor de ángulo fijo', 'Adaptadores de tubo'],
            'requiere_insumos': True,
            'insumos': 'Tubos de 1,5 mL y guantes.',
            'ubicacion': 'Área de biología molecular',
        },
        {
            'codigo': 'BIO-EQ-ESPECTRO',
            'nombre': 'Espectrofotómetro de microvolumen',
            'categoria_codigo': 'BIO-MOLECULAR',
            'categoria': 'Biología molecular',
            'icono': '🔬',
            'unidades': ['BIO-UNIT-ESP-01'],
            'descripcion': (
                'Mide concentración y pureza de ácidos nucleicos y proteínas con '
                'volúmenes de un microlitro.'
            ),
            'caracteristicas_publicas': (
                'Lectura de 1 µL, curvas de absorbancia y registro exportable de '
                'cada medición.'
            ),
            'uso_publico': (
                'Cuantificación de ADN y proteínas antes de una amplificación o '
                'un ensayo.'
            ),
            'instrucciones_publicas': (
                'Trae las muestras en tubos rotulados. La medición toma pocos '
                'minutos por muestra.'
            ),
            'software': '',
            'accesorios': ['Pedestal de lectura', 'Papel libre de pelusa'],
            'requiere_insumos': True,
            'insumos': 'Agua libre de nucleasas y puntas de 10 µL.',
            'ubicacion': 'Área de biología molecular',
        },
        {
            'codigo': 'BIO-EQ-INCUBADORA',
            'nombre': 'Incubadora con agitación',
            'categoria_codigo': 'BIO-CULTIVO',
            'categoria': 'Cultivo y manipulación estéril',
            'icono': '🌡️',
            'unidades': ['BIO-UNIT-INC-01'],
            'descripcion': (
                'Mantiene cultivos a temperatura y agitación constantes durante '
                'el tiempo que exige el protocolo.'
            ),
            'caracteristicas_publicas': (
                'Rango de 20 a 60 °C, agitación orbital regulable y capacidad para '
                'veinte matraces.'
            ),
            'uso_publico': (
                'Crecimiento de cultivos bacterianos y ensayos de fermentación a '
                'pequeña escala.'
            ),
            'instrucciones_publicas': (
                'Indica temperatura, agitación y duración: si supera la jornada, '
                'el laboratorio custodia el cultivo.'
            ),
            'software': '',
            'accesorios': ['Pinzas para matraz', 'Bandeja orbital'],
            'requiere_insumos': True,
            'insumos': 'Medio de cultivo y matraces estériles.',
            'ubicacion': 'Área de cultivo celular',
        },
        {
            'codigo': 'BIO-EQ-BALANZA',
            'nombre': 'Balanza analítica',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '⚖️',
            'rol': 'auxiliar',
            'apoya_a': ['BIO-EQ-TERMOCICLADOR', 'BIO-EQ-ESPECTRO', 'BIO-EQ-AUTOCLAVE'],
            'unidades': ['BIO-UNIT-BAL-01'],
            'descripcion': (
                'Balanza de precisión para pesar reactivos y preparar medios y '
                'soluciones antes de cada ensayo.'
            ),
            'caracteristicas_publicas': (
                'Precisión de una décima de miligramo, cabina antiviento y '
                'calibración interna.'
            ),
            'uso_publico': (
                'Pesaje de reactivos y preparación de medios. Acompaña a los '
                'equipos del área molecular y al autoclave.'
            ),
            'instrucciones_publicas': (
                'No se reserva aparte: está disponible junto al equipo principal '
                'que reserves.'
            ),
            'software': 'No requiere programas del laboratorio',
            'accesorios': ['Pesas de calibración', 'Pinzas', 'Espátulas'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Mesón de preparación de medios',
        },
        {
            'codigo': 'BIO-EQ-PHMETRO',
            'nombre': 'Medidor de pH de mesa',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '🧪',
            'rol': 'auxiliar',
            'apoya_a': ['BIO-EQ-AUTOCLAVE', 'BIO-EQ-INCUBADORA'],
            'unidades': ['BIO-UNIT-PH-01'],
            'descripcion': (
                'Medidor de pH con electrodo de vidrio para ajustar medios de '
                'cultivo y soluciones.'
            ),
            'caracteristicas_publicas': (
                'Electrodo combinado, compensación de temperatura y calibración '
                'en tres puntos.'
            ),
            'uso_publico': 'Ajuste del pH de medios y soluciones antes de esterilizar o sembrar.',
            'instrucciones_publicas': (
                'No se reserva aparte: acompaña al autoclave y a la incubadora.'
            ),
            'software': 'No requiere programas del laboratorio',
            'accesorios': ['Soluciones de calibración', 'Electrodo de repuesto'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Mesón de preparación de medios',
        },
    ],
    'espacios': [
        {
            'codigo': 'BIO-AREA-MOLECULAR',
            'nombre': 'Área de biología molecular',
            'tipo': 'area',
            'ubicacion': 'Laboratorio de Biotecnología, zona limpia',
            'capacidad': 8,
            'equipos_asociados': ['BIO-EQ-TERMOCICLADOR', 'BIO-EQ-CENTRIFUGA', 'BIO-EQ-ESPECTRO'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Mesones con tomas eléctricas, gradillas, congelador de reactivos y lavabo.',
            'descripcion': (
                'Zona destinada a extracción, amplificación y cuantificación de '
                'ácidos nucleicos.'
            ),
            'caracteristicas': (
                'Mesones separados para preparación y amplificación, congelador de '
                'reactivos y control de acceso.'
            ),
            'instrucciones': (
                'Exige inducción de bioseguridad y el uso de bata, guantes y '
                'gafas durante toda la práctica.'
            ),
        },
        {
            'codigo': 'BIO-AREA-CULTIVO',
            'nombre': 'Área de cultivo celular',
            'tipo': 'area',
            'ubicacion': 'Laboratorio de Biotecnología, zona estéril',
            'capacidad': 6,
            'equipos_asociados': ['BIO-EQ-CABINA', 'BIO-EQ-INCUBADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Cabinas de flujo laminar, incubadora, refrigerador de medios y mesón de apoyo.',
            'descripcion': (
                'Zona estéril para siembra, repique y mantenimiento de cultivos '
                'bajo condiciones controladas.'
            ),
            'caracteristicas': (
                'Acceso restringido, presión controlada y protocolos de limpieza '
                'antes y después de cada sesión.'
            ),
            'instrucciones': (
                'Solo con inducción vigente. Programa el tiempo de desinfección '
                'dentro de tu reserva.'
            ),
        },
        {
            'codigo': 'BIO-MESON-PREPARACION',
            'nombre': 'Mesón de preparación de medios',
            'tipo': 'area',
            'ubicacion': 'Laboratorio de Biotecnología, zona de preparación',
            'capacidad': 10,
            'equipos_asociados': ['BIO-EQ-AUTOCLAVE'],
            'politica_reserva': 'mixto',
            'mobiliario': 'Mesones amplios, balanza, agitadores, fregadero y almacenamiento de vidriería.',
            'descripcion': (
                'Espacio para pesar reactivos, preparar medios y organizar el '
                'material que se esteriliza.'
            ),
            'caracteristicas': (
                'Balanza analítica, agitadores magnéticos, vidriería y acceso '
                'directo al autoclave.'
            ),
            'instrucciones': (
                'Puede reservarse para prácticas de preparación sin operar equipos '
                'mayores, con la inducción básica del laboratorio.'
            ),
        },
    ],
    'software': [
        {
            'codigo': 'BIO-SW-IMAGEJ', 'nombre': 'ImageJ', 'version': '1.54',
            'tipo_recurso': 'software', 'tipo_acceso': 'instalacion', 'licencias': 5,
            'descripcion': 'Análisis de imágenes de geles, conteo celular y medición morfométrica.',
            'instrucciones': 'Instalado en el puesto de documentación del área molecular.',
            'equipos_instalados': ['BIO-EQ-ESPECTRO'],
        },
    ],
    'consumibles': [
        {
            'codigo': 'BIO-REA-AGAR',
            'nombre': 'Agar nutritivo deshidratado',
            'clasificacion': 'reactivo',
            'familia': 'Medios de cultivo',
            'variante': 'Frasco de 500 g',
            'color': '',
            'presentacion': 'Frascos de 500 g',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'g',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.18'),
            'descripcion': 'Base para preparar medios sólidos de cultivo bacteriano.',
            'instrucciones_solicitud': 'Calcula los gramos según el volumen de medio que vas a preparar.',
            'ubicacion': 'Estante de medios, zona de preparación',
            'equipos': ['BIO-EQ-AUTOCLAVE'],
            'lotes': [
                {'codigo': 'BIO-AGAR-L1', 'cantidad': Decimal('1000'), 'vence_en_dias': 420, 'estado': 'bodega'},
                {'codigo': 'BIO-AGAR-L2', 'cantidad': Decimal('500'), 'vence_en_dias': 180, 'estado': 'en_uso',
                 'equipo': 'BIO-UNIT-AUT-01'},
            ],
        },
        {
            'codigo': 'BIO-REA-CALDO',
            'nombre': 'Caldo Luria-Bertani',
            'clasificacion': 'reactivo',
            'familia': 'Medios de cultivo',
            'variante': 'Frasco de 500 g',
            'color': '',
            'presentacion': 'Frascos de 500 g',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'g',
            'stock_total': Decimal('1000'),
            'minimo': Decimal('200'),
            'precio_unitario': Decimal('0.21'),
            'descripcion': 'Medio líquido para crecimiento de cultivos bacterianos.',
            'instrucciones_solicitud': 'Veinticinco gramos rinden un litro de medio.',
            'ubicacion': 'Estante de medios, zona de preparación',
            'equipos': ['BIO-EQ-INCUBADORA'],
            'lotes': [
                {'codigo': 'BIO-CALDO-L1', 'cantidad': Decimal('1000'), 'vence_en_dias': 365, 'estado': 'bodega'},
            ],
        },
        {
            'codigo': 'BIO-REA-ETANOL',
            'nombre': 'Etanol al 96 %',
            'clasificacion': 'reactivo',
            'familia': 'Reactivos de desinfección',
            'variante': 'Grado técnico',
            'color': '',
            'presentacion': 'Garrafas de 4 L',
            'cantidad_por_presentacion': Decimal('4000'),
            'unidad_medida': 'mL',
            'stock_total': Decimal('8000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.004'),
            'descripcion': 'Desinfección de superficies y material en las áreas estériles.',
            'instrucciones_solicitud': 'Indica los mililitros que consumirá la sesión.',
            'ubicacion': 'Armario de inflamables',
            'equipos': ['BIO-EQ-CABINA'],
            'lotes': [
                {'codigo': 'BIO-ETOH-L1', 'cantidad': Decimal('4000'), 'vence_en_dias': 540, 'estado': 'en_uso',
                 'equipo': 'BIO-UNIT-CAB-01'},
                {'codigo': 'BIO-ETOH-L2', 'cantidad': Decimal('4000'), 'vence_en_dias': 720, 'estado': 'bodega'},
            ],
        },
        {
            'codigo': 'BIO-MAT-GUANTES',
            'nombre': 'Guantes de nitrilo talla M',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Talla M',
            'color': 'Azul',
            'presentacion': 'Cajas de 100 unidades',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'par',
            'stock_total': Decimal('400'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.12'),
            'descripcion': 'Protección obligatoria en las áreas de cultivo y molecular.',
            'instrucciones_solicitud': 'Un par por persona y cambio en cada procedimiento estéril.',
            'ubicacion': 'Estante de protección personal',
            'equipos': ['BIO-EQ-CABINA', 'BIO-EQ-CENTRIFUGA'],
            'lotes': [],
        },
        {
            'codigo': 'BIO-MAT-PUNTAS',
            'nombre': 'Puntas para micropipeta de 200 µL',
            'clasificacion': 'material',
            'familia': 'Material fungible',
            'variante': 'Estériles con filtro',
            'color': '',
            'presentacion': 'Racks de 96 puntas',
            'cantidad_por_presentacion': Decimal('96'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('960'),
            'minimo': Decimal('192'),
            'precio_unitario': Decimal('0.06'),
            'descripcion': 'Puntas estériles con filtro para trabajo con ácidos nucleicos.',
            'instrucciones_solicitud': 'Calcula una punta por muestra y por reactivo dispensado.',
            'ubicacion': 'Estante de material estéril',
            'equipos': ['BIO-EQ-TERMOCICLADOR', 'BIO-EQ-ESPECTRO'],
            'lotes': [
                {'codigo': 'BIO-PUNTAS-L1', 'cantidad': Decimal('960'), 'vence_en_dias': 900, 'estado': 'en_uso',
                 'equipo': 'BIO-UNIT-PCR-01'},
            ],
        },
        {
            'codigo': 'BIO-MAT-TUBOS',
            'nombre': 'Tubos de microcentrífuga de 1,5 mL',
            'clasificacion': 'material',
            'familia': 'Material fungible',
            'variante': 'Libres de nucleasas',
            'color': 'Transparente',
            'presentacion': 'Bolsas de 500 unidades',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Tubos para separación, almacenamiento y transporte de muestras.',
            'instrucciones_solicitud': 'Indica cuántos tubos usará cada muestra del protocolo.',
            'ubicacion': 'Estante de material estéril',
            'equipos': ['BIO-EQ-CENTRIFUGA'],
            'lotes': [],
        },
        {
            'codigo': 'BIO-REA-KIT-ADN',
            'nombre': 'Kit de extracción de ADN genómico',
            'clasificacion': 'reactivo',
            'familia': 'Reactivos de biología molecular',
            'variante': '50 reacciones',
            'color': '',
            'presentacion': 'Cajas de 50 reacciones',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'reacción',
            'stock_total': Decimal('100'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('3.40'),
            'descripcion': 'Kit comercial para obtener ADN genómico a partir de cultivos o tejidos.',
            'instrucciones_solicitud': 'Una reacción por muestra; considera un control por tanda.',
            'ubicacion': 'Congelador de reactivos, área molecular',
            'equipos': ['BIO-EQ-ESPECTRO', 'BIO-EQ-CENTRIFUGA'],
            'lotes': [
                {'codigo': 'BIO-KIT-L1', 'cantidad': Decimal('50'), 'vence_en_dias': 150, 'estado': 'en_uso',
                 'equipo': 'BIO-UNIT-CEN-01'},
                {'codigo': 'BIO-KIT-L2', 'cantidad': Decimal('50'), 'vence_en_dias': 320, 'estado': 'bodega'},
            ],
        },
        {
            'codigo': 'BIO-REA-AGAROSA',
            'nombre': 'Agarosa para electroforesis',
            'clasificacion': 'reactivo',
            'familia': 'Reactivos de biología molecular',
            'variante': 'Grado molecular',
            'color': '',
            'presentacion': 'Frascos de 100 g',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'g',
            'stock_total': Decimal('300'),
            'minimo': Decimal('50'),
            'precio_unitario': Decimal('1.10'),
            'descripcion': 'Preparación de geles para verificar la amplificación del ADN.',
            'instrucciones_solicitud': 'Un gel al 1 % usa un gramo por cada cien mililitros de buffer.',
            'ubicacion': 'Estante de reactivos, área molecular',
            'equipos': ['BIO-EQ-TERMOCICLADOR'],
            'lotes': [
                {'codigo': 'BIO-AGAROSA-L1', 'cantidad': Decimal('300'), 'vence_en_dias': 600, 'estado': 'bodega'},
            ],
        },
    ],
    'servicios': [
        {
            'code': 'BIO-SRV-EXTRACCION',
            'familia': 'Análisis molecular',
            'nombre': 'Extracción y cuantificación de ADN',
            'descripcion': (
                'El laboratorio extrae el ADN de las muestras entregadas, mide su '
                'concentración y pureza, y entrega el material listo para análisis.'
            ),
            'resultado_entregado': (
                'ADN extraído en tubos rotulados e informe con concentración, '
                'pureza y condiciones de conservación.'
            ),
            'cuando_elegirlo': (
                'Cuando necesitas el ADN de tus muestras y no vas a ejecutar el '
                'protocolo con tus propias manos.'
            ),
            'tiempo_estimado_texto': '3 a 5 días laborables según el número de muestras',
            'tipo_servicio': 'analisis',
            'equipo': 'BIO-EQ-ESPECTRO',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega las muestras rotuladas con su procedencia y la cadena de '
                'custodia firmada.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '3.00', 'horas_equipo': '1.50', 'costo_equipo': '4.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '6.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('BIO-REA-KIT-ADN', '1.000', True),
                ('BIO-MAT-PUNTAS', '12.000', True),
                ('BIO-MAT-TUBOS', '4.000', True),
                ('BIO-MAT-GUANTES', '2.000', False),
            ],
        },
        {
            'code': 'BIO-SRV-ESTERIL',
            'familia': 'Apoyo técnico',
            'nombre': 'Esterilización de material y medios',
            'descripcion': (
                'Preparación y esterilización en autoclave de medios de cultivo, '
                'vidriería o material de otra unidad académica.'
            ),
            'resultado_entregado': (
                'Material esterilizado con indicador de control y registro del '
                'ciclo aplicado.'
            ),
            'cuando_elegirlo': (
                'Para prácticas de otras asignaturas o proyectos que necesitan '
                'material estéril y no operan el autoclave.'
            ),
            'tiempo_estimado_texto': '1 a 2 días laborables',
            'tipo_servicio': 'soporte',
            'equipo': 'BIO-EQ-AUTOCLAVE',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Indica el tipo de carga, el volumen y si el material regresa a tu '
                'unidad o se conserva aquí.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': False,
            'tarifa_base': '1.50', 'horas_equipo': '1.00', 'costo_equipo': '3.00',
            'horas_mano_obra': '0.50', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('BIO-REA-AGAR', '25.000', False),
                ('BIO-REA-CALDO', '25.000', False),
            ],
        },
        {
            'code': 'BIO-SRV-CULTIVO',
            'familia': 'Análisis molecular',
            'nombre': 'Cultivo y conservación de cepas',
            'descripcion': (
                'Siembra, crecimiento y conservación de cepas autorizadas bajo el '
                'protocolo del laboratorio.'
            ),
            'resultado_entregado': (
                'Cultivo crecido o cepa conservada con su registro de condiciones '
                'y fecha de siembra.'
            ),
            'cuando_elegirlo': (
                'Cuando el proyecto necesita mantener una cepa viva o preparar '
                'cultivos para un ensayo posterior.'
            ),
            'tiempo_estimado_texto': '2 a 7 días según el crecimiento requerido',
            'tipo_servicio': 'analisis',
            'equipo': 'BIO-EQ-INCUBADORA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Declara la cepa, su origen autorizado y las condiciones de '
                'crecimiento que necesita.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '2.00', 'horas_equipo': '8.00', 'costo_equipo': '1.20',
            'horas_mano_obra': '1.50', 'costo_mano_obra': '6.00',
            'diseno_asistido': '5.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('BIO-REA-CALDO', '50.000', True),
                ('BIO-REA-ETANOL', '100.000', False),
                ('BIO-MAT-GUANTES', '2.000', False),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Blga. Andrea Pozo',
            'rol': 'coordinacion',
            'email': 'biotecnologia@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2820',
            'descripcion': 'Coordina la bioseguridad, la agenda de las áreas y la custodia de reactivos.',
            'horario_atencion': 'Lunes a viernes · 07:00–18:00',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Diego Ibarra',
            'rol': 'laboratorista',
            'email': 'laboratorio.biotec@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2821',
            'descripcion': 'Prepara medios, opera el autoclave y acompaña las prácticas en las áreas estériles.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.biotecnologia',
            'nombres': 'Andrea',
            'apellidos': 'Pozo',
            'email': 'coordinacion.biotec@citt.test',
            'cargo': 'Coordinación del Laboratorio de Biotecnología Aplicada',
            'rol': 'coordinacion',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.biotecnologia',
            'nombres': 'Diego',
            'apellidos': 'Ibarra',
            'email': 'laboratorista.biotec@citt.test',
            'cargo': 'Laboratorista de Biotecnología Aplicada',
            'rol': 'laboratorista',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'inventario': True, 'practicas': True,
            },
        },
    ],
    'ejemplos': [
        {
            'proposito': 'servicio',
            'ejemplo': (
                'Necesito que el laboratorio extraiga y cuantifique el ADN de '
                'las muestras de suelo de mi proyecto de titulación. Son cuatro '
                'muestras recolectadas en campo la semana pasada, conservadas '
                'en frío y rotuladas con su punto de origen; entrego la cadena '
                'de custodia firmada. Pido que el informe incluya la '
                'concentración y la pureza de cada extracción y las condiciones '
                'en que debo conservar el material. Lo necesito antes del '
                'cierre del semestre porque la secuenciación se hace fuera de '
                'la Universidad.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de quinto semestre de Biología Molecular haremos '
                'la práctica de electroforesis en gel. Cada pareja preparará su '
                'gel de agarosa en el área molecular y correrá las muestras del '
                'ejercicio. Buscamos que reconozcan las bandas, calculen el '
                'tamaño de los fragmentos y expliquen qué pudo salir mal cuando '
                'el patrón no se ve. Somos dieciséis, necesitamos dos horas por '
                'sesión y todos tienen vigente la inducción de bioseguridad.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de bioprospección necesitamos el área de '
                'cultivo celular durante dos sesiones de tres horas. Somos dos '
                'investigadores con inducción vigente; trabajaremos con una '
                'cepa autorizada y usaremos medio de cultivo y material estéril '
                'del inventario. En la primera sesión sembraremos y en la '
                'segunda evaluaremos el crecimiento, dejando registrado el '
                'consumo real de cada reactivo.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación necesito el termociclador y el '
                'área de biología molecular durante dos sesiones de tres horas. '
                'Traigo el ADN ya extraído y los cebadores; solicito la agarosa '
                'y las puntas del laboratorio. Pido el acompañamiento de la '
                'laboratorista en la primera amplificación porque es la primera '
                'vez que programo el termociclador.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'BIO-ACT-MOLECULAR',
            'nombre': 'Práctica de biología molecular',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Biología Molecular',
        },
        {
            'codigo': 'BIO-ACT-INVESTIGACION',
            'nombre': 'Proyecto de investigación en bioprospección',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'proyecto_investigacion',
            'responsable': 'Investigador responsable del proyecto',
        },
    ],
}

EMPRENDIMIENTO = {
    'slug': 'laboratorio-emprendimiento-innovacion-empresarial',
    'prefijo': 'EMP',
    'capacidad_personas': 40,
    # Atiende en jornada extendida: sus usuarios trabajan o estudian de día.
    'horario_atencion': ('08:00', '20:00'),
    'unidad_de_trabajo': 'prototipos',
    # Esta unidad nace con la carga: no existía una ficha para las carreras
    # administrativas. Los datos solo se aplican al crearla.
    'unidad': {
        'nombre': 'Laboratorio de Emprendimiento e Innovación Empresarial',
        'descripcion': (
            'Espacio de la Universidad donde los equipos emprendedores dan forma '
            'a su idea de negocio: modelan la propuesta, validan el mercado, '
            'arman el prototipo de su producto o servicio y preparan la '
            'presentación con la que lo defienden. Acompaña a las carreras '
            'administrativas y a los proyectos de vinculación con la comunidad.'
        ),
        'descripcion_corta': (
            'Salas de trabajo, mentoría y herramientas para llevar una idea de '
            'negocio hasta su primer prototipo.'
        ),
        'fecha_inicio': date(2026, 1, 6),
        'dependencia': 'laboratorios',
        'clasificacion_funcional': 'laboratorio_mixto',
        'area_conocimiento': 'formacion',
        'codigo': 'CITT-EMP',
        'ubicacion': 'Bloque de Comercio y Administración, primer piso',
        'horario_atencion': 'Lunes a viernes · 08:00–20:00',
        'contacto_email': 'emprendimiento@upec.edu.ec',
        'facultad': 'Facultad de Comercio Internacional, Integración, Administración y Economía Empresarial',
        'carreras': (
            'Administración de Empresas, Administración Pública, Comercio '
            'Exterior, Contabilidad y Auditoría, Logística y Transporte, Turismo'
        ),
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'EMP-EQ-PORTATIL',
            'nombre': 'Portátil de trabajo para emprendedores',
            'categoria_codigo': 'EMP-TRABAJO',
            'categoria': 'Puestos de trabajo',
            'icono': '💻',
            'unidades': [
                'EMP-UNIT-PC-01', 'EMP-UNIT-PC-02', 'EMP-UNIT-PC-03',
                'EMP-UNIT-PC-04', 'EMP-UNIT-PC-05', 'EMP-UNIT-PC-06',
            ],
            'descripcion': (
                'Computador portátil con las herramientas de gestión, finanzas y '
                'diseño que usa el laboratorio.'
            ),
            'caracteristicas_publicas': (
                'Portátil de catorce pulgadas con suite ofimática, simulador '
                'financiero y programas de diseño de marca.'
            ),
            'uso_publico': (
                'Trabajo del equipo emprendedor durante la sesión: modelo de '
                'negocio, proyección financiera y material de presentación.'
            ),
            'instrucciones_publicas': (
                'Trae tu información en la nube o en memoria externa: el portátil '
                'se entrega limpio y se borra al devolverlo.'
            ),
            'software': 'Suite de gestión y finanzas instalada por el laboratorio',
            'admite_software_adicional': True,
            'accesorios': ['Cargador', 'Ratón', 'Adaptador de video'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de coworking',
        },
        {
            'codigo': 'EMP-EQ-PROYECTOR',
            'nombre': 'Proyector portátil para presentaciones',
            'categoria_codigo': 'EMP-TRABAJO',
            'categoria': 'Puestos de trabajo',
            'icono': '📽️',
            'unidades': ['EMP-UNIT-PROY-01', 'EMP-UNIT-PROY-02'],
            'descripcion': (
                'Proyector de alta luminosidad para exponer el avance del proyecto '
                'ante el comité o los mentores.'
            ),
            'caracteristicas_publicas': (
                'Resolución alta, conexión por cable y de forma inalámbrica, y '
                'maletín de traslado.'
            ),
            'uso_publico': (
                'Presentaciones de avance, defensas de proyecto y talleres con '
                'grupos numerosos.'
            ),
            'instrucciones_publicas': (
                'Reserva el proyector junto con la sala: se entrega y se devuelve '
                'en la misma sesión.'
            ),
            'software': 'No requiere programas del laboratorio',
            'accesorios': ['Cable de video', 'Control remoto', 'Maletín'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de juntas',
        },
        {
            'codigo': 'EMP-EQ-PITCH',
            'nombre': 'Kit de grabación de pitch',
            'categoria_codigo': 'EMP-MEDIOS',
            'categoria': 'Medios y difusión',
            'icono': '🎬',
            'unidades': ['EMP-UNIT-PITCH-01', 'EMP-UNIT-PITCH-02'],
            'descripcion': (
                'Cámara, trípode, micrófono de solapa y luz continua para grabar '
                'la presentación del emprendimiento.'
            ),
            'caracteristicas_publicas': (
                'Cámara de video, micrófono inalámbrico, aro de luz y fondo '
                'neutro montable.'
            ),
            'uso_publico': (
                'Grabación del pitch para postular a convocatorias, ferias o '
                'defensas de titulación.'
            ),
            'instrucciones_publicas': (
                'Reserva la cabina junto al kit y trae tu guion: la grabación se '
                'entrega el mismo día en la nube institucional.'
            ),
            'software': 'Edición básica incluida por el laboratorio',
            'accesorios': ['Trípode', 'Micrófono de solapa', 'Aro de luz', 'Fondo neutro'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Cabina de grabación',
        },
        {
            'codigo': 'EMP-EQ-PIZARRA',
            'nombre': 'Pizarra digital para talleres',
            'categoria_codigo': 'EMP-TRABAJO',
            'categoria': 'Puestos de trabajo',
            'icono': '🖍️',
            'unidades': ['EMP-UNIT-PIZ-01'],
            'descripcion': (
                'Pantalla interactiva para construir el modelo de negocio en '
                'grupo y guardar lo trabajado en la sesión.'
            ),
            'caracteristicas_publicas': (
                'Pantalla táctil de gran formato, lápiz digital y exportación de '
                'la pizarra a archivo.'
            ),
            'uso_publico': (
                'Talleres de modelo de negocio, tutorías grupales y sesiones de '
                'mentoría con varios equipos.'
            ),
            'instrucciones_publicas': (
                'Al terminar, exporta la pizarra: el laboratorio la borra antes '
                'de la siguiente sesión.'
            ),
            'software': 'Aplicación de pizarra instalada por el laboratorio',
            'accesorios': ['Lápiz digital', 'Borrador', 'Control de la pantalla'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de juntas',
        },
        {
            'codigo': 'EMP-EQ-PLOTTER',
            'nombre': 'Impresora de gran formato para tableros',
            'categoria_codigo': 'EMP-PROTOTIPADO',
            'categoria': 'Prototipado de baja fidelidad',
            'icono': '🖨️',
            'unidades': ['EMP-UNIT-PLOT-01'],
            'descripcion': (
                'Impresora de gran formato para los lienzos, tableros y láminas '
                'que el equipo presenta o usa en el taller.'
            ),
            'caracteristicas_publicas': (
                'Impresión a color hasta tamaño A1, papel en rollo y corte '
                'automático.'
            ),
            'uso_publico': (
                'Lienzos de modelo de negocio, tableros de propuesta de valor y '
                'láminas para ferias de emprendimiento.'
            ),
            'instrucciones_publicas': (
                'Declara cuántos prototipos vas a imprimir: el papel y la tinta '
                'se descuentan del inventario por cada uno.'
            ),
            'software': 'Cola de impresión del laboratorio',
            'accesorios': ['Rollo cargado', 'Bandeja de recepción'],
            'requiere_insumos': True,
            'insumos': 'Papel en rollo A1 y cartucho de tinta a color',
            'ubicacion': 'Área de prototipado',
        },
    ],
    'consumibles': [
        {
            'codigo': 'EMP-MAT-CANVAS',
            'nombre': 'Lienzo de modelo de negocio impreso',
            'clasificacion': 'insumo',
            'familia': 'Material de taller',
            'variante': 'Formato A1',
            'color': 'Blanco',
            'presentacion': 'Paquetes de 25 lienzos',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('200'),
            'minimo': Decimal('25'),
            'precio_unitario': Decimal('1.20'),
            'descripcion': 'Lienzo impreso para trabajar el modelo de negocio sobre la mesa.',
            'instrucciones_solicitud': 'Pide un lienzo por cada prototipo de propuesta que vayas a trabajar.',
            'ubicacion': 'Armario del área de prototipado',
            'equipos': [],
            'lotes': [
                {
                    'codigo': 'EMP-CANVAS-L1', 'cantidad': Decimal('100'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PIZ-01',
                    'vence_en_dias': None,
                },
                {
                    'codigo': 'EMP-CANVAS-L2', 'cantidad': Decimal('100'),
                    'estado': 'bodega', 'vence_en_dias': None,
                },
            ],
        },
        {
            'codigo': 'EMP-MAT-NOTAS',
            'nombre': 'Bloc de notas adhesivas',
            'clasificacion': 'insumo',
            'familia': 'Material de taller',
            'variante': 'Bloc de 100 hojas',
            'color': 'Surtido',
            'presentacion': 'Paquetes de 5 blocs',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'bloc',
            'stock_total': Decimal('120'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('1.60'),
            'descripcion': 'Notas adhesivas para las sesiones de ideación y priorización.',
            'instrucciones_solicitud': 'Indica cuántos blocs necesita el equipo para la sesión.',
            'ubicacion': 'Armario del área de prototipado',
            'equipos': [],
            'lotes': [
                {
                    'codigo': 'EMP-NOTAS-L1', 'cantidad': Decimal('120'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PIZ-01',
                    'vence_en_dias': None,
                },
            ],
        },
        {
            'codigo': 'EMP-MAT-CARTON',
            'nombre': 'Cartón pluma para maqueta',
            'clasificacion': 'insumo',
            'familia': 'Prototipado',
            'variante': 'Plancha de 50 × 70 cm',
            'color': 'Blanco',
            'presentacion': 'Paquetes de 10 planchas',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'plancha',
            'stock_total': Decimal('80'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('3.40'),
            'descripcion': 'Plancha ligera para armar la maqueta del producto o del punto de venta.',
            'instrucciones_solicitud': 'Calcula las planchas por prototipo: una maqueta sencilla usa dos.',
            'ubicacion': 'Armario del área de prototipado',
            'equipos': [],
            'lotes': [
                {
                    'codigo': 'EMP-CARTON-L1', 'cantidad': Decimal('40'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PLOT-01',
                    'vence_en_dias': None,
                },
                {
                    'codigo': 'EMP-CARTON-L2', 'cantidad': Decimal('40'),
                    'estado': 'bodega', 'vence_en_dias': None,
                },
            ],
        },
        {
            'codigo': 'EMP-MAT-MARCADOR',
            'nombre': 'Marcador para pizarra y lienzo',
            'clasificacion': 'material',
            'familia': 'Material de taller',
            'variante': 'Punta media',
            'color': 'Surtido',
            'presentacion': 'Cajas de seis colores',
            'cantidad_por_presentacion': Decimal('6'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('90'),
            'minimo': Decimal('12'),
            'precio_unitario': Decimal('0.85'),
            'descripcion': 'Marcadores para escribir sobre el lienzo y la pizarra del taller.',
            'instrucciones_solicitud': 'Indica cuántos necesita el equipo durante la sesión.',
            'ubicacion': 'Armario del área de prototipado',
            'equipos': [],
            'lotes': [
                {
                    'codigo': 'EMP-MARCADOR-L1', 'cantidad': Decimal('90'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PIZ-01',
                    'vence_en_dias': None,
                },
            ],
        },
        {
            'codigo': 'EMP-MAT-PAPEL-A1',
            'nombre': 'Papel en rollo para impresión de tableros',
            'clasificacion': 'insumo',
            'familia': 'Prototipado',
            'variante': 'Rollo de 91 cm',
            'color': 'Blanco',
            'presentacion': 'Rollo de 30 metros',
            'cantidad_por_presentacion': Decimal('30'),
            'unidad_medida': 'metro',
            'stock_total': Decimal('120'),
            'minimo': Decimal('15'),
            'precio_unitario': Decimal('2.10'),
            'descripcion': 'Papel del rollo que consume la impresora de gran formato.',
            'instrucciones_solicitud': 'Un tablero A1 consume cerca de un metro de rollo.',
            'ubicacion': 'Área de prototipado, junto a la impresora',
            'equipos': ['EMP-EQ-PLOTTER'],
            'lotes': [
                {
                    'codigo': 'EMP-PAPEL-R1', 'cantidad': Decimal('60'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PLOT-01',
                    'vence_en_dias': None,
                },
                {
                    'codigo': 'EMP-PAPEL-R2', 'cantidad': Decimal('60'),
                    'estado': 'bodega', 'vence_en_dias': None,
                },
            ],
        },
        {
            'codigo': 'EMP-INS-TINTA',
            'nombre': 'Cartucho de tinta a color para gran formato',
            'clasificacion': 'insumo',
            'familia': 'Prototipado',
            'variante': 'Cartucho de 80 ml',
            'color': 'Tricolor',
            'presentacion': 'Cartucho individual',
            'cantidad_por_presentacion': Decimal('1'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('320'),
            'minimo': Decimal('40'),
            'precio_unitario': Decimal('0.45'),
            'descripcion': 'Tinta que consume la impresora de gran formato en cada tablero.',
            'instrucciones_solicitud': 'La calcula el laboratorio según la cobertura del tablero.',
            'ubicacion': 'Área de prototipado, junto a la impresora',
            'equipos': ['EMP-EQ-PLOTTER'],
            'lotes': [
                {
                    'codigo': 'EMP-TINTA-C1', 'cantidad': Decimal('160'),
                    'estado': 'en_uso', 'equipo': 'EMP-UNIT-PLOT-01',
                    'vence_en_dias': 540,
                },
                {
                    'codigo': 'EMP-TINTA-C2', 'cantidad': Decimal('160'),
                    'estado': 'bodega', 'vence_en_dias': 720,
                },
            ],
        },
    ],
    'software': [
        {
            'codigo': 'EMP-SW-CANVAS', 'nombre': 'Plataforma de modelo de negocio',
            'version': '2026', 'tipo_recurso': 'licencia', 'tipo_acceso': 'red',
            'licencias': 30,
            'descripcion': 'Construcción del modelo de negocio y la propuesta de valor en línea.',
            'instrucciones': 'Acceso con la cuenta institucional: treinta personas a la vez.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'EMP-SW-FINANZAS', 'nombre': 'Simulador financiero y de flujo de caja',
            'version': '2026.1', 'tipo_recurso': 'software', 'tipo_acceso': 'instalacion',
            'licencias': 6,
            'descripcion': 'Proyección de ingresos, costos y punto de equilibrio del emprendimiento.',
            'instrucciones': 'Viene instalado en el portátil: se incluye al reservar el equipo.',
            'equipos_instalados': ['EMP-EQ-PORTATIL'],
            'uso_en_equipo': 'obligatorio',
        },
        {
            'codigo': 'EMP-SW-ENCUESTAS', 'nombre': 'Plataforma de encuestas para estudio de mercado',
            'version': '2026', 'tipo_recurso': 'licencia', 'tipo_acceso': 'remoto',
            'licencias': 3,
            'descripcion': 'Diseño y publicación de encuestas para validar el mercado del proyecto.',
            'instrucciones': 'Solo hay tres accesos: se entregan por el tiempo que dure la validación.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'EMP-SW-DISENO', 'nombre': 'Suite de diseño de marca y presentaciones',
            'version': '2026', 'tipo_recurso': 'licencia', 'tipo_acceso': 'licencia',
            'licencias': 10,
            'descripcion': 'Identidad visual, material de venta y láminas de presentación.',
            'instrucciones': 'Licencia asignada al portátil del laboratorio durante la sesión.',
            'equipos_instalados': ['EMP-EQ-PORTATIL'],
        },
    ],
    'espacios': [
        {
            'codigo': 'EMP-SALA-COWORK',
            'nombre': 'Sala de coworking',
            'tipo': 'sala',
            'ubicacion': 'Bloque de Comercio y Administración, primer piso',
            'capacidad': 24,
            'equipos_asociados': ['EMP-EQ-PORTATIL'],
            'politica_reserva': 'mixto',
            'mobiliario': 'Doce mesas de trabajo, tomas eléctricas por puesto, casilleros y red inalámbrica.',
            'descripcion': (
                'Sala abierta donde los equipos emprendedores trabajan por su '
                'cuenta durante la semana.'
            ),
            'caracteristicas': (
                'Mesas agrupables, tomas por puesto, red inalámbrica y casilleros '
                'para guardar material entre sesiones.'
            ),
            'instrucciones': (
                'Puede reservarse sola, sin equipos: indica cuántos puestos ocupa '
                'tu equipo porque la sala se comparte.'
            ),
        },
        {
            'codigo': 'EMP-SALA-JUNTAS',
            'nombre': 'Sala de juntas para comité',
            'tipo': 'sala',
            'ubicacion': 'Bloque de Comercio y Administración, primer piso',
            'capacidad': 12,
            'equipos_asociados': ['EMP-EQ-PROYECTOR', 'EMP-EQ-PIZARRA'],
            'politica_reserva': 'general',
            'mobiliario': 'Mesa para doce personas, pizarra digital, proyector y equipo de videoconferencia.',
            'descripcion': (
                'Sala cerrada para reuniones con mentores, comités evaluadores y '
                'aliados externos.'
            ),
            'caracteristicas': (
                'Mesa de directorio, pizarra digital, proyector y videoconferencia '
                'para invitados a distancia.'
            ),
            'instrucciones': (
                'Reserva la sala sola si solo necesitas reunirte, o súmale el '
                'proyector y la pizarra si vas a presentar.'
            ),
        },
        {
            'codigo': 'EMP-CABINA-PITCH',
            'nombre': 'Cabina de grabación de pitch',
            'tipo': 'cabina',
            'ubicacion': 'Bloque de Comercio y Administración, primer piso',
            'capacidad': 3,
            'equipos_asociados': ['EMP-EQ-PITCH'],
            'politica_reserva': 'general',
            'mobiliario': 'Fondo neutro, iluminación continua, tratamiento acústico y silla alta.',
            'descripcion': (
                'Cabina tratada acústicamente para grabar la presentación del '
                'emprendimiento sin ruido de fondo.'
            ),
            'caracteristicas': (
                'Aislamiento acústico, iluminación continua, fondo neutro y '
                'espacio para hasta tres personas.'
            ),
            'instrucciones': (
                'Reserva la cabina junto al kit de grabación y llega con el guion '
                'listo: la sesión dura lo reservado.'
            ),
        },
        {
            'codigo': 'EMP-AREA-PROTOTIPO',
            'nombre': 'Área de prototipado de baja fidelidad',
            'tipo': 'area',
            'ubicacion': 'Bloque de Comercio y Administración, primer piso',
            'capacidad': 16,
            'equipos_asociados': ['EMP-EQ-PLOTTER'],
            'politica_reserva': 'mixto',
            'mobiliario': 'Mesones amplios, muro de lienzos, herramientas de corte manual e impresora de gran formato.',
            'descripcion': (
                'Zona de mesones para armar maquetas, tableros y lienzos del '
                'proyecto antes de presentarlo.'
            ),
            'caracteristicas': (
                'Mesones de trabajo, muro para colgar lienzos, herramientas de '
                'corte manual e impresora de gran formato.'
            ),
            'instrucciones': (
                'Declara cuántos prototipos vas a armar: el material se calcula y '
                'se descuenta por cada uno.'
            ),
        },
    ],
    'servicios': [
        {
            'code': 'EMP-SRV-MENTORIA',
            'familia': 'Acompañamiento',
            'nombre': 'Mentoría para modelo de negocio',
            'descripcion': (
                'Sesión de trabajo con un mentor del laboratorio para revisar el '
                'modelo de negocio, el segmento de clientes y la propuesta de '
                'valor del proyecto.'
            ),
            'resultado_entregado': (
                'Informe de la sesión con las observaciones del mentor y los '
                'siguientes pasos acordados con el equipo.'
            ),
            'cuando_elegirlo': (
                'Cuando el equipo tiene una idea y necesita que alguien la '
                'cuestione antes de invertir tiempo o dinero en ella.'
            ),
            'tiempo_estimado_texto': '1 a 2 sesiones de dos horas',
            'tipo_servicio': 'soporte',
            'equipo': 'EMP-EQ-PIZARRA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Llega con la idea escrita y con lo que ya sabes de tus posibles '
                'clientes, aunque sea poco.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '8.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            # Una mentoría no consume inventario: es tiempo de una persona.
            'consumibles': [],
        },
        {
            'code': 'EMP-SRV-PROTOTIPO',
            'familia': 'Prototipado',
            'nombre': 'Prototipado de producto mínimo viable',
            'descripcion': (
                'El laboratorio arma con el equipo la primera versión presentable '
                'del producto o del servicio: maqueta, tablero y lienzos '
                'impresos para mostrarlo.'
            ),
            'resultado_entregado': (
                'Maqueta armada y tableros impresos en gran formato, listos para '
                'la feria o la defensa del proyecto.'
            ),
            'cuando_elegirlo': (
                'Cuando el proyecto ya está definido y necesita algo que la gente '
                'pueda ver y tocar para dar su opinión.'
            ),
            'tiempo_estimado_texto': '3 a 5 días laborables según los prototipos',
            'tipo_servicio': 'produccion',
            'equipo': 'EMP-EQ-PLOTTER',
            'requiere_archivos': True,
            'requisitos_usuario': (
                'Envía el boceto o las medidas de lo que quieres armar y el '
                'archivo de los tableros que se van a imprimir.'
            ),
            'formatos_archivo': 'PDF, PNG, JPG',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': True,
            'tarifa_base': '2.00', 'horas_equipo': '1.00', 'costo_equipo': '3.50',
            'horas_mano_obra': '3.00', 'costo_mano_obra': '8.00',
            'diseno_asistido': '10.00', 'diseno_completo': '25.00',
            'consumibles': [
                ('EMP-MAT-PAPEL-A1', '1.000', True),
                ('EMP-INS-TINTA', '6.000', True),
                ('EMP-MAT-CARTON', '2.000', False),
            ],
        },
        {
            'code': 'EMP-SRV-PITCH',
            'familia': 'Medios y difusión',
            'nombre': 'Grabación y edición de pitch',
            'descripcion': (
                'Grabación en cabina de la presentación del emprendimiento y '
                'edición del video con el que se postula a convocatorias.'
            ),
            'resultado_entregado': (
                'Video editado de hasta tres minutos, entregado en la nube '
                'institucional con su versión para redes.'
            ),
            'cuando_elegirlo': (
                'Cuando hay que enviar el proyecto a una convocatoria, una feria '
                'o un concurso que pide video.'
            ),
            'tiempo_estimado_texto': '2 a 4 días laborables después de la grabación',
            'tipo_servicio': 'produccion',
            'equipo': 'EMP-EQ-PITCH',
            'requiere_archivos': True,
            'requisitos_usuario': (
                'Envía el guion y las láminas de apoyo con dos días de '
                'anticipación a la grabación.'
            ),
            'formatos_archivo': 'PDF, PPTX, DOCX',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '1.50', 'horas_equipo': '2.00', 'costo_equipo': '2.50',
            'horas_mano_obra': '4.00', 'costo_mano_obra': '8.00',
            'diseno_asistido': '12.00', 'diseno_completo': '0.00',
            'consumibles': [],
        },
        {
            'code': 'EMP-SRV-MERCADO',
            'familia': 'Acompañamiento',
            'nombre': 'Estudio de mercado asistido',
            'descripcion': (
                'El laboratorio diseña con el equipo la encuesta, la publica en '
                'la plataforma del laboratorio y entrega los resultados '
                'ordenados.'
            ),
            'resultado_entregado': (
                'Informe con los resultados de la encuesta, los gráficos y la '
                'lectura de lo que dicen sobre el mercado del proyecto.'
            ),
            'cuando_elegirlo': (
                'Cuando el proyecto necesita datos de sus posibles clientes y no '
                'sabe cómo preguntarlos ni cómo leerlos.'
            ),
            'tiempo_estimado_texto': '1 a 3 semanas según el tamaño de la muestra',
            'tipo_servicio': 'analisis',
            'equipo': 'EMP-EQ-PORTATIL',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Declara a quién quieres preguntar, cuántas respuestas esperas y '
                'qué decisión vas a tomar con ellas.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '3.00', 'horas_equipo': '2.00', 'costo_equipo': '1.50',
            'horas_mano_obra': '6.00', 'costo_mano_obra': '8.00',
            'diseno_asistido': '15.00', 'diseno_completo': '0.00',
            'consumibles': [],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Paola Chamorro',
            'rol': 'coordinacion',
            'email': 'emprendimiento@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2840',
            'descripcion': 'Coordina la agenda de las salas, la cartera de proyectos y la red de mentores.',
            'horario_atencion': 'Lunes a viernes · 08:00–20:00',
            'orden': 1,
        },
        {
            'nombre': 'Econ. Luis Benavides',
            'rol': 'soporte',
            'email': 'mentoria.emprendimiento@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2841',
            'descripcion': 'Acompaña los modelos de negocio, las proyecciones financieras y los estudios de mercado.',
            'horario_atencion': 'Mentorías con reserva confirmada',
            'orden': 2,
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.emprendimiento',
            'nombres': 'Paola',
            'apellidos': 'Chamorro',
            'email': 'coordinacion.emprendimiento@citt.test',
            'cargo': 'Coordinación del Laboratorio de Emprendimiento e Innovación Empresarial',
            'rol': 'coordinacion',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'mentoria.emprendimiento',
            'nombres': 'Luis',
            'apellidos': 'Benavides',
            'email': 'mentoria.emprendimiento@citt.test',
            'cargo': 'Mentoría del Laboratorio de Emprendimiento e Innovación Empresarial',
            'rol': 'soporte',
            'modulos': {
                'reservas': True, 'agenda': True, 'recursos': True,
                'practicas': True, 'reportes': True,
            },
        },
    ],
    'ejemplos': [
        {
            'proposito': 'servicio',
            'ejemplo': (
                'Necesito que el laboratorio me acompañe a revisar el modelo de '
                'negocio de la tienda de barrio que quiero abrir con dos '
                'compañeras. Tenemos la idea escrita y hablamos con doce '
                'posibles clientes, pero no logramos explicar por qué nos '
                'comprarían a nosotras y no a la tienda de la esquina. Pido una '
                'sesión de mentoría para ordenar la propuesta de valor y saber '
                'qué debemos validar primero. Somos tres y podemos asistir en '
                'la tarde, después de las cinco.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de cuarto semestre de Administración haremos el '
                'taller de modelo de negocio. Cada equipo trabajará su lienzo '
                'en el área de prototipado, con los marcadores y las notas '
                'adhesivas del laboratorio, y al cerrar presentará su propuesta '
                'en la sala de juntas. Buscamos que distingan una idea de una '
                'oportunidad y que sustenten a quién le venden. Somos '
                'veinticuatro en seis equipos y necesitamos dos horas por '
                'sesión durante tres semanas.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de incubación necesitamos la sala de '
                'coworking y la plataforma de encuestas durante dos semanas. '
                'Somos cuatro integrantes del emprendimiento; publicaremos una '
                'encuesta a doscientos posibles clientes y procesaremos las '
                'respuestas en los portátiles del laboratorio. Con lo que '
                'salga armaremos tres prototipos del empaque para probarlos en '
                'la feria.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre un plan de negocios '
                'necesito la sala de coworking y el simulador financiero '
                'durante tres sesiones de tres horas. Traigo el estudio de '
                'mercado hecho y la proyección de ventas en borrador. Quiero '
                'construir el flujo de caja y el punto de equilibrio con el '
                'simulador y dejarlos sustentados en el capítulo financiero.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'EMP-ACT-TALLER',
            'nombre': 'Taller de modelo de negocio',
            'proposito_codigo': 'capacitacion',
            'subtipo_actividad': 'taller',
            'responsable': 'Mentor del Laboratorio de Emprendimiento',
        },
        {
            'codigo': 'EMP-ACT-TITULACION',
            'nombre': 'Plan de negocios como trabajo de titulación',
            'proposito_codigo': 'titulacion',
            'subtipo_actividad': 'trabajo_titulacion',
            'responsable': 'Docente tutor del trabajo de titulación',
        },
        {
            'codigo': 'EMP-ACT-VINCULACION',
            'nombre': 'Acompañamiento a emprendimientos de la comunidad',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
        {
            'codigo': 'EMP-ACT-INCUBACION',
            'nombre': 'Incubación de emprendimientos universitarios',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'innovacion_prototipado',
            'responsable': 'Coordinación del Laboratorio de Emprendimiento',
        },
    ],
}

LACTEOS = {
    'slug': 'planta-piloto-lacteos',
    'prefijo': 'LAC',
    'modo_operacion': 'lotes',
    'estado_catalogo': 'reserva_previa',
    'capacidad_personas': 20,
    # La leche llega de madrugada: la planta abre a las 07:00.
    'horario_atencion': ('07:00', '17:00'),
    'unidad_de_trabajo': 'lotes',
    'unidad': {
        'nombre': 'Planta Piloto de Lácteos',
        'descripcion': (
            'Planta de la Universidad donde la leche del centro experimental se '
            'transforma en yogur, queso fresco y otros derivados. Reproduce a '
            'escala piloto las etapas de recepción, pasteurización, '
            'fermentación, moldeo, empaque y frío, con control de calidad en '
            'cada lote. Atiende prácticas de las carreras de alimentos y '
            'agropecuaria, proyectos de desarrollo de productos y producción '
            'para venta.'
        ),
        'descripcion_corta': (
            'De la leche cruda al producto terminado: líneas de proceso, '
            'control de calidad y lotes trazables.'
        ),
        'fecha_inicio': date(2026, 1, 6),
        'dependencia': 'plantas_piloto',
        'clasificacion_funcional': 'planta_piloto',
        'area_conocimiento': 'agro',
        'codigo': 'CITT-PPL',
        'ubicacion': 'Centro Experimental San Francisco, bloque de plantas piloto',
        'horario_atencion': 'Lunes a viernes · 07:00–17:00',
        'contacto_email': 'planta.lacteos@upec.edu.ec',
        'facultad': 'Facultad de Industrias Agropecuarias y Ciencias Ambientales',
        'carreras': 'Alimentos, Agropecuaria, Veterinaria',
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'LAC-EQ-TANQUE',
            'nombre': 'Tanque de recepción y enfriamiento de leche',
            'categoria_codigo': 'LAC-RECEPCION',
            'categoria': 'Recepción y frío',
            'icono': '🥛',
            'unidades': ['LAC-EQP-TANQ-01'],
            'descripcion': (
                'Tanque de acero inoxidable de 500 litros con enfriamiento a '
                '4 °C donde se recibe, filtra y conserva la leche cruda.'
            ),
            'caracteristicas_publicas': (
                'Capacidad de 500 litros, agitación, enfriamiento por banco de '
                'hielo y toma de muestras.'
            ),
            'uso_publico': (
                'Recepción de leche del centro experimental o de productores, '
                'y conservación hasta el proceso.'
            ),
            'instrucciones_publicas': (
                'Toda leche que entra se registra por lote con su prueba de '
                'alcohol y su acidez antes de descargarse.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Filtro de recepción', 'Bidones de 40 litros', 'Cucharón de muestreo'],
            'requiere_insumos': True,
            'insumos': 'Leche cruda por lote',
            'ubicacion': 'Área de recepción de leche',
        },
        {
            'codigo': 'LAC-EQ-PASTEUR',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Pasteurizador por lotes',
            'categoria_codigo': 'LAC-PROCESO',
            'categoria': 'Proceso térmico',
            'icono': '🔥',
            'unidades': ['LAC-EQP-PAST-01'],
            'descripcion': (
                'Marmita de doble camisa con agitador para pasteurizar la leche '
                'a 65 °C durante treinta minutos o a 85 °C para yogur.'
            ),
            'caracteristicas_publicas': (
                'Capacidad de 200 litros, calentamiento por vapor, agitador y '
                'registro de temperatura.'
            ),
            'uso_publico': (
                'Pasteurización de leche para queso o yogur y tratamiento térmico '
                'de mezclas.'
            ),
            'instrucciones_publicas': (
                'Requiere la caldera encendida con anticipación: coordina la hora '
                'de arranque con el laboratorista.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Termómetro de proceso', 'Válvula de descarga sanitaria'],
            'requiere_insumos': True,
            'insumos': 'Leche pasteurizada, cultivos y azúcar según el producto',
            'ubicacion': 'Línea de proceso térmico',
        },
        {
            'codigo': 'LAC-EQ-DESCREMADORA',
            'familia_tecnologica': 'extraccion',
            'nombre': 'Descremadora centrífuga',
            'categoria_codigo': 'LAC-PROCESO',
            'categoria': 'Proceso térmico',
            'icono': '🌀',
            'unidades': ['LAC-EQP-DESC-01'],
            'descripcion': (
                'Separadora centrífuga que estandariza la grasa de la leche y '
                'obtiene crema para mantequilla o para ajustar recetas.'
            ),
            'caracteristicas_publicas': 'Capacidad de 150 litros por hora y ajuste del porcentaje de grasa.',
            'uso_publico': 'Estandarización de leche y obtención de crema.',
            'instrucciones_publicas': 'Se desarma y se lava después de cada uso: reserva ese tiempo.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de discos', 'Bandeja de crema'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de proceso térmico',
        },
        {
            'codigo': 'LAC-EQ-TINA',
            'nombre': 'Tina quesera con agitador',
            'categoria_codigo': 'LAC-QUESERIA',
            'categoria': 'Quesería',
            'icono': '🧀',
            'unidades': ['LAC-EQP-TINA-01'],
            'descripcion': (
                'Tina de doble pared donde la leche se coagula, se corta y se '
                'desuera para elaborar queso fresco y madurado.'
            ),
            'caracteristicas_publicas': 'Capacidad de 300 litros, agitación lenta y descarga de suero.',
            'uso_publico': 'Elaboración de quesos y cuajadas.',
            'instrucciones_publicas': 'Trabaja con la lira y los moldes de la planta; solicítalos con la reserva.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Lira de corte', 'Pala de cuajada', 'Termómetro'],
            'requiere_insumos': True,
            'insumos': 'Leche, cuajo, cloruro de calcio y sal',
            'ubicacion': 'Sala de quesería',
        },
        {
            'codigo': 'LAC-EQ-PRENSA',
            'nombre': 'Prensa neumática de quesos',
            'categoria_codigo': 'LAC-QUESERIA',
            'categoria': 'Quesería',
            'icono': '🧱',
            'unidades': ['LAC-EQP-PREN-01'],
            'descripcion': 'Prensa de dos pisos para dar forma y desuerar los quesos en molde.',
            'caracteristicas_publicas': 'Doce moldes por tanda y presión regulable.',
            'uso_publico': 'Prensado de quesos frescos y madurados.',
            'instrucciones_publicas': 'Se usa junto a la tina: el tiempo de prensado entra en la reserva.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Placas de prensado', 'Manómetro'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de quesería',
        },
        {
            'codigo': 'LAC-EQ-INCUBADORA',
            'familia_tecnologica': 'fermentacion',
            'nombre': 'Incubadora de yogur',
            'categoria_codigo': 'LAC-FERMENTACION',
            'categoria': 'Fermentación',
            'icono': '🫙',
            'unidades': ['LAC-EQP-INC-01', 'LAC-EQP-INC-02'],
            'descripcion': (
                'Cámara de incubación a 42 °C donde la leche inoculada fermenta '
                'hasta alcanzar la acidez del yogur.'
            ),
            'caracteristicas_publicas': 'Capacidad de 100 litros por cámara y control de temperatura.',
            'uso_publico': 'Fermentación de yogur y bebidas lácteas.',
            'instrucciones_publicas': 'La fermentación toma de cuatro a seis horas: reserva la jornada completa.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Bandejas', 'Termómetro de cámara'],
            'requiere_insumos': True,
            'insumos': 'Leche pasteurizada, cultivo láctico y azúcar',
            'ubicacion': 'Sala de fermentación y envasado',
        },
        {
            'codigo': 'LAC-EQ-ENVASADORA',
            'nombre': 'Envasadora semiautomática',
            'categoria_codigo': 'LAC-EMPAQUE',
            'categoria': 'Empaque',
            'icono': '📦',
            'unidades': ['LAC-EQP-ENV-01'],
            'descripcion': 'Dosificadora y selladora para envases de yogur de 200 ml y 1 litro.',
            'caracteristicas_publicas': 'Dosificación regulable y sellado térmico de tapas.',
            'uso_publico': 'Envasado de yogur y bebidas lácteas.',
            'instrucciones_publicas': 'Declara los envases y etiquetas del inventario que usará el lote.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Boquillas de dosificación', 'Rollo de tapas'],
            'requiere_insumos': True,
            'insumos': 'Envases, tapas y etiquetas',
            'ubicacion': 'Sala de fermentación y envasado',
        },
        {
            'codigo': 'LAC-EQ-CAMARA',
            'nombre': 'Cámara de refrigeración de producto',
            'categoria_codigo': 'LAC-RECEPCION',
            'categoria': 'Recepción y frío',
            'icono': '❄️',
            'unidades': ['LAC-EQP-CAM-01'],
            'descripcion': 'Cámara a 4 °C donde se conserva el producto terminado hasta su salida.',
            'caracteristicas_publicas': 'Doce metros cúbicos, registro de temperatura y estanterías.',
            'uso_publico': 'Conservación de yogur, queso y crema por lote.',
            'instrucciones_publicas': 'Cada lote entra con su etiqueta y su fecha de vencimiento.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Estanterías', 'Registrador de temperatura'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Cámara de frío',
        },
        {
            'codigo': 'LAC-EQ-CALDERA',
            'nombre': 'Caldera de vapor',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '♨️',
            'rol': 'auxiliar',
            'apoya_a': ['LAC-EQ-PASTEUR', 'LAC-EQ-TINA', 'LAC-EQ-MARMITA'],
            'unidades': ['LAC-EQP-CALD-01'],
            'descripcion': 'Genera el vapor que calienta el pasteurizador y la tina quesera.',
            'caracteristicas_publicas': 'Caldera eléctrica de 30 kW con control automático de presión.',
            'uso_publico': 'Suministro de vapor a los equipos de proceso térmico.',
            'instrucciones_publicas': 'No se reserva aparte: el laboratorista la enciende antes de cada corrida.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Trampas de vapor', 'Manómetro'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Cuarto de máquinas',
        },
        {
            'codigo': 'LAC-EQ-BALANZA',
            'nombre': 'Balanza de plataforma',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '⚖️',
            'rol': 'auxiliar',
            'apoya_a': ['LAC-EQ-TANQUE', 'LAC-EQ-ENVASADORA'],
            'unidades': ['LAC-EQP-BAL-01'],
            'descripcion': 'Pesa la leche que entra y el producto que sale de cada lote.',
            'caracteristicas_publicas': 'Hasta 150 kilogramos con precisión de 20 gramos.',
            'uso_publico': 'Pesaje de materias primas y producto terminado.',
            'instrucciones_publicas': 'No se reserva aparte: acompaña a la recepción y al envasado.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Pesa patrón'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Área de recepción de leche',
        },
        {
            'codigo': 'LAC-EQ-PHMETRO',
            'nombre': 'Medidor de pH portátil',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '🧪',
            'rol': 'auxiliar',
            'apoya_a': ['LAC-EQ-INCUBADORA', 'LAC-EQ-TINA'],
            'unidades': ['LAC-EQP-PH-01'],
            'descripcion': 'Controla la acidez durante la fermentación y la coagulación.',
            'caracteristicas_publicas': 'Electrodo para alimentos y compensación de temperatura.',
            'uso_publico': 'Control de acidez de yogur y cuajada.',
            'instrucciones_publicas': 'No se reserva aparte: acompaña a la incubadora y a la tina.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Soluciones de calibración'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Laboratorio de control de calidad',
        },
        {
            'codigo': 'LAC-EQ-LACTODENS',
            'nombre': 'Termolactodensímetro',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '🌡️',
            'rol': 'auxiliar',
            'apoya_a': ['LAC-EQ-TANQUE'],
            'unidades': ['LAC-EQP-LACT-01'],
            'descripcion': 'Mide la densidad y la temperatura de la leche en la recepción.',
            'caracteristicas_publicas': 'Escala de 1,015 a 1,040 con termómetro incorporado.',
            'uso_publico': 'Control de calidad de la leche recibida.',
            'instrucciones_publicas': 'No se reserva aparte: está en la recepción con la probeta.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Probeta de 250 ml'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Área de recepción de leche',
        },
        {
            'codigo': 'LAC-EQ-MARMITA',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Marmita con agitación',
            'categoria_codigo': 'LAC-PROCESO',
            'categoria': 'Proceso térmico',
            'icono': '🍯',
            'unidades': ['LAC-EQP-MARM-01'],
            'descripcion': 'Marmita de cien litros con chaqueta de vapor y agitador para concentrar leche con azúcar.',
            'caracteristicas_publicas': 'Cien litros, agitador de raspado y control de temperatura por vapor de la caldera.',
            'uso_publico': 'Manjar de leche, arequipe y jarabes.',
            'instrucciones_publicas': 'La concentración toma cuatro horas de agitación continua: reserva la jornada.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Refractómetro', 'Paleta de raspado'],
            'requiere_insumos': True,
            'insumos': 'Leche, azúcar, bicarbonato y glucosa',
            'ubicacion': 'Línea de proceso térmico',
        },
        {
            'codigo': 'LAC-EQ-HILADORA',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Hiladora de mozzarella',
            'categoria_codigo': 'LAC-QUESERIA',
            'categoria': 'Quesería',
            'icono': '🧀',
            'unidades': ['LAC-EQP-HILA-01'],
            'descripcion': 'Hiladora de cuajada en agua caliente para dar la textura fibrosa de la mozzarella.',
            'caracteristicas_publicas': 'Veinte kilos por tanda, agua a 80 °C y brazos de hilado.',
            'uso_publico': 'Hilado de mozzarella y quesos de pasta hilada.',
            'instrucciones_publicas': 'Se usa después de la acidificación de la cuajada; el agua caliente es un riesgo de quemadura.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Termómetro de inmersión', 'Guantes térmicos'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de quesería',
        },
        {
            'codigo': 'LAC-EQ-MANTEQUILLERA',
            'nombre': 'Mantequillera de batido',
            'categoria_codigo': 'LAC-DERIVADOS',
            'categoria': 'Mantequilla y crema',
            'icono': '🧈',
            'unidades': ['LAC-EQP-MANT-01'],
            'descripcion': 'Batidora de crema madurada que separa la grasa de la mazada y amasa la mantequilla.',
            'caracteristicas_publicas': 'Veinte litros de crema por tanda, dos velocidades y lavado en el mismo tambor.',
            'uso_publico': 'Mantequilla a partir de la crema del descremado.',
            'instrucciones_publicas': 'La crema debe madurar en frío desde el día anterior.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Paletas de amasado', 'Moldes de mantequilla'],
            'requiere_insumos': True,
            'insumos': 'Crema madurada y sal',
            'ubicacion': 'Sala de quesería',
        },
        {
            'codigo': 'LAC-EQ-MADURACION',
            'nombre': 'Cámara de maduración de quesos',
            'categoria_codigo': 'LAC-RECEPCION',
            'categoria': 'Recepción y frío',
            'icono': '🧊',
            'unidades': ['LAC-EQP-MADU-01'],
            'descripcion': 'Cámara a 12 °C y 85 % de humedad donde los quesos semimaduros hacen su tiempo.',
            'caracteristicas_publicas': 'Seis metros cúbicos, estanterías de madera y registro de temperatura y humedad.',
            'uso_publico': 'Maduración de quesos semimaduros y maduros por semanas.',
            'instrucciones_publicas': 'Los quesos se voltean cada dos días; la cámara queda ocupada todo el tiempo de maduración.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Higrómetro', 'Cepillos de volteo'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Cámara de maduración',
        },
    ],
    'consumibles': [
        {
            'codigo': 'LAC-INS-LECHE',
            'plazo_dias': 1,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Leche cruda',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Entera',
            'color': '',
            'presentacion': 'Bidón de 40 litros',
            'cantidad_por_presentacion': Decimal('40'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('400'),
            'minimo': Decimal('80'),
            'precio_unitario': Decimal('0.48'),
            'descripcion': 'Leche entera del centro experimental, recibida con prueba de alcohol y acidez.',
            'instrucciones_solicitud': 'Pide los litros por lote; la planta la recibe la madrugada del día de proceso.',
            'ubicacion': 'Tanque de recepción',
            'equipos': ['LAC-EQ-TANQUE', 'LAC-EQ-PASTEUR', 'LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-LECHE-L1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': 3},
                {'codigo': 'LAC-LECHE-L2', 'cantidad': Decimal('200'), 'estado': 'bodega', 'vence_en_dias': 3},
            ],
        },
        {
            'codigo': 'LAC-INS-CULTIVO-YOG',
            'plazo_dias': 20,
            'proveedor': 'Cultivos y Fermentos Andinos',
            'nombre': 'Cultivo láctico para yogur',
            'clasificacion': 'insumo',
            'familia': 'Cultivos y fermentos',
            'variante': 'Termófilo liofilizado',
            'color': '',
            'presentacion': 'Sobre para 100 litros',
            'cantidad_por_presentacion': Decimal('1'),
            'unidad_medida': 'sobre',
            'stock_total': Decimal('24'),
            'minimo': Decimal('6'),
            'precio_unitario': Decimal('9.50'),
            'descripcion': 'Cultivo directo de Streptococcus thermophilus y Lactobacillus bulgaricus.',
            'instrucciones_solicitud': 'Un sobre inocula 100 litros; se conserva congelado.',
            'ubicacion': 'Congelador de cultivos',
            'equipos': ['LAC-EQ-INCUBADORA', 'LAC-EQ-PASTEUR'],
            'lotes': [
                {'codigo': 'LAC-CULT-L1', 'cantidad': Decimal('12'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-INC-01', 'vence_en_dias': 180},
                {'codigo': 'LAC-CULT-L2', 'cantidad': Decimal('12'), 'estado': 'bodega', 'vence_en_dias': 360},
            ],
        },
        {
            'codigo': 'LAC-INS-CUAJO',
            'plazo_dias': 21,
            'proveedor': 'Insumos Lácteos del Norte',
            'nombre': 'Cuajo líquido',
            'clasificacion': 'insumo',
            'familia': 'Cultivos y fermentos',
            'variante': 'Quimosina 1:10 000',
            'color': '',
            'presentacion': 'Frasco de 500 ml',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('1000'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.06'),
            'descripcion': 'Coagulante para queso; diez mililitros por cada cien litros de leche.',
            'instrucciones_solicitud': 'Calcula 10 ml por cada 100 litros de leche.',
            'ubicacion': 'Refrigerador de aditivos',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-CUAJO-L1', 'cantidad': Decimal('500'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': 365},
                {'codigo': 'LAC-CUAJO-L2', 'cantidad': Decimal('500'), 'estado': 'bodega', 'vence_en_dias': 540},
            ],
        },
        {
            'codigo': 'LAC-INS-CLORURO',
            'plazo_dias': 21,
            'proveedor': 'Insumos Lácteos del Norte',
            'nombre': 'Cloruro de calcio alimentario',
            'clasificacion': 'insumo',
            'familia': 'Aditivos',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Bolsa de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('3000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.01'),
            'descripcion': 'Repone el calcio de la leche pasteurizada para una buena coagulación.',
            'instrucciones_solicitud': 'Veinte gramos por cada cien litros de leche.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-CLORURO-L1', 'cantidad': Decimal('3000'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-INS-SAL',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Sal refinada',
            'clasificacion': 'insumo',
            'familia': 'Aditivos',
            'variante': 'Yodada',
            'color': '',
            'presentacion': 'Saco de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('50'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('0.60'),
            'descripcion': 'Sal para el salado de quesos.',
            'instrucciones_solicitud': 'Alrededor de un kilo por cada cien litros de leche para queso fresco.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-SAL-L1', 'cantidad': Decimal('50'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-INS-AZUCAR',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Azúcar',
            'clasificacion': 'insumo',
            'familia': 'Aditivos',
            'variante': 'Blanca',
            'color': '',
            'presentacion': 'Saco de 50 kg',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('100'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('1.10'),
            'descripcion': 'Azúcar para yogur y bebidas lácteas.',
            'instrucciones_solicitud': 'Ocho kilos por cada cien litros de yogur.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['LAC-EQ-PASTEUR', 'LAC-EQ-INCUBADORA'],
            'lotes': [
                {'codigo': 'LAC-AZUCAR-L1', 'cantidad': Decimal('100'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-PAST-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-REA-ALCOHOL',
            'nombre': 'Alcohol al 68 % para prueba de estabilidad',
            'clasificacion': 'reactivo',
            'familia': 'Control de calidad de leche',
            'variante': '68 %',
            'color': '',
            'presentacion': 'Frasco de 1 litro',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.01'),
            'descripcion': 'Prueba de alcohol en la recepción: detecta leche inestable al calor.',
            'instrucciones_solicitud': 'Dos mililitros por prueba.',
            'ubicacion': 'Laboratorio de control de calidad',
            'equipos': ['LAC-EQ-TANQUE'],
            'lotes': [
                {'codigo': 'LAC-ALCOHOL-L1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': 540},
                {'codigo': 'LAC-ALCOHOL-L2', 'cantidad': Decimal('1000'), 'estado': 'bodega', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-REA-NAOH',
            'nombre': 'Hidróxido de sodio 0,1 N',
            'clasificacion': 'reactivo',
            'familia': 'Control de calidad de leche',
            'variante': 'Solución valorada',
            'color': '',
            'presentacion': 'Frasco de 1 litro',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('1000'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.02'),
            'descripcion': 'Titulante para la acidez Dornic de la leche y el yogur.',
            'instrucciones_solicitud': 'Unos dos mililitros por determinación.',
            'ubicacion': 'Laboratorio de control de calidad',
            'equipos': ['LAC-EQ-TANQUE', 'LAC-EQ-INCUBADORA'],
            'lotes': [
                {'codigo': 'LAC-NAOH-L1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': 180},
            ],
        },
        {
            'codigo': 'LAC-REA-FENOL',
            'nombre': 'Fenolftaleína al 1 %',
            'clasificacion': 'reactivo',
            'familia': 'Control de calidad de leche',
            'variante': 'Indicador',
            'color': '',
            'presentacion': 'Frasco gotero de 100 ml',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('200'),
            'minimo': Decimal('50'),
            'precio_unitario': Decimal('0.08'),
            'descripcion': 'Indicador de la titulación de acidez.',
            'instrucciones_solicitud': 'Tres gotas por determinación.',
            'ubicacion': 'Laboratorio de control de calidad',
            'equipos': ['LAC-EQ-TANQUE'],
            'lotes': [
                {'codigo': 'LAC-FENOL-L1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-MAT-MOLDE',
            'nombre': 'Molde para queso fresco de 500 g',
            'clasificacion': 'material',
            'familia': 'Quesería',
            'variante': 'Plástico alimentario',
            'color': 'Blanco',
            'presentacion': 'Juego de 12 moldes',
            'cantidad_por_presentacion': Decimal('12'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('48'),
            'minimo': Decimal('12'),
            'precio_unitario': Decimal('4.20'),
            'descripcion': 'Molde perforado con seguidor para prensar queso fresco.',
            'instrucciones_solicitud': 'Un molde por cada queso de la tanda; se devuelven lavados.',
            'ubicacion': 'Sala de quesería',
            'equipos': ['LAC-EQ-TINA', 'LAC-EQ-PRENSA'],
            'lotes': [
                {'codigo': 'LAC-MOLDE-J1', 'cantidad': Decimal('48'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-PREN-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-MAT-LIRA',
            'nombre': 'Lira de corte de cuajada',
            'clasificacion': 'material',
            'familia': 'Quesería',
            'variante': 'Corte de 1 cm',
            'color': '',
            'presentacion': 'Unidad',
            'cantidad_por_presentacion': Decimal('1'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('2'),
            'minimo': Decimal('1'),
            'precio_unitario': Decimal('85.00'),
            'descripcion': 'Lira de acero inoxidable para cortar la cuajada en la tina.',
            'instrucciones_solicitud': 'Viene con la tina; indícalo si necesitas la lira de corte fino.',
            'ubicacion': 'Sala de quesería',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-LIRA-U1', 'cantidad': Decimal('2'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-MAT-PANO',
            'nombre': 'Paño de quesería',
            'clasificacion': 'material',
            'familia': 'Quesería',
            'variante': 'Tela de 60 × 60 cm',
            'color': 'Blanco',
            'presentacion': 'Paquete de 10',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('1.80'),
            'descripcion': 'Tela para desuerar y forrar moldes.',
            'instrucciones_solicitud': 'Un paño por molde; se lavan y se reutilizan.',
            'ubicacion': 'Sala de quesería',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-PANO-P1', 'cantidad': Decimal('40'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-EMP-ENVASE-1L',
            'plazo_dias': 15,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Envase de yogur de 1 litro con tapa',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': '1 litro',
            'color': 'Blanco',
            'presentacion': 'Caja de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('600'),
            'minimo': Decimal('200'),
            'precio_unitario': Decimal('0.22'),
            'descripcion': 'Envase de polietileno con tapa a presión para yogur.',
            'instrucciones_solicitud': 'Un envase por litro de yogur del lote.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-ENVASE-C1', 'cantidad': Decimal('300'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
                {'codigo': 'LAC-ENVASE-C2', 'cantidad': Decimal('300'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-EMP-FUNDA-QUESO',
            'plazo_dias': 15,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Funda termoencogible para queso',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': '500 g',
            'color': 'Transparente',
            'presentacion': 'Paquete de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('400'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.15'),
            'descripcion': 'Funda para empacar queso fresco al vacío.',
            'instrucciones_solicitud': 'Una funda por queso.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA', 'LAC-EQ-PRENSA'],
            'lotes': [
                {'codigo': 'LAC-FUNDA-P1', 'cantidad': Decimal('400'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-EMP-ETIQUETA',
            'plazo_dias': 10,
            'proveedor': 'Imprenta Universitaria',
            'nombre': 'Etiqueta de producto con lote y vencimiento',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Adhesiva 60 × 40 mm',
            'color': '',
            'presentacion': 'Rollo de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.04'),
            'descripcion': 'Etiqueta institucional con espacio para lote, fecha y contenido.',
            'instrucciones_solicitud': 'Una por envase.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-ETIQ-R1', 'cantidad': Decimal('1500'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-PRO-COFIA',
            'nombre': 'Cofia desechable',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Plisada',
            'color': 'Blanco',
            'presentacion': 'Caja de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('500'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Obligatoria para entrar a las áreas de proceso.',
            'instrucciones_solicitud': 'Una por persona y por sesión.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'LAC-COFIA-C1', 'cantidad': Decimal('500'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-PRO-GUANTES',
            'nombre': 'Guantes de nitrilo',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Talla M',
            'color': 'Azul',
            'presentacion': 'Caja de 50 pares',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'par',
            'stock_total': Decimal('200'),
            'minimo': Decimal('50'),
            'precio_unitario': Decimal('0.18'),
            'descripcion': 'Guantes para manipular producto y reactivos.',
            'instrucciones_solicitud': 'Un par por persona y por sesión.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'LAC-GUANTES-C1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TANQ-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-LIM-ALCALINO',
            'nombre': 'Detergente alcalino para limpieza en sitio',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Concentrado',
            'color': '',
            'presentacion': 'Bidón de 20 litros',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('2.40'),
            'descripcion': 'Remueve residuos de grasa y proteína de tanques y líneas.',
            'instrucciones_solicitud': 'La planta lo dosifica en cada ciclo de limpieza; no se pide por reserva.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['LAC-EQ-PASTEUR', 'LAC-EQ-TANQUE'],
            'lotes': [
                {'codigo': 'LAC-ALCALINO-B1', 'cantidad': Decimal('40'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-PAST-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-LIM-SANITIZANTE',
            'nombre': 'Sanitizante de amonio cuaternario',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Concentrado',
            'color': '',
            'presentacion': 'Bidón de 5 litros',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('20'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('4.80'),
            'descripcion': 'Desinfección final de superficies y equipos.',
            'instrucciones_solicitud': 'La planta lo aplica al cerrar cada corrida.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['LAC-EQ-PASTEUR', 'LAC-EQ-TINA', 'LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-SANIT-B1', 'cantidad': Decimal('20'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-PAST-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-INS-CULTIVO-TERMO',
            'nombre': 'Cultivo termófilo para mozzarella',
            'clasificacion': 'insumo',
            'familia': 'Cultivos y fermentos',
            'variante': 'Termófilo liofilizado',
            'color': '',
            'presentacion': 'Sobre para 100 litros',
            'cantidad_por_presentacion': Decimal('1'),
            'unidad_medida': 'sobre',
            'stock_total': Decimal('12'),
            'minimo': Decimal('4'),
            'precio_unitario': Decimal('11.00'),
            'descripcion': 'Cultivo directo de Streptococcus thermophilus para quesos de pasta hilada.',
            'instrucciones_solicitud': 'Un sobre por cada cien litros; se conserva congelado.',
            'ubicacion': 'Congelador de cultivos',
            'equipos': ['LAC-EQ-TINA', 'LAC-EQ-HILADORA'],
            'lotes': [
                {'codigo': 'LAC-CULT-TERMO-L1', 'cantidad': Decimal('12'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': 240},
            ],
        },
        {
            'codigo': 'LAC-INS-CULTIVO-MESO',
            'nombre': 'Cultivo mesófilo para quesos madurados',
            'clasificacion': 'insumo',
            'familia': 'Cultivos y fermentos',
            'variante': 'Mesófilo liofilizado',
            'color': '',
            'presentacion': 'Sobre para 100 litros',
            'cantidad_por_presentacion': Decimal('1'),
            'unidad_medida': 'sobre',
            'stock_total': Decimal('12'),
            'minimo': Decimal('4'),
            'precio_unitario': Decimal('12.50'),
            'descripcion': 'Cultivo de Lactococcus lactis para quesos semimaduros y maduros.',
            'instrucciones_solicitud': 'Un sobre por cada cien litros; se conserva congelado.',
            'ubicacion': 'Congelador de cultivos',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-CULT-MESO-L1', 'cantidad': Decimal('12'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': 240},
            ],
        },
        {
            'codigo': 'LAC-INS-PULPA-MORA',
            'plazo_dias': 5,
            'proveedor': 'Asociación de Productores de Mora',
            'nombre': 'Pulpa de mora',
            'clasificacion': 'insumo',
            'familia': 'Frutas y saborizantes',
            'variante': 'Pulpa congelada sin azúcar',
            'color': '',
            'presentacion': 'Bolsa de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('3.20'),
            'descripcion': 'Pulpa de mora del centro experimental, pasteurizada y congelada.',
            'instrucciones_solicitud': 'Diez kilos por cada cien litros de yogur batido.',
            'ubicacion': 'Congelador de pulpas',
            'equipos': ['LAC-EQ-TINA'],
            'lotes': [
                {'codigo': 'LAC-PULPA-L1', 'cantidad': Decimal('40'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-TINA-01', 'vence_en_dias': 180},
            ],
        },
        {
            'codigo': 'LAC-INS-BICARBONATO',
            'nombre': 'Bicarbonato de sodio',
            'clasificacion': 'insumo',
            'familia': 'Aditivos alimentarios',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Bolsa de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.004'),
            'descripcion': 'Neutraliza la acidez de la leche antes de concentrarla en el manjar.',
            'instrucciones_solicitud': 'Medio gramo por litro de leche.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['LAC-EQ-MARMITA'],
            'lotes': [
                {'codigo': 'LAC-BICARB-L1', 'cantidad': Decimal('2000'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-MARM-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'LAC-INS-GLUCOSA',
            'nombre': 'Glucosa',
            'clasificacion': 'insumo',
            'familia': 'Aditivos alimentarios',
            'variante': 'Jarabe de glucosa',
            'color': '',
            'presentacion': 'Balde de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('50'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('1.80'),
            'descripcion': 'Evita la cristalización del manjar de leche.',
            'instrucciones_solicitud': 'Un kilo por cada cincuenta litros de leche.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['LAC-EQ-MARMITA'],
            'lotes': [
                {'codigo': 'LAC-GLUCOSA-L1', 'cantidad': Decimal('50'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-MARM-01', 'vence_en_dias': 540},
            ],
        },
        {
            'codigo': 'LAC-INS-CERA',
            'nombre': 'Cera de recubrimiento para quesos',
            'clasificacion': 'insumo',
            'familia': 'Recubrimientos',
            'variante': 'Cera alimentaria amarilla',
            'color': 'Amarillo',
            'presentacion': 'Bloque de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('10'),
            'minimo': Decimal('2'),
            'precio_unitario': Decimal('6.50'),
            'descripcion': 'Recubre los quesos semimaduros antes de la cámara de maduración.',
            'instrucciones_solicitud': 'Trescientos gramos por cada diez kilos de queso.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': [],
            'lotes': [
                {'codigo': 'LAC-CERA-L1', 'cantidad': Decimal('10'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-PREN-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-INS-CREMA',
            'nombre': 'Crema de leche madurada (intermedio de la planta)',
            'clasificacion': 'insumo',
            'familia': 'Intermedios de la planta',
            'variante': 'Crema del descremado, 40 % de grasa',
            'color': '',
            'presentacion': 'Balde de 5 litros',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('0'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('4.50'),
            'descripcion': 'La crema que sale del descremado y vuelve a entrar en la mantequilla; no se compra, se produce.',
            'instrucciones_solicitud': 'Entra al inventario cuando un lote de crema se registra como consumo interno.',
            'ubicacion': 'Cámara de refrigeración de producto',
            'equipos': ['LAC-EQ-MANTEQUILLERA'],
            'lotes': [],
        },
        {
            'codigo': 'LAC-EMP-PAPEL-MANTEQUILLA',
            'nombre': 'Papel parafinado para mantequilla',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Hoja de 250 g impresa',
            'color': '',
            'presentacion': 'Paquete de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1000'),
            'minimo': Decimal('200'),
            'precio_unitario': Decimal('0.03'),
            'descripcion': 'Envuelve los bloques de mantequilla de 250 g.',
            'instrucciones_solicitud': 'Cuatro hojas por kilo de mantequilla.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-PAPELM-P1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-EMP-FRASCO-MANJAR',
            'nombre': 'Frasco de vidrio de 250 g con tapa',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Vidrio con tapa metálica',
            'color': '',
            'presentacion': 'Caja de 48',
            'cantidad_por_presentacion': Decimal('48'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('480'),
            'minimo': Decimal('96'),
            'precio_unitario': Decimal('0.35'),
            'descripcion': 'Frasco para manjar de leche envasado en caliente.',
            'instrucciones_solicitud': 'Cuatro frascos por kilo de manjar.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-FRASCO-C1', 'cantidad': Decimal('480'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'LAC-EMP-BALDE-5L',
            'nombre': 'Balde de 5 litros con tapa',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Polipropileno alimentario',
            'color': 'Blanco',
            'presentacion': 'Paquete de 20',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('60'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('0.90'),
            'descripcion': 'Balde para crema de leche y para el intermedio que vuelve a la planta.',
            'instrucciones_solicitud': 'Un balde por cada cinco litros de crema.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['LAC-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'LAC-BALDE-P1', 'cantidad': Decimal('60'), 'estado': 'en_uso', 'equipo': 'LAC-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
    ],
    'software': [
        {
            'codigo': 'LAC-SW-TRAZA', 'nombre': 'Registro de trazabilidad de lotes',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'red',
            'licencias': 10,
            'descripcion': 'Bitácora digital donde cada lote registra su leche, su proceso y su salida.',
            'instrucciones': 'Se abre en el navegador con la cuenta institucional; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'LAC-SW-BALANCE', 'nombre': 'Simulador de balance de materia y energía',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': 'Cuánto entra, cuánto sale y cuánto calor exige una corrida; corre sobre el proceso real y toma los datos de la reserva.',
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'LAC-SW-LINEA', 'nombre': 'Simulador de balance de línea',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': 'Tiempos por estación, cuello de botella y capacidad de la jornada para un proceso.',
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'LAC-SW-MRP', 'nombre': 'Simulador de requerimiento de materiales',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': 'Lo que el inventario debe tener para un plan de corridas o para toda una programación.',
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
    ],
    'espacios': [
        {
            'codigo': 'LAC-AREA-RECEPCION',
            'visitable': True,
            'nombre': 'Área de recepción de leche',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ingreso de materia prima',
            'capacidad': 6,
            'equipos_asociados': ['LAC-EQ-TANQUE'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Andén de descarga, mesón de control de calidad, lavabo y tanque de recepción.',
            'descripcion': 'Zona donde se recibe, analiza y enfría la leche antes del proceso.',
            'caracteristicas': 'Andén cubierto, piso lavable, toma de agua potable y drenaje sanitario.',
            'instrucciones': 'Toda leche pasa por la prueba de alcohol y la acidez antes de entrar al tanque.',
        },
        {
            'codigo': 'LAC-LINEA-PROCESO',
            'visitable': True,
            'nombre': 'Línea de proceso térmico',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 8,
            'equipos_asociados': ['LAC-EQ-PASTEUR', 'LAC-EQ-DESCREMADORA', 'LAC-EQ-MARMITA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Pasteurizador, descremadora, mesones de acero, bomba sanitaria y tuberías.',
            'descripcion': 'Línea donde la leche se estandariza y se pasteuriza para cualquier producto.',
            'caracteristicas': 'Vapor de caldera, agua fría, piso con pendiente y drenaje central.',
            'instrucciones': 'Se reserva completa: una corrida ocupa toda la línea y su limpieza posterior.',
        },
        {
            'codigo': 'LAC-AREA-QUESERIA',
            'nombre': 'Sala de quesería',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 10,
            'equipos_asociados': ['LAC-EQ-TINA', 'LAC-EQ-PRENSA', 'LAC-EQ-HILADORA', 'LAC-EQ-MANTEQUILLERA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Tina quesera, prensa, mesa de moldeo y estantería de moldes.',
            'descripcion': 'Sala para coagular, cortar, moldear y prensar quesos.',
            'caracteristicas': 'Temperatura controlada, mesones de acero y saladero.',
            'instrucciones': 'Cofia, mascarilla y botas son obligatorias; la sala se entrega lavada.',
        },
        {
            'codigo': 'LAC-AREA-FERMENTACION',
            'nombre': 'Sala de fermentación y envasado',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 8,
            'equipos_asociados': ['LAC-EQ-INCUBADORA', 'LAC-EQ-ENVASADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Dos incubadoras, envasadora, mesa de empaque y etiquetadora manual.',
            'descripcion': 'Sala donde el yogur fermenta, se envasa y se etiqueta por lote.',
            'caracteristicas': 'Área limpia con acceso restringido y control de temperatura.',
            'instrucciones': 'La fermentación toma la jornada: reserva el día completo para un lote.',
        },
        {
            'codigo': 'LAC-CAMARA-FRIO',
            'nombre': 'Cámara de frío',
            'tipo': 'camara',
            'ubicacion': 'Planta piloto, zona de despacho',
            'capacidad': 2,
            'equipos_asociados': ['LAC-EQ-CAMARA', 'LAC-EQ-MADURACION'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Estanterías de acero, registrador de temperatura y cortina de aire.',
            'descripcion': 'Conserva el producto terminado hasta su venta o transferencia.',
            'caracteristicas': 'Cuatro grados centígrados con registro continuo.',
            'instrucciones': 'Cada lote entra etiquetado; el laboratorista registra la entrada y la salida.',
        },
        {
            'codigo': 'LAC-LAB-CALIDAD',
            'nombre': 'Laboratorio de control de calidad',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, junto a la recepción',
            'capacidad': 6,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesón con lavabo, titulador manual, estufa y refrigerador de reactivos.',
            'descripcion': 'Pruebas de plataforma de la leche y controles del producto terminado.',
            'caracteristicas': 'Mesón de trabajo para seis personas y reactivos de la planta.',
            'instrucciones': 'Puede reservarse solo, sin equipos, para las pruebas de plataforma.',
        },
        {
            'codigo': 'LAC-SALA-CAPACITACION',
            'visitable': True,
            'nombre': 'Sala de capacitación y degustación',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, planta alta',
            'capacidad': 20,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesas, proyector, pizarra y mesón de degustación.',
            'descripcion': 'Sala para clases, capacitaciones a productores y paneles de degustación.',
            'caracteristicas': 'Vista a la sala de proceso a través de ventanal.',
            'instrucciones': 'Puede reservarse sola para clases y visitas.',
        },
    ],
    'servicios': [
        {
            'code': 'LAC-SRV-MAQUILA',
            'receta': 'LAC-REC-YOGUR-100',
            'materia_prima_cliente': True,
            'familia': 'Producción',
            'nombre': 'Elaboración de yogur por maquila',
            'descripcion': (
                'La planta elabora yogur con la leche y la receta acordadas, '
                'lo envasa, lo etiqueta con su lote y lo entrega en frío.'
            ),
            'resultado_entregado': (
                'Yogur envasado y etiquetado con lote, fecha de vencimiento y '
                'registro de control de calidad.'
            ),
            'cuando_elegirlo': (
                'Cuando una asociación, un proyecto o una carrera necesita '
                'producto terminado y no va a operar la planta.'
            ),
            'tiempo_estimado_texto': '2 días laborables por lote de hasta 200 litros',
            'tipo_servicio': 'maquila_academica',
            'equipo': 'LAC-EQ-PASTEUR',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Indica los litros, el sabor y el envase. Si traes la leche, '
                'llega la madrugada del proceso con su prueba de alcohol.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '5.00', 'horas_equipo': '6.00', 'costo_equipo': '4.50',
            'horas_mano_obra': '6.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '20.00',
            'consumibles': [
                ('LAC-INS-CULTIVO-YOG', '1.000', True),
                ('LAC-INS-AZUCAR', '8.000', True),
                ('LAC-EMP-ENVASE-1L', '100.000', True),
                ('LAC-EMP-ETIQUETA', '100.000', True),
            ],
        },
        {
            'code': 'LAC-SRV-ANALISIS',
            'familia': 'Control de calidad',
            'nombre': 'Análisis fisicoquímico de leche',
            'descripcion': (
                'Pruebas de plataforma de la leche cruda: densidad, acidez, '
                'prueba de alcohol, grasa y temperatura de recepción.'
            ),
            'resultado_entregado': (
                'Informe por muestra con los resultados y su comparación con '
                'la norma de leche cruda.'
            ),
            'cuando_elegirlo': (
                'Cuando un productor, una asociación o un proyecto necesita '
                'saber si su leche cumple para acopio o proceso.'
            ),
            'tiempo_estimado_texto': '1 día laborable',
            'tipo_servicio': 'analisis',
            'equipo': 'LAC-EQ-TANQUE',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega la muestra refrigerada en frasco limpio de 250 ml, '
                'rotulada con procedencia y hora de ordeño.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': False,
            'tarifa_base': '2.00', 'horas_equipo': '0.50', 'costo_equipo': '2.00',
            'horas_mano_obra': '1.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('LAC-REA-ALCOHOL', '5.000', True),
                ('LAC-REA-NAOH', '10.000', True),
                ('LAC-REA-FENOL', '1.000', False),
            ],
        },
        {
            'code': 'LAC-SRV-PRACTICA',
            'familia': 'Docencia',
            'nombre': 'Práctica supervisada de elaboración de queso fresco',
            'descripcion': (
                'El laboratorista conduce con el grupo la elaboración de queso '
                'fresco de principio a fin: recepción, pasteurización, cuajado, '
                'moldeo, prensado y empaque.'
            ),
            'resultado_entregado': (
                'Quesos elaborados por el grupo, con su registro de proceso y '
                'los resultados de control de calidad.'
            ),
            'cuando_elegirlo': (
                'Cuando el grupo no opera todavía la planta por su cuenta y '
                'necesita que la práctica la dirija el laboratorista.'
            ),
            'tiempo_estimado_texto': '1 jornada de seis horas',
            'tipo_servicio': 'practica',
            'equipo': 'LAC-EQ-TINA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Grupos de hasta diez personas con cofia, mascarilla y botas. '
                'La guía de práctica se entrega con la solicitud.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '3.00', 'horas_equipo': '4.00', 'costo_equipo': '4.50',
            'horas_mano_obra': '6.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '10.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('LAC-INS-LECHE', '50.000', True),
                ('LAC-INS-CUAJO', '5.000', True),
                ('LAC-INS-CLORURO', '10.000', True),
                ('LAC-INS-SAL', '0.500', True),
                ('LAC-MAT-MOLDE', '10.000', False),
            ],
        },
        {
            'code': 'LAC-SRV-VISITA',
            'familia': 'Vinculación',
            'nombre': 'Visita técnica a la planta',
            'descripcion': (
                'Recorrido guiado por la recepción, el proceso térmico, la '
                'quesería, la fermentación y la cámara de frío, con degustación.'
            ),
            'resultado_entregado': 'Recorrido guiado con explicación de cada etapa y degustación final.',
            'cuando_elegirlo': (
                'Para colegios, asociaciones de productores y visitas '
                'institucionales que quieren conocer cómo se produce.'
            ),
            'tiempo_estimado_texto': '2 horas',
            'tipo_servicio': 'visita',
            'equipo': 'LAC-EQ-PASTEUR',
            'requiere_archivos': False,
            'requisitos_usuario': 'Grupos de hasta veinte personas; la planta provee cofias y mascarillas.',
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('LAC-PRO-COFIA', '20.000', True),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Marcela Ortega',
            'rol': 'coordinacion',
            'email': 'planta.lacteos@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2860',
            'descripcion': 'Coordina la producción, la inocuidad y la agenda de las líneas de proceso.',
            'horario_atencion': 'Lunes a viernes · 07:00–17:00',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Andrés Puetate',
            'rol': 'laboratorista',
            'email': 'laboratorista.lacteos@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2861',
            'descripcion': 'Recibe la leche, opera las líneas, conduce las prácticas y cierra cada lote.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    # El sílabo práctico de la asignatura que programa la planta: un tema por
    # semana, con el proceso que se practica y los ejercicios del aula.
    'asignaturas': [
        {
            'codigo': 'LAC-ASIG-TECLAC', 'nombre': 'Tecnología de Lácteos', 'carrera': 'Alimentos',
            'semestre': 'Sexto semestre', 'estudiantes': 16,
            'descripcion': 'Procesos de la planta piloto de lácteos, del análisis de la leche al plan de producción.',
            'temas': [
                {'orden': 1, 'nombre': 'Recepción y control de calidad de la leche', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Prueba de alcohol, acidez y densidad; registro del lote en el trazador.',
                 'resultado': 'Decide si un lote de leche entra al proceso con base en sus análisis.'},
                {'orden': 2, 'nombre': 'Leche pasteurizada', 'receta': 'LAC-REC-LECHE-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Curva de pasteurización y registro del lote.',
                 'resultado': 'Conduce la pasteurización con control de tiempo y temperatura.'},
                {'orden': 3, 'nombre': 'Yogur batido de mora', 'receta': 'LAC-REC-YOGUR-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Balance de materia de la corrida: azúcar y pulpa incorporadas.',
                 'resultado': 'Fermenta, bate y envasa un yogur con la acidez final prevista.'},
                {'orden': 4, 'nombre': 'Queso fresco', 'receta': 'LAC-REC-QUESO-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Rendimiento quesero: litros de leche por kilo de queso.',
                 'resultado': 'Coagula, corta, desuera y prensa un queso fresco con el rendimiento esperado.'},
                {'orden': 5, 'nombre': 'Queso mozzarella', 'receta': 'LAC-REC-MOZZARELLA-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Punto de hilado y control de pH.',
                 'resultado': 'Hila y moldea una pasta filata en su punto.'},
                {'orden': 6, 'nombre': 'Queso semimaduro', 'receta': 'LAC-REC-SEMIMADURO-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Plan de maduración y control de la cámara.',
                 'resultado': 'Prensa y lleva a maduración un queso con su registro de cámara.'},
                {'orden': 7, 'nombre': 'Crema de leche', 'receta': 'LAC-REC-CREMA-100', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Balance del descremado: crema y leche descremada.',
                 'resultado': 'Descrema y estandariza la crema para la mantequilla.'},
                {'orden': 8, 'nombre': 'Mantequilla', 'receta': 'LAC-REC-MANTEQUILLA-20', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Rendimiento del batido y mazada obtenida.',
                 'resultado': 'Bate, lava y amasa la mantequilla con la humedad prevista.'},
                {'orden': 9, 'nombre': 'Manjar de leche', 'receta': 'LAC-REC-MANJAR-50', 'software': ['LAC-SW-TRAZA'],
                 'ejercicios': 'Balance de energía de la concentración en la marmita.',
                 'resultado': 'Concentra el manjar hasta los grados Brix esperados.'},
                {'orden': 10, 'nombre': 'Balance de materia y energía de la planta', 'software': ['LAC-SW-TRAZA', 'LAC-SW-BALANCE'],
                 'ejercicios': 'Balance de una semana de producción con los datos reales de las corridas.',
                 'resultado': 'Cierra el balance de materia y energía de un proceso completo.'},
                {'orden': 11, 'nombre': 'Balance de línea, métodos y tiempos',
                 'ejercicios': 'Cursograma analítico y balance de línea con los tiempos de las etapas.',
                 'resultado': 'Propone un balance de línea a partir de los tiempos medidos.'},
                {'orden': 12, 'nombre': 'Plan maestro y requerimiento de materiales',
                 'ejercicios': 'Plan maestro de una semana y el MRP de sus insumos.',
                 'resultado': 'Formula el plan maestro y el requerimiento de materiales de la planta.'},
            ],
        },
    ],
    # Qué mide la planta, con qué límite y en qué momento: el plan que libera
    # cada lote y que sostiene el plan HACCP de sus procesos.
    'calidad': [
        {
            'codigo': 'LAC-CAL-RECEPCION-LECHE',
            'nombre': 'Recepción de leche cruda',
            'momento': 'recepcion',
            'consumible': 'LAC-INS-LECHE',
            'descripcion': (
                'La leche se controla en la plataforma antes de descargar al tanque: la que no cumple '
                'se devuelve al proveedor sin entrar a la planta. Es el primer punto crítico de todos '
                'los procesos, propios y de maquila.'
            ),
            'parametros': [
                {'nombre': 'Temperatura de llegada', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '6',
                 'metodo': 'Termómetro de sonda en el bidón'},
                {'nombre': 'Acidez titulable', 'unidad_medida': '°D', 'minimo': '14', 'maximo': '18',
                 'metodo': 'Titulación con NaOH 0,1 N y fenolftaleína'},
                {'nombre': 'Densidad a 15 °C', 'unidad_medida': 'g/mL', 'minimo': '1.028', 'maximo': '1.034',
                 'metodo': 'Lactodensímetro de Quevenne'},
                {'nombre': 'Prueba de alcohol', 'tipo': 'cualitativo', 'valor_esperado': 'negativa',
                 'metodo': 'Alcohol al 68 % en volúmenes iguales'},
                {'nombre': 'Inhibidores y antibióticos', 'tipo': 'cualitativo', 'valor_esperado': 'negativa',
                 'metodo': 'Prueba rápida de betalactámicos'},
                {'nombre': 'Grasa', 'unidad_medida': '%', 'minimo': '3',
                 'metodo': 'Método Gerber', 'critico': False},
            ],
        },
        {
            'codigo': 'LAC-CAL-PROCESO-QUESO',
            'nombre': 'Control en proceso del queso fresco',
            'momento': 'proceso',
            'producto': 'LAC-PRD-QUESO-FRESCO',
            'descripcion': 'Lo que se vigila mientras corre el proceso; la pasteurización decide la inocuidad del lote.',
            'parametros': [
                {'nombre': 'Temperatura de pasteurización', 'unidad_medida': '°C', 'minimo': '63', 'maximo': '68',
                 'metodo': 'Curva registrada por el pasteurizador', 'etapa': ('LAC-REC-QUESO-100', 2)},
                {'nombre': 'Tiempo de sostenimiento', 'unidad_medida': 'min', 'minimo': '30',
                 'metodo': 'Cronómetro y registro de la corrida', 'etapa': ('LAC-REC-QUESO-100', 2)},
                {'nombre': 'Temperatura de cuajado', 'unidad_medida': '°C', 'minimo': '36', 'maximo': '39',
                 'metodo': 'Termómetro en la tina', 'etapa': ('LAC-REC-QUESO-100', 3), 'critico': False},
            ],
        },
        {
            'codigo': 'LAC-CAL-PROCESO-YOGUR',
            'nombre': 'Control en proceso del yogur',
            'momento': 'proceso',
            'producto': 'LAC-PRD-YOGUR-MORA',
            'descripcion': 'El tratamiento térmico alto y el pH final de la incubación definen el cuerpo y la vida útil.',
            'parametros': [
                {'nombre': 'Temperatura de pasteurización', 'unidad_medida': '°C', 'minimo': '83', 'maximo': '87',
                 'metodo': 'Curva registrada por el pasteurizador', 'etapa': ('LAC-REC-YOGUR-100', 2)},
                {'nombre': 'Temperatura de inoculación', 'unidad_medida': '°C', 'minimo': '42', 'maximo': '45',
                 'metodo': 'Termómetro en la tina', 'etapa': ('LAC-REC-YOGUR-100', 3), 'critico': False},
                {'nombre': 'pH al final de la incubación', 'minimo': '4.4', 'maximo': '4.7',
                 'metodo': 'Potenciómetro calibrado, muestra del centro', 'etapa': ('LAC-REC-YOGUR-100', 4)},
            ],
        },
        {
            'codigo': 'LAC-CAL-PROCESO-LECHE',
            'nombre': 'Control en proceso de la leche pasteurizada',
            'momento': 'proceso',
            'producto': 'LAC-PRD-LECHE-PAST',
            'descripcion': 'La pasteurización rápida se vigila con la temperatura y el tiempo del tubo de retención.',
            'parametros': [
                {'nombre': 'Temperatura de pasteurización HTST', 'unidad_medida': '°C', 'minimo': '72', 'maximo': '75',
                 'metodo': 'Registrador del pasteurizador', 'etapa': ('LAC-REC-LECHE-100', 3)},
                {'nombre': 'Tiempo de sostenimiento', 'unidad_medida': 's', 'minimo': '15',
                 'metodo': 'Registro del tubo de retención', 'etapa': ('LAC-REC-LECHE-100', 3)},
            ],
        },
        {
            'codigo': 'LAC-CAL-LIBERACION-QUESO',
            'nombre': 'Liberación de queso fresco',
            'momento': 'liberacion',
            'producto': 'LAC-PRD-QUESO-FRESCO',
            'descripcion': 'El lote sale de cuarentena cuando estos resultados están dentro del límite.',
            'parametros': [
                {'nombre': 'pH del queso', 'minimo': '6.1', 'maximo': '6.8',
                 'metodo': 'Potenciómetro de punción'},
                {'nombre': 'Humedad', 'unidad_medida': '%', 'maximo': '60',
                 'metodo': 'Secado en estufa a 102 °C'},
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '6',
                 'metodo': 'Termómetro en el centro de la horma'},
                {'nombre': 'Coliformes totales', 'unidad_medida': 'UFC/g', 'maximo': '100',
                 'metodo': 'Siembra en placa, lectura a 24 horas'},
                {'nombre': 'Aspecto, olor y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
        {
            'codigo': 'LAC-CAL-LIBERACION-YOGUR',
            'nombre': 'Liberación de yogur',
            'momento': 'liberacion',
            'producto': 'LAC-PRD-YOGUR-MORA',
            'descripcion': 'El yogur se libera con su acidez estabilizada y la cadena de frío cumplida.',
            'parametros': [
                {'nombre': 'pH del yogur', 'minimo': '4.2', 'maximo': '4.6',
                 'metodo': 'Potenciómetro calibrado'},
                {'nombre': 'Acidez titulable', 'unidad_medida': '% ácido láctico', 'minimo': '0.7', 'maximo': '1.1',
                 'metodo': 'Titulación con NaOH 0,1 N'},
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '6',
                 'metodo': 'Termómetro en la botella testigo'},
                {'nombre': 'Coliformes totales', 'unidad_medida': 'UFC/g', 'maximo': '10',
                 'metodo': 'Siembra en placa, lectura a 24 horas'},
                {'nombre': 'Consistencia, color y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
        {
            'codigo': 'LAC-CAL-LIBERACION-LECHE',
            'nombre': 'Liberación de leche pasteurizada',
            'momento': 'liberacion',
            'producto': 'LAC-PRD-LECHE-PAST',
            'descripcion': 'La fosfatasa negativa confirma que la pasteurización se cumplió: sin ella el lote no sale.',
            'parametros': [
                {'nombre': 'Fosfatasa alcalina', 'tipo': 'cualitativo', 'valor_esperado': 'negativa',
                 'metodo': 'Prueba de fosfatasa residual'},
                {'nombre': 'Acidez titulable', 'unidad_medida': '°D', 'minimo': '14', 'maximo': '18',
                 'metodo': 'Titulación con NaOH 0,1 N'},
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '4',
                 'metodo': 'Termómetro en la botella testigo'},
                {'nombre': 'Grasa', 'unidad_medida': '%', 'minimo': '2.8', 'maximo': '3.3',
                 'metodo': 'Método Gerber', 'critico': False},
            ],
        },
    ],
    # Lo que la planta exige para entrar, por categoría de persona: el
    # reglamento de ingreso de una planta de alimentos.
    'visitas': {
        'acepta': True,
        'personas_por_guia': 15,
        'texto': (
            'La planta recibe grupos de colegios, carreras y empresas en un recorrido guiado: la recepción de leche, '
            'la línea de proceso térmico vista desde el pasillo y la sala de capacitación y degustación. El grupo no entra '
            'a la línea en producción ni manipula producto; la planta entrega la cofia y toma la lista de asistencia en la puerta.'
        ),
    },
    'acceso': [
        {
            'codigo': 'LAC-ACC-INDUCCION', 'nombre': 'Inducción de seguridad e inocuidad', 'tipo': 'induccion',
            'aplica_a': [], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Buenas prácticas de manufactura, riesgos de la planta (vapor, superficies calientes, '
                'pisos húmedos, químicos de limpieza) y actuación en emergencias. La dicta la planta '
                'como una sesión de capacitación y vale un período académico.'
            ),
        },
        {
            'codigo': 'LAC-ACC-SALUD', 'nombre': 'Certificado de salud o carné de manipulador de alimentos',
            'tipo': 'sanitario', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'vigencia_dias': 365, 'momento': 'reservar',
            'descripcion': 'Quien manipula producto presenta su certificado vigente; el visitante no lo necesita porque no manipula.',
        },
        {
            'codigo': 'LAC-ACC-COFIA', 'nombre': 'Cofia desechable', 'tipo': 'proteccion', 'aplica_a': [],
            'consumible': 'LAC-PRO-COFIA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'La entrega la planta en la puerta; cubre todo el cabello.',
        },
        {
            'codigo': 'LAC-ACC-GUANTES', 'nombre': 'Guantes de nitrilo', 'tipo': 'proteccion',
            'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'consumible': 'LAC-PRO-GUANTES', 'cantidad_por_persona': '2', 'momento': 'ingresar',
            'descripcion': 'Un par para manipular producto y otro para la limpieza con detergente alcalino.',
        },
        {
            'codigo': 'LAC-ACC-MANDIL', 'nombre': 'Mandil o bata blanca limpia', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'La trae cada persona, limpia y de uso exclusivo en la planta.',
        },
        {
            'codigo': 'LAC-ACC-BOTAS', 'nombre': 'Botas blancas o cubrecalzado', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'Botas de caucho blancas para quien procesa; cubrecalzado para las visitas.',
        },
        {
            'codigo': 'LAC-ACC-RESTRICCIONES', 'nombre': 'Restricciones de ingreso', 'tipo': 'restriccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'Sin joyas ni relojes; sin comida, bebidas ni goma de mascar; celular fuera de la línea; '
                'cabello recogido bajo la cofia; uñas cortas y sin esmalte; sin heridas expuestas ni '
                'síntomas de enfermedad.'
            ),
        },
        {
            'codigo': 'LAC-ACC-ESCOLTA', 'nombre': 'Visitante acompañado y sin manipular producto',
            'tipo': 'restriccion', 'aplica_a': ['visitante'], 'momento': 'ingresar',
            'descripcion': 'Toda visita entra escoltada por personal de la planta y no toca producto ni equipos.',
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.lacteos',
            'nombres': 'Marcela',
            'apellidos': 'Ortega',
            'email': 'coordinacion.lacteos@citt.test',
            'cargo': 'Coordinación de la Planta Piloto de Lácteos',
            'rol': 'coordinacion',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.lacteos',
            'nombres': 'Andrés',
            'apellidos': 'Puetate',
            'email': 'laboratorista.lacteos@citt.test',
            'cargo': 'Laboratorista de la Planta Piloto de Lácteos',
            'rol': 'laboratorista',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'inventario': True, 'practicas': True,
            },
        },
    ],
    'ejemplos': [
        {
            'proposito': 'servicio',
            'ejemplo': (
                'Necesito que la planta elabore doscientos litros de yogur de '
                'mora para la feria de la asociación de productores de Tulcán. '
                'La leche la entrega la asociación la madrugada del proceso, '
                'con su prueba de alcohol hecha; la planta pone el cultivo, el '
                'azúcar y los envases de un litro. Pido que el lote salga '
                'etiquetado con fecha de vencimiento y que el informe de '
                'control de calidad acompañe la entrega, porque lo vendemos '
                'en la feria del sábado.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de séptimo semestre de Tecnología de Lácteos '
                'elaboraremos queso fresco en la sala de quesería. Cada '
                'equipo procesará cincuenta litros en la tina, cortará la '
                'cuajada, moldeará y prensará sus quesos, y registrará '
                'rendimiento y acidez. Buscamos que relacionen el cuajado '
                'con la temperatura y el calcio, y que calculen el '
                'rendimiento por litro. Somos diez, con cofia, mascarilla y '
                'botas, y necesitamos la jornada completa.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de desarrollo de un yogur con fruta de la '
                'zona necesitamos la línea de proceso y una incubadora durante '
                'dos jornadas. Somos dos investigadoras; procesaremos dos lotes '
                'de cien litros con dos niveles de pulpa y mediremos acidez, '
                'viscosidad y aceptación. La leche la aporta el centro '
                'experimental y el cultivo lo pone la planta.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre queso fresco reducido en '
                'sal necesito la sala de quesería y la tina durante tres '
                'jornadas, una por tratamiento. Procesaré cien litros por lote '
                'con tres niveles de sal y evaluaré rendimiento, humedad y '
                'aceptación. Pido el acompañamiento del laboratorista en el '
                'primer lote para ajustar el corte de la cuajada.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'LAC-ACT-PRACTICA',
            'nombre': 'Práctica de tecnología de lácteos',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Tecnología de Lácteos',
        },
        {
            'codigo': 'LAC-ACT-PRODUCCION',
            'nombre': 'Producción de derivados lácteos para venta',
            'proposito_codigo': 'servicio_cientifico_tecnologico',
            'subtipo_actividad': 'servicio_autorizado',
            'responsable': 'Coordinación de la Planta Piloto de Lácteos',
        },
        {
            'codigo': 'LAC-ACT-DESARROLLO',
            'nombre': 'Desarrollo de nuevos productos lácteos',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'desarrollo_experimental',
            'responsable': 'Investigador responsable del proyecto',
        },
        {
            'codigo': 'LAC-ACT-VINCULACION',
            'nombre': 'Capacitación a productores de leche',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
    ],
    # Lo que fluye por la planta, por tipo: terminados que se venden,
    # intermedios que vuelven a entrar, subproductos con valor y residuos que
    # solo se registran. Cada receta es la lista de materiales por corrida base.
    'productos': [
        {
            'codigo': 'LAC-PRD-QUESO-FRESCO',
            'familia': 'Quesos',
            'nombre': 'Queso fresco',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Bloque de 500 g envasado al vacío',
            'precio_venta': '6.50',
            'vida_util_dias': 15,
            'requiere_frio': True,
            'descripcion': (
                'Queso fresco pasteurizado, prensado y salado en seco; el producto '
                'insignia de la planta.'
            ),
        },
        {
            'codigo': 'LAC-PRD-YOGUR-MORA',
            'familia': 'Leches y fermentados',
            'nombre': 'Yogur de mora',
            'tipo': 'terminado',
            'unidad_medida': 'litro',
            'presentacion': 'Botella de 1 litro',
            'precio_venta': '2.80',
            'vida_util_dias': 21,
            'requiere_frio': True,
            'descripcion': (
                'Yogur batido con pulpa de mora del centro experimental, fermentado '
                'en la incubadora.'
            ),
        },
        {
            'codigo': 'LAC-PRD-LECHE-PAST',
            'familia': 'Leches y fermentados',
            'nombre': 'Leche pasteurizada',
            'tipo': 'terminado',
            'unidad_medida': 'litro',
            'presentacion': 'Botella de 1 litro',
            'precio_venta': '1.10',
            'vida_util_dias': 5,
            'requiere_frio': True,
            'descripcion': 'Leche entera pasteurizada y envasada el mismo día de la recepción.',
        },
        {
            'codigo': 'LAC-PRD-CREMA',
            'familia': 'Cremas y mantequilla',
            'nombre': 'Crema de leche',
            'tipo': 'intermedio',
            'unidad_medida': 'litro',
            'presentacion': 'Balde de 5 litros',
            'precio_venta': '4.50',
            'vida_util_dias': 10,
            'requiere_frio': True,
            'descripcion': (
                'Crema separada en la descremadora; vuelve a entrar en la mantequilla '
                'o se vende.'
            ),
        },
        {
            'codigo': 'LAC-PRD-SUERO',
            'familia': 'Derivados del suero',
            'nombre': 'Suero de quesería',
            'tipo': 'subproducto',
            'unidad_medida': 'litro',
            'presentacion': 'Bidón de 20 litros',
            'precio_venta': '0.10',
            'vida_util_dias': 2,
            'requiere_frio': True,
            'descripcion': (
                'Suero dulce del desuerado; se vende a productores porcícolas o pasa '
                'al centro experimental.'
            ),
        },
        {
            'codigo': 'LAC-PRD-AGUA-LAVADO',
            'familia': 'Leches y fermentados',
            'nombre': 'Agua de lavado y residuos de proceso',
            'tipo': 'residuo',
            'unidad_medida': 'litro',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': (
                'Efluente del lavado de equipos y línea; se registra para el control '
                'ambiental.'
            ),
        },
        {
            'codigo': 'LAC-PRD-MOZZARELLA',
            'familia': 'Quesos',
            'nombre': 'Queso mozzarella',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Bloque de 500 g envasado al vacío',
            'precio_venta': '8.50',
            'vida_util_dias': 20,
            'requiere_frio': True,
            'descripcion': 'Queso de pasta hilada para pizza y cocina; cuajada acidificada e hilada en agua caliente.',
        },
        {
            'codigo': 'LAC-PRD-QUESO-SEMIMADURO',
            'familia': 'Quesos',
            'nombre': 'Queso semimaduro',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Horma de 1 kg encerada',
            'precio_venta': '9.00',
            'vida_util_dias': 90,
            'requiere_frio': True,
            'descripcion': 'Queso prensado, salado en salmuera y madurado treinta días en cámara.',
        },
        {
            'codigo': 'LAC-PRD-MANTEQUILLA',
            'familia': 'Cremas y mantequilla',
            'nombre': 'Mantequilla',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Bloque de 250 g en papel parafinado',
            'precio_venta': '7.00',
            'vida_util_dias': 30,
            'requiere_frio': True,
            'descripcion': 'Mantequilla con sal batida a partir de la crema madurada del descremado.',
        },
        {
            'codigo': 'LAC-PRD-MANJAR',
            'familia': 'Dulces de leche',
            'nombre': 'Manjar de leche',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Frasco de 250 g',
            'precio_venta': '5.50',
            'vida_util_dias': 45,
            'requiere_frio': False,
            'descripcion': 'Leche concentrada con azúcar hasta 70 °Brix en la marmita; envasado en caliente.',
        },
        {
            'codigo': 'LAC-PRD-MAZADA',
            'familia': 'Cremas y mantequilla',
            'nombre': 'Mazada de mantequilla',
            'tipo': 'subproducto',
            'unidad_medida': 'litro',
            'presentacion': 'Bidón de 20 litros',
            'precio_venta': '0.20',
            'vida_util_dias': 2,
            'requiere_frio': True,
            'descripcion': 'Líquido que queda al batir la crema; se vende para alimentación animal o se usa en bebidas.',
        },
        {
            'codigo': 'LAC-PRD-LECHE-DESCREMADA',
            'familia': 'Leches y fermentados',
            'nombre': 'Leche descremada',
            'tipo': 'intermedio',
            'unidad_medida': 'litro',
            'presentacion': 'A granel en tanque',
            'precio_venta': '0.90',
            'vida_util_dias': 3,
            'requiere_frio': True,
            'descripcion': 'Lo que queda de la leche al separar la crema; vuelve a entrar en quesos y yogur descremados.',
        },
        {
            'codigo': 'LAC-PRD-AGUA-EVAPORADA',
            'familia': 'Dulces de leche',
            'nombre': 'Agua evaporada en la concentración',
            'tipo': 'residuo',
            'unidad_medida': 'litro',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': 'Vapor de agua que sale de la marmita al concentrar el manjar; solo se registra en el balance.',
        },
    ],
    'recetas': [
        {
            'codigo': 'LAC-REC-QUESO-100',
            'software': ['LAC-SW-TRAZA', 'LAC-SW-LINEA'],
            'nombre': 'Queso fresco por 100 litros de leche',
            'producto': 'LAC-PRD-QUESO-FRESCO',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '12',
            'duracion_horas': '6',
            'instrucciones': (
                'Pasteurizar a 65 °C por 30 minutos, enfriar a 38 °C, añadir cloruro '
                'de calcio y cuajo, cortar la cuajada a los 40 minutos, desuerar, '
                'salar, moldear y prensar dos horas.'
            ),
            # El proceso paso a paso: tipo del cursograma, dónde, tiempos,
            # personas, cuánta masa continúa y los puntos críticos de control.
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez, densidad y prueba de alcohol de la leche', 'limite': '14 a 18 °D; 1,028 a 1,034; alcohol negativo', 'instrucciones': 'Filtrar, medir la temperatura y tomar la muestra para el laboratorio de calidad antes de descargar al tanque.'},
                {'nombre': 'Pasteurización', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '65 °C durante 30 minutos', 'instrucciones': 'Calentar con agitación, sostener el tiempo y registrar la curva.'},
                {'nombre': 'Enfriamiento y adición de cloruro y cuajo', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 20, 'personas': 2, 'instrucciones': 'Bajar a 38 °C, disolver el cloruro de calcio y añadir el cuajo diluido; agitar un minuto.'},
                {'nombre': 'Coagulación', 'tipo': 'espera', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 0, 'espera': 40, 'personas': 0, 'instrucciones': 'Reposo sin agitar hasta el corte limpio.'},
                {'nombre': 'Corte y desuerado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 2, 'rendimiento': '14', 'instrucciones': 'Cortar con la lira en cubos de un centímetro, agitar suave y retirar el suero.'},
                {'nombre': 'Salado y moldeado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 3, 'rendimiento': '98', 'instrucciones': 'Salar en seco, llenar los moldes con paño y voltear.'},
                {'nombre': 'Prensado', 'tipo': 'espera', 'equipo': 'LAC-EQ-PRENSA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 10, 'espera': 120, 'personas': 1, 'rendimiento': '86', 'instrucciones': 'Dos horas de prensa con un volteo a la hora.'},
                {'nombre': 'Empaque y etiquetado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 30, 'personas': 2, 'instrucciones': 'Bloques de 500 g al vacío con etiqueta de lote y vencimiento.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25', 'instrucciones': 'En gavetas limpias, sin apilar más de cuatro.'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 1440, 'personas': 0, 'instrucciones': 'A 4 °C hasta la liberación por calidad.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2, 'instrucciones': 'Enjuague, detergente alcalino, enjuague y sanitizante; registrar en la bitácora.'},
            ],
            # Insumo, cantidad por corrida base, obligatorio y la etapa en la que entra.
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-INS-CUAJO', '10', True, 3),
                ('LAC-INS-CLORURO', '20', True, 3),
                ('LAC-INS-SAL', '0.4', True, 6),
                ('LAC-EMP-FUNDA-QUESO', '24', True, 8),
                ('LAC-EMP-ETIQUETA', '24', True, 8),
                ('LAC-MAT-PANO', '2', False, 6),
            ],
            # Salida, cantidad por corrida base y la etapa en la que sale.
            'salidas': [
                ('LAC-PRD-SUERO', '85', 5),
                ('LAC-PRD-AGUA-LAVADO', '60', 11, True),
            ],
        },
        {
            'codigo': 'LAC-REC-YOGUR-100',
            'software': ['LAC-SW-TRAZA', 'LAC-SW-BALANCE'],
            'nombre': 'Yogur de mora por 100 litros de leche',
            'producto': 'LAC-PRD-YOGUR-MORA',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '116',
            'duracion_horas': '8',
            'instrucciones': (
                'Pasteurizar a 85 °C por 10 minutos, enfriar a 43 °C, inocular el '
                'cultivo, incubar hasta pH 4,6, batir con la pulpa y el azúcar, '
                'envasar y refrigerar.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_critico': True, 'parametro': 'Acidez, densidad y antibióticos', 'limite': '14 a 18 °D; 1,028 a 1,034; antibióticos negativo', 'instrucciones': 'La leche con antibióticos no fermenta: la prueba decide si la corrida arranca.'},
                {'nombre': 'Pasteurización a 85 °C', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 40, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '85 °C durante 10 minutos', 'instrucciones': 'Tratamiento alto para desnaturalizar las proteínas del suero y dar cuerpo al yogur.'},
                {'nombre': 'Enfriamiento e inoculación', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 25, 'personas': 1, 'instrucciones': 'Bajar a 43 °C y sembrar el cultivo con agitación suave.'},
                {'nombre': 'Incubación', 'tipo': 'espera', 'equipo': 'LAC-EQ-INCUBADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 5, 'espera': 360, 'personas': 0, 'punto_control': True, 'parametro': 'pH al final de la incubación', 'limite': '4,6', 'instrucciones': 'Seis horas a 43 °C; medir el pH cada hora desde la cuarta.'},
                {'nombre': 'Batido con azúcar y pulpa', 'tipo': 'operacion', 'equipo': 'LAC-EQ-INCUBADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 30, 'personas': 2, 'instrucciones': 'Romper el gel, integrar el azúcar y la pulpa de mora en frío.'},
                {'nombre': 'Envasado y etiquetado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 45, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Botellas de un litro con tapa y etiqueta de lote.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 720, 'personas': 0, 'instrucciones': 'Doce horas a 4 °C antes de liberar.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2, 'instrucciones': 'Enjuague, detergente alcalino, enjuague y sanitizante.'},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-INS-CULTIVO-YOG', '1', True, 3),
                ('LAC-INS-AZUCAR', '8', True, 5),
                ('LAC-INS-PULPA-MORA', '10', True, 5),
                ('LAC-EMP-ENVASE-1L', '116', True, 6),
                ('LAC-EMP-ETIQUETA', '116', True, 6),
            ],
            'salidas': [
                ('LAC-PRD-AGUA-LAVADO', '40', 9, True),
            ],
        },
        {
            'codigo': 'LAC-REC-LECHE-100',
            'software': ['LAC-SW-TRAZA'],
            'nombre': 'Leche pasteurizada por 100 litros',
            'producto': 'LAC-PRD-LECHE-PAST',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '95',
            'duracion_horas': '2',
            'instrucciones': (
                'Descremar parcialmente, pasteurizar a 72 °C por 15 segundos, '
                'enfriar a 4 °C y envasar.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez, densidad y temperatura de llegada', 'limite': '14 a 18 °D; 1,028 a 1,034; 6 °C o menos'},
                {'nombre': 'Descremado parcial', 'tipo': 'operacion', 'equipo': 'LAC-EQ-DESCREMADORA', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 20, 'personas': 1, 'rendimiento': '97', 'instrucciones': 'Estandarizar la grasa al 3 %; la crema va a un balde rotulado.'},
                {'nombre': 'Pasteurización HTST', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 30, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '72 °C durante 15 segundos'},
                {'nombre': 'Enfriamiento a 4 °C', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 15, 'personas': 1},
                {'nombre': 'Envasado y etiquetado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 40, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Botellas de un litro; la primera y la última se apartan como muestra.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 240, 'personas': 0},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-EMP-ENVASE-1L', '95', True, 5),
                ('LAC-EMP-ETIQUETA', '95', True, 5),
            ],
            'salidas': [
                ('LAC-PRD-CREMA', '3', 2),
                ('LAC-PRD-AGUA-LAVADO', '30', 8, True),
            ],
        },
        {
            'codigo': 'LAC-REC-MOZZARELLA-100',
            'software': ['LAC-SW-TRAZA'],
            'nombre': 'Queso mozzarella por 100 litros de leche',
            'producto': 'LAC-PRD-MOZZARELLA',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '10',
            'duracion_horas': '7',
            'instrucciones': (
                'Pasteurizar, inocular con cultivo termófilo y cuajo, cortar y '
                'desuerar, dejar acidificar la cuajada hasta pH 5,2, hilar en agua '
                'a 80 °C, moldear, salar en salmuera y envasar al vacío.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez, densidad y prueba de alcohol de la leche', 'limite': '14 a 18 °D; 1,028 a 1,034; alcohol negativo'},
                {'nombre': 'Pasteurización', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '65 °C durante 30 minutos'},
                {'nombre': 'Enfriamiento e inoculación', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 20, 'personas': 2, 'instrucciones': 'Bajar a 36 °C, sembrar el cultivo termófilo y añadir el cuajo diluido.'},
                {'nombre': 'Coagulación', 'tipo': 'espera', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 0, 'espera': 30, 'personas': 0},
                {'nombre': 'Corte y desuerado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 2, 'rendimiento': '14', 'instrucciones': 'Cortar en cubos de dos centímetros, agitar y retirar el suero.'},
                {'nombre': 'Acidificación de la cuajada', 'tipo': 'espera', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 10, 'espera': 120, 'personas': 0, 'rendimiento': '98', 'punto_control': True, 'parametro': 'pH de la cuajada antes de hilar', 'limite': '5,2 a 5,3', 'instrucciones': 'La cuajada reposa apilada hasta el pH de hilado; medir cada veinte minutos.'},
                {'nombre': 'Hilado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-HILADORA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 2, 'rendimiento': '76', 'punto_control': True, 'parametro': 'Temperatura del agua de hilado', 'limite': '78 a 82 °C', 'instrucciones': 'Hilar en tandas de veinte kilos con guantes térmicos.'},
                {'nombre': 'Moldeo y salmuera', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 2, 'rendimiento': '97', 'instrucciones': 'Bloques de 500 g en moldes y veinte minutos en salmuera fría.'},
                {'nombre': 'Empaque al vacío', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 30, 'personas': 2},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 720, 'personas': 0},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-INS-CULTIVO-TERMO', '1', True, 3),
                ('LAC-INS-CUAJO', '10', True, 3),
                ('LAC-INS-SAL', '2', True, 8, 'no'),
                ('LAC-EMP-FUNDA-QUESO', '20', True, 9),
                ('LAC-EMP-ETIQUETA', '20', True, 9),
            ],
            'salidas': [
                ('LAC-PRD-SUERO', '85', 5),
                ('LAC-PRD-AGUA-LAVADO', '60', 12, True),
            ],
        },
        {
            'codigo': 'LAC-REC-SEMIMADURO-100',
            'software': ['LAC-SW-TRAZA'],
            'nombre': 'Queso semimaduro por 100 litros de leche',
            'producto': 'LAC-PRD-QUESO-SEMIMADURO',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '10',
            'duracion_horas': '10',
            'instrucciones': (
                'Pasteurizar, inocular con cultivo mesófilo, cloruro y cuajo, cortar, '
                'agitar y desuerar, moldear, prensar cuatro horas, salar en salmuera, '
                'encerar y madurar treinta días a 12 °C.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez, densidad y prueba de alcohol de la leche', 'limite': '14 a 18 °D; 1,028 a 1,034; alcohol negativo'},
                {'nombre': 'Pasteurización', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '65 °C durante 30 minutos'},
                {'nombre': 'Inoculación y adición de cloruro y cuajo', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 25, 'personas': 2, 'instrucciones': 'Bajar a 32 °C, sembrar el cultivo mesófilo, madurar treinta minutos y añadir cloruro y cuajo.'},
                {'nombre': 'Coagulación', 'tipo': 'espera', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 0, 'espera': 40, 'personas': 0},
                {'nombre': 'Corte, agitado y desuerado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-TINA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 45, 'personas': 2, 'rendimiento': '14', 'instrucciones': 'Cortar en grano de arroz, agitar treinta minutos con calentamiento suave y desuerar.'},
                {'nombre': 'Moldeado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 20, 'personas': 3, 'rendimiento': '99', 'instrucciones': 'Hormas de un kilo con tela.'},
                {'nombre': 'Prensado', 'tipo': 'espera', 'equipo': 'LAC-EQ-PRENSA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 10, 'espera': 240, 'personas': 1, 'rendimiento': '90', 'instrucciones': 'Cuatro horas con dos volteos.'},
                {'nombre': 'Salado en salmuera', 'tipo': 'espera', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 10, 'espera': 720, 'personas': 1, 'rendimiento': '99', 'instrucciones': 'Doce horas en salmuera al 20 % a 12 °C.'},
                {'nombre': 'Oreo y recubrimiento con cera', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 60, 'personas': 2, 'instrucciones': 'Secar la corteza un día y encerar por inmersión.'},
                {'nombre': 'Maduración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-MADURACION', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 43200, 'personas': 0, 'rendimiento': '82', 'punto_control': True, 'parametro': 'Temperatura y humedad de la cámara', 'limite': '12 °C y 85 % de humedad', 'instrucciones': 'Treinta días con volteo cada dos días.'},
                {'nombre': 'Etiquetado y empaque', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 20, 'personas': 2},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-INS-CULTIVO-MESO', '1', True, 3),
                ('LAC-INS-CLORURO', '20', True, 3),
                ('LAC-INS-CUAJO', '10', True, 3),
                ('LAC-INS-SAL', '3', True, 8, 'no'),
                ('LAC-INS-CERA', '0.3', True, 9),
                ('LAC-EMP-ETIQUETA', '10', True, 11),
            ],
            'salidas': [
                ('LAC-PRD-SUERO', '85', 5),
                ('LAC-PRD-AGUA-LAVADO', '60', 12, True),
            ],
        },
        {
            'codigo': 'LAC-REC-MANTEQUILLA-20',
            'software': ['LAC-SW-TRAZA'],
            'nombre': 'Mantequilla por 20 litros de crema',
            'producto': 'LAC-PRD-MANTEQUILLA',
            'cantidad_base': '20',
            'unidad_base': 'litros de crema',
            'rendimiento_esperado': '8',
            'duracion_horas': '3',
            'instrucciones': (
                'La crema del descremado madura en frío desde el día anterior; se bate '
                'hasta separar la mazada, se lava, se amasa, se sala y se moldea.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la crema', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 10, 'personas': 1, 'punto_critico': True, 'parametro': 'Fosfatasa alcalina y temperatura de la crema pasteurizada', 'limite': 'Fosfatasa negativa; 5 °C o menos'},
                {'nombre': 'Maduración de la crema', 'tipo': 'espera', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 720, 'personas': 0, 'instrucciones': 'Doce horas a 8 °C para que la grasa cristalice.'},
                {'nombre': 'Batido', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MANTEQUILLERA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 40, 'personas': 1, 'rendimiento': '45', 'instrucciones': 'Batir a 12 °C hasta que los granos de mantequilla se separen de la mazada.'},
                {'nombre': 'Lavado y amasado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MANTEQUILLERA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 20, 'personas': 1, 'rendimiento': '92', 'instrucciones': 'Dos lavados con agua fría y amasado hasta que no suelte agua.'},
                {'nombre': 'Salado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 10, 'personas': 1, 'instrucciones': 'Dos por ciento de sal fina, incorporada en el amasado final.'},
                {'nombre': 'Moldeado y empaque', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 30, 'personas': 2, 'rendimiento': '97', 'instrucciones': 'Bloques de 250 g en papel parafinado con etiqueta.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 240, 'personas': 0},
                {'nombre': 'Limpieza de la mantequillera', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MANTEQUILLERA', 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 30, 'personas': 1},
            ],
            'insumos': [
                ('LAC-INS-CREMA', '20', True, 1, 'base'),
                ('LAC-INS-SAL', '0.16', True, 5),
                ('LAC-EMP-PAPEL-MANTEQUILLA', '32', True, 6),
                ('LAC-EMP-ETIQUETA', '32', True, 6),
            ],
            'salidas': [
                ('LAC-PRD-MAZADA', '11', 3),
                ('LAC-PRD-AGUA-LAVADO', '20', 9, True),
            ],
        },
        {
            'codigo': 'LAC-REC-MANJAR-50',
            'software': ['LAC-SW-TRAZA', 'LAC-SW-BALANCE'],
            'nombre': 'Manjar de leche por 50 litros de leche',
            'producto': 'LAC-PRD-MANJAR',
            'cantidad_base': '50',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '25',
            'duracion_horas': '7',
            'instrucciones': (
                'Neutralizar la leche con bicarbonato, añadir azúcar y glucosa, '
                'concentrar en la marmita con agitación hasta 70 °Brix y envasar en caliente.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez y densidad de la leche', 'limite': '14 a 18 °D; 1,028 a 1,034'},
                {'nombre': 'Neutralización y mezcla', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MARMITA', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 15, 'personas': 1, 'instrucciones': 'Disolver el bicarbonato en la leche fría y añadir el azúcar y la glucosa.'},
                {'nombre': 'Concentración con agitación', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MARMITA', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 240, 'personas': 1, 'rendimiento': '41', 'punto_critico': True, 'parametro': 'Sólidos solubles al final de la concentración', 'limite': '68 a 72 °Brix', 'instrucciones': 'Vapor abierto y agitación continua; medir con el refractómetro desde la tercera hora.'},
                {'nombre': 'Envasado en caliente', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 30, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Frascos de 250 g llenados a más de 80 °C y tapados de inmediato.'},
                {'nombre': 'Enfriamiento', 'tipo': 'espera', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 0, 'espera': 120, 'personas': 0},
                {'nombre': 'Etiquetado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'LAC-AREA-QUESERIA', 'duracion': 15, 'personas': 1},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Almacenamiento', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 240, 'personas': 0},
                {'nombre': 'Limpieza de la marmita', 'tipo': 'operacion', 'equipo': 'LAC-EQ-MARMITA', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '50', True, 1, 'base'),
                ('LAC-INS-BICARBONATO', '25', True, 2),
                ('LAC-INS-AZUCAR', '10', True, 2),
                ('LAC-INS-GLUCOSA', '1', True, 2),
                ('LAC-EMP-FRASCO-MANJAR', '100', True, 4),
                ('LAC-EMP-ETIQUETA', '100', True, 6),
            ],
            'salidas': [
                ('LAC-PRD-AGUA-EVAPORADA', '35.5', 3),
                ('LAC-PRD-AGUA-LAVADO', '30', 9, True),
            ],
        },
        {
            'codigo': 'LAC-REC-CREMA-100',
            'software': ['LAC-SW-TRAZA'],
            'nombre': 'Crema de leche por 100 litros de leche',
            'producto': 'LAC-PRD-CREMA',
            'cantidad_base': '100',
            'unidad_base': 'litros de leche',
            'rendimiento_esperado': '8',
            'duracion_horas': '2',
            'instrucciones': (
                'Calentar la leche a 40 °C, descremar, pasteurizar la crema, enfriar y '
                'envasar en baldes; la leche descremada vuelve a la planta.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la leche', 'tipo': 'inspeccion', 'equipo': 'LAC-EQ-TANQUE', 'espacio': 'LAC-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'punto_control': True, 'parametro': 'Acidez, densidad y grasa de la leche', 'limite': '14 a 18 °D; 1,028 a 1,034; 3,5 % de grasa o más'},
                {'nombre': 'Calentamiento a 40 °C', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 15, 'personas': 1},
                {'nombre': 'Descremado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-DESCREMADORA', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 20, 'personas': 1, 'rendimiento': '8', 'instrucciones': 'La crema sale por el tubo superior; la leche descremada vuelve al tanque.'},
                {'nombre': 'Pasteurización de la crema', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 30, 'personas': 1, 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización de la crema', 'limite': '85 °C durante 10 minutos'},
                {'nombre': 'Enfriamiento y envasado', 'tipo': 'operacion', 'equipo': 'LAC-EQ-ENVASADORA', 'espacio': 'LAC-AREA-FERMENTACION', 'duracion': 20, 'personas': 2, 'instrucciones': 'Baldes de cinco litros rotulados con lote y vencimiento.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '25'},
                {'nombre': 'Refrigeración', 'tipo': 'almacenamiento', 'equipo': 'LAC-EQ-CAMARA', 'espacio': 'LAC-CAMARA-FRIO', 'duracion': 0, 'espera': 240, 'personas': 0},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'LAC-EQ-PASTEUR', 'espacio': 'LAC-LINEA-PROCESO', 'duracion': 45, 'personas': 2},
            ],
            'insumos': [
                ('LAC-INS-LECHE', '100', True, 1, 'base'),
                ('LAC-EMP-BALDE-5L', '2', True, 5),
                ('LAC-EMP-ETIQUETA', '2', True, 5),
            ],
            'salidas': [
                ('LAC-PRD-LECHE-DESCREMADA', '92', 3),
                ('LAC-PRD-AGUA-LAVADO', '30', 8, True),
            ],
        },
    ],
}

LABORATORIOS = {
    'ia': IA,
    'biotecnologia': BIOTECNOLOGIA,
    'emprendimiento': EMPRENDIMIENTO,
    'lacteos': LACTEOS,
    # Las otras cuatro plantas piloto viven en su propio paquete: cada una
    # trae sus procesos y este archivo ya es bastante largo.
    **PLANTAS,
}
# Cada planta suma un proceso de referencia para las familias que no tenían ninguno y la
# especificación de liberación de cada producto con proceso de referencia.
LABORATORIOS.update({
    clave: ampliar(LABORATORIOS[clave], {**extra, 'calidad': ESPECIFICACIONES.get(clave, [])})
    for clave, extra in AMPLIACIONES.items()
})


class Command(BaseCommand):
    help = (
        'Deja operativas las unidades institucionales de prueba: los '
        'laboratorios de IA y Ciencia de Datos, Biotecnología Aplicada y '
        'Emprendimiento e Innovación Empresarial, y las cinco plantas piloto '
        '(lácteos, cárnicos, panificación, hortofrutícola y almidones), con '
        'equipos, espacios, software, inventario, servicios, procesos, planes '
        'de calidad, personal y actividades.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--laboratorio',
            choices=sorted(LABORATORIOS) + ['todos'],
            default='todos',
            help='Carga uno de los laboratorios o todos.',
        )
        parser.add_argument(
            '--password',
            help=(
                'Contraseña de las cuentas operativas del laboratorio. Sin ella '
                'se cargan los datos pero no se crean las cuentas.'
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        seleccion = options['laboratorio']
        password = options.get('password')
        if password and len(password) < 10:
            raise CommandError('La contraseña debe tener al menos 10 caracteres.')
        definiciones = (
            LABORATORIOS.values()
            if seleccion == 'todos'
            else [LABORATORIOS[seleccion]]
        )
        for definicion in definiciones:
            self._cargar(definicion, password)

    # ------------------------------------------------------------------ carga
    def _cargar(self, definicion, password):
        try:
            unidad = Unidad.objects.get(slug=definicion['slug'])
        except Unidad.DoesNotExist as error:
            # Un laboratorio que nace con esta carga trae su ficha institucional;
            # los que ya estaban registrados conservan la suya intacta.
            ficha = definicion.get('unidad')
            if not ficha:
                raise CommandError(
                    f'No existe una unidad con slug "{definicion["slug"]}".'
                ) from error
            unidad = Unidad.objects.create(slug=definicion['slug'], **ficha)

        unidad.capacidad_personas = definicion['capacidad_personas']
        campos_unidad = ['capacidad_personas']
        if unidad.dependencia == 'plantas_piloto':
            unidad.modo_operacion = definicion['modo_operacion']
            unidad.estado_catalogo = definicion['estado_catalogo']
            campos_unidad.extend(['modo_operacion', 'estado_catalogo'])
        unidad.save(update_fields=campos_unidad)
        self._horario_atencion(unidad, definicion)

        equipos, unidades_equipo = self._equipos(unidad, definicion)
        consumibles = self._consumibles(unidad, definicion, equipos, unidades_equipo)
        self._servicios(unidad, definicion, equipos, consumibles)
        self._software(unidad, definicion, unidades_equipo)
        self._espacios(unidad, definicion, unidades_equipo)
        familias = self._familias(unidad, definicion)
        self._produccion(unidad, definicion, consumibles, equipos, familias)
        self._calidad(unidad, definicion)
        self._seguridad(unidad, definicion, consumibles)
        self._asignaturas(unidad, definicion)
        self._responsables(unidad, definicion)
        self._vincular_responsables_servicios(unidad)
        self._actividades(unidad, definicion)
        if unidad.dependencia == 'plantas_piloto':
            # Una guía de práctica de referencia por proceso de referencia (2.6).
            crear_guias_de_referencia(unidad)
        self._ejemplos(unidad, definicion)
        self._fichas(unidad, definicion)
        self._conservacion(unidad)
        if password:
            self._cuentas(unidad, definicion, password)

        self.stdout.write(self.style.SUCCESS(
            f'{unidad.nombre}: {len(definicion["equipos"])} equipos, '
            f'{len(definicion["espacios"])} espacios, '
            f'{len(definicion["software"])} software, '
            f'{len(definicion["consumibles"])} artículos de inventario, '
            f'{len(definicion["servicios"])} servicios y '
            f'{len(definicion["responsables"])} personas en la ficha, '
            f'con {len(definicion["ejemplos"])} ejemplos de redacción propios'
            + (
                f', {Producto.objects.filter(unidad=unidad).count()} productos y '
                f'{len(definicion.get("recetas", []))} recetas'
                if definicion.get('productos') else ''
            )
            + '.'
        ))

    def _horario_atencion(self, unidad, definicion):
        """Horario que la unidad ofrece y palabra con la que cuenta su trabajo."""
        configuracion = unidad.configuracion_operativa
        apertura, cierre = definicion['horario_atencion']
        configuracion.hora_apertura_atencion = hora_del_dia(int(apertura[:2]), 0)
        configuracion.hora_cierre_atencion = hora_del_dia(int(cierre[:2]), 0)
        configuracion.unidad_de_trabajo = definicion['unidad_de_trabajo']
        # Las visitas guiadas: si la unidad las ofrece, con cuántas personas por guía y qué publica.
        visitas = definicion.get('visitas') or {}
        configuracion.acepta_visitas = bool(visitas.get('acepta'))
        configuracion.personas_por_guia = int(visitas.get('personas_por_guia', 15))
        configuracion.visitas_texto = visitas.get('texto', '')
        configuracion.full_clean()
        configuracion.save(update_fields=[
            'hora_apertura_atencion', 'hora_cierre_atencion', 'unidad_de_trabajo',
            'acepta_visitas', 'personas_por_guia', 'visitas_texto',
        ])

    def _equipos(self, unidad, definicion):
        equipos = {}
        unidades_equipo = {}
        for orden, datos in enumerate(definicion['equipos'], start=1):
            categoria, _ = CategoriaEquipo.objects.update_or_create(
                codigo=datos['categoria_codigo'],
                defaults={
                    'nombre': datos['categoria'],
                    'descripcion': f'Categoría operativa de {unidad.nombre}.',
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
                    'caracteristicas_publicas': datos['caracteristicas_publicas'],
                    'uso_publico': datos['uso_publico'],
                    'instrucciones_publicas': datos['instrucciones_publicas'],
                    'marca': datos.get('marca', ''),
                    'modelo': datos.get('modelo', ''),
                    'estado': 'disponible',
                    'familia_tecnologica': datos.get('familia_tecnologica', ''),
                    'software': datos['software'],
                    'admite_software_adicional': datos.get('admite_software_adicional', False),
                    'rol': datos.get('rol', 'principal'),
                    'cantidad': len(datos['unidades']),
                    'accesorios_incluidos': datos['accesorios'],
                    'accesorios_opcionales': [],
                },
            )
            equipo.categorias.set([categoria])
            self._datos_tecnicos_de_referencia(equipo)
            for posicion, codigo_unidad in enumerate(datos['unidades'], start=1):
                unidad_equipo, _ = actualizar_o_crear(
                    unidad_vigente, UnidadEquipo, 'codigo_unidad', codigo_unidad,
                    {
                        'equipo': equipo,
                        'laboratorio': unidad,
                        'estado_unidad': 'disponible',
                        'numero_serie': f'{definicion["prefijo"]}-{orden:03d}-{posicion}',
                        'observaciones': f'Registro operativo de {unidad.nombre}.',
                        'requiere_insumos': datos['requiere_insumos'],
                        'insumos_necesarios': datos['insumos'] or None,
                        'ubicacion_especifica': datos['ubicacion'],
                        'activa': True,
                    },
                )
                unidad_equipo.laboratorios.set([unidad])
                if unidad.dependencia == 'plantas_piloto' and '-EQP-' in codigo_unidad:
                    AliasCodigoUnidadEquipo.objects.update_or_create(
                        codigo=codigo_unidad.replace('-EQP-', '-UNIT-', 1),
                        defaults={'unidad_equipo': unidad_equipo},
                    )
                unidades_equipo.setdefault(datos['codigo'], []).append(unidad_equipo)
            equipos[datos['codigo']] = equipo
        # Los auxiliares se enlazan cuando ya existen todos los principales.
        for datos in definicion['equipos']:
            if datos.get('rol') == 'auxiliar':
                equipos[datos['codigo']].apoya_a.set(
                    [equipos[codigo] for codigo in datos.get('apoya_a', [])]
                )
        return equipos, unidades_equipo

    def _datos_tecnicos_de_referencia(self, equipo):
        """Valores típicos para validar la planta, marcados «por verificar».

        Nunca tocan un equipo con levantamiento validado; sin origen declarado solo
        llenan los campos vacíos, para no pisar un dato que alguien ya cargó a mano.
        """
        referencia = datos_de_referencia(equipo.codigo)
        if not referencia or equipo.origen_datos_tecnicos == 'medido':
            return
        if equipo.origen_datos_tecnicos != 'referencia':
            referencia = {
                campo: valor for campo, valor in referencia.items() if getattr(equipo, campo) in (None, '')
            }
        for campo, valor in referencia.items():
            setattr(equipo, campo, valor)
        equipo.origen_datos_tecnicos = 'referencia'
        equipo.save(update_fields=[*referencia, 'origen_datos_tecnicos'])

    def _consumibles(self, unidad, definicion, equipos, unidades_equipo):
        consumibles = {}
        hoy = timezone.localdate()
        for datos in definicion['consumibles']:
            defaults = {
                'unidad': unidad,
                'nombre': datos['nombre'],
                'clasificacion': datos['clasificacion'],
                'familia': datos.get('familia', ''),
                'variante': datos.get('variante', ''),
                'color': datos.get('color', ''),
                'presentacion': datos.get('presentacion', ''),
                'cantidad_por_presentacion': datos['cantidad_por_presentacion'],
                'unidad_medida': datos['unidad_medida'],
                'descripcion': datos['descripcion'],
                'instrucciones_solicitud': datos.get('instrucciones_solicitud', ''),
                'minimo': datos['minimo'],
                'stock_seguridad': (datos['minimo'] / 2).quantize(Decimal('0.001')),
                'stock_objetivo': max(datos['stock_total'], datos['minimo']),
                'plazo_reposicion_dias': datos.get('plazo_dias', 0),
                'proveedor_referencia': datos.get('proveedor', ''),
                'precio_unitario': datos['precio_unitario'],
                'ubicacion': datos['ubicacion'],
                'visible_en_reservas': True,
                'activo': True,
            }
            consumible, _ = Consumible.objects.update_or_create(
                codigo=datos['codigo'],
                defaults=defaults,
                create_defaults={**defaults, 'stock_total': datos['stock_total']},
            )
            for codigo_equipo in datos.get('equipos', []):
                ConsumiblePorEquipo.objects.update_or_create(
                    consumible=consumible,
                    equipo=equipos[codigo_equipo],
                    defaults={
                        'cantidad': datos['minimo'],
                        'minimo_alerta': datos['minimo'],
                        'ubicacion': datos['ubicacion'],
                    },
                )
            # Los reactivos se manejan por lote: vencen y se abren en un equipo.
            for lote in datos.get('lotes', []):
                equipo_en_uso = None
                if lote.get('equipo'):
                    equipo_en_uso = UnidadEquipo.objects.filter(
                        codigo_unidad=lote['equipo']
                    ).first()
                # Una recarga del catálogo no vuelve a recibir material ni
                # restablece saldos, ubicación o vencimientos ya gestionados.
                LoteConsumible.objects.get_or_create(
                    consumible=consumible,
                    codigo=lote['codigo'],
                    defaults={
                        'cantidad_inicial': lote['cantidad'],
                        'cantidad_actual': lote['cantidad'],
                        'estado': lote['estado'],
                        'bodega': consumible.ubicacion,
                        'fecha_ingreso': hoy - timedelta(days=30),
                        'fecha_apertura': hoy - timedelta(days=10) if lote['estado'] == 'en_uso' else None,
                        'fecha_vencimiento': (
                            hoy + timedelta(days=lote['vence_en_dias'])
                            if lote.get('vence_en_dias')
                            else None
                        ),
                        'equipo_en_uso': equipo_en_uso,
                        'costo_unitario': consumible.precio_unitario,
                        'observaciones': 'Lote operativo cargado con el inventario inicial.',
                    },
                )
            consumibles[datos['codigo']] = consumible
        return consumibles

    def _servicios(self, unidad, definicion, equipos, consumibles):
        for datos in definicion['servicios']:
            servicio, _ = FablabService.objects.update_or_create(
                code=datos['code'],
                defaults={
                    'nombre': datos['nombre'],
                    'descripcion': datos['descripcion'],
                    'resultado_entregado': datos['resultado_entregado'],
                    'cuando_elegirlo': datos['cuando_elegirlo'],
                    'tiempo_estimado_texto': datos['tiempo_estimado_texto'],
                    'tutorial_titulo': '',
                    'tutorial_youtube_url': '',
                    'permite_modelo_listo': datos['permite_modelo_listo'],
                    'permite_diseno_asistido': datos['permite_diseno_asistido'],
                    'permite_diseno_completo': datos['permite_diseno_completo'],
                    'unidad': unidad,
                    'tipo_servicio': datos['tipo_servicio'],
                    'familia': datos['familia'],
                    'activo': True,
                    'publico': True,
                    'requiere_reserva': True,
                    'requiere_revision_tecnica': True,
                    'requiere_cotizacion': True,
                    'requiere_archivos': datos['requiere_archivos'],
                    'requisitos_usuario': datos['requisitos_usuario'],
                    'unidad_cobro': datos.get('unidad_cobro', {
                        'analisis': 'Por muestra',
                        'maquila_academica': 'Por corrida',
                        'practica': 'Por sesión',
                        'capacitacion': 'Por grupo',
                        'uso_equipo': 'Por hora',
                        'visita': 'Por grupo',
                    }.get(datos['tipo_servicio'], 'Por solicitud')),
                    'formatos_archivo': datos['formatos_archivo'],
                    'tarifa_base': Decimal(datos['tarifa_base']),
                    'horas_equipo_estimadas': Decimal(datos['horas_equipo']),
                    'costo_hora_equipo': Decimal(datos['costo_equipo']),
                    'horas_mano_obra_estimadas': Decimal(datos['horas_mano_obra']),
                    'costo_hora_mano_obra': Decimal(datos['costo_mano_obra']),
                    'costo_diseno_asistido': Decimal(datos['diseno_asistido']),
                    'costo_diseno_completo': Decimal(datos['diseno_completo']),
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
                        'notas': 'Cantidad de referencia por pieza o muestra; la confirma el responsable.',
                    },
                )
                # El material del servicio se usa en la máquina que lo ejecuta,
                # salvo el de uso general (cofias, guantes), que no se ata a
                # ninguna máquina y sigue disponible en toda la unidad.
                if consumible.por_equipo.exists():
                    ConsumiblePorEquipo.objects.update_or_create(
                        consumible=consumible,
                        equipo=equipos[datos['equipo']],
                        defaults={
                            'cantidad': Decimal(cantidad),
                            'minimo_alerta': consumible.minimo,
                            'ubicacion': consumible.ubicacion,
                        },
                    )

    def _software(self, unidad, definicion, unidades_equipo):
        for datos in definicion['software']:
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
                for codigo in datos['equipos_instalados']
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ])

    def _espacios(self, unidad, definicion, unidades_equipo):
        integradas = []
        for orden, datos in enumerate(definicion['espacios'], start=1):
            vieja = integrada(unidad, datos['codigo'])
            if vieja is not None:
                # El área se fusionó en otra: no se reactiva y sus equipos van a la que la integró.
                integradas.append((area_vigente(vieja), datos))
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
                    'mobiliario_incluido': datos['mobiliario'],
                    'politica_reserva': datos['politica_reserva'],
                    'caracteristicas': datos['caracteristicas'],
                    'instrucciones_uso': datos['instrucciones'],
                    'activo': True,
                    'reservable': True,
                    'visitable': datos.get('visitable', False),
                    'orden': orden,
                },
            )
            # Los equipos que el área recibió de su ficha (sincronizar_equipamiento_areas) se conservan.
            de_su_ficha = espacio.equipos_asociados.filter(
                equipo__unidades__elementos_de_ficha__ficha__espacio=espacio,
            ).distinct()
            espacio.equipos_asociados.set([
                unidad_equipo
                for codigo in datos['equipos_asociados']
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ] + list(de_su_ficha))
        for vigente, datos in integradas:
            vigente.equipos_asociados.add(*[
                unidad_equipo
                for codigo in datos['equipos_asociados']
                for unidad_equipo in unidades_equipo.get(codigo, [])
            ])

    def _conservacion(self, unidad):
        """El límite de conservación de lo que requiere frío, donde la planta no fijó el suyo."""
        pendientes = Producto.objects.filter(
            unidad=unidad, requiere_frio=True, temperatura_maxima__isnull=True,
        ).select_related('familia')
        for producto in pendientes:
            producto.temperatura_maxima = temperatura_de_conservacion(
                producto.nombre, producto.familia.nombre if producto.familia_id else '',
            )
            producto.save(update_fields=['temperatura_maxima'])

    def _familias(self, unidad, definicion):
        """Crea el mismo maestro ordenado en cada carga de una planta."""
        nombres = TAXONOMIA_FAMILIAS.get(definicion.get('prefijo'), ())
        familias = {}
        for orden, nombre in enumerate(nombres, start=1):
            familia, _ = FamiliaProducto.objects.update_or_create(
                unidad=unidad,
                orden=orden,
                defaults={
                    'codigo': f'{definicion["prefijo"]}-F{orden:02d}',
                    'nombre': nombre,
                    'descripcion': '',
                    'activa': True,
                },
            )
            familias[nombre] = familia
        return familias

    def _produccion(self, unidad, definicion, consumibles, equipos, familias):
        """Lo que la unidad produce y con qué receta; solo las plantas lo traen."""
        if not definicion.get('productos'):
            return
        configuracion = unidad.configuracion_operativa
        configuracion.registra_produccion = True
        if configuracion.tarifa_energia_kwh is None:
            configuracion.tarifa_energia_kwh = TARIFA_ENERGIA_KWH
        if configuracion.costo_hora_persona is None:
            configuracion.costo_hora_persona = COSTO_HORA_PERSONA
        configuracion.save(update_fields=['registra_produccion', 'tarifa_energia_kwh', 'costo_hora_persona'])
        productos = {}
        for datos in definicion['productos']:
            productos[datos['codigo']], _ = Producto.objects.update_or_create(
                codigo=datos['codigo'],
                defaults={
                    'unidad': unidad,
                    'familia': familias.get(datos.get('familia')),
                    'nombre': datos['nombre'],
                    'tipo': datos['tipo'],
                    'unidad_medida': datos['unidad_medida'],
                    'presentacion': datos['presentacion'],
                    'precio_venta': Decimal(datos['precio_venta']),
                    'vida_util_dias': datos['vida_util_dias'],
                    'requiere_frio': datos['requiere_frio'],
                    'descripcion': datos['descripcion'],
                    'publico': datos['tipo'] != 'residuo',
                    'activo': True,
                },
            )
        self._productos_del_catalogo(unidad, definicion, familias)
        for datos in definicion.get('recetas', []):
            receta, _ = Receta.objects.update_or_create(
                codigo=datos['codigo'],
                defaults={
                    'unidad': unidad,
                    'familia': productos[datos['producto']].familia,
                    'producto': productos[datos['producto']],
                    'nombre': datos['nombre'],
                    'cantidad_base': Decimal(datos['cantidad_base']),
                    'unidad_base': datos['unidad_base'],
                    'rendimiento_esperado': Decimal(datos['rendimiento_esperado']),
                    'duracion_horas': Decimal(datos['duracion_horas']),
                    'instrucciones': datos['instrucciones'],
                    'activa': True,
                },
            )
            # Las etapas del proceso, en orden; las que sobran de una carga anterior se retiran.
            etapas = {}
            for orden, datos_etapa in enumerate(datos.get('etapas', []), start=1):
                espacio = area_vigente(
                    EspacioReservable.objects.filter(unidad=unidad, codigo=datos_etapa['espacio']).first()
                    if datos_etapa.get('espacio') else None
                )
                etapas[orden], _ = EtapaReceta.objects.update_or_create(
                    receta=receta,
                    orden=orden,
                    defaults={
                        'nombre': datos_etapa['nombre'],
                        'familia': receta.familia,
                        'tipo': datos_etapa['tipo'],
                        'equipo': equipos[datos_etapa['equipo']] if datos_etapa.get('equipo') else None,
                        'espacio': espacio,
                        'duracion_min': datos_etapa.get('duracion', 0),
                        'espera_min': datos_etapa.get('espera', 0),
                        'personas': datos_etapa.get('personas', 1),
                        'rendimiento_pct': Decimal(datos_etapa.get('rendimiento', '100')),
                        'distancia_m': Decimal(datos_etapa.get('distancia', '0')),
                        'punto_critico': datos_etapa.get('punto_critico', False),
                        'punto_control': datos_etapa.get('punto_control', False),
                        'parametro': datos_etapa.get('parametro', ''),
                        'limite': datos_etapa.get('limite', ''),
                        'instrucciones': datos_etapa.get('instrucciones', ''),
                    },
                )
            receta.etapas.filter(orden__gt=len(datos.get('etapas', []))).delete()
            receta.software.set(
                SoftwareDisponible.objects.filter(unidad=unidad, codigo__in=datos.get('software', []))
            )
            for datos_insumo in datos['insumos']:
                codigo, cantidad, obligatorio, numero_etapa = datos_insumo[:4]
                InsumoReceta.objects.update_or_create(
                    receta=receta,
                    consumible=consumibles[codigo],
                    defaults={
                        'cantidad': Decimal(cantidad),
                        'obligatorio': obligatorio,
                        'etapa': etapas.get(numero_etapa),
                        # Materia prima base, se incorpora al producto o auxiliar del proceso.
                        'forma_parte': datos_insumo[4] if len(datos_insumo) > 4 else 'si',
                    },
                )
            for datos_salida in datos.get('salidas', []):
                codigo, cantidad, numero_etapa = datos_salida[:3]
                SalidaReceta.objects.update_or_create(
                    receta=receta,
                    producto=productos[codigo],
                    defaults={
                        'cantidad': Decimal(cantidad), 'etapa': etapas.get(numero_etapa),
                        'externa_al_flujo': datos_salida[3] if len(datos_salida) > 3 else False,
                    },
                )

        # Los servicios por encargo se ligan a su proceso: sus materiales por lote son los insumos del proceso.
        for datos in definicion.get('servicios', []):
            if not datos.get('receta'):
                continue
            servicio = FablabService.objects.get(code=datos['code'])
            servicio.receta = Receta.objects.get(codigo=datos['receta'])
            servicio.materia_prima_cliente = bool(datos.get('materia_prima_cliente'))
            servicio.save(update_fields=['receta', 'materia_prima_cliente'])
            sincronizar_insumos_del_proceso(servicio)

        # Cada producto sin proceso parte del de referencia más cercano, marcado «derivado, por validar».
        derivar_procesos(unidad, definicion.get('plantillas_derivadas'), definicion.get('sin_derivar', {}))

    def _productos_del_catalogo(self, unidad, definicion, familias):
        """Completa los productos del mapa maestro sin fabricar recetas técnicas.

        Una receta necesita cantidades, etapas, equipos y controles validados.
        La taxonomía solo declara nombres; por eso los faltantes nacen como
        productos publicables y quedan disponibles para completar su ficha.
        """
        prefijo = definicion.get('prefijo')
        for orden_familia, (nombre_familia, referencias) in enumerate(
            PRODUCTOS_TAXONOMIA.get(prefijo, {}).items(), start=1,
        ):
            familia = familias[nombre_familia]
            for orden_producto, (nombre, unidad_medida) in enumerate(referencias, start=1):
                presentacion, precio, vida_util, frio, descripcion = FICHAS.get(
                    (prefijo, nombre), ('', '0', 0, False, ''),
                )
                producto = Producto.objects.filter(unidad=unidad, nombre__iexact=nombre).first()
                if producto is not None:
                    # Solo se completa lo vacío: lo que la planta editó no se pisa.
                    cambios = {
                        'familia': familia if producto.familia_id != familia.pk else None,
                        'presentacion': presentacion if not producto.presentacion else None,
                        'descripcion': descripcion if not producto.descripcion else None,
                        'precio_venta': Decimal(precio) if not producto.precio_venta else None,
                        'vida_util_dias': vida_util if not producto.vida_util_dias else None,
                        'requiere_frio': frio if not producto.presentacion and frio else None,
                    }
                    cambios = {campo: valor for campo, valor in cambios.items() if valor not in (None, '', 0)}
                    for campo, valor in cambios.items():
                        setattr(producto, campo, valor)
                    if cambios:
                        producto.save(update_fields=[*cambios, 'actualizado_en'])
                    continue
                Producto.objects.update_or_create(
                    codigo=f'{prefijo}-PRD-CAT-{orden_familia:02d}-{orden_producto:02d}',
                    defaults={
                        'unidad': unidad,
                        'familia': familia,
                        'nombre': nombre,
                        'tipo': 'terminado',
                        'unidad_medida': unidad_medida,
                        'presentacion': presentacion,
                        'precio_venta': Decimal(precio),
                        'vida_util_dias': vida_util,
                        'requiere_frio': frio,
                        'descripcion': descripcion,
                        'publico': True,
                        'activo': True,
                    },
                )

    def _calidad(self, unidad, definicion):
        """Qué mide la unidad, con qué límite y en qué momento; solo las plantas lo declaran."""
        for datos in definicion.get('calidad', []):
            plan, _ = PlanCalidad.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'nombre': datos['nombre'],
                    'momento': datos['momento'],
                    'producto': (
                        Producto.objects.get(unidad=unidad, codigo=datos['producto'])
                        if datos.get('producto') else None
                    ),
                    'consumible': (
                        Consumible.objects.get(unidad=unidad, codigo=datos['consumible'])
                        if datos.get('consumible') else None
                    ),
                    'descripcion': datos.get('descripcion', ''),
                    'activo': True,
                },
            )
            for orden, parametro in enumerate(datos['parametros'], start=1):
                etapa = None
                if parametro.get('etapa'):
                    receta_codigo, numero = parametro['etapa']
                    etapa = EtapaReceta.objects.filter(
                        receta__codigo=receta_codigo, orden=numero,
                    ).first()
                ParametroCalidad.objects.update_or_create(
                    plan=plan,
                    nombre=parametro['nombre'],
                    defaults={
                        'orden': orden,
                        'tipo': parametro.get('tipo', 'numerico'),
                        'unidad_medida': parametro.get('unidad_medida', ''),
                        'minimo': Decimal(parametro['minimo']) if parametro.get('minimo') else None,
                        'maximo': Decimal(parametro['maximo']) if parametro.get('maximo') else None,
                        'valor_esperado': parametro.get('valor_esperado', ''),
                        'metodo': parametro.get('metodo', ''),
                        'etapa': etapa,
                        'critico': parametro.get('critico', True),
                        'activo': True,
                    },
                )
            if plan.producto_id:
                plan.familia = plan.producto.familia
            parametro_con_familia = plan.parametros.filter(etapa__familia__isnull=False).select_related('etapa').first()
            if plan.familia_id is None and parametro_con_familia:
                plan.familia = parametro_con_familia.etapa.familia
            plan.save(update_fields=['familia'])

    def _fichas(self, unidad, definicion):
        """Registra el gobierno editorial sin duplicar el contenido de las fichas."""
        if unidad.dependencia != 'plantas_piloto':
            return

        def registrar(
            objeto, codigo, tipo, titulo, descripcion, familia=None, visible=True,
            *, estado=None, visibilidad=None,
        ):
            estado_inicial = estado or ('publicada' if visible else 'archivada')
            visibilidad_inicial = visibilidad or ('publica' if visible else 'interna')
            defaults = {
                'unidad': unidad,
                'familia': familia,
                'tipo': tipo,
                'titulo': titulo,
                'descripcion': descripcion or '',
                'estado': estado_inicial,
                'version': 1,
                'visibilidad': visibilidad_inicial,
                'content_type': ContentType.objects.get_for_model(objeto) if objeto is not None else None,
                'object_id': objeto.pk if objeto is not None else None,
            }
            ficha, creada = FichaContenido.objects.get_or_create(
                codigo=codigo,
                defaults=defaults,
            )
            if not creada:
                for campo in (
                    'unidad', 'familia', 'tipo', 'titulo', 'descripcion',
                    'content_type', 'object_id',
                ):
                    setattr(ficha, campo, defaults[campo])
                campos = [
                    'unidad', 'familia', 'tipo', 'titulo', 'descripcion',
                    'content_type', 'object_id', 'actualizado_en',
                ]
                if not visible:
                    ficha.estado = 'archivada'
                    ficha.visibilidad = 'interna'
                    campos.extend(['estado', 'visibilidad'])
                ficha.save(update_fields=campos)
            return ficha

        fichas_producto = {}
        for producto in Producto.objects.filter(unidad=unidad).select_related('familia'):
            fichas_producto[producto.pk] = registrar(
                producto, producto.codigo, 'producto', producto.nombre, producto.descripcion,
                producto.familia, producto.publico and producto.activo,
            )
        for receta in Receta.objects.filter(unidad=unidad).select_related('producto', 'familia'):
            ficha_receta = registrar(
                receta, receta.codigo, 'proceso', receta.nombre, receta.instrucciones,
                receta.familia, receta.activa,
            )
            if receta.producto_id in fichas_producto:
                ficha_receta.relacionadas.add(fichas_producto[receta.producto_id])
            for etapa in receta.etapas.filter(punto_critico=True):
                codigo_objeto = receta.codigo.split('-REC-', 1)[-1]
                ficha_pcc = registrar(
                    etapa, f'{definicion["prefijo"]}-PCC-{codigo_objeto}-{etapa.orden:02d}',
                    'pcc', etapa.nombre, etapa.instrucciones, etapa.familia, receta.activa,
                )
                ficha_pcc.relacionadas.add(ficha_receta)
        for equipo in UnidadEquipo.objects.filter(laboratorio=unidad).select_related('equipo'):
            registrar(
                equipo, equipo.codigo_unidad, 'equipo', equipo.equipo.nombre,
                equipo.equipo.descripcion, visible=equipo.activa,
                estado='en_revision' if equipo.activa else 'archivada',
                visibilidad='publica' if equipo.activa else 'interna',
            )
        for plan in PlanCalidad.objects.filter(unidad=unidad).select_related('familia'):
            registrar(plan, plan.codigo, 'especificacion', plan.nombre, plan.descripcion, plan.familia, plan.activo)
        for guia in GuiaActividadReserva.objects.filter(actividad__unidad=unidad).select_related('familia'):
            registrar(
                guia, guia.codigo_guia or f'{definicion["prefijo"]}-GUI-{guia.pk:04d}',
                'guia', guia.titulo, guia.descripcion, guia.familia,
                guia.activo and guia.estado_publicacion == 'publicada' and guia.visibilidad == 'publica',
            )
        for clave, titulo in (
            ('BALANCE', 'Balance de materia y energía'),
            ('LINEA', 'Balance de línea'),
            ('MATERIALES', 'Requerimiento de materiales'),
        ):
            registrar(
                None, f'{definicion["prefijo"]}-SIM-{clave}', 'simulador', titulo,
                'Simulador integrado que usa los datos vigentes de los procesos de la planta.',
            )
        registrar(
            None, f'{definicion["prefijo"]}-DOC-CORRIDAS-RESUMEN', 'documento',
            'Corridas y lotes',
            'Agregado público de corridas cerradas este mes y lotes vigentes.',
            estado='publicada', visibilidad='publica',
        )
        registrar(
            None, f'{definicion["prefijo"]}-DOC-CORRIDAS-DETALLE', 'documento',
            'Detalle operativo de corridas y lotes',
            'Órdenes, cantidades, ubicaciones, controles y movimientos de cada lote.',
            estado='publicada', visibilidad='interna',
        )

    def _seguridad(self, unidad, definicion, consumibles):
        """Lo que la unidad exige para entrar; solo quien lo declara lo carga."""
        for orden, datos in enumerate(definicion.get('acceso', []), start=1):
            codigo_consumible = datos.get('consumible')
            RequisitoAcceso.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'nombre': datos['nombre'],
                    'tipo': datos['tipo'],
                    'aplica_a': datos.get('aplica_a', []),
                    'obligatorio': datos.get('obligatorio', True),
                    'momento': datos.get('momento', 'reservar'),
                    'vigencia_dias': datos.get('vigencia_dias'),
                    'consumible': consumibles[codigo_consumible] if codigo_consumible else None,
                    'cantidad_por_persona': Decimal(str(datos.get('cantidad_por_persona', '1'))),
                    'descripcion': datos.get('descripcion', ''),
                    'orden': orden,
                    'activo': True,
                },
            )

    def _asignaturas(self, unidad, definicion):
        """El sílabo práctico que la unidad programa; solo quien lo declara lo carga."""
        for datos in definicion.get('asignaturas', []):
            asignatura, _ = Asignatura.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'nombre': datos['nombre'],
                    'carrera': datos.get('carrera', ''),
                    'semestre': datos.get('semestre', ''),
                    'estudiantes': datos.get('estudiantes', 0),
                    'descripcion': datos.get('descripcion', ''),
                    'activa': True,
                },
            )
            for tema_datos in datos.get('temas', []):
                receta = (
                    Receta.objects.filter(unidad=unidad, codigo=tema_datos['receta']).first()
                    if tema_datos.get('receta')
                    else None
                )
                tema, _ = TemaAsignatura.objects.update_or_create(
                    asignatura=asignatura,
                    orden=tema_datos['orden'],
                    defaults={
                        'nombre': tema_datos['nombre'],
                        'receta': receta,
                        'ejercicios': tema_datos.get('ejercicios', ''),
                        'resultado_aprendizaje': tema_datos.get('resultado', ''),
                    },
                )
                tema.software.set(
                    SoftwareDisponible.objects.filter(unidad=unidad, codigo__in=tema_datos.get('software', []))
                )

    def _responsables(self, unidad, definicion):
        for datos in definicion['responsables']:
            ResponsableUnidad.objects.update_or_create(
                unidad=unidad,
                email=datos['email'],
                defaults={
                    'nombre': datos['nombre'],
                    'rol': datos['rol'],
                    'telefono': datos['telefono'],
                    'descripcion': datos['descripcion'],
                    'horario_atencion': datos['horario_atencion'],
                    'publico': True,
                    'recibe_reservas': False,
                    'permisos_operativos': {},
                    'activo': True,
                    'orden': datos['orden'],
                },
            )

    def _vincular_responsables_servicios(self, unidad):
        """Los servicios nuevos reciben el contacto público principal de la unidad."""
        principal = (
            ResponsableUnidad.objects.filter(unidad=unidad, activo=True, publico=True)
            .order_by('orden', 'id')
            .first()
        )
        if principal:
            FablabService.objects.filter(
                unidad=unidad,
                responsable__isnull=True,
            ).update(responsable=principal)

    def _actividades(self, unidad, definicion):
        periodo = (
            PeriodoAcademico.objects.filter(estado='publicado')
            .order_by('-anio_referencia', '-ciclo')
            .first()
        )
        for orden, datos in enumerate(definicion['actividades'], start=1):
            CatalogoActividadReserva.objects.update_or_create(
                unidad=unidad,
                codigo=datos['codigo'],
                defaults={
                    'proposito_codigo': datos['proposito_codigo'],
                    'subtipo_actividad': datos['subtipo_actividad'],
                    'nombre': datos['nombre'],
                    'periodo': periodo,
                    'periodo_academico': periodo.codigo if periodo else '',
                    'responsable': datos['responsable'],
                    'activo': True,
                    'orden': orden,
                },
            )

    def _ejemplos(self, unidad, definicion):
        """Lo que esta unidad quiere que se escriba al pedirle algo."""
        for datos in definicion['ejemplos']:
            EjemploSolicitudUnidad.objects.update_or_create(
                unidad=unidad,
                proposito_codigo=datos['proposito'],
                defaults={
                    'ejemplo': datos['ejemplo'],
                    'checklist': datos.get('checklist', []),
                    'activo': True,
                },
            )

    def _cuentas(self, unidad, definicion, password):
        """Cuentas con las que el laboratorio atiende desde su panel."""
        Usuario = get_user_model()
        for datos in definicion['cuentas']:
            usuario, _ = Usuario.objects.update_or_create(
                username=datos['username'],
                defaults={
                    'first_name': datos['nombres'],
                    'last_name': datos['apellidos'],
                    'email': datos['email'],
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                },
            )
            usuario.set_password(password)
            usuario.save(update_fields=['password'])
            UserProfile.objects.update_or_create(
                user=usuario,
                defaults={
                    'tipo_usuario': 'administrativo',
                    'facultad': 'administracion_central',
                    'carrera': 'administrativo',
                    'nivel_academico': 'administrativo',
                    'institucion': 'Universidad Politécnica Estatal del Carchi',
                    'cargo': datos['cargo'],
                },
            )
            permisos = {modulo: False for modulo in MODULOS_OPERATIVOS}
            permisos.update(datos['modulos'])
            responsable = (
                ResponsableUnidad.objects.filter(unidad=unidad, usuario=usuario)
                .order_by('pk')
                .first()
            ) or ResponsableUnidad(unidad=unidad, usuario=usuario)
            responsable.nombre = f'{datos["nombres"]} {datos["apellidos"]}'
            responsable.rol = datos['rol']
            responsable.email = datos['email']
            responsable.descripcion = datos['cargo']
            responsable.horario_atencion = 'Cuenta operativa del laboratorio'
            responsable.publico = False
            responsable.recibe_reservas = True
            responsable.permisos_operativos = permisos
            responsable.activo = True
            responsable.orden = 900
            responsable.full_clean()
            responsable.save()
