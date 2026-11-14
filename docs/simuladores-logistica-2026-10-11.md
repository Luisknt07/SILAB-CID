# Simulación logística: implementación y guía de uso

Fecha: 11 de octubre de 2026. Unidad: Laboratorio de Logística, Transporte y Cadena de Suministro, slug conservado laboratorio-logistica-comercio-internacional. Estado: implementación y migraciones aplicadas localmente; sin despliegue al servidor universitario.

## Qué se incorporó

El menú **Recursos de aprendizaje y simuladores** ofrece el laboratorio de operaciones 3D, el juego de la cerveza multijugador y la práctica individual anterior. Abrir la ficha de la unidad no descarga estos simuladores ni consulta sus partidas. Cada recurso se abre cuando se selecciona y respeta la publicación de la tipología, unidad, módulo docente y sección 4.4.

Las escenas usan geometría tridimensional propia en WebGL: cámara orbital, acercamiento, selección por rayos, luces, sombras geométricas, etiquetas y transición de posiciones después de una decisión validada. La presentación es esquemática; no se ha demostrado fidelidad fotográfica ni física industrial. La lista de objetos, las reglas, tablas y decisiones siguen disponibles sin WebGL. No se incorporó una biblioteca 3D de terceros ni dependencia de CDN.

La exploración es pública. Guardar, participar y puntuar requiere la cuenta del usuario. Las partidas se recuperan desde **Mis partidas** y conservan caso, semilla, versiones, decisiones, resultados y observaciones por rol. Archivar conserva la evidencia; no borra la partida.

## Relación con las seis áreas existentes

| Área registrada | Recurso implementado | Operación y evidencia |
|---|---|---|
| LOG-ALMACEN · Almacenamiento e intralogística inteligente | Almacén: del muelle al despacho | Calidad, recepción, ubicación, capacidad, FIFO, picking, empaque, despacho y balance de existencias. |
| LOG-AREA-SIM · Planificación de la cadena de suministro | Juego de la cerveza, individual y multijugador | Pedidos privados, demoras, faltantes, inventario, costos, servicio y efecto látigo. |
| LOG-AREA-TMS · Transporte, distribución y movilidad | Última milla y ventanas | Camión, depósito, cinco clientes, recargas, capacidad, distancia, espera y entregas tardías. |
| LOG-AREA-PRODUCCION · Logística de producción y operaciones | Smart factory: flujo y cuello de botella | Tres estaciones, buffers, alimentación, mejora de capacidad, parada, calidad y OEE didáctico. |
| LOG-AREA-COMERCIO · Logística internacional y operaciones de comercio exterior | Terminal de contenedores | Buque, atraque, grúa, carga seca/refrigerada, patio, documentos, liberación, puerta y permanencia. |
| LOG-AREA-ERP · Tecnologías aplicadas y simulación logística | Misión de AMR/dron y pronóstico verificable | A*, obstáculos, baterías, inspecciones; entrenamiento, validación temporal, selección de modelo y prueba reservada. |

Los códigos enlazan conceptualmente con las áreas ya registradas; no se crearon áreas, carreras ni asignaturas paralelas. Se mantienen las 23 asignaturas, las carreras y la matriz académica del paso 1. El catálogo del motor añade esos mismos códigos a cada caso para futuras relaciones explícitas con guías y evaluaciones.

## Juego de la cerveza en equipo

El diseño se contrastó con el [Beer Game de MIT](https://web.mit.edu/jsterman/www/SDG/beergame.html). El código, la interfaz y los datos de práctica son propios; no representan el producto de MIT ni una afiliación institucional.

1. El facilitador inicia sesión, crea una sala y elige caso y semilla. Los casos son cambio de demanda, pico temporal y disrupción de suministro.
2. Comparte el código de 12 caracteres con el equipo. Cada persona autenticada ocupa un solo puesto: minorista, mayorista, distribuidor o fábrica. La misma cuenta no puede ocupar dos puestos.
3. El facilitador puede ocupar un puesto o coordinar sin jugar. Antes de iniciar debe haber al menos una persona en un puesto; las vacantes se operan mediante la política automática declarada.
4. Cada participante observa su situación local, consulta la guía y confirma un pedido entero de 0 a 200. En fábrica se distingue solicitud de producción de producción efectiva limitada por capacidad.
5. La semana avanza una sola vez cuando están confirmadas las decisiones de todos los puestos humanos. Los participantes pueden decidir simultáneamente sobre la misma semana; el servidor impide reutilizar una decisión de la semana anterior.
6. Al terminar se publica el análisis conjunto: costos por eslabón, comparación con la política automática, servicio inmediato/acumulado, inventarios, atraso final y amplificación de pedidos. Antes del cierre no se muestran saldos de otros puestos ni demanda futura.

La conectividad no determina un ganador por velocidad de clic. No hay reloj que borre una decisión al desconectarse: el pedido confirmado queda guardado y el usuario puede volver con su cuenta. Una sala con un participante humano ausente espera su decisión; no se sustituye silenciosamente por un bot. Después de iniciar se conservan los puestos del equipo.

La rúbrica suma servicio 35, costo relativo 40 y estabilidad 25. Se explican fórmulas, pesos, efecto del horizonte y tratamiento de demanda con varianza nula. La política de comparación utiliza el mismo caso, semilla, horizonte y retardos; no se declara óptima. El puntaje es didáctico y no emite automáticamente una nota o certificado.

El JSON final descarga el registro del servidor y permite verificar su reproducción. El CSV recoge la bitácora propia o el análisis conjunto al terminar. Los valores que podrían interpretarse como fórmulas de hoja de cálculo se escapan.

## Casos operativos 3D

Todos los tiempos, demandas y capacidades de los casos son parámetros didácticos propios. No representan mediciones verificadas de las maquetas ni autorizaciones de operación real.

**Almacén.** Se reciben seis pallets de dos unidades. Uno tiene daño determinado por la semilla y solo se identifica al inspeccionarlo. Se registran recepción y rechazo, se distribuye el stock entre una zona cercana de capacidad limitada y reserva, y se despachan tres pallets siguiendo FIFO. El motor comprueba existencias + rechazo + salida = ingreso inicial. La selección de ubicaciones afecta recorridos y tiempo. Los intentos incompatibles con capacidad o secuencia quedan explicados en la bitácora. Las referencias son [trazabilidad GS1/EPCIS](https://www.gs1.org/standards/epcis) y [riesgos de almacén de OSHA](https://www.osha.gov/warehousing/hazards-solutions); los identificadores son sintéticos y no se declara conformidad EPCIS.

**Puerto.** Se asigna atraque y se trabaja con cuatro contenedores. La preparación de la grúa cambia el tiempo de descarga; cada contenedor necesita documentación, traslado a patio apropiado, liberación y salida. Los perecederos requieren frío. La permanencia comienza en el atraque y se mide hasta la salida; se informan productividad y límites de cadena de frío. La [información de SENAE](https://www.aduana.gob.ec/servicio-al-ciudadano/para-exportar/) sirve para contrastar la práctica documental. El caso no envía declaraciones ni autoriza un trámite.

**Fábrica.** Una línea de tres estaciones procesa 12 unidades en intervalos de cinco minutos. La alimentación admite 12 y los buffers intermedios 8. Las transferencias son simultáneas: una unidad no atraviesa toda la línea en el mismo intervalo. Mejorar una estación consume parada; calibrar calidad previene defectos del caso. Se conservan trabajo en proceso + unidades buenas + defectos = lote inicial. El OEE expone disponibilidad, rendimiento y calidad, con ciclo ideal declarado. La simulación operativa se relaciona con el enfoque de [eventos discretos de SimPy](https://simpy.readthedocs.io/en/stable/), sin instalar SimPy como dependencia.

**Transporte.** Cinco pedidos se atienden con un camión de capacidad 8 y un inventario de depósito finito. El usuario decide orden de visitas y recargas. Se calculan distancias euclidianas, viaje a 30 km/h, espera por apertura de ventana, servicio y retrasos. Se verifica el balance entre depósito, carga y unidades entregadas. La referencia es una heurística reproducible con los mismos clientes, no un óptimo global. El planteamiento de capacidades y ventanas se apoya en la documentación de [OR-Tools](https://developers.google.com/optimization/routing/vrp); el motor actual usa implementación propia y una red sintética.

**AMR y dron.** El robot móvil trabaja sobre una cuadrícula 8×6 y obstáculos explícitos. A* usa cuatro vecinos, costo unitario y heurística Manhattan; se prueba contra búsqueda en anchura. Primero se calibra el sensor, luego se planifica y ejecuta cada paso. El dron realiza comprobación previa, tres inspecciones y retorno con reserva de batería. Las posiciones del robot, objetivo, ruta, obstáculos y puntos de inspección se reflejan en la escena. Son misiones virtuales, sin conexiones a maquinaria o aeronaves reales.

**Pronóstico.** Se generan 60 semanas con tendencia, estacionalidad y ruido. Entrenamiento 1–36, validación 37–48 y prueba 49–60. Se ajustan último valor, media de las últimas cuatro observaciones y regresión con tendencia/estacionalidad; se selecciona por MAE de validación, se reajusta con 1–48 y se evalúa una sola vez sobre la prueba. La API no entrega las semanas 49–60 hasta evaluar. El procedimiento sigue la separación temporal explicada en [scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split). La evaluación de riesgo y uso previsto se relaciona con el [AI RMF de NIST](https://www.nist.gov/itl/ai-risk-management-framework). No se instaló un LLM ni se envían datos a proveedores externos.

Los casos operativos puntúan cumplimiento 60 + eficiencia 25 + precisión 15, con fórmula y criterios específicos visibles en el resultado. Las referencias de tiempo son realizables; pronóstico compara error frente a último valor. Cada partida tiene hasta 120 decisiones. La evidencia final puede descargarse y verificarse mediante el servidor.

## Actividad docente replicable

Una práctica lista para desarrollar con la matriz de asignaturas consiste en ejecutar una línea base, documentar una hipótesis, cambiar decisiones y repetir con la misma semilla. El estudiante entrega bitácora, indicadores, comparación y explicación del resultado. El docente evalúa cumplimiento de reglas, interpretación del modelo y justificación, además del puntaje.

Para almacén se compara ubicación cercana/reserva; para fábrica, mejora de capacidad y calibración; para transporte, dos secuencias de clientes; para puerto, preparación de grúa y orden de contenedores; para robótica, ruta y reservas; para pronóstico, validación y prueba. En cadena de suministro se comparan equipos y política automática con parámetros iguales. Los datos sintéticos permiten repetir sin atribuir resultados a una empresa o instalación real.

## Persistencia, modularidad y actualización

- Modelos PartidaSimulador, ParticipantePartida y EventoPartida en la base central de laboratorios/unidades. Centros I+D conserva su base y estructura independiente.
- Las simulaciones anteriores de plantas piloto mantienen SimulacionGuardada y su semántica de parámetros. Las nuevas partidas tienen estado y evidencia versionados; no se mezclaron ambos modelos.
- Índices por propietario/unidad/fecha, unidad/simulador/fase y usuario/partida. Restricciones SQL impiden duplicar usuario o rol y revisión de evento dentro de una partida.
- Bloqueo de fila y transacción para cada decisión; bloqueo por autor para respetar el máximo de 20 partidas abiertas incluso con creaciones simultáneas.
- El servidor calcula y guarda observaciones por rol. Las lecturas normales no repiten el motor; las listas extraen solo el puntaje y omiten los JSON completos. Los sondeos condicionales pueden responder 304 sin cargar el estado ni transferir la partida.
- CSRF, identidad y permisos por unidad/participación, JSON acotado, límites de solicitudes, pedidos enteros y decisiones reconocidas. No se aceptan puntajes calculados en el navegador. El administrador puede consultar evidencia, sin formularios para editar estados o resultados.
- La reproducción verifica estado, resultado y observaciones almacenadas. Una versión desconocida queda consultable mediante sus vistas guardadas, pero no se reanuda ni se verifica con reglas distintas. Al publicar un motor nuevo debe conservarse su implementación anterior si se quiere seguir ejecutando partidas de esa versión.

Archivos principales: modelos/partidas_simulador.py; domains/unidades/logistica_partidas.py; motores logistica_cerveza_servidor.py y logistica_operaciones_motor.py; templates y estáticos propios en logistica. Las cuatro rutas nuevas se importan de forma diferida. No se añadió una consulta de partidas a la portada o a la ficha general.

## Rendimiento y comprobaciones

243 pruebas Django aprobadas en la base temporal de QA y 153 pruebas JavaScript aprobadas. Incluyen cuatro conexiones PostgreSQL decidiendo una semana a la vez, dos creaciones simultáneas con cupo, duplicados, aislamiento entre usuarios/unidades, CSRF, privacidad, recuperación, reproducción e integridad de resultados. Los motores suman 54 pruebas puras. Ruff, Django check y comprobación de migraciones pendientes de generar correctos.

Se comprobaron ocho páginas contra la base local: sala, práctica individual y seis casos; todas respondieron HTTP 200 con siete consultas y sin escrituras ni consulta de partidas durante la exploración. No se crearon participantes o partidas ficticias en la base operativa. Esto no es una prueba de carga del servidor universitario.

El JavaScript de operaciones ocupa aproximadamente 66 KB y el multijugador 40 KB, antes de compresión. Se cargan por separado al abrir cada recurso. El visor limita resolución/DPR, renderiza bajo demanda y pausa fuera de vista; las transiciones respetan reducción de movimiento. El multijugador sondea cada tres segundos, pausa al ocultar la pestaña y aplica espera creciente ante errores.

Las migraciones 0328 y 0329 se aplicaron localmente tras respaldo PostgreSQL verificado. Se conservaron 56 conteos/huellas de catálogos y datos de Centros I+D. El respaldo y los registros privados están en var/logistica-simuladores-20261011; no deben publicarse ni incluirse en Git.

## Límites y siguiente integración técnica

La revisión de GPU real, legibilidad, oclusiones y dispositivos móviles queda pendiente: este entorno no ofrece un navegador gráfico habilitado. Las pruebas de geometría, cámara, selección, ciclo del visor y alternativa sin GPU no sustituyen esa inspección. Tampoco se ha ejecutado una carga masiva contra infraestructura universitaria.

WebXR se investigó y su disponibilidad se explica en la interfaz; no se iniciaron sesiones inmersivas. La [documentación de MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API/Permissions_and_security) exige contexto seguro, interacción del usuario y permisos apropiados. Para AR/VR se necesitan pruebas con el navegador, visor y entorno de publicación elegidos, además de interacción inmersiva y ubicación de la escena.

Para física robótica, sensores y control de autonomía, la integración siguiente debe conectarse a [Gazebo](https://gazebosim.org/libs/sim/) y, para drones, a [PX4 SITL/HITL](https://docs.px4.io/main/en/simulation/). Esos motores tienen capacidades que este modelo operativo no reproduce. No están instalados ni conectados aquí.

La conexión con las maquetas requiere inventario verificado, mapeo entre equipo/objeto virtual, mediciones de capacidad y tiempos, calibración, eventos fechados y prueba conjunta con responsables del laboratorio. Primero debe incorporarse telemetría validada y compararse la simulación con mediciones; cualquier control físico requiere su propia autorización y mecanismos de seguridad. No se atribuyen prestaciones a los 131 registros de equipamiento existentes sin verificarlos.

La implementación deja una base funcional evaluable para estas integraciones. No se ha demostrado superioridad frente a todos los simuladores comerciales ni una certificación de laboratorio industrial.
