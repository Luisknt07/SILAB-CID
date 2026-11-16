# Estado actual del proyecto — 16 de noviembre de 2026

**Un anexo por cada documento que pide la universidad (16 de noviembre).**

- **Estructura.** Los anexos del informe responden uno a uno a las exigencias de la
  universidad y llevan su nombre. Un laboratorio entrega ocho anexos fijos y tres
  condicionales (desechos, investigación y transferencia). Cada tipo de unidad lleva los
  suyos: [docs/estructura-anexos-por-tipo-de-unidad.md](docs/estructura-anexos-por-tipo-de-unidad.md).
- **Formato.** Datos generales con la exigencia que responde y tablas numeradas «n.m», con
  todos los registros del período. Cada dato tiene un anexo dueño.
- **Captura.** Campos nuevos: unidad del syllabus, superficie y tipo de espacio, simulador,
  clases de insumos, datos del ensayo y condiciones de inspección por tipo de unidad.
- **Control automático.** Revisa cada anexo por separado.
- **Pendiente, a cargo del usuario:** aplicar `documentos.0027` y las migraciones de los
  campos nuevos con un respaldo nuevo, y volver a generar los informes ya preparados.

Detalle en
[docs/calificacion-y-anexos-del-expediente.md](docs/calificacion-y-anexos-del-expediente.md#un-anexo-por-cada-documento-que-pide-la-universidad-16-de-noviembre-de-2026).

**Estado al 15 de noviembre de 2026.**

**Anexos como formato de registro (15 de noviembre, después del rediseño).**

- **Formato.** Un anexo recoge datos; no es un informe. Lleva un cuadro de datos
  generales y una tabla por registro con su total, sin apartados numerados ni
  párrafos. El avance y lo que falta para cumplir quedan solo en el informe.
- **Anexos propios.** Los de planta piloto, centro experimental y observatorio usan
  el mismo formato y ya no se llaman «Informe de…» (`documentos.0026`).
- **Control automático.** Revisa cada anexo fusionado entero (prácticas, seguridad
  y desechos, equipos e inventario, investigación y transferencia).
- **Nombres.** FT02/FT03 desaparecen también de las pantallas de prácticas y
  logística, del consolidado de asignaturas y de su Excel.
- **Pendiente, a cargo del usuario:**
  - aplicar `documentos.0023` a `0026` con un respaldo nuevo;
  - volver a generar los informes 2026-B ya preparados.

**Documentos principales con el formato del informe y seis documentos por semestre (15 de noviembre, rediseño).**

- **Formato principal.** El protocolo, el plan de compras, la planificación y el
  informe vuelven al formato del informe institucional: portada, responsabilidad y
  contenido, y apartados en verde subrayados en dorado. Usan 10 pt con interlineado
  sencillo y tablas de 9 pt, sin desbordes.
- **Anexos.** Los demás documentos conservan el encabezado de tres columnas. El
  informe lleva cinco anexos con una sola plantilla: qué respalda, registros que
  cuentan y qué falta.
- **Paquete del FabLab.** Seis documentos por semestre, que pasan de 124 a 30
  páginas.
- **Nombres.** FT02/FT03 pasan a «prácticas planificadas» y «prácticas ejecutadas».
- **Pendiente, a cargo del usuario:** aplicar `documentos.0023`, `0024` y `0025` con
  un respaldo nuevo y volver a generar los informes 2026-B ya preparados.

Detalle en
[docs/calificacion-y-anexos-del-expediente.md](docs/calificacion-y-anexos-del-expediente.md#seis-documentos-por-semestre-15-de-noviembre-de-2026-rediseño)
y [docs/expediente-de-calidad.md](docs/expediente-de-calidad.md#dos-formatos-documentos-principales-y-anexos).

**Formato único y expediente depurado (15 de noviembre, cierre).**

- **Encabezado.** Todos los PDF de las unidades llevan el encabezado
  institucional de tres columnas: logo; formato e institución; Código,
  Revisión, Período y Versión. Va en todas las páginas, con LiberationSans y
  una sola escala de letra, en vertical y en apaisado.
- **Documentos redactados.** Ya no tienen portada ni índice; las secciones van
  en banda verde.
- **Anexos.** El expediente pasa de 17/16 a 13 documentos por semestre en un
  laboratorio:
  - se retiran el plan semestral de prácticas, el plan de mantenimiento, los
    préstamos y los insumos al corte;
  - el inventario trae los movimientos de insumos;
  - el equipamiento reúne mantenimiento, disponibilidad y funcionalidad, con
    anexo para la meta de mantenimiento en A y en B;
  - los observatorios ya no reciben el registro de uso;
  - las consultas sin registros no se muestran.
- **Pendiente, a cargo del usuario:** aplicar las migraciones
  `documentos.0023` y `0024` en la base local.
- **Validación.** Se hizo sobre una copia restaurada, con datos de prueba en el
  FabLab y en Realidad Extendida; los guiones están en `var/validacion-20261115/`.

Formato en
[docs/expediente-de-calidad.md](docs/expediente-de-calidad.md#dos-formatos-documentos-principales-y-anexos);
expediente depurado en
[docs/calificacion-y-anexos-del-expediente.md](docs/calificacion-y-anexos-del-expediente.md).

**Centro de reportes: solo el informe semestral se califica (15 de noviembre, noche).** El informe de
actividades y cumplimiento de la planificación es el único documento con nota, y esa nota es el
cumplimiento de las metas del plan medido con los registros del período: la Dirección confirma el cierre
calculado y ya no se escribe un porcentaje a mano. Resolución, protocolo, planificación, plan de compras y
demás son de cumplimiento obligatorio (se aceptan u observan; la no entrega queda como incumplimiento, sin
0). Se retiró la rúbrica manual. Cada anexo dice lo que contiene y la meta que respalda (migración
`documentos.0023`); el anexo de equipamiento ya no repite el inventario y la vista previa de acciones de
mejora es el documento que se archiva. La migración quedó sin aplicar en la base local (respaldo y
pasos en el documento). Las 22 categorías del Centro de reportes responden en las 32 unidades. Regla, anexos y unidades sin administrador en
[docs/calificacion-y-anexos-del-expediente.md](docs/calificacion-y-anexos-del-expediente.md).

**Existencias y referencias (15 de noviembre, tarde).** Lo que no existe en una
unidad ya no se muestra ni se cuenta: queda como referencia inactiva o dotación
propuesta, fuera del visor (también para quien gestiona), de las páginas de área,
del inventario, los reportes, los insumos, el software instalado, las reservas y
las operaciones. `manage.py conciliar_existencias --aplicar` separó en la base
local 426 de 2 463 equipos (respaldo previo en
`var/backups/pre-existencias-20261115/`). Existe lo verificado, lo patrimonial del
reporte de bodega y lo declarado; sin reporte de bodega sigue lo básico por
confirmar. El FabLab quedó con sus 26 bienes reales y 12 impresoras declaradas
(se aplicó `preparar_fablab_2026`) y con 4 áreas. La sincronización de fichas ya
no crea existencias que nada respalda. `--revertir` lo deshace. Regla, cifras y
pendientes en [docs/existencias-y-referencias.md](docs/existencias-y-referencias.md).

**Imágenes y videos del catálogo.** `manage.py completar_medios_catalogo --aplicar`
cargó 35 fotos nuevas de familias de equipos y 48 videos (ninguna familia activa
queda sin videos), 22 fotos de insumos y 49 íconos oficiales de programas, todo
con su crédito: fotos libres de Wikimedia Commons y videos verificados para
insertarse. Quedan sin imagen 29 modelos de equipo y 94 insumos para los que no
hay una foto libre que los represente; 66 programas son herramientas internas
sin ícono propio.

**Laboratorio de Realidad Extendida, listo para atender (15 de noviembre).**
`manage.py preparar_laboratorio_xr --aplicar` completó su operación y ya está
aplicado en la base local (respaldo previo en
`var/backups/pre-laboratorio-xr-20261115/`): 7 servicios sin tarifa, 4 requisitos
de acceso con inducción anual, 6 guías de práctica, 5 documentos de la sala,
fichas de las 5 áreas publicadas, recorrido de visitas, plano e ilustraciones
dibujados por el sistema y el curso `XR-CUR-001` sin publicar. Operación,
comprobaciones y lo que le queda a la unidad (verificar equipos, facultad,
cuentas del personal, tarifas, fotos) en
[docs/laboratorio-realidad-extendida.md](docs/laboratorio-realidad-extendida.md).
De paso se corrigió para todas las unidades: un visitante ya no recibe enlaces
a equipos que no puede abrir, la galería de un área no repite imágenes de
referencia, la portada de un curso sin publicar la ve quien lo prepara y la
ficha de un equipo inactivo no ofrece descargas que respondían 404.

Bloque vigente: **desarrollo con Docker en SILAB-CID**.
El usuario identificó expresamente la carpeta
`C:\Users\PC2\Documents\GitHub\SILAB-CID` y el repositorio
`https://github.com/Luisknt07/SILAB-CID`. La rama principal es `main` y `origin`
apunta exclusivamente a ese repositorio. La copia inicial proviene del árbol
validado de CITT, commit `6f6b9a56`; el historial anterior permanece en la carpeta
original. El traslado partió de un único commit, con los dos vídeos LFS
completos. Consultar Git para comprobar el estado de la publicación.

**Auditoría integral del 14 de noviembre.** Revisión completa previa a
producción en [docs/auditoria-integral-2026-11-14.md](docs/auditoria-integral-2026-11-14.md):
qué se midió, qué se corrigió y los pendientes con su ubicación. Resumen:

- **Carga.** Estáticos con huella, derivados WebP y catálogo de traducciones
  publicado (`apps/core/estaticos.py`); la portada pasa de 60,4 MB a 5,4 MB.
- **Seguridad.** Corregidos tres fallos altos (datos personales en la búsqueda
  de participantes, adjuntos ejecutables, vinculación de cuentas sociales).
  El administrador exige segundo factor con aplicación autenticadora:
  obligatorio en producción, optativo en desarrollo con
  `SLCID_ADMIN_SEGUNDO_FACTOR=true`; `SLCID_ADMIN_REDES_PERMITIDAS` lo limita
  por red ([detalle](docs/autenticacion.md#segundo-factor-para-administrar)).
- **Decisiones de publicación.** `SLCID_EXIGIR_EQUIPOS_VERIFICADOS` y
  `SLCID_MEDICION_METAS_HABILITADA` pueden faltar en desarrollo; producción no
  arranca sin declararlas. La primera sigue en falso: de 2 234 equipos
  públicos solo 1 tiene la existencia verificada.
- **Conexiones físico-digitales.** Módulo opcional
  [apps/conexiones](apps/conexiones/README.md) para dispositivos y series de
  medición, activo en el perfil de desarrollo.
- **Gestión.** Las ediciones desde la página de la unidad registran auditoría;
  un área nueva nace no reservable; el asistente de reservas solo ofrece los
  medios propios de la unidad.
- **Limpieza.** 11 funciones y 80 estáticos sin uso retirados.

**Base local.** Se aplicaron `conexiones.0001` y `core.0002` (cuatro tablas
nuevas en `citt_db`; ninguna tabla cambió en `citt_centros_id`, donde solo se
completó el registro de migraciones). Respaldo previo de ambas bases y roles
en `var/backups/pre-migracion-20261114-auditoria/`.

**Abierto para publicar.** Correo SMTP, dominio HTTPS y credenciales
institucionales de Google y Microsoft (aplazados hasta tenerlos); programar
los recordatorios documentales cuando Dirección revise los plazos; depurar los
datos demostrativos en el corte; y los nueve pendientes de seguridad del
informe.

**Arranque de desarrollo.** Usar `docker-compose.local.yml` o
`scripts/iniciar_docker_desarrollo.ps1`, con Docker Desktop iniciado. El perfil
usa PostgreSQL existente en `citt_default`; no recrea bases, volúmenes ni
contenedores de datos. El código y los adjuntos se montan desde SILAB-CID, con
recarga de cambios. La web no recibe credenciales de migración/respaldo ni
montajes del `.env` o de respaldos. El servicio manual `migrar` dispone de
escritura en `apps/` para generar migraciones y de los propietarios para
aplicarlas. Ver comandos y límites locales en README. Producción conserva
su Compose y su procedimiento separados.

**Datos conservados.** Se copiaron `.env`, `var/media`, `var/private`,
`var/microproyectos` y `var/output`. El manifiesto privado con tamaños y huellas
está en `var/traslado-20261114/COPIA-ARCHIVOS.json`. El entorno `.venv` se instaló
desde `uv.lock` en esta carpeta; no depende del entorno de CITT.

Las bases `citt_db` y `citt_centros_id` continúan en el PostgreSQL existente,
volumen `citt_postgres_data`, con sus roles restringidos y configuración
originales. No se sustituyeron ni se reinicializaron. Los respaldos completos
de ambas bases y sus roles están en `var/backups/traslado-20261114/`: restauración
aislada y comparación de 302 tablas / 48.468 filas centrales y 50 tablas / 1.324
filas de Centros. Coinciden datos, secuencias, propietarios, restricciones y RLS.
También se respaldaron el volumen y la imagen del WMS de Logística. Ver
`RESPALDOS-VERIFICADOS.json` y `var/traslado-20261114/LEEME-DATOS.txt`.

**Publicación y privacidad.** GitHub es público. Datos, credenciales y respaldos
quedan en las rutas privadas ignoradas por Git; sólo se publica el código.
El siguiente equipo necesitará esos archivos por un canal protegido para
reproducir los contenidos. No copiar el `.git` histórico de CITT ni sus ramas.
Para nuevos cambios usar `main` y el remoto indicado arriba; la autorización
histórica para publicar en COMPUMAX-EC/CITT ya no es el destino de este proyecto.

**Continuidad funcional.** Permanecen las reservas, visitas, cobro exclusivo de
materiales y agendas unificadas; los 95 artículos de validación conciliados y
los expedientes existentes. La existencia física de equipos e inventario debe
validarse institucionalmente. HTTPS, SMTP y el servidor universitario siguen
aplazados. Las claves antiguas de OAuth y el historial compartido del repositorio
anterior mantienen los límites descritos en el mantenimiento del 11 de noviembre.
Para el desarrollo habitual iniciar el perfil Docker local descrito arriba.

## Historial de bloques anteriores

Las entradas siguientes conservan sus comprobaciones y límites originales;
sus menciones de «vigente», «pendiente» o «siguiente» describen cada corte
histórico. Para retomar el trabajo prevalece el bloque de SILAB-CID anterior.

Bloque vigente: **visitas con modelos de redacción y tabla editable de asistentes**. Dos modelos por propósito, adaptados a unidad, temas y grupo; actualización automática conserva textos manuales. Sin rango de edades en la pantalla. Tabla con cédula, nombres, rol, celular y correo; añadir/quitar, conteo automático o estimado, validación de duplicados y formatos. Persistencia de rol/contactos mediante reservas.0002 aplicada localmente tras respaldo; tres asistentes y una visita históricos conservados íntegramente. Contactos visibles solo en asistencia autorizada, fuera de la agenda pública. Mismo modal, cinco pasos y calendario. 60 pruebas Django y 21 JavaScript correctas; prueba DOM completa en cuatro unidades con tabla y modelos correcta. PostgreSQL QA retirado. [Detalle y respaldo](docs/visitas-modelos-asistentes-2026-11-08.md). Revisión visual Chrome no disponible; sin solicitudes ni correos operativos de prueba ni despliegue universitario.

Bloque anterior: **visitas integradas en el modal y calendario aprobados**. La tercera tarjeta se selecciona y avanza con Continuar por los mismos cinco pasos: grupo/finalidad, recorrido/calendario, requisitos/condiciones y confirmación. Usa la agenda mensual/semanal existente, su API de ocupación y /reservas/crear/; se retiraron la página y el calendario independientes. Los enlaces anteriores abren el modal con visitas seleccionadas. Los controles de otras rutas se restauran al cambiar de tarjeta y no se mezclan recursos con visitantes. Se conservan las 27 unidades habilitadas, sus áreas, requisitos y la activación anterior; sin nuevas migraciones ni cambios operativos. 52 pruebas Django aisladas y 19 JavaScript correctas; prueba DOM con HTML real del asistente en los cinco pasos y cambio entre las tres rutas, un único calendario; 81 HTTP correctos en las 27 unidades y cuatro estáticos vigentes por SHA-256. Computer Use bloqueó la revisión visual por no verificar la URL de Chrome; no se afirma geometría revisada. [Detalle, respaldo y límites](docs/reservas-tres-rutas-2026-11-08.md). 8000 activo; sin solicitudes ni correos operativos de prueba ni despliegue universitario. c5bf33f5 y 1acacd52 publicados con autorización; consultar Git para la corrección.

Bloque vigente: **ocho evidencias universitarias: contenido, nombres y acreditación documental**. Pendientes de FT02/FT03 y guías, inventario físico y lotes, mantenimiento acotado al período, seguridad e inspecciones, desechos con respaldos y resultados de investigación/transferencia. Detalle estructurado, aceptación y huellas en fuentes existentes; accesos directos desde reportes. Misma información en HTML/PDF/Excel. Método 4 conserva enviados 1/2/3; FabLab provisional 19,10 % DEMO y nota oficial 0, sin fabricar evidencias. Migraciones documentos 0004/0005 aplicadas localmente con respaldo y nueve modelos preservados; cuatro nombres estándar aclarados. Regresión y focales cubren 202 casos distintos, más cierre de 20 correcto; 28 HTTP reales unidad/admin y 16 PDF/134 páginas revisados. Navegador conectado no disponible; no se afirma ensayo interactivo. [Detalle y límites](docs/gestion-reportes-verificacion-2026-10-11.md#cobertura-de-las-ocho-evidencias-universitarias--16-de-octubre-de-2026). Pendiente institucional: completar evidencias reales y rectificar archivo ajeno de planificación 2026-A. 8000 activo, sin carga operativa ni despliegue universitario; consultar Git para el commit publicado.

Bloque anterior: **PDF de reportes y visor completos en unidad y administrador**. Formación previa y descarga comparten encabezado/pie institucional. Corregidos pesos faltantes de FT02/FT03 y ancho de tablas; FT02 FabLab pasa de 22 a 12 páginas sin invadir márgenes. Modal abre la página completa; miniaturas sin altura heredada de botones administrativos, rango de fechas adaptable y sin botón comprimido por Grappelli. Mejora FabLab 2026-B: nueva v2 no remitida, recurso 328, con auditoría de sistema; PDF v1/recurso 47 conservado íntegro como obsoleto. Documentos, redacciones y notas sin cambios. Regresión de 73 pruebas con migraciones reales y 5 focales finales correctas; dos escenarios JS correctos, 24 PDF actuales/136 páginas con geometría correcta, Chrome real en 24 escenarios de unidad/admin y cuatro anchos. Sin migraciones nuevas ni despliegue universitario; 8000 activo. [Detalle y límites](docs/pdf-reportes-estandar-2026-10-16.md). Evidencia privada: var/medicion-fablab-20261016/pdf-visual/. Consultar Git para el commit publicado.

Bloque anterior: **documento enviado y fecha de corrección obligatoria de Dirección**. Matriz y revisión priorizan el PDF enviado; borradores y preparados quedan en «Consulta preliminar». «Gestionar fechas» abre un modal propio desde Plazo vigente: institucional, ultimátum colectivo, reapertura individual y corrección. Catálogo describe correctamente fechas fijas y reglas por meses. Usuario confirmó fecha de corrección obligatoria: devolución exige motivo y fecha futura en UI/servidor, audita, invalida recepción/nota vigente y abre la nueva versión; al vencer bloquea incluso si el archivo ya estaba cargado. Solicitud justificada permite reabrir corrección sin un nuevo ultimátum. Preserva puntualidad inicial e instrucciones y exige solicitud nueva tras cada devolución. Retirada acción masiva sin fecha. Históricos observados no reciben fechas inventadas: FabLab debe asignar la de su planificación desde el modal. Migración documentos.0003 aplicada localmente en 8000 tras respaldo verificado y ensayo real de 100 pruebas correctas; cierre adicional 16 pruebas de límites correcto. Conservados todos los campos anteriores de 615 documentos y recursos comprobados; columna nueva nula, cero fechas o notas asignadas. Chrome/HTTP en unidad y administrador a 1600/500 px correctos, sin desbordamiento ni errores JS. Sesiones/Chrome propios retirados al finalizar; 8000 activo con recarga automática. [Detalle](docs/plazos-entregas-direccion-2026-10-16.md). Sin despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **tarjeta de progreso y tablas ordenadas en unidad y administrador**. Avance destacado en tarjeta blanca de máximo 660 px, porcentaje grande, borde verde y cálculo desplegable. Contadores en columnas junto a la tarjeta en escritorio; adaptación a ventanas pequeñas. Dirección muestra el mismo avance general por unidad, también en su resumen cerrado. Corregida matriz administrativa cuyos anchos sumaban 110 %: ahora 100 %, notas envuelven y botones separados. Desplazamiento interno para tablas estrechas; sin invasión de celdas. Cálculos y nivel institucional conservados. 21 pruebas correctas; HTTP 200 en ambas vistas, Chrome real en 1600/1280/500 px: seis casos sin desbordamiento de página, elementos fuera de celdas ni errores JavaScript. Huella de 615 documentos sin cambios; sin migraciones ni escrituras operativas. Sesiones y Chrome propios de QA retirados al cierre. 8000 activo. [Detalle](docs/progreso-general-reportes-2026-10-16.md#tarjeta-visible-y-orden-en-unidad-y-administrador). Consultar Git para el commit publicado.

Bloque anterior: **corrección de la barra general en la consola**. La inclusión del expediente dentro del panel omitía progreso_general y total_entregas: mostraba ausencia de obligaciones aunque había cinco filas con aportes. Se pasan ambos valores, sin cambiar el cálculo. Prueba nueva cubre el panel completo y su fragmento con nota 80 entre cinco: barra 16/100, aporte 16/20 y total cinco. Once pruebas correctas en PostgreSQL desechable; prueba nueva también correcta con migraciones reales completas. Consola real en 8000: HTTP 200 en ambas modalidades, barra 0/100 y cinco aportes. Chrome a 1600/500 px confirma visibilidad sin desbordamiento global ni errores JavaScript. Sesión y Chrome exclusivos de QA retirados; sin escrituras operativas. [Detalle](docs/progreso-general-reportes-2026-10-16.md#corrección-de-la-consola-de-la-unidad). Consultar Git para el commit publicado.

Bloque anterior: **barra general según las evaluaciones de Dirección**. Sobre las entregas, progreso hacia los 100 puntos de todas las obligaciones del período: cada nota final aporta nota/N, con igual peso; pendientes no suman y mantienen su lugar. Cinco entregas: máximo 20 puntos por documento, nota 80 aporta 16. Columna de calificación muestra el aporte individual. Excluye anexos/no aplica, respeta versión y tardanza, incluye filas previstas y cambia con período/año. No modifica promedio parcial, notas ni metas del cierre. FabLab 2026-B: 0 % general (dos notas vigentes cero y tres pendientes); 52,43 % de metas conserva su sección. Diez pruebas nuevas correctas, HTTP y Chrome en 8000 a 1600/500 px correctos, cinco aportes y 615 documentos conservados por huella. Pasada ampliada 18/22; cuatro expectativas antiguas de interfaz fallan también con las plantillas del commit previo, sin modificar esas pruebas. Check/Ruff/migraciones/diferencias correctos. [Detalle](docs/progreso-general-reportes-2026-10-16.md). Evidencia privada: var/medicion-fablab-20261016/progreso-general/. Sin migraciones ni escrituras operativas; 8000 activo. Consultar Git para el commit publicado.

Bloque anterior: **activación autorizada de la medición en 8000**. El usuario pidió concentrar la aplicación en el servidor habitual. Tras respaldo verificado se aplicó exclusivamente documentos.0002 a citt_db y se habilitó SLCID_MEDICION_METAS_HABILITADA=true localmente. FabLab recibió siete registros de evidencia DEMO y seis PDF, sin copiar reservas, prácticas, personas ni requisitos de acceso del escenario aislado. Dos conciliaciones rectificadas con historial para el calendario académico publicado: nueve filas finales (seis verificadas, un borrador, dos rectificadas). Avance provisional real de esa combinación: 52,43 %, doce metas obligatorias, diez barras y dos mediciones pendientes. Nota oficial y bloqueo de envío DEMO conservados. Huellas completas de 615 documentos y de 250 recursos anteriores idénticas. HTTP autenticado, 20 PDF y Chrome a 1600/500 px correctos, sin errores JavaScript. Sesiones QA retiradas; instancia 8001 y su contenedor temporal detenidos con respaldo. 8000 sigue activo. [Detalle](docs/medicion-automatica-fablab-2026-10-16.md#autorización-y-activación-en-la-aplicación-principal). Evidencia privada: var/medicion-fablab-20261016/activacion-8000/. Sin despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **medición automática y demostración de FabLab**. Siete fuentes antes pendientes conectadas a registros y evidencias verificadas, con conciliaciones independientes, inducción por primera entrada, acta de inventario, huellas y rectificación. Formulario modal y respaldos privados para unidad/Dirección. Avance separado de nota oficial; snapshots v1/v2 conservados, v3 con control de fuentes al enviar. DEMO aislada en http://127.0.0.1:8001/: 12 metas obligatorias, avance 80,56 %, sin aprobar planes ni enviar ejemplos. Cierre: 60 pruebas correctas (59 + 1 focal), migración real ensayada en QA, 20 PDF y Chrome a 1600/500 px correctos. pypdf fijado en dependencias. Base institucional intacta: 615 documentos, tabla nueva ausente y función desactivada. **Pendiente: autorización expresa para migrar documentos.0002 y activar la medición en 8000**; revisión automática rechazó ese cambio persistente y no se ejecutó. Ejemplos en PostgreSQL temporal separado, sin volúmenes operativos. [Detalle](docs/medicion-automatica-fablab-2026-10-16.md). Evidencia privada: var/medicion-fablab-20261016/. Consultar Git para el commit publicado.

Bloque anterior: **auditoría del Centro de reportes**. Cinco correcciones: atenciones/horas con cierre efectivo (FabLab 18/195 frente a 1/1 verificables), FT03 sin eliminados, veredicto único con medir_meta, código canónico centro_experimental y FT02 aprobado/vigente para acreditar la meta (6 de 71 registros). Se conservan archivos, estados y notas históricas. Lectura estricta de 594 reportes/32 unidades, 75 PDF, 77 archivos con huellas correctas, 68 salidas de tres Centros I+D y 615 registros conservados. Regresión amplia de 397 casos: 393 correctos y cuatro expectativas/fixtures ajustadas; cierre focal 36/36 correcto, con siete regresiones nuevas. Check/Ruff/auditoría estricta correctos. **Pendiente importante:** siete metas obligatorias de FabLab carecen de ruta automática completa; no usar la nota como evaluación integral hasta conectar sus evidencias/denominadores. Mantenimiento requiere programación real. Planificación FabLab 2026-A, documento 626, contiene una certificación equivocada; se conserva para rectificación autorizada. [Informe y alcance](docs/auditoria-centro-reportes-2026-10-16.md). Evidencia privada: var/auditoria-centro-reportes-20261016/. Sin migraciones de aplicación ni despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **numeración de entregas, metas y documentos**. Columna N.º continua entre grupos en ambas tablas, con total visible. Un anexo con varios indicadores conserva un número. Texto aclara borrador al día frente a anexos archivados con el envío. Nueve pruebas puras correctas, Ruff/check y auditoría estricta sin errores. Lecturas SQL estrictas verifican cinco entregas por corte y siete en el año; Chrome aislado a 1366/500 px verifica 16 ítems y 17 indicadores en unidad/Dirección, sin desbordamiento global. FT03 actual con marca y archivo conservado sin ella. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#numeración-de-entregas-y-evidencias--16-de-octubre-de-2026). Evidencia privada: `var/reportes-items-20261016/`. Sin cambios de envíos, datos, archivos ni calificaciones. Consultar Git para el commit publicado.

Bloque anterior: **fondo principal blanco en la consola de unidad**. La superficie `.unit-console__viewport` cambia de `#f8faf9` a `#fff`, con versión de caché renovada en sus cuatro plantillas. Django check sin incidencias y CSS actualizado servido con HTTP 200. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#fondo-principal-blanco--16-de-octubre-de-2026).

Bloque anterior: **tabla de metas más compacta e iconos**. Se recupera el icono de documento con SVG local y se separan Estado, Avance y Detalle en columnas, conservando meta, registrado y acceso PDF. Motivos largos quedan en desplegables nativos; faltante y excedente se muestran en Detalle. Se retiran fondos amarillos de pendientes, exigencias, grupos y aviso; tonos neutros/verde institucional y rojo de incumplimiento conservados. Borde amarillo de títulos mantiene identidad institucional. Sin cambios de cálculos, permisos, datos ni archivos. Ocho pruebas puras existentes, check, 411 plantillas y auditoría estricta correctos. Chrome aislado: unidad/Dirección a 1366/500 px, nueve columnas, 16 iconos y 16 enlaces; mismos 17 indicadores, porcentajes y destinos. Sin excepciones ni desbordamiento global; detalles desplegables y PDF visibles en escritorio. Tabla de unidad comparada con HTML anterior y CSS de HEAD: 1253→961 px (23 % menos altura) a 1366 px. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#tabla-compacta-iconos-y-paleta-neutra--16-de-octubre-de-2026). Evidencia privada: `var/reportes-compacto-20261016/`. Sin migraciones ni despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **metas y anexos en una sola tabla**. Unidad y Dirección comparten Metas y documentos del informe de cierre: documento/actividad, exigencia, indicador, meta, registrado, cumplimiento y enlace PDF. Se retira la tabla de indicadores duplicada. Las metas sin anexo específico, incluidas mantenimiento, capacitación y difusión, permanecen con acceso al informe general; los anexos con dos indicadores conservan ambos y un único enlace. Se mantienen agrupaciones, barras, faltante, excedente, motivos y alertas; explicación de cálculo en desplegable. Proyección de presentación sin consultas adicionales, cambios de nota ni escritura de instantáneas. Regresión de 37 casos, 36 correctos inicialmente; la fixture nueva se completó con un plan guardado y cierre de 2/2 correcto. Ocho pruebas puras finales correctas. Check, Ruff, 410 plantillas y auditoría estricta correctos. Lectura de 59 vistas/32 unidades, 28 PDF, cuatro cortes y 615 registros conservados. Chrome aislado: unidad/Dirección en 1366/500 px, una tabla, 17 indicadores y 16 enlaces por escenario, sin excepciones ni desbordamiento global. Sin migraciones, datos operativos modificados ni despliegue universitario. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#metas-y-anexos-en-una-sola-tabla--15-de-octubre-de-2026). Evidencia privada: `var/reportes-unificados-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **orden de entrega y carga con envío conjunto**. Tabla de unidad: Reporte → Plazo → Edición → Borrador → Documento enviado (Cargar documento si aún no se envió) → Fecha de envío → Estado → Observación → Calificación de Dirección. La fecha de revisión acompaña a la calificación. El modal de carga retira PDF, editor, descripción extensa e historial repetidos; conserva adjuntar/enviar y requisitos de entrega, revisión de anexos y retiro opcional de una carga equivocada. `cargar` con `enviar=1` ejecuta carga y validación dentro del bloqueo y transacción existentes: un rechazo revierte archivo nuevo, recursos y auditoría. El envío confirmado sustituye el botón de carga por el PDF enviado y cierra el modal. No se cambian metas, notas anteriores ni permisos de Dirección. Check, Ruff, sintaxis JS, 410 plantillas y auditoría estricta correctos; lectura de 59 vistas/32 unidades, 28 PDF, cuatro cortes y 615 registros conservados. Regresión de 88 casos y cierre focal de 6/6 con migraciones reales; detalle de expectativas ajustadas en el informe. Ocho condiciones de interfaz verificadas con HTML real en Chrome aislado, PDF y POST simulados, sin escrituras operativas. [Detalle y regresión](docs/gestion-reportes-verificacion-2026-10-11.md#orden-de-entrega-y-carga-con-envío-conjunto--15-de-octubre-de-2026). Evidencia privada: `var/reportes-flujo-20261015/`. Sin migraciones de aplicación ni despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **edición directa, PDF y obligaciones por catálogo**. Columna Edición independiente: abre el editor guiado en un único modal, cierra antes el diálogo de entrega y conserva guardado automático, control de cierre y regreso a la tabla. Documentos abre directamente borrador actualizado y archivo preparado/firmado/enviado; Dirección mantiene Evaluar separado. Los planes nuevos/revisados guardan `minimos_catalogo=2`: mínimos numéricos aplicables obligatorios, FT02 y FT03 con seis prácticas en tipos técnicos; no se pueden desactivar ni rebajar. Préstamos, equipamiento, insumos y mejora sin mínimo quedan como anexos automáticos, sin meta independiente ni cero en la media. Demanda conserva compromiso cuando se programa. Histórico enviado y política 1 conservados. Regresión: 69 casos, 67 correctos inicialmente y dos corregidos/repetidos correctamente; nueve comprobaciones de interacción en Chrome aislado sin POST operativo, motor PDF simulado, PDF reales comprobados por separado. Lectura estricta de 59 vistas/32 unidades, 28 PDF, cuatro cortes y 615 registros conservados. Sin migraciones ni escrituras de datos/archivos operativos. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#edición-directa-pdf-y-obligaciones-por-catálogo--15-de-octubre-de-2026). Evidencia privada: `var/reportes-accesos-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **mínimos automáticos y avance de metas**. El catálogo completa las metas y el servidor impide reducir su mínimo. Cantidades por tipología obligatorias en planes nuevos/revisados; demanda sin cupo inventado. `minimos_catalogo=1` conserva la regla en el plan; lecturas históricas y notas enviadas no se recalculan. Borradores anteriores proponen corregir metas inferiores y requieren guardar. Editor, indicadores y anexos muestran registrado, estado, barra y faltante; mediciones ausentes siguen pendientes. Avance lateral renombrado a redacción. Primera regresión 54/56 con migraciones reales; expectativa antigua y fixture de prueba corregidos. Cierre 57/57 en PostgreSQL desechable con esquema actual y siete pruebas puras posteriores correctas. Check, Ruff, JS, 377 plantillas, inventario y auditoría estricta correctos. Lectura de 59 vistas/32 unidades, 28 PDF, cuatro cortes y 615 registros conservados; Chrome aislado a 1348/500 px sin desbordamiento global. Sin migraciones ni escrituras de datos/archivos operativos. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#mínimos-automáticos-y-avance-de-metas--15-de-octubre-de-2026). Evidencia privada: `var/reportes-metas-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **corrección de paleta institucional**. Por aclaración del usuario, el realce se limita a títulos con verde suave, texto verde y borde amarillo institucionales. Tablas, nombres y carpetas recuperan sus colores previos; se retira el azul generalizado. Agrupaciones y alertas conservadas, opcionales en neutro. Solo estilos y renovación de caché, sin cambios de lógica/documentos. Check y diferencias correctos; Chrome aislado a 1348/500 px sin desbordamiento global, con láminas previas y CSS actualizado. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#corrección-de-paleta-institucional--15-de-octubre-de-2026). Evidencia privada: `var/reportes-paleta-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **jerarquía visual y alertas de metas**. Encabezados azul oscuro, títulos azules con fondo suave y grupos de reportes resaltados. Metas/anexos agrupados por exigencia, conservando la condición de cada indicador. Etiquetas con símbolo y texto: cumple verde, no cumple obligatorio rojo, pendiente de medición ámbar, opcionales azul y no aplicables/indefinidos neutros. CSS compartido entre unidad y Dirección. No cambia cálculos, notas, permisos ni documentos. Cinco pruebas sin base de datos, check, Ruff, 376 plantillas y auditoría estricta correctos. Lectura: 59 vistas/32 unidades, 28 PDF, cuatro cortes y 615 registros conservados. Chrome aislado a 1348/500 px sin desbordamiento global; estados alternativos en lámina sintética separada. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#jerarquía-visual-y-alertas-de-metas--15-de-octubre-de-2026). Evidencia privada: `var/reportes-estilo-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **anexos en tabla compacta**. Unidad y Dirección muestran Anexo, Exigencia, Indicador, Meta, Registrado, Cumplimiento y Documento; nombres y enlaces agrupados cuando hay dos indicadores. Desplazamiento horizontal interno en ventanas estrechas. Se conservan metas, cálculos, enlaces, estados y resumen general; sin migraciones ni escrituras de datos operativos. Check y 374 plantillas correctos; 59 vistas/32 unidades, 28 PDF, cuatro cortes alternativos y 615 registros conservados. Chrome aislado a 1350/502 px interiores, sin desbordamiento global. [Detalle](docs/gestion-reportes-verificacion-2026-10-11.md#anexos-en-tabla-compacta--15-de-octubre-de-2026). Evidencia privada: `var/reportes-tabla-anexos-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **exigencia, meta e indicador junto a cada anexo**. Planeación permite elegir obligatoria del período, opcional o no aplica; se mantienen los cuatro requisitos institucionales existentes y el servidor impide desactivarlos. Todos los anexos del cierre tienen vínculo de indicador; FT02 usa planificación, FT03 ejecución. Cada tarjeta y la revisión de Dirección muestran exigencia, indicador, meta, registrado y estado. Opcionales no entran en la media; no aplicables no se convierten en ceros. La planificación PDF conserva las elecciones y no se genera para firma con actividades seleccionadas sin meta. Préstamos entregados, movimientos de insumos y disponibilidad actual del equipo tienen contador; lo no verificable sigue pendiente, sin aprobación ficticia. Las entregas anteriores y cálculos enviados v1 conservan sus condiciones y notas. Sin migraciones ni cambios de datos/archivos operativos. [Detalle y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#exigencia-y-metas-de-los-anexos-desde-planeación--15-de-octubre-de-2026). Evidencia privada: `var/reportes-obligaciones-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **borrador al día e informe de cierre por indicadores**. Ver → borrador del sistema + documento firmado/enviado; historial interno conservado. Cierre con avance proporcional hasta 100 %, evidencia ausente 0 % y metas sin denominador verificable pendientes sin crédito. Requiere plan aprobado e informe completo. Preparar conserva cálculo y anexos antes de firmar; enviar no regenera sus archivos y rechaza cambios posteriores de contenido/anexos. Dirección revisa metas y anexos en un modal y confirma el cálculo o devuelve; unidad nunca evalúa. Entregas históricas conservan evaluación documental. PDF con enlaces a todas las evidencias, visor con regreso al informe y borrador marcado sin reemplazar el enviado. Ver [detalle y comprobaciones](docs/gestion-reportes-verificacion-2026-10-11.md#borrador-al-día-y-cierre-con-indicadores--15-de-octubre-de-2026). Evidencia privada: `var/reportes-indicadores-20261015/`. Sin migraciones ni cambios de datos o archivos operativos. Consultar Git para el commit publicado.

Bloque anterior: **documentos, fechas y rectificación de anexos**, detallado en [la verificación de reportes](docs/gestion-reportes-verificacion-2026-10-11.md#documentos-fechas-y-rectificación-de-anexos--15-de-octubre-de-2026). Unidad: tabla con Documentos, Gestión y fechas de envío/revisión; un acceso por función, archivos/versiones en modal y anexos dentro de Gestionar entrega. Administrador: documentos separados de Evaluar y fechas visibles. Se puede retirar la revisión de un anexo, actualizarlo individualmente y revisarlo otra vez; conserva PDF anterior, versión y auditoría. Enviado permanece cerrado, incluso para superadmin, hasta devolución de Dirección. La carga no se presenta como envío; los envíos devueltos se recuperan de auditoría cuando existe constancia para esa versión. Sin migraciones ni cambios de datos operativos. Regresión inicial de 125 casos; tres casos necesitaron ajustar expectativas de enlaces/textos o una referencia de archivo en la prueba. Cierre focal de 16/16 correcto. Lectura de 59 vistas/32 unidades, 28 accesos a PDF y cuatro cortes alternativos: 615 registros conservados. Check, Ruff, sintaxis JS y 367 plantillas resueltas correctos; inventario actualizado. Evidencia privada: `var/reportes-documentos-20261015/`. Consultar Git para el commit publicado.

Bloque anterior: **unidad remitente y Dirección evaluadora**, con [detalle y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#separación-entre-unidad-remitente-y-dirección--14-de-octubre-de-2026). El Centro de reportes de la unidad no muestra Evaluar ni rúbrica, tampoco para superadmin: tabla de seis columnas con estado/PDF/observación/acciones; Gestión en modal y Versiones en acceso separado. Preparación, firma, carga, revisión de anexos y envío conservados; anexos se presentan como revisión de la unidad. Enviado queda en consulta; nota y respuesta completas son lectura, no edición. Las acciones de recepción/evaluación/habilitación se rechazan en el endpoint de unidad; su edición de enviados se bloquea transaccionalmente incluso para root. Enviar no recibe ni evalúa. Dirección conserva tablero general y modal de evaluación en administrador; versiones/retiro de enviado en otro modal, preservando archivo e historial. Devolución habilita corrección y nueva versión enlazada. Guardados administrativos permanecen en admin; fragmento de revisión preservado al actualizar tablero. 131 casos cubiertos: 128 correctos inicialmente, tres comprobaciones de etiquetas/accesibilidad ajustadas y cierre 13/13 correcto; siete casos nuevos de roles y flujo. 211 JavaScript, 399 plantillas, check/Ruff/auditoría estricta e inventario correctos. Chrome consola/página/admin en cuatro tamaños, gestión/PDF/versiones/evaluación y cuatro guardados simulados correctos; operaciones reales verificadas en PostgreSQL QA. 59 lecturas/32 unidades, 28 PDF y cuatro cortes alternativos; 615 registros conservados con ambas conexiones en lectura estricta. Evidencia privada en `var/reportes-roles-20261014/`. Sin migraciones, cambios de datos/archivos operativos ni despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **reportes en un solo espacio y versiones de archivos**, con [diagnóstico y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#reportes-en-un-solo-espacio-y-versiones-de-archivos--14-de-octubre-de-2026). Gestionar, Evaluar, Ver detalle y PDF trabajan dentro del mismo Centro de reportes; se elimina su diálogo adicional y el enlace de evaluación al tablero general. PDF junto a entrega/rúbrica, lectura adaptable y regreso de foco a la tabla. Se reutilizan comandos y rúbrica administrativos, con regreso limitado a la misma unidad; carga, firma, anexos, plazos, recepción, observaciones y evaluación conservados. Historial de archivos por cadena y auditoría nativas; versiones anteriores consultables con autorización. Retiro con motivo/confirmación/versionado y huella; enviados solo por Dirección, archivo e instantáneas conservados, retorno a pendiente sin calificación y carga posterior con numeración continua. Los archivos compartidos con otro año se respetan. Diagnóstico FabLab: adjunto del informe de cierre es planificación LOTCE y ya es v1 sin predecesor; no existe una original anterior recuperable. No se retiró ni sustituyó operativamente. Regresión de 124 casos: 120 correctos, cuatro expectativas adaptadas al detalle diferido y cierre focal 4/4 correcto; diez casos nuevos incluidos. 211 JavaScript, 396 plantillas, check/Ruff/auditoría estricta e inventario correctos. Chrome página/consola en cuatro tamaños: visor real, evaluación, control histórico, guardado visual simulado y foco correctos. 59 lecturas/32 unidades, 28 PDF y cuatro cortes alternativos; 615 registros conservados, ambas conexiones en lectura estricta. Evidencia privada en `var/reportes-unificados-20261014/`; sin migraciones, cambios de archivos/datos operativos o despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **tabla de entregas y ruta visible**, con [detalle y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#tabla-y-ruta-de-trabajo--14-de-octubre-de-2026). Por preferencia del usuario, las entregas vuelven a una tabla fija con PDF, nota y observación breve visibles; las agrupaciones no se despliegan. Se separa el comentario de la conclusión numérica generada, conservando íntegramente la evaluación oficial en Ver detalle. Ruta visible: preparar, revisar/enviar, recibir/evaluar y seguimiento, con responsables; cada fila indica su siguiente paso según firma, plazos y estado real. Gestionar abre una ventana con entrega/plazos y evaluación/observaciones; se conservan formularios, responsables, fechas, avance del editor y recomendaciones anteriores. Sin JavaScript se abre un detalle autorizado de la misma unidad/período; selección ajena rechazada y receptor en solo lectura. Anexos e informes siguen visibles; tras una acción se resalta la fila. Pasaron 54 regresiones iniciales, 16 de cierre y 12 de entrega/navegación; 211 JavaScript, 396 plantillas y controles correctos. Chrome página/consola en cuatro tamaños: tabla adaptada, observación visible, ventanas, cambio de sección y foco/Tab/Escape con PDF superpuesto. 59 lecturas/32 unidades, 28 PDF y cuatro cortes alternativos correctos; 615 registros conservados. Inventario actualizado. Evidencia privada en `var/reportes-experiencia-20261014/`; sin migraciones, cambios de datos operativos o despliegue universitario. Consultar Git para el commit publicado.

Bloque anterior: **acceso visible a todos los reportes**, con [corrección y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#acceso-visible-a-reportes--corrección-del-14-de-octubre-de-2026). El usuario aclaró que optimizar debe conservar todas las funciones y facilitar encontrar los reportes existentes. La lista «Reportes y anexos» vuelve a estar desplegada en la pantalla principal; FabLab conserva sus 13 anexos del cierre, uno de planificación y cuatro informes auxiliares también visibles. Navegación directa y enlace desde la entrega, sin duplicar los documentos ni convertir anexos en obligaciones independientes. Filtros limitados a entregas; actualizar/validar regresa a la lista correspondiente. Firma, permisos, recepción, evaluación, metas, historial, mejora y reporte institucional conservados. 59 vistas/32 unidades correctas, 615 registros sin modificaciones, 28 accesos a PDF originales en el proceso QA de lectura y cuatro períodos alternativos sin colisiones. Chrome: página/consola en cuatro tamaños, filtros, anclas, regreso y lectura sin JavaScript. 211 JavaScript, 394 plantillas y controles correctos. Evidencia privada en `var/reportes-experiencia-20261014/`. Consultar Git para el commit publicado; sin despliegue universitario.

Bloque anterior: **experiencia compacta de reportes**, con [alcance y verificación](docs/gestion-reportes-verificacion-2026-10-11.md#experiencia-de-reportes--14-de-octubre-de-2026). Una lista de entregas con seis columnas, búsqueda y estado; Ver PDF, Gestionar y Evaluar según permiso. Se retiró la matriz repetida de nueve columnas; la corrección vigente restituye la visibilidad inicial de anexos e informes auxiliares. Dirección también usa seis columnas y una sola acción de guardado de rúbrica; visor PDF atiende Tab/Escape sin cerrar la evaluación subyacente. Se conservan firma, recepción, notas, criterios, plazos, auditoría y archivos, sin migraciones ni cambios de datos operativos. Regresión: 144 casos aprobados y 13 focales de cierre; dos expectativas antiguas de texto/botón se adaptaron al diseño. 211 JavaScript, 394 plantillas y controles de código/modelos correctos. Lectura de 59 perfiles sobre 32 unidades HTTP 200, sin IDs duplicados. Comparación Chrome en 1366/768/390/320 y consola/tablero/modal; filtros, regreso a la entrega y visor comprobados. La reducción de altura entonces medida corresponde al diseño previo a la corrección de visibilidad. Evidencia privada en `var/reportes-experiencia-20261014/`; sin despliegue universitario.

Bloque anterior: **estándar común e imágenes de café**, con [detalle y comprobación](docs/aceptacion-plantas-piloto.md#estandarización-visual-de-café--14-de-octubre-de-2026). Las 56 referencias usan exactamente `portal/pages/unidades/aula/equipo.html`, igual que los equipos de Lácteos; se retiró la plantilla particular y se conservaron rutas y datos. Las cinco áreas usan la galería y reproductor comunes: 24 imágenes y siete videos de fuentes verificadas. Cada equipo y los 17 insumos tienen imagen. Veinte WebP nuevos (13 generados con image_gen integrado y siete CC BY-SA 4.0) suman 3.630.496 bytes; se reutiliza el catálogo existente. Procedencia y conjunto resumido de instrucciones junto a los recursos. Trilla explícita en el menú y relacionada con las tres rutas de café verde, sin duplicar las 15 recetas/118 etapas. `completar_medios_cafe` simula solo SELECT, aplica en transacción y conserva ediciones, archivos propios y decisiones editoriales mediante códigos estables. Carga local aplicada; segunda simulación sin cambios, cero activos/stock/órdenes/lotes. Regresión: 130 casos aprobados y seis pruebas de cierre de medios, 211 JavaScript, 391 plantillas, Ruff/check y sin migraciones nuevas. Chrome: 189 vistas de café y tres de contraste con Lácteos en 1366/390/320 px; visor normal/completo, imágenes cargadas y ampliación, sin desbordamiento global. Se corrigieron mínimos de cuadrículas en el CSS común del equipo. Evidencia privada en `var/cafe-estandar-20261014/`; consultar Git para el commit publicado. Sin despliegue universitario ni habilitación comercial.

Bloque anterior: **equipamiento individual y cadena completa de café**, con [alcance y comprobación](docs/aceptacion-plantas-piloto.md#equipamiento-individual-y-cadena-completa-de-café--14-de-octubre-de-2026). Cinco áreas y 56 fichas individuales agrupadas por función, incluido laboratorio de calidad con 19. Quince rutas/118 etapas; grano y molido de 250, 500 y 1.000 g, recepción/silo/trilla/tamaños/banda/tueste/silo/molienda/empaque/etiqueta/bodega. Diecisiete productos y diecisiete insumos, sin activos ni stock inventados. `completar_planta_cafe` conserva ids, relaciones y ediciones mediante reconocimiento de contenidos previos; simulación SELECT y repetición sin cambios. Carga local aplicada preservando las doce recetas, 59 etapas y 29 referencias originales. Fichas GET con gobierno editorial y edición nativa; áreas móviles ajustadas a 320 px. Pasaron 125 ejecuciones de regresión, nueve pruebas de cierre, 211 JavaScript, 391 plantillas y controles de código/modelos. Chrome: 164 casos y 16 focales finales en cuatro tamaños, sin desbordamientos. Evidencia privada en `var/cafe-cadena-20261014/`; consultar Git para el commit publicado. Sin despliegue universitario ni habilitación comercial.

Bloque anterior: **contenidos y sistemas productivos de la planta de café**, con [alcance y verificación](docs/aceptacion-plantas-piloto.md#ampliación-técnica-de-café--13-de-octubre-de-2026). Cinco familias, doce procesos/59 etapas, catorce productos (doce públicos y dos residuos internos), dieciséis insumos/materiales, dos fichas de área y veintinueve tipos de equipo de referencia. Lavado/honey/natural, preparación de verde, desarrollo de muestras, perfiles de filtro/espresso, molienda y empaque; 34 adjuntos (32 HTML originales y dos CSV), ocho prácticas y ruta formativa de 32 horas sin crear edición o certificación. Guías de origen/finca, fermentación, secado, cata/CVA, calidad, ambiente, almacenes/inventario, costos, servicios/maquila, ventas y trazabilidad/retiro. Calculadora propia sin escrituras ni red: cadena de rendimientos por matriz, secado por sólidos conservados, bolsas completas, remanente y costos. Ruta nativa relativa al dominio y menú de simuladores; reutiliza ERP, permisos y editores. Cargador `preparar_planta_cafe --simular` sólo SELECT; `--aplicar` transaccional, altas conservadoras, preserva ediciones/desactivaciones y retira sus propios archivos ante fallo. Aplicado localmente y repetido sin cambios. Se conserva estado en formación; cero activos físicos vinculados, stock, órdenes o lotes de café, sin precios/vidas útiles/autorizaciones inventados. 104 pruebas de regresión y ocho focales finales aprobadas; 211 JavaScript; Ruff/check, sin migraciones y 389 plantillas. Chrome: 40 vistas en 1366/768/390/320, visor normal/completo y ocho capturas. Adjuntos nuevos 158.428 bytes; evidencia ignorada en `var/cafe-20261013/`. En balances teóricos, lavado/natural difieren 1 g/4 g por precisión de porcentajes de etapa; no son registros medidos. Pendiente institucional: recursos/capacidad, responsable, constitución, validación de procedimientos/inocuidad, habilitación comercial, tarifa, arte y estabilidad. Código y cargador se publican por Git; datos locales no se suben ni se despliega al servidor universitario en este bloque.

El cierre anterior se conserva a continuación como antecedente.

Bloque anterior: **organización y operación aplicada del CIDT**, con [implementación y verificación](docs/auditoria-centros-id-contenidos-funciones-2026-10-07.md#implementación-de-organización-y-operación-del-cidt--13-de-octubre-de-2026). Navegación por cinco Tecnologías aplicadas, dos Plataformas operativas y Sistemas transversales; Comercio Exterior integrado en Smart CEDI con FK propia y enlaces conservados. Sala de Control como sistema transversal; oficina de innovación/transferencia en Gobierno y gestión, con coordinación de I+D, servicios, producción, vinculación, prácticas, visitas y pasantías. Nueve fichas con 37 sectores/operaciones, materiales y 37 aplicaciones para 16 carreras. Factory: industrialización, celdas, líneas, calidad y lotes/series; CEDI: diez sectores y flujo de abastecimiento, almacén y distribución, con entrada directa de plantas/fincas. Cuatro servicios nuevos: CIDT pasa de 57 a 61; nueve servicios transversales completados. Migración aditiva 0017 aplicada con el migrador local y rol de mantenimiento, sin elevar el usuario web. Carga conservadora: 49 registros iniciales y 99 en cierre (90 etiquetas heredadas y nueve fichas); repetición cero cambios. Identificadores previos conservados: nueve componentes, 103 fichas de equipos, 18 imágenes, 12 documentos, 12 proyectos y diez resultados; pasos 61→64, articulaciones 28→35. Sin cambios en muestras, estados, precios, validaciones o permisos. Resultados compartidos visibles desde áreas participantes sin duplicación y con filtros públicos. 306 pruebas principales y nueve focales finales, 195 JavaScript, Ruff/check y 388 plantillas correctos; modelo sin migración pendiente. Chrome: doce páginas/vistas nativas en cuatro anchos (1366/768/390/320), además de CEDI incrustado y completo; seis capturas. Rejillas heredadas corregidas para ajustarse al ancho del iframe sin recortar contenido. Evidencia ignorada en `var/cidt-organizacion-20261013/`. Este bloque organiza y documenta la operación: no instala maquinaria ni certifica capacidad masiva o integración MES/WMS industrial completa. Siguiente: verificar activos, capacidad, responsables y condiciones, operar expedientes piloto y conectar sistemas propietarios según la ruta. Consultar Git para el commit publicado.

Bloque anterior: **análisis de contenidos, capacidad científica y servicios de Centros I+D**, con [inventario, matriz de veinte áreas y ruta de implementación](docs/auditoria-centros-id-contenidos-funciones-2026-10-07.md#análisis-de-contenidos-capacidad-científica-y-servicios--13-de-octubre-de-2026). Revisión de código y bases locales `centros`/`default` en transacciones de solo lectura: 3 centros, 20 áreas, 80 servicios sujetos a evaluación. Los 12 proyectos, 10 resultados y 3 casos del CIDT son muestras locales; fuera del escenario no hay proyectos/resultados institucionales registrados. Cien fichas no demostrativas de equipamiento son categorías sin código ni activo individual/reserva; no equivalen a cien máquinas instaladas. Tres áreas CIDT carecen del texto de capacidades y nueve servicios transversales de alcance técnico completo. No hay validación de identidad/estado registrada, tarifas documentadas ni correo general en los tres centros; CIAB/CDHT siguen como propuestas. Sí existe lectura de cursos vinculados, con seis fichas mostradas en CIDT; no confundirla con formación propia operada. 103 direcciones comprobadas: 101 HTTP 200, dos 404 previstos para Innovación sin contenido en CIAB/CDHT, sin respuestas 500. Sin cambios de aplicación, migraciones, permisos o datos institucionales; esta auditoría no vuelve a ejecutar la suite funcional ni certifica recursos físicos. Referentes oficiales contrastados: Fraunhofer, TNO, VTT, CENAIM/SILAB, LabXchange, OCDE, GO FAIR y W3C. Evidencia local ignorada en `var/auditoria-centros-contenido-20261013/`. Siguiente bloque recomendado: veracidad/estado, responsables/contacto, capacidades pendientes y fichas técnicas, seguido de proyectos reales, operación, autogestión y experimentación reproducible. Consultar Git para el commit publicado.

Bloque anterior: **indicador de Centros I+D y lateral compacto**, con [medición y verificación](docs/auditoria-centros-id-contenidos-funciones-2026-10-07.md#ajuste-de-distribución-y-navegación--13-de-octubre-de-2026). La cabecera reconoce los controladores de Centros, además del catálogo. El lateral integra carreras en la adscripción, resume contacto/ubicación y muestra los cuatro conteos en dos filas compactas. Acceso a identidad completa y edición autorizado. Altura combinada reducida 45 % a 1.720 px y 46 % a 390 px con los mismos registros. 74 pruebas multibase, 195 JavaScript y controles de código/migraciones aprobados. Cinco tamaños comprobados en Chrome, incluido el indicador en el menú móvil. Perfiles y contenedor QA retirados; evidencia privada en `var/centros-distribucion-20261013/`.

Bloque anterior: **áreas completas e información lateral de Centros I+D**, con [implementación y verificación](docs/auditoria-centros-id-contenidos-funciones-2026-10-07.md#actualización-de-interfaz--13-de-octubre-de-2026). El catálogo muestra todas las áreas publicadas y cada etiqueta abre su visor. Debajo de Contenidos aparecen Información del centro y Capacidades del centro, desde registros propios, con carreras completas, datos públicos y reglas de validación conservadas. Sin cambios de modelos ni datos institucionales. 70 pruebas con dos bases temporales y 195 JavaScript aprobadas. Tres fichas y 20 accesos a áreas HTTP 200; Chrome en cinco tamaños, incluidos 320 y 390 px, sin recortes. Perfiles y contenedor QA retirados. Evidencia privada: `var/centros-informacion-20261013/`.

Bloque anterior: **verificación posterior de aplicaciones**, detallada en la [revisión del 13 de octubre](docs/extraccion-aplicaciones-2026-10-12.md#revisión-posterior--13-de-octubre-de-2026). Se corrigió el icono del sitio y documentación de rutas retiradas. Pasaron 17 regresiones de portal/rutas en PostgreSQL temporal, los controles de arquitectura, seguridad/operación, 195 JavaScript y 10 de entregas. HTTP: 38 páginas/sondas y 401 recursos sin fallos; galerías de 32 unidades con 204 URL locales de originales/miniaturas verificadas mediante HEAD. Los 38 paquetes Python fijados no tienen avisos conocidos en la consulta actual. Ambos aliases sin migraciones pendientes. El rol web de Centros pasa el verificador; la conexión local de default conserva privilegios administrativos y debe sustituirse por el rol restringido antes de publicar. Inventario: 292 rutas compuestas y 424 modelos.

Bloque anterior: **retirada de `webcitt/` y propiedad real de aplicaciones**, con [mapa vigente](apps/README.md), [arquitectura y actualización](docs/arquitectura.md) y [verificación](docs/extraccion-aplicaciones-2026-10-12.md). Se trasladaron 182 modelos, 259 rutas operativas y 3.406 archivos; se conservaron sus 628 métodos y los SHA-256 de 1.712 binarios. Modelos, administración, comandos, vistas y recursos viven en sus propietarios. Hay 21 manifiestos y 424 modelos del proyecto, incluidos proxies. `apps/historial_modelos` conserva solo migraciones históricas con etiqueta `webcitt`, sin modelos activos; las tablas físicas mantienen sus nombres para preservar identidad y datos. No reintroducir un contenedor general ni borrar el historial.

El corte local está aplicado en ambas bases. Ensayo sobre copias y comparación local de las 339 tablas confirmaron conservación de filas, permisos, restricciones y configuración de capacidades; también se ensayó reversión exacta y segunda actualización. Sin diferencias de modelos ni migraciones pendientes en ningún alias. Suite final: 3.898 pruebas sin fallos (13 omitidas por perfil), 293 con dos bases separadas, 195 JavaScript y 10 de entregas correctas. Auditorías de repositorio, 386 plantillas y 33 señales sin hallazgos. Recorrido real de 1.017 pantallas del administrador: cero fallos, con sesión volátil y SQL de escritura bloqueado. Servidor local reiniciado en `127.0.0.1:8000`; portal, Logística, cursos, galería, Centros I+D, acceso y estáticos HTTP 200; 13 imágenes y 16 scripts revisados sin fallos. No hay despliegue universitario ni certificación general de producción. Evidencia privada en `var/extraccion-apps-20261012/`; consultar git log para el commit publicado.

Bloque anterior: **revisión de la estructura `webcitt`**, con [mapa histórico](docs/historial/estructura-webcitt-2026-10-12.md). El diagnóstico previo a la extracción identificaba 182 modelos heredados, 259 rutas y 11 manifiestos. Sus pendientes de traslado se resolvieron en el bloque vigente. Ruff conserva su caché en `var/cache/ruff/`.

Bloque anterior: **visor móvil en pantalla completa**, con [diagnóstico y verificación](docs/visor-movil-pantalla-completa-2026-10-12.md). Reproducido con CSS real: el iframe se expandía a 561 px en una ventana de 390 px por la columna implícita de la cuadrícula. Columna explícita reducible, contenido acotado, espacio para controles y altura dinámica corregidos en el visor común; versión del CSS renovada. Cinco tamaños comprobados en Chrome headless al entrar y salir, incluidos cuatro con emulación móvil; evidencia privada en `var/visor-movil-20261012/`. La página real de Logística y el CSS sirven la versión corregida HTTP 200. Django check y diff correctos. Sin cambios de datos ni modelos, sin despliegue universitario. Consultar git log para el commit publicado.

Bloque anterior: **fotos y miniaturas de todas las unidades**, con [diagnóstico y verificación](docs/fotos-miniaturas-verificacion-2026-10-12.md). Los originales estaban intactos; la entrega protegida rechazaba los derivados sin registro. Los enlaces ahora acreditan procedencia firmada y la entrega comprueba los permisos actuales del original. Se reutilizan los JPEG existentes, sin migraciones ni cambios de contenidos. Inventario de 464 referencias ImageField sin originales ausentes; 408 fotos publicadas y 181 miniaturas distintas HTTP 200, incluidos mosaicos, galerías y mapa de las 32 unidades activas. Las páginas reales de Logística generan los nuevos enlaces. Evidencia privada en `var/fotos-miniaturas-20261012/`. Servidor local en 127.0.0.1:8000 con recarga automática; recargar las páginas abiertas para obtener enlaces firmados. No hubo despliegue universitario. Consultar git log para el commit publicado.

Bloque anterior: **organización de aplicaciones activas**, con [informe y recuperación de pruebas](docs/organizacion-aplicaciones-2026-10-12.md). Quedan tres contenedores (PostgreSQL, pasarela y WMS 90 de Logística) y dos volúmenes en uso. Los WMS de prueba 88/89 están desactivados, con visibilidad interna y carpeta exclusiva archivada. ZIP y recursos nativos conservados; dos archivos privados de datos verificados por SHA-256, comparación binaria e integridad SQLite antes de retirar exactamente sus contenedores, volúmenes, imágenes y redes. PostgreSQL y WMS 90 sin reinicio; enlace y conteos del WMS conservados. Recurso 90 renombrado «WMS: gestión de almacenes» y descrito. Por defecto guardar ZIP ya no encola despliegues: `MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=false`, solicitud manual disponible. Recursos o carpetas desactivados, incluidos ancestros, bloquean despliegue y enlace antiguo. 31 pruebas del módulo en PostgreSQL QA efímero aislado y nueve focales posteriores aprobadas; Ruff, check, migraciones y 138 huellas documentales correctos. Conteos 32/3/186/21 conservados; pruebas públicas 404 y WMS operativo HTTP 200. Copias históricas anteriores intactas; no se desplegó en la universidad. Consultar git log para el commit publicado.

Bloque anterior: **limpieza local e integridad de bases**, con [informe y arranque sin respaldos periódicos](docs/limpieza-desarrollo-bases-2026-10-12.md). Se retiraron seis bases QA inactivas, 18 volúmenes históricos desconectados tras la autorización expresa y verificación de 17 copias privadas, y el cliente periódico local de respaldo con dos volúmenes exclusivos vacíos. Quedan cinco contenedores y cuatro volúmenes, todos en uso. Las copias autorizadas se conservan fuera de Git con SHA-256 y ACL privada. Un servidor PostgreSQL conserva `citt_db` (32 unidades, 186 recursos y 21 cursos) y `citt_centros_id` (3 centros); no se crea una base por entidad. Comprobadas 769 relaciones FK sin huérfanos ni índices inválidos y 138 documentos sin fallos ni huellas ausentes tras normalizar tres metadatos heredados con auditoría. Historial de migraciones Centros sincronizado para 0328/0329 sin tablas de otros dominios; ambos aliases sin pendientes ni cambios de modelos. Doce pruebas multibase correctas. PostgreSQL saludable y tres WMS HTTP 200. `docker-compose.desarrollo.yml` independiente reutiliza el volumen externo existente y no inicia respaldos; producción conserva sus procedimientos. No se recrearon contenedores operativos ni se desplegó al servidor universitario; publicación antigua de 5433 y cierre de producción siguen pendientes. Consultar git log para el commit publicado.

Bloque anterior: **estructura de bases y limpieza del contenedor sin asignar**, con [guía de topología y actualización](docs/estructura-bases-datos-docker.md). Se estableció un servidor compartido y dos bases por dominio, con alternativa Compose compartida o dedicada para Centros. Servidor renombrado sin reiniciar; PostgreSQL sin asignar y su volumen vacío retirados. Los 18 volúmenes históricos y seis bases QA que quedaron pendientes entonces fueron tratados en el bloque vigente.

Bloque anterior: **nombres descriptivos de Docker**, con [mapa y reglas de identidad](docs/nombres-contenedores-docker.md). Siete contenedores locales renombrados sin recrearlos: WMS por aplicación/unidad, pasarela, base, respaldos y PostgreSQL detenido sin asignación. Tres WMS HTTP 200, PostgreSQL saludable, procesos/volúmenes/IP/puertos conservados. Alias estables añadidos a WMS existentes; nuevos despliegues los declaran y encuentran la aplicación por etiqueta al cambiar su título. Compose define nombres descriptivos para todos sus servicios, incluidos Centros, y fija el proyecto histórico `citt` para conservar identidad de almacenamiento. Cuarenta pruebas Django de despliegue/navegador en PostgreSQL aislado y configuraciones Compose base/combinada correctas. No hubo migraciones ni recreación de servicios operativos. Consultar git log para el commit de este bloque.

Bloque anterior: **almacenamiento, Docker y entrega del código**, con [inventario y procedimiento](docs/almacenamiento-entrega-servidor-2026-10-12.md). Código versionado inicial 323,54 MB frente a 11,11 GB locales legibles. Retirados 53 perfiles exclusivos de QA (1.982.116.739 bytes), conservando evidencias, medios, respaldos y bases; Docker liberó unos 281 MB de caché antigua sin detener servicios. Trece directorios protegidos impiden certificar el total completo. Se ampliaron exclusiones, Dockerfile copia raíces explícitas, web/migraciones/tareas comparten imagen, Compose limita logs y evita volúmenes PGDATA anónimos de clientes de respaldo. Centros conserva almacenamiento separado. Nuevas herramientas de inventario y entrega con manifiesto/SHA-256, archivos LFS reales y diez pruebas incluidas en CI. Compose base/combinado, Ruff, Django check y runner temporal verificados. Configuración operativa antigua no recreada: PostgreSQL local aún expuesto en 5433 y volumen de respaldo antiguo vacío; completar roles/restauración/infraestructura antes de producción. No se borraron adjuntos históricos ni volúmenes. Consultar git log para el commit de este bloque.

Proyecto Django SLCID, rama reestructura-modular, repositorio COMPUMAX-EC/CITT.
La auditoría, separación y reportes se publicaron en origin/reestructura-modular
con el commit 3c58f40a (consultar git log). Las mejoras posteriores del catálogo de
formación, simulación logística y prácticas se incluyen en el punto de control
solicitado el 12 de octubre; consultar git log y los informes siguientes.
No se ha desplegado al servidor universitario. El 11 de octubre se aplicaron
las migraciones compatibles y se activó localmente la base propia de Centros I+D
tras respaldo, ensayo y copia verificada.

## Publicación de avances

Usar `main` y `origin` → `https://github.com/Luisknt07/SILAB-CID.git`.
Antes de publicar revisar `git status` y confirmar que datos y credenciales
siguen ignorados. Las publicaciones en COMPUMAX-EC/CITT mencionadas en las
entradas posteriores describen el historial anterior a este traslado.
Publicar código no despliega ni copia bases al servidor universitario.

## Lectura inicial

Último bloque trabajado: **visor del catálogo de cursos**; consultar el [diagnóstico y verificación del 12 de octubre](docs/visor-cursos-verificacion-2026-10-12.md). Con el código actual el catálogo carga en Chrome; el bloqueo original no se reprodujo. Se corrigió el marcado de categorías por consulta y se añadió recuperación para marcos nativos bloqueados o que no terminan de cargar; los eventos obsoletos no pisan una nueva selección. Versión del script actualizada. Nueve comprobaciones de navegador, 100 pruebas Django y 195 JavaScript correctas. Se corrigió también la detección de títulos con tildes/mayúsculas bajo colación C en dos precargas: normalización Unicode y lectura acotada de PK/nombre, preservando datos manuales. Sin cambios de permisos, contenidos académicos ni migraciones. Instancia PostgreSQL QA retirada; servidor QA detenido. Se dejó iniciado el servidor local normal en 127.0.0.1:8000 con recarga automática; catálogo 200/SAMEORIGIN. Si otra instancia conserva el fallo, reiniciar su proceso Django y recargar el cliente antes de contrastar su respuesta HTTP concreta.

Bloque anterior: **contenidos completos de las seis pestañas de logística**; consultar el [informe de cobertura y publicación](docs/contenidos-logistica-cobertura-2026-10-12.md). Carga local respaldada: 59 recursos nuevos en 27 carpetas, doce prácticas para las 23 asignaturas y siete programas con 21 módulos, 112 lecciones y 84 preguntas. Quedan 45 carpetas públicas sin vacíos; los programas tienen presentación publicada y ediciones inactivas sin fechas, cupos ni certificación. Odoo recibió 40 correcciones conservando siete valores manuales. Integridad comprobada de 73 modelos y 538 registros operativos. 778 pruebas Django distintas y 187 JavaScript aprobadas; 95 focales repetidas al cierre. Antivirus de 77 adjuntos y 28 archivos del aula sin amenazas; 21 PDF revisados. Sin migraciones; la instancia QA propia fue detenida y retirada, conservando evidencias. La publicación en Git no despliega la carga local de contenidos al servidor universitario: aplicar allí sólo con respaldo y revisión antivirus nueva. Operación presencial, aceptación gráfica real y carga universitaria siguen pendientes.

Bloque anterior: **paso 4, seguimiento y ensayo técnico de operación logística**; consultar el [informe del 12 de octubre](docs/logistica-paso4-ensayo-2026-10-12.md). Se añadió selección de expediente, próxima acción y evidencias agregadas; se comprueban recursos al aprobar/iniciar y guía aprobada al ejecutar. Correcciones de FT03 cerrada conservan datos operativos y revalidan permisos. 680 pruebas Django y 187 JavaScript aprobadas; 23 focales repetidas tras ampliar comprobaciones. Sin nuevas migraciones ni cambios en datos operativos; QA PostgreSQL propio retirado. Pendientes: ensayo físico con inventario/aforo/responsables confirmados, inspección gráfica GPU/móvil y carga/despliegue universitario. El paso 3 conserva su [revisión anterior](docs/centro-distribucion-practica-2026-10-11.md).

Implementación previa conservada: [Preparación presencial y expediente de prácticas de logística](docs/logistica-operacion-presencial-2026-10-11.md).
Base docente: [Centro de distribución: práctica guiada y comparación reproducible](docs/centro-distribucion-practica-2026-10-11.md).
Base técnica anterior: [Simulación logística: multijugador y operaciones 3D](docs/simuladores-logistica-2026-10-11.md).
Antecedente: [Laboratorio de Logística, paso1 implementado](docs/avance-logistica-paso1-2026-10-11.md).
El [catálogo de cursos, capacitaciones y eventos](docs/catalogo-formacion-2026-10-11.md) conserva su cierre anterior.
Conserva como antecedente la [verificación de gestión y reportes](docs/gestion-reportes-verificacion-2026-10-11.md).

1. [Auditoría integral vigente](docs/auditoria-integral-produccion-2026-10-10.md),
   incluidos sus tres informes de detalle y condiciones de publicación.
2. [Despliegue Linux](docs/produccion-linux.md).
3. [Índice documental](docs/indice.md).
4. [Historial detallado](docs/historial/TRASPASO-CODEX.md), especialmente entradas 217–223.

## Seguimiento y ensayo técnico del bloque 4 del 12 de octubre

- Expediente seleccionado por actividad, con hasta cinco sesiones recientes, tres guías y acceso directo a la publicada; sesión histórica seleccionable fuera de la ventana. Próxima acción, estados de reserva/FT02/FT03 y conteos de evidencias. Sin JSON pesado, archivos privados o partidas/eventos en el resumen.
- Aprobación e inicio comparten elegibilidad actual y agenda. El inicio detecta cambios posteriores de equipos, espacios y software; selección corrupta responde 409 sin efectos. No se activa la política opcional de verificación de existencia. Guía completa en revisión puede reservar turno, pero no iniciar ni completar.
- FT03 cerrado conserva campos operativos, snapshot y resumen exactos, asistencia y consumos; admite documentación y evidencias. Snapshot vacío no se reconstruye, responsables históricos inactivos no bloquean aclaraciones. Permiso de escritura se relee bajo locks. Exportación XLSX sin N+1 de ejecuciones o responsables.
- 680/680 Django en 54 módulos, 187/187 JavaScript y 23/23 focales posteriores aprobados. Ruff, Django check, ausencia de nuevas migraciones y diff correctos. Evidencia privada: var/logistica-paso4-ensayo-20261012. No se modificaron bases operativas ni se desplegó.
- El ensayo es técnico, con fixtures y medios temporales. Pendiente confirmación de maquetas, interfaces, aforo, responsables y seguridad; validación gráfica y carga universitaria. Centros I+D conserva su dominio y base. Después de aceptación presencial, continuar bloque 5 con transporte/capacidad/ventanas; las doce prácticas de la ruta son totales.

## Preparación presencial de logística del 11 de octubre

- Página privada logistica/operacion con recursos y capacidad según delegación, seis etapas, selección de actividad paginada a 12, últimas tres guías y cinco planes. No crea estadísticas físicas ni consulta partidas/eventos. Recursos principales y asociados M2M se cuentan una sola vez; disponible sin existencia verificada no se presenta como comprobado.
- Adaptación completa al editor institucional FT04 desde plantilla=logistica-cd. GET no crea registros; guardado normal genera actividad y guía privadas pendientes de revisión. Contenido editable, semilla y versiones conservadas en procedencia_simulacion; metadata de cliente ignorada y procedencia preservada al reeditar. Precarga exclusiva de reserva no se etiqueta como CD.
- Correcciones: plan sin actividad ya no produce500; nueva versión conserva requiere_guia y tema del sílabo; ejecución en revisión/validada no se sobrescribe; locks Unidad→Reserva→Plan→Ejecución. Validación FT03 posterior al cierre atendido conserva reserva, asistencia y consumos y no repite avisos. Lista de prácticas sin N+1 de ejecuciones ni JSON pesado.
- Delegado con solo seguridad accede a su módulo, con aislamiento y sin cargas de otros módulos; enlace agenda acepta permiso agenda o reservas. Enlace de ejecución exige reserva vinculada. Guía aprobada anterior se reconoce aunque tres borradores posteriores ocupen el resumen.
- No hay equipos con existencia verificada ni aforo general o requisitos de acceso configurados en la unidad local. No tiene actividades/guías/planes/ejecuciones institucionales; única reserva vencida. No habilitar operación física por la existencia de este panel. Responsables, espacios y software catalogados necesitan revisión de disponibilidad y alcance.
- Verificación: 531 pruebas integradas y 71 de cierre focal aprobadas; el cierre incorpora una adicional, para 532 distintas. También 184 pruebas JavaScript, Ruff, Django check, ausencia de nuevas migraciones y revisión de diferencias. Las 32 vistas locales respondieron HTTP 200 con cuatro a catorce consultas, sin escrituras ni consultas a partidas/eventos. Conteos operativos conservados y base QA propia retirada. Inspección gráfica y carga universitaria pendientes. No hay commit, push ni despliegue; consultar evidencia en el informe.

## Centro de distribución: práctica guiada del 11 de octubre

- Motor independiente con tres variantes: normal, pico y falla de montacargas. Inspección, rechazo parcial, recepción, ubicación ABC con capacidad, picking FIFO, embalaje, despacho, balance por SKU y OTIF sobre todos los pedidos. Motor/caso/dataset/guía 1.0.0; máximo 240 decisiones.
- Guía completa vinculada a las asignaturas existentes, datasets y diccionario, hipótesis, comparación por pares, entregables y rúbrica docente separada del puntaje. Comparador privado de dos a tres resultados compatibles, gráficos, CSV/JSON y cuaderno descargable; las notas no se guardan en servidor.
- Entrada en Recursos de aprendizaje y simuladores: Centro de distribución: práctica guiada. Ruta /laboratorio/laboratorio-logistica-comercio-internacional/logistica/distribucion/. API de operaciones conserva los seis casos anteriores y las partidas históricas. La semilla se conserva al cambiar de variante.
- 312/312 pruebas Django y 184/184 JavaScript aprobadas, más repetición focal de 23 vistas/navegación. Ruff general, Django check, ausencia de nuevas migraciones y git diff --check correctos. 26 rutas públicas HTTP 200, de cuatro a siete consultas por respuesta y cero escrituras; sin consultas de partidas en vistas públicas.
- Sin nuevas migraciones, precarga de partidas o cambios en datos operativos. Base QA propia retirada con comprobante; Centros I+D conserva su dominio y base. Sin commit, push ni despliegue.
- Pendiente: inspección visual real con GPU/móvil, carga universitaria, calibración y operación presencial. No instalar ni anunciar AR/VR, física industrial, maquetas conectadas o un LLM por esta entrega. Reglas y guía están versionadas en código; aún no tienen editor administrativo propio.
- Continuidad: bloque 4 del plan, vincular actividad reservable, inducción, guía aprobada, planificación, ejecución, evidencias, incidencias y reportes con recursos/responsables/aforo verificados. La simulación no registra uso físico.

## Simulación logística: ampliación del 11 de octubre

- Beer Game multijugador con cuatro roles, facilitador, vacantes automáticas, códigos de sala, decisiones privadas y semanas atómicas. Se conserva el individual anterior.
- Seis casos operativos con WebGL propio: almacén, puerto, fábrica, transporte, AMR/dron y pronóstico temporal. Mis partidas, bitácora, KPIs, rúbrica, evidencia y verificación del servidor.
- Persistencia separada de los parámetros de plantas piloto: tres modelos y migraciones 0328/0329 aplicadas localmente tras respaldo. 56 conteos/huellas previos preservados, incluida la base de Centros I+D.
- 243 pruebas Django y 153 Node aprobadas, incluyendo concurrencia real PostgreSQL. Ruff/check/makemigrations correctos. Ocho páginas locales HTTP 200, siete consultas cada una, sin partidas demo operativas.
- Pendiente: inspección gráfica real y móvil, carga en infraestructura universitaria, XR inmersivo, física industrial y conexión/calibración de maquetas. No están instalados Gazebo/PX4 ni un LLM.
- Motor/versiones/casos y guía docente: consultar el informe enlazado. Partidas históricas conservan vistas y evidencia; no se reinterpretan con otro motor.
- Sin commit, push ni despliegue de esta ampliación.

## Logística: paso 1 del 11 de octubre

Se publicó localmente una portada nativa con SVG animado, mapa de seis áreas,
matriz paginada basada en 23 asignaturas y tres carreras, seis fichas metodológicas
y 30 recursos (18 documentos propios y doce fuentes primarias). Investigación
formativa se activó para contenidos metodológicos sin inventar proyectos o convenios.
El juego propio de la cerveza incorpora cuatro eslabones, retardos, tres escenarios,
indicadores, gráficos y exportación/reproducción JSON/CSV. Es individual y local al
navegador; no persiste partidas institucionales ni controla maquetas.

La publicación preparar_logistica_paso1 es idempotente y conserva edición manual;
--simular sólo SELECT, --aplicar exige manifiesto de revisión y crea respaldo.
Se verificaron respaldos PostgreSQL/JSON y escaneo limpio de los 18 HTML.
Permanecen idénticos los 23 registros académicos, 131 equipos, 26 programas, nueve
cursos y 159 elementos anteriores de fichas. Los recursos administrativos y ABE
mal titulados se reclasificaron como internos sin borrar archivos o enlaces.

La portada respeta módulos/secciones ocultos y no consulta sus tablas. Las rutas
son diferidas y los enlaces directos evitan descargar la portada inicial.
Se corrigió cierre/reapertura de archivos al calcular metadatos. El árbol público
pasó de consultas por recurso a precargas compartidas, con la misma autorización:
la ficha local bajó de 213 a 82 consultas; el árbol usa cuatro tanto con uno como
con 30 recursos. Cierre focalizado ampliado: 296/296 Django y 104/104 JavaScript, Ruff general,
check, ausencia de migraciones pendientes y 28 páginas HTTP 200. Base QA propia
retirada con propietario y cero conexiones; el informe registra límites.
No hay despliegue al servidor universitario ni inspección visual interactiva;
la disponibilidad física de maquetas y equipos sigue requiriendo verificación.

## Catálogo de formación del 11 de octubre

El menú usa catálogo y categorías sin enumerar todos los cursos. El catálogo y
la administración paginan 12 ofertas; el catálogo de reservas pagina seis y el
seguimiento 25 participantes. Los externos muestran organizador, participación
y enlace público validado; no abren aulas, matrícula, pagos ni certificados locales.
Activar/desactivar conserva historial; eliminar exige código y ausencia de
participantes, invitaciones o evidencias. Se corrigieron altas simultáneas con
desactivación y se añadieron índices de listado. Centros consume DTO con seis
fichas por unidad y enlace al catálogo completo, manteniendo bases separadas.

Migración aditiva 0327 aplicada localmente en ambos alias, con respaldos previos
y huella anterior conservada. Se añadieron siete propuestas editoriales en
Logística, Transporte y Cadena de Suministro, todas borradores, sin fechas ni
alianzas confirmadas y sin cohortes o matrículas. El comando repetible conserva
las ediciones manuales; --simular sólo consulta. Hay 14 cursos y siete ediciones
locales. No desplegado al servidor universitario ni publicado este cambio en Git.
El [informe del catálogo](docs/catalogo-formacion-2026-10-11.md) registra las
comprobaciones de este cierre y sus límites.

Cierre: 3.365 casos generales, 3.349 aprobados y 16 reservados para multibase;
356/356 duales, 72/72 JavaScript, 380 plantillas y controles estrictos aprobados.
Las 2.041 fuentes finales conservaron su huella. Ocho bases QA propias retiradas
con propietario y cero conexiones. Sin navegador habilitado para inspección
interactiva; no confundir el cierre local con despliegue universitario.

## Gestión y reportes del 11 de octubre

La gestión carga consultas, históricos y formularios de la sección solicitada.
Observatorios paginan a 25 y consultan su sección activa. Inventario,
mantenimiento, personal y configuración inicializan operaciones aunque no
exista formulario de reservas. La navegación conserva la última selección ante
respuestas fuera de orden. No volver a preparar todas las pestañas al abrir el
panel ni reintroducir la dependencia de reservas para operaciones generales.
La búsqueda de cuentas de responsables es por demanda, autorizada por unidad.

Formación integra catálogo, ediciones, inscripciones y certificados en los
reportes por unidad y macro, con PDF, Word y Excel. No confundir inscripciones
con personas únicas ni reservas confirmadas con atenciones ejecutadas. Los
participantes de cursos tienen exportación privada Word/Excel. El exportador
común apps/core/reportes.py no importa ORM ni el dominio heredado; cada dominio
entrega contenido autorizado y el adaptador institucional conserva la marca UPEC.

Centros I+D tiene reportes propios con 17 categorías sobre 42 modelos, alcance
macro institucional y por centro asignado. Conserva base y consultas propias;
no mezclar sus tablas con la gestión de unidades ni conceder acceso por staff.
Consultar [cobertura y extensión](docs/reportes-centros-id-cobertura.md).

Medición final en solo lectura: 59 perfiles, 32 unidades, mediana de consultas
583 a 67, HTML 1.779.223 a 20.356 bytes y render local 1.192,96 a 129,85 ms.
No mide red ni concurrencia del servidor universitario. Los estáticos comunes
siguen compartidos y cacheables; la selección aplica a datos, formularios y HTML.

Primer cierre: regresión general 3.190 casos sin fallos, 13 reservados para dos bases;
Centros dual 279 sin omisiones y revisión posterior dirigida 36. JavaScript
57 aprobadas; 73 scripts sin errores de sintaxis. Recorridos reales de lectura:
1.003 pantallas administrativas, 152 de gestión y 68 respuestas de reportes de
Centros. Cierre HTTP 9/9. Check, Ruff, contratos, 378 plantillas e inventario
estricto de 3.937 archivos aprobados. Sin nuevas migraciones en esta revisión.
Cinco bases QA propias retiradas tras comprobar propietario y cero conexiones.
No sumar pruebas solapadas ni afirmar una inspección interactiva del navegador:
no hubo navegador habilitado; sí se inspeccionaron muestras PDF.

Evidencia privada en var/auditoria-gestion-reportes-20261011/ y carpetas
referidas por el informe. Cambios locales, sin despliegue. Permanecen las
condiciones universitarias de producción del informe de separación vigente.

### Segunda revisión y cierre previo

Regresión final de continuidad: 3.200 casos en 384,863 segundos, 3.187 aprobados,
13 reservados para dos bases y cero fallos. Comprobaciones dirigidas duales:
39 de Centros/seguridad/infraestructura y 99 de reportes y documentos, sin
omisiones; son conjuntos solapados. Gestión: 20 dirigidas. JavaScript: 60
aprobadas; 74 archivos JS/CJS con sintaxis válida, incluidos tests. Inventario
vigente: 3.938 archivos. Pasan check, Ruff, 378 plantillas, contratos modulares
y 33 contratos de señales. Ambas bases tienen cero migraciones pendientes.

Corregidos: búsqueda sin coincidencias de centro seleccionado que devolvía
500; Editar→Nuevo sin restaurar campos obligatorios; cambio de responsable con
valores sugeridos anteriores; semanas inválidas/extremas; diferencia entre
asistencia prevista y real en macro/unidad; ausencia de aviso al superar 500
filas; JSON/horarios históricos inválidos; demostraciones en reportes operativos.
Preservar Reserva.es_efectiva como propiedad canónica; su protección de tipo se
revisó y actualizó en la huella de contratos, sin alterar señales ni esquema.
No acreditar atenciones con datos de ejecución inválidos. Los scripts de gestión
y responsables tienen versiones nuevas para invalidar la caché.

En lectura real, 68 respuestas de Centros con centro seleccionado y búsqueda
vacía fueron correctas. El macro de 32 unidades mantiene 12 consultas centrales
y cero a Centros: 302,30 ms primera petición y 16,38 ms siguiente, solo datos
locales sin render/red/concurrencia. Las 2.023 fuentes verificadas conservaron
su huella durante la regresión. QA propias retiradas con propietario y cero
conexiones; no se escribieron datos operativos en estos recorridos.

Los reportes detallados de reservas y las etiquetas temporales señalados en ese
cierre fueron atendidos en la tercera revisión. Continúan la inspección interactiva
de navegador no disponible aquí y las validaciones del servidor universitario. El rol central elevado de desarrollo
sigue sin ser apto para producción. La configuración endurecida sintética pasó
los controles sin SQL; no equivale a validar dominio, TLS, correo ni carga reales.
Evidencia privada: var/revision-continuidad-20261011/ y carpetas dirigidas citadas
en el [informe vigente](docs/gestion-reportes-verificacion-2026-10-11.md).

### Tercera revisión y cierre vigente

Regresión definitiva: 3.302 casos en 399,505 segundos, 3.289 aprobados y
13 reservados para dos bases; cero fallos. Dual física: 315/315 en 94,373 segundos,
sin omisiones y con hashers estándar. General usa MD5 exclusivamente en QA y
medios temporales aislados. No sumar conjuntos solapados. JavaScript 70/70;
76 scripts válidos; 379 plantillas, Ruff, check, contratos modulares y 33 señales
aprobados. Inventario 3.956 archivos, cero huérfanos/colisiones, seis copias
intencionales. Las 2.051 fuentes conservaron SHA-256 durante la regresión.

La general anterior detectó un empate de mantenimiento dependiente del plan SQL.
A igual fecha programada prevalece ahora el mayor PK; prueba directa y 51 casos
dirigidos en dos bases aprobados antes de repetir la general completa. Conservar
esa regla estable: no volver a ordenar únicamente por fecha. El intento fallido
queda en integral-empate-fallido.log, separado del cierre verde.

Lectura real: 1.003 pantallas administrativas, 152 de gestión, 544 combinaciones
de filtros extremos de Centros y ocho comprobaciones HTTP correctas. El macro
de 32 unidades mantiene 12 SQL principales y cero en Centros: 314,14/18,73 ms,
sólo construcción local de datos. Ocho QA propias retiradas con dueño y cero
conexiones comprobados; recibo y cierre integrado en
var/auditoria-optimizacion-20261011/. Las 43 dependencias son compatibles;
no se consultaron nuevas vulnerabilidades publicadas.

Catálogos de equipos/espacios/software/insumos paginan 50 en SQL y mantienen
búsqueda, modo, filtros y retorno. Selectores remotos por unidad/centro validan
el alcance completo del POST y bloquean guardar si la hidratación está incompleta.
No reintroducir querysets completos en el HTML ni vaciar relaciones si falta JS.
La nueva ruta privada de búsqueda conserva la carga diferida; ahora hay 250
callbacks heredados, incluyendo la búsqueda nueva y las rutas históricas.

Los reportes conservan detalle limitado, totales completos y notas temporales;
no sumar conjuntos dirigidos solapados. Con 20.000 reservas el pico Python de
unidad bajó 190,06→2,92 MB y administrativo 237,69→6,66 MB. Trazabilidad de 40 consumos
bajó 81→máximo 3 SQL. No conformidades ligadas a controles demostrativos se excluyen
sin borrar registros docentes. Mantener denominadores/fechas explícitos.

Originales de imágenes y entregas sólo se eliminan físicamente después de commit;
el modo simulado conserva los archivos. Las fotos privadas exigen alcance y
permisos. Identificadores HTTP extremos se rechazan antes del ORM en los flujos
corregidos. No sustituir estos controles por isdigit() seguido de int/filtroSQL.

Inscritos: GET del listado no genera certificados. La acción académica usa POST
con CSRF, alcance y servicio idempotente; completar una actividad y descargar el
certificado propio conservan sus flujos legítimos. Reutilizar relaciones precargadas:
1→51 inscritos mantiene 16 SQL, antes 18→118. El HTML e historiales de la cohorte aún
crecen; falta paginación y agregaciones equivalentes antes de validar grupos masivos.
Syllabus mantiene 9 SQL al crecer de 1 a 121 asignaturas y 1 SQL al crecer de 1 a 121 sesiones pendientes de la
muestra. Mantenimiento recorre el histórico por bloques; 5.000 órdenes pasaron de
21,66 a 0,48 MB Python para filas. Activos, planes y pendientes siguen completos.

Conexiones operativas en solo lectura; QA propias retiradas tras verificar dueño
y cero conexiones. Sin migraciones nuevas en esta iteración ni despliegue.
El rol web central debe restringirse para producción. Faltan navegador interactivo,
servidor universitario/TLS/correo/restauración/carga concurrente; no afirmar
capacidad universal ni ausencia absoluta de errores. Consultar alcance, métricas
y evidencia en el [informe vigente](docs/gestion-reportes-verificacion-2026-10-11.md).

## Arquitectura y datos

Monolito modular: apps contiene verticales y capas extraídas; config configura
entornos y módulos; webcitt conserva tablas y migraciones históricas, además de
adaptadores compartidos. Centros I+D sí tiene modelos, migraciones, formularios,
servicios y gestión propios en apps/centros_id. No asumir la estructura de
septiembre en los informes históricos como descripción actual.

Laboratorios, plantas piloto, centros experimentales y observatorios reutilizan
la ficha y la operación de Unidad. Centros I+D tiene ficha propia compacta,
pestañas separadas como Laboratorios y gestión dinámica en modal. El visualizador
compartido de las demás unidades incluye copiar enlace a la sección, con
restauración de pestaña/recurso. Preservar rutas y contratos existentes.

Los datos generados viven en var y no se versionan. No borrar archivos por
parecer duplicados sin comprobar consumidores y referencias de base de datos:
la auditoría identifica cuatro pares de imágenes usados como alias.

## Auditoría integral del 10 de octubre

Las 249 rutas heredadas difieren sus controladores; presentación, catálogo,
niveles, calendario y avisos consultan únicamente cuando se usan en la petición.
La portada de Centros I+D pasó de 51 a 10 consultas locales; Servicios y Normativa,
de 12 a 3. Los aforos agrupan conteos por edición. No hay caché global de permisos.
Los estáticos usan STORAGES vigente con WhiteNoise comprimido.

`cargar_centros_id --conservar-existentes` crea faltantes sin sustituir decisiones
editoriales, vacíos, estados o archivos existentes. No ejecutar cargas al arrancar
ni borrar migraciones históricas. Los índices concurrentes centros_id.0015 y
webcitt.0326 están aplicados localmente después de respaldo.

Centros I+D opera localmente con el alias centros: 42 modelos, 49 tablas y
857 registros copiados, con digests coincidentes y 92 FK internas. La base
principal conserva las tablas previas selladas en solo lectura. CuentaCentro
proyecta identidades utilizadas sin credenciales; la autoridad sigue en auth
central. El runtime de Centros es restringido y su propietario de migración
está separado. El rol elevado de desarrollo de default sigue siendo inválido
para web en producción. El proceso y los archivos continúan compartidos.
[Estado y verificación del corte](docs/separacion-centros-verificacion-2026-10-11.md)
y [procedimiento operativo](docs/separacion-centros-operacion.md).
La auditoría detalla credenciales centrales, carga y monitoreo pendientes. La comparación con LabXchange define próximos simuladores por dominio;
no afirma que esos candidatos estén ya implementados.

La regresión integral del 10 de octubre aprobó 3.025 pruebas PostgreSQL (613,584 s, cuatro
trabajadores; MD5 únicamente en ese proceso QA y medios temporales). También
aprobaron 34 pruebas dirigidas con hashers habituales. El informe vigente separa
las verificaciones posteriores de portada, Docker y salud interna: 86 pruebas
dirigidas con hashers habituales y 27 pruebas Node aprobadas (con solapamiento).
Al cierre se retiraron las cinco bases QA propias tras comprobar propiedad y
ausencia de conexiones; se conservaron los logs y los datos operativos.

La portada difiere doce de trece fotografías: 24,29 MB a 1,61 MB iniciales de
archivos locales. El contexto Docker excluye entornos anidados y datos privados;
la regla se verificó con BuildKit sobre una fixture sintética. La supervisión
interna distingue proceso y SQL, con bloqueo público en el ejemplo Nginx.
La [validación continua](.github/workflows/ci.yml) usa PostgreSQL efímero y controles
automáticos; su primera ejecución remota queda pendiente de subir los cambios.

## Verificación de separación del 11 de octubre

La nueva regresión general: 3.120 casos, OK, con 13 reservados para el entorno
dual. En dos PostgreSQL reales: 258 casos, OK, sin omisiones. No sumar conjuntos
solapados. La general usó MD5 solo en QA; la dual conservó hashers normales.
Después del corte se comprobaron migraciones completas, esquema exclusivo,
permisos runtime, protección del archivo origen y respuestas HTTP del servidor
reiniciado. Inicio/Servicios/Normativa/Unidades no consultan la base Centros.
Se restauraron y compararon ambas bases en QA; los 54.521 archivos del respaldo
se validaron por SHA-256 y se restauraron todos los archivos de Centros y marca
con una muestra adicional por formato. Una focal externa dual aprobó 119 casos.
El servidor local quedó con recarga automática.
Evidencias privadas: var/separacion-centros-20261011/.

## Logística docente actualizada

Se actualizó localmente el nombre a «Laboratorio de Logística, Transporte y
Cadena de Suministro», con «Smart Logistics Lab» como nombre corto. Las seis
áreas quedan como almacenamiento e intralogística, planificación de cadena,
transporte y movilidad, logística de producción, logística internacional y
tecnologías aplicadas y simulación. Se conserva el slug histórico y los códigos
LOG; también los identificadores, inventario, reservas, software y responsables.
La presentación y las referencias de las asignaturas usan el nuevo enfoque.
El curso introductorio de aplicaciones logísticas con IA se incorporó en la etapa siguiente descrita abajo. El laboratorio independiente de Comercio queda pendiente.

La fuente compartida es webcitt/management/laboratorios/logistica_docente.py.
Para otra base que ya tenga sus seis áreas: ejecutar primero
`python manage.py actualizar_logistica_docente --simular`, y después
`python manage.py actualizar_logistica_docente`. La orden respalda los registros
que actualiza en var/backups antes de escribir y no ejecuta la reforma global.
La carga local dejó el respaldo logistica-docente-20261008T164628083398.json.
Pasaron 14 pruebas relacionadas y check; la ficha y sus seis áreas devolvieron
HTTP 200 con los nombres nuevos. Se verificó que la operación no cambió y que
una segunda simulación no encuentra cambios.

## Curso de aplicaciones logísticas con IA

Ficha publicada localmente: «Desarrollo de Aplicaciones Logísticas con Inteligencia
Artificial», LOG-CUR-002, en Logística. URL:
/laboratorio/laboratorio-logistica-comercio-internacional/cursos/LOG-CUR-002/.
Usa el aula existente: cinco unidades de 480 minutos (40 horas), 39 lecciones,
37 obligatorias y dos ampliaciones opcionales. Incluye 10 lecturas, bienvenida
propia, siete videos externos, cinco PDF, ZIP práctico, cuatro referencias,
cinco cuestionarios de ocho preguntas y seis entregas, incluido el proyecto.
La edición sigue inactiva, sin fechas, instructor, cupos ni costo inventados.
La primera unidad se consulta libremente; la gestión permite revisar todo.
Definir la convocatoria antes de abrir inscripción. La ficha indica costo por
anunciar mientras no exista edición vigente ni precio configurado.

La primera lección es un video propio de 2:49, narración sintética española,
ocho escenas, subtítulos abiertos, pista VTT opcional y transcripción completa.
MP4 versionado de 3.06 MB; se entrega por la ruta protegida de materiales.
No requiere FFmpeg ni voces en el servidor Linux: se carga el archivo terminado.
Los cinco minutos de estudio se descontaron de la primera lectura: no se
ampliaron las 40 horas. No se exige programación previa ni pago de USD 200.
La aplicación funciona sin IA; un asistente conversacional requiere acceso a
un modelo compatible, sujeto a disponibilidad. Existe prueba MCP sin modelo.

Todas las lecciones usan contenido wiki optativo con índice desplegable,
secciones, tablas, pasos, ejemplos, glosarios, avisos y fuentes. Son ocho
ilustraciones originales SVG ampliables con equivalentes PNG para imprimir.
Las lecturas rondan 930–1010 palabras y los laboratorios explican comandos,
resultados y diagnóstico. Hay 68 tablas en el conjunto del aula; los ejemplos
y evidencias no añaden entregas extra. Las cinco guías reúnen las lecturas,
laboratorios y proyecto de su unidad en 48 páginas, sin repetir diagramas
idénticos dentro de cada PDF. Los cursos de texto anteriores mantienen su
renderer; no se habilita HTML arbitrario ni imágenes remotas en el contenido.

Fuentes de contenido:
- aplicaciones_logisticas_ia.py: composición y duración.
- aplicaciones_logisticas_wiki.py: diez lecturas y cinco laboratorios.
- aplicaciones_logisticas_recursos_wiki.py: bienvenida, videos, materiales,
  orientaciones y proyecto; rúbrica 30/25/15/10/10/10, mínimo 70.
- aplicaciones_logisticas_evaluaciones.py: 40 preguntas, tres intentos.
- aplicaciones_logisticas_fuentes.json: atribuciones, enlaces y límites.
- aplicaciones_logisticas_medios/: MP4, guion, transcripción, generación y
  diagramas.py. Los temporales .qa están excluidos de Git.
- domains/unidades/wiki_curso.py y curso_wiki_pdf.py: parser y PDF compartido;
  templatetags/curso_wiki.py y curso_wiki.css: presentación del aula.
- domains/unidades/video_protegido.py: rangos GET para avanzar/retroceder en
  MP4/WebM autorizados, transmisión acotada, HEAD sin cuerpo y fallback completo
  para unidades desconocidas o If-Range; PDF/ZIP mantienen su comportamiento.

Para otra base con la unidad existente: simular y después ejecutar
python manage.py cargar_curso_precargado aplicaciones-logisticas-ia.
La carga nace en borrador, no abre convocatorias y es idempotente. Genera
archivos sólo desde fuentes confiables, nunca durante una simulación.
Sin --reescribir rellena campos vacíos, por lo que no sustituye textos ya
existentes. La actualización local se hizo de forma puntual y respaldada:
38 textos actualizados, una bienvenida nueva, mismas preguntas, IDs anteriores,
avances, entregas y edición. PDF y ZIP se sustituyeron en su ruta existente;
no se crearon alias para los adjuntos anteriores.

Kit versionado en aplicaciones_logisticas_kit/: Django 5.2.17, caso ficticio
Andina Distribución, productos/movimientos/CSV/roles, cinco guías, datos válidos
e inválidos, prompts y plantillas. MCP 2.3.0 opcional, stdio local y dos consultas
de sólo lectura: no hereda los roles de sesión del portal. Exporta todo el
catálogo, no sólo la búsqueda; el historial no incorpora filtros de fecha.
ZIP determinista de 56 archivos; excluye bases, claves y entornos.
SHA256: 6f3e4c3318ca1cf0a22e4ab9618fbe73b18fe6449a0bb57d2b283115be809400.
Sólo README y cinco guías cambiaron para aclarar el reparto de horas.
El código extraído ya pasó 15 pruebas con Python 3.11.9, migraciones, datos y
permisos, y una conexión MCP real por stdio sin cambios en la base. Se recomiendan
Python 3.11/3.12. No se ensayó conversación con un proveedor de IA.

Las sesiones Jhoni Cerón WNjQclnnIWA y TmB8mXKs9jI siguen opcionales en la unidad 4:
149 y 81 minutos, fuera de las 40 horas. Metadatos e inserción comprobados en
YouTube. La transcripción automática estuvo inaccesible; no atribuir temas,
capítulos ni resúmenes no observados. Sus consignas son actividades originales
de observación y contraste. Las entregas requieren revisión docente y los
fallos críticos de saldo o permisos deben corregirse antes de aprobar.

Validación final: 42 pruebas focalizadas aprobadas (20 de composición/carga,
wiki y PDF; 22 de aula y videos protegidos), check sin incidencias y las
39 vistas del aula con HTTP 200. Se revisaron 13 combinaciones de lección/ancho
entre 320 y 1440 px, sin desbordamiento horizontal de página. Las 48 páginas
PDF se renderizaron e inspeccionaron; diagramas, tablas y comandos ajustan al
ancho. El navegador reprodujo el MP4, cargó 37 subtítulos VTT y saltó a 160 s;
se comprobaron también los rangos contra el servidor activo. El navegador
y su perfil temporal se cerraron y retiraron; las capturas siguen en var.

Respaldo de esta mejora: var/backups/curso-ia-antes-wiki-20261008T215526Z.json,
SHA256 fa09919e0c875db7debc10f17270bf66e4c61d8f949687843721fa53c8e67e28.
Se conservaron los adjuntos anteriores en var/qa-curso-wiki/media-antes.
El curso anterior LOG-CUR-001 permanece idéntico:
SHA256 afbd890ee614740cb2520573dc9bad6b20f7104a54105d0ee54f9023718cfcf6.
No se aplicaron migraciones ni se hicieron commit/push durante esta mejora.
Evidencia local ignorada: var/qa-curso-wiki (PDF renderizados, capturas, métricas,
respaldos de archivos y comprobación de las 39 vistas del aula).

## Matrículas, grupos, calificaciones y certificados

La gestión del curso reutiliza EdicionCurso como grupo o convocatoria. Ofrece
crear/editar grupos por período o a medida (organización, fechas, inscripciones,
cupo, horario y lugar) desde el portal. No duplica contenido de estudio.
El administrador puede matricular una persona con correo, nombres completos y
cédula/documento, o una lista CSV UTF-8 de hasta 100 filas / 1 MB. Valida toda la
lista antes de guardar en una transacción. Reserva cupo también para invitaciones
pendientes. No sobrescribe identidades ni reasigna matrículas vinculadas.

Las cuentas externas se registran y verifican el mismo correo usado en la lista;
la matrícula pendiente se vincula al confirmar ese correo. No hay envío automático
de invitaciones desde el formulario. Los conflictos de identidad o documentos
se rechazan antes de guardar y los cupos se comprueban bajo bloqueo del grupo.
El participante elige un grupo explícito al inscribirse. Los enlaces de aula,
pagos, evaluaciones, reportes y certificados conservan su grupo. Salas, asistencia
y grabaciones también se separan con ClaseGrupoCurso; callbacks legacy ambiguos
no acreditan asistencia en varias cohortes.

En Inscritos hay filtros de grupo, nombre/correo/documento, resultado y certificado;
resumen de avance/aprobación, reportes individuales HTML/PDF y acceso al libro de
notas/exportación CSV. El perfil incluye «Mis cursos y certificados» (/mis-cursos/)
con todas las matrículas propias, incluidos históricos retirados o despublicados.
No habilita el aula a quien perdió acceso; conserva su reporte y certificado
vigente. Los reportes se entregan con permisos por objeto y caché privada.

La interfaz usa notas sobre 10 (7 para aprobar por defecto); el almacenamiento
sigue sobre 100 para respetar datos históricos. Nuevas evaluaciones tienen tres
intentos, configurables desde el editor. La migración amplía de 2 a 3 las
configuraciones anteriores de evaluaciones, sin borrar intentos ni recalificar.
Respeta los valores personalizados 1 y mayores de 3 y los umbrales históricos.
Para recalificar una entrega con certificado vigente, la unidad debe anularlo
explícitamente primero. No se anula ni cambia un certificado silenciosamente.

El editor «Diseñar certificado» se abre en modal desde el curso y desde Inscritos.
Incluye dos diseños, títulos/textos con variables permitidas, colores, nota
opcional y hasta dos firmantes con cargo e imagen de firma privada. Debe revisarse
la vista previa PDF antes de guardar; el token se invalida si cambia el diseño.
Al emitir se congelan identidad, texto, institución, logo y firmas. Los PDF
anteriores no se rediseñan al leerlos. La verificación pública no muestra cédula.
Las muestras de QA son ficticias y no emiten certificados reales.

Personalización LOG-CUR-002 (9 de octubre): guardado diseño horizontal sobrio,
verde/dorado, textos específicos del curso de 40 horas y nota sobre 10. Los
firmantes quedan pendientes; la opción usar_firmante_curso permite desactivar
la herencia de una etiqueta genérica de coordinación sin cambiar certificados
previos. La placa verde usa la variante de logo para fondo oscuro. Migración
0317 aplicada localmente tras respaldo verificado
var/backups/antes-personalizar-certificado-20261009-143410.dump
(SHA256 209c98d4142176af226dc16161375a4b935fc9ffd88d6ab48b298da5dd302bb1).
Pasaron 16 pruebas del editor y emisión, incluidas firma pendiente y firma única
secundaria; makemigrations --check sin cambios. Muestra revisada visualmente
en output/pdf/certificado-logistica-ia-vista-previa.pdf, con datos ficticios.
La configuración se guarda en la base de datos; debe conservarse al desplegar.

Pasaron 151 pruebas relacionadas (matrícula, aula, notas, certificados, clases,
contenido wiki y video protegido). Tras serializar también la emisión desde
PDF/reportes, pasaron 23 pruebas focalizadas, incluida una nueva regresión de
matrícula retirada. Check de Django y makemigrations --check
pasaron. Migraciones 0313–0316 aplicadas en la base local después de pg_dump
verificado: var/backups/antes-grupos-cursos-20261009-110047.dump,
SHA256: 1437dbe5325e2d440c9a7f5de73265dd78fe7de4c3bbfc863329be322bc26eca.
La ficha LOG-CUR-002 responde 200 y el historial exige inicio de sesión.
Se revisaron seis pantallas a 320/390/768/1440 px y el modal de certificados
en los cuatro anchos. Se corrigieron formularios, nombres largos de grupos,
contraste y el nombre de sesión móvil; las tablas conservan scroll interno.
No se creó ninguna convocatoria real ni se abrieron las inscripciones del curso.

## Catálogo interdisciplinario incorporado

Se mantiene CIDT-UPEC; CIAB-UPEC amplía su alcance a Agropecuaria, Alimentos y
Biodiversidad y se incorpora CDHT-UPEC, Desarrollo Humano y Territorial. Ambos
se registran como propuestas y tienen contenidos, áreas, líneas, servicios,
articulaciones, relaciones e imágenes conceptuales optimizadas. El CIDT no se
reescribió. Las tarjetas usan cuatro indicadores comunes y el catálogo no tiene
filtros generales; los filtros internos se conservan. Se retiraron también la
navegación local, las tres puertas de entrada y el destacado duplicado. La
portada se concentra en las tarjetas; se retiró el resumen global de actualidad.
La actividad permanece en cada centro. Sus accesos devolvieron HTTP 200 tras los
ajustes de presentación. Las tarjetas tienen una sola acción, alturas iguales
y vista horizontal entre 600 y 1279 px; desde 1280 px incluyen selector de
cuadrícula/horizontal, con horizontal predeterminada y preferencia persistida.
La imagen ocupa el 50 % del ancho en la vista horizontal de escritorio.
En móviles pequeños usan una columna. Se verificaron nueve anchos entre 320 y 1440 px
y se corrigió el desbordamiento de los indicadores generales a 320 px. Se cargaron localmente los dos centros tras respaldar sus datos.
La migración centros_id.0014 cambia etiquetas (SQL no-op) y se aplicó sola.
Las migraciones de seguridad se aplicaron localmente el 9 de octubre junto con
la gestión académica descrita en la siguiente sección, después de verificar un
respaldo completo de PostgreSQL.

Las 182 pruebas de Centros I+D pasaron; también check y la comprobación de
migraciones. Se revisaron tarjetas en escritorio y móvil y doce secciones
públicas por centro nuevo devolvieron HTTP 200. Detalle, comandos y prompts:
[Red interdisciplinaria](docs/centros-id-red-interdisciplinaria-2026-10-08.md).

## Trabajo de seguridad actual

- CORS exacto por entorno, validación estructural de entradas y rate limiting
  atómico en PostgreSQL, complementado por Nginx.
- CSP con nonce por petición y acciones de interfaz sin atributos inline.
- Medios con registro y permisos explícitos; archivos privados y desconocidos
  no se vuelven públicos por conocer su URL.
- Verificación obligatoria de correo respetada por el login y registro propios.
- RLS forzado en seis tablas académicas/personales. No es RLS universal: otras
  tablas conservan autorización por objeto en backend y consultas de cupos.
- Roles separados de migración, web y respaldo. El arranque rechaza privilegios
  excesivos del rol web. Migraciones webcitt 0313 y 0314 verificadas en pruebas y
  aplicadas a la base local el 9 de octubre; el despliegue Linux conserva su
  procedimiento y roles de producción separados.
- OAuthLib/PyJWT actualizados; PDF.js local actualizado; jQuery 3.7.1 y Bootstrap
  JS 4.6.2 compatibles con los modales. Bootstrap 4 sigue fuera de soporte y
  requiere una migración planificada de componentes.

## Estado de validación y despliegue

Los resultados de pruebas y auditorías se mantienen en el informe de producción.
No atribuir pruebas visuales de navegador a los ensayos Node/DOM. El despliegue
previsto es un servidor Linux propio de la universidad, con portal y backend
en el mismo origen. No hay acceso a ese servidor desde esta sesión.

Falta configurar dominio/TLS, SMTP, roles reales, proxy de confianza, ejecutar
migraciones y comprobar respaldo/restauración y navegación HTTPS allí. El .env
estuvo versionado históricamente; los valores locales son distintos, pero TI
debe confirmar la revocación de las credenciales antiguas. No se reescribió Git.

No fusionar main/version2 ni aplicar migraciones a una base activa sin el
procedimiento de respaldo y despliegue correspondiente. Mantener los cambios
ajenos y consultar el estado del repositorio antes de crear commits.

## Cursos dentro de la gestión del laboratorio

La consola de cada unidad autorizada incorpora la pestaña «Cursos», después de
«Prácticas y ejecución». Reutiliza el visor compartido para crear/editar cursos,
grupos, matrículas, calificaciones, contenidos y diseño del certificado.
«Participantes y reportes» reúne avances, notas /10, resultados académicos,
actividades por revisar y certificados, con filtros por curso, grupo, estado
y persona; 25 inscripciones por página y exportaciones completas CSV/PDF.
Los filtros y la subpestaña se conservan al volver de una herramienta.

El módulo es webcitt/domains/unidades/gestion_cursos.py; acceso por permiso
operativo «practicas», siempre limitado a la unidad. El panel y las exportaciones
son privados y no se almacenan en caché. Consultar esta nueva pestaña o exportar
reportes no emite certificados. Se conservan los flujos académicos existentes.
No requiere migración ni carga adicional de datos.

Validación: 133 pruebas de panel/permisos/grupos/matrículas/formación y una pasada
final de 23 pruebas de panel/certificados; revisión visual a 320, 390, 768 y
1440 px, apertura de grupos en el visor, filtros y retorno
y PDF institucional horizontal. Las muestras en var/qa-panel-cursos usan datos
ficticios en test_citt_db con rollback verificado y cero certificados emitidos.

## Editor completo del curso desde gestión y aula

La acción «Editar curso» de Gestión del laboratorio → Cursos abre un editor
privado dentro del visor compartido. La ficha y el aula ofrecen «Editar curso
completo» con el mismo editor en modal. No redirige al administrador de Django.
La nueva ruta es /laboratorio/<slug>/cursos/<codigo>/editar/; requiere permiso
operativo practicas de la unidad y envía Cache-Control private, no-store.

El editor reúne cinco apartados: datos del curso; programa y contenidos;
evaluaciones y proyecto; grupos y participantes; y certificado. Muestra también
lecciones sin publicar y módulos vacíos. Reutiliza los formularios y validaciones
de editar_registro para crear, ordenar, editar y eliminar módulos, lecciones
y preguntas. Presentación, contenidos, duración/inscripción, instructores y
pagos se editan por separado; código y unidad conservan sus identificadores.
Las herramientas existentes de grupos, matrículas, notas y diseño PDF permanecen
accesibles desde estos apartados.

Se corrigió el formulario de una sola sección: ocupa toda la fila y utiliza
dos columnas en escritorio, una en móvil y todo el ancho para textos largos.
Dentro del editor, los formularios se cargan y guardan con fetch/multipart,
CSRF y validación del backend; los campos visibles corresponden al tipo de
lección o pregunta sin vaciar los demás valores. Se conserva el apartado y
la expansión de módulos al guardar; los visores reflejan los cambios al volver.
Cerrar, cancelar o pasar a pantalla completa comprueba cambios pendientes.

No se permite borrar módulos/lecciones con avances, intentos o entregas ni
cambiar el tipo de una lección con actividad. Después de rendir un examen no
se agregan o eliminan sus preguntas ni se cambian respuestas/puntuaciones; se
puede crear una evaluación nueva. Un curso con inscritos conserva su protección
contra eliminación; un curso vacío que se elimina retorna a Gestión → Cursos.
No requiere migración ni modifica los cursos o inscripciones reales al consultar.

Validación: 32 pruebas finales del editor y panel de cursos, más 104 pruebas
de regresión de gestión, cursos, aula, auditoría y certificados. Ruff, sintaxis
JavaScript, check y makemigrations --check pasaron. Las 40 páginas de QA se
generan en test_citt_db con rollback verificado y cero certificados emitidos;
los POST del servidor visual son simulados, la persistencia se valida con tests.

Revisión visual del editor: 320, 390, 768 y 1440 px, con 12 vistas y 56
aperturas de formularios. Se comprobaron campos por tipo, modal directo y visor
de gestión sin anidar, guardado AJAX y cambios pendientes. Se corrigió además
el mínimo de las columnas de la ficha del curso para que no desborde a 320 px.
Los textos de lecciones siguen editándose como HTML en textarea; no se añadió
un editor visual de texto enriquecido.


## Visor PDF unificado en la misma pantalla

Certificados (incluida la vista previa del diseñador), reportes, materiales del
aula, centros I+D, reservas y guías, fichas de equipos, prácticas, repositorio
y observatorio utilizan el visor institucional PDF.js local. Se retiraron los
iframes PDF nativos y los accesos de visualización en pestañas nuevas. Las
descargas explícitas conservan su acción y los permisos del backend.

El componente compartido usa un dialog nativo para aparecer también sobre los
modales de gestión de cursos. Dentro de marcos del mismo origen delega en el
visor superior; cerrar devuelve el foco y conserva el contenido anterior. El
diseñador del certificado mantiene el PDF integrado en su formulario y habilita
guardar sólo después de cargar una vista previa válida. Ampliar la gestión del
curso cambia el tamaño del modal; no navega a otra página.

La carga se cancela al cerrar o cambiar de documento. Páginas y miniaturas se
dibujan según su proximidad a la vista, con límite de resolución y controles de
zoom adaptados a móvil. Los PDF externos dependen del CORS del servidor de origen:
si éste impide cargarlos, se muestra un error dentro del visor. No se incorporó
un proxy de URLs arbitrarias ni se cambiaron las autorizaciones.

Validación: 83 pruebas de integración de PDF, cursos, certificados, recursos
externos y repositorio; Ruff, sintaxis de nueve scripts, compilación de plantillas, check y
makemigrations --check sin errores. Revisión en Chrome a 320, 390, 768 y 1440 px:
41 comprobaciones y 17 capturas, con tinta real en canvas, página 12, zoom,
cambio rápido de documento, cierre pendiente, PDF sobre gestión y regreso a
la misma pantalla. Sin excepciones JS ni pestañas adicionales.

Las muestras en var/qa-pdf-unificado usan test_citt_db con rollback verificado,
cero certificados emitidos y cero configuraciones guardadas; los POST del
servidor visual son simulados. Los helpers 8060/9229 se cerraron y el servidor
Django existente en 8000 permanece intacto. Esta unificación no requiere
migraciones ni cambios en los datos reales.


## Mostrar u ocultar la contraseña

Inicio de sesión, registro y formularios de definir/cambiar/restablecer contraseña
incorporan el ojo con un componente compartido (contrasena.js). El botón no envía
el formulario y conserva el valor y la selección al pulsarlo mientras se escribe.
Cuenta con etiqueta Mostrar/Ocultar contraseña, aria-controls, estado aria-pressed,
SVG propio, foco visible y área táctil de 44 px. Se mantienen autocompletado y
validaciones; vuelve a ocultarse al enviar, restablecer el formulario o salir.

Las etiquetas de las pantallas de contraseña se asociaron con for/id para que
el botón quede fuera de ellas. JavaScript externo, sintaxis comprobada y siete
plantillas compiladas. No requiere migraciones ni cambios de datos.

Revisión real en Chrome del acceso y registro a 320 y 1440 px: cuatro vistas
y seis campos, ratón/Enter/Espacio, valor/cursor/foco conservados, cero envíos
y cero excepciones JavaScript. Se corrigió el main anidado del registro que
provocaba desbordamiento en móvil. Evidencia en var/qa-ojo-contrasena.


## Estabilidad del visor PDF y proporciones de certificados

Se reprodujo el titileo del certificado: los espacios provisionales tenían
proporción vertical y el PDF real era horizontal. Al dibujarlo desaparecía la
barra vertical, cambiaba el ancho y ResizeObserver iniciaba de nuevo el ciclo.
En 8,4 segundos de reposo se añadían 31 canvas y se retiraban 29; el ancho
alternaba entre 703 y 688 px sin interacción.

El visor ahora obtiene las medidas reales de la primera página antes de
construirlo, conserva la proporción de cada hoja y miniatura y reserva un ancho
estable para la barra de desplazamiento. Zoom y redimensionado mantienen los
canvas existentes: la nueva imagen se prepara en un canvas auxiliar y se
copia al terminar, con cancelación y control de generación. Las páginas que
cargan durante el zoom respetan el tamaño actual del gesto. Se actualizó la
versión de los recursos compartidos a 20261009-estable-v3.

Validación: 19 pruebas de integración del visor PDF aprobadas y sintaxis JS
correcta. En Chrome, certificado integrado a 320, 390, 768 y 1440 px: más de
8 segundos por tamaño, cero sustituciones de canvas y ancho estable. Certificado
y material de 12 páginas en modal a los cuatro anchos: 6 segundos por caso,
sin hojas transparentes, desbordamientos ni deformación de proporciones.
Evidencia y capturas antes/después en var/qa-pdf-unificado/titileo-*.
No requiere migraciones ni cambios en datos; se reutilizaron las muestras
ficticias existentes.

QA final de estabilidad: 19 comprobaciones visuales, 16 capturas después y
una antes; incluye reportes a 320/1440 px, zoom 4x, página 12, miniaturas,
cinco cambios rápidos de tamaño y cambio/cierre pendiente de documento.
Cero sustituciones de canvas, muestras transparentes, excepciones o pestañas
nuevas; desviación máxima de proporción 0,463% por redondeo de píxeles.
Se cerraron los helpers QA 8060/9229 y Django 8000 sigue respondiendo HTTP 200.


## Escala visual adaptable entre computadoras

Se ajustaron Inicio, catálogo, fichas de unidades, centros I+D, Servicios,
Quiénes somos, Normativa, Noticias y presentación de cursos para ventanas de
portátil y pantallas con menos espacio útil. La cabecera y las portadas usan
reglas locales por ancho/altura; los títulos tienen límites de tamaño y las
acciones se distribuyen sin solaparse. El catálogo reduce columnas antes de
estrechar demasiado sus tarjetas. La primera revisión usó 1600 px; el ajuste
vigente amplía el ancho a 1780 px, con los márgenes de Quiénes somos, y aplica
la densidad compacta hasta 2047 px. Los visores adaptan su altura a la ventana.

Se corrigió también un margen global de 80 px que afectaba al main interno
de la ficha en móvil. El ajuste se limita al contenedor de trabajo de la unidad.
Se respeta el zoom y la escala institucional; no se modifica Bootstrap global
ni se oculta desbordamiento del documento.

Montserrat y Poppins se alojan en static/font/institucional, con licencias OFL,
procedencia y SHA-256; fuentes.css se carga desde el componente de paleta tanto
con configuración como sin ella. Se retiró Google Fonts del layout principal
y del import redundante de reservas administrativas. Se verificaron pesos,
caracteres españoles, finders y procesamiento comprimido de estáticos en una
carpeta temporal. No se añadieron dependencias ni migraciones.


Validación del ajuste: Django check sin incidencias y plantillas afectadas
compiladas. Chrome: 54 combinaciones de las vistas principales en nueve tamaños
entre 320 y 2560 px, 12 combinaciones de portadas institucionales y 30
comparativas previas, con fuentes locales reales verificadas. Sin desbordamiento
horizontal ni excepciones JavaScript en esas vistas. Cuadrícula/lista en
catálogo y centros, y menú móvil con nombre largo a 320/1024 px, comprobados.
La revisión final del visor de la ficha confirmó 22 px de separación del menú
a 320, 390, 1366 y 1920 px.

Evidencia en var/qa-responsive-portal: metricas.json, metricas-extra.json,
interacciones.json y capturas bajo final/. Se usaron documentos HTML capturados
con rollback y un perfil de navegador aislado. Los medios externos y Font Awesome
CDN no se cargaron en QA; el panorama Pano2VR se excluyó porque bloqueaba el
renderer headless sin GPU. Se mantuvo el resto de JavaScript activo. No es una
certificación de equipos físicos ni de todos los flujos privados del sistema.
La equivalencia de zoom utiliza un viewport CSS de 960×540 con DPR 2.

Los helpers de QA 8061/9231 quedaron cerrados y Django 8000 permanece activo.
La consulta inicial real de FabLab pudo sumar una visita al contador; las
capturas posteriores se obtuvieron con rollback y no realizaron ediciones.
Resumen y cierre de procesos en resumen-final.json y cleanup.json dentro de
var/qa-responsive-portal/.


## Segundo ajuste: márgenes comunes y densidad de escritorio — 9 de octubre de 2026

Esta revisión sustituye el límite anterior de 1600 px. La referencia es el
bloque «La UPEC en acción» de Quiénes somos: hasta 1780 px, centrado. La separación
lateral total es clamp(32px, 8vw, 152px); en móvil es 28 px. El nuevo archivo
portal/css/core/encuadre.css se carga desde la paleta compartida y alinea cabecera,
Inicio, catálogo, fichas, centros, páginas institucionales, Servicios y cursos.
Los fondos conservan todo el ancho y los párrafos mantienen límites de lectura.

La densidad compacta también se aplica en escritorios de 768 a 2047 px CSS,
aunque tengan más de 820 px de alto. Se corrige así el salto de tamaño que antes
reaparecía en Full HD. El catálogo usa títulos de portada de 30–40 px, nombres de
tarjetas de 16 px, descripciones de 13 px y columnas de al menos 296 px, con
un máximo de cuatro desde 1440 px. En pantallas mayores los nombres de tarjetas
quedan en 18 px; los metadatos tienen interlineado proporcional. Se conservan títulos
completos, alturas iguales dentro de la rejilla y las vistas de cuadrícula/lista.

Se eliminó el margen superior duplicado del layout del portal. El desplazamiento
del contenido corresponde a la altura de la cabecera, incluidos sus bordes:
108 px en escritorio amplio, 94 px compacto y 98 px móvil. Un nombre largo se
trunca visualmente sin expandir la barra; el texto completo permanece en el
enlace accesible al perfil. La ubicación secundaria deja espacio a contacto y
cuenta en escritorios menores de 1680 px. No cambia datos ni preferencias de zoom.


Validación del segundo ajuste: 118 casos finales distintos en 130 ejecuciones
(incluye 12 repeticiones del catálogo definitivo), comparados con 86 casos
previos. Se revisaron anchos CSS de 320 a 2560 px, además de DPR 1,25,
cuadrícula/lista, menú móvil, cuenta con nombre largo y aula. No se detectaron
desbordamientos horizontales ni excepciones JavaScript en esos casos. Django
check y compilación de las plantillas afectadas terminaron sin incidencias.

A 1920 px el título del catálogo pasó de 67,2 a 40 px y la tarjeta de
386,5 × 557,89 a 426,25 × 489,33 px. A 2560 px las tarjetas definitivas miden
433 × 524,02 px. Se confirmó la alineación entre cabecera y contenidos:
1753 px de ancho y 76 px de margen a 1920; 1780 px y 382,5 px a 2560;
292 px y 14 px a 320. También se corrigió el contraste de las acciones del aula.

La evidencia está en var/qa-responsive-portal-v2/resumen-final.json, las métricas
y capturas bajo final/, y cleanup.json. Las últimas mediciones del catálogo
sustituyen la prueba intermedia de cinco columnas. Se usaron HTML reales
capturados con rollback y una identidad ficticia sin guardar para el aula;
no se alteraron usuarios, matrículas, avances, certificados ni visitas.
Las fuentes locales se verificaron en Chrome. Las equivalencias de escala
125 %/150 % usan viewports CSS, sin cambiar el zoom real del usuario. Los medios
externos y Pano2VR no se validaron en esta ronda; pantalla completa no se repitió
funcionalmente. Se cerraron los helpers 8061/9231 y se conservó Django 8000 activo.


## Cabecera, visualizador y asistente de reservas — 9 de octubre de 2026

El tercer ajuste conserva los márgenes comunes de 1780 px. La barra principal
retira su borde inferior claro y reduce su altura de 74 a 64 px en escritorio
amplio, de 64 a 54 px en compacto y de 64 a 56 px en móvil. El desplazamiento
superior correspondiente pasa a 97, 83 y 89 px, respectivamente. El nombre
corto del sistema deja de limitarse a 210 px y permanece en una línea en
escritorio; logo, separador, menú y herramientas tienen espacio independiente.

El visualizador de la unidad recupera altura: se retira el límite compacto
de 58dvh/640 px y se usa 78dvh con límites según el ancho, hasta 1080 px
en escritorio. Los límites móviles y la distribución de pantalla completa
conservan sus reglas específicas.

El asistente de reservas retira la introducción repetida y reúne título y nombre
de unidad en una fila de escritorio. Se neutraliza el margen de Dore que afectaba
al main interno. Las dos rutas usan imágenes laterales y texto a su derecha;
preparativos y tutoriales siguen completos. La nota de confirmación comparte
el pie del primer paso y las acciones de las cinco etapas permanecen en el
flujo, sin cubrir campos.

La ventana deja de forzarse a toda la altura de escritorio: ajusta su altura
al contenido, con un máximo de viewport y desplazamiento interno para pasos
largos. Por encima de 1366 px tiene un ancho máximo de 1780 px y márgenes de
16 px; entre 821 y 1366 px conserva márgenes de 4 px. En móvil conserva
la ventana completa y las tarjetas se apilan. Se actualizan las versiones de
los estilos de cabecera, visualizador y reservas para invalidar la caché.

Validación de esta ronda: 20 casos de cabecera y visualizador, dos pruebas
funcionales de entrar/salir de pantalla completa, 62 casos visuales de reservas
y 20 comprobaciones focales tras limitar la ventana, más dos casos de altura
natural en 1280/1366 px. Se cubren anchos CSS de
320, 390, 1280, 1366, 1536, 1920, 2048 y 2560 px según componente, cuenta
con nombre largo, menú móvil y cabecera en inglés. No se detectaron
desbordamientos horizontales ni excepciones JavaScript en los casos medidos.

A 1366 × 768 el visualizador completo pasa de 496 a 650 px de alto; a
1920 × 960, de 608 a 800 px. El primer paso de reservas mide 1780 × 653,5 px
en escritorio de 1920/2560 px; a 1280 × 720 ambas tarjetas y Continuar quedan
completos, con unos 24 px libres bajo el pie. Los pies de las cinco etapas son
alcanzables al desplazar el cuerpo del modal. Django check, sintaxis JavaScript,
compilación de plantilla y tres pruebas existentes del asistente pasan. Se
actualizan dos expectativas antiguas del test de contrato: título compacto y
marcador del visor PDF integrado.

La evidencia está en var/qa-responsive-portal-v3/resumen-final.json y final/.
Los HTML reales se capturaron con rollback y participantes ficticios sin guardar.
La navegación local de reservas cubre los pasos 1–3; los pasos 4–5 se activaron
para inspección visual, sin cotizar ni enviar solicitudes. Los medios externos,
Pano2VR y los glifos FontAwesome del CDN bloqueado por el aislamiento de QA
no se validaron; las fuentes locales sí cargaron. Esta ronda no cambia el zoom
del usuario ni valida equipos físicos.

Cierre: los helpers QA de los puertos 8061/9231 se cerraron y Django 8000 sigue
activo. Cleanup y resumen final confirman que no hubo escrituras persistentes.


## Ventanas completas y escala de lectura — 9 de octubre de 2026

La nueva indicación sustituye el límite de 1780 px y la altura natural del
asistente de reservas: su ventana ocupa el 100 % del viewport y 100dvh, sin
margen, radio exterior ni sombra. El cuerpo conserva desplazamiento interno
y las acciones siguen en el flujo de cada etapa. Las imágenes de las dos
rutas aprovechan más altura en escritorio amplio, con límites de 220–360 px.

Reservas usa una escala común de 14 px para contenido, etiquetas y controles,
12 px para ayudas, 18 px para subtítulos, 20 px para títulos de panel y 22 px
para la cabecera (20 px en móvil estrecho). Se reemplazan las declaraciones
numéricas menores de 12 px y se neutralizan herencias globales en párrafos y
formularios. La escala queda centralizada en variables CSS del componente.

La gestión del laboratorio usa el mismo shell completo, con título y nombre
de unidad en una fila de escritorio, sin el rótulo repetido «Gestión y reserva».
En móvil la cabecera se redistribuye conservando la lectura a 20/14 px. El
panel mantiene cuerpo de 14 px, ayudas de al menos 12 px y títulos de 20–24 px;
se eliminan márgenes heredados del main anidado. Los gráficos SVG limitan su
ancho entre 740 y 1000 px y desplazan su propio contenedor cuando hace falta,
para que sus anotaciones conserven al menos 12 px visibles.

La agenda insertaba reglas de 7–11 px desde JavaScript. El CSS del asistente
prevalece ahora sobre esas reglas, incluidos horarios, leyendas, eventos y
detalle de actividades. Se anula también el radio exterior impuesto con
!important por main.css en ambos modales. No se cambian validaciones, flujos,
permisos ni datos.

Durante QA se reprodujo una respuesta tardía de disponibilidad que intentaba
renderizar después de cerrar el modal. El cierre invalida ahora la secuencia
de consulta y el render comprueba la fecha; ocho pruebas Node cubren éxito,
error, lectura de JSON y reapertura. Hora y estado de los eventos se envuelven
en filas separadas cuando falta ancho, manteniendo la tipografía legible.

Validación final: 36 casos base y 12 casos de calendario con actividades
ficticias, en viewports CSS de 320, 390, 1280, 1366, 1920 y 2560 px. Ambos
shells cubren el viewport con borde y radio cero; no hay desbordamiento
horizontal del documento/modal y los pies siguen accesibles. Texto mínimo
de 12 px, fuentes locales cargadas y ninguna excepción JavaScript en la
matriz; el cierre restaura la página y el desplazamiento. El foco adicional
de bloques «Disponible» en 1280/390 px confirma dos líneas sin recortes.
Los gráficos de recursos pasan en 390/1280/1920 px sin rótulos fuera ni
colisiones, con texto efectivo de 12,63–17,07 px.

Django check, compilación de seis plantillas y git diff --check pasan. La
prueba `node --test webcitt/tests/js/test_calendario_cierre.cjs` pasa 8/8;
el mismo arnés sobre el respaldo anterior reproduce siete fallos. Evidencia:
var/qa-responsive-portal-v4/resumen-final.json y final/. Los snapshots usan
rollback; no se registran personas, reservas ni avances. Los pasos finales
se inspeccionan visualmente sin enviar solicitudes. CDN/FontAwesome y
Pano2VR externos permanecen fuera de la prueba aislada; no se valida hardware
físico ni se modifica el zoom del navegador.

Cierre de QA: helpers 8061/9231 apagados y servidor Django 8000 conservado.
No se realizan commits ni publicación.


## Cabeceras y acciones de los submodales — 9 de octubre de 2026

La cabecera principal de reservas, historial y gestión usa ahora 18 px y una
altura mínima de 48 px. Los iconos son de 32 px y el botón de cierre de 36 px.
El nombre de la unidad conserva 14 px y se redistribuye cuando falta ancho.
Se mantiene la ventana completa de V4. La regla global de main.css imponía
24 px (!important), o 20 px en móvil; las anulaciones se acotan a estas
cabeceras para que la reducción se aplique realmente sin cambiar el tema.

Los paneles de solicitud y agenda muestran sólo el título de la operación
y el cierre: no repiten «Gestión y reserva», el icono y el nombre de la unidad
que ya aparecen en el marco exterior. El ajuste también cubre la gestión
independiente y los 51 formularios que comparten el cajón de agenda. Se
conservan todos los identificadores y acciones. «Cancelar reserva» distingue
la decisión operativa del botón de navegación «Volver». El pie usa botones
de 34 px, texto de 14 px, separación de 6 px y una sola fila cuando cabe;
en móvil envuelve sin reservar una segunda franja vacía.

El marco de tareas incrustadas tiene título de 15 px y controles de 32 px.
En el editor del curso se conserva el nombre del curso y su estado y se
quita el encabezado de función duplicado. En las vistas de gestión dentro
de un iframe se conserva unidad y operador en una franja contextual breve.
Los pies de edición y diseño de certificado usan controles de 32/14 px.
El diálogo de edición directa usa título de 16 px; en móvil distribuye
título y cierre arriba y el enlace al editor completo debajo.

En móvil hasta 560 px, el cajón integrado se ancla al cuerpo del modal.
Se neutralizan sólo allí las coordenadas de viewport escritas en línea por
panel_trabajo.js, para evitar que se sumen al desplazamiento de su contenedor
y dejen el pie fuera de pantalla. La geometría de escritorio se conserva.

Se versionaron las cinco hojas CSS en sus 14 plantillas consumidoras.
Respaldos, manifest de caché y validación se guardan en
var/qa-responsive-portal-v5/. Django check, compilación de 16 plantillas
con SQL bloqueado y git diff --check pasan.

Validación visual V5: 51 capturas finales en seis viewports CSS (320, 390,
1280, 1366, 1920 y 2560 px), sin excepciones JavaScript ni desbordamiento
horizontal del documento/modal. Títulos principales y de cajones computados
a 18 px; barra de tareas a 15 px. El cajón de solicitud pasa de 91 a 46 px
de cabecera y de 96 a 47 px de pie en escritorio. En móvil el pie usa dos
filas (87 px) y queda dentro del viewport; cajón y cuerpo comparten el mismo
punto de inicio. El diálogo directo distribuye correctamente su cabecera
en 390 px. Root inspeccionó las capturas de solicitud 1920/390/320, editores
de curso/certificado y diálogo directo.

Las capturas se generaron con datos ficticios y SQL de sólo lectura/rollback;
no se guardaron solicitudes ni diseños. Los recursos externos y los glifos
FontAwesome del CDN no forman parte de la prueba aislada. Esta revisión de
la interfaz no valida equipos físicos ni modifica el zoom del navegador.

Comprobación adicional: el pie del diálogo de edición mide 44 px y es
alcanzable en 390 px; el formulario de bloqueo conserva sus acciones en
320/390 px. Tres cierres restauran correctamente la vista y CSSOM confirma
las cinco hojas sin declaraciones descartadas. Evidencias: final/metricas.json
y final/comprobaciones-finales.json dentro del directorio V5.

Cierre V5: resumen-final.json PASS; helpers QA 8061/9231 cerrados y servidor
Django 8000 conservado. Sin commits, publicación ni escrituras persistentes.


### Certificados profesionales de capacitaciones y eventos (2026-10-09)

Editor ampliado, hoja completa y ampliación en modal a pantalla completa.
Seis modelos PDF, hasta cuatro logos y tres firmas; inicio, fin, emisión y
horas, sin nota en documentos nuevos ni en la validación pública. Textos
editables para aprobación, participación, asistencia, ponente y organizador.
Acreditación de roles desde participantes, limitada al gestor del curso y
con motivo/confirmación. Aprobación sigue dependiendo del aula y sus notas.
Fechas y horas del grupo prevalecen; se exigen datos completos al emitir.
Snapshots históricos mantienen su composición; código único y QR verifican
registros vigentes/anulados. QR decodificado y comprobado en 12 muestras.

0318 aplicada con respaldo previo de las tres tablas; sin nuevas matrículas
ni certificados reales. SITE_URL sigue en localhost: hace falta el dominio
público definitivo antes de emitir certificados para consulta desde fuera.
El editor advierte de esta configuración. Detalles, matriz de modalidades
y referencias institucionales en docs/responsive-portal-y-operacion.md.
Evidencia en var/qa-certificados-profesionales/, var/qa-certificados-diseno/
y var/qa-certificado-editor/. Sin commits ni publicación.


### Certificados V3 y respaldo institucional (2026-10-10)

La previa ahora centra controles de 330 px y dimensiona el PDF por la proporción
A4 y la altura útil: hoja completa, sin un panel extendido a todo el sobrante.
Seis composiciones vectoriales propias renovadas, cuatro logos proporcionales
y tres firmantes. Emisor y frase de otorgamiento editables. Período español
y horas en el párrafo; emisión secundaria; sin nota en certificados nuevos.
Snapshots V1/V2 y documentos sin snapshot conservan texto y raster.

0319 aplicada con respaldo y comparación de datos: 0 certificados, 1 configuración
y 7 grupos sin cambios de cantidad. Sólo se migraron tres defaults antiguos;
textos personalizados preservados. Seis previas reales HTTP 200 con SQL
exclusivamente de lectura. QA de 8 tamaños y 12 PDF de composición; QR recuperado
desde píxeles sin invasiones. Cierre detallado y fuentes primarias sobre UPEC,
Ministerio del Trabajo, SAE y CEDIA en docs/responsive-portal-y-operacion.md.

La ruta recomendada es confirmar autorización de educación continua y
firmantes con la dependencia competente UPEC. OCC y OEC corresponden a
procesos específicos del Ministerio del Trabajo; no se atribuyen avales.
SITE_URL continúa local y debe definirse el dominio público antes de emitir
para consulta externa. No se implementó firma electrónica criptográfica.
Evidencia: var/qa-certificados-v3/, var/qa-certificados-diseno-v3/ y
var/qa-certificado-editor-v3/. Helpers QA cerrados; puerto 8000 conservado.
Sin commits, publicación ni certificados reales emitidos.

Cierre V3: 142/142 pruebas integradas PASS. Normalización de imágenes libera
el FieldFile que abre, sin cerrar uploads del llamador; reemplazo de firmas
en Windows comprobado. Django check y git diff --check pasan.


### Márgenes mínimos y contenido centrado (2026-10-10, revisión V4)

El editor ahora aprovecha el ancho con 12 px exteriores (8 px móvil), controles
de 330 px y el resto para la previa; reemplaza el bloque estrecho centrado V3.
La superficie PDF sigue ajustada a la hoja completa y centrada dentro del
panel. Estado vacío compacto. CSS/JS versionados editor-margenes-v4.

Geométrico nuevo centra todos sus textos; la clave JSON alineacion_contenido
congela esa decisión. V3 sin clave conserva el diseño anterior. Emisión
separada del filete. QA: 9 tamaños, 13 combinaciones, 12 pruebas de composición
y seis previas reales de sólo lectura correctas. Sin migraciones ni guardados.
Helpers QA cerrados; app 8000 activa. Evidencias V4 en docs/responsive-portal-y-operacion.md.

Validación final V4: 28/28 pruebas de contenido, editor y composición correctas; base de pruebas liberada. Registro: `var/qa-certificados-margenes-v4/pruebas-certificados-v4.log`.


### Certificados V5 e importación desde hojas de cálculo (2026-10-10)

Doce modelos propios en el editor, incluidos industrial, circuitos, horizonte,
editorial, académico e inmersivo. Logos sin placas; adaptación de contraste
sólo de la marca institucional transparente y fotografía propia/de la unidad
en cuatro estilos. Texto breve, bloque institucional y relato con competencias;
subtítulo y alineación editables. Propuestas de texto por rol y actividad con
aplicación explícita. Márgenes de 12/8 px y previa completa conservados.
Snapshot V4 nuevo; 20 comparaciones V1–V3 mantienen texto y raster.

Cursos → Participantes → Subir lista y revisar: plantillas XLSX/CSV, hasta
500 personas/2 MB. Eventos usan cedula y nombres_completos y permiten
certificados sin cuenta (asistencia, participación, ponente y organizador),
con motivo y datos completos. Cursos usan también correo, resoluble por
cédula sólo con cuenta activa inequívoca y correo verificado. Conserva cupos,
pagos y exoneraciones previamente autorizadas; nuevas invitaciones sin
exoneración. No envía correos automáticamente ni crea cuentas ficticias.
Revisión por fila, confirmación atómica e idempotente, ligada a sesión,
actor, curso y grupo durante 20 minutos. ZIP de PDF emitidos; anulaciones,
reemisiones y consulta QR para ambas identidades.

0320/0321 aplicadas tras respaldo completo PostgreSQL verificado:
antes-certificados-importacion-v5-20261010-113033.dump. Conservación de todas
las columnas previas PASS: 0 certificados, 1 configuración, 0 invitaciones,
0 inscripciones, 7 grupos; 0 participantes externos reales nuevos.

Validación: 113 casos únicos en 11 módulos, último focal 50/50 PASS y
editor/contenido 16/16 PASS; 18 pruebas de composición, 24 PDF/QR y
20 regresiones históricas PASS. Doce previas reales 200 con 117 SELECT y
0 escrituras. Navegador: 14 escenarios de editor, 8 funcionales, 7 controles
nuevos, 14 de importación y 2 recapturas focales PASS. Checks Django,
migraciones y diff PASS; base de pruebas libre. Evidencia en
var/qa-certificados-v5/ y detalles en docs/responsive-portal-y-operacion.md.
Sin commits ni publicación; aplicación 8000 conservada.


### Visor automático y diseños tecnológicos V6 (2026-10-10)

Visor del certificado con una sola acción: Descargar PDF. Ajuste al ancho
útil y desplazamiento vertical, márgenes de 12/8 px; sin pie ni controles
de zoom/ampliación. Previa al abrir, pulsar un modelo y editar campos
(500 ms). El botón manual se elimina. Respuestas y montajes tardíos no
reemplazan la última selección; el guardado exige la previa vigente.

Dieciséis modelos: se añaden IA de partículas, red científica, polígonos
digitales y ondas tecnológicas. Paletas y fondos claro/oscuro, temática por
actividad, intensidad y fondo propio PNG/JPEG de 2 MB con cinco encuadres.
Gráficos vectoriales propios y zonas de lectura/firmas/QR protegidas.
Snapshot nuevo V5; V1–V4 mantienen texto y raster. Se conserva la carga masiva
XLSX/CSV incorporada en V5. Guardado AJAX con errores por campo sin perder
uploads, validación de los cinco roles y revalidación de permisos bajo lock.

0322 aplicada después del respaldo verificado
antes-certificados-fondos-v6-20261010-124614.dump. Todas las columnas previas
conservadas: 0 certificados, 1 configuración, 0 invitaciones/inscripciones,
7 grupos y 0 participantes externos; sin emisiones ni diseños ficticios
guardados. Validación: 71 casos únicos, 32 regresiones históricas exactas,
18 PDF/QR y 16 previas reales 200 con 73 SELECT/0 escrituras. Checks Django,
migraciones y diff correctos; conexiones de pruebas liberadas. Detalles
y respaldo SHA256 en docs/responsive-portal-y-operacion.md.
Evidencia: var/qa-certificados-v6/. Sin commits ni publicación.

Navegador V6: 7 escenarios visuales y 13 funcionales PASS, sin overflow ni
excepciones JS. PDF ocupa 97–99,5 % del ancho útil; edición rápida y guardado
conservan la selección vigente y los archivos. POST de guardado interceptados
en QA; no se modificaron diseños reales.

Tres comprobaciones adicionales de los controles de fondo pasan. Helpers QA
8061/9231 cerrados; aplicación Django 8000 conservada activa. Sin commits ni
publicación. Resumen: var/qa-certificados-v6/root/cierre-integrado.json.


### Certificados V7: firmas, instituciones y hoja completa (2026-10-10)

Previa ajustada al ancho y alto para mostrar la hoja completa centrada,
sin desplazamiento interno y con cabeceras más pequeñas. Sólo Descargar PDF.
Snapshot nuevo V6: firmas más destacadas en hasta tres columnas y emisión/fecha
pequeñas junto al QR de 25 mm. V1–V5 conservan composición y contenido.

UPEC + laboratorio permanecen por defecto; hasta cuatro aliados agregables
con nombres, logos opcionales, posición y contraste sin placas. Facultad y
carrera opcionales. Nueva variable {organizadores}; textos personalizados
anteriores conservados. Datos conocidos precargados desde curso/unidad/grupo
sin escribir al abrir; datos ambiguos o desconocidos no se inventan.

Validaciones recuperables de variables del emisor y fallos del visor. Cambiar
modelo y guardar/reabrir conserva imágenes y textos. Se mantiene la importación
XLSX/CSV y los dieciséis diseños incorporados en revisiones anteriores.

0323 aplicada tras respaldo verificado
antes-certificados-entidades-v7-20261010-140214.dump. Todas las columnas
previas conservadas: 2 configuraciones, 7 grupos y 0 certificados,
invitaciones, inscripciones o participantes externos. Sin guardados de muestra.
Evidencia y hash en docs/responsive-portal-y-operacion.md y var/qa-certificados-v7/.

Validación V7: 89 casos únicos PASS (incluyen 32 de composición), 48
regresiones históricas exactas y 32 PDF/QR de una página. Dos expectativas
antiguas se actualizaron y repitieron con éxito. GET +16 previas reales 200:
93 SELECT, 0 escrituras. Checks Django/migraciones/JS/diff correctos.

Navegador V7: 8 escenarios visuales, 13 funcionales y 10 de instituciones
PASS. Hoja completa sin scroll interno; barra real 33 px y título 13 px.
Cambios/guardado conservan archivos y editor abierto; estabilidad tras montaje
0 mutaciones, 0 errores JS y 0 escrituras reales. Capturas finales PDF V7.

Cierre operativo V7: helpers QA 8061/9231 cerrados, aplicación Django 8000
activa. Sin commits ni publicación. Resumen integrado:
var/qa-certificados-v7/root/cierre-integrado.json.


### Certificados V8: plantillas y logos corregidos (2026-10-10)

Causa real: redes/claro/alta guardados reemplazaban la apariencia de Sobrio
y otros modelos por ondas, aunque el modelo sí llegaba bien al servidor.
Snapshot nuevo V7 conserva formas individuales y limita las personalizaciones
a las áreas artísticas. Cabecera limpia protege logos/títulos frente a fotos
y rejillas; UPEC y 1–4 aliados comparten una fila según cantidad real.
Ayuda/cache HTML v8; visor y personalizaciones del usuario conservados.

16 previas reales con configuración FabLab y cuatro recapturas finales PASS:
16 fondos distintos, Sobrio con franjas, logos sin superposición; 110 SELECT
y 0 escrituras. Cuatro regresiones focales únicas PASS. Navegador usa endpoint
real: 4 cambios y 2 focos finales PASS, 8 previas/56 SELECT, 0 errores/escrituras.
Django/migraciones/JS/diff PASS. Datos completos de 2 configuraciones y 7
grupos intactos; 0 emisiones y sin migraciones. Detalles en
docs/responsive-portal-y-operacion.md y var/qa-certificados-v8/.

Cierre de QA V8: 36 pruebas de composición únicas aprobadas; 32 PDF (16 modelos en caso normal y denso), todos de una página, con los 32 QR decodificados y coincidentes con su enlace. Las 64 comparaciones históricas V1–V6/sin snapshot conservan texto y raster exactos. La revisión visual final verificó Sobrio, Tecnológico e Industrial con la configuración real, el caso de cinco logos y tres firmas, y el PDF completo en navegador. Helpers 8061/9231 cerrados; aplicación 8000 conservada. Evidencia consolidada: `var/qa-certificados-v8/root/cierre-integrado.json`.


Auditoría certificados V9 (2026-10-10): corregidos reemplazo/quitar imágenes,
colores automáticos de miniaturas, contraste y continuidad de cabecera oscura,
y duplicidad matrícula/evento por cédula sólo en perfil. Nuevas emisiones
snapshot8; snapshots7 conservados exactos. Sin migraciones ni datos reales
modificados. 203 pruebas funcionales, 38 composición, 10 adicionales del panel,
12 casos navegador/4 tamaños PASS. 16 diseños oscuros y 17 QR verificados;
Django/JS/lint/migraciones/datos PASS. Helpers cerrados y aplicación 8000 activa.
Evidencia: var/qa-certificados-v9/root/cierre-integrado.json.


### Integridad por unidad y límites modulares (2026-10-10)

Revisada la propiedad de formación: Unidad → Curso → EdicionCurso →
InscripcionCurso o ParticipanteEvento → CertificadoCurso. Los hijos derivan
la unidad del curso; no se añadieron FK redundantes ni migraciones. Corregidas
seis validaciones de relaciones cruzadas (progreso, intentos, entregas, pagos,
invitaciones y respuestas de comentarios). completar valida antes de escribir.
Las reglas de identidad y matrícula ahora son puras, sin dependencia de
modelos hacia formularios/aplicación; imports anteriores compatibles.

85 casos funcionales únicos PASS, incluidos 8 de aislamiento y 10 de rutas;
18 de límites/manifiestos/validación pura PASS. Una fixture antigua se completó
con fechas y horas reales de prueba, manteniendo su aserción de certificado.
Django, lint, migraciones y diff PASS; 0 conexiones de testDB al cierre.

Base real: 73 relaciones físicas con unidad directa revisadas; las dos
diferencias pertenecen a una transferencia de inventario válida. Raíces y
seis relaciones indirectas de formación sin incoherencias. Conservación de
todas las columnas de formación PASS; 0 escrituras reales. Sin commits.

Modularidad parcial: formación comparte operación en webcitt y permiso
practicas; no tiene despliegue independiente. Documentado en arquitectura y
manifiestos sin cambiar permisos. clean/ModelForm y servicios protegen estos
flujos; save/create/bulk o SQL directos no ejecutan clean automáticamente.
Evidencia consolidada: var/qa-unidades-modular-v1/root/cierre-integrado.json.


### Jerarquía institucional de certificados V10 (2026-10-10)

Snapshot9 nuevo: la UPEC conserva logo y nombre protagonistas, seguidos por
la unidad/laboratorio y adscripciones opcionales en líneas propias. Hasta
cuatro entidades aparecen en una columna secundaria «En colaboración con»,
con marcas proporcionales sin placas y nombres adaptados al ancho disponible.
El editor separa bloque principal y colaboradores; el organizador/emisor
sigue correspondiendo al texto de la actividad, sin sustituir la unidad.

100 pruebas únicas PASS (57 funcionales +36 de composición existentes +7
nuevas); 37 PDF/QR,32 casos densos claro/oscuro y188 comparaciones históricas
V1–V8 exactas. Dieciséis previas finales del endpoint real PASS:85 SELECT y
0 escrituras. Render visual revisado con UPEC/Mariana reales, adscripciones
largas y tres firmas. CUA no ofreció navegador; se verificaron PDF reales y
plantilla/formulario sin afirmar una nueva prueba interactiva. Sin migraciones,
guardados, emisiones reales, helpers ni commits. Evidencia consolidada:
var/qa-certificados-jerarquia-v10/root/cierre-integrado.json.

### Catálogo académico, colaboradores y paletas V11 (2026-10-10)

- El editor reutiliza el catálogo canónico contextual: facultad y carrera son selectores dependientes; el servidor resuelve códigos a los nombres existentes y rechaza relaciones cruzadas. Los textos históricos no coincidentes se conservan mediante la opción personalizada. Sin catálogo duplicado ni columnas nuevas.
- Snapshot 10: UPEC centrada y más visible cuando no hay colaboradores. Con aliados, cada nombre aparece debajo de su logo, en una o dos columnas y hasta dos filas. Se respetan posiciones y contraste; sin placas alrededor de los logos.
- Picker nativo, hexadecimal y tres paletas (institucional, laboratorio, tecnología). Vacío usa la paleta institucional contextual o #006633/#ffce00; cambiar de diseño conserva colores personales. Miniaturas y muestras siguen la paleta efectiva.
- Verificación: 61 pruebas funcionales únicas validadas (la ejecución completa tuvo 60 correctas y una expectativa antigua de color; corregida únicamente esa expectativa, el targeted de 5, incluidos los 4 casos nuevos, pasó), 50 de composición y 6 de formulario; 10 escenarios DOM. Matriz de 37 PDF/37 QR, 32 casos densos y 220 comparaciones V1–V9 exactas.
- Endpoint real: 16 modelos con colaboradores y 16 sin ellos; 85 SELECT por matriz, 0 escrituras y 0 emisiones reales. Previa real Sobrio/oscuro adicional confirma Mariana blanca y legible en auto, sin placa. Inspección visual del PDF realizada; CUA no dispone de navegador y no se atribuye QA interactiva.
- Sin cambios de esquema, migraciones ni helpers. Evidencia integrada: var/qa-certificados-jerarquia-v11/root/cierre-integrado.json.


### Certificados: fondos y tipografía V12 (10 de octubre de 2026)

Los nuevos certificados congelan snapshot 11. El fondo oscuro deriva del color principal institucional; desaparecen las placas opacas de cabecera que ocultaban fotografías. Las fotos laterales reservan su espacio y las fotos panorámicas usan transparencia gradual. Los logos se dibujan sin contenedor; las opciones explícitas claro/oscuro describen ahora correctamente el color del logo monocromo. Se mantienen intactos los renderizadores históricos 1–10.

El editor separa los colores de diseño de los colores de texto y títulos, permite Poppins (por defecto), Nunito o clásica, y muestra el PDF aceptado en la tarjeta activa. Poppins regular/negrita se incrusta desde TTF locales derivados de los WOFF2 existentes bajo OFL; la procedencia figura en fuentes.json. El visor del editor solicita densidad mínima 2, respetando el límite de memoria del componente compartido. Los nombres largos ajustan el espacio del documento y del contenido; los colaboradores tienen más ancho.

El pie tecnológico es opcional y está apagado por defecto: circuitos, fabricación o calidad/formación. Conserva el área de firmas y el bloque de QR/emisión. Migración aditiva 0324_estilo_visual_certificados aplicada localmente; se verificaron todas las columnas anteriores de las seis tablas de formación sin cambios de valores ni filas. No se emitieron certificados ni se guardaron configuraciones reales durante la QA.

Evidencia: var/qa-certificados-fondos-v12/cierre-integrado.json. Regresión completa de 127 pruebas PASS; tras corregir la semántica del contraste explícito, 7 pruebas focales PASS. 15 escenarios de eventos/estado en JSDOM, 50 previas del endpoint real en 16 modelos (incluidos dos archivos monocromos cargados temporalmente), inspección visual de PDF rasterizado y 252 comparaciones históricas idénticas en páginas, texto y píxeles. No hubo revisión interactiva del navegador en esta iteración.


### Certificados: superficie blanca y formación lateral V13 (10 de octubre de 2026)

Los nuevos certificados utilizan snapshot 12 y el módulo certificados_composicion.py. El color se limita a franjas, siluetas y ornamentos; el contenido académico y las firmas permanecen sobre blanco, sin la división horizontal de los fondos oscuros. El campo legado modo_fondo se conserva para compatibilidad, se oculta en el editor y se normaliza a claro para emisiones nuevas. Los snapshots 1–11 mantienen sus renderizadores originales.

Se añade «Formación lateral · competencias», inspirado en la distribución editorial de la referencia CEDIA con identidad UPEC: banda institucional, fotografía separada de las dependencias, QR y emisión juntos, colaboradores en su propio bloque, texto y competencias en columna y hasta tres firmas sobre blanco. Las competencias se imprimen al elegir «Texto y competencias o logros»; no se inventan logros del curso. Las fotografías no invaden los logos de cabecera y las imágenes de fondo se atenúan para mantener el contraste. Se conserva el pie tecnológico opcional.

La galería deja de utilizar dibujos CSS aproximados: cada tarjeta visible se genera desde el mismo endpoint PDF y PDF.js que la vista principal, después de completar ésta y con una solicitud a la vez. Los datos, imágenes y colores son los actuales; cambiar el modelo reutiliza tarjetas vigentes, editar los datos invalida las anteriores y cancela tareas pendientes. Las miniaturas no modifican el token de guardado ni bloquean un PDF principal válido si falla una tarjeta. Assets versionados 20261010-editor-composicion-v13.

Migración 0325_formacion_lateral_certificados aplicada localmente, sólo para registrar la opción de diseño. Verificación: 128 pruebas existentes correctas en la corrida integrada, 7 pruebas focales finales correctas, 20 escenarios DOM/galería (PDF.js simulado), 36 previas del endpoint real (17 con y 17 sin colaboradores y 2 con logo blanco cargado), matriz de 34 PDF densos/normales y 284 comparaciones históricas V1–V11 idénticas en texto, páginas y píxeles. Se inspeccionaron los PDF rasterizados; no se atribuye una revisión interactiva del navegador. Datos de las seis tablas de formación sin cambios; cero emisiones reales y cero configuraciones reales guardadas. Evidencia: var/qa-certificados-composicion-v13/cierre-integrado.json.
