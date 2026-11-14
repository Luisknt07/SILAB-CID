# Pertenencia efectiva en guias y tarifas

Continuacion compatible de M02.1, 16 de septiembre de 2026. Implementa los
consumidores que quedaron pendientes en [revision institucional](verificacion-institucional.md).
No extrae modelos, no traslada datos y no necesita otra migracion.

## Una regla para cada decision

`usuarios/pertenencia.py` consulta UserProfile y User actuales en la base y
evalua la ultima revision. No reutiliza un perfil en cache para conceder
beneficios. Completar datos, declarar docente, usar correo institucional,
escribir el nombre de la institucion o tener `is_staff` no acredita pertenencia.

| Estado actual | Guia nueva sin delegacion | Segmento de cotizacion nueva |
| --- | --- | --- |
| Docente con aprobacion vigente | Permitida | Personal |
| Estudiante con aprobacion vigente | Denegada | Estudiante |
| Otro tipo interno aprobado vigente | Denegada | Personal, para los tipos internos reconocidos |
| Externo aprobado | Denegada | Externo |
| Pendiente, rechazada, revocada, vencida o identidad modificada | Denegada | Externo |
| Cuenta inactiva | Denegada | Externo; autenticacion conserva su propio control |

El segmento externo es una regla tarifaria, **no una reclasificacion del
perfil**. No cambia los reportes ni la vinculacion academica por periodo.
Una solicitud nueva puede conservar estudiante/docente en su fotografia de
periodo y usar segmento externo si no tiene aprobacion vigente.

`unidades/permisos.py::puede_crear_guias_unidad` permite tambien al personal
con permiso efectivo de practicas de **esa unidad**, al administrador principal
y al superusuario activo. Estas delegaciones no conceden descuentos por si
solas. Ser docente verificado permite autoria; no permite aprobar/publicar
guias de terceros ni gestionar unidades. La aprobacion editorial conserva
la matriz operativa existente.

Editor, formulario de reserva y detalle de unidad usan la misma regla. El
personal con acceso al admin ya no obtiene por `is_staff` lectura/descarga de
guias privadas, listado de guias ajenas ni fuentes privadas del formulario.
Los participantes autorizados conservan la consulta prevista; documentos
publicados conservan las reglas de visibilidad y descarga.

## Documentos propios y operaciones anteriores

El autor conserva lectura y correccion de sus guias existentes mientras el
estado editorial permita editar y la cuenta este activa. Una revocacion no
borra documentos ni obliga a crear una guia nueva para corregirlos. Una guia
firmada/aprobada no se vuelve editable por esta excepcion.

Las cotizaciones nuevas de servicios y recursos incluyen `pertenencia_tarifaria`
en el JSON existente: version, estado, revision_id, tipo evaluado, codigo
institucional, vigencia, segmento y momento de evaluacion. No copian nombre,
correo, cedula, fundamento, referencia ni la identidad historica completa.
Es evidencia de la decision usada, no una firma criptografica ni una nueva
concesion de permisos. Sigue siendo dato interno de una operacion privada.

Al recalcular una reserva modificada por una decision operativa o al liquidar
consumo real, se usa primero el segmento guardado en su cotizacion, luego el
tipo historico guardado en la reserva. Sin ambos se usa externo: nunca se
deduce del perfil mutable actual. Los registros antiguos se identifican como
`historica_sin_revision`, version 0; no se fabrican aprobaciones retroactivas.
El recalculo conserva el fundamento anterior y el segmento, aunque cambie
la pertenencia. Puede cambiar cantidades/horas y usar las tarifas operativas
vigentes, como antes: **no congela todo el tarifario ni certifica una factura**.
La liquidacion no sobrescribe el desglose estimado original.

Aprobar/revocar pertenencia no reescribe cotizaciones, costos o reservas.
No hay script de actualizacion masiva. No se aprobaron cuentas reales en
este bloque. Las aprobaciones sinteticas existen solo en las bases de prueba.

## Envio y presentacion

Antes de emitir una reserva se bloquea primero la unidad, luego User y UserProfile en el mismo orden
que la revision institucional, se coteja el fundamento calculado y se revalida
la autoria de una guia nueva. Si la revision cambia durante las validaciones,
el envio devuelve un error controlado y pide recargar. El alta directa de
guia usa el mismo orden unidad/usuario/perfil y revalida tambien la autoria
antes de crear la actividad/documento. Esto evita adquirir unidad y usuario
en orden opuesto entre ambos comandos.
Estas medidas se aplican a estos comandos; no certifican todas las escrituras
externas o todos los flujos concurrentes del sistema.

El visualizador/reserva muestra un aviso ES/EN para pertenencia no vigente.
La simulacion de apoyos en el navegador usa el segmento tarifario efectivo,
separado del tipo declarado para el calendario. El servidor calcula el valor
emitido y no recibe del cliente una aprobacion o segmento tarifario.
Una simulacion abierta puede quedar desactualizada si cambia la revision;
recargar antes de confirmar permite revisar el valor actual. No constituye
un cobro ni una garantia de tarifa definitiva.

La cabecera Grappelli conserva identidad y herramientas: se elimina su recorte
de marca a 36px, se distribuyen marca/idiomas y herramientas en filas hasta
1200px y la cabecera participa del flujo para no tapar el formulario. No se
ocultan las acciones de usuario para simular ausencia de desbordamientos.

## Transicion administrativa y limites

Las cuentas internas pendientes necesitan cotejo por un revisor autorizado
antes de obtener tarifa interna o autoria docente nueva. Pueden conservar
sus reservas propias y solicitar recursos con las reglas generales existentes;
la pertenencia pendiente no bloquea toda reserva. El administrador debe
confirmar procedencia interna canonica y evidencia, sin autoaprobar por correo
o por un registro de demostracion. El bloque anterior detecto 31 procedencias
internas distintas de las siglas configuradas: requieren revision manual.

No se han eliminado todos los usos de `is_staff` del sistema. Calendarios,
otros modulos, admin y excepciones horarias requieren sus auditorias propias.
M02.1 sigue en curso; M01 institucional sigue abierto y condiciona los futuros
traslados de datos. No se certifica aislamiento de despliegue ni seguridad
integral por compartir una funcion de permisos.

Fuentes de las APIs: [permisos y cache de Django](https://docs.djangoproject.com/en/5.2/topics/auth/default/#permissions-and-authorization),
[bloqueo de filas](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update).

## Validacion

Resultados finales y alcance de navegador se registran en CODEX_CONTEXT.md,
seccion 144, y en el traspaso. Las pruebas incluyen pendientes, aprobacion de
docente/estudiante/externo, revocacion, vigencia, identidad modificada sin
save, fuentes/listado/descarga ajenos, fotografia de periodo distinta del
segmento emitido, legado sin revision y cambios durante el envio. Las pruebas
de flujos anteriores acreditan sus identidades sinteticas explicitamente;
`identificar` por si solo sigue sin aprobar pertenencia.

Suite completa: 934 pruebas, OK. Una omitida; 781.806 segundos.
Chrome: 140 combinaciones con cuatro estados de pertenencia, ES/EN y siete
anchos, sin fallos en las comprobaciones de permisos, segmentacion y cabecera
admin. Se usaron y retiraron bases y sesiones temporales. No se modificaron
perfiles reales para aprobar las pruebas.

Limite responsive pendiente: el titulo/subtitulo de la cabecera del modal
de reserva en ingles a 360 px aun requiere ajustar su altura. No se certifica
navegacion por teclado, dispositivos fisicos ni carga masiva.
