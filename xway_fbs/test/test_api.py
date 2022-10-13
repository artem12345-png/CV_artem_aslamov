import httpx
import pymongo
import pytest

from test.conftest import (
    OZON_COLL_MOCK,
    get_mock_ozon_api,
    LABELS_COLL_MOCK,
    send_s3_mock,
    mock_epool_request,
)


@pytest.mark.asyncio
async def test_update_warehouses(mock_dependencies):
    from scripts.update_warehouses import main as update_warehouses
    from ozon.tools import init_dbs, disconnect_dbs

    await init_dbs()
    try:
        await update_warehouses()
    finally:
        await disconnect_dbs()


@pytest.mark.asyncio
async def test_base_scenario(mocker, mock_dependencies):
    mocker.patch("ozon.create_order.OZON_COLL", OZON_COLL_MOCK)
    mocker.patch("ozon.endpoints.OZON_COLL", OZON_COLL_MOCK)
    mocker.patch("server.LABEL_REQUESTS_COLL", LABELS_COLL_MOCK)
    mocker.patch("ozon.xway_requests.get_ozon_api", get_mock_ozon_api)
    mocker.patch("ozon.labels_utils.send_then_delete_file", send_s3_mock)
    mocker.patch("ozon.create_order.epool_request", mock_epool_request)
    mocker.patch("ozon.endpoints.epool_request", mock_epool_request)
    mocker.patch("scripts.update_statuses.epool_request", mock_epool_request)
    mocker.patch("server.epool_request", mock_epool_request)

    from ozon.tools import init_dbs, disconnect_dbs
    from server import create_from_queue, trace_it
    from scripts.get_new_orders import main as get_new_orders
    from env import SETTINGS
    from api_ozon.models import OzonStatuses
    from ozon.consts import QUEUE_DATE_FORMAT

    OZON_COLL = OZON_COLL_MOCK

    await init_dbs()
    try:
        await get_new_orders()
        await create_from_queue()
        mongo_client = pymongo.MongoClient(SETTINGS.CONECT_MONGO).get_database("xway")
        row = mongo_client.get_collection(OZON_COLL).find_one(
            {"_id": "89723295-0005-1"}
        )
        assert row
        assert row["status"] == OzonStatuses.awaiting_deliver.value
        from test.conftest import count_create, create_request, create_request_template

        assert (
            create_request == create_request_template
        ), "Неверно передаются параметры в epool_request"
        assert (
            count_create == 1
        ), f"Заявка была создана {count_create} раз, хотя должна была создаться один раз"

        from scripts.update_statuses import main as update_statuses

        await update_statuses()
        from test.conftest import count_update

        assert count_update == 2, "Статус заявки должен был обновиться 2 раза"
        row = mongo_client.get_collection(OZON_COLL).find_one(
            {"_id": "89723295-0005-1"}
        )

        assert row["status"] == OzonStatuses.delivering.value
        async with httpx.AsyncClient() as client:
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
                client,
            )
        from test.conftest import count_stickers

        assert count_stickers == 1, "Наклейка должна быть передана в админку"

        label_row = mongo_client.get_collection(LABELS_COLL_MOCK).find_one(
            {"_id": row["id_zakaz"]}
        )

        assert label_row, "В базу не сохранена информация о скаченной наклейке"
    finally:
        await disconnect_dbs()
