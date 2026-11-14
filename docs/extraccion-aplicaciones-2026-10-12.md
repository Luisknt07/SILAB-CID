# Retirada de webcitt y propiedad de aplicaciones

La carpeta `webcitt/` se retiró. Sus modelos, administración, funciones HTTP,
comandos, plantillas y estáticos pertenecen a aplicaciones reales bajo `apps/`.
El [mapa de aplicaciones](../apps/README.md) y la
[arquitectura vigente](arquitectura.md) son las referencias de mantenimiento.

## Conservación

- 182 modelos trasladados, incluidos los dos proxies existentes, con sus
  nombres de tablas y relaciones M2M conservados.
- 628 métodos de esos modelos presentes después del traslado.
- 3.406 archivos originales inventariados y localizados en sus destinos.
- 1.712 archivos binarios comparados por SHA-256, sin alteraciones.
- 259 rutas operativas conservadas con nombre, controlador y precedencia;
  sus definiciones residen en cada aplicación propietaria.
- 424 modelos del proyecto, incluidos proxies por tipología, y 21 manifiestos.

Los paneles de modelos trasladados se implementan en sus aplicaciones
propietarias. Los adaptadores por tipología reutilizan capacidades comunes y
acotan los expedientes por unidad. No se crea una base o contenedor por cada
laboratorio registrado. Centros I+D conserva su aplicación y base separadas.

Los comandos mantienen sus nombres públicos. Autenticación y recursos comunes
están en `core` y `portal`; inventario, reservas, formación y documentos tienen
sus propias entradas. Los cálculos productivos y los simuladores de campo
quedaron en sus verticales correspondientes. El material de los cursos y el
código autónomo del kit docente se conservan.

## Corte de bases

La migración `webcitt.0330_propiedad_modular` transfiere el estado Django y
actualiza los propietarios de ContentType manteniendo sus ID. No recrea ni
renombra tablas de negocio. Conserva permisos, grupos, Guardian, referencias
genéricas e historial. También conserva la configuración de suspensión y
la versión de la capacidad de reservas.

El historial anterior está en `apps/historial_modelos`, con etiqueta técnica
`webcitt` y cero modelos activos. Esa etiqueta y los nombres físicos antiguos
se mantienen deliberadamente para actualizar instalaciones existentes.

El ensayo final con copias privadas verificó 289 tablas institucionales y 50
de Centros I+D: filas, permisos y restricciones idénticos, reversión exacta y
segunda actualización correcta. Después se aplicó el corte local con los
roles de mantenimiento configurados. La comparación de ambas bases confirmó
la conservación de filas, permisos, restricciones y estados de capacidad.
Los dos aliases quedaron sin migraciones pendientes; `makemigrations --check`
no detecta diferencias de estado.

## Validación

| Comprobación | Resultado |
| --- | --- |
| Suite general PostgreSQL | 3.898 pruebas, sin fallos; 13 omitidas según el perfil |
| Perfil con dos bases y Centros I+D | 293 pruebas, sin fallos |
| JavaScript | 195 pruebas, sin fallos |
| Entregas reproducibles | 10 pruebas, sin fallos |
| Ruff y Django check | Correctos |
| Auditoría de repositorio | 0 errores y 0 colisiones de nombres |
| Plantillas activas | 386, sin referencias rotas |
| Señales | 33 contratos y conexiones; 0 hallazgos; archivos de receivers con huella propia |
| Rutas y manifiestos | Contratos de propiedad y carga selectiva aprobados |
| HTTP local | Portal, unidades, Logística, cursos, galería, Centros I+D, login y estáticos: 200 |
| Recursos revisados por HTTP | 13 imágenes y 16 scripts, sin fallos |
| Administrador con datos reales | 1.017 pantallas, 0 fallos, sesión volátil y escrituras bloqueadas |

Los controles impiden reintroducir importaciones del paquete retirado,
administradores fuera de su propietario o receivers nuevos sin revisión.
Se probaron instalación desde cero, actualización de bases existentes y
reversión. Las pruebas usaron PostgreSQL temporal y archivos aislados; los
contenedores de QA se retiraron al terminar.

Los archivos locales de los kits se conservaron en sus destinos o en el
archivo privado. Secretos, SQLite locales, entornos, cachés, adjuntos y copias
de bases quedan fuera de Git, de la imagen y de la entrega del código.

## Publicación

El servidor local se reinició con los estáticos vigentes en
`http://127.0.0.1:8000/`. No se desplegó al servidor universitario. Su publicación
requiere concretar dominio/TLS, secretos, roles, copias operativas,
monitorización y validación de carga y dependencias del entorno final.
Esta extracción no certifica por sí sola todos los requisitos de producción.

Evidencia privada: `var/extraccion-apps-20261012/`. El inventario de código
actualizado está en [inventario-arquitectura.json](inventario-arquitectura.json).
El historial Git identifica el commit de esta entrega.

## Revisión posterior — 13 de octubre de 2026

Se corrigió el HTTP 404 de `/favicon.ico`: la entrada pertenece al portal,
resuelve el icono existente mediante el almacenamiento estático configurado y
admite GET/HEAD. La plantilla base también declara el icono. Se actualizaron
tres rutas de documentación de los cargadores y la descripción del contrato
de unidades. El inventario vigente registra 292 rutas compuestas; se mantienen
los 259 controladores operativos y los 424 modelos.

Comprobaciones repetidas después de la extracción:

| Comprobación | Resultado |
| --- | --- |
| Django check, Ruff y estado de modelos | Sin errores ni diferencias |
| Migraciones de default y centros | Sin pendientes en ambos aliases |
| Arquitectura y manifiestos | 22 pruebas aprobadas |
| Seguridad, operación y manifiestos | 42 pruebas aprobadas; incluye casos de la fila anterior |
| Portal y rutas, PostgreSQL temporal | 17 pruebas aprobadas; contenedor retirado |
| JavaScript y entregas | 195 y 10 pruebas aprobadas |
| Archivos, plantillas y señales | 4.233 archivos, 386 plantillas y 33 contratos; sin hallazgos bloqueantes |
| Importación de controladores diferidos | Los 259 destinos existen y son invocables |
| HTTP local | 38 páginas/sondas y 401 recursos enlazados sin fallos; incluye 25 fichas públicas |
| Galerías de las 32 unidades activas | 408 referencias de fotos; 204 URL locales distintas de originales/miniaturas responden HEAD 200, con imagen y longitud positiva |
| Dependencias Python fijadas | 38 paquetes; pip-audit estricto con hashes, sin vulnerabilidades conocidas reportadas |

La suite general de 3.898 pruebas y la multibase de 293 corresponden al cierre
del apartado anterior. En esta revisión se repitieron los controles dirigidos
al cambio; no se presentan esas suites como nuevas ejecuciones. Las galerías
también contienen 358 referencias a videos externos: su disponibilidad y la de
sus miniaturas externas no forman parte de la comprobación de imágenes locales.
La revisión HTTP no sustituye una inspección visual ni una prueba de carga.

El verificador de seguridad de base aprueba el rol y el esquema exclusivo del
alias `centros`. En `default` rechaza la conexión local por sus privilegios
administrativos. Antes de producción debe configurarse el rol web restringido
contemplado en la [guía de despliegue](produccion-linux.md), separado del rol de
migraciones. Este requisito sigue abierto. El análisis Python no cubre las
bibliotecas del navegador, la imagen Docker ni las alertas de otras ramas.

Evidencia local adicional, excluida de Git: `http-revision-20261013.json`,
`galerias-revision-20261013.json`, `dependencias-revision.json`,
`repositorio-revision.json` y `pruebas-focalizadas.log`, dentro de
`var/extraccion-apps-20261012/`.
