import json
from functools import lru_cache
from typing import Callable

import motor.motor_asyncio as aiomotor
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pytest_mock import MockFixture

from test.api_ozon_mock import MockOzonAPI
from test.api_reservation_mock import MockReservationClient
from test.api_ya_queue_mock import MockYAQueueClient

LABELS_COLL_MOCK = "xway_fbs_requests_label_auto_test"
ACT_REQUEST_COLL_MOCK = "xway_fbs_requests_act_auto_test"
WAREHOUSES_COLL_MOCK = "epool_warehouses_auto_test"
AUTH_COLL_MOCK = "xway_fbs_auth_auto_test"
OZON_COLL_MOCK = "ozon_auto_test"
MONGO_COLLECTIONS = [
    LABELS_COLL_MOCK,
    ACT_REQUEST_COLL_MOCK,
    WAREHOUSES_COLL_MOCK,
    AUTH_COLL_MOCK,
    OZON_COLL_MOCK,
]


def mock_get_c_username():
    return "test_user"


def get_client(mapping_dependencies: dict[Callable, Callable]):
    """
    :param mapping_dependencies: заменяет зависимости в FastAPI.
    :return: generator[TestClient]
    """
    from server import init_app

    app = init_app(use_sentry=False)
    # Обходим авторизацию для тестов
    for k, v in mapping_dependencies.items():
        app.dependency_overrides[k] = v
    with TestClient(app) as client_:
        yield client_


async def send_s3_mock(*args, **kwargs):
    return "test_s3"


@lru_cache(maxsize=1)
def get_mock_ozon_api():
    return MockOzonAPI("", "", url="")


@lru_cache(maxsize=1)
def get_mock_reservation_client():
    return MockReservationClient("", "")


@lru_cache(maxsize=1)
def get_mock_queue_client():
    return MockYAQueueClient("", "")


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    clear_mongo()


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    clear_mongo()


def clear_mongo():
    from env import SETTINGS

    assert (
        "192.168.0.78" in SETTINGS.CONECT_MONGO
    ), "Должна быть тестовая монга для тестов"
    db = MongoClient(SETTINGS.CONECT_MONGO).get_database("xway")
    for collection_name in MONGO_COLLECTIONS:
        coll = db.get_collection(collection_name)
        assert (
            "_auto_test" in collection_name
        ), "Коллекция должна содержать постфикс _auto_test"
        coll.drop()


class MockResponse:
    def __init__(self, j: dict):
        self._dict = j
        self.content = json.dumps(j)

    def json(self):
        return self._dict


count_create = 0
count_idmonopolia = 0
count_update = 0
count_stickers = 0
create_request_template = {
    "act": "create_from_market",
    "date_delivery": "2022-06-22 10:00",
    "delivery_method": "Ozon Логистика курьеру, Реутов",
    "uidsource": "89723295-0005-1",
    "goods": [
        {
            "idgood": 51462,
            "amount": 1,
            "name": "Фильтр-насос Bestway 58381/58145, производительность 1.2 куб.м/ч",
            "price": "2890.000000",
        }
    ],
    "source": "ozon",
    "is_oversized": False,
}
create_request = None


async def mock_epool_request(*args, **kwargs):
    global create_request, count_create, count_idmonopolia, count_update, count_stickers

    body = args[0]
    act = body["act"]
    if act == "status_market":
        count_update += 1
        return MockResponse({"result": "Status is changed"})
    if act == "create_from_market":
        count_create += 1
        create_request = body
        return MockResponse({"id": 2178152})
    if act == "param_market":
        if body.get("idmonopolia"):
            count_idmonopolia += 1
            return MockResponse({"result": "idmonopolia is changed"})
        if body.get("date_delivery"):
            return MockResponse({"result": "date_delivery is changed"})
    if act == "stickers_after":
        count_stickers += 1
        return MockResponse({"result": "ok"})


@pytest.fixture()
def mock_dependencies(mocker):
    mocker.patch("ozon.labels_utils.send_then_delete_file", send_s3_mock)
    mocker.patch("ya_queue.YAQueueClient", MockYAQueueClient)
    mocker.patch("api_reservation.ReservationClient", MockReservationClient)
    mocker.patch("api_ozon.OzonAPI", MockOzonAPI)
    mocker.patch("ozon.tools.get_ozon_api", get_mock_ozon_api)
    mocker.patch("ozon.tools.get_queue_client", get_mock_queue_client)
    mocker.patch("ozon.tools.get_reservation_client", get_mock_reservation_client)
    mocker.patch("ozon.create_order.epool_request", mock_epool_request)
    mocker.patch("ozon.consts.OZON_COLL", OZON_COLL_MOCK)
    mocker.patch("ozon.consts.AUTH_COLL", AUTH_COLL_MOCK)
    mocker.patch("ozon.consts.EPOOL_WAREHOUSES_COLL", WAREHOUSES_COLL_MOCK)
    mocker.patch("ozon.consts.REQUESTS_ACT_COLL", ACT_REQUEST_COLL_MOCK)
    mocker.patch("ozon.consts.LABEL_REQUESTS_COLL", LABELS_COLL_MOCK)
    mocker.patch("ozon.consts.TRACE_LABELS_WAIT_SECONDS", 100000)
    mocker.patch("ozon.consts.CREATING_QUEUE_WAIT_SECONDS", 100000)


@pytest.fixture()
def client(mock_dependencies):
    from server import get_current_username

    yield from get_client({get_current_username: mock_get_c_username})
