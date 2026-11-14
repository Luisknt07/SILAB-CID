"""Configuración endurecida para ejecutar la plataforma en producción."""

import os

from django.core.exceptions import ImproperlyConfigured

from apps.core.middleware.origenes import origen_https_valido

from .settings import *  # noqa: F403


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _env_list(name):
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


DEBUG = False
REQUIRE_STRONG_DEPLOYMENT = True
ALLOW_DEMO_DATA_COMMANDS = False

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("replace-"):
    raise ImproperlyConfigured(
        "SECRET_KEY debe contener al menos 50 caracteres aleatorios en producción."
    )

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS or any("*" in host or "://" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS debe enumerar los dominios reales y no puede contener '*'."
    )

CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
if any(not origen_https_valido(origin) for origin in [*CSRF_TRUSTED_ORIGINS, *CORS_ALLOWED_ORIGINS]):  # noqa: F405
    raise ImproperlyConfigured('CSRF y CORS requieren orígenes HTTPS exactos, sin rutas ni comodines.')
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS debe declarar los orígenes HTTPS de producción."
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", True)
# Waitress elimina cabeceras proxy de la sonda loopback cuando Nginx usa otra
# IP. Solo estas dos respuestas sin datos admiten HTTP interno; Nginx impide
# su acceso público. El resto del sitio conserva la redirección HTTPS.
SECURE_REDIRECT_EXEMPT = [r'^salud/(?:vivo|listo)/$']
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

# La excepción SAMEORIGIN se aplica únicamente en la respuesta controlada que
# entrega un recurso multimedia interno.
X_FRAME_OPTIONS = "DENY"

# Sin dominio propio (DNS comodín y certificado) no se ponen en marcha microproyectos.
MICROPROYECTOS_DOMINIO = os.getenv("MICROPROYECTOS_DOMINIO", "").strip()
MICROPROYECTOS_ESQUEMA = os.getenv("MICROPROYECTOS_ESQUEMA", "https").strip()
MICROPROYECTOS_PUERTO_PUBLICO = os.getenv("MICROPROYECTOS_PUERTO_PUBLICO", "").strip()
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

ACCOUNT_PREVENT_ENUMERATION = True
SOCIALACCOUNT_LOGIN_ON_GET = False
# Cualquiera puede crear una cuenta con correo y contraseña. En producción esa
# cuenta no se usa hasta confirmar el correo: sin eso alguien podría registrar
# una dirección institucional ajena antes que su dueño. Google y Microsoft ya
# entregan el correo verificado, así que la entrada social no se detiene.
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
REQUIRE_TRANSACTIONAL_EMAIL = _env_bool("REQUIRE_TRANSACTIONAL_EMAIL", True)

# La base puede estar aislada dentro de la red privada de contenedores o usar
# TLS verificado cuando reside en otro servidor. El check de despliegue exige
# que se declare una de las dos protecciones.
DB_NETWORK_ISOLATED = _env_bool("DB_NETWORK_ISOLATED", False)
DB_SSLMODE = os.getenv("DB_SSLMODE", "").strip().lower()
DB_SSLROOTCERT = os.getenv("DB_SSLROOTCERT", "").strip()
DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DB_CONN_MAX_AGE", "60"))  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
    "options": " ".join(
        (
            f"-c statement_timeout={int(os.getenv('DB_STATEMENT_TIMEOUT_MS', '30000'))}",
            f"-c lock_timeout={int(os.getenv('DB_LOCK_TIMEOUT_MS', '5000'))}",
        )
    ),
}
if DB_SSLMODE:
    DATABASES["default"]["OPTIONS"]["sslmode"] = DB_SSLMODE  # noqa: F405
if DB_SSLROOTCERT:
    DATABASES["default"]["OPTIONS"]["sslrootcert"] = DB_SSLROOTCERT  # noqa: F405

# El destino preparado también se endurece antes del corte. Sus credenciales
# y protección de transporte son independientes; no se heredan de default.
CENTROS_DB_NETWORK_ISOLATED = _env_bool('CENTROS_DB_NETWORK_ISOLATED', False)
if 'centros' in DATABASES:  # noqa: F405
    _centros = DATABASES['centros']  # noqa: F405
    _centros['CONN_MAX_AGE'] = int(os.getenv('CENTROS_DB_CONN_MAX_AGE', '60'))
    _centros['CONN_HEALTH_CHECKS'] = True
    _centros['OPTIONS'] = {
        'connect_timeout': int(os.getenv('CENTROS_DB_CONNECT_TIMEOUT', '3')),
        'options': ' '.join((
            f"-c statement_timeout={int(os.getenv('CENTROS_DB_STATEMENT_TIMEOUT_MS', '30000'))}",
            f"-c lock_timeout={int(os.getenv('CENTROS_DB_LOCK_TIMEOUT_MS', '5000'))}",
        )),
    }
    for _opcion in ('sslmode', 'sslrootcert'):
        _valor = os.getenv('CENTROS_DB_' + _opcion.upper(), '').strip()
        if _valor:
            _centros['OPTIONS'][_opcion] = _valor

CONTENT_SECURITY_POLICY = os.getenv(
    "CONTENT_SECURITY_POLICY",
    "; ".join(
        (
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'self'",
            "form-action 'self' https://accounts.google.com https://login.microsoftonline.com",
            "img-src 'self' data: blob: https:",
            "font-src 'self' data: https://fonts.gstatic.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
            "script-src 'self' 'nonce-{nonce}' https://ajax.googleapis.com https://cdnjs.cloudflare.com",
            "script-src-attr 'none'",
            "connect-src 'self' https:",
            "frame-src 'self' blob: https:",
            "media-src 'self' blob: https:",
            "worker-src 'self' blob:",
        )
    ),
)

# Una variable de entorno puede restringir más la política, pero no desactivar
# las garantías de scripts que requiere este despliegue.
_partes_csp = [d.strip().split() for d in CONTENT_SECURITY_POLICY.split(';') if d.strip()]
if len({d[0] for d in _partes_csp}) != len(_partes_csp):
    raise ImproperlyConfigured('CSP no admite directivas duplicadas.')
_directivas_csp = {d[0]: d[1:] for d in _partes_csp}
if ("'nonce-{nonce}'" not in _directivas_csp.get('script-src', [])
        or any('*' in x or x in {"'unsafe-inline'", "'unsafe-eval'", 'http:', 'https:', 'data:', 'blob:'}
               for x in _directivas_csp.get('script-src', []))
        or _directivas_csp.get('script-src-attr') != ["'none'"]
        or ('script-src-elem' in _directivas_csp
            and _directivas_csp['script-src-elem'] != _directivas_csp.get('script-src'))):
    raise ImproperlyConfigured('CSP requiere nonce por petición y script-src-attr none, sin inline, eval ni comodines para scripts.')

RATE_LIMIT_ENABLED = True
RLS_ENABLED = True

# Los adjuntos subidos no son ejecutables ni legibles por otros usuarios del
# sistema; los directorios creados por Django siguen la misma politica.
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

# Registro explicito a la salida estandar del contenedor o servicio: los
# avisos de seguridad (hosts rechazados, CSRF, subidas sospechosas) y los
# errores de peticion no dependen de que ADMINS este configurado.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "estandar": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "consola": {"class": "logging.StreamHandler", "formatter": "estandar"},
    },
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        "django.security": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["consola"], "level": "ERROR", "propagate": False},
        "apps": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}
