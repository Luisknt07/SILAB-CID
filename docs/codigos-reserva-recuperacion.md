# Codigos de reserva: asignacion y recuperacion

Bloque 163, avance de M02.4. El modelo, la tabla y el receiver siguen en
`webcitt`; `webcitt/services/codigos_reserva.py` separa la operacion compartida
del legado. No traslada la autoridad a una vertical ni agrega dependencias de
modelos hacia dominios. El servicio no importa modelos, vistas o dominios al
cargar; resuelve el modelo dentro de la operacion.

## Comportamiento conservado y fallo observable

El formato sigue siendo `RL{unidad_id:03d}-{reserva_id:06d}`. El constructor usa
`laboratorio_id`, sin consultar la relacion Unidad. Un codigo persistido no
vacio se conserva, incluso si la instancia llamadora esta obsoleta. No se
renumeran codigos historicos o personalizados al cambiar la unidad.

`asegurar_codigo_reserva()` lee la fila fresca con `select_for_update()` en una
transaccion del alias recibido, del estado de la instancia o del router. Solo
escribe `codigo_reserva` cuando es NULL o vacio, mediante update sin volver a
disparar post_save. Dos conexiones PostgreSQL que compiten por la misma fila
convergen: una asigna y la otra conserva el resultado.

Dentro de una transaccion del llamador, atomic crea un savepoint: un error SQL
de asignacion se revierte antes de propagarse, sin invalidar esa transaccion.
La copia en memoria ocurre despues del savepoint exitoso. No equivale al commit
de una transaccion exterior: si esta se revierte, descartar o recargar la
instancia, como en las otras operaciones ORM. La prueba de concurrencia es
PostgreSQL; no certifica motores sin bloqueo de fila equivalente.

El receiver conserva el comportamiento no bloqueante: si falla la asignacion,
la reserva puede quedar persistida sin codigo. Ahora emite el evento WARNING
`reserva_codigo_asignacion_fallida`; omite raw=True y propaga using al servicio.
El servicio, invocado directamente, propaga sus errores; no oculta el fallo al
operador. No se agrega un retry automatico o una cola global.

Los registros contienen mensajes fijos, sin argumentos, excepcion, traceback,
IDs, codigo, usuario o SQL. Facilitan detectar el problema; no constituyen un
historial criptografico o una trazabilidad individual de los registros fallidos.
El diagnostico agregado del comando permite comprobar pendientes.

## Procedimiento administrativo

Primero contar pendientes, sin escribir datos:

```powershell
.venv/Scripts/python.exe manage.py recuperar_codigos_reservas
.venv/Scripts/python.exe manage.py recuperar_codigos_reservas --unidad 16
```

El comando acepta `--database` entre los aliases configurados. La unidad de
ejemplo debe reemplazarse por la unidad cuyo alcance haya verificado el operador.
La auditoria predeterminada solo consulta; no repara automaticamente el conjunto.
En desarrollo se ejecuto la auditoria y encontro **0 pendientes**; no se aplico
una reparacion sobre datos reales.

Para escribir, indicar explicitamente una unidad positiva:

```powershell
.venv/Scripts/python.exe manage.py recuperar_codigos_reservas --aplicar --unidad 16
```

Se seleccionan codigos NULL/vacios de esa unidad. Cada fila tiene su propia
transaccion y se comprueba nuevamente la unidad bajo bloqueo. Si cambio de
unidad entre seleccion y bloqueo, no se asigna el codigo. Una fila fallida no
revierte las asignaciones exitosas de otras filas; no hay atomicidad global del
lote. Los codigos existentes se conservan al reintentar.
Si el codigo canonico ya pertenece a otra reserva, se conserva la restriccion
de unicidad y la fila queda pendiente. Investigar la colision con acceso
administrativo autorizado; el comando no inventa sufijos ni altera el otro codigo.

La salida JSON solo incluye modo y contadores: pendientes_observados, asignados,
ya_existentes, fuera_de_alcance y fallidos. Un fallo o cambio de alcance produce
CommandError y estado de salida no exitoso despues del resumen parcial. Un error
al consultar/iterar produce un mensaje operativo generico y el evento fijo
`reserva_codigo_recuperacion_fallida`. Bajo concurrencia, el conteo inicial no es
una instantanea inmutable y puede diferir del total procesado.

La herramienta requiere un operador autorizado mediante acceso al sistema
operativo y credenciales de base. No es una API HTTP ni verifica permisos de
usuario/objeto por si misma. Si otro caso de uso invoca el servicio, debe validar
su autoridad antes. La separacion de credenciales/roles/procesos y la politica
de respaldo/restauracion siguen en M11/M01; este cambio no las reemplaza.

## Consumidores revisados

Se conserva el campo y el momento de asignacion; no se reescriben sus fallbacks.
La revision de referencias en dominios encontro los siguientes grupos:

| Area | Archivos de referencia en webcitt/domains/unidades | Uso del codigo |
| --- | --- | --- |
| Reservas | reservas/views.py, forms.py, ejecucion.py, comprobantes.py | Mensajes, referencias, cierre, documentos y servicios |
| Guias | reservas/guia_firmas.py, guia_automatizacion.py | Referencia de reserva fuente y firmas |
| Docencia | aula.py, asignaturas.py, practicas.py, planificacion.py | Etiquetas, busquedas, sesiones y planes |
| Operacion | gestion.py, gestion_produccion.py, seguridad.py | Resumen, conflictos, induccion y trabajos |
| Maquila | maquila.py | Referencias de lotes de cliente y actas de entrega |
| Reportes | gestion_reportes.py, reportes_excel.py | Busquedas y exportaciones |

Al crear una sesion recurrente, views.py limpia el codigo de la copia con nueva
identidad; la asignacion del nuevo registro se mantiene. Recuperar un codigo
faltante no modifica referencias ya materializadas en documentos u otros
registros. Tampoco vuelve a generar QR, guias, eventos, fechas o historial.

La preservacion de codigos existentes corresponde a este servicio. No impide
que escrituras directas ORM/SQL u otro guardado de una instancia obsoleta
modifiquen el campo fuera del servicio. Los contratos completos de escritura,
permisos y restricciones de capacidad deben cubrir esos otros caminos antes
de ofrecer una suspension de reservas por unidad.

## Revision y continuidad

El contrato de asignar_codigo_reserva declara fallo no bloqueante observable,
alias propagado al servicio y savepoint para codigo. El auditor mantiene 19
contratos/decoradores/conexiones y revisa seis archivos, incluido el servicio.
Las huellas se actualizaron tras revisar el diff y las pruebas; no son una
firma de seguridad ni cobertura de dependencias externas.

Hay 17 pruebas nuevas: identidad, instancias obsoletas, NULL/vacio, raw/using,
constructor sin SQL, ausencia de reentrada, error de unicidad real sin romper
la transaccion del llamador, logs sin detalles, diagnostico de solo lectura,
alcance de unidad, cambio de alcance, recuperacion parcial/reintento y carrera
entre dos conexiones reales. Las pruebas usan test_citt_db con datos sinteticos.
La verificacion integral y su resultado se registran en CODEX_CONTEXT, bloque 163.

M02.4 sigue parcial: falta revisar todos los escritores, validadores, tareas y
consumidores de la capacidad de reservas y otras capacidades. El siguiente
paso es acotar esos caminos y su autoridad por unidad antes de implementar
guardas de suspension; despues categorias/extensiones y extraccion por vertical.
Ese contrato debe distinguir nuevas operaciones de mantenimiento del historial:
definir explicitamente la autoridad de esta recuperacion si reservas esta
suspendida, sin habilitar por ello creacion, aprobacion o ejecucion de reservas.
M02.2/M02.3/M01 institucional/M11 siguen abiertos. Proceso, base y URLconf siguen
compartidos: separar este servicio no garantiza aislamiento de disponibilidad.

La continuacion 164 revisa entradas principales y refuerza autoridad/fila fresca
de completar_sesion y aplicar_solicitud_cambio. No instala suspension de reservas;
el cierre operativo y otros escritores siguen pendientes.
[Matriz y siguiente secuencia](escritores-y-autoridad-reservas.md).

Referencias: [contratos de senales](contratos-senales-heredadas.md),
[inventario de superficies](superficies-y-autoridades-capacidades.md),
[controles de capacidades](controles-capacidades.md),
[ruta](ruta-ejecucion-arquitectura-modular.md).
