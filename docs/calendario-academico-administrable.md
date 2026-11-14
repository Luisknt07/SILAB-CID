# Politica de calendario administrable

Continuacion 148 de M02.1. La app `configuracion_institucional` administra la
politica academica con el mismo editor compartido de catalogos y niveles.
Los periodos, versiones, semanas y vinculaciones mantienen su propietario
operativo y sus tablas `webcitt`. La politica no duplica fechas oficiales.

## Recorrido administrativo

Configuracion institucional -> Revisiones de politica de calendario -> Agregar.
El responsable configura ciclos, ambitos, seleccion automatica, ambito inicial
y semanas. Guardar crea un borrador; no activa sus cambios. El historial es de
lectura: copiar una revision produce un borrador nuevo. Revisar y publicar
muestra activos, historicos, defaults y problemas de compatibilidad. Confirmar
repite la comprobacion con autoridad fresca y cambia un puntero atomico.

Conservar codigos estables. Retirar como historico evita ofrecerlos para nuevos
periodos y permite leer/validar los existentes. Los ciclos mantienen su tipo
ordinario, extraordinario o interperiodo, incluso si no tienen registros aun.
No borrar ni reutilizar codigos antiguos para otro significado. Las etiquetas
pueden cambiar; no se congelan etiquetas por cada registro operativo.

La publicacion nunca genera periodos, fechas o semanas; tampoco modifica
reservas, suspensiones, permisos operativos ni vinculaciones. Las fechas
oficiales y reformas siguen en Periodos academicos y Versiones del calendario.
La accion existente de generar semanas conserva su idempotencia y restricciones.

## Contrato y efectos

El contrato puro en `apps/core/calendario.py` conserva nueve campos. Sus ciclos
requieren codigo de un caracter A-Z/0-9, etiqueta simple y tipo conocido.
Ambitos: codigo de hasta treinta caracteres, etiqueta simple y hasta doscientas
filas por lista. Los activos/historicos son disjuntos. Los ciclos usan hasta
treinta y seis filas por lista; la unicidad global y el alfabeto limitan el total.

Los ambitos de operacion son un subconjunto activo. Cambiarlos modifica la
asociacion automatica futura de perfiles/reservas; una lista vacia evita esa
asociacion. No elimina relaciones explicitas ni bloquea por si misma reservas.
El ambito predeterminado debe permanecer activo. Retirar el predeterminado
requiere seleccionar otro antes de guardar. Las semanas son enteros, sin
booleanos: 1 <= minimo <= predeterminadas <= maximo <= 24. No ampliar a 52 sin
un bloque propio de esquema, datos, recuperacion y conciliacion.

Antes de publicar se conservan todos los codigos anteriores y los tipos de
ciclo. El auditor comprueba periodos con ciclos/ambitos desconocidos, relacion
ciclo/tipo, rangos de semanas y semanas fuera del plan o fechas. Solo comunica
conteos; no exporta nombres, motivos, documentos ni datos de usuarios.
Las consultas usan la politica candidata explicitamente y no una cache de
la politica anterior. El auditor CLI usa el proveedor publicado en modo estricto
y el alias `--database`; una proyeccion rota no se certifica mediante fallback.

Los ambitos simultaneos conservan la seleccion por fechas reales y desempate
actual. No se agrega prioridad inferida por programa, facultad o unidad; una
institucion que la necesite debe relacionarla explicitamente en otro bloque.

## Arquitectura y seguridad

`calendario/models.py` conserva revisiones inmutables y un puntero unico.
`selectors.py` valida contrato, estado publicado e identidad producto/institucion.
`services.py` concentra guardar/publicar, bloqueo de puntero, base esperada y
compatibilidad. `forms.py`, `admin.py`, plantillas y JS pertenecen a esa app.
El editor compartido evita repetir flujos administrativos de catalogos/niveles.
La app pasa a ocho modelos propios; no extrae ORM operativo ni sus permisos.

Permisos especificos: agregar/ver `RevisionPoliticaCalendario` y
`publicar_calendario`. Ser staff no basta para publicar. El servicio vuelve a
consultar autoridad vigente; una cache previa de permisos no autoriza una
escritura tras revocacion. El puntero carece de admin y permisos predeterminados.
La confirmacion requiere POST y CSRF. PUT devuelve 405. La revision nueva
registra autor, base y fuente; guardar no acepta metadata de autoria/estado
del navegador. Una base obsoleta bloquea publicar hasta copiar/revisar otra vez.
Restaurar una publicada crea una nueva revision, sin borrar el historial.

El proveedor fijo `ACADEMIC_CALENDAR_PROVIDER` lo controla el despliegue:
`apps.configuracion_institucional.calendario.selectors.calendario_publicado`.
Cadena vacia desactiva esa proyeccion; `slcid.E010` rechaza rutas no registradas
o app ausente. `slcid.E004` siempre valida el contrato de despliegue sin SQL.
No importar codigo elegido desde datos del administrador.

El middleware resuelve una politica por solicitud mediante ContextVar y limpia
su contexto al salir. Periodo vigente, resolucion de periodo de reserva y accion
de generar semanas abren tambien ese contexto para llamadas directas.
Otras tareas, constructores/defaults, formularios y validaciones ORM fuera de
HTTP deben abrir `con_calendario_institucional(database=...)` explicitamente;
sin contexto usan el contrato de despliegue. No hay SQL al importar/checkear
choices/defaults. Lectura normal con tablas ausentes, identidad ajena o revision
invalida usa despliegue y registra aviso generico. Auditoria estricta falla.
No demuestra ASGI/streaming ni aislamiento por proceso.

El editor progresivo escribe un unico JSON. Sin JS se puede editar el mismo
contrato. Se rechazan claves duplicadas/desconocidas, HTML, ciclos invalidos,
payload mayor de 100.000 caracteres, filas excesivas y limites incompatibles.
Un POST rechazado mantiene texto original y desactiva el editor guiado; no
normaliza claves duplicadas ni recorta filas mediante JSON.parse. Editar JSON
manualmente desconecta el guiado y conserva el texto enviado. El servidor
valida siempre; el navegador no otorga autoridad ni garantiza compatibilidad.

Las guardas ORM no protegen de SQL privilegiado, escrituras bulk operativas sin
validacion ni escritores concurrentes externos. El bloqueo serializa las
publicaciones de esta politica; no coordina automaticamente todos los cambios
simultaneos de periodos/semanas. M01/M11 siguen abiertos. No prometer seguridad
total o que un fallo de PostgreSQL/proceso compartido queda aislado por app.

## Migracion y recuperacion

0004 agrega dos tablas, dos ContentTypes y cinco permisos. No convierte datos
ni concede esos permisos a cuentas/grupos reales. Ensayo en copia restaurada:
0003 -> 0004 -> 0003 -> 0004; las 142 tablas anteriores conservan filas,
columnas, indices y claves; django_migrations cambia por diseno. Copia retirada.
La reversa se ensayo solo en tablas nuevas vacias. Conservar y conciliar
historial antes de cualquier reversa tras uso.

Cambiar de rama no restaura PostgreSQL/media. Codigos/limites nuevos pueden no
ser compatibles con codigo anterior o proveedor desactivado: auditar contra
su contrato antes de volver. No limpiar ContentTypes, permisos o publicaciones
automaticamente. El respaldo local no cierra recuperacion institucional,
copia externa cifrada/inmutable, custodios, RPO/RTO o minimo privilegio DB.

## Evidencia

14 pruebas nuevas; integracion final 74 OK (9.537 s).
Suite completa: 997 pruebas, OK. Una omitida; 465.637 segundos.
Ruff/check/makemigrations/JavaScript y locale --check OK.
Traducciones ES/EN: 8622 mensajes.

Chrome final: 370 casos ES/EN, siete anchos 360..1920, cuatro estados de
pertenencia; reservas/guias/admin/verificacion/login, catalogos/niveles y cinco
vistas de calendario. Alta/retiro de ciclo/ambito, operacion/default sincronizan
JSON. Payload 201 ambitos visible/rechazado y JSON manual con clave duplicada
conservado sin sobrescribir. Capturas ingles 360 editor y bloqueo inspeccionadas;
tipos semanticos traducidos. Primera corrida corrigio fixture Save Draft y
traducciones faltantes; final repetida OK. Sin errores JS, overflow, recortes o
solapamientos medidos. DB/sesiones QA retiradas; no cuentas reales aprobadas ni
roles concedidos. No certifica toda UI, dispositivos fisicos, accesibilidad,
ASGI/streaming, carga masiva ni aislamiento del proceso/motor compartido.

0004 aplicada localmente despues de suite y respaldo protegido: dump ignorado
con ACL operador/SYSTEM, checksum y catalogo verificado. No se afirma restauracion
integral de este dump ni cierre de M01. Filas/esquema/indices/claves de 142 tablas
previas identicos; metadata aditiva esperada: una migracion, dos ContentTypes y
cinco permisos. Cero revisiones/publicaciones de politica o concesiones explicitas
nuevas reales; datos/permisos anteriores conservados. Media no modificada.
Auditores estricto academico (dieciseis campos) y de calendario compatibles, sin
PII ni escrituras. Servidor propio reiniciado --noreload, estaticos recogidos;
doce rutas: inicio/planta/login 200, perfil/listados/editores anonimos 302. Login
conserva CSRF; anonimo sin autoria y segmento externo. Sin login con cuenta real.
Tres overrides JS Grappelli preexistentes en collectstatic, sin nuevos duplicados.

M02.1 sigue con paleta y consumidores editoriales; M09 otras secciones y luego
M02.2-M02.4 manifiestos/categorias/contratos. No iniciar traslado de datos hasta
cerrar la puerta de recuperacion M01.

Referencias tecnicas: [transacciones de Django 5.2](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
y [choices/defaults](https://docs.djangoproject.com/en/5.2/ref/models/fields/#choices).
