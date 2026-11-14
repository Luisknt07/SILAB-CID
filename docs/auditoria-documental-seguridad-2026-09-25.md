# Documentos, integridad y continuidad: auditoría del 25 de septiembre de 2026

## Alcance y criterio editorial

Revisión de los generadores de informes del expediente, reportes de unidad,
planificaciones y guías; carga firmada de guías y expediente; acceso a archivos,
versiones, trazabilidad y scripts de respaldo. No constituye una certificación
de seguridad de todo el sistema ni una prueba del despliegue de producción.

El encabezado debe identificar el documento emitido, no llamarlo «FORMATO»
automáticamente. Se mantiene el logo y la institución configurados, el código
existente, la cobertura y la versión del documento. El expediente deja de
mostrar una revisión fija «01» sin relación con una revisión aprobada y evita
«Período: Período». No se inventaron nuevos códigos institucionales.

Se formalizaron los subtítulos: «Evaluación por documento», «Actividad registrada
en el período», «Hallazgos y recomendaciones» y «Actividades previstas en la
planificación». «Resolución de la autoridad competente» evita asignar por defecto
la decisión a un decanato. El cuerpo conserva la dependencia de adscripción y
aclara que preparar el PDF no significa remitirlo ni registrar una resolución.
El registro de resolución pendiente no se presenta como una decisión ya tomada.

Se generó y revisó visualmente un informe de dos páginas con datos locales:
encabezado, contenido, tablas, metadatos y pies sin desbordamientos.

## Datos actuales frente a evidencia archivada

La consulta y generación leen datos registrados en ese momento. El PDF archivado
es una instantánea con fecha, cobertura y versión: no se debe sobrescribir para
que parezca actualizado. Una actualización produce una nueva versión.

El expediente ya serializa comandos por unidad, guarda recurso e historial en
transacción y compensa archivos nuevos cuando falla la operación. La carga
firmada ahora conserva los anexos existentes: antes los regeneraba con datos
posteriores a la generación del documento que se firmó. Solo produce los anexos
faltantes. Esto no demuestra por sí solo que un PDF externo corresponda al
documento generado: esa correspondencia continúa siendo parte de la revisión.

## Correcciones de seguridad y conservación

- Las guías firmadas ya no borran la carga anterior antes de guardar la nueva.
  Se bloquea la fila, se releen permisos y estado, se usa un nombre único y se
  confirman referencia y auditoría juntos. El historial registra ambas rutas
  y la nueva huella SHA-256 completa. Si falla la auditoría se conserva el
  registro anterior y se retira el nuevo archivo. Los archivos anteriores se
  conservan para recuperación; no hay todavía una interfaz de restauración.
- La URL directa de una guía firmada aplica los permisos del visor. No entrega
  versiones anteriores por ruta ni restos sin referencia. Se añaden aislamiento
  de contenido y cabeceras de caché para esta ruta.
- La lectura de la carga firmada se limita a 20 MB más un byte aun si el tamaño
  declarado es incorrecto.
- Detectar una firma o generar un PDF ya no marca falsamente revisión antivirus
  en los nuevos recursos del expediente y mejora. El personal autorizado puede
  revisar una entrega interna, manteniendo el control de alcance y aislamiento
  de contenido; esto no habilita publicación ni certifica ausencia de malware.
  La publicación de recursos sigue requiriendo revisión de seguridad.

Las protecciones se separan entre permisos, servicio de carga, entrega de medios,
generación y verificación. No se incorporan dependencias de modelos a vistas ni
nuevas dependencias de paquetes. Se mantienen los contratos de arquitectura.
La aplicación y base compartidas siguen siendo un monolito modular: no existe
aislamiento total ante un fallo del proceso o de la base.

## Comprobación de archivos y recuperación local

Nuevo comando de solo lectura:

```powershell
.\.venv\Scripts\python.exe manage.py verificar_integridad_documental
```

Comprueba existencia, tamaño y SHA-256 de los recursos y huella completa de las
guías firmadas actuales. Sale con error si hay discrepancias, archivos ilegibles
o huellas insuficientes. No modifica ni «corrige» huellas para hacer pasar un
archivo alterado. No verifica firmas criptográficas ni reemplaza un antivirus.

Resultado local: **76 archivos verificados, cero discrepancias y ocho sin huella
completa verificable** (recursos 1–6 y guías 13–14). No puede acreditarse la
integridad histórica de esos ocho sin contrastarlos con un original confiable.

El recurso 47 tenía una reparación visual previa que había cambiado los bytes
sin cambiar su huella. Se recuperó la copia original de respaldo, verificando
antes que tamaño y SHA-256 coincidían exactamente con la base, y se registró la
recuperación en auditoría. Se conservaron versión y contenido originales. Esa
versión histórica conserva su diseño anterior; para el diseño nuevo debe
generarse otra versión desde el flujo habitual. No se reescribieron PDFs firmados.

## Respaldos: implementado y pendiente de verificar

El repositorio tiene copias PostgreSQL y media con SHA-256, publicación mediante
archivo temporal, retención y restauración de ensayo en base temporal. Docker
configura frecuencia diaria por defecto. Se revisaron scripts y sus pruebas;
no se ejecutó una restauración nueva contra el servidor de producción.

Pendientes necesarios antes de declarar continuidad operativa verificada:

1. Confirmar dónde se ejecuta producción, si el servicio de respaldo está activo
   y dónde se guarda una copia externa independiente, cifrada y protegida.
2. Ensayar recuperación conjunta de base, adjuntos y marca institucional en un
   entorno aislado; ejecutar allí el comando de integridad. Las copias actuales
   son secuenciales, no una instantánea coordinada de todos los módulos.
3. Medir RPO/RTO y verificar alertas de fallos. Un respaldo diario no proporciona
   recuperación al último segundo; no se ha configurado aquí PITR/WAL ni réplica.
4. Confirmar que el proxy no expone MEDIA_ROOT directamente, evitando Django.

## Límites de seguridad pendientes

La validación de firma actual detecta marcadores PDF, no verifica certificado,
cadena de confianza, revocación ni integridad criptográfica. El nombre legado
`firma_verificada` no debe interpretarse como certificación criptográfica.
Se necesita un validador institucional de firma y evidencia de su resultado.
Tampoco hay un motor antivirus conectado: se corrigió la afirmación falsa, no se
simuló un escaneo. No se han analizado todas las dependencias ni todos los roles
de todo el sistema mediante una auditoría de penetración.

Como referencia de controles de carga se consultó
[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html):
permisos, límites, nombres controlados y análisis antivirus son controles
complementarios; la extensión o la detección del tipo no bastan.

## Validación

Pruebas enfocadas de permisos, historial, concurrencia de expediente, reversión,
generación, identidad institucional, carga firmada, integridad y contratos de
arquitectura. Se incluyeron regresiones para la URL directa, conservación de
versiones, fallo de auditoría, límites de carga y detección de archivo alterado
o ausente. Las expectativas antiguas que exigían «FORMATO» se actualizaron al
criterio editorial nuevo. Ruff no reporta incidencias en los archivos revisados.
