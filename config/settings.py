"""Configuración del proyecto Restaurante.

Los valores sensibles se leen de variables de entorno (archivo .env en local).
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_browser_reload",
    # Aplicaciones del proyecto
    "core",
    "accounts",
    "menu",
    "orders",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.LoginRequeridoMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

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

# Rutas accesibles sin sesión iniciada (el resto exige login vía middleware).
LOGIN_EXEMPT_URL_NAMES = ("accounts:login", "accounts:registro")
LOGIN_EXEMPT_PATH_PREFIXES = ("/static/", "/django-admin/")

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