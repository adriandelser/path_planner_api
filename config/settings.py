"""
Django settings

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import json
import logging
import os

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from sentry_sdk.integrations.django import DjangoIntegration

from django_extras.utils import load_env_val

logger = logging.getLogger(__name__)

# Project info
SERVICE_NAME = load_env_val("SERVICE_NAME")
PROJECT_NAME = "Server Template"
PROJECT_VERSION = "0.1"
PROJECT_DESCRIPTION = "Base Django Template"
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
# Environment checks
ENVIRONMENT = os.environ["ENVIRONMENT"]
ALLOWED_ENVIRONMENTS = {
    "development",
    "build",
    "test",
    "integration",
    "staging",
    "production",
    "prelive",
}

if ENVIRONMENT not in ALLOWED_ENVIRONMENTS:
    raise ImproperlyConfigured(
        f"ENVIRONMENT:{ENVIRONMENT} must be set to one of: {ALLOWED_ENVIRONMENTS}"
    )
# Running in development or production mode
if ENVIRONMENT == "development":
    ALLOW_ANONYMOUS_ADMIN = True
    DEBUG = True
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    DEBUG = False

# Apps
SERVER_TEMPLATE_APPS = [
    "config.apps.ServerTemplateConfig",
    "accounts.config.apps.AccountsConfig",
    "django_extras.config.apps.DjangoExtrasConfig",
]

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "taggit",
    "django_ltree",
]

INSTALLED_APPS = SERVER_TEMPLATE_APPS + DJANGO_APPS + THIRD_PARTY_APPS
AUTH_USER_MODEL = "accounts.User"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": load_env_val("POSTGRES_HOST", "postgres"),
        "NAME": load_env_val("POSTGRES_DB", "dev"),
        "USER": load_env_val("POSTGRES_USER", "dev"),
        "PASSWORD": load_env_val("POSTGRES_PASSWORD", "dev"),
    }
}

_db_middleware = []

if "POSTGRES_SLAVE_HOST" in os.environ:
    from django_replicated.settings import *  # noqa

    DATABASES["slave"] = {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": os.environ["POSTGRES_SLAVE_HOST"],
        "NAME": load_env_val("POSTGRES_SLAVE_DB", "dev"),
        "USER": load_env_val("POSTGRES_SLAVE_USER", "dev"),
        "PASSWORD": load_env_val("POSTGRES_SLAVE_PASSWORD", "dev"),
    }

    REPLICATED_DATABASE_SLAVES = ["slave"]
    DATABASE_ROUTERS = ["django_replicated.router.ReplicationRouter"]
    _db_middleware = ["django_replicated.middleware.ReplicationMiddleware"]

# Middleware
MIDDLEWARE = [
    *_db_middleware,
    "crum.CurrentRequestUserMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_extras.cache.CacheMiddleware",
]


# Redis config (used for caching and celery)
# if REDIS_URL is provided it will take precedence, REDIS_HOST etc
# left for backwards compatability
_REDIS_HOST = load_env_val("REDIS_HOST")
_REDIS_PORT = int(load_env_val("REDIS_PORT", "6379"))
_REDIS_DB = int(load_env_val("REDIS_DB", "1"))
REDIS_URL = load_env_val(
    "REDIS_URL", f"redis://{_REDIS_HOST}:{_REDIS_PORT}/{_REDIS_DB}"
)

REDIS_ENABLED = any((REDIS_URL, _REDIS_HOST))

# Celery
CELERY_RESULT_BACKEND = REDIS_URL if REDIS_ENABLED else None
CELERY_REDIS_CONNECT_RETRY = True
CELERYD_HIJACK_ROOT_LOGGER = False
BROKER_URL = load_env_val("BROKER_URL", REDIS_URL if REDIS_ENABLED else None)
BROKER_TRANSPORT_OPTIONS = {"fanout_prefix": True}

CELERY_TIMEZONE = "UTC"

# Celerybeat tasks / schedule here
CELERYBEAT_SCHEDULE = {}

# Caching
if REDIS_ENABLED:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = "en"
LANGUAGES = (("en", "English"),)
LOCALE_PATHS = ("locale",)

TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = True
USE_TZ = True

# Static files and media (CSS, JavaScript, images)
# Build paths inside the project like this: os.path.join(SITE_ROOT, ...)
SITE_ROOT = os.path.dirname(os.path.dirname(__file__))
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
STATIC_URL = os.path.join(os.getenv("PROXY_PATH", ""), "static/")
if os.getenv("PROXY_PATH", False):
    URL_PREFIX = os.getenv("PROXY_PATH")[1:]
else:
    URL_PREFIX = False
logger.info(f"Use '{URL_PREFIX}' as URL_PREFIX")
if os.getenv("PREPEND_PATH", False):
    PREPEND_PATH = os.getenv("PREPEND_PATH")[1:]
else:
    PREPEND_PATH = False
logger.info(f"Use '{PREPEND_PATH}' as PREPEND_PATH")

MEDIA_ROOT = "/files/media"
MEDIA_URL = "/media/"

STATIC_ROOT = "/files/assets"
STATIC_URL = "/static/"

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Logging
LOGLEVEL = load_env_val("LOGLEVEL", "INFO")

# Base logging config. Logs INFO and higher-level messages to console.
# Also Propagates and delegates to the root handler so that we only have
# to configure that.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(message)s %(asctime)s %(levelname)s "
                "%(name)s %(lineno)d %(funcName)s"
            ),
        },
        "dev": {
            "format": (
                "%(asctime)s [%(levelname)s] "
                "%(name)s:%(lineno)d %(funcName)s - %(message)s"
            )
        },
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": LOGLEVEL,
        },
        # Want tracebacks to be easy to read during development
        "console-dev": {
            "class": "logging.StreamHandler",
            "formatter": "dev",
            "level": "ERROR",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": LOGLEVEL},
        "django": {"handlers": [], "propagate": True, "level": LOGLEVEL},
        "django.request": {"handlers": [], "propagate": True, "level": LOGLEVEL},
        "django.security": {"handlers": [], "propagate": True},
        "celery": {"handlers": [], "propagate": True},
        "gunicorn": {"handlers": [], "propagate": True},
    },
}

if DEBUG:
    LOGGING["loggers"][""]["handlers"].append("console-dev")

# Metrics, exception reporting, etc.
# App insights
AZURE_APP_INSIGHTS_KEY = load_env_val("AZURE_APP_INSIGHTS_KEY", default=False)
if AZURE_APP_INSIGHTS_KEY:
    APPLICATION_INSIGHTS = {
        "ikey": AZURE_APP_INSIGHTS_KEY,
        "use_view_name": True,
        "record_view_arguments": True,
        "log_exceptions": True,
    }
    MIDDLEWARE.append("applicationinsights.django.ApplicationInsightsMiddleware")

# Sentry
SENTRY_DSN = load_env_val("SENTRY_DSN", default=False)
SENTRY_SAMPLE_RATE = load_env_val("SENTRY_SAMPLE_RATE", 0.05)
SENTRY_PERFORMANCE_SAMPLE_RATE = load_env_val("SENTRY_PERFORMANCE_SAMPLE_RATE", 0.05)

if SENTRY_DSN:
    sentry_integrations = [DjangoIntegration()]

    try:
        import celery  # noqa
    except ImportError:
        pass
    else:
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_integrations.append(CeleryIntegration())

    try:
        import redis  # noqa
    except ImportError:
        pass
    else:
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_integrations.append(RedisIntegration())

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=sentry_integrations,
        environment=ENVIRONMENT,
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PERFORMANCE_SAMPLE_RATE,
    )

# Django toolbar
SHOW_BROWSABLE_API = load_env_val("SHOW_BROWSABLE_API", default=True)
SHOW_DJANGO_TOOLBAR = load_env_val("SHOW_DJANGO_TOOLBAR", False)

if SHOW_DJANGO_TOOLBAR:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "debug_toolbar_force.middleware.ForceDebugToolbarMiddleware",
    ] + MIDDLEWARE

# Allow swagger
SHOW_SWAGGER_DOCS = load_env_val("SHOW_SWAGGER_DOCS") in ("true", "1")


def show_toolbar(request):
    return bool(SHOW_DJANGO_TOOLBAR)


DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": SHOW_DJANGO_TOOLBAR}

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "PAGE_SIZE": 15,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# Silence System checks (Use with caution)
SILENCED_SYSTEM_CHECKS = [
    "security.W001",
]

# Miscellaneous
SECRET_KEY = load_env_val("SECRET_KEY", get_random_secret_key())
SESSION_COOKIE_NAME = "app_ssid"

ALLOWED_HOSTS = ["*"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Don't allow site's content to be included in frames/iframes.
X_FRAME_OPTIONS = "DENY"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/"

TEST_RUNNER = "django.test.runner.DiscoverRunner"


# Documentation
SPECTACULAR_SETTINGS = {
    "TITLE": PROJECT_NAME,
    "DESCRIPTION": PROJECT_DESCRIPTION,
    "VERSION": PROJECT_VERSION,
    "SWAGGER_UI_SETTINGS": {
        "useSessionAuth": False,
        "deepLinking": True,
        "displayOperationId": True,
        "defaultModelExpandDepth": 3,
        "loginUrl": "/",
        "logoutUrl": "/",
    },
    "ENUM_NAME_OVERRIDES": {},
}

PRESIGNED_LINK_LIFETIME = int(load_env_val("PRESIGNED_LINK_LIFETIME", "3600"))

# ClamAV
SCANNING_ACTIVE = load_env_val("SCANNING_ACTIVE", "false").lower() in {
    "1",
    "true",
}
SCANNING_HOST = load_env_val("SCANNING_HOST", "clamav")
SCANNING_PORT = int(load_env_val("SCANNING_PORT", "3310"))

PROFILE_REQUESTS = load_env_val("PROFILE_REQUESTS", "false").lower() in {
    "1",
    "true",
}
if PROFILE_REQUESTS:
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE = [
        "silk.middleware.SilkyMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
    ] + MIDDLEWARE
    SILKY_PYTHON_PROFILER = True
    SILKY_META = True

SNS_TOPIC_MAP = json.loads(load_env_val("SNS_TOPIC_MAP", "{}"))
SQS_QUEUES = json.loads(load_env_val("SQS_QUEUES", "{}"))

CELERY_BEAT_SCHEDULE_ACTIVE = load_env_val(
    "CELERY_BEAT_SCHEDULE_ACTIVE", "false"
).lower() in {
    "1",
    "true",
}

AMQP_CONNECTION = load_env_val("AMQP_CONNECTION", "")

CELERYBEAT_SCHEDULE = {} if CELERY_BEAT_SCHEDULE_ACTIVE else {}
CELERY_IMPORTS = []

FEATURE_FLAGS = load_env_val(
    "FEATURE_FLAGS", default=dict(), validation=lambda x: isinstance(x, dict)
)
