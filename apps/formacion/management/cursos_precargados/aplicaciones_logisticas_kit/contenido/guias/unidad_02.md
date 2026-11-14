# Unidad 2 · Primeros pasos con Python, Django y asistentes de IA

**Unidad: 8 horas en total**, incluyendo las lecturas, videos, archivos, laboratorio y evaluación del aula. **Laboratorio guiado: 4 h 50 min.** Meta: ejecutar el kit, reconocer su estructura y realizar un cambio pequeño que puedas explicar y recuperar.

## Conceptos que usarás

Python es el lenguaje de las instrucciones. Django organiza datos, URLs, formularios y pantallas. Un entorno virtual separa las dependencias de este proyecto de otros programas. Una migración crea o modifica la estructura de tablas. El servidor local atiende únicamente la dirección de práctica; mantenerlo encendido no publica una web en Internet.

No necesitas dominar Python. Empieza reconociendo variables como datos con nombre, funciones como operaciones reutilizables, condiciones como decisiones y modelos como descripciones de registros. Si la IA introduce un concepto nuevo, pídele un ejemplo con los productos del caso.

## Recorrido de trabajo

1. **Preparación guiada:** sigue README.md para tu sistema. Ejecuta cada comando por separado, lee el resultado y no continúes si falla. Crea operador y lector con contraseñas propias.
2. **Exploración del proyecto:** localiza manage.py, andina/settings.py, inventario/models.py, services.py, views.py y templates/. Relaciona cada archivo con pantalla, regla o dato.
3. **Primera explicación con IA:** utiliza prompts/02_explicar_codigo.md. Pide una explicación de models.py en lenguaje sencillo. Comprueba la explicación buscando los campos reales.
4. **Cambio reversible:** guarda una copia del proyecto o un commit. Cambia el título visible de templates/inventario/tablero.html a «Control de existencias del almacén docente» y añade una frase de ayuda. Solicita a la IA sólo esa modificación y revisa la diferencia antes de aceptarla.
5. **Catálogo y roles:** registra MAN-01, «Material de práctica», UN y mínimo 3.00. La existencia debe ser 0.00. Sal del sistema, entra como lector y comprueba que no puedes registrar productos.
6. **Pruebas y evidencias:** ejecuta python manage.py test inventario. Anota el cambio realizado, archivos afectados, resultado y cómo volverías al estado anterior.

## La plantilla es un punto de partida

El kit incluye una solución docente funcional para que todos puedan practicar, aunque su modelo gratuito tenga límites. Tu aprendizaje consiste en entenderla, modificarla con criterio y verificarla. No presentes la plantilla íntegra como si la hubieras programado desde cero: identifica el material inicial y tus aportaciones en la bitácora.

## Cuando una instrucción falla

Copia únicamente el mensaje de error necesario, el comando que ejecutaste y el archivo implicado. No envíes contraseñas, el archivo .secreto-local ni una base con datos personales. Pide una explicación y una corrección acotada. Evita ejecutar comandos que no puedas explicar con ayuda del docente.

## Entrega

Captura del acceso y tablero, producto MAN-01 registrado, breve mapa de archivos y evidencia del cambio visual y de las pruebas. Incluye una explicación de entorno virtual y migración con tus propias palabras.

## Comprueba tu comprensión

1. ¿Por qué se utiliza el Python de .venv para instalar dependencias y ejecutar manage.py?
2. ¿Modificar un texto de una pantalla requiere cambiar el modelo de datos?
3. ¿Qué revisarías antes de aceptar una modificación de veinte archivos para cambiar un título?

**Orientación:** mismo entorno, cambio de pantalla independiente de tablas y revisión del alcance antes de aceptar.

Lecturas: Python venv y tutorial de Django, enlaces oficiales en fuentes.md.
