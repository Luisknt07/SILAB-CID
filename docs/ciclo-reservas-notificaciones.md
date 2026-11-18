# Ciclo operativo y notificaciones de reservas

Una solicitud confirmada no se contabiliza como uso efectivo hasta que el
laboratorista la cierre como `completada`. Cuando el horario termina, el panel
muestra la reserva en **pendientes de cierre** y permite registrar una de estas
resoluciones:

- atendida y completada;
- el usuario no se presentó;
- no atendida por la unidad, con motivo;
- reprogramada mediante la edición controlada.

Las solicitudes todavía pendientes al finalizar su horario pasan a `vencida`
y no se contabilizan como atención efectiva.

## Valoración de la atención (satisfacción de los usuarios)

- **Quién:** solo quien hizo la reserva, una vez por reserva. Nadie valora por
  otro, tampoco el personal de la unidad.
- **Cuándo:** cuando la unidad cerró la reserva como `completada` con resultado
  «atendida y completada». Una reserva pendiente, cancelada, rechazada, vencida,
  sin presentación o no atendida no se valora.
- **Dónde:** en **Mis reservas**, la fila de la reserva atendida muestra el
  botón «Valorar atención»: valoración general de 1 a 5 (obligatoria), tres
  aspectos opcionales (atención del personal, estado de los equipos,
  instalaciones) y un comentario de hasta 500 caracteres. Después la fila
  muestra la valoración y ya no el botón. No se envían correos ni avisos.
- **Dónde se consulta:** en el Centro de reportes de la unidad, familia
  «Seguimiento y trazabilidad», consulta **Satisfacción de los usuarios**
  (pantalla, PDF, Excel y Word). Para el rango pedido, por fecha de la reserva:
  respuestas, tasa de respuesta sobre las reservas atendidas, promedio general
  y por aspecto, distribución de 1 a 5, respuestas por mes y comentarios con su
  fecha y valoración, sin el nombre ni la reserva de quien los escribió. La
  consulta se ofrece en el expediente solo si la unidad tiene valoraciones.
- **Rastro:** la auditoría de la unidad registra que el solicitante valoró la
  reserva; no guarda el comentario ni las puntuaciones.
- La valoración no alimenta metas, notas de documentos ni páginas públicas.

## Qué automatiza el proceso

El comando genera, de forma idempotente:

- recordatorio al usuario dentro de las 24 horas previas;
- segundo recordatorio dentro de las 2 horas previas;
- aviso de cierre operativo al responsable cuando termina la reserva;
- vencimiento de solicitudes que terminaron sin aprobación;
- aviso al administrador cuando una reserva activa sigue sin responsable;
- diagnóstico preventivo de equipos fuera de servicio, espacios cerrados,
  licencias agotadas, bloqueos y stock proyectado insuficiente;
- reintento de correos fallidos sin duplicar el aviso interno.

Los avisos dirigidos al personal abren la bandeja correspondiente y, cuando la
reserva está en la página visible, despliegan directamente su panel de gestión.
El diagnóstico considera por defecto los próximos 30 días; puede modificarse
con `RESERVATION_OPERATIONAL_ALERT_DAYS`.

El proceso nunca marca automáticamente como atendida, no presentada o no
atendida una reserva confirmada. Cuando termina el horario conserva su estado
y exige que el personal registre el resultado. Solo las reservas cerradas como
`completada` alimentan utilización, asistentes efectivos, ingresos y reportes
de atención efectiva.

Cada correo registra el número y la fecha del último intento. Se detiene al
alcanzar `RESERVATION_EMAIL_MAX_ATTEMPTS`.

Antes de entregar, el proceso reclama el intento bajo bloqueo de la notificación.
Dos programadores concurrentes no envían el mismo aviso a la vez: el segundo ve
el intento reciente y lo deja para el intervalo de recuperación si el primero
no consigue completar la entrega.

## Configuración del correo

El comprobante HTML se crea y queda consultable en **Mis reservas** aunque el
correo todavía no esté configurado. El backend local de consola ya no se marca
como una entrega real: conserva el aviso como pendiente hasta habilitar el
servicio institucional.

La lista completa de datos que debe entregar la Dirección de TIC y el
procedimiento de activación están en
[`configuracion-correo-transaccional.md`](configuracion-correo-transaccional.md).

Copie en el `.env` las variables de `.env-example` y reemplace únicamente los
valores de despliegue. La contraseña SMTP no debe guardarse en Git.

Variables principales:

- `EMAIL_BACKEND`
- `EMAIL_HOST`, `EMAIL_PORT`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`

La verificación nunca presenta el backend de consola como una entrega real:

```powershell
python manage.py verificar_correo_reservas --enviar --destinatario usuario@upec.edu.ec
```

Para inspeccionar el ciclo automático sin modificar reservas ni crear avisos:

```powershell
python manage.py procesar_recordatorios_reservas --simular
```

El diagnóstico también puede limitarse a una unidad mediante su slug:

```powershell
python manage.py procesar_recordatorios_reservas --unidad planta-piloto-lacteos --simular
```
- `EMAIL_USE_TLS`, `EMAIL_TIMEOUT`
- `DEFAULT_FROM_EMAIL`, `SITE_URL`
- `RESERVATION_EMAIL_MAX_ATTEMPTS`
- `RESERVATION_EMAIL_RETRY_MINUTES`
- `RESERVATION_OPERATIONAL_ALERT_DAYS`

En desarrollo, el backend de consola solo muestra el mensaje en la terminal.
No lo entrega a una bandeja real. Para inspeccionar la configuración sin enviar:

```powershell
.\.venv\Scripts\python.exe manage.py verificar_correo_reservas
```

Cuando las credenciales institucionales estén configuradas, se puede realizar
una prueba controlada:

```powershell
.\.venv\Scripts\python.exe manage.py verificar_correo_reservas --enviar --destinatario usuario@upec.edu.ec
```

## Ejecución manual

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios_reservas
```

Para procesar estados y avisos internos sin intentar correos:

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios_reservas --sin-correo
```

Para ejecutar vencimientos, recordatorios, riesgos, reintentos y avisos de guías
exclusivamente en una unidad:

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios_reservas --unidad planta-piloto-lacteos
```

Un slug inexistente detiene el comando antes de modificar datos. Omitir
`--unidad` conserva el recorrido institucional usado por los programadores ya
instalados. Este alcance no constituye todavía una suspensión comercial de la
capacidad de reservas.

## Programador de tareas de Windows

Ejecute PowerShell con permisos para registrar tareas y, desde la raíz del
proyecto, instale el proceso cada 15 minutos:

```powershell
.\scripts\instalar_tarea_recordatorios.ps1
```

Mientras no existan credenciales SMTP verificadas, puede instalarlo solo para
el ciclo interno:

```powershell
.\scripts\instalar_tarea_recordatorios.ps1 -SinCorreo
```

La tarea usa el entorno virtual del proyecto, impide ejecuciones simultáneas y
escribe el resultado en `var/logs/recordatorios-reservas.log`.

Para revisar la tarea:

```powershell
Get-ScheduledTask -TaskName 'CITT - Recordatorios de reservas'
```

Para retirarla:

```powershell
Unregister-ScheduledTask -TaskName 'CITT - Recordatorios de reservas'
```
