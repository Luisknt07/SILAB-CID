"""
Configuración Django del SLCID.

Configuracion comun para desarrollo y produccion.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os

from config.identidad import configuracion_identidad
from config.catalogos import configuracion_catalogo
from config.niveles import configuracion_niveles
from config.calendario import configuracion_calendario
from config.regional import configuracion_regional_entorno
from config.roles import configuracion_roles
from config.capacidades import configuracion_capacidades
from config.bases_datos import configurar_centros
from config.opcionales import conexiones_activo, decision, redes_permitidas

# Desarrollo puede leer .env. En producción el gestor de servicios entrega
# solo las variables de cada proceso; no se recargan credenciales elevadas.
if os.getenv('DJANGO_SETTINGS_MODULE') != 'config.settings_production':
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Identidad del producto separada de la institucion. No contiene secretos.
PRODUCT_IDENTITY, INSTITUTION_IDENTITY = configuracion_identidad(os.environ)
ACADEMIC_CATALOG = configuracion_catalogo(os.environ)
ACADEMIC_LEVELS = configuracion_niveles(os.environ)
ACADEMIC_CALENDAR = configuracion_calendario(os.environ)
OPERATIONAL_ROLES = configuracion_roles(os.environ)
# Politica de despliegue: no modifica permisos ni INSTALLED_APPS. Default compatible.
CAPABILITY_CONTROLS = configuracion_capacidades(os.getenv('SLCID_CAPABILITY_CONTROLS', '{}'))

# Microproyectos Django: cada uno se publica en microproyecto-<id>.<dominio> a través
# de una pasarela local. Ver docs/microproyectos-django.md.
MICROPROYECTOS_DOMINIO = os.getenv('MICROPROYECTOS_DOMINIO', 'localhost').strip()
MICROPROYECTOS_ESQUEMA = os.getenv('MICROPROYECTOS_ESQUEMA', 'http').strip()
MICROPROYECTOS_PUERTO_PASARELA = int(os.getenv('MICROPROYECTOS_PUERTO_PASARELA', '19000'))
MICROPROYECTOS_PUERTO_PUBLICO = os.getenv('MICROPROYECTOS_PUERTO_PUBLICO', str(MICROPROYECTOS_PUERTO_PASARELA)).strip()
# Guardar contenido no debe consumir un contenedor sin una puesta en marcha explícita.
MICROPROYECTOS_DESPLIEGUE_AUTOMATICO = os.getenv('MICROPROYECTOS_DESPLIEGUE_AUTOMATICO', 'false').lower() == 'true'
# Navegador remoto para sitios que prohíben incrustarse; comparte la pasarela anterior.
NAVEGADOR_REMOTO_MAX_SESIONES = int(os.getenv('NAVEGADOR_REMOTO_MAX_SESIONES', '3'))
NAVEGADOR_REMOTO_DURACION_MIN = int(os.getenv('NAVEGADOR_REMOTO_DURACION_MIN', '30'))
NAVEGADOR_REMOTO_INACTIVIDAD_MIN = int(os.getenv('NAVEGADOR_REMOTO_INACTIVIDAD_MIN', '5'))
NAVEGADOR_REMOTO_MEMORIA = os.getenv('NAVEGADOR_REMOTO_MEMORIA', '2g')
NAVEGADOR_REMOTO_IMAGEN = os.getenv('NAVEGADOR_REMOTO_IMAGEN', 'lscr.io/linuxserver/chromium:latest')

# Clases en vivo dentro del aula: la dirección de la API de BigBlueButton y su secreto compartido. Sin ellos,
# las clases usan YouTube Live o un enlace externo.
CLASES_EN_VIVO_BBB_URL = os.getenv('CLASES_EN_VIVO_BBB_URL', '').strip()
CLASES_EN_VIVO_BBB_SECRETO = os.getenv('CLASES_EN_VIVO_BBB_SECRETO', '').strip()
CLASES_EN_VIVO_BBB_CHECKSUM = os.getenv('CLASES_EN_VIVO_BBB_CHECKSUM', 'sha256').strip()
# O Daily, en la nube: su clave de API y el dominio de la cuenta (por ejemplo upec.daily.co). Lo que se conecta desde
# la pantalla «Servidor de clases en vivo» tiene prioridad sobre estas variables.
CLASES_EN_VIVO_DAILY_API_KEY = os.getenv('CLASES_EN_VIVO_DAILY_API_KEY', '').strip()
CLASES_EN_VIVO_DAILY_DOMINIO = os.getenv('CLASES_EN_VIVO_DAILY_DOMINIO', '').strip()
NAVEGADOR_REMOTO_DOMINIOS_EXTRA = os.getenv(
    'NAVEGADOR_REMOTO_DOMINIOS_EXTRA', 'youtube.com youtube-nocookie.com googlevideo.com vimeo.com')
CAPABILITY_STATE_PROVIDER = 'apps.configuracion_institucional.capacidades.selectors'
# Proveedor opcional instalado por el despliegue; no proviene de datos del admin.
PUBLIC_IDENTITY_PROVIDER = 'apps.configuracion_institucional.selectors.identidad_publicada'
ACADEMIC_CATALOG_PROVIDER = 'apps.configuracion_institucional.catalogos.selectors.catalogo_publicado'
ACADEMIC_LEVELS_PROVIDER = 'apps.configuracion_institucional.niveles.selectors.niveles_publicados'
ACADEMIC_CALENDAR_PROVIDER = 'apps.configuracion_institucional.calendario.selectors.calendario_publicado'
UNIT_TYPOLOGY_PROVIDER = 'apps.configuracion_institucional.tipologias.selectors.tipologias_publicadas'
# Las novedades que publican las unidades llegan a «Noticias» del portal.
PORTAL_NEWS_PROVIDER = 'apps.gestion_unidades.presentation.novedades.novedades_del_portal'
# Los Centros I+D nombran y enlazan las unidades con las que se articulan por el contrato del directorio.
# Escenarios de contenido visibles únicamente en desarrollo (DEBUG).
CENTROS_ID_ESCENARIOS_OPERATIVOS = tuple(s.strip() for s in os.getenv('CENTROS_ID_ESCENARIOS_OPERATIVOS', '').split(',') if s.strip())
CENTROS_ID_UNIT_PROVIDER = 'apps.directorio_unidades.selectors.obtener_identidad_publica'
# Y dibujan las sedes de la institución en su mapa de ubicación con el mismo contrato que las unidades.
CENTROS_ID_SEDES_PROVIDER = 'apps.directorio_unidades.presentation.ubicacion.sedes_en_el_mapa'

# Todo lo que la aplicacion escribe en ejecucion vive bajo var/: adjuntos,
# estaticos recopilados, caches, registros, salidas y la marca privada. El
# codigo fuente nunca se mezcla con datos de ejecucion en la raiz.
VAR_DIR = BASE_DIR / "var"
MICROPROYECTOS_DIRECTORIO = VAR_DIR / 'microproyectos'

# Matplotlib genera una cache de fuentes al importar los reportes. Se dirige a
# una ruta escribible de la aplicacion para evitar bloqueos por perfiles de
# usuario sin permisos en servidores y tareas programadas.
_matplotlib_cache = Path(
    os.getenv("MPLCONFIGDIR", VAR_DIR / "cache" / "matplotlib")
)
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
CORS_ALLOWED_ORIGINS = tuple(o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip())
RATE_LIMIT_ENABLED = False
# También permite usar un rol web restringido en el servidor local. Producción
# lo impone siempre; el contexto del usuario se limita a cada transacción.
RLS_ENABLED = os.getenv('SLCID_RLS_ENABLED', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
RATE_LIMIT_AUTH_PER_MINUTE = int(os.getenv('RATE_LIMIT_AUTH_PER_MINUTE', '10'))
RATE_LIMIT_WRITE_PER_MINUTE = int(os.getenv('RATE_LIMIT_WRITE_PER_MINUTE', '120'))

# SECURITY WARNING: don't run with debug turned on in production!
# Use a project-specific variable first. Some Windows environments define a
# generic DEBUG value (for example, "release"), which must not silently turn
# off Django's local static-file server.
DEBUG = os.getenv('DJANGO_DEBUG', os.getenv('DEBUG', 'False')).lower() == 'true'

# Las cargas ficticias exigen habilitación explícita además de la confirmación
# del comando. Producción vuelve a cerrarlas de forma incondicional.
ALLOW_DEMO_DATA_COMMANDS = os.getenv(
    'SLCID_ALLOW_DEMO_DATA_COMMANDS',
    'False',
).strip().lower() in {'1', 'true', 'yes', 'si', 'sí', 'on'}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1').split(',')
    if host.strip()
]

# Microsoft/Azure OAuth (compatibilidad con distintos nombres de variables)
G_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
G_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
MS_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID') or os.getenv('MICROSOFT_APPLICATION_ID', '')
MS_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET') or os.getenv('MICROSOFT_SECRET_VALUE', '')
MS_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID') or os.getenv('MICROSOFT_DIRECTORY_ID', 'organizations')


# Application definition

INSTALLED_APPS = [
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'apps.core.apps.CoreConfig',
    'apps.directorio_unidades.apps.DirectorioUnidadesConfig',
    'apps.gestion_unidades.apps.GestionUnidadesConfig',
    'apps.recursos.apps.RecursosConfig',
    'apps.reservas.apps.ReservasConfig',
    'apps.formacion.apps.FormacionConfig',
    'apps.documentos.apps.DocumentosConfig',
    'apps.finanzas.apps.FinanzasConfig',
    'apps.laboratorios.operacion.apps.LaboratoriosOperacionConfig',
    'apps.plantas_piloto.operacion.apps.PlantasOperacionConfig',
    'apps.centros_experimentales.operacion.apps.CampoExperimentalConfig',
    'apps.observatorios.operacion.apps.ObservacionConfig',
    'apps.integraciones.apps.IntegracionesConfig',
    'apps.historial_modelos.apps.HistorialModelosConfig',
    'apps.configuracion_institucional.apps.ConfiguracionInstitucionalConfig',
    'apps.portal.apps.PortalConfig',
    'apps.laboratorios.apps.LaboratoriosConfig',
    'apps.plantas_piloto.apps.PlantasPilotoConfig',
    'apps.centros_experimentales.apps.CentrosExperimentalesConfig',
    'apps.observatorios.apps.ObservatoriosConfig',
    'apps.centros_id.apps.CentrosIDConfig',
    

     'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.microsoft',
    'guardian',  # Añadido django-guardian
]

# Módulos opcionales: se instalan por despliegue y, apagados, no dejan tablas,
# rutas ni administración. Conexiones físico-digitales: apps/conexiones/README.md.
MODULO_CONEXIONES = conexiones_activo()
if MODULO_CONEXIONES:
    INSTALLED_APPS.append('apps.conexiones.apps.ConexionesConfig')
# Envíos por minuto que admite cada dispositivo; uno por minuto con todas sus lecturas es lo habitual.
CONEXIONES_ENVIOS_POR_MINUTO = int(os.getenv('SLCID_CONEXIONES_ENVIOS_POR_MINUTO', '60'))

SITE_ID = 1

LOGIN_REDIRECT_URL = '/'  # ruta a la que va después de loguearse
LOGOUT_REDIRECT_URL = '/' # ruta después de cerrar sesión

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.core.middleware.security.SecurityHeadersMiddleware',
    'apps.core.presentation.salud.SaludInternaMiddleware',
    'apps.core.middleware.origenes.OrigenesPermitidosMiddleware',
    'apps.core.middleware.estaticos.EstaticosNegociadosMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'apps.core.presentation.presentacion_institucional.PresentacionInstitucionalMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.core.middleware.administracion.AccesoAdministracionMiddleware',
    'apps.core.middleware.filas.ContextoFilasMiddleware',
    'apps.core.middleware.limites.LimitePeticionesMiddleware',
    'apps.core.middleware.entradas.ValidacionEntradaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.panel_trabajo.PanelTrabajoMiddleware',
    # Sin datos institucionales vigentes no se entra a reservas ni a gestión.
    'apps.core.usuarios.middleware.PerfilInstitucionalVigenteMiddleware',
]
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': G_CLIENT_ID,
            'secret': G_CLIENT_SECRET,
            'key': '',
        },
    },
    'microsoft': {
        'tenant': MS_TENANT_ID,
        'SCOPE': ['User.Read', 'email', 'openid', 'profile'],
        'AUTH_PARAMS': {'prompt': 'select_account'},
        'APP': {
            'client_id': MS_CLIENT_ID,
            'secret': MS_CLIENT_SECRET,
            'key': '',
        },
    },
}

# ✅ AGREGAR: Configuraciones para saltarse páginas intermedias
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*']
ACCOUNT_SESSION_REMEMBER = True
SOCIALACCOUNT_QUERY_EMAIL = True

# ✅ AGREGAR: Configuración adicional para evitar duplicados
ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_PREVENT_ENUMERATION = False
SOCIALACCOUNT_EMAIL_REQUIRED = True

# ✅ Configurar adaptador personalizado
SOCIALACCOUNT_ADAPTER = 'apps.core.acceso.social.CustomSocialAccountAdapter'
ALLOWED_SOCIAL_EMAIL_DOMAINS = [
    domain.strip().lower()
    for domain in os.getenv(
        'ALLOWED_SOCIAL_EMAIL_DOMAINS',
        'gmail.com,upec.edu.ec,labs.upec.edu.ec'
    ).split(',')
    if domain.strip()
]
SOCIAL_UPEC_GROUP_NAME = os.getenv('SOCIAL_UPEC_GROUP_NAME', 'UsuariosUPEC')
SOCIAL_GMAIL_GROUP_NAME = os.getenv('SOCIAL_GMAIL_GROUP_NAME', 'UsuariosGmail')

# Entrada al administrador. El segundo factor (aplicación autenticadora) es
# optativo en desarrollo y obligatorio en producción. Las redes limitan desde
# dónde responde el administrador; vacío, desde cualquier dirección.
ADMIN_SEGUNDO_FACTOR = bool(decision('SLCID_ADMIN_SEGUNDO_FACTOR'))
ADMIN_SEGUNDO_FACTOR_HORAS = int(os.getenv('SLCID_ADMIN_SEGUNDO_FACTOR_HORAS', '12'))
ADMIN_REDES_PERMITIDAS = redes_permitidas(os.getenv('SLCID_ADMIN_REDES_PERMITIDAS', ''))

ROOT_URLCONF = 'config.urls'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # permisos normales
    'allauth.account.auth_backends.AuthenticationBackend',  # necesario para allauth
    'guardian.backends.ObjectPermissionBackend',  # permisos por objeto
)

ANONYMOUS_USER_NAME = 'None'  # Recomendado para django-guardian

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # Asegúrate de que esta línea esté configurada
        'APP_DIRS': False,
        'OPTIONS': {
            'libraries': {'marca': 'apps.core.templatetags.marca'},
            'loaders': [('django.template.loaders.cached.Loader', [
                'apps.core.presentation.template_loaders.FilesystemLoader',
                'apps.core.presentation.template_loaders.AppDirectoriesLoader',
            ])],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.presentation.identidad.identidad_publica',
                'apps.core.presentation.regional.regional_publica',
                'apps.portal.context_processors.institutional_navigation',
                'apps.integraciones.context_processors.reservation_notifications',
                'apps.integraciones.context_processors.seguimiento_funcional',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# El destino se puede preparar con el flag desactivado. Activarlo exige haber
# verificado la copia; nunca provoca una migración ni copia automática.
CENTROS_DB_ENABLED = configurar_centros(DATABASES, os.environ)
DATABASE_ROUTERS = ['config.router_centros.RouterCentros']


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
# La plataforma completa no puede incrustarse en marcos. Las respuestas
# multimedia que realmente lo necesitan habilitan SAMEORIGIN de forma puntual.
_requested_x_frame_options = os.getenv('X_FRAME_OPTIONS', 'DENY').upper()
X_FRAME_OPTIONS = (
    _requested_x_frame_options
    if _requested_x_frame_options in {'DENY', 'SAMEORIGIN'}
    else 'DENY'
)

# Los dominios públicos y túneles se declaran en el entorno. Los dos orígenes
# locales son estables y permiten iniciar sesión al publicar el puerto 8000
# desde un IDE: el proxy puede marcar la petición como HTTPS aunque el navegador
# conserve http://localhost:8000 como Origin. settings_production reemplaza
# esta lista y sigue exigiendo únicamente los dominios HTTPS desplegados.
_csrf_origins_from_env = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    *_csrf_origins_from_env,
]))

# Usa un nombre propio para no confundir cookies de otras aplicaciones Django
# que hayan pasado por el mismo navegador o tunel de desarrollo.
CSRF_COOKIE_NAME = 'citt_csrftoken'
CSRF_FAILURE_VIEW = 'apps.core.usuarios.views.csrf_failure_view'

# Fuerza a que todos los enlaces generados usen HTTPS (evita el error de conexión rechazada)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

REGIONAL_CONFIGURATION = configuracion_regional_entorno(os.environ)
LANGUAGE_CODE = REGIONAL_CONFIGURATION.idioma

TIME_ZONE = REGIONAL_CONFIGURATION.zona_horaria

USE_I18N = True

LANGUAGES = [('es', 'Español'), ('en', 'English')]
LOCALE_PATHS = [BASE_DIR / 'locale']
LANGUAGE_COOKIE_NAME = 'slcid_language'
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
LANGUAGE_COOKIE_HTTPONLY = True
LANGUAGE_COOKIE_SAMESITE = 'Lax'
LANGUAGE_COOKIE_SECURE = os.getenv('LANGUAGE_COOKIE_SECURE', 'False').lower() == 'true'

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
# Los archivos fuente viven en los static/ de cada app y Django los descubre mediante
# AppDirectoriesFinder. No se registra la misma carpeta en STATICFILES_DIRS
# para evitar duplicados durante collectstatic.
STATIC_ROOT = os.path.join(VAR_DIR, 'static')
# Huella de contenido (caché de un año), compresión y derivados WebP de las
# imágenes pesadas. Los originales conservan su nombre: apps/core/estaticos.py.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'apps.core.estaticos.AlmacenEstaticos'},
}
# Un estático citado sin huella (rutas armadas en JavaScript o guardadas en
# datos) se revalida cada diez minutos; los que llevan huella son inmutables.
WHITENOISE_MAX_AGE = 0 if DEBUG else int(os.getenv('SLCID_STATIC_MAX_AGE', '600'))
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(VAR_DIR, 'media')
# Dos decisiones de publicación que cada instalación declara en su entorno.
# Sin declarar valen falso; producción exige que se escriban (slcid.E014).
#   medicion_metas: medición automática de metas del expediente. Activar
#     después de aplicar documentos.0002 en la base del expediente.
#   equipos_verificados: mientras se cargan los datos los equipos se toman
#     como existentes; al exigirlo, el público solo ve y reserva aquellos cuya
#     existencia confirmó la unidad.
DECISIONES_DE_PUBLICACION = {
    'SLCID_MEDICION_METAS_HABILITADA': decision('SLCID_MEDICION_METAS_HABILITADA'),
    'SLCID_EXIGIR_EQUIPOS_VERIFICADOS': decision(
        'SLCID_EXIGIR_EQUIPOS_VERIFICADOS', heredada='CITT_EXIGIR_EQUIPOS_VERIFICADOS'),
}
MEDICION_METAS_HABILITADA = bool(DECISIONES_DE_PUBLICACION['SLCID_MEDICION_METAS_HABILITADA'])
# El nombre interno se conserva: lo usan el código y las pruebas existentes.
CITT_EXIGIR_EQUIPOS_VERIFICADOS = bool(DECISIONES_DE_PUBLICACION['SLCID_EXIGIR_EQUIPOS_VERIFICADOS'])

# El editor de una unidad envía en un solo formulario todos sus archivos, bloques y responsables: con muchos
# recursos pasa de los 1000 campos que Django admite por omisión y el guardado fallaba con TooManyFieldsSent.
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv('DJANGO_DATA_UPLOAD_MAX_NUMBER_FIELDS', '20000'))
TEST_RUNNER = 'config.testing.PruebasAisladas'
# Los borradores de marca nunca se sirven por el alias publico MEDIA_URL.
INSTITUTION_LOGO_ROOT = os.environ.get(
    'INSTITUTION_LOGO_ROOT', os.path.join(VAR_DIR, 'private', 'institutional-brand')
)

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Correo transaccional. En desarrollo se muestra en consola; en producción se
# configura SMTP mediante variables de entorno y el comando programado de reservas.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.office365.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes', 'si'}
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '20'))
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or INSTITUTION_IDENTITY['correo'])
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')
RESERVATION_EMAIL_MAX_ATTEMPTS = int(os.getenv('RESERVATION_EMAIL_MAX_ATTEMPTS', '5'))
DOCUMENT_SMS_BACKEND = os.getenv('DOCUMENT_SMS_BACKEND', '')
RESERVATION_EMAIL_RETRY_MINUTES = int(os.getenv('RESERVATION_EMAIL_RETRY_MINUTES', '15'))
RESERVATION_REMINDER_INTERVAL_MINUTES = int(os.getenv('RESERVATION_REMINDER_INTERVAL_MINUTES', '15'))
RESERVATION_OPERATIONAL_ALERT_DAYS = int(os.getenv('RESERVATION_OPERATIONAL_ALERT_DAYS', '30'))

GRAPPELLI_ADMIN_TITLE = f"ADMIN · {PRODUCT_IDENTITY['nombre_corto']}"

# ✅ AGREGAR: Variables de entorno para las credenciales
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID', '')
MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID', 'organizations')

# Alias para soportar variables existentes en .env
MICROSOFT_CLIENT_ID = MICROSOFT_CLIENT_ID or os.getenv('MICROSOFT_APPLICATION_ID', '')
MICROSOFT_CLIENT_SECRET = MICROSOFT_CLIENT_SECRET or os.getenv('MICROSOFT_SECRET_VALUE', '')
MICROSOFT_TENANT_ID = MICROSOFT_TENANT_ID if MICROSOFT_TENANT_ID != 'organizations' else os.getenv('MICROSOFT_DIRECTORY_ID', 'organizations')

