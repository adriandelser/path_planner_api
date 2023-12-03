from io import StringIO

from django.core.management import call_command

import pytest


@pytest.mark.django_db
def test_for_missing_migrations():
    output = StringIO()
    apps = [ "accounts"]
    try:
        call_command(
            "makemigrations",
            *apps,
            interactive=False,
            dry_run=True,
            check=True,
            stdout=output
        )
    except SystemExit:
        pytest.fail("There are missing migrations:\n %s" % output.getvalue())


@pytest.mark.django_db
def test_django_checks():
    try:
        call_command("check", fail_level="WARNING")
    except SystemExit:
        pytest.fail("Django system checks falied")
