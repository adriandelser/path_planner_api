import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


def test_user_endpoint(db, api_client):
    # ARRANGE
    user = baker.make(User)
    # ACT
    resp = api_client.get(f"/users/{user.pk}")
    # ASSERT
    assert resp.status_code == status.HTTP_200_OK
