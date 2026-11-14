# Arquitectura vigente del SLCID

La extracción del contenedor `webcitt/` asigna 182 modelos y 259 rutas
operativas a aplicaciones propietarias. No existe código activo en esa
carpeta. El [mapa de aplicaciones](../apps/README.md) define dónde modificar
cada capacidad. La configuración del proyecto madre vive en `config/`.

## Organización y límites

Las verticales de Laboratorios, Plantas piloto, Centros experimentales y
Observatorios poseen sus perfiles y operaciones específicas. Directorio,
recursos, reservas, formación, documentos, finanzas y gestión de unidades son
capacidades explícitas reutilizables. Los administradores de cada tipología
filtran los expedientes de sus unidades; compartir implementación no concede
acceso a datos de otra unidad.

Centros I+D conserva su aplicación `apps/centros_id`, sus tablas, permisos,
rutas, administración y base separada mediante el router existente. Vincula
unidades mediante contratos explícitos; no reemplaza al laboratorio docente.
No se crea una base ni un contenedor por cada laboratorio o centro registrado.

Es un monolito modular: las aplicaciones se ejecutan dentro del mismo proceso
Django y comparten capacidades declaradas. No son servicios desplegables de
forma independiente. Los ZIP que contienen aplicaciones autónomas siguen el
servicio aislado de microproyectos; no se importan como parte del sistema madre.

## Carga HTTP y recursos

Cada aplicación define sus URL operativas en `presentation/operativas_urls.py`.
`config/rutas_operativas.py` solo las compone y conserva su precedencia. Los
controladores diferidos se importan al atender su primera petición. Las
entradas públicas por tipología tampoco importan otras verticales durante la
composición de rutas. Django sí registra modelos, administración y señales al
arrancar; esa inicialización no equivale a consultar todos los datos o cargar
todas las páginas en cada petición.

Plantillas, CSS, JavaScript, fuentes e imágenes viven en sus aplicaciones.
Los nombres públicos de plantillas y URL de estáticos se mantienen. No copiar
un mismo recurso en varias aplicaciones: usar su namespace publicado.
`collectstatic` recopila los archivos para el servidor desde los propietarios.

## Persistencia y actualización sin pérdida

`apps/historial_modelos` mantiene la etiqueta Django histórica `webcitt`
exclusivamente para que las instalaciones existentes reconozcan las
migraciones aplicadas. No tiene modelos actuales, vistas ni administración.
Las tablas `webcitt_*`, nombres de tablas M2M y referencias SQL existentes
conservan su identidad; renombrarlas exigiría DDL innecesario. Esto no implica
que el código siga en la aplicación anterior.

La migración `webcitt.0330_propiedad_modular` traslada el estado completo de
modelos a sus propietarios. Cambia únicamente el propietario de los tipos de
contenido existentes, conservando sus ID, permisos, grupos, relaciones,
referencias genéricas e historial administrativo. También conserva el estado
y la versión de la capacidad de reservas al cambiar su identificador de
módulo. No copia, elimina ni recrea tablas de negocio. Los destinos en
conflicto bloquean la operación antes de modificar identidades.

Cada propietario inicia su historial con `0001_propiedad_modelos`, que depende
de ese traslado. Las siguientes modificaciones se generan y aplican en su
aplicación real. No borrar migraciones históricas, cambiar los nombres físicos
por estética, usar `--fake`, reinicializar bases o recargar datos sobre datos
administrados. Los catálogos y contenidos siguen editándose en sus interfaces
y servicios existentes; esta extracción no sustituye sus registros.

## Procedimiento de corte

1. Detener web, tareas y cualquier escritor; preparar una copia privada
   verificable de ambas bases y conservar los adjuntos y secretos existentes.
2. Revisar `check`, `makemigrations --check --dry-run`, el plan de migración y
   posibles tipos de contenido de destino. Ensayar el traslado en una copia
   completa, incluida su reversión. Nunca ejecutar pruebas contra datos reales.
3. Migrar con el rol de mantenimiento, para las dos bases configuradas,
   usando `python scripts/migrar_desarrollo.py` en el entorno local. En el
   servidor seguir [producción Linux](produccion-linux.md) y el procedimiento
   de mantenimiento autorizado de esa instalación.
4. Comparar filas, claves, permisos y restricciones; recopilar estáticos,
   reiniciar procesos y comprobar páginas, administración, cursos, PDF,
   multimedia y aislamiento entre unidades y Centros I+D.
5. Ante un fallo previo a nuevas escrituras, detener procesos y revertir el
   plan probado. Tras nuevas migraciones o escrituras, evaluar primero el
   plan inverso: no asumir que cualquier versión posterior es reversible.

El ensayo sobre copias locales verificó 289 tablas institucionales y 50 de
Centros I+D, con reversión exacta y una segunda actualización. Las evidencias
privadas se guardan en `var/`; no se publican datos ni credenciales. Las pruebas
de contrato están en `tests/architecture/` y las funcionales en
`tests/integration/`. La CI verifica arquitectura, señales, plantillas,
archivos, migraciones, JavaScript y PostgreSQL.

## Continuidad y producción

Las funciones nuevas pertenecen al propietario indicado en el mapa. La
composición transversal se declara en `integraciones`, con dependencias
explícitas; no importar el catálogo completo para resolver una función local.
Las migraciones nuevas deben preservar datos y tener un plan de despliegue.
Cambiar contenido institucional no requiere modificar código ni reemplazar
tablas. El registro de manifiestos documenta dependencias, no habilita permisos.

Esta separación no certifica por sí sola seguridad, capacidad bajo carga ni
disponibilidad del servidor universitario. Antes de publicar siguen siendo
necesarias la configuración concreta de dominio/TLS, roles y secretos,
retención de respaldos, monitorización, actualización de dependencias y una
prueba de carga representativa. Consultar [despliegue](despliegue-produccion.md).

Antecedentes conservados: [estructura anterior de webcitt](historial/estructura-webcitt-2026-10-12.md)
y [arquitectura previa a la extracción](historial/arquitectura-anterior-extraccion-2026-10-12.md).
