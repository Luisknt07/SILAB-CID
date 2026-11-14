# Integración selectiva desde `version2`

La rama `integracion-version2-funciones` parte de `version3` y sirve como zona
aislada para revisar el trabajo paralelo realizado en `version2`. No se hizo un
merge completo ni se aplicaron commits enteros, porque esa rama mezcla funciones
útiles con estructura antigua, configuración Oracle y cambios de identidad UTPL.

## Incorporado y adaptado

- Flujo administrativo de solicitudes de fabricación FabLab.
- Revisión técnica por laboratorista, estados y estimaciones.
- Aprobación y amortización por Decanato con permisos mínimos.
- Carga de comprobante asociada a la solicitud.
- Umbral mínimo y alerta para consumibles.
- Autocompletado de identidad del usuario autenticado al reservar.
- Seguimiento especializado de solicitudes FabLab por unidad.
- Configuración de capacidades e indicadores internos por unidad.
- Gestión de inventario, incidencias, mantenimiento y ciclo de vida de equipos.

Estas funciones se distribuyeron entre `models/`, `admin/`,
`domains/unidades/reservas/` y `domains/unidades/tablero_operativo.py`; no se
recuperó el antiguo `webcitt/admin.py` monolítico. El esquema nuevo está contenido en las
migraciones `0094` a `0100`.

## Reestructuración institucional de la interfaz

El detalle público de una unidad conserva la interfaz de consulta y una sola
entrada a **Reservas**. No expone gestión de unidad, control operativo,
indicadores, inventario administrativo ni una acción independiente para
solicitar servicios.

El mismo asistente de reservas permite elegir entre equipo, espacio o servicio.
El paso de materiales siempre guía al solicitante: debe indicar si no necesita
insumos, si los solicitará del inventario de la unidad, si llevará materiales
propios o si requiere orientación técnica. El catálogo cuantificado muestra
código, clasificación, unidad de medida, existencia —incluido el estado
agotado—, lote, vencimiento, imagen y ficha técnica. Cuando una unidad todavía
no tiene registros publicados, el sistema informa ese estado en lugar de
ocultar la sección. El texto libre queda reservado para requisitos adicionales.

La operación se concentra en Django Admin: **Reportes operativos** resume cada
unidad y enlaza a la administración de reservas, inventario y configuración.
Solo el superusuario o el administrador asignado a la unidad puede consultar
ese reporte.

## Reconstrucción organizada completada

El formulario público de solicitudes FabLab y sus endpoints de seguimiento se
reconstruyeron como un dominio propio de fabricación, enlazado al portal actual y
sin recuperar las vistas extensas, plantillas antiguas ni rutas globales de
`version2`.

Ese dominio de fabricación y su entrada pública `/fabricacion/` se retiraron
el 4 de septiembre de 2026: el encargo de un servicio se pide desde el
asistente de reservas de cada unidad y su orden de servicio vive en
`domains/unidades/reservas/`. Los modelos de máquinas y trabajos de aquella
etapa (`FablabMachine`, `FabricationJob`) se eliminaron el 12 de septiembre de
2026 sin un solo registro operativo.

## Revisado, pero no importado

- Cambios de marca UPEC → UTPL y sus recursos visuales.
- Configuración de Oracle y dominios provisionales de despliegue.
- Volcados JSON de datos del sistema anterior.
- Plantillas y administración monolíticas.
- Rutas históricas que no pertenecen a la arquitectura vigente.

## Seguridad y dependencias

`version2` actualiza Django, django-allauth y otras dependencias vulnerables. Es un
cambio válido, pero independiente de las funciones FabLab. Debe hacerse en una
rama de actualización de dependencias, regenerando el archivo de bloqueo y
probando los flujos Google/Microsoft con la versión nueva de allauth. El adaptador
actual todavía usa el hook anterior `authentication_error`; allauth 65 utiliza
`on_authentication_error`.

## Verificación

Antes de integrar a `version3` se debe ejecutar:

```powershell
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py check
python manage.py test webcitt.tests
```

Las migraciones `0094` a `0100` deben aplicarse en cada entorno al desplegar la
rama. Las pruebas automatizadas usan una base temporal y no modifican los datos de
trabajo.
