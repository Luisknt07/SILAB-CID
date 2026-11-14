# CPC en las necesidades de compra

El nombre del bien identifica lo que la unidad solicita. Las características
técnicas y la justificación tienen sus propios campos. El CPC clasifica la
adquisición nueva; no identifica cada activo existente del inventario.

En el informe interno de necesidades se permite dejar el CPC por confirmar.
Una búsqueda muestra referencias y la unidad debe elegir una explícitamente.
La coincidencia con el archivo no certifica que el código sea el adecuado para
el objeto contractual ni que esté vigente o habilitado en el SOCE. La revisión
administrativa precede a su incorporación al PAC institucional.

El Reglamento publicado por SERCOP, reformado el 30 de julio de 2026, distingue
la identificación de la necesidad de la elaboración y publicación del PAC. Su
artículo 64 exige una descripción concordante con el CPC y la categoría a nivel
nueve para el PAC. Los artículos 65 y 72 regulan el informe de necesidad y la
selección del código relacionado con el objeto. La interfaz no convierte el
informe de una unidad en la publicación institucional del PAC.

Fuente normativa consultada el 20 de octubre de 2026:
[Reglamento de la LOSNCP, SERCOP](https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2026/08/REGLAMENTO-DE-LA-LEY-ORGANICA-SISTEMA-NACIONAL-CONTRATACION-PUBLICA.pdf).

## Copia de referencia incorporada

Se extrajeron únicamente las columnas de código y descripción del archivo
`CPC_SOLICITUD_GEN.xls` aportado por el usuario. Sus indicaciones para solicitar
CPC de giro específico de negocio no se aplican al flujo del sistema.

- 31.932 productos únicos con descripción, sin ejecutar fórmulas ni macros.
- SHA-256 del archivo: `e10439fd8706e394ea36a046c75d988183384e41c8bedf01b7f2646e4fae76ad`.
- Incorporación: 20 de octubre de 2026. El archivo no aporta una fecha verificable de vigencia del catálogo.
- Se conservan los ceros iniciales y los códigos completos. No se recortan ni rellenan.
- El archivo contiene 41 códigos de ocho dígitos. Permanecen disponibles para contraste técnico, pero no se ofrecen como selección de compra.
- Los códigos extendidos de diez a doce dígitos también existen en la consulta pública de productos del SOCE. Se conservan sin convertirlos artificialmente en otro código.

El sistema sirve la copia comprimida del repositorio sin depender del archivo
personal del usuario ni de conexión a Internet en cada búsqueda. La respuesta
incluye procedencia y estado «por validar». Las descripciones y procedencia se
derivan del servidor al guardar el borrador; el navegador no puede atribuirse una
validación institucional. Las copias emitidas conservan su captura original.

La búsqueda oficial está disponible en
[Consulta de productos del SOCE](https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/EP/buscarComProducto.cpe).
Un ejemplo público de códigos extendidos se encuentra en
[Productos de equipos portátiles, SOCE](https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/exe/verComProductos_exe.php?idProducto=45220.00.1&tipo=buscar).

Para renovar la copia, `scripts/importar_catalogo_cpc.py` lee otro archivo con la
misma estructura mediante `xlrd`, conserva su hash y verifica códigos únicos.
`xlrd` sólo se necesita en esa operación de mantenimiento. La aplicación no lo
requiere. La incorporación de un archivo nuevo debe revisar su procedencia y
las diferencias de códigos; no cambia retroactivamente documentos enviados.
