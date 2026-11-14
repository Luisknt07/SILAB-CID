# Visor del catálogo de cursos: diagnóstico y recuperación

Revisión del 12 de octubre de 2026 para laboratorio-logistica-comercio-internacional.

## Diagnóstico observado

La captura comunicada muestra nueve actividades y un marco gris. Con el código y la base local actuales, el catálogo muestra dieciséis actividades para administración y ocho para público. La vista devuelve HTTP 200 y X-Frame-Options SAMEORIGIN; no se encontró un error del servidor ni se reprodujo el bloqueo original en esta versión. No se atribuye el fallo original a caché, permisos o datos sin evidencia adicional.

Se comprobó el recorrido real con Chrome headless y un perfil temporal exclusivo. El navegador interactivo no estaba disponible. El servidor QA escuchó únicamente en 127.0.0.1:8001, con lectura administrativa local y registro de visitas deshabilitado para esta comprobación; esos ajustes viven en var y no forman parte del producto.

## Correcciones

El menú comparaba únicamente la ruta de la página cargada. Todas las categorías comparten la ruta del catálogo y se diferencian por categoria: al navegar dentro del marco, podía marcarse el catálogo general en lugar de la categoría seleccionada. Se compara ahora la consulta exacta, luego la categoría conservada al buscar o paginar y finalmente el catálogo sin categoría.

El navegador puede bloquear un iframe sin disparar onerror. Para las rutas nativas de cursos del mismo origen, se comprueba también el documento recibido al terminar la carga y se ofrece recuperación si resulta inaccesible. Una carga que no termina en veinte segundos ofrece el mismo aviso. Aparecen Reintentar y Abrir en otra pestaña; los eventos antiguos nunca reemplazan una selección nueva. Los sitios externos conservan su tratamiento previo.

La regresión ampliada detectó además que cargar_ejemplos_formacion podía duplicar un curso manual al comparar mayúsculas acentuadas bajo la colación C. Se sustituyó la comparación dependiente de la base por normalización NFC, espaciado y casefold en Python; preparar_logistica_formacion comparte el mismo criterio. La búsqueda está aislada por unidad y lee sólo PK/nombre en lotes de mil mediante SELECT con LIMIT; conserva el primer registro, códigos, textos, estados e historial. No se ejecutó una nueva carga sobre la base operativa.

Se actualizó la versión del script en la plantilla para renovar la caché del cliente. No se relajaron cabeceras, permisos, aislamiento, publicación ni matrícula; no hubo migraciones ni modificaciones de contenidos o datos académicos.

## Verificación

Chrome completó nueve comprobaciones: catálogo, categoría de cursos cortos, webinars, regreso al catálogo, segunda página, búsqueda, ficha nativa, recuperación ante un bloqueo real y regreso final al catálogo. Para provocar el bloqueo se solicitó una ficha inexistente: conservó HTTP 404 y DENY, y el visor mostró las opciones de recuperación. Se verificó la nueva versión del script.

Las ocho pruebas nuevas de JavaScript cubren documento bloqueado, onerror, recuperación, temporizador, eventos obsoletos, categorías y recursos externos. Las 195 pruebas JavaScript del repositorio pasaron. Las 100 pruebas Django de regresión pasaron en PostgreSQL aislado. La regresión Django comprueba además que catálogo, filtros y fichas públicas admitan SAMEORIGIN incluso con DENY global, y que un borrador anónimo siga rechazado.

La instancia PostgreSQL propia y el servidor de comprobación fueron detenidos; se retiró sólo su directorio de datos, conservando evidencias. Ruff y Django check correctos; no hay nuevas migraciones. La simulación final sobre la base local informó cero programas/borradores nuevos y conservó sus catorce fichas existentes.

Evidencia privada: var/cursos-visor-20261012, excluida de Git. Incluye diagnóstico HTTP, resultados del navegador, capturas, registros y pruebas aisladas. El fallo original no pudo reproducirse con la versión actual; si persiste en otra instancia, comprobar la URL y respuesta concretas y reiniciar su proceso Django para cargar el código actualizado. El servidor local normal estaba detenido: se inició en 127.0.0.1:8000 con configuración habitual y recarga automática, sin autenticación QA. Su catálogo respondió HTTP 200/SAMEORIGIN después del cambio. La publicación Git no despliega al servidor universitario.
