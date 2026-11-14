# Centros de Investigación y Desarrollo

Centros I+D es un contexto independiente de las unidades experimentales. Un
Centro I+D **sostiene una agenda científica y tecnológica e integra capacidades,
talento y proyectos**: líneas, investigadores, grupos, proyectos, resultados,
propiedad intelectual, transferencia, alianzas e impacto (clasificación
institucional §13, Reglamento UPEC 2026, arts. 20 a 31). No es un laboratorio
grande ni un espacio reservable: usa capacidades propias o vinculadas y se
accede a él por una propuesta de proyecto, una colaboración, el acceso a una
capacidad o un servicio científico-tecnológico. No es un quinto valor de
`TipoUnidad` ni hereda reservas, corridas, ensayos de campo o solicitudes de
observatorios; se articula con laboratorios, plantas, centros experimentales y
observatorios, pero nunca guarda una clave foránea hacia la tabla de unidades.

## Estado actual

El catálogo versionado incluye CIDT-UPEC, Agropecuaria, Alimentos y Biodiversidad
(CIAB-UPEC) y Desarrollo Humano y Territorial (CDHT-UPEC). Los dos últimos se
registran como propuestas sujetas a validación institucional, con once áreas y
veintitrés servicios en conjunto. Sus módulos están en `contenido/ciab.py` y
`contenido/cdht.py`; comparten la construcción de contenido interdisciplinario.
Las tarjetas comparan áreas, servicios, unidades vinculadas y líneas en el mismo
orden; la portada del catálogo no incluye filtros generales. El resumen cuenta
las unidades compartidas una sola vez. La portada se concentra en las tarjetas,
sin navegación local, puertas de entrada, destacado duplicado ni actualidad global.
La actividad se consulta dentro de cada centro. Cada tarjeta tiene una sola
acción: «Entrar al centro». Se igualan sus alturas mediante la grilla; desde
1280 px el selector alterna entre horizontal (predeterminada) y tres columnas,
recordando la preferencia. En horizontal de escritorio, la imagen ocupa la
mitad del ancho de la tarjeta; de 600 a 1279 px se presentan en filas horizontales
y por debajo de 600 px en una columna. El resumen incluye todas las áreas
publicadas y tres carreras; los datos completos se consultan en la ficha.
Ver [alcance y verificación](../../docs/centros-id-red-interdisciplinaria-2026-10-08.md).

La app es propietaria de su dominio, su administración, sus migraciones y sus
páginas públicas. El primer centro montado es el **CIDT-UPEC** (Centro de
Innovación y Desarrollo Tecnológico). El estado registrado se conserva, pero la página lo marca pendiente hasta que un gestor registre y valide su respaldo.

```text
apps/centros_id/
|-- models.py         # centro, áreas (divisiones y plataformas) con equipos y procesos, gobierno, ruta,
|                     # modalidades, líneas, servicios, espacios y planos, indicadores, riesgos,
|                     # articulación (con instrumento y modalidad), integrantes, grupos, proyectos,
|                     # resultados, casos, aliados, convocatorias, novedades, documentos, carpetas,
|                     # ajustes de secciones y solicitudes
|-- mapa.py           # las 6 pestañas, sus secciones, sus portadas y las páginas que cuelgan de ellas
|-- contenidos.py     # lo que la ficha necesita, sección por sección; el árbol del panel
|-- admin.py          # el centro con sus inlines; lo que crece a diario con su propia lista
|-- carga.py          # cargador idempotente del contenido documentado
|-- contenido/        # módulos cidt.py, ciab.py, cdht.py y sus imágenes en medios/
|-- formularios.py    # formularios por intención, disponibilidad y seguimiento privado
|-- operaciones.py    # confirmación transaccional, requisitos, horarios, bloqueos y acompañamiento
|-- reportes.py       # el reporte institucional del centro en PDF
|-- vinculos.py       # unidades y sedes resueltas por proveedores en lista blanca
|-- texto.py          # lectura de listas, pares y ternas escritas en texto
|-- management/commands/cargar_centros_id.py
|-- presentation/     # portada, ficha, visualizador (secciones, áreas, carpetas, fragmentos), solicitar y reporte
|-- templates/centros_id/
|-- static/centros_id/
`-- tests/
```

## La ficha: seis pestañas, las mismas para todo centro

| Pestaña | Secciones |
| --- | --- |
| El centro | Conoce el centro (con identidad y ubicación), Ahora en el centro, Cómo trabaja, Gobierno y gestión, Documentos y normativa |
| Áreas y capacidades | Áreas del centro (con el edificio que las aloja), Equipos, espacios y herramientas, Relaciones entre áreas, Capacidades vinculadas |
| Investigación | Agenda y líneas, Proyectos, Resultados de investigación |
| Innovación y transferencia | Desarrollos y propiedad intelectual, Casos de transferencia, Alianzas y financiamiento |
| Equipo | Dirección y comité, Investigadores, Grupos y carreras, Técnicos y formación |
| Servicios y colaboración | Portafolio, Proponer o solicitar, Visitas, Formación y oportunidades |

La estructura responde a lo que es un Centro I+D, no a cómo se organiza uno en
particular: ninguna pestaña depende de los tipos de área de un centro. Las áreas de
cada centro (divisiones, laboratorios, plataformas…) viven en «Áreas y
capacidades», agrupadas por su tipo y en el orden del centro; el primer grupo (en el
CIDT, sus divisiones tecnológicas) va destacado en «Conoce el centro», en «Áreas del
centro» y en la portada de la pestaña. Cada área tiene su página con todo lo que
hace: cómo trabaja paso a paso, sus equipos con ficha, sus servicios, sus proyectos,
sus resultados y su gente.

El panel «Contenidos» muestra solo lo esencial: la mayoría de las secciones es una
página que se abre directo; despliegan elementos «Conoce el centro» (identidad y
ubicación), «Documentos y normativa» (cada PDF) y «Áreas del centro» (cada área). Las
instalaciones no son una sección aparte: el plano con dónde está cada área, los espacios
por nivel, el recorrido 360° y las imágenes del edificio viven en «Áreas del centro», y
las fotos y videos de cada área, en su página. No hay carpetas de equipos, procesos ni personas en el
panel: viven en la página de su área o de su sección. Las secciones no llevan
numeración. Cada pestaña abre con su portada, la misma pieza de Laboratorios
(`portal/css/components/portada_tecnologica.css`): fotos de lo que contiene, su
frase, sus cifras, «Qué vas a encontrar», de dónde salen los datos y cómo leerlos.

Las páginas del visualizador se arman con las piezas de Laboratorios, las mismas de
«Conoce la unidad», la ficha de la unidad y la página de un área
(`portal/css/pages/unidades/conoce_unidad.css`, `ficha_unidad.css` y `area_unidad.css`, con
sus guiones `conoce_unidad.js` y `area_unidad.js`): cabecera institucional con cifras sobre
su borde, índice que acompaña la lectura, secciones con antetítulo, tarjetas de actividad,
pasos, tablas, galería con visor, videos con lista, diagrama paso a paso y fichas técnicas
en ventana. La página de un área tiene la estructura de la página de un área de
Laboratorios; «Conoce el centro», la de «Conoce la unidad». `centros_id/visor.css` guarda
solo lo que Laboratorios no tiene: el mapa de relaciones, el plano con sus puntos, los
filtros, el formulario de solicitud, la madurez tecnológica y el avance de un proyecto. La
ficha del centro ofrece `abrirUbicacion` a esas páginas, que la usan para abrir sus accesos
en el visualizador.

Todo sale de registros: una sección vacía no se ofrece al público y quien
gestiona la ve pendiente con el enlace para completarla. Nunca hay saltos a una
parte de la misma página. Los equipos siguen siendo capacidad de su área; el índice
transversal de recursos consulta esos mismos registros y permite ver su disponibilidad
cuando están individualizados y habilitados.

## Organización aplicada del CIDT — octubre de 2026

La organización distingue cinco áreas de **Tecnologías aplicadas**, dos
**Plataformas operativas** (Smart Factory y Smart CEDI) y **Sistemas
transversales** (Sala de Control). Comercio Exterior es un módulo integrado
en Smart CEDI mediante `Componente.integrado_en`; conserva su identificador,
ficha, servicios, equipos y enlaces. La oficina de innovación y transferencia
es una instancia de gobierno y coordinación, no una plataforma productiva.

`integrado_en` admite un nivel de módulos, dentro del mismo centro. La
validación rechaza autorreferencias, ciclos, padres de otro centro y módulos
anidados. La FK protege al padre ante borrado. La jerarquía pública se arma
desde la colección ya cargada, sin consultar una vez por cada padre. Si un
padre no está publicado no se expone su nombre o enlace desde un hijo visible.

Cada área tiene tres campos editables adicionales, con el mismo formato
de tablas de texto que utiliza el resto de la aplicación:

- `organizacion_operativa`: sector/celda, operación y control/evidencia.
- `insumos_materiales`: material y condiciones de aceptación/uso.
- `usos_academicos`: carrera, actividad y evidencia de trabajo.

El CIDT detalla recepción, cuarentena, almacenamiento automatizado,
conservación, abastecimiento, preparación de pedidos, comercio exterior,
despacho y retornos. Smart Factory detalla industrialización, materiales,
celdas, líneas, calidad y producción por lotes/series. Se incluye participación
aplicada propuesta para dieciséis carreras; no acredita acuerdos, matrícula,
dotación de activos ni capacidad instalada. El escalamiento de alto volumen
depende de medición, recursos habilitados y aprobación del plan operativo.

El contenido de esta revisión vive en `contenido/cidt_organizacion.py`.
`cidt.py` lo aplica al catálogo y conserva en memoria el antes/después de
los campos afectados para reconocer la precarga previa. No es una copia de
la base operativa ni sustituye la edición en gestión. En una instalación nueva,
el cargador ordinario crea la organización completa. Para una existente:

```powershell
# Aplicar antes la migración 0017 con el rol de mantenimiento configurado.
.venv\Scripts\python.exe scripts\migrar_desarrollo.py
.venv\Scripts\python.exe manage.py actualizar_organizacion_cidt
.venv\Scripts\python.exe manage.py actualizar_organizacion_cidt --aplicar
```

El primer comando de contenido ensaya en una transacción que se revierte.
El segundo actualiza sólo vacíos o valores reconocidos del catálogo anterior,
conserva campos manuales y reporta sus identificadores sin imprimir su contenido.
No cambia estado operativo, validaciones, precios, permisos o recursos habilitados.
Actualiza pasos por número y mantiene sus identificadores; no borra pasos extra,
equipos ni sus relaciones. No usar `--reescribir` global para aplicar esta revisión.
Producción utiliza el procedimiento separado de migración y su rol correspondiente.

Las áreas muestran también resultados y líneas de proyectos en los que participan.
El resultado conserva su área responsable y su único registro; los filtros de
muestra, publicación y confidencialidad siguen aplicándose antes de presentarlo.

## Solicitudes y acceso a capacidades

Toda necesidad entra por `SolicitudCentro` (reto, servicio, uso, capacitación a
medida, visita o acompañamiento), con campos según intención. La entrada ofrece
servicios y uso de recursos cuando existen registros habilitados; si no hay oferta,
permite plantear la necesidad sin presentar un formulario imposible de completar. Sigue la ruta
`recibida → evaluación → aprobada → ejecución → entregada → cerrada`, o
`no procede` desde los tres primeros estados; admite cancelación hasta ejecución.
El solicitante retira hasta aprobación. La ruta no salta pasos ni reabre lo cerrado.
El expediente privado reúne respuesta, plan, horario, sesiones, tareas e historial;
las notas internas y referencias privadas no se presentan al solicitante.

Los usos propios requieren equipo individual o espacio habilitado, horario,
requisitos comprobados, aforo y ausencia de cruces. La inducción, supervisión y
calibración se comprueban cuando corresponden. Horarios y bloqueos determinan la
disponibilidad orientativa; confirmar vuelve a validarla bajo bloqueos de filas.
Las solicitudes recibidas no ocupan recursos. Las atiende gestión desde el
administrador. Los recursos históricos no quedan reservables automáticamente.

La oferta pública de cursos y ediciones se consulta desde el proveedor del
directorio y enlaza a la matrícula original. Las reservas vinculadas usan la
agenda propietaria; no hay transacción conjunta con recursos propios del centro.
Las herramientas virtuales necesitan revisión de método, versión, supuestos y
límites. El escenario local incorpora una calculadora educativa de capacidad de
dos etapas; el catálogo institucional no versiona escenarios. La guía de
[servicios, recursos y seguimiento](../../docs/centros-id-servicios-recursos-seguimiento-2026-10-07.md)
explica configuración, validación y pendientes de la migración 0012.

## Carga del contenido

```text
python manage.py cargar_centros_id [--centro cidt-upec] [--reescribir | --conservar-existentes] [--medios] [--muestra]
```

Crea lo que falta y no pisa lo editado en el administrador, salvo con
`--reescribir`, que también actualiza los créditos de las imágenes y rehace los
documentos generados que siguen siendo borradores. Las muestras nunca reemplazan registros institucionales, incluso con esta opción. `--medios` copia las imágenes del centro y genera en PDF
los documentos que salen de sus registros (plan de desarrollo, ruta de atención,
protocolo de seguridad, catálogo de servicios y equipamiento por área). Un módulo
de contenido puede omitir FASES, PRESUPUESTO, INDICADORES, RIESGOS o DOCUMENTOS.

`--muestra` carga ejemplos internos desde `contenido/cidt_muestra.py`. Personas, proyectos, resultados, casos, aliados, convocatorias, novedades y documentos llevan `es_muestra=True`: no aparecen en páginas públicas, fragmentos ni indicadores. Los retos de ejemplo se conservan en `retos_muestra`, separados de la agenda institucional. El gestor los revisa en el administrador; retirar la marca exige una fuente y la acción explícita «Validar procedencia». Quedan registrados autor y fecha de validación. Los documentos generados empiezan como borradores internos; generar un PDF no acredita aprobación.

Los indicadores con `calculo` se cuentan solos desde los registros (proyectos,
investigadores, producción, propiedad intelectual, prototipos, casos, aliados,
servicios). Un conteo automático vacío vale cero y lleva fecha de consulta; una medición manual sin valor sigue pendiente. Consultar la página no guarda ni modifica mediciones. «Servicios atendidos» cuenta exclusivamente solicitudes de tipo servicio entregadas o cerradas, en su histórico.

### Actualizaciones que conservan incluso campos vaciados

Para añadir centros, áreas o servicios faltantes a una instalación que ya tiene
contenido editorial, use:

```text
python manage.py cargar_centros_id --conservar-existentes
```

Este modo conserva los registros que existían antes de la ejecución, incluidos
los campos que el gestor dejó vacíos, los estados desactivados, las relaciones
vacías y los archivos retirados. Los registros nuevos sí reciben sus detalles
completos durante esa carga. Puede combinarse con `--medios` para crear imágenes y
documentos faltantes; no restablece la portada de un centro existente ni regenera
sus documentos. Es incompatible con `--reescribir`.

Un registro eliminado ya no puede distinguirse de uno faltante y puede volver
a crearse desde el catálogo. Para retirar contenido y conservar esa decisión,
use su estado inactivo, no publicado o equivalente, según el tipo de registro.

El modo original sin estas opciones sigue completando vacíos para instalaciones
iniciales; no debe ejecutarse automáticamente en cada despliegue. El arranque de
producción comprueba la configuración y recopila estáticos; las migraciones se
ejecutan en su servicio separado. Ninguno vuelve a cargar el catálogo.

## Identidad y documentos institucionales

La ficha del centro permite registrar adscripción, misión, visión, sectores y retos,
y dos respaldos separados: identidad y estado. Las acciones del administrador validan
cada respaldo y registran fecha y persona. Los borradores de misión y visión solo los
ve gestión; cambiar los campos revisados invalida su validación anterior. La operación
validada del centro no acredita disponibilidad de equipos ni de horarios.

Los documentos distinguen informativo, borrador y aprobado; este último requiere
emisor, fecha y fuente. Admiten versión y un tipo específico para creación o
reconocimiento institucional. El reporte PDF es un resumen automático de los registros
publicados y muestra los estados pendientes de validación.

La migración 0010 identifica las muestras históricas del CIDT por sus firmas de contenido;
conserva coincidencias modificadas en los campos comparados o que ya tienen fuente de
validación. No elimina registros ni archivos. Detalle de implementación y pendientes en
[el primer bloque de auditoría](../../docs/centros-id-primer-bloque-2026-10-07.md).

## Investigación y transferencia documentada

Las líneas tienen ficha científica y relaciones con proyectos, resultados, personas y
grupos. Los proyectos distinguen categoría, problema, método, actividad actual y
estado; el porcentaje de avance exige método, fecha y evidencia. Los hitos se
registran con seguimiento y generan alertas internas para gestión. El monto es
privado salvo autorización de divulgación.

Los resultados permiten filtros compartidos con exportación JSON y RIS, DOI único
por centro, versión y condiciones de acceso. TRL, protección e impacto se muestran
con metadatos de respaldo; los casos necesitan aceptación y autorización de
divulgación. Las solicitudes conservan proyecto o desarrollo y finalidad al
autenticarse. No aprueban accesos ni transferencias automáticamente.

Los archivos protegidos requieren un repositorio con control de acceso: el
almacenamiento actual es público y el guardado bloquea adjuntos confidenciales,
restringidos o bajo embargo vigente. Los plazos por revisar se consultan en la administración del centro, dentro de
«Seguimiento de gestión», únicamente por su responsable o gestores. No se muestran
como paneles laterales en la ficha ni envían notificaciones programadas.

La migración 0011 incorpora estos campos y los hitos. Reglas, administración,
verificación y pendientes en [investigación y transferencia](../../docs/centros-id-investigacion-transferencia-2026-10-07.md).

## Dependencias

```text
centros_id -> core
centros_id ~> directorio_unidades   (integración opcional)
```

- Las rutas se cargan sin configurar Django: las vistas importan los modelos
  dentro de cada función.
- Las unidades articuladas se nombran por su slug y se resuelven con
  `CENTROS_ID_UNIT_PROVIDER`; las sedes del mapa de ubicación, con
  `CENTROS_ID_SEDES_PROVIDER`. Ambos aceptan solo el proveedor registrado; sin
  proveedor no se enlazan ni se dibujan.
- No importa `webcitt` ni ninguna de las cuatro verticales de unidades. La
  ficha de cada unidad pregunta a `vinculos.centros_que_integran` a qué centro
  se integra y recibe nombres y enlaces, no modelos.

## Límite de aislamiento actual

La app tiene 42 modelos concretos y 49 tablas propias, incluidas sus relaciones
muchos a muchos. `CENTROS_DB_ENABLED=true` dirige su ORM a la base `centros`;
Unidades, autenticación y configuración institucional permanecen en `default`.
Las 19 referencias a usuarios y la relación de gestores apuntan a `CuentaCentro`,
una proyección local sin contraseñas ni privilegios. La autorización consulta
siempre la cuenta institucional vigente. No hay FK entre ambas bases.

El proceso web y el almacenamiento de archivos siguen compartidos. Separar
persistencia no implica procesos ni servicios independientes. La instalación
existente debe actualizar, copiar y verificar antes de activar el router; no
basta con cambiar una variable. Véase [operación y recuperación de Centros I+D](../../docs/separacion-centros-operacion.md).


## Escenario operativo para desarrollo local

La petición del 7 de octubre exige recorrer el CIDT con estructura y contenido
como un centro en funcionamiento. Se construye con:

```text
python manage.py construir_escenario_centros --centro cidt-upec
CENTROS_ID_ESCENARIOS_OPERATIVOS=cidt-upec
```

La segunda línea es una variable del entorno local. Se exige `DEBUG=True`;
con `DEBUG=False` las muestras vuelven a excluirse, aunque la variable esté definida.
El comando no convierte ejemplos en registros institucionales ni valida identidades.
Completa vacíos y conserva las ediciones existentes. No se ejecuta en producción.

Incluye 12 proyectos con 48 hitos, 10 resultados con fichas descargables, 28 perfiles
por función, 4 grupos, 5 actores de colaboración, 3 casos, 4 programas formativos,
actividad reciente, documentación de operación y detalle para 57 servicios.
Añade 3 activos y 3 espacios de práctica con horarios; los espacios representan
subáreas y no aumentan la superficie arquitectónica. La solicitud de uso queda
recibida hasta que gestión comprueba requisitos y confirma el intervalo.
Los cursos propios del escenario reciben solicitudes de participación; la oferta
vinculada mantiene su matrícula y aula originales.

En Equipos, espacios y herramientas se abre la calculadora de capacidad. Calcula
unidades por turno de dos etapas en serie, etapa limitante y demanda pendiente.
Es un modelo determinista educativo con entradas manuales y límites explícitos.
Los archivos y las exportaciones conservan la procedencia del escenario.
Los documentos institucionales privados permanecen privados durante la vista local.

Guía: [estructura y contenido operativo](../../docs/centros-id-escenario-operativo-2026-10-07.md).


## Acciones de la ficha

La cabecera pública ofrece «Trabajar con el centro» y un icono accesible para
compartir el enlace. La primera acción abre las opciones de solicitud por
intención ya disponibles. «Gestionar centro» aparece junto a estas acciones,
dentro de la imagen, únicamente para responsables, gestores y administradores.
Conserva el contador de solicitudes pendientes y su nombre accesible en móvil.
Abre un modal con navegación y formularios propios; no enlaza al administrador
de Django. Los accesos de edición, carpetas y bandeja abren ese mismo modal.

La cabecera sigue las proporciones de Laboratorios: altura base de 260 px,
título compacto y acciones a la derecha en escritorio; en pantallas pequeñas
se acomodan debajo del texto. Las cifras permanecen en «Conoce el centro».

«Descargar ficha del centro (PDF)» vive en Documentos y normativa. Esta sección
está disponible incluso sin otros documentos, porque la ficha PDF se genera
con los registros públicos existentes. Identidad y contacto enlaza a Documentos
y descargas. La cabecera no repite el PDF.


## Panel dinámico de gestión

La ruta privada `/centros-id/<slug>/gestion/` devuelve el panel completo;
`?fragment=1` entrega solo su contenido para el modal. Cada consulta y cada
guardado comprueba que el usuario activo sea responsable, gestor del centro
o superusuario. No requiere acceso al administrador ni condición de staff.
Las respuestas privadas no se almacenan en caché y los POST requieren CSRF.

El panel reúne nueve secciones: indicadores; solicitudes y atención; reservas
y acompañamiento; recursos y horarios; investigación y transferencia;
servicios y formación; equipo y gobierno; contenidos y documentos;
configuración. Los indicadores se consultan desde registros, y la agenda
reúne reservas confirmadas y sesiones programadas de los próximos siete días.
No calcula utilización real sin registros de ejecución.

Sus 29 tipos de registro ofrecen listas con búsqueda, paginación y formularios
para crear o editar; las solicitudes existentes se atienden desde su expediente
y conservan actor e historial. Los selectores y las consultas se limitan al
centro, incluidas relaciones indirectas y múltiples. Los formularios usan
campos explícitos: no reasignan solicitantes, centros, gestores ni privilegios,
ni alteran automáticamente procedencia o sellos de validación. En un escenario
local, el nuevo contenido demostrativo conserva esa condición.

Las reservas usan las reglas transaccionales existentes: ruta de estados,
requisitos comprobados, aforo, horarios, márgenes, bloqueos, inducción,
calibración y supervisión. El acompañamiento mantiene diagnóstico, plan,
sesiones y compromisos. No se traslada ni duplica la operación de las unidades
vinculadas. La configuración permite guardar y, mediante acciones explícitas
con respaldo, validar identidad o estado.

Un identificador de revisión impide sobrescribir un registro que cambió
mientras se editaba. El modal conserva los datos al fallar una consulta,
permite reintentar y avisa antes de descartar cambios. Al guardar actualiza
la ficha, su árbol de contenidos y el visualizador. No hay borrado masivo ni
acciones destructivas en este panel.
