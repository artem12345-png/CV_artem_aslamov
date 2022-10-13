import json
from functools import lru_cache
from typing import Callable
import pytest
import datetime
from fastapi.testclient import TestClient
from pymongo import MongoClient
from tests.api_reservation_mock import MockReservationClient
from tests.api_ya_queue_mock import MockYAQueueClient
from wb.models import FullInfo

LABELS_COLL_MOCK = "wb_fbs_requests_label_auto_test"
ACT_REQUEST_COLL_MOCK = "wb_fbs_requests_act_auto_test"
WAREHOUSES_COLL_MOCK = "epool_warehouses_auto_test"
# AUTH_COLL_MOCK = "wb_fbs_auth_auto_test"
WB_COLL_MOCK = "wb_auto_test"
MONGO_COLLECTIONS = [
    LABELS_COLL_MOCK,
    ACT_REQUEST_COLL_MOCK,
    WAREHOUSES_COLL_MOCK,
    # AUTH_COLL_MOCK,
    WB_COLL_MOCK,
]
datetime_now_mock = datetime.datetime.now(tz=datetime.timezone.utc)


def mock_get_c_username():
    return "test_user"


def get_client(mapping_dependencies: dict[Callable, Callable]):
    """
    :param mapping_dependencies: заменяет зависимости в FastAPI.
    :return: generator[TestClient]
    """
    from server_wb import init_app

    app = init_app(use_sentry=False)
    # Обходим авторизацию для тестов
    for k, v in mapping_dependencies.items():
        app.dependency_overrides[k] = v
    with TestClient(app) as client_:
        yield client_


async def send_s3_mock(*args, **kwargs):
    return "test_s3"


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
    db = MongoClient(SETTINGS.CONECT_MONGO).get_database("xway_wb")
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


ORDER = 12345
count_create = 0
count_idmonopolia = 0
count_update = 0
count_stickers = 0
create_request_template = {
    "_id": ORDER,
    "id_zakaz": ORDER,
    'idmonopolia': 111,
    "goods": [
        {
            "idgood": 51844,
            "amount": 1,
            "name": "Лестницы для бассейнов",
            "price": "8900.0000000000"
        }
    ],
    "date": datetime_now_mock,
    "date_delivery": datetime_now_mock,
    "delivery_method": "SELLER_SEND_GOODS",
    "status": "awaiting_packaging"
}
create_request = None


async def get_full_info_mock(posting_number):
    from tests.info_mock import info_mock
    return FullInfo(**info_mock)


async def mock_epool_request(*args, **kwargs):
    global create_request, count_create, count_idmonopolia, count_update, count_stickers

    body = args[0]
    goods = body.get('goods', None)
    if goods:
        count_create += 1
        create_request = body
        return MockResponse({"id": ORDER})
    else:
        return MockResponse({"id": ORDER})


@pytest.fixture()
def mock_dependencies(mocker):
    mocker.patch("wb.labels.send_then_delete_file", send_s3_mock)
    mocker.patch("ya_queue.YAQueueClient", MockYAQueueClient)
    mocker.patch("api_reservation.ReservationClient", MockReservationClient)
    mocker.patch("wb.tools.get_queue_client", get_mock_queue_client)
    mocker.patch("wb.tools.get_reservation_client", get_mock_reservation_client)
    mocker.patch("wb.create_order.epool_request", mock_epool_request)
    mocker.patch("wb.consts.WB_COLL", WB_COLL_MOCK)
    # mocker.patch("wb.consts.AUTH_COLL", AUTH_COLL_MOCK)
    mocker.patch("wb.consts.LABEL_REQUESTS_COLL", LABELS_COLL_MOCK)


@pytest.fixture()
def client(mock_dependencies):
    from server_wb import get_current_username

    yield from get_client({get_current_username: mock_get_c_username})
