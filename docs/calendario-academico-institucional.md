# Politica del calendario academico institucional

M02.1, cuarto bloque compatible. El nucleo define ciclos, ambitos y limites
sin importar Django ni verticales. Un adaptador compartido conecta el admin,
los modelos de periodos, la vigencia del perfil, la asociacion de reservas,
las propuestas de entrega y los calendarios del asistente de unidades.

## Configuracion por instalacion

ACADEMIC_CALENDAR_JSON es un objeto JSON del entorno de despliegue. El perfil
upec conserva ciclos A/B ordinarios, E extraordinario, I interperiodo, seis
ambitos y los valores anteriores: carreras_centros, dieciseis semanas y rango
uno a veinticuatro. Su seleccion automatica contempla carreras_centros e
institucional. El perfil custom utiliza un calendario neutro de ambito
institucional; no hereda CIDEN, carreras_centros ni otros ambitos UPEC.

Ejemplo para un instituto con tres periodos ordinarios:

```json
{
  "ciclos": [
    ["A", "Primer trimestre", "ordinario"],
    ["B", "Segundo trimestre", "ordinario"],
    ["C", "Tercer trimestre", "ordinario"],
    ["I", "Operación entre períodos", "interperiodo"]
  ],
  "ambitos": [["formacion", "Formación técnica"]],
  "ambitos_operacion": ["formacion"],
  "ambito_predeterminado": "formacion",
  "semanas_minimas": 1,
  "semanas_maximas": 24,
  "semanas_predeterminadas": 12
}
```

| Campo | Contrato |
| --- | --- |
| ciclos | Codigo de un caracter A-Z o 0-9, etiqueta y tipo semantico estable |
| ciclos_historicos | Misma estructura para conservar codigos retirados |
| ambitos | Codigo de hasta 30 caracteres y etiqueta; admite dependencias academicas propias |
| ambitos_historicos | Ambitos retirados conservados para leer y administrar historial |
| ambitos_operacion | Subconjunto activo considerado para asociacion automatica del perfil y de reservas |
| ambito_predeterminado | Ambito activo utilizado al crear un periodo |
| semanas_minimas / maximas / predeterminadas | Enteros, sin booleanos; minimo <= predeterminadas <= maximo, dentro de 1..24 |

Los tipos ordinario, extraordinario e interperiodo conservan su significado:
las funciones de horarios y avance dependen de esa semantica. Un tipo nuevo
requiere implementar y validar su comportamiento, no solamente otra etiqueta.
El ciclo C puede declararse ordinario; ya no se limita esa categoria a A/B.
El codigo estable del periodo sigue teniendo hasta veinte caracteres y debe
comenzar por su año de referencia al validarlo.

El JSON admite hasta 100.000 caracteres. Se rechazan claves desconocidas o
duplicadas, HTML, ciclos repetidos/solapados, ambitos inexistentes y rangos
incompatibles. Los codigos de ambito usan letra minuscula inicial seguida de
letras minusculas, numeros o guiones bajos. manage.py check diagnostica
slcid.E004 y bloquea el arranque normal con politica invalida. No eludir checks.
Las opciones se evalúan al consultar, sin consultas de base en el arranque.

## Periodos, seleccion y semanas

Crear y editar periodos/calendarios sigue siendo una funcion del administrador
existente. Sus opciones y valores iniciales vienen de la politica institucional;
no se generan fechas oficiales desde el nombre de un trimestre. El responsable
publica la version vigente y configura sus fechas reales.

Las consultas para_fecha eligen por fecha de inicio de la version vigente,
con desempate estable por ID, en lugar del orden alfabetico del ciclo.
Los filtros operativos compartidos sustituyen los pares de ambitos UPEC
repetidos en perfil, reservas y visualizador. Si ambitos_operacion queda vacio,
no hay asociacion automatica. Esto no deshabilita modulos, no bloquea reservas
ni elimina periodos; una actividad con periodo explicitamente relacionado
conserva esa relacion y la validacion de fechas existente.

No se introduce prohibicion nueva de calendarios solapados: distintos ambitos
pueden coincidir. La seleccion automatica utiliza el calendario mas reciente
entre los ambitos admitidos. Si una instalacion necesita prioridad por programa,
unidad o ambito, relacionarla explicitamente antes de depender de automatismos;
no se infiere esa pertenencia desde una etiqueta o facultad.

La accion administrativa de generar semanas valida primero periodo y version.
Una configuracion invalida se informa y se omite sin generar nuevas semanas.
Se conserva get_or_create: repetir la accion no duplica ni reemplaza semanas,
suspensiones o restricciones de reservas existentes. Las fechas generadas
empiezan en la fecha publicada, duran hasta siete dias y se recortan al cierre
del periodo. El reporte ofrece las semanas del periodo seleccionado o el
maximo institucional cuando no se selecciona uno.

La restriccion fisica de las tablas permanece en 1..24, tanto para periodos
como para numeros de semana. Politicas de menos semanas pueden configurarse
si son compatibles con el historial. Periodos anuales de 52 semanas necesitan
otro bloque de esquema/datos, copia protegida, conciliacion y reversa ensayada;
no se habilitan ampliando este JSON.

## Auditoria y continuidad

Antes de cambiar de perfil, retirar codigos o restringir limites:

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py auditar_catalogo_institucional
.venv/Scripts/python.exe manage.py auditar_calendario_institucional
.venv/Scripts/python.exe manage.py migrate --noinput
```

El auditor del calendario informa solamente conteos: ciclos y ambitos
desconocidos, relaciones ciclo/tipo incompatibles, periodos fuera del rango
institucional y semanas fuera del plan o fechas de su version. Sale con error
ante incompatibilidades y no escribe ni expone usuarios. La base local tenia
un periodo y dieciseis semanas, todos compatibles. El auditor academico
mantiene dieciseis campos compatibles.

Retirar un ciclo/ambito requiere conservar su codigo y semantica en las listas
historicas mientras existan consumidores. El administrador puede seguir
validando periodos existentes con esos codigos; los periodos nuevos necesitan
codigos activos. No se convierten periodos existentes ni se modifica su ambito
al cambiar defaults. Mantener limites que cubran el historial o conciliarlo
antes de desplegar. Las escrituras directas/bulk deben validar estas reglas;
el JSON no agrega una restriccion SQL por institucion.

0200_calendario_academico_configurable altera solo choices/defaults de tres
campos. sqlmigrate confirma tres no-op en UPEC y en los perfiles propios de
prueba. Se ensayaron 0197 -> 0198 -> 0199 -> 0200 -> 0199 -> 0200 en una copia
restaurada del dump protegido M01: hashes de datos de las 135 tablas, columnas,
indices y claves identicos, salvo django_migrations por diseño. La base
temporal se elimino; resumen ignorado en tmp/evidencia-migracion-calendario.json.
0200 se aplico en desarrollo.

La reversa usa datos UPEC compatibles. Una version anterior puede no entender
ciclo C o ambitos propios escritos despues del despliegue: auditar contra su
politica y conciliar cambios posteriores antes de regresar al codigo anterior.
Cambiar de rama no revierte PostgreSQL ni transforma esos codigos.
Conservar rutas Python de los proveedores usados por migraciones.

## Validacion y siguientes bloques

Suite completa: **850 pruebas, OK (1 omitida), 892.496 s**.
Seis casos nuevos, 46 pruebas focalizadas y 14 tras el ultimo ajuste;
cuatro arranques
independientes, migracion/reversa en copia de 135 tablas, ambos
auditores, diez recorridos HTTP, Ruff, check, migraciones sin cambios
inesperados, 61 enlaces locales y diff correctos.

Este bloque no cambia idioma/zona horaria, fechas publicadas, snapshots de
reservas, permisos, tarifas o afiliacion. La configuracion regional se completo en el [bloque siguiente](configuracion-regional-institucional.md);
siguen pendientes pertenencia/roles verificados, catalogos persistentes y
contenido visual/editorial de M02.1. La politica se configura por despliegue;
el admin existente administra los periodos y sus versiones, pero no hay aun
un editor persistente del contrato JSON. No demuestra aislamiento de apps o
instalacion comercial minima: esas puertas siguen en M02.2-M02.4 y M11.

Referencias: [niveles y avance](niveles-y-avance-institucional.md),
[ruta modular](ruta-ejecucion-arquitectura-modular.md) y
[seguridad y continuidad](seguridad-continuidad.md). M01 institucional sigue
abierto; no mover datos hasta cerrar su puerta de recuperacion.

## Continuacion actual: editor persistente (148)

La politica ahora tiene [editor propio, borradores e historial](calendario-academico-administrable.md)
en configuracion_institucional. El despliegue conserva contrato de base y proveedor
opcional; CLI estricto comprueba publicado por alias. Periodos/versiones/semanas
siguen en admin operativo, sin duplicar fechas ni transformar historial. La
evidencia anterior es historica; consultar CODEX_CONTEXT 148 para cierre vigente.
