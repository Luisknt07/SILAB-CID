# Auditoría integral de las plantas piloto: contenidos, veracidad y organización

Fecha: 27 de septiembre de 2026. Base: datos de desarrollo de las cinco plantas
(Lácteos, Cárnicos, Panificación, Hortofrutícola, Almidones y Derivados), su ficha
pública, su tablero en el admin y el código que los arma.

## 1. Propósito evaluado

La plataforma debe dar a conocer cada planta piloto como un contenido de alto impacto:

1. **Del concepto a lo técnico:** qué es la planta, sus definiciones y sus sistemas
   productivos.
2. **Teoría y práctica:** contenidos teóricos que explican y contenidos dinámicos y
   editables para simular la producción.
3. **Utilidad doble:** información verídica, útil para los estudiantes y para la
   propia producción de la planta.
4. **Dos miradas:** la técnico-productiva (procesos, layout, productos, calidad,
   logística) y la operativa tipo ERP (módulos, departamentos, responsables y cómo
   se relacionan).

## 2. Estado actual en cifras

| Dato | Lácteos | Cárnicos | Panificación | Hortofrutícola | Almidones |
|---|---|---|---|---|---|
| Familias de producto | 6 | 6 | 6 | 6 | 7 |
| Productos | 22 | 25 | 26 | 24 | 26 |
| Procesos técnicos (recetas) | **8** | 3 | 3 | 3 | 3 |
| Familias sin ningún proceso | 2 | 3 | 5 | 3 | 5 |
| Equipos / espacios | 17 / 7 | 10 / 6 | 10 / 6 | 11 / 6 | 10 / 6 |
| Insumos con existencias | 29 | 16 | 16 | 16 | 16 |
| Planes de calidad | 7 | 6 | 6 | 6 | 6 |
| Órdenes / lotes / salidas | 6 / 9 / 3 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Guías de práctica publicadas | 0 | 0 | 0 | 0 | 0 |
| Responsables | 4 | 4 | 4 | 4 | 4 |

**Lácteos es la planta modelo; las otras cuatro tienen el esqueleto, pero no la
operación.** En total hay 123 productos y 20 procesos: solo el 16 % de lo que se
anuncia tiene su proceso técnico.

## 3. Lo que ya cumple el propósito

- **Mapa de 33 secciones** en seis pestañas, con contenido que se arma solo desde
  los datos de la planta; lo vacío solo lo ve quien lo completa.
- **Procesos técnicamente verosímiles:** tiempos, rendimientos y parámetros
  coherentes con la práctica industrial. Por ejemplo: jamón cocido con curado de
  24 h y 72 °C en el centro geométrico; pulpa de mora pasteurizada a 85 °C por
  2 min; mermelada a 68–70 °Brix con llenado a 85 °C o más.
- **Diagramas normativos:** flujo (Codex / ISO 5807), DOP, cursograma OIT y recorrido,
  iguales en la página y en el PDF.
- **Contenido dinámico:** tres simuladores (balance de materia y energía, balance de
  línea y requerimiento de materiales), simulaciones que se guardan, ejercicios con
  resultados, trazabilidad de lotes y control de calidad.
- **Administración por planta:** tablero con cada dato filtrado a la planta.

## 4. Hallazgos

### H1. La mayoría de las familias no tiene proceso técnico — prioridad alta
18 de 31 familias no tienen ninguna receta. Algunos ejemplos:
- **Lácteos:** Helados, Derivados del suero.
- **Cárnicos:** Cortes y despiece, Curados y madurados, Platos preparados.
- **Panificación:** todo salvo Panes.
- **Hortofrutícola:** Conservas, Congelados e IV gama, Extractos.
- **Almidones:** Harinas y premezclas, Snacks extruidos, Fermentados, Destilados,
  Vinagres.

Sin proceso, esos productos solo tienen su ficha comercial: no hay diagramas,
balance, capacidad ni simulación.

### H2. Se llama «PCC» a controles que son de calidad — prioridad alta (veracidad)
El Codex (CXC 1-1969) reserva «punto crítico de control» para los peligros de
**inocuidad**. Hoy hay etapas marcadas como PCC que controlan **calidad** o proceso:
- **Panificación:** temperatura final de la masa, cámara de fermentación.
- **Lácteos:** acidez y densidad de la leche.
- **Cárnicos:** temperatura del molino.

En un plan HACCP real serían puntos de control (PC); son PCC la pasteurización, la
cocción al centro geométrico, el nitrito, el cloro de lavado, el vacío y el sello, y
los residuos de antibióticos. Para los estudiantes enseña el concepto al revés, y
para la planta infla su plan HACCP.

### H3. La operación solo existe en Lácteos — prioridad alta
Las otras cuatro plantas no tienen órdenes, lotes ni salidas. Por eso 4.5 «Corridas y
lotes», la trazabilidad y los indicadores de producción no pueden mostrar nada real,
y los simuladores no tienen con qué compararse.

### H4. Ninguna planta tiene guías de práctica publicadas — prioridad media
2.6 está vacía en las cinco. Las prácticas son el puente entre el aula y la planta;
sin guías publicadas, el estudiante no sabe qué hacer con cada proceso.

### H5. Secciones sin fuente de datos — prioridad media
- **3.3 Servicios industriales** (vapor, agua, aire, frío): no hay equipos
  clasificados como servicio.
- **4.6 Desarrollo de producto:** no hay modelo.
- **5.2 Especificaciones:** **el dato ya existe.** Los planes de calidad de
  «liberación de producto» son especificaciones; solo falta publicarlos ahí.
- **5.5 Buenas prácticas:** documental; bastan carpetas manuales o un protocolo tipo.

### H6. El layout no se puede representar — prioridad media
Ningún equipo tiene coordenadas X/Y, así que no hay diagrama de recorrido. Tampoco
hay un plano por áreas (recepción, proceso, empaque, cámaras, despacho) que ubique
el flujo: 1.3 depende de una imagen del plano.

### H7. La logística está incompleta — prioridad media
| Parte | Estado |
|---|---|
| Almacén | Existe: existencias, mínimos, stock de seguridad, lotes de insumo y conteos |
| Abastecimiento | Falta: el proveedor es un texto, no hay órdenes de compra |
| Despacho | Parcial: salidas de producto sin clientes ni rutas |
| Cadena de frío | Solo el dato «requiere frío» del producto |

### H8. No hay estructura organizacional — prioridad media (mirada ERP)
Los responsables tienen seis roles genéricos (coordinación, responsable técnico,
laboratorista…). No hay áreas o departamentos, ni quién responde por cada proceso,
equipo o plan, ni cómo se relacionan.

### H9. Clasificación de los contenidos
| Tipo | Hoy | Falta |
|---|---|---|
| Teóricos | Ruta del saber, documentación técnica, fichas | Concepto de la planta y glosario por sistema productivo |
| Dinámicos y editables | Balance de materia y energía, balance de línea, requerimiento de materiales, ejercicios | Planificación de la producción con capacidad; costos por corrida; árbol de decisión HACCP; layout interactivo |
| Operativos (reales) | Lotes, trazabilidad, control de calidad (solo Lácteos) | Lo mismo en las otras cuatro plantas |

## 5. Propuesta de organización

Dos ejes que se complementan, sobre los mismos datos: lo que se carga una vez
alimenta los dos.

### Eje A — Aula técnica de la planta (ficha pública)

Conserva las seis pestañas y las ordena del concepto a la operación:

| Pestaña | Contenido | Tipo |
|---|---|---|
| 1. La planta | Concepto y propósito, organización y responsables, **layout por áreas con el flujo**, normativa y repositorio | Teórico |
| 2. Productos y procesos | Familias → procesos (ficha, diagramas, métodos, materiales), guías de práctica | Teórico + dinámico |
| 3. Ingeniería de planta | Equipos y fichas, **servicios industriales**, capacidad y balanceo, recorrido | Dinámico |
| 4. Producción y logística | Catálogo y fichas técnicas, empaque, **planificación y requerimiento**, corridas y lotes, **almacén y despacho** | Dinámico + real |
| 5. Calidad e inocuidad | **PCC** (inocuidad) y **PC** (calidad) separados, especificaciones, HACCP, BPM | Teórico + real |
| 6. Servicios y reservas | Servicios, agenda, requisitos, reglamento, visitas | Operativo |

### Eje B — Planta operativa por módulos (tipo ERP, en el admin)

El tablero de cada planta se organiza como una cuadrícula de módulos, al estilo de
Odoo. Cada módulo muestra su responsable, sus indicadores y a qué otros módulos
alimenta.

| Módulo | Qué gestiona | Responsable sugerido | Datos hoy | Estado |
|---|---|---|---|---|
| Dirección y organización | Áreas, cargos, responsables por proceso (RACI) | Coordinación | Responsables y roles | Parcial |
| Planificación | Plan de ventas, plan maestro y requerimientos | Responsable técnico | Plan de ventas, simulador de materiales | Parcial |
| Producción | Órdenes, corridas, lotes, rendimientos | Responsable técnico | Órdenes, lotes | Existe |
| Inventario y almacén | Existencias, lotes de insumo, conteos, alertas | Laboratorista | Insumos, entradas, conteos | Existe |
| Abastecimiento | Proveedores, órdenes de compra, recepción | Soporte operativo | Solo proveedor en texto | Falta |
| Calidad | Planes, controles, no conformidades, HACCP | Responsable técnico | Planes, controles, NC | Existe |
| Mantenimiento | Planes preventivos, órdenes, incidencias | Técnico especialista | Planes, mantenimientos | Existe |
| Logística y despacho | Salidas, clientes, cadena de frío | Soporte operativo | Salidas de producto | Parcial |
| Servicios y ventas | Catálogo, tarifas, solicitudes | Coordinación | Servicios, solicitudes | Existe |
| Seguridad y ambiente | Desechos, inducciones, EPP | Laboratorista | Desechos, inducciones | Existe |
| Formación | Asignaturas, guías, planificación y ejecución de prácticas | Coordinación | Asignaturas, guías, prácticas | Existe |
| Finanzas y costos | Ingresos, gastos, costo por corrida | Coordinación | Movimientos, precios de insumo | Parcial |
| Documentación | Expediente, repositorio, fichas | Coordinación | Expediente, adjuntos | Existe |

**Cómo se relacionan (flujo operativo de la planta):**

Planificación → Abastecimiento → Almacén (insumos) → Producción ⇄ Calidad →
Almacén (producto terminado) → Logística y despacho → Servicios y ventas.
Mantenimiento sostiene la producción; Seguridad y ambiente la acompaña; Finanzas
recibe de todos; Formación usa la producción como práctica.

## 6. Hoja de ruta propuesta

**Fase 1 — Verídico y completo (primero):**
1. Separar **PCC (inocuidad)** de **PC (calidad)** en las etapas y reclasificar los
   actuales con el árbol de decisión del Codex.
2. Publicar **5.2 Especificaciones** desde los planes de calidad de liberación.
3. **Un proceso por familia como mínimo** (18 procesos). Se redactan con la misma
   estructura que los existentes y **los valida el responsable técnico de cada
   planta antes de publicarse**.
4. Coordenadas X/Y de los equipos y áreas del layout, para habilitar el recorrido.
5. Publicar al menos una guía de práctica por proceso.

**Fase 2 — Planta operativa:**
6. Tablero por módulos (eje B) con su responsable e indicadores.
7. Áreas y responsables por proceso, equipo y plan (RACI).
8. Proveedores y órdenes de compra; clientes y despacho.
9. Corridas de ejemplo en las cuatro plantas sin operación, marcadas como
   demostrativas.

**Fase 3 — Más dinámico:**
10. Simulador de planificación con capacidad y de costo por corrida.
11. Árbol de decisión HACCP interactivo.
12. Layout interactivo por áreas.

## 7. Decisiones que se necesitan

1. ¿Se aprueba separar PCC y PC, y que el responsable técnico de cada planta valide
   la reclasificación?
2. Los 18 procesos faltantes: ¿se redactan como borrador para validación de cada
   planta, o la planta entrega sus procedimientos reales?
3. Eje B: ¿se construye dentro del tablero del admin, o también como vista pública
   «cómo funciona la planta por dentro»?
4. ¿Se crean corridas demostrativas en las plantas sin operación, o se espera a su
   producción real?

## 8. Avance de la fase 1 (27 de septiembre de 2026)

- **PCC y PC separados** (migración 0244): 28 PCC de inocuidad y 37 PC de calidad;
  cada proceso conserva al menos un PCC y el plan HACCP lleva solo los PCC.
- **Las 31 familias tienen proceso de referencia:** 23 procesos nuevos
  (`webcitt/management/plantas/ampliacion.py`) con sus equipos, insumos, PCC y
  balance cuadrado. Se corrigieron los balances sembrados: el alcalino de limpieza
  contaba como ingrediente, varias salidas declaraban más de lo que salía de su
  etapa y los embutidos y el pan de papa contaban dos veces parte de la materia prima base.
- **Cada producto tiene un proceso de partida:** 54 procesos derivados del más
  cercano de su familia, marcados «derivado, por validar» (campo `Receta.origen`:
  referencia, derivado, validado). Una nueva carga no pisa lo editado. Quedan sin
  proceso propio los nombres genéricos del catálogo que ya tienen su producto
  específico («Chorizo» es el «Chorizo parrillero») y dos productos que piden
  equipos que no hay: suero en polvo (secador por aspersión) y aceites esenciales
  (destilador por arrastre de vapor).
- Quitar un proceso archiva su ficha y libera el código, sin perder sus adjuntos.
- **Ámbitos separados:** cada corrida declara su ámbito (académico, investigación o
  producción real, según su origen) y puede marcarse **demostrativa**. Una corrida
  demostrativa recorre planificación, cierre, calidad, trazabilidad y despacho, pero no
  descuenta inventario, sus lotes llevan «DEMO» en el código, no entran a ninguna unidad,
  su venta no genera ingreso y ningún indicador ni reporte la cuenta
  (`OrdenProduccion.objects.reales()` y equivalentes en lotes, movimientos, controles y
  no conformidades).
- **Datos técnicos de referencia de los 60 equipos** (`plantas/referencia_equipos.py`):
  capacidad, tiempos, potencia, consumos, dimensiones, MTBF/MTTR y coordenadas sobre el
  plano de cada planta. Quedan marcados «valores de referencia, por verificar en planta»
  (`origen_datos_tecnicos`) y la carga nunca pisa un levantamiento validado. Con ellos se
  dibuja el recorrido (1.3), se calcula la capacidad (3.4) y se publica **3.3 Servicios
  industriales**: energía, vapor (con la cobertura de la caldera), agua, aire, frío y
  efluentes. Las 66 fichas de equipo siguen «en revisión» hasta que cada planta las publique.
- **5.2 Especificaciones publicada:** cada producto con proceso de referencia tiene su
  especificación de liberación (32 nuevas, `plantas/especificaciones.py`) con parámetros
  fisicoquímicos, microbiológicos y sensoriales; la norma (NTE INEN, Codex) se cita solo
  cuando el requisito proviene de ella. La sección tiene su página y su PDF por familia.
- **4.2 Fichas técnicas completas:** los 62 productos del catálogo que solo tenían nombre
  traen presentación, precio de referencia, vida útil, cadena de frío y descripción
  (`plantas/catalogo_fichas.py`); la carga solo completa lo vacío.
- **2.6 Guías de práctica:** una guía FT04 de referencia por proceso de referencia (43),
  armada desde el proceso: objetivos, fundamento de sus operaciones unitarias, equipos,
  materiales, procedimiento con sus PCC y PC, seguridad, resultados del balance, residuos y
  evaluación. Cada una tiene su actividad «Práctica: …»; el docente la adapta y la carga no
  pisa lo editado. Quitar una guía o un equipo también archiva su ficha y libera el código.
- **Corridas demostrativas en las cinco plantas** (`manage.py cargar_corridas_demostrativas`):
  una por proceso de referencia, rotando los ámbitos, cerrada con las cantidades de la receta,
  con su lote controlado contra su especificación (una de cada cinco sale no conforme y abre
  su no conformidad) y despachado; más una corrida planificada por planta para ejercitar el
  panel. No descuentan inventario, no generan ingresos, no bloquean la agenda ni entran en
  los indicadores; los registros se atribuyen a una cuenta de sistema inactiva, no a una
  persona. `--limpiar` las rehace.
- **«¿Qué pasa si?»:** el escenario del simulador de balance mueve, además de rendimientos,
  insumos y salidas, el trabajo y la espera de cada etapa y puede quitar etapas. El balance,
  el cronograma y el diagrama de flujo se recalculan, la página y el PDF comparan el
  escenario con la receta, y la simulación se guarda con esos cambios. La planta, desde su
  panel, edita un proceso predefinido y lo guarda como **versión nueva** (derivada, el
  original no cambia) y marca sus procesos como validados.
- **La planta por módulos** (botón «Módulos» en la ficha de cada planta, con sesión
  iniciada): el **aula** (procesos, simuladores, «¿qué pasa si?», especificaciones), que
  consulta cualquier cuenta, separada de la **operación real** en 13 módulos tipo ERP
  (dirección, planificación, abastecimiento, inventario, producción, calidad, mantenimiento,
  logística, servicios, seguridad, formación, finanzas y documentación). Cada módulo muestra
  sus indicadores reales y a qué alimenta; solo quien tiene el permiso delegado recibe el
  enlace para operarlo en el panel. El flujo paso a paso recorre la cadena, de la
  planificación a la venta. Página y PDF.
