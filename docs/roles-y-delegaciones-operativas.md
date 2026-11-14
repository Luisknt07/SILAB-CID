# Roles y delegaciones operativas

Bloque M02.1, 16 de septiembre de 2026. La instalacion pertenece a una
institucion; no crea multiinstitucion ni aislamiento de infraestructura.

## Datos personales y autorizacion

El tipo de usuario, carrera e institucion del perfil describen a quien
solicita. No asignan administracion de unidades. Un nombre visible, correo
institucional o tipo declarado no es por si mismo prueba de pertenencia.

La gestion sigue tres fuentes expresas: superusuario activo, administrador
principal activo de la unidad y responsabilidad activa con cuenta activa y
delegacion operativa valida. La delegacion pertenece a una unidad concreta.
El administrador principal y el superusuario conservan todos sus permisos;
el personal delegado conserva su matriz granular. Un responsable publico sin
cuenta es un contacto y no puede operar el panel.

La verificacion institucional de tipos declarados, condiciones docentes y
segmentos tarifarios sigue pendiente. Este bloque fortalece las delegaciones
operativas; no convierte el registro academico en una credencial verificada.

## Distribucion de responsabilidades

| Archivo | Responsabilidad |
| --- | --- |
| apps/core/roles.py | Modulos y roles conocidos, recomendaciones neutrales y validacion/resolucion de matrices; sin Django o modelos |
| config/roles.py | Lectura de OPERATIONAL_ROLES_JSON, sin ejecutar codigo ni aceptar claves duplicadas |
| apps/core/presentation/roles.py | Adaptador de configuracion Django sin consultar unidades |
| apps/core/checks.py | slcid.E006 impide iniciar con una politica invalida |
| webcitt/domains/unidades/permisos.py | Vinculacion concreta, cuenta activa y alcance de la unidad; mantiene la interfaz compatible |
| webcitt/models/espacios.py | Validacion de la delegacion al editar ResponsableUnidad |

El nucleo no importa verticales; cada vertical utiliza el mismo contrato sin
compartir responsables ni sus datos. Esto no extrae modelos de webcitt ni
implementa todavia los manifiestos de habilitacion de M02.2.

## Configuracion y administracion

Sin OPERATIONAL_ROLES_JSON se mantienen las recomendaciones anteriores para
coordinacion, responsable_tecnico, laboratorista, tecnico, soporte y otro.
Las facultades, siglas o marca de la institucion no intervienen en ellas.
Una instalacion puede proporcionar un objeto JSON de rol a lista de modulos:

```json
{
  "coordinacion": ["reservas", "agenda", "recursos", "reportes"],
  "responsable_tecnico": ["agenda", "recursos", "mantenimiento"],
  "laboratorista": ["recursos", "inventario"],
  "tecnico": ["recursos", "mantenimiento"],
  "soporte": ["agenda"],
  "otro": []
}
```

El objeto sustituye las recomendaciones, no se mezcla implicitamente con las
predeterminadas. Un rol omitido no tiene recomendaciones; una delegacion
expresa valida puede concederle permisos. El cambio se aplica tras reiniciar
el proceso. Ejecutar manage.py check antes de ponerlo en servicio.

La configuracion no asigna cuentas y no reemplaza la matriz administrada de
cada responsable. Para modificar una persona, usar el panel de personal bajo
el administrador principal o el inline de Responsables de unidad del admin
Django con los permisos correspondientes. La matriz existente admite, por ejemplo:

```json
{"reservas": false, "inventario": true, "finanzas": false}
```

Una clave ausente conserva la recomendacion del rol. Un false expreso prevalece
sobre ella. Las recomendaciones de reservas para responsables tecnicos,
laboratoristas y soporte requieren recibe_reservas; coordinacion conserva su
recomendacion anterior. Una delegacion expresa sigue prevaleciendo.

Solo se aceptan objetos con modulos conocidos y valores true/false reales.
Textos como "false", numeros, listas, null o claves desconocidas son invalidos.
La edicion muestra un error de campo en ES/EN. Al leer un registro invalido se
deniega su matriz completa, incluso si se escribio sin validar; no se corrige
ni se concede acceso mediante una conversion automatica.

Desactivar la cuenta o el responsable revoca las operaciones. La matriz se
conserva para revisar o reactivar. permisos_operativos_responsable es una
previsualizacion para el formulario, incluso al desactivar: no autoriza
operaciones. La autorizacion usa permisos_operativos_unidad. Cambiar una
politica afecta claves que siguen sin configurar, pero no borra decisiones
expresas. Desactivar una responsabilidad no revoca a un administrador principal;
para eso cambiar el administrador o desactivar su cuenta.

Al desarrollar una accion nueva, comprobar puede_operar_modulo_unidad para
el modulo y la unidad reales antes de escribir datos. puede_gestionar_unidad
permite entrar al panel de esa unidad, pero no concede todos sus modulos.
Las operaciones de personal exigen ademas puede_administrar_personal_unidad;
una delegacion de configuracion no reemplaza esa restriccion. No usar la
previsualizacion del formulario como autorizacion ni aceptar un nombre de
unidad del cliente sin resolver y comprobar su alcance en el servidor.

## Validacion y limites

19 pruebas nuevas: datos malformados, precedencia de false, configuracion
inmutable, JSON duplicado, importacion independiente, tipo declarado sin
privilegios, cuatro tipos de unidades, revocacion/reactivacion, cuenta inactiva
incluyendo superusuario/principal y cuenta sin guardar, validacion del modelo, endpoint real que
responde 403 y errores traducidos. Las 35 pruebas focalizadas pasan (21.475 s). Las 19 nuevas vuelven a pasar
en la version final (0.589 s).

Auditoria de solo lectura de la base activa: cero matrices invalidas, roles
desconocidos o delegaciones activas con cuentas inactivas. No se modificaron
datos, esquemas, permisos Django ni usuarios existentes.

Fuentes de criterio: [autenticacion de Django 5.2](https://docs.djangoproject.com/en/5.2/ref/contrib/auth/)
explica que is_authenticated no comprueba actividad ni permisos;
[validacion de modelos](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects)
explica que save no llama automaticamente a full_clean. Por eso hay comprobacion
de actividad y validacion de lectura ademas de la validacion al editar.

Siguiente: verificacion institucional de pertenencia y tipos declarados, con
trazabilidad y conservacion de reservas historicas; luego tarifas historicas.
M01 institucional continua abierto antes de futuros traslados de datos. Seguir
la [ruta modular](ruta-ejecucion-arquitectura-modular.md).

Suite completa del bloque: 893 pruebas, OK, una omitida, 1047.899 segundos.
Ruff, Django check y compilacion ES/EN correctos; makemigrations sin cambios.
Historial: CODEX_CONTEXT.md, seccion 142.

Continuacion 143: [revision institucional de pertenencia](verificacion-institucional.md).
Administra aprobaciones, rechazos y revocaciones con historial; no asigna roles
operativos ni cambia las matrices de este bloque. Consumidores de autoria y
segmentos tarifarios deben conectarse en la siguiente entrega.

Continuacion 144: [autoria y tarifas con pertenencia efectiva](pertenencia-guias-y-tarifas.md).
No concede autoria/lectura de terceros por is_staff ni descuento por delegacion.
Nuevas cotizaciones registran la revision usada; operaciones anteriores
conservan su segmento y los autores conservan correccion de documentos propios.
No modifica datos reales, aprueba cuentas automaticamente ni mueve esquemas.
