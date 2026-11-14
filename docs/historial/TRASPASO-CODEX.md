# Traspaso para continuar en otro chat

Pega este archivo (o su contenido) como primer mensaje del chat nuevo. Está
escrito para que quien lo lea pueda seguir trabajando sin haber visto nada de
las sesiones anteriores.

---

## 1. Qué es esto y dónde está

Sistema de Laboratorios y Centros I+D (compatibilidad técnica **CITT**):
Django 5.2 LTS, PostgreSQL, repositorio en
`C:\Users\PC2\Documents\GitHub\CITT`.

| Cosa | Valor |
| --- | --- |
| Rama de trabajo | `reestructura-modular`; la base estable anterior permanece en `integracion-version2-funciones` (**nunca** hacer merge a `main`/`version2` sin aprobación explícita del usuario) |
| Remoto | `origin` → `github.com/COMPUMAX-EC/CITT` |
| Intérprete | `.venv/Scripts/python.exe` (no hay `python` global útil) |
| Base de desarrollo | `citt_db`; la de pruebas es `test_citt_db` |
| Entorno local | `config.settings`; revisar flags vigentes, no asumir DEBUG=False. Produccion exige `config.settings_production` y sus controles |
| Idioma y zona | Selector ES/EN por navegador; zona institucional por INSTITUTION_TIME_ZONE; defaults es-ec y America/Guayaquil (floatformat localiza: ver trampas) |
| Marcos | `X_FRAME_OPTIONS = 'DENY'`; una página que se incrusta en el visor necesita `@xframe_options_sameorigin` |
| Historial técnico | `CODEX_CONTEXT.md`, secciones numeradas; la continuación actual es la **185** |

Publicación resuelta: el usuario autorizó explícitamente COMPUMAX-EC/CITT,
rama `reestructura-modular`; los bloques 150–155 se publicaron hasta `6ce91d0f`.
El bloque 156 ya publicado corresponde a `387f0373`; el 157, a `db301cd7`, y el 158, a `8361f4d5`.
El 159 corresponde a `b803cb9d`, el 160 a `7be47058` y el 161 a `f1533b13`;
el bloque 162 corresponde a `a179a499`.
El bloque 163 corresponde a `ef6ea863`.
El bloque 164 corresponde a `746c4b16`.
El bloque 165 corresponde a `dafd07ad`.
El bloque 166 corresponde a `a6dd8152`.
El bloque 167 corresponde a `2b037a96`.
El bloque 168 corresponde a `4b4fcd3d` y el 169 a `b536bbc1`.
El bloque 170 corresponde a `9b4659c0`, el 171 a `15e2a586` y el 172 a
`cda6ef02`. El bloque 173 corresponde a `6f3fcc47`; la auditoría posterior al
bloque está en `docs/auditoria-arquitectura-modular.md`. El bloque 174
corresponde a `5fff7d60` y su documentación a `3a49570b`. El código del bloque
175 corresponde a `1874d972`; su documentación se publica en el commit
inmediatamente posterior. Comprobar siempre
`git log -1` y `origin/reestructura-modular` antes de continuar.
Los bloques 176-183 y su documentación están publicados hasta `7a0f6e57`; el
código funcional del interruptor integral de reservas es `7edae539`. El bloque
184 y la aceptación definitiva de Laboratorios se documentan en la sección 67
de este archivo y la sección 184 de `CODEX_CONTEXT.md`.
El primer bloque funcional de Plantas Piloto corresponde a `214528b4`; se
documenta en la sección 68 de este archivo y la 185 de `CODEX_CONTEXT.md`.
Las notas históricas de autorización pendiente quedaron superadas por esa
confirmación. Mantener publicaciones en ese destino conforme a su instrucción.

Comandos que se usan todo el tiempo:

```bash
.venv/Scripts/python.exe manage.py test --keepdb --noinput    # suite completa (1402 pruebas + 1 omitida)
.venv/Scripts/python.exe -m ruff check apps/ config/ webcitt/
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py collectstatic --noinput    # tras tocar CSS/JS
node --check <archivo.js>                                      # tras tocar JS
```

---

## 2. Reglas de trabajo del usuario (no negociables)

1. **Conservar la interfaz institucional** ya trabajada. No rediseñar identidad
   ni UI global.
2. **Nada de código muerto.** Si algo deja de tener quien lo llame, se borra en
   el mismo cambio (plantillas, CSS, funciones, claves de contexto).
3. **Las superficies deben coincidir:** Reservas, Gestionar laboratorio, Mis
   reservas y el admin de Django muestran los mismos datos sin duplicar ni
   distorsionar. La guía FT04 debe verse igual en el asistente, en HTML y en PDF.
4. **Por bloque de trabajo:** suite completa en verde → documentar en
   `CODEX_CONTEXT.md` con sección numerada → commit claro **en español y sin
   tildes** → push a la rama de trabajo activa (`reestructura-modular`).
5. **Atribución obligatoria al final de cada mensaje de commit:**
   `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
   (el otro chat debe poner su propia atribución si su herramienta lo exige,
   pero el formato del cuerpo se mantiene: qué estaba mal, qué se hizo, por qué,
   y la línea `Suite completa: N pruebas, OK.`).
6. **Presentar el bloque terminado al final**, sin preguntar a mitad de camino.
   Las decisiones que son suyas se plantean al cerrar, no se resuelven solo.
7. **Alcance actual:** Laboratorios está aceptado. Plantas piloto ya cerró la
   planificación completa; continuar con completitud administrable y repositorio trazable;
   después ejecutar una sola aceptación funcional. M01 institucional, M02.3 y
   M10-M13 siguen registrados y no autorizan a mover tablas ni afirmar
   aislamiento físico o recuperación institucional.
8. **Nunca correr dos invocaciones de pruebas de Django a la vez:** comparten el
   nombre de base `test_citt_db` y la segunda mata a la primera.

---

## 3. Antecedentes y continuación actual

```
e350dcd feat: cada pagina del aula se ve y se baja como documento
796dafd feat: el balance de materia de toda la corrida, en un bloque
6a10a35 feat: el aula mueve cada dato de la receta y guarda lo que simula
d8bdc55 fix: el listado de reservas se descarga como documento, no como foto
0fa2f6d feat: cada pestana se presenta sola y cada proceso explica su teoria
```

La sesión actual partió de `78a38e7` (traspaso), con árbol limpio y
**730 pruebas OK (1 omitida)** verificadas de nuevo. La sección 96 añadió
`externa_al_flujo` en el commit `c14a010`; la sección 97 incorporó los PDF
propios de los diez formatos oficiales y las secciones 98–99 iniciaron la nueva
arquitectura de Plantas Piloto. La rama `reestructura-modular` conserva ese
trabajo y añade la base de seguridad y continuidad descrita en la sección 126.
Suite actual: **1345 pruebas OK (1 omitida), 794.142 s**.
Consultar `git log -1` para el último commit de esta continuación.

Auditoría vigente del 19 de septiembre de 2026: el árbol está estable para
continuar, con M00 implementado; M02.1, M02.2, M02.4 y M09 parciales; M01
probado localmente pero pendiente de cierre institucional; y M03-M08/M10-M13
pendientes en su alcance final. Todas las escrituras de
`gestion_reserva_accion_view` ya delegan en servicios transaccionales. El
siguiente bloque revisa primitivas, tareas, admin y cargadores, además de las
dependencias internas que aún importan resolución de período o constantes desde
`reservas.views`. Persisten proceso, base, URLConf y credenciales compartidos;
no declarar aislamiento M11 ni producción recuperable.

### 3.1 Mapa de los módulos nuevos

Todos en `webcitt/domains/unidades/`:

| Módulo | Qué hace |
| --- | --- |
| `portadas.py` | La portada de cada pestaña de la ficha pública: qué es la sección, qué contiene (sale de las carpetas reales), de dónde salen los datos y cómo se lee. También cuelga «Lo que produce» de la portada de producción. |
| `documentacion.py` | La teoría de un proceso: glosario de 18 operaciones unitarias, `clasificar_etapa`, `entradas_y_salidas`, `flujo_por_etapa`, **`balance_general`**, `variables_del_proceso`, `datos_que_usa`. |
| `escenarios.py` | Las variables que el aula mueve sin tocar la receta: `variables_del_escenario`, `leer_escenario`, `escenario_del_formulario`, `aplicar_escenario`, `cambios_del_escenario`, `valores_del_formulario`. |
| `motores.py` | Los cálculos puros, fuera de las vistas: `balance_de_energia`, `balance_de_linea`, `requerimiento_de_materiales`, `etapas_termicas`, `masa_de`, y los ayudantes `_num/_decimal/_texto`. |
| `simulaciones.py` | Guardar / editar / borrar / descargar una simulación (`SimulacionGuardada`), «Mis simulaciones» y el documento de una simulación guardada. |
| `documentos.py` | La forma común de un documento descargable: `documento()`, `tabla()`, `formato_pedido()`, `respuesta_pdf()`, `enlaces_de_documento()`. |
| `documentos_gestion.py` | Conserva la vista, sus permisos y filtros, y sirve el PDF propio de los diez formatos oficiales. |
| `maquetas_pdf.py` | Compone con ReportLab la estructura y los textos de las mismas plantillas HTML: membrete, bandas, tablas, casillas, barras y firmas. |
| `documentos_aula.py` | Un constructor por página del aula (once), que recibe el contexto ya armado por la vista y lo traduce al presentador institucional. |
| `reservas_publicas.py` | Catálogo público de servicios y tarifas y agenda anónima de 14 días; agrupa la oferta de la planta y oculta identidades y motivos de reserva. |

El presentador institucional es **`render_unit_report_pdf(reporte)`** en
`webcitt/domains/unidades/gestion_reportes.py`. Consume un diccionario con
`scope_label`, `category_label`, `filter_summary`, `dataset.headers/rows/cards/tablas`
y dibuja cabecera con logo, banda de criterios, tarjetas y tablas. Se usa para
reportes y documentos del aula. **Por decisión del usuario, los diez formatos
oficiales de gestión usan su propia maqueta** (`render_maqueta_pdf`), manteniendo
los mismos enlaces de vista previa y descarga. Ninguno depende de `window.print()`.

### 3.2 Cómo se descarga algo (patrón establecido)

La página es su propia vista previa. En la dirección:

- `?formato=pdf` → el PDF `inline`, para revisarlo en el visor del navegador.
- `?formato=pdf&descargar=1` → el mismo PDF como `attachment`.

Los enlaces conservan los filtros que tenga puesta la página, así que lo
revisado es exactamente lo descargado. En la barra: «Ver el documento» +
«Descargar PDF».

### 3.3 Otras piezas que conviene conocer

- **Migraciones vigentes:** `webcitt.0201_verificacion_institucional`,
  `configuracion_institucional.0007_habilitacion_capacidades` y `portal.0001_initial`.
  Comprobar su aplicación con `showmigrations`; no usar el corte antiguo 0193
  como referencia del esquema actual.
- **Dentro del visor** (`<html class="esta-incrustado">`, lo marca
  `portal/components/marco_incrustado.html` cuando la página va en un iframe):
  se esconden el logo, el `h1`, el nombre de la unidad y los enlaces de
  navegación marcados con la clase **`es-navegacion`**. Al imprimir vuelven.
- **`webcitt/tests/`**: pruebas nuevas de la sesión —
  `test_portadas_modulo` (6), `test_documentacion_proceso` (19),
  `test_reporte_listado_reservas` (8), `test_simulaciones_guardadas` (31),
  `test_documentos_del_aula` (11), `test_gobierno_recursos` (8).

---

## 4. Trampas que ya costaron tiempo (no repetirlas)

1. **CRLF.** `webcitt/models/reservas.py`, `webcitt/models/__init__.py` y
   `webcitt/admin/reservas.py` usan CRLF; el resto LF. Un parche que busca `\n`
   no encuentra nada en esos tres. Leer con `read_bytes()`, normalizar a `\n`,
   aplicar y restaurar el final detectado.
2. **Parches grandes = scripts Python transaccionales.** Los heredocs de Bash con
   comillas anidadas fallan una y otra vez (la herramienta manda CRLF). Escribir
   el script con la herramienta de escritura de archivos y ejecutarlo. El script
   debe guardar cada archivo en un diccionario en memoria y **escribir solo los
   que de verdad cambiaron** (un barrido que lee muchos archivos y los reescribe
   normaliza finales de línea y ensucia el diff).
3. **`floatformat` está localizado** (`es-ec`): `{{ 1.5|floatformat:"-3" }}`
   rinde «1,500». En texto visible está bien; en `data-field-*`, en `value` de un
   `<input type="number">` o en cualquier cosa que lea `parseFloat`, usar el
   sufijo `u` (`floatformat:'-3u'`). Un `Decimal('364.340')` impreso con
   `floatformat` se lee como «364 mil».
4. **Códigos únicos entre unidades.** El cargador busca equipos, insumos, áreas,
   software, productos, recetas y servicios **por código sin filtrar por unidad**,
   y `CategoriaEquipo.nombre` es único en toda la plataforma. Prefijar todo con la
   sigla de la unidad. `test_plantas_piloto.py::LasDefinicionesNoSePisanTests` lo
   revisa sin tocar la base.
5. **Perfil vigente.** `PerfilInstitucionalVigenteMiddleware` exige perfil
   completo en toda ruta `/reservas/`; una cuenta de prueba creada a mano recibe
   403 sin razón aparente hasta que se le pone `tipo_usuario` e `institucion`.
6. **Nombres de campo que no son los obvios** (comprobar siempre antes de citar):
   `MovimientoProducto.motivo` (no `observaciones`);
   `MovimientoFinancieroUnidad.fecha_movimiento/monto/estado`;
   `resumen_proceso()['duracion_texto']` (no `duracion_total`);
   `cursograma_analitico()['filas'][i]['tiempo_texto']` (no `minutos`);
   `ParametroCalidad.unidad_medida/minimo/maximo` (no `unidad/valor_minimo/valor_maximo`);
   `ResponsableUnidad.permisos_operativos` es un JSONField, no columnas.
7. **Plantillas en caché** con `DEBUG=False`: tras editar una, tocar un `.py`
   para que el servidor recargue.
8. **Verificar construyendo, no leyendo.** Antes de dar por bueno un documento
   nuevo, construirlo para todas las unidades cargadas con un script contra la
   base de desarrollo. Así aparecieron dos errores de nombres de campo que
   ninguna lectura del código había detectado.

### Navegador simulado (para reproducir problemas de interfaz)

No hay Playwright ni Selenium. Hay Node y un arnés con **jsdom** en el
scratchpad de la sesión (`jsdom-harness/`, `npm install jsdom@24`) que carga las
páginas reales desde `http://127.0.0.1:8000` con una cookie de sesión y ejecuta
los scripts de verdad. **Ante cualquier reporte de «no responde / se congela /
no aparece», reproducir primero con el arnés antes de tocar código.**

Para ver el diseño real (jsdom no calcula estilos): `curl` con la cookie →
reemplazar `"/static/` por `file:///…/static_deployed/` → `chrome.exe
--headless=new --screenshot`. Los recortes necesitan el envoltorio con la clase
correcta o los colores con `var()` no se resuelven y parece un fallo que no existe
(`.reservation-wizard-enhanced` para el asistente, `.unit-console` para el panel,
`.unit-detail` para la ficha pública).

---

## 5. Lo que queda pendiente

### 5.1 Resuelto: PDF propios que conservan la maqueta oficial

El usuario eligió rescatar la maqueta oficial. La lista original decía nueve,
pero enumeraba **diez** formatos; todos ofrecen ahora «Ver el documento» y
«Descargar PDF», desde la misma vista y con los mismos permisos y filtros:

```
gestion/acta_entrega.html        gestion/plan_maestro.html
gestion/control_calidad.html     gestion/reporte_institucional.html
gestion/maquila.html             gestion/resultados_ejercicio.html
gestion/plan_haccp.html          gestion/trazabilidad_lote.html
visitas/asistencia.html          visitas/oferta.html
```

No volver a preguntar esta decisión. Detalles y validación en §97 del historial.
Al cambiar su estructura HTML, comprobar también su composición en PDF.

### 5.2 Marca implementada; quedan datos de recetas por revisar

El usuario eligió añadir `SalidaReceta.externa_al_flujo`, no modificar cantidades
ni rendimientos. Migración 0186 aplicada: 17 salidas conocidas de agua de lavado
y proceso marcadas; panel, admin, cargadores y motor usan el mismo dato.

Se eliminó la inferencia que ocultaba toda salida de una etapa al 100 %.
De las 20 recetas activas, **11 cuadran y 9 muestran excesos internos reales**:

| Receta | Descuadre restante |
| --- | --- |
| Hortofrutícola: mermelada / pulpa / uvilla | 3.358 / 4.929 / 0.08 kg |
| Almidones: almidón / pregel / glucosa | 16.175 / 35.112 / 73.09 kg, en tamizado |
| Panificación: molde / masa madre / papa | 1.5 / 1.2 / 1.2 kg |

Panificación estaba oculta por la inferencia anterior. No marcar bagazo, afrecho
o merma de harina como externos para hacer cuadrar cifras. La revisión de estos
datos permanece pendiente de indicación del usuario; la marca ya está terminada.
Ver §96 del historial para el porqué y las pruebas.

### 5.3 Decisiones viejas, todavía abiertas

Excepción del Decanato · visibilidad de nombres en la agenda · registro abierto ·
limpieza de datos de prueba · Observatorio de Turismo · fotos reales de equipos ·
antelación de guía configurable · aforo solo en unidades controladas.

También, de las cuatro plantas cargadas, panificación tiene productos de
catálogo sin receta. La asesoría en formulación de Cárnicos se clasifica como
desarrollo de producto; no se inventó un servicio de análisis para esa planta.

### 5.4 Nueva arquitectura de Plantas Piloto: pasos 1 a 5 terminados

La especificación entregada en `C:\Users\PC2\Downloads\Plantas piloto` se
contrastó completa con el repositorio. `docs/arquitectura-plantas-piloto.md`
consolida la precedencia de fuentes, las seis pestañas, las 33 secciones, lo que
se reutiliza y la secuencia de siete pasos. Los documentos 09 y 10 prevalecen
sobre propuestas anteriores de los libros; sus valores físicos siguen siendo
referenciales hasta validación de la UPEC.

El paso 1 quedó implementado en la migración 0187: 31 familias maestras para las
cinco plantas; familia en producto, proceso, etapa/PCC, plan de calidad, guía y
simulación guardada; `FichaContenido` para estado editorial, versión,
visibilidad, completitud y relaciones; códigos físicos `EQP` en las cinco
plantas; alias y redirección HTTP 301 desde los 58 códigos `UNIT` históricos.
Los 42 códigos `UNIT` de laboratorios permanecen intactos. Calidad se agrupa y
filtra por familia y las tablas públicas dicen «Código».

La base de desarrollo quedó migrada y la carga de las ocho unidades fue
idempotente: cinco plantas, 31 familias, 58 equipos de planta con alias, cero
productos o procesos de planta sin familia y 229 fichas editoriales.

El paso 2 quedó implementado en la migración 0188 y en el catálogo compartido,
con una rama visual exclusiva para `plantas_piloto`: modo de operación y estado
de catálogo controlados, responsable público obligatorio en el maestro, imagen
de portada con respaldo genérico, cifras calculadas desde el núcleo y filtros
por familia, tecnología, servicio y disponibilidad. Los filtros institucionales
permanecen plegados. La tarjeta ya no muestra el contador de visitas ni los
textos «Por asignar» o «Por registrar». Lácteos muestra 11 productos públicos,
8 procesos activos y 17 equipos físicos. La captura de las cinco tarjetas está
en `tmp/catalogo-plantas-paso2.png`.

La tecnología se registra en `EquiposServicios.familia_tecnologica`; la
disponibilidad y el modo viven en `Unidad`. Las maquilas y la asesoría de
Cárnicos usan los nuevos tipos de `FablabService`, y el asistente de reservas
conoce su vocabulario. No se alteraron los datos ni el catálogo de laboratorios.
El paso 3 quedó implementado en la migración 0189 y en la ficha pública. Las
tres primeras pestañas usan secciones numeradas y mantienen visibles las que
aún no tienen contenido con contador cero y estado pendiente; el balance de materia está en 2.4 y el balance de línea en 3.4 como
secciones de primer nivel. Información general integra presentación, cifras y
datos operativos; `Unidad.video_unidad` permite sustituir el video institucional
sin perderlo como respaldo. El árbol derecho conserva un solo encabezado,
agrupa las guías aprobadas por familia y muestra el estado editorial solo a
gestores. La ruta antigua de simuladores redirige a 2.4. Laboratorios conserva
sus acordeones. Los pasos 1 a 3 se auditaron de nuevo en las secciones 103 a
107 del historial.

La sección 100 corrigió la presentación dañada que podía ver un navegador con
la hoja de estilos anterior en caché. `catalogo_unidades.html` publica ahora
`catalogo.css?v=20260913-plantas-v1`, por lo que el HTML del paso 2 siempre se
combina con la cuadrícula que distribuye sus filtros a todo el ancho. La captura
verificada está en `tmp/catalogo-plantas-cache-corregida.png`; no hubo cambios
en modelos, datos, laboratorios ni reservas.

La sección 101 aplica únicamente a «Conocer unidad» de Plantas Piloto el
degradado solicitado `linear-gradient(100deg, #17a2b8, #01697a)` y publica el
CSS como `20260913-plantas-v2`. Los distintivos dorados y los botones de las
demás clases de unidad conservan su tratamiento anterior. La evidencia visual
está en `tmp/catalogo-plantas-botones-azules.png`.

La sección 102 amplió esa decisión a toda la identidad de las tarjetas de
Plantas Piloto. Sus variables son `#17a2b8`, `#01697a` y fondo suave `#e8f7fa`;
por ello borde, rótulo, emblema, decoración, datos, familias, conteos, modo y
botón ya no usan café. La versión pública es `20260913-plantas-v3` y la captura
completa está en `tmp/catalogo-plantas-identidad-azul.png`.

Las secciones 108 y 109 completaron y auditaron el paso 4. Producción y lotes
separa el catálogo estable del detalle operativo: 4.1 contiene fichas propias
para todos los productos, 4.4 conserva el requerimiento de materiales y 4.5
publica solo el agregado de actividad. 2.1 contiene exclusivamente procesos;
balance, capacidad y documentación se alcanzan desde su barra sin repetir las
recetas. El detalle de corridas y lotes permanece interno.

La sección 110 corrigió la omisión visual que todavía ocultaba parte del mapa.
Información general muestra ahora 1.1–1.5; Procesos, Equipos y Producción muestran
en orden 2.1–2.6, 3.1–3.4 y 4.1–4.6. Las secciones relacionadas remiten a la
ficha única del proceso o producto y las que todavía no tienen datos aprobados
muestran un estado pendiente dentro de su acordeón. Las portadas centrales
siguen enumerando solo contenido real y Laboratorios conserva su comportamiento.

La sección 111 completa el gobierno editorial de los pasos 1 a 4. Las carpetas
y subcarpetas creadas desde el administrador se integran en una sección
canónica, con orden, estado y visibilidad heredable; sus archivos y ZIP se
sirven por rutas controladas. `FichaContenido` permite ocultar, restringir o
archivar también productos y procesos sin que una nueva carga institucional
deshaga la decisión. Familias, productos, recetas, asignaturas y temas tienen
administradores relacionados y el mapa académico del plan de Alimentos quedó
documentado en `docs/plan-estudios-alimentos-y-plantas.md`. La migración 0191
conserva los recursos anteriores y no modifica el árbol de los laboratorios.

La sección 112 completa el paso 5. La sexta pestaña de cada planta contiene las
secciones 6.1–6.7 con acordeones, integra el catálogo de servicios y tarifas con
el mismo asistente de reservas, y publica una agenda anónima de 14 días sin
identidades ni motivos. Los requisitos de acceso, las guías, el reglamento y
las visitas reutilizan los flujos existentes; `Gestionar laboratorio` permanece
solo en la cabecera. Las guías publicadas pueden usarse, clonarse con trazabilidad
o servir de referencia para crear una nueva; una guía completa habilita la
aprobación y debe enviarse antes de la ejecución. Las migraciones 0192 y 0193
incorporan la unidad de cobro, el responsable del servicio y el origen de una
guía clonada. Laboratorios mantiene su navegación compartida anterior.

---

## 6. Cómo seguir

1. Leer `CODEX_CONTEXT.md` de la sección **91** a la **112** para conocer los
   antecedentes, las decisiones aceptadas y la validación de los pasos 1 a 5.
2. Confirmar la rama `reestructura-modular`, el estado del árbol y
   `git log -1`; la última suite completa tiene **1094 pruebas OK (1 omitida)**.
3. Continuar desde las secciones 129-136 y la ruta M00-M13 revisada en
   `docs/ruta-ejecucion-arquitectura-modular.md`. Las entradas publicas y contratos ya estan
   bajo `apps/`; 104 rutas operativas permanecen en `webcitt/routing/heredadas.py`.
   M02.1 ya separa identidad, catalogo academico, niveles, calendario y configuracion regional; sigue abierto junto a M01.
   Revisar pertenencia/roles verificados y configuracion
   administrable/editorial y recuperacion institucional;
   M02.2 tiene manifiestos/registro (158) y controles declarados de Inicio (159);
   seguir habilitacion institucional persistente/auditada, despues M02.3-M02.4 antes de extraer Observatorios M03. No crear una
   app universal de reservas. Antes de mover modelos, comprobar relaciones,
   permisos, respaldo y reversa sobre una copia de PostgreSQL.
4. Trabajar por bloques con la regla 4 de §2: suite completa → sección nueva en
   `CODEX_CONTEXT.md` → commit en español sin tildes → push.

---

## 7. Base obligatoria de seguridad y continuidad

La rama `reestructura-modular` actualiza el proyecto a Django 5.2 LTS y deja
las dependencias sin vulnerabilidades conocidas según `pip-audit`. El inicio
social usa POST con CSRF; producción bloquea contraseñas débiles de PostgreSQL,
orígenes inseguros, acceso social por GET y `unsafe-eval`. La base solo se
publica en `127.0.0.1` dentro de Docker y admite TLS verificado cuando el motor
es externo.

Los respaldos de PostgreSQL y `media/` se generan de forma atómica, validan su
contenido, crean SHA-256 y aplican retención configurable. El restaurador de
base usa una base efímera y debe ejecutarse mensualmente. La copia externa,
cifrada e inmutable y el PITR dependen de infraestructura institucional; no se
deben declarar operativos hasta completar una restauración real documentada.

`webcitt/tests/test_limites_arquitectura.py` congela los cuatro acoplamientos
de modelo a dominio ya existentes para impedir que aparezcan otros durante la
transición. `docs/seguridad-continuidad.md` contiene la topología, RPO/RTO,
runbook de restauración y orden de extracción de las apps. No se eliminó
ningún archivo público durante esta fase: tres pares de imágenes idénticas se
conservaron porque todavía tienen consumidores distintos.

---

## 8. Fronteras verticales obligatorias

La arquitectura vigente ya no agrupa la operacion de las cuatro clases en una
sola app `unidades` ni crea una reserva universal. Laboratorios, Plantas piloto,
Centros experimentales y Observatorios tendran configuracion, datos, rutas,
admin, plantillas, estaticos y pruebas propias. `directorio_unidades` conserva
solamente identidad publica, tipo, slug, responsables y contacto.

Centros I+D es un quinto contexto independiente, no una unidad reservable. Es
propietario de investigadores, lineas, grupos, proyectos, resultados, servicios
y transferencia. Se relaciona con las capacidades mediante contratos e IDs,
sin importar modelos de las cuatro unidades. La definicion obligatoria y el
orden de transicion estan en
`docs/arquitectura-vertical-unidades-centros-id.md`.

---

## 9. Portal institucional administrable

Inicio, Quienes somos, Servicios, Normativa y Noticias permanecen dentro de la
app `portal`, pero cada seccion tendra su propio modulo, modelos, consultas,
vistas, permisos, admin y pruebas. Hoy solo estan separadas como plantillas con
contenido fijo. La migracion convertira ese contenido en datos administrables
sin cambiar URLs ni el diseno institucional.

La pagina actual de Centros I+D es transitoria, pero ya posee ruta y vista en
`apps/centros_id/presentation`. Sus modelos y administracion siguen pendientes.
El portal consumira solo una proyeccion publicada. La definicion esta en
`docs/arquitectura-portal-administrable.md`.

## 10. Primera frontera ejecutada

`docs/rutas-y-contratos-modulares.md` describe los seis modulos de presentacion,
el contrato de identidad v1 y los adaptadores temporales. La fotografia en
`docs/inventario-arquitectura.json` se regenera con
`manage.py inventario_arquitectura`. Los paquetes nuevos todavia no se registran
como apps Django con modelos; `webcitt` conserva tablas, permisos y admin.
Un fallo de peticion se aisla del portal, pero un fallo de arranque del legado
todavia puede detener el proceso completo. No declarar aislamiento de datos o
despliegue hasta completar las siguientes fronteras.

## 11. Secuencia de ejecucion obligatoria

Seguir `docs/ruta-ejecucion-arquitectura-modular.md` y sus puertas de cierre.
Primero recuperacion y dependencias; despues codigo por vertical; modelos y
permisos se trasladan por agregado preparado, con copia y reversa. Aislamiento
de servicio requiere procesos y URLconf propios. No mezclar reorganizacion con
nuevas funciones de producto ni declarar migrado contenido aun no existente.

## 12. Producto configurable por institucion

El usuario define SLCID como producto comercial reutilizable. UPEC es un perfil
institucional; una institucion puede usar solo Laboratorios, otras agregar o
limitar categorias y habilitar modulos diferentes. Las cuatro verticales
actuales no son un techo: categorias compatibles son datos administrables,
modalidades nuevas requieren implementacion/contratos/pruebas propias.

La ruta revision 2 conserva M00-M13 y divide M02 en identidad/configuracion,
manifiestos/habilitacion/limites, categorias/extensiones y contratos/efectos
(M02.1-M02.4). La marca se inicia en M02.1; empaquetado y retiro quedan en M12.
Primero instalaciones con base/adjuntos/credenciales propios por institucion,
sin una rama del nucleo por cliente. SaaS multiinstitucion es una fase posterior.

Disponibilidad del despliegue, habilitacion institucional, derechos comerciales
y permisos son controles diferentes y se aplican en servidor. El admin no
instala codigo ni cambia INSTALLED_APPS en caliente. Suspender conserva datos
e historial, bloquea operaciones/tareas y permite recuperacion autorizada.
Los perfiles de aceptacion son: solo Laboratorios, Laboratorios con categorias
propias, UPEC y seleccion ampliada con extension operativa implementada.

El bloque documental 131 solo actualizo la ruta: perfiles minimos, registro configurable,
limites comerciales, empaquetado e aislamiento no estan implementados aun.
No renombrar ahora carpeta, repositorio, base, tablas o app labels heredados.

## 13. Primer bloque de identidad y ensayo de recuperacion

Se implementan contratos puros e inmutables en apps/core/identidad.py, perfil
publico UPEC en config/perfiles y constructor validado de entorno. HTML, admin,
correos, PDF principales y citas generadas consumen el mismo adaptador.
INSTITUTION_PROFILE=custom requiere nombre/siglas y no hereda contactos/logos
UPEC. Sin logo, cabecera y PDF usan siglas. No cambiar el entorno completo ni
exponer credenciales como configuracion publica. manage.py check valida campos.

M01 tiene evidencia local real: 135 tablas/6.654 registros y 358 adjuntos
comparados por hash en destinos temporales; la base temporal fue eliminada.
La copia y evidencia estan en backups/m01_20260916T112440Z_47d2ba30, ignoradas
por Git y con ACL privada. No sustituye coordinacion de escritores, copia
externa cifrada/inmutable, roles de infraestructura o servidor de contingencia.
La credencial local es superusuario y no se acepta como credencial de ejecucion
de produccion. No trasladar datos hasta cerrar M01 institucional.

No hay migraciones nuevas, traslados de tablas o cambios de permisos. Mantener
noticias/mapas/fotos/codigos FT, documentos emitidos y autorias reales de UPEC.
Catalogos academicos, calendario y configuracion visual/editorial siguen
pendientes; esta frontera no habilita modulos ni perfiles comerciales minimos.
Variables y alcance en docs/identidad-producto-institucion.md. Servidor unico
reiniciado en 127.0.0.1:8000; los diez recorridos HTTP principales respondieron
200, incluido PDF materiales/insumos con SAMEORIGIN.

Validacion final: suite completa de 829 pruebas, OK (1 omitida), 771.271 s.
Ruff, Django check, makemigrations --check y diff check correctos. Publicar este
bloque en reestructura-modular; mantener intacta integracion-version2-funciones.

## 14. Catalogo academico compartido por instalacion

apps/core/catalogos.py define el contrato puro/inmutable. config/perfiles/upec.py
conserva seis dependencias, dieciseis carreras y cinco categorias historicas.
ACADEMIC_CATALOG y el JSON de entorno permiten una configuracion propia; custom
no hereda carreras UPEC. Los providers callable de choices alimentan modelos,
formularios, admin, reservas, periodos e indicadores. Los tipos de clasificacion
conservan codigos y muestran siglas configuradas; no se crean permisos o grupos.

auditar_catalogo_institucional comprueba doce campos con conteos sin escrituras
ni identificacion de personas. Retirar codigos usados exige conservarlos como
historicos o revisar datos mediante un bloque autorizado. Las nuevas carreras
beneficiarias y perfiles requeridos no admiten categorias/carreras historicas.

0198_catalogo_academico_configurable se aplico en desarrollo. Es solo estado
Django/etiquetas: SQL no-op en ambos sentidos. En copia temporal se ensayaron
actualizacion/reversa/actualizacion con hashes identicos de datos, columnas,
indices y claves de 135 tablas; la copia temporal se elimino. django_migrations
registra el cambio de estado. La reversa se probo con datos UPEC compatibles;
si se agregan codigos propios, auditar contra el catalogo de la version anterior
antes de volver al codigo: cambiar de rama no convierte esos datos.
Ninguna de estas comprobaciones cierra M01 institucional o mueve modelos.

Pendientes: calendario/niveles, pertenencia/roles verificados, catalogos/tema
administrables y contenido editorial. Documentacion y procedimiento en
docs/catalogo-academico-institucional.md. No declarar instalacion comercial
completa, habilitacion de modulos o aislamiento real a partir de este bloque.

Validacion final: **837 pruebas, OK (1 omitida), 858.312 s**; cuatro arranques
independientes con resultados esperados, doce campos auditados compatibles,
reversa ensayada en copia y diez recorridos HTTP correctos. Ruff, check,
makemigrations --check, enlaces locales y diff check correctos. Publicacion en
reestructura-modular; integracion-version2-funciones permanece en 654bd1a4.


## 15. Continuacion M02.1: niveles y propuesta de avance (seccion 134)

Desde 95e43541 se separaron niveles y secuencias en el nucleo puro y adaptador
compartido por perfil, registro, admin, reservas, participantes y vinculaciones.
ACADEMIC_LEVELS_JSON admite niveles activos/historicos, niveles de estudiantes,
rutas disjuntas y etiqueta de dato faltante. UPEC conserva veinte codigos y
diez semestres; custom sin configuracion no hereda niveles. El modal del perfil
ya no filtra codigos por la palabra semestre. E003 bloquea configuracion invalida.

El avance ignora futuro/inactividad/borradores y usa fechas de la version vigente
de periodos anteriores, mismo ambito/tipo y carrera actual. Una propuesta de
avance requiere confirmacion y admite correccion sin cambiar el periodo anterior.
No concede roles ni acredita pertenencia. Calendario regional y tipos/ciclos/
ambitos siguen pendientes en otro bloque compatible de M02.1.

0199 cambia solo choices, sin SQL de tablas; aplicada en desarrollo. Actualizacion
y reversa ensayadas en copia M01 de 135 tablas, datos/columnas/indices/claves
identicos salvo django_migrations; copia eliminada. Auditor ampliado: dieciseis
campos compatibles, solo conteos. Conservar codigos historicos y no suponer que
regresar a una rama convierte datos propios al catalogo de esa version.

Suite completa: **844 pruebas, OK (1 omitida), 746.823 s**.
Ruff, check, ausencia de migraciones inesperadas, cuatro arranques
independientes, auditoria de dieciseis campos, reversa en copia, diez
recorridos HTTP y 53 enlaces locales correctos. Bloque preparado para
commit/push en reestructura-modular; base estable sin cambios.

Referencia: [Niveles y avance institucional](docs/niveles-y-avance-institucional.md).
Siguiente: calendario/configuracion regional y pertenencia/roles verificados,
catalogos administrables y contenido editorial. La recuperacion institucional
M01 sigue abierta; no extraer datos ni dar por completo aislamiento comercial.


## 16. Calendario institucional compatible (seccion 135)

Desde 2dcf4931 se separo politica de ciclos, ambitos y limites en el nucleo puro,
configuracion ACADEMIC_CALENDAR_JSON y proveedores compartidos con admin/modelo.
UPEC conserva cuatro ciclos/seis ambitos, default carreras_centros/16 semanas;
custom neutro solo ambito institucional. Admite C ordinario o ambitos propios.
E004 bloquea politica invalida. No cambia idioma/zona ni fechas existentes.

Perfil, reservas/propuestas y asistente usan filtros operativos comunes;
seleccion automatica por fechas reales de version vigente. Una actividad con
periodo explicito conserva su relacion. Ambitos_operacion vacio solo desactiva
asociacion automatica. Generar semanas valida periodo/version, es idempotente
y conserva restricciones existentes. Reportes usan maximo institucional.

Nuevo comando auditar_calendario_institucional, solo conteos: desarrollo un
periodo y dieciseis semanas sin incompatibilidades; auditor academico tambien
compatible. 0200 metadata de tres campos no-op SQL, aplicada en desarrollo.
Actualizacion y reversa en copia M01 de 135 tablas, datos/esquema/indices/FKs
identicos salvo django_migrations; base temporal eliminada. No dar por seguro
volver a codigo anterior tras escribir ciclos/ambitos propios: auditar/conciliar.

Suite completa: **850 pruebas, OK (1 omitida), 892.496 s**.
Seis casos nuevos, 46 pruebas focalizadas y 14 tras el ultimo ajuste;
cuatro arranques
independientes, migracion/reversa en copia de 135 tablas, ambos
auditores, diez recorridos HTTP, Ruff, check, migraciones sin cambios
inesperados, 61 enlaces locales y diff correctos.

Referencia: [Calendario institucional](docs/calendario-academico-institucional.md).
Siguiente: configuracion regional y pertenencia/roles verificados; luego
catalogos persistentes, tema/editorial y M02.2-M02.4. Limite fisico 24 semanas
no se amplio: requiere bloque propio de esquema/recuperacion. M01 institucional
y aislamiento real de despliegue siguen pendientes. No trasladar datos todavia.


## 17. Configuracion regional institucional (seccion 136)

Desde edca93a6, contrato puro + entorno + adaptadores para idioma y zona.
INSTITUTION_LANGUAGE_CODE=es-ec e INSTITUTION_TIME_ZONE=America/Guayaquil son
predeterminados compatibles incluso en custom sin override. Otra zona exige
conciliacion de agendas, no se infiere de identidad ni dispositivo. E005 y
validacion temprana bloquean configuracion invalida; no traduccion integral.

HTML/calendario/asistente usan idioma institucional. Hoy en JS se calcula con
Intl y zona institucional; timestamps en tarjetas/CSV usan esa zona. Reserva
usa default_timezone para fecha/hora, y fecha pasada usa localdate institucional.
API/modelo rechazan horas inexistentes/duplicadas y salto en reserva diaria;
valida todas las sesiones antes de escribir. Servicios convierten plazos.
Historial se conserva; no hay fold/offset persistente ni migraciones nuevas.

Auditor auditar_configuracion_regional admite --zona-horaria y --database,
solo conteos; error si hay cambios de instante o horarios incompatibles.
UPEC: 103 reservas sin conflictos. Ejecutarlo con zona actual antes de cambiar
entorno; tambien conciliar servicios/bloqueos/notificaciones/integraciones.
No convierte ni certifica esos dominios.

Suite completa: **860 pruebas, OK (1 omitida), 865.210 s**.
Diez casos nuevos, 92 pruebas focalizadas y nueve tras ultimo ajuste;
seis arranques independientes, auditor regional de 103 reservas compatible,
diez recorridos HTTP, PDF SAMEORIGIN, cuatro archivos JS, Ruff, check,
makemigrations sin cambios, 69 enlaces y diff correctos.

Referencia: [Configuracion regional](docs/configuracion-regional-institucional.md).
Siguiente: pertenencia/roles verificados y fallback historico de tarifas;
luego catalogos administrables y tema/editorial. M01 institucional pendiente,
no extraer datos ni afirmar aislamiento comercial. M02.1 sigue abierto.

## 18. Interfaz ES/EN por navegador (seccion 137)

Selector en cabecera publica y admin, preferencia anual HttpOnly/SameSite=Lax,
Secure en produccion. POST CSRF y next seguro; conserva pagina/query/ancla.
LocaleMiddleware entre sesiones y CommonMiddleware. Idioma personal separado
de zona institucional; no cambia UTC, permisos, perfil, IDs o datos historicos.
No nuevas migraciones. ES conserva formato regional institucional.

8430 mensajes por idioma, PO/MO en locale/es y locale/en. Un solo dominio django
para templates/Python/JS, catalogo por idioma con cache privada/Vary Cookie.
Gzip/Vary Accept-Encoding reduce descarga. Selector conserva modulo/recurso
abierto usando ?recurso=<id>#modulo existente, sin almacenar formularios ni PII.
Helper interfaz.html traduce literales y escapa traducciones; conserva valores
interpolados, cuyo escape sigue siendo responsabilidad de quien crea HTML.
Formularios/admin traducen etiquetas/grupos y mantienen claves/ModelChoice.
Documentos independientes cargan assets. Build reserva 20260916-idiomas-v141.

Editar ambos PO y compilar con scripts/compilar_idiomas.py; --check detecta MO
obsoleto. No herramientas/modelos de traduccion en produccion. Asistencia local
y glosario revisado; no certifica todos los textos cientificos. Contenido escrito,
nombres/productos/recursos y archivos cargados permanecen en idioma original.
No auto-traducir documentos ni duplicar registros para cambiar idioma de interfaz.

Catorce casos nuevos y Chrome aislado con portal/lacteos ES/EN y 1366/390/360 px
sin errores JS. Plantillas ES/EN, JS, Ruff y makemigrations correctos.
Suite completa: 874 pruebas, OK; una omitida, 1573.894 segundos.
Catalogos compilados y 75 enlaces locales verificados.

Referencia: [Interfaz ES/EN](docs/internacionalizacion-es-en.md).
Siguiente: pertenencia/roles verificados y tarifas historicas; luego catalogos
persistentes/editorial. M01 institucional sigue abierto; no extraer datos.


## 19. Idioma en barra superior

Selector ES/EN a la derecha de Contacto en barra verde, fuera de nav-tools.
Barra visible tambien en movil (32 px); menu y notificaciones desplazados
para conservar accesibilidad. Admin mantiene su selector. Sin cambio de datos.
Suite completa: 874 pruebas, OK; una omitida, 526.272 segundos.
Chrome verificado en 1366/1200/1024/768/390/360 px sin errores JavaScript.


## 20. Selector compacto

Barra verde con altura inicial de 32 px; selector de 26 px y botones de 22 px.
Menu y notificaciones ajustados a la barra. Sin cambios en admin o idiomas.
Suite completa: 874 pruebas, OK; una omitida, 445.969 segundos.
Chrome ES/EN y seis anchos comprobados, sin desbordamiento ni errores JS.


## 21. Estado y responsive auditados

M02.1 sigue en curso; M01 institucional abierto. Pasos funcionales 1-7
integrados, pero falta contenido tecnico aprobado y procesos por completar.
Auditoria responsive publica: 182 combinaciones, HTTP 200, cero errores JS;
36 presentan desbordamiento horizontal en login movil y decoracion de cuatro
catalogos. No estan corregidos. Prioridad: arreglo y pantallas autenticadas.
30 pruebas focalizadas OK (29.287 s); suite integral vigente del bloque 139,
874 OK con una omitida (445.969 s). Esta entrega solo documenta la auditoria.
[Estado y pendientes](docs/estado-plan-y-responsive-20260916.md).


## 22. Responsive corregido y operacion revisada

Continuacion de la auditoria 140, historial 141. Correcciones locales en acceso,
registro, decoracion de catalogos y filas anidadas del Perfil. Encabezado con
menu plegable por debajo de 1280 px evita solapamiento autenticado a 1200.
Conserva selector ES/EN compacto y rutas/datos/permisos. Cache CSS renovada.

Chrome: 182 combinaciones publicas y 574 autenticadas con cuatro perfiles,
ES/EN y siete anchos, sin desbordamientos ni errores JavaScript. Modales de
edicion, paneles de reservas, gestion y admin incluidos segun rol. QA en base
temporal retirada al terminar, sin cambiar datos activos. Revision del asistente
es de presentacion, sin envio de reservas. Detalle con 30 recursos se desplaza
internamente en escritorio y se expande dentro del asistente en movil.
Modal PDF: 14 casos correctos, mismo tab y cierre Escape. No certifica zoom,
dispositivos fisicos o navegacion por teclado. Plantillas/JS/Ruff/check correctos;
sin migraciones nuevas.

Seguir M02.1 con pertenencia/roles y tarifas historicas; M01 institucional
continua abierto antes de traslados de datos. No cerrar modularidad por estos
ajustes de interfaz. [Metodo y limites](docs/responsive-portal-y-operacion.md).

Suite completa: 874 pruebas, OK; una omitida, 1115.434 segundos.


## 23. Roles operativos y delegaciones seguras

Historial 142. Recomendaciones neutrales en apps/core/roles, sin Django/modelos;
OPERATIONAL_ROLES_JSON y check slcid.E006. Defaults mantienen comportamiento;
politica configurable por instalacion no asigna cuentas ni reemplaza matrices
expresas. Tipo academico declarado no concede gestion de unidades.

Matriz JSON exige modulos conocidos y true/false reales. Datos invalidos se
rechazan al editar y se deniegan al usar, incluso escritos sin validar. Cuenta
inactiva o sin guardar no administra; responsabilidad desactivada no opera.
La previsualizacion para editar conserva matriz al desactivar y no autoriza.
19 pruebas nuevas, cuatro tipos de unidades; 35 focalizadas OK (21.475 s) y
19 finales OK (0.589 s). ES/EN compilados, Ruff/check correctos, sin migraciones.
Auditoria activa solo lectura sin matrices/roles invalidos ni delegaciones
activas con cuenta inactiva; base activa intacta.

Siguiente: verificar pertenencia/tipos declarados con trazabilidad y documentos
historicos preservados; despues tarifas historicas. M02.1 y M01 institucional
siguen abiertos. [Politica y administracion](docs/roles-y-delegaciones-operativas.md).

Suite completa: 893 pruebas, OK; una omitida, 1047.899 segundos.


## 24. Revision institucional e historial

Historial 143. Separacion de perfil completo, confirmacion de periodo y
pertenencia/tipo aprobado. Nucleo puro apps/core/pertenencia; servicio y admin
bajo usuarios. Revisor activo staff con permiso especifico y lectura/cambio del
perfil; sin autorrevision, tampoco superusuario. No se otorgan permisos nuevos
a grupos/cuentas. Datos nuevos o de demostracion nunca se autoaprueban.

Revision desde perfil admin, con decision, fundamento, referencia y vencimiento
opcional. POST/CSRF, identidad y ultima decision para evitar formularios viejos,
bloqueos transaccionales. Historial readonly, paginado, FK PROTECT perfil/revisor:
desactivar es posible, eliminar cuentas con decisiones no. API impide cambios
o borrado ordinarios; SQL/credenciales privilegiadas requieren infraestructura.
Migracion aditiva 0201, conservarla al volver al codigo anterior si tiene datos.
Con decisiones, las FK pueden impedir borrados que el codigo viejo no conoce:
el retorno requiere parche de retencion o bloquear esas eliminaciones, no DROP.

Perfil ES/EN muestra estado y vigencia sin evidencia privada; paginas no-store.
Identidad modificada, vencimiento/cuenta inactiva requieren nueva revision o
restauracion de identidad exacta revisada; no audita cada edicion. Nivel por
periodo sigue independiente. No modifica reservas/cotizaciones ni delegaciones.

28 nuevas/finales OK, 2.383 s. Huella no ASCII no causa error interno.
Chrome temporal: 28 combinaciones ES/EN en siete
anchos, Perfil/formulario, sin desbordamientos ni errores JS. Boton Grappelli
recortado corregido; cabecera compartida del admin recorta elementos en movil,
pendiente medir controles y corregir. No certificar toda esa cabecera por ancho.

Siguiente: conectar pertenencia verificada con autoria de guias y segmentos
tarifarios, sin cambiar historia ni aprobar automaticamente cuentas existentes.
M02.1/M01 institucional siguen abiertos; no extraer datos/apps.
[Funcionamiento y limites](docs/verificacion-institucional.md).

Migracion 0201 aplicada localmente. Auditoria agregada: 34 perfiles, 27 con datos
completos, 31 internos con procedencia distinta a las siglas configuradas; necesitan
revision/canonicalizacion antes de aprobar, sin actualizacion masiva automatica.
Cero decisiones, cero usuarios/grupos con permiso de revision explicito; cinco
permisos nuevos. Superusuario activo conserva autoridad para revisar otros perfiles.

Suite completa: 921 pruebas, OK; una omitida, 909.938 segundos.


## 25. Continuacion 144: pertenencia efectiva en guias y tarifas

Autoria nueva unificada en permisos.puede_crear_guias_unidad: docente con
revision vigente o practicas de esa unidad; staff solo no acredita. Editor,
reserva y detalle usan la misma regla. Se filtran guia/actividad/fuentes
privadas por propiedad/delegacion; no leer objetos ajenos desde otra unidad.
Autores conservan correccion de documentos propios existentes segun estado.

Servicios/recursos nuevos guardan pertenencia_tarifaria en JSON existente.
Sin aprobacion vigente se estima como externo, sin cambiar perfil/periodo.
Externo aprobado sigue externo; delegacion no implica descuento. Consultar
perfil y User frescos; no inferir pertenencia de correo/nombre institucional.
Historicos: segmento emitido -> tipo guardado -> externo, nunca perfil actual.
Recalculo/consumo real conserva segmento/prueba anterior; no congela todos
los precios del tarifario ni genera una factura definitiva.

Bloqueos para altas: unidad -> User -> UserProfile; revision User -> perfil.
Revalidacion bajo bloqueo detiene cambio durante envio sin alta parcial.
No se necesitan migraciones ni escrituras masivas sobre la base activa.
Las cuentas reales pendientes necesitan cotejo por un revisor autorizado;
ninguna cuenta real se aprobo en este bloque. Datos completos no es revision.

Header admin corregido: marca, herramientas e idiomas visibles sin
solapamientos, filas hasta 1200px. QA Chrome 140 combinaciones ES/EN siete
anchos, cuatro estados de pertenencia, guia/reserva/admin/revision. Sin JS
errors/overflow/recortes de controles admin; DB/sesiones temporales retiradas.
Revisar alto del titulo/subtitulo ingles en modal reserva a 360px: ese detalle
queda pendiente, no certificar toda la interfaz. Catalogos 8477 mensajes.

13 pruebas nuevas y finales OK. Suite completa: 934 pruebas, OK; una omitida, 781.806 segundos.
Ver CODEX_CONTEXT.md 144 y docs/pertenencia-guias-y-tarifas.md.
Siguiente M02.1: configuracion editorial/persistente y marca restante;
despues M02.2-M02.4. M01 institucional no cerrado: no trasladar datos ni
afirmar aislamiento total o seguridad certificada.


## 26. Continuacion 145: editor de presentacion en app propia

Configuracion institucional > Presentaciones institucionales: guardar borrador,
abrir Revisar y publicar, confirmar. Publicar requiere staff activo + view y
publicar_presentacion; guardar requiere add. No concede permisos reales.
Recuperar crea snapshot nuevo; En uso muestra actual, Publicada es historia.
No modificar/borrar historia/puntero. Solo nombres/contactos/logos instalados:
no codigos, credenciales, SMTP, dominios OAuth, pertenencia o tarifas.

apps/configuracion_institucional tiene models/services/selectors/admin,
migrations/management/templates/tests propios, sin webcitt en codigo operativo.
ORM operativo existente sigue en webcitt. PUBLIC_IDENTITY_PROVIDER instalado
en settings, vacio permite solo despliegue; E007 valida configuracion sin SQL.
identidad_actual usa scope HTTP; fuera de scope usa despliegue. Mail reserva
ya abre scope; tareas/PDF futuros necesitan con_presentacion_institucional.
No cambiar codigos para adoptar datos de otra institucion.

Ausencia/invalidez usa base y advertencia generica. Comando
auditar_presentacion_institucional agrega conteos/estado y falla si inconsistente.
No garantiza operacion ante caida de todo el motor. M01 institucional abierto;
SQL privilegiado puede eludir guardas. Reversa solo nuevas tablas vacias;
conservar historia/tablas con codigo compatible, sin limpieza ContentTypes.

16 nuevas pruebas; integracion final 40 OK. Chrome 210 combinaciones ES/EN,
siete anchos/cuatro estados: corrige login 360 y header reserva ingles pendiente
144. Auth Django/CSRF/next conservados. Base/sesiones QA retiradas. Catalogos
8510 mensajes; Ruff/check/makemigrations/templates/JS OK.
M02.1 sigue: persistir/versionar catalogos academicos, paleta y consumidores
editoriales; M09 otras secciones. Despues M02.2-M02.4. Referencia CODEX_CONTEXT
145 y docs/presentacion-institucional-administrable.md.

Migracion 0001 aplicada en desarrollo despues de la suite, con dump previo
local ignorado y ACL solo operador/SYSTEM, checksum y catalogo verificado.
No se afirma restauracion integral de ese dump nuevo ni cierre de M01.
Comparacion activa: filas/esquema/indices/claves previos identicos; metadata
aditiva (dos ContentTypes, cinco permisos, una migracion). Cero revisiones,
publicaciones o concesiones explicitas reales; datos/permisos anteriores
conservados. Media no modificada. Auditoria previa de pertenencia conserva
34 perfiles, 27 completos, 31 procedencias no canonicas, cero decisiones y
concesiones explicitas. No autoaprobar/canonicalizar cuentas reales.

Servidor propio reiniciado --noreload con codigo final y estaticos recogidos.
Inicio/planta/login admin 200; perfil/listado/editor institucional anonimos 302.
Sin login con cuenta real. Avisos preexistentes de overrides Grappelli en
collectstatic; sin nuevos duplicados.

Suite completa: 950 pruebas, OK. Una omitida; 925.918 segundos.

## 27. Continuacion 146: catalogo academico en app propia

Configuracion institucional > Catalogos academicos: crear revision, guardar
borrador y Revisar y publicar. Dependencias/carreras/historicos/tipos con carrera
se editan mediante filas; sin JS queda JSON validado. Un payload maximo 1 MB,
200 dependencias internas mas externo, 2000 carreras. No edita niveles/calendario.
Guardar requiere add; publicar staff activo + view + publicar_catalogo.
Cuenta/permisos se recargan; CSRF/checkbox/version revalidados. Sin permisos
reales concedidos. En uso muestra actual, Publicada es historia inmutable.

Conservar todos los codigos. Carrera retirada pasa a historica; reactivar solo
en dependencia original. Historicos heredados sin relacion no se reutilizan
como carrera nueva. Cambiar relacion exige nuevo codigo. Recuperar crea nueva
publicacion compatible; versiones obsoletas/incompatibles se bloquean.
Los reportes usan etiquetas actuales, no snapshots de etiquetas por registro.

catalogos/ guarda models/services/selectors/forms/admin; templates/static/tests
y 0002 dentro de apps/configuracion_institucional. versionado.py comparte
guardas con presentacion. Cuatro modelos propios total; ORM operativo sigue
webcitt. ACADEMIC_CATALOG_PROVIDER fijo, vacio usa despliegue; E008 sin SQL.
Scope HTTP comparte version; tareas/importadores necesitan
con_catalogo_institucional. Verificacion ya abre scope fuera de HTTP.
Auditor explicito estricto revisa dieciseis campos con conteos, sin PII; fallback
no certifica inconsistencia. Namespace ajeno no hereda catalogo publicado.

19 pruebas nuevas, integracion final 81 OK (22.479 s). Chrome 224 casos ES/EN,
cuatro estados/siete anchos; capturas editor/revision ingles 360 inspeccionadas.
Sin errores o recortes medidos; no certifica toda la interfaz/carga masiva.
QA retirado, ningun perfil real aprobado/normalizado. Catalogos 8556 mensajes.
Ruff/check/makemigrations/JS OK. Ensayo 138 tablas anteriores identicas, dos
nuevas vacias, aplicar/revertir/aplicar 0002; reversa solo en vacio.

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

M02.1 siguiente: persistir niveles/calendario, paleta y consumidores editoriales.
M09 otras secciones; despues M02.2-M02.4. M01 institucional abierto; SQL
privilegiado puede eludir guardas, misma DB/proceso sin aislamiento M11.
Cambiar rama no restaura datos/media. Codigo previo debe auditarse contra
codigos nuevos publicados antes de retornar; no limpiar permisos/ContentTypes.
Ver CODEX_CONTEXT.md 146 y docs/catalogo-academico-administrable.md.

Suite completa: 969 pruebas, OK. Una omitida; 979.411 segundos.

## 28. Continuacion 147: niveles y rutas administrables

Configuracion institucional > Revisiones de niveles academicos: crear/guardar
borrador, revisar activos/historicos/estudiantes/rutas y confirmar publicacion.
Add para guardar; publicar staff activo + view + publicar_niveles, autoridad
fresca/CSRF/checkbox/base vigente. Sin concesiones reales. Historial inmutable
y recuperacion nueva compatible. Conservar codigos, retirar como historicos;
perfil estudiantil con nivel retirado necesita actualizarse para operar.
Cambiar ruta modifica propuestas futuras, conserva confirmacion/historia;
sin bifurcaciones/planes simultaneos con mismo codigo sin relaciones explicitas.
MAX 200 activos/historicos, codigos 30 caracteres y JSON 100.000, fallback sin
JS. Payload invalido visible, sin truncarlo. ES/EN: 8590 mensajes.

niveles/ y templates/static/tests/0003 en app propia. Seis modelos propios;
ORM operativo sigue webcitt. editor_revisiones.py/formularios.py/editor.css
compartidos con catalogos; lectura comun sustituye plantilla sin consumidores.
ACADEMIC_LEVELS_PROVIDER fijo/vacio base, E009/E003 sin SQL. Scope HTTP y APIs
vigencia/verificacion fuera de HTTP; futuras tareas necesitan
con_niveles_institucionales. Auditor CLI ambos proveedores estrictos por alias,
dieciseis campos, sin PII/escrituras ni certificar fallback.
14 pruebas nuevas; integracion 89 OK (22.506 s), navegacion final 14 OK (2.574 s).
Ruff/check/makemigrations/
templates/JS OK. Ensayo aplicar/revertir/aplicar 0003: 140 tablas anteriores
identicas y dos nuevas vacias; reversa solo vacia. SQL privilegiado elude guardas.

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

Siguiente M02.1 calendario persistente, paleta y consumidores editoriales;
M09 otras secciones; despues M02.2-M02.4. M01/M11 abiertos; no extraer datos.
Cambiar rama no restaura base/media; auditar codigos nuevos contra proveedor
previo. No limpiar permisos/ContentTypes. CODEX_CONTEXT 147 y
docs/niveles-academicos-administrables.md.

Suite completa: 983 pruebas, OK. Una omitida; 1008.144 segundos.

## 29. Continuacion 148: calendario administrable

App configuracion_institucional agrega calendario propio y 0004: ocho modelos
total. Editor comun para catalogos/niveles/calendario; borrador no activa,
historial inmutable, publicar con base esperada y autoridad fresca. Ciclos,
ambitos, seleccion automatica/default y semanas 1..24 editables. Conserva
codigos y tipo historico, incluso sin uso; valida candidato contra periodos/
semanas. No cambia fechas oficiales, reservas, vinculaciones ni suspensiones.

Nuevo proveedor fijo ACADEMIC_CALENDAR_PROVIDER, E010 y contexto por peticion.
Periodo vigente/resolver periodo reserva/generar semanas abren scope para llamadas
directas; tareas y constructores/formularios ORM fuera HTTP deben abrirlo tambien.
No SQL al importar/checkear; fallback normal con aviso generico. CLI auditor estricto
por alias: falla sin proyeccion integra, no usa fallback para certificar.

14 pruebas nuevas y cuatro instituciones; inicial 53 OK (6.242 s).
Ajuste final: 74 OK (9.537 s). ES/EN 8622 mensajes; JSON manual/rechazado
conservado sin truncar/normalizar duplicados; no conceder permisos reales.
Reversa/ida en copia conserva 142 tablas; solo ensayada con nuevas vacias.

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

Sigue M02.1 paleta y consumidores editoriales; M09 otras secciones, luego M02.2-M02.4.
M01/M11 abiertos. No extraer datos ni afirmar aislamiento de DB/proceso compartidos.
Cambiar rama no restaura PostgreSQL/media; conservar historia y auditar referencias
nuevas contra contrato anterior. CODEX_CONTEXT 148 y
docs/calendario-academico-administrable.md.

Suite completa: 997 pruebas, OK. Una omitida; 465.637 segundos.

## 30. Continuacion 149: paleta institucional administrable

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

## 31. Continuacion 150: logos institucionales administrables

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

## 32. Continuacion 151: editor de paleta HEX y degradados

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


## 33. Continuacion 152: Vista previa inmediata en los cinco campos de logo

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


## 34. Continuacion 153: Paleta de botones y tarjetas en el sistema

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


## 35. Continuacion 154: lineas, degradados, tipografia y contraste

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


## 36. Continuacion 155: acciones solidas y lectura sobre imagenes

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


## 37. Continuacion 156: portada bilingue en la app Portal

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


## 38. Continuacion 157: soporte institucional y titulos operativos

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


## 39. Continuacion 158: manifiestos y registro de modulos

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


## 40. Continuacion 159: controles de Inicio editorial

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


## 41. Continuacion 160: habilitacion institucional de Inicio

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

## 42. Continuacion 161: inventario antes de ampliar controles

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

## 43. Continuacion 162: contratos y auditoria de senales

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

## 44. Continuacion 163: codigos de reserva y recuperacion

Servicio compartido webcitt/services/codigos_reserva.py: fila fresca bloqueada,
atomic/savepoint y preservacion de codigo no vacio; formato RL conservado.
Receiver conserva fallo no bloqueante con WARNING fijo sin datos/SQL/traceback,
omite raw y propaga using. Error SQL no invalida transaccion llamadora.
CLI recuperar_codigos_reservas audita por defecto; aplicar exige unidad positiva,
revisa alcance fresco por fila, informa lote parcial y permite reintento.
Auditoria de desarrollo: 0 pendientes, sin reparacion de datos reales.
Guia y limites: docs/codigos-reserva-recuperacion.md.

Manifiestos legado/integraciones 1.3.0; 19 contratos/decoradores/conexiones,
cero hallazgos, cero fallos descartados/uno observable; seis archivos revisados.
Inventario sin SQL: 11 modulos, 104 rutas, 96 modelos heredados/12 propios,
67 admin, 23 comandos, 11 scripts y 19 receivers.
17 pruebas nuevas; focal contratos/limites 38 OK (13.480 s).
Suite integral: 1162 pruebas, OK, una omitida; 1050.122 segundos.
Ruff/check/makemigrations en seco correctos; sin esquema, rutas o interfaz nueva.
Log ignorado: tmp/validacion-codigos-integral.log.

M02.4 parcial. Siguiente: revisar escritores/validadores/tareas de reservas y
su autoridad por unidad antes de ofrecer guardas de suspension.
M02.2/M02.3/M01 institucional/M11 abiertos; proceso/base/URLconf compartidos.
No se traslada modelo/receiver/autoridad ni se garantiza aislamiento operativo.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## 45. Continuacion 164: autoridad y escritores de reservas

Matriz docs/escritores-y-autoridad-reservas.md: entradas HTTP, servicios,
primitivas, modelo, admin, tareas y cargas; autoridad/alcance/efectos/pendientes.
No certifica todos los escritores ni instala suspension institucional.
Dos servicios reforzados: completar_sesion atomic propio, fila fresca bloqueada,
titular/unidad/estado/programacion vigentes; aplicar_solicitud_cambio exige
permiso reservas dentro del servicio. Vistas pasan unidad_esperada.
Guarda carga cuenta persistida activa, no confia en privilegios obsoletos;
practicas/reservas separados, staff de otra unidad no concede acceso.
Scope distinto rechaza incluso superusuario; eliminado durante POST da 404.

23 pruebas nuevas; focal final cambios/programacion/limites/idiomas:
57 OK, 43.277 s. Carrera PostgreSQL real verifica SELECT FOR UPDATE enviado,
espera Lock y rechaza edicion despues de aprobacion; rollback tardio conserva datos.
Fixtures HTTP vigentes y assert de invocacion verifican 403/404 en el servicio.
Suite integral final: 1185 pruebas, OK, una omitida; 1012.622 segundos.
Log ignorado tmp/validacion-escritores-integral.log. Ruff/check/migraciones en
seco correctos; ES/EN 8762 mensajes compilados/verificados, tres textos nuevos.
Auditoria senales 19/19/19, cero hallazgos. Inventario permanece 11 modulos,
104 rutas, 96 modelos heredados/12 propios, 67 admin, 23 comandos/11 scripts.

No se ejecutaron cargas/reparaciones sobre datos reales. Sin modelos/esquema/
rutas/CSS/HTML/JS nuevos; no renueva certificacion responsive.
M02.4/M02.2 parciales; siguiente registrar_cierre_operativo: autoridad, fila
fresca, repeticion y efectos inventario/finanzas/produccion sin duplicacion.
Luego propuestas/gestion/tareas/admin/cargas y clasificar historial bajo suspension.
M02.3/M01 institucional/M11 abiertos; base/proceso/URLconf/credenciales compartidos.
Guarda no sustituye perfil middleware, control comercial o aislamiento de procesos;
no serializa toda revocacion posterior ni disponibilidad entre otras reservas.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## 46. Continuacion 165: cierre operativo autorizado y sin repeticion

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

## 47. Continuacion 166: auditoria del estado y siguiente bloque

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

## 48. Continuacion 167: envio seguro de propuestas

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

## 49. Continuacion 168: decisiones propias de solicitudes de cambio

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

## 50. Continuacion 169: solicitudes y cancelacion propias

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

## 51. Continuacion 170: gestion administrativa simple de reservas

gestion_reserva_accion_view delega asignar, anotar y solicitar_info en
reservas.administracion.gestionar_reserva_administrativa, conservando ruta y JSON.
Servicio atomic en default: bloquea Reserva, revalida cuenta/permiso/unidad/estado
persistidos y devuelve fila fresca. Guarda cerrada suma asignar_responsable,
anotar_reserva y solicitar_informacion: doce operaciones conocidas.

Asignar solo acepta ResponsableUnidad vigente de la misma unidad, con cuenta,
activo y recibe_reservas. Notas/solicitud requieren texto hasta 1200 caracteres;
workflow conserva estados permitidos. Reserva, LogEntry, auditoria y aviso de
informacion son atomicos; fallo tardio revierte todo. Las primitivas de observacion,
fotografia y bitacora se centralizan en reservas.trazabilidad y la gestion heredada
usa wrappers, sin duplicar la representacion del historial.

11 pruebas nuevas de autoridad, alcance, estado/responsable frescos, alias,
ES/EN, rollback y adaptacion HTTP. Carrera PostgreSQL observa FOR UPDATE/Lock:
dos notas simultaneas conservan ambas. Focal con dos recorridos heredados: 13 OK,
7.073 s. Suite completa: 1308 OK, una omitida, 1294.069 s. Ruff/check/migraciones
en seco correctos; ES/EN 8799; senales 19/19/19 sin hallazgos. Sin rutas/modelos/
esquema/interfaz/datos reales nuevos y sin nueva certificacion responsive.

M02.4/M02.2 parciales. Siguiente: aprobacion/rechazo/cancelacion administrativa,
inicio/cierres alternos/correccion; luego primitivas/tareas/admin/cargas y controles
de capacidad. M01 institucional/M11 pendientes; proceso/base/URLconf/credenciales
compartidos. Publicar en origin reestructura-modular; conservar rama estable.

## 52. Continuacion 171: rechazo y cancelacion administrativa

gestion_reserva_accion_view delega rechazo y cancelacion por laboratorio en
reservas.decisiones_reserva.decidir_reserva, conservando ruta y JSON. Servicio
atomic en default: bloquea Reserva, revalida cuenta/permiso/unidad/estado y
devuelve fila fresca. La guarda cerrada suma rechazar_reserva/cancelar_reserva:
catorce operaciones conocidas.

Rechazar solo admite pendiente y atribuye validacion; cancelar admite pendiente
o confirmada y conserva autor, fecha, origen laboratorio y motivo. Ambas exigen
motivo textual no vacio de hasta 1200. Orden de practica abierta, solicitud de
cambio activa, avisos incompatibles, LogEntry y auditoria se resuelven en la
misma transaccion. Fallo tardio revierte todo y una carrera PostgreSQL serializa
dos cierres rivales. No se elimina la reserva ni su expediente.

9 pruebas nuevas y tres recorridos heredados: focal 12 OK, 5.116 s; conjunto
ampliado 96 OK, 15.528 s. Suite completa: 1317 OK, una omitida, 601.415 s.
Ruff/check/migraciones en seco correctos; ES/EN 8803; senales 19/19/19 sin
hallazgos. Sin rutas/modelos/esquema/interfaz/datos reales nuevos y sin nueva
certificacion responsive.

M02.4/M02.2 parciales. Siguiente: aprobacion con agenda, responsable, orden de
practica y planificacion; luego inicio/cierres/correccion y despues tareas/admin/
cargas. M01 institucional/M11 pendientes; proceso/base/URLconf/credenciales
compartidos. Publicar en origin reestructura-modular; conservar rama estable.

## 53. Continuacion 172: aprobacion integral de reservas

gestion_reserva_accion_view conserva ruta y contrato HTTP, pero la aprobacion
delega en reservas.aprobacion.aprobar_reserva. El servicio bloquea Unidad y
Reserva, vuelve a comprobar cuenta, permiso, alcance y estado, valida la
compuerta documental, asigna un responsable vigente y comprueba aforo y agenda.
La confirmacion, orden de practica, planificacion, avisos, LogEntry y auditoria
se escriben atomicamente. La guarda interna llega a quince operaciones.

La validacion persistente de conflictos se traslado de reservas.views a
reservas.conflictos y ahora la comparten creacion, cambios, cronograma, visitas,
reprogramacion y aprobacion sin depender de una vista. Diez pruebas nuevas y una
carrera PostgreSQL cubren permisos, datos frescos, rollback y asignacion bajo
concurrencia. Focal ampliado: 156 OK, 82.859 s. Suite integral: 1327 OK, una
omitida, 641.935 s. Ruff/check/migraciones, catalogos ES/EN 8805 y senales
19/19/19 correctos. No hubo cambios de interfaz, rutas, esquema ni datos reales.

Siguiente: separar inicio, no_presentado y no_atendida; despues cerrar la
orquestacion exterior de completar y extraer actualizar/correcciones. Luego
continuar primitivas, tareas, admin, cargas y la cobertura completa de capacidad.
M02.4/M02.2 siguen parciales; M01 institucional y M11 permanecen pendientes.

## 54. Continuacion 173: inicio y cierres alternos

gestion_reserva_accion_view conserva ruta y contrato HTTP, pero iniciar,
no_presentado y no_atendida delegan en transiciones_operativas. El servicio
bloquea la Reserva y revalida cuenta, permiso, alcance y estado. Mantiene la
documentacion y control de ingreso al iniciar; en los cierres conserva horario,
regularizacion, asistencia, orden de practica, solicitudes, avisos y trazabilidad
dentro de una transaccion. La guarda interna llega a dieciseis operaciones.

responsables.py centraliza la seleccion explicita usada por administracion,
aprobacion y transiciones, incluida la cuenta vinculada activa. Diez pruebas
nuevas y una carrera PostgreSQL cubren datos frescos, rollback y dos cierres
rivales. Focal combinado: 150 OK, 298.112 s. Suite integral: 1337 OK, una
omitida, 1767.513 s. Ruff/check/migraciones, catalogos ES/EN 8809 y senales
19/19/19 correctos. No hubo cambios de interfaz, rutas, esquema ni datos reales.

La vista heredada conserva solo actualizar y completar. Siguiente: extraer la
orquestacion exterior de completar; despues actualizar/correccion, tareas,
admin, cargas y controles completos de capacidad. M02.4/M02.2 siguen parciales;
M01 institucional y M11 permanecen pendientes.

## 55. Continuacion 174: finalizacion integral fuera de la vista

reservas.finalizacion.completar_reserva es ahora la frontera transaccional de la
accion completar. Revalida autoridad, alcance, estado, documentacion y horario;
sincroniza responsable y participantes; y confirma cierre operativo,
habilitaciones, solicitudes, avisos y trazabilidad como una sola unidad. Un fallo
tardio revierte tambien la liquidacion y cualquier cambio de asistencia.

reservas.participantes contiene la clasificacion historica y asistencia que antes
estaban duplicadas o privadas en views.py y gestion.py. Cambios y visitas ya
consumen esa frontera. La vista conserva ruta, payload, JSON y codigos HTTP.

Dos pruebas nuevas elevan la suite a 1339: directo 23 OK, focal ampliado 185 OK
y suite integral 1339 OK, una omitida, 933.797 s. Ruff/check/migraciones,
catalogos ES/EN con 8810 mensajes mas cabecera y contratos de senales 19/19/19
correctos. No hubo cambios de interfaz, rutas, esquema ni datos reales.

La vista heredada conserva solamente actualizar/correccion. Siguiente: extraer
esa transaccion completa y despues revisar primitivas, tareas, admin, cargas y
controles de capacidad. M02.4/M02.2 siguen parciales; M01 institucional y M11
permanecen pendientes.

## 56. Continuacion 175: correccion integral de reservas

gestion_reserva_accion_view conserva ruta, payload, JSON y mapeo 400/403/409,
pero ya no escribe reservas. reservas.correccion.corregir_reserva bloquea primero
la Unidad y luego la Reserva, revalida cuenta, permiso, alcance y estado vigentes,
y coordina agenda, recursos, condiciones, participantes, consumibles, adjuntos,
responsable, revisiones, planificacion, avisos, LogEntry y auditoria dentro de un
atomic. Un fallo tardio revierte el expediente; correcciones concurrentes de una
unidad esperan el mismo bloqueo. La guarda cerrada llega a diecisiete operaciones.

reservas.horarios centraliza jornadas y validacion operativa; cambios, visitas,
creacion y gestion ya no importan esa regla desde una vista. reservas.adjuntos
centraliza limites, extensiones y tamano de archivos tecnicos. Seis pruebas nuevas
cubren servicio directo, revisiones, rollback, datos persistidos frescos, alias,
revocacion durante POST y carrera PostgreSQL. Focal ampliado: 252 OK, 137.613 s.
Suite integral: 1345 OK, una omitida, 794.142 s. Ruff/check/migraciones y senales
19/19/19 correctos; catalogos ES/EN intactos con 8810 mensajes mas cabecera. No
hubo cambios de interfaz, rutas, esquema ni datos reales.

Siguiente: inventariar y cerrar primitivas, tareas, admin y cargadores de la
capacidad de reservas; extraer resolucion de periodo y constantes de guia que aun
se importan desde reservas.views; despues dividir crear_reserva. M02.4/M02.2
siguen parciales; M01 institucional y M11 permanecen pendientes.

## 57. Continuacion 176: contratos de periodo y guia

`reservas.periodos.resolver_periodo_reserva` es la frontera publica para PAO,
version y semana. Creacion, cronograma y visitas ya no importan esa regla desde
`reservas.views`. `reservas.guia_contrato` concentra los campos y obligatorios
de la guia integrada; creacion y vista previa PDF consumen el mismo contrato.

Una prueba AST impide nuevas importaciones de `reservas.views` desde el negocio
de unidades, con excepcion de la fachada de endpoints en `reservas/__init__.py`.
La busqueda global no encuentra el nombre privado anterior. El commit de codigo
`9729ea1d` reduce views.py de 3087 a 3020 lineas y eleva el paquete de 37 a 39
modulos. No hubo cambios de rutas, modelos, esquema, datos reales o interfaz.

Dos lotes focales, 31 y 23 pruebas, correctos. Suite integral: 1346 pruebas OK,
una omitida, 978.032 s. Ruff, check, migraciones en seco, diff y senales
19/19/19 correctos; catalogos ES/EN intactos. No se renueva certificacion
responsive porque no cambiaron HTML, CSS ni JavaScript.

Siguiente: inventariar primitivas, tareas, admin y cargadores de reservas;
despues dividir `crear_reserva` por etapas y casos de uso. M02.4/M02.2 siguen
parciales; M01 institucional y M11 permanecen pendientes. Publicar
`reestructura-modular` y conservar `integracion-version2-funciones`.

## 58. Continuacion 177: expediente de reservas protegido en Admin

`ProgramacionReservaAdmin` y `RegistroParticipanteReservaAdmin` se incorporaron
al contrato `_ExpedienteSoloLecturaAdmin`. Django Admin ya no permite crear,
editar ni borrar cronogramas, asistencia o participantes por fuera de los casos
de uso de reservas. Reserva, revisiones y solicitudes de cambio ya tenian esa
proteccion; catalogos y guias conservan su administracion editorial propia.

Una prueba nueva verifica todos los campos concretos, altas y eliminaciones en
ambas superficies. Directo: 15 OK. Focal con administracion, reportes, FT02 y
programacion: 44 OK, 55.286 s. Suite integral: 1347 OK, una omitida, 988.174 s.
Ruff, Django check, migraciones en seco, diff y senales 19/19/19 correctos. No
hubo cambios de interfaz, rutas, modelos, esquema ni datos reales. Codigo:
`5dbc2d14`.

Siguiente: cerrar tareas automaticas de reservas con alcance por unidad,
suspension, idempotencia y recuperacion; revisar despues comandos y cargadores;
y dividir finalmente `crear_reserva`. M00 esta implementado; M02.1 avanzado y
M02.2/M02.4 parciales. M01 institucional, M02.3 y M03-M13 siguen pendientes
segun la auditoria vigente. Publicar `reestructura-modular` y conservar
`integracion-version2-funciones`.

## 59. Continuacion 178: ciclo automatico acotado por unidad

El proceso periodico admite `unidad` y el comando `--unidad <slug>`. El filtro
se aplica a vencimientos, recordatorios, cierres, responsables, riesgos,
reintentos SMTP y avisos de guias; un slug inexistente se rechaza antes de
mutar. Omitirlo conserva la ejecucion institucional existente y `--simular`
continua sin correo y con rollback.

`_reclamar_intento_email` bloquea la notificacion y registra un solo intento
antes de salir a SMTP. Un segundo ejecutor no entrega el mismo aviso durante el
intervalo; un fallo conserva la recuperacion posterior. Cuatro pruebas nuevas:
directo 18 OK, focal 52 OK en 71.158 s y suite integral 1351 OK, una omitida,
953.429 s. Ruff, check, migraciones, diff y senales 19/19/19 correctos. Sin
cambios de interfaz, rutas, modelos, esquema o datos reales. Codigo `993d296f`.

Siguiente: comandos y cargadores de reservas, primero revisiones iniciales y
FT02; despues dividir `crear_reserva`. La suspension se integrara solo cuando la
capacidad completa tenga protegidas todas sus superficies. M02.2/M02.4 siguen
parciales; M01 institucional, M02.3 y M03-M13 mantienen el alcance pendiente de
la auditoria vigente.

## 60. Continuacion 179: reconciliaciones historicas por unidad

`inicializar_revisiones_reservas` y `sincronizar_planificaciones_reservas`
delegan ahora en `reservas.mantenimiento`. Ambos exigen `--unidad`, bloquean la
Unidad y sus Reservas, y confirman o revierten el alcance local como una sola
transaccion. Omitir el slug o indicar uno inexistente termina antes de cualquier
escritura. `--simular` conserva conteos, pero no persiste revisiones, FT02 ni
auditoria.

La linea base se detecta mediante `EXISTS`, sin `DISTINCT` incompatible con
`FOR UPDATE`, y repara el numero 1 ausente incluso si el expediente tiene una
revision posterior. FT02 conserva su comportamiento idempotente. Los fallos
tardios de revision o auditoria revierten todo el lote de la unidad.

Ocho pruebas nuevas: directo 18 OK, focal 89 OK y suite integral 1359 OK, una
omitida, 497.398 s. Ruff, check, migraciones, diff y senales 19/19/19 correctos.
Sin cambios de interfaz, rutas, modelos, esquema ni datos reales. Codigo
`cafb643a`.

Siguiente: separar cargadores operativos y demostrativos, acotar cada carga por
unidad y asegurar reintentos/rollback; despues dividir `crear_reserva`. La
suspension integral de la capacidad sigue pendiente hasta cubrir todas las
superficies. M02.2/M02.4 permanecen parciales.

## 61. Continuacion 180: datos demostrativos cerrados

Los dos cargadores FabLab requieren ahora habilitacion local mediante
`SLCID_ALLOW_DEMO_DATA_COMMANDS=True`, un `--unidad` explicito y
`--confirmar-datos-demo`. Produccion fija la habilitacion en False. El slug
implicito fue retirado, por lo que una invocacion accidental termina antes de
consultar o mutar datos.

Cada cargador bloquea la Unidad dentro de su transaccion y ofrece `--simular`
con rollback total. Un fallo al final del cargador base revierte tambien todo lo
creado previamente. Estas herramientas usan codigos y cuentas demo compartidas:
no son migraciones ni semillas institucionales y deben ejecutarse secuencialmente
solo sobre bases desechables.

Cinco pruebas nuevas: directo 6 OK, focal 37 OK y suite integral 1364 OK, una
omitida, 981.657 s. Ruff, check, migraciones, diff y senales 19/19/19 correctos.
Sin cambios de interfaz, rutas, modelos, esquema o datos reales. Codigo
`d7f5c62f`.

Siguiente: dividir `crear_reserva` por etapas y casos de uso. La suspension
integral de reservas se instalara cuando todas sus entradas esten protegidas;
M02.2/M02.4 permanecen parciales.

## 62. Ruta finita de cierre y regreso a las verticales

La reestructuracion general deja de tratar todos los hitos M00-M13 como
prerrequisitos del desarrollo funcional. Quedan tres entregas de codigo:
separar entrada/validacion de `crear_reserva`, extraer su transaccion y completar
el interruptor integral de reservas; una unica auditoria general cierra esta
fase en el bloque 184.

Despues se trabaja sin intercalar redisenios generales: aceptar Laboratorios,
terminar Plantas piloto, construir Centros experimentales, construir
Observatorios y finalmente Centros I+D. Son seis puertas de auditoria futuras
en total contando el cierre arquitectonico, no una auditoria por commit.

La ruta, los criterios de salida, el estado funcional real y el trabajo diferido
estan en `docs/ruta-cierre-reestructuracion-y-verticales.md`. M01 institucional,
M02.3 y M10-M13 conservan su alcance de seguridad, producto y despliegue, pero
no bloquean las funciones de las verticales ni autorizan a mover tablas sin
reversa comprobada.

La revision inicial de Laboratorios quedo en
`docs/aceptacion-laboratorios.md`: suite integral 1.366 OK y una omitida;
Django, Ruff y migraciones limpios. Se detectaron 71 relaciones directas hacia
Unidad/Reserva, 51 con CASCADE. `UnidadAdmin` ya no permite borrar una unidad
ni publica eliminacion masiva; se debe desactivar para conservar expedientes.
Codigo `52ccbe52`; focal 50 OK.
La aceptacion definitiva se ejecuta despues del bloque 184. El proceso Django,
URLConf y base siguen compartidos hasta M10-M11; recuperacion institucional
sigue condicionada por M01.

## 63. Continuacion 181: entrada inicial de creacion de reservas

El primer corte de `crear_reserva` separa la entrada comun, proposito,
intencion, calendario y seleccion de producto/proceso en
`reservas.creacion_entrada`. El nuevo modulo no conoce HTTP, devuelve datos
tipados y conserva aliases, textos de error, horario local y filtros por unidad.
Siete pruebas directas cubren normalizacion, compatibilidad historica, limites
de intencion, terminos, offsets, horas discontinuas y JSON invalido.

La vista bajo de 3.020 a 2.893 lineas y `crear_reserva` de 1.246 a 1.160. El
bloque 181 sigue abierto: faltan seleccion de recursos, espacios, software y
servicios antes de extraer la transaccion en 182. Focal: 124 OK, 55.881 s.
Suite integral: 1.373 OK, una omitida, 661.484 s. Ruff, Django check,
migraciones en seco, compilacion y diff correctos. Sin cambios de interfaz,
rutas, modelos, esquema ni datos reales. Codigo `70fdd8f5`.

Siguiente: completar 181 con la resolucion de recursos y servicios fuera de la
vista; despues ejecutar 182, 183 y la unica auditoria general 184. La aceptacion
definitiva de Laboratorios se mantiene inmediatamente despues de 184.

## 64. Cierre 181: recursos, servicios y preparacion desacoplados

`reservas.creacion_recursos` concentra equipos, espacios, software,
consumibles, servicios y adjuntos con filtros obligatorios por unidad.
`reservas.creacion_servicio` normaliza modalidad, trabajo, fecha, equipo,
insumos y cotizacion antes de persistir. Ninguno construye respuestas HTTP ni
crea reservas. La vista conserva coordinacion, conflictos y la transaccion que
se extraera en 182.

Siete pruebas directas cubren aislamiento de equipos y servicios entre
unidades, consumibles, duplicados, reserva de recursos y restricciones de
modalidad. La prueba de revocacion entre cotizacion y guardado apunta ahora al
nuevo limite y sigue impidiendo crear con una pertenencia retirada.

La vista bajo de 2.893 a 2.145 lineas y `crear_reserva` de 1.160 a 890. Focal:
176 OK, 168.372 s. Suite integral: 1.380 OK, una omitida, 873.797 s. Ruff,
Django check, migraciones, compilacion y diff correctos. Sin cambios de rutas,
interfaz, modelos, esquema ni datos reales. Codigo `41108c9c`.

El bloque 181 queda cerrado. Siguiente: 182, extraer la transaccion completa del
expediente, participantes, recursos, consumibles, programacion, guias, avisos y
rollback; despues 183 y la auditoria unica 184 antes de aceptar Laboratorios.

## 65. Cierre 182: transaccion de creacion desacoplada

`reservas.creacion_transaccion` recibe un comando con los datos ya validados y
es el unico propietario de la escritura de creacion. Dentro de una sola
transaccion crea expediente, sesiones repetidas, participantes, recursos,
consumibles, programacion, guias, adjuntos, solicitud de servicio,
planificaciones, auditoria y aviso. Conserva el orden de bloqueos `Unidad ->
User -> UserProfile` y revalida pertenencia, autorizacion de guias y conflictos
con filas bloqueadas antes de persistir.

La vista construye el comando y adapta el resultado HTTP. Los efectos que
requieren contexto de la peticion se inyectan como callbacks, por lo que el caso
de uso no depende de `HttpRequest`; las siglas institucionales tambien llegan
como entrada y el dominio no importa la capa de presentacion. Una prueba directa
confirma la creacion con revision inicial y otra provoca un fallo al final del
aviso para demostrar rollback total.

`reservas/views.py` bajo de 2.145 a 1.809 lineas y `crear_reserva` de 890 a 573.
Dentro de esa funcion quedan cero `objects.create`, cero `transaction.atomic` y
cero `select_for_update`. Focal: 178 OK, 201.754 s. Suite integral definitiva:
1.382 OK, una omitida, 980.383 s. Ruff, Django check y migraciones en seco
correctos. Sin cambios de rutas, interfaz, modelos, esquema ni datos reales.
Codigo `90fa0215`.

El bloque 182 queda cerrado. Siguiente: 183, completar el interruptor de la
capacidad de reservas en entradas nuevas, tareas, comandos y exportaciones;
despues ejecutar la unica auditoria general 184 y la aceptacion de Laboratorios.

## 66. Cierre 183: suspension integral y recuperable de reservas

`legado_webcitt.reservas_operativas` es la autoridad unica para las operaciones
que modifican reservas mientras su propiedad siga en el legado compartido. La
misma compuerta cubre creacion, aprobacion, decisiones, cambios, correccion,
inicio, finalizacion, cancelacion, visitas, ingreso, validacion de practicas,
comprobantes de pago, reconciliaciones y cargadores demostrativos. La vista de
creacion traduce la suspension a 403 sin confundirla con un permiso propio del
caso de uso.

El ciclo periodico suspendido devuelve contadores en cero y conserva sus
pendientes; al reactivar procesa el trabajo recuperable. El diagnostico de
codigos, las consultas, el historial y los comprobantes PDF siguen disponibles,
mientras las reparaciones y comandos de escritura terminan de forma explicita.
El admin institucional gestiona Inicio y reservas por separado, con el mismo
CAS, permiso especifico, motivo e historial inmutable.

PostgreSQL usa un advisory lock compartido para cada operacion y uno exclusivo
para suspender o reactivar. Esto coordina el cambio institucional sin serializar
reservas independientes. El fallback de otros motores conserva el bloqueo de
fila. Las carreras existentes detectaron y obligaron a corregir una primera
version que serializaba todos los escritores.

Pruebas focales de reservas: 204 OK. Manifiestos y superficies: 27 OK. Suite
integral: 1.392 OK, una omitida, 501,783 s. Ruff, Django check, migraciones en
seco, catalogos ES/EN compilados y diff correctos. No cambia modelos, migraciones,
rutas publicas o datos reales. Codigo `7edae539`.

El bloque 183 queda cerrado. Siguiente y unico paso de esta fase: bloque 184,
auditoria final de estabilizacion; despues se ejecuta la aceptacion definitiva
de Laboratorios y se vuelve al desarrollo funcional de Plantas piloto.

## 67. Cierre 184 y aceptacion definitiva de Laboratorios

La estabilizacion arquitectonica queda cerrada. La auditoria estricta mantiene
19 contratos, 19 decoradores y 19 conexiones propias sin hallazgos. El inventario
registra 11 modulos, 104 rutas heredadas, 96 modelos heredados, 12 propios, 67
administradores, 23 comandos y 11 scripts. Django check, migraciones en seco y
Ruff permanecen correctos. El perfil de produccion falla cerrado en el entorno
local porque no se proporciona una clave de despliegue fuerte, que es el
comportamiento esperado.

La certificacion responsive se renovo sobre Chrome headless aislado: 182
combinaciones publicas, 574 autenticadas con cuatro roles y 14 del visor PDF.
Las 770 combinaciones cubren ES/EN y anchos 360, 390, 768, 1024, 1200, 1366 y
1920 px, sin desbordamientos ni errores JavaScript. El PDF es valido, permanece
en la misma pestana y cierra con Escape. La base y las sesiones QA temporales se
retiraron sin alterar la base activa.

Laboratorios queda aceptado funcionalmente. Ademas de la suite integral vigente
de 1.392 pruebas correctas y una omitida, se ejecutaron 277 pruebas enfocadas en
catalogo institucional, unidades, gestion, reservas e interruptor, practicas,
documentos, servicios, seguridad y administracion; todas correctas en 86,159 s.
No se detectaron defectos que requieran codigo, modelos, migraciones, rutas o
datos reales.

Los limites se conservan explicitamente: M01 institucional debe demostrar
respaldo coordinado, copia externa inmutable y RPO/RTO; M10-M11 deben separar
propiedad de tablas, procesos, credenciales y colas; CSP aun admite
`unsafe-inline`; no hay CI versionado; y Django, URLConf y PostgreSQL siguen
siendo dominios de fallo compartidos. La aceptacion no afirma aislamiento
fisico ni recuperacion institucional.

Siguiente: volver al desarrollo funcional de Plantas piloto. El primer bloque
es planificacion completa: demanda estimada, plan de ventas y plan agregado
sobre el Plan Maestro existente. Despues siguen completitud administrable,
repositorio trazable y una sola aceptacion de Plantas piloto.

## 68. Planificacion completa de Plantas Piloto

`PlanVentas` y `LineaPlanVentas` agregan la decision previa al Plan Maestro.
Cada linea conserva historico promedio de tres periodos, pronostico,
compromisos, docencia y ajuste manual. El total nunca es negativo. La
aprobacion exige un Plan Maestro en borrador de la misma planta que cubra todo
el horizonte; la incorporacion es idempotente y solo crea corridas por demanda
abierta, mientras encargos y practicas entran por sus Reservas para no
duplicarse.

El plan agregado consolida periodo, familia y unidad base calculada desde la
receta existente. No crea recetas, no mueve inventario y no genera ordenes por
si mismo. El panel de gestion y la hoja imprimible presentan demanda, agregado,
programa, capacidad, materiales y pedidos en una sola secuencia. El horizonte
no puede cambiar mientras conserve lineas calculadas.

Las reglas puras de periodos, ventanas historicas, promedio, total y equivalencia
pertenecen a `apps.plantas_piloto.domain.planificacion`; los modelos siguen en
`webcitt` hasta M10 para conservar tablas, permisos, auditoria y reversa. El
manifiesto 1.1 declara `planificacion_demanda`. Migracion 0202. Catalogos ES/EN:
8.879 mensajes por idioma.

Validacion: 30 pruebas directas; 231 pruebas enfocadas en las cinco plantas,
una omitida; suite integral 1.402 OK, una omitida, 656,102 s. Django check,
migraciones en seco, Ruff, compilacion y diff correctos. Senales 19/19/19 sin
hallazgos; inventario: 11 modulos, 104 rutas heredadas, 98 modelos heredados,
12 propios, 67 administradores, 23 comandos y 11 scripts. Codigo `214528b4`.

Siguiente: completitud administrable por planta, pestana, familia y ficha,
protegiendo las decisiones editoriales frente a recargas. Luego repositorio
trazable y una sola aceptacion funcional de Plantas Piloto.

## 69. Completitud administrable de Plantas Piloto

El tablero de completitud ya cubre planta, las seis pestanas, las 33 secciones,
las familias y cada ficha. Usa aprobado, parcial, pendiente y bloqueado sin
confundir que un contenido este publicado con que haya sido validado. Los
bloqueos tecnicos indican que calculos, diagramas o protocolos todavia carecen
de datos institucionales suficientes.

El gobierno de `FichaContenido` conserva estado de validacion, observacion,
responsable y fecha, junto con la autoria y fecha de cada decision editorial
manual. El admin esta acotado a las unidades gestionables y dispone de acciones
de revision, validacion y bloqueo. El cargador institucional fue probado dos
veces sobre la misma planta y no altera esas decisiones; una desactivacion del
origen aun archiva la ficha para evitar contenido huerfano.

Reglas puras en `apps.plantas_piloto.domain.completitud`, manifiesto Plantas
1.2.0 con `gobierno_completitud`, migracion 0203 y catalogos ES/EN con 8.888
mensajes. Pruebas enfocadas: 140 OK. Suite integral: 1.407 OK, una omitida,
518,148 s. Django, migraciones, Ruff, idiomas, diff y senales 19/19/19 correctos.

Faltan dos entregas para cerrar Plantas Piloto: repositorio trazable y una sola
aceptacion funcional de las cinco plantas. Luego se inicia Centros
Experimentales; despues Observatorios y Centros I+D.

## 70. Repositorio trazable de Plantas Piloto

Artefactos externos y adjuntos ya tienen un gobierno comprobable. Para publicar
un artefacto se exige fuente, licencia, version, responsable, fecha de
validacion, vigencia y evidencia. Los vencidos, programados o marcados por un
cambio de fuente no aparecen en el repositorio, la ficha de proceso ni la
exportacion publica.

Una importacion de resultados conserva la alerta de desactualizacion. Solo la
accion administrativa de confirmar sincronizacion la resuelve y deja usuario y
fecha. Los resultados son internos para gestores; los tres administradores del
repositorio estan acotados por unidad y los archivos conservan descarga
controlada, huella y revision de seguridad.

Reglas puras en `apps.plantas_piloto.domain.repositorio`, manifiesto Plantas
1.3.0 con `repositorio_trazable`, migracion 0204 y catalogos ES/EN con 8.896
mensajes. Cobertura conjunta: 169 OK. Suite integral: 1.412 OK, una omitida,
506,677 s. Django, migraciones, Ruff, idiomas y diff correctos.

Falta una sola entrega para terminar Plantas Piloto: la aceptacion funcional de
las cinco plantas, perfiles, ES/EN, responsive, permisos, reservas, produccion,
calidad, inventario, planificacion y reportes. Despues comienza el dominio de
Centros Experimentales.

## 71. Aceptacion funcional de Plantas Piloto

Plantas Piloto queda cerrada funcionalmente para Lacteos, Carnicos,
Hortofruticola, Almidones y derivados, y Panificacion. La puerta enfocada
termino con 275 pruebas correctas, una omitida, en 223,249 s. La suite integral
termino con 1.412 correctas, una omitida, en 513,720 s. Django, migraciones,
Ruff y senales 19/19/19 permanecen limpios.

La revision visual ejecuto doce combinaciones: las cinco plantas a 360 px en
espanol y 1366 px en ingles, mas Lacteos a 768 px en ambos idiomas. No hubo
desbordamiento global. Se corrigio el recorte de la navegacion de modulos en
movil y se sustituyo el logotipo remoto del visor institucional por el recurso
local responsivo. La base activa no fue modificada.

La evidencia completa esta en `docs/aceptacion-plantas-piloto.md`. Plantas
queda congelada salvo contenido institucional o correcciones criticas. El
siguiente trabajo funcional es Centros Experimentales: especificacion del
dominio de ensayo o campana, ciclos, parcelas o areas, activos biologicos,
tratamientos, protocolos y permisos propios. M01 y M10-M11 siguen declarados y
no bloquean esta continuidad.
## 189. Frontera estructural de Centros Experimentales

Se inició la siguiente vertical sin adelantar funciones de negocio. Las URLs de
catálogo y detalle se conservan, pero `presentation` ya no conoce directamente
el adaptador compartido: delega en
`apps.centros_experimentales.infrastructure.unidades_heredadas`, único puente
temporal hacia el legado. El manifiesto sube a 1.1.0 y declara el contrato
`identidad_unidad_v1` que la entrada pública ya consume.

La estructura, dependencias permitidas, propiedad futura y límites reales de
aislamiento quedaron documentados en `apps/centros_experimentales/README.md`.
No se crearon `domain` o `application` vacíos, modelos, migraciones,
administración, campañas, parcelas, tratamientos o flujos. Esos paquetes se
abrirán con código real después de validar el vocabulario institucional.

Validación enfocada: 26 pruebas correctas sobre estructura, manifiestos, rutas,
catálogos y detalles. Siguiente: terminar la comprobación técnica de este
bloque y luego iniciar la especificación funcional institucional de Centros
Experimentales.

## 190. App y presentación propias de Centros Experimentales

La vertical ya está instalada mediante `CentrosExperimentalesConfig`. Su
experiencia pública exclusiva salió de `webcitt/templates` y ahora pertenece a
`apps/centros_experimentales/templates/centros_experimentales`, sin cambiar el
HTML, la URL ni el contexto que recibe. El manifiesto 1.2.0 declara la app
Django; sigue exponiendo únicamente catálogo y detalle.

El inventario de `README.md` identifica cada pieza heredada y su destino. El
perfil operativo, inline administrativo, controladores, CSS y JavaScript
compartidos permanecen donde están hasta que exista una separación con reversa
o una responsabilidad exclusiva comprobable. No se añadieron funciones,
modelos o migraciones.

Validación proporcional: 51 pruebas correctas; Django check, migraciones en
seco, Ruff y compilación sin hallazgos.

## 191. Frontera estructural de Observatorios

`apps.observatorios` queda instalada como app Django y es propietaria de su
experiencia pública. `presentation` delega catálogo y detalle en un único
adaptador de `infrastructure`; el manifiesto 1.1.0 declara
`identidad_unidad_v1` y solo las dos capacidades existentes.

El README registra los límites, el árbol futuro y el inventario heredado. El
perfil, inline, controladores y recursos compartidos siguen en `webcitt` hasta
una migración con reversa. No se crearon fuentes, indicadores, publicaciones,
solicitudes, modelos o migraciones.

Validación proporcional conjunta: 55 pruebas correctas; Django check,
migraciones en seco, Ruff y compilación sin hallazgos.

## 192. Frontera estructural de Centros I+D

`apps.centros_id` queda instalada como app Django y ya posee la ruta, vista y
plantilla de `/centros-id/`. El manifiesto 1.1.0 sigue declarando únicamente
`portada_publica` y depende solo de `core`; no usa `Unidad`, integraciones ni
otra vertical.

El README documenta el árbol futuro, inventario y límite de aislamiento. No se
crearon centros, líneas, grupos, investigadores, proyectos, resultados,
modelos, administración o migraciones.

Validación proporcional conjunta: 71 pruebas correctas; Django check,
migraciones en seco, Ruff y compilación sin hallazgos.

## 193. Pausa y traspaso a otro asistente

El trabajo se detuvo voluntariamente con la rama limpia en `69142d2b`. Se creó
`TRASPASO-CLAUDE.md` como contexto breve y mensaje listo para pegar. El alcance
inmediato continúa siendo solo estructural: uniformar Laboratorios y Plantas
Piloto con el patrón de apps instaladas y plantillas propias, sin modificar sus
funciones aceptadas. Después se realizará una única validación integral antes
de retomar las funciones de las verticales pendientes.

## 194. Frontera estructural de Laboratorios

`apps.laboratorios` queda instalada como app Django mediante
`LaboratoriosConfig` y es propietaria de su experiencia pública exclusiva. La
plantilla salió de `webcitt/templates/portal/pages/unidades/experiencias` sin
cambiar un byte de HTML, y el include del catálogo apunta al paquete
propietario. `presentation` delega catálogo y detalle en un único adaptador de
`infrastructure`; el manifiesto sube a 1.1.0, declara la app Django y el
contrato `identidad_unidad_v1` que la entrada pública ya consume.

Este bloque no reabre la aceptación funcional. Reservas, equipos, prácticas,
documentos, servicios, reportes, modelos, migraciones, administración y
permisos siguen en `webcitt`; su traslado pertenece a M10 y exige una reversa
comprobada. El README registra el inventario heredado, la estructura prevista y
el límite real de aislamiento.

Validación proporcional: 63 pruebas correctas sobre estructura de las cuatro
apps instaladas, manifiestos, rutas modulares y unidades. Django check,
migraciones en seco, Ruff y compilación sin hallazgos.

## 195. Frontera estructural de Plantas Piloto

`apps.plantas_piloto` queda instalada como app Django mediante
`PlantasPilotoConfig` y es propietaria de su experiencia pública exclusiva. La
plantilla salió de `webcitt/templates/portal/pages/unidades/experiencias` sin
cambiar un byte de HTML; esa carpeta queda vacía y se retira, porque las cuatro
experiencias ya pertenecen a sus verticales. `presentation` delega catálogo y
detalle en un único adaptador de `infrastructure`.

El manifiesto sube a 1.4.0: declara la app Django y el contrato
`identidad_unidad_v1`, y conserva íntegras las cinco capacidades aceptadas
—catálogo, detalle, planificación de demanda, gobierno de completitud y
repositorio trazable—. `domain/planificacion.py`, `domain/completitud.py` y
`domain/repositorio.py` no se tocaron: siguen siendo las reglas reales y
probadas de la vertical.

Este bloque no reabre la aceptación de las cinco plantas. Perfil, procesos,
recetas, órdenes, lotes, calidad, inventario, Plan Maestro, persistencia de
completitud y repositorio, inline administrativo y recursos compartidos
permanecen en `webcitt`; el README los inventaría uno por uno con su destino
en M10.

Con este bloque las cinco verticales son consistentes: app instalada,
plantilla propia, puente heredado aislado y manifiesto que declara app y
contrato. La prueba de manifiestos ya exige `app_django` a las cuatro
verticales de unidad sin excepciones.

Validación proporcional: 77 pruebas correctas sobre estructura de las cinco
apps, manifiestos, rutas modulares y unidades. Django check, migraciones en
seco y Ruff sin hallazgos.

## 196. Cierre de la uniformidad estructural

Las cinco verticales quedan consistentes: cada una es una app Django instalada,
propietaria de su plantilla pública exclusiva, con su manifiesto declarando la
app y —en los cuatro tipos de unidad— el contrato `identidad_unidad_v1`, y con
el acceso al legado concentrado en un único adaptador de `infrastructure`.
Centros I+D no necesita ese adaptador porque su portada no consulta el legado.

La primera suite integral posterior a los traslados descubrió un defecto
heredado del bloque 192: `webcitt/tests/test_portal.py` seguía exigiendo
`portal/pages/centros_id/centros_id.html`, plantilla que ese bloque había
trasladado a `apps/centros_id`. La corrida enfocada de entonces no incluía
`test_portal`, de modo que el fallo pasó inadvertido. La aserción se corrigió
aquí y la carpeta vacía del legado se retiró, igual que la de experiencias.

El bloque no movió modelos, tablas, `ContentTypes`, permisos ni administración
heredada, y no añadió funciones. Las aceptaciones de Laboratorios y Plantas
Piloto siguen vigentes sin reabrirse.

Validación integral única del cierre: 1.433 pruebas correctas y una omitida
en 804,103 segundos; Django check, migraciones en seco, `auditar_modulos`,
Ruff y compilación sin hallazgos.

Siguiente trabajo, cuando el usuario lo indique: especificación funcional
institucional de Centros Experimentales, después Observatorios y finalmente
Centros I+D. M10 y M11 siguen abiertos y no bloquean ese desarrollo.

## 197. Auditoria de categorias administrables (M02.3)

Primer bloque de M02.3. El hito exige auditar `Categoria` y `TipoLaboratorio`
antes de implementar, para no crear un catalogo duplicado. La auditoria esta en
`docs/categorias-administrables.md` y deja cinco hallazgos.

Los dos modelos son identicos —`nombre` unico y `descripcion`— y ninguno esta
acotado a su modulo: el administrador permite asociar un tipo de laboratorio a
un observatorio. El catalogo publico filtra por nombre, no por identificador
estable, asi que renombrar rompe enlaces publicados. Falta ordenar, ocultar y
archivar; hoy la unica forma de retirar una categoria es eliminarla, y eso borra
en silencio la clasificacion historica de cada unidad. Las etiquetas publicas
tampoco coinciden con los nombres del codigo: `Categoria` se muestra como
"Subarea" y `TipoLaboratorio` como "Modo de operacion", que es ademas el nombre
de otro campo distinto de `Unidad`.

El quinto hallazgo se corrigio en este bloque. `Unidad.clean` comprobaba el
maximo de seis categorias con `self.categorias.count()`, que solo alcanza la
relacion ya guardada: al crear no hay clave primaria y al editar contaba la
seleccion anterior. Se reprodujo con el propio formulario del admin, que acepto
y guardo ocho. La regla vive ahora en `Unidad.MAXIMO_CATEGORIAS` y la aplica
`UnidadAdminForm.clean_categorias`. Se retiro tambien un `get_form` que no
personalizaba nada. Sin cambio de esquema.

Validacion proporcional: 62 pruebas correctas sobre admin, unidades y las dos
verticales aceptadas; Django check, migraciones en seco y Ruff sin hallazgos.

Siguiente: las seis capacidades pendientes de M02.3 —identificador estable,
orden, ocultar, archivar, referencias protegidas y alcance por modulo— exigen
migracion sobre el paquete heredado y dependen de cinco decisiones
institucionales todavia abiertas.

## 198. Higiene del repositorio y consolidacion documental

Bloque sin cambio de esquema. Siete docstrings de `config/` y `webcitt/` aun
nombraban "Plataforma Cientifica UPEC"; ahora nombran al SLCID. Las siete
imagenes de los pilares de Quienes somos se servian con rutas fijas a `/media/`,
que no se versiona en despliegue; se copiaron a `webcitt/static/img/pilares/` y
la plantilla usa `{% static %}`. Se dejo de rastrear `media/` (18 archivos,
entre ellos cinco HTML subidos por usuarios) y se retiro un PDF estatico sin
referencias con comillas y acentos en el nombre.

`TRASPASO-CLAUDE.md` pasa a `TRASPASO.md` como unico punto de entrada; este
archivo y `CODEX_CONTEXT.md` viven ahora en `docs/historial/` como registros
acumulativos. README enlaza ambos. La auditoria de arquitectura recibe una
seccion de actualizacion con las cifras medidas sobre `cdbb0a62`, y la ruta de
ejecucion declara que, en el orden funcional de las verticales, manda la ruta
de cierre.

Validacion proporcional: 45 pruebas de portal, idiomas y unidades; Ruff,
Django check y resolucion de estaticos correctos.

## 199. Tipologias de unidad administrables (M02.3)

La lista fija de cuatro tipos de unidad pasa a ser un catalogo institucional
administrable en `apps.configuracion_institucional.tipologias`, consumido por
el legado a traves del adaptador `apps.core.presentation.tipologias`, con el
mismo patron de proveedor que niveles y catalogos. `Unidad.dependencia` sigue
guardando el codigo y solo pierde sus `choices`; la validacion y las etiquetas
salen del catalogo. Migraciones: `configuracion_institucional.0008` (modelo y
semilla idempotente de las cuatro implementadas) y `webcitt.0205` (AlterField
sin datos). Respaldo previo en `backups/tipologias_pre199_*`.

Desde el admin se crea una tipologia nueva que reutiliza una base operativa
—catalogo, detalle, modulos y reserva de esa base— y se desactiva cualquiera,
incluidas las cuatro implementadas. La desactivacion se aplica en el servidor:
catalogo historico y detalle responden 404, la pestana desaparece y el admin
deja de ofrecerla a unidades nuevas; reactivar restituye todo. Las tipologias
sin app propia se sirven en `unidades/<codigo>/` desde `directorio_unidades`,
que redirige las implementadas a sus rutas historicas. El proveedor superpone
sus filas a las implementadas y falla cerrado a ellas.

Las pestanas del catalogo, el icono y el nombre de tipo en tarjetas y detalle
se generan desde el catalogo con nombres ES/EN por fila. `Unidad.codigo_base`
alimenta clasificacion, modo de operacion, modulos predeterminados, modulo de
reserva, detalle y catalogo. Catorce mensajes nuevos en ES/EN, compilados.
Decisiones, aplicacion y limites en `docs/tipologias-administrables.md`.

Validacion proporcional: 145 pruebas correctas (tipologias, capacidades,
unidades, admin, rutas, manifiestos, idiomas, portal y las cinco verticales);
Django check, migraciones en seco, Ruff y catalogos de idioma correctos.

## 200. Clasificaciones administrables (cierre de M02.3)

`Categoria` y `TipoLaboratorio` comparten ahora la base abstracta
`ClasificacionInstitucional`: codigo estable generado del nombre y fijo,
orden, archivado (`activa`), alcance por tipologia (`tipologias`, codigos del
catalogo institucional; vacio es todas) y eliminacion protegida cuando hay
unidades que la usan. Migracion `webcitt.0206`: agrega campos, asigna codigos
a las filas existentes y los vuelve unicos; sin datos perdidos ni tablas
movidas. Aplicada a la base de desarrollo tras el respaldo `tipologias_pre199`.

Vocabulario fijado: `Categoria` es "Subarea" y `TipoLaboratorio` es "Modo de
uso", lo que elimina la colision con el "Modo de operacion" de plantas. El
catalogo publico filtra por codigo, acepta el nombre historico en enlaces ya
publicados y solo ofrece clasificaciones activas, aplicables a la tipologia y
en uso en ella. El formulario de unidad ofrece solo activas mas las asignadas
y rechaza las que no se ofrezcan para la tipologia elegida. Admin compartido
con tipologias como casillas, codigo de solo lectura, conteo de unidades y
eliminacion permitida solo sin unidades. Ocho mensajes ES/EN nuevos.

Con esto M02.3 queda cerrado: tipologias y clasificaciones administrables,
con decisiones registradas en `docs/categorias-administrables.md`.

Validacion proporcional: 131 pruebas correctas; Django check, migraciones en
seco, Ruff y catalogos de idioma correctos.

## 201. Cierre integral de la sesion

Suite integral posterior a los bloques 198-200: 1.449 pruebas, con tres
fallos del auditor de contratos de senales porque `models/core.py` y
`models/recursos.py` cambiaron. Revision realizada: los cuatro receivers de
esos archivos no cambiaron; `create_default_modules` resuelve por base
operativa, identico para los codigos existentes. Huellas actualizadas y los
19 contratos del auditor en verde. Humo de solo lectura contra la base de
desarrollo: cuatro tipologias sembradas, 14 subareas y 4 modos de uso con
codigo, pestanas dinamicas, ruta generica con redireccion y 404.

Estado del plan: M02.3 cerrado; auditoria, estado del plan y ruta de
ejecucion actualizados. Siguiente bloque funcional: Centros Experimentales,
cuando la institucion entregue su especificacion.

## 202. Revision integral: huerfanos, nombres, duplicados y seguridad

Barridos automaticos sobre los archivos rastreados: sin duplicados por
contenido salvo `__init__.py` vacios; sin modulos Python, plantillas ni
estaticos propios sin referencia (los `account/*.html` los resuelve allauth y
los comandos y templatetags se descubren solos); sin secretos ni claves
privadas; `.env` fuera de Git. Se retiro el `demo.html` del paquete de iconos,
una carpeta vacia de plantillas y se renombro `inventario_estilos.md` a la
convencion con guiones. Los pares de documentos "institucional/administrable"
de catalogo, calendario y niveles describen dos etapas de la misma funcion y
se conservan enlazados.

El nombre viejo sobrevivia en `pyproject.toml` (`plataforma-cientifica-upec`,
descripcion "de la UPEC"); ahora el proyecto se llama `slcid` con descripcion
neutral y `uv.lock` regenerado. `requirements.txt` listaba solo dependencias
directas y `ruff` viajaba a produccion: ahora se genera desde `uv.lock` con
todas las transitivas fijadas y con hashes, `ruff` esta en el grupo `dev`, y
la imagen instala con `--require-hashes`. `pip-audit` sin vulnerabilidades.

Seguridad y respaldos: `check --deploy` con `settings_production` y un entorno
completo de prueba no reporta incidencias; los fallos cerrados existentes
(clave, hosts, correo, aislamiento de base) se comprobaron. Se agrego un
usuario de sistema sin privilegios en la imagen, permisos 640/750 para los
adjuntos y un registro explicito de seguridad y errores a la salida estandar.
El ciclo de respaldo restaura ahora cada copia de base en una base temporal
antes de darla por valida (`BACKUP_VERIFY_RESTORE`). Documentacion de
despliegue, seguridad y README actualizadas.

## 203. Raiz limpia: todo lo de ejecucion bajo var/

La raiz mezclaba codigo con directorios de ejecucion ignorados por Git
(`media`, `backups`, `output`, `tmp`, `static_deployed`, `private`) y restos
locales (`.agents` vacio, `.uv-cache`, un entorno virtual de 220 MB en
`tmp/security-venv` y un servidor de desarrollo del 18 de septiembre que
seguia corriendo con codigo viejo y bloqueaba su registro). Ahora
`settings.VAR_DIR = BASE_DIR / "var"` agrupa `media/`, `static/` (salida de
collectstatic), `cache/matplotlib`, `logs/`, `output/`, `backups/`, `tmp/` y
`private/institutional-brand/`; `.gitignore` ignora `/var/` completo y
`.dockerignore` lo excluye de la imagen. Docker monta los volumenes bajo
`/app/var`, el usuario `slcid` solo posee ese arbol y `BACKUP_HOST_DIR` cae a
`./var/backups`.

La carpeta raiz `static/` con dos logotipos no la usaba ningun codigo: los PDF
resuelven el logo por `finders` desde `webcitt/static/img`. Se retiro. Los
datos de desarrollo se movieron en disco (8 imagenes de unidad presentes bajo
`var/media`, respaldos conservados en `var/backups`). Documentacion de
arquitectura, estructura objetivo, logos, despliegue y README actualizadas.

Validacion: Ruff, Django check, collectstatic (1.559 archivos a `var/static`),
55 pruebas de imagenes, previsualizacion, identidad, reportes, portal e
idiomas, `check --deploy` de produccion sin incidencias e imagen Docker
construida con el nuevo arbol.

## 204. Colores institucionales, cabecera y sesion

Diagnostico con capturas reales (Chrome sin interfaz) del sitio servido. La
causa principal era la derivacion de la paleta: `acento_sobre_oscuro` pasaba a
blanco cuando el acento no alcanzaba 4,5:1 sobre el primario (el dorado
#f2bd3f sobre el verde #006633 da 4,1:1), con lo que todas las cejas y acentos
"sobre oscuro" perdian la marca. Ahora el acento se aclara en pasos hasta ser
legible sobre el oscuro y el primario (#f5ca65 para UPEC) y solo cae a blanco
si ninguna variante lo consigue. Ademas `acciones_superficies.css` forzaba
`#fff !important` sobre cejas y acentos del heroe; se retiro esa regla y se
conservo blanco solo en etiquetas sobre foto sin veladura.

Se corrigieron usos de la tinta oscura del acento sobre fondos oscuros o sobre
el primario: etiquetas del explorador de Quienes somos (un solo color
institucional en lugar de cian/lima), cejas de heroe, pilares, instancias,
directorio, banda de historia y conexion en Quienes somos, tarjeta verde de
Centros I+D (ceja dorada y titulo blanco), kickers de las experiencias sobre
pantalla oscura y la ceja del centro de administracion.

Cabecera: se retiro el bloque que comprimia el menu a partir de 1280 px
(saltos de linea y separaciones minimas) y vuelven las separaciones
originales; la marca muestra el nombre completo del producto en dos lineas.
La sesion pasa a la barra superior verde con usuario, nombre completo y
"Cerrar sesion"; el acceso "Iniciar sesion" tambien vive alli. La barra de
titulo queda para la marca, la navegacion y las notificaciones. Prueba de
cierre de sesion actualizada al nuevo contrato.

Validacion: 129 pruebas de portal, idiomas, usuarios, presentacion y paleta;
71 de superficies, portal, idiomas, usuarios y paleta tras los ajustes finales;
Ruff limpio; capturas de Inicio, catalogo, Centros I+D y Quienes somos con el
dorado institucional restituido y la cabecera con aire.

## 205. Ajuste de la barra superior

Correcciones sobre el bloque anterior: redes sociales y Contacto vuelven a
mostrarse tambien con sesion iniciada (antes los sustituia el bloque de
sesion), el nombre aparece una sola vez —el completo si existe, si no el
usuario— y la sesion cierra la barra por la derecha, separada de contacto,
redes e idiomas por un filete. Sin sesion, ese mismo lugar ofrece "Iniciar
sesion". Verificado con la barra renderizada en ambos estados; 49 pruebas de
usuarios, portal e idiomas correctas y Ruff limpio.

## 206. Presentacion institucional manejable

El editor permitia crear revisiones pero publicar estaba escondido dentro de la
ficha de cada revision, de modo que desde el listado parecia que no se podia
activar nada. Ahora cada fila ofrece "Revisar y publicar" —o "Restaurar esta
presentacion" si ya estuvo publicada— y "Crear revision desde estos datos", y el
listado explica la ruta en tres pasos y por que no hay eliminar ni desactivar:
activar es publicar, solo una esta En uso y el historial es el registro de lo
publicado. No se cambio el modelo de inmutabilidad ni la confirmacion POST.

El formulario pasa de una lista plana de veinte campos a cuatro bloques con
descripcion: identidad y contactos, logotipos, logotipos de respaldo instalados
(plegado, avanzado) y colores/tipografia. Cada logotipo declara donde se usa y
se confirmo que son los mismos archivos para el portal y para los PDF:
comprobantes y guias usan la variante clara, reportes y maquetas la oscura, y el
reporte de reservas imprime ademas la segunda marca. La paleta agrupa sus
controles en colores base, lineas, veladura sobre fotografias, tipografia y
degradados, cada grupo con una linea que dice a que aplica.

Migracion `0009_ayudas_presentacion`: solo etiquetas y textos de ayuda.
Documentacion nueva para quien administra en
`docs/guia-presentacion-institucional.md`, enlazada desde README y desde los
documentos tecnicos de presentacion y logos. Treinta mensajes ES/EN nuevos.

Validacion: 173 pruebas de configuracion institucional, idiomas y admin; Ruff,
Django check y migraciones en seco limpios; listado y formulario revisados en
capturas reales.

## 207. Editor de paleta interactivo

Los acabados se ajustaban escribiendo numeros y codigos HEX en cajas de texto,
sabiendo de memoria los rangos y el valor que asume el sistema cuando el campo
queda vacio. Ahora cada control es interactivo sobre el mismo campo del
formulario, de modo que el contrato del servidor no cambia y vacio sigue
significando automatico:

- medidas con deslizador, lectura del valor y "Automatico (2px)" cuando no hay
  valor propio;
- colores de estilo con selector y la lectura del color que heredan;
- degradados con deslizador de angulo y dos selectores de color, conservando el
  campo de texto para pegar un valor externo de hasta cinco paradas; si se pega
  algo que el generador no puede representar se respeta tal cual y un boton
  devuelve el mando al generador;
- boton "Volver a automatico" visible solo cuando hay un valor propio.

La vista previa ya existente reacciona a cada cambio. Se corrigio ademas que
Grappelli forzaba `display` en los botones y anulaba el atributo `hidden`.

Validacion: sintaxis JS, Ruff, Django check y 154 pruebas de configuracion
institucional e idiomas; editor revisado en capturas reales.

## 208. Alcance del degradado, vista previa lateral y botones controlables

Tres correcciones sobre el editor de acabados.

El degradado "no funcionaba" en los botones porque `paleta_componentes.css`
forzaba `background-image: none` en las acciones: el degradado solo llegaba a
la banda superior y a la marca del admin. Se agrega la opcion
`degradado_alcance` (bandas | botones | ambos, predeterminado bandas) al
contrato de estilos, con validacion propia y dos variables derivadas,
`--institucion-degradado-bandas` y `--institucion-degradado-botones`. Elegir
uno u otro no cambia el degradado guardado, solo donde se aplica.

La vista previa deja de estar al final: el editor pasa a dos columnas y la
muestra queda fija a la derecha desde 1100 px, apilandose en pantallas
estrechas. La muestra tambien refleja el alcance elegido.

Inventario de botones: el sistema tiene familias heredadas —upec-button,
home-btn, guide-btn, unit-console__row-action, Bootstrap y las del asistente de
reservas— que no se renombran para no tocar pantallas aceptadas. Se completo su
cobertura en los tres papeles institucionales (principal, destacada,
secundaria), de modo que ya no quedan botones ajenos a la paleta; antes
`upec-button--primary/secondary/outline`, `guide-btn--primary/gold/outline`,
`btn-primary-custom`, `btn-outline-custom`, `home-btn.secondary` y
`unit-console__row-action` no obedecian la paleta publicada.

Validacion: 156 pruebas de configuracion institucional e idiomas, con tres
casos nuevos de alcance; 15 de superficies y portal; Ruff, Django check y
migraciones en seco limpios.

## 209. La vista previa deja de congelarse y el editor se simplifica

Defecto real: `actualizar()` abortaba con `throw` ante el primer problema, de
modo que al elegir colores sin contraste suficiente la vista previa quedaba
congelada en el ultimo estado valido. El usuario cambiaba cuatro colores y solo
veia el primero. Ahora la funcion no interrumpe: cada campo invalido cae a su
color predeterminado, los problemas se acumulan como avisos junto a la muestra
y el dibujo se completa siempre. El servidor sigue rechazando la publicacion de
una combinacion ilegible; lo que cambia es que previsualizar ya no depende de
que todo este bien.

Simplificacion: al abrir solo se ven los colores base y el degradado principal.
Lineas, veladura, tipografia y alcance quedan plegados en "Acabados finos". Se
retiraron los dos parrafos largos de ayuda —incluida la lista de variables CSS,
que es material de desarrollo— y quedo una sola linea; el detalle vive en la
guia del administrador.

Validacion: 156 pruebas de configuracion institucional e idiomas, sintaxis JS,
Ruff y Django check; comprobado en el navegador con los cuatro colores del caso
reportado, que ahora se reflejan junto al aviso de contraste.

## 210. El degradado se previsualiza y el visualizador cubre la marca

El degradado seguia sin verse: `degradado()` lanzaba al no alcanzar 4,5:1 con
blanco y acento, y la muestra caia al color plano. Ese contraste pasa a ser
aviso durante la previsualizacion —la estructura se sigue validando— de modo
que un degradado como `linear-gradient(205deg, #c84660, #30d5a9)` se dibuja y
el motivo aparece en rojo al lado. Publicar sigue exigiendo el contraste.

Se retiro el acordeon de acabados finos: volvia a estrechar los controles en
una sola columna y escondia justo lo que se queria probar. Todos los grupos
quedan a la vista.

El visualizador pasa de tres piezas a una hoja de marca: franja del degradado
principal, tarjeta con subtitulo, titulo, filete, texto de lectura, texto
secundario y etiquetas, los cuatro tipos de accion —principal, destacada,
secundaria y enlace—, banda oscura con titulo e icono, y fotografia con
veladura. Se agregaron a la muestra los derivados de lectura que ya calcula el
servidor (superficie suave, borde, tinta del primario y acento legible).

Validacion: 156 pruebas de configuracion institucional e idiomas, sintaxis JS,
Ruff y Django check; comprobado en el navegador con el degradado del caso
reportado.

## 211. La hoja de marca cabe en pantalla y el degradado se puede retirar

Tres correcciones comprobadas con el DOM real del editor.

La columna de vista previa no tenia limite de alto: al ser mas alta que la
pantalla, desplazarse por los controles dejaba fuera de vista justo la pieza
que se queria mirar. De ahi venian dos quejas distintas —"las ultimas no se
alcanzan a ver" y "el degradado de bandas no se visualiza"— con la misma causa.
Medido: la columna ocupaba mas que la ventana. Ahora se limita a la altura
disponible, la hoja de marca se desplaza dentro de su propio marco y la columna
se ensancha de 380 a 440 px. Con 804 px de ventana la columna mide 686 y entra
completa.

El degradado de bandas si se aplicaba: el volcado del DOM confirma
`--preview-superficie: linear-gradient(240deg in srgb, #082b22, #b1489b)`. No
era un fallo de calculo sino de visibilidad.

Defecto real: el boton "Quitar degradado" solo aparecia si el valor llegaba ya
escrito, porque `escribir()` no refrescaba su estado. Quien construia un
degradado moviendo el angulo o los colores no podia deshacerlo y quedaba sin
forma de volver a un color plano. Comprobado en navegador: ahora aparece al
construirlo y al pulsarlo el campo queda vacio.

Validacion: 156 pruebas de configuracion institucional e idiomas, sintaxis JS,
Ruff y Django check.

## 212. Colores independientes y esquema de plataforma

Tres peticiones del usuario en un bloque.

**Colores propios.** Se agregan al contrato cinco opciones nuevas, todas
opcionales y compatibles hacia atras: `color_secundario`, `boton_principal`,
`boton_acento`, `barra_color` y `barra_degradado`. Lo que se deja vacio hereda
el color base de siempre. El color del texto de cada boton se deriva por
contraste, de modo que un boton claro recibe tinta oscura y uno oscuro, blanca.
La barra superior deja de estar atada al color primario: acepta su propio color
y su propio degradado, plano o degradado, con independencia de las bandas.

**Panel Contenidos.** Sus tres niveles usaban turquesas y dorados escritos en
el codigo (#087f8f, #087787, #17a2b8, #d8a91f) ajenos a la paleta. Ahora se
diferencian por jerarquia con variables institucionales: modulo con el color de
boton principal, carpeta con filete de acento y archivo como superficie con
borde, resaltando el seleccionado.

**Visualizador.** Deja de ser una tarjeta suelta y pasa a ser un esquema de la
plataforma: barra superior y navegacion, portada sobre fotografia, pestanas del
catalogo, tarjeta completa con los cuatro tipos de accion, panel de contenidos
con sus tres niveles, formulario, y bandas con el degradado. La columna se
ensancha al 46 % y el editor deja de limitarse a 1180 px.

Comprobado en navegador con colores deliberadamente ajenos —boton morado,
acento turquesa y barra violeta— viendo cada superficie tomar su color propio
sin arrastrar a las demas.

Validacion: 190 pruebas de configuracion institucional, idiomas, unidades y
portal, con tres casos nuevos sobre colores propios, herencia y degradado de
barra; sintaxis JS, Ruff, Django check y migraciones en seco limpios.


## 213. Centros I+D: procedencia, indicadores e identidad institucional (7 de octubre de 2026)

A partir de la auditoría solicitada por el usuario se añadió la separación de
muestras y contenido institucional, con revisión administrativa, fuente, autor y fecha.
Los ejemplos no se publican ni inflan indicadores; un conteo vacío vale cero y las
mediciones manuales ausentes siguen pendientes. Servicios atendidos solo cuenta
solicitudes de servicio entregadas o cerradas. Las recargas preservan registros reales.

El centro tiene adscripción, misión, visión, sectores y retos, con validación de
identidad y estado separadas. Los documentos generados son borradores internos;
un documento aprobado requiere emisor, fecha y fuente. Las migraciones 0009 y 0010
se aplicaron con respaldo previo comprobado por inventario y SHA-256.

Pasaron 108 pruebas de centros, portal, rutas y manifiestos, además de Django
check, migraciones en seco, Ruff de Centros I+D y auditoría modular. Revisión
visual pendiente: el inventario de automatización no ofreció navegadores. No
se cierra todavía la aceptación integral de la vertical.

Guía: [primer bloque implementado](../centros-id-primer-bloque-2026-10-07.md).
El [prompt maestro](../prompt-maestro-centros-id.md) conserva los siguientes
bloques de investigación, transferencia e integraciones operativas.


## 214. Centros I+D con investigación y transferencia documentadas

Se amplió la agenda científica de las líneas y el detalle de proyectos, con
problema, objetivos, metodología, sector, categoría e hitos. Avance, TRL y
protección exigen metadatos de respaldo para mostrarse; una etapa no da por
completadas las anteriores. Los montos privados se excluyen también de los
agregados de alianzas. Suspensión y cancelación se distinguen de actividad.

Los catálogos de resultados comparten filtros con exportaciones JSON y RIS.
Se añadió DOI normalizado y único por centro, versión y acceso con embargo.
El guardado bloquea adjuntos protegidos en el almacenamiento público actual.
Los casos requieren receptor, mecanismo, aceptación, evidencia y autorización
de divulgación; el impacto cuantificado exige referencia y método. La vigencia
de aliados se calcula con instrumento, fuente y fechas. Las alertas son internas
y se calculan al consultar, sin correo programado.

Las solicitudes guardan proyecto o desarrollo y finalidad, preservan el contexto
al iniciar sesión y rechazan relaciones incompatibles. Pasaron 133 pruebas
(incluidas 25 nuevas), Ruff, Django check, migraciones en seco y auditoría modular.
La migración 0011 se aplicó con respaldo previo inventariado y SHA-256 en
var/backups/centros-id-pre0011-20261007-211335. Verificación HTTP 200 en ambas
fichas e identidades y en una línea del CIDT. Revisión visual pendiente por falta
de navegador disponible. No se rellenaron contenidos reales con ejemplos.

Guía: [investigación y transferencia](../centros-id-investigacion-transferencia-2026-10-07.md).
Sigue el bloque operativo de servicios, acompañamiento, cursos, reservas y
simulación del prompt maestro. No se cierra la aceptación integral de la vertical.


## 215. Servicios, recursos propios y seguimiento privado de centros I+D

El portafolio incorpora alcance, exclusiones, entradas, requisitos, método,
entregables, aceptación, plazos, condiciones y contacto. La oferta distingue
consulta, disponibilidad y suspensión; las tarifas requieren fuente y vigencia.
Las solicitudes muestran campos por intención y conservan el recurso al entrar.

Se agregó un índice del inventario existente, sin duplicarlo. La reserva propia
requiere activos individuales o espacios habilitados, horario, aforo, requisitos,
inducción, supervisión y calibración cuando correspondan. La disponibilidad
pública descuenta márgenes, bloqueos y ocupaciones sin divulgar datos privados.
La confirmación se revalida con bloqueos de filas y transacción. Cancelar libera
el uso y conserva antecedentes; las sesiones pendientes quedan canceladas.

El expediente privado reúne diagnóstico, plan, responsable, sesiones, tareas,
respuestas, entregable y evaluación. El catálogo de cursos muestra propietario,
ediciones y enlaces a la matrícula original. Las agendas vinculadas conservan
su operación en origen. Las herramientas virtuales necesitan revisión de método,
versión, supuestos y límites; todavía no hay motor de escenarios versionados.

Pasaron 177 pruebas, incluidas confirmaciones simultáneas de un mismo equipo y
espacio. Ruff, Django check, migraciones en seco, auditoría modular y diff check
limpios. La migración 0012 se aplicó después del respaldo inventariado y SHA-256
verificado en var/backups/centros-id-pre0012-20261007-213837. HTTP 200 en ficha,
identidad y solicitud de ambos centros, y recursos, portafolio y ficha de servicio
del CIDT. El CIDT tiene 100 registros de equipamiento, pero aún cero activos
reservables, espacios habilitados, horarios y herramientas revisadas. No se
habilitaron históricos ni se agregaron ejemplos a la base real. Sin navegador
controlable para inspección visual.

Guía con diseño por sección, reglas, administración, automatizaciones y prompt
complementario: [servicios, recursos y seguimiento](../centros-id-servicios-recursos-seguimiento-2026-10-07.md).
Siguen pendientes datos reales para habilitar recursos, revisión visual,
restauración completa, notificaciones, cotizaciones/pagos, coordinación de
reservas vinculadas y simulaciones reproducibles. No se cierra la aceptación
integral de la vertical.


## 216. Fichas sin avisos administrativos y accesos acordes con la oferta

A petición del usuario se retiró «Muestras por revisar» de la ficha y sus
consultas de conteo; los ejemplos siguen revisándose en el administrador.
También se trasladó «Plazos por revisar» a «Seguimiento de gestión» dentro
de la administración del centro, únicamente para responsables o gestores.
Las alertas se consultan al necesitarlas y no cargan un panel sobre Contenidos.

La entrada ofrece servicios y uso solo cuando hay oferta habilitada. Sin ella,
abre la propuesta de necesidad y evita formularios sin opciones; los enlaces
generales a operaciones sin oferta muestran una alternativa y conservan Mis
solicitudes. Los servicios elegidos se validan antes de autenticarse. Los errores
de campos ocultos se muestran. Los selectores omiten recursos inhabilitados.

Los servicios sujetos a evaluación dicen «Consultar servicio» y los disponibles
«Solicitar servicio»; las ofertas suspendidas no presentan acción. Se eliminaron
notas genéricas repetidas sobre pagos. El detalle de equipo explica inducción,
supervisión y vigencia de calibración sin divulgar el respaldo privado.
Los cursos muestran fin y lugar de la edición y evitan mensajes contradictorios
de ausencia de oportunidades cuando sí hay cursos publicados.

Pasaron 184 pruebas de centros, laboratorios, cursos vinculados, portal, rutas y
manifiestos. Ruff, Django check, migraciones en seco y diff check limpios. No se
necesitaron migraciones ni cambios de datos. HTTP 200 en ficha y solicitud de
ambos centros; el CIDT ofrece servicios y el CIAB propuestas de necesidad, sin
ofrecer uso de recursos no habilitados. La revisión visual permanece pendiente
por falta de navegador controlable.

Guías actualizadas: README de Centros I+D, investigación/transferencia y
[servicios, recursos y seguimiento](../centros-id-servicios-recursos-seguimiento-2026-10-07.md).


## 217. CIDT con estructura y contenido de funcionamiento para desarrollo local

El usuario mostró las secciones vacías y pidió construir contenido como si el
centro estuviera funcionando. Se completó y activó un escenario operativo local
del CIDT, sin convertir muestras en evidencia institucional. La vista exige
DEBUG y CENTROS_ID_ESCENARIOS_OPERATIVOS=cidt-upec; en producción se excluye.
La configuración se aplicó en el .env local y el servidor recargó correctamente.

Contiene 12 proyectos con problema, objetivos, método y 48 hitos; 10 resultados
con versiones y fichas descargables; 28 perfiles por función; 4 grupos; 3 casos
conectados a proyectos/desarrollos; 5 actores de colaboración; 6 novedades;
6 convocatorias generales y 4 programas formativos. Estos últimos muestran
horas, modalidad, fechas, requisitos, programa, lugar y trabajo final, con una
solicitud de participación que conserva curso y área. No se fabrican matrículas.

Se completaron los campos editoriales vacíos de 57 servicios y ocho líneas;
las ediciones existentes se conservan. Se añadieron cinco guías informativas.
La vista pública local reúne siete documentos representativos y mantiene fuera
los documentos institucionales privados. Misión, visión y estado operativo se
presentan en el escenario sin otorgar sellos administrativos.

Tres activos individuales y tres espacios de práctica tienen 30 ventanas de
horario de lunes a viernes, 08:00–17:00, con 15 minutos por extremo. La petición
queda recibida y no ocupa el recurso hasta su confirmación. Las subáreas de
práctica no aumentan la superficie del edificio. Grupos, equipos y zonas tienen
procedencia desde la migración 0013. Fuera del escenario, muestras y recursos
de práctica no se ofrecen ni se confirman.

Se implementó una calculadora educativa de capacidad de dos etapas en serie,
con turno, porcentaje productivo, demanda, ciclos y puestos paralelos. Calcula
capacidad, etapa limitante y demanda pendiente; valida rangos y explica sus
supuestos. No es un gemelo digital conectado ni guarda escenarios versionados.
Las exportaciones JSON/RIS y los archivos conservan procedencia representativa.

Pasaron 195 pruebas de centros, laboratorios, cursos vinculados y portal;
después del ajuste de presentación y manifiesto, otras 48 comprobaciones de
escenario, publicación institucional, estructura, rutas y manifiestos. Ruff,
Django check, migraciones en seco, auditoría modular y diff check limpios.
Se verificaron 42 rutas sobre la base local (ficha, seis pestañas, secciones,
subpáginas, nueve áreas y calculadora): todas HTTP 200, ninguna sección vacía.
El servidor en localhost:8000 devuelve Ahora en el centro con proyectos y sin
el aviso de ausencia. No se afirma inspección visual de navegador.

La migración 0013 se aplicó después del respaldo verificado por inventario y
SHA-256: var/backups/centros-id-pre0013-20261007-222001/database.dump,
3.661.082 bytes. No se hizo restauración completa. El CIAB conserva su contenido
y no recibe el escenario tecnológico del CIDT. El cambio ajeno en
scripts/docker_scheduler.sh se conserva. La restricción de escritura de .git
sigue impidiendo consolidar los cambios en un commit desde esta sesión.

Guía: [estructura y contenido operativo](../centros-id-escenario-operativo-2026-10-07.md).


## 218. Acciones de la ficha con una prioridad pública y gestión separada

Aprobada por el usuario la simplificación de los cuatro botones de cabecera.
«Trabajar con el centro» abre la sección existente de solicitudes por intención;
Compartir permanece como icono con nombre accesible y el mismo comportamiento.
Se retiraron de la cabecera el PDF y Gestionar.

Gestionar y su contador de solicitudes pendientes viven en una barra separada,
únicamente para usuarios con permiso de gestión. El PDF se ofrece como
«Descargar ficha del centro (PDF)» en Documentos y normativa. Esta sección
siempre está disponible porque ofrece el resumen generado aun sin documentos
adicionales. Identidad y contacto enlaza a Documentos y descargas. Se quitaron
el aviso de documentos vacíos y los estilos de la acción administrativa antigua.
CSS con versión v18 y collectstatic ejecutado.

Pasaron 79 pruebas existentes de ficha/contenido CIDT, publicación institucional
y escenario operativo. Se ajustaron las expectativas por la ubicación del PDF
y la disponibilidad de Documentos. Django check, Ruff y diff check limpios.
Comprobación de HTML renderizado: acción principal y compartir accesible para
público y gestor; gestión fuera del hero y ausente para anónimos. HTTP 200 en
ficha, Documentos de ambos centros, CSS actualizado y PDF con firma %PDF-.
Sin navegador disponible para inspección visual (inventario vacío).
No se necesitaron migraciones ni cambios de datos; se conserva el cambio ajeno
en scripts/docker_scheduler.sh y la restricción previa de escritura de .git.


## 219. Cabecera compacta de centros con acciones al estilo de Laboratorios

El usuario pidió retirar la barra superior de administración y reducir el
protagonismo de la imagen. Gestionar centro vuelve al grupo de acciones dentro
de la cabecera, junto a Compartir y Trabajar con el centro; conserva permisos,
contador de pendientes y nombre accesible cuando el móvil oculta su texto.
No existe una franja administrativa encima de la imagen.

La cabecera toma una altura base de 260 px, título compacto, sigla en el
antetítulo y acciones a la derecha en escritorio. En pantallas pequeñas las
acciones pasan debajo y la altura se adapta al contenido. Se retiraron las
tarjetas de cifras del hero; los indicadores dinámicos permanecen en Conoce
el centro. PDF en Documentos y normativa, sin cambios en sus funciones.
Se retiró el contexto de cifras sin uso de la ficha y se ajustó la prueba
existente para comprobar el conteo en Conoce el centro. CSS v19 y collectstatic
ejecutado; README actualizado.

Pasaron 79 pruebas existentes de CIDT, publicación institucional y escenario
operativo, además de Ruff, Django check y diff check. El HTML renderizado para
público y gestor confirma la ubicación y permisos de las acciones y la ausencia
de la barra y las tarjetas de cifras. HTTP 200 en ambas fichas, Conoce el centro,
Documentos y CSS actualizado. No se afirma revisión visual: no hay navegador
controlable disponible. No se necesitaron migraciones ni cambios de datos;
se conserva el cambio ajeno en scripts/docker_scheduler.sh.


## 220. Gestión del centro dentro de un modal dinámico propio

El usuario pidió que Gestionar centro reproduzca el patrón de Laboratorios
sin abrir Django admin. El botón conserva su ubicación en el hero compacto
y abre un dialog con cabecera verde, navegación lateral y contenido cargado
por fetch. La ruta privada gestion/ sirve una página propia como alternativa
y fragment=1 sirve el panel. Los accesos Editar, completar contenido y crear
carpetas también usan este gestor; desde el visualizador solicitan al padre
abrir el modal mediante postMessage validado por origen y ventana emisora.

El panel reúne nueve secciones y 29 tipos de registro: indicadores y atención;
agenda de reservas y sesiones; recursos y horarios; investigación y
transferencia; servicios y formación; equipo y gobierno; contenidos y
documentos; configuración. Las listas tienen búsqueda y paginación, y los
formularios permiten crear o editar sin usar pantallas del administrador.
Las solicitudes existentes conservan ruta, actor e historial; no se inventan
indicadores de utilización. Guardar refresca la ficha, el árbol y el visor.

Cada GET y POST comprueba responsable, gestor o superusuario activo. Los
selectores, relaciones múltiples y expedientes se limitan al centro. POST
requiere CSRF y las respuestas privadas no se cachean. Las reservas y el
acompañamiento reutilizan las validaciones y bloqueos transaccionales del
dominio. Los conflictos de edición se detectan mediante una revisión firmada
y los errores mantienen el formulario. No se exponen campos de privilegios,
solicitante ni marcas de procedencia; las muestras locales siguen siendo
muestras. Identidad y estado se validan solo mediante acciones explícitas
con respaldo. No se modifica la operación de laboratorios vinculados.

Pasaron 175 pruebas de Centros I+D y oferta vinculada, incluidas 18 nuevas de
permisos, CSRF, solicitudes, reservas solapadas, edición concurrente, creación
y configuración; además pasaron 23 pruebas de rutas y manifiestos modulares.
Se comprobaron 77 listas y editores con datos locales mediante GET sin
mutaciones. El controlador JS se comprobó en un DOM simulado para apertura,
consulta autenticada, bloqueo de URL externa, POST con acción y CSRF, y cierre.
Ruff, Django check, auditoría modular, sintaxis JS, migraciones en seco y
diff check limpios. Collectstatic ejecutado; ficha v20 y gestión v1.
HTTP 200 en ambas fichas y nuevos recursos; gestión anónima redirige al login.
Sin navegador controlable (inventario vacío); no se afirma revisión visual.
No se necesitaron migraciones ni cambios de datos activos. README actualizado
y cambio ajeno en scripts/docker_scheduler.sh conservado.


## 221. Separación del menú de Centros I+D como en Laboratorios

A petición del usuario, las pestañas del centro llevan separadores verticales
del mismo color y grosor que Laboratorios, sin huecos entre columnas. La
selección tiene esquinas de 3 px, acordes con el estilo efectivo del menú
de referencia. Los separadores se omiten en los extremos de cada fila
en las distribuciones de tres y dos columnas. CSS compartido v21;
collectstatic ejecutado. Ficha y CSS actualizado devuelven HTTP 200,
y diff check limpio. Cambio de presentación, sin migraciones ni datos.
No se afirma inspección visual de navegador.


## 222. Copiar enlaces a secciones de laboratorios y demás unidades

Se añadió «Copiar enlace a esta sección» junto a pantalla completa en el
visualizador compartido por laboratorios, plantas piloto, centros experimentales
y observatorios. El enlace conserva la ruta y el idioma de la unidad, la pestaña
y el identificador del recurso seleccionado. Para páginas internas del visor
sin botón asociado se reutiliza el enlace directo existente; no se copian URLs
externas del iframe ni parámetros ajenos a la sección.

La copia muestra confirmación accesible y tiene alternativa cuando el navegador
no permite Clipboard API. La restauración espera a que los manejadores estén
registrados: el video inicial ya no reemplaza el recurso solicitado. Se mantienen
los enlaces anteriores a guías y se sincroniza la pestaña del recurso activo.
Estilos y controladores con versión 20261007-enlace-seccion-v1; collectstatic
ejecutado. No se necesitaron migraciones ni cambios de datos activos.

Pasaron 37 pruebas existentes de fichas y contenidos de unidades y ocho pruebas
JS de copia, restauración, idioma, enlaces internos, guías y carga inicial.
Estas últimas se ejecutan con:

`node --test webcitt/tests/js/test_enlace_seccion.cjs`

Comprobados HTML y controlador en fichas de las cuatro clases de unidad: HTTP
200. Sintaxis JS y diff check limpios. Sin navegador controlable disponible;
las pruebas JS usan DOM simulado y no se afirma revisión visual. Se conserva
el cambio ajeno en scripts/docker_scheduler.sh.


## 223. Auditoría integral y preparación de seguridad para producción Linux

El usuario pidió auditar estructura, duplicados y archivos sin uso, y reforzar
secretos por entorno, CORS, validación/saneado, límites de frecuencia, RLS y CSP.
Confirmó que el despliegue será en un servidor Linux propio de la universidad.
El portal y el backend comparten origen por defecto; los dominios reales se
exigen mediante variables de entorno. No se accedió ni desplegó en ese servidor.

Se añadieron auditores de estructura y plantillas; el de huérfanos reconoce los
destinos dinámicos registrados y archivos nuevos. Resultado: 3.636 archivos,
cero errores, cero colisiones de mayúsculas, cero huérfanos y 346 plantillas
válidas. Cuatro pares de imágenes idénticas se conservan como alias. Las tres
coincidencias de collectstatic son overrides intencionales de Grappelli.
Se corrigieron problemas de Ruff y la clasificación de seis modelos de centros.
El índice documental reúne las guías existentes; TRASPASO.md describe el estado
actual y remite a docs/auditoria-produccion-2026-10-08.md y produccion-linux.md.

CORS usa orígenes exactos; el backend rechaza JSON inválido/no finito, NUL y
estructuras excesivas. El HTML enriquecido se sanea al guardar y al presentar;
los ejemplos de reserva usan json_script. El contador PostgreSQL atómico limita
autenticación y escrituras, con limpieza programada y límites adicionales Nginx.
La CSP usa nonce aleatorio en código de plantillas confiable y se retiraron
handlers inline. Los recursos HTML/ZIP revisados permanecen aislados en sandbox;
la política del portal no habilita inline/eval. La entrega de medios comprueba
registro, privacidad, permisos y embargos; archivos desconocidos se deniegan.
Login y registro respetan la verificación obligatoria de correo de producción.

Las migraciones 0313 y 0314 crean contadores y fuerzan RLS en seis tablas
académicas/personales, con identidad local a la transacción y control de lectura
y escritura. No es RLS universal: agenda compartida, cupos y restantes dominios
conservan autorización por objeto. Se separaron credenciales/servicios de
migración, web y respaldo; el arranque verifica que el rol web no tenga privilegios
excesivos. La web no recibe credenciales elevadas ni recarga .env en producción.
Se añadió guía Linux, servidor Waitress con proxy exacto y plantilla Nginx TLS.

OAuthLib/PyJWT, PDF.js local, jQuery y Bootstrap JS se actualizaron. El contraste
de 35 paquetes Python y siete bibliotecas del navegador no reportó avisos conocidos.
Bootstrap 4 permanece fuera de soporte; su migración a 5 requiere adaptar la UI.
Se detectó .env en cuatro commits históricos, sin revelar valores: aunque las
credenciales locales son distintas, TI debe confirmar la revocación de las antiguas.
No se reescribió Git ni se aplicaron migraciones a los datos activos.

Validación final: 2.634 pruebas completas, sin fallos ni omisiones, en bases y
medios aislados; además 116 pruebas dirigidas y 12 JS. La prueba entre unidades
antes omitida ahora crea sus datos. Ruff, checks Django, migraciones en seco,
auditorías modulares/señales, sintaxis JS/shell, Compose y diff check correctos.
Collectstatic correcto; PDF renderizado en Node y modales ensayados con DOM
simulado. No se afirma inspección visual de navegador. Solo QA aceleró fixtures
con MD5; los hashers normales/producción no cambian. Logs y herramientas
transitorias en var, fuera de Git.

Queda comprobar en Linux dominio/TLS, SMTP, roles PostgreSQL reales, Nginx,
respaldos/restauración y navegación HTTPS/CSP con los recursos de la instalación.
El usuario solicitó crear el commit y subir esta auditoría a reestructura-modular.
Esta entrada acompaña ese commit; consultar git log y el remoto para su hash y
estado de publicación.
