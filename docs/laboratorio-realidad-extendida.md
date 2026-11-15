# Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales: puesta a punto

15 de noviembre de 2026. Qué se dejó listo para que el laboratorio atienda, cómo se
opera y qué le corresponde completar a la unidad. Unidad `laboratorio-realidad-extendida`
(código `LAB-FIACA-001`, aula 015).

## Qué quedó listo

| Qué | Estado |
| --- | --- |
| Áreas | 5 activas, con ficha explicativa publicada, ilustración propia y aforo: Desarrollo de experiencias XR (8), Simulación y gemelos digitales (8), Contenidos 3D y captura (6), Metaverso (12) y Sala de experiencias (12) |
| Equipos | 123 activos, todos asociados a su área (46, 19, 24, 11 y 24). Siguen siendo equipamiento de referencia: sin marca ni serie, 1 con existencia verificada |
| Insumos y software | 31 insumos y 32 programas, ya registrados; no se modificaron |
| Servicios | 7 nuevos, sin tarifa: sesión inmersiva guiada, digitalización 3D, prototipo de RV o RA, recorrido 360°, captura de movimiento, prototipo de gemelo digital y pruebas con usuarios |
| Requisitos de acceso | 4: inducción anual y condiciones de salud (obligatorios), higiene del visor y consentimiento (informativos) |
| Guías de práctica | 6 de referencia, publicadas y descargables, una por línea de trabajo |
| Documentos de la sala | 5 en PDF: protocolo de visores, registro de malestar, apertura y cierre, hoja de pruebas con usuarios y cómo reservar |
| Ejemplos de solicitud | 8, uno por propósito del asistente de reservas |
| Visitas | Recorrido por tres áreas: sala de experiencias, desarrollo XR y contenidos 3D |
| Curso | «Realidad extendida: de la idea al prototipo» (`XR-CUR-001`), 24 horas, 9 módulos y 31 lecciones; cargado sin publicar |
| Imágenes | Plano funcional de las áreas, 5 ilustraciones de área, 7 de servicio y portada del curso |

Además se corrigió lo que el sitio mostraba mal: un hito que hablaba de seis áreas,
seis imágenes de referencia repetidas tras integrar áreas y dos zonas con el mismo
nombre en el área de desarrollo.

## Cómo se aplica

```bash
python manage.py preparar_laboratorio_xr            # simula y no guarda nada
python manage.py preparar_laboratorio_xr --aplicar  # guarda solo esta unidad
```

Antes de aplicar en otra base, respaldarla. El comando se puede repetir: crea lo que
falte y no cambia lo que la unidad ya editó. El recorrido de visitas y la publicación
de la inducción se proponen solo la primera vez; una ficha de área que la unidad retire
no se vuelve a publicar. Lo que se borre por error (un servicio, un documento) se
repone al repetirlo. Los datos están en
`apps/laboratorios/operacion/management/laboratorios/realidad_extendida.py`, las
imágenes se dibujan en `esquemas.py` de la misma carpeta y el curso está en
`apps/formacion/management/cursos_precargados/realidad_extendida.py`.

En la base local ya está aplicado. Respaldo previo de las dos bases en
`var/backups/pre-laboratorio-xr-20261115/`.

## Cómo opera el laboratorio

**Reservar.** La persona elige área y equipos, describe la actividad y agrega a los
participantes. Las áreas de desarrollo, simulación y contenidos 3D piden elegir al
menos un equipo o programa; la sala de experiencias se reserva sola.

**Inducción y control de ingreso.** Con la inducción obligatoria, el laboratorio
controla el ingreso:

1. Cualquiera puede reservar sin inducción; el asistente le avisa que la necesita.
2. Al aprobar, el sistema no deja pasar un grupo mayor que el aforo del área.
3. La sesión no inicia hasta registrar el ingreso persona por persona. Quien no tiene
   la inducción vigente queda registrado como «no ingresa» con su motivo.
4. La inducción se obtiene en una sesión con propósito *Capacitación → Inducción*: al
   cerrarla, quienes asistieron quedan habilitados por un año. También se puede
   registrar a mano en *Gestión → Seguridad*.

La inducción se exige a estudiantes, docentes y externos. No se exige al personal del
laboratorio, que la imparte, ni a las visitas, que entran guiadas con su lista de
asistencia. Para dejar de controlar el ingreso basta con marcar la inducción y las
condiciones de salud como no obligatorias en *Gestión → Seguridad*.

**Visitas.** Se solicitan desde el mismo asistente. El grupo no puede superar el aforo
de ninguna de las áreas que recorra: 12 personas en la sala de experiencias, 8 en
desarrollo XR y 6 en contenidos 3D. Un grupo mayor se divide en turnos o quita esa
área del recorrido.

**Servicios.** Se solicitan y aprueban, y quedan con valor cero mientras la unidad no
apruebe tarifas.

## Las imágenes

Son dibujos generados por el sistema, no fotografías. El plano dice de qué áreas se
compone el laboratorio y lo declara: no representa medidas ni ubicación física. Las
ilustraciones de área y de servicio son lineales y sin texto. Cuando la unidad suba
una foto propia en la ficha del área o del servicio, reemplaza a la ilustración. El
comando no vuelve a generar una imagen donde ya hay una.

## Cómo se comprobó

- `tests/integration/test_preparar_laboratorio_xr.py`: simulación sin rastro,
  aplicación completa, repetición sin duplicar ni pisar ediciones, reposición de lo
  borrado, control de acceso y páginas públicas.
- `tests/integration/test_enlaces_equipos_no_publicos.py`: un visitante no recibe
  enlaces a equipos que no puede abrir, y la galería de un área no repite sus imágenes
  de referencia.
- El curso pasa las pruebas comunes de cursos precargados, incluido el recorrido
  completo hasta el certificado.
- Sobre la base real, dentro de una transacción que se deshizo al final: 145
  comprobaciones correctas. Sesión de inducción que habilita a los asistentes,
  práctica con un visor y control en la puerta, bloqueo por aforo, visita guiada,
  solicitud de servicio y los 22 reportes del centro de reportes en HTML, PDF, DOCX,
  XLSX y CSV.
- Recorrido del sitio: 142 páginas y archivos públicos sin error.

Las pruebas en seco consumen números de secuencia: la próxima reserva real no será
consecutiva con la anterior. Es normal.

## Lo que le corresponde a la unidad

1. **Verificar el equipamiento.** De 123 equipos, 1 tiene existencia verificada, 21
   están como no disponibles y ninguno tiene serie. El sistema no inventa marcas,
   series ni existencias: se registran en la ficha de cada equipo al recibirlos.
2. **Facultad.** La ficha dice «Facultad de Comercio integración» y el código es
   `LAB-FIACA-001`; hay que dejar la que corresponda.
3. **Cuentas del personal.** El coordinador PhD. Luis Omar Alpala figura como
   responsable pero no tiene cuenta, así que no recibe ni aprueba solicitudes. Hoy solo
   opera la cuenta `admin.realidad-extendida`.
4. **Curso.** Revisar el contenido, poner fechas a la edición 2027-I y publicarlo.
5. **Tarifas.** Los servicios están en cero; si alguno se va a cobrar, la unidad
   aprueba su tarifa.
6. **Fotografías.** Reemplazar las ilustraciones por fotos reales de las áreas.
7. **Registro de prueba.** `XR-GEN-01-01` «Equipo de Prueba para Debug» sigue en el
   inventario, inactivo y fuera del sitio público; conviene eliminarlo.
8. **Correo.** Las notificaciones de reserva quedan en el sistema; el envío por correo
   espera la cuenta institucional.
