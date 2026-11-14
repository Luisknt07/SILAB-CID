# Contexto de continuidad — Plataforma Científica UPEC / CITT

> Documento de traspaso para continuar el proyecto desde otros chats, equipos o
> cuentas. Leer este archivo antes de modificar la plataforma. Actualizarlo al
> terminar cada bloque importante de trabajo.

## 1. Estado de referencia

- Proyecto local: `C:\Users\PC2\Documents\GitHub\CITT`.
- Repositorio remoto: `https://github.com/COMPUMAX-EC/CITT.git` (privado).
- Rama de trabajo publicada: `reestructura-modular`.
- Código funcional de referencia: `214528b4`.
- Entrega: planificación completa de Plantas Piloto sobre el Plan Maestro;
  bloque 184 y aceptación de Laboratorios permanecen como base cerrada.
- La rama está enlazada con `origin/reestructura-modular`.
- En el momento de publicación no se fusionó ni se modificó `main`/`version2`.
- La base estable anterior permanece en `integracion-version2-funciones`.
- Pull request de la rama actual:
  `https://github.com/COMPUMAX-EC/CITT/pull/new/reestructura-modular`.
- Última suite integral: 1.402 pruebas aprobadas y una omitida. La aceptación
  enfocada de Plantas Piloto agregó 231 pruebas correctas y una omitida.
- GitHub notificó 17 alertas Dependabot en la rama predeterminada (3 altas,
  6 moderadas y 8 bajas). La actualización de dependencias debe tratarse en una
  rama separada y con pruebas de autenticación.

## 2. Objetivo institucional

La plataforma debe funcionar como **un solo sistema institucional UPEC** para
publicar y gestionar laboratorios, unidades experimentales, centros I+D,
equipos, software, espacios, servicios, inventario, reservas, mantenimiento y
reportes.

La experiencia pública debe ser clara y ligera. La operación, los indicadores,
los reportes y la administración de inventarios pertenecen al administrador y a
los responsables autorizados de cada unidad; no se deben repetir ni exponer
como grandes paneles en la ficha pública del laboratorio.

## 3. Decisiones de producto que no deben regresarse

### Ficha pública de la unidad

- Conservar la interfaz institucional ya trabajada: cabecera, identidad UPEC,
  pestañas, visualizador y navegación del módulo.
- No volver a insertar debajo del visualizador el antiguo bloque público
  **Control operativo / Estado de la unidad**.
- No mostrar al público **Gestionar unidad**; solo administradores o responsables
  autorizados pueden administrar.
- No crear una acción pública independiente **Solicitar servicio** si duplica la
  reserva. La entrada pública debe ser una sola: **Reservar / Gestión y reserva**.
- No mostrar en la ficha pública el contenedor lateral **Categorías de equipos**.
- Evitar botones o bloques repetidos como “Operación y acceso”, “Gestiona tu
  actividad”, “Control operativo” y capacidades administrativas dispersas.
- Los reportes, inventario, mantenimiento, incidencias, costos e indicadores se
  concentran en Django Admin.
- **Mis reservas** debe abrirse como modal propio, centrado, por encima de la
  página y con la misma lógica visual del modal de reserva; nunca debe quedar
  debajo del overlay ni ser imposible de seleccionar.

### Terminología de inventario

- **Insumo/consumible:** se consume, transforma o agota durante la actividad.
  Ejemplos: filamento PLA, resina fotopolimérica, reactivos químicos, cinta.
- **Material:** elemento físico reutilizable o complementario que no se consume
  necesariamente en una sola operación. Ejemplos en química: probetas, tubos y
  material de vidrio; en FabLab pueden existir accesorios o soportes
  reutilizables. La clasificación final debe configurarse por unidad.
- Organizar insumos y materiales por **familias** y luego por variantes. No
  mezclar todo en una lista plana.
- Mostrar al usuario variantes reales, unidad comprensible y existencia
  disponible. Para PLA: tipo, diámetro, color y gramos disponibles; no pedir un
  rollo completo ni una cifra en kg sin guía.
- Las cantidades solicitadas deben corresponder a la unidad operativa (g, ml,
  lámina/unidad, etc.). Cuando el usuario no conoce el consumo, debe poder pedir
  estimación o revisión técnica.
- Cada registro público puede mostrar imagen, nombre, familia, variante,
  presentación, unidad, existencia y guía de uso. La imagen se amplía en un
  visor acotado, por encima del modal principal, sin ocupar toda la pantalla.

## 4. Asistente unificado de solicitudes y reservas

El modal **Planifica tu actividad / Nueva solicitud a la unidad** es el flujo
principal. Debe ocupar bien el ancho disponible, sin panel lateral “¿Cómo
funciona?”, sin márgenes/paddings excesivos, sin scroll horizontal y sin quedar
corrido a la derecha. La reducción de `margin-top` realizada por el usuario se
debe conservar mientras no provoque colisiones en otras resoluciones.

### Paso 1 — Tipo de solicitud

Se consolidó la entrada en dos rutas conceptuales:

1. **Reservar recursos:** permite combinar en una misma solicitud equipos,
   espacios/áreas/estaciones y software/licencias.
2. **Encargar un servicio al laboratorio:** el laboratorio entrega un resultado
   técnico (diseño, fabricación, análisis o soporte).

No volver a limitar la reserva a tarjetas mutuamente excluyentes de “equipos” o
“espacios” si el caso requiere recursos combinados. El contenido de los pasos
siguientes debe activarse dinámicamente según la selección real.

La primera pantalla debe explicar ambas rutas con contenido breve y un
videotutorial genérico por ruta (dos videos en total), no un video por cada
recurso. Puede incluir un diagrama simple del recorrido.

### Paso 2 — Solicitante, participantes y propósito

- El solicitante principal se toma de la cuenta autenticada.
- Su perfil debe validar tipo de usuario, institución, facultad y carrera cuando
  corresponda. Para externos se registra su institución/procedencia y tipo.
- La carrera y facultad deben existir como datos estructurados, no texto libre,
  porque alimentan reportes de demanda por carrera, facultad, tipo de usuario y
  laboratorio.
- Los participantes secundarios se agregan mediante buscador por nombre,
  usuario o correo y solo pueden seleccionarse si ya están registrados.
- Al seleccionar un participante se recuperan automáticamente sus datos y tipo
  de usuario. No se pide una cantidad manual de usuarios: el total se deriva del
  solicitante más los participantes seleccionados.
- El propósito se elige con etiquetas/tarjetas: Docencia y práctica,
  Investigación, Vinculación, Capacitación, Servicio especializado, Proyecto de
  titulación u Otro.
- Evitar pedir que el usuario redacte un título. El **título automático** se
  genera en el último paso a partir de tipo de solicitud + propósito + recursos,
  espacio, software o servicio seleccionado.

### Paso 3 — Recursos, modalidad, responsables y calendario

Para reservas de recursos:

- Mostrar catálogos diferenciados de equipos, software/licencias y
  espacios/áreas/estaciones según lo configurado por el laboratorio.
- Permitir seleccionar combinaciones: por ejemplo equipo + software + área.
- FabLab contempla áreas de impresión 3D, corte/grabado láser, fresado/mecanizado
  CNC y digitalización/escaneo 3D.
- En equipos, mostrar imagen, características, uso, preparación, ubicación y
  disponibilidad. Ocultar al usuario observaciones internas y último
  mantenimiento; esos campos son administrativos.
- Diferenciar con claridad software de licencia, versión, tipo de acceso,
  cantidad de licencias y disponibilidad.

Para servicios:

- Mostrar los servicios configurados por la unidad, sus requisitos, qué entrega
  el laboratorio y cómo se calcula el valor.
- Modalidades:
  1. **Entrego el modelo listo:** el archivo técnico es obligatorio.
  2. **Diseño con asesoría:** el usuario trabaja en la instalación con apoyo;
     adjuntos opcionales y puede requerir área, equipos y software.
  3. **Diseño completo del laboratorio:** el equipo técnico diseña y ejecuta;
     adjuntos opcionales.
- Al hacer clic en “Entrego el modelo listo” debe aparecer inmediatamente debajo
  el cargador, sin esperar a pulsar Continuar.
- Cargador requerido: arrastrar o seleccionar, formatos permitidos, progreso,
  estado “subido/guardado”, lista con nombre/tamaño, descarga y eliminación.
- Formatos contemplados: STL, 3MF, OBJ, STEP, PDF e imágenes de referencia; la
  configuración del servicio puede ampliar o restringir la lista.
- Permitir indicaciones de visualización (software, versión, unidades, escala u
  otras instrucciones). El administrador debe poder ver y descargar el adjunto.
- No mostrar de entrada un recuadro rojo como sustituto del cargador. La alerta
  solo debe aparecer al validar una modalidad obligatoria sin archivo.
- Los archivos se persisten en `ReservaAdjunto`; no deben desaparecer al cambiar
  de paso o reabrir el resumen.

Responsable de atención:

- La unidad puede tener coordinación, responsable técnico y otras personas.
- El usuario selecciona el responsable/rol que atenderá la reserva; si hay uno
  solo se asigna automáticamente.
- Mostrar nombre/rol y datos de contacto institucionales.

Calendario:

- Ofrecer vistas **Día, Semana y Mes**.
- Mantener un tamaño intermedio: legible, completo y sin desbordar el modal.
- Mostrar disponibilidad y ocupación por día/bloque.
- Las reservas existentes deben verse como eventos con una descripción breve de
  lo reservado y el solicitante, respetando permisos y privacidad.
- La vista semanal debe distribuir días y horas de forma similar a un calendario
  laboral; la mensual resume ocupación y permite abrir el detalle del día.
- Permitir seleccionar uno o varios bloques válidos y mostrar claramente fecha y
  horas elegidas.
- El botón Continuar debe funcionar para equipos, combinaciones, software,
  espacios y las tres modalidades de servicio cuando sus requisitos estén
  completos.

### Paso 4 — Insumos, materiales y condiciones aplicables

- Para reservas, mostrar solo insumos/materiales relacionados con la unidad o
  los recursos seleccionados, organizados por familia y variante.
- Guiar con opciones: no necesito; usaré inventario de la unidad; llevaré
  materiales propios; necesito orientación/estimación.
- Para software u otros requisitos adicionales, preferir etiquetas/opciones
  preconfiguradas en vez de texto libre; el texto libre queda solo para una
  observación extraordinaria.
- Para un servicio totalmente ejecutado por el laboratorio no se obliga al
  usuario a reservar equipos ni a elegir manualmente consumibles. El sistema
  calcula internamente recursos, insumos y mano de obra.
- La aceptación de condiciones de uso, seguridad y responsabilidad **no va en el
  paso 4**; debe estar al final, antes de enviar.

### Paso 5 — Resumen, título, cotización y confirmación

- Presentar un resumen limpio únicamente con lo realmente seleccionado; no
  incluir equipos residuales/no seleccionados.
- Generar un nombre llamativo y automático para la solicitud, apto para reportes.
  Ejemplo conceptual: “Solicitud de recursos · Docencia · Impresora 3D FDM +
  Autodesk Fusion”.
- Para servicios, mostrar estimación/cotización desglosada por uso de equipos,
  insumos, mano de obra, diseño y otros costos.
- Contemplar tarifas preferenciales UPEC, descuentos por tipo de usuario y
  tarifas para externos.
- El costo cambia según el usuario entregue el diseño, lo desarrolle con asesoría
  o lo delegue completamente al laboratorio.
- Mostrar métodos de pago configurados, incluido pago físico cuando aplique.
- La cotización queda sujeta a revisión técnica y aceptación del usuario.
- Al final se aceptan las condiciones y se envía la solicitud.

## 5. Datos demostrativos FabLab

Existe el comando:

```powershell
uv run python manage.py cargar_pruebas_fablab
```

Fue creado para poblar datos de prueba del **Laboratorio de Manufactura Digital
y Prototipado**. Incluye cinco conjuntos demostrativos y, entre otros:

- Equipos: Impresora 3D FDM, Impresora 3D de resina, cortadora/grabadora láser,
  fresadora CNC de escritorio y escáner 3D.
- Software: Autodesk Fusion 2026 y Blender 4.
- Áreas: impresión 3D, corte y grabado láser, fresado/mecanizado CNC y
  digitalización/escaneo 3D.
- Inventario: PLA de 1,75 mm por colores blanco, negro, rojo, azul y gris con
  existencias separadas; resina fotopolimérica; láminas MDF y acrílico de 3 mm;
  cinta de enmascarar.
- Servicios demostrativos de fabricación/uso de equipo con recursos e insumos
  relacionados.
- Imágenes de catálogo en `webcitt/static/img/catalogo/fablab/`.

Los nombres con “dato de prueba”, “demostración” o registros de debug no deben
confundirse con inventario real de producción. Antes de un despliegue real hay
que revisar o reemplazar esos datos.

## 6. Administración y reportes

- La operación se concentra en Django Admin.
- `webcitt/admin/reportes.py` contiene reportes de uso/operación por unidad.
- `webcitt/admin/inventario.py` gestiona catálogo, clasificación, variantes,
  existencias y movimientos.
- `webcitt/admin/reservas.py` gestiona solicitudes, estados, adjuntos y reportes.
- `webcitt/admin/mantenimiento.py` gestiona planes, incidencias, órdenes,
  mantenimiento y ciclo de vida.
- `webcitt/admin/usuarios.py` expone información institucional necesaria para
  segmentación y reportes.
- Los reportes deben permitir analizar uso por laboratorio, carrera, facultad,
  tipo de usuario, propósito, recurso, servicio y estado.
- Solo superusuarios o administradores/responsables asignados a la unidad pueden
  acceder al control y reporte operativo correspondiente.

## 7. Modelo y migraciones incorporadas

El commit de referencia incorporó migraciones `0094` a `0110`, entre ellas:

- integración FabLab y generalización operativa de unidades;
- mantenimiento, incidencias y estados de equipos;
- reportes operativos;
- clasificación de consumibles/insumos/materiales, imágenes y provisión en
  reservas;
- adjuntos e indicaciones de visualización;
- flujos de software, servicios y cotización;
- perfiles institucionales y reportes;
- configuración detallada de servicios y recursos combinados;
- espacios reservables, responsables de unidad, catálogo público y tutoriales.

Archivos estructurales relevantes:

- `webcitt/domains/unidades/reservas/views.py`
- `webcitt/domains/unidades/reservas/cotizaciones.py`
- `webcitt/domains/unidades/api.py`
- `webcitt/models/reservas.py`
- `webcitt/models/consumibles.py`
- `webcitt/models/espacios.py`
- `webcitt/models/mantenimiento.py`
- `webcitt/models/usuarios.py`
- `webcitt/templates/portal/pages/unidades/detalle/modales/reserva_equipos.html`
- `webcitt/templates/portal/pages/unidades/detalle/modales/mis_reservas.html`
- `webcitt/static/portal/js/pages/unidades/reservas/reservation_wizard.js`
- `webcitt/static/portal/css/pages/unidades/reservation_wizard.css`
- `webcitt/templates/registration/profile.html`
- `webcitt/management/commands/cargar_pruebas_fablab.py`

Documentación adicional:

- `docs/arquitectura.md`
- `docs/integracion-version2.md`
- `docs/mantenimiento-equipos.md`
- `docs/inventario_estilos.md`

## 8. Pruebas y verificación requerida

Pruebas incorporadas en el commit:

- `test_calendario_reservas.py`
- `test_configuracion_servicios_fablab.py`
- `test_espacios_responsables.py`
- `test_fabricacion_publica.py`
- `test_gestion_operativa_unidad.py`
- `test_integracion_version2.py`
- `test_mantenimiento_equipos.py`
- `test_reservas.py`
- `test_tablero_operativo.py`
- `test_unidades.py`
- `test_usuarios.py`

Antes de cualquier nuevo commit o pull request ejecutar:

```powershell
uv run python manage.py makemigrations --check
uv run python manage.py migrate --plan
uv run python manage.py check
uv run python manage.py test webcitt.tests
```

También hacer validación manual en escritorio y responsive de:

1. apertura/cierre y centrado de ambos modales;
2. continuidad de todas las rutas del asistente;
3. carga, persistencia, eliminación y descarga de adjuntos;
4. calendario Día/Semana/Mes y eventos ocupados;
5. combinación equipo + software + espacio;
6. modalidades de servicio y obligatoriedad condicional de archivo;
7. perfil con facultad/carrera o datos externos;
8. ausencia del bloque público de categorías de equipos;
9. permisos de administración y reportes por unidad;
10. ausencia de scroll horizontal o contenido oculto con el `margin-top`
    reducido.

## 9. Riesgos y asuntos a revisar antes de fusionar

- La captura de GitHub mostró la rama detrás de `version2`; comparar primero y
  resolver conflictos de forma selectiva. No ejecutar `reset --hard` ni borrar
  cambios para igualar ramas.
- Confirmar en el navegador que las últimas correcciones de adjuntos, Continuar,
  calendario, modal Mis reservas, márgenes y categorías públicas están realmente
  incluidas en el commit publicado; fueron zonas con varias iteraciones y fallos
  reportados durante las pruebas visuales.
- Verificar persistencia real de los archivos y permisos de descarga desde Admin,
  no solo el cambio visual del componente.
- Revisar privacidad al mostrar “por quién” se hizo una reserva en el calendario.
- Sustituir datos demostrativos por inventario y responsables reales antes de
  producción.
- Mantener cambios de dependencias y autenticación social separados de esta
  integración funcional.

## 10. Historial resumido de decisiones e iteraciones

1. Se descartó una propuesta que añadía bloques operativos públicos debajo del
   visualizador y demasiados accesos repetidos.
2. Se devolvió la ficha pública a una experiencia de consulta y se trasladó la
   operación/reportes al administrador.
3. Se unificó solicitar servicio con el flujo de reservas.
4. Se convirtió el texto libre de consumibles en catálogo cuantificado con
   clasificación, familias, variantes e imágenes.
5. Se añadieron datos FabLab para probar equipos, servicios, software, áreas,
   insumos y materiales.
6. Se rediseñó el inventario público a filas/tablas y visor de imagen acotado.
7. Se incorporaron rutas dinámicas de reserva de recursos y encargo de servicio,
   participantes registrados, perfil institucional y título automático.
8. Se añadieron servicios con tres modalidades, adjuntos condicionales,
   trazabilidad, responsables, cotización y pagos.
9. Se amplió el calendario a Día/Semana/Mes con ocupaciones y detalle resumido.
10. Se corrigieron repetidamente botones Continuar, desbordes, espacios vacíos y
    el cargador de archivos; estas zonas requieren regresión visual cuidadosa.
11. Se ajustó el `margin-top` del modal para aprovechar mejor la altura.
12. Se adaptó Mis reservas al estilo modal y se retiró Categorías de equipos de
    la ficha pública.
13. Se ejecutaron pruebas, se creó el commit `60b2b18` y se publicó la rama
    `integracion-version2-funciones` en GitHub.

## 11. Convenciones para continuar

- No modificar la interfaz institucional global salvo que el usuario lo pida de
  forma expresa.
- No duplicar funciones públicas y administrativas.
- Mantener colores y jerarquía visual UPEC: verde institucional, azul oscuro y
  amarillo/dorado como acento.
- Priorizar datos estructurados y selecciones guiadas sobre campos de texto libre.
- Mantener los flujos flexibles y condicionales; ocultar pasos que no aplican.
- Preservar cambios no relacionados que existan en el árbol de trabajo.
- Usar migraciones para cambios de modelo y pruebas para cada regla nueva.
- No afirmar que una corrección visual está lista sin comprobarla en el navegador
  real y en más de un tamaño de pantalla.
- Antes de publicar: revisar `git status`, ejecutar pruebas, crear commit claro y
  subir una rama; no fusionar a la rama principal sin aprobación explícita.

## 12. Auditoría estructural del 27 de agosto de 2026

Se revisó la raíz, seguimiento Git, configuración Django, módulos, plantillas,
estáticos y pruebas. Resultado:

- La estructura funcional vigente es coherente: `webcitt/domains/` contiene
  portal, unidades, reservas, fabricación y usuarios; `webcitt/models/` separa
  los modelos por responsabilidad; `webcitt/admin/` concentra la operación por
  inventario, equipos, unidades, reservas, fabricación, mantenimiento, usuarios
  y reportes.
- Se eliminaron 14 archivos locales `*.log`, incluidos
  `.codex-runserver*.log`, `runserver*.log` y registros de `var/`. Eran salidas
  temporales de distintas instancias del servidor, no código ni datos.
- `.gitignore` declara expresamente `.codex-*`, `.agents/`, `.ruff_cache/`,
  `.pytest_cache/`, cobertura, entornos, logs y medios locales.
- El único `CODEX_CONTEXT.md` canónico queda en la raíz. No debe ubicarse dentro
  de `templates/admin`, porque Django podría tratarlo como parte de la capa de
  presentación y se crearían copias divergentes.
- La antigua personalización global `templates/admin/change_form.html` contenía
  navegación y formularios HTML manuales de “Unidad” que se aplicaban a todos
  los modelos y no estaban enlazados correctamente con los `ModelAdmin`. Se
  redujo a una extensión limpia que conserva únicamente los estilos UPEC y deja
  el formulario real a Django Admin.
- Se eliminó el JavaScript `admin_custom.js` y sus estilos asociados porque solo
  controlaban esas secciones administrativas antiguas ya retiradas.
- Se retiraron asignaciones repetidas de `list_display`, `list_filter` y
  `search_fields` en `webcitt/admin/unidades.py`.
- Las rutas de los logos del PDF de reservas ahora parten de
  `settings.BASE_DIR`; por eso los dos logos de `static/` en la raíz siguen
  teniendo una función y no deben borrarse todavía.
- `media/` no es basura: contiene imágenes y archivos subidos. Está ignorado
  para cargas nuevas, pero hay recursos históricos ya versionados. No moverlos
  ni borrarlos sin migrar primero sus referencias de base de datos.
- `.env` contiene configuración local sensible; `.env-example` es la plantilla
  versionable. `.venv` es el entorno Python. `.ruff_cache` y `__pycache__` son
  cachés regenerables. `.agents` pertenece al entorno de trabajo y puede
  reaparecer aunque esté ignorado; no forma parte de la aplicación.
- `var/logs/README.md` es el único archivo versionado de `var/`; explica el uso de
  esa carpeta. Los logs reales se regeneran localmente y no se versionan.

Verificación posterior a la auditoría:

```text
Ruff:                        OK
Django system check:         OK (0 incidencias)
Migraciones sin generar:     OK (No changes detected)
Plantillas admin cargables:  OK
Pruebas Django:              129/129 OK
```

La revisión visual automatizada no pudo ejecutarse porque no había un navegador
conectado al entorno de control. La regresión visual del Admin, modal de reserva
y modal Mis reservas debe comprobarse manualmente antes del próximo commit.

### Mejoras estructurales futuras, no urgentes

- Dividir `reservation_wizard.js`, `modal_reserva_equipos.js` y
  `domains/unidades/reservas/views.py` en módulos menores cuando se vuelva a
  intervenir el asistente; hoy son los principales archivos grandes del flujo.
- Revisar y migrar progresivamente los recursos históricos versionados bajo
  `media/` hacia estáticos o fixtures administrados, conservando las referencias
  existentes.
- Mantener el comando `cargar_pruebas_fablab` como generador de demostración; no
  mezclar sus datos con inventario productivo.

## 13. Clasificación institucional de centros y unidades operativas

Esta sección consolida la revisión funcional, normativa y técnica realizada el
27 de agosto de 2026. Su finalidad es impedir que el sistema aplique el mismo
modelo de reserva a estructuras que cumplen funciones diferentes.

### 13.1 Regla de arquitectura institucional

La UPEC debe operar una sola plataforma, con identidad, usuarios, permisos,
auditoría, inventario y reportes compartidos, pero con **dominios y flujos
especializados según la finalidad predominante de cada estructura**.

No se debe utilizar «laboratorio» como sinónimo de toda unidad ni tratar un
Centro I+D como un espacio reservable. La clasificación no depende únicamente
del nombre institucional; depende de su propósito, gobernanza, resultados,
escala de operación y forma de acceso.

La arquitectura conceptual acordada es:

```text
Sistema institucional UPEC
├── Centros I+D
│   ├── líneas y agendas de investigación
│   ├── investigadores, grupos y proyectos
│   ├── resultados, propiedad intelectual y transferencia
│   └── capacidades propias o vinculadas
└── Unidades/capacidades operativas
    ├── laboratorios académicos o de I+D
    ├── plantas piloto
    ├── centros experimentales
    ├── observatorios
    └── plataformas tecnológicas, como FabLab
```

Una unidad puede existir de manera autónoma, pertenecer operativamente a otra
unidad o vincular sus capacidades a uno o varios Centros I+D. La vinculación no
implica automáticamente transferencia de propiedad ni dependencia
administrativa.

### 13.2 Diferencias funcionales que debe reconocer el sistema

| Estructura | Finalidad predominante | Objeto que se gestiona | Forma principal de acceso | Resultados esperados |
| --- | --- | --- | --- | --- |
| Laboratorio académico | Práctica, experimentación, simulación y formación de competencias | Sesiones, equipos, puestos, software, prácticas e insumos | Reserva por fecha, horario, recurso y grupo | Prácticas realizadas, horas de uso, competencias y evidencias académicas |
| Laboratorio de I+D | Investigación, desarrollo, validación o innovación | Ensayos, protocolos, muestras, equipos especializados y datos | Solicitud técnica o acceso ligado a proyecto | Datos reproducibles, prototipos, validaciones, publicaciones o resultados de I+D |
| Planta piloto | Reproducir y escalar procesos en condiciones controladas | Campañas, lotes, recetas, líneas de proceso, materias primas, servicios auxiliares y control de calidad | Programación por campaña o lote, normalmente multihoraria o multidiaria | Parámetros de escalamiento, lotes piloto, rendimientos, calidad y validación de procesos |
| Centro experimental | Experimentación en condiciones reales, controladas o semicontroladas | Parcelas, invernaderos, establos, áreas, ciclos biológicos, tratamientos y muestreos | Programación por zona, ciclo, temporada o protocolo | Ensayos de campo, datos longitudinales, validaciones territoriales o productivas |
| Observatorio | Recopilar, organizar, analizar, visualizar y difundir información | Fuentes, conjuntos de datos, indicadores, metodologías, tableros, boletines y solicitudes de análisis | Solicitud de datos/análisis, suscripción o acceso a productos; no una reserva física genérica | Indicadores, series, informes, visualizaciones y evidencia para decisiones |
| Plataforma tecnológica / FabLab | Acceso transversal a capacidades de diseño, fabricación, prueba y prototipado | Equipos, software, áreas, archivos técnicos, materiales, insumos y servicios | Flujo híbrido: reserva de recursos o encargo de servicio | Prototipos, diseños, piezas, pruebas, capacitación o asistencia técnica |
| Centro I+D | Sostener una agenda científica/tecnológica e integrar capacidades, talento y proyectos | Líneas, investigadores, grupos, proyectos, financiamiento, capacidades vinculadas, resultados e impacto | Propuesta de proyecto, colaboración, acceso a capacidad vinculada o servicio científico-tecnológico | Producción científica, innovación, transferencia, propiedad intelectual e impacto |

### 13.3 Necesidades comunes y especializadas

Todas las estructuras comparten una base institucional:

- identidad, reconocimiento, estado, responsables y contactos;
- facultad o dependencia de adscripción cuando corresponda;
- capacidades, espacios, equipos, software e inventario;
- seguridad, bioseguridad, mantenimiento, costos y trazabilidad;
- usuarios internos/externos, permisos y auditoría;
- documentos, evidencias, indicadores y reportes.

Sobre esa base, cada tipo necesita módulos propios:

- **Laboratorio:** prácticas, aforo, puestos, prerrequisitos, horarios y recursos.
- **Planta piloto:** campañas, lotes, recetas, balances, materias primas,
  utilidades, limpieza, residuos, calidad, escalamiento y entregables.
- **Centro experimental:** áreas georreferenciadas, ciclos, tratamientos,
  especies/material biológico, clima, muestreos, bioseguridad y bitácoras de
  campo.
- **Observatorio:** catálogo de datos, fuentes, periodicidad, metodología,
  versiones, calidad, confidencialidad, permisos, API, tableros y publicaciones.
- **Plataforma tecnológica:** recursos combinables, archivos técnicos,
  simulación, materiales, cotización, fabricación y órdenes de servicio.
- **Centro I+D:** plan plurianual, líneas, grupos, investigadores, proyectos,
  convenios, financiamiento, hitos, resultados, propiedad intelectual,
  transferencia e indicadores científicos.

### 13.4 Diagnóstico del código actual

La documentación del proyecto ya reconoce dos dominios conceptuales en
`docs/arquitectura.md`:

- `unidades`: laboratorios, observatorios, centros experimentales, plantas
  piloto, contenido, inventario, equipos, reservas e indicadores;
- `centros_id`: investigadores, líneas, proyectos, resultados, servicios y
  transferencia.

Sin embargo, la implementación vigente está concentrada en unidades:

- `Unidad` se encuentra en `webcitt/models/core.py` y usa `dependencia` para
  clasificar laboratorios, observatorios, plantas piloto y centros
  experimentales.
- Los módulos públicos cambian parcialmente con
  `DEFAULT_MODULES_BY_DEPENDENCIA` en `webcitt/models/recursos.py`.
- La reserva en `webcitt/models/reservas.py` y el asistente de
  `webcitt/domains/unidades/reservas/views.py` conservan supuestos de recurso
  físico, fecha y bloques horarios. Cambiar `dependencia` no cambia realmente el
  motor operativo.
- `ConfiguracionOperativaUnidad` en `webcitt/models/operaciones.py` aporta
  banderas y etiquetas, pero todavía no define procesos especializados por tipo.
- `/centros-id/` es una página de portal estática servida por
  `CentrosIDView`; no existe todavía un modelo `CentroID`, dominio funcional,
  administración, API ni pruebas propias.
- `Unidad.centro_vinculado` es texto libre. No representa una relación auditable
  ni permite que una capacidad se vincule a más de un Centro I+D.
- Algunas métricas de la portada permanecen escritas directamente en la
  plantilla, por lo que no deben considerarse datos institucionales reales.
- `Categoria` y `TipoLaboratorio` requieren revisar sus `get_absolute_url()`,
  porque hacen referencia a campos que no pertenecen a esos modelos.
- El perfil de usuario aún debe evolucionar desde opciones/textos hacia
  catálogos institucionales normalizados de facultad, carrera, dependencia y
  procedencia externa.

Fotografía de la base local durante la revisión: 14 unidades —12 laboratorios,
1 observatorio y 1 centro experimental— y ninguna planta piloto registrada. No
existe aún una entidad persistente para Centros I+D. Estos conteos son datos de
desarrollo y deben volver a consultarse antes de tomar decisiones o reportarlos.

### 13.5 Modelo de datos objetivo

Conservar `Unidad` como identidad común de una capacidad operativa y añadir
perfiles especializados uno a uno:

```text
Unidad
├── PerfilLaboratorio
├── PerfilPlantaPiloto
├── PerfilCentroExperimental
├── PerfilObservatorio
└── PerfilPlataformaTecnologica
```

Crear el dominio independiente de Centros I+D:

```text
CentroID
├── LineaInvestigacion
├── GrupoInvestigacion
├── CentroInvestigador
├── ProyectoInvestigacion
├── ResultadoInvestigacion
├── ConvenioFinanciamiento
└── TransferenciaPropiedadIntelectual
```

Relaciones necesarias:

- `CentroUnidad`: relación muchos-a-muchos entre Centro I+D y capacidad propia
  o vinculada. Debe guardar modalidad, alcance, disponibilidad, reglas de
  reserva, costos, mantenimiento, seguridad, acceso, datos/resultados, vigencia
  y resolución de conflictos.
- `UnidadRelacion`: jerarquía o asociación entre unidades operativas. Ejemplo:
  una planta piloto o un laboratorio ubicado dentro de un centro experimental.
- Catálogos institucionales para facultades, carreras, dependencias, tipos de
  usuario y organizaciones externas, evitando texto libre en datos destinados a
  reportes.

No reemplazar `Unidad.centro_vinculado` hasta migrar su información a la nueva
relación y verificar referencias existentes.

### 13.6 Orquestación de solicitudes

Crear una cabecera común `SolicitudInstitucional` con código, solicitante,
participantes, propósito, unidad/capacidad, Centro I+D relacionado, responsable,
estado, prioridad, adjuntos, costos, aprobaciones, trazabilidad y fechas. Sobre
ella, activar el proceso correspondiente:

```text
SolicitudInstitucional
├── ReservaSesionRecurso
├── CampañaPiloto
├── EnsayoExperimental
├── SolicitudDatosAnalisis
├── ServicioCientificoTecnologico
└── PropuestaProyectoColaboracion
```

Reglas de experiencia:

1. El usuario primero indica **qué necesita lograr**, no qué formulario desea
   llenar.
2. El sistema identifica el tipo de unidad, modalidad de acceso y recursos
   aplicables.
3. Solo aparecen los pasos, campos y aprobaciones necesarios para ese caso.
4. La disponibilidad puede representarse por hora, campaña, lote, ciclo,
   temporada, conjunto de datos o plazo de entrega.
5. Un servicio científico-tecnológico sigue: solicitud, evaluación técnica,
   costeo/tarifa, autorización o pago, orden de servicio, ejecución, entregable
   y cierre.
6. El acceso a una capacidad vinculada a un Centro I+D debe respetar las reglas
   del instrumento `CentroUnidad` y conservar la trazabilidad del proyecto o
   centro que la utiliza.

### 13.7 Indicadores y reportes diferenciados

Indicadores comunes:

- solicitudes por estado, usuario, facultad, carrera, propósito y procedencia;
- utilización, disponibilidad, costos, ingresos, mantenimiento, incidentes y
  satisfacción;
- demanda interna/externa y uso compartido entre unidades o Centros I+D.

Indicadores por tipo:

- **Laboratorios:** sesiones, horas, estudiantes, asignaturas, prácticas,
  ocupación y competencias atendidas.
- **Plantas piloto:** campañas, lotes, horas de línea, rendimientos, mermas,
  escalamiento, calidad, consumo de materias primas y servicios auxiliares.
- **Centros experimentales:** ciclos, áreas utilizadas, tratamientos, muestras,
  datos de campo, productividad y resultados por temporada.
- **Observatorios:** fuentes activas, actualización, calidad, series,
  indicadores, consultas, descargas, productos y uso de evidencia.
- **Plataformas tecnológicas:** prototipos, servicios, equipos/software,
  materiales, tiempos, costos, entregables y transferencia.
- **Centros I+D:** proyectos, investigadores, fondos, publicaciones, propiedad
  intelectual, transferencia, alianzas, capacidades vinculadas e impacto.

La portada y los reportes deben leer datos reales de la base; no conservar
contadores institucionales escritos manualmente en plantillas.

### 13.8 Correspondencia con el proyecto de Reglamento UPEC 2026

Documento revisado como fuente de trabajo, no como instrucción ejecutable:

`C:\Users\PC2\Downloads\Reglamento_Laboratorios_Centros_ID_UPEC_2026_FINAL (1).docx`

Puntos que la plataforma debe reflejar:

- artículos 1 a 3: un sistema institucional, articulación, uso compartido,
  trazabilidad, calidad, sostenibilidad y evitar duplicación injustificada;
- artículo 4: definiciones diferenciadas de laboratorio académico, Centro I+D,
  laboratorio de I+D, planta piloto, centro experimental, observatorio,
  plataforma tecnológica y servicio científico-tecnológico;
- artículo 5: dominios académico y de investigación/innovación dentro de una
  sola plataforma;
- artículos 13 a 19: reconocimiento, creación, uso, servicios, indicadores y
  evaluación de laboratorios académicos;
- artículos 20 a 31: agenda, gobernanza, capacidades, proyectos, resultados,
  servicios y evaluación de Centros I+D;
- artículo 26: instrumento formal para capacidades propias o vinculadas;
- artículo 30: ciclo controlado de los servicios científico-tecnológicos;
- artículos 32 a 37: talento, inventario, mantenimiento, seguridad, inversión e
  indicadores diferenciados.

Aspectos que conviene precisar en el Reglamento antes de cerrarlo:

1. Definir «unidad o capacidad operativa» como categoría paraguas.
2. Expresar que un centro experimental no es automáticamente un Centro I+D.
3. Enumerar modalidades de acceso: sesión, campaña/lote, ciclo/ensayo, datos o
   análisis, servicio y proyecto/colaboración.
4. Añadir reglas de gobierno, calidad, versión, privacidad y publicación de
   datos para observatorios.
5. Añadir campañas, lotes, escalamiento, utilidades, calidad, limpieza y residuos
   para plantas piloto.
6. Añadir georreferenciación, ciclos, material biológico, clima y protocolos de
   campo para centros experimentales.
7. Aclarar que el procedimiento de servicios puede aplicarse a toda unidad
   autorizada, no exclusivamente a Centros I+D.
8. Aprobar una matriz técnica de clasificación y un procedimiento de
   reclasificación basado en la finalidad predominante.

### 13.9 Fuentes oficiales consultadas

- Reglamento UPEC 2026 en elaboración, ruta local indicada en 13.8.
- Estatuto UPEC 2026: `https://upec.edu.ec/images/stories/Elecciones_CSUP/2026/Estatuto_UPEC.pdf`.
- Reglamento de Régimen Académico del CES:
  `https://www.ces.gob.ec/lotaip/2022/Octubre/a3/Reglamento%20de%20R%C3%A9gimen%20Acad%C3%A9mico.pdf`.
- Modelo de evaluación externa CACES:
  `https://www.caces.gob.ec/blog-post/caces-aprobo-el-modelo-de-evaluacion-externa-con-fines-de-acreditacion-para-las-universidades-y-escuelas-politecnicas/`.
- Manual de Frascati de la OECD:
  `https://www.oecd.org/content/dam/oecd/en/publications/reports/2015/10/frascati-manual-2015_g1g57dcb/9789264239012-en.pdf`.
- ISO/IEC 17025:
  `https://www.iso.org/standard/66912.html`.
- Infraestructuras tecnológicas de la Comisión Europea:
  `https://research-and-innovation.ec.europa.eu/research-area/industrial-research-and-innovation/technology-infrastructures_en`.
- Infraestructuras de investigación de la Comisión Europea:
  `https://research-and-innovation.ec.europa.eu/strategy/strategy-research-and-innovation/our-digital-future/european-research-infrastructures_en`.
- Guía de observatorios de ONU-Hábitat:
  `https://unhabitat.org/sites/default/files/2020/06/urban_observatory_guide.pdf`.
- Referencia INIAP sobre estaciones experimentales:
  `https://repositorio.iniap.gob.ec/items/eab812e8-031c-4961-bf46-e30451ce66ae`.
- Referencias de plantas piloto del Departamento de Energía de EE. UU.:
  `https://www.energy.gov/cmei/fuels/full-text-glossary` y
  `https://www.energy.gov/cmei/fuels/articles/national-laboratory-pilot-plants-help-industry-de-risk-biofuel-processes`.

### 13.10 Orden recomendado para continuar

1. Corregir defectos puntuales del modelo actual y eliminar métricas estáticas.
2. Normalizar facultades, carreras, dependencias y procedencias de usuarios.
3. Crear perfiles operativos especializados sobre `Unidad` y una matriz de
   clasificación/migración para las unidades existentes.
4. Introducir `SolicitudInstitucional` y adaptar primero los flujos actuales de
   laboratorio/FabLab sin romper `Reserva`.
5. Implementar progresivamente campaña piloto, ensayo experimental y solicitud
   de datos/análisis.
6. Crear `CentroID`, su administración, permisos, líneas, investigadores,
   proyectos, resultados y reportes.
7. Implementar `CentroUnidad` y `UnidadRelacion`, migrando el texto
   `centro_vinculado` de manera controlada.
8. Añadir servicios científico-tecnológicos transversales con evaluación,
   cotización, orden, entregable y cierre.
9. Validar la clasificación y los flujos con responsables reales de cada tipo de
   estructura antes de desplegarlos.

La siguiente fase técnica recomendada es diseñar e implementar los perfiles por
tipo de unidad y la configuración de modalidades de solicitud. Construir primero
una pantalla completa de Centros I+D sin estas relaciones volvería a crear dos
sistemas aislados y duplicaría capacidades.

## 15. Cierre de validación visual del flujo de recursos — 27 de agosto de 2026

Se validó manualmente en el navegador la ruta completa de una reserva de equipo
en el Laboratorio de Manufactura Digital y Prototipado: datos y participantes,
catálogo de equipos, insumos/materiales y confirmación. El modal utiliza el ancho
disponible sin desbordamiento horizontal y permite avanzar entre los cinco pasos.

### Ajustes posteriores a la validación

- El contador de participantes secundarios inicia en cero y cuenta únicamente a
  las personas agregadas; el solicitante principal permanece separado.
- La confirmación ya no presenta valores técnicos como
  `2026-08-28T09:00 · [9,11]`. La fecha se muestra en español y los bloques
  horarios contiguos o separados se convierten en intervalos legibles.
- El tipo de solicitud se calcula con las selecciones reales: reserva de equipo,
  equipos, espacio, espacios, software, licencia(s) o reserva combinada cuando se
  utilizan categorías diferentes.
- Se incrementó el contrato visual del asistente a
  `20260827-summary-v20` para invalidar recursos estáticos anteriores del
  navegador.

### Verificación de este bloque

```text
Sintaxis JavaScript (node --check):  OK
Ruff:                                OK
Django system check:                 OK (0 incidencias)
Migraciones sin generar:             OK (No changes detected)
Pruebas de reservas:                 34/34 OK
Suite Django completa:              135/135 OK
```

Permanece únicamente la advertencia local conocida de Django porque no existe
`static_deployed/`; no afecta las pruebas ni el servidor de desarrollo.

## 14. Primera implementación de perfiles operativos — 27 de agosto de 2026

Se inició la fase recomendada sin modificar todavía las URLs públicas ni el
asistente de reservas. El objetivo de este bloque es separar la identidad y el
catálogo actual de una unidad de su finalidad y comportamiento operativo.

### Cambios incorporados

- `Unidad` incorpora `clasificacion_funcional` con las opciones:
  laboratorio académico, laboratorio de I+D, laboratorio mixto, planta piloto,
  centro experimental, observatorio y plataforma tecnológica.
- `dependencia` se conserva como clasificación de catálogo y compatibilidad. Por
  ejemplo, un FabLab puede continuar dentro del catálogo de laboratorios y
  operar como plataforma tecnológica.
- Se eliminaron los métodos `get_absolute_url()` inválidos de `Categoria` y
  `TipoLaboratorio`; utilizaban campos `dependencia` y `slug` inexistentes.
- Se añadió `webcitt/models/perfiles_unidad.py` con cinco perfiles uno-a-uno:
  `PerfilLaboratorio`, `PerfilPlantaPiloto`, `PerfilCentroExperimental`,
  `PerfilObservatorio` y `PerfilPlataformaTecnologica`.
- Cada perfil contiene únicamente condiciones especializadas de su dominio y
  conserva en `ConfiguracionOperativaUnidad` las capacidades transversales ya
  existentes.
- Las señales crean el perfil correspondiente al registrar o reclasificar una
  unidad. Una reclasificación crea el nuevo perfil sin borrar automáticamente el
  anterior, para no perder configuración histórica.
- Django Admin muestra la clasificación funcional en la lista/filtros y carga
  solamente el perfil especializado que corresponde a la unidad editada.
- La migración `0111_unidad_clasificacion_funcional_and_more.py` clasifica las
  unidades existentes y crea sus perfiles. Detecta FabLab/manufactura digital
  como plataforma tecnológica; las demás unidades reciben la clasificación
  predeterminada compatible con su dependencia.
- Se añadieron pruebas de valores predeterminados, perfiles automáticos,
  compatibilidad de clasificación, reclasificación conservadora y validaciones.

### Estado local después de migrar

```text
Centro experimental:          1
Laboratorios académicos:     10
Plataformas tecnológicas:     2
Observatorios:                1
Plantas piloto:               0
```

Las plataformas detectadas fueron `FabLab Impresión 3D` y `Laboratorio de
Manufactura Digital y Prototipado`. Esta clasificación debe validarse con los
responsables institucionales antes de considerarse definitiva.

### Verificación

```text
Ruff:                         OK
Django system check:          OK (0 incidencias)
Migraciones sin generar:      OK (No changes detected)
Pruebas focalizadas:          20/20 OK
Suite Django completa:       135/135 OK
Migración local 0111:         aplicada correctamente
```

La conexión del navegador no estuvo disponible para el controlador durante esta
sesión, aunque el usuario indicó estar conectado. La validación visual del nuevo
inline administrativo sigue pendiente. Para habilitarla, conectar el navegador
desde **Settings → Computer use** y mantener abierta la aplicación local.

### Próximo bloque recomendado

No crear todavía `SolicitudInstitucional`. Primero se debe conectar la
clasificación funcional con una **matriz de modalidades de acceso** que determine
qué flujos admite cada unidad: sesión/recurso, campaña/lote, ensayo/ciclo,
datos/análisis o servicio técnico. Esa matriz debe extender
`ConfiguracionOperativaUnidad`, conservar las reservas actuales y controlar de
forma explícita qué pasos presenta el asistente.

## 16. Períodos y calendario académico institucional — 27 de agosto de 2026

Se reemplazó la dependencia funcional de un texto libre como `2026-B` por una
estructura temporal institucional que permite conservar reformas de calendario
y clasificar las reservas sin reescribir el historial.

### Estructura incorporada

- `PeriodoAcademico` identifica el período estable: año, ciclo A/B o
  extraordinario, tipo, ámbito, número planificado de semanas y estado.
- `VersionCalendarioAcademico` conserva el calendario original y cada reforma,
  con fechas, resolución, documento, fuente y una sola versión vigente.
- `SemanaAcademica` modela los cortes numerados del período. Puede distinguir
  clases, evaluación, recuperación, vacaciones o suspensión, e indicar si la
  semana admite reservas y si debe incluirse en reportes.
- `VinculacionUsuarioPeriodo` conserva el tipo de usuario, facultad, carrera,
  nivel, paralelo e institución que una persona tuvo en ese período. Por ello,
  el cambio semestral de carrera o nivel no altera los reportes anteriores.
- `Reserva` conserva simultáneamente la relación con período, versión y semana,
  además de los campos de texto/número históricos para trazabilidad.
- `CatalogoActividadReserva` puede asociar una asignatura, proyecto o actividad
  a un período administrado.

### Comportamiento de las reservas

- La interfaz ya no solicita al usuario que escriba el período.
- Una actividad catalogada aporta su período; de lo contrario, la fecha elegida
  se cruza con la versión vigente del calendario publicado.
- Al guardar se congelan período, versión y número de semana. Una reforma futura
  no cambia la clasificación de solicitudes ya registradas.
- Si todavía no existe calendario publicado, el sistema no bloquea las reservas
  heredadas. Los registros quedan identificables como `Sin período` o
  `Sin semana` hasta completar la configuración administrativa.
- Cuando exista un calendario publicado, una actividad docente fuera de sus
  fechas se rechaza para evitar indicadores inconsistentes.

### Administración y reportes

- Django Admin permite gestionar períodos, versiones, semanas y vinculaciones de
  usuarios. La acción **Generar semanas académicas faltantes** crea los cortes
  semanales a partir de la versión seleccionada.
- El reporte institucional de uso permite filtrar por período, semana académica
  y rango de fechas, y agrupar por semana académica, semana calendario, mes,
  trimestre calendario, período académico o año.
- El período académico es el corte semestral institucional. Mes y trimestre son
  cortes calendario y no deben utilizarse como sustitutos del período A/B.
- La migración `0114_periodoacademico_reserva_semana_academica_numero_and_more.py`
  transforma códigos históricos en períodos borrador y enlaza las actividades y
  reservas existentes sin inventar fechas oficiales.

### Configuración pendiente con datos oficiales

El registro local `2026-B` existe como borrador. Antes de activar la asignación
automática, un administrador debe cargar las fechas y el documento aprobado,
generar/revisar las 16 semanas y cambiar el período a `Publicado`. No se deben
inferir fechas institucionales a partir de capturas o ejemplos.

### Verificación

```text
Django system check:          OK (0 incidencias)
Migraciones sin generar:      OK (No changes detected)
Migración local 0114:         aplicada correctamente
Pruebas del calendario:       4/4 OK
Pruebas de reservas:         52/52 OK
Suite Django completa:      143/143 OK
```

La validación visual automatizada no estuvo disponible porque el paquete local
de control del navegador indicado por Codex no existía en la ruta configurada.
La plantilla del reporte sí fue renderizada y validada mediante pruebas Django.

## 17. Operación intersemestral y fines de semana — 28 de agosto de 2026

El calendario y el horario de una unidad se separaron porque no representan lo
mismo. El período clasifica institucionalmente la actividad y el horario define
cuándo y para quién puede operar cada laboratorio.

### Períodos contemplados

- Los ciclos ordinarios continúan como `A` y `B`, normalmente con 16 semanas.
- El ciclo `E` identifica un período extraordinario.
- El nuevo ciclo `I` identifica un interperíodo institucional, por ejemplo
  `2026-I1`. Sus fechas y cantidad de semanas se cargan desde el calendario
  aprobado; no deben inferirse ni copiarse de un período ordinario.
- `SemanaAcademica` incorpora el tipo `operacion_interperiodo`. La acción
  administrativa que genera semanas lo utiliza automáticamente cuando el
  período es intersemestral.
- Cada semana mantiene `permite_reservas`; por tanto se pueden bloquear feriados,
  cierres, mantenimiento o suspensiones aunque exista un horario de la unidad.

### Horarios administrables por unidad

`HorarioOperacionUnidad` normaliza la disponibilidad que antes era solamente un
texto descriptivo. Cada jornada define:

- unidad, día de lunes a domingo y rango horario;
- horario general o período específico;
- si admite reservas de recursos, solicitudes de servicio o ambos flujos;
- tipos de usuario habilitados;
- propósitos institucionales habilitados;
- estado y observaciones internas.

Una unidad nueva recibe como base lunes a viernes de 07:00 a 20:00. Sábados y
domingos no se presuponen: el administrador debe habilitarlos explícitamente.
Cuando existen jornadas para un período concreto, esas jornadas reemplazan por
completo el horario general durante sus fechas. Esta regla permite, por ejemplo,
que durante `2026-I1` un laboratorio atienda los sábados de 08:00 a 13:00 solo
servicios de investigación para docentes e investigadores, sin abrir reservas
académicas ordinarias para estudiantes.

La configuración se realiza desde **Administrador → Unidades → Horarios
operativos** o dentro de la propia unidad. La interfaz pública solo consulta las
reglas vigentes; no permite modificarlas.

### Comportamiento del asistente de reservas

- El calendario deja de asumir lunes a viernes y 07:00–20:00.
- Las vistas diaria, semanal y mensual calculan días y bloques desde el horario
  general o el horario específico del período.
- La semana muestra los siete días cuando la unidad puede operar en fin de semana.
- Se filtran las jornadas por flujo, modalidad, propósito y tipo de usuario. Una
  modalidad de servicio con diseño asistido exige también acceso a recursos.
- Los bloques seleccionados deben ser consecutivos y pertenecer a una misma
  jornada habilitada.
- La ficha pública de la unidad resume el horario general e indica cuando puede
  variar por período.
- El servidor repite todas las validaciones. Manipular el navegador no permite
  crear una solicitud fuera de jornada ni dentro de una semana cerrada.

### Indicadores y trazabilidad

Las solicitudes intersemestrales quedan relacionadas con su período `I`, versión
de calendario y semana. Los reportes pueden incluirlas o filtrarlas de forma
independiente de los períodos A/B y conservar el tipo de usuario que la persona
tenía en ese momento mediante `VinculacionUsuarioPeriodo`. Esto permite comparar:

- uso ordinario frente a uso intersemestral;
- actividades por semana, mes, trimestre, período y año;
- atención en días laborables frente a fines de semana;
- recursos y servicios usados por estudiantes, docentes, investigadores,
  personal UPEC y usuarios externos;
- propósitos institucionales y unidades con mayor demanda.

### Verificación

```text
Sintaxis JavaScript:                  OK
Ruff:                                OK
Django system check:                 OK (0 incidencias)
Migraciones sin generar:             OK (No changes detected)
Pruebas focalizadas:                 49/49 OK
Suite Django completa:              150/150 OK
```

La migración es `0115_horarios_operativos_interperiodo.py`. Se aplicó en la base
local y crea el horario general para las unidades existentes. No se creó un
`2026-I1` institucional real porque sus fechas deben proceder de una resolución
o calendario aprobado por la UPEC.

## 18. Ciclo institucional, comprobante y cambios controlados — 4 de septiembre de 2026

Este bloque cierra el trabajo que quedó sin confirmar en el árbol después del
commit `4712a0e`. La definición funcional vive en
[`docs/ciclo-institucional-laboratorios.md`](docs/ciclo-institucional-laboratorios.md)
y los estados ejecutables en `webcitt/workflows/reservas.py`. Ese módulo es la
fuente única: las vistas, el calendario y las tareas automáticas no deben volver
a declarar listas locales de estados.

### Qué se incorporó

- **Máquina de estados única** (`webcitt/workflows/reservas.py`): estados,
  conjuntos derivados (`ESTADOS_OCUPAN_AGENDA`, `ESTADOS_APROBADOS`,
  `ESTADOS_CERRADOS`, `ESTADOS_ATENCION_EFECTIVA`) y reglas de transición con
  origen, destino y exigencia de motivo.
- **Compuerta documental** (`webcitt/domains/unidades/practicas_integracion.py`):
  `estado_documental_reserva()` y `validar_compuerta_documental()` impiden
  aprobar, iniciar o completar mientras falte una guía obligatoria. Rechazar y
  cancelar siguen disponibles para cerrar una solicitud inviable.
- **Comprobante de la solicitud** (`webcitt/domains/unidades/reservas/comprobantes.py`,
  `templates/portal/pages/unidades/reservas/comprobante.html`): una sola
  construcción del contenido que se muestra en pantalla, se envía por correo y
  se descarga en PDF.
- **Cambios controlados** (`cambios.py`, `cambios_views.py`): el titular solicita
  el cambio, el laboratorio autoriza grupos de campos por 48 horas, la propuesta
  se guarda separada de la reserva vigente y solo `aplicar_solicitud_cambio`
  la traslada, revalidando agenda, recursos e insumos. Estados de la solicitud:
  `solicitada`, `autorizada`, `enviada`, `aprobada`, `rechazada`, `vencida`,
  `cancelada`; una sola activa por reserva.
- **Revisiones inmutables** (`RevisionReserva`): cada cambio aplicado crea una
  versión que conserva responsable y motivo. El historial no se sobrescribe.
- **Firma electrónica interna de guías** (`guia_firmas.py`): aceptación con
  usuario, momento y huella SHA-256 del contenido. Si cambia cualquier dato, la
  firma deja de verificar y debe repetirse.
- **Costos referenciales y liquidación real**: la unidad configura tarifas y
  aporte institucional (migración `0146`); la reserva guarda la fotografía
  económica usada al enviar y la liquidación real al cerrar (migración `0147`).
- **Planificación FT02 automática**: cada reserva de recursos genera su
  planificación por sesión, incluidas las series semanales. «Sin guía» se
  presenta como **No aplica**, nunca como documento faltante.

### Migraciones de este bloque

`0143` notificación de confirmación · `0144` revisiones y solicitudes de cambio ·
`0145` `requiere_guia` en planificación · `0146` costos referenciales por unidad ·
`0147` liquidación real de la reserva. Todas aplicadas en la base local.

### Comandos idempotentes incorporados

```powershell
.\.venv\Scripts\python.exe manage.py inicializar_revisiones_reservas
.\.venv\Scripts\python.exe manage.py sincronizar_planificaciones_reservas
```

El segundo admite `--simular` y `--unidad <slug>`.

## 19. Auditoría del 4 de septiembre de 2026

Revisión del árbol de trabajo antes de confirmar. Estado verificado:

```text
Ruff:                        OK
Django system check:         OK (0 incidencias)
makemigrations --check:      OK (No changes detected)
migrate --plan:              sin operaciones pendientes
Sintaxis JavaScript:         OK (4 archivos del asistente)
Pruebas Django:              312/312 OK
```

### Defectos corregidos durante la auditoría

1. **`codigo_reserva` quedaba nulo en memoria.** La señal `post_save` usaba
   `queryset.update()`, que escribe en la base pero no toca la instancia. Quien
   acababa de crear la reserva seguía leyendo `None`. El asistente lo compensaba
   regenerando el mismo código a mano en dos lugares más, de modo que el formato
   `RL{lab:03d}-{id:06d}` vivía triplicado. Ahora existe
   `Reserva.construir_codigo_reserva()` como única definición, la señal actualiza
   también la instancia y se eliminaron las dos duplicaciones.
2. **La asignatura escrita por el docente se descartaba.** El asistente pide
   «Asignatura o actividad formativa» como campo obligatorio y editable, pero el
   formulario la trataba como dato operativo bloqueado y la reemplazaba por el
   nombre corto de la actividad. Se separó `CAMPOS_AUTOMATICOS_RESERVA` (datos
   operativos que nunca son texto libre) de `CAMPOS_ACADEMICOS_PROPUESTOS`
   (asignatura y precauciones, que la reserva propone y el docente redacta).
3. **Las precauciones específicas de la actividad se perdían.** El apartado de
   seguridad quedaba deshabilitado cuando la guía provenía de una reserva, así
   que solo sobrevivía la política institucional. Ahora la política encabeza
   siempre el apartado, las precauciones del autor se agregan a continuación y la
   fusión es idempotente: reeditar la guía no duplica las líneas institucionales.
   El editor muestra la política como bloque de solo lectura y las precauciones
   como campo editable.
4. **Prueba acoplada a una versión de estáticos.** `test_unidades` exigía el
   literal `20260903-unified-request-v69`, que ya no existía. Ahora comprueba que
   el modal cargue su archivo con marcador de versión, sin fijar el valor.
5. **Import sin uso** de `SolicitudCambioReserva` en `gestion.py`.

### Puntos abiertos que no se tocaron en este bloque

- **La portada sigue con métricas inventadas.** `inicio.html` mantiene escritos a
  mano «6 Centros I+D», «48 Laboratorios», «356 Reservas este mes», «312 Equipos»,
  «84 Proyectos», «24 Normativas», además de noticias con fechas de 2025 y cifras
  de impacto. `InicioView` no consulta la base. Es el punto visible más alejado
  del resto del sistema y debe leer datos reales o retirarse.
- **La rama va 20 commits por detrás de `origin/version2`**, que incluye
  actualizaciones de seguridad no presentes aquí: Django 4.2.17 → 4.2.30,
  django-allauth 0.57.0 → 65.19.0, cryptography 46.0.3 → 50.0.0, idna 3.6 → 3.15,
  PyJWT 2.8.0 → 2.13.0 y python-dotenv 1.0.0 → 1.2.2. El salto de allauth es de
  versión mayor y `version2` ya resolvió su adaptación en `webcitt/adapters.py`.
  Debe integrarse en una rama propia, con pruebas de autenticación social.
- **`webcitt/domains/unidades/gestion.py` tiene 5516 líneas.** Es el archivo más
  grande del proyecto y concentra panel, acciones operativas y contexto. Conviene
  dividirlo cuando se vuelva a intervenir, junto con `reservation_wizard.js`
  (3951 líneas) y `reservas/views.py` (2707 líneas).
- **Sigue pendiente la validación visual en navegador** de comprobante, solicitud
  de cambio y guía integrada.

## 21. Retiro de la entrada paralela `/fabricacion/` — 4 de septiembre de 2026

### Diagnóstico

La revisión inicial supuso que `SolicitudFabricacion` era un modelo heredado que
duplicaba el encargo de servicios. **No lo es.** El asistente unificado lo crea
como **orden de servicio** cada vez que se envía una solicitud con
`tipo_solicitud == "servicio"`, enlazada a la reserva por
`Reserva.solicitudes_operativas`. Es exactamente el expediente que describe
`docs/ciclo-institucional-laboratorios.md`: «una solicitud de servicio no crea
FT02: genera una orden de servicio».

Las cuatro solicitudes de la base local lo confirman: todas tienen `reserva`
vinculada y su nombre procede del asistente
(«Solicitud de servicio: … · Modalidad: …»).

Lo que sí estaba duplicado era la **entrada pública** `/fabricacion/`: un
formulario independiente que creaba órdenes **sin reserva, sin agenda, sin
cotización, sin responsable y sin compuerta documental**. No estaba enlazado
desde ninguna plantilla fuera de su propia carpeta.

### Qué se conserva

- `SolicitudFabricacion` y `SolicitudConsumible`: son la orden de servicio del
  flujo vigente.
- `webcitt/admin/fabricacion.py`: la unidad gestiona ahí revisión del
  laboratorista, aprobación de Decanato, costos y comprobante de pago.
- `EquiposServicios`: catálogo transversal, sin relación con el módulo retirado.

### Qué se retiró

- `webcitt/domains/fabricacion/` (vistas, formulario, servicios y rutas).
- `webcitt/templates/fabricacion/`.
- `webcitt/static/portal/{css,js}/pages/fabricacion/`.
- La inclusión `path('fabricacion/', ...)` en `webcitt/urls.py`.
- `webcitt/tests/test_fabricacion_publica.py`.

Total: 723 líneas y 10 archivos.

### Capacidad preservada: comprobante de pago

La única función exclusiva de la entrada retirada era que el solicitante
adjuntara su respaldo de pago. Se trasladó al comprobante unificado, sobre la
misma orden de servicio:

- Vista `subir_comprobante_pago` en `reservas/notificaciones_views.py`.
- Ruta `reservas/<id>/comprobante/pago/`.
- Bloque en `portal/pages/unidades/reservas/comprobante.html`, visible solo para
  el titular y solo cuando la reserva tiene orden de servicio.
- Acepta PDF, PNG, JPG o WEBP hasta 5 MB. La verificación del pago sigue siendo
  del personal, desde el administrador.
- `webcitt/tests/test_comprobante_pago_servicio.py` cubre subida válida, formato
  rechazado, acceso ajeno y visibilidad del bloque.

### Verificación

```text
Ruff:                        OK
Django system check:         OK (0 incidencias)
Pruebas Django:              305/305 OK
```

El total baja de 312 a 305: se retiran las 11 pruebas de la entrada pública y se
incorporan 4 del comprobante de pago.

## 22. Motor único de reportes de uso — 4 de septiembre de 2026

### Problema

Existían dos reportes que respondían la misma pregunta con definiciones
propias:

- **Panel de la unidad** (`gestion_reportes.py`): 8 dimensiones, horas y
  asistencia calculadas desde la ejecución real.
- **Institucional** (`admin/reservas.py::reporte_uso_view`): 8 dimensiones
  distintas más cortes de tiempo, agregación por base de datos con
  `Sum('duracion')` y conteo por estado.

No solo ofrecían dimensiones diferentes: **medían distinto**. Una atención de
09:00 a 12:00 solicitada y ejecutada de 09:00 a 11:00 aparecía como 2 horas en
el panel y como 3 en el administrador. El responsable de la unidad veía además
menos dimensiones que el administrador, pese a que los datos ya estaban en
`Reserva`.

### Solución

`webcitt/domains/unidades/reportes_dimensiones.py` define una sola vez:

- `horas_efectivas(reserva)`: prioriza el horario real sobre el planificado.
- `participantes(reserva)`: asistencia conciliada cuando la atención se cerró.
- `DIMENSIONES`: 19 dimensiones con clave, etiqueta, resolución y ámbito.
- `agrupar(reservas, clave)`: filas con total, efectivas, horas, participantes
  y porcentaje.
- `es_multiple(clave)`: marca las dimensiones en las que una reserva puede
  aparecer en varias filas.

Ambos reportes lo consumen. Las etiquetas dejan de escribirse dos veces: el
administrador presenta cada sección como «Uso por {etiqueta en minúscula}».

### Dimensiones nuevas en el panel de la unidad

De 8 a 19. Se incorporan **facultad beneficiaria**, **período académico**,
**semana académica**, **semana calendario**, **mes**, **trimestre**, **año**,
**tipo de jornada**, **tipo de actividad**, **vinculación** y **recurso
utilizado**.

`recurso` es la única dimensión múltiple: una solicitud que combina equipo,
espacio y software aparece en tres filas, porque la pregunta que responde es
cuánto se usa cada recurso, no cuántas solicitudes hubo. Ambos reportes lo
advierten en pantalla.

### Métricas alineadas en el institucional

La columna «Aprobadas» (estado en confirmada/en_proceso/completada) pasa a
**«Efectivas»**, con el mismo criterio del panel: cerrada, atendida y con
ejecución registrada. Se añade la columna de participantes. Las participaciones
por tipo de usuario, facultad y carrera usan el mismo conjunto de reservas
efectivas en lugar de un filtro por estado propio.

### Costo asumido

El institucional deja de agregar en la base de datos y materializa las reservas
filtradas para calcular en Python. Es la consecuencia de medir con la ejecución
real, que vive en un `JSONField`. La vista ya filtra por unidad, período y rango
de fechas; si el volumen creciera hasta hacerlo lento, la salida sería
persistir horas y asistencia efectivas en columnas al cerrar la atención, no
volver a dos definiciones distintas.

### Verificación

```text
Ruff:                        OK
Django system check:         OK (0 incidencias)
Pruebas Django:              312/312 OK
```

`webcitt/tests/test_reportes_dimensiones.py` fija las métricas, la dimensión
múltiple y —lo importante— que ambas pantallas informen las mismas horas y
participantes para el mismo dato.

## 23. Coincidencia entre superficies de la reserva — 5 de septiembre de 2026

Objetivo pedido por el usuario: que el asistente y su comprobante, **Mis
reservas**, **Gestionar laboratorio** y el **administrador de Django** muestren la
misma reserva sin duplicados ni distorsión, y que ninguna superficie pueda
saltarse las reglas que otra aplica.

### Distorsiones corregidas

1. **El administrador se saltaba todas las reglas.** `ReservaAdmin` permitía
   editar `estado`, horario, recursos, participantes y cotización directamente;
   sus acciones masivas «Confirmar» y «Cancelar» hacían `queryset.update()`, sin
   compuerta documental, sin responsable, sin motivo, sin revisión, sin FT02, sin
   notificación, sin auditoría y sin disparar señales. Ahora `ReservaAdmin`
   hereda de `_ExpedienteSoloLecturaAdmin` (el patrón que el proyecto ya usaba
   para revisiones y solicitudes de cambio): todo es de consulta, incluidos los
   inlines, y el formulario enlaza a «Abrir en Gestionar laboratorio». Lo mismo
   para el ciclo documental de la guía (`estado_publicacion`, `es_vigente`,
   `contenido`, firmas) y para el FT02 (`estado`, `es_version_vigente`, `guia`,
   `reserva`).
2. **Validar la ejecución FT03 cerraba la reserva con un `update()` crudo.** Ahora
   pasa por `validar_compuerta_documental` y `validar_accion_reserva`, guarda con
   `save()`, registra auditoría y notifica, igual que el panel. Si la reserva no
   admite la transición, la validación se rechaza con mensaje y sin cambios.
3. **Una reserva cerrada conservaba su solicitud de cambio activa.**
   `cerrar_solicitudes_activas()` en `cambios.py` la pasa a `cancelada` con motivo
   cuando la reserva sale de pendiente/confirmada, desde el panel y desde la
   cancelación del titular.
4. **Mis reservas repetía listas de estados a mano** y omitía `completada` entre
   los cerrados. El JSON de `obtener_reservas_usuario` entrega `es_cerrada`,
   `ocupa_agenda`, `puede_cancelar` y `puede_solicitar_cambio` derivados de
   `workflows/reservas.py`; el JS los consume.
5. **Los mensajes de Django no se mostraban en el portal.** Solo dos plantillas
   de prácticas los renderizaban; el rechazo de un comprobante de pago era
   invisible y el aviso aparecía después fuera de contexto. El layout
   `portal/layouts/base.html` los muestra ahora en todas las páginas.
6. **Los enlaces de seguimiento apuntaban a `#mis-reservas`, un ancla sin
   destino.** Ahora llevan `?reserva=<id>#mis-reservas` y el modal se abre solo
   con esa reserva seleccionada.
7. **«Nueva versión» de la guía creaba borradores duplicados.** Solo puede haber
   una versión en trabajo; la vista ofrece «Continuar la versión N en trabajo».
8. **Los PDF de respaldo que pedían publicación quedaban en «revisión» sin
   pantalla que los decidiera.** La aprobación de la guía estructurada de la
   actividad los resuelve con la visibilidad solicitada.
9. **El contador «Por revisar» del panel** se calculaba sobre las 40
   planificaciones más recientes; ahora cuenta toda la unidad.
10. **Las estadísticas del administrador** llamaban «no aprobadas» a las reservas
    en proceso y completadas, y el PDF imprimía «Periodo: PAO-2025B» fijo. Usan
    `ESTADOS_APROBADOS` y el período publicado más reciente.

### Hallazgos verificados y pendientes (no abordados en este bloque)

- El titular no puede retirar ni corregir una propuesta de cambio ya enviada;
  depende de que el laboratorio la rechace.
- Tras enviar la propuesta, el titular no ve qué propuso (`cambio.diferencias`
  llega al navegador pero no se pinta).
- Una propuesta con un insumo sin cantidad se acepta y falla al aprobar, con el
  error visible solo para el personal.

### Verificación

```text
Ruff:                        OK
Django system check:         OK (0 incidencias)
Pruebas nuevas:              test_coincidencia_superficies.py (8), admin (5),
                             guía (1), Mis reservas (1)
```

Nota: las dos auditorías paralelas de este bloque chocaron con el límite de
sesión de los subagentes; sus rastreadores terminaron pero la mayoría de los
verificadores no. Todo lo corregido arriba fue **verificado a mano leyendo el
código**, no tomado de esos reportes.

## 24. Lo que el titular puede hacer con su solicitud de cambio — 5 de septiembre de 2026

Cierra los tres huecos verificados en la sección 23.

### Retirar una solicitud de cambio

- Vista `retirar_solicitud_cambio_reserva` (`reservas/cambios/<id>/retirar/`),
  solo para quien la solicitó y solo mientras esté en `solicitada`,
  `autorizada` o `enviada`. La pasa a `cancelada`, deja auditoría y notifica al
  personal («Solicitud de cambio retirada»). Con `X-Requested-With` responde
  JSON; sin él, redirige a Mis reservas con el aviso visible.
- El JSON de la solicitud incluye `puede_retirar` y `retirar_url`. Mis reservas
  muestra «Retirar solicitud» junto a «Editar propuesta»; el editor de la
  propuesta lo ofrece al pie mientras la solicitud siga activa.
- Al retirarla, la reserva vuelve a admitir una solicitud nueva.

### Ver lo que se propuso

- `describir_diferencias()` en `cambios.py` traduce los identificadores de
  `diferencias_propuesta()` a nombres: equipos (`código · nombre`), software,
  espacios, servicios, participantes e insumos (`nombre: cantidad unidad
  (método)`), y la fecha a `dd/mm/aaaa`.
- `serializar_solicitud_cambio()` entrega esas diferencias legibles. Mis
  reservas pinta «Lo que propusiste» (antes → después) en la propuesta enviada
  y en el historial; el editor lo muestra bajo el aviso de «propuesta enviada».
  El cajón del panel recibe el mismo formato.

### Cantidades de insumos al enviar

- `_propuesta_desde_post` valida cada cantidad con
  `cantidad_insumo_normalizada` (alias público de `_decimal_solicitada`) en el
  momento del envío. Una cantidad vacía con método «indicada por el
  solicitante» o «calculada con software» devuelve el formulario con el error;
  con «revisión técnica» se admite dejarla abierta. Las cantidades válidas se
  normalizan (`12,5` → `12.5`).
- En el navegador, la cantidad pasa a obligatoria al marcar el insumo, salvo
  que se pida revisión.

### Mensajes de Django en todas las páginas

La sección 23 los había puesto en `portal/layouts/base.html`, pero la ficha
pública de la unidad, el panel, el editor de propuesta y las páginas de cuenta
extienden `base.html` directamente. El bloque vive ahora en `templates/base.html`
y sus estilos en `portal/css/core/foundation.css`, que carga toda página.

### Verificación

`webcitt/tests/test_cambios_titular.py`: retiro (propio, ajeno, resuelta, sin
AJAX con aviso visible), propuesta legible en JSON y en el editor, cantidad
vacía rechazada al enviar y cantidad válida normalizada y descrita.

## 25. Asistente de reserva: selección guiada, guía desde la reserva y capacidad visible — 5 de septiembre de 2026

Revisión del asistente de reserva (`reservation_wizard.js`, plantilla
`reserva_equipos.html`, `reservation_wizard.css`) a partir de las capturas del
usuario: el paso de recursos no se sentía activo, las opciones de guía
cambiaban al elegir el tipo de actividad y la unidad completa se ofrecía para
cualquier propósito.

### Paso de recursos en cascada

- Se retiran los "tipos de recurso" como pregunta previa. El paso guía en el
  orden natural y cada elección abre la siguiente:
  1. **Dónde** (obligatorio): áreas, estaciones o sala publicadas.
  2. **Equipos** del área elegida (`EspacioReservable.equipos_asociados`);
     un área técnica exige al menos un equipo; una sala general se reserva
     con su mobiliario.
  3. **Software** instalado en esos equipos (`SoftwareDisponible.equipos_instalados`)
     y un bloque plegable «¿Necesitas otro software?» para software adicional
     que la unidad deberá habilitar (`software_adicional`, texto libre
     `software_adicional_texto`); queda anotado en `requisitos_especiales`
     como «Software adicional por habilitar».
  4. **Insumos** compatibles con los equipos elegidos
     (`Consumible.equipos_compatibles`), con cantidad y costo referencial en
     el mismo bloque (`placeInventoryCatalog` traslada la sección al paso).
  5. **Fecha y horario**.
- Los tipos de recurso se deducen de la selección real (`syncCascadeState`);
  la mecánica previa (compatibilidad espacio–equipo, licencias, calendario)
  no cambia, solo la orquestación.
- Servidor (`crear_reserva`): espacio obligatorio en la ruta de recursos cuando
  la unidad publica áreas; software adicional exento de la validación
  «instalado en el equipo elegido».
- La orientación (plano, video, 360) queda en un `<details>` plegable.

### Unidad completa y capacidad compartida

- «Unidad completa» solo se ofrece (JS) y se acepta (servidor) para
  `docencia_practica`: bloquea todo el laboratorio y la ayuda de frecuencia
  sugiere repetir semanalmente o todo el período.
- Para el resto de propósitos se eligen áreas y el servidor comparte la
  capacidad (regla previa de `availability.evaluate_selection_conflicts`:
  docencia exclusiva; los demás suman `numero_participantes` hasta
  `capacidad`).
- Nuevo `availability.selection_occupancy` (mismo índice `_usage_by_slot` que
  la evaluación de conflictos) alimenta al endpoint del calendario con
  `capacidad_seleccion` y `dias[fecha].ocupacion[hora]`; cada bloque muestra
  «X de N puestos ocupados» con barra de llenado.

### Guía de práctica: nace de la reserva

- La pregunta «¿ya existe una guía aprobada?» aparece únicamente al elegir
  **práctica curricular**, siempre con las mismas dos opciones en el mismo
  orden: vincular una aprobada / crearla con esta reserva (solo «crear» si la
  unidad no tiene guías aprobadas para el propósito; el estudiante solo puede
  vincular).
- Docencia no curricular (simulación, demostración, etc.): sin pregunta al
  inicio; en el paso 4 aparece el interruptor **Generar guía (FT04)**,
  opcional (`guideIsOptionalHere`). Marca `vinculacion_actividad=manual` y
  el servidor crea la actividad y la guía borrador como antes.
- Otros propósitos: sin guía; los respalda el reporte de reserva.
- Al entrar al paso 4 con guía requerida y campos vacíos se ejecuta
  `applyGuideSuggestions()`: el contenido se propone con lo capturado
  (horario, espacio, equipos, software, insumos, participantes) y solo se
  revisa; nunca sobrescribe lo escrito a mano.

### Limpieza y pulido

- Retirada la selección de responsables del paso de recursos (tarjetas,
  `responsibleInputs`, validación y CSS): la plantilla solo mostraba un ítem
  estático. Queda una nota compacta de acompañamiento técnico.
- Rótulos «Paso 01…04» de la plantilla sustituidos por nombres de sección
  (el stepper del asistente numera los cinco pasos reales).
- Botones del recorrido con foco visible, estado pulsado y deshabilitado;
  responsivo hasta 480 px.
- Copia inalcanzable retirada (pregunta de guía para otros propósitos e
  ícono dependiente).

### Verificación

`test_cascada_recursos.py` (espacio obligatorio, área técnica con equipo,
sala sola, unidad completa por propósito, software adicional, publicación de
la cascada); `test_calendario_reservas.py` (ocupación y capacidad de la
selección; unidad completa sin cupo); contrato del asistente en
`test_reservas.py` derivando la versión del HTML.

## 26. Guía FT04 desde el asistente: revisión, asignatura, referencias IEEE, figuras y contenido listo — 5 de septiembre de 2026

Revisión del paso final del asistente a partir de las capturas del usuario:
«Continuar» no dejaba pasar, el botón de vista previa «no funcionaba», había
dos botones de vista previa, la asignatura se confundía con el nombre de la
práctica y el nombre estaba limitado a 30 caracteres.

### Vista previa y firma

- Causa del bloqueo: el diálogo de vista previa tenía `z-index: 20050` y el
  modal del asistente `100100 !important`; se abría detrás, pero la firma
  interna se registraba al abrir, así que la casilla de firma nunca se
  habilitaba. Ahora el diálogo va a `100700` y la firma
  (`guidePreviewSignature`) se registra solo al pulsar «Contenido revisado».
- Un solo botón «Visualizar guía completa en HTML», en la revisión final donde
  se firma. Se retiró el bloque «Revisión preliminar».

### Asignatura y nombre de la práctica

- La asignatura se pide en la identificación de la actividad («Asignatura o
  módulo formativo», `guia_asignatura`), nunca se copia del nombre de la
  práctica y el servidor la exige sin reutilizar `referencia_actividad`. La
  guía la muestra como dato automático y la planificación de prácticas la
  toma de la guía (`practicas_integracion.datos_planificacion_desde_reserva`).
- Nombre de la práctica hasta 120 caracteres (antes 30) con tres patrones a
  un clic: aplicado o por retos (`[Problema real]: [Técnica académica]`),
  técnico o metodológico (`[Técnica] aplicada a [Caso de estudio]`) y directo
  u objetivo (`[Proceso o fenómeno] de [Sustancia u objeto]`). El servidor
  rechaza corchetes sin completar. La sugerencia automática usa el enfoque
  técnico: «Uso de <equipo> con <software> aplicado a <asignatura>».

### Bibliografía BibTeX → IEEE y materiales complementarios

- `guia_referencias.py`: analiza BibTeX (artículo, libro, capítulo, congreso,
  tesis, informe, manual, en línea) y formatea en IEEE en español (iniciales,
  «y», «et al.» desde el séptimo autor, vol./n.º/pp., mes abreviado, doi,
  «[En línea]. Disponible en:»). Nombres corporativos entre dobles llaves.
- `contenido.bibliografia` guarda el resultado; `contenido.bibliografia_fuente`
  la fuente que se vuelve a editar. La numeración `[n]` la ponen la vista HTML
  (`<ol class="guide-references">`), el PDF y la vista previa.
- Endpoint `POST reservas/actividades/guias/bibliografia/` (sesión) para que la
  vista previa del asistente use el mismo formateador que el guardado.
- «Materiales complementarios» (`Título | https://enlace`) se guardan como
  `{titulo, url}` y se muestran como enlaces en HTML, PDF y vista previa.

### Tablas y figuras

- `guia_contenido.py`: mini-lenguaje compartido por vista previa, HTML
  (`guia_richtext`, `guia_procedimiento`) y PDF: `## Subtítulo`, listas,
  tablas (`|` por línea, primera fila cabecera) e imágenes
  `![Figura 1: título](figura:1)` o por URL. En el procedimiento, lo escrito
  debajo de un paso queda adjunto a ese paso.
- `ImagenGuiaActividad` (migración 0148): figuras citadas por posición.
  Se cargan desde el asistente (miniaturas, título, inserción a un clic) y
  desde el editor del panel (agregar/eliminar); inline de consulta en el
  admin. Validación real con Pillow, JPG/PNG/GIF/WebP, 5 MB, 12 por guía,
  antes de crear la reserva.
- PDF: tablas con cabecera y figuras escaladas con pie; las secciones con
  adjuntos fluyen sin caja para poder saltar de página.

### Orientación del laboratorio en pestañas

El bloque «Elige dónde trabajarás» muestra primero las áreas. El plano, el
recorrido en video y la vista 360° pasan de tres tarjetas grandes (antes en
un `<details>`) a una barra de pestañas compacta cerrada por defecto
(`data-space-orientation`); los iframes usan `data-src` y cargan solo al
abrir la pestaña. Se retiró el aviso amarillo de reglas (lo dice la cabecera
de la cascada) y el bloque de alcance se oculta cuando solo cabe «áreas».
Recordar reiniciar waitress (`scripts/iniciar_produccion.ps1`) tras cambiar
plantillas: el servidor las conserva en memoria.

### Contenido listo para incluir

Cada apartado académico ofrece opciones detalladas (resultado de aprendizaje
procedimental/analítico/actitudinal, objetivos general y específicos, marco
conceptual, principio de funcionamiento, tabla de variables, normativa,
seguridad por tipo de riesgo, pasos de preparación/calibración/registro/
cierre, tabla de registro de datos, resultados e informe, rúbrica base). Se
insertan al final del campo reemplazando `{practica}`, `{asignatura}` y
`{recursos}` con los datos de la solicitud; la persona decide cuáles usar.

### Correcciones tras la prueba en pantalla

- Insumos por equipo: `filterConsumablesByService` buscaba las tarjetas en el
  contenedor del paso 4, pero la cascada mueve el catálogo al paso 3; ahora
  consulta `inventoryCatalog` (raíz del catálogo, esté donde esté).
- Vista previa: abre desde el inicio (el foco al botón del pie la desplazaba
  al final), el motivo del botón deshabilitado va junto al botón y los campos
  obligatorios vacíos se marcan; si la revisión caduca, el mensaje dice qué
  cambió (`guideSignatureChanges`).
- Aviso visible `rw-stale-notice` cuando `data-reservation-build` de la
  plantilla no coincide con `EXPECTED_BUILD`. Caso real del 5 de septiembre:
  un `runserver --noreload` del día anterior seguía atendiendo el puerto
  8000 (los reinicios nuevos no podían tomarlo) y servía la plantilla v78 en
  caché con los estáticos v89 del disco. `iniciar_desarrollo.ps1` arranca
  ahora con recarga automática por defecto (`-SinRecarga` para un solo
  proceso) y aborta si el puerto ya está ocupado, indicando el proceso.

### Descarga y firma electrónica

- Tres niveles: (1) aceptación electrónica del autor al enviar y (2)
  aprobación del responsable, ambas internas con usuario, fecha y huella
  SHA-256 (`guia_firmas.py`), validan la guía dentro de la plataforma;
  (3) opcional, **firma electrónica certificada**: tras la aprobación, la
  persona autora descarga el PDF, lo firma con FirmaEC (o certificado
  acreditado) y lo carga en `subir_guia_firmada` (`guia_firma_certificada.py`).
  Se valida que sea un PDF con firma PAdES (`/ByteRange` + `/Type /Sig` o
  `/DocTimeStamp`), se guarda `archivo_firmado`, `firmado_por`, `firmado_en` y
  un resumen con la huella (migración 0149). La plataforma no custodia
  claves privadas; la validez del certificado la comprueba FirmaEC. Si se
  quisiera validar la cadena de certificación en el servidor haría falta una
  librería (pyHanko), decisión de dependencias aparte.
- Descarga: autor y personal de la unidad en cualquier estado; participantes
  solo con la guía aprobada y la descarga habilitada. Si existe versión
  firmada, `?download=1` la entrega; `?preview=pdf` sigue generando la del
  sistema. El comprobante enlaza «Descargar PDF» junto a «Ver guía».

### Verificación

`test_guia_asistente.py`, `test_guia_referencias.py`, `test_guia_contenido.py`,
`test_guia_firmada.py` y ajustes en `test_reservas.py` / `test_guias_practica.py`.

## 27. Paso de recursos: tarjetas de equipo con su software e insumos — 5 de septiembre de 2026

Revisión con datos reales del laboratorio de prueba: los filamentos PLA solo
son compatibles con la Impresora 3D FDM (única unidad dañada), la cinta y el
MDF son transversales (FDM+CNC, láser+CNC) y todo el software está en la
estación CAD. La tabla anterior mostraba «no compatible con los equipos
seleccionados» sin explicar por qué y listaba equipos en mantenimiento.

- **API** (`obtener_unidades_laboratorio`): `categoria` deducida del nombre
  (`categoria_publica_equipo`, palabras clave por inicio de palabra) y
  `video_url`.
- **Lista de equipos** (`modal_reserva_equipos.js`): una tarjeta por equipo del
  catálogo, agrupadas por categoría; sus unidades disponibles son chips con el
  `.unidad-checkbox` de siempre. Solo características resumidas; «Ver ficha»
  abre el diálogo. Equipos en mantenimiento, dañados o en uso van a un
  plegable aparte y no aparecen en la lista. El filtro pasa a ser por
  categoría; se retiran el filtro por estado y «seleccionar todo».
- **Integración** (`integrateResourcesIntoEquipment`): los nodos originales
  de software (`.reservation-software-item`) e insumos
  (`.reservation-consumable`) se mueven dentro de la tarjeta de su equipo y
  se devuelven a su sitio antes de cada redibujado
  (`reservationBeforeUnitsRender` / `reservationAfterUnitsRender`). Regla:
  insumo con un solo equipo compatible → en su tarjeta; con varios o ninguno →
  catálogo general (transversales y de uso general); software instalado en
  unidades visibles → en su tarjeta y habilitado solo al marcar ese equipo;
  sin equipo → uso general; con equipo no disponible → adicional.
- Marcar un insumo activa por sí solo «Solicitar insumos del laboratorio»;
  elegir otra opción limpia lo marcado. Los insumos incompatibles del catálogo
  general se ocultan en lugar de mostrar el aviso.
- **Fichas** (`reservation-sheet`): equipo (características, unidades y
  ubicación, software e insumos, archivos), software (acceso, licencias,
  dónde está instalado, descripción, cómo acceder) e insumo (variantes,
  existencia, compatibilidad, descripción, orientación, ficha técnica).
- Contrato del servidor intacto: mismos inputs (`unidades_seleccionadas`,
  `software_solicitado`, insumos y provisión).

## 28. Toda actividad docente exige guía; datos de prueba completos — 5 de septiembre de 2026

- **Subtipos**: docencia = práctica curricular, clase demostrativa o
  simulación, práctica evaluativa o examen práctico, proyecto integrador de
  asignatura y taller práctico de asignatura. «Investigación formativa o
  semillero» pasa a investigación e innovación y «Entrenamiento técnico» a
  capacitación (`SUBTIPOS_POR_PROPOSITO`, migración de choices y
  `subtypeOptions` del asistente, mismo mapa).
- **Guía**: cualquier subtipo docente exige guía (servidor: `es_docencia`;
  asistente: la pregunta «¿Ya existe una aprobada?» aparece al elegir el
  subtipo). Se retiró el interruptor de «guía opcional». La opción «Sí,
  vincular una guía aprobada» siempre es visible: si la unidad no tiene guías
  aprobadas para docencia queda deshabilitada y lo explica.
- **Espacio único**: una unidad sin áreas publicadas ya no bloquea la cascada;
  el espacio se incluye solo («Espacio único incluido») y se abren equipos.
- **Datos de prueba** (`cargar_pruebas_fablab`, idempotente): un equipo puede
  declarar varias unidades físicas (`unidades`), que comparten software y
  área; dos impresoras FDM, tres estaciones CAD, plotter de vinilo y estación
  de electrónica con su área; 15 insumos y materiales nuevos con existencias,
  precios y compatibilidad explícita (`COMPATIBILIDAD_EQUIPOS`: de un solo
  equipo, transversales y de uso general); PrusaSlicer, Chitubox, LightBurn
  e Inkscape (uso general por red); capacidad de la unidad. Ejecutar el
  comando también devuelve las unidades a «disponible».

## 29. Software propio del equipo, software adicional por equipo y casos de prueba — 6 de septiembre de 2026

- **`SoftwareDisponible.uso_en_equipo`** (migración 0151): `obligatorio` =
  programa propio del equipo (laminador de la impresora, controlador del
  CNC, licencia del escáner); `opcional` = programa disponible en un puesto
  que la persona marca solo si lo necesita. En el asistente el obligatorio se
  marca y bloquea al marcar su equipo (`is-required`, `data-rwRequired`,
  clic interceptado en captura) y el servidor lo incorpora aunque la
  solicitud llegue sin él (`_incluir_software_propio_de_equipos`), así la
  guía y la trazabilidad lo registran.
- **`EquiposServicios.admite_software_adicional`**: computadoras o
  estaciones donde se pueden instalar otros programas. La tarjeta del equipo
  pregunta «¿Necesitas instalar otro programa en este equipo?» y el texto
  viaja consolidado (`Equipo: programa; …`) en `software_adicional_texto`
  (hasta 300 caracteres); se retiró la pregunta general del paso de software.
  La API `obtener_unidades_laboratorio` publica el indicador.
- **Datos de prueba**: PrusaSlicer → FDM, Chitubox → SLA, LightBurn → láser,
  Candle → CNC, EXScan → escáner y Silhouette Studio → plotter, todos
  obligatorios; la estación CAD conserva Fusion, SOLIDWORKS, Blender, MeshLab
  y Cura como opcionales y admite instalar más. `RESERVAS_EJEMPLO`: nueve
  reservas en septiembre de 2026 que cubren programa propio, software de uso
  general, software adicional, insumos ligados y transversales, sala sola,
  docencia con guía, rechazada y cancelada.
- Diagnóstico del reporte «no aparecen espacios ni equipos, calendario
  vacío»: el servidor de desarrollo se había arrancado con el Python del
  sistema (Django 5.2, sin dependencias) y nunca escuchó; con el entorno
  virtual todo se publica. Arrancar siempre con `scripts/iniciar_desarrollo.ps1`.

## 30. Guía FT04 editada sobre su propio formato (editor visual controlado) — 6 de septiembre de 2026

- **Una sola plantilla** para la vista HTML, el editor y el asistente:
  `guias/includes/documento.html` (`modo` = lectura | edicion | asistente).
  Solo las zonas `[data-guia-campo]` se editan (resultado de aprendizaje,
  objetivos, fundamento, precauciones de la actividad, procedimiento,
  resultados esperados, criterios); encabezado, numeración, datos de la
  reserva, recursos, políticas de la unidad, residuos y firmas quedan fuera
  del editor. Bibliografía y materiales conservan BibTeX → IEEE y enlaces.
- **Formato de contenido** `contenido['formato_contenido'] = 'html'`: cada
  apartado es HTML acotado saneado por lista blanca en
  `guia_html.py` (analizador de la biblioteca estándar, nunca regex): p, h4
  (subtítulo), h5 (subapartado), strong, em, a (https/mailto), ul/ol/li,
  tablas como `<figure class="guide-table" data-titulo data-cabecera>` y
  figuras como `<figure class="guide-figure" data-figura=ID data-titulo
  data-fuente data-tamano>` sin `src` (la URL se resuelve al presentar).
  Políticas por apartado: texto / tablas / rico / pasos
  (`POLITICA_POR_CAMPO`). `DocumentoHtml` numera figuras y tablas por orden
  de aparición y produce el HTML de la vista y los bloques del PDF (mismos
  números). Las guías anteriores siguen leyéndose con el mini-lenguaje; al
  abrirlas en el editor se convierten (`html_desde_legado`) y el registro
  cambia solo al guardar.
- **Figuras**: `ImagenGuiaActividad.guia` admite nulo con `borrador_token`
  y `subido_por` (migración 0152). `subir_figura_guia` carga desde el editor
  (con guía o en borrador); se asocian al guardar la solicitud
  (`adjuntar_figuras_borrador`); `limpiar_figuras_guia_huerfanas` borra las
  abandonadas. Solo se citan figuras propias (`figuras_permitidas`).
- **Guardado**: `guardar_contenido_guia` (JSON, solo apartados autorizados,
  `version_base` → 409 en conflicto, invalida `firma_elaborador`); el
  formulario completo rechaza una `version_base` antigua. El editor muestra
  Cambios sin guardar / Guardando / Guardado hh:mm / Error y avisa al salir.
- **Asistente**: la tarjeta del paso 4 abre «Revisar y completar guía»
  (modos Editar contenido / Vista final) con el documento clonado de
  `<template id="guiaDocumentoPlantilla">`; los valores viajan en inputs
  ocultos `guia_<campo>` + `guia_formato_contenido=html` +
  `guia_imagenes_token`. Las sugerencias y el contenido listo para incluir
  rellenan solo zonas vacías. `guia_editor.js` (sin dependencias): barra
  reducida, tablas (filas, columnas, encabezado, título), imágenes (cargar,
  galería, tamaño, título, fuente), enlaces, pasos (nuevo, párrafo en el
  paso, subir, bajar, quitar), pegado desde Word/Google Docs normalizado
  (listas por `mso-list`, tablas, énfasis; imágenes no recuperables se
  avisan). El editor y `guia_html.py` aplican las mismas reglas.
- **PDF**: `construir_pdf_guia` usa los bloques de `DocumentoHtml` (listas
  anidadas, tablas con encabezado repetido y título, figuras por tamaño,
  pasos con adjuntos).
- **Navegador simulado**: `scratchpad/jsdom-harness` (jsdom sobre el
  servidor de desarrollo con la sesión real) reproduce el asistente y el
  editor; detectó el bucle del observador de equipos que congelaba la pestaña.

## 31. Insumos seleccionables y tarjeta de equipo en una fila — 7 de septiembre de 2026

- **Corrección**: las casillas, cantidades y métodos de los insumos se tomaban
  al iniciar desde la rejilla del paso 4, que en ese momento está vacía
  (la cascada mueve el catálogo al paso 3 y las filas a la tarjeta de su
  equipo), por lo que nunca se habilitaban. Ahora se consultan en todo el
  formulario. Reproducido y verificado con el navegador simulado.
- **Tarjeta en una fila**: columna 1 equipo (imagen, nombre, marca y modelo,
  descripción, ubicación, unidades como «Unidad 1», «Unidad 2» o «Seleccionar
  este equipo»; el código de inventario solo en la ficha); columna 2 software
  con su cantidad; columna 3 insumos y materiales con su cantidad. Ambas
  columnas se ven siempre y se habilitan al marcar el equipo (aviso «Marca el
  equipo…»). Los insumos integrados son filas compactas y la cantidad aparece
  al marcarlos.

## 32. Insumos y software con detalles desplegables, existencia controlada y cantidades en la cotización — 7 de septiembre de 2026

- **Catálogo de insumos** ya no es una tabla: cada insumo es una tarjeta
  (`reservation-consumable-list`) con foto, nombre, variante y existencia a
  la vista, y «Detalles» desplegables (descripción, presentación, lote,
  compatibilidad con equipos, código, orientación, ficha técnica). En cada
  lista solo hay un elemento abierto a la vez (`toggleItemDetails`); lo
  mismo para el software (`reservation-software-item__details`). Se
  retiraron las fichas modales de software e insumo; la ficha modal sigue
  solo para el equipo.
- **Existencia**: la cantidad no puede superar lo disponible
  (`checkConsumableStock`: aviso en la tarjeta y bloqueo de «Continuar»);
  el servidor ya lo rechazaba. El estado del bloque de insumos muestra
  cantidad seleccionada y valor (`n solicitados · $x`). El origen de la
  cantidad se explica: «La calculó el programa (laminador, CAM o
  simulación)», «Estimación propia», «Que la calcule el laboratorio».
- **Servicios**: la cotización lista los insumos con una cantidad editable
  (existencia visible, aviso si la supera) y se recalcula al cambiarla;
  `cotizar_servicios_reserva` acepta `cantidades` y la creación de la
  reserva `consumibles_servicio` (`normalizar_cantidades_servicio`,
  `validar_cantidades_servicio`, `calcular_cotizacion(..., cantidades)`,
  `consumibles_sugeridos_servicios(..., cantidades)`).
- **Unidades idénticas** se identifican como «Unidad 1 · FAB-UNIT-FDM-01 ·
  zona». Datos de prueba: tres impresoras FDM y «Computadora especializada
  para diseño» con procesador, RAM, tarjeta gráfica, disco y periféricos.
- Etiquetas QR y Code 128 de lotes (gestión → inventario) siguen intactas:
  `gestion_lote_identificador` y `gestion_etiquetas_inventario_pdf`.

## 33. Software en filas con casilla, sin sección general; insumos con ficha completa — 7 de septiembre de 2026

- **Software**: fila compacta (casilla solo para el opcional, icono, nombre y
  versión, «Detalles» al lado). Los detalles traen versión instalada, para
  qué se utiliza, en qué equipos, tipo y acceso con licencias, condiciones y
  si es propio u opcional. El propio del equipo no muestra casilla: queda
  «Incluido con el equipo».
- **Sin software de uso general**: todo programa va ligado a un equipo y se
  elige en su tarjeta; el catálogo general del paso 3 solo sirve al servicio
  con diseño asistido. Se retiró «software adicional» por identificadores
  (el servidor sigue aceptándolo); la instalación de otros programas se pide
  en la tarjeta del equipo que lo admite. Inkscape pasa a las computadoras
  de diseño.
- **Insumos**: sin la opción «No estoy seguro; necesito orientación» (queda
  «No necesito», «Solicitar del laboratorio», «Materiales propios»);
  cabeceras de tipo más ligeras; detalles con marca, presentación y cantidad
  por presentación, características técnicas, existencia, lote en uso,
  vencimiento, compatibilidad, código y ficha técnica. Proveedor, ubicación
  en estantería, lotes, costos y umbrales de reposición se ven solo en
  Gestionar laboratorio (inventario, etiquetas QR/Code 128). Datos de prueba
  con `FICHA_INSUMOS` (marca, especificación, proveedor) para los 24 insumos.

## 34. Insumos compartidos en la tarjeta del equipo y software sin distintivos — 7 de septiembre de 2026

- Cada insumo vive en la tarjeta de un equipo compatible: si es compatible
  con varios, en el que esté marcado (o en el primero) y se reubica al
  cambiar la selección. El bloque «Insumos y materiales» del paso 3 solo
  conserva lo que la unidad no ligó a ningún equipo. En los datos de prueba
  cinta, lija, cianoacrilato y guantes quedan ligados a las estaciones donde
  se usan (`COMPATIBILIDAD_EQUIPOS`).
- Software: el opcional ya no lleva distintivo (la casilla lo dice); solo el
  propio del equipo muestra «Incluido con el equipo». Detalles en viñetas
  con título y contenido (versión, para qué se utiliza, instalado en, tipo y
  acceso, condiciones, uso).
- Dentro de las tarjetas no se rotula «no compatible»; el aviso «Marca el
  equipo…» basta. Verificado con captura real en Chrome sin interfaz sobre
  una instantánea del DOM del asistente (`jsdom-harness/recorte_equipos.html`).

## 35. Software en una fila, insumos espejados y rediseño del flujo de servicios — 8 de septiembre de 2026

- Software: la etiqueta es una rejilla plana (casilla | icono | nombre y
  distintivo | Detalles); se retiraron las reglas heredadas sobre
  `.reservation-software-item > span` que apilaban el icono. Insumos
  compatibles con varios equipos: la tarjeta original en el primero y un
  espejo sincronizado (`syncConsumableMirrors`, `relayMirrorEvent`) en cada
  uno de los demás; el servidor solo lee los controles del original.
- Política de cobro de servicios (`ConfiguracionOperativaUnidad`):
  `cobrar_tarifa_base`, `cobrar_uso_equipo`, `cobrar_mano_obra` (falso) y
  `cobrar_diseno` (verdadero). Los materiales se cobran siempre según
  consumo. `calcular_cotizacion` descompone cada servicio en `componentes`
  con `cobrado`; lo no cobrable es aporte institucional y el descuento del
  segmento solo aplica sobre lo cobrable. Las horas y cantidades sugeridas
  del catálogo son por pieza (`piezas`); `seleccion` limita los materiales a
  los elegidos más los obligatorios. La liquidación real usa la misma
  política. Migración 0153.
- Trabajo del servicio en `Reserva`: `urgencia_servicio`, `cantidad_piezas`,
  `detalle_trabajo`, `fecha_entrega_prevista`; en el desglose queda
  `trabajo` (incluido el equipo elegido). `SolicitudFabricacion` recibe
  prioridad, fechas programadas, horas estimadas de la cotización, materiales
  principales y `maquinas_requeridas`.
- Propuesta de entrega (`proponer_entrega_servicio`): horas de máquina ×
  piezas; urgente entra al día hábil siguiente, normal tras 2 días más la
  cola pendiente (8 h referenciales por día); usa `_jornadas_habilitadas`
  (compartida con la validación) y las horas ocupadas por servicios de la
  unidad; reparte el trabajo en varios días cuando excede la jornada. Quien
  registró reservas no utilizadas en 6 meses pierde la atención urgente.
- Asistente: paso 3 con «Detalles del trabajo» (piezas, precisiones, equipo
  de fabricación derivado de los materiales exclusivos, materiales con
  casilla y cantidad total controlada por existencia), programación con
  urgencia y propuesta aplicable al calendario heredado (`calendarState`,
  `updateFormFields`); el calendario solo se despliega para elegir otra
  fecha. Paso 4: simulaciones comparables (hasta 5) con «Usar esta», que
  reaplica piezas, urgencia, equipo y materiales. Envío: `cantidad_piezas`,
  `urgencia_servicio`, `detalle_trabajo`, `materiales_seleccionados`,
  `consumibles_servicio`, `equipo_servicio`, `fecha_entrega_prevista`.
- Recursos: nota de compromiso de uso en la confirmación y en la estimación
  (los insumos se cobran según consumo; no usar la reserva resta prioridad).
- Comprobante (HTML y PDF): fila «Trabajo solicitado» y tabla «Detalle
  económico estimado» con condición por fila; gestión muestra y edita
  urgencia y entrega prevista; Mis reservas muestra trabajo y entrega.
- Pruebas: `test_servicios_trabajo.py` (política, selección, piezas,
  propuesta urgente/normal/incumplimiento, creación, comprobante) y
  contratos en `test_cascada_recursos.py`. Verificado con el navegador
  simulado (escenario `servicio`) y captura en Chrome sin interfaz.

## 36. Estimaciones claras: columnas, cantidad sin método y valor del servicio en el paso 3 — 8 de septiembre de 2026

- Estimación de recursos: columnas «Concepto · Cantidad · Precio unitario ·
  Subtotal · Lo asume la UPEC · A tu cargo»; bajo el nombre del insumo va su
  detalle (`data-detalle`: variante, color, presentación, especificación
  técnica); el aporte nunca se muestra como «−$0.00».
- Insumos de una reserva: solo se pide la cantidad (vacía = la calcula el
  laboratorio en la revisión, `metodo_estimacion` «revision»); desapareció
  el selector «¿Cómo calculaste la cantidad?» y sus referencias en el
  asistente y en los espejos.
- Servicios: el valor estimado se calcula solo (`scheduleServiceQuote`, con
  retardo de 350 ms) cada vez que cambian servicio, modalidad, piezas,
  urgencia, equipo o materiales, y se muestra en el paso 3 antes del
  acompañamiento técnico; ya no hay botón «Simular valor». El paso 4
  (`pagoServicioSeccion`) repite el total en un resumen y pide método de
  pago y aceptación, dejando claro que el valor final se determina con el
  peso real de los materiales. Versión del asistente `20260908-valores-v101`.

## 37. IVA configurable, tabla unificada de valores e insumos bloqueados hasta marcar el equipo — 9 de septiembre de 2026

- `ConfiguracionOperativaUnidad.aplicar_iva` (falso) y `porcentaje_iva`
  (15): `calcular_iva` agrega el impuesto sobre lo que paga la persona en
  la cotización de servicios, la estimación de recursos y la liquidación
  real (`subtotal_usuario`, `iva`, `valor_estimado_usuario`). Migración
  0154; fieldset «Impuestos» en el administrador.
- Cada componente del servicio lleva `cantidad`, `precio_unitario`,
  `valor`, `descuento`, `aporte_institucional` (todo el valor si es
  referencial; solo el descuento si se cobra) y `valor_usuario`.
- Asistente: la misma tabla de seis columnas (Concepto · Cantidad · Precio
  unitario · Subtotal · Lo asume la UPEC · A tu cargo) en recursos y en
  servicios (`quoteTable`), con lo asumido en negativo, fila de IVA cuando
  aplica y fila Total; en servicios se muestra en el paso 3 y otra vez en el
  paso 4 junto al pago y a las simulaciones. Sin horario elegido, los apoyos
  de una reserva se muestran por hora («7 × cada hora · $56.00/h · −$56.00/h»).
- Insumos de una reserva: bloqueados hasta marcar el equipo de su tarjeta
  (`rwBaseEnabled` + `is-selected` del grupo, también en los espejos); los
  de uso general esperan a un equipo o a una reserva solo de espacio.
- Un solo servicio por solicitud: marcar uno desmarca los demás.
- Comprobante: bloque destacado «Valor estimado a tu cargo», tabla con
  cantidad, subtotal, lo que asume la UPEC (negativo) y a cargo del usuario,
  fila de IVA y total. Versión del asistente `20260909-iva-tablas-v102`.

## 38. Programaciones semanales valoradas completas y recálculo tras cambios — 9 de septiembre de 2026

- `calcular_costo_referencial_recursos(..., sesiones, alcance_cantidades)`:
  los apoyos por hora se multiplican por las sesiones y las cantidades de
  insumos, si son «por sesión», también; si son «el total del programa» se
  reparten (cada sesión registra su parte en `ReservaConsumible`). El
  desglose lleva `programa` (sesiones, alcance, horas por sesión y totales,
  valor por sesión) y cada concepto su `cantidad_por_sesion`.
- Asistente: cuando la reserva se repite cada semana, el paso 4 pregunta si
  las cantidades son por sesión o totales (`alcance_cantidades`), estima el
  número de sesiones con el calendario académico (`estimatedSessions`) y
  muestra el costo de todo el programa y por sesión.
- Cambios: al aprobar una solicitud de cambio del titular,
  `recalcular_estimacion_reserva` vuelve a valorar esa sesión (marcada
  `sesion_modificada`) para que el comprobante refleje las cantidades
  aprobadas. El comprobante muestra la línea «Trazabilidad» (revisión,
  cambios aprobados y fecha del último) y el resumen del programa.
  Versión del asistente `20260909-sesiones-v103`.

## 39. Paso 2 directo para servicios — 9 de septiembre de 2026

- Un servicio es un encargo concreto: el paso 2 («Finalidad del servicio»)
  solo ofrece un campo opcional `finalidad_servicio` (para qué se necesita)
  y aclara que el solicitante es la persona responsable. Se ocultan la
  clasificación de propósito, el contexto de actividad y los participantes;
  el propósito institucional queda fijado en «Servicio científico-
  tecnológico» para los indicadores y la validación del paso no exige nada
  más. La finalidad se añade a la descripción trazable («Finalidad: …»).
  Versión del asistente `20260909-finalidad-v104`.

## 40. Diálogo de la guía dentro del modal y bibliografía por pegado — 10 de septiembre de 2026

- El diálogo «Revisar y completar guía» se añadía al `body`, fuera del modal
  del asistente; Bootstrap 4 (`_enforceFocus`) devolvía el foco al modal en
  cuanto se intentaba escribir en una zona editable, por lo que la guía
  parecía bloqueada y no admitía pegado. Ahora se añade al propio modal
  (`modal.appendChild(guidePreview)`) y la edición funciona.
- Bibliografía: se retiraron las plantillas de código BibTeX; la persona
  pega las entradas ya listas exportadas desde su gestor y el sistema las
  convierte a IEEE.
- Cabecera del diálogo en dos filas (título y cierre; modos «Editar
  contenido» / «Vista final» debajo), texto del documento con
  `overflow-wrap: anywhere` y tablas desplazables, y botón «Contenido
  revisado» en amarillo UPEC (legible también deshabilitado). Versión del
  asistente `20260910-guia-dialogo-v105`.

## 41. Tarjetas de ruta con la ayuda integrada y botón de cerrar fijo — 10 de septiembre de 2026

- Paso 1: cada tarjeta reúne la descripción, los beneficios, el botón
  «Elegir esta ruta», el bloque «Prepárate con» y el videotutorial
  (`rw-type__prepare`, `rw-type__tutorial`); desaparecen la franja
  desplazable de pasos (`rw-route`) y el bloque plegable «Orientación para
  usuarios nuevos» (`rw-onboarding`, `rw-guide-card`,
  `rw-tutorial-trigger`), que repetían la misma información. Debajo queda
  una sola nota: nada se registra hasta la confirmación final.
- El botón de cerrar del modal ya no usa `top: 50%` con `translateY` ni
  escala al pasar el cursor: posición fija y sin transición de transform,
  por lo que no se mueve al pulsarlo.
- Versión del asistente `20260910-rutas-v106`.

## 42. Guía FT04: apartados 10 y 11 en el documento, paso 4 sin redundancia y PDF continuo — 10 de septiembre de 2026

- `documento.html`: el comentario de plantilla pasa a `{% comment %}` (el
  `{# #}` multilínea se imprimía en el diálogo). Materiales complementarios
  (10) y bibliografía (11) son apartados propios con cajetín; su fuente se
  edita en `[data-guide-source]` dentro del documento (el asistente y el
  editor trasladan allí sus campos) y debajo se ve el resultado formateado.
- Asistente: el diálogo de la guía vive dentro del formulario
  (`form.appendChild(guidePreview)`), el paso 4 deja de repetir datos
  generales, políticas y un segundo botón: la revisión final solo firma.
  Botón «Ver PDF» que envía los campos y los datos automáticos a
  `vista_previa_pdf_guia` y abre el mismo PDF que generará la guía. Cabecera
  del diálogo sin superposición (la regla de 36 px solo aplica al cierre) y
  ancho de 1400 px.
- PDF (`construir_pdf_guia`): sin `PageBreak` ni `KeepTogether` de bloques
  completos; los títulos llevan `keepWithNext` para no quedar solos al pie y
  el contenido fluye sin hojas en blanco. Apartados 10 (materiales) y 11
  (bibliografía) separados. `_contenido_para_vista(guia, figuras)` acepta
  figuras de borrador para la vista previa transitoria.
- Versión del asistente `20260910-guia-apartados-v107`.

## 43. Firmas de la guía editables y PDF firmado antes de la aprobación — 10 de septiembre de 2026

- `contenido['firmas']` = `{elaborado|revisado|aprobado: {activo, nombre,
  cargo, fecha}}` (`guia_firmas.py`: `normalizar_firmas`, `firmas_desde_post`,
  `firmas_faltantes`, `ROLES_FIRMA`). Quien elabora firma siempre (nombre
  propuesto desde la sesión, editable); revisión y aprobación se incluyen
  solo si el autor las marca y entonces exigen nombre y cargo
  (`secciones_faltantes` los añade como «Firma Revisado por: nombre»).
  Guías anteriores sin configuración conservan las tres columnas.
- Documento FT04: bloque `[data-guide-signatures]` con inputs por rol en
  edición (asistente y editor) y solo los roles activos en vista final,
  lectura y PDF (columnas según roles activos). Etiqueta de plantilla
  `firmas_documento`; el asistente envía `guia_firmas` (JSON) y el editor
  clásico `firma_<rol>_*` o `firmas` en el guardado por apartado.
- Versión firmada (FirmaEC): se carga ya durante la revisión (además de
  tras la aprobación); la vista explica el circuito descargar → firmar →
  cargar → el laboratorio aprueba, y la aprobación conserva el archivo.
- Versión del asistente `20260910-guia-firmas-v108`.

## 44. Descripción obligatoria de la solicitud, catálogo por familias y colores UPEC — 11 de septiembre de 2026

- `Reserva.intencion_solicitud`: lo que la persona pretende realizar (50 a
  200 palabras, `validar_intencion_solicitud` cuando el formulario la envía).
  El asistente la pide en ambas rutas con un solo componente
  (`reservation-intent`): en servicios sustituye a la finalidad breve; en
  reservas aparece tras propósito y tipo de actividad. Trae contador de
  palabras, lista de qué incluir y un ejemplo redactado que se inserta con un
  botón. Se añade a la descripción trazable («Finalidad:» / «Intención:») y
  alimenta las sugerencias de la guía (`intentSummary`, marcador
  `{intencion}` en los fragmentos) sin publicarse en ella.
- `FablabService.familia` (migración 0155): el catálogo de servicios se
  agrupa por familia (`servicios_por_familia`; Impresión 3D, Corte y
  mecanizado, Digitalización 3D en los datos de prueba) para elegir la opción
  que mejor se ajusta; vacío usa el tipo de servicio.
- Tarjeta de servicio en amarillo UPEC `#ebc55a` combinado con el verde
  (borde, etiquetas, barra del videotutorial). Versión del asistente
  `20260911-intencion-v109`.

## 45. Flujo directo del asistente y hora de almuerzo — 12 de septiembre de 2026

- Paso 3 sin cabeceras numeradas de la cascada (`cascadeHeading` y
  `setCascadeStatus` desaparecen): cada catálogo conserva su cabecera. Sin
  filtro de categoría (`filtroEquipo`): las áreas marcadas ya filtran.
- Insumos sin opciones de provisión: `provision_consumibles` viaja en un campo
  oculto que `syncProvision()` deduce de los insumos marcados (`unidad` si hay
  alguno, `ninguno` si no). El servidor solo admite esos dos valores; la
  declaración de material propio y `_normalizar_material_propio` se retiran
  (los valores históricos siguen en el modelo).
- «Apoyos y condiciones adicionales» se reemplaza por la nota fija
  `#apoyoLaboratorioNota` en ambas rutas: el apoyo forma parte de la
  prestación del servicio de la unidad. El campo oculto `requisitos_especiales`
  sigue recibiendo solo la nota de software por habilitar.
- Descripción obligatoria en dos columnas (`.reservation-intent__grid`):
  redacción a la izquierda; qué incluir y ejemplo siempre visibles a la
  derecha. La descripción opcional de la actividad desaparece: la intención
  alimenta `descripcion` de la actividad y de la guía.
- Sin simulaciones comparables del servicio (`registerSimulation`,
  `renderSimulations`, `[data-quote-simulations]`).
- Hora de almuerzo (`HORA_ALMUERZO = 13` en `models/operaciones.py`, espejo en
  `modal_reserva_equipos.js`): `_validar_horario_operativo` rechaza el bloque
  13:00–14:00 en reservas de recursos salvo administración; los servicios se
  planifican por la cola. El calendario semanal y la lista del día muestran el
  bloque «Almuerzo · no se reserva» (`is-lunch`).
- Presentación del procedimiento dentro del editor: selector
  `.guide-toolbar-inline__format` en la barra del apartado (evento `formato`
  de `GuiaEditor`); el asistente y `editor.html` conservan el campo oculto
  `guia_formato_procedimiento` / `formato_procedimiento`.
- Guía firmada: el botón «Cargar versión firmada» aparece en la vista de la
  guía desde que se envía a revisión (antes de que el laboratorio valide) y
  sigue disponible tras la aprobación para reemplazarla; el comprobante lo
  indica en «Guía en revisión». Versión del asistente
  `20260912-flujo-directo-v110`.
- Ajuste posterior: la descripción obligatoria cambia con el propósito. Solo
  docencia (`docencia_practica`) conserva 50–200 palabras y alimenta la guía;
  en los demás propósitos el bloque pide 30–150 palabras (`briefIntent`,
  `validar_intencion_solicitud(..., breve=True)`) con título, lista y ejemplo
  propios, y el comprobante la muestra en la fila «Lo que se solicita
  realizar» (HTML, correo y PDF) sin repetirla en la descripción trazable.
  El bloque de almuerzo se bloquea también para cuentas administradoras en el
  asistente; solo el panel de gestión y la aprobación de cambios lo registran
  (`permitir_almuerzo=True`). Versión `20260912-intencion-proposito-v111`.
- Filtro de áreas estricto: un equipo sin área asignada ya no aparece salvo con
  la unidad completa (o si la unidad no define áreas), y la lista «no
  disponibles» (`#equiposNoDisponibles`, `li[data-unit-id]`) sigue el mismo
  filtro con su contador. Versión `20260913-filtro-areas-v112`.

## 46. Bloqueo desde el calendario del panel y cancelación trazable — 13 de septiembre de 2026

- Agenda semanal del panel: las horas libres son seleccionables
  (`[data-block-slot]`, `is-block-selected`); una barra fija
  (`[data-block-selection-bar]`) resume los tramos y abre el cajón «Bloqueo de
  agenda» en modo compacto: solo tipo y «¿Para qué se bloquea?»; título,
  fechas, horas, alcance por áreas o equipos y las casillas quedan en «Más
  opciones» (`[data-block-advanced]`), abiertas solo al editar o al bloquear
  sin selección. `agendaOperationPayloads` envía un bloqueo por cada tramo
  continuo de un día; el servidor genera el título («Tipo · fecha») si viene
  vacío.
- Cancelar nunca elimina: `Reserva.registrar_cancelacion(actor, origen,
  motivo)` guarda `cancelada_en`, `cancelada_por`, `origen_cancelacion`
  (solicitante/laboratorio) y `motivo_cancelacion` (migración 0156) y anota
  la observación. El solicitante indica el motivo al cancelar (Mis reservas);
  el laboratorio ya lo exigía. `texto_cancelacion` aparece en el comprobante
  (HTML, correo, PDF), en el listado de Mis reservas y en la respuesta de
  cancelar. La reserva cancelada sale de la agenda (`ESTADOS_OCUPAN_AGENDA`)
  y sigue en historial, reportes y auditoría.
- Tarjetas de la agenda del panel: nombre corto (`Reserva.resumen_solicitud`,
  recorta el prefijo generado, la modalidad y el propósito y deja dos recursos
  con «+N»), quién reserva con su tipo (`tipo_usuario_solicitante_corto`),
  categoría de uso (`proposito_corto`) y el estado como distintivo de color
  (`.unit-console__calendar-event-who` / `-meta`).

## 47. Expediente de la reserva en las dos pantallas — 13 de septiembre de 2026

- `domains/unidades/reservas/seguimiento.py` (`linea_tiempo_reserva`) es la
  fuente única del recorrido: cinco etapas (solicitud, revisión, confirmada,
  ejecución, cierre) con su situación (`hecho`, `actual`, `pendiente`,
  `detenido`, `descartado`), fecha y nota. Un desenlace distinto de
  «completada» corta la línea en la etapa donde ocurrió y el resto queda
  descartado. Lo consumen el payload del solicitante y el del laboratorio.
- «Mis reservas»: el detalle bajo el calendario queda como resumen con el
  avance; todo lo demás vive en `#misReservasExpediente`, una ventana con
  pestañas (Seguimiento, Detalle, Documentos, Cambios y mensajes) que se abre
  al pulsar una tarjeta de la agenda. Documentos embebe el comprobante
  (`comprobante_reserva?fragmento=1`) y abre el PDF del comprobante
  (`?inline=1`) y de la guía (`?preview=pdf`) en un lector propio, sin salir
  del panel. Cancelar y solicitar cambio viven en la pestaña de cambios.
- Panel del laboratorio: el cajón de la reserva suma «Recorrido de la
  solicitud» (`#managementTimeline`) y «Documentos» con el mismo lector
  (`#managementDocumentViewer`); el payload trae `linea_tiempo` y
  `documentos`.
- `comprobante_reserva_pdf` respeta `inline=1` (lector) o descarga; el
  fragmento reutiliza `_comprobante_contenido.html`. Las páginas que lo
  embeben cargan `comprobante_reserva.css`. Versiones
  `reservas.css/modal_mis_reservas.js` `20260913-expediente-v92/v18` y
  `panel_gestion.*` `20260913-expediente-v31`.
- Agenda semanal por franjas continuas en los tres calendarios. Cada reserva
  es un solo bloque de su hora inicial a la final (ya no se repite la tarjeta
  hora por hora) y las simultáneas se reparten en carriles del mismo día.
  Panel: `_agenda_grid` sustituye a `_agenda_horaria` y entrega `horas` y, por
  día, `celdas` (rail de horas para bloquear), `eventos` (con `inicio`,
  `filas`, `carril`, `carriles`) y `bandas` de bloqueos; la tarjeta se
  simplifica con `is-narrow` / `is-tight` cuando comparte el día. Asistente:
  `franjasAgendaDia` + `repartirCarrilesAgenda` en el calendario semanal, con
  un carril izquierdo que conserva la selección hora por hora y un chip
  «+N más» cuando hay más de dos franjas simultáneas. «Mis reservas» ya
  dibujaba franjas y solo cambia al nombre corto. La agenda pública
  (`api.py`) también usa `resumen_solicitud`.
- El expediente se abre como ventana sobre la agenda, no embebido: al pulsar
  la solicitud en el calendario, `#misReservasExpediente` cubre todo el
  historial (`.my-reservations-record__scrim` + `__dialog`, `aria-modal`), el
  fondo queda atenuado (`.has-open-record`) y cierra con el botón, el fondo o
  Escape. Vive dentro de `#misReservasModal` para no perder el foco del modal
  de Bootstrap. Versiones `reservas.css/modal_mis_reservas.js`
  `20260913-ventana-v93/v19`.
- La guía se lee dentro del expediente y ya no manda a otra pantalla: pestaña
  propia «Guía de práctica» (separada de «Comprobante»), con el documento
  institucional embebido (`ver_guia_actividad?fragmento=1` →
  `guias/fragmento.html`), «Leer el PDF» en el lector incrustado y
  «Descargar»; solo se sale para corregir una guía en borrador o rechazada.
  Los PDF se pueden incrustar porque `ver_guia_actividad` y
  `comprobante_reserva_pdf` llevan `@xframe_options_sameorigin` (antes
  `X-Frame-Options: DENY` dejaba el lector en blanco). Cada lector recuerda su
  propia petición (`data-viewer-request`) para que guía y comprobante se
  carguen a la vez. El panel del laboratorio suma el mismo botón «Guía».
- La guía se firma desde el expediente: la pestaña «Guía de práctica» incluye
  el bloque FirmaEC (`[data-subir-firmada]`) que sube el PDF firmado por
  `subir_guia_firmada`, ahora con respuesta JSON cuando llega con
  `X-Requested-With: XMLHttpRequest`. El payload trae `puede_firmar`,
  `subir_firmada_url` y `firmada`; la página de la guía conserva el mismo
  formulario para quien entre por ahí.
- Cajetín de firmas idéntico en HTML y PDF: un recuadro por firma con el
  espacio reservado para la firma electrónica en QR
  (`.guide-signature__space` / fila de 24 mm en el PDF) y el conjunto
  centrado en la hoja sea una o tres firmas
  (`.guide-signatures--final` con ancho ajustado; `hAlign='CENTER'` en el
  PDF). Versiones `reservas.css/modal_mis_reservas.js`
  `20260913-firma-v95/v21` y `guias_practica.css` `20260913-firma-v89`.
- El panel lateral de «Mis reservas» deja de ser la ficha de la reserva
  seleccionada y pasa a ser el listado de solicitudes (`#misReservasListado`,
  `[data-ir-a-reserva]`): código, nombre corto, fecha y horario y el estado.
  Al pulsar una, `irAReservaEnAgenda` mueve la agenda a su semana, desplaza la
  vista hasta su hora y resalta la tarjeta para abrir el expediente desde
  allí. Se retiran la ficha y su resumen de avance
  (`resumenSeguimientoReserva`, `.my-reservations-detail__header/__selector/
  __footer/__actions/__progress`). Versiones `20260913-listado-v96/v22`.
  Cada fila del listado ocupa una sola tarjeta compacta: código, nombre y
  fecha a la izquierda (`.my-reservations-list__main`) y el estado como
  distintivo a la derecha, en la misma fila, para que quepan muchas
  solicitudes sin crecer en alto. Versiones `20260913-listado-v97/v23`.
- Los cajones del panel («Gestionar solicitud» y las operaciones de agenda)
  dejan de estar pegados al borde derecho: son ventanas centradas de hasta
  1180 px con más aire (cabecera, pestañas y cuerpo) y, en pantallas anchas,
  las tarjetas de «Resumen» y «Recursos» se reparten en dos columnas con el
  bloque de decisión a fila completa. Versión `panel_gestion.*`
  `20260913-centrado-v34`.
  La ventana del expediente ocupa casi todo el historial (hasta 1720 px) con
  más margen interno; el seguimiento se reparte en dos columnas solo cuando
  hay avisos (`is-two-columns`, que el render aplica tras pintar los paneles)
  y el detalle usa tres columnas en pantallas anchas. Versiones
  `20260913-ancha-v98/v24`.
  Ajuste posterior: el cajón toma el mismo tamaño que la ventana del
  expediente (hasta 1720 px y toda la altura disponible) y sus seis pestañas
  caben en una fila (`repeat(auto-fit, minmax(140px, 1fr))`). Versión
  `panel_gestion.*` `20260914-ancho-v35`.
  La ventana del expediente y el cajón del panel comparten el mismo encuadre:
  `position: fixed; inset: 0; padding: 14px` con un panel de
  `min(1720px, 100%)` y toda la altura. Antes el expediente se limitaba al
  recuadro del historial y se veía más pequeño. Versión `reservas.css`
  `20260914-igualada-v99`.

## 48. Las tres vistas de guías dejan de solaparse — 14 de septiembre de 2026

- Cada superficie responde a una pregunta distinta y se nombra en consecuencia:
  «Guías publicadas» en Recursos y prácticas (catálogo público, solo aprobadas
  y publicadas), «Mis guías de práctica» en Gestión y reserva (autoría:
  crear, corregir, historial de versiones y las guías sin reserva) y la
  pestaña «Guía de práctica» del expediente (leer, firmar y corregir la de esa
  reserva).
- La lista de autoría entrega `fichas` (`{guia, reserva, reserva_url}`) en vez
  de `guias`: cada tarjeta muestra de qué solicitud viene («Solicitud
  RL011-000081 · 11/09/2026» o «Sin solicitud asociada») y su acción principal
  es «Abrir en la reserva», que lleva al expediente; «Corregir» y «Ver
  documento» quedan como secundarias. Antes repetía «Ver HTML» y «PDF», que ya
  hace el expediente.
- Entrar por `?reserva=<id>#mis-reservas` (avisos, comprobante o la lista de
  guías) abre el expediente de esa solicitud, no solo su semana. Versiones
  `reservas.css/modal_mis_reservas.js` `20260914-guias-v100/v25` y
  `guias_practica.css` `20260914-guias-v90`.
- La carga del PDF firmado deja de pedirse dos veces: quien es titular de la
  reserva la sube desde la pestaña «Guía de práctica» de su expediente y la
  página de la guía solo se lo indica (`reserva_para_firmar`,
  `.guide-certified__redirect`); el personal de la unidad y las guías sin
  reserva conservan el formulario ahí. Con una versión firmada cargada, el
  lector en línea (`?preview=pdf`) entrega ese archivo, no el regenerado.
  Versión `guias_practica.css` `20260914-firma-unica-v91`.

## 49. La guía se corrige hasta que se valida y la lista lleva a su sitio — 7 de septiembre de 2026

- `GuiaActividadReserva.es_editable` incluye `revision`: enviada no es
  definitiva, así que quien la escribió y el personal de la unidad la corrigen
  con el mismo editor hasta que el laboratorio la apruebe. La versión firmada
  con certificado cierra la edición (`archivo_firmado`), porque el PDF firmado
  dejaría de corresponder con el contenido.
- Guardar una guía que ya está en revisión rehace la huella de elaboración
  (`firmar_contenido_guia`): el revisor lee el documento vigente y
  `verificar_firma_elaborador` sigue dando válido. El estado no cambia; solo
  «Enviar a revisión» lo mueve.
- El expediente del solicitante ofrece «Corregir la guía enviada»
  (`_documentacion_solicitante` usa `_puede_editar_guia`) y el cajón del
  laboratorio «Abrir y corregir guía» mientras la guía sea editable; una vez
  aprobada, ambos vuelven a «Revisar guía».
- La lista de autoría deja de repetir el visor: cada ficha trae un `destino`
  contextual. Publicada abre el módulo público de la unidad
  (`?guia=<pk>#recursos-practicas`), pendiente propia lleva a «Mis reservas»
  para terminar de editar o firmar (`?reserva=<id>#mis-reservas`) y el resto
  abre el documento. `pestanas_modulos.js` aprende a leer el enlace: activa la
  pestaña del módulo por `#clave` y abre la guía pedida por `?guia=`
  (versión `20260914-enlace-modulo-v3`).

## 50. El material se ve igual en el servicio y en la reserva — 7 de septiembre de 2026

- `consumibles_planificados` (detalle de la unidad) publica la identidad
  completa del insumo: `clasificacion`, `variante` y `color` por separado,
  `detalle` (la combinación que resume la tarjeta del servicio) e `imagen`,
  resuelta con `_imagen_consumible` — foto cargada, imagen del catálogo o
  nada, sin inventar una imagen que no corresponde al material.
- La fila de «Materiales para este trabajo» adopta las mismas piezas visuales
  que la tarjeta de «Insumos y materiales» de la reserva: casilla
  (`reservation-consumable__select`), miniatura (`__media`, 44 px), identidad
  (`__identity` con el tipo, el nombre y los distintivos `__variants`) y la
  existencia (`__stock`). Antes era una fila de texto donde el color y la
  existencia se pegaban («Blanco3200 g en existencia»); ahora el precio y los
  equipos compatibles van en `reservation-service-material__meta`, separados
  por CSS.
- La cantidad puede quedar vacía en los dos caminos y ahora se dice en los
  dos: el asistente sugiere la cantidad por pieza, pero
  `consumibles_sugeridos_servicios` y `_validar_consumibles` registran
  `cantidad_solicitada=None` con `metodo_estimacion='revision'` cuando no hay
  valor. Versión del asistente `20260914-materiales-imagen-v113`.
- Cuidado al revisar en el navegador: el servidor de desarrollo corre con
  `DEBUG=False`, así que las plantillas quedan en caché; hay que tocar un
  archivo `.py` (o reiniciar) para que un cambio de plantilla se sirva.

## 51. La cantidad se pide siempre y la máquina se cobra cuando la opera el laboratorio — 7 de septiembre de 2026

- Sin cantidad no hay valor estimado, así que dejarla vacía dejó de ser un
  descuido silencioso: el asistente no deja avanzar con un material marcado sin
  cantidad, ni en el trabajo por servicio ni en el catálogo de insumos de la
  reserva. La salida es explícita — «No conozco la cantidad: pido la estimación
  previa del laboratorio» (`[data-service-estimate]` y `[data-resource-estimate]`,
  controles de interfaz que no se envían) —, y con ella las cantidades vacías
  siguen registrándose como `metodo_estimacion='revision'`, como antes.
- Apoyo para llenarla, en vez de solo exigirla: cada material muestra la
  referencia del catálogo por pieza y las `instrucciones_solicitud` del
  inventario («carga el modelo en el laminador y escribe los gramos»), el
  campo se rellena con la cantidad sugerida × piezas y el laboratorio ofrece
  la estimación previa a quien no la conoce.
- `calcular_cotizacion` devuelve `materiales_por_calcular` y `aviso_estimacion`:
  cuando falta una cantidad, la estimación dice qué material no está incluido,
  en la cotización del asistente y en el resumen final.
- El uso del equipo se cobra cuando el laboratorio ejecuta el trabajo
  (`MODALIDADES_EJECUTA_LABORATORIO = {modelo_listo, diseno_completo}`), con el
  descuento del segmento: un estudiante asume una fracción de las horas de
  máquina. Con asesoría en la unidad la persona reserva el equipo y se mantiene
  como referencia. La unidad puede desactivarlo con
  `ConfiguracionOperativaUnidad.cobrar_uso_equipo_ejecucion` (migración 0157,
  activo por omisión); `politica_cobro_servicios(configuracion, modalidad)` lo
  resuelve para la estimación y para la liquidación del cierre.
- Versión del asistente `20260914-cantidad-y-equipo-v114`.

## 52. Cantidad por unidad con total calculado, y el equipo del servicio asistido — 8 de septiembre de 2026

- La persona escribe **cuánto usa una unidad** y el sistema muestra el total,
  calculado y no editable: por pieza en el trabajo por servicio (`× piezas`) y
  por sesión en la reserva de recursos (`× sesiones`). Antes el campo era el
  total y el asistente lo rellenaba solo al cambiar las piezas, así que
  aparecía un número que nadie había escrito. Ahora el campo nace vacío, con la
  referencia del catálogo como ejemplo.
- Al servidor sigue yendo lo mismo que antes: el consumo del trabajo completo
  en el servicio (`consumibles_servicio`) y el de una sesión en la reserva
  (cada sesión registra su `ReservaConsumible`). La existencia se compara ya
  con el consumo total, no con el de una unidad.
- Desaparece el selector «¿las cantidades son por sesión o del programa?»
  (`alcance_cantidades`, en asistente, `crear_reserva`,
  `calcular_costo_referencial_recursos` y el comprobante): la cantidad siempre
  es la de una sesión y el total lo calcula el sistema, así que la pregunta ya
  no tenía sentido.
- Con «diseño con asesoría» la tarjeta del equipo se arma como en la reserva de
  recursos —su software se integra y se puede marcar—, y la sección de insumos
  deja de mostrar un cero: explica que los materiales del trabajo se eligen
  arriba, junto a las piezas, porque en un servicio vienen del catálogo técnico
  (`describeEquipmentConsumables`, `integrateResourcesIntoEquipment` con
  `eligeInsumos`).
- Versión del asistente `20260914-cantidad-por-unidad-v115`.

## 53. La reserva pregunta sus piezas, como el servicio — 8 de septiembre de 2026

- La reserva de recursos pide «¿Cuántas piezas, muestras o ensayos harás en
  cada sesión?» (`piezas_por_sesion`, campo `#piezasPorSesionReserva` al frente
  del catálogo de insumos, valor 1 por omisión). Antes solo se pedía la
  cantidad del insumo, así que «2 kg» no distinguía dos piezas de un kilo de
  veinte de cien gramos y quien revisaba no podía juzgar la cantidad.
- La cadena queda igual en los dos caminos: se escribe el consumo **de una
  pieza** y el sistema calcula el total —`por pieza × piezas × sesiones` en la
  reserva, `por pieza × piezas` en el servicio—, lo muestra sin permitir
  editarlo y compara la existencia con ese total. La etiqueta del campo pasa a
  «Cantidad por pieza» en cuanto hay más de una.
- Al servidor sigue yendo el consumo de una sesión (`por pieza × piezas`), de
  modo que cada sesión registra su `ReservaConsumible` sin cambios de contrato.
  Las piezas se guardan en `Reserva.cantidad_piezas` —el mismo campo del
  servicio— y aparecen en el comprobante junto a la cantidad («2 kg solicitados
  · 5 piezas») y en el cajón del laboratorio, junto a la provisión.
- El campo se oculta en la ruta de servicio, que ya pregunta sus piezas en el
  detalle del trabajo. Versiones `20260914-piezas-en-reserva-v116` (asistente) y
  `20260914-piezas-v36` (panel).

## 54. Acceso institucional y perfil con el trabajo real de cada rol — 9 de septiembre de 2026

- La pantalla de acceso deja de ser la del tema comprado: imagen propia del
  laboratorio (`img/generated/home-hero/hero-laboratorio-conectado.png`, la
  misma del inicio, con velo oscuro), texto en español que nombra la
  plataforma, y las tres puertas ordenadas — correo institucional, Gmail para
  externos y usuario con contraseña. «Forget password?» apuntaba a `#`; ahora
  lleva a `account_reset_password`.
- `login_view` respeta el `?next=` validado con
  `url_has_allowed_host_and_scheme`: quien llega desde una página que pidió
  sesión vuelve a ella, no al inicio; un destino de otro dominio se ignora. Ya
  autenticado, `/login/` lleva al perfil.
- El perfil dejó de mostrar cifras inventadas (proyectos visitados, sesiones
  activas, certificaciones, «perfil actualizado» calculado con la fecha de
  registro) y tres interruptores que no guardaban nada. En su lugar:
  - Chips de rol reales: administrador del sistema, personal de la unidad que
    atiende, y el tipo de usuario del perfil institucional.
  - Estado de sus solicitudes (en revisión, confirmadas, en ejecución,
    completadas), la próxima reserva y las cinco últimas, cada una con el
    enlace de siempre al expediente de «Mis reservas».
  - Quien atiende una unidad ve las suyas con las solicitudes que esperan
    decisión y el enlace al panel (`gestion_unidad`), ordenadas por trabajo
    pendiente y limitadas a cinco; un administrador del sistema las ve como
    «Unidades de la plataforma».
  - Quien escribe guías ve cuántas tiene en edición, en revisión y publicadas,
    con el enlace a su lista.
  - Las novedades salen de `NotificacionReserva`, con su enlace real.
- `Reserva.url_seguimiento` centraliza el enlace `?reserva=<id>#mis-reservas`
  que ya usaban los avisos y la lista de guías; de paso deja de fijar
  `laboratorio_detalle` y respeta la ruta de cada dependencia.
- Versión de los estáticos de acceso y perfil `20260915-perfil-institucional-v5`.

## 55. Salir de la sesión y el perfil como puerta, no como segundo panel — 9 de septiembre de 2026

- No existía forma de cerrar sesión en la interfaz: la ruta `logout` estaba
  publicada pero ningún enlace la usaba. Ahora está en la cabecera junto a «Mi
  perfil» y en el perfil bajo «Cambiar contraseña». `salir` pasa a exigir POST
  (`require_POST`): con GET bastaba una imagen o un enlace ajeno para sacar a
  alguien de su sesión.
- El perfil dice qué tiene la persona y abre la puerta; el detalle sigue
  viviendo donde ya estaba:
  - La gestión se resume en una tarjeta («atiendes N unidades · M solicitudes
    esperan tu decisión») con hasta tres unidades y su enlace al panel. La
    bandeja, la agenda y el inventario no se repiten: son del panel.
  - Las novedades salieron del perfil porque la campana de la cabecera ya las
    muestra.
  - De «Mis reservas» quedan la próxima y las tres últimas, como índice entre
    unidades —la única vista que cruza laboratorios—, cada una con su enlace al
    expediente.
- Versión de los estáticos de acceso, perfil y botones `20260915-perfil-puerta-v6`.

## 56. Datos institucionales obligatorios y vigentes por período — 9 de septiembre de 2026

- El correo institucional solo entrega nombre y correo, y con eso la persona
  entraba y nunca completaba el resto. Ahora
  `webcitt/domains/usuarios/vigencia.py` decide cuándo un perfil está listo y
  `PerfilInstitucionalVigenteMiddleware` cierra las funciones hasta entonces.
- Alcance de la compuerta: `/reservas/` —crear, seguir, cambiar, comprobantes,
  cotizaciones, firmas—, salvo la lectura de una guía publicada
  (`/reservas/actividades/guias/`). El portal público se sigue leyendo con la
  cuenta incompleta, y el panel de la unidad queda fuera a propósito: ahí se
  atiende el trabajo de otros bajo un rol que asigna la unidad, y detenerlo por
  un dato del perfil personal dejaría al laboratorio sin atender su agenda.
- La respuesta se adapta a quien pregunta: una navegación del navegador vuelve
  a `/profile/?completar=1` con el formulario abierto; una llamada del
  asistente recibe el mismo aviso en JSON con `perfil_url`, que es lo que sabe
  mostrar.
- Vigencia por período académico, sobre `VinculacionUsuarioPeriodo`, que ya
  guardaba la clasificación de cada período sin reescribir la historia:
  - Cuando los datos no cambian, la vinculación del período en curso se
    registra sola desde el perfil: nadie se interrumpe.
  - Al estudiante que viene de un período ordinario anterior se le propone el
    semestre siguiente (`siguiente_semestre`) y **debe confirmarlo**: hasta que
    lo haga, las funciones esperan. El irregular corrige la propuesta en el
    mismo formulario antes de confirmar.
  - Guardar el perfil confirma el período (`confirmar_periodo`), y el aviso lo
    dice con el código del período.
- Sin calendario académico publicado no se puede exigir la confirmación: basta
  con que los datos estén completos.
- Las pruebas que reservan identifican a sus usuarios con
  `webcitt/tests/utiles.identificar`, porque una cuenta sin clasificar ya no
  puede reservar. Versión de los estáticos del perfil
  `20260915-perfil-obligatorio-v7`.

## 57. Turismo en el catálogo y el formulario del perfil vuelve a desplazarse — 10 de septiembre de 2026

- El catálogo institucional suma `turismo` («Carrera de Turismo») en la
  Facultad de Industrias Agropecuarias y Ciencias Ambientales, con su
  migración `0158_carrera_turismo`. El selector sigue filtrando por facultad:
  cada carrera declara la suya en `CARRERA_FACULTAD` y el formulario muestra
  solo las que corresponden.
- El formulario del perfil no se podía desplazar: la ventana limita su alto y
  esconde el desbordamiento, pero el `<form>` es el hijo directo del contenido
  y cortaba la cadena flex, así que el cuerpo no encogía y el formulario
  quedaba recortado. Con `display:flex`, `flex-direction:column` y
  `min-height:0` en ese formulario —y `min-height:0` en el cuerpo— el cuerpo
  vuelve a desplazarse y el pie con «Guardar cambios» queda siempre visible.

## 58. Cédula en lugar de código y perfil profesional solo para quien lo publica — 10 de septiembre de 2026

- `UserProfile.codigo_estudiante` pasa a llamarse `cedula` («Cédula o documento
  de identidad», migración `0159` con `RenameField`, sin perder lo registrado).
  Es el documento con el que la Universidad identifica a cualquiera, así que se
  pide a todos y sigue siendo obligatorio para el estudiante, como lo era el
  código. Diez dígitos se validan con el dígito verificador ecuatoriano
  (`cedula_ecuatoriana_valida`); un pasaporte o documento extranjero se acepta
  tal cual, porque no sigue esa regla.
- «Cargo o función» y «Biografía» dejaban datos que no se usaban en ninguna
  parte. Ahora forman el **perfil profesional** y solo se piden a quien aparece
  como personal: quien atiende una unidad o administra la plataforma
  (`_perfil_publico`). Al estudiante ni se le muestran, y al guardar sin la
  sección esos campos se conservan en vez de vaciarse.
- Esa información alimenta la ficha: `ResponsableUnidad.descripcion_publica`
  usa la descripción que declaró la unidad y, si no la hay, el cargo o la
  biografía del perfil; el «Equipo humano» del panel ya la muestra. El resto de
  la ficha ya tomaba del perfil el nombre, el correo, el teléfono y la foto.
- Pendiente y avisado: el equipo de «Quiénes somos» sigue siendo contenido de
  demostración escrito en la plantilla, y la ficha pública de cada unidad
  todavía no muestra a su personal. Ambos son los candidatos naturales para
  consumir este perfil profesional.

## 59. Las pantallas de cuenta heredan la cara institucional — 10 de septiembre de 2026

- Recuperar la contraseña mostraba la plantilla cruda de allauth: sin estilos,
  con su propio «Menú:» y textos en inglés. Ahora
  `webcitt/templates/account/base.html` extiende la base del portal y reutiliza
  la tarjeta del inicio de sesión, así que toda la familia de acceso se ve
  igual. Las páginas propias llenan `auth_lema`, `auth_titulo`,
  `auth_subtitulo` y `auth_cuerpo`; una pantalla de allauth que no se haya
  reescrito cae en `content` y al menos queda dentro del portal.
- Escritas en español y con la salida clara: pedir el enlace, avisar de que se
  envió, definir la nueva contraseña (con su rama de enlace caducado),
  confirmar, cambiarla desde el perfil y definirla por primera vez cuando se
  entró con el correo institucional.
- Los campos vienen de allauth sin clases propias, así que se visten por su
  envoltorio (`.auth-form-field`) en `autenticacion.css`.
- Recorrido comprobado contra el servidor: pedir el enlace, recibirlo en el
  correo de consola y abrirlo hasta el formulario de la nueva contraseña.

## 60. Cuatro fotografías más en la portada — 10 de septiembre de 2026

- El carrusel del inicio pasa de nueve a trece imágenes con escenas propias de
  la Universidad: análisis clínico con micropipeta, fila de microscopios en
  docencia, simulación logística con realidad virtual y agricultura de
  precisión con dron en campo
  (`img/generated/home-hero/hero-analisis-clinico.png`,
  `hero-microscopia-docencia.png`, `hero-simulacion-logistica.png`,
  `hero-agricultura-precision.png`).
- Los marcadores del pie se generan por JavaScript según el número de
  imágenes; los del HTML se actualizaron para que sin JavaScript también
  correspondan.

## 61. Las piezas entran al cierre operativo — 10 de septiembre de 2026

- En «Ejecución» la cantidad de material no decía si era por pieza o por todo
  el trabajo. Ahora la etiqueta es «Uso útil total» y «Desperdicio total»: lo
  registrado siempre es lo que salió del lote, que es lo que el inventario
  descuenta y lo que la liquidación cobra.
- «Horario y resultado real» pregunta las **piezas obtenidas**
  (`ejecucion_piezas`), propuestas con las que declaró la solicitud y
  corregibles cuando salieron más o menos. La solicitud no se toca; el cierre
  guarda `piezas_solicitadas` y `piezas_producidas` en `detalle_ejecucion`.
- Cada material trae un asistente de piezas (solo si la reserva declaró más de
  una): «Las piezas salieron iguales» multiplica la cantidad de una pieza,
  «Cada pieza usó una cantidad distinta» abre una casilla por pieza y suma, y
  «Escribo el total medido» deja el campo libre. Con las dos primeras el total
  queda calculado y bloqueado, como en el asistente de reserva.
- La línea de referencia recuerda lo que pidió el usuario: piezas declaradas,
  cantidad estimada y su equivalente por pieza, para comparar contra lo real.
- El servidor valida el reparto: `_detalle_por_pieza` exige una cantidad por
  cada pieza obtenida y que la suma coincida con el uso registrado; guarda
  `detalle_piezas` y, cuando fueron iguales, `por_pieza`.
- Más de 24 piezas deshabilita el detalle pieza por pieza: se usa el promedio o
  el total medido.
- Comprobado con el panel real en jsdom (`harness_cierre.js`): campo de piezas,
  referencia, multiplicación, suma, cambio del número de piezas rehaciendo las
  casillas y el JSON que se envía.

## 62. Las piezas se preguntan en la tarjeta del equipo — 10 de septiembre de 2026

- En la reserva de recursos la pregunta por las piezas quedaba al pie del
  catálogo, lejos de las cantidades: ahora `placeWorkUnitsField` la sube a la
  tarjeta del equipo marcado que ofrece insumos, como una franja sobre el
  software y los insumos (`grid-column: 1 / -1`).
- Si ningún equipo tiene insumos ligados, la franja vuelve a su sitio del
  catálogo: `rememberWorkUnitsHome` guarda el padre **y** el hermano siguiente,
  porque `parkIntegratedResources` solo sabe colgar al final.
- Manda el equipo marcado (`is-selected`); si no hay ninguno, el primero con
  insumos.
- Cuidado al fotografiar el asistente: las variables `--rw-*` viven en
  `#equiposReservaModal.reservation-wizard-enhanced`, así que el recorte debe
  envolver con ese id y esa clase o los colores se pierden.
- El servidor de desarrollo sirve los estáticos desde `static_deployed`: tras
  tocar CSS o JS hay que correr `collectstatic --noinput` o el navegador
  simulado seguirá viendo la versión anterior.

## 63. Cada equipo declara su trabajo y la cantidad deja de ser opcional — 11 de septiembre de 2026

- **Desmarcar un equipo volvía a marcarlo.** El software propio («incluido con
  el equipo») se marca solo al elegir la máquina, y
  `syncSoftwareEquipmentCompatibility({autoSelect:true})` lo tomaba como una
  elección de la persona y devolvía el equipo a la selección. Ahora el
  autoSelect ignora el software con `dataset.rwRequired`.
- **Las piezas son de cada equipo.** Se acabó la franja única que se mudaba de
  tarjeta: `syncEquipmentWorkUnits` clona `#plantillaTrabajoEquipo` en cada
  equipo marcado y `workUnitsByEquipment` conserva lo escrito cuando la lista
  de equipos se vuelve a dibujar. `resourceWorkUnits(card)` toma las piezas de
  la tarjeta donde vive el material.
- Para que el multiplicador sea el correcto, el insumo **original** (el que se
  edita y viaja al servidor) se coloca en un equipo marcado; los espejos van a
  los demás compatibles.
- `syncEquipmentWorkSummary` arma lo que se envía: `piezas_por_sesion` es la
  suma de las tarjetas y `detalle_trabajo_recursos` una línea por equipo
  («Impresora 3D FDM · 3 piezas: soportes en PLA»), que el servidor guarda en
  `detalle_trabajo` y el comprobante muestra como «Trabajo solicitado».
- El catálogo general conserva su propia cuenta de piezas, visible solo si
  queda algún material fuera de las tarjetas.
- **La cantidad de material es obligatoria en las dos rutas.** Desaparecen la
  casilla «No conozco la cantidad: pido la estimación previa del laboratorio»
  (recursos y servicios), su CSS y los avisos que la mencionaban. El servidor
  sigue aceptando `metodo_estimacion='revision'` porque el laboratorio puede
  registrar cantidades por calcular desde el panel.
- Escenarios nuevos del navegador simulado: `deseleccion` (marcar y desmarcar)
  y `dosequipos` (dos tarjetas con piezas distintas y sus totales).
- Una prueba de la cola de servicios fallaba los viernes: ocupaba las horas en
  el mismo día que iba a proponerse (hoy + 3), así que la propuesta se corría
  un día. Ahora la cola se llena veinte días después y la prueba ya no depende
  del día de la semana.

## 64. Reservar solo el espacio se declara, no se bloquea — 11 de septiembre de 2026

- Un área técnica exigía equipo o software y devolvía «Selecciona un equipo o
  software asociado a…». Trabajar solo en el puesto es legítimo (una práctica
  sin máquina, un ensayo con material propio), así que
  `validateSpaceEquipmentSelection` desaparece y en su lugar la solicitud
  **declara su alcance**: `#avisoAlcanceRecursos` enumera el espacio, los
  insumos con su cantidad y deja claro que no se reserva ninguna máquina ni
  ningún programa; sin la confirmación no se avanza.
- La confirmación se vuelve a pedir cuando cambia lo que se solicita: el aviso
  guarda una firma de su contenido en `dataset.firma`.
- `cascadeConsumablesStageOpen` también se abre con solo el espacio, así que
  los insumos de uso general (los que no cuelgan de un equipo) se pueden pedir
  con su cantidad obligatoria y las piezas del catálogo general.
- El software de la ruta de recursos siempre vive en la tarjeta de su equipo;
  «solo software» no existe como tal y no se reintrodujo la sección de software
  de uso general que se había retirado.
- Cuidado con el estilo: `#equiposReservaModal .reservation-card` fija
  `background: #fff !important`, así que un aviso no se distingue por el fondo
  de la tarjeta; se distingue por dentro (cintillo, lista y caja de
  confirmación en dorado suave).
- Escenario nuevo del navegador simulado: `soloespacio` (con `CON_INSUMO=1`
  simula un insumo de uso general quitándole su atadura a un equipo).

## 65. Enviar la reserva ya no lleva a una guía ajena — 11 de septiembre de 2026

- Síntoma: al enviar una reserva de práctica docente sobre una actividad del
  catálogo, el asistente redirigía a `editar_guia_practica` y respondía 404
  «Guía no disponible para edición».
- Causa: `asegurar_borrador_guia_desde_reserva` devolvía la guía de mayor
  versión de la actividad. Si su docente ya tenía una versión posterior en
  borrador, la reserva de otra persona se colgaba de ese borrador y
  `crear_reserva` la mandaba a terminarlo, aunque `puede_editar_guia` no se lo
  permitiera.
- Arreglo doble: con la actividad tomada del catálogo se devuelve la versión
  **publicada** (los borradores posteriores son de su autor), y el destino tras
  enviar solo existe si quien reservó puede editar esa guía; si no, la
  solicitud termina en su comprobante.
- `_puede_editar_guia` pasa a llamarse `puede_editar_guia` porque ahora la usan
  el editor, el expediente de la reserva y la lista de guías, cuyo botón
  «Corregir» ya no se muestra por `es_editable` a secas.
- La reserva afectada (RL011-000088) sí quedó registrada: el 404 era solo la
  página de destino.

## 66. Ventana de atención 08:00–18:00 y agendas que se leen de una mirada — 11 de septiembre de 2026

- Las unidades publican su jornada de 07:00 a 20:00, pero al público se le
  atiende de **08:00 a 18:00**. Las dos horas siguientes quedan para casos
  justificados y solo las registra la administración, igual que el fin de
  semana. La regla vive en `webcitt/models/operaciones.py`
  (`HORA_APERTURA`, `HORA_CIERRE_ATENCION`, `HORA_CIERRE_AMPLIADO`,
  `ventana_atencion`), no en los datos de cada unidad.
- La aplican `_validar_horario_operativo` (con mensajes propios para «empieza a
  las 08:00» y «termina a las 18:00»), la propuesta de entrega de servicios, la
  agenda del panel y el asistente, que recibe la ventana en
  `data-hora-apertura`, `data-hora-cierre` y `data-hora-cierre-ampliado`.
- Lo ya reservado fuera de la ventana se sigue viendo: el panel no esconde una
  atención registrada y la agenda semanal del asistente suma las horas de los
  eventos existentes.
- Menos desplazamiento: la fila horaria del asistente pasa de 96 px a 76 px (y
  de 126 px a 70 px en la vista unificada), su contenedor a
  `clamp(620px,82vh,960px)`; la del panel de 88 px a 72 px con el marco hasta
  920 px. Con diez filas en vez de trece, la jornada completa cabe sin
  desplazar.
- «Mis reservas» arranca en 08:00–18:00 y solo se estira si una reserva
  registrada se sale de ahí.

## 67. El horario de atención lo decide cada laboratorio — 11 de septiembre de 2026

- La ventana dejó de ser institucional: `ConfiguracionOperativaUnidad` gana
  `hora_apertura_atencion` (08:00) y `hora_cierre_atencion` (18:00), que son
  solo el punto de partida. Un laboratorio que atiende de 07:00 a 20:00 lo
  declara y **sus usuarios** reservan esas horas, sin pedir permiso.
- `ventana_atencion(configuracion, es_administrador=False)` devuelve la franja
  de esa unidad; con `es_administrador` devuelve `(0, 24)`, es decir, manda la
  jornada operativa (`HorarioOperacionUnidad`), que sigue siendo el límite real.
- Se declara en horas en punto y el cierre debe ser posterior a la apertura:
  lo comprueba `ConfiguracionOperativaUnidad.clean()`.
- Se edita en el formulario del administrador (`webcitt/admin/unidades.py`),
  en el bloque «Horario de atención al público», junto al resto de la
  configuración operativa de la unidad.
- Lo aplican la validación de reservas, la propuesta de entrega, la agenda del
  panel (que además recorta su alto a esa franja) y el asistente, que recibe la
  franja en `data-hora-apertura` y `data-hora-cierre`.
- Migración 0160. Las catorce unidades existentes quedaron con 08:00–18:00.
- Comprobado contra la base real: con 07:00–20:00 declarado una estudiante
  reserva 07:00 y 18:00–20:00; con el valor de partida esas horas se rechazan
  con el horario de la propia unidad en el mensaje y la administración las
  sigue registrando.

## 68. Auditoría del sistema de reservas: fantasmas fuera — 11 de septiembre de 2026

- **Aviso invisible (error real).** Al pulsar «Continuar» sin fecha ni horas,
  `showCalendarSelectionError` escribía en `#selSummary`, dentro de un panel que
  la propia agenda oculta en cada dibujo, y además escondía el mensaje del paso:
  la persona no veía nada. Ahora el aviso sale en el mensaje del paso y la barra
  de la agenda semanal se marca en rojo.
- **Panel de horas del día retirado.** `renderDayHours`, `filasHorarioDia` y
  `updateSummary` llenaban ese panel oculto, y `inicializarCalendario` exigía
  `#hourList` para arrancar. Se retiran ellos, su marcado y su estilo.
- Otras funciones sin un solo uso: `enviarReserva` (envío anterior al
  asistente), `setCalendarView` (ignoraba su parámetro), `reservarEquipo` y
  `moveField`.
- **49 métodos de modelo muertos** en equipos, reservas, unidades, consumibles,
  núcleo, espacios, finanzas, operaciones y el conversor de guías: restos de
  versiones anteriores que no aparecían en código, plantillas, JavaScript ni
  como texto en el admin. Unas mil líneas menos.
- Auditorías que quedaron limpias: las 387 rutas registradas, todos los
  `{% url %}`, `{% include %}`, `{% extends %}` y `{% static %}` de las
  plantillas, `manage.py check` y `makemigrations --check`.
- El guion de auditoría vive en el scratchpad (`auditar_fantasmas.py`,
  `auditar_enlaces.py`, `auditar_python_muerto.py`); conviene repetirlo antes de
  cerrar cada bloque grande.

## 69. Estructura: gestion.py se reparte y el árbol queda ordenado — 11 de septiembre de 2026

- `gestion.py` tenía 5.710 líneas. Salen dos módulos hermanos, al estilo de
  `gestion_reportes.py`: `gestion_agenda.py` (agenda semanal, carriles y
  calendario mensual, 290 líneas) y `gestion_analitica.py` (series, gráficas e
  indicadores de inventario, activos y finanzas, 780 líneas). El panel queda en
  4.680 y las nueve vistas públicas no cambian.
- Los nombres conservan su guion bajo a propósito: al publicarlos chocaban con
  variables locales que se llaman igual que la función que las produce
  (`analitica_inventario = _analitica_inventario(...)`).
- `var/log/` y `var/logs/` eran dos carpetas para lo mismo; el README pasa a
  `var/logs/`, que es donde escriben los guiones.
- Se retira `guias/includes/seccion.html`: ninguna vista la incluía, porque ese
  HTML lo arma `seccion_html` en Python.
- Auditoría de módulos y plantillas: no queda ningún módulo sin importar ni
  ninguna plantilla propia sin usar.

## 70. Cierre de la auditoría — 11 de septiembre de 2026

- Comprobaciones que quedaron limpias: los 57 modelos del admin abren su
  listado y su formulario de alta (`probar_admin.py` en el scratchpad, con
  `Client(SERVER_NAME='127.0.0.1')` porque `DEBUG=False` rechaza «testserver»),
  las 387 rutas, `manage.py check`, `makemigrations --check`, ruff, `node
  --check` y los diez escenarios del navegador simulado sin un solo error de
  JavaScript.
- **Un hallazgo se revirtió a propósito.** La compuerta de perfil libera todo
  `/reservas/actividades/guias/`, no solo la lectura. Al intentar afinarlo se
  cayeron cinco pruebas de guías: firmar, validar y cargar la versión firmada
  son trabajo docente y de la unidad, y la compuerta existe para el flujo de
  reservas. Se conserva el comportamiento y se explica en el código.

## 71. Dos laboratorios más, listos y probados — 11 de septiembre de 2026

- `cargar_laboratorios_institucionales` deja operativos el **Laboratorio de IA
  y Ciencia de Datos** (9 puestos, 2 salas, 4 programas, 3 materiales de uso
  general, 2 servicios) y el de **Biotecnología Aplicada** (7 equipos, 3 áreas,
  8 artículos con 9 lotes y vencimiento, 3 servicios). Ambos con su personal
  público, dos cuentas operativas cada uno y su horario declarado: 08:00–18:00
  el primero, 07:00–18:00 el segundo. La carga es idempotente.
- `test_laboratorios_institucionales.py` los prueba como los usaría la
  Universidad: reserva de puesto con licencia y sala, licencias concurrentes
  que se agotan, sala de uso general reservada sola, horario propio de cada
  unidad, práctica docente con guía aprobada y reactivos por muestra, servicio
  con materiales obligatorios y cierre operativo que descuenta del lote
  abierto.
- **Error real encontrado al cargar el segundo laboratorio:** `equipo_codigo`
  de la reserva admitía veinte caracteres, pero guarda el código del recurso
  principal, que puede ser un espacio (60) o un software (40). El área
  `BIO-MESON-PREPARACION`, de veintiún caracteres, rompía la creación con un
  error de base de datos. Migración 0161: el campo pasa a sesenta.
- Lo que enseñaron las pruebas y ya era correcto: el software marcado como
  propio del equipo se incluye solo, reservar un equipo exige declarar el
  espacio, una práctica del catálogo exige su guía aprobada y un servicio suma
  sus materiales obligatorios aunque se marque uno solo.
- El navegador simulado acepta ahora `UNIDAD=<slug>` y trae dos escenarios
  genéricos, `laboratorio` y `servicioLab`, que recorren cualquier unidad
  cargada sin conocer sus códigos.

## 72. Cada laboratorio nombra lo que produce — 11 de septiembre de 2026

- Cargar un laboratorio húmedo dejó a la vista que el asistente pedía «cantidad
  por pieza» para ocho muestras de ADN. `ConfiguracionOperativaUnidad` gana
  `unidad_de_trabajo` (piezas, muestras o ensayos; migración 0162) y la
  propiedad `palabras_trabajo` con su singular y su plural.
- La palabra viaja al asistente en `data-trabajo-singular` y
  `data-trabajo-plural`, y al panel en el mismo par sobre
  `#unitManagementConsole`; el comprobante la recibe en el bloque del trabajo.
- La usan las etiquetas de cantidad, los totales por unidad de trabajo, el
  detalle que se envía al laboratorio, la propuesta de entrega, la cotización,
  el aviso de existencia y el asistente de cierre del panel.
- Biotecnología quedó en «muestras», IA y Ciencia de Datos en «ensayos» y el
  resto conserva «piezas», que es el valor de partida.

## 73. Revisión completa para producción: usuarios, lo público, fantasmas y hojas de cálculo — 12 de septiembre de 2026

- Tres tipos de usuario y nada más. El superusuario administra todo; el
  personal de una unidad es su administrador principal (`Unidad.administrador`)
  y sus responsables con cuenta (`ResponsableUnidad`), y solo gestiona su
  unidad; el resto son usuarios con lo propio. Se retiraron los dos caminos
  paralelos que otorgaban gestión (`Unidad.mentor`, `Integrante`) y
  `CarpetaSubmodulo`, sin uso (migración 0166). `test_tipos_de_usuario.py`
  fija lo que alcanza cada tipo, incluido quien no inicia sesión.
- Lo público: la ficha, el catálogo y la agenda con identidades enmascaradas se
  leen sin sesión; existencias y precios por unidad del inventario solo con
  sesión (`mostrar_existencias_reserva`). Producción exige confirmar el correo
  de una cuenta nueva (`ACCOUNT_EMAIL_VERIFICATION = "mandatory"`) y no
  detiene la entrada social.
- Fantasmas fuera: «Flujo predeterminado» se guardaba y nadie lo leía;
  `Unidad.laboratorio` duplicaba `ubicacion` (trece unidades migradas,
  migración 0167); `FablabMachine`, `FabricationJob`, `FabricationStep` y
  `FabricationConsumible` eran el modelo anterior al inventario, sin un
  trabajo registrado (migración 0168).
- El centro de reportes entrega hoja de cálculo además de HTML y PDF, desde el
  mismo presentador: portada de criterios y una hoja por tabla, con cifras que
  Excel reconoce como números (`reportes_excel.py`). Los formatos F1 y F2
  usan el mismo libro.
- `docs/unidades-y-centros-id.md` recoge el análisis: estado para producción,
  lo que ve cada tipo de usuario, qué comparten y qué no los cuatro tipos de
  unidad con simulaciones sobre el sistema actual, el modelo de datos por tipo,
  la ruta hacia los Centros I+D, los reportes y el orden de trabajo.
  `docs/autenticacion.md` sustituye a `google_auth_setup.md`, que era una
  plantilla pegada por error.
- Decisiones pendientes de la Universidad: Decanato como excepción a los tres
  tipos; si la agenda muestra nombres a los demás usuarios con sesión; si el
  registro con contraseña sigue abierto a cualquier dominio.

## 74. La planta produce: productos, recetas, órdenes, lotes y salidas — 12 de septiembre de 2026

- Lo que fluye por una unidad tiene nombre en todas: equipo principal (se
  reserva) y auxiliar (acompaña y no se reserva aparte, `EquiposServicios.rol`
  y `apoya_a`); insumo, reactivo, material, empaque, protección y limpieza
  (`Consumible.clasificacion`); y, desde este bloque, producto terminado,
  intermedio, subproducto y residuo (`Producto.tipo`). La tabla comparada
  FabLab, Biotecnología y planta está en `docs/unidades-y-centros-id.md` § 3.3.
- Módulo de producción (`webcitt/models/produccion.py`, migración 0171):
  `Receta` es la lista de materiales por corrida base con `InsumoReceta` y
  `SalidaReceta`; `OrdenProduccion` la escala con un factor, ocupa la línea y
  los equipos con un `BloqueoAgendaUnidad` de tipo «Corrida de producción»
  (una reserva de la línea esos días recibe el motivo, y una corrida no se
  planifica sobre reservas vigentes), y al cerrarse descuenta cada insumo del
  lote abierto con `EntradaInventario` idempotente y crea los `LoteProducto`
  con vencimiento, merma y rendimiento. Un terminado espera en cuarentena el
  control de calidad; un subproducto sale directo; un residuo nace retirado.
  `MovimientoProducto` registra venta (ingreso confirmado en finanzas,
  categoría «producto»), transferencia (la unidad destino recibe un lote en
  bodega de su insumo con el mismo vencimiento), muestra, consumo interno y
  baja; una salida registrada no se edita.
- Panel: pestaña «Producción» con órdenes, lotes, salidas, productos y
  recetas; cajones para producto, receta (filas repetibles), orden (con la
  escala explicada), avance (iniciar o cerrar con filas de insumos por lote y
  de salidas), control de calidad y salida de producto (campos de
  transferencia solo cuando corresponde). Módulo `produccion` en
  `MODULOS_OPERATIVOS`, recomendado para coordinación, responsable técnico y
  laboratorista; capacidad «Registra producción» en la configuración, que
  decide si la pestaña existe. Un laboratorio no la ve.
- Reporte «Producción» (órdenes que tocan el período, con planificado,
  obtenido, merma, rendimiento, lotes y ventas) en HTML, PDF y hoja de
  cálculo, solo en unidades que producen. La ficha pública lista lo que se
  produce con presentación y precio, nunca residuos ni existencias.
- Cargador: la Planta Piloto de Lácteos trae seis productos y tres recetas
  (queso fresco, yogur de mora, leche pasteurizada, con suero, crema y agua de
  lavado como salidas). Corrección de idempotencia: el material de uso
  general de un servicio (cofias) ya no se ata a la máquina del servicio.
- Pruebas: `test_produccion_planta.py` (13) recorre carga, panel, ficha,
  bloqueo de la línea y conflicto con reservas, cierre con descuento por lote,
  calidad, venta a finanzas, transferencia entre unidades, permisos y reporte.
  Práctica en vivo sobre la base de desarrollo con las cuentas de la planta y
  arnés jsdom de la pestaña y sus cajones.

## 75. La receta con etapas: el proceso del que sale todo lo demás — 12 de septiembre de 2026

- Dos análisis previos fijan la ruta: `docs/planta-por-procesos.md` (de la
  orden de producción al plan de requerimientos, capacidad, plan maestro y
  calidad) y `docs/aula-de-produccion.md` (la planta como sistema real y como
  simulador: quién carga qué, dónde vive cada protocolo, los ejercicios
  acordes a los sistemas de producción reales y la trazabilidad por
  estudiante). Este bloque es el primero de esa ruta.
- `EtapaReceta` (migración 0172): cada paso del proceso con el tipo del
  cursograma (operación, inspección, transporte, espera, almacenamiento),
  equipo principal y área, trabajo y espera en minutos, personas, cuánta masa
  continúa, distancia y punto crítico de control con parámetro y límite.
  `InsumoReceta` y `SalidaReceta` saben en qué etapa entran o salen.
- `webcitt/domains/unidades/procesos.py` son funciones puras sobre una
  estructura de datos (`datos_de_receta`): resumen, balance de masa por
  porcentaje en la unidad de la corrida base, cronograma, diagrama de flujo,
  diagrama sinóptico (solo operaciones e inspecciones, con los materiales que
  entran), cursograma analítico con sus totales, y lo que la guía toma del
  proceso. Sirven igual para la receta real y, después, para un escenario de
  simulación.
- Panel: el cajón de la receta tiene filas repetibles de etapas, numeradas
  solas, y cada insumo o salida declara su etapa; la pestaña de producción
  muestra por receta el diagrama de flujo, la tabla de etapas y el enlace a
  la ficha de proceso (`gestion/unidades/<slug>/procesos/<id>/`), que trae
  ambos diagramas, el cursograma, el balance y el cronograma, imprimible.
  Reporte «Procesos» en HTML, PDF y hoja de cálculo, solo en unidades que
  producen.
- El editor de guías ofrece «Tomar del proceso»: llena equipos (con
  auxiliares), materiales por etapa, duración, el procedimiento paso a paso,
  los puntos críticos como medidas de seguridad y el resultado esperado desde
  `procesos/<id>/guia.json`; el docente ajusta. De paso quedó corregido un
  fallo latente: el documento de la guía nueva dereferenciaba
  `guia.actividad.codigo` dentro de un filtro y la página «Nueva guía» caía
  con quinientos; ahora usa `firstof`.
- Cargador: las tres recetas de la planta con sus etapas (once el queso,
  nueve el yogur, ocho la leche pasteurizada), con la leche entrando en la
  recepción, el cuajo en la tina, el suero saliendo en el desuerado y el agua
  de lavado en la limpieza. `test_procesos_planta.py` (9) cubre carga,
  motores, diagramas, cajón con validaciones, pestaña, ficha, reporte y
  guía; el arnés jsdom rearma las once etapas al editar.

## 76. El catálogo completo de lácteos y la hoja de ruta de la planta — 12 de septiembre de 2026

- `docs/ruta-planta-piloto.md` es la ruta única: doce secciones de la
  planta con actores, datos, interfaz y lo que reciben y entregan; las
  decisiones pedidas (reserva por proceso con todo marcado por defecto, guía
  general con cronograma y guías por sesión obligatorias, seguridad
  industrial de una planta de alimentos, visitas como solicitud con
  responsable y no como cuarto tipo de usuario, maquila ligada a un proceso)
  y el orden de construcción en doce pasos.
- Paso 1 hecho: la Planta de Lácteos declara todo lo que hace. Cuatro equipos
  nuevos (marmita con agitación, hiladora, mantequillera, cámara de
  maduración; la caldera también apoya a la marmita), diez insumos (cultivos
  termófilo y mesófilo, pulpa de mora, bicarbonato, glucosa, cera, la crema
  como intermedio de la propia planta, papel de mantequilla, frascos y
  baldes), siete productos (mozzarella, semimaduro, mantequilla, manjar,
  mazada, leche descremada y agua evaporada) y las ocho recetas con etapas:
  leche pasteurizada, yogur, queso fresco, mozzarella, semimaduro,
  mantequilla, manjar y crema, todas con la recepción como inspección con
  punto crítico al inicio y la limpieza al final.
- `Receta.software` (migración 0173) liga a cada proceso su software; hoy la
  trazabilidad, mañana los simuladores propios cuando existan. El cajón de
  la receta lo elige, la ficha y la guía prellenada lo muestran.
- `InsumoReceta.forma_parte` (migración 0174): materia prima de la corrida
  base, se incorpora al producto o auxiliar del proceso. El balance de masa
  suma en su etapa lo que se incorpora en kilos o litros (azúcar y pulpa del
  yogur, sal en seco del queso), no suma la salmuera ni el empaque, y trata
  el agua de lavado como salida externa al flujo, no como exceso. Las ocho
  recetas cierran el balance a menos de medio kilo del rendimiento declarado
  y la prueba lo exige.
- `MovimientoProducto` de tipo consumo interno admite un insumo receptor de
  la misma unidad: la crema del descremado entra como lote en bodega del
  insumo «crema madurada» y alimenta la mantequilla; el cajón de salida
  muestra los insumos propios en ese caso.
- Corrección de paso: un código de equipo de veinticuatro caracteres no cabe
  en el campo de veinte; la cámara de maduración es `LAC-EQ-MADURACION`.

## §77 · La práctica por proceso (paso 2 de la ruta de la planta)

**Qué resuelve.** El docente pide la planta diciendo qué proceso hará y a
qué escala; el sistema marca todo lo que el proceso exige y él solo llena
lo específico de su práctica. Es la tercera ruta del asistente, propia de
las unidades que registran producción y tienen recetas con etapas.

**Dónde vive.**
- `webcitt/domains/unidades/reservas/proceso.py`: `seleccion_por_proceso`
  deriva de la receta las áreas de sus etapas (más el área donde la planta
  publica cada equipo, si ninguna etapa lo ubica ahí), la primera unidad
  disponible de cada equipo con sus auxiliares, el software del proceso, los
  insumos escalados (obligatorios y opcionales), las personas máximas, los
  puntos críticos, la sesión propuesta desde la hora elegida (horas de
  línea hasta la última etapa con personas; el almacenamiento no cuenta) y
  los días siguientes que la corrida ocupa (lo trabajado que no cabe en la
  jornada, en jornadas; el reposo y la refrigeración, en días de
  calendario). `validar_cobertura_del_proceso` exige en la solicitud cada
  equipo y área de las etapas y cada insumo obligatorio.
  `guia_integrada_desde_proceso` prellena los apartados FT04 en HTML.
- Página `laboratorio/<slug>/procesos/<id>/practica/` (plantilla
  `reservas/practica_por_proceso.html`) y su JSON
  `.../practica/seleccion.json?factor=&hora=`. La página arma la misma carga
  que el asistente y la envía a `crear_reserva`; los recursos del proceso
  van bloqueados, la guía se muestra prellenada y el docente confirma que
  la revisó. Investigación, vinculación y capacitación no llevan guía.
- Motor (`reservas/views.py`): `receta_id` y `factor_proceso` solo en
  solicitudes de recursos, con receta activa y con etapas de la misma
  unidad; guarda `Reserva.receta` y `Reserva.factor_proceso` (migración
  0175); tras la compatibilidad de consumibles valida la cobertura del
  proceso; la sesión puede incluir la hora de almuerzo (`permitir_almuerzo`)
  porque un proceso no se detiene al mediodía, igual que el panel.
- Aprobación (`gestion.py`, dentro de la transacción tras `reserva.save()`):
  `orden_de_practica` crea la `OrdenProduccion` de origen práctica o
  investigación con el factor de la reserva, la línea del proceso, los
  equipos reservados y el bloqueo de agenda desde la fecha de la sesión
  hasta los días siguientes; rechazar, cancelar, inasistencia o no atendida
  cancelan la orden y liberan la línea. Volver a aprobar no duplica.
- Cierre: `_plan_json` marca `descontado_en_reserva` y propone cero para
  los insumos que ya salieron al cerrar la atención de la reserva; el
  cajón de avance lo dice en la fila.
- Ficha y asistente: `detalle.py` publica `procesos_practica`; la ficha
  enlaza «Práctica por proceso: …» por cada proceso y el asistente muestra
  la tarjeta «Práctica por proceso» con los enlaces (build
  `20260921-practica-por-proceso-v131`, panel `v45`).

**Catálogo corregido de paso.** Cada equipo se usa donde la planta lo
publica: el envasado de las ocho recetas ocurre en la sala de fermentación
y envasado (donde vive la envasadora), la marmita se publica en la línea,
la hiladora y la mantequillera en la quesería, la cámara de maduración en
la cámara de frío, y el yogur se bate en la incubadora.

**Pruebas.** `webcitt/tests/test_reserva_por_proceso.py`: selección
derivada (áreas, equipos, auxiliares, software, insumos, sesión, días
siguientes, reubicación de un equipo), JSON y página solo con sesión,
ficha y asistente con la ruta y un laboratorio sin ella, solicitud que
guarda proceso y escala, rechazo sin la prensa o con un proceso ajeno,
compuerta documental antes de aprobar, orden con bloqueo al aprobar y sin
duplicado, cierre sin doble descuento, cancelación que libera la línea y
la ruta de investigación sin guía.

## §78 · Seguridad industrial y acceso (paso 3 de la ruta de la planta)

**Qué resuelve.** Una planta de alimentos no deja entrar a cualquiera de
cualquier forma. La unidad declara lo que exige por categoría de persona,
cada persona acumula sus habilitaciones vigentes y cada sesión registra
quién entró, con qué protección y por qué alguien no entró. Un laboratorio
sin requisitos no cambia en nada.

**Modelos (`webcitt/models/seguridad.py`, migración 0176).**
- `RequisitoAcceso`: unidad, código, nombre, tipo (inducción, sanitario,
  documento, protección, restricción), `aplica_a` (categorías: estudiante,
  docente, personal, externo, visitante; vacío es todas), obligatorio,
  momento (al reservar y al ingresar, o solo al ingresar), vigencia en días
  para lo habilitable, `consumible` y `cantidad_por_persona` para la
  protección que la unidad entrega del inventario.
- `HabilitacionAcceso`: persona, requisito habilitable, fecha, vence (se
  calcula con la vigencia si no se indica), origen (sesión de inducción,
  documento, registro de la unidad), la reserva de inducción que la otorgó.
- `RegistroIngreso`: reserva, participante, ingresa o no, motivo, hora,
  protección y restricciones verificadas, habilitaciones vigentes y lo
  pendiente en ese momento; único por participante y sesión.

**Dominio (`webcitt/domains/unidades/seguridad.py`).** La categoría de
una persona sale de su perfil (docente e investigador son «docente»,
administrativo es «personal», egresado y externo son «externo») y el
personal activo de la unidad siempre es «personal». `estado_de_persona`
dice por requisito si está vigente, pendiente o se verifica al ingresar;
`acceso_de_usuario` lo resume para quien solicita; `acceso_de_reserva` lo
hace persona por persona con el ingreso registrado y el aforo del área más
pequeña. Compuertas: `pendientes_al_reservar` avisa (no bloquea) y viaja
en la respuesta de `crear_reserva` como `acceso_pendiente`; `validar_aforo`
detiene la aprobación cuando las personas declaradas superan la capacidad
del área más pequeña, solo en unidades con requisitos obligatorios;
`validar_inicio` exige al menos un ingreso registrado para iniciar;
`registrar_ingresos` deja entrar solo a quien tiene sus habilitaciones al
día y la protección y las restricciones verificadas, y guarda como «no
ingresa» con motivo a quien no; `otorgar_habilitaciones_por_sesion`
habilita a quienes asistieron a una sesión de capacitación con subtipo
inducción al cerrarla. A la inducción se viene sin inducción: no cuenta
como pendiente para entrar.

**Panel.** Módulo `seguridad` en `MODULOS_OPERATIVOS` (coordinación,
responsable técnico y laboratorista lo tienen por defecto). Pestaña
«Seguridad y acceso» (`includes/seguridad.html`) con métricas, requisitos,
habilitaciones y las sesiones aprobadas de la semana; cajones
`requisito_acceso`, `habilitacion_acceso` (persona por usuario, correo o
cédula) e `ingreso` (una fila por persona con lo pendiente a la vista,
`includes/formularios_seguridad.html`). El expediente de la reserva lleva
`acceso` y la pestaña de participantes muestra la tarjeta «Acceso a la
unidad» con el botón «Registrar ingreso» (build del panel v46).

**Solicitante.** La ficha publica «Para ingresar a la unidad»; el
asistente muestra en la confirmación el bloque «Acceso a la unidad» con el
estado de quien solicita (build v132); la práctica por proceso muestra «Tu
acceso a la planta» y suma la protección por persona a los insumos
(`personas` en la selección y en el JSON); el comprobante repite el
estado de cada persona.

**Catálogo.** La planta de lácteos carga ocho requisitos: inducción de
seguridad e inocuidad (180 días), certificado de salud o carné de
manipulador (365 días; el visitante no), cofia y guantes desde el
inventario, mandil y botas que trae cada persona, las restricciones de
ingreso y el acompañamiento del visitante.

**Pruebas.** `webcitt/tests/test_seguridad_acceso.py`: reglamento y
categorías, protección por persona en la práctica por proceso, ficha y
asistente, panel (requisito, habilitación, permisos), aviso y comprobante,
aforo al aprobar, ingreso e inicio, laboratorio sin requisitos, inducción
como sesión.

## §79 · Programación de asignatura (paso 4 de la ruta de la planta)

**Qué resuelve.** El docente programa el período eligiendo su asignatura;
el cronograma de la guía general nace de los temas y cada sesión nace con
su guía prellenada desde el tema y su proceso. Una sesión sin guía
aprobada no se ejecuta. Sirve igual para una planta y un laboratorio.

**Modelos (migración 0177).**
- `Asignatura` (`webcitt/models/asignaturas.py`): unidad, período
  opcional, código único por unidad, nombre, carrera, semestre, docente
  opcional (vacío es cualquiera que la elija), estudiantes.
  `TemaAsignatura`: orden (semana), nombre, `receta` (el proceso),
  `software` (simuladores), ejercicios del aula y resultado de aprendizaje.
- `GuiaActividadReserva.alcance` (sesión o período), `guia_general` (la
  general a la que sirve una guía de sesión) y `sesion` (la planificación a
  la que pertenece). Las restricciones de versión única y vigente única por
  actividad quedan para las guías sin sesión; las guías de sesión tienen las
  suyas por sesión. `guia_vigente_para` ya no devuelve ni la general ni las
  de sesión: ninguna autoriza otra sesión.
- `ProgramacionReserva.asignatura`, `PlanificacionPractica.tema_asignatura`
  (el plan ya tenía un texto `tema`) y
  `ConfiguracionOperativaUnidad.dias_antelacion_guia` (dos días hábiles).

**Flujo (`webcitt/domains/unidades/asignaturas.py`).** `crear_reserva`
acepta `asignatura_id` solo en docencia; con programación semanal y guía
integrada llama a `programar_asignatura`: la guía integrada pasa a
`alcance='periodo'` con `contenido['cronograma']` (sesión, fecha, semana,
tema, proceso, ejercicios, software) y cada sesión recibe `tema_asignatura`
y una guía de sesión en borrador (`-S01`, `-S02`…) que hereda los datos
generales, la seguridad institucional y el manejo de residuos de la
general, toma resultado, objetivos y ejercicios del tema y, si el tema
tiene proceso, el procedimiento, la seguridad y los resultados desde
`guia_integrada_desde_proceso`. Contenido en formato HTML saneado.

**Compuertas.** `estado_documental_reserva` devuelve además `general` y
`lista_para_aprobar`: la guía general aprobada permite aprobar las
sesiones; la guía de cada sesión, aprobada, permite iniciarla y cerrarla.
`operar_ingreso` respeta la misma compuerta. El panel oculta «Aprobar»
por `lista_para_aprobar` y «Iniciar»/«Completar» por `lista`. Aprobar una
guía de sesión no desplaza la vigencia de la general (el reemplazo de
vigente y la versión en trabajo se acotan por sesión).

**Bandeja, aviso y reporte.** `sesiones_sin_guia` lista las sesiones
programadas sin guía aprobada con su margen en días hábiles (pestaña de
prácticas, junto a «Asignaturas y sus temas»). `avisar_guias_de_sesion`
corre dentro de `procesar_recordatorios_reservas` y crea una notificación
`guia_sesion_pendiente` por sesión, una sola vez, cuando faltan a lo sumo
antelación más dos días hábiles. `reporte_asignaturas` (categoría
«Cumplimiento del cronograma por asignatura») clasifica cada sesión:
ejecutada con guía, ejecutada sin cumplir lo previsto, reprogramada, no
ejecutada o pendiente, a partir de la ejecución registrada y el estado de
la reserva.

**Interfaz.** Cajones `asignatura` y `tema_asignatura` (permiso
`practicas`); el asistente ofrece «Asignatura registrada en la unidad»
(`asignaturasDocente`, build v133) y al elegirla llena la asignatura de la
guía; el FT04 muestra la sesión programada y la guía general en los datos
generales, y la sección 12 «Cronograma de sesiones del período» en la
guía general, en pantalla y en PDF. Panel v47.

**Pruebas.** `webcitt/tests/test_programacion_asignatura.py`: sílabo del
cargador y ficha, panel (asignatura, tema, semana repetida, quitar,
permisos), período programado (cronograma, guías por sesión prellenadas,
bandeja, documento y PDF), asignatura ajena o sin docencia, compuertas de
aprobación e inicio, aviso único, cumplimiento del cronograma y reporte.

## §80 · El proceso dentro del asistente (corrección del paso 2)

**Qué corrige.** La página «práctica por proceso» (§77) era un atajo fuera
de la ruta de reservas. Se retiró: la vista, su plantilla, su URL, los
enlaces de la ficha y la tarjeta del asistente. El proceso se elige en la
misma ruta de siempre y todo lo que exige entra por el mismo formulario.

**Dónde vive.**
- Contexto (paso 2, `reserva_equipos.html`, bloque `#procesoReservaCampo`):
  con docencia, investigación, vinculación, capacitación o titulación en
  una unidad con procesos aparece «¿Qué proceso vas a realizar?» (los
  procesos de `procesos_practica`, con corrida base, unidad y rendimiento
  en `data-*`) y «Materia prima que procesarás». En docencia el proceso es
  obligatorio, con la opción explícita «uso de recursos sin un proceso
  definido». El factor viaja en `factor_proceso` y el proceso en
  `receta_id`, como ya esperaba `crear_reserva`.
- Selección (`reservation_wizard.js`, bloque «Práctica por proceso dentro
  del asistente», declarado junto a los catálogos porque la sincronización
  de participantes y el observador de equipos lo consultan desde el
  arranque): `fetchProcessSelection` pide
  `laboratorio/<slug>/procesos/<id>/seleccion.json?factor&personas&guia=1`;
  `applyProcessMode` fuerza el alcance por áreas y marca las áreas del
  proceso; `applyProcessLocks` (al final de `syncEquipmentAvailability`,
  así sobrevive a cada redibujo del catálogo) marca los equipos, el
  software y los insumos con su cantidad, oculta lo ajeno al proceso
  (`rw-process-hidden`, con el botón «Mostrar todos los recursos») y
  bloquea lo obligatorio (`data-process-locked`: un clic no lo desmarca,
  `syncSpaceScope` y `updateConsumableGuidance` lo respetan, y la falta de
  existencia no detiene el paso). La guía del paso 4 toma del proceso el
  procedimiento, la seguridad, los resultados y los objetivos (`guia` del
  JSON, HTML saneado).
- Calendario (`modal_reserva_equipos.js`): con `window.reservaProcesoActivo`
  el almuerzo entra en la jornada y `calendarState.processHours` hace que
  la primera hora marcada tome las horas seguidas que la corrida necesita.
- Confirmación: el resumen lleva «Proceso de la planta».

**Comprobado en el navegador simulado** (`harness_proceso_asistente.js`):
investigación, queso fresco a 200 litros: 5 áreas y 6 equipos marcados y
bloqueados, 9 insumos con cantidad (incluida la protección por persona),
lo ajeno oculto, un clic no desmarca un área bloqueada, la hora 07:00 toma
07:00–14:00 con el almuerzo, y el paso 3 valida.

## §81 · El cronograma por sesión dentro del asistente (bloque B del paso 2)

**Qué resuelve.** Una práctica de una sola sesión va directo con su guía.
Cuando la persona programa varias sesiones (semanal hasta una fecha o todo
el período) el sistema cambia: pide qué práctica hará en cada sesión y con
qué proceso, cada sesión nace con lo que su proceso exige, la guía general
del período lleva el cronograma y cada sesión su guía prellenada. Después,
mientras la sesión sigue pendiente, la persona la completa (práctica,
proceso, materia prima e insumos) desde «Mis sesiones programadas».

**Dónde vive.**
- `reservas/cronograma.py`: `fechas_de_programacion` (las fechas, antes en
  `views._fechas_de_programacion`, que ahora delega); `fechas_programacion_view`
  (`reservas/programacion/fechas.json?unidad&fecha&frecuencia&fin`, lo que
  el asistente consulta para dibujar las filas); `normalizar_cronograma` (una
  fila por fecha: práctica, tema del sílabo, proceso y materia prima; la
  primera fila es la del contexto); `recursos_de_sesion` +
  `aplicar_recursos_a_sesion` (lo que el proceso exige, en la forma en que la
  reserva lo guarda); `completar_sesion` + `completar_sesion_view`
  (`reservas/<id>/sesion/`, solo mientras la sesión está pendiente; después
  el cambio va por «Mis reservas»); `mis_sesiones_view`
  (`laboratorio/<slug>/mis-sesiones/`).
- `views.crear_reserva`: lee `cronograma` (JSON) tras la asignatura; cada
  sesión con proceso propio se valida con sus recursos
  (`_recursos_para_validar`) y nace con ellos en el bucle de clonación;
  `programar_asignatura` recibe las filas. La respuesta trae `sesiones_url`.
- `asignaturas.programar_asignatura(filas=…)`: las filas mandan (práctica,
  tema, proceso de la sesión); sin filas, los temas de la asignatura en su
  orden. `contenido_de_sesion`, `prellenar_guia_de_sesion` (una guía en
  borrador se vuelve a prellenar al completar la sesión) y
  `actualizar_fila_cronograma`. Bandejas, aviso y reporte ya no exigen
  asignatura: cuentan las sesiones cuya guía nació de una guía general
  (`SESIONES_CON_GUIA`); `guia_general_de` tampoco la exige.
- Asistente (`reservation_wizard.js`, «El cronograma por sesión»: estado
  junto al proceso, funciones antes de `validateStep`): `refreshSchedulePlan`
  (al cambiar frecuencia, fecha o fin de la serie) pide las fechas y
  `renderScheduleRows` dibuja una fila por sesión (la primera refleja el
  proceso del contexto; las demás eligen proceso y materia prima, con los
  temas del sílabo como sugerencias); `describeScheduleRow` consulta la
  selección del proceso para decir cuántas horas necesita la corrida;
  `validateSchedulePlan` exige la práctica en docencia y la materia prima
  cuando hay proceso; el JSON viaja en `cronograma`. Plantilla:
  `#cronogramaReserva` tras la agenda. Build `20260923-cronograma-por-sesion-v135`.
- Comprobante (`sesion_programada`, completo y embebido), ficha («Mis
  sesiones programadas» cuando la persona programó aquí),
  `completar_sesion.html` y `mis_sesiones.html`.

## §82 · El aula en el visor público: sistemas de producción, fichas y simuladores (bloque C)

**Qué resuelve.** Las funciones de la planta vivían solo en «Gestionar
laboratorio». Ahora el módulo público «Procesos y protocolos» de la ficha
(o el módulo de reservas si la unidad no lo tiene) publica los sistemas de
producción por carpetas: la línea de producción (categoría, `Producto.linea`,
migración 0178) agrupa los procesos (subcategoría) y cada proceso ofrece sus
temáticas: la ficha (diagramas, etapas, cursograma, balance y cronograma),
los simuladores (balance de materia y energía, balance de línea,
requerimiento de materiales) y los protocolos de control. Un simulador toma
los datos de una reserva o de una programación («si pidió 100 litros, simula
con 100 litros») o corre libre.

**Dónde vive.**
- `domains/unidades/aula.py`: `procesos_publicos` / `lineas_de_procesos` /
  `contexto_aula` (lo que la ficha dibuja; `guias_modulo_clave` decide dónde
  van las guías publicadas, que ahora también aparecen en las plantas);
  `sesion_de_referencia` (`?reserva=` o `?programacion=`, solo si quien entra
  es titular, participante u operador de prácticas o producción);
  `enlaces_del_aula(reserva)` (los enlaces con datos cargados que usan el
  comprobante, la sesión y «Mis sesiones programadas»);
  `balance_de_energia` (masa por densidad, calor útil y suministrado con
  eficiencia, kWh, vapor equivalente, frío por retirar, minutos a una
  potencia), `balance_de_linea` (takt, cuello de botella, capacidad,
  estaciones por agrupación consecutiva, eficiencia y retraso de balance),
  `requerimiento_de_materiales` (bruto por insumo frente a inventario y
  stock de seguridad, faltantes y salidas), `protocolos_de_control` (puntos
  críticos con parámetro y límite). Vistas: `ficha_proceso_publica_view`
  (reutiliza `gestion/ficha_proceso.html` con `publica=True`),
  `simulador_balance_view`, `simulador_linea_view`,
  `simulador_materiales_view`, `protocolos_control_view`; plantillas en
  `portal/pages/unidades/aula/` (páginas HTML completas que el visor carga
  en su iframe y que también se abren solas desde el comprobante).
- Ficha (`detalle_unidad.html`): carpetas «Sistemas de producción» (grupos
  por línea, botones `ficha-proceso-<id>`) y «Simuladores y protocolos»
  (`simulador-balance|linea|materiales`, `protocolos-control`);
  `pestanas_modulos.js` admite `?recurso=<data-id>` para abrir cualquier
  botón por enlace directo.
- Cargador de lácteos: líneas de los productos; `LAC-SW-BALANCE`,
  `LAC-SW-LINEA` y `LAC-SW-MRP` como software propio de acceso remoto (50
  licencias) ligado a yogur y manjar (balance) y queso fresco (línea), y al
  tema 10 del sílabo. Panel: el producto tiene «Línea de producción».

**Corrección (13 de septiembre, tras probar en el navegador).** El visor
carga las páginas en un iframe y el proyecto responde `X-Frame-Options:
DENY`: Chrome bloqueaba la ficha (jsdom no lo detecta porque no carga los
iframes). Las vistas del aula llevan `@xframe_options_sameorigin` y la
prueba comprueba la cabecera. Además cada pestaña recibe sus carpetas
(`carpetas_del_aula`): «Procesos y protocolos» (sistemas de producción y
simuladores del proceso), «Producción y lotes» («Lo que produce la planta»:
productos por línea, corridas y lotes disponibles; requerimiento de
materiales), «Calidad e inocuidad» (protocolos de control; control de
calidad de los lotes, requisitos de ingreso y normas de seguridad) y
«Equipos e infraestructura» («Áreas y equipos», cada área con sus equipos y
auxiliares). Si la unidad no tiene alguno de esos módulos, la carpeta va al
módulo de procesos; el aviso «No hay carpetas» solo sale en las pestañas que
de verdad quedan vacías.

## §83 · Visitas: un papel en una solicitud, no un cuarto tipo de usuario (paso 5)

**Qué resuelve.** Quien organiza la visita tiene cuenta; el grupo, no. La
visita es una solicitud con su propio formulario apoyada en una reserva de
las áreas del recorrido, así que la agenda, el aforo, la aprobación, el
comprobante, «Mis reservas» y los avisos son los de siempre.

**Dónde vive.**
- `models/visitas.py` (migración 0179): `SolicitudVisita` (unidad, reserva
  1:1, responsable, institución, propósito académico/institucional/comercial,
  personas, edades, recorrido M2M a `EspacioReservable`, guía, guías
  necesarios, requisitos aceptados, costo, observaciones) y `AsistenteVisita`
  (nombre, documento, asistió, ingreso). `EspacioReservable.visitable`;
  `ConfiguracionOperativaUnidad.acepta_visitas`, `personas_por_guia`,
  `visitas_texto`.
- `domains/unidades/visitas.py`: `oferta_de_visitas` (áreas visitables, aforo
  del área más pequeña, personas por guía, requisitos de la categoría
  «visitante», servicio «visita técnica» y su costo por guía: tarifa base más
  mano de obra); `crear_visita` (valida institución, personas, fecha con un
  día de anticipación, horas, recorrido dentro de lo visitable, aforo del
  área más pequeña, requisitos aceptados, lista no mayor que el grupo,
  horario operativo y conflictos de agenda; crea la `Reserva` de recursos con
  las áreas, propósito vinculación, `numero_participantes`, costo y desglose;
  la protección de visitante sale de `proteccion_por_persona`; revisión
  inicial y aviso al responsable); `registrar_asistencia` (quién ingresa,
  quién se suma, observaciones); `asistencia_registrada` (con ella
  `seguridad.validar_inicio` deja iniciar la visita aunque el grupo no tenga
  cuenta); panel: `contexto_visitas`/`seccion_visitas` (pestaña «Visitas»
  para quien opera reservas), operadores `visita` (guía y observaciones,
  permiso reservas) y `oferta_visitas` (permiso configuración: áreas
  visitables, personas por guía, texto, publicar). Vistas:
  `oferta_visitas_view` (`laboratorio/<slug>/visitas/`, dentro del visor),
  `solicitar_visita_view` (`…/visitas/solicitar/`, exige cuenta),
  `asistencia_visita_view` (`gestion/unidades/<slug>/visitas/<id>/asistencia/`,
  lista imprimible para la unidad).
- Ficha: botón «Visitas a la unidad» en la carpeta de reservas cuando la
  oferta está publicada; comprobante con el bloque de la visita (grupo,
  recorrido, guía, lista). Cargador de lácteos: recepción, línea térmica y
  sala de capacitación visitables; oferta publicada con quince personas por
  guía.

## §84 · Servicios y maquila por proceso (paso 6)

**Qué resuelve.** Las plantas ofrecen servicios como el FabLab, pero lo que
entregan es producto elaborado según un proceso. El servicio se liga a su
proceso y admite una escala; la cotización sale de la lista de materiales
escalada; la materia prima puede ser del cliente; al aprobar nace la orden;
el cliente ve el avance; se entrega con acta y certificado.

**Dónde vive.**
- Modelos (migración 0180): `FablabService.receta` y
  `materia_prima_cliente`; `Reserva.materia_prima_cliente`;
  `LoteConsumible.material_cliente` y `reserva`.
- `domains/unidades/maquila.py`: `sincronizar_insumos_del_proceso(servicio)`
  (los `FablabServiceConsumible` del servicio son los insumos del proceso por
  corrida base; la materia prima base queda opcional cuando el cliente puede
  traerla); `servicio_de_proceso` y `trae_materia_prima_el_cliente` (los usa
  `crear_reserva` en la rama de servicio: `receta = servicio.receta`,
  `factor_proceso = piezas`, y el cliente trae la materia prima cuando no
  marcó la base entre los materiales); `expediente_maquila(reserva)` (orden,
  lotes, material del cliente, entregas, etapa y pasos);
  `recibir_material_cliente` (lote `en_uso` a costo cero + `EntradaInventario`
  de recepción con `responsable_costo='usuario'`, de modo que el consumo de la
  corrida lo devuelve a cero); `entregar_lote` (movimiento `venta` a precio
  cero del lote aprobado y disponible: sin ingreso financiero porque el
  encargo se cobra como servicio); vistas `maquila_view`
  (`gestion/unidades/<slug>/maquila/<reserva>/`, permiso producción) y
  `acta_entrega_view` (`…/acta/`, planta y cliente).
- `gestion_produccion.orden_de_practica`: para un servicio la orden nace con
  origen «maquila» y toma los equipos del proceso cuando la reserva no
  reservó máquinas. La pestaña de producción enlaza el expediente del encargo
  en cada orden de maquila.
- Ficha: la tarjeta del servicio dice su proceso y qué es un lote; el
  comprobante (y «Mis reservas», que lo embebe) muestra «Tu encargo» con los
  pasos, la materia prima recibida, los lotes con su calidad y el acta.
- Cargador de lácteos: «Elaboración de yogur por maquila» ligado a la receta
  de yogur con materia prima del cliente.

## 85. Calidad e inocuidad: planes, controles, no conformidades y HACCP

El paso 7 de la ruta de la planta. Lo que la planta promete controlar deja de
ser un texto del protocolo y pasa a ser un límite que un control cumple o no.

- `webcitt/models/calidad.py`: `PlanCalidad` (unidad, código, nombre, momento
  `recepcion|proceso|liberacion`, producto o consumible, activo);
  `ParametroCalidad` (plan, orden, nombre, tipo `numerico|cualitativo`, unidad
  de medida, mínimo, máximo, valor esperado, método, etapa de la receta que
  vigila, crítico, activo) con `limite_texto` y `evaluar()`; `ControlCalidad`
  (unidad, plan, lote de producto o de consumible u orden, fecha, quien
  registró, resultado) con sus `MedicionCalidad`; `NoConformidad` (gravedad
  `menor|mayor|critica`, estado `abierta|en_tratamiento|cerrada`, disposición
  `pendiente|reproceso|liberacion_condicionada|rechazo|devolucion`, causa,
  código `NC-0001` autogenerado) y `AccionCorrectiva` (responsable, fecha de
  compromiso, estado, verificación, `vencida`). Migración 0181.
- `webcitt/domains/unidades/calidad.py`: `registrar_control` mide el plan,
  guarda las mediciones y decide: conforme aprueba el lote de producto
  (`LoteProducto.aprobar_calidad`), no conforme abre la no conformidad
  (crítica si falló un parámetro crítico). `decidir_no_conformidad` aplica la
  disposición: el rechazo llama a `rechazar_calidad` (baja del lote), el
  rechazo o la devolución retiran el lote de materia prima, la liberación
  condicionada aprueba el lote. `plan_haccp(unidad, procesos)` cruza las
  etapas con `punto_critico` de cada receta con los parámetros ligados a ellas.
  `indicadores_calidad` alimenta la pestaña; `calidad_publicada` la ficha.
- Panel: pestaña «Calidad e inocuidad» (permiso producción, solo unidades con
  `registra_produccion`), junto a producción. Lista los lotes en cuarentena y
  la materia prima del cliente sin controlar, con «Controlar» hacia
  `gestion/unidades/<slug>/calidad/control/?lote_producto=` (o
  `?lote_consumible=`, `?orden=`, `?plan=`); los planes con sus parámetros; las
  no conformidades con su disposición y sus acciones; los últimos controles con
  sus mediciones. Operaciones `plan_calidad`, `parametro_calidad`,
  `no_conformidad` y `accion_correctiva`.
- Público: `laboratorio/<slug>/plan-haccp/` (embebible, `xframe_options_sameorigin`)
  es un botón más de la carpeta «Calidad e inocuidad» del aula, y la página de
  calidad de la ficha publica qué mide cada plan y con qué límite.
- Cargador: la planta de lácteos trae siete planes (recepción de leche cruda,
  control en proceso de queso, yogur y leche, y liberación de los tres) con
  veintiocho parámetros reales; los de proceso quedan ligados a las etapas
  críticas de sus recetas, de modo que el plan HACCP se arma solo.

## 86. Planificación: plan maestro, explosión de materiales y pedidos

El paso 8 de la ruta de la planta. La planta deja de reaccionar a lo que le
piden y programa su período: qué producir, qué pedir y cuándo.

- `webcitt/models/planificacion.py`: `PlanMaestro` (unidad, código `PM016-…`,
  nombre, desde, hasta, estado `borrador|firme|cerrado`) y sus
  `LineaPlanMaestro` (receta, día, escala en corridas base, producto y cantidad
  derivados de la receta, origen `demanda|maquila|docencia|stock`, la reserva
  que atiende y la orden que generó); `PedidoAbastecimiento` (código `PA016-…`,
  insumo, proveedor, cantidad, costo, fecha de pedido y de entrega, estado
  `borrador|enviado|confirmado|recibido|cancelado`; enviado o confirmado cuenta
  como existencia en camino) con sus `EntregaPedido` (día, cantidad, recibida,
  lote y entrada de inventario). Migración 0182.
- `webcitt/domains/unidades/planificacion.py`: `demanda_comprometida` y
  `proponer_lineas` llevan al plan los encargos aceptados y las prácticas
  programadas con proceso que todavía no estaban en él;
  `explosion_de_materiales(plan)` camina el calendario por insumo (saldo de
  bodega + lo que viene en camino − lo que pide cada día, sin bajar del stock
  de seguridad) y devuelve lo que falta y la fecha límite de pedido (necesidad
  menos `plazo_reposicion_dias`); `carga_por_dia(plan)` compara las horas de
  proceso con las horas de jornada (`HorarioOperacionUnidad`) y enciende el
  semáforo `holgado|ajustado|excedido`; `generar_ordenes(plan, usuario)`
  convierte cada línea firme en `OrdenProduccion` con su línea bloqueada (la
  reserva que ya trajo la suya se enlaza en vez de duplicarla);
  `crear_pedidos_sugeridos(plan, usuario)` crea un pedido por insumo que falta
  con una entrega por cada día que hace falta; `recibir_entrega` crea el
  `LoteConsumible` y la `EntradaInventario` de recepción.
- Panel: pestaña «Planificación» (permiso producción, solo unidades con
  `registra_produccion`), delante de producción. Las cuatro acciones del plan
  viajan en `accion_plan` porque el cajón reserva `accion` para guardar.
  Operaciones `plan_maestro`, `linea_plan`, `pedido_abastecimiento` y
  `entrega_pedido`. La hoja imprimible está en
  `gestion/unidades/<slug>/planificacion/<plan>/`.
- Cargador: los insumos aceptan `plazo_dias` y `proveedor`; la planta de
  lácteos declara el plazo real de cada materia prima, con la leche cruda a un
  día para que su pedido salga en entregas diarias.

## 87. Aula calificable: un escenario por estudiante, corregido por el motor

Cierra el paso 9 de la ruta. Los simuladores dejan de ser una demostración y
pasan a ser el instrumento de evaluación de la asignatura.

- `webcitt/models/aula.py`: `EjercicioAula` (unidad, código `EJ016-…`, nombre,
  simulador `balance|linea|materiales`, receta, la sesión cuyos participantes
  lo reciben, tema de la asignatura, consigna, `factor_base` y `paso` que dan
  la escala de cada estudiante, `parametros` del simulador iguales para todos,
  `tolerancia_pct`, puntaje, estado `borrador|abierto|cerrado`, fecha límite) e
  `IntentoEjercicio` (estudiante, su factor, respuestas, resultados, puntaje,
  estado, entregado y calificado, comentario del docente). Migración 0183.
- `webcitt/domains/unidades/ejercicios.py`: `preguntas_de(ejercicio, factor)`
  arma cuatro preguntas por simulador y calcula su respuesta con los mismos
  motores que la planta usa (`balance_de_masa`, `balance_de_energia`,
  `balance_de_linea`, `requerimiento_de_materiales`); `asignar_intentos`
  reparte la escala en el orden de la lista de participantes;
  `url_del_simulador` abre el simulador con los datos del estudiante;
  `calificar` compara cada respuesta con el valor del motor dentro de la
  tolerancia y reparte el puntaje entre las preguntas. El estudiante no ve el
  valor esperado hasta entregar.
- Rutas: `laboratorio/<slug>/mis-ejercicios/` (lo que le asignaron),
  `laboratorio/<slug>/ejercicio/<intento>/` (su ejercicio: consigna, su escala,
  el enlace al simulador y el formulario de respuestas; después, su nota y en
  qué se apartó) y `gestion/unidades/<slug>/ejercicios/<ejercicio>/` (la hoja
  del docente). Las dos primeras son embebibles, como el resto del aula, y
  «Mis ejercicios» es un botón más de la carpeta de simuladores de la ficha.
- Panel: pestaña «Aula y ejercicios» (permiso prácticas, solo unidades con
  procesos activos), junto a prácticas. Operaciones `ejercicio_aula` (con la
  acción `accion_ejercicio=asignar`) e `intento_ejercicio` para ajustar la nota
  y comentar.

## 88. Almacén: cobertura del plan, vencimientos y conteo cíclico

El paso 10 de la ruta. El kardex ya decía cuánto hay; el almacén dice si
alcanza para lo que viene, qué se va a echar a perder y qué hay de verdad en
el estante.

- `webcitt/models/almacen.py`: `ConteoInventario` (unidad, código `CI016-…`,
  nombre, alcance `todo|bodega|clasificacion` con su referencia, fecha,
  responsable, estado `abierto|cerrado|anulado`) y `LineaConteo` (lote,
  insumo, `cantidad_sistema` congelada al abrir, `cantidad_contada`, el ajuste
  que generó). Migración 0184.
- `webcitt/domains/unidades/almacen.py`: `cobertura_del_plan(unidad)` corre la
  explosión de materiales del plan vigente y compara con las existencias;
  `lotes_por_vencer` y `orden_de_salida` implementan la salida por vencimiento
  (primero el que antes vence; entre los que no vencen, el que antes entró);
  `dar_de_baja_por_caducidad` retira el saldo entero del lote como exige
  `EntradaInventario`; `abrir_conteo`, `registrar_linea` y `cerrar_conteo`
  hacen el conteo cíclico, y el cierre crea un `EntradaInventario` de ajuste
  por cada diferencia (si aparece más de lo que el lote decía haber recibido,
  el conteo manda y se sube su `cantidad_inicial`); `material_del_cliente`
  separa lo que está en bodega pero no es de la unidad.
- Panel: modo «Almacén y conteo» dentro de la pestaña de recursos, junto a
  «Insumos y materiales» (permiso inventario y `configuracion.consumibles`).
  Operaciones `conteo_inventario` (con `accion_conteo=cerrar`), `linea_conteo`
  y `baja_lote`; los formularios vuelven al modo con
  `data-reload-resources-mode`.

## 89. Trazabilidad de un lote y reporte institucional

El paso 11 de la ruta. La plataforma ya tenía los datos; faltaba poder
mostrarlos como una cadena y como un consolidado.

- `webcitt/domains/unidades/trazabilidad.py`: `trazabilidad_de_lote(lote)`
  arma la cadena de un `LoteProducto`: la orden con su receta, su línea y sus
  equipos; la reserva que la originó; los lotes de insumo consumidos (se
  encuentran por `clave_idempotencia` `orden-produccion-<orden>-…`) con la
  `EntregaPedido` y el `PedidoAbastecimiento` por los que llegaron y su control
  de recepción; los puntos críticos del proceso; los `ControlCalidad` con sus
  mediciones y las `NoConformidad`; y los `MovimientoProducto` de salida. Vista
  `trazabilidad_lote_view` (permiso producción), imprimible, enlazada desde
  cada lote de la pestaña de producción.
- `consolidado_institucional(usuario, desde, hasta)` recorre
  `unidades_gestionables` y devuelve una fila por unidad (solicitudes,
  atendidas, personas, corridas, lotes, liberados, rechazados, controles,
  conformes, no conformidades abiertas, ejercicios, entregas e ingresos) más el
  total. Vista `reporte_institucional_view` en `gestion/reporte-institucional/`,
  enlazada desde la pestaña de reportes de cualquier unidad.
- `gestion_reportes.py` suma dos categorías al reporte de unidad: «calidad»
  (controles con sus mediciones, filtrable por resultado) y «aula» (intentos
  con su escala y su nota, filtrable por estado). La de calidad solo aparece en
  unidades que producen.

## 90. Las otras cuatro plantas piloto

El paso 12 cierra la ruta. Cárnicos, panificación, hortofrutícola y almidones
se cargan con la misma definición que lácteos: cambian los procesos, no el
modelo.

- `webcitt/management/plantas/` es un paquete con un archivo por planta
  (`carnicos.py`, `panificacion.py`, `hortofruticola.py`, `almidones.py`), cada
  uno con una constante en mayúsculas con la definición completa, y un
  `__init__.py` que las reúne en `PLANTAS`. El cargador institucional las suma
  a `LABORATORIOS` con `**PLANTAS`, de modo que
  `cargar_laboratorios_institucionales --laboratorio carnicos` funciona igual
  que el de lácteos, y `--laboratorio todos` carga las ocho unidades.
- Cada planta trae equipos con sus unidades, áreas (con su línea de proceso y
  las visitables), software propio, insumos con `plazo_dias` y `proveedor`,
  servicios (visita guiada a tarifa cero, maquila ligada a una de sus recetas
  con materia prima del cliente, y análisis), productos con su línea, tres
  procesos con etapas, puntos críticos, insumos y salidas, planes de calidad de
  recepción, proceso y liberación, requisitos de acceso incluida la protección
  por persona, oferta de visitas, una asignatura con sus temas, dos
  responsables y dos cuentas operativas.
- `webcitt/tests/test_plantas_piloto.py` corre sobre las cuatro: catálogo
  mínimo, cuentas con permiso de producción, cada proceso derivando su
  selección sin faltantes, planes de calidad con límites reales, visita guiada
  con sus requisitos, ficha pública con sus procesos y carga idempotente.
  `LasDefinicionesNoSePisanTests`, en el mismo archivo, revisa sin tocar la
  base que ningún código pertenezca a dos unidades y que dos plantas no llamen
  igual a categorías de equipo distintas: `CategoriaEquipo.nombre` es único en
  toda la plataforma y el cargador busca por código, sin filtrar por unidad.

## 91. La portada de cada pestaña y la documentación de cada proceso

Dos cosas que la ficha pública hacía mal y una que le faltaba.

- **El visor arrastraba el documento de la pestaña anterior.**
  `ModuloTabs.handleTabClick` cambiaba las carpetas y el título del módulo pero
  no tocaba `#dynamic-content`: quien abría la ficha de un proceso y pasaba a
  «Calidad e inocuidad» seguía viéndola, con su nombre en el encabezado.
  Reproducido con `harness_arrastre.js` antes de tocar nada. Ahora cada
  pestaña tiene su **portada** (`webcitt/domains/unidades/portadas.py`), que el
  visor muestra al cambiar de sección: qué es la sección, qué contiene de
  verdad (sale de las carpetas reales del módulo, no de un texto fijo), de
  dónde salen sus datos y cómo se lee. Van como `<template>` en la ficha, así
  que no cuestan una petición. El encabezado del visor alterna entre «Archivo
  activo» y «Sección» (`#viewer-eyebrow`).
- **El documento repetía el título dentro del visor.** El marco ya dice de qué
  documento se trata y de qué unidad es. `portal/components/marco_incrustado.html`
  marca `<html class="esta-incrustado">` cuando la página va dentro de un
  iframe, y `reporte_gestion.css` esconde el logo, el `h1` y el nombre de la
  unidad, conservando los datos de cabecera. Al imprimir vuelve entero, porque
  ahí sí encabeza la hoja.
- **La documentación del proceso** (`webcitt/domains/unidades/documentacion.py`)
  es la pestaña teórica que faltaba: la ficha dice *qué* hace la planta y la
  documentación dice *por qué*. Un glosario de 18 operaciones unitarias
  (tratamiento térmico, fermentación, separación, reducción de tamaño,
  concentración, secado, conformado…) clasifica cada etapa por su nombre —el
  tipo manda solo en el transporte, porque mover no transforma— y de ahí salen
  el fenómeno, la variable que la gobierna, qué pasa fuera de rango y cómo se
  mide. `flujo_por_etapa` arma el diagrama de entradas y salidas: los insumos
  entrando por la izquierda, el bloque de la etapa con el icono de su operación
  en el centro, y las salidas declaradas y las mermas del balance por la
  derecha. Clasifica las 207 etapas de las quince recetas de las cinco plantas
  sin dejar ninguna en la categoría genérica.
- De paso, `datos_de_receta` normaliza `cantidad_base`, `rendimiento_esperado`
  y `factor`: un `Decimal('60.000')` sin normalizar se leía como sesenta mil en
  la ficha.

## 92. El listado de reservas se descarga como documento, no como fotografía

El botón «Descargar» del listado del admin llamaba a `descargarPantallaPDF()`:
html2canvas rasterizaba `document.documentElement` entero —barra lateral, menús
y filtros incluidos—, lo convertía en PNG y jsPDF pegaba esa imagen en un A4. El
resultado salía borroso, cortado a la mitad cuando la tabla era larga, sin poder
buscar ni copiar un código de reserva, y el logo era parte de la foto.

Ahora `reporte_listado_reservas` (en `gestion_reportes.py`) arma con el listado
el mismo diccionario que ya consumen la vista HTML y el PDF institucional de los
laboratorios, así que el documento sale por la maquinaria que ya funcionaba: la
cabecera con el logo, los criterios aplicados, las cuatro tarjetas y la tabla con
sus filas. Las filas son las del `ChangeList`, no una consulta paralela: el
reporte lee `listado.queryset` y `listado.filter_specs`, de modo que lo que
muestra la pantalla y lo que dice la cabecera del documento no pueden discrepar.

La ruta `admin:reservas-reporte-listado` responde dos cosas con los mismos datos:
sin parámetros, **la vista previa** —el documento en pantalla, con su botón de
descarga—; con `formato=pdf`, el archivo. Primero se ve cómo queda, después se
baja. `report['unit'].nombre` pasó a ser `report['scope_label']` porque este
reporte cruza unidades y no tiene una sola; el alcance lo calcula de la selección.

Con el script se fueron también el aviso flotante `.upec-admin-toast` y sus dos
animaciones, que no tenían otro llamador.

## 93. El escenario del aula: mover cada dato y guardar lo simulado

Los simuladores solo dejaban cambiar la escala y las temperaturas. Todo lo demás
—el rendimiento de cada etapa, cuánto entra de cada insumo, cuánto se declara de
cada salida— venía fijo de la receta, así que el estudiante no podía preguntarse
«¿y si el desuerado pierde un 20 % más?».

- **El escenario** (`webcitt/domains/unidades/escenarios.py`) toma la estructura
  plana de `datos_de_receta` y le aplica lo que el estudiante escribió, sin tocar
  la base. Lo que sigue —el balance de masa, el flujo de entradas y salidas, las
  mermas— corre sobre esa estructura, así que el escenario pasa por el mismo
  motor que la corrida real: si el balance cambia, cambia porque cambiaron los
  datos, no porque haya un segundo cálculo para el aula. Un escenario guarda solo
  lo que se movió; un rendimiento que sigue siendo el de la receta no se guarda,
  y volver a la receta es borrar el ajuste.
- **El simulador de balance** muestra ahora el diagrama de entradas y salidas
  etapa por etapa (el mismo de la documentación, con el icono de cada operación
  unitaria), la tabla de todo lo que entra, la de todo lo que sale con sus
  mermas, y una tabla de «lo que moviste» que compara tu escenario con la receta.
- **Las simulaciones se guardan** (`SimulacionGuardada`, migración 0185, y
  `webcitt/domains/unidades/simulaciones.py`). Lo que se guarda son las variables
  con que se corrió, no los resultados: al abrirla se vuelve a calcular con el
  proceso como está hoy, de modo que una simulación de marzo abierta en junio
  muestra la receta vigente y no una foto vieja. El resumen sí se guarda aparte,
  y solo para reconocerla en la lista sin recalcular quince simulaciones para
  pintar una tabla. Desde «Mis simulaciones» se retoman, se guardan aparte como
  variante, se ven o se borran; solo las ve y las borra quien las guardó.
- **El documento se ve antes de bajarse.** Cada simulador tiene el suyo: el
  balance descarga sus mermas y su flujo; el balance de línea, sus estaciones y
  su takt; el requerimiento, lo que falta comprar contra las existencias de hoy.
  Los tres salen por el presentador institucional, así que la vista previa y el
  PDF son el mismo documento. Para que quepan sus tres o cuatro tablas, un
  reporte puede traer `dataset['tablas']`, que la vista HTML y el PDF pintan
  igual, y cada tarjeta puede decir su propio pie en vez de repetir el título.
- **Los motores salieron de las vistas** a `webcitt/domains/unidades/motores.py`:
  balance de energía, balance de línea y requerimiento de materiales trabajan
  sobre la estructura plana y no saben de peticiones. El documento de una
  simulación los necesita y no podía importar `aula.py` sin un ciclo.

## 94. El balance de materia de toda la corrida, y las recetas que no cuadran

Al diagrama por etapa le faltaba el de arriba: la corrida entera en un bloque,
con todo lo que entra a la izquierda, el proceso en el centro y todo lo que sale
a la derecha. Es el que responde de un vistazo qué desperdicia una corrida, y
está en la documentación del proceso y en el simulador de balance.

`balance_general` no suma sus totales aparte: los toma del balance por etapa, que
ya resolvió las conversiones y sabe qué salida pertenece al flujo. Un insumo se
muestra en su propia unidad —diez mililitros de cuajo son diez mililitros— pero
al total entra por su masa. Tres cosas quedan fuera del flujo y se dicen aparte
en vez de disimularse: la materia prima ya contada como entrada (que encabeza el
diagrama con su nombre real, no como «materia prima» genérica), los auxiliares
que se consumen sin quedar en el producto, y las salidas declaradas en etapas que
no pierden masa, como el agua de lavado de la línea.

**Lo que destapó.** De las veinte recetas cargadas, catorce cuadran al milésimo
y seis no: `HOR-REC-MERMELADA-60`, `HOR-REC-PULPA-MORA-100`,
`HOR-REC-UVILLA-SECA-24`, `ALM-REC-PREGEL-400`, `ALM-REC-ALMIDON-500` y
`ALM-REC-GLUCOSA-200`. La causa es siempre la misma: una etapa declara más
salida de la que pierde. En almidón, «Lavado del almidón» declara 2500 litros de
agua de proceso con un rendimiento del 98 %: el agua es externa al flujo, pero la
etapa sí pierde masa, así que la regla que aparta el agua de lavado (la que sale
de etapas que no pierden nada) no la alcanza. En hortofrutícola, el afrecho y el
bagazo declarados superan lo que la etapa pierde según su rendimiento.

El diagrama no lo disimula: marca el descuadre, lo cuantifica y nombra la etapa
culpable para que la planta corrija la receta. Falta decidir si esas seis se
corrigen ajustando el rendimiento declarado o si el modelo necesita una marca de
«salida externa al flujo» en `SalidaReceta`, que es la solución de fondo para el
agua de proceso.

## 95. Cada página del aula se ve y se baja; el visor deja de repetirse

Tres cosas que se veían mal en la ficha pública.

- **La barra repetía la navegación dentro del visor.** Una página abierta en el
  visor traía su propia fila de simuladores y su «Volver a la unidad», cuando la
  lista de secciones y de simuladores ya está a la derecha. Los enlaces de
  navegación llevan ahora la clase `es-navegacion` y `reporte_gestion.css` los
  esconde bajo `.esta-incrustado`: dentro del visor queda solo lo que no está en
  ningún otro lado, que son las acciones del documento. Abierta sola, la página
  conserva su barra entera.
- **«Lo que produce» colgaba del panel lateral**, donde acompañaba por igual a
  todas las secciones. Pasó a la portada de «Producción y lotes», que es la
  sección que habla de eso, con su presentación y su precio. `portadas_de`
  recibe el catálogo y lo cuelga del módulo de producción; si la unidad no tiene
  esa pestaña o no publica productos, el bloque no aparece.
- **Descargar seguía siendo el «Imprimir» del navegador.** Ese botón escribe la
  dirección, la fecha y el número de página en los bordes, corta las tablas
  donde caiga y no sabe nada del formato institucional: una fotografía de la
  pantalla con otro nombre. Ahora cada página del aula declara su documento
  (`documentos_aula.py`) y lo arma el mismo presentador que ya hacía bien los
  reportes de laboratorio. Once documentos: ficha, documentación, los tres
  simuladores, protocolos, producción, calidad, áreas, mis ejercicios y mis
  simulaciones.

**Cómo se ve antes de bajarse.** `formato=pdf` devuelve el archivo en el visor
del navegador —`inline`, para revisarlo— y `formato=pdf&descargar=1` lo baja.
Es el mismo archivo con un parámetro de diferencia, así que lo revisado es
exactamente lo descargado. Los enlaces conservan los filtros que tenga puesta la
página, de modo que un balance con datos movidos se baja con esos datos.

`documentos.py` guarda la forma común (`documento`, `tabla`, `formato_pedido`,
`respuesta_pdf`, `enlaces_de_documento`) y `documentos_aula.py` un constructor
por página, que recibe el contexto ya armado por la vista y no vuelve a
consultar nada: si una cifra cambia en la pantalla cambia en el PDF, porque
salen del mismo cálculo. La cabecera del PDF deja de anunciar un período cuando
el documento no cubre ninguno: una ficha de proceso no va «del 13/09 al 13/09».

Se comprobó construyendo los once documentos de las veintiuna unidades
cargadas. Dos errores que solo aparecen así: el cursograma devuelve
`tiempo_texto`, no `minutos`; y `ParametroCalidad` guarda `unidad_medida`,
`minimo` y `maximo`, no `unidad`, `valor_minimo` ni `valor_maximo`.

## 96. Cada salida declara si pertenece al flujo del producto

El usuario eligió añadir a `SalidaReceta` la marca **Salida externa al flujo**,
sin ajustar por nuestra cuenta cantidades ni rendimientos. También autorizó
PDF propios que respeten la maqueta oficial para los documentos pendientes;
ese trabajo corresponde al bloque siguiente.

- `externa_al_flujo` (migración 0186) es falsa por defecto. El panel de recetas
  la guarda, la recupera al editar y permite retirarla; el inline del admin
  muestra el mismo campo. `salidas_para` y `datos_de_receta` transmiten el rol
  al motor común, al escenario, al procedimiento de la guía y a los documentos.
- El balance deja de inferir que toda salida de una etapa con rendimiento
  del 100 % es externa. Clasifica cada salida: una etapa puede perder masa,
  declarar un subproducto y descargar agua auxiliar a la vez. El agua no
  consume la merma ni oculta un exceso interno. Las cantidades de salida en
  gramos o mililitros se convierten antes de compararlas con la masa.
- La migración marca las 17 salidas de agua de lavado/proceso identificadas
  por sus códigos del catálogo. El cargador declara expresamente ese mismo
  rol. No se marca como externo el bagazo, el afrecho ni la merma de harina.
- Se auditó cada una de las 20 recetas activas en la base de desarrollo.
  Quedan 11 balances consistentes y 9 con datos pendientes: hortofrutícola
  mantiene 3.358 kg (mermelada), 4.929 kg (pulpa) y 0.08 kg (uvilla);
  almidones queda en 16.175 kg (almidón), 35.112 kg (pregel) y 73.09 kg
  (glucosa), todos en tamizado. Al apartar correctamente el agua también
  se reconoce la merma propia de su etapa, antes absorbida por esa salida.
  Panificación ahora muestra 1.5 kg (molde), 1.2 kg (masa madre) y 1.2 kg
  (papa): eran salidas internas en etapas al 100 %, antes ocultadas por la
  inferencia automática. Estos datos requieren revisión de las recetas;
  no se han alterado para hacer cuadrar el diagrama.
- Validación: cinco pruebas puras cubren salida mixta, exceso interno,
  rendimiento del 100 %, unidades y escenarios; una prueba del panel cubre
  guardar, recuperar y retirar la marca. Migración aplicada, `check`,
  `makemigrations --check`, ruff, sintaxis JavaScript y `collectstatic` correctos.
  Suite completa: **736 pruebas, OK (1 omitida), 536.561 s**. No estuvo
  disponible un navegador conectado para una validación visual interactiva.

## 97. Los formatos de gestión se descargan conservando su maqueta oficial

El usuario eligió rescatar la maqueta oficial. El traspaso decía nueve páginas,
pero enumeraba diez: acta de entrega, expediente de maquila, plan maestro,
control de calidad, plan HACCP, resultados del ejercicio, reporte institucional,
trazabilidad del lote, asistencia y oferta de visitas. Las diez dejan de depender
de «Imprimir» y ofrecen **Ver el documento** y **Descargar PDF**.

- `documentos_gestion.py` adapta la respuesta al final de la vista, después de
  sus verificaciones de acceso y de sus cálculos. Conserva los filtros y los
  flujos POST; `formato=pdf` sirve el archivo inline y `descargar=1` lo entrega
  como adjunto, con caché privada deshabilitada. No se añadieron rutas públicas
  para documentos privados.
- `maquetas_pdf.py` compone con ReportLab la estructura y los textos del mismo
  HTML institucional. Conserva el membrete de tres columnas, el logo, los verdes
  y el dorado, las bandas, tarjetas, anchos propios de las tablas, estados,
  barras de carga, casillas de asistencia y firmas. No transforma estos formatos
  al dataset del reporte genérico ni copia sus cálculos a otro constructor.
- La composición usa A4 horizontal, con pie y numeración propios. Las tablas
  repiten su banda y columnas al pasar de página. Una fila que cabe en una hoja
  se mantiene completa; una fila mayor que una hoja puede dividirse sin impedir
  la descarga. Se reserva espacio real para las firmas del acta.
- El compositor admite solo marcado tipográfico controlado y el logo local;
  escapa los datos y no ejecuta scripts ni carga recursos remotos. Se omiten
  barras de acciones, formularios operativos y navegación a otros lotes.
- Calidad y asistencia avisan que el PDF refleja datos guardados. La asistencia
  conserva las marcas de ingreso y las observaciones registradas; el control
  conserva la medición guardada cuando se consulta con su filtro `hecho`.
  No se modificaron la identidad, el CSS ni el JavaScript globales.
- Se generaron **50 PDF**, los diez formatos para cada una de las cinco plantas
  con recetas activas entre las 21 unidades cargadas. Los registros auxiliares
  de esa revisión se revirtieron mediante una transacción. Se compararon los
  textos del HTML y los PDF sin pérdida de contenido y se verificaron los
  límites del papel. Se inspeccionaron las páginas renderizadas de los diez
  formatos de lácteos, incluidos documentos de varias páginas, entregas,
  controles y firmas. No hubo navegador conectado para una revisión interactiva;
  la revisión visual se hizo sobre las imágenes generadas de los PDF.
- Nueve pruebas nuevas cubren las diez respuestas, permisos, filtros, igualdad
  entre vista previa y descarga, datos guardados, escape de texto y paginación.
  Ruff y comprobación de migraciones correctos, sin migraciones pendientes ni
  nuevas dependencias del proyecto. Las herramientas de inspección PDF quedaron
  aisladas en `tmp/`. Suite completa: **745 pruebas, OK (1 omitida), 378.766 s**.

Se actualiza `TRASPASO-CODEX.md` para no volver a plantear las decisiones ya
resueltas y para conservar como pendiente únicamente la revisión de los datos
de las nueve recetas identificadas en §96, además de las decisiones antiguas.

## 98. La arquitectura nueva empieza por una taxonomía y códigos únicos

Se revisó el paquete completo de Plantas Piloto: documentos 00 a 10, índice,
catálogo y mapa de la fase 1, y los tres libros de cálculo. El paquete contiene
versiones repetidas de los prompts 09 y 10 y propuestas de navegación anteriores
que ya no coinciden con la decisión final. `docs/arquitectura-plantas-piloto.md`
deja explícita la precedencia: las decisiones del usuario y los documentos 09 y
10 gobiernan; el documento 08 organiza las 6 pestañas y 33 secciones; los demás
documentos y libros aportan requisitos y datos de referencia. No se importaron
como reales capacidades, tiempos o parámetros que todavía requieren
levantamiento y validación de la UPEC.

Este bloque implementa el paso 1 de siete sin rehacer lo existente:

- `FamiliaProducto` reemplaza el texto libre `Producto.linea` con 31 familias
  exactas y ordenadas: 6 de Lácteos, 6 de Cárnicos, 6 de Hortofrutícola, 7 de
  Almidones y Derivados y 6 de Panificación. Producto, receta, etapa/PCC, plan de
  calidad, guía y simulación guardada comparten esa clave. Los cargadores y las
  operaciones del panel la propagan y validan que pertenezca a la misma planta.
- Calidad deja la lista plana: el árbol agrupa Protocolos, Control de calidad y
  Plan HACCP por familia. Cada enlace filtra los procesos y planes que le
  corresponden. Procesos y Producción leen el mismo maestro.
- Las 58 unidades físicas de las cinco plantas cambian de `PLANTA-UNIT-*` a
  `PLANTA-EQP-*`. `AliasCodigoUnidadEquipo` conserva cada código anterior y la
  ficha pública responde con redirección permanente 301. La migración actualiza
  también `Reserva.equipo_codigo` y el JSON textual de unidades seleccionadas.
  Los 42 códigos `UNIT` de laboratorios quedan intactos.
- Las tablas públicas de equipos muestran «Código». Cada equipo tiene una ficha
  pública institucional y un porcentaje calculado de datos básicos disponibles.
- `FichaContenido` añade un índice editorial común con código, tipo, estado,
  versión, visibilidad, completitud calculada, objeto fuente y fichas
  relacionadas. No copia el contenido técnico. Señales mantienen ese índice al
  editar productos, procesos, PCC, especificaciones, guías y equipos; los
  cargadores añaden además las fichas de los tres simuladores.
- La migración 0187 carga la taxonomía, vincula los registros existentes, crea
  fichas y alias, transforma códigos y después retira el campo libre. Es
  reversible: al volver atrás restituye códigos y referencias guardadas en las
  reservas antes de retirar las tablas nuevas.

La base de desarrollo aceptó la migración y una recarga de las ocho unidades.
Resultado: cinco plantas, 31 familias, cero productos o procesos sin familia,
58 equipos de planta en `EQP`, 58 alias y 229 fichas editoriales. La recarga no
duplicó registros. Las pruebas nuevas verifican la taxonomía exacta, propagación
de familia, aislamiento de laboratorios, códigos canónicos, alias, 301, columna
«Código», filtro de calidad y fichas editoriales. También se comprobó que las
guías de una sesión y las simulaciones guardadas heredan la familia del proceso.

Validación final: migración aplicada, recarga idempotente, `check`,
`makemigrations --check`, Ruff y `collectstatic` correctos. Suite completa:
**753 pruebas, OK (1 omitida), 418.431 s**. El paso siguiente es completar los
huecos visibles del catálogo sin alterar todavía la estructura interna de las
seis pestañas ni el motor compartido de reservas.

## 99. Las cinco plantas ya se distinguen y el catálogo filtra datos reales

El paso 2 conserva la rejilla institucional y cambia únicamente lo que una
persona necesita para elegir una planta. La captura completa quedó en
`tmp/catalogo-plantas-paso2.png`: aparecen las cinco tarjetas, los filtros
propios y el bloque institucional plegado. No se tocó la estructura de las seis
pestañas ni el flujo compartido de reservas.

- La tarjeta prioriza el `ResponsableUnidad` público con rol de coordinación,
  muestra una etiqueta corta de la planta y hasta tres familias con productos o
  procesos. Desaparecen «Por asignar», «Por registrar» y el contador público de
  visitas. `Unidad.visitas` se conserva para administración y gestión posterior.
- Los conteos se calculan con relaciones activas, no con cifras escritas en la
  plantilla: productos públicos, recetas activas y unidades físicas de equipo
  activas. Lácteos muestra **11 productos, 8 procesos y 17 equipos**. Si los tres
  conteos son cero, la tarjeta dice «En construcción».
- El campo existente `Unidad.imagen` se presenta en el maestro como **Imagen de
  portada**. Conserva todos los archivos previos y usa
  `img/default_project.jpg` cuando Coordinación todavía no ha cargado una foto.
- La migración 0188 incorpora `Unidad.modo_operacion`, obligatorio para plantas,
  y `Unidad.estado_catalogo`. Las cinco cargas institucionales declaran
  producción por lotes con reserva previa. El inline de responsables impide
  guardar una planta sin al menos una persona activa, pública e identificada.
- `EquiposServicios.familia_tecnologica` aporta el vocabulario controlado de
  tratamiento térmico, fermentación, deshidratación, congelación, extracción,
  envasado al vacío/MAP y destilación. El cargador clasifica expresamente los 22
  equipos existentes que pertenecen a esas tecnologías; no infiere la etiqueta
  desde textos en cada consulta.
- El catálogo filtra por las 31 familias del paso 1, tecnología de equipos
  físicos activos, servicio público activo y disponibilidad de la unidad. La
  búsqueda suma también productos, procesos y equipos. Área de conocimiento,
  subárea y modo de operación permanecen como filtros institucionales avanzados.
- `FablabService` distingue ahora desarrollo de producto, maquila académica,
  escalamiento y capacitación. Las cinco maquilas existentes y la asesoría de
  formulación de Cárnicos se clasificaron sin crear ofertas ficticias. El
  asistente recibió vocabulario coherente para los cuatro tipos nuevos, de modo
  que catálogo y reservas siguen leyendo el mismo servicio.

La migración se aplicó y después se recargaron las ocho unidades sin duplicar
registros. Se probaron familia, tecnología, servicio, disponibilidad, modo y
búsqueda, incluido el resultado vacío correcto de destilación mientras no exista
esa capacidad. La captura en Chrome headless confirmó la composición de las
cinco tarjetas y el respaldo gráfico. `check`, `makemigrations --check`, Ruff,
`collectstatic` y la revisión de diferencias terminaron correctamente. Suite
completa: **756 pruebas, OK (1 omitida), 335.741 s**. El siguiente bloque es el
paso 3: ordenar por dentro las pestañas 1, 2 y 3 sin alterar sus seis nombres.

## 100. El catálogo fuerza la hoja visual que contiene los filtros de plantas

La captura revisada por el usuario mostró los controles apilados en el extremo
izquierdo y una superficie blanca vacía. La estructura y la hoja nueva estaban
correctas, pero `catalogo_unidades.html` seguía publicando `catalogo.css` con el
identificador de caché `20260808-structure-v2`, anterior a la cuadrícula añadida
en el paso 2. Un navegador que ya tuviera esa URL almacenada combinaba el HTML
nuevo con el CSS antiguo: interpretaba todo el contenedor de filtros como una
sola celda del formulario compartido.

Se cambió únicamente la versión pública del recurso a
`20260913-plantas-v1`. La URL distinta obliga a cargar la hoja vigente sin
alterar la interfaz institucional ni las reglas de laboratorio. La comprobación
en Chrome a 1600 px muestra las cuatro listas, la búsqueda y el botón usando
todo el ancho; el bloque avanzado queda en su propia franja y «Limpiar filtros»
permanece alineado a la derecha. La evidencia quedó en
`tmp/catalogo-plantas-cache-corregida.png`.

Las dos pruebas dirigidas del catálogo pasaron y la suite completa confirmó
**756 pruebas, OK (1 omitida), 418.844 s**. No cambió ningún modelo, dato,
servicio ni flujo de reservas. El siguiente bloque continúa siendo el paso 3:
ordenar por dentro las pestañas 1, 2 y 3 sin alterar sus seis nombres.

## 101. Los botones de las plantas usan el degradado azul solicitado

La acción «Conocer unidad» de las tarjetas de Plantas Piloto dejó el degradado
café derivado del acento de la tarjeta. La regla específica
`.lab-unit-card--plantas_piloto .lab-unit-card__cta` aplica ahora exactamente
`linear-gradient(100deg, #17a2b8, #01697a)`. La regla común sigue atendiendo a
laboratorios, observatorios y centros experimentales, y los distintivos dorados
de las plantas no cambian.

La plantilla publica `catalogo.css?v=20260913-plantas-v2` para que el navegador
no reutilice la versión anterior. `collectstatic` copió y procesó el recurso. La
captura `tmp/catalogo-plantas-botones-azules.png` verificó las cinco tarjetas a
1600 px, con texto y flecha blancos legibles sobre el degradado. Suite completa:
**756 pruebas, OK (1 omitida), 362.824 s**. El siguiente bloque continúa siendo
el paso 3 de la arquitectura de Plantas Piloto.

## 102. La paleta azul identifica la tarjeta completa de cada planta

La solicitud anterior abarcaba toda la tarjeta y no solo «Conocer unidad». Se
reemplazaron las tres variables propias de Plantas Piloto: acento `#17a2b8`,
acento oscuro `#01697a` y fondo suave `#e8f7fa`. Con ellas cambian de forma
coordinada el borde superior, el rótulo del tipo, el emblema, la decoración, los
títulos de datos, las familias, los conteos, el modo y los estados interactivos.
El botón conserva el degradado exacto solicitado.

Ya no quedan los valores café `#b47b13`, `#785007` ni `#fbf2df` en la identidad
de las tarjetas. Laboratorios, observatorios y centros experimentales mantienen
sus variables. La plantilla publica `catalogo.css?v=20260913-plantas-v3` y
`collectstatic` procesó la hoja. La captura
`tmp/catalogo-plantas-identidad-azul.png` verificó las cinco tarjetas completas
a 1600 px. Suite completa: **756 pruebas, OK (1 omitida), 377.685 s**. El paso 3
funcional sigue siendo el siguiente bloque.

## 103. Las tres primeras pestañas siguen el mapa funcional de Plantas Piloto

El paso 3 conserva los seis nombres y las vistas que ya funcionaban, pero ordena
el árbol interno de las tres primeras pestañas. Las secciones aparecen con su
numeración oficial y su cantidad de fichas; si no existe contenido publicado,
no se crea el bloque ni se muestra el antiguo mensaje «Todavía sin contenido».
Este criterio se aplica también a los recursos configurables y a la sexta
pestaña. El panel derecho queda reducido a un solo encabezado «Contenidos» y su
árbol, sin repetir el nombre de la pestaña activa.

- **Información general:** 1.1 integra el video, el resumen de la unidad y los
  conteos reales de productos, procesos, equipos y áreas. La migración 0189
  añade `Unidad.video_unidad`; mientras esté vacío mantiene el video
  institucional de las cinco plantas. 1.2 recibe dependencia, área, modo,
  código, responsable, ubicación, mapa de acceso, horario, capacidad, estado y
  equipo técnico público. 1.3 aparece únicamente si hay plano, recorrido en
  video o tour 360; 1.5 depende de archivos activos del repositorio. Las
  secciones 1.3, 1.4 y 1.5 permanecen ocultas en los datos actuales.
- **Procesos y protocolos:** 2.1 conserva las fichas de proceso. El balance de
  materia y energía, las simulaciones guardadas y los ejercicios forman 2.4
  como sección de primer nivel, sin el acordeón «Simuladores del proceso». 2.5
  conserva la documentación técnica. 2.6 muestra solamente guías aprobadas,
  agrupadas por familia y con los procesos relacionados; «Mis guías de
  práctica» no se movió de Reservas y servicios. La ruta histórica
  `/laboratorio/<slug>/simuladores/` responde 301 hacia 2.4 y el enlace directo
  activa la pestaña correcta antes de abrir el recurso.
- **Equipos e infraestructura:** 3.1 conserva la vista de áreas y equipos, 3.2
  enumera las fichas públicas de cada unidad física y 3.4 recibe el balance de
  línea. Servicios industriales queda oculto porque aún no tiene una
  publicación propia. Los puntos de estado editorial aparecen únicamente a
  quienes pueden gestionar la unidad y distinguen publicada, parcial y
  pendiente.

La organización se activa solo cuando `Unidad.dependencia` es
`plantas_piloto`; Laboratorios conserva sus acordeones y su información lateral.
La inspección del HTML renderizado de Lácteos y Cárnicos confirmó seis pestañas,
las ocho secciones actualmente publicables, un solo título en el panel y cero
marcadores vacíos. El entorno no ofreció una superficie de navegador conectada,
por lo que esta revisión se hizo sobre el documento final renderizado por
Django. `check`, `makemigrations --check`, Ruff y `collectstatic` terminaron
correctamente. Suite completa: **759 pruebas, OK (1 omitida), 709.388 s**. El
siguiente bloque es el paso 4: Producción y lotes.

## 104. El paso 3 queda auditado contra el mapa de contenidos — 14 de septiembre de 2026

La comparación con `Mapa_de_Contenidos_Plataforma_UPEC.xlsx` confirmó que no
correspondía publicar las 33 secciones como cascarones vacíos, pero también
encontró cuatro diferencias reales: las familias se ordenaban alfabéticamente,
2.4 solo ofrecía un balance general, los controles de recepción sin familia
desaparecían al filtrar calidad y las fichas básicas de equipo se declaraban
publicadas y completas antes del levantamiento técnico.

- `secciones_plantas.py` fija en una sola fuente las seis pestañas y las 33
  secciones oficiales. El árbol usa sus títulos, pero conserva la regla de no
  dibujar una sección sin contenido real.
- Procesos, productos y guías usan ahora `FamiliaProducto.orden`. En Lácteos el
  árbol empieza por Leches y fermentados, Quesos, Cremas y mantequilla y Dulces
  de leche, en el orden del maestro, y las otras cuatro plantas siguen sus
  propios órdenes.
- 2.4 agrupa los simuladores por esas mismas familias y crea un acceso por
  proceso con `?receta=<id>`. El balance libre, Mis simulaciones y Mis
  ejercicios permanecen como herramientas personales, y la redirección
  histórica continúa funcionando.
- Los planes cuya familia es nula son controles transversales de recepción. La
  vista de una familia incluye su control común y el árbol de calidad aporta un
  acceso que muestra solamente esos planes, sin asignarlos arbitrariamente a
  una familia.
- Las 58 fichas de equipo de las plantas permanecen consultables para no romper
  3.1, enlaces ni alias, pero la migración 0190 cambia su estado a `en_revision`.
  La completitud se calcula con identificación, características públicas,
  instrucciones, marca, modelo, serie, ubicación, adquisición, respaldo y
  documentación. En los datos actuales resulta 77 %, en vez del 100 %
  artificial; el levantamiento de capacidad, consumos, conexiones y coordenadas
  sigue perteneciendo al paso 6.
- La prueba de recordatorios de guías dependía accidentalmente del día de la
  semana y falló al cruzar la sesión de domingo a lunes. Ahora fija la fecha de
  referencia del aviso sobre la primera sesión y verifica de forma determinista
  tanto la creación única como la idempotencia, sin cambiar la lógica de
  notificaciones.

La migración 0190 quedó aplicada en la base de desarrollo. La respuesta HTTP
del servidor confirmó ocho simuladores por proceso en Lácteos, el control
transversal, el orden maestro y la ausencia de 2.2, 2.3 y 3.3 mientras no tengan
publicaciones. La captura headless `tmp/paso3-corregido.png` verificó la
composición del árbol a 1600 px. `check`, `makemigrations --check`, Ruff y
`git diff --check` terminaron correctamente. La suite focalizada pasó 84 casos;
la suite completa cerró con **763 pruebas, OK (1 omitida), 779.984 s**. El
siguiente bloque es el paso 4: Producción y lotes.

## 105. El paso 3 elimina repeticiones y completa el catálogo maestro — 14 de septiembre de 2026

La revisión visual del árbol de Lácteos mostró que la corrección anterior había
convertido cada receta en tres accesos repetidos: ficha en 2.1, balance en 2.4 y
documentación en 2.5. Además, los nombres públicos incorporaban la escala de la
corrida («por 100 litros», «por 80 kg»), aunque esa cantidad pertenece al motor
interno. La comparación final con la hoja `03_Taxonomia_Familias` también
confirmó que se habían cargado únicamente los productos con receta técnica y no
las 93 referencias de producto de las cinco plantas.

- `PRODUCTOS_TAXONOMIA` reúne las 93 referencias, su familia oficial y la unidad
  con que el núcleo debe contarlas: 18 de Lácteos, 19 de Cárnicos, 18 de
  Hortofrutícola, 19 de Almidones y 19 de Panificación. El cargador conserva los
  productos, subproductos y residuos anteriores y completa solo los faltantes.
  No crea recetas, cantidades, equipos ni controles ficticios para ellos; cada
  proceso seguirá apareciendo únicamente cuando exista su ficha técnica.
- La carga idempotente deja 22 productos totales en Lácteos, 25 en Cárnicos, 24
  en Hortofrutícola y 26 en Almidones y Panificación. Los productos del maestro
  se ven en «Lo que produce la planta», agrupados por las 31 familias en su
  orden oficial. Los residuos operativos conservan su visibilidad interna.
- `Receta.nombre_publico` toma el nombre limpio de su producto. La receta sigue
  guardando su nombre y escala completos para cálculos, planificación y
  trazabilidad, pero la ficha pública, los simuladores, los documentos HTML y
  PDF, el asistente de reservas, los comprobantes y el editor de guías ya no
  presentan «por 100 litros» como parte del nombre.
- En Plantas Piloto cada sección del panel «Contenidos» es ahora un acordeón y
  cada familia es una subcarpeta plegable. Solo queda abierta la primera sección
  de la pestaña activa y la primera familia de esa sección. Un enlace directo a
  un recurso abre automáticamente sus dos carpetas antes de marcarlo activo.
  Información general, repositorio y guías usan el mismo patrón y los colores
  verde y oro de la interfaz institucional.
- 2.1 conserva una sola lista de procesos por familia. 2.4 quedó reducido a
  Balance de materia y energía, Mis simulaciones y Mis ejercicios. La carpeta
  2.5 dejó de repetir todas las recetas: la documentación técnica continúa
  disponible desde la ficha correspondiente.
- La barra donde aparecen «Ver el documento» y «Descargar PDF» concentra ahora
  los accesos relacionados con el proceso abierto: Ficha del proceso, Balance
  de materia y energía, Capacidad y equilibrado y Documentación técnica. La
  misma navegación se conserva al pasar entre la ficha, el balance y la
  documentación.

Las cinco cargas se ejecutaron sobre la base de desarrollo. El proceso del
servidor seguía sirviendo el código anterior, por lo que se reinició de forma
controlada en `127.0.0.1:8000 --noreload`; la respuesta nueva quedó en 200. La
inspección del HTML servido confirmó diez subacordeones en Lácteos,
cero accesos `simulador-balance-<receta>`, ausencia de la carpeta repetida
`DocumentacionProcesos`, subacordeones por familia y los 18 productos de la
taxonomía de Lácteos sin faltantes. El entorno no ofreció un navegador gráfico
conectado. `check`, `makemigrations --check`, Ruff, `collectstatic` y
`git diff --check` terminaron correctamente. Suite completa final: **764
pruebas, OK (1 omitida), 752.385 s**. El siguiente bloque continúa siendo el
paso 4: Producción y lotes.

## 106. El árbol publica todos los productos y conserva las acciones del proceso — 14 de septiembre de 2026

La comprobación en el servidor reveló dos diferencias que las pruebas de la
sección 105 no detectaban. Los 93 productos del maestro sí estaban cargados en
la base, pero 2.1 construía su árbol desde `Receta`; por eso Lácteos enseñaba
solo los ocho productos con proceso completo y, en Dulces de leche, aparecía
Manjar de leche pero faltaba Arequipe. Las cuatro acciones relacionadas también
llegaban al HTML de la ficha, pero compartían la clase `es-navegacion` con el
enlace «Volver» y la hoja de estilos ocultaba esa clase dentro del iframe.

- El árbol de Sistemas de producción se arma ahora desde todos los productos
  públicos y activos, agrupados por `FamiliaProducto.orden`. Las recetas
  publicadas se relacionan por producto: cuando existen, el producto abre la
  ficha completa de su proceso; cuando todavía faltan datos técnicos, abre una
  ficha de catálogo que informa su familia, unidad, presentación, conservación
  y el estado pendiente sin inventar cantidades, etapas, balances ni equipos.
- La cobertura verifica uno por uno los 18 nombres oficiales de Lácteos y todos
  los nombres definidos para Cárnicos, Hortofrutícola, Almidones y
  Panificación. Arequipe tiene un acceso propio bajo Dulces de leche y su ficha
  pública responde correctamente.
- Ficha del proceso, Balance de materia y energía, Capacidad y equilibrado y
  Documentación técnica usan ahora `accion-proceso`. Solo «Volver a la unidad»
  conserva `es-navegacion`, de modo que el marco evita duplicar el regreso y
  mantiene visibles las cuatro acciones junto a «Ver el documento» y
  «Descargar PDF».
- El cambio se limita a Plantas Piloto. Los laboratorios mantienen su árbol de
  procesos y documentación anterior.

La validación focalizada pasó **67 pruebas**. `check`, `makemigrations
--check`, Ruff y `git diff --check` terminaron correctamente. Suite completa
final: **764 pruebas, OK (1 omitida), 718.022 s**. El siguiente bloque continúa siendo el paso 4:
Producción y lotes.

## 107. Auditoría de cierre de los pasos 1 a 3 — 14 de septiembre de 2026

Antes de iniciar Producción y lotes se compararon nuevamente los tres primeros
pasos con `PROMPT_PARA_EL_CHAT.md`, el documento 09 de migración, las hojas
`01_Arquitectura`, `03_Taxonomia_Familias` y `04_Codificacion` de
`Mapa_de_Contenidos_Plataforma_UPEC.xlsx`, las secciones 98 a 106 de este
historial, la base de desarrollo y el HTML que sirve Django. La auditoría no
encontró una corrección pendiente que bloquee el paso 4.

- **Paso 1:** las cinco plantas comparten exactamente 31 familias en su orden
  maestro; no hay productos ni recetas sin familia. Productos, procesos,
  etapas/PCC, especificaciones, guías, simulaciones y fichas editoriales
  propagan esa relación. Los 58 equipos físicos usan códigos `PLANTA-EQP-*` y
  cada uno conserva un alias para su código `PLANTA-UNIT-*`; la ruta anterior
  responde con redirección permanente. Calidad usa la misma agrupación y las
  tablas públicas dicen «Código».
- **Paso 2:** existen cinco tarjetas, todas con modo por lotes y dos
  responsables públicos activos. La validación del maestro exige modo de
  operación y el inline administrativo impide dejar una planta sin responsable
  público. Las tarjetas no muestran «Por asignar», «Por registrar» ni el
  contador de visitas; calculan productos, procesos y equipos desde el núcleo,
  conservan la portada genérica como respaldo y los filtros de familia,
  tecnología, servicio y disponibilidad siguen cubiertos por pruebas.
- **Paso 3:** cada planta conserva las mismas seis pestañas y la fuente única
  contiene las 33 secciones oficiales. El servidor devuelve 200 para las cinco
  fichas, mantiene el vídeo propio con respaldo institucional, no publica
  secciones huecas ni «Todavía sin contenido», no repite el título del módulo y
  redirige la ruta histórica de simuladores a 2.4. Los estados editoriales solo
  aparecen a quien gestiona la unidad. Las 93 referencias de producto definidas
  por el maestro están presentes en la base y en el árbol de su planta.
- Dos decisiones posteriores del usuario sustituyen literalmente parte de la
  redacción inicial del paso 3: el árbol usa acordeones para mostrar solo la
  carpeta activa, y 2.5 no repite cada proceso. La documentación, el balance y
  la capacidad permanecen accesibles desde la barra de la ficha activa. Son
  ajustes de navegación documentados en las secciones 105 y 106; no eliminan
  contenido ni rompen rutas.

La consulta de auditoría obtuvo cinco respuestas HTTP 200, seis pestañas
exactas por planta, 31 familias, cero referencias maestras ausentes, cero
códigos físicos no canónicos, 58 alias, redirección 301 del simulador anterior
y cuatro acciones visibles en cada proceso. La rama estaba limpia y
sincronizada con `origin/integracion-version2-funciones`. La última suite sobre
el código vigente sigue siendo **764 pruebas, OK (1 omitida), 718.022 s**. Los
pasos 1, 2 y 3 quedan cerrados y el siguiente bloque autorizado es el **paso 4:
Producción y lotes**.

## 108. Producción y lotes separa el catálogo público de la operación interna — 14 de septiembre de 2026

El paso 4 reordenó la cuarta pestaña sin cambiar su nombre ni devolver el
catálogo al alcance anterior de once fichas. La instrucción posterior de
publicar todos los productos del maestro prevalece: Lácteos conserva sus 18
referencias taxonómicas y los productos operativos públicos que ya existían.
El cambio separa esa estructura estable de las órdenes y los lotes que cambian
a diario.

- El árbol de `Producción y lotes` muestra primero **4.1 Lo que produce la
  planta**, después **4.4 Requerimiento de materiales** y finalmente **4.5
  Corridas y lotes**. Las secciones 4.2, 4.3 y 4.6 continúan ocultas porque aún
  no tienen fichas técnicas, empaques ni desarrollos aprobados; no se crearon
  cascarones ni datos ficticios.
- 4.1 contiene únicamente el catálogo por familia, con presentación, vida útil,
  conservación y precio. El contexto de la vista y su PDF dejaron de consultar
  o transportar códigos, cantidades, fechas, ubicaciones y rendimientos de
  órdenes y lotes.
- 4.5 tiene una página y un PDF propios con dos cifras: corridas cerradas en el
  mes y lotes aprobados, disponibles y vigentes. No lista registros. El
  cargador idempotente crea una `FichaContenido` pública para este agregado y
  una interna para el detalle operativo; si la ficha pública se retira, la
  sección y su URL dejan de publicarse.
- El detalle completo permanece funcional en el módulo Producción del panel,
  protegido por autenticación, vínculo con la unidad y permiso operativo de
  producción. La trazabilidad directa de un lote conserva la misma protección.
  La vista interna declara `data-content-visibility="interna"` desde el gobierno
  editorial.
- El botón `Gestionar laboratorio` abre en Plantas Piloto un espacio con los
  diez módulos solicitados y en el orden oficial: Tablero, Programación,
  Planificación, Producción, Inventario y logística, Calidad, Mantenimiento,
  Supervisión, Datos maestros y Reservas. Programación enlaza la agenda común
  ya existente; Supervisión nace como estructura vacía y explícita, sin fingir
  señales reales. Prácticas, seguridad, visitas y reportes conservan sus vistas
  y se acceden como funciones relacionadas desde el Tablero.
- El contador de aperturas de la ficha pública aparece ahora en el Tablero
  interno. Sigue ausente de las tarjetas públicas de las plantas. Laboratorios
  conserva su navegación y su panel anteriores.

Las cinco plantas recibieron las dos fichas editoriales en la base de
desarrollo. La comprobación real de Lácteos devolvió HTTP 200 para la ficha, el
catálogo y el agregado; confirmó 4.1, 4.4 y 4.5 en orden, y verificó que un
código de orden y otro de lote existentes no aparecen en ninguna respuesta
pública. La URL directa de trazabilidad respondió 302 hacia el inicio de sesión
y el panel autenticado mostró los diez módulos y el contador trasladado. El
entorno no ofreció navegador gráfico conectado, por lo que la revisión se hizo
sobre el HTML final servido por Django. `check`, `makemigrations --check`, Ruff
y `git diff --check` terminaron correctamente. Las pruebas focalizadas pasaron
96 casos y los documentos 11; la suite completa final cerró con **765 pruebas,
OK (1 omitida), 346.973 s**. El siguiente bloque es el paso 5: Reservas y
servicios.

## 109. Auditoría completa del libro y separación definitiva entre producto y proceso — 14 de septiembre de 2026

La revisión solicitada abrió completas las siete hojas de
`Mapa_de_Contenidos_Plataforma_UPEC.xlsx`: leyenda, arquitectura, las 165 filas
del mapa de contenidos, taxonomía, codificación, completitud y migración. La
fuente canónica del código conserva las mismas 33 secciones para cada una de
las cinco plantas y quedó con los títulos literales del maestro en 2.6 y 5.1.
La hoja 06 contiene la propuesta anterior de renombrar y retirar pestañas; no
se aplica porque el Documento 09 posterior y la decisión del usuario conservan
las seis pestañas y Reservas y servicios.

La diferencia funcional estaba en la navegación. Para completar los productos
del Excel, el cambio previo había llevado todo `Producto` a 2.1 y mezclaba en
Lácteos veinte productos con sus ocho procesos. Ahora **2.1 Sistemas de
producción** vuelve a nacer exclusivamente de `Receta`: ocho entradas en
Lácteos y tres en cada una de las otras plantas. Cada proceso aparece una sola
vez, agrupado por el orden de `FamiliaProducto`; balance, capacidad y
documentación siguen llegando desde la barra de esa misma ficha. La barra suma
la relación inversa con la ficha del producto sin copiar su contenido.

**4.1 Lo que produce la planta** es la fuente visible del catálogo completo.
Conserva las 93 referencias expandidas de la taxonomía y los 24 productos
operativos válidos que ya existían: 20 productos públicos en Lácteos, 24 en
Cárnicos, 23 en Hortofrutícola y 25 en Almidones y Panificación. Cada fila
enlaza una ficha propia de producto. Esa ficha ya no redirige a la receta
cuando existe: muestra solo los datos comerciales, referencia el único proceso
técnico y se puede revisar y descargar como PDF institucional. El PDF se
construye del mismo contexto de la pantalla y su render de una página quedó sin
cortes, solapamientos ni glifos dañados.

La portada central de cada pestaña de Plantas Piloto resume ahora las secciones
publicadas, en vez de repetir todos los hijos del acordeón y todo el catálogo.
El detalle permanece en la carpeta activa y en el documento abierto. Los
laboratorios conservan su portada detallada, su carpeta de documentación y su
navegación anteriores; una prueba específica cubre esa separación.

La auditoría HTTP sobre la base de desarrollo obtuvo respuesta 200 para ficha
de unidad, catálogo, ficha de producto y ficha de proceso en las cinco plantas;
no encontró referencias taxonómicas ni enlaces ausentes y construyó un PDF de
producto válido en cada planta. El servidor se renovó sin recarga automática y
quedó con un solo listener en `127.0.0.1:8000` (PID 66852). `check`,
`makemigrations --check`, Ruff, `collectstatic` y `git diff --check` terminaron
correctamente. Las pruebas focalizadas pasaron 27, 60 y 7 casos; la suite
completa final cerró con **766 pruebas, OK (1 omitida), 354.002 s**. Los pasos
1 a 4 quedan auditados y el siguiente bloque continúa siendo el paso 5:
Reservas y servicios.

## 110. El árbol muestra el mapa completo de las secciones 1 a 4 — 14 de septiembre de 2026

La revisión visual del usuario mostró que Información general solo enseñaba
1.1 Presentación y 1.2 La unidad. La fuente canónica sí contenía las 33
secciones del libro, pero una decisión anterior ocultaba toda sección con cero
fichas publicadas. Esa regla impedía reconocer la arquitectura y hacía parecer
que 1.3 La planta por dentro, 1.4 Normativa y marco sanitario y 1.5 Repositorio
y descargas no se habían implementado.

La ficha de Planta Piloto mantiene ahora visibles y ordenadas todas las
secciones comprendidas en los pasos terminados: 1.1–1.5, 2.1–2.6, 3.1–3.4 y
4.1–4.6. Cada pestaña abre únicamente su primer acordeón; los demás quedan
plegados. Una sección sin publicación muestra contador cero y «Contenido
pendiente de publicación por la unidad», sin crear documentos, cantidades ni
datos técnicos ficticios.

La arquitectura conserva la fuente única acordada. 2.2 Materiales e insumos y
2.3 Métodos y tiempos indican que su información vive dentro de cada ficha de
proceso de 2.1; 2.5 remite a la barra de esa misma ficha. 4.2 remite a la ficha
de producto abierta desde 4.1. De este modo las secciones del Excel aparecen
sin volver a listar cada proceso o producto. Las portadas centrales excluyen
los marcadores pendientes y continúan resumiendo únicamente el contenido real.
Los laboratorios no pasan por esta ampliación del árbol.

Las respuestas reales de las cinco plantas devolvieron HTTP 200 y exactamente
21 encabezados en orden para las pestañas 1 a 4. La revisión visual en Chrome confirmó que los
cinco encabezados de Información general y los seis de Procesos caben en el
panel, conservan el color institucional y solo muestran el acordeón activo. Las
pruebas focalizadas cerraron 76 casos en verde. La suite completa final cerró
con **767 pruebas, OK (1 omitida), 528.864 s**.

## 111. Gobierno editorial y recursos configurables para los pasos 1 a 4 — 14 de septiembre de 2026

La auditoría final de los pasos 1 a 4 revisó también cómo crecerá el contenido
desde el administrador. La ficha pública ya no depende de crear nuevas listas
en las plantillas: cada `CarpetaRecurso` se asigna a una de las 21 secciones
canónicas 1.1–4.6, admite carpetas hijas y orden propio, y se incorpora dentro
del mismo acordeón de esa sección. El árbol descarta ramas vacías, mantiene
plegadas las carpetas que no están activas y evita un segundo menú paralelo.
En los laboratorios, estas relaciones siguen siendo opcionales y el árbol
anterior permanece sin numeración.

- Carpetas y recursos disponen de orden, estado activo y visibilidad pública,
  restringida a cuentas o interna para gestores. La regla más restrictiva se
  hereda desde la carpeta padre. El administrador permite publicar, restringir,
  volver interno u ocultar en lote; borrar una carpeta elimina sus subcarpetas
  y deja sus recursos disponibles para reclasificarlos.
- Un recurso puede ser un archivo alojado o una URL. Los archivos y el contenido
  interno de paquetes ZIP se entregan por una ruta controlada que comprueba la
  unidad, el estado y el usuario; la descarga solo se ofrece cuando el archivo
  lo permite. La extracción valida previamente todas las rutas del ZIP para no
  escribir fuera de su directorio.
- Productos, familias, recetas, asignaturas y temas quedan editables y
  relacionables desde sus administradores. Un tema académico apunta a la misma
  `Receta` y al mismo software que usa la operación, de modo que una asignatura
  reutiliza el proceso existente en lugar de copiar su ficha técnica.
- `FichaContenido` gobierna ahora también la publicación del contenido generado
  por productos y procesos. Las recargas institucionales actualizan los datos
  técnicos, pero conservan el estado, la visibilidad y la versión elegidos por
  el administrador. Al desactivar el objeto fuente, su ficha se archiva y pasa
  a visibilidad interna.

Se contrastó `Plan_estudio_Alimentos.pdf` sin inventar códigos, períodos ni
docentes. La carga de desarrollo relaciona Lácteos con Tecnología de Lácteos en
sexto semestre; Cárnicos con Tecnología de Productos Cárnicos y Hortofrutícola
con Tecnología de Frutas y Vegetales en séptimo; Panificación y Almidones con
Tecnología de Cereales en octavo. El documento
`docs/plan-estudios-alimentos-y-plantas.md` registra además las asignaturas
transversales que pueden usar las cinco plantas, como análisis de alimentos,
microbiología, inocuidad, operaciones unitarias, empaque, diseño de plantas,
desarrollo de producto e investigación, siempre mediante temas relacionados
con procesos ya existentes.

La migración 0191 se aplicó a desarrollo y conservó la restricción de los
recursos anteriores. La auditoría real obtuvo HTTP 200 en las cinco plantas,
verificó exactamente las 21 secciones 1.1–4.6, un solo encabezado de Contenidos
y los catálogos completos: 31 familias, 123 productos activos y 20 procesos.
La inspección en Chrome confirmó el menú compacto, con 1.1 abierto y las demás
secciones plegadas. `check`, `makemigrations --check`, Ruff y
`git diff --check` terminaron correctamente. La suite completa final cerró con
**775 pruebas, OK (1 omitida), 737.224 s**. El siguiente bloque continúa siendo
el paso 5: Reservas y servicios.

## 112. Reservas y servicios completan la sexta pestaña de Plantas Piloto — 14 de septiembre de 2026

El paso 5 conserva el motor común de reservas y organiza su acceso desde la
sexta pestaña de las plantas. El árbol muestra las siete secciones oficiales
6.1–6.7 como acordeones: reservar y consultar Mis reservas, servicios y tarifas,
agenda pública, requisitos de acceso, guías de práctica, reglamento y visitas o
uso interno. Solo 6.1 nace abierto. Las carpetas administrables se incorporan a
su sección canónica con el gobierno editorial del paso anterior. Visitas y uso
interno se muestra solamente a gestores, y `Gestionar laboratorio` permanece
como acción de cabecera para no duplicar el mismo destino dentro del árbol.
Los laboratorios continúan usando su acordeón anterior y las mismas vistas de
reservas.

El catálogo de servicios ya no es una lista aislada. `FablabService` incorpora
unidad de cobro y responsable de la unidad, valida que ese responsable pertenezca
a la misma ficha y calcula el valor referencial con sus reglas existentes. La
vista pública agrupa la oferta por familia, muestra alcance, entregable,
modalidad, plazo, tarifa, condiciones y responsable, y abre el mismo asistente
con el servicio preseleccionado. La carga institucional completa solamente los
responsables vacíos y conserva cualquier asignación manual. En desarrollo,
Lácteos mantiene cuatro servicios con las unidades de cobro `Por muestra`,
`Por corrida`, `Por sesión` y `Por grupo`, todos relacionados con la responsable
pública correspondiente.

La agenda de 6.3 publica catorce días a partir del horario común de operación.
Cruza las reservas activas y los bloqueos de la unidad y expone solo franjas
libres u ocupadas; no entrega solicitantes, participantes, motivos ni detalles
internos. Tanto la agenda como el catálogo se limitan a Plantas Piloto y admiten
el visor de la ficha mediante `SAMEORIGIN`.

La obligación documental de las prácticas sigue utilizando la misma guía FT04.
Una guía estructurada completa habilita la aprobación de la reserva; para
iniciar y cerrar debe haberse enviado a revisión, y el cierre mantiene el
registro de ejecución real. Un docente con una práctica operativa pasada y una
guía propia aún en borrador o rechazada debe resolverla antes de crear otra.
Las reservas que reutilizan una guía publicada no generan esa deuda. El
asistente ofrece primero usar una guía publicada, luego clonarla y adaptarla,
y finalmente crear una desde cero. Las coincidencias se priorizan por unidad,
familia del proceso y asignatura; una copia guarda `guia_origen` y crea una
actividad independiente, por lo que nunca modifica la versión institucional.

Las migraciones `0192_fablabservice_responsable_fablabservice_unidad_cobro` y
`0193_guia_origen_y_vinculacion_clonada` se aplicaron en desarrollo. La carga
idempotente de las ocho unidades terminó correctamente. Con el servidor
reiniciado sin recarga automática y con un solo listener (PID 14772), Lácteos
devolvió HTTP 200 para su ficha (361505 bytes), el catálogo de servicios
(18479 bytes) y la agenda (33943 bytes);
el HTML final contiene 6.1–6.7, las tres alternativas de guía y el catálogo de
clonado. No hubo una superficie gráfica conectada para esta verificación, por lo
que se inspeccionó el HTML servido por Django.

Las cinco regresiones detectadas por la primera suite completa se corrigieron
sin retirar el contrato nuevo: versión sincronizada del asistente, requisitos
visibles dentro de 6.4, etiqueta correcta de la guía enviada y expectativas
anteriores actualizadas para permitir aprobar con una guía completa. Las cinco
pruebas afectadas y el conjunto de 98 pruebas de reservas, procesos, seguridad y
paso 5 cerraron en verde. Ruff, la sintaxis de los dos JavaScript modificados,
`check`, `makemigrations --check`, `collectstatic` y `git diff --check` terminaron
correctamente. La suite completa final cerró con **782 pruebas, OK (1 omitida),
634.187 s**. Los pasos 1 a 5 quedan terminados; el siguiente bloque de la
secuencia es el paso 6: Completitud y contenido.

## 113. Completitud y contenido construye la ruta del saber y del hacer — 14 de septiembre de 2026

El paso 6 se implementó después de auditar completos el Documento 09 de
migración, el glosario, Ingeniería de procesos y planta, Modelado gráfico,
simulación y supervisión, la auditoría de cobertura, la arquitectura de
información, las guías del repositorio y las hojas de contenido, taxonomía y
catálogos semilla. La página de arquitectura de Human Codeable se tomó como
referencia de organización: concepto central, esquema inicial, bloques breves y
una secuencia de lectura. Se conservó la identidad visual institucional y no se
copió su diseño.

La documentación técnica de cada proceso es ahora una **ruta del saber y del
hacer** con cuatro momentos: Comprender, Calcular, Aplicar y Comprobar. Explica
las operaciones unitarias de sus etapas, el fenómeno que ocurre, la variable
que lo gobierna, lo que sucede fuera de rango y cómo se mide. Incluye balances
total y por componente, energía sensible, tiempo estándar, takt, capacidad por
lote y OEE, con ecuación, datos requeridos, uso y comprobación. El diagrama por
etapas, los iconos, las entradas y salidas y las fuentes del dato se forman
desde la receta vigente; no se mantienen versiones paralelas escritas a mano.
Balance de materia y energía, capacidad y equilibrado y requerimiento de
materiales enseñan la base teórica junto al cálculo. El escenario térmico deja
visibles y editables densidad, calor específico, calor latente y COP para que el
resultado pueda revisarse y no parezca una cifra opaca.

La barra contextual se conserva al pasar de proceso a producto y de regreso.
Agrupa Ficha del producto, Ficha del proceso, Simular balance, Capacidad y
equilibrado, Documentación técnica y Datos CSV. La ficha relacionada enlaza el
producto, especificaciones, guías publicadas y equipos usados por la receta;
cada vínculo lleva al objeto fuente sin duplicarlo en el árbol. HTML, PDF y CSV
se construyen con el mismo contexto. Todas las fichas incorporan una cita con
institución, código, versión y fecha de actualización. La ficha de equipo
también dispone de HTML, CSV y PDF institucional.

`EquiposServicios` admite el levantamiento que exige el paso: capacidad nominal
y útil, modo de operación, preparación y limpieza, conexiones y consumos,
dimensiones, peso, lados de acceso, coordenadas de equipo y operario, MTBF,
MTTR, criticidad, calibración y uso compartido entre plantas. El administrador
organiza estos campos por su finalidad y valida rangos y fechas. Todos nacen
vacíos: la plataforma no convierte un ejemplo de los libros en una medición de
la UPEC.

Cada documentación muestra una matriz de disponibilidad. Flujo, sinóptico,
cursograma y balance total se publican desde los datos actuales. El recorrido
queda bloqueado hasta registrar coordenadas; capacidad efectiva hasta declarar
carga útil, modo, preparación y limpieza; simulación de fallas hasta contar con
MTBF y MTTR; balance por componente hasta cargar composición; supervisión en
tiempo real hasta disponer de señales y contrato de datos. Esta separación
evita presentar supuestos como resultados reales y deja una instrucción exacta
para terminar cada artefacto después del levantamiento.

Gestión incorpora un tablero propio de completitud que reproduce las seis
pestañas y las 33 secciones del mapa maestro. Calcula fichas publicadas frente a
esperadas por sección, pestaña, planta y plataforma dentro del alcance del
gestor, lista cada ficha y ordena los campos críticos por la cantidad de
contenidos que bloquean. El porcentaje y los bloqueos permanecen internos; la
ficha pública solo enseña datos efectivamente publicados.

La migración `0194_ficha_tecnica_equipos_paso_6` se aplicó en desarrollo. La
validación focalizada cerró **36 pruebas, OK (1 omitida)**. `check`,
`makemigrations --check`, Ruff y `git diff --check` terminaron correctamente.
La suite completa final cerró con **788 pruebas, OK (1 omitida), 911.060 s**.
El servidor se reinició sin recarga automática y quedó atendiendo en
`127.0.0.1:8000` (PID 44156). La comprobación directa obtuvo HTTP 200 para la
planta, la ficha, la documentación, el CSV y los PDF de documentación y equipo;
confirmó la fórmula de energía y la ruta contextual. No hubo navegador gráfico
conectado, por lo que la revisión final se hizo sobre HTML, encabezados y
documentos realmente servidos por Django. Los pasos 1 a 6 quedan completos en
código; los artefactos sujetos a levantamiento se habilitarán al incorporar sus
datos validados. El siguiente bloque de la secuencia es el paso 7: artefactos
externos, trazabilidad de fuentes y cierre de cobertura.

## 114. Repositorio gobernado y artefactos externos cierran el paso 7 — 15 de septiembre de 2026

Antes de implementar se auditaron de nuevo los documentos 09 y 10, la
auditoría de cobertura, el mapa de contenidos y la arquitectura funcional. La
revisión encontró una deuda del paso anterior que coincidía con lo observado
en la ficha: 2.2 Materiales e insumos, 2.3 Métodos y tiempos y 2.5
Documentación de los procesos se habían dejado como contadores en cero con un
mensaje que remitía a 2.1. Ya no son marcadores vacíos. Cada sección abre un
índice real de la planta, agrupado por la taxonomía institucional y por proceso,
con acordeones que muestran respectivamente la matriz de insumos, la secuencia
con tiempos y recursos, y la ruta del saber con acceso a la documentación
técnica. Los índices leen las recetas y etapas vigentes; enlazan la ficha fuente
y no copian ocho veces el mismo proceso. También tienen PDF institucional
generado desde el mismo contexto. La sección 2.6 conserva únicamente guías FT04
publicadas: no se inventaron guías para llenar su contador.

La sección 1.5 incorpora un acceso permanente al repositorio institucional,
además de las carpetas personalizadas existentes. `Recurso` funciona ahora como
adjunto gobernado: exige descripción, tipo cerrado, autoría y procedencia,
licencia, visibilidad, versión, estado y vínculo con unidad, sección o ficha;
calcula formato, tamaño, nombre institucional y SHA-256. Rechaza formatos no
permitidos, archivos mayores de 200 MB sin autorización y duplicados físicos.
La publicación en los bloques uniformes al pie de las fichas exige metadatos y
revisión de seguridad. Un documento puede reemplazar otra versión sin borrar su
historial y la descarga controlada contabiliza uso. `CarpetaRecurso` admite un
contenedor de sección o ficha y un máximo de dos niveles, de forma que el
administrador puede ordenar, ocultar, restringir o retirar carpetas y adjuntos
sin crear otro árbol paralelo. Productos, procesos, documentación y equipos
presentan el mismo bloque de archivos y conservan la navegación principal.

`ArtefactoExterno` separa los modelos de Arena, Simulink, Aspen, hojas de
cálculo, notebooks, XR, CAD y datasets del núcleo transaccional. Cada registro
declara unidad y relación con familia, receta, equipo o área; software y
licencia; nivel 1 integrado, 2 conectado o 3 depositado; qué representa,
supuestos, validación con evidencia, limitaciones, autoría, versión y estado.
Los niveles 1 y 2 requieren un contrato legible por máquina con entradas,
salidas, esquema y formato JSON, CSV o XLSX. La exportación toma exclusivamente
los campos declarados, el XLSX se genera como paquete Office estándar y el
resultado externo se importa sin ejecutar binarios ni software propietario.
Una modificación en la receta, en los tiempos de sus etapas o en la ficha del
equipo marca automáticamente el artefacto como posiblemente desactualizado;
solo una nueva importación validada restablece su sincronización. Los archivos
y la evidencia deben pertenecer a la misma unidad. Los artefactos publicados se
integran en 2.4 y en las relaciones de la ficha del proceso.

Gestión dispone de administradores propios para adjuntos, artefactos y
resultados, junto con un informe de candidatos a promoción que detecta huellas
duplicadas heredadas, títulos usados en más de cinco fichas y documentos más
descargados. La migración
`0195_artefactoexterno_adjunto_carpetarecurso_ficha_and_more` se aplicó en
desarrollo. No se cargaron modelos externos ni evidencias ficticias: el
repositorio explica qué falta y mostrará cada elemento cuando el responsable
incorpore un archivo real y validado.

La prueba focalizada final cerró **5 pruebas, OK**. `check`,
`makemigrations --check` y `git diff --check` terminaron correctamente. La
suite completa final cerró con **793 pruebas, OK (1 omitida), 358.992 s** e
incluyó regresiones de plantas, laboratorios, reservas, administración,
documentos y seguridad. La comprobación HTTP sobre el servidor migrado obtuvo
200 para la ficha de Lácteos, los tres índices y el repositorio. Durante esta
verificación se detectaron dos procesos históricos de Django escuchando a la
vez en el puerto 8000; se retiraron ambos y se dejó un único listener con el
código actual. Los pasos 1 a 7 quedan integrados sin cambiar la estructura de
los laboratorios.

## 115. Auditoria final e integral de los pasos 1 a 7 — 15 de septiembre de 2026

Se auditó la implementación completa contra `TRASPASO-CODEX.md`, las secciones
91–114 de este historial, los documentos 09 y 10 y el libro maestro
`Mapa_de_Contenidos_Plataforma_UPEC.xlsx`. El cruce automático confirmó las
**33 secciones canónicas** con los mismos nombres en código y Excel, **33 filas
por cada una de las cinco plantas**, y las **31 familias** en el mismo orden y
con la misma denominación. La ficha mantiene seis pestañas y la taxonomía es
una sola fuente compartida por catálogos, procesos, productos, calidad,
reservas y contenidos. Los laboratorios conservan sus seis módulos anteriores,
sin numeración ni ramas propias de Plantas Piloto.

La revisión funcional separó la existencia de la arquitectura de la
publicación de datos. Las secciones 1.1–6.7 existen, son administrables y
calculan su completitud. Una sección cuyo levantamiento real sigue pendiente
en el Excel permanece plegada, vacía o marcada pendiente hasta recibir planos,
normas, especificaciones, guías, mediciones o evidencias validadas. No se
crearon resultados, referencias técnicas ni archivos ficticios para elevar el
porcentaje. Los productos de la taxonomía sí se cargan completos. El cargador
mantiene 22 registros en Lácteos, 25 en Cárnicos, 24 en Hortofrutícola y 26 en
Almidones y Panificación, incluidos coproductos y salidas internas; el catálogo
público muestra respectivamente 20, 24, 23, 25 y 25. Los procesos publicados
continúan siendo 8 para Lácteos y 3 para cada una de las otras plantas, todos
con selección operativa completa.

La auditoría encontró y corrigió tres incumplimientos concretos del paso 7.
Primero, el catálogo cerrado de adjuntos ya incluye el tipo **Artefacto** que
exige el Documento 10. Segundo, un adjunto activo público o restringido no
puede validarse ni entregarse mientras la revisión de seguridad no esté
confirmada; los recursos históricos sin los metadatos incorporados en el paso
7 conservan su acceso anterior hasta ser gobernados desde el administrador.
Tercero, los artefactos externos conectados usan el código canónico `SIM` y
cada artefacto nivel 1 o 2 publicado para una receta añade a la barra contextual
del proceso una acción directa **Exportar datos**, junto con producto, proceso,
balance, capacidad, documentación y CSV. La exportación sigue limitada al
contrato declarado y cualquier cambio en la receta, una etapa o el equipo
marca el modelo como posiblemente desactualizado.

Se añadieron cuatro casos integrales y reproducibles:

1. Un visitante recorre las cinco plantas, comprueba catálogos, familias,
   pestañas, procesos y selecciones operativas, y verifica que un laboratorio
   común conserva su arquitectura.
2. Un estudiante pasa por ficha de producto, ficha de proceso, ruta del saber,
   balance y capacidad sin perder la barra contextual; valida diagramas, CSV,
   PDF y permiso `SAMEORIGIN`.
3. Un docente solicita una práctica por proceso; una FT04 incompleta bloquea la
   aprobación, la versión completa genera una sola orden y la agenda pública
   solo expone disponibilidad agregada.
4. Un gestor crea una carpeta, intenta publicar un adjunto sin revisión y el
   sistema lo bloquea; después publica evidencia segura, conecta un artefacto,
   exporta su paquete y comprueba la alerta de desactualización.

La migración `0196_alter_recurso_tipo_adjunto` se aplicó en desarrollo y se
volvieron a ejecutar de forma idempotente los cinco cargadores de plantas para
sincronizar su catálogo sin alterar los módulos de laboratorios.
`makemigrations --check`, Ruff y `git diff --check` terminaron correctamente.
Las 9 pruebas focalizadas de la auditoría y el repositorio cerraron en verde.
La suite completa final cerró con **797 pruebas, OK (1 omitida), 352.703 s**.
El servidor se reinició sin recarga automática y quedó como único listener en
`127.0.0.1:8000` (PID 28380). La comprobación directa obtuvo HTTP 200 para el
catálogo, la ficha de Lácteos, una ficha de proceso, su documentación, el índice
2.2, el repositorio y la agenda pública.
Con este cierre los pasos 1 a 7 quedan implementados e integrados; la labor
pendiente es editorial y de levantamiento institucional, administrable desde
la plataforma y sin cambios adicionales de arquitectura.

## 116. Reserva guiada por producto y proceso — 15 de septiembre de 2026

La auditoría del asistente encontró que la selección técnica estaba disponible,
pero aparecía después de clasificar la actividad y la propuesta automática se
explicaba en una lista extensa de recursos. El flujo de Plantas Piloto pregunta
ahora primero qué producto y proceso se realizará y luego solicita el propósito,
la actividad y sus beneficiarios. La opción `Uso de recursos sin un proceso
definido` conserva los casos que no corresponden a una receta. Los laboratorios
comunes mantienen su flujo anterior porque el campo solo existe cuando la unidad
tiene procesos publicados.

La receta continúa como única fuente operativa. Al indicar la cantidad de
materia prima, el servidor calcula el factor respecto a la corrida base y entrega
las áreas, equipos principales y auxiliares, software, insumos escalados,
duración y sesiones. El asistente los marca automáticamente. Los recursos
obligatorios quedan bloqueados porque retirarlos invalidaría el proceso; las
cantidades ajustables y los recursos complementarios siguen bajo decisión de la
persona. La validación de servidor vuelve a comprobar la cobertura al guardar,
por lo que una modificación manual del navegador no permite omitir un requisito.

Antes del inventario se incorporó una ruta horizontal de elaboración. Cada
estación muestra orden, símbolo, operación, área, equipo, duración, espera,
insumos y punto crítico. La vista toma las mismas etapas de la receta y permite
recorrerlas horizontalmente; las tarjetas de áreas y equipos se compactan cuando
hay un proceso activo para reducir altura sin ocultar controles. Al retirar el
proceso se restaura el selector general de recursos.

La agenda pública y el asistente respetan siempre la jornada configurada de la
unidad. En Lácteos la cuadrícula queda entre 07:00 y 17:00 incluso si existe una
reserva administrativa de día completo; las excepciones se gestionan desde el
panel sin convertir la consulta pública en una agenda de 24 horas. El panel de
detalle usa una fila flexible con desplazamiento interno, de modo que pueden
consultarse todos los recursos y ocupaciones sin que los botones inferiores
bloqueen el contenido.

La verificación funcional cubrió cuatro propuestas reales de Lácteos con
recorridos distintos: Crema de leche (8 etapas, 5 equipos, 4 áreas y 5 insumos),
Leche pasteurizada (8, 5, 4 y 5), Manjar de leche (9, 4, 5 y 8) y Mantequilla
(9, 3, 3 y 6). Además se comprobó Queso fresco a doble escala: 11 etapas,
200 litros de leche cruda, 0,8 kg de sal, área inicial y pasteurizador correctos,
recursos obligatorios protegidos y presencia de puntos críticos. Una prueba de
regresión fija la agenda 07:00–17:00 frente a un evento 00:00–23:59.

`check`, `makemigrations --check`, Ruff, `node --check` y `git diff --check`
terminaron correctamente. La tanda focalizada cerró con **84 pruebas, OK** y la
suite completa con **798 pruebas, OK (1 omitida), 801.173 s**. No hubo navegador
gráfico disponible en el entorno; la revisión visual se sustituyó por validación
del HTML servido, estructura del DOM, sintaxis JavaScript, CSS, datos JSON y los
casos de Django. La arquitectura de los pasos 1 a 7 permanece integrada y este
bloque mejora su uso en reservas sin duplicar procesos ni afectar laboratorios.

## 117. Catálogo completo en reservas y sistemas de producción — 15 de septiembre de 2026

La revisión volvió a cruzar la hoja `03_Taxonomia_Familias` de
`Mapa_de_Contenidos_Plataforma_UPEC.xlsx` con la base cargada, el selector de
reservas y el árbol 2.1. El problema no estaba en la taxonomía ni en el
cargador: Lácteos ya tenía sus seis familias y todos los productos esperados,
pero las dos interfaces se construían únicamente con las ocho recetas que hoy
tienen proceso técnico validado. Por eso no aparecían Leche descremada, Queso
maduro, Mazada, Arequipe, las tres clases de helado ni los tres derivados del
suero. La misma omisión se repetía en las demás plantas para todo producto sin
receta.

El selector de Plantas Piloto se construye ahora desde el catálogo público
completo y lo agrupa por la familia maestra del Excel. Cada opción identifica
primero el producto. Si existe una receta activa, declara también el proceso y
su número de etapas, pide la materia prima y conserva la propuesta automática
de áreas, equipos, software e insumos. Si aún no existe receta, muestra
`proceso por configurar`, mantiene identificado el producto y permite elegir
los recursos manualmente. No se inventaron etapas, rendimientos ni balances
para productos cuyo levantamiento técnico sigue pendiente. La opción sin
producto definido permanece para actividades que solo usan recursos.

La reserva guarda ahora `producto_solicitado` además de la receta opcional y
valida que ambos pertenezcan a la unidad y coincidan entre sí. El dato se copia
a las sesiones recurrentes, se actualiza cuando una sesión adopta otro proceso,
aparece en el título, se entrega en `Mis reservas` y queda visible, filtrable y
buscable en el administrador. La migración
`0197_reserva_producto_solicitado` se aplicó en desarrollo.

La sección 2.1 también parte del catálogo completo. Dentro de cada familia,
los productos con receta abren su ficha de proceso; los restantes abren su
ficha de producto canónica con la indicación `proceso por configurar`. Así se
mantiene una sola fuente para cada contenido y se conserva la navegación del
visor. Las recetas siguen siendo ocho en Lácteos y tres en cada una de las
otras plantas; el catálogo público comprobado contiene 20 productos en
Lácteos, 24 en Cárnicos, 23 en Hortofrutícola y 25 en Almidones y
Panificación, incluyendo todos los ejemplos exigidos por la taxonomía y los
coproductos públicos ya existentes.

La validación dirigida cubrió **65 pruebas, OK** para el aula, las reservas por
proceso y las cinco plantas. Incluyó una reserva real de Arequipe sin receta,
la persistencia del producto, los seis grupos de Lácteos y todos los productos
esperados de las cinco plantas tanto en el selector como en el visualizador.
`check`, `makemigrations --check`, `node --check` y `git diff --check`
terminaron correctamente. La suite completa final cerró con **799 pruebas, OK
(1 omitida), 501.304 s**. El servidor migrado quedó como único listener en
`127.0.0.1:8000` (PID 27460); la comprobación directa obtuvo HTTP 200 y confirmó
la versión v139, Arequipe, Helados, Derivados del suero y los enlaces a fichas
de productos sin proceso. No hubo navegador gráfico conectado; la revisión se
realizó sobre el HTML servido, el DOM esperado, la sintaxis JavaScript y los
casos funcionales de Django.

## 118. Jerarquía visual del árbol de contenidos — 15 de septiembre de 2026

El árbol lateral conservaba correctamente sus tres niveles funcionales, pero
las carpetas de familia y las fichas internas compartían fondos y bordes muy
parecidos. Esto hacía difícil distinguir de un vistazo una categoría, un
proceso técnico disponible y un producto cuyo proceso aún debe configurarse.

Las secciones numeradas mantienen el verde institucional. Las carpetas de
familia usan ahora un degradado amarillo institucional, borde dorado e icono de
carpeta contrastado; los estados abierto y al pasar el puntero intensifican el
amarillo sin alterar el funcionamiento del acordeón. Las fichas quedan como
botones independientes con borde, sombra leve y una franja lateral: cian para
los procesos técnicos configurados y dorada para los productos pendientes de
proceso. El recurso activo conserva el amarillo destacado ya usado por la
plataforma. La separación se obtiene mediante los identificadores existentes,
sin duplicar contenido ni introducir campos o código de presentación en el
modelo.

Se actualizó la clave de caché de `detalle_visual.css` para que los navegadores
reciban el cambio de inmediato. Durante la comprobación se detectaron dos
servidores antiguos escuchando en el puerto 8000; se cerraron y se dejó una
sola instancia con la plantilla actual. La consulta directa obtuvo HTTP 200,
confirmó la clave `20260915-jerarquia-contenidos-v8` y verificó el CSS servido.

`git diff --check` terminó correctamente. La suite completa cerró con **799
pruebas, OK (1 omitida), 362.506 s** usando la base de pruebas existente y sin
ejecutar tandas en paralelo. El servidor quedó como único listener en
`127.0.0.1:8000` (PID 15400).

## 119. Carpetas sobrias y recursos administrables — 15 de septiembre de 2026

El amarillo aplicado a toda la superficie de las familias en la sección 2.1
competía visualmente con el recurso activo. Las carpetas recuperan el fondo
claro y el comportamiento de los demás acordeones. El amarillo institucional
queda como color del icono y como una línea lateral discreta al desplegar la
familia; así se reconoce la carpeta sin confundirla con un botón seleccionado.
Los procesos y productos conservan sus acentos diferenciados dentro de cada
familia. La clave de caché de `detalle_visual.css` avanzó a
`20260915-jerarquia-contenidos-v9`.

La edición de recursos desde el administrador fallaba con `ValueError` cuando
el modelo rechazaba un adjunto sin descripción o sin revisión de seguridad.
El problema era una desalineación entre capas: `Recurso.clean()` devolvía los
errores correctos para `descripcion` y `seguridad_verificada`, pero
`RecursoInlineForm` no incluía esos campos y Django no podía mostrarlos.

El formulario de recursos ahora expone todos los metadatos editables que ya
gobierna el modelo: unidad, descripción, carpeta, ficha relacionada, archivo o
URL, tipo, autoría, fecha, fuente, licencia, versión y reemplazo, estado,
palabras clave, orden, visibilidad, descarga, revisión de seguridad y
autorización excepcional de tamaño. En el inline de una unidad, las fichas y
versiones de reemplazo se limitan a esa misma unidad. No se relajaron las
validaciones de seguridad ni se añadió una segunda fuente de datos.

Tres pruebas de regresión verifican que los errores aparecen dentro del
formulario sin provocar una excepción, que un administrador puede crear y
editar un recurso, y que el inline de la unidad presenta los campos
obligatorios. La tanda focalizada cerró con **3 pruebas, OK, 1.251 s**.
`check`, `makemigrations --check`, Ruff y `git diff --check` terminaron
correctamente. La suite completa cerró con **802 pruebas, OK (1 omitida),
466.515 s**. La comprobación directa obtuvo HTTP 200 y confirmó la versión v9;
el servidor quedó como único listener en `127.0.0.1:8000` (PID 30024).

## 120. Apertura de adjuntos con título personalizado — 15 de septiembre de 2026

El recurso real `Prueba` estaba correctamente guardado como PDF, con formato
`pdf`, visibilidad pública y revisión de seguridad aprobada. Su endpoint
respondía HTTP 200 y `Content-Type: application/pdf`. El error del visualizador
se originaba en la plantilla: al abrir el recurso enviaba el título visible
`Prueba` al detector de formato. Como ese título no contiene extensión y la URL
institucional `/recursos-unidad/<id>/` tampoco la expone, el visor no podía
inferir que se trataba de un PDF.

Las carpetas personalizadas conservan ahora el título breve para mostrarlo en
el menú, pero entregan al visualizador el nombre original del archivo. Si no
existe, aplican una cadena de respaldo con el nombre almacenado, la URL y el
título. Los adjuntos PDF y los demás formatos admitidos se identifican así sin
depender de que el administrador escriba la extensión en el campo `Nombre`.
Los paquetes ZIP se conectaron además con el manejador de recursos
interactivos ya existente para abrir su `index.html` extraído dentro del mismo
visor.

La prueba de regresión crea un PDF cuyo título es `Prueba`, verifica que el
botón use `plan_estudio.pdf`, comprueba la respuesta `application/pdf` y cubre
también la llamada de apertura para un ZIP. El módulo del repositorio cerró con
**6 pruebas, OK**. `check`, `makemigrations --check`, Ruff y
`git diff --check` terminaron correctamente. La suite completa final cerró con
**803 pruebas, OK (1 omitida), 696.879 s**.

## 121. Vista previa PDF dentro del aula — 15 de septiembre de 2026

La acción `Ver el documento` del índice 2.2 abría una pestaña nueva y el PDF
fallaba antes de generarse con `Table 1 rows x 0 cols`. La causa era que el
presentador institucional siempre construía la tabla de indicadores, incluso
cuando un documento no declaraba tarjetas. Los índices 2.2, 2.3 y 2.5 no usan
esas tarjetas porque su contenido principal ya está en la matriz por familia y
proceso.

El generador omite ahora la tabla de indicadores cuando la colección está
vacía y calcula el ancho de las tarjetas presentes. La URL exacta
`/laboratorio/planta-piloto-lacteos/procesos/materiales-e-insumos/?formato=pdf`
respondió HTTP 200, `application/pdf`, disposición `inline` y produjo un archivo
de 53 530 bytes.

Todas las acciones `Ver el documento` del aula, fichas de productos, procesos,
documentación, simulaciones y espacios de estudiante abren ahora un visor PDF
en un modal sobre la página actual. El modal incluye título, cierre mediante
botón, fondo o tecla Escape, vista amplia adaptable y descarga directa. Al
cerrarlo se descarga el `iframe` y se devuelve el foco al botón que lo abrió.
Las acciones dejaron de usar `target="_blank"`; `Descargar PDF` conserva su
comportamiento independiente.

Las pruebas de documentos incorporaron los tres índices que antes no estaban
cubiertos y verifican el disparador, el modal y la ausencia de una pestaña
nueva. La tanda del módulo cerró con **11 pruebas, OK**. `check`,
`makemigrations --check`, Ruff y `git diff --check` terminaron correctamente.
La suite completa final cerró con **803 pruebas, OK (1 omitida), 858.201 s**.
La sesión no expuso un navegador automatizable para una captura gráfica; la
validación se realizó sobre las respuestas reales del servidor, el HTML del
modal y los casos funcionales de Django.

## 122. Inicio de sesión por puerto reenviado — 15 de septiembre de 2026

La prueba mediante el puerto 8000 devolvía 403 al iniciar sesión con el mensaje
`Origin checking failed - http://localhost:8000 does not match any trusted
origins`. `ALLOWED_HOSTS` ya aceptaba `localhost`, pero la configuración base
tenía `CSRF_TRUSTED_ORIGINS` vacío. Además, el proxy del IDE marca la petición
como HTTPS mediante `X-Forwarded-Proto` mientras el navegador local conserva
`http://localhost:8000` en el encabezado `Origin`; por eso Django exigía que el
origen local estuviera declarado explícitamente.

La configuración de desarrollo incorpora ahora `http://localhost:8000` y
`http://127.0.0.1:8000`, además de los orígenes opcionales definidos por la
variable `CSRF_TRUSTED_ORIGINS`. Se eliminan duplicados conservando el orden.
`settings_production.py` continúa reemplazando por completo esta lista y exige
que producción declare sus dominios HTTPS reales, por lo que el ajuste local no
amplía la confianza del despliegue público.

La prueba de regresión usa el cliente Django con verificación CSRF real, obtiene
un token del formulario y envía el POST con `Origin: http://localhost:8000` y
`X-Forwarded-Proto: https`. El flujo llega a validar credenciales y no responde
403. La comprobación contra el servidor real obtuvo GET 200, token válido, POST
200 y confirmó que no apareció el fallo CSRF. Las **5 pruebas de seguridad**
aprobaron. `check`, `makemigrations --check`, Ruff y `git diff --check`
terminaron correctamente. La suite completa final cerró con **804 pruebas, OK
(1 omitida), 849.338 s**.

## 123. Recuperacion CSRF desde dispositivos externos - 15 de septiembre de 2026

El acceso mediante Dev Tunnels ya superaba la validacion del origen, pero el
telefono conservaba un token distinto del valor presente en la cookie y Django
respondia `CSRF token from POST incorrect`. Una sesion limpia contra
`https://tdv5t4s7-8000.use.devtunnels.ms/login/` confirmo GET 200, formulario
de 64 caracteres, cookie de 32 caracteres y POST 200; el problema restante era
la reutilizacion de una cookie o formulario anterior en el dispositivo.

La plataforma usa ahora la cookie propia `citt_csrftoken`, de modo que no se
confunde con una cookie generica `csrftoken` conservada por otra aplicacion
Django o por una ejecucion anterior del tunel. La pagina de acceso incluye
`Cache-Control: no-store` mediante `never_cache`, por lo que el navegador no
reutiliza un formulario antiguo.

Se agrego una recuperacion acotada al POST de `/login/`: si falta su cookie o el
token del formulario ya no coincide, las credenciales rechazadas no se
procesan, se rota el secreto y se vuelve a `/login/?seguridad=renovada` con una
explicacion para reintentar. Las fallas de origen, referer y las solicitudes a
otras rutas conservan el 403 normal de Django.

La prueba publica, despues de reiniciar el servidor, recibio
`citt_csrftoken`; al sustituir deliberadamente la cookie por otra valida pero
diferente, el POST respondio 302 hacia el formulario renovado en lugar de 403.
La regresion automatizada cubre el acceso normal y esa recuperacion. `check`,
`makemigrations --check`, Ruff y `git diff --check` aprobaron. La suite completa
cerro con **805 pruebas, OK (1 omitida), 758.443 s**. El servidor quedo con un
solo listener en `127.0.0.1:8000` (PID 55704).

## 124. Auditoría para la reestructuración modular — 15 de septiembre de 2026

El commit funcional `654bd1a4` quedó conservado y publicado en
`integracion-version2-funciones`. Desde ese punto se creó la rama
`reestructura-modular`, destinada exclusivamente a separar responsabilidades
sin mezclar nuevas funciones ni mover tablas de forma masiva.

La auditoría está en `docs/auditoria-arquitectura-modular.md`. El inventario
encontró una sola app propia (`webcitt`), 95 modelos, 197 migraciones aplicadas,
220 archivos Python, 590 importaciones internas y 120 rutas de negocio sin
nombres duplicados. Los 220 módulos compilaron. El ciclo principal conecta 20
módulos, sobre todo por retornos desde cronograma, cambios y guías hacia
`reservas.views`, y por dependencias cruzadas de aula, calidad, seguridad,
visitas y prácticas. Además, cuatro importaciones hacen que modelos conozcan
funciones de presentación o casos de uso.

Los principales puntos de concentración son `gestion.py` (4.910 líneas),
`gestion_unidad_view` (1.053), `reservas/views.py` (3.406), `crear_reserva`
(1.220), `models/reservas.py` (2.105) y `reservas/guias.py` (2.060). El admin
registra directamente 59 de 95 modelos; los 36 restantes deberán clasificarse
como inline, panel propio o modelo interno antes de decidir si necesitan una
pantalla administrativa.

La arquitectura objetivo usa seis contextos contenidos: `core`, `portal`,
`unidades`, `reservas`, `operaciones` y `aprendizaje`. La transición empieza
separando URLs, retirando importaciones anticipadas y fijando contratos sin
tocar modelos. Después reduce controladores, rompe ciclos, crea las apps con
sus vistas y recursos, y finalmente traslada modelos uno por uno conservando
tablas, permisos y `ContentType` mediante migraciones de estado explícitas.

El hito utilizado como línea base conserva **805 pruebas, OK (1 omitida)**.
Los casos directos de portada, acceso, ficha de planta y PDF respondieron HTTP
200; el administrador anónimo redirigió correctamente a su acceso.
`manage.py check`, `makemigrations --check --dry-run`, Ruff y `compileall`
terminaron correctamente. En esta entrega solo cambió documentación.

## 125. Estructura objetivo y nuevo nombre institucional - 15 de septiembre de 2026

Se definio como nombre oficial **Sistema de Laboratorios y Centros de
Investigacion y Desarrollo**, nombre corto **Sistema de Laboratorios y Centros
I+D** y codigo tecnico nuevo `SLCID`. La especificacion completa quedo en
`docs/estructura-objetivo-sistema-laboratorios.md` y se enlazo desde el README y
la arquitectura general.

La estructura final propuesta usa `apps/core`, `portal`, `unidades`, `reservas`,
`operaciones`, `aprendizaje` y `centros_id`. Operaciones agrupa internamente
produccion, inventario, mantenimiento, calidad, trazabilidad y servicios para
no crear una app por cada pantalla. Aprendizaje posee asignaturas, practicas,
guias, simuladores y ejercicios. `centros_id` se activa cuando tenga modelos y
casos de uso reales.

El cambio de nombre se dividio en cuatro capas. La marca visible aparece hoy en
33 archivos y se centralizara primero. La infraestructura (`citt-*`), los
codigos de negocio `CITT-*` y la identidad tecnica `webcitt` se tratan por
separado. `webcitt` aparece en 176 archivos y ademas identifica tablas,
permisos, rutas administrativas, `ContentType`, Guardian y migraciones; se
mantendra como compatibilidad hasta trasladar los modelos por contexto.

El documento describe el arbol de carpetas, la direccion permitida de
dependencias, la organizacion del administrador y seis etapas de cambio:
marca, rutas, casos de uso, apps y recursos, modelos y permisos, y retiro del
legado. En esta entrega no se cambio codigo ejecutable ni base de datos.
`manage.py check`, `makemigrations --check --dry-run` y `git diff --check`
terminaron correctamente.

## 126. Base de seguridad y continuidad para la reestructuracion - 15 de septiembre de 2026

La reestructuracion empezo por la capa que protege todos los contextos. El
entorno anterior acumulaba avisos conocidos en once dependencias y Django 4.2
ya habia terminado su soporte. El proyecto, sus archivos fijados y el entorno
principal se actualizaron a Django 5.2 LTS y versiones compatibles. `pip-audit`
termino sin vulnerabilidades conocidas.

Produccion incorpora comprobaciones que detienen el despliegue ante una clave
de PostgreSQL corta o comun, un host ausente, una base remota sin TLS verificado
ni red aislada, acceso social por GET o `unsafe-eval` en CSP. Las sesiones
sociales ahora empiezan mediante POST con CSRF. La base y la aplicacion de
Docker solo se enlazan a `127.0.0.1`; PostgreSQL admite CA, `verify-full`, tiempo
maximo de conexion, consultas y bloqueos. La configuracion real de `.env` no se
publico ni se imprimio: antes de produccion se deben rotar de forma coordinada
la clave de la base y las credenciales de correo, y las comprobaciones nuevas
impiden declarar seguro un despliegue que aun conserve valores debiles.

Los respaldos de PostgreSQL y `media/` se escriben primero en un temporal,
validan su contenido, se mueven de forma atomica y generan SHA-256. La retencion
es configurable y el restaurador verifica el respaldo en una base efimera con
`ON_ERROR_STOP`. `docs/seguridad-continuidad.md` fija una politica 3-2-1, RPO
inicial de 24 horas, RTO de 4 horas, prueba mensual de restauracion y la ruta a
PITR. La copia externa cifrada e inmutable, el gestor de secretos, MFA y PITR
requieren infraestructura institucional; quedan identificados como requisitos,
no como capacidades ya garantizadas.

La frontera modular quedo protegida por una prueba AST: solo tolera los cuatro
acoplamientos historicos de modelos a dominios ya inventariados y falla si se
agrega otro o si `config` importa una app de negocio. Esto permite extraer
`core`, `portal`, `unidades`, `reservas`, `operaciones` y `aprendizaje` por
etapas, conservando tablas, rutas y permisos. La auditoria de hashes encontro
tres pares de imagenes iguales con consumidores publicos distintos; no se
eliminaron hasta migrar esas referencias. Tambien se corrigio una salida HTML
almacenada del administrador: nombres e iconos de categorias se escapan y los
colores solo aceptan hexadecimal de seis digitos.

La validacion final ejecuto **813 pruebas, OK (1 omitida), 528.306 s**.
`manage.py check`, `makemigrations --check`, Ruff, la comprobacion de despliegue
con configuracion fuerte, `docker compose config`, `pip-audit` y las pruebas de
contrato de respaldos aprobaron. Portada y acceso respondieron HTTP 200 en el
unico servidor local `127.0.0.1:8000`.

## 127. Fronteras verticales de unidades y Centros I+D - 15 de septiembre de 2026

Antes de mover codigo se corrigio la arquitectura objetivo. La implementacion
vigente usa un solo `Unidad`, un expediente `Reserva` y el dominio amplio
`webcitt/domains/unidades`; los perfiles especializados ya distinguen los tipos,
pero gran parte de su comportamiento sigue concentrado en la ficha, el asistente
y la gestion comunes. Esa reutilizacion se mantiene solo como compatibilidad
durante la migracion.

La nueva frontera separa cinco contextos operativos: Laboratorios, Plantas
piloto, Centros experimentales, Observatorios y Centros I+D. Los cuatro primeros
son tipos de unidad, pero cada uno sera propietario de configuracion, datos,
reglas, URLs, admin, plantillas, estaticos y pruebas. Una sesion por horas, una
corrida, un ensayo de campo y una solicitud de datos dejan de tratarse como la
misma reserva con banderas.

Centros I+D no es una unidad reservable. Tendra modelos y casos de uso propios
para centros, lineas, grupos, investigadores, proyectos, resultados, servicios,
propiedad intelectual y transferencia. Podra usar capacidades mediante
contratos, IDs estables y tablas de enlace, sin importar modelos internos de
las unidades. `directorio_unidades` solo conservara identidad publica, tipo,
slug, responsables y contacto.

La especificacion canonica quedo en
`docs/arquitectura-vertical-unidades-centros-id.md`. Tambien se corrigieron
`docs/arquitectura.md`, la estructura objetivo, la auditoria modular, seguridad,
el documento de unidades, el README y el traspaso. El siguiente bloque separa
rutas y contratos por vertical sin cambiar tablas, datos, paths publicos ni
permisos. Como solo cambio documentacion, se conserva la base verificada de
**813 pruebas, OK (1 omitida)** del commit `7b93fed7`; `manage.py check`,
`makemigrations --check` y `git diff --check` deben cerrar esta revision.

## 128. Portal institucional con secciones administrables - 15 de septiembre de 2026

La auditoria del portal encontro que Inicio, Quienes somos, Servicios,
Normativa y Noticias ya tienen rutas y plantillas distintas, pero su contenido
esta escrito directamente en HTML. `webcitt/domains/portal/views.py` solo
entrega plantillas y no existen modelos ni administracion editorial para esas
cinco secciones.

La arquitectura las mantiene dentro de una app `portal`, porque comparten ciclo
editorial y componentes visuales, pero cada una tendra modulo, modelos,
selectores, vistas, permisos, administracion y pruebas propios. Inicio gestiona
portada, bloques e indicadores; Quienes somos, identidad e hitos; Servicios,
oferta institucional; Normativa, documentos versionados; Noticias, articulos,
agenda y convocatorias. Los servicios editoriales no sustituyen los servicios
tecnicos de las unidades.

Centros I+D no forma parte del portal editorial. La pagina actual es transitoria
y conservara su URL cuando la app `centros_id` asuma modelos, administracion y
vistas. El portal solo consumira una proyeccion publica cacheable.

La especificacion canonica esta en `docs/arquitectura-portal-administrable.md`.
Se enlazo desde el README y se corrigieron la arquitectura general, vertical,
objetivo, auditoria y traspaso. No se modifico codigo ejecutable ni base de
datos; se mantiene la base de **813 pruebas, OK (1 omitida)**.

## 129. Primera frontera ejecutable de rutas y contratos - 16 de septiembre de 2026

Se implemento el primer bloque de la arquitectura vertical aprobada. Las
entradas publicas de Portal, Centros I+D, Laboratorios, Plantas piloto, Centros
experimentales y Observatorios viven ahora en `apps/<contexto>/presentation`.
Centros I+D tiene su vista transitoria propia y no importa el portal ni las
unidades. `webcitt/urls.py` compone las entradas y las 104 rutas operativas
compartidas quedan explicitamente en `webcitt/routing/heredadas.py`.

La enumeracion directa congela **119 endpoints: 118 con nombre y uno de media
sin nombre**, corrigiendo el recuento anterior de 120. No se cambiaron paths,
nombres de reverse, argumentos ni callbacks operativos. El alias historico
`/laboratorio/<slug>/` conserva los enlaces ya publicados de plantas y otros
tipos. Los catalogos y el detalle comunes se cargan al atender la peticion
mediante el adaptador temporal `apps/integraciones/unidades_heredadas.py`.

Se retiraron las fachadas anticipadas del portal y Unidades, el archivo
`unidades/views.py` y cinco wrappers de catalogo sin consumidores. Las rutas
heredadas importan directamente sus modulos operativos. El paquete de reservas
aun conserva su fachada hasta extraer sus consumidores; no se declara eliminado
todo el acoplamiento de arranque.

`apps/directorio_unidades/contracts.py` define los cuatro tipos existentes y
la identidad publica v1 como valores inmutables y serializables. Centros I+D
queda fuera de esa enumeracion. Su selector solo proyecta ID, nombre, slug,
tipo y correo publico de unidades activas; no entrega objetos ORM, permisos,
responsables privados o reservas. La proyeccion no redefine la politica de
acceso del detalle heredado.

El comando `manage.py inventario_arquitectura` genera metadatos sin consultar
filas ni adjuntos. La fotografia en `docs/inventario-arquitectura.json` cubre
95 modelos, 120 tablas incluidas M2M, 380 permisos declarados, 59 registros de
admin, 135 plantillas, 851 estaticos, 14 comandos y 10 scripts operativos. Los
destinos de modelos son propuestas; los agregados compartidos siguen marcados
como pendientes de descomponer, no como migrados.

Diez pruebas nuevas comparan el mapa previo, resuelven y reconstruyen cada URL,
verifican sus propietarios y bloquean importaciones cruzadas. Cada modulo de
URLs carga en un interprete limpio sin django.setup ni codigo heredado. Cuatro
casos reales cubren catalogo, detalle, aliases e identidad de Laboratorio,
Planta, Centro experimental y Observatorio. Un fallo operativo simulado no
impide responder al portal ni a Centros I+D.

Validacion integral: **823 pruebas, OK (1 omitida), 778.720 s**. Ruff, Django
check, makemigrations --check y git diff --check aprobaron. El unico servidor
local se reinicio en `127.0.0.1:8000` y portada, acceso, Centros I+D y los cuatro
catalogos respondieron HTTP 200. No hay migraciones nuevas ni traslados de
tablas, permisos o administracion.

La referencia ejecutable esta en `docs/rutas-y-contratos-modulares.md`.
Siguiente bloque: extraer Observatorios del flujo de reserva fisica, con
configuracion, consultas y publicaciones propias. El URLconf completo aun
carga operacion heredada; un error de arranque puede afectar el proceso Django
completo. Aislamiento de datos, admin, colas y despliegue sigue pendiente y
exige pruebas de migracion y reversa sobre una copia antes de mover modelos.

## 130. Ruta de ejecucion modular por hitos - 16 de septiembre de 2026

Se documento la secuencia M00-M13 solicitada por el usuario en
`docs/ruta-ejecucion-arquitectura-modular.md`. Es una ruta de arquitectura,
distinta de los pasos funcionales 1-7 de plantas. El primer bloque M00 esta
implementado; siguen recuperacion M01 y fronteras/propietarios M02 aplicadas
a Observatorios antes de extraer su comportamiento M03.

La revision identifico señales compartidas que crean perfiles/configuracion,
una matriz comun de permisos, acoplamientos de cronograma a validadores de
vistas y ejercicios de aula vinculados a recetas/familias. No se aceptan los
destinos automaticos de modelos como propiedad definitiva. Se conservan
Django auth/allauth/Guardian y los identificadores historicos durante el cambio.

La ruta divide cada vertical en lecturas, comandos, presentacion/admin,
traslado controlado de modelos y retiro de consumidores antiguos. El traslado
M10 se repite por agregado cuando sus dependencias esten resueltas; no es una
migracion masiva final. Observatorios, Plantas, Centros experimentales y
Laboratorios se separan en ese orden; Aprendizaje, Centros I+D, Portal y las
funciones centrales conservan contratos y propiedad definida.

Se exigen pruebas por roles/unidad, cuatro casos por contexto, concurrencia
donde corresponde, conciliacion de datos/permisos/archivos y reversa ensayada.
La base de continuidad requiere copia consistente de PostgreSQL y media y
restauracion integral; cambiar de rama solo devuelve codigo. El aislamiento
real requiere URLconf/ajustes/procesos/colas/credenciales propios y controles
de caida; dependencias compartidas requieren disponibilidad independiente.

Se contrasto la estrategia con documentacion oficial de Django 5.2 sobre
migraciones y despliegue y de PostgreSQL sobre respaldos. La ruta se enlazo
desde README, arquitectura vigente, estructura objetivo, bloque de rutas y
traspaso. No cambia codigo, tablas, configuracion o permisos. Se conserva la
suite integral vigente de `eda9ded9`: **823 pruebas, OK (1 omitida), 778.720 s**;
esta entrega documental verifica enlaces, Django check, ausencia de nuevas
migraciones y git diff --check sin declarar una suite nueva.

## 131. Ruta del producto configurable por institucion - 16 de septiembre de 2026

El usuario confirma la orientacion comercial reutilizable y precisa que una
institucion puede tener solo Laboratorios o categorias distintas de UPEC.
Se revisa la ruta sin ejecutar aun el refactor: M00-M13 conserva trazabilidad,
M02 se divide en M02.1 identidad/configuracion, M02.2 manifiestos/habilitacion/
limites, M02.3 categorias/extensiones y M02.4 contratos/propietarios/efectos.
Esta base se prepara antes de extraer Observatorios. La marca SLCID se inicia
en M02.1 y se separa del perfil UPEC; empaquetado/retiro se completa en M12.

Se aprovechan Categoria y TipoLaboratorio existentes tras auditar relaciones;
los cuatro valores fijos de Unidad/TipoUnidad son implementaciones iniciales,
no un limite permanente. Categorias compatibles son datos administrables;
modalidades con otras reglas necesitan estrategia/app implementada y probada.
No se aceptan plugins de codigo arbitrario subidos desde el admin ni una
reserva universal que fuerce el mismo flujo a todas las verticales.

Se distinguen modulo disponible en despliegue, habilitado en institucion,
derecho comercial/limites y permisos por objeto. Control en servidor, comandos,
rutas directas y tareas; suspension conserva historial y recuperacion autorizada.
Primero instalacion independiente con datos/adjuntos/secretos/respaldos propios
por institucion; un SaaS compartido necesita otra fase de aislamiento. Nucleo
versionado comun, sin ramas por cliente ni datos UPEC en la distribucion.

La aceptacion agrega cuatro perfiles: solo Laboratorios, categorias propias,
UPEC y seleccion ampliada con extension operativa. Cada uno exige arranque,
instalacion/actualizacion, permisos/limites, suspension/reactivacion y
recuperacion, ademas de los casos funcionales por vertical. Se revisa licencia
de distribucion y dependencias antes de comercializar, sin asumir derechos
ni facturacion implementados. Se consulto documentacion oficial de Django 5.2
sobre registro de apps y empaquetado reutilizable.

Se actualizan ruta, estructura objetivo, arquitectura vertical y traspaso.
No cambian codigo, datos, ajustes, tablas, permisos o rama estable. Validacion
documental: enlaces locales, Django check, makemigrations --check y diff check.
Suite integral vigente del bloque eda9ded9: **823 pruebas, OK (1 omitida),
778.720 s**; no se declara una nueva ejecucion de suite en este bloque.

## 132. Primera identidad neutra y ensayo local de recuperacion - 16 de septiembre de 2026

Se inicia M01/M02.1 con codigo compatible, sin migrar datos. Contratos puros
e inmutables en apps/core/identidad.py, constructor de configuracion permitida
y perfil UPEC separado en config/perfiles. El adaptador de presentacion comun
alimenta cabecera/contactos, acceso, admin, notificaciones HTML/texto, reportes,
maquetas oficiales, comprobantes, guias y citas generadas. El perfil custom
requiere nombre/siglas y no hereda logo/contactos de UPEC. Ausencia de imagen
usa siglas y evita lecturas remotas. Campos simples sin HTML/saltos de linea,
correo validado, rutas relativas de imagen local y claves desconocidas
rechazadas; ningun entorno completo ni secreto se proyecta al usuario.

Se genera snapshot PostgreSQL y dump protegido, se restaura en una base con
nombre aleatorio distinta de la activa, se compara hash de todas sus filas
y se elimina la base temporal. Coinciden 135 tablas y 6.654 registros,
incluyendo auth, ContentType y Guardian. Se recuperan y comparan 358 adjuntos,
con estabilidad observada durante la captura; cero FK sin validar. Artefactos,
checksums y detalle quedan ignorados por Git en backups/m01_20260916T112440Z_47d2ba30,
con ACL privada sin herencia para operador y SYSTEM. No se escribio en la base
activa ni se modificaron usuarios/permisos/esquema.

M01 institucional sigue abierto: coordinar escritores/subidas, separar roles
PostgreSQL, copia externa cifrada/inmutable y restauracion en servidor aislado.
La credencial local actual es superusuario; no usarla para ejecucion de
produccion. El ensayo local no acredita RPO/RTO o aislamiento de despliegue.
Continuar solamente codigo compatible hasta cerrar la puerta de datos.

M02.1 tambien conserva pendientes: catalogos academicos, calendario/idioma,
configuracion visual administrable y contenido editorial. Se preservan noticias,
mapas, fotos, cargadores y codigos FT historicos; no se alteran autorias ni
migraciones antiguas. Los perfiles modulares/comerciales requieren M02.2-M02.3
y posteriores extracciones. No se renombran repo/base/tablas/labels/cookies.

Se agregan seis pruebas de identidad, con UPEC y tres instituciones custom,
configuracion invalida, PDF real sin logo y contrato puro sin Django. Pasan
50 pruebas enfocadas, Ruff, Django check y makemigrations --check; collectstatic
conserva los estaticos existentes. Servidor unico reiniciado: diez recorridos
HTTP 200, incluido PDF de materiales/insumos con SAMEORIGIN. La suite integral
final cerro con 829 pruebas, OK (1 omitida), 771.271 s.

La revision adicional detecto colision con el contexto producto de la ficha
publica. Se usan identidad_producto/identidad_institucion y una regresion
verifica marca y producto real juntos en cabecera/aula. La primera corrida
integral se interrumpio para corregirlo y se reinicia sobre el bloque final.

La segunda corrida completa detecto un cambio involuntario de texto en el
comprobante referencial: faltaba el articulo de lo asume la UPEC. Se conserva
la redaccion original con siglas configurables; el caso fallido mas las seis
pruebas de identidad pasan (7 pruebas). Se vuelve a ejecutar la suite integral
antes de publicar, sin cambiar importes o reglas economicas.

La corrida final completa paso: **Suite completa: 829 pruebas, OK (1 omitida),
771.271 s**. Ruff, Django check, makemigrations --check, enlaces locales y
git diff --check correctos. El servidor unico se reinicio sobre el codigo final
y los diez recorridos HTTP respondieron 200. Este bloque se publica en
reestructura-modular; la rama estable permanece en 654bd1a4. Continuar M02.1
con catalogos/politicas institucionales y cerrar la recuperacion institucional
M01 antes de trasladar datos. Identidad configurable no concede permisos ni
completa instalacion comercial, categorias o aislamiento de fallos.

## 133. Catalogo academico compatible por instalacion - 16 de septiembre de 2026

Se continua M02.1 sin extraer modelos o mover datos. apps/core/catalogos.py
define contrato puro e inmutable de dependencias/carreras/historicos y politica
de carrera obligatoria. config/perfiles/upec.py conserva codigos/etiquetas
operativas: seis dependencias, dieciseis carreras, cinco categorias heredadas.
ACADEMIC_CATALOG y ACADEMIC_CATALOG_JSON seleccionan el catalogo por despliegue;
custom no hereda carreras UPEC. Se rechazan estructura desconocida, duplicados,
HTML/control, codigos invalidos y relaciones a dependencias inexistentes/externas.
Una institucion de investigacion puede clasificar por dependencias sin carreras.

Providers callable compartidos alimentan modelos, registro/perfil, admin de
perfiles y horarios, solicitantes/beneficiarios/participantes de reservas,
actividades, periodos e indicadores. Se elimina el catalogo duplicado del modelo
UserProfile y sus consumidores directos. Los codigos de tipo de usuario se
conservan; etiquetas/procedencia interna utilizan siglas configuradas. Externos
conservan organizacion propia. No se modifican grupos, permisos, User o OAuth;
clasificar no verifica pertenencia ni concede privilegios administrativos.

auditar_catalogo_institucional descubre los doce campos que usan proveedores y
compara codigos/relaciones mediante conteos sin escribir datos ni exponer
personas. La base de desarrollo no presenta incompatibilidades. Codigos
retirados pueden conservarse como historicos para no reescribir reportes;
registro/perfil/otra_carrera solo seleccionan carreras academicas. Quien tiene
carrera obligatoria debe actualizar una carrera historica antes de reservar.
UserProfile.clean rechaza cruces de facultad/carrera; el periodo utiliza la
misma politica de carrera requerida.

Migracion 0198_catalogo_academico_configurable: diecisiete cambios de estado de
choices/etiquetas, SQL no-op adelante y atras. Se restauro el dump privado M01
en una base temporal y MigrationExecutor ensayo 0197 -> 0198 -> 0197 -> 0198.
Hashes identicos de datos (excepto registro de migraciones), columnas, indices
y claves en 135 tablas. Se elimino la base temporal; evidencia resumida ignorada
en tmp/evidencia-migracion-catalogo.json. 0198 se aplico en desarrollo; no se
reescribieron tablas o registros de negocio. La puerta M01 institucional sigue
abierta, sin copia externa, roles separados o topologia de contingencia probada.

Ocho pruebas nuevas cubren UPEC, universidad propia, investigacion sin carreras,
externos, cruces/carreras ajenas, admin/modelos/vistas, retiro historico, auditoria
sin escrituras y configuracion invalida/contrato sin Django. La primera suite
focalizada amplia paso 57 casos; el ultimo ajuste de compuerta paso 36 casos.
La prueba de arranque invalido revelo que Django evaluaba choices antes del
diagnostico. Se interrumpio la corrida integral y se corrigieron los providers
para permitir reportar E001/E002 y detener el servicio. La politica mantiene
validacion directa. Los cuatro arranques en procesos independientes ahora
confirman resultado esperado, incluida configuracion invalida rechazada.

La correccion final paso 42 pruebas focalizadas y se inicio una nueva suite
integral unica sobre esos providers. No se ejecutan suites Django simultaneas.

Ruff, check y migraciones sin cambios inesperados correctos. Servidor unico
reiniciado; diez recorridos HTTP 200, incluido PDF con SAMEORIGIN. Suite integral
final cerrada con **837 pruebas, OK (1 omitida), 858.312 s**.

M02.1 sigue abierto: calendario/niveles, pertenencia/roles verificados,
catalogos/tema administrables y contenido editorial. Referencia tecnica en
docs/catalogo-academico-institucional.md. Mantener compatibilidad de rutas de
providers usadas por migraciones al empaquetar o extraer apps posteriormente.

Revision de politica pendiente explicita: cotizaciones.clasificar_usuario y
clasificar_reserva usan el tipo declarado y conservan fallback UPEC por texto
de institucion; tambien existen etiquetas UPEC en tarifas/asistente. No se
cambia financiacion en este bloque. Revisar acreditacion/roles, procedencia y
segmentos historicos antes del uso comercial; no decidir derechos por marca.

La reversa ensayada tiene datos UPEC compatibles. Antes de volver a una version
anterior despues de incorporar codigos propios, auditar datos contra su catalogo
y conciliar operaciones posteriores; una reversa SQL no-op o cambiar de rama
no convierte esos codigos ni acredita compatibilidad funcional automaticamente.

Validacion integral final: **Suite completa: 837 pruebas, OK (1 omitida),
858.312 s**. Cuatro arranques independientes confirmados; 42 pruebas focalizadas
finales, auditoria de doce campos compatible, migracion/reversa en copia y
diez recorridos HTTP correctos. Ruff, check, makemigrations --check, 44 enlaces
locales y git diff --check correctos. Publicar en reestructura-modular;
integracion-version2-funciones permanece intacta en 654bd1a4. Siguiente bloque:
calendario/niveles y politicas acreditadas de pertenencia/roles, sin declarar
M02.1, M01 institucional o perfiles comerciales completos.


## 134. M02.1: niveles institucionales y propuesta historica de avance

16 de septiembre de 2026. Continuacion autorizada en reestructura-modular desde
95e43541; integracion-version2-funciones permanece en 654bd1a4.

Se separaron los niveles de la constante UserProfile y de la inferencia por
texto semestre. apps/core/niveles.py define el contrato puro inmutable:
niveles activos, historicos, niveles estudiantiles y rutas de avance explicitas
sin ciclos ni bifurcaciones. config/niveles.py carga ACADEMIC_LEVELS_JSON,
valida limite/formato JSON y selecciona el perfil UPEC o uno propio vacio.
El adaptador presentation/niveles comparte opciones evaluadas al consultar,
sin consultas de arranque ni dependencias de verticales.

UPEC conserva sus veinte codigos/etiquetas, diez niveles estudiantiles y avance
de semestres; el decimo no se transforma en tesis. Perfil y formulario validan
pertenencia al catalogo; el modal deja de filtrar por la palabra semestre y
ofrece años/trimestres configurados. Admin, participantes, reservas y periodos
usan los mismos proveedores. E003 permite diagnosticar y rechazar arranque
invalido; las decisiones de politica usan validacion estricta.

La propuesta solo toma una vinculacion activa de periodo publicado/cerrado,
mismo tipo y ambito, con version vigente terminada antes de iniciar el actual.
Se ordena por fecha real de cierre e ignora futuro/inactividad/borradores.
El avance requiere periodos ordinarios y misma carrera actual. El estudiante
confirma o corrige; no se reescribe su vinculacion anterior ni se asignan roles.

Auditor ampliado: dieciseis campos de facultades, carreras y niveles compatibles
en desarrollo; ningun dato personal expuesto ni escritura por el auditor.
0199_niveles_academicos_configurables contiene cuatro AlterField de choices,
todos no-op SQL. Ensayo en copia protegida M01: 0197 -> 0198 -> 0199 -> 0198 ->
0199, 135 tablas con hashes de datos, columnas, indices y claves identicos en
todas las etapas, excepto django_migrations por diseño. Copia temporal
eliminada; resumen ignorado tmp/evidencia-migracion-niveles.json. Migracion
0199 aplicada en desarrollo. Reversa compatible UPEC; no convierte niveles
propios al regresar a codigo anterior. Auditar y conciliar escrituras posteriores.

Siete pruebas nuevas: UPEC, años/trimestres con modelo/admin/UI, avance y
correccion con historial intacto, vinculaciones futuras/inactivas/otra carrera,
institucion sin niveles, retiro historico/auditoria sin escrituras y configuracion
invalida/contrato sin Django. Pruebas focalizadas iniciales: 48 OK; ajuste final
de exclusión de borradores: 10 OK. Cuatro procesos de arranque independientes
confirmados. Servidor reiniciado y diez recorridos HTTP 200, incluido PDF valido
con SAMEORIGIN. Ruff, check y makemigrations --check correctos.

Suite completa: **844 pruebas, OK (1 omitida), 746.823 s**.
Ruff, check, ausencia de migraciones inesperadas, cuatro arranques
independientes, auditoria de dieciseis campos, reversa en copia, diez
recorridos HTTP y 53 enlaces locales correctos. Bloque preparado para
commit/push en reestructura-modular; base estable sin cambios.

Documentacion: docs/niveles-y-avance-institucional.md y enlaces de arquitectura.
M02.1 sigue abierto: calendario/ciclos/ambitos y configuracion regional,
pertenencia/roles verificados, catalogos persistentes y contenido editorial.
No se cambia financiacion/cotizaciones ni los permisos, tablas o repositorio.
Las rutas de progreso por planes simultaneos necesitan relacion/versionado
explicitos; no se infieren desde un nombre. M01 institucional no queda cerrado.


## 135. M02.1: politica del calendario institucional compatible

16 de septiembre de 2026. Continuacion autorizada desde 2dcf4931 en
reestructura-modular. Base estable integracion-version2-funciones sin cambios.

apps/core/calendario.py define ciclos, ambitos activos/historicos, ambitos de
asociacion automatica, valores predeterminados y limites de semanas en un
contrato inmutable sin Django/verticales. Tres tipos semanticos estables:
ordinario, extraordinario e interperiodo. config/calendario.py selecciona
perfil UPEC preservado o neutro propio y carga ACADEMIC_CALENDAR_JSON.
Rechaza JSON duplicado, claves desconocidas, HTML, solapamientos y rangos fuera
de 1..24; E004 diagnostica y bloquea el arranque normal. No cambia configuracion
regional, permisos, roles, afiliacion ni financiacion.

El modelo de periodos utiliza proveedores compartidos y defaults evaluados al
consultar. La relacion ciclo/tipo se valida por politica, admitiendo C ordinario
si esta configurado. Periodos existentes pueden conservar codigos historicos;
los nuevos requieren activos. Las restricciones fisicas 1..24 permanecen.
Consultas para_fecha ordenan por inicio real de version vigente, no por ciclo
alfabetico. QuerySet.operativos comparte filtros entre perfil, reservas y
propuestas; detalle del asistente usa el mismo subconjunto. Relacion explicita
de actividad/periodo conservada; ambitos vacios detienen asociacion automatica,
no son una deshabilitacion de modulo ni prohibicion de reservas.

Generacion administrativa de semanas valida periodo/version y omite configuracion
invalida. Sigue idempotente, conserva semanas y permisos existentes. Reporte
ofrece semanas del periodo seleccionado o maximo institucional. Nuevo auditor
auditar_calendario_institucional muestra solo conteos y falla por codigos,
relaciones ciclo/tipo, limites o semanas fuera de plan/fechas. Desarrollo:
un periodo y dieciseis semanas compatibles; auditor academico mantiene dieciseis
campos compatibles. Auditores no escriben ni muestran personas.

0200 cambia choices/defaults de tres campos, no-op SQL en UPEC y propios.
Ensayo en copia protegida M01: 0197 -> 0198 -> 0199 -> 0200 -> 0199 -> 0200;
datos de 135 tablas, columnas, indices y claves identicos salvo django_migrations
por diseño. Copia temporal eliminada; resumen ignorado en
tmp/evidencia-migracion-calendario.json. Aplicada 0200 en desarrollo. Antes de
regresar a version anterior tras nuevos ciclos/ambitos propios, auditar contra
su politica y conciliar operaciones posteriores; no convertir codigos con ramas.

Seis casos nuevos: UPEC preservada; tres trimestres en admin/perfil/reserva;
seleccion por fechas; semanas idempotentes e invalidas; retiro/historia y
subconjunto operativo; configuracion invalida/contrato sin Django. Primera
focalizada detecto assertion de initial callable, corregida a valor evaluado
de BoundField. Focalizada final: 46 pruebas OK, 34.313 s. Cuatro arranques
independientes confirmados y SQL no-op en tres perfiles validos. Ruff, check,
makemigrations --check y diez recorridos HTTP 200, PDF valido con SAMEORIGIN.

Suite completa: **850 pruebas, OK (1 omitida), 892.496 s**.
Seis casos nuevos, 46 pruebas focalizadas y 14 tras el ultimo ajuste;
cuatro arranques
independientes, migracion/reversa en copia de 135 tablas, ambos
auditores, diez recorridos HTTP, Ruff, check, migraciones sin cambios
inesperados, 61 enlaces locales y diff correctos.

Revision final de altas: un periodo nuevo con PK manual podia eludir la
exigencia de ciclo/ambito activo. Se cambio la distincion a _state.adding y se
agrego el caso con PK manual al retiro historico. Se interrumpio la primera
integral; nueva focalizada de catorce pruebas OK, 7.463 s, Ruff y ausencia de
migraciones inesperadas correctos. Integral final iniciada sobre esa correccion.
El campo/SQL de 0200 no cambia; la reversa en copia sigue siendo la misma.

Referencia: docs/calendario-academico-institucional.md. M02.1 continua con
configuracion regional, pertenencia/roles verificados, catalogos persistentes
y editorial. Calendarios anuales >24 semanas requieren esquema y recuperacion;
relacion/prioridad por programa/unidad necesita contrato explicito. M01
institucional sigue abierto; no mover datos ni afirmar aislamiento comercial.


## 136. M02.1: configuracion regional institucional y agendas civiles

Desde edca93a6 se separan idioma/zona en contrato puro, builder de entorno y
adaptadores. INSTITUTION_LANGUAGE_CODE/TIME_ZONE conservan es-ec y
America/Guayaquil tambien en custom sin override; no cambia agendas por perfil.
Valores invalidos fallan antes de modelos; E005 valida settings y USE_TZ/I18N.
HTML y calendarios consumen idioma/zona; hoy usa reloj institucional con Intl,
no la fecha del dispositivo. Tarjetas/CSV interpretan timestamps en esa zona.
No hay traduccion completa del portal: editorial/negocio espanol permanece.

Reserva usa zona institucional para propiedades de inicio/fin y localdate
para validar fecha pasada/fallback de duracion. Conversion civil rechaza
extremos inexistentes/duplicados y saltos dentro de reserva diaria. API valida
todas las sesiones antes de escrituras, rechaza offsets de cliente, convierte
plazos de servicio con zona institucional. Lectura historica preservada.
Calendario puede mostrar bloques de transicion; API no los confirma. Sin fold
persistente no se ofrecen las dos ocurrencias de una hora repetida.

Nuevo auditar_configuracion_regional, solo conteos y sin escrituras/personas.
Zona candidata se compara bajo configuracion actual; error si cambia instantes
o hay horarios incompletos/no representables. UPEC: 103 reservas, cero conflictos.
No certifica bloqueos/servicios/integraciones; conciliar dominios antes de cambiar.
No nuevas migraciones; 0200 permanece. No cambia timestamps UTC o datos publicados.

Diez casos nuevos; focalizada final 92 OK, 34.140 s y nueve tras ultimo ajuste.
Primera ejecucion detecto cache build distinto entre JS y template; sincronizado.
Validacion de idioma trasladada al builder para evitar que Django evaluara
traducciones invalidas antes de E005. Rechazo de formato en-12 evita locale
invalido en Intl. Seis arranques independientes: UPEC, UTC, Bogota, Madrid,
idioma inexistente y zona inexistente. Ruff, check, makemigrations y cuatro
archivos JS correctos; diez recorridos HTTP, incluido PDF SAMEORIGIN, OK.

Suite completa: **860 pruebas, OK (1 omitida), 865.210 s**.
Diez casos nuevos, 92 pruebas focalizadas y nueve tras ultimo ajuste;
seis arranques independientes, auditor regional de 103 reservas compatible,
diez recorridos HTTP, PDF SAMEORIGIN, cuatro archivos JS, Ruff, check,
makemigrations sin cambios, 69 enlaces y diff correctos.

Referencia: docs/configuracion-regional-institucional.md. Siguiente M02.1:
pertenencia/roles verificados y segmentacion historica de tarifas, luego
catalogos persistentes y tema/editorial. M01 institucional sigue abierto;
no mover datos ni afirmar aislamiento real. Base estable conservada.

## 137. M02.1: interfaz en espanol e ingles por navegador

Desde 15a02d35 se incorpora LocaleMiddleware despues de sesiones y antes de
CommonMiddleware. Selector ES/EN compartido en cabecera publica y administrador,
POST protegido por CSRF, destino seguro mediante set_language de Django,
preferencia anual HttpOnly/SameSite=Lax y Secure en settings de produccion.
Conserva URL, query y ancla; sin i18n_patterns ni cambios de rutas de negocio.
Visor conserva modulo/recurso activo via ?recurso=<id>#modulo existente;
portada elimina seleccion anterior, sin guardar formularios ni PII en storage.
Dos clientes conservan preferencias independientes y la sesion no se pierde.

Presentacion regional distingue idioma personal de zona institucional. Elegir
ingles no modifica INSTITUTION_TIME_ZONE, timestamps, perfil, permisos o datos.
Default espanol conserva formato regional institucional. Sin nuevas migraciones;
0200 y las tablas de negocio permanecen como estaban.

8430 mensajes por idioma en locale/es y locale/en, PO/MO publicados juntos.
Catalogo unico django para templates/Python/JavaScript, endpoint con idioma
explicito, cache privada y Vary Cookie. Catalogo admite gzip/Vary Accept-Encoding
para reducir descarga en movil. Helper HTML traduce solo fragmentos literales
y atributos presentacionales, escapa traducciones y conserva valores
interpolados; las interpolaciones siguen requiriendo escape de quien las construye.
Si falla el catalogo JS, la interfaz opera con textos fuente. Documentos
independientes cargan helper/catalogo, lang actual y no duplican navegador.

Adaptadores core traducen etiquetas, ayudas, errores y opciones estaticas de
formularios sin alterar claves; conserva grupos y opciones de modelos. Bases
admin propias traducen fieldsets/forms/inlines por peticion sin tocar metadata
de modelos o permisos. Avisos y etiquetas de agenda se localizan al presentar;
codigos, nombres de recursos, solicitantes y fechas se conservan.

Catálogos preparados con asistencia local Argos/OPUS-MT y glosario revisado;
no se enviaron datos de usuarios a un traductor ni hay llamadas de traduccion
en runtime. Herramientas/modelo solo tmp ignorado, sin nuevas dependencias de
produccion. Revision de cifras y marcadores; no certifica revision linguistica
especializada de todos los textos cientificos. Nombres, contenido editorial,
productos, resultados y archivos subidos conservan idioma original. Nuevas
versiones de contenido requieren redaccion y revision, no duplicacion automatica.

Compilador scripts/compilar_idiomas.py usa biblioteca estandar, genera GNU MO
y verifica duplicados, vacios, fuzzy, contexto/plurales y marcadores nombrados;
--check detecta catalogo obsoleto. Pruebas cargan MO con GNUTranslations y Django.
Versiones JS invalidadas; build reserva 20260916-idiomas-v141 coherente con HTML.
Pruebas previas de contrato ajustadas para selector independiente y etiquetas
gettext, conservando unicidad del formulario de reserva, IDs y valores.

Catorce casos nuevos: preferencias, sesion/cookies, CSRF, idiomas/metodos
invalidos, destinos externos/HTTP downgrade, cache/catalogos, ocho entradas
publicas, administrador/permisos/datos, cuatro tipos de unidad, region, grupos
de opciones, GNU MO actualizado, escape y datos en helper JS, error de reserva.
Chrome headless verifico portal/lacteos, ES/EN y 1366/390/360 px sin errores JS;
selector cabe. Se comprobo retorno al mismo producto y modulo tras cambio de idioma.
Browser interactivo no disponible; se uso Chrome aislado sin perfil personal.
Plantillas ES/EN y JS correctos, Ruff y makemigrations sin cambios.

Suite completa: 874 pruebas, OK. Una prueba omitida; 1573.894 segundos.
Ruff, catalogos MO y 75 enlaces locales correctos; Chrome ES/EN en escritorio y movil.

Primera suite integral detecto dos comparaciones de etiquetas crudas en
plantilla y mapa de subtipos JS; ajustadas para translate/gettext conservando
vocabulario neutral y valores. Focalizada final: 21 casos OK, 8.496 s.
Revision adicional detecto riesgo de tratar atributos partidos por interpolacion
como texto. Helper conserva estado de etiqueta/comilla entre fragmentos; prueba
envenena traducciones de name/value y exige IDs/cantidades intactos, tambien con
nombre de etiqueta dinamico. Focalizada de 21 OK (8.374 s) y 14 tras ultimo ajuste
OK (8.806 s). Suite reiniciada despues del ajuste; nunca tomar corrida interrumpida
como validacion integral.

Referencia: docs/internacionalizacion-es-en.md. Siguiente M02.1 permanece
pertenencia/roles verificados y tarifas historicas, catalogos persistentes y
editorial. M01 institucional pendiente; no trasladar tablas ni afirmar
aislamiento comercial. Base estable conservada; publicar en reestructura-modular.


## 138. Selector ES/EN en barra verde superior (2026-09-16)

El selector de idioma se solapaba con Noticias y las acciones de usuario.
Se mueve al extremo derecho de la barra verde, junto a Contacto, y se retira
de nav-tools. El administrador mantiene su selector independiente.
La barra superior queda visible en movil, con Contacto e idioma; el menu
principal y las notificaciones ajustan su desplazamiento por los 40 px
adicionales. Encabezado compartido, sin duplicar formularios ni rutas.
CSS versionado y collectstatic ejecutado. Chrome aislado comprueba cambio
ES/EN y retorno al mismo recurso, sin errores JS, en 1366/1200/1024/768/390/360 px.
Selector dentro de barra verde y menu movil debajo del encabezado.
Suite completa: 874 pruebas, OK. Una omitida; 526.272 segundos.
Plantillas ES/EN, JavaScript y 75 enlaces locales correctos.


## 139. Selector de idioma compacto (2026-09-16)

Se recupera la altura inicial de 32 px de la barra verde. Selector del portal
con botones de 22 px, letra de 10 px y relleno de 1 px: caja total de 26 px
que cabe dentro de la barra sin ampliarla. Se mantienen foco y estado activo.
Menu movil, contenido y notificaciones ajustan sus desplazamientos a la
barra mas delgada. Admin sin cambio. CSS versionado v3 y collectstatic.
Suite completa: 874 pruebas, OK. Una omitida; 445.969 segundos.
Chrome verifica ES/EN en 1366/1200/1024/768/390/360 px sin desbordamiento
ni errores JavaScript; conserva modulo y recurso abiertos.
Plantillas ES/EN, scripts y 75 enlaces locales correctos.


## 140. Estado de planificacion y auditoria responsive (2026-09-16)

Auditoria sobre d0d2c057. No cambia codigo, esquema o datos. Plan funcional
1-7 integrado, con levantamiento/publicacion tecnica institucional pendientes;
no equiparar catalogo completo a todos los procesos configurados. Ruta modular
en M02.1, M01 institucional abierto y extraccion de apps/datos no iniciada.
INSTALLED_APPS mantiene webcitt como unica app propia de negocio.
Chrome aislado: 13 rutas publicas x ES/EN x 7 anchos (360/390/768/1024/1200/1366/1920),
182 combinaciones HTTP 200 sin errores JS. Selector y cabecera anonima sin
solapamiento. 36 combinaciones tienen desplazamiento horizontal: login 360/390
(10 px por row con margen negativo) y cuatro catalogos 768/1024/1200/1366
(3/135/91/50 px por pseudoelementos decorativos). A 1200 se reprodujo scrollX=91;
desactivar pseudo solo en diagnostico recupera 1200 y scrollX=0. No se aplica
correccion en esta auditoria. Priorizar arreglo y recorridos autenticados de
reservas/calendario/panel/admin/modales antes de dar responsive por cerrado.
30 pruebas focalizadas OK, 29.287 s. Check y makemigrations sin incidencias.
Suite completa vigente: 874 pruebas, OK, una omitida, 445.969 s (bloque 139);
no nueva suite integral en entrega documental. Evidencia/capturas en tmp ignorado.
Referencia: docs/estado-plan-y-responsive-20260916.md.

## 141. Responsive publico y autenticado corregido (2026-09-16)

Continuacion de 140 sobre bd5a96e5. Rejillas locales de acceso/registro y Perfil
coherentes con columnas Bootstrap; filas anidadas sin desbordamiento. Decoracion
de los catalogos limitada al componente. Menu plegable por debajo de 1280 px
evita choque con Noticias al autenticarse. Versiones CSS renovadas; selector
compacto en barra verde conservado. No modifica modelos, rutas, permisos o datos.

Chrome ES/EN, siete anchos 360/390/768/1024/1200/1366/1920: 182 combinaciones
publicas y 574 autenticadas, cero desbordamientos/choques de cabecera/errores JS.
Cuatro perfiles en base temporal unica: estudiante, docente, coordinacion y
administrador. Perfil, edicion/modal, ficha, cinco paneles de reservas, gestion
y admin segun rol. Base y sesiones temporales retiradas; base activa intacta.
La inspeccion de paneles mide presentacion; no envia una reserva ni equivale a
recorrer sus pasos reales. Detalle con 30 recursos desplazable internamente
desde 1024; en movil expande el contenido dentro del asistente desplazable.
PDF: 14 casos, documento valido, misma pestaña, modal ajustado y cierre Escape.
Cambio ES/EN conserva modulo y recurso; apertura de menu movil comprobada.

Plantillas ES/EN, JavaScript, Ruff webcitt/config/apps y Django check correctos;
makemigrations sin cambios. No certifica todas las pantallas, dispositivos
fisicos, zoom, orientacion o teclado. Evidencia/capturas en tmp ignorado.
M02.1 sigue en curso: continuar pertenencia/roles y tarifas historicas;
M01 institucional sigue abierto antes de trasladar datos. No extrae apps.
Referencia: docs/responsive-portal-y-operacion.md.

Suite completa: 874 pruebas, OK. Una omitida; 1115.434 segundos.


## 142. Politica neutral y delegaciones operativas seguras (2026-09-16)

Continuacion M02.1 sobre 52bd2823. Nucleo apps/core/roles sin Django/modelos:
modulos/roles conocidos, recomendaciones expresas por nombre, validacion JSON
estricta y resolucion de delegaciones. Adaptador de settings y configuracion
OPERATIONAL_ROLES_JSON por instalacion; duplicados/codigo/tipos invalidos
rechazados. Check slcid.E006. Defaults conservan recomendaciones anteriores;
configuracion expresa sustituye defaults, no asigna cuentas ni borra matrices.

Corrige bool("false") que concedia acceso y .values() sobre JSON de tipo errado
que podia romper la validacion. Solo true/false, claves conocidas y objeto JSON.
Al leer matriz invalida, deniega completa incluso si fue escrita sin full_clean.
Modelo muestra error de campo; tres errores traducidos ES/EN y MO compilados
(8433 mensajes cada idioma). Cuenta inactiva o sin guardar denegada en helpers,
incluso principal/superusuario. Responsabilidad desactivada revoca operaciones.
Previsualizacion del formulario conserva matriz al desactivar: no autoriza.
Asignacion expresa a la unidad sigue independiente del tipo declarado/nombre
institucional; usuarios ajenos no reciben privilegios.

19 pruebas nuevas: rechazo de datos corruptos, false expreso, independencia
Django/modelos, configuracion inmutable, endpoint real 403, revocacion,
reactivacion y alcance en cuatro tipos de unidades. 35 focalizadas OK, 21.475 s;
19 nuevas en version final OK, 0.589 s. Auditoria activa solo lectura: cero
matrices invalidas, roles desconocidos o delegaciones activas de cuentas
inactivas. No altera base activa, esquema, permisos Django o usuarios.
Ruff/check y compilacion ES/EN correctos; makemigrations sin cambios.

No cierra M02.1: verificar pertenencia y tipos declarados con trazabilidad y
conservacion historica, luego tarifas historicas. Clasificacion academica y
segmentos tarifarios actuales aun no son prueba verificada de pertenencia.
M01 institucional sigue abierto; no extrae modelos/apps ni traslada datos.
Referencia: docs/roles-y-delegaciones-operativas.md.

Suite completa: 893 pruebas, OK. Una omitida; 1047.899 segundos.


## 143. Revision institucional de pertenencia y tipo declarado (2026-09-16)

Continuacion compatible M02.1 sobre 271ca634. apps/core/pertenencia define
identidad permitida y huella estable sin Django/modelos. Servicio bajo usuarios
mantiene decisiones separadas del perfil declarado; no presume pertenencia por
correo, siglas escritas, acceso social o tipo docente. Solo cuenta activa staff
con permiso especifico revisar_pertenencia_institucional y lectura/cambio de
perfil puede revisar. Sin autorrevision, incluso superusuario; se releen cuenta
y permisos al escribir para no usar concesiones revocadas en cache.

Admin de perfiles distingue Datos completos de Verificacion institucional.
Revision por perfil: aprobar/rechazar/revocar, fundamento/referencia obligatorios
y vigencia opcional. Formulario POST con CSRF, huella de identidad/ultima decision,
transaccion y bloqueo usuario/perfil; envio viejo o doble envio se rechaza.
Errores de full_clean del perfil se aplanan como errores generales; el formulario
no tiene esos campos. Campos readonly seguros tambien al crear un perfil nuevo.
Historial paginado a veinte decisiones y consulta independiente de solo lectura
para revisores autorizados, dentro de Usuarios, responsables y acceso.

Migracion 0201 crea VerificacionInstitucional y cinco permisos Django; no
transforma perfiles ni reservas, no aprueba cuentas ni concede grupos/roles.
Historial protege perfil/revisor con FK PROTECT: desactivar cuentas es posible,
borrarlas con historial no. API ordinaria impide creacion directa, edicion,
borrado y bulk_create; se agrega cada decision desde servicio. No confundir
proteccion de API con inmutabilidad frente a SQL/DB privilegiada/codigo que la
eluda. No deshacer migracion si ya tiene decisiones: borraria el historial.
Con tabla vacia, codigo anterior no necesita leerla. Con decisiones, codigo viejo
no conoce las FK y borrar cuentas referenciadas puede dar IntegrityError: retorno
debe conservar historial y llevar parche de retencion/bloquear esas eliminaciones.
No certificar todas las acciones antiguas sobre esquema posterior.

Identidad incluye codigo institucional, usuario, nombres, correo, tipo,
procedencia, facultad, carrera y documento. Cambio actual, catalogo invalido,
vencimiento o cuenta inactiva deniega estado verificado. Si vuelve exactamente
la identidad revisada y ultima decision sigue aprobada/vigente, conserva revision;
no se registra cada edicion del perfil. Nivel periodico/telefono/avatar/biografia
no se revisan en pertenencia. Tipos internos deben usar procedencia configurada.
Rechazo/revocacion mantienen las aprobaciones anteriores como evidencia, sin
volver a utilizarlas como ultima decision.

Perfil muestra estado ES/EN sin fundamento/referencia/revisor/identidad historica.
Perfil/edicion/revision no-store. La aprobacion no asigna staff/grupos/permisos
operativos ni cambia reservas/cotizaciones anteriores. Las reglas antiguas de
autoria docente declarada/atajos is_staff y tarifas aun no exigen esta aprobacion: conectar en
el siguiente bloque, con transicion explicita y conservacion historica.

28 pruebas nuevas y finales OK, 2.383 s: aprobacion/evidencia, rechazo/revocacion,
vigencia, cambios por queryset, cuenta/revisor inactivos, cache de permisos,
autorrevision, editor sin permiso, revision sin lectura, CSRF, envio viejo,
huella no ASCII rechazada sin TypeError (suite inicial detenida y reiniciada),
alta admin, perfil POST malicioso, errores de campos, historial protegido,
paginacion, independencia del nucleo y cotizacion historica intacta. MO ES/EN
compilados, 8471 mensajes cada idioma. Ruff/check/makemigrations correctos.
Chrome aislado: 28 combinaciones de Perfil/formulario, dos roles, ES/EN y siete
anchos. Sin errores JS ni desbordamiento; boton antes recortado corregido a
posicion visible y altura minima de 44 px. Base y sesiones QA retiradas.
Cabecera compartida admin todavia recorta marca/herramientas en movil: medir
sus controles y corregir antes de certificar toda la cabecera. No es overflow
del contenido nuevo. Revision visual en 360 y 1366 incluida.

M02.1 en curso, M01 institucional abierto. No extrae apps ni traslada datos.
Referencia: docs/verificacion-institucional.md.

Migracion 0201 aplicada localmente despues de validar. Auditoria agregada:
34 perfiles, 27 completos, 31 internos con procedencia no canonica respecto
de siglas configuradas; revisar/corregir con evidencia, sin normalizacion masiva
ni aprobacion automatica. Cero decisiones y cero concesiones explicitas del
permiso a usuarios/grupos; cinco permisos nuevos. Base QA/sesiones retiradas,
ninguna cuenta real aprobada ni datos personales modificados por este bloque.

Suite completa: 921 pruebas, OK. Una omitida; 909.938 segundos.


## 144. Pertenencia efectiva en autoria y tarifas; cabecera admin responsive

16 de septiembre de 2026. Continuacion compatible de M02.1, rama
reestructura-modular; base integracion-version2-funciones conservada.

usuarios/pertenencia.py consulta perfil/usuario actuales y ultima decision;
resumen minimo sin identidad historica, documento, referencia o fundamento.
permisos.puede_crear_guias_unidad centraliza editor/reserva/visualizador:
docente verificado vigente o permiso efectivo practicas de esa unidad.
Staff no concede autoria, lectura/descarga/listado privado ni fuentes del
formulario, detalle o planificacion de otra unidad. Operador conserva su
delegacion; no obtiene tarifa interna por ella. Autor de guia existente
conserva correccion mientras estado editorial y cuenta activa lo permitan.

Tarifas nuevas verifican identidad vigente: estudiante/personal solo si
aprobado; externo aprobado sigue externo; pendiente/revocado/vencido/datos
modificados usa externo sin cambiar tipo declarado ni indicadores. Se retira
inferencia por texto UPEC/procedencia. Cotizacion registra pertenencia_tarifaria
version 1 con id de revision, estado, tipo/codigo/fecha/vigencia/segmento.
ES/EN explica la tarifa. Simulacion cliente usa segmento efectivo propio,
separado del tipo declarado para horarios/reportes.

Recalculo de cambio y liquidacion usan segmento emitido, luego tipo historico;
sin ambos, externo sin consultar perfil actual. Legado sin prueba usa version
0 historica_sin_revision, sin fabricar una aprobacion. Recalculo conserva
fundamento previo; un cambio operativo puede actualizar cantidades/horas y
tarifas vigentes, no es congelacion integral del tarifario ni factura definitiva.
Aprobar/revocar no modifica reservas/costos/cotizaciones anteriores.

Antes de crear, guia y reserva bloquean unidad, User y UserProfile con orden
comun; revision bloquea User/perfil. Cotejo bajo bloqueo detecta revocacion
durante validaciones y revalida autoria, sin crear actividad/reserva parcial.
Se detecto el posible cruce de FK al adquirir unidad/usuario en orden inverso;
suite inicial interrumpida y reiniciada con el orden comun antes del cierre.
No se certifican todos los escritores concurrentes o cambios de delegacion.

Cabecera Grappelli: marca sin recorte de 36px, filas hasta 1200px, header en
flujo y margen correcto del contenido; idiomas con botones estaticos visibles
sin heredar posicion absoluta. QA inicial descubrio botones ES/EN solapados y
padding sobrante, corregidos y reejecutados. Chrome final: 140 combinaciones,
cuatro estados (docente aprobado, pendiente, revocado, externo aprobado),
guias/reserva y admin/revision, ES/EN y siete anchos 360..1920. Sin errores JS,
desbordamiento o controles header admin recortados/solapados; capturas
revisadas en 360px. Titulo/subtitulo de modal reserva en ingles a 360px requiere
revision adicional del alto: no se certifica toda la interfaz responsive.
Base y sesiones sinteticas QA retiradas, base activa sin cambios.

13 pruebas nuevas de pertenencia/operaciones/cambios durante el envio, 4.357 s
en version final; 59 focalizadas anteriores, 22.541 s; suite anterior de
flujos guia/reserva/servicios, 218, revelo dos expectativas de transicion,
actualizadas y 105 reejecutadas OK. Identidades de fixtures acreditadas
explicitamente; identificar no aprueba y una reserva general pendiente
sigue cubierta. Catalogos ES/EN 8477 mensajes, Ruff/check/makemigrations,
plantillas y JavaScript correctos. Sin nueva migracion, sin roles/permisos
asignados en base activa, sin aprobaciones masivas.

M02.1 sigue abierto: configuracion editorial/persistente, consumidores de
marca/configuracion restantes. M01 institucional abierto antes de trasladar
datos; despues M02.2-M02.4 manifiestos/capacidades/contratos. Revisor debe
cotejar perfiles reales; 31 procedencias internas no canonicas del bloque
anterior no se normalizan automaticamente.
Referencia: docs/pertenencia-guias-y-tarifas.md.

Auditoria activa repetida: 34 perfiles, 27 completos, 31 procedencias internas
no canonicas, cero decisiones/cero concesiones explicitas de revision a
usuarios o grupos; cinco permisos del modelo. Servidor --noreload reiniciado
con codigo final y estaticos recogidos. Inicio/planta 200; perfil/revision
anonimos 302, sin autoria ni tarifa interna en contexto anonimo.

Suite completa: 934 pruebas, OK. Una omitida; 781.806 segundos.


## 145. Presentacion institucional administrable en app propia

16 de septiembre de 2026. Continuacion M02.1, reestructura-modular; base
integracion-version2-funciones conservada. No renombra repositorio, base,
tablas existentes o permisos heredados.

apps/configuracion_institucional es app Django instalada con dos modelos,
services/selectors, administrador, migracion, comando, plantillas y tests
propios. Codigo operativo sin imports webcitt/verticales; AUTH_USER_MODEL
atribuye responsables. Inventario agrega modelos_propios (tabla, archivo,
propietario, registro admin y permisos) sin romper contrato previo. Entradas
de portal son adaptadores; ORM operativo existente sigue en webcitt. Motor y
proceso compartidos: esto no asegura aislamiento total de fallos.

RevisionPresentacion conserva ocho campos publicos: nombres de sistema,
institucion, telefono, correo, ubicacion y dos rutas de logos instalados.
Borrador no modifica portal. Publicar crea snapshot nuevo y actualiza puntero
unico; recuperar crea otra publicacion sin borrar/reescribir historia. En uso
indica actual; Publicada es estado historico. Guardas save/update/bulk/delete y
admin sin change/delete; puntero no registrado ni permisos por defecto. SQL
privilegiado puede eludir guardas de aplicacion. No concede roles reales.

Comandos recargan actor activo staff y permisos, bloquean actor/puntero,
comparan base mostrada y base original del borrador. No publicar borrador
obsoleto aun modificando hidden; crear revision nueva. PK unica y savepoint
resuelven primera creacion concurrente. GET revisa, POST exige checkbox/CSRF,
PUT 405. Editor/publicador separados o una cuenta autorizada a ambas acciones.
Bloquear User no serializa todas las revocaciones SQL directas de grupos.

No cambia codigos, SMTP, dominios OAuth, credenciales, pertenencia, tarifas ni
catalogo academico. Texto plano, correo validado, logos locales png/jpg/webp
instalados; no HTML, controles, rutas remotas/absolutas/traversal, SVG o activo
ausente. Errores asociados a campos. Proyeccion coteja codigos de despliegue;
otra institucion no utiliza publicacion de esta base.

Middleware despues de Locale resuelve una identidad por solicitud; ContextVar
anidado reutiliza/reset incluso con excepciones. Base/checks/import sin SQL.
Proveedor opcional, cadena vacia usa despliegue; E007 valida app/proveedor sin
consultas. Invalidez o tabla ausente usa base y advertencia generica; savepoint
protege transaccion exterior. No oculta fallos globales de PostgreSQL. Auditor
explicito solo conteos/estado y falla ante inconsistencia sin datos privados.
Correo de reservas abre contexto fuera de HTTP; futuras tareas/PDF deben usar
con_presentacion_institucional. Contacto publico no altera remitente SMTP.

Marca dinamica en header/index/login admin y correos. Login conserva
AdminAuthenticationForm/vista Django, errores, widgets, CSRF y next seguro;
markup propio evita titulo congelado Grappelli. Login real rechaza next externo
y conserva fallback LOGIN_REDIRECT_URL. Botones publicar/social no heredan
ancho de icono; campos/logo caben 360px. Header reserva no encoge con cuerpo
largo; medicion espera fin de animacion.

16 nuevas pruebas: borrador/publicacion/recuperacion, permisos frescos/revocacion,
cuenta inactiva, historia, base obsoleta, formatos/extra fields, admin real y
CSRF/POST vacio, login real/CSRF/password/next, scope/reset/nested, checks sin
consultas, namespace ajeno, tabla SQL ausente/transaccion utilizable, mail real
locmem, PDF y auditor de inconsistencia. 16 finales OK (6.113 s); integracion
final tras mover templates/tests a la app, 40 OK (18.319 s). Fallos iniciales
de method decorator, expectativa redirect y encoding PowerShell de PO corregidos.
ES/EN 8510 mensajes; Ruff/check/makemigrations/templates de tres carpetas,
JavaScript y diff --check pasan.

Chrome final: 210 combinaciones, ES/EN, cuatro estados (docente aprobado,
pendiente, revocado, externo aprobado), siete anchos 360..1920; reserva/guias,
admin/revision pertenencia, historial/editor/lectura/confirmacion presentacion y
login anonimo. Sin errores JS, overflow o campos/controles medidos recortados o
solapados. Capturas ingles 360 login/confirmacion/reserva revisadas. Base y
sesiones sinteticas retiradas; ninguna cuenta real aprobada/modificada. No
certifica toda la interfaz, streaming/ASGI, dispositivos fisicos o carga masiva.

Migracion propia 0001 aplicar -> revertir -> aplicar en copia: 136 tablas
anteriores identicas en datos/esquema/indices/claves, dos nuevas vacias. Reversa
solo ensayada en vacio; despues de uso preservar/conciliar historia antes de
revertir. Codigo anterior compatible puede conservar tablas nuevas. Cambiar
rama no revierte datos/media; no limpiar ContentTypes/permisos automaticamente.

M02.1 abierto: editor/versionado catalogos academicos, paleta configurable y
consumidores editoriales restantes; M09 admin propio otras secciones. M01
institucional abierto antes de extraer datos. Despues M02.2-M02.4 manifiestos,
categorias y contratos. docs/presentacion-institucional-administrable.md.

Migracion 0001 aplicada en desarrollo despues de la suite, con dump previo
local ignorado y ACL solo operador/SYSTEM, checksum y catalogo verificado.
No se afirma restauracion integral de ese dump nuevo ni cierre de M01.
Comparacion activa: filas/esquema/indices/claves previos identicos; metadata
aditiva (dos ContentTypes, cinco permisos, una migracion). Cero revisiones,
publicaciones o concesiones explicitas reales; datos/permisos anteriores
conservados. Media no modificada. Auditoria previa de pertenencia conserva
34 perfiles, 27 completos, 31 procedencias no canonicas, cero decisiones y
concesiones explicitas. No autoaprobar/canonicalizar cuentas reales.

Servidor propio --noreload reiniciado con codigo final y dos estaticos recogidos.
Inicio/planta/login admin 200; perfil/listado/editor institucional anonimos 302.
Anonimo sin autoria y segmento externo. Formulario login conserva CSRF.
Avisos de tres overrides JS Django/Grappelli preexistentes en collectstatic;
no son archivos duplicados nuevos. No se hizo login con cuenta real.

Suite completa: 950 pruebas, OK. Una omitida; 925.918 segundos.

## 146. Catalogo academico administrable en app propia

M02.1 continua en apps/configuracion_institucional: paquete catalogos con
models/services/selectors/forms/admin, templates/static/tests propios y 0002.
Dos modelos nuevos: RevisionCatalogoAcademico y PublicacionCatalogoAcademico;
cuatro modelos propios en total. No extrae ORM operativo ni renombra CITT,
tablas, permisos o base. Sin imports operativos de webcitt/verticales.
versionado.py comparte guardas inmutables, autoridad fresca y bloqueo de
puntero con presentacion; rutas anteriores siguen compatibles.

Editor progresivo de dependencias, carreras, historicos y tipos que requieren
carrera. Un solo payload JSON de maximo 1 MB, sin miles de campos POST.
Interfaz con etiquetas/controles DOM seguros, filas adaptables, alta/retiro,
errores por campo y fallback sin JS. Hasta 200 dependencias internas mas
externo y 2000 carreras; normalizacion serializada conserva limite. No agrega
tipos de unidad ni edita niveles/calendario. ES/EN: 8556 mensajes.

Guardar requiere add; revisar/publicar requiere view + publicar_catalogo,
staff activo. Actor/permisos recargados bajo bloqueo; datos hidden no dan
autoridad. GET revisa y POST exige CSRF/checkbox/base vigente; PUT 405.
Historia inmutable y recuperacion mediante snapshot nuevo compatible. Modelo
puntero sin admin/permisos por defecto; QuerySet y save impiden alteracion
ordinaria. SQL privilegiado puede eludir guardas. No asigna permisos reales.

Transicion conservadora: mantener codigos previos aun sin uso. Retirar carrera
la conserva como historica. Reserva relacion carrera/dependencia para impedir
reclasificacion y reactivacion en otra dependencia; categorias historicas
heredadas sin relacion no pueden convertirse en carrera academica reutilizando
codigo. Para reclasificar usar codigo nuevo. Etiquetas actuales pueden cambiar
en reportes consultados: no se congelan etiquetas por registro ni reescriben
documentos archivados. Restauracion incompatible se bloquea; no merger silencioso.

Scope HTTP despues de Locale resuelve catalogo una vez, reutiliza anidados y
resetea incluso con excepciones. ACADEMIC_CATALOG_PROVIDER fijo/registrado,
opcional vacio; E008/checks validan despliegue sin SQL. DTO explicito permite
auditar propuesta en dieciseis campos sin publicar. Modo estricto del auditor
no certifica fallback; devuelve conteos, sin nombres/correos. Savepoint protege
transaccion exterior si falta tabla; no garantiza motor/proceso ante caida.
Proyeccion valida producto/institucion, estado y relaciones reservadas.
Base corrupta bloquea nueva publicacion y muestra motivo sin HTTP 500.

QA detecto que verificacion directa fuera de HTTP usaba catalogo de despliegue.
estado_verificacion y registrar_revision abren ahora ambito del catalogo;
la aprobacion sigue explicita y revisada, sin inferencia por marca/carrera.
Futuras tareas/importadores necesitan con_catalogo_institucional para operar
con la version publicada. No cache global entre solicitudes/usuarios.

19 pruebas nuevas cubren publicacion y perfil, retiro/reactivacion, instalacion
solo investigacion, referencias cruzadas/historicas, base obsoleta/hidden,
recuperacion, revocacion/cache/inactividad, guardas ORM, admin real/idiomas/CSRF,
limites de payload/codigos, namespace ajeno, context/reset/consultas, tabla
ausente, auditor estricto, conteos incompatibles y base corrupta. Integracion
final: 81 pruebas OK (22.479 s). Ruff/check/makemigrations/JS correctos.

Chrome: 224 combinaciones ES/EN, siete anchos 360..1920, cuatro estados de
pertenencia y recorridos reserva/guias/admin/verificacion/catalogos/login.
Editor sincroniza alta y retiro con payload; propuesta incompatible sin boton
confirmar. Sin errores JS, overflow o controles medidos recortados/solapados.
Capturas ingles 360 editor y ambas revisiones inspeccionadas. Base/sesiones
sinteticas retiradas; sin cuentas reales aprobadas ni normalizadas. No prueba
toda la interfaz, dispositivos fisicos, ASGI/streaming, carga masiva o WCAG.

Ensayo protegido 0001 -> 0002 -> 0001 -> 0002: 138 tablas anteriores identicas
en filas/columnas/indices/claves, dos nuevas vacias; copia retirada. Reversa
solo ensayada en vacio. Con historia preservar/conciliar antes de revertir.
Cambiar rama no revierte base/media; codigos nuevos requieren auditoria contra
proveedor anterior antes de volver al codigo previo. No limpiar ContentTypes.

Migracion 0002 aplicada en desarrollo tras suite y respaldo local protegido:
dump ignorado, ACL operador/SYSTEM, checksum y catalogo verificado. No se afirma
restauracion integral de este dump ni cierre de M01. Filas/esquema/indices/claves
de 138 tablas previas identicos; metadata aditiva esperada: una migracion,
dos ContentTypes y cinco permisos. Cero revisiones/publicaciones del catalogo
o concesiones explicitas nuevas reales; datos/permisos previos conservados.
Media no modificada. Auditor estricto: dieciseis campos compatibles, sin PII
ni escrituras. Servidor propio reiniciado --noreload y estaticos recogidos;
inicio/planta/login 200 y perfil/listados/editores anonimos 302 (ocho rutas).
Login conserva CSRF; anonimo sin autoria y segmento externo. Sin login ni
aprobacion de cuenta real. Tres overrides JS Grappelli preexistentes en
collectstatic, no duplicados nuevos.

M02.1 sigue abierto: persistencia de niveles/calendario, paleta y consumidores
editoriales restantes. Despues M02.2-M02.4 manifiestos/categorias/contratos; M09
admin propio de otras secciones. M01 institucional abierto: custodia externa
cifrada/inmutable, escritores, RPO/RTO, usuario DB minimo privilegio. No extraer
datos ni afirmar aislamiento o seguridad certificados. M11 infraestructura
independiente pendiente. docs/catalogo-academico-administrable.md.

Suite completa: 969 pruebas, OK. Una omitida; 979.411 segundos.

## 147. Niveles y rutas administrables con editor compartido

M02.1 continua primero con niveles/rutas; calendario persistente sigue despues.
apps/configuracion_institucional/niveles contiene modelos, servicios, lecturas,
forms y admin propios, templates/static/tests y 0003. RevisionNivelesAcademicos
y PublicacionNivelesAcademicos agregan dos modelos, seis propios total.
No extrae ORM operativo, renombra CITT ni cambia tablas/permisos existentes.
editor_revisiones.py comparte flujo admin con catalogos; formularios.py comparte
titulo/JSON; editor.css sustituye catalogos.css. Lectura comun reemplaza copia
especifica y confirmacion anterior sin consumidores retirada. URLs/imports
existentes de catalogos preservados. Sin imports operativos de verticales.

Editor progresivo: activos, checkbox estudiante, retiro historico, rutas
ordenadas con selectores y texto de compuerta. MAX 200 activos/historicos,
codigo 30 caracteres, JSON 100.000. Rechaza duplicados/desconocidos/HTML/rutas
ambiguas/ciclicas. Payload invalido conserva JSON visible, sin truncarlo;
fallback sin JS. DOM/textContent/Option, sin eval. ES/EN: 8590 mensajes.
Guardar add; publicar staff activo + view + publicar_niveles, autoridad fresca,
bloqueos de actor/puntero, CSRF/checkbox/base mostrada y original revalidados.
Historia inmutable, recuperacion nueva compatible, sin concesiones reales.
Todos los codigos previos se conservan aun sin uso; retirar como historicos.
Perfil estudiantil con nivel retirado necesita actualizarse para operar.

Ruta modificada cambia propuestas futuras, sin confirmar/autoavanzar estudiante
ni reescribir vinculacion previa. Confirmacion/correccion se mantiene. Rutas
disjuntas por codigo; finales/independientes/historicos no inventan saltos.
No planes simultaneos/bifurcaciones con mismo codigo sin relaciones explicitas.
Etiquetas actuales pueden cambiar en consultas; no se archivan por registro.

ACADEMIC_LEVELS_PROVIDER fijo, vacio usa despliegue; E009/E003 sin SQL.
Scope HTTP resuelve version una vez, reutiliza/reset anidados y excepciones.
Vigencia/propuestas/confirmacion/verificacion abren scope fuera de HTTP;
futuras tareas/importadores requieren con_niveles_institucionales. Namespace
ajeno no hereda publicacion. Fallback generico/savepoint no sostiene todo el
motor. Publicar audita propuesta explicita en dieciseis campos y resuelve
catalogo academico estricto; auditor CLI resuelve ambos proveedores estrictos
por alias. Incompatibilidad/tabla ausente/base corrupta no se certifican,
sin PII ni altas parciales. No serializa escritores/revocaciones SQL directos.

14 pruebas nuevas: UPEC y cuatro modelos/formulario, anios/trimestres/nivel
independiente, institucion sin docencia, retiro/reactivacion, codigos previos,
propuesta con confirmacion/historia, base obsoleta/recuperacion/guardas,
revocacion cache/inactividad, JSON/HTML/limites, admin ES/EN/CSRF/PUT/POST,
context/reset/checks/namespace, SQL tabla ausente/savepoint/base corrupta,
propuesta incompatible y revision explicita de estudiante fuera de HTTP.
Integracion: 89 OK (22.506 s); ajuste final de navegacion 14 OK (2.574 s).
Ruff/check/makemigrations/templates/JS OK.
Fixtures corregidos: datos incompletos/cache de perfil, cookie idioma, selector
submit global y etiqueta de modulo inexistente. Sin cuentas reales modificadas.

Chrome final: 296 casos ES/EN, siete anchos 360..1920 y cuatro estados
de pertenencia; reserva/guias/admin/verificacion/login, editor de catalogos y
niveles, historia y publicaciones compatibles/bloqueadas. Alta/ruta/retiro
sincronizan JSON; payload 201 niveles se mantiene visible/rechazado, sin
truncar. Textos ingles de nivel/remover verificados tras corregir dos ausentes;
suite inicial interrumpida y reiniciada para validar version final. Capturas
ingles 360 editor y vistas previas inspeccionadas. Sin errores JS, overflow,
recortes o solapamientos medidos. DB/sesiones QA retiradas, sin cuentas reales
aprobadas/normalizadas. No certifica toda la UI, dispositivos fisicos, ASGI,
streaming, carga masiva o accesibilidad completa.

Ensayo 0002 -> 0003 -> 0002 -> 0003 en copia: 140 tablas anteriores identicas
en filas/columnas/indices/claves y dos nuevas vacias; copia retirada. Reversa
solo vacia; tras uso preservar/conciliar historial. Cambiar rama no revierte
base/media; auditar codigos nuevos contra proveedor anterior. SQL privilegiado
puede eludir guardas. No limpiar ContentTypes/permisos automaticamente.

Migracion 0003 aplicada localmente despues de suite y respaldo protegido:
dump ignorado con ACL operador/SYSTEM, checksum y catalogo verificado. No se
afirma restauracion integral de este dump ni cierre de M01. Filas/esquema/
indices/claves de 140 tablas previas identicos; metadata aditiva esperada:
una migracion, dos ContentTypes y cinco permisos. Cero revisiones/publicaciones
de niveles o concesiones explicitas nuevas reales; datos/permisos anteriores
conservados. Media no modificada. Auditor estricto confirma dieciseis campos
compatibles y calendario anterior compatible, sin PII ni escrituras.
Servidor propio reiniciado --noreload, estaticos recogidos y diez rutas:
inicio/planta/login 200, perfil/listados/editores anonimos 302. Login conserva
CSRF, anonimo sin autoria y segmento externo. Sin login con cuenta real.
Tres overrides JS Grappelli preexistentes en collectstatic; no nuevos duplicados.

M02.1 sigue: calendario persistente, paleta y consumidores editoriales. M09
otras secciones; despues M02.2-M02.4 manifiestos/categorias/contratos.
M01 institucional abierto antes de extraer datos: escritores/custodios,
usuario DB minimo privilegio, RPO/RTO, copia externa cifrada/inmutable y
recuperacion aislada. M11 pendiente. docs/niveles-academicos-administrables.md.

Suite completa: 983 pruebas, OK. Una omitida; 1008.144 segundos.

## 148. Politica de calendario administrable, con historial y editor compartido

M02.1 continua sin trasladar ORM operativo. App configuracion_institucional:
calendario/models/selectors/services/forms/admin propios, plantillas/JS y 0004;
dos modelos nuevos (ocho propios en total), mismos flujos de catalogos/niveles.
Guardar crea borrador; publicar genera revision inmutable y cambia puntero
unico, con base esperada, permisos frescos, confirmacion POST/CSRF e historial
de lectura. Recuperar una publicada crea otra revision; no borra anteriores.

Editor progresivo para ciclos, ambitos, operacion, default y semanas. JSON unico,
maximo 100000 caracteres, claves duplicadas/desconocidas/HTML/booleanos/rangos
invalidos rechazados. POST rechazado conserva texto y desactiva guiado; manual
desconecta guiado para no sobrescribir ni truncar. ES/EN: 8622 mensajes; tipos
semanticos traducidos tras inspeccion visual. Etiquetas institucionales conservan
su contenido; no se traducen automaticamente registros de la institucion.

Core puro serializa nueve campos y valida transicion conservadora: todos los
codigos anteriores se mantienen activos/historicos; tipo de ciclo estable aun
sin uso. Auditor candidato explicito comprueba periodos, relaciones ciclo/tipo,
rangos 1..24 y semanas fuera de plan/fechas. Publicar no altera fechas oficiales,
periodos, semanas, reservas, vinculaciones ni restricciones de suspensiones.
Cambiar ambitos de operacion afecta seleccion automatica futura; lista vacia
no elimina relaciones explicitas. Sin prioridades inferidas por programa/unidad.

ContextVar publicado por solicitud, nested sin nuevas consultas y reset al salir.
Middleware agrega scope de calendario; periodo_vigente, resolver periodo reserva
y generar semanas lo abren tambien para llamada directa. Otros constructores,
defaults/forms/full_clean/tareas fuera de HTTP necesitan scope explicito con alias;
sin scope usan despliegue. No SQL durante import/checks. E004 valida base y E010
proveedor fijo/app instalada; cadena vacia desactiva proyeccion. Selector con
savepoint, fallback normal/aviso generico ante ausencia/corrupcion/identidad ajena;
auditor CLI estricto por alias falla en esos casos, no certifica fallback.

Permisos agregar/ver revisionpoliticacalendario y publicar_calendario. No concede
roles, pertenencia, grupos/permisos a cuentas reales ni verifica automaticamente
usuarios. Puntero sin admin/default permissions. Guardas save/update/bulk/delete
ordinarias; SQL privilegiado puede eludirlas. Lock serializa publicar politica,
no coordina todos los escritores externos/concurrentes de periodos/semanas.
Motor y proceso compartidos; M01/M11 abiertos, sin garantia de aislamiento total.

14 pruebas nuevas: cuatro instalaciones (UPEC, tres trimestres, instituto de ciclo
unico y centro sin asociacion automatica), continuidad/defaults/admin/reserva,
retiro/reactivacion, codigos/tipos, limites, generacion idempotente, autoridad
revocada, bases obsoletas, historia, CSRF/PUT, JSON, contextos/checks/corrupcion.
Integracion inicial: 53 OK (6.242 s). Ajuste final: 74 OK (9.537 s).

Ensayo 0003 -> 0004 -> 0003 -> 0004 en copia del dump M01 restaurado: 142 tablas
anteriores conservan filas/columnas/indices/claves (django_migrations cambia por
diseno), dos nuevas vacias. Copia retirada; reversa solo en vacio. No revertir
tras uso sin conservar y conciliar historial. Cambiar rama no restaura base/media;
nuevos codigos/limites necesitan auditoria contra proveedor/codigo anterior.

Chrome final: 370 casos ES/EN, siete anchos 360..1920, cuatro estados de
pertenencia; reservas/guias/admin/verificacion/login, catalogos/niveles y cinco
vistas de calendario. Alta/retiro de ciclo/ambito, operacion/default sincronizan
JSON. Payload 201 ambitos visible/rechazado y JSON manual con clave duplicada
conservado sin sobrescribir. Capturas ingles 360 editor y bloqueo inspeccionadas;
tipos semanticos traducidos. Primera corrida corrigio fixture Save Draft y
traducciones faltantes; final repetida OK. Sin errores JS, overflow, recortes o
solapamientos medidos. DB/sesiones QA retiradas; no cuentas reales aprobadas ni
roles concedidos. No certifica toda UI, dispositivos fisicos, accesibilidad,
ASGI/streaming, carga masiva ni aislamiento del proceso/motor compartido.

0004 aplicada localmente despues de suite y respaldo protegido: dump ignorado
con ACL operador/SYSTEM, checksum y catalogo verificado. No se afirma restauracion
integral de este dump ni cierre de M01. Filas/esquema/indices/claves de 142 tablas
previas identicos; metadata aditiva esperada: una migracion, dos ContentTypes y
cinco permisos. Cero revisiones/publicaciones de politica o concesiones explicitas
nuevas reales; datos/permisos anteriores conservados. Media no modificada.
Auditores estricto academico (dieciseis campos) y de calendario compatibles, sin
PII ni escrituras. Servidor propio reiniciado --noreload, estaticos recogidos;
doce rutas: inicio/planta/login 200, perfil/listados/editores anonimos 302. Login
conserva CSRF; anonimo sin autoria y segmento externo. Sin login con cuenta real.
Tres overrides JS Grappelli preexistentes en collectstatic, sin nuevos duplicados.

M02.1 sigue: paleta y consumidores editoriales. M09 otras secciones; despues
M02.2-M02.4 manifiestos/categorias/contratos. M01 institucional requiere escritores,
custodios, RPO/RTO, DB minimo privilegio y copia externa cifrada/inmutable; M11
aislamiento real. No extraer datos. docs/calendario-academico-administrable.md.

Suite completa: 997 pruebas, OK. Una omitida; 465.637 segundos.

## 149. Paleta institucional versionada y compartida

La paleta forma parte de RevisionPresentacion: sin nuevo modelo, puntero,
permiso o SQL por peticion. Contrato puro apps/core/paleta.py, cinco colores
HEX completos y seis pares 4.5:1. {} no emite CSS y conserva diseno actual.
DTO de identidad inmutable; proyeccion publica permitida solo contiene colores.
Editor propio con cinco controles nativos y opcion de conservar diseno; revisa
propuesta antes de publicar, historia inmutable/autoridad fresca/CSRF/base
esperada existentes. Nombre, contactos, logos y colores se publican juntos.
Variable opcional INSTITUTION_PALETTE_JSON, parser cerrado sin duplicados.

Conecta cabecera/tokens de botones compartidos/admin, cabecera de comprobantes
y PDF comun. Mantiene colores semanticos, diagramas, maquetas oficiales y
estilos particulares de verticales. No hace reemplazo global de UPEC/autoria.
El fallo de proveedor conserva identidad completa del despliegue; no garantiza
aislamiento de proceso, DB o infraestructura compartidos.

M02.1 sigue con consumidores editoriales; administracion/persistencia propia
de Inicio/Noticias/Servicios/Normativa/Quienes somos permanece en M09.
Despues M02.2 manifiestos, M02.3 categorias y M02.4 contratos. No extraer
datos operativos ni limpiar ContentTypes/permisos; cambiar rama no restaura DB/media.
Documentacion: docs/paleta-institucional-administrable.md.

11 pruebas nuevas; integracion final 33 OK (6.688 s): cuatro
instituciones sinteticas con namespaces propios;
HEX cerrado, contraste, parser de entorno/duplicados, DTO inmutable, borrador,
publicacion/restauracion, continuidad del proveedor, formulario/preview y
color efectivo en PDF. Pruebas de identidad y presentacion existentes pasan.
Chrome: 169 casos, cuatro paletas (original, azul, violeta y marron), ES/EN,
siete anchos 360..1920, portal/admin/editor y rechazo de contraste invalido
con colores conservados. Captura inglesa 360 inspeccionada. Corrida inicial
corrigio tipos text/color ambiguos y conversion HTML5 de Grappelli a texto,
desactivada solo para este editor; final OK. Sin errores
JS ni overflow de pagina/etiquetas medidos. Copia y sesiones QA eliminadas.
No se aprobo ninguna cuenta real ni se concedieron permisos reales.
No certifica toda UI, dispositivos fisicos, accesibilidad o carga masiva.

Default {} persistente en PostgreSQL: prueba con modelo historico 0004
confirma insercion compatible sin la columna paleta. Primera corrida integral
interrumpida para incluir este ajuste antes de aplicar/publicar; suite final
repetida con fuentes finales.
0005 ensayada ida/reversa/ida en copia: 144 tablas anteriores conservadas,
cero nuevas y una columna nueva. Compara datos/esquema/indices/claves
excluyendo solamente la columna nueva y metadata de migraciones.
Reversa ensayada con paletas vacias; retirarla perderia paletas personalizadas.
Aplicada localmente despues de suite y respaldo protegido ACL operador/SYSTEM,
checksum y catalogo del dump comprobados. Datos/esquema anteriores identicos;
una migracion nueva, cero ContentTypes/permisos/concesiones. Todas las revisiones
anteriores conservan diseno original. Media sin cambios. Restauracion integral
del ultimo dump no ensayada: M01 institucional y M11 siguen abiertos.
Servidor propio reiniciado sin recarga y estaticos recogidos. Smoke anonimo
conserva login CSRF y acceso administrativo protegido; no login real.
Ruff/check/makemigrations y catalogos ES/EN (8635 mensajes) OK.

Suite completa: 1008 pruebas, OK. Una omitida; 1210.355 segundos.

## 150. Logos institucionales subidos y variantes por superficie

Logos subidos desde Presentacion institucional: escritorio claro/oscuro,
movil claro/oscuro y marca secundaria. Conserva campos estaticos como respaldo.
Cuatro configuraciones sinteticas: sin subidos, marca unica, dos superficies,
y todas las variantes. PNG/JPEG/WebP estaticos; 2 MiB por archivo, 4096 px por
lado y 4 MP; normaliza a PNG, quita metadatos/bytes adjuntos, preserva alpha.
Referencias UUID inmutables en DTO; almacenamiento fuera de media/estaticos/Git.
Ruta propia con namespace y autoridad fresca: borrador privado/no-store;
marca publicada e historica publica/image/png/nosniff. No cambia colores del
logo ni incorpora un interruptor global de tema. Picture selecciona compacto
hasta 575.98 px segun el fondo real de cada componente. Adaptados cabecera,
admin/login, seis portadas/pies, visualizador/fichas/guias/reportes/asistencia HTML,
maquetas/practicas/reportes PDF, asistente de reservas y segunda
marca de innovacion. Comprobantes de correo siguen consumiendo nombres/colores;
no se agregan enlaces de imagen relativos a correos de clientes externos.

Herencia de archivos en POST mediante ID de revision, validado en el servidor:
reemplazar una variante conserva las demas; Limpiar solo afecta la nueva revision.
GET respeta la imagen resuelta en contexto y su namespace, incluso si cambia
la publicacion. Resuelve formulario historico de solo lectura sin acceder a
campos excluidos. Confirmacion previsualiza cada archivo sobre ambos fondos.
No reescribe ni elimina archivos anteriores. Reversa 0006 bloqueada si existen
referencias: restaurar la marca con una revision, no retirando columnas.

Persistencia local INSTITUTION_LOGO_ROOT, check contra alias publicos. Docker
incluye volumen institutional_brand_data en web/scheduler y ro en respaldo;
bucle reutiliza script de adjuntos para /backups/institutional-brand. Ensayo
real de ese script con imagen sintetica: checksum y bytes restaurados identicos.
Docker no desplegado; adaptador actual local, almacenamiento de objetos futuro
requiere adaptacion. Windows necesita ACL operadora/servicio/SYSTEM; raiz local preparada
sin imagenes reales subidas por este bloque. Servidor propio reiniciado y CSS
recogido; smoke anonimo de rutas/login CSRF/404 de marca desconocida.

M02.1 mantiene consumidores editoriales pendientes; administracion propia de
Inicio/Noticias/Servicios/Normativa/Quienes somos permanece en M09. Luego M02.2
manifiestos, M02.3 categorias y M02.4 contratos. No extraer datos operativos ni
limpiar ContentTypes/permisos. M01 institucional/M11 siguen abiertos. Una rama
Git no restaura la base ni los archivos.
Documentacion: docs/logos-institucionales-administrables.md.

16 pruebas nuevas; integracion focal 49 OK antes de la suite final.
Valida formatos/peso/pixeles, animaciones/disfrazados/corrupcion/poliglotas,
transparencia/metadatos, borrador/publicacion/restauracion, herencia real en
POST, lectura historica, rechazo de fuente inexistente/fuera de namespace,
revocacion de acceso, preview ES/EN y logo incrustado en PDF. El escritor
historico 0004 sigue insertando con defaults persistentes de las nuevas columnas.
Chrome final: 450 casos OK, cuatro configuraciones, ES/EN, siete anchos
360/390/768/1024/1200/1366/1920, seis portadas publicas/admin/editor, carga real de archivo y
preview de cinco variantes conservadas. Seleccion de currentSrc/naturalWidth
comprobada, cero errores JS/overflow. Capturas movil/preview 390 inspeccionadas.
Copia, sesiones y archivos QA retirados; no permisos ni aprobaciones reales.
No certifica dispositivos fisicos, toda UI, accesibilidad o carga masiva.

Corrida integral preliminar interrumpida, sin fallos detectados, para conectar
las portadas/fichas restantes antes de aplicar/publicar. Final repetida con
fuentes completas y caches de JS/CSS versionadas para evitar codigo anterior.

0006 ensayada ida/reversa/ida en copia restaurada del respaldo protegido
pre149: 144 tablas anteriores, cero nuevas, cinco columnas nuevas. Datos,
esquema anterior, indices y claves identicos excluyendo solamente los cinco
campos nuevos y metadata de migracion. La reversa solo se ensaya sin imagenes;
prueba de guarda rechaza retirarla con referencias historicas.
Aplicada despues de suite/respaldo ACL/checksum/catalogo PG. Filas y esquema
previos identicos; una migracion nueva, cero ContentTypes/permisos/concesiones.
Media de negocio sin cambios y sin imagenes reales creadas. No certifica una
restauracion institucional completa del respaldo mas reciente.
Ruff/check/makemigrations y catalogos ES/EN (8648 mensajes) OK.

Suite completa: 1024 pruebas, OK. Una omitida; 939.563 segundos.

## 151. Editor HEX y degradado institucional con vista previa

M02.1: editor de paleta con selector visual y campo HEX sincronizados.
Acepta #082b22 o 082b22, mayusculas, espacios y entidades copiadas; servidor
normaliza a seis digitos en minusculas. El campo Degradado principal es
opcional y separado de los cinco colores base. Linear-gradient con angulo
-360..360 grados (hasta dos decimales), dos a cinco colores opacos, posiciones
0..100% ascendentes y variables de lista cerrada. Guarda HEX e interpolacion
in srgb; no queda dependencia de variables CSS futuras. --unit-green-600 es
principal; --unit-green-800 reduce cada canal al 75%. --institucion-<rol>
resuelve uno de los cinco colores base. No acepta CSS arbitrario, URLs,
HTML, alfa, funciones anidadas o variables externas.

Contraste de blanco y acento >=4.5:1 en cada parada, incluso intermedias;
fondos mas oscuros que esas tintas. Mantiene los seis pares de la paleta solida.
Aplica degradado a contacto superior, marca admin y pestanas activas de unidades;
PDF, correo, bordes y textos siguen usando colores solidos. No certifica
accesibilidad integral de todos los componentes. Preview seguro sin HTML
procedente de campos, estado ES/EN y rechazo autoritativo sin JS. Guardar
crea borrador; confirmacion, autoridad fresca, historial y base esperada
siguen en la app propietaria. Sin migracion, permisos ni datos reales nuevos.

Fila de paleta movil ocupa ancho completo: la inspeccion detecto columna
estrecha en Grappelli y se corrigio solo este campo. CSS/JS con version 151
recogidos y servidor propio reiniciado; smoke anonimo/CSRF/404 de marca
correcto. 37 pruebas focales OK (3.738 s), 10 nuevas. Cuatro configuraciones
sinteticas: original, solida, degradado HEX y degradado de variables. Chrome
final 227 casos OK, ES/EN, 360/390/768/1024/1200/1366/1920, inicio, planta QA,
admin y formulario; sincronizacion, pegado del ejemplo con NBSP/entidades,
contraste/parada intermedia, entradas invalidas, publicacion/restauracion,
POST real sin JS y preview guardado. Cero JS/overflow; capturas inspeccionadas.
Copia y sesiones QA retiradas; no se aprueba ni normaliza ninguna cuenta real.
Ensayo inicial del navegador encontro ausencia de planta en la fixture,
no un fallo del portal: se creo unidad sintetica en la copia QA y se repitio.
La inspeccion visual motivo repetir el ensayo final con columnas corregidas.
Ruff/check/makemigrations, sintaxis JS y 8659 mensajes por idioma OK.

M02.1 y M09 siguen con los pendientes editoriales previos; luego M02.2
manifiestos, M02.3 categorias y M02.4 contratos. M01 institucional/M11 no
cerrados. No renombrar ORM operativo ni limpiar ContentTypes/permisos.
Commit local; publicacion GitHub pendiente de autorizacion explicita del
destino COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo de revision
automatica en el push del bloque 150. No reintentar sin resolver autorizacion.
Guia: docs/paleta-institucional-administrable.md (continuacion 151).

Suite completa: 1034 pruebas, OK. Una omitida; 925.057 segundos.


## 152. Vista previa inmediata en los cinco campos de logo

Widget propio en configuracion_institucional, conservando ClearableFileInput,
formulario multipart, herencia en POST, campos y almacenamiento privados.
Dos fondos por imagen, nombre/dimensiones del archivo seleccionado, retirar y
restablecer seleccion. El preview nuevo usa blob local: no sube ni publica.
Los logos guardados se muestran tambien sin JavaScript. Server validation,
normalizacion a PNG, historial y autoridad de publicacion conservados.

CSS/JS exclusivos del formulario propietario, recursos incluidos una vez,
filas de logo completas en movil y botones con dimensiones propias para evitar
el estilo compacto de Grappelli. Catalogos ES/EN: 8668 mensajes por idioma.
Sin migracion, concesiones ni cambios de datos reales. Servidor propio
reiniciado; smoke anonimo, marca inexistente 404 y nuevos assets correctos.
El smoke anterior suponia paleta desactivada: la configuracion real del usuario
ya cambio; se retiro esa suposicion sin modificar la configuracion publicada.

Dos regresiones nuevas: editor sin escrituras y herencia/retiro que conserva
archivos historicos. Primera corrida focal 101/102: el conteo incluia tambien
el logo de cabecera; se ajusto a las imagenes del widget y las dos regresiones
pasaron. Chrome preliminar 63 casos OK, cuatro configuraciones, ES/EN, siete
anchos 360/390/768/1024/1200/1366/1920; seleccion PNG/JPEG/WebP, reset/clear,
rechazo SVG disfrazado/peso/dimensiones y logos existentes sin JS. La inspeccion
detecto boton compacto del tema y se amplio antes de validacion final.
No certifica dispositivos fisicos ni accesibilidad integral.

Chrome final: 63 casos OK, cero errores JS ni desbordamientos; capturas movil y escritorio inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos. Suite completa: 1036 pruebas, OK. Una omitida; 722.611 segundos.

M02.1/M09 editoriales, M02.2/M02.3/M02.4, M01 institucional y M11 mantienen
sus pendientes. No cerrar etapas por esta mejora de interfaz.
Publicacion pendiente de autorizar explicitamente COMPUMAX-EC/CITT, rama
reestructura-modular, tras rechazo automatico del push del bloque 150.


## 153. Paleta de botones y tarjetas en el sistema

Auditoria de colores efectivos: la continuacion 149/151 cubria cabecera y
consumidores de tokens, pero multiples estilos locales mantenian colores
HEX/RGBA propios. Se conectan los estilos propietarios de portal, seis
entradas publicas, cuatro catalogos, detalle/visor, gestion, reservas,
practicas/guias, documentos HTML y administrador. Cada referencia conserva
su color anterior como fallback; sin paleta publicada el diseno original
permanece. Librerias externas, imagenes y recursos del usuario conservan su
contenido y formato propios.

Contrato comun de componentes con principal, oscuro, acento, texto y fondo.
Tarjetas blancas con bordes, indicadores y superficies suaves derivados;
acciones principales blancas sobre principal/degradado, destacadas sobre
acento y acciones secundarias con contorno. Los cuatro tipos de unidades
siguen identificados por nombres e iconos; con paleta personalizada sus
acciones/tarjetas comparten marca. Controles Grappelli de guardar conectados,
sin alterar eliminar. Bootstrap conserva sus variantes semanticas.

Estados y datos cientificos separados de la marca: reglas de advertencias,
errores, confirmaciones, disponibilidad y diagramas mantienen sus colores.
Alias locales de marca se resuelven a roles compartidos, sin renombrar apps,
ORM operativo ni archivos. Fondos alfa usan canales RGB derivados validados.
ComponentesPaleta calcula tintas/superficies legibles >=4.5:1 en los pares
probados; fallback blanco para superficies cerca del limite de contraste.
No certifica accesibilidad integral ni todos los recursos personalizados.

El editor agrega muestra local de tarjeta y tres acciones; valida tambien
los seis pares solidos antes de dar preview valido. Guardar crea borrador,
publicar sigue requiriendo confirmacion, autoridad fresca y base esperada.
CTA del correo usa principal solido, sin variables CSS/degradados; envoltorio
usa fondo/texto. HTML independientes reciben la misma paleta en su head.
Recursos/versiones de cache actualizados, servidor propio reiniciado.
No migracion, permisos nuevos, publicaciones ni datos institucionales cambiados.

Validacion: Suite completa: 1039 pruebas, OK. Una omitida; 1483.064 segundos. Focal institucional: 105 OK, 19.739 segundos. Chrome final: 791 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye comparacion del diseno original en cuatro pantallas, apertura real del asistente, preview local y parseo CSS. Capturas de escritorio, movil y editor inspeccionadas. Geometria/selectores de 28 hojas existentes conservados. Ruff/check/makemigrations y sintaxis JS correctos; catalogos ES/EN de 8675 mensajes compilados. Copias y sesiones QA retiradas. Smoke del servidor local y assets nuevos: OK. No modifica datos reales ni esquema.
Primer ensayo encontro 404 de aula en fixture sin proceso: se agrego proceso
sintetico con una etapa y capacidad productiva solo en la copia QA.
Ensayo preliminar 786 casos Chrome OK; se repite con fuentes finales tras
separar estados/tintas y comparar diseno original. Copias/sesiones QA retiradas.

M02.1/M09 mantienen pendientes editoriales; M01 institucional/M11 no cerrados.
Publicacion GitHub pendiente de autorizacion explicita del destino
COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo automatico del bloque150.


## 154. lineas, degradados, tipografia y contraste

La presentacion institucional incorpora opciones visuales adicionales dentro
del mismo JSON validado; no modifica modelos ni requiere migracion. Las
revisiones antiguas siguen siendo validas y las nuevas mantienen valores
primitivos en el DTO inmutable. Guardar genera borrador; revisar/publicar y
restaurar conservan la autoridad, base esperada e historial existente.

- Lineas de marca: color HEX, degradado independiente, grosor 1-6 px,
  intensidad 25-100 % y longitud 20-100 %. Se aplican a subrayado del menu,
  separadores decorativos, lineas de seccion y bordes superiores de tarjetas.
  Los bordes de campos y los diagramas cientificos mantienen su funcion.
- Acciones y bandas: degradados independientes, intensidad 0-100 % y
  extension 20-100 %. Intensidad mezcla los stops con el color oscuro;
  extension define donde termina la transicion, conservando el ultimo color.
  No aplica opacidad al texto ni a los iconos. Los stops siguen protegidos
  por contraste de blanco/acento; una linea decorativa admite colores claros.
- Fotos: color de capa, intensidad 30-100 % y extension 35-100 %. Una placa
  de texto opaca y contrastada permite mantener la lectura con capas tenues
  o claras. El color de capa nunca se confunde con el fondo de lectura.
- Tipografia web: fuentes distintas de contenido y titulos, escala 90-115 %,
  colores opcionales de titulos/iconos sobre fondos claros. Lista cerrada:
  sistema, Poppins, Montserrat, Arial, Verdana, Trebuchet y Georgia; fallbacks
  por familia. No permite CSS, URL ni carga de fuentes arbitrarias. PDF y
  correo conservan sus fuentes compatibles; sus colores siguen la marca.

Opciones vacias conservan los valores actuales. Vista previa local incluye
tarjeta, acciones, linea, banda e imagen esquematica; no modifica la
presentacion publica antes de confirmar. Variables nuevas se derivan una
vez por scope sin consultas adicionales. HEX/degradados/numeros/fuentes
usan validacion autoritativa cerrada. Fondos suaves retroceden a blanco si
una tinta personalizada quedara por debajo del contraste de 4.5:1.

Se corrigen los iconos/contadores sobre bandas oscuras, el titulo largo del
slider y el espacio entre flechas, texto y recuadro inferior en movil. El
carrusel adapta su altura al ampliar la lectura. El menu de Inicio usa el
mismo breakpoint de 1279.98 px que la cabecera compartida. Se corrige una ruta de
imagen con una etiqueta de template dentro de CSS estatico. Cambia la
version de cache de estilos; no modifica imagenes ni recursos de usuarios.

Validacion: Suite completa: 1045 pruebas, OK. Una omitida; 1047.906 segundos. Focal institucional: 111 OK, 31.394 segundos. Chrome final: 1011 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye cuatro slides por ancho/idioma, limites de lectura/controles, fuentes de contenido/titulos/iconos, longitud/intensidad de linea, gradiente efectivo y preview con entradas invalidas/desactivado. Ensayo de breakpoint: 171 casos OK. Capturas de escritorio, movil, bandas y editor inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos; ES/EN de 8702 mensajes compilados. Copias y sesiones QA retiradas. Smoke anonimo/recursos del servidor propio: OK. No modifica datos reales ni esquema.
Ensayo inicial detecto desbordamiento a 360 px con lectura ampliada; ajuste
posterior y ensayo focal Chrome 339 casos OK. La comprobacion de longitud
ignora el menu oculto en movil, que no tiene dimensiones de layout.
No certifica accesibilidad integral, dispositivos fisicos ni recursos externos.

M02.1/M09 mantienen pendientes editoriales; M01 institucional/M11 no cerrados.
Publicacion GitHub pendiente de autorizacion explicita del destino
COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo automatico del bloque150.


## 155. Acciones solidas y lectura sobre imagenes

Se unifican acciones solidas: principal (blanco sobre principal), secundario
(superficie blanca y texto oscuro; contorno claro sobre portadas), destacado
(acento con texto oscuro). Los nombres heredados de las clases se conservan:
upec-button--primary/unit-action--primary son destacados; home-btn.primary
y upec-button--secondary son acciones principales. Los estados de peligro
y exito mantienen colores semanticos solidos independientes de la marca.

Contrato comun: webcitt/static/portal/css/components/acciones_superficies.css,
cargado por paleta_institucional.html con y sin personalizacion. Se conserva
la validacion cerrada de paleta, fuentes y degradados. Los degradados
administrables quedan en cabecera, bandas y lineas decorativas; botones,
pestanas activas y controles del visualizador tienen fondos sin degradado.
El preview del administrador refleja estas variantes.

Las portadas de Inicio, Quienes somos, catalogos y servicios usan sombreado
continuo del color oscuro sobre la foto, sin placas verdes opacas en el
texto ni en los titulos de miniaturas. La capa administrable aporta un tinte
suave adicional; intensidad/ancho no debilitan la capa de lectura. Textos
de portadas y de detalles oscuros usan blanco; objetivos y leyendas sobre
acento usan texto oscuro. Se corrigen subtitulos e iconos de seleccion en
el visualizador y se conservan los limites de lectura ampliada del bloque154.

No cambia datos, esquema, imagenes, publicaciones institucionales, permisos
ni rutas. Cache CSS nueva. La revision anterior de la presentacion conserva
sus valores; el codigo nuevo aplica la misma regla de acciones solidas.

Validacion 155: focal institucional 111 pruebas OK (47.584 s). Chrome: 1027 casos OK, cuatro configuraciones (incluido diseno sin paleta), ES/EN, siete anchos 360-1920 px, 14 rutas y cuatro slides; sin errores JS ni desbordamientos. Comprueba acciones sin degradados, contorno blanco sobre fotos, ausencia de placas opacas, estados normal/hover, fuentes, lineas y preview con entradas invalidas/desactivado. Capturas de Inicio, catalogo, carrusel escritorio/movil y editor inspeccionadas. Regresion final de tarjetas: 355 casos OK adicionales en Inicio/Quienes somos, con nombres completos en ES/EN y sin fondos amarillos dentro del titulo. Miniaturas sobre superficies oscuras. Capturas reales de catalogo, identidad y unidades inspeccionadas. Auditoria de lectura del servidor real: 48 botones opacos en 10 rutas con contraste >=4.5:1. Ruff, check, makemigrations --check, sintaxis JS y collectstatic correctos. Smoke anonimo y recursos: OK. Copias y sesiones QA retiradas; datos reales sin cambios. Servidor propio reiniciado para invalidar cache de plantillas de DEBUG=False y servir assets nuevos; query final v155-final. Ultima suite integral: bloque154, 1045 OK (una omitida); este ajuste visual se valida con pruebas focales y navegacion real. No certifica accesibilidad integral ni dispositivos fisicos.

M02.1/M09 conservan pendientes editoriales; M01/M11 no cerrados. GitHub
pendiente de autorizacion explicita del destino COMPUMAX-EC/CITT, rama
reestructura-modular, por rechazo automatico del bloque150. No reintentar
el push sin esa confirmacion. La base estable anterior se conserva.


## 156. Portada bilingue de Inicio en su app editorial

Primera seccion editorial con persistencia propia en apps/portal/inicio:
lema, titulo, resumen, etiquetas de dos acciones y mensaje de marca de Inicio,
en ES/EN. Portal es app Django instalada con migracion, admin, permisos,
contratos, servicios, consulta publica, plantillas y pruebas propios. La
plantilla publica compatible sigue en webcitt; se conservan rutas, fotos,
galeria, indicadores referenciales y las funciones de las otras secciones.

El administrador separa Portal institucional de Configuracion institucional.
Guardar crea un borrador; vista previa privada no publica; confirmar POST con
CSRF crea una revision publicada nueva. Recuperar una version anterior crea
otra, conservando historia. Permisos propios de crear, leer y publicar,
revalidados desde la base. Bloqueo transaccional, comprobacion de base enviada
y prueba concurrente impiden sobrescribir una publicacion posterior.

La lectura publica proyecta solo la revision publicada vigente a un DTO
inmutable, con validacion de ambos idiomas, limites y autoescape. Texto simple,
sin HTML/CSS ni URLs configurables. Falta de contenido, corrupcion o error de
consulta usan los textos traducidos instalados. Una sola consulta, sin modelos
operativos. Guardas comunes extraidas a apps/core/persistence/publicacion.py;
configuracion_institucional/versionado.py conserva imports compatibles. Portal
arranca con Auth/ContentTypes sin webcitt ni Configuracion institucional; esto
no garantiza aislamiento de procesos o de la base compartida.

portal.0001_initial aplicada localmente tras respaldo protegido, restauracion,
aplicacion/reversa/reaplicacion en copia y comparacion contra snapshot. Datos,
columnas, indices y claves de las 144 tablas previas conservados literalmente
en la base real; hashes de 386 archivos iguales. El restaurador represento de
forma equivalente el cast de un array de un indice parcial previo: verificada
la equivalencia solo en copia, sin cambiar el indice real. Dos tablas nuevas
vacias, dos ContentTypes y tres permisos, ninguna concesion a usuarios/grupos.
No se crean publicaciones reales ni se cambian cuentas, imagenes o temas.
Con historia real no revertir tablas ni limpiar ContentTypes/permisos: usar
codigo compatible. Git no restaura datos. M01 institucional sigue abierto:
restauracion coordinada de adjuntos, copia externa cifrada/inmutable, custodia
de claves y RPO/RTO siguen pendientes.

Validacion: Suite completa: 1068 pruebas, OK. Una omitida; 838.981 segundos.
Final Portal: 23 pruebas OK (2.786 s); institucional + Portal: 134 OK
(29.034 s). Incluye permisos revocados, CSRF, historial, formularios obsoletos,
concurrencia, recuperacion, corrupcion y carga independiente. Ruff/check y
makemigrations --check correctos; ES/EN con 8731 mensajes compilados.
Chrome final: 454 casos OK, ES/EN, once anchos 360-1920 px, con diseno
original y paleta personalizada al 115 % con titulos Georgia. Comprueba texto
normal y maximo sin espacios, vistas privadas, publicar/recuperar, roles,
formularios, botones completos y sin degradado en normal/hover; cero errores
JS ni desbordamientos. Cabecera compartida: otros 84 casos OK en siete rutas,
ES/EN y seis anchos de escritorio, sin colisiones entre marca, enlaces o
acciones. Capturas de escritorio/movil inspeccionadas. Se corrigen h1 junto
al lema, tamano heredado de botones Grappelli, espacio del menu ampliado y
columnas de indicadores de Inicio a 1280 px; no se cambian sus cifras.
Copias y sesiones QA retiradas. Smoke anonimo de nueve recursos/rutas publicas
y proteccion del editor: OK. Servidor propio recargado para invalidar cache de
DEBUG=False y servir los estilos finales. No certifica dispositivos fisicos,
accesibilidad integral, login OAuth ni aislamiento de despliegue.

Guia de uso y estructura: docs/portada-inicio-administrable.md.
M02.1/M09 avanzan con la portada; otras secciones editoriales siguen pendientes.
Siguiente frontera: completar consumidores de identidad M02.1 y el manifiesto
M02.2, despues categorias M02.3 y propietarios/efectos M02.4 antes de extraer verticales
M03+. Noticias, Normativa, Servicios y Quienes somos se abordaran por seccion
con sus reglas propias. M01 institucional y M11 no se declaran cerrados.

El usuario confirmo COMPUMAX-EC/CITT, rama reestructura-modular: los bloques
150-155 ya publicados hasta 6ce91d0f. Esa confirmacion supera las notas
historicas de autorizacion pendiente. El bloque 156 se publica en el mismo
destino conforme a su instruccion permanente; sin merge a main/version2 y
conservando integracion-version2-funciones como base anterior.


## 157. Identidad y soporte en cuentas y titulos operativos

M02.1: seis pantallas de contrasenas, ficha de unidad, Gestion, Completitud y
reporte administrativo proyectan nombre corto y siglas de la identidad actual
en el titulo. Recuperacion y confirmacion comparten account/includes/soporte.html:
correo publico publicado con autoescape; vacio elimina el enlace sin heredar
soporte UPEC. La orientacion social remite a opciones disponibles y no presupone
que cuentas sociales carezcan de contrasena. Usa el proveedor institucional
existente, sin una consulta o configuracion de soporte independiente.

Los PDF nuevos del listado usan reservas-AAAAMMDD-HHMM.pdf; no se renombran
archivos emitidos. Cabecera, autor, filas, filtros y permisos conservan el
presentador. No hay migraciones ni cambios de datos, cuentas, contrasenas,
pertenencia, dominios OAuth, cookies, URLs, marcas publicadas, imagenes o codigos
FT oficiales. El contacto publico no acredita pertenencia ni autoriza usuarios.

Validacion focal: 33 pruebas OK (7.110 s), tres nuevas. Incluye perfil custom en
ES/EN, sin contacto heredado, texto escapado, publicacion/retirada del soporte
sin cambiar credenciales/enviar correo y concordancia HTML/PDF personalizada.
Chrome: 252 casos OK de seis pantallas, tres perfiles (UPEC, custom y sin correo),
ES/EN y siete anchos 360-1920 px. HTML sintetico con formularios Allauth reales
y recursos del servidor local; estilos cargados comprobados y capturas movil/
escritorio inspeccionadas. Sin desbordamientos ni errores JS; no envia formularios
ni inicia OAuth. No certifica dispositivos fisicos o accesibilidad integral.
Cuatro mensajes nuevos, ES/EN con 8735 mensajes compilados. Ruff/check y
makemigrations --check correctos.
Suite completa: 1071 pruebas, OK. Una omitida; 767.629 segundos.
Smoke HTTP anonimo: siete rutas de cuentas, Inicio, login, catalogo y ficha
responden 200 con el servidor local final; titulos sin marca compuesta antigua.
Servidor propio iniciado con codigo y catalogos finales, sin publicar contenido
institucional real ni alterar credenciales.

Pendientes clasificados en docs/identidad-producto-institucion.md: contenido
editorial UPEC para M09; etiquetas/choices operativos revisados juntos sin
renombrar valores historicos; codigos FT/bibliografia conservados; acceso social
segun politica propia; traslado tecnico en M10. Se corrige el estado documental
obsoleto que aun describia catalogos/niveles/calendario como no persistentes.
M02.1 y M09 siguen parciales; M01 institucional y M11 abiertos. Siguiente bloque:
iniciar M02.2 con contratos del manifiesto y registro de modulos/dependencias;
sin retirar apps heredadas, alterar derechos o borrar historial al suspender.

Publicar en COMPUMAX-EC/CITT, reestructura-modular, conforme a la autorizacion
permanente. Base estable anterior conservada; sin merge a main/version2.


## 158. Manifiestos propios y registro de dependencias M02.2

Primer avance M02.2: once paquetes conservan manifiesto.py propio. El contrato
inmutable y el registro viven en apps/core/modulos.py; config/modulos.py compone
metadatos sin cargar rutas, admin, tareas, modelos o Django. El nucleo de
contratos no importa verticales. Manifiesto v1, version inicial 1.0.0, separado
de versiones comerciales y contratos de datos.

Declara paquetes, etapas, dependencias, integraciones opcionales, app Django,
rutas, admin, migraciones, comandos, tareas, salud, capacidades y contratos.
Puntos aun no implementados quedan vacios, sin salud_ok o permisos ficticios.
Identificadores y paquetes unicos, tuplas inmutables, referencias del propietario,
ciclos y dependencias obligatorias ausentes se validan antes de exponer el
registro. Planes deterministas agregan dependencias, no integraciones opcionales.

Centros I+D y Portal no exigen verticales en el plan. Cada vertical declara
integraciones/directorio/legado sin exigir otra vertical. No implica que el
URLconf completo o sus recursos funcionen sin webcitt. El legado conserva
operacion, modelos, permisos, admin y tablas; no hay extraccion o migracion.

manage.py auditar_modulos devuelve JSON de metadatos sin consultar filas,
adjuntos, credenciales, usuarios o settings privados. --modulo se puede repetir
y filtra el plan; no instala, autoriza, suspende o borra datos. slcid.E011 detecta
registro invalido y apps Django requeridas ausentes desde AppConfig resuelto.
El comando permanece en el legado hasta el traslado tecnico M10. Las entradas
de comandos declaradas no sustituyen el inventario exhaustivo existente.

Validacion focal: 23 pruebas OK, 3.112 segundos. Trece nuevas cubren formatos,
inmutabilidad, ciclos, planes, archivos existentes, carga aislada bloqueando
Django/ORM/controladores, diagnosticos sin detalles internos y auditoria sin DB.
La compatibilidad de rutas permanece correcta. Ruff, check y makemigrations
--check --dry-run correctos; no cambia interfaz, CSS, JS, URLs o traducciones.
Suite completa: 1084 pruebas, OK. Una omitida; 455.002 segundos.
Auditoria CLI reproducida con seleccion Laboratorios y seleccion Portal/Centros
I+D: correcta, sin consultas de datos o modificaciones reales.

Guia: docs/manifiestos-y-registro-modular.md. Arquitectura y fotografia historica
de rutas enlazan el estado actual. No altera cuentas, permisos, contenido
publicado, configuracion institucional, historial o adjuntos reales.

Siguiente frontera M02.2: controles separados de disponibilidad en despliegue,
habilitacion institucional, derechos/limites y permisos de usuario/objeto,
probados en servidor para todas las superficies del alcance antes de ofrecer
suspension en admin. Suspension conserva historial y exportacion administrativa.
No retirar apps heredadas ni mover tablas. M02.1/M02.2/M09 parciales;
M01 institucional y M11 siguen abiertos. No afirma aislamiento de procesos,
credenciales de base o funcionamiento durante caidas del motor.

Publicar en COMPUMAX-EC/CITT, rama reestructura-modular, segun autorizacion
permanente; conservar base estable anterior y no hacer merge a main/version2.


## 159. Controles de capacidad y archivo administrativo de Inicio

M02.2 avanza con la capacidad editorial portal.portada_inicio. Contrato puro
ControlCapacidad en core, politica validada en config/capacidades.py y proveedor
local con fallo cerrado. Disponibilidad, habilitacion y derecho son booleanos
separados; no conceden permisos. Los servicios recargan actividad, staff y
permisos de usuario desde base antes de crear/publicar/exportar.

CAPABILITY_CONTROLS carga SLCID_CAPABILITY_CONTROLS JSON, default {} compatible.
Solo admite portal.portada_inicio, cuyo alcance tiene guardas completas. No
habilita controles de verticales sin cobertura. Rechaza claves/tipos desconocidos,
duplicados y JSON >4096 caracteres; slcid.E012 diagnostica politica invalida.
No altera .env real o flags del despliegue real. La habilitacion institucional
es declarada por despliegue: su administracion persistente/dinamica sigue pendiente.
Derecho es declarativo, sin licencia firmada, facturacion o cuotas ficticias.

Cada flag bloqueado deniega nuevas revisiones/publicaciones en servicios,
modelos incluso con marcador interno y URLs GET/POST directas del admin.
Oculta acciones nuevas; no mueve puntero ni borra historial, permisos o adjuntos.
Inicio conserva portada base ES/EN, sin consulta editorial cuando esta suspendida.
No suspende todo el Portal ni las otras secciones o tipos de unidad.

Historial, detalle y preview privados conservan permiso de lectura. Nueva accion
Exportar revision descarga JSON v1 bilingue con identidad tecnica y datos del
contenido, sin datos personales de autor, claves o permisos. Exportacion recarga
permiso, valida instalacion y devuelve private/no-store/nosniff; POST 405 y acceso
anonimo redirigido. Se conserva incluso al bloquear derecho. Reactivar reutiliza
el mismo puntero; no crea registros. El archivo no es respaldo integral M01.

Comando propio Portal auditar_capacidades muestra politica sin consultar datos
o conceder acceso. Manifiesto Portal 1.1.0. Diez pruebas nuevas; focal Portal,
rutas y manifiestos: 56 pruebas OK, 6.593 segundos. Incluye permisos revocados,
otra institucion, servicios/modelos/URLs, cuatro controles, fallback sin SQL,
conservacion y reactivacion. Ruff/check/migraciones en seco correctos. Un mensaje
nuevo ES/EN; 8736 mensajes compilados. No modifica CSS/JS, migraciones o rutas
publicas. La nueva accion reutiliza herramientas del admin; no se presenta
como una nueva certificacion responsive o de dispositivos fisicos.
Suite completa: 1094 pruebas, OK. Una omitida; 450.654 segundos.
Auditoria CLI default y carga desde entorno con habilitada=false reproducidas;
suspension solo en proceso aislado, configuracion real sin cambios.

Guia: docs/controles-capacidades.md; arquitectura y guia de manifiestos enlazan
alcance actual. No modifica datos reales, cuentas, roles, contenido publicado,
marcas o adjuntos. No retira INSTALLED_APPS ni mueve tablas.

Siguiente M02.2: habilitacion institucional persistente con permiso especifico,
pertenencia de instalacion, historial auditado, version esperada y bloqueos que
serialicen suspension/escrituras; separar autoridad institucional de disponibilidad
y derechos del despliegue. Antes de ampliar a verticales, inventariar y proteger
URLs, comandos, API, exportaciones y tareas del alcance. M02.1/M02.2/M09 parciales;
M01 institucional y M11 abiertos. SQL privilegiado y caidas compartidas requieren
controles de base/despliegue; no afirma aislamiento de procesos o credenciales.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente;
conservar base estable anterior y no hacer merge a main/version2.


## 160. Habilitacion institucional auditada de Inicio

M02.2 agrega habilitacion institucional persistente exclusivamente para
portal.portada_inicio. Configuracion institucional posee capacidades/ con
models, selectors, services y admin, CSS/plantillas/pruebas propios. Manifiesto
1.1.0; core resuelve proveedor opcional fijo CAPABILITY_STATE_PROVIDER. Portal
sigue cargando en interprete aislado con auth sin importar esta app cuando el
despliegue omite el proveedor. No ofrece controles para verticales sin cobertura.

EstadoCapacidad usa clave producto/institucion/modulo/capacidad y version CAS.
Ausencia significa true/version 0; las lecturas no crean filas. Primer escritor
materializa estado base; cada cambio real agrega CambioCapacidad inmutable con
actor/fecha/motivo/estados/version. Unique constraints previenen duplicados;
estado/historia bloquean CRUD directo y operaciones masivas ORM. Marcadores
internos y SQL privilegiado son interfaces de confianza, no aislamiento del motor.

Admin > Configuracion institucional > Habilitaciones institucionales > Configurar
Inicio editorial requiere view_estadocapacidad y administrar_capacidades; lectura
del historial usa view_cambiocapacidad. No concede esos permisos automaticamente.
Formulario POST con CSRF, motivo simple, confirmacion y version esperada; GET
no escribe y campos de autoridad ajenos se rechazan. Sin selector de institucion,
modulo o derechos. Queries administrativas se filtran por identidad tecnica
del despliegue; no convierte el sistema en multitenencia.

El servicio recarga actor activo/staff/permisos. Orden de bloqueo actor ->
estado institucional -> puntero editorial; SELECT FOR UPDATE compartido entre
cambio de habilitacion y guardar/publicar, tambien modelos con marcador interno.
La transaccion mantiene el bloqueo hasta commit. Escritura primero completa
antes de suspender; suspension primero hace esperar y deniega la escritura.
Contexto acotado a transaccion se limpia ante errores sin ocultar errores del
negocio. Dos confirmaciones con misma version no se sobrescriben.

Control efectivo: disponible/despliegue, habilitada/despliegue AND institucional,
derecho/despliegue y permiso del actor. Habilitar en admin no levanta bloqueos
de despliegue ni concede permisos editoriales. Lectura fresca sin cache entre
peticiones; error de politica falla cerrado. Suspension usa portada base ES/EN,
deniega nueva revision/publicacion y conserva puntero, historial, preview privado
y exportacion autorizada. Reactivar usa publicacion vigente sin duplicarla.
No suspende las otras secciones o unidades. Caches externos deben invalidarse
si se incorporan. Cambiar flags del despliegue sigue requiriendo recarga de procesos.

18 pruebas nuevas: permisos frescos/revocados, actividad, lectura requerida,
CAS, tipos/motivo, instalacion, guardas ORM, CSRF/metodos/campos ajenos, proveedor
opcional/fallo cerrado, conservacion y carreras reales guardar/publicar/suspender
en ambos ordenes y dos confirmaciones iniciales. Focal: 74 OK, 21.994 segundos.
Suite integral: 1112 pruebas, OK, una omitida; 1245.019 segundos. El ajuste final
de plantilla (solo media.css en extrastyle, evita JS antes de Grappelli) y su
mensaje de portada base se validaron despues con la focal y Chrome.
Ruff/check/makemigrations --check --dry-run/catalogos correctos; 23 mensajes
nuevos, 8759 por idioma ES/EN compilados. No modifica JS o rutas publicas.

Chrome en copia temporal: 49 casos OK; formulario/listado en ES/EN, seis anchos
360,390,768,1024,1366,1920 y preferencias de color clara/oscura. Geometria sin
overflow, textos y confirmacion traducidos, cero errores JS. Suspension conserva
preview/exportacion, deniega add y reactivacion recupera portada. Capturas
390/1366 inspeccionadas. Conserva tema propio del admin; no certifica dispositivos
fisicos o un nuevo tema oscuro. Copia/cuentas/sesiones QA retiradas.

0007 aditiva aplicada localmente solo despues de dump custom protegido con ACL,
snapshot consistente/SHA256, restauracion y aplicacion -> reversa 0006 ->
reaplicacion en copia. Reconciliadas las 146 tablas previas, sus filas, columnas,
indices y claves; 390 archivos verificados sin cambios. La restauracion normaliza
solo el cast ARRAY equivalente del indice parcial previo de solicitudes de
cambio, probado contra filas y nueve casos limite. Fuente compara DDL literal.
Dos tablas nuevas vacias, dos ContentTypes y tres permisos nuevos, sin asignarlos
a cuentas/grupos. No cambia contenido publicado, marcas o adjuntos reales.
Dump/huellas/evidencias solo en backups/tmp ignorados; copia restaurada retirada.
Es evidencia local de base, no cierre M01 institucional ni copia coordinada de
adjuntos, cifrado externo, RPO/RTO o aislamiento de credenciales/procesos M11.

Guia actualizada: docs/controles-capacidades.md. Ruta/arquitectura/manifiestos
enlazan alcance. Siguiente bloque: inventario de superficies y autoridades de
las otras capacidades antes de extender habilitacion a verticales: URLs,
comandos, API, tareas, exportacion/historial y dependencias. No retirar apps,
cambiar app labels o mover tablas sin ensayos M01/M10. M02.1/M02.2/M09 parciales;
M01 institucional y M11 abiertos. Las categorias/extensiones M02.3 y contratos/
propietarios/senales M02.4 preceden la extraccion funcional de las verticales.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente;
conservar base estable anterior y no hacer merge a main/version2.

## 161. Inventario de superficies y autoridades de capacidades

Inventario reproducible de superficies y autoridades antes de ampliar controles
de capacidad. Implementacion en apps/integraciones/superficies.py y adaptador CLI
webcitt.management.commands.auditar_superficies_capacidades. --modulo repetible
filtra modulos declarados; conserva todas las superficies compartidas. --resumen
omite detalle. JSON sin filas, adjuntos, valores de credenciales o permisos efectivos.
Bloqueo SQL por execute_wrapper en todos los aliases durante la inspeccion;
limpieza al terminar o fallar. No ejecuta handlers, acciones, permisos, scripts,
comandos operativos ni receivers. Arranque Django fuera del wrapper; codigo
confiable, no sandbox. Origen relativo/lineas y hashes de codigo; AST sin evaluar
argumentos. Acciones callable serializables y acciones globales del admin incluidas.

11 modulos; 104 rutas heredadas; 96 modelos heredados y 12 propios; 67 ModelAdmin;
21 comandos instalados propios, 11 scripts y 19 receivers decorados. Seleccionar
Observatorios no oculta reservas, admin ni tareas compartidas. Solo
portal.portada_inicio se registra en politica: no se afirma habilitacion efectiva.
Centros I+D tiene portada propia sin operacion/modelos propios; las cuatro
verticales siguen delegando detalle/operacion al legado. El catalogo recibe tipo,
el detalle usa slug sin limitarlo por prefijo historico. Otras cuatro secciones
Portal siguen en presentacion sin nuevas capacidades editoriales propias.

Receivers en signals.py (12), models/core.py (2), reservas.py (2), recursos.py (2)
y usuarios.py (1). Guardar Decanato puede activar staff/grupo/permisos de
SolicitudFabricacion; User guarda/crea perfil; Unidad genera configuracion,
horarios, perfiles, modulos y contenido. CodigoReserva descarta excepciones:
observabilidad/recuperacion requiere contrato posterior. No se alteran esos
comportamientos en este inventario. Registro dinamico/connect/aliases, todas las
llamadas ORM y rutas internas de terceros no quedan certificados por AST.

Corregida agrupacion admin: EstadoCapacidad y CambioCapacidad estaban en
Configuracion complementaria; ahora Configuracion institucional con modelos
ya visibles segun permisos, sin ampliar autoridad. Integraciones y legado
manifiesto 1.1.0; sin cambios de modelos, migraciones, datos reales, CSS/JS,
politicas de capacidad o rutas publicas. No hay nueva certificacion responsive:
se conserva validacion visual 160 y agrupador existente.

14 pruebas nuevas: ausencia de SQL/datos secretos, serializacion, filtros que
conservan superficies compartidas, limites de politica, entradas Portal/Centros,
signals en modelos, comandos/scheduler, acciones callable sin ejecutar/globales,
CLI/selecciones invalidas, origen local, agrupacion y limpieza del bloqueo SQL
en exito/error. Focal 14 OK, 46.782 segundos. Ruff completo/check/makemigrations
--check --dry-run correctos. CLI resumen sin SQL reproduce cantidades.
Suite integral: 1126 pruebas, OK, una omitida; 1106.725 segundos.
Log/reportes solo tmp ignorado. No se requiere migracion o restauracion nueva:
no hay cambios de esquema/datos de desarrollo en este bloque.

Guia: docs/superficies-y-autoridades-capacidades.md; arquitectura, manifiestos,
controles y ruta enlazan alcance. Siguiente: M02.4 trazar efectos/asignar
propietarios y contratos; despues ampliar una capacidad acotada con guardas en
servicios/URLs/API/admin/comandos/tareas y pruebas negativas, concurrencia,
conservacion y recuperacion. M02.3 categorias/extensiones antes de extraer
verticales. M02.2 sigue parcial; M01 institucional/M11 abiertos: Django, base y
URLconf siguen compartidos. No mover app labels/tablas sin ensayo M01/M10.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente.
Conservar integracion-version2-funciones y no hacer merge a main/version2.

## 162. Contratos de senales heredadas e integridad de archivos

Primer avance M02.4: revision manual de las 19 senales heredadas, con registro
inmutable/importable sin Django en apps/integraciones/contratos_senales.py y
auditor en auditoria_senales.py. CLI de compatibilidad auditar_contratos_senales
con --resumen/--estricto. Integraciones y legado manifiesto 1.2.0; contrato
senales_heredadas_v1. No mueve receivers, tablas, app labels o autoridad.

Contratos: disparador/sender, lecturas/escrituras logicas, condicion, repeticion,
fallo, encadenamiento, alias, atomicidad, autoridad y responsable de revision.
Propietario actual siempre legado_webcitt; responsable no es traslado de datos.
Codigo y conexiones: 19 contratos/decoradores/conexiones; cero hallazgos.
El inventario general sigue sin SQL: 11 modulos, 104 rutas heredadas, 96 modelos
heredados/12 propios, 67 ModelAdmin, 22 comandos propios, 11 scripts/19 receivers.

Auditor bloquea SQL en todos los aliases durante inspeccion y limpia wrapper
ante errores. No envia senales, ejecuta callbacks, comandos o permisos. Lee
bajo lock dispatcher Django 5.2 y resuelve weakrefs; verifica identidad de
callback/sender, duplicados, conexiones propias adicionales, asincronas y
decoradores sin contrato. Estructura incompatible falla diagnostico. No expone
IDs/UIDs. Arranque Django fuera del wrapper; no sandbox ni auditoria de terceros.
SHA256 de cinco archivos revisados, LF/CRLF normalizados, detecta cambios
pendientes incluidos helpers locales. Actualizar huellas requiere revisar
diff/contratos y probar consumidores; no es firma de seguridad o cobertura
de todas las dependencias externas. No hay guardas globales nuevas en ready.

Hallazgos: efectos sincronos, sin transaccion completa propia; atomicidad depende
del llamador. Horarios/eventos/OneToOne no son reintentos genericos seguros.
Unidad inicializa configuracion/horarios/perfiles/modulos/reglamento en dos
archivos. Decanato concede staff/grupo/permisos y puede guardar User -> perfil;
borrar Decanato no revoca concesiones. Receta/etapa/equipos actualizan fichas e
invalidan integraciones sin ejecutar artefactos. No propagan using explicitamente
ni omiten raw en general. Codigo de reserva descarta excepciones sin observabilidad.
Se documenta el comportamiento; no se cambia momento/autoridad de estos efectos.

Corregida falla concreta validar_archivos_del_artefacto: pre_add inverso
recurso.artefactos_externos.add antes omitido; ahora valida unidad en ambos
sentidos con alias recibido. Rechaza lote mixto completo; set inverso rechazado
preserva relacion previa dentro de transaccion. Misma unidad/repeticion valida.
No elimina historial. No cubre SQL/bulk/through directo o cambio posterior de
unidad; control de servicios/base y concurrencia sigue en M02.2/M10.
Comprobacion citt_db con transaccion READ ONLY: cero asociaciones existentes
y cero cruzadas. No hubo datos historicos que reconciliar; casos con datos son
sinteticos en test_citt_db, no certificacion con asociaciones reales existentes.

19 pruebas nuevas: import puro, inmutabilidad/validacion/encadenamiento, cobertura,
ready repetido, conexiones ausentes/duplicadas/globales, no ejecutar callbacks,
revision de huellas/LF-CRLF, limites de autoridad, CLI estricto/error sin detalles,
error actual del codigo de reserva, SQL denegado/limpieza, M2M directo/inverso,
lotes mixtos, repeticion, rollback de set y alias recibido. Focal con repositorio
paso 7/manifiestos: 38 OK, 20.884 segundos. Ruff completo/check correctos;
makemigrations --check --dry-run sin cambios. CLI estricto sin hallazgos.
Suite integral: 1145 pruebas, OK, una omitida; 985.170 segundos.
Log en tmp/validacion-senales-integral.log ignorado, sin publicar datos privados.

Guia docs/contratos-senales-heredadas.md enlazada desde arquitectura, manifiestos,
inventario y ruta. No cambia modelos/esquema/datos fuente o CSS/JS/HTML/rutas;
no requiere migracion/restauracion nueva ni renueva certificacion responsive.
M02.4 parcial: falta trazar todos los servicios/validadores/modelos consumidores.
M02.2/M02.3/M01 institucional/M11 abiertos; proceso/base/URLconf compartidos.
Siguiente bloque: contrato de fallo/recuperacion del codigo de reserva y sus
consumidores, observabilidad segura y pruebas antes de moverlo; despues guardas
de una capacidad acotada, categorias/extensiones y extraccion por vertical.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente.
Conservar integracion-version2-funciones y no hacer merge a main/version2.

## 163. Asignacion observable y recuperacion de codigos de reserva

Asignacion heredada de codigo de reserva: antes descartaba cualquier excepcion,
incluso un error SQL que podia invalidar la transaccion exterior. Se incorpora
webcitt/services/codigos_reserva.py como servicio compartido del legado, sin
imports de modelos/vistas/dominios al cargar ni nuevas excepciones a los cuatro
imports model->domain congelados. No extrae tabla/app label/receiver/autoridad.

Servicio: fila fresca select_for_update en alias explicitado/estado/router,
atomic/savepoint, preserva codigo persistido no vacio y actualiza solo faltante.
Codigo RL{unidad:03d}-{reserva:06d} conservado; constructor usa laboratorio_id
sin consultar Unidad. Tras savepoint exitoso sincroniza memoria; rollback de
transaccion exterior requiere descartar/recargar instancia. No garantiza
bloqueo equivalente en otros motores ni protege cambios ORM/SQL fuera del servicio.

Receiver no bloqueante conserva creacion sin codigo ante fallo, pero emite
WARNING reserva_codigo_asignacion_fallida. Omite raw y propaga using; update
no reentra. No registra argumentos, IDs, codigo, usuario, SQL o traceback.
Servicio directo propaga errores despues de rollback de savepoint; transaccion
llamadora permanece utilizable. No agrega retries/cola/on_commit globales.

CLI recuperar_codigos_reservas: default cuenta NULL/vacios, sin mutacion.
--aplicar exige unidad positiva; --database alias configurado. Por fila bloqueo
fresco y unidad_esperada impiden reparar fuera del alcance si cambia la unidad.
Lote parcial conserva exitosas; resumen JSON solo contadores y CommandError
ante fallos/cambio de alcance. Evento fijo reserva_codigo_recuperacion_fallida
sin detalles. Errores de consulta/iteracion producen mensaje generico. Reintento
conserva existentes; conteo inicial no es snapshot bajo concurrencia. Herramienta
operativa privilegiada OS/DB, sin API HTTP ni concesion de permisos; el llamador
del servicio debe validar su autoridad. No es historial criptografico de fallos.

Auditoria fuente en desarrollo: cero pendientes; no se aplico reparacion real.
Errores SQL/recuperacion/carrera solo datos sinteticos de test_citt_db.
Consumidores revisados: reservas/ejecucion/comprobantes/guias, aula/asignaturas,
practicas/planificacion, gestion/produccion/seguridad, maquila y reportes/Excel.
No cambia fallbacks, referencias materializadas, QR, fechas o historia. Copias
de sesiones recurrentes siguen limpiando codigo para generar la nueva identidad.

Integraciones/legado manifiestos 1.3.0; contrato senales_heredadas_v1 preservado
en integraciones. Registro declara savepoint/alias propagado/fallo observable.
Huellas revisadas de seis archivos, incluido servicio, LF/CRLF normalizados.
CLI estricto: 19 contratos/decoradores/conexiones, cero hallazgos; cero fallos
descartados y uno no bloqueante observable. Inventario sin SQL: 11 modulos,
104 rutas heredadas, 96 modelos heredados/12 propios, 67 admin, 23 comandos,
11 scripts y 19 receivers. No certifica permisos o aislamiento efectivo.

17 pruebas nuevas: raw/using, no persistida/alcance invalido antes de SQL,
constructor sin consultas, memoria, historico fresco, NULL/vacio/repeticion,
error SQL real sin romper transaccion/memoria, no reentrada/log seguro,
auditoria solo SELECT, unidad separada, movimiento tras seleccion,
recuperacion parcial/reintento y carrera real dos conexiones con una asignacion.
Focal junto a contratos/limites: 38 OK, 13.480 segundos. Ruff completo/check
correctos; makemigrations --check --dry-run sin cambios.
Suite integral: 1162 pruebas, OK, una omitida; 1050.122 segundos.
Log ignorado tmp/validacion-codigos-integral.log; sin publicar datos privados.

Guia docs/codigos-reserva-recuperacion.md enlazada desde arquitectura, contratos,
manifiestos e inventario. No hay CSS/JS/HTML/rutas ni migracion/esquema nueva;
no repite certificacion responsive ni requiere restauracion nueva por DDL.
M02.4 sigue parcial: siguiente bloque revisa escritores/validadores/tareas y
su autoridad por unidad en capacidad acotada de reservas antes de guardas de
suspension. Luego categorias/extensiones/extraccion por vertical.
M02.2/M02.3/M01 institucional/M11 abiertos; proceso/base/URLconf compartidos.
Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente.
Conservar integracion-version2-funciones; no merge a main/version2.

## 164. Autoridad de escritores de reservas y bloqueo de sesiones

M02.4: revisadas las entradas principales de escritura de reservas antes de
ampliar controles de capacidad. Guia docs/escritores-y-autoridad-reservas.md
con entradas HTTP, servicios/primitivas, ORM, admin, tareas y cargas; autoridad,
alcance, efectos, transaccion y pendientes. No certifica escritores dinamicos
ni todos los permisos. No instala suspension institucional de reservas.

Dos fallas concretas: completar_sesion usaba estado de instancia anterior a
transaccion; aplicar_solicitud_cambio dependia solo del permiso de la vista.
Nuevo autorizacion.exigir_autoridad_reserva, solo dos operaciones conocidas,
recibe fila fresca bloqueada del caller, carga cuenta persistida activa y
consulta delegacion en su unidad. No confia en is_active/is_superuser obsoletos
ni staff global. Practicas y reservas siguen permisos distintos. Alcance
explicito distinto se rechaza incluso para superusuario, sin datos de expediente.
No agrega imports de modelos hacia dominios: cuatro excepciones siguen congeladas.

completar_sesion ahora atomic propio, recarga SELECT FOR UPDATE OF self,
revalida titular/unidad/estado pendiente/programacion antes de mutar. Devuelve
instancia fresca; vista consume retorno y pasa unidad_esperada. Reserva
eliminada durante POST produce 404 al recargar, no DoesNotExist/500.
Error posterior a guardar revierte los cambios de su transaccion.
aplicar_solicitud_cambio conserva atomic y bloqueos de solicitud/reserva,
recarga unidad con reserva y exige permiso reservas propio antes de validar
propuesta. Vista pasa unidad_esperada desde slug. Titular no aprueba por ser
titular. Mantiene revision/auditoria/estimacion/notificacion y compuertas existentes.

Guarda de cuenta/objeto/delegacion no sustituye admision de perfil institucional
en middleware ni habilitacion/derechos comerciales. No bloquea todos los cambios
de cuenta/administrador/delegacion hasta commit: no garantiza serializacion de
revocacion posterior. Alias default y politica de instalacion actuales;
no certifica multibase o varias instituciones simultaneas. Bloqueo de una reserva
no resuelve todas las carreras de disponibilidad entre diferentes reservas.

23 pruebas nuevas: guardas directas/operacion desconocida/anonimo/ES-EN,
titular, staff ajeno, cuentas/privilegios/admin/delegacion revocados, modulo
practicas frente a reservas, titular/unidad/estado/programacion frescos,
reserva desaparecida, alcance incluso superusuario, HTTP 403 tras revocacion
y 404 tras eliminacion, rollback tardio y aprobacion concurrente dos conexiones.
Prueba real observa SELECT FOR UPDATE enviado y espera Lock de backend antes de
liberar aprobacion; rechaza estado confirmado y conserva factor. No depende de
consulta larga truncable de pg_stat_activity. Fixtures HTTP con perfil vigente
y assert de invocacion para no confundir bloqueo de middleware con guarda interna.
Focal final contratos de cambio/programacion/arquitectura/idiomas: 57 OK, 43.277 s.

Ruff completo/check correctos; makemigrations --check --dry-run sin cambios.
Tres textos nuevos con gettext; ES/EN 8762 mensajes compilados y --check correcto.
Auditoria estricta de senales: 19 contratos/decoradores/conexiones, cero hallazgos.
Inventario conserva 11 modulos, 104 rutas, 96 modelos heredados/12 propios,
67 admin, 23 comandos, 11 scripts y 19 receivers; no nuevos manifiestos/rutas.
Suite integral final: 1185 pruebas, OK, una omitida; 1012.622 segundos.
Log ignorado tmp/validacion-escritores-integral.log. Primera suite interrumpida
para agregar el caso HTTP de eliminacion; evidencia final es la suite reiniciada.
No se ejecutaron cargas/simulaciones/reparaciones ni modificaron datos reales.

Guia enlazada desde arquitectura, codigos, senales e inventario. No modifica
modelos/esquema/CSS/HTML/JS ni repite certificacion responsive. Sin migracion
nueva o necesidad de restauracion nueva por DDL.
M02.4/M02.2 parciales; siguiente escritor critico registrar_cierre_operativo:
autoridad, fila fresca, repeticion, bloqueos/alias y efectos inventario/finanzas/
produccion sin duplicacion. Luego editar propuestas/gestion/tareas/admin/cargas,
clasificar mantenimiento bajo suspension y cerrar guardas en todas superficies.
M02.3/M01 institucional/M11 abiertos; proceso/URLconf/base/credenciales compartidos.
No se extraen tablas/apps ni se declara aislamiento operativo por esta guarda.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior
sin merge a main/version2, por autorizacion permanente.

## 165. Contrato autonomo y serializado de cierre operativo

Contrato de registrar_cierre_operativo reforzado sin alterar interfaz o datos reales.
Atomic propio, reserva fresca bloqueada FOR UPDATE OF self y autoridad persistida
de reservas/unidad/cuenta activa; unidad_esperada del slug en el panel. La guarda
admite cerrar_operacion y retorna la cuenta fresca para atribucion y excepciones.
No acepta privilegios, unidad o estado obsoletos ni otro alias de base.

Conserva workflow y compuerta documental. Confirmada espera fin del horario;
regularizacion de completada sin detalle exige corregir_cerradas. Cualquier detalle
previo impide repetir efectos, incluso si se cambio erroneamente el estado.
No elimina detalles parciales heredados: requieren revision explicita.
Persiste detalle, liquidacion, completada/atendida/fecha/observaciones en la misma
transaccion que asistencia, consumos, incidencia, ingreso y ejecucion practica.
Copia solo campos del cierre al objeto recibido; panel guarda responsable antes
de recargar y mantiene su orquestacion en la transaccion exterior.

21 pruebas nuevas. Persistencia directa sin save del caller; cuentas/privilegios/
administrador revocados, delegaciones reservas/practicas, alcance incluso para
superusuario, unidad/estado/horario frescos, alias, desaparicion, regularizacion,
ES/EN, rollback de asistencia/consumo/stock/lote/incidencia/ingreso y repeticion con
monto cambiado. POST revocado da 403 con servicio invocado y participantes revertidos.
Dos cierres concurrentes reales PostgreSQL: SELECT FOR UPDATE observado, espera
Lock y un solo ingreso. Focal combinado 127 OK, 47.972 s; focal final 21 OK, 1.054 s.
Primer focal tuvo un error de fixture al intentar refresh desde alias inexistente;
corregido con refresh explicito default, no fallo del servicio.

Suite integral final: 1206 pruebas, OK, una omitida; 724.325 segundos.
Log ignorado tmp/validacion-cierre-integral.log. Ruff/check/migraciones en seco
correctos; sin esquema nuevo. ES/EN 8765 mensajes compilados y verificados.
Auditoria estricta de senales: 19/19/19, cero hallazgos; no certifica estos servicios.
Sin cargas, reparaciones, ejecuciones de cierre o modificaciones de datos reales.
Sin rutas/CSS/HTML/JS nuevos; no renueva certificacion responsive.

M02.4/M02.2 parciales. Servicio directo no reproduce historial, propuestas, avisos
o habilitaciones del panel ni crea orden/lote de produccion/maquila. Siguiente:
orquestacion, escritores de propuestas/gestion, admin/tareas/cargas y controles
de capacidad en todos sus caminos antes de extraer verticales.
Default con configuracion actual sin routers; no soporte multibase certificado
ni serializacion de toda revocacion posterior. Proceso/URLconf/base/credenciales
compartidos: no aislamiento operativo. M02.3/M01 institucional/M11 abiertos.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## 166. Punto de control vigente antes de continuar la reestructura

Revision de cierre antes del siguiente bloque. Codigo ejecutable vigente dafd07ad;
no se modifica Python, modelos, rutas, permisos, CSS/JS/HTML o datos reales.
Se conserva suite integral 165: 1206 pruebas, OK, una omitida; 724.325 s.
No se ejecuta otra suite integral para cambios exclusivamente documentales.
Focal de auditoria: 83 pruebas, OK; 36.303 s (limites, manifiestos, rutas, idiomas,
superficies, cierre operativo y seguridad de produccion).
Ruff/check/migraciones en seco correctos; ES/EN 8765 mensajes verificados.
Senales 19/19/19, cero hallazgos; inventario 11 modulos, 104 rutas heredadas,
96 modelos heredados/12 propios, 67 admin, 23 comandos/11 scripts/19 receivers.
Catalogos academicos: 16 campos compatibles; zona/agenda sin incompatibilidades.
Auditorias de datos solo lectura; sin cargas, reparaciones o cierres reales.

Estado-plan-y-responsive-20260916.md incorpora corte vigente sin borrar historia.
Se corrige el traspaso: migraciones actuales 0201/0007/0001 aplicadas, no 0193;
se retira la afirmacion incorrecta DEBUG=False del entorno local. Ruta,
arquitectura y responsive enlazan el estado actual y separan evidencia historica.
M00 implementado; M02.1/M02.2/M02.4/M09 parciales. M03-M08/M10-M13 pendientes
para sus alcances finales; M01 local probado, cierre institucional pendiente.
Tres apps propias instaladas; paquetes/manifiestos no son once apps de negocio.
Cierre operativo 165 validado; no declarar terminada toda la reestructuracion.

check --deploy de config.settings detecta seis avisos reales: DEBUG, clave debil,
HSTS, redireccion HTTPS y cookies seguras de sesion/CSRF. Entorno de desarrollo,
no listo para produccion. Perfil config.settings_production probado en proceso
separado: bloquea por clave de despliegue. No se publican valores o rotan secretos,
no se alteran .env, credenciales, HTTPS local o sesiones durante esta auditoria.
Completar despliegue endurecido, proxy, recuperacion y controles institucionales
antes de exponer instancia publica; dependencias de seguridad siguen diferidas.
No nueva inspeccion de navegador o certificacion responsive/dispositivos fisicos.

Siguiente: edicion de propuestas y orquestacion de reservas; POST todavia carece
de transaccion propia y GET puede vencer autorizacion. Definir autoridad fresca,
bloqueos, vencimientos/envio repetido/rollback; despues gestion/admin/tareas/cargas,
capacidad operativa completa, categorias extensibles y extraccion por vertical.
M01/M10 son puertas del traslado de datos; aislamiento real M11 aun pendiente.
Publicar COMPUMAX-EC/CITT reestructura-modular y conservar rama estable anterior.

## 167. Envio transaccional y autorizado de propuestas de reservas

Envio de propuestas separado en cambios.enviar_propuesta_cambio con atomic
propio, reserva/solicitud frescas y bloqueadas, cuenta activa persistida,
titular/solicitante/unidad/ventana/estado/campos/base vigentes. Titular es autoridad
de envio; staff, superusuario o administrador ajeno no reemplazan esa identidad.
Guarda enviar_propuesta agregada al contrato cerrado de autorizacion.
Rechaza alias diferente de default, claves fuera de grupos autorizados,
propuesta sin diferencias, reserva iniciada/cerrada y segundo envio.
Persiste propuesta/enviada_en/estado y auditoria en una transaccion; devuelve
solicitud fresca y no modifica reserva, recursos o revisiones.

Helper interno bloquea reserva antes de solicitud. Aplicacion de cambios y
panel de autorizar/rechazar/aprobar usan el mismo orden que gestion/cierres.
Retirada tambien bloquea reserva primero por la relacion de sus avisos.
No declara eliminado cualquier deadlock o cerrado el resto de escritores.
HTTP conserva parser/normalizacion de insumos y errores de formulario;
rechazo de ventana/estado/campos da 409 y formulario fresco, revocacion da 403.
GET vencido muestra estado en memoria sin actualizar expediente/auditoria.
POST vencido rechaza sin materializar vencida. Nueva solicitud por POST autorizado
conserva cleanup anterior, historial y unicidad activa. Plazo comprobado despues
de bloqueos antes del envio, no congelado hasta commit o expiracion por tarea.

28 pruebas nuevas: persistencia/autoria sin cambios en reserva, cuenta/titular/
solicitante/unidad/estado/ventana/campos/base frescos, anonimo/superusuario ajeno,
scope, alias, desaparicion, campos desconocidos, repeticion, ES/EN, rollback real
de auditoria/propuesta, GET sin actualizar, POST vencido/nueva ventana y HTTP
403/409 con servicio invocado. Tres carreras PostgreSQL observan FOR UPDATE,
espera Lock y orden reserva -> solicitud: rechazo conservado, un envio/una
auditoria y retirada con aviso. Primera suite interrumpida para completar
orden de retirada; evidencia integral es la suite final reiniciada. Panel comprueba orden SQL real de autorizacion.
Focal final: 81 pruebas OK, 25.693 s. Primer focal fallo ES/EN por entrada gettext
duplicada que impedia compilar; corregida conservando msgid previo y mejorando
su traduccion. Catalogos finales ES/EN 8769 mensajes, compilados/verificados.

Suite integral final: 1234 pruebas, OK, una omitida; 1406.403 segundos.
Log ignorado tmp/validacion-propuestas-integral.log. Ruff/check correctos;
makemigrations --check --dry-run sin cambios. Senales 19/19/19 cero hallazgos;
esa auditoria no verifica hashes de todos estos escritores. Sin nuevas rutas,
modelos/esquema/manifiestos/CSS/HTML/JS. Sin cargas, reparaciones, envios de
propuestas o cambios de datos reales; pruebas sinteticas en test_citt_db.
No renueva certificacion responsive o habilita produccion institucional.

M02.4/M02.2 parciales. Siguiente: autoridad propia de autorizar/rechazar/retirar,
gestion, tareas/admin/cargas e historial bajo suspension; luego cubrir una
capacidad operativa completa, categorias extensibles y extraccion por vertical.
Perfil institucional sigue en middleware HTTP. Default con configuracion actual,
no multibase/routers certificado ni serializacion de toda revocacion posterior.
Proceso/URLconf/base/credenciales compartidos; M01 institucional/M11 pendientes.
Publicar COMPUMAX-EC/CITT reestructura-modular y conservar rama estable anterior.

## 168. Decisiones autorizadas y transaccionales de solicitudes de cambio

Decisiones de autorizar/rechazar/retirar extraidas de cambios_views a
decisiones_cambio, sin importar vistas desde negocio. Cada servicio tiene
atomic propio, bloqueos reserva -> solicitud, cuenta activa persistida,
unidad esperada y autoridad vigente. Guarda tres nuevas operaciones conocidas;
retirada exige titular de reserva y solicitante actuales, sin override super.
Autorizar/rechazar requieren reservas; practicas/staff/otra unidad no bastan.

Helper compartido con aplicar/enviar carga unidad despues de esperar ambos
bloqueos, evitando administrador obsoleto del snapshot del JOIN bloqueado.
No serializa cualquier revocacion posterior hasta commit, otros catalogos o
escritores externos. Alcance se comprueba incluso para superusuario.
Alias distinto de default rechazado; no certifica routers/multibase.

Autorizar exige solicitada, reserva pendiente/confirmada y solicitante igual
al titular. Una segunda autorizacion no extiende plazo ni campos. Ausencia
de campos conserva todos; seleccion explicita invalida/vacia/desconocida
rechazada sin ampliarla. HTTP lista/JSON de lista conservados; mal formato,
elementos no textuales/profundidad excesiva dan 400. Rechazo exige motivo
textual de cinco caracteres despues de strip. Conflictos 409, revocacion 403.
Retirada/rechazo limpian activas con reserva cerrada/ventana vencida sin cambiar
reserva. Retirada atribuye revisada_por al titular. Conserva propuesta/base/
ventana/historial/unicidad. Cambios, auditoria y aviso interno atomicos;
correo previo on_commit/reintentos no equivale a entrega SMTP atomica.
Notificador al personal compartido con solicitar cambio, sin helper muerto
o duplicacion; autorizado por su caller, no gateway de negocio propio.

31 pruebas nuevas de persistencia/autoria, autoridad/cuenta/privilegios/
delegacion/unidad/titular/solicitante/estado vigentes, scope/alias/desaparicion,
campos/motivo, repeticion, limpieza, ES/EN y HTTP 403/400 con assert de invocacion.
Rollback real despues de aviso revierte solicitud/auditoria/aviso y callback.
Tres carreras PostgreSQL observan FOR UPDATE y espera Lock: doble autorizacion,
rechazo frente a retirada y administrador revocado mientras espera reserva.
Primer focal fallo por fixture que recargaba reserva antes de probar relacion
obsoleta; corregido manteniendo relacion original. Focal final 112 OK, 32.668 s.
Suite completa: 1265 pruebas, OK, una omitida; 1085.389 segundos.
Log ignorado tmp/validacion-decisiones168-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8785 mensajes compilados/verificados.
Senales 19/19/19 cero hallazgos; no certifica hashes de todos estos escritores.

M02.4/M02.2 siguen parciales: siete servicios reforzados no cubren la capacidad
completa. Siguiente: solicitar cambio, gestion/cancelacion y otros escritores,
primitivas/tareas/admin/cargas, mantenimiento bajo suspension; despues controles
de capacidad completa, categorias extensibles y extraccion por vertical.
Sin rutas/modelos/esquema/interfaz nuevos, cambios de datos reales o nueva
certificacion responsive. Perfil institucional sigue en middleware HTTP.
M01 institucional/M11 pendientes; base/proceso/URLconf/credenciales compartidos.
No habilita produccion ni certifica aislamiento por carpetas. Publicar rama
reestructura-modular COMPUMAX-EC/CITT, conservar estable anterior.

## 169. Solicitud de cambio y cancelacion propias de reservas

Nueva solicitud de cambio y cancelacion propia extraidas de vistas a
solicitudes_propias. Servicios con transaccion propia, Reserva fresca bloqueada,
cuenta activa/titular/unidad vigentes. Dos operaciones cerradas nuevas en guarda:
solicitar_cambio/cancelar_propia; nueve en total. Administrador/superusuario ajeno
no sustituyen titular. Alias distinto de default rechazado. Retorno fresco y
unidad cargada despues de esperar bloqueos; no guardan instancia obsoleta.

Crear admite pendiente/confirmada y motivo textual de 10-1200 tras strip.
Bloquea reserva -> cambio activo. Ventana anterior vencida conserva propuesta/
fechas y pasa a vencida solo dentro de crear nueva solicitud. Revision inicial
unica y base actual, solicitud/auditoria/aviso internos atomicos; auditoria
traza PK de ventana vencida cuando aplica. Conflicto activo incluye solicitud
del expediente ya autorizado, sin duplicar revision/aviso/auditoria.
Solo traduce restriccion PostgreSQL una_solicitud_cambio_activa_por_reserva
despues de rollback; otros IntegrityError no se ocultan como duplicado.
No certifica traduccion de restriccion en otros motores.

Cancelar admite solo pendiente y conserva workflow/autoria/fecha/origen/motivo/
texto documental previo. Motivo opcional normalizado/truncado a 500. Cancelacion,
cierre de cambios activos y auditoria atomicos; no borra expediente/propuesta/
recursos/revision/comprobante ni agrega aviso ajeno al flujo. Confirmada puede
solicitar cambio pero no cancelar por titular. Repeticion rechazada sin reescribir
motivo/autoria. Vistas adaptan JSON: alta 201, motivo 400, revocacion 403,
lectura ajena/desaparicion 404, estado/duplicado 409; payload y cancelacion
conservados. Perfil/admisiones institucionales siguen en middleware HTTP.
Correo conserva on_commit/reintentos, no entrega SMTP atomica.

32 pruebas nuevas: persistencia/base/autoria, cuenta/titular/unidad/estado frescos,
scope/alias/desaparicion, motivos/repeticion, vencimiento/historial, rollback
real de aviso y auditoria, restriccion SQL real y otro IntegrityError no oculto,
ES/EN y HTTP 403/404/409 con servicio invocado. Cuatro carreras PostgreSQL observan
FOR UPDATE y espera Lock: doble solicitud, solicitud -> cancelacion, cancelacion
previa a solicitud y cuenta desactivada durante espera. Focal final 132 OK,
68.825 s; incluye tres recorridos existentes de cancelacion/coincidencia.
Primer focal fallo en foto de alias y expectativa EN; foto consulta por PK
default, traduccion previa mejorada sin duplicar msgid. No debilita contrato.
Suite completa: 1297 pruebas, OK, una omitida; 901.265 segundos.
Log ignorado tmp/validacion-propias169-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8793 mensajes compilados/verificados.
Senales 19/19/19 cero hallazgos; no certifica hashes de todos estos escritores.

M02.4/M02.2 parciales: nueve servicios no cubren capacidad completa. Siguiente:
orquestacion de gestion y otros escritores/primitivas/tareas/admin/cargas,
mantenimiento bajo suspension, luego capacidad completa/categorias/extraccion.
Default actual sin routers/multibase ni toda revocacion posterior serializada.
Sin rutas/modelos/esquema/interfaz o datos reales modificados; no nueva
certificacion responsive ni produccion institucional habilitada. M01/M11
pendientes; base/proceso/URLconf/credenciales compartidos. Publicar en
COMPUMAX-EC/CITT reestructura-modular y conservar estable anterior.

## 170. Gestion administrativa simple de reservas

Asignar responsable, anotar y solicitar informacion adicional salen del cuerpo
monolitico de gestion_reserva_accion_view y delegan en
reservas.administracion.gestionar_reserva_administrativa. La ruta y el JSON se
conservan. El servicio tiene atomic propio en default, bloquea primero Reserva,
recarga estado/unidad vigentes y exige cuenta activa y permiso de reservas con
unidad_esperada. Tres operaciones nuevas entran en la guarda cerrada:
asignar_responsable, anotar_reserva y solicitar_informacion; doce en total.

Asignar bloquea y valida un ResponsableUnidad actual de la misma unidad, con
cuenta, activo y recibe_reservas; no acepta la relacion obsoleta del caller.
Respeta los estados pendiente/confirmada/en_proceso del workflow. Anotar admite
todos los estados; solicitar informacion solo pendiente/confirmada. Las dos
exigen texto y las observaciones del servicio se limitan a 1200 caracteres.
Solicitar informacion crea el aviso existente; anotar no agrega uno. Asignar
marca como leidos los avisos sin responsable. Reserva, bitacora LogEntry,
auditoria y aviso quedan en la misma transaccion, con rollback tardio completo.

La fotografia de auditoria, agregado de observaciones y LogEntry se movieron a
reservas.trazabilidad como implementacion comun. Gestion conserva wrappers
internos para sus acciones heredadas, evitando cambiar sus contratos mientras
usa la misma representacion. No se crean rutas, modelos o migraciones.

11 pruebas nuevas: asignacion y trazabilidad, nota/solicitud sin cambio de estado,
accion/observacion/alias, ES/EN, estado/unidad/cuenta/responsable frescos, rollback
real de reserva/aviso/bitacora/auditoria y revocacion entre vista y servicio con
403. Una carrera PostgreSQL observa SELECT FOR UPDATE y espera Lock; dos notas
concurrentes conservan ambas, dos auditorias y dos entradas de bitacora. Focal
final con dos recorridos heredados: 13 pruebas OK, 7.073 s. El primer focal solo
ajusto la expectativa de campo vacio None/"" del fixture; no debilito el servicio.

Suite completa: 1308 pruebas, OK, una omitida; 1294.069 segundos. Log ignorado
tmp/validacion-administracion170-final.log. Ruff/check correctos, migraciones
en seco sin cambios, ES/EN 8799 mensajes compilados/verificados. Senales
19/19/19, cero hallazgos; esa auditoria no certifica todos estos escritores.

M02.4/M02.2 siguen parciales. Siguiente: extraer aprobacion/rechazo/cancelacion
administrativa e inicio/cierres alternos/correccion por bloques coherentes;
despues primitivas/tareas/admin/cargas, mantenimiento bajo suspension, capacidad
completa, categorias extensibles y extraccion vertical. Default actual sin
routers/multibase ni serializacion de toda revocacion posterior. Sin datos reales,
interfaz o certificacion responsive nueva. M01 institucional/M11 pendientes;
base/proceso/URLconf/credenciales compartidos. Publicar reestructura-modular y
conservar integracion-version2-funciones.

## 171. Rechazo y cancelacion administrativa de reservas

Rechazo y cancelacion por laboratorio salen del cuerpo monolitico de
gestion_reserva_accion_view y delegan en
reservas.decisiones_reserva.decidir_reserva. Ruta, payload y respuesta JSON se
conservan. El servicio tiene atomic propio en default, bloquea primero Reserva,
recarga estado/unidad vigentes y exige cuenta activa, permiso de reservas y
unidad_esperada. Dos operaciones nuevas entran en la guarda cerrada:
rechazar_reserva y cancelar_reserva; catorce en total.

Rechazar admite solo pendiente, registra validada_por/fecha_validacion y agrega
la observacion. Cancelar admite pendiente o confirmada y conserva la cancelacion
trazable: autor, fecha, origen laboratorio y motivo. Ambas exigen motivo textual
no vacio de hasta 1200 caracteres. Si existe receta, cancelan ordenes de practica
abiertas y liberan su bloqueo; tambien cierran solicitudes de cambio activas,
marcan avisos incompatibles y notifican al titular. Reserva, efectos, LogEntry,
auditoria y aviso forman una transaccion; un fallo tardio revierte todo.

9 pruebas nuevas: persistencia/autoria, cierre de solicitudes/avisos, entrada y
alias invalidos, ES/EN, estado/unidad/cuenta frescos, rollback real y revocacion
entre vista y servicio con 403. Una carrera PostgreSQL observa SELECT FOR UPDATE
y espera Lock: rechazo y cancelacion concurrentes producen un solo cierre, una
auditoria, una bitacora y un aviso. Focal con tres recorridos heredados: 12 OK,
5.116 s. Conjunto ampliado de reservas/procesos: 96 OK, 15.528 s.

Suite integral final: 1317 pruebas, OK, una omitida; 601.415 segundos. Log
ignorado tmp/validacion-decisiones171-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8803 mensajes compilados/verificados.
Senales 19/19/19, cero hallazgos; esa auditoria no certifica todos los escritores.

M02.4/M02.2 siguen parciales. Permanecen en gestion actualizar, aprobar, iniciar,
completar, no_presentado y no_atendida; completar solo delega el nucleo operativo
desde 165. Siguiente: extraer aprobacion con agenda/responsable/practica/
planificacion como una unidad coherente, luego inicio/cierres/correccion y despues
primitivas/tareas/admin/cargas. Sin datos reales, rutas, modelos, esquema o
interfaz modificados; no nueva certificacion responsive. M01 institucional/M11
pendientes; base/proceso/URLconf/credenciales compartidos. Publicar
reestructura-modular y conservar integracion-version2-funciones.

## 172. Aprobacion integral y agenda compartida de reservas

La aprobacion sale del cuerpo monolitico de gestion_reserva_accion_view y
delega en reservas.aprobacion.aprobar_reserva. La ruta, el payload, los estados
HTTP y la respuesta JSON se conservan. El servicio tiene atomic propio en
default, bloquea primero la Unidad para serializar aprobaciones de su agenda y
despues la Reserva vigente. Revalida cuenta activa, permiso de reservas, unidad
esperada y transicion; aprobar_reserva eleva a quince las operaciones conocidas
por la guarda cerrada de autoridad.

La compuerta documental se evalua antes de mutar. La asignacion explicita exige
un ResponsableUnidad actual de la misma unidad, activo, receptor de reservas y
con cuenta activa. La automatica bloquea los candidatos en orden determinista,
conserva un responsable vigente o elige por carga, rol, orden y PK. La reserva
solo pasa de pendiente a confirmada despues de volver a validar aforo, bloqueos
administrativos, equipos, espacios y software. Reserva, responsable, validador,
orden de practica, planificacion, avisos, LogEntry y auditoria se confirman en
una transaccion; un fallo tardio revierte el conjunto.

La consulta persistente de conflictos se movio desde reservas.views a
reservas.conflictos. Creacion de reservas, solicitudes de cambio, cronograma,
visitas, reprogramacion administrativa y aprobacion comparten ahora esa frontera
sin importar una vista desde negocio. El bloqueo opcional ordena reservas por PK.
El bloqueo de Unidad serializa las aprobaciones que usan este servicio; no se
afirma que todos los escritores externos adopten ya el mismo bloqueo.

10 pruebas nuevas cubren aprobacion explicita/automatica, autoria y trazabilidad,
cuenta de responsable, entradas/alias, ES/EN, estado/unidad/cuenta frescos,
compuerta documental, rollback tardio, revocacion HTTP y concurrencia PostgreSQL.
La carrera observa espera sobre Unidad y distribuye dos aprobaciones entre dos
responsables. Focal final con consumidores de conflictos: 156 pruebas OK,
82.859 s. Suite integral: 1327 pruebas, OK, una omitida; 641.935 segundos.
Log ignorado tmp/validacion-aprobacion172-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8805 mensajes compilados/verificados.
Senales 19/19/19, cero hallazgos; esa auditoria no certifica todos los escritores.

M02.4/M02.2 siguen parciales. Permanecen en gestion actualizar, iniciar,
completar, no_presentado y no_atendida; completar solo delega el nucleo desde
165. Siguiente: extraer inicio y cierres alternos como bloque coherente, luego
correccion/actualizacion y despues primitivas, tareas, admin y cargas. Sin datos
reales, rutas, modelos, esquema o interfaz modificados; no nueva certificacion
responsive. M01 institucional/M11 pendientes; base, proceso, URLconf y
credenciales siguen compartidos. Publicar reestructura-modular y conservar
integracion-version2-funciones.

## 173. Inicio y cierres alternos de reservas

Iniciar, no_presentado y no_atendida salen del cuerpo monolitico de
gestion_reserva_accion_view y delegan en
reservas.transiciones_operativas.transicionar_reserva_operativa. La ruta, el
payload, los estados HTTP y la respuesta JSON se conservan. El servicio tiene
atomic propio en default, bloquea Reserva y revalida cuenta activa, permiso de
reservas, unidad esperada y estado. Una operacion cerrada nueva eleva a dieciseis
las conocidas por la guarda de autoridad.

Iniciar conserva compuerta documental, control de ingreso, fecha de inicio,
responsable opcional y cierre de solicitudes de cambio. No presentado y no
atendida exigen motivo y horario finalizado o regularizacion autorizada; guardan
resultado, fecha y detalle. La inasistencia marca los participantes como no
asistieron; no atendida conserva su asistencia. Los cierres alternos cancelan la
orden de practica cuando existe, limpian avisos de cierre/riesgo y cierran cambios
activos. Reserva, participantes, orden, cambios, avisos, LogEntry y auditoria se
confirman o revierten juntos.

responsables.resolver_responsable_operativo centraliza la asignacion explicita
que antes se repetia en administracion, aprobacion y el nuevo servicio. Exige
misma unidad, relacion activa, recepcion de reservas y cuenta vinculada activa;
los tres callers bloquean la fila dentro de su transaccion. La vista heredada
queda con actualizar y completar; completar ya delega el nucleo desde 165 pero
mantiene participantes, habilitaciones, avisos y trazabilidad exteriores.

10 pruebas nuevas cubren inicio y cierres, participante/avisos/cambio activo,
responsable, entradas/alias/horario, ES/EN, estado/unidad/cuenta frescos,
compuerta documental, rollback tardio, revocacion HTTP y carrera PostgreSQL.
Dos cierres rivales esperan SELECT FOR UPDATE y solo uno deja estado, aviso,
bitacora y auditoria. Directo: 10 OK, 2.810 s. Focal con aprobacion, asignacion,
panel, seguridad, visitas, programacion y procesos: 150 OK, 298.112 s.

Suite integral: 1337 pruebas, OK, una omitida; 1767.513 segundos. Log ignorado
tmp/validacion-transiciones173-integral.log. Ruff/check correctos, migraciones
en seco sin cambios, ES/EN 8809 mensajes compilados/verificados. Senales
19/19/19, cero hallazgos; esa auditoria no certifica todos los escritores.

M02.4/M02.2 siguen parciales. Siguiente: extraer la orquestacion exterior de
completar alrededor de registrar_cierre_operativo; luego actualizar/correccion,
primitivas, tareas, admin y cargas. Sin datos reales, rutas, modelos, esquema o
interfaz modificados; no nueva certificacion responsive. M01 institucional/M11
pendientes; base, proceso, URLconf y credenciales siguen compartidos. Publicar
reestructura-modular y conservar integracion-version2-funciones.

## 174. Finalizacion integral de reservas fuera de la vista

La accion completar deja de compartir su transaccion con
gestion_reserva_accion_view. El nuevo servicio
reservas.finalizacion.completar_reserva bloquea la Reserva, revalida cuenta,
permiso, unidad y estado, comprueba documentacion y horario, resuelve el
responsable vigente y sincroniza participantes antes de delegar el detalle
operativo en registrar_cierre_operativo. Habilitaciones por induccion, detalle
de cierre, solicitudes de cambio, avisos, LogEntry y RegistroAuditoriaUnidad se
confirman o revierten dentro del mismo atomic.

reservas.participantes centraliza la fotografia institucional, validacion y
asistencia que antes eran funciones privadas de reservas.views y gestion.py.
Creacion, cambios, visitas y administracion conservan su comportamiento mediante
esa frontera compartida. La ruta, payload, respuesta JSON y estados HTTP del
panel no cambian; documentacion pendiente y horario no finalizado continúan en
409, entradas invalidas en 400 y perdida de autoridad en 403.

Dos pruebas nuevas comprueban la finalizacion completa y el rollback de todos
los efectos cuando falla una operacion posterior al nucleo. La prueba de
revocacion durante el POST ahora intercepta el servicio exterior. Directo: 23
pruebas OK, una carrera PostgreSQL omitida fuera de ese motor. Focal con panel,
practicas, programacion, seguridad, procesos, visitas, maquila y cambios: 185
pruebas OK, 170.732 s. Suite integral: 1339 pruebas, OK, una omitida; 933.797 s.

Ruff y Django check correctos; migraciones en seco sin cambios. Catalogos ES/EN
con 8810 mensajes traducibles mas cabecera, compilados mediante msgfmt.py y
verificados en ambos idiomas. Senales 19/19/19, cero hallazgos. No se modificaron
HTML, CSS o JavaScript y no se atribuye una nueva certificacion responsive. No
hubo cambios de rutas, modelos, esquema o datos reales.

gestion_reserva_accion_view conserva solamente actualizar/correccion como
escritor heredado. M02.4/M02.2 siguen parciales; el siguiente bloque debe extraer
esa correccion completa y luego revisar primitivas, tareas, admin y cargadores
antes de declarar la capacidad aislada. M01 institucional y M11 permanecen
pendientes; base, proceso, URLconf y credenciales siguen compartidos. Publicar
reestructura-modular y conservar integracion-version2-funciones.

## 175. Correccion integral de reservas fuera de la vista

La ultima escritura directa de gestion_reserva_accion_view sale al servicio
reservas.correccion.corregir_reserva. La vista conserva ruta, payload, respuesta
JSON y clasificacion HTTP: transicion, recurso o reprogramacion incompatibles en
409; datos invalidos en 400; perdida de autoridad en 403. El servicio bloquea
primero Unidad y luego Reserva para compartir el orden de creacion/aprobacion,
recarga cuenta, permiso, alcance y estado, y eleva a diecisiete las operaciones
cerradas conocidas por autorizacion.

La transaccion abarca fecha y horario, recursos, condiciones comerciales,
participantes, consumibles, adjuntos, responsable, revision inicial y correccion,
planificacion de practica, solicitudes de cambio, avisos, notificacion, LogEntry
y RegistroAuditoriaUnidad. Un fallo de auditoria posterior revierte todo el
expediente persistido. Dos correcciones concurrentes de la misma unidad esperan
el bloqueo comun antes de validar agenda.

reservas.horarios contiene jornadas_habilitadas y validar_horario_operativo;
creacion conserva aliases compatibles, mientras cambios, visitas y pruebas usan
la frontera publica. reservas.adjuntos concentra cantidad, extensiones y 25 MB
por archivo. gestion.py baja de 4859 a 4344 lineas, su accion de reservas de 672
a 399, y reservas.views de 3234 a 3087. No se cambiaron rutas, modelos, esquema,
HTML, CSS, JavaScript ni datos reales.

Seis pruebas nuevas cubren persistencia y autoria, revisiones, rollback tardio,
unidad/cuenta frescas, entrada y alias invalidos, revocacion durante POST y la
carrera PostgreSQL por Unidad. Directo: 6 OK. Focal ampliado con panel, cambios,
horarios, aprobacion, administracion, transiciones, solicitudes propias, visitas,
programacion y reservas: 252 OK, 137.613 s. Suite integral: 1345 pruebas OK, una
omitida, 794.142 s.

Ruff, Django check y migraciones en seco correctos. Catalogos ES/EN sin cambios,
con 8810 mensajes traducibles mas cabecera y binarios vigentes. Senales
19/19/19, cero hallazgos. M02.4/M02.2 siguen parciales: el siguiente bloque debe
inventariar primitivas, tareas, admin y cargadores de reservas, y retirar las
dependencias restantes de cronograma, visitas y guias hacia reservas.views antes
de dividir crear_reserva. M01 institucional y M11 permanecen pendientes; base,
proceso, URLconf y credenciales siguen compartidos. Publicar reestructura-modular
y conservar integracion-version2-funciones.

## 176. Contratos de periodo y guia fuera de reservas.views

La resolucion del periodo academico aplicable a una reserva vive ahora en
`reservas.periodos.resolver_periodo_reserva`. Creacion de reservas, cronograma y
visitas consumen esa frontera publica para obtener PAO, version y semana, con la
misma seleccion por actividad, codigo solicitado o fecha y los mismos errores de
calendario publicado. Las pruebas de configuracion institucional dejaron de
depender de una funcion privada de la vista.

`reservas.guia_contrato` contiene los campos y obligatorios del formulario de
guia integrada. La vista de creacion y la vista previa PDF comparten el mismo
contrato sin que `guias.py` importe `reservas.views`. Una prueba AST recorre el
negocio de unidades y rechaza nuevas importaciones de la vista monolitica; solo
se exceptua `reservas/__init__.py`, que sigue siendo la fachada publica de
endpoints. La busqueda global no conserva referencias al nombre privado
`_resolver_periodo_reserva`.

El commit de codigo `9729ea1d` anade dos modulos y reduce `reservas/views.py` de
3.087 a 3.020 lineas; el paquete pasa de 37 a 39 modulos internos. No cambia
rutas, modelos, esquema, datos reales, HTML, CSS ni JavaScript. No corresponde
renovar la certificacion responsive.

Validacion: dos lotes focales de 31 y 23 pruebas correctos; suite integral de
1.346 pruebas correcta, una omitida, 978,032 s. Ruff, Django check,
`makemigrations --check --dry-run` y `git diff --check` correctos. Auditoria de
senales 19/19/19, cero hallazgos. Catalogos ES/EN sin cambios.

M02.4/M02.2 siguen parciales. Siguiente: inventariar primitivas, tareas, admin y
cargadores de reservas para fijar autoridad, consumidores y efectos; despues
dividir `crear_reserva` por etapas y casos de uso. M01 institucional y M11
permanecen pendientes; base, proceso, URLconf y credenciales siguen compartidos.
Publicar `reestructura-modular` y conservar `integracion-version2-funciones`.

## 177. Cierre de escritura directa del expediente en Django Admin

El inventario de superficies de reservas encontro dos caminos administrativos
que aun permitian alterar datos operativos fuera de los casos de uso:
`ProgramacionReservaAdmin` y `RegistroParticipanteReservaAdmin`. Ambos heredan
ahora de `_ExpedienteSoloLecturaAdmin`; todos sus campos concretos son de solo
lectura y no admiten altas ni eliminaciones desde Django Admin. Cronograma,
asistencia y participantes se mantienen sincronizados exclusivamente por los
flujos de reservas que aplican transacciones, permisos y auditoria.

Una prueba de regresion comprueba el contrato completo para los dos modelos. No
se modificaron rutas, modelos, esquema, datos reales, HTML, CSS ni JavaScript;
por ello no corresponde renovar la certificacion responsive.

Validacion: 15 pruebas directas de administracion correctas; 44 recorridos
focales de administracion, reportes, FT02 y programacion correctos; suite
integral de 1.347 pruebas correcta, una omitida, 988,174 s. Ruff, Django check,
`makemigrations --check --dry-run` y `git diff --check` correctos. Auditoria de
senales 19 contratos, 19 decoradores y 19 conexiones propias, cero hallazgos.

Estado: M00 implementado; M02.1 avanzado; M02.2/M02.4 parciales y activos. El
siguiente bloque debe cerrar vencimientos, recordatorios y sincronizaciones
automaticas con alcance de unidad, suspension, idempotencia y recuperacion.
Despues siguen comandos/cargadores y la division de `crear_reserva`. M01
institucional, M02.3 y M03-M13 permanecen pendientes en los alcances descritos
por la auditoria; base, proceso, URLconf y credenciales siguen compartidos. El
commit de codigo es `5dbc2d14`.

## 178. Alcance por unidad e idempotencia del ciclo automatico

`procesar_recordatorios_reservas` acepta ahora una Unidad explicita y propaga
ese alcance a vencimientos, recordatorios, cierres pendientes, responsables,
riesgos operativos, reintentos de correo y avisos de guias de sesion. El comando
incorpora `--unidad <slug>` y valida la existencia antes de cualquier efecto;
sin el argumento conserva el recorrido institucional compatible con los
programadores instalados. `--simular` mantiene correo desactivado y rollback.

Cada intento SMTP se reclama en `_reclamar_intento_email` bajo
`select_for_update`. Dos ejecutores no pueden incrementar y enviar a la vez la
misma notificacion; si el proceso falla despues del reclamo, el intervalo ya
existente permite recuperarla sin duplicar el aviso interno. La entrega externa
permanece fuera de la transaccion de base, como requiere un efecto SMTP.

Cuatro pruebas nuevas cubren aislamiento entre unidades, alcance de reintentos,
reclamo unico y contrato del comando. Directo: 18 OK. Focal con programacion,
FT02 y superficies: 52 OK, 71,158 s. Suite integral: 1.351 OK, una omitida,
953,429 s. Ruff, Django check, migraciones en seco, diff y senales 19/19/19 sin
hallazgos. No se modificaron rutas, modelos, esquema, datos reales, HTML, CSS o
JavaScript; no corresponde renovar la certificacion responsive.

La suspension institucional de reservas no se instala en este bloque: hacerlo
antes de cubrir rutas, tareas, comandos y exportaciones produciria un interruptor
parcial. Siguiente: revisar `inicializar_revisiones_reservas`, sincronizacion FT02
y cargadores; despues dividir `crear_reserva`. M02.2/M02.4 siguen parciales y la
base, proceso, URLconf y credenciales continuan compartidos. Codigo `993d296f`.

## 179. Mantenimiento historico de reservas acotado por unidad

`reservas.mantenimiento` concentra la inicializacion de revisiones y la
sincronizacion FT02 historica. Ambos servicios exigen el slug de una Unidad,
bloquean primero esa Unidad y despues sus Reservas por PK, y ejecutan cada unidad
en una sola transaccion. Los comandos rechazan la omision de `--unidad` antes de
escribir y conservan `--simular` con rollback de revisiones, planificaciones y
auditoria.

La busqueda de lineas base usa una subconsulta `EXISTS`, compatible con
`FOR UPDATE` de PostgreSQL, y detecta una revision 1 ausente aunque existan
revisiones posteriores. La sincronizacion conserva idempotencia y registra
auditoria solo cuando crea o actualiza FT02. Un fallo tardio de la revision o de
la auditoria revierte todo el alcance local.

Ocho pruebas nuevas cubren requisito de alcance, aislamiento entre unidades,
idempotencia, simulacion, reparacion historica y rollback tardio. Directo: 18 OK.
Focal ampliado: 89 OK. Suite integral: 1.359 OK, una omitida, 497,398 s. Ruff,
Django check, migraciones en seco, diff y senales 19/19/19 sin hallazgos. No se
modificaron rutas, modelos, esquema, datos reales ni interfaz; no corresponde
renovar la certificacion responsive. Codigo `cafb643a`.

Siguiente: auditar y separar cargadores de mantenimiento y datos demo; despues
dividir `crear_reserva`. M02.2/M02.4 siguen parciales; M01 institucional, M02.3
y M03-M13 mantienen el alcance pendiente de la auditoria vigente.

## 180. Cargadores demostrativos cerrados por entorno y unidad

`cargar_pruebas_fablab` y `cargar_escenarios_evaluacion_fablab` se clasifican
explicitamente como cargas ficticias. El mixin `management.datos_demo` exige
`SLCID_ALLOW_DEMO_DATA_COMMANDS=True`, `--unidad <slug>` y
`--confirmar-datos-demo` antes de consultar o escribir. Ya no existe un slug
predeterminado. `config.settings_production` fuerza la capacidad a False aunque
la variable exista en el entorno.

Ambos comandos conservan una unica transaccion, bloquean la Unidad y admiten
`--simular`; el recorrido se ejecuta completo y se revierte antes de salir. Un
fallo tardio del cargador base tambien revierte recursos, usuarios relacionados,
reservas y cambios de la unidad. No envian correo. Sus codigos y cuentas demo
siguen siendo compartidos, por lo que no son semillas institucionales ni se
deben ejecutar en paralelo o sobre datos reales.

Cinco pruebas nuevas cubren entorno cerrado, alcance, confirmacion, simulacion
de los dos comandos y rollback tardio. Directo: 6 OK. Focal ampliado: 37 OK.
Suite integral: 1.364 OK, una omitida, 981,657 s. Ruff, check, migraciones, diff
y senales 19/19/19 correctos. Sin cambios de rutas, modelos, esquema o interfaz;
no corresponde renovar responsive. Codigo `d7f5c62f`.

Siguiente: dividir `crear_reserva` por etapas y casos de uso sin cambiar su
contrato HTTP. M02.2/M02.4 siguen parciales; la suspension de capacidad se
instalara despues de proteger todas las superficies.

## 183. Suspension integral y recuperable de reservas

`legado_webcitt.reservas_operativas` gobierna las operaciones que modifican
reservas mientras el contexto siga en `webcitt`. Protege creacion, aprobacion,
decisiones, cambios, correccion, inicio, cierre, cancelacion, visitas, ingreso,
practicas, comprobantes de pago, tareas, mantenimiento y cargadores demo. La
suspension no oculta consultas, historial ni PDF; el ciclo automatico conserva
pendientes y los recupera tras reactivar, y el auditor de codigos mantiene su
modo de solo lectura.

La coordinacion usa advisory locks compartidos para escritores y exclusivo
para el cambio institucional en PostgreSQL. Las reservas independientes siguen
concurrentes y la suspension espera operaciones activas antes de impedir nuevas.
Otros motores conservan el fallback de fila. El admin ofrece Inicio y reservas
como capacidades separadas, con version esperada, motivo e historial inmutable.

Focal de reservas: 204 OK. Manifiestos/superficies: 27 OK. Integral: 1.392 OK,
una omitida, 501,783 s. Ruff, check, migraciones en seco, ES/EN compilado y diff
correctos. Sin cambios de esquema, rutas publicas o datos reales. Codigo
`7edae539`. Siguiente: bloque 184, unica auditoria final; despues aceptacion de
Laboratorios y continuidad funcional de Plantas piloto.

## 184. Auditoria final y cierre de Laboratorios

El bloque 184 cierra la estabilizacion arquitectonica sin cambios de codigo
ejecutable. `auditar_contratos_senales --resumen --estricto` confirma 19
contratos, 19 decoradores y 19 conexiones propias, cero hallazgos y cero fallos
descartados. `auditar_modulos` conserva 11 modulos y un plan valido;
`auditar_superficies_capacidades` registra 104 rutas y 96 modelos heredados, 12
modelos propios, 67 administradores, 23 comandos, 11 scripts y 19 receivers.

La evidencia funcional base es la suite integral del bloque 183: 1.392 pruebas
correctas, una omitida, 501,783 s. La aceptacion definitiva de Laboratorios
agrega 277 pruebas correctas en 86,159 s sobre catalogo, unidades, gestion,
reservas, capacidad, practicas, documentos, servicios, seguridad y admin.
Django check, `makemigrations --check --dry-run` y Ruff quedan limpios.

La revision de navegador suma 770 combinaciones sin incidencias: 182 publicas,
574 autenticadas para estudiante, docente, coordinacion y administrador, y 14
del visor PDF. Cubre ES/EN y 360, 390, 768, 1024, 1200, 1366 y 1920 px. No hay
desbordamientos ni errores JavaScript; el PDF es valido, usa la misma pestana y
cierra con Escape. La ejecucion autenticada usa una base y sesiones temporales
que se eliminan al finalizar.

Laboratorios queda aceptado y congelado funcionalmente salvo correcciones
criticas. La fase general no continua con nuevas auditorias. Quedan como deuda
declarada M01 institucional, M02.3, M10-M13, CSP `unsafe-inline`, CI ausente y
la conciliacion de alertas de dependencias antes de una entrega. El monolito
modular aun comparte proceso Django, URLConf y PostgreSQL, por lo que la
aceptacion no demuestra aislamiento fisico ni recuperacion institucional.

La siguiente etapa es Plantas piloto: planificacion completa, completitud
administrable, repositorio trazable y una sola aceptacion funcional. Despues se
continua con Centros experimentales, Observatorios y Centros I+D.

## 185. Planificacion completa de Plantas Piloto

El primer bloque posterior a la aceptacion de Laboratorios esta completo.
`PlanVentas` define un horizonte semanal o mensual y enlaza opcionalmente un
unico `PlanMaestro`; `LineaPlanVentas` conserva por producto el promedio de las
tres ventanas historicas, pronostico, compromisos, docencia, ajuste, total,
valor y equivalencia de materia prima base. La migracion 0202 agrega ambas
tablas y el enlace uno a uno desde la linea maestra hacia su fuente comercial.

La capa de aplicacion calcula ventas desde `MovimientoProducto`, compromisos y
docencia desde `Reserva`, y agrupa por periodo, familia y unidad base. La
aprobacion exige demanda positiva y un maestro en borrador que cubra el
horizonte. La incorporacion crea o actualiza una sola corrida por linea de
demanda abierta y trae los compromisos mediante el flujo preexistente; repetir
la accion no duplica ninguno. Fechas o periodicidad no cambian mientras existan
lineas, y planes aprobados o cerrados son inmutables.

Las reglas deterministas viven en `apps.plantas_piloto.domain.planificacion`,
sin importar Django. La persistencia queda deliberadamente en `webcitt` hasta
M10 para evitar mover tablas o permisos sin reversa. El manifiesto de Plantas
Piloto sube a 1.1.0 y declara `planificacion_demanda`. El panel y el documento
imprimible muestran demanda, plan agregado y Plan Maestro junto a capacidad,
materiales y pedidos. Catalogos ES/EN compilados con 8.879 mensajes.

Validacion directa: 30 pruebas correctas. Aceptacion enfocada de procesos,
produccion, reservas por proceso, maquila, planificacion, calidad, almacen,
aula, ejercicios, documentos y seguridad: 231 correctas, una omitida, 256,010
s. Suite integral: 1.402 correctas, una omitida, 656,102 s. Django check,
migraciones en seco, Ruff, compilacion y diff correctos. Contratos de senales:
19/19/19, cero hallazgos. Codigo `214528b4`.

Siguiente bloque: completitud administrable de Plantas Piloto. Debe mostrar el
estado real por planta, pestana, familia y ficha e impedir que los cargadores
sobrescriban decisiones editoriales. Despues sigue el repositorio trazable y
una sola aceptacion funcional antes de pasar a Centros Experimentales.

## 186. Completitud administrable de Plantas Piloto

El segundo bloque funcional de Plantas Piloto queda completo. El tablero
interno conserva las 33 secciones y ahora resume avance por planta, pestana,
familia y ficha con cuatro estados estables: aprobado, parcial, pendiente y
bloqueado. Una ficha solo queda aprobada cuando esta completa, publicada y
validada por la institucion; los vacios de equipos, procesos, PCC, productos y
especificaciones permanecen visibles y bloquean las secciones que consumen el
dato.

`FichaContenido` registra estado y observacion de validacion, responsable y
fecha, ademas de autor y fecha de la decision editorial manual. El administrador
ofrece acciones para enviar, validar o bloquear y limita fichas y familias a las
unidades gestionables. Senales y cargadores siguen actualizando identidad y
relaciones, pero una recarga conserva estado, visibilidad, version, validacion y
decision manual; desactivar el origen continua forzando el archivo.

Las reglas puras viven en `apps.plantas_piloto.domain.completitud`; el
manifiesto 1.2.0 declara `gobierno_completitud`. Migracion 0203. Catalogos ES/EN:
8.888 mensajes por idioma. Validacion enfocada: 140 pruebas correctas. Suite
integral: 1.407 correctas, una omitida, 518,148 s. Django check, migraciones en
seco, Ruff, compilacion y diff correctos. Senales 19/19/19 sin hallazgos.

Siguiente bloque: repositorio trazable. Debe cerrar fuente, licencia, version,
responsable, vigencia, evidencia, permisos y descarga de los artefactos
externos. Despues queda una unica aceptacion funcional de las cinco Plantas
Piloto antes de iniciar Centros Experimentales.

## 187. Repositorio trazable de Plantas Piloto

El tercer bloque funcional de Plantas Piloto queda completo. Cada artefacto
externo publicado exige fuente concreta, licencia, version, responsable y fecha
de validacion, inicio de vigencia y evidencia. La fecha final es opcional, pero
una vigencia futura o vencida impide publicarlo. Un cambio en receta, operacion
o equipo lo marca para revision y lo retira del repositorio, la ficha del
proceso y la exportacion publica.

Importar un resultado ya no elimina la alerta de desactualizacion. Un gestor de
la unidad debe confirmar expresamente la sincronizacion; esa accion registra
responsable y fecha. Los resultados importados solo aparecen a gestores. Los
administradores de adjuntos, artefactos y resultados limitan consultas y
selectores al alcance por unidad; archivos y evidencia siguen usando la entrega
controlada existente.

Las reglas puras de vigencia viven en
`apps.plantas_piloto.domain.repositorio`; el manifiesto 1.3.0 declara
`repositorio_trazable`. Migracion 0204. Catalogos ES/EN: 8.896 mensajes por
idioma. Cobertura conjunta de Plantas: 169 pruebas correctas. Suite integral:
1.412 correctas, una omitida, 506,677 s. Django check, migraciones en seco,
Ruff, catalogos y diff correctos.

Solo falta la aceptacion funcional unica de las cinco Plantas Piloto. No quedan
bloques de implementacion arquitectonica antes de esa puerta. Al cerrarla se
congela la vertical salvo defectos criticos y se inicia Centros Experimentales.

## 188. Aceptacion funcional de Plantas Piloto

Las cinco plantas quedan aceptadas: Lacteos, Carnicos, Hortofruticola,
Almidones y derivados, y Panificacion. La puerta enfocada cubrio 275 pruebas de
catalogo, procesos, reserva por proceso, produccion, calidad, almacen,
planificacion, documentos, completitud, repositorio y seguridad; termino sin
fallos y con una omision en 223,249 s. La suite integral finalizo con 1.412
pruebas correctas, una omitida, en 513,720 s.

La validacion visual uso una base de prueba aislada y emulacion real del
viewport. Recorrio las cinco plantas a 360 px en espanol y 1366 px en ingles,
ademas de Lacteos a 768 px en ambos idiomas. Las doce combinaciones conservaron
el ancho del documento igual al viewport. Se corrigio la navegacion de modulos
con dos columnas fluidas por debajo de 768 px. El visor
institucional dejo de depender de un logotipo remoto y ahora usa el recurso
local con dimensiones responsivas.

Django check, migraciones en seco y Ruff estan limpios. Senales conserva 19
contratos, 19 decoradores y 19 conexiones propias, sin hallazgos. La base activa
no se modifico; la base temporal se vacio despues de la inspeccion visual antes
de ejecutar las pruebas.

Plantas Piloto queda congelada salvo contenido institucional o correcciones
criticas. Permanecen M01 para recuperacion institucional y M10-M11 para
aislamiento fisico; no bloquean las funciones. La siguiente vertical es Centros
Experimentales, empezando por especificar ensayo o campana, ciclos, parcelas o
areas, activos biologicos, tratamientos, protocolos y permisos propios.
## 72. Frontera estructural de Centros Experimentales

Centros Experimentales conserva sus rutas públicas y la operación existente,
pero su presentación delega ahora en un adaptador propio de infraestructura.
Ese archivo es el único puente temporal hacia `apps.integraciones`; no contiene
reglas de campo. El manifiesto 1.1.0 declara `identidad_unidad_v1` y mantiene
solo las capacidades reales de catálogo y detalle.

`apps/centros_experimentales/README.md` fija la dirección de dependencias, la
propiedad futura y el límite del aislamiento actual. No se generaron capas
vacías ni funciones: `domain` y `application` se crearán al implementar reglas
y casos de uso institucionalmente aprobados. Validación enfocada inicial: 26
pruebas correctas.

## 73. App y plantilla propias de Centros Experimentales

`apps.centros_experimentales` está instalada como app Django y es propietaria
de la experiencia pública que antes residía bajo las plantillas de `webcitt`.
El include conserva el mismo contenido y contexto. El manifiesto sube a 1.2.0.

El inventario del README deja `PerfilCentroExperimental`, su inline y los
recursos compartidos en el legado hasta M10 o hasta demostrar propiedad
exclusiva. No hay modelos, migraciones ni funciones nuevas en este bloque.
Validación proporcional: 51 pruebas correctas; Django, migraciones, Ruff y
compilación limpios.

## 74. Frontera estructural de Observatorios

Observatorios ya es una app Django instalada, posee su plantilla pública y
encapsula el acceso heredado en infraestructura. Su manifiesto 1.1.0 declara
`identidad_unidad_v1` y conserva solamente catálogo y detalle.

El perfil y administración existentes permanecen en `webcitt`; no se añadieron
fuentes, conjuntos, indicadores, solicitudes, modelos ni migraciones. El README
documenta el inventario y la estructura futura.

Validación proporcional conjunta: 55 pruebas correctas; Django, migraciones,
Ruff y compilación limpios.

## 75. Frontera estructural de Centros I+D

Centros I+D está instalado como app Django y es propietario de su URL, vista y
portada pública. El manifiesto 1.1.0 conserva solo `portada_publica`, con `core`
como única dependencia. No usa `Unidad` ni las verticales operativas.

El README registra la estructura futura y lo que todavía no existe. Este
bloque no agrega modelos, migraciones, administración o funciones de
investigación.

Validación proporcional conjunta: 71 pruebas correctas; Django, migraciones,
Ruff y compilación limpios.

## 76. Punto de pausa y traspaso

Se añadió `TRASPASO-CLAUDE.md` con el estado operativo, mensaje listo para el
nuevo chat, archivos prioritarios, comandos, límites y siguiente bloque. La
rama estaba limpia en `69142d2b` antes de crear el documento. Sigue pendiente
uniformar estructuralmente Laboratorios y Plantas Piloto; las funciones nuevas
continúan fuera del alcance inmediato.

## 77. App y plantilla propias de Laboratorios

`apps.laboratorios` está instalada como app Django y es propietaria de la
experiencia pública que antes residía bajo las plantillas de `webcitt`. El
include conserva el mismo contenido y contexto, y el acceso al legado queda
encapsulado en `infrastructure`. El manifiesto sube a 1.1.0 con `app_django` y
`identidad_unidad_v1`.

La aceptación funcional de Laboratorios no se reabre: `PerfilLaboratorio`,
reservas, equipos, prácticas, documentos, servicios, inline administrativo y
recursos compartidos permanecen en el legado hasta M10. No hay modelos,
migraciones ni funciones nuevas en este bloque.

Validación proporcional: 63 pruebas correctas; Django, migraciones, Ruff y
compilación limpios.

## 78. App y plantilla propias de Plantas Piloto

`apps.plantas_piloto` está instalada como app Django y es propietaria de la
experiencia pública que antes residía bajo las plantillas de `webcitt`. El
include conserva el mismo contenido y contexto, y el acceso al legado queda
encapsulado en `infrastructure`. El manifiesto sube a 1.4.0 con `app_django` y
`identidad_unidad_v1`, sin perder ninguna de sus cinco capacidades.

Las reglas propias de `domain` no se modificaron. `PerfilPlantaPiloto`,
procesos, recetas, órdenes, lotes, calidad, inventario, Plan Maestro,
administración y recursos compartidos permanecen en el legado hasta M10. No hay
modelos, migraciones ni funciones nuevas en este bloque.

La carpeta `webcitt/templates/portal/pages/unidades/experiencias` queda vacía y
se retira; el árbol documentado en `docs/arquitectura.md` lo refleja.

Validación proporcional: 77 pruebas correctas; Django, migraciones y Ruff
limpios.

## 79. Uniformidad estructural de las cinco verticales

Laboratorios, Plantas Piloto, Centros Experimentales, Observatorios y Centros
I+D comparten la misma frontera: app Django instalada, plantilla pública
propia, puente heredado aislado donde existe y manifiesto que declara la app.
Las carpetas vacías del legado —experiencias de unidades y portada de Centros
I+D— se retiraron, y el árbol de `docs/arquitectura.md` lo refleja.

La suite integral descubrió que `test_portal` seguía exigiendo la plantilla
anterior de la portada de Centros I+D, trasladada en el bloque 192 sin
actualizar esa aserción. Se corrigió en este bloque.

Sin traslados de datos, permisos o administración; sin funciones nuevas. La
prueba de manifiestos exige `app_django` a las cuatro verticales de unidad sin
excepciones.

Validación integral única: 1.433 pruebas correctas y una omitida en 804,103
segundos; Django, migraciones, auditoría de módulos, Ruff y compilación
limpios.

## 80. Auditoria de categorias administrables

M02.3 abre con la auditoria que el propio hito exige. `Categoria` y
`TipoLaboratorio` tienen la misma forma minima, no estan acotados a su modulo,
se filtran por nombre en el catalogo publico y no admiten orden, ocultacion ni
archivado; eliminarlos pierde la clasificacion historica.

Se corrigio un defecto real: el limite de seis categorias por unidad no se
aplicaba desde el admin porque `Unidad.clean` solo lee la relacion ya guardada.
Ahora lo aplica `UnidadAdminForm` sobre la seleccion enviada, con dos pruebas de
regresion y sin migracion.

El resto del hito queda bloqueado por cinco decisiones institucionales:
vocabulario, alcance, unificacion de los dos catalogos, limites configurables y
semantica del archivado.

Validacion proporcional: 62 pruebas correctas; Django, migraciones y Ruff
limpios.

## 81. Higiene del repositorio

Nombre anterior retirado de docstrings, imagenes de pilares como estaticos,
`media/` sin rastrear, PDF huerfano eliminado, documentos de traspaso
consolidados en `TRASPASO.md` y `docs/historial/`, auditoria actualizada y
rutas reconciliadas. Sin esquema ni funciones nuevas; 45 pruebas correctas.

## 82. Tipologias administrables

Catalogo institucional de tipologias de unidad con base operativa, orden,
icono, nombres ES/EN y estado; crear y desactivar desde el admin, con
aplicacion en el servidor y conservacion de datos. Ruta generica para
tipologias sin app propia; las implementadas conservan las suyas. Proveedor
que superpone filas y falla cerrado. Dos migraciones, respaldo previo, 145
pruebas correctas.

## 83. Clasificaciones administrables

Subareas y modos de uso con codigo estable, orden, archivado, alcance por
tipologia y eliminacion protegida; filtros publicos por codigo con
compatibilidad por nombre; formulario de unidad acotado. Migracion 0206
aplicada con respaldo previo. M02.3 cerrado. 131 pruebas correctas.

## 84. Cierre integral

1.449 pruebas; tres huellas del auditor de senales revisadas y actualizadas
tras el cambio en modelos; auditor en verde. M02.3 cerrado y documentado.

## 85. Revision integral del repositorio

Sin huerfanos ni duplicados reales; nombre viejo retirado de pyproject;
dependencias reproducibles con hashes y sin herramientas de desarrollo en
produccion; imagen sin root; permisos de adjuntos; registro explicito;
verificacion automatica de restauracion en el ciclo de respaldo; pip-audit y
check --deploy limpios.

## 86. Raiz limpia con var/

Directorios de ejecucion agrupados bajo `var/` e ignorados; restos locales y
servidor obsoleto retirados; `static/` raiz sin uso eliminado; Docker,
ignorados, pruebas y documentos alineados. La raiz contiene solo codigo,
configuracion, documentacion y scripts.

## 87. Colores institucionales y cabecera

La paleta derivada ya no sustituye el acento por blanco sobre fondos oscuros:
lo aclara hasta ser legible. Se retiraron reglas que forzaban blanco en cejas y
acentos, y se corrigieron usos de la tinta oscura del acento sobre fondos
oscuros. Cabecera con separaciones originales; sesion y acceso en la barra
superior con usuario y nombre completo. 129 y 71 pruebas correctas.
