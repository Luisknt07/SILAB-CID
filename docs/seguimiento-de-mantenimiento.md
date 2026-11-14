# Seguimiento del mantenimiento de equipos

Fecha: 22 de septiembre de 2026. Rama `reestructura-modular`.

El mantenimiento se audita equipo por equipo, desde que el activo entra hasta
que se da de baja. Todo se resume en un semáforo y en gráficos, de modo que la
unidad y la Dirección vean de un vistazo qué está al día y qué no.

## Qué mira el semáforo

`webcitt/domains/unidades/mantenimiento_panel.py` clasifica cada equipo en
tres estados y explica por qué, en este orden:

| Estado | Cuándo | Qué lo dispara |
| --- | --- | --- |
| **Requiere intervención** | Detiene o compromete el servicio | Fuera de servicio por daño, plan de mantenimiento vencido, o equipo crítico sin plan vigente |
| **Requiere atención** | No detiene, pero hay que actuar | Incidencias abiertas, mantenimiento por vencer, vida útil sobre el 80 %, equipo en mantenimiento |
| **Al día** | Sin novedades | Con plan vigente y sin pendientes |

Un equipo dado de baja sale del semáforo operativo y pasa al cierre de ciclo,
con su motivo, su acta y el equipo que lo reemplaza.

## Qué datos lo sostienen

Se añadieron al activo (`UnidadEquipo`) los datos que faltaban para auditar:

- **Criticidad** (crítico, importante, normal). Un equipo crítico sin plan es
  una falta, uno normal no.
- **Vida útil en años** y **garantía**. De ahí sale el porcentaje de vida
  consumida, la alerta de renovación y la obsolescencia.
- **Baja**: fecha, motivo (obsolescencia, fin de vida útil, daño irreparable,
  pérdida, transferencia, otro), acta o justificación y **equipo que lo
  reemplaza**. Al registrarla queda un evento en el ciclo de vida del activo.
- **Repuestos** de cada orden (`RepuestoMantenimiento`): la pieza que se
  reemplazó, descripción, cantidad, costo unitario y procedencia (inventario,
  compra, garantía o proveedor del servicio). Es lo que permite saber cuánto
  cuesta sostener cada equipo.
- **Costo**: el de la orden es el del servicio, es decir la mano de obra del
  técnico externo; los repuestos suman aparte con su cantidad y su precio. El
  costo acumulado del activo es la suma de ambos, así que no se registra el
  repuesto dos veces.

## Qué muestra el panel de la consola

Pestaña *Mantenimiento e incidencias* de la unidad:

1. **Cifras con semáforo**: equipos en operación y fuera de servicio,
   cobertura de planes (y críticos sin plan), mantenimientos vencidos y por
   vencer, incidencias abiertas, cumplimiento del plan y costo acumulado.
2. **Programado frente a ejecutado**: barras de los últimos doce meses, la
   clara es lo programado y la oscura lo completado.
3. **Estado de los equipos** y **vida útil**: barras con el reparto del parque.
4. **Qué le toca a cada equipo**: plan y frecuencia, responsable o proveedor,
   último y próximo mantenimiento con los días que faltan, órdenes ejecutadas
   sobre programadas, incidencias abiertas, días detenido, vida útil y costo.
   Los que requieren intervención van primero. Cada dato aparece una sola vez:
   el semáforo muestra su etiqueta y guarda el motivo en su título, porque las
   columnas de próximo, órdenes y vida útil ya lo dicen con su fecha; la
   criticidad se reduce a una palabra.
5. **Lo que viene**: los planes ordenados por urgencia —vencidos, esta semana,
   este mes y más adelante—, cada uno con su día, su equipo, quién lo ejecuta y
   el botón que programa su orden ya rellenada. Sustituye al listado de planes,
   que repetía lo que la tabla dice equipo por equipo.
6. **Equipos dados de baja**: motivo, acta y reemplazo.
7. Debajo siguen las tarjetas de operación: reportar incidencias y programar
   órdenes.

## Reportar una novedad

El formulario de incidencia se usa con el equipo delante y con prisa, así que
no pide abrir tres menús desplegables iguales:

- El **equipo** se elige una vez y queda a la vista con su fotografía, su
  código, su estado y su ubicación, para confirmar que es el correcto.
- El **tipo** son tarjetas con icono: falla, seguridad, calibración, accesorio
  o pieza, software y otro.
- La **prioridad** es una escala de cuatro pasos que toma color al elegirla.
- El **estado** es la ruta de la novedad: abierta, en evaluación, en
  reparación, resuelta, cerrada o descartada. Al elegir resuelta o cerrada, la
  solución se marca y se exige, que es lo que ya validaba el registro.
- El **impacto** explica su consecuencia: marcarlo deja el equipo fuera de
  servicio y lo retira de las reservas hasta cerrar la incidencia.

La orden de mantenimiento declara además **quién la ejecuta** y el **costo del
servicio**, que antes solo podían registrarse desde el administrador.

## La ficha del activo

En la tabla del seguimiento cada fila lleva la fotografía pequeña del equipo
y su nombre completo con marca y modelo; el nombre abre la ficha
(`gestion/unidades/<slug>/equipos/<id>/`), que relaciona el mantenimiento con
el equipo real del inventario. *Ver la ficha en PDF* abre el documento en el
visor de la plataforma, el mismo del aula y del expediente, sin salir de la
página; el botón de descarga está dentro del visor. El visor lee el documento
como el reporte operativo: el ancho de su hoja, papel blanco sobre lienzo gris
neutro y la cabecera verde con su filo dorado. El PDF (`.../ficha.pdf`)
lleva el marco institucional, igual que el plan de mantenimiento:

1. **Identidad**: fotografía, categoría, marca y modelo, número de serie,
   ubicación, adquisición, valor, garantía, criticidad y semáforo con sus
   motivos. La fotografía y la categoría son exactamente las del catálogo de
   reservas (`EquiposServicios.imagen_publica_url` y `categoria_publica_equipo`):
   una sola fuente, sin duplicar el dato.
2. **Ciclo de vida**: cuánta vida le queda y por qué se cerrará su ciclo, con
   el porcentaje por tiempo y por horas de operación. Si está de baja, el
   motivo, el acta y el equipo que lo reemplaza, o el aviso de que la vacante
   sigue abierta.
3. **Nivel de uso**: sesiones, horas efectivas, usuarios y horas acumuladas,
   con barras por mes, y el espacio o área desde el que se reserva (la misma
   categorización de las reservas).
4. **Qué contiene**: características, para qué sirve, cómo se opera, equipos
   auxiliares, accesorios que llegan con el equipo, insumos compatibles con su
   existencia, software instalado, documentación técnica y los otros activos
   del mismo tipo.
5. **Piezas, herramientas y protección**: las partes de la máquina, aparte de
   los insumos, con lo que se le ha cambiado a ese activo.
6. **Plan y fichas de estado**: el plan vigente con su frecuencia, quién lo
   ejecuta e instrucciones, y una ficha por cada intervención con lo que se
   hizo, quién la ejecutó, cuánto se detuvo el equipo, su origen (plan o
   incidencia), sus repuestos con cantidad, costo y procedencia, y el informe
   adjunto.
7. **Trazabilidad**: la línea de tiempo desde que el activo entró al
   laboratorio, con los cambios de estado, incidencias, mantenimientos y baja.

## De dónde sale cada dato y por dónde se corrige

La ficha no guarda información propia: reúne la que ya vive en su sitio. Para
que nadie la vuelva a escribir aparte, cada tarjeta cierra con una línea que
dice de dónde sale y ofrece la pantalla donde se edita, solo a quien tiene
permiso de entrar en ella.

| Bloque | De dónde sale | Dónde se corrige |
| --- | --- | --- |
| Fotografía, categoría, características, accesorios | Ficha técnica del equipo en el catálogo, la misma que ve quien reserva; vale para todos los activos de ese tipo | Ficha técnica del equipo |
| Serie, ubicación, estado, criticidad, adquisición, garantía | El activo, y solo él | Equipo de la unidad |
| Vida útil y baja | El activo; si no declara vida útil, la de referencia del tipo | Equipo de la unidad |
| Horas de operación y nivel de uso | Se calculan solos con las reservas atendidas | No se edita |
| Insumos, software, espacios | Inventario y recursos de la unidad | Insumos compatibles del equipo |
| Piezas | Se registran una vez por tipo de equipo; los cambios son los repuestos de las órdenes de este activo | Piezas del tipo de equipo |
| Plan y fichas de estado | Planes y órdenes de la unidad | Seguimiento de la unidad |
| Trazabilidad | Ingreso, cambios de estado, incidencias, mantenimientos y baja | No se edita |

El enlace apunta a la sección de la vertical de la unidad (laboratorios,
plantas piloto, centros experimentales u observatorios) y cae a la sección
común cuando la persona administra toda la plataforma. Si no tiene permiso en
ninguna, no se ofrece un enlace que terminaría en un aviso de acceso negado.
El fragmento es `portal/pages/unidades/gestion/includes/origen_del_dato.html`
y lo alimenta `origenes_de_la_ficha()`.

## Piezas y accesorios, que no son insumos

Un **insumo** se consume en el trabajo (filamento, resina, alcohol) y no
cambia cómo opera la máquina. Una **pieza** sí: la boquilla, el extrusor, la
cama o un sensor deciden si el equipo funciona y con qué calidad. Por eso se
registran aparte, en `PiezaEquipo`, colgando del tipo de equipo, con cuatro
clases:

| Clase | Qué es | Ejemplo en una impresora FDM |
| --- | --- | --- |
| **Componente** | Parte que decide el funcionamiento | Boquilla 0,4 mm, extrusor, cama con lámina PEI, termistor, sensor de nivelación, correas, cubierta y ventiladores |
| **Accesorio** | Viene con el equipo y sirve para operarlo | Espátula de desmontaje |
| **Herramienta** | Llave o útil de servicio | Juego de llaves Allen |
| **Protección** | Cuida el equipo o a quien lo opera | Regulador de voltaje o UPS |

Cada pieza declara cuántas lleva el equipo, si es **crítica** (sin ella no
opera, conviene tener repuesto), cada cuántas horas de operación suele
cambiarse, si hay repuesto en la unidad y la recomendación de cuidado que
alarga su vida. Un regulador de voltaje, por ejemplo, lleva la nota de
conectar siempre a través de él: un corte durante la impresión daña la
electrónica.

**Qué se le ha cambiado a este activo.** Cuando una orden reemplaza una
pieza, el repuesto (`RepuestoMantenimiento.pieza`) la señala. La ficha muestra
entonces cuántas veces se ha cambiado en ese equipo y la fecha de la última,
que es lo que permite distinguir un equipo bien cuidado de uno que consume
boquillas cada dos meses.

La migración 0218 siembra las piezas de referencia de las familias del
laboratorio de manufactura digital: impresión FDM y de resina, corte láser,
CNC, escaneo 3D, plotter de vinilo, computación y secado o curado. La familia
se reconoce por palabra completa del nombre, del código o de la categoría, y
la más específica manda: si no fuera así, «cad» casaría dentro de «secador» y
un molino terminaría con las piezas de una computadora de diseño.

## Ejemplos sembrados para ver cómo funciona

La migración 0219 deja armados, en el laboratorio de manufactura digital, los
tres casos que la unidad va a repetir. Son datos de partida: se editan o se
borran desde el administrador.

| Ejemplo | Equipo | Qué muestra |
| --- | --- | --- |
| Cambio de boquilla obstruida | Impresora FDM | Correctivo del laboratorista, repuesto del inventario ligado a la pieza, la ficha lo cuenta como cambio del activo |
| Reemplazo de la lámina PEI | Impresora FDM | Pieza de desgaste comprada, con la nota de cuánto duró la anterior |
| Limpieza mensual y tensión de correas | Impresora FDM | Preventivo del plan, sin repuestos ni costo |
| Cambio de película FEP | Impresora de resina | Pieza que la garantía excluye por ser de desgaste |
| Alineación del tubo y cambio de lente | Cortadora láser | Técnico externo: mano de obra en la orden, lente en el repuesto, nacido de una incidencia |
| Calibración de ejes y guías | Fresadora CNC | Calibración externa con certificado para el expediente |
| Reemplazo del extrusor | Impresora FDM nueva | Cubierto por la garantía: sin costo para la unidad, registrado igual |

También quedan dos activos recién adquiridos con la garantía corriendo, para
ver el aviso de días restantes, y piezas marcadas con repuesto en la unidad
frente a otras sin él, que es lo que hay que presupuestar.

## Quién ejecuta el mantenimiento

El plan y cada orden declaran el **ejecutor**, porque de eso dependen el costo
y el plazo:

| Ejecutor | Cuándo | Qué implica |
| --- | --- | --- |
| **Personal de la unidad** (laboratorista o técnico) | Rutina preventiva: limpieza, calibración, cambio de piezas de desgaste, ajuste de correas | Sin costo externo, se programa dentro de la jornada |
| **Técnico especializado externo o proveedor** | Electrónica de potencia, ópticas, husillos, calibración certificada, cualquier trabajo que exija instrumental propio | Se registra el proveedor y el costo; el equipo suele quedar detenido más tiempo |
| **Cubierto por la garantía** | Falla dentro del plazo del proveedor | Sin costo para la unidad; se registra igual para que quede la trazabilidad |

## Garantías

Cuando un equipo nuevo entra se registra en el activo cuántos **meses de
garantía** ofrece el proveedor y **qué cubre**, con su contacto. La fecha de
fin se calcula desde la adquisición, así que basta con declarar los meses; si
el proveedor entregó una fecha distinta se escribe directamente.

La ficha avisa si está vigente y cuántos días quedan, y recuerda que un
correctivo dentro del plazo se registra con ejecutor «cubierto por la
garantía» y sin costo para la unidad. Las garantías de referencia sembradas
para este laboratorio (migración 0218):

| Familia | Meses | Qué incluye |
| --- | --- | --- |
| Impresión 3D FDM y de resina | 12 | Partes y mano de obra por defecto de fabricación. No cubre boquillas, láminas ni películas FEP, que son piezas de desgaste, ni daños por corte eléctrico sin regulador |
| Corte láser y mecanizado CNC | 24 | Partes, mano de obra y dos visitas preventivas. No cubre ópticas, fresas ni daños por operar sin refrigeración o sin extracción |
| Escaneo 3D, computación y plotter | 12 | Partes y mano de obra en taller. No cubre golpes, humedad ni pérdida de accesorios |

Lo que la garantía excluye es justamente lo que la unidad debe presupuestar:
por eso las piezas de desgaste llevan sus horas de vida útil y la marca de si
hay repuesto disponible.

## Cuándo se cumple la vida útil

Un equipo llega al fin de su vida útil por lo que ocurra primero:

- **Por tiempo**: los años de vida útil desde su adquisición.
- **Por uso**: las horas de operación acumuladas, que salen de las sesiones
  atendidas en la plataforma.
- **Por daño**: una baja anticipada por daño irreparable.

La referencia la fija el tipo de equipo (`EquiposServicios`) y cada activo
puede ajustarla. Para el laboratorio de manufactura digital se sembraron estos
valores (migración 0216):

| Categoría | Años | Horas |
| --- | --- | --- |
| Impresión 3D FDM | 8 | 12 000 |
| Impresión en resina | 6 | 6 000 |
| Corte y grabado láser | 10 | 15 000 |
| Mecanizado CNC | 12 | 20 000 |
| Digitalización 3D | 7 | 8 000 |
| Computación especializada | 5 | 20 000 |
| Electrónica e instrumentación | 10 | 10 000 |
| Plotter de vinilo | 8 | 10 000 |
| Equipos de apoyo | 8 | 10 000 |

Al cumplirse, la ficha avisa que corresponde evaluar la renovación. La
reposición se registra dando de baja el activo con su motivo y señalando el
equipo que asume su función: así la vacante queda cubierta y ambas fichas
quedan enlazadas.

## El mantenimiento en el calendario

Un mantenimiento que no cierra sus horas termina chocando con una reserva ya
aceptada. Por eso cada orden declara su **duración prevista** y, salvo que se
indique lo contrario, **reserva el equipo en el calendario**: al guardarla se
crea el mismo tipo de cierre que usa la unidad para cualquier indisponibilidad
(`BloqueoAgendaUnidad` de tipo «mantenimiento», con alcance al equipo).

Eso significa que la intervención:

- aparece en la agenda de la unidad y en los cierres próximos, con su código y
  su título;
- impide reservar **ese** equipo en esas horas, sin tocar a los demás;
- se mueve sola si cambian la fecha, la hora o la duración;
- se libera si la orden se cancela;
- al completarse toma las horas que realmente duró, no las previstas.

El cierre nace de la orden y se mantiene con ella: no hay que registrarlo dos
veces ni recordarlo al reprogramar.

**No hay un segundo calendario en el seguimiento, y es a propósito.** El de la
unidad ya muestra estas intervenciones, porque lee los mismos cierres; repetir
la rejilla obligaría a mirar en dos sitios y a mantener dos vistas. Además una
rejilla mensual responde mal la pregunta del mantenimiento: diez planes
repartidos en doscientos días dan un mes casi vacío, mientras que lo que hace
falta es en qué orden atenderlos. Por eso el seguimiento ordena por urgencia y
tiende el puente: *Ver en la agenda* abre el calendario, y el día de cada plan
lo abre directamente en esa semana.

Las órdenes anteriores a esta regla, y las que sembraron las migraciones sin
pasar por la lógica del modelo, recibieron su cierre en la migración 0221. La
0222 corrigió además la hora de los ejemplos, que se habían sembrado en UTC y
aparecían a las cuatro de la madrugada.

## Cuando no aplica

El plan de mantenimiento se arma sobre el inventario. Una unidad sin equipos
registrados no incumple nada: el panel lo dice en lugar de dibujar ceros y
barras vacías, y el expediente lo consigna como «no aplica». La pestaña misma
solo aparece cuando la unidad tiene habilitado el mantenimiento o las
incidencias en su configuración operativa.

## El reporte institucional

La categoría *Plan de mantenimiento e incidencias de equipos* del Centro de
reportes (`reportes_mantenimiento.py`) es el documento **Plan anual de
mantenimiento preventivo y correctivo** del expediente de calidad. Va equipo
por equipo con su criticidad, su estado en el semáforo, su plan y frecuencia,
**quién lo ejecuta**, el **cronograma previsto** —las próximas ejecuciones que
proyecta la frecuencia declarada—, el último y el próximo mantenimiento, lo
ejecutado sobre lo programado, las incidencias abiertas, los días detenido, la
vida útil, la **garantía**, las **piezas críticas sin repuesto** y el costo
acumulado. Se puede filtrar por estado del semáforo.

Sus tarjetas resumen lo que la Dirección pregunta: equipos con seguimiento,
cobertura del plan con los críticos que no lo tienen, órdenes del período y
cumplimiento, cuántas ejecutó un tercero, incidencias, equipos en garantía,
repuestos y el costo separado entre servicio y repuestos.

## Archivos

- Modelos: `webcitt/models/operaciones.py` (el cierre de agenda que nace de la
  orden), `webcitt/models/unidades.py` (criticidad, vida útil, garantía,
  baja y reemplazo), `webcitt/models/equipos.py` (`PiezaEquipo` y la vida útil
  de referencia del tipo), `webcitt/models/mantenimiento.py`
  (`RepuestoMantenimiento` con su pieza y el ejecutor del plan y la orden),
  migraciones `webcitt` 0214 a 0222.
- Ciclo de vida: `webcitt/signals.py` registra el evento de baja.
- Dominio: `webcitt/domains/unidades/mantenimiento_panel.py`,
  `ficha_equipo.py`, `ficha_equipo_pdf.py`, `reportes_mantenimiento.py`.
- Consola: `portal/pages/unidades/gestion/includes/mantenimiento_panel.html`
  y el formulario de `includes/formularios_operativos.html`
  con los estilos `mant-*` de `panel_gestion.css`; la ficha en
  `portal/pages/unidades/gestion/ficha_equipo.html` con `ficha_equipo.css`,
  el fragmento `includes/origen_del_dato.html` y el visor compartido
  `aula/includes/visor_pdf_modal.html`.
- Admin: piezas como tabla de la ficha técnica del equipo y catálogo propio;
  repuestos como inline de la orden, con la pieza que reemplazan; criticidad,
  vida útil, garantía y baja en la ficha del activo; el ejecutor en el plan y
  en la orden.
- Pruebas: `webcitt/tests/test_mantenimiento_seguimiento.py`,
  `test_ficha_equipo.py`.

## Pendiente institucional

Validar los años y las horas de referencia sembrados por categoría, el umbral
de renovación (hoy 80 %) y si la baja exige acta firmada además del registro.
Confirmar también las garantías reales de cada contrato de compra, que aquí
están sembradas como referencia por familia, y quién queda autorizado a
declarar que un trabajo exige técnico externo.
