# Plantas Piloto

Esta vertical es propietaria de la corrida de proceso y la transformación de
materia prima. Su unidad de trabajo es la orden o corrida productiva, no una
sesión de laboratorio por horas, un ensayo de campo ni una solicitud de datos.

Las cinco plantas —Lácteos, Cárnicos, Hortofrutícola, Almidones y derivados, y
Panificación— están **aceptadas funcionalmente**. Su comportamiento queda
congelado salvo correcciones críticas o contenido institucional nuevo; los
criterios comprobados están en
[`docs/aceptacion-plantas-piloto.md`](../../docs/aceptacion-plantas-piloto.md).
Este paquete describe la frontera estructural y las reglas propias ya
extraídas.

## Estado vigente: operación y café, 14 de octubre de 2026

La operación ya pertenece a `apps/plantas_piloto/operacion` (app Django
`plantas_operacion`): modelos de producción, planificación, calidad y ERP,
administración, controladores, comandos y plantillas. Las tablas históricas
con prefijo `webcitt_` se conservan para preservar datos; ese prefijo no implica
que exista una app de negocio `webcitt`. El adaptador público actual es
`infrastructure/unidades.py`, que consume directorio y gestión compartidos.

La planta de café amplía las cinco plantas aceptadas con contenido técnico
propio: cinco familias, quince procesos/118 etapas, diecisiete productos
(quince públicos y dos residuos internos), diecisiete insumos, cinco fichas
de área y cincuenta y seis fichas individuales de equipamiento de referencia.
Beneficiadero, recepción/trilla/selección, torrefacción/molienda,
empaque/bodega y laboratorio de calidad tienen contenidos propios. Grano y
molido cuentan con rutas de 250, 500 y 1.000 g. Su material vive en
`operacion/management/plantas/cafe*.py`.
Los procesos, productos, insumos, áreas y adjuntos se administran con los
editores existentes, sin una nueva base ni un ERP paralelo.

```powershell
.venv\Scripts\python.exe manage.py completar_planta_cafe --simular
.venv\Scripts\python.exe manage.py completar_planta_cafe --aplicar
```

El comando inicial `preparar_planta_cafe` sigue disponible; el de ampliación
lo usa cuando falta contenido de base. La simulación sólo hace SELECT. La
aplicación es transaccional, conserva ids y relaciones y reconoce los valores
originales antes de actualizar. Las firmas de contenido permiten conservar
las ediciones posteriores; los procesos validados o con decisiones editoriales
manuales quedan intactos. No borra etapas ni crea activos
físicos, existencias, corridas, ventas, tarifas ni certificaciones. Publica
referencias técnicas conservando pendiente su validación operativa. Los
archivos originales son HTML autocontenido sin scripts ni imágenes externas,
más dos CSV; la calculadora nativa usa JavaScript propio sin llamadas de red
ni escrituras. La URL se resuelve con Django y funciona al cambiar de dominio.

La documentación de alcance está en
[`docs/aceptacion-plantas-piloto.md`](../../docs/aceptacion-plantas-piloto.md#equipamiento-individual-y-cadena-completa-de-café--14-de-octubre-de-2026).

## Antecedente de la primera extracción estructural

Los apartados siguientes conservan la decisión inicial anterior al traslado
operativo; las menciones a `webcitt` como propietario describen ese antecedente,
no el estado vigente indicado arriba.

El catálogo y el detalle públicos conservan las rutas históricas y la
persistencia existente. `presentation` atiende HTTP y delega en
`infrastructure/unidades_heredadas.py`, único puente temporal con
`apps.integraciones`. A diferencia de las otras verticales, `domain` ya
contiene reglas reales y probadas: planificación de demanda, completitud
administrable y repositorio trazable.

```text
apps/plantas_piloto/
|-- apps.py
|-- manifiesto.py
|-- domain/
|   |-- planificacion.py
|   |-- completitud.py
|   `-- repositorio.py
|-- infrastructure/
|   `-- unidades_heredadas.py
|-- presentation/
|   |-- urls.py
|   `-- views.py
|-- templates/plantas_piloto/
|   `-- experiencia.html
`-- tests/
    |-- test_estructura.py
    |-- test_planificacion.py
    |-- test_completitud.py
    `-- test_repositorio.py
```

El paquete está instalado mediante `PlantasPilotoConfig`, por lo que Django
descubre la plantilla de la vertical sin agregar rutas globales de plantillas.
El contenido visual conserva el HTML y los recursos compartidos anteriores;
trasladar CSS, JavaScript o imágenes comunes requerirá separar primero lo
exclusivo de lo transversal.

No se crea `application` vacío. Aparecerá cuando un caso de uso real deje de
pertenecer al legado.

## Dirección de dependencias

```text
presentation -> infrastructure -> integraciones -> legado_webcitt
                         |
                         `-> directorio_unidades (identidad_unidad_v1)

domain  # reglas puras, sin HTTP, ORM ni legado
```

- La presentación no importa modelos, vistas o formularios de `webcitt`.
- El dominio no importa Django, el ORM ni el adaptador heredado.
- La infraestructura no contiene decisiones de negocio.
- La vertical no importa Laboratorios, Centros Experimentales, Observatorios
  ni Centros I+D.
- Una integración futura con otra vertical —por ejemplo la transferencia de
  materia prima desde un centro experimental— usará contratos versionados e
  identificadores estables.

## Qué permanece en `webcitt` hasta M10

La persistencia operativa de las plantas no se movió en este bloque
estructural. Sigue siendo propiedad del legado, con sus tablas, migraciones,
permisos y administración intactos:

| Pieza actual | Propietario actual | Decisión estructural |
| --- | --- | --- |
| Identidad, slug y tipo de unidad | `webcitt.models.Unidad` | Se consume mediante `identidad_unidad_v1`; no se duplica |
| Perfil operativo | `webcitt.models.PerfilPlantaPiloto` | Permanece en el legado hasta una migración M10 con reversa |
| Familias, productos, procesos y recetas | `webcitt.models` | Permanecen en el legado; las reglas puras ya viven en `domain` |
| Órdenes, corridas, lotes y trazabilidad | `webcitt.models` y `webcitt.domains` | Permanecen en el legado hasta M10 |
| Calidad, PCC y no conformidades | `webcitt.models` y `webcitt.domains` | Permanecen en el legado hasta M10 |
| Inventario, almacén y movimientos | `webcitt.models` | Permanecen en el legado hasta M10 |
| Plan Maestro y persistencia de planificación | `webcitt.models` | Permanece en el legado; `domain/planificacion.py` no duplica sus datos |
| Persistencia de completitud y repositorio | `webcitt.models` | Permanece en el legado; `domain/completitud.py` y `domain/repositorio.py` deciden sin consultarla |
| Inline y administración de unidad | `webcitt.admin.unidades` | Permanece junto al modelo heredado; no se copia |
| Catálogo y detalle | Controladores compartidos de `webcitt` | Se accede solo mediante el adaptador de infraestructura |
| Experiencia pública exclusiva | `webcitt/templates` | Trasladada a `templates/plantas_piloto` |
| CSS y JavaScript del catálogo | Recursos compartidos de unidades | Permanecen compartidos hasta separar responsabilidades reales |

## Estructura prevista al trasladar la operación

```text
apps/plantas_piloto/
|-- domain/          # procesos, recetas, lotes, calidad y planificación
|-- application/     # casos de uso, comandos y consultas
|-- infrastructure/  # persistencia, repositorios y tareas
|-- presentation/    # URLs, vistas, formularios y administración
`-- tests/           # reglas, casos de uso, permisos e integración
```

Este árbol no autoriza mover tablas. El traslado de modelos, `ContentTypes` y
permisos pertenece a M10 y exige una migración con reversa institucional
comprobada.

## Límite de aislamiento actual

La separación presente evita dependencias directas entre verticales y permite
evolucionar el código por contexto. El despliegue sigue compartiendo proceso,
base de datos y almacenamiento con el monolito; un aislamiento de fallos,
credenciales o restauración por vertical corresponde a M10-M11 y no se afirma
como resuelto por esta estructura.
