import logging
import shutil
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock, Mock

from django.apps import apps
from django.contrib.auth.models import Group, Permission, User
from django.db import connections, models
from django.db.models import Model
from django.test.utils import CaptureQueriesContext

import pytest
from model_bakery import baker
from model_utils import FieldTracker

from ..cache import get_content_type_for_model
from ..fields import SetChoiceField
from ..models_utils import ParentModel, UpdatableMixin
from ..wrappers import ProtectFields

logger = logging.getLogger(__name__)

# Constants for the source and destination paths
TEST_MIGRATIONS_PATH = Path(__file__).parent / "test_migrations"
MIGRATIONS_PATH = Path(__file__).parent.parent / "migrations"


class ExtendedCaptureQueriesContext(CaptureQueriesContext):
    def __init__(self, connection):
        super().__init__(connection)
        self.start_time = None
        self.final_queries_time = None
        self.query_stats = defaultdict(lambda: {"count": 0, "total_time": 0.0})
        self.total_sql_time = 0

    def __enter__(self):
        self.start_time = time.time()
        return super().__enter__()

    def __exit__(self, *args, **kwargs):
        super().__exit__(*args, **kwargs)
        self.final_queries_time = time.time() - self.start_time
        self._accumulate_query_stats()

    def _accumulate_query_stats(self):
        total_sql_time = 0
        for query in self.captured_queries:
            self.query_stats[query["sql"]]["count"] += 1
            self.query_stats[query["sql"]]["total_time"] += float(query["time"])
            total_sql_time += float(query["time"])
        self.total_sql_time = total_sql_time

    def print_detailed_queries(self, sort_by="count"):
        if sort_by not in ["count", "total_time"]:
            raise ValueError("sort_by must be either 'count' or 'total_time'")
        for query, stats in sorted(
            self.query_stats.items(), key=lambda item: item[1][sort_by], reverse=True
        ):
            print(
                f"Query: {query}\n Count: {stats['count']}\n Total time: "
                f"{stats['total_time']}s\n"
            )
        print(
            f"TOTAL SQL QUERYIES & EXEC TIME: [{len(self.captured_queries)} {self.total_sql_time} ]"
        )

    def check_and_print(self, time_threshold, query_threshold):
        msgs = []
        if len(self.captured_queries) > query_threshold:
            msgs.append(
                f"Too many queries: {len(self.captured_queries)} expected le: {query_threshold}"
            )
        if self.total_sql_time > time_threshold:
            msgs.append(f"Queries took too long: {self.final_queries_time}")
        print("PRINTING ---------------\n ")
        self.print_detailed_queries(sort_by="total_time")
        print("DONE ------------\n")
        if len(msgs) > 0:
            assert False, msgs


def pytest_configure(config):
    shutil.copytree(TEST_MIGRATIONS_PATH, MIGRATIONS_PATH, dirs_exist_ok=True)


# def pytest_unconfigure(config):


@pytest.fixture
def authz(settings):
    settings.AUTHZ_ACTIVE = True


@pytest.fixture(scope="session")
def test_model_choices_class():
    class Choices(models.TextChoices):
        OPTION_1 = "option1"
        OPTION_2 = "option2"
        OPTION_3 = "option3"

    return Choices


@pytest.fixture(scope="session")
def test_model_class(test_model_choices_class, django_db_blocker):
    class TestModel(ParentModel, UpdatableMixin, models.Model):
        field1 = models.CharField(max_length=100, default="", blank=True)
        field2 = models.CharField(max_length=100, default="", blank=True)
        protected_field = models.CharField(max_length=100, default="", null=True)
        tracker = FieldTracker()
        choice_field = SetChoiceField(
            choices_class=test_model_choices_class, default=set, null=True
        )

        def save(self, *args, **kwargs):
            if self.parent_id is None:
                self.path = str(self.id)
            else:
                parent = TestModel.objects.get(id=self.parent_id)
                self.path = parent.path + "." + str(self.id)

            super().save(*args, **kwargs)

        def update_descendants_path(self):
            descendants = TestModel.objects.filter(path__descendants=self.path)
            for descendant in descendants:
                descendant.path = self.path + "." + str(descendant.id)
                descendant.save()

    with django_db_blocker.unblock():
        model_name = "TestModel"
        app_config = apps.get_app_config("django_extras")
        TestModel._meta.app_label = "django_extras"
        TestModel._meta.model_name = model_name.lower()
        app_config.models[TestModel._meta.model_name] = TestModel

    @ProtectFields(sender=TestModel, fields=["protected_field"])
    def protect_test_model_fields(instance, **kwargs):
        pass

    yield TestModel


@pytest.fixture
def api_client_authenticated(authz, api_client, user):
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture
def add_perms_to_user() -> (
    Callable[[User, List[Model], List[Group], List[Permission]], None]
):
    def add_perms(
        user,
        models: List[Model] = None,
        groups: List[str] = None,
        permissions: List[str] = None,
    ):
        models = models or []
        groups = groups or []
        permissions = permissions or []
        content_type = [get_content_type_for_model(model) for model in models]
        perms = Permission.objects.filter(content_type__in=content_type)
        user.user_permissions.set(perms)
        for group in groups:
            fte_core, _ = Group.objects.get_or_create(name=group)
            user.groups.add(fte_core)
        for permission in permissions:
            # Get or create the permission
            permission_obj, _ = Permission.objects.get_or_create(
                content_type=get_content_type_for_model(user.__class__),
                codename=permission,
            )
            # Add the permission to the user
            user.user_permissions.add(permission_obj)

    return add_perms


@pytest.fixture
def db_threshold_factory(db, settings):
    class _runner:
        def __init__(self, env_name, time_threshold, query_threshold):
            self.env_name = env_name
            self.time_threshold = time_threshold
            self.query_threshold = query_threshold

        def __enter__(self):
            db_context = "default"
            self.context = ExtendedCaptureQueriesContext(connections[db_context])
            self.context.__enter__()

        def __exit__(self, *args, **kwargs):
            self.context.__exit__(*args, **kwargs)
            self.context.check_and_print(self.time_threshold, self.query_threshold)

    return _runner


@pytest.fixture
def db_localhost_t2_q5(db_threshold_factory):
    return db_threshold_factory("localhost", 0.2, 5)


@pytest.fixture(scope="session")
def factory_seed_graph_data_for_model(django_db_blocker, django_db_setup):
    def _seed(model_cls):
        with django_db_blocker.unblock():
            # Create a root instance
            root = baker.make(model_cls)

            # Create some tree
            for i in range(1, 4):
                parent = root
                for j in range(1, 4):
                    node = baker.make(model_cls, parent=parent)
                    parent = node
            root.refresh_from_db()
        # Return the root node for access in tests
        return root

    return _seed


@pytest.fixture
def mock_request():
    mock_request = Mock()

    class QueryDict(dict):
        def dict(self):
            return self.copy()

    mock_request.query_params = QueryDict()
    mock_request.user = MagicMock()
    mock_request.path = ""
    return mock_request


@pytest.fixture(scope="session")
def s_ff_test_flag_pk():
    return "_test_flag"


@pytest.fixture
def f_ff_test_flag_set_true(settings, s_ff_test_flag_pk):
    settings.FEATURE_FLAGS[s_ff_test_flag_pk] = True


@pytest.fixture
def f_ff_test_flag_set_false(settings, s_ff_test_flag_pk):
    settings.FEATURE_FLAGS[s_ff_test_flag_pk] = False


@pytest.fixture(scope="session")
def f_ff_cp_4164_croudie_statuses_pk():
    return "cp_4164_croudie_statuses"


@pytest.fixture
def f_ff_cp_4164_croudie_statuses_set_true(settings, f_ff_cp_4164_croudie_statuses_pk):
    settings.FEATURE_FLAGS[f_ff_cp_4164_croudie_statuses_pk] = True


@pytest.fixture(scope="session")
def mock_uuid():
    return uuid.uuid4()
