# ERP integrado de las plantas piloto (fase 2)

## Diagnóstico

La plataforma ya tiene un ERP: **Gestionar laboratorio** (`/gestion/unidades/<slug>/`,
`webcitt/domains/unidades/gestion.py`) planifica ventas y producción, genera
órdenes y pedidos, recibe entregas, produce lotes, los controla y libera, lleva
inventario, mantenimiento, finanzas, prácticas, seguridad y reportes. La
arquitectura lo fija como el espacio interno único: la ficha pública muestra lo
aprobado y una misma entidad alimenta ambas superficies (`arquitectura-plantas-piloto.md`).

Lo que lo hace sentir fragmentado:

1. **Una tercera superficie.** La página «La planta por módulos» repetía los
   indicadores y pestañas de la consola, mostraba cifras internas (ingresos del
   mes) a cualquier cuenta con sesión y enlazaba un módulo a una vista equivocada.
2. **Menú de planta incompleto.** La consola de planta dejaba fuera prácticas,
   ejercicios, seguridad, visitas y reportes; los accesos rápidos del tablero
   llevaban a vistas sin botón y el visor quedaba vacío.
3. **Tablero sin la planta.** El tablero muestra uso de reservas y equipos, pero
   no la cadena productiva: planificación, producción, calidad ni inventario.
4. **Sin modo consulta.** Quien no tiene el permiso de un módulo no lo ve; en un
   ERP el personal consulta todo lo de su planta y opera solo lo delegado.
5. **Módulos sin relaciones.** La orden no lleva a sus lotes, a su control ni a
   su línea del plan; el lote no lleva a su control con mediciones; la entrega
   recibida no lleva al lote de insumo; la compra sugerida no crea el pedido; la
   reserva no muestra su orden; el equipo no lleva a su ficha.
6. **Aula y ERP sin puente.** El proceso, el producto, el equipo y la
   especificación de la ficha pública no llevan a donde se operan, y desde la
   consola no se llega al aula ni al simulador del mismo proceso.
7. **5.4 pública con detalle interno.** Publica los últimos 20 lotes reales y no
   filtra por familia, contra la regla de que los detalles de lotes permanecen
   en la superficie interna.
8. **La práctica no ve su corrida.** La orden de una práctica nace al aprobar la
   reserva, pero ninguna pantalla del usuario la muestra.

## Diseño

- **Una sola superficie operativa:** la consola es el ERP. Su tablero de planta
  es el mapa de módulos con el flujo paso a paso; cada módulo abre su sección.
- **Tres niveles de acceso:** el público ve el aula; el personal de la planta
  consulta todos los módulos de producción; cada responsable opera solo los
  módulos que la coordinación le delegó (`permisos_operativos_unidad`).
- **Relaciones navegables:** cada registro enlaza a lo que lo originó y a lo que
  produjo, en el módulo que corresponde.
- **Puente aula ↔ ERP:** desde el aula, quien opera salta a su módulo; desde la
  consola, el proceso abre su ficha, su documentación y su simulador.
- **El admin queda para los datos maestros** (familias, fichas editoriales,
  carpetas y catálogos) y se enlaza desde «Datos maestros».

## Bloques

**2.1 Un solo ERP.** Menú de planta completo y agrupado; tablero con el mapa de
módulos y el flujo; retiro de la página aparte; modo consulta de planificación,
producción y calidad; relaciones entre módulos; puente aula ↔ ERP; 5.4 sin
detalle de lotes; la orden de la práctica visible para quien reservó.

*Hecho (27 de septiembre de 2026):* menú agrupado con los 15 módulos; mapa del
ERP y flujo en el tablero (`planta_operativa.mapa_de_la_planta`), con acceso
«Operas», «Solo consulta» o «Sin acceso» por módulo; página aparte retirada;
modo consulta; enlaces orden → reserva, ficha, plan, lotes y control; lote →
control; no conformidad y control → trazabilidad; entrega → lote; compra
sugerida → pedido; insumos por pedido en «por controlar»; «En el aula» y
«¿Qué pasa si?» desde cada proceso; «Operar en la consola» en el aula; 5.4 sin
detalle de lotes; corrida de la práctica en el comprobante.

**2.2 Lo que le falta al ERP.** Proveedores y órdenes de compra desde la compra
sugerida; control de calidad de los insumos recibidos; clientes y despacho con
cadena de frío; costo por corrida (insumos, energía y mano de obra);
responsables por proceso, equipo y plan.

*Costo por corrida, hecho (27 de septiembre de 2026):* `costos.py` calcula el
costo estándar de cada receta (insumos a su precio, potencia de cada equipo
por el tiempo de su etapa con la espera, horas-persona por etapa; el tiempo
crece con las corridas base, como en el plan maestro) y el real de cada orden
cerrada (lo consumido al costo de su lote, repartido sobre lo obtenido). Lo que
no tiene precio, potencia o tarifa queda «sin dato» y el total se declara
parcial. La tarifa de energía y la hora-persona se fijan en los permisos
operativos; las plantas cargadas traen referencias de validación
(`management/plantas/costos_referencia.py`) que no pisan las propias. Se ve en
la consola (recetas y órdenes), en el reporte de producción y en la ficha
interna del proceso con su PDF; la ficha del aula no publica costos.

*Proveedores y órdenes de compra, hecho (27 de septiembre de 2026):* el
proveedor pasa de texto libre a un maestro único para la institución
(`Proveedor`, sin duplicados aunque se escriba distinto; la migración traslada
los nombres ya escritos). Los pedidos en borrador de un proveedor salen en una
orden de compra con número (`OrdenCompra`), con hoja y PDF para enviarse; se
confirma cuando el proveedor la acepta, se anula devolviendo sus pedidos al
borrador mientras nada se haya recibido y queda recibida sola al llegar todo.
La evaluación de proveedores sale de lo registrado: entregas a tiempo y
controles de recepción, con la calificación confiable, en observación o
crítico (BPM e ISO 9001, 8.4). Todo en la pestaña de planificación; el mapa del
ERP cuenta las órdenes abiertas.

## Redistribución: el ERP en su propia pestaña

Integrar el ERP dentro de «Gestionar laboratorio» mezcló dos trabajos distintos.
La consola la usa la coordinación para administrar la unidad: reservas, agenda,
equipos, mantenimiento, seguridad, personal y reportes. Las operaciones del ERP
las hacen los docentes y los estudiantes en sus prácticas, y el personal de
producción cuando la planta produce de verdad. Además, varias personas operando
a la vez sobre los mismos datos los confunden. Por eso el ERP queda como una
superficie propia, con sesiones separadas.

| Superficie | Quién la usa | Para qué | Contenido |
| --- | --- | --- | --- |
| Ficha pública (seis pestañas) | Cualquiera | Conocer y aprender lo que la planta sabe hacer | Procesos y protocolos (fichas técnicas, diagramas, métodos, simuladores, guías), equipos e infraestructura, producción y lotes (catálogo, fichas de producto, actividad agregada), calidad e inocuidad (protocolos, especificaciones, HACCP, BPM, resumen por producto), reservas y servicios |
| ERP de la planta | Docentes y estudiantes (sesiones de práctica), personal de producción (producción real) | Operar la cadena productiva paso a paso | Tablero con el mapa y el flujo, planificación (ventas, plan maestro, materiales), compras (proveedores, órdenes de compra), almacén de insumos (recepción y existencias), producción (órdenes y cierre), calidad operativa (controles, liberación, no conformidades), despacho (clientes, cadena de frío), costos |
| Gestionar laboratorio | Coordinación y personal de la unidad | Administrar la unidad y su uso | Tablero de uso, reservas, programación, visitas, prácticas (FT02/FT03), ejercicios, activos, inventario y conteo de bodega, finanzas, mantenimiento, supervisión, seguridad y acceso, personal y permisos, reportes, configuración y seguimiento de las sesiones del ERP |

No se repite nada: la ficha pública explica con lo aprobado y con cifras
agregadas; el ERP registra transacciones; la consola administra recursos y
personas. Una misma entidad, como un proceso, se explica en el aula, se usa en el
ERP para planificar y producir, y se administra como dato maestro.

**Sesiones del ERP.** Cada operación ocurre dentro de una sesión:

- *Producción real:* una por planta; la operan el personal con permiso de
  producción y los docentes que la coordinación delegue. Es la única que mueve
  el inventario, las finanzas, los indicadores y los reportes.
- *Sesión de práctica:* la abre un docente para un grupo, desde una práctica
  aprobada o a mano, y los estudiantes entran con ella.
- *Sesión individual:* la abre un estudiante para practicar por su cuenta.
- *Sesión demostrativa:* las corridas de ejemplo de cada planta, para mostrar el
  flujo completo.

Lo de una sesión no toca el inventario real ni cuenta en indicadores, reportes o
finanzas, y no se ve desde otra sesión. Sus existencias parten de una foto del
inventario al abrirla y cambian con lo que se recibe y se consume dentro de ella.
Los datos maestros (productos, procesos, insumos, proveedores, clientes y
equipos) son compartidos; en una sesión se puede guardar una versión propia de un
proceso que solo vive en ella. Al cerrarse, la sesión queda para que el docente
revise lo que hizo el grupo.

**Bloques.** 2.3: el ERP en su propia pestaña y la consola sin la cadena
productiva. 2.4: las sesiones y el acceso de docentes y estudiantes. 2.5: el
despacho con cadena de frío y los responsables por proceso, equipo y plan, ya
dentro del ERP.

*2.3, hecho (27 de septiembre de 2026):* el ERP vive en `/erp/<planta>/`
(`erp_planta`) y comparte con la consola su plantilla, su JS y sus formularios;
cada superficie pinta solo sus secciones (`planta_operativa.SECCIONES_ERP`). El
ERP abre con el mapa: los módulos de la cadena se abren en la misma pestaña y los
de la administración, en Gestionar laboratorio. La consola de una planta queda
con uso de la unidad, formación, recursos y administración; la completitud de
contenidos pasa a su tarjeta de contenidos. Cada pestaña lleva a la otra; la
ficha de la planta ofrece el ERP junto a Gestionar laboratorio; el aula, las
hojas internas (proceso, trazabilidad, plan maestro, control, orden de compra,
encargo) y la compra sugerida del inventario llevan al ERP. Un laboratorio que
no produce no tiene ERP.

*2.4, hecho (27 de septiembre de 2026):* `SesionERP` y `ExistenciaSesion`
(`models/erp.py`). Planes de ventas y maestros, pedidos, órdenes de compra y
órdenes de producción llevan su sesión; lotes, salidas, controles y no
conformidades la heredan de su orden (`en_sesion()` en sus consultas). El ERP
arma su propio contexto (`domains/unidades/erp.py`), así un estudiante entra sin
permisos sobre la unidad: sin sesión solo ve «Sesiones de práctica»; el docente
abre una sesión de práctica (con clave de seis letras) o cualquiera abre la suya
individual, y el grupo entra con la clave. Las reglas de acceso están en
`sesiones_erp.py`: en una sesión opera quien participa mientras está abierta y
solo la cadena productiva (`OPERACIONES_EN_SESION`), nunca los datos maestros;
el personal de la planta la ve y la acompaña; cerrada, se consulta. En una
sesión se eligen proveedores ya registrados: la práctica no amplía el maestro
de la institución. Las
existencias de la sesión parten de una foto del inventario, suben con lo
recibido y bajan con lo consumido; la explosión de materiales las usa. Las
corridas demostrativas pasaron a la sesión demostrativa de cada planta (sin la
casilla de antes), y la producción real, sus indicadores y el reporte de la
unidad ya no las listan. La consola sigue las sesiones desde «Prácticas». El JS
manda la sesión con cada operación, y las hojas sueltas (control, plan maestro,
trazabilidad, orden de compra) respetan la sesión de su registro.

*2.5, hecho (27 de septiembre de 2026):* clientes y despacho con cadena de frío
(`despacho.py`): el cliente es un maestro único como el proveedor (base común
`ContraparteComercial`); cada producto con frío declara su límite de
conservación (4 °C refrigerado, −18 °C congelado; la migración y el cargador lo
fijan donde falta) y una venta, transferencia o muestra no sale sin su
temperatura ni por encima del límite. Cada despacho tiene su guía con PDF; la
trazabilidad y la consola dicen a quién fue y a qué temperatura salió; el aula
y su PDF muestran la conservación del producto. En una sesión el cliente se
elige entre los registrados o se vende al consumidor final. El proceso y el plan
maestro tienen su responsable del personal de la planta; los equipos ya lo
tienen en sus planes y órdenes de mantenimiento. En una sesión no aparecen los
botones de los datos maestros.
