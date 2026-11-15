# Conexiones físico-digitales

Módulo opcional para los laboratorios y unidades que conectan equipos y
sensores al sistema. Registra los **dispositivos** de cada unidad, los
**canales** que miden y las **lecturas** que envían, y entrega esas series ya
resumidas a quien las necesite: una gráfica del panel, un indicador de uso, una
alerta de mantenimiento o un análisis posterior.

Está apagado por defecto. Apagado no existen sus tablas, sus rutas ni su
administración, y ninguna otra aplicación lo importa. El perfil de desarrollo
(`docker-compose.local.yml`) lo trae activado.

## Activarlo en una instalación

1. Definir `SLCID_MODULO_CONEXIONES=true` en el entorno de la web, del
   programador y del proceso de migraciones.
2. Con un respaldo vigente, aplicar la migración por el procedimiento habitual
   (`migrar` en desarrollo, `migrar_produccion.sh` en producción). Solo crea
   tres tablas nuevas (`conexiones_*`); no modifica ninguna existente. El rol
   web recibe sus permisos con `preparar_roles_bd`, como el resto.
3. Reiniciar la web. En el administrador aparece **Conexiones físico-digitales**,
   visible solo para superusuarios.

Para retirarlo: `migrate conexiones zero` y quitar la variable.

## Dar de alta un dispositivo

1. En el administrador, crear el **dispositivo conectado**: unidad, código
   estable (`fablab-clima-01`), tipo y, si corresponde, el equipo inventariado
   al que pertenece.
2. Declarar sus **canales**: la clave con la que el dispositivo los nombra
   (`temperatura`), la unidad de medida, el rango esperado y los días de
   conservación.
3. Con la acción **Generar una clave nueva**, copiar la credencial que se
   muestra. Solo se ve en ese momento: el sistema guarda su huella, no la
   clave. Generar otra invalida la anterior.

## Contrato de envío `lectura_dispositivo_v1`

```http
POST /conexiones/ingesta/
Authorization: Bearer <credencial>
Content-Type: application/json

{"lecturas": [
  {"canal": "temperatura", "instante": "2026-11-14T10:00:00-05:00", "valor": 21.5},
  {"canal": "humedad", "instante": "2026-11-14T10:00:00-05:00", "valor": 48}
]}
```

Respuesta `200`:

```json
{"aceptadas": 2, "repetidas": 0, "fuera_de_rango": 0, "rechazadas": []}
```

- Hasta 500 lecturas y 256 KB por envío. Conviene agrupar: un envío por minuto
  con todas las lecturas es mejor que una petición por lectura.
- `instante` lleva zona horaria. Se admiten lecturas de hasta 30 días atrás
  (un dispositivo sin red puede guardarlas y enviarlas luego) y hasta 5 minutos
  de adelanto de reloj.
- Reenviar un lote no duplica: una lectura es única por canal e instante.
- Las lecturas no válidas se devuelven en `rechazadas` con su posición y el
  motivo; las demás se guardan.
- Un valor fuera del rango esperado se guarda y se cuenta en `fuera_de_rango`.
- Credencial ausente, incorrecta, revocada o de un dispositivo o unidad
  inactivos: `401`, siempre con el mismo mensaje.

En producción cada dispositivo tiene su propio cupo de envíos por minuto
(`SLCID_CONEXIONES_ENVIOS_POR_MINUTO`, 60 por defecto): varios equipos detrás
de una misma salida a Internet no se bloquean entre sí. Los intentos sin una
credencial válida sí se cuentan por dirección (30 por minuto). El ejemplo de
Nginx reparte igual, por credencial (`scripts/nginx/slcid.conf.example`).

## Ver el estado de los dispositivos de una unidad

```http
GET /conexiones/unidades/<slug-de-la-unidad>/
```

Página para quien tiene permiso de **recursos** o **mantenimiento** en la
unidad: cada dispositivo con su estado (en línea si envió en los últimos 15
minutos, sin señal o inactivo), la última lectura de cada canal, su rango
esperado y el aviso de fuera de rango. Con `?formato=json` devuelve lo mismo
como datos, con la dirección de la serie de cada canal. Desde el administrador
se llega con **Ver en el sitio**.

## Consultar una serie

```http
GET /conexiones/canales/<id>/lecturas/?desde=<ISO>&hasta=<ISO>&intervalo=hora
```

Requiere sesión y permiso de **recursos** o **mantenimiento** en la unidad del
dispositivo. `intervalo` admite `crudo`, `minuto`, `hora` (predeterminado) y
`dia`; sin fechas devuelve las últimas 24 horas. La respuesta trae el canal,
el resumen del periodo y los puntos (promedio, mínimo, máximo y número de
lecturas por tramo).

Dentro del código, `apps/conexiones/series.py` es el único punto de lectura:
`serie(canal, desde, hasta, intervalo)` y `resumen(canal, desde, hasta)`.
Tableros, reportes y análisis parten de ahí en lugar de consultar la tabla.

## Conservación

`python manage.py depurar_lecturas` elimina lo que superó los días de
conservación de su canal (`--simular` solo cuenta). El programador de Docker
(`scripts/docker_scheduler.sh`) lo ejecuta en cada ciclo cuando el módulo está
activo; en una instalación sin Docker hay que programarlo una vez al día.

## Qué queda fuera, a propósito

- **Tiempo real.** El servidor es WSGI (Waitress): no hay WebSocket ni un
  intermediario MQTT. Los dispositivos envían por HTTPS y las pantallas
  consultan por intervalos. Un intermediario MQTT o ASGI se añade cuando una
  práctica concreta lo exija, como un servicio aparte que entregue al mismo
  contrato.
- **Órdenes hacia los equipos.** El módulo solo recibe. Accionar un equipo
  desde el portal requiere su propio análisis de seguridad.
- **Realidad virtual y aumentada.** Las experiencias ya tienen su registro en
  `ArtefactoExterno` (tipo `xr`, `apps/gestion_unidades/models/repositorio.py`),
  ligado a unidad, área y equipo. Aquí solo se identifica la estación
  (`tipo = estacion_xr`) cuando envía datos de uso.
- **Inteligencia artificial.** No hay cliente de ningún proveedor. Antes hay
  que decidir proveedor, costos y qué datos pueden salir de la institución. El
  punto de partida para cualquier modelo son las series de `series.py`.
- **Tablas agregadas.** Las series se resumen al consultarlas. Si el volumen
  crece, el resumen por hora se materializa detrás de `series.py` sin cambiar a
  quienes lo usan.

## Pruebas

```powershell
$env:SLCID_MODULO_CONEXIONES = 'true'
python manage.py test apps.conexiones
```

Sin la variable, las pruebas del módulo se omiten y la suite general no lo ve.
