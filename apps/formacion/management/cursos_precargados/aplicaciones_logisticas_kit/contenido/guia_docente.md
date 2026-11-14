# Guía docente · 40 horas, cinco unidades

Este kit acompaña el aula del curso Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial. La planificación mantiene cinco unidades de 8 horas. Las lecturas, videos, cuestionarios y actividades del aula se articulan con las guías; no son horas adicionales al total.

## Preparación antes de la edición

1. Extraer el ZIP en un equipo de prueba Windows y, si se utiliza, otro Linux.
2. Comprobar Python 3.11/3.12 y permisos para instalar dependencias. No alterar políticas del equipo sin soporte.
3. Ejecutar README completo en un entorno nuevo; verificar demo y permisos de operador/lector.
4. Ejecutar las 15 pruebas y verificar_mcp.py con SDK 2.3.0. Probar el host/modelo disponible; no prometer cuotas gratuitas que no se hayan comprobado.
5. Preparar una demostración sin IA usando plantilla, instrucciones y cliente MCP de protocolo para quienes alcancen su cuota o no tengan cuenta.
6. Revisar que videos externos siguen disponibles. Los videos son apoyos, no sustituyen la guía y la práctica. No descargarlos ni redistribuirlos sin permiso.
7. Acordar condiciones de evaluación, recuperación, asistencia y certificación institucional. El curso no crea automáticamente una acreditación por una plataforma externa.

## Distribución sugerida

| Unidad | Explicación y recursos | Práctica guiada/autónoma | Comprobación/quiz | Total |
|---|---:|---:|---:|---:|
| 1. Diseño de la aplicación | 2 h | 5 h | 1 h | 8 h |
| 2. Herramientas y Django | 2 h | 5 h | 1 h | 8 h |
| 3. Funciones logísticas | 2 h | 5 h | 1 h | 8 h |
| 4. Datos e integración MCP | 2 h | 5 h | 1 h | 8 h |
| 5. Pruebas y proyecto | 1 h | 6 h | 1 h | 8 h |

En unidad 4, reserva cuatro horas al recorrido MCP y el resto a CSV e indicadores. Ajusta el ritmo dentro del bloque, sin añadir funciones avanzadas. Cada participante identifica una mejora propia sobre el kit. La plantilla completa permite recuperar el avance si un asistente genera una solución errónea.

## Acompañamiento para personas no programadoras

Introduce conceptos al utilizarlos: campo, función, condición, permiso, ruta, servidor y prueba. Comprueba que cada persona puede explicar una operación conocida. Utiliza trabajo en parejas, demostración breve, ejecución individual y contraste de resultados. Diferencia un error de instalación de un error de lógica; ofrece recuperación desde otra extracción, conservando la anterior.

No evalúes por número de líneas de código ni por la marca de IA. Pide evidencia de decisiones, revisión y pruebas. Si el modelo no está disponible, acepta la modalidad documentada de plantilla y cliente MCP sin modelo; no atribuyas una conexión inexistente.

## Evaluación del proyecto

Usa la rúbrica común de plantillas/rubrica.csv, idéntica a la del aula: A. Funciones y recorrido operativo (30), B. Datos y validaciones (25), C. Consultas, reportes e integración (15), D. Uso de IA explicado y trazable (10), E. Pruebas y permisos (10) y F. Guía y demostración (10). MCP aporta 5 puntos dentro de Consultas, reportes e integración; no es un criterio independiente de 10 puntos. Los desgloses, evidencias, pruebas mínimas y condiciones completas están en plantillas/rubrica_detallada.md.

La nota mínima del proyecto es 70/100. Antes de aprobar deben corregirse fallos críticos que permitan stock negativo o modificaciones sin permiso, aunque la suma inicial supere 70. La aprobación del proyecto no sustituye las demás actividades requeridas ni la validación institucional de la certificación.

La tabla pruebas_aceptacion.csv contiene situaciones conocidas. Son complementarias a las 15 pruebas automatizadas. El docente puede pedir al participante explicar dónde se resuelve una de las reglas y cómo verificar una modificación.

## Limitaciones técnicas que explicar

SQLite simplifica la instalación para prácticas locales; no se promete concurrencia de producción. El servicio utiliza transacciones, actualización condicionada y claves de envío. La importación crea catálogo, no existencias. El MCP abre sólo lectura y no comparte la sesión web: no es una demostración de permisos multiusuario institucionales.

DEBUG y dirección local están elegidos para enseñanza. No cargar información sensible ni abrir el servicio a la red. Un siguiente curso debe diseñar despliegue, autenticación remota, auditoría, copias, operación real y pruebas de carga.

## Evidencias y atribución

Distinguir kit inicial, cambios de estudiante, ayuda de IA y recursos externos. Las referencias están en fuentes.md. El material propio se distribuye bajo MIT. No se afirma aprobación, patrocinio ni autoría oficial de Django, OpenCode o MCP.
