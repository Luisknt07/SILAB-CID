# Presentacion institucional administrable

## Propietario y alcance

`apps/configuracion_institucional/` es una app Django instalada con modelos,
servicios, consultas, administrador, comando de auditoria y migracion propios.
Su codigo operativo no importa `webcitt`, laboratorios, plantas ni otros dominios. Su
unica relacion externa de persistencia es AUTH_USER_MODEL para atribucion.
Las plantillas administrativas estan dentro de templates/ en esa misma app;
sus pruebas estan en apps/configuracion_institucional/tests/. El inventario
incluye modelos propios, tablas, propietario, registro admin y permisos.
No se extraen ni cambian las tablas existentes. Comparte el proceso y la base:
esto separa responsabilidad de codigo, no proporciona aislamiento de motor.

El editor controla nombres visibles del sistema/institucion, contactos publicos,
rutas de logos estaticos instalados y colores versionados. Sin personalizacion
conserva la paleta anterior: [uso y alcance](paleta-institucional-administrable.md).
Siglas/codigos permanecen en el despliegue, igual que dominios OAuth, remitente
SMTP, credenciales, zona, catalogos y reglas de permisos. Cambiar un nombre
visible no modifica la pertenencia aprobada, las tarifas o las cuentas.

La guía para quien administra, sin detalle técnico, está en
[Guía para cambiar la presentación institucional](guia-presentacion-institucional.md).

## Ruta del administrador

1. Abrir Configuracion institucional > Presentaciones institucionales.
2. Agregar una presentacion. Los valores iniciales vienen de la publicacion
   actual; guardar crea un borrador y no modifica el portal.
3. Abrir la revision guardada y elegir Revisar y publicar. Se muestran los
   campos propuestos y se requiere una confirmacion POST protegida por CSRF.
4. Confirmar con autoridad de publicacion. El listado marca En uso solo en
   la revision activa; Publicada indica que una revision fue publicada en
   algun momento, no que todas las revisiones esten activas a la vez.
5. Para editar datos anteriores, Crear revision desde estos datos. El historial
   es de lectura y no permite cambiar/eliminar registros desde el administrador.
6. Para recuperar una presentacion anterior, usar Restaurar esta presentacion
   en su fila: se crea una publicacion nueva con referencia a la fuente y a la
   publicacion reemplazada. No se borra ni reescribe el historial.

El listado publica la ruta en pantalla y ofrece Revisar y publicar, Restaurar
y Crear revision desde estos datos en cada fila; el formulario agrupa los
campos en identidad, logotipos, respaldo instalado y paleta, cada bloque con
su descripcion. No hay accion de eliminar ni de desactivar: activar es
publicar y volver atras es publicar de nuevo la revision anterior.

Un borrador conserva la publicacion sobre la que se creo. Si otra publicacion
cambia esa base, el sistema exige una revision nueva; modificar el campo oculto
no convierte un borrador obsoleto en vigente. Cada confirmacion comprueba la
base mostrada y bloquea el puntero unico. Dos publicaciones basadas en la misma
version no pueden sobrescribirse silenciosamente. La segunda debe recargar.

## Permisos

| Accion | Autoridad |
| --- | --- |
| Guardar borrador | Cuenta activa staff + add_revisionpresentacion |
| Leer historial | Permiso view_revisionpresentacion en el administrador |
| Publicar/restaurar | Cuenta activa staff + view_revisionpresentacion + publicar_presentacion |
| Modificar/eliminar historia | No disponible |

El superusuario activo conserva la autoridad Django. Editor y publicador
pueden ser personas distintas o una cuenta con ambas autorizaciones. No se
asignan permisos automaticamente a cuentas reales por ser docentes o staff.
Los comandos recargan y bloquean al actor antes de decidir; no aceptan permisos
cacheados de una cuenta revocada. La revocacion concurrente de grupos/permisos
por SQL directo no queda serializada por este bloqueo de User: la atribucion
administrativa y la custodia del motor mantienen su procedimiento propio.

## Una proyeccion por ambito

El contrato puro `apps/core/identidad.py` sigue independiente de Django.
`identidad_de_despliegue()` no consulta datos y los checks validan esta base.
El middleware resuelve una publicacion por solicitud HTTP y la mantiene con
ContextVar. `identidad_actual()` y los context processors, HTML, admin y PDF
usan esa misma proyeccion durante la solicitud. Se restaura el contexto al
terminar, incluso con excepciones. No hay cache global de marca entre usuarios
ni consulta de tablas durante import/ready/check.

Correos de reservas resuelven el ambito tambien fuera de HTTP. Las nuevas tareas
o generadores de documentos que se invoquen directamente deben usar:

```python
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional

with con_presentacion_institucional():
    # Generar el documento/correo usando identidad_actual()/identidad_publica().
    ...
```

Fuera de ese ambito, identidad_actual devuelve la base del despliegue. Los
ambitos anidados reutilizan la misma revision. Este bloque no certifica
streaming diferido, todas las tareas futuras o todos los consumidores editoriales.

PUBLIC_IDENTITY_PROVIDER apunta al proveedor instalado en settings. Se puede
usar cadena vacia para operar solo con el despliegue. Retirar la app requiere
desactivar ese proveedor; check slcid.E007 detecta configuracion inconsistente.
El administrador no puede instalar codigo ni modificar esta ruta.

## Validacion y continuidad

La publicacion pertenece a las siglas y codigo del despliegue; no se aplica a
otra identidad que reutilice la base. No es multiinstitucion ni aislamiento
por tenant. No cambiar codigos para adoptar otra institucion sobre una base
con datos ajenos: cada instalacion comercial necesita sus datos e infraestructura.

Texto plano <=250 caracteres, correo validado y logos png/jpg/jpeg/webp locales.
No HTML, controles, rutas absolutas, traversal, URL externa, SVG o imagen no
instalada. Fuentes estaticas y STATIC_ROOT usan la misma resolucion segura.
Campo vacio permite retirar el contacto o mostrar las siglas como alternativa.
No hay subida de imagenes de marca ni secretos en estos formularios.
Los valores creados por el administrador se conservan como contenido original;
ES/EN traduce interfaz y mensajes, sin traducir automaticamente nombres propios.

Si la tabla/proyeccion no esta disponible o es invalida, el proveedor registra
una advertencia sin contenido privado y utiliza la identidad del despliegue.
Un savepoint evita dejar rota una transaccion exterior por una tabla ausente.
Esto no oculta fallos de otras consultas, ni mantiene reservas si falla todo
PostgreSQL. La auditoria explicita informa errores en lugar de certificarlos:

```bash
.venv/Scripts/python.exe manage.py auditar_presentacion_institucional
```

El comando solo imprime conteos y estado; no cambia datos ni muestra nombres,
correos, credenciales o responsables. La inmutabilidad es de aplicacion;
SQL privilegiado puede eludirla. No sustituye proteccion/custodia de la base.

La migracion configuracion_institucional.0001_initial agrega dos tablas. En
copia restaurada y temporal se probo aplicar -> revertir -> aplicar con tablas
nuevas vacias: las 136 tablas previas mantuvieron datos, columnas, indices y
claves identicos. La copia fue retirada. Evidencia agregada en
`tmp/evidencia-migracion-presentacion.json`, excluida de Git.

No revertir la migracion despues de crear revisiones sin preservar/conciliar
su historia. Para volver a codigo anterior compatible, las tablas nuevas
pueden conservarse; cambiar de rama no restaura la base. No ejecutar limpieza
de ContentTypes/permisos como parte automatica de esta reversa. Los adjuntos
y documentos archivados, perfiles y cotizaciones anteriores no se reescriben.
M01 institucional sigue abierto antes de traslados de datos.

## Validacion final y siguiente bloque

Suite completa: 950 pruebas, OK. Una omitida; 925.918 segundos.
16 pruebas nuevas y 40 de integracion final correctas. Chrome: 210
combinaciones ES/EN, cuatro estados/siete anchos, login/admin/reserva/guias,
sin errores ni recortes de campos/controles medidos. Capturas 360 revisadas.
Migracion aplicada localmente con respaldo protegido; datos/esquema anteriores
identicos y metadata aditiva esperada. No hay revision/publicacion real ni
concesion explicita de permisos. Ver CODEX_CONTEXT.md 145 y TRASPASO-CODEX.md.

Continuacion 146: [catalogo academico administrable](catalogo-academico-administrable.md).
M02.1 sigue abierto: persistencia de niveles/calendario, paleta configurable
y consumidores editoriales restantes. M09 dara administracion
propia a Inicio, Quienes somos, Servicios, Normativa y Noticias. No se hizo
una sustitucion global de nombres UPEC en documentos historicos o autoria.
Despues: manifiestos M02.2, categorias M02.3 y contratos M02.4.

Referencias: [vistas administrativas](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_urls)
y [transacciones/savepoints](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).

## Continuacion 149

La presentacion incorpora colores versionados: [paleta institucional administrable](paleta-institucional-administrable.md). Niveles y calendario ya tienen persistencia propia (147/148); siguen consumidores editoriales de M02.1 y administracion editorial M09.

## Continuacion 150

La presentacion permite subir logos con variantes para fondos y celulares, preservando historial y respaldos: [logos institucionales administrables](logos-institucionales-administrables.md). M02.1 y M09 siguen con los pendientes editoriales documentados.
