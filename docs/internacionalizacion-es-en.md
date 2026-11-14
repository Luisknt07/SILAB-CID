# Interfaz en español e inglés

La selección ES/EN está en el encabezado público y en el administrador. Cambia
el idioma de la interfaz y conserva la página, sus parámetros y su ancla. La
preferencia se guarda durante un año en una cookie de ese navegador; no modifica
el perfil, los permisos ni la configuración de otra persona.

Esta función pertenece a la presentación transversal de M02.1. No introduce
otra instalación, otra base de datos o copias de las apps. Las rutas de negocio
mantienen sus nombres y direcciones actuales.

## Responsabilidades y archivos

| Responsabilidad | Archivo o carpeta |
| --- | --- |
| Idiomas habilitados, middleware y cookies | `config/settings.py` y `config/settings_production.py` |
| Cambio de idioma y catálogo JavaScript | `apps/core/presentation/idiomas.py` y `urls.py` |
| Idioma de presentación y zona institucional | `apps/core/presentation/regional.py` |
| Etiquetas de formularios y administración | `apps/core/presentation/traducciones.py` y `administracion.py` |
| Selector compartido y recursos para documentos independientes | `webcitt/templates/portal/components/navegacion/` |
| Fragmentos literales de HTML en JavaScript | `webcitt/static/portal/js/components/idiomas.js` |
| Traducciones editables y compiladas | `locale/es/LC_MESSAGES/` y `locale/en/LC_MESSAGES/` |
| Compilación reproducible en Windows, sin paquetes adicionales | `scripts/compilar_idiomas.py` |
| Pruebas de idioma, seguridad y conservación de datos | `webcitt/tests/test_idiomas.py` |

`LocaleMiddleware` se ejecuta después de las sesiones y antes de
`CommonMiddleware`. El cambio usa el mecanismo de Django con validación del
destino y una lista limitada a `es` y `en`. Se exige POST y token CSRF; no se
habilitan redirecciones a sitios externos. Esta organización sigue la
[documentación oficial de Django](https://docs.djangoproject.com/en/5.2/topics/i18n/translation/#the-set-language-redirect-view).

El catálogo JavaScript usa el dominio `django`, compartido con las plantillas
y los adaptadores Python. Su dirección incluye el idioma y su caché es privada,
con `Vary: Cookie`. La descarga admite gzip y varía también por `Accept-Encoding`,
reduciendo el tamaño del catálogo para los navegadores que lo solicitan.
Las traducciones se sirven desde archivos del proyecto; no hay llamadas a
proveedores de traducción durante el uso del sistema. Si no
se descarga ese catálogo, los scripts conservan los textos fuente y operan.

## Qué se traduce y qué se conserva

Se marcaron textos de navegación, cuentas, reservas, gestión, plantillas del
aula y del administrador. Las etiquetas, ayudas y opciones estáticas de los
formularios se traducen al construirlos para cada petición. Los grupos de
opciones conservan sus claves. Las opciones de modelos conservan los nombres
que se registraron en la base.

Los títulos y textos escritos por los administradores, nombres institucionales,
productos, equipos, recursos, resultados científicos y archivos cargados
mantienen su contenido original. Un PDF subido en español sigue estando en
español. Publicar una versión inglesa de ese contenido requiere redactarla y
revisarla; cambiar la interfaz no traduce automáticamente documentos ni datos.

Los códigos de actividad, valores de POST, identificadores HTML, claves JSON,
cantidades, fórmulas y timestamps no se traducen. No se duplican procesos o
productos. No hay nuevas migraciones ni se reescriben reservas históricas.

Si hay un recurso abierto, el selector construye el retorno con el módulo
activo y su identificador mediante la ruta existente `?recurso=…#modulo`.
Conserva los demás parámetros y elimina la referencia anterior a una guía.
Si se está viendo una portada, elimina la selección anterior de recurso.
No guarda formularios ni datos personales en almacenamiento del navegador.

La preferencia de idioma y la zona horaria son distintas. El navegador puede
mostrar inglés mientras la agenda utiliza `America/Guayaquil`. El formato
regional de español mantiene el predeterminado institucional. La configuración
de una instalación continúa usando `INSTITUTION_LANGUAGE_CODE` y
`INSTITUTION_TIME_ZONE`; seleccionar EN no cambia esas variables.

## Incorporar o mejorar traducciones

1. Marcar el nuevo texto de interfaz: `{% translate 'Texto' %}` en una plantilla
   con `{% load i18n %}`, o `gettext('Texto')` en Python. Para mensajes con datos,
   usar `blocktranslate` o variables nombradas; no interpolar datos antes de
   localizar el mensaje.
2. En JavaScript usar `gettext('Texto')` o `window.interfaz.html` para una
   plantilla de HTML. Este último traduce los fragmentos literales, normalizando
   espacios; conserva las interpolaciones y el contexto de etiquetas/atributos
   entre ellas. Seguir escapando las interpolaciones
   que provienen de usuarios. Las traducciones del helper se escapan como HTML.
3. Añadir el `msgid` literal a ambos `django.po`. En español, `msgstr` conserva
   el texto fuente; en inglés, contiene la traducción revisada. Para el helper
   HTML, registrar cada fragmento de texto o atributo presentacional; no las
   etiquetas, atributos técnicos ni la plantilla completa.
4. Mantener exactamente los marcadores de formato y las cantidades. Las
   herramientas GNU de Django pueden extraer Python y plantillas; los fragmentos
   del helper JavaScript y las etiquetas dinámicas de catálogos deben registrarse
   también en el dominio compartido. Evitar un segundo catálogo `djangojs` que
   el endpoint actual no consume.
5. Compilar y verificar, ejecutar las pruebas correspondientes e invalidar la
   versión de los scripts modificados. Publicar los PO y MO juntos. Reiniciar
   los procesos Django porque mantienen traducciones en memoria.

```powershell
.venv/Scripts/python.exe scripts/compilar_idiomas.py
.venv/Scripts/python.exe scripts/compilar_idiomas.py --check
.venv/Scripts/python.exe manage.py test webcitt.tests.test_idiomas --keepdb --noinput
.venv/Scripts/python.exe manage.py collectstatic --noinput
```

El compilador verifica duplicados, traducciones vacías, entradas `fuzzy`,
marcadores nombrados y que los MO correspondan a los PO. Admite contexto,
continuaciones y los dos plurales de español e inglés. No ejecuta los archivos
de traducción ni depende de servicios externos.

Los catálogos iniciales contienen **8430 mensajes por idioma**. Se prepararon
con asistencia de traducción local y un glosario revisado de navegación,
formularios, reservas, recursos y balances. Se comprobaron cantidades y
marcadores. Esto no equivale a una revisión lingüística especializada de todos
los textos científicos. La revisión editorial puede mejorar los PO sin tocar
la lógica ni los datos.

La preparación local utilizó Argos es→en 1.9 y CTranslate2 en una carpeta de
herramientas temporal, excluida de Git y del despliegue. El modelo deriva de
OPUS-MT, Jörg Tiedemann y Santhosh Thottingal, «OPUS-MT — Building open translation
services for the World», EAMT 2020; su README declara CC-BY 4.0 para el modelo
original. No se redistribuye el modelo ni se incorporan esas dependencias al
entorno de la aplicación. Referencia del distribuidor:
[índice oficial de Argos](https://github.com/argosopentech/argospm-index).

## Despliegue y comprobaciones

En producción, `LANGUAGE_COOKIE_SECURE=True`, cookie HttpOnly y SameSite=Lax.
El entorno de desarrollo permite HTTP local. El selector no sustituye los
controles de autenticación, CSRF ni permisos existentes.

Se probaron navegadores con preferencias independientes, conservación de
sesión, POST protegido, destinos externos rechazados, catálogos separados,
cuentas, administrador y las cuatro categorías de unidades. Chrome comprobó
ES/EN en el portal y la planta de lácteos, con anchos de 1366, 390 y 360 px,
sin errores JavaScript. Plantillas de ambos idiomas y todos los scripts del
portal compilan. También se comprobó el retorno al mismo producto y módulo.
`makemigrations --check --dry-run` no detecta cambios.

Validación integral: 874 pruebas, OK; una omitida, 1573.894 segundos.

La siguiente etapa M02.1 continúa con pertenencia y roles verificados, tarifas
históricas, catálogos persistentes y edición institucional. M01 institucional
sigue abierto; esta función no demuestra aislamiento del despliegue.

Referencias: [Configuración regional](configuracion-regional-institucional.md),
[Ruta modular](ruta-ejecucion-arquitectura-modular.md).


El selector del portal se encuentra a la derecha de Contacto en la barra verde
superior, visible tambien en movil. El administrador conserva su selector.
