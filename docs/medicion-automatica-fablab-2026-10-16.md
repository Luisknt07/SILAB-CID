# Medición automática y demostración de FabLab — 16 de octubre de 2026

El Centro de reportes calcula el avance desde registros efectivos y evidencias de gestión verificadas. **La medición ya está activada en http://127.0.0.1:8000/** tras autorización expresa del usuario. La primera demostración se comprobó en una base temporal independiente de 8001, cuya instancia se retiró después. Los documentos y archivos anteriores de la aplicación principal se conservan.

## Resultado del escenario aislado

Se preparó FabLab para 2026-B con seis atenciones efectivas, seis planificaciones aprobadas, tres ejecuciones válidas, una guía publicada, tres participantes nuevos, cinco mantenimientos críticos programados y tres partidas de desechos acondicionadas. Una ejecución en borrador y otra eliminada se excluyen de la medición.

| Meta obligatoria | Evidencia del ejemplo | Cumplimiento |
|---|---|---:|
| Registro de uso | 6 sesiones efectivas de 8 observadas en bitácora independiente | 75 % |
| Mantenimiento crítico | 4 de 5 programados; mínimo institucional 80 % | 100 % |
| Inventario | 1 acta que comprueba equipos, software y espacios | 100 % |
| Inducción | 2 de 3 personas nuevas con habilitación documentada vigente al primer ingreso | 66,67 % |
| Capacitación | 2 constancias para una meta de 1 | 100 % |
| Difusión | 1 publicación documentada | 100 % |
| FT03 | 3 ejecuciones válidas para una meta de 6 | 50 % |
| Guías | 1 guía publicada para una meta de 1 | 100 % |
| Investigación | 1 atención efectiva de investigación | 100 % |
| Transferencia | Borrador sin respaldo verificado | 0 % |
| Desechos | 3 partidas registradas de 4 generadas según conciliación | 75 % |
| FT02 | 6 prácticas aprobadas para una meta de 6 | 100 % |

**Avance provisional: 80,56 %.** La nota oficial sigue en cero por falta de planificación aprobada; el ejemplo no simula una firma ni una aprobación de Dirección. Los datos llevan una advertencia de demostración y se bloquea su envío como informe oficial.

## Fuentes y cálculo

Las cantidades se comparan con la meta del plan, proporcionalmente y con un máximo de 100 %. Superar la meta se muestra por separado. Los requisitos institucionales y los mínimos según tipo de unidad se conservan.

- Uso: solo reservas con cierre efectivo. El universo de sesiones proviene de una conciliación independiente, nunca del mismo contador que se quiere evaluar.
- Seguridad: primeras entradas de personas identificadas en la unidad; se comprueban todas las inducciones aplicables y su vigencia en esa fecha. Personas repetidas no duplican el denominador. Ingresos sin identidad dejan la medición pendiente.
- Desechos: partidas con cantidad positiva, identificación, responsable y almacenamiento o entrega documentada. La conciliación establece el total generado, expresado en partidas, no en kilogramos.
- Inventario: acta de revisión física que cubre equipos, software y espacios. Generar el PDF automático del inventario no acredita esta meta.
- Capacitación, difusión y transferencia: registros con resultado, responsable de la unidad y respaldo. Los borradores y las rectificaciones no suman. También se conectan los contadores documentados del catálogo para boletines, eventos, proyectos, publicaciones, ensayos y producción cuando correspondan a la tipología.

Las conciliaciones deben cubrir todo el período transcurrido hasta la fecha de medición, sin solapamientos. Un denominador cero, un tramo incompleto o un total menor al registrado no acreditan cumplimiento. Por ello, una conciliación debe actualizarse al ampliar el período observado; el sistema no inventa el total del día siguiente.

La opción **Registrar evidencia** abre un formulario dentro del editor modal existente. Permite adjuntar un PDF o imagen, usar un archivo de la unidad o enlazar una publicación. Queda constancia de quién verificó la correspondencia del respaldo con la actividad. La comprobación de contenido descarta PDF vacíos o corruptos e imágenes uniformes; no certifica por sí sola la veracidad de una publicación.

Las huellas impiden acreditar dos copias idénticas del mismo archivo para una actividad o seguir acreditando un respaldo sustituido. Los enlaces repetidos tampoco suman dos veces. Rectificar exige motivo y conserva el archivo y la auditoría. Los respaldos se abren por una ruta privada del expediente, con acceso de la unidad y de Dirección; no se publican como recursos abiertos.

## Entregas conservadas

El cálculo nuevo usa `metas-cierre-3`. Las entregas congeladas de las versiones 1 y 2 conservan su lectura. La preparación del cierre guarda las fuentes y sus huellas; si cambian antes del envío, debe generarse y firmarse nuevamente el informe. Los ejemplos no alteran documentos enviados ni calificaciones históricas.

Se separa el avance de las metas de la nota habilitada por planificación aprobada e informe completo. Así se pueden comprobar resultados mientras se redacta sin presentarlos como evaluación oficial.

## Verificación

- Migración `documentos.0002_evidencia_gestion_medicion` ejecutada en PostgreSQL QA nuevo y desechable. El primer ensayo tuvo un fallo en el identificador de documento del fixture demostrativo; se corrigió `INFORME` por `INFORME-SEMESTRAL`.
- Cierre: **60 pruebas correctas (59 en la suite y una focal de fuentes/firma)**, con esquema actual aislado. Incluyen proporciones, fuentes vacías, archivos blancos o corruptos, duplicados, identidad y vigencia, inventario, acceso privado de unidad/Dirección, errores del formulario, rectificación, reversión de archivos, idempotencia del escenario y bloqueo de envío de ejemplos. Se conserva la regresión anterior del cierre y la redacción.
- Chrome con perfil separado a 1600 y 500 px: numeración continua de 16 ítems, diez columnas, desplazamiento horizontal interno en móvil, un solo editor modal y visor PDF real funcionando; sin errores JavaScript.
- **20 PDF consultados por HTTP y analizados**, incluidos los seis respaldos de demostración. Se corrigió un 404 descubierto en esta comprobación: los respaldos nuevos requieren su ruta privada, no el acceso público de recursos.
- `check`, Ruff, `makemigrations --check --dry-run` y diferencias sin errores. `pypdf==6.21.0` fijado en proyecto, lock y exportación de dependencias.
- Comprobación previa a la activación, en modo de solo lectura: **615 documentos**, tabla nueva entonces ausente y medición nueva desactivada. La activación posterior se documenta debajo.

Evidencia local privada: `var/medicion-fablab-20261016/`. El servidor de demostración utilizó base y archivos separados, correo en memoria y un usuario de unidad local; no se publica su configuración de acceso automático en el repositorio. Su base temporal se respaldó antes de detener el contenedor.

## Autorización y activación en la aplicación principal

La revisión automática rechazó inicialmente la migración sobre la base institucional activa porque preparar ejemplos no autorizaba claramente un cambio persistente de esquema operativo. Se completó la implementación y la demostración aislada. El usuario autorizó después dejar la medición en 8000 para evitar interferencias entre instancias.

La activación autorizada se completó con respaldo previo, comprobación del listado y huella del respaldo, aplicación exclusiva de `documentos.0002` y habilitación local de `SLCID_MEDICION_METAS_HABILITADA=true`. Se reinició 8000 después de migrar. El cargador general `demostrar_medicion_fablab` conserva sus barreras: exige base `citt_demo_`, entorno DEBUG, `ALLOW_DEMO_DATA_COMMANDS`, `MEDICION_SOLO_DEMO`, unidad explícita y `--confirmar-datos-demo`; rechaza unidades reales existentes.

Para atender esta autorización concreta se copiaron únicamente siete registros de evidencia de ejemplo a FabLab, mediante el servicio transaccional con auditoría y marca DEMO. Se conservaron sus seis respaldos PDF internos. No se trasladaron las reservas, prácticas, personas ni requisitos de acceso del escenario aislado. Las conciliaciones de uso y desechos se rectificaron con historial para ajustarlas al calendario real publicado, del 17 de agosto al 16 de octubre de 2026 como tramo transcurrido. Quedan nueve registros de evidencia: seis verificados, un borrador y dos rectificados.

El avance de FabLab en la aplicación principal es **52,43 %**, distinto del 80,56 % del escenario aislado porque utiliza los registros que la unidad ya tenía. La tabla muestra doce metas obligatorias, diez barras medibles y dos pendientes de medición: seguridad y mantenimiento. La advertencia de demostración y el bloqueo de envío oficial con datos ficticios se mantienen.

Se compararon las huellas completas de los **615 documentos** antes y después de la activación, incluyendo estados, archivos, firmas, plazos y calificaciones; coinciden. También coinciden los campos de archivo, estado y huella de los **250 recursos anteriores**. La aplicación principal incorporó seis recursos de evidencia nuevos. El esquema y la base de Centros I+D no se modificaron.

Comprobación final autenticada como responsable de FabLab: HTTP 200, 52,43 % y diez barras. Chrome aislado a 1600/500 px volvió a verificar la numeración, el editor único y el visor PDF real, sin errores JavaScript; **20 PDF de 8000** consultados y analizados correctamente. Las sesiones creadas exclusivamente para las comprobaciones se retiraron. La instancia de 8001 y su contenedor temporal quedaron detenidos, con respaldo de ese escenario; 8000 permanece en ejecución.

[Abrir las metas de FabLab en 8000](http://127.0.0.1:8000/gestion/unidades/laboratorio-fabricacion-digital-prototipado/expediente/#anexos-302). Evidencia privada de esta activación: `var/medicion-fablab-20261016/activacion-8000/`. No se realizó despliegue al servidor universitario.

La planificación FabLab 2026-A con archivo equivocado, identificada en la [auditoría anterior](auditoria-centro-reportes-2026-10-16.md), sigue conservada y requiere su rectificación autorizada.
