# Fotos y miniaturas: verificación del 12 de octubre de 2026

## Diagnóstico

Las fotografías originales cargaban, pero los mosaicos de «Conoce la unidad», las miniaturas de «Fotos y videos» y las del mapa apuntaban a derivados JPEG rechazados con HTTP 404. Los archivos estaban presentes. La entrega protegida exigía un registro del archivo original y el derivado no tenía una fila propia.

El inventario de los campos ImageField del registro de medios públicos encontró 464 referencias en siete campos, sin originales ausentes: 12 imágenes de unidades, una de equipo, 18 imágenes de ejes, 408 fotos interiores, tres imágenes principales de Centros I+D, 20 imágenes de centros y dos planos. Este inventario comprueba existencia local; no certifica la disponibilidad de imágenes de servicios externos.

## Corrección común

`webcitt/domains/unidades/miniaturas.py` conserva los JPEG y sus tamaños (96, 160 y 480 píxeles). Añade a la URL una procedencia firmada que vincula original, carpeta, dimensión y archivo derivado. La firma es estable para reutilizar el enlace y no sustituye los permisos.

`webcitt/domains/portal/media.py` valida la firma y las rutas canónicas, comprueba que el original aún existe y aplica su autorización actual antes de entregar el JPEG. Ocultar, reemplazar o eliminar el registro original revoca también el acceso al derivado anterior. Las imágenes privadas conservan sus restricciones para GET, HEAD y peticiones con Range. Los archivos sin registro siguen bloqueados y las respuestas mantienen `private, no-store` y `nosniff`.

La corrección se aplica a todas las unidades que usan el generador común; no requiere migraciones, reimportar fotos ni modificar contenidos. Recargar las páginas genera los enlaces nuevos. Los enlaces antiguos sin procedencia continúan denegados por diseño.

## Verificación

- 32 unidades activas y 408 fotos interiores publicadas revisadas.
- 181 URL de miniaturas distintas verificadas por HTTP: todas respondieron 200 con JPEG. El total es menor que las referencias porque varias reutilizan la misma imagen.
- Las páginas reales de Logística respondieron 200: presentación con tres miniaturas firmadas y galería con 18 fotos cuyos enlaces se generan correctamente.
- 28 pruebas Django aprobadas en PostgreSQL QA efímero aislado: miniaturas, medios privados, presentación y galerías. Incluyen firmas alteradas, destino distinto, originales ocultos, eliminados o reemplazados, archivos ausentes y acceso privado por GET, HEAD y Range. El contenedor QA se retiró al terminar, sin volúmenes persistentes.
- Django check, ausencia de nuevas migraciones, Ruff y revisión de espacios del diff correctos.
- Auditoría de 4.078 archivos: cero errores y cero colisiones de nombres entre Windows y Linux; seis grupos de duplicados preexistentes identificados, sin modificaciones en este bloque.

Las evidencias locales y el runner PostgreSQL QA temporal se conservan fuera de Git en `var/fotos-miniaturas-20261012/`. La verificación usa HTTP y pruebas de aplicación; no se efectuó inspección visual en navegador en este bloque. No se desplegó al servidor universitario ni se cambiaron registros operativos.

## Despliegue

Mantener `/media/` detrás de la entrega protegida de Django. El proxy debe conservar la cadena de consulta de las miniaturas, incluida `origen`. No resolver el fallo publicando toda la carpeta de medios mediante un alias. La clave de firma debe ser estable entre procesos; al rotarla, recargar las páginas para obtener enlaces nuevos.
