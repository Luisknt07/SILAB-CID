"""Configuración exclusiva para prácticas locales con datos ficticios."""

from pathlib import Path
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent.parent
# El secreto se genera por equipo. No es una credencial institucional.
_secret_path = BASE_DIR / ".secreto-local"
if os.environ.get("ANDINA_SECRET_KEY"):
    SECRET_KEY = os.environ["ANDINA_SECRET_KEY"]
else:
    try:
        with _secret_path.open("x", encoding="utf-8") as secret_file:
            secret_file.write(secrets.token_urlsafe(48))
        try:
            _secret_path.chmod(0o600)
        except OSError:
            pass
    except FileExistsError:
        pass
    SECRET_KEY = _secret_path.read_text(encoding="utf-8").strip()
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventario",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "andina.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tablero"
LOGOUT_REDIRECT_URL = "login"
DATA_UPLOAD_MAX_MEMORY_SIZE = 1_048_576
FILE_UPLOAD_MAX_MEMORY_SIZE = 1_048_576
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
