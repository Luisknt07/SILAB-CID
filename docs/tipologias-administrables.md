# Tipologías de unidad administrables (M02.3)

Fecha: 20 de septiembre de 2026
Rama: `reestructura-modular`

Este bloque retira la lista fija de cuatro tipos de unidad y la convierte en un
catálogo institucional administrable, sin convertir el sistema en una reserva
universal. Las cuatro tipologías implementadas —laboratorios, plantas piloto,
centros experimentales y observatorios— siguen siendo código; el catálogo
permite **crear tipologías nuevas** que reutilizan una de esas bases y
**desactivar** cualquiera de ellas conservando datos e historial.

## Decisiones tomadas

| Pregunta | Decisión | Motivo |
| --- | --- | --- |
| ¿Dónde vive el catálogo? | `apps.configuracion_institucional.tipologias` | Es configuración de la institución, como catálogos académicos y calendario; el legado lo consume por el adaptador `apps.core.presentation.tipologias`, igual que niveles y catálogos |
| ¿Se cambia la columna `Unidad.dependencia`? | No. Sigue guardando el código; solo pierde los `choices` fijos | Ningún dato se mueve ni se reescribe; la validación pasa al catálogo |
| ¿Qué hace una tipología nueva? | Reutiliza la **base operativa** que declare | Catálogo, detalle, módulos predeterminados y módulo de reserva de esa base; una modalidad con otras reglas exige una extensión implementada |
| ¿Cómo se retira una tipología? | Se desactiva; no se elimina | Sus unidades, reservas, documentos e historial permanecen; el admin no ofrece eliminar |
| ¿Se pueden desactivar las cuatro implementadas? | Sí, una a una | Es el interruptor institucional de cada vertical: si Observatorios no aplica, desaparece del catálogo público y sus rutas responden 404 |
| ¿Idiomas? | Nombre y plural en español, con inglés opcional por fila | Los datos institucionales no se traducen automáticamente; el inglés cae al español si no se registró |

## Qué se administra

`Configuración institucional → Catálogos institucionales → Tipologías de
unidad`. Cada fila tiene código estable, nombre y plural (ES y EN opcional),
descripción, icono, orden, base operativa y estado. El código y la base no
cambian después de crear la fila: el código identifica unidades existentes y la
base define su comportamiento.

La migración `0008_tipologias_unidad` siembra las cuatro implementadas. La
función `sembrar_bases` es idempotente y la reutilizan las pruebas.

## Cómo se aplica en el servidor

La desactivación no es solo cosmética:

- el catálogo histórico de la tipología (`/hublab/`, `/observatorios/`,
  `/centros-experimentales/`, `/plantas-piloto/`) responde **404**;
- el detalle de cada una de sus unidades responde **404**;
- su pestaña desaparece del catálogo institucional;
- una unidad nueva no puede elegirla en el admin, pero una existente conserva
  su valor;
- reactivarla restituye todo sin migración ni pérdida.

Una tipología nueva sin app propia se sirve en `/unidades/<codigo>/` mediante
`apps.directorio_unidades.presentation`. Si se pide por esa ruta una de las
cuatro implementadas, se redirige a su ruta histórica; un código desconocido
responde 404.

El proveedor institucional **superpone** sus filas a las cuatro implementadas.
Una base sin filas, o con filas solo de tipologías nuevas, conserva las cuatro;
si la lectura falla o el catálogo resultante es inválido, se usan las cuatro
implementadas y queda un aviso en el registro. Nunca se oculta una tipología
implementada por un error de lectura.

## Dónde consulta el código la base operativa

`Unidad.codigo_base` devuelve la base de la tipología vigente; sin tipología
registrada devuelve el propio código, de modo que los mapas heredados resuelven
igual que antes. Lo usan la clasificación funcional predeterminada y su
validación, la obligatoriedad del modo de operación de plantas, los módulos
predeterminados y el módulo de reserva (`webcitt/models/recursos.py`), el
detalle (`detalle.py`) y el catálogo (`catalogo.py`).

Las operaciones específicas de plantas piloto —inlines de perfil, señales,
cargadores institucionales— siguen comparando con el código `plantas_piloto`.
Una tipología nueva con base `plantas_piloto` obtiene su catálogo, detalle y
módulos, pero no sus perfiles ni cargadores; extenderlo forma parte del traslado
de cada vertical, no de este catálogo.

## Límites conocidos

- El contrato `identidad_unidad_v1` sigue enumerando las cuatro implementadas.
  Las unidades de una tipología nueva se sirven públicamente, pero no entran
  en ese contrato hasta una versión posterior.
- Las experiencias interactivas del catálogo (`experiencia.html`) pertenecen a
  cada vertical y se incluyen por código, no por base; una tipología nueva no
  muestra la de su base.
- La inventario congelado `docs/inventario-arquitectura.json` no se regenera;
  la línea base de rutas de pruebas sí incorpora `catalogo_tipologia`.

## Verificación

Nueve pruebas propias cubren el contrato puro, la semilla idempotente, la
prohibición de eliminar, la tipología nueva en pestañas, ruta genérica, detalle
y admin, la redirección de las implementadas, la desactivación con conservación
de datos, el rechazo de códigos fuera del catálogo y el fallo cerrado del
proveedor. Se ejecutaron junto con capacidades, unidades, admin, rutas,
manifiestos, idiomas, portal y las cinco verticales: 145 pruebas correctas.
