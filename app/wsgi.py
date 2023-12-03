"""
WSGI config

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/

isort:skip_file
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402
from dj_static import Cling  # noqa: E402

application = Cling(get_wsgi_application())
