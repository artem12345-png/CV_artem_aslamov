import datetime
import json

import httpx

from api_reservation.consts import ReservationClientCreate
from env import SETTINGS, METHOD
from wb.consts import WB_COLL, PLACEMARKET, QUEUE_DATE_FORMAT, STATUS2STANDARD
from wb.models import BasicModel, FullInfo, Equip
from wb.tools import (
    write_to_mongo,
    logger,
    delete_none,
    extract_datetime,
    get_mongo_coll,
    get_reservation_client,
    weight_calc,
    get_queue_client, update_mongo,
)
from wb.xway_request import xway_request, RequestType


async def create_reserve(client_httpx, id_zakaz, note: str) -> int:
    client = get_reservation_client()
    idmonopolia = await client.create_reserve(
        client_httpx, id_zakaz, ReservationClientCreate.wildberries, note=note
    )

    return idmonopolia


async def get_full_info(posting_number):
    # https://wiki.xway.ru/docs/metod-dlja-poluchenija-informacii-po-zak-3/
    res = await xway_request(
        method=RequestType.get, api_method=f"/api/v1/orders/get/{posting_number}?key=order_id"
    )
    if res.status_code != 200:
        raise Exception(
            f"Не удалось получить полную информацию по заказу {posting_number}"
        )
    else:
        return FullInfo(**res.json())


async def check_goods(goods, posting_number) -> bool:
    """
    goods = [
        {
            "idgood": int(i.offer_id),
            "amount": i.product_count,
            "name": i.name,
            "price": i.product_unit_price_amount,
        }
        for i in items
    ]
    """
    # Проверяем остатки каждого товара на складе
    idgoods = [i["idgood"] for i in goods]
    async with httpx.AsyncClient() as client:
        url = SETTINGS.RESERVATION_URL + "/reservation/remainder"
        response = await client.post(url=url, json=idgoods)
        logger.info(
            f"POST {response.status_code} {url} json={idgoods} response={response.json()}"
        )
        if response.status_code != 200:
            raise Exception(
                f"Не удалось запросить остатки, номер отправления order_id={posting_number}"
            )
        remains = response.json()
        for item in goods:
            idgood, amount = item["idgood"], item["amount"]
            if remains[str(idgood)] < amount:
                logger.info(
                    f"Отказываемся от заказа order_id={posting_number},"
                    f" тк имеющегося товара меньше {remains[idgood]}, необходимого {amount}"
                )
                return False

    return True


async def equip(order: Equip, id_zakaz):
    response = await xway_request(
        method=RequestType.post, api_method="/api/v1/orders/equip/", body=order.dict()
    )
    if response.status_code == 200:
        if id_zakaz:  # если заказ создан, то надо сменить его остатус
            body = {
                "act": "status_market",
                "id": id_zakaz,
                "status": "awaiting_deliver",
            }
            _ = await epool_request(body)
            await update_mongo(
                WB_COLL, int(order.posting_number), {"$set": {"status": "awaiting_deliver"}}
            )
        return True
    else:
        raise Exception(
            f"Не получилось обратиться к методу equip, order_id={order.posting_number}"
        )


async def cancel(order: BasicModel):
    canceled_order = Equip(
        shipmentId=int(order.order_id),
        weight=1,
        width=1,
        height=1,
        depth=1,
        items=[{"quantity": "0", "sku": str(item.item_offer).replace('*','')} for item in order.order_items],
    )
    if await equip(canceled_order, None):
        logger.info(f"Отменили заказ успешно order_id={order.order_id}")
    else:
        logger.exception(f"Не смогли отменить заказ order_id={order.order_id}")


async def confirm(order_id: int):
    # https://wiki.xway.ru/docs/podtverzhdenija-zakaza/
    response = await xway_request(
        method=RequestType.patch,
        api_method=f"/api/v1/orders/confirm/{order_id}",
    )
    response = response.json()
    if not response.get('success'):
        raise Exception(f"Не удалось подтвердить заказ order_id={order_id}")


async def create_order(order: BasicModel):
    posting_number = order.order_id
    assert len(str(posting_number)) < 11, f"Это сломанный заказ {posting_number}"
    full_info = await get_full_info(posting_number)
    items = full_info.order_items
    goods = [
        {
            "idgood": int(i.offer_id),
            "amount": i.product_count,
            "name": i.name,
            "price": i.product_unit_price_amount,
        }
        for i in items
    ]

    shipment_date = full_info.shipment_date
    is_have_enough = False
    try:
        is_have_enough = await check_goods(goods, order.order_id)
        logger.info(f"Проверка остатков завершилась: {is_have_enough} order_id={order.order_id}")
    except Exception as e:
        logger.warning(f"Проверка остатков order_id={order.order_id} завершилась с ошибкой: {e}")

    if is_have_enough:
        await confirm(int(order.order_id))
        _ = await create_order_logic(
            shipment_date, goods, full_info, posting_number
        )
    else:
        await cancel(order)
        raise Exception("Товара не хватает на складе, заказ отменён.")


def get_date_delivery_for_warehouse(date_creation: datetime.datetime) -> datetime.datetime:
    """
    Возвращает день, в который складу необходимо передать посылку на склад МП.
    Требования: скайп Евгений 13 августа 13:05 Интеграция с WB OZON и Yandex Market.
    :param date_creation: дата создания заказа (datetime в таймзоне UTC)
    :return: datetime.date
    """
    assert date_creation.tzinfo == datetime.timezone.utc, "Указана неверная таймзона"
    days = 1

    return (date_creation + datetime.timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)


async def create_order_logic(shipment_date, goods, full_info, posting_number):
    date, datetime_ = extract_datetime(shipment_date)
    datetime_now = datetime.datetime.now(tz=datetime.timezone.utc)
    business_date_delivery = get_date_delivery_for_warehouse(datetime_now)

    request_wc = {
        "act": METHOD,
        "date_delivery": business_date_delivery.replace(hour=13).strftime("%Y-%m-%d %H:%M"),
        "delivery_method": full_info.order_items[0].send_goods_operator,
        "uidsource": posting_number,
        "goods": goods,
        "source": PLACEMARKET,
    }
    res = await epool_request(request_wc)
    id_zakaz = res.json().get("id")
    await write_to_mongo(
        coll_name=WB_COLL,
        data={
            "_id": int(posting_number),
            "id_zakaz": int(id_zakaz),
            "goods": goods,
            "date": datetime_now,
            "date_delivery": business_date_delivery,
            "delivery_method": full_info.order_items[0].send_goods_operator,
            "status": STATUS2STANDARD[full_info.xway_status],
        },
    )
    _ = await epool_request(
        {
            "act": "status_market",
            "id": int(id_zakaz),
            "status": STATUS2STANDARD[full_info.xway_status],
        }
    )

    message = {
        "id_zakaz": id_zakaz,
        "posting_number": full_info.order_id,
        "goods": goods,
        "date_delivery": datetime_.strftime(QUEUE_DATE_FORMAT),
    }
    await actions_after_create(id_zakaz, full_info, message)

    return id_zakaz


async def actions_after_create(id_zakaz, info: FullInfo, message):
    posting = info
    _, _datetime = extract_datetime(posting.shipment_date)
    note = " // ".join(
        [
            _datetime.strftime("%d.%m.%Y %H:%M"),
            f"Номер заказа на WB: {posting.order_id}",
            "Адрес склада: МКАД, 19-й километр, вл20с1",
            "Ограничения: до 5 паллет, в рамках установленного лимита",
            posting.order_items[0].send_goods_operator,
        ]
    )
    try:
        idmon = await get_mongo_coll(WB_COLL).find_one({"id_zakaz": id_zakaz})
        if idmon.get("idmonopolia") is None:
            async with httpx.AsyncClient() as client:
                idmonopolia = await create_reserve(client, id_zakaz, note)
            await get_mongo_coll(WB_COLL).update_one(
                {"id_zakaz": id_zakaz}, {"$set": {"idmonopolia": idmonopolia}}
            )
            logger.info(f"Для id_zakaz={id_zakaz} создан резерв. idmonopolia={idmonopolia}")
            _ = await epool_request(
                {
                    "act": "param_market",
                    "id": id_zakaz,
                    "idmonopolia": idmonopolia,
                }
            )
            logger.info(f"idmonopolia={idmonopolia} успешно передан в админку")
        else:
            idmonopolia = idmon["idmonopolia"]
        message["_id"] = idmonopolia

        if idmon["status"] == "awaiting_packaging":
            idgoods = [int(item.offer_id) for item in info.order_items]
            cnts = [item.product_count for item in info.order_items]
            result_calc: list[dict] = await weight_calc(idgoods, cnts, info.order_id)
            confirm_order = Equip(
                posting_number=str(info.order_id),
                weight=(result_calc[0]["weight"] or result_calc[-1]["weight"]) * 1000,
                width=(result_calc[0]["width"] or result_calc[-1]["width"]) * 100,
                height=(result_calc[0]["height"] or result_calc[-1]["height"]) * 100,
                depth=(result_calc[0]["length"] or result_calc[-1]["length"]) * 100,
                items=[
                    {"quantity": str(item.product_count), "sku": int(str(item.item_offer).replace('*',''))}
                    for item in info.order_items
                ],
            )

            await equip(confirm_order, id_zakaz)

        get_queue_client().send_message(
            SETTINGS.YANDEX_QUEUES["trace"], json.dumps(message)
        )
        logger.info(
            f"В очередь {SETTINGS.YANDEX_QUEUES['trace']} отправлено сообщение {message}"
        )
    except Exception as e:
        logger.exception(e)
        _ = await epool_request(
            {
                "act": "status_market",
                "id": int(id_zakaz),
                "status": STATUS2STANDARD[info.xway_status],
            }
        )


async def epool_request(request_wc, url=SETTINGS.EPOOL_URL) -> httpx.Response:
    request_wc = delete_none(request_wc)
    request = {"login": SETTINGS.LOGIN_AB, "passw": SETTINGS.PASSWORD_AB, **request_wc}
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(url=url, json=request)
    logger.info(
        f"POST {res.status_code} {url} json={request_wc} resp={res.content}"  # type: ignore
    )
    return res
