# Video propio de bienvenida

Primera lección: **Bienvenida: tu ruta para crear una aplicación logística**.

Material original de ocho escenas, ilustraciones dibujadas para el curso y narración sintética española (Microsoft Sabina, es-MX). No representa a un docente ni imita a una persona. No utiliza fotografías, música, videos ni voces de terceros descargados de Internet.

La bienvenida explica las cinco unidades y 40 horas, el acceso sin programación previa, el caso ficticio Andina Distribución, el recorrido de estudio y las evaluaciones. Incluye la conexión MCP de consulta preparada, alternativas sin plan de pago obligatorio y cómo pausar o solicitar ayuda.

## Integración

- builder.get_welcome_video() devuelve bytes del MP4 versionado; no necesita FFmpeg en el servidor.
- builder.WELCOME_FILENAME: bienvenida-logistica-ia.mp4.
- builder.get_welcome_metadata(): duración medida, formato, tamaño, huella y escenas.
- Carga de estudio: 5 minutos. Esta bienvenida abre la primera unidad; no añade una unidad ni cambia las 40 horas.
- Poster público: portal/img/cursos/logistica-ia/bienvenida-poster.png.
- Subtítulos públicos: portal/img/cursos/logistica-ia/bienvenida-es.vtt.
- El video contiene subtítulos abiertos. El VTT separado sirve para consulta o como pista opcional: no añadas el atributo default al elemento track del reproductor, para que no aparezca automáticamente encima de los subtítulos ya incorporados. Advierte que activar esa pista duplica el texto visible; la transcripción completa también está disponible.

## Fuentes editables y reproducción

- escenas.json: texto y guion original.
- sintetizar_voz.ps1: genera WAV intermedios con una voz española instalada; no sustituye una voz inglesa.
- renderizar.py: dibuja escenas con Pillow, crea subtítulos y codifica H.264/AAC usando FFmpeg.
- transcripcion.md: narración completa en texto.
- assets/: MP4 final, copia fuente del poster y VTT; los dos últimos se copian a static para el reproductor.
- metadata.json: resultados de la generación.
- .qa/: intermedios y herramientas temporales, excluidos de Git.

Para regenerar se necesita Python, Pillow y FFmpeg. En Windows, el script de voz utiliza SAPI; hay que ejecutarlo en un entorno que permita acceder a la voz instalada. No abre ventanas ni utiliza el micrófono. Si no hay voz española disponible, debe prepararse una versión explícitamente subtitulada; no insertar una voz inglesa.

~~~powershell
powershell.exe -NoProfile -WindowStyle Hidden -File sintetizar_voz.ps1 -Directorio RUTA_A_ESTA_CARPETA
python renderizar.py --ffmpeg RUTA_A_FFMPEG --public-dir RUTA_A_STATIC_PORTAL_IMG_CURSOS_LOGISTICA_IA
~~~

La versión generada usa FFmpeg 7.1 distribuido en la rueda oficial imageio-ffmpeg 0.6.0 de PyPI. Sólo se utilizó la herramienta para codificar; no se redistribuye el ejecutable FFmpeg. Pillow utiliza las fuentes Arial del equipo; el paquete no distribuye archivos de fuentes.

Los tiempos del VTT se reparten proporcionalmente por palabras dentro de cada narración de escena; son subtítulos de apoyo, no una alineación fonética. El texto también se presenta completo en la transcripción. Las escenas reservan espacio para subtítulos y utilizan texto estable con fundidos sencillos.

Referencias de herramientas: https://pypi.org/project/imageio-ffmpeg/0.6.0/ y https://ffmpeg.org/ffmpeg-filters.html. No se usaron estos sitios como contenido narrativo del curso.

El guion, ilustraciones y código propios se pueden reutilizar bajo la licencia MIT del material docente del repositorio. Las marcas y herramientas mantienen sus derechos. La generación del material no implica aval de proveedores de IA ni certificación de Python, Django o MCP.

## Diagramas de consulta del aula

`diagramas.py` conserva las fuentes de ocho diagramas SVG accesibles y sus PNG equivalentes para los PDF. Ejecutarlo regenera sólo esos nombres en `static/portal/img/cursos/logistica-ia/`; no modifica el video, el poster ni los subtítulos. Utiliza Arial instalada o DejaVu Sans en Linux, sin distribuir archivos de fuentes. Los recursos terminados están versionados y no se generan durante una petición.
