# Aplicación compartida heredada

`webcitt` es la aplicación Django original del SLCID. Sigue siendo propietaria de las tablas históricas de unidades, reservas, cursos e inventario. No es una copia de `apps/` y no se puede retirar mientras esas funciones dependan de ella.

La estructura combina las convenciones de Django con módulos internos para dividir una aplicación que creció. Django admite modelos, administración, plantillas y estáticos dentro de una aplicación; usar paquetes `models/` y `admin/` permite separar archivos por tema. Véase la [documentación oficial de aplicaciones](https://docs.djangoproject.com/en/5.2/ref/applications/).

## Dónde está cada responsabilidad

| Ubicación | Contenido actual |
| --- | --- |
| `models/` | Modelos históricos, divididos por función; `__init__.py` los registra y conserva importaciones compatibles. |
| `migrations/` | Historial versionado de cambios de esquema y datos. Se conserva para actualizar instalaciones existentes. |
| `admin/` | Registro y gestión administrativa de esos modelos. |
| `domains/` | Controladores, formularios y funciones de usuarios, portal y operación de unidades. No es todavía una capa de dominio pura. |
| `routing/` | Rutas operativas de compatibilidad; las vistas diferidas se importan al atender su primera petición. |
| `services/codigos_reserva.py` | Asignación y reconciliación de códigos, compartida por señales y comandos. |
| `workflows/reservas.py` | Estados y reglas de transición de reservas, reutilizados por modelos, vistas y tareas. |
| `management/` | Comandos y paquetes de contenidos; no se ejecutan por abrir una página. |
| `middleware/` | Controles que intervienen en las peticiones, según `config/settings.py`. |
| `templates/`, `static/`, `templatetags/` | Presentación compartida y recursos del navegador. |
| `tests/` | Pruebas del legado y sus contratos de integración. |
| `apps.py`, `signals.py`, `checks.py` | Registro de la aplicación, señales y comprobaciones. |
| `adapters.py`, `context_processors.py`, `template_loaders.py` | Integración de acceso social, contexto de plantillas y carga de plantillas con CSP. |
| `manifiesto.py`, `urls.py` | Declaración del legado y composición de entradas públicas de las aplicaciones. |

`__pycache__/` contiene caché regenerable de Python; no son fotografías ni datos de usuarios. `.ruff_cache/` es caché del analizador. Ambos están excluidos de Git y del contexto Docker. Ruff se configura ahora para utilizar `var/cache/ruff/`; sus antiguas carpetas locales pueden retirarse sin afectar datos. Python puede volver a crear `__pycache__/` al ejecutar el código.

## Separación real y trabajo pendiente

`apps/centros_id` tiene sus propios modelos y migraciones y usa la base `centros` cuando se habilita el router correspondiente. `apps/laboratorios`, `apps/plantas_piloto`, `apps/centros_experimentales` y `apps/observatorios` conservan modelos proxy sobre tablas de `webcitt`: sus entradas y permisos están separados, pero aún no toda su persistencia ni operación. Crear más carpetas no cambia esa dependencia.

Los modelos se registran al iniciar Django; eso no implica consultar todas sus filas ni ejecutar todas las funciones en cada página. Las rutas heredadas usan `vista_diferida`, pero el servidor, las señales y parte de la operación siguen compartidos. Los contratos se comprueban en `tests/test_carga_selectiva.py` y `tests/test_manifiestos_modulares.py`.

## Criterio para continuar

1. Asignar cada nueva función al propietario de `apps/` y a una capacidad concreta. Reutilizar las tablas y contratos existentes cuando corresponda; no duplicarlos para aparentar independencia.
2. Extraer funciones coherentes del legado con sus rutas, permisos, plantillas y pruebas, conservando adaptadores públicos durante la transición. No mover archivos entre `domains`, `services` y `workflows` solo por su nombre.
3. Tratar el traslado de modelos y tablas como un bloque independiente, con migraciones verificadas, conciliación de datos y reversión. Mantener las identidades históricas hasta completar ese corte.
4. Comparar inventario y contratos antes y después. No usar reemplazos globales de `webcitt`: su etiqueta figura en tablas, migraciones, permisos y referencias. Django advierte que cambiar la [etiqueta de una aplicación con migraciones aplicadas](https://docs.djangoproject.com/en/5.2/ref/applications/#django.apps.AppConfig.label) produce cambios incompatibles.

La [arquitectura vigente](../arquitectura.md), la [estructura objetivo](../estructura-objetivo-sistema-laboratorios.md) y la [ruta de cierre](../ruta-cierre-reestructuracion-y-verticales.md) distinguen implementación actual y trabajo pendiente. Esta revisión del 12 de octubre de 2026 inventarió 182 modelos heredados y 259 rutas operativas; no equivale a extraerlos ni a certificar cada flujo funcional.

En esta revisión pasaron las 22 pruebas de carga selectiva y manifiestos, sin bases de prueba ni cambios de datos. Los inventarios de metadatos se conservan fuera de Git en `var/estructura-webcitt-20261012/`. No se renombraron paquetes, tablas, permisos o migraciones.
