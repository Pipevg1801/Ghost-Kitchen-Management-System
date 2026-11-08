"""Configuración del proyecto Restaurante.

Los valores sensibles se leen de variables de entorno (archivo .env en local).
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(nombre, por_defecto=None, requerido=False):
    valor = os.environ.get(nombre, por_defecto)
    if requerido and not valor:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre}.")
    return valor


def env_bool(nombre, por_defecto=False):
    return str(env(nombre, str(por_defecto))).strip().lower() in {"1", "true", "yes", "si", "sí"}


def env_list(nombre, por_defecto=""):
    return [item.strip() for item in env(nombre, por_defecto).split(",") if item.strip()]


SECRET_KEY = env("SECRET_KEY", requerido=True)
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# Render define RENDER_EXTERNAL_HOSTNAME (p. ej. mi-app.onrender.com) en cada servicio web.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
    # Render termina HTTPS en su proxy y reenvía la petición por HTTP.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Aplicaciones del proyecto
    "core",
    "accounts",
    "menu",
    "orders",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.LoginRequeridoMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.navegacion",
                "orders.context_processors.carrito",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de datos: PostgreSQL ---------------------------------------------
DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    # Producción (Render): una sola URL postgresql://usuario:clave@host:puerto/base
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(env("DB_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", requerido=True),
            "USER": env("DB_USER", requerido=True),
            "PASSWORD": env("DB_PASSWORD", requerido=True),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
            "ATOMIC_REQUESTS": False,
            "OPTIONS": {"connect_timeout": int(env("DB_CONNECT_TIMEOUT", "10"))},
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autenticación ---------------------------------------------------------
AUTH_USER_MODEL = "accounts.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email", "nombre")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:inicio"
LOGOUT_REDIRECT_URL = "accounts:login"

# La API de informes valida su propia autenticación y devuelve errores JSON.
REPORTS_API_TOKEN = env("REPORTS_API_TOKEN", "")
LOGIN_EXEMPT_URL_NAMES = (
    "accounts:login", "accounts:registro", "accounts:inicio", "menu:restaurante",
    "reports:api_informes",
)
LOGIN_EXEMPT_PATH_PREFIXES = ("/static/", "/django-admin/", "/media/platos/")
if DEBUG:
    # La recarga del frontend también debe funcionar en login y registro.
    LOGIN_EXEMPT_PATH_PREFIXES += ("/__reload__/",)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Internacionalización --------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# --- Archivos estáticos ----------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # En producción WhiteNoise sirve los estáticos comprimidos y con hash.
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- Mensajes (clases de Bootstrap) ----------------------------------------
MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    # Los 403/404 esperados (accesos por URL a otro rol) no necesitan traza completa.
    "loggers": {"django.request": {"level": "ERROR"}},
}


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
