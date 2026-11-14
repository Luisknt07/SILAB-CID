"""Precarga editable del FT04 para la práctica de centro de distribución.

Adaptador puro: no importa Django, no crea actividades, reservas ni guías y no
convierte parámetros digitales en datos operativos. El editor normaliza los
campos y conserva su flujo de privacidad, revisión y aprobación ordinario.
"""

from html import escape

from apps.laboratorios.operacion.presentation import logistica_distribucion_guia as docente
from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor

VERSION = "1.0.0"
ADVERTENCIA = (
    "Datos sintéticos de simulación. Esta guía no autoriza una sesión presencial, "
    "no acredita equipos instalados ni sustituye una reserva aprobada, la inducción "
    "y la verificación local de seguridad, aforo y recursos. Los tiempos digitales "
    "no son horas reales de uso del laboratorio."
)


def _semilla(semilla):
    if type(semilla) is not int or not 0 <= semilla <= 2147483647:
        raise ValueError("La semilla debe ser un entero entre 0 y 2147483647.")
    return semilla


def _p(texto):
    return "<p>" + escape(str(texto), quote=True) + "</p>"


def _lista(elementos, *, ordenada=False):
    etiqueta = "ol" if ordenada else "ul"
    return (
        "<"
        + etiqueta
        + ">"
        + "".join(
            "<li>" + escape(str(elemento), quote=True) + "</li>"
            for elemento in elementos
        )
        + "</"
        + etiqueta
        + ">"
    )


def _tabla(cabeceras, filas):
    return (
        "<table><thead><tr>"
        + "".join(
            "<th>" + escape(str(valor), quote=True) + "</th>" for valor in cabeceras
        )
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join(
                "<td>" + escape(str(valor), quote=True) + "</td>" for valor in fila
            )
            + "</tr>"
            for fila in filas
        )
        + "</tbody></table>"
    )


def procedencia_guia(caso="cd-normal", semilla=42):
    """Metadatos confiables para adjuntar después de normalizar el formulario.

    El integrador puede conservar esta fotografía en
    contenido['procedencia_simulacion']. No aceptar una fotografía equivalente
    enviada por el cliente como fuente de autorización o de verificación física.
    """
    ficha = docente.guia(caso)
    return {
        "tipo": "precarga_docente_centro_distribucion",
        "caso": caso,
        "semilla": _semilla(semilla),
        "version_adaptador": VERSION,
        "version_guia": ficha["version_guia"],
        "version_motor": motor.VERSION,
        "version_caso": motor.VERSION_CASO,
        "version_dataset": motor.DATASET_VERSION,
        "area": dict(ficha["area"]),
        "asignaturas": [dict(asignatura) for asignatura in ficha["asignaturas"]],
        "datos": "sinteticos",
        "autoriza_presencial": False,
    }


def _fundamento(ficha, procedencia):
    texto = _p(ADVERTENCIA) + "<h4>Contexto y procedencia del experimento</h4>"
    texto += _p(ficha["contexto"])
    texto += _tabla(
        ("Parámetro de simulación", "Valor"),
        [
            (clave, procedencia[clave])
            for clave in (
                "caso",
                "semilla",
                "version_adaptador",
                "version_guia",
                "version_motor",
                "version_caso",
                "version_dataset",
            )
        ],
    )
    texto += _p(
        "Área académica de referencia: "
        + ficha["area"]["codigo"]
        + " · "
        + ficha["area"]["nombre"]
        + ". La duración docente orientativa es "
        + str(ficha["duracion_minutos"])
        + " minutos; el horario y la asistencia reales se registran mediante el flujo institucional."
    )
    texto += "<h4>Asignaturas vinculadas</h4>" + _tabla(
        ("Código", "Asignatura", "Aplicación"),
        [(x["codigo"], x["nombre"], x["aplicacion"]) for x in ficha["asignaturas"]],
    )
    texto += "<h4>Prerrequisitos</h4>" + _lista(ficha["prerrequisitos"])
    for tema in ficha["teoria"]:
        texto += (
            "<h4>"
            + escape(tema["titulo"], quote=True)
            + "</h4>"
            + _p(tema["contenido"])
        )
    texto += "<h4>Hipótesis y condiciones de refutación</h4>" + _tabla(
        ("Elemento", "Definición"), list(ficha["hipotesis"].items())
    )
    texto += "<h4>Flujo y controles de las seis etapas</h4>" + _tabla(
        ("Etapa", "Entrada", "Operación", "Salida", "Control", "Indicador"),
        [
            (
                x["nombre"],
                x["entrada"],
                x["operacion"],
                x["salida"],
                x["control"],
                x["indicador"],
            )
            for x in ficha["etapas"]
        ],
    )
    texto += "<h4>Comparación experimental</h4>"
    comparacion = ficha["comparacion"]
    texto += _p(comparacion["unidad"]) + _p(comparacion["control"])
    texto += _p("Igualar: " + ", ".join(comparacion["igualar"]) + ".")
    texto += _p(comparacion["replicas"]) + _lista(comparacion["calculos"])
    texto += _p(comparacion["entre_variantes"]) + _p(comparacion["versiones"])
    texto += "<h4>Diccionario y visibilidad de los datos</h4>"
    for nombre, dataset in ficha["diccionario_datos"].items():
        texto += "<h5>" + escape(nombre, quote=True) + "</h5>"
        texto += _p(dataset["descripcion"]) + _p(dataset["visibilidad"])
        texto += _tabla(
            ("Campo", "Tipo", "Unidad", "Significado"),
            [
                (x["campo"], x["tipo"], x["unidad"], x["descripcion"])
                for x in dataset["campos"]
            ],
        )
    texto += "<h4>Límites de interpretación</h4>" + _lista(ficha["limites"])
    return texto


def _procedimiento(ficha):
    pasos = []
    for paso in ficha["procedimiento"]:
        pasos.append(
            "<li>"
            + _p(paso["titulo"])
            + _lista(paso["pasos"])
            + _p("Evidencia: " + paso["evidencia"])
            + "</li>"
        )
    pasos.append(
        "<li>"
        + _p("Vincular la práctica presencial únicamente cuando esté autorizada")
        + _lista(
            [
                "El responsable verifica existencia y operatividad de cada recurso, capacidad de atención, aforo, manuales, inducción y riesgos locales antes de programar. No convertir un nombre de catálogo en prueba de disponibilidad.",
                "Crear o utilizar una actividad y una guía mediante el editor institucional; el docente adapta el protocolo, el responsable revisa y aprueba. Esta precarga no publica ni aprueba documentos.",
                "Solicitar por separado la reserva real con fecha, horario, grupo y recursos comprobados; obtener aprobación y realizar el control de acceso que corresponda. No generar reservas desde resultados del simulador.",
                "Si la maqueta está autorizada, definir qué se mide, con qué instrumento y unidad, la identificación del recurso y el criterio de inicio y fin. Conservar mediciones físicas separadas del reloj y recorridos digitales.",
                "Registrar asistencia, horario, recursos realmente utilizados, incidencias y evidencias en la ejecución institucional. Una partida o captura digital no demuestra asistencia ni funcionamiento físico.",
                "Cerrar y validar la ejecución con el responsable. Comparar mediciones físicas y digitales declarando diferencias, incertidumbre y límites; no afirmar calibración ni equivalencia industrial sin validación independiente.",
            ]
        )
        + "</li>"
    )
    return "<ol>" + "".join(pasos) + "</ol>"


def _evaluacion(ficha):
    rubrica = ficha["rubrica_docente"]
    texto = _p(rubrica["nota"]) + _tabla(
        ("Criterio", "Puntos máximos", "Evidencia"),
        [(x["titulo"], x["puntos"], x["evidencia"]) for x in rubrica["criterios"]],
    )
    for criterio in rubrica["criterios"]:
        texto += (
            "<h4>"
            + escape(criterio["titulo"], quote=True)
            + "</h4>"
            + _tabla(
                ("Nivel", "Fracción de puntos", "Descriptor"),
                [
                    (x["nivel"], x["fraccion"], x["descriptor"])
                    for x in criterio["niveles"]
                ],
            )
        )
    return texto + _p(
        "Total de la rúbrica docente: " + str(rubrica["total"]) + " puntos."
    )


def inicial_guia(caso="cd-normal", semilla=42):
    """Devuelve initial compatible con GuiaPracticaForm, sin datos operativos.

    Bibliografía y materiales son texto fuente: el formulario institucional los
    normaliza al guardar. No hay campo 'conclusiones'; su protocolo se incorpora
    a resultados esperados y al paso de análisis. El integrador debe aplicar esta
    función sólo en un GET de guía nueva y nunca sobrescribir POST ni una versión
    ya guardada. Los campos de reserva se rellenan desde la reserva auténtica.
    """
    ficha = docente.guia(caso)
    procedencia = procedencia_guia(caso, semilla)
    codigo = "LOG-" + caso.upper()
    titulo = ficha["titulo"]
    objetivos = [
        x["verbo"] + ": " + x["criterio"] + " Evidencia: " + x["evidencia"]
        for x in ficha["objetivos"]
    ]
    resultados = "<h4>Entregables verificables</h4>" + _lista(ficha["entregables"])
    resultados += "<h4>Conclusión y reflexión</h4>" + _lista(
        ficha["preguntas_reflexion"]
    )
    resultados += _p(
        "Redactar una conclusión sustentada en los pares observados: indicar dirección y magnitud "
        "del cambio, resultado adverso o nulo, restricciones y qué dato real falta verificar. "
        "No presentar puntaje como calificación oficial ni simulación como prestación física."
    )
    return {
        "proposito_codigo": "docencia_practica",
        "subtipo_actividad": "practica_curricular",
        "nombre_actividad": titulo,
        "codigo_actividad": codigo,
        "descripcion_actividad": ficha["resumen"] + " " + ADVERTENCIA,
        "titulo": titulo,
        "codigo_guia": codigo + "-GUIA",
        "asignatura": ficha["asignaturas"][0]["nombre"],
        "formato_contenido": "html",
        "formato_procedimiento": "numerado",
        "resultado_aprendizaje": _p(
            "Operar y analizar un centro de distribución docente conciliando inventario por SKU, "
            "aplicando inspección, capacidad y FIFO, y contrastando una política con evidencia "
            "reproducible. Distinguir los datos sintéticos y los requisitos de una sesión presencial autorizada."
        ),
        "objetivos": _lista(objetivos),
        "fundamento_teorico": _fundamento(ficha, procedencia),
        "medidas_seguridad": _p(ADVERTENCIA) + _lista(ficha["seguridad_maqueta"]),
        "procedimiento": _procedimiento(ficha),
        "resultados_esperados": resultados,
        "criterios_evaluacion": _evaluacion(ficha),
        "bibliografia": "\n".join(
            fuente["titulo"]
            + ". [En línea]. Disponible: "
            + fuente["url"]
            + ". Consulta de la guía de origen: "
            + fuente["consulta"]
            + ". "
            + fuente["alcance"]
            for fuente in ficha["fuentes"]
        ),
        "materiales_complementarios": "\n".join(
            fuente["titulo"] + " | " + fuente["url"] for fuente in ficha["fuentes"]
        ),
        "permite_descarga": False,
        "solicita_publicacion": False,
    }
