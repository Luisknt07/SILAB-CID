# Laboratorios, plantas piloto, centros experimentales, observatorios y Centros I+D

Revisión completa del sistema de reservas y gestión hecha el 12 de septiembre
de 2026 sobre la rama `integracion-version2-funciones`, con la base local
(quince unidades, cuatro cargadas y probadas) y la suite completa en verde.
Este documento fija tres cosas: en qué estado sale a producción la sección de
laboratorios, qué comparten y qué no los cuatro tipos de unidad, y en qué orden
se construye lo que falta hasta llegar a los Centros I+D.

Las decisiones funcionales del ciclo de una reserva siguen en
`docs/ciclo-institucional-laboratorios.md`; la clasificación institucional y
sus fuentes normativas, en la sección 13 de `CODEX_CONTEXT.md`. Aquí no se
repiten: se aplican.

## 1. La sección de laboratorios, lista para reservas reales

### 1.1 Lo que ya funciona y está probado

| Capacidad | Estado | Dónde se verifica |
| --- | --- | --- |
| Reserva de recursos: espacio, equipo, software, insumos por pieza/muestra/ensayo/prototipo | Operativa | `test_reservas.py`, `test_cascada_recursos.py`, `test_laboratorios_institucionales.py` |
| Encargo de servicio con cotización, orden de servicio y comprobante de pago | Operativa | `test_servicios_trabajo.py`, `test_comprobante_pago_servicio.py` |
| Guía de práctica (FT04) igual en asistente, HTML y PDF, con firma y validación | Operativa | `test_guia_*.py`, `test_guias_practica.py` |
| Agenda por unidad, horario de atención propio, bloqueos, fines de semana y horas extra del administrador | Operativa | `test_horarios_operacion.py`, `test_calendario_reservas.py` |
| Cierre operativo con consumo por lote, reparto por pieza y liquidación | Operativa | `test_laboratorios_institucionales.py`, `test_gestion_operativa_unidad.py` |
| Cambios, cancelaciones, vencimientos automáticos, recordatorios y notificaciones | Operativa | `test_cambios_*.py`, `test_ciclo_notificaciones_reservas.py` |
| Panel de la unidad: reservas, agenda, recursos, inventario, finanzas, mantenimiento, prácticas, reportes, configuración | Operativa | `test_panel_gestion_unidad.py`, `test_mantenimiento_equipos.py` |
| Centro de reportes con ocho categorías en HTML, PDF y hoja de cálculo | Operativa | `test_practicas_flujo_reportes.py`, `test_reportes_dimensiones.py` |
| Cuatro laboratorios cargados con todo y recorridos de punta a punta | Operativa | `cargar_laboratorios_institucionales`, `test_laboratorios_institucionales.py` |

Se puede reservar de verdad hoy. Lo que sigue son las condiciones del entorno
y de los datos, no del código.

### 1.2 Tres tipos de usuario, y solo tres

| Tipo | Quién es en el sistema | Qué alcanza | Qué no alcanza |
| --- | --- | --- | --- |
| Superusuario | `is_superuser` de Django | Toda la plataforma: administrador institucional, panel de cualquier unidad, todos los módulos, reporte institucional | Nada le queda fuera |
| Personal de una unidad | El **administrador principal** (`Unidad.administrador`) y los **responsables con cuenta** (`ResponsableUnidad` activo) | El panel de su unidad con la matriz de módulos que la unidad le asigna: reservas, agenda, recursos, mantenimiento, inventario, finanzas, prácticas, reportes, configuración. El administrador principal tiene todo y es el único que cambia al personal | El panel de otra unidad (403), el administrador de Django (no es `is_staff`), las reservas ajenas fuera de su unidad |
| Usuario | Cualquier cuenta con perfil institucional vigente | Reservar, ver y cancelar sus propias reservas, sus comprobantes y sus guías. Un docente además redacta guías | El panel de cualquier unidad, los comprobantes de otras personas, el inventario |

Reglas que se cumplen en el código y quedaron fijadas en
`webcitt/tests/test_tipos_de_usuario.py`:

- El personal se identifica de una sola manera. La mentoría de unidad y los
  integrantes con rol de texto libre, que otorgaban gestión por caminos
  paralelos, se retiraron.
- Sin datos institucionales vigentes nadie usa las funciones de reserva,
  tampoco el personal: la compuerta de perfil no distingue por quién pregunta.
- La única excepción a los tres tipos es **Decanato**: una cuenta que entra al
  administrador de Django solo para aprobar y amortizar las órdenes de servicio
  del FabLab. Es una decisión institucional pendiente: o esa aprobación pasa al
  panel como un permiso del personal, o Decanato se declara como cuarto tipo.

### 1.3 Lo que ve quien no inicia sesión

| Contenido | Sin sesión | Con sesión de usuario | Personal de la unidad |
| --- | --- | --- | --- |
| Portal, catálogo de unidades, ficha de cada unidad, reglamento, personal público con correo institucional y extensión | Sí | Sí | Sí |
| Catálogo de equipos, espacios, licencias, servicios y materiales | Sí | Sí | Sí |
| Existencias y precios por unidad de los materiales | No: solo «disponible» o «agotado» | Sí | Sí |
| Agenda de ocupación | Sí, sin nombres: «Docente UPEC», «Personal administrativo UPEC» | Con el nombre de quien reservó y el título de su solicitud | Completa |
| Asistente de reserva | Se explora; al enviar, el servidor responde 401 y el asistente pide iniciar sesión | Envía | Envía |
| Panel, comprobantes, guías, administrador | Redirige a iniciar sesión | Solo lo propio | Su unidad |

Quedan dos decisiones de política que no cambian código: si la agenda debe
mostrar el nombre de quien reservó a los demás usuarios con sesión (hoy sí, y
sirve para coordinarse), y si el registro con correo y contraseña sigue abierto
a cualquier dominio. En producción esa cuenta no se usa hasta confirmar el
correo (`ACCOUNT_EMAIL_VERIFICATION = "mandatory"`), que es lo que impide que
alguien registre una dirección institucional ajena.

### 1.4 Condiciones para salir a producción

1. Entorno según `docs/despliegue-produccion.md`: `SECRET_KEY`, dominio HTTPS,
   PostgreSQL, SMTP real. Sin SMTP no hay confirmación de correo, comprobantes
   ni recordatorios; `manage.py check --deploy` lo detiene.
2. La tarea de recordatorios instalada (`scripts/instalar_tarea_recordatorios.ps1`
   o el servicio del `docker-compose`). Es la que vence las solicitudes sin
   aprobación y avisa de cierres pendientes.
3. Un superusuario institucional y, por unidad, un administrador principal y
   sus responsables con cuenta registrados desde el panel.
4. Datos de prueba fuera: las 86 reservas y las diez cuentas `*.test` y
   `*.prueba` del FabLab y de los laboratorios cargados, y las once unidades
   con sufijo `-prueba` que no correspondan a una unidad real.
5. El registro del Observatorio de Turismo conserva el slug y la descripción
   de una unidad agroalimentaria: hay que corregirlo antes de publicarlo.
6. Fotografías reales de los equipos cargados; hoy son marcadores.

## 2. Contenidos de cada unidad: qué se administra y desde dónde

| Contenido | Dónde se administra hoy | Quién |
| --- | --- | --- |
| Identidad, descripción, imagen, facultad, carreras, contacto, ubicación, horario publicado | Administrador de Django | Solo el superusuario |
| Módulos de la ficha pública (Información general, Recursos y prácticas, etc.) y sus recursos: archivos, videos, enlaces | Administrador de Django | Solo el superusuario |
| Reglamento de la unidad | Administrador de Django | Solo el superusuario |
| Equipos y sus unidades físicas, espacios, licencias, materiales y lotes | Panel de la unidad, módulo Recursos | Personal con permiso |
| Servicios y sus materiales | Administrador de Django | Solo el superusuario |
| Horarios de atención, jornadas, bloqueos, capacidad, tarifas, módulos habilitados, personal | Panel de la unidad, módulo Configuración | Personal con permiso; el personal solo lo cambia el administrador principal |
| Palabra del trabajo, ventana de atención, ejemplos de redacción | Administrador de Django (y el cargador institucional) | Solo el superusuario |

Conclusión: la operación diaria está en el panel, pero **la ficha pública y los
servicios siguen dependiendo del superusuario**. Para que cada laboratorio sea
administrable por su propio personal, el siguiente bloque de trabajo es un
módulo «Ficha pública» en el panel (imagen, descripción, módulos, recursos,
reglamento, palabra del trabajo, ejemplos de redacción) y un módulo
«Servicios» para crear y tarifar los servicios de la unidad.

La ficha mínima de una unidad, que es lo que garantiza el cargador
institucional y lo que debe exigir ese módulo, es: identidad y ubicación;
horario de atención y palabra del trabajo; personal público y cuentas
operativas; equipos con sus unidades físicas y su ubicación; espacios con su
política de reserva; licencias con su tipo de acceso; materiales con
presentación, lote y punto de reposición; servicios con su tipo; actividades
del catálogo; y los ejemplos de redacción con los que la unidad enseña a pedir.

## 3. Cuatro tipos de unidad: qué comparten y qué no

El sistema vigente usa `Unidad` y `Reserva` como motor común. Se conservarán
como adaptadores durante la transición para no perder datos, pero no serán el
destino final. Identidad, acceso y auditoría comparten contratos; cada tipo será
propietario de su configuración, operación, persistencia, administración y
pruebas. Lo que cambia por tipo es **qué se solicita, en qué unidad de tiempo,
qué se cuenta como trabajo y qué sale de la actividad**.

La decisión arquitectónica completa está en
[arquitectura-vertical-unidades-centros-id.md](arquitectura-vertical-unidades-centros-id.md).

| | Laboratorio | Planta piloto | Centro experimental | Observatorio |
| --- | --- | --- | --- | --- |
| Qué se reserva | Espacio, equipo, licencia | Línea o área de proceso, equipos de la línea | Parcela, invernadero, establo, corral, equipo de campo | Nada físico; se solicitan datos, análisis y asesoría |
| Unidad de tiempo | Horas de un día | Corrida de varias horas o varios días | Ciclo o temporada, con visitas puntuales | Plazo de entrega |
| Lo que se cuenta | Piezas, muestras, ensayos, prototipos | Lotes de producto | Ciclos, tratamientos, animales, muestras | Conjuntos de datos, informes, consultas |
| Material | Insumos por sesión, con lote y vencimiento | Materias primas según receta, con rendimiento y merma | Insumos de alimentación, sanidad y cultivo, por activo biológico | Ninguno |
| Resultado | Práctica, ensayo, prototipo | Producto terminado para venta o para otra planta | Datos de campo, producción agropecuaria, leche y fruta para las plantas | Indicadores, tableros, boletines |
| Restricción propia | Inducción, aforo, licencias concurrentes | Inocuidad, limpieza entre corridas, control de calidad | Bioseguridad, clima, temporada, protocolo de campo | Confidencialidad y versión de los datos |
| Reporte propio | Sesiones, horas, estudiantes, prácticas | Campañas, lotes, rendimiento, merma, calidad | Ciclos, áreas, tratamientos, productividad | Fuentes, actualizaciones, consultas, descargas |

### 3.1 Simulaciones sobre el sistema actual

Cada simulación se hizo sobre el código vigente, marcando lo que hoy funciona
y lo que se detiene.

**Planta piloto de lácteos, práctica docente.** Una docente de Alimentos
reserva la línea de pasteurización para dieciséis estudiantes, con guía, dos
horas, y pide leche cruda y cultivo láctico del inventario. *Funciona hoy*:
espacio de tipo área con política técnica, equipo de la línea, insumos por lote
con vencimiento, guía FT04, cierre con consumo real. *Se detiene*: la unidad
cuenta «lotes», y esa palabra no existe (piezas, muestras, ensayos,
prototipos); y la práctica que usa la línea de 07:00 a 19:00 con la planta
cerrada al público cabe, pero solo dentro de un mismo día.

**Planta piloto de lácteos, producción para venta.** El laboratorista programa
una corrida de yogur: 200 litros de leche del centro experimental, receta con
sus materiales por litro, dos días de proceso, un lote de producto con fecha,
rendimiento y control de calidad, y luego venta o envío a otra planta.
*Se detiene* en cuatro puntos: una reserva no puede abarcar dos días; no hay
receta ni lista de materiales por unidad de producto; no existe el producto
terminado ni su lote; y no hay salida por venta ni transferencia entre
unidades. Todo el resto (línea, equipos, insumos por lote, personal, cierre)
sirve tal cual.

**Centro experimental San Francisco, práctica en invernadero.** Un docente
reserva el invernadero dos horas con su grupo. *Funciona hoy* como espacio de
tipo área. *Se detiene* en el nombre: no hay tipos de espacio para parcela,
invernadero, establo o corral, y un centro de más de cuarenta hectáreas
necesita ubicar cada área en un plano o coordenadas, que tampoco existen.

**Centro experimental, ensayo de noventa días.** Una investigadora evalúa tres
tratamientos en seis parcelas durante un ciclo, con muestreos semanales y
bitácora. *Se detiene*: la reserva es de un día y de horas; no hay ensayo,
tratamientos ni muestreos; no hay bitácora de campo. El propósito
«investigación» y el vínculo con un proyecto sí existen.

**Centro experimental, manejo del hato.** El personal registra cuántas vacas
hay, el alimento y los medicamentos que entran para ellas, la leche que sale
cada día y cuánta va a la planta de lácteos. *Se detiene*: no existe inventario
biológico (animales por lote o arete, cultivos por parcela y ciclo), los
insumos solo se atribuyen a máquinas, y no hay salida de producto hacia otra
unidad. Es el mismo vacío que el de la planta piloto, visto desde el otro lado:
**la leche que produce el centro es la materia prima que consume la planta**.

**Observatorio de Turismo, uso de sus datos.** Un investigador quiere la serie
de llegadas de turistas 2020 a 2026 y un análisis por cantón; un estudiante
quiere el tablero público; una alcaldía pide un informe. *Se detiene* casi
todo: el observatorio no presta equipos, así que el asistente de reservas no
tiene sentido allí; hoy la ficha muestra el botón «Reservar» como en un
laboratorio. Lo que necesita es un catálogo de conjuntos de datos e
indicadores con periodicidad y nivel de acceso, publicaciones, y una solicitud
de datos o análisis que sí puede vivir sobre el flujo de servicio actual con
el tipo «análisis», sin calendario ni materiales.

**Visita técnica a una planta o a un centro.** Un colegio pide recorrer la
planta de cárnicos. *Funciona hoy* como servicio de tipo «visita», con las
palabras que corresponden y cotización si la unidad la cobra.

### 3.2 Qué cambia en el motor para que quepan todos

Cambios al motor común, todos compatibles con las reservas existentes:

1. **Palabra del trabajo**: añadir «lotes» y «ciclos» al catálogo de palabras.
2. **Tipos de espacio**: parcela, invernadero, establo, corral y línea de
   proceso, con ubicación en plano o coordenadas para los centros.
3. **Equipos compartidos entre dependencias**: hoy una unidad física de equipo
   solo puede asociarse a laboratorios; una planta dentro de un centro comparte
   equipos con él.
4. **Reservas de varios días**: una campaña o corrida es una reserva con fecha
   de inicio y de fin; la agenda ya sabe dibujar bloques y sesiones.
5. **Consumo sin máquina**: hoy el material se descuenta de un lote abierto en
   un equipo; en el campo y en la mesa de taller se consume sin máquina.
6. **Modalidad de acceso por tipo**: la configuración de la unidad decide qué
   ofrece el asistente: sesión con recursos, encargo de servicio, campaña,
   ensayo, solicitud de datos. Un observatorio no muestra «Reservar»; una
   planta lo muestra con sus restricciones.
7. **Restricciones propias**: inducción obligatoria, tipos de usuario y
   propósitos por jornada (ya existe por horario), y aprobación en dos pasos
   para producción.

Lo que es propio de cada tipo se modela en su vertical. Durante la migración
puede reutilizar adaptadores heredados, pero no importa modelos internos de
otra vertical:

- **Producción** (plantas piloto y centros que producen), construido el 12
  de septiembre de 2026 en `webcitt/models/produccion.py`: `Producto` con su
  tipo (terminado, intermedio, subproducto, residuo), `Receta` con
  `InsumoReceta` y `SalidaReceta` por corrida base, `OrdenProduccion` que
  escala la receta y ocupa la línea y los equipos con un bloqueo de tipo
  «Corrida de producción», `LoteProducto` con vencimiento y control de
  calidad, y `MovimientoProducto` (venta que entra a finanzas, transferencia
  que llega al inventario de otra unidad como lote en bodega, muestra,
  consumo interno, baja). Se administra desde la pestaña «Producción» del
  panel con el permiso `produccion`, sale en la categoría de reporte
  «Producción» y la ficha pública muestra lo que se produce sin existencias.
  Solo lo ve una unidad con «Registra producción» activo; un laboratorio no.
- **Campo** (centros experimentales): Área productiva georreferenciada, Activo
  biológico (animal o cultivo) con sus movimientos e insumos, Ensayo con
  tratamientos y muestreos, Bitácora.
- **Datos** (observatorios): Conjunto de datos, Indicador, Publicación,
  Solicitud de datos o análisis.
- **Relación entre unidades**: una planta o un laboratorio dentro de un centro
  experimental, y la leche o la fruta que pasa de uno a otro, es la misma
  relación que en el reglamento se llama capacidad propia o vinculada.

### 3.3 Lo que fluye por una unidad, con el mismo nombre en todas

La regla, fijada en el bloque de taxonomía (`EquiposServicios.rol`,
`Consumible.clasificacion`, `Producto.tipo`):

| Qué es | Cómo se reconoce | FabLab | Biotecnología | Planta de lácteos |
| --- | --- | --- | --- | --- |
| Equipo principal | Se reserva; hace el trabajo | Impresora 3D, cortadora láser | Termociclador, autoclave, incubadora | Pasteurizador, tina, prensa, incubadora, envasadora |
| Equipo auxiliar | Acompaña a un principal y no se reserva aparte | Secador de filamento, estación de curado | Balanza analítica, medidor de pH | Caldera, balanza, medidor de pH, lactodensímetro |
| Insumo | Se convierte en el resultado | Filamento, láminas de MDF y acrílico | Medios de cultivo | Leche, cultivo, cuajo, sal, azúcar |
| Reactivo | Sustancia química o biológica con lote y vencimiento | Alcohol isopropílico | Agarosa, kit de ADN, etanol | Alcohol, hidróxido de sodio, fenolftaleína |
| Material | Se usa y se desgasta sin formar parte del resultado | Fresas, lijas, película FEP | Puntas, tubos | Moldes, lira, paños |
| Empaque | Envuelve el resultado | — | — | Envases, fundas, etiquetas |
| Protección | Cuida a la persona | Guantes | Guantes | Cofias, guantes |
| Limpieza | Mantiene la inocuidad | — | — | Detergente alcalino, sanitizante |
| Producto terminado | Sale para la venta o para otra unidad | (la pieza queda en el cierre de la reserva) | (la muestra queda en el cierre) | Queso fresco, yogur, leche pasteurizada |
| Producto intermedio | Vuelve a entrar en otra corrida | — | — | Crema de leche |
| Subproducto | Sale con valor propio | — | — | Suero de quesería |
| Residuo | Sale sin valor y solo se registra | — | — | Agua de lavado |

Un laboratorio termina su flujo en el cierre de la reserva (piezas, muestras
o ensayos con el consumo real por lote); una planta sigue con la orden de
producción, el lote de producto y su salida. Un centro experimental usará el
mismo tramo para la leche y la fruta que entrega a las plantas.

El paso siguiente para las plantas, trabajar por procesos (etapas de la
receta, reserva por proceso, plan de requerimientos, capacidad, plan
maestro y plan de calidad), está analizado en `docs/planta-por-procesos.md`.

## 4. Centros I+D: la ruta

Un Centro I+D no es una unidad reservable: sostiene líneas, grupos, proyectos y
resultados, y usa las capacidades de las unidades. La ruta ya prevista en
`CODEX_CONTEXT.md` § 13.5 sigue vigente y se ordena así:

1. `CentroID` con líneas de investigación, grupos e investigadores, proyectos y
   resultados, con su propio dominio, administración y pruebas.
2. `CentroUnidad`: la relación entre un centro y una capacidad propia o
   vinculada, con la modalidad de acceso, las reglas de reserva y la vigencia.
   Sustituye al texto libre `Unidad.centro_vinculado` con una migración de datos.
3. `UnidadRelacion`: una unidad dentro de otra, que es lo que ya piden las
   plantas piloto dentro de los centros experimentales.
4. La reserva o solicitud lleva, cuando aplica, el proyecto y el centro que la
   usan; con eso los reportes cruzan producción científica con uso de
   capacidades sin un segundo sistema.

Construir primero las pantallas de Centros I+D sin estas relaciones volvería a
crear dos sistemas aislados; por eso van después de la matriz de modalidades y
de la relación entre unidades.

## 5. Reportes

Estado verificado:

- El centro de reportes de cada unidad tiene ocho categorías (reservas,
  planificaciones, ejecuciones, inventario, finanzas, mantenimiento, recursos,
  auditoría) sobre un solo presentador; la vista HTML, el PDF y, desde este
  bloque, la hoja de cálculo salen de la misma consulta. Las dimensiones de
  agrupación (propósito, tipo de usuario, facultad, carrera, recurso, semana
  académica, período, jornada, responsable) son las mismas que usa el reporte
  institucional, y hay pruebas que obligan a que ambos informen las mismas
  horas efectivas.
- Solo una atención completada con ejecución registrada aporta horas y
  participantes; una solicitud confirmada y no cerrada no suma. Es la regla
  correcta y está probada.
- El reporte institucional vive en el administrador de Django, solo para el
  superusuario, y convive con dos superficies más: «Estadísticas» y «Reportes
  operativos». Las tres muestran cortes distintos de lo mismo.

Lo que falta:

1. Un solo reporte institucional, con las categorías y la hoja de cálculo del
   centro de reportes de la unidad, en lugar de tres pantallas del administrador.
2. Indicadores por tipo de unidad cuando existan sus modelos: ciclos, áreas y
   activos para centros; fuentes, consultas y descargas para observatorios.
   Las plantas ya tienen la categoría «Producción» (órdenes con lo
   planificado, lo obtenido, la merma y el rendimiento, más los lotes y las
   ventas del período) en HTML, PDF y hoja de cálculo.
3. Depurar los datos de prueba antes de leer cualquier cifra: hoy 37 de las 93
   reservas de la base están vencidas y 86 pertenecen al FabLab de pruebas.

## 6. Estructura del código

Lo que se retiró en esta revisión: los caminos de permiso por mentoría e
integrantes y sus modelos; `CarpetaSubmodulo`; el ajuste «Flujo predeterminado»
que se guardaba y nadie leía; el campo `Unidad.laboratorio`, duplicado de
`ubicacion`, con sus datos migrados; y los cuatro modelos de fabricación
anteriores al inventario actual (`FablabMachine`, `FabricationJob`,
`FabricationStep`, `FabricationConsumible`), que solo el administrador mostraba
y no tenían un solo trabajo registrado.

Lo que queda y por qué:

- `modal_reserva_equipos.js` no es código muerto: es el motor del calendario y
  del envío que usa el asistente. Fundirlo en `reservation_wizard.js` es una
  tarea de estructura, no de funcionalidad.
- Los perfiles por tipo (`PerfilPlantaPiloto`, `PerfilCentroExperimental`,
  `PerfilObservatorio`, `PerfilPlataformaTecnologica`) son hoy banderas con
  poco comportamiento. Se conservan como compatibilidad mientras cada vertical
  recibe su configuración propia; después se migran y se retiran de forma
  explícita.
- `CODEX_CONTEXT.md` es el historial de decisiones, con más de setenta bloques.
  Se conserva como historial; la definición vigente está en `docs/`.
- `Decanato` y la revisión de órdenes de servicio en el administrador quedan
  hasta la decisión del punto 1.2.

## 7. Orden de trabajo recomendado

1. Ficha pública y servicios administrables desde el panel de cada unidad.
2. Motor común para los cuatro tipos. Hecho: palabras «lotes» y «ciclos»,
   tipos de espacio de campo y de proceso, equipos compartidos entre
   dependencias, y la corrida de varios días como orden de producción. Falta:
   consumo sin máquina en el campo y la matriz de modalidades por tipo en la
   configuración de la unidad.
3. Hecho: Planta Piloto de Lácteos cargada con todo, con producto, receta,
   orden de producción, lote y movimientos, probada de punta a punta
   (`test_laboratorios_institucionales.py`, `test_produccion_planta.py`) y
   recorrida sobre la base de desarrollo. Las otras cuatro plantas se cargan
   con la misma definición: productos, recetas y cuentas propias.
4. Centro experimental San Francisco: áreas georreferenciadas, activos
   biológicos, ensayos y la transferencia de leche y fruta a las plantas.
5. Observatorio de Turismo corregido y cargado con su catálogo de datos y su
   solicitud de análisis, sin asistente de reservas.
6. Centros I+D con `CentroID`, `CentroUnidad` y `UnidadRelacion`.
7. Reporte institucional unificado con los indicadores por tipo.

Cada paso se entrega como los anteriores: cargador idempotente, pruebas,
recorrido real en la base y en el navegador, y un bloque en el historial.
