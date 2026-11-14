# Niveles y avance por periodo institucional

M02.1, tercer bloque compatible. Los niveles dejan de depender de una constante
en UserProfile. El nucleo define datos y rutas inmutables; Django adapta sus
opciones para el registro, el perfil, las reservas, los participantes, las
vinculaciones historicas y el administrador. No consulta la base durante el
arranque ni importa verticales desde el contrato puro.

## Configuracion

El perfil upec conserva los veinte codigos y etiquetas anteriores. Sus diez
semestres son los niveles admitidos para estudiantes y forman una sola ruta.
Decimo semestre no avanza a tesis automaticamente. Los demas codigos se
conservan para registros heredados y administracion.

INSTITUTION_PROFILE=custom no hereda niveles UPEC. Configurar ACADEMIC_LEVELS_JSON
como un objeto JSON en el entorno del despliegue, junto con la identidad y el
[catalogo academico institucional](catalogo-academico-institucional.md):

```json
{
  "niveles": [
    ["anio_uno", "Primer año"],
    ["anio_dos", "Segundo año"],
    ["trimestre_uno", "Primer trimestre"],
    ["trimestre_dos", "Segundo trimestre"],
    ["tesis", "Desarrollo de tesis"]
  ],
  "estudiantes": ["anio_uno", "anio_dos", "trimestre_uno", "trimestre_dos", "tesis"],
  "secuencias": [
    ["anio_uno", "anio_dos"],
    ["trimestre_uno", "trimestre_dos"]
  ],
  "historicos": [["nivel_retirado", "Nivel del plan anterior"]],
  "etiqueta_faltante": "nivel académico"
}
```

| Clave | Regla |
| --- | --- |
| niveles | Codigos activos y etiquetas de texto, hasta 200 filas |
| historicos | Codigos retirados conservados para lectura y edicion administrativa |
| estudiantes | Subconjunto activo permitido al registrar o actualizar un estudiante |
| secuencias | Rutas explicitas de al menos dos niveles estudiantiles; ningun codigo puede repetirse o pertenecer a dos rutas |
| etiqueta_faltante | Texto que muestra la compuerta del perfil; por defecto nivel académico, semestre en UPEC |

Los codigos tienen hasta 30 caracteres: letra minuscula inicial seguida de
letras minusculas, numeros o guiones bajos. Se rechazan HTML, claves desconocidas,
JSON duplicado, niveles activos/historicos solapados y rutas ambiguas o ciclicas.
El JSON tiene un limite de 100.000 caracteres; nunca se interpreta como codigo
ni como ruta a un archivo. manage.py check informa slcid.E003 ante una estructura
invalida y bloquea el arranque normal. No eludir checks con --skip-checks.

Las opciones se evalúan al construir el formulario o consultar el modelo, no
quedan congeladas al importar UserProfile. El formulario del estudiante ofrece
solo niveles estudiantiles activos; los modelos/admin conservan tambien los
historicos. Una institucion sin docencia puede dejar el objeto vacio: el
personal administrativo puede completar su perfil, pero un estudiante sin
nivel admitido no queda habilitado para operar.

## Propuesta de avance y confirmacion

La seleccion del nivel se valida por pertenencia al catalogo, sin buscar la
palabra semestre dentro del codigo. Los niveles independientes, historicos y
finales conservan su valor; no se infiere otro programa ni un salto a posgrado.

La propuesta utiliza una vinculacion activa del mismo tipo de usuario y ambito
academico, de un periodo publicado o cerrado cuya version vigente termino
antes del inicio del actual. Se ordena por la fecha real de cierre. Se ignoran
vinculaciones futuras, inactivas y borradores. Solo se propone avance entre
periodos ordinarios cuando la ultima vinculacion corresponde a la carrera
actual del perfil.

Si hay avance, el estudiante debe confirmar o corregir la propuesta. Leer el
perfil no confirma el siguiente nivel. Una correccion puede conservar el nivel
anterior; confirmar guarda una vinculacion para el periodo actual sin cambiar
la clasificacion del periodo previo. La seleccion academica no concede grupos,
staff, permisos administrativos ni acredita pertenencia institucional.

## Compatibilidad y despliegue

Antes de retirar codigos, ejecutar:

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py auditar_catalogo_institucional
.venv/Scripts/python.exe manage.py migrate --noinput
```

El auditor revisa ahora dieciseis campos de facultades, carreras y niveles en
la base local: todos compatibles, sin escrituras ni exposicion de personas.
Conservar codigos retirados en historicos hasta conciliar sus consumidores;
retirar un codigo usado hace fallar la auditoria. Configurar una instalacion
propia no transforma automaticamente los datos de otra institucion.

0199_niveles_academicos_configurables cambia solamente el estado de choices.
sqlmigrate confirma cuatro operaciones SQL no-op. Se ensayaron
0197 -> 0198 -> 0199 -> 0198 -> 0199 en una copia restaurada del dump protegido
M01. Los datos de las 135 tablas, columnas, indices y claves conservaron sus
hashes en todas las etapas, exceptuando el registro django_migrations que cambia
por diseño. La copia temporal se elimino. Evidencia resumida local e ignorada:
tmp/evidencia-migracion-niveles.json. 0199 se aplico en desarrollo.

El ensayo utiliza datos UPEC compatibles. Antes de regresar a codigo anterior
despues de crear niveles propios, verificar que esa version entiende los
codigos guardados y conciliar operaciones posteriores. Cambiar de rama no
revierte datos ni convierte codigos. Conservar las rutas Python de proveedores
referenciadas por migraciones al extraer apps posteriormente.

## Validacion del bloque

Suite integral: 844 pruebas OK (una omitida), 746.823 segundos.
Siete casos nuevos, 48 pruebas focalizadas iniciales y diez tras el ajuste final;
cuatro arranques independientes, auditoria de dieciseis campos y ensayo de
reversa en copia correctos. Diez recorridos HTTP, Ruff, check, ausencia de
migraciones inesperadas y 53 enlaces locales validos.

## Limites y siguiente entrega

Continuacion implementada: [politica del calendario institucional](calendario-academico-institucional.md)
separa ciclos, ambitos y limites dentro del esquema compatible; permite tres
ciclos ordinarios y comparte filtros operativos con perfiles y reservas.
La propuesta de niveles y confirmacion descrita aqui se conserva.

Los periodos siguen en webcitt y la restriccion fisica permanece en 1..24 semanas.
Ampliarla requiere un bloque de esquema/recuperacion. Idioma es-ec y zona
America/Guayaquil conservan su configuracion actual; no se reescriben fechas,
horarios de reservas ni calendarios publicados. No se habilita una instalacion
multiinstitucion compartida o aislamiento de fallos.

M02.1 continua con configuracion regional, pertenencia/roles verificados,
catalogos persistentes administrables y contenido visual/editorial.
El alcance inicial configuraba por despliegue. La continuacion 147 incorpora
[editor y publicaciones de niveles](niveles-academicos-administrables.md).
El contrato no asigna rutas por plan de estudios: si un
programa requiere bifurcaciones o planes simultaneos, versionar y relacionar
esas rutas explicitamente antes de habilitar avance automatico.

M01 institucional sigue pendiente de coordinacion de escritores, roles de base,
respaldo externo cifrado/inmutable y restauracion en infraestructura aislada.
Seguir la [ruta modular](ruta-ejecucion-arquitectura-modular.md) y los limites de
[seguridad y continuidad](seguridad-continuidad.md).
