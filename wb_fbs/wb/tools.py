import logging
import logging.config
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import httpx
import motor.motor_asyncio as aiomotor
import sentry_sdk
import yaml
from fastapi import HTTPException
from starlette.requests import Request

from api_reservation.api import ReservationClient
from env import SETTINGS
from wb.consts import ROOT_DIR, LOGS_DIR, VERSION, conf
from ya_queue import YAQueueClient

logger = logging.getLogger(SETTINGS.SERVICE_NAME)


async def init_dbs():
    conf.mongo = aiomotor.AsyncIOMotorClient(SETTINGS.CONECT_MONGO)


async def disconnect_dbs():
    conf.mongo.close()


@lru_cache(maxsize=3)
def get_mongo_coll(collection):
    db = conf.mongo.get_database(name="xway_wb")
    mng_coll = db.get_collection(collection)

    return mng_coll


async def weight_calc(ids, cnts, order_id):
    # [{"id": 10001, "cnt": 4},{"id": 10000, "cnt": 1}]
    d_of_items = [{"id": id_good, "cnt": amount} for id_good, amount in zip(ids, cnts)]
    async with httpx.AsyncClient() as client:
        url = f"{SETTINGS.WEIGHT_CALC_URL}/weight_calc/sizes/"
        result = await client.post(url=url, json=d_of_items)
        logger.info(f"POST {url} json={d_of_items} response={result.content}")
        if result.status_code == 200:
            return result.json()
        else:
            logger.error(
                f"Не удалось рассчитать габариты weight_calc order_id={order_id}"
            )


def delete_none(_dict):
    for key, value in list(_dict.items()):
        if isinstance(value, dict):
            delete_none(value)
        elif value is None:
            _dict.pop(key)
    return _dict


def extract_datetime(shipment_date):
    #   "2021-08-17T16:27:33+03:00"
    date = shipment_date.split("+")[0]
    datetime_ = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    date = datetime_.strftime("%Y-%m-%d %H:%M")
    return date, datetime_


async def write_to_mongo(coll_name: str, data: dict):
    mng_coll = get_mongo_coll(coll_name)
    await mng_coll.insert_one(data)
    logger.info(f"В MongoDB в коллекцию {coll_name} добавлена запись {data}")


async def replace_mongo(coll_name: str, data: dict):
    mng_coll = get_mongo_coll(coll_name)
    await mng_coll.replace_one({"_id": data["_id"]}, data, upsert=True)
    logger.info(f"В MongoDB в коллекцию {coll_name} перезаписана запись {data}")


async def find_mongo(coll_name: str, posting_number: int | str) -> dict:
    res = await find_mongo_data(coll_name, {"_id": posting_number})

    assert res, f"Такой posting_number={posting_number} в БД не найден"

    logger.info(
        f"В MongoDB в коллекции {coll_name} найдена запись с posting_number={posting_number}"
    )
    return res


async def find_mongo_data(
    coll_name: str, data: dict | None, projection: dict | None = None
) -> dict | None:
    mng_coll = get_mongo_coll(coll_name)
    if projection:
        res = await mng_coll.find_one(data, projection)
    else:
        res = await mng_coll.find_one(data)
    return res


async def update_mongo(coll_name: str, index, data: dict):
    mng_coll = get_mongo_coll(coll_name)
    await mng_coll.update_one({"_id": index}, data)
    logger.info(
        f"В MongoDB в коллекции {coll_name} дополнена запись с _id={index} следующими полями: {data}"
    )


def check_auth_token(request: Request):
    """Проверяет авторизационный токен из заголовка запроса."""

    auth_token = request.headers.get("Authorization")

    if auth_token != SETTINGS.AUTH_TOKEN_XWAY:
        logger.info("Получен невалидный токен: %s", auth_token)
        raise HTTPException(status_code=403, detail="Bad token.")

    logger.info("Получен валидный токен.")


def init_logging(use_sentry=True, self_path: Path = ROOT_DIR):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    conf_log_path = self_path / "logging.yaml"
    config = yaml.full_load(conf_log_path.open())
    logging.config.dictConfig(config["logging"])

    if use_sentry and SETTINGS.SENTRY_TOKEN:
        sentry_sdk.init(  # type: ignore
            dsn=SETTINGS.SENTRY_TOKEN, release=f"{SETTINGS.SERVICE_NAME}@{VERSION}"
        )

    sentry_sdk.set_tag("service_name", SETTINGS.SERVICE_NAME)
    sentry_sdk.set_tag("maintainer", "aslamov")


@lru_cache(maxsize=1)
def get_queue_client():
    return YAQueueClient(
        aws_access_key_id=SETTINGS.YANDEX_QUEUE_AUTH["access_key"],
        aws_secret_access_key=SETTINGS.YANDEX_QUEUE_AUTH["secret_key"],
    )


@lru_cache(maxsize=1)
def get_reservation_client():
    return ReservationClient(
        token=SETTINGS.RESERVATION_TOKEN, url=SETTINGS.RESERVATION_URL, logger=logger
    )
