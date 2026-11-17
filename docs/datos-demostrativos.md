# Datos demostrativos

`cargar_pruebas_fablab` y `cargar_escenarios_evaluacion_fablab` son herramientas
de evaluación. Crean usuarios, catálogos, recursos, reservas, participantes,
inventario, mantenimiento y finanzas ficticias. No son migraciones, datos base
institucionales ni mecanismos de recuperación.

Los comandos fallan cerrados. Para ejecutarlos se requieren simultáneamente:

1. un entorno local o temporal con `SLCID_ALLOW_DEMO_DATA_COMMANDS=True`;
2. `--unidad <slug>` para declarar el alcance;
3. `--confirmar-datos-demo` para reconocer que la carga es ficticia.

Antes de guardar puede comprobarse el recorrido completo con rollback:

```powershell
$env:SLCID_ALLOW_DEMO_DATA_COMMANDS = 'True'
.venv\Scripts\python.exe manage.py cargar_pruebas_fablab `
  --unidad laboratorio-manufactura-digital-prototipado-prueba `
  --confirmar-datos-demo --simular
.venv\Scripts\python.exe manage.py cargar_escenarios_evaluacion_fablab `
  --unidad laboratorio-manufactura-digital-prototipado-prueba `
  --confirmar-datos-demo --simular
```

Quite `--simular` únicamente después de revisar el resultado. Cada ejecución
bloquea la Unidad y usa una transacción; un fallo revierte el lote. Los comandos
no envían correo, pero sí usan códigos y cuentas demostrativas compartidas, por
lo que deben ejecutarse de forma secuencial sobre una base desechable.

`config.settings_production` establece `ALLOW_DEMO_DATA_COMMANDS=False` de forma
incondicional. Definir la variable de entorno no habilita estas cargas cuando el
despliegue usa la configuración de producción.

`completar_inventario_de_referencia` completa metadatos deducibles sin generar
existencias. Su opción `--demostrativo` exige las mismas tres condiciones
anteriores y admite `--simular`. Solo genera cantidades en artículos sin saldo,
lotes ni movimientos; no debe utilizarse para conciliar un inventario real.

```powershell
.venv\Scripts\python.exe manage.py completar_inventario_de_referencia `
  --unidad laboratorio-manufactura-digital-prototipado-prueba `
  --demostrativo --confirmar-datos-demo --simular
```

## Cuentas de prueba del panel

`crear_usuarios_prueba_gestion` crea cuentas locales para recorrer los perfiles
del panel de laboratorio —gestor, laboratorista, docente, estudiante— sin tocar
personas reales. Pide `--password` de forma explícita, así que la contraseña no
queda escrita en ningún archivo:

```powershell
.venv\Scripts\python.exe manage.py crear_usuarios_prueba_gestion --password '<una contraseña larga>'
```

Son cuentas de una base desechable. No deben crearse en la base activa.

## Limpieza de figuras huérfanas

El editor visual de guías sube cada figura antes de guardar la solicitud. Si
quien la redacta abandona el asistente, el archivo queda sin guía a la que
pertenecer. `limpiar_figuras_guia_huerfanas` las retira y conserva las recientes
por si el borrador sigue abierto:

```powershell
.venv\Scripts\python.exe manage.py limpiar_figuras_guia_huerfanas
```

Es mantenimiento periódico, no una carga de datos: puede ejecutarse en la base
activa.


## Limpiar los movimientos antes de registrar datos reales

`limpiar_movimientos` deja la base sin lo que se registró para probar y conserva lo que describe a la
institución.

- **Borra** (tablas completas): reservas, visitas e ingresos; prácticas planificadas y ejecutadas con sus
  evidencias; documentos y anexos del expediente con sus archivos, constancias y controles; evidencias de
  gestión; mantenimientos con su plan, incidencias, préstamos, alertas y desechos; solicitudes de fabricación;
  planes, órdenes, lotes y calidad de las plantas piloto; movimientos financieros; y la auditoría de todo ello.
- **Conserva:** unidades, espacios, equipos, existencias y kárdex de inventario (salvo con `--existencias`),
  software, asignaturas, guías,
  catálogo de actividades, cursos, portal, biblioteca de recursos de cada unidad y cuentas reales. La base de
  Centros no se toca.
- **Cuentas de demostración** (`demo.`, `.demo.`, `estudiante.prueba`, `sistema.demostrativo`): se borran; si una
  está ligada a un dato que se conserva, se desactiva.

Sin `--aplicar` solo ensaya: hace todo dentro de una transacción, informa cuántas filas borraría y la revierte.

```powershell
.venv\Scripts\python.exe manage.py limpiar_movimientos
.venv\Scripts\python.exe manage.py limpiar_movimientos --aplicar --confirmar BORRAR-MOVIMIENTOS --base <nombre de la base> --retirar-archivos-a <carpeta>
```

Garantías: nada fuera de la lista pierde filas (si ocurriera, se revierte todo); una fila conservada que señalaba
a un movimiento queda sin esa referencia y se informa; los archivos de lo borrado se mueven a la carpeta indicada
en lugar de eliminarse; y las tablas vaciadas vuelven a numerar desde 1. Antes de aplicar hay que respaldar las
dos bases.

Con `--existencias` borra además los lotes y el kárdex de insumos y deja cada insumo con saldo 0. El insumo sigue
en el catálogo con su mínimo, su objetivo y su precio de referencia; la unidad registra después su recepción real.

No corrige lo que es de demostración dentro de los catálogos: equipos marcados `[EVAL]` o
`[Ejemplo de inventario]`. Eso se decide aparte.
