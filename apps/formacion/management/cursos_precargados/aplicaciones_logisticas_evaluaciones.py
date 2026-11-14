"""Evaluaciones originales del curso introductorio de aplicaciones logísticas con IA.

Formato compatible con estandar.evaluacion: tipo, enunciado, opciones y explicación.
Las respuestas correctas llevan * al inicio de la opción. Las situaciones utilizan
únicamente datos ficticios y comprueban decisiones, no la memorización de comandos.
"""

QUIZZES = [
    [
        (
            'unica',
            'Una distribuidora registra entradas en un cuaderno y salidas en varios archivos. '
            '¿Cuál sería una primera versión razonable para el proyecto de 40 horas?',
            '*Registrar productos, entradas y salidas, y consultar existencias.\n'
            'Desarrollar inventarios, nómina, facturación fiscal, transporte y compras a la vez.\n'
            'Crear primero una portada con gráficos y dejar los movimientos para después.',
            'Una primera versión debe resolver un proceso completo y comprobable. Limitar el alcance '
            'permite terminar el recorrido producto → movimiento → existencia sin construir un ERP completo.',
        ),
        (
            'unica',
            'Un estudiante propone «hacer una app moderna». ¿Qué información necesita añadir '
            'antes de pedir a la IA que la construya?',
            'El color exacto de todos los botones.\n'
            '*Quién la utilizará, qué problema resolverá, qué datos requiere y qué reglas cumplirá.\n'
            'Una lista extensa de tecnologías, aunque no conozca su utilidad.',
            'La necesidad operativa guía las pantallas y el código. Usuarios, datos, reglas y resultados '
            'permiten convertir una idea general en tareas verificables.',
        ),
        (
            'multiple',
            'Para registrar una salida de mercadería, ¿qué reglas pertenecen al funcionamiento de la aplicación?',
            '*La cantidad debe ser positiva.\n'
            '*El usuario debe tener permiso para registrar salidas.\n'
            '*La cantidad no debe superar la existencia disponible.\n'
            'El botón debe usar necesariamente una animación.',
            'Las tres reglas controlan la operación y los datos. Una animación puede mejorar la presentación, '
            'pero no determina si el movimiento es válido.',
        ),
        (
            'unica',
            'Una pantalla muestra 25 unidades, pero el servidor guarda 18. ¿Qué parte debe resolver '
            'el cálculo y la validación antes de registrar una salida?',
            'La imagen del tablero.\n'
            'La respuesta escrita del asistente de IA.\n'
            '*La lógica de la aplicación en el servidor, consultando los datos vigentes.',
            'La pantalla muestra información y recoge solicitudes; el servidor valida contra los datos vigentes. '
            'Una cifra visible o una respuesta de IA no sustituye el registro del sistema.',
        ),
        (
            'unica',
            '¿Cuál describe mejor la relación entre pantalla, servidor y base de datos?',
            '*La pantalla recibe la solicitud, el servidor aplica las reglas y la base conserva los registros.\n'
            'La base de datos decide por sí sola qué colores y botones utilizar.\n'
            'El asistente de IA debe permanecer conectado para guardar cada formulario.',
            'Estas partes colaboran: interfaz para interactuar, servidor para procesar y base para conservar '
            'información. Una aplicación puede funcionar sin consultar una IA en cada operación.',
        ),
        (
            'unica',
            'La empresa guarda «5 cajas» en un archivo y «5 unidades» en otro. ¿Qué debe aclararse en el diseño?',
            'Que ambos valores significan lo mismo porque el número coincide.\n'
            '*La unidad de medida y, si corresponde, la equivalencia entre cajas y unidades.\n'
            'Que el asistente elija una unidad distinta en cada consulta.',
            'Un número necesita contexto. Definir las unidades evita sumar cantidades incompatibles; las '
            'conversiones requieren una equivalencia explícita y comprobada.',
        ),
        (
            'multiple',
            '¿Qué evidencias ayudarían a comprobar que el diseño responde al problema logístico?',
            '*Un recorrido dibujado desde la recepción hasta la consulta de existencias.\n'
            '*Ejemplos de operaciones aceptadas y rechazadas.\n'
            '*Una lista breve de funciones incluidas y funciones que quedan fuera.\n'
            'Únicamente una captura de una portada atractiva.',
            'El recorrido muestra cómo se usa la aplicación; los ejemplos precisan las reglas y el alcance '
            'evita añadir funciones sin terminar las esenciales. La portada no demuestra la operación.',
        ),
        (
            'unica',
            'Para el curso, ¿qué significa entregar un prototipo funcional?',
            'Garantizar que puede operar cualquier empresa sin revisión adicional.\n'
            'Entregar solamente las instrucciones que se dieron a la IA.\n'
            '*Demostrar un proceso acotado con datos de prueba, reglas verificadas y limitaciones documentadas.',
            'Un prototipo demuestra aprendizaje y funcionamiento dentro de un alcance. Operar en producción '
            'requiere revisiones y condiciones adicionales que el curso introductorio no certifica.',
        ),
    ],
    [
        (
            'unica',
            'En el curso se mencionan un modelo de Django y un modelo de IA. ¿Cuál es la diferencia?',
            '*El modelo de Django describe datos de la aplicación; el modelo de IA genera respuestas a partir de entradas.\n'
            'Son dos nombres para una misma tabla de productos.\n'
            'El modelo de IA reemplaza automáticamente todas las validaciones de Django.',
            'La palabra modelo cambia de significado según el contexto. Definir productos y movimientos '
            'en Django no equivale a utilizar un modelo que interpreta instrucciones y genera contenido.',
        ),
        (
            'unica',
            'El asistente propone una función que no existe en la versión instalada. ¿Cómo conviene continuar?',
            'Copiarla y ocultar el error de la pantalla.\n'
            '*Compartir el mensaje de error sin secretos, comprobar la documentación y probar una corrección pequeña.\n'
            'Reemplazar todo el proyecto antes de entender el problema.',
            'La IA puede sugerir funciones incorrectas o de otra versión. El error, la documentación y una '
            'prueba pequeña permiten corregir la causa y conservar el trabajo que sí funciona.',
        ),
        (
            'multiple',
            '¿Qué incluye una instrucción útil para desarrollar el catálogo de productos con IA?',
            '*Los campos que debe guardar cada producto.\n'
            '*Las reglas, como código único y mínimo no negativo.\n'
            '*Un ejemplo que permita comprobar el resultado.\n'
            'La contraseña de acceso a una base de datos institucional real.',
            'Los campos, las reglas y un ejemplo reducen ambigüedades. Las contraseñas no ayudan a explicar '
            'el problema y no deben compartirse con el asistente ni incluirse en el material del curso.',
        ),
        (
            'unica',
            '¿Qué criterio permite participar sin una suscripción costosa de IA?',
            'Exigir que todas las personas contraten el mismo plan premium.\n'
            '*Utilizar una alternativa gratuita o institucional comprobada para las prácticas y permitir opciones de pago.\n'
            'Suponer que cualquier modelo gratuito tiene capacidad y disponibilidad ilimitadas.',
            'El recorrido debe comprobarse con la alternativa de acceso prevista. La disponibilidad y los límites '
            'pueden variar; pagar una herramienta no debe cambiar las competencias ni la calificación.',
        ),
        (
            'unica',
            'La IA incluye una clave de acceso directamente en un archivo Python. ¿Qué decisión corresponde?',
            'Mantenerla allí porque el archivo aún no se publicó.\n'
            '*Retirarla del código, usar la configuración de entorno y reemplazarla si llegó a exponerse.\n'
            'Cambiar solamente el nombre de la variable para que sea difícil de reconocer.',
            'Cambiar el nombre no protege una clave. Separar secretos del código reduce su exposición; una clave '
            'compartida o publicada debe tratarse como expuesta aunque se elimine después.',
        ),
        (
            'unica',
            'Antes de pedir a la IA que modifique varias pantallas que ya funcionan, ¿qué paso facilita recuperar el trabajo?',
            '*Guardar una versión identificable y hacer cambios en tareas pequeñas.\n'
            'Borrar las versiones anteriores para ahorrar espacio.\n'
            'Aceptar todas las modificaciones y comprobar únicamente la última pantalla.',
            'Un punto de recuperación y cambios pequeños permiten comparar, probar y revertir. Guardar versiones '
            'no sustituye las pruebas, pero reduce el costo de corregir una modificación equivocada.',
        ),
        (
            'multiple',
            'Una persona nunca ha programado. ¿Qué acciones demuestran que está aprendiendo durante la práctica guiada?',
            '*Explicar con sus palabras qué datos guarda un formulario.\n'
            '*Pedir a la IA que aclare un cambio antes de aceptarlo.\n'
            '*Ejecutar un caso de prueba y comparar el resultado esperado.\n'
            'Aceptar cualquier código mientras la pantalla tenga buen aspecto.',
            'El curso busca comprender, dirigir y comprobar el desarrollo. No exige memorizar comandos, pero sí '
            'reconocer qué hace la aplicación y revisar los resultados que produce.',
        ),
        (
            'unica',
            'La aplicación abre en la dirección local del computador. ¿Qué significa esto?',
            'Que cualquier usuario de internet puede entrar de inmediato.\n'
            'Que ya dispone de HTTPS, copias de seguridad y operación institucional.\n'
            '*Que está ejecutándose en el entorno local; publicarla para otras personas es un paso adicional.',
            'Ejecutar en local permite practicar y probar. No demuestra que el sistema esté desplegado ni que '
            'cumpla las condiciones necesarias para una operación pública.',
        ),
    ],
    [
        (
            'unica',
            'Un producto inicia con 12 unidades. Se registra una entrada de 8 y una salida de 5. '
            'Sin otros movimientos, ¿qué existencia debe mostrar?',
            '25 unidades.\n'
            '*15 unidades.\n'
            '7 unidades.',
            'La existencia es 12 + 8 − 5 = 15. Esta cuenta sencilla sirve como resultado esperado para probar '
            'el sistema independientemente de la explicación que entregue la IA.',
        ),
        (
            'unica',
            'Hay 7 unidades y alguien solicita una salida de 9. ¿Qué debería hacer la aplicación del curso?',
            'Guardar −2 y esperar a que una entrada futura lo compense.\n'
            'Reducir automáticamente la salida a 7 sin informar al usuario.\n'
            '*Rechazar la operación sin cambiar el inventario y explicar que no hay disponibilidad suficiente.',
            'El caso del curso no admite stock negativo. Rechazar sin modificar datos conserva la consistencia '
            'y permite que el usuario corrija la solicitud de manera explícita.',
        ),
        (
            'multiple',
            '¿Qué controles deben aplicarse en el servidor al recibir un movimiento?',
            '*Comprobar que el producto existe y puede utilizarse.\n'
            '*Comprobar cantidad positiva y formato numérico válido.\n'
            '*Comprobar permisos y disponibilidad cuando sea una salida.\n'
            'Confiar solo en que el botón de la pantalla esté desactivado.',
            'Las solicitudes pueden enviarse fuera de la interfaz prevista. El servidor debe validar identidad, '
            'datos y reglas antes de guardar; los controles visuales ayudan al uso, pero no bastan.',
        ),
        (
            'unica',
            'El laboratorio necesita registrar cantidades fraccionarias y valores monetarios con precisión definida. '
            '¿Qué enfoque es más adecuado?',
            'Guardar todas las cantidades como texto y compararlas alfabéticamente.\n'
            '*Utilizar campos decimales con precisión, unidades y reglas de redondeo explícitas.\n'
            'Redondear todos los valores al entero más cercano sin avisar.',
            'Los decimales permiten representar cantidades con precisión definida. También hay que fijar '
            'unidades y reglas de redondeo; el tipo de dato por sí solo no define la regla del negocio.',
        ),
        (
            'unica',
            'Un usuario de consulta no ve el botón de registrar salidas, pero intenta acceder directamente '
            'a la dirección de esa operación. ¿Qué debe ocurrir?',
            '*El servidor debe impedir el registro por falta de permiso.\n'
            'La operación debe aceptarse porque conoce la dirección.\n'
            'La aplicación debe darle permisos de administrador para evitar errores.',
            'Ocultar un botón mejora la interfaz, pero no controla el acceso. La operación debe verificar '
            'el permiso del usuario en el servidor, incluso si recibe una solicitud directa.',
        ),
        (
            'unica',
            'Se registró una salida equivocada que ya aparece en el historial. ¿Cómo conviene diseñar su corrección?',
            'Eliminar el movimiento y cambiar la existencia manualmente sin dejar constancia.\n'
            '*Aplicar una corrección autorizada y trazable, conservando la referencia y el motivo.\n'
            'Pedir a la IA que reescriba el historial para que parezca que no ocurrió.',
            'La trazabilidad permite reconstruir lo sucedido. El mecanismo concreto puede variar, pero debe '
            'identificar quién corrigió, por qué y cómo afectó a las existencias.',
        ),
        (
            'multiple',
            '¿Qué casos conviene probar antes de dar por terminado el formulario de salidas?',
            '*Salida válida que deja la existencia en cero.\n'
            '*Cantidad cero, negativa o no numérica.\n'
            '*Salida superior al stock disponible.\n'
            'Solo una salida válida realizada por el administrador.',
            'Las pruebas deben cubrir límites y solicitudes incorrectas además del caso exitoso. Probar únicamente '
            'con un administrador no detecta errores de validación ni de acceso.',
        ),
        (
            'unica',
            'Dos personas consultan 10 unidades y cada una intenta retirar 8 casi al mismo tiempo. '
            '¿Qué resultado debe garantizar la aplicación?',
            'Aceptar ambas solicitudes porque ambas pantallas mostraban 10.\n'
            '*Impedir que el conjunto de salidas supere las existencias, verificando y guardando de forma consistente.\n'
            'Elegir al azar qué existencia mostrar al terminar.',
            'La pantalla puede quedar desactualizada entre consulta y registro. La validación y la actualización '
            'deben proteger la operación completa para que las solicitudes simultáneas no produzcan stock negativo.',
        ),
    ],
    [
        (
            'unica',
            'Un CSV tiene dos filas con el mismo código de producto y descripciones distintas. '
            '¿Qué decisión corresponde antes de importarlo?',
            'Crear dos productos con el mismo código para conservar ambas filas.\n'
            '*Detectar el conflicto, informar las filas y aplicar una regla explícita de corrección o rechazo.\n'
            'Pedir a la IA que elija una descripción sin dejar evidencia.',
            'Un código único identifica un producto. La importación necesita validar duplicados y comunicar '
            'su política; resolverlos silenciosamente puede cambiar información sin que el usuario lo advierta.',
        ),
        (
            'multiple',
            '¿Qué aspectos deben comprobarse al importar datos desde Excel o CSV?',
            '*Encabezados y campos obligatorios.\n'
            '*Formato decimal y unidad de medida.\n'
            '*Códigos duplicados y valores fuera de las reglas.\n'
            'Solo que el archivo abra en una hoja de cálculo.',
            'Abrir el archivo no garantiza que los registros sean válidos. Los tipos, las unidades, los campos '
            'y la unicidad deben comprobarse antes de incorporarlos al sistema.',
        ),
        (
            'unica',
            'El indicador define «bajo mínimo» como existencia estrictamente menor al mínimo. '
            'A tiene stock 4 y mínimo 5; B tiene 5 y mínimo 5; C tiene 0 y mínimo 2. ¿Cuántos productos cuenta?',
            'Uno.\n'
            '*Dos.\n'
            'Tres.',
            'A y C cumplen stock < mínimo. B es igual al mínimo y queda fuera con esta definición. '
            'La condición debe estar escrita y coincidir en el reporte, el código y las pruebas.',
        ),
        (
            'unica',
            '¿Qué aporta MCP en la práctica del curso?',
            'Es el modelo que calcula probabilísticamente todas las respuestas.\n'
            '*Define una forma de conectar el asistente con herramientas y datos expuestos por una aplicación.\n'
            'Permite acceder a cualquier aplicación aunque no tenga integración ni permisos.',
            'MCP es un protocolo de integración, no el modelo de IA. La aplicación o su conector debe exponer '
            'herramientas concretas y controlar su acceso; el protocolo no elimina estos requisitos.',
        ),
        (
            'unica',
            'El asistente tiene únicamente herramientas MCP de consulta. El usuario pide «registra una salida '
            'de 20 unidades». ¿Cuál es la respuesta adecuada?',
            'Inventar una confirmación para que la experiencia resulte fluida.\n'
            '*Explicar que no dispone de esa operación y remitir al flujo autorizado de la aplicación.\n'
            'Cambiar directamente la base de datos para cumplir la solicitud.',
            'La conexión de esta unidad es de solo lectura. El asistente debe respetar las herramientas y '
            'permisos disponibles, y nunca afirmar que ejecutó una acción que no realizó.',
        ),
        (
            'unica',
            'La IA informa que hay 40 unidades, pero la herramienta devuelve 14. ¿Qué debe revisarse?',
            'Cambiar la base a 40 para que coincida con la respuesta.\n'
            '*Comparar la respuesta con los datos y filtros de la herramienta, y corregir la interpretación.\n'
            'Aceptar 40 porque una respuesta conversacional es más clara que una tabla.',
            'La claridad de una respuesta no prueba su exactitud. Hay que revisar filtros, unidades, fecha '
            'y resultados de la herramienta; las existencias se obtienen del sistema, no se adivinan.',
        ),
        (
            'unica',
            'Por un reintento, una consulta MCP devuelve el mismo movimiento dos veces. '
            '¿Cómo debe prepararse un reporte de movimientos únicos?',
            'Sumar ambas filas porque aparecieron en dos respuestas.\n'
            '*Identificar los movimientos por su identificador estable y evitar contar dos veces el mismo registro.\n'
            'Eliminar movimientos con igual cantidad aunque tengan identificadores distintos.',
            'Una repetición de transporte no representa una segunda operación. El identificador permite '
            'distinguir duplicados reales; dos movimientos diferentes pueden compartir producto y cantidad.',
        ),
        (
            'multiple',
            '¿Qué información ayuda a interpretar correctamente un indicador o reporte?',
            '*El período y los filtros utilizados.\n'
            '*La fórmula o criterio de cálculo.\n'
            '*Las unidades y la fecha de consulta.\n'
            'Una afirmación de la IA de que el dato es correcto, sin poder comprobarlo.',
            'El contexto del indicador permite reproducirlo y compararlo. Un reporte sin período, unidad '
            'o criterio puede llevar a conclusiones equivocadas aunque su gráfico esté bien presentado.',
        ),
    ],
    [
        (
            'unica',
            'En la demostración final, un producto tiene 10 unidades; se reciben 6 y salen 4. '
            '¿Qué evidencia comprueba mejor el recorrido completo?',
            'Una captura de la portada y la afirmación de que todo funciona.\n'
            '*Los dos movimientos registrados, existencia final 12 y una prueba que rechaza una salida superior al saldo.\n'
            'La conversación donde la IA prometió implementar el recorrido.',
            'El resultado esperado es 10 + 6 − 4 = 12. El historial y la prueba negativa comprueban '
            'funcionamiento y reglas; una promesa de implementación no demuestra que el código funcione.',
        ),
        (
            'multiple',
            '¿Qué evidencias deberían incluirse al entregar el prototipo?',
            '*Archivos del proyecto y pasos para ejecutarlo.\n'
            '*Datos ficticios y resultados de pruebas.\n'
            '*Una guía de uso y limitaciones conocidas.\n'
            'Claves personales o datos reales de clientes para que la demostración parezca más auténtica.',
            'La entrega debe permitir reproducir y comprender el trabajo. Los datos ficticios son suficientes '
            'para evaluar; no deben incluirse secretos ni información personal innecesaria.',
        ),
        (
            'unica',
            'La aplicación obtiene 82 puntos en la rúbrica, pero permite stock negativo. '
            '¿Qué corresponde según el criterio del proyecto?',
            'Aprobar porque el promedio supera 70.\n'
            '*Corregir el fallo de integridad y volver a demostrar las pruebas antes de aprobar el proyecto.\n'
            'Quitar la prueba fallida del informe para conservar la nota.',
            'Además de alcanzar 70 puntos, el proyecto exige corregir fallos críticos de stock y permisos. '
            'La suma de puntos no compensa una regla esencial que sigue fallando.',
        ),
        (
            'unica',
            'Un usuario de consulta intenta registrar un movimiento mediante una solicitud directa. '
            '¿Qué resultado demuestra un control de acceso correcto?',
            '*El servidor rechaza la operación y no cambia ni el saldo ni el historial.\n'
            'El botón está oculto, pero la solicitud crea el movimiento.\n'
            'El sistema registra el movimiento y después muestra un aviso de falta de permiso.',
            'La autorización debe comprobarse antes de modificar datos. El rechazo debe dejar intacto '
            'el inventario y funciona aunque se intente evitar la pantalla normal.',
        ),
        (
            'unica',
            'Durante la presentación, el estudiante afirma «la IA construyó todo». '
            '¿Qué evidencia demuestra mejor su aprendizaje?',
            'La cantidad total de mensajes enviados al asistente.\n'
            '*Explicar una regla, mostrar el cambio que pidió y comprobar su resultado con una prueba.\n'
            'La marca o el precio del asistente utilizado.',
            'Aprender con IA implica dirigir y revisar el trabajo. Una instrucción, un cambio y su '
            'comprobación muestran criterio; el número de mensajes o el plan contratado no lo demuestran.',
        ),
        (
            'unica',
            'El prototipo funciona en el equipo del estudiante. Una empresa quiere usarlo mañana '
            'con información real. ¿Qué conclusión es adecuada?',
            'La aprobación del curso equivale a una autorización para operar en producción.\n'
            'Basta con compartir la dirección local del equipo.\n'
            '*Hace falta una revisión adicional de seguridad, despliegue, respaldo y operación antes de utilizarlo en producción.',
            'El proyecto acredita un aprendizaje introductorio dentro de un alcance de prueba. '
            'No reemplaza la preparación técnica y operativa de un servicio de producción.',
        ),
        (
            'multiple',
            'La aplicación importa datos, muestra un KPI y responde consultas MCP. '
            '¿Qué comprobaciones finales son necesarias?',
            '*Que la importación identifique duplicados y cantidades inválidas.\n'
            '*Que el KPI coincida con un cálculo manual conocido.\n'
            '*Que la respuesta del asistente coincida con la herramienta y respete el acceso de solo lectura.\n'
            'Que todos los resultados se acepten si la IA los explica con seguridad.',
            'La integración no elimina la necesidad de comprobar cada componente. Datos válidos, '
            'cálculos reproducibles y herramientas limitadas permiten evaluar el proceso completo.',
        ),
        (
            'unica',
            '¿Qué demuestra la aprobación del curso y sus actividades?',
            '*Que el participante cumplió los criterios de aprendizaje y evaluación definidos para el curso introductorio.\n'
            'Que cualquier aplicación futura del participante es segura y está lista para producción.\n'
            'Que se autoriza el uso de marcas o certificaciones técnicas de proveedores de IA.',
            'La aprobación se refiere a los objetivos y evidencias evaluados en este curso. '
            'No implica acreditaciones de terceros ni valida automáticamente otros desarrollos.',
        ),
    ],
]

RUBRICA_PROYECTO = """PROYECTO FINAL: UNA APLICACIÓN LOGÍSTICA CON DATOS COMPROBABLES

Propósito
Demuestra cómo convertir una necesidad logística en un prototipo educativo con ayuda de IA.
El caso común es un control de productos, entradas, salidas y existencias. Puedes adaptar los
nombres y el contexto a un almacén comercial, agroindustria, transporte o abastecimiento,
conservando las funciones y pruebas evaluadas. Utiliza únicamente información ficticia.
No hace falta incorporar facturación, rutas optimizadas, compras completas ni un ERP.

Alcance mínimo
• Catálogo de productos con código único, descripción, unidad y stock mínimo.
• Registro de entradas y salidas con cantidad, fecha o marca temporal y motivo o referencia.
• Consulta de existencias y un historial que permita reconstruir los movimientos.
• Búsqueda o filtros útiles para encontrar productos y movimientos.
• Importación o carga controlada de datos de práctica y exportación de una consulta.
• Indicador de productos bajo el mínimo con su criterio escrito y comprobado.
• Consulta de solo lectura mediante el conector MCP preparado durante el curso.
• Acceso diferenciado entre quien consulta y quien registra operaciones.
Trabaja sobre la plantilla del curso; no se exige desarrollar cada componente desde cero.

Entregables
1. Proyecto comprimido o repositorio accesible al evaluador, sin claves ni archivos de entorno
   con secretos, sin entornos virtuales ni datos personales. Incluye instrucciones de ejecución
   y las dependencias necesarias para reproducir la versión entregada.
2. Ficha de una página: problema, usuario, funciones incluidas, reglas, herramientas utilizadas
   y limitaciones. Identifica el asistente empleado, sin valorar más una opción por ser de pago.
3. Datos ficticios de prueba y tabla de resultados esperados/obtenidos. Incluye el cálculo
   manual de al menos un saldo y un indicador para que puedan compararse con la aplicación.
4. Registro breve de tres intervenciones de IA: necesidad, instrucción, cambio propuesto,
   decisión del estudiante y prueba realizada. Resume la evidencia; no entregues conversaciones
   completas con información innecesaria ni secretos.
5. Guía breve de uso y demostración de 5 a 8 minutos, en directo o grabada según indique
   el docente. Muestra un recorrido completo y explica al menos una decisión y una corrección.

Rúbrica: 100 puntos

A. Funciones y recorrido operativo — 30 puntos
• 10: crea y consulta productos con los campos requeridos y búsqueda o filtros útiles.
• 10: registra una entrada y una salida válidas y calcula la existencia esperada.
• 10: conserva un historial comprensible y permite demostrar el recorrido completo.
Para cada criterio se asigna el total si funciona y se demuestra; aproximadamente la mitad
si está parcialmente implementado con evidencia; cero si no existe o no puede comprobarse.

B. Datos y validaciones — 25 puntos
• 5: códigos únicos y campos obligatorios comprobados en el servidor.
• 5: cantidades positivas, formato decimal y unidades coherentes.
• 10: una salida superior a la disponibilidad se rechaza sin modificar saldo ni historial.
• 5: una importación o carga detecta duplicados y datos inválidos, comunica los errores y
  explica si acepta filas válidas o rechaza el lote completo. No cambia datos silenciosamente.
Se conceden puntos por funcionamiento comprobado, no por mostrar mensajes de validación
que puedan evitarse enviando una solicitud directa.

C. Consultas, reportes e integración — 15 puntos
• 5: indicador bajo mínimo y consulta de movimientos coinciden con los datos y filtros.
• 5: exportación utilizable, con encabezados y unidades comprensibles.
• 5: consulta MCP reproducible que respeta el acceso de solo lectura y cuya respuesta
  coincide con la herramienta. Se demuestra con el conector preparado, sin exigir crear
  un servidor MCP completo ni contratar una API de pago. Si el modelo no está disponible,
  se acepta el cliente de prueba de protocolo del kit con sus resultados, rotulados como
  prueba sin conversación. Se evalúan conexión, datos y límites con los mismos criterios.

D. Uso de IA explicado y trazable — 10 puntos
• 5: documenta tres instrucciones, cambios y decisiones del estudiante.
• 5: explica qué comprobó, qué corrigió y qué limitación conserva el resultado generado.
La cantidad de código generado o el precio de la herramienta no otorgan puntos adicionales.

E. Pruebas y permisos — 10 puntos
• 5: presenta resultados esperados y obtenidos de casos válidos, inválidos y de límite.
• 5: demuestra que el usuario de consulta no puede modificar datos, incluso mediante
  solicitud directa, y que el rechazo no produce cambios en la base de datos.
La evaluación puede usar las pruebas guiadas de la plantilla y una demostración manual
registrada; no exige diseñar una infraestructura avanzada de pruebas.

F. Guía y demostración — 10 puntos
• 5: otra persona puede seguir la guía para ejecutar y utilizar el prototipo de práctica.
• 5: demuestra el recorrido, interpreta los resultados y comunica las limitaciones.
No se requiere una grabación con producción audiovisual profesional.

Pruebas mínimas para la demostración
• Crear un producto y comprobar el rechazo de un código duplicado.
• Partir de 10 unidades, recibir 6 y retirar 4: el saldo esperado es 12.
• Intentar retirar 13 sobre ese saldo: la operación se rechaza y el saldo sigue en 12.
• Probar cantidad cero, negativa y un campo numérico con texto.
• Intentar registrar una operación con el usuario de consulta: debe rechazarse sin cambios.
• Comparar el KPI bajo mínimo con una tabla calculada manualmente.
• Mostrar una consulta MCP y contrastar su respuesta con los registros de la aplicación.
• Identificar y explicar un caso duplicado o inválido en el archivo de importación.

Aprobación y correcciones
La nota mínima del proyecto es 70/100. Además, deben corregirse los fallos críticos que
permitan stock negativo o modificaciones sin permiso antes de aprobar el proyecto, aunque
el total inicial supere 70. El docente registra la nota que corresponde a la entrega validada
y utiliza la devolución del deber para solicitar correcciones; el aula almacena la nota,
no detecta automáticamente esos fallos del prototipo.

La aprobación del proyecto no sustituye las otras actividades y evaluaciones requeridas por
el curso. La emisión de un certificado depende de los requisitos configurados en el aula y
de la validación académica que corresponda. Este prototipo no es una certificación de
producción ni una acreditación de Python, Django, MCP o de proveedores de inteligencia artificial.
"""
