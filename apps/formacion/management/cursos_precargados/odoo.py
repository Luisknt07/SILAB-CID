"""Curso precargado: «Odoo Lab: monta, opera y programa el ERP de tu cadena de suministro», del Laboratorio de
Logística, Transporte y Cadena de Suministro (área Tecnologías aplicadas y simulación logística).

Revisión técnica original del 4 de octubre de 2026 con la documentación oficial de Odoo 20.0 (odoo.com/documentation/20.0, salida en
septiembre de 2026), el código de la rama 20.0 en github.com/odoo/odoo, la imagen oficial de Docker Hub, la página de
precios y del programa educativo de odoo.com y el portal de facturación electrónica del SRI; los videos de YouTube se
comprobaron con el oEmbed público. Puntos de Odoo 20 que el curso enseña tal cual: PostgreSQL 16 o superior y Python
3.12 o superior; los datos de demostración ya no se instalan por defecto (--with-demo); los permisos del núcleo van en
security/ir.access.csv (el modelo ir.access reúne permisos y reglas de registro); la API externa es JSON-2 y XML-RPC y
JSON-RPC están obsoletos (se retiran en Odoo 22); la vista de lista se llama <list> desde Odoo 18. La localización
ecuatoriana l10n_ec es libre; la facturación electrónica con el SRI (l10n_ec_edi), el ATS, Código de barras y la
Contabilidad completa son de Enterprise: se practican en las bases educativas gratuitas que la unidad pide al programa
educativo de Odoo, previa habilitación y comprobación por la unidad. La edición queda inactiva y sin fechas ni cupo. Sigue la estructura estándar (estandar.py) y lo carga `manage.py cargar_curso_precargado odoo`.
Revisión editorial del 12 de octubre: se retiran agenda, cupo, tarifas y ofertas no confirmadas;
se cotejaron requisitos Python/PostgreSQL y condiciones de bases educativas. No se repitió la revisión de videos.
"""
from .estandar import clase_en_vivo, deber, evaluacion, guia_pdf, lectura, practica, video

DOC = 'https://www.odoo.com/documentation/20.0'
AREA = 'Área de Tecnologías aplicadas y simulación logística del Laboratorio de Logística, Transporte y Cadena de Suministro'
SALA = 'Sala virtual del aula; acompañamiento sólo con fecha y responsable confirmados en la edición'
DOBLAJE = ('Comprueba si el video ofrece pista de audio en español en ⚙ › Pista de audio. Si no está disponible, '
           'usa subtítulos y la lectura en español; las opciones dependen del canal y del video.')


CURSO = {
    'nombre': 'Odoo Lab: monta, opera y programa el ERP de tu cadena de suministro',
    'lema': 'De instalar Odoo 20 con Docker a operar compras, almacén, ventas y facturación electrónica, y programar tus '
            'propios módulos en Python',
    'clasificacion': 'largo',
    'modalidad': 'mixto',
    'duracion_horas': 40,
    'inscripcion': 'aprobacion',
    'emite_certificado': False,
    'video_url': 'https://www.youtube.com/watch?v=J5eNjkijVc4',
    'descripcion': (
        'Odoo es un ERP modular: integra en un mismo entorno compras, inventario, ventas, '
        'facturación, fabricación y reportes. En este curso lo montas tú mismo, lo operas con una empresa logística '
        'completa y aprendes a programarlo.\n\n'
        'Trabajarás con Andina Trade, una importadora y exportadora ficticia de Tulcán que compra empaques y repuestos, '
        'simula fabricación de snacks, ventas de quesos y distribución internacional por Rumichaca; toda la empresa es ficticia. '
        'La facturación se estudia documentalmente o en sandbox autorizado, sin emitir comprobantes reales. Configurarás almacén, lotes con '
        'caducidad, reabastecimiento automático, multimoneda, Incoterms e indicadores logísticos.\n\n'
        'El programa compara tres entornos: una base educativa en línea si la unidad la habilita, Odoo instalado '
        'con Docker en tu computadora y desde el código fuente, donde crearás un módulo propio para el control de '
        'importaciones y lo conectarás por la API JSON-2.\n\n'
        'Cada módulo tiene lecturas con ejercicios guiados, videos seleccionados y una actividad calificada; hay clases '
        'de acompañamiento que la unidad calendariza, dos prácticas en un entorno virtual o presencial autorizado, y un '
        'proyecto final con sustentación sólo cuando exista una edición y acompañamiento aprobados.'
    ),
    'aprendizajes': (
        'Explicar qué resuelve un ERP y elegir entre Odoo Community, Enterprise, Odoo Online y Odoo.sh\n'
        'Instalar Odoo 20 con Docker Compose y desde el código fuente, y administrar sus bases de datos\n'
        'Configurar una empresa ecuatoriana: localización, usuarios, permisos, productos y contactos\n'
        'Operar compras, reabastecimiento mín./máx. y bajo pedido, y control de facturas de proveedor\n'
        'Diseñar el almacén: ubicaciones, rutas de 1 a 3 pasos, reglas de almacenamiento, lotes, FEFO y conteos\n'
        'Vender al exterior con listas de precios, multimoneda e Incoterms, y facturar electrónicamente al SRI\n'
        'Planificar la fabricación con listas de materiales, órdenes y centros de trabajo\n'
        'Medir la operación con reportes, tableros e indicadores logísticos\n'
        'Programar un módulo propio en Python: modelos, vistas, permisos, herencia y la API JSON-2'
    ),
    'dirigido_a': (
        'Estudiantes de Logística, Administración, Contabilidad y Computación, docentes y personas de empresas de la '
        'zona que quieran implementar o administrar un ERP. Los módulos de programación están pensados para que '
        'quien no programa los siga con los ejemplos listos.'
    ),
    'requisitos': (
        'Cuenta en la plataforma con el perfil completo\n'
        'Computadora con 8 GB de RAM (16 GB recomendado), Windows 10/11 con WSL 2, macOS o Linux, y permisos para '
        'instalar programas (o una estación del área ERP del laboratorio)\n'
        'Conocimientos básicos de logística o de administración; para los módulos de programación ayuda conocer Python, '
        'pero no es obligatorio'
    ),
    'instructores': '',
}

EDICION = {
    'nombre': '2026-II', 'anio': 2026, 'activa': False,
    'horario': '40 horas de estudio y práctica; sesiones de acompañamiento y calendario por configurar.',
    'lugar': 'Aula virtual y espacios autorizados del ' + AREA,
}


COMO_FUNCIONA = (
    'Cómo funciona el curso: avanza por lecturas, ejercicios, evaluaciones y entregas. Las evaluaciones exigen '
    'la nota mínima; las entregas requieren revisión docente. El programa incluye actividades de acompañamiento '
    'que la unidad debe calendarizar antes de activar una edición. La carga de contenidos no abre inscripciones '
    'ni confirma docentes, licencias, espacios, cupos o certificación.\n\n'
    'Acompañamiento: consulta las fechas y condiciones que publique la unidad en la edición aprobada. Una sesión '
    'sin fecha todavía no es una convocatoria. La disponibilidad de grabación depende de la sesión y de la '
    'autorización de sus participantes.\n\n'
    'Las tres formas de usar Odoo en el curso:\n'
    '• En línea: base educativa que el instructor debe solicitar y comprobar antes de asignarla (gratuita, con apps habilitadas, válida '
    '24 meses según las condiciones oficiales). Si se habilita, duplica una plantilla docente; verifica allí Código de barras, Contabilidad y la '
    'facturación electrónica del SRI.\n'
    '• Con Docker: Odoo 20 Community en tu computadora, para administrarlo y para tus módulos.\n'
    '• Desde el código fuente: para programar y depurar.\n\n'
    'La empresa del curso es Andina Trade Cía. Ltda. (ficticia), de Tulcán. Sus productos:\n'
    '• Snack de papa andina 150 g: fabricación virtual con papa, aceite, sal y funda; lote con fecha de '
    'caducidad.\n'
    '• Queso andino 500 g: lo compra a una asociación de productores de El Ángel; lote con caducidad (FEFO).\n'
    '• Caja de cartón corrugado 40×30×20: empaque que se repone con una regla mín./máx.\n'
    '• Rodamiento 6204: repuesto que se importa de Colombia en pesos colombianos.\n'
    '• Lector RFID de mano: equipo con número de serie.\n'
    'Clientes: tiendas de Tulcán e Ibarra y un distribuidor de Ipiales (Colombia) que compra en dólares con Incoterm '
    'FCA Tulcán.'
)

MODULOS = [
    ('Bienvenida: el ERP de Andina Trade', 'Cómo funciona el curso, qué es un ERP y la empresa con la que trabajarás.', [
        lectura('Cómo funciona el curso y la empresa del caso', COMO_FUNCIONA, 15),
        lectura('Qué es un ERP y por qué Odoo', (
            'Un ERP (planificación de recursos empresariales) reúne en una sola base de datos los procesos que en muchas '
            'empresas viven en hojas de cálculo separadas: compras, inventario, ventas, facturación, contabilidad, '
            'fabricación y personas. Su valor está en que un dato se registra una vez y lo usan todos: la orden de venta '
            'reserva el inventario, genera la entrega y luego la factura, y la contabilidad se actualiza sola.\n\n'
            'Odoo es un ERP modular: cada proceso es una app que se instala cuando hace falta (Inventario, Compras, '
            'Ventas, Facturación, Fabricación, Sitio web…) y todas comparten los mismos productos, contactos y '
            'documentos. Está escrito en Python sobre PostgreSQL, con una interfaz web.\n\n'
            'Versiones: Odoo publica una versión mayor cada año en septiembre. La vigente es Odoo 20 (septiembre de '
            '2026), con soporte estándar hasta septiembre de 2029; Odoo 19 y 18 siguen con soporte hasta 2028 y 2027. '
            'En Odoo Online aparecen además versiones intermedias (20.1, 20.2…) cada pocos meses.\n\n'
            'Novedades de Odoo 20 que verás en el curso: mínimos y máximos sugeridos en el reabastecimiento según la '
            'demanda, informe de antigüedad del stock, inventario a una fecha pasada, Incoterm por defecto en la ficha '
            'del proveedor, panel de ventas, un solo botón «Producir» en fabricación y la API JSON-2.\n\n'
            'Ejercicio: anota tres procesos de una empresa que conozcas (o de Andina Trade) que hoy se lleven en hojas '
            'de cálculo y qué app de Odoo los cubriría. Lo comentaremos en la primera clase en vivo.\n\n'
            f'Notas de la versión 20: https://www.odoo.com/odoo-20-release-notes · Versiones con soporte: '
            f'{DOC}/administration/standard_extended_support.html'), 15),
        video('¿Qué es Odoo? En menos de un minuto', 'J5eNjkijVc4', 2, 'La idea de Odoo en un minuto, del canal oficial '
              'en español.', ingles=False),
        video('Lo mejor de Odoo 20', 'YlmN5QcAdLs', 14, 'Presentación oficial de las novedades de Odoo 20 (septiembre '
              'de 2026), la versión que usa el curso.', obligatorio=False),
        clase_en_vivo('Clase en vivo 1: el ERP de Andina Trade', (
            'Presentación del curso y de la empresa del caso. Recorremos una base de Odoo con datos de demostración '
            'siguiendo un pedido de punta a punta (cotización → entrega → factura → pago) y revisamos tu ejercicio de '
            'procesos. Trae la cuenta de la plataforma lista; no hace falta instalar nada.'), None, lugar=SALA),
    ]),
    ('Odoo en línea: ediciones, planes y tu base educativa', 'Community, Enterprise, Odoo Online y Odoo.sh; empezar sin instalar nada.', [
        lectura('Community, Enterprise y las formas de usar Odoo', (
            'Ediciones:\n'
            '• Community: libre (licencia LGPLv3), gratis, se instala donde quieras. Trae Inventario, Compras, Ventas, '
            'Facturación y pagos, Fabricación, Mantenimiento, Flota, Sitio web, Comercio electrónico y Punto de venta.\n'
            '• Enterprise: de pago; agrega, entre otras, Contabilidad completa, Código de barras, Studio (personalizar '
            'sin programar), Calidad, PLM, Documentos, la app móvil, la facturación electrónica del SRI y el ATS, y '
            'soporte y migraciones oficiales.\n\n'
            'Dónde corre:\n'
            '• Odoo Online (SaaS): Odoo lo aloja y lo actualiza; no admite módulos propios.\n'
            '• Odoo.sh: nube de Odoo con repositorio Git, ramas de prueba y módulos propios.\n'
            '• On-premise: en tu servidor o tu computadora (Docker, código fuente o paquetes).\n\n'
            'Compara las opciones One App Free, Standard y Custom en la página oficial de precios. Registra fecha, '
            'país, moneda, periodicidad, impuestos, alojamiento y aplicaciones incluidas; no uses una tarifa del '
            'material como cotización. En Odoo Online comprueba expresamente acceso a API externa y módulos propios '
            'antes de elegir un plan.\n\n'
            'Para el curso: el instructor debe comprobar una base educativa en el programa de Odoo (gratuita, con las apps '
            'que habilite el programa y válida 24 meses). No se entrega una base por cargar este curso. Consulta las '
            'condiciones de actividad: el programa exige conectarse al menos una vez cada tres meses. Exporta antes '
            'del vencimiento de 24 meses y conserva una copia de tus datos sintéticos. '
            'Sin instalar nada, también puedes mirar una base de demostración compartida en https://demo.odoo.com '
            '(dura unas horas).\n\n'
            'Ejercicio guiado: 1) entra a tu base educativa con el enlace que publica el instructor; 2) abre el menú '
            'principal y ubica Inventario, Compras, Ventas, Facturación y Fabricación; 3) en Ajustes › Usuarios, revisa '
            'qué apps tiene tu usuario; 4) activa el modo desarrollador desde Ajustes › Herramientas de desarrollador '
            '(o agregando ?debug=1 a la dirección) y observa qué menús técnicos aparecen.\n\n'
            'Comparación de ediciones: https://www.odoo.com/page/editions · Precios: https://www.odoo.com/pricing · '
            'Programa educativo: https://www.odoo.com/education/program · Odoo Online: '
            f'{DOC}/administration/odoo_online.html'), 20),
        video('Primeros pasos con Odoo: configuración inicial', 'QimdSMX6mkw', 6, 'Serie oficial para el aula: crear '
              'la base educativa gratuita, los contactos y el primer producto.', ingles=False),
        evaluacion('Evaluación: ediciones y planes', [
            ('unica', '¿Bajo qué licencia se publica Odoo Community?', '*LGPLv3\nPropietaria, solo de pago\nCreative Commons',
             'Community es libre (LGPLv3); Enterprise es propietaria.'),
            ('multiple', '¿Qué apps son solo de Odoo Enterprise?', '*Código de barras\n*Studio\n*Contabilidad completa\nInventario\nFabricación',
             'Inventario y Fabricación están en Community; Código de barras, Studio y la Contabilidad completa no.'),
            ('unica', '¿Dónde NO se pueden instalar módulos propios?', '*En Odoo Online\nEn Odoo.sh\nEn un servidor propio',
             'Odoo Online no admite módulos propios; Odoo.sh y on-premise sí.'),
            ('unica', '¿En qué plan está disponible la API externa?', 'One App Free\nStandard\n*Custom',
             'La documentación lo aclara: ni One App Free ni Standard tienen API externa.'),
            ('unica', '¿Cuánto dura una base del programa educativo de Odoo?', '15 días\n*24 meses\nUn semestre',
             'Las bases educativas son gratuitas y válidas 24 meses.'),
        ]),
    ]),
    ('Montarlo con Docker', 'Odoo 20 y PostgreSQL 16 con Docker Compose, la configuración y el gestor de bases.', [
        lectura('Odoo 20 con Docker Compose, paso a paso', (
            'Docker ejecuta Odoo y su base de datos en contenedores, sin instalar Python ni PostgreSQL en tu equipo. En '
            'Windows instala Docker Desktop con WSL 2; en Linux, Docker Engine y el complemento compose.\n\n'
            'La imagen oficial se llama odoo (Docker Hub). Etiquetas: 20.0 (o 20, latest), 19.0 y 18.0. Ojo: los ejemplos '
            'de Docker Hub todavía usan postgres:15, pero Odoo 20 exige PostgreSQL 16 o superior.\n\n'
            '1) Crea una carpeta odoo-lab con dos subcarpetas: config y addons.\n'
            '2) Crea en ella el archivo docker-compose.yml:\n'
            'services:\n'
            '  web:\n'
            '    image: odoo:20.0\n'
            '    depends_on: [db]\n'
            '    ports: ["127.0.0.1:8069:8069"]\n'
            '    volumes: [odoo-web-data:/var/lib/odoo, ./config:/etc/odoo, ./addons:/mnt/extra-addons]\n'
            '    environment: [HOST=db, USER=odoo, PASSWORD=${ODOO_DB_PASSWORD:?defina_la_clave_local}]\n'
            '  db:\n'
            '    image: postgres:16\n'
            '    environment: [POSTGRES_DB=postgres, POSTGRES_USER=odoo, POSTGRES_PASSWORD=${ODOO_DB_PASSWORD:?defina_la_clave_local}]\n'
            '    volumes: [odoo-db-data:/var/lib/postgresql/data]\n'
            'volumes: {odoo-web-data: {}, odoo-db-data: {}}\n'
            '3) Crea un archivo .env local con ODOO_DB_PASSWORD y una clave única; no lo subas al repositorio. '
            'El compose exige esa variable y no publica PostgreSQL. Usa Docker actualizado y conserva la aplicación '
            'en loopback; no es una configuración de producción. Crea config/odoo.conf:\n'
            '[options]\n'
            'addons_path = /mnt/extra-addons\n'
            'admin_passwd = REEMPLAZAR_POR_CLAVE_MAESTRA_UNICA\n'
            'list_db = True\n'
            '4) Reemplaza la clave maestra antes de arrancar. Ejecuta docker compose up -d y revisa '
            'docker compose logs -f web sin compartir claves. El puerto se publica sólo en 127.0.0.1.\n'
            '5) Abre http://localhost:8069 y crea la base: nombre, correo y contraseña del administrador, idioma '
            'Español, país Ecuador. Marca «Datos de demostración» solo en una base de práctica.\n\n'
            'Qué es cada cosa: el puerto 8069 es la aplicación web; el 8072 atiende el chat y las notificaciones en vivo '
            'cuando Odoo corre con varios procesos (workers). El volumen odoo-web-data guarda los adjuntos (filestore) y '
            'odoo-db-data la base de PostgreSQL: si borras los volúmenes, pierdes los datos. En addons pondrás tus '
            'módulos propios.\n\n'
            'Gestor de bases: http://localhost:8069/web/database/manager permite crear, duplicar, respaldar (ZIP con base '
            'y adjuntos), restaurar y borrar bases, protegido por la contraseña maestra (admin_passwd). En un servidor '
            'expuesto a internet, pon list_db = False y una contraseña maestra fuerte.\n\n'
            'Comandos útiles: docker compose stop (detener), docker compose pull y up -d (actualizar la imagen dentro de '
            'la misma versión), docker compose down (borra los contenedores, no los volúmenes).\n\n'
            'Imagen oficial: https://hub.docker.com/_/odoo · Despliegue y gestor de bases: '
            f'{DOC}/administration/on_premise/deploy.html'), 25),
        video('Instalar Odoo con Docker paso a paso', 'vCUBjMytEH8', 11, 'El docker-compose explicado, la carpeta de '
              'addons, la contraseña maestra y los datos de demostración. Está grabado con Odoo 18: usa la imagen '
              'odoo:20.0 y postgres:16 de la lectura.', ingles=False),
        video('Crear una instancia de Odoo 19 con Docker', 'QqvTzCMTCPM', 9, 'Otra forma de armar el compose; el '
              'archivo está en la descripción del video (cambia la versión de PostgreSQL a 16).', ingles=False,
              obligatorio=False),
        deber('Deber: tu Odoo 20 con Docker', (
            'Levanta Odoo 20 con PostgreSQL 16 usando el docker-compose.yml de la lectura. Crea una base llamada '
            '«andina-<tu-apellido>» en español con país Ecuador e instala Inventario. Desde el gestor de bases, haz un '
            'respaldo ZIP. Entrega un PDF con: tu docker-compose.yml y odoo.conf, la salida de «docker compose ps», una '
            'captura del gestor de bases y otra de Inventario instalado. Oculta contraseñas, tokens y datos personales '
            'en todos los archivos/capturas; no entregues .env ni credenciales de la base.'), 60),
    ]),
    ('Montarlo desde el código fuente', 'Odoo 20 desde GitHub en Ubuntu 24.04 (o WSL 2), en modo desarrollador.', [
        lectura('Instalación desde el código fuente en Ubuntu 24.04', (
            'Instalar desde el código es la forma de trabajar para programar y depurar: ves el código de cada app y lo '
            'reinicias al instante. En Windows, usa Ubuntu 24.04 dentro de WSL 2.\n\n'
            'Requisitos de Odoo 20: Python 3.12 o superior (hasta 3.14), PostgreSQL 16 o superior, Git y wkhtmltopdf '
            '0.12.6 (la versión que genera encabezados y pies en los PDF; se instala aparte).\n\n'
            '1) Paquetes: sudo apt install git python3-venv python3-dev build-essential libldap2-dev libpq-dev libsasl2-dev '
            'postgresql\n'
            '2) Usuario de PostgreSQL (Odoo no permite conectarse como postgres): sudo -u postgres createuser -d -R -S $USER '
            'y luego createdb $USER\n'
            '3) Código: git clone --branch 20.0 --single-branch --depth 1 https://github.com/odoo/odoo.git\n'
            '4) Entorno virtual: cd odoo; python3 -m venv .venv; source .venv/bin/activate; pip install -r requirements.txt '
            '(alternativa oficial: sudo ./setup/debinstall.sh instala las dependencias del sistema).\n'
            '5) Arranque: python3 odoo-bin --http-interface=127.0.0.1 --addons-path=addons -d andina --with-demo -i base\n'
            '6) Entra a http://localhost:8069 con el usuario admin y la contraseña admin, y cámbiala.\n\n'
            'Opciones que más usarás: -d (base de datos), -i (instalar módulos), -u (actualizar módulos; ambos piden -d), '
            '--addons-path (carpetas de módulos separadas por comas), --dev=all (recarga el código Python y las vistas '
            'al guardar), --with-demo (en Odoo 20 los datos de demostración ya no vienen por defecto), -c archivo.conf, '
            'y el subcomando shell (python3 odoo-bin shell -d andina) para trabajar con el ORM desde la consola.\n\n'
            'Otras formas: paquetes .deb oficiales para Ubuntu 24.04 desde nightly.odoo.com (apt install odoo) y un '
            'instalador para Windows, que la documentación desaconseja para producción.\n\n'
            'Ejercicio guiado: con el servidor corriendo con --dev=all, abre addons/stock/models/stock_warehouse.py y '
            'busca los campos reception_steps y delivery_steps: verás los valores one_step, two_steps, three_steps, '
            'pick_ship y pick_pack_ship que configurarás en el módulo de Inventario.\n\n'
            f'Guía oficial: {DOC}/administration/on_premise/source.html · Opciones de la línea de comandos: '
            f'{DOC}/developer/reference/cli.html · Paquetes: {DOC}/administration/on_premise/packages.html'), 25),
        video('Instala Odoo de forma local (serie oficial para desarrolladores)', 'PFaunK8C08c', 9, 'Primer episodio '
              'de la serie oficial en español: instalación desde el código fuente y arquitectura de Odoo. Está '
              'grabado con Odoo 17: en Odoo 20 usa Python 3.12 y PostgreSQL 16.', ingles=False),
        guia_pdf('Guía de instalación y del caso Andina Trade (PDF)',
                 'Reúne en un PDF el caso de la empresa y las dos instalaciones para tenerlas a mano en el laboratorio.',
                 ['Cómo funciona el curso y la empresa del caso', 'Odoo 20 con Docker Compose, paso a paso',
                  'Instalación desde el código fuente en Ubuntu 24.04']),
        clase_en_vivo('Clase en vivo 2: taller de instalación', (
            'Instalamos juntos Odoo 20 con Docker y desde el código fuente, resolvemos los errores más comunes (puerto '
            'ocupado, versión de PostgreSQL, dependencias de pip, permisos del usuario de la base) y comparamos las tres '
            'formas de usar Odoo. Ten Docker Desktop o WSL 2 instalado antes de la clase.'), None, lugar=SALA),
        evaluacion('Evaluación: montar Odoo', [
            ('unica', '¿Qué versión mínima de PostgreSQL exige Odoo 20?', '13\n15\n*16',
             'Odoo 20 pide PostgreSQL 16 o superior; ojo con los ejemplos viejos que usan postgres:15.'),
            ('unica', '¿Qué guarda el volumen montado en /var/lib/odoo?', '*Los adjuntos (filestore) y las sesiones\nEl código de Odoo\nLa base PostgreSQL',
             'La base de datos vive en el volumen del contenedor de PostgreSQL.'),
            ('unica', '¿Qué protege la contraseña maestra (admin_passwd)?', '*El gestor de bases de datos\nEl usuario admin de cada base\nEl contenedor de PostgreSQL',
             'Sin ella no se pueden crear, respaldar ni borrar bases desde /web/database/manager.'),
            ('unica', 'En Odoo 20, ¿cómo se instalan los datos de demostración desde la línea de comandos?', 'Vienen por defecto\n*Con --with-demo\nCon --dev=all',
             'Desde Odoo 20 las bases se crean sin datos de demostración salvo que se pidan.'),
            ('unica', '¿Qué opción actualiza un módulo al reiniciar el servidor?', '-i\n*-u\n--addons-path', '-u (update) actualiza; -i instala.'),
            ('corta', '¿En qué puerto atiende por defecto la aplicación web de Odoo? (solo el número)', '8069',
             'El 8072 es para el chat y las notificaciones en vivo con varios procesos.'),
        ]),
    ]),
    ('Configurar la empresa ecuatoriana', 'Compañía, localización, usuarios y permisos, productos y contactos.', [
        lectura('La empresa, la localización de Ecuador y los datos maestros', (
            'Empresa: Ajustes › Compañías: razón social, RUC, dirección en Tulcán, logotipo y moneda USD. Al elegir '
            'Ecuador se instala la localización l10n_ec (libre): plan de cuentas, impuestos del IVA (15 % y 0 %, además '
            'de las tasas históricas), retenciones, tipos de identificación (RUC, cédula, pasaporte) y tipos de '
            'documento y de sustento tributario del SRI.\n\n'
            'Usuarios y permisos: Ajustes › Usuarios y compañías › Usuarios. Cada usuario tiene, por app, un nivel '
            '(por ejemplo, Inventario: Usuario o Administrador). Crea tres usuarios para practicar: Bodega (Inventario: '
            'Usuario), Compras (Compras: Usuario) y Gerencia (Administrador en todo).\n\n'
            'Productos: Inventario › Productos. Tipo «Bienes» con «Seguir inventario» activado para lo que se almacena; '
            'unidad de medida y de compra; categoría (que define el costeo y la valoración); peso y volumen; en la '
            'pestaña Inventario, las rutas y la estrategia de seguimiento (por lotes o por números de serie). En Odoo 20 '
            'las variantes también llevan su código arancelario (HS), útil para exportar.\n\n'
            'Contactos: Contactos › Nuevo. Para empresas ecuatorianas, tipo de identificación RUC y número; para el '
            'distribuidor de Ipiales, país Colombia y su NIT. En la ficha de cada proveedor, pestaña Compras: plazo de '
            'pago, moneda y, en Odoo 20, el Incoterm por defecto.\n\n'
            'Importar datos: cualquier lista (Productos, Contactos) tiene Acción › Importar registros: descarga la '
            'plantilla, llénala en una hoja de cálculo y súbela. Así se migran cientos de productos en minutos.\n\n'
            'Ejercicio guiado: crea los cinco productos de Andina Trade (ver la bienvenida) con su tipo, categoría y '
            'seguimiento; importa diez contactos desde una hoja de cálculo; y comprueba con el usuario Bodega que no puede '
            'ver Compras.\n\n'
            f'Localización Ecuador: {DOC}/applications/finance/fiscal_localizations/ecuador.html · Usuarios: '
            f'{DOC}/applications/general/users.html · Importar datos: {DOC}/applications/essentials/export_import_data.html'), 20),
        video('Datos maestros de la localización de Ecuador', 'kP0bswrxjfs', 10, 'Video oficial: compañía, contactos '
              'con RUC y cédula, productos e impuestos con la localización ecuatoriana.', ingles=False),
        video('Módulos y conceptos básicos de la localización de Ecuador', '7kvsKVog0jk', 10, 'Qué instala cada '
              'módulo de la localización.', ingles=False, obligatorio=False),
        deber('Deber: Andina Trade lista para operar', (
            'En tu base educativa: configura la compañía Andina Trade (RUC ficticio de 13 dígitos, Tulcán, USD), los cinco '
            'productos con su seguimiento correcto (lotes con caducidad para el snack y el queso, número de serie para el '
            'lector RFID), al menos ocho contactos importados desde una hoja de cálculo (clientes ecuatorianos, el '
            'distribuidor de Ipiales, la asociación de productores y el proveedor colombiano de rodamientos) y los tres '
            'usuarios con sus permisos. Entrega un PDF con capturas de cada parte y la hoja de cálculo que importaste.'), 60),
    ]),
    ('Compras y reabastecimiento', 'De la solicitud de cotización a la factura del proveedor, y reponer sin pedir a mano.', [
        lectura('El ciclo de compras y el reabastecimiento automático', (
            'Ciclo: Compras › Nuevo crea una solicitud de cotización (RFQ) para un proveedor; al enviarla y confirmarla '
            'se vuelve orden de compra. La orden genera la recepción en Inventario y, al recibir, se registra la factura '
            'del proveedor.\n\n'
            'Control de facturas: en la ficha del producto (pestaña Compras) eliges facturar sobre cantidades pedidas o '
            'recibidas. Con «cantidades recibidas» se pagan solo las unidades que llegaron: es la conciliación a tres '
            'vías (orden, recepción y factura).\n\n'
            'Acuerdos de compra (Ajustes › Compras › Acuerdos de compra): los acuerdos marco (blanket orders) fijan precio '
            'y cantidad con un proveedor por un período; las licitaciones (calls for tenders) comparan varias '
            'cotizaciones para la misma necesidad. En Odoo 20 los acuerdos admiten secciones y la comparación de '
            'alternativas mejoró.\n\n'
            'Reabastecimiento:\n'
            '• Regla mín./máx. (Inventario › Operaciones › Reabastecimiento): cuando el pronóstico baja del mínimo, Odoo '
            'propone o crea una compra hasta el máximo. En Odoo 20 sugiere el mínimo y el máximo según la demanda y un solo '
            'botón «Pedir» crea la orden.\n'
            '• Bajo pedido (MTO, Ajustes › Logística › Reabastecer bajo pedido): cada venta dispara su propia compra o '
            'fabricación; útil para el rodamiento importado, que no se tiene en stock.\n'
            '• Plazos: el plazo de entrega del proveedor (en la lista de precios de proveedor del producto) y los días de '
            'seguridad mueven la fecha de pedido.\n\n'
            'Ejercicio guiado: 1) pon a la caja de cartón una regla mín. 200 / máx. 1 000 con el proveedor de empaques; '
            '2) vende 900 cajas y observa la propuesta de compra en Reabastecimiento; 3) configura el rodamiento como MTO '
            'con el proveedor colombiano en COP y vende 50: revisa la compra generada y su moneda.\n\n'
            f'Solicitudes de cotización: {DOC}/applications/inventory_and_mrp/purchase/manage_deals/rfq.html · '
            f'Reglas de reabastecimiento: {DOC}/applications/inventory_and_mrp/inventory/warehouses_storage/replenishment/'
            f'reordering_rules.html · MTO: {DOC}/applications/inventory_and_mrp/inventory/warehouses_storage/replenishment/'
            f'mto.html · Control de facturas: {DOC}/applications/inventory_and_mrp/purchase/manage_deals/control_bills.html'), 20),
        video('Primeros pasos con Odoo: comprar, recibir y registrar', 'bbjZP1_4_BE', 4, 'Serie oficial: solicitud '
              'de cotización, orden de compra, recepción y factura del proveedor.', ingles=False),
        video('Reabastecimiento automático paso a paso', 'EVoUzCFqGrw', 7, 'Reglas de reabastecimiento, rutas y '
              'reabastecimiento entre almacenes en Odoo 19.', ingles=False),
        video('Fabricar o comprar bajo pedido (MTO)', 'sBtSYPszKfM', 5, 'Video oficial de la ruta bajo pedido.',
              obligatorio=False),
        clase_en_vivo('Clase en vivo 3: comprar con datos, no a ojo', (
            'Resolvemos en vivo el ejercicio de reabastecimiento: calculamos el mínimo con la demanda y el plazo del '
            'proveedor, comparamos con lo que sugiere Odoo 20 y armamos una licitación entre dos proveedores de empaques.'),
            None, lugar=SALA),
        evaluacion('Evaluación: compras y reabastecimiento', [
            ('unica', '¿Qué documento se convierte en orden de compra al confirmarlo?', '*La solicitud de cotización (RFQ)\nLa factura del proveedor\nLa recepción',
             'La RFQ confirmada pasa a ser orden de compra.'),
            ('unica', '¿Qué política permite pagar solo lo que realmente llegó?', '*Facturar sobre cantidades recibidas\nFacturar sobre cantidades pedidas\nPagar por adelantado',
             'Es la conciliación a tres vías: orden, recepción y factura.'),
            ('unica', 'Una regla mín. 200 / máx. 1 000 y un pronóstico de 150 unidades. ¿Cuánto propone pedir?', '200\n*850\n1 000',
             'Repone hasta el máximo: 1 000 − 150 = 850.'),
            ('unica', '¿Qué conviene para un repuesto caro que no se tiene en stock y se pide cuando un cliente lo compra?', 'Regla mín./máx.\n*Reabastecer bajo pedido (MTO)\nConteo cíclico',
             'Con MTO cada venta genera su propia compra.'),
            ('multiple', '¿Qué datos mueven la fecha en que Odoo propone comprar?', '*El plazo de entrega del proveedor\n*Los días de seguridad\nEl color del producto',
             'Los plazos del proveedor y los días de seguridad adelantan la propuesta.'),
        ]),
    ]),
    ('Inventario I: almacenes, ubicaciones y rutas', 'Diseñar el almacén: ubicaciones, rutas de 1 a 3 pasos y reglas de almacenamiento.', [
        lectura('Almacenes, ubicaciones, rutas y reglas de almacenamiento', (
            'Almacén (Inventario › Configuración › Almacenes): cada almacén tiene un código corto (por ejemplo TUL) que '
            'antecede a sus documentos (TUL/IN/00001).\n\n'
            'Ubicaciones (activa Ajustes › Almacén › Ubicaciones de almacenamiento; luego Configuración › Ubicaciones): '
            'jerarquía como TUL/Stock/Pasillo A/Estante 1/Nivel 2. Tipos: internas (stock real), de proveedor, de cliente, '
            'de tránsito, de pérdida de inventario y de producción. Las ubicaciones virtuales explican de dónde viene y a '
            'dónde va cada movimiento: el stock nunca aparece ni desaparece sin dejar rastro.\n\n'
            'Rutas de varios pasos (activa Ajustes › Almacén › Rutas de varios pasos): en el almacén eliges\n'
            '• Recepción: 1 paso (directo a stock), 2 pasos (entrada → stock) o 3 pasos (entrada → control de calidad → '
            'stock).\n'
            '• Entrega: 1 paso (directo), 2 pasos (picking → despacho) o 3 pasos (picking → empaque → despacho).\n'
            'Cada paso es un documento propio, con su responsable y su ubicación intermedia (WH/Input, WH/Quality, '
            'WH/Output, WH/Packing Zone). Detrás hay reglas de empuje (push: al llegar a una ubicación, mover a la '
            'siguiente) y de tirón (pull: una necesidad en destino crea el movimiento desde el origen). En Odoo 20 hay '
            'además rutas push según la ubicación de destino.\n\n'
            'Cross-dock (recibir y despachar sin almacenar): desde Odoo 19 ya no es una opción del almacén; se arma con una '
            'ruta personalizada que lleve de la entrada directamente a la salida.\n\n'
            'Reglas de almacenamiento (putaway, Configuración › Reglas de almacenamiento): al recibir, envían cada producto '
            'o categoría a su ubicación (por ejemplo, el queso a la cámara fría).\n\n'
            'Ejercicio guiado: configura el almacén TUL de Andina Trade con recepción en 2 pasos y entrega en 3 pasos, '
            'crea la ubicación «Cámara fría» y una regla para que todo producto lácteo vaya allí; recibe 100 quesos y '
            'sigue los documentos que se generan.\n\n'
            f'Almacenes: {DOC}/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/warehouses.html'
            f' · Rutas: {DOC}/applications/inventory_and_mrp/inventory/shipping_receiving/daily_operations/use_routes.html · '
            f'Reglas de almacenamiento: {DOC}/applications/inventory_and_mrp/inventory/shipping_receiving/daily_operations/'
            'putaway.html'), 25),
        video('Gestiona tus almacenes y rutas', 'AYZSbzsk24U', 7, 'Video oficial: almacenes, ubicaciones y rutas.',
              ingles=False),
        video('Rutas de varios pasos: entradas y salidas en 2 y 3 pasos', '3425tKFtYWY', 18, 'Recepciones y entregas '
              'en 2 y 3 pasos, tipos de operación y rutas en Odoo 19.', ingles=False),
        video('Entrega en 3 pasos con paquetes', 'pjztXAbuxD0', 9, 'Picking, empaque y despacho con paquetes. ' + DOBLAJE,
              ingles=False, obligatorio=False),
        practica('Práctica presencial: el minialmacén en Odoo', (
            'Reproduce el almacén TUL en la base educativa. Si la unidad autoriza una práctica presencial, etiqueta sus ubicaciones, '
            'recibimos mercadería en dos pasos con regla de almacenamiento y despachamos un pedido en tres pasos '
            '(picking, empaque en la mesa de packing y despacho), registrando cada paso en Odoo desde las estaciones del '
            'área ERP sólo cuando haya responsable, inducción y reserva aprobados. Sin esos recursos, reproduce el '
            'mismo flujo en ubicaciones virtuales de Odoo; la evidencia debe indicar la modalidad realmente usada.'),
            'Minialmacén y área ERP del Laboratorio de Logística, Transporte y Cadena de Suministro', 180),
        deber('Deber: diseña el almacén TUL', (
            'Entrega un PDF con: el plano del almacén TUL con sus ubicaciones (al menos dos pasillos, la cámara fría, la '
            'entrada, el control y el despacho), la configuración de recepción en 2 pasos y entrega en 3 pasos, dos reglas '
            'de almacenamiento y la trazabilidad de una recepción de quesos y de un despacho al cliente de Ibarra '
            '(capturas de cada documento generado).'), 60),
    ]),
    ('Inventario II: lotes, caducidad, conteos y valoración', 'Trazabilidad, FEFO, inventario físico, oleadas y el valor del stock.', [
        lectura('Lotes, series, FEFO, conteos y valoración', (
            'Trazabilidad (Ajustes › Trazabilidad › Lotes y números de serie): por lote (un código para muchas unidades: '
            'el queso de la producción del lunes) o por número de serie (uno por unidad: cada lector RFID). Con «Fechas de '
            'caducidad» activado, el lote guarda las fechas de consumo preferente, retiro y alerta. El informe de '
            'trazabilidad, unificado en Odoo 20, muestra de dónde vino y a quién se vendió cada lote: es lo que pide una '
            'alerta sanitaria o un retiro de producto.\n\n'
            'Estrategias de salida (en la categoría o la ubicación, «Forzar estrategia de retiro»): FIFO (lo primero que '
            'entró), LIFO, FEFO (lo primero que caduca; obligatorio para el queso y el snack) y la ubicación más '
            'cercana.\n\n'
            'Inventario físico (Inventario › Operaciones › Inventario físico): cuentas, registras la cantidad contada y '
            'aplicas: Odoo crea el movimiento contra la ubicación de pérdida de inventario. Los conteos cíclicos fijan '
            'cada cuántos días contar cada ubicación, para no cerrar el almacén por un inventario anual.\n\n'
            'Picking por lotes y oleadas (Ajustes › Operaciones › Transferencias por lotes, oleadas y clústeres): agrupa '
            'pedidos para recorrer el almacén una sola vez. Paquetes (Ajustes › Paquetes) y el botón «Poner en paquete» '
            'registran qué va en cada caja. Código de barras (Enterprise) permite hacer todo esto con un lector o un '
            'teléfono.\n\n'
            'Valoración (Contabilidad › Configuración › Ajustes): en la categoría del producto eliges el costeo (estándar, '
            'promedio o FIFO) y la valoración manual o automática (asientos contables en tiempo real). Los costos en '
            'destino (Operaciones › Costos en destino) suman flete, seguro y aranceles al costo del producto importado. '
            'Odoo 20 agrega el inventario a una fecha pasada y el informe de antigüedad del stock.\n\n'
            'Ejercicio guiado: recibe dos lotes de queso con caducidades distintas, vende 30 unidades y comprueba que FEFO '
            'tomó el lote que vence antes; haz un conteo con una diferencia de 3 unidades y busca el asiento que generó; '
            'registra un costo en destino de 120 USD de flete sobre una importación de rodamientos.\n\n'
            f'Lotes: {DOC}/applications/inventory_and_mrp/inventory/product_management/product_tracking/lots.html · FEFO: '
            f'{DOC}/applications/inventory_and_mrp/inventory/shipping_receiving/removal_strategies/fefo.html · Conteos: '
            f'{DOC}/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/count_products.html · '
            f'Costos en destino: {DOC}/applications/inventory_and_mrp/inventory/product_management/inventory_valuation/'
            'landed_costs.html'), 25),
        video('Lotes, fechas de caducidad, FIFO y FEFO', 'd5zCn7ETHyY', 8, 'Lotes, alertas de caducidad, FIFO, FEFO y '
              'trazabilidad en Odoo 19.', ingles=False),
        video('Números de serie, lotes y fechas de vencimiento', 'QVdJaop9JYE', 7, 'Tutorial oficial en español.',
              ingles=False, obligatorio=False),
        video('Ajuste de existencias', 'IZccP7aTJ9U', 12, 'Tutorial oficial: conteo físico y ajuste, con la plantilla '
              'de importación.', ingles=False),
        video('Costos en destino: flete, seguro y aranceles', 'wO68SuzIw8c', 9, 'Cómo sumar los gastos de una '
              'importación al costo del inventario.', ingles=False),
        video('Valoración automatizada de inventario', 'wePBbRlicrg', 21, 'Video oficial de la valoración '
              'automática desde Odoo 19.', ingles=False, obligatorio=False),
        video('Código de barras: lo básico', 'LGJJemFE-C0', 7, 'Tipos de código, cómo elegir un lector y cómo usar '
              'el teléfono. ' + DOBLAJE, ingles=False,
              obligatorio=False),
        clase_en_vivo('Clase en vivo 4: simulacro de retiro de un lote', (
            'Un lote de queso salió con un defecto: en vivo usamos el informe de trazabilidad para encontrar a todos los '
            'clientes que lo recibieron, bloqueamos el stock restante y medimos cuánto tardamos. Cerramos con valoración y '
            'costos en destino de una importación.'), None, lugar=SALA),
        evaluacion('Evaluación: trazabilidad y valoración', [
            ('unica', '¿Qué seguimiento corresponde a los lectores RFID, que se controlan uno por uno?', 'Por lote\n*Por número de serie\nSin seguimiento',
             'El número de serie identifica cada unidad.'),
            ('unica', '¿Qué estrategia de salida conviene para el queso?', 'FIFO\nLIFO\n*FEFO',
             'FEFO despacha primero lo que caduca antes.'),
            ('unica', 'Al aplicar un conteo con 3 unidades de menos, ¿contra qué ubicación se mueve la diferencia?', '*La ubicación virtual de pérdida de inventario\nLa ubicación del cliente\nNinguna: se borra',
             'Las ubicaciones virtuales dejan rastro de toda diferencia.'),
            ('unica', '¿Qué herramienta suma el flete y los aranceles al costo de un producto importado?', 'Listas de precios\n*Costos en destino (landed costs)\nReglas de almacenamiento',
             'Los costos en destino reparten esos gastos sobre la recepción.'),
            ('multiple', '¿Qué métodos de costeo ofrece la categoría de producto?', '*Estándar\n*Promedio\n*FIFO\nAleatorio',
             'Estándar, promedio (AVCO) y FIFO.'),
        ]),
    ]),
    ('Ventas y negocios internacionales', 'Cotizaciones, listas de precios, multimoneda, Incoterms y entregas.', [
        lectura('Vender en Ecuador y al exterior', (
            'Ciclo de venta: Ventas › Nuevo crea la cotización (cliente, productos, plazo de pago); al confirmarla se vuelve '
            'orden de venta, reserva el stock y genera la entrega; luego se factura. En Odoo 20 hay un panel de ventas, '
            'líneas solo de descripción, numeración de líneas y cotizaciones guardadas como plantilla.\n\n'
            'Listas de precios (Ventas › Productos › Listas de precios, activándolas en Ajustes): precios por cliente, '
            'cantidad, fecha o moneda; en Odoo 20 también periódicas y por tipo de embalaje. Crea una lista «Mayoristas» '
            'con 8 % de descuento desde 100 unidades y otra «Exportación» en USD para el distribuidor de Ipiales.\n\n'
            'Multimoneda (Contabilidad › Configuración › Monedas): activa COP y actualiza los tipos de cambio (a mano o de '
            'forma automática). Una compra en pesos colombianos se registra en COP y la contabilidad la convierte a USD; '
            'la diferencia de cambio al pagar se contabiliza sola.\n\n'
            'Incoterms: Odoo trae las 11 reglas de Incoterms 2020 (EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DPU, DAP y DDP). '
            'Se eligen en la orden de venta y la de compra, y en la factura (Otra información › Incoterm y lugar del '
            'Incoterm); puedes fijar uno por defecto en Ajustes. Para Andina Trade: FCA Tulcán con el distribuidor de '
            'Ipiales (Andina entrega la mercadería despachada para exportación al transportista en Tulcán); CPT Ipiales '
            'si Andina contrata el transporte. El Incoterm define quién paga y asume el riesgo; Odoo lo imprime en la '
            'factura comercial, que luego respalda la declaración aduanera en Ecuapass.\n\n'
            'Entregas y transportistas (Inventario › Configuración › Métodos de envío): costo fijo, por reglas (peso, '
            'zona) o con conectores de transportistas (de Enterprise). En Odoo 20, el documento CMR del transporte '
            'internacional por carretera sale prellenado desde la entrega.\n\n'
            'Ejercicio guiado: cotiza 200 quesos al distribuidor de Ipiales con la lista «Exportación», Incoterm FCA Tulcán '
            'y entrega en 3 pasos; confirma, despacha y factura; luego registra una compra de rodamientos en COP y revisa '
            'el asiento en USD.\n\n'
            f'Cotizaciones: {DOC}/applications/sales/sales/sales_quotations/create_quotations.html · Listas de precios: '
            f'{DOC}/applications/sales/sales/products_prices/prices/pricing.html · Incoterms: '
            f'{DOC}/applications/finance/accounting/customer_invoices/incoterms.html · Multimoneda: '
            f'{DOC}/applications/finance/accounting/get_started/multi_currency.html'), 25),
        video('Primeros pasos con Odoo: vender, entregar y facturar', 'dBm3aYGhiug', 5, 'Serie oficial: cotización, '
              'orden de venta, entrega y factura.', ingles=False),
        video('Configura listas de precios y promociones', 'Ii2p14oCZ1o', 8, 'Listas de precios en Odoo 19.',
              ingles=False),
        video('Facturación en otra moneda', 'n62Wlq24z-w', 8, 'Video oficial grabado con la localización mexicana; '
              'el manejo de monedas y tipos de cambio es el mismo para Ecuador.', ingles=False, obligatorio=False),
        clase_en_vivo('Clase en vivo 5: una exportación por Rumichaca', (
            'Seguimos una exportación de punta a punta: cotización en USD con Incoterm, despacho en tres pasos, factura '
            'comercial y lo que necesita la declaración aduanera; comparamos FCA, CPT y DAP para el mismo pedido y su '
            'efecto en el precio.'), None, lugar=SALA),
        deber('Deber: tu primera exportación', (
            'En tu base educativa: crea la lista de precios «Exportación», cotiza y confirma una venta al distribuidor de '
            'Ipiales con Incoterm FCA Tulcán, despáchala en tres pasos y factúrala; registra además una compra en COP con '
            'su pago y la diferencia de cambio. Entrega un PDF con los documentos y una tabla que compare quién paga '
            'flete, seguro y trámites en FCA, CPT y DAP para ese pedido.'), 75),
    ]),
    ('Facturación y contabilidad con el SRI', 'Impuestos, retenciones, facturación electrónica y conciliación.', [
        lectura('Facturar en Ecuador con Odoo', (
            'Facturas y pagos: desde la orden de venta, «Crear factura»; al confirmarla queda el asiento contable; el pago '
            'se registra en la factura o se concilia con el extracto bancario (Contabilidad › Conciliar).\n\n'
            'Impuestos (Contabilidad › Configuración › Impuestos): la localización trae el IVA 15 % y 0 %, y las '
            'retenciones en la fuente y del IVA. Cada producto lleva su impuesto de venta y de compra; las posiciones '
            'fiscales los cambian según el cliente (por ejemplo, exportación con IVA 0 %).\n\n'
            'Facturación electrónica con el SRI (módulo l10n_ec_edi, de Enterprise: se practica en la base educativa): en '
            'Contabilidad › Configuración › Ajustes › Localización ecuatoriana cargas el certificado de firma electrónica '
            '(PKCS#12 con su contraseña), eliges el régimen (por ejemplo RIMPE) y dejas desactivado «Usar servidores de '
            'producción» para trabajar en el ambiente de pruebas del SRI, que no tiene validez tributaria. Cada punto de '
            'emisión es un diario con el formato 001-001. Odoo firma y envía factura, nota de crédito, nota de débito, '
            'liquidación de compra y comprobante de retención; con l10n_ec_edi_stock, también la guía de remisión. Odoo 20 '
            'debe contrastarse con las resoluciones vigentes del SRI y con la configuración del proveedor de facturación electrónica '
            'en el RIDE. El ATS se genera con l10n_ec_reports_ats.\n\n'
            'Ejercicio guiado: en la base educativa, emite una factura electrónica de prueba a un cliente de Tulcán, '
            'revisa su clave de acceso y su estado de autorización, registra una retención de un cliente y haz una nota de '
            'crédito por una devolución.\n\n'
            f'Localización Ecuador: {DOC}/applications/finance/fiscal_localizations/ecuador.html · Impuestos: '
            f'{DOC}/applications/finance/accounting/taxes.html · Conciliación: '
            f'{DOC}/applications/finance/accounting/bank/reconciliation.html · SRI: https://www.sri.gob.ec/facturacion-electronica'), 20),
        video('Factura a cliente desde el pedido de venta', 'ohWQN_E2ibs', 6, 'Tutorial oficial en español.',
              ingles=False),
        video('Conciliación bancaria', 'cx0gjNKixcM', 8, 'Tutorial oficial en español.', ingles=False,
              obligatorio=False),
        video('Ambiente de pruebas: localización Ecuador', 'Pi-Z-BQd6OE', 10, 'Video oficial: trabajar con el ambiente '
              'de pruebas del SRI.', ingles=False),
        video('Flujo base de la factura electrónica: localización Ecuador', 'MnfWSRtDKyc', 8, 'Video oficial de la '
              'emisión y autorización (grabado con una versión anterior).', ingles=False, obligatorio=False),
        video('Guía de remisión: localización Ecuador', 'DMkQcmw6OGI', 7, 'La guía de remisión electrónica, clave '
              'para el transporte.', ingles=False, obligatorio=False),
        video('Webinar: localización de Ecuador en Odoo 18', 'teTSBWYwClw', 38, 'El recorrido oficial completo de '
              'la localización.', ingles=False, obligatorio=False),
        evaluacion('Evaluación: facturación y SRI', [
            ('unica', '¿Qué tasa general del IVA trae la localización ecuatoriana vigente?', '12 %\n*15 %\n5 %',
             'Las tasas de 12 % y 5 % quedan como históricas.'),
            ('unica', '¿En qué edición está el módulo de facturación electrónica del SRI (l10n_ec_edi)?', 'Community\n*Enterprise\nEn ninguna',
             'l10n_ec es libre; l10n_ec_edi, el ATS y los informes son de Enterprise.'),
            ('unica', '¿Qué opción mantiene la facturación electrónica en el ambiente de pruebas del SRI?', '*Dejar desactivado «Usar servidores de producción»\nBorrar el certificado\nCambiar de moneda',
             'Sin esa opción, Odoo usa el ambiente de pruebas, sin validez tributaria.'),
            ('multiple', '¿Qué comprobantes electrónicos emite Odoo para el SRI?', '*Factura\n*Comprobante de retención\n*Nota de crédito\nOrden de compra',
             'La orden de compra no es un comprobante tributario.'),
            ('corta', '¿Con qué formato se nombra un punto de emisión en Odoo? (por ejemplo, el primero)', '001-001',
             'Cada punto de emisión es un diario con establecimiento y punto: 001-001.'),
        ]),
    ]),
    ('Fabricación con la minifábrica', 'Listas de materiales, órdenes de fabricación y centros de trabajo.', [
        lectura('Fabricar en Odoo: del pedido a la producción', (
            'Lista de materiales (Fabricación › Productos › Listas de materiales): los componentes y cantidades para '
            'producir una unidad o un lote. Para el snack de papa 150 g: 0,30 kg de papa, 0,04 l de aceite, 2 g de sal y '
            'una funda; puede llevar operaciones (pelar y cortar, freír, sazonar, empacar) en centros de trabajo. Los '
            'kits son listas de materiales que no se fabrican, solo agrupan productos al vender.\n\n'
            'Centros de trabajo (Fabricación › Configuración › Centros de trabajo): capacidad, costo por hora, tiempos de '
            'preparación y limpieza; con ellos Odoo calcula el costo y la planificación.\n\n'
            'Orden de fabricación (Fabricación › Operaciones › Órdenes de fabricación): consume los componentes y produce '
            'el terminado, con su lote y su fecha de caducidad. Se crea a mano, desde una regla mín./máx. con la ruta '
            'Fabricar o bajo pedido desde una venta. En Odoo 20: un solo botón «Producir», consumo flexible por defecto, '
            'producción continua, dividir órdenes, devolverlas a borrador y ver el costo provisional y el real.\n\n'
            'Ejercicio guiado: crea la lista de materiales del snack con tres operaciones, dos centros de trabajo de la '
            'minifábrica y una regla mín./máx. con la ruta Fabricar; vende 500 snacks y sigue la orden de fabricación '
            'hasta el lote producido y su costo.\n\n'
            f'Listas de materiales: {DOC}/applications/inventory_and_mrp/manufacturing/basic_setup/bill_configuration.html · '
            f'Centros de trabajo: {DOC}/applications/inventory_and_mrp/manufacturing/advanced_configuration/'
            'using_work_centers.html'), 20),
        video('Lo que nadie te había mostrado de Manufactura', 'gHjRPelEoJU', 8, 'Listas de materiales, plan maestro '
              'y órdenes de fabricación en Odoo 19.', ingles=False),
        video('Lista de materiales: lo básico', 'EQMjhnHTV5s', 9, 'Video oficial: de la lista de materiales a la '
              'orden de fabricación.', obligatorio=False),
        practica('Práctica presencial: la minifábrica conectada a Odoo', (
            'Simula un lote de kits de muestra siguiendo una orden de '
            'fabricación de Odoo: consumimos componentes del minialmacén, registramos tiempos por centro de trabajo, '
            'etiqueta el lote y compara el costo provisional con el registrado. La modalidad presencial requiere recursos, '
            'responsable, inducción y reserva aprobados; no conectes una maqueta sólo por seguir esta lectura.'),
            'Minifábrica y área ERP del Laboratorio de Logística, Transporte y Cadena de Suministro', 180),
    ]),
    ('Reportes e indicadores logísticos', 'Tablas dinámicas, gráficos, tableros e indicadores para decidir.', [
        lectura('Medir la operación en Odoo', (
            'Cada lista de Odoo tiene vistas de gráfico y de tabla dinámica (pivot): agrupas por producto, almacén, mes o '
            'cliente, filtras y exportas a Excel. Guarda una búsqueda como favorita o agrégala a un tablero.\n\n'
            'Informes de Inventario: Existencias (con valor), Historial de movimientos, Trazabilidad, Rendimiento '
            '(entregas a tiempo) y, en Odoo 20, Antigüedad del stock. Compras y Ventas tienen sus análisis por proveedor, '
            'cliente y producto; Compras en Odoo 20 muestra la tasa de calidad del proveedor.\n\n'
            'Indicadores para Andina Trade (y cómo sacarlos):\n'
            '• Nivel de servicio (pedidos entregados completos y a tiempo / pedidos totales): análisis de entregas por '
            'fecha prometida y fecha efectiva.\n'
            '• Rotación del inventario (costo de ventas / inventario promedio) y días de inventario.\n'
            '• Exactitud del inventario (ubicaciones sin diferencia en el conteo / ubicaciones contadas).\n'
            '• Cumplimiento de proveedores (recepciones a tiempo / recepciones).\n'
            '• Productos con stock antiguo o próximo a caducar (antigüedad del stock y fechas de alerta de los lotes).\n\n'
            'Para análisis más profundos, los datos se exportan o se leen por la API (módulo de programación) hacia los '
            'tableros del curso transversal de Power BI y Metabase.\n\n'
            'Ejercicio guiado: arma una tabla dinámica de ventas por cliente y mes, un gráfico de entregas a tiempo por '
            'semana y una lista de lotes que caducan en los próximos 30 días; agrégalos a un tablero.\n\n'
            f'Informes de inventario: {DOC}/applications/inventory_and_mrp/inventory.html · Vistas y filtros: '
            f'{DOC}/applications/essentials/search.html'), 20),
        video('Conceptos básicos de tableros', 'J9XAZBh5B8I', 10, 'Video oficial: tableros e informes desde Odoo 19.',
              ingles=False),
        deber('Deber: el tablero de Andina Trade', (
            'Con los datos de tu base (al menos 15 ventas, 8 compras y un conteo), entrega un PDF con un tablero de cinco '
            'indicadores (nivel de servicio, rotación, exactitud del inventario, cumplimiento de proveedores y lotes por '
            'caducar), cómo calculaste cada uno en Odoo y una decisión que tomarías con ellos.'), 60),
    ]),
    ('Programar Odoo I: tu primer módulo', 'Estructura de un módulo, modelos, vistas, menús y permisos de Odoo 20.', [
        lectura('Un módulo de Odoo 20 desde cero', (
            'Un módulo es una carpeta en el addons_path con:\n'
            '• __manifest__.py: name, version, depends (por ejemplo [\'stock\']), data (los XML y CSV que carga, en orden), '
            'license (LGPL-3 por defecto) y application.\n'
            '• __init__.py y models/: las clases Python del ORM.\n'
            '• views/: vistas XML (form, list, search, kanban), acciones y menús.\n'
            '• security/: los permisos.\n\n'
            'Créalo con: python3 odoo-bin scaffold andina_importaciones ./mis_addons (agrega ./mis_addons al '
            '--addons-path; con Docker, usa la carpeta addons montada en /mnt/extra-addons).\n\n'
            'Modelo (models/importacion.py):\n'
            'from odoo import api, fields, models\n'
            'class Importacion(models.Model):\n'
            '    _name = \'andina.importacion\'\n'
            '    _description = \'Importación\'\n'
            '    name = fields.Char(\'Referencia\', required=True)\n'
            '    proveedor_id = fields.Many2one(\'res.partner\', \'Proveedor\')\n'
            '    incoterm_id = fields.Many2one(\'account.incoterms\', \'Incoterm\')\n'
            '    estado = fields.Selection([(\'transito\', \'En tránsito\'), (\'aduana\', \'En aduana\'), '
            '(\'liberada\', \'Liberada\')], default=\'transito\')\n'
            '    fob = fields.Monetary(\'Valor FOB\')\n'
            '    flete = fields.Monetary(\'Flete\')\n'
            '    seguro = fields.Monetary(\'Seguro\')\n'
            '    cif = fields.Monetary(\'Valor CIF\', compute=\'_compute_cif\', store=True)\n'
            '    currency_id = fields.Many2one(\'res.currency\', default=lambda self: self.env.company.currency_id)\n'
            '    @api.depends(\'fob\', \'flete\', \'seguro\')\n'
            '    def _compute_cif(self):\n'
            '        for registro in self:\n'
            '            registro.cif = registro.fob + registro.flete + registro.seguro\n\n'
            'Vistas: un registro ir.ui.view con <list> (desde Odoo 18 ya no se llama <tree>) y <form>, una acción '
            'ir.actions.act_window con view_mode list,form y un <menuitem>.\n\n'
            'Permisos en Odoo 20: el núcleo los declara en security/ir.access.csv (modelo ir.access, que reúne los '
            'permisos por grupo y las reglas de registro):\n'
            'id,name,model_id,group_id/id,operation,domain\n'
            'access_importacion_user,importacion.user,andina.importacion,stock.group_stock_user,r,\n'
            'access_importacion_manager,importacion.manager,andina.importacion,stock.group_stock_manager,crud,\n'
            'Una fila sin grupo y con domain restringe en lugar de conceder (es la antigua regla de registro). En módulos '
            'escritos para Odoo 18 y 19 verás ir.model.access.csv e ir.rule: en la clase en vivo comprobamos cómo los '
            'trata Odoo 20.\n\n'
            'Instalar y actualizar: python3 odoo-bin -d andina -i andina_importaciones; después de cambiar modelos o XML, '
            '-u andina_importaciones (con --dev=all, las vistas y el Python se recargan solos).\n\n'
            f'Tutorial oficial «Server framework 101»: {DOC}/developer/tutorials/server_framework_101.html · Manifiesto: '
            f'{DOC}/developer/reference/backend/module.html · ORM: {DOC}/developer/reference/backend/orm.html · Vistas: '
            f'{DOC}/developer/reference/user_interface/view_architectures.html'), 30),
        video('Comencemos con un módulo (serie oficial para desarrolladores)', 'mTnqsxZv69g', 8, 'Episodio 3 de la '
              'serie oficial en español: estructura del módulo y manifiesto.', ingles=False),
        video('Modelos y campos en Odoo', 'nVzmOkwe3Ik', 9, 'Episodio 4 de la serie oficial.', ingles=False),
        video('Aprende a crear vistas', '6lJtPPdxW_I', 10, 'Episodio 8 de la serie oficial (grabada con Odoo 17: '
              'donde diga <tree>, en Odoo 20 escribe <list>).', ingles=False),
        video('Seguridad: permisos de acceso', '4FdOx3WX2C0', 6, 'Episodio 5 de la serie oficial. Muestra '
              'ir.model.access.csv de Odoo 17; compáralo con el ir.access.csv de Odoo 20 de la lectura.',
              ingles=False, obligatorio=False),
        clase_en_vivo('Clase en vivo 6: programamos el módulo de importaciones', (
            'Programación en vivo: creamos andina_importaciones desde el scaffold, con su modelo, la lista, el formulario, '
            'el menú y los permisos de Odoo 20; agregamos el valor CIF calculado y una restricción para que el FOB no sea '
            'negativo. Ten la instalación desde el código fuente funcionando.'), None, lugar=SALA),
        deber('Deber: tu módulo andina_importaciones', (
            'Completa el módulo de la clase: modelo andina.importacion con referencia, proveedor, Incoterm, estado, FOB, '
            'flete, seguro, CIF calculado y fecha estimada de llegada; vistas de lista, formulario y búsqueda (filtro por '
            'estado); menú propio; permisos para usuarios y administradores de Inventario; y una restricción @api.constrains '
            'que impida valores negativos. Entrega el enlace a tu repositorio Git (o el ZIP del módulo) y capturas del '
            'módulo instalado.'), 120),
    ]),
    ('Programar Odoo II: herencia y API externa', 'Extender apps existentes y conectar Odoo con otros sistemas.', [
        lectura('Herencia, botones de acción y la API JSON-2', (
            'Herencia de modelos: para agregar un campo a un modelo que ya existe, se hereda con _inherit:\n'
            'class Picking(models.Model):\n'
            '    _inherit = \'stock.picking\'\n'
            '    importacion_id = fields.Many2one(\'andina.importacion\', \'Importación\')\n'
            '    numero_dae = fields.Char(\'N.º de declaración aduanera\')\n'
            'El manifiesto debe declarar depends: [\'stock\'].\n\n'
            'Herencia de vistas: un ir.ui.view con inherit_id apuntando a la vista original y un xpath:\n'
            '<xpath expr="//field[@name=\'origin\']" position="after"><field name="numero_dae"/></xpath>\n\n'
            'Métodos y botones: un método Python (def action_liberar(self): self.write({\'estado\': \'liberada\'})) se '
            'llama desde un <button name="action_liberar" type="object"/> del formulario. @api.onchange cambia valores '
            'mientras el usuario edita; @api.constrains valida al guardar.\n\n'
            'Consola: python3 odoo-bin shell -d andina abre Python con env listo, por ejemplo: '
            'env[\'stock.quant\'].search([(\'quantity\', \'<\', 10)]).\n\n'
            'API externa JSON-2 (nueva desde Odoo 19): POST https://<servidor>/json/2/<modelo>/<método>, con las '
            'cabeceras «Authorization: bearer <clave de API>», «X-Odoo-Database: <base>» y «Content-Type: application/json». '
            'La clave se crea en Preferencias › Seguridad de la cuenta › Nueva clave de API. Ejemplo con Python:\n'
            'import requests\n'
            'r = requests.post(\'http://localhost:8069/json/2/stock.quant/search_read\',\n'
            '    headers={\'Authorization\': \'bearer \' + CLAVE, \'X-Odoo-Database\': \'andina\'},\n'
            '    json={\'domain\': [[\'location_id.usage\', \'=\', \'internal\']], '
            '\'fields\': [\'product_id\', \'quantity\']})\n'
            'print(r.json())\n'
            'Las API antiguas XML-RPC y JSON-RPC (/xmlrpc, /jsonrpc) están obsoletas: Odoo 20 ya quitó su servicio db y '
            'Odoo 22 (2028) quitará el resto. En Odoo Online la API externa solo existe en el plan Custom; en tu Odoo con '
            'Docker o código fuente está siempre disponible.\n\n'
            'Odoo 20 también permite conectar asistentes de IA a la base mediante MCP (sección AI de la documentación).\n\n'
            'Comunidad: la OCA (Odoo Community Association) mantiene módulos libres revisados en github.com/OCA, por '
            'ejemplo stock-logistics-warehouse y stock-logistics-workflow; a octubre de 2026 sus ramas 20.0 aún no tienen '
            'módulos migrados, así que para usarlos se trabaja en 18.0 o 19.0.\n\n'
            f'API JSON-2: {DOC}/developer/reference/external_api.html · API RPC obsoleta: '
            f'{DOC}/developer/reference/external_rpc_api.html · Herencia: {DOC}/developer/tutorials/server_framework_101/'
            '12_inheritance.html'), 30),
        video('Herencia de modelos y vistas', 'kzMhFXct-eI', 10, 'Episodio 17 de la serie oficial, con xpath.',
              ingles=False),
        video('Herencia de métodos', 'TTKa0LDr8Ys', 7, 'Episodio 16 de la serie oficial: extender un método con '
              'super().', ingles=False, obligatorio=False),
        video('La API de Odoo: cómo funciona y qué cambió', 'MoQf_ADz6p4', 25, 'Charla oficial: las API antiguas y la '
              'nueva API JSON, con ejemplos. ' + DOBLAJE, ingles=False),
        video('Integración externa con la API JSON-2', 'T6DKP7shi1Y', 29, 'Charla oficial dedicada a JSON-2 '
              '(septiembre de 2026).', obligatorio=False),
        evaluacion('Evaluación: programar Odoo', [
            ('unica', '¿Qué atributo agrega campos a un modelo existente sin crear uno nuevo?', '_name con otro nombre\n*_inherit\n_description',
             'Con _inherit (y sin un _name distinto) se extiende el modelo original.'),
            ('unica', '¿Cómo se llama en Odoo 18, 19 y 20 la vista de lista en el XML?', 'tree\n*list\ntable',
             'Desde Odoo 18, <tree> pasó a llamarse <list>.'),
            ('unica', '¿Dónde declaran los permisos los módulos del núcleo de Odoo 20?', 'ir.model.access.csv\n*security/ir.access.csv\nEl manifiesto',
             'El modelo ir.access reúne permisos por grupo y reglas de registro.'),
            ('unica', '¿Qué decorador recalcula un campo cuando cambian otros?', '@api.constrains\n*@api.depends\n@api.model',
             '@api.depends declara de qué campos depende el cálculo.'),
            ('unica', '¿Qué API externa recomienda Odoo 20?', 'XML-RPC\nJSON-RPC\n*JSON-2',
             'XML-RPC y JSON-RPC están obsoletos y se retiran en Odoo 22.'),
            ('corta', 'En la API JSON-2, ¿qué cabecera indica la base de datos? (escríbela tal cual)', 'X-Odoo-Database\nx-odoo-database',
             'La clave va en Authorization: bearer y la base en X-Odoo-Database.'),
        ]),
    ]),
    ('Proyecto final y evaluación final', 'Implementa Andina Trade completa, con tu módulo, y sustenta en vivo.', [
        deber('Proyecto final: Andina Trade en producción', (
            'Implementa en Odoo la operación completa de Andina Trade y entrega un informe en PDF (máximo 15 páginas) con '
            'el enlace a tu base y a tu repositorio:\n'
            '1) Instalación: tu Odoo 20 local con Docker (compose y conf); añade la base educativa sólo si fue habilitada.\n'
            '2) Datos maestros: empresa, usuarios con permisos, productos con su seguimiento y contactos importados.\n'
            '3) Abastecimiento: reglas mín./máx., un producto bajo pedido y una licitación.\n'
            '4) Almacén: recepción en 2 pasos, entrega en 3 pasos, reglas de almacenamiento, FEFO y un conteo cíclico.\n'
            '5) Ventas y exportación: lista de precios, una venta con Incoterm y una compra en COP.\n'
            '6) Facturación: documenta el flujo de una factura y retención con datos sintéticos. Usa el ambiente oficial de '
            'pruebas sólo con credenciales y autorización institucional; si no existe acceso, entrega una simulación '
            'documental rotulada y explica qué validación quedó pendiente.\n'
            '7) Fabricación: lista de materiales y una orden terminada con su lote.\n'
            '8) Indicadores: el tablero con cinco indicadores y una decisión.\n'
            '9) Programación: el módulo andina_importaciones con la herencia en stock.picking (número de declaración '
            'aduanera) y un script que lea por la API JSON-2 el stock por ubicación. No incluyas claves ni secretos en el repositorio.'), 288),
        clase_en_vivo('Clase en vivo 7: sustentación del proyecto final', (
            'Cada participante presenta en 10 minutos su implementación de Andina Trade y responde preguntas del jurado: '
            'un flujo completo en vivo (venta con Incoterm → despacho en tres pasos → factura) y su módulo propio.'),
            None, minutos=150, lugar=SALA),
        evaluacion('Evaluación final', [
            ('unica', '¿Qué ventaja principal tiene un ERP frente a hojas de cálculo separadas?', '*Un dato se registra una vez y lo usan todos los procesos\nEs siempre gratis\nNo necesita usuarios',
             'La integración evita digitar dos veces y desincronizar la información.'),
            ('unica', '¿Qué edición de Odoo trae Inventario, Compras, Ventas y Fabricación sin costo de licencia?', '*Community\nEnterprise\nNinguna',
             'Community es libre (LGPLv3).'),
            ('unica', 'Al montar Odoo 20 con Docker, ¿qué imagen de base de datos corresponde?', 'postgres:13\npostgres:15\n*postgres:16 o superior',
             'Odoo 20 exige PostgreSQL 16 o superior.'),
            ('unica', 'Una entrega en 3 pasos genera, en orden…', '*Picking, empaque y despacho\nEntrada, control y stock\nCompra, recepción y factura',
             'La recepción en 3 pasos es entrada, control de calidad y stock.'),
            ('unica', '¿Qué regla envía el queso a la cámara fría al recibirlo?', '*Una regla de almacenamiento (putaway)\nUna lista de precios\nUna regla de reabastecimiento',
             'Las reglas de almacenamiento deciden la ubicación de destino.'),
            ('unica', '¿Qué estrategia despacha primero el lote que caduca antes?', 'FIFO\n*FEFO\nLIFO', 'First Expired, First Out.'),
            ('unica', 'Con Incoterm FCA Tulcán, ¿dónde entrega Andina Trade la mercadería?', '*Al transportista en Tulcán, despachada para exportación\nEn el almacén del cliente en Ipiales\nEn su propio almacén, sin despachar',
             'En FCA el vendedor entrega al transportista designado en el lugar convenido.'),
            ('unica', '¿Qué suma los aranceles y el flete al costo del producto importado?', '*Los costos en destino\nEl conteo cíclico\nLa posición fiscal', 'Landed costs.'),
            ('unica', '¿Qué documento consume componentes y produce un terminado con su lote?', '*La orden de fabricación\nLa orden de venta\nLa factura', 'Fabricación › Órdenes de fabricación.'),
            ('multiple', '¿Qué es correcto sobre la facturación electrónica del SRI en Odoo?', '*Requiere el certificado de firma electrónica\n*Tiene un ambiente de pruebas sin validez tributaria\n*Es parte de Enterprise\nSe hace con XML-RPC',
             'l10n_ec_edi firma y envía los comprobantes; las pruebas van al ambiente de certificación.'),
            ('unica', '¿Qué se escribe para extender stock.picking en un módulo propio?', "*_inherit = 'stock.picking'\n_name = 'stock.picking.nuevo'\nimport stock",
             'La herencia agrega campos y métodos al modelo existente.'),
            ('corta', '¿Qué subcomando de odoo-bin crea el esqueleto de un módulo nuevo?', 'scaffold',
             'python3 odoo-bin scaffold nombre_modulo carpeta'),
        ]),
    ]),
]
