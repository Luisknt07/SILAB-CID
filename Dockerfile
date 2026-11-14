FROM python:3.11-slim AS aplicacion

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings_production

WORKDIR /app

# requirements.txt se genera desde uv.lock (fijado y con hashes); pip exige
# que cada paquete coincida con su hash.
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --require-hashes -r /app/requirements.txt

# Copiar solo las raíces de la aplicación. Un archivo temporal nuevo en la
# raíz del checkout no debe terminar accidentalmente dentro de la imagen.
COPY manage.py /app/manage.py
COPY config/ /app/config/
COPY apps/ /app/apps/
COPY templates/ /app/templates/
COPY locale/ /app/locale/
COPY scripts/ /app/scripts/

# La aplicacion no corre como root y solo escribe bajo var/: adjuntos,
# estaticos recopilados, caches, registros y la marca institucional privada.
RUN groupadd --system slcid \
    && useradd --system --gid slcid --home-dir /app --shell /usr/sbin/nologin slcid \
    && mkdir -p /app/var/media /app/var/static /app/var/cache /app/var/logs /app/var/private/institutional-brand \
    && chown -R slcid:slcid /app/var

USER slcid

EXPOSE 8000

ENTRYPOINT ["sh", "/app/scripts/docker_web.sh"]

# Servicio de microproyectos: la misma aplicacion con el cliente de Docker. Solo
# este servicio recibe el socket; la web nunca lo tiene (docs/microproyectos-django.md).
FROM aplicacion AS microproyectos
USER root
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
USER slcid
ENTRYPOINT ["python", "manage.py", "atender_microproyectos"]

# Imagen por defecto: web y programador de tareas, sin cliente de Docker.
FROM aplicacion AS web
