"""Organización y operación del CIDT; contenido editable, sin acreditar activos o volúmenes.

Amplía el catálogo base y expone sus valores anteriores para actualizar sólo
precargas reconocidas. Los textos del gestor, estados y evidencias se conservan.
"""


def filas(*valores):
    return '\n'.join(' | '.join(fila) for fila in valores)


OPERACIONES = {
    'ia-datos': (
        ('Ingeniería de datos e interoperabilidad', 'Captura autorizada, catálogo de variables, APIs y conexión entre sistemas de planta, almacén y unidades vinculadas.', 'Diccionario, versiones, pruebas de intercambio y calidad del dato.'),
        ('Analítica e IA aplicada', 'Formular hipótesis, construir una referencia, entrenar y contrastar modelos de demanda, visión o mantenimiento.', 'Datos separados de entrenamiento y prueba, error, sesgos, costo y límites.'),
        ('Software industrial', 'Construir aplicaciones y conectores con pruebas, despliegue controlado y seguimiento.', 'Código, pruebas, manuales, permisos y registro de cambios.'),
    ),
    'automatizacion': (
        ('Electrónica y sistemas embebidos', 'Diseñar circuitos, PCB, firmware y bancos de prueba para equipos y prototipos.', 'Esquemas, lista de componentes, mediciones y pruebas funcionales.'),
        ('Control y comunicaciones industriales', 'Integrar PLC, HMI, sensores, actuadores y redes de equipos habilitados.', 'Entradas/salidas, secuencia, alarmas, paros y prueba de aceptación.'),
        ('Robótica y movilidad', 'Desarrollar integración de brazos, cobots o vehículos móviles según recursos y zona autorizada.', 'Trayectorias, seguridad, repetibilidad y registro de fallos.'),
    ),
    'xr-mediatech': (
        ('Modelado y simulación', 'Comparar configuraciones de celdas, almacenamiento, rutas y comportamiento de equipos.', 'Modelo, supuestos, datos, versión y contraste con mediciones.'),
        ('XR e interacción', 'Entrenamiento inmersivo, revisión de diseño y experimentación con usuarios.', 'Guion, tareas, evaluación de aprendizaje/usabilidad y alternativa accesible.'),
        ('MediaTech y comunicación científica', 'Documentar experimentos, elaborar manuales, recursos y demostraciones de transferencia.', 'Archivos fuente, derechos de uso, subtítulos y revisión técnica.'),
    ),
    'fablab': (
        ('Ingeniería de producto', 'Transformar requisitos en diseño CAD, selección de materiales y plan de validación.', 'Planos, tolerancias requeridas, versión y revisión de fabricabilidad.'),
        ('Fabricación y postproceso', 'Fabricar y ajustar piezas, carcasas, herramental y componentes con equipos habilitados.', 'Parámetros, material/lote, inspección y consumo documentados.'),
        ('Integración y entrega a Smart Factory', 'Validar el prototipo y preparar su repetición o integración en una celda productiva.', 'Diseño liberado, lista de materiales, instrucciones y pruebas de aceptación.'),
    ),
    'energia': (
        ('Instrumentación y línea base', 'Medir energía y condiciones ambientales del equipo, proceso o espacio autorizado.', 'Ubicación, unidad, frecuencia, calibración pertinente y cobertura del dato.'),
        ('Eficiencia y cadena de frío', 'Contrastar alternativas de operación y conservación para Factory, CEDI y unidades vinculadas.', 'Consumo por unidad, excursiones térmicas, causas y acciones.'),
        ('Edificio vivo y mantenimiento', 'Relacionar sensores, ocupación, ambiente y desempeño para investigación y mejora.', 'Series temporales, hipótesis, comparación y límites del resultado.'),
    ),
    'smart-factory': (
        ('Ingeniería e industrialización', 'Recibir diseños de FabLab y las otras áreas; definir producto, ruta, materiales, capacidad y pruebas.', 'Diseño y lista de materiales liberados, orden y plan de control.'),
        ('Recepción y supermercado de materiales', 'Recibir insumos del CEDI, verificar lote/estado y preparar kits para cada orden.', 'Consumo autorizado, ubicación, trazabilidad y segregación de no conformes.'),
        ('Celdas de manufactura reconfigurables', 'Fabricar componentes, integrar automatización y probar configuraciones de proceso y herramental.', 'Instrucción vigente, seguridad, tiempos y registro de parámetros.'),
        ('Líneas de producción y ensamble', 'Ejecutar órdenes por lote o serie, balancear estaciones, abastecer y controlar trabajo en proceso.', 'Cantidades planificadas/reales, ciclo, paros, defectos y genealogía del producto.'),
        ('Calidad y validación de equipos', 'Inspeccionar producto y ensayar prototipos o equipamiento desarrollado por las áreas tecnológicas.', 'Criterios de aceptación, mediciones, liberación o reproceso autorizado.'),
        ('Acondicionamiento y transferencia al CEDI', 'Identificar unidades y lotes aprobados y preparar entrega interna para almacenamiento o distribución.', 'Registro de liberación, cantidad, destino y confirmación de recepción.'),
    ),
    'smart-cedi': (
        ('Planificación y citas de recibo', 'Programar ingresos desde proveedores, Smart Factory, plantas piloto y centros experimentales.', 'Orden, origen, lote, cantidad, requisitos de conservación y ventana de atención.'),
        ('Muelle, recepción y verificación', 'Descargar con medios autorizados, contrastar documentos y capturar identidad, peso y cantidad.', 'Diferencias, evidencia de recibo, condición y trazabilidad del origen.'),
        ('Cuarentena y control de entrada', 'Separar productos pendientes, rechazados, devueltos o que requieren evaluación.', 'Estado bloqueado; liberar únicamente por el responsable competente.'),
        ('Almacenamiento automatizado', 'Asignar ubicación y ejecutar movimientos con sensores, lectores y equipos habilitados.', 'Confirmación física-digital, ocupación, restricciones de carga y seguridad.'),
        ('Cadena de frío y condiciones especiales', 'Conservar productos compatibles según condiciones acordadas con su unidad responsable.', 'Temperatura/humedad, tiempo, alertas y manejo de desviaciones.'),
        ('Reabastecimiento a Smart Factory', 'Preparar kits, componentes y reposición de línea para órdenes autorizadas.', 'Lote, cantidad, consumo, entrega y devolución de remanentes.'),
        ('Picking y consolidación', 'Asignar tareas, verificar ubicación y preparar pedidos internos o externos.', 'Exactitud, productividad, faltantes y trazabilidad de cada pedido.'),
        ('Packing, cubicaje y comercio exterior', 'Empacar, medir, rotular y preparar expediente documental en el módulo integrado.', 'Material de empaque, dimensiones, control documental y destino.'),
        ('Staging, despacho y transporte', 'Consolidar carga, verificar autorización y coordinar ruta y entrega.', 'Registro de despacho, responsable, tiempos y confirmación de entrega.'),
        ('Inventario, devoluciones y logística inversa', 'Conteos, conciliación, recuperación y clasificación de devoluciones.', 'Historial de movimientos; no ajustar ni reincorporar producto sin autorización.'),
    ),
    'comercio-exterior': (
        ('Cubicaje y protección de carga', 'Comparar embalajes, dimensiones, peso y consolidación dentro del Smart CEDI.', 'Ficha dimensional, materiales, protección y límites de la prueba.'),
        ('Expediente y costos de operación', 'Preparar documentación de casos, responsabilidades, alternativas de ruta y costos con fuentes vigentes.', 'Packing list, documentos de soporte, supuestos y revisión de consistencia.'),
        ('Preparación para despacho', 'Entregar carga y expediente al responsable logístico; coordinar operadores externos cuando corresponda.', 'Autorizaciones y revisión competente; los ejercicios académicos se identifican como tales.'),
    ),
    'sala-control': (
        ('Integración y observabilidad', 'Recibir telemetría autorizada de Factory, CEDI, energía, equipos y servicios.', 'Fuente, unidad, fecha, calidad y estado de conexión; distinguir medición y simulación.'),
        ('Coordinación de eventos', 'Priorizar alertas y comunicar incidencias a los operadores responsables.', 'Asignación, respuesta y cierre; la seguridad local del equipo conserva su autoridad.'),
        ('Análisis y evidencia', 'Comparar órdenes y experimentos, documentar cuellos de botella y preparar informes.', 'Indicador con período, método, versión y acceso según rol.'),
    ),
}

MATERIALES = {
    'ia-datos': (('Datos y modelos', 'Fuentes autorizadas, diccionario, licencia, separación de ambientes y versiones; los datos personales o industriales tienen acceso controlado.'),),
    'automatizacion': (('Componentes y consumibles', 'Sensores, actuadores, placas, conectores, cables, soldadura, protecciones y repuestos compatibles; lista y consumo por prototipo.'),),
    'xr-mediatech': (('Activos digitales y captura', 'Modelos, texturas, audio, imágenes y datos con derechos de uso; accesorios higienizables y zona segura para visores.'),),
    'fablab': (('Materiales de fabricación', 'Polímeros, resinas, tableros, metales y componentes únicamente compatibles con la máquina y proceso habilitados; registrar lote, ficha y disposición.'),
               ('Herramental y acabado', 'Fresas, boquillas, abrasivos, adhesivos y fijaciones; selección técnica, seguridad y consumo por orden.')),
    'energia': (('Instrumentación y repuestos', 'Sensores, medidores, registradores, cableado, conectores y elementos de fijación compatibles; identificación y verificación de mediciones.'),),
    'smart-factory': (('Lista de materiales de producto', 'Componentes, materias primas, piezas de FabLab, electrónica y embalajes asociados a diseño, lote y orden aprobados.'),
                      ('Consumibles y repuestos', 'Herramental, lubricantes, fijaciones, protección y piezas de mantenimiento según equipos y procesos habilitados.'),
                      ('Productos de otras unidades', 'Recibir sólo transformaciones compatibles con la instalación y el plan aprobado; el proceso especializado conserva su unidad responsable.')),
    'smart-cedi': (('Carga admitida', 'Productos, componentes y muestras con origen, identidad, estado y condiciones conocidos. Compatibilidad de almacenamiento y separación por riesgo antes de aceptar.'),
                   ('Embalaje y unidades de carga', 'Cajas, pallets, contenedores, etiquetas, protección y sellos compatibles con producto, rack, equipo y destino.'),
                   ('Operación y conservación', 'Consumibles de lectura/impresión, limpieza y conservación; registrar reposición y uso, sin mezclar cargas incompatibles.')),
    'comercio-exterior': (('Embalajes y documentación', 'Muestras de empaque, etiquetas, fichas dimensionales y documentos autorizados; parámetros y fuentes de cada caso con fecha de consulta.'),),
    'sala-control': (('Datos, red y continuidad', 'Catálogo de fuentes, almacenamiento, conectividad, energía y repuestos; permisos, retención y plan de atención de fallos.'),),
}

# Carrera, trabajo concreto y evidencia. Participación propuesta, no convenio o matrícula aprobados.
ACADEMIA = {
    'ia-datos': (
        ('Computación', 'Construir conectores, analítica e IA con pruebas sobre datos autorizados.', 'Código versionado, comparación con referencia y evaluación.'),
        ('Contabilidad y Auditoría', 'Definir costos, conciliación y trazabilidad de movimientos junto con operadores.', 'Modelo de costos y pruebas de integridad.'),
        ('Administración Pública', 'Diseñar indicadores y servicios digitales con evaluación de usuarios.', 'Diccionario de indicadores y estudio de implementación.'),
    ),
    'automatizacion': (
        ('Computación', 'Programar firmware, control e integración IoT en bancos supervisados.', 'Esquemas, código, pruebas y registro de fallos.'),
        ('Logística y Transporte', 'Evaluar identificación y automatización del movimiento de materiales.', 'Comparación de tiempos, errores y condiciones seguras.'),
        ('Agropecuaria', 'Instrumentar procesos de campo con la unidad experimental competente.', 'Protocolo, datos de medición y validación de lectura.'),
    ),
    'xr-mediatech': (
        ('Multimedia y Producción Audiovisual', 'Diseñar interacción, simuladores, documentación y comunicación científica.', 'Guion, activos, pruebas de usuario y recurso accesible.'),
        ('Turismo', 'Evaluar recorridos y experiencias inmersivas con actores del territorio.', 'Experiencia, evaluación y derechos de contenidos.'),
        ('Educación Básica', 'Diseñar y evaluar secuencias de aprendizaje con simulación.', 'Guía, rúbrica y resultados de aprendizaje.'),
        ('Educación Inicial', 'Evaluar recursos adecuados a la edad con responsables educativos y permisos.', 'Recurso accesible y evaluación pedagógica.'),
        ('Enfermería', 'Colaborar en entrenamiento y evaluación de interfaces, sin sustituir la simulación clínica especializada.', 'Escenario y evaluación revisados por la unidad competente.'),
        ('Ciencias de la Actividad Física y Deporte', 'Evaluar interacción, ergonomía y uso de tecnologías inmersivas.', 'Protocolo de usuario e informe de accesibilidad/usabilidad.'),
    ),
    'fablab': (
        ('Computación', 'Integrar dispositivos y carcasas con electrónica y software.', 'Diseño CAD, prototipo y prueba funcional.'),
        ('Multimedia y Producción Audiovisual', 'Desarrollar modelos, interfaces físicas y comunicación del producto.', 'Modelo, documentación y evaluación con usuarios.'),
        ('Medicina Veterinaria', 'Codesarrollar dispositivos o soportes de investigación con la unidad veterinaria.', 'Requisitos, prototipo y validación dentro del alcance autorizado.'),
        ('Laboratorio Clínico', 'Codesarrollar soportes, trazabilidad o interfaces para investigación con el laboratorio competente.', 'Expediente técnico; no acredita dispositivo clínico ni resultado diagnóstico.'),
    ),
    'energia': (
        ('Computación', 'Implementar captura, alertas y análisis de eficiencia.', 'Series temporales y modelo contrastado.'),
        ('Alimentos', 'Evaluar conservación y condiciones del producto con su planta/laboratorio.', 'Datos térmicos y análisis del ensayo.'),
        ('Agropecuaria', 'Evaluar recursos y condiciones ambientales de sistemas productivos.', 'Línea base y comparación de alternativas.'),
    ),
    'smart-factory': (
        ('Administración de Empresas', 'Planificar órdenes, capacidad, balanceo y calidad en celdas y líneas.', 'Plan productivo, indicadores y propuesta de mejora.'),
        ('Computación', 'Integrar MES, automatización, visión y trazabilidad del producto.', 'Integración probada y registro de eventos.'),
        ('Contabilidad y Auditoría', 'Analizar material, trabajo, merma y costos de lote.', 'Costo unitario con supuestos y conciliación.'),
        ('Alimentos', 'Desarrollar empaque y acondicionamiento compatibles; la transformación alimentaria permanece en la planta habilitada.', 'Especificación de empaque y pruebas del lote.'),
        ('Logística y Transporte', 'Abastecer líneas, definir kits y evaluar flujo hacia el CEDI.', 'Plan de materiales, tiempos y trazabilidad de entrega.'),
    ),
    'smart-cedi': (
        ('Logística y Transporte', 'Operar recepción, ubicación, inventario, picking, despacho y rutas bajo supervisión.', 'Registro WMS, exactitud, tiempos y comparación de políticas.'),
        ('Comercio Exterior', 'Preparar cubicaje, embalaje, expediente y alternativas de distribución.', 'Expediente consistente y costos con fuentes fechadas.'),
        ('Administración de Empresas', 'Planificar demanda, capacidad, servicio y relación con clientes/proveedores.', 'Plan de operación y evaluación de nivel de servicio.'),
        ('Contabilidad y Auditoría', 'Conciliar movimientos, costo de almacenamiento y diferencias de inventario.', 'Conciliación y costo por pedido con evidencia.'),
        ('Computación', 'Integrar WMS, lectura, automatización, analítica y seguimiento.', 'Conector, eventos y validación del dato.'),
        ('Alimentos', 'Verificar condiciones y trazabilidad de lotes de plantas piloto.', 'Registro de conservación y seguimiento de desviaciones.'),
        ('Agropecuaria', 'Relacionar origen de finca, acondicionamiento y distribución de producto.', 'Lote de origen, condiciones y registro de entrega.'),
        ('Medicina Veterinaria', 'Estudiar trazabilidad y condiciones de productos/muestras con su unidad competente.', 'Protocolo de manejo autorizado y evidencia de cadena de custodia.'),
    ),
    'comercio-exterior': (
        ('Comercio Exterior', 'Comparar responsabilidades, documentos, embalaje y escenarios de operación.', 'Expediente técnico con fuentes y límites.'),
        ('Logística y Transporte', 'Diseñar consolidación, distribución y verificación de carga.', 'Plan de carga, ruta y registro dimensional.'),
    ),
    'sala-control': (
        ('Computación', 'Diseñar observabilidad, integración y análisis de eventos.', 'Tablero, diccionario y pruebas de alertas.'),
        ('Administración de Empresas', 'Evaluar desempeño y decisiones con datos de operación.', 'Informe con período, método y decisiones documentadas.'),
        ('Administración Pública', 'Evaluar indicadores de servicios y colaboración territorial.', 'Indicadores y análisis de cobertura.'),
    ),
}

FACTORY = (
    ('Planificar orden y capacidad', 'Definir lote o serie, ruta, recursos, materiales, calendario y responsable; comprobar capacidad y aceptación.'),
    ('Liberar diseño y proceso', 'Recibir de FabLab y áreas tecnológicas planos, BOM, firmware, instrucciones y prueba del prototipo.'),
    ('Abastecer y preparar', 'El CEDI entrega materiales y kits identificados; preparar herramental, estaciones y condiciones seguras.'),
    ('Fabricar e integrar', 'Ejecutar celdas de manufactura y ensamblar equipos o productos según la orden y versión liberada.'),
    ('Controlar la serie', 'Medir tiempos, cantidades, defectos y paros; ajustar sólo con autorización y conservar datos del experimento.'),
    ('Validar y liberar', 'Separar producto aprobado, no conforme y reproceso; aplicar criterios y documentar aceptación.'),
    ('Identificar y entregar al CEDI', 'Codificar producto/lote y transferir cantidad, estado, documentación y condiciones de conservación.'),
    ('Evaluar y escalar', 'Contrastar desempeño, costo y repetibilidad; autorizar ampliación de serie según capacidad demostrada.'),
)
CEDI = (
    ('Planificar ingreso', 'Confirmar origen, orden, lote, cantidad y condiciones de entrada desde Factory, proveedores, plantas o fincas.'),
    ('Recibir y verificar', 'Capturar identidad y contrastar cantidad, condición y documentación de la carga.'),
    ('Clasificar y liberar', 'Mantener cuarentena o rechazo cuando corresponda; registrar autorización de entrada.'),
    ('Ubicar y almacenar', 'Asignar ubicación y confirmar movimientos con los equipos de manejo y automatización habilitados.'),
    ('Conservar y monitorear', 'Controlar compatibilidad, condiciones ambientales y alertas; documentar desviaciones.'),
    ('Abastecer producción', 'Preparar kits y reposición a Factory; confirmar entrega, consumos y remanentes.'),
    ('Preparar pedidos', 'Liberar olas o tareas de picking, verificar lote/ubicación y consolidar cantidades.'),
    ('Empacar y documentar', 'Aplicar packing, cubicaje, etiquetado y módulo de comercio exterior según destino.'),
    ('Despachar y entregar', 'Verificar carga, autorización, ruta, transportista y confirmación de entrega.'),
    ('Conciliar y gestionar retornos', 'Revisar inventario, diferencias, devoluciones y disposición; comparar desempeño y mejorar.'),
)

SERVICIOS_TRANSVERSALES = {
    'Cursos y talleres': (
        'Formación a medida vinculada a capacidades del centro y necesidades del participante o institución.',
        'Diagnosticar competencias, acordar programa y prácticas, confirmar recursos/instructor y evaluar aprendizaje.',
        'Programa, materiales, práctica y rúbrica; certificación únicamente bajo condiciones institucionales aprobadas.'),
    'Demostraciones tecnológicas': (
        'Visitas y demostraciones de tecnologías o procesos con objetivo técnico o formativo definido.',
        'Seleccionar recorrido o demostrador, evaluar riesgos, programar responsables, realizar inducción y registrar observaciones.',
        'Guion, registro de participación y conclusiones; no acredita competencia profesional ni validación industrial.'),
    'Transferencia de soluciones': (
        'Preparar la entrega y adopción de un resultado tecnológico por un receptor identificado.',
        'Revisar madurez, evidencia, titularidad y restricciones; acordar mecanismo, documentación, capacitación y seguimiento.',
        'Expediente técnico, acta de entrega y plan de adopción; los instrumentos se revisan por la autoridad competente.'),
    'Evaluación de madurez tecnológica': (
        'Valorar la madurez de un desarrollo tecnológico dentro de un alcance y fecha de corte.',
        'Definir escala aplicable, revisar pruebas por nivel, contrastar evidencias y documentar brechas sin convertir expectativas en logros.',
        'Informe de madurez con evidencia, evaluador, límites y hoja de validación; TRL sólo cuando corresponda.'),
    'Apoyo a registros de software': (
        'Organizar documentación técnica y de autoría de software para revisión por la instancia institucional competente.',
        'Identificar versión, autores, dependencias, licencias, documentación y evidencia de desarrollo; revisar restricciones de divulgación.',
        'Expediente técnico y lista de pendientes; el apoyo no equivale a registro concedido ni dictamen jurídico.'),
    'Apoyo a modelos de utilidad o patentes': (
        'Documentar un desarrollo y coordinar la evaluación de alternativas de protección con especialistas competentes.',
        'Delimitar aporte, autores/titulares, antecedentes, pruebas y divulgaciones; preparar dossier y derivación para evaluación especializada.',
        'Dossier, evidencia y revisión de antecedentes; no garantiza patentabilidad, concesión ni representación legal.'),
    'Formulación de proyectos externos': (
        'Estructurar propuestas con empresas, instituciones, cooperación o comunidad, articuladas con la agenda del centro.',
        'Definir problema, novedad, método, socios, presupuesto, riesgos, hitos e indicadores; coordinar revisión y convocatoria aplicable.',
        'Propuesta versionada y matriz de evaluación; financiación y aprobación se tramitan por las instancias correspondientes.'),
    'Acompañamiento a innovación': (
        'Acompañar decisiones de desarrollo, validación y adopción de una solución con usuario o beneficiario definido.',
        'Diagnosticar necesidad, priorizar hipótesis, planificar pruebas, revisar evidencia con usuarios y acordar próximos hitos.',
        'Plan, sesiones, decisiones y evidencias; no garantiza éxito comercial o adopción.'),
    'Evaluación de impacto': (
        'Diseñar y analizar cambios asociados a proyectos, servicios o soluciones con población y período delimitados.',
        'Definir teoría de cambio, línea base, indicadores, fuentes y comparación viable; analizar sesgos, atribución y límites.',
        'Informe reproducible, fuentes y recomendaciones; distinguir resultados, adopción e impacto causal demostrado.'),
}


def aplicar(catalogo):
    """Devuelve antes/después para una actualización conservadora y reproducible."""
    revision = {'componentes': {}, 'centro': {}, 'gobierno': [], 'articulacion': [], 'ruta': [], 'modalidades': []}
    for area in catalogo['COMPONENTES']:
        codigo = area['codigo']
        cambios = {'organizacion_operativa': filas(*OPERACIONES[codigo]),
                   'insumos_materiales': filas(*MATERIALES[codigo]),
                   'usos_academicos': filas(*ACADEMIA[codigo])}
        if area['tipo'] == 'division':
            cambios['nombre'] = area['nombre'].replace('División de ', 'Área de ')
        if codigo == 'smart-factory':
            cambios.update(
                descripcion='Plataforma de manufactura real para desarrollar equipamiento, fabricar componentes, integrar prototipos y operar celdas y líneas reconfigurables. Recibe diseños de FabLab, automatización, electrónica, software y otras áreas; transforma un prototipo validado en un proceso repetible con órdenes, materiales, control de calidad y trazabilidad.\nOpera investigación experimental, producción piloto y producción por lotes o series para servicios internos y externos. El escalamiento hacia producción de alto volumen requiere demostrar capacidad, abastecimiento, seguridad, calidad, mantenimiento y viabilidad económica; el catálogo no fija una cantidad instalada.\nEl Smart CEDI abastece las líneas y recibe producto liberado. Las plantas piloto mantienen los procesos especializados que les corresponden; Factory aporta equipos, automatización, empaque o integración dentro de su alcance.',
                capacidades=filas(('Manufactura e industrialización', 'Desarrollo de celdas, líneas, herramental y equipos a partir de diseños liberados.'),
                                  ('Producción por lotes y series', 'Planificación de capacidad, balanceo, abastecimiento, ejecución y escalamiento documentado.'),
                                  ('Experimentación y servicios', 'Comparación de configuraciones, pruebas de proceso y fabricación por encargo con aceptación.'),
                                  ('Calidad y trazabilidad', 'Genealogía de materiales, parámetros, inspección, liberación y entrega al CEDI.')),
                flujo=filas(*FACTORY))
        elif codigo == 'smart-cedi':
            cambios.update(
                descripcion='Centro de distribución y almacén automatizado para operaciones físicas reales de recepción, almacenamiento, inventario, abastecimiento, preparación de pedidos y distribución. Integra personas, ubicaciones, equipos de manejo habilitados, identificación y WMS, con supervisión y trazabilidad.\nFunciona en doble sentido con Smart Factory: entrega materias primas, componentes y kits a las líneas; recibe productos y equipos liberados para almacenar o despachar. También recibe directamente lotes de plantas piloto, centros experimentales, proveedores y proyectos externos: no obliga a pasar todo producto por Factory.\nCombina investigación logística, operación de servicios y formación supervisada. El módulo de Comercio Exterior pertenece a esta plataforma. La capacidad de carga, automatización instalada, conservación y volumen de servicio se verifican antes de aceptar cada operación.',
                capacidades=filas(('Almacenamiento y automatización', 'Ubicaciones, identificación, movimiento y control con recursos reales habilitados.'),
                                  ('Abastecimiento y fulfillment', 'Kits para producción, preparación de pedidos, empaque, despacho y confirmación de entrega.'),
                                  ('Cadena de suministro integrada', 'Origen en unidades productoras, lotes, conservación, distribución y retornos.'),
                                  ('Investigación logística', 'Comparar políticas de inventario, slotting, picking, transporte y resiliencia con datos reproducibles.')),
                flujo=filas(*CEDI))
        elif codigo == 'comercio-exterior':
            cambios.update(integrado_en_codigo='smart-cedi',
                capacidades=filas(('Cubicaje y embalaje', 'Comparar protección, dimensiones, peso, consolidación y rotulado.'),
                                  ('Documentación y escenarios', 'Preparar expedientes, responsabilidades y alternativas con fuentes vigentes.'),
                                  ('Apoyo a distribución', 'Coordinar con despacho del CEDI y operadores competentes según el caso.')))
        elif codigo == 'sala-control':
            cambios['descripcion'] = ('Sistema transversal de observación, coordinación de eventos y análisis del CIDT. Su sala física permite seguir Smart Factory, Smart CEDI, energía y las áreas tecnológicas; no constituye una tercera plataforma de producción.\n'
                'IA y Datos sostiene la integración digital; Coordinación Operativa asigna y atiende incidencias; la Oficina de Innovación y Transferencia utiliza evidencia para proyectos, servicios y vinculación. El control de seguridad y la autorización de maniobras permanecen en cada equipo y operador. Una pantalla o réplica 3D no acredita conexión con equipamiento real.')
        revision['componentes'][codigo] = {'antes': {k: area.get(k, '') for k in cambios}, 'despues': cambios}
        area.update(cambios)
    nuevos = {
        'presentacion': ('El CIDT organiza investigación aplicada, desarrollo experimental, innovación y servicios especializados mediante cinco áreas de tecnologías aplicadas y dos plataformas operativas: Smart Factory y Smart CEDI. Comercio Exterior se integra al CEDI y la Sala de Control presta una función transversal.\n'
                        'La Oficina de Innovación y Transferencia de Tecnología coordina el portafolio, la formulación y evaluación de proyectos, los servicios y la vinculación con empresas, comunidad y universidad. Las prácticas, visitas y pasantías se planifican con objetivos, responsables, inducción y evidencias.\n'
                        'FabLab y las áreas tecnológicas desarrollan soluciones; Factory integra equipos, procesos y producción por lotes o series; CEDI conecta abastecimiento, almacenamiento y distribución con plantas piloto, centros experimentales y otros centros. Cada unidad conserva la responsabilidad de su proceso y sus recursos.'),
        'cadena': filas(
            ('Reto y acuerdo de trabajo', 'Oficina de Innovación y Transferencia de Tecnología', 'Propuesta evaluada, alcance, recursos, responsabilidades y condiciones.'),
            ('Diseño y desarrollo aplicado', 'Áreas de tecnologías aplicadas', 'Diseño, software, automatización, prototipo y protocolo versionados.'),
            ('Prototipado e ingeniería de producto', 'Prototipado y FabLab', 'Piezas, herramental y prototipo validados con diseño y materiales documentados.'),
            ('Industrialización y producción', 'Smart Factory', 'Celda o línea, orden, lote/serie y producto liberado con calidad y trazabilidad.'),
            ('Entrada de otras unidades', 'Plantas piloto, centros experimentales y centros I+D', 'Lote con origen, estado y condiciones; entrada directa al CEDI cuando corresponde.'),
            ('Abastecimiento y almacenamiento', 'Smart CEDI', 'Recepción, ubicación, conservación y materiales para producción.'),
            ('Preparación y comercio exterior', 'Smart CEDI y módulo integrado', 'Pedido, empaque, cubicaje y expediente según destino.'),
            ('Distribución y retorno', 'Smart CEDI', 'Despacho, entrega, conciliación y logística inversa.'),
            ('Datos y mejora', 'Sala de Control y áreas responsables', 'Eventos, indicadores, evaluación de escenarios y acciones documentadas.'),
            ('Transferencia y vinculación', 'Oficina de Innovación y Transferencia de Tecnología', 'Adopción, capacitación, prácticas/pasantías y seguimiento del resultado.')),
    }
    nuevos['objetivos_especificos'] = catalogo['CENTRO']['objetivos_especificos'].replace(
        'divisiones tecnológicas', 'áreas de tecnologías aplicadas')
    revision['centro'] = {'antes': {k: catalogo['CENTRO'].get(k, '') for k in nuevos}, 'despues': nuevos}
    catalogo['CENTRO'].update(nuevos)
    gobierno = list(catalogo['GOBIERNO'])
    for i, fila in enumerate(gobierno):
        if fila[0].startswith('Oficina de Innovación'):
            nueva = ('Oficina de Innovación y Transferencia de Tecnología', 'Coordinación de I+D, servicios y vinculación', fila[2],
                'Coordina el portafolio científico-tecnológico y la relación con universidad, empresas y comunidad. Estructura proyectos y servicios, articula áreas y unidades y acompaña transferencia y adopción; las decisiones científicas, de seguridad y económicas corresponden a las autoridades competentes.',
                filas(('Proyectos internos y externos', 'Recibir retos, formular propuestas, coordinar evaluación, financiación, hitos, riesgos y evidencia.'),
                      ('Servicios y producción', 'Acordar alcance, recursos, capacidad, costeo, calidad, entregas y aceptación con operadores.'),
                      ('Innovación y transferencia', 'Coordinar validación, documentación, propiedad intelectual y mecanismos de adopción.'),
                      ('Vinculación y formación', 'Programar prácticas, visitas técnicas, pasantías, estancias, capacitación y proyectos comunitarios con objetivos y responsables.'),
                      ('Red de capacidades', 'Articular plantas piloto, centros experimentales, laboratorios y otros centros sin duplicar su operación.'),
                      ('Seguimiento', 'Consolidar resultados, satisfacción, adopción y sostenibilidad con fuentes y período.')))
            revision['gobierno'].append({'antes': fila, 'despues': nueva})
            gobierno[i] = nueva
        elif fila[0] == 'Responsables de divisiones':
            nueva = ('Responsables de tecnologías aplicadas', *fila[1:])
            revision['gobierno'].append({'antes': fila, 'despues': nueva})
            gobierno[i] = nueva
    catalogo['GOBIERNO'] = tuple(gobierno)
    ruta = []
    for fila in catalogo['RUTA']:
        nuevo_responsable = fila[3]
        if nuevo_responsable.startswith('Oficina de Innovación'):
            nuevo_responsable = 'Oficina de Innovación y Transferencia de Tecnología'
        nuevo_responsable = nuevo_responsable.replace('Divisiones tecnológicas', 'Áreas de tecnologías aplicadas').replace(
            'Divisiones, plataformas', 'Áreas tecnológicas, plataformas')
        nueva = (*fila[:3], nuevo_responsable, fila[4])
        if nueva != fila:
            revision['ruta'].append({'antes': fila, 'despues': nueva})
        ruta.append(nueva)
    catalogo['RUTA'] = tuple(ruta)
    modalidades = list(catalogo['MODALIDADES'])
    for i, fila in enumerate(modalidades):
        if fila[0] == 'Maquila tecnológica controlada':
            nueva = ('Producción por lotes, series y escalamiento',
                     'Fabricación por lotes y series; escalar volumen tras demostrar capacidad, calidad, abastecimiento y sostenibilidad.',
                     fila[2], fila[3])
            revision['modalidades'].append({'antes': fila, 'despues': nueva})
            modalidades[i] = nueva
    catalogo['MODALIDADES'] = tuple(modalidades)
    equivalencias = {'Administración': 'Administración de Empresas', 'Contabilidad': 'Contabilidad y Auditoría', 'Educación': 'Educación Básica'}
    articulacion = list(catalogo['ARTICULACION'])
    for i, fila in enumerate(articulacion):
        if fila[0] == 'carrera' and fila[1] in equivalencias:
            nueva = (fila[0], equivalencias[fila[1]], fila[2], fila[3])
            revision['articulacion'].append({'antes': fila, 'despues': nueva})
            articulacion[i] = nueva
    existentes = {f[1] for f in articulacion if f[0] == 'carrera'}
    for carrera in dict.fromkeys(f[0] for filas_area in ACADEMIA.values() for f in filas_area):
        if carrera not in existentes:
            areas = ', '.join(c for c, usos in ACADEMIA.items() if any(f[0] == carrera for f in usos))
            articulacion.append(('carrera', carrera, 'Participación aplicada en ' + areas + '; actividades y evidencias detalladas en cada área.', ''))
    catalogo['ARTICULACION'] = tuple(articulacion)
    for codigo, pasos in (('smart-factory', FACTORY), ('smart-cedi', CEDI)):
        revision['componentes'][codigo]['proceso_anterior'] = catalogo['PROCESOS'][codigo]
        revision['componentes'][codigo]['pasos_anteriores'] = catalogo['FLUJOS'].get(codigo, '') or revision['componentes'][codigo]['antes']['flujo']
        # Conserva el identificador del proceso; amplía sus pasos sin crear otro proceso equivalente.
        catalogo['FLUJOS'][codigo] = filas(*pasos)
    nuevos_servicios = (
        ('Producción y escalamiento', 'smart-factory', 'Fabricación por lotes y series',
         'Preparación y ejecución de producción repetible con materiales, capacidad y control acordados.',
         'Lote o serie, registro de materiales, inspección y entrega aceptada.'),
        ('Producción y escalamiento', 'smart-factory', 'Integración de equipamiento y líneas',
         'Integración de prototipos, automatización, estaciones y herramental para un proceso productivo.',
         'Configuración, expediente técnico y prueba de aceptación.'),
        ('Operación logística integrada', 'smart-cedi', 'Almacenamiento y preparación de pedidos',
         'Recepción, conservación, ubicación, picking, packing y entrega de cargas compatibles.',
         'Movimientos trazables, pedidos verificados e informe de operación.'),
        ('Operación logística integrada', 'smart-cedi', 'Abastecimiento y trazabilidad entre unidades',
         'Coordinación de lotes, materiales y entregas entre Factory, plantas, fincas y usuarios autorizados.',
         'Plan de abastecimiento, registros de origen, movimientos y confirmación de entrega.'),
    )
    catalogo['SERVICIOS'] = tuple(catalogo['SERVICIOS']) + nuevos_servicios
    detalles = catalogo.setdefault('DETALLES_SERVICIOS', {})
    for _, _, nombre, descripcion, entregable in nuevos_servicios:
        detalles[nombre] = {
            'alcance': descripcion,
            'entradas': 'Producto/material, especificación, cantidad, origen/destino, calendario y condiciones de manejo.',
            'requisitos': 'Evaluación de compatibilidad, recursos habilitados, responsable, capacidad y acuerdo de trabajo.',
            'metodo': 'Evaluar, planificar orden y recursos, ejecutar con registros, verificar calidad y entregar con aceptación.',
            'exclusiones': 'No incluye disponibilidad automática, volumen industrial no demostrado ni procesos fuera del alcance de la unidad operadora.',
            'formato_entrega': entregable,
            'plazo': 'Se fija al aprobar el plan, según lote, recursos, abastecimiento y verificaciones requeridas.',
            'aceptacion': 'Cantidades, condiciones y pruebas acordadas, trazabilidad completa y conformidad del solicitante.',
            'condiciones': 'Definir costos, titularidad, confidencialidad, conservación, responsabilidades y tratamiento de no conformes.',
            'estado_oferta': 'consultar',
        }
    for nombre, (alcance, metodo, formato) in SERVICIOS_TRANSVERSALES.items():
        detalles[nombre] = {
            'alcance': alcance, 'metodo': metodo, 'formato_entrega': formato,
            'entradas': 'Necesidad, antecedentes, objetivo, usuarios previstos y documentación disponible del caso.',
            'requisitos': 'Responsable designado, acceso autorizado a datos/recursos y acuerdo de alcance y seguimiento.',
            'exclusiones': 'No incluye autorizaciones, certificaciones, financiación, registro o capacidad de ejecución automáticos.',
            'plazo': 'Se acuerda según alcance, revisiones, disponibilidad y hitos del expediente.',
            'aceptacion': 'Entregables revisados contra el alcance y criterios acordados, con evidencias y conformidad registrada.',
            'condiciones': 'Acordar costos cuando correspondan, confidencialidad, titularidad, permisos de divulgación y responsabilidades.',
        }
    revision['servicios_transversales'] = tuple(SERVICIOS_TRANSVERSALES)
    revision['servicios_nuevos'] = nuevos_servicios
    return revision
