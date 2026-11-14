# Catalogo academico administrable y versionado

## Propiedad y alcance

El editor vive en apps/configuracion_institucional/catalogos/. Tiene modelos,
consultas, servicios, formulario y administrador propios. Sus templates y
estaticos pertenecen a la misma app. No importa modelos de webcitt: usa el
auditor del nucleo, que descubre campos de choices en las apps instaladas.
No se copian facultades/carreras a cada laboratorio ni se extraen datos.
Compartir proceso y PostgreSQL no asegura aislamiento de todos los fallos.

Versiona dependencias, carreras academicas, referencias historicas y tipos
para los que se requiere carrera. Los codigos de tipo de usuario siguen
estables; no concede grupos, permisos o pertenencia. Niveles, calendario y
politicas regionales conservan sus proveedores separados de despliegue.
Su edicion persistente no forma parte de esta entrega.

## Secuencia del administrador

1. Configuracion institucional > Revisiones de catalogo academico > Agregar.
2. Nombrar la revision y editar filas: codigo, nombre y dependencia de carrera.
   Agregar dependencia/carrera/referencia historica y seleccionar tipos que
   requieren carrera. Pasar a historica conserva codigo/nombre de una carrera.
3. Guardar borrador. No cambia el catalogo publicado ni datos operativos.
4. Abrir Revisar y publicar: propuesta agrupada, conteo de campos auditados y
   bloqueos por incompatibilidad. La confirmacion requiere checkbox y POST CSRF.
5. Un publicador autorizado confirma. El servicio repite validacion/auditoria
   y compara base bajo bloqueo; crea snapshot nuevo y actualiza puntero unico.
6. Historial de lectura: En uso marca actual, Publicada es estado historico.
   Crear revision desde estos datos permite partir de una version anterior.
   Restaurar/publicar una version anterior crea otra publicacion si sigue siendo
   compatible, sin borrar historia. Si perderia codigos agregados despues, se
   bloquea: crear una propuesta que los conserve, no restaurar silenciosamente.

Editor y publicador pueden ser distintos o una cuenta con ambos permisos.
Guardar exige cuenta activa staff y add_revisioncatalogoacademico; publicar
exige view_revisioncatalogoacademico y publicar_catalogo. Superusuario activo
conserva autoridad Django. No hay concesiones automaticas a cuentas reales.
El actor se recarga antes de escribir; permisos cacheados/revocados no bastan.
Bloquear User no serializa todas las modificaciones SQL de sus grupos.

## Compatibilidad obligatoria

Una publicacion conserva todos los codigos de dependencias y carreras de la
base anterior, aunque aun no tengan registros. Esto mantiene referencias para
formularios/solicitudes que ya estaban en curso. Una carrera puede pasar a
historica y dejar de ofrecerse para clasificaciones nuevas. Una dependencia
existente no se retira en este bloque; retirar codigos de manera destructiva
requiere otro procedimiento coordinado con todos los escritores.

No reasignar un codigo de carrera existente a otra dependencia. La publicacion
conserva un mapa de relaciones academicas incluso al retirarla; reactivacion
mantiene dependencia original. Clasificaciones historicas no academicas del
legado no se reutilizan como carreras. Para otro significado, usar codigo nuevo.
Nombres/etiquetas pueden corregirse; las versiones guardadas no se reescriben.
Los reportes que consultan choices actuales pueden mostrar la etiqueta actual:
esta entrega no agrega snapshots de etiquetas a cada registro operativo.
Comprobantes archivados y cotizaciones anteriores no se regeneran.

Borrador obsoleto necesita revision nueva; cambiar su base oculta no lo hace
vigente. Puntero unico/PK y savepoint serializan primeras publicaciones y el
servicio compara base antes de confirmar. El auditor comprueba codigos y
relaciones en consumidores instalados; una referencia invalida bloquea el alta.
La conservacion de codigos/relaciones contiene escrituras de solicitudes previas;
no certifica que todos los escritores adopten simultaneamente cambios de
requisitos de carrera. Coordinar estos cambios y revisar perfiles pendientes.
El retiro puede exigir actualizar una carrera de perfil antes de reservar o
mantener verificacion vigente; no aprueba, reasigna o normaliza identidades.

## Contrato, interfaz e idiomas

200 dependencias internas y la opcion reservada externo; 2.000 carreras y
2.000 historicas. Codigos minusculos de hasta 50 caracteres; nombres en texto
simple <=250. Sin HTML/control, duplicados, claves desconocidas o dependencias
inexistentes/externas para carreras. Politica de carrera usa tipos internos,
sin duplicados y con al menos una carrera disponible. Nombre de revision <=100.

El formulario transforma filas en un unico payload JSON <=1 millon de
caracteres. Evita aumentar globalmente DATA_UPLOAD_MAX_NUMBER_FIELDS para
permitir catalogos grandes. Parser servidor rechaza claves duplicadas y valida
el contrato; JavaScript solo facilita edicion, no autoriza/publica.
Sin JavaScript queda textarea validada. Valor invalido permanece editable y
errores se muestran antes de guardar. UI ES/EN; nombres institucionales del
contenido se conservan originales, sin traduccion automatica.

## Proveedor y consumidores

ACADEMIC_CATALOG_PROVIDER es una ruta fija instalada en settings, no codigo
elegible por administrador/cliente. Cadena vacia utiliza el despliegue;
check E008 exige app/proveedor coherentes. Checks/migraciones/imports no
consultan tablas del catalogo. catalogo_de_despliegue valida la base;
catalogo_actual usa la proyeccion inmutable del contexto, o la base fuera de el.

El middleware resuelve una publicacion por solicitud, despues de Locale.
Ambitos anidados reutilizan la version y reset ocurre tambien con excepciones.
Los proveedores existentes de choices conservan rutas de migracion. Registro,
perfil, admin, reservas, participantes, periodos e indicadores ven esa misma
version durante la solicitud, sin cache global entre usuarios.
Verificacion institucional abre el ambito tambien fuera de HTTP; no obtiene
pertenencia por publicar una carrera. Nuevas tareas/importadores que validen
datos operativos directamente deben usar:

```python
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional

with con_catalogo_institucional():
    # Validar/operar con catalogo_actual y los choices compartidos.
    ...
```

Catalogo publicado valida estado, estructura, relaciones reservadas y codigos
de producto/institucion del despliegue. Otra identidad no hereda la publicacion.
No es multiinstitucion/tenant ni licencia comercial. No cambiar codigos para
adoptar datos ajenos sobre la misma base.

Fallo de tabla/proyeccion usa base y advertencia generica sin nombres/correos.
Savepoint evita romper transaccion exterior; no sostiene toda la operacion
ante caida global del motor. Auditor explicito usa modo estricto y no certifica
una proyeccion invalida que haya requerido fallback:

```bash
.venv/Scripts/python.exe manage.py auditar_catalogo_institucional
```

Solo conteos/campos/modelos, sin identidades personales ni escrituras;
--database conserva seleccion de alias configurado. Auditoria y checks de
aplicacion no sustituyen custodia SQL o respaldos institucionales.

## Esquema y recuperacion

0002 agrega dos tablas propias y no mueve/modifica las 138 anteriores. Ensayo
en copia protegida: 0001 -> 0002 -> 0001 -> 0002, con nuevas tablas vacias;
datos/columnas/indices/claves anteriores identicos. La copia fue retirada.
Historial bloquea save/update/bulk/delete; SQL privilegiado puede eludirlo.
Puntero no tiene admin/permisos predeterminados. Metadata nueva: dos modelos
y cinco permisos, sin asignaciones reales automaticas.

Despues de usar editor no revertir esquema sin preservar/conciliar historia.
Volver a codigo previo puede usar tablas conservadas, pero codigos nuevos
creados bajo catalogo publicado deben auditarse contra el proveedor anterior.
Desactivar proveedor no migra/normaliza esos registros. Cambiar rama no
restaura base/media ni revierte datos posteriores. No limpiar ContentTypes
automaticamente. M01 institucional y extraccion de datos siguen pendientes.

## Validacion y siguiente bloque

19 pruebas nuevas; integracion final 81 pruebas OK (22.479 s).
Suite completa: 969 pruebas, OK. Una omitida; 979.411 segundos.
Ruff/check/makemigrations/plantillas ES/EN y JavaScript correctos.
Traducciones ES/EN: 8556 mensajes. Chrome 224 combinaciones: cuatro estados
de pertenencia, siete anchos 360..1920 y ambos idiomas; reserva/guias/admin,
verificacion/editor/historial/publicacion y login. Alta/retiro sincroniza JSON;
incompatibles sin confirmacion. Sin errores JS, overflow o recortes medidos.
Capturas ingles 360 inspeccionadas. Base/sesiones QA retiradas. No certifica
toda la interfaz, carga masiva, dispositivos fisicos o accesibilidad completa.

Migracion 0002 aplicada en desarrollo tras suite y respaldo local protegido:
dump ignorado, ACL operador/SYSTEM, checksum y catalogo verificado. No se afirma
restauracion integral de este dump ni cierre de M01. Filas/esquema/indices/claves
de 138 tablas previas identicos; metadata aditiva esperada: una migracion,
dos ContentTypes y cinco permisos. Cero revisiones/publicaciones del catalogo
o concesiones explicitas nuevas reales; datos/permisos previos conservados.
Media no modificada. Auditor estricto: dieciseis campos compatibles, sin PII
ni escrituras. Servidor propio reiniciado --noreload y estaticos recogidos;
inicio/planta/login 200 y perfil/listados/editores anonimos 302 (ocho rutas).
Login conserva CSRF; anonimo sin autoria y segmento externo. Sin login ni
aprobacion de cuenta real. Tres overrides JS Grappelli preexistentes en
collectstatic, no duplicados nuevos.

La continuacion 147 incorpora [niveles administrables](niveles-academicos-administrables.md)
y comparte el flujo admin/formularios/estilos con catalogos.
M02.1 sigue abierto: persistencia del calendario, paleta y consumidores
editoriales. M09 admin propio de otras secciones; despues M02.2-M02.4
manifiestos/categorias/contratos. Esta entrega no cierra M01 ni el aislamiento
de infraestructura M11.
