# Unidad 5 · Pruebas, mejora y presentación de la aplicación

**Unidad: 8 horas en total**, incluyendo las lecturas, videos, archivos y evaluación del aula. **Laboratorio guiado: 3 h; proyecto final: 1 h 50 min.** Meta: entregar un prototipo reproducible, explicar sus reglas y demostrar una mejora propia.

## Comprobar antes de presentar

Una aplicación que abre no necesariamente calcula bien. Las pruebas de aceptación describen acciones y resultados observables; las pruebas automatizadas repiten controles del código. Una captura de pantalla puede documentar un resultado, pero no sustituye la comprobación de permisos, saldo e historial.

## Recorrido de trabajo

1. **Preparar una lista de pruebas:** completa datos/pruebas_aceptacion.csv con datos iniciales, resultado esperado, observado y evidencia.
2. **Ejecutar y corregir:** comprueba catálogo, entrada, salida, error de stock, archivo inválido, permisos y consulta MCP. Ejecuta python manage.py test inventario; registra el resultado. Si has hecho cambios, explica qué prueba protege cada regla.
3. **Aplicar una mejora propia:** selecciona una mejora pequeña: ayuda de pantalla, filtro de lectura o presentación de un indicador. Describe el alcance, guarda versión, usa IA si está disponible, revisa la diferencia y comprueba que las reglas se conservan.
4. **Documentar:** completa plantillas/proyecto_final.md y bitacora_ia.csv. Incluye instrucciones para ejecutar, datos ficticios, fuentes, límites y tu contribución sobre el kit.
5. **Demostrar:** presentación de 5–8 minutos y preguntas. Muestra un flujo correcto y uno rechazado; compara un dato del asistente con la base.
6. **Evaluar y mejorar:** aplica la rúbrica, recibe retroalimentación y corrige una observación concreta.

## Paquete de entrega

- Fuentes del proyecto con la mejora propia, sin .venv, base SQLite, secreto local, configuración personal ni contraseñas.
- README con pasos reproducibles y alcance educativo.
- Ficha de proyecto y diccionario de datos.
- Tabla de pruebas con evidencias.
- Bitácora de cambios y uso de IA, identificando el material inicial.
- Demostración o grabación breve; sólo utiliza datos ficticios.
- Evidencia de MCP de la modalidad realizada, sin atribuir conexión a un modelo si no ocurrió.

Usa plantillas/rubrica.csv y plantillas/rubrica_detallada.md, alineadas con el aula: A. Funciones y recorrido operativo (30), B. Datos y validaciones (25), C. Consultas, reportes e integración (15), D. Uso de IA explicado y trazable (10), E. Pruebas y permisos (10) y F. Guía y demostración (10). La consulta MCP vale 5 puntos dentro de Consultas, reportes e integración.

La nota mínima del proyecto es 70/100 y deben corregirse fallos críticos de stock negativo o escritura sin permiso antes de aprobar. Esto no sustituye las demás actividades del curso ni las condiciones institucionales de certificación. El proyecto no emite certificados ni garantiza competencias avanzadas.

## Lo que debes poder explicar

Qué problema resuelve; dónde se guardan productos y movimientos; qué impide una salida excesiva; quién puede registrar; por qué el catálogo no trae stock; cómo se verificó el cálculo; qué hace MCP; qué puede y qué no puede hacer tu prototipo.

## Comprueba tu comprensión

1. ¿Qué evidencia demostraría que tu mejora no rompe una regla anterior?
2. ¿Por qué excluyes la base de datos al compartir código?
3. ¿Cómo diferenciarías lo generado por IA, el kit inicial y tu revisión personal?

**Orientación:** pruebas antes/después y resultados observados; prevención de compartir cuentas/datos y reproducción desde datasets; bitácora con cambios, explicación y comprobaciones.

La siguiente etapa de formación podría abordar más bodegas, API, despliegue y automatización. Anótalo como evolución futura y no como una función ya construida.
