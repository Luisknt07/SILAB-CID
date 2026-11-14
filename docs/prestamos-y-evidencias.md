# Préstamo de equipos y las evidencias que faltaban

Fecha: 23 de septiembre de 2026. Rama `reestructura-modular`.

La Universidad pide ocho informes a los laboratorios y centros. Los ocho
existían como reporte, pero cuatro evidencias no llegaban al expediente y una
de ellas, el registro de préstamos, ni siquiera tenía de dónde salir.

## Cómo se prestaba un equipo antes

No se prestaba: se marcaba. El activo tenía un estado «prestado» que alguien
ponía a mano desde el administrador. Esa casilla lo sacaba de las reservas,
y hasta ahí llegaba. No decía quién lo tiene, desde cuándo, para qué, cuándo
debe volver ni en qué condición salió. Al cerrar el período la unidad tenía
que redactar el registro de préstamos en un archivo aparte y cargarlo firmado.

## Cómo se presta ahora

`PrestamoEquipo` es el acta viva de cada salida. Se registra desde *Recursos
e inventario → Equipos prestados*, sin abrir el administrador.

| | Interno | Externo |
| --- | --- | --- |
| A dónde va | Otra área de la Universidad | Fuera de la institución |
| Qué exige | Quién retira y para qué | Además: institución receptora y quién autoriza la salida |
| Por qué | El activo sigue bajo custodia universitaria | Deja de estarlo: sin receptor ni autorización no hay a quién reclamarlo |

En los dos casos se registra la condición de salida, el plazo de retorno y,
al volver, la condición de retorno con sus observaciones. El acta firmada se
adjunta; en el préstamo externo es la evidencia que revisa la auditoría.

**Qué hace el sistema solo.** Al entregar, el equipo pasa a «prestado» y
recuerda el estado que tenía; al devolverlo vuelve a ese estado. Mientras está
afuera no se ofrece ni se puede reservar, y el calendario de la unidad lo
muestra ocupado todo el plazo con el mismo cierre de agenda que usa el
mantenimiento. Un préstamo cuyo plazo venció se marca vencido sin que nadie
lo declare.

La cadena de prioridad del estado del equipo quedó así: una incidencia que
detiene la operación manda sobre todo, después el mantenimiento en proceso,
después el préstamo, y al final el estado propio del activo.

## Las cuatro evidencias que faltaban

| Evidencia | Antes | Ahora |
| --- | --- | --- |
| Registro de préstamos de equipos | Se exigía cargado a mano | Sale del reporte de préstamos |
| Reactivos e insumos del período | Solo consulta | Documento del expediente, condicional |
| Investigación aplicada y desarrollo | Solo consulta | Documento del expediente, condicional |
| Transferencia y servicios a la sociedad | Solo consulta | Documento del expediente, condicional |

Los tres nuevos son condicionales: una unidad que no recibió investigación en
el período no incumple, le consta «no aplica». Con esto son catorce las
categorías del Centro de reportes que sustentan un documento exigido.

## Cómo se llega a cada informe

**En la unidad.** El Centro de reportes tenía un menú desplegable con veinte
categorías: había que abrirlo y leerlo entero para encontrar la que se
buscaba, y no se veía cuáles cuentan como evidencia. Ahora los ocho informes
están a la vista, agrupados como los pide la Universidad; el que está abierto
despliega su grupo, y cada categoría dice si es evidencia del expediente o
solo consulta.

**En la administración institucional.** *Evidencias por tipo de unidad* suma
una fila por unidad y ahora incluye los préstamos con los vencidos sin
devolver. Cada cifra es un enlace: abre el informe del que sale, en esa
unidad, en vez de dejar al lector en la pestaña de reportes para volver a
buscarlo.

## Ejemplos sembrados

Tres reportes salían en cero porque nunca se había registrado nada, así que
no había forma de revisar si sus columnas dicen lo que la auditoría pide. Las
migraciones 0225 y 0226 dejan casos con sus dos caras:

- **Préstamos**: un escáner que salió a una feria escolar y volvió completo;
  una computadora que volvió tarde y con un cable rayado; un plotter que sigue
  afuera por un convenio de vinculación; y una estación de electrónica con el
  plazo vencido.
- **Desechos**: resina y alcohol contaminado entregados a gestor autorizado
  con su manifiesto, y tres lotes todavía almacenados.
- **Control de ingreso**: quienes entraron con su protección verificada y
  quien no entró por llegar en sandalias.

## Archivos

- Modelo: `webcitt/models/prestamos.py`; el cierre de agenda que nace del
  préstamo vive en `operaciones.py` y la cadena de estados en
  `mantenimiento.py`. Migraciones `webcitt` 0223 a 0226.
- Reporte: `reportes_evidencias.reporte_prestamos`; catálogo del expediente en
  `expediente_catalogo.py`.
- Consola: el formulario en `includes/formularios_operativos.html`, la tarjeta
  de custodia y el navegador de informes en `includes/panel_contenido.html`.
- Consolidado institucional: `reportes_consolidados.py` con la plantilla
  `admin/webcitt/reporteoperativounidad/evidencias.html`.
- Pruebas: `webcitt/tests/test_prestamos_equipos.py`.

## Pendiente institucional

Definir quién autoriza una salida externa en cada tipo de unidad y si el acta
debe ir firmada antes de la entrega o puede adjuntarse después. Hoy el sistema
exige declarar quién autoriza, pero acepta el acta más tarde.
