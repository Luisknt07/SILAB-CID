# Puesta en marcha del seguimiento de Laboratorios y Centros

15 de noviembre de 2026. Adecuación de SILAB-CID al proyecto de reglamento. Esta entrega implementa un circuito funcional; no constituye aprobación jurídica ni asigna personas o cargos por cuenta de la Universidad.

## Qué se incorpora

- Designaciones funcionales con cuenta, ámbito, acto de asignación, vigencia, dedicación y posibilidad de revocación. Se comprueba la cuenta activa y la vigencia en cada decisión. Ser superadministrador no equivale a ser revisor institucional.
- Mesa de seguimiento en `/seguimiento/`, accesible con una cuenta funcional sin necesidad de convertirla en superusuario. Desde la cabecera se muestra el enlace a quienes tienen designaciones vigentes y al administrador técnico para configurar las designaciones respaldadas.
- Consolidado de cada dependencia de adscripción y de cada Centro, con fechas explícitas, versión, fuentes conservadas y huella. El Decanato o la autoridad documentada valida su ámbito; el responsable del Centro valida el suyo. El seguimiento institucional se registra separadamente, por una persona independiente.
- Una modificación de las fuentes o una versión posterior impide continuar validando el consolidado anterior. Las decisiones previas se conservan como historial. Repetir la preparación sin cambios devuelve la misma versión.
- Evidencias de Centro por código, período y versión, enlazadas a su repositorio y, cuando corresponde, al documento del Centro. No se copian los Centros a la tabla de laboratorios ni se publica automáticamente documentación interna.
- Observaciones y compromisos institucionales con responsable del ámbito, plazo, respuesta, evidencia y verificación independiente. Las correcciones de operación de cada laboratorio mantienen los mecanismos locales existentes; no se concede a un coordinador acceso al expediente completo de otras instalaciones de su Facultad.
- Lectura y revisión documental institucional sin conceder administración cotidiana de reservas, prácticas, recursos, finanzas o personal. La descarga de documentos de laboratorio y documentos internos de Centro se autoriza contra la instantánea correspondiente y comprueba la huella del archivo, sin hacerlos públicos.
- Registro de la identidad patrimonial común: código único, inventario y equipo individual de origen, fuente y responsable. Se impide registrar dos identidades para el mismo equipo de origen o para el mismo código. Las articulaciones ya existentes conservan su inventario y agenda de origen; no se fusionan equipos por nombres parecidos.
- Referencias a proyectos y resultados del sistema oficial de investigación: Centro, registro local, sistema de origen, identificador, enlace y estado según fuente. Solo la función documentada de Investigación e Innovación verifica la correspondencia. La constancia no aprueba un nuevo proyecto, resultado científico o derecho de propiedad intelectual.
- Exportación institucional por período con las últimas versiones, vigencia, fuentes y ámbitos que todavía no tienen consolidado. No suma activos enlazados como si fueran bienes diferentes, ni suma documentos como si fueran resultados científicos aprobados.

## Qué debe completar la Universidad

1. **Designaciones y actos.** Identificar la cuenta del responsable institucional, la autoridad de cada dependencia que validará sus consolidados, el responsable de cada Centro y la función que verificará referencias de Investigación. Confirmar alcance, dedicación y sustituciones. No se crearon designaciones ficticias en los datos operativos.
2. **Adscripciones.** Cotejar las instalaciones, sus actos de creación, su dependencia vigente y su coordinador. El origen histórico del financiamiento o el uso actual para docencia no bastan para trasladar una instalación de autoridad. La revisión anterior encontró adscripciones o receptores sin configurar; esos datos no se inventan para cerrar el diagnóstico.
3. **Centros y personal.** Asignar al responsable real de cada Centro tanto en su ficha como en su designación funcional. Diferenciar propuesta, implementación y operación. Confirmar cobertura y habilitación del personal técnico; el registro del área no acredita su disponibilidad física.
4. **Exigibles y criterios de calidad.** Confirmar el catálogo aprobado de documentos, periodicidad, plazos, criterios y excepciones aplicables. Este circuito conserva evidencias y decisiones: no interpreta automáticamente «revisado» como cumplimiento de todos los requisitos. La política de evaluación existente necesita respaldo institucional y no se sustituye por porcentajes inventados.
5. **Inventario e investigación.** Verificar códigos físicos, fuente patrimonial y vínculos propios/compartidos. Confirmar con Investigación el identificador y estado oficial. Se dispone de enlaces y constancias; la sincronización automática con un Portafolio externo requiere conocer su interfaz, credenciales autorizadas y reglas de intercambio.
6. **Ensayo con personas reales.** Ejecutar el caso XR: un laboratorio académico y un área del Centro, apoyo programado, una evidencia de cada ámbito, validación por su autoridad, observación institucional, corrección, nueva versión y consolidación. Verificar la recepción por quienes efectivamente desempeñarán esas funciones.

## Configuración de roles

En la administración, abrir **Asignaciones funcionales documentadas**. Cada registro requiere cuenta, función, acto y alcance, fecha inicial, fecha final si procede, dedicación y estado activo.

| Función | Referencia del ámbito | Efecto |
|---|---|---|
| Seguimiento institucional de Laboratorios y Centros | Vacía | Consulta común y revisión independiente de documentación y consolidados. |
| Validación del consolidado de dependencia | ID de la dependencia académica | Valida únicamente el consolidado de esa adscripción. Ser receptor permite preparar/consultar, pero no sustituye esta designación para validar. |
| Responsabilidad de Centro | Identificador público del Centro | Valida el consolidado de ese Centro cuando la misma cuenta figura como responsable en su ficha. Los gestores pueden preparar evidencias bajo esa responsabilidad vigente. |
| Verificación de referencias científicas oficiales | Vacía | Comprueba correspondencia de una referencia con la fuente oficial de Investigación; no modifica la decisión científica de origen. |

La ausencia, vencimiento, revocación o inactivación impide la decisión correspondiente. El administrador técnico registra los actos respaldados; no debe usar esa configuración para autoatribuir competencias. Las modificaciones de las designaciones quedan en el historial de administración.

## Uso por período

1. La dependencia o el Centro prepara una versión a partir de las fuentes existentes; el Centro registra previamente sus evidencias del período.
2. La autoridad del ámbito consulta las fuentes y registra su validación. No se exige que apruebe otra vez cada reserva o cada anexo.
3. El responsable institucional consulta archivos, cobertura, observaciones y consistencia. Registra la revisión o devuelve con observaciones. Si participó en la gestión o autoría, interviene otro revisor designado.
4. Las observaciones pueden dar lugar a compromisos con respuesta y evidencia. La verificación de su cumplimiento es independiente de quien respondió.
5. Cuando una corrección modifica las fuentes, se prepara otra versión. El historial no se borra y la nueva versión requiere su propia validación.
6. La exportación común identifica qué consolidados están revisados y vigentes y cuáles faltan o quedaron desactualizados.

## Alcance de despliegue

La preparación y modificación del proyecto se realizan desde este chat en la misma carpeta que se abre en Visual Studio Code. Ese editor es opcional para inspeccionar o continuar el trabajo. Publicar en un servidor requiere aplicar las migraciones y la configuración de ese servidor, recopilar los archivos estáticos cuando corresponda y efectuar el ensayo institucional. La instalación local no implica publicación en `labs.upec.edu.ec`.

Las migraciones nuevas crean estructuras de seguimiento y designaciones. No reclasifican laboratorios, no asignan autoridades, no trasladan inventarios, no alteran presupuestos ni cierran proyectos. Los dos borradores reglamentarios deben concordarse y aprobarse por el procedimiento institucional antes de tratarlos como normativa vigente.

## Referencias de organización

- [Estatuto UPEC, ficha de Resolución 093-CSUP-2026](https://normativa.upec.edu.ec/handle/123456789/481).
- [Estructura Organizacional UPEC, Resolución 047.1-CSUP-2026](https://normativa.upec.edu.ec/handle/123456789/478).
- Proyecto local de Reglamento de Laboratorios y Centros de Investigación y Desarrollo, versión de concordancia con el borrador de Investigación 2026. La figura funcional y su alcance transversal requieren validación jurídica y organizacional expresa.
