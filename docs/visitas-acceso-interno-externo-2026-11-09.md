# Visitas internas y externas

La tercera ruta del asistente conserva sus cinco pasos y la agenda compartida.
La tabla de asistentes ocupa el ancho del formulario y deja de estar centrada.

Las visitas internas requieren sesión y cuenta institucional interna. La búsqueda
incluye al responsable para que pueda añadirse si también asistirá. Cada selección
completa documento, nombre, rol, teléfono y correo desde el perfil. El servidor
resuelve nuevamente las cuentas, comprueba perfil completo, actividad y duplicados,
recalcula el conteo y conserva el vínculo con el usuario en AsistenteVisita.
Los datos del perfil se muestran de solo lectura. Al cambiar de categoría se
conservan por separado las listas introducidas durante esa edición.

Las visitas externas permiten enviar sin crear una cuenta. Se exigen nombre,
correo y celular del responsable, institución, grupo, horario y aceptación de
condiciones. Un correo que ya pertenece a una cuenta interna exige iniciar sesión.
Los organizadores autenticados pueden coordinar también grupos externos; sus
datos proceden de su cuenta. Recursos y servicios siguen exigiendo sesión.
La búsqueda de cuentas nunca está disponible para visitantes anónimos.

El envío externo conserva la protección CSRF y las validaciones de agenda, aforo,
recorrido, guías y asistentes. Entrega una referencia de solicitud pendiente;
no abre un comprobante privado ni promete un envío automático de correo.
La unidad ve los contactos y puede revisar, abrir el comprobante y aprobar la visita.

## Datos y verificación

La migración `reservas.0003_visitas_internas_externas` permite un responsable sin
cuenta, añade la categoría y vincula asistentes internos con sus usuarios. Fue
aplicada únicamente en default local. La visita y los tres asistentes existentes
se compararon campo por campo con el respaldo y se conservaron. Respaldo local:
`var/backups/visitas/acceso-previo-20261109-060218-587970.json` (UTC).

Se verificaron en PostgreSQL temporal las ocho pruebas de acceso, registro sin
cuenta, contacto, CSRF, identidad, conteo y revisión/aprobación sin cuenta, además
de las regresiones de asistentes, visitas y calendario. La preparación inicial
de QA se corrigió añadiendo una clave de firma exclusiva de pruebas; dos
expectativas de pruebas se corrigieron para respetar el nombre real de la cookie
CSRF y el aforo compartido de la agenda.

Las pruebas DOM verifican las cinco etapas, búsqueda/selección, lectura del perfil,
conteo, duplicados, conservación al cambiar de categoría y bloqueo por sesión.
Ruff, sintaxis JavaScript, Django check y consistencia de migraciones correctos.
Las pruebas no crearon reservas ni usuarios de demostración en la base operativa.
La revisión visual mediante control del navegador sigue sin estar disponible.
