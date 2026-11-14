# Despliegue de SLCID en el servidor Linux de la universidad

Para transferir sólo una versión de código y mantener datos/secretos separados, seguir la [entrega e inventario de almacenamiento](almacenamiento-entrega-servidor-2026-10-12.md). No subir la carpeta de desarrollo completa. Fijar `SLCID_VERSION` al commit desplegado: web, migraciones y scheduler comparten imagen; los volúmenes permanecen entre actualizaciones.

Esta guía corresponde a la auditoría del 8 de octubre de 2026. El portal y el backend comparten dominio. CORS permanece cerrado a aplicaciones externas salvo autorización explícita mediante CORS_ALLOWED_ORIGINS. No se ha ejecutado un despliegue en el servidor universitario.

La [auditoría del 10 de octubre](auditoria-seguridad-produccion-2026-10-10.md) amplía el estado de roles/RLS, capacidad y recuperación de esa fecha. El [mantenimiento del 11 de noviembre](mantenimiento-validacion-2026-11-11.md) separó también los roles locales y restringió el puerto de PostgreSQL. No copiar las credenciales de validación a producción; generar las propias del servidor universitario.

## Configuración y secretos

Copiar .env-example a un archivo .env del servidor, fuera de Git y con permisos 600. Completar valores reales; los ejemplos no son credenciales utilizables. Definir como mínimo:

- DJANGO_SETTINGS_MODULE=config.settings_production; DEBUG desactivado por este módulo.
- SECRET_KEY aleatoria de al menos 50 caracteres. Conservarla entre reinicios y respaldarla con acceso restringido.
- ALLOWED_HOSTS con el dominio sin protocolo; CSRF_TRUSTED_ORIGINS y SITE_URL con https:// y el dominio. CORS_ALLOWED_ORIGINS vacío para este despliegue del mismo origen.
- DB_NAME, DB_HOST, DB_PORT y tres pares distintos: DB_USER/DB_PASSWORD para la web; DB_MIGRATION_USER/DB_MIGRATION_PASSWORD para migraciones; DB_BACKUP_USER/DB_BACKUP_PASSWORD para respaldos. Contraseñas aleatorias diferentes de al menos 20 caracteres. Nombres de rol PostgreSQL en minúsculas, letras, números y guion bajo.
- SMTP real: EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL y TLS/SSL según el servicio institucional. Las cuentas locales exigen confirmar el correo.
- TRUSTED_PROXY_IP: IP exacta desde la que Nginx llega a Waitress. Es 127.0.0.1 en instalación nativa; dentro de Docker suele ser la IP de la pasarela de su red. Confirmarla en esa instalación. No se acepta *.
- DB_NETWORK_ISOLATED=true solo cuando la base está en la red privada del servidor/contenedores, sin acceso público. Una base remota requiere DB_SSLMODE=verify-full y DB_SSLROOTCERT.

El aprovisionamiento de preparar_roles_bd requiere un administrador PostgreSQL: crear/alterar BYPASSRLS del rol de respaldo exige superusuario. Estas credenciales se usan exclusivamente en el servicio de migración/aprovisionamiento; nunca en peticiones web.

Cuando Centros usa un propietario sin `CREATEROLE`, el administrador aprovisiona primero sus cuentas web y de respaldo. Después, `preparar_roles_bd --database centros --solo-permisos` verifica los atributos de esas cuentas y concede permisos sobre el esquema; conserva sus contraseñas. El servicio de migraciones usa ese modo para Centros, evitando elevar a su propietario solo para gestionar cuentas globales.

El rol web no puede ser superusuario, propietario de tablas/esquema/base, crear roles/bases/objetos en public ni pertenecer a otros roles. El servicio de migraciones crea el rol web y concede CRUD y uso de secuencias; el rol de respaldo tiene lectura, BYPASSRLS y CREATEDB para ensayar restauraciones. Sus credenciales nunca se entregan a los procesos web, scheduler o microproyectos.

## Base existente y datos

Confirmar que se revocaron los secretos históricos identificados en auditoria-produccion-2026-10-08.md. Aunque los valores locales actuales son distintos, el historial Git conserva el .env antiguo.

Antes de migrar, generar respaldo de PostgreSQL, medios y marca institucional privada. Ensayar la restauración en una base separada. Conservar copias fuera del servidor y verificar recuperación con los responsables universitarios.

En una base existente, DB_MIGRATION_USER debe corresponder al rol propietario actual de los objetos, con capacidad de administrar los roles necesarios; DB_USER debe ser un rol nuevo y restringido. Cambiar POSTGRES_USER en Compose no modifica roles ni contraseñas de un volumen existente. No borrar postgres_data para solucionar permisos. Si los propietarios actuales son diferentes, el DBA debe hacer el traspaso explícito en una copia de ensayo antes de producción.

Las migraciones 0313 y 0314 crean contadores de abuso y seis políticas RLS. No se aplicaron a los datos activos durante esta auditoría. El contenido de ejemplo de los centros sigue excluido en producción; los escenarios operativos locales dependen de DEBUG.

## Con Docker Compose

Para habilitar Centros I+D conservando un único servidor PostgreSQL, utilizar
`docker-compose.centros-compartido.yml` junto a la base. La
[guía de estructura de bases](estructura-bases-datos-docker.md) detalla el
aprovisionamiento previo, los comandos y la alternativa de servidor dedicado.
No crear una base ni un contenedor por laboratorio o centro.

Se requiere Docker Engine y Compose v2 en el servidor Linux. La web corre sin root. PostgreSQL y Waitress publican únicamente en loopback del host.

1. Completar y proteger .env; instalar certificado TLS y DNS.
2. Validar la definición sin imprimir secretos: docker compose config --quiet.
3. Construir la imagen y ejecutar las migraciones: docker compose build y docker compose run --rm migrate. El servicio utiliza exclusivamente el rol de migraciones y provisiona los permisos después del esquema.
4. Iniciar: docker compose up -d. web y scheduler esperan que migrate termine correctamente. La web ejecuta check --deploy, verificar_seguridad_bd y collectstatic antes de servir peticiones.
5. Verificar: docker compose exec web python manage.py check --deploy y docker compose exec web python manage.py verificar_seguridad_bd.
6. Comprobar el respaldo y la restauración que ejecuta backup. Monitorizar sus errores, espacio disponible y retención. Mantener los microproyectos desactivados salvo que se configure su dominio separado y se acepte la operación del servicio con socket Docker.

El servicio migrate recibe las credenciales elevadas; environment las vacía expresamente en web, scheduler y microproyectos. No publicar la salida completa de docker compose config ni docker inspect: puede contener secretos del servidor.

## Sin Docker

Crear un usuario de sistema slcid, clonar la versión aprobada en /opt/slcid, instalar Python 3.11 y PostgreSQL 17 y crear el entorno con uv sync --locked --no-dev. Configurar un servicio oneshot de migración con /opt/slcid/scripts/migrar_produccion.sh, el entorno virtual al principio de PATH y su archivo de variables privado administrado por root. El script requiere DB_MIGRATION_USER y DB_MIGRATION_PASSWORD en el entorno del servicio.

El servicio web usa otro archivo de entorno que contiene solo credenciales web y ejecuta el Python del entorno virtual con scripts/servir_produccion.py. Definir WEB_LISTEN=127.0.0.1:8000 y TRUSTED_PROXY_IP=127.0.0.1. Ejecutar check --deploy, verificar_seguridad_bd y collectstatic antes de iniciar. Ejecutar scripts/docker_scheduler.sh mediante un servicio separado con las mismas credenciales restringidas. Programar los scripts de respaldo con el rol de respaldo, separado de la web.

No utilizar runserver en producción ni cargar un .env mediante eval. Django lee .env automáticamente solo en desarrollo. En producción Compose o el gestor de servicios deben suministrar el entorno; un .env del repositorio no se recarga dentro del proceso web.

## Nginx y HTTPS

La plantilla scripts/nginx/slcid.conf.example contiene el proxy TLS, límites de frecuencia y tamaño de subida. Sustituir el dominio y las rutas del certificado. Ejecutar nginx -t antes de recargar el servicio. Nginx sobrescribe Host, X-Forwarded-For y X-Forwarded-Proto; Waitress solo confía en la IP configurada y en un salto de proxy. Esto mantiene la IP real en el límite de peticiones e impide usar una cabecera enviada por el cliente para eludirlo.

No crear un alias público de /media/: todos los adjuntos pasan por Django para aplicar sus permisos. Los estáticos los entrega WhiteNoise; si se trasladan a Nginx, copiar el resultado completo de collectstatic y mantener rutas/tipos MIME de .mjs. No activar caché compartida de las páginas HTML con nonce CSP ni de archivos privados.

## Supervisión interna

`/salud/vivo/` responde 204 sin consultar la base; `/salud/listo/` ejecuta únicamente `SELECT 1` y devuelve 204 o 503. Solo admiten GET/HEAD, validan `Host`, nunca se almacenan en caché y no publican excepciones ni datos. Estas dos rutas exactas evitan sesiones, autenticación, RLS y módulos funcionales; los controles del resto del sitio conservan su funcionamiento.

Compose comprueba la segunda mediante `scripts/comprobar_salud.py` dentro de la web, cada 30 segundos, con timeout de 5 segundos y tres fallos antes de marcarla `unhealthy`; dispone de 60 segundos iniciales de gracia. La sonda usa HTTP loopback en el puerto 8000 y un Host de `ALLOWED_HOSTS`, sin proxy del entorno, sin seguir redirecciones ni iniciar Django; únicamente 204 cuenta como éxito. El timeout interno de la petición es de 3 segundos. Consultar el estado con `docker compose ps` y ejecutar la sonda manualmente con `docker compose exec web python scripts/comprobar_salud.py`.

Waitress solo confía en la IP exacta de Nginx; una petición loopback no debe fingir provenir de ese proxy. Por ello únicamente `^salud/(?:vivo|listo)/$` queda exenta de redirección HTTPS. Nginx bloquea públicamente `/salud` y `/salud/`; aplicar esas reglas al desplegar. Todas las demás rutas conservan HTTPS obligatorio. Fuera de Compose se puede ejecutar la misma sonda desde el servidor con el entorno del proceso web y su puerto 8000, sin publicar el backend.

El estado `unhealthy` no reinicia por sí solo el contenedor: `restart: unless-stopped` actúa cuando el proceso termina. Configurar alertas y una respuesta operativa antes de recibir usuarios. Estas sondas comprueban el proceso HTTP y la conexión SQL, no sustituyen la revisión de migraciones, SMTP, adjuntos, restauración, saturación ni latencia de las funciones reales.

## Comprobación antes de abrir al público

- Acceso HTTPS con certificado válido, redirección HTTP y hosts ajenos rechazados.
- Registro, correo de verificación, inicio/cierre de sesión y recuperación de contraseña con el SMTP real.
- Con dos usuarios de prueba: reservas, aula, entregas, comprobantes, simulaciones y solicitudes. Intentar abrir los adjuntos del otro usuario mediante sus URL directas debe denegarse.
- Gestión modal, copiar enlaces, reservas de espacios/equipos, acompañamiento y reportes. Revisar la consola del navegador por bloqueos CSP con los recursos reales.
- Recursos interactivos revisados se abren aislados mediante sandbox sin acceso al DOM/sesión del portal. Archivos HTML antiguos sin revisión se descargan como adjuntos. Los mapas y contenidos externos pueden necesitar orígenes específicos autorizados, manteniendo la política estricta del portal.
- Confirmar RLS con el rol web real y verificar que las tareas programadas y respaldos funcionan con sus roles previstos. RLS cubre las seis tablas personales detalladas en la auditoría; la agenda compartida y las restantes tablas conservan autorización de dominio.
- Restaurar un respaldo en una instalación de ensayo y comprobar al menos una reserva y un adjunto. Definir responsables de actualizaciones, monitoreo, certificados y reversión.

No declarar el servicio listo para recibir usuarios hasta superar estas comprobaciones en el servidor real.

Referencias: [lista de despliegue Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [seguridad por filas de PostgreSQL 17](https://www.postgresql.org/docs/17/ddl-rowsecurity.html), [proxy de Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html).

## Límites del proceso web

`WEB_THREADS=8`, `WEB_CONNECTION_LIMIT=100` y `WEB_CHANNEL_TIMEOUT=60` son los valores iniciales. Se pueden configurar sin editar Python; el servidor rechaza hilos fuera de 1–64, canales fuera de 16–1.024, timeout fuera de 15–300 segundos y menos canales que hilos. Cada proceso puede utilizar hasta aproximadamente una conexión PostgreSQL por hilo ocupado: sumar procesos, tareas y administración antes de cambiar capacidad. Los canales no expresan cuántos usuarios soporta el sistema. Las cabeceras admiten hasta 32 KiB y el cuerpo conserva 64 MiB.

El timeout de canal limita inactividad de red; no cancela una función lenta. Validar `nginx -t` y medir la mezcla real de cursos, agenda, PDFs y adjuntos antes de aumentar procesos o publicar cifras de capacidad.
