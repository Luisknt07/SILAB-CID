# Superficies y autoridades antes de separar capacidades

Inventario del bloque 161, M02.2. Describe el codigo actual; no certifica permisos
efectivos, ausencia de vulnerabilidades o aislamiento entre procesos.

La continuacion 162 incorpora [contratos revisados de señales](contratos-senales-heredadas.md)
y corrige la validacion inversa M2M de archivos entre unidades. El inventario
reproducible cuenta ahora 22 comandos propios por el nuevo auditor; las 19
señales mantienen su propietario de ejecucion heredado.

## Reproducir sin consultar datos

La continuacion 163 agrega el comando recuperar_codigos_reservas: ahora son
23 comandos propios. Su modo predeterminado solo cuenta pendientes; aplicar
requiere unidad positiva explicita. La asignacion heredada tiene fallo
observable y servicio con savepoint, sin trasladar autoridad o modelo.
[Procedimiento y limites](codigos-reserva-recuperacion.md).

La continuacion 164 conserva ese inventario y revisa los escritores principales
de reservas: [matriz de autoridad](escritores-y-autoridad-reservas.md).
Completar sesion y aplicar cambio validan autoridad dentro del servicio;
esto no certifica los otros escritores ni habilitacion de toda la capacidad.

```powershell
.venv/Scripts/python.exe manage.py auditar_superficies_capacidades --resumen
.venv/Scripts/python.exe manage.py auditar_superficies_capacidades --modulo observatorios
```

`--modulo` es repetible y filtra solo los modulos declarados. Conserva todas las
superficies compartidas para no esconder accesos alternativos. No habilita apps.
Salida JSON con rutas, callbacks, archivos relativos, lineas, modelos, acciones
declaradas, comandos, scripts y receivers decorados. Las referencias AST y de
scripts son estaticas; no prueban ejecucion ni autorizacion.

El adaptador `apps/integraciones/superficies.py` bloquea SQL en todos los aliases
Django durante la inspeccion. No invoca handlers HTTP, acciones, verificaciones de
permisos, comandos operativos, scripts o receivers. Enumera URLs del admin con
`get_urls()`; cualquier SQL accidental alli se rechaza. `django.setup()` ocurre
antes del bloqueo: este diagnostico inspecciona codigo confiable, no constituye
una sandbox para plugins o Python hostil. No lee adjuntos, respaldos, credenciales
ni filas. La salida completa se genera a demanda, sin duplicarla en el repositorio.

Conteo actual: 11 modulos registrados; 104 rutas heredadas; 96 modelos heredados
y 12 propios; 67 ModelAdmin propios/heredados; 21 comandos instalados propios;
11 scripts operativos; 19 receivers decorados. Incluye acciones globales del
admin, incluso cuando `actions` local esta vacio. No evalua acciones dinamicas.
No detecta registros de señales mediante aliases, metaprogramacion o `.connect()`:
deben revisarse manualmente al modificar contratos. Las cantidades no son una
lista de funcionalidades completadas y pueden cambiar con nuevas funciones.

El alcance son los manifiestos registrados y la operacion propia/heredada.
No enumera todas las rutas internas de Grappelli/allauth ni constituye auditoria
de sus dependencias. Tampoco detecta cada llamada ORM fuera de una entrada:
servicios, modelos y tareas requieren el trazado manual siguiente.

## Propietarios y limites actuales

| Area | Entrada y datos actuales | Autoridad que debe cubrirse |
| --- | --- | --- |
| Laboratorios | `apps/laboratorios`; catalogo y detalle delegan al legado | Permisos por unidad, reservas, recursos, servicios y configuracion particular |
| Plantas piloto | `apps/plantas_piloto`; mismas entradas delegadas; produccion/calidad en legado | Lo anterior mas procesos, productos, lotes, inventario y practicas |
| Centros experimentales | `apps/centros_experimentales`; entradas delegadas | Operacion particular y visitas si la unidad las acepta |
| Observatorios | `apps/observatorios`; entradas delegadas | Operacion particular; no adjudicar reservas u otros servicios por el nombre |
| Centros I+D | `apps/centros_id`; portada propia, sin modelos operativos propios | Definir contratos y permisos de sus futuras funciones antes de implementarlas |
| Inicio | `apps/portal`; revisiones/publicacion propias | Unica capacidad hoy registrada en politica: `portal.portada_inicio`; controles del bloque 160 |
| Quienes somos, servicios, normativa, noticias | Cinco rutas Portal contando Inicio; otras cuatro en presentacion | Aun no tienen capacidad editorial/persistencia propia declarada; no heredan el control de Inicio |
| Configuracion institucional | App propia, presentacion, catalogo, niveles, calendario y habilitaciones | Permisos Django frescos por proveedor; publicaciones, lectura privada e historial separados |
| Directorio, core, integraciones | Contratos y adaptadores declarados | No confundir registro de modulo con aislamiento de datos o extraccion terminada |

Las cuatro verticales estan en etapa `presentacion`, no poseen tablas/admin
operativos independientes. `apps/integraciones/unidades_heredadas.py` pasa el tipo
al catalogo; el detalle delega por slug sin restringir tipo. El prefijo historico
`laboratorio/` tambien sirve unidades de otros tipos. Una suspension por prefijo
de URL seria incorrecta. No se altera esa compatibilidad en este bloque.

## Matriz de revision obligatoria antes de ampliar suspension

| Superficie | Autoridad observada | Condicion para incorporar control |
| --- | --- | --- |
| URLs publicas y detalle | Filtros de catalogo y resolucion de unidad en legado | Resolver unidad/tipo real y distinguir lectura base de operacion suspendida |
| Gestion, agenda y reservas | `webcitt/domains/unidades/permisos.py`: actor activo, administrador de unidad o responsabilidad activa con roles/delegacion | Revisar cada servicio/POST/API; staff por si solo no concede operacion por unidad |
| Admin y acciones | Permisos Django y comprobaciones particulares del ModelAdmin | Revisar permisos por objeto, acciones globales y dinamicas; no deducirlos del acceso a la portada |
| Recursos y repositorio | Visibilidad efectiva del recurso/carpeta, actividad, comprobaciones de adjunto y gestion de unidad | Mantener lectura privada/exportacion autorizada y negar nuevas mutaciones cuando corresponda |
| Visitas y asistencia | Configuracion de unidad, perfil vigente; asistencia acepta reservas o seguridad | Determinar alcance por unidad, no asignarlo automaticamente a una sola categoria |
| Marca institucional | `apps/configuracion_institucional/urls.py`: imagen publicada o lectura privada autorizada; almacen en `imagenes.py` | Conservar marcas historicas, permisos privados y cache; no romper documentos de otras apps |
| Comandos de reservas | `procesar_recordatorios_reservas`, `sincronizar_planificaciones_reservas` y otros comandos compartidos | Aplicar control en servicio por unidad, no solo en vista; `--simular` no equivale a no ejecutar |
| Tareas y scripts | Scheduler Docker y tarea Windows invocan recordatorios compartidos | Revisar identidades, configuracion, logs, idempotencia y unidades suspendidas sin detener las demas |
| Señales | Cambios de modelos generan efectos y contenido derivado | Definir propietario, entradas/salidas y politica de fallo antes de mover o desconectar |
| Historico, preview y exportacion | Autoridades propias de cada proveedor | Probar conservacion y acceso autorizado durante suspension/reactivacion |

Los 12 modulos operativos de permisos heredados son reservas, agenda, recursos,
mantenimiento, inventario, finanzas, practicas, produccion, seguridad, reportes,
configuracion y corregir_cerradas. Son permisos funcionales del legado; no se
convierten automaticamente en capacidades comerciales o apps nuevas.

La ruta publica de imagenes se declara en el manifiesto de configuracion.
Los permisos observados requieren pruebas
negativas por actor, unidad y tipo; el inventario no los ejecuta.

## Señales y secuencia siguiente

Los receivers estan repartidos en `webcitt/signals.py` (12),
`webcitt/models/core.py` (2), `reservas.py` (2), `recursos.py` (2) y `usuarios.py`
(1). Cubren perfiles/configuracion de Unidad, usuarios y decanatos, reservas,
ciclo de equipos, contenido derivado de productos/recetas/calidad/practicas y
archivos externos. Mover solo `signals.py` dejaria dependencias activas ocultas.

Dos puntos necesitan contrato explicito en el siguiente bloque: guardar Decanato
puede activar `is_staff`, crear/asignar su grupo y permisos de SolicitudFabricacion,
y guardar User crea/guarda UserProfile. Una escritura puede generar otra señal.
Ademas, `asignar_codigo_reserva` captura cualquier excepcion y la descarta: debe
evaluarse su observabilidad y recuperacion sin cambiar ahora su compatibilidad.
Las señales de Unidad inicializan configuracion, horarios, perfil especializado,
modulos y contenido; no se deben desconectar como si fueran exclusivas de una app.

1. M02.4: trazar efectos de esas señales y asignar propietarios/contratos;
   revisar todos los servicios de escritura y tareas vinculados a cada capacidad.
2. M02.2: escoger una capacidad acotada, especificar lectura/escritura/historial
   y autoridad, implementar guardas en servidor y probar concurrencia,
   conservacion, recuperacion y ausencia de efectos sobre otras unidades.
3. M02.3: categorias configurables y extensiones propias antes de extraer las
   operaciones de las cuatro verticales. Mantener app labels/tablas hasta ensayo
   de migracion y restauracion M01/M10.
4. M11: aislamiento de procesos, credenciales y recuperacion. Apps dentro de un
   mismo Django comparten proceso, URLconf y base: un fallo de arranque o de base
   todavia puede afectar al conjunto. Separar carpetas no garantiza disponibilidad.

En este bloque solo se corrige que EstadoCapacidad y CambioCapacidad aparezcan
en Configuracion institucional, con los modelos ya visibles segun permisos.
No cambia autoridad, contenido, esquema ni las reglas de suspension vigentes.
M02.2 sigue parcial; M01 institucional y M11 siguen abiertos.

Referencias: [controles](controles-capacidades.md),
[arquitectura](arquitectura.md),
[ruta de ejecucion](ruta-ejecucion-arquitectura-modular.md).
