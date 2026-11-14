# Andina Distribución: tu primera aplicación logística

Kit del curso **Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial**. Nivel introductorio, 40 horas y cinco unidades. No se exige experiencia previa en programación: se trabaja con una plantilla funcional, cambios pequeños y acompañamiento.

Las 40 horas se distribuyen en cinco unidades de 8 horas **totales**, incluyendo lecturas, videos, archivos, práctica y evaluación del aula. Las guías siguientes acompañan el laboratorio: unidades 1 a 4, 4 h 50 min cada una; unidad 5, 3 h de laboratorio y 1 h 50 min de proyecto final. Estos tiempos ya están incluidos en las 8 horas de cada unidad; no se suman aparte. Sigue el orden del aula y utiliza guias/unidad_01.md a guias/unidad_05.md cuando llegues a la actividad correspondiente.

Andina Distribución es una organización completamente ficticia. El caso representa un almacén de materiales de empaque y demostración. Ningún dato describe existencias, usuarios, empresas o servicios reales de la UPEC.

## Qué puedes hacer

Registrar productos, entradas y salidas; consultar existencias y mínimos; revisar el historial; importar un catálogo CSV compatible con Excel; exportar datos; diferenciar un rol de consulta y otro de operación. La conexión MCP opcional sólo consulta existencias y productos bajo mínimo.

Este es un prototipo educativo para ejecutar en tu computador. Funciona sin IA. No integra facturación, lotes, varias bodegas, valoración contable, equipos físicos, optimización de rutas ni operaciones institucionales. No lo publiques con esta configuración: contiene DEBUG local y no aborda despliegue de producción.

## Antes de empezar

Necesitas Python 3.11 o 3.12, navegador, editor de texto y conexión para descargar dependencias. Una IA con suscripción no es obligatoria. Si utilizas un asistente, elige uno disponible y utiliza únicamente estos datos ficticios. Las condiciones de los proveedores pueden cambiar; no se garantiza una cuota gratuita determinada.

La aplicación base usa Django 5.2 LTS; las prácticas se han probado con Django 5.2.17. El SDK MCP 2.3.0 se instala únicamente para la unidad 4. Las referencias oficiales están en fuentes.md.

## Instalación en Windows (PowerShell)

Descomprime el kit en una carpeta propia. Abre PowerShell en la carpeta que contiene manage.py. Ejecuta cada línea por separado:

~~~powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py preparar_demo
.venv\Scripts\python.exe manage.py crear_usuario operador --rol operacion
.venv\Scripts\python.exe manage.py crear_usuario lector --rol consulta
.venv\Scripts\python.exe manage.py test inventario
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
~~~

Si tienes Python 3.12, sustituye únicamente py -3.11 por py -3.12. Los comandos usan la ruta explícita del intérprete para no cambiar la política de ejecución de PowerShell. La contraseña se escribe de forma oculta y se solicita dos veces; elige una propia, larga y diferente para cada usuario.

Abre http://127.0.0.1:8001/ e ingresa con operador. Mantén la terminal abierta. Para detener el servidor, pulsa Ctrl+C. Para volver a empezar otro día, ejecuta únicamente la última línea.

## Instalación en Linux

Con Python 3.11 o 3.12 y el componente venv instalado en el equipo:

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py preparar_demo
.venv/bin/python manage.py crear_usuario operador --rol operacion
.venv/bin/python manage.py crear_usuario lector --rol consulta
.venv/bin/python manage.py test inventario
.venv/bin/python manage.py runserver 127.0.0.1:8001
~~~

Cuando las guías digan python, usa .venv\Scripts\python.exe en Windows o .venv/bin/python en Linux. Puedes activar tu entorno si ya conoces ese procedimiento.

## Comprobación inicial

En una base nueva, después de preparar_demo:

| Código | Producto ficticio | Existencia | Mínimo | Unidad |
|---|---|---:|---:|---|
| AD-001 | Caja corrugada mediana | 17.00 | 10.00 | UN |
| AD-002 | Etiqueta adhesiva | 20.00 | 30.00 | UN |
| AD-003 | Film de embalaje | 9.25 | 5.00 | KG |
| AD-004 | Cinta de empaque | 4.00 | 8.00 | UN |

El tablero muestra **4 productos, 2 bajo mínimo y 0 sin stock**. No suma kilogramos y unidades. El usuario interno carga_docente tiene contraseña inutilizable y sólo identifica los seis movimientos iniciales; no se utiliza para ingresar. Preparar_demo puede repetirse sin duplicar esos movimientos y conserva tus operaciones posteriores.

## Datos de práctica y CSV

- datos/productos_validos.csv: añade cuatro códigos nuevos AD-101 a AD-104; existencia inicial cero. Úsalo una sola vez por base. Una segunda importación se rechaza porque los códigos ya existen.
- datos/productos_invalidos.csv: contiene duplicado, mínimo negativo, unidad inexistente, texto con etiquetas y precisión excesiva. Debe rechazarse completo, sin registrar AD-201.
- datos/movimientos_ejemplo.csv: guion de operaciones para introducir desde el formulario, después de preparar_demo. No se importa automáticamente.
- datos/pruebas_aceptacion.csv: lista de comprobaciones para llenar en la unidad 5.

La cabecera de importación debe ser exactamente codigo,nombre,unidad,minimo, separada por comas. Guarda como CSV UTF-8 y utiliza punto decimal. Si Excel utiliza punto y coma por tu configuración regional, importa el CSV con **Datos > Desde texto/CSV**, elige coma y comprueba las columnas; no alteres el archivo original. Se admiten hasta 100 filas y 1 MB. Importar catálogo no altera stock; para eso se registran movimientos.

La exportación tiene dos columnas adicionales: existencia y bajo_minimo; es un reporte, no la plantilla de importación. Las celdas textuales que podrían interpretarse como fórmulas se protegen con apóstrofo.

## Roles

**Consulta:** lee existencias e historial y exporta CSV. **Operación:** además crea productos, importa catálogo y registra entradas/salidas. Ambas restricciones se comprueban en el backend. Las cuentas no son administradoras.

Si el docente necesita administrar grupos, puede crear una cuenta separada con python manage.py createsuperuser y entrar por /admin/. No compartas esa cuenta con estudiantes. El historial no se edita y la existencia se modifica mediante el servicio de movimientos.

## Cómo trabajar con IA

Comienza leyendo el código y usando la aplicación. Después, pide a tu asistente que explique un archivo y proponga un cambio pequeño. Guarda una copia o un commit antes de aceptar cambios. Revisa los archivos modificados y ejecuta las pruebas. En prompts/ tienes instrucciones de ejemplo y un registro de evidencias.

La ruta gratuita es independiente del proveedor: puedes usar un modelo gratuito compatible, uno local adecuado al equipo o el servicio autorizado por el laboratorio. Si la cuota del asistente se agota, continúa con las guías y la plantilla. No necesitas IA para ejecutar, comprobar o presentar el prototipo.

## MCP opcional: unidad 4

1. Con el servidor web detenido, instala python -m pip install -r requirements-mcp.txt.
2. Ejecuta python verificar_mcp.py. Conecta un cliente con las dos herramientas reales del servidor y verifica que la base no cambia. **No utiliza un modelo ni una API de IA.**
3. Si vas a usar OpenCode, sigue la instalación oficial para tu sistema: https://opencode.ai/docs/. El laboratorio debe probar su versión y modelo antes de la sesión.
4. Ejecuta python preparar_opencode.py: genera opencode.json con las rutas del Python de tu entorno y del servidor. No añade claves ni sobrescribe una configuración existente.
5. Abre OpenCode desde esta carpeta, selecciona un modelo disponible compatible con herramientas y comprueba el servidor con opencode mcp list.
6. Solicita: «Usa andina para consultar AD-001 y explica su existencia y mínimo; no ejecutes comandos ni cambies archivos». Confirma sólo la herramienta de consulta esperada y contrasta con el tablero.

MCP no es un modelo ni da una suscripción. El servidor utiliza stdio local y abre SQLite en modo de sólo lectura. Sólo expone consultar_existencias y productos_bajo_minimo; no acepta SQL, no crea movimientos y no abre un puerto. No conecta con datos reales ni hereda los roles web: consulta el dataset local de tu equipo. El asistente de desarrollo puede tener otras herramientas; revisa sus permisos y no le autorices cambios durante la demostración MCP.

Si no hay modelo disponible, completa la verificación de protocolo y analiza el resultado con el docente. Documenta esa modalidad; no simules una conversación inexistente ni asegures que se conectó a una IA.

## Mapa de archivos

- andina/: configuración y rutas de la aplicación local.
- inventario/models.py: datos y restricciones.
- inventario/services.py: validación de cantidades, movimientos atómicos e importación.
- inventario/forms.py, views.py, urls.py: formularios y operaciones web.
- inventario/tests.py: pruebas de cálculos, permisos, transacciones y archivos.
- templates/: pantallas adaptables sin recursos externos.
- mcp_consultas.py y servidor_mcp.py: conexión opcional de consulta.
- guias/: actividades de las cinco unidades.
- plantillas/: diseño del proyecto, bitácora y rúbrica.
- MANIFIESTO_SHA256.txt: huellas de los archivos distribuidos.

## Si algo falla

- **No existe Python:** verifica py --list en Windows o python3 --version en Linux y solicita la instalación al soporte del laboratorio.
- **No se encuentra Django:** ejecuta pip con el mismo Python del entorno que utiliza manage.py.
- **No existe la tabla:** ejecuta migrate desde la carpeta del kit.
- **Puerto ocupado:** usa otro puerto local, por ejemplo 8002, y abre esa dirección.
- **Acceso restringido:** comprueba si ingresaste como lector u operador; no desactives permisos.
- **Stock insuficiente:** revisa cantidad, producto e historial. No edites la base para forzar la salida.
- **CSV rechazado:** lee las filas indicadas, conserva la cabecera y revisa UTF-8, comas y punto decimal.
- **MCP espera sin mostrar nada:** servidor_mcp.py espera a un cliente por stdio; utiliza verificar_mcp.py o el host configurado.

Conserva evidencias fuera de la carpeta de código. Para recuperar una práctica, descomprime el ZIP en otra carpeta y repite los pasos; no necesitas borrar tu proyecto anterior. Al compartir el proyecto, excluye .venv, db.sqlite3, .secreto-local, opencode.json y credenciales. El material propio tiene licencia MIT; las fuentes externas mantienen sus licencias y se enlazan, sin redistribuir videos ni manuales ajenos.
