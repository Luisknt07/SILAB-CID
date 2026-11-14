# CIDT: estructura y contenido operativo

El problema mostrado por el usuario era de contenido: las reglas estaban construidas,
pero las muestras excluidas dejaban Ahora en el centro, Proyectos y Resultados vacíos.
La instrucción actual pide un escenario completo de funcionamiento para revisar
la estructura, las fichas, las relaciones y las acciones.

## Qué contiene cada pestaña

| Pestaña | Contenido construido y propósito |
| --- | --- |
| El centro | Presentación, misión y visión de trabajo, actividad reciente, ruta de atención, gobierno, indicadores calculados y guías de operación. |
| Áreas y capacidades | Nueve áreas con procesos, inventario, servicios, proyectos y personas relacionados; espacios de práctica, horarios, búsqueda y consulta de disponibilidad. |
| Investigación | Ocho líneas con problema, preguntas, método y territorio; doce proyectos con objetivos y metodología; 48 hitos; seis productos de investigación con versión, autores y ficha descargable. |
| Innovación y transferencia | Tres prototipos y un expediente de software con metadatos del escenario; tres casos conectados a sus proyectos y desarrollos; cinco actores genéricos de colaboración. |
| Equipo | 28 perfiles expresados por función y cuatro grupos conectados a las líneas. Se conservan las restricciones de nombres de estudiantes y tesistas. |
| Servicios y colaboración | 57 servicios con alcance, entradas, método, requisitos, entrega, aceptación, plazos y exclusiones; solicitudes por intención, visitas, oportunidades y cuatro programas formativos completos. |

La actividad se obtiene de los mismos proyectos, resultados, convocatorias y novedades.
No se duplica su edición para llenar la portada. Los cursos propios se separan de
las convocatorias generales; los cursos vinculados conservan el propietario y sus
accesos canónicos a matrícula y aula.

## Acciones y funciones

- Consultar servicio mantiene el servicio elegido y abre el expediente de solicitud.
- Solicitar uso permite elegir tres activos individuales o tres espacios de práctica.
  Hay ventanas de lunes a viernes, 08:00–17:00, con 15 minutos de preparación y cierre.
  La solicitud inicial no asigna el recurso: gestión confirma requisitos y horario.
- Solicitar participación conserva curso y área. El centro comunica la aceptación;
  no se inventan matrículas ni cupos ocupados.
- Proponer un reto, pedir acompañamiento, demostración o transferencia conserva
  proyecto o desarrollo. El seguimiento privado usa diagnóstico, plan, sesiones,
  tareas, respuestas y cierre ya implementados.
- Exportar resultados produce JSON/RIS con procedencia del escenario y mantiene
  los mismos filtros del catálogo.
- Calcular capacidad recibe duración, tiempo productivo, demanda, tiempos de ciclo
  y puestos paralelos. Calcula la capacidad mínima de dos etapas, la etapa limitante
  y la demanda pendiente. Permite comparar alternativas cambiando las entradas.
  No modela colas, aleatoriedad ni fallos y no es un gemelo digital conectado.

## Construcción y procedencia

`construir_escenario_centros` completa únicamente el CIDT con `DEBUG=True`.
No ejecuta una recarga global con reescritura: preserva los textos editados, las
coincidencias institucionales y los archivos existentes. Los grupos y recursos
incorporan procedencia con la migración 0013. Los registros representativos
mantienen `es_muestra=True` y no reciben sellos de validación ficticios.

La vista local requiere `CENTROS_ID_ESCENARIOS_OPERATIVOS=cidt-upec`. Los mismos
filtros se aplican en ficha, secciones, áreas, fragmentos, formularios, reportes y
exportaciones. Con `DEBUG=False` se excluye el escenario aunque la variable exista.
Los documentos institucionales privados y los resultados confidenciales siguen
excluidos de la vista pública. Los nuevos archivos señalan su origen representativo.

No se atribuyen nombres reales, DOI, contratos oficiales, aprobaciones, financiación,
reservas históricas o mediciones de impacto a los contenidos creados.
Los espacios de práctica son subáreas con superficie adicional cero para conservar
los 2.516 m² del programa arquitectónico existente.

El CIAB conserva su contenido y configuración. Necesita un guion propio del dominio
agropecuario; el contenido del CIDT no se copia a otro centro.

## Verificación

Pruebas de cobertura de las seis pestañas, todas las secciones y las nueve áreas;
fichas y exportación; aislamiento por centro y modo; privacidad documental;
idempotencia y conservación de ediciones; cursos; disponibilidad y solicitud
pendiente; cálculo de capacidad y entradas inválidas. La regresión incluye los
flujos de centros, laboratorios, cursos vinculados, portal, rutas y manifiestos.
El historial registra el resultado final y el respaldo aplicado.
