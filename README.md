# SILAB-CID — Sistema de Laboratorios y Centros I+D

Sistema institucional para gestionar y publicar los Centros de Investigación y
Desarrollo, laboratorios, observatorios, centros experimentales y plantas
piloto de la Universidad Politécnica Estatal del Carchi.

El producto se reorganiza para instalaciones configurables por institucion.
La identidad SLCID ya esta separada del perfil UPEC; los modulos opcionales,
catalogos propios y aislamiento completo siguen la ruta de arquitectura.
Configuracion y alcance actual en
[Identidad del producto e institucion](docs/identidad-producto-institucion.md).

La interfaz permite elegir español o inglés desde ES/EN en el encabezado y el
administrador. La preferencia conserva la navegación y la zona institucional;
los archivos y datos publicados mantienen su idioma original. Configuración y
mantenimiento: [Interfaz ES/EN](docs/internacionalizacion-es-en.md).

Los dos dominios principales son:

- **Unidades:** catálogo, contenidos, equipos, inventario, reservas, usuarios,
  indicadores y reportes para laboratorios y unidades experimentales.
- **Centros I+D:** capacidades científicas, investigadores, líneas, proyectos,
  resultados, servicios y transferencia.

Las páginas de Inicio, Quiénes somos, Servicios, Normativa y Noticias forman el
portal institucional que conecta ambos dominios.

El código operativo pertenece a aplicaciones bajo `apps/`: cada una define
sus modelos, servicios, administración, rutas y recursos. La carpeta
`webcitt/` fue retirada. Se conserva exclusivamente su historial de migraciones
en `apps/historial_modelos`; las tablas existentes mantienen sus nombres para
preservar datos, permisos y relaciones. El [mapa vigente de aplicaciones](apps/README.md)
y la [arquitectura](docs/arquitectura.md) explican la propiedad y la actualización.
La [verificación de la extracción](docs/extraccion-aplicaciones-2026-10-12.md)
recoge la conservación de archivos y bases, y las pruebas realizadas.

## Repositorio y datos conservados

Repositorio: [Luisknt07/SILAB-CID](https://github.com/Luisknt07/SILAB-CID), rama
principal `main`. La copia local está en
`C:\Users\PC2\Documents\GitHub\SILAB-CID`. El sistema conserva su identidad
funcional SLCID y la configuración institucional existente.

El inicio independiente conserva el código vigente, la documentación y los dos
vídeos Git LFS. El historial original permanece en CITT. Para clonar los vídeos
instalar Git LFS y ejecutar `git lfs pull` después de clonar.

Las dos bases completas y sus roles tienen respaldos restaurados y comparados
en `var/backups/traslado-20261114/`. Los adjuntos, aplicaciones locales y la
configuración privada también se copiaron a esta carpeta. En este equipo se
siguen usando las bases existentes `citt_db` y `citt_centros_id` y el volumen
`citt_postgres_data`, sin reinicializarlos ni duplicar sus registros.

El repositorio GitHub es público: `.env`, bases, roles, adjuntos y respaldos
permanecen fuera de Git. Clonar el código no descarga esos datos. Para cambiar
de equipo deben trasladarse por un canal privado junto con los medios; la guía
local está en `var/traslado-20261114/LEEME-DATOS.txt`. El estado para continuar
está en [TRASPASO.md](TRASPASO.md).

## Puesta en marcha local

Para reutilizar el PostgreSQL local existente con Django nativo, configurar
las variables privadas de base y arrancar solo ese servicio:

```powershell
docker compose -f docker-compose.desarrollo.yml config --quiet
docker compose -f docker-compose.desarrollo.yml up -d --no-recreate db
```

Este archivo independiente no inicia respaldos y exige el volumen existente
`citt_postgres_data`. No combinarlo con los archivos Compose de producción ni
usar `--remove-orphans`. Para una instalación nueva, seguir el aprovisionamiento
de la [guía de bases](docs/estructura-bases-datos-docker.md); este comando no
crea ni importa las dos bases. Estado y comprobaciones en la
[limpieza local](docs/limpieza-desarrollo-bases-2026-10-12.md).
La [organización de aplicaciones](docs/organizacion-aplicaciones-2026-10-12.md)
deja PostgreSQL, pasarela y WMS de Logística activos. Guardar nuevos ZIP no
inicia aplicaciones automáticamente; su puesta en marcha se solicita desde el admin.

```powershell
uv sync --locked
uv run python manage.py migrate
uv run python manage.py runserver
```

La aplicación escribe todo lo de ejecución bajo `var/` (adjuntos, estáticos
recopilados, cachés, registros, salidas, respaldos y marca privada); ese
directorio no se versiona y la raíz del repositorio contiene solo código,
configuración, documentación y scripts.

`uv run` usa siempre el intérprete y las dependencias de `.venv`, sin depender de
la política de ejecución de PowerShell. Si no se dispone de `uv`, puede crearse el
entorno con `py -3.11 -m venv .venv` e instalar `requirements.txt` antes de usar
`.\.venv\Scripts\python.exe manage.py runserver`. `requirements.txt` se genera
desde `uv.lock` y no se edita a mano; ver
[Despliegue de producción](docs/despliegue-produccion.md).

En Windows se recomienda iniciar el entorno local con:

```powershell
.\scripts\iniciar_desarrollo.ps1
```

El script valida la configuración y las migraciones, aplica las pendientes,
elimina la copia recopilada anterior de los archivos estáticos y publica la
versión vigente antes de iniciar el servidor.

Para incorporar reservas históricas al FT02 después de habilitar la
planificación automática se usa el comando idempotente:

```powershell
.\.venv\Scripts\python.exe manage.py sincronizar_planificaciones_reservas
```

Puede revisarse previamente sin guardar con `--simular` y limitarse a una unidad
con `--unidad <slug>`.

La configuración sensible se suministra mediante variables de entorno. En
desarrollo puede usarse `.env`; `.env-example` contiene la referencia. Para el
servidor universitario seguir [producción Linux](docs/produccion-linux.md), con
roles separados de base de datos. La [auditoría integral del 10 de octubre](docs/auditoria-integral-produccion-2026-10-10.md)
recoge optimizaciones, evidencia, límites y condiciones pendientes de producción.

La [auditoría de reservas y gestión del 10 de noviembre](docs/auditoria-reservas-gestion-2026-11-10.md)
detalla las correcciones de integridad, las pruebas de permisos e inventario y
las condiciones de datos e infraestructura que deben resolverse antes de publicar.

El [mantenimiento del 11 de noviembre](docs/mantenimiento-validacion-2026-11-11.md)
actualiza los roles locales, respaldos, claves, conciliación y saneamiento del historial.
Para iniciar la validación con credenciales web restringidas:
`python scripts/servidor_local_seguro.py`.

La [validación continua](.github/workflows/ci.yml) comprueba cada push y pull request
con PostgreSQL efímero: pruebas Django/JavaScript, arquitectura, migraciones, Ruff
y vulnerabilidades de dependencias. No despliega ni utiliza credenciales de producción.

Para repetir la regresión con las herramientas PDF y trazas paralelas, configurar
primero un servidor **QA aislado** y sus variables de conexión, incluidas las de
Centros. Desactivar la lectura del `.env` operativo con
`$env:PYTHON_DOTENV_DISABLED = '1'` en esa sesión. No ejecutar esta regresión
contra las bases operativas ni crear bases `test_*` en producción:

~~~powershell
uv run --with tblib==3.2.2 --with PyMuPDF==1.28.2 python manage.py test tests scripts.tests apps --parallel 4 --noinput
~~~

Esos dos paquetes son temporales para las pruebas y no forman parte de la imagen web.
El runner rechaza pruebas con SQL si se carga `.env`, si el nombre de base no
empieza por `citt_qa_` (salvo `citt_ci` en CI) o si el servidor no es loopback.
También debe declararse el alias `centros`, aunque su router esté desactivado,
cuando una prueba solicite explícitamente ambas bases.

La planta de café conserva la plantilla común de áreas y equipos. Su ampliación
de procesos y medios se instala sobre la unidad existente, primero revisando
la simulación y después aplicando los cambios:

```powershell
uv run python manage.py completar_planta_cafe --simular
uv run python manage.py completar_planta_cafe --aplicar
uv run python manage.py completar_medios_cafe --simular
uv run python manage.py completar_medios_cafe --aplicar
```

Los cargadores conservan identificadores, edición manual y archivos propios.
Las imágenes y videos del catálogo son referenciales; no crean activos físicos
ni existencias. Alcance, fuentes y verificación en la
[aceptación de café](docs/aceptacion-plantas-piloto.md#estandarización-visual-de-café--14-de-octubre-de-2026).

## Organización

- [Auditoría de reportes y unidades (25-09-2026)](docs/auditoria-reportes-unidades-20260925.md):
  hallazgos de seguridad, integridad y arquitectura, con la ruta priorizada de continuación.
- [Remisión y seguimiento de mejora: paso 3](docs/circuito-mejora-decanato.md):
  entrega interna al decanato, acuse, resolución y acciones con responsable y plazo.
- [Filtros, alcance y rendimiento de reportes: paso 4](docs/reportes-filtros-rendimiento.md):
  fechas controladas, subtipos, exportaciones consistentes y consultas compartidas.
- [Evaluación asistida de unidades](docs/evaluacion-asistida-unidades.md):
  visor contenido, acordeones, rúbrica por documento y observaciones trazables.
- [Seguridad e integridad del expediente: pasos 1 y 2](docs/cierre-seguridad-integridad-expediente.md):
  correcciones, migración aplicada, validación y siguiente bloque del circuito al decanato.
- [`TRASPASO.md`](TRASPASO.md): estado operativo vigente, orden de lectura y
  siguiente bloque. Es el punto de entrada para continuar el trabajo.
- [`docs/historial/`](docs/historial/): registros acumulativos de cada bloque
  (`CODEX_CONTEXT.md`, `TRASPASO-CODEX.md`); historia, no estado vigente.
- [`docs/rutas-y-contratos-modulares.md`](docs/rutas-y-contratos-modulares.md):
  primera separacion ejecutada, contrato del directorio, inventario de codigo
  y datos, pruebas de compatibilidad y limites pendientes.

- [`docs/ruta-ejecucion-arquitectura-modular.md`](docs/ruta-ejecucion-arquitectura-modular.md):
  secuencia M00-M13, entregas por contexto, puertas de calidad y recuperacion
  de codigo, datos y permisos.

- [`docs/arquitectura.md`](docs/arquitectura.md): estructura vigente, límites
  de dominio y evolución planificada.
- [`docs/estructura-objetivo-sistema-laboratorios.md`](docs/estructura-objetivo-sistema-laboratorios.md):
  árbol modular propuesto, responsabilidades de cada app y cambio seguro del
  nombre institucional y de los identificadores heredados.
- [`docs/arquitectura-vertical-unidades-centros-id.md`](docs/arquitectura-vertical-unidades-centros-id.md):
  separación de Laboratorios, Plantas piloto, Centros experimentales,
  Observatorios y Centros I+D, con propiedad de datos y aislamiento de fallos.
- [`docs/arquitectura-portal-administrable.md`](docs/arquitectura-portal-administrable.md):
  módulos y administración editorial de Inicio, Quiénes somos, Servicios,
  Normativa y Noticias.
- [`docs/guia-presentacion-institucional.md`](docs/guia-presentacion-institucional.md):
  cómo cambiar nombres, logotipos y colores desde el administrador, y dónde se
  usa cada logotipo.
- [`docs/inventario-estilos.md`](docs/inventario-estilos.md): sistema visual y
  recursos compartidos.
- [`docs/visor-pdf.md`](docs/visor-pdf.md): visor PDF compartido por la consola
  de la unidad y la vista previa de documentos, y sus gestos en pantalla táctil.
- [`docs/ciclo-reservas-notificaciones.md`](docs/ciclo-reservas-notificaciones.md):
  estados de una reserva y correos que dispara cada uno.
- [`docs/plan-estudios-alimentos-y-plantas.md`](docs/plan-estudios-alimentos-y-plantas.md):
  correspondencia entre el plan de estudios y las prácticas de planta piloto.
- [`docs/autenticacion.md`](docs/autenticacion.md): entrada social y con
  contraseña, tipos de usuario y compuerta de perfil.
- [`docs/unidades-y-centros-id.md`](docs/unidades-y-centros-id.md): estado
  para producción, los cuatro tipos de unidad, reportes y la ruta hacia los
  Centros I+D.
- [`docs/planta-por-procesos.md`](docs/planta-por-procesos.md): la planta por
  procesos, del proceso con etapas al plan de requerimientos, la capacidad,
  el plan maestro y el plan de calidad.
- [`docs/ruta-planta-piloto.md`](docs/ruta-planta-piloto.md): la hoja de ruta
  única de la planta como sistema real: secciones, actores, la reserva por
  proceso, las guías por sesión, la seguridad industrial, las visitas, los
  servicios y el orden de construcción.
- [`docs/aula-de-produccion.md`](docs/aula-de-produccion.md): la planta como
  sistema real y como simulador: quién carga qué, dónde vive cada protocolo,
  los ejercicios (calidad, balances, diagramas, MRP, ERP, WMS) y la
  trazabilidad de lo que hace cada estudiante.
- [`docs/integracion-version2.md`](docs/integracion-version2.md): auditoría e
  integración selectiva del trabajo paralelo realizado en `version2`.
- [`docs/mantenimiento-equipos.md`](docs/mantenimiento-equipos.md): alcance,
  flujo y reglas del mantenimiento, incidencias y ciclo de vida de activos.
- [`docs/ciclo-institucional-laboratorios.md`](docs/ciclo-institucional-laboratorios.md):
  fuente funcional del ciclo solicitud, aprobación, ejecución y cierre.

La versión actual inicia sobre PostgreSQL con un esquema propio. No conserva
fixtures, importadores ni procedimientos de migración del sistema anterior.

`config` contiene la configuración del proyecto. `webcitt` se conserva como
identificador interno de la aplicación por compatibilidad con las migraciones,
permisos y datos existentes; no representa el nombre vigente del producto.

La preparación para el servidor universitario se describe en [producción Linux](docs/produccion-linux.md) y en la [auditoría del 8 de octubre](docs/auditoria-produccion-2026-10-08.md).

La documentación y sus auditorías están reunidas en el [índice documental](docs/indice.md).

La separación de Centros I+D usa una segunda base PostgreSQL y conserva la identidad institucional central. Antes de activarla en otra instalación, seguir [copia, corte y recuperación](docs/separacion-centros-operacion.md).

Estado local del 11 de octubre: Centros I+D ya opera con su base propia; consultar [verificación y límites de producción](docs/separacion-centros-verificacion-2026-10-11.md).
