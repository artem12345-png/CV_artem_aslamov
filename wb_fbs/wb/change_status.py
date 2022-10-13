import httpx

from wb.consts import WB_COLL, STATUS2STANDARD
from wb.create_order import epool_request
from wb.models import BasicModel
from wb.tools import find_mongo, get_reservation_client, update_mongo
from wb.tools import logger


async def update_status(order):
    logger.info(f"Обновляем статус {order['order_id']} на {order['order_status']}")
    mongo_data = await find_mongo(WB_COLL, int(order['order_id']))
    if order['xway_status'] is None:
        # если в данной записи нет xway_status, то нас это не интересует
        return

    current_status = STATUS2STANDARD[order['xway_status']]
    if current_status == "cancelled":
        try:
            r_c = get_reservation_client()
            async with httpx.AsyncClient() as client:
                await r_c.clear_reserve(client, idmonopolia=mongo_data["idmonopolia"])
        except Exception as e:
            logger.exception(f"При отмене заказа не удалось отменить резерв: {e}")

    previous_status = mongo_data["status"]
    if current_status != previous_status:
        body = {
            "act": "status_market",
            "id": mongo_data["id_zakaz"],
            "status": current_status,
        }

        await update_mongo(
            WB_COLL, int(order['order_id']), {"$set": {"status": current_status}}
        )
        _ = await epool_request(body)
