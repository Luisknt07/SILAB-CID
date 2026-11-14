# Remisión y seguimiento del informe de mejora

Implementación del paso 3 de la auditoría del centro de reportes, en la rama
`reestructura-modular`. El flujo técnico está implementado; su puesta en uso
requiere completar adscripciones y receptores con información institucional.

## Flujo disponible

1. La unidad o la Dirección archiva el informe del período. Generarlo no lo
   remite. Cada versión tiene una relación explícita con unidad, año y corte.
2. La Dirección remite la versión vigente desde el expediente. Se exige una
   dependencia activa con receptores activos. Se conservan dependencia,
   destinatarios, autor y fecha. La entrega ocurre dentro del sistema.
3. Un destinatario vigente registra la recepción y después una resolución:
   continuidad con plan de mejora, rediseño o cierre, con motivo obligatorio.
   La Dirección no suplanta el acuse o la decisión del destinatario.
4. La Dirección o el destinatario definen acciones con responsable y plazo.
   El responsable debe tener acceso operativo a los reportes de esa unidad.
5. El responsable registra avances; la Dirección o el destinatario verifican
   y cierran la acción. Los avances conservan autor, fecha y detalle, y no se
   sobrescriben. Las acciones vencidas se señalan en pantalla.

El acceso está en **Reportes e indicadores → Remisión y seguimiento de mejora**,
y en el expediente del período, también desde la consola de la unidad.
La bandeja es de consulta; sus enlaces conducen al trámite autorizado.
El anexo de seguimiento incluye tanto las acciones narradas en los informes
semestrales como las acciones formales y sus avances.

## Reglas y límites

- La Dirección conserva el criterio de superusuario activo del expediente
  existente. No se crean roles equivalentes por el solo hecho de ser staff.
- Se admite una remisión por unidad y período. Una vez remitida, la versión
  no se regenera, reemplaza ni edita desde la administración de recursos.
- Recibir exige estar entre los destinatarios originales y seguir designado
  en la dependencia activa a la que pertenece actualmente la unidad.
  Revocar al receptor o cambiar la adscripción retira su acceso.
- Un nuevo receptor no hereda automáticamente trámites remitidos a otra
  persona. Un procedimiento de reasignación o rectificación con trazabilidad
  requiere definición institucional; no existe edición libre de resoluciones.
- Registrar «cierre» conserva la resolución; no desactiva automáticamente la
  unidad ni cancela sus reservas. Esas actuaciones requieren su propio trámite.
- Los avances guardan evidencia descriptiva. No se introduce un segundo
  repositorio de adjuntos ni se reemplaza el repositorio documental existente.
- No se envía correo ni se comunica con servicios externos.
- Las mutaciones se autorizan en servicios, usan bloqueo y transacción, y
  guardan auditoría junto con el cambio. Un fallo de auditoría revierte el trámite.

## Arquitectura y migración

`webcitt/models/mejora.py` contiene `InformeMejora`, `AccionMejora` y
`SeguimientoMejora`. `domains/unidades/mejora_seguimiento.py` concentra las
transiciones y sus permisos. La vista existente del expediente atiende los
POST y comparte contexto y plantilla con la consola. El recurso se entrega
por la ruta protegida existente, incluida la protección de su URL de medios.
No se trasladaron modelos, tablas ni permisos heredados entre aplicaciones.

La migración **0236** crea las relaciones y vincula únicamente informes
históricos cuyo nombre completo y versión coinciden con el formato del
generador. No inventa destinatarios, remisiones, acuses ni decisiones.
Se ensayó sobre una restauración del respaldo local
`var/backups/antes_0236_20260925T130707.dump`, con su archivo SHA-256.
Se aplicó después a la base local. Los 761 documentos y 82 recursos conservan
la huella de sus identificadores, referencias, versiones y estados previos:
`f9cf451a07efcdecef8ab19f371448a83e8fe8024caf23cba58444e05d1ba4d8`.
Revertir el esquema elimina los nuevos registros de trámite; no hacerlo sobre
trámites reales sin respaldo y un procedimiento de recuperación acordado.

## Configuración pendiente

Lectura local al cierre de la implementación: 21 unidades activas,
14 sin adscripción, tres dependencias activas y ninguna con receptor activo.
Un informe histórico vinculado, cero remisiones reales. No se asignaron personas
ni dependencias supuestas.

La institución debe proporcionar las adscripciones y cuentas receptoras.
La Dirección las configura en la administración de unidades y dependencias
académicas. Después puede revisar el informe, remitirlo y comprobar el circuito
con sus destinatarios. El bloqueo de remisión evita entregas sin destino.

## Validación

- Primera ejecución enfocada: 21 pruebas correctas.
- Verificación ampliada: 120 pruebas, con dos fallos de navegación corregidos
  (tarjeta duplicada y expectativa de siete entradas). Cierre posterior:
  **73 pruebas correctas**, incluidos trámite, permisos, menú y señales.
- Revisión administrativa: 749 pantallas, cero fallos.
- Siete lecturas del expediente, consola, bandeja e índice con PostgreSQL en
  solo lectura: HTTP 200, cero escrituras. El índice contiene ocho reportes,
  sin tarjeta duplicada ni área complementaria sobrante.
- Django y migraciones sin incidencias; Ruff de los archivos modificados limpio.
- Contratos de señales revisados; la señal de inicialización de módulos no
  cambió. Se actualizó la huella del archivo que también contiene `Recurso`.
- Suite integral única: **1.806 pruebas**, una omitida, cinco fallos y un error
  en 1.209,819 segundos. Arrancó antes de los últimos ajustes y conservó en
  memoria esa versión: tres incidencias correspondieron a clasificación/filtro
  del administrador y tres a la huella del contrato de señales. Las
  correcciones están cubiertas por las 73 pruebas posteriores y la verificación
  del índice en solo lectura. No se repitió la suite integral ni se presenta
  esa ejecución como completamente aprobada.

El siguiente bloque técnico es el paso 4: filtros de período compartidos,
entradas inválidas controladas, subtipos y rendimiento de reportes. La
configuración institucional del paso 3 sigue siendo necesaria para operarlo.
