# Niveles y rutas administrables

Continuacion 147 de M02.1. Configuracion institucional > Revisiones de niveles
academicos tiene editor propio, borradores, publicaciones e historial.
No cambia fechas/calendarios oficiales, credenciales, pertenencia ni permisos.
El calendario se conserva con su proveedor actual y sera el siguiente bloque.

## Editar y publicar

1. Crear revision muestra la version en uso, o el despliegue si no hay publicacion.
2. Agregar/editar niveles con codigo estable y nombre visible. Marcar cuales
   pueden seleccionar estudiantes. Retirar como historico conserva referencias.
3. Crear rutas seleccionando niveles en orden. Cada ruta necesita dos niveles
   estudiantiles como minimo; no repetir un nivel ni usarlo en dos rutas.
4. Revisar el texto solicitado por la compuerta del perfil y guardar borrador.
5. Abrir Revisar y publicar: comprobar activos, historicos, estudiantes, rutas
   y compatibilidad. Confirmar publica una revision inmutable nueva.
6. Para recuperar, abrir una publicacion anterior y revisar/publicar de nuevo,
   o crear una revision desde sus datos. La recuperacion debe ser compatible.

Guardar no activa cambios. Publicar requiere cuenta staff activa, view del
modelo y publicar_niveles; guardar requiere add. Comandos recargan permisos y
cuenta, bloquean actor/puntero y cotejan base mostrada y base original del
borrador. CSRF y checkbox obligatorios; PUT 405. No autoasignar permisos.
Una revision obsoleta necesita un borrador nuevo y otra revision administrativa.

Conservar TODOS los codigos previos, incluso sin uso, en activos/historicos.
No es una operacion de borrado sobre perfiles, reservas o vinculaciones.
Codigo historico mantiene lectura/admin; el estudiante debe actualizar un
nivel retirado antes de operar. Rehabilitar un nivel no normaliza perfiles.
Cambiar etiquetas afecta consultas actuales; documentos archivados no se
reescriben, y no se congelan etiquetas por registro operativo.

## Rutas y confirmacion

Cambiar una ruta modifica propuestas futuras. El estudiante sigue confirmando
o corrigiendo el avance entre periodos compatibles; publicar no confirma por
el ni altera su nivel/perfil o clasificacion historica. Finales, historicos y
niveles independientes no inventan un salto a otro programa.

Las rutas son disjuntas por codigo, no se infieren por nombre de facultad o
carrera. No implementa bifurcaciones, planes de estudio simultaneos con un
mismo codigo ni versiones de ruta enlazadas por programa/registro. Esas
necesidades requieren relaciones explicitas y su propia validacion antes de
habilitar automatismos adicionales.

## Estructura y validacion

```text
apps/configuracion_institucional/
  niveles/                    modelos, comandos, lecturas, forms y admin
  editor_revisiones.py         flujo admin compartido con catalogos
  formularios.py               titulo y JSON validado compartidos
  versionado.py                autoridad, bloqueos e historial comunes
  migrations/0003_*            dos tablas nuevas
  templates/admin/.../niveles/ editor, widget y vista previa
  static/.../editor.css        estilos compartidos
  static/.../niveles.js        filas y rutas progresivas
  tests/test_niveles.py        casos y consumidores reales
apps/core/
  niveles.py                  contrato puro y transicion conservadora
  presentation/niveles.py      choices compatibles con migraciones
  presentation/niveles_institucionales.py contexto por solicitud/tarea
```

Hasta 200 niveles activos y 200 historicos, codigos de hasta 30 caracteres,
JSON maximo 100.000 caracteres. Rechaza claves/JSON duplicados, HTML, codigos
ambiguos, ciclos y rutas cruzadas. JS usa DOM/texto, no eval/HTML de datos.
Un payload sincronizado evita miles de campos POST. Sin JS queda campo JSON
con el mismo validador servidor. Vista previa expone rutas y efecto futuro.

La app tiene seis modelos propios; ORM operativo sigue webcitt. No importa
verticales en su codigo operativo. Adaptadores/contratos del nucleo mantienen
las rutas Python usadas por migraciones. El editor compartido no duplica el
flujo administrativo ni mezcla los punteros de catalogos y niveles.

ACADEMIC_LEVELS_PROVIDER es un proveedor fijo registrado; vacio utiliza solo
despliegue. E009 valida registro/app sin SQL y E003 valida siempre base de
despliegue. Middleware despues de Locale resuelve una version por solicitud,
ambitos anidados reutilizan/reset incluso con excepciones. Verificacion,
propuesta y confirmacion de periodo abren el ambito fuera de HTTP.
Otras tareas/importadores que validen modelos directamente necesitan:

```python
from apps.core.presentation.niveles_institucionales import con_niveles_institucionales
with con_niveles_institucionales():
    # Validar con niveles_actuales/choices de la version publicada.
    ...
```

Namespaces de producto/institucion distintos no heredan publicaciones. No
multiinstitucion sobre una base compartida. Proyeccion ausente/invalida usa
base y aviso generico, sin PII; savepoint conserva transaccion exterior.
No garantiza continuidad del motor/proceso compartido ante caida global.

Publicar coteja codigos previos y dieciseis campos del auditor con propuesta
explicita, sin publicar primero. Fallo de compatibilidad/integridad bloquea
sin alta parcial ni HTTP 500. auditar_catalogo_institucional resuelve ambos
proveedores en modo estricto: no certifica fallback, solo conteos/campos sin
nombres/correos. No es certificacion de escritores concurrentes o SQL directo.

## Migracion y recuperacion

0003 agrega dos tablas, dos ContentTypes y cinco permisos; no traslada datos.
Ensayo en copia: 0002 -> 0003 -> 0002 -> 0003; 140 tablas anteriores identicas
en filas/columnas/indices/claves y nuevas vacias. Copia retirada. Reversa solo
ensayada en vacio: conservar/conciliar historial antes de revertir tras uso.
Guardas bloquean save/update/bulk/delete ordinarios; SQL privilegiado puede
eludirlas. Puntero sin admin/default permissions, unico por instalacion.

Cambiar rama no revierte PostgreSQL/media. Nuevos codigos requieren auditoria
contra proveedor anterior antes de volver a codigo previo. Desactivar el
proveedor no convierte datos. No limpiar ContentTypes/permisos/historial
automaticamente. M01 institucional sigue abierto; no extraer datos aun.

## Evidencia de cierre

14 pruebas nuevas; integracion 89 OK (22.506 s).
Ajuste final de navegacion: 14 OK (2.574 s).
Suite completa: 983 pruebas, OK. Una omitida; 1008.144 segundos.
Ruff/check/makemigrations/plantillas ES/EN/JavaScript y locale --check OK.
Traducciones ES/EN: 8590 mensajes.

Chrome final: 296 casos ES/EN, siete anchos 360..1920 y cuatro estados
de pertenencia; reserva/guias/admin/verificacion/login, editor de catalogos y
niveles, historia y publicaciones compatibles/bloqueadas. Alta/ruta/retiro
sincronizan JSON; payload 201 niveles se mantiene visible/rechazado, sin
truncar. Textos ingles de nivel/remover verificados tras corregir dos ausentes;
suite inicial interrumpida y reiniciada para validar version final. Capturas
ingles 360 editor y vistas previas inspeccionadas. Sin errores JS, overflow,
recortes o solapamientos medidos. DB/sesiones QA retiradas, sin cuentas reales
aprobadas/normalizadas. No certifica toda la UI, dispositivos fisicos, ASGI,
streaming, carga masiva o accesibilidad completa.

Migracion 0003 aplicada localmente despues de suite y respaldo protegido:
dump ignorado con ACL operador/SYSTEM, checksum y catalogo verificado. No se
afirma restauracion integral de este dump ni cierre de M01. Filas/esquema/
indices/claves de 140 tablas previas identicos; metadata aditiva esperada:
una migracion, dos ContentTypes y cinco permisos. Cero revisiones/publicaciones
de niveles o concesiones explicitas nuevas reales; datos/permisos anteriores
conservados. Media no modificada. Auditor estricto confirma dieciseis campos
compatibles y calendario anterior compatible, sin PII ni escrituras.
Servidor propio reiniciado --noreload, estaticos recogidos y diez rutas:
inicio/planta/login 200, perfil/listados/editores anonimos 302. Login conserva
CSRF, anonimo sin autoria y segmento externo. Sin login con cuenta real.
Tres overrides JS Grappelli preexistentes en collectstatic; no nuevos duplicados.

M02.1 siguiente: calendario persistente, paleta y consumidores editoriales.
M09 otras secciones; despues M02.2-M02.4 manifiestos/categorias/contratos.
M01 institucional requiere custodios, escritores, usuario DB minimo privilegio,
RPO/RTO, copia externa cifrada/inmutable y recuperacion aislada. M11 aislamiento
de infraestructura sigue pendiente. Esta entrega no certifica seguridad total.

## Continuacion 148

[Calendario persistente](calendario-academico-administrable.md) usa el mismo
editor comun. M02.1 sigue con paleta y consumidores editoriales; M09 otras secciones.
