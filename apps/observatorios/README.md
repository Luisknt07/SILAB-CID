# Observatorios

Esta vertical será propietaria del gobierno y publicación de información de
los observatorios. Su unidad de trabajo será una fuente, conjunto versionado,
indicador, publicación o solicitud de análisis, no una reserva física, ensayo
de campo o corrida productiva.

## Estado actual

El catálogo y el detalle conservan las rutas y persistencia existentes.
`presentation` delega en `infrastructure/unidades_heredadas.py`, único puente
temporal con `apps.integraciones`. El paquete está instalado como app Django y
es propietario de su experiencia pública exclusiva.

```text
apps/observatorios/
|-- apps.py
|-- manifiesto.py
|-- infrastructure/
|   `-- unidades_heredadas.py
|-- presentation/
|   |-- urls.py
|   `-- views.py
|-- templates/observatorios/
|   `-- experiencia.html
`-- tests/
    `-- test_estructura.py
```

No se crean paquetes vacíos. `domain` y `application` se agregarán cuando
existan reglas y casos de uso aprobados.

## Dirección de dependencias

```text
presentation -> infrastructure -> integraciones -> legado_webcitt
                         |
                         `-> directorio_unidades (identidad_unidad_v1)
```

- La presentación no importa modelos, vistas o formularios del legado.
- La infraestructura no decide visibilidad, calidad, licencias o permisos.
- La vertical no importa Laboratorios, Plantas Piloto, Centros Experimentales
  ni Centros I+D.
- Las integraciones futuras usarán contratos versionados y proveedores
  opcionales.

## Estructura prevista al iniciar funciones

```text
apps/observatorios/
|-- domain/          # fuentes, conjuntos, versiones, indicadores, metodología
|-- application/     # publicación, actualización y solicitudes de análisis
|-- infrastructure/  # persistencia, almacenamiento e importadores
|-- presentation/    # HTTP, administración, API y exportaciones
`-- tests/           # reglas, permisos, privacidad y reproducibilidad
```

Antes de implementar se deben acordar clasificación de datos, licencias,
retención, periodicidad, metodología, responsables y política de publicación.

## Inventario heredado y destino previsto

| Pieza actual | Propietario actual | Decisión estructural |
| --- | --- | --- |
| Identidad, slug y tipo | `webcitt.models.Unidad` | Consumir mediante `identidad_unidad_v1`; no duplicar |
| Perfil operativo | `webcitt.models.PerfilObservatorio` | Mantener hasta una migración M10 con reversa |
| Inline administrativo | `webcitt.admin.unidades` | Mantener junto al modelo heredado |
| Catálogo y detalle | Controladores compartidos de `webcitt` | Acceder solo mediante infraestructura |
| Experiencia pública exclusiva | `webcitt/templates` | Trasladada a `templates/observatorios` |
| CSS y JavaScript del catálogo | Recursos compartidos de unidades | Mantener hasta separar responsabilidades exclusivas |
| Fuentes, indicadores y publicaciones | No existen | Diseñar después de la especificación institucional |

## Límite de aislamiento actual

La frontera reduce el acoplamiento de código, pero el despliegue todavía
comparte proceso, base y almacenamiento. El aislamiento de credenciales,
procesos y restauración por vertical pertenece a M10-M11.
