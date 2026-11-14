# Unidad 3 · Construcción de funciones logísticas con IA

**Unidad: 8 horas en total**, incluyendo las lecturas, videos, archivos, laboratorio y evaluación del aula. **Laboratorio guiado: 4 h 50 min.** Meta: explicar y comprobar el flujo de entrada y salida, sus validaciones y la trazabilidad de cada operación.

## De formulario a operación

El formulario recoge producto, tipo, cantidad y motivo. La vista comprueba acceso y llama al servicio. El servicio valida los datos, actualiza el saldo y guarda el movimiento dentro de una transacción. Si una parte falla, ambas se revierten. La cantidad se maneja con Decimal para conservar dos decimales de forma explícita.

Un doble clic puede enviar el mismo formulario dos veces. El identificador oculto de operación permite reconocer el mismo envío y evita registrarlo nuevamente. Una clave reutilizada con otros datos se rechaza. Este mecanismo reduce errores, pero no convierte este prototipo SQLite en un WMS multiusuario de producción.

## Recorrido de trabajo

1. **Trazar una operación:** sigue MovimientoForm → movimiento_nuevo → registrar_movimiento. Pide a la IA que explique la secuencia sin cambiar el código. Verifica que la respuesta corresponde a esos archivos.
2. **Ejecutar movimientos conocidos:** si ya modificaste el stock de la demo, usa otra extracción del kit para obtener una base nueva. Abre datos/movimientos_ejemplo.csv e introduce los pasos desde el formulario, en orden.
3. **Interpretar controles:** prueba 0, -1 y 1.234 como cantidad. Si el navegador impide enviarlos, lee con el docente el test que los rechaza desde el servicio; no elimines las validaciones para completar la práctica.
4. **Reconocer permisos:** como lector, visita /movimientos/nuevo/. Debe responder acceso restringido. Explica la diferencia entre no mostrar un botón y proteger la URL.
5. **Mejora acotada con IA:** aplica prompts/03_mejorar_mensaje.md para mejorar la ayuda del formulario sin cambiar las reglas. Revisa la diferencia y ejecuta pruebas.
6. **Documentar:** completa las filas de pruebas de movimientos y presenta un historial coherente con las operaciones realizadas.

## Resultados esperados del guion

Desde una demo nueva: AD-001 recibe 5.00 y queda 22.00; luego sale 2.00 y queda 20.00. AD-003 sale 0.25 y queda 9.00. La salida de 99.00 de AD-002 se rechaza: conserva 20.00 y no aparece un movimiento de 99.00. Cada operación válida añade un registro con motivo, fecha y usuario.

## Tres decisiones que debes poder explicar

- El stock no se escribe directamente en un formulario: cambia mediante un movimiento.
- El motivo es texto simple; no se utiliza para ejecutar código ni HTML.
- Las cantidades se verifican en el backend, incluso si la pantalla ya las limita.

En inventario/tests.py encontrarás pruebas de salida insuficiente, precisión, doble envío y reversión cuando falla el historial. Ejecútalas y relaciona cada una con un riesgo operativo.

## Entrega

Tabla de movimientos con saldos esperados y observados, evidencia de una salida rechazada y un acceso restringido, mejora del mensaje y prueba de regresión. No necesitas construir todos los componentes desde cero.

## Comprueba tu comprensión

1. Si falla el registro del historial, ¿debería conservarse el descuento de stock?
2. ¿Por qué no se debe redondear 1.234 silenciosamente a 1.23?
3. ¿Qué información permite identificar quién registró un movimiento?

**Orientación:** operación completa o reversión; precisión explícita y decisión del usuario; usuario, fecha y motivo en el historial.

Lecturas: transacciones, validación y permisos de Django en fuentes.md.
