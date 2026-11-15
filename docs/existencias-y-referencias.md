# Existencias y referencias: lo que no existe no se muestra ni se cuenta

15 de noviembre de 2026. Hasta esta fecha, casi todo el equipamiento de las unidades se había creado a partir de las
fichas de área: describían lo que un laboratorio de ese tipo suele tener y la sincronización lo convertía en
inventario. Por eso cada unidad mostraba como existente equipamiento que no tiene. Ahora el sistema separa lo que
existe de lo que es solo referencia, y lo aplica igual en laboratorios, plantas piloto, centros experimentales y
observatorios.

## La regla

**Existe** un equipo que tiene respaldo:

- se **verificó** su existencia (conteo físico desde la ficha del equipo);
- es un **bien patrimonial** importado del reporte de bodega, con su código y su valor o su fecha de ingreso;
- su cantidad la **declaró** el responsable de la unidad.

En una unidad cuyo reporte de bodega ya se importó, su inventario es ese reporte, más lo que se verificó o se
declaró. Hoy solo el FabLab lo tiene.

En las demás unidades, mientras no llega su reporte de bodega, sigue como **existencia por confirmar** el
equipamiento básico de cada área. Pasa a **referencia** lo que la ficha del área describe:

- como de alta capacidad;
- «por verificar»;
- con cantidad opcional;

y lo que nunca se habilitó (no disponible y sin verificar).

Una **referencia** no se borra. Queda inactiva y su elemento de la ficha pasa a «dotación propuesta». No aparece en:

- el visor de la unidad, ni siquiera para quien la gestiona;
- la página del área ni la ficha de equipo;
- el inventario, los reportes ni los contadores;
- los insumos («equipos que lo usan») ni el software («instalado en»);
- las reservas, los préstamos, las incidencias, los mantenimientos ni el consumo de insumos.

Vuelve a existir cuando se verifica su existencia o cuando se recibe por compra. Quien gestiona la unidad sigue
viendo las referencias en Gestión → Recursos, que es donde se activan, se solicitan para compra o se verifican.

Un área que se queda sin ningún equipo existente se desactiva. También se desactivan las áreas que no pertenecen a
la unidad.

## El comando

```bash
python manage.py conciliar_existencias                    # simula todas las unidades
python manage.py conciliar_existencias --unidad <slug>    # una (se puede repetir)
python manage.py conciliar_existencias --detalle          # lista cada equipo y su motivo
python manage.py conciliar_existencias --aplicar
python manage.py conciliar_existencias --revertir --aplicar
```

Cada aplicación deja en la auditoría de la unidad qué equipos, elementos de ficha y áreas cambió.

- `--revertir` lee ese registro y lo devuelve todo, salvo las integraciones de áreas.
- Repetir la conciliación no cambia nada nuevo.
- Las decisiones propias de una unidad (áreas que se integran en otra o que no le pertenecen) están en
  `apps/recursos/management/catalogos/existencias.py`.

La sincronización de fichas (`sincronizar_equipamiento_areas`) ya no crea existencias que nada respalda:

- lo de alta capacidad, «por verificar» u opcional queda como dotación propuesta;
- en una unidad con inventario patrimonial, o sin ningún equipo registrado, la ficha solo enlaza lo registrado;
- las áreas inactivas no reciben equipos;
- un equipo que pasó a referencia cuenta para la cantidad de la ficha, así que no se vuelve a crear.

## Lo que cambió en la base local

Aplicado el 15 de noviembre de 2026. Antes se respaldaron las dos bases en
`var/backups/pre-existencias-20261115/`.

| | Antes | Después |
| --- | --- | --- |
| Equipos activos (todas las unidades) | 2 463 | 2 049 |
| Pasan a referencia | — | 426 |
| Elementos de ficha como dotación propuesta | 0 | 263 |
| Equipos del FabLab | 192 | 38 |
| Áreas activas del FabLab | 7 | 4 |

Por unidad pasaron a referencia entre 5 y 27 equipos. El FabLab es la excepción, con 166.

### FabLab

Antes de conciliar se aplicó `preparar_fablab_2026`. Es la revisión técnica que hizo la unidad: suma 12 impresoras
declaradas (4 Bambu Lab H2C, 4 H2D y 4 Anycubic i3 Mega S) y 17 propuestas de ampliación como dotación propuesta.
Con eso, el FabLab queda con 38 equipos:

- 26 bienes de su reporte de bodega: impresoras X1-Carbon y de resina Halot Mage S, secadores, láser de fibra,
  grabadora láser de diodo, impresoras UV y DTF, escáner 3D, dos estaciones HP Z, cinco visores Meta, horno de
  reflujo y microscopio digital;
- las 12 impresoras declaradas. Siguen como «no disponibles» hasta que la unidad las verifique.

Las áreas quedan en cuatro, que son las de un FabLab:

- **Diseño, digitalización 3D y CAD/CAM.** Recibió el escáner y la metrología: un FabLab digitaliza donde modela.
- **Electrónica y prototipado de hardware.**
- **Manufactura aditiva.**
- **Manufactura sustractiva: láser y CNC.**

Se desactivaron dos áreas:

- **Robótica y Automatización** es del Laboratorio de Robótica, que ocupa una zona del aula mientras no tenga sala
  propia.
- **Servicios, materiales y formación** no tenía ningún equipo existente.

Cuatro equipos tenían códigos de bien de ejemplo (99009001–99009004), de la carga de datos demostrativos. Pasaron a
referencia como el resto: no figuran en el reporte de bodega.

### Planta Piloto de Café

Sus 56 equipos solo están descritos en las fichas y nunca se registraron. Ya no se muestran al público ni en la
cadena del café; quien gestiona la planta los sigue viendo. La sincronización ya no los convierte en inventario.

## Lo que queda para cada unidad

- **Importar su reporte de bodega.** Es la forma de que su inventario sea el real:
  `importar_reporte_bienes`, con un CSV por área en `apps/recursos/management/bienes_bodega/<unidad>/`. Hecho eso,
  `conciliar_existencias --unidad <slug> --aplicar` deja solo lo que figura en él.
- **Verificar** desde la ficha del equipo lo que existe y no está en bodega (herramientas menores, préstamos de otras
  unidades). Lo verificado no vuelve a pasar a referencia.
- **Robótica.** Su ubicación dice que ocupa una zona del aula del FabLab, pero muestra 5 áreas y 190 equipos. Es la
  siguiente unidad a revisar con datos reales.
