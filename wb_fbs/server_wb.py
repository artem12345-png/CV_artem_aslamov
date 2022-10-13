import asyncio
import datetime
import json
import secrets
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_utils.tasks import repeat_every
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.background import BackgroundTasks

from env import SETTINGS
from wb.change_status import update_status
from wb.consts import WB_COLL, PREFIX, LABEL_REQUESTS_COLL, DIRECTORY, QUEUE_DATE_FORMAT, ACT_CACHE_COLL, \
    LABELS_CACHE_COLL
from wb.create_order import create_order, epool_request, get_full_info, actions_after_create
from wb.endpoint import get_this_day_labels
from wb.labels import get_labels, modify_cargo_pdf, send_then_delete_file
from wb.models import BasicModel, DateRequest, Goods, ChangeStatusRequest
from wb.tools import (
    replace_mongo,
    get_mongo_coll,
    init_dbs,
    disconnect_dbs,
    logger,
    init_logging,
    get_queue_client,
    check_auth_token
)

xway_router = APIRouter()
basic_router = APIRouter()
security = HTTPBasic()


async def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    auth_secret = SETTINGS.AUTH_TO_SERVICE
    correct_username = secrets.compare_digest(
        credentials.username, auth_secret.get("username")
    )
    correct_password = secrets.compare_digest(
        credentials.password, auth_secret.get("password")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@basic_router.get("/self_check/")
async def self_check():
    await get_mongo_coll(WB_COLL).find_one()
    return {"status": "Ok"}


@basic_router.on_event("startup")
async def startup():
    await init_dbs()
    asyncio.create_task(trace_label())


@repeat_every(wait_first=True, seconds=60)
async def trace_label():
    QUEUE_TRACE = SETTINGS.YANDEX_QUEUES["trace"]
    tasks = []
    for body, receipt in get_queue_client().get_messages(QUEUE_TRACE):
        logger.info(f"Взято сообщение {body} из очереди {QUEUE_TRACE}")
        task = asyncio.create_task(trace_it(body, receipt, QUEUE_TRACE))
        tasks.append(task)
    for task in tasks:
        await task


async def get_label(posting_number, id_zakaz, goods, date_delivery, idmonopolia):
    pdf = await get_labels(posting_number)
    pdf_modified = modify_cargo_pdf(
        pdf,
        idmonopolia,
        goods.items[0].name,
        artikul=goods.items[0].idgood,
        date_delivery=date_delivery,
    )
    result_file = f"{DIRECTORY}/wb_label_{id_zakaz}_{idmonopolia}_{posting_number}.pdf"
    with open(result_file, "wb") as f:
        f.write(pdf_modified.read())
    return result_file


async def trace_it(body, receipt, queue_name):
    id_zakaz, posting_number, goods, date_delivery = (
        body["id_zakaz"],
        body["posting_number"],
        body["goods"],
        body["date_delivery"],
    )
    goods = Goods(items=goods)
    try:
        logger.info(f"Получаем этикетку для id_zakaz={id_zakaz}")

        pdf_path = await get_label(
            posting_number,
            id_zakaz,
            goods,
            datetime.datetime.strptime(date_delivery, QUEUE_DATE_FORMAT).strftime(
                "%d-%m-%Y %H:%M"
            ),
            idmonopolia=body["_id"],
        )
        logger.info(f"Этикетка получена для id_zakaz={id_zakaz}")
        s3_path = await send_then_delete_file(id_zakaz, pdf_path)
        logger.info(f"Этикетка положена в S3 по s3_path={s3_path}")

        resp = await epool_request(
            {"act": "stickers_after", "id": id_zakaz, "s3_path": s3_path}
        )
        j_resp = resp.json()
        assert (
            j_resp.get("error") is None
        ), f"Ошибка при запросе к Epool {j_resp['error']}"

        await replace_mongo(
            LABEL_REQUESTS_COLL,
            {
                "_id": id_zakaz,
                "posting_number": posting_number,
                "s3_path": s3_path,
                "date": datetime.datetime.now(tz=datetime.timezone.utc),
            },
        )
        get_queue_client().ack(queue_name, receipt)
    except Exception as e:
        logger.exception(e)


@basic_router.on_event("shutdown")
async def shutdown():
    await disconnect_dbs()


@xway_router.post("/add")
async def new_order(
    request: Request, background_tasks: BackgroundTasks, order: BasicModel
):
    check_auth_token(request)
    background_tasks.add_task(
        replace_mongo,
        coll_name="wb_create_order",
        data={
            "_id": int(order.order_id),
            "date": datetime.datetime.now(tz=datetime.timezone.utc),
            "request": order.dict(),
        },
    )
    coll = get_mongo_coll(WB_COLL)
    res = await coll.find_one({"_id": int(order.order_id)})
    if res:
        return {"success": True}

    success = True
    try:
        await create_order(order)
    except Exception as e:
        logger.exception(f"Не удалось создать заказ {order.order_id}: {e}")
        success = False

    return {"success": success}


@xway_router.post("/add/xway/orders/add")
async def new_order(
    request: Request, background_tasks: BackgroundTasks, order: BasicModel
):
    check_auth_token(request)
    background_tasks.add_task(
        replace_mongo,
        coll_name="wb_create_order",
        data={
            "_id": int(order.order_id),
            "date": datetime.datetime.now(tz=datetime.timezone.utc),
            "request": order.dict(),
        },
    )
    coll = get_mongo_coll(WB_COLL)
    res = await coll.find_one({"_id": int(order.order_id)})
    if res:
        return {"success": True}

    success = True
    try:
        await create_order(order)
    except Exception as e:
        logger.exception(f"Не удалось создать заказ {order.order_id}: {e}")
        success = False

    return {"success": success}


@xway_router.put("/update")
async def update_order(
    request: Request, background_tasks: BackgroundTasks, order: dict
):
    """
    Это вебхук для XWAY
    Change status с помощью xway
    order с другим статусом
    """
    check_auth_token(request)
    background_tasks.add_task(
        get_mongo_coll("wb_statuses").insert_one,
        document={"date": datetime.datetime.now(), "request": json.loads((await request.body()).decode())},
    )
    await update_status(order)
    return {"success": True}


@xway_router.put("/add/xway/order/update")
async def update_order(
    request: Request, background_tasks: BackgroundTasks, order: dict
):
    """
    Это вебхук для XWAY
    Change status с помощью xway
    order с другим статусом
    """
    check_auth_token(request)
    background_tasks.add_task(
        get_mongo_coll("wb_statuses").insert_one,
        document={"date": datetime.datetime.now(), "request": json.loads((await request.body()).decode())},
    )
    try:
        await update_status(order)
    finally:
        return {"success": True}


@xway_router.get("/create_act")
async def get_act(username: str = Depends(get_current_username)):
    today_datetime = datetime.datetime.now().replace(microsecond=0, minute=0, second=0, hour=0)
    result = await get_mongo_coll(ACT_CACHE_COLL).find_one({"date": today_datetime})
    if result is None:
        return {"error": "Не удалось получить акт. Обратитесь к разработчикам."}
    del result["_id"]

    return result


@xway_router.post("/concat_labels")
async def concat_labels(
    req_date: DateRequest, username: str = Depends(get_current_username)
):
    date = datetime.datetime.strptime(req_date.date, "%d-%m-%Y")
    today_datetime = datetime.datetime.now().replace(microsecond=0, minute=0, second=0, hour=0)

    if date == (today_datetime + datetime.timedelta(days=1)):
        return {"error": f"Запросить наклейки на {req_date.date} можно только после 00:00 по МСК"}

    result = await get_mongo_coll(LABELS_CACHE_COLL).find_one({"date": today_datetime})
    if result is None:
        return {"error": "Не удалось получить наклейки на сегодня. Обратитесь к разработчикам."}

    del result["_id"]
    return result


@xway_router.post("/change_status")
async def change_status_request(
    request_change: ChangeStatusRequest,
    username: str = Depends(get_current_username),
):
    idmonopolia, id_zakaz = request_change.idmonopolia, request_change.id_zakaz
    logger.info(f"Запрос на смену статуса equip {idmonopolia} {id_zakaz}")

    mongo_info = await get_mongo_coll(WB_COLL).find_one({"id_zakaz": id_zakaz})
    message = {
        "id_zakaz": id_zakaz,
        "posting_number": mongo_info["_id"],
        "goods": mongo_info["goods"],
        "date_delivery": mongo_info["date_delivery"].strftime(QUEUE_DATE_FORMAT),
    }
    info = await get_full_info(mongo_info["_id"])
    await actions_after_create(id_zakaz, info, message)
    return {
        "error": "Не удалось перевести заказ в состояние 'Собранный'. Обратитесь к разработчикам."
    }


def init_app(use_sentry=True):
    Path(DIRECTORY).mkdir(exist_ok=True)
    init_logging(use_sentry=use_sentry)
    app = FastAPI()
    app.include_router(basic_router)
    app.include_router(xway_router, prefix=PREFIX)
    if use_sentry:
        app = SentryAsgiMiddleware(app)

    return app


def run():
    app = init_app()
    uvicorn.run(app, host="0.0.0.0", port=8866)


if __name__ == "__main__":
    run()
