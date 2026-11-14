# Unidad 1 · De la necesidad logística al diseño de una aplicación

**Unidad: 8 horas en total**, incluyendo las lecturas, videos, archivos, laboratorio y evaluación del aula. **Laboratorio guiado: 4 h 50 min.** Meta: explicar un problema operativo y traducirlo a datos, reglas, pantallas y criterios de aceptación. No hace falta escribir código en esta unidad.

## Idea central

Una aplicación registra hechos y aplica reglas. En un inventario, un producto describe qué se administra; una entrada o salida registra un hecho; la existencia es el saldo resultante. Un tablero resume esos datos. La IA ayuda a describir o construir componentes, pero no determina si un saldo es correcto: eso se comprueba con operaciones conocidas.

Un navegador muestra la pantalla. Django recibe la solicitud, comprueba permisos y datos, ejecuta la operación y devuelve una respuesta. La base de datos conserva productos y movimientos. Aunque una persona cambie el formulario desde el navegador, las reglas deben comprobarse nuevamente en el servidor.

## Caso Andina Distribución

El almacén ficticio maneja materiales de empaque. Una persona recibe mercadería, otra consulta disponibilidad y una tercera autoriza entregas. Los archivos dispersos provocan códigos repetidos y diferencias entre registros. La primera aplicación debe registrar catálogo, entradas, salidas e historial, mostrando alertas cuando la existencia sea menor que el mínimo.

El mínimo es un dato de práctica; no es una recomendación comercial calculada. El prototipo no pronostica demanda ni calcula stock de seguridad. UN, KG y LT son unidades diferentes: no se suman para obtener un único stock global.

## Recorrido de trabajo

1. **Comprender el caso:** identifica usuarios, decisiones, problemas y tres ejemplos concretos de error.
2. **Diseñar una primera versión:** completa plantillas/ficha_proyecto.md. Selecciona cinco funciones: catálogo, movimiento, existencias, historial y reporte. Deja funciones futuras fuera del alcance.
3. **Describir datos:** completa plantillas/diccionario_datos.csv. Explica por qué el código debe ser único y la cantidad debe admitir decimales.
4. **Bocetar pantallas:** dibuja tablero, formulario de producto y formulario de movimiento. Puedes usar papel; muestra una ruta de entrada y otra de error.
5. **Dar instrucciones a una IA o a un compañero:** usa prompts/01_diseno.md y evalúa si la respuesta respeta el alcance. Si no dispones de modelo, intercambia instrucciones y revisa con el docente.
6. **Comprobar y entregar:** escribe criterios observables y responde la comprobación final.

## Reglas mínimas del proyecto

- Código de producto único, nombre no vacío y unidad válida.
- Cantidad positiva con hasta dos decimales.
- Una salida no puede superar la existencia.
- Entrada y salida conservan usuario, fecha, motivo y producto.
- El rol de consulta no registra operaciones.
- La importación de catálogo no modifica stock y no guarda filas si el archivo contiene errores.

**Ejemplo de criterio:** dado un producto con 4.00 UN, al solicitar una salida de 5.00 UN, se muestra stock insuficiente y el saldo y el historial permanecen iguales.

## Entrega

Ficha de proyecto, diccionario de datos, tres bocetos y cinco criterios de aceptación. Explica una diferencia entre dato, regla e indicador. Conserva una versión de la instrucción utilizada y una corrección que hayas hecho a la respuesta.

## Comprueba tu comprensión

1. ¿Una alerta bajo mínimo significa necesariamente que hay que emitir una compra? Explica qué datos faltan.
2. ¿Por qué ocultar un botón no basta para impedir una salida?
3. ¿Cuál es la diferencia entre existencia y movimiento?

**Orientación:** la alerta señala una condición del registro, la compra necesita decisión y contexto; el servidor debe autorizar; la existencia es saldo y el movimiento es un hecho trazable.

Lectura de apoyo: tutorial de Django, partes 1 y 2, enlazado en fuentes.md. No es necesario memorizar su código.
