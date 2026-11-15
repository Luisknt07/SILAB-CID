# Auditoría integral del 14 de noviembre de 2026

Revisión completa del sistema antes de pasar a producción: arquitectura y
modularidad, seguridad, estructura de archivos y nombres, código sin uso,
funcionamiento de reservas, gestión de unidades y administrador, preparación
de la fase de laboratorios de alta complejidad y velocidad de carga.

Este documento registra lo que se midió, lo que se corrigió en esta revisión y
lo que queda por decidir. Cada pendiente indica dónde está en el código.

## Resumen

| Área | Estado | Lo más importante |
| --- | --- | --- |
| Velocidad de carga | Corregido | La portada pasa de 60,4 MB a 5,4 MB; los estáticos se guardan un año en el navegador |
| Código sin uso y duplicados | Corregido | 11 funciones y 80 archivos estáticos retirados (46 MB); no hay código duplicado |
| Seguridad | Tres fallos altos corregidos y administrador con segundo factor; nueve pendientes | Ver «Seguridad» |
| Reservas | Listo con condiciones | Correo SMTP y dominio HTTPS, aplazados hasta tenerlos |
| Gestión de unidades | Listo con condiciones | Verificación física de equipos e inventario por las unidades |
| Administrador | Listo | Depurar datos demostrativos antes del corte |
| Independencia Centros I+D / Laboratorios | Parcial | Centros es independiente en datos y código; ningún perfil arranca hoy sin el otro |
| Laboratorios de alta complejidad | Base lista y activa en desarrollo | Módulo opcional `apps/conexiones` para dispositivos y series de medición |

## Cómo se revisó

- Estado base en el entorno Docker local: `check` sin incidencias, ninguna
  migración pendiente y modelos sincronizados con sus migraciones.
- Análisis estático de las 280 000 líneas de Python (2 033 archivos, 17
  aplicaciones): Ruff para errores e importaciones sin uso, búsqueda de
  archivos idénticos por huella, y de funciones, plantillas y estáticos que
  nadie referencia. Los estáticos candidatos se buscaron además en las 3 403
  columnas de texto de la base, en solo lectura, antes de retirarlos.
- Cuatro lecturas independientes del código: seguridad, cadena completa de
  reservas, gestión y administrador, dependencias entre aplicaciones, y
  puntos de extensión para laboratorios conectados. Los hallazgos altos se
  volvieron a comprobar en el código antes de corregirlos.
- Peso real de las páginas públicas, pidiendo cada recurso al servidor.
- Suite completa con PostgreSQL desechable, separado de las bases operativas.

## Velocidad de carga

**Medido antes.** La portada descargaba 60,4 MB: 54 imágenes PNG de unos 2 MB
cada una, solo una con carga diferida. Los estáticos se revalidaban cada 60
segundos porque sus nombres no cambiaban con su contenido. Los adjuntos
públicos (fotos de unidades y centros) salían con `no-store`, de modo que cada
visita los descargaba otra vez. El contenedor recopilaba y comprimía 300 MB de
estáticos en cada arranque.

**Corregido.**

- **Imágenes.** `collectstatic` genera un derivado WebP de cada PNG o JPEG que
  pesa (`apps/core/estaticos.py`) y el servidor lo entrega a los navegadores
  que lo aceptan (`apps/core/middleware/estaticos.py`). Los originales no se
  tocan ni cambian de nombre: las rutas escritas en plantillas, en datos
  (`imagen_estatica`) y en JavaScript siguen valiendo, y las imágenes
  verificadas por SHA-256 conservan sus bytes. Un PNG de 2 MB queda en unos
  150 KB.
- **Caché.** Los estáticos llevan huella de contenido en el nombre y se sirven
  como inmutables durante un año. Una referencia sin huella o a un archivo
  ausente no falla: se entrega la dirección original.
- **Carga diferida** en 71 imágenes bajo el pliegue de la portada, Servicios,
  Noticias, Quiénes somos y las cuatro páginas de tipología.
- **Adjuntos publicados.** Las imágenes que cualquier visitante puede ver
  (`apps/recursos/entrega/media.py`) se guardan en el navegador y se revalidan
  en cada uso: el permiso se vuelve a evaluar y, si sigue vigente, la respuesta
  es un 304 sin cuerpo. Lo que se entrega por un permiso (titular, gestor,
  operador) conserva `no-store`.
- **Arranque.** La imagen Docker trae los estáticos ya recopilados; el
  contenedor no los recopila al iniciar. Las copias con huella comparten
  bloques de disco con sus originales (427 MB en lugar de 770 MB).
- **Catálogo de traducciones.** El que usa JavaScript pesa 920 KB (179 KB
  comprimido), se carga en todas las páginas y se calculaba en cada petición,
  con una hora de caché. Ahora se publica al recopilar como un estático por
  idioma, con huella y ya comprimido; desarrollo y pruebas conservan la vista.
- **Nginx.** El ejemplo de configuración comprime páginas y respuestas JSON.

**Medido después**, en modo producción: portada 5,4 MB con los 85 estáticos
con huella e inmutables; en visitas siguientes no se descargan de nuevo.

## Código sin uso, duplicados y nombres

- **Duplicados.** No hay archivos de código idénticos. Los únicos archivos
  repetidos son seis imágenes de catálogo que comparten foto a propósito y dos
  recursos de un curso precargado.
- **Importaciones y nombres sin definir.** Ruff no encuentra ninguno.
- **Funciones sin ninguna referencia** (retiradas, 103 líneas): `area_principal`
  y `es_estandar` en `apps/core/presentation/codigos_sistema.py`; `_fecha_texto`
  en `certificados_diseno.py`; `_leccion_firmada` en `clases_en_vivo.py`;
  `seccion_ejercicios`, `seccion_seguridad`, `seccion_visitas` y
  `secciones_observatorio`, restos del índice anterior del panel (las
  secciones vigentes se definen en `gestion.py`); `_reservation_unit_ids` y
  `_reservation_space_ids` en `api.py`; `exigir_reservas_habilitadas` en
  `apps/reservas/presentation/capacidad.py`.
- **Estáticos sin uso** (retirados, 46 MB): 78 imágenes de la plantilla de
  tema original y de contenidos anteriores, el ZIP del recorrido 360 que ya
  está extraído, y el plano demostrativo del asistente de reservas.
- **Funciones que solo usan las pruebas** (se conservan, conviene revisarlas):
  `solicitar_traspaso` en `apps/recursos/presentation/traspasos.py` no tiene
  pantalla que la invoque; `historial_equipo`, `clasificar_usuario`,
  `etapa_institucional`, `evidencias_por_unidad`, `contenido_consolidado`,
  `alertas_vigentes` y `diagrama_sinoptico_svg` están en la misma situación.

**Nombres y estructura.** Lo que más dificulta ubicar cosas:

- Las reglas viven en `presentation/` (unas 20 000 líneas por aplicación),
  aunque `apps/README.md` anuncia `services/` y `workflows/`; solo `reservas`
  los tiene.
- 281 de las 492 plantillas están en `apps/gestion_unidades/templates/portal/`,
  incluidas la plantilla base, la cabecera y las páginas del portal; `apps/portal`
  solo tiene cuatro y en cambio aloja los estáticos de todo el sistema.
- `apps/gestion_unidades/presentation/gestion.py` tiene 5 037 líneas y reúne
  reservas, inventario y finanzas. `certificados_diseno.py` tiene 5 306.
- 42 800 de las 65 700 líneas de `gestion_unidades` son contenido institucional
  escrito como diccionarios Python (`management/fichas_area/`).
- «Unidad» nombra a la vez la unidad organizativa (`Unidad`) y el equipo físico
  (`UnidadEquipo`); `EquiposServicios` es el modelo técnico de equipo;
  `Reserva.laboratorio` sirve a todas las tipologías.
- En reservas, `capacidad.py` es el interruptor institucional (no el aforo),
  `mantenimiento.py` es la conciliación de reservas y `seguridad.py` el control
  de ingreso.
- Quedan etiquetas heredadas: `webcitt` (etiqueta de base de datos, no debe
  cambiarse), `citt_csrftoken`, `CITT_EXIGIR_EQUIPOS_VERIFICADOS`, proyecto
  Compose `citt`.
- Español e inglés mezclados en nombres de módulos (`availability.py`,
  `views.py`, `selectors`, `signals_uso.py`).

Ninguno de estos puntos impide publicar. Renombrar o mover a gran escala antes
del corte añadiría riesgo sin beneficio para el usuario; conviene hacerlo por
partes, con la prueba de límites nueva como red.

## Seguridad

### Corregido en esta revisión

1. **Cédula y teléfono de cualquier usuario.** `GET /reservas/participantes/buscar/`
   devolvía a toda cuenta registrada la cédula y el teléfono de las personas
   encontradas. Ahora solo los ve quien gestiona una unidad; los demás ven los
   tres últimos caracteres al añadir participantes, y nada en la lista de
   visitas internas. El servidor ya tomaba esos datos del perfil al guardar
   (`apps/reservas/presentation/views.py`).
2. **Adjuntos que podían ejecutar código en el portal.** La entrega de
   archivos aislaba una lista de extensiones peligrosas; otras variantes de XML
   (`.xsl`, `.rdf`, `.xht`) se abrían dentro del sitio. Ahora la lista es la de
   formatos que sí se muestran (imagen, PDF, audio, vídeo, texto) y todo lo
   demás se descarga o se aísla (`apps/recursos/entrega/media.py`,
   `apps/formacion/presentation/recursos_publicos.py`).
3. **Vinculación de cuentas por correo sin confirmar.** Quien registrara antes
   el correo institucional de otra persona conservaba la contraseña de esa
   cuenta cuando el titular entraba con Google o Microsoft. Al vincular, una
   contraseña de un correo nunca confirmado se anula, y Google debe declarar el
   correo como verificado (`apps/core/acceso/social.py`).
4. **Inicio de sesión social roto en consolas Windows.** El adaptador escribía
   con `print()` símbolos que una consola sin UTF-8 no puede mostrar; el error
   interrumpía el acceso. Ahora usa el registro del sistema.
5. **ZIP sin tope al descomprimir**: 512 MB o 20 000 archivos, como los
   microproyectos (`apps/recursos/models/recursos.py`).
6. **Rol de un modelo de equipo compartido**: solo lo cambia quien gestiona los
   recursos de todas las unidades que lo tienen (`gestion.py`).
7. **Comandos que crean cuentas y datos de prueba** exigen ahora la
   habilitación del entorno, que producción mantiene cerrada.
8. **Administrador sin segundo factor.** La documentación lo daba por hecho
   en el proveedor de identidad, pero un superusuario entraba solo con su
   contraseña. Ahora toda entrada al administrador exige el código de una
   aplicación autenticadora: obligatorio en producción, optativo en
   desarrollo. El alta se hace en el primer ingreso; un código no se acepta
   dos veces, cinco fallos bloquean 15 minutos, hay ocho códigos de respaldo
   de un solo uso y el secreto se guarda cifrado. `SLCID_ADMIN_REDES_PERMITIDAS`
   limita además las redes desde las que el administrador responde
   ([detalle](autenticacion.md#segundo-factor-para-administrar)). No añade
   dependencias: el algoritmo se comprueba con los vectores del RFC 6238.

### Pendiente, por prioridad

| # | Hallazgo | Dónde | Corrección propuesta |
| --- | --- | --- | --- |
| 1 | Una sesión ERP de práctica puede asociar órdenes a reservas reales | `apps/plantas_piloto/operacion/presentation/erp.py:191`, `gestion_produccion.py:485` | Forzar `reserva=None` dentro de una sesión de práctica |
| 2 | Reservar concede acceso permanente a la actividad compartida: planificaciones, evidencias y borradores de otros grupos | `apps/reservas/presentation/creacion_transaccion.py:234`, `apps/formacion/presentation/practicas.py:76` | Autorizar por reserva, no por actividad |
| 3 | Un docente verificado puede despublicar la actividad de otro | `apps/reservas/presentation/guias.py:553`, `forms.py:190` | Exigir autoría u operador |
| 4 | Recetas no publicadas legibles, alguna sin sesión | `apps/formacion/presentation/simulaciones.py:72`, `apps/documentos/presentation/documentacion.py:926` | Filtrar con `procesos_publicos(unidad, usuario)` |
| 5 | La agenda muestra el nombre del solicitante y la actividad a cualquier cuenta | `apps/gestion_unidades/presentation/api.py:546` | Decidir la política: hoy es deliberado y está probado |
| 6 | Las visitas externas se crean sin sesión y ocupan agenda sin confirmar el correo | `apps/reservas/presentation/views.py:919` | Confirmación por correo o límite por dirección |
| 7 | Las subidas desde el panel no validan el tipo del archivo | `apps/gestion_unidades/presentation/gestion.py:1855, 2005` | Validar con formulario; la entrega ya lo neutraliza |
| 8 | Tres orígenes de peticiones del servidor sin exigir destino público | `apps/recursos/presentation/sitios_externos.py:64`, `conectores_observatorio.py:31`, `navegador_remoto.py:107` | Validar el destino final tras redirecciones |
| 9 | `manage.py` y `config/wsgi.py` caen a la configuración base si falta la variable | `manage.py:9`, `config/wsgi.py:14` | El servidor de producción ya lo impide; documentarlo en despliegues nativos |

Los puntos 1 a 4 proceden de la lectura del código y deben reproducirse con una
prueba antes de corregirlos.

### Comprobado y correcto

Los adjuntos se deniegan salvo registro explícito por modelo y Nginx no publica
`/media/`. Solo hay dos rutas exentas de CSRF y ambas son avisos firmados. Todo
el SQL está parametrizado. No hay `eval`, `exec`, `pickle` ni órdenes del
sistema compuestas con texto. Las redirecciones se validan. Las plantillas no
tienen manejadores en línea y el cargador añade el identificador de la política
de contenido a cada `<script>`. No hay secretos ni datos personales
versionados. Las rutas de archivos están contenidas. La configuración de
producción exige HTTPS, cabeceras de seguridad, roles de base separados y
política por filas en las tablas personales.

## Reservas, gestión de unidades y administrador

La cadena completa está conectada: 273 rutas y 339 nombres sin vistas
inexistentes, enlaces rotos ni plantillas faltantes; todos los estados de la
reserva tienen salida y cada transición pasa por un servicio con autoridad;
los cinco comandos del programador existen; todos los modelos tienen
administración.

### Corregido

- **El asistente de reservas mostraba medios de otra unidad.** Sin plano,
  video o recorrido propios, enseñaba el plano de FabLab, un video fijo y el
  360 de Lácteos. Ahora cada botón aparece solo si la unidad publicó ese medio.
- **Un área recién creada era reservable de inmediato**, con un texto guía
  como descripción. Ahora nace no reservable y la unidad la habilita desde el
  panel (`apps/gestion_unidades/presentation/altas_en_ficha.py`).
- **Banderas sin documentar.** `.env-example` explica
  `SLCID_MEDICION_METAS_HABILITADA`, `CITT_EXIGIR_EQUIPOS_VERIFICADOS` y
  `SLCID_CAPABILITY_CONTROLS`.
- **Ediciones sin rastro.** Editar desde la página de la unidad (alta de área y
  de equipo, edición de un área, secciones propias y el editor de registros)
  no dejaba registro de auditoría, a diferencia del panel. Ahora cada alta,
  edición y eliminación queda anotada con su autor. El formulario de
  referencia comercial ya anotaba el suyo y no se duplica.
- El control de salud del entorno local daba por fallido un arranque normal
  (tarda cerca de un minuto y solo esperaba 30 segundos).

### Condiciones para publicar

1. **Correo y dominio.** Aplazados hasta disponer de ellos; mientras tanto se
   trabaja en local. Con la configuración de producción el sistema no arranca
   sin SMTP (`webcitt.E001` a `E003`). Sin correo nadie confirma su cuenta y
   los avisos de reservas quedan pendientes. Faltan también el dominio HTTPS
   y las credenciales institucionales de Google y Microsoft.
2. **Dos decisiones de publicación**, resueltas así: en desarrollo pueden
   faltar y valen falso; producción no arranca hasta que ambas estén escritas
   como `true` o `false` (`slcid.E014`), de modo que no se publique por olvido
   con el valor por omisión.
   - `SLCID_EXIGIR_EQUIPOS_VERIFICADOS` (se sigue leyendo el nombre anterior,
     `CITT_EXIGIR_EQUIPOS_VERIFICADOS`). Debe seguir en falso por ahora: de
     2 234 equipos públicos solo 1 tiene la existencia verificada, y activarla
     ocultaría el resto. Se activa cuando las unidades terminen su verificación.
   - `SLCID_MEDICION_METAS_HABILITADA`: apagada, los indicadores de cierre
     salen como desactivados. En este equipo está activa.
3. **Recordatorios documentales.** El programador de Docker no ejecuta
   `procesar_recordatorios_documentales`, y así debe seguir por ahora: al
   vencer un plazo ese comando registra la evaluación automáticamente, de modo
   que se programa cuando Dirección haya revisado los plazos
   (`docs/plazos-documentales.md`).
4. **Datos demostrativos.** La base de validación conserva evidencias de
   demostración de FabLab; deben depurarse antes del corte, no antes: siguen
   sirviendo para validar mientras se trabaja en local.
5. Por confirmar en uso real: el enlace «Abrir en Gestionar laboratorio» del
   administrador no abre el expediente de una reserva ya cerrada; el titular no
   puede cancelar una reserva confirmada; no existe encuesta tras el cierre.

## Independencia de Centros I+D y de Laboratorios y unidades

**Lo que es real.** `apps/centros_id` solo importa el núcleo, sus relaciones
apuntan a modelos propios, tiene migraciones propias y puede vivir en otra
base de datos mediante el enrutador. El resto del sistema lo nombra en seis
puntos, todos dentro de una función.

**Lo que no.** Ningún perfil «solo Laboratorios» o «solo Centros» arranca hoy:

- `INSTALLED_APPS` y las rutas eran fijos, y la comprobación `slcid.E011`
  exige instaladas las 21 aplicaciones del registro.
- La migración histórica `0330_propiedad_modular` depende de `centros_id` y de
  las cuatro verticales; el primer paso de cada aplicación depende de ella.
- La cabecera y la portada enlazan a Centros con `{% url 'centros_id' %}` sin
  protección (12 lugares en `apps/gestion_unidades/templates/portal/`).
- Centros usa la plantilla base, los componentes, los estilos y la entrega de
  adjuntos que viven en `gestion_unidades` y `recursos`.
- `apps/core` importa gestión, reservas y directorio: no es un núcleo neutral.
- Reservas, formación, gestión y finanzas tienen relaciones de base de datos
  hacia Plantas y Laboratorios; las verticales se importan entre sí.
- Solo los manifiestos de `centros_id` y `configuracion_institucional`
  declaran sus dependencias reales.

**Hecho en esta revisión.**

- `tests/architecture/test_limites_centros_unidades.py` fija el límite actual:
  Centros solo depende del núcleo, y los puntos que lo consultan forman una
  lista cerrada. Una dependencia nueva hace fallar la prueba.
- Primer módulo realmente opcional: `apps/conexiones` se instala con una
  variable de entorno y, apagado, no deja tablas, rutas ni administración. El
  registro, las rutas y `INSTALLED_APPS` ya admiten ese patrón
  (`config/settings.py`, `config/modulos.py`, `config/rutas_aplicaciones.py`).

**Decisión.** La primera publicación es una sola institución con los dos
dominios, así que esta ruta no condiciona el corte y no se ejecuta ahora:
mueve plantillas y migraciones históricas, y no hay todavía una instalación
que necesite uno solo para comprobar el resultado. Hasta entonces la prueba de
límites impide que la dependencia crezca.

**Ruta, de menor a mayor riesgo**, para cuando exista esa segunda instalación.

1. Proteger los seis puntos y los enlaces de navegación con el patrón que ya
   usa `apps/gestion_unidades/presentation/detalle.py:47`.
2. Cargar las señales desde `integraciones` y no desde `apps/core/apps.py:21`.
3. Perfil de instalación que derive aplicaciones, registro, rutas y
   proveedores; `validar_apps` valida solo la selección. Corregir manifiestos.
4. Llevar la plantilla base, los componentes y la entrega de adjuntos a
   `portal` o al núcleo, sin renombrar.
5. Quitar la dependencia de `centros_id` en `0330` tras comprobarlo con
   `migrate --plan` en una copia. Con esto arranca «sin Centros».
6. Invertir las importaciones del núcleo (`admin/cuentas.py`,
   `usuarios/views.py`). Con esto arranca «solo Centros».
7. Las relaciones de las aplicaciones comunes hacia Plantas y Laboratorios:
   lo mínimo es declarar productos, recetas y servicios de fabricación como
   capacidad común y ocultar Plantas por tipología, sin mover tablas.

## Laboratorios de alta complejidad

**Cómo llega hoy una función nueva a un laboratorio.** La simulación logística
se añadió a mano en cuatro aplicaciones, con condiciones por identificador de
unidad en 11 archivos (`logistica_juego.py`, `aula.py`, `detalle.py`,
`equipo_referencia.py`, `cafe.py`, entre otros). No es un patrón repetible:
cada función nueva de este tipo obliga a tocar aplicaciones comunes.

**Qué existía.** Registro de artefactos externos con tipo de realidad
extendida, ligado a unidad, área y equipo (`ArtefactoExterno`); visores de PDF,
de recorridos 360 y de contenido interactivo aislado; `<model-viewer>` cargado
en la plantilla base; microproyectos en contenedores; series diarias solo para
observatorios. No existía nada para dispositivos, telemetría ni inteligencia
artificial, ni una entrada autenticada para máquinas.

**Qué queda listo.** El módulo opcional `apps/conexiones`
([guía](../apps/conexiones/README.md)):

- Dispositivos por unidad, opcionalmente ligados a un equipo inventariado.
- Credencial por dispositivo: se muestra una vez y solo se guarda su huella.
- Entrada de lecturas por lotes, tolerante a reenvíos y a cortes de red.
- Series resumidas por minuto, hora o día para el personal de la unidad, y un
  único punto de lectura en el código para tableros, indicadores y análisis.
- Página de estado por unidad para su personal: cada dispositivo en línea,
  sin señal o inactivo, con la última lectura de cada canal y el aviso de
  fuera de rango.
- Cupo de envíos por dispositivo, no por dirección: varios equipos detrás de
  una misma salida a Internet no se bloquean entre sí.
- Conservación por canal; el programador depura las lecturas vencidas.
- 16 pruebas propias y un paso en la validación continua.

**Activación.** El perfil de desarrollo lo trae activado y su migración (tres
tablas nuevas) está aplicada en la base local, con respaldo previo en
`var/backups/pre-migracion-20261114-auditoria/`. Se comprobó de punta a punta
contra el servidor local con un dispositivo temporal, ya eliminado. En
producción se activa con `SLCID_MODULO_CONEXIONES=true`.

**Qué no se construyó, y por qué.**

- *Tiempo real.* El servidor es WSGI con ocho hilos; el juego multijugador
  funciona por consultas periódicas. Un intermediario MQTT o WebSocket se
  añade cuando una práctica lo exija, entregando al mismo contrato.
- *Realidad virtual y aumentada.* El registro ya existe. Falta abrir, solo en
  las vistas de experiencia, los permisos del navegador para sesiones
  inmersivas y la ejecución de WebAssembly que usan los modelos comprimidos
  (`config/settings_production.py:131`, `apps/core/middleware/security.py:19`).
  El tope real de subida es 64 MB aunque el modelo admita 200.
- *Inteligencia artificial.* No hay proveedor decidido. Elegirlo implica
  costos y una política sobre qué datos pueden salir de la institución.
- *Reemplazar las condiciones por unidad* con un registro donde cada
  aplicación aporte sus botones a la ficha: es el cambio que haría repetible
  añadir funciones, y toca código que hoy funciona.

## Pendientes de rendimiento

- **Catálogo de traducciones.** Usa el dominio completo de textos del sistema;
  separar los que de verdad usa JavaScript lo reduciría a una fracción.
- **Miniaturas.** Las galerías usan imágenes de 1 672 × 941 como miniatura.
- **Caché compartida.** No hay `CACHES`: cada proceso tiene la suya.
- `politica_de_permisos` consulta la base en cada respuesta HTML
  (`apps/core/middleware/security.py:8`).

## Verificación

Todo se ejecutó contra PostgreSQL desechable, separado de las bases operativas,
sobre el mismo árbol que se confirmó en Git.

| Comprobación | Resultado |
| --- | --- |
| Suite completa (`tests`, `scripts.tests`, `apps`, 4 procesos) | 5 887 pruebas correctas; 29 omitidas (16 son las del módulo opcional, que se ejecutan aparte) |
| Módulo opcional activado (`apps.conexiones`) | 16 correctas; migraciones sincronizadas |
| Ruff (`ruff check .`) | Sin incidencias |
| `check --fail-level WARNING` y `makemigrations --check` | Sin incidencias, con el módulo apagado y activado |
| Auditorías del repositorio, módulos, contratos de señales, plantillas y huérfanos | Sin hallazgos |
| Pruebas de JavaScript | 347 correctas |
| Construcción de la imagen de producción | Correcta; 2 754 estáticos en el manifiesto |
| `check --deploy` con valores de ejemplo | Falta el correo SMTP y declarar las dos decisiones de publicación |
| Servidor local | Portada y páginas principales en 200; módulo de conexiones probado de punta a punta |

Durante la revisión la suite detectó tres contratos del propio sistema que los
cambios habían roto, y se respetaron al corregir:

- El registro de módulos debe cargarse sin importar Django: la decisión del
  módulo opcional se lee del entorno en `config/opcionales.py`.
- `apps/recursos/models/recursos.py` tiene una huella de revisión de señales,
  que se actualizó tras revisar el cambio
  ([detalle](contratos-senales-heredadas.md)).
- El formulario de referencia comercial ya registra su propia auditoría: el
  registro añadido al editor no la duplica.

**Base local.** Se aplicaron `conexiones.0001` y `core.0002`, que crean cuatro
tablas en la base central y no tocan ninguna existente. En la base de Centros
no cambió ninguna tabla; solo se completó su registro de migraciones, que
estaba atrasado. Antes se respaldaron ambas bases y los roles en
`var/backups/pre-migracion-20261114-auditoria/`.
