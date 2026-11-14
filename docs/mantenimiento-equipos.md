# Mantenimiento, incidencias y ciclo de vida de equipos

Este bloque administra activos físicos asignados a cualquiera de las cuatro
clases de unidad: laboratorios, observatorios, centros experimentales y plantas
piloto. No replica inventarios por tipo de unidad; todos parten de
`UnidadEquipo` y conservan una trazabilidad común.

## Alcance implementado

- `PlanMantenimientoEquipo`: periodicidad, anticipación, responsable,
  proveedor e instrucciones del mantenimiento preventivo.
- `IncidenciaEquipo`: reporte, prioridad, responsable de atención, evidencia,
  solución y cierre. Una incidencia bloqueante retira temporalmente el activo
  de servicio.
- `MantenimientoEquipo`: orden planificada o correctiva, fechas, responsable,
  proveedor, costo, resultado, informe y próxima intervención.
- `EventoCicloVidaEquipo`: bitácora de registro, asignación, transferencia,
  cambios de estado, incidencias, mantenimientos y baja del activo.
- `DiagnosticoIncidenciaEquipo`: garantía revisada, causa, impacto, componente
  afectado, atención, plazo y decisión técnica fundamentada.
- `ServicioReparacionEquipo`: alcance real del servicio interno, familias de
  equipos que puede atender y capacidad mensual declarada.

Las unidades nacen con estas tres capacidades activas en
`ConfiguracionOperativaUnidad`, pero pueden deshabilitarse individualmente
desde el administrador cuando una unidad no las requiera.

## Flujo operativo

1. El equipo físico se registra y se asigna a una unidad.
2. El sistema crea el primer evento de ciclo de vida.
3. Se define un plan preventivo o se reporta una incidencia.
4. Una orden de mantenimiento concentra la ejecución y sus evidencias.
5. El cierre actualiza el estado del equipo, la última intervención, la próxima
   fecha y la bitácora.

## Fallas tempranas, garantía y componentes

En **Gestionar unidad → Mantenimiento e incidencias**, la cola «Fallas,
garantía y repuestos» ordena las incidencias abiertas por detención operativa,
prioridad y antigüedad. Identifica fallas anteriores al fin de vida útil
documentado, evaluaciones pendientes, ausencia de cobertura interna declarada
y respuestas cuyo plazo previsto venció. Una referencia de vida útil ausente
no se sustituye por una antigüedad inventada.

El botón **Diagnóstico** reutiliza el equipo y la unidad de la incidencia.
Registra hallazgos, impacto sobre las actividades y revisión de garantía.
Estar dentro del plazo de garantía no prueba que la avería esté cubierta:
antes de decidir reparación, repuesto o reposición, se exige documentar su
cobertura, exclusión o falta de información. La elección de cambiar una pieza
requiere nombre o pieza del catálogo del modelo, cantidad y compatibilidad.
La avería de un accesorio no propone reemplazar automáticamente todo el activo.

La decisión compara reparación, garantía, pieza y reposición en seguridad,
costo, plazo y continuidad. Puede permanecer en evaluación mientras faltan
pruebas. El presupuesto estimado y la respuesta del servicio admiten un dato
pendiente; no se convierten en costos pagados ni en compras ejecutadas.
Cada modificación del diagnóstico conserva otro evento en el ciclo de vida.

## Centro de reparación y capacidad disponible

Dirección configura **Servicios internos de reparación** en el administrador
de Recursos. Debe declarar las familias exactas, trabajos admitidos,
exclusiones, contacto y, cuando se conozca, capacidad mensual. No se crea un
centro ficticio ni se presupone que el servicio informático atiende equipos
de otras especialidades. La selección de un servicio fuera de su cobertura
se rechaza; la unidad puede registrar una derivación especializada externa.

La derivación conserva fecha, respuesta prevista, respuesta recibida, costo
y plazo estimados. El panel muestra los casos sin cobertura y las respuestas
vencidas. El administrador del servicio contrasta capacidad mensual declarada
y casos pendientes. Es evidencia para evaluar ampliaciones; no acredita que
esa ampliación ya exista ni que esté financiada.

## Ejecución, financiación y retorno al servicio

**Programar atención** abre una orden correctiva ya vinculada al activo y a
la incidencia. Las piezas se registran en **Piezas utilizadas en las órdenes**
con cantidad, costo unitario, procedencia y referencia de adquisición,
garantía o salida de inventario. Una pieza del catálogo debe corresponder al
modelo del equipo; su cambio aparece en la ficha del activo. El registro
conserva además un evento con la orden y sus datos de respaldo.

La financiación de autogestión se conserva separada de la revisión
administrativa. Ni la urgencia ni un valor pequeño determinan automáticamente
una compra directa. El área competente debe verificar el procedimiento y
su autorización; los egresos se registran en Finanzas y los consumos de
inventario por su flujo, vinculados al equipo o a la orden cuando proceda.
Registrar una pieza no duplica un egreso ni descuenta existencias por sí solo.

Una intervención diagnosticada exige inicio real, resultado y prueba de
funcionamiento antes de completarse. Un resultado no apto o limitado mantiene
el activo fuera de la disponibilidad general. Resolver una incidencia cuya
decisión fue reparación o repuesto exige una orden completada con prueba
apta. Los registros históricos sin diagnóstico conservan sus reglas previas;
no se inventan pruebas para cerrarlos retrospectivamente.

La propuesta anual de compras puede reutilizar un diagnóstico abierto y
justificado, con su identificador, activo padre, componente, cantidad y
especificación. No propone otra compra cuando la incidencia está cerrada,
la reparación ya tiene prueba apta o la solución está cubierta por garantía,
existencias o donación. La propuesta se revisa antes de emitirla y se conserva
en la captura del documento enviado.

Una incidencia no puede cerrarse sin solución y una orden no puede completarse
sin resultado. Los planes, incidencias y órdenes vinculados deben pertenecer al
mismo equipo.

El estado operativo anterior se conserva mientras exista un bloqueo temporal.
Si coinciden varias incidencias o mantenimientos, una incidencia bloqueante
tiene prioridad visual sobre el estado de mantenimiento. Al resolver o cancelar
el último bloqueo, el equipo recupera el estado que tenía antes del primero; no
se fuerza artificialmente a `disponible`.

## Acceso administrativo

Los registros se limitan a las unidades gestionables por cada usuario. El
portal exige el permiso de mantenimiento de esa unidad para registrar
diagnósticos, órdenes y piezas. Dirección conserva el acceso institucional y
configura la cobertura de los servicios internos.

## Tablero operativo

El detalle de cada unidad muestra a sus responsables un resumen calculado, sin
copiar ni persistir cifras derivadas. El tablero reúne disponibilidad de
equipos, cobertura y vencimientos de mantenimiento, incidencias abiertas y
umbrales de consumibles. También prioriza las alertas críticas y respeta las
capacidades que hayan sido desactivadas para esa unidad.

## Verificación

`test_reparacion_trazabilidad` cubre fallas tempranas, garantía, repuestos,
cobertura por familia, autogestión separada del procedimiento, conservación
de revisiones, fechas de corte, cierre con prueba, estado no apto y permisos
entre unidades. La migración `recursos.0004_diagnostico_reparacion_equipos`
añade los campos sin cambiar registros, capacidades institucionales ni
decisiones anteriores.
