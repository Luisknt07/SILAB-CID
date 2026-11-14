"""Lecturas wiki y laboratorios del curso introductorio de aplicaciones logísticas.

Contenido docente original en español; referencias externas enlazadas, no republicadas.
Las actividades desarrollan el mismo caso y mantienen la carga de 40 horas del aula.
"""
from textwrap import dedent


def _wiki(contenido):
    return "[AULA_WIKI]\n" + dedent(contenido).strip()


LECTURAS_WIKI = {
    'El curso y el caso Andina Distribución': _wiki(r'''
## Empieza aquí: qué vas a aprender

Este curso te acompaña desde una necesidad del almacén hasta una aplicación que puedes ejecutar, explicar y mejorar. No necesitas haber programado. Trabajarás con una base preparada, conocerás sus componentes y realizarás cambios pequeños con ayuda de Inteligencia Artificial. Tu tarea será decidir qué necesita el usuario, observar lo que cambia y comprobar los resultados. Una respuesta convincente de la IA no sustituye esa comprobación.

El producto del curso es un prototipo educativo local. Local significa que funciona en tu computador; no hace falta publicar una página en internet para demostrar lo aprendido. Usaremos el mismo caso durante las cinco unidades para que puedas concentrarte en comprender el proceso, en lugar de volver a empezar con herramientas distintas.

![Ruta de las cinco unidades del curso](/static/portal/img/cursos/logistica-ia/ruta-curso.svg)

## Conoce el caso Andina Distribución

Andina Distribución es una organización ficticia que administra materiales de empaque. Recibe cajas, etiquetas, film y cinta. Cuando registra entradas y salidas en archivos separados, puede repetir códigos o consultar un saldo desactualizado. Necesita un lugar común para registrar productos, comprobar disponibilidad y conservar el historial de lo ocurrido.

No trabajaremos con información de empresas reales. Los nombres, cuentas, cantidades y operaciones del kit se prepararon para aprender. Esto permite repetir una práctica, provocar un error y volver a empezar sin afectar un almacén. Si reconoces una situación de tu trabajo, descríbela con ejemplos inventados y conserva únicamente las reglas que necesitas analizar.

| Necesidad del almacén | Función del prototipo | Evidencia que buscarás |
|---|---|---|
| Reconocer cada material | Catálogo con código único | Un código identifica un producto |
| Saber cuánto hay | Consulta de existencias | Saldo calculado y unidad visibles |
| Registrar lo recibido o entregado | Entradas y salidas | Movimiento y saldo coinciden |
| Explicar una diferencia | Historial de movimientos | Producto, cantidad, usuario y motivo |
| Detectar una condición de revisión | Indicador bajo mínimo | Existencia menor que el mínimo |

## Cómo recorrer las cinco unidades

Cada unidad ocupa ocho horas. Las horas incluyen las lecturas, videos seleccionados, consultas, práctica, elaboración de evidencias y evaluación. No son cuarenta horas de video. Las ampliaciones opcionales se identifican por separado y no son necesarias para aprobar. Esta wiki amplía las explicaciones de las actividades existentes: no añade una segunda lista de tareas.

1. En la primera unidad explicarás el problema y dibujarás la solución.
2. En la segunda ejecutarás el kit y reconocerás sus archivos.
3. En la tercera registrarás movimientos y comprobarás sus reglas.
4. En la cuarta importarás datos, interpretarás indicadores y probarás una consulta MCP.
5. En la quinta reunirás pruebas y presentarás tu mejora.

Antes de completar una lectura, utiliza su punto de control. Antes de entregar un laboratorio, revisa sus resultados esperados. La misma ficha de proyecto, bitácora y tabla de pruebas crecerá durante el curso; no necesitas redactar cinco documentos independientes que repitan el mismo contenido.

## Qué necesitas y cómo usar el kit

Descarga el ZIP del aula y extráelo en una carpeta propia. Busca `README.md`: contiene los comandos de Windows y Linux. La aplicación base usa Python y Django; la práctica se ha comprobado con Python 3.11. El asistente de IA puede ser gratuito, de pago o facilitado por el laboratorio. No se exige una suscripción de USD 200.

> [!NOTE]
> OpenCode es una herramienta que conecta modelos. Sus modelos gratuitos pueden cambiar, tener límites o aplicar condiciones particulares. La aplicación del kit funciona sin IA; conversar con un asistente sí necesita un modelo disponible.

Si se agota una cuota, continúa leyendo los archivos y ejecutando la plantilla. Anota la limitación y utiliza la alternativa guiada acordada para la actividad. La evaluación se centra en tu explicación y tus comprobaciones, no en la marca del asistente. No inventes capturas de una conversación que no ocurrió.

## Una primera versión con límites claros

Administraremos una existencia por producto. Cada producto tiene una unidad definida: UN, KG o LT. No convertiremos cajas en unidades ni mezclaremos unidades diferentes. El kit no incluye facturación, rutas óptimas, lotes, varias bodegas ni valoración contable. Puedes proponer esas funciones como evolución posterior, explicando qué datos nuevos requerirían.

La plantilla ya contiene funciones que trabajan. Debes reconocer ese material inicial y describir tus aportaciones. Cambiar una ayuda de pantalla, mejorar un mensaje o explicar una validación son pasos útiles cuando puedes demostrar su efecto. Pedir una aplicación completa sin entenderla dificulta saber si realmente resuelve el problema.

## Mini práctica: sitúa tu proyecto

Abre `plantillas/ficha_proyecto.md`. Completa el problema en dos frases y escribe quién usará la aplicación. Elige una operación que hayas realizado: por ejemplo, recibir diez cajas. Describe qué debería verse después y qué evidencia conservarías. Todavía no instales nada; este paso forma parte del diseño del laboratorio 1.

| Si ocurre esto | Haz esto |
|---|---|
| Quieres añadir muchas funciones | Separa indispensables y mejoras futuras |
| No entiendes un concepto | Pide una explicación con el mismo material de empaque |
| La IA produce demasiado código | Solicita un plan y una sola modificación |
| Una pantalla muestra un resultado | Compáralo con el cálculo y el historial |

### Glosario breve

- **Prototipo:** versión limitada para aprender y comprobar una idea.
- **Existencia:** cantidad disponible de un producto.
- **Movimiento:** hecho registrado que aumenta o disminuye esa cantidad.
- **Evidencia:** resultado observable que permite comprobar una afirmación.

## Punto de control y aprobación

Puedes continuar cuando expliques el problema, nombres tres funciones y distingas existencia de movimiento. Conserva la ficha para el laboratorio. Cada quiz requiere 70 % y permite tres intentos; las entregas y el proyecto requieren revisión y al menos 70/100. Completar lecturas no equivale por sí solo a aprobar. El certificado depende de todos los requisitos del aula y de la validación académica correspondiente.

## Fuentes para consultar

- [Django Girls en español](https://tutorial.djangogirls.org/es/): introducción accesible a las aplicaciones web.
- [OpenCode: primeros pasos](https://opencode.ai/docs/): herramienta, proveedores y flujo de trabajo.
- [OpenCode: modelos y condiciones](https://opencode.ai/docs/zen/): revisa disponibilidad antes de una práctica.
'''),
    'Del proceso logístico a las reglas de la aplicación': _wiki(r'''
## Primero describe qué ocurre en el almacén

Antes de pedir código, observa una operación de principio a fin. Imagina que llegan diez cajas: alguien identifica el material, verifica la cantidad, explica el motivo de recepción y registra la entrada. Otra persona necesita saber si podrá entregar tres cajas. La aplicación debe conectar esas tareas sin perder la información que permite explicar el saldo.

Describe hechos concretos. «El sistema debe ser moderno» expresa una preferencia; «al recibir diez y entregar tres debe mostrar siete» expresa un comportamiento que podemos probar. Ambos pueden interesarte, pero las reglas comprobables permiten construir y evaluar una primera versión. En esta lectura prepararás esas reglas para el laboratorio 1.

![Recorrido de productos, movimientos y existencias](/static/portal/img/cursos/logistica-ia/flujo-inventario.svg)

## Separa datos, acciones, reglas e indicadores

Un dato describe algo. Una acción hace que ocurra una operación. Una regla establece cuándo esa operación se admite. Un indicador resume registros para ayudar a interpretar una situación. Si mezclas estos conceptos, puedes pedir a la IA una pantalla que parece completa pero carece de controles.

| Concepto | Ejemplo del caso | Pregunta que responde |
|---|---|---|
| Dato | Código PRUEBA-001 | ¿Qué producto es? |
| Acción | Registrar una salida de 3 UN | ¿Qué quiere hacer la persona? |
| Regla | No retirar más de lo disponible | ¿Cuándo se permite? |
| Indicador | Cantidad de productos bajo mínimo | ¿Qué condición conviene revisar? |

La alerta bajo mínimo no es una orden automática de compra. Para decidir cuánto comprar faltarían demanda, plazo de entrega, presupuesto y política de reposición. El prototipo solo compara existencia y mínimo; no inventa información que no tiene.

## Escribe una historia y sus criterios

Una historia de usuario explica necesidad y propósito: «Como operador del almacén, quiero registrar una salida para mantener actualizada la disponibilidad». Acompáñala con criterios de aceptación: situaciones que dos personas pueden repetir y evaluar de la misma manera.

1. Dado un producto con 10 UN, al registrar una salida de 3 UN quedan 7 UN.
2. Dado ese saldo de 7 UN, al intentar una salida de 8 UN aparece un rechazo.
3. Tras el rechazo siguen 7 UN y no se añade otro movimiento.
4. Si el usuario solo tiene permiso de consulta, no puede registrar la salida.

Escribe el resultado esperado antes de ejecutar. No cambies el criterio para que coincida con un resultado incorrecto. Si deseas una regla diferente, justifica el cambio y revisa las actividades que dependen de ella.

## Sigue el recorrido de la información

La pantalla recibe producto, tipo, cantidad y motivo. El servidor comprueba la identidad del usuario y sus permisos. El formulario interpreta los campos; el servicio aplica las reglas del movimiento; la base de datos conserva el cambio. La pantalla muestra la respuesta y permite consultar el saldo y el historial.

Una página puede mostrar «operación realizada» sin que el dato se haya guardado correctamente. Por eso comprobarás tres cosas: mensaje, saldo e historial. También puede ocultarse un botón y conservar una dirección accesible: los permisos deben comprobarse en el servidor, no depender solo del diseño visual.

> [!TIP]
> Dibuja el recorrido con cinco cajas: persona, pantalla, comprobación, datos y respuesta. Marca dónde cambia el saldo y dónde se conserva la evidencia. No necesitas aprender símbolos técnicos para hacer este dibujo.

## Diseña los datos que realmente existen

El producto del kit tiene `codigo`, `nombre`, `unidad`, `minimo` y `existencia`. El formulario de alta solicita los cuatro primeros; la existencia empieza en cero y cambia mediante movimientos. No añadas una casilla de saldo inicial suponiendo que la aplicación ya la utiliza.

Un movimiento relaciona producto, tipo, cantidad, motivo, usuario y fecha. El sistema añade fecha y usuario al registrar; no hace falta pedir que el alumno los invente. El código debe identificar consistentemente un producto. El nombre ayuda a reconocerlo, pero dos nombres parecidos no garantizan que se trate del mismo registro.

Completa `plantillas/diccionario_datos.csv` con significado, ejemplo y restricción. Usa los nombres exactos que encontrarás después en los archivos. Cuando necesites otra información, como número de lote o ubicación, anótala como ampliación y explica qué parte del proceso cambiaría.

## Dibuja una solución pequeña

Prepara tres bocetos: tablero, formulario de producto y formulario de movimiento. En cada uno indica qué hará la persona, qué campos verá y qué respuesta espera. Añade un ejemplo de error comprensible: «No hay cantidad suficiente» permite revisar producto y saldo; un mensaje interno de base de datos no ayuda al usuario del almacén.

Elige tres funciones prioritarias. Para el caso común pueden ser registrar producto, registrar movimiento y consultar existencias. Historial, exportación e indicadores ya están disponibles en la base que explorarás. Mantén un apartado de mejoras futuras para evitar transformar el ejercicio en un ERP completo.

## Mini práctica: convierte una petición imprecisa

Reescribe «quiero controlar mi bodega» en una historia, cuatro campos y dos criterios. Después redacta una instrucción para la IA: contexto, objetivo, límites y comprobación. Pide primero que revise el diseño, sin generar archivos. Si no tienes modelo, intercambia la instrucción con un compañero y comprueba si entiende qué construiría.

| Error frecuente | Cómo corregirlo |
|---|---|
| Pedir solo una pantalla bonita | Añadir operación y resultado verificable |
| Confundir cantidad con unidad | Escribir siempre 3 UN o 3 KG según el producto |
| Llamar stock de seguridad al mínimo | Usar mínimo configurado; aquí no se calcula seguridad |
| Aceptar un rechazo sin revisar datos | Comparar saldo e historial antes y después |

### Glosario breve

- **Regla de negocio:** condición propia del proceso que la aplicación debe respetar.
- **Criterio de aceptación:** resultado que demuestra que una función cumple.
- **Backend:** parte que atiende solicitudes y aplica reglas en el servidor.
- **Alcance:** funciones incluidas en esta primera versión.

## Punto de control

Muestra tu dibujo y explica qué ocurre con una salida excesiva. Debes poder señalar el dato utilizado, la regla que se comprueba y la evidencia del rechazo. Guarda la historia y los criterios en la misma ficha del laboratorio 1; se utilizarán después para probar el proyecto.

## Fuentes para consultar

- [Django Girls: cómo funciona internet](https://tutorial.djangogirls.org/es/how_the_internet_works/).
- [Django: proyecto, aplicación y solicitud](https://docs.djangoproject.com/es/5.2/intro/tutorial01/).
'''),
    'Preparar el entorno y reconocer el proyecto': _wiki(r'''
## Objetivo: abrir tu copia y saber dónde estás

En esta lectura conocerás las piezas que hacen funcionar la aplicación. No necesitas memorizar comandos: necesitas reconocer qué orden estás ejecutando, en qué carpeta y con qué resultado. El laboratorio 2 contiene la secuencia completa. Aquí entenderás el propósito de cada paso para no continuar a ciegas cuando aparezca un mensaje.

Descarga y extrae el kit en una carpeta propia llamada, por ejemplo, `andina-distribucion`. Abre esa carpeta con tu editor y localiza `manage.py`. No ejecutes las prácticas dentro del proyecto institucional CITT ni copies sus claves o bases. Cada participante utiliza su aplicación y sus datos ficticios.

![Mapa de los archivos del proyecto docente](/static/portal/img/cursos/logistica-ia/mapa-proyecto.svg)

## Comprende las herramientas con una comparación sencilla

| Pieza | Para qué sirve | Cómo reconocerla |
|---|---|---|
| Python | Ejecuta las instrucciones | Intérprete que usas en los comandos |
| Django | Organiza datos, formularios y páginas | Dependencia del proyecto |
| Editor | Permite leer y cambiar archivos | Muestra carpetas y contenido |
| Terminal | Recibe órdenes y muestra resultados | Lugar donde ejecutas `manage.py` |
| Navegador | Muestra y utiliza la aplicación | Abre `127.0.0.1:8001` |
| SQLite | Conserva los registros locales | Archivo `db.sqlite3` generado |

El navegador no ejecuta todas las reglas del inventario. Envía una solicitud a la aplicación. Django la atiende y utiliza los datos guardados. Si cierras el servidor, el navegador deja de recibir respuestas, pero tus archivos y registros locales no desaparecen.

## Prepara un entorno separado

El entorno virtual es una carpeta con el Python y las bibliotecas que utilizará esta copia. Evita mezclar requisitos de ejercicios distintos. El kit se ha probado con Python 3.11; también ofrece indicaciones para 3.12. Revisa `README.md` antes de sustituir versiones por recomendaciones de un video antiguo.

En Windows, desde PowerShell en la carpeta de `manage.py`:

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

En Linux, comprueba que `python3` corresponde a 3.11 o 3.12 y crea el entorno:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Ejecuta cada línea por separado. Si falla, lee el mensaje antes de continuar. Las rutas explícitas permiten utilizar el mismo intérprete en todos los pasos; en Windows evitan tener que cambiar la política general de ejecución para activar el entorno.

## Comprende el primer arranque

Las migraciones preparan las tablas. `preparar_demo` incorpora cuatro productos y seis movimientos ficticios sin duplicarlos cuando se repite. `crear_usuario` configura cuentas para operación o consulta y solicita contraseñas propias. `runserver` pone en marcha el servidor de práctica en la dirección local indicada.

La primera ejecución sigue ese orden. Para volver a trabajar otro día, normalmente solo necesitas iniciar el servidor. No vuelvas a crear las cuentas cada vez. No uses contraseñas de otros servicios ni las incluyas en tu entrega. El comando de arranque utiliza 8001 para diferenciar esta aplicación del portal institucional que puede estar en 8000.

> [!NOTE]
> Mantén abierta la terminal del servidor. Para ejecutar otra orden, abre una segunda terminal en la misma carpeta o detén el servidor con Ctrl+C y vuelve a iniciarlo cuando corresponda.

## Lee el mapa sin intentar entenderlo todo

Abre `inventario/models.py` y localiza `Producto`. Reconoce código, nombre, unidad y mínimo; todavía no necesitas explicar cada línea. Después abre `templates/inventario/tablero.html` y busca el título visible. Has encontrado dos cosas distintas: descripción de datos y presentación de una pantalla.

| Archivo | Pregunta que ayuda a responder |
|---|---|
| `manage.py` | ¿Qué tarea quiero ejecutar? |
| `andina/settings.py` | ¿Cómo está configurada esta copia? |
| `inventario/models.py` | ¿Qué información se guarda? |
| `inventario/forms.py` | ¿Qué datos recibe un formulario? |
| `inventario/services.py` | ¿Qué reglas aplica una operación? |
| `inventario/views.py` | ¿Cómo se atiende una solicitud? |
| `inventario/tests.py` | ¿Qué situaciones se comprueban? |

## Mini práctica: sigue un campo

Busca `minimo` en el modelo y después en el formulario de producto. Describe su propósito con una frase. En la pantalla crea el producto que indique el laboratorio y comprueba que el mínimo se conserva, mientras la existencia comienza en cero. Guarda una captura con datos ficticios; no es necesario compartir archivos de configuración.

Pide al asistente una explicación de un solo archivo. Si menciona una función que no encuentras, solicita que señale el fragmento real. Una explicación generada puede resultar plausible y referirse a otra versión del proyecto.

## Diagnóstico sin cambiar todo

| Mensaje o situación | Primera comprobación |
|---|---|
| No se encuentra `manage.py` | Estás en la carpeta correcta |
| No se encuentra Django | Instalaste con el Python de `.venv` |
| No existe una tabla | Ejecutaste `manage.py migrate` |
| Puerto ocupado | Usa otro puerto local y abre esa dirección |
| Acceso restringido | Revisa el usuario y su rol |
| No abre la página | El servidor sigue encendido y usas 8001 |

No borres la base para resolver cualquier problema: podrías perder las evidencias de tu práctica. Conserva comando, mensaje y paso anterior. Oculta contraseñas o secretos antes de pedir ayuda. Una copia extraída en otra carpeta permite recuperar el punto inicial sin destruir tu trabajo actual.

### Glosario breve

- **Dependencia:** biblioteca que necesita el proyecto.
- **Intérprete:** programa que ejecuta Python.
- **Migración:** cambio preparado en la estructura de datos.
- **Servidor local:** proceso que responde en tu computador.

## Punto de control y fuentes

Continúa cuando puedas abrir el tablero, identificar cinco archivos y explicar la diferencia entre iniciar el servidor y preparar la base. La evidencia pertenece al laboratorio 2 y no añade otra entrega.

- [Python: entornos virtuales](https://docs.python.org/es/3/tutorial/venv.html).
- [Django: instalación](https://docs.djangoproject.com/es/5.2/intro/install/).
- [Django Girls: instalación](https://tutorial.djangogirls.org/es/django_installation/).
'''),
    'Pedir, revisar y corregir cambios con un asistente de IA': _wiki(r'''
## La IA te ayuda; tú defines el resultado

Un asistente puede explicar archivos, proponer un plan y escribir una modificación. No conoce automáticamente las necesidades del almacén ni garantiza que sus cambios funcionen. Tu papel será dar contexto, comprobar lo propuesto y decidir qué conservar. No necesitas redactar código sin apoyo, pero sí poder explicar para qué sirve el cambio y cómo lo comprobaste.

Trabajaremos sobre la plantilla Andina Distribución. Esto reduce la dificultad inicial y permite comparar el antes y el después. Si pides «haz todo el sistema», es difícil identificar qué regla se perdió. Una petición pequeña, como mejorar una ayuda de pantalla, permite practicar el ciclo completo sin cambiar simultáneamente muchas piezas.

![Ciclo de petición, revisión, prueba y recuperación](/static/portal/img/cursos/logistica-ia/ciclo-ia.svg)

## Escribe una instrucción que pueda comprobarse

Incluye contexto, objetivo, límites y resultado esperado. Añade el archivo si ya lo conoces. Utiliza lenguaje normal y ejemplos concretos; no hace falta llenar el mensaje de términos técnicos. La precisión proviene de describir bien el comportamiento.

| Parte | Ejemplo para este proyecto |
|---|---|
| Contexto | Prototipo docente de inventarios, Python y Django |
| Objetivo | Aclarar la ayuda del campo cantidad |
| Límite | No cambiar cálculos, permisos ni dependencias |
| Resultado | La pantalla explica que se utiliza punto decimal |
| Comprobación | Una entrada de 2.50 sigue registrándose correctamente |

Una petición completa podría ser: «Trabajamos sobre el kit Andina Distribución. Quiero que la ayuda del campo cantidad sea más clara para una persona sin experiencia. Revisa `inventario/forms.py`. Propón primero el texto y explica qué modificarías. Conserva las validaciones, rutas y permisos. Después comprobaremos una entrada de 2.50 y el rechazo de cantidad cero».

## Usa el ciclo de trabajo de principio a fin

1. Abre la aplicación y confirma que la versión actual funciona.
2. Guarda una copia o un commit antes del cambio.
3. Pide un plan pequeño, todavía sin editar.
4. Comprueba que los archivos propuestos tienen relación con el objetivo.
5. Autoriza únicamente el cambio que entiendes.
6. Lee la diferencia: qué había y qué quedó.
7. Ejecuta las pruebas y repite la operación desde la pantalla.
8. Registra el resultado y conserva la nueva versión o vuelve a la anterior.

En OpenCode puedes comenzar en modo Plan y pasar a Build cuando comprendas la propuesta. Si utilizas otra herramienta, conserva la misma secuencia. Los botones o atajos pueden variar con la versión: la documentación oficial es la referencia para su manejo. No necesitas habilitar todos los permisos para que la práctica sea útil.

## Preguntas que facilitan la revisión

Pide al asistente: «Explica este cambio con un ejemplo de entrada y salida». Luego pregunta: «¿Qué regla podría verse afectada y cómo la pruebo?». Solicita que identifique los archivos realmente modificados. Abre el fragmento, aunque todavía necesites ayuda para interpretarlo.

Si la IA afirma que la cantidad se valida, comprueba que el código sigue rechazando cero y negativos. Si propone eliminar una validación porque impide guardar un dato incorrecto, la propuesta contradice el objetivo del curso. Documentar que descartaste un cambio demuestra comprensión; no es un fracaso de la actividad.

> [!TIP]
> Cuando aparezcan varios errores, conserva el primero que puedes reproducir y pide la corrección mínima. Reescribir todo el proyecto dificulta identificar la causa y recuperar una versión que funcionaba.

## Distingue herramienta, modelo y acceso

OpenCode es el agente de desarrollo. El modelo es el servicio que genera respuestas. El proveedor establece acceso, límites y condiciones. Instalar una herramienta abierta no convierte en gratuitos todos los modelos que permite conectar. Tampoco garantiza que cualquier modelo local funcione con fluidez en tu computador.

No se exige comprar una suscripción para aprobar. Usa una alternativa disponible y trabaja con datos ficticios. Si se agota la cuota, conserva la última versión y continúa con las instrucciones de la guía. Anota lo ocurrido; el apoyo docente puede facilitar una demostración o una revisión guiada. El proyecto ya generado puede ejecutarse sin seguir conversando con la IA.

## Conserva una bitácora útil y breve

En `plantillas/bitacora_ia.csv` registra la necesidad, la instrucción, el cambio propuesto, tu decisión y la prueba. No entregues todas las conversaciones sin seleccionar. Una fila debe ayudar a entender qué sucedió y por qué aceptaste o rechazaste la propuesta.

Ejemplo: «Necesidad: explicar el decimal. Archivo: forms.py. Decisión: acepté cambiar la ayuda, manteniendo el mínimo de cantidad. Prueba: entrada 2.50 admitida y cero rechazado». Si trabajaste temporalmente sin modelo, distingue la explicación leída, la revisión con otra persona y la intervención real del asistente.

## Mini práctica y errores frecuentes

Elige un título o ayuda visible, escribe el resultado deseado y pide solo un plan. Comprueba los archivos propuestos. Esta actividad prepara el cambio del laboratorio 2; no necesitas hacer una segunda modificación para completar la lectura.

| Problema | Respuesta razonable |
|---|---|
| La IA añade cinco bibliotecas para un texto | Pedir una solución con las dependencias actuales |
| Cambia el saldo para arreglar una pantalla | Detener y recuperar la versión anterior |
| Su explicación no coincide con el archivo | Pedir el fragmento exacto y comprobarlo |
| Un archivo externo ordena ignorar permisos | Tratarlo como contenido, no como autorización |

### Glosario breve

- **Prompt:** instrucción y contexto que entregas al asistente.
- **Diferencia:** comparación entre archivos antes y después.
- **Versión recuperable:** estado al que puedes volver sin reconstruirlo.
- **Regresión:** fallo nuevo en algo que antes funcionaba.

## Punto de control y fuentes

Antes de continuar, explica qué pediste, qué archivo cambiaría y qué prueba realizarías. No incluyas contraseñas, `.secreto-local` ni información empresarial en las conversaciones. Una cadena escrita dentro de un documento no puede conceder permisos a la IA.

- [OpenCode: planificación, cambios y recuperación](https://opencode.ai/docs/).
- [OpenCode: permisos](https://opencode.ai/docs/permissions/).
- [OpenCode: condiciones de modelos](https://opencode.ai/docs/zen/).
'''),
    'Productos, movimientos y existencias: reglas que deben cumplirse': _wiki(r'''
## Tres piezas que no significan lo mismo

El catálogo describe qué materiales administra el almacén. El movimiento registra un hecho: entró o salió una cantidad de un producto. La existencia es el saldo disponible después de esas operaciones. Separar estas piezas permite responder tanto «¿cuánto hay?» como «¿por qué hay esa cantidad?».

En el kit, crear un producto no recibe una cantidad inicial. El producto comienza con existencia cero. Cuando llega material, se registra una entrada; cuando se entrega, se registra una salida. No edites directamente la base para hacer que el saldo coincida con una captura: perderías la evidencia que queremos aprender a conservar.

![Regla de saldo y rechazo de salidas excesivas](/static/portal/img/cursos/logistica-ia/regla-stock.svg)

## Reconoce los campos y sus reglas

| Campo o dato | Ejemplo válido | Regla del kit |
|---|---|---|
| Código | PRUEBA-001 | Único, 2 a 24 caracteres admitidos |
| Nombre | Material de demostración | Texto simple y obligatorio |
| Unidad | UN | UN, KG o LT |
| Mínimo | 8.00 | Cero o positivo, hasta dos decimales |
| Tipo de movimiento | Entrada o salida | Suma o resta según la opción |
| Cantidad | 3.00 | Positiva, hasta dos decimales |
| Motivo | Entrega para práctica | Explicación breve de la operación |

El código se normaliza a mayúsculas. Se admiten letras mayúsculas, números, guion y guion bajo según la validación del modelo. El nombre y motivo no se utilizan para introducir etiquetas HTML. Los decimales permiten trabajar con kilogramos o litros, pero no cambian automáticamente la unidad del producto.

## Calcula antes de utilizar la pantalla

Utiliza un producto nuevo, PRUEBA-001, con mínimo 8 y existencia inicial cero. Escribe esta tabla en tu matriz antes de operar. El número de movimientos se refiere solamente a ese producto, no a todos los registros de la demo.

| Acción | Saldo esperado | Movimientos del producto |
|---|---:|---:|
| Crear producto | 0.00 | 0 |
| Entrada de 10.00 | 10.00 | 1 |
| Salida de 3.00 | 7.00 | 2 |
| Intentar salida de 8.00 | 7.00 | 2 |
| Intentar cantidad cero | 7.00 | 2 |
| Entrada posterior de 5.00 | 12.00 | 3 |

El rechazo es un resultado correcto cuando protege la regla. No basta con que aparezca un mensaje de error: saldo e historial deben conservarse. Después de cada operación, revisa ambos. El mínimo no bloquea una salida válida; solo señala una condición de revisión cuando la existencia queda por debajo.

## Cómo se protege la operación

`inventario/forms.py` recibe los datos de la pantalla y comprueba su formato. `inventario/services.py` contiene `registrar_movimiento`: comprueba permiso, cantidad, tipo y motivo antes de cambiar la existencia. La actualización del saldo y el nuevo movimiento se realizan dentro de una transacción.

Una transacción significa que los cambios relacionados se completan juntos o se deshacen juntos si ocurre un error. El servicio también condiciona una salida a que siga existiendo cantidad suficiente. No necesitas escribir estas instrucciones desde cero; debes localizar la regla y explicar por qué el formulario por sí solo no basta.

> [!NOTE]
> El proyecto es una práctica local con SQLite. Sus controles y pruebas no equivalen a una validación completa para cargas empresariales o muchos usuarios simultáneos. Esa revisión corresponde a un alcance posterior.

## Cantidades y reintentos

La cantidad debe ser positiva y tener como máximo dos decimales significativos admitidos. Si ingresas 1.234, el sistema no debe redondearla silenciosamente para aceptar otra operación. Usa punto decimal y comprueba que 2.50 mantiene su significado.

Cada solicitud de movimiento lleva una clave identificadora. Enviar nuevamente la misma operación con la misma clave no debe descontar dos veces. Dos salidas diferentes pueden tener igual producto y cantidad; se distinguen por su identidad, no se eliminan simplemente porque se parecen. Si aparece un aviso de operación ya procesada, consulta primero el historial antes de volver a enviar.

## Quién puede hacer cada cosa

La cuenta `lector` tiene el rol Consulta: lee el tablero, consulta el historial y exporta. La cuenta `operador`, con rol Operación, también registra productos, importa catálogo y registra movimientos. Las dos cuentas son diferentes de una cuenta administradora.

Para comprobar los roles, sal de una cuenta e ingresa con la otra. El lector no debe poder entrar a `/movimientos/nuevo/` para registrar. El servidor rechaza el acceso aunque alguien copie esa dirección. No soluciones un acceso restringido concediendo permisos de administrador: eso impediría demostrar la diferencia que exige el ejercicio.

## Mini práctica y diagnóstico

Antes del laboratorio 3, explica a otra persona por qué una salida de 8 sobre un saldo de 7 se rechaza. Identifica en `services.py` el mensaje de stock insuficiente. Después elige un dato inválido y escribe qué debe permanecer igual si se rechaza.

| Dificultad | Qué revisar |
|---|---|
| El saldo esperado no coincide | Producto seleccionado, unidad y secuencia realizada |
| No aparece un movimiento | Si hubo rechazo o utilizaste otra cuenta/copia |
| El lector puede operar | Cuenta, rol y pruebas de permisos |
| Hay dos operaciones parecidas | Sus identificadores; no deduplicar solo por cantidad |

### Glosario breve

- **Saldo:** existencia actual de un producto.
- **Transacción:** conjunto de cambios que se completan juntos.
- **Validación:** comprobación de que un dato o una operación cumple reglas.
- **Permiso:** autorización concreta para leer o realizar una acción.

## Punto de control y fuentes

Continúa cuando puedas demostrar entrada, salida válida y rechazo sin cambios. Si una mejora permite saldo negativo o escritura con Consulta, corrígela antes de aprobar aunque otras partes del proyecto funcionen. Conserva la tabla para la entrega; no representa otra tarea adicional.

- [Django: validación](https://docs.djangoproject.com/en/5.2/ref/forms/validation/).
- [Django: transacciones](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).
- [Django: usuarios y permisos](https://docs.djangoproject.com/es/5.2/topics/auth/default/).
'''),
    'Construir una función y demostrar que funciona': _wiki(r'''
## Una mejora pequeña permite comprender el desarrollo

Ya tienes una aplicación de referencia que abre, registra y consulta información. Ahora practicarás cómo mejorar una función sin perder las reglas del inventario. No se trata de pedir muchas pantallas y esperar que todo esté bien: elegirás una necesidad, describirás el resultado y comprobarás qué cambió.

En este curso construir también significa adaptar una base, reconocer sus componentes y demostrar una aportación propia. La plantilla resuelve el punto de partida; tu bitácora mostrará las decisiones que tomaste. Esta lectura prepara la mejora del laboratorio 3 y la revisión posterior del proyecto, sin exigir una aplicación adicional.

![Ciclo para construir una mejora y comprobarla](/static/portal/img/cursos/logistica-ia/ciclo-ia.svg)

## Reconoce lo que la aplicación ya ofrece

El tablero busca productos por código o nombre. El historial muestra los movimientos recientes; la plantilla actual no incorpora filtros de fechas. Los formularios permiten crear productos e introducir entradas o salidas. Importar y exportar son funciones separadas. Confirmar este punto evita solicitar una mejora sobre un campo o filtro que todavía no existe.

| Necesidad | Qué existe | Mejora acotada posible |
|---|---|---|
| Encontrar material | Búsqueda del tablero | Ayuda con un ejemplo de código |
| Comprender un rechazo | Mensaje de stock insuficiente | Explicación más clara sin cambiar la regla |
| Saber qué escribir | Ayuda de cantidad | Recordatorio del punto decimal |
| Reconocer el tablero | Título y texto de presentación | Nombre apropiado para el almacén docente |

Si escoges añadir un filtro nuevo, tendrás que definir su dato, criterio y prueba. Para una primera experiencia conviene comenzar con una ayuda de pantalla: es más fácil comprobarla y no requiere introducir nuevas reglas. Una mejora visual puede ser útil si facilita una tarea concreta del usuario.

## Define la aceptación antes de editar

Ejemplo: «Una persona debe reconocer cómo escribir 2.50 en el campo cantidad. La ayuda se verá antes de enviar el formulario. Los rechazos de cero, negativo y stock insuficiente se conservarán». Este objetivo diferencia la presentación de las reglas que no queremos alterar.

1. Abre `inventario/forms.py` y localiza la ayuda de `cantidad`.
2. Anota el texto actual o conserva una captura.
3. Escribe el nuevo texto en lenguaje sencillo.
4. Pide al asistente un plan para cambiar únicamente esa ayuda.
5. Comprueba que no propone modificar `registrar_movimiento` ni instalar bibliotecas.

Puedes modificar manualmente el texto con apoyo de la guía si el modelo no está disponible. En la bitácora distingue esa edición de una sugerencia realmente generada por IA. No atribuyas al asistente un trabajo que no realizó.

## Revisa y ejecuta el cambio

Guarda una versión recuperable. Después revisa la diferencia de archivos. Un cambio de ayuda no debería alterar el permiso de la vista ni la forma de calcular saldos. Si el asistente hace modificaciones adicionales, pregunta su necesidad y descarta las que no correspondan al objetivo.

Reabre el formulario y comprueba el texto. Si una página no actualiza, recarga el navegador y revisa que el servidor corresponde a la carpeta donde editaste. Puedes tener dos copias del kit y estar viendo la antigua. Conserva esa comprobación antes de pedir más cambios al modelo.

> [!TIP]
> Describe «en esta pantalla, antes de enviar, debe aparecer esta ayuda» en lugar de «mejora toda la experiencia». Una petición localizada facilita que tú y el evaluador comprobéis lo mismo.

## La pantalla y las reglas se prueban por separado

Primero observa la ayuda. Después utiliza un producto nuevo para una operación válida y una inválida. Si había 10 UN y registras una salida de 3, debe quedar 7. El intento posterior de retirar 8 debe rechazarse sin cambiar saldo ni historial. La ayuda puede haber mejorado, pero estas reglas siguen siendo necesarias.

El formulario transforma los campos enviados. La vista recibe la solicitud y llama al servicio. El servicio aplica las reglas del movimiento. Un mensaje agradable no demuestra que el servicio guardó correctamente. Por eso la evidencia debe incluir el resultado operativo, además de una captura del texto cambiado.

## Cuando aparece un error

Registra la acción, los datos ficticios y el mensaje. Pide una causa probable y una corrección mínima, evitando enviar secretos. Contrasta la propuesta con el archivo señalado. Si cambia un cálculo para eliminar el error, vuelve a la expectativa original: la salida inválida debe rechazarse, no hacerse posible.

| Situación | Cómo avanzar |
|---|---|
| El cambio no se ve | Revisar carpeta, servidor y recarga |
| La aplicación deja de abrir | Comprobar la última diferencia y recuperar copia |
| El modelo elimina validaciones | Rechazar esa modificación y explicar el criterio |
| Un test falla después del cambio | Leer qué comportamiento esperaba y repetirlo manualmente |

## Mini práctica: documenta una aportación

Prepara tres frases: «El usuario necesitaba…», «Cambié…» y «Lo comprobé mediante…». Añade archivo y versión. Ejemplo: «Cambié la ayuda de cantidad en forms.py; la entrada de 2.50 se registró y la cantidad cero se rechazó». Esta explicación cabe en una fila de la bitácora y acompaña la mejora del laboratorio.

Al presentar el código, reconoce que catálogo, permisos e importador pertenecían al material inicial. Tu aportación puede ser pequeña y estar bien justificada. El número de líneas escritas no es una medida suficiente del aprendizaje ni de la utilidad logística.

### Glosario breve

- **Formulario:** campos y comprobaciones para recibir datos.
- **Vista:** componente que atiende una solicitud web.
- **Servicio:** función que concentra reglas de una operación.
- **Prueba de regresión:** revisión de funciones anteriores después de un cambio.

## Punto de control y fuentes

Continúa cuando puedas mostrar el antes, el después y una regla que sigue cumpliéndose. Ejecuta también las pruebas del kit como indica el laboratorio. Si la mejora no tiene un resultado observable, delimítala antes de añadir más funciones.

- [Django: modelos y administración](https://docs.djangoproject.com/es/5.2/intro/tutorial02/).
- [Django: formularios y vistas](https://docs.djangoproject.com/es/5.2/intro/tutorial04/).
- [Django Girls: formularios](https://tutorial.djangogirls.org/es/django_forms/).
'''),
    'De Excel al tablero: importar, comprobar y explicar indicadores': _wiki(r'''
## El dato debe conservar su significado

Pasar de Excel a una aplicación no consiste solamente en subir un archivo. Debes comprobar columnas, códigos, unidades y cantidades. Un archivo puede abrirse sin errores y contener información que la aplicación no admite. Antes de importar, entiende qué representa cada fila y qué cambiará en el sistema.

El kit utiliza CSV, un archivo de texto con encabezados y filas separadas por comas. Excel puede abrirlo, pero CSV no contiene las hojas, fórmulas ni formatos de un libro XLSX. Esta elección permite observar exactamente qué se envía a la aplicación. No debes cambiar la extensión de un libro a .csv suponiendo que eso convierte su contenido.

![Datos, reglas de importación e indicadores del tablero](/static/portal/img/cursos/logistica-ia/datos-indicadores.svg)

## Comprueba el contrato de importación

El archivo debe estar guardado como CSV UTF-8, separado por comas y con punto decimal. La primera línea es exactamente `codigo,nombre,unidad,minimo`. El orden forma parte del contrato. Se admiten hasta 100 productos y 1 MB por archivo. Los códigos no deben existir previamente ni repetirse dentro del mismo documento.

| Columna | Ejemplo | Qué comprobar |
|---|---|---|
| `codigo` | AD-101 | Código válido y nuevo |
| `nombre` | Material ficticio | Texto simple, no vacío |
| `unidad` | UN | UN, KG o LT |
| `minimo` | 3.50 | Cero o positivo, hasta dos decimales |

La importación crea productos con existencia cero. No añade stock aunque el nombre del archivo mencione inventarios. Las existencias cambian mediante movimientos. El archivo `datos/movimientos_ejemplo.csv` es un guion para introducir operaciones desde el formulario; no hay un importador automático de esos movimientos en el kit.

## Abre los archivos sin alterar el original

1. Abre `datos/productos_validos.csv` con el editor y reconoce la cabecera.
2. En Excel utiliza Datos y la opción Desde texto/CSV si la apertura directa mezcla columnas.
3. Selecciona coma como separador y comprueba los códigos como texto.
4. Revisa el punto decimal y la unidad de cada fila.
5. Conserva el archivo original y guarda cualquier adaptación con otro nombre.

Una configuración regional puede hacer que Excel espere punto y coma. No significa que el importador esté preparado para ese separador. El mensaje de error y la cabecera del kit te indican qué debes conservar. Si usas otra hoja de cálculo, aplica la misma comprobación de texto, separador y decimales.

## Observa una carga correcta y otra rechazada

`productos_validos.csv` contiene cuatro códigos nuevos, AD-101 a AD-104. En una base donde no existen, se crean cuatro productos con saldo cero. Una segunda importación se rechaza por duplicados: no es una orden de actualizar registros existentes.

`productos_invalidos.csv` incluye varias condiciones incorrectas. El importador revisa el conjunto y, si encuentra errores, no guarda ningún producto del archivo. Comprueba que AD-201 no aparece después del rechazo. Esta política evita dejar una carga parcialmente realizada sin que el alumno sepa qué quedó registrado.

> [!NOTE]
> Si tu base ya tiene productos añadidos en prácticas anteriores, el total puede ser diferente del ejemplo de una base nueva. Anota el estado inicial y compara los cambios, no fuerces el saldo para igualar una captura.

## Interpreta tres indicadores suficientes

El tablero cuenta productos registrados, productos bajo mínimo y productos sin stock. Son conteos de registros, no suma de cantidades. Bajo mínimo significa `existencia < minimo`; la igualdad no activa esa condición. Sin stock significa existencia cero.

| Producto de prueba | Existencia / mínimo | Bajo mínimo | Sin stock |
|---|---|---|---|
| A | 7.00 / 8.00 | Sí | No |
| B | 5.00 / 5.00 | No | No |
| C | 0.00 / 0.00 | No | Sí |

En una base recién preparada hay 4 productos, 2 bajo mínimo y 0 sin stock. Después de importar el catálogo válido habrá 8, 6 y 4, respectivamente, si no has añadido ni cambiado otros registros. La barra de cada producto compara existencia con mínimo y se limita al 100 %; no representa ocupación de la bodega ni capacidad de estanterías.

La búsqueda filtra las filas visibles del tablero; los tres indicadores siguen describiendo el catálogo completo. La exportación también contiene todo el catálogo. No presentes los contadores como si correspondieran únicamente a la búsqueda actual.

## Exporta y comprueba el reporte

El archivo exportado tiene seis columnas: las cuatro del catálogo, `existencia` y `bajo_minimo`. Es un reporte, no una plantilla válida para reimportar directamente. Compara un producto con el tablero y conserva la unidad. No sumes 9.25 KG con 17 UN como si fueran la misma magnitud.

Los textos que podrían interpretarse como fórmulas se protegen en la exportación. Si aparece un apóstrofo de protección, conserva el significado del texto; no ejecutes fórmulas recibidas de fuentes desconocidas. La IA puede ayudarte a explicar un indicador, pero la cifra debe salir de los datos comprobados.

## Mini práctica y diagnóstico

Calcula manualmente las condiciones de A, B y C. Después usa los productos que crearás en el laboratorio 4 para contrastar el subconjunto. Anota por separado los totales anteriores y posteriores. Esta tabla será parte de la misma entrega de datos e indicadores.

| Error | Remedio |
|---|---|
| Todo aparece en una columna | Revisar separador de importación en la hoja |
| Se intenta importar el reporte exportado | Volver a la cabecera de cuatro campos |
| Cambia el total respecto del ejemplo | Revisar productos añadidos y operaciones previas |
| Se confunde mínimo con compra recomendada | Explicar el criterio y la información faltante |

### Glosario y punto de control

**Cabecera** nombra las columnas; **UTF-8** es la codificación del texto; **indicador** resume una condición; **carga completa** significa que el conjunto se acepta entero o no se guarda. Continúa cuando puedas explicar una fila rechazada y calcular un indicador sin depender del texto de la IA.

## Fuentes para consultar

- [Python: lectura y escritura CSV](https://docs.python.org/es/3/library/csv.html).
- [Django: respuestas CSV](https://docs.djangoproject.com/en/5.2/howto/outputting-csv/).
'''),
    'MCP: conectar un asistente a los datos de la aplicación': _wiki(r'''
## Una conexión con funciones definidas

MCP es un protocolo que permite a una aplicación de IA descubrir y utilizar herramientas de otro programa. No es el modelo que redacta respuestas y no da acceso automático a cualquier aplicación. Para conectarse necesita una integración que describa qué funciones existen, qué datos reciben y qué devuelven.

En nuestro caso conectaremos el asistente con datos ficticios del inventario. El objetivo es comprender el recorrido y verificar la respuesta. El servidor preparado evita que tengas que desarrollar una integración completa desde cero. Esa construcción avanzada queda fuera de esta primera experiencia.

![Asistente, cliente, servidor MCP y datos del inventario](/static/portal/img/cursos/logistica-ia/arquitectura-mcp.svg)

## Distingue las piezas con una pregunta real

Pides «consulta AD-001 y explica si está bajo el mínimo». El host es la aplicación donde conversas, por ejemplo OpenCode. Su cliente MCP solicita una herramienta al servidor. El servidor ejecuta una consulta fija sobre el archivo local `db.sqlite3` y devuelve datos estructurados. El modelo utiliza esos datos para redactar la explicación.

| Pieza | Función en la práctica | Qué no debes asumir |
|---|---|---|
| Modelo | Interpreta la petición y redacta | Que siempre interpreta bien los datos |
| Host y cliente | Gestionan la conexión y herramientas | Que solo disponen de las herramientas MCP |
| Servidor MCP | Expone funciones concretas | Que crea cualquier función solicitada |
| Base local | Conserva el estado del inventario | Que contiene información institucional |

La documentación también distingue recursos y prompts. Un recurso proporciona contexto; un prompt ofrece una instrucción preparada; una herramienta ejecuta una función definida. En el ejercicio usarás herramientas. No necesitas implementar los tres tipos para demostrar que entiendes su diferencia.

## Conoce las dos herramientas del kit

`consultar_existencias` recibe un código opcional. Permite consultar AD-001 o devolver el catálogo limitado cuando no se especifica código. `productos_bajo_minimo` devuelve productos cuya existencia es menor que el mínimo. Ambas respuestas identifican el origen ficticio, el carácter de solo lectura y un límite de 100 registros.

El servidor usa `stdio`: el cliente inicia un proceso local y se comunica con él. No abre un puerto de consulta a internet. `mcp_consultas.py` abre SQLite en modo de solo lectura y utiliza consultas predefinidas; no recibe una frase SQL del asistente para ejecutarla.

## Primero verifica sin contratar un modelo

El laboratorio 4 incluye instalar `requirements-mcp.txt` y ejecutar `verificar_mcp.py` con el Python del entorno. El cliente de prueba descubre las dos herramientas, consulta AD-001, comprueba la lista bajo mínimo y verifica el rechazo de un código inválido. También compara la huella del archivo de base antes y después.

El mensaje final indica que se verificaron dos herramientas de consulta, se rechazó una entrada inválida y la base no cambió. Esta prueba no utiliza una API de IA. Demuestra comunicación y datos; no demuestra una conversación con un modelo. Conserva esa diferencia en las evidencias y en la presentación.

> [!TIP]
> Antes de comprobar que la base no cambia, detén el servidor web y evita registrar operaciones al mismo tiempo. Así una modificación ajena a la consulta no confundirá el resultado de la práctica.

## Después conecta un asistente disponible

`preparar_opencode.py` genera `opencode.json` con las rutas reales de tu intérprete y servidor. No introduce claves y no sobrescribe una configuración existente. Abre OpenCode desde la misma carpeta y utiliza un modelo disponible compatible con herramientas. La disponibilidad gratuita puede variar; no necesitas comprar un plan para demostrar el protocolo.

La configuración pide autorización para edición, comandos y herramientas de Andina. Revisa qué operación solicita el host. Aunque nuestro MCP sea de lectura, el asistente de desarrollo podría tener herramientas propias para ejecutar comandos o modificar archivos. Durante esta demostración solo autoriza la consulta esperada, no una vía alternativa para cambiar inventario.

## Contrasta antes de creer la explicación

1. Consulta AD-001 y registra código, unidad, existencia y mínimo devueltos.
2. Inicia el servidor web cuando termines la prueba aislada y compara el producto en el tablero.
3. Consulta productos bajo mínimo y verifica varios registros con el mismo criterio.
4. Pide registrar una salida, sin autorizar comandos ni edición.
5. Explica que no hay una herramienta MCP de escritura y comprueba que el historial no cambia.

La conexión local no hereda las cuentas y roles web: lee el dataset ficticio de tu computador. No la describas como autenticación institucional. Una integración real necesitaría diseñar identidad, permisos y alcance de datos además del protocolo.

## Mini práctica, límites y problemas frecuentes

Dibuja el recorrido de una consulta y escribe quién calcula y quién explica. Si observas las sesiones externas de Jhoni Cerón, registra una idea y su minuto real; no atribuyas a esos videos una demostración del inventario del kit. Sus sesiones son ampliaciones opcionales, fuera de las cuarenta horas obligatorias.

| Situación | Qué hacer |
|---|---|
| Ejecutas servidor_mcp.py y parece esperar | Utilizar el cliente de prueba o el host configurado |
| No encuentra la base | Revisar carpeta, migraciones y datos demo |
| No hay modelo disponible | Entregar prueba de protocolo, claramente identificada |
| La respuesta incluye otra cantidad | Comparar datos devueltos y explicación del modelo |
| El asistente pide ejecutar una salida por terminal | Rechazar esa acción; excede la consulta preparada |

### Glosario y punto de control

**Host** es la aplicación de IA; **herramienta** es una función disponible; **stdio** comunica procesos locales; **solo lectura** permite consultar sin modificar datos. Continúa cuando puedas demostrar dos consultas, explicar el límite y distinguir conversación de prueba sin modelo. El proyecto evalúa esas evidencias, no el proveedor utilizado.

## Fuentes para consultar

- [MCP: arquitectura](https://modelcontextprotocol.io/docs/learn/architecture).
- [MCP: servidores, herramientas y recursos](https://modelcontextprotocol.io/docs/learn/server-concepts).
- [OpenCode: conexión MCP](https://opencode.ai/docs/mcp-servers/).
- [SDK oficial de Python](https://github.com/modelcontextprotocol/python-sdk).
'''),
    'Probar y mejorar con evidencias': _wiki(r'''
## Probar significa comparar una expectativa

Una aplicación que abre puede tener un cálculo incorrecto. Una pantalla bonita puede permitir una operación no autorizada. Probar consiste en establecer una situación inicial, ejecutar una acción y comparar el resultado con lo que debería ocurrir. Escribe la expectativa primero; así evitas aceptar como correcto cualquier resultado que aparezca.

Durante el curso ya comprobaste productos, movimientos, importaciones e indicadores. La unidad 5 organiza esas evidencias en una matriz y vuelve a ejecutar las reglas después de tu mejora. No necesitas inventar un proyecto de pruebas distinto: utilizarás los mismos archivos y el mismo prototipo.

![Pruebas, correcciones y preparación de la entrega](/static/portal/img/cursos/logistica-ia/pruebas-entrega.svg)

## Prepara una matriz que otra persona pueda seguir

Abre `datos/pruebas_aceptacion.csv`. Una fila útil describe estado inicial, acción, esperado, obtenido y evidencia. Utiliza un producto exclusivo para no confundir operaciones de unidades anteriores. Conserva la unidad de medida y registra cuántos movimientos de ese producto hay antes y después.

| Estado inicial | Acción | Resultado esperado |
|---|---|---|
| Código disponible | Crear producto | Un producto con existencia cero |
| Código ya registrado | Intentar repetirlo | Rechazo, sin segundo producto |
| Existencia 10 UN | Salida de 3 UN | Existencia 7 y un nuevo movimiento |
| Existencia 7 UN | Salida de 8 UN | Rechazo, mismo saldo e historial |
| Usuario lector | Abrir registro de movimiento | Acceso restringido |

Añade cantidades cero, negativa y texto; una búsqueda sin coincidencias; CSV inválido; igualdad entre existencia y mínimo; y consulta MCP. Elige datos pequeños que puedas calcular a mano. No hace falta tener cientos de filas para comprobar una regla de esta práctica.

## Diferencia una comprobación manual de una automática

La comprobación manual utiliza la pantalla y permite ver mensajes y recorridos. La automática ejecuta casos preparados en `inventario/tests.py`. Ambas aportan evidencia diferente: una captura muestra una situación; un test repite una regla del código con datos controlados.

En Windows ejecuta, desde la carpeta de `manage.py`:

```powershell
.venv/Scripts/python.exe manage.py test inventario
```

En Linux:

```bash
.venv/bin/python manage.py test inventario
```

Lee el resumen final. Un resultado correcto demuestra que pasan los casos incluidos, no que la aplicación carece de cualquier error posible. Pide al asistente que explique una prueba y señala el comportamiento que protege. No necesitas diseñar una infraestructura de pruebas avanzada para aprobar este curso introductorio.

## Comprueba permisos sin falsear el escenario

Sal de la cuenta operador e ingresa como lector. Revisa que puede leer tablero, historial y exportación. Después abre directamente `/movimientos/nuevo/`. Debe recibir un acceso restringido. Ocultar el botón no sería evidencia suficiente si la dirección permitiera registrar.

Las pruebas automáticas del kit también comprueban solicitudes de escritura sin permiso. No intentes resolver un rechazo concediendo permisos al lector. El rechazo es precisamente el resultado esperado. Si tu modificación rompió este comportamiento, recupera la versión anterior o corrige el cambio antes de presentar.

> [!WARNING]
> Un prototipo que permite stock negativo o escritura sin permiso necesita corrección antes de aprobar, aunque la suma inicial de otros criterios supere 70/100. El docente verifica esas condiciones; el aula no analiza automáticamente tu aplicación entregada.

## Corrige el cambio mínimo y vuelve a probar

Cuando un caso falla, registra qué versión utilizaste, qué acción hiciste y qué resultado apareció. Solicita a la IA una explicación y una modificación acotada. Revisa los archivos y comprueba que la solución conserva las reglas anteriores. No elimines la prueba que detectó un fallo solo para obtener un resumen correcto.

Después ejecuta nuevamente el caso que fallaba y las operaciones básicas. Esto se llama revisión de regresión: comprobar que una mejora no dañó algo que ya funcionaba. Guarda una nueva versión cuando tengas evidencia, no solamente cuando desaparezca un mensaje visible.

## Evalúa los datos y MCP con el mismo criterio

Una importación inválida debe rechazar el archivo completo; busca AD-201 para comprobar ausencia de carga parcial. La exportación debe coincidir con el catálogo completo. Para los indicadores explica si comparas toda la base o un subconjunto de productos de prueba.

En MCP conserva herramienta, entrada, resultado y contraste con el tablero. Si solo utilizaste `verificar_mcp.py`, escribe prueba de protocolo sin modelo. Esa modalidad demuestra conexión, reglas de consulta y ausencia de cambios; no debe presentarse como una conversación real que no ocurrió.

## Mini práctica: explica una corrección

Elige una mejora de las unidades anteriores. Completa cinco frases: «Antes ocurría…», «Se esperaba…», «Cambié…», «Repetí estas pruebas…» y «Ahora observé…». Si no apareció ningún fallo, utiliza una propuesta descartada y explica por qué habría contradicho una regla. Guarda esa nota en la bitácora del proyecto.

| Problema de evidencia | Cómo mejorarlo |
|---|---|
| Solo escribes funciona | Añadir datos, acción y resultado |
| Captura sin producto identificable | Mostrar código y unidad ficticios |
| Comparas bases o versiones diferentes | Anotar carpeta, versión y estado inicial |
| Una prueba falla y se omite | Registrar el fallo y la corrección |

### Glosario breve

- **Caso de prueba:** situación preparada para comprobar un comportamiento.
- **Esperado:** resultado definido antes de ejecutar.
- **Obtenido:** resultado observado realmente.
- **Regresión:** pérdida de una función anterior por un cambio nuevo.

## Punto de control y fuentes

La matriz debe permitir repetir al menos diez casos del laboratorio 5. Identifica un éxito, un rechazo correcto y un caso límite. Puedes continuar al proyecto cuando expliques qué comprobaron las pruebas y qué limitaciones conservan. Las capturas y la matriz forman parte de la misma entrega existente.

- [Django: pruebas](https://docs.djangoproject.com/es/5.2/topics/testing/overview/).
- [Django: seguridad](https://docs.djangoproject.com/es/5.2/topics/security/).
- [GitHub: versiones y cambios](https://docs.github.com/es/get-started/start-your-journey/hello-world).
'''),
    'Presentar el prototipo y reconocer su alcance': _wiki(r'''
## Presenta una solución que puedas explicar

Tu presentación debe mostrar qué necesidad logística atiende la aplicación y cómo sabes que funciona. No necesitas producir un video profesional ni explicar cada línea de código. Sí debes reconocer los datos, las reglas, tu aportación sobre la plantilla y las comprobaciones que realizaste.

El proyecto final reúne lo trabajado durante las cinco unidades. Utiliza `plantillas/proyecto_final.md` para organizar la entrega y `plantillas/rubrica_detallada.md` para revisar los criterios. No empieces otra aplicación al llegar al final: prepara la versión del caso común y documenta tus mejoras.

![Ruta de revisión y entrega del prototipo](/static/portal/img/cursos/logistica-ia/pruebas-entrega.svg)

## Organiza una demostración de cinco a ocho minutos

Prepara los productos de prueba antes de presentar. Usa cantidades pequeñas y códigos que se reconozcan en pantalla. El recorrido debe incluir una operación correcta y otra rechazada. Una presentación que solo muestra pantallas iniciales no demuestra que se conserven saldos o permisos.

| Momento | Qué mostrar | Qué explicar |
|---|---|---|
| Problema | Ficha breve | Usuario y necesidad del almacén |
| Catálogo | Producto y unidad | Identificación y mínimo |
| Operación | Entrada y salida | Cálculo de la existencia |
| Rechazo | Salida superior al saldo | Regla y ausencia de cambios |
| Consulta | Indicador o exportación | Origen y significado del dato |
| Integración | Evidencia MCP | Herramienta y límite de lectura |
| Aportación | Antes y después | Tu decisión, prueba y mejora |

Si la consulta MCP se comprobó sin modelo, muestra esa modalidad claramente. No necesitas simular un diálogo. Explica lo que verificó el cliente y qué parte conversacional no se realizó. La honestidad de la evidencia permite evaluar el aprendizaje con independencia del acceso a un proveedor.

## Escribe una guía que otra persona pueda seguir

Describe para qué sirve la aplicación, qué necesita instalarse, desde qué carpeta se ejecutan los comandos y qué dirección debe abrirse. Distingue Windows de Linux. Si el servidor utiliza 8001, la guía debe llevar a `http://127.0.0.1:8001/`. Incluye crear cuentas propias, no una contraseña compartida.

Explica cómo registrar un producto, recibir material, hacer una salida y consultar el resultado. Añade un ejemplo de error y qué revisar. Una persona que no leyó tus conversaciones con la IA debe entender la guía. Pruébala en una carpeta nueva o pide a otra persona que la siga; anota las confusiones y mejora el texto.

## Comparte fuentes reproducibles

Entrega código, requisitos, migraciones, datos ficticios, instrucciones y evidencias. Excluye `.venv`, `db.sqlite3`, `.secreto-local`, `opencode.json` y credenciales. La nueva copia debe poder prepararse con los comandos del README, sin depender de cuentas o rutas privadas de tu computador.

No basta con adjuntar el archivo de base que funciona en tu equipo. La reproducibilidad consiste en reconstruir la práctica a partir de instrucciones y datos conocidos. Conserva una copia personal antes de preparar el paquete y comprueba que entregas la versión final correcta.

> [!TIP]
> Incluye un apartado Material inicial y contribución. Escribe qué venía en el kit, qué modificaste y cómo lo comprobaste. Reconocer la plantilla no disminuye el valor de una mejora bien comprendida.

## Revisa la rúbrica antes de enviar

| Criterio del proyecto | Puntos |
|---|---:|
| A. Funciones y recorrido operativo | 30 |
| B. Datos y validaciones | 25 |
| C. Consultas, reportes e integración | 15 |
| D. Uso de IA explicado y trazable | 10 |
| E. Pruebas y permisos | 10 |
| F. Guía y demostración | 10 |
| Total | 100 |

MCP representa cinco puntos dentro del criterio C. Se admite el cliente preparado sin conversación cuando no hay modelo disponible, con los mismos requisitos de conexión, datos y límites. La marca o precio del asistente no otorga puntos adicionales. Debes documentar tres intervenciones de IA y tus decisiones, distinguiéndolas del material inicial y de revisiones guiadas.

La nota mínima del proyecto es 70/100. Los fallos críticos que permiten stock negativo o modificaciones sin permiso requieren corrección antes de aprobar. El docente registra la nota de la entrega validada. El proyecto no sustituye los demás laboratorios, quizzes ni actividades obligatorias configuradas en el aula.

## Reconoce qué resultado has alcanzado

Has trabajado con un prototipo docente local. No incluye varias bodegas, lotes, valoración, facturación ni optimización de transporte. Llevar una aplicación a una empresa requiere decidir responsabilidades, alojamiento, respaldo, privacidad, soporte y pruebas con uso real. El servidor `runserver` sirve para desarrollo; no debe presentarse como un despliegue de producción.

Puedes explicar una adaptación sin construirla todavía. Para transporte cambiarían datos como vehículo, entrega y estado; para compras, proveedor y solicitud. Indica qué regla e indicador serían distintos. Esta transferencia demuestra que comprendes el patrón y su relación con logística, sin afirmar que ya existe un sistema nuevo.

## Mini práctica y errores frecuentes

Ensaya la demostración con cronómetro y elige una pregunta que podría hacerte el evaluador. Responde dónde se guardan los datos, qué impide una salida excesiva o por qué el mínimo no calcula una compra. Esta práctica utiliza el tiempo de preparación ya asignado al proyecto.

| Error | Cómo corregirlo |
|---|---|
| Presentar solo colores y títulos | Mostrar cálculo, rechazo y evidencia |
| No explicar el código generado | Señalar función y prueba en lenguaje sencillo |
| Entregar claves o rutas privadas | Revisar archivos y guía antes de comprimir |
| Afirmar funciones futuras como construidas | Separar resultado actual y evolución |

### Glosario y punto de control

**Reproducible** significa que otra persona puede repetir los pasos; **contribución** identifica tu cambio; **limitación** precisa lo que la versión no resuelve. Estás listo para entregar cuando tu guía permite iniciar, la matriz coincide con los resultados y puedes explicar una decisión tomada con IA.

## Fuentes para consultar

- [Django: lista de despliegue](https://docs.djangoproject.com/es/5.2/howto/deployment/checklist/): referencia para distinguir práctica y uso real.
- [Django Girls](https://tutorial.djangogirls.org/es/): apoyo introductorio.
- [GitHub: organizar cambios](https://docs.github.com/es/get-started/start-your-journey/hello-world).
'''),
}


LABORATORIOS_WIKI = [
    _wiki(r'''
## Laboratorio 1: diseña una aplicación que puedas explicar

**Tiempo incluido en la unidad: 4 horas y 50 minutos.** Trabajarás sobre Andina Distribución, el mismo caso de las lecturas. Hoy no necesitas instalar Python ni escribir código. Al terminar tendrás una ficha que permitirá construir y comprobar una solución pequeña. Las mini prácticas anteriores se incorporan aquí; no son entregas adicionales.

![Ruta del diseño a la comprobación](/static/portal/img/cursos/logistica-ia/ruta-curso.svg)

## Prepara tus materiales

Abre el kit descargado y localiza `guias/unidad_01.md`, `plantillas/ficha_proyecto.md`, `plantillas/diccionario_datos.csv` y `prompts/01_diseno.md`. Puedes completar los documentos en tu editor o en una herramienta de oficina. Si abres el CSV en una hoja de cálculo, conserva una copia original y comprueba que los encabezados sigan separados correctamente.

Distribuye el tiempo entre entender el caso, dibujar el proceso, describir datos, preparar pantallas y revisar la propuesta. No necesitas una herramienta profesional de diagramación: papel, fotografías legibles y cuadros sencillos son suficientes.

## Paso 1. Explica el problema con una operación concreta

Escribe quién registra las entradas y salidas y quién consulta la disponibilidad. Describe una dificultad observable: códigos repetidos, saldo desactualizado o falta de explicación de una salida. Después redacta el objetivo en dos frases. Por ejemplo: registrar los movimientos de materiales y conservar el saldo junto con su historial.

Define tres funciones indispensables y dos mejoras futuras. Mantén el primer alcance en productos, movimientos y consultas. Varias bodegas, facturación o rutas óptimas pueden quedar como evolución. No las presentes como funciones del kit.

**Resultado esperado:** otra persona comprende qué problema resolverás, quién usa la aplicación y qué queda para después.

## Paso 2. Dibuja el recorrido y señala las reglas

Dibuja producto, entrada, consulta, salida e historial. Une cada elemento con flechas. Junto a entrada y salida escribe dónde cambia la existencia. Junto al historial indica qué información permite explicar lo ocurrido.

![Flujo operativo del inventario](/static/portal/img/cursos/logistica-ia/flujo-inventario.svg)

Completa esta secuencia con el mismo producto y unidad:

| Situación | Acción | Existencia esperada | Evidencia |
|---|---|---|---|
| Producto nuevo | Crear el registro | 0 UN | Código único |
| Existencia 0 | Recibir 10 UN | 10 UN | Una entrada |
| Existencia 10 | Entregar 3 UN | 7 UN | Una salida |
| Existencia 7 | Intentar entregar 8 UN | 7 UN | Rechazo sin nuevo movimiento |

El último rechazo es una parte del funcionamiento correcto. Explica por qué no debe cambiar ni saldo ni historial. Escribe también que un usuario de consulta no puede registrar operaciones.

## Paso 3. Redacta tres historias de usuario

Usa la fórmula «Como…, quiero…, para…». Elige una historia de producto, otra de movimiento y otra de consulta. Para cada una escribe al menos dos criterios que puedas comprobar. Evita «que funcione bien»: indica datos, acción y resultado.

Ejemplo: «Como operador, quiero registrar una salida para actualizar la disponibilidad». Criterios: retirar tres de diez deja siete; retirar ocho de siete se rechaza sin cambios. Si la IA propone criterios distintos, contrástalos con las reglas del caso antes de aceptarlos.

## Paso 4. Describe los datos sin inventar campos del kit

Completa un diccionario con al menos seis campos reales, su significado, ejemplo y restricción. Puedes combinar campos de producto y movimiento.

| Campo | Ejemplo | Regla que debes reconocer |
|---|---|---|
| `codigo` | PRUEBA-001 | Identifica un producto; no se repite |
| `nombre` | Caja de práctica | Texto breve para reconocerlo |
| `unidad` | UN | Seleccionar UN, KG o LT |
| `minimo` | 8.00 | Valor no negativo |
| `existencia` | 7.00 | Se calcula mediante movimientos |
| `tipo` | E o S | Entrada o salida |
| `cantidad` | 3.00 | Positiva, hasta dos decimales |
| `motivo` | Entrega de práctica | Explica la operación |

Fecha y usuario se incorporan al registrar. El formulario de producto no pide una existencia inicial: empieza en cero. No añadas un campo solo porque aparece en una propuesta generada; identifícalo como ampliación si todavía no existe.

## Paso 5. Prepara tres bocetos comprensibles

Dibuja tablero, formulario de producto y formulario de movimiento. Escribe títulos, campos, acción principal y respuesta esperada. En el tablero incluye producto, unidad y existencia. En el movimiento indica entrada o salida, cantidad y motivo.

Añade un mensaje de rechazo y la acción para resolverlo: comprobar producto y saldo. No hace falta diseñar cada color ni copiar la estética de una aplicación comercial. El propósito es que el usuario encuentre la operación y entienda la respuesta.

## Paso 6. Pide una revisión y conserva tu decisión

Utiliza el asistente disponible o la revisión guiada de la plantilla. Puedes partir de esta instrucción y adaptarla:

```text
Contexto: prototipo docente local de Andina Distribución.
Objetivo: revisar tres historias y sus criterios, sin escribir código.
Alcance: productos, entradas, salidas, existencias e historial.
Límites: no stock negativo; existencia calculada; roles consulta y operación.
Comprueba: recibir 10, retirar 3 y rechazar una salida de 8 cuando quedan 7.
Primero señala dudas y propone un plan. No inventes funciones existentes.
```

Copia una recomendación, explica si la aceptaste y por qué. Si no hay modelo, un compañero o docente puede revisar la instrucción con la misma lista. Identifica honestamente esa modalidad: no inventes una conversación ni capturas.

> [!TIP]
> La decisión es tuya: una sugerencia puede ser razonable y ampliar demasiado el ejercicio. Conserva lo que facilita comprobar el proceso actual.

## Resuelve dificultades y comprueba tu avance

| Si ocurre esto | Revisa esto |
|---|---|
| El dibujo tiene demasiadas funciones | Deja las imprescindibles y mueve otras a evolución |
| No sabes qué poner en un campo | Busca su nombre en el diccionario y la guía |
| Dos criterios se contradicen | Repite el cálculo con el mismo producto y unidad |
| La propuesta solo habla de pantallas | Añade regla, saldo e historial esperado |

**Glosario:** una historia describe una necesidad; un criterio establece cómo comprobarla; un diccionario explica los datos; un alcance limita la versión.

**Punto de control:** explica sin leer qué ocurre al recibir diez, retirar tres e intentar retirar ocho. Señala qué dato cambia y qué evidencia queda. Si no puedes hacerlo, ajusta el flujo antes de pasar a la instalación.

## Entrega y criterios de revisión

Entrega una ficha PDF o documento con problema, usuarios, flujo, diccionario, tres bocetos, tres historias con criterios e instrucción revisada. Puedes reunirlo en un solo archivo. El chat por sí solo no sustituye el diseño.

| Criterio | Puntos |
|---|---|
| Problema y usuario claros | 20 |
| Flujo coherente | 20 |
| Diccionario de datos | 20 |
| Criterios comprobables | 25 |
| Alcance e instrucción razonada | 15 |
| Total | 100 |

Se requiere al menos **70/100**. Conserva estos materiales: los usarás para construir y probar, sin volver a redactarlos desde cero.

- [Django Girls: cómo funciona internet](https://tutorial.djangogirls.org/es/how_the_internet_works/).
- [Django: proyecto y aplicación](https://docs.djangoproject.com/es/5.2/intro/tutorial01/).
'''),
    _wiki(r'''
## Laboratorio 2: pon en marcha tu copia y realiza un primer cambio

**Tiempo incluido en la unidad: 4 horas y 50 minutos.** Abrirás el kit en tu computador, reconocerás sus archivos y cambiarás una ayuda o título de pantalla. No construirás otra aplicación. Reserva tiempo para instalar, explorar, comprobar el cambio y registrar una dificultad con su solución.

![Archivos y responsabilidades del proyecto](/static/portal/img/cursos/logistica-ia/mapa-proyecto.svg)

## Paso 1. Sitúate en la carpeta correcta

Extrae el ZIP y abre la carpeta `andina-distribucion`. Debes ver `README.md`, `manage.py` y `requirements.txt`. Abre una terminal allí. Los comandos siguientes se ejecutan en esa carpeta, no dentro del proyecto institucional ni dentro de `inventario`.

Comprueba que tienes Python 3.11; es la versión con la que se ha verificado la práctica. El README también contempla 3.12. Si no está instalado, utiliza la descarga oficial y vuelve a abrir la terminal. No cambies versiones del kit por instrucciones de un video distinto.

## Paso 2. Prepara la aplicación en Windows

En PowerShell, ejecuta **una línea cada vez**. Si una línea falla, detente y revisa su mensaje antes de seguir.

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py preparar_demo
.venv/Scripts/python.exe manage.py crear_usuario operador --rol operacion
.venv/Scripts/python.exe manage.py crear_usuario lector --rol consulta
.venv/Scripts/python.exe manage.py test inventario
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8001
```

Los comandos de cuentas solicitan una contraseña propia y su confirmación. Al escribirla puede no verse ningún carácter: es normal. Utiliza contraseñas distintas de tus servicios personales y no las incluyas en las evidencias. Si usas 3.12, sustituye únicamente la primera línea por `py -3.12 -m venv .venv` antes de crear el entorno.

## Paso 2 alternativo. Prepara la aplicación en Linux

Sigue este bloque si trabajas en Linux; no ejecutes también el de Windows. Comprueba que `python3 --version` indica 3.11 o 3.12.

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py preparar_demo
.venv/bin/python manage.py crear_usuario operador --rol operacion
.venv/bin/python manage.py crear_usuario lector --rol consulta
.venv/bin/python manage.py test inventario
.venv/bin/python manage.py runserver 127.0.0.1:8001
```

Las rutas explícitas utilizan siempre el Python del entorno. No necesitas activar el entorno ni modificar la política de ejecución de PowerShell. Las migraciones preparan tablas; `preparar_demo` carga datos ficticios; las pruebas comprueban reglas; el último comando inicia el servidor.

## Paso 3. Abre el navegador y comprueba la base

Abre [la aplicación local](http://127.0.0.1:8001/). Mantén abierta la terminal. Ingresa como operador y recorre tablero, catálogo e historial. En una base nueva, antes de otras prácticas, debes encontrar:

| Producto | Existencia | Mínimo |
|---|---|---|
| AD-001 | 17.00 UN | 10.00 |
| AD-002 | 20.00 UN | 30.00 |
| AD-003 | 9.25 KG | 5.00 |
| AD-004 | 4.00 UN | 8.00 |

Son cuatro productos y seis movimientos. El tablero inicial presenta dos productos bajo mínimo y ninguno sin existencia. Si ya hiciste operaciones, calcula el estado actual; no lo fuerces para que coincida con esta tabla. Repetir `preparar_demo` no duplica la carga ni elimina tus operaciones posteriores.

## Paso 4. Reconoce cinco archivos

Abre `manage.py`, `inventario/models.py`, `inventario/forms.py`, `inventario/services.py` y `templates/inventario/tablero.html`. En tu bitácora escribe qué responsabilidad tiene cada uno y un elemento que reconoces. No necesitas explicar toda la sintaxis.

Pide a la IA que explique un solo archivo, con los nombres realmente presentes. Contrasta la explicación con el texto abierto. Si cita una función inexistente, solicita que rectifique. Puedes utilizar `prompts/02_explicar_codigo.md` como punto de partida y conservar tu comprobación en la bitácora.

## Paso 5. Realiza una mejora visible y acotada

Guarda una copia del archivo antes de cambiarlo, o un commit si ya utilizas Git. En `templates/inventario/tablero.html` localiza el título y cámbialo por **Control de existencias del almacén docente**. Añade una frase de ayuda que explique que la existencia cambia mediante movimientos. Mantén nombres de campos, enlaces y bloques de plantilla.

Actualiza el navegador y compara antes y después. Si aparece un error, recupera la copia y solicita un cambio más pequeño. No aceptes que el asistente reescriba modelos o permisos para modificar un título.

> [!NOTE]
> Para ejecutar pruebas mientras el servidor funciona, abre otra terminal en la misma carpeta. También puedes detenerlo con Ctrl+C, ejecutar la prueba y volver a iniciar únicamente el comando `runserver`.

## Paso 6. Registra un producto y contrasta los roles

Con operador crea `MAN-01`, nombre `Material de práctica`, unidad `UN` y mínimo `3.00`. La existencia debe quedar en cero. Busca el producto en el tablero. Cierra sesión e ingresa como lector: debe consultar, pero no registrar productos ni movimientos.

Guarda evidencias con el código y el resultado, sin mostrar contraseñas. Después del cambio de pantalla vuelve a ejecutar `manage.py test inventario` con el Python de tu sistema según los bloques anteriores. Anota el resumen real y describe una prueba en lenguaje sencillo.

## Si algo falla, diagnostica antes de cambiar

| Situación | Comprobación y remedio |
|---|---|
| No encuentra manage.py | Abre la terminal en la carpeta que lo contiene |
| No encuentra Django | Instala requisitos con el Python de .venv |
| Falta una tabla | Ejecuta migrate antes de cargar o abrir |
| La contraseña parece no escribirse | Termina de introducirla y pulsa Enter |
| El navegador no conecta | Revisa que runserver sigue activo y usa 8001 |
| El puerto está ocupado | Elige otro puerto local y abre exactamente esa dirección |
| El cambio rompe la plantilla | Recupera la copia y modifica un fragmento menor |

No inventes un fallo para la entrega. Si no tuviste problemas, documenta un mensaje normal y cómo reconociste que el paso terminó, o una comprobación preventiva.

### Glosario y punto de control

**Entorno** reúne bibliotecas; **migración** prepara tablas; **terminal** ejecuta órdenes; **servidor local** responde en tu computador. Continúa cuando puedas detener y reiniciar la aplicación, señalar un archivo de datos y otro de pantalla, y explicar por qué el lector no registra movimientos.

## Entrega y revisión

Entrega captura del arranque y tablero, mapa de cinco archivos, antes y después del cambio, comprobación de MAN-01, roles y pruebas. Incluye una bitácora breve de decisiones y diagnóstico. No adjuntes `.venv`, claves ni la base local como sustituto del código.

| Criterio | Puntos |
|---|---|
| Entorno y arranque reproducible | 30 |
| Reconocimiento de componentes | 20 |
| Cambio pequeño comprobado | 25 |
| Recuperación y bitácora | 25 |
| Total | 100 |

Se requiere **70/100**. Esta misma copia continuará en la siguiente unidad.

- [Python: entornos virtuales](https://docs.python.org/es/3.11/library/venv.html).
- [Django Girls: instalación de Django](https://tutorial.djangogirls.org/es/django_installation/).
- [Django: primer proyecto](https://docs.djangoproject.com/es/5.2/intro/tutorial01/).
'''),

    _wiki(r'''
## Laboratorio 3: demuestra que las existencias respetan las reglas

**Tiempo incluido en la unidad: 4 horas y 50 minutos.** Registrarás operaciones, provocarás rechazos controlados y realizarás una mejora pequeña. Utiliza la copia de la unidad 2 y datos ficticios. No necesitas otra instalación ni un nuevo modelo de IA.

![Regla de una salida y conservación del saldo](/static/portal/img/cursos/logistica-ia/regla-stock.svg)

## Paso 1. Prepara una prueba que puedas repetir

Abre `guias/unidad_03.md`, `datos/movimientos_ejemplo.csv` y tu ficha. El archivo de movimientos es un guion para introducir operaciones manualmente: **no es un archivo admitido por el importador de productos**.

Inicia la aplicación desde la carpeta de `manage.py`.

Windows:

```powershell
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8001
```

Linux:

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8001
```

Abre [el tablero local](http://127.0.0.1:8001/) e ingresa como operador. Crea `PRUEBA-001`, nombre `Caja de comprobación`, unidad `UN` y mínimo `8.00`. Debe aparecer con existencia cero. Si ya utilizaste ese código en otra práctica, elige uno nuevo como `PRUEBA-002` y sustitúyelo en todas tus evidencias; no borres movimientos para hacer coincidir la tabla.

## Paso 2. Ejecuta el recorrido principal

Antes de cada operación anota saldo y cantidad de movimientos **del producto de prueba**. El historial contiene también registros de otros productos. No confundas el total del historial con las operaciones de esta secuencia.

| Acción en orden | Motivo de ejemplo | Saldo esperado | Movimientos del producto |
|---|---|---|---|
| Crear producto | No corresponde movimiento | 0 UN | 0 |
| Entrada de 10 | Recepción de práctica | 10 UN | 1 |
| Salida de 3 | Entrega de práctica | 7 UN | 2 |
| Intentar salida de 8 | Comprobación de rechazo | 7 UN | 2 |

Registra producto, tipo, cantidad y motivo en cada formulario. Comprueba el mensaje, vuelve al tablero y consulta el historial. En el último intento debe aparecer un rechazo y conservarse el estado anterior. No cambies el criterio si observas un saldo incorrecto: documenta el fallo para corregirlo.

## Paso 3. Comprueba entradas incorrectas

Con el mismo producto intenta cantidades cero, negativas y con más de dos decimales. Anota el dato exacto utilizado, lo esperado y el resultado real. La cantidad debe ser positiva y tener hasta dos decimales; no se debe redondear silenciosamente una precisión que el formulario no admite.

Intenta crear otro producto con el mismo código. Debe rechazarse sin duplicar el registro. Comprueba un nombre vacío y una unidad fuera de las opciones admitidas utilizando las pruebas preparadas, sin manipular permisos ni cambiar el modelo. El navegador puede impedir una entrada antes de enviarla; las pruebas automáticas también comprueban reglas del servidor.

| Caso | Qué debe ocurrir | Qué observar |
|---|---|---|
| Cantidad 0 | Rechazo | Saldo e historial iguales |
| Cantidad -1 | Rechazo | No aparece una salida negativa |
| Cantidad 1.234 | Rechazo | No se acepta precisión adicional |
| Código repetido | Rechazo | Un solo producto con ese código |

## Paso 4. Contrasta permisos con una dirección directa

Cierra la sesión operador e ingresa como lector. Revisa tablero e historial: debe poder consultarlos. Después abre [registro de movimiento](http://127.0.0.1:8001/movimientos/nuevo/). El resultado esperado es acceso restringido, normalmente una respuesta 403, y ninguna operación nueva.

Ocultar un botón no es toda la comprobación. Explica por qué el servidor debe rechazar también la dirección directa. No concedas al lector permisos de operación para eliminar el rechazo: en este caso el rechazo demuestra que la regla funciona.

> [!WARNING]
> Si el lector consigue escribir o aparece una existencia negativa, detén la mejora y corrige o recupera la versión anterior. Son condiciones críticas que necesitan resolverse antes de aprobar.

## Paso 5. Sigue una regla en los archivos

Abre `inventario/forms.py` y `inventario/services.py`. Busca el tratamiento de cantidad y salida. Pide una explicación sencilla de ese fragmento, utilizando `prompts/02_explicar_codigo.md` si necesitas una guía. Señala qué dato entra, qué condición se comprueba y qué sucede si no se cumple.

No necesitas comprender cada instrucción interna. Sí debes poder explicar: «La salida se permite cuando la cantidad es válida y hay disponibilidad; saldo e historial cambian juntos». Una frase de la IA no demuestra esa regla: relaciónala con la prueba de 10, 3 y 8 que acabas de ejecutar.

## Paso 6. Mejora una ayuda y vuelve a comprobar

Elige un cambio pequeño: explicar cómo buscar por código o nombre, aclarar la unidad de la cantidad o mejorar una ayuda del formulario. No añadas varias bodegas ni modifiques directamente la existencia. Guarda una copia antes y utiliza `prompts/03_mejorar_mensaje.md` como apoyo.

Pide al asistente un plan breve, los archivos que propone modificar y la prueba que harás después. Revisa el resultado y repite el recorrido principal con un producto nuevo. Guarda antes y después de la ayuda y el saldo final comprobado.

En una segunda terminal, ejecuta las pruebas incluidas.

Windows:

```powershell
.venv/Scripts/python.exe manage.py test inventario
```

Linux:

```bash
.venv/bin/python manage.py test inventario
```

Anota el resumen real. Elige una prueba de `inventario/tests.py` y explica qué comportamiento protege. Que los casos incluidos pasen aporta evidencia; no permite afirmar que se probaron todas las situaciones posibles.

## Errores frecuentes y recuperación

| Dificultad | Cómo resolverla |
|---|---|
| El saldo inicial no es cero | Usa un producto exclusivo y anota su código |
| El intento rechazado cambia el historial | Conserva evidencia y recupera o corrige el cambio |
| Confundes UN con KG | Repite con un único producto y unidad |
| La IA propone escribir la existencia | Rechaza esa propuesta; utiliza movimientos |
| Las pruebas fallan tras cambiar una ayuda | Revisa el cambio concreto y vuelve a la copia si procede |

**Glosario:** validación comprueba datos; permiso decide qué puede hacer una cuenta; historial registra hechos; regresión comprueba que un cambio conserva funciones anteriores.

## Punto de control, entrega y rúbrica

Reúne al menos ocho casos con dato inicial, acción, esperado, obtenido y evidencia. Explica una operación correcta, un rechazo de datos y un rechazo de permisos. Incluye capturas del saldo e historial, cambio realizado, pruebas automáticas y decisión tomada con IA o revisión guiada.

| Criterio | Puntos |
|---|---|
| Entradas y salidas verificadas | 30 |
| Validaciones y conservación del saldo | 30 |
| Permisos e historial | 20 |
| Mejora acotada con evidencia | 20 |
| Total | 100 |

La nota mínima es **70/100**, con corrección de fallos críticos. Utilizarás la misma tabla en la revisión final, ampliándola sin duplicar documentos.

- [Django: validación de formularios](https://docs.djangoproject.com/es/5.2/ref/forms/validation/).
- [Django: usuarios y permisos](https://docs.djangoproject.com/es/5.2/topics/auth/default/).
- [Django: pruebas](https://docs.djangoproject.com/es/5.2/topics/testing/overview/).
'''),
    _wiki(r'''
## Laboratorio 4: conecta datos, indicadores y una consulta MCP

**Tiempo incluido en la unidad: 4 horas y 50 minutos.** Trabajarás con importación, exportación y la integración preparada. La conexión no exige contratar un modelo. Primero comprobarás el protocolo con el cliente incluido y después, si hay un asistente compatible disponible, contrastarás una conversación real.

![De los registros a indicadores comprensibles](/static/portal/img/cursos/logistica-ia/datos-indicadores.svg)

## Paso 1. Registra tu estado inicial y exporta

Abre tu aplicación con operador. Anota número de productos, productos bajo mínimo y productos sin existencia. Conserva una exportación antes de importar. El tablero y la exportación representan el catálogo completo; una búsqueda por código filtra la lista visible, pero no convierte los indicadores en un resumen de ese subconjunto.

Abre el archivo exportado con un editor o una hoja de cálculo y reconoce sus seis campos: `codigo`, `nombre`, `unidad`, `minimo`, `existencia` y `bajo_minimo`. La última columna utiliza SI o NO. No sumes cantidades de UN, KG y LT como si representaran una misma magnitud.

## Paso 2. Comprueba el rechazo de un archivo inválido

Abre `datos/productos_invalidos.csv`. Identifica códigos repetidos, unidad o cantidades no admitidas y otros datos incorrectos incluidos. Intenta importarlo desde la aplicación. Anota los errores que realmente aparecen y busca después `AD-201`: no debe existir.

El importador comprueba el archivo entero antes de confirmar la carga. Una primera fila válida no debe guardarse si las demás contienen errores. Compara también el número de productos anterior y posterior. Un mensaje de error sin comprobar el catálogo no demuestra ausencia de carga parcial.

## Paso 3. Importa una vez el catálogo válido

Abre `datos/productos_validos.csv`. Su cabecera exacta y orden son:

```csv
codigo,nombre,unidad,minimo
```

Utiliza separador coma, texto UTF-8 y punto decimal. El importador admite hasta 100 filas y 1 MB, exige códigos nuevos y no actualiza productos existentes. No agregues existencia a esa cabecera: cada nuevo producto empieza en cero y cualquier cantidad recibida requiere un movimiento.

Importa el archivo. Deben aparecer AD-101 a AD-104 con existencia cero. Intenta importarlo otra vez: los códigos existentes deben provocar rechazo, sin duplicación. Si ya lo habías usado, documenta ese estado; no borres datos para simular una primera carga.

| Evidencia | Comprobación |
|---|---|
| Archivo inválido | Rechazado completo; AD-201 ausente |
| Archivo válido, primera carga | Cuatro nuevos productos, todos en cero |
| Mismo archivo, segunda carga | Rechazo por códigos repetidos |
| Productos originales | Saldos conservados |

Solo en una demo nueva sin otras prácticas, después de la carga válida habrá ocho productos, seis bajo mínimo y cuatro sin existencia. Si creaste MAN-01 o productos de prueba, calcula los totales de tu catálogo actual.

## Paso 4. Explica indicadores con ejemplos de frontera

Crea tres productos exclusivos con unidad UN: `KPI-A` con mínimo 8, `KPI-B` con mínimo 5 y `KPI-C` con mínimo 0. Registra una entrada de 7 para A y otra de 5 para B. Deja C en cero. Usa otros códigos si ya existen y anota la sustitución.

| Producto de prueba | Existencia y mínimo | Interpretación |
|---|---|---|
| A | 7 y 8 | Está bajo mínimo |
| B | 5 y 5 | Igualdad: no está bajo mínimo |
| C | 0 y 0 | Sin existencia; no está bajo mínimo |

En este subconjunto hay tres productos, uno bajo mínimo y uno sin existencia. El tablero muestra los totales **de toda la base**; explica la diferencia. La barra visual limitada al 100 % compara existencia y mínimo, no representa capacidad física del almacén ni calcula automáticamente una compra.

## Paso 5. Instala y verifica MCP sin modelo

Detén el servidor web con Ctrl+C y evita operaciones simultáneas mientras compruebas que la base no cambia. En la misma carpeta de `manage.py` instala la dependencia opcional y ejecuta el cliente preparado.

Windows:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-mcp.txt
.venv/Scripts/python.exe verificar_mcp.py
```

Linux:

```bash
.venv/bin/python -m pip install -r requirements-mcp.txt
.venv/bin/python verificar_mcp.py
```

El resultado esperado termina indicando: **MCP verificado: dos herramientas de consulta, entrada inválida rechazada y base sin cambios.** El cliente descubre herramientas, consulta AD-001 y productos bajo mínimo, rechaza un código inválido y compara la huella de la base. No utiliza una API de IA ni necesita una suscripción.

![Recorrido de una consulta de solo lectura](/static/portal/img/cursos/logistica-ia/arquitectura-mcp.svg)

Las herramientas son `consultar_existencias` y `productos_bajo_minimo`. La primera admite un código opcional; la segunda aplica existencia menor que mínimo. El servidor usa consultas predefinidas y SQLite en lectura; no recibe SQL para ejecutarlo ni hereda los roles de la sesión web.

## Paso 6. Conecta un asistente si está disponible

Genera la configuración con las rutas reales de tu copia.

Windows:

```powershell
.venv/Scripts/python.exe preparar_opencode.py
```

Linux:

```bash
.venv/bin/python preparar_opencode.py
```

El script crea `opencode.json` y se detiene si ya existe; no lo sobrescribas sin revisar tu configuración anterior. Instala o abre OpenCode siguiendo su documentación oficial y el README. Desde la carpeta del kit puedes comprobar la conexión con:

```text
opencode mcp list
```

Utiliza `prompts/04_consulta_mcp.md` o pide: «Usa Andina para consultar AD-001 y explicar su existencia y mínimo. No ejecutes comandos ni cambies archivos». Después consulta los productos bajo mínimo. Conserva herramienta utilizada, entrada y datos devueltos. Reinicia la web y contrasta con el tablero.

Solicita registrar una salida de una unidad, **sin autorizar comandos ni edición**. Explica que este MCP no ofrece escritura y comprueba que el historial sigue igual. El host puede disponer de otras herramientas: no las autorices para eludir el límite del ejercicio.

> [!NOTE]
> Sin modelo compatible, entrega la prueba de protocolo y explica esa modalidad. No afirmes que ocurrió una conversación. Las dos modalidades requieren verificar datos y límites; el proveedor o precio no da puntos adicionales.

## Diagnóstico y punto de control

| Situación | Primera comprobación |
|---|---|
| CSV válido es rechazado | Cabecera exacta y códigos ya existentes |
| Totales distintos del ejemplo | Productos de prácticas anteriores |
| Falta el módulo MCP | Instala requirements-mcp.txt con el Python de .venv |
| No encuentra la base | Migraciones y preparar_demo en esta copia |
| Servidor MCP parece esperar | Utiliza el cliente de prueba o el host configurado |
| Respuesta de IA cambia una cantidad | Compara datos estructurados y resumen |

**Glosario:** CSV intercambia tablas; indicador resume registros; herramienta MCP ejecuta una función definida; solo lectura permite consultar sin modificar.

Continúa cuando expliques igualdad y bajo mínimo, distingas exportación de importación y demuestres las dos consultas. Identifica quién consulta la base y quién redacta la explicación.

## Entrega y revisión

Entrega exportación, errores observados, indicadores antes y después, contraste de los tres productos y evidencia MCP identificando la modalidad. Explica los límites del catálogo y la ausencia de escritura.

| Criterio | Puntos |
|---|---|
| Importación y rechazo completo | 25 |
| Indicadores interpretados | 25 |
| Exportación contrastada | 15 |
| Consultas MCP verificadas | 25 |
| Límites explicados | 10 |
| Total | 100 |

Se requiere **70/100**. No compartas claves ni `opencode.json` con rutas privadas como parte de la entrega.

- [MCP: arquitectura](https://modelcontextprotocol.io/docs/learn/architecture).
- [SDK oficial de Python](https://github.com/modelcontextprotocol/python-sdk).
- [OpenCode: servidores MCP](https://opencode.ai/docs/mcp-servers/).
'''),

    _wiki(r'''
## Laboratorio 5: comprueba tu versión y prepara una entrega reproducible

**Tiempo incluido en la unidad: 3 horas.** Reunirás pruebas, corregirás lo necesario y ensayarás el recorrido. La actividad de proyecto final dispone después de **110 minutos** para preparar su entrega. Juntas conservan los 290 minutos de trabajo práctico de la unidad; no necesitas desarrollar una aplicación distinta.

![Revisión, corrección y entrega del prototipo](/static/portal/img/cursos/logistica-ia/pruebas-entrega.svg)

## Paso 1. Organiza las evidencias que ya tienes

Abre `guias/unidad_05.md`, `datos/pruebas_aceptacion.csv`, `plantillas/proyecto_final.md`, `plantillas/rubrica_detallada.md` y tu bitácora. Reúne ficha de diseño, cambios de las unidades 2 y 3, importaciones, exportación y consultas MCP.

Conserva una copia de la versión que vas a revisar. Escribe fecha, carpeta y cambios incluidos. Si trabajas con otra persona, acuerden qué copia es la de entrega; dos carpetas de nombre parecido pueden contener funciones diferentes.

**Resultado esperado:** puedes reconocer qué venía en la plantilla, qué modificaste y qué falta comprobar, sin buscarlo en una conversación extensa.

## Paso 2. Completa una matriz de al menos diez casos

La plantilla contiene columnas `id`, `caso`, `precondicion`, `accion`, `esperado`, `observado`, `estado` y `evidencia`. Completa las vacías y conserva el resultado real. Un caso rechazado correctamente puede tener estado aprobado: el éxito consiste en cumplir el resultado esperado, no en permitir cualquier operación.

Revisa la precondición antes de reutilizar una fila. Los ejemplos de demo nueva no describen automáticamente tu base después de varias prácticas. Puedes preparar una copia nueva o adaptar cantidades y códigos a un producto exclusivo, dejando constancia del cambio.

| Caso que debes cubrir | Resultado que comprobarás |
|---|---|
| Producto nuevo y código repetido | Alta en cero; segundo código igual rechazado |
| Entrada y salida válida | Cálculo e historial coherentes |
| Salida superior al saldo | Rechazo sin cambios |
| Cantidad cero, negativa o demasiados decimales | Rechazo sin cambios |
| Cuenta de consulta | Lectura permitida y escritura restringida |
| CSV inválido | Archivo rechazado completo |
| CSV válido | Altas en cero, sin duplicación |
| Indicador en igualdad | Existencia igual al mínimo no está bajo mínimo |
| Exportación | Datos del catálogo completo |
| Consulta MCP | Datos contrastados y base sin cambios |

Puedes separar estos grupos en más filas. Señala dónde está cada captura o salida de terminal. No completes todos con «funciona»: escribe saldo, cantidad de registros o rechazo observado.

## Paso 3. Ejecuta las pruebas automáticas y comprende una

Desde la carpeta de `manage.py` ejecuta el comando correspondiente.

Windows:

```powershell
.venv/Scripts/python.exe manage.py test inventario
```

Linux:

```bash
.venv/bin/python manage.py test inventario
```

Guarda el resumen real. Abre `inventario/tests.py`, selecciona una prueba y explica qué prepara, qué acción ejecuta y qué comprueba. Puedes pedir ayuda a la IA, pero debes contrastar su explicación con ese archivo.

Para repetir la verificación MCP, detén el servidor web y ejecuta el cliente incluido. No hagas operaciones simultáneas mientras compara la base.

Windows:

```powershell
.venv/Scripts/python.exe verificar_mcp.py
```

Linux:

```bash
.venv/bin/python verificar_mcp.py
```

La dependencia de MCP debe estar instalada desde la unidad 4. Identifica si tu evidencia corresponde al protocolo sin modelo, a una demostración docente o a un asistente real. No intercambies esas etiquetas.

## Paso 4. Corrige lo mínimo y repite las reglas

Si hay un fallo, registra primero lo que esperabas y lo que ocurrió. Solicita una explicación con el fragmento real, un cambio acotado y una comprobación posterior. Guarda la versión anterior. No elimines una prueba que muestra un problema ni aceptes modificaciones generales que no comprendes.

Después de corregir, repite el caso que fallaba, entradas, salidas, rechazo por saldo y permisos. Revisa dos mejoras justificadas realizadas durante el curso, por ejemplo la ayuda del tablero y la explicación de cantidad. No inventes fallos ni agregues funciones para llenar la entrega: explica el valor y la comprobación de esas mejoras existentes.

> [!WARNING]
> Antes de aprobar deben corregirse los fallos que permiten stock negativo o escribir sin permiso. Superar 70/100 en otros aspectos no reemplaza esa corrección.

## Paso 5. Comprueba que otra persona pueda iniciar la aplicación

Escribe una guía breve con requisitos, carpeta, comandos y dirección local. Pide a un compañero que la siga o utiliza una carpeta nueva con el código final. No sobrescribas tu copia de trabajo ni copies `.venv` o una base privada para evitar la instalación.

En una carpeta nueva que ya contenga los archivos del proyecto, prepara Windows con:

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py preparar_demo
.venv/Scripts/python.exe manage.py crear_usuario operador --rol operacion
.venv/Scripts/python.exe manage.py crear_usuario lector --rol consulta
.venv/Scripts/python.exe manage.py test inventario
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8001
```

Para Linux con Python 3.11 o 3.12 disponible:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py preparar_demo
.venv/bin/python manage.py crear_usuario operador --rol operacion
.venv/bin/python manage.py crear_usuario lector --rol consulta
.venv/bin/python manage.py test inventario
.venv/bin/python manage.py runserver 127.0.0.1:8001
```

Abre [la aplicación local](http://127.0.0.1:8001/). Las cuentas llevan contraseñas propias introducidas en los prompts. Comprueba el arranque y una operación. Añade a la guía los pasos opcionales de MCP del laboratorio 4 si vas a demostrar la conexión en esta copia. Corrige cualquier instrucción que dependa de una ruta particular de tu computador.

## Paso 6. Ensaya la demostración y prepara el proyecto

Organiza un recorrido de cinco a ocho minutos: problema, producto, entrada, salida, rechazo, indicador, MCP, mejora y límites. Utiliza un producto de demostración exclusivo. Por ejemplo, recibe 10, recibe 6, retira 4: quedan 12. Intentar retirar 13 debe conservar 12 y el historial previo.

Explica por qué un producto en el mínimo no activa bajo mínimo, por qué el CSV exportado no se importa directamente y qué herramientas ofrece tu MCP. Si no utilizaste un modelo, muestra el cliente de prueba sin simular una conversación.

Prepara la lista de archivos para el proyecto final: código, requisitos, migraciones, datos ficticios, guía y evidencias. Excluye `.venv`, `db.sqlite3`, `.secreto-local`, `opencode.json`, credenciales y datos reales. La guía debe permitir reconstruir la práctica, no depender de tu sesión abierta.

## Diagnóstico, glosario y punto de control

| Problema de revisión | Acción útil |
|---|---|
| La fila esperaba una base nueva | Revisa precondición y adapta el caso documentadamente |
| La captura no identifica el dato | Incluye código, unidad y resultado |
| El cambio rompe una función anterior | Recupera o corrige y repite la regresión |
| Otra persona no logra iniciar | Sigue la guía con ella y corrige el paso ambiguo |
| La presentación solo muestra diseño | Añade una operación y un rechazo comprobados |

**Glosario:** evidencia demuestra un resultado; regresión revisa funciones anteriores; reproducible significa que otra persona puede repetir; limitación describe lo que todavía no resuelve.

**Punto de control:** alguien que no conoce tu chat puede seguir la guía, comprender diez casos y distinguir tu aportación de la plantilla. Debes poder explicar una prueba, una decisión de IA o revisión guiada y un límite del prototipo.

## Entrega del laboratorio y aprobación

Entrega el informe breve, matriz de al menos diez casos, resumen de pruebas, dos mejoras justificadas y correcciones verificadas. La aplicación y la presentación se reúnen en la siguiente actividad de proyecto final; no repitas documentos que ya puedes referenciar.

| Criterio del laboratorio | Puntos |
|---|---|
| Pruebas manuales del recorrido | 35 |
| Permisos y entradas incorrectas | 25 |
| Correcciones y regresión | 25 |
| Informe comprensible | 15 |
| Total | 100 |

Se requiere **70/100** y resolver los fallos críticos. El proyecto final conserva su propia rúbrica de 100 puntos y mínimo 70; este laboratorio no lo sustituye ni reemplaza los quizzes. La plataforma registra la revisión de la entrega: no analiza automáticamente el código para certificarlo.

- [Django: pruebas](https://docs.djangoproject.com/es/5.2/topics/testing/overview/).
- [Django: lista de despliegue](https://docs.djangoproject.com/es/5.2/howto/deployment/checklist/).
- [GitHub: guardar y explicar cambios](https://docs.github.com/es/get-started/start-your-journey/hello-world).
'''),
]
