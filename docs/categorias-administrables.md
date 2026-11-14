# Categorías administrables y nuevas modalidades (M02.3)

Fecha de auditoría: 19 de septiembre de 2026
Rama: `reestructura-modular`

Este documento cierra el paso que M02.3 exige antes de implementar: *"aprovechar
`Categoria` y `TipoLaboratorio` existentes tras auditar su significado y sus
relaciones; no crear un segundo catálogo que duplique lo mismo"*. Registra lo
que esos dos modelos son hoy, qué les falta para ser administrables y qué
decisiones institucionales bloquean el resto del hito.

## Los tres niveles del producto

| Nivel | Ejemplo | Cómo se amplía | Dónde vive hoy |
| --- | --- | --- | --- |
| Módulo operativo | Laboratorios, Plantas piloto | Paquete con reglas, datos y pruebas propias | `apps/<vertical>/` |
| Categoría o subtipo | Química, microbiología, calibración | Catálogo institucional administrable | `webcitt.models.core.Categoria` y `TipoLaboratorio` |
| Unidad concreta | Laboratorio de Microbiología | Registro en el módulo propietario | `webcitt.models.core.Unidad` |

El nivel intermedio es el alcance de M02.3. Los otros dos ya tienen propietario.

## Qué son hoy los dos catálogos

Ambos modelos tienen exactamente la misma forma:

```python
nombre = models.CharField(max_length=100, unique=True)
descripcion = models.TextField(blank=True, null=True)
```

`Unidad` los consume con dos relaciones múltiples: `categorias` (con un límite
documentado de seis) y `tipos_laboratorio` (sin límite).

### Hallazgo 1: los nombres del código no coinciden con los de la interfaz

| Modelo | Etiqueta pública real | Dónde |
| --- | --- | --- |
| `Categoria` | **"Subárea"** | Filtro del catálogo institucional |
| `TipoLaboratorio` | **"Modo de operación"** | Filtro del catálogo institucional |
| `Unidad.modo_operacion` | **"Modo de operación"** | Filtro del catálogo de plantas piloto |

Dos conceptos distintos se presentan al usuario con la misma etiqueta según el
tipo de unidad que esté consultando. Además, `TipoLaboratorio` se llama así
pero su docstring lo describe como *"Docencia, Investigación, Innovación,
Servicios"*, que son modos de uso, no tipos de laboratorio. Cualquier trabajo de
M02.3 debe fijar primero el vocabulario; renombrar después cuesta migración,
traducciones y pruebas.

### Hallazgo 2: ningún catálogo está acotado a su módulo

Nada impide asociar un `TipoLaboratorio` a un observatorio o a una planta
piloto. El catálogo público lo disimula porque solo muestra los valores en uso
(`TipoLaboratorio.objects.filter(unidades__dependencia=dependencia)`), pero el
administrador permite cualquier combinación. M02.3 pide categorías *"asociadas a
capacidades compatibles"*: esa asociación no existe todavía.

### Hallazgo 3: el catálogo filtra por nombre, no por identificador

```python
unidades.filter(categorias__nombre=categoria)
unidades.filter(tipos_laboratorio__nombre=tipo_laboratorio)
```

Renombrar una categoría rompe los enlaces publicados que la usan como filtro.
Un identificador estable —código o slug— es requisito previo a poder editar
nombres desde el administrador, que es justamente lo que M02.3 pide habilitar.

### Hallazgo 4: no hay ordenar, ocultar ni archivar

M02.3 exige *"crear, editar, ordenar, limitar uso, ocultar y archivar"*. De esas
seis operaciones solo existen crear y editar. Faltan `orden`, un estado de
visibilidad y un estado de archivado.

Hoy la única forma de retirar una categoría es eliminarla, y al hacerlo las
filas de la relación múltiple desaparecen sin aviso: se pierde la clasificación
histórica de cada unidad que la usaba. Es lo contrario de *"referencias
protegidas"* y de *"archivar no borra reservas, corridas o documentos
históricos"*.

### Hallazgo 5, corregido en este bloque: el límite de seis no se aplicaba

`Unidad.clean` comprobaba el máximo así:

```python
if getattr(self, 'pk', None) and self.categorias.count() > 6:
```

Una relación múltiple solo se guarda **después** del modelo. Al crear una unidad
no hay clave primaria y la comprobación se saltaba entera; al editarla, contaba
la selección *anterior*, no la enviada. Se reprodujo el defecto con el propio
formulario del administrador: aceptó y guardó **ocho** categorías.

La regla ahora vive en `Unidad.MAXIMO_CATEGORIAS` y la aplica
`UnidadAdminForm.clean_categorias`, donde sí llega la selección del formulario.
Dos pruebas de regresión cubren el rechazo por exceso y la aceptación del máximo
exacto. No hubo cambio de esquema.

## Lo que falta para cerrar M02.3

| Requisito del hito | Estado |
| --- | --- |
| Crear y editar desde el admin | Existe |
| Configuración validada | Hecho: límite de categorías, códigos de tipología y alcance |
| Identificador estable independiente del nombre | Hecho: `codigo` generado del nombre, único y fijo |
| Orden configurable | Hecho: `orden` |
| Ocultar y archivar conservando historial | Hecho: `activa=False` |
| Referencias protegidas al retirar una categoría | Hecho: no se elimina con unidades; el admin lo refleja |
| Asociación a módulos o capacidades compatibles | Hecho: `tipologias` con códigos del catálogo; vacío es todas |
| Tipos de unidad dejan de ser una lista fija de cuatro | Hecho: [Tipologías administrables](tipologias-administrables.md) |
| Vocabulario institucional acordado | Hecho con las decisiones de abajo; la institución puede renombrar sin romper enlaces |

## Decisiones tomadas (20 de septiembre de 2026)

1. **Vocabulario.** `Categoria` se presenta como **Subárea** en admin y
   catálogo. `TipoLaboratorio` se presenta como **Modo de uso** (docencia,
   investigación, innovación, servicios), lo que elimina la colisión con
   `Unidad.modo_operacion` ("Modo de operación") de plantas piloto. Los nombres
   técnicos de los modelos y sus tablas no cambian.
2. **Alcance.** Cada clasificación declara en qué tipologías se ofrece
   (`tipologias`, lista de códigos del catálogo institucional). Vacío significa
   todas. Se valida en el modelo y en el formulario de unidad; el catálogo
   público solo ofrece las que aplican a la tipología consultada.
3. **Unificación.** Siguen siendo dos catálogos porque significan cosas
   distintas (área de conocimiento y modo de uso); comparten la base abstracta
   `ClasificacionInstitucional` para no duplicar reglas.
4. **Límites.** El máximo de seis subáreas por unidad es una regla del producto
   (`Unidad.MAXIMO_CATEGORIAS`). Se hará configurable cuando una institución lo
   pida, no antes.
5. **Archivado.** Una clasificación archivada sale de los filtros públicos y
   del formulario de unidades nuevas; las unidades que ya la tienen la
   conservan y la muestran. Eliminar solo es posible sin unidades que la usen.

## Implementación

- `ClasificacionInstitucional` (abstracta, `webcitt/models/core.py`): `codigo`
  (slug único, generado del nombre y fijo), `orden`, `activa`, `tipologias`;
  `aplica_a(dependencia)`; `delete` protegido.
- Migración `webcitt.0206_clasificaciones_administrables`: añade los campos,
  asigna códigos a las filas existentes y luego los vuelve únicos. Sin datos
  perdidos ni tablas movidas.
- Admin (`webcitt/admin/__init__.py`): un `ModelAdmin` compartido con
  tipologías como casillas, código de solo lectura tras crear, orden, estado,
  conteo de unidades y eliminación permitida solo sin unidades.
- Formulario de unidad: solo ofrece clasificaciones activas más las ya
  asignadas, y rechaza las que no se ofrezcan para la tipología elegida.
- Catálogo público: filtra por código y acepta el nombre histórico para no
  romper enlaces publicados; ofrece solo clasificaciones activas, aplicables a
  la tipología y en uso en ella.

Verificación: seis pruebas propias (código estable, filtro por código y nombre,
archivado, alcance por tipología, eliminación protegida y admin), ejecutadas
con admin, unidades, tipologías, idiomas, portal, rutas, manifiestos y las
cinco verticales: 131 pruebas correctas.

## Lo que no hará M02.3

No convierte el sistema en una reserva universal. Una modalidad nueva que
necesite otro ciclo de aprobación, otro modelo de datos u otros cálculos exige
una extensión implementada y probada: dar de alta un nombre en el catálogo no
crea esa función. No se aceptará código Python subido por administradores como
mecanismo de extensión.
