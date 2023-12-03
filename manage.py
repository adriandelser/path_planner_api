#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.conf import settings
    from django.core.management import execute_from_command_line

    if settings.DEBUG:
        # If you are running in pycharm, debugpy will throw an import error, see exception.
        try:
            if os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN"):
                import debugpy

                debugpy.listen(("0.0.0.0", os.environ.get("DEBUG_PORT", 3000)))  # nosec
        except ImportError as e:
            # Error observed: cannot import name 'pydevd_defaults' from '_pydevd_bundle'
            # This will not prevent the debugger from working.
            print(f"[ Error ] connecting debugpy: {e}")
    execute_from_command_line(sys.argv)
