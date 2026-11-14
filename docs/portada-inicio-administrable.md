# Portada de Inicio administrable

Bloque 156 de M02.1/M09: primera persistencia editorial en `apps/portal`.
No traslada modelos ni datos de `webcitt`.

## Uso

En **Portal institucional > Portadas de Inicio** se editan lema, título,
resumen, etiquetas de los dos botones y mensaje junto al logo, por separado
en español e inglés. Título vacío conserva nombre del sistema y siglas
institucionales. Imágenes, galería, indicadores referenciales y otros bloques
mantienen su configuración anterior; esta entrega no certifica sus cifras.

Guardar crea un borrador. **Vista previa** permite revisar ambos idiomas con
el selector ES/EN sin cambiar la página pública. **Revisar y publicar** exige
confirmación y crea una versión nueva. Una publicación antigua puede
recuperarse publicándola como revisión nueva o copiándola a un borrador.
El historial anterior se conserva.

| Permiso de `portal` | Autoridad |
| --- | --- |
| `add_revisioninicio` | Crear borradores |
| `view_revisioninicio` | Consultar historia, copiar y previsualizar |
| `publicar_inicio` + lectura | Confirmar publicación o recuperación |

Requieren cuenta activa y acceso al administrador. No se conceden permisos a
cuentas o grupos existentes; el superusuario activo conserva su autoridad.
Una creación sin lectura parte del respaldo instalado y no copia historia.

## Estructura y protección

`apps/portal/apps.py`, `models.py` y `admin.py` componen las secciones. Inicio
posee `contracts.py`, `defaults.py`, `models.py`, `forms.py`, `admin.py`,
`services.py` y `selectors.py` bajo `apps/portal/inicio`. Tiene migración,
plantillas administrativas, CSS y pruebas propios. La plantilla pública
conserva su ubicación compatible en `webcitt/templates`.

Las guardas de historial, autoridad y bloqueo se extraen a
`apps/core/persistence/publicacion.py`; `configuracion_institucional/versionado.py`
mantiene imports compatibles. Las dos apps no dependen entre sí. El registro
de `portal` puede arrancar con Auth/ContentTypes sin `webcitt`; esto no implica
aislamiento de procesos ni del motor de base de datos.

Crear/publicar revalida usuario y permisos desde la base, bloquea el puntero
transaccionalmente y comprueba la versión enviada por el formulario. Un
formulario antiguo no sobrescribe contenido posterior. Publicar exige POST,
CSRF y confirmación; GET no publica. Vista previa requiere lectura y `no-store`.

Solo la revisión publicada vigente se proyecta al público en un DTO inmutable,
con texto simple y límites por campo. Ambos idiomas se validan; no admite
HTML, CSS, URLs configurables ni claves adicionales. Conserva autoescape.
La consulta pública usa una sola lectura con `select_related`, sin consultar
operaciones de unidades. Si falta publicación, la consulta no está disponible
o el contenido es inválido, usa el respaldo traducido instalado y registra
una advertencia genérica. No muestra borradores ni datos de otra instalación.

Las revisiones no se modifican/borran por el ORM ordinario. Autor y referencias
usan `PROTECT`. SQL privilegiado requiere los controles pendientes de M11.
Noticias, Normativa, Servicios, Quiénes somos y otros bloques siguen pendientes.

## Migración y recuperación

`portal.0001_initial` agrega dos tablas, dos ContentTypes y tres permisos;
no renombra tablas, crea contenido ni asigna permisos. Hasta publicar, Inicio
conserva sus textos anteriores. Requiere suite correcta, respaldo local
protegido y ensayo de aplicación/reversa en copia antes de aplicarse.

La reversa de esquema se ensaya con las tablas nuevas vacías. Con historia
real, conservar tablas y usar código compatible, sin limpiar ContentTypes o
permisos. Una rama Git por sí sola no restaura datos/archivos.
M01 institucional sigue abierto: el ensayo local no sustituye copia externa
cifrada/inmutable, captura coordinada de adjuntos, custodia de claves ni RPO/RTO.

## Validación

Suite completa: 1068 pruebas, OK; una omitida, 838.981 segundos. Comprobación
final de Portal: 23 pruebas OK, incluida publicación concurrente, permisos,
CSRF, formularios obsoletos y recuperación. La extracción de guardas también
se verificó con las 111 pruebas institucionales. Ruff, Django check,
makemigrations --check y catálogos ES/EN compilados correctos.

Migración aplicada localmente tras restauración, aplicación/reversa/reaplicación
en copia protegida. Las 144 tablas previas conservaron datos, columnas,
índices y claves; 386 archivos conservaron sus hashes. Dos tablas nuevas
vacías, dos ContentTypes y tres permisos; ninguna concesión a usuarios/grupos
ni publicación real. El restaurador PostgreSQL representó de forma equivalente
el cast de un array en un índice parcial previo: se comprobó esa equivalencia
en copia y se comparó literalmente el esquema real, sin alterar ese índice.

Chrome: 454 casos OK, español/inglés y once anchos de 360 a 1920 px, con y
sin paleta personalizada y lectura al 115 %. Incluye textos máximos sin
espacios, borradores privados, publicación/recuperación y botones completos,
sin degradado en normal/hover; sin desbordamientos ni errores JS. La cabecera
compartida pasó otros 84 casos en siete rutas y seis anchos de escritorio,
sin solapamientos. Capturas de escritorio/móvil inspeccionadas; copias y
sesiones QA retiradas. No certifica dispositivos físicos ni accesibilidad
integral. La guía de ejecución y el historial del bloque 156 registran el
commit y las siguientes fronteras pendientes.
