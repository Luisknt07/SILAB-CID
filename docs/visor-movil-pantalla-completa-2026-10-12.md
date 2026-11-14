# Visor móvil en pantalla completa — 12 de octubre de 2026

El visor cambiaba de bloque a cuadrícula al entrar en pantalla completa, pero no definía una columna que pudiera encogerse. La anchura mínima del encabezado expandía la columna implícita y el iframe; el contenedor exterior ocultaba el desbordamiento. El contenido interno recibía un ancho superior al celular y perdía parte de su lado derecho.

Se reprodujo con los estilos existentes y una lección representativa: en una ventana de 390 píxeles, encabezado e iframe alcanzaban 561 píxeles al entrar en pantalla completa y los controles quedaban fuera de la ventana. Al salir, recuperaban su ancho normal.

La corrección común en `detalle_visual.css` define una columna `minmax(0,1fr)`, permite encoger el contenido y reserva espacio para las acciones del encabezado. El iframe conserva el ancho del visor y la altura disponible utiliza `100dvh`, con respaldo `100vh`. Se mantienen los selectores estándar y WebKit. La plantilla renueva la versión del CSS para que los clientes reciban el cambio.

## Verificación

Chrome headless con un perfil exclusivo comprobó los estados normal, pantalla completa nativa y salida en 360×800, 390×844, 520×1100, 844×390 y 1366×768. La segunda comprobación usó emulación móvil en los cuatro primeros tamaños. Se verificaron por aserciones el ancho del iframe y encabezado, la visibilidad de controles, el video dentro del ancho disponible, la ausencia de desbordamiento del documento interior y la recuperación del tamaño original al salir.

En 390 píxeles, el contenido corregido permanece en 390; los controles están visibles. La prueba gráfica utiliza una reproducción estructural del visor y del aula con sus CSS reales, un título largo, video representativo y tabla wiki, sin cuentas ni contenido operativo. No equivale a una prueba en un teléfono físico o en Safari.

La página real del laboratorio de Logística y su CSS respondieron HTTP 200 con la versión corregida en el servidor local. Django check y revisión del diff correctos. No hay cambios de modelos, datos, contenidos académicos ni lógica de cursos; la solución se aplica al visor compartido de las unidades.

Evidencia privada fuera de Git: `var/visor-movil-20261012/`, con métricas y capturas antes/después. No se desplegó al servidor universitario. Recargar las páginas abiertas para recibir la versión nueva.
