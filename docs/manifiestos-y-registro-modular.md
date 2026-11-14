# Manifiestos y registro de modulos

> Actualización del 12 de octubre de 2026: hay 21 manifiestos y aplicaciones
> propietarias reales. `webcitt/` se retiró; su etiqueta permanece únicamente
> en el historial técnico de migraciones. El estado vigente está en
> [arquitectura](arquitectura.md) y el [mapa de aplicaciones](../apps/README.md).
> Los bloques siguientes conservan el recorrido y las decisiones anteriores.

El bloque 161 agrega `auditar_superficies_capacidades`, diagnostico del adaptador
de integraciones que conserva superficies compartidas aunque se filtre un modulo.
No consulta datos ni certifica permisos efectivos. Manifiestos de integraciones
y legado pasan a 1.1.0. [Alcance y matriz](superficies-y-autoridades-capacidades.md).

La continuacion 162 agrega el contrato `senales_heredadas_v1` en integraciones y
el auditor CLI de compatibilidad `auditar_contratos_senales` en legado. Ambos
manifiestos 1.2.0; no registra handlers o mueve modelos. El modo estricto exige
revision de codigo y conexiones. [Guia](contratos-senales-heredadas.md).

## Estado: bloque 158, primer avance de M02.2

Cada paquete tiene `manifiesto.py`. El contrato y el registro viven en
`apps/core/modulos.py`; `config/modulos.py` compone explicitamente los once
manifiestos del despliegue actual. El nucleo de contratos no importa las
verticales, Django, modelos ni controladores. La composicion importa solamente
metadatos, sin ejecutar los puntos de entrada descritos.

Este registro describe codigo. **No habilita modulos, concede permisos ni
cambia INSTALLED_APPS.** El sistema conserva rutas, interfaz, tablas, cuentas,
administracion y funciones existentes. No hay migraciones en este bloque.

## Donde editar

```text
apps/
|-- core/modulos.py                  # Contrato v1, validacion y planes
|-- core/manifiesto.py               # Metadatos del nucleo
|-- configuracion_institucional/manifiesto.py
|-- portal/manifiesto.py
|-- directorio_unidades/manifiesto.py
|-- integraciones/manifiesto.py
|-- centros_id/manifiesto.py
|-- laboratorios/manifiesto.py
|-- plantas_piloto/manifiesto.py
|-- centros_experimentales/manifiesto.py
`-- observatorios/manifiesto.py
config/modulos.py                    # Composicion del despliegue
webcitt/manifiesto.py                # Operacion compartida pendiente de extraer
webcitt/management/commands/auditar_modulos.py
webcitt/tests/test_manifiestos_modulares.py
```

La version `1.0.0` es la del manifiesto, no una nueva version comercial del
sistema. `version_esquema=1` identifica el contrato de sus campos. Los contratos
de datos tienen identificadores propios, por ejemplo `identidad_unidad_v1`.

Un manifiesto declara identificador estable, paquete propietario, etapa,
dependencias obligatorias, integraciones opcionales, app Django, rutas,
administracion, migraciones, comandos, tareas, salud, capacidades y contratos.
Las colecciones son tuplas inmutables; los puntos de entrada deben pertenecer
al paquete propietario. No se admiten expresiones CSS, URLs, codigo ejecutable
o paths suministrados por usuarios en esos campos.

Las etapas describen el alcance actual: `nucleo`, `propio`, `heredado` y
`presentacion`. Una etapa `propio` no afirma que todos sus casos de uso ya se
hayan extraido; Inicio tiene persistencia propia, las otras paginas del portal
aun esperan su bloque editorial. `tareas` y `salud` quedan vacios cuando no hay
puntos independientes implementados. No significan que el modulo este sano.
Las capacidades son nombres descriptivos; no son autorizaciones.

## Dependencias actuales y limites

| Modulo | Dependencias obligatorias declaradas | Alcance actual |
| --- | --- | --- |
| core | Ninguna | Contratos y presentacion transversal; proveedor institucional opcional |
| configuracion_institucional | core | App Django con datos y administracion propios; desde 1.2.0 incluye el catalogo administrable de tipologias de unidad |
| portal | core | App Django con portada de Inicio propia; integraciones publicas opcionales |
| centros_id | core | App Django con modelos, migraciones, administración, investigación y atención propios; directorio de unidades opcional |
| legado_webcitt | core | App Django con operacion compartida, modelos, permisos y admin heredados |
| directorio_unidades | core, legado_webcitt | Proyeccion de identidad publica desde tablas heredadas; desde 1.1.0 sirve la ruta generica `unidades/<tipologia>/` de las tipologias sin app propia |
| integraciones | core, directorio_unidades, legado_webcitt | Adaptadores temporales hacia consultas y detalle heredados |
| laboratorios | core, integraciones | App Django instalada, plantilla pública propia, puente heredado aislado en infraestructura y contrato `identidad_unidad_v1`; operación aceptada aún en el legado |
| plantas_piloto | core, integraciones | App Django instalada, plantilla pública propia, puente heredado aislado en infraestructura, contrato `identidad_unidad_v1` y reglas propias de planificación, completitud y repositorio |
| centros_experimentales | core, integraciones | App Django instalada, plantilla pública propia, puente heredado aislado en infraestructura y contrato `identidad_unidad_v1` |
| observatorios | core, integraciones | App Django instalada, plantilla pública propia, puente heredado aislado en infraestructura y contrato `identidad_unidad_v1` |

Las cuatro verticales de Unidad declaran su app Django y plantillas públicas;
conservan operación, modelos y permisos compartidos en el legado. Centros I+D
ya tiene persistencia y administración propias. Ninguna vertical exige otra
vertical; Centros I+D no exige Laboratorios ni el directorio. Las integraciones
opcionales no se agregan al plan obligatorio: pueden faltar y no generan ciclos obligatorios. Su ausencia
controlada debe probarse en cada consumidor cuando se implemente la seleccion
de capacidades.

Cursos, eventos formativos y certificados se adscriben a la Unidad organizadora
en `webcitt`; su gestión se autoriza con `practicas`. No tienen aún manifiesto
ni capacidad de despliegue independientes. La oferta enlazada desde Centros I+D
no transfiere matrícula, calificaciones ni emisión de certificados al centro.

Estas son dependencias declaradas de paquetes, no un inventario exhaustivo de
cada importacion o funcion. `inventario_arquitectura` conserva ese diagnostico
mas amplio, incluyendo los comandos heredados no enumerados aqui. Las paginas
todavia usan plantillas y recursos alojados en `webcitt`, y el URLconf completo
compone la operacion heredada. Un plan de Portal o Centros I+D sin legado **no
demuestra un despliegue Django minimo sin webcitt**. Tampoco demuestra aislamiento
de procesos, credenciales de base o caidas; esos ensayos pertenecen a M10/M11.

## Auditoria para desarrollo y despliegue

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py auditar_modulos
.venv/Scripts/python.exe manage.py auditar_modulos --modulo laboratorios
.venv/Scripts/python.exe manage.py auditar_modulos --modulo portal --modulo centros_id
```

La auditoria devuelve JSON de metadatos y un plan determinista, con dependencias
antes que sus consumidores. No consulta filas, adjuntos, settings privados o
cuentas. `--modulo` filtra el plan mostrado; no instala, suspende, autoriza o
retira apps. La validacion de apps se aplica al despliegue completo actual.

`slcid.E011` impide pasar el chequeo con registro invalido o una app requerida
ausente. Los registros rechazan identificadores/paquetes duplicados, versiones
invalidas, dependencias obligatorias desconocidas y ciclos. Los nombres de apps
se verifican desde AppConfig resuelto, incluyendo `webcitt`,
`apps.configuracion_institucional` y `apps.portal`; no se comparan con los paths
de clases de INSTALLED_APPS. No se importan rutas o tareas desde el JSON.

Para agregar un modulo: crear su paquete y manifiesto, implementar sus casos
de uso, registrar la composicion en despliegue y verificar dependencias,
contratos, permisos y compatibilidad. Si necesita persistencia, instalar su
AppConfig y ejecutar migraciones mediante el procedimiento de despliegue.
La creacion de categorias institucionales nuevas es otra operacion, M02.3;
no requiere inventar un paquete de codigo por cada categoria.

## Siguiente bloque obligatorio

En el bloque 163, legado e integraciones pasan a manifiesto `1.3.0`.
Legado declara recuperar_codigos_reservas; integraciones conserva el contrato
senales_heredadas_v1 y revisa el servicio nuevo junto con su
receiver. La propiedad sigue en legado_webcitt. No se traslada la tabla ni se
instala una capacidad operativa nueva. [Recuperacion](codigos-reserva-recuperacion.md).

Desde el bloque 159, `portal.portada_inicio` tiene controles de despliegue y
guardas de servidor para escritura, publicacion y archivo administrativo.
Portal manifiesto `1.1.0`; [alcance y pendientes](controles-capacidades.md).
El bloque 160 agrega administracion institucional dinamica y auditada solo para
esa capacidad; Configuracion institucional manifiesto `1.1.0`. No habilita
controles para verticales sin cobertura de sus superficies.

Implementar por separado disponibilidad de despliegue, habilitacion
institucional, derechos/limites comerciales y permisos de usuario/objeto.
El registro no sustituye ninguno de esos controles. El servidor debera
verificarlos en URLs, escrituras, exportaciones, API, comandos y tareas; ocultar
menus no es suficiente. No aplicar restricciones comerciales ficticias.

La suspension debera bloquear nuevas operaciones sin borrar historial,
permisos o adjuntos, manteniendo lectura/exportacion administrativa explicita.
No ofrecer un interruptor en admin hasta que todas las superficies del alcance
elegido tengan esas reglas y sus pruebas. No retirar el legado ni mover tablas
antes de los ensayos M01/M10. M02.1, M02.2, M09 y M11 siguen abiertos.

## Verificacion de este bloque

Trece pruebas nuevas cubren formatos invalidos, inmutabilidad publica,
dependencias, ciclos, planes reducidos, archivos de entrada existentes, carga
en interprete aislado bloqueando Django/ORM/controladores, diagnostico de apps
ausentes y auditoria sin acceso de base. Junto con compatibilidad de rutas:
23 pruebas OK, 3.112 segundos. Ruff y migraciones en seco correctos.
Suite completa: 1084 pruebas, OK. Una omitida; 455.002 segundos.
Registro de cierre: CODEX_CONTEXT, continuacion 158.
No hay cambios visuales, CSS o JS que requieran repetir la matriz responsive.
