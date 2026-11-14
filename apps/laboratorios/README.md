# Laboratorios

Esta vertical es propietaria de la operación por sesión de laboratorio:
práctica, ensayo o servicio con recursos reservables. Su unidad de trabajo es
la sesión con horario, no una corrida productiva, un ensayo de campo ni una
solicitud de datos.

Laboratorios ya está **aceptado funcionalmente**. Su comportamiento, reglas,
permisos y apariencia quedan congelados salvo correcciones críticas; los
criterios comprobados están en
[`docs/aceptacion-laboratorios.md`](../../docs/aceptacion-laboratorios.md).
Este paquete describe únicamente la frontera estructural.

## Estado actual

El catálogo y el detalle públicos conservan las rutas históricas y la
persistencia existente. La capa `presentation` atiende HTTP y delega en
`infrastructure/unidades_heredadas.py`, único puente temporal con
`apps.integraciones`. La operación, los modelos, las migraciones, la
administración y los permisos permanecen en `webcitt`.

```text
apps/laboratorios/
|-- apps.py
|-- manifiesto.py
|-- infrastructure/
|   `-- unidades_heredadas.py
|-- presentation/
|   |-- urls.py
|   `-- views.py
|-- templates/laboratorios/
|   `-- experiencia.html
`-- tests/
    `-- test_estructura.py
```

El paquete está instalado mediante `LaboratoriosConfig`, por lo que Django
descubre la plantilla de la vertical sin agregar rutas globales de plantillas.
El contenido visual conserva el HTML y los recursos compartidos anteriores;
trasladar CSS, JavaScript o imágenes comunes requerirá separar primero lo
exclusivo de lo transversal.

No se crean paquetes vacíos. `domain` y `application` aparecerán cuando se
traslade una regla real desde el legado, no antes.

## Dirección de dependencias

```text
presentation -> infrastructure -> integraciones -> legado_webcitt
                         |
                         `-> directorio_unidades (identidad_unidad_v1)
```

- La presentación no importa modelos, vistas o formularios de `webcitt`.
- La infraestructura no contiene decisiones de negocio.
- La vertical no importa Plantas Piloto, Centros Experimentales,
  Observatorios ni Centros I+D.
- Una integración futura con otra vertical usará contratos versionados e
  identificadores estables.

## Estructura prevista al trasladar la operación

```text
apps/laboratorios/
|-- domain/          # sesiones, prácticas, muestras, equipos y consumos
|-- application/     # casos de uso, comandos y consultas
|-- infrastructure/  # persistencia, repositorios y tareas
|-- presentation/    # URLs, vistas, formularios y administración
`-- tests/           # reglas, casos de uso, permisos e integración
```

Este árbol no autoriza mover tablas. El traslado de modelos, `ContentTypes` y
permisos pertenece a M10 y exige una migración con reversa institucional
comprobada.

## Inventario heredado y destino previsto

| Pieza actual | Propietario actual | Decisión estructural |
| --- | --- | --- |
| Identidad, slug y tipo de unidad | `webcitt.models.Unidad` | Se consume mediante `identidad_unidad_v1`; no se duplica |
| Perfil operativo | `webcitt.models.PerfilLaboratorio` | Permanece en el legado hasta una migración M10 con reversa |
| Reservas, sesiones y expedientes | `webcitt.models` y `webcitt.domains` | Permanecen en el legado; su comportamiento ya está aceptado |
| Equipos, espacios, software y consumibles | `webcitt.models` | Permanecen en el legado hasta M10 |
| Prácticas, guías y documentos | `webcitt.domains` | Permanecen en el legado hasta M10 |
| Inline y administración de unidad | `webcitt.admin.unidades` | Permanece junto al modelo heredado; no se copia |
| Catálogo y detalle | Controladores compartidos de `webcitt` | Se accede solo mediante el adaptador de infraestructura |
| Experiencia pública exclusiva | `webcitt/templates` | Trasladada a `templates/laboratorios` |
| CSS y JavaScript del catálogo | Recursos compartidos de unidades | Permanecen compartidos hasta separar responsabilidades reales |

## Límite de aislamiento actual

La separación presente evita dependencias directas entre verticales y permite
evolucionar el código por contexto. El despliegue sigue compartiendo proceso,
base de datos y almacenamiento con el monolito; un aislamiento de fallos,
credenciales o restauración por vertical corresponde a M10-M11 y no se afirma
como resuelto por esta estructura.
