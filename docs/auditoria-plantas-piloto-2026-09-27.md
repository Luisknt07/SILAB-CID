# Auditoría de plantas piloto (27 de septiembre de 2026)

Alcance: las cinco plantas piloto (Lácteos, Cárnicos, Panificación, Hortofrutícola,
Almidones y Derivados), en su ficha pública y en el área «Plantas piloto» del admin.
Recorrido automático con el cliente de pruebas de Django sobre la base de desarrollo,
solo con peticiones GET.

## Funcionamiento

| Qué se recorrió | Resultado |
|---|---|
| Fichas públicas, como administrador y como visitante: 600 enlaces y botones de sus secciones | Todos responden |
| 48 pantallas del área, sin filtro, filtradas por cada planta y formulario de alta | Todas responden |
| Ficha de cada planta en el admin | Responde |
| Tablero de cada planta: 47 herramientas y 78 enlaces por planta (390 en total) | Todos responden |

## Contenido de la ficha pública por sección

Números = elementos propios que muestra la sección; «pend.» = sin contenido.

| Sección | Lácteos | Cárnicos | Panificación | Hortofrutícola | Almidones |
|---|---|---|---|---|---|
| 2.1 Sistemas de producción | 20 | 24 | 25 | 23 | 25 |
| 2.2 a 2.5 | con contenido | con contenido | con contenido | con contenido | con contenido |
| 3.2 Fichas de equipo | 17 | 10 | 10 | 11 | 10 |
| 3.3 Servicios industriales | pend. | pend. | pend. | pend. | pend. |
| 4.2 Fichas técnicas de producto | remite a 4.1 | remite a 4.1 | remite a 4.1 | remite a 4.1 | remite a 4.1 |
| 4.3 Empaque y presentación | pend. | pend. | pend. | pend. | pend. |
| 4.6 Desarrollo de producto | pend. | pend. | pend. | pend. | pend. |
| 5.1 / 5.3 / 5.4 Calidad | pestaña desactivada | 3 / 3 / 4 | 1 / 1 / 2 | 3 / 3 / 4 | 2 / 2 / 3 |
| 5.2 Especificaciones y 5.5 Buenas prácticas | pestaña desactivada | pend. | pend. | pend. | pend. |

Las secciones 1.x, 2.6 y 6.x salen de datos fijos de la unidad (video, plano,
reglamento, reservas, guías publicadas); sus enlaces están dentro del recorrido.

## Hallazgos

1. **Secciones sin fuente de datos propia:** 3.3, 4.3, 4.6, 5.2 y 5.5. Hoy solo se
   completan con carpetas de «Carpeta recursos» ancladas a esa sección. El tablero de
   cada planta las lista para no perderlas de vista.
2. **Lácteos tiene desactivada la pestaña «Calidad e inocuidad»**, aunque tiene 7
   planes de calidad. Sus secciones 5.x no se muestran hasta activarla en «Módulos de
   contenido».
3. **Lácteos no tiene guías de práctica publicadas** (2.6 vacía), aunque tiene
   reservas.

## Organización del admin

- El área «Plantas piloto» se abre con una tarjeta por planta y sus cifras clave.
  La vista general de las 49 herramientas queda plegada, y cada tarjeta dice qué
  contiene.
- El **tablero de cada planta** (`/admin/plantas_piloto/plantapiloto/<id>/tablero/`)
  reúne todo lo suyo en dos partes:
  - lo que muestra la ficha pública, pestaña por pestaña y con la sección donde
    aparece cada dato;
  - la operación: reservas, prácticas, equipos, mantenimiento, inventario, seguridad,
    expediente, producción, servicios y trazabilidad.

  En cada fila se ve qué es, cuántos registros tiene esa planta y los accesos «Ver y
  editar» y «Nuevo», ya filtrados a la planta.
