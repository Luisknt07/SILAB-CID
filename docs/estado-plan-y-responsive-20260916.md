# Estado de la planificacion y revision responsive

## Estado vigente: cierre del 19 de septiembre de 2026

La estabilización arquitectónica terminó en el bloque 184 y Laboratorios superó
su aceptación funcional definitiva. Código funcional validado: `7edae539` en
`reestructura-modular`.

- Suite integral: 1.392 pruebas correctas, una omitida, 501,783 s.
- Aceptación enfocada de Laboratorios: 277 pruebas correctas, 86,159 s.
- Señales: 19 contratos, 19 decoradores y 19 conexiones propias, sin hallazgos.
- Responsive: 182 combinaciones públicas, 574 autenticadas y 14 del visor PDF;
  770 en total, ES/EN y anchos de 360 a 1920 px, sin incidencias.
- Django check, migraciones en seco y Ruff: correctos.
- Producción falla cerrada si falta una clave fuerte u otra configuración
  obligatoria; el perfil local no constituye un despliegue productivo.

El trabajo inmediato vuelve a funciones: planificación completa de Plantas
piloto, después completitud administrable, repositorio trazable y su aceptación.
Luego siguen Centros experimentales, Observatorios y Centros I+D. M01
institucional, M02.3 y M10-M13 permanecen como deuda explícita y no autorizan a
afirmar recuperación o aislamiento físico que todavía no existe.

## Estado histórico: revisión del 18 de septiembre de 2026

Código funcional validado: continuación 170; consultar `git log -1` en
`reestructura-modular`. La continuación 166 consolidó la revisión documental; el corte original del
16 de septiembre se conserva debajo como evidencia histórica. Los pendientes
de aquel corte no deben interpretarse como el estado actual.

**Dictamen actual:** los contratos de cierre, propuestas, decisiones, solicitudes propias y gestión administrativa simple están validados y podemos
continuar desarrollando desde esta base. La reestructuración completa y la
puesta en producción todavía no están cerradas. El trabajo actual corresponde
a **M02.4 y M02.2**, con M02.1/M09 parciales.

| Hito | Estado actual | Qué está implementado / qué permanece |
| --- | --- | --- |
| M00 | Implementado | Inventario y compatibilidad de entradas; mantener comparaciones |
| M01 | Evidencia local; institucional pendiente | Ensayos de restauración/reversas realizados; falta captura institucional de base/adjuntos, copia externa cifrada/inmutable, custodia y RPO/RTO |
| M02.1 | Parcial | Identidad neutra SLCID/UPEC, marca y logos, paleta/tipografía, ES/EN, catálogos, niveles, calendario, roles y pertenencia; faltan consumidores/contenidos institucionales y validación operativa completa |
| M02.2 | Parcial | Manifiestos de despliegue y habilitación institucional de `portal.portada_inicio`; falta cubrir todos los caminos de las capacidades operativas |
| M02.3 | Cerrado el 20 de septiembre de 2026 | Tipologías de unidad y clasificaciones administrables desde el admin, con efecto en el servidor ([tipologías](tipologias-administrables.md), [categorías](categorias-administrables.md)) |
| M02.4 | Parcial; trabajo actual | 19 contratos de señales, inventario de superficies, recuperación de códigos y doce operaciones de reservas bajo la guarda común; faltan escritores, validadores y propietarios restantes |
| M03-M07 | Pendientes de extracción | Entradas por tipo y motores organizados; negocio, datos y administración operativos siguen en legado |
| M08 | Pendiente de negocio propio | Centros I+D dispone de entrada pública; falta su app de investigación con funciones y datos propios |
| M09 | Parcial | Portada de Inicio administrable con modelos propios; otras secciones editoriales pendientes |
| M10 | Pendiente para negocio operativo | No se trasladaron sus tablas, app labels, permisos o ContentTypes; ensayar cada traslado/reversa en copia |
| M11 | Pendiente de aislamiento real | Proceso, base, URLconf y credenciales compartidos; no se demuestra contención de una caída por app |
| M12-M13 | Pendientes | Empaquetado instalable, retiro de compatibilidad y auditoría operativa/comercial |

### Validación vigente de 170

**1308 pruebas, OK, una omitida; 1294.069 s**. Focal final: 13 OK, 7.073 s;
11 pruebas nuevas de autoridad, estado y responsable vigentes, rollback y
concurrencia. Asignar responsable, anotar y solicitar información salen de la
vista monolítica hacia un servicio transaccional con bloqueo de la reserva,
alcance por unidad y cuenta persistida. La auditoría visible y la bitácora
administrativa comparten una sola implementación; nota, aviso y trazabilidad
se confirman o revierten juntas. Una carrera PostgreSQL comprueba que dos notas
simultáneas se serializan sin perder contenido.
Ruff/check/migraciones en seco, señales 19/19/19 y ES/EN (8799 mensajes)
correctos. Sin esquema, rutas, interfaz ni datos reales modificados; no nueva
certificación de navegador.

### Evidencia anterior de 169

**1297 pruebas, OK, una omitida; 901.265 s**. Focal final: 132 OK, 68.825 s;
32 pruebas nuevas de autoridad/persistencia, rollback real y concurrencia.
Solicitar cambio/cancelar reserva propia delegan en servicios con transacción
propia, cuenta/titular/unidad/estado vigentes y fila fresca bloqueada. Alta guarda
revisión/base/solicitud/auditoría/aviso juntas; cancelación cierra cambios activos
conservando expediente/historial. Cuatro carreras PostgreSQL y restricción real;
otros errores de integridad no se disfrazan de duplicados.
Ruff/check/migraciones en seco y ES/EN (8793 mensajes) correctos. Sin esquema,
interfaz ni datos reales modificados; no nueva certificación de navegador.

### Evidencia anterior de 168

**1265 pruebas, OK, una omitida; 1085.389 s**. Focal final: 112 OK, 32.668 s;
31 pruebas nuevas de persistencia, autoridad, rollback real y concurrencia.
Autorizar/rechazar/retirar tienen servicios propios con reserva -> solicitud,
cuenta/unidad/autoridad/estado vigentes y auditoría/aviso internos atómicos.
Unidad cargada después de bloqueos; selección explícita inválida no amplía campos.
Tres carreras PostgreSQL: doble autorización, rechazo frente a retirada y
administrador revocado durante espera. Se conserva limpieza de solicitudes activas
con reserva cerrada/ventana vencida, propuesta/historial y adaptación AJAX/redirect.
Ruff/check/migraciones en seco y ES/EN (8785 mensajes) correctos. Sin esquema,
interfaz ni datos reales modificados; no nueva certificación de navegador.

### Evidencia anterior de 167

**1234 pruebas, OK, una omitida; 1406.403 s**. Focal final: 81 OK, 25.693 s;
28 pruebas nuevas de autoridad, persistencia, rollback y concurrencia real.
Envío separado y transaccional, orden reserva -> solicitud también en aplicación
y panel de cambios; GET vencido no actualiza la solicitud. Conserva aprobación,
parser de insumos, historial y recuperación mediante nueva ventana.
Ruff/check/migraciones en seco y ES/EN (8769 mensajes) correctos. Sin esquema,
interfaz o datos reales modificados; no nueva certificación de navegador.

### Comprobaciones y límites históricos del corte 166

Suite integral del código al cierre de 165: **1206 pruebas, OK, una omitida; 724.325 s**.
La revisión documental de 166 no modificó código ejecutable ni atribuyó otra
suite integral a cambios documentales. Ruff, Django check, migraciones en seco,
catálogos ES/EN y auditoría estricta de señales se vuelven a comprobar en 166.
Las migraciones existentes están aplicadas; no se genera ninguna nueva.

Validación focal de 166: **83 pruebas, OK; 36.303 s**. Incluye límites de
arquitectura, manifiestos, rutas, idiomas, superficies, contrato de cierre y
controles de seguridad de producción. No amplía la certificación a todos los
escritores pendientes ni a un despliegue institucional real.

Inventario sin consultas a datos: 11 módulos declarados, 104 rutas operativas
heredadas, 96 modelos heredados/12 propios, 67 administradores, 23 comandos,
11 scripts y 19 receivers. Tener paquetes y manifiestos no equivale a tener
11 apps Django de negocio independientes: las instaladas propias son `webcitt`,
`configuracion_institucional` y `portal`.

La agenda y los 16 campos auditados de catálogos académicos son compatibles,
sin reparaciones ni cambios de datos. No se ejecutan cargas o cierres reales.
La revisión de responsive conserva la evidencia y los límites documentados
en [Responsive del portal y operación](responsive-portal-y-operacion.md).
No hay una nueva inspección de navegador o dispositivos físicos en este corte.

**Producción no habilitada:** el entorno local `config.settings` tiene seis
avisos de `check --deploy`: DEBUG, clave débil, HSTS, redirección HTTPS y cookies
seguras de sesión/CSRF. No se publican valores de secretos ni se rotan credenciales
durante esta auditoría. `config.settings_production` rechaza este entorno por
la clave de despliegue; completar su configuración, proxy y controles antes
de exponer una instancia pública. Ver [Despliegue de producción](despliegue-produccion.md).

### Siguiente secuencia acordada

1. Propuestas/decisiones reforzadas en 167-168, solicitudes propias en 169 y
   asignación/notas/solicitud de información en 170. Continuar aprobación,
   rechazo, cancelación administrativa, inicio, cierres alternos y corrección;
   doce operaciones bajo la guarda todavía no cubren toda la capacidad.
2. Completar la matriz de gestión, primitivas, tareas, admin y cargas; distinguir
   operaciones nuevas del mantenimiento, cancelación e historial.
3. Cubrir una capacidad operativa en todos sus caminos antes de habilitar su
   suspensión institucional. La guarda de Inicio no cubre las reservas.
4. Implementar categorías/extensiones M02.3 y cerrar contratos por propietario.
5. Extraer verticales una a una con compatibilidad y pruebas; los traslados de
   datos requieren las puertas M01/M10. El aislamiento real se prueba en M11.

La base anterior permanece en `integracion-version2-funciones`. Cambiar de
rama recupera código; no restaura por sí mismo PostgreSQL ni los adjuntos.
La [ruta modular](ruta-ejecucion-arquitectura-modular.md) conserva el detalle
de cada entrega y sus criterios de cierre.

## Corte histórico del 16 de septiembre de 2026

Fecha: 16 de septiembre de 2026. Codigo revisado: `d0d2c057`, rama
`reestructura-modular`. Esta entrega es una auditoria; no cambia codigo,
configuracion, modelos ni datos.

## Dictamen

No esta terminada toda la planificacion. Los pasos funcionales 1-7 de plantas
piloto tienen implementacion e integracion registradas en la seccion 115 de
CODEX_CONTEXT y recorridos automatizados. Esto no significa que todos los
productos tengan procesos tecnicos publicados ni que todas las carpetas
contengan documentacion institucional aprobada.

La reestructuracion sigue en **M02.1**, con M01 institucional abierto. Hay
entradas publicas separadas en seis paquetes, pero `INSTALLED_APPS` sigue
registrando `webcitt` como la aplicacion propia de negocio. Sus modelos,
migraciones, permisos, administracion y rutas operativas no se han trasladado
a aplicaciones independientes. No se ha demostrado contencion real de una
caida de proceso, base o credencial por vertical.

## Plan funcional de plantas piloto

| Bloque | Estado comprobado | Trabajo que permanece |
| --- | --- | --- |
| Pasos 1-3 | Taxonomia, estructura y rutas integradas | Mantener una fuente por producto/proceso y completar levantamientos |
| Paso 4 | Catalogo y produccion/lotes diferenciados | Completar especificaciones, empaques, capacidades y evidencias reales |
| Paso 5 | Reservas y servicios integrados con procesos | Publicar recursos y procesos tecnicos validados para los productos pendientes |
| Paso 6 | Completitud, documentacion, diagramas y motores implementados | Revision docente/especialista, mediciones, referencias, guias y contenido faltante |
| Paso 7 | Repositorio, gobierno de adjuntos y contratos de artefactos | Conectar y validar cada artefacto externo; no asumir conexiones reales por disponer del contrato |

El catalogo completo no equivale a un proceso configurado para cada producto.
El cierre historico registra ocho procesos publicados en Lacteos y tres en
cada una de las otras plantas. Las fichas pendientes deben seguir indicando
su estado; no inventar recetas, resultados o documentos para elevar contadores.
Una plataforma con contratos de integracion tampoco demuestra que ya existan
telemetria operativa o capacidad probada para uso masivo.

## Ruta modular

| Hito | Estado | Falta para cerrarlo |
| --- | --- | --- |
| M00 | Implementado | Mantener inventario y compatibilidad de rutas |
| M01 | Ensayo local realizado; institucional pendiente | Captura coordinada base/adjuntos, restauracion aislada, copia externa cifrada/inmutable, custodia de claves y RPO/RTO |
| M02.1 | En curso | Pertenencia y roles verificados, tarifas/procedencia historicas, catalogos persistentes administrables, tema y contenido institucional |
| M02.2-M02.4 | Pendientes | Manifiestos y habilitacion en servidor, limites, categorias extensibles, propietarios, contratos, validadores y senales |
| M03-M07 | Pendientes | Extraer Observatorios, Plantas piloto, Centros experimentales, Laboratorios y Aprendizaje de forma gradual |
| M08-M09 | Pendientes | Aplicacion propia de Centros I+D y administracion editorial por seccion del portal |
| M10-M11 | Pendientes | Propiedad de persistencia/permisos y aislamiento real de ejecucion, credenciales y recuperacion |
| M12-M13 | Pendientes | Empaquetado comercial, retiro de compatibilidad y auditoria de perfiles institucionales, seguridad, carga y recuperacion |

M02.1 ya incluye identidad SLCID/institucion, catalogo academico configurable,
niveles, calendario institucional, zona horaria y selector ES/EN. Esto conserva
UPEC y las identidades tecnicas heredadas; no equivale a renombrar el repositorio
o a distribuir un framework instalable ya terminado.

## Responsive comprobado

Chrome headless aislado, sin perfil ni credenciales personales. Trece rutas
publicas, idiomas ES y EN, y siete anchos: **360, 390, 768, 1024, 1200, 1366 y
1920 px**. Son **182 combinaciones**, todas HTTP 200 y sin errores JavaScript.
Las mediciones y capturas se conservan en `tmp/`, fuera de Git.

Rutas: Inicio, Quienes somos, Centros I+D, Servicios, Normativa, Noticias,
catalogos de unidades y de los cuatro tipos, acceso, ficha de Lacteos e indice
de materiales/insumos. Esta prueba no cubre todas las pantallas ni sustituye
el uso en dispositivos fisicos.

El selector permanece dentro de la barra verde y no se detecta solapamiento
entre enlaces del menu principal y acciones en estos recorridos anonimos.
El ajuste anterior tambien comprobo apertura del menu movil y conservacion de
modulo/recurso al cambiar ES/EN. No se ha ensayado aqui la cabecera con todos
los controles de una cuenta autenticada.

**Responsive no cerrado:** 36 combinaciones presentan desplazamiento horizontal,
debidas a dos problemas compartidos y reproducibles:

| Superficie | Anchos afectados | Exceso | Causa localizada |
| --- | --- | --- | --- |
| Acceso `/login/` | 360 y 390, en ambos idiomas | 10 px | Margenes negativos de `.row.h-100` exceden el contenedor |
| Cuatro catalogos | 768, 1024, 1200 y 1366, en ambos idiomas | 3, 135, 91 y 50 px respectivamente | Pseudoelementos decorativos de la experiencia extendidos fuera del ancho disponible |

En el catalogo a 1200 px se reprodujo `scrollX=91`. Desactivar los
pseudoelementos solo en la sesion de diagnostico recupero el ancho de 1200 y
`scrollX=0`. Esa comprobacion localiza el origen; no es una correccion aplicada
al proyecto. No ocultar indiscriminadamente el desbordamiento del documento
para aparentar conformidad, porque podria recortar contenido util.

Pendiente probar responsive autenticado: perfil, asistente de reservas y sus
pasos, calendario/detalle desplazable, panel de gestion, administrador,
tablas, formularios largos y modales PDF; tambien contenido extremo, zoom,
orientacion horizontal, teclado tactil y navegacion por teclado. Los permisos
y flujos tienen pruebas funcionales, pero estas no certifican su presentacion
en cada tamano de pantalla.

## Verificacion y siguiente bloque

`manage.py check` sin incidencias; `makemigrations --check --dry-run` sin
cambios. La suite integral vigente es **874 pruebas, OK, una omitida,
445.969 segundos**, ejecutada en el bloque anterior. No se atribuye una nueva
suite completa a esta auditoria documental.

Validacion focalizada de esta auditoria: 30 pruebas, OK, 29.287 segundos
(integracion de pasos 1-7, rutas modulares, limites de dependencias e idiomas).

Prioridad inmediata: corregir las dos causas responsive y completar recorridos
autenticados. Despues continuar M02.1 con pertenencia/roles y tarifas historicas,
manteniendo M01 como puerta de los futuros traslados de datos. Completar el
contenido institucional puede avanzar en paralelo desde la administracion.

Referencias: [Ruta modular](ruta-ejecucion-arquitectura-modular.md),
[Arquitectura funcional de plantas](arquitectura-plantas-piloto.md),
[Internacionalizacion](internacionalizacion-es-en.md),
[Identidad y recuperacion](identidad-producto-institucion.md),
[Historial](historial/CODEX_CONTEXT.md).

## Continuacion: correcciones y revision autenticada

El diagnostico anterior se conserva como fotografia del corte auditado.
La continuacion corrige los 36 casos, la rejilla anidada del Perfil y el
solapamiento del encabezado autenticado a 1200 px. Ahora el menu se pliega
por debajo de 1280 px. No se cambian rutas, permisos, modelos o datos.

Nueva revision: 182 combinaciones publicas y 574 autenticadas con cuatro
perfiles, ES/EN y siete anchos, sin desbordamiento ni errores JS. Los 14 casos
del modal PDF mantienen la misma pestaña y generan un documento valido.
El detalle largo del calendario se desplaza internamente en escritorio y se
expande dentro del asistente en movil. La revision de paneles del asistente
es de presentacion; no sustituye completar una reserva real.

Metodo, limites y mantenimiento: [Responsive del portal y operacion](responsive-portal-y-operacion.md).
M02.1 sigue abierto; continuar pertenencia/roles y tarifas historicas. M01
institucional sigue pendiente y precede los futuros traslados de datos.

Validacion del bloque corregido: suite completa de 874 pruebas, OK, una
omitida, 1115.434 segundos. Ruff, Django check y plantillas/JS correctos;
makemigrations sin cambios. Historial: CODEX_CONTEXT.md, seccion 141.

## Continuacion 171: decisiones administrativas de cierre

El panel conserva su interfaz y rutas. Rechazo y cancelacion administrativa se
separaron del escritor monolitico a un servicio que bloquea la reserva y vuelve
a comprobar cuenta, permiso, unidad y estado persistidos. La decision y sus
efectos en ordenes de practica, solicitudes de cambio, avisos y trazabilidad son
atomicos. Una carrera PostgreSQL confirma que dos cierres rivales no se aplican
dos veces. No se modificaron CSS, HTML o JavaScript; la certificacion responsive
anterior no cambia.

Suite integral vigente: 1317 pruebas OK, una omitida, 601.415 segundos. Ruff,
Django check, migraciones en seco, catalogos ES/EN y senales correctos. M02.4 y
M02.2 siguen parciales; aprobacion y los cierres operativos restantes todavia
comparten la orquestacion heredada. Historial: CODEX_CONTEXT.md, seccion 171.

## Continuacion 172: aprobacion transaccional y conflictos compartidos

La aprobacion ya no comparte el escritor monolitico del panel. Un servicio
transaccional revalida autoridad y estado, asigna responsable vigente, comprueba
documentacion, aforo y agenda, y confirma junto con practica, planificacion,
avisos y trazabilidad. La regla persistente de conflictos tambien salio de la
vista y sirve a reservas, cambios, cronograma, visitas y gestion.

Suite integral vigente: 1327 pruebas OK, una omitida, 641.935 segundos. Ruff,
Django check, migraciones en seco, catalogos ES/EN y senales correctos. No se
modifico CSS, HTML o JavaScript, por lo que no se atribuye una nueva certificacion
responsive. M02.4/M02.2 siguen parciales: faltan inicio, cierres alternos,
orquestacion exterior de completar y actualizacion/correccion. Historial:
CODEX_CONTEXT.md, seccion 172.

## Continuacion 173: inicio y cierres alternos transaccionales

Inicio, inasistencia y cierre no atendido ya no comparten el escritor monolitico
del panel. El nuevo servicio revalida autoridad y estado, conserva documentacion,
ingreso, horario, participantes, ordenes, solicitudes, avisos y trazabilidad. La
asignacion explicita de personal tambien queda en una regla compartida por tres
servicios.

Suite integral vigente: 1337 pruebas OK, una omitida, 1767.513 segundos. Ruff,
Django check, migraciones en seco, catalogos ES/EN y senales correctos. No se
modifico CSS, HTML o JavaScript, por lo que no se atribuye una nueva certificacion
responsive. M02.4/M02.2 siguen parciales: faltan la orquestacion exterior de
completar y actualizar/correccion. Historial: CODEX_CONTEXT.md, seccion 173.

## Continuacion 174: finalizacion integral transaccional

La accion completar ya no comparte la transaccion heredada del panel. El nuevo
servicio conserva autoridad, documentacion, horario, responsable, participantes,
ejecucion, liquidacion, habilitaciones, solicitudes, avisos y trazabilidad como
una sola unidad reversible. La gestion de participantes tambien sale de las
vistas y se comparte con cambios y visitas.

Suite integral vigente: 1339 pruebas OK, una omitida, 933.797 segundos. Ruff,
Django check, migraciones en seco, catalogos ES/EN y senales correctos. No se
modifico CSS, HTML o JavaScript, por lo que no se atribuye una nueva certificacion
responsive. M02.4/M02.2 siguen parciales: falta actualizar/correccion y despues
la auditoria de primitivas, tareas, admin y cargadores. Historial:
CODEX_CONTEXT.md, seccion 174.
