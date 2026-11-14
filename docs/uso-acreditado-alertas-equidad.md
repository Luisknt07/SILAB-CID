# Seguimiento del uso de equipos

La consulta **Uso, alertas y redistribución**, disponible desde el inventario
del administrador, muestra cada activo físico, su unidad, áreas, estado,
horas acreditadas, actividades fuente, cierres pendientes y compromiso de uso.
Dirección puede consultar el conjunto; el personal autorizado consulta sus
unidades. El HTML pagina los activos y las actividades. El CSV conserva todos
los resultados filtrados.

## Qué demuestra uso

Se exige una atención completada y atendida con horario real, asistencia
positiva, fecha de cierre al corte y equipos reales capturados en el cierre.
Las prácticas, servicios y otras finalidades usan el mismo criterio. Los
equipos solicitados o una actividad planificada no acreditan uso. Un cierre
incompleto se señala para regularizar y no permite afirmar abandono.

Los IDs físicos prevalecen sobre el código; los códigos anteriores se resuelven
mediante sus alias. Un activo compartido se cuenta una vez y la lectura
conserva las unidades y finalidades que lo utilizaron. Si hay franjas
simultáneas para el mismo activo, el tiempo se une y la coincidencia queda
señalada. La suma de las dimensiones puede solaparse; no sustituye al total
conciliado del activo.

## Política y oportunidad de corregir

Dirección configura la **Política de seguimiento del uso de equipos**:

- Días sin uso acreditado para iniciar la revisión.
- Mínimo de horas acreditadas en doce meses, si se adopta esta regla.
- Días de atención después de comunicar una alerta.
- Fundamento de la política.

No se cargan valores por defecto. Sin política configurada siguen disponibles
las mediciones y las advertencias de calidad de datos, pero no se abren alertas
institucionales de inactividad ni se habilita la revisión por redistribución.
La ausencia de fecha de ingreso tampoco se convierte en antigüedad supuesta.

Cada alerta conserva su lectura fuente. La unidad puede documentar actividades
y responsable en el compromiso. Dirección registra una comunicación realizada
y su fecha: guardar el campo no envía mensajes. Si existe un plazo institucional
de atención y no se indicó otro, se calcula la fecha de revisión desde esa
comunicación. Dirección puede acordar una fecha específica por alerta.

El vencimiento sin uso nuevo sólo habilita **revisar una posible
redistribución**. Cierres pendientes, falta de política, equipos nuevos o fuera
de servicio impiden tratar la alerta como candidata. La falta de registros no
prueba falta de uso físico: deben verificarse las causas, disponibilidad,
custodia y necesidades de la unidad receptora. El traspaso conserva solicitud,
aprobación de Dirección, entrega y recepción, códigos anteriores y acta. No se
ejecutan movimientos automáticos.

## Actualización

Las consultas no crean ni cierran alertas. Después de guardar o eliminar una
actividad, una función `on_commit` revisa su unidad; una transacción revertida
no publica cambios. Para detectar el transcurso del tiempo sin actividad, el
programador existente `scripts/docker_scheduler.sh` ejecuta también
`detectar_equipos_sin_uso` en su ciclo configurado.

Una instalación local sin ese programador puede ejecutar un monitor separado:

```powershell
.venv/Scripts/python.exe manage.py vigilar_uso_equipos --intervalo 60
```

El intervalo sólo controla la frecuencia de lectura; no establece una política
de uso ni un plazo para responder. `--una-vez` realiza una revisión y termina.
El comando `detectar_equipos_sin_uso --simular` conserva una revisión sin
mutaciones. Ninguno de estos comandos comunica a terceros ni ejecuta traspasos.
