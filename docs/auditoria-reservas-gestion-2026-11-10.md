# Auditoría de reservas y gestión de unidades — 10 de noviembre de 2026

> Estado histórico al 10 de noviembre. Los pendientes de infraestructura, claves y datos se actualizan en el [mantenimiento del 11 de noviembre](mantenimiento-validacion-2026-11-11.md).

La revisión corrige problemas de integridad en el código y comprueba los datos locales mediante transacciones de solo lectura. **La publicación en producción sigue condicionada a la conciliación del inventario y a los ajustes de infraestructura indicados al final.** No se alteraron existencias, expedientes económicos históricos ni credenciales operativas.

## Alcance y datos comprobados

Se revisaron reservas de recursos, servicios y visitas; calendario, participantes, permisos operativos, áreas, equipos compartidos, materiales, lotes, kardex y administración. El inventario local consultado contiene:

| Registro | Cantidad |
|---|---:|
| Unidades institucionales | 32 |
| Áreas y espacios | 166 |
| Unidades físicas de equipo | 2.471 |
| Artículos de inventario | 781 |
| Lotes de materiales | 898 |
| Movimientos de inventario | 2.503 |
| Reservas | 219 |
| Solicitudes de visita | 2 |
| Incidencias de equipos | 5 |

Las dos bases PostgreSQL tienen 302 y 50 tablas, respectivamente. Se comprobaron 809 relaciones de clave foránea sin encontrar registros huérfanos, índices inválidos, restricciones sin validar o disparadores propios desactivados. No hay migraciones pendientes correspondientes a los modelos que posee cada base; las migraciones de aplicaciones centrales excluidas por el router no son migraciones pendientes de Centros.

No se detectaron asociaciones entre áreas y equipos de otra unidad, reservas con espacios/programas/servicios de otra unidad, responsables ajenos, recorridos cruzados, movimientos enlazados a insumos o reservas de otra unidad, existencias negativas ni lotes con saldo superior al recibido. Un equipo compartido se considera válido cuando la unidad está declarada como principal o asociada. Las áreas fusionadas inactivas se conservan como referencias históricas.

El catálogo académico pasó la comprobación de 56 campos. El calendario institucional tiene un período y 16 semanas sin códigos desconocidos ni incompatibilidades de fechas o ciclos.

## Correcciones realizadas

1. **Fusión de áreas.** Se bloquean ambas filas en orden estable, se releen sus estados y se rechazan destinos inactivos o integrados. Una cadena histórica circular o entre unidades se detiene y la ficha devuelve 404, evitando consultas infinitas y redirecciones incorrectas.
2. **Conteos de almacén.** El registro y cierre releen el estado bajo bloqueo. Un objeto desactualizado no permite modificar ni cerrar dos veces. La captura de auditoría bloquea el conteo antes de su línea; los conteos, cierres de reserva y corridas de planta bloquean artículos antes de sus lotes, con orden estable para varios materiales. Se rechazan ajustes cuando el saldo cambió desde la apertura. Se validan unidad, artículo, lote y ajuste; las cantidades e importes no finitos producen un error de validación.
3. **Materiales de servicios.** Las relaciones de materiales con servicios y solicitudes validan su unidad y rechazan cantidades negativas al guardar. Se conserva la compatibilidad con servicios generales heredados sin unidad.
4. **Recarga institucional.** Las existencias iniciales se asignan únicamente al crear el artículo. Recargar el catálogo conserva saldos, lotes, ubicación y vencimientos ya gestionados; el código del lote se busca dentro de su artículo.
5. **Datos demostrativos.** La generación de existencias ficticias del comando de referencia exige habilitación del entorno, una unidad y confirmación explícita. No se mezcla con artículos que ya tengan saldo, lotes o movimientos. El modo normal de completar metadatos conserva su funcionamiento.
6. **Importes de visitas.** La reserva es el expediente económico canónico. Al guardar su importe se sincroniza la copia de la visita dentro de la misma transacción y base. La presentación consulta el importe del expediente, evitando mostrar una copia antigua como precio vigente. Un guardado parcial de otro campo no publica un precio local obsoleto.
7. **Nombres por tipología.** Los accesos de gestión usan la denominación del catálogo institucional: laboratorio, observatorio, planta piloto, centro experimental o tipología propia. Se conservan los identificadores técnicos y las rutas compatibles.
8. **Auditoría administrativa.** Los enlaces históricos que redirigen a una pantalla administrativa válida se comprueban hasta su destino. Se rechazan ciclos, destinos externos y redirecciones al acceso o fuera del administrador. La ruta conservada de evidencias llega al centro de reportes y responde correctamente.

Las pruebas de cierre se actualizaron para que los ingresos positivos correspondan a materiales realmente consumidos, con lote, equipo y kardex. Se mantiene la comprobación de rollback, permisos revocados, concurrencia y ausencia de doble ingreso. Los contratos de señales se revisaron después del cambio de etiqueta y de la sincronización del importe; se actualizaron únicamente sus huellas de revisión.

## Validación

La regresión general ejecutó **5.821 pruebas**, con 13 omitidas por condiciones de entorno y sin errores de ejecución. Registró siete aserciones fallidas en tres métodos de dos clases de interfaz: dependían del idioma que hubiera dejado una prueba anterior. Se fijó explícitamente el español en esas clases; sus 17 pruebas pasaron con orden aleatorio y, después, **las 1.176 pruebas sin SQL pasaron completas**. Este último resultado corresponde a la repetición del subconjunto afectado, no a otra ejecución de toda la batería SQL.

- Separación física y operaciones de Centros: **307 pruebas aprobadas** en dos bases temporales.
- Correcciones de integridad, visitas, inventario, fusión y auditoría: **46 pruebas aprobadas** en una base temporal independiente.
- Regresiones adicionales de almacén, cierres, inventario y producción: 77 pruebas aprobadas y **76 aprobadas tras los últimos controles de bloqueo y validación numérica**.
- JavaScript: **347 pruebas aprobadas**.
- Plantillas: **486 compiladas, sin errores**.
- Ruff y detección de migraciones: sin errores ni cambios de esquema faltantes.
- Contratos de señales: 35 contratos y 35 conexiones propias, sin hallazgos.
- Auditoría administrativa de los cinco módulos revisados: **164 pantallas sin fallos**, incluyendo el destino de evidencias.
- Arquitectura y archivos: sin colisiones entre Windows/Linux ni archivos sin referencia. Las siete agrupaciones de contenido idéntico corresponden a marcadores de propiedad de migraciones y recursos estáticos con rutas de catálogo; no se eliminaron referencias necesarias.
- Dependencias: 44 paquetes instalados compatibles entre sí; `requirements.txt` coincide con `uv.lock`, incluidos marcadores y hashes, y la comprobación del lock pasa. **39 dependencias de ejecución auditadas contra avisos de PyPI, sin vulnerabilidades conocidas en esta consulta**.

Los registros técnicos se conservan fuera del árbol versionado en `var/auditoria-reservas-20261110/` y `var/auditoria-20261109/`. Las pruebas SQL se ejecutan en PostgreSQL de QA, con nombres `citt_qa_*`, correo en memoria y archivos temporales. El análisis de datos operativos utiliza snapshots de solo lectura y registra conteos e identificadores técnicos, sin exportar datos personales al repositorio.

El servidor local se reinició con el código actualizado. La ficha de FabLab y los tres recursos estáticos compartidos del calendario respondieron HTTP 200. La revisión de interfaz cubre compilación y pruebas automatizadas; no incluye una inspección visual nueva en navegador.

Al terminar se verificaron cero conexiones de pruebas y se retiraron exclusivamente los dos contenedores PostgreSQL temporales de esta auditoría y sus volúmenes. PostgreSQL operativo y su pasarela permanecen activos; FabLab volvió a responder HTTP 200 después de retirar QA.

## Pendientes antes de publicar

1. **Conciliar 95 artículos.** La suma de sus lotes supera el stock del artículo. La recarga ya no reinicia esos valores, pero corregir el pasado exige revisar el kardex y contar físicamente, por unidad, con la persona responsable. No se debe convertir la suma de lotes en saldo real automáticamente. Los identificadores afectados están en el informe local privado `datos-integridad.json`.
2. **Completar una visita antigua sin estimación en su expediente.** Su copia contiene cero y la reserva no tiene importe ni desglose; esto significa estimación pendiente, no una diferencia entre dos importes emitidos. Debe revisarse antes de aprobarla. Las visitas nuevas generan ambos datos en una sola transacción.
3. **Restringir el rol principal de PostgreSQL.** El usuario configurado para la aplicación central es superusuario y puede crear bases y roles o saltarse RLS. `verificar_seguridad_bd --database default` lo rechaza. El rol de Centros pasa la comprobación. Preparar un rol web restringido y mantener separados los roles de migraciones y respaldo, siguiendo [el despliegue de producción](produccion-linux.md) y [la separación de bases](estructura-bases-datos-docker.md). No se cambiaron permisos del servidor durante esta revisión.
4. **Corregir el puerto del contenedor operativo.** La instancia actualmente iniciada publica PostgreSQL en todas las interfaces del host, aunque el Compose versionado lo limita a loopback. Hay que recrear esa instancia con la configuración prevista, preservando y verificando sus volúmenes y respaldos. No se comprobó exposición desde Internet ni se interrumpió el contenedor operativo.
5. **Configurar secretos de producción.** El perfil local no supera la comprobación de producción porque su `SECRET_KEY` no cumple la longitud mínima. Usar una clave aleatoria propia del despliegue y completar las comprobaciones de HTTPS, dominios, correo y transporte de base de datos del [procedimiento de publicación](despliegue-produccion.md). La revisión no da por validado ese entorno externo.
6. **Resolver el historial sensible.** Git conserva versiones antiguas de `.env` y copias SQLite. El árbol actual no contiene esos archivos privados. Antes de dar acceso al historial, comprobar revocación de las credenciales expuestas y retención de las bases antiguas. No se reescribió el historial compartido.

Esta auditoría delimita lo comprobado y las correcciones realizadas. No certifica la existencia física de equipos o materiales a partir de datos de referencia, ni sustituye la conciliación de almacén, la aprobación de responsables o la validación del entorno de producción.
