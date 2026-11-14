# Ruta de cierre de la reestructuración y desarrollo de verticales

Fecha de corte: 19 de septiembre de 2026  
Rama: `reestructura-modular`  
Base funcional de Plantas Piloto: `49e446a3`

## Decisión de alcance

La estabilización arquitectónica y las aceptaciones de Laboratorios y Plantas
Piloto están cerradas. El sistema tiene una base estable para continuar
funciones: la última suite integral terminó con 1.412 pruebas correctas y una
omitida, sin cambios de esquema pendientes ni errores de Django o Ruff. La
aceptación enfocada de Plantas Piloto añadió 275 pruebas correctas y la revisión
responsive final terminó con doce combinaciones de las cinco plantas sin
desbordamientos.

Los bloques anteriores combinaron implementación, pruebas y evidencia. No
fueron 180 auditorías independientes. La ruta definió seis puertas de auditoría;
las tres primeras ya están cerradas y quedan tres:

1. una auditoría final para cerrar la estabilización arquitectónica actual
   (**cerrada**);
2. una aceptación funcional de Laboratorios (**cerrada**);
3. una aceptación funcional al terminar Plantas piloto (**cerrada**);
4. una aceptación funcional al terminar Centros experimentales;
5. una aceptación funcional al terminar Observatorios;
6. una aceptación funcional al terminar Centros I+D.

Los commits intermedios tendrán pruebas proporcionales al cambio, pero no
abrirán una auditoría general nueva. M10-M13 permanecen como evolución de
producto y despliegue; no bloquean el desarrollo funcional de las verticales.

## Secuencia antes de volver a las funciones

La ruta se fijó en tres entregas de código y una única auditoría de cierre.
Las entregas 181, 182, 183 y 184 están completas:

| Entrega | Alcance | Criterio de salida |
| --- | --- | --- |
| 181 | Extraer de `crear_reserva` la lectura, normalización y validación de la solicitud y la selección de proceso, recursos y servicio | Las reglas se prueban sin construir una petición HTTP completa y la vista conserva las mismas rutas y respuestas |
| 182 | Extraer la creación transaccional del expediente, participantes, recursos, consumibles, programación, guías y avisos | La vista adapta HTTP y un caso de uso es el único propietario de la escritura; creación y reversa conservan su comportamiento |
| 183 | Completar el interruptor de la capacidad de reservas en entradas nuevas, tareas, comandos y exportaciones | La suspensión impide nuevas operaciones por la misma autoridad, conserva consulta e historial y no pierde trabajos recuperables |
| 184 | Auditoría final de estabilización | Completada: suite integral, Django, migraciones, Ruff, señales, ES/EN, carreras relevantes y 770 recorridos responsive en verde; mapa de deuda actualizado |

Esta fase terminó en el bloque 184. No se ampliará con M01 institucional,
M02.3 o M10-M13. Si aparece un defecto, se corrige dentro del bloque que lo
descubre; no se crea una fase de auditoría nueva.

El bloque 181 está **completado**. Entrada común, propósito, intención,
calendario, producto/proceso, equipos, espacios, software, consumibles,
servicios, adjuntos, modalidad y cotización tienen módulos sin respuestas HTTP
y pruebas directas. La vista bajó de 3.020 a 2.145 líneas y `crear_reserva` de
1.246 a 890 líneas.

El bloque 182 también está **completado**. `creacion_transaccion` es el único
propietario de la escritura del expediente, sesiones, participantes, recursos,
consumibles, programación, guías, planificación y aviso. Conserva el orden de
bloqueos `Unidad -> User -> UserProfile`, revalida pertenencia y conflictos
dentro de la transacción y revierte todo ante un fallo tardío. La vista quedó en
1.809 líneas y `crear_reserva` en 573, sin escrituras ORM ni bloqueos en esa
función.

El bloque 183 está **completado**. La capacidad
`legado_webcitt.reservas_operativas` protege la creación, decisiones, cambios,
correcciones, ejecución, cierre, visitas, ingreso, tareas y comandos de
mantenimiento. La suspensión conserva consultas, comprobantes PDF e historial;
el ciclo periódico se omite sin perder trabajo y lo recupera al reactivar. En
PostgreSQL las operaciones usan un bloqueo advisory compartido y el cambio de
habilitación uno exclusivo: las reservas independientes conservan concurrencia
y una suspensión espera las operaciones activas antes de impedir las nuevas.
El bloque 184 quedó cerrado sin defectos nuevos. Señales conserva 19 contratos,
19 decoradores y 19 conexiones propias, sin hallazgos; la configuración de
producción falla cerrada cuando falta una clave de despliegue fuerte. La revisión
responsive cubrió 182 recorridos públicos, 574 autenticados y 14 del visor PDF.

## Trabajo que no bloquea las verticales

- **M01 institucional:** respaldo coordinado de base y adjuntos, copia externa
  cifrada e inmutable, custodia de claves y medición real de RPO/RTO. Necesita
  infraestructura y responsables institucionales.
- **M02.3:** catálogo comercial de categorías y modalidades instalables. Se
  diseñará con casos reales de las verticales, evitando inventar una taxonomía
  antes de conocer sus reglas.
- **M10:** traslado físico de modelos, tablas, ContentTypes y permisos. Se hará
  por contexto cuando exista reversa institucional comprobada.
- **M11:** aislamiento de procesos, credenciales, colas y recuperación. Es una
  fase de despliegue; el monolito modular actual comparte proceso y base.
- **M12-M13:** empaquetado comercial, retiro de compatibilidad y certificación
  final. Corresponden a una versión posterior del producto.

La regla durante el desarrollo funcional será poner el código nuevo bajo su
vertical (`domain`, `application`, `infrastructure`, `presentation` y `tests`)
y usar adaptadores para los datos heredados. No se moverán tablas solo para
mejorar el árbol de carpetas.

## Estado funcional real

| Vertical | Estado actual | Deuda funcional principal |
| --- | --- | --- |
| Laboratorios | Aceptado funcionalmente; app Django instalada y propietaria de su plantilla, con catálogo y detalle delegados al legado | Trasladar propiedad técnica gradualmente en M10-M11 sin reabrir su funcionalidad salvo correcciones críticas |
| Plantas piloto | Aceptada funcionalmente en las cinco plantas; app Django instalada y propietaria de su plantilla y de sus reglas de planificación, completitud y repositorio | Incorporar únicamente contenido institucional o correcciones críticas mientras avanza la siguiente vertical |
| Centros experimentales | Catálogo y detalle público delegados al legado | No existen todavía ciclos, campañas, parcelas, activos biológicos, tratamientos, muestreos ni bitácoras propios |
| Observatorios | Catálogo y detalle público delegados al legado | No existen todavía fuentes, conjuntos versionados, indicadores, metodologías, publicaciones ni solicitudes de análisis propios |
| Centros I+D | Portada pública transitoria independiente de `Unidad` | Falta todo el dominio administrable de centros, líneas, grupos, investigadores, proyectos, resultados, propiedad intelectual, servicios y transferencia |

Plantas piloto tiene cobertura automatizada específica sobre catálogo,
procesos, producción, calidad, planificación, almacén, visitas y unidades. Los
ocho archivos principales suman 121 métodos de prueba declarados, además de
casos heredados, parametrizados y dinámicos.

## Etapa A: aceptar Laboratorios

Después del bloque 184 se ejecutó una sola aceptación de Laboratorios sobre
catálogo, ficha, gestión, equipos, prácticas, reservas, servicios, documentos,
reportes, permisos por unidad y conservación de datos. Los defectos encontrados
se corrigen dentro de esta puerta; no reabren una fase general de arquitectura.

La puerta terminó con 277 pruebas enfocadas, la suite integral de 1.392 pruebas
y 770 comprobaciones responsive en verde. Los criterios y límites comprobables
están en [Aceptación funcional y límites de aislamiento de
Laboratorios](aceptacion-laboratorios.md). Su aprobación congela la
funcionalidad actual de Laboratorios y permite continuar con Plantas piloto.
M10-M11 podrán reforzar después el aislamiento físico sin cambiar este orden
funcional.

**Frontera estructural completada el 19 de septiembre de 2026.** Laboratorios
ya está instalado como app Django mediante `LaboratoriosConfig`, es propietario
de su experiencia pública exclusiva y concentra el puente al legado en un único
adaptador de `infrastructure`. El manifiesto 1.1.0 declara la app y el contrato
`identidad_unidad_v1`. La uniformidad no reabrió la aceptación: rutas,
plantilla, contexto, modelos, administración y permisos conservan su
comportamiento. La estructura y sus límites están en
[`apps/laboratorios/README.md`](../apps/laboratorios/README.md).

## Etapa B: terminar Plantas piloto

La arquitectura funcional ya completó los pasos 1 a 5. Se cerrarán los pasos 6
y 7 con cuatro entregas:

1. **Planificación completa. Completada el 19 de septiembre de 2026.** La
   demanda estimada, el plan de ventas y el agregado por familia se apoyan en
   el Plan Maestro existente sin duplicar recetas, inventario, compromisos ni
   órdenes. La persistencia permanece en `webcitt` hasta M10; las reglas puras
   ya pertenecen a `apps.plantas_piloto.domain`.
2. **Completitud administrable. Completada el 19 de septiembre de 2026.** El
   tablero interno muestra por planta, pestaña, familia y ficha qué está
   aprobado, parcial, pendiente o bloqueado. La validación institucional
   registra responsable y fecha, y las recargas posteriores conservan estado,
   visibilidad, versión, observación y decisión editorial manual.
3. **Repositorio trazable. Completado el 19 de septiembre de 2026.** Cada
   artefacto externo registra fuente, licencia, versión, responsable, fecha de
   validación, vigencia y evidencia. Un artefacto vencido o marcado por cambios
   en su fuente sale de las superficies públicas y de las exportaciones hasta
   una confirmación expresa; archivos, resultados y administradores respetan el
   alcance de la unidad.
4. **Aceptación de Plantas piloto. Completada el 19 de septiembre de 2026.** Se probaron las cinco plantas, los perfiles,
   ES/EN, responsive, permisos, reserva por proceso, producción, calidad,
   inventario, planificación y reportes. Los valores pendientes de la UPEC se
   registrarán como dependencia externa, sin inventarlos ni bloquear el
   software listo. La evidencia y los límites están en
   [Aceptación funcional de Plantas Piloto](aceptacion-plantas-piloto.md).

La salida de esta etapa es una Planta piloto funcionalmente cerrada y una lista
explícita de contenido institucional por entregar. Desde aquí no se seguirá
añadiendo funciones de planta mientras se construye la siguiente vertical,
salvo correcciones críticas.

**Frontera estructural completada el 19 de septiembre de 2026.** Plantas piloto
ya está instalada como app Django mediante `PlantasPilotoConfig`, es
propietaria de su experiencia pública exclusiva y concentra el puente al legado
en un único adaptador de `infrastructure`. El manifiesto 1.4.0 declara la app y
el contrato `identidad_unidad_v1` conservando las cinco capacidades aceptadas.
`domain/planificacion.py`, `domain/completitud.py` y `domain/repositorio.py`
siguen siendo las reglas propias de la vertical. La uniformidad no reabrió la
aceptación: rutas, plantilla, contexto, modelos, administración y permisos
conservan su comportamiento, y lo que permanece en `webcitt` hasta M10 está
inventariado en
[`apps/plantas_piloto/README.md`](../apps/plantas_piloto/README.md).

## Etapa C: Centros experimentales

Esta vertical no reutilizará una reserva de laboratorio como núcleo. Su unidad
de trabajo será el ensayo o campaña de campo.

0. **Frontera estructural completada el 19 de septiembre de 2026.** Las rutas
   públicas conservan su comportamiento, `presentation` delega en un único
   adaptador dentro de `infrastructure` y el manifiesto declara el contrato de
   identidad que ya consume. El paquete ya está instalado como app Django y es
   propietario de su plantilla pública exclusiva. No se crearon capas vacías,
   modelos, migraciones, administración ni reglas de negocio. La estructura y sus límites están en
   [`apps/centros_experimentales/README.md`](../apps/centros_experimentales/README.md).
1. Especificar con la institución clases de centro, ciclos, campañas, parcelas
   o áreas, activos biológicos, tratamientos y protocolos.
2. Crear dominio, administración, permisos y datos maestros propios.
3. Implementar programación, agenda de campo y solicitudes sobre `EnsayoCampo`.
4. Implementar ejecución: tratamientos, muestreos, incidencias, bitácora,
   evidencias y trazabilidad de activos.
5. Implementar resultados, reportes e integración por contrato con Plantas
   piloto cuando se transfiera materia prima.
6. Ejecutar la aceptación de Centros experimentales y publicar su proyección en
   el directorio institucional.

## Etapa D: Observatorios

Un observatorio administra información y análisis; no reservará equipos ni
heredará el flujo físico de las unidades.

0. **Frontera estructural completada el 19 de septiembre de 2026.** El paquete
   está instalado como app Django, posee su plantilla pública exclusiva y
   concentra el puente temporal al legado en `infrastructure`. No incluye
   modelos, migraciones, administración ni reglas funcionales.
1. Crear fuentes, conjuntos de datos, versiones, licencias y metodologías.
2. Crear indicadores reproducibles, series, metadatos y validación de calidad.
3. Crear publicaciones, tableros y descargas con visibilidad y trazabilidad.
4. Crear `SolicitudDatos` y `SolicitudAnalisis` con su propio flujo, tiempos,
   responsables, entregables y permisos.
5. Ejecutar la aceptación de Observatorios, incluidas privacidad, exportaciones,
   accesibilidad, ES/EN y responsive.

## Etapa E: Centros de Investigación y Desarrollo

Centros I+D seguirá siendo un contexto independiente y no un tipo de `Unidad`.
Antes de crear modelos se cerrará una especificación funcional con la
institución.

0. **Frontera estructural completada el 19 de septiembre de 2026.** La app está
   instalada y posee su ruta, vista y plantilla pública. Solo depende de
   `core`; no contiene modelos, migraciones, administración ni reglas de
   investigación.
1. Centros, líneas, grupos, investigadores, afiliaciones y perfiles públicos.
2. Proyectos, convocatorias, equipos, hitos, actividades y seguimiento.
3. Resultados: publicaciones, conjuntos, prototipos, propiedad intelectual y
   evidencias de impacto.
4. Servicios, transferencia, convenios y vinculación con capacidades de las
   otras verticales mediante identificadores y contratos públicos.
5. Administración, permisos por rol, proyección pública, reportes y auditoría.
6. Aceptación integral de Centros I+D y revisión del producto completo.

## Uniformidad estructural de las cinco verticales

**Cerrada el 19 de septiembre de 2026.** Las cinco verticales comparten ahora
la misma frontera estructural:

| Vertical | App instalada | Plantilla propia | Puente heredado aislado | Manifiesto |
| --- | --- | --- | --- | --- |
| Laboratorios | `LaboratoriosConfig` | `laboratorios/experiencia.html` | `infrastructure/unidades_heredadas.py` | 1.1.0 |
| Plantas piloto | `PlantasPilotoConfig` | `plantas_piloto/experiencia.html` | `infrastructure/unidades_heredadas.py` | 1.4.0 |
| Centros experimentales | `CentrosExperimentalesConfig` | `centros_experimentales/experiencia.html` | `infrastructure/unidades_heredadas.py` | 1.2.0 |
| Observatorios | `ObservatoriosConfig` | `observatorios/experiencia.html` | `infrastructure/unidades_heredadas.py` | 1.1.0 |
| Centros I+D | `CentrosIDConfig` | `centros_id/portada.html` | No aplica; su portada no consulta el legado | 1.1.0 |

Los cuatro tipos de unidad declaran además el contrato `identidad_unidad_v1`.
Las carpetas `webcitt/templates/portal/pages/unidades/experiencias` y
`webcitt/templates/portal/pages/centros_id` quedaron vacías y se retiraron:
ninguna de esas superficies públicas pertenece ya al legado.

La primera suite integral posterior a los traslados encontró un defecto
heredado del bloque de Centros I+D: `webcitt/tests/test_portal.py` seguía
exigiendo la plantilla anterior de la portada, que había cambiado de
propietario sin actualizar esa prueba. Se corrigió la aserción dentro de este
bloque, conforme a la regla de resolver los defectos donde se descubren.

Este cierre es estructural. No movió modelos, tablas, `ContentTypes`, permisos
ni administración heredada, y no añadió funciones a ninguna vertical. Las
aceptaciones de Laboratorios y Plantas piloto no se reabrieron. El traslado de
propiedad de datos sigue siendo M10 y el aislamiento de procesos M11.

Validación de cierre: 1.433 pruebas correctas y una omitida en 804,103
segundos; Django check, `makemigrations --check --dry-run`,
`auditar_modulos`, Ruff y compilación sin hallazgos.

## Orden de ejecución obligatorio

```text
181 -> 182 -> 183 -> 184 -> Laboratorios aceptado
                                  |
                                  v
Plantas piloto aceptado -> Centros experimentales -> Observatorios -> Centros I+D
```

Una etapa puede recibir correcciones mientras se prueba, pero no se intercalan
rediseños generales ni traslados masivos de tablas. Cada vertical se considera
terminada cuando sus reglas, administración, datos, permisos, interfaz, pruebas
y documentación cumplen su aceptación, no cuando solo existe una carpeta o una
portada.
