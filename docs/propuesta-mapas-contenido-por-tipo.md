# Propuesta: mapa de contenidos nativo por tipo de unidad

Estado: **propuesta para revisión** (27 de septiembre de 2026). No está implementada.

## Punto de partida

- **Plantas piloto** ya tienen un mapa fijo de 33 secciones numeradas
  (`webcitt/domains/unidades/secciones_plantas.py`). Casi todas se llenan solas con
  los datos de la planta: familias, productos, recetas, planes de calidad, equipos y
  guías. Las carpetas manuales («Carpeta recursos») se anclan a una sección y se
  muestran debajo de lo propio. Desde la Fase 1, la ficha del admin enlaza a cada
  dato y calidad ocupa 5.1 a 5.5.
- **Laboratorios, observatorios y centros experimentales** dependen de carpetas
  manuales por módulo. Tienen datos propios que la ficha pública podría mostrar solos,
  pero hoy no los usa o los usa sin orden: equipos, software, espacios, guías,
  asignaturas, reglamento, requisitos, servicios, adjuntos gobernados y artefactos.

## Principios

1. **Un mapa por tipo**, con secciones numeradas por pestaña (la clave del módulo
   no cambia). Cada sección declara qué dato propio la alimenta.
2. **Lo propio primero y automático.** Una sección con datos se llena sola; sin datos
   muestra «pendiente de publicación» y nunca inventa contenido.
3. **Las carpetas manuales se anclan a una sección** (el mismo campo que hoy usa
   `seccion_planta`, generalizado como `seccion`). Aparecen debajo de lo propio y
   una sola vez.
4. **La ficha del admin enlaza** a cada dato de la sección con su cantidad («Ver y
   editar», «Nuevo»), como en plantas.
5. **Un solo mecanismo** para todos los tipos: el mapa es un dato por tipo, no
   plantillas distintas.

## Mapas propuestos

### Laboratorios

| Pestaña (módulo) | Sección | Dato propio que la alimenta |
|---|---|---|
| Información general | 1.1 Presentación | Video y descripción de la unidad |
| | 1.2 La unidad | Identidad, responsables públicos |
| | 1.3 Espacios | Plano, recorrido 360 y espacios reservables |
| | 1.4 Normativa | Reglamento de uso y requisitos de acceso |
| Recursos y prácticas | 2.1 Guías de práctica | Guías publicadas, por asignatura |
| | 2.2 Asignaturas y temas | Asignaturas y temas vinculados |
| | 2.3 Simuladores y recursos interactivos | Recursos multimedia y microproyectos |
| | 2.4 Documentación técnica | Adjuntos de tipo manual, norma o ficha técnica |
| Tecnología y software | 3.1 Equipos | Equipos de la unidad con su ficha |
| | 3.2 Software | Software disponible y licencias |
| | 3.3 Sitios y herramientas externas | Recursos con enlace (incluye navegador remoto) |
| Gestión y reserva | 4.1 Reservar / 4.2 Agenda / 4.3 Mis reservas y guías | Sistema de reservas (como hoy) |
| Proyectos | 5.1 Proyectos y artefactos | Artefactos externos y sus resultados |
| | 5.2 Publicaciones | Adjuntos de tipo publicación |
| Formación y comunidad | 6.1 Formación | Carpetas manuales (sin dato propio aún) |
| | 6.2 Visitas | Oferta de visitas |

### Observatorios

| Pestaña | Sección | Dato propio |
|---|---|---|
| Información general | 1.1–1.4 | Como laboratorios |
| Datos, mapas e indicadores | 2.1 Conjuntos de datos | Adjuntos de tipo dataset |
| | 2.2 Mapas e indicadores | Recursos multimedia, sitios externos y microproyectos |
| Monitoreo y alertas | 3.1 Estaciones y equipos | Equipos de la unidad |
| | 3.2 Alertas | Carpetas manuales (sin dato propio aún) |
| Reportes y publicaciones | 4.1 Reportes | Adjuntos de tipo informe (no los del expediente) |
| | 4.2 Publicaciones | Adjuntos de tipo publicación |
| Investigación y vinculación | 5.1 Proyectos y artefactos | Artefactos externos |
| Acceso y servicios | 6.x | Reservas, servicios, requisitos y reglamento |

### Centros experimentales

| Pestaña | Sección | Dato propio |
|---|---|---|
| Información general | 1.1–1.4 | Como laboratorios |
| Áreas y sistemas productivos | 2.1 Áreas | Espacios reservables y sus equipos |
| | 2.2 Sistemas productivos | Familias y recetas, si la unidad registra producción |
| Producción y ensayos | 3.1 Producción | Productos, órdenes y lotes (como plantas) |
| | 3.2 Ensayos y prácticas | Guías publicadas y ejecuciones con evidencias |
| Infraestructura y equipos | 4.1 Equipos / 4.2 Mantenimiento visible | Equipos de la unidad |
| Investigación y vinculación | 5.1 Proyectos y artefactos | Artefactos externos |
| Visitas y servicios | 6.x | Visitas, reservas, servicios y reglamento |

## Plan de implementación sugerido

1. **Generalizar el mecanismo:** `secciones_plantas.py` pasa a ser un mapa por tipo y
   `CarpetaRecurso.seccion_planta` se vuelve `seccion`, válido para todos los tipos.
   Con una migración que conserve las plantas tal cual.
2. **Constructores por dato:** una función por fuente (equipos, software, guías,
   adjuntos por tipo, artefactos, espacios) que devuelva los botones de la sección.
   Se reutilizan entre tipos.
3. **Ficha del admin:** el bloque «Contenido propio» se genera del mapa del tipo.
4. **Migración de las carpetas manuales actuales:** asignar cada carpeta existente a
   la sección más cercana según su módulo, sin mover archivos. Se revisaría la
   asignación unidad por unidad antes de aplicarla.
5. **Por tipo, en este orden:** laboratorios (más unidades), centros experimentales
   (comparten producción con plantas) y observatorios.

## Decisiones pendientes

- ¿Los nombres y el orden de las secciones propuestas son los que cada tipo necesita?
- ¿«Formación y comunidad» y «Monitoreo y alertas» necesitan un dato propio nuevo
  (por ejemplo, cursos o alertas) o bastan las carpetas manuales?
- ¿Se permite que una unidad oculte secciones vacías, o el mapa se muestra completo
  con «pendiente» como en plantas?
