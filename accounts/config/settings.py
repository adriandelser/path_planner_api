import os

from django.conf import settings

# from django_extras import ClassRef

app_name = ""


# serializers
prepend_serializer = f"{app_name}.serializers."
prepend_serializer_nested = f"{app_name}.serializers_nested."
# Services

# Constants
PICKER_TIMED_OUT_INTERVAL = os.environ.get("PICKER_TIMED_OUT_INTERVAL", "3 months")
PICKER_GIVEN_WORK_INTERVAL = os.environ.get("PICKER_GIVEN_WORK_INTERVAL", "1 month")
PICKER_RECENT_USAGE_INTERVAL = os.environ.get(
    "PICKER_RECENT_USAGE_INTERVAL", "3 months"
)
PICKER_RESPONSE_TIME_INTERVAL = os.environ.get(
    "PICKER_RESPONSE_TIME_INTERVAL", "3 months"
)
DOMAIN_NAME_REGEX = (
    r"^(?!:\/\/)([a-zA-Z0-9-_])*[a-zA-Z0-9][a-zA-Z0-9-_.]+\.[a-zA-Z]{2,11}?$"
)
