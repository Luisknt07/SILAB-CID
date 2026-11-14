"""Recursos auxiliares del curso, en wiki opt-in y sin alterar sus horas.

Explicaciones y orientaciones originales. Los videos y referencias permanecen en
la fuente del autor; no se atribuyen demostraciones que no se hayan observado.
Cada lista sigue el orden de las cinco unidades del curso principal.
"""

from textwrap import dedent


def _wiki(contenido):
    return '[AULA_WIKI]\n' + dedent(contenido).strip()


BIENVENIDA_WIKI = _wiki('''
    ## Tu primera aplicación, paso a paso

    Bienvenido a **Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial**. Aprenderás a convertir una necesidad del almacén en un prototipo que puedas utilizar, explicar y comprobar. **No necesitas experiencia previa en programación**: comenzarás con una plantilla funcional y realizarás cambios pequeños con acompañamiento.

    ![Tu recorrido: comprender, construir, comprobar y presentar](/static/portal/img/cursos/logistica-ia/ruta-curso.svg)

    ## Una ruta de cinco unidades

    | Unidad | Qué harás | Tiempo |
    | --- | --- | --- |
    | 1. Diseñar | Definir problema, datos, pantallas y reglas. | 8 h |
    | 2. Comenzar | Preparar herramientas y entender la plantilla. | 8 h |
    | 3. Operar | Registrar entradas, salidas y consultar existencias. | 8 h |
    | 4. Conectar | Trabajar con CSV, indicadores y MCP de consulta. | 8 h |
    | 5. Demostrar | Probar, corregir y presentar tu aplicación. | 8 h |

    ## Cómo avanzar sin perderte

    1. **Leer:** comprende la necesidad y los conceptos.
    2. **Ver:** observa los fragmentos indicados y toma notas.
    3. **Practicar:** sigue la guía sobre tu copia del kit.
    4. **Verificar:** compara el resultado con un caso conocido.
    5. **Entregar:** reúne las evidencias y completa la evaluación.

    > [!TIP]
    > Guarda una versión antes de cambiar archivos. Si algo falla, conserva el error relevante y solicita una explicación sencilla.

    ## Herramientas y aprobación

    No se exige una suscripción de USD 200. Utiliza una alternativa gratuita disponible o el acceso autorizado por el laboratorio. Los límites del proveedor pueden cambiar. La aplicación funciona sin IA; la conexión conversacional necesita un modelo compatible y dispone de una alternativa de protocolo documentada.

    Las actividades obligatorias requieren aprobación; los cuestionarios admiten **tres intentos y mínimo 70 %**. El proyecto se revisa con rúbrica. El resultado es un **prototipo educativo local**, no un WMS empresarial ni una acreditación de terceros.

    ## Transcripción del video

    Narración sintética en español. Puedes leerla si prefieres estudiar sin audio.

    **Tu primera aplicación logística.** Bienvenido al curso Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial. Aquí transformarás una necesidad de inventarios y operaciones en un prototipo que puedas utilizar, explicar y comprobar. En este video conocerás la ruta del curso y cómo avanzar paso a paso.

    **Puedes empezar desde cero.** Este curso es introductorio. Está dirigido a estudiantes, egresados de Logística y carreras afines, y personas interesadas en digitalizar operaciones. No necesitas experiencia previa en programación. Trabajarás con una plantilla, instrucciones sencillas y cambios pequeños que puedas entender.

    **Una ruta de cinco unidades.** La ruta tiene cinco unidades y cuarenta horas. Primero defines el problema y diseñas la aplicación. Después preparas las herramientas. Luego construyes funciones logísticas, trabajas con datos y una conexión de inteligencia artificial, y finalmente pruebas y presentas tu proyecto.

    **Aprender con un caso concreto.** Nuestro caso es Andina Distribución, una organización ficticia. Su almacén registra productos, entradas, salidas y existencias. Aprenderás a impedir una salida sin stock y a conservar el historial de cada operación. Todos los datos de práctica son ficticios; no cargues información real de empresas o personas.

    **Así se estudia cada unidad.** En cada unidad sigue este recorrido: lee la explicación, mira los videos de apoyo, descarga los archivos y practica. Comprueba lo que obtienes antes de continuar. Los pasos están organizados como una guía de consulta: puedes volver a ellos cuando lo necesites. Guarda evidencias y entrega las actividades solicitadas.

    **Comprueba antes de avanzar.** Los cuestionarios requieren al menos setenta por ciento y permiten tres intentos. Lee la retroalimentación y revisa la explicación antes de volver a intentar. Las entregas y el proyecto final reciben revisión docente. Presenta resultados esperados y obtenidos, y explica las decisiones que tomaste. Las condiciones completas están en el aula.

    **IA que ayuda; datos que se verifican.** La inteligencia artificial ayuda a comprender y desarrollar. No necesitas contratar un plan de doscientos dólares para realizar el curso. Usarás las alternativas disponibles y una plantilla que funciona sin inteligencia artificial. La conexión preparada mediante MCP sólo consulta existencias. Siempre contrasta su respuesta con los registros; no modifica el inventario.

    **Pausa, pregunta y continúa.** Si un paso falla, pausa el video y vuelve a la guía. Anota qué hiciste y qué mensaje apareció. Busca ayuda en el espacio de acompañamiento del aula y conserva una versión anterior antes de cambiar archivos. Ahora abre la primera unidad y comienza con el problema logístico que quieres resolver.
''')

KIT_WIKI = _wiki('''
    ## Tu carpeta de trabajo

    Descarga el ZIP y extráelo en una carpeta propia. El kit contiene una aplicación funcional de **Andina Distribución**, una organización ficticia. Sus productos, cantidades y usuarios de práctica sirven para aprender; no representan operaciones reales de la universidad.

    ## Qué encontrarás

    | Carpeta o archivo | Para qué sirve |
    | --- | --- |
    | `README.md` | Instalación, arranque, roles y diagnóstico. |
    | `inventario/` | Datos, formularios, servicios y pruebas. |
    | `guias/` | Recorridos de las cinco unidades. |
    | `datos/` | CSV y casos de prueba ficticios. |
    | `plantillas/` | Ficha, diccionario, bitácora y rúbrica. |
    | Archivos MCP | Dos consultas preparadas de solo lectura. |

    ## Primer recorrido

    1. Lee `README.md` antes de instalar.
    2. Identifica `manage.py` y el Python indicado para el kit.
    3. Sigue los comandos de tu sistema, una línea por vez.
    4. Crea las cuentas **operador** y **lector**, con contraseñas propias.
    5. Comprueba el catálogo, el historial y el tablero antes de modificar nada.

    > [!WARNING]
    > No ejecutes el prototipo dentro del proyecto institucional. No compartas contraseñas, secretos ni bases con datos personales.

    ## Cómo aprovecharlo

    La plantilla evita que una dificultad de instalación o una cuota agotada detenga todo el aprendizaje. Tu aportación será **entender, mejorar y verificar** su funcionamiento. Identifica en la bitácora qué recibiste y qué cambiaste.

    Este recurso asigna **20 minutos de descarga y reconocimiento**. La instalación y los ejercicios se cuentan en sus laboratorios, no se añaden a las 40 horas. Para comprender los componentes consulta la [guía de Django para principiantes](https://tutorial.djangogirls.org/es/).
''')

VIDEOS_WIKI = [
    _wiki('''
        ## Mira para comprender, no para memorizar

        **Recurso del autor:** MoureDev, curso de Python para principiantes. En esta unidad utiliza la introducción y el bloque inicial de conceptos. No necesitas completar el video entero ni reproducir todas sus prácticas.

        El tiempo asignado es **30 minutos de estudio**, incluyendo reproducción, pausas y notas; no corresponde a la duración completa del recurso externo.

        | Observar | Aplicar a nuestro caso | Verificar |
        | --- | --- | --- |
        | Una explicación de dato o instrucción. | Describe código, cantidad y una operación. | Diferencia el dato de la acción. |
        | Un ejemplo que puedas seguir. | Escríbelo con productos ficticios. | Explica qué resultado esperarías. |
        | Una dificultad o concepto nuevo. | Formula una pregunta concreta. | Contrasta la respuesta con la lectura. |

        ## Tu nota de aprendizaje

        Anota tres palabras nuevas y explícalas sin copiar una definición. Puedes usar «cantidad», «condición» o «función» si aparecen en el fragmento que observaste. Si no aparece un concepto, búscalo en la lectura y señala que proviene de allí.

        > [!TIP]
        > Una duda bien descrita ayuda más que copiar una pantalla completa de código que todavía no entiendes.

        El video pertenece a su autor. Utilízalo desde el reproductor o [abre el recurso en YouTube](https://www.youtube.com/watch?v=Kp4Mvapo5kc). La alternativa en español es la lectura de esta unidad y la [introducción de Django Girls](https://tutorial.djangogirls.org/es/introduction/).
    '''),
    _wiki('''
        ## Observa un ciclo de trabajo con IA

        **Recurso del autor:** MoureDev, OpenCode desde cero. El objetivo del curso es reconocer cómo explicar una necesidad, revisar un plan y comprobar un cambio. No necesitas contratar el proveedor o plan mostrado por el autor.

        Dedica **30 minutos entre fragmentos y notas**. Estos capítulos de referencia permiten elegir lo que necesitas; no son una obligación de ver la sesión completa.

        | Fragmento de referencia | Observar | Aplicar y verificar |
        | --- | --- | --- |
        | Instalación, 00:04:20 | Preparación del agente. | Contrasta el procedimiento con tu sistema. |
        | Proveedores, 00:19:38; modelos, 00:26:56 | Opciones de conexión. | Comprueba disponibilidad y condiciones. |
        | Instrucciones, 00:31:16 | Forma de describir una tarea. | Pide un cambio pequeño y verificable. |
        | Desarrollo, desde 00:49:39 | Flujo de trabajo del ejemplo. | Relaciónalo con tu copia del kit. |

        ## Tu comprobación

        Escribe una instrucción para cambiar únicamente una ayuda de pantalla. Pide primero el plan, identifica los archivos afectados y prepara una prueba. No aceptes modificar veinte archivos para cambiar una frase sin entender la razón.

        > [!NOTE]
        > El agente y el modelo son componentes diferentes. Una opción gratuita puede tener límites; consulta las condiciones antes de activar una API.

        Consulta el [video de su autor](https://www.youtube.com/watch?v=aDJNG_f2C3E) y contrasta los pasos con la [documentación de OpenCode](https://opencode.ai/docs/). La lectura del aula es la alternativa textual y mantiene el alcance de nuestro prototipo.
    '''),
    _wiki('''
        ## Reconoce el patrón de una aplicación Django

        **Recurso del autor:** Fazt, ejemplo CRUD con Django. Selecciona los fragmentos sobre modelos, formularios y registro de datos. El proyecto del video no es nuestro inventario: úsalo para comparar componentes, mientras trabajas sobre el kit del curso.

        Dedica **30 minutos con pausas y contraste**. No necesitas terminar el recurso ni reemplazar las versiones de Python o Django fijadas en el kit por las del ejemplo externo.

        | Observar | Aplicar al almacén | Verificar en tu copia |
        | --- | --- | --- |
        | Cómo se describen los datos. | Identifica un producto y sus campos. | Busca los campos reales en `models.py`. |
        | Cómo se recibe una entrada del usuario. | Reconoce el formulario de movimiento. | Localiza sus comprobaciones. |
        | Cómo se muestra un resultado. | Revisa saldo e historial. | Contrasta una entrada conocida. |

        ## Una comparación útil

        Dibuja el recorrido **formulario → vista → servicio → datos → respuesta**. Pide a la IA que explique una parte, sin modificarla, y comprueba que los nombres que menciona existen en tus archivos. Un ejemplo genérico de edición de registros no autoriza cambiar saldos directamente.

        > [!WARNING]
        > Conserva las validaciones, el historial y los permisos del inventario. No copies una operación solo porque funciona en otro proyecto.

        Abre el [video de Fazt](https://www.youtube.com/watch?v=e6PkGDH4wWA). Como alternativa consulta [modelos y administración](https://docs.djangoproject.com/es/5.2/intro/tutorial02/) y [formularios y vistas](https://docs.djangoproject.com/es/5.2/intro/tutorial04/) en la documentación oficial.
    '''),
    _wiki('''
        ## Ubica las piezas de una conexión MCP

        Este recurso está enlazado desde **Microsoft MCP for Beginners**. Utilízalo como apoyo para reconocer cliente, servidor y herramienta. La práctica logística se realiza con las dos consultas preparadas del kit, no con integraciones de escritura de otros sistemas.

        Dedica **30 minutos de observación, pausas y notas**. El video está en inglés: usa subtítulos en español si el reproductor los ofrece. La lectura del aula proporciona una alternativa en español para completar el mismo aprendizaje.

        | Observar | Aplicar al caso | Verificar |
        | --- | --- | --- |
        | Una explicación de cliente o servidor. | Dibuja el recorrido de nuestra consulta. | Distingue conexión y generación de respuesta. |
        | Cómo se presenta una herramienta. | Reconoce `consultar_existencias`. | Comprueba su entrada y resultado. |
        | Una condición o límite mencionado. | Compara con nuestro acceso de lectura. | Identifica qué operación queda fuera. |

        ## Tu actividad de contraste

        Pregunta por un código ficticio y compara la respuesta con la aplicación. Anota si utilizaste un modelo o el cliente de protocolo. Esa diferencia importa: probar una herramienta sin modelo no equivale a mantener una conversación con IA.

        > [!TIP]
        > El protocolo no incluye un modelo gratuito ilimitado ni permisos automáticos. Comprueba qué herramientas están realmente disponibles.

        Consulta el [video enlazado](https://www.youtube.com/watch?v=agBbdiOPLQA) y la [explicación oficial de herramientas y recursos MCP](https://modelcontextprotocol.io/docs/learn/server-concepts). Las sesiones adicionales de Jhoni Cerón son ampliaciones opcionales, fuera de las 40 horas.
    '''),
    _wiki('''
        ## Aprende a conservar cambios recuperables

        **Recurso del autor:** MoureDev, Git y GitHub para principiantes. Selecciona la introducción a versiones y commits. Dedica **30 minutos entre observación y contraste** con tu proyecto; no necesitas completar todo el curso externo ni publicar el repositorio en internet.

        | Observar | Aplicar | Verificar |
        | --- | --- | --- |
        | Una explicación de versión o commit. | Identifica un estado que funciona. | Puedes describir qué contiene. |
        | Un cambio respecto de la versión anterior. | Guarda una mejora pequeña del kit. | Reconoces los archivos afectados. |
        | Una forma de revisar el historial. | Localiza antes y después de una corrección. | Explicas cómo recuperarías el estado anterior. |

        ## Conecta versiones con pruebas

        Una versión guardada no demuestra que el inventario calcule correctamente. Ejecuta las pruebas y comprueba una entrada, una salida y un rechazo después de tu mejora. En la bitácora relaciona **cambio, motivo, prueba y resultado**.

        Si todavía no utilizas Git, sigue la alternativa de copias identificadas que permite la guía. Conserva la copia anterior; no ensayes recuperación borrando tu único proyecto.

        > [!WARNING]
        > Excluye entornos virtuales, bases de datos, configuración personal, secretos y contraseñas. Guardar versiones no vuelve seguro publicar esos archivos.

        Consulta el [video de MoureDev](https://www.youtube.com/watch?v=3GymExBkKjE) y la [introducción oficial de GitHub](https://docs.github.com/es/get-started/start-your-journey/hello-world). La entrega final evalúa comprensión y reproducibilidad; no la cantidad de commits ni el servicio que utilizaste.
    '''),
]

GUIAS_WIKI = [
    _wiki('''
        ## Tu guía para diseñar antes de construir

        Abre el PDF para consultar las lecturas y el laboratorio de esta unidad sin depender de la conexión. Su revisión asigna **20 minutos**; las tareas prácticas ya están incluidas en las ocho horas de la unidad.

        | Revisa | Busca | Conserva como evidencia |
        | --- | --- | --- |
        | Caso y necesidad | Usuario, problema y decisión. | Ficha del proyecto. |
        | Datos y reglas | Campos, ejemplos y restricciones. | Diccionario de datos. |
        | Recorrido | Pantalla, operación y resultado. | Tres bocetos comprensibles. |
        | Alcance | Lo indispensable y lo posterior. | Criterios de aceptación. |

        ## Cómo utilizar el documento

        1. Lee una sección y explica su idea con un ejemplo de almacén.
        2. Completa la plantilla correspondiente del kit.
        3. Comprueba una operación conocida antes de describir funciones nuevas.
        4. Reúne las evidencias solicitadas en el laboratorio del aula.

        > [!TIP]
        > El criterio «una salida excesiva se rechaza sin cambiar saldo ni historial» se puede comprobar. «La aplicación será moderna» todavía no define un resultado observable.

        El PDF no reemplaza el cuestionario ni la entrega del laboratorio. Los videos externos se consultan desde la fuente del autor; no están incorporados como archivos dentro de la guía.

        Si necesitas aclarar la relación entre pantalla y servidor consulta [cómo funciona internet](https://tutorial.djangogirls.org/es/how_the_internet_works/). Vuelve después al caso y evita ampliar el alcance a facturación, rutas o varias bodegas.
    '''),
    _wiki('''
        ## Tu guía para arrancar y entender el kit

        Revisa el PDF durante **20 minutos** para ubicar la secuencia y los conceptos. La instalación se realiza dentro del laboratorio de esta unidad; estas orientaciones no añaden horas al curso.

        | Paso | Referencia principal | Resultado que comprobarás |
        | --- | --- | --- |
        | Preparar | `README.md` del kit. | Python y entorno correctos. |
        | Ejecutar | Comandos de tu sistema. | Aplicación local disponible. |
        | Reconocer | Mapa de archivos. | Puedes explicar dato, pantalla y regla. |
        | Cambiar | Instrucción pequeña a la IA. | Mejora visible y recuperable. |

        ## Sigue el orden

        1. Extrae el kit en una carpeta propia.
        2. Ejecuta los pasos uno por uno y lee sus resultados.
        3. Ingresa como operador y después como lector.
        4. Realiza una modificación pequeña y compruébala.
        5. Guarda las evidencias y anota cómo volverías atrás.

        > [!WARNING]
        > Si falla un comando, identifica el error antes de continuar. No desactives permisos del equipo ni compartas secretos para resolverlo.

        El PDF explica el recorrido, pero los comandos exactos y las versiones se consultan en el README. Esa referencia evita mezclar ejemplos de otros sistemas o tutoriales antiguos.

        Puedes ampliar el significado del entorno virtual en la [documentación de Python](https://docs.python.org/es/3/tutorial/venv.html). Al regresar al aula, entrega el arranque, el mapa de archivos y el cambio comprobado; ver una pantalla no completa por sí solo el laboratorio.
    '''),
    _wiki('''
        ## Tu guía para comprobar una operación completa

        Este PDF reúne las lecturas y el laboratorio de inventario. Dedica **20 minutos a revisar el recorrido** y utiliza después tu copia del kit para practicar dentro del tiempo asignado al laboratorio.

        | Operación del ejemplo | Resultado esperado | Qué revisar |
        | --- | --- | --- |
        | Entrada de 10 sobre saldo 0. | Saldo 10. | Movimiento guardado. |
        | Salida de 3. | Saldo 7. | Historial actualizado. |
        | Intento de salida de 8. | Rechazo; saldo 7. | Ningún movimiento adicional. |
        | Solicitud desde Consulta. | Escritura rechazada. | Datos sin cambios. |

        ## Trabaja con un producto de prueba

        No mezcles esta secuencia con productos que ya tienen operaciones. Identifica estado inicial, acción, resultado esperado y obtenido. Si el navegador impide enviar una cantidad incorrecta, revisa también la comprobación del servidor mediante las pruebas guiadas; no elimines la validación para experimentar.

        > [!NOTE]
        > Un mensaje de éxito no basta. Comprueba saldo e historial. Un botón oculto tampoco basta para proteger una operación.

        Conserva la matriz de pruebas y la mejora pequeña que solicitaste a la IA. Los errores y correcciones documentados son parte del aprendizaje, siempre que puedas explicar y verificar el resultado final.

        Consulta la [validación de formularios de Django](https://docs.djangoproject.com/en/5.2/ref/forms/validation/) si necesitas ampliar una regla. La guía no exige construir varias bodegas, lotes o un sistema empresarial completo.
    '''),
    _wiki('''
        ## Tu guía de datos, indicadores y MCP

        Revisa el PDF durante **20 minutos** para ubicar archivos, reglas y evidencias. Las importaciones y la conexión se practican dentro del laboratorio de la unidad, sin añadir horas a las cuarenta del curso.

        | Parte | Qué comprobar | Evidencia |
        | --- | --- | --- |
        | CSV válido | Encabezados, unidad y formato decimal. | Catálogo cargado. |
        | CSV inválido | Rechazo completo y errores informados. | Ausencia de carga parcial. |
        | Indicadores | Conteos reproducibles y criterio bajo mínimo. | Tabla esperado/obtenido. |
        | MCP | Dos consultas y acceso de lectura. | Respuesta contrastada. |

        ## Cuida el contexto del indicador

        El tablero cuenta productos registrados, bajo mínimo y sin existencias. Si agregas productos, el total cambia. Para comparar casos A, B y C, delimita ese subconjunto o registra el total anterior; no atribuyas a tu prueba los cambios de otros registros.

        > [!TIP]
        > Detén el servidor web cuando lo indique el README para la verificación MCP. Al comparar después con la pantalla, vuelve a iniciar la aplicación local según esa misma guía.

        Si no hay un modelo disponible, utiliza el cliente de protocolo preparado y declara esa modalidad. No fabriques una conversación: explicar la conexión, los datos y el límite de lectura es la evidencia necesaria de esa ruta.

        Consulta las [herramientas MCP](https://modelcontextprotocol.io/docs/learn/server-concepts). Las sesiones externas de ampliación son opcionales y no cambian la evaluación ni el tiempo obligatorio.
    '''),
    _wiki('''
        ## Tu guía para revisar y presentar

        Este PDF reúne las lecturas, el laboratorio de revisión y la consigna del proyecto final. Asigna **20 minutos de consulta**; la elaboración del proyecto se distribuye entre las prácticas anteriores y el cierre de esta unidad.

        | Revisión | Pregunta útil | Evidencia |
        | --- | --- | --- |
        | Funciones | ¿El recorrido llega al resultado esperado? | Demostración. |
        | Datos | ¿Se rechazan cantidades y códigos incorrectos? | Matriz de pruebas. |
        | Acceso | ¿Consulta puede leer sin modificar? | Intento rechazado. |
        | Entrega | ¿Otra persona puede ejecutar el proyecto? | Guía y archivos. |

        ## Prepara una entrega reproducible

        1. Repite las pruebas después de la última mejora.
        2. Reúne datos ficticios y resultados esperados/obtenidos.
        3. Identifica el kit recibido, la ayuda de IA y tu aportación.
        4. Excluye contraseñas, secretos, bases y entornos virtuales.
        5. Ensaya un recorrido correcto y otro rechazado.

        > [!WARNING]
        > Si hay stock negativo o escritura sin permiso, corrige antes de solicitar aprobación, aunque otros apartados obtengan una buena puntuación.

        Consulta la rúbrica completa del proyecto en el aula. El mínimo es 70/100 y la aprobación requiere revisión del instructor; marcar un archivo como leído no equivale a aprobar el proyecto.

        Amplía la interpretación de las comprobaciones en la [introducción a pruebas de Django](https://docs.djangoproject.com/es/5.2/topics/testing/overview/). Comunica las limitaciones del prototipo y evita presentarlo como un servicio listo para producción.
    '''),
]

REFERENCIAS_WIKI = [
    _wiki('''
        ## Consulta puntual: Django Girls

        Esta referencia en español ayuda a comprender cómo funciona una aplicación web desde el inicio. No debes completar todo el tutorial ni crear un segundo proyecto para avanzar en nuestro curso.

        Dedica **20 minutos a una consulta acotada**: localiza una explicación que aclare el recorrido de nuestro caso y regresa al aula. El kit sigue siendo la base de la práctica.

        | Busca | Relación con logística | Pregunta de comprobación |
        | --- | --- | --- |
        | Navegador y servidor. | Solicitar una consulta de existencias. | ¿Dónde se comprueban los datos? |
        | Datos de una aplicación. | Identificar productos y movimientos. | ¿Qué se conserva? |
        | Una explicación para principiantes. | Describir una pantalla y su resultado. | ¿Puedes explicarla sin copiar? |

        ## Convierte la consulta en una nota

        Escribe la duda inicial, la idea encontrada y un ejemplo de Andina Distribución. Si la explicación utiliza otro proyecto, conserva el concepto sin copiar sus datos o funciones a nuestro inventario.

        > [!NOTE]
        > No memorices comandos en esta primera consulta. Comprende qué parte recibe la solicitud, cuál aplica reglas y cuál guarda información.

        Consulta [Django Girls en español](https://tutorial.djangogirls.org/es/) y vuelve a completar el diseño de tu primera versión. La fuente externa apoya la lectura; no reemplaza las reglas ni las evidencias solicitadas en el laboratorio.
    '''),
    _wiki('''
        ## Consulta puntual: trabajar con OpenCode

        Utiliza la documentación de OpenCode para aclarar una tarea concreta: instalar el agente, distinguir planificación y construcción o revisar sus permisos. El objetivo del curso se mantiene aunque utilices otro asistente disponible.

        Dedica **20 minutos de consulta**. No es necesario recorrer toda la documentación ni conectar todos los proveedores que aparecen en ella.

        | Tema | Qué necesitas comprender | Aplicación en el curso |
        | --- | --- | --- |
        | Primeros pasos | Cómo abrir tu carpeta de trabajo. | Trabajar sobre el kit. |
        | Plan y modificación | Qué cambiaría antes de editar. | Pedir una mejora pequeña. |
        | Permisos | Qué acciones puede ejecutar el agente. | Revisar comandos y archivos. |
        | Modelos | Disponibilidad y condiciones. | Elegir acceso sin compra obligatoria. |

        ## Comprueba lo que encontraste

        Escribe una instrucción que incluya necesidad, límite y prueba. Pide que el asistente explique los archivos afectados y conserva una versión antes de aceptar el cambio. Si una propuesta elimina una validación, detén el cambio y pide una alternativa.

        > [!WARNING]
        > Una suscripción de chat no implica crédito de API. Revisa las condiciones vigentes y no añadas claves al código o a la entrega.

        Consulta la [documentación principal](https://opencode.ai/docs/) y los [permisos de OpenCode](https://opencode.ai/docs/permissions/). Registra una duda concreta y vuelve a practicar: leer todas las opciones del agente no es un requisito del curso.
    '''),
    _wiki('''
        ## Consulta puntual: formularios y vistas

        La documentación oficial de Django ayuda a entender cómo una pantalla recibe una solicitud y produce una respuesta. Utiliza esta consulta para reconocer el patrón en nuestro kit, sin reemplazar sus reglas por las de otro ejemplo.

        Dedica **20 minutos** a localizar el concepto que necesitas. No debes terminar el tutorial entero ni memorizar todas las opciones de Django.

        | Componente | Qué buscar | Qué comprobar en el kit |
        | --- | --- | --- |
        | Formulario | Campos, datos recibidos y errores. | Cantidad y motivo. |
        | Vista | Respuesta a una solicitud. | Permiso antes de operar. |
        | Servicio | Regla logística de nuestro proyecto. | Entrada, salida y rechazo. |
        | Pantalla | Mensaje que recibe el usuario. | Saldo e historial coherentes. |

        ## Sigue una operación

        Localiza el formulario de movimiento y sigue su recorrido con ayuda de la lectura. Anota dónde se comprueba la cantidad y dónde se registra el movimiento. Si la IA menciona una función, búscala realmente antes de dar por correcta la explicación.

        > [!NOTE]
        > El tutorial enseña Django con otro caso. Las reglas del almacén y la separación en servicios pertenecen a nuestro kit; no se atribuyen al ejemplo externo.

        Abre [formularios y vistas de Django 5.2](https://docs.djangoproject.com/es/5.2/intro/tutorial04/) y vuelve al laboratorio con una explicación breve. Comprueba también una solicitud incorrecta: completar un caso exitoso no demuestra por sí solo que el servidor rechace datos inválidos.
    '''),
    _wiki('''
        ## Consulta puntual: herramientas MCP

        La referencia oficial distingue las funciones que un servidor expone y los datos que pueden consultarse. Úsala para comprender la conexión preparada del curso; no exige construir otro servidor ni automatizar escritura.

        Dedica **20 minutos** a identificar herramienta, entrada, resultado y límite. Después regresa al kit para contrastar la explicación con las consultas disponibles.

        | Pieza | Pregunta útil | Ejemplo del curso |
        | --- | --- | --- |
        | Herramienta | ¿Qué función existe realmente? | Consultar existencias. |
        | Entrada | ¿Qué dato necesita? | Código de producto. |
        | Resultado | ¿Qué devuelve? | Datos del registro consultado. |
        | Límite | ¿Qué acción no ofrece? | Registrar una salida. |

        ## Contrasta una respuesta

        Describe la ruta de la solicitud y comprueba los datos en el tablero. Distingue lo que devolvió la herramienta de la explicación redactada por el modelo. Si utilizaste el cliente de protocolo, registra esa modalidad: comprobaste la integración, no una conversación inexistente.

        > [!WARNING]
        > Un texto de producto no otorga autoridad para ejecutar acciones. El asistente debe respetar las herramientas y permisos disponibles.

        Consulta [herramientas y recursos MCP](https://modelcontextprotocol.io/docs/learn/server-concepts) y la [arquitectura del protocolo](https://modelcontextprotocol.io/docs/learn/architecture). Anota una duda y una comprobación propia. Las ampliaciones externas no modifican la consigna ni la rúbrica del proyecto.
    '''),
    _wiki('''
        ## Consulta puntual: pruebas en Django

        Esta referencia permite entender qué comprueban las pruebas automáticas y cómo se ejecutan dentro de un proyecto. En el curso utilizas las comprobaciones preparadas del kit y las relacionas con situaciones logísticas conocidas.

        Dedica **20 minutos a una pregunta concreta**. No se exige diseñar una infraestructura avanzada de pruebas ni memorizar todas las clases y métodos del framework.

        | Situación | Resultado esperado | Evidencia complementaria |
        | --- | --- | --- |
        | Entrada válida | Suma e historial coherentes. | Saldo calculado manualmente. |
        | Salida excesiva | Rechazo sin cambios. | Historial antes y después. |
        | Cantidad inválida | Error de validación. | Mensaje y prueba. |
        | Usuario de consulta | Escritura impedida. | Solicitud rechazada. |

        ## Explica una comprobación

        Elige una prueba del kit y describe estado inicial, acción y resultado esperado. Ejecuta el conjunto después de tu mejora y conserva el resumen. Si falla, identifica la causa antes de cambiar la expectativa para que la prueba pase.

        > [!TIP]
        > Un resultado correcto aporta evidencia de los escenarios incluidos. No demuestra que cualquier uso futuro esté libre de errores.

        Consulta la [introducción a pruebas de Django](https://docs.djangoproject.com/es/5.2/topics/testing/overview/). Vuelve al aula para completar tu matriz y la entrega. Las capturas, pruebas automáticas y demostración manual se complementan; ninguna sustituye explicar las reglas del prototipo.
    '''),
]


def _quiz(numero, tabla, caso, referencia):
    final = 'la evaluación final integradora' if numero == 5 else f'el quiz de la unidad {numero}'
    return _wiki(f'''
        ## Prepárate para {final}

        Esta actividad tiene **ocho preguntas**, **30 minutos asignados**, **tres intentos** y requiere **70 % para aprobar**. Encontrarás decisiones y situaciones del caso, no una prueba de memorización de comandos. Lee si se solicita una respuesta o varias.

        ## Antes de comenzar

        Completa las lecciones y actividades obligatorias anteriores. La evaluación se habilita cuando esas actividades están aprobadas o completadas según su tipo. Si un deber sigue en revisión, consulta su estado antes de intentar avanzar.

        | Revisa | Debes poder explicar |
        | --- | --- |
        {tabla}

        ## Ensaya con un caso conocido

        {caso}

        Escribe primero lo que esperarías y después compáralo con el comportamiento observado. Separa una afirmación del asistente de una evidencia del sistema: una explicación convincente no garantiza que el resultado sea correcto.

        > [!TIP]
        > Si una respuesta resulta incorrecta, lee la explicación, localiza la regla y prueba otro ejemplo antes de usar el siguiente intento.

        La calificación no depende del precio del asistente. Usa las lecturas, el kit y la [referencia de apoyo]({referencia}) para preparar los conceptos; no necesitas completar documentación adicional entera. La evaluación final también requiere que el proyecto y las actividades anteriores estén aprobados.
    ''')


ORIENTACIONES_QUIZ = [
    _quiz(1,
          '| Alcance | Una primera versión completa y pequeña. |\n'
          '| Datos y reglas | Diferencia entre campo, operación y restricción. |\n'
          '| Recorrido | Pantalla, servidor y base de datos. |',
          'Describe cómo registrarías una salida cuando hay 7 unidades y se solicitan 8. '
          'Indica qué información necesitas y qué registros deberían permanecer iguales.',
          'https://tutorial.djangogirls.org/es/how_the_internet_works/'),
    _quiz(2,
          '| Herramientas | Diferencia entre agente, modelo y aplicación. |\n'
          '| Instrucciones | Contexto, límite y prueba de aceptación. |\n'
          '| Recuperación | Versiones, errores y secretos. |',
          'Quieres cambiar una frase de la pantalla. Describe qué pedirías, qué revisarías '
          'antes de aceptar y cómo comprobarías que el inventario sigue funcionando.',
          'https://opencode.ai/docs/'),
    _quiz(3,
          '| Existencias | Entrada, salida y saldo esperado. |\n'
          '| Validación | Cantidad, precisión y disponibilidad. |\n'
          '| Permisos | Rechazo del servidor e historial intacto. |',
          'Parte de 10 unidades, recibe 6 y retira 4. Calcula el saldo y prepara un intento '
          'de salida que deba rechazarse. Comprueba saldo e historial, no solo el mensaje.',
          'https://docs.djangoproject.com/en/5.2/ref/forms/validation/'),
    _quiz(4,
          '| CSV | Encabezados, formato y duplicados. |\n'
          '| Indicadores | Fórmula, alcance y unidades. |\n'
          '| MCP | Protocolo, herramienta, resultado y límite de lectura. |',
          'El modelo informa un saldo diferente del que devuelve la herramienta. Describe '
          'qué contrastarías y por qué no cambiarías el inventario para igualar la respuesta.',
          'https://modelcontextprotocol.io/docs/learn/server-concepts'),
    _quiz(5,
          '| Funcionamiento | Recorrido completo y resultados comprobables. |\n'
          '| Evidencias | Pruebas, permisos y aportación propia. |\n'
          '| Alcance | Prototipo educativo, aprobación y limitaciones. |',
          'El proyecto supera 70 puntos, pero permite una salida mayor a las existencias. '
          'Explica qué debe corregirse y qué evidencia presentarías antes de solicitar aprobación.',
          'https://docs.djangoproject.com/es/5.2/topics/testing/overview/'),
]

PROYECTO_WIKI = _wiki('''
    ## Tu reto final: una aplicación que puedas explicar

    Demuestra cómo conviertes una necesidad logística en un **prototipo educativo con datos comprobables**. Utiliza el caso de productos, entradas, salidas y existencias; puedes adaptar nombres a un almacén comercial, agroindustria o abastecimiento conservando las funciones evaluadas. Trabaja con datos ficticios y la plantilla del curso. No debes construir un WMS empresarial desde cero.

    Los **110 minutos de esta actividad** se destinan a reunir, revisar y presentar el trabajo acumulado en los laboratorios. No son el tiempo para comenzar de nuevo toda la aplicación.

    ![Recorrido de comprobación y preparación de la entrega](/static/portal/img/cursos/logistica-ia/pruebas-entrega.svg)

    ## Paso 1. Delimita y completa el recorrido

    | Función | Evidencia mínima |
    | --- | --- |
    | Catálogo | Código único, descripción, unidad y mínimo. |
    | Operación | Entradas y salidas con cantidad, fecha, motivo y responsable. |
    | Consulta | Existencias, búsqueda de productos e historial. |
    | Datos | Carga controlada y exportación comprensible. |
    | Indicador | Bajo mínimo, con criterio escrito y cálculo comprobado. |
    | Acceso | Consulta lee; Operación registra según sus permisos. |
    | MCP | Consultas de lectura con resultados contrastados. |

    Usa la búsqueda disponible y consulta el historial; **no se exige añadir filtros al historial**. No incluyas facturación, compras completas, optimización de rutas ni varias bodegas para obtener una mejor nota.

    ## Paso 2. Comprueba datos y permisos

    Antes de ejecutar, escribe estado inicial, acción y resultado esperado. Después registra lo obtenido y su evidencia. Utiliza un producto de prueba para no mezclar secuencias anteriores.

    | Prueba | Resultado esperado |
    | --- | --- |
    | Crear producto y repetir su código. | Duplicado rechazado. |
    | Partir de 10, recibir 6 y retirar 4. | Saldo final 12. |
    | Intentar retirar 13 sobre ese saldo. | Rechazo; saldo 12 e historial intacto. |
    | Enviar cero, negativo o texto como cantidad. | Rechazo sin cambios indebidos. |
    | Intentar escribir como Consulta. | Rechazo también mediante solicitud directa. |
    | Importar archivo inválido. | Errores informados; ninguna carga parcial. |
    | Comparar bajo mínimo. | Coincide con el cálculo manual definido. |
    | Consultar mediante MCP. | Respuesta coincide con los registros; no escribe. |

    Repite las pruebas después de la última mejora. El kit ofrece comprobaciones automáticas y guías; puedes complementarlas con una demostración manual registrada, sin crear una infraestructura avanzada.

    ## Paso 3. Documenta tu aportación

    Entrega una ficha de una página con problema, usuario, funciones, reglas, herramientas y limitaciones. Distingue **kit inicial, propuesta de IA y decisión personal**. Registra tres intervenciones: necesidad, instrucción, cambio propuesto, revisión y prueba. Incluye una corrección o propuesta descartada cuando corresponda; no inventes conversaciones.

    Si el acceso al modelo se agotó, identifica lo realizado con las guías y solicita al docente la alternativa prevista. El precio de la herramienta y la cantidad de código generado no conceden puntos adicionales.

    ## Paso 4. Reúne una entrega reproducible

    - Código comprimido o repositorio accesible al evaluador, con dependencias e instrucciones.
    - Ficha, datos ficticios y tabla de resultados esperados/obtenidos.
    - Cálculo manual de un saldo y un indicador.
    - Bitácora de intervenciones y cambios.
    - Guía breve de uso y demostración de **5 a 8 minutos**, en directo o grabada según indique el docente.

    Excluye `.venv`, base local, contraseñas, secretos y configuración personal. Otra persona debe poder preparar el prototipo desde los archivos entregados. No se requiere una grabación con producción audiovisual profesional.

    ## Paso 5. Revisa la rúbrica completa

    | Apartado | Criterio comprobable | Puntos |
    | --- | --- | --- |
    | A. Funciones | Crea y consulta productos con campos y búsqueda útiles. | 10 |
    | A. Funciones | Registra entrada y salida válidas; calcula el saldo. | 10 |
    | A. Funciones | Conserva historial y demuestra el recorrido completo. | 10 |
    | **Subtotal A** | **Funciones y recorrido operativo** | **30** |
    | B. Datos | Código único y campos obligatorios en servidor. | 5 |
    | B. Datos | Cantidad positiva, decimales y unidades coherentes. | 5 |
    | B. Datos | Rechaza salida excesiva sin cambiar saldo ni historial. | 10 |
    | B. Datos | Detecta duplicados y datos inválidos; informa errores y política de carga. | 5 |
    | **Subtotal B** | **Datos y validaciones** | **25** |
    | C. Consultas | Bajo mínimo y consulta de movimientos coinciden con registros y alcance. | 5 |
    | C. Consultas | Exportación utilizable, con encabezados y unidades. | 5 |
    | C. Consultas | MCP reproducible, solo lectura y resultados contrastados. | 5 |
    | **Subtotal C** | **Consultas, reportes e integración** | **15** |
    | D. IA | Documenta tres instrucciones, cambios y decisiones. | 5 |
    | D. IA | Explica comprobaciones, correcciones y limitaciones. | 5 |
    | **Subtotal D** | **Uso de IA explicado y trazable** | **10** |
    | E. Pruebas | Casos válidos, inválidos y de límite: esperado/obtenido. | 5 |
    | E. Pruebas | Consulta no modifica datos; rechazo directo sin cambios. | 5 |
    | **Subtotal E** | **Pruebas y permisos** | **10** |
    | F. Entrega | Guía que permite ejecutar y utilizar el prototipo. | 5 |
    | F. Entrega | Demuestra, interpreta resultados y comunica límites. | 5 |
    | **Subtotal F** | **Guía y demostración** | **10** |
    | **TOTAL** | | **100** |

    Cada criterio obtiene sus puntos completos si funciona y se demuestra; aproximadamente la mitad si está parcialmente implementado con evidencia; cero si no existe o no puede comprobarse. Los mensajes visuales no sustituyen la validación del servidor.

    ## MCP sin compra obligatoria

    Utiliza el conector preparado. No se exige crear otro servidor ni contratar una API. Si no hay modelo disponible, se acepta el **cliente de prueba de protocolo**, con sus resultados identificados como prueba sin conversación. Se evalúan conexión, datos y límites con los mismos criterios del apartado C: **MCP vale 5 puntos**.

    ## Aprobación y correcciones

    > [!WARNING]
    > El mínimo es **70/100**. Además, debes corregir fallos que permitan stock negativo o modificaciones sin permiso antes de aprobar, aunque el total inicial supere 70.

    El instructor revisa la entrega, solicita correcciones y registra la nota validada. El aula almacena esa nota; no inspecciona automáticamente los fallos de tu prototipo. Aprobar el proyecto no sustituye los cuestionarios ni las demás actividades obligatorias. La emisión del certificado depende de cumplir los requisitos configurados y la validación académica correspondiente.

    Consulta como apoyo las [pruebas de Django](https://docs.djangoproject.com/es/5.2/topics/testing/overview/) y las [herramientas MCP](https://modelcontextprotocol.io/docs/learn/server-concepts). La entrega demuestra aprendizaje introductorio; no certifica producción ni acredita Python, Django o proveedores de IA.
''')


MCP_AMPLIACIONES_WIKI = [
    _wiki('''
        ## Una sesión para ampliar cuando quieras

        **Recurso del autor:** «Curso MCPs - Primera sesión», Jhoni Cerón. Duración completa: **2 h 28 min 57 s**; el menú la redondea a 149 minutos.

        Esta sesión es **opcional y está fuera de las 40 horas obligatorias**. No necesitas verla completa para aprobar. Las lecturas y el kit mantienen la referencia de nuestra práctica y evaluación.

        ## Prepara tu observación

        Dibuja el recorrido del caso: asistente, cliente MCP, servidor y datos ficticios. Distingue dónde se consultan existencias y dónde se redacta una respuesta. Después selecciona un fragmento del video.

        | Durante la observación | Tu nota | Contraste con el curso |
        | --- | --- | --- |
        | Elige una explicación observada. | Minuto y descripción propia. | ¿Qué comprobarías en la fuente oficial? |
        | Identifica una relación con el prototipo. | Aplicación posible o diferencia. | ¿Cabe en nuestro alcance? |
        | Registra una duda o requisito. | Qué información falta. | ¿Qué consultarías antes de probar? |

        No completes por suposición aquello que no aparezca en el fragmento elegido. Estas preguntas orientan tu observación; no atribuyen al autor una demostración específica del inventario.

        ## Aplícalo sin ampliar el proyecto

        Formula una consulta sobre AD-001 y otra sobre productos bajo mínimo. Señala qué herramienta preparada usarías y cómo comprobarías los datos. Esta actividad es una adaptación del curso, no un resumen atribuido al video.

        > [!NOTE]
        > Conserva una nota personal con minuto, explicación, relación y duda. No es una entrega calificada ni requiere comprar servicios.

        Abre la [sesión original](https://www.youtube.com/watch?v=WNjQclnnIWA) y contrasta conceptos con la [documentación MCP](https://modelcontextprotocol.io/docs/learn/server-concepts).
    '''),
    _wiki('''
        ## Continúa la ampliación a tu ritmo

        **Recurso del autor:** «Curso MCPs Sesion 2», Jhoni Cerón. Duración completa: **1 h 20 min 59 s**; el menú la redondea a 81 minutos.

        Esta sesión es **opcional**, fuera de las 40 horas. No condiciona el quiz, el proyecto ni el certificado. Puedes elegir un fragmento y volver a la sesión completa cuando lo necesites.

        ## Observa y registra lo que realmente aparece

        Elige una idea, explicación o demostración observada. Anota su minuto y qué intenta resolver. Si no encuentras pasos reproducibles, escribe qué información faltaría; no inventes comandos, requisitos o resultados.

        | Casilla de tu ficha | Qué registrar |
        | --- | --- |
        | Necesidad | Qué problema relacionas con logística. |
        | Dato | Qué información necesitarías consultar. |
        | Herramienta | Qué función preparada existe o faltaría. |
        | Resultado | Qué evidencia permitiría comprobarlo. |

        La ficha adapta tu observación al caso del curso; no pretende resumir contenidos no verificados ni afirmar que el video muestre Andina Distribución.

        ## Contrasta con las herramientas del kit

        Consulta `consultar_existencias` o `productos_bajo_minimo` y compara código, saldo o lista con la aplicación. Si no hay modelo disponible, utiliza `verificar_mcp.py` como en el laboratorio y declara la modalidad.

        > [!WARNING]
        > Conserva el acceso de solo lectura. Las ideas que exijan escritura, otros sistemas o servicios de pago quedan como mejoras futuras; no son requisitos de esta ampliación.

        Guarda una nota personal con minuto, ficha y contraste. No tiene calificación adicional. Consulta la [sesión original](https://www.youtube.com/watch?v=TmB8mXKs9jI) y la [integración de OpenCode](https://opencode.ai/docs/mcp-servers/) cuando necesites aclarar la conexión preparada.
    '''),
]
