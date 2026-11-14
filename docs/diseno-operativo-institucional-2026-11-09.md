# Interfaz operativa de reservas

La referencia visual son las capturas del Portafolio Institucional UPEC
aportadas por el usuario y el diseño previo del asistente. Se conservan las
imágenes, iconos, bloques de color y tres rutas. Se refina la jerarquía y la
lectura con los colores configurados de la institución. Las capturas son
referencias, no un manual oficial de marca.

Se consultó [Impeccable](https://github.com/pbakaus/impeccable), especialmente
sus recomendaciones para interfaces de operación y lectura: reducir decoración,
mantener jerarquía y estados visibles. No se instaló software externo.

## Decisiones

- Poppins/Montserrat del sitio, cuerpo de 16 px y ayudas de 14 px en el asistente.
- Verde institucional en encabezados, acciones y selección; amarillo en franjas,
  tutoriales y ayudas. Los colores se toman de las variables de marca existentes.
- Superficies de lectura claras; sombras suaves y un degradado sobre las fotos
  para asegurar el contraste de sus leyendas. Cabecera sin rejillas animadas.
- Las cabeceras principales conservan verde sólido. Las opciones secundarias de
  finalidad, guía y programación tienen fondo blanco, título oscuro y descripción
  alineada. Se diferencian por borde e icono sobre un fondo marfil discreto.
  Al elegir una opción, el borde y un acento lateral son verdes; solo el icono
  lleva amarillo. Se mantienen los radios visibles y el foco de teclado.
- Las categorías de visita usan la misma jerarquía: tarjeta clara, acento lateral
  y un indicador pequeño para la elegida, sin grandes superficies verdes.
- Las áreas conservan portadas fotográficas grandes (180–230 px), con la foto
  cargada o las referencias del catálogo, rotuladas como referenciales. Se evita
  repetir la escena genérica de fabricación. Solo si no hay una imagen pertinente
  se presenta la portada institucional con marca, código e icono de actividad.
  La cuadrícula admite como máximo cuatro columnas. La tarjeta muestra nombre
  de 15 px, descripción breve de dos líneas, aforo y regla técnica. La selección
  vuelve a ser una casilla visible sobre la foto; «Ver área» abre la ficha.
  Descripción, ubicación, mobiliario, indicaciones y todos los modelos asociados
  se consultan en la ficha modal; no se despliegan dentro de la cuadrícula.
- Plano, video y 360° abren el mismo visor modal amplio, de hasta 1840 px y
  ajustado a la altura de la ventana. Los iframes se cargan al abrir y se retiran
  al cerrar. El cierre devuelve el foco al origen y Tab queda dentro del diálogo.
  Sus botones usan verde, amarillo y verde oscuro con texto en contraste.
- Tres rutas con sus imágenes originales, preparación, tutoriales y acciones;
  altura de imagen acotada a la ventana y bloque seleccionado visible.
- Paneles con bordes finos y radios de 8 a 14 px. La sección de clasificación
  recupera encabezado verde y franja amarilla.
- Propósito y participantes tienen contenedor delimitado, cabecera verde y
  separador amarillo. La tabla usa encabezados verdes y filas alternas.
- Continuar y elegir ruta usan verde sólido. Volver, añadir y otras acciones
  secundarias usan amarillo. Se mantienen los estados de error y deshabilitado.
- Se retiró la prioridad `!important` de la antigua capa de superficies y campos
  que impedía aplicar el refinamiento. La capa final controla su apariencia.
- El calendario conserva la agenda y sus validaciones, con vistas Día/Semana;
  móvil abre por día. Los bloques libres aprovechan todo el ancho. Solo las horas
  con actividad reservan una franja lateral de 88 px, con etiquetas de 11 px sin
  cortar palabras. Las filas vacías usan 48 px. Las reservas reciben al menos
  128 px repartidos en las horas que ocupan; solo se amplían las filas necesarias
  y todas las columnas comparten la misma escala. Las reservas simultáneas que
  no caben con texto legible se consultan mediante «+N más»; no se descartan.
  El buscador mensual y los detalles usan 320–420 px en escritorio. Las celdas
  del mes ajustan su ancho a cada columna y miden 44 px de alto para no superponerse.
  El panel se reorganiza en pantallas pequeñas.
  Se conserva el pie de navegación y cambiar de vista no borra el horario elegido.
- La capa se limita a reservas, visitas, expediente y revisión de guía, sin
  cambiar los documentos institucionales exportados ni el sitio público.

La capa está en `reservas_institucional.css` y se carga después de los estilos
de los componentes desde `reserva_equipos.html`. La geometría responsive sigue
perteneciendo a cada componente. No cambiar por separado el tamaño del texto de
las tarjetas del calendario: depende de su altura y del número de reservas.

## Verificación

Comprobación de Django, sintaxis JS y CSS, respuesta HTTP de la hoja nueva y
pruebas de DOM de los cinco pasos, visitas internas/externas y participantes.
Se revisaron las reglas de columnas entre 320 y 2560 px y los cálculos de ajuste
de altura. Las pruebas JS incluyen la distribución, el cambio de vista, la
compatibilidad, las reservas simultáneas y la navegación por jornadas habilitadas.
Las etiquetas se contrastan con Poppins del proyecto y el espacio útil disponible.
Estas verificaciones no sustituyen una revisión visual en navegador.

## Política económica unificada — 10 de noviembre de 2026

En recursos, servicios y visitas, la UPEC asume íntegramente espacios,
mobiliario, equipos, software y personal, incluidos diseño y guías. Los valores
referenciales permanecen para reportar el aporte institucional; no son cargos
al usuario. Solo se cobran materiales provistos por la unidad y realmente
consumidos. El desperdicio del proceso queda a cargo del laboratorio. Los
impuestos, si la unidad ya los tiene configurados, se calculan exclusivamente
sobre el subtotal de materiales, redondeado a centavos.

La cobertura es independiente del segmento, la verificación del perfil y las
banderas antiguas de cobro. La identificación, los roles y los permisos siguen
validándose por sus reglas propias. Las visitas incluyen la protección personal
prevista por visitante en la estimación y registran los guías como aporte UPEC.

El panel recalcula las reservas pendientes o confirmadas desde las cantidades
aprobadas de materiales, sin admitir precios libres ni reducir la cobertura.
El cierre impide registrar ingresos superiores a la liquidación de materiales;
los ajustes a la baja mantienen su justificación y trazabilidad. Los comprobantes
y reportes conservan el desglose emitido y la liquidación real. No se reescriben
automáticamente las cotizaciones ni los cierres históricos. La migración 0004
solo actualiza metadatos/defaults de campos heredados, sin SQL de modificación
de tablas ni de datos.

Regresión: alcohol 100 mL × USD 0,006 + espacio 8 + equipo 18 + personal 12
produce referencia USD 38,60, aporte UPEC USD 38,00 y cargo USD 0,60, con
impuestos desactivados. Se verifica con perfiles internos y externos.

Validación: 213 casos de integración de reservas, visitas, roles y reportes,
con actualización de expectativas que antes exigían cobros por recursos; los
26 casos económicos y de cierre se revalidaron sin fallos, además de 6 casos
de regresión de cobertura y 340 pruebas JavaScript. Django y las 485 plantillas
no registraron errores. Las pruebas SQL usaron contenedores temporales separados
de las bases operativas. La comprobación de interfaz ejecutó el cálculo real
del asistente, incluidas programación repetida, materiales propios e IVA.

## Mis reservas y Reservas y agenda — 10 de noviembre de 2026

Las tres agendas comparten `agenda_distribucion.js`: las filas libres miden
48 px y solo se amplían las necesarias para dar al menos 128 px a las tarjetas.
El cálculo alinea horas, eventos y selección, incluidas las franjas de minutos.
El calendario de solicitud conserva su comportamiento y delega su escala en
este módulo. No se modifica la disponibilidad ni la autorización de reservas.

Mis reservas y la agenda de gestión usan `agenda_unificada.css`, con texto de
13 px en títulos y 12 px en horas y estados, mes de 44 px por celda y panel
lateral de 320–420 px. Se retiró un `display: grid !important` antiguo que
impedía reorganizar Mis reservas en móviles. La vista móvil abre por día; la
vista Semana sigue disponible y conserva el día y la selección. El historial
sincroniza el desplazamiento horizontal entre horas y cabeceras.

Las reservas simultáneas se resumen con «+N más» y siguen disponibles en el
listado del día. Gestión incorpora un panel lateral del día con títulos completos
y las mismas acciones y permisos del expediente; no se crean rutas alternativas.
Los botones de bloqueo y el acceso al expediente se mantienen. Los atributos
HTML de las tarjetas de gestión se emiten como atributos, sin traducciones de
fragmentos de sintaxis HTML.

Verificación: 347 pruebas JavaScript; renderizado de las plantillas reales con
datos sintéticos y consultas SQL bloqueadas; cambio Día/Semana, reanudación del
panel, solapamientos, acciones conservadas, foco y escape de nombres. Se comprueba
la cascada CSS entre 320 y 2560 px y se compilan las 486 plantillas Django.
Estas comprobaciones no sustituyen una revisión visual en navegador.
