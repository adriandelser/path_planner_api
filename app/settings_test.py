"""
isort:skip_file
"""

import datetime
import os

import jwt

os.environ["ENVIRONMENT"] = "dev"
os.environ["AUTH_ACTIVE"] = "false"
os.environ["SNS_TOPIC_MAP"] = (
    '{"test-topic": {"topic": "ARN"},'
    ' "user-creation": {"topic": "user-creation-ARN"},'
    ' "user-deletion": {"topic": "user-deletion-ARN"},'
    ' "user-anonymisation": {"topic": "user-deletion-ARN"},'
    ' "croudie-save": {"topic": "ARN"}}'
)
os.environ["SQS_QUEUES"] = '{"test": "test"}'
os.environ["AUTHZ_ACTIVE"] = "false"

for var in [
    "SECRET_KEY",
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_USER_POOL",
    "AWS_CLIENT_ID",
    "AWS_BUCKET_PUBLIC",
    "LOCALE_SERVICE_CRN",
    "NOTIFICATION_CLIENT_RECIPIENTS",
]:
    os.environ[var] = "dummy"

from .settings import *  # noqa

SERVICE_NAME = "test-service"
SCANNING_ACTIVE = False
SHOW_SWAGGER_DOCS = True
PICKER_UPDATE_USER_METRICS = True
PICKER_UPDATE_USER_SCORES = True
PROFILE_REQUESTS = False
NOTIFICATION_BASE_DOMAIN = "example.com"
NOTIFICATION_AGENCY_DOMAIN = "example.com"
TASK_DEADLINE_CHECK_MINUTES = 7
TASK_UPCOMING_DEADLINE_CHECK_DAYS = 3

TASK_CREDENTIALS_PROVISIONER_API_URL = "example.com/provisions"

AMQP_CONNECTION = "amqp://dummy"
os.environ.pop("BROKER_URL", None)

INVOICING_API_URL = "example.com"

FILE_API_URL = "https://example.com/files"
os.environ["ACCESS_TOKEN"] = jwt.encode(
    {"exp": datetime.datetime.now()}, "secret", algorithm="HS256"
)
os.environ["AUTH_APPEND_CLIENT_TOKEN"] = "1"  # nosec
os.environ["AUTH_CLIENT_ID"] = "test"  # nosec
os.environ["AUTH_CLIENT_SECRET"] = "test"  # nosec
os.environ["AUTH_TOKEN_ENDPOINT"] = "https://example.com/oauth/token"  # nosec

JOURNAL_SERVICE_URL = "https://journalsapi.test.example.com"
FEATURE_FLAGS = load_env_val(  # noqa
    "FEATURE_FLAGS",
    default={
        "rate_change_snapshot_flag": True,
        "enable_task_alerts_flag": True,
        "cp_4164_croudie_statuses": True,
        "cp_4828_onboarding_progress_flag": True,
    },
)
