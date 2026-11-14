"""Catálogo editorial de Logística; se importa sólo al preparar contenidos.

No consulta la base, no abre archivos, no descarga contenidos y no ejecuta IA.
Los adjuntos públicos se sirven individualmente por el visor ya existente.
"""
import re
from pathlib import PurePosixPath

from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import documento_html


GUIAS_ORIENTACION = {
    'ruta-de-aprendizaje': {
        'titulo': 'Cómo trabajar en el laboratorio: preparar, experimentar y demostrar',
        'seccion': '1.1', 'carpeta': 'Inicio y rutas de aprendizaje', 'fuentes': ('upec', 'scor'),
        'objetivo': 'Elegir una ruta por asignatura o problema, ejecutar un caso reproducible y presentar evidencia útil para docencia, investigación formativa o diagnóstico empresarial.',
        'bloques': [
            ('Tres formas de comenzar', [
                'Estudiante: identificar asignatura en 4.2; elegir una de las doce prácticas en 4.1; leer fundamentos y diccionario; resolver el caso; contrastar controles sólo después; entregar evidencias y reflexión.',
                'Docente: definir resultado observable y rúbrica; adaptar duración y restricciones al sílabo; realizar primero el ensayo virtual; revisar la planificación antes de solicitar recursos físicos; evaluar evidencia y no sólo puntaje.',
                'Investigador o empresa: formular pregunta y decisión esperada; definir quién autoriza los datos; sustituir identificadores sensibles; comparar escenario base y alternativa; comunicar incertidumbre y alcance antes de proponer intervención.',
            ]),
            ('Ruta por pestañas', [
                'Información general: identidad, responsables, normas, recorrido y repositorio. Áreas y equipos: capacidad metodológica, fichas, software y materiales; el inventario determina qué se puede utilizar físicamente.',
                'Procesos y productos: secuencia operativa, método experimental y entregable verificable. Docencia y capacitación: asignaturas, prácticas, programas, datos y simuladores propios.',
                'Reservas y servicios: preparación, agenda, requisitos y expediente. Investigación formativa: preguntas replicables, articulación con Centros I+D, validación y devolución de resultados.',
            ]),
            ('Ciclo de una actividad', [
                'Preparar: descargar guía y CSV, fijar versión y objetivo, comprobar unidades, registrar semilla si se usa simulador y definir escenario base. Ejecutar: guardar decisiones y resultados sin sustituir el histórico de otra sesión.',
                'Analizar: conciliar balances y restricciones; comparar una alternativa cambiando una variable a la vez; revisar rendimiento, servicio, costo y seguridad en conjunto. Explicar la diferencia entre ejemplo analítico y motor virtual.',
                'Demostrar: entregar datos originales, hoja de cálculo o procedimiento reproducible, métricas con denominador, gráficos rotulados y conclusión con límites. La ejecución física requiere aprobación y evidencia de sus propios registros.',
            ]),
            ('Criterios de cierre', [
                'Otra persona puede repetir el caso con los mismos datos, versión y decisiones; el balance cierra; no se omiten incumplimientos; las fuentes están atribuidas y los supuestos diferenciados de mediciones.',
                'Los programas autoguiados están disponibles como manual y kit. La publicación del material no confirma una edición, inscripción, certificado, convenio ni disponibilidad de equipo.',
                'Para continuidad: conservar expediente de actividad, retroalimentación y cambio propuesto. Modificar contenido desde administración sin borrar partidas, entregas ni reportes anteriores.',
            ]),
        ],
    },
    'recorrido-funcional': {
        'titulo': 'Recorrido funcional: seis áreas conectadas por pedidos, materiales y datos',
        'seccion': '1.3', 'carpeta': 'Recorrido y conexiones entre áreas', 'fuentes': ('scor', 'gs1-traza'),
        'objetivo': 'Reconocer cómo se conectan las seis áreas docentes y qué evidencia intercambia cada una en un caso completo, sin confundir el mapa funcional con un plano físico verificado.',
        'bloques': [
            ('Mapa funcional de extremo a extremo', [
                'Pedido y demanda → planificación de abastecimiento → recepción y almacén → producción o preparación → transporte y distribución → operación internacional y terminal → entrega y devolución. El análisis y la trazabilidad conectan todos los pasos.',
                'Cada traspaso conserva identificador de pedido/lote, cantidad, unidad, estado, origen, destino, tiempo y responsable del registro. Una cantidad en tránsito no vuelve a contarse como existencia disponible.',
                'Este recorrido es conceptual. Consultar la galería, los espacios, fichas y responsables de la unidad para verificar ubicación, estado, aforo y recursos físicos antes de una visita o práctica.',
            ]),
            ('Áreas y decisiones', [
                'Almacén: recepción, ubicaciones, exactitud, slotting y picking; prácticas 01–02. Cadena de suministro: demanda, reposición y efecto látigo; prácticas 03–04 y juego de la cerveza.',
                'Transporte y distribución: red, carga, ventanas y contingencias; prácticas 05–06 y Centro de distribución. Producción y operaciones: capacidad, flujo y logística inversa; prácticas 07–08 y Smart factory.',
                'Operaciones internacionales: expediente coherente, controles documentales y terminal; prácticas 09–10 y Puerto virtual. Tecnologías aplicadas: eventos, trazabilidad y validación de IA; prácticas 11–12, transversales a las demás áreas.',
            ]),
            ('Caso integrador y puntos de control', [
                'Un equipo prepara un pedido sintético: define demanda y política de reposición, comprueba saldo por SKU, propone ubicación y registra preparación. Otro equipo recibe únicamente el expediente de traspaso y debe poder reconstruirlo.',
                'El equipo de distribución propone ruta con carga y horarios; operaciones internacionales comprueba coherencia del expediente; tecnologías revisa eventos y calidad de datos. Cada área informa discrepancias al área de origen sin modificar silenciosamente sus datos.',
                'Resultado: diagrama de flujo, tabla de traspasos, indicadores por área, incidencias y alternativa comparada. No atribuir estas cantidades a operaciones reales ni presentar un expediente docente como declaración aduanera.',
            ]),
            ('Del entorno virtual a la maqueta', [
                'Repetir primero el caso con datos sintéticos y simuladores; documentar señales, sensores o actuadores que se necesitarían. Conectar una maqueta sólo tras comprobar existencia, autorización, energía, parada y procedimiento seguro.',
                'No enviar órdenes desde un caso docente a un equipo real. Una integración futura debe separar simulación y operación, autenticar dispositivos y conservar registro de comandos y estados.',
                'Para experimentar con Centros I+D: identificar pregunta, recursos y custodio de datos; cada dominio conserva su inventario, autorización y expediente. El laboratorio docente complementa capacidades de investigación sin reemplazarlas.',
            ]),
        ],
    },
}


def _manual(clave, guia, html):
    return {
        'clave': clave, 'nombre': guia['titulo'], 'seccion': guia['seccion'],
        'carpeta': guia['carpeta'], 'descripcion': guia['objetivo'],
        'tipo_adjunto': 'manual', 'fuente': 'interna', 'licencia_uso': 'interna',
        'autor': 'UPEC · Contenido formativo original de logística',
        'url': '', 'html': html, 'nombre_archivo': 'logistica-' + clave + '.html',
    }


def recursos_complementarios():
    # Estos paquetes contienen sólo datos originales y renderizadores estáticos.
    from apps.formacion.management.cursos_precargados.cursos_logistica_aplicada import PROGRAMAS, build_kit, programa_documento_html
    from apps.laboratorios.operacion.management.laboratorios.logistica_contenidos import GUIAS as CONTENIDOS
    from apps.laboratorios.operacion.management.laboratorios.logistica_practicas import GUIAS as PRACTICAS, documento_html as practica_html, recursos_datasets

    recursos = []
    for clave, guia in {**GUIAS_ORIENTACION, **CONTENIDOS}.items():
        html = documento_html(clave, guia).replace('LOG-P1/', 'LOG-CONT/').replace(
            'Referencias revisadas 2026-10-11', 'Referencias revisadas 2026-10-12')
        recursos.append(_manual('contenido-' + clave, guia, html))
    for clave, guia in PRACTICAS.items():
        recursos.append(_manual(clave, guia, practica_html(clave, guia)))
    for datos in recursos_datasets():
        recursos.append({
            'clave': 'dataset-' + datos['clave'], 'nombre': datos['titulo'],
            'seccion': datos['seccion'], 'carpeta': datos['carpeta'],
            'descripcion': 'Datos sintéticos de aula con diccionario y resultados de control en la guía vinculada. No representan mediciones ni operaciones de UPEC.',
            'tipo_adjunto': 'dataset', 'fuente': 'interna', 'licencia_uso': 'interna',
            'autor': 'UPEC · Casos docentes originales de logística', 'url': '', 'html': '',
            'contenido': datos['contenido'], 'nombre_archivo': datos['nombre'],
        })
    for clave, programa in PROGRAMAS.items():
        curso = programa['CURSO']
        guia = {
            'titulo': curso['nombre'] + ' — programa y lecciones', 'seccion': '4.3',
            'carpeta': 'Programas autoguiados de logística aplicada',
            'objetivo': 'Programa de aprendizaje con lecciones, caso reproducible, datos sintéticos, autoevaluación y rúbrica. Disponible para consulta; una edición presencial o certificada exige convocatoria autorizada.',
        }
        recursos.append(_manual('formacion-' + clave, guia, programa_documento_html(clave)))
        recursos.append({
            'clave': 'kit-' + clave, 'nombre': curso['nombre'] + ' — kit de trabajo',
            'seccion': '4.3', 'carpeta': 'Kits reproducibles de formación logística',
            'descripcion': 'Manual HTML y datos CSV originales para realizar el caso y contrastar resultados sin conexión. Ejercicio sintético; no contiene ejecutables ni datos personales.',
            'tipo_adjunto': 'dataset', 'fuente': 'interna', 'licencia_uso': 'interna',
            'autor': 'UPEC · Formación logística aplicada', 'url': '', 'html': '',
            'contenido': build_kit(clave), 'nombre_archivo': 'logistica-formacion-' + clave + '.zip',
        })
    validar_catalogo(recursos)
    return recursos


def validar_catalogo(recursos):
    """Rechaza identidades duplicadas y rutas ambiguas antes de publicar."""
    claves, nombres = set(), set()
    for datos in recursos:
        clave = datos['clave']
        if not re.fullmatch(r'[a-z0-9-]+', clave) or clave in claves:
            raise ValueError('Identificador de recurso inválido o duplicado: ' + clave)
        claves.add(clave)
        if datos['seccion'] not in MAPA_LABORATORIO.secciones:
            raise ValueError('Sección de laboratorio desconocida: ' + datos['seccion'])
        nombre = datos.get('nombre_archivo', 'log-p1-' + clave + '.html')
        if (not re.fullmatch(r'[a-z0-9][a-z0-9_.-]*\.(?:html|csv|zip)', nombre)
                or PurePosixPath(nombre).name != nombre or nombre in nombres
                or nombre.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                    *('COM' + str(n) for n in range(1, 10)), *('LPT' + str(n) for n in range(1, 10))}):
            raise ValueError('Nombre de archivo inválido o duplicado: ' + nombre)
        nombres.add(nombre)
        if 'contenido' in datos and not isinstance(datos['contenido'], bytes):
            raise TypeError('El adjunto debe contener bytes: ' + clave)
        if not isinstance(datos.get('html', ''), str) or not isinstance(datos.get('url', ''), str):
            raise TypeError('HTML y URL deben ser texto: ' + clave)
        if sum(bool(datos.get(campo)) for campo in ('contenido', 'html', 'url')) != 1:
            raise ValueError('El recurso requiere exactamente una fuente de contenido: ' + clave)
        if datos.get('url') and not datos['url'].startswith('https://'):
            raise ValueError('La referencia debe usar HTTPS: ' + clave)
        if datos.get('contenido') and datos.get('html'):
            raise ValueError('El adjunto tiene dos contenidos: ' + clave)
        if datos.get('url') and (datos.get('contenido') or datos.get('html')):
            raise ValueError('El recurso mezcla archivo y enlace: ' + clave)
        for campo in ('nombre', 'descripcion', 'carpeta', 'autor'):
            if not str(datos[campo]).strip():
                raise ValueError('Metadato vacío: ' + campo + ' en ' + clave)
