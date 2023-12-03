import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient



@pytest.fixture
def api_client():
    return APIClient()
def test_user_endpoint(db,api_client):
    from accounts.models.user import User
    user=baker.make(User)
    resp=api_client.get(f'/users/{user.pk}')
    assert resp.status_code==status.HTTP_200_OK