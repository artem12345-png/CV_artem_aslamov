from app.db import DBS
from app.settings.log import logger


async def get_number(idmonopolia: int):
    logger.info(f"SMS-SENDER: поиск номера для заказа {idmonopolia}")

    QUERY_GET_PHONE = (
        "SELECT phone "
        "FROM mircomf4_epool.ep_zakaz_mon4tk "
        f'WHERE idmonopolia="{idmonopolia}";'
    )
    mysql_read = DBS["mysql"]
    phone = (await mysql_read.fetch_one(QUERY_GET_PHONE))[0]
    logger.info(f"SMS-SENDER: найден номер {phone} для заказа {idmonopolia}")

    res = ""
    try:
        res = await _validate_phone(idmonopolia, phone)
        is_found = True
    except AssertionError:
        is_found = False

    if not is_found:
        logger.info(f"SMS-SENDER: пробуем взять номер из другой базы")
        QUERY_GET_PHONE = (
            "SELECT phone_delivery "
            "FROM mircomf4_epool.ep_zakaz "
            f'WHERE idmonopolia="{idmonopolia}";'
        )
        phone = (await mysql_read.fetch_one(QUERY_GET_PHONE))[0]
        res = await _validate_phone(idmonopolia, phone)

    logger.info(f"SMS-SENDER: взят номер из базы {res} для заказа {idmonopolia}")

    return res


async def _validate_phone(idmonopolia, phone):
    if len(phone) == 11 and phone[:2] == "89":
        res = phone

    elif len(phone) == 12 and phone[:3] == "+79":
        res = "89" + phone[3:]

    elif len(phone) == 10 and phone[0] == "9":
        res = "8" + phone

    else:
        logger.warning(f"SMS-SENDER: номер {phone} невалидный для заказа {idmonopolia}")
        raise AssertionError("Номер невалиден")

    logger.info(f"SMS-SENDER: номер прошел валидацию {phone} для заказа {idmonopolia}")
    return res
