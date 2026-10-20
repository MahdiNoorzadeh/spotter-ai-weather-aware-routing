
from typing import cast

import pytest
from django.http import HttpResponse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_returns_ok():
    response = cast(HttpResponse, APIClient().get("/api/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
