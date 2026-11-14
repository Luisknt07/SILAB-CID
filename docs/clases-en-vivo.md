# Clases en vivo dentro del aula

Cada clase en vivo elige su sala: la de la plataforma (por defecto), una transmisión de YouTube Live con su chat, un
enlace externo (Zoom, Meet o Teams), Teams transmitido por YouTube Live o solo presencial. La sala de la plataforma
abre la videollamada dentro del aula con uno de tres servicios, que conecta quien administra la plataforma en
**Clases en vivo · Servicio** (`/cursos/vivo/servidor/`), sin variables de entorno ni reinicios.

| Servicio | Instalar algo | Costo | Asistencia | Grabación |
| --- | --- | --- | --- | --- |
| Digital Samba (por defecto) | No: está en la nube (Unión Europea) | 10 000 minutos-participante gratis al mes, sin tarjeta | Quien modera la registra al terminar con un botón | Automática; el mismo botón la publica y la lección la reproduce |
| Daily | No: está en la nube | 10 000 minutos-participante gratis al mes, pero exige registrar una tarjeta antes de abrir salas; luego 0,004 USD por minuto-participante | Quien modera la registra al terminar con un botón (la plataforma la descarga de Daily) | De pago en Daily; no se activa |
| BigBlueButton | Sí: servidor propio o de un proveedor | Solo el servidor | Llega sola al terminar la clase | Llega sola y se publica en la lección |

Fuentes: daily.co/pricing/video-sdk, dashboard.daily.co/billing, docs.daily.co, docs.bigbluebutton.org (revisadas el
4 de octubre de 2026).

## Digital Samba, sin instalar nada ni tarjeta

1. Crear una cuenta gratuita en digitalsamba.com. El subdominio del equipo (por ejemplo `laboratorios`) será la
   dirección de las salas.
2. En el panel, sección **Team**, copiar el **Team ID** y la **Developer key**.
3. En la plataforma, **Clases en vivo · Servicio**: elegir Digital Samba, pegar ambos y guardar. La plataforma comprueba
   las credenciales y toma el dominio del equipo (la API no lo publica: sale del enlace de acceso de una sala; si el
   equipo no tiene salas, crea una de prueba y la borra).

Cada clase con sala de la plataforma crea al entrar la primera persona su sala privada `citt-leccion-<id>`, en español,
con los roles del equipo `teacher` (quien gestiona la unidad) y `student` (inscritos, que hablan y comparten pantalla) y
grabación automática. Cada persona entra con un JWT firmado con la Developer key (HS256) con su nombre, su identificador
y su rol. Al terminar, quien modera pulsa **Registrar la asistencia y publicar la grabación**: la plataforma descarga los
participantes de la sala y guarda la grabación lista más reciente, que la lección reproduce pidiendo en el momento el
enlace temporal del MP4 (`/recordings/<id>/download`).

Fuentes: digitalsamba.com/pricing, docs.digitalsamba.com/reference/rest-api (revisadas el 4 de octubre de 2026).

## Daily, sin instalar nada

1. Crear una cuenta en daily.co y registrar una tarjeta en **Billing**: sin ella, la sala muestra «Missing payment
   method». Solo cobra lo que pase de los 10 000 minutos del mes.
2. En el panel de Daily, sección **Developers**, copiar la **API key**.
3. En la plataforma, **Clases en vivo · Servicio**: elegir Daily, pegar la clave y guardar. La plataforma comprueba la
   clave y toma el dominio de la cuenta (por ejemplo `upec.daily.co`), al que el aula deja usar cámara, micrófono y
   pantalla compartida.

Desde ahí, cada clase con sala de la plataforma crea su sala privada en Daily al entrar la primera persona. Cada
inscrito entra con un acceso firmado con su nombre; quien gestiona la unidad entra como moderador. Al terminar, quien
modera pulsa **Registrar la asistencia de la clase** en la sala.

## BigBlueButton, con servidor

Requisitos de BigBlueButton 3.0 (docs.bigbluebutton.org/administration/install): Ubuntu 22.04 dedicado, 8 núcleos,
16 GB de memoria, 500 GB de disco con grabaciones, 250 Mbit/s simétricos, puertos TCP 80/443 y UDP 16384–32768, y un
dominio con certificado. Se instala con el instalador oficial `bbb-install.sh`; al terminar, `sudo bbb-conf --secret`
muestra la dirección y el secreto que se pegan en la misma pantalla de la plataforma. Un proveedor administrado entrega
esos dos datos sin instalar nada en la universidad.

## Microsoft Teams

Teams no se puede incrustar en el aula: Microsoft impide abrir `teams.microsoft.com` dentro de otra página. La única vía
para incrustarlo es Azure Communication Services, que cobra por minuto, exige configurar el tenant y hace entrar a las
personas como invitadas.

Lo que sí aprovecha las cuentas institucionales es crear la reunión desde la plataforma con Microsoft Graph: la clase
se abre en Teams (pestaña o aplicación) y cada estudiante entra con su cuenta de la UPEC sin escribir nada; la
asistencia se descarga del informe de asistencia de Teams. Para construirlo, TI de la universidad debe:

1. Registrar una aplicación en Microsoft Entra ID del tenant de la UPEC.
2. Concederle los permisos de aplicación `OnlineMeetings.ReadWrite.All` y `OnlineMeetingArtifact.Read.All`, con
   consentimiento de administrador.
3. Crear una directiva de acceso de aplicación (application access policy) que la autorice a crear reuniones en nombre
   de la cuenta organizadora de las clases.
4. Entregar el identificador del tenant, el de la aplicación, su secreto y la cuenta organizadora.

### Teams transmitido por YouTube Live (disponible ya)

La sala **Microsoft Teams transmitido por YouTube Live** muestra la clase dentro del aula sin incrustar Teams: el
docente da la clase en una reunión de Teams y la transmite a YouTube Live con la aplicación **Custom Streaming** de la
reunión (dirección y clave de transmisión de YouTube Studio). En la lección se pegan dos enlaces: el de la reunión de
Teams, para quien quiera hablar o compartir pantalla con su cuenta institucional, y el de la transmisión de YouTube Live,
que el aula muestra con su chat.

- TI debe activar **Live streaming** en Centro de administración de Teams › Reuniones › Directivas de reunión
  (`Set-CsTeamsMeetingPolicy -Identity Global -LiveStreamingMode Enabled`). El organizador necesita licencia
  Office 365 A3 o A5. La salida es de 720p a 30 cuadros por segundo.
- Al terminar la clase, YouTube archiva la transmisión con el mismo enlace y la lección la muestra como grabación sin
  hacer nada.
- Para mostrar la grabación de Teams en su lugar: en Stream, **Compartir › Insertar**, y pegar en **Grabación de la
  clase** la dirección `https://<tenant>.sharepoint.com/.../_layouts/15/embed.aspx?...` del código. La ve quien tenga
  permiso en Stream (por ejemplo, «personas de la UPEC»). Traerla sola necesita la aplicación de Graph descrita arriba.

Fuente: learn.microsoft.com/microsoftteams/stream-teams-meetings (revisada el 4 de octubre de 2026).

Una reunión de Teams también se puede usar en cualquier clase con la opción **Enlace externo**.
