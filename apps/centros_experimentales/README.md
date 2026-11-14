# Centros Experimentales

Esta vertical es propietaria de la futura operacion de campo del sistema. Su
unidad de trabajo sera el ensayo o la campana, no una reserva de laboratorio,
una corrida de planta ni una solicitud de datos de observatorio.

## Estado actual

El catalogo y el detalle publicos conservan las rutas historicas y la
persistencia existente. La capa `presentation` atiende HTTP y delega en
`infrastructure/unidades_heredadas.py`, que es el unico puente temporal con
`apps.integraciones`. Sus modelos son delegados de las tablas heredadas: una
seccion de administracion por cada funcion declarada en `models.FUNCIONES`.

## Ejes productivos y mapa de la ficha

Un centro es una finca que produce y experimenta a la vez. Su trabajo se
organiza en ejes productivos (ganaderia de leche, cultivos andinos, cafe,
frutales...), cada uno con su pagina como el area de un laboratorio: que
produce, como trabaja, su calendario, sus areas, a donde va lo que produce,
para quien sirve, que le falta para producir mas, sus fotos y videos.

- La funcion `agropecuaria` administra los ejes (`webcitt.EjeProductivo`,
  con sus fotos) desde el area de los centros experimentales.
- La ficha publica sigue `MAPA_CENTRO` (seis pestanas numeradas, en
  `webcitt/domains/unidades/secciones_plantas.py`); sus secciones propias
  (como funciona, ejes, calendario, destino y temas) las arma
  `webcitt/domains/unidades/centro_experimental.py`.
- `manage.py cargar_ejes_centros [--reescribir] [--sin-fotos]` carga los ejes
  de San Francisco y Alonso Tadeo con cifras con fuente, fotos con credito y
  videos verificados; no pisa lo que el centro edita.
- La ficha nombra roles (administracion, familias cuidadoras), nunca personas.
- Gestion productiva: cada eje planifica ciclos (`webcitt.CicloProductivo`, con
  meta y referencia) y anota cada dia cosechas, ordenos, posturas, labores,
  entregas y novedades (`webcitt.RegistroProduccion`). La seccion 3.1 compara
  lo producido con la meta; el publico ve los totales y quien tiene el modulo
  de produccion registra desde la pagina y descarga el CSV.
- Simuladores (2.3): leche, cosecha, postura y cafe, con rendimientos publicados
  como valor de partida (`webcitt/domains/unidades/centro_simuladores.py`).
- Cursos (5.2): uno armado por centro en el aula (`cargar_curso_precargado
  ordeno-calidad-leche` y `cafe-cereza-taza`, sin publicar hasta que el centro los
  revise) y la lista de cursos recomendados por eje.
- Reservas (6.1): que se reserva en cada eje (practicas, ensayos, recorridos,
  cursos), los pasos y los cuidados. `manage.py configurar_reservas_centros` abre
  los recorridos por las areas visitables y registra en el catalogo una practica
  y un ensayo por eje; no crea requisitos de acceso obligatorios (los decide el
  centro).

```text
apps/centros_experimentales/
|-- apps.py
|-- manifiesto.py
|-- infrastructure/
|   `-- unidades_heredadas.py
|-- presentation/
|   |-- urls.py
|   `-- views.py
|-- templates/centros_experimentales/
|   `-- experiencia.html
`-- tests/
    `-- test_estructura.py
```

El paquete está instalado mediante `CentrosExperimentalesConfig`, por lo que
Django descubre la plantilla de la vertical sin agregar rutas globales de
plantillas. El contenido visual conserva el HTML y los recursos compartidos
anteriores; trasladar CSS, JavaScript o imágenes comunes requerirá separar
primero lo exclusivo de lo transversal.

No se crean paquetes vacios. `domain` y `application` se agregaran cuando
existan reglas y casos de uso reales aprobados por la institucion.

## Direccion de dependencias

```text
presentation -> infrastructure -> integraciones -> legado_webcitt
                         |
                         `-> directorio_unidades (identidad_unidad_v1)
```

- La presentacion no importa modelos, vistas o formularios de `webcitt`.
- La infraestructura no contiene decisiones de negocio.
- La vertical no importa Laboratorios, Plantas Piloto, Observatorios ni
  Centros I+D.
- Una integracion futura con otra vertical usara contratos versionados e
  identificadores estables.

## Estructura prevista al iniciar funciones

```text
apps/centros_experimentales/
|-- domain/          # ensayo, campana, ciclo, area, activo, tratamiento
|-- application/     # casos de uso y puertos, sin HTTP ni ORM
|-- infrastructure/  # persistencia y adaptadores externos
|-- presentation/    # URLs, vistas, formularios y administracion
`-- tests/           # reglas, casos de uso, permisos e integracion
```

Antes de crear esos componentes se debe acordar el vocabulario institucional,
los estados, responsables, permisos, retencion y evidencias. Este arbol no
autoriza mover tablas ni reutilizar reglas de otra vertical.

## Limite de aislamiento actual

La separacion presente evita dependencias directas entre verticales y permite
evolucionar el codigo por contexto. El despliegue sigue compartiendo proceso,
base de datos y almacenamiento con el monolito; por ello un aislamiento de
fallos, credenciales o restauracion por vertical corresponde a M10-M11 y no se
afirma como resuelto por esta estructura.

## Inventario heredado y destino previsto

| Pieza actual | Propietario actual | Decisión estructural |
| --- | --- | --- |
| Identidad, slug y tipo de unidad | `webcitt.models.Unidad` | Se consume mediante `identidad_unidad_v1`; no se duplica |
| Perfil operativo | `webcitt.models.PerfilCentroExperimental` | Permanece en el legado hasta una migración M10 con reversa |
| Inline administrativo | `webcitt.admin.unidades` | Permanece junto al modelo heredado; no se copia |
| Catálogo y detalle | Controladores compartidos de `webcitt` | Se accede solo mediante el adaptador de infraestructura |
| Experiencia pública exclusiva | `webcitt/templates` | Trasladada a `templates/centros_experimentales` |
| CSS y JavaScript del catálogo | Recursos compartidos de unidades | Permanecen compartidos hasta separar responsabilidades reales |
| Datos de ensayos y campañas | No existen | Se diseñarán e implementarán en esta vertical después de la especificación |
