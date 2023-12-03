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
from urllib import request

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

import sentry_sdk
from celery.schedules import crontab
from sentry_sdk.integrations.django import DjangoIntegration

from django_extras.utils import load_env_val

logger = logging.getLogger(__name__)

# Project info
SERVICE_NAME = os.environ.get("SERVICE_NAME")
PROJECT_NAME = "Platform API"
PROJECT_VERSION = "0.1"
PROJECT_DESCRIPTION = "Backend API for Croud Control"
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
# Environment checks
ENVIRONMENT = os.environ["ENVIRONMENT"]
ALLOWED_ENVIRONMENTS = {
    "dev",
    "development",
    "build",
    "test",
    "integration",
    "staging",
    "production",
    "prod",
    "prelive",
}

if ENVIRONMENT not in ALLOWED_ENVIRONMENTS:
    raise ImproperlyConfigured(
        f"ENVIRONMENT must be set to one of: {ALLOWED_ENVIRONMENTS}"
    )

if ENVIRONMENT == "dev":
    ENVIRONMENT = "development"
if ENVIRONMENT == "prod":
    ENVIRONMENT = "production"

# Running in development or production mode
if ENVIRONMENT == "development":
    ALLOW_ANONYMOUS_ADMIN = True
    DEBUG = True
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    DEBUG = False
    # Fail early if required keys are not set in prod
    for required_setting in [
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "SECRET_KEY",
    ]:
        os.environ[required_setting]

# Apps
SERVER_TEMPLATE_APPS = [
    "app.apps.CroudAppConfig",
    "clients.config.apps.ClientsConfig",
    "core.config.apps.CoreConfig",
    "files.config.apps.FilesConfig",
    "status.config.apps.StatusConfig",
    "softskills.apps.SoftskillsConfig",
    "users.config.apps.UsersConfig",
    "tasks.config.apps.TasksConfig",
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
]

INSTALLED_APPS = SERVER_TEMPLATE_APPS + DJANGO_APPS + THIRD_PARTY_APPS

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "NAME": os.environ.get("POSTGRES_DB", "dev"),
        "USER": os.environ.get("POSTGRES_USER", "dev"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "dev"),
    }
}

_db_middleware = []

if "POSTGRES_SLAVE_HOST" in os.environ:
    from django_replicated.settings import *  # noqa

    DATABASES["slave"] = {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": os.environ["POSTGRES_SLAVE_HOST"],
        "NAME": os.environ.get("POSTGRES_SLAVE_DB", "dev"),
        "USER": os.environ.get("POSTGRES_SLAVE_USER", "dev"),
        "PASSWORD": os.environ.get("POSTGRES_SLAVE_PASSWORD", "dev"),
    }

    REPLICATED_DATABASE_SLAVES = ["slave"]
    DATABASE_ROUTERS = ["django_replicated.router.ReplicationRouter"]
    _db_middleware = ["django_replicated.middleware.ReplicationMiddleware"]

# Middleware
MIDDLEWARE = [
    "core.utils.middleware.stats_middleware",
    *_db_middleware,
    "crum.CurrentRequestUserMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_extras.cache.CacheMiddleware",
]

AUTH_USER_MODEL = "users.User"

# Redis config (used for caching and celery)
# if REDIS_URL is provided it will take precedence, REDIS_HOST etc
# left for backwards compatability
_REDIS_HOST = os.environ.get("REDIS_HOST")
_REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
_REDIS_DB = int(os.environ.get("REDIS_DB", "1"))
REDIS_URL = os.environ.get(
    "REDIS_URL", f"redis://{_REDIS_HOST}:{_REDIS_PORT}/{_REDIS_DB}"
)

REDIS_ENABLED = any((REDIS_URL, _REDIS_HOST))

# Celery
CELERY_RESULT_BACKEND = REDIS_URL if REDIS_ENABLED else None
CELERY_REDIS_CONNECT_RETRY = True
CELERYD_HIJACK_ROOT_LOGGER = False
BROKER_URL = os.environ.get("BROKER_URL", REDIS_URL if REDIS_ENABLED else None)
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
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO")

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
AZURE_APP_INSIGHTS_KEY = os.environ.get("AZURE_APP_INSIGHTS_KEY", default=None)
if AZURE_APP_INSIGHTS_KEY:
    APPLICATION_INSIGHTS = {
        "ikey": AZURE_APP_INSIGHTS_KEY,
        "use_view_name": True,
        "record_view_arguments": True,
        "log_exceptions": True,
    }
    MIDDLEWARE.append("applicationinsights.django.ApplicationInsightsMiddleware")

# Sentry
SENTRY_DSN = os.environ.get("SENTRY_DSN", default=None)
SENTRY_SAMPLE_RATE = float(os.environ.get("SENTRY_SAMPLE_RATE", 0.05))
SENTRY_PERFORMANCE_SAMPLE_RATE = float(
    os.environ.get("SENTRY_PERFORMANCE_SAMPLE_RATE", 0.05)
)

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
SHOW_DJANGO_TOOLBAR = ENVIRONMENT not in ("prod", "production") and os.environ.get(
    "SHOW_DJANGO_TOOLBAR"
) in ("true", "1")

SHOW_BROWSABLE_API = ENVIRONMENT not in ("prod", "production") and os.environ.get(
    "SHOW_BROWSABLE_API", "true"
) in ("true", "1")

if SHOW_DJANGO_TOOLBAR:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "debug_toolbar_force.middleware.ForceDebugToolbarMiddleware",
    ] + MIDDLEWARE

# Allow swagger
SHOW_SWAGGER_DOCS = os.environ.get("SHOW_SWAGGER_DOCS") in ("true", "1")


def show_toolbar(request):
    return bool(SHOW_DJANGO_TOOLBAR)


DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": show_toolbar,
}

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
}

if ENVIRONMENT == "production":
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]
else:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer"
    ]

    if SHOW_BROWSABLE_API:
        REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [
            "rest_framework.renderers.BrowsableAPIRenderer"
        ]

# Silence System checks (Use with caution)
SILENCED_SYSTEM_CHECKS = [
    "security.W001",
]

# Miscellaneous
SECRET_KEY = os.environ.get("SECRET_KEY", get_random_secret_key())
SESSION_COOKIE_NAME = "app_ssid"

ALLOWED_HOSTS = ["*"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Don't allow site's content to be included in frames/iframes.
X_FRAME_OPTIONS = "DENY"

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
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
    "ENUM_NAME_OVERRIDES": {
        "TaskStates": "tasks.models.Task.States",
        "StageStates": "tasks.models.Stage.States",
        "ClientStates": "clients.models.Client.States",
        "ChannelStates": "clients.models.Channel.States",
        "ContractStates": "clients.models.Contract.States",
        "ClientGatingRestrictions": "clients.models.ClientGatingModel.Restrictions",
        "ClientGatingAccessLevels": "clients.models.ClientGatingUserModel.AccessLevel",
        "CountryStates": "core.models.Country.States",
        "QualificationSources": "users.models.Qualification.Sources",
        "AssigneeStates": "tasks.models.Assignee.AssigneeState",
    },
}

# AWS Config
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-2")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# JWT Auth
AWS_USER_POOL = os.environ.get("AWS_USER_POOL")
AWS_CLIENT_ID = os.environ.get("AWS_CLIENT_ID")
AUTH_ACTIVE_DEFAULT = "false" if ENVIRONMENT in ("dev", "development") else "true"
AUTH_ACTIVE = os.environ.get("AUTH_ACTIVE", AUTH_ACTIVE_DEFAULT).lower() in {
    "1",
    "true",
}
AUTHZ_ACTIVE = os.environ.get("AUTHZ_ACTIVE", "false").lower() in {
    "1",
    "true",
}


def get_rsa_keys():
    """Fetch JWKS from computed Cognito IDP endpoint.
    Returns
    -------

    """

    cognito_pool_full_url = f"{JWT_AUTH['JWT_ISSUER']}/.well-known/jwks.json"
    jwks = json.loads(request.urlopen(cognito_pool_full_url).read())  # nosec
    return {key["kid"]: json.dumps(key) for key in jwks["keys"]}


if AUTH_ACTIVE:
    AUTHENTICATION_BACKENDS = [
        "core.utils.auth.CroudRemoteUserBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]

    permission_classes = [
        "rest_framework.permissions.IsAuthenticated",
    ]

    if AUTHZ_ACTIVE:
        permission_classes.append("core.utils.permissions.IsOwnerPermission")

    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = permission_classes
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
        "rest_framework_jwt.authentication.JSONWebTokenAuthentication",
    ]

    JWT_AUTH = {
        "JWT_PAYLOAD_GET_USERNAME_HANDLER": "core.utils.jwt.auth_user_and_get_username_from_payload",  # noqa
        "JWT_DECODE_HANDLER": "core.utils.jwt.cognito_jwt_decode_handler",
        "JWT_PUBLIC_KEY": {},
        "JWT_ALGORITHM": "RS256",
        "JWT_ISSUER": f"https://cognito-idp.{AWS_REGION}.amazonaws."
        f"com/{AWS_USER_POOL}",
        "JWT_AUTH_HEADER_PREFIX": "Bearer",
    }

    JWT_AUTH["JWT_PUBLIC_KEY"] = get_rsa_keys()

AWS_BUCKET_PUBLIC = os.environ.get("AWS_BUCKET_PUBLIC", "dummy")
AWS_BUCKET_PRIVATE = os.environ.get("AWS_BUCKET_PRIVATE", "dummy")
AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN")
PRESIGNED_LINK_LIFETIME = int(os.environ.get("PRESIGNED_LINK_LIFETIME", "3600"))

# ClamAV
SCANNING_ACTIVE = os.environ.get("SCANNING_ACTIVE", "false").lower() in {
    "1",
    "true",
}
SCANNING_HOST = os.environ.get("SCANNING_HOST", "clamav")
SCANNING_PORT = int(os.environ.get("SCANNING_PORT", "3310"))

PROFILE_REQUESTS = os.environ.get("PROFILE_REQUESTS", "false").lower() in {
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

SNS_TOPIC_MAP = json.loads(os.environ.get("SNS_TOPIC_MAP", "{}"))
SQS_QUEUES = json.loads(os.environ.get("SQS_QUEUES", "{}"))

CELERY_BEAT_SCHEDULE_ACTIVE = os.environ.get(
    "CELERY_BEAT_SCHEDULE_ACTIVE", "false"
).lower() in {
    "1",
    "true",
}

TASK_DEADLINE_CHECK_MINUTES = os.environ.get("TASK_DEADLINE_CHECK_MINUTES", 7)
TASK_UPCOMING_DEADLINE_CHECK_DAYS = os.environ.get(
    "TASK_UPCOMING_DEADLINE_CHECK_DAYS", 3
)
AMQP_CONNECTION = os.environ.get("AMQP_CONNECTION", "")

CELERYBEAT_SCHEDULE = (
    {
        "check-user-activate": {
            "task": "users.tasks.periodic_check_user_activate",
            "schedule": crontab(hour="*/1"),
        },
        "collect-workflow-user-metrics": {
            "task": "users.tasks.update_all_task_user_metrics",
            "schedule": crontab(minute="*/5"),
        },
        "check-user-offboard": {
            "task": "users.tasks.periodic_check_user_offboard",
            "schedule": crontab(hour="*/1"),
        },
        "tasks-start-scheduled-tasks": {
            "task": "tasks.tasks.start_scheduled_tasks",
            "schedule": crontab(minute="*/1"),
        },
        "tasks-check_auto_assign_or_decline": {
            "task": "tasks.tasks.check_auto_assign_or_decline",
            "schedule": crontab(minute="*/1"),
        },
        "task-deadline-for-user-check": {
            "task": "users.tasks.notify_user_deadline",
            "schedule": crontab(minute=0, hour=9),
        },
        "task-deadline-missed-for-user-check": {
            "task": "users.tasks.notify_user_deadline_missed",
            "schedule": crontab(minute=f"*/{TASK_DEADLINE_CHECK_MINUTES}"),
        },
        "task-recurrence-end-report": {
            "task": "tasks.tasks.task_recurrence_end_check",
            "schedule": crontab(minute=0, hour=9, day_of_week=1),
        },
        "task-auto-delete-draft-tasks": {
            "task": "tasks.tasks.auto_delete_draft_tasks",
            "schedule": crontab(minute=0, hour=9),
        },
        "task-generate-periodic-task-log": {
            "task": "tasks.tasks.generate_periodic_task_log",
            "schedule": crontab(minute=0, hour=9, day_of_week=1),
        },
        "task-auto-expire-recurring-tasks": {
            "task": "tasks.tasks.auto_expire_recurring_tasks",
            "schedule": crontab(minute=0),
        },
        "task-remove-expired-tags": {
            "task": "users.tasks.remove_expired_tags",
            "schedule": crontab(minute="*/6"),
        },
        "daily-clean-cvs-after-90-days": {
            "task": "users.tasks.daily_clean_cvs_after_90_days",
            "schedule": crontab(minute=0, hour="8"),
        },
        "task-auto-transition-clients": {
            "task": "clients.tasks.auto_transition_clients",
            "schedule": crontab(minute=0, hour=0, day_of_week=1),
        },
        "cleanup-alert-silences": {
            "task": "core.tasks.cleanup_alert_silences",
            "schedule": crontab(minute=5, hour=0),
        },
        "clean-up-completed-alerts": {
            "task": "core.tasks.clean_up_completed_alerts",
            "schedule": crontab(minute=0, hour=0),
        },
        "client-profile-overview-elasticsearch-log": {
            "task": "clients.tasks.client_profile_overview_elasticsearch_log",
            "schedule": crontab(hour=9, day_of_week=6),
        },
    }
    if CELERY_BEAT_SCHEDULE_ACTIVE
    else {}
)
CELERY_IMPORTS = [
    "users.state_machine.user_default.background_actions",
    "users.state_machine.user_network.background_actions",
    "clients.state_machine.client_default.background_actions",
    "tasks.state_machine.task_default.background_actions",
    "core.state_machine.alert_default.background_actions",
    "tasks.notifications",
]

DEBUG_NOTIFICATIONS = ENVIRONMENT not in ("prod", "production") and os.environ.get(
    "DEBUG_NOTIFICATIONS"
) in ("true", "1")

NOTIFICATION_BASE_DOMAIN = os.environ.get("NOTIFICATION_BASE_DOMAIN", "")

NOTIFICATION_AGENCY_DOMAIN = os.environ.get("NOTIFICATION_AGENCY_DOMAIN", "")

NOTIFICATION_NETWORK_EMAIL = os.environ.get(
    "NOTIFICATION_NETWORK_EMAIL", "network@croud.com"
)
NOTIFICATION_HR_EMAIL = os.environ.get("NOTIFICATION_HR_EMAIL", "cchr@croud.com")

NOTIFICATION_TRAINING_EMAIL = os.environ.get(
    "NOTIFICATION_TRAINING_EMAIL", "training@croud.com"
)
NOTIFICATION_CAMPUS_EMAIL = os.environ.get(
    "NOTIFICATION_CAMPUS_EMAIL", "support@campus.croud.com"
)
NOTIFICATION_CLIENT_RECIPIENTS = os.environ.get("NOTIFICATION_CLIENT_RECIPIENTS", "")

NOTIFICATION_SUPPORT_EMAIL = os.environ.get(
    "NOTIFICATION_SUPPORT_EMAIL", "croudsupport@croud.com"
)
NOTIFICATION_ACCESS_EMAIL = os.environ.get(
    "NOTIFICATION_ACCESS_EMAIL", "access@croud.com"
)
NOTIFICATION_ACTIVATION_EMAIL = os.environ.get(
    "NOTIFICATION_ACTIVATION_EMAIL", "cc.activation@croud.com"
)
NOTIFICATION_CONTRACTS_EMAIL = os.environ.get(
    "NOTIFICATION_CONTRACTS_EMAIL", "contracts@croud.com"
)
AUTO_OFFBOARD_VERIFICATION_DAYS = os.environ.get("AUTO_OFFBOARD_VERIFICATION_DAYS", 60)
SIGNUP_AUTO_OFFBOARD_VERIFICATION_WEEKS = os.environ.get(
    "SIGNUP_AUTO_OFFBOARD_VERIFICATION_WEEKS", 6
)

LOCALE_SERVICE_CRN = os.environ.get("LOCALE_SERVICE_CRN", "")

CROUD_CAMPUS_DEFAULT_TAG_AGENCY = os.environ.get("CROUD_CAMPUS_DEFAULT_TAG_AGENCY")
CROUD_CAMPUS_DEFAULT_TAG_NETWORK = os.environ.get("CROUD_CAMPUS_DEFAULT_TAG_NETWORK")

PICKER_UPDATE_USER_METRICS = os.environ.get(
    "PICKER_UPDATE_USER_METRICS", "false"
).lower() in {
    "1",
    "true",
}

PICKER_UPDATE_USER_SCORES = os.environ.get(
    "PICKER_UPDATE_USER_SCORES", "false"
).lower() in {
    "1",
    "true",
}

PICKER_LOGGED_IN_RECENTLY_WEEKS = os.environ.get("PICKER_LOGGED_IN_RECENTLY_WEEKS", 12)
PICKER_HOURS_DUE_LIMIT_MINUTES = int(
    os.environ.get("PICKER_HOURS_DUE_LIMIT_MINUTES", 1200)
)

DISTRIBUTION_HOURS_STANDARD = int(os.environ.get("DISTRIBUTION_HOURS_STANDARD", "12"))
DISTRIBUTION_HOURS_FAST_TRACK = float(
    os.environ.get("DISTRIBUTION_HOURS_FAST_TRACK", "3")
)
DISTRIBUTION_HOURS_FAST_TRACK_THRESHOLD = float(
    os.environ.get("DISTRIBUTION_HOURS_FAST_TRACK_THRESHOLD", "24")
)
DISTRIBUTION_USER_ORDERING = os.environ.get("DISTRIBUTION_USER_ORDERING", "rate")

RECURRING_TASK_ALERT_LIMIT = os.environ.get("RECURRING_TASK_ALERT_LIMIT", "7 DAY")

TASK_CREDENTIALS_PROVISIONER_API_URL = os.environ.get(
    "TASK_CREDENTIALS_PROVISIONER_API_URL"
)

ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST")

ELASTICSEARCH_USERNAME = os.environ.get("ELASTICSEARCH_USERNAME")

ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD")

ELASTICSEARCH_DOC_TYPE = os.environ.get("ELASTICSEARCH_DOC_TYPE", "server_metric")

TAG_EXPIRATION_DAYS = json.loads(
    os.environ.get(
        "TAG_EXPIRATION_DAYS", '{"hourly_rate_change": 30, "new_network_user": 90}'
    )
)
INVOICING_API_URL = os.environ.get("INVOICING_API_URL")
FILE_API_URL = os.environ.get("FILE_API_URL")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
AUTH_APPEND_CLIENT_TOKEN = os.environ.get("AUTH_APPEND_CLIENT_TOKEN")
AUTH_CLIENT_ID = os.environ.get("AUTH_CLIENT_ID")
AUTH_CLIENT_SECRET = os.environ.get("AUTH_CLIENT_SECRET")
AUTH_TOKEN_ENDPOINT = os.environ.get("AUTH_TOKEN_ENDPOINT")

JOURNAL_SERVICE_URL = os.environ.get("JOURNAL_SERVICE_URL")
FEATURE_FLAGS = load_env_val(
    "FEATURE_FLAGS", default=dict(), validation=lambda x: isinstance(x, dict)
)
AGENCY_USER_CRN_PREFIX = "89e9001c-dda2-4938-8f3f-4285b360ac42:user-service:users:"
NETWORK_USER_CRN_PREFIX = (
    "72b48838-6d7c-4a56-8f7d-e179ba5ac58f:croudie-network:croudies:"
)

CRN_PREFIXES = {
    "agency": AGENCY_USER_CRN_PREFIX,
    "network": NETWORK_USER_CRN_PREFIX,
}

DEFAULT_CLIENT_CHANNEL = os.environ.get("DEFAULT_CLIENT_CHANNEL", "new_business")
DEFAULT_CLIENT_CHANNEL_ACCOUNT_ID = os.environ.get(
    "DEFAULT_CLIENT_CHANNEL_ACCOUNT_ID", "3025"
)
