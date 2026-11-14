# Rúbrica y condiciones del proyecto final

Texto alineado con la evaluación del aula.

PROYECTO FINAL: UNA APLICACIÓN LOGÍSTICA CON DATOS COMPROBABLES

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
