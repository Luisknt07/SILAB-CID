# Reservas, servicios y visitas en el mismo asistente — 8 de noviembre de 2026

Las tres tarjetas seleccionan una ruta dentro de `equiposReservaModal` y se
avanza con **Continuar**. Visitas usa el mismo formulario `reservaForm`, los
mismos cinco paneles, acciones, selección mensual/semanal y calendario de
ocupación ya aprobado para recursos y servicios.

## Flujo final de visitas

1. **Forma de atención:** elegir la tercera tarjeta, sin navegar a otra página.
2. **Grupo y finalidad:** responsable desde el perfil, institución/grupo,
   propósito, visitantes, edades, interés y lista de asistentes opcional.
3. **Recorrido y calendario:** áreas visitables y la agenda integrada existente.
   Muestra ocupación, eventos, capacidad y conflictos; permite elegir bloques
   consecutivos y conserva los controles de mes, semana y detalle de actividad.
4. **Requisitos y condiciones:** oferta de la unidad, áreas permitidas y
   excluidas, protección, guías, valor estimado y aceptación del responsable.
5. **Confirmación:** resumen de grupo, recorrido, horario, guías y condiciones;
   el envío final usa `/reservas/crear/` y devuelve el comprobante habitual.

La agenda consulta `/api/laboratorio/<id>/calendario/` para las tres rutas.
Para visitas proyecta exclusivamente el recorrido y el número de visitantes
más sus guías, sin arrastrar equipos o software de otra selección. Antes de
elegir áreas muestra conservadoramente la ocupación de la unidad completa.
Una consulta fallida o pendiente no habilita horas como si estuvieran libres.
El alta vuelve a comprobar perfil, fecha, bloques consecutivos, aforo,
restricciones, requisitos y conflictos, con el bloqueo transaccional existente.

El controlador de visitas adapta los paneles y restaura el estado de controles
al cambiar a recursos o servicios; conserva sus valores sin exigir datos de
otras rutas. Los datos de visita permanecen al volver a su tarjeta.

Se retiraron la página/formulario y el calendario independientes, su API JSON,
su JavaScript y sus estilos de agenda. Los enlaces antiguos a
`visitas/solicitar/` redirigen a la ficha con `?reserva=visita`, que abre el modal
y selecciona su tercera tarjeta. El POST anterior conserva compatibilidad,
sin mantener una segunda interfaz de reserva.

## Oferta y activación conservadas

Se mantienen las 27 unidades activas solicitadas (laboratorios, centros
experimentales y plantas piloto), además de los cinco observatorios que ya
recibían visitas. Las áreas y requisitos publicados no se abren ni cambian
automáticamente. Sin áreas publicadas se solicita presentación y orientación
con recorrido a confirmar; ocupa conservadoramente la unidad completa.

La activación anterior cambió veinte banderas y conservó siete ya activas.
Respaldo: `var/backups/visitas/configuracion-20261109-034421-147407.json` (UTC).
La migración gestion_unidades.0003 cambió el valor por defecto en el estado de
Django, SQL no-op; permanece aplicada. Esta corrección no añade migraciones
ni modifica datos operativos. La oferta se mantiene desde el panel de la
unidad; los requisitos de visitantes se mantienen desde Seguridad.

## Verificación y límites

- 52 pruebas Django correctas con PostgreSQL temporal aislado: visitas,
  envío del modal, agenda compartida, conflictos y elegibilidad de reservas.
- 19 pruebas JavaScript correctas: proyección de visitantes/guías, consulta
  a la API común, fallos y respuestas tardías, y resúmenes de recursos.
- Prueba de componentes sobre HTML público real y scripts completos del
  asistente: selección de visita, cinco pasos, resumen, regreso a recursos y
  servicios, conservación de datos y un único `monthGrid`. Se ejecutó con
  LinkeDOM en `var/qa-visitas-modal/check.cjs`, sin dependencias del producto:
  Frutas, FabLab, San Francisco y Cítricos sin áreas publicadas correctos.
- 81 HTTP correctos en las 27 unidades: ficha/modal, enlace anterior y API
  compartida. Cuatro estáticos entregados por 8000 coinciden con las fuentes
  por SHA-256. Evidencia: `var/qa-visitas-modal/http.json`.
- Django check, Ruff, sintaxis JavaScript, migraciones y diferencias correctos.
- Computer Use volvió a bloquear la revisión visual porque no pudo verificar
  la URL de Chrome. La prueba DOM no acredita geometría ni apariencia visual.

Las solicitudes de prueba se crearon solo en QA; no se enviaron solicitudes ni
correos operativos a las unidades. PostgreSQL temporal y sus volúmenes retirados
al finalizar. Los commits anteriores c5bf33f5 y 1acacd52
se publicaron con autorización expresa. Consultar Git para esta corrección.
Sin despliegue universitario.
