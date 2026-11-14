# Navegador remoto para sitios que prohíben incrustarse

Algunos sitios enlazados como recursos (por ejemplo, labxchange.org con
`X-Frame-Options: DENY`) no permiten mostrarse dentro de otras páginas. Para esos
recursos puede activarse **«Usar navegador remoto»** en la ficha del recurso: el
visor abre el sitio en un Chromium que corre en el servidor y transmite su pantalla.

## Comportamiento

- Solo se usa si el sitio prohíbe incrustarse; si lo permite, se muestra directo.
- Solo para usuarios con sesión iniciada. Los visitantes anónimos ven el botón
  «Abrir sitio en una pestaña nueva», que siempre está disponible.
- **Cupo limitado:** `NAVEGADOR_REMOTO_MAX_SESIONES` sesiones simultáneas en todo el
  servidor (3 por defecto) y una por persona; abrir otro sitio libera la anterior.
  Sin cupo, el visor lo indica y ofrece abrir el sitio en otra pestaña.
- **Bajo demanda:** la sesión se crea al abrir el recurso y se libera al salir de él.
  El servicio también la cierra tras `NAVEGADOR_REMOTO_INACTIVIDAD_MIN` minutos sin
  actividad (5) o al cumplir `NAVEGADOR_REMOTO_DURACION_MIN` (30).
- Chromium solo navega por el dominio del recurso y por los reproductores de
  `NAVEGADOR_REMOTO_DOMINIOS_EXTRA` (YouTube y Vimeo); sin herramientas de
  desarrollo, descargas, impresión ni perfiles. Así el servidor no sirve de
  navegador libre ni alcanza la red interna.
- «Sesiones de navegador remoto», en el admin, lista las sesiones y permite cerrarlas.

## Funcionamiento

El portal solo registra la sesión. El servicio `atender_microproyectos` (el único
con acceso a Docker) crea el contenedor `citt-navegador-<token>` con la imagen
`NAVEGADOR_REMOTO_IMAGEN` (`lscr.io/linuxserver/chromium`), le copia la política de
Chromium, lo une a la pasarela y comprueba que responda. La pasarela publica cada
sesión en `navegador-<token>.<dominio>` con WebSocket para la transmisión. El token
de 24 caracteres aleatorios es la llave de la sesión: solo lo recibe su usuario.

## Recursos del servidor

Cada sesión reserva hasta `NAVEGADOR_REMOTO_MEMORIA` (2 GB) y 1,5 CPU; al iniciar
usa unos 300 MB. Con el cupo por defecto, prevea 6 GB de RAM libres. La imagen
ocupa 1,2 GB y se descarga en la primera sesión: conviene descargarla antes con
`docker pull lscr.io/linuxserver/chromium:latest`.

## Producción

Usa la misma pasarela, dominio y servicio que los microproyectos
(`docs/microproyectos-django.md`). En el proxy frontal, el bloque debe aceptar
también los subdominios del navegador y reenviar WebSocket:

```nginx
server_name ~^(microproyecto-\d+|navegador-[a-f0-9]+)\.apps\.ejemplo\.edu\.ec$;
location / {
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto https;
  proxy_read_timeout 3600s;
  proxy_pass http://127.0.0.1:19000;
}
```

Para desactivarlo sin quitar la opción de los recursos: `NAVEGADOR_REMOTO_MAX_SESIONES=0`.
