# Fuentes del kit descargable

Carpeta independiente del curso Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial.

- builder.build_zip() devuelve bytes y empaqueta exclusivamente contenido/.
- builder.KIT_FILENAME devuelve kit-aplicaciones-logisticas-ia.zip.
- El ZIP abre con una raíz andina-distribucion/, fuentes editables y manifiesto SHA-256.
- Se excluyen entornos, bases SQLite, cachés, configuraciones personales y secretos.
- No versionar ZIP ni archivos generados. El cargador puede adjuntar los bytes como ContentFile.
- Proyecto probado con Python 3.11.9 y Django 5.2.17. MCP opcional: SDK oficial 2.3.0.
- No modifica modelos, migraciones, usuarios ni base de datos del portal CITT.

Punto de entrada: contenido/README.md. Guía docente: contenido/guia_docente.md.
Pruebas desde contenido/: python manage.py test inventario.
Prueba MCP después de preparar la demo: python verificar_mcp.py.
