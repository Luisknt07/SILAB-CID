# Grupo y finalidad: modelos y tabla de asistentes — 8 de noviembre de 2026

Se conserva el asistente de cinco pasos y la agenda aprobada. Este bloque
mejora únicamente la captura del grupo y la persistencia de sus asistentes.

## Pantalla

- Dos modelos de redacción para cada propósito: académico, institucional y
  comercial. Se adaptan al nombre de la unidad, temas publicados, institución
  y cantidad del grupo. El ejemplo se muestra junto al objetivo y se puede
  aplicar con «Usar modelo de redacción».
- El texto generado se actualiza con el contexto mientras no haya sido
  editado manualmente. Un cambio de propósito no sobrescribe una redacción
  propia; el botón permite reemplazarla expresamente por el modelo elegido.
- Se retira el rango de edades de esta pantalla; el campo histórico se conserva.
- Tabla editable con cédula/documento, nombres completos, rol (estudiante,
  profesor, administrativo u otro), celular y correo. Añadir/quitar filas,
  numeración, validación de duplicados y desplazamiento interno en móvil.
  Nombres y rol obligatorios en las filas con datos; documento y contactos
  opcionales. Las filas totalmente vacías no se envían.
- Conteo automático desde las filas con datos, o cantidad estimada cuando
  la lista se completará después. El calendario y los guías reciben el grupo
  actualizado. El servidor recalcula el modo automático y comprueba aforo.

## Datos

`reservas.0002_datos_asistentes_visita` añade rol, teléfono y correo a
AsistenteVisita. Los registros anteriores reciben cadenas vacías, sin
inventar roles o contactos. Se preservan nombre, documento e ingreso.
El envío del modal usa JSON estructurado; se conserva la compatibilidad
con las listas de texto anteriores. Se rechazan formatos rotos, roles no
válidos, correos inválidos, documentos duplicados y límites excedidos.

Los datos completos se muestran en la asistencia protegida por los permisos
existentes; no se publican en la agenda ni se crean cuentas para visitantes.

Migración aplicada en default local tras pruebas y respaldo:
`var/backups/visitas/asistentes-previos-20261109-044328-997869.json` (UTC).
Los tres asistentes y la visita previos se compararon íntegramente y se
conservaron. Sin solicitudes nuevas ni correos operativos de demostración.

## Verificación

La tabla se compactó en una superficie centrada de hasta 1120 px, con
columnas proporcionales, controles de 32 px y botones pequeños. La cabecera
permanece visible y el desplazamiento queda dentro de la tabla al superar
320 px o el 42 % del alto de pantalla. En pantallas estrechas conserva
desplazamiento horizontal interno para poder editar los datos.
El botón «Añadir fila» y Enter desde el último correo agregan asistentes;
el foco pasa a la nueva fila sin desplazar todo el modal. Verificados con
el componente DOM real: alta, eliminación, atajo Enter, conservación de
datos, conteo y navegación entre pasos. Django check y sintaxis JS correctos.
Este ajuste no modifica datos, migraciones ni el calendario compartido.

- 60 pruebas Django correctas con migraciones reales en PostgreSQL temporal:
  guardado de todos los campos, conteo revalidado, privacidad, validación de
  datos y regresión del asistente/calendario. Contenedor QA retirado al cierre.
- 21 pruebas JavaScript correctas de modelos, conteos y agenda compartida.
- Prueba DOM con HTML público actual y scripts completos en Frutas, FabLab,
  San Francisco y Cítricos sin áreas publicadas: edición de tabla, conteo,
  duplicados, quitar filas, redacción manual preservada, aplicación de modelos,
  cinco pasos y cambio entre las tres rutas correctos.
- Ruff, sintaxis JavaScript, migraciones y diferencias correctos.

Las pruebas DOM no acreditan geometría o apariencia en Chrome; la revisión
visual del navegador sigue sin estar disponible en esta sesión. Evidencias y
dependencia DOM exclusivamente bajo `var/qa-visitas-modal/`, fuera de Git.
Sin despliegue universitario; consultar Git para el commit local del bloque.
