import asyncio
import datetime
import logging
from pathlib import Path

from env import SETTINGS
from wb.consts import WB_COLL, ACT_CACHE_COLL, LABELS_CACHE_COLL
from wb.create_acts import create_acts, get_act_by_id
from wb.create_order import epool_request
from wb.endpoint import get_this_day_labels
from wb.labels import send_then_delete_file
from wb.tools import get_mongo_coll, init_logging, init_dbs


async def update_statuses(logger):
    # полночь
    right_now = datetime.datetime.now()
    day_before = (right_now - datetime.timedelta(days=1)).replace(hour=0, microsecond=0, second=0, minute=0)

    cache_coll = get_mongo_coll(ACT_CACHE_COLL)
    act_cache = await cache_coll.find_one({"date": day_before})
    postings = act_cache["postings"]

    coll = get_mongo_coll(WB_COLL)
    mongo_info = coll.find({"_id": {"$in": postings}})

    async for row in mongo_info:
        _ = await epool_request(
            {
                "act": "status_market",
                "id": int(row["id_zakaz"]),
                "status": "delivering",
            }
        )

    update_result = await coll.update_many({"_id": {"$in": postings}}, {"$set": {"status": "delivering"}})
    logger.info(f"Обновлено {update_result.modified_count} статусов по следующим {len(postings)} заявкам: {postings}")


async def main():
    Path("docs").mkdir(exist_ok=True)
    init_logging()
    await init_dbs()
    logger = logging.getLogger(SETTINGS.SERVICE_NAME)

    # если не получится обновить статусы -- то и акт не получится заполучить
    await update_statuses(logger)

    # МСК время
    right_now = datetime.datetime.now()
    logger.info(f"Запрос акта {right_now}")
    today = right_now.replace(hour=0, minute=0, second=0, microsecond=0)
    orders = [
        i
        async for i in get_mongo_coll(WB_COLL).find(
            {"status": {"$eq": "awaiting_deliver"}},
            {"_id": 1, "id_zakaz": 1},
        )
    ]
    postings = [i["_id"] for i in orders]
    if not postings:
        logger.info(f"Не найдены отправления со статусом `awaiting_deliver` на момент {today}")
        return
    try:
        id_act = await create_acts(postings)
        await asyncio.sleep(11)
        filename = await get_act_by_id(id_act)
        s3_path = await send_then_delete_file("Акт", filename, directory="acts")

        await get_mongo_coll(ACT_CACHE_COLL).insert_one(document={"date": today, "postings": postings,
                                                                  "s3_path": s3_path, "id_act": id_act})
    except Exception as e:
        logger.exception(f"Не удалось сформировать акт {e}")

    try:
        ids_zakaz = [i["id_zakaz"] for i in orders]
        result = await get_this_day_labels(ids_zakaz)
        await get_mongo_coll(LABELS_CACHE_COLL).insert_one(document={"date": today, "postings": postings, **result})
    except Exception as e:
        logger.exception(f"Не удалось сформировать файл наклеек на сегодня {e}")


if __name__ == "__main__":
    asyncio.run(main())
