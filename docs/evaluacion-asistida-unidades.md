# Evaluación asistida de documentos de unidades

> **Regla vigente desde el 15 de noviembre de 2026:** solo el informe semestral se califica, con el
> cumplimiento de las metas de su planificación; los demás documentos son de cumplimiento obligatorio y no
> reciben porcentaje. Lo que aquí se dice sobre porcentajes, rúbricas o calificación a mano quedó
> reemplazado por [calificacion-y-anexos-del-expediente.md](calificacion-y-anexos-del-expediente.md).

Prioridad solicitada tras el paso 4, antes de la limpieza del paso 5.

## Recorrido

Los enlaces a cumplimiento usan el slug de la unidad. La vista también admite
los identificadores numéricos emitidos anteriormente y los normaliza, buscando
solo entre las unidades autorizadas. Verificación de solo lectura sobre los
casos reportados (unidades 3 y 9): ambas vistas responden 200.
Regresión: seis casos correctos, incluidos los enlaces reales de los tres
reportes; el caso de permisos pasó al corregir su preparación y repetirlo.

En «Evidencias por tipo de unidad», las cifras abren el informe de respaldo
en el visor PDF del administrador, conservando categoría y fechas. «Revisar
cumplimiento» abre el tablero administrativo de la unidad. La consulta del
responsable sigue disponible como «Informes de respaldo», con el selector
plegado y retorno a las entregas del período; no es otra pantalla de evaluación.
Validación: 15 casos correctos en la ejecución inicial y el caso de navegación
actualizado correcto en una ejecución posterior; PDF inline, fechas y rechazo
de acceso a unidades ajenas comprobados.

«Reporte institucional» se consulta desde Reportes e indicadores dentro del
administrador, con filtros y visor PDF. Comparte datos y contenido con la
exportación; la URL anterior redirige al administrador para usuarios staff
cuando se solicita HTML. La consulta autorizada del portal para usuarios sin
acceso al administrador se conserva.

«Resumen anual de entregas» es el nombre del anterior «Expediente de calidad
por tipo de unidad»: compara A, B y documentos anuales. Sus enlaces conducen
al cumplimiento de la unidad y el año seleccionado dentro del administrador.
Validación: 13 pruebas correctas de navegación administrativa, permisos,
filtros, PDF y resumen anual; incluye el reporte sin unidades registradas.

La calificación se realiza exclusivamente en el administrador de la Dirección.
El Centro de reportes y el expediente de la unidad no muestran el formulario,
incluso cuando accede un superusuario; su endpoint rechaza con 403 las acciones
de calificación. La unidad conserva la consulta de resultados y observaciones.
Regresión de esta separación: 12 pruebas correctas de evaluación y rúbrica,
incluido el rechazo del POST para coordinador y superusuario y la consulta
del resultado por la unidad; Ruff sin incidencias.

1. En Cumplimiento del expediente, abrir el acordeón de la unidad.
2. Seleccionar Revisar y continuar, Calificar o Recibir y evaluar.
3. Abrir el PDF, contrastar las comprobaciones y seleccionar los cuatro niveles.
4. Confirmar la revisión y guardar: nota, observaciones y recomendaciones se
   calculan en el servidor. La revisión permanece abierta en el mismo documento.

El PDF generado permite revisión previa; no equivale a una entrega firmada.
Si falta firma, recepción o habilitación tardía, la pantalla explica el paso
pendiente. Las reglas anteriores de carga, recepción y tardanza se conservan.
No se califican documentos reales durante las verificaciones de desarrollo.

## Rúbrica y métricas

El avance del editor indica campos completados, no firma ni calificación;
se oculta después del envío. Cada obligación pendiente identifica si falta
entrega, firma o evaluación. Los borradores vencidos sin envío cuentan cero
en ambos tableros, aunque tengan un PDF archivado; lo entregado pendiente de
evaluación no recibe una nota ficticia. Los pendientes sin plazo siguen siendo
obligatorios. El promedio mostrado es el resultado actual y puede cambiar.

«Habilitar expediente del año» aparece solo si faltan registros. El POST crea
esos registros de forma idempotente, sin generar PDFs ni validar entregas;
consultar un año sigue siendo una operación de lectura.
Validación de estos ajustes: 11 pruebas correctas de cumplimiento, presentación
y preparación idempotente, ejecutadas sin reutilizar la base de pruebas.

`evaluacion_rubrica.py` define la versión `gestion-unidades-1`. Cada documento
tiene cuatro criterios de 25 puntos: planificación, informe semestral, compras,
resolución y protocolo tienen criterios propios. Otros documentos usan un
conjunto general de integridad, evidencia, coherencia y resultados/mejora.

Cada criterio se valora en 0, 25, 50, 75 o 100 %, con descriptores de ausencia,
insuficiencia, cumplimiento parcial, adecuado o completo. El promedio se
redondea al entero más cercano, elevando los medios puntos. Se aplica una sola
vez el descuento vigente por tardanza. El mínimo procede de la política de
calidad existente; no se modifica la política institucional.

La nota final de 90 o más y por encima del mínimo reconoce «Gestión destacada».
Las deficiencias generan debilidades y recomendaciones por criterio; una nota
bajo el mínimo conserva el circuito de mejora continua. No se crean sanciones
laborales, incentivos económicos ni cambios de responsables automáticos.

La auditoría de apoyo lee la completitud del editor y, en informes, las metas
medibles y cumplidas según los registros. Los campos pendientes se enumeran.
La integridad propone un nivel aproximado; los otros criterios requieren que
la Dirección seleccione su nivel. Se evalúa respecto de las funciones, metas
y recursos de cada unidad, evitando premiar solamente el volumen de equipos
o de actividades.

Estos indicadores reflejan datos actuales: no se presentan como extracción
del PDF ni como verificación de su veracidad. La Dirección debe contrastarlos
con el archivo, confirmar y, si corresponde, corregir la sugerencia. No se
utiliza un servicio externo de IA ni se envían documentos a terceros.

## Seguridad y auditoría

El guardado utiliza el bloqueo por unidad y los comandos del expediente.
Comprueba autoridad, firma, recepción, versión, huella y niveles permitidos.
Rechaza revisiones obsoletas y formularios sin confirmación. La nota del cliente
no se acepta como autoridad: se recalcula con los cuatro valores permitidos.

El historial existente conserva usuario, fecha, versión de rúbrica, criterios,
valores, motivos, versión del documento, recurso, SHA-256, descuento, mínimo,
nota y observaciones. Se muestran las últimas cinco evaluaciones con rúbrica;
el historial completo permanece en la auditoría de la unidad. No se necesita
migración ni se alteran las evaluaciones históricas anteriores.

## Presentación

Las unidades se abren como acordeones, uno a la vez. La revisión usa un panel
en el flujo de la página, con dos columnas adaptables a una en pantallas
estrechas. La matriz documental tiene desplazamiento horizontal propio.

El visor compartido se monta directamente en `body` para evitar quedar bajo
el encabezado del administrador o encerrado por un contenedor. Sus dimensiones
se limitan al viewport, el título admite varias líneas y descarga/cierre
conservan su espacio. Se conserva PDF.js y su comportamiento de carga existente.

## Validación

- Ocho pruebas nuevas de rúbrica, permisos, versiones, cálculo y navegación.
  Verificación específica final: 34 pruebas correctas.
- Comprobación visual en Chrome con una copia local de la vista renderizada y
  el PDF del período B: siete páginas dibujadas. A 1440 × 1000 se ven título,
  descarga, cierre, miniaturas y zoom sin solaparse. A 390 × 844, el título y
  el cierre quedan dentro del viewport y la revisión no desborda la página.
- Se corrigió también el margen negativo que Grappelli heredaba a los botones
  de zoom. El ajuste visual se comprobó mientras corría la suite integral;
  el código Python y JavaScript se mantuvo estable durante esa ejecución.
- Comprobaciones Django, Ruff de los archivos modificados y detección de
  migraciones correctas; no hay cambios de esquema.
- Recorrido administrativo: 749 pantallas, ninguna falla.
- Suite integral: 1.827 pruebas en 1.414 segundos, una omitida y dos fallos
  de presentación: la expectativa del ancho anterior del visor y la etiqueta
  «Nivel» del resumen. Se corrigieron ambos durante el cierre. La ejecución
  integral no se repitió; los dos casos se ejecutaron de nuevo sobre una base
  de pruebas nueva y ambos pasaron.
