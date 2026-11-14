# Auditoría de estructura y seguridad — 8 de octubre de 2026

## Dictamen y alcance

Se revisa el árbol de trabajo de reestructura-modular después del commit 378dd743. La preparación técnica se realiza para un servidor Linux propio de la universidad, con portal y backend en el mismo origen. No se ha accedido a ese servidor, configurado el DNS/certificado real ni publicado estos cambios.

Esta revisión combina inventario de archivos, compilación, contratos modulares, referencias de plantillas/estáticos, análisis de dependencias, pruebas funcionales y consultas SQL reales bajo un rol PostgreSQL restringido. No sustituye una prueba de penetración ni acredita ausencia absoluta de fallos.

## Hallazgos y correcciones

| Hallazgo | Corrección | Alcance |
|---|---|---|
| /media/ entregaba archivos existentes sin comprobar su registro o visibilidad | Registro explícito de campos públicos/privados y autorización antes de abrir; archivos desconocidos denegados | Finanzas, perfiles, reservas, guías, evidencias, operaciones y centros; el aula conserva descargas propias autorizadas |
| Documentos internos y resultados bajo embargo podían abrirse por URL directa | Verificar público, confidencialidad, embargo, publicación y carpeta activa | Documentos, resultados y recursos de Centros I+D |
| El login/registro propio omitía la verificación obligatoria de allauth | Unificar las entradas con los flujos públicos de allauth; impedir cambiar el correo verificado desde el perfil | Producción exige correo confirmado |
| CSP permitía scripts inline | Nonce aleatorio por petición en scripts del código fuente; retirar atributos inline; acciones explícitas sin eval | Portal y administración; CSP rechaza overrides que reabran inline/eval |
| No había control central de origen ni de frecuencia | CORS de lista exacta, rechazo de orígenes ajenos, contador PostgreSQL atómico y límites Nginx | 10 autenticaciones y 120 escrituras por minuto por defecto; lectura limitada por proxy |
| JSON malformado, profundidad excesiva y HTML importado podían saltarse controles de estructura | Objeto JSON obligatorio, límites estructurales, rechazo de NUL/no finitos; saneado HTML también al presentar | No altera contraseñas, apóstrofes ni expresiones científicas; cada dominio mantiene validación semántica |
| Los ejemplos editables de reservas se insertaban como JSON sin escapar delimitadores HTML | Serializar con json_script y comprobar que un cierre de script malicioso sigue siendo texto recuperable | Asistente compartido por todas las unidades |
| El rol web podía ser el superusuario inicial de Docker | Separar servicio/credenciales de migración, web y respaldo; comprobar atributos, propiedad, esquema y membresías del rol | Fallo cerrado del arranque ante privilegios excesivos |
| Ausencia de defensa por filas en datos académicos personales | ENABLE + FORCE RLS, USING y WITH CHECK; identidad local a la transacción | Seis tablas, detalladas abajo |
| OAuthLib y PyJWT tenían avisos de seguridad | OAuthLib 4.0.0 y PyJWT 2.15.0; regenerar uv.lock y requirements con hashes | Segunda revisión pip-audit sin vulnerabilidades conocidas |
| PDF.js 3.11.174 tenía un aviso conocido de ejecución de código | PDF.js 6.4.299 legacy local, biblioteca y worker coincidentes, sin eval del portal | Licencia y procedencia en static/js/vendor/pdfjs/6.4.299/README.md |
| Seis modelos de Centros I+D quedaban en Configuración complementaria | Declarar zonas, herramientas, horarios, bloqueos, habilitaciones y líneas dentro del área del centro | Administrador agrupado, sin esconder modelos |
| 29 candidatos a huérfanos | Resolver destinos del mapa de centros y crear índice documental | No se borraron plantillas válidas ni documentos históricos |

## Bibliotecas del navegador

Se sustituyó jQuery 3.3.1 por 3.7.1, posterior a las correcciones XSS de jQuery 3.5, y Bootstrap JS 4.3.1 por 4.6.2 para conservar la API de los modales. Fuentes y licencias en webcitt/static/js/vendor/VERSIONES.md. El contraste npm de siete versiones exactas (incluidos Leaflet, ZXing, Perfect Scrollbar y Mousetrap) no reportó vulnerabilidades conocidas. Bootstrap 4 está fuera de soporte; planificar la migración a Bootstrap 5 con adaptación de componentes, sin tratar esta actualización compatible como una modernización completa. Los avisos CVE-2024-6531 y CVE-2024-6484 fueron retirados por sus responsables y no se presentan como vulnerabilidades activas corregidas. [jQuery 3.5](https://blog.jquery.com/2020/04/10/jquery-3-5-0-released/), [soporte Bootstrap 4](https://getbootstrap.com/docs/4.6/end-of-life/).

## Secretos en el historial

El .env estuvo versionado en cuatro revisiones históricas. La inspección sin revelar valores identificó DB_PASSWORD, GOOGLE_CLIENT_SECRET y SECRET_KEY. Ninguno coincide con el entorno local actual; esto no acredita revocación en los proveedores. Confirmar con TI la revocación de la contraseña y el secreto OAuth antiguos, y usar una SECRET_KEY nueva en producción. No se reescribió ni forzó el historial Git: la revocación de credenciales es el paso indispensable. Las nuevas variantes .env.* y archivos de claves están excluidos de Git y del contexto Docker.

## Organización del repositorio

Se conserva el monolito modular: apps contiene las verticales y capas extraídas; config configura entornos y módulos; webcitt mantiene tablas/migraciones y compatibilidad histórica; scripts contiene operación; docs contiene guías e informes; var contiene datos generados fuera de Git. Cambiar masivamente nombres de modelos o carpetas durante el endurecimiento pondría en riesgo migraciones, enlaces y datos existentes.

El auditor scripts/auditar_repositorio.py revisa archivos ausentes, colisiones por mayúsculas entre Linux/Windows, sintaxis Python, mayúsculas de imports, UTF-8, artefactos privados, patrones de secretos y duplicados SHA-256. Las eliminaciones intencionales del árbol se enumeran por separado. No imprime valores de secretos ni lee el .env ignorado. El auditor de huérfanos incluye archivos nuevos y reconoce solo los destinos dinámicos efectivamente registrados.

Existen cuatro pares de imágenes idénticas usados como alias por catálogos y potencialmente por registros históricos: refractometros-de-proceso/refractometros, termometros-de-proceso/termometros-y-registradores-de-temperatura, documentation-wazuh-com/wazuh-com y tljh-jupyter-org/z2jh-jupyter-org. Se conservan por compatibilidad; retirarlos requiere migrar referencias de base de datos. Los archivos __init__.py vacíos no son contenidos duplicados retirables: definen paquetes. No se encontraron otros archivos vacíos inesperados.

collectstatic identifica tres destinos compartidos entre Grappelli y Django admin: actions.js, DateTimeShortcuts.js y RelatedObjectLookups.js. Son sustituciones intencionales del tema; findstatic confirma que Grappelli tiene precedencia. No son archivos fantasma ni copias eliminables del proyecto.

El índice docs/indice.md reúne informes que antes no estaban enlazados. Los informes fechados conservan su valor histórico; esta auditoría y produccion-linux.md describen el trabajo actual.

## Acceso por filas y sus límites

Las políticas cubren webcitt_simulacionguardada, webcitt_intentoejercicio, webcitt_progresoleccion, webcitt_intentoevaluacion, webcitt_entregadeber y webcitt_pagoinscripcion. Sin identidad no se leen filas; el propietario accede a las propias. Docentes acceden a sus ejercicios y personal con delegación de prácticas a los datos académicos de sus unidades. El superusuario de la aplicación conserva gestión institucional mediante contexto establecido por el servidor. Las políticas controlan también INSERT/UPDATE.

La identidad se establece mediante set_config local dentro de una transacción y se elimina al terminarla; no se acepta desde formularios, cabeceras ni JSON. El rol de aplicación carece de BYPASSRLS y de propiedad sobre las tablas. La comprobación de despliegue rechaza roles que podrían desactivar estas políticas.

RLS no se ha aplicado indiscriminadamente a todas las tablas: la agenda necesita consultar ocupación entre usuarios y los cursos necesitan calcular cupos. Esas tablas y las solicitudes de centros conservan sus controles de autorización por objeto en el backend. No debe describirse esta implementación como RLS universal; ampliar su cobertura exige separar vistas agregadas públicas y filas privadas, con pruebas del contrato de disponibilidad.

## Sanitización y contenido interactivo

El texto normal se conserva y se escapa al mostrarlo; consultas ORM parametrizadas evitan interpretar apóstrofes como SQL. El HTML enriquecido usa listas permitidas de etiquetas, atributos y URL, se sanea antes de guardar y vuelve a sanearse al presentar datos antiguos. JSON no sustituye formularios/validadores del dominio: fechas, rangos, relaciones, cupos y permisos siguen siendo responsabilidad del backend correspondiente.

Los scripts del portal requieren fuente autorizada o nonce. La anotación ocurre al leer código de plantillas confiable, antes de interpolar contenido, por lo que no concede nonce a scripts guardados por usuarios. Las respuestas HTML no usan caché compartida. Los estilos inline existentes se conservan; esta revisión endurece la ejecución de scripts.

Los recorridos y recursos HTML/ZIP previamente revisados conservan scripts dentro de sandbox de origen opaco, con política propia. Su compatibilidad requiere inline/eval dentro de ese aislamiento; no tienen acceso al DOM del portal ni a sus API autenticadas porque se rechaza Origin:null. La CSP del portal no permite inline/eval. Evidencias y HTML legacy sin revisión se entregan aislados y/o como descarga.

## Validación reproducible

Ejecutar desde el entorno virtual:

- python -X utf8 scripts/auditar_repositorio.py --estricto --json var/auditoria-repositorio.json
- python manage.py auditar_modulos
- python manage.py auditar_contratos_senales
- python manage.py auditar_huerfanos --estricto
- python manage.py auditar_plantillas
- node --test webcitt/tests/js/test_acciones_seguras.cjs webcitt/tests/js/test_enlace_seccion.cjs
- python manage.py check
- python manage.py makemigrations --check --dry-run
- python manage.py test --noinput
- uvx pip-audit -r requirements.txt
- Con el entorno real de producción: python manage.py check --deploy y python manage.py verificar_seguridad_bd

Resultados del cierre:

| Comprobación | Resultado |
|---|---|
| Suite completa | 2.634 pruebas, OK, sin fallos ni omisiones; 389,266 s con cuatro procesos |
| Seguridad y regresiones dirigidas | 116 pruebas, OK; esquema creado desde cero con todas las migraciones |
| JavaScript | 12 pruebas, OK; sintaxis de los controladores modificados válida |
| Inventario | 3.636 archivos, cero errores, cero colisiones de nombres y cuatro grupos de imágenes idénticas conservados como alias |
| Referencias | Cero huérfanos; 346 plantillas válidas; imports compatibles con las mayúsculas de Linux |
| Contratos | Auditoría modular limpia; 31 contratos/conexiones de señales revisados, sin hallazgos |
| Código y esquema | Ruff, Django check, makemigrations --check --dry-run y git diff --check correctos |
| Dependencias | 35 paquetes Python y siete bibliotecas de navegador contrastadas, sin vulnerabilidades conocidas reportadas |
| Estáticos | collectstatic correcto: 200 archivos copiados y 2.308 sin cambios |
| Despliegue simulado | check --deploy con variables ficticias endurecidas, definición Compose y sintaxis de los scripts shell correctos |

La última suite usa un esquema de prueba actualizado clonado en una base temporal con nombre exclusivo y cuatro clones independientes; cada proceso tiene su propio MEDIA_ROOT. Para acelerar fixtures, solo el proceso de QA usa MD5PasswordHasher. La configuración normal y la de producción conservan sus hashers seguros. Una corrida dirigida anterior de 87 pruebas también pasó con la configuración normal. El soporte opcional tblib se instaló únicamente en el entorno de pruebas para informar errores de procesos paralelos; no forma parte de las dependencias de producción.

Las corridas intermedias permitieron corregir expectativas de interfaz, un contrato administrativo antiguo y una prueba que se omitía por falta de datos: esa prueba ahora crea explícitamente otra unidad y comprueba el 404. La suite final incorpora esas correcciones y la prueba de inyección en el JSON de reservas.

Los logs de trabajo permanecen en var, fuera de Git. Las pruebas no migran ni modifican los datos activos. No se afirma inspección visual de navegador: los ensayos de modales usan DOM simulado y el visor PDF se comprobó con renderizado real en Node. Falta comprobar la navegación real con CSP en Linux.

## Pendiente en infraestructura

Seguir produccion-linux.md: dominio y certificados, credenciales reales, migraciones con rol separado, permisos efectivos de PostgreSQL, SMTP, prueba de restauración, Nginx y prueba de navegación con CSP en el servidor Linux. Confirmar la IP del proxy para que los límites se apliquen a cada cliente. No se dispone de acceso al servidor ni de los datos de dominio/certificado para completar esas comprobaciones desde este equipo.

Fuentes primarias: [despliegue Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [RLS PostgreSQL](https://www.postgresql.org/docs/17/ddl-rowsecurity.html), [recomendaciones REST OWASP](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), [aviso PDF.js](https://github.com/mozilla/pdf.js/security/advisories/GHSA-wgrm-67xf-hhpq), [PDF.js 6.4.299](https://github.com/mozilla/pdf.js/releases/tag/v6.4.299), [OAuthLib 4.0.0](https://github.com/oauthlib/oauthlib/releases/tag/v4.0.0), [PyJWT 2.15.0](https://github.com/jpadilla/pyjwt/releases/tag/2.15.0).
