# Microproyectos Django: carga, puesta en marcha y producción

En el editor de recursos seleccione **Microproyecto Django (ZIP con SQLite)** en
«Tipo adjunto». El archivo mantiene nombre, carpeta, URL compartible y permisos
de pertenencia a la unidad. La visualización tiene un tratamiento propio:
no pasa por el extractor de sitios estáticos ni sirve el ZIP, Python o SQLite
como archivos descargables. Los HTML y ZIP estáticos conservan su tratamiento.

El paquete debe contener un único `manage.py` y `requirements.txt`, en la raíz
o dentro de una carpeta. Puede contener `db.sqlite3`. Se excluyen del entorno
`.venv`, `venv`, `.git`, `node_modules`, `.env*` y cachés Python. Se rechazan rutas
con escape, enlaces simbólicos y paquetes de más de 20.000 entradas o 512 MB
descomprimidos. El ZIP original se conserva como adjunto controlado, no se
publica. No incluir secretos ni datos que no deban formar parte del proyecto.
`manage.py` debe declarar su configuración con
`os.environ.setdefault('DJANGO_SETTINGS_MODULE', '...')`; se lee sin ejecutarlo.

## Puesta en marcha desde el admin

Subir un ZIP **no ejecuta su código** en CITT. La puesta en marcha tiene dos pasos
separados:

1. **El admin registra la solicitud.** Guardar un ZIP nuevo no crea un contenedor
   por defecto. Quien tenga el permiso «Puede poner en marcha microproyectos
   Django» (los superusuarios lo tienen) revisa el paquete y utiliza **Poner en
   marcha**. En «Entorno del microproyecto»
   aparecen el estado y el botón **Poner en marcha / Reintentar / Volver a
   desplegar**; el estado se actualiza solo mientras la página está abierta.
2. **El servicio `atender_microproyectos` la atiende.** Es el único proceso con
   acceso a Docker y no recibe tráfico web: construye la imagen, arranca el
   contenedor, comprueba que responda a través de la pasarela y deja constancia
   en «Puestas en marcha de microproyectos» (quién lo pidió, cuándo y resultado).

Solo se ponen en marcha recursos activos, públicos y en carpetas públicas
activas, con todos sus ancestros activos; la
aplicación conserva su propio inicio de sesión. Un fallo muestra su causa en la
ficha (por ejemplo, las últimas líneas del registro) y se reintenta con el botón;
guardar de nuevo la misma versión no la vuelve a encolar. Si el paquete omite
una dependencia en `requirements.txt`, agréguela en **Dependencias adicionales**
(`nombre==versión`, separadas por espacios; no se aceptan URLs ni opciones de pip).

Para habilitar expresamente el encolado al guardar, configurar
`MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=true`. Por defecto es `false`, sin afectar
aplicaciones existentes ni la solicitud manual. Una aplicación independiente
consume recursos; no se despliega una por cada nuevo laboratorio o contenido.

El servicio también retira los contenedores de recursos eliminados, ocultos o que
dejaron de ser públicos (conserva su volumen de datos), y migra a la pasarela los
proyectos de la versión anterior que usaban un puerto propio (`-visor`).

### Arquitectura y aislamiento

- Cada proyecto corre en `slcid-TITULO-UNIDAD-ID`, con alias DNS estable
  `citt-microproyecto-ID`: usuario no privilegiado,
  sistema de archivos de solo lectura, 512 MB, 1 CPU, límite de procesos y una
  red interna sin salida a Internet. Solo monta su volumen `citt-microproyecto-ID-datos`.
- Una única pasarela Nginx, `slcid-pasarela-aplicaciones-laboratorios`, sin código de los
  paquetes, escucha en `127.0.0.1:MICROPROYECTOS_PUERTO_PASARELA` y dirige
  `microproyecto-ID.<dominio>` al contenedor de ese proyecto.
- Ningún contenedor monta el repositorio, las credenciales o la base de CITT.
  La construcción de la imagen sí necesita acceso a los repositorios de paquetes.

La [guía de nombres Docker](nombres-contenedores-docker.md) documenta los nombres
actuales, la adopción de la pasarela anterior y la conservación de redes,
volúmenes y enlaces aunque se edite el título del recurso.
La [organización local de aplicaciones](organizacion-aplicaciones-2026-10-12.md)
registra el WMS operativo y el archivo privado de las dos pruebas anteriores.

Cada origen `microproyecto-ID.<dominio>` es distinto del portal y tiene cookies
propias. La página pública del recurso muestra el proyecto solo dentro del visor;
su dirección directa se comparte únicamente desde la ficha del administrador
(«Abrir proyecto» en «Entorno del microproyecto»).

## Desarrollo local

Con Docker Desktop iniciado, en otra consola:

```powershell
.\scripts\iniciar_microproyectos.ps1
```

Los proyectos quedan en `http://microproyecto-ID.localhost:19000/`. Para atender
la cola una sola vez: `manage.py atender_microproyectos --una-vez`. Para poner en
marcha un recurso de inmediato, sin cola: `manage.py desplegar_microproyecto ID`
(`--project-settings` solo si `manage.py` no declara su configuración).

## Producción

El servicio necesita, además del código de esta rama:

1. **Dominio comodín y certificado.** Un DNS `*.apps.ejemplo.edu.ec` (o el
   subdominio elegido) apuntando al servidor y un certificado TLS comodín para él.
2. **Proxy frontal** (el mismo que publica CITT): reenvía `*.apps.ejemplo.edu.ec`
   a `http://127.0.0.1:19000` conservando `Host` y enviando
   `X-Forwarded-Proto: https`. Ejemplo en Nginx:

   El mismo bloque sirve al navegador remoto (`docs/navegador-remoto.md`), que
   además necesita reenviar WebSocket:

   ```nginx
   server {
     listen 443 ssl;
     server_name ~^(microproyecto-\d+|navegador-[a-f0-9]+)\.apps\.ejemplo\.edu\.ec$;
     ssl_certificate     /ruta/comodin.crt;
     ssl_certificate_key /ruta/comodin.key;
     client_max_body_size 20m;
     location / {
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-Proto https;
       proxy_read_timeout 3600s;
       proxy_pass http://127.0.0.1:19000;
     }
   }
   ```
3. **Variables en `.env`:** `MICROPROYECTOS_DOMINIO=apps.ejemplo.edu.ec`
   (sin él, la puesta en marcha queda deshabilitada y el admin lo indica).
   Opcionales: `MICROPROYECTOS_PUERTO_PASARELA` (19000), `MICROPROYECTOS_ESQUEMA`
   (`https`) y `MICROPROYECTOS_PUERTO_PUBLICO` (vacío).
4. **El servicio en marcha**, según cómo se despliegue CITT:
   - Docker Compose: `docker compose --profile microproyectos up -d --build`.
     El servicio `microproyectos` recibe el socket de Docker; indique en
     `DOCKER_GID` el grupo propietario de `/var/run/docker.sock`
     (`stat -c %g /var/run/docker.sock`). La web y el programador no lo reciben.
   - Windows con Waitress: `.\scripts\iniciar_microproyectos.ps1 -Produccion`
     como tarea o servicio de la cuenta que ejecuta Docker.
5. **Permisos:** asigne «Puede poner en marcha microproyectos Django» solo a quien
   revise los paquetes antes de publicarlos.

Validación: suba un ZIP en una carpeta pública; la ficha debe pasar de «En cola»
a «En funcionamiento» con el enlace `https://microproyecto-ID.apps.ejemplo.edu.ec/`,
y la página pública del recurso debe mostrarlo dentro del visor.

El socket de Docker equivale a control del servidor: por eso lo tiene solo un
servicio que no publica puertos ni procesa peticiones web. Como refuerzo, puede
interponerse un proxy del socket que limite la API a contenedores, imágenes y redes.
Este mecanismo no es un servicio de ejecución de código hostil: los paquetes deben
revisarse antes de ponerlos en marcha.

## Versiones y datos

Solo se copia la SQLite inicial cuando todavía no existe `/data/db.sqlite3`. Cada
arranque crea una copia `antes-de-migrar.sqlite3` antes de aplicar migraciones.
Reemplazar el ZIP encola la nueva versión; el hash evita mostrar una versión
anterior como si fuera la nueva. La reconstrucción conserva el volumen. La copia
previa complementa, no sustituye, backups externos. Si falla, la versión anterior
ya fue retirada: corrija y reintente desde la ficha.

## Proyectos de prueba

- Recurso 88, «WMS UPEC - microproyecto Django» (Laboratorio de Realidad
  Extendida): solo publica `/admin/`; la portada la añade el entorno cuando el
  paquete no define `/`. El admin usa sus propias credenciales, no las de CITT.
- Recurso 89, «WMS 2 - prueba independiente»: declara `unfold` sin su dependencia,
  resuelta con `django-unfold==0.91.0` en «Dependencias adicionales». No incluye
  SQLite; las migraciones crean su base. Su cuenta local de prueba está en
  `var/microproyectos/89/credenciales-prueba.md`, fuera de Git.
- Recurso 90, «wms» (Laboratorio de Logística, Transporte y Cadena de Suministro):
  con su propia SQLite.
