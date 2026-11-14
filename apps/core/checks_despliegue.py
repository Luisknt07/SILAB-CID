"""Comprobaciones de despliegue propias de la plataforma."""

from django.conf import settings
from django.core.checks import Error, Tags, register


COMMON_DATABASE_PASSWORDS = {
    "admin",
    "citt",
    "changeme",
    "password",
    "postgres",
    "replace-with-database-password",
    "secret",
}


@register(Tags.security, deploy=True)
def transactional_email_configuration(app_configs, **kwargs):
    if not getattr(settings, "REQUIRE_TRANSACTIONAL_EMAIL", False):
        return []

    errors = []
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if "smtp.EmailBackend" not in backend:
        errors.append(
            Error(
                "El correo transaccional de producción debe usar SMTP.",
                id="webcitt.E001",
            )
        )
    if not getattr(settings, "EMAIL_HOST_USER", ""):
        errors.append(
            Error("Falta EMAIL_HOST_USER para producción.", id="webcitt.E002")
        )
    if not getattr(settings, "EMAIL_HOST_PASSWORD", ""):
        errors.append(
            Error("Falta EMAIL_HOST_PASSWORD para producción.", id="webcitt.E003")
        )
    if not getattr(settings, "SITE_URL", "").startswith("https://"):
        errors.append(
            Error("SITE_URL debe utilizar HTTPS en producción.", id="webcitt.E004")
        )
    return errors


@register(Tags.security, deploy=True)
def hardened_production_configuration(app_configs, **kwargs):
    """Impide publicar una instancia con secretos o limites debiles."""

    if not getattr(settings, "REQUIRE_STRONG_DEPLOYMENT", False):
        return []

    errors = []
    database = settings.DATABASES.get("default", {})
    password = str(database.get("PASSWORD") or "")
    if len(password) < 20 or password.lower() in COMMON_DATABASE_PASSWORDS:
        errors.append(
            Error(
                "DB_PASSWORD debe ser aleatoria, no reutilizada y tener al menos 20 caracteres.",
                id="webcitt.E005",
            )
        )
    if not str(database.get("HOST") or "").strip():
        errors.append(
            Error("DB_HOST es obligatorio en produccion.", id="webcitt.E006")
        )

    options = database.get("OPTIONS", {})
    sslmode = str(options.get("sslmode") or "").lower()
    isolated = getattr(settings, "DB_NETWORK_ISOLATED", False)
    if sslmode != "verify-full" and not isolated:
        errors.append(
            Error(
                "La base debe usar DB_SSLMODE=verify-full o declarar DB_NETWORK_ISOLATED=true.",
                id="webcitt.E007",
            )
        )
    if sslmode == "verify-full" and not options.get("sslrootcert"):
        errors.append(
            Error(
                "DB_SSLROOTCERT es obligatorio cuando DB_SSLMODE=verify-full.",
                id="webcitt.E008",
            )
        )
    if 'centros' in settings.DATABASES:
        centros = settings.DATABASES['centros']
        configuracion = centros.get('OPTIONS', {})
        errores_centros = (
            centros.get('ENGINE') != 'django.db.backends.postgresql'
            or not centros.get('HOST')
            or len(str(centros.get('PASSWORD') or '')) < 20
            or str(centros.get('PASSWORD') or '').lower() in COMMON_DATABASE_PASSWORDS
            or centros.get('USER') == database.get('USER')
            or centros.get('PASSWORD') == database.get('PASSWORD')
            or (configuracion.get('sslmode') != 'verify-full'
                and not getattr(settings, 'CENTROS_DB_NETWORK_ISOLATED', False))
            or (configuracion.get('sslmode') == 'verify-full'
                and not configuracion.get('sslrootcert'))
        )
        if errores_centros:
            errors.append(Error(
                'Centros requiere PostgreSQL, rol y contraseña propios (20 caracteres), '
                'host explícito y red privada declarada o TLS verify-full con CA.',
                id='webcitt.E011',
            ))
    if getattr(settings, "SOCIALACCOUNT_LOGIN_ON_GET", False):
        errors.append(
            Error(
                "El inicio de sesion social debe requerir POST con proteccion CSRF.",
                id="webcitt.E009",
            )
        )
    if "'unsafe-eval'" in getattr(settings, "CONTENT_SECURITY_POLICY", ""):
        errors.append(
            Error(
                "CONTENT_SECURITY_POLICY no puede permitir 'unsafe-eval'.",
                id="webcitt.E010",
            )
        )
    return errors
