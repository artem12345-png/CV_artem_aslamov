import pytest
from fastapi.testclient import TestClient

from server import init_app


@pytest.fixture()
def client():
    app = init_app(use_sentry=False)

    with TestClient(app) as client_:
        yield client_
