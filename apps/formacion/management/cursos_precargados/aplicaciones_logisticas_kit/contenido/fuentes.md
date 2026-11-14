# Referencias primarias y procedencia del material

Revisión: 8 de octubre de 2026. Estas fuentes respaldan conceptos y APIs; las explicaciones, código del kit, ejercicios, datos y rúbrica son redacción y desarrollo propios. Los enlaces permiten consultar documentación completa; no se redistribuyen manuales, cursos o videos de terceros.

| Tema | Fuente oficial | Uso en el kit |
|---|---|---|
| Entornos virtuales | https://docs.python.org/es/3/library/venv.html | Aislar dependencias y utilizar el intérprete correcto. |
| Decimal | https://docs.python.org/es/3/library/decimal.html | Cantidades explícitas y comprobación de precisión. |
| Tutorial Django 5.2 | https://docs.djangoproject.com/es/5.2/intro/tutorial01/ | Comprender proyecto, rutas y flujo de solicitud. |
| Modelos y migraciones | https://docs.djangoproject.com/es/5.2/intro/tutorial02/ | Relacionar campos, tablas y migraciones. |
| Validación | https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects | full_clean explícito y reglas de datos. |
| Transacciones | https://docs.djangoproject.com/en/5.2/topics/db/transactions/ | Registrar saldo e historial dentro de atomic. |
| Expresiones F | https://docs.djangoproject.com/en/5.2/ref/models/expressions/#f-expressions | Actualización condicionada de cantidades. |
| Permisos | https://docs.djangoproject.com/en/5.2/topics/auth/default/ | Usuarios, grupos y control en vistas/servicios. |
| Pruebas Django | https://docs.djangoproject.com/en/5.2/topics/testing/overview/ | Reproducir comprobaciones del inventario. |
| SDK oficial MCP | https://github.com/modelcontextprotocol/python-sdk | Dependencia opcional y protocolo. |
| SDK MCP 2.3.0 | https://pypi.org/project/mcp/2.3.0/ | Versión concreta verificada del kit. |
| Ejecución MCP | https://py.sdk.modelcontextprotocol.io/run/ | Servidor local stdio con MCPServer. |
| Salida estructurada MCP | https://py.sdk.modelcontextprotocol.io/servers/structured-output/ | Respuestas de herramientas como diccionarios tipados. |
| Cliente MCP | https://py.sdk.modelcontextprotocol.io/client/transports/ | Verificar protocolo sin contratar un modelo. |
| Configuración OpenCode | https://opencode.ai/docs/mcp-servers/ | type local, command, cwd y enabled. |
| Permisos OpenCode | https://opencode.ai/docs/permissions/ | Pedir revisión de ediciones, comandos y herramientas MCP. |
| SQLite URI | https://www.sqlite.org/uri.html | Apertura mode=ro del archivo docente. |

## Criterio de actualización

Las prácticas están verificadas con Python 3.11.9, Django 5.2.17 y SDK MCP 2.3.0. Antes de otra edición, revisar parches de seguridad dentro de Django 5.2 LTS, compatibilidad de MCP y esquema de OpenCode; ejecutar nuevamente pruebas. Cambiar una versión requiere comprobar el kit, no sólo modificar requirements.

OpenCode es un host/asistente; el costo y los límites dependen del modelo utilizado. El kit no incluye claves, una suscripción ni una garantía de modelos gratuitos. El prototipo y el cliente de prueba MCP se ejecutan sin consumir una API de IA.

## Derechos

Django, Python, MCP y OpenCode mantienen sus nombres, marcas y licencias. Los datos de Andina Distribución fueron creados exclusivamente para estas prácticas. LICENSE cubre el material propio del kit; no concede derechos sobre recursos externos enlazados.
