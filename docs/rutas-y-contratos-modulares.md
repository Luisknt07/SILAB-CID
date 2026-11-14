# Primera separacion ejecutable: rutas y contratos

> Este documento conserva la fotografia del primer bloque de rutas. Desde los
> bloques 145 y 156, Configuracion institucional y Portal son apps Django
> instaladas con persistencia propia. El bloque 158 incorpora
> [manifiestos y registro de dependencias](manifiestos-y-registro-modular.md),
> sin extraer aun la operacion heredada de las verticales.

## Estado del bloque

Las entradas publicas ya pertenecen a seis contextos de presentacion. Los
paquetes de `apps/` todavia no registran modelos nuevos en `INSTALLED_APPS`.
`webcitt` conserva sus tablas, migraciones, permisos y administracion; no hay
conversion de datos en este bloque.

```text
apps/
|-- portal/presentation/                  # Las cinco paginas editoriales
|-- centros_id/presentation/              # Portada propia, sin importar el portal
|-- laboratorios/presentation/            # Catalogo y detalle de laboratorio
|-- plantas_piloto/presentation/           # Catalogo y detalle de planta
|-- centros_experimentales/presentation/   # Catalogo y detalle de campo
|-- observatorios/presentation/           # Catalogo y detalle de observatorio
|-- directorio_unidades/
|   |-- contracts.py                      # TipoUnidad e IdentidadUnidad v1
|   `-- selectors.py                      # Proyeccion publica del modelo legado
`-- integraciones/
    |-- unidades_heredadas.py              # Puente temporal de presentacion
    `-- inventario.py                     # Metadatos para auditar la migracion

webcitt/
|-- urls.py                               # Composicion de los contextos
`-- routing/heredadas.py                   # Operacion compartida pendiente de extraer
```

## Propietarios de las rutas

| Propietario actual de la entrada | Rutas publicas propias |
| --- | --- |
| `portal` | `/`, `/quienes-somos/`, `/servicios/`, `/normativa/`, `/noticias/` |
| `centros_id` | `/centros-id/` |
| `laboratorios` | `/laboratorios-unidades/`, `/hublab/`, `/laboratorio/<slug>/` |
| `plantas_piloto` | `/plantas-piloto/`, `/planta-piloto/<slug>/` |
| `centros_experimentales` | `/centros-experimentales/`, `/centro-experimental/<slug>/` |
| `observatorios` | `/observatorios/`, `/observatorio/<slug>/` |
| `webcitt.routing.heredadas` | 104 rutas de operacion, acceso, recursos y API |

Se conservan las **119 rutas propias de webcitt**, 118 con nombre y una de
multimedia sin nombre. La enumeracion directa corrige el recuento anterior
de 120 y enumera solamente los endpoints. Las rutas de
`admin`, Grappelli y allauth pertenecen a la configuracion del proyecto y a sus
paquetes, respectivamente.

Los nombres de `reverse`, convertidores, argumentos y callbacks operativos
permanecen compatibles. El prefijo historico `/laboratorio/<slug>/` sigue
aceptando los enlaces de plantas ya publicados. No representa una nueva
dependencia de Plantas piloto hacia la app Laboratorios.

El catalogo y detalle comunes solo se importan cuando se atiende una peticion,
mediante `integraciones/unidades_heredadas.py`. Se retiraron las fachadas
anticipadas de Unidades y del portal, el archivo `unidades/views.py` y los cinco
wrappers de catalogo que quedaron sin consumidores.

## Contrato del directorio

`TipoUnidad` identifica exactamente los cuatro tipos existentes. Centros I+D
no pertenece a esa enumeracion. `IdentidadUnidad` es una copia inmutable con
ID estable, nombre, slug, tipo y correo de contacto publico; su version es 1.
No transmite modelos ORM, sesiones, reservas, credenciales o datos privados de
responsables. La consulta `obtener_identidad_publica` devuelve `None` si la
unidad no existe, esta inactiva o no coincide con el tipo solicitado.

Por ahora esta proyeccion no sustituye el controlador completo del detalle:
esa pantalla sigue usando las reglas y permisos heredados. La separacion de
identidad no redefine silenciosamente su politica de acceso.

## Matriz reproducible de codigo y datos

El comando siguiente inventaria rutas y sus callbacks, cada modelo declarado,
tablas y tablas M2M, permisos, registro administrativo, plantillas, estaticos,
comandos y scripts operativos:

```powershell
.venv/Scripts/python.exe manage.py inventario_arquitectura
```

La fotografia de este bloque esta en
[inventario-arquitectura.json](inventario-arquitectura.json). No consulta filas
de la base ni adjuntos. El destino de un modelo es una propuesta de propiedad,
no una migracion ejecutada. Los agregados compartidos quedan marcados como
`heredado_compartido_por_descomponer`; no se adjudican artificialmente a una
sola vertical. Plantillas y estaticos conservan propietario `webcitt` hasta
trasladar sus consumidores. Comandos y scripts enumeran los puntos actuales de
ejecucion; todavia no existen colas independientes por vertical.

## Verificacion y limites

Las pruebas congelan el mapa previo, resuelven y reconstruyen cada URL y
verifican el propietario de cada callback. Cada modulo publico se importa en
un interprete limpio, sin `django.setup`, bloqueando `webcitt` y las otras
verticales. Las reglas AST rechazan importaciones internas cruzadas.

Los cuatro casos reales cubren laboratorio, planta, centro experimental y
observatorio: catalogo filtrado, detalle, aliases, identidad publica y
aislamiento por tipo. Un fallo simulado del catalogo operativo comprueba que
Inicio, Quienes somos, Servicios, Normativa, Noticias y Centros I+D siguen
respondiendo.

El URLconf completo aun importa las rutas operativas heredadas. Un error de
arranque en esa operacion puede impedir iniciar el proceso Django; la prueba
de fallo de peticion no demuestra aislamiento de procesos. La separacion de
tablas, permisos, configuracion operativa, admin y despliegue sigue pendiente.

## Siguiente bloque

Seguir [la ruta M00-M13](ruta-ejecucion-arquitectura-modular.md). Antes de la
extraccion funcional se aplican los controles M01-M02 a Observatorios.

Extraer Observatorios: consultas, publicaciones y configuracion propias,
conservar su identidad del directorio y retirar dependencias de reserva fisica.
Antes de mover sus modelos hay que comprobar relaciones, permisos y reversa
sobre una copia de PostgreSQL. Despues siguen Plantas piloto, Centros
experimentales y Laboratorios conforme a la arquitectura vertical aprobada.
