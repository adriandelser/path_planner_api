from rest_framework.test import APIClient


def test_swagger(db):
    client = APIClient()

    response = client.get("/swagger/")
    assert response.status_code == 200
