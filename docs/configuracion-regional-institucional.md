# Configuracion regional institucional

Quinto bloque de M02.1, desde edca93a6. La configuracion publica de idioma y
zona se separa de la operacion de reservas. No requiere nuevas tablas ni
migraciones. Cada despliegue tiene una zona institucional; la zona del
navegador no decide la fecha ni el horario de la reserva.

## Configuracion por instalacion

```dotenv
INSTITUTION_LANGUAGE_CODE=es-ec
INSTITUTION_TIME_ZONE=America/Guayaquil
```

Son los predeterminados para UPEC y tambien para instalaciones custom que
ya funcionaban con esos valores. Cambiar el perfil de identidad no cambia
silenciosamente la interpretacion de sus agendas. Ejemplos explicitos:

| Institucion | Idioma | Zona |
| --- | --- | --- |
| UPEC | es-ec | America/Guayaquil |
| Centro en Colombia | es-co | America/Bogota |
| Centro en Espana | es | Europe/Madrid |
| Instalacion con agenda UTC | en-gb | UTC |

El idioma admite codigo principal, escritura opcional y region opcional
(por ejemplo zh-hant-tw o es-419), con traduccion Django o fallback al idioma
principal disponible. La zona debe existir en ZoneInfo/IANA instalado; no
admite rutas relativas o codigo. Valores estructuralmente invalidos o idiomas
sin soporte conocido fallan con ImproperlyConfigured antes de cargar modelos.
El check slcid.E005 valida tambien settings sobrescritos y obliga a conservar
USE_TZ/USE_I18N. Un despliegue debe ejecutar manage.py check al arrancar.

Idioma configura metadatos HTML, formatos de fecha de calendarios y
traducciones de componentes Django. Los textos editoriales y muchas etiquetas
de negocio siguen en espanol: este bloque no entrega traduccion completa del
portal, selector por usuario ni gestion de contenido multilingue. Los numeros
para JavaScript siguen sin localizar, y JSON/ISO/CSV conservan sus contratos.

## Propiedad y consumidores

- apps/core/regional.py: contrato inmutable y conversion de horarios civiles,
  sin Django ni acceso a datos.
- config/regional.py: lectura del entorno y validacion temprana. Solo datos
  publicos; sin credenciales ni configuracion de acceso.
- apps/core/presentation/regional.py: adaptadores Django y contexto HTML.
- apps/core/presentation/auditoria_regional.py: conteos sobre agenda existente.
- regional_institucion.js: idioma y zona institucional; calcula hoy mediante
  Intl en cada uso. Fechas civiles se representan sin convertirlas a UTC en
  el navegador, para no desplazar el dia elegido.

Las propiedades fecha_hora_inicio/fin de Reserva interpretan sus campos civiles
con la zona predeterminada institucional, incluso si un contexto de ejecucion
activa otra zona. La validacion de fecha pasada y el fallback de duracion usan
la fecha institucional, en lugar del reloj local del sistema operativo.
Calendario, resumen del asistente y fechas de registro en tarjetas/exportacion
consumen la misma configuracion. Reportes y comprobantes existentes usan
localtime Django; sus timestamps se mantienen en UTC. No se reescriben fechas
publicadas, snapshots, tarifas o permisos.

## Cambios de hora y reservas

La agenda existente almacena fecha y horas locales separadas y no conserva
fold. Por eso una reserva nueva no puede distinguir las dos ocurrencias de
una hora duplicada al terminar el horario de verano. La API y validacion del
modelo rechazan extremos inexistentes/duplicados e intervalos diarios que
atraviesan el salto horario, con un mensaje para seleccionar otro intervalo.
La comprobacion se realiza para todas las fechas de una programacion antes
de escribir reservas. La API rechaza timestamps con offset: recibe horarios
civiles de la institucion, no horarios del dispositivo.

Servicios convierten los extremos de su fecha programada y plazo de entrega
con esa zona; un plazo de varios dias puede atravesar horario de verano, sin
confundir la duracion estimada del trabajo con horas de calendario.

Los registros historicos se pueden seguir leyendo. No se reparan ni eliminan
silenciosamente al activar una zona diferente. El calendario todavia puede
mostrar bloques durante transiciones; la API impide confirmarlos. Ofrecer dos
ocurrencias de una hora repetida requeriria contrato y modelo que almacenen el
offset/fold, junto con una migracion validada y su recuperacion.
Objects.create, bulk y SQL no ejecutan clean automaticamente: cualquier nueva
entrada debe usar la validacion compartida antes de escribir, como la API
actual y los formularios del administrador.

## Auditar antes de cambiar la zona

Ejecutar bajo la configuracion actual, antes de editar el entorno:

```powershell
.venv/Scripts/python.exe manage.py auditar_configuracion_regional
.venv/Scripts/python.exe manage.py auditar_configuracion_regional --zona-horaria UTC
```

Admite --database. Devuelve solo conteos de reservas, horarios incompletos,
horarios no representables y reservas cuyo instante UTC cambiaria. Sale con
error si hay conflictos o cambios de instante; no realiza escrituras ni
muestra personas. En UPEC, 103 reservas auditadas: cero incompletas, cero no
representables, cero cambios con su zona actual.

Cambiar la zona no convierte DateField/TimeField: conservan sus valores civiles
pero pueden representar otros instantes. Hay que conciliar agendas y plazos
con los responsables antes de cambiarla, incluyendo servicios, bloqueos,
horarios operativos, notificaciones y cualquier integracion externa. El
comando cubre Reserva, no certifica todos esos dominios ni recalcula servicios.
Cambiar de rama tampoco revierte base/media ni operaciones posteriores.

## Validacion y siguiente bloque

Suite completa: **860 pruebas, OK (1 omitida), 865.210 s**.
Diez casos nuevos, 92 pruebas focalizadas y nueve tras ultimo ajuste;
seis arranques independientes, auditor regional de 103 reservas compatible,
diez recorridos HTTP, PDF SAMEORIGIN, cuatro archivos JS, Ruff, check,
makemigrations sin cambios, 69 enlaces y diff correctos.

Diez casos nuevos cubren predeterminados, UTC/HTML, Bogota/reportes, Madrid y
transiciones, limite de dia en Auckland, configuracion invalida, navegadores
en tres zonas, contrato puro, auditor sin escrituras ni datos personales y
rechazo real por API sin crear reservas. Seis procesos de arranque separados
incluyen cuatro configuraciones validas y dos rechazos esperados.

Siguiente revision concreta: UserProfile en models/core.py,
VinculacionUsuarioPeriodo en models/periodos.py, permisos_operativos_unidad y
clasificar_usuario/clasificar_reserva de reservas/cotizaciones.py. La gestion
usa responsables activos y matriz por unidad; la clasificacion tarifaria usa
tipo declarado y fallback textual UPEC. Separar confirmacion de datos de
verificacion institucional; conservar snapshots y cotizaciones historicas.
Este bloque regional no modifica esas decisiones.

M02.1 sigue abierto: pertenencia y roles verificados (incluido el fallback
historico de tarifas UPEC), catalogos administrables y contenido/tema
institucional. M01 institucional requiere restauracion coordinada, roles de
base separados y evidencia fuera del servidor; el ensayo local no lo cierra.
No se trasladan tablas ni se afirma aislamiento independiente de las apps.

Referencias: [Calendario institucional](calendario-academico-institucional.md),
[Ruta modular](ruta-ejecucion-arquitectura-modular.md),
[Seguridad y continuidad](seguridad-continuidad.md).
