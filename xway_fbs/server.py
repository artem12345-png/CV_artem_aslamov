import asyncio
import binascii
import datetime
import io
import json
import secrets
from pathlib import Path

import httpx
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.background import BackgroundTasks

from api_ozon.models import OzonStatuses
from env import BUCKET_NAME_S3, QUEUE_CREATE, QUEUE_TRACE
from ozon.consts import (
    PREFIX,
    DIRECTORY,
    GET_IDZAK_BY_IDMON,
    QUEUE_DATE_FORMAT,
    OZON_COLL,
    AUTH_COLL,
    REQUESTS_ACT_COLL,
    LABEL_REQUESTS_COLL,
    TRACE_LABELS_WAIT_SECONDS,
    CREATING_QUEUE_WAIT_SECONDS,
)
from ozon.create_order import create_order, actions_after_create
from ozon.epool_request import epool_request
from ozon.labels_utils import send_then_delete_file
from ozon.endpoints import ship_endpoint
from ozon.models import (
    BasicModel,
    APIUpdateResponse,
    APIUpdateRequest,
    ChangeStatusRequest,
    Goods,
    DateRequest,
    ManualCreate,
    CancelModel,
    ManualIdmonopolia,
    GetLabelsAnotherDay,
)
from ozon.pdf_utils import concat_pdf, modify_cargo_pdf
from ozon.repeat_every import repeat_every
from ozon.simple_functions import extract_datetime
from ozon.tools import (
    init_dbs,
    disconnect_dbs,
    find_mongo,
    execute_sql,
    replace_mongo,
    get_ozon_api,
    get_queue_client,
)
from ozon.tools import (
    init_logging,
    logger,
    check_auth_token,
    write_to_mongo,
    find_mongo_data,
    get_mongo_coll,
)
from ozon.utils import (
    send_to_s3,
    get_object,
    get_single_pdf_act,
    get_today_delivery_methods,
)
from ozon.xway_requests import (
    CancelledError,
    get_label,
    get_idmonopolia,
)

xway_router = APIRouter()
basic_router = APIRouter()
security = HTTPBasic()


async def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    mng_coll = get_mongo_coll(AUTH_COLL)
    res = await mng_coll.find_one({"_id": credentials.username})

    correct_username = secrets.compare_digest(
        credentials.username, res.get("_id") if res else ""
    )
    correct_password = secrets.compare_digest(
        credentials.password, res.get("password") if res else ""
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def get_async_client():
    async with httpx.AsyncClient() as client:
        yield client


@basic_router.get("/self_check/")
async def self_check():
    await get_mongo_coll(OZON_COLL).find_one()
    await execute_sql("SELECT %s;", (1,))
    return {"status": "Ok"}


@xway_router.on_event("startup")
async def startup():
    await init_dbs()
    asyncio.create_task(trace_label())
    asyncio.create_task(get_messages())


@repeat_every(wait_first=True, seconds=TRACE_LABELS_WAIT_SECONDS)
async def trace_label():
    async with httpx.AsyncClient() as client:
        tasks = []
        for body, receipt in get_queue_client().get_messages(QUEUE_TRACE):
            logger.info(f"Взято сообщение {body} из очереди {QUEUE_TRACE}")
            task = asyncio.create_task(trace_it(body, receipt, QUEUE_TRACE, client))
            tasks.append(task)
        for task in tasks:
            await task


async def trace_it(body, receipt, queue_name, client):
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
            client=client,
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
                "s3_path": s3_path,
                "ozon_wait": [posting_number],
                "ozon_posting_numbers": [],
                "date": datetime.datetime.now(tz=datetime.timezone.utc),
            },
        )
        get_queue_client().ack(queue_name, receipt)
    except ValueError as e:
        logger.info(f"Для заказа {id_zakaz} этикетка ещё не создалась. {e}")
    except Exception as e:
        logger.exception(e)


@xway_router.on_event("shutdown")
async def shutdown():
    await disconnect_dbs()


@xway_router.post("/add")
async def new_order(
    request: Request, background_tasks: BackgroundTasks, order: BasicModel
):
    check_auth_token(request)
    background_tasks.add_task(
        replace_mongo,
        coll_name="xway_create_order",
        data={
            "_id": order.order_id,
            "date": datetime.datetime.now(tz=datetime.timezone.utc),
            "request": order.dict(),
        },
    )
    coll = get_mongo_coll(OZON_COLL)
    res = await coll.find_one({"_id": order.order_id})
    if res:
        logger.info(f"Запрос от XWAY - {order.order_id} уже создан")
        return {"success": True}
    else:
        return {"success": False}


@basic_router.post("/add_manual")
async def manual_new_order(
    order: ManualCreate,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    logger.info(f"CREATE NEW ORDER MANUAL {order.posting_number}")
    await create_order(client, order.posting_number)
    return {"detail": "ok"}


@basic_router.post("/actions_after_create_manual")
async def actions_after_create_endpoint(
    order: ManualCreate,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    logger.info(f"ACTIONS AFTER CREATE_MANUAL {order.posting_number}")
    coll = get_mongo_coll(OZON_COLL)
    row = await coll.find_one({"_id": order.posting_number})
    if row is None:
        return {"error": "Заказ не найден в системе. Сначала нужно создать заказ."}
    if row["status"] != OzonStatuses.awaiting_packaging.value or row["ozon_departures"]:
        return {
            "error": f"Заказ не находится в состоянии {OzonStatuses.awaiting_packaging.value}"
        }
    ozon_client = get_ozon_api()
    info = await ozon_client.get_info(order.posting_number)
    await actions_after_create(client, row["id_zakaz"], info["result"])
    return {"detail": "ok"}


@basic_router.post("/trace_manual")
async def trace_manual(
    order: ManualCreate, username: str = Depends(get_current_username)
):
    logger.info(f"TRACE MANUAL {order.posting_number}")
    posting_number = order.posting_number
    row = await get_mongo_coll(OZON_COLL).find_one({"_id": posting_number})
    if row is None:
        error_message = {"error": f"Такой заказ {posting_number} не найден"}
        logger.info(error_message)
        return error_message

    id_zakaz = row["id_zakaz"]
    idmonopolia = await get_idmonopolia(id_zakaz)
    body = json.dumps(
        {
            "_id": idmonopolia,
            "idmonopolia": idmonopolia,
            "id_zakaz": id_zakaz,
            "posting_number": posting_number,
            "goods": row["goods"],
            "date": datetime.datetime.now(tz=datetime.timezone.utc).strftime(
                QUEUE_DATE_FORMAT
            ),
            "date_delivery": row["date_delivery"].strftime(QUEUE_DATE_FORMAT),
        }
    )
    get_queue_client().send_message(QUEUE_TRACE, body)
    return {"detail": "ok"}


@basic_router.post("/idmonopolia_link_manual")
async def link_manual(
    req: ManualIdmonopolia, username: str = Depends(get_current_username)
):
    _ = await epool_request(
        {
            "act": "param_market",
            "id": req.id_zakaz,
            "idmonopolia": req.idmonopolia,
        }
    )
    return {"detail": "ok"}


@basic_router.post(
    "/get_postings_another_day",
    description="""
    Использовать, когда нужны наклейки для отправлений, которые не забрали в один из дней.
""",
)
async def get_postings_another_day(
    req: GetLabelsAnotherDay,
    client: httpx.AsyncClient = Depends(get_async_client),
    username: str = Depends(get_current_username),
):
    return await redownload_previous_labels(client, req.date)


async def redownload_previous_labels(client, date):
    date_obj = datetime.datetime.strptime(date, "%d-%m-%Y")
    postings = [
        i["_id"]
        async for i in get_mongo_coll(OZON_COLL).find(
            {
                "$and": [
                    {"date_delivery": {"$gte": date_obj}},
                    {"date_delivery": {"$lt": date_obj + datetime.timedelta(days=1)}},
                    {"status": {"$eq": OzonStatuses.awaiting_deliver.value}},
                ]
            }
        )
    ]

    ozon_api = get_ozon_api()
    pdfs = []
    for posting in postings:
        try:
            pdf = await ozon_api.get_label(client, {"posting_number": [posting]})
            pdfs.append(io.BytesIO(pdf))
        except Exception as e:
            logger.info(f"Не удалось скачать наклейку для {posting}")
        await asyncio.sleep(0.2)

    if not pdfs:
        return {"error": "Не удалось скачать наклейки"}

    id2row = {
        i["_id"]: i
        async for i in get_mongo_coll(OZON_COLL).find({"_id": {"$in": postings}})
    }
    result = []
    for i, doc in enumerate(pdfs):
        posting_number = postings[i]
        info = id2row[posting_number]
        modified_doc = modify_cargo_pdf(
            doc,
            info["idmonopolia"],
            info["goods"][0]["name"],
            info["goods"][0]["idgood"],
            datetime.datetime.now().strftime("%d-%m-%Y"),
        )
        result.append(modified_doc)
    pdf_path: str = concat_pdf(result)
    try:
        s3_path = await send_to_s3(
            pdf_path, f"labels/{pdf_path.split('/')[-1].replace(' ', '_')}"
        )
    except Exception as e:
        logger.exception(e)
        return {"error": "Не удалось отправить файл в хранилище S3"}
    return {"s3_path": s3_path}


@xway_router.post("/cancel")
async def cancel(
    request: CancelModel,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    logger.info(f"Пришёл запрос на удаление {request}")
    try:
        mongo_row = await find_mongo(OZON_COLL, request.id_zakaz)
        posting_number: str = mongo_row["_id"]
        ozon_api = get_ozon_api()
        resp = await ozon_api.cancel_order(
            client, posting_number, request.id_cancel, request.reason
        )
        logger.info(
            f"Заказ {posting_number} по отмене вернул {resp}. Успешно отменён {request.id_zakaz}"
        )

        return {"status": f"Заказ с номером {request.id_zakaz} отменен", "resp": resp}
    except (AssertionError, CancelledError) as e:
        logger.info(f"Ошибка отмены заказа: {e}")
        return {"error": e.args[0]}


@basic_router.put("/xway/order/update")
async def update_order(
    request: Request, background_tasks: BackgroundTasks, order: BasicModel
):
    """
    Это вебхук для XWAY
    """
    check_auth_token(request)
    return {"success": True}


async def delete_cache_cancellation(sh_date):
    if sh_date is None:
        return

    if isinstance(sh_date, datetime.datetime):
        shipment_date = sh_date
    else:
        _, shipment_date = extract_datetime(sh_date)

    shipment_date = shipment_date.replace(hour=0, minute=0, second=0, microsecond=0)

    today_midnight = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if shipment_date == today_midnight:
        ozon_coll = get_mongo_coll(REQUESTS_ACT_COLL)
        logger.info(f"Очищаем кэш акта на сегодня {today_midnight}")
        await ozon_coll.delete_many({"date": {"$gte": shipment_date}})


@xway_router.post("/change_status")
async def change_status_request(
    request_change: ChangeStatusRequest,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    idmonopolia, id_zakaz = request_change.idmonopolia, request_change.id_zakaz
    result = await ship_endpoint(
        client, id_zakaz, idmonopolia, request_change.force_label
    )

    return result


@xway_router.post("/concat_labels")
async def concat_labels(
    req_date: DateRequest,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    yesturday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%d-%m-%Y"
    )
    if req_date.date == yesturday:
        result = await redownload_previous_labels(client, yesturday)
        return result
    else:
        pdfs = await get_this_day_pdfs(req_date)
        if not pdfs:
            return {"error": "Для этого дня не нашлось этикеток"}

        result_filename = concat_pdf(pdfs)
        s3_path = await send_then_delete_file("Общая заявка", result_filename)

        return {"s3_path": s3_path}


async def get_this_day_pdfs(req_date):
    # Найти в монге с ответами нашего апи релевантные файлы
    logger.info(f"Пришёл запрос на формирование наклеек: {req_date}")
    date = datetime.datetime.strptime(req_date.date, "%d-%m-%Y")
    ozon_coll = get_mongo_coll(OZON_COLL)
    ids = [
        i["id_zakaz"]
        async for i in ozon_coll.find(
            {
                "$and": [
                    {"date_delivery": {"$gte": date}},
                    {"date_delivery": {"$lt": date + datetime.timedelta(days=1)}},
                    {"status": {"$not": {"$eq": "cancelled"}}},
                ]
            },
            {"id_zakaz": 1},
        )
    ]
    tasks = []
    request_coll = get_mongo_coll(LABEL_REQUESTS_COLL)
    async for i in request_coll.find({"_id": {"$in": ids}}):
        filename = i["s3_path"]
        task = asyncio.create_task(get_object(bucket=BUCKET_NAME_S3, filename=filename))
        tasks.append(task)
    pdfs = []
    for task in tasks:
        file_path = await task
        with open(file_path, "rb") as f:
            content = f.read()
        pdfs.append(io.BytesIO(content))
    return pdfs


@xway_router.get("/create_act")
async def get_act(
    background_tasks: BackgroundTasks,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    requests_db = REQUESTS_ACT_COLL
    # Проверка на кэш
    today_midnight = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    row: dict | None = await find_mongo_data(
        requests_db, {"date": {"$gte": today_midnight}}, {"_id": False, "date": False}
    )
    if row:
        logger.info(
            f"Возвращаем для create_act кэшированный результат на сегодняшний день: {row}"
        )
        return row

    result_posting_numbers = await get_today_delivery_methods()
    file_name = await get_single_pdf_act(result_posting_numbers)
    s3_path = await send_to_s3(
        file_name, f"acts/{file_name.split('/')[-1].replace(' ', '_')}"
    )
    logger.info(f"Возвращаем ссылку на s3 с накладными, s3_path={s3_path}")

    res = {"s3_path": s3_path}
    background_tasks.add_task(
        write_to_mongo,
        coll_name=requests_db,
        data={**res, "date": datetime.datetime.now(tz=datetime.timezone.utc)},
    )

    return res


async def get_info_by_id(*, idmonopolia: int | None, id_zakaz: int | None) -> dict:
    assert idmonopolia or id_zakaz, "Должен быть указан idmonopolia или id_zakaz"
    if id_zakaz is None:
        rows: tuple[tuple] = await execute_sql(GET_IDZAK_BY_IDMON, (idmonopolia,))  # type: ignore
        assert rows, f"По idmonopolia={idmonopolia} не найден id_zakaz"
        id_zakaz = rows[0][0]

    mongo_row = await find_mongo(coll_name=OZON_COLL, id_zakaz=id_zakaz)
    return mongo_row


@xway_router.post("/update", response_model=APIUpdateResponse)
async def update_realfbs(
    request: APIUpdateRequest,
    username: str = Depends(get_current_username),
    client: httpx.AsyncClient = Depends(get_async_client),
):
    logger.info(f"Пришёл запрос на обновление статуса: {request.dict()}")
    logger.exception("Запрос не реализован")

    return {"error": "Метод не реализован"}


@repeat_every(wait_first=True, seconds=CREATING_QUEUE_WAIT_SECONDS)
async def get_messages():
    await create_from_queue()


async def create_from_queue():
    queue_name = QUEUE_CREATE
    client = get_queue_client()
    client_httpx = httpx.AsyncClient()
    try:
        messages = client.get_messages(queue_name, count_messages=10)
        if len(messages):
            logger.info(f"Взято {len(messages)} сообщений из очереди {queue_name}")
        for message, id_delete in messages:
            try:
                await create_order(client_httpx, message["posting_number"], message)
                client.ack(queue_name, id_delete)
                logger.info(
                    f"Заказ posting_number={message['posting_number']} обработан"
                )
            except Exception as e:
                logger.exception(e)
    except Exception as e:
        logger.exception(e)
    finally:
        await client_httpx.aclose()


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
    uvicorn.run(app, host="0.0.0.0", port=8998)


if __name__ == "__main__":
    run()
