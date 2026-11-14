# Seguridad y operación para producción — 10 de octubre de 2026

## Dictamen

La aplicación contiene defensas y una separación operativa de credenciales adecuadas para preparar su publicación. **La configuración local examinada no debe copiarse a producción tal como está:** su conexión PostgreSQL usa un superusuario. Las políticas por filas existen, pero ese rol las elude. El arranque de producción ya incluye `verificar_seguridad_bd`, que rechaza esa situación. No se modificaron roles, contraseñas, datos de negocio ni migraciones durante esta revisión.

Esta auditoría revisa código de configuración, autenticación, cabeceras, entradas, adjuntos, despliegue y recuperación, y ejecuta pruebas dirigidas. No acredita ausencia absoluta de fallos, capacidad de usuarios determinada ni cumplimiento de una certificación. Las verificaciones del servidor universitario, de la red y de recuperación con datos reales siguen siendo necesarias antes de publicar.

## Estado medido de la base local

La consulta se realizó dentro de una transacción `READ ONLY`, sin leer contenido de usuarios ni imprimir nombres de roles, direcciones o credenciales. Evidencia de trabajo: `var/auditoria-roles-rls-2026-10-10.json`, excluida de Git.

| Medida | Resultado local | Implicación |
|---|---|---|
| Entorno cargado | `config.settings` | Es desarrollo; no una instancia de producción validada |
| PostgreSQL | 17.9 | Motor actual inspeccionado |
| Rol actual | SUPERUSER, BYPASSRLS, CREATEROLE y CREATEDB activos | No utilizar ese rol para web, API ni programador en producción |
| Propiedad y permisos | Dueño de 2.018 objetos en `public`, puede crear en el esquema, 15 membresías | Producción exige un rol distinto, sin propiedad ni membresías elevadas |
| Tablas personales protegidas | Seis con ENABLE RLS, FORCE RLS y política con USING/WITH CHECK | La política existe; el superusuario local puede saltársela |
| Conexiones máximas del servidor | 100 | Presupuestar conexiones de cada proceso, tareas y administración |
| Timeouts efectivos locales | Statement, lock e idle transaction: 0 | No confundirlos con los límites de `settings_production` |
| TLS en la conexión inspeccionada | Desactivado | Una base remota requiere TLS verificado; una red privada debe acreditarse como tal |

Las seis tablas son entregas, intentos de ejercicios/evaluaciones, pagos de inscripción, progreso de lección y simulaciones guardadas. La protección no es RLS universal: los otros datos dependen de autorización por objeto y dominio. Aumentar cobertura exige pruebas de agenda, cupos, búsquedas y agregados; habilitar políticas genéricas sin ese contrato puede romper funcionalidades.

Se ejecutó también `python manage.py verificar_seguridad_bd` con la conexión actual: rechazó el arranque por los privilegios elevados del rol, tal como corresponde. Fue una comprobación de solo lectura; no se provisionaron ni cambiaron roles para forzar un resultado aprobado.

## Controles existentes revisados

- `config/settings_production.py` desactiva DEBUG y comandos de demostración, exige hosts y orígenes HTTPS exactos, protege cookies, fuerza verificación de correo local y login social mediante POST, y valida una CSP con nonce sin `unsafe-eval` ni scripts inline autorizados globalmente.
- El proxy sobrescribe cabeceras de origen. Waitress confía en una IP exacta y un salto; no admite comodines ni cabeceras de clientes no confiables. PostgreSQL y el backend se publican en loopback en Compose.
- Los límites compartidos de autenticación y escrituras se cuentan atómicamente en PostgreSQL; un fallo del contador devuelve 503. Nginx limita además lectura y tamaño. La identificación real de la IP depende de configurar correctamente `TRUSTED_PROXY_IP` en el servidor.
- Los recursos privados requieren autorización de la aplicación. La guía de Nginx evita un alias público de `/media/` que saltaría esos permisos. Se conserva aislamiento para HTML interactivo y archivos desconocidos se deniegan.
- La importación masiva de participantes limita tamaño, filas y expansión XLSX; rechaza fórmulas, macros, objetos incrustados y vínculos externos. Es un límite funcional explícito de 500 participantes por lote, no una cola de trabajo para importaciones ilimitadas.
- Compose separa migración, web, programador y respaldo. La web corre sin root y se vacían las credenciales elevadas en sus servicios. `verificar_seguridad_bd` comprueba propiedad, membresías y privilegios antes del arranque.
- El código conserva las contraseñas seguras de Django. Las optimizaciones de hash usadas únicamente en QA no se trasladan a producción.

La auditoría del [8 de octubre](auditoria-produccion-2026-10-08.md) documenta exposición histórica de secretos en Git. No se han leído esos valores en esta revisión. TI debe acreditar la revocación de los secretos antiguos y generar credenciales de producción nuevas; que el entorno local actual sea distinto no demuestra revocación.

## Mejoras aplicadas en esta revisión

| Hallazgo | Cambio | Comprobación |
|---|---|---|
| El verificador instalaba un `dropdb` incondicional antes de confirmar `createdb` | Solo elimina la base temporal cuando ese proceso confirmó su creación; las señales terminan y ejecutan una única limpieza | Creación fallida no invoca dropdb; restauración fallida limpia exclusivamente su propia base |
| Prefijo de la base temporal sin validación | Prefijo ASCII en minúsculas, sin separadores ni espacios, máximo 32 caracteres | Rechazo antes de conexión y nombre final dentro de 63 caracteres |
| Retención cero aceptada aunque el contrato exigía días positivos | Los respaldos de base y adjuntos rechazan valores menores de un día antes de crear archivos | Prueba de ambos scripts sin herramientas PostgreSQL reales |
| Waitress fijaba ocho hilos y usaba límites de cabeceras/conexiones por omisión | `WEB_THREADS`, `WEB_CONNECTION_LIMIT` y `WEB_CHANNEL_TIMEOUT` configurables y acotados; cabeceras limitadas a 32 KiB | Valores válidos, inválidos e inconsistentes probados; límites de cuerpo y confianza del proxy conservados |
| El ejemplo de proxy carecía de límites explícitos de conexiones inactivas y conexión al upstream | Timeouts de cabecera, cuerpo, envío, keepalive y conexión al backend; oculta versión Nginx | Revisión de configuración; falta `nginx -t` con el binario y certificados del servidor real |
| El inventario leía archivos privados antes de clasificarlos | Detecta `.env*`, claves, PEM y respaldos privados antes de leer bytes o calcular hashes | Fixture que falla si el auditor siquiera intenta leer un archivo privado |

Las mejoras de almacenamiento comprimido y carga diferida de módulos se integran en la auditoría general. Se mantiene `FileSystemStorage` para medios: no se movieron archivos ni cambiaron sus nombres o direcciones.

## Capacidad y dimensionamiento

**No hay una prueba de carga representativa en infraestructura de producción.** Por eso no es correcto prometer un número de usuarios por RAM ni afirmar que una máquina de altas prestaciones resuelve consultas, transferencias o procesos largos. Esta es una estimación inicial de ingeniería que debe comprobarse con uso real:

| Perfil | Punto de partida propuesto | Condición |
|---|---|---|
| Pruebas y piloto pequeño | 2 vCPU, 4 GiB RAM y SSD | Sin contenedores de alumnos, videoconferencia propia ni generación masiva simultánea |
| Primera producción institucional | 4 vCPU, 8 GiB RAM y SSD/NVMe, con 80–160 GiB iniciales según medios | Aplicación y PostgreSQL; respaldos fuera de ese disco; medir antes de ampliar |
| Mayor concurrencia o medios pesados | Separar PostgreSQL y almacenamiento de medios; dimensionar procesos web mediante medición | Requiere TLS privado, copias, observabilidad y presupuesto de conexiones |
| Microproyectos, IA, simulaciones de servidor o videoconferencia | Capacidad y aislamiento separados de la web transaccional | No habilitarlos contra el socket Docker del host institucional sin operación e aislamiento específicos |

Los rangos de disco dependen sobre todo de vídeos, cursos, adjuntos y retención; no se derivan del tamaño del código. Reservar espacio para archivos temporales de subida, restauración y migraciones. Los respaldos y la restauración completa pueden requerir otra copia del volumen de datos.

Waitress conserva por defecto ocho hilos, cien canales y sesenta segundos de inactividad. Los canales no equivalen a consultas simultáneas ni usuarios registrados. Con conexiones persistentes Django, presupuestar aproximadamente hasta un enlace PostgreSQL por hilo ocupado, más tareas, migración y administración. Por ejemplo, cuatro procesos de ocho hilos pueden consumir hasta 32 conexiones web: sumar el resto y mantener margen bajo `max_connections`, en vez de aumentarlo sin medir memoria. El timeout de canal es de **inactividad**, no cancela una vista Python lenta; el statement timeout de PostgreSQL limita cada consulta, no el trabajo completo de una vista.

La prueba de capacidad debe cubrir navegación anónima, usuario autenticado, agenda, cursos, búsquedas, alta de participantes y PDF con mezcla realista y concurrencia creciente. Registrar latencias p50/p95/p99, errores, tiempo y cantidad de SQL, conexiones activas/en espera, bloqueos, CPU, RAM, I/O, espacio temporal y bytes descargados. Ensayar también clientes móviles con red lenta. Separar tareas largas de las respuestas HTTP cuando los datos medidos lo justifiquen.

## Recuperación y actualizaciones frecuentes

El respaldo lógico de PostgreSQL es coherente dentro de la base; el archivo de medios y la marca institucional se copian por separado. **Esas tres copias no representan automáticamente el mismo instante.** Para una recuperación coherente, acordar una ventana sin escrituras o utilizar una estrategia coordinada de almacenamiento/versionado y registro de archivos. No se cambió ese contrato de negocio de forma automática.

El intervalo predeterminado es diario: sin otra estrategia de WAL/PITR, el RPO puede aproximarse a 24 horas de cambios perdidos. El RTO no está medido: depende del tamaño real, ancho de banda y tiempo de restauración. Definir ambos con los responsables de la universidad, probar recuperación fuera del servidor principal y documentar el tiempo observado. La suma SHA-256 detecta corrupción accidental; no acredita por sí sola autenticidad, cifrado ni una copia externa.

Para cada actualización: generar y verificar respaldos, probar en staging con copia anonimizada, inspeccionar el plan de migraciones, aplicar cambios aditivos compatibles, ejecutar el rol de migración separado, comprobar roles/RLS, recopilar estáticos y validar recorridos de negocio. Los índices de tablas grandes requieren evaluar bloqueo y creación concurrente. No usar `flush`, borrar migraciones o regenerar la base como mecanismo de actualización. Restaurar una copia antigua para deshacer código también perdería escrituras nuevas; preferir compatibilidad hacia atrás y correcciones hacia delante.

`BACKUP_VERIFY_RESTORE=true` realiza una restauración efímera. El rol de respaldo tiene privilegios elevados de lectura y CREATEDB para ese ensayo; mantenerlo aislado, sin acceso desde la web. La restauración debe recibir respaldos de origen confiable: los dumps SQL incluyen definiciones que se ejecutan al restaurar.

## Validación y límites de evidencia

Ejecutados en esta revisión:

- 29 regresiones de cabeceras, CSP, cuentas de producción, orígenes, saneado de entradas y JSON seguro, más las pruebas nuevas de operación e inventario: aprobadas, sin omisiones. Reproducción: `python manage.py test webcitt.tests.test_seguridad_produccion.SecurityHeadersTests webcitt.tests.test_seguridad_produccion.ProduccionCuentasTests webcitt.tests.test_endurecimiento.OrigenesTests webcitt.tests.test_endurecimiento.EntradaYHtmlTests webcitt.tests.test_endurecimiento.EjemplosJsonTests webcitt.tests.test_operacion_produccion --noinput`.
- Los casos de recuperación usan ejecutables PostgreSQL simulados. Verifican control de flujo y ausencia de borrados ajenos; no sustituyen restaurar un respaldo real en infraestructura aislada.
- Consulta SQL actual exclusivamente READ ONLY y auditor de repositorio en modo estricto: cero errores y cero colisiones de nombres; seis grupos de duplicados conservados para la revisión de compatibilidad.
- Sintaxis POSIX de los scripts modificados y revisión de los argumentos con la API instalada de Waitress.

La primera ejecución de `pip-audit` falló por la conexión restringida a PyPI (`10013`). El reintento con acceso autorizado sí terminó el 10 de octubre de 2026: `pip-audit -r requirements.txt --no-deps --disable-pip` devolvió código 0 y ningún aviso conocido para las versiones Python fijadas; la evidencia JSON está en `var/auditoria-integral-20261010/dependencias.json`. Esto no cubre la imagen base ni las bibliotecas de navegador, ni garantiza la ausencia de vulnerabilidades. No se modificaron `requirements.txt` ni el entorno virtual de la aplicación; la herramienta quedó en la caché local de auditoría. Repetir los tres escaneos en CI antes de publicar y con cada actualización. Bootstrap 4 conserva el pendiente de migración documentado anteriormente.

Antes de recibir usuarios, faltan las comprobaciones reales de DNS/TLS/proxy, roles web efectivos, SMTP, permisos de volúmenes, firewall, restauración y red lenta. Se añadieron sondas internas de proceso y conexión SQL, con healthcheck de la web en Compose y bloqueo público en el ejemplo de Nginx; su contrato y excepción HTTPS de dos rutas exactas se detallan en [supervisión interna](produccion-linux.md#supervisión-interna). El estado `unhealthy` no autorreinicia el proceso. Añadir alertas privadas de disponibilidad, latencia, saturación, espacio y antigüedad de respaldos. La revisión de controles de seguridad de infraestructura y una prueba de penetración deben usar un alcance acordado; las pruebas unitarias no las reemplazan.

## Fuentes y guías de operación

- [Lista oficial de despliegue Django 5.2](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
- [Parámetros de Waitress 3.0.2](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).
- [Respaldo lógico PostgreSQL 17](https://www.postgresql.org/docs/17/backup-dump.html).
- [Seguridad por filas PostgreSQL 17](https://www.postgresql.org/docs/17/ddl-rowsecurity.html).
- [Almacenamiento WhiteNoise para Django](https://whitenoise.readthedocs.io/en/stable/django.html).
- [Guía del proyecto para Linux](produccion-linux.md) y [seguridad y continuidad](seguridad-continuidad.md).
