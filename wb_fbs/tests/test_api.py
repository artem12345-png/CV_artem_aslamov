import datetime

import pymongo
import pytest
from wb.models import BasicModel
from conftest import ORDER
from tests.conftest import (
    WB_COLL_MOCK,
    LABELS_COLL_MOCK,
    send_s3_mock,
    mock_epool_request,
    get_full_info_mock,
)


@pytest.mark.asyncio
async def test_pro_smoke(mock_dependencies):
    from wb.tools import init_dbs, disconnect_dbs

    try:
        await init_dbs()
    finally:
        await disconnect_dbs()


async def check_goods_mock(x, y):
    return True


async def confirm_mock(x):
    pass


async def create_reserve_mock(x, y, z):
    return 111


def delivery_for_warehouse_mock(x):
    return x


@pytest.mark.asyncio
async def test_base_scenario(mocker, mock_dependencies):
    mocker.patch("wb.create_order.WB_COLL", WB_COLL_MOCK)
    mocker.patch("server_wb.LABEL_REQUESTS_COLL", LABELS_COLL_MOCK)
    mocker.patch("wb.labels.send_then_delete_file", send_s3_mock)
    mocker.patch("wb.create_order.epool_request", mock_epool_request)
    mocker.patch("server_wb.epool_request", mock_epool_request)
    mocker.patch("wb.create_order.get_full_info", get_full_info_mock)
    mocker.patch("wb.create_order.check_goods", check_goods_mock)
    mocker.patch("wb.create_order.confirm", confirm_mock)
    mocker.patch("wb.create_order.create_reserve", create_reserve_mock)

    from wb.consts import QUEUE_DATE_FORMAT
    from wb.create_order import create_order
    from wb.tools import init_dbs, disconnect_dbs
    from server_wb import trace_label, trace_it
    from env import SETTINGS

    WB_COLL = WB_COLL_MOCK

    await init_dbs()
    try:
        order = BasicModel(order_id=str(ORDER))
        await create_order(order)
        await trace_label()
        mongo_client = pymongo.MongoClient(SETTINGS.CONECT_MONGO).get_database("xway_wb")
        row = mongo_client.get_collection(WB_COLL).find_one(
            {"_id": ORDER}
        )
        assert row

        await mock_epool_request(row)
        from tests.conftest import count_create, create_request, create_request_template
        create_request['date'] = create_request['date'].date()
        create_request['date_delivery'] = create_request['date_delivery'].date() - datetime.timedelta(days=1)
        create_request_template['date'] = create_request_template['date'].date()
        create_request_template['date_delivery'] = create_request_template['date_delivery'].date()
        assert (
                create_request == create_request_template
        ), "Неверно передаются параметры в epool_request"
        assert (
                count_create == 2
        ), f"Заявка была создана {count_create} раз, хотя должна была создаться один раз"

        print(row)

        await trace_it(
            {
                "_id": row["idmonopolia"],
                "id_zakaz": row["id_zakaz"],
                "posting_number": row["_id"],
                "goods": row["goods"],
                "date_delivery": row["date_delivery"].strftime(QUEUE_DATE_FORMAT),
            },
            "1",
            "",
        )

    finally:
        await disconnect_dbs()
