# Aplicaciones del sistema

El proyecto madre es `config/`. Compone aplicaciones instaladas, rutas y
políticas. Cada aplicación es dueña del código y de las migraciones futuras
de sus modelos.

| Aplicación | Responsabilidad |
| --- | --- |
| `core` | Usuarios, autenticación, periodos, identidad e infraestructura básica. |
| `configuracion_institucional` | Catálogos, presentación, calendario y capacidades con historial. |
| `portal` | Inicio, noticias, servicios, normativa y presentación institucional. |
| `directorio_unidades` | Identidad, clasificación, sedes y dependencias de unidades. |
| `gestion_unidades` | Fichas, espacios, responsables, contenido, configuración e indicadores comunes. |
| `recursos` | Equipos, inventario, mantenimiento, software, archivos y aplicaciones anexas. |
| `reservas` | Agenda, solicitudes, guías, aprobación, ejecución, acceso y visitas. |
| `formacion` | Asignaturas, cursos, matrículas, evaluaciones, certificados, prácticas y partidas. |
| `documentos` | Expedientes, requisitos, informes y seguimiento de mejoras. |
| `finanzas` | Proveedores, clientes, compras y movimientos financieros. |
| `laboratorios/operacion` | Perfiles de laboratorio, fabricación, consumibles y simulación logística. |
| `plantas_piloto/operacion` | Producción, recetas, lotes, calidad y planificación. |
| `centros_experimentales/operacion` | Ejes, ciclos y registros de producción de campo. |
| `observatorios/operacion` | Fuentes, indicadores, tableros, publicaciones y solicitudes de datos. |
| `centros_id` | Centros I+D, investigadores, capacidades, proyectos, resultados y servicios científicos. |
| `integraciones` | Composición explícita de capacidades por tipo de unidad y auditorías entre aplicaciones. |
| `historial_modelos` | Migraciones históricas exclusivamente; no define modelos ni funciones operativas. |
| `conexiones` | Opcional (`SLCID_MODULO_CONEXIONES`): dispositivos conectados de las unidades, canales y series de medición. |

Las raíces de `laboratorios`, `plantas_piloto`, `centros_experimentales` y
`observatorios` contienen las entradas públicas y los paneles por tipología.
Sus proxies filtran por unidad y aprovechan capacidades comunes. El subpaquete
`operacion` es una aplicación Django real, con modelos y migraciones propias;
no es un segundo ejemplar de cada laboratorio.

Convenciones internas: `models/` para persistencia, `services/` y `workflows/`
para reglas, `presentation/` para HTTP, `admin/` para administración,
`management/commands/` para tareas, `templates/` y `static/` para recursos.
Las pruebas integradas están en `tests/integration/`, los contratos de
arquitectura en `tests/architecture/` y las pruebas específicas existentes en
cada aplicación. No crear otro contenedor general de funciones.

Un módulo opcional se instala por despliegue con su variable de entorno;
apagado no tiene tablas, rutas ni administración, y ninguna otra aplicación lo
importa. `conexiones` es el primero: su [guía](conexiones/README.md) describe
el patrón (`config/settings.py`, `config/modulos.py`, `config/rutas_aplicaciones.py`).

Los estáticos se recopilan con huella de contenido, compresión y derivados
WebP de las imágenes pesadas (`core/estaticos.py`); los originales conservan
su nombre y su ruta.

Las URL de estáticos y las rutas públicas conservan sus nombres. Django busca
los recursos en la aplicación propietaria. Los datos de ejecución van a
`var/`; secretos, bases y adjuntos locales quedan fuera de Git y de la imagen.

Para actualizar, revisar [arquitectura y migraciones](../docs/arquitectura.md).
