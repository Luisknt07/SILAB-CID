# Auditoría de estructura y continuidad editorial — 10 de octubre de 2026

## Alcance y evidencia

Se revisaron el inventario completo de archivos controlados por Git y nuevos no
ignorados, los manifiestos de aplicaciones, la propiedad de los modelos, el
cargador de Centros I+D, sus pantallas de gestión y los scripts de arranque y
migración. El inventario analiza sintaxis e importaciones de Python, nombres
sensibles a mayúsculas en Linux, huellas de archivos y patrones limitados de
secretos. No sustituye una revisión semántica línea por línea ni demuestra que
cada flujo visual sea correcto.

La medición inicial se puede reproducir con:

```text
python scripts/auditar_repositorio.py --estricto --json var/auditoria-2026-10-10/estructura.json
```

El primer informe, conservado localmente en
`var/auditoria-2026-10-10/estructura-inicial.json`, registró **3.861 archivos,
320.518.620 bytes, cero errores detectados, cero colisiones de nombres y seis
grupos de duplicados exactos**. Las cifras pueden aumentar al incorporar esta
auditoría. No se eliminaron ni renombraron archivos de compatibilidad.

## Organización real y propiedad de datos

| Área | Propiedad actual | Aislamiento real |
| --- | --- | --- |
| `apps/core` | Contratos de identidad, módulos, permisos y piezas comunes | Núcleo compartido; evita que cada vertical reconstruya estas reglas |
| `apps/configuracion_institucional` | Presentación, logos, niveles, catálogo académico, calendario y capacidades | Tablas propias, revisiones y publicación explícita |
| `apps/portal` | Inicio y su presentación configurable | Inicio con datos propios; integra dominios mediante manifiestos |
| `apps/centros_id` | Centros, áreas, proyectos, resultados, equipo, servicios, solicitudes y recursos | 40 modelos concretos propios; no comparte agenda ni inventario con `Unidad` |
| `apps/laboratorios` | Presentación, administración y permisos de laboratorios | Modelos proxy; operación y tablas todavía en `webcitt` |
| `apps/plantas_piloto` | Presentación y funciones de producción de plantas | Modelos proxy sobre operación heredada |
| `apps/centros_experimentales` | Presentación y funciones agropecuarias | Modelos proxy sobre operación heredada |
| `apps/observatorios` | Presentación y observación, indicadores y series | Modelos proxy sobre operación heredada |
| `apps/directorio_unidades` | Identidad pública y resolución de unidades | Proyección sobre tablas heredadas; no es otro dueño de inventario |
| `apps/integraciones` | Adaptadores entre contratos nuevos y legado | Único lugar destinado a conectar estas fronteras |
| `webcitt` | Operación histórica de unidades, cursos, reservas, producción y expedientes | Principal deuda de extracción gradual; conservar rutas y tablas durante la transición |

**Tablas distintas no significan bases físicas distintas.** Centros I+D y
unidades siguen compartiendo PostgreSQL, proceso, autenticación y almacenamiento.
La separación lógica de los centros existe y se verifica; la separación física
solicitada sigue pendiente y requiere una migración planificada. Las cuatro
verticales de unidades tampoco tienen una base independiente entre sí.

Las relaciones de Centros I+D deben permanecer en su dominio, con la excepción
del usuario compartido. Una unidad vinculada se identifica por slug y se resuelve
mediante un proveedor opcional; no se introduce una clave foránea a `Unidad`.
Se añadieron pruebas que bloquean dependencias de modelos o importaciones
directas hacia la operación de las unidades.

Para separar físicamente los centros se necesitan: inventario de relaciones y
datos, identificador estable de usuario externo, contratos de lectura y eventos,
router de base o servicio independiente, migración y reconciliación de conteos,
copias y restauración por dominio y prueba de corte/reversión. Un router aislado
no resuelve las claves foráneas al usuario: PostgreSQL y Django no mantienen
integridad referencial entre bases. No se efectuó ese traslado sobre la base
actual ni se simula independencia cambiando solo nombres de carpetas.

## Tamaño y archivos duplicados

La distribución del árbol versionado al comenzar la revisión fue:

| Grupo | Archivos | Bytes aproximados |
| --- | ---: | ---: |
| `webcitt/static` | 1.859 | 280.154.656 |
| `webcitt/management` | 214 | 15.500.409 |
| `apps/centros_id` | 148 | 5.684.764 |
| `webcitt/domains` | 216 | 3.444.954 |
| `webcitt/tests` | 255 | 3.206.171 |
| `webcitt/templates` | 273 | 2.139.901 |
| `docs` | 90 | 1.981.321 |
| `webcitt/migrations` | 326 | 975.479 |

Los estáticos representan aproximadamente el 87 % del tamaño del repositorio.
Los recursos mayores incluyen `img/video/fablab.mp4` (20,4 MB),
`img/360/lacteos1.zip` (15,5 MB) y varias imágenes de 2–3,6 MB. Son un punto de
trabajo para dispositivos y conexiones lentas: variantes de imagen por tamaño,
carga de recorridos y video bajo demanda y entrega mediante Nginx o CDN. El
tamaño total del repositorio no es el peso descargado por cada página y tampoco
equivale al consumo de RAM del servidor.

Los seis pares detectados son:

| Archivos iguales | Interpretación y decisión |
| --- | --- |
| Subtítulos `bienvenida-es.vtt` en paquete de curso y estáticos | Paquete redistribuible y recurso publicado; mantener hasta definir una única fuente de empaquetado |
| Poster `bienvenida-poster.png` en paquete de curso y estáticos | Mismo caso; documentar generación, no quitar la copia que consume la página |
| `refractometros-de-proceso.jpg` / `refractometros.jpg` | Nombres de catálogo distintos; revisar rutas y registros persistidos antes de consolidar |
| `termometros-de-proceso.jpg` / `termometros-y-registradores-de-temperatura.jpg` | Alias de catálogo; mismo criterio |
| `documentation-wazuh-com.png` / `wazuh-com.png` | Logos asociados a dominios distintos; mismo criterio |
| `tljh-jupyter-org.png` / `z2jh-jupyter-org.png` | Productos/documentación de Jupyter; mismo criterio |

Los seis grupos detectados no incluyen archivos de implementación. El detector
excluye los archivos vacíos y `__init__.py`; tampoco descarta similitud parcial
ni lógica repetida. Los avisos de nombre fueron cuatro scripts
de respaldo que contienen `backup`; son herramientas operativas válidas, no
copias abandonadas. El PDF de demostración en `output/pdf` es un entregable
versionado de 50 KB; cualquier política de dejarlo fuera debe acordarse y
documentarse, sin confundirlo con información de operación.

## Continuidad editorial durante actualizaciones

Ya existen bases útiles: publicación institucional versionada e inmutable,
desactivación de centros conservando sus registros, procedencia de muestras
separada de evidencia real, documentos con estados y validación explícita,
panel con campos permitidos y comprobación de revisión para evitar sobrescribir
ediciones concurrentes. El panel de centros pagina sus listas a 25 registros y
marca las respuestas privadas para no almacenarlas en caché.

Se encontró un matiz importante del cargador: su modo original completa campos
vacíos de registros existentes. Conserva texto editado, pero puede restaurar
contenido que un gestor vació deliberadamente. Se añadió:

```text
python manage.py cargar_centros_id --conservar-existentes
```

Este modo respeta todos los registros anteriores a la ejecución, también sus
vacíos, desactivaciones, relaciones retiradas, créditos y archivos existentes.
Solo crea faltantes; los nuevos registros reciben todos sus detalles en la misma
carga. Puede combinarse con `--centro` y `--medios`. No puede combinarse con
`--reescribir`; el comando y la clase rechazan esa contradicción. Cada nueva
ejecución restablece el conjunto de registros creados, aunque se reutilice la
instancia del cargador.

El modo conservador no interpreta un cambio de título o código como un renombrado:
los identificadores naturales de los catálogos siguen siendo relevantes. Los
renombrados editoriales se realizan desde gestión; los traslados o cambios de
identificador necesitan una migración explícita con correspondencias. Las cargas
de catálogo no deben ejecutarse en paralelo: no son una cola de importación.
Un registro eliminado puede recrearse porque ya no se distingue de un faltante;
para retirar contenido de forma persistente se conserva el registro con su
estado inactivo o no publicado. La garantía sobre archivos retirados corresponde
a campos vaciados de registros que siguen existiendo.

Los scripts actuales mantienen una buena separación: `docker_web.sh` comprueba
configuración y seguridad, recopila estáticos y sirve; `migrar_produccion.sh`
ejecuta migraciones con credenciales específicas. No hacen `flush`, `loaddata`
ni vuelven a sembrar Centros I+D durante cada arranque. Se debe conservar esta
regla al automatizar despliegues.

## Carga modular y puntos que requieren continuación

Django registra aplicaciones y modelos al iniciar cada proceso. Ese registro es
metadato de funcionamiento; no equivale a descargar todas las tablas ni a cargar
todos los contenidos en cada visita. El objetivo verificable es que una petición
solo evalúe sus consultas, módulos de ejecución y recursos necesarios, además
de autenticación y configuración común. Los imports de motores costosos también
deben diferirse hasta ejecutar su función. Desinstalar aplicaciones para abrir
una sola pantalla no es el mecanismo adecuado de optimización.

Se encontró carga anticipada de colecciones en `Contenidos` de centros y
evaluación de secciones ajenas mediante diccionarios calculados completamente.
La corrección de carga diferida, consulta por sección y sus medidas pertenecen
al bloque paralelo de auditoría de base y rendimiento. Esta documentación no
atribuye su validación a las pruebas editoriales.

La organización no está terminada por tener carpetas separadas. Se midieron
concentraciones de aproximadamente 5.309 líneas en `certificados_diseno.py`,
4.587 en `gestion.py`, 2.115 en modelos de reservas y 1.902 en los modelos de
centros. Se recomienda extraer responsabilidades por caso de uso y conservar
fachadas de importación. En certificados, los renderizadores históricos son
compatibilidad de documentos emitidos: extraerlos por versión conserva esa
garantía; borrarlos o reescribirlos por uniformidad puede alterarla.

Las migraciones históricas se conservan. Compactarlas exige una transición
probada desde instalaciones existentes y desde una base vacía; borrarlas para
reducir número de archivos perjudica actualizaciones y restauraciones. Los
recursos de terceros y los paquetes formativos también tienen licencias y
consumidores distintos: un inventario de duplicados no autoriza a eliminarlos.

### Plantillas del portal y proyectos formativos descargables

La auditoría anterior seleccionaba cualquier HTML con `/templates/` en su ruta.
Eso mezclaba las plantillas del proyecto Django descargable de logística con las
del portal y reportaba falsos errores por `inventario/base.html`. También omitía
la carpeta principal `templates/`, porque su nombre comienza directamente ahí.

Se corrigió `auditar_plantillas` para descubrir las raíces de los loaders Django
activos, incluidos los wrappers de caché, directorios instalados de apps y rutas
explícitas del filesystem loader. Solo compila archivos del árbol del repositorio
que pertenezcan a esas raíces; un directorio configurado sin loader que lo lea no
se considera activo. Las referencias se resuelven en el motor que consumirá esa
plantilla, evitando que otro motor o un proyecto formativo disimulen un fallo.
Se conservan las comprobaciones de estáticos, includes, extends y widgets.

Resultado sobre el portal real: **376 plantillas compiladas, cero errores de
referencias literales**. No se renderizan páginas ni se consultan datos durante
la comprobación; las referencias dinámicas requieren sus propios flujos de
prueba. Se añadieron seis `SimpleTestCase`, todos aprobados, con un proyecto
formativo de fixture, plantillas activas inválidas, raíces no convencionales,
apps, motores distintos y loader en memoria.

## Extensiones nativas sin romper lo existente

Centros I+D ya tiene registro de herramientas con objetivo, entradas, método,
salidas, supuestos, límites, versión, enlace y publicación. El escenario local
incluye una calculadora educativa de capacidad; su existencia no acredita un
catálogo de simuladores de alta fidelidad para todos los centros.

Una extensión de simulación por unidad o centro debe añadir un proveedor
versionado: descriptor público de capacidades, entradas validadas, ejecución
aislada, resultado trazable, evidencia del método y límites y publicación por el
responsable. Las capacidades de ejecución se cargan al abrir la herramienta;
procesos costosos y exportaciones grandes deben ir a trabajos de fondo con
límites, estado y cancelación. El núcleo guarda referencia y resultado, sin
importar en cada página todos los motores de simulación.

Orden sugerido de evolución:

1. Consolidar pruebas y medición de consultas/latencia sobre el despliegue real.
2. Extraer servicios de unidades detrás de los contratos ya declarados.
3. Separar almacenamiento de adjuntos protegidos y trabajos de importación,
   certificados y exportación masiva.
4. Versionar herramientas y escenarios con permisos por centro y unidad.
5. Probar separación física de Centros I+D con reconciliación y restauración
   antes de efectuar el corte de producción.

Las funciones nuevas se incorporan mediante migraciones aditivas y capacidades
apagadas hasta configurarse. No se cambian las reglas de una reserva, matrícula
o certificado histórico para introducir una simulación o un contenido nuevo.

Editar un nombre, descripción, logo, catálogo o contenido ya modelado debe ser
una operación de gestión, sin despliegue ni alteración del esquema. Incorporar
una entidad nueva o cambiar una restricción sí puede requerir migración: evitar
esa evolución guardando toda la operación en JSON sin validación deterioraría
integridad y consultas. La continuidad consiste en conservar datos y contratos
mientras evoluciona el esquema, no en prohibir migraciones para siempre.

## Verificación de este bloque

Se añadieron cinco regresiones de carga conservadora y dos pruebas del límite
de dominio. Cubren vacíos editoriales, estados desactivados, faltantes completos,
reutilización del cargador, medios retirados, documentos existentes, relaciones
vacías y modos contradictorios. Las pruebas se ejecutan en una base independiente
`test_citt_auditoria_contenidos_20261010`, con almacenamiento temporal del runner;
no modifican la base operativa.

Resultado: **18 pruebas aprobadas**: las cinco nuevas de carga, ocho del catálogo
interdisciplinario, tres de estructura y dos del límite de dominio. La suite con
base creó y destruyó su base de pruebas; las dos últimas no requieren base. Los
logs locales son `var/auditoria-2026-10-10/tests-contenidos.log` y
`tests-limites-dominio.log`. Ruff, compilación de Python y revisión de espacios
del diff también pasan para los cambios de este bloque.

El bloque posterior de plantillas añade **seis pruebas aprobadas**, para un total
de **24 pruebas en este alcance**. Sus logs locales son
`var/auditoria-2026-10-10/tests-plantillas-activas.log` y
`auditoria-plantillas-activas.log`; Ruff y revisión del diff también pasan.
