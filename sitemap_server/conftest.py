import pytest
from fastapi.testclient import TestClient

from server import app as a


@pytest.fixture()
def client():
    app = a

    with TestClient(app) as client_:
        yield client_
