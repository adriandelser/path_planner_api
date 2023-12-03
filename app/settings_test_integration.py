"""
isort:skip_file
"""

from .settings_test import *  # noqa

os.environ["ENVIRONMENT"] = "integration"  # noqa
os.environ["AUTHZ_ACTIVE"] = "true"  # noqa


DATABASES["default"] = {  # noqa
    "ENGINE": "django.db.backends.postgresql_psycopg2",  # noqa
    "HOST": os.environ.get("POSTGRES_HOST"),  # noqa
    "NAME": os.environ.get("POSTGRES_DB"),  # noqa
    "USER": os.environ.get("POSTGRES_USER"),  # noqa
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),  # noqa
    "TEST": {
        "NAME": "int_v3_platform",
    },
}
