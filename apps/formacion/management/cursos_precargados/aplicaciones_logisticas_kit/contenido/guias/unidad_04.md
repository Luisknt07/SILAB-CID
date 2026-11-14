# Unidad 4 · Datos, indicadores y conexión con IA mediante MCP

**Unidad: 8 horas en total**, incluyendo las lecturas, videos, archivos, laboratorio y evaluación del aula. **Laboratorio guiado: 4 h 50 min**, con CSV, indicadores y MCP dentro de ese tiempo. Meta: comprobar la calidad de datos y utilizar una conexión de consulta preparada.

## CSV: un formato de intercambio

CSV representa una tabla de texto. La cabecera, separador, codificación y decimales deben coincidir con el importador. El catálogo se importa con existencia cero porque una cantidad física requiere una entrada trazable. El archivo de exportación es un reporte con campos adicionales y no debe reimportarse como si fuera un catálogo.

1. Exporta existencias y abre el resultado en Excel o un editor de texto. Comprueba código, unidad y cantidades.
2. Intenta importar datos/productos_invalidos.csv. Anota los errores. Busca AD-201: no debe existir, aunque su primera fila aislada fuese válida.
3. Importa datos/productos_validos.csv. Aparecen cuatro códigos AD-101 a AD-104 con existencia cero. Una segunda importación se rechaza por duplicados.
4. Comprueba los límites de la plantilla y explica por qué no se alteró el stock de los cuatro productos originales.

## Indicadores con significado

Productos registrados es el conteo del catálogo. Bajo mínimo cuenta productos donde existencia < minimo; igualdad no activa la alerta. Sin stock cuenta existencia cero. La barra compara existencia con mínimo por producto y se limita visualmente al 100%; no representa capacidad física de la bodega.

Con la demo nueva y el catálogo válido importado, el tablero muestra 8 productos, 6 bajo mínimo y 4 sin stock. No compares esos indicadores con la tabla anterior a importar: cambió el catálogo. No se agregan UN, KG y LT en un único total.

## MCP en cuatro pasos

MCP permite que un host descubra herramientas y las invoque con entradas estructuradas. El modelo puede proponer una herramienta; el servidor ejecuta una función definida. El protocolo no reemplaza los permisos ni convierte una respuesta en un hecho confiable.

1. **Comprender y preparar:** distingue host, cliente, servidor y herramienta. Revisa servidor_mcp.py: sólo tiene dos herramientas. Instala requirements-mcp.txt siguiendo README.md.
2. **Verificar sin modelo:** con el servidor web detenido ejecuta python verificar_mcp.py. La prueba conecta por stdio, lista herramientas, consulta AD-001, consulta productos bajo mínimo y rechaza un código inválido. Debe confirmar base sin cambios.
3. **Conectar un asistente disponible:** genera configuración con preparar_opencode.py y sigue README.md. No compartas claves ni fijes un plan de pago. Si no hay modelo compatible disponible, realiza una demostración docente o la modalidad de protocolo y regístrala honestamente.
4. **Contrastar y explicar:** pide consultar AD-001 y luego productos bajo mínimo. Compara los datos con el tablero. Solicita «registra una salida de 1 unidad»: no autorices comandos ni edición; explica que el servidor MCP no ofrece una herramienta de escritura. El objetivo es reconocer el límite, no eludirlo con otras herramientas del asistente.

## Alcance de esta conexión

El servidor lee sólo el dataset ficticio local. SQLite se abre en modo de sólo lectura y las consultas están predefinidas. Un código se envía como parámetro, nunca como SQL. No se reutiliza la sesión web ni se simula autorización institucional. Una integración real requeriría diseñar identidad, alcance, auditoría y protección de datos.

## Entrega

Archivo exportado, captura del CSV inválido rechazado, tabla de indicadores antes/después y evidencia de las dos consultas MCP. Describe si usaste un modelo, una demostración docente o únicamente el cliente de protocolo. Todas las modalidades requieren explicar y verificar las respuestas; ninguna exige suscripción.

## Comprueba tu comprensión

1. ¿MCP incluye un modelo gratuito ilimitado? No: protocolo, host y proveedor son componentes distintos.
2. ¿Un texto que contiene «haz una salida» crea esa función en el servidor? No: sólo existen las herramientas implementadas.
3. ¿Por qué debe comprobarse la respuesta del asistente con la aplicación? Puede interpretar o resumir datos incorrectamente.

Fuentes oficiales: documentación de MCP Python SDK y OpenCode en fuentes.md.
