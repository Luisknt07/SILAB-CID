> Para el despliegue actual en Linux, seguir [produccion-linux.md](produccion-linux.md). Esa guía actualiza la separación de roles PostgreSQL, migraciones, proxy y controles de arranque; prevalece sobre los ejemplos anteriores de este documento.

# Despliegue de producción

La configuración local continúa usando `config.settings`. En producción debe
definirse:

```text
DJANGO_SETTINGS_MODULE=config.settings_production
```

Antes de iniciar el servicio:

1. Copiar `.env-example` a un archivo de entorno fuera del repositorio.
2. Generar una `SECRET_KEY` aleatoria de al menos 50 caracteres.
3. Reemplazar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL` por el
   dominio HTTPS real.
4. Configurar la base PostgreSQL y las credenciales SMTP.
5. Declarar `DB_NETWORK_ISOLATED=true` para la red privada de Docker o usar
   `DB_SSLMODE=verify-full` junto con `DB_SSLROOTCERT` para una base externa.
6. Configurar `BACKUP_HOST_DIR` fuera del volumen de PostgreSQL (predeterminado
   `./var/backups`).
7. Ejecutar `python manage.py migrate` y `python manage.py collectstatic --noinput`.
8. Ejecutar `python manage.py check --deploy --settings=config.settings_production`.

## Dependencias reproducibles

`pyproject.toml` y `uv.lock` son la única fuente de dependencias. El archivo
`requirements.txt` que instala la imagen Docker se genera desde el lock, con
todas las dependencias transitivas fijadas y con hashes, y `pip` lo instala con
`--require-hashes`; un paquete alterado en el índice no se instala. Las
herramientas de desarrollo (`ruff`) pertenecen al grupo `dev` y no entran en la
imagen. Después de cambiar una dependencia:

```powershell
uv lock
uv export --no-dev --no-emit-project --format requirements.txt -o requirements.txt
uvx pip-audit -r requirements.txt
```

La imagen ejecuta la aplicación con el usuario de sistema `slcid`, sin
privilegios; solo puede escribir en adjuntos, estáticos recopilados, la caché
de gráficos y la marca institucional privada. En producción los adjuntos se
guardan con permisos `640` y sus directorios con `750`, y el registro de
seguridad y de errores de petición sale siempre por la salida estándar del
servicio, sin depender de `ADMINS`.

`settings_production` activa redirección HTTPS, HSTS, cookies seguras, evita la
enumeración de cuentas, restringe el anidamiento a recursos del mismo origen y
publica una política de seguridad de contenidos. La aplicación no iniciará si
la clave, los hosts o los orígenes CSRF no están configurados correctamente.

La plataforma utiliza `X_FRAME_OPTIONS=DENY`. Solo la ruta controlada que sirve
recursos multimedia internos responde con `SAMEORIGIN`; nunca se utiliza
`ALLOWALL`.

## Ejecución

En Windows, después de completar el entorno, puede iniciarse Waitress detrás
del proxy HTTPS con:

```powershell
.\scripts\iniciar_produccion.ps1
```

Con Docker, `docker compose up --build` inicia PostgreSQL, la aplicación web,
el procesador periódico de reservas y los respaldos de base y adjuntos. El
archivo `.env` no se copia en la imagen y debe contener valores reales antes de
levantarla. PostgreSQL y la aplicación se enlazan a `127.0.0.1`; el proxy es el
unico servicio publico.

Waitress escucha HTTP internamente. La terminación TLS/HTTPS debe realizarla el
proxy institucional (IIS, Nginx, Apache o el balanceador disponible), enviando
`X-Forwarded-Proto: https`.

La politica de copias, el ensayo de restauracion, RPO/RTO y la ruta hacia PITR
se detallan en [seguridad-continuidad.md](seguridad-continuidad.md).
